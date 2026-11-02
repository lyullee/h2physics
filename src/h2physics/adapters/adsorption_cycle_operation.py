"""Scheduled native PSA checkpoint accounting without another integration driver.

Only slot/cycle checkpoint states are available from the reviewed native runner.
No accepted internal time history or continuous rate history is reconstructed.
"""

from dataclasses import dataclass, field

import numpy as np

from ..core import immutable_array, finite
from .adsorption_operation import audit_bed_inventory
from .psa_cycle import PsaCycleRun, PsaDynaCycle


@dataclass(frozen=True, slots=True)
class AdsorptionCycleCheckpoint:
    native_point: object = field(repr=False)
    time_s: float
    bed_inventory_audits: tuple
    component_residual_mol: np.ndarray
    energy_residual_j: float
    native_vacuum_work_j: float


@dataclass(frozen=True, slots=True)
class AdsorptionCycleOperation:
    run: PsaCycleRun = field(repr=False)
    clock_id: str
    period_s: float
    native_geometry_evidence_id: str
    checkpoints: tuple[AdsorptionCycleCheckpoint, ...]
    component_tolerance_mol: float
    energy_tolerance_j: float

    def require_current(self):
        current = audit_adsorption_cycle(
            self.run, clock_id=self.clock_id, period_s=self.period_s,
            native_geometry_evidence_id=self.native_geometry_evidence_id,
            component_tolerance_mol=self.component_tolerance_mol,
            energy_tolerance_j=self.energy_tolerance_j,
        )
        if len(current.checkpoints) != len(self.checkpoints):
            raise ValueError("Native adsorption checkpoint count changed")
        for original, replay in zip(self.checkpoints, current.checkpoints, strict=True):
            if (original.native_point is not replay.native_point
                    or original.time_s != replay.time_s
                    or original.energy_residual_j != replay.energy_residual_j
                    or original.native_vacuum_work_j != replay.native_vacuum_work_j
                    or not np.array_equal(original.component_residual_mol, replay.component_residual_mol)):
                raise ValueError("Native adsorption checkpoint receipt changed")
            for audit in original.bed_inventory_audits:
                audit.require_current()
        return self


