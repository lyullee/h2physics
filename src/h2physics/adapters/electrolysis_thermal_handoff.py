"""Post-run compatibility receipt for PV electrolysis and finite stack heat."""

from dataclasses import dataclass, field
import math

import numpy as np

from ..core import finite
from ..electrochemical_thermal import FiniteThermalStack, ThermalStackTrace
from .pv_electrolysis import PVElectrolysisTrace
from .result_provenance import recorded_content_sha256

_PENDING_RECEIPT_ISSUERS: set[object] = set()


def _issue_receipt_token():
    token = object()
    _PENDING_RECEIPT_ISSUERS.add(token)
    return token


def _signature(owner, trace):
    return recorded_content_sha256((
        owner.stack, owner.boundary, owner.relative_tolerance,
        owner.absolute_tolerance, owner.energy_tolerance_j,
        tuple((stage.command, stage.initial_temperature_k, stage.final_temperature_k,
               stage.generated_heat_j, stage.coolant_heat_out_j,
               stage.auxiliary_heat_into_j, stage.internal_energy_change_j,
               stage.energy_residual_j, stage.initial_stack_result,
               stage.final_stack_result, np.asarray(stage.native_result.t),
               np.asarray(stage.native_result.y)) for stage in trace.stages),
        trace.initial_temperature_k, trace.final_temperature_k,
        trace.generated_heat_j, trace.coolant_heat_out_j,
        trace.auxiliary_heat_into_j, trace.internal_energy_change_j,
        trace.energy_residual_j,
    ))


@dataclass(frozen=True, slots=True)
class ElectrolysisThermalReceipt:
    """Bind completed PV electrolysis and thermal traces without coupling solvers."""

    thermal_owner: FiniteThermalStack
    thermal_trace: ThermalStackTrace
    electrolysis_trace: PVElectrolysisTrace
    clock_id: str
    evidence_id: str
    temperature_tolerance_k: float
    energy_tolerance_j: float
    generated_heat_residual_j: float
    _signature: str
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _integrity_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_RECEIPT_ISSUERS:
            raise TypeError("Create electrolysis thermal receipts only through the binding API")
        _PENDING_RECEIPT_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_integrity_seal", self._content_seal())

    def _content_seal(self):
        return recorded_content_sha256((
            id(self.thermal_owner), id(self.thermal_trace), id(self.electrolysis_trace),
            self.clock_id, self.evidence_id, self.temperature_tolerance_k,
            self.energy_tolerance_j, self.generated_heat_residual_j, self._signature,
        ))

    def require_current(self):
        if not self._integrity_seal or self._content_seal() != self._integrity_seal:
            raise ValueError("Electrolysis thermal receipt identity, evidence or ledger changed")
        self.electrolysis_trace.require_current()
        if _signature(self.thermal_owner, self.thermal_trace) != self._signature:
            raise ValueError("Original electrolysis thermal trajectory or owner changed")
        residual = _admit(self.thermal_owner, self.thermal_trace, self.electrolysis_trace,
                          self.clock_id, self.temperature_tolerance_k, self.energy_tolerance_j)
        if residual != self.generated_heat_residual_j:
            raise ValueError("Electrolysis thermal receipt heat ledger changed")
        return self


