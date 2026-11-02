"""Staggered approximate temperature feedback over explicit held-current stages.

Existing thermal and finite-reactant solvers run sequentially. A caller projects
each original thermal trajectory onto one held material temperature. Chemical
and material-conditioning heat differences are retained, never corrected away.
"""

from dataclasses import dataclass, field, replace

from ..core import finite
from ..electrochemical_thermal import FiniteThermalStack, ThermalStackStage
from ..thermochemical import ThermochemicalInventory
from .fuel_cell import FiniteFuelCell, FuelCellStep
from .result_provenance import recorded_content_sha256


_PENDING_STAGED_TRACE_TOKENS: set[object] = set()


class StagedElectrochemicalError(RuntimeError):
    def __init__(self, cause, *, command, completed, thermal_result=None, material_result=None):
        super().__init__(str(cause))
        self.cause, self.command, self.completed = cause, command, tuple(completed)
        self.thermal_result, self.material_result = thermal_result, material_result


@dataclass(frozen=True, slots=True)
class StagedElectrochemicalStep:
    command: ThermalStackStage
    thermal_result: object
    material_result: object
    held_temperature_k: float
    generated_vs_material_heat_residual_j: float
    held_stack_generated_heat_j: float
    material_conditioning_heat_j: float
    thermal_projection_heat_difference_j: float


@dataclass(frozen=True, slots=True)
class StagedElectrochemicalTrace:
    thermal_owner: FiniteThermalStack
    material_owner: FiniteFuelCell
    initial_material: ThermochemicalInventory
    steps: tuple[StagedElectrochemicalStep, ...]
    temperature_projection: object
    projection_evidence_id: str
    refinement_identity: str
    clock_id: str
    heat_mismatch_budget_j: float
    thermal_capacity_scope_evidence_id: str
    _signature: str = field(init=False, repr=False)
    status: str = "implemented_unverified"
    interpretation: str = "staggered held-temperature approximation; not a simultaneous coupled energy solver"
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_STAGED_TRACE_TOKENS:
            raise ValueError("Staged operation traces are issued only by the completed native-owner runner")
        _PENDING_STAGED_TRACE_TOKENS.remove(self._issuer_token)
        if (type(self.thermal_owner) is not FiniteThermalStack
                or type(self.material_owner) is not FiniteFuelCell
                or not self.steps
                or any(type(step) is not StagedElectrochemicalStep for step in self.steps)):
            raise ValueError("A staged receipt requires actual owners and completed staged outputs")
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.thermal_owner), id(self.material_owner), self.thermal_owner.boundary,
            self.thermal_owner.relative_tolerance, self.thermal_owner.absolute_tolerance,
            self.thermal_owner.energy_tolerance_j,
            self.initial_material, self.temperature_projection,
            self.projection_evidence_id, self.refinement_identity, self.clock_id,
            self.heat_mismatch_budget_j, self.thermal_capacity_scope_evidence_id,
            tuple((step.command, step.held_temperature_k,
                   step.generated_vs_material_heat_residual_j,
                   step.held_stack_generated_heat_j, step.material_conditioning_heat_j,
                   step.thermal_projection_heat_difference_j,
                   step.thermal_result.stages,
                   tuple((stage.native_result.t, stage.native_result.y)
                         for stage in step.thermal_result.stages),
                   id(step.material_result)) for step in self.steps),
        ))

    def require_current(self):
        self.material_owner.require_current()
        if self.thermal_owner.stack is not self.material_owner.stack or self._content() != self._signature:
            raise ValueError("Staged electrochemical source, configuration or trajectory changed")
        for step in self.steps:
            step.material_result.require_current()
        return self


