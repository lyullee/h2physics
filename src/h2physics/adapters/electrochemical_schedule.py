"""Finite closed-reactant schedule preparation using existing model owners.

Held material temperature and independent finite thermal evolution remain an
explicit approximation checked by electrochemical_operation. No new thermal
feedback solver or reactant depletion event is introduced.
"""

from dataclasses import dataclass, field, replace
from types import MappingProxyType

import numpy as np

from ..constants import FARADAY_C_MOL
from ..core import finite
from ..electrochemical_thermal import FiniteThermalStack, ThermalStackStage
from ..thermochemical import ThermochemicalInventory
from .electrochemical_operation import (
    ElectrochemicalOperationReceipt,
    bind_electrochemical_operation,
)
from .fuel_cell import FiniteFuelCell, FuelCellStep
from .result_provenance import recorded_content_sha256


@dataclass(frozen=True, slots=True)
class ElectrochemicalScheduleComparison:
    coarse: ElectrochemicalOperationReceipt
    fine: ElectrochemicalOperationReceipt
    refinement_identity: str
    normalizations: MappingProxyType
    signed_changes: MappingProxyType
    normalized_changes: MappingProxyType
    threshold: float
    within_threshold: bool
    _seal: str = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.coarse), id(self.fine), self.refinement_identity,
            self.normalizations, self.signed_changes, self.normalized_changes,
            self.threshold, self.within_threshold,
        ))

    def require_current(self):
        if self._content() != self._seal:
            raise ValueError("Refinement threshold, normalization or retained result changed")
        repeated = compare_electrochemical_schedules(
            self.coarse, self.fine, refinement_identity=self.refinement_identity,
            normalizations=self.normalizations, threshold=self.threshold,
        )
        if (dict(repeated.signed_changes) != dict(self.signed_changes)
                or dict(repeated.normalized_changes) != dict(self.normalized_changes)
                or repeated.within_threshold != self.within_threshold):
            raise ValueError("Refinement comparison no longer reproduces its retained changes")
        return self


def compare_electrochemical_schedules(coarse, fine, *, refinement_identity,
                                      normalizations, threshold):
    """Report nested held-schedule output changes, never a numerical error bound.

    Normalizations are positive caller scales in mol, J and K for the named
    outputs. Maximum temperature is the maximum retained native sample only.
    Coarse and fine commands must describe the same piecewise-constant forcing.
    """
    for result in (coarse, fine):
        if type(result) is not ElectrochemicalOperationReceipt:
            raise TypeError("Compare original admitted electrochemical operation receipts")
        result.require_current()
    if not isinstance(refinement_identity, str) or not refinement_identity.strip():
        raise ValueError("Declare the shared schedule refinement identity")
    if any(not result.evidence_id.endswith(":"+refinement_identity) for result in (coarse, fine)):
        raise ValueError("Both operation receipts must declare this same refinement identity")
    a, b = coarse.fuel_cell_trace, fine.fuel_cell_trace
    if (a.stack is not b.stack or coarse.clock_id != fine.clock_id
            or a.initial != b.initial or coarse.thermal_owner.boundary is not fine.thermal_owner.boundary):
        raise ValueError("Refinement requires a shared stack, initial stock, clock and thermal boundary")
    coarse_edges = (a.steps[0].command.start_s, *(step.command.end_s for step in a.steps))
    fine_edges = (b.steps[0].command.start_s, *(step.command.end_s for step in b.steps))
    if (coarse_edges[0] != fine_edges[0] or coarse_edges[-1] != fine_edges[-1]
            or not set(coarse_edges).issubset(fine_edges) or len(fine_edges) <= len(coarse_edges)):
        raise ValueError("Fine schedule must strictly refine the same finite window")
    for step, thermal in zip(b.steps, fine.thermal_trace.stages, strict=True):
        start, end = step.command.start_s, step.command.end_s
        matches = [(old, heat) for old, heat in zip(a.steps, coarse.thermal_trace.stages, strict=True)
                   if old.command.start_s <= start and end <= old.command.end_s]
        if len(matches) != 1:
            raise ValueError("Every fine interval must lie inside one coarse held interval")
        old, heat = matches[0]
        if ((step.command.current_density_a_m2, step.command.temperature_k,
             thermal.command.coolant_temperature_k, thermal.command.auxiliary_heat_into_w)
                != (old.command.current_density_a_m2, old.command.temperature_k,
                    heat.command.coolant_temperature_k, heat.command.auxiliary_heat_into_w)):
            raise ValueError("Refinement cannot change held current, temperature or coolant forcing")

    def outputs(result):
        material, thermal = result.fuel_cell_trace, result.thermal_trace
        return dict(hydrogen_consumed_mol=material.hydrogen_consumed_mol,
                    electricity_into_j=material.electricity_into_j,
                    required_heat_into_j=material.required_heat_into_j,
                    coolant_heat_out_j=thermal.coolant_heat_out_j,
                    maximum_sampled_temperature_k=max(
                        float(np.max(stage.native_result.y[0])) for stage in thermal.stages))

    left, right = outputs(coarse), outputs(fine)
    if set(normalizations) != set(left):
        raise ValueError("Provide one explicit physical normalization per comparison output")
    scales = {key: finite(value, key+" normalization", positive=True)
              for key, value in normalizations.items()}
    limit = finite(threshold, "normalized change threshold", positive=True)
    changes = {key: right[key]-left[key] for key in left}
    normalized = {key: abs(changes[key])/scales[key] for key in left}
    return ElectrochemicalScheduleComparison(
        coarse, fine, refinement_identity, MappingProxyType(scales),
        MappingProxyType(changes), MappingProxyType(normalized), limit,
        all(value <= limit for value in normalized.values()),
    )