def _admit(owner, thermal, electrolysis, clock_id, temperature_tolerance, energy_tolerance):
    if type(owner) is not FiniteThermalStack or type(thermal) is not ThermalStackTrace:
        raise TypeError("Retain the actual finite thermal stack owner and result")
    if type(electrolysis) is not PVElectrolysisTrace:
        raise TypeError("Retain an original finite PV electrolysis result")
    electrolysis.require_current()
    thermal.require_current()
    if thermal._source_owner is not owner:
        raise ValueError("Thermal trace must be issued by the exact admitted stack owner")
    if owner.stack is not electrolysis.stack:
        raise ValueError("Thermal and PV operation must share the exact electrochemical stack")
    if clock_id != electrolysis.evidence.clock_id:
        raise ValueError("Thermal clock declaration differs from the PV electrolysis clock")
    if owner.boundary.reference_id != electrolysis.caloric_provider.basis_id:
        raise ValueError("Thermal and PV operation caloric references differ")
    if len(thermal.stages) != len(electrolysis.steps) or not thermal.stages:
        raise ValueError("Match every thermal stage to one original PV electrolysis interval")
    for thermal_stage, production_step in zip(thermal.stages, electrolysis.steps, strict=True):
        command, pv_point = thermal_stage.command, production_step.point
        pv_stage = pv_point.stage
        expected_current_density = pv_point.stack.current_a / owner.stack.geometry.active_area_m2
        if (command.mode != "electrolysis" or command.start_s != pv_stage.start_s
                or command.end_s != pv_stage.end_s or pv_stage.clock_id != clock_id
                or not math.isclose(command.current_density_a_m2, expected_current_density,
                                    rel_tol=1e-12, abs_tol=1e-12)
                or command.faradaic_efficiency != 1.0):
            raise ValueError("Thermal/PV held commands differ in mode, clock, interval or current")
        native = thermal_stage.native_result
        times, values = np.asarray(native.t), np.asarray(native.y)
        if (not native.success or times.ndim != 1 or values.shape != (3, times.size)
                or not np.all(np.isfinite(values)) or times.size < 2
                or times[0] != command.start_s or times[-1] != command.end_s
                or np.any(np.diff(times) <= 0)):
            raise ValueError("Retain a complete successful thermal trajectory")
        if (abs(thermal_stage.initial_temperature_k-pv_stage.stack_temperature_k)
                > temperature_tolerance
                or np.max(np.abs(values[0]-pv_stage.stack_temperature_k)) > temperature_tolerance):
            raise ValueError("Thermal trajectory exceeds its declared PV-temperature compatibility budget")
        if (thermal_stage.initial_stack_result.mode != "electrolysis"
                or thermal_stage.final_stack_result.mode != "electrolysis"
                or thermal_stage.initial_stack_result.reaction_energy.reference_id
                != electrolysis.caloric_provider.basis_id
                or thermal_stage.initial_stack_result.reaction_energy.water_phase
                != production_step.point.stack.reaction_energy.water_phase):
            raise ValueError("Thermal trace does not retain the compatible electrolysis thermochemistry")
        if abs(thermal_stage.generated_heat_j-production_step.stack_heat_rejected_j) > energy_tolerance:
            raise ValueError("Thermal generated heat differs from the PV stack heat ledger")
    residual = thermal.generated_heat_j-math.fsum(
        step.stack_heat_rejected_j for step in electrolysis.steps
    )
    if not math.isclose(residual, 0., rel_tol=0., abs_tol=energy_tolerance):
        raise ValueError("Whole-operation electrolysis heat does not close")
    return residual


def bind_electrolysis_thermal_operation(
    thermal_owner, thermal_trace, electrolysis_trace, *, clock_id, evidence_id,
    temperature_tolerance_k, energy_tolerance_j,
):
    """Admit two completed compatible runs; no thermal feedback is introduced."""
    if any(not isinstance(value, str) or not value.strip() for value in (clock_id, evidence_id)):
        raise ValueError("Declare shared-clock and approximation evidence")
    temperature = finite(temperature_tolerance_k, "temperature tolerance", positive=True)
    energy = finite(energy_tolerance_j, "energy tolerance", positive=True)
    residual = _admit(thermal_owner, thermal_trace, electrolysis_trace,
                      clock_id, temperature, energy)
    return ElectrolysisThermalReceipt(
        thermal_owner, thermal_trace, electrolysis_trace, clock_id, evidence_id,
        temperature, energy, residual, _signature(thermal_owner, thermal_trace),
        _issue_receipt_token(),
    )


__all__ = ["ElectrolysisThermalReceipt", "bind_electrolysis_thermal_operation"]
