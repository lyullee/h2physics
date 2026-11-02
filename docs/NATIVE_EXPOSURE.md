# Conditional receptor exposure through native HyRAM6.1

`HyRAMExposure` evaluates supplied receptor heat/pressure data with the actual
separately installed HyRAM6.1 dose, probit and probability functions. It does
not calculate a release, flame, blast waveform, receptor projection, human
participation or event frequency. The existing native Flame/source acceptance
failures remain rejected. Every result has the status
`conditional-on-supplied-exposure`; a probability here verifies no source/fire chain.

The installed engine is GPL-3.0-only. Its code, harm coefficients and tables are
not copied or bundled by this adapter. Installed source/license/metadata hashes
and primary model references remain distinct from experimental qualification.

## Python API and direct risk coupling

```python
from h2physics.core import Origin
from h2physics.adapters.hyram_exposure import (
    HyRAMExposure, ExposureReceptor, ExposureHistory, NativeHarmSelection,
    incident_history_from_hyram_radiation,
)

# Install/import HyRAM separately in the chosen compatible environment.
engine = HyRAMExposure()
receptor = ExposureReceptor(
    "authored-receptor", "global-xyz", (4., -1., 1.5),
    "supplied-incident-flux-on-declared-receptor-plane",
)
history = ExposureHistory(
    receptor, [100., 105., 110.], [40000., 0.],
    "incident_radiant_flux", "W/m2", "left_hold",
    "authored-absolute-clock", "conditional-supplied-radiation",
    "authored-flux-basis", Origin.SYNTHETIC,
)
selection = NativeHarmSelection(
    "eise", 5., "explicit-native-model-choice",
    "caller-evidenced-applicability-not-independently-validated", Origin.SYNTHETIC,
)
result = engine.thermal_response(
    history, selection, additivity_evidence_id="explicit-additive-dose-no-recovery",
)
native_probability = result.native_result
conditional_probability = result.probability
verified = engine.verify_result(result)
assert verified is result
```

For a direct typed boundary from the actual HyRAM+ flame/radiation adapter, use
`incident_history_from_hyram_radiation(radiation, observer_index=..., start_s=...,
end_s=..., receptor_id=..., basis_id=...)`. It requires an accepted native
radiation result and a live unchanged native flame. The chosen observer retains
its exact global coordinates and source frame. The absolute interval must fit
inside the caller-evidenced `SteadyFlameWindow`; the result is a single
left-held `incident_radiant_flux` value with the same source and clock. The
history fingerprint includes the source and steady-window evidence IDs.
This adapter supplies no transient fire evolution, receptor normal/projection,
absorption, shielding, or fire-duration estimate. The interval is a caller
assumption about exposure while the native steady result applies, not a duration
predicted by HyRAM. Use the existing source/radiation API and this adapter as
one chain; do not substitute a separate project radiation surrogate.

For a native HyRAM Bauwens static peak, `pressure_peak_from_hyram_overpressure()`
requires the owner's current `BauwensPeakResult` and an explicit receptor index,
clock support, receptor ID and pressure basis. It carries gauge pressure rise
(the ambient absolute pressure is not passed as the peak), the native event
clock/frame/source and event, participating-fuel, ambient and domain evidence.
The declared support must include the event snapshot time. HyRAM provides no
waveform, arrival time or positive-phase impulse here, so `positive_impulse_pa_s`
remains `None`; the support is caller context and is not a predicted duration.
Hangang contracts `hyram-bauwens-result-issuer` and
`hyram-bauwens-native-exposure-handoff` are deferred under profile
`hyram-overpressure`. Both require the separately staged HyRAM6.1 installation.

