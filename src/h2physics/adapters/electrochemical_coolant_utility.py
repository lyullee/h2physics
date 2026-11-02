"""Original finite coolant external and internal heat observations.

Signed external heat is a physical boundary duty, not a purchase or recovery
claim. Stack-to-coolant heat remains an already settled internal transfer.
"""

from dataclasses import dataclass

from ..electrochemical_thermal import FiniteCoolantStackTrace
from .thermal_utilities import HeatComponent, HeatSnapshot, HeatWindow


@dataclass(frozen=True, slots=True)
class ElectrochemicalCoolantHeatAdapter:
    boundary_kind: str
    scope_evidence_id: str
    identifier: str = "original-finite-electrochemical-coolant-heat"

    def __post_init__(self):
        if self.boundary_kind not in {"external-coolant", "internal-stack-to-coolant"}:
            raise ValueError("Select external coolant heat or already settled internal exchange")
        if not isinstance(self.scope_evidence_id, str) or not self.scope_evidence_id.strip():
            raise ValueError("Declare the heat boundary scope evidence")

    def snapshot(self, source, window):
        if type(source) is not FiniteCoolantStackTrace or type(window) is not HeatWindow:
            raise TypeError("Retain the original finite coolant trace and heat window")
        source.require_current()
        stages = source.stages
        if (not stages or window.clock_id != source.reservoir.clock_id
                or window.start_s != stages[0].command.start_s
                or window.end_s != stages[-1].command.end_s
                or any(a.command.end_s != b.command.start_s
                       for a, b in zip(stages, stages[1:]))):
            raise ValueError("Heat duty must retain the exact original finite coolant clock and window")
        if any(stage.initial_coolant_state is None or stage.final_coolant_state is None
               for stage in stages):
            raise ValueError("Every coolant heat interval must retain both coolant endpoints")
        for stage in stages:
            source.reservoir.properties.basis.require_compatible(
                stage.initial_coolant_state.basis
            )
            source.reservoir.properties.basis.require_compatible(
                stage.final_coolant_state.basis
            )
        internal = self.boundary_kind == "internal-stack-to-coolant"
        heat = tuple(stage.coolant_heat_out_j if internal else stage.external_coolant_heat_j
                     for stage in stages)
        owner = source.owner if internal else source.reservoir
        temperatures = tuple((stage.initial_coolant_state.temperature_k,
                              stage.final_coolant_state.temperature_k) for stage in stages)
        result = HeatSnapshot(
            source=source, window=window,
            source_id=source.reservoir.boundary_id+":"+self.boundary_kind,
            boundary_id=source.reservoir.boundary_id+":"+self.boundary_kind,
            energy_basis_id=source.reservoir.properties.basis.reference_id,
            edges_s=(stages[0].command.start_s, *(stage.command.end_s for stage in stages)),
            heat_into_process_j=heat,
            components=(HeatComponent(owner, self.boundary_kind),),
            reported_temperature_k=temperatures,
            scope="internal-transfer" if internal else "external-device-heat",
            evidence_ids=(self.scope_evidence_id, source.reservoir.evidence_id, window.evidence_id),
            original_objects=(source.owner, source.reservoir, source.reservoir.properties, *stages),
            verification_scope=(
                "original shared-RHS coolant boundary heat; endpoint temperature observations only; "
                "no purchased utility, recovery availability, COP or independent thermal validation"
            ),
        )
        source.require_current()
        return result


__all__ = ["ElectrochemicalCoolantHeatAdapter"]
