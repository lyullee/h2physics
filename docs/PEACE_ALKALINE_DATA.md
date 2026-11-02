# PEACE pressurized alkaline short-stack data

The Zenodo v1 record describes measured operational data for a three-cell
alkaline electrolyser at nominal pressures of 2, 4 and 6 bar. It states that
the electrolyte was 30% KOH and that the short stack did not reach its desired
80 °C operating temperature. The raw exports contain the original sensor
channels and are described as semicolon-delimited with comma decimal notation;
the separate column-description file maps source sensor identifiers to
readable labels. See the [source record](https://zenodo.org/records/19605474)
and [PEACE project dataset index](https://www.h2peace.eu/public-media/datasets).

## Rights and provenance

Zenodo's record API identifies the record license as `cc-by-4.0`. Reuse must
retain attribution to Hesham Mahfouz, Sai Ram Vissavajhala and Lars Röntzsch,
the dataset title, DOI `10.5281/zenodo.19605474`, and license link
<https://creativecommons.org/licenses/by/4.0/>. The source page lists seven
files and publisher MD5 values in
[`research/data/peace-alkaline-short-stack.toml`](../research/data/peace-alkaline-short-stack.toml).

The API and `/api/records/.../content` endpoints returned HTTP 403, but the
record's ordinary public `?download=1` links were accessible. The column map and
three raw experiment files (11,514,333 bytes total) were downloaded byte-for-byte
to ignored `data/raw/peace-alkaline/`. All four publisher MD5 checksums match;
local SHA-256 receipts are recorded in the manifest. No exact API JSON snapshot
was acquired or hashed. The three publisher-cleaned tables are intentionally
omitted because the raw source channels are the basis for schema review.

## Schema and interpretation boundary

The three acquired raw files share an identical first-line header of 131 fields;
its UTF-8 header hash is in the manifest. The publisher reports 6,695, 8,794 and
13,187 rows for the three experiments. `Zeit` is the first field, and the
companion description table maps selected instrument IDs to channel names and
some units. Numerous fields remain `Unnamed`; channel availability, clock
rollover, calibrations, pressure basis, cell wiring and physical interpretation
are not inferred. Never assign units from raw column labels alone.

`h2physics.data.peace_alkaline.load_raw_file` accepts an expected raw filename,
byte length, publisher MD5 and manifest-recorded SHA-256. It checks the path's
basename and all four receipt values against exact file bytes before strict
UTF-8 decoding or CSV parsing. It returns a typed `SourceTokenTable` carrying
the unchanged bytes, filename, verified digests, parsed preamble/header and
string-valued rows. `require_current()` rereads the original path and rejects
changed bytes. Callers should take expected values from the provenance TOML;
the reader does not fetch metadata or decide whether a receipt is trustworthy.
It does not parse comma decimals, interpret the description map, align clocks,
or create physical observations. The `peace-alkaline-source-bound-file-integrity`
deferred case exercises loading and stale-file rejection with synthetic bytes
only. It does not open ignored publisher files and is not model validation.
The acquired files have not yet been mapped to model observations or used for
fitting.

## Source-bound observation projection

`load_peace_alkaline_column_descriptions()` verifies the description CSV's
declared filename, byte length, publisher MD5 and local SHA-256 before UTF-8
decoding. The map has exactly three publisher columns:
`original_column`, `cleaned_column`, and `description`. The description is
retained verbatim; it is not split into a new unit field. The raw experiment
loader independently verifies the experiment file. Then
`project_peace_alkaline_observations()` binds selected channels by exact source
ID and returns an immutable `PEACEObservationBlock`, with each string-valued
series aligned to zero-based data-row indices after the header. The block keeps
both file identities and hashes and can call `require_current()` on both paths.
The three wrapper types are admissible only when issued by their corresponding
loaders/projector. Freshness checks reread and hash exact bytes, reconstruct CSV
rows and description entries, and reconstruct the selected projection; directly
constructed, replaced, or mutated wrappers are rejected when content no longer
matches the verified source owners. A text-only `SourceTokenTable` cannot be
projected.

The projection includes `Zeit`; ATA00 CE001/CE002/CE003; RAA10 CT001/CT002/CT003;
RAA30 CT001; RAA20 CT001/CP001/CF002/CQ001. The description map labels these
as time, total current, total power, total voltage, three lye temperatures,
oxygen-side gas temperature, hydrogen-side gas temperature, system pressure,
hydrogen flow rate and hydrogen quality. Values remain original comma-decimal
or blank tokens. Although the publisher's text says `Nm3/h`, the normal-volume
reference conditions are not provided in this mapping and are not supplied by
the projection. The aggregate `Total ...` labels do not establish cell versus
stack electrical semantics; no calibration, clock rollover, or H2-quality
measurement method is inferred. This object is a source-row projection, not an
`ObservationTable` and not validated model input.

The deferred `peace-alkaline-publisher-described-source-projection` and
`peace-alkaline-projection-forgery-rejection` cases use synthetic raw and
description files with temporary receipts only. They do not open ignored files
or establish physical model validity.

## Unit-safe numeric views

`normalize_peace_alkaline_channels(block)` is an optional numeric view that
retains its source `PEACEObservationBlock` and exact tokens. It converts only
channels whose source description fixes the input unit: amperes remain A,
kilowatts become W, volts remain V, degrees Celsius become K, and reported bar
becomes Pa using a dimensional scale only. Empty cells remain `None`. A numeric
view carries its original series, source/target units, conversion description
and semantic boundary; it does not overwrite raw tokens. Its `require_current()`
checks the issued source block and rebuilds the conversions from it.

The pressure quantity remains `reported_pressure`; the bar-to-Pa operation does
not determine absolute versus gauge basis. The aggregate electrical labels do
not resolve stack-versus-cell meaning. Temperatures are publisher-described
indications, not calibrated process states. Time remains a clock string; H2
flow remains `Nm3/h` tokens because the normal-volume reference state is
unspecified; H2 quality remains percent text because the quality measurement
basis/method is not defined by the map. No `ObservationTable` is created.
The deferred `peace-alkaline-unit-safe-source-normalization` case checks the
conversions and raw-only boundaries with synthetic files; it does not read the
ignored archive or validate a process model.

## Deferred use

The raw files are now acquired, but source-document review and explicit mapping
from their hashes and source-native column tokens to observations are still future
work. Any stack-performance comparison must establish cell/stack
voltage and current meanings, area, temperature/pressure conventions, gas
production or flow basis, water/electrolyte state, and run boundaries from
source evidence. The record alone does not qualify an electrolyser model or
support transfer to commercial-scale equipment.

## Existing stack-model input bridge

`h2physics.adapters.bind_peace_alkaline_electrolysis_profile()` accepts only a
loader-issued normalized projection. It maps same-row reported current (A),
reported total voltage (V), and one caller-selected publisher temperature (K)
to the existing `HydrogenStack.evaluate()` API. The caller must identify the
electrical scope, supply compatible stack geometry/series-cell count, and
document why the selected temperature represents the model state. The bridge
evaluates only rows with all three fields; it records missing rows and performs
no interpolation or extrapolation. Voltage residuals are diagnostics, not
calibration or validation claims.

The source describes current and voltage only as total quantities and does not
resolve cell-versus-stack semantics. Temperatures are sensor indications, not
calibrated stack temperatures. H2 flow remains raw because its normal-volume
reference is unspecified. No Faradaic efficiency, polarization loss,
thermochemistry or stack geometry is fitted. Deferred Hangang case
`peace-alkaline-existing-stack-model-bridge` exercises the API using synthetic
publisher-shaped files; it neither reads the ignored raw archive nor qualifies
the physical stack model.

The returned `PEACEElectrolysisTrace` retains the exact `HydrogenStack` owner,
the source and description SHA-256 values, caller mapping evidence and each
immutable `StackResult`. Its `require_current()` rechecks the source receipt,
geometry/thermochemistry/loss-owner identities, and recomputes the same rows to
confirm the snapshots still reproduce. `active_area_m2` converts measured
current to model current density and `series_cells` sets predicted stack
voltage; both must match the declared interpretation of the publisher's
aggregate electrical channels. This evidence is caller supplied, not
established by the dataset.
