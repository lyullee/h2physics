# Acquired data schema audit

Counts refer to files, tables or declared dimensions. They are not independent experiment counts.
Pressure basis, clock alignment, geometry and measurement origin require separate review.
For geological-adsorption-2026-09, four processed isotherm CSVs were streamed from the
acquired archive and schema-audited without extracting raw files or executing bundled
analysis. Each has 38 columns and six data rows. Raw logger/calibration schemas, uncertainty
reproduction and excess-to-absolute conversion remain unreviewed.

Hydride PCT workbook dimensions below come from review of the acquired, checksum-bound
ABS/DES workbooks. The source reader preserves the first three rows, formulas and raw
cells while streaming; no full numeric-column audit, unit conversion or fit is claimed.
The Mendeley record identifies this release as simulated.

The acquired PEM ripple ZIP contains 41 CSV members: 36 IV curves, four continuous
voltage logs and one fitted-parameter table. The source-bound reader checks the declared
CSV headers and streams each requested member while verifying its digest and row count;
it does not summarize the combined row total here. Field names and the units explicitly
declared in the deposited README are documented in `PEM_RIPPLE_DEGRADATION.md`.

| Dataset | Inspected files | Tables | Rows in delimited tables | Container errors |
|---|---:|---:|---:|---:|
| ab2-hydride-tank | 3 | 7 | 0 | 0 |
| austenite-embrittlement | 9 | 9 | 246 | 0 |
| oedi-hydrogen-materials | 1 | 4 | 0 | 0 |
| oedi-hydrogen-materials | 1 | 4 worksheets | 0 delimited | 0 |
| carbon-chemisorption | 19 | 19 | 1179 | 0 |
| carpark-thermal | 10 | 47 | 0 | 0 |
| carpark-unignited | 22 | 126 | 0 | 0 |
| cds-photo-screen | 1 | 2 | 0 | 0 |
| cryo-mof-dormancy | 68 | 67 | 35247 | 0 |
| dark-fermentation | 1 | 1 | 0 | 0 |
| elvhys-shock-tube | 42 | 39 | 4886238 | 0 |
| geological-adsorption-v1-historical | 1 | 51 | 4971 | 0 |
| geological-adsorption-2026-09 | 1 | 4 | 24 | 0 |
| h2safe-indoor | 2 | 7 | 21113 | 0 |
| hydride-compressor | 1 | 193 | 0 | 0 |
| hydride-pct-simulation | 5 | 10 | 0 | 0 |
| hydrogen-channel | 23 | 22 | 417340 | 0 |
| hydrogen-sound-speed | 3 | 0 | 0 | 0 |
| lohc-enthalpies | 1 | 3 | 30587 | 0 |
| mechanical-ventilation | 7 | 48 | 0 | 0 |
| pem-crossover | 1 | 0 | 0 | 0 |
| pem-grid-system | 0 | 0 | 0 | 0 |
| preslhy-discharge | 10 | 160 | 0 | 0 |
| pressure-ignited | 14 | 84 | 0 | 0 |
| pressure-unignited | 19 | 57 | 0 | 0 |
| pv-pem-dispatch | 1 | 9 | 1214 | 0 |
| sofc-polarization | 4 | 0 | 0 | 0 |
| tio2-photo-evolution | 1 | 0 | 0 | 0 |

## Source-specific austenitic compilation audit

The pre-existing generic246CSVrows are113main+31composition+102mapping. The new
scientific profile resolves1697valid main numeric cells and203linked-composition
numeric cells with distinct quantities/bases, preserving902blank main cells.
All6workbook sheets and14OOXMLmembers were inspected;257formulas have no cached
value and are not newly measured data. The CSV45columns match their worksheet
source; two extra worksheet columns are derived figure helpers. Version labels,
data-dictionary count disagreement,23publisher assets versus9acquired and
40composition conflicts remain explicit. Read EMBRITTLEMENT_DATA.md and the
source-specific research report; this supplements the old genericnumeric0 audit.

## Full BLEVE signal qualification

