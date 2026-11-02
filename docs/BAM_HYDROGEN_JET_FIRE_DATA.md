# BAM hydrogen jet-fire measurement data

The Federal Institute for Materials Research and Testing (BAM) published an open
dataset accompanying its hydrogen fire-test study. The Zenodo record identifies
the creator as Maximilian Naster, declares CC BY 4.0, and lists one 75,221,648-byte
archive. The archive contains three fire-reference-plate exports and ten
first-experiment measurement exports, plus infrared-camera assets. See the
[Zenodo record](https://doi.org/10.5281/zenodo.21026781) and its
[record API](https://zenodo.org/api/records/21026781).

The local raw archive and the exact API response are kept under ignored
data/raw/bam-hydrogen-jet-fire/21026781/; neither is part of the package or
public source tree. The API response captured on 2026-10-30 has SHA-256
646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0.
The downloaded archive is 75,221,648 bytes, matches the publisher MD5
019059edc40e776d6c54d917931e4e39, and has local SHA-256
c4e199a20960174845f27dbbb6521b65c797740ba3f503463ee96073cf2d8bed.
The full acquisition and rights receipt is in
[research/data/bam-hydrogen-jet-fire.toml](../research/data/bam-hydrogen-jet-fire.toml).

## Reader contract

h2physics.data.load_bam_jet_fire_text() admits only .txt files from
H2_Data/FRP_exp/ or H2_Data/First_exp_set/Measurement_data/. It checks the
resolved Zenodo identity, open-access/CC BY declaration, complete one-file
listing, archive length, publisher MD5, optional separately pinned local
SHA-256, ZIP member paths, and selected member digest. It accepts the source
Windows-1252 text encoding, separates the metadata block from the Data1 table,
and parses semicolon-separated values with decimal commas.

The returned BAMJetFireTable retains the metadata strings, exact channel
labels, raw cell tokens, parsed numeric values, blank-cell mask, source-record
identities, and archive/member hashes. It has no unit conversion, clock
reconstruction, sensor calibration, experiment-condition inference, or
model-specific projection. Calls to require_current() recheck the immutable
table seal and hash the full source archive; this is intentionally strict and
reads the 75 MB archive again.

Example:

~~~~python
from pathlib import Path
from h2physics.data import DATASETS, load_bam_jet_fire_text, resolve_dataset

record = resolve_dataset(next(
    item for item in DATASETS if item.key == "bam-hydrogen-jet-fire"
))
table = load_bam_jet_fire_text(
    Path("data/raw/bam-hydrogen-jet-fire/21026781/H2_Data.zip"),
    dataset=record,
    member_path="H2_Data/FRP_exp/BAM6_H2_1590_04.txt",
    expected_sha256=(
        "c4e199a20960174845f27dbbb6521b65c797740ba3f503463ee96073cf2d8bed"
    ),
)
time_values, time_valid = table.column("Time [s]")
~~~~

Channel labels retain the publisher's literal units, including kg/h and °C.
The export also includes voltage and pressure channels whose calibration and
reference basis are not assigned here. The time label alone does not qualify a
clock's synchronization, trigger, or absolute-time basis. The archive's
thermocouple traces are candidate measured inputs for later thermal-target
comparison; target geometry, thermocouple placement/calibration, surface
properties, flame boundary, and matched model inputs still need independent
source review. The reader is an ingestion API, not evidence that HyRAM,
SLABx-LH2, a jet-radiation projection, or a target-response model is validated.
The measured labels do not determine incident heat flux or cylindrical wall
conditions; see [BAM thermal-target mapping gap](BAM_THERMAL_TARGET_MAPPING_GAP.md)
before proposing any model comparison.

The offline synthetic contract bam-jet-fire-text-parser is registered under
source-data-ingestion. It checks delimiter/decimal handling, raw-token and
mask retention, and schema rejection. It has not been run and does not use the
measured archive or test any physical model.

## Explicit-unit channel view

`load_bam_jet_fire_unit_view(...)` composes the checksum-bound text reader with
`project_bam_jet_fire_units()`. It returns a sealed `BAMJetFireUnitProjection`
that retains the source table, DOI, creator, CC BY 4.0 declaration, metadata
hash, archive SHA-256, member path and member SHA-256. Each normalized series
also retains its exact publisher label and all raw tokens.

Only these label forms currently receive numeric unit views: `Time [s]` remains
seconds, `Massenstrom… [kg/h]` converts to kg/s, `[V]` remains volts, and
`[Bar]`/`[bar]` converts dimensionally to reported Pa. Pressure remains marked
absolute/gauge unresolved; mass-flow sign, sensor calibration and boundary
assignment remain unresolved; volts are sensor outputs with no calibration or
physical transducer mapping. Temperature-like `[°C]` channels remain raw because
the available channel labels use a `- T` marker and do not establish whether the
values are absolute temperatures or differences. `[-]` and all other unrecognized
labels remain raw token channels. No temperature-to-K conversion or measured
model input is admitted here. A source token can be finite while its converted
value exceeds the floating-point range; such a projection raises `ValueError`
rather than returning a nonfinite normalized value. The original token remains
available on the source table.

The deferred `bam-jet-fire-unit-boundary-projection` case uses synthetic labels
and decimal-comma rows only. It checks unit scaling and raw-only boundaries; it
does not access the ignored archive or validate a fire, radiation, or target
model. The existing BAM module is already imported by both Hangang and Nurion
campaign source plans, so the new case is included through that module.

The deferred observation bridge reconstructs its source `Dataset` from the pinned
Zenodo metadata response. It passes the source-origin classification as the exact
string `"measured"`, which is the BAM reader's admitted repository representation;
it does not pass a model `Origin` enum or infer origin from a thermal response.
DOI, open-access status, CC BY 4.0 license, complete archive listing, metadata SHA-256,
publisher MD5,
metadata bytes and the archive SHA-256 remain checked independently.

The new source-bound comparator `compare_bam_plate_temperature_to_target()` uses one exact plate `[°C]` channel and the rights-bearing BAM unit projection to compare against an already completed `ThermalTargetTrace`. It requires explicit caller evidence for absolute-Celsius semantics, target-sensor mapping, clock alignment and interpolation of model samples. This is an observation interface; BAM temperature does not drive or calibrate the model and is never inverted into incident flux. Hangang contract `bam-fire-plate-temperature-thermal-target-observation-bridge` uses one staged FRP archive member and a synthetic target trace only. It is not model qualification. See `BAM_THERMAL_TARGET_MAPPING_GAP.md`.

## Channel-count metadata

The export field Number of channels counts measured signals and excludes the leading Time [s] coordinate. The parser validates the declared count against the non-time header width while retaining time as a row-alignment coordinate.
