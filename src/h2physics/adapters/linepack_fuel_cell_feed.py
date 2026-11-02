"""Bind one accepted linepack withdrawal bin to an existing fuel-cell feed.

The linepack owner has a mass ledger but no enthalpy integral. This boundary
therefore requires the caller's integrated stream enthalpy and reference/heat
ledger as explicit evidence; it never infers an interval energy from the
representative source state.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, replace

from ..core import Origin, ThermoState, finite
from ..thermochemical import ThermochemicalFeed, ThermochemicalInventory
from .fuel_cell import FiniteFuelCell, FuelCellStep
from .linepack_source import LinepackSourceHandoff
from .real_gas_linepack_source import RealGasLinepackSourceHandoff

_PENDING: set[object] = set()


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label}")
    return value.strip()


def _project(source, fuel_cell, step, *, feed_source_id, origin,
             fuel_cell_feed_state, source_enthalpy_j, source_enthalpy_reference_id,
             receiver_energy_basis_id, reference_offset_j, clock_evidence_id,
             state_evidence_id, transfer_evidence_id, energy_evidence_id,
             conditioning_energy_j, absolute_mass_tolerance_kg,
             relative_mass_tolerance, absolute_energy_tolerance_j,
             relative_energy_tolerance):
    if type(source) not in {LinepackSourceHandoff, RealGasLinepackSourceHandoff}:
        raise TypeError("Supply an accepted ideal or native real-gas linepack source receipt")
    if type(fuel_cell) is not FiniteFuelCell or type(step) is not FuelCellStep:
        raise TypeError("Supply the existing fuel-cell owner and one FuelCellStep")
    if type(fuel_cell_feed_state) is not ThermoState:
        raise TypeError("Supply a caller-mapped typed H2 feed state")
    source.require_current()
    fuel_cell.require_current()
    native = source.source
    start, end = (float(value) for value in native.edges_s)
    if (native.location.clock_id != step.clock_id
            or fuel_cell.evidence.clock_id != step.clock_id or start != step.start_s
            or end != step.end_s):
        raise ValueError("Fuel-cell owner/step must match the exact linepack interval and clock")
    if native.state.basis.fluid not in {"H2", "Hydrogen", "ParaHydrogen"}:
        raise ValueError("Linepack source must identify pure hydrogen")
    if (native.state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or native.state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Linepack source must be a single gas phase")
    if (fuel_cell_feed_state.basis.fluid not in {"H2", "Hydrogen", "ParaHydrogen"}
            or fuel_cell_feed_state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or fuel_cell_feed_state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Mapped fuel-cell feed must remain single-phase hydrogen gas")
    source_spin = native.state.basis.spin_composition
    if (source_spin != "unspecified"
            and fuel_cell_feed_state.basis.spin_composition != source_spin):
        raise ValueError("Known linepack hydrogen spin composition requires the same feed spin; no converter is supplied")
    receiver_pressure = fuel_cell.boundary.pressure_pa
    if not math.isclose(fuel_cell_feed_state.pressure_pa, receiver_pressure,
                        rel_tol=1e-10, abs_tol=1e-6):
        raise ValueError("Mapped fuel-cell feed pressure must match its conditioned inlet boundary")
    source_molar_mass = (source.hydrogen_molar_mass_kg_mol
                        if type(source) is RealGasLinepackSourceHandoff
                        else source.initial.molecular_mass_kg_mol)
    if not math.isclose(source_molar_mass,
                        fuel_cell.stack.geometry.hydrogen_molar_mass_kg_mol,
                        rel_tol=1e-9, abs_tol=0.):
        raise ValueError("Linepack and fuel-cell hydrogen molar-mass bases differ")
    mass = finite(source.ledger.outlet_mass_kg, "accepted linepack outlet mass", positive=True)
    if not math.isclose(native.total_mass_kg, mass, rel_tol=1e-12, abs_tol=1e-15):
        raise ValueError("Linepack source mass differs from its accepted withdrawal ledger")
    exported_h = finite(source_enthalpy_j, "caller-integrated linepack withdrawal enthalpy")
    source_reference = _text(source_enthalpy_reference_id,
                              "integrated source enthalpy reference identity")
    receiver_reference = _text(receiver_energy_basis_id,
                                "fuel-cell caloric energy-basis identity")
    if receiver_reference != fuel_cell.kernel.energy_basis_id:
        raise ValueError("Declared receiver energy basis differs from the fuel-cell kernel")
    reference_offset = finite(reference_offset_j, "signed enthalpy-reference offset")
    species_id = fuel_cell.hydrogen_id
    species = next((s for s in fuel_cell.reaction.species if s.identifier == species_id), None)
    if (species is None or dict(species.elements) != {"H": 2} or species.charge != 0
            or species.phase not in {"gas", "vapor", "ideal-gas"}
            or not math.isclose(species.molar_mass_kg_mol,
                                fuel_cell.stack.geometry.hydrogen_molar_mass_kg_mol,
                                rel_tol=1e-9, abs_tol=0.)):
        raise ValueError("Fuel-cell reaction must expose a matching neutral gaseous H2 species")
    names = tuple(fuel_cell.kernel.names)
    if species_id not in names:
        raise ValueError("Fuel-cell caloric kernel lacks its declared H2 species")
    feed_hs = fuel_cell.caloric_source.provider.enthalpies_j_mol(
        fuel_cell_feed_state.temperature_k, receiver_pressure)
    if len(feed_hs) != len(names) or not all(math.isfinite(float(v)) for v in feed_hs):
        raise ValueError("Fuel-cell caloric provider returned an invalid enthalpy vector")
    amount = mass / species.molar_mass_kg_mol
    feed_h = finite(amount * float(feed_hs[names.index(species_id)]), "fuel-cell feed enthalpy")
    required = feed_h - exported_h - reference_offset
    supplied = finite(conditioning_energy_j, "signed linepack-to-feed conditioning/reference energy")
    abs_m = finite(absolute_mass_tolerance_kg, "absolute mass tolerance", positive=True)
    rel_m = finite(relative_mass_tolerance, "relative mass tolerance", positive=True)
    abs_e = finite(absolute_energy_tolerance_j, "absolute energy tolerance", positive=True)
    rel_e = finite(relative_energy_tolerance, "relative energy tolerance", positive=True)
    if rel_m > 1e-2 or rel_e > 1e-2:
        raise ValueError("Relative mass and energy tolerances cannot exceed 1e-2")
    mass_residual = amount * species.molar_mass_kg_mol - mass
    energy_residual = exported_h + reference_offset + supplied - feed_h
    if abs(mass_residual) > abs_m + rel_m * mass:
        raise ValueError("Fuel-cell feed amount does not close to linepack withdrawal mass")
    if abs(energy_residual) > abs_e + rel_e * max(abs(supplied), abs(required), 1.):
        raise ValueError("Caller conditioning/reference ledger does not close feed enthalpy")
    feed_id = _text(feed_source_id, "unique finite fuel-cell feed identity")
    if any(feed.source_id == feed_id for feed in step.feeds):
        raise ValueError("Feed identity already exists on the target fuel-cell step")
    clock_id = _text(clock_evidence_id, "linepack-to-fuel-cell clock mapping evidence")
    state_id = _text(state_evidence_id, "fuel-cell feed-state mapping evidence")
    transfer_id = _text(transfer_evidence_id, "linepack transfer evidence")
    energy_id = _text(energy_evidence_id, "integrated source enthalpy/reference evidence")
    selected_origin = Origin(origin)
    if selected_origin is Origin.UNRESOLVED:
        raise ValueError("Resolve the linepack withdrawal origin")
    if selected_origin != native.origin:
        raise ValueError("Fuel-cell feed origin must preserve the accepted linepack source origin")
    packet = ThermochemicalFeed(ThermochemicalInventory(
        {species_id: amount}, fuel_cell_feed_state.temperature_k,
        receiver_pressure, fuel_cell.kernel.energy_basis_id,
    ), feed_id, selected_origin)
    ports = dict(step.feed_ports)
    ports[feed_id] = fuel_cell.boundary.hydrogen_inlet_id
    revised = replace(step, feeds=tuple(step.feeds) + (packet,), feed_ports=ports)
    return (packet, revised, start, end, mass, exported_h, amount, feed_h,
            reference_offset, required, supplied, mass_residual, energy_residual,
            abs_m, rel_m, abs_e, rel_e, feed_id, source_reference,
            receiver_reference, clock_id, state_id, transfer_id, energy_id,
            selected_origin)


@dataclass(frozen=True, slots=True)
class LinepackFuelCellFeed:
    source: LinepackSourceHandoff | RealGasLinepackSourceHandoff = field(repr=False, compare=False)
    fuel_cell: FiniteFuelCell = field(repr=False, compare=False)
    original_step: FuelCellStep
    step: FuelCellStep
    feed: ThermochemicalFeed
    feed_state: ThermoState = field(repr=False, compare=False)
    source_enthalpy_j: float
    source_enthalpy_reference_id: str
    receiver_energy_basis_id: str
    reference_offset_j: float
    start_time_s: float
    end_time_s: float
    source_mass_kg: float
    feed_amount_mol: float
    feed_enthalpy_j: float
    required_conditioning_energy_j: float
    supplied_conditioning_energy_j: float
    mass_residual_kg: float
    energy_residual_j: float
    absolute_mass_tolerance_kg: float
    relative_mass_tolerance: float
    absolute_energy_tolerance_j: float
    relative_energy_tolerance: float
    feed_source_id: str
    clock_evidence_id: str
    state_evidence_id: str
    transfer_evidence_id: str
    energy_evidence_id: str
    origin: Origin
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue through bind_linepack_fuel_cell_feed")
        _PENDING.remove(self._issuer)
        self.require_current()
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return hashlib.sha256(repr((
            id(self.source), id(self.fuel_cell), id(self.original_step), id(self.step),
            id(self.feed), id(self.feed_state), self.source_enthalpy_j,
            self.source_enthalpy_reference_id, self.receiver_energy_basis_id,
            self.reference_offset_j,
            self.start_time_s, self.end_time_s, self.source_mass_kg,
            self.feed_amount_mol, self.feed_enthalpy_j,
            self.required_conditioning_energy_j, self.supplied_conditioning_energy_j,
            self.mass_residual_kg, self.energy_residual_j,
            self.absolute_mass_tolerance_kg, self.relative_mass_tolerance,
            self.absolute_energy_tolerance_j, self.relative_energy_tolerance,
            self.feed_source_id, self.clock_evidence_id, self.state_evidence_id,
            self.transfer_evidence_id, self.energy_evidence_id, self.origin,
        )).encode()).hexdigest()

    def require_current(self):
        self.source.require_current()
        self.fuel_cell.require_current()
        replay = _project(
            self.source, self.fuel_cell, self.original_step,
            feed_source_id=self.feed_source_id, origin=self.origin,
            fuel_cell_feed_state=self.feed_state, source_enthalpy_j=self.source_enthalpy_j,
            source_enthalpy_reference_id=self.source_enthalpy_reference_id,
            receiver_energy_basis_id=self.receiver_energy_basis_id,
            reference_offset_j=self.reference_offset_j,
            clock_evidence_id=self.clock_evidence_id, state_evidence_id=self.state_evidence_id,
            transfer_evidence_id=self.transfer_evidence_id, energy_evidence_id=self.energy_evidence_id,
            conditioning_energy_j=self.supplied_conditioning_energy_j,
            absolute_mass_tolerance_kg=self.absolute_mass_tolerance_kg,
            relative_mass_tolerance=self.relative_mass_tolerance,
            absolute_energy_tolerance_j=self.absolute_energy_tolerance_j,
            relative_energy_tolerance=self.relative_energy_tolerance,
        )
        actual = (self.feed, self.step, self.start_time_s, self.end_time_s,
                  self.source_mass_kg, self.source_enthalpy_j, self.feed_amount_mol,
                  self.feed_enthalpy_j, self.reference_offset_j,
                  self.required_conditioning_energy_j,
                  self.supplied_conditioning_energy_j, self.mass_residual_kg,
                  self.energy_residual_j, self.absolute_mass_tolerance_kg,
                  self.relative_mass_tolerance, self.absolute_energy_tolerance_j,
                  self.relative_energy_tolerance, self.feed_source_id,
                  self.source_enthalpy_reference_id, self.receiver_energy_basis_id,
                  self.clock_evidence_id, self.state_evidence_id,
                  self.transfer_evidence_id, self.energy_evidence_id, self.origin)
        if actual != replay:
            raise ValueError("Linepack fuel-cell receipt differs from its replayed projection")
        if self._seal and self._content() != self._seal:
            raise ValueError("Linepack fuel-cell receipt changed after issue")
        return self


def bind_linepack_fuel_cell_feed(
    source: LinepackSourceHandoff | RealGasLinepackSourceHandoff,
    fuel_cell: FiniteFuelCell, step: FuelCellStep, *,
    feed_source_id: str, origin: Origin, fuel_cell_feed_state: ThermoState,
    source_enthalpy_j: float, source_enthalpy_reference_id: str,
    receiver_energy_basis_id: str, reference_offset_j: float,
    clock_evidence_id: str, state_evidence_id: str,
    transfer_evidence_id: str, energy_evidence_id: str, conditioning_energy_j: float,
    absolute_mass_tolerance_kg: float, relative_mass_tolerance: float,
    absolute_energy_tolerance_j: float, relative_energy_tolerance: float,
) -> LinepackFuelCellFeed:
    """Project one exact linepack interval into a finite fuel-cell H2 packet.

    The caller owns source interval enthalpy, thermodynamic state mapping,
    source reference identity, receiver energy basis, signed reference offset,
    conditioning energy and all transfer evidence. The closure is
    ``H_source + offset + conditioning - H_feed = 0``. This issues an
    input packet only; it does not run either model or add pipe cooling.
    """
    values = dict(feed_source_id=feed_source_id, origin=origin,
        fuel_cell_feed_state=fuel_cell_feed_state, source_enthalpy_j=source_enthalpy_j,
        source_enthalpy_reference_id=source_enthalpy_reference_id,
        receiver_energy_basis_id=receiver_energy_basis_id,
        reference_offset_j=reference_offset_j,
        clock_evidence_id=clock_evidence_id, state_evidence_id=state_evidence_id,
        transfer_evidence_id=transfer_evidence_id, energy_evidence_id=energy_evidence_id,
        conditioning_energy_j=conditioning_energy_j,
        absolute_mass_tolerance_kg=absolute_mass_tolerance_kg,
        relative_mass_tolerance=relative_mass_tolerance,
        absolute_energy_tolerance_j=absolute_energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance)
    projected = _project(source, fuel_cell, step, **values)
    token = object()
    _PENDING.add(token)
    try:
        (packet, revised, start, end, mass, source_h, amount, feed_h,
         reference_offset, required, supplied, mres, eres, am, rm, ae, re,
         feed_id, source_reference, receiver_reference, clock_id, state_id,
         transfer_id, energy_id, selected_origin) = projected
        return LinepackFuelCellFeed(source, fuel_cell, step, revised, packet,
            fuel_cell_feed_state, source_h, source_reference, receiver_reference,
            reference_offset, start, end, mass, amount, feed_h,
            required, supplied, mres, eres, am, rm, ae, re, feed_id, clock_id,
            state_id, transfer_id, energy_id, selected_origin, token).require_current()
    except Exception:
        _PENDING.discard(token)
        raise
