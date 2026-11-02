# Common-reference gas and pure-solid molar calorimetry

`CanteraMultiphaseMolarEnthalpy` implements the existing
`MolarEnthalpyProvider.species`, `basis_id`, and `enthalpies_j_mol(T,P)` contract.
Actual Cantera3.2 owns every caloric and pressure correction. The bridge reuses
`CanteraMolarEnthalpy` for ideal-gas partial enthalpies and the audited independent
gas/pure-solid copy paths from the existing native adapters. No new EOS, heat
capacity fit, equilibrium algorithm or reaction trajectory is introduced.

The intended consumer is existing `StoichiometricReaction.convert` and
`conversion_heat_j`, including a finite staged process with externally supplied
extent. A thermochemical table does not establish equilibrium yield, reaction
rate, phase stability, catalyst activity or feasibility of a practical cycle.

## Deep Python construction

The following constructs native phases from separately installed source bytes.
The **4800 and5000kg/m3 densities are authored verification fixtures**, not
measured magnetite/wustite densities. The installed condensed-species file has
thermochemical fits but supplies no EOS/density for these two species. A real
application must replace those fixture values and evidence with appropriate
phase/volume evidence. The native library implements their constant-volume EOS.

```python
import hashlib
from pathlib import Path
import cantera as ct
from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_multiphase import EquilibriumPhase
from h2physics.adapters.cantera_caloric import (
    CanteraMultiphaseMolarEnthalpy, SolidDensityEvidence,
)
from h2physics.core import Origin

data = Path(ct.__file__).parent / "data"
reference = "declared-native-NASA-standard-formation-reference"
spin = "native-mechanism-H2-spin-unresolved"

def phase(phase_id, native_species=None, density=None):
    file = "h2o2.yaml" if native_species is None else "nasa_condensed.yaml"
    raw = (data / file).read_bytes()
    def factory():
        if native_species is None:
            return ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
        selected = next(s for s in ct.Species.list_from_yaml(
            raw.decode("utf-8"), "species") if s.name == native_species)
        definition = dict(selected.input_data)
        definition["equation-of-state"] = {
            "model": "constant-volume", "density": density,
        }
        result = ct.Solution(
            thermo="fixed-stoichiometry", species=[ct.Species.from_dict(definition)],
            name=phase_id, transport_model="none",
        )
        result.TP = 300., 101325.
        return result
    basis = MechanismBasis(
        "installed-" + file + ":" + phase_id, hashlib.sha256(raw).hexdigest(),
        "Cantera BSD-3-Clause; upstream NASA thermochemistry provenance",
        ("https://ntrs.nasa.gov/citations/19940013151",),
        300., 1650., 1e4, 2e6,
    )
    return EquilibriumPhase(phase_id, "gas" if native_species is None else "solid",
                            factory, basis, reference, spin)

phases = (phase("Fe3O4", "Fe3O4(s)", 4800.),
          phase("FeO", "FeO(s)", 5000.), phase("gas"))
mapping = (("Fe3O4", "Fe3O4(s)", "Fe3O4"),
           ("FeO", "FeO(s)", "FeO"),
           ("gas", "H2O", "H2O"), ("gas", "H2", "H2"), ("gas", "O2", "O2"))
evidence = {name: SolidDensityEvidence(
    density, "authored-calorimetry-fixture:" + name, Origin.SYNTHETIC,
    "Constant-density verification fixture; no measured solid EOS claim",
) for name, density in (("Fe3O4", 4800.), ("FeO", 5000.))}
caloric = CanteraMultiphaseMolarEnthalpy(
    phases, mapping, solid_density_evidence=evidence,
)
enthalpy_j_mol = caloric.enthalpies_j_mol(1400., 101325.)
native_magnetite, native_wustite, native_gas = caloric.owned_phases
```

Mapping order is exactly the provider's `ChemicalSpecies` and output-array order.
Each `(phase_id,native_species,host_alias)` pair and alias must be unique; every
declared phase must be represented. `CaloricSpeciesMapping` is an alternative to
tuples. Host aliases are independent of native names, allowing explicit phase
identity even for polymorphs. Solid phase labels are `solid:<phase_id>`; ideal
gas species use `ideal-gas`. The same complete `caloric.species` tuple can be
used for every stage reaction, with coefficients zero for unaffected species.
Atomic counts and kg/mol masses come from native species and kg/kmol weights.

For the mapping above, externally imposed reduction has coefficients
`(-1,3,0,0,.5)` and steam oxidation `(1,-3,-1,1,0)`. These represent
Fe3O4→3FeO+.5O2 and3FeO+H2O→Fe3O4+H2. No conversion extent or preferred
temperature is inferred. The replay uses finite quantities and checks the net
water-splitting caloric balance after the solid inventory returns to its initial
composition. Heat recovery, solar absorption, vacuum work, equipment losses,
chemical equilibrium and achievable reduction temperature need other models.

