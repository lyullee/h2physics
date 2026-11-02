# Brookite photocatalysis data qualification

Qualification date:2026-10-27. This record describes original ingestion/schema
verification. It does not claim measured validation of a photocatalytic model.

## Source and rights

Dataset DOI:[10.5281/zenodo.15277951](https://doi.org/10.5281/zenodo.15277951),
pinned version15277951, CC BY4.0. Attribution: Seyyedmohammadhossein Hejazi,
Mahdi Shahrezaei, Sergii Kalytchuk, Josef Kašlík, Vojtěch Kupka, Alessia Zollo,
Mario Chiesa, Stefano Livraghi, Radek Zboril, Marco Altomare, Štěpán Kment and
Alberto Naldoni. The receipt preserves author spellings and metadata provenance.

The source receipt is `research/data/tio2-photo-evolution.toml`:
SHA-256 `5419c4187320de5090cc17781e65c46547a439c28d8ac2a5388688853f53fe2a`.
Pinned repository metadata:
`716af3ccf26a319d41e55b27b7669377c0fa759fbeb5bd6283bab1b89c94baf7`.
`Dataset.zip` is1946372bytes, SHA-256
`b22f168f0244fa9138c6e392150171d9c808bec605f619268f8e8d18de997353`,
publisher MD5 `e2c5add2c67b322b750ad941f0536c13`. All41 members passed native
ZIP CRC and individual SHA computation; expanded size is3087488bytes. No member
was extracted or executed. Public code/tests/docs contain no source observations,
publication prose, figures or tables. Raw sources and detailed results remain
ignored and excluded from distributions.

## Actual all-source coverage

All37 TXT files were consumed twice with512-row and127-row partitions; canonical
original-line/raw-cell/numeric/mask/identity digests agree for every member.
There are48 header lines and42856 retained data rows. Of241264 original data
cells,196397 are finite numeric,35604 blank,9243 `--` and20 categorical.
No nonfinite numeric values were found. Signed numeric negatives:21517.
42002 rows contain at least one numeric field;854 entirely missing/padded rows
remain. All37 TXT decode as UTF-8. Header regions and widths are fixed by the
reviewed source layout and guarded by the receipt SHA.

The following is audit metadata, not source observations. Independent columns
remain separate even where their reported coordinates happen to agree.

| Member | Header lines | Columns | Retained data rows |
|---|---:|---:|---:|
| Figure2a |0|6|3846|
| Figure2a_ref. |0|2|103|
| Figure2b |0|6|3466|
| Figure2c |0|5|1821|
| Figure2d |0|5|1821|
| Figure4a |0|3|12|
| Figure4b |3|7|6|
| Figure5_dark |0|3|10000|
| Figure5_under_UV |0|3|10000|
| Figure6a |3|4|201|
| Figure7a |1|4|521|
| Figure7b |1|62|305|
| Figure7c |0|62|305|
| Figure7d |1|62|305|
| FigureS1 |2|12|107|
| FigureS10 |2|3|7|
| FigureS11a |0|2|2048|
| FigureS11b |3|4|1376|
| FigureS13a1 |2|6|398|
| FigureS13a2 |1|6|392|
| FigureS13a3 |1|6|397|
| FigureS13b |1|4|3|
| FigureS2a |3|7|1821|
| FigureS2b |3|7|1821|
| FigureS3a |2|9|101|
| FigureS3b |2|9|271|
| FigureS3c |2|9|271|
| FigureS3d |2|9|271|
| FigureS3e |1|2|4|
| FigureS5 |0|3|5|
| FigureS6a |2|9|271|
| FigureS6b |2|9|271|
| FigureS6c |2|9|271|
| FigureS6d |1|2|3|
| FigureS8 |1|7|21|
| FigureS9a |2|2|7|
| FigureS9b |2|2|7|

## Scientific boundaries and primary evidence

Figure2's headerless characterization axes need separate mappings. Tauc fields
are processed. Figure5 field-coordinate spectra are not time-resolved kinetics.
Figure6a/S11b preserve separate energy grids and their original eV/a.u. headers.
Figure7b/d have numeric coordinate headers and are byte-identical; Figure7c has
no header, so neither axes nor units are borrowed. FigureS1 preserves relative
pressure and cm³/g STP headers; it does not establish hydrogen adsorption or a
specified STP temperature/pressure. S3/S6 XPS fits retain experimental, fitted,
component, background and residual fields; residual magnification is not sigma.
S13 PL experimental labels have no qualified main-catalyst crosswalk; duplicate
component names and values outside a header-described normalization range survive.
S3e/S6d durations describe preparation. S9/S10 `Time(h)` headers do not establish
the ordinate's rate/cumulative unit or a shared reaction clock.

The linked [primary article DOI](https://doi.org/10.1021/acsaem.4c01950) and
[author-institution PDF](https://ris.utwente.nl/ws/portalfiles/portal/472661098/hejazi-et-al-2024-suppressing-charge-recombination-by-engineering-homojunctions-in-brookite-tio2-nanorods-for-enhanced.pdf)
were inspected through primary indexed text. Direct full-PDF fetch returned403;
full SI was not retrieved. The specific locators and limited interpretation are
documented in `docs/PHOTOCATALYSIS_DATA.md`. The replay exercises a separate
member-SHA/column/primary-locator evidence object
and returns12 reconstructed SI specific-rate observations. This does not qualify
the mass preparation, gas collection, complete light source or full apparatus.
Figure4a's third field stays auxiliary; no error model or replicate count follows.

Figure4b supplies its own wavelength nm and first AQY % headers. The native-header
view has6 rows/12 valid fields. The second candidate AQY column's unit is not
explicit and is rejected without separate reviewed evidence. No extra
factor2, optical correction or yield binding is applied by the data API. Full SI
photon power and optical/T/P/GC calibration boundaries remain unresolved.

All files remain one study group. Figure7b/d have distinct source-row identities
and a common exact-member equivalence hash. Figure4a/S5 share two exact raw rows;
this proves numerical reuse, not the independent provenance of repeated physical
experiments. No random row/member split, fitted-spectrum comparison or catalyst
label is promoted to independent model validation.

## Reproduction and continuation

Commands use only local acquired sources:

```powershell
.venv\Scripts\python -m ruff check src/h2physics/data/photocatalysis.py tests/test_photocatalysis_data.py scripts/check_photocatalysis_data.py
.venv\Scripts\python -X utf8 -m pytest tests/test_photocatalysis_data.py tests/test_observations.py -q
.venv\Scripts\python -X utf8 scripts/check_photocatalysis_data.py
```

Original fixture cases cover masks, categorical labels, signs, whole-missing rows,
source windows, bounded blocks, separate x-grids, duplicate headers/members,
one-study partition rejection, explicit mapping gates, source mutation and unsafe
archive/budget/hash/schema rejection. The positive SI scaling case uses authored
values and an authored evidence object. Source-derived rate and AQY retain
`Origin.RECONSTRUCTED` and the original source block; they are not independent
raw gas/light/catalyst measurements.

Next comparisons should use a conditioned specific-rate operator or an explicit
incident-photon AQY operator after source/light/medium/catalyst review. Actual
illumination fingerprint, catalyst basis, medium, temperature, pressure, geometry,
gas collection and optical boundaries must be supplied to the coupled model.
Do not infer a solar spectrum from total power, assign characterization photons
to the reactor, estimate noise from the auxiliary field, fit a universal rate,
or close methanol-assisted chemistry as overall water splitting. The parent owns
the coupled production API, catalogue and receiving-project requests.

Final verification: Ruff passed;19 original profile tests plus3 common observation
tests passed in1.69s. The final complete two-partition source replay took2.8832113s.
Receipt, metadata and archive SHA checks matched before/after. The limited
specific-rate view has12 valid reconstructed fields; the first AQY view has12
valid reconstructed fields across6 rows. Both missing-evidence negative gates
passed. Every member's block-partition equality gate passed.

Ignored audit:
`data/processed/tio2-photo-evolution/15277951/audit.json`, SHA-256
`683305c602a350215dba91c7e0878ffa66c697b9e49adba0a2df3f294d184c35`.
The JSON is an optional reproduction artifact; the public integration API is
the Python objects described above.

Executed Python input hashes matched exactly at replay begin/end, all LF:

| Input | SHA-256 |
|---|---|
| `src/h2physics/data/photocatalysis.py` | `a4c1082a2ee76ddf28da565f958bada52eb5103171e9017728058702b4115e1a` |
| `tests/test_photocatalysis_data.py` | `1da71e5e5b178a3cece0350657f95d340dd443e21917d877b5821f8dc5b32c5e` |
| `scripts/check_photocatalysis_data.py` | `4218f948394514371103c69aaa86bea29d93afc091e596f4a7aa3ef7212bcc12` |
| reused `src/h2physics/data/pressure_peaking.py` | `44235ac1ffa7e447ebc58a42eba5368e8008af517f48bd3605fa41140507fa15` |
| reused `src/h2physics/observations.py` | `e0a6f1e26b5b6ca20fb31b8f7f19d5f86c6dbaffadfd37e2adc22de8bf6d1ba0` |
