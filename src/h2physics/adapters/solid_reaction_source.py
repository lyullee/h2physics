"""Finite H2 product source projection from an accepted solid-reaction trace."""

from dataclasses import dataclass, field
from hashlib import sha256
from math import fsum, isclose

import numpy as np

from ..core import Origin, ThermoState
from ..release import SourceLocation
from ..sources import IntervalMassSource
from .solid_reaction_energy import inventory_enthalpy_j
from .result_provenance import recorded_content_sha256

_PENDING_SOLID_H2_SOURCE: set[object] = set()


def _signature(trace, source, location_projection_evidence_id, trace_digest):
    return sha256(repr((id(trace), trace_digest, id(source), source._fingerprint,
                        location_projection_evidence_id)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SolidReactionHydrogenSource:
    trace: object
    source: IntervalMassSource
    hydrogen_species_id: str
    location_projection_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _trace_digest: str = field(default="", init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_SOLID_H2_SOURCE:
            raise TypeError("Create product-source receipts through the typed adapter")
        _PENDING_SOLID_H2_SOURCE.remove(self._issuer)
        from ..storage.solid_reaction import SolidReactionTrace

        if type(self.trace) is not SolidReactionTrace:
            raise TypeError("Retain the original reactor-issued SolidReactionTrace")
        digest = recorded_content_sha256(self.trace)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_trace_digest", digest)
        object.__setattr__(self, "_seal", _signature(
            self.trace, self.source, self.location_projection_evidence_id, digest))

    def _signature(self):
        return _signature(self.trace, self.source,
                          self.location_projection_evidence_id, self._trace_digest)

    def require_current(self):
        from ..storage.solid_reaction import SolidReactionTrace

        if self._issuer is not self._issued or type(self.trace) is not SolidReactionTrace:
            raise ValueError("Product-source receipt lost its original producer identity")
        self.source.require_current()
        if (recorded_content_sha256(self.trace) != self._trace_digest
                or self.source.location.source_id != self.trace.evidence.process_id
                or self.source.origin != self.trace.evidence.origin
                or self.source.state.basis.reference_id != self.trace.evidence.caloric_basis_id
                or self.source.state.basis.fluid != "H2"
                or self.source.state.phase != "gas"
                or self._signature() != self._seal):
            raise ValueError("Original reaction product, state basis or finite-source content changed")
        return self


def source_from_solid_reaction_hydrogen(trace, *, location: SourceLocation,
        gas_state: ThermoState, location_projection_evidence_id: str,
        energy_tolerance_j: float = 1e-6):
    """Project pure H2 takeoff into exact finite interval mass bins.

    Each bin uses the original step's actual H2 withdrawal, never its generated
    extent. Non-H2 co-withdrawal, changing product state, mismatched molar
    enthalpy reference or energy beyond the declared tolerance are rejected.
    The fixed source location is caller-owned because the reaction trace has no
    spatial product-plane model.
    """
    from ..storage.solid_reaction import SolidReactionTrace

    if type(trace) is not SolidReactionTrace:
        raise TypeError("Supply an original reactor-issued SolidReactionTrace")
    if type(location) is not SourceLocation or type(gas_state) is not ThermoState:
        raise TypeError("Supply an explicit source location and typed H2 gas state")
    if not isinstance(location_projection_evidence_id, str) or not location_projection_evidence_id.strip():
        raise ValueError("Declare the product-to-source spatial projection")
    if location.source_id != trace.evidence.process_id:
        raise ValueError("Source location must retain the producer's original process identity")
    trace_digest = recorded_content_sha256(trace)
    rows = tuple(trace.steps)
    if not rows:
        raise ValueError("H2 source needs at least one accepted product-withdrawal step")
    commands = tuple(row.step for row in rows)
    clock_ids = {command.clock_id for command in commands}
    edges = np.asarray((commands[0].start_s, *(command.end_s for command in commands)), dtype=float)
    if (clock_ids != {location.clock_id} or np.any(np.diff(edges) <= 0.)
            or any(left.end_s != right.start_s
                   for left, right in zip(commands[:-1], commands[1:]))):
        raise ValueError("One finite product source requires a contiguous single-clock reaction schedule")
    if (trace.kernel.energy_basis_id != trace.evidence.caloric_basis_id
            or trace.enthalpy_provider.basis_id != trace.evidence.caloric_basis_id
            or trace.kernel.enthalpy is not trace.enthalpy_provider):
        raise ValueError("Producer trace, kernel and provider must retain one caloric reference")
    tolerance = trace.kernel.tolerances
    species_mass = {species.identifier: species.molar_mass_kg_mol for species in trace.species}
    initial_scale = sum(trace.initial.amounts_mol.get(name, 0.)*mass
                        for name, mass in species_mass.items())
    final_scale = sum(trace.final.amounts_mol.get(name, 0.)*mass
                      for name, mass in species_mass.items())
    initial_scale += sum(sum(supply.inventory.amounts_mol.get(name, 0.)*mass
                             for name, mass in species_mass.items())
                         for supply in trace.initial_supplies)
    final_scale += sum(sum(supply.inventory.amounts_mol.get(name, 0.)*mass
                           for name, mass in species_mass.items())
                       for supply in trace.remaining_supplies)
    mass_budget = tolerance.mass_kg+tolerance.relative*max(initial_scale, final_scale, 1.)
    inventory_energy = lambda inventory: inventory_enthalpy_j(
        inventory, species=trace.species, provider=trace.enthalpy_provider,
        kernel=trace.kernel,
        energy_basis_id=trace.evidence.caloric_basis_id)
    initial_energy = fsum((inventory_energy(trace.initial), *(inventory_energy(
        supply.inventory) for supply in trace.initial_supplies)))
    final_energy = fsum((inventory_energy(trace.final), *(inventory_energy(
        supply.inventory) for supply in trace.remaining_supplies)))
    energy_budget = tolerance.energy_j+tolerance.relative*max(
        abs(initial_energy), abs(final_energy), abs(trace.exported_enthalpy_j),
        abs(trace.heat_input_j), 1.)
    amount_scale = max(sum(trace.initial.amounts_mol.values())
                       +sum(sum(supply.inventory.amounts_mol.values())
                            for supply in trace.initial_supplies), 1.)
    element_budget = tolerance.amount_mol+tolerance.relative*amount_scale
    exported_by_steps = np.sum([np.asarray(row.removed_mol, dtype=float) for row in rows], axis=0)
    if (abs(trace.mass_residual_kg) > mass_budget
            or abs(trace.enthalpy_residual_j) > energy_budget
            or max(abs(value) for value in trace.element_residual_mol) > element_budget
            or not np.allclose(exported_by_steps, trace.exported_mol,
                               rtol=tolerance.relative, atol=tolerance.amount_mol)
            or not isclose(sum(row.removed_enthalpy_j for row in rows),
                           trace.exported_enthalpy_j,
                           rel_tol=tolerance.relative, abs_tol=tolerance.energy_j)
            or not isclose(sum(command.heat_input_j for command in commands),
                           trace.heat_input_j,
                           rel_tol=tolerance.relative, abs_tol=tolerance.energy_j)):
        raise ValueError("Accepted reaction material/energy ledger does not close within its budget")
    if (gas_state.basis.fluid != "H2" or gas_state.phase != "gas"
            or gas_state.vapor_mass_fraction not in (None, 1.)
            or gas_state.basis.reference_id != trace.evidence.caloric_basis_id):
        raise ValueError("Product gas state must retain the trace's exact gaseous-H2 enthalpy basis")
    candidates = tuple(i for i, species in enumerate(trace.species)
        if dict(species.elements) == {"H": 2} and species.charge == 0
        and (species.phase.lower() in {"gas", "ideal-gas"}
             or species.phase.lower().startswith("gas:")))
    if len(candidates) != 1:
        raise ValueError("Exactly one neutral gaseous H2 species must be declared in the reaction")
    h2_index = candidates[0]
    h2 = trace.species[h2_index]
    energy_tolerance = float(energy_tolerance_j)
    if not np.isfinite(energy_tolerance) or energy_tolerance <= 0.:
        raise ValueError("Declare a positive finite H2 enthalpy-projection tolerance")
    mass_bins = []
    for row in rows:
        if (row.after.energy_basis_id != trace.evidence.caloric_basis_id
                or not isclose(row.after.temperature_k, gas_state.temperature_k,
                               rel_tol=1e-12, abs_tol=1e-10)
                or not isclose(row.after.pressure_pa, gas_state.pressure_pa,
                               rel_tol=1e-12, abs_tol=1e-6)):
            raise ValueError("One source ThermoState cannot represent changing product P/T states")
        removed = np.asarray(row.removed_mol, dtype=float)
        if removed.shape != (len(trace.species),) or not np.all(np.isfinite(removed)) or np.any(removed < 0.):
            raise ValueError("Accepted reaction takeoff must preserve its nonnegative species vector")
        other = np.delete(removed, h2_index)
        if np.any(other > tolerance.amount_mol):
            raise ValueError("A single-component H2 finite source cannot hide co-withdrawn species")
        h2_mol = float(removed[h2_index])
        mass_bins.append(h2_mol*h2.molar_mass_kg_mol)
        molar_h = np.asarray(trace.enthalpy_provider.enthalpies_j_mol(
            gas_state.temperature_k, gas_state.pressure_pa), dtype=float)
        if (molar_h.shape != (len(trace.species),) or not np.all(np.isfinite(molar_h))):
            raise ValueError("Original caloric provider returned invalid product enthalpies")
        native_output_h = h2_mol*float(molar_h[h2_index])
        state_output_h = mass_bins[-1]*gas_state.enthalpy_j_kg
        residual = state_output_h-native_output_h
        budget = energy_tolerance+tolerance.relative*max(
            abs(state_output_h), abs(native_output_h), 1.)
        if abs(residual) > budget:
            raise ValueError("Representative gas state does not conserve the native H2 takeoff enthalpy")
        if not isclose(row.removed_enthalpy_j, native_output_h,
                       rel_tol=tolerance.relative, abs_tol=tolerance.energy_j):
            raise ValueError("Reaction step total takeoff enthalpy is not pure-H2 enthalpy")
    if not isclose(sum(mass_bins), h2.molar_mass_kg_mol*float(trace.exported_mol[h2_index]),
                   rel_tol=tolerance.relative, abs_tol=tolerance.mass_kg):
        raise ValueError("Stepwise H2 source bins do not close to the accepted export ledger")
    if trace.evidence.origin == Origin.UNRESOLVED:
        raise ValueError("Resolve the reaction product source origin")
    source = IntervalMassSource(location, edges, mass_bins, gas_state, trace.evidence.origin,
        ":".join((trace.evidence.process_id, trace.evidence.stoichiometry_source_id,
                   trace.evidence.caloric_basis_id,
                   trace.evidence.common_temperature_assumption_id,
                   trace.evidence.fixed_pressure_boundary_id,
                   trace.evidence.component_takeoff_assumption_id,
                   trace.kinetics.identifier, trace.kinetics.source_id,
                   *(command.evidence_id for command in commands),
                   location_projection_evidence_id.strip())),
        "window_end")
    token = object()
    _PENDING_SOLID_H2_SOURCE.add(token)
    try:
        result = SolidReactionHydrogenSource(trace, source, h2.identifier,
            location_projection_evidence_id.strip(), token)
    except Exception:
        _PENDING_SOLID_H2_SOURCE.discard(token)
        raise
    return result.require_current()
