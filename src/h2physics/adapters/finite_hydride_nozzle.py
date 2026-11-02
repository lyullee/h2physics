"""Handoff from finite hydride-bed discharge states to the shared nozzle history."""

from dataclasses import dataclass, field
import hashlib

import numpy as np

from ..core import Origin
from ..release import HomogeneousIsentropicNozzle, NozzleOpening, SourceHistory, SourceLocation

_PENDING_HYDROGEN_SOURCES: set[object] = set()


def _trace_digest(trace):
    digest = hashlib.sha256(repr((id(trace), trace.clock_id, trace.termination,
        trace.event_time_s, trace.gas_port_boundary, trace.energy_reference,
        trace.gas_thermodynamics.basis, id(trace.native_solution),
        tuple((row.time_s, row.fraction, row.solid_temperature_k, row.gas,
               row.total_hydrogen_mass_kg) for row in trace.snapshots))).encode())
    for value in (trace.time_s, trace.integrated_external_gas_mass_kg,
                  trace.integrated_external_gas_enthalpy_j):
        digest.update(np.ascontiguousarray(value).tobytes())
    native = trace.native_solution
    for name in ("t", "y"):
        value = np.asarray(getattr(native, name))
        digest.update(value.dtype.str.encode())
        digest.update(repr(value.shape).encode())
        digest.update(np.ascontiguousarray(value).tobytes())
    digest.update(repr((native.success, native.message)).encode())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class HydrideNozzleSource:
    hydride_trace: object
    nozzle: HomogeneousIsentropicNozzle
    opening: NozzleOpening
    source_history: SourceHistory
    back_pressure_pa: float
    evidence_id: str
    source_origin: Origin
    port_mass_quadrature: str
    relative_mass_tolerance: float
    absolute_mass_tolerance_kg: float
    mass_closure_evidence_id: str
    port_interval_mass_kg: tuple[float, ...]
    nozzle_interval_mass_kg: tuple[float, ...]
    interval_mass_residual_kg: tuple[float, ...]
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _trace_seal: str = field(default="", init=False, repr=False, compare=False)
    _history_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_HYDROGEN_SOURCES:
            raise TypeError("Create hydride nozzle histories through the typed handoff")
        _PENDING_HYDROGEN_SOURCES.remove(self._issuer)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_trace_seal", _trace_digest(self.hydride_trace))
        object.__setattr__(self, "_history_seal", self._history_digest())

    def _history_digest(self):
        digest = hashlib.sha256(repr((self.source_history.location, self.source_history.time_s,
            self.source_history.end_reason, self.evidence_id, self.back_pressure_pa,
            self.port_mass_quadrature, self.relative_mass_tolerance,
            self.absolute_mass_tolerance_kg, self.mass_closure_evidence_id,
            self.port_interval_mass_kg, self.nozzle_interval_mass_kg,
            self.interval_mass_residual_kg, self.source_origin,
            self.opening, id(self.nozzle), id(self.nozzle.properties),
            self.nozzle.properties.basis, self.nozzle.search)).encode())
        for sample in self.source_history.samples:
            digest.update(repr((sample.upstream_stagnation, sample.back_pressure_pa,
                sample.effective_area_m2, sample.mass_flow_kg_s, sample.velocity_m_s,
                sample.regime, sample.model_id)).encode())
        return digest.hexdigest()

    def require_current(self):
        from ..storage.finite_hydride import FiniteHydrideTrace

        if self._issuer is not self._issued:
            raise ValueError("Hydride release handoff lost its original issuer identity")
        if type(self.hydride_trace) is not FiniteHydrideTrace:
            raise TypeError("Retain the original finite-hydride trace")
        trace = self.hydride_trace
        port_mass = _port_interval_mass(trace)
        nozzle_mass = _integrated_nozzle_mass(self.source_history, self.port_mass_quadrature)
        residual = tuple(float(a-b) for a, b in zip(nozzle_mass, port_mass, strict=True))
        tolerance = tuple(self.absolute_mass_tolerance_kg
                          + self.relative_mass_tolerance*mass for mass in port_mass)
        if (_trace_digest(trace) != self._trace_seal
                or self.source_history.location.clock_id != trace.clock_id
                or self.source_history.time_s != tuple(float(t) for t in trace.time_s)
                or len(self.source_history.samples) != len(trace.snapshots)
                or self.port_interval_mass_kg != port_mass
                or self.nozzle_interval_mass_kg != nozzle_mass
                or self.interval_mass_residual_kg != residual
                or any(abs(error) > limit for error, limit in zip(residual, tolerance, strict=True))
                or any(sample.upstream_stagnation is not snapshot.gas
                       or sample.opening != self.opening
                       or sample.back_pressure_pa != self.back_pressure_pa
                       for sample, snapshot in zip(self.source_history.samples,
                                                   trace.snapshots, strict=True))
                or self._history_digest() != self._history_seal):
            raise ValueError("Hydride source, exact nozzle states or retained history changed")
        return self