def audit_adsorption_cycle(run, *, clock_id, period_s, native_geometry_evidence_id,
                           component_tolerance_mol, energy_tolerance_j):
    """Audit supported scheduled endpoints in their original native references.

    Native vacuum work is retained separately. It is a utility ledger and does
    not enter the native bed stored-energy balance, which uses stream enthalpy
    and ambient heat. No vacuum-machine efficiency or thermal deposition is inferred.
    """
    if type(run) is not PsaCycleRun:
        raise TypeError("Retain the actual PsaDynaCycle.run result")
    run.require_current()
    if not isinstance(clock_id, str) or not clock_id.strip() or clock_id != run.clock_id:
        raise ValueError("Retain the original physical cycle clock")
    period = finite(period_s, "period_s", positive=True)
    component_budget = finite(component_tolerance_mol, "component_tolerance_mol", positive=True)
    energy_budget = finite(energy_tolerance_j, "energy_tolerance_j", positive=True)
    if period != run.native_schedule["cycle_time_s"]:
        raise ValueError("Declared cycle period differs from native schedule")
    if not run.points:
        raise ValueError("Retain at least the native initial checkpoint")
    initial = run.points[0]
    if (initial.completed_cycles != 0 or initial.completed_slots_in_cycle != 0
            or initial.native_elapsed_s != 0. or initial.time_s != run.start_time_s):
        raise ValueError("Retain the original zero-elapsed native initial checkpoint")
    slots = run.native_schedule["slots"]
    if not slots:
        raise ValueError("Native cycle schedule must retain physical slots")
    for slot in slots:
        finite(slot["duration_s"], "native slot duration", positive=True)
    native = run.bed_adapter.native_bed
    checkpoints = []
    previous = None
    for point in run.points:
        if (type(point.completed_cycles) is not int or point.completed_cycles < 0
                or type(point.completed_slots_in_cycle) is not int
                or not 0 <= point.completed_slots_in_cycle <= len(run.native_schedule["slots"])):
            raise ValueError("Native checkpoint cycle/slot indices are invalid")
        elapsed = point.completed_cycles*period+sum(
            slot["duration_s"] for slot in run.native_schedule["slots"][:point.completed_slots_in_cycle])
        if (point.native_elapsed_s != elapsed or point.time_s != run.start_time_s+elapsed
                or previous is not None and point.time_s <= previous):
            raise ValueError("Native checkpoint time disagrees with the declared slot/cycle schedule")
        previous = point.time_s
        audits = tuple(audit_bed_inventory(
            bed, adsorbent_mass_kg_by_cell=native.mass,
            free_volume_m3_by_cell=native.vgas,
            geometry_evidence_id=native_geometry_evidence_id,
            molar_tolerance=component_budget,
        ) for bed in point.beds)
        if not audits or any(audit.native_energy_reference_id != run.evidence.energy_reference_id for audit in audits):
            raise ValueError("Native bed checkpoints must retain the run energy reference")
        inventory = np.sum([audit.total_component_mol for audit in audits], axis=0)
        energy = sum(audit.native_stored_energy_j for audit in audits)
        if (not np.allclose(inventory, point.inventory_mol, rtol=0., atol=component_budget)
                or abs(energy-point.stored_energy_j) > energy_budget):
            raise ValueError("Independent bed inventory disagrees with native aggregate checkpoint")
        component = inventory-initial.inventory_mol-point.feed_mol+point.product_mol+point.tail_mol
        energy_residual = (energy-initial.stored_energy_j-point.feed_enthalpy_j
                           +point.product_enthalpy_j+point.tail_enthalpy_j-point.ambient_heat_j)
        if (not np.allclose(component, point.component_residual_mol, rtol=0., atol=component_budget)
                or abs(energy_residual-point.energy_residual_j) > energy_budget):
            raise ValueError("Native checkpoint residual fields disagree with their retained ledgers")
        component = np.array(component, copy=True)
        component = immutable_array(component, name="component")
        vacuum_work = finite(point.vacuum_work_j, "native vacuum work J")
        if vacuum_work < 0:
            raise ValueError("Native vacuum-work ledger cannot be negative")
        checkpoints.append(AdsorptionCycleCheckpoint(point, point.time_s, audits, component,
                                                      energy_residual, vacuum_work))
    run.require_current()
    return AdsorptionCycleOperation(run, clock_id, period, native_geometry_evidence_id,
                                    tuple(checkpoints), component_budget, energy_budget)


def run_adsorption_cycle_operation(owner, *, start_time_s, clock_id, period_s,
                                   native_geometry_evidence_id,
                                   component_tolerance_mol, energy_tolerance_j):
    """Call the existing native cycle runner once, then audit its actual endpoints."""
    if type(owner) is not PsaDynaCycle:
        raise TypeError("Supply the existing admitted native PsaDynaCycle owner")
    if finite(period_s, "period_s", positive=True) != owner.schedule["cycle_time_s"]:
        raise ValueError("Declare the existing owner's actual cycle period before execution")
    finite(component_tolerance_mol, "component_tolerance_mol", positive=True)
    finite(energy_tolerance_j, "energy_tolerance_j", positive=True)
    if not isinstance(native_geometry_evidence_id, str) or not native_geometry_evidence_id.strip():
        raise ValueError("Declare native geometry evidence before execution")
    run = owner.run(start_time_s=start_time_s, clock_id=clock_id)
    try:
        return audit_adsorption_cycle(
            run, clock_id=clock_id, period_s=period_s,
            native_geometry_evidence_id=native_geometry_evidence_id,
            component_tolerance_mol=component_tolerance_mol, energy_tolerance_j=energy_tolerance_j,
        )
    except Exception as cause:
        raise AdsorptionCycleOperationError(cause, run) from cause


class AdsorptionCycleOperationError(RuntimeError):
    def __init__(self, cause, run):
        self.cause = cause
        self.run = run
        super().__init__("Native adsorption cycle completed but host checkpoint audit failed")


