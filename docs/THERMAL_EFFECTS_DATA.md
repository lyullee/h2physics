# USN carpark thermal observations

`h2physics.data.thermal_effects.ThermalEffectsFile` exposes the acquired USN
thermal-effects MATLAB v7.3 exports through optional native h5py dataset slicing.
It reuses the existing SHA helper, SI unit conversion, origins and immutable
observation contracts. It does not decode another MAT representation, supply a
thermal/fire model or infer calibration and noise parameters.

```python
from h2physics.data.thermal_effects import ThermalEffectsFile

with ThermalEffectsFile(
    acquired_path,
    source_id="10.23642/usn.17695082.v1",
    experiment_id="Exp_00001",
    expected_sha256=receipt_sha256,
) as source:
    for recorder in source.recorders:
        for block in source.iter_blocks(recorder, block_rows=16384):
            table = block.observations
            # Select variables by their quantity/unit/basis, not only their label.
            # A source clock is deliberately not a physical seconds coordinate.
```

The acquired collection now contains all eight MAT experiments and two DOCX
descriptions. The acquisition receipt preserves the previous five MAT and two
description hashes and the original supporting metadata; the final version-1
metadata identifies the complete ten-attachment scope. Qualification uses the
receipt rather than silently assuming unacquired experiments exist.

Each native source vector keeps its dataset path, original HDF5 shape and 1-based
linear element index. Both `(N,1)` and `(1,N)` orientations are sliced on their
actual varying axis. `ThermalBlock.raw_values` contains the source clock (when
associated) followed by untouched channel values in schema order. The normalized
`values` and `valid` arrays add a reconstructed `source_index` column before the
reported clock. `source_indices` and all arrays are read-only copies bounded by
the block size. `observations` materializes long source row identities on demand;
the identity includes collection, experiment, source SHA, export/vector identity
and element index. `first_index` and `last_index` select a closed original-index
window without resampling or renumbering.

The exported HF, MFM, TS, Tank and Vent groups remain distinct. They do not
identify five independent hardware devices: the description refers to multiple
recording devices without a complete group-to-device/clock mapping. Numeric clock
equality, matching lengths, a common first value and equal source indices do not
establish synchronization. The HDF5 attributes and inspected descriptions do not
establish the physical time unit or the clock zero/trigger relationship. The
clock variable therefore has quantity `reported_time_coordinate` and unit
`source_time_unit_unresolved`. It cannot satisfy a `time`/`s` variable contract.
`as_time_series()` refuses automatic conversion, even for finite increasing
clocks. No sample frequency, event time, physical duration, integral mass, thermal
dose or automatic time shift follows from this profile.

RHF3 requires particular care. Its length matches the separately exported
`HF/timech7` in the actual collection, but the documentation does not explicitly
identify the physical channel-7 relationship. The default profile returns RHF3
as an unclocked signal and timech7 as a separate clock-only observation. Candidate
path metadata records the possible relationship without a paired measurement
claim. An explicit caller declaration is available when evidence exists:

```python
associated = source.associate_clock(
    "/HF/RHF3", "/HF/timech7", evidence_id="caller-reviewed-clock-mapping",
)
```

That declaration requires equal lengths, retains `Origin.RECONSTRUCTED` for the
clock relationship, records the caller's evidence identity in its basis and still
leaves physical time units unresolved. A nonempty identity is the caller's
declaration, not independent verification of its evidence. Arbitrarily constructed
descriptors cannot silently promote a candidate pairing to measured provenance.

Experiment 2 has a further source discrepancy: Vent/T contains 999,999 elements,
while Vent/time, ACH and vfr contain 4,999 each. Its entire temperature vector
survives unclocked. The profile neither truncates it nor borrows HF/MFM clocks.
Experiment 3 contains no TS group; no temperatures or trigger are fabricated.

| Source fields | Profile quantity/unit | Interpretation boundary |
|---|---|---|
| HF/RHF1–4 | radiative heat flux, W/m2 | Point radiometer output; response and incident/net/absorbed convention unresolved |
| HF/THF1–2 | reported total heat flux, W/m2 | Combined convection/radiation export associated with steel plates; processing/inversion provenance unresolved |
| HF/temp1–2 | temperature, K | Plate surface thermocouples; not gas temperature |
| MFM/mfr | signed mass flow, kg/s | Coriolis output; zero offset/direction interpretation unqualified |
| MFM/P, Tank/P | reported pressure, Pa | Meter/tank outlet readings; absolute/gauge reference unresolved |
| MFM/T | temperature, K | Instrument/gas composite reading; not thermodynamic gas temperature |
| Tank/T | temperature, K | Bolt-installed thermocouple; not exact bulk tank gas temperature |
| TS/TT1–9 | temperature, K | Point sensors near ceiling/car/wall; source coordinates and sensor response matter |
| TS/trig | reported trigger, unresolved unit | Trigger amplitude; no voltage or ignition-event assignment guessed |
| Vent/T | temperature, K | Ventilation-pipe thermocouple; bulk-flow response operator unresolved |
| Vent/ACH, vfr | air-change rate, 1/s; volume flow, m3/s | Reported ventilation outputs; no density or room volume inferred |