## Reference, phase and pressure contracts

All phases must carry the same explicit formation-energy and hydrogen-partition
identities. A common string is a caller provenance declaration; the adapter
cannot prove caloric-zero compatibility of arbitrary sources. The native NASA
formation energies remain included. No independent sensible-enthalpy zero,
CoolProp offset or ParaHydrogen/spin-mixture reference is substituted. Atomic
weights for shared elements must match exactly across phases.

The checked gas model is neutral ideal gas. Solids are neutral, pure,
fixed-stoichiometry constant-volume phases, with explicit density evidence whose
value matches the actual native phase. At most one gas phase is admitted; a
solid-only provider is also possible. Phase roles and stable temperature ranges
are caller evidence. Fit bounds alone do not establish a stable phase. In
particular, the broad Fe3O4(s) fit is not a claim that magnetite remains the
stable material throughout that range.

Each query enforces finite positive absolute T/P, every declared mechanism
envelope and every **selected species'** native fit bounds. Installed FeO(s)
is300–1650K, Fe3O4(s)300–5000K; the demonstration uses their300–1650K
intersection, restricted further by the caller's gas/phase evidence. It does
not select FeO(L), interpolate a phase transition, force saturation or extrapolate.

Native partial molar gas enthalpy and pure-solid molar enthalpy are divided
by1000 from J/kmol to J/mol. Solid pressure dependence is retained. For the
native constant-volume solid, `H-U=P*V` and the enthalpy difference between
pressures is `delta_P*V`; using only a species' reference-pressure polynomial
would omit this correction. These identities are independently checked against
native phase H/U/volume. Ideal-gas species enthalpy is pressure independent.
The provider returns H; it does not rename that energy as rigid-volume U.

`conversion_heat_j` gives `H_final-H_initial`, positive heat into a constant-P
finite conversion with no separately imposed shaft/kinetic terms. Native
formation energy already participates in H. Adding a separate nominal reaction
heat would double count it. No physical clock or reaction duration is implied.

## Ownership and audit scope

The original `EquilibriumPhase` factories and source metadata are retained in
`phases`. `source_phases`, `owned_phases`, `phase_copy_audits`,
`native_gas_providers` and `solid_density_evidence` expose the actual objects.
Native Species objects are independently reconstructed; the original thermo
objects are not reused. Exact native fit bounds/coefficients/reference pressure
are restored by the existing copy helpers. Source and actual owned hashes are
separate because native serialization can change notes/units or incur audited
tiny parameter roundtrips.

Every property query checks source and owned exact definition fingerprints,
including gas reactions and runtime multipliers, before/after calculation.
The reused gas provider must remain bound to the original owned native phase,
selected native indices, species/order, `MechanismBasis` and caloric `basis_id`.
Rebinding its exposed `native_phase` to another actual native object is rejected
even if the original owned phase remains unchanged. An actual alternate-phase
regression shifts H2's native formation offset and verifies rejection under the
old basis; separate regressions change each exposed binding metadata field.
Mutation is rejected until a new provider with rebound evidence is constructed.
State/composition changes are reset at every query. Definitions remain native
and inspectable; returned enthalpy arrays are immutable snapshots. This mutable
native provider is not intended for concurrent queries on the same instance.

## Reproduction and rights

Run `python scripts/check_cantera_caloric.py`; detailed evidence is in
research/multiphase_calorimetry.md. The replay executes actual native gas and
iron-oxide properties, native Mixture extensive H, independent U/PV checks,
finite two-stage conversion, a product-temperature roundtrip, native Cp derivative
checks and deliberate domain/reference/definition failures. It fingerprints
host/test/script/docs, reused host contracts, installed thermochemical files,
the Cantera compiled binary and license before/after computation, and records LF.

Cantera3.2 implementation is BSD-3-Clause. The installed condensed-species file
identifies [NASA TM-4513](https://ntrs.nasa.gov/citations/19940013151), whose
publisher record marks public distribution and US-government public use.
Source-specific provenance remains distinct from the software license. No native
coefficient table, mechanism, printed example or experimental dataset is bundled.
See the [native thermodynamic API](https://cantera.org/3.2/python/thermo.html),
[fixed-stoichiometry phase model](https://cantera.org/3.2/reference/thermo/phase-thermo.html),
and [versioned condensed-species provenance](https://github.com/Cantera/cantera/blob/v3.2.0/data/nasa_condensed.yaml).
These checks are software/thermochemical verification, with no measured iron-cycle
validation or industrial qualification.
