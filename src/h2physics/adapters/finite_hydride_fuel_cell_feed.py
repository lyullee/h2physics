"""Project one accepted hydride desorption interval into a fuel-cell H2 feed.

This adapter reuses the existing ``ThermochemicalFeed`` and ``FuelCellStep``
input types. It does not integrate a hydride or fuel-cell model, and it rejects
an interval whose endpoint gas states differ because a single finite feed
packet cannot retain that state history.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, replace

import numpy as np

from ..core import Origin, ThermoState, finite
from ..storage.finite_hydride import FiniteHydrideTrace
from ..thermochemical import ThermochemicalFeed, ThermochemicalInventory
from .fuel_cell import FiniteFuelCell, FuelCellStep

_PENDING: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _project(trace, fuel_cell, step, *, interval_index, feed_source_id,
             origin, fuel_cell_feed_state, clock_mapping_evidence_id,
             state_mapping_evidence_id, transfer_evidence_id,
             energy_mapping_evidence_id, conditioning_energy_j,
             absolute_mass_tolerance_kg, relative_mass_tolerance,
             absolute_energy_tolerance_j, relative_energy_tolerance):
    if type(trace) is not FiniteHydrideTrace:
        raise TypeError("Supply an accepted FiniteHydrideTrace")
    if type(fuel_cell) is not FiniteFuelCell:
        raise TypeError("Supply the existing FiniteFuelCell owner")
    if type(step) is not FuelCellStep:
        raise TypeError("Supply one existing FuelCellStep input")
    if type(fuel_cell_feed_state) is not ThermoState:
        raise TypeError("Supply the caller-mapped typed H2 state at the fuel-cell feed boundary")
    trace.require_current()
    fuel_cell.require_current()
    if trace.gas_port_boundary is None:
        raise ValueError("Hydride trace must retain its accepted external gas-port schedule")
    if trace.integrated_external_gas_mass_kg is None or trace.integrated_external_gas_enthalpy_j is None:
        raise ValueError("Hydride trace must retain external gas mass and enthalpy ledgers")
    if trace.gas_thermodynamics.basis.fluid not in {"H2", "Hydrogen", "ParaHydrogen"}:
        raise ValueError("Hydride gas-port source must retain a pure-H2 thermodynamic basis")
    if fuel_cell.evidence.clock_id != trace.clock_id or step.clock_id != trace.clock_id:
        raise ValueError("Hydride, fuel-cell owner, and feed step must share one declared clock")
    if not math.isclose(trace.gas_thermodynamics.molar_mass_kg_mol,
                        fuel_cell.stack.geometry.hydrogen_molar_mass_kg_mol,
                        rel_tol=1e-9, abs_tol=0.):
        raise ValueError("Hydride and fuel-cell H2 molar-mass bases differ")

    index = interval_index
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(trace.snapshots)-1:
        raise ValueError("Select one accepted hydride interval by its left-edge index")
    start, end = float(trace.time_s[index]), float(trace.time_s[index+1])
    if (start != step.start_s or end != step.end_s
            or trace.clock_id != step.clock_id):
        raise ValueError("Fuel-cell feed step must match the exact hydride interval and clock")
    if not (trace.gas_port_boundary.support_start_s <= start
            and end <= trace.gas_port_boundary.support_end_s):
        raise ValueError("Selected feed interval lies outside the admitted hydride gas-port support")
    before, after = trace.snapshots[index].gas, trace.snapshots[index+1].gas
    if (before.phase not in {"gas", "supercritical_gas", "supercritical"}
            or before.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Hydride desorption feed must be a single gas-phase H2 stream")
    if (fuel_cell_feed_state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or fuel_cell_feed_state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Mapped fuel-cell feed state must remain single-phase hydrogen gas")

    mass_ledger = np.asarray(trace.integrated_external_gas_mass_kg, dtype=float)
    energy_ledger = np.asarray(trace.integrated_external_gas_enthalpy_j, dtype=float)
    if (mass_ledger.shape != (len(trace.time_s),)
            or energy_ledger.shape != (len(trace.time_s),)
            or not np.all(np.isfinite(mass_ledger))
            or not np.all(np.isfinite(energy_ledger))):
        raise ValueError("Hydride external ledgers must share the accepted state clock")
    mass = finite(-(mass_ledger[index+1]-mass_ledger[index]),
                  "outward hydride H2 mass", positive=True)
    exported_enthalpy = finite(-(energy_ledger[index+1]-energy_ledger[index]),
                               "outward hydride H2 enthalpy")
    h2_id = fuel_cell.hydrogen_id
    h2_species = next((item for item in fuel_cell.reaction.species
                       if item.identifier == h2_id), None)
    if (h2_species is None or dict(h2_species.elements) != {"H": 2}
            or h2_species.charge != 0 or h2_species.phase not in {"gas", "vapor", "ideal-gas"}
            or not math.isclose(h2_species.molar_mass_kg_mol,
                                trace.gas_thermodynamics.molar_mass_kg_mol,
                                rel_tol=1e-9, abs_tol=0.)):
        raise ValueError("Existing fuel-cell reaction does not expose a matching neutral gaseous H2 species")
    feed_state_basis = fuel_cell_feed_state.basis
    if feed_state_basis.fluid not in {"H2", "Hydrogen", "ParaHydrogen"}:
        raise ValueError("Mapped feed state must identify pure hydrogen")
    names = tuple(fuel_cell.kernel.names)
    if h2_id not in names:
        raise ValueError("Fuel-cell material kernel lacks its declared H2 species")
    feed_enthalpies = np.asarray(
        fuel_cell.caloric_source.provider.enthalpies_j_mol(
            fuel_cell_feed_state.temperature_k, fuel_cell_feed_state.pressure_pa,
        ), dtype=float,
    )
    if feed_enthalpies.shape != (len(names),) or not np.all(np.isfinite(feed_enthalpies)):
        raise ValueError("Fuel-cell caloric owner returned an invalid H2 feed enthalpy vector")
    amount_mol = mass/h2_species.molar_mass_kg_mol
    mass_residual = amount_mol*h2_species.molar_mass_kg_mol-mass
    absolute_mass = finite(absolute_mass_tolerance_kg, "absolute H2 mass tolerance", positive=True)
    relative_mass = finite(relative_mass_tolerance, "relative H2 mass tolerance", positive=True)
    if relative_mass > 1e-2:
        raise ValueError("Relative H2 mass tolerance cannot exceed 1e-2")
    if abs(mass_residual) > absolute_mass+relative_mass*mass:
        raise ValueError("Fuel-cell H2 moles do not reproduce the accepted hydride withdrawal mass")
    feed_enthalpy = finite(amount_mol*float(feed_enthalpies[names.index(h2_id)]),
                           "fuel-cell H2 feed enthalpy")
    expected_conditioning = feed_enthalpy-exported_enthalpy
    supplied_conditioning = finite(conditioning_energy_j,
                                   "signed source-to-fuel-cell conditioning energy")
    absolute_energy = finite(absolute_energy_tolerance_j, "absolute energy tolerance", positive=True)
    relative_energy = finite(relative_energy_tolerance, "relative energy tolerance", positive=True)
    if relative_mass > 1e-2 or relative_energy > 1e-2:
        raise ValueError("Relative mass/energy tolerances cannot exceed 1e-2")
    energy_residual = supplied_conditioning-expected_conditioning
    energy_budget = absolute_energy+relative_energy*max(
        abs(supplied_conditioning), abs(expected_conditioning), 1.,
    )
    if abs(energy_residual) > energy_budget:
        raise ValueError("Caller conditioning ledger does not close to the fuel-cell H2 feed energy basis")

    feed_id = _text(feed_source_id, "unique fuel-cell feed packet identity")
    if any(existing.source_id == feed_id for existing in step.feeds):
        raise ValueError("Feed packet identity is already present on this fuel-cell step")
    clock_evidence = _text(clock_mapping_evidence_id, "clock mapping evidence")
    state_evidence = _text(state_mapping_evidence_id, "feed-state mapping evidence")
    transfer_evidence = _text(transfer_evidence_id, "hydrogen transfer evidence")
    energy_evidence = _text(energy_mapping_evidence_id, "energy-reference mapping evidence")
    feed_origin = Origin(origin)
    if feed_origin is Origin.UNRESOLVED:
        raise ValueError("Resolve the origin of the hydride-to-fuel-cell hydrogen feed")

    packet = ThermochemicalFeed(
        ThermochemicalInventory(
            {h2_id: amount_mol}, fuel_cell_feed_state.temperature_k,
            fuel_cell_feed_state.pressure_pa, fuel_cell.kernel.energy_basis_id,
        ), feed_id, feed_origin,
    )
    feed_ports = dict(step.feed_ports)
    feed_ports[feed_id] = fuel_cell.boundary.hydrogen_inlet_id
    revised_step = replace(step, feeds=tuple(step.feeds)+(packet,), feed_ports=feed_ports)
    return (packet, revised_step, start, end, mass, exported_enthalpy,
            amount_mol, feed_enthalpy, expected_conditioning, supplied_conditioning,
            energy_residual, absolute_mass, relative_mass, absolute_energy,
            relative_energy, feed_id, clock_evidence, state_evidence,
            transfer_evidence, energy_evidence, feed_origin, before, after)


@dataclass(frozen=True, slots=True)
class FiniteHydrideFuelCellFeed:
    """Issued one-interval fuel-cell packet with the source ledger retained."""

    trace: FiniteHydrideTrace = field(repr=False, compare=False)
    fuel_cell: FiniteFuelCell = field(repr=False, compare=False)
    original_step: FuelCellStep
    step: FuelCellStep
    feed: ThermochemicalFeed
    fuel_cell_feed_state: ThermoState = field(repr=False, compare=False)
    interval_index: int
    start_time_s: float
    end_time_s: float
    source_mass_kg: float
    source_enthalpy_j: float
    feed_amount_mol: float
    feed_enthalpy_j: float
    required_conditioning_energy_j: float
    supplied_conditioning_energy_j: float
    conditioning_energy_residual_j: float
    absolute_mass_tolerance_kg: float
    relative_mass_tolerance: float
    absolute_energy_tolerance_j: float
    relative_energy_tolerance: float
    feed_source_id: str
    clock_mapping_evidence_id: str
    state_mapping_evidence_id: str
    transfer_evidence_id: str
    energy_mapping_evidence_id: str
    origin: Origin
    source_state: ThermoState = field(repr=False, compare=False)
    source_end_state: ThermoState = field(repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING:
            raise TypeError("Issue feed receipts through bind_finite_hydride_fuel_cell_feed")
        _PENDING.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        self.require_current()
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return hashlib.sha256(repr((
            id(self.trace), id(self.fuel_cell), id(self.original_step), id(self.step),
            id(self.feed), id(self.fuel_cell_feed_state), self.interval_index,
            self.start_time_s, self.end_time_s,
            self.source_mass_kg, self.source_enthalpy_j, self.feed_amount_mol,
            self.feed_enthalpy_j, self.required_conditioning_energy_j,
            self.supplied_conditioning_energy_j, self.conditioning_energy_residual_j,
            self.absolute_mass_tolerance_kg, self.relative_mass_tolerance,
            self.absolute_energy_tolerance_j, self.relative_energy_tolerance,
            self.feed_source_id, self.clock_mapping_evidence_id,
            self.state_mapping_evidence_id, self.transfer_evidence_id,
            self.energy_mapping_evidence_id, self.origin, id(self.source_state),
            id(self.source_end_state),
        )).encode()).hexdigest()

    def _replay(self):
        return _project(
            self.trace, self.fuel_cell, self.original_step,
            interval_index=self.interval_index, feed_source_id=self.feed_source_id,
            origin=self.origin, fuel_cell_feed_state=self.fuel_cell_feed_state,
            clock_mapping_evidence_id=self.clock_mapping_evidence_id,
            state_mapping_evidence_id=self.state_mapping_evidence_id,
            transfer_evidence_id=self.transfer_evidence_id,
            energy_mapping_evidence_id=self.energy_mapping_evidence_id,
            conditioning_energy_j=self.supplied_conditioning_energy_j,
            absolute_mass_tolerance_kg=self.absolute_mass_tolerance_kg,
            relative_mass_tolerance=self.relative_mass_tolerance,
            absolute_energy_tolerance_j=self.absolute_energy_tolerance_j,
            relative_energy_tolerance=self.relative_energy_tolerance,
        )

    def require_current(self):
        self.trace.require_current()
        self.fuel_cell.require_current()
        projected = self._replay()
        (feed, revised_step, start, end, mass, source_h, amount, feed_h,
         required, supplied, residual, abs_m, rel_m, abs_e, rel_e, feed_id,
         clock_id, state_id, transfer_id, energy_id, feed_origin,
         source_state, source_end_state) = projected
        actual = (self.feed, self.step, self.start_time_s, self.end_time_s,
                  self.source_mass_kg, self.source_enthalpy_j, self.feed_amount_mol,
                  self.feed_enthalpy_j, self.required_conditioning_energy_j,
                  self.supplied_conditioning_energy_j, self.conditioning_energy_residual_j,
                  self.absolute_mass_tolerance_kg, self.relative_mass_tolerance,
                  self.absolute_energy_tolerance_j, self.relative_energy_tolerance,
                  self.feed_source_id, self.clock_mapping_evidence_id,
                  self.state_mapping_evidence_id, self.transfer_evidence_id,
                  self.energy_mapping_evidence_id, self.origin, self.source_state,
                  self.source_end_state)
        expected = (feed, revised_step, start, end, mass, source_h, amount, feed_h,
                    required, supplied, residual, abs_m, rel_m, abs_e, rel_e,
                    feed_id, clock_id, state_id, transfer_id, energy_id,
                    feed_origin, source_state, source_end_state)
        if actual != expected:
            raise ValueError("Hydride-to-fuel-cell receipt differs from replayed feed/source projection")
        if (self.feed.inventory.amounts_mol.get(self.fuel_cell.hydrogen_id, 0.) != self.feed_amount_mol
                or self.feed.inventory.temperature_k != self.fuel_cell_feed_state.temperature_k
                or self.feed.inventory.pressure_pa != self.fuel_cell_feed_state.pressure_pa):
            raise ValueError("Fuel-cell feed packet composition or amount changed")
        if self._seal and self._content() != self._seal:
            raise ValueError("Hydride-to-fuel-cell receipt changed after issue")
        return self


def bind_finite_hydride_fuel_cell_feed(
    trace: FiniteHydrideTrace,
    fuel_cell: FiniteFuelCell,
    step: FuelCellStep,
    *,
    interval_index: int,
    feed_source_id: str,
    origin: Origin,
    fuel_cell_feed_state: ThermoState,
    clock_mapping_evidence_id: str,
    state_mapping_evidence_id: str,
    transfer_evidence_id: str,
    energy_mapping_evidence_id: str,
    conditioning_energy_j: float,
    absolute_mass_tolerance_kg: float,
    relative_mass_tolerance: float,
    absolute_energy_tolerance_j: float,
    relative_energy_tolerance: float,
) -> FiniteHydrideFuelCellFeed:
    """Bind one exact desorption interval to one existing fuel-cell step.

    The step must use the exact hydride interval and clock. The original source
    trace retains every accepted state and its integrated gas enthalpy. The
    caller supplies a typed representative fuel-cell feed state plus signed
    energy/reference mapping; no averaging rule, conditioning law, or solver
    physics is inferred.
    """
    projected = _project(
        trace, fuel_cell, step, interval_index=interval_index,
        feed_source_id=feed_source_id, origin=origin,
        fuel_cell_feed_state=fuel_cell_feed_state,
        clock_mapping_evidence_id=clock_mapping_evidence_id,
        state_mapping_evidence_id=state_mapping_evidence_id,
        transfer_evidence_id=transfer_evidence_id,
        energy_mapping_evidence_id=energy_mapping_evidence_id,
        conditioning_energy_j=conditioning_energy_j,
        absolute_mass_tolerance_kg=absolute_mass_tolerance_kg,
        relative_mass_tolerance=relative_mass_tolerance,
        absolute_energy_tolerance_j=absolute_energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance,
    )
    token = object()
    _PENDING.add(token)
    try:
        (packet, revised, start, end, mass, source_h, amount, feed_h, required,
         supplied, residual, abs_m, rel_m, abs_e, rel_e, feed_id, clock_id,
         state_id, transfer_id, energy_id, feed_origin, source_state,
         source_end_state) = projected
        receipt = FiniteHydrideFuelCellFeed(
            trace, fuel_cell, step, revised, packet, fuel_cell_feed_state,
            interval_index, start, end,
            mass, source_h, amount, feed_h, required, supplied, residual,
            abs_m, rel_m, abs_e, rel_e, feed_id, clock_id, state_id,
            transfer_id, energy_id, feed_origin, source_state, source_end_state,
            _issuer_token=token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    return receipt.require_current()


__all__ = ["FiniteHydrideFuelCellFeed", "bind_finite_hydride_fuel_cell_feed"]