The source-specific shock-tube audit reads all42acquired attachments/534,609,893
bytes with publisher/source checksums. Among38signal CSVs it retains4,886,225rows,
48,526,984finite numeric cells and48,034,198valid cells;492,786T2e zeros remain
raw but masked. Fast PRESF/MICR exports each have262144rows at10us. Twenty-seven
duplicate/nonincreasing TEMP clock steps are preserved and rejected where a
strict TimeSeries would be required. Pressure validity denotes finite reported
output, not qualified absolute/gauge meaning; signed values are not clipped.
META's Latin1 degree/micro symbols are reversibly decoded; numeric CSVs remain
UTF8. These results supplement the earlier generic file/schema inventory.

## Complete ELVHYS4.2v1.1 source profile

The bounded source-specific profile reuses the existing recorder/hash/units/
observation kernels and retains every original source line/cell. Full198asset
hash/metadata audit and195CSV scans cover40actualcases,8150693rows and
89332905sourcecells. All195first8192row windows agree under137versus4096row
blocks. The public report identifies source/receipt/code hashes and the ignored
detailed audit. Signed/blank/nonfinite/source-invalid values remain separate.

Unknown physical Time unit and epoch prevent automatic time integration or
TimeSeries conversion. Actual separate blast-clock labels, unresolved pressure
placeholders and candidate-only sensor matches survive. An empty flow recorder
is an absent channel, not a fabricated zero. H2 is source-processed, O2 is absent
and source mass flow is unqualified. Dataset quantity/shape audit is not evidence
of a successful physical model comparison.

## KIT NH3/H2 counterflow flame package

The official KITopen/RADAR4KIT package is released under CC BY 4.0. The acquired
785,920-byte BagIt archive has SHA-256
`8b905fe6653c2c526301f050883ec271eee5d85df73797faf85f0c45c4b729db`. All eight
payload MD5 entries match the archive manifest. Five Excel workbooks contain nine
worksheets; the file SHA-256 receipts and shapes are recorded in
`research/data/nh3_h2_counterflow_flame.toml`. Originals remain in the git-ignored
`data/raw/` tree.

The extinction-rate worksheet is a flat 14-row by three-column table with eight
measurements, one header and five blank rows. Temperature uses two condition rows and nine adjacent position/
temperature pairs with variable profile lengths. In-flame H2/NH3/NO profiles use
five condition rows and four grouped three-species profiles. Optical intensity uses
four multirow worksheets and contains fifteen source profiles per diagnostic sheet.
The band-integral and spectra sheets each contain three signal blocks. Source-bound
Python readers expose these normalized optical signals separately from the eight
extinction rows, nine paired temperature profiles and twelve grouped H2/NH3/NO
profiles. They retain workbook hashes, worksheet row/column identity, condition
labels, units and missing values; reported spatial coordinates are normalized to
metres. No optical signal is treated as an absolute concentration or temperature.
Missing inlet-flow, apparatus, uncertainty and strain-definition mapping prevent a
defensible Cantera comparison; no experimental validation is claimed.

## OEDI 4130X fatigue workbook

The four-sheet, read-only workbook contains five paired ΔK/da/dN series with ASTM E647,
CL orientation, R=0.1 and 1 Hz fields. Four H2 series are labeled 45 MPa at RT and one air
reference is labeled 0.1 MPa at RT. The source sheet does not assign an unambiguous heat
name to each fatigue series; its formula cells point to bibliography references, not to a
heat ID. A 4.5 MPa value in the related HyMatBase record is a metadata discrepancy for
the exact same bytes: its listed MD5 equals the acquired file. The workbook's own condition
cells and Sandia's publication record both support 45 MPa. Temperature remains an RT label;
the deferred native-law diagnostic reconstructs 298.15 K from the associated 25 C metadata
and marks that input reconstructed. Crack-growth points can be compared to a selected rate
law without fitting, but heat identity, frequency dependence, specimen geometry and
component/vessel transfer remain unqualified. See the source receipt and hashes in
`research/data/oedi-hydrogen-materials.toml`.
The typed measured series and dataset are issued by the checksum-validating reader;
manually assembling source-labelled values cannot claim that file provenance.