@dataclass(frozen=True, slots=True)
class AdsorptionProductWindow:
    """Finite-window product mean; no instantaneous or CSS performance inference."""

    operation: AdsorptionCycleOperation = field(repr=False)
    start_time_s: float
    end_time_s: float
    component_product_mol: np.ndarray
    component_mean_molar_rate_mol_s: np.ndarray
    composition: object
    declared_product_state: object
    mean_stream: object
    state_projection_evidence_id: str
    includes_startup: bool
    _captured: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "_captured", self._content())

    def _content(self):
        return (id(self.operation), self.start_time_s, self.end_time_s,
                self.component_product_mol.tobytes(), self.component_mean_molar_rate_mol_s.tobytes(),
                repr(self.composition), repr(self.declared_product_state), repr(self.mean_stream),
                self.state_projection_evidence_id, self.includes_startup)

    def require_current(self):
        self.operation.require_current()
        if self._content() != self._captured:
            raise ValueError("Product reporting window changed after construction")
        endpoints = {point.time_s: point for point in self.operation.run.points}
        if (self.start_time_s not in endpoints or self.end_time_s not in endpoints
                or not np.array_equal(endpoints[self.end_time_s].product_mol
                                      - endpoints[self.start_time_s].product_mol,
                                      self.component_product_mol)):
            raise ValueError("Native cumulative product changed after reporting projection")
        return self


def adsorption_product_window(operation, *, first_checkpoint_index, last_checkpoint_index,
                              molar_masses_kg_mol, composition_id, product_state,
                              component_id, port_id, state_projection_evidence_id):
    """Project actual cumulative native product increments onto a declared mean stream.

    Select native scheduled endpoints explicitly. Product composition is computed
    from the complete product molar vector over that finite window; the caller
    supplies species molar masses and thermodynamic state evidence. The state is
    a reporting projection, not measured native instantaneous outlet conditions.
    This projection makes no enthalpy conservation or CSS/steady-capacity claim.
    """
    from ..core import Stream, ThermoState
    from ..mixtures import GasComposition

    if type(operation) is not AdsorptionCycleOperation:
        raise TypeError("Use the actual audited native cycle operation")
    operation.require_current()
    points = operation.run.points
    indices = (first_checkpoint_index, last_checkpoint_index)
    if any(type(value) is not int or not 0 <= value < len(points) for value in indices):
        raise ValueError("Select valid integer native checkpoint indices")
    if first_checkpoint_index >= last_checkpoint_index:
        raise ValueError("Product window needs increasing checkpoint indices")
    if not isinstance(product_state, ThermoState):
        raise TypeError("Declare the thermodynamic state of the reporting stream")
    for value in (composition_id, component_id, port_id, state_projection_evidence_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Declare composition, stream and state-projection evidence identities")
    first, last = (points[index] for index in indices)
    duration = finite(last.time_s-first.time_s, "product reporting duration", positive=True)
    amount = np.array(last.product_mol-first.product_mol, dtype=float, copy=True)
    if not np.all(np.isfinite(amount)) or np.any(amount < 0) or amount.sum() <= 0:
        raise ValueError("Product window must retain a positive finite nonnegative species increment")
    composition = GasComposition(composition_id, operation.run.basis.species,
                                 amount/amount.sum(), molar_masses_kg_mol)
    if hasattr(product_state, "vapor_mole_fraction") and product_state.phase == "two_phase":
        raise ValueError("A two-phase mixture reporting stream requires explicit phase-specific product accounting")
    rate = amount/duration
    mass_rate = float(np.sum(rate*composition.molar_masses_kg_mol))
    stream = Stream(component_id, port_id, mass_rate, product_state)
    amount = immutable_array(amount, name="amount")
    rate = immutable_array(rate, name="rate")
    return AdsorptionProductWindow(operation, first.time_s, last.time_s, amount, rate,
                                    composition, product_state, stream,
                                    state_projection_evidence_id, first_checkpoint_index == 0)


__all__ = ["AdsorptionCycleCheckpoint", "AdsorptionCycleOperation",
           "audit_adsorption_cycle", "run_adsorption_cycle_operation", "AdsorptionCycleOperationError",
           "AdsorptionProductWindow", "adsorption_product_window"]
