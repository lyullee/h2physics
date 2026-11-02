"""Admit an isothermal finite fuel-cell run against an existing thermal run.

This composes completed results; temperature feedback and reactant depletion
events are still owned by their original solvers. No trajectory is integrated here.
"""

from dataclasses import dataclass
from math import fsum, isclose

import numpy as np

from ..core import finite
from ..electrochemical_thermal import FiniteThermalStack, ThermalStackTrace
from .fuel_cell import FuelCellTrace
from .result_provenance import recorded_content_sha256


def _thermal_signature(trace):
    return recorded_content_sha256(tuple(
        (stage.command, stage.initial_temperature_k, stage.final_temperature_k,
         stage.generated_heat_j, stage.coolant_heat_out_j, stage.auxiliary_heat_into_j,
         stage.internal_energy_change_j, stage.energy_residual_j,
         stage.initial_stack_result, stage.final_stack_result,
         np.asarray(stage.native_result.t), np.asarray(stage.native_result.y))
        for stage in trace.stages
    ))


@dataclass(frozen=True, slots=True)
class ElectrochemicalOperationReceipt:
    thermal_owner: FiniteThermalStack
    thermal_trace: ThermalStackTrace
    fuel_cell_trace: FuelCellTrace
    clock_id: str
    evidence_id: str
    temperature_tolerance_k: float
    energy_tolerance_j: float
    generated_heat_residual_j: float
    _signature: str

    def require_current(self):
        self.fuel_cell_trace.require_current()
        if _thermal_signature(self.thermal_trace) != self._signature:
            raise ValueError("Original electrochemical thermal trajectory changed")
        _admit(self.thermal_owner, self.thermal_trace, self.fuel_cell_trace,
               self.clock_id, self.temperature_tolerance_k, self.energy_tolerance_j)
        return self


def _admit(owner, thermal, material, clock_id, temperature_tolerance, energy_tolerance):
    if type(owner) is not FiniteThermalStack or type(thermal) is not ThermalStackTrace:
        raise TypeError("Retain the actual finite thermal owner and its trace")
    if type(material) is not FuelCellTrace:
        raise TypeError("Retain an original finite fuel-cell trace")
    material.require_current()
    if owner.stack is not material.stack:
        raise ValueError("Thermal and material operation must share the exact stack")
    if clock_id != material.evidence.clock_id:
        raise ValueError("Thermal clock declaration differs from the material clock")
    if owner.boundary.coolant_boundary_id != material.boundary.thermal_boundary_id:
        raise ValueError("Declare the same thermal boundary on both model owners")
    if owner.boundary.reference_id != material.initial.energy_basis_id:
        raise ValueError("Thermal and finite material energy references differ")
    if len(thermal.stages) != len(material.steps) or not thermal.stages:
        raise ValueError("Match every held thermal stage to one finite material step")
    for thermal_stage, material_step in zip(thermal.stages, material.steps, strict=True):
        command, step = thermal_stage.command, material_step.command
        if (command.mode != "fuel_cell" or command.start_s != step.start_s
                or command.end_s != step.end_s or step.clock_id != clock_id
                or command.current_density_a_m2 != step.current_density_a_m2
                or command.faradaic_efficiency != step.faradaic_efficiency):
            raise ValueError("Thermal/material held commands differ in mode, clock or current")
        native = thermal_stage.native_result
        times, values = np.asarray(native.t), np.asarray(native.y)
        if (not native.success or times.ndim != 1 or values.shape != (3, times.size)
                or not np.all(np.isfinite(values)) or times.size < 2
                or times[0] != command.start_s or times[-1] != command.end_s
                or np.any(np.diff(times) <= 0)):
            raise ValueError("Retain a complete successful thermal trajectory")
        if np.max(np.abs(values[0]-step.temperature_k)) > temperature_tolerance:
            raise ValueError("Material step is isothermal; thermal trajectory exceeds its declared approximation")
        for observed, retained in (
            (values[0, 0], thermal_stage.initial_temperature_k),
            (values[0, -1], thermal_stage.final_temperature_k),
            (values[1, -1], thermal_stage.generated_heat_j),
            (values[2, -1], thermal_stage.coolant_heat_out_j),
        ):
            if observed != retained:
                raise ValueError("Thermal summary differs from its retained native trajectory")
        for result in (thermal_stage.initial_stack_result, thermal_stage.final_stack_result):
            if (result.reaction_energy.reference_id != material_step.stack_result.reaction_energy.reference_id
                    or result.reaction_energy.water_phase != material.boundary.water_phase):
                raise ValueError("Thermal/material reaction energy reference or water phase differs")
        if abs(thermal_stage.generated_heat_j+material_step.required_heat_into_j) > energy_tolerance:
            raise ValueError("Thermal generated heat and finite material heat duty disagree")
    if thermal.generated_heat_j != fsum(stage.generated_heat_j for stage in thermal.stages):
        raise ValueError("Whole-operation thermal heat differs from its stage ledger")
    residual = thermal.generated_heat_j+material.required_heat_into_j
    if not isclose(residual, 0., rel_tol=0., abs_tol=energy_tolerance):
        raise ValueError("Whole-operation generated heat does not close")
    return residual


def bind_electrochemical_operation(thermal_owner, thermal_trace, fuel_cell_trace, *,
                                   clock_id, evidence_id, temperature_tolerance_k,
                                   energy_tolerance_j):
    """Bind compatible near-isothermal runs with explicit approximation budgets.

    The caller supplies the thermal trace clock because the thermal API has no
    clock field. This is post-run admission, not coupled temperature feedback.
    """
    if any(not isinstance(value, str) or not value.strip() for value in (clock_id, evidence_id)):
        raise ValueError("Declare a shared clock and approximation evidence")
    temperature = finite(temperature_tolerance_k, "temperature tolerance", positive=True)
    energy = finite(energy_tolerance_j, "energy tolerance", positive=True)
    residual = _admit(thermal_owner, thermal_trace, fuel_cell_trace, clock_id, temperature, energy)
    return ElectrochemicalOperationReceipt(
        thermal_owner, thermal_trace, fuel_cell_trace, clock_id, evidence_id,
        temperature, energy, residual, _thermal_signature(thermal_trace),
    )