def _port_interval_mass(trace):
    values = -np.diff(trace.integrated_external_gas_mass_kg)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)) or np.any(values < 0.):
        raise ValueError("Accepted hydride gas-port intervals must contain finite outward H2 mass")
    return tuple(float(value) for value in values)


def _integrated_nozzle_mass(history, rule):
    if rule not in {"left_hold", "right_hold", "trapezoid"}:
        raise ValueError("Select left_hold, right_hold or trapezoid mass-flow quadrature")
    times = np.asarray(history.time_s, dtype=float)
    rates = np.asarray([sample.mass_flow_kg_s for sample in history.samples], dtype=float)
    if (len(times) < 2 or rates.shape != times.shape or not np.all(np.isfinite(rates))
            or np.any(rates < 0.)):
        raise ValueError("Nozzle mass-flow samples must be finite and nonnegative")
    if rule == "left_hold":
        interval_rate = rates[:-1]
    elif rule == "right_hold":
        interval_rate = rates[1:]
    else:
        interval_rate = .5*(rates[:-1]+rates[1:])
    return tuple(float(value) for value in interval_rate*np.diff(times))


def nozzle_history_from_hydride_trace(trace, *, nozzle, opening, location,
        back_pressure_pa: float, evidence_id: str, origin: Origin,
        port_mass_quadrature: str, relative_mass_tolerance: float,
        absolute_mass_tolerance_kg: float, mass_closure_evidence_id: str):
    """Run the existing nozzle at each native hydride output state.

    Each nozzle interval is integrated under the caller-selected quadrature and
    compared with the accepted finite-bed outward gas-port mass. A mismatch is
    rejected; the adapter never rescales nozzle flow or edits the bed ledger.
    """
    from ..storage.finite_hydride import FiniteHydrideTrace
    from ..core import finite

    if type(trace) is not FiniteHydrideTrace or trace.gas_port_boundary is None:
        raise TypeError("Supply a finite hydride trace with its original gas-port boundary")
    if not isinstance(nozzle, HomogeneousIsentropicNozzle) or not isinstance(opening, NozzleOpening):
        raise TypeError("Supply the existing shared nozzle owner and explicit opening")
    if not isinstance(location, SourceLocation) or location.clock_id != trace.clock_id:
        raise ValueError("Declare a source location on the exact hydride trace clock")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Declare the hydride-to-release handoff evidence")
    origin = Origin(origin)
    if origin == Origin.UNRESOLVED:
        raise ValueError("Resolve the source origin")
    back = finite(back_pressure_pa, "release back pressure", positive=True)
    relative = finite(relative_mass_tolerance, "relative_mass_tolerance")
    absolute = finite(absolute_mass_tolerance_kg, "absolute_mass_tolerance_kg")
    if relative < 0. or absolute < 0. or (relative == 0. and absolute == 0.):
        raise ValueError("Declare a positive finite mass-closure tolerance budget")
    if not isinstance(mass_closure_evidence_id, str) or not mass_closure_evidence_id.strip():
        raise ValueError("Declare the basis for the nozzle/port mass-closure tolerance")
    if len(trace.snapshots) < 2 or not np.array_equal(trace.time_s,
            np.asarray([snapshot.time_s for snapshot in trace.snapshots])):
        raise ValueError("Hydride source clock must retain at least two exact native snapshots")
    outlet_mass = _port_interval_mass(trace)
    if not np.any(np.asarray(outlet_mass) > 0.):
        raise ValueError("The retained H2 port history must describe outward-only discharge")
    for snapshot in trace.snapshots:
        snapshot.gas.basis.require_compatible(nozzle.properties.basis)
    if trace.gas_port_boundary.clock_id != trace.clock_id:
        raise ValueError("Hydrogen outlet port and release history clocks differ")
    samples = tuple(nozzle.solve(snapshot.gas, back_pressure_pa=back, opening=opening)
                    for snapshot in trace.snapshots)
    history = SourceHistory(location, tuple(float(t) for t in trace.time_s), samples,
        "inventory_limit" if trace.termination == "gas_inventory_floor" else "window_end")
    nozzle_mass = _integrated_nozzle_mass(history, port_mass_quadrature)
    residual = tuple(float(a-b) for a, b in zip(nozzle_mass, outlet_mass, strict=True))
    tolerance = tuple(absolute + relative*mass for mass in outlet_mass)
    if any(abs(error) > limit for error, limit in zip(residual, tolerance, strict=True)):
        raise ValueError("Integrated nozzle flow does not close against accepted finite-bed gas-port mass")
    token = object()
    _PENDING_HYDROGEN_SOURCES.add(token)
    try:
        result = HydrideNozzleSource(trace, nozzle, opening, history, back,
            evidence_id.strip(), origin, port_mass_quadrature, relative, absolute,
            mass_closure_evidence_id.strip(), outlet_mass, nozzle_mass, residual, token)
    except Exception:
        _PENDING_HYDROGEN_SOURCES.discard(token)
        raise
    return result.require_current()
