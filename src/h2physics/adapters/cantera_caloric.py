"""Common-reference native ideal-gas / pure-solid molar enthalpies.

Native thermochemistry and constant-volume solid pressure dependence stay in
Cantera. This is a property bridge for prescribed finite conversion, with no
equilibrium, phase-selection, heat-capacity or reaction-rate solver.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from ..core import immutable_array, Origin, finite
from ..reactions import ChemicalSpecies
from .cantera_multiphase import EquilibriumPhase, _solid_copy
from .cantera_thermo import CanteraMolarEnthalpy
from .cantera_volume import _phase_fingerprint, _private_native_phase


@dataclass(frozen=True, slots=True)
class SolidDensityEvidence:
    """Evidence for the actual factory's constant-volume density, in kg/m3.

    A synthetic value is an authored calorimetry fixture, not a measurement or
    evidence that a thermochemical species database supplies a solid EOS.
    """

    density_kg_m3: float
    source_id: str
    origin: Origin
    description: str

    def __post_init__(self):
        finite(self.density_kg_m3, "constant-volume solid density", positive=True)
        if not all(isinstance(s, str) and s.strip() for s in (self.source_id, self.description)):
            raise ValueError("Declare the density source and its physical/fixture meaning")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve the solid-density data role")


@dataclass(frozen=True, slots=True)
class CaloricSpeciesMapping:
    phase_id: str
    native_species: str
    host_alias: str

    def __post_init__(self):
        if not all(isinstance(s, str) and s.strip() for s in (
                self.phase_id, self.native_species, self.host_alias)):
            raise ValueError("Declare phase, native species and host alias explicitly")


class CanteraMultiphaseMolarEnthalpy:
    """MolarEnthalpyProvider using independently owned actual native phases.

    Mapping order defines ``species`` and ``enthalpies_j_mol`` order. Compatible
    formation/reference and hydrogen-partition identities are caller evidence,
    not inferred from species names. Returned native objects remain available;
    definition mutation is rejected and state/composition changes are reset.
    """

    def __init__(self, phases, species_mapping, *, solid_density_evidence: Mapping | None = None):
        import cantera as ct

        if tuple(int(v) for v in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("Native copy/calorimetry is checked with Cantera3.2")
        self.phases = tuple(phases)
        self.species_mapping = tuple(m if isinstance(m, CaloricSpeciesMapping)
                                     else CaloricSpeciesMapping(*m) for m in species_mapping)
        if (not self.phases or not all(isinstance(p, EquilibriumPhase) for p in self.phases)
                or len({p.phase_id for p in self.phases}) != len(self.phases)):
            raise ValueError("Declare unique evidenced native phases")
        if sum(p.role == "gas" for p in self.phases) > 1:
            raise ValueError("This caloric bridge supports at most one ideal-gas phase")
        if (not self.species_mapping or len({m.host_alias for m in self.species_mapping})
                != len(self.species_mapping) or len({(m.phase_id, m.native_species)
                for m in self.species_mapping}) != len(self.species_mapping)):
            raise ValueError("Declare unique host aliases and native phase/species pairs")
        if {m.phase_id for m in self.species_mapping} != {p.phase_id for p in self.phases}:
            raise ValueError("Map species from every declared phase and no foreign phase")
        if len({p.energy_reference_id for p in self.phases}) != 1:
            raise ValueError("Every phase needs the same explicit formation-energy reference")
        if len({p.hydrogen_partition_id for p in self.phases}) != 1:
            raise ValueError("Every phase needs the same explicit hydrogen-partition identity")
        self.energy_reference_id = self.phases[0].energy_reference_id
        self.hydrogen_partition_id = self.phases[0].hydrogen_partition_id
        evidence = dict(solid_density_evidence or {})
        if set(evidence) != {p.phase_id for p in self.phases if p.role == "solid"}:
            raise ValueError("Declare density evidence for every solid and no other phase")
        if not all(isinstance(v, SolidDensityEvidence) for v in evidence.values()):
            raise ValueError("Use explicit SolidDensityEvidence records")
        self.solid_density_evidence = MappingProxyType(evidence)
        sources, owned, audits, weights = [], [], [], {}
        for spec in self.phases:
            source = spec.factory()
            expected = "ideal-gas" if spec.role == "gas" else "fixed-stoichiometry"
            if (not isinstance(source, ct.Solution) or source.thermo_model != expected
                    or source.n_selected_species != source.n_species or np.any(source.charges != 0)
                    or (spec.role == "solid" and source.n_species != 1)):
                raise ValueError("Use full neutral native ideal-gas or pure stoichiometric-solid phases")
            if any(source is earlier for earlier in sources):
                raise ValueError("Factories must not share one native object between phases")
            copy, audit = (_private_native_phase(source, ct) if spec.role == "gas"
                           else _solid_copy(source, ct))
            if spec.role == "solid" and source.density_mass != evidence[spec.phase_id].density_kg_m3:
                raise ValueError("Native solid density differs from its explicit evidence")
            for element in copy.element_names:
                weight = copy.atomic_weight(element)
                if element in weights and weights[element] != weight:
                    raise ValueError("Phase element atomic-weight bases differ")
                weights[element] = weight
            sources.append(source)
            owned.append(copy)
            audits.append(audit)
        self.source_phases, self.owned_phases = tuple(sources), tuple(owned)
        self.phase_copy_audits = tuple(audits)
        self.atomic_weights_kg_kmol = MappingProxyType(weights)
        self._phase_indices = {p.phase_id: i for i, p in enumerate(self.phases)}
        self._mapped_indices = tuple(self.owned_phases[self._phase_indices[m.phase_id]].species_index(
            m.native_species) for m in self.species_mapping)
        species = []
        for mapping, index in zip(self.species_mapping, self._mapped_indices, strict=True):
            k = self._phase_indices[mapping.phase_id]
            native = owned[k].species(index)
            if any(not float(n).is_integer() or n <= 0 for n in native.composition.values()):
                raise ValueError("Host reactions require positive integer atomic counts")
            species.append(ChemicalSpecies(mapping.host_alias,
                {e: int(n) for e, n in native.composition.items()},
                owned[k].molecular_weights[index]/1000.,
                "ideal-gas" if self.phases[k].role == "gas" else "solid:"+mapping.phase_id))
        self.species = tuple(species)
        gas_providers, gas_bindings = {}, []
        for k, spec in enumerate(self.phases):
            if spec.role == "gas":
                names = tuple(m.native_species for m in self.species_mapping if m.phase_id == spec.phase_id)
                gas_providers[spec.phase_id] = CanteraMolarEnthalpy(
                    lambda native=owned[k]: native, spec.mechanism_basis, names)
                gas = gas_providers[spec.phase_id]
                gas_bindings.append((k, spec.phase_id, gas, owned[k], spec.mechanism_basis,
                                     tuple(gas._indices), tuple(gas.species), gas.basis_id))
        self.native_gas_providers = MappingProxyType(gas_providers)
        self._gas_bindings = tuple(gas_bindings)
        material = {
            "references": (self.energy_reference_id, self.hydrogen_partition_id),
            "mapping": [(m.phase_id, m.native_species, m.host_alias) for m in self.species_mapping],
            "phases": [(p.phase_id, p.role, p.mechanism_basis.identifier,
                        p.mechanism_basis.source_sha256, a.source_fingerprint, a.owned_fingerprint)
                       for p, a in zip(self.phases, audits, strict=True)],
            "density_evidence": {k: (v.density_kg_m3, v.source_id, v.origin, v.description)
                                 for k, v in evidence.items()},
        }
        self.basis_id = "cantera3.2-common-reference-molar-h:"+hashlib.sha256(
            json.dumps(material, sort_keys=True).encode()).hexdigest()

    def _require_definitions(self):
        for k, phase_id, gas, native, basis, indices, species, basis_id in self._gas_bindings:
            if (self.native_gas_providers.get(phase_id) is not gas
                    or gas.native_phase is not native or self.owned_phases[k] is not native
                    or gas.mechanism_basis != basis or self.phases[k].mechanism_basis != basis
                    or tuple(gas._indices) != indices or tuple(gas.species) != species
                    or gas.basis_id != basis_id):
                raise ValueError("Reused native gas caloric binding changed; rebind its evidence")
        for source, owned, audit in zip(self.source_phases, self.owned_phases,
                                        self.phase_copy_audits, strict=True):
            if (_phase_fingerprint(source, include_reactions=True) != audit.source_fingerprint
                    or _phase_fingerprint(owned, include_reactions=True) != audit.owned_fingerprint):
                raise ValueError("Native phase definition changed; rebind its thermochemical evidence")

    def enthalpies_j_mol(self, temperature_k, pressure_pa):
        temperature_k = finite(temperature_k, "temperature", positive=True)
        pressure_pa = finite(pressure_pa, "absolute pressure", positive=True)
        self._require_definitions()
        for spec in self.phases:
            spec.mechanism_basis.require_state(temperature_k, pressure_pa)
        for mapping, index in zip(self.species_mapping, self._mapped_indices, strict=True):
            thermo = self.owned_phases[self._phase_indices[mapping.phase_id]].species(index).thermo
            if not thermo.min_temp <= temperature_k <= thermo.max_temp:
                raise ValueError("State exceeds selected native species thermochemistry fit bounds")
        gas_values = {}
        for k, spec in enumerate(self.phases):
            native = self.owned_phases[k]
            # Composition is reset even though ideal-gas h_i is independent of X.
            composition = np.zeros(native.n_species)
            composition[0] = 1.
            native.TPX = temperature_k, pressure_pa, composition
            if spec.role == "gas":
                gas_values[spec.phase_id] = dict(zip(
                    (m.native_species for m in self.species_mapping if m.phase_id == spec.phase_id),
                    self.native_gas_providers[spec.phase_id].enthalpies_j_mol(temperature_k, pressure_pa),
                    strict=True))
        values = np.array([gas_values[m.phase_id][m.native_species]
            if self.phases[self._phase_indices[m.phase_id]].role == "gas"
            else self.owned_phases[self._phase_indices[m.phase_id]].enthalpy_mole/1000.
            for m in self.species_mapping])
        self._require_definitions()
        if not np.all(np.isfinite(values)):
            raise ValueError("Native molar enthalpies must be finite")
        values = immutable_array(values, name="values")
        return values