An existing finite `PoolFireTrace` can feed this exposure API through
`exposure_history_from_pool_fire(trace, receptor_id, basis_id=..., evidence_id=...)`.
The adapter requires the original current trace, preserves contiguous stage
edges and receptor activity, and inserts zero incident flux over the inactive
tail of a stage. It preserves the source clock/frame/position, declared origin,
and caller, seed, ignition, stage, receptor geometry and transmission evidence.
The output remains incident scalar W/m²; it is not absorbed heat or a receiver
surface energy balance. The trace's own scope flags still apply: no fire
feedback, spreading, dispersion, ignition probability or fully validated LH₂
fire chain is inferred. The deferred Hangang case is
`pool-fire-exposure-history-handoff` under profile `pool-fire` and uses the
separately staged pool-risk provider package, not HyRAM.

Model choice and normal-distribution mean are required inputs. The supplied
mean must match the actual native published probit convention, inspected from
its API; changing that convention without refitting the native coefficients is
rejected. Canonical native thermal keys are exposed in `engine.thermal_models`,
and pressure keys in `engine.pressure_models`. The selection's evidence and
applicability IDs are caller declarations, not proof of calibration/domain.
No model or exposure-duration default is inferred.

`ExposureResult` exposes `probability`, `receptor_id`, `frame_id`, `clock_id`,
`support_s`, `source_id`, `model_id`, `evidence_id`, `assumption_evidence_id`,
`thermal_dose`, `fluence_j_m2`, `peak_overpressure_pa`,
`positive_impulse_pa_s`, `status` and source/input fingerprints.
It retains the actual `.input`, `.selection`, `.native_module`, `.native_probit`,
`.native_result`, `.native_calls` and native quadrature records. Native functions
return scalars; no fabricated native result object is supplied. Risk consumers
may retain this result object and its conditional probability directly, with
separate source-to-harm/occupancy/branch evidence. A dose-only result has no harm
probability and cannot implicitly become a risk branch.

Before binding a cached result to a risk branch, call the owner's public
`verify_result`. It requires an actual `ExposureResult`, reexecutes the existing
native path using the retained input/selection/assumption/tolerance, checks the
bound source/input/model/mean/evidence/status identity and compares probability,
dose, fluence, peak/impulse, native probit/raw result and actual native-call
function/arguments/results. It returns the **original object** after verification.
Changing a summary with `dataclasses.replace`, relabeling the model or detaching
the raw native scalar from its recorded call is rejected. A structural object
with a matching probability cannot claim computed-native provenance.

`ExposureVerificationError` retains the supplied record, actual native replay
when available, native module and cause. Native QUADPACK workspace comparisons
use only meaningful active entries/diagnostics; uninitialized allocated tails
are not compared. This verification adds no harm/response algorithm and does
not promote a conditional exposure to a verified source/fire chain.

## Complete clock histories and dose meaning

`ExposureHistory` has explicit receptor/frame/position/basis, absolute clock,
source and origin. `left_hold` uses N increasing time edges and **N-1 interval
values**, so no unexposed terminal spike is inferred. `linear` uses N values,
one at every edge. Units are literal SI: radiant flux W/m2 and gauge overpressure
Pa. There is no extrapolation, clock alignment, missing-value filling or unit
guessing. Masks/nonfinite/sign-invalid heat data remain inspectable and cause a
retaining evaluation error. Boolean/complex physical arrays are rejected.

Native constant-flux thermal dose has units `(W/m2)^(4/3) s`. With the explicit
additive/no-recovery assumption, held histories sum the native interval doses:
`D_total = sum(D_native(q_j, delta_t_j))`. This is exact for that declared
piecewise-constant dose law. Linear histories integrate the **native unit-time
dose rate** using SciPy quadrature: the native dose for1s divided by1s is the
SI rate. The adapter does not reimplement its intensity exponent or probit
coefficients. Quadrature tolerance/raw records and every native call are retained.

Each native thermal model depends on the scalar accumulated dose, so the chosen
native dose-to-probit function and native probability CDF can be applied to the
sum directly. No invented effective flux, averaged probability or mean-flux
replacement is used. This is a conditional equivalent-dose extension; biological
recovery, repeated-event memory, movement, escape and model validity for a given
pulse history are not established by summing doses. The caller must evidence
that reduction for the intended case.

