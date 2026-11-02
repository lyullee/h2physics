# Finite thermochemical cycle enthalpy and material verification

Actual native Cantera3.2.0; SciPy1.18.1; 3.4620159s.

All extents, temperatures, clocks and solid densities are authored calorimetry inputs. No phase-stability, equilibrium/kinetic yield, source material or achievable iron-cycle claim is made. The existing reaction core owns finite conversion and native Cantera owns gas/solid enthalpies.

The fixed101325Pa campaign begins with1mol Fe3O4 at300K. It prescribes0.1mol reduction extent at1400K during[100,110]s; withdraws0.05mol O2 at1400K; admits0.1mol steam at500K; prescribes0.1mol steam oxidation at900K during[110,120]s; withdraws0.1mol H2 at900K; and returns the carrier to300K during[120,130]s. Component withdrawals are imposed boundary operations, not predicted separator performance. Native FeO/Fe3O4 source fits admit these caloric evaluations; this does not establish thermochemical reaction feasibility.

| Stage | Conditioning J | Reaction J | Total required heat J | Native-independent defect J |
|---|---:|---:|---:|---:|
| reduction | 226669.629592 | 28489.6284763 | 255159.258069 | 1.16415321827e-10 |
| steam-oxidation | -99086.9527804 | -3958.50567673 | -103045.458457 | -7.27595761418e-11 |
| carrier-reset | -125008.181065 | 0 | -125008.181065 | -4.36557456851e-11 |

Net duty=27105.6185471J; gross input=255159.258069J; gross rejected=228053.639522J. Independent hot exports minus cold feed=27105.6185471J. Global energy defect=7.27595761418e-12J; mass defect=0kg; max element defect=0mol.

Heat is required signed constant-pressure enthalpy input, not a predicted furnace power or utility. Mean W divides by the caller's stage duration; no residence time is inferred. No heat recovery, thermal storage, optical absorption, pressure-change work, non-PV work, mixture excess heat or solar efficiency is assumed. Carrier, thermal and complete-inventory closure remain separate tests.

| Gate | Pass |
|---|---|
| executed sources unchanged | True |
| actual native caloric phases and existing reaction conversions retained | True |
| carrier composition and temperature return without resetting amounts | True |
| finite water feed and separate H2/O2 export ratio | True |
| global element and mass defects below1e-12mol/1e-14kg | True |
| stage and global enthalpy ledgers below1e-6J | True |
| fresh native mixture reconstructs every stage heat below1e-6J | True |
| net heat equals actual hot-product less cold-feed enthalpy below1e-6J | True |
| gross input less rejection equals signed net duty below1e-8J | True |
| different finite supplied conversion retains correct material scaling | True |
| incomplete carrier loop retains completed trace | True |
| over-depletion rejects without inventing conversion or feed | True |
| reused native caloric buffer preserves all stage heat below1e-8J | True |
| finite input with extensive overflow rejects with actual stage and cause | True |

Primary context: [DOE thermochemical cycles](https://www.energy.gov/cmei/fuels/hydrogen-production-thermochemical-water-splitting), [native NASA thermochemistry provenance](https://ntrs.nasa.gov/citations/19940013151), [native Cantera properties](https://cantera.org/3.2/python/thermo.html). No published operating table, coefficient array, worked example or source implementation is bundled.

## Executed source identities

| Host source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| `src/h2physics/thermochemical.py` | `23e151a9c4b6bc70a96f61b65ccab185198fa05da5e3449e86e70ec598bdff20` | `23e151a9c4b6bc70a96f61b65ccab185198fa05da5e3449e86e70ec598bdff20` |
| `tests/test_thermochemical.py` | `d1d0f426452f0d7b4d45e9e1ce30eabc557971dabcc46a8fc1c07ee9df97da7d` | `d1d0f426452f0d7b4d45e9e1ce30eabc557971dabcc46a8fc1c07ee9df97da7d` |
| `scripts/check_thermochemical_cycle.py` | `932c36dc0e7923da33d09a0d4b0913f820711ba6ddf113b59248826ab6fcc38f` | `932c36dc0e7923da33d09a0d4b0913f820711ba6ddf113b59248826ab6fcc38f` |
| `src/h2physics/reactions.py` | `3748b88bd70a2c0572faa32fd83be8c43a47b124d92dd905c1923d47963caf35` | `3748b88bd70a2c0572faa32fd83be8c43a47b124d92dd905c1923d47963caf35` |
| `src/h2physics/adapters/cantera_caloric.py` | `1b1cad4e3592143c9c103ec5870453677c034e68e953b16884f4b9b3184e672d` | `1b1cad4e3592143c9c103ec5870453677c034e68e953b16884f4b9b3184e672d` |
| `docs/THERMOCHEMICAL_CYCLES.md` | `49e7151c655a0b2925ffd5ec39a63c68ef4ebe223d3a1e476b7862a71bd8ded2` | `49e7151c655a0b2925ffd5ec39a63c68ef4ebe223d3a1e476b7862a71bd8ded2` |
