# Mendeley SOFC polarization curves and shared-stack bridge

The Mendeley v1 record [10.17632/j8b9v4cb9d.1](https://doi.org/10.17632/j8b9v4cb9d.1)
is licensed CC BY 4.0. It contains four text files with SOFC polarization grids
at 750, 775, 800 and 825 °C and nominal H2/H2O/N2 feed fractions in filenames.
The publisher states the collection includes both experimentally measured and
multiphysics-model-generated curves; individual voltage origins are not
identified, so all values remain source-reported with unresolved origin. Retain
creator attribution and the DOI when reusing these data.

## Hash-pinned Python API

`h2physics.data.load_sofc_polarization_data(path)` accepts only one of the four
manifest-listed v1 files after checking exact size and SHA-256. It parses the
two-row text grid through the existing `load_polarization_grid` reader. The
header's degree/current-density glyphs are corrupted; the declared Mendeley
description and already-reviewed source profile supply fixed units: °C,
mA/cm², and V. The reader preserves the voltage `Origin.UNRESOLVED` and returns
one source-bound `ObservationTable` per temperature.

## Existing fuel-cell core connection

`h2physics.adapters.compare_sofc_curve_with_hydrogen_stack(...)` sends one
available same-file temperature condition and its recorded current-density
rows through the existing `HydrogenStack.evaluate(mode="fuel_cell")` model.
It retains the source voltage, row ID, exact stack owner, file hash, caller
thermochemistry/loss evidence, and each `StackResult`. Its `require_current()`
rechecks the source bytes and reproduces every model result. The returned cell-
voltage residuals are diagnostics only; there is no fit, interpolation,
extrapolation, or model acceptance threshold.

The caller supplies active area/series-cell geometry and SOFC-applicable
thermochemistry and polarization losses. The data do not identify which curves
are experimental, local electrode gas activities, pressure, reaction-state
thermochemistry, or the material/cell geometry needed for independent
qualification. A fit to any selected curve would be source-specific curve
reproduction, not independent validation. The Hangang contract
`sofc-polarization-existing-hydrogen-stack-bridge` uses a synthetic stack model
and checks the file/API binding only; it is not SOFC model validation.

The source hashes, exact filenames and sizes are in
`research/data/sofc-polarization.toml`. The raw publisher files remain in the
ignored data area and must be pinned/staged for the deferred Hangang case.