class ElectrochemicalScheduleError(RuntimeError):
    def __init__(self, cause, *, schedule, stage, material_result=None, thermal_result=None):
        super().__init__(str(cause))
        self.cause = cause
        self.schedule = schedule
        self.stage = stage
        self.material_result = material_result
        self.thermal_result = thermal_result


@dataclass(frozen=True, slots=True)
class ClosedFuelCellSchedule:
    material_owner: FiniteFuelCell
    thermal_owner: FiniteThermalStack
    initial: ThermochemicalInventory
    material_steps: tuple[FuelCellStep, ...]
    thermal_stages: tuple[ThermalStackStage, ...]
    refinement_identity: str
    approximation_evidence_id: str
    temperature_tolerance_k: float
    energy_tolerance_j: float
    _input_signature: str
    _configuration_signature: str = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_configuration_signature", self._configuration())

    def _configuration(self):
        return recorded_content_sha256((
            id(self.material_owner), id(self.thermal_owner), self.thermal_owner.boundary,
            self.thermal_owner.relative_tolerance, self.thermal_owner.absolute_tolerance,
            self.thermal_owner.energy_tolerance_j, self.refinement_identity,
            self.approximation_evidence_id, self.temperature_tolerance_k,
            self.energy_tolerance_j,
        ))

    def require_current(self):
        self.material_owner.require_current()
        if self._configuration() != self._configuration_signature:
            raise ValueError("Prepared approximation budget or thermal configuration changed")
        if recorded_content_sha256((self.initial, self.material_steps,
                                     self.thermal_stages)) != self._input_signature:
            raise ValueError("Prepared closed-reactant schedule inputs changed")
        if self.thermal_owner.stack is not self.material_owner.stack:
            raise ValueError("Prepared thermal/material stack identity changed")
        return self

    def run(self):
        """Run both existing owners and admit their declared held approximation.

        The returned operation receipt retains original model outputs. A failed
        second owner preserves the successfully completed first owner result.
        """
        material, thermal = None, None
        stage = "schedule admission"
        try:
            self.require_current()
            stage = "finite reactant operation"
            material = self.material_owner.run(self.initial, self.material_steps)
            stage = "finite thermal operation"
            thermal = self.thermal_owner.run(self.initial.temperature_k, self.thermal_stages)
            self.require_current()
            stage = "held-temperature approximation admission"
            return bind_electrochemical_operation(
                self.thermal_owner, thermal, material,
                clock_id=self.material_owner.evidence.clock_id,
                evidence_id=self.approximation_evidence_id+":"+self.refinement_identity,
                temperature_tolerance_k=self.temperature_tolerance_k,
                energy_tolerance_j=self.energy_tolerance_j,
            )
        except Exception as cause:
            raise ElectrochemicalScheduleError(
                cause, schedule=self, stage=stage,
                material_result=material, thermal_result=thermal,
            ) from cause


