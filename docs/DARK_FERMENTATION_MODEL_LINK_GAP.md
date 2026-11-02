# Dark-fermentation hydrogen production: model-linkage gap

## Source and existing observation API

The source is Mendeley Data [Raw data v2, DOI 10.17632/2nwcdx9hst.2](https://doi.org/10.17632/2nwcdx9hst.2),
by Roberto Hernández under CC BY 4.0. The single acquired `Raw data.xlsx` is 165,296 bytes;
its SHA-256 is pinned in `research/data/dark-fermentation.toml`. The source-specific
`h2physics.data.fermentation.FermentationWorkbook` reader preserves raw cells, source
worksheet rows, missingness, formulas/caches and reactor labels. The worksheet has 830
data rows. `component_production_check()` compares publisher-derived component gas rates
against the total gas rate and reported fractions from the same export; this is an
internal consistency check, not an independent H2 yield measurement.

## Model linkage not admitted

The existing native `QsdSanAdm1Digester` API evolves liquid/headspace states and gas
production, but needs explicit biomass/feed inventory, reactor geometry, chemistry basis,
temperature, clock and gas transfer/vent boundary. The workbook's reported BP has unit
`m3_reported/s`; its gas reference pressure/temperature and wet/dry condition are not
defined. The H2/CO2/CH4 columns have fractions, but their denominator species and whether
they are volume or mole fractions are not documented. Their sampling/averaging alignment
to BP is unknown. HP/HY/HPR are reconstructed from other workbook columns; they are not
independent gas observations.

Additional blockers include `Duration` event zero/cadence and connection to feeds, liquid
working/headspace volumes, initial substrate/COD and biomass, feed/harvest histories, pH
dosing/control, gas collection/backpressure, and whether R1/R2/R3 are independent
experiments. The source preserves an HP/MP mismatch at worksheet row 239 (source Nr 241);
no values are silently repaired. Those issues prevent fitting ADM1 kinetics or using gas
traces as an independent prediction target. Available HRT, COD and reported concentration
fields do not recover the missing initial/process state.

The manifest now states these requirements explicitly. Deferred Hangang case
`dark-fermentation-h2-process-model-link-gap` checks source metadata only; it does not
open workbook rows, convert to molar flow, initialize ADM1, or claim process validation.

## Prepared request

The targeted request in [`requests/dark_fermentation_gas_basis_request.md`](../requests/dark_fermentation_gas_basis_request.md)
has not been sent. It asks for a row-keyed sidecar defining gas collection calibration,
reference P/T and moisture basis, fraction denominator and synchronized sampling, reactor
volumes, feed/COD/biomass initial conditions, event clock, replicate identity and
measurement uncertainty. A future gas comparison should be admitted only after these
fields map to exact workbook rows and the same physical units/bases as the model
observation operator.
