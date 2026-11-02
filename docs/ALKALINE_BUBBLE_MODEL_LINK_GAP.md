# Alkaline electrolysis bubble-data linkage gap

## Source record

Mendeley Data version 2, DOI [10.17632/r6np4f7gmf.2](https://doi.org/10.17632/r6np4f7gmf.2),
is titled *Oxygen sticks, Hydrogen glides: Bubbles in alkaline water electrolysis*.
The public record was published 2026-03-06 and declares CC BY 4.0. Its description
states that the deposit contains raw data for article figures and videos from which
snippets were obtained. The official public files endpoint lists 35 completed
root-level assets: one README, 17 MP4 videos and 17 PNG images. Their combined
publisher-reported size is 375,513,822 bytes. The README alone (1,274 bytes) was
acquired and its local SHA-256 matches the publisher's value
`21946b964b3b260361f7bf797583f28a7fc6c1db3c02ddca1f77d9d956fc0c57`. Its authored
metadata reports 7M KOH, room-temperature experiments and 1000 FPS capture saved
as 15 FPS MP4. It also describes processed figure folders and scripts, but the
root listing exposes no tabular data file. A request to the site's
`public-api/.../folders` route returned HTTP 404; the documented public-dataset
folder API on `api.data.mendeley.com` returned HTTP 401 and its API reference
specifies OAuth authorization. Therefore the advertised processed folders are
not available through the anonymous listing used here; no authentication was
attempted. See the [official Mendeley Data API reference](https://data.mendeley.com/api/docs/).
No image or video has been acquired or processed. The publisher's prose README
and original JSON response stay in the ignored `data/raw/` cache. File-level
publisher IDs, sizes, types, license and SHA-256 values are retained in the
TOML conversion at
[`research/data/alkaline-bubble-observations-file-list.toml`](../research/data/alkaline-bubble-observations-file-list.toml);
local acquisition is recorded in
[`research/data/alkaline-bubble-observations.toml`](../research/data/alkaline-bubble-observations.toml).
The follow-up request for nested processed assets, condition mapping and
measurement methods is prepared but not sent in
[`requests/alkaline_bubble_file_schema_request.md`](../requests/alkaline_bubble_file_schema_request.md).

## Model-link assessment

The shared `HydrogenStack` supports declared electrochemical and Faradaic
operation. The host now adds an optional caller-calibrated reduced-order bubble
loss correction in `h2physics.adapters.alkaline_bubbles`. It accepts separate
anode/cathode surface coverage, electrolyte gas void fraction, bubble-free area
resistance, and Tafel slopes. A condition object passes mandatory absolute
pressure along with current density and temperature to each closure; optional
electrolyte concentration/composition identity and paired electrode IDs travel
with that operating point. It accounts for active-area masking and a
Bruggeman-form electrolyte-resistance increment. It predicts none of those
inputs, supplies no detachment/coalescence or spatial gas-holdup dynamics, and
does not qualify against the acquired image/video record. See
[`ALKALINE_BUBBLE_LOSSES.md`](ALKALINE_BUBBLE_LOSSES.md).

The source page alone does not tell us whether the raw records contain
digitizable bubble-size/velocity/coverage values, what the image scale or time
base is, or how each frame maps to gas identity, electrode, polarity, current
density, electrolyte and operating conditions. It also does not identify paired
cell voltage, resistance, or performance traces that could support a
source-bound comparison with the stack API. Therefore no source observation is
converted to a model input. The metadata-only ingestion case
`alkaline-bubble-electrolysis-model-link-gap` still records the data boundary;
the separate synthetic API contract
`alkaline-bubble-electrode-and-electrolyte-losses` checks software composition
only. Neither implies that images or videos were processed.

## Evidence needed to qualify the model link

Resolve any nested-folder listing and, if the processed data files are present,
acquire the version-pinned assets before determining whether they include
quantitative bubble observations. Retain their native units,
spatial scale, frame clock, electrode/gas identity, current density, electrolyte
composition, temperature and pressure. Any comparison to an electrolysis model
also needs an explicit, source-supported relation between those bubble quantities
and cell voltage, resistance, active area, or hydrogen rate. If the data only
contain images, a separately qualified image-measurement workflow is required;
the project will not infer measurements from plots or videos in this gap record.

No source dataset was analyzed for calibration. The reduced-order API has a
deferred synthetic Hangang contract; no local model test or calculation was run.
