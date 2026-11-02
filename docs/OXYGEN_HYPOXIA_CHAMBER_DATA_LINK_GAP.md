# Dryad hypoxia chamber: gas-model linkage gap

## Primary record and rights

Qayyum et al., *Data from: A modeling approach to inform in vitro Hypoxia platforms for patient-specific analyses*, Dryad version 6, [DOI 10.5061/dryad.t1g1jwtg9](https://doi.org/10.5061/dryad.t1g1jwtg9). The primary Dryad page lists a 229.85 KB workbook and a 5.22 KB README and describes the collection as experimental chamber data; the dataset manifest records CC0 1.0. The captured file-list response, metadata digest and current acquisition receipts are in `research/data/oxygen-hypoxia-chamber.toml`.

The rendered primary README describes ten workbook sheets with gas and liquid temperature, water evaporation, gas- and liquid-phase oxygen, inlet oxygen fraction, and inlet flow patterns. It says the gas-phase O2 observations and probe delay were used to calibrate/validate the source authors' oxygen-transfer model. This provides a potentially useful measured gas-phase observation family, but does not itself define the current host-model boundary.

## Exact access and model boundary

The captured metadata lists `Compiled_Data_PAPER_unformatted.xlsx` (publisher SHA-256 `f301464111d1feb33c1b28a192b8b9d868a352a6041d8f4b0da03eeccc152383`) and `README.md` (publisher SHA-256 `93517b02fa207c24ca7510802eff56da82f0e49aafa598229481d8d451ce6bc5`). The current acquisition attempt recorded HTTP 401 for both downloads; no bytes, local hashes, or workbook row schema are present. The primary page exposes the broad sheet descriptions and variable names, but not all condition rows and joined recorders.

The existing `CanteraOxygenRoom` can model a declared gas-volume inventory with explicit species-feed, exhaust and heat boundaries. A measured gas-O2 comparison may become admissible if inlet fraction and total flow can be joined on a verified clock, flow units/reference conditions and inlet composition are resolved, and room volume/pressure/venting plus sensor position/calibration/delay are documented. The repository API does not model oxygen transfer into liquid culture or evaporation, so the liquid traces are outside this boundary.

Deferred Hangang case `oxygen-hypoxia-chamber-gas-transfer-model-link-gap` checks the CC0 record identity, exact publisher file listing and the acquisition gap. It does not read observations or execute the model. Until the workbook is acquired and its raw headers/row conditions reviewed, do not construct a source boundary from the README descriptions or claim a measured-model comparison.
