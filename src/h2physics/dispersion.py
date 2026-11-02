"""User-selected dispersion ownership; selection does not establish validity."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import numpy as np

from .core import ThermoState
from .release import NozzleOpening, SourceLocation

if TYPE_CHECKING:
    from .adapters.slabx_lh2 import SLABLH2SnapshotSeries, SLABLH2SourceTolerances
    from .sources import IntervalMassSource


_PENDING_DISPERSION_EXECUTION_ISSUERS = set()


def _configuration_snapshot(value, active=None):
    """Fingerprint nested solver-option containers without copying native objects."""
    if isinstance(value, np.ndarray):
        contiguous = np.ascontiguousarray(value)
        if contiguous.dtype.hasobject:
            payload = tuple(_configuration_snapshot(item, active) for item in contiguous.flat)
        else:
            payload = sha256(contiguous.tobytes()).hexdigest()
        return ("array", contiguous.shape, contiguous.dtype.str, payload)
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return (type(value).__name__, value)
    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        return ("cycle", type(value).__qualname__, identity)
    if isinstance(value, Mapping):
        active.add(identity)
        result = ("mapping", tuple(sorted(
            ((_configuration_snapshot(key, active), _configuration_snapshot(item, active))
             for key, item in value.items()), key=repr,
        )))
        active.remove(identity)
        return result
    if isinstance(value, (tuple, list)):
        active.add(identity)
        result = (type(value).__name__, tuple(_configuration_snapshot(item, active) for item in value))
        active.remove(identity)
        return result
    if isinstance(value, (set, frozenset)):
        active.add(identity)
        result = (type(value).__name__, tuple(sorted(
            (_configuration_snapshot(item, active) for item in value), key=repr,
        )))
        active.remove(identity)
        return result
    # Native option objects are passed through by identity; their internal state
    # belongs to the provider and is not treated as scenario configuration here.
    return (type(value).__qualname__, identity)


def _issue_dispersion_execution_token():
    token = object()
    _PENDING_DISPERSION_EXECUTION_ISSUERS.add(token)
    return token


@dataclass(frozen=True, slots=True)
class DispersionExecution:
    """Scenario-level receipt retaining release origin and provider ownership."""

    family: HydrogenReleaseFamily
    provider_id: str
    result: Any = field(repr=False, compare=False)
    source_evidence_ids: tuple[str, ...]
    accepted: bool | None
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _snapshot: Any = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_DISPERSION_EXECUTION_ISSUERS:
            raise TypeError("Create dispersion executions through DispersionScenario.run()")
        _PENDING_DISPERSION_EXECUTION_ISSUERS.remove(self._issuer_token)
        family = HydrogenReleaseFamily(self.family)
        expected = preferred_dispersion_provider(family)
        if self.provider_id != expected:
            raise ValueError("Execution provider does not match its declared release family")
        if isinstance(self.source_evidence_ids, (str, bytes)):
            raise TypeError("Source evidence must be a sequence of evidence identities")
        evidence = tuple(self.source_evidence_ids)
        if not evidence or any(not isinstance(value, str) or not value.strip()
                               for value in evidence):
            raise ValueError("Execution receipt needs explicit source evidence identities")
        if self.accepted is not None and type(self.accepted) is not bool:
            raise TypeError("Execution acceptance is bool when reported, otherwise None")
        result_acceptance = getattr(self.result, "accepted", None)
        if result_acceptance is not None and type(result_acceptance) is not bool:
            raise TypeError("Provider result acceptance must be bool or None")
        if result_acceptance is not self.accepted:
            raise ValueError("Execution acceptance must match the retained provider result")
        if family is HydrogenReleaseFamily.HIGH_PRESSURE_GAS:
            result_evidence = (getattr(self.result, "evidence_id", None),)
        else:
            boundary = getattr(self.result, "boundary", None)
            mass_source = getattr(boundary, "mass_source", None)
            result_evidence = (
                getattr(mass_source, "evidence_id", None),
                getattr(boundary, "footprint_evidence_id", None),
            )
        if result_evidence != evidence:
            raise ValueError("Execution evidence IDs differ from the retained provider boundary")
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "source_evidence_ids", evidence)
        object.__setattr__(self, "_snapshot", self._current_snapshot())

    def _current_snapshot(self):
        # Lazy import avoids the adapters package's public re-exports importing
        # this module during initialization. This only fingerprints stored data.
        from .adapters.slabx_lh2 import _snapshot_signature

        return _snapshot_signature((self.family, self.provider_id, self.result,
                                    self.source_evidence_ids, self.accepted))

    def require_current(self) -> DispersionExecution:
        """Reject changed provider results or evidence after receipt construction."""
        if self._issuer_token in _PENDING_DISPERSION_EXECUTION_ISSUERS:
            raise ValueError("Dispersion execution has an unconsumed result issuer")
        if self._current_snapshot() != self._snapshot:
            raise ValueError("Dispersion result, acceptance, or source evidence changed after capture")
        return self


class DispersionExecutionError(RuntimeError):
    """Add selected provider identity while preserving the original failure/result."""

    def __init__(self, family, provider_id, cause):
        self.family = HydrogenReleaseFamily(family)
        self.provider_id = provider_id
        self.result = getattr(cause, "result", None)
        self.cause = cause
        super().__init__(f"Preferred dispersion provider {provider_id!r} failed for {self.family.value}")


class HydrogenReleaseFamily(StrEnum):
    HIGH_PRESSURE_GAS = "high_pressure_gas"
    LIQUID_HYDROGEN_ORIGIN = "liquid_hydrogen_origin"


def _require_acceptance_flag(value):
    if type(value) is not bool:
        raise TypeError("require_accepted must be an explicit bool")
    return value


def preferred_dispersion_provider(family: HydrogenReleaseFamily | str) -> str:
    """Choose by declared release origin; absence/failure never triggers fallback."""
    return {
        HydrogenReleaseFamily.HIGH_PRESSURE_GAS: "hyram",
        HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN: "slabx-lh2",
    }[HydrogenReleaseFamily(family)]


@dataclass(frozen=True, slots=True)
class DispersionScenario:
    """Lazy, Python-native dispersion request with explicit physical ownership."""

    family: HydrogenReleaseFamily | str
    inputs: Mapping = field(repr=False)
    _solver_options_signature: Any = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        selected = HydrogenReleaseFamily(self.family)
        if not isinstance(self.inputs, Mapping):
            raise TypeError("Scenario inputs must be a mapping of named Python objects")
        inputs = dict(self.inputs)
        if any(not isinstance(key, str) or not key for key in inputs):
            raise ValueError("A scenario needs named, explicit provider inputs")
        common = {"require_accepted"}
        gas = common | {
            "fluid_factory", "orifice_factory", "jet_factory", "upstream", "ambient",
            "opening", "location", "evidence_id", "solver_options",
        }
        liquid = common | {
            "source", "native_pool_factory", "substance", "area_m2",
            "footprint_evidence_id", "ambient_pressure_pa", "atmosphere",
            "emission_thermo", "water_thermo", "runner", "premise_check",
            "width_context", "width_coupling", "x_max_m", "solver_options",
            "source_tolerances",
        }
        permitted = gas if selected is HydrogenReleaseFamily.HIGH_PRESSURE_GAS else liquid
        unknown = set(inputs) - permitted
        if unknown:
            raise ValueError(
                f"Scenario inputs are not accepted by the {selected.value} provider: "
                f"{', '.join(sorted(unknown))}"
            )
        if "require_accepted" in inputs:
            _require_acceptance_flag(inputs["require_accepted"])
        required = (
            {"fluid_factory", "orifice_factory", "jet_factory", "upstream", "ambient",
             "opening", "location", "evidence_id", "solver_options"}
            if selected is HydrogenReleaseFamily.HIGH_PRESSURE_GAS
            else {"source", "native_pool_factory", "substance", "area_m2",
                  "footprint_evidence_id", "ambient_pressure_pa", "atmosphere",
                  "emission_thermo", "water_thermo", "runner", "premise_check",
                  "width_context", "width_coupling", "x_max_m"}
        )
        missing = required - set(inputs)
        if missing:
            raise ValueError(
                f"Scenario is missing required {selected.value} inputs: "
                f"{', '.join(sorted(missing))}"
            )
        if any(value is None for value in inputs.values()):
            raise ValueError("Scenario provider inputs cannot be implicit None values")
        if "solver_options" in inputs and inputs["solver_options"] is not None:
            options = inputs["solver_options"]
            if not isinstance(options, Mapping):
                raise TypeError("Scenario solver_options must be a Python mapping or None")
            inputs["solver_options"] = MappingProxyType(dict(options))
        object.__setattr__(self, "family", selected)
        object.__setattr__(self, "inputs", MappingProxyType(inputs))
        object.__setattr__(self, "_solver_options_signature",
                           _configuration_snapshot(inputs.get("solver_options")))

    @property
    def provider_id(self) -> str:
        return preferred_dispersion_provider(self.family)

    def require_current(self):
        """Reject edits to nested solver-option containers after request construction."""
        if _configuration_snapshot(self.inputs.get("solver_options")) != self._solver_options_signature:
            raise ValueError("Dispersion solver options changed after scenario construction")
        return self

    def run(self):
        self.require_current()
        try:
            if self.family is HydrogenReleaseFamily.HIGH_PRESSURE_GAS:
                result = run_preferred_gas_dispersion(self.family, **self.inputs)
                evidence = (self.inputs["evidence_id"],)
            else:
                result = run_preferred_lh2_dispersion(self.family, **self.inputs)
                evidence = (
                    result.boundary.mass_source.evidence_id,
                    result.boundary.footprint_evidence_id,
                )
        except Exception as error:
            raise DispersionExecutionError(self.family, self.provider_id, error) from error
        accepted = getattr(result, "accepted", None)
        return DispersionExecution(
            self.family, self.provider_id, result, evidence, accepted,
            _issue_dispersion_execution_token(),
        )


def run_preferred_gas_dispersion(
    family: HydrogenReleaseFamily | str,
    *,
    fluid_factory: Callable,
    orifice_factory: Callable,
    jet_factory: Callable,
    upstream: ThermoState,
    ambient: ThermoState,
    opening: NozzleOpening,
    location: SourceLocation,
    evidence_id: str,
    solver_options: dict,
    require_accepted: bool = True,
):
    """Run the preferred gas provider while retaining the declared accident origin.

    HyRAM supports this checked high-pressure-gas entry point. An LH2-origin
    release needs its separate pool/source boundary and SLABx-LH2 interface;
    it cannot be represented by this nozzle call or rerouted automatically.
    """
    _require_acceptance_flag(require_accepted)
    selected_family = HydrogenReleaseFamily(family)
    provider = preferred_dispersion_provider(selected_family)
    if provider != "hyram":
        raise NotImplementedError(
            "SLABx-LH2 requires an explicit liquid source and pool boundary; no fallback is allowed"
        )
    from .adapters.hyram import run_hyram_gas_jet

    return run_hyram_gas_jet(
        fluid_factory=fluid_factory,
        orifice_factory=orifice_factory,
        jet_factory=jet_factory,
        upstream=upstream,
        ambient=ambient,
        opening=opening,
        location=location,
        evidence_id=evidence_id,
        solver_options=solver_options,
        require_accepted=require_accepted,
    )


def run_preferred_lh2_dispersion(
    family: HydrogenReleaseFamily | str,
    *,
    source,
    native_pool_factory: Callable,
    substance: Any,
    area_m2: float,
    footprint_evidence_id: str,
    ambient_pressure_pa: float,
    atmosphere: Any,
    emission_thermo: Any,
    water_thermo: Any,
    runner: Callable,
    premise_check: Callable,
    width_context: Callable,
    width_coupling: bool,
    x_max_m: float,
    solver_options: dict | None = None,
    source_tolerances: SLABLH2SourceTolerances | None = None,
    require_accepted: bool = True,
):
    """Run the preferred SLABx-LH2 vapor path from an explicit pool boundary.

    The interval source describes emitted vapor, not liquid release or pool
    formation. Callers must supply that declared boundary, footprint evidence,
    atmosphere, thermophysical objects and native engine functions themselves.
    """
    _require_acceptance_flag(require_accepted)
    selected_family = HydrogenReleaseFamily(family)
    provider = preferred_dispersion_provider(selected_family)
    if provider != "slabx-lh2":
        raise NotImplementedError(
            "HyRAM gas dispersion requires its gas-jet boundary; no fallback is allowed"
        )
    source.require_current()
    from .adapters.slabx_lh2 import run_slabx_lh2, steady_vapor_pool_boundary

    boundary = steady_vapor_pool_boundary(
        source,
        native_pool_factory=native_pool_factory,
        substance=substance,
        area_m2=area_m2,
        footprint_evidence_id=footprint_evidence_id,
        ambient_pressure_pa=ambient_pressure_pa,
    )
    return run_slabx_lh2(
        boundary=boundary,
        atmosphere=atmosphere,
        emission_thermo=emission_thermo,
        water_thermo=water_thermo,
        runner=runner,
        premise_check=premise_check,
        width_context=width_context,
        width_coupling=width_coupling,
        x_max_m=x_max_m,
        solver_options=solver_options,
        source_tolerances=source_tolerances,
        require_accepted=require_accepted,
    )


def run_preferred_lh2_quasi_steady_slices(
    family: HydrogenReleaseFamily | str,
    *,
    source: IntervalMassSource,
    native_pool_factory: Callable,
    substance: Any,
    area_m2: float | Sequence[float],
    footprint_evidence_id: str | Sequence[str],
    state_by_interval: Sequence[ThermoState | None] | None = None,
    state_projection_evidence_ids: Sequence[str | None] | None = None,
    ambient_pressure_pa: float,
    atmosphere: Any,
    emission_thermo: Any,
    water_thermo: Any,
    runner: Callable,
    premise_check: Callable,
    width_context: Callable,
    width_coupling: bool,
    x_max_m: float,
    solver_options: Mapping[str, Any] | None = None,
    source_tolerances: SLABLH2SourceTolerances | None = None,
    require_accepted: bool = True,
) -> SLABLH2SnapshotSeries:
    """Run independent steady SLABx-LH2 snapshots for each finite vapor bin.

    This explicitly selected diagnostic preserves each source interval but does
    not evolve or carry a plume between bins. It cannot be used as a transient
    dispersion result or as a substitute for a native transient source model.
    """
    _require_acceptance_flag(require_accepted)
    selected = HydrogenReleaseFamily(family)
    if preferred_dispersion_provider(selected) != "slabx-lh2":
        raise NotImplementedError(
            "Quasi-steady pool-source slices are only available on the explicit LH2-origin path"
        )
    source.require_current()
    from .adapters.slabx_lh2 import run_slabx_lh2_quasi_steady_slices

    return run_slabx_lh2_quasi_steady_slices(
        source=source,
        native_pool_factory=native_pool_factory,
        substance=substance,
        area_m2=area_m2,
        footprint_evidence_id=footprint_evidence_id,
        state_by_interval=state_by_interval,
        state_projection_evidence_ids=state_projection_evidence_ids,
        ambient_pressure_pa=ambient_pressure_pa,
        atmosphere=atmosphere,
        emission_thermo=emission_thermo,
        water_thermo=water_thermo,
        runner=runner,
        premise_check=premise_check,
        width_context=width_context,
        width_coupling=width_coupling,
        x_max_m=x_max_m,
        solver_options=solver_options,
        source_tolerances=source_tolerances,
        require_accepted=require_accepted,
    )
