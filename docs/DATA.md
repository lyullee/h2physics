# Data acquisition and qualification

The first priority is experimentally measured process and safety data with explicit
reuse conditions. Metadata discovery, file acquisition, parsing and suitability for
independent model validation are separate stages.

For each record retain dataset/version/DOI, authors, license evidence, files, publisher
checksums, local SHA-256, retrieval outcome, instrument/geometry descriptions, raw units,
time basis, measured/reconstructed origin and unresolved conditions.

## Initial search families

- Metal-hydride tank absorption/desorption: time, flow, pressure and temperatures.
- Open-channel hydrogen releases: source histories and spatial concentration sensors.
- Synchronized axial pressure and flow histories in hydrogen-carrying pipes for
  pressure-wave, linepack and decompression observations ([current gap and
  rights-reviewed candidates](PIPELINE_TRANSIENT_DATA_GAP.md)).
- Buried hydrogen-blend pipeline leaks and delayed-ignition concentration evolution
  ([dataset scope and source receipt](BURIED_PIPELINE_DATA.md)).
- Mechanical ventilation and pressure peaking: flow, enclosure state and concentration.
- Ignited releases: pressure, thermal exposure and experimental boundary conditions.
- Hydrogen jet-flame fire-reference-plate measurements ([BAM source, rights, acquisition and scope](BAM_HYDROGEN_JET_FIRE_DATA.md)).
- A rights-reviewed shortlist of acquired, machine-readable dispersion and
  jet-fire sources, plus the NIST helium dataset excluded pending file-level
  reuse terms ([open hydrogen safety data screen](OPEN_HYDROGEN_SAFETY_DATA.md)).
- Cryogenic discharge, pool spreading and evaporation: initial state, rate, geometry,
  surface properties and independent observations.
- Adsorption isotherms and material characterization with source-specific rights.
- Electrolyzer/fuel-cell polarization, dynamic response and process operating records,
  including the PEACE three-cell pressurized alkaline stack dataset
  ([rights, raw acquisition and schema limits](PEACE_ALKALINE_DATA.md)) and a
  separate TU/e alkaline flow-cell electrochemistry candidate whose repository
  files remain unavailable ([source-status note](PEACE_ALKALINE_CELL_TESTING_DATA.md)).
  Newly reviewed CC BY primary-source candidates include 1,000 h PEM current-ripple
  polarization/voltage data, a 1,402 h PEM accelerated-stress record, and alkaline
  electrode current/voltage tests comparing KOH purity; the PEM current-ripple
  archive is now acquired with its publisher checksum and CC BY 4.0 record, while
  the other candidates remain metadata-only or schema-limited ([source discovery](ELECTROLYZER_PROCESS_DATA_DISCOVERY.md),
  [PEM ripple schema and reader](PEM_RIPPLE_DEGRADATION.md)).
  An additional CC BY 4.0 alkaline bubble dataset has 17 high-speed videos and
  17 PNG assets; the README is acquired, while nested processed data and a
  quantitative table contract remain to be resolved
  ([asset inventory and model-link gap](ALKALINE_BUBBLE_MODEL_LINK_GAP.md)).
- Containment, material diffusion/permeation and fracture/fatigue experiments.

Hydrogen-engine flame and wall-temperature observations ([scope and receipt](DATA_INVENTORY.md)) are separate from full-cycle cylinder pressure and work validation.
The current `h2physics.data` Python API binds the TUdatalib item UUID, DOI and permissive
license, captures exact bundle/bitstream metadata bytes, and can acquire `.h5` files to
ignored raw storage with publisher checksum verification. `inspect_hdf5_metadata()`
lists container objects, shapes, dtypes, storage layout, attributes and links without
loading dataset arrays or assigning units or physical meanings. The published description assigns figure files 2, 3, 5, 6, 7, 8
and 9; figures 1 and 4 are unavailable. See the [engine-cycle input boundary](ENGINE_CYCLE.md)
before deciding whether a measurement can be compared with a model quantity.
Call `inventory.require_current()` before reusing a retained structural snapshot; it
checks the reader-issued metadata seal and that the local source path still resolves
to the same regular-file bytes. Cloning or editing the snapshot invalidates it.

## Qualification rules

1. Count independent experiments as well as rows. A time series is not thousands of trials.
2. Inspect actual file columns and metadata before assigning units or pressure basis.
3. Keep calibrating and held-out cases separate by experiment/apparatus as appropriate.
4. Fix observation operators: point/time average, sensor response and location matter.
5. Do not infer an unknown deposition fraction, opening or geometry from a desired fit.
6. A dataset can validate one component without qualifying the entire facility chain.
7. Preserve failed downloads, ambiguous units and negative comparison results.

