"""Original stage energy diagnostics for the composed liquid accident chain.

Residuals from different system boundaries are never summed as a global energy
balance. The pool's cumulative mass integral is not a substrate heat integral.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import fsum
from types import MappingProxyType
from typing import TYPE_CHECKING

from ..core import finite
from .liquid_accident_ledger import LiquidAccidentMassLedger


_PENDING_ENERGY_DIAGNOSTIC_ISSUERS: set[object] = set()


def _issue_energy_diagnostic_token():
    token = object()
    _PENDING_ENERGY_DIAGNOSTIC_ISSUERS.add(token)
    return token

if TYPE_CHECKING:
    from .pool_energy_ledger import PoolEnergyLedger


def _energy_terms(mass_ledger):
    mass_ledger.require_current()
    population = mass_ledger.population
    impact = mass_ledger.member_impact.impact_result.steps[0]
    flash = population.initial_flash
    def weighted(name):
        return fsum(group.count*getattr(trace, name)
                    for group, trace in population.groups_and_traces)
    terms = dict(
        flash_upstream_enthalpy_j=flash.total_release_mass_kg*flash.upstream_state.enthalpy_j_kg,
        flash_phase_enthalpy_residual_j=flash.enthalpy_residual_j,
        flight_heat_into_liquid_j=weighted("heat_into_liquid_j"),
        flight_drag_work_j=weighted("drag_work_j"),
        flight_ambient_pressure_work_into_j=weighted("ambient_pressure_work_into_j"),
        flight_vapor_enthalpy_kinetic_gravity_out_j=weighted("vapor_total_energy_out_j"),
        flight_total_internal_kinetic_gravity_residual_j=weighted("total_energy_residual_j"),
        impact_wall_internal_energy_change_j=impact.wall_internal_energy_change_j,
        impact_fluid_phase_internal_energy_change_j=impact.fluid_internal_energy_change_j,
        impact_ambient_pressure_work_into_j=impact.ambient_pressure_work_into_j,
        impact_interfacial_internal_energy_change_j=impact.interfacial_internal_energy_change_j,
        impact_initial_kinetic_energy_j=impact.mechanical.initial_kinetic_energy_j,
        impact_outgoing_kinetic_energy_j=impact.mechanical.outgoing_kinetic_energy_j,
        impact_intercontact_heat_into_wall_j=impact.intercontact_thermal.heat_into_patch_j,
        impact_total_internal_energy_residual_j=impact.total_energy_residual_j,
        pool_evaporation_reference_enthalpy_j=mass_ledger.pool.vapor_source.enthalpy_transfer_j)
    for name, value in terms.items():
        finite(value, name)
    return terms


@dataclass(frozen=True, slots=True)
class LiquidAccidentEnergyDiagnostics:
    mass_ledger: LiquidAccidentMassLedger
    stage_energy_j: object
    unresolved_energy_terms: tuple
    global_energy_balance_closed: bool = False
    pool_energy_ledger: PoolEnergyLedger | None = None
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ENERGY_DIAGNOSTIC_ISSUERS:
            raise TypeError("Create energy diagnostics through liquid_accident_energy_diagnostics()")
        _PENDING_ENERGY_DIAGNOSTIC_ISSUERS.remove(self._issuer_token)
        if type(self.mass_ledger) is not LiquidAccidentMassLedger:
            raise TypeError("Energy diagnostics must retain the original liquid accident mass ledger")
        if type(self.global_energy_balance_closed) is not bool:
            raise TypeError("Global energy closure is an explicit bool diagnostic")

    def require_current(self):
        pool_identity = id(self.pool_energy_ledger) if self.pool_energy_ledger is not None else None
        if self._binding != (id(self.mass_ledger), pool_identity, self.unresolved_energy_terms,
                             self.global_energy_balance_closed):
            raise ValueError("Energy diagnostics require their original issuing chain")
        if dict(self.stage_energy_j) != _energy_terms(self.mass_ledger):
            raise ValueError("Original stage energy diagnostics changed")
        if self.pool_energy_ledger is not None:
            self.pool_energy_ledger.require_current()
            if self.pool_energy_ledger.continuation is not self.mass_ledger.pool:
                raise ValueError("Pool energy ledger must belong to this exact accident-chain continuation")
        if self.global_energy_balance_closed:
            raise ValueError("Separate stage ledgers do not establish global accident energy closure")
        return self


def liquid_accident_energy_diagnostics(
    mass_ledger: LiquidAccidentMassLedger,
    *,
    pool_energy_ledger: PoolEnergyLedger | None = None,
) -> LiquidAccidentEnergyDiagnostics:
    """Inspect original stage energies without inventing a combined control volume.

    Flight includes liquid U+kinetic+gravity and exiting vapor H+kinetic+gravity.
    Impact uses phase U, wall U, interfacial U, kinetic changes and ambient work.
    Flash uses a steady isenthalpic partition. These ledgers have different
    boundaries and time windows. Their residual sum has no global interpretation.
    """
    if type(mass_ledger) is not LiquidAccidentMassLedger:
        raise TypeError("Use the original exhaustive liquid accident mass ledger")
    if pool_energy_ledger is not None:
        # Lazy import preserves the optional native pool provider boundary.
        from .pool_energy_ledger import PoolEnergyLedger

        if type(pool_energy_ledger) is not PoolEnergyLedger:
            raise TypeError("Supply the original typed native PoolEnergyLedger")
        pool_energy_ledger.require_current()
        if pool_energy_ledger.continuation is not mass_ledger.pool:
            raise ValueError("Pool energy ledger must match the exact pool continuation and output window")
    terms = _energy_terms(mass_ledger)
    unresolved = [
        "Common global system boundary and gravitational datum for all selected/unselected branches",
        "Initial flash vapor mechanical energy and launch energy supplied to prescribed parcel velocities/positions",
        "Unrouted flash vapor, rebound and unselected liquid energy transport at declared downstream boundaries",
    ]
    if pool_energy_ledger is None:
        unresolved[2:2] = [
            "Separate pool substrate cumulative heat and substrate internal-energy change",
            "Pool remaining-liquid U and pressure-volume work on exactly the source reference",
        ]
    unresolved = tuple(unresolved)
    result = LiquidAccidentEnergyDiagnostics(
        mass_ledger,
        MappingProxyType(terms),
        unresolved,
        False,
        pool_energy_ledger,
        _issue_energy_diagnostic_token(),
    )
    object.__setattr__(result, "_binding", (
        id(mass_ledger),
        id(pool_energy_ledger) if pool_energy_ledger is not None else None,
        unresolved,
        False,
    ))
    return result.require_current()
