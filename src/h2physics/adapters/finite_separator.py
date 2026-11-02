"""Finite pure-fluid phase-selective storage over the native stratified tank.

This is a two-region native vessel operation, not an equilibrium mixture separator.
Incoming phase assignment is explicit. Native interface transfer, EOS, heat and
phase-selective outgoing enthalpy remain owned by StratifiedTank.
"""

from dataclasses import dataclass, field
from math import fsum

import numpy as np

from ..core import finite
from .lh2dt import Lh2dtProperties, from_lh2dt_state
from .lh2dt_compressor import Lh2dtNativeProvenance, _property_binding, _record_signature

_PENDING_SEPARATOR_TRACE_ISSUERS = set()


def _issue_finite_separator_trace(**values):
    token = object()
    _PENDING_SEPARATOR_TRACE_ISSUERS.add(token)
    try:
        return FiniteSeparatorTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_SEPARATOR_TRACE_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class FiniteSeparatorPoint:
    time_s: float
    native_state: object
    liquid: object
    vapor: object
    total_mass_kg: float
    fluid_internal_energy_j: float
    wall_internal_energy_j: float
    boundary_mass_kg: float
    boundary_energy_j: float
    mass_residual_kg: float
    energy_residual_j: float
    native_step: object


@dataclass(frozen=True, slots=True)
class FiniteSeparatorTrace:
    native_owner: object
    initial_state: object
    clock_id: str
    phase_assignment_evidence_id: str
    points: tuple
    native_rows: tuple
    boundary_evaluations: tuple
    material_species_id: str
    native_provenance: object
    source_guard: object = field(repr=False, compare=False)
    _captured_points: str = field(init=False, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SEPARATOR_TRACE_ISSUERS:
            raise ValueError("Finite separator traces are issued only by the completed native run")
        _PENDING_SEPARATOR_TRACE_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_captured_points", repr(self.points))

    def require_current(self):
        self.source_guard()
        if repr(self.points) != self._captured_points:
            raise ValueError("Native separator accepted point changed after capture")
        return self


class FiniteSeparatorError(RuntimeError):
    def __init__(self, cause, owner, initial, evaluations, rows):
        self.cause, self.native_owner, self.initial_state = cause, owner, initial
        self.boundary_evaluations, self.native_rows = tuple(evaluations), tuple(rows)
        self.accepted_prefix_available = bool(rows)
        self.accepted_prefix_limitation = (
            "Native simulate keeps accepted results local until return; on an integration exception "
            "only original evaluated boundary trials are exposed, not accepted checkpoint rows")
        super().__init__("Native pure-fluid phase-selective separator operation failed")


def run_finite_pure_fluid_separator(native_owner, initial_state, *, bridge,
        material_species_id, duration_s, maximum_step_s, start_time_s, clock_id,
        phase_flows, ambient_temperature_k, phase_assignment_evidence_id,
        phase_domains, mass_tolerance_kg, energy_tolerance_j,
        minimum_liquid_inventory_kg, minimum_vapor_inventory_kg,
        wall_heat_callback=None, fluid_heat_callback=None):
    """Run the existing native two-region phase inventories and audit stored energy.

    ``phase_flows(time_s, thermo)`` returns native ``(liquid_flows,vapor_flows)``.
    Positive streams enter the assigned phase. Outgoing enthalpy is the current
    native phase enthalpy, regardless of the outgoing stream's supplied number.
    All callbacks receive absolute physical time; commands must be continuous
    within this single native run. Unknown phase depletion rejects natively.
    """
    from lh2dt.stratified_tank import StratifiedTank
    from lh2dt.streams import MassEnergyFlow

    if type(native_owner) is not StratifiedTank or type(bridge) is not Lh2dtProperties:
        raise TypeError("Supply the actual native StratifiedTank and its property bridge")
    if native_owner.properties is not bridge.native:
        raise ValueError("Native separator and bridge must share one property owner")
    if bridge.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}:
        raise ValueError("Finite separator requires an explicit pure native hydrogen spin identity")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("Declare a nonempty physical clock identity")
    for value in (material_species_id, phase_assignment_evidence_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Declare pure material identity and phase-assignment evidence")
    phase_domains = dict(phase_domains)
    if (not callable(phase_flows) or set(phase_domains) != {"liquid", "vapor"}
            or any(not callable(domain) for domain in phase_domains.values())):
        raise ValueError("Supply actual phase flows and separate phase domain owners")
    duration = finite(duration_s, "duration_s", positive=True)
    step = finite(maximum_step_s, "maximum_step_s", positive=True)
    start = finite(start_time_s, "start_time_s")
    if (duration < 1e-9 or min(step, duration) < 1e-9 or start+min(step, duration) <= start
            or abs((start+duration)-start-duration) > 1e-10):
        raise ValueError("Physical clock must resolve native RK steps and the requested finite duration")
    mass_budget = finite(mass_tolerance_kg, "mass_tolerance_kg", positive=True)
    energy_budget = finite(energy_tolerance_j, "energy_tolerance_j", positive=True)
    floors = (finite(minimum_liquid_inventory_kg, "liquid inventory floor", positive=True),
              finite(minimum_vapor_inventory_kg, "vapor inventory floor", positive=True))
    evaluations, rows = [], ()
    parameters = native_owner.parameters
    provenance = Lh2dtNativeProvenance.capture(native_owner, initial_state)
    # Bind ordinary callback code/configuration across the native integration.
    # A callback that mutates its captured schedule or bound receiver during a
    # run must not silently change the physical operation halfway through.
    from .facility_consequence import _evaluator_binding

    def callback_bindings():
        return (
            _evaluator_binding(phase_flows),
            _evaluator_binding(ambient_temperature_k) if callable(ambient_temperature_k) else ambient_temperature_k,
            _evaluator_binding(wall_heat_callback) if wall_heat_callback is not None else None,
            _evaluator_binding(fluid_heat_callback) if fluid_heat_callback is not None else None,
            tuple((key, _evaluator_binding(value)) for key, value in phase_domains.items()),
        )

    callbacks = callback_bindings()
    configuration = (_property_binding(bridge), _record_signature(parameters),
                     _record_signature(vars(native_owner.shape)), callbacks)

    def guard():
        provenance.require_current(check_files=False)
        if (native_owner.properties is not bridge.native or native_owner.parameters is not parameters
                or (_property_binding(bridge), _record_signature(native_owner.parameters),
                    _record_signature(vars(native_owner.shape)), callback_bindings()) != configuration):
            raise ValueError("Original native separator source, callbacks, or configuration changed")

    def inventories(state):
        for name in ("liquid_mass_kg", "vapor_mass_kg", "lower_wall_temperature_K", "upper_wall_temperature_K"):
            finite(getattr(state, name), "native "+name, positive=True)
        finite(state.liquid_internal_energy_J, "native liquid internal energy")
        finite(state.vapor_internal_energy_J, "native vapor internal energy")
        if state.liquid_mass_kg <= floors[0] or state.vapor_mass_kg <= floors[1]:
            raise ValueError("A separator phase reached its declared finite inventory floor")
        mass = state.liquid_mass_kg+state.vapor_mass_kg
        fluid = state.liquid_internal_energy_J+state.vapor_internal_energy_J
        wall = (parameters.lower_wall_heat_capacity_J_K*state.lower_wall_temperature_K
                +parameters.upper_wall_heat_capacity_J_K*state.upper_wall_temperature_K)
        return mass, fluid, wall

    initial_mass, initial_u, initial_wall = inventories(initial_state)

    def admit(thermo, state=None):
        guard()
        liquid = from_lh2dt_state(thermo.liquid, basis=bridge.basis)
        vapor = from_lh2dt_state(thermo.vapor, basis=bridge.basis)
        for name, fluid in (("liquid", liquid), ("vapor", vapor)):
            # The caller's domain owns fluid T/P/phase admission. Inventory floors
            # are enforced natively and at accepted snapshots, not fabricated here.
            decision = phase_domains[name](fluid)
            if decision is not None and not isinstance(decision, (bool, np.bool_)):
                raise TypeError("Phase domain must validate by exception/None or return one boolean")
            if decision is not None and not bool(decision):
                raise ValueError("Caller phase domain rejected the native separator state")
            guard()
        trial_masses = (finite(thermo.liquid_volume_m3, "native liquid volume", positive=True)*thermo.liquid.density_kg_m3,
                        finite(thermo.vapor_volume_m3, "native vapor volume", positive=True)*thermo.vapor.density_kg_m3)
        if any(mass <= floor for mass, floor in zip(trial_masses, floors)):
            raise ValueError("Native separator trial reached a declared phase inventory floor")
        return liquid, vapor

    def flows(local_time, thermo):
        liquid, vapor = admit(thermo)
        original = phase_flows(start+local_time, thermo)
        if not isinstance(original, (tuple, list)) or len(original) != 2:
            raise ValueError("Declare distinct liquid and vapor native stream sequences")
        groups = tuple(tuple(group) for group in original)
        guard()
        for group in groups:
            for flow in group:
                if type(flow) is not MassEnergyFlow:
                    raise TypeError("Use actual native MassEnergyFlow objects")
                finite(flow.mass_flow_kg_s, "native phase mass flow")
                finite(flow.specific_enthalpy_J_kg, "native phase stream enthalpy")
        evaluations.append((start+local_time, thermo, groups))
        return groups

    def absolute(callback):
        if callback is None:
            return None
        def evaluate(local_time, thermo):
            guard()
            result = callback(start+local_time, thermo)
            guard()
            return result
        return evaluate

    def ambient(local_time):
        guard()
        value = ambient_temperature_k(start+local_time) if callable(ambient_temperature_k) else ambient_temperature_k
        guard()
        return finite(value, "separator ambient temperature K", positive=True)
    try:
        admit(native_owner.thermo(initial_state), initial_state)
        rows = tuple(native_owner.simulate(initial_state, duration, min(step, duration),
            ambient, flows, wall_heat_callback=absolute(wall_heat_callback),
            fluid_heat_callback=absolute(fluid_heat_callback)))
        guard()
        if not rows or abs(rows[-1].time_s-duration) > 1e-10:
            raise ValueError("Native separator did not reach its requested endpoint")
        points = []
        for local_time, state, thermo, row in [(0., initial_state, native_owner.thermo(initial_state), None)]+[
                (row.time_s, row.state, row.thermo, row) for row in rows]:
            if points and not 0 < start+local_time-points[-1].time_s <= step+1e-10:
                raise ValueError("Native separator accepted clock/step sequence is invalid")
            liquid, vapor = admit(thermo, state)
            mass, fluid, wall = inventories(state)
            boundary_mass = 0. if row is None else row.cumulative_boundary_mass_kg
            boundary_energy = 0. if row is None else row.cumulative_boundary_energy_J
            residual_m = mass-initial_mass-boundary_mass
            residual_e = fsum((fluid, wall, -initial_u, -initial_wall, -boundary_energy))
            if abs(residual_m) > mass_budget or abs(residual_e) > energy_budget:
                raise ValueError("Native phase-selective inventory mass/energy ledger failed")
            points.append(FiniteSeparatorPoint(start+local_time, state, liquid, vapor, mass,
                fluid, wall, boundary_mass, boundary_energy, residual_m, residual_e, row))
        return _issue_finite_separator_trace(
            native_owner=native_owner,
            initial_state=initial_state,
            clock_id=clock_id,
            phase_assignment_evidence_id=phase_assignment_evidence_id,
            points=tuple(points),
            native_rows=rows,
            boundary_evaluations=tuple(evaluations),
            material_species_id=material_species_id,
            native_provenance=provenance,
            source_guard=guard,
        )
    except Exception as cause:
        raise FiniteSeparatorError(cause, native_owner, initial_state, evaluations, rows) from cause


__all__ = ["FiniteSeparatorPoint", "FiniteSeparatorTrace", "FiniteSeparatorError",
           "run_finite_pure_fluid_separator"]