The `radar-kit` provider and explicit `--include-suffixes`/`--minimum-download-interval-s`
options support the public PRESLHY discharge collection. A server 429 defers further network
requests in that dataset, retaining Retry-After and still auditing valid cached files.
There is no automatic immediate retry. See PRESLHY_COMPARISON.md for source layout,
clock-preserving observation operators and the conditional comparison's scientific limits.

The MHCv1.2 compressor profile reads separately clocked raw/selected/calibration
exports through native Python observation blocks. Run
`python scripts/check_hydride_compressor_data.py --workers 2` after acquisition;
review HYDRIDE_COMPRESSOR_DATA.md before coupling pressure/flow/temperature to a
model. Explicit Date/Time schema and workbook epoch decode source serial clocks,
while gauge atmosphere, normal reference P/T and synchronization remain unresolved.
Durable ignored checkpoints support exact-source `--resume` after an actual
process interruption; only a completed all-experiment report establishes the audit.

THERMAL_EFFECTS_DATA.md now covers all eight version1 USN thermal MAT exports and
two descriptions, including the three newly acquired files. Its native-HDF5
profile keeps signed signals, source indices, unclocked vectors and candidate
clock metadata. Unknown time units/trigger relationships prohibit automatic
duration, mass integral, thermal dose and TimeSeries conversion. The complete
source-vector audit is research/thermal_effects_data.md; it is ingestion evidence.

## Fully acquired cryogenic enclosure and O2 evidence discovery

The separate cryogenic MOF data record also has a source-bound H2 isotherm CSV
reader. It preserves distinct adsorption/desorption rows, hashes, missing cells
and unresolved pressure/uptake semantics; see [CRYO_MOF_DATA.md](CRYO_MOF_DATA.md).

The two new discovery seeds are elvhys-cold-room (DataverseNOJXJP0H) and
oxygen-hypoxia-chamber (Dryadt1g1jwtg9). ELVHYSv1.1 has all198 acquired assets
and195 fully scanned numerical CSVs. Dryadv6 has only reviewed metadata/rights
and zero acquired attachments dueHTTP401. Neither status is independent ODH or
cold-room model validation.

CryogenicRoomCollection verifies the actual receipt/native metadata and exposes
bounded original physical-line blocks with source rows/raw cells, numeric/SI
arrays, masks, per-channel quantity/basis/origin and resolved/candidate positions.
The existing bounded recorder/hash/units/observation kernels are reused. Default
TimeSeries conversion refuses unresolved clock units/epochs. An explicit caller
file/hash-bound time declaration creates a reconstructed clock, not a claim
about the source's own clock qualification. See OXYGEN_OBSERVATION_DATA.md.

## Repository acquisition integrity

Dataset constructors bind exact metadata bytes to their SHA-256 and validate
attachment sizes, checksum declarations, normalized filename uniqueness and
cache-safe record identity. Repository, rights and supporting-metadata URLs must
use credential-free HTTPS; metadata fetches reject redirects away from HTTPS before
following them and enforce byte/time limits. OpenEI attachment size discovery uses
HEAD only, rejects unsafe redirect targets before following them, and rejects absent or malformed lengths
without downloading the attachment. Provider-omitted author or DOI fields remain visible.
Unresolved rights do not permit downloads, and absent metadata is not synthesized.
Cached attachment paths and dataset identity directories that are symbolic links
or junctions are rejected by the read-only cache audit and receipt replay. This
prevents outside files or sibling dataset/version directories from claiming a
publisher-bound relative path; it does not change the separate file-level rights
or redistribution review.

`dataset_from_mendeley_bytes()` parses staged Mendeley snapshot and root-listing
responses for offline source readers. It requires expected SHA-256 values and
retains the exact response bytes, but returns an ordinary `Dataset` without the
repository issuer marker. Source-specific loaders must validate the source's
pinned identity and attachment hashes. This helper cannot authorize receipt
replay; that remains restricted to records returned by `resolve_dataset()`.

`dataset_from_figshare_bytes()` provides the same offline metadata path for an
exact staged Figshare v2 response. It validates a separately pinned SHA-256,
preserves the response bytes, and returns an ordinary `Dataset` without the
repository issuer marker. Source-specific readers remain responsible for
checking their pinned dataset identity and attachment checksums.
