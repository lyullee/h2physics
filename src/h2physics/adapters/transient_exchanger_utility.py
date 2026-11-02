"""Original transient flowing exchanger interwall heat observation.

The native exchanger has already exchanged this heat internally. These duty
profiles carry ``internal-transfer`` scope and cannot be treated as an external
heater/chiller demand or a newly available recoverable heat stream.
"""

from dataclasses import dataclass

import numpy as np

from .lh2dt_transient_flowing_exchanger import TransientFlowingExchangerTrace
from .thermal_utilities import HeatComponent, HeatSnapshot, HeatWindow


@dataclass(frozen=True, slots=True)
class TransientExchangerInterwallHeatAdapter:
    side_id: str
    evidence_id: str
    identifier: str = "original-native-transient-flowing-interwall-heat"

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.side_id, self.evidence_id, self.identifier)):
            raise ValueError("Declare exact native side and interwall observation evidence")

    def snapshot(self, source, window):
        """Expose original per-side accepted interwall integrals over one full run.

        Wall temperatures are retained as endpoint observations, not qualified
        passive-exchange temperature levels. No recoverability or availability
        follows from this trace adapter.
        """
        if type(source) is not TransientFlowingExchangerTrace or type(window) is not HeatWindow:
            raise TypeError("Supply the original transient exchanger trace and heat window")
        source.require_current()
        rows = source.points
        if (not rows or window.clock_id != source.clock_id
                or window.start_s != rows[0].time_s or window.end_s != rows[-1].time_s):
            raise ValueError("Heat window must match the exact original transient run and clock")
        base = source.owner.finite_owner
        candidates = tuple((index, side) for index, side in enumerate((base.left, base.right))
                           if side.side_id == self.side_id)
        if len(candidates) != 1:
            raise ValueError("Select exactly one original native exchanger side")
        index, side = candidates[0]
        state_name, ledger_name = (("left", "left_ledgers"), ("right", "right_ledgers"))[index]
        cumulative = np.asarray([getattr(row.native_state, ledger_name)[2] for row in rows])
        temperatures = tuple((getattr(a.native_state, state_name).wall_temperature_K,
                              getattr(b.native_state, state_name).wall_temperature_K)
                             for a, b in zip(rows, rows[1:]))
        result = HeatSnapshot(
            source=source, window=window, source_id=side.initial_source_id,
            boundary_id=side.side_id+":interwall",
            energy_basis_id=side.bridge.basis.reference_id,
            edges_s=np.asarray([row.time_s for row in rows]),
            heat_into_process_j=np.diff(cumulative),
            components=(HeatComponent(side.native_component, "interwall-heat-port"),),
            reported_temperature_k=temperatures, scope="internal-transfer",
            evidence_ids=(self.evidence_id, source.boundary_evidence_id, window.evidence_id),
            original_objects=(source.owner, base, side, side.native_component,
                              source.native_simulator, *rows),
            verification_scope=(
                "original simultaneous flowing hold-up interwall integral already settled; "
                "endpoint wall temperatures only; no external utility or recoverability credit"
            ),
        )
        source.require_current()
        return result


__all__ = ["TransientExchangerInterwallHeatAdapter"]
