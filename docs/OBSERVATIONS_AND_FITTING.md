# Non-time observations and native fitting

## Table identities

An isotherm, polarization curve or material property table does not need a time coordinate.
`ObservationTable` retains a two-dimensional array, immutable validity masks, one `Variable`
per column, source-row IDs, experiment-group IDs, per-column `Origin` and named context.
Repeated/decreasing coordinates are allowed and no sorting, interpolation or row removal
occurs implicitly. Missing data remain masked values rather than zeros.

`Variable(name, quantity, unit, basis_id)` separates physical meaning from the printed unit.
Two Pa columns are incompatible if one is unresolved reported pressure and another is
absolute pressure. Reference-volume uptake in m³/kg cannot become mol/kg until the
reference gas state and molar mass are explicit. Excess/absolute uptake and the adsorbent
mass convention need their own basis evidence.

`content_sha256` fingerprints arrays, masks, variable meanings, origins, source, row/group
identities and context. It complements the original-file hash: a filename alone does not
identify the exact data used by a fit. `concatenate_observations` retains source row order
and parent fingerprints. It requires matching variables and origins, not guessed conversions.

## Example: loading a table without time

```python
from pathlib import Path
from h2physics.core import Origin
from h2physics.data.loaders import Column, load_observation_table

with Path("isotherm.csv").open(encoding="utf-8-sig", newline="") as source:
    observations = load_observation_table(
        source,
        columns=(
            Column("P_bar", "pressure", "pressure", "bar", pressure_basis="absolute"),
            Column("q_mmol_g", "uptake", "specific_amount", "mmol/g",
                   basis_id="reviewed:absolute-H2-per-dry-adsorbent"),
        ),
        experiment_id="apparatus-A/run-01", source_id="reviewed-record/file-01",
        origins=(Origin.MEASURED, Origin.MEASURED),
    )
```

The declarations in this example are assertions that require source evidence. They must
not be substituted into the ambiguous acquired files simply to make a model run.
`reported_pressure` accepts only unit scaling and retains an explicit unresolved basis;
it cannot satisfy a model's absolute-pressure variable contract. Basis IDs also survive
time-series loaders and must match when requesting a reference-dependent channel.

## Experiment grouping and fitting

Use `split_experiments(table, held_out={...})` before fitting. Entire declared groups move
to the held-out subset. The code rejects unknown groups, an empty split or a split that
uses every group. Group separation prevents row leakage but does not prove independence
of instruments, materials, apparatus or the source used to develop a model.
`ExperimentPartition.require_partition_of(source)` rechecks both child tables against
the exact row order, values, masks, group IDs, variables, origins and context from the
original source. This is a lineage check; it does not upgrade the held-out data into an
independent validation set.

`research.fit_observations` accepts native `Variable` specifications, a tuple of
`BoundedParameter(name, initial, lower, upper, scale)`, a named observation-model identity
and a Python prediction function. The prediction function receives the observation table
and an immutable mapping of parameter values, and returns a vector in the response unit.
It can call existing native equipment/equilibrium objects directly; no serialization is needed.

Finite parameter bounds, starting values and scales are explicit. Jointly invalid rows
are omitted with their original identities retained in the result. A prediction must be
finite for every retained row; changing parameters must not change the residual's row set.
Residual normalization is a numerical scale. It is not automatically an instrument standard
deviation, and the result does not invent a covariance matrix or confidence interval.

The fit defaults to SciPy's `loss="linear"`, preserving ordinary least squares. For data
with a pre-identified outlier-contamination concern, callers may select `soft_l1`, `huber`,
`cauchy` or `arctan` and provide a positive `f_scale` in normalized-residual units. This is
an explicit estimator choice, not an automatic outlier detector or a substitute for reviewing
source records. `FitResult.optimizer_loss` and `optimizer_f_scale` retain the choice. Its
`optimizer_cost` is the selected loss's objective, while `root_mean_square_error` remains the
unweighted RMSE of the original response-unit residuals; these values need not track each
other for a robust loss.

The deferred Nurion case `research-fit-robust-loss` exercises the unchanged linear default,
the recorded robust-loss settings, a synthetic gross-outlier comparison, and invalid option
rejection. It is a software contract only; it does not qualify any physical parameter fit.

`purpose="parameter_estimation"` requires a measured/reconstructed target origin.
Computed or unresolved targets require `purpose="curve_reproduction"`. Every fit retains
its purpose, model/data fingerprints, selected rows/groups, active bounds, parameter values,
response-unit RMSE and scaled-Jacobian singular values. `validation_qualified` stays false.

## Jacobian diagnostics and held-out assessment

The optimizer's residual Jacobian is multiplied by the declared parameter scales before
SVD. Numerical rank uses an explicit relative singular-value threshold (default 1e-8).
A deficient rank produces an infinite condition indicator. Full numerical rank is still
not proof of structural/practical identifiability; noise, parameter correlations, active
bounds, available input excitation and observation operators require separate analysis.

`assess_held_out` rejects any reused fitted row or experiment group. It checks the same
variable identities, records the held-out data fingerprint and returns bias, RMSE, MAE and
maximum absolute error. Those metrics are comparisons, not automatic validation or a
universal acceptance criterion. Declare application-specific limits and independent evidence
before qualifying a model.

## Actual open-data use

- `scripts/check_static_ingestion.py`: 36 MOF adsorption/desorption branches with 860 rows,
  and 16 SOFC temperature curves with 9080 records. No artificial time coordinate is used.
- `research/static_ingestion.md`: actual retained quantities, missing cells and unresolved
  pressure/STP/uptake origins. Both directions from one isotherm keep the same group.
- `scripts/fit_sofc_reproduction.py`: fits three complete temperature curves and holds out
  the 800 °C curve. Shared Butler–Volmer/ohmic loss primitives are used. Effective coefficients
  are not reinterpreted as standard thermochemistry or a uniquely identified electrode mechanism.
- `research/sofc_reproduction.md`: observed results, parameter bounds, singular values,
  dataset fingerprints and explicit reproduction scope. Voltage measurement/model origin
  remains unresolved, and the temperatures share a source/apparatus.

The maintained optimizer is [SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html).
No optimizer implementation is copied into this package.
