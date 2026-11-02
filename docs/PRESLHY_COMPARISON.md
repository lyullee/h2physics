# Public discharge data and conditional model comparison

## Source and reproducible acquisition

[Jordan, T. (2023), KIT PRESLHY high-pressure discharge data](https://doi.org/10.35097/1187)
is published under CC BY 4.0. The new `radar-kit` discovery provider resolves DataCite identity
and rights, the public versioned landing-page distribution, paginated file identities and
anonymous public download links. Exact metadata bytes, publisher MD5 and local SHA-256 are
preserved. Internal backend URLs and authenticated archive-management APIs are not used.
Nested repository folders are currently rejected rather than silently omitted.

```powershell
.venv\Scripts\python scripts/acquire_data.py --keys preslhy-discharge --maximum-mb 1400 --maximum-file-mb 260 --include-suffixes .zip .pdf --minimum-download-interval-s 60
.venv\Scripts\python scripts/compare_discha_release.py
```

`research/data/preslhy-discharge.toml` is authoritative for actually completed/omitted/deferred
files. The repository may throttle requests. A 429 response records Retry-After, defers further
network requests for the dataset and still checks existing cached files. There is no immediate
automatic retry or assumption that the full collection was downloaded. Explicit request spacing
reduces request bursts. After a suitable wait, another explicit acquisition can reuse valid
cached bytes; recorded-hash replay still reacquires only previously completed files.

Raw attachments and metadata snapshots remain ignored under `data/raw`. Additional file
extensions require explicit selection; rights checks remain mandatory. The receipt is not
permission to redistribute every attachment inside a source distribution.

## Native loader and clocks

`data.preslhy.load_discha_workbook(Path_or_bytes, ...)` and `load_discha_member(archive,
member, ...)` produce `DischaRun`. The latter reads a bounded selected workbook without
extracting the outer archive. The run retains its exact original workbook hash, nominal
opening diameter, converted initial pressure and independent loaded series for temperatures,
ambient/slow pressure/force, balance and optional fast pressure.

```python
from pathlib import Path
from h2physics.data.preslhy import load_discha_member

run = load_discha_member(
    Path("data/raw/preslhy-discharge/archive-1/PRE3P1A_KIT_D1_300K_DATA.zip"),
    "20190523_144939.xlsx",
    source_id="10.35097/1187:warm-1mm:20190523_144939",
    clock_id="20190523_144939:publisher-PNoz-onset",
    pressure_basis="gauge", reference_pressure_pa=101325.,
    include_fast_pressure=True,
)
pressure = run.fast_pressure.series
temperatures = run.temperatures.series
```

The profile explicitly checks source labels and units; it does not infer them from numerical
ranges. Pressure basis and gauge reference are caller declarations. Relative humidity is
omitted unless the caller explicitly supplies `relative_humidity_unit="%"` or `"1"`; its
source label alone does not establish the scale. Concentration channels and open-junction
thermocouples are outside this profile. Source column A retains the author's synchronized
time; original recorder elapsed time from column B is also retained. Different sampling
frequencies remain separate. No new clock shift or concentration-tube delay is estimated.

The generic `load_excel_sheet` supports separate measurement and clock header rows and a
declared data-start row. Binary streams allow in-memory archive reading. It still reads
cached values only and neither executes formulas/macros nor sorts/deduplicates clocks.

`data.sampling.bin_means` takes explicit edges, a matching clock ID and minimum valid sample
count. It returns arithmetic means, masks, readonly counts and edges. It is sample weighting,
not a time-weighted mean, coverage guarantee or independent-replicate count. `linear_sample`
requires a matching clock and explicit maximum gap, retains exact valid source points and
masks invalid bracketing/extrapolation. Both mark outputs reconstructed and preserve units/bases.

## Comparison meaning

The implemented comparison uses four actual 1 mm warm experiments, with approximate initial
gauge pressures 200, 10, 20 and 5 bar. Source fast-pressure records and three closed vessel
thermocouples are binned on identical 2–10 s centers at 0.2, 0.1 and 0.05 s resolution.
The assumed ambient pressure is 101325 Pa, the declared rigid volume is 0.002815 m³ and
the selected fluid is frozen normal hydrogen. No barometric/spin measurement is claimed.

Measured pressure and the mean vessel temperature determine an EOS-reconstructed inventory.
The same inputs drive the shared isentropic nozzle and an independently integrated mass
flow. A per-run endpoint ratio and a shared bounded effective-area fit quantify consistency.
The complete approximately 20 bar experiment is held out; whole-experiment separation and
fingerprints use the existing native observation/fitting API.

The shared fitted factor is approximately 0.6111. Held-out RMSE is approximately 0.003612
of initial-window inventory, with maximum absolute error 0.007037. Fitting RMSE is larger,
about 0.02265. These numbers do not define an acceptance threshold or a universal flow
coefficient. The observed closed-thermocouple spread can exceed 20 K; their simple mean is
not a measured volume-weighted density. Valve/line losses and thermal observation bias can
therefore enter the effective factor. No confidence interval is inferred from correlated
integrated samples or a full-rank one-parameter Jacobian.

Temperature is observed forcing, not a prediction from an energy-conserving tank model.
Mass is EOS-reconstructed, not an independent calibrated flow measurement. Force and balance
channels are ingested but do not supply a quantitative validation target in this comparison.
Independent flow/inventory metrology, sensor response/uncertainty, spatial temperatures,
reference conditions and resolved valve/line hydraulics remain needed for qualification.

Actual tables, fingerprints, hashes and code identities are in
`research/discha_inventory_comparison.md`. The data exposed flat-maximum numerical failures;
the negative results and unchanged-gate corrections are in `research/nozzle_search_coordinates.md`.


## 2026-11-01 completed public-data replay

The full local four-experiment, three-bin-width PRESLHY replay completed with
exit 0. Source archive/workbook identities were checked by the existing script,
all twelve endpoint diagnostics returned, and the conditional fitting/held-out
report was regenerated at research/discha_inventory_comparison.md.
The fitted shared effective-area factor is 0.611074310718; fitting RMSE is
0.0226498819126 and held-out RMSE is 0.00361222122091 of initial-window inventory.
Held-out maximum absolute error is 0.00703731797345. The original train/test
fingerprints and experiment separation remain unchanged; the new values closely
reproduce the prior recorded comparison. Current code hashes are in the report.

This is conditional inventory/nozzle consistency: both reconstructed inventory
and nominal nozzle flow use the same measured P/T and native EOS. Temperature
is observed forcing and not a predicted tank-energy response. Therefore the
0.3612% normalized held-out RMSE is not independent flow accuracy, a universal
flow coefficient or complete blowdown qualification. Measurement uncertainties,
spatial thermal representativeness and independent flow metrology remain open.
The replay is finished; its previous source-file freeze can be released.
