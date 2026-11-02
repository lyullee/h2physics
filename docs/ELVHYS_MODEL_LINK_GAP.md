# ELVHYS LH2 rupture source/model evidence gap

## Source and licensed scope

The source is ELVHYS 4.3.1, “BLEVE tests with a shock tube filled with LH2 in an A2 vessel,” DataverseNO DOI [10.18710/M5LOLM](https://doi.org/10.18710/M5LOLM), version 1.0. Its record declares CC0-1.0. The repository receipt lists 133 attachments and 534,609,893 B acquired; 91 video files are omitted. File-level SHA-256 and publisher-checksum entries remain in `research/data/elvhys-shock-tube.toml`. The acquired CSV/text scope supports source-row ingestion, not independent validation.

## Why current model comparison is blocked

The source reader preserves separate recorder clocks and signed pressure channels. The record does not identify a common rupture-time origin or synchronization offsets. `PRESF` labels contain `bar_a`, yet the exported containment waveforms include negative readings; calibration, dynamic zero, response and coordinate mapping are unresolved. They therefore remain reported waveforms and are not thermodynamic absolute-pressure inputs.

The initial containment oxygen and temperature summaries do not specify tube-side gas/liquid state. Full hydrogen inventory, phase split, pressure basis, oxidizer composition, humidity and residual gas are not established for model boundary conditions. The missing D4.8 drawing prevents placement of containment pressure stations. These gaps preclude a quantitative link to LH2 release/dispersion, containment pressure response, thermal exposure or detonation APIs. The acquired experiment is not a free-field pool release, and its data do not establish premixed detonation or CJ conditions.

## Follow-up

The evidence request at `requests/elvhys_shock_tube_model_link_evidence.md` is prepared but not sent. Hangang case `elvhys-lh2-rupture-model-link-evidence-gap` checks record rights/scope and the gap manifest only. It does not read measurements or run a physics model. Revisit comparison after obtaining rupture clock mapping, pressure calibration/positions, tube-side initial state/composition, and any required sensor response data.
