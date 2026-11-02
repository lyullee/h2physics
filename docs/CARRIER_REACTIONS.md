# Carrier reaction inventory and calorimetry

This level calculates finite material conversion, molecular hydrogen capacity and the
heat associated with a **supplied reaction extent**. It does not predict catalyst rate,
equilibrium extent, liquid stability or reactor residence time. The same conservation
and caloric functions can serve chemical-storage and production models; no additional
gas kinetics, equilibrium or thermodynamic solver is introduced.

## Installation and actual data replay

```powershell
.venv\Scripts\python -m pip install -e ".[molecules,chemistry]"
.venv\Scripts\python scripts/check_reaction_models.py
```

Acquire the source with `scripts/acquire_data.py --keys lohc-enthalpies` first, following
DATA.md. The versioned receipt is `research/data/lohc-enthalpies.toml`. External raw data
remain ignored and excluded from distributions. The optional molecule dependency is
RDKit 2026.9.1; the caloric example reuses the existing Cantera 3.2.0 dependency.

The actual acquired QM9-LOHC archive contains 10,373 authoritative reaction rows and a
byte-identical web copy of that table. Native canonicalization finds 10,345 distinct
ordered molecular pairs. All 28 repeated pairs have conflicting reported enthalpies;
their 56 rows retain original cells but supply no heat in the dataset-level API.
The remaining 10,317 rows admit a computed reference heat. Nine capacity values differ
from the consistently reconstructed native atomic-weight basis beyond the declared
0.01 percentage-point reporting threshold; no source value is repaired.

Those counts describe this exact release and method, not measured validation. Read
`research/carrier_reactions.md` for source fingerprints, issue counts and residuals.

## Meaning of the data

Hassan Harb's [QM9-LOHC release](https://doi.org/10.5281/zenodo.10926772), CC BY 4.0,
is interpreted with its [primary descriptor](https://doi.org/10.1038/s41597-025-04468-0).
The reference heat is computed with G4MP2 for **gas-phase dehydrogenation at 298.15 K
and 101325 Pa**, in **kJ per mol H2**. Thus for

`rich -> lean + n H2`,

the host reaction enthalpy in J per mol extent is `1000 * n * publisher_delta_H`.
Positive duty means heat supplied to the material. A negative extent reverses the
material change and heat sign, subject to finite available lean species and H2.
The `molar_mass` column corresponds to the lean species, while gravimetric capacity
uses the rich carrier as denominator. Neither an isolated carrier mass fraction nor
a computed heat establishes usable vessel/system capacity, cycle reversibility or safety.

Molecular topology is parsed by the separately installed native RDKit. The adapter
retains its actual molecule, canonical isomeric SMILES, element counts, formal charge,
average molar mass and version. This level rejects isotope-labeled and radical inputs
rather than treating them as an unspecified ordinary atomic-weight basis. It does not
infer a liquid phase from an organic SMILES string.

## Python use

```python
from h2physics.data.lohc import load_qm9_lohc_archive, audit_qm9_lohc_dataset

archive = load_qm9_lohc_archive(
    "data/raw/lohc-enthalpies/QM9-LOHC/QM9-LOHC-QM9-LOHC.zip"
)
audits = audit_qm9_lohc_dataset(archive)
accepted = [row for row in audits if row.reference_heat is not None]

# An explicit source row is selected here; a research application should select its
# intended chemical identity and retain the row/source, rather than choose by rank.
row = accepted[0]
conversion = row.reaction.convert({"rich": 2.0}, extent_mol=0.5)
heat_j = row.reference_heat.heat_j(
    conversion, temperature_k=298.15, pressure_pa=101325.0
)
amounts = conversion.final_amounts
```

`audit_lohc_reaction(row)` is a **row-local diagnostic**. It cannot detect contradictions
in other rows. Use `audit_qm9_lohc_dataset(archive)` before supplying any data-derived
heat to a model. It withholds all conflicting pair heats, without averaging or selecting
the first row. Original CSV line, member/archive identity and cells remain available.
The archive reader verifies the declared SHA-256, expected columns, bounded member
sizes and duplicate names. It reads the one numeric table without extracting or executing
any archived notebook, application or bytecode. A changed release needs another audit.

## Finite conservation contract

`ChemicalSpecies` declares identity, element counts, charge, phase and kg/mol on one
atomic-weight basis. `StoichiometricReaction` checks element, charge and mass conservation
separately. Negative coefficients consume species; positive coefficients produce species;
zero coefficients represent explicitly declared spectators.

`extent_limits_mol(initial)` returns both reverse and forward limits. Missing declared
species begin at zero; foreign names, negative/nonfinite amounts and out-of-range extents
fail. `convert` returns read-only initial/final arrays, immutable named amounts and the
actual mass residual. A possible one-rounding-unit endpoint correction is reported as
`maximum_roundoff_correction_mol`; it is never used to permit an extent outside the limits.
There is no assumed infinite hydrogen reservoir or implicit discarded product stream.

## Temperature-dependent heat and native reuse

`FunctionalMolarEnthalpy` accepts actual caller-owned functions `h_i(T, P)` in J/mol,
species/order/phase identity, a common formation/reference basis and bounded T/P domain.
An EOS's arbitrary sensible enthalpy zero alone cannot supply chemical formation energy.
CoolProp callbacks may supply qualified phase/sensible terms only after the caller has
anchored all participating species to a compatible reaction-energy basis. Unrelated
CoolProp and native mechanism references must not be summed as formation enthalpies.

`conversion_heat_j` computes `sum(n_out*h_out) - sum(n_in*h_in)` at the declared common
pressure, with positive heat into the material. Shaft work, kinetic energy, vessel wall
storage, phase transfer and separate stream pressures require explicit additional models.
`solve_product_temperature` solves that enthalpy balance in a user-supplied temperature
bracket at the imposed extent and supplied heat. Its result retains the residual and
energy basis. Bracket/domain failure is an error, never a substituted temperature.

`CanteraMolarEnthalpy` uses actual native ideal-gas species composition, molar masses and
partial molar enthalpies, converting J/kmol to J/mol exactly once. The native phase is
retained as `native_phase`. The mechanism's declared domain and selected species' fit
bounds are enforced. Native thermochemistry is not copied or refitted. This provider
is stateful and should be separately instantiated per concurrent worker.

The reproducible CH4 + H2O -> CO + 3 H2 example imposes conversion and checks the result
against the native whole-mixture enthalpy path. It is a calorimetry example using installed
GRI-Mech thermochemistry, not a qualified reforming catalyst model. The existing
`CanteraGas.equilibrium` and `.closed_reactor` continue to own their respective native
equilibrium and kinetic calculations. Existing fit-breakpoint limitations remain visible.

## Evidence and remaining research

The checks cover analytic finite/reactant limits, reverse material/heat cycles,
element-based enthalpy-reference invariance, an analytic constant-Cp calorimetric limit,
actual full-table molecular checks, conflicting identities and native enthalpy accounting.
Authored fixtures contain newly chosen test inputs and no copied dataset table.

Measured reaction heats, phase-change thermochemistry, liquid mixtures, solubility,
catalyst kinetics/deactivation, residence time and finite coupled gas/wall inventories
remain open. Heat alone cannot determine equilibrium: entropy/free-energy evidence is
also needed. A reaction extent is not an accident source; clocks, flows, pressure,
temperature, spin/reference, transfer geometry and termination are required before any
hydrogen amount can connect to existing equipment/release consumers.
