# PV-driven PEM dispatch archive: model-link boundary

## Source and rights

The source is Gao Xiang, *Dataset for Coordinated Optimization of a PV-Driven PEM Electrolyzer Array*, Zenodo [10.5281/zenodo.22900353](https://doi.org/10.5281/zenodo.22900353), CC BY 4.0. The publisher record and file receipt are pinned in `research/data/pv-pem-dispatch.toml`. The selected attachment `Manuscript_Figure3-10_Data.zip` is 47,443 bytes, SHA-256 `2fb59438156bd9ccfd8caad6e9540dd68648ffa08816a5c2eedde0043be96b39`. Preserve author attribution and license notices; the raw archive is kept outside release artifacts.

## Schema-level classification

The archive contains manuscript figure outputs, including reconstructed photovoltaic power, operating-state duration summaries, strategy-specific electrolyzer power curves, and cumulative hydrogen curves. The source record has mixed origin, and these outputs are not independent measurements of an operating PV/PEM plant. The listed records and their source labels do not furnish measured effective irradiance, PV cell temperature, matched stack temperature/current/voltage, or sufficient row-level measured-versus-simulated lineage.

## Why the existing model cannot be driven or validated from these outputs

The existing `h2physics.adapters.pv_electrolysis.PVElectrolysis` couples an explicit pvlib array with `HydrogenStack`. Its `PVStage` boundary requires effective irradiance, PV cell temperature, stack temperature, and absolute interval/clock information. Reconstructed PV power is an output of a separate system reconstruction; it does not establish those input values or pvlib module/array parameters. Dispatch power and cumulative-H2 curves also cannot independently qualify the host stack polarization, Faraday production, or thermal calculations.

The metadata-only Hangang case `pv-pem-dispatch-figure-output-model-linkage-gap` checks the exact CC BY receipt and records this boundary. It is not a model evaluation. A future bridge needs source-row input/response lineage, measured weather and cell/stack conditions, PV array parameters, clock and aggregation definitions, hydrogen measurement basis, and uncertainty. Until then, do not use these figure outputs as measured experimental validation or infer PVStage inputs from them.
