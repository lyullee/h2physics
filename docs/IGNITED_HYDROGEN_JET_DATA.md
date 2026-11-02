# DataverseNO X044QK ignited hydrogen-jet matrix

## Source, license, and acquired scope

The primary dataset is Agnieszka Weronika Lach, *Replication data for: Laboratory-Scale Experiments on Ignited Hydrogen Jets: Flame Acceleration and Overpressure Analysis*, DataverseNO, version 1, DOI [10.18710/X044QK](https://doi.org/10.18710/X044QK). The repository declares the dataset CC0 1.0 and the selected matrix attachment is public. Dataset citation remains appropriate research practice. The associated conference paper is linked from the dataset record as DOI 10.5281/zenodo.16621853.

The acquired matrix attachment is `Matrix and H2 flow results.xlsx`, Dataverse file PID `doi:10.18710/X044QK/JH7P7P`, size 14,199 bytes, publisher MD5 `6c929ee530ac393ee8e76f6db2eff05c`, project SHA-256 `c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557`. The local source stays under ignored `data/raw/ignited-hydrogen-jets-x044qk/1/`; it is not bundled into the package. The case requires a separately staged Hangang copy at `/scratch/CLUSTER_USER/h2physics-source-attachments/ignited-hydrogen-jet-x044qk/1/Matrix and H2 flow results.xlsx`.

The matrix has 40 numbered experiment rows. Its source note states that mass-flow results were calculated from experimental pressure. The reader retains the reported pressure and mass-flow values without re-deriving them. Pressure absolute/gauge basis and the pressure-to-flow calculation basis are not established by this workbook.

The Dataverse version lists 47 public files: the matrix, a README, 39 experiment CSV time histories, and six high-speed video bundles. The CSV sequence has `EXP_001` through `EXP_021` and `EXP_023` through `EXP_040`; matrix row 22 has no matching time-history CSV. The 39 CSV files and six video archives are not acquired by this project. They are large (the pressure-history CSVs are roughly 0.4–1.1 GB each, and the video bundles total tens of GB). The current reader therefore covers experiment conditions and publisher-reported summary fields only, not the raw transient pressure histories or images.

## Reader and deferred contract

```python
from h2physics.data import load_ignited_hydrogen_jet_matrix

matrix = load_ignited_hydrogen_jet_matrix(
    "data/raw/ignited-hydrogen-jets-x044qk/1/Matrix and H2 flow results.xlsx"
)
exp_1 = matrix.experiment(1)
print(exp_1.reported_max_pressure_bar,
      exp_1.pressure_derived_max_mass_flow_kg_s)
```

The reader checks exact attachment size, publisher MD5, project SHA-256, worksheet, title, headers, source row ordering, formula/cache agreement, and all 40 experiment IDs. It retains original worksheet cell values and row identities. Its small Hangang contract `dataverse-x044qk-open-atmosphere-ignited-hydrogen-jet-matrix` checks those identities and emits descriptive matrix extrema. This is source ingestion and summary accounting only; it is not an independent model comparison or experimental qualification.

## Channel and physics boundaries

The primary README describes laboratory under-expanded hydrogen releases into open atmosphere, delayed ignition, obstacle variation, high-speed imaging, and four pressure sensors. The first raw CSV's header describes a millisecond time channel, a trigger-voltage channel, four pressure-position voltage channels, and a nozzle-pressure voltage channel. No raw CSV is currently acquired or decoded by the project.

The README states a piezoelectric sensor calibration of 1 V = -1 bar, but channel offsets, sensor-to-position mapping, and exact treatment of atmospheric baseline need experiment-level review. Its upstream pressure conversion equation is malformed in the README text. Consequently the present reader performs no voltage-to-pressure conversion, absolute-pressure assignment, flow calculation, jet reconstruction, ignition-time inference, or dispersion reconstruction. The raw time histories must be separately staged, hash-verified, and schema-reviewed before any transient pressure metric or model comparison is added.

This is an ignited-jet and overpressure evidence source, not a direct unignited concentration-dispersion dataset. The matrix alone cannot validate HYRAM release rate, free-field concentration contours, ignition probability, flame acceleration, or blast loading.

## Bounded finite-source bridge

`h2physics.adapters.project_ignited_jet_average_source(matrix, experiment_number, ...)` sends one experiment's published average pressure-derived H2 mass flow and stated release duration into the existing `IntervalMassSource` API as a single finite bin. The caller must provide a pure-H2 representative thermodynamic state, a source location, clock/start placement, evidence accepting the reported pressure-derived flow for this boundary, and evidence mapping the published duration to that clock. The source average MFR is carried unchanged; the adapter does not convert the reported pressures or rerun a nozzle model. Its one-bin constant mean rate is only an aggregate boundary approximation; it is not the unavailable pressure/flow time history and does not encode peak flow, ignition delay, or flame dynamics. `require_current()` keeps the selected source row, matrix SHA-256, caller evidence and `IntervalMassSource` together. Hangang contract `x044qk-average-flow-finite-hydrogen-source-bridge` uses the staged CC0 matrix and synthetic location/state; it tests source projection only and is not dispersion or ignition validation.
