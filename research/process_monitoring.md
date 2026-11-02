# Native physical-residual monitoring verification

2026-10-28. Original host composition of actual native learned PCA monitoring,
existing finite gas thermodynamics and existing instrument response. This is
software/numerical verification on authored signals, not measured fault
validation, instrument qualification or calibrated facility risk.
The [public contract](../docs/PROCESS_MONITORING.md) defines the scope.

## Native ownership and provenance

The official [user repository](https://github.com/lyullee/process-monitoring-toolkit)
was inspected at immutable revision
79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a. Its project metadata declares
version 0.1.0 and MIT. The original LICENSE and THIRD_PARTY_NOTICES files were
inspected and remain in the separately installed distribution. The PyPI project
and JSON metadata endpoint returned 404; there was no assumed published wheel.

| Artifact | SHA256 |
|---|---|
| Official immutable source ZIP | b75ce534eb8da0d4977ed9ad1221492065adcdc3a12d38487a09d13cd63ff1d5 |
| Locally built native wheel | 05c9d5473433844a80915727e8e98200ec917b57ce66e0d0bd0ba4bf4defecd4 |
| Native MIT LICENSE | e0fef3c9588ffa333d456718f5c32ae9450ffeedcaa710e7c6cc44d8c568c06a |
| Native THIRD_PARTY_NOTICES | 0ded0d0fac922dc95c939d7c34caaa107904652fc22aafd2b6f656313fead2fd |
| Built wheel METADATA | 99ffd71e4ba5323a214f4048f250833b140b5a5df89d5cf1dfd5f7cae2242e6b |
| Actual native Python aggregate | 6c4b02f9d578b33c08194a5545e0f524a0b937373aad4f1981e814c3e12ac10b |

All 28 installed native Python files were compared byte-for-byte with the
official archive. The aggregate is SHA256 of sorted relative Python paths and
original bytes under process_monitoring. The isolated target also contains
reviewed scikit-learn 1.9.1, joblib 1.6.0, cloudpickle 3.1.2,
threadpoolctl 3.7.0 and narwhals 2.28.0. Actual dependency wheel URLs/hashes and
original license hashes are in
[monitoring_dependency.toml](monitoring_dependency.toml).
The first four dependency licenses are BSD-3-Clause and narwhals is MIT.

The native source wheel was built with pip's isolated build backend, then
installed with --no-deps into artifacts/native_monitoring_packages. Main
NumPy 2.5.4, SciPy 1.18.1 and pandas 3.1.0 were not upgraded or replaced.
No .csv/.pkl/.npy/.pt/.onnx files were in the inspected native wheel. No
external observations, pretrained weights, implementation code or coefficient
tables were copied into host source or distributions.

Native objects actually used and retained are SignalBatch, ModeMonitor,
per-mode Monitor, WindowFeatures, StandardScaler, the native PCADetector and
its actual sklearn.decomposition.PCA. Native fit/calibrate/score and
predicted_measurement_residual own the calculations. The host checks meaning,
admission, state integrity and returned decision semantics. It does not
implement another detector or physical model.

## Executed physical and statistical case

The physical reference reuses CanteraOpenGasVolume: actual native ReactorNet,
finite 0.05 m3 pure H2 inventory, initial 350 K/200000 Pa absolute, output 100–220 s
at 1 s spacing and maximum native step 0.5 s. The existing frozen native gas
thermochemistry has explicit unresolved H2 spin identity. A real stationary
Wall applies signed 20cos(2pi(t−100)/120)W. There is no external mass flow.
The independent energy check is its analytic heat integral, evaluated against
native stored U. The pressure/temperature move; this is not a constant
reference-field mock.

Actual native LH2DT FirstOrderTransmitter pressure/temperature models, through
the existing Lh2dtTransmitter adapter, generate expected indicated values.
Their authored held-input time constants are 2 s and 3 s, with explicit initial
native states, range 0–1e6 Pa and 0–1000 K, native state/readings and physical
bulk-vessel location. This pressure is not substituted for a physical
pressure-triggered protection input.

Authored noise uses separate seeds 101 fitting, 202 calibration, 303 nominal
heldout and 404 shifted heldout. The temperature residual is an authored
correlated combination of two random draws. Physical residual scales are
80 Pa and 0.06 K, with explicit authored IDs. They are not measured sensor
standard deviations. The shifted observation has a +7-scale pressure
offset over 160–200 s. No source material/facility fault law was fitted.

Each realization is an explicitly different whole-run group on the same
authored scenario/reference clock. This split verifies lifecycle isolation
and deterministic synthetic behavior. Reusing one deterministic physical
scenario with different noise does not establish independent experimental
conditions or transfer to another plant.

Observed modes are the declared sign of the prescribed heat command:
warming/cooling. They are metadata, never numerical fault labels.
Four-row mean/std features are computed by the actual native causal feature
owner with 1.5 s maximum gap. Each observed mode has its own trained native
scaler and one-component PCA. Native combined-PCA scoring and separate
empirical 95th-percentile calibration determine the thresholds. No threshold
was adjusted against the heldout offset case.

| Final replay result, both numerical profiles | Observed |
|---|---:|
| Nominal heldout usable rows | 112 |
| Nominal heldout alarm fraction | 0.008928571428571428 |
| Offset interior alarm fraction, 164–198 s usable rows | 1 |
| Cooling native threshold | 9.934772369099182 |
| Warming native threshold | 6.584596399434747 |
| Maximum finite native mass residual kg | 0 |
| Maximum finite native energy residual J | 1.3270816623389692e-7 |

These alarm fractions are authored demonstration outputs, not estimated
future false-alarm/detection probabilities. The native output is a
mode-specific score minus that mode's calibration threshold, compared with
zero. Negative margins are meaningful usable values; invalid NaN margins are
abstentions. Scores are not physical severity or fault/cause probabilities.

An independent covariance eigenspace check agrees with the actual trained
native PCA projection to 1e-10. Calibration is checked not to refit any native
detector/scaler/feature parameters. The native trained-state hash is equal
before/after every successful evaluation. Prefix scoring matches the complete
evaluation exactly within the numerical comparison, including validity.
Invalid samples, excessive gaps and episode/mode boundaries reset windows.
Unknown modes abstain. No absent measurement is imputed or labelled healthy.

## Review corrections, guards and preserved failures

A narrow review reproduced a method-binding gap: forwarding through the
original ModeMonitor.score under a replaced class method passed the old
class-object/source-file/trained-state guards. The source file and trained
hash were unchanged. The provider now records 22 actual called native method/
function origins, module/file/qualified names, function/code references and
defaults. Source/exports/call bindings are rechecked at operation boundaries;
the actual forwarding-method regression rejects with original failure context.

The same review reproduced admission of empty current clock IDs after
explicit mutation of otherwise valid frozen TimeSeries. Admission now
reuses the existing TimeSeries constructor to revalidate current fields,
while retaining the original source objects. Empty current clock/source
regressions reject. ResidualContext and ResidualFeature current fields are
also revalidated; source/mask/array/feature/metadata fingerprints are checked.

Whole-run fitting/calibration/evaluation identities must be disjoint and their
physical/model/mode/feature contracts must match. Normal-reference confirmation
is explicit for fitting/calibration. The checks operate on declared provenance:
they do not discover experiments that were relabelled to hide common ancestry.
Retaining a prediction owner is a Python composition/provenance boundary; the
adapter does not independently replay every arbitrary caller prediction.

Actual native no-usable-training-window and insufficient-calibration failures
are preserved. MonitoringNativeError retains the original exception, actual
ModeMonitor, factory-created native Monitor attempts, attempted data, completed
fitting/calibration data, last admitted model hash and prior evaluations.
Native code does not expose every temporary object inside a failing sklearn
fit; those are not claimed retained. A failure is terminal for this campaign.
There is no fallback detector, zero-filled reference or guessed threshold.

Raw native DetectionResult objects and separate read-only host score/time/
valid/alarm snapshots are retained. A regression mutates a raw native result
and confirms the original snapshot remains unchanged. Model-state mutation
and mutable native batch-metadata tampering are rejected before scoring.

## Final executed checks and fingerprints

Final scoped source:

- 25 tests passed in 23.10 s, no skips; Ruff passed.
- Main SciPy 1.18.1 actual native replay 18/18 gates passed in 12.2333951000 s.
- Compatible SciPy 1.16.3 actual native replay 18/18 gates passed in 8.1748902000 s.

Durable ignored logs are tests-reviewed-final.log, replay-reviewed-final.log
and replay-compatible-reviewed-final.log under artifacts/monitoring_feasibility.
The earlier 22-test/development replays remain separate evidence for the
pre-review source. Both final replays record matching source/test/script and
native begin/end hashes. Commands from the repository root:

```powershell
.venv/Scripts/python.exe -m ruff check src/h2physics/adapters/process_monitoring.py tests/test_process_monitoring.py scripts/check_process_monitoring.py
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_process_monitoring.py -q
.venv/Scripts/python.exe -X utf8 scripts/check_process_monitoring.py
```

For the compatible profile, preload SciPy from the separately installed
artifacts/native_hyram_packages target, then execute the same script; no
monitoring dependency or source changes are made between profiles.

| File | SHA256 at both final replay boundaries |
|---|---|
| src/h2physics/adapters/process_monitoring.py | 971a5ba6227e393d5f4bb970ad4b1d1f15f3e7e153131ab950be404aa310b1f8 |
| tests/test_process_monitoring.py | ba4372347476045c766ab46c5064a9dc2813e4b02b9ebe216fce28c52bbb1dd5 |
| scripts/check_process_monitoring.py | d5b65d00123b8b33a0fcbad1d205eabc5139694c89a7ea33175de779404cbc29 |

The main-profile trained-state hash is
e2174e1c9de19636bb601271c9cceda43a2502c2de33de4c414d512576bb56e1.
Fitting/calibration residual hashes are respectively
fcc433ff77f745d48abc2813c20ea6a3eef780f78ea125285079bcafe5ea1294 and
afae195f735d1902223f43b822e9f647100c77638d102caa86c7ef048ec9ba00.
These serialization hashes identify the actual local state; they are not
portable model interchange or experimental validation certificates.

All six owned text files use LF. Final six-file hashes are reported after
writing this record; its own hash is not embedded recursively. No shared
catalog/general docs/requirements/request file or receiving repository was
edited by this lane.

## Remaining applicability and receiving work

The [pinned native API](https://github.com/lyullee/process-monitoring-toolkit/blob/79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a/docs/API.md),
[native method definitions](https://github.com/lyullee/process-monitoring-toolkit/blob/79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a/docs/METHODS.md)
and [official PCA reference](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)
are primary sources. Original finite-volume and instrument owners retain
their existing thermodynamic/observation scopes and native source receipts.

This first level does not expose the toolkit's other detector families,
inventory-residual utilities, streaming state machine or elapsed-time alarm
policy. It has no fault classifier, online adaptation, control action,
annual-frequency conversion or protection-system credit. A receiving typed
source bridge should preserve quantity/reference/location and native owner
identities as first-class objects rather than only metadata; stable native
trained-state receipts and per-mode partial-failure returns would reduce
host bookkeeping. No missing capability was replaced by another algorithm.

Source-specific healthy/fault experiments, model discrepancy and uncertainty
budgets, historian pressure/location/clock admission, independent mode
definitions and cross-equipment/operating-envelope validation remain open.
The toolkit's external benchmark results are not imported as hydrogen-facility
validation.
