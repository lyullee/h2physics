# Learned native monitoring of physical prediction residuals

`h2physics.adapters.process_monitoring` connects physical/instrument predictions
and observations to the actual optional Process Monitoring Toolkit. The first
level uses its native mode-specific PCA models, train-only normalization,
causal window features and separate normal-reference threshold calibration.
The fitted native monitors, scikit-learn PCA objects, scalers, native signal
batches and native results remain available for Python composition.

A score describes deviation from the configured residual reference. It does
not identify a leak, determine a physical cause, classify an untrained fault,
estimate annual risk or command a protective action. No detector, PCA solver,
EOS, inventory equation or instrument-response solver is reimplemented here.

The related `h2physics.adapters.sensor_calibration` module optionally estimates
the first-order concentration sensor's time constant from paired sampled truth
and indication histories. It requires matching clock, quantity basis and units,
distinct source-series IDs, an initial indication, an episode origin, a maximum
sample gap and bounded positive search interval. The fitter reuses the existing
piecewise-linear input/first-order response law and retains an immutable residual
receipt. It does not estimate gain, offset, transport delay, noise or uncertainty;
an RMS fit error is not a confidence bound. It does not qualify the detector or
provide a public field dataset. See [sensor calibration](SENSOR_CALIBRATION.md).

## Native source and installation