Radiant fluence `integral(q dt)` in J/m2 is a separate diagnostic. Equal fluence
does not imply equal native dose. Incident and absorbed flux are distinct
quantities. `thermal_dose` permits either as a labeled mathematical diagnostic;
`thermal_response` requires **incident** flux for these native models. It never
infers absorptivity, clothing, transmission, projected area or an absorbed-to-
incident conversion. Model-specific native factors remain inside the selected
engine function. No absorbed-flux harm calibration is invented.

## Waveform, peak and positive-phase pressure

`pressure_response` accepts a `gauge_overpressure` history or an explicit
`PressurePeak` carrying peak Pa, optional positive-phase impulse Pa*s, receptor,
clock support, source and pressure-basis evidence. Absolute pressure is not
converted by subtracting an assumed ambient. Incident/reflected/local pressure
and sensor/receptor transfer must be evidenced in the input basis; this adapter
performs no wave propagation, reflection or shielding calculation.

An explicit `positive_phase_evidence_id` selects the positive gauge part of the
supplied waveform. The peak is its maximum positive pressure and impulse its
positive-part time integral. Original negative phases are retained, not changed
or silently integrated as positive impulse. For a held waveform the integral
is exact; linear segments use native SciPy quadrature. This reduction discards
waveform details because the chosen native model uses only peak, or peak plus
impulse. It does not assert that all wave shapes with those summaries have the
same physical consequences outside that native assumption.

The native pressure function signature determines whether impulse is required.
Missing impulse for an impact model is rejected; it is not replaced by zero or
estimated from peak/duration. Peak-only models receive no unused impulse. The
native convenience wrapper has a zero-impulse short circuit even for pressure-
only models; passing an irrelevant zero to it changes its result. This adapter
uses the chosen native pressure function with its documented inputs and records
that distinction; it neither alters native code nor chooses another harm model.

## Numerical/failure limits and rights

Zero thermal exposure uses the actual native zero branch. The native wrapper
does not expose its intermediate probit there, so `native_probit` is None.
Positive dose underflow, nonfinite native dose/probit/probability, integration
failure, invalid/missing data, unsupported model/convention and absent required
impulse raise `ExposureEvaluationError`. The error retains the exact input,
selection, actual native module, successful native-call prefix, raw returned
results, quadrature diagnostics, failed-call function/arguments and original
cause. Native probabilities can numerically saturate at0/1 in CDF tails; that
is not proof of physical certainty or independent validation.

Actual source bytes, function/code/default bindings and native model dictionaries
are checked before/after evaluation. Inputs and scalar/array snapshots are
immutable by normal API use; native objects remain available for deep Python
inspection. Editing them invalidates prior evidence. No native source copy or
monkeypatch is used. The main environment is unchanged; the separate native
target can supply SciPy1.16.3, while probability/dose replay also checks1.18.1.

Run `python scripts/check_hyram_exposure.py --hyram-packages artifacts/native_hyram_packages`.
The replay checks native constant/pulse/linear reduction, independent power
integrals/CDF symmetry, clock splitting, pressure triangle/peak/impulse semantics,
zero and numeric failure limits and source/input identity. These are numerical
verification cases, not measured injury data or qualified receptor vulnerability.
No population count, participation fraction, exposure occurrence or annual
frequency is supplied by a conditional probability.

Primary sources: [Sandia's HyRAM overview and versioned documentation](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/),
[official native probit implementation](https://github.com/sandialabs/hyram/blob/master/src/hyram/qra/probits.py),
[HyRAM6.1 package metadata](https://pypi.org/project/hyram/6.1/),
and [HyRAM6.0 technical reference manual](https://doi.org/10.2172/2563814).
The installed6.1 source, API and GPL notice were inspected. This check does not
audit original human-harm calibration datasets or establish permission to copy
their tables. Coefficients/data remain in the separately installed engine.
