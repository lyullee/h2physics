# Cryogenic LH₂ phase-change observations

## Source and attribution

Use the versioned [Mendeley Data record](https://doi.org/10.17632/z5zc7kk76g.2),
*Data from cryo-neutron phase change experiments with LH2 and LCH4*, by Kishan
Bellur (version 2), under CC BY 4.0. Give credit to Bellur and the DOI, link the
license, and identify the selected-member extraction when redistributing derived
materials. The source API receipt and selected members' hashes are recorded in
`research/data/cryo-neutron-phase-change.toml`.

The publisher archive is 4,511,372,825 bytes and declares SHA-256
`46301398eeed7c93d7c522581422f45ff5664a844abd412a2d40bcdd175cbbed`. The
complete archive was not downloaded. Three files for one hydrogen run were read
through public HTTP byte ranges, checked against the ZIP central-directory CRC32,
and stored under ignored `data/raw/cryo-neutron-phase-change/2/`. The source archive
SHA is publisher-declared but not locally verified; each extracted CSV has an
independent pinned size and SHA-256 in the reader and manifest.

## Selected experiment and physical boundary

The selected run is `Jan(H2)/jan_tc1/jan_tc1_run1`, test cell `tc1`, a conical
cell. The data article reports 17.9 psia, a 21 K saturation temperature,
condensation subcool values of 20.8/20.6 K, and evaporation superheat values of
22/23 K. The experiment uses instrumented cryogenic cells in the NIST BT-2
neutron imaging facility with controlled hydrogen condensation followed by
evaporation. It is cell-scale phase-change evidence, not a pressure-vessel
blowdown test.

## Reading from Python

```python
from pathlib import Path
from h2physics.data import load_cryo_neutron_phase_change_run

run = load_cryo_neutron_phase_change_run(Path(
    "data/raw/cryo-neutron-phase-change/2/Jan(H2)/jan_tc1/jan_tc1_run1"
))
daq_time_s = tuple(point.time_s for point in run.daq_points)
image_time_s = tuple(point.image_elapsed_time_s for point in run.image_points)
rate_label = run.rate_windows[0].rate_unit
run.require_current()
```

The source CSVs are UTF-8 comma-separated files. The DAQ table has 5,391
observations in `daq_time, daq_s1, daq_s2, daq_s3, daq_s4, daq_htr, daq_stick,
daq_p_kpa, daq_htr_pow`; the accompanying source documentation assigns seconds,
kelvin, kilopascals and heater percent with 100% representing 5 W. The image table
has 1,165 rows and adds the image identifier/name/timestamp, elapsed image time,
matched sensor/pressure/heater channels, `vol_it_mm3`, `vol_od_mm3`,
`thickness_um`, and `apex`. These are image-derived fields; volume is in mm³,
thickness in µm, and apex remains a pixel token.

The six phase-rate rows carry `rate_od_mug` and `od_error` labels. The publisher's
data article describes image-derived evaporation/condensation rates but does not
establish units for those exact columns. They remain numeric source values with
unresolved units; no mass-rate or energy conversion is provided. The source's
nominal one-second DAQ and ten-second imaging descriptions are not used to resample
either clock. `daq_time` and `img_time` remain distinct seconds axes; image date-time
strings retain their text and their timezone is unresolved. Rate windows retain
source image indices instead of being aligned to DAQ rows.

The pinned DAQ run contains four adjacent pairs with identical `daq_time` values
and no decreasing timestamps. The reader and ingestion contract preserve every
row in publisher order and report those duplicate pairs; they do not sort,
deduplicate, interpolate, or force a strict clock. Any downstream solver that
requires a strictly increasing grid must receive an explicit caller-owned
resampling or duplicate-time policy.

## Model-use limit

This reader is a provenance and observation bridge. The repository's finite
cryogenic vessel model does not currently resolve the NIST cell geometry, local
interface shape, instrument-to-cell thermal mapping, or an independently sourced
accommodation coefficient for this experiment. A direct model fit or validation
claim would therefore be unsupported. A later coupling must retain separate clocks
and require explicit cell geometry, material properties, heater/cell heat paths,
sensor locations, rate-unit evidence, and an evidence-backed mapping to the model's
state boundary. The Hangang case
`cryo-neutron-lh2-phase-change-source-ingestion` checks the selected CSV identities
and schema only.
