"""Predictive, finite two-solid redox equilibrium using native Cantera phases.

The shared native multiphase adapter owns Gibbs minimization and all fluid and
solid thermochemistry. This layer maps its accepted equilibrium to an existing
balanced finite reaction, its required isothermal heat, and an optional declared
equilibrium-relaxation rate for the existing finite-solid reactor.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..adapters.cantera import MechanismBasis
from ..adapters.cantera_caloric import (
    CaloricSpeciesMapping,
    CanteraMultiphaseMolarEnthalpy,
    SolidDensityEvidence,
)
from ..adapters.cantera_multiphase import (
    CanteraMultiphaseEquilibrium,
    EquilibriumPhase,
    MultiphaseFeed,
    MultiphaseSettings,
)
from ..core import Origin, finite
from ..reactions import ReactionConversion, StoichiometricReaction
from .solid_reaction import SolidReactionKinetics


@dataclass(frozen=True, slots=True)
class RedoxEquilibriumResult:
    conversion: ReactionConversion
    temperature_k: float
    pressure_pa: float
    heat_into_j: float
    caloric_basis_id: str
    source_id: str
    maximum_stoichiometry_residual_mol: float
    native_result: object


class TwoSolidRedoxEquilibrium:
    """One reaction spanning one reacting gas and two pure stoichiometric solids.

    Candidate gas species must be exactly those mapped to the balanced reaction.
    Competing oxides, nonstoichiometric vacancies, solid solutions, nucleation,
    transport and intrinsic rates require a different declared material model.
    """

    def __init__(self, phases, species_mapping, coefficients, *, identifier: str,
                 solid_density_evidence: Mapping[str, SolidDensityEvidence],
                 source_id: str):
        self.phases = tuple(phases)
        if not identifier.strip() or not source_id.strip():
            raise ValueError("Declare reaction identity and material-data provenance")
        if len(self.phases) != 3 or sum(p.role == "solid" for p in self.phases) != 2:
            raise ValueError("This model requires one gas and exactly two pure solids")
        self.caloric = CanteraMultiphaseMolarEnthalpy(self.phases, species_mapping,
            solid_density_evidence=solid_density_evidence)
        self.reaction = StoichiometricReaction(identifier, self.caloric.species, tuple(coefficients))
        self.equilibrium = CanteraMultiphaseEquilibrium(self.phases)
        self.species_mapping = self.caloric.species_mapping
        self.source_id = source_id
        gas_phase = next(p for p in self.phases if p.role == "gas")
        gas_names = {m.native_species for m in self.species_mapping if m.phase_id == gas_phase.phase_id}
        if gas_names != set(gas_phase.factory().species_names):
            raise ValueError("Map every candidate gas species; hidden gas reactions are unsupported")
        # Three independent elements in four species give one reaction for the
        # iron-oxide example. Check the same one-dimensional extent assumption
        # for any caller-supplied material rather than silently project several
        # equilibrium reactions onto a single supplied extent.
        elements = sorted({e for s in self.reaction.species for e in s.elements})
        atoms = np.array([[s.elements.get(e, 0) for s in self.reaction.species] for e in elements])
        if len(self.reaction.species)-np.linalg.matrix_rank(atoms) != 1:
            raise ValueError("Declared candidate phases must have exactly one reaction degree of freedom")

    @property
    def basis_id(self):
        """Same formation-enthalpy reference used by the finite-solid reactor."""
        return self.caloric.basis_id

    def equilibrate(self, amounts_mol: Mapping[str, float], *, temperature_k: float,
                    pressure_pa: float, source_id: str,
                    origin: Origin = Origin.PREDICTED,
                    settings: MultiphaseSettings = MultiphaseSettings()) -> RedoxEquilibriumResult:
        """Predict signed finite extent and isothermal heat; no conversion input.

        Positive extent follows the declared balanced reaction. A negative result
        means reverse conversion is favoured by the supplied finite composition.
        The required fixed-T/P heat is supplied externally; it is not a heat-
        recovery prediction. The native result retains all original audit gates.
        """
        finite(temperature_k, "temperature", positive=True)
        finite(pressure_pa, "pressure", positive=True)
        for phase in self.phases:
            phase.mechanism_basis.require_state(temperature_k, pressure_pa)
        initial = self.reaction.amounts(amounts_mol)
        feed = {p.phase_id: {} for p in self.phases}
        for mapping, amount in zip(self.species_mapping, initial, strict=True):
            feed[mapping.phase_id][mapping.native_species] = float(amount)
        native = self.equilibrium.equilibrate(MultiphaseFeed(temperature_k, pressure_pa,
            feed, source_id, origin), settings=settings)
        native.require_current()
        final = np.array([native.amount_mol(m.phase_id, m.native_species) for m in self.species_mapping])
        coefficients = np.asarray(self.reaction.coefficients)
        pivot = int(np.argmax(np.abs(coefficients)))
        extent = float((final[pivot]-initial[pivot])/coefficients[pivot])
        lo, hi = self.reaction.extent_limits_mol(amounts_mol)
        scale = max(float(initial.sum()), 1e-12)
        # Native equilibrium may differ from a finite pure-phase endpoint by
        # roundoff. Reject a physical discrepancy; record the actual mapping
        # error while admitting only this bounded numerical endpoint correction.
        tol = 1e-8*scale + 1e-12
        if not lo-tol <= extent <= hi+tol:
            raise ValueError("Native equilibrium exceeds the finite balanced-reaction bounds")
        extent = min(hi, max(lo, extent))
        conversion = self.reaction.convert(amounts_mol, extent)
        residual = float(np.max(np.abs(conversion.final_mol-final)))
        if residual > tol:
            raise ValueError("Native equilibrium is not represented by the declared single reaction")
        return RedoxEquilibriumResult(conversion, float(native.final.temperature_k),
            float(native.final.pressure_pa), float(native.heat_into_j), self.basis_id,
            self.source_id, residual, native)

    def relaxation_kinetics(self, relaxation_rate_s: float, *, identifier: str,
                            source_id: str, origin: Origin) -> SolidReactionKinetics:
        """Connect predicted equilibrium to the existing forward finite reactor.

        Rate = k times the remaining positive equilibrium extent. k [1/s] must
        come from an identified material fit or be marked synthetic. This is a
        lumped relaxation closure, not intrinsic surface chemistry. The existing
        reactor owns time stepping, feed stocks and thermal balance. Reverse
        thermodynamic driving returns zero in that forward-only reactor.
        """
        rate = finite(relaxation_rate_s, "relaxation rate 1/s")
        if rate < 0:
            raise ValueError("Relaxation rate cannot be negative")
        def evaluate(state, parameters):
            if state.inventory.energy_basis_id != self.basis_id:
                raise ValueError("Finite reactor and redox closure have different caloric references")
            equilibrium = self.equilibrate(state.inventory.amounts_mol,
                temperature_k=state.inventory.temperature_k, pressure_pa=state.inventory.pressure_pa,
                source_id=source_id, origin=origin)
            return parameters["relaxation_rate_s"]*max(0., equilibrium.conversion.extent_mol)
        return SolidReactionKinetics(self.reaction, evaluate, identifier, source_id, origin,
                                     {"relaxation_rate_s": rate})


def iron_oxide_steam_redox(*, ferrous_density: SolidDensityEvidence,
                           magnetite_density: SolidDensityEvidence) -> TwoSolidRedoxEquilibrium:
    """Restricted FeO/Fe3O4 + H2/H2O equilibrium, 900–1500 K, 0.1–10 bar.

    Native installed Cantera NASA species provide thermochemistry; coefficients
    are not copied into this package. Both constant solid densities need explicit
    external evidence. The two-oxide candidate set does not establish global
    iron/oxygen phase stability or fit nonstoichiometric wuestite. Phase-domain
    qualification and measured material conversion data remain separate work.
    """
    import cantera as ct
    if not isinstance(ferrous_density, SolidDensityEvidence) or not isinstance(magnetite_density, SolidDensityEvidence):
        raise TypeError("Supply explicit SolidDensityEvidence for both pure solids")
    data_directory = Path(ct.__file__).parent / "data"
    raw_gas = (data_directory/"h2o2.yaml").read_bytes()
    raw_solid = (data_directory/"nasa_condensed.yaml").read_bytes()
    source = "Cantera-"+ct.__version__+":h2o2.yaml+nasa_condensed.yaml; restricted-two-oxide-candidates"
    reference = "native-NASA-formation-and-third-law; FeO-Fe3O4-H2-H2O"
    partition = "native-H2-spin-not-resolved"
    # Python preserves non-ASCII installation paths that some Windows native
    # file resolvers cannot read. Parse the unchanged, hash-bound provider bytes.
    gas_species = tuple(s for s in ct.Species.list_from_yaml(raw_gas.decode("utf-8"), section="species")
                        if s.name in {"H2", "H2O"})
    solid_species = {s.name: s for s in ct.Species.list_from_yaml(raw_solid.decode("utf-8"), section="species")
                     if s.name in {"FeO(s)", "Fe3O4(s)"}}
    def basis(name, raw):
        return MechanismBasis(name, hashlib.sha256(raw).hexdigest(),
            "Cantera-BSD-3-Clause; installed NASA thermochemical data attribution",
            ("https://cantera.org/3.2/python/thermo.html",), 900., 1500., 1e4, 1e6)
    def gas_factory():
        phase = ct.Solution(name="restricted-H2-H2O", thermo="ideal-gas", species=gas_species)
        phase.TP = 1000., 101325.
        return phase
    phases = [EquilibriumPhase("gas", "gas", gas_factory, basis("restricted-H2-H2O",raw_gas), reference, partition)]
    densities = {"ferrous": ferrous_density, "magnetite": magnetite_density}
    for phase_id, species_name in (("ferrous", "FeO(s)"), ("magnetite", "Fe3O4(s)")):
        density = densities[phase_id].density_kg_m3
        def solid_factory(name=phase_id, native_name=species_name, rho=density):
            definition = dict(solid_species[native_name].input_data)
            definition["equation-of-state"] = {"model": "constant-volume", "density": f"{rho} kg/m^3"}
            species = ct.Species.from_dict(definition)
            phase = ct.Solution(name=name, thermo="fixed-stoichiometry", species=[species])
            # Explicit native initialization resolves constant-volume standard-
            # state metadata before the shared exact definition seal is bound.
            phase.TP = 1000., 101325.
            return phase
        phases.append(EquilibriumPhase(phase_id, "solid", solid_factory,
            basis("installed-NASA-"+species_name, raw_solid), reference, partition))
    mappings = (CaloricSpeciesMapping("ferrous", "FeO(s)", "FeO"),
        CaloricSpeciesMapping("gas", "H2O", "H2O"),
        CaloricSpeciesMapping("magnetite", "Fe3O4(s)", "Fe3O4"),
        CaloricSpeciesMapping("gas", "H2", "H2"))
    return TwoSolidRedoxEquilibrium(phases, mappings, (-3.,-1.,1.,1.),
        identifier="three-ferrous-oxide-plus-steam-to-magnetite-and-hydrogen",
        solid_density_evidence=densities, source_id=source)
