"""Accepted-edge relief withdrawal accounting over the existing relief/nozzle owners.

This module does not choose a pickup phase, solve flow, or advance a vessel. It
integrates two adjacent owner-issued endpoint rates under an explicit linear
rate assumption and checks the caller's finite phase inventory balance.
"""

from dataclasses import dataclass

from ..core import finite
from .relief_lift import FiniteLiftRelief, ReliefLiftResult


@dataclass(frozen=True, slots=True)
class ReliefWithdrawalReceipt:
    """One phase-specific accepted-edge withdrawal and inventory balance."""

    start_time_s: float
    end_time_s: float
    clock_id: str
    phase_id: str
    selection_id: str
    start_state_id: str
    end_state_id: str
    mass_withdrawn_kg: float
    enthalpy_withdrawn_j: float
    phase_mass_before_kg: float
    other_phase_inventory_change_kg: float
    phase_mass_after_kg: float
    mass_balance_residual_kg: float
    quadrature_id: str
    evidence_id: str


def integrate_relief_withdrawal_edge(
    owner: FiniteLiftRelief,
    left: ReliefLiftResult,
    right: ReliefLiftResult,
    *,
    other_phase_inventory_change_kg: float,
    evidence_id: str,
    balance_tolerance_kg: float = 1e-10,
) -> ReliefWithdrawalReceipt:
    """Integrate one adjacent accepted edge with linear endpoint-rate quadrature.

    `other_phase_inventory_change_kg` is the caller's signed net addition to
    this selected phase over the edge, excluding relief withdrawal. The supplied
    endpoint phase inventories must close the resulting balance. Phase switching
    within an edge is rejected because two different streams cannot support this
    quadrature. The linear interpolation is an explicit numerical assumption,
    not native solver quadrature or a continuous depletion event locator.
    """
    if type(owner) is not FiniteLiftRelief:
        raise TypeError("Use the existing FiniteLiftRelief owner")
    if type(left) is not ReliefLiftResult or type(right) is not ReliefLiftResult:
        raise TypeError("Both edge endpoints must be original relief-lift results")
    owner.require_current(left)
    owner.require_current(right)
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Accepted-edge quadrature and inventory evidence are required")
    tolerance = finite(balance_tolerance_kg, "balance tolerance", positive=True)
    other_change = finite(other_phase_inventory_change_kg,
                          "other phase inventory change")

    t0, t1 = left.state.time_s, right.state.time_s
    dt = finite(t1 - t0, "accepted relief interval", positive=True)
    if left.state.clock_id != right.state.clock_id:
        raise ValueError("Relief edge endpoints must use the same explicit clock")
    if (right.interval_start_s != t0 or right.interval_end_s != t1
            or left.interval_end_s != t0):
        raise ValueError("Relief results must be adjacent accepted endpoints")
    if (left.source_owner_id != right.source_owner_id
            or left.native_relief_origin is not right.native_relief_origin):
        raise ValueError("Relief endpoints must retain the same physical source owners")
    p0, p1 = left.pickup, right.pickup
    if (p0.phase_id != p1.phase_id or p0.selection_id != p1.selection_id):
        raise ValueError("Phase or pickup selection changed within one accepted edge")
    if left.state.demanded_open != right.state.demanded_open:
        raise ValueError("A relief set/reseat transition requires an edge split before quadrature")
    if p0.state_id == p1.state_id:
        raise ValueError("Accepted tank endpoint state identities must be distinct")
    left.downstream.basis.require_compatible(right.downstream.basis)

    mass_rate_0 = finite(left.mass_flow_kg_s, "left endpoint mass rate")
    mass_rate_1 = finite(right.mass_flow_kg_s, "right endpoint mass rate")
    if mass_rate_0 < 0 or mass_rate_1 < 0:
        raise ValueError("Relief withdrawal rates cannot reverse in this ledger")
    energy_rate_0 = finite(left.enthalpy_flow_w, "left endpoint enthalpy rate")
    energy_rate_1 = finite(right.enthalpy_flow_w, "right endpoint enthalpy rate")
    withdrawn = .5 * (mass_rate_0 + mass_rate_1) * dt
    energy = .5 * (energy_rate_0 + energy_rate_1) * dt
    before = finite(p0.available_mass_kg, "phase mass before")
    after = finite(p1.available_mass_kg, "phase mass after")
    if before < 0 or after < 0:
        raise ValueError("Accepted phase inventories cannot be negative")
    predicted_after = before + other_change - withdrawn
    residual = after - predicted_after
    allowed = max(tolerance, 1e-12 * max(before, after, withdrawn, 1.))
    if predicted_after < -allowed:
        raise ValueError("Accepted-edge relief withdrawal exceeds available phase inventory")
    if abs(residual) > allowed:
        raise ValueError("Accepted phase inventory does not close with relief withdrawal")

    return ReliefWithdrawalReceipt(
        start_time_s=t0, end_time_s=t1, clock_id=left.state.clock_id,
        phase_id=p0.phase_id, selection_id=p0.selection_id,
        start_state_id=p0.state_id, end_state_id=p1.state_id,
        mass_withdrawn_kg=withdrawn, enthalpy_withdrawn_j=energy,
        phase_mass_before_kg=before,
        other_phase_inventory_change_kg=other_change,
        phase_mass_after_kg=after, mass_balance_residual_kg=residual,
        quadrature_id="linear-endpoint-trapezoid-v1", evidence_id=evidence_id,
    )
