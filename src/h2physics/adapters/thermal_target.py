"""Finite lumped target response to an explicitly supplied incident heat history.

This implemented-unverified composition does not predict a fire, view factor,
injury or failure.  It advances one uniform target temperature and audits every
thermal boundary.  A caller may bind the incident history to an existing pool
fire trace without copying the native fire/radiation implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import quad, solve_ivp

from ..core import Origin, finite, immutable_array
from .result_provenance import recorded_content_sha256

STATUS = "implemented_unverified"
STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8
_PENDING_TRACE_ISSUERS = set()


def _issue_trace_token():
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    return token


def _text(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare source, clock, frame, boundary and material evidence")


def _array(values, name):
    result = np.array(values, dtype=float, copy=True)
    if result.ndim != 1 or not np.all(np.isfinite(result)):
        raise ValueError(name + " must be a finite one-dimensional SI array")
    result = immutable_array(result, name="result")
    return result


def _target_capacity(target, temperature_k):
    temperature = finite(temperature_k, "target capacity evaluation temperature", positive=True)
    capacity = target.heat_capacity_j_k
    value = capacity(temperature) if callable(capacity) else capacity
    return finite(value, "target total heat capacity", positive=True)


@dataclass(frozen=True, slots=True)
class IncidentHeatHistory:
    """Piecewise-constant incident flux on finite half-open time intervals."""

    edges_s: np.ndarray
    incident_flux_w_m2: np.ndarray
    clock_id: str
    frame_id: str
    source_id: str
    boundary_id: str
    evidence_id: str
    origin: Origin
    source_owner: object

    def __post_init__(self):
        edges = _array(self.edges_s, "heat-history edges")
        flux = _array(self.incident_flux_w_m2, "incident heat flux")
        _text(self.clock_id, self.frame_id, self.source_id, self.boundary_id, self.evidence_id)
        if len(edges) < 2 or flux.shape != (len(edges) - 1,) or np.any(np.diff(edges) <= 0):
            raise ValueError("Incident flux needs one value per increasing finite interval")
        if np.any(flux < 0):
            raise ValueError("This boundary uses nonnegative heat incident on the target")
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED or self.source_owner is None:
            raise ValueError("Retain the resolved origin and actual source owner")
        object.__setattr__(self, "edges_s", edges)
        object.__setattr__(self, "incident_flux_w_m2", flux)
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class LumpedThermalTarget:
    area_m2: float
    heat_capacity_j_k: float | Callable[[float], float]
    initial_temperature_k: float
    absorptivity: float
    emissivity: float
    convective_coefficient_w_m2_k: float
    ambient_temperature_k: float
    radiant_surroundings_temperature_k: float
    minimum_temperature_k: float
    maximum_temperature_k: float
    material_evidence_id: str
    geometry_evidence_id: str
    convection_evidence_id: str
    radiation_evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in (
            "area_m2", "initial_temperature_k",
            "ambient_temperature_k", "radiant_surroundings_temperature_k",
            "minimum_temperature_k", "maximum_temperature_k",
        ):
            finite(getattr(self, name), name, positive=True)
        if callable(self.heat_capacity_j_k):
            for temperature in (self.minimum_temperature_k, self.initial_temperature_k,
                                self.maximum_temperature_k):
                _target_capacity(self, temperature)
        else:
            finite(self.heat_capacity_j_k, "target total heat capacity", positive=True)
        finite(self.convective_coefficient_w_m2_k, "convective coefficient")
        if self.convective_coefficient_w_m2_k < 0:
            raise ValueError("Convective coefficient cannot be negative")
        for name in ("absorptivity", "emissivity"):
            value = finite(getattr(self, name), name)
            if not 0 <= value <= 1:
                raise ValueError(name + " must lie in [0,1]")
        if not (
            self.minimum_temperature_k
            <= self.initial_temperature_k
            <= self.maximum_temperature_k
        ):
            raise ValueError("Initial target temperature lies outside its declared domain")
        if self.maximum_temperature_k <= self.minimum_temperature_k:
            raise ValueError("Target temperature domain must increase")
        _text(self.material_evidence_id, self.geometry_evidence_id,
              self.convection_evidence_id, self.radiation_evidence_id)
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Target parameters require a resolved origin")
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class ThermalTargetTolerances:
    energy_j: float
    relative_energy: float
    clock_s: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if self.relative_energy >= 1:
            raise ValueError("Relative energy tolerance must be below one")


@dataclass(frozen=True, slots=True)
class ThermalTargetTrace:
    history: IncidentHeatHistory
    target: LumpedThermalTarget
    tolerances: ThermalTargetTolerances
    time_s: np.ndarray
    temperature_k: np.ndarray
    absorbed_incident_j: np.ndarray
    convective_export_j: np.ndarray
    radiative_export_j: np.ndarray
    stored_energy_j: np.ndarray
    energy_residual_j: np.ndarray
    native_segments: tuple
    maximum_temperature_k: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    status: str = STATUS
    applicability: str = (
        "uniform-temperature target; supplied properties and external coefficients; "
        "no flame, occlusion, conduction gradient, phase change, damage or injury prediction"
    )
    _signature: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRACE_ISSUERS:
            raise TypeError("Create thermal-target traces through a completed native integration")
        _PENDING_TRACE_ISSUERS.remove(self._issuer_token)
        if (type(self.history) is not IncidentHeatHistory
                or type(self.target) is not LumpedThermalTarget
                or type(self.tolerances) is not ThermalTargetTolerances):
            raise TypeError("Retain the original typed incident history, target and tolerances")
        for name in (
            "time_s", "temperature_k", "absorbed_incident_j", "convective_export_j",
            "radiative_export_j", "stored_energy_j", "energy_residual_j",
        ):
            object.__setattr__(self, name, _array(getattr(self, name), name))
        object.__setattr__(self, "native_segments", tuple(self.native_segments))
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        return recorded_content_sha256((
            self.history, self.target, self.tolerances, self.time_s, self.temperature_k,
            self.absorbed_incident_j, self.convective_export_j, self.radiative_export_j,
            self.stored_energy_j, self.energy_residual_j, self.native_segments,
            self.maximum_temperature_k, self.status, self.applicability,
        ))

    def require_current(self):
        guard = getattr(self.history.source_owner, "require_current", None)
        if callable(guard):
            guard()
        if self._content() != self._signature:
            raise ValueError("Original incident history or retained target thermal ledger changed")
        return self


class ThermalTargetError(RuntimeError):
    def __init__(self, cause, *, history, target, native_segments=(), partial=None):
        super().__init__(str(cause))
        self.cause, self.history, self.target = cause, history, target
        self.native_segments, self.partial = tuple(native_segments), partial


def incident_history_from_pool_fire(trace, receptor_identifier: str, *, evidence_id: str):
    """Bind exact receptor intervals from an existing finite pool-fire trace."""
    from .pool_fire import PoolFireTrace

    if not isinstance(trace, PoolFireTrace):
        raise TypeError("Supply an actual PoolFireTrace")
    trace.require_current()
    _text(receptor_identifier, evidence_id)
    if not trace.steps:
        raise ValueError("Pool-fire trace contains no finite stages")
    edges = [trace.steps[0].stage.start_s]
    flux = []
    for step in trace.steps:
        if step.stage.start_s != edges[-1]:
            raise ValueError("Pool-fire stages must be contiguous on the retained clock")
        matches = [r for r in step.receptors if r.receptor.identifier == receptor_identifier]
        if len(matches) != 1:
            raise ValueError("Each stage must retain exactly one selected receptor")
        receptor = matches[0]
        active_end = receptor.active_end_s
        if (
            receptor.active_start_s != step.stage.start_s
            or not step.stage.start_s < active_end <= step.stage.end_s
        ):
            raise ValueError("Native receptor activity must remain inside its fire stage")
        flux.append(receptor.incident_flux_w_m2)
        edges.append(active_end)
        if active_end < step.stage.end_s:
            flux.append(0.0)
            edges.append(step.stage.end_s)
    result = IncidentHeatHistory(np.asarray(edges), np.asarray(flux),
        trace.ignition.clock_id, trace.seed.location.coordinate_frame_id,
        "pool-fire-receptor:" + receptor_identifier, "incident-radiation",
        evidence_id, Origin.PREDICTED, trace)
    trace.require_current()
    return result


def incident_history_from_exposure(history, *, evidence_id: str):
    """Adapt a left-held incident-radiation exposure to the lumped target boundary.

    This accepts only explicit W/m² incident radiant flux on finite intervals.
    It preserves the exact source clock, frame, source identity, interval values,
    validity and origin. It does not reinterpret absorbed flux, overpressure or
    linearly interpolated samples as a piecewise-constant boundary.
    """
    from .hyram_exposure import ExposureHistory

    if type(history) is not ExposureHistory:
        raise TypeError("Supply an admitted ExposureHistory object")
    _text(evidence_id)
    if history.quantity != "incident_radiant_flux" or history.unit != "W/m2":
        raise ValueError("Thermal target requires incident radiant flux in W/m2")
    if history.interpolation != "left_hold":
        raise ValueError("Thermal target requires an exact left-held interval history")
    if not np.all(history.valid):
        raise ValueError("Thermal target cannot consume invalid or missing exposure intervals")
    return IncidentHeatHistory(
        history.time_s, history.values, history.clock_id,
        history.receptor.frame_id, history.source_id,
        "incident-radiant-flux:left-hold:" + history.basis_id,
        evidence_id, history.origin, history,
    )


def run_thermal_target(history: IncidentHeatHistory, target: LumpedThermalTarget,
                       tolerances: ThermalTargetTolerances, *, maximum_step_s: float):
    """Advance the target and retain native SciPy segments plus an energy audit."""
    segments = []
    try:
        if not isinstance(history, IncidentHeatHistory) or not isinstance(
            target, LumpedThermalTarget
        ):
            raise TypeError("Use actual incident-history and target objects")
        if not isinstance(tolerances, ThermalTargetTolerances):
            raise TypeError("Use explicit audit tolerances")
        finite(maximum_step_s, "maximum native step", positive=True)
        source_guard = getattr(history.source_owner, "require_current", None)
        if callable(source_guard):
            source_guard()
        input_signature = recorded_content_sha256((history, target, tolerances))

        def guard_inputs():
            if callable(source_guard):
                source_guard()
            if recorded_content_sha256((history, target, tolerances)) != input_signature:
                raise ValueError("Incident history or thermal target configuration changed during integration")
        area = target.area_m2
        sigma = STEFAN_BOLTZMANN_W_M2_K4
        state = np.array([target.initial_temperature_k, 0.0, 0.0, 0.0])
        times, states = [], []
        for index, incident in enumerate(history.incident_flux_w_m2):
            start, end = history.edges_s[index:index + 2]

            def rates(_time, values):
                guard_inputs()
                temperature = values[0]
                if not target.minimum_temperature_k <= temperature <= target.maximum_temperature_k:
                    raise ValueError("Target response left the declared material temperature domain")
                capacity = _target_capacity(target, temperature)
                absorbed = area * target.absorptivity * incident
                convective = area * target.convective_coefficient_w_m2_k * (
                    temperature - target.ambient_temperature_k
                )
                radiative = area * target.emissivity * sigma * (
                    temperature**4 - target.radiant_surroundings_temperature_k**4
                )
                return ((absorbed - convective - radiative) / capacity,
                        absorbed, convective, radiative)

            native = solve_ivp(rates, (start, end), state, method="DOP853",
                               rtol=1e-9, atol=(1e-10, 1e-7, 1e-7, 1e-7),
                               max_step=maximum_step_s)
            segments.append(native)
            if not native.success or native.t[-1] != end or not np.all(np.isfinite(native.y)):
                raise ValueError("Native target integration did not complete its finite interval")
            if index:
                times.extend(native.t[1:])
                states.extend(native.y[:, 1:].T)
            else:
                times.extend(native.t)
                states.extend(native.y.T)
            state = native.y[:, -1]
        values = np.asarray(states)
        time = np.asarray(times)
        temperature = values[:, 0]
        def stored_energy(value):
            if not target.minimum_temperature_k <= value <= target.maximum_temperature_k:
                raise ValueError("Target response left the declared material temperature domain")
            if not callable(target.heat_capacity_j_k):
                return target.heat_capacity_j_k * (float(value) - target.initial_temperature_k)
            lower = min(target.initial_temperature_k, float(value))
            upper = max(target.initial_temperature_k, float(value))
            if lower == upper:
                return 0.0
            integral, error = quad(
                lambda state: _target_capacity(target, state),
                lower, upper,
                epsabs=max(tolerances.energy_j * 0.01, np.finfo(float).tiny),
                epsrel=max(tolerances.relative_energy * 0.1,
                          50.0 * np.finfo(float).eps),
            )
            if error > tolerances.energy_j * 0.01 + tolerances.relative_energy * 0.1 * abs(integral):
                raise ValueError("Target enthalpy integration did not meet its declared ledger tolerance")
            return integral if value >= target.initial_temperature_k else -integral

        stored = np.asarray([stored_energy(value) for value in temperature])
        residual = stored - values[:, 1] + values[:, 2] + values[:, 3]
        scale = max(float(np.max(np.abs(stored))), float(np.max(np.abs(values[:, 1:]))), 1.0)
        limit = tolerances.energy_j + tolerances.relative_energy * scale
        if np.max(np.abs(residual)) > limit:
            raise ValueError("Target heat-storage ledger exceeds its declared budget")
        if (
            np.min(temperature) < target.minimum_temperature_k
            or np.max(temperature) > target.maximum_temperature_k
        ):
            raise ValueError("Target response left the declared material temperature domain")
        if np.any(np.diff(time) <= 0) or abs(time[0] - history.edges_s[0]) > tolerances.clock_s \
                or abs(time[-1] - history.edges_s[-1]) > tolerances.clock_s:
            raise ValueError("Native response does not preserve the supplied heat-history clock")
        guard_inputs()
        return ThermalTargetTrace(history, target, tolerances, time, temperature,
            values[:, 1], values[:, 2], values[:, 3], stored, residual,
            tuple(segments), float(np.max(temperature)), _issue_trace_token()).require_current()
    except Exception as cause:
        raise ThermalTargetError(cause, history=history, target=target,
                                 native_segments=segments) from cause
