# Hydrogen engine HDF5 schema admission review

This review covers the eight acquired attachments pinned by
`research/data/hydrogen-engine-flame-wall.toml` for TUdatalib record
[10.48328/tudatalib-2291](https://doi.org/10.48328/tudatalib-2291). Dataset and
publisher information is available through the
[repository record](https://tudatalib.ulb.tu-darmstadt.de/items/dbec6035-12f9-4ba6-b776-7b4ec4b11979)
and article [10.1016/j.proci.2026.106478](https://doi.org/10.1016/j.proci.2026.106478).
Local inspection read HDF5 object paths, shapes, dtypes, and attributes only; it
did not load dataset values or create a measurement mapping.

The source-to-model gap, exact author request and deferred Hangang contract are
tracked separately in [`HYDROGEN_ENGINE_DATA_LINK_GAP.md`](HYDROGEN_ENGINE_DATA_LINK_GAP.md).

An observation-series reader requires an identified quantity, units, independent
coordinate and its reference, and measurement location. Several attachments carry
some of these labels, but none currently establishes all of them in the stored
schema. The existing `inspect_hdf5_metadata()` remains the correct exposed API;
do not turn these containers into engine pressure traces or wall boundary inputs.

| Attachment | Explicit schema cues | Missing information that blocks an observation mapping |
|---|---|---|
| `Fig2.h5` | Per-mixture groups; `axis` in `degCA`; mean and standard-deviation pressure arrays; pressure unit `bar` | Crank-angle zero/reference convention; pressure transducer location; population represented by the summary and standard deviation |
| `Fig3.h5` | Temperature array in `K`; lifetime mean and standard deviation in `s` | The lifetime phenomenon and measurement location; the independent temperature/condition mapping |
| `Fig5.h5` | Three crank-angle labels in `degCA`; X/Y coordinates in `mm`; a flame-map array | Flame-map quantity and units; spatial origin, orientation, and clock reference; meaning of the three map indices |
| `Fig6.h5` | Crank angle; angle after flame impingement; reference and temperature-difference values in `K` | Temperature-difference definition and sensor location; angle reference and pairing of the two clocks |
| `Fig7.h5` | Angle after flame impingement; mean and standard-deviation temperature differences in `K` | Sensor location, reference for the difference, and aggregation/population identity |
| `Fig8.h5` | Crank angle; mean impingement angle; heat flux and flame power in `W/m²`; quartz thermophysical properties | Heat-flux measurement location and clock reference; definition of flame power and its relation to the heat-flux samples |
| `Fig9.h5` | Local flame-power and maximum-heat-flux arrays in `W/m²` | Coordinate/clock arrays, spatial location, and sample correspondence |
| `README.txt` | States that the files contain figure data and that headers/datasets carry interpretation properties | Does not specify the field-level coordinate conventions or measurement locations absent from the individual objects |

These are schema-level observations, not claims about the published experiment.
The article and record identify flame propagation and piston-surface-temperature
measurements as the collection topic, but this broad experiment context does not
resolve each field's sensor position, axis reference, or estimator. Request the
missing per-field definitions from the repository authors or an authoritative
supplement before implementing typed measurement ingestion.

No HDF5 values are copied into this repository. Raw attachments remain excluded
from Git and package artifacts pending the existing component-level rights review.
No crank-angle pressure/work model comparison or thermal boundary fit is admitted
by this schema review.

## Additional engine-data candidate — Durham free-piston study

The [Durham data record](https://collections.durham.ac.uk/files/r144558d30v)
describes hydrogen operation in two-stroke and four-stroke modes and lists CC BY
4.0. A separate [Durham publication record](https://durham-repository.worktribe.com/output/1274321)
describes the related dataset under the Open Data Commons Database License.
These records do not yet establish a single consistent grant covering the
candidate files. A direct download attempt timed out during discovery, and no
candidate bytes were acquired or inspected. Therefore no loader, observation
mapping, or validation case is admitted. Revisit only after the repository
confirms the applicable rights and makes the source files retrievable; then
record per-file hashes, schema, units, coordinate references, and measurement
locations before connecting data to the engine model.