def run_staged_electrochemical_operation(material_owner, thermal_owner, initial, commands, *,
                                         temperature_projection, projection_evidence_id,
                                         refinement_identity, clock_id,
                                         heat_mismatch_budget_j,
                                         thermal_capacity_scope_evidence_id):
    """March original thermal and material owners over caller-selected intervals.

    ``temperature_projection(thermal_trace, command)`` explicitly selects the
    held material temperature. It must lie within the accepted thermal range.
    The thermal heat capacity must exclude material sensible heat already owned
    by the finite caloric kernel; the caller declares that capacity scope. The
    residual includes material conditioning and temperature projection effects,
    so an admitted budget is an approximation decision, never energy correction.
    """
    if type(material_owner) is not FiniteFuelCell or type(thermal_owner) is not FiniteThermalStack:
        raise TypeError("Supply existing original finite material and thermal owners")
    if type(initial) is not ThermochemicalInventory or not callable(temperature_projection):
        raise TypeError("Supply the finite material stock and explicit temperature projection")
    for identity in (projection_evidence_id, refinement_identity, clock_id,
                     thermal_capacity_scope_evidence_id):
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("Declare clock, projection, refinement and thermal-capacity scope evidence")
    if (material_owner.stack is not thermal_owner.stack
            or clock_id != material_owner.evidence.clock_id
            or thermal_owner.boundary.reference_id != initial.energy_basis_id
            or thermal_owner.boundary.coolant_boundary_id != material_owner.boundary.thermal_boundary_id):
        raise ValueError("Shared stack, clock, energy reference and thermal boundary are mandatory")
    material_owner.require_current()
    replace(initial)
    if (initial.pressure_pa != material_owner.boundary.pressure_pa
            or initial.energy_basis_id != material_owner.kernel.energy_basis_id):
        raise ValueError("Initial finite stock pressure/reference differs from the material owner")
    if set(initial.amounts_mol)-set(material_owner.kernel.names):
        raise ValueError("Initial stock contains species absent from the finite material kernel")
    thermal_lower, thermal_upper = thermal_owner.boundary.temperature_bounds_k
    material_lower, material_upper = material_owner.boundary.temperature_bounds_k
    if not (max(thermal_lower, material_lower) <= initial.temperature_k
            <= min(thermal_upper, material_upper)):
        raise ValueError("Initial temperature must lie in both original owners' domains")
    energy = material_owner.stack.thermochemistry(initial.temperature_k)
    if (energy.water_phase != material_owner.boundary.water_phase
            or energy.reference_id != initial.energy_basis_id):
        raise ValueError("Initial reaction energy reference or product water phase differs")
    budget = finite(heat_mismatch_budget_j, "per-stage heat mismatch budget", positive=True)
    schedule = tuple(commands)
    if not schedule or any(type(command) is not ThermalStackStage or command.mode != "fuel_cell"
                           for command in schedule):
        raise ValueError("Supply explicit fuel-cell ThermalStackStage commands")
    if len({command.identifier for command in schedule}) != len(schedule):
        raise ValueError("Staged command identities must be unique")
    for left, right in zip(schedule, schedule[1:]):
        if left.end_s != right.start_s:
            raise ValueError("Staged operation requires contiguous explicit intervals")
    remaining_h2 = initial.amounts_mol.get(material_owner.hydrogen_id, 0.)
    remaining_o2 = initial.amounts_mol.get(material_owner.oxygen_id, 0.)
    from ..constants import FARADAY_C_MOL
    geometry = material_owner.stack.geometry
    for command in schedule:
        replace(command)
        if command.current_density_a_m2 > material_owner.boundary.maximum_current_density_a_m2:
            raise ValueError("Staged current exceeds the original material owner limit")
        extent = finite(command.current_density_a_m2*geometry.active_area_m2*geometry.series_cells
                        *(command.end_s-command.start_s)/(2*FARADAY_C_MOL),
                        "finite requested hydrogen consumption")
        remaining_h2 -= extent
        remaining_o2 -= .5*extent
        if remaining_h2 < 0. or remaining_o2 < 0.:
            raise ValueError("Closed staged schedule exceeds original finite H2 or O2 stock")
    completed = []
    stock, temperature = initial, initial.temperature_k
    def configuration():
        return recorded_content_sha256((
            initial, schedule, id(material_owner), id(thermal_owner),
            thermal_owner.boundary, thermal_owner.relative_tolerance,
            thermal_owner.absolute_tolerance, thermal_owner.energy_tolerance_j,
            id(thermal_owner.stack), temperature_projection,
        ))

    original_configuration = configuration()
    for command in schedule:
        thermal, material = None, None
        try:
            material_owner.require_current()
            if configuration() != original_configuration:
                raise ValueError("Original staged inputs or thermal owner configuration changed")
            thermal = thermal_owner.run(temperature, (command,))
            if configuration() != original_configuration:
                raise ValueError("Thermal callbacks changed the staged operation configuration")
            native_content = recorded_content_sha256((
                thermal, thermal.stages[0].native_result.t,
                thermal.stages[0].native_result.y,
            ))
            held = finite(temperature_projection(thermal, command), "projected held material temperature", positive=True)
            if recorded_content_sha256((thermal, thermal.stages[0].native_result.t,
                                         thermal.stages[0].native_result.y)) != native_content:
                raise ValueError("Temperature projection mutated the original thermal trajectory")
            if configuration() != original_configuration:
                raise ValueError("Temperature projection changed the staged operation configuration")
            samples = thermal.stages[0].native_result.y[0]
            if not min(samples) <= held <= max(samples):
                raise ValueError("Projected material temperature leaves accepted thermal sample range")
            material_command = FuelCellStep(
                command.identifier, command.start_s, command.end_s, clock_id, held,
                command.current_density_a_m2, command.faradaic_efficiency, projection_evidence_id,
            )
            material = material_owner.run(stock, (material_command,))
            if configuration() != original_configuration:
                raise ValueError("Material callbacks changed the staged operation configuration")
            held_generated = finite(
                material.steps[0].stack_result.unallocated_energy_rate_w
                *(command.end_s-command.start_s), "held-temperature generated stack heat")
            conditioning = finite(material.required_heat_into_j+held_generated,
                                  "finite material sensible conditioning heat")
            projection_difference = finite(thermal.generated_heat_j-held_generated,
                                           "temperature projection generated-heat difference")
            residual = finite(thermal.generated_heat_j+material.required_heat_into_j,
                              "thermal/material heat mismatch")
            if abs(residual) > budget:
                raise ValueError("Staggered heat mismatch exceeds the explicit per-stage budget")
            completed.append(StagedElectrochemicalStep(
                command, thermal, material, held, residual, held_generated,
                conditioning, projection_difference,
            ))
            stock, temperature = material.final, thermal.final_temperature_k
        except Exception as cause:
            raise StagedElectrochemicalError(
                cause, command=command, completed=completed,
                thermal_result=thermal, material_result=material,
            ) from cause
    token = object()
    _PENDING_STAGED_TRACE_TOKENS.add(token)
    try:
        result = StagedElectrochemicalTrace(
            thermal_owner, material_owner, initial, tuple(completed), temperature_projection,
            projection_evidence_id, refinement_identity, clock_id, budget,
            thermal_capacity_scope_evidence_id, _issuer_token=token,
        )
    except Exception:
        _PENDING_STAGED_TRACE_TOKENS.discard(token)
        raise
    return result.require_current()
