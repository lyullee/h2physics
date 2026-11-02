"""Exhaustive mass partition of original liquid accident stage receipts.

Intermediate deposited stock is a transfer, not an additional terminal mass.
Unselected trajectories, flash vapor and rebound retain explicit un-routed
branches. This accounting does not infer atmospheric sources or deposition.
"""

from dataclasses import dataclass, field
from math import fsum
from types import MappingProxyType

from ..core import finite
from .parcel_impact_chain import PopulationMemberImpact
from .parcel_pool_chain import ParcelPoolContinuation
from .parcel_population import ParcelPopulationResult


_PENDING_ISSUERS = set()


def _issue_token():
    token = object()
    _PENDING_ISSUERS.add(token)
    return token


def _account(population, member, pool):
    population.require_current()
    member.require_current()
    pool.require_current()
    if member.population is not population:
        raise ValueError("Selected impact must belong to the original population")
    step = member.impact_result.steps[0]
    if (pool.initialization.impact_step is not step
            or pool.initialization.impact_owner is not member.impact_owner):
        raise ValueError("Pool must consume the original selected impact's deposited stock")
    flash = population.initial_flash
    selected = member.incident_trace.states[-1].mass_kg
    unused = fsum(group.count*trace.states[-1].mass_kg
        for group, trace in population.groups_and_traces if group is not member.group)
    last = pool.native_result.ledger[-1]
    terminal = dict(initial_flash_vapor_kg=flash.flashed_vapor_mass_kg,
        flight_evaporation_kg=population.evaporated_mass_kg,
        unselected_liquid_kg=unused, selected_impact_vapor_kg=step.mechanical.vapor_mass_kg,
        selected_rebound_liquid_kg=step.mechanical.rebound_mass_kg,
        pool_evaporation_kg=pool.vapor_source.total_mass_kg,
        pool_remaining_liquid_kg=last.liquid_mass_kg)
    transfers = dict(released_mass_kg=flash.total_release_mass_kg,
        post_flash_liquid_kg=flash.liquid_mass_kg,
        selected_incident_liquid_kg=selected,
        deposited_stock_transfer_kg=step.deposited_batch.mass_kg)
    residuals = dict(flash_kg=flash.total_release_mass_kg-flash.flashed_vapor_mass_kg-flash.liquid_mass_kg,
        flight_kg=flash.liquid_mass_kg-population.evaporated_mass_kg-selected-unused,
        impact_kg=selected-step.mechanical.vapor_mass_kg-step.mechanical.rebound_mass_kg-step.deposited_batch.mass_kg,
        pool_kg=step.deposited_batch.mass_kg-pool.vapor_source.total_mass_kg-last.liquid_mass_kg,
        terminal_kg=flash.total_release_mass_kg-fsum(terminal.values()))
    for name, value in (*terminal.items(), *transfers.items(), *residuals.items()):
        finite(value, name)
    if any(value < 0. for value in (*terminal.values(), *transfers.values())):
        raise ValueError("Accident partition contains negative branch inventory")
    return terminal, transfers, residuals


@dataclass(frozen=True, slots=True)
class LiquidAccidentMassLedger:
    population: ParcelPopulationResult
    member_impact: PopulationMemberImpact
    pool: ParcelPoolContinuation
    terminal_branches_kg: object
    intermediate_transfers_kg: object
    residuals_kg: object
    absolute_mass_tolerance_kg: float
    relative_mass_tolerance: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token is None or token not in _PENDING_ISSUERS:
            raise TypeError("Construct liquid accident mass ledgers through the binding factory")
        _PENDING_ISSUERS.remove(token)
        if (type(self.terminal_branches_kg) is not MappingProxyType
                or type(self.intermediate_transfers_kg) is not MappingProxyType
                or type(self.residuals_kg) is not MappingProxyType):
            raise TypeError("Issued mass ledger values must be immutable factory snapshots")

    def require_current(self):
        if self._binding != (id(self.population), id(self.member_impact), id(self.pool),
                             self.absolute_mass_tolerance_kg, self.relative_mass_tolerance):
            raise ValueError("Mass ledger must retain its original issuing stage receipts")
        observed = _account(self.population, self.member_impact, self.pool)
        expected = (self.terminal_branches_kg, self.intermediate_transfers_kg, self.residuals_kg)
        if any(dict(a) != dict(b) for a, b in zip(observed, expected, strict=True)):
            raise ValueError("Original accident branch mass accounting changed")
        return self


def bind_liquid_accident_mass_ledger(population, member_impact, pool, *,
                                    absolute_mass_tolerance_kg, relative_mass_tolerance):
    if (type(population) is not ParcelPopulationResult or type(member_impact) is not PopulationMemberImpact
            or type(pool) is not ParcelPoolContinuation):
        raise TypeError("Retain original typed population, selected impact and pool receipts")
    absolute = finite(absolute_mass_tolerance_kg, "absolute mass tolerance", positive=True)
    relative = finite(relative_mass_tolerance, "relative mass tolerance", positive=True)
    terminal, transfers, residuals = _account(population, member_impact, pool)
    limit = absolute+relative*transfers["released_mass_kg"]
    if any(abs(value) > limit for value in residuals.values()):
        raise ValueError("Liquid accident intermediate or terminal mass closure exceeds caller budgets")
    result = LiquidAccidentMassLedger(population, member_impact, pool,
        MappingProxyType(terminal), MappingProxyType(transfers), MappingProxyType(residuals),
        absolute, relative, _issue_token())
    object.__setattr__(result, "_binding", (id(population), id(member_impact), id(pool), absolute, relative))
    return result.require_current()


def liquid_accident_mass_ledger_from_scenario(result, **budgets):
    """Consume original standard chain nodes; retain every un-routed branch."""
    outputs = result.results
    population, impact, pool = (outputs[name] for name in ("population", "impact", "pool"))
    if "flash" in outputs and outputs["flash"] is not population.initial_flash:
        raise ValueError("Scenario flash node differs from the original population flash")
    return bind_liquid_accident_mass_ledger(population, impact, pool, **budgets)