The [user's official repository](https://github.com/lyullee/process-monitoring-toolkit)
has MIT-licensed source version 0.1.0 at immutable revision
`79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a`. Both the PyPI project and JSON
metadata endpoint returned 404 at review. This adapter uses a locally built
wheel from that exact official source archive; it does not assume a published
same-name distribution or substitute another package.

The ignored target is `artifacts/native_monitoring_packages`. Only the native
package and reviewed scikit-learn 1.9.1, joblib 1.6.0, cloudpickle 3.1.2,
threadpoolctl 3.7.0 and narwhals 2.28.0 were installed there with `--no-deps`.
The main NumPy/SciPy/pandas environment was not modified. Build dependencies
were confined to pip's temporary isolated build environment. No external
signals, pretrained weights or benchmark datasets were installed. Original
native notices remain in the separate target.

[monitoring_dependency.toml](../research/monitoring_dependency.toml) records
the source archive, built wheel, native source files, dependency wheels and
license-file hashes. The 28 installed native Python files are byte-identical
to the official archive. No native code or data is bundled with the host.
Importing the host module loads neither the native package, scikit-learn,
cloudpickle, Cantera nor LH2DT.

`NativeProcessMonitoring.from_installed()` is the explicit optional import.
It checks the reviewed native tree and tested native/scikit-learn/cloudpickle
versions. Native source is checked again at operation boundaries. Application
code selects its separate package target through its Python environment;
the adapter does not install packages or alter `sys.path`.
The called native method/function origins and bindings are also retained and
checked. Rebinding a method on an otherwise unchanged class cannot silently
change the calculation basis while leaving source files and trained weights
unchanged.

## Residual and provenance contract

`residual_batch` accepts the existing `TimeSeries` and `Variable` objects.
Observed and predicted samples must have identical time arrays and clock IDs.
There is no interpolation, clock offset estimate or gap fill.
The existing TimeSeries constructor revalidates current values at admission,
including nonempty clock/source identities, while the original objects remain
retained.

Each ordered `ResidualFeature` declares observed/predicted column names, a
physical Variable, both physical locations and a positive scale with its
evidence ID. Locations must agree; quantity, unit and reference basis must
match both series. Pressure uses Pa with an explicit absolute/gauge/differential
basis and temperature uses K. Other quantities retain their exact supplied
unit/basis without conversion. The caller owns the original measurement-location
binding; a matching string does not independently qualify that binding.

The native `predicted_measurement_residual` calculates
(observation−prediction)/scale. Scale is in the original physical unit. It is
not silently interpreted as Gaussian sigma, a manufacturer's accuracy bound,
a coverage interval or the sum of several uncertainty sources. Signed
measurements and signed residuals are retained.

The usable mask is the intersection of the original masks. An unusable
residual is NaN and remains invalid. A valid nonfinite native residual fails;
it is not changed to zero. The output is both an actual native `SignalBatch`
and the existing immutable `ObservationTable`, retaining source IDs,
whole-run groups, clock, physical meanings and per-feature origin.

`ResidualContext` records partition ID, role, physical/model scope, observed
mode definition, prediction-model identity and observation-operator identity.
Fitting/calibration also require explicit normal-reference evidence.
`prediction_owner` retains the actual physical/observation owner that produced
the prediction. The original TimeSeries, feature definitions, context, native
batch and ObservationTable contents are fingerprinted and rechecked.

The caller supplies a nonempty episode ID and observed operating mode for
every row. Modes and group labels are metadata, not numerical sensor inputs.
Episodes must identify whole source experiments/runs consistently across
partitions. Renaming a reused experiment does not create independent evidence;
the adapter can check declared groups, not discover hidden common ancestry.
No normality, clock registration, instrument calibration or source independence
is inferred from an evidence label.

## Python lifecycle

Prepare separate observed/predicted TimeSeries pairs for fitting, calibration
and held-out evaluation, then build them with this pattern:

```python
from h2physics.adapters.process_monitoring import (
    NativeProcessMonitoring, NativeResidualMonitor,
    ResidualContext, ResidualFeature, residual_batch,
)
from h2physics.observations import Variable

native = NativeProcessMonitoring.from_installed()
columns = (
    ResidualFeature("P_error", "P_observed", "P_indicated",
        Variable("P", "pressure", "Pa", "absolute"),
        "vessel-P1", "vessel-P1", 100., "explicit-100Pa-residual-scale"),
    ResidualFeature("T_error", "T_observed", "T_indicated",
        Variable("T", "temperature", "K"),
        "vessel-T1", "vessel-T1", .1, "explicit-0.1K-residual-scale"),
)

def prepare(role, observed, predicted, episode, modes, prediction_owner):
    return residual_batch(
        native, observed, predicted, columns,
        context=ResidualContext(
            f"{episode}:{role}", role, "explicit-physical-envelope",
            "observed-mode-definition", "physical-model-reference",
            "instrument-observation-operator",
            "independently-confirmed-normal-reference" if role != "evaluation" else "",
        ),
        episodes=(episode,)*len(observed.time_s), modes=modes,
        prediction_owner=prediction_owner,
    )

# fit_data, calibration_data and heldout_data are separate prepared source runs.
monitor = NativeResidualMonitor(native)
monitor.fit(fit_data)
monitor.calibrate(calibration_data)
answer = monitor.evaluate(heldout_data)
usable_scores = answer.scores[answer.valid]
actual_pca = monitor.native_model.monitors["observed-mode"].detector.model
```

The example scales are caller-authored examples, not fitted device values.
The existing instrument adapter supplies expected indicated values after
native lag/calibration/range effects when appropriate. Process truth and
instrument indication are different prediction planes; comparing an indicated
measurement directly to process truth requires an explicitly different
observation operator.

The default settings use four-row causal windows, per-channel mean/std,
maximum gap 1.5 s, one PCA component and a separately calibrated empirical upper
5% score quantile. All are explicit replaceable settings. The native
`Monitor` owns its scaler and PCA; native `ModeMonitor` owns one such monitor
per observed mode. Train-only standardization follows the physical residual scaling;
the resulting PCA score describes a learned covariance reference rather than
an absolute physical uncertainty-budget exceedance. Fitting, calibration and
evaluation are separate operations. Calibration is checked not to refit the model/scaler/feature
parameters. Every fitted mode needs usable independent calibration data.

Evaluation cannot reuse fitting/calibration partition IDs or whole-run
episode IDs. Feature order, units/basis, physical location, scale evidence,
prediction/observation identity and mode scope must agree. Native model,
scaler, threshold or setting mutation is rejected. No online refitting or
automatic adaptation to unalarmed operation is performed. Start a new owner
for a new fitted campaign.

Native mode scores are their combined-PCA score **minus that mode's calibrated
threshold**. The public result's zero threshold is therefore a mode-specific
score margin, not a probability. Individual native thresholds and models are
retained. A nominal calibration fraction is an empirical quantile setting;
it does not guarantee a future false-alarm rate.

## Causality, abstention and failure evidence

Windows end at the sample being scored. Native features do not cross a
declared episode, mode change, invalid sample or excessive gap. Removing
invalid samples and joining the remaining time axis is not permitted.
Unseen observed modes abstain. Warmup/gap/missing/unseen-mode rows have NaN
scores, `valid=False` and `alarms=False`; this means no usable decision.

This level evaluates finite supplied batches with causal windows. Prefix
invariance is tested. It does not implement a new bounded-memory streaming
state machine, alarm persistence/latching policy, automatic mode inference,
control loop or physical fault diagnostic.

`MonitoringEvaluation` keeps the actual native result and separate read-only
score/time/mask/alarm snapshots, together with fitting/calibration data, native
model and trained-state hash. Raw native objects remain inspectable and mutable;
later mutation of raw result arrays does not change the snapshot.

Native fit/calibration/evaluation failures raise `MonitoringNativeError`
with the original exception as cause. It retains the attempted data, actual
mode owner and factory-created native monitor attempts, last admitted model
hash, completed fitting/calibration data and prior evaluations. No alternative
detector, filled matrix or default threshold is used. The failed campaign
becomes terminal, including an admission failure, while its evidence remains
inspectable. Unexposed temporary objects created inside a failing sklearn
call cannot be returned by this native API.

## Executed coupling and qualification boundary

Run from the repository root with the reviewed native target installed:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_process_monitoring.py -q
.venv/Scripts/python.exe -X utf8 scripts/check_process_monitoring.py
```

The replay reuses a finite Cantera H2 gas enclosure with an actual wall,
ReactorNet and signed cosine heat input. It retains mass/U ledgers and checks
the independent analytic heat integral. Actual LH2DT pressure and temperature
transmitters then produce the predicted indication. Authored independent noise
realizations define disjoint fitting, calibration and held-out episodes.
One held-out realization contains an explicit pressure-indication offset.
The same deterministic process scenario is reused; this is synthetic software
verification rather than independent physical experiments.

The native learned model is checked against an independent covariance
eigenspace. Separate calibration, original failures, temporal prefix behavior,
masks/gaps/episode/mode boundaries and object/state integrity are exercised.
Detailed numbers and final fingerprints are in
[process_monitoring.md](../research/process_monitoring.md).

Primary API/method sources are the
[pinned native contracts](https://github.com/lyullee/process-monitoring-toolkit/blob/79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a/docs/API.md),
[pinned native method definitions](https://github.com/lyullee/process-monitoring-toolkit/blob/79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a/docs/METHODS.md)
and [official scikit-learn PCA reference](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html).
This adapter does not reproduce the toolkit's other advertised algorithms or
import its external benchmark results as hydrogen-facility validation.
Measured healthy/fault campaigns, source-specific uncertainty/model-error
budgets, historian clock/location qualification and independent transfer
assessment remain open.
