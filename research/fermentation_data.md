# Dark-fermentation v2 complete-source qualification

Roberto Hernández, [Raw data, version 2](https://doi.org/10.17632/2nwcdx9hst.2), CC BY 4.0. The pinned metadata and actual acquired workbook were inspected read-only. This original audit reproduces no source prose, measured-data table, publication figure or source program.

Complete offline scan: 0.50s. Workbook/publisher checksum, pinned and supporting metadata and source begin/end hashes matched. No formulas or links were executed, source rows changed, interpolated or repaired.

- Actual dimensions: 831 x 24; 830 data rows / 19920 source data cells.
- Cached numeric cells: 13280; strict decimal numeric strings: 700.
- Blank cells: 3893; source `--` placeholders: 2047.
- Valid numeric observations: 13980; invalid reasons: {'source_missing_placeholder': 2047, 'source_blank': 3893}.
- Source formula cells: 0; missing formula caches: 0; error cells: 0.
- Nonincreasing per-reactor Duration edges retained: 4.
- Source Nr discontinuities: 25; identifier skips total 40.0. Missing identifiers do not create invented rows.

| Source reactor label | Source rows | First/last worksheet row | Valid COD in/out cells | Valid other chemistry cells |
|---|---:|---|---|---:|
| R-1 | 287 | 2/288 | 81/83 | 85 |
| R-2 | 273 | 289/561 | 73/77 | 84 |
| R-3 | 270 | 562/831 | 75/76 | 66 |

R is retained as a reactor identifier; independent replicates or common forcing are not established. All reactors therefore share one study experiment group. Blocks do not mix reactor clock bases. Duration's declared days convert to seconds without assigning a common day-zero, event clock or correcting repeated days. Automatic TimeSeries conversion and independent reactor holdout claims are not supplied.

## Same-export algebra, not biological validation

The executable comparison operator checks HP against BP times reported H2 volume fraction and MP against BP times reported CH4 volume fraction on the same reported-volume convention. It retains source rows, masks and reconstructed origin. It supplies no mass/molar yield, gas reference state, physical reactor volume, kinetics or independent measured target.

At an explicitly declared algebraic tolerance of 1e-09 reported L/d (not noise sigma), 2 component fields differ across source worksheet row(s) [239]. Their values remain unaltered. Maximum absolute residual: 1.75824890722 reported L/d.
The listed gas fractions close numerically with maximum absolute residual 9.9997787828e-13. This does not establish wet/dry conditions, absence of other gases, ideal mixing or sensor accuracy.

HP/HY/HPR/MP/MPR are publisher-derived/reconstructed fields even though stored as numbers rather than Excel formulas. HRT/OLR operating/derived provenance remains unresolved. HPR/MPR retain the literal printed L/(L/d) units; no denominator repair or physical volume is inferred. Per-reactor proportionality diagnostics and the numerical HY/OLR/HPR relation remain local source-consistency evidence, not an independent reactor volume or yield calibration.

## Biological model applicability

Metadata identifies pig manure and glucose qualitatively, without a resolved feed composition/species/COD mapping, added/consumed substrate yield denominator, biomass inventory, growth/decay observations or uncertainty. COD is not glucose or biomass mass; abbreviated acid labels do not supply species/speciation. BP/HP/MP are reported gas volume per day, not liquid flow or hydrogen mass flow. Gas reference P/T and wet/dry/collection conventions are unresolved. Temperature alone does not supply energy input, heat loss or reaction heat.

A next native biological level needs finite liquid/substrate/biomass and gas states, explicit feed/withdrawal and pH-control histories, working/headspace volume, phase transfer, source species/stoichiometric/COD/element/charge bases, gas observation/reference operators and qualified initial conditions. Reuse the existing reaction-core balance contracts after species/empirical biomass composition is supplied; its prescribed stoichiometric conversion does not provide microbial kinetics. Fit no Monod growth or inhibition parameters from these gas/yield columns alone. No biological model family or independent validation is claimed.

## Source and executed identities

- Workbook SHA-256: `f13352e6ae633878aa7cf47a9b7d79f859ad815cda24000c11f04abf32b60729` (165296 bytes).
- Metadata SHA-256: `887b80088dfb7b635690fa3150171c953621b9863b11a0f9e44ab45075af6811`.
- Receipt SHA-256: `7f94e8dd65a7f3917b51da4347ba29b89d74bc19d535cdb4d6ff832b4a3337b0`.
- Canonical normalized rows/masks/identities SHA-256: `791dc13421dba675335742dca7b1f6d2cbadc50c5d0f0c8cca95c46f9081293f`.

Executed source begin/end fingerprints matched; sources used LF.

- `src/h2physics/data/fermentation.py`: `e3b5704418d1304bc9862bc4209628d3662c7546a6a4579337b972716ba77b36`
- `tests/test_fermentation_data.py`: `cef672af5029a0b51e26573245b7066a75bdd516f855dee412c2927a91d65678`
- `scripts/check_fermentation_data.py`: `ea71b24f78d3cc9a7d84189adc4d765cc1f6f0e3bec92e87fb3cb7106a5c063f`
- `src/h2physics/data/pressure_peaking.py`: `44235ac1ffa7e447ebc58a42eba5368e8008af517f48bd3605fa41140507fa15`
- `src/h2physics/observations.py`: `e0a6f1e26b5b6ca20fb31b8f7f19d5f86c6dbaffadfd37e2adc22de8bf6d1ba0`
- `src/h2physics/units.py`: `af252872dc63e784879d31408008151531e1992f7fe6acacde1c7bd5cc70bc0c`

Detailed source units/bases/origins, formula/cache metadata, reactor clocks, source row identities, missingness, consistency residuals and normalization diagnostics remain in ignored `data/processed/dark-fermentation/2/audit.json`. External raw and normalized records remain outside Git and distributions. The receipt retains `validation_qualified = false`.