Known engineering scales are applied only as documented: kW/m2 to W/m2, g/s to
kg/s, bar to Pa, degrees Celsius to K, per-hour rates to per-second rates. Time
axes remain unresolved despite physical seconds appearing in the units of flow
and flux instruments. THF's origin is deliberately unresolved because the source
description does not establish independent flux-measurement/plate-inversion
provenance. Related THF and plate-temperature exports are not independent fitting
and validation targets by default.

Nonfinite data remain masked. Converted absolute temperatures at or below zero
are retained and masked as nonphysical. Signed heat-flux, flow and pressure values
are preserved; no baseline subtraction, clipping or automatic sign reversal is
performed. Zero fields remain valid source outputs, and a constant-zero vector
does not create a sensor-failure classification. Source masks are ingestion/domain
masks, not instrument accuracy, uncertainty distributions or noise sigma.

`thermal_location_rows(description_path)` returns the original location-table
cells as local runtime metadata after verifying the description SHA. The table
uses source order **y,x,z** and millimetres. Its drawing frame, axis interpretation
and incomplete ventilation location remain explicit; no coordinate permutation,
missing coordinate or model geometry is invented. The source table and images
remain outside public artifacts. The profile preserves source channel identity
and location evidence without deriving sensor heat-transfer coefficients or
making wall/plate/bolt readings into gas states.

The source context describes ignited hydrogen releases, but does not provide an
executable per-file assignment of all combustion, opening, inventory, ventilation,
ignition, radiation and sensor-response conditions. Those conditions must be
qualified independently before a forward-model comparison. Successful ingestion
does not validate a fire/radiation calculation, thermal dose, CFD model or facility.

HDF5 sources are read-only and checked by SHA before entry and after context exit.
Preflight rejects external/soft links, virtual/external storage, unreviewed
struct/double-vector schemas, unsupported filters and oversized sources. Defaults
bound source bytes to 150 MB, each vector to two million elements, total declared
numeric storage to 300 MB and requested blocks to 100,000 rows. Normalized arrays
and identities are block bounded; HDF5 metadata/chunk caches remain native-library
memory. Closing the context releases its file. The existing optional `data` extra
provides h5py; module import does not require it.

```powershell
.venv\Scripts\python -m pytest tests/test_thermal_effects_data.py -q
.venv\Scripts\python -X utf8 scripts/check_thermal_effects_data.py --workers 2
```

The offline audit verifies every acquired attachment SHA and publisher checksum,
pinned and supporting metadata, all actual native source vectors exactly once,
raw signed/nonfinite/zero fields, masks, clock anomalies and schema identities.
It retains canonical per-vector value hashes and source-index endpoints. At most
two workers run; atomic per-file checkpoints support explicit `--resume` only when
the executed source and receipt identities match. Long local runs can use hidden
detached stdout/stderr logs. A partial checkpoint or disappeared process is not a
completed audit. Source/test/script and shared helper hashes are checked at begin
and end. The complete local record stays in ignored
`data/processed/carpark-thermal/1/audit.json`; original aggregate evidence is in
[the research report](../research/thermal_effects_data.md). Raw and normalized
external observations remain excluded from Git and distributions.

Attribution: Agnieszka Lach and Andre Vagner Gaathaug,
[Experimental data—hydrogen safety, thermal effects, version 1](https://doi.org/10.23642/usn.17695082.v1),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The pinned
[version-1 metadata](https://api.figshare.com/v2/articles/17695082/versions/1) and
acquisition receipt establish scope and rights; they do not establish independent
model validation.


## Source-issued observation blocks

The thermal-effects reader issues each ThermalBlock only after validating the selected
native recorder and slicing its HDF5 vectors. A caller cannot create a block with
arbitrary numeric values and attach an admitted source digest, and dataclass
replacement cannot carry the consumed issuance token to modified content. The
deferred thermal-effects-block-loader-provenance case uses a synthetic HDF5 fixture
to check both rejection paths and the reader-issued source identity. It is planned
for the fracture-fatigue/data profile and has not been executed.