def prepare_closed_fuel_cell_schedule(material_owner, thermal_owner, initial, *,
                                      material_steps, thermal_stages,
                                      refinement_identity, approximation_evidence_id,
                                      temperature_tolerance_k, energy_tolerance_j):
    """Check closed finite stocks and prepare original owner calls without running.

    Finite feeds and withdrawals require their existing source-event binding
    API and are intentionally rejected here. Unity Faradaic efficiency gives
    exact H2/O2/H2O stoichiometry for preflight resource accounting.
    """
    if type(material_owner) is not FiniteFuelCell or type(thermal_owner) is not FiniteThermalStack:
        raise TypeError("Supply original finite material and thermal owners")
    if type(initial) is not ThermochemicalInventory:
        raise TypeError("Supply the finite initial reactant inventory")
    material_owner.require_current()
    if material_owner.stack is not thermal_owner.stack:
        raise ValueError("Both operation owners must share the exact stack")
    if (initial.pressure_pa != material_owner.boundary.pressure_pa
            or initial.energy_basis_id != material_owner.kernel.energy_basis_id
            or thermal_owner.boundary.reference_id != initial.energy_basis_id
            or thermal_owner.boundary.coolant_boundary_id != material_owner.boundary.thermal_boundary_id):
        raise ValueError("Initial pressure, thermal boundary and material energy reference must agree")
    if not (thermal_owner.boundary.temperature_bounds_k[0] <= initial.temperature_k
            <= thermal_owner.boundary.temperature_bounds_k[1]):
        raise ValueError("Initial stack temperature is outside the thermal owner domain")
    for value in (refinement_identity, approximation_evidence_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Declare schedule refinement and held-approximation identities")
    material, thermal = tuple(material_steps), tuple(thermal_stages)
    if not material or len(material) != len(thermal):
        raise ValueError("Pair every finite material step with one held thermal stage")
    remaining_h2 = initial.amounts_mol.get(material_owner.hydrogen_id, 0.)
    remaining_o2 = initial.amounts_mol.get(material_owner.oxygen_id, 0.)
    previous_end = None
    identities = set()
    geometry = material_owner.stack.geometry
    for step, command in zip(material, thermal, strict=True):
        if type(step) is not FuelCellStep or type(command) is not ThermalStackStage:
            raise TypeError("Use original typed fuel-cell and thermal commands")
        replace(step)
        replace(command)
        if step.feeds or step.pre_withdrawal_mol:
            raise ValueError("Closed schedule cannot admit external feeds or withdrawals")
        if (step.identifier in identities or step.clock_id != material_owner.evidence.clock_id
                or (previous_end is not None and step.start_s != previous_end)):
            raise ValueError("Schedule identities and contiguous material clock must agree")
        identities.add(step.identifier)
        previous_end = step.end_s
        if (command.mode != "fuel_cell" or command.start_s != step.start_s
                or command.end_s != step.end_s
                or command.current_density_a_m2 != step.current_density_a_m2
                or command.faradaic_efficiency != step.faradaic_efficiency):
            raise ValueError("Paired commands differ in held current, mode or time window")
        lower, upper = material_owner.boundary.temperature_bounds_k
        if (not lower <= step.temperature_k <= upper
                or step.current_density_a_m2 > material_owner.boundary.maximum_current_density_a_m2):
            raise ValueError("Finite command exceeds material stack temperature/current limits")
        extent = (step.current_density_a_m2*geometry.active_area_m2*geometry.series_cells
                  *(step.end_s-step.start_s)/(2*FARADAY_C_MOL))
        finite(extent, "finite schedule hydrogen extent")
        remaining_h2 -= extent
        remaining_o2 -= .5*extent
        if remaining_h2 < 0. or remaining_o2 < 0.:
            raise ValueError("Requested schedule exceeds the finite H2 or O2 stock")
    return ClosedFuelCellSchedule(
        material_owner, thermal_owner, initial, material, thermal,
        refinement_identity, approximation_evidence_id,
        finite(temperature_tolerance_k, "temperature approximation budget", positive=True),
        finite(energy_tolerance_j, "energy approximation budget", positive=True),
        recorded_content_sha256((initial, material, thermal)),
    )
