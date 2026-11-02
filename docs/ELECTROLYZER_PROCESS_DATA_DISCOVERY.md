# Electrolyzer process-data discovery

## Scope and qualification bar

This review checked existing receipts under `research/data/`, data-family entries and current suitability notes for machine-readable experimental PEM and alkaline electrolysis measurements. Candidate sources must be primary repository records with explicit source rights. A candidate is not input-qualified until raw payload bytes and per-file checksums are pinned, the columns and units are inspected, and operating conditions and time support are clear. No figures have been digitized. The large archives below were not downloaded.

## Existing project coverage and non-duplication

- `peace-alkaline-short-stack` is already locally acquired and has raw 2/4/6 bar three-cell measurements under CC BY 4.0. Its recorded schema and limitations remain in `research/data/peace-alkaline-short-stack.toml` and `docs/PEACE_ALKALINE_DATA.md`.
- `grinhy2-electrolysis-transient` is an acquired plant-boundary hydrogen-flow trace; it contains no electrolyzer current, voltage, or temperature channels and is not stack electrochemical evidence.
- `pressurized-alkaline-bubble-electrode-potentials` is a rights-qualified RODARE source, but only its condition-index CSV is acquired; its 8.59 GB numeric HDF5 archive has not been downloaded or schema-reviewed.
- `pem-crossover` is an already acquired and distinct PEM catalyst/crossover degradation dataset. The new current-ripple record below varies electrical supply waveform and has a separate experiment matrix; it is not a duplicate.
- Other existing system candidates include `pem-grid-system` (Dryad experimental/system traces; payload inaccessible) and `pv-pem-dispatch` (simulation/model output, not independent measured process response).

## New primary-source candidates

### Current-ripple PEM cell degradation, Mendeley Data v2

[The official Mendeley record](https://data.mendeley.com/datasets/93jz2rgy4d/2) and its versioned public API declare CC BY 4.0 and list one ZIP, `PEM_ripple_degradation_data.zip`, 90,759,411 bytes, API SHA-256 `47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab`. The exact v2 record and file-list JSON responses are preserved in ignored `data/raw/electrolyzer-source-metadata/pem-ripple-degradation/`; local response hashes, attribution, and publisher file metadata are in `research/data/pem-ripple-degradation.toml`.

The repository description identifies four single-cell PEM electrolyzers under a 1,000-hour campaign, each at 2 A mean current and 50% ripple magnitude, with 300 Hz, DC, 600 Hz and 1,200 Hz conditions. It reports nine per-cell polarization characterizations and about 1 Hz continuous voltage logging (~3.37 million samples per cell); all payload members are said to be CSV, with a README for column units and cell mapping. This is a strong reusable candidate for temporal degradation and measured polarization work. The archive and README have not been inspected, so exact field names and units, calibration, test temperature/pressure, active area/current density, water conditions and current/voltage clock alignment are still unverified. It is metadata-only and not a validation input.

### Long-duration PEMWE under accelerated-stress protocol, Leibniz University Hannover

[The official LUIS dataset page](https://data.uni-hannover.de/dataset/pemwe-single-cell-dataset-under-ast-protocol) declares CC BY 4.0 and lists one CSV, `PEMWE_single_cell_AST_1402h.csv`, 709,873,892 bytes. The official CKAN `package_show` response is preserved in ignored `data/raw/electrolyzer-source-metadata/pemwe-ast-hannover/`; its SHA-256 and exact URL are in `research/data/pemwe-ast-hannover.toml`.

The title and tags identify electrochemical and operational observations from a 1,402-hour PEM single-cell AST campaign. The deposit page/API does not expose a data dictionary, channels, units, sample cadence, calibration, or clock semantics, and the publisher returned no checksum. The large CSV was not downloaded. It is a high-value, rights-qualified metadata candidate, pending author/repository schema documentation and a bounded acquisition decision.

### Alkaline cathode response to electrolyte purity, 4TU.ResearchData / WUR

[The WUR primary dataset record](https://research.wur.nl/en/datasets/experimental-data-overlooked-impact-of-electrolyte-purity-on-benc/) describes recorded current and voltage during nickel-electrode tests with high-purity and laboratory-grade KOH. Its version-3 DataCite record declares CC BY 4.0, text/CSV UTF-8 formats, 25 °C, and atmospheric pressure. The exact DataCite response is pinned under ignored `data/raw/electrolyzer-source-metadata/alkaline-electrolyte-purity/` and referenced in `research/data/alkaline-electrolyte-purity-candidate.toml`.

The repository resource inventory could not be retrieved during this audit, so exact filenames, count, bytes and checksums remain unknown. The record does not expose current/voltage units or a sampling/time basis. This is a suitable alkaline benchmarking lead, but not yet an ingestible or comparable polarization dataset.

## Other reviewed alkaline leads that remain unqualified

- [RWTH Aachen's Ni-mesh anode dataset](https://zenodo.org/records/11103701), v1, CC BY 4.0, lists `Dataset.zip` (1,266,562 bytes; MD5 `d22e5f3c91d7481987d0ff9a64405b9d`). The record describes a 1 cm² three-electrode Ni-mesh setup at 80 °C and 30 wt.% KOH, but does not identify payload channels, measurement units or temporal basis. It is a relevant electrode-characterization lead, not a qualified electrolyzer polarization record. The 1.3 MB file was not acquired.
- [St Andrews' alkaline water-density dataset](https://doi.org/10.17630/ed763e15-e88d-421d-b672-9a95e4f73b28) declares CC BY and lists two small ZIP attachments containing `.z` and `.corr` text-readable files. The repository says methodology will be linked when the paper is published; exact measured fields, units, experimental clock and file checksums were not established, so it is not presently qualified.
- The existing PEACE repository list contains a TU/e alkaline electrochemical candidate, but the accessible repository record/API has not yet yielded a verifiable file inventory or schema. The 2026 PEACE project data management plan describes an additional demonstrator-operation data package planned for the Open Energy Platform; the reviewed public dataset page does not list that package yet. Keep both as follow-up leads, not available trace data.

## Current gap and next evidence needed

Public rights-qualified electrolysis measurements do exist, and this review found useful new PEM temporal/polarization candidates. The remaining gap is consistent, inspected source data that pairs per-cell or system electrical channels with explicit units, operating state, calibration, clock, test geometry and condition metadata. For cell polarization comparisons, current density, active area, cell count/voltage scope, temperature and pressure basis are required. For process/operation comparisons, the boundary between stack, rectifier, water loop and plant auxiliaries must be explicit. The reviewed new sources have not been used for calibration, validation or model fitting.

## Source and acquisition receipts

Metadata-only API snapshots are local under ignored `data/raw/electrolyzer-source-metadata/`. Their byte counts and SHA-256 hashes are recorded in the corresponding TOML candidate receipts. No measured raw payload was downloaded for this review. See `docs/DATA_INVENTORY.md` for acquired-versus-listed counts and `docs/DATA_QUALIFICATION.md` for adjacent source-specific boundaries.
