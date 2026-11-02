# ELVHYS LH2 rupture data qualification

This qualification covers the locally acquired version1.0 of
[10.18710/M5LOLM](https://doi.org/10.18710/M5LOLM), authored by Eugenio Torres
de Ritter, Andreas Friedrich and Manuel Ignacio Ferraro Porcel de Peralta at KIT.
The pinned Dataverse metadata confirms version1.0, CC0-1.0 and unrestricted
access for every acquired attachment. The source README also refers generally
to project sharing terms; no separate restriction was attached to the acquired
files in the reviewed repository metadata. Raw files, normalized observations
and the detailed audit remain ignored and are not redistributed here.

## Scope and provenance

The receipt contains42 completed files totalling534,609,893bytes:39CSVs,
including the campaign metadata file, and3text files. The numerical population
is38recorder CSVs:12temperature,12slow pressure,12fast pressure and2sound-level
files. The metadata establishes12date-qualified runs. There are133listed
attachments;91video files are omitted. Those videos, original proprietary
recorder files, original instrument workbooks and the referenced D4.8 report
have not been examined by this qualification. The two acquired observation
notes identify missing webcam recordings; they do not supply replacement
event timing or visual evidence.

Each completed receipt SHA256 and publisher MD5 was checked against actual
bytes. Publisher file sizes and unrestricted-access flags were checked against
the pinned native Dataverse metadata. All42source hashes, metadata and receipt
were checked again after the complete scan. No source was modified.

- Receipt SHA256: `570e555c962e826bb5e0d464095ba6ff9124273c5e5e653228cd71076f231a31`.
- Native repository metadata SHA256: `8b16f9b388c7b92139630ce40b78ea37a830a720bcb26e98ee394e48af83e1a1`.
- Source README SHA256: `d81e0b29971e12ca0a0920052daf5ff02a7c392d4fc5dc4c2b8c6ecdf35bda9a`.
- Campaign metadata CSV SHA256: `124b58269e9f006bb09e4c0cd6b2299695eef9fe440c6962e360eb8baab5c27b`.

The README was inspected as UTF8 text. The campaign CSV contains non-UTF8
degree/micro bytes and is decoded through an explicit reversible Latin1 mapping.
The original bytes remain authoritative; no publisher encoding declaration is
invented. That CSV has67physical lines, including multiline quoted fields. The
README has266lines and each observation note has1line. The12condition entries
retain their physical source lines and metadata hash.

## Scientific population and boundaries

This is a cryogenic, heated LH2 membrane-rupture/BLEVE campaign. The source
describes a1m tube with51.2mm internal diameter inside evacuated/conditioned
containment. The8unignited/inert-labelled and4ignited/oxidizing-labelled runs
retain those original labels. Source campaign summaries span4.80–20.27bar
absolute reported rupture pressure,10.5–12.5%initial containment O2 in the
inert-labelled group and21.9%in the ignited group, and18–36C initial containment
temperature. Combined membranes and batch markers are retained directly from
the campaign metadata, rather than inferred from the three-digit filename code.

These are reported experimental summaries, not a complete pre-event gas state.
They do not determine tube H2/oxidizer composition, initial tube-H2 temperature,
phase fraction, fill mass, H2 spin composition, flame initiation energy/location,
premixed-gas uniformity, a propagation speed or a detonation regime. The cited
D4.8 apparatus/procedure evidence is absent from the acquired set. No CJ,
ignition-delay, DDT or transient rupture model is experimentally validated here.

Date is part of every run identity. Multiple dates reuse the same nominal code.
Recorder and station samples within a run are dependent observations, and all
runs share apparatus/campaign dependencies. Source batch markers do not establish
independent specimen or membrane-manufacturer identities without further evidence.

## Full numerical audit

The final bounded scan read all4,886,225data rows and all48,526,984numeric cells.
Every cell was finite and parseable. There were no empty, nonnumeric, formula-like
or nonfinite numerical fields. CSVs supply no executable formulas or cached
formula lineage; publisher conversion/calibration and synchronization history
cannot be reconstructed from their numerical contents.

| Recorder | Files | Data rows | Finite numeric cells | Valid cells | Invalid cells |
|---|---:|---:|---:|---:|---:|
| Temperature |12|492,786|3,942,288|3,449,502|492,786|
| Slow pressure |12|723,423|5,787,384|5,787,384|0|
| Sound level |2|524,288|1,048,576|1,048,576|0|
| Fast pressure |12|3,145,728|37,748,736|37,748,736|0|
| Total |38|4,886,225|48,526,984|48,034,198|492,786|

All492,786invalid cells are the original all-zero `T_2e` channel across the12
temperature files. They remain0in both raw and SI arrays and carry the reason
`outside_reported_diode_range_2_to_500_K`. This masks physically unavailable
temperature observations without asserting why the source channel is zero.
The other tube diode extrema are approximately21.04–364.94K and the jet diode
extrema approximately293.84–443.78K. These are instrument readings, not a uniform
gas state or an ignition-temperature observation.

Validity of the pressure and sound entries means retained finite numerical
output in the declared reported basis. It does not certify sensor range,
absolute calibration, phase applicability, pressure baseline or acoustic weighting.
The slow `p_20` channel has1,818negative values despite its `bar_a` label. All
six fast tube-pressure channels also contain negative values, and containment
wave channels have many signed negative values. No values were clipped or
shifted. The profile exposes these pressures as `reported_pressure`, preventing
automatic substitution for an absolute thermodynamic pressure variable.

Feed pressure conflicts between the actual gauge header and the README variable
list. Counterpressure conflicts between the gauge header and an instrument
absolute range. The differential-pressure export says bar while the instrument
description gives a0–7mbar range; the actual output reaches approximately182.10mbar.
The profile preserves the header conversion, reported range discrepancy and
unresolved calibration/sign/elevation context. It does not invent a scale repair.
Sound output spans65.1–201.5875dB; detector range, weighting, reference pressure
and averaging remain unresolved, so it is not converted to linear pressure.

## Clocks and stations

All12fast-pressure files and both sound files contain262,144rows each.
Their signed reported seconds span−0.13107to2.49036, with10microsecond increments
to export rounding. This is100kHz. The README simultaneously states10kHz and
10microseconds per sample; the measured export grid supports the latter. Both
statements remain source discrepancies rather than silently replacing one.

Slow pressure clocks have approximately0.05s increments and overall file-support
extrema−3176.100to1879.250s after minute-to-second conversion. Temperature file
support extrema are−2876.334to4401.069s, with variable increments up to0.242s.
All source clocks are finite. There are27nonincreasing steps, all equal-time
duplicates in temperature files:2or3per file. The rows remain distinct source
observations. At the4096row scan block size,27affected `TimeSeries` blocks are
rejected; `ObservationTable` access remains available. No sorting, row deletion,
clock offset, rupture-time inference or cross-recorder synchronization is applied.
The export's zero convention and the source synchronization method are unavailable.

The README provides11tube station coordinates, retained at runtime with their
source lines/hash. Axial positions for tube pressure stations cover0–0.9m from
the bottom flange. Tube temperature stations have opposite reported angular
orientation. The reported wall-sensor radial coordinate equals the stated51.2mm
inner diameter, leaving its geometric convention unresolved. No radius correction
is made. Exact containment pressure-wave station coordinates require the missing
D4.8drawing. The sound meter has a source-reported approximate2mrelease distance,
but no direction or resolved propagation path is supplied; the API does not
turn that description into a wave-speed measurement.

## Executable qualification and freeze

The public Python API returns original-row, file/hash-qualified immutable
`ObservationTable` and `TimeSeries` objects in bounded blocks. It retains source
engineering units/text, explicit SI conversion, masks/reasons, station context,
date-qualified run identity, separate recorder clocks and source-derived summary
roles. It supplies no copied source table, raw observation, pressure interpolation,
noise sigma, kinetic fit or thermal/combustion reconstruction in the public tree.

Original small fixtures test unit scaling, signed pressures, sensor masks,
formula-like and nonfinite fields, invalid/duplicate clocks, block boundaries,
physical source-line windows, date/recorder identity, schema/hash/budget failures,
rights/path guards, source conditions and station lineage. The scoped command
`python -m pytest -q tests/test_shock_tube_data.py` passed16tests in3.67s.
Ruff check and format passed for the three executable files.

`python scripts/check_shock_tube_data.py` ran as a detached local process with
durable progress. The complete final replay took123.8398987s. Besides the full
scan, each file's first8192rows was replayed with137row blocks instead of4096;
SI arrays, raw numeric arrays, masks and original row indices matched exactly.
The iterator verifies complete file SHA256 before/after selected windows. All
acquired publisher checksums, source-before/after and code-before/after gates
passed. The report is the ignored local `artifacts/shock_tube_audit.json`, SHA256
`3f9dd3d28ad2bd52c9669a32bf52b8ff12377d31537b510e49f12a706c6d4bad`.

Executed host fingerprints, identical before and after the full replay:

- src/h2physics/data/shock_tube.py: `bb9db6da1ee929c2cf6187d6fff776de96a5280045838bfebffda5a14a9cfcbb`.
- tests/test_shock_tube_data.py: `0d90b03ffefe8e5b506b0b0c0f15367b4caf3f6ff64221d44124769f46ff6a5b`.
- scripts/check_shock_tube_data.py: `cee17cc7804ef1e88b1171926b96f82c7d4af69938d59fc346e63de62fe22860`.
- src/h2physics/data/pressure_peaking.py: `44235ac1ffa7e447ebc58a42eba5368e8008af517f48bd3605fa41140507fa15`.
- src/h2physics/observations.py: `e0a6f1e26b5b6ca20fb31b8f7f19d5f86c6dbaffadfd37e2adc22de8bf6d1ba0`.
- src/h2physics/core.py: `4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68`.
- src/h2physics/units.py: `af252872dc63e784879d31408008151531e1992f7fe6acacde1c7bd5cc70bc0c`.

Next receiving work requires the original alignment/calibration procedure,
event-zero definition, complete tube inventory/phase boundary, containment gas
composition, initiation details for ignited cases, station drawings and pressure
reference resolution. A comparison should use the same declared station and
instrument quantity/clock and hold out whole date-qualified runs, with campaign
dependence stated. Equilibrium warm premixed CJ results cannot replace these
missing BLEVE boundaries or be fitted to a transient pressure maximum.
