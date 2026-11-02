"""Finite O2 displacement by the existing native Cantera gas-volume owner.

This module assembles interval boundaries and audits native finite inventories.
It supplies no hypoxia response law, cold-injury model or cryogenic mixture EOS.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass, replace

import numpy as np

from ..core import immutable_array, Origin, PropertyBasis, ThermoState, finite, partial_pressure_pa
from ..release import SourceLocation
from ..sources import IntervalMassSource
from .cantera import MechanismBasis, ReactiveState
from .cantera_properties import CanteraFrozenGasProperties
from .cantera_volume import (
    CanteraOpenGasVolume,
    GasBoundaryRate,
    GasFeed,
    GasHeatBoundary,
    GasVent,
    GasVolumeIntegrationError,
    GasVolumeSnapshot,
    GasVolumeTrace,
    _phase_fingerprint,
)


def _text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare source, region, clock, frame and evidence identities")


def _plain(value):
    if is_dataclass(value):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


def _digest(value):
    return hashlib.sha256(
        json.dumps(_plain(value), sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _readonly(value, dtype=float):
    value = np.array(value, dtype=dtype, copy=True)
    value = immutable_array(value, name="value")
    return value


def _source_digest(source):
    if (
        type(source) is not IntervalMassSource
        or not isinstance(source.state, ThermoState)
        or type(source.state.basis) is not PropertyBasis
        or type(source.location) is not SourceLocation
    ):
        raise TypeError(
            "An actual finite source, ThermoState, PropertyBasis and location are required"
        )
    source.require_current()
    for value in (source.state.basis, source.state, source.location):
        type(value)(**{f.name: getattr(value, f.name) for f in fields(value) if f.init})
    IntervalMassSource(**{f.name: getattr(source, f.name) for f in fields(source) if f.init})
    if source.origin == Origin.UNRESOLVED:
        raise ValueError("Source origin cannot be unresolved")
    finite(source.total_mass_kg, "finite source total mass")
    finite(source.enthalpy_transfer_j, "finite source total enthalpy")
    return _digest(source)


def _provider_signature(provider):
    return _digest(
        (
            provider.basis,
            provider.mass_fractions,
            provider.composition_sha256,
            provider.phase_sha256,
            provider.hydrogen_partition_id,
            provider.version,
        )
    )


@dataclass(frozen=True, slots=True)
class OxygenRoomRegion:
    region_id: str
    receptor_id: str
    frame_id: str
    clock_id: str
    position_m: tuple[float, float, float]
    elevation_m: float
    volume_m3: float
    mixing_evidence_id: str
    single_gas_evidence_id: str
    prescribed_transfer_evidence_id: str
    origin: Origin

    def __post_init__(self):
        _text(
            self.region_id,
            self.receptor_id,
            self.frame_id,
            self.clock_id,
            self.mixing_evidence_id,
            self.single_gas_evidence_id,
            self.prescribed_transfer_evidence_id,
        )
        position = tuple(finite(v, "receptor position") for v in self.position_m)
        if len(position) != 3:
            raise ValueError("A receptor position needs three SI coordinates")
        object.__setattr__(self, "position_m", position)
        finite(self.elevation_m, "declared site elevation")
        finite(self.volume_m3, "finite room volume", positive=True)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Room assumptions need a resolved origin")


@dataclass(frozen=True, slots=True)
class OxygenFeedAdmission:
    """A real interval source with exactly the native formation/spin reference.

    The native properties object remains available. No enthalpy offset or cold
    source warming is inferred. Zero outside support needs explicit evidence;
    a window_end source cannot be extrapolated after its unobserved endpoint.
    """

    source: IntervalMassSource
    properties: CanteraFrozenGasProperties
    admission_evidence_id: str
    outside_support_evidence_id: str | None = None

    def __post_init__(self):
        _source_digest(self.source)
        if type(self.properties) is not CanteraFrozenGasProperties:
            raise TypeError("Use the actual frozen native property provider")
        _text(self.admission_evidence_id)
        if self.outside_support_evidence_id is not None:
            _text(self.outside_support_evidence_id)


@dataclass(frozen=True, slots=True)
class OxygenRoomSettings:
    maximum_time_step_s: float = 0.1
    relative_tolerance: float = 1e-10
    absolute_tolerance: float = 1e-14
    minimum_inventory_kg: float = 1e-9
    mass_absolute_budget_kg: float = 1e-9
    energy_absolute_budget_j: float = 0.001
    pressure_absolute_budget_pa: float = 1e-5
    relative_audit_budget: float = 1e-8

    def __post_init__(self):
        for f in fields(self):
            finite(getattr(self, f.name), f.name, positive=True)
        for name in ("relative_tolerance", "absolute_tolerance", "relative_audit_budget"):
            if getattr(self, name) >= 1:
                raise ValueError("Numerical tolerances must be below one")


@dataclass(frozen=True, slots=True)
class _OxygenResultBinding:
    signature: str
    traces: tuple
    snapshots: tuple
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_OXYGEN_BINDING_ISSUERS:
            raise ValueError("Oxygen-room bindings are issued only by a completed room run")
        _PENDING_OXYGEN_BINDING_ISSUERS.remove(self._issuer_token)


_PENDING_OXYGEN_BINDING_ISSUERS: set[object] = set()


def _issue_oxygen_result_binding(signature, traces, snapshots):
    token = object()
    _PENDING_OXYGEN_BINDING_ISSUERS.add(token)
    try:
        return _OxygenResultBinding(signature, tuple(traces), tuple(snapshots), token)
    except Exception:
        _PENDING_OXYGEN_BINDING_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class OxygenRoomResult:
    region: OxygenRoomRegion
    mechanism_basis: MechanismBasis
    settings: OxygenRoomSettings
    feeds: tuple[OxygenFeedAdmission, ...]
    exhausts: tuple[GasVent, ...]
    heat_boundaries: tuple[GasHeatBoundary, ...]
    native_traces: tuple
    admission_native_phases: tuple
    source_sha256: tuple[str, ...]
    source_definition_sha256: str
    requested_time_s: np.ndarray
    time_s: np.ndarray
    snapshots: tuple
    ledger_names: tuple[str, ...]
    boundary_integrals: np.ndarray
    species_names: tuple[str, ...]
    species_inventory_kg: np.ndarray
    oxygen_inventory_kg: np.ndarray
    oxygen_inventory_mol: np.ndarray
    wet_oxygen_mole_fraction: np.ndarray
    dry_oxygen_mole_fraction: np.ndarray
    dry_fraction_valid: np.ndarray
    oxygen_partial_pressure_pa: np.ndarray
    mass_residual_kg: np.ndarray
    species_residual_kg: np.ndarray
    energy_residual_j: np.ndarray
    pressure_identity_residual_pa: np.ndarray
    source_mass_residual_kg: np.ndarray
    source_enthalpy_residual_j: np.ndarray
    probability: None = None
    status: str = "finite-homogeneous-oxygen-inventory;no-human-response-law"
    _binding: _OxygenResultBinding | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, np.ndarray):
                object.__setattr__(self, f.name, _readonly(value, value.dtype))

    @property
    def native(self):
        return tuple(trace.native for trace in self.native_traces)

    def integral(self, name):
        return self.boundary_integrals[:, self.ledger_names.index(name)]


class OxygenRoomError(RuntimeError):
    """Retain completed traces, the actual failed native owner and original cause.

    The common native owner does not expose output prefixes within a failed run.
    completed_traces contains completed command partitions, never alleged hidden
    accepted steps. failure_time_s is the retained network time after failure.
    """

    def __init__(
        self,
        message,
        *,
        region,
        feeds,
        completed_traces=(),
        failed_native=None,
        completed_result=None,
        native_phases=(),
    ):
        super().__init__(message)
        self.region, self.feeds = region, feeds
        self.completed_traces = tuple(completed_traces)
        self.failed_native, self.completed_result = failed_native, completed_result
        self.native_phases = tuple(native_phases)
        self.failure_time_s = None
        self.native_state = None
        if failed_native is not None:
            self.failure_time_s = float(failed_native.network.time)
            self.native_state = failed_native.reactor.phase.state.copy()


class CanteraOxygenRoom:
    """Partition interval commands; delegate every physical step to the shared owner.

    MassFlowControllers are prescribed transfers, including fan/pump work upstream
    of the specified enthalpy boundary. No passive pressure-flow relation or
    pressure-independent ventilation efficiency is inferred. Supply a GasVent
    callback using the shared nozzle when a pressure-driven outlet is intended.
    """

    def __init__(self, phase_factory, mechanism_basis: MechanismBasis, region: OxygenRoomRegion):
        if not callable(phase_factory) or type(mechanism_basis) is not MechanismBasis:
            raise TypeError("Declare a native phase factory and MechanismBasis")
        if type(region) is not OxygenRoomRegion:
            raise TypeError("Declare the finite well-mixed region")
        self.phase_factory, self.mechanism_basis, self.region = (
            phase_factory,
            mechanism_basis,
            region,
        )

    def run(
        self,
        initial: ReactiveState,
        time_s,
        *,
        feeds=(),
        exhausts=(),
        heat_boundaries=(),
        event_times_s=(),
        settings=OxygenRoomSettings(),
    ):
        region, basis = self.region, self.mechanism_basis
        feeds, exhausts, heat_boundaries = tuple(feeds), tuple(exhausts), tuple(heat_boundaries)
        traces, result, failed_native = [], None, None
        factory_phases = []
        try:
            if type(settings) is not OxygenRoomSettings or type(initial) is not ReactiveState:
                raise TypeError("Use actual native reactive state and integration settings")
            for item in (settings, region, basis, initial):
                type(item)(**{f.name: getattr(item, f.name) for f in fields(item)})
            if (
                np.asarray(time_s).dtype.kind in "bc"
                or np.asarray(event_times_s).dtype.kind in "bc"
            ):
                raise ValueError("Clock coordinates must be real numeric seconds")
            times = np.array(time_s, dtype=float, copy=True)
            if (
                times.ndim != 1
                or len(times) < 2
                or np.any(~np.isfinite(times))
                or np.any(np.diff(times) <= 0)
            ):
                raise ValueError("Declare strictly increasing finite absolute output times")
            events = np.array(event_times_s, dtype=float)
            if (
                events.ndim != 1
                or np.any(~np.isfinite(events))
                or np.any((events <= times[0]) | (events >= times[-1]))
            ):
                raise ValueError("Declared event times must lie strictly inside the output window")
            region_digest, basis_digest = _digest(region), _digest(basis)
            phase = self.phase_factory()
            factory_phases.append(phase)
            import cantera as ct

            if (
                not isinstance(phase, ct.Solution)
                or phase.thermo_model != "ideal-gas"
                or phase.n_reactions != 0
                or phase.n_selected_species != phase.n_species
            ):
                raise ValueError("Use a full native frozen ideal gas with zero reactions")
            if "O2" not in phase.species_names or phase.species("O2").composition != {"O": 2.0}:
                raise ValueError("The native phase must contain neutral molecular O2")
            if phase.species("O2").charge != 0:
                raise ValueError("The O2 species must be neutral")
            if "H2O" in phase.species_names and phase.species("H2O").composition != {
                "H": 2.0,
                "O": 1.0,
            }:
                raise ValueError("Dry fractions require actual molecular vapor H2O")
            definition = _phase_fingerprint(phase)
            source_hashes, providers, native_states = [], [], []
            identifiers = []
            breaks = {float(times[0]), float(times[-1]), *map(float, events)}
            for admission in feeds:
                if type(admission) is not OxygenFeedAdmission:
                    raise TypeError("Use an actual source admission object")
                source, provider = admission.source, admission.properties
                source_hashes.append(_source_digest(source))
                _text(admission.admission_evidence_id)
                if (
                    source.location.clock_id != region.clock_id
                    or source.location.coordinate_frame_id != region.frame_id
                ):
                    raise ValueError("Source and receptor clock/frame identities differ")
                if source.edges_s[0] > times[0] or source.edges_s[-1] < times[-1]:
                    _text(admission.outside_support_evidence_id)
                if source.edges_s[-1] < times[-1] and source.end_reason == "window_end":
                    raise ValueError("An unobserved window_end tail cannot become zero flow")
                if (
                    provider.mechanism_basis != basis
                    or _phase_fingerprint(provider.native_phase) != definition
                ):
                    raise ValueError("Source provider and native volume thermochemistry differ")
                canonical = CanteraFrozenGasProperties(
                    provider.native_phase, basis, provider.mass_fractions
                )
                if _provider_signature(provider) != _provider_signature(canonical):
                    raise ValueError("Source provider reference/composition identity was relabeled")
                expected = provider.state_pt(source.state.pressure_pa, source.state.temperature_k)
                declared_y = np.array(
                    [
                        provider.mass_fractions.get(k, 0.0)
                        for k in provider.native_phase.species_names
                    ]
                )
                if not np.array_equal(provider.native_phase.Y, declared_y):
                    raise ValueError("Source provider composition and native caloric state differ")
                source.state.basis.require_compatible(expected.basis)
                if source.state.phase != "gas" or source.state.vapor_mass_fraction != 1.0:
                    raise ValueError("Only an admitted single gas source is supported")
                for name in (
                    "pressure_pa",
                    "temperature_k",
                    "density_kg_m3",
                    "enthalpy_j_kg",
                    "internal_energy_j_kg",
                    "entropy_j_kg_k",
                ):
                    if not math.isclose(
                        getattr(source.state, name),
                        getattr(expected, name),
                        rel_tol=5e-12,
                        abs_tol=1e-7,
                    ):
                        raise ValueError(f"Source caloric/state mismatch: {name}")
                native_states.append(
                    ReactiveState(
                        expected.temperature_k,
                        expected.pressure_pa,
                        dict(
                            zip(
                                provider.native_phase.species_names,
                                provider.native_phase.X,
                                strict=True,
                            )
                        ),
                    )
                )
                providers.append(
                    (provider, provider.native_phase, provider.basis, _provider_signature(provider))
                )
                identifiers.append(source.location.source_id)
                breaks.update(float(t) for t in source.edges_s if times[0] < t < times[-1])
            if len(set(identifiers)) != len(identifiers):
                raise ValueError("Finite source IDs must be unique")
            for vent in exhausts:
                if type(vent) is not GasVent:
                    raise TypeError("Reuse an actual shared GasVent")
                self._require_support(vent.rate, times)
            for heat in heat_boundaries:
                if type(heat) is not GasHeatBoundary:
                    raise TypeError("Reuse an actual shared native wall boundary")
                self._require_support(heat, times)

            def guard():
                if any(_phase_fingerprint(p) != definition for p in factory_phases):
                    raise ValueError("A retained native factory phase definition changed")
                if (
                    _digest(self.region) != region_digest
                    or _digest(self.mechanism_basis) != basis_digest
                ):
                    raise ValueError("Room identity or mechanism basis changed during integration")
                for admission, sha, (provider, native, reference, signature) in zip(
                    feeds, source_hashes, providers, strict=True
                ):
                    if (
                        _source_digest(admission.source) != sha
                        or admission.properties is not provider
                        or provider.native_phase is not native
                        or provider.basis != reference
                        or _provider_signature(provider) != signature
                        or provider.mechanism_basis != basis
                        or _phase_fingerprint(native) != definition
                    ):
                        raise ValueError(
                            "Source contents, native provider or caloric definition changed"
                        )

            ordered = sorted(breaks)
            current = initial

            def independent_factory():
                candidate = self.phase_factory()
                if any(candidate is previous for previous in factory_phases) or any(
                    candidate is p[1] for p in providers
                ):
                    raise ValueError(
                        "Native phase factory must be fresh across all room partitions and sources"
                    )
                factory_phases.append(candidate)
                return candidate

            for left, right in zip(ordered[:-1], ordered[1:], strict=True):
                guard()

                # A frozen command's numerical extension supports native trial
                # times after a partition endpoint. Only [left,right] is physical.
                def stage_time(t, a=left, b=right):
                    return max(a, min(float(t), math.nextafter(b, a)))

                stage_feeds = []
                for admission, state in zip(feeds, native_states, strict=True):
                    source = admission.source
                    midpoint = left + (right - left) / 2
                    if source.edges_s[0] <= midpoint < source.edges_s[-1]:
                        rate = source.rate_at(midpoint, clock_id=region.clock_id)
                    else:
                        rate = 0.0
                    boundary = GasBoundaryRate(
                        "feed:" + source.location.source_id,
                        region.clock_id,
                        left,
                        right + settings.maximum_time_step_s,
                        lambda t, p, value=rate: value,
                        source.origin,
                        source.evidence_id,
                    )
                    stage_feeds.append(GasFeed(boundary, state))
                stage_vents = tuple(
                    GasVent(
                        GasBoundaryRate(
                            v.rate.boundary_id,
                            region.clock_id,
                            left,
                            right + settings.maximum_time_step_s,
                            lambda t, p, original=v.rate, clock=stage_time: original.value(
                                clock(t), p
                            ),
                            v.rate.origin,
                            v.rate.source_id,
                        ),
                        v.downstream_state,
                    )
                    for v in exhausts
                )
                stage_heat = tuple(
                    replace(
                        h,
                        support_start_s=left,
                        support_end_s=right + settings.maximum_time_step_s,
                        heat_flux_w_m2=lambda t, original=h, clock=stage_time: original.value(
                            clock(t)
                        ),
                    )
                    for h in heat_boundaries
                )
                local_times = np.unique(np.r_[left, times[(times > left) & (times < right)], right])
                owner = CanteraOpenGasVolume(independent_factory, basis)
                trace = owner.run(
                    current,
                    local_times,
                    volume_m3=region.volume_m3,
                    clock_id=region.clock_id,
                    feeds=tuple(stage_feeds),
                    vents=stage_vents,
                    heat_boundaries=stage_heat,
                    maximum_time_step_s=settings.maximum_time_step_s,
                    relative_tolerance=settings.relative_tolerance,
                    absolute_tolerance=settings.absolute_tolerance,
                    minimum_inventory_kg=settings.minimum_inventory_kg,
                )
                traces.append(trace)
                failed_native = trace.native
                if trace.source_phase_fingerprint != definition:
                    raise ValueError("A partition factory changed the native source definition")
                guard()
                last = trace.snapshots[-1]
                current = ReactiveState(last.temperature_k, last.pressure_pa, last.mole_fractions)
            result = self._assemble(
                region,
                basis,
                settings,
                feeds,
                exhausts,
                heat_boundaries,
                tuple(traces),
                tuple(p[1] for p in providers),
                tuple(source_hashes),
                definition,
                times,
                phase,
            )
            guard()
            self._audit(result)
            return result
        except Exception as cause:
            if isinstance(cause, GasVolumeIntegrationError):
                failed_native = cause.native
            raise OxygenRoomError(
                f"Finite native oxygen-room evaluation failed: {cause}",
                region=region,
                feeds=feeds,
                completed_traces=traces,
                failed_native=failed_native,
                completed_result=result,
                native_phases=factory_phases,
            ) from cause

    def _require_support(self, boundary, times):
        if (
            boundary.clock_id != self.region.clock_id
            or boundary.support_start_s > times[0]
            or boundary.support_end_s < times[-1]
        ):
            raise ValueError("Boundary clock/support must cover the physical output window")

    @staticmethod
    def _assemble(
        region,
        basis,
        settings,
        feeds,
        exhausts,
        heat,
        traces,
        admission_phases,
        source_hashes,
        definition,
        requested,
        phase,
    ):
        snapshots = list(traces[0].snapshots)
        integrals = list(traces[0].boundary_integrals)
        for trace in traces[1:]:
            if trace.ledger_names != traces[0].ledger_names:
                raise ValueError("Partition ledger identities changed")
            offset = integrals[-1].copy()
            integrals.extend(trace.boundary_integrals[1:] + offset)
            snapshots.extend(trace.snapshots[1:])
        times = np.array([s.time_s for s in snapshots])
        ledger = np.array(integrals)
        names = traces[0].species_names
        mass = np.array([s.mass_kg for s in snapshots])
        species = np.array([[s.mass_kg * s.mass_fractions[k] for k in names] for s in snapshots])
        energy = np.array([s.internal_energy_j for s in snapshots])
        nf, nv = len(feeds), len(exhausts)
        mass_res = mass - mass[0] - ledger[:, :nf].sum(axis=1) + ledger[:, nf : nf + nv].sum(axis=1)
        species_res = species - species[0] - ledger[:, nf + nv : nf + nv + len(names)]
        energy_res = energy - energy[0] - ledger[:, -3] + ledger[:, -2] - ledger[:, -1]
        wet = np.array([s.mole_fractions["O2"] for s in snapshots])
        water = np.array([s.mole_fractions.get("H2O", 0.0) for s in snapshots])
        valid = water < 1.0
        dry = np.full(len(wet), np.nan)
        dry[valid] = wet[valid] / (1.0 - water[valid])
        pressure = np.array([s.pressure_pa for s in snapshots])
        oxygen = species[:, names.index("O2")]
        weights = np.asarray(phase.molecular_weights)
        temperature = np.array([s.temperature_k for s in snapshots])
        import cantera as ct

        pressure_res = (
            pressure
            - (species / weights).sum(axis=1) * ct.gas_constant * temperature / region.volume_m3
        )
        source_mass, source_heat = [], []
        for i, admission in enumerate(feeds):
            source = admission.source
            expected = np.array(
                [
                    source.mass_between(
                        max(times[0], source.edges_s[0]),
                        min(t, source.edges_s[-1]),
                        clock_id=region.clock_id,
                    )
                    if min(t, source.edges_s[-1]) > max(times[0], source.edges_s[0])
                    else 0.0
                    for t in times
                ]
            )
            source_mass.append(ledger[:, i] - expected)
            source_heat.append(expected * source.state.enthalpy_j_kg)
        source_res = np.array(source_mass).T if feeds else np.empty((len(times), 0))
        enthalpy_res = ledger[:, -3] - np.array(source_heat).sum(axis=0) if feeds else ledger[:, -3]
        result = OxygenRoomResult(
            region,
            basis,
            settings,
            feeds,
            exhausts,
            heat,
            traces,
            admission_phases,
            source_hashes,
            definition,
            requested,
            times,
            tuple(snapshots),
            traces[0].ledger_names,
            ledger,
            names,
            species,
            oxygen,
            oxygen / (weights[names.index("O2")] / 1000.0),
            wet,
            dry,
            valid,
            partial_pressure_pa(pressure, wet),
            mass_res,
            species_res,
            energy_res,
            pressure_res,
            source_res,
            enthalpy_res,
        )
        # Only this completed native assembly creates the correspondence record.
        # Dataclass construction/replacement never refreshes it automatically.
        object.__setattr__(
            result,
            "_binding",
            _issue_oxygen_result_binding(_result_signature(result), traces, tuple(snapshots)),
        )
        return result

    @staticmethod
    def _audit(result):
        settings = result.settings
        mass_scale = max(
            float(np.max(result.species_inventory_kg)),
            float(np.max(np.abs(result.boundary_integrals[:, :-3]))),
            1e-30,
        )
        energy_scale = max(
            max(abs(s.internal_energy_j) for s in result.snapshots),
            float(np.max(np.abs(result.boundary_integrals[:, -3:]))),
            1e-30,
        )
        pressure_scale = max(s.pressure_pa for s in result.snapshots)
        for name, residual, absolute, scale in (
            ("mass", result.mass_residual_kg, settings.mass_absolute_budget_kg, mass_scale),
            ("species", result.species_residual_kg, settings.mass_absolute_budget_kg, mass_scale),
            (
                "source interval mass",
                result.source_mass_residual_kg,
                settings.mass_absolute_budget_kg,
                mass_scale,
            ),
            ("energy", result.energy_residual_j, settings.energy_absolute_budget_j, energy_scale),
            (
                "source caloric",
                result.source_enthalpy_residual_j,
                settings.energy_absolute_budget_j,
                energy_scale,
            ),
            (
                "pressure identity",
                result.pressure_identity_residual_pa,
                settings.pressure_absolute_budget_pa,
                pressure_scale,
            ),
        ):
            budget = absolute + settings.relative_audit_budget * scale
            if (
                not math.isfinite(budget)
                or np.any(~np.isfinite(residual))
                or np.any(np.abs(residual) > budget)
            ):
                raise ValueError(f"Native finite-room {name} conservation/admission gate failed")
        for snapshot in result.snapshots:
            for mapping in (snapshot.mole_fractions, snapshot.mass_fractions):
                if (
                    any(not math.isfinite(v) or not 0 <= v <= 1 for v in mapping.values())
                    or abs(math.fsum(mapping.values()) - 1) > 1e-10
                ):
                    raise ValueError("Accepted gas composition is outside the physical simplex")


@dataclass(frozen=True, slots=True)
class OxygenCriterion:
    criterion_id: str
    quantity: str
    threshold: float
    comparator: str
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_elevation_m: float
    maximum_elevation_m: float
    authority_reference: str
    applicability_evidence_id: str

    def __post_init__(self):
        _text(self.criterion_id, self.authority_reference, self.applicability_evidence_id)
        if self.quantity not in {
            "wet_oxygen_mole_fraction",
            "dry_oxygen_mole_fraction",
            "oxygen_partial_pressure_pa",
        }:
            raise ValueError("Select an explicit oxygen quantity and wet/dry basis")
        if self.comparator not in {"below", "at_or_below"}:
            raise ValueError("Oxygen-deficit criteria require an explicit low-side comparator")
        finite(self.threshold, "criterion threshold", positive=True)
        if "mole_fraction" in self.quantity and self.threshold > 1:
            raise ValueError("Mole-fraction thresholds use fraction, not percent or mass fraction")
        for name in ("minimum_pressure_pa", "maximum_pressure_pa"):
            finite(getattr(self, name), name, positive=True)
        finite(self.minimum_elevation_m, "criterion minimum elevation")
        finite(self.maximum_elevation_m, "criterion maximum elevation")
        if (
            self.minimum_pressure_pa >= self.maximum_pressure_pa
            or self.minimum_elevation_m > self.maximum_elevation_m
        ):
            raise ValueError("Criterion applicability bounds must increase")


@dataclass(frozen=True, slots=True)
class OxygenCrossing:
    lower_time_s: float
    upper_time_s: float
    left_value: float
    right_value: float
    linearly_estimated_time_s: float
    enters_deficit: bool


@dataclass(frozen=True, slots=True)
class OxygenCriterionResult:
    room_result: OxygenRoomResult
    criterion: OxygenCriterion
    deficient_samples: np.ndarray
    sample_minimum: float
    reconstructed_deficit_duration_s: float
    crossings: tuple[OxygenCrossing, ...]
    interpolation: str
    probability: None = None
    sampled_window_s: tuple[float, float] | None = None
    sampled_times_s: np.ndarray | None = None
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_OXYGEN_CRITERION_ISSUERS:
            raise ValueError("Oxygen criterion results are issued only by the screening evaluator")
        _PENDING_OXYGEN_CRITERION_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "deficient_samples", _readonly(self.deficient_samples, bool))
        if self.sampled_times_s is None:
            raise ValueError("Retain the exact output sample times covered by this criterion screen")
        object.__setattr__(self, "sampled_times_s", _readonly(self.sampled_times_s))
        object.__setattr__(self, "crossings", tuple(self.crossings))
        if type(self.room_result) is not OxygenRoomResult or type(self.criterion) is not OxygenCriterion:
            raise TypeError("An oxygen criterion result must retain its exact room result and criterion")
        if self.probability is not None:
            raise ValueError("No probability or human-response law is implemented by this screen")
        if self.interpolation != "linear_between_native_output_samples":
            raise ValueError("An oxygen criterion result must retain its explicit sample reconstruction")
        if self.sampled_window_s is not None:
            window = tuple(finite(value, "criterion sample-window time")
                           for value in self.sampled_window_s)
            if (len(window) != 2 or window[1] <= window[0]
                    or window[0] < self.room_result.time_s[0]
                    or window[1] > self.room_result.time_s[-1]
                    or not np.any(self.room_result.time_s == window[0])
                    or not np.any(self.room_result.time_s == window[1])):
                raise ValueError("Criterion windows must use ordered exact output samples inside the run")
            object.__setattr__(self, "sampled_window_s", window)
        if (self.sampled_times_s.ndim != 1 or len(self.sampled_times_s) < 2
                or np.any(~np.isfinite(self.sampled_times_s))
                or np.any(np.diff(self.sampled_times_s) <= 0)):
            raise ValueError("Criterion sample times must be finite and increasing")
        expected_window = (float(self.sampled_times_s[0]), float(self.sampled_times_s[-1]))
        if self.sampled_window_s != expected_window:
            raise ValueError("Criterion sample times must reproduce its declared exact window")
        start, stop = _resolve_exact_output_window(self.room_result.time_s, expected_window)
        expected_times = self.room_result.time_s[start:stop + 1]
        if not np.array_equal(self.sampled_times_s, expected_times):
            raise ValueError("Criterion times must be original room output samples")
        values = getattr(self.room_result, self.criterion.quantity)[start:stop + 1]
        threshold = self.criterion.threshold
        expected_flags = values < threshold if self.criterion.comparator == "below" else values <= threshold
        if (not np.array_equal(self.deficient_samples, expected_flags)
                or self.sample_minimum != float(np.min(values))):
            raise ValueError("Criterion flags and minimum must reproduce the retained room samples")
        object.__setattr__(self, "_seal", self._current_signature())

    def _current_signature(self):
        return _digest((
            id(self.room_result), _result_signature(self.room_result),
            id(self.criterion), _plain(self.criterion),
            _array_signature(self.deficient_samples), self.sample_minimum,
            self.reconstructed_deficit_duration_s, self.crossings,
            self.interpolation, self.probability, self.sampled_window_s,
            _array_signature(self.sampled_times_s),
        ))

    def require_current(self):
        verify_oxygen_room_result(self.room_result)
        OxygenCriterion(**{f.name: getattr(self.criterion, f.name) for f in fields(self.criterion)})
        if self._current_signature() != self._seal:
            raise ValueError("Oxygen criterion result changed after evaluator issuance")
        return self


_PENDING_OXYGEN_CRITERION_ISSUERS: set[object] = set()


def _array_signature(value):
    value = np.asarray(value)
    return (value.dtype.str, value.shape, hashlib.sha256(value.tobytes(order="C")).hexdigest())


def _result_signature(result):
    """In-process correspondence, including meaningful native snapshot values.

    Native object identities deliberately do not form a portable serialized or
    cryptographic authenticity claim. Undefined dry fractions keep their raw NaN
    bytes in the array signature, instead of being converted to finite values.
    """
    payload = {}
    for f in fields(result):
        name, value = f.name, getattr(result, f.name)
        if name == "_binding":
            continue
        if isinstance(value, np.ndarray):
            payload[name] = _array_signature(value)
        elif name == "native_traces":
            payload[name] = [
                (
                    id(t),
                    id(t.native),
                    id(t.native.reactor),
                    id(t.native.network),
                    t.clock_id,
                    t.mechanism_basis,
                    t.phase_fingerprint,
                    t.source_phase_fingerprint,
                    t.species_names,
                    t.ledger_names,
                    _array_signature(t.time_s),
                    _array_signature(t.boundary_integrals),
                    [(id(s), _plain(s)) for s in t.snapshots],
                )
                for t in value
            ]
        elif name == "snapshots":
            payload[name] = [(id(s), _plain(s)) for s in value]
        elif name == "feeds":
            payload[name] = [
                (
                    id(a),
                    _source_digest(a.source),
                    _provider_signature(a.properties),
                    id(a.properties.native_phase),
                    a.admission_evidence_id,
                    a.outside_support_evidence_id,
                )
                for a in value
            ]
        elif name in {"exhausts", "heat_boundaries", "admission_native_phases"}:
            payload[name] = [id(v) for v in value]
        else:
            payload[name] = value
    return _digest(payload)


class OxygenResultVerificationError(ValueError):
    """A cached record no longer corresponds to its retained actual native trace."""

    def __init__(self, message, supplied):
        super().__init__(message)
        self.supplied = supplied
        self.native_traces = getattr(supplied, "native_traces", ())


def _resolve_exact_output_window(output_times_s, sampled_window_s):
    """Return inclusive sample indices; never interpolate a requested window edge."""
    times = np.asarray(output_times_s, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or np.any(~np.isfinite(times))
            or np.any(np.diff(times) <= 0)):
        raise ValueError("Oxygen output times must be finite, one-dimensional and increasing")
    if sampled_window_s is None:
        return 0, len(times) - 1
    window = tuple(finite(value, "criterion sample-window time")
                   for value in sampled_window_s)
    if len(window) != 2 or window[1] <= window[0]:
        raise ValueError("A sampled window requires increasing start and end times")
    start_matches = np.flatnonzero(times == window[0])
    stop_matches = np.flatnonzero(times == window[1])
    if (len(start_matches) != 1 or len(stop_matches) != 1
            or start_matches[0] >= stop_matches[0]):
        raise ValueError("Window endpoints must be distinct exact output samples in this run")
    return int(start_matches[0]), int(stop_matches[0])


def verify_oxygen_room_result(result: OxygenRoomResult) -> OxygenRoomResult:
    """Return the original verified object without repeating physical integration.

    The owner-built binding survives dataclasses.replace unchanged. Verification
    also compares the exposed histories to actual retained snapshot objects;
    ordinary construction of another result does not create native provenance.
    """
    try:
        if (
            type(result) is not OxygenRoomResult
            or type(result._binding) is not _OxygenResultBinding
        ):
            raise TypeError("Use a completed owner-built native oxygen-room result")
        for item, expected_type in (
            (result.region, OxygenRoomRegion),
            (result.settings, OxygenRoomSettings),
            (result.mechanism_basis, MechanismBasis),
        ):
            if type(item) is not expected_type:
                raise TypeError("Result context types changed")
            expected_type(**{f.name: getattr(item, f.name) for f in fields(item)})
        binding = result._binding
        if (
            len(result.native_traces) != len(binding.traces)
            or not binding.traces
            or any(a is not b for a, b in zip(result.native_traces, binding.traces, strict=True))
        ):
            raise ValueError("Actual native trace identities changed")
        actual = []
        for i, trace in enumerate(binding.traces):
            if type(trace) is not GasVolumeTrace:
                raise TypeError("Retain actual common native GasVolumeTrace objects")
            if (
                trace.clock_id != result.region.clock_id
                or trace.mechanism_basis != result.mechanism_basis
                or trace.species_names != result.species_names
                or trace.source_phase_fingerprint != result.source_definition_sha256
                or _phase_fingerprint(trace.native.reactor.phase) != trace.phase_fingerprint
            ):
                raise ValueError("Native clock, phase, species or mechanism correspondence changed")
            if len(trace.snapshots) != len(trace.time_s) or not np.array_equal(
                trace.time_s, [s.time_s for s in trace.snapshots]
            ):
                raise ValueError("Actual native trace clock/snapshot correspondence changed")
            actual.extend(trace.snapshots if i == 0 else trace.snapshots[1:])
        if (
            len(actual) != len(result.snapshots)
            or len(actual) != len(binding.snapshots)
            or any(type(s) is not GasVolumeSnapshot for s in actual)
            or any(
                s is not a or s is not b
                for s, a, b in zip(result.snapshots, actual, binding.snapshots, strict=True)
            )
        ):
            raise ValueError("Snapshots are not the original flattened native output prefix")
        if _result_signature(result) != binding.signature:
            raise ValueError(
                "Computed summary, clock or context differs from original native assembly"
            )
        wet = np.array([s.mole_fractions["O2"] for s in actual])
        water = np.array([s.mole_fractions.get("H2O", 0.0) for s in actual])
        valid = water < 1.0
        dry = np.full(len(actual), np.nan)
        dry[valid] = wet[valid] / (1.0 - water[valid])
        oxygen = np.array([s.mass_kg * s.mass_fractions["O2"] for s in actual])
        pressure = np.array([s.pressure_pa for s in actual])
        expected = {
            "time_s": np.array([s.time_s for s in actual]),
            "wet_oxygen_mole_fraction": wet,
            "dry_oxygen_mole_fraction": dry,
            "dry_fraction_valid": valid,
            "oxygen_partial_pressure_pa": wet * pressure,
            "oxygen_inventory_kg": oxygen,
        }
        for name, values in expected.items():
            if not np.array_equal(getattr(result, name), values, equal_nan=True):
                raise ValueError(f"{name} is not derived from retained actual native snapshots")
        if (
            result.probability is not None
            or result.status != "finite-homogeneous-oxygen-inventory;no-human-response-law"
        ):
            raise ValueError("Result status or unsupported harm probability changed")
        CanteraOxygenRoom._audit(result)
        return result
    except Exception as cause:
        raise OxygenResultVerificationError(
            f"Native oxygen-result verification failed: {cause}", result
        ) from cause


def evaluate_oxygen_criterion(
    result: OxygenRoomResult, criterion: OxygenCriterion, *, interpolation: str,
    sampled_window_s: tuple[float, float] | None = None,
) -> OxygenCriterionResult:
    """Report a declared low-O2 screen on the linear interpolant of output samples.

    Duration and crossing estimates belong to this explicit reconstruction, not
    native event roots, hidden accepted steps or a physiological exposure law.
    """
    if type(result) is not OxygenRoomResult or type(criterion) is not OxygenCriterion:
        raise TypeError("Use actual finite-room result and criterion objects")
    OxygenCriterion(**{f.name: getattr(criterion, f.name) for f in fields(criterion)})
    verify_oxygen_room_result(result)
    if interpolation != "linear_between_native_output_samples":
        raise ValueError("Declare the sampled linear reconstruction explicitly")
    if (
        not criterion.minimum_elevation_m
        <= result.region.elevation_m
        <= criterion.maximum_elevation_m
    ):
        raise ValueError("Site elevation is outside the chosen criterion's declared applicability")
    start, stop = _resolve_exact_output_window(result.time_s, sampled_window_s)
    pressure = np.array([s.pressure_pa for s in result.snapshots[start:stop + 1]])
    if np.any(
        (pressure < criterion.minimum_pressure_pa) | (pressure > criterion.maximum_pressure_pa)
    ):
        raise ValueError("Absolute gas pressure is outside the chosen criterion's applicability")
    all_values = getattr(result, criterion.quantity)
    if np.any(~np.isfinite(all_values)):
        raise ValueError("The chosen oxygen quantity is undefined at an output sample")
    times = result.time_s[start:stop + 1]
    values = all_values[start:stop + 1]
    threshold = criterion.threshold
    deficient = values < threshold if criterion.comparator == "below" else values <= threshold
    durations, crossings = [], []
    for i, (left, right) in enumerate(zip(times[:-1], times[1:], strict=True)):
        a, b = values[i : i + 2]
        if a == b:
            duration = right - left if deficient[i] else 0.0
        elif max(a, b) <= threshold:
            duration = right - left
        elif min(a, b) >= threshold:
            duration = 0.0
        else:
            fraction = (threshold - a) / (b - a)
            duration = (right - left) * (fraction if a < b else 1 - fraction)
        durations.append(float(duration))
        if deficient[i] != deficient[i + 1]:
            when = left + (right - left) * (threshold - a) / (b - a)
            crossings.append(
                OxygenCrossing(
                    float(left),
                    float(right),
                    float(a),
                    float(b),
                    float(when),
                    bool(deficient[i + 1]),
                )
            )
    duration = math.fsum(durations)
    if not math.isfinite(duration):
        raise ValueError("Reconstructed duration overflowed")
    token = object()
    _PENDING_OXYGEN_CRITERION_ISSUERS.add(token)
    try:
        evaluated = OxygenCriterionResult(
            result,
            criterion,
            deficient,
            float(np.min(values)),
            duration,
            tuple(crossings),
            interpolation,
            _issuer_token=token,
            sampled_window_s=(float(times[0]), float(times[-1])),
            sampled_times_s=times,
        )
        verify_oxygen_room_result(result)
        return evaluated.require_current()
    except Exception:
        _PENDING_OXYGEN_CRITERION_ISSUERS.discard(token)
        raise
