"""Finite relief accepted-edge ledger to the shared dispersion source type.

This bridge introduces no relief flow, plume or property algorithm. It projects
only adjacent accepted endpoint quadratures that close against the finite phase
inventory, and requires an explicit single-state source enthalpy basis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256

import numpy as np

from ..core import Origin, ThermoState, finite
from ..release import SourceLocation
from ..sources import IntervalMassSource
from .relief_lift import FiniteLiftRelief, ReliefLiftResult
from .relief_withdrawal_ledger import (
    ReliefWithdrawalReceipt,
    integrate_relief_withdrawal_edge,
)

_ISSUED = object()
_PENDING = set()


def _seal(owner, points, receipts, source, projection_id):
    return sha256(repr((id(owner), tuple(map(id, points)), tuple(map(id, receipts)),
                        id(source), source._fingerprint, projection_id)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ReliefFiniteSourceHandoff:
    """Auditable relief source preserving exact accepted samples and interval totals."""

    owner: FiniteLiftRelief = field(repr=False, compare=False)
    points: tuple[ReliefLiftResult, ...] = field(repr=False, compare=False)
    withdrawals: tuple[ReliefWithdrawalReceipt, ...]
    source: IntervalMassSource
    projection_evidence_id: str
    enthalpy_residual_j: float
    enthalpy_tolerance_j: float
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal_value: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use relief_source_from_accepted_withdrawals")
        _PENDING.remove(self._issuer)
        if not isinstance(self.projection_evidence_id, str) or not self.projection_evidence_id.strip():
            raise ValueError("Declare why one source state represents the relief intervals")
        object.__setattr__(self, "_seal_value", _seal(
            self.owner, self.points, self.withdrawals, self.source, self.projection_evidence_id))

    def require_current(self):
        if type(self.owner) is not FiniteLiftRelief or type(self.source) is not IntervalMassSource:
            raise TypeError("Handoff must retain its original relief and finite-source owners")
        if (self.source is None or _seal(self.owner, self.points, self.withdrawals,
                self.source, self.projection_evidence_id) != self._seal_value):
            raise ValueError("Relief finite-source handoff identity or content changed")
        self.source.require_current()
        if len(self.points) != len(self.withdrawals) + 1 or len(self.withdrawals) < 1:
            raise ValueError("Retain one more accepted sample than withdrawal intervals")
        masses, energies = [], []
        for index, receipt in enumerate(self.withdrawals):
            left, right = self.points[index:index + 2]
            self.owner.require_current(left)
            self.owner.require_current(right)
            rebuilt = integrate_relief_withdrawal_edge(
                self.owner, left, right,
                other_phase_inventory_change_kg=receipt.other_phase_inventory_change_kg,
                evidence_id=receipt.evidence_id,
            )
            if rebuilt != receipt:
                raise ValueError("Withdrawal receipt no longer matches its native accepted edge")
            if receipt.clock_id != self.source.location.clock_id:
                raise ValueError("Relief edge and finite source clock identities differ")
            masses.append(receipt.mass_withdrawn_kg)
            energies.append(receipt.enthalpy_withdrawn_j)
        edges = [self.points[0].state.time_s, *(p.state.time_s for p in self.points[1:])]
        if (not np.array_equal(self.source.edges_s, edges)
                or not np.array_equal(self.source.mass_kg, masses)
                or self.source.state.basis != self.points[0].downstream.basis):
            raise ValueError("Finite-source bins, clock or property basis differ from accepted relief")
        if any(p.downstream.basis != self.source.state.basis or p.downstream.phase != self.source.state.phase
               for p in self.points):
            raise ValueError("A source-state phase change cannot be inferred at the handoff")
        expected_energy = self.source.total_mass_kg * self.source.state.enthalpy_j_kg
        if (self.enthalpy_residual_j != expected_energy - sum(energies)
                or abs(self.enthalpy_residual_j) > self.enthalpy_tolerance_j):
            raise ValueError("Representative source enthalpy does not close to relief ledger")
        if self._seal_value != _seal(self.owner, self.points, self.withdrawals,
                                     self.source, self.projection_evidence_id):
            raise ValueError("Relief finite-source receipt is stale")
        return self


def relief_source_from_accepted_withdrawals(
    owner: FiniteLiftRelief,
    points,
    withdrawals,
    *,
    location: SourceLocation,
    representative_state: ThermoState,
    origin: Origin,
    projection_evidence_id: str,
    end_reason: str = "window_end",
    enthalpy_tolerance_j: float = 1e-3,
) -> ReliefFiniteSourceHandoff:
    """Project closed accepted relief edges to ``IntervalMassSource``.

    ``points`` must be adjacent results issued by one relief owner and
    ``withdrawals`` their inventory-closing trapezoidal receipts. Because the
    common source schema has one thermodynamic state for all bins, the caller
    owns that state projection and must disclose its support. Integrated
    source enthalpy must match the accepted relief energy ledger within the
    explicit joule tolerance; no pressure drop, flashing or downstream plume is
    calculated here.
    """
    if type(owner) is not FiniteLiftRelief:
        raise TypeError("Supply the existing FiniteLiftRelief owner")
    points, withdrawals = tuple(points), tuple(withdrawals)
    if len(points) != len(withdrawals) + 1 or not withdrawals:
        raise ValueError("Supply a contiguous accepted point sequence and its edge receipts")
    if type(location) is not SourceLocation or type(representative_state) is not ThermoState:
        raise TypeError("Source location and representative thermodynamic state must be typed")
    if not isinstance(projection_evidence_id, str) or not projection_evidence_id.strip():
        raise ValueError("Representative-state projection needs caller evidence")
    tolerance = finite(enthalpy_tolerance_j, "enthalpy closure tolerance", positive=True)
    for i, receipt in enumerate(withdrawals):
        if type(receipt) is not ReliefWithdrawalReceipt:
            raise TypeError("Every accepted interval needs its original withdrawal receipt")
        owner.require_current(points[i])
        owner.require_current(points[i + 1])
        rebuilt = integrate_relief_withdrawal_edge(
            owner, points[i], points[i + 1],
            other_phase_inventory_change_kg=receipt.other_phase_inventory_change_kg,
            evidence_id=receipt.evidence_id,
        )
        if rebuilt != receipt:
            raise ValueError("Receipt does not match its adjacent owner-issued interval")
        if points[i].state.clock_id != points[i + 1].state.clock_id:
            raise ValueError("Relief points must use one clock")
        if points[i].downstream.basis != representative_state.basis:
            raise ValueError("Representative state must preserve the exact property basis")
        if points[i].downstream.phase != representative_state.phase:
            raise ValueError("Representative state must retain the relief outlet phase")
        if location.clock_id != receipt.clock_id:
            raise ValueError("Source location clock differs from relief accepted-edge clock")
    if len({p.source_owner_id for p in points}) != 1 or len({id(p.native_relief_origin) for p in points}) != 1:
        raise ValueError("All samples must belong to one unchanged physical relief owner")
    edges = [points[0].state.time_s, *(p.state.time_s for p in points[1:])]
    masses = [receipt.mass_withdrawn_kg for receipt in withdrawals]
    energies = [receipt.enthalpy_withdrawn_j for receipt in withdrawals]
    source = IntervalMassSource(
        location, edges, masses, representative_state, Origin(origin),
        projection_evidence_id.strip(), end_reason,
    )
    residual = source.total_mass_kg * representative_state.enthalpy_j_kg - sum(energies)
    if abs(residual) > tolerance:
        raise ValueError("Representative state fails accepted relief enthalpy closure")
    token = object()
    _PENDING.add(token)
    try:
        result = ReliefFiniteSourceHandoff(
            owner, points, withdrawals, source, projection_evidence_id.strip(),
            residual, tolerance, token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    return result.require_current()


__all__ = ["ReliefFiniteSourceHandoff", "relief_source_from_accepted_withdrawals"]



