"""Finite-source projection for a completed pure-H2 Cantera gas-volume vent."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from math import fsum

import numpy as np

from ..core import Origin, ThermoState, finite
from ..release import SourceLocation
from ..sources import IntervalMassSource
from .cantera_volume import GasVolumeTrace, _phase_fingerprint


_PENDING: set[object] = set()


def _trace_payload(trace):
    snapshots = tuple((item.time_s, item.mass_kg, item.volume_m3,
        item.temperature_k, item.pressure_pa, tuple(item.mass_fractions.items()),
        tuple(item.mole_fractions.items()), item.internal_energy_j,
        item.specific_enthalpy_j_kg) for item in trace.snapshots)
    arrays = tuple((name, getattr(trace, name).shape, getattr(trace, name).dtype.str,
                    getattr(trace, name).tobytes()) for name in (
        "time_s", "ledger_native_scale_to_si", "boundary_integrals", "mass_residual_kg",
        "species_residual_kg", "energy_residual_j", "reaction_species_integrals_kg",
        "element_residual_kg"))
    heat = tuple((item.boundary_id, item.clock_id, item.support_start_s,
        item.support_end_s, item.environment_state.temperature_k,
        item.environment_state.pressure_pa, tuple(item.environment_state.mole_fractions.items()),
        item.area_m2, item.heat_transfer_coefficient_w_m2_k, item.emissivity,
        id(item.heat_flux_w_m2)) for item in trace.heat_boundaries)
    return (id(trace), trace.mechanism_basis, trace.phase_fingerprint, trace.clock_id,
        tuple(trace.species_names), snapshots, tuple(trace.ledger_names),
        tuple(trace.ledger_units), arrays, trace.ledger_method,
        trace.evaluated_clock_bounds_s, trace.element_names,
        trace.source_phase_fingerprint, trace.phase_copy_audits, trace.definition_guard,
        id(trace.native), id(trace.native.reactor), id(trace.native.network),
        tuple(id(item) for item in trace.native.feed_devices),
        tuple(id(item) for item in trace.native.vent_devices),
        heat,
        tuple((item.rate.boundary_id, item.rate.clock_id, item.rate.support_start_s,
               item.rate.support_end_s, item.rate.source_id, item.rate.origin,
               item.rate.phase_access, id(item.rate.callback),
               item.state.temperature_k, item.state.pressure_pa,
               tuple(item.state.mole_fractions.items())) for item in trace.feeds),
        tuple((item.rate.boundary_id, item.rate.clock_id, item.rate.support_start_s,
               item.rate.support_end_s, item.rate.source_id, item.rate.origin,
               item.rate.phase_access, id(item.rate.callback), item.downstream_state.temperature_k,
               item.downstream_state.pressure_pa,
               tuple(item.downstream_state.mole_fractions.items())) for item in trace.vents),
        trace.chemistry, trace.hydrogen_partition_id)


def _require_trace_current(trace, signature):
    if type(trace) is not GasVolumeTrace or _trace_payload(trace) != signature:
        raise ValueError("Cantera gas-volume output or retained boundary identity changed")
    if not trace.snapshots or trace.time_s.size != len(trace.snapshots):
        raise ValueError("Cantera gas-volume trace has no complete aligned output history")
    phase = trace.native.reactor.phase
    if _phase_fingerprint(phase, include_reactions=trace.chemistry == "finite_rate") != trace.phase_fingerprint:
        raise ValueError("Native gas-volume thermochemistry changed after the completed run")
    last = trace.snapshots[-1]
    if (trace.native.reactor.mass != last.mass_kg
            or trace.native.reactor.volume != last.volume_m3
            or phase.T != last.temperature_k or phase.P != last.pressure_pa
            or not np.array_equal(phase.Y, np.asarray(
                [last.mass_fractions[name] for name in trace.species_names]))
            or not np.array_equal(phase.X, np.asarray(
                [last.mole_fractions[name] for name in trace.species_names]))
            or trace.native.reactor.mass*phase.int_energy_mass != last.internal_energy_j
            or phase.enthalpy_mass != last.specific_enthalpy_j_kg):
        raise ValueError("Native gas-volume endpoint no longer matches its accepted snapshot")


def _projection(trace, location, state, *, vent_boundary_id,
                boundary_projection_evidence_id, state_projection_evidence_id,
                mass_tolerance_kg, species_tolerance_kg, energy_tolerance_j,
                relative_energy_tolerance):
    if type(trace) is not GasVolumeTrace:
        raise TypeError("Use a completed original GasVolumeTrace")
    if type(location) is not SourceLocation or type(state) is not ThermoState:
        raise TypeError("Supply an explicit source location and a representative H2 state")
    if trace.chemistry != "frozen" or trace.feeds or len(trace.vents) != 1:
        raise ValueError("Only frozen, no-feed, exactly-one-vent control volumes are admitted")
    vent = trace.vents[0]
    if vent.rate.boundary_id != vent_boundary_id:
        raise ValueError("Select the exact retained vent boundary identity")
    if (tuple(trace.species_names) != ("H2",)
            or trace.hydrogen_partition_id != "mechanism-H2-spin-unresolved"):
        raise ValueError("This projection requires one pure, spin-unresolved molecular-H2 species")
    native_h2 = trace.native.reactor.phase.species("H2")
    if dict(native_h2.composition) != {"H": 2.} or native_h2.charge != 0.:
        raise ValueError("The retained native H2 species must be neutral molecular hydrogen")
    phase = trace.native.reactor.phase
    if phase.n_reactions != 0:
        raise ValueError("A frozen-source receipt requires a native phase with no reactions")
    if any(snapshot.mass_fractions != {"H2": 1.}
           or snapshot.mole_fractions != {"H2": 1.} for snapshot in trace.snapshots):
        raise ValueError("Every retained accepted snapshot must remain a pure H2 gas")
    if location.source_id != vent.rate.source_id or location.clock_id != trace.clock_id:
        raise ValueError("Source location must preserve the vent source and native operation clock")
    basis_reference_token = (
        f":{trace.mechanism_basis.identifier}:source-sha256="
        f"{trace.mechanism_basis.source_sha256}:"
    )
    if (not state.basis.fluid.startswith("Cantera:frozen-ideal-gas:Y-sha256=")
            or not state.basis.reference_id.startswith("Cantera:")
            or basis_reference_token not in state.basis.reference_id
            or state.basis.spin_composition != trace.hydrogen_partition_id
            or state.phase not in {"gas", "supercritical", "supercritical_gas"}):
        raise ValueError("Representative state must preserve the same native Cantera H2 mechanism/reference")
    if state.vapor_mass_fraction not in (None, 1.):
        raise ValueError("Representative H2 source state must be all vapor")
    if not isinstance(boundary_projection_evidence_id, str) or not boundary_projection_evidence_id.strip():
        raise ValueError("Declare the vent-to-source spatial projection evidence")
    if not isinstance(state_projection_evidence_id, str) or not state_projection_evidence_id.strip():
        raise ValueError("Declare the single-state thermodynamic projection evidence")
    mass_budget = finite(mass_tolerance_kg, "mass closure budget", positive=True)
    species_budget = finite(species_tolerance_kg, "species closure budget", positive=True)
    energy_budget_abs = finite(energy_tolerance_j, "outlet enthalpy projection budget", positive=True)
    energy_budget_rel = finite(relative_energy_tolerance, "relative outlet enthalpy budget", positive=True)
    if energy_budget_rel > 1e-2:
        raise ValueError("Relative outlet enthalpy budget cannot exceed 1e-2")

    time = np.asarray(trace.time_s, dtype=float)
    if (time.ndim != 1 or time.size < 2 or np.any(np.diff(time) <= 0.)
            or not np.all(np.isfinite(time))):
        raise ValueError("Source times must match the increasing finite native output clock")
    mass_name = f"outlet:{vent_boundary_id}:mass"
    if mass_name not in trace.ledger_names or trace.ledger_units[trace.ledger_names.index(mass_name)] != "kg":
        raise ValueError("Named vent must retain its native cumulative mass ledger in kg")
    cumulative_mass = np.asarray(trace.integral(mass_name), dtype=float)
    cumulative_energy = np.asarray(trace.integral("outlet:enthalpy"), dtype=float)
    energy_index = trace.ledger_names.index("outlet:enthalpy")
    if (trace.ledger_units[energy_index] != "J"
            or cumulative_mass.shape != time.shape or cumulative_energy.shape != time.shape
            or not np.all(np.isfinite(cumulative_mass)) or not np.all(np.isfinite(cumulative_energy))
            or abs(cumulative_mass[0]) > mass_budget or abs(cumulative_energy[0]) > energy_budget_abs):
        raise ValueError("Native vent mass/energy integrals must align and begin at zero")
    mass_bins = np.diff(cumulative_mass)
    if np.any(mass_bins < -mass_budget):
        raise ValueError("Native outward vent mass ledger cannot reverse")
    mass_bins = np.maximum(mass_bins, 0.)
    total_mass = fsum(float(value) for value in mass_bins)
    if total_mass <= 0.:
        raise ValueError("The selected native vent has no positive integrated discharge")
    if (trace.mass_residual_kg.shape != time.shape
            or trace.species_residual_kg.shape != (time.size, len(trace.species_names))
            or trace.energy_residual_j.shape != time.shape
            or not np.all(np.isfinite(trace.mass_residual_kg))
            or not np.all(np.isfinite(trace.species_residual_kg))
            or not np.all(np.isfinite(trace.energy_residual_j))):
        raise ValueError("Native control-volume residual axes must match the accepted clock/species")
    if np.max(np.abs(trace.mass_residual_kg)) > mass_budget:
        raise ValueError("Native control-volume total-mass residual exceeds its declared budget")
    if np.max(np.abs(trace.species_residual_kg)) > species_budget:
        raise ValueError("Native control-volume species residual exceeds its declared budget")
    if np.max(np.abs(trace.energy_residual_j)) > energy_budget_abs:
        raise ValueError("Native control-volume energy residual exceeds its declared budget")
    native_enthalpy = finite(cumulative_energy[-1], "integrated native vent enthalpy")
    projected_enthalpy = total_mass*state.enthalpy_j_kg
    projection_residual = projected_enthalpy-native_enthalpy
    projection_budget = energy_budget_abs+energy_budget_rel*max(
        abs(projected_enthalpy), abs(native_enthalpy), 1.)
    if abs(projection_residual) > projection_budget:
        raise ValueError("Representative H2 state does not close integrated native vent enthalpy")
    source = IntervalMassSource(
        location, time, mass_bins, state, vent.rate.origin,
        ":".join((vent.rate.source_id, vent.rate.boundary_id, trace.phase_fingerprint,
                   boundary_projection_evidence_id.strip(), state_projection_evidence_id.strip())),
        "window_end",
    )
    return source, total_mass, native_enthalpy, projected_enthalpy, projection_residual, projection_budget


@dataclass(frozen=True, slots=True)
class CanteraGasVentFiniteSource:
    """Owner-sealed finite source from one conservative frozen-H2 vent ledger."""

    trace: GasVolumeTrace = field(repr=False, compare=False)
    source: IntervalMassSource
    location: SourceLocation = field(repr=False, compare=False)
    representative_state: ThermoState = field(repr=False, compare=False)
    vent_boundary_id: str
    boundary_projection_evidence_id: str
    state_projection_evidence_id: str
    mass_tolerance_kg: float
    species_tolerance_kg: float
    energy_tolerance_j: float
    relative_energy_tolerance: float
    released_mass_kg: float
    native_outlet_enthalpy_j: float
    projected_outlet_enthalpy_j: float
    enthalpy_residual_j: float
    enthalpy_budget_j: float
    _token: object = field(default=None, repr=False, compare=False)
    _trace_signature: tuple = field(default=(), init=False, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Create a vent source through bind_cantera_gas_volume_vent")
        _PENDING.remove(self._token)
        values = (id(self.trace), id(self.source), id(self.location), id(self.representative_state),
            self.vent_boundary_id, self.boundary_projection_evidence_id,
            self.state_projection_evidence_id, self.mass_tolerance_kg,
            self.species_tolerance_kg, self.energy_tolerance_j,
            self.relative_energy_tolerance, self.released_mass_kg,
            self.native_outlet_enthalpy_j, self.projected_outlet_enthalpy_j,
            self.enthalpy_residual_j, self.enthalpy_budget_j)
        object.__setattr__(self, "_trace_signature", _trace_payload(self.trace))
        object.__setattr__(self, "_seal", values)
        object.__setattr__(self, "_token", None)

    def require_current(self):
        _require_trace_current(self.trace, self._trace_signature)
        projection = _projection(
            self.trace, self.location, self.representative_state,
            vent_boundary_id=self.vent_boundary_id,
            boundary_projection_evidence_id=self.boundary_projection_evidence_id,
            state_projection_evidence_id=self.state_projection_evidence_id,
            mass_tolerance_kg=self.mass_tolerance_kg,
            species_tolerance_kg=self.species_tolerance_kg,
            energy_tolerance_j=self.energy_tolerance_j,
            relative_energy_tolerance=self.relative_energy_tolerance)
        source, mass, native_h, projected_h, residual, budget = projection
        actual = (id(self.trace), id(self.source), id(self.location), id(self.representative_state),
            self.vent_boundary_id, self.boundary_projection_evidence_id,
            self.state_projection_evidence_id, self.mass_tolerance_kg,
            self.species_tolerance_kg, self.energy_tolerance_j,
            self.relative_energy_tolerance, self.released_mass_kg,
            self.native_outlet_enthalpy_j, self.projected_outlet_enthalpy_j,
            self.enthalpy_residual_j, self.enthalpy_budget_j)
        self.source.require_current()
        if (actual != self._seal or self.source.location is not self.location
                or self.source.state is not self.representative_state
                or self.source.edges_s.tolist() != source.edges_s.tolist()
                or self.source.mass_kg.tolist() != source.mass_kg.tolist()
                or self.source.evidence_id != source.evidence_id
                or mass != self.released_mass_kg or native_h != self.native_outlet_enthalpy_j
                or projected_h != self.projected_outlet_enthalpy_j
                or residual != self.enthalpy_residual_j or budget != self.enthalpy_budget_j):
            raise ValueError("Cantera vent-source projection or retained owner changed")
        return self


def bind_cantera_gas_volume_vent(
    trace: GasVolumeTrace,
    *,
    vent_boundary_id: str,
    location: SourceLocation,
    representative_state: ThermoState,
    boundary_projection_evidence_id: str,
    state_projection_evidence_id: str,
    mass_tolerance_kg: float = 1e-9,
    species_tolerance_kg: float = 1e-9,
    energy_tolerance_j: float = 1e-3,
    relative_energy_tolerance: float = 1e-8,
) -> CanteraGasVentFiniteSource:
    """Project one completed native frozen pure-H2 vent into finite mass bins.

    Native CVODES outlet-mass and outlet-enthalpy integrals define the source.
    This bounded route rejects feeds, reactions, multiple outlets and changing
    gas species so no component split is inferred from sparse snapshots.
    """
    _require_trace_current(trace, _trace_payload(trace))
    result = _projection(
        trace, location, representative_state, vent_boundary_id=vent_boundary_id,
        boundary_projection_evidence_id=boundary_projection_evidence_id,
        state_projection_evidence_id=state_projection_evidence_id,
        mass_tolerance_kg=mass_tolerance_kg, species_tolerance_kg=species_tolerance_kg,
        energy_tolerance_j=energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance)
    source, mass, native_h, projected_h, residual, budget = result
    token = object()
    _PENDING.add(token)
    return CanteraGasVentFiniteSource(
        trace, source, location, representative_state, vent_boundary_id,
        boundary_projection_evidence_id.strip(), state_projection_evidence_id.strip(),
        finite(mass_tolerance_kg, "mass closure budget", positive=True),
        finite(species_tolerance_kg, "species closure budget", positive=True),
        finite(energy_tolerance_j, "outlet enthalpy projection budget", positive=True),
        finite(relative_energy_tolerance, "relative outlet enthalpy budget", positive=True),
        mass, native_h, projected_h, residual, budget, _token=token).require_current()


__all__ = ["CanteraGasVentFiniteSource", "bind_cantera_gas_volume_vent"]
