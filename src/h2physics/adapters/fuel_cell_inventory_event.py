"""Positive-time reactant reserve events for the existing held-current owner.

Each command has fixed current and temperature. Faraday consumption is linear
inside that command; the accepted prefix is executed by FiniteFuelCell.run.
Instantaneous pre-withdrawals precede complete start-boundary feed packets.
This is not a root locator for the coupled native ReactorNet driver.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from ..constants import FARADAY_C_MOL
from ..core import finite
from ..thermochemical import ThermochemicalInventory
from .carrier_conversion import CarrierWithdrawal
from .fuel_cell import FiniteFuelCell, FuelCellStep, FuelCellTrace, FuelCellWithdrawal
from .result_provenance import recorded_content_sha256

_PENDING = set()


def _derive(owner, initial, commands, h2_reserve, o2_reserve, amount_tolerance):
    owner.require_current()
    if type(initial) is not ThermochemicalInventory or not commands:
        raise TypeError("Supply a finite initial inventory and nonempty held-step schedule")
    if initial.pressure_pa != owner.boundary.pressure_pa:
        raise ValueError("Initial pressure differs from the declared cell boundary")
    if initial.energy_basis_id != owner.kernel.energy_basis_id:
        raise ValueError("Initial caloric reference differs from the cell owner")
    if any(type(step) is not FuelCellStep for step in commands):
        raise TypeError("Use existing constant-current FuelCellStep objects")
    if len({step.identifier for step in commands}) != len(commands):
        raise ValueError("Requested step identities must be unique")
    feed_ids = set()
    for index, step in enumerate(commands):
        if step.clock_id != owner.evidence.clock_id:
            raise ValueError("Requested schedule uses a foreign clock")
        if index and commands[index-1].end_s != step.start_s:
            raise ValueError("Requested held steps must be contiguous")
        lo, hi = owner.boundary.temperature_bounds_k
        if (not lo <= step.temperature_k <= hi
                or step.current_density_a_m2 > owner.boundary.maximum_current_density_a_m2):
            raise ValueError("Requested step is outside the existing owner domain")
        for packet in step.feeds:
            if packet.source_id in feed_ids:
                raise ValueError("A finite feed packet is scheduled more than once")
            feed_ids.add(packet.source_id)
            if (packet.inventory.pressure_pa != owner.boundary.pressure_pa
                    or packet.inventory.energy_basis_id != owner.kernel.energy_basis_id):
                raise ValueError("Feed pressure/reference requires an explicit prior conditioning map")

    names = tuple(s.identifier for s in owner.reaction.species)
    amounts = dict(zip(names, owner.reaction.amounts(initial.amounts_mol), strict=True))
    accepted = []
    for index, step in enumerate(commands):
        # Reuse reaction species admission and preserve the native boundary order.
        withdrawal = owner.reaction.amounts(step.pre_withdrawal_mol)
        before = owner.reaction.amounts(amounts)
        if any(out > stock for out, stock in zip(withdrawal, before, strict=True)):
            raise ValueError("Pre-withdrawal exceeds stock before this step's feed")
        post = before-withdrawal
        for packet in step.feeds:
            post = post+owner.reaction.amounts(packet.inventory.amounts_mol)
        post = dict(zip(names, map(float, post), strict=True))
        h_margin = post[owner.hydrogen_id]-h2_reserve
        o_margin = post[owner.oxygen_id]-o2_reserve
        if h_margin <= 0. or o_margin <= 0.:
            raise ValueError(
                "Initial/start-boundary inventory is at or below a reserve; "
                "positive-time event API executes no fake boundary duration"
            )
        current = step.current_density_a_m2*owner.stack.geometry.active_area_m2
        rate = current*owner.stack.geometry.series_cells/(2.*FARADAY_C_MOL)
        duration = step.end_s-step.start_s
        requested_extent = rate*duration
        limit = min(h_margin, 2.*o_margin)
        endpoint_roundoff = 8.*math.ulp(max(limit, requested_extent))
        if rate > 0. and limit-requested_extent <= endpoint_roundoff:
            analytic_time = step.start_s+limit/rate
            end = min(step.end_s, analytic_time)
            # Keep the native strict finite-conversion bound admissible without
            # clipping an amount or modifying current. Retain this tiny bracket.
            for _ in range(33):
                if rate*(end-step.start_s) <= limit:
                    break
                end = math.nextafter(end, step.start_s)
            else:
                raise ValueError("Reserve event has no admissible floating-point endpoint")
            if not end > step.start_s:
                raise ValueError("Event cannot be represented at positive duration on this clock")
            shortened = step if end == step.end_s else replace(step, end_s=end)
            accepted.append(shortened)
            conversion = owner.reaction.convert(post, rate*(end-step.start_s))
            final = conversion.final_amounts
            limiting = tuple(name for name, margin in (
                (owner.hydrogen_id, h_margin), (owner.oxygen_id, 2.*o_margin))
                if abs(margin-limit) <= amount_tolerance)
            residuals = (final[owner.hydrogen_id]-h2_reserve,
                         final[owner.oxygen_id]-o2_reserve)
            if min(residuals) < -amount_tolerance or not any(
                    abs(value) <= amount_tolerance for value in residuals):
                raise ValueError("Localized event does not reach its declared molar tolerance")
            return (tuple(accepted), "reserve_event", index, limiting,
                    end, (min(end, analytic_time), max(end, analytic_time)), residuals)
        accepted.append(step)
        amounts = dict(owner.reaction.convert(post, requested_extent).final_amounts)
    return (tuple(accepted), "horizon_complete", None, (), commands[-1].end_s,
            None, None)


@dataclass(frozen=True, slots=True)
class FuelCellInventoryEventRun:
    owner: FiniteFuelCell = field(repr=False, compare=False)
    initial: ThermochemicalInventory
    requested_commands: tuple[FuelCellStep, ...]
    executed_commands: tuple[FuelCellStep, ...]
    requested_feed_bindings: tuple = field(repr=False)
    trace: FuelCellTrace = field(repr=False)
    hydrogen_reserve_mol: float
    oxygen_reserve_mol: float
    amount_tolerance_mol: float
    status: str
    event_step_index: int | None
    limiting_reactants: tuple[str, ...]
    stop_time_s: float
    event_time_bracket_s: tuple[float, float] | None
    event_residuals_mol: tuple[float, float] | None
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue through run_fuel_cell_until_reserve")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            self.owner, self.initial, self.requested_commands, self.executed_commands,
            self.requested_feed_bindings, self.trace, self.hydrogen_reserve_mol,
            self.oxygen_reserve_mol, self.amount_tolerance_mol, self.status,
            self.event_step_index, self.limiting_reactants, self.stop_time_s,
            self.event_time_bracket_s, self.event_residuals_mol))

    def require_current(self):
        if self._seal != self._content():
            raise ValueError("Fuel-cell event request, prefix, trace or event evidence changed")
        self.owner.require_current()
        self.trace.require_current()
        for _, source in self.requested_feed_bindings:
            source.require_current()
        expected = _derive(self.owner, self.initial, self.requested_commands,
                           self.hydrogen_reserve_mol, self.oxygen_reserve_mol,
                           self.amount_tolerance_mol)
        actual = (self.executed_commands, self.status, self.event_step_index,
                  self.limiting_reactants, self.stop_time_s, self.event_time_bracket_s,
                  self.event_residuals_mol)
        if actual != expected or self.trace.owner is not self.owner or self.trace.initial is not self.initial:
            raise ValueError("Event prefix no longer reproduces from its actual owner and request")
        if tuple(result.command for result in self.trace.steps) != self.executed_commands:
            raise ValueError("Actual native trace does not execute the admitted event prefix")
        if self.status == "reserve_event":
            observed = (self.trace.final.amounts_mol.get(self.owner.hydrogen_id, 0.)-self.hydrogen_reserve_mol,
                        self.trace.final.amounts_mol.get(self.owner.oxygen_id, 0.)-self.oxygen_reserve_mol)
            if any(abs(a-b) > self.amount_tolerance_mol
                   for a, b in zip(observed, self.event_residuals_mol, strict=True)):
                raise ValueError("Native stop inventory disagrees with the planned reserve root")
        return self


def run_fuel_cell_until_reserve(owner: FiniteFuelCell, initial: ThermochemicalInventory,
        commands, *, hydrogen_reserve_mol: float, oxygen_reserve_mol: float,
        amount_tolerance_mol: float = 1e-10, feed_bindings=None) -> FuelCellInventoryEventRun:
    """Stop at the first H2/O2 reserve root of a held-current step.

    Feed packets are complete instantaneous start-boundary additions. A boundary
    that is already at/below a reserve is rejected before executing any prefix;
    this API reports positive-time roots only, without invented zero-time ledgers.
    Requested tail commands/bindings are retained but not consumed after a root.
    """
    if type(owner) is not FiniteFuelCell:
        raise TypeError("Reuse an existing FiniteFuelCell owner")
    h2 = finite(hydrogen_reserve_mol, "H2 reserve")
    o2 = finite(oxygen_reserve_mol, "O2 reserve")
    tolerance = finite(amount_tolerance_mol, "event amount tolerance", positive=True)
    if min(h2, o2) < 0.:
        raise ValueError("Reactant reserves cannot be negative")
    requested = tuple(commands)
    if feed_bindings is not None and not isinstance(feed_bindings, Mapping):
        raise TypeError("Feed bindings must map finite packet IDs to original source withdrawals")
    bindings = tuple(dict(feed_bindings or {}).items())
    declared_ids = {packet.source_id for step in requested if type(step) is FuelCellStep
                    for packet in step.feeds}
    if set(dict(bindings))-declared_ids:
        raise ValueError("Source binding does not belong to a requested finite packet")
    for _, source in bindings:
        if type(source) not in {CarrierWithdrawal, FuelCellWithdrawal}:
            raise TypeError("Retain actual source-issued finite withdrawals for requested bindings")
        source.require_current()
    plan = _derive(owner, initial, requested, h2, o2, tolerance)
    prefix = plan[0]
    active_ids = {packet.source_id for step in prefix for packet in step.feeds}
    active = {key: value for key, value in bindings if key in active_ids}
    trace = owner.run(initial, prefix, feed_bindings=active)
    token = object()
    _PENDING.add(token)
    try:
        result = FuelCellInventoryEventRun(owner, initial, requested, prefix, bindings, trace,
            h2, o2, tolerance, *plan[1:], token)
    finally:
        _PENDING.discard(token)
    return result.require_current()
