# PEM ripple curve input bridge

`h2physics.adapters.pem_ripple_stack.compare_pem_ripple_curve_with_hydrogen_stack`
maps one receipted single-cell IV member into the existing
`h2physics.electrochemistry.HydrogenStack` electrolysis evaluator. It preserves the
source curve and parent-archive/member checksums on an immutable diagnostic trace. It
does not add a second polarization solver.

The Mendeley Data v2 release [10.17632/93jz2rgy4d.2](https://doi.org/10.17632/93jz2rgy4d.2)
is CC BY 4.0 and its acquisition details, attribution, and member schemas are documented
in `research/data/pem-ripple-degradation.toml` and
`PEM_RIPPLE_DEGRADATION.md`. The parent ZIP is 90,759,411 bytes with SHA-256
`47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab`. The selected
member path is `PEM_ripple_degradation_data/IV_curves/PEM1/PEM1_Initial.csv`; it is
915,460 bytes with SHA-256
`a054dad7a1d5ce1f2154b60a79a1adea4f84d5ec00e23c12ca72639ffcddcf0d`, header
`current_A,voltage_V,step_index`, and 20,040 rows.

## Mapping contract

The source provides cell current in A, cell voltage in V and a sweep step index. The
bridge requires a source-reader-issued `PemRippleIVCurve` or
`PemRippleIVMemberCurve` and a one-series-cell
`HydrogenStack`. The stack's caller-declared `geometry.active_area_m2` converts each
measured current to current density; the caller supplies one temperature for the curve.
Both assumptions are attached by evidence identifiers. The returned rows retain the
source row number and step index, measured amperes and volts, projected current density,
caller temperature and native `StackResult`. The voltage residual is model cell voltage
minus source-reported voltage.

```python
from h2physics.adapters.pem_ripple_stack import compare_pem_ripple_curve_with_hydrogen_stack
from h2physics.data.pem_ripple_member import load_pem_ripple_iv_member

curve = load_pem_ripple_iv_member("data/processed/pem-ripple/2/PEM1_Initial.csv.gz")
trace = compare_pem_ripple_curve_with_hydrogen_stack(
    curve, existing_hydrogen_stack,
    temperature_k=caller_temperature_k,
    active_area_evidence_id="documented-area-source",
    temperature_evidence_id="documented-cell-temperature-source",
    model_evidence_id="documented-thermochemistry-and-loss-model",
)
trace.require_current()
```

This is a forward input and diagnostic comparison, not a parameter fit. The release does
not report active area or cell temperature, so those cannot be supplied as dataset
measurements. The publisher's fitted-parameter file is not used by the bridge. Caller
thermochemistry and losses must be independently justified for the source test state.
Until area, temperature, calibration, voltage/current uncertainty, operating state and
model applicability are established, the residuals are not validation evidence.

Deferred case `pem-ripple-iv-to-hydrogen-stack-diagnostic` uses only the compressed
selected member on Hangang and exercises source/member integrity and row lineage with
synthetic callbacks. It does not stage or verify the full parent ZIP on Hangang, and no
model accuracy or physical result is claimed.
