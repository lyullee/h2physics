# Computed carrier reactions and constrained calorimetry

This is data qualification and software/numerical verification. It is not measured liquid-carrier, catalyst, kinetic, equilibrium or process validation.

## Actual acquired data

Hassan Harb, HydrogenStorage/QM9-LOHC, release QM9-LOHC, [Zenodo 10.5281/zenodo.10926772](https://doi.org/10.5281/zenodo.10926772), CC BY 4.0. Interpretation uses the independently accessible [primary descriptor](https://doi.org/10.1038/s41597-025-04468-0). Its reference is gas-phase dehydrogenation at 298.15 K and 1 atm, in kJ/mol H2. Publisher values stay unmodified. Raw data and native molecular objects are excluded from public distributions.

Archive SHA-256 `9f89ee72586dd00e5be58c0650b11d2e135e993873f90da23c8094c5265ee242`; authoritative CSV SHA-256 `835702d576486662b70b84f26c9f0760e4b50888db1794448d07725832049ffc`.
Rows: 10373; unique canonical ordered pairs: 10345; extra repeated-pair rows: 28; admitted reference-heat rows: 10317. Repeated pairs and the duplicate web CSV are not independent reactions or validation data.

Repeated molecular-pair groups: 28; largest within-pair enthalpy spread: 7.98086363 kJ/mol H2. Conflicting pairs retain every original row, but all their reference heats are withheld by the dataset-level API. No average or first-row selection is used without additional molecular-state evidence.

Native mass reconstruction uses RDKit 2026.9.1 average atomic weights for both carriers and H2; explicit isotopes/radicals are rejected by this level. The source molar_mass column is tested against the lean species. Source capacity differences are recorded at an explicit 0.01 percentage-point reporting threshold; a capacity discrepancy cannot change molecular stoichiometry or its computed heat.

| Source issue | Rows |
|---|---:|
| conflicting_reference_enthalpies_for_canonical_pair | 56 |
| reported_capacity_differs_from_native_mass_basis | 9 |

Capacity reconstruction minus publisher range: -0.01136424119 to 0.001742088509 percentage points; maximum absolute lean mass difference: 1.421085472e-14 g/mol.

Rows without an admitted heat remain available with original cells, CSV line and member/archive identity. No unqualified row is silently repaired or dropped.

Largest accepted mass residual: 7.4593109467e-17 kg; reverse-cycle error: 0 mol; capacity-scaling error: 0. Aggregate reference duty for one mole extent per admitted row is 3799597667.98 J. That aggregate is a reproducibility checksum, not a realizable carrier blend.

## Native thermochemistry reuse

Cantera 3.2.0, installed gri30.yaml SHA-256 `06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345`. The native phase object, molecular weights, species compositions and caloric fits are used directly. Mechanism files are not bundled. Source/license context is [Cantera GRI input documentation](https://cantera.org/3.2/examples/input/gri30.html). This authored CH4/H2O -> CO + 3 H2 case imposes extent, without a catalyst or rate claim. Existing native equilibrium/reactor modules retain those solvers.

At 298.15 K and 101325 Pa: reaction heat 205894.826377 J/mol extent; mixture/species accounting difference 3.49245965481e-10 J. For one initial mol CH4, three mol steam, imposed extent 0.2 mol, inlet 1200 K and zero supplied heat: outlet 980.323959909 K, enthalpy residual 1.16415321827e-10 J. The fitted thermochemistry's previously documented breakpoint behavior is not changed.

## Authored numerical acceptance gates

| Gate | Result |
|---|---|
| authoritative row count | PASS |
| archive web table is an exact duplicate | PASS |
| all source rows have balanced molecular reactions | PASS |
| versioned qualified reference-heat count | PASS |
| conflicting canonical-pair heats withheld | PASS |
| accepted molecular mass conservation <1e-12 kg per mol extent | PASS |
| accepted forward/reverse inventory cycle <1e-12 mol | PASS |
| accepted independent capacity scaling <1e-14 mass fraction | PASS |
| native mixture/species heat paths <1e-7 J | PASS |
| native prescribed-extent calorimetry <1e-6 J | PASS |

These gates assess admitted data paths and bookkeeping; they do not require all publisher rows to be admissible, nor prove measured reaction heat, liquid stability, reversibility, safety or equipment performance.

## Reproduction fingerprints

| File | SHA-256 |
|---|---|
| src/h2physics/reactions.py | `3748b88bd70a2c0572faa32fd83be8c43a47b124d92dd905c1923d47963caf35` |
| src/h2physics/data/lohc.py | `f56f9ea9e13d780c6559325a1a8aa943abf50f006f6054b7888e33ef18d79866` |
| src/h2physics/adapters/rdkit.py | `477b0e80ee043718478d88a8a786debb0f04244202d9d612fed1e46d918247f1` |
| src/h2physics/adapters/cantera_thermo.py | `f5bf30b7536c432fd84f9b7c4b81a72949dc936a9662a7c89f15ea8a62e8d027` |
| scripts/check_reaction_models.py | `3bdc02f7629e52327fa3e3ad2ba5bd98741d7ee6aa19f9ab736a75f3e92f5bba` |
