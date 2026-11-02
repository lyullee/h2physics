# Radial thermal field to vessel failure history

`h2physics.adapters.bind_radial_thermal_history_to_vessel` connects an actual
`RadialHeatResult` to the existing sampled cylinder-pressure and HELPR vessel
failure-history interfaces. It does not add a heat solver, stress solver, fracture
criterion, failure probability or vessel-life model.

The caller supplies:

- `CylinderStressSamples` containing the admitted absolute-pressure loads,
- a `VesselFailureContext` on the same clock and with its wall-temperature evidence
  set to the thermal result's `evidence_id`,
- a `RadialHeatResult` with exactly matching output times and cylinder surfaces,
- an explicit `temperature_radius_m` for the mechanically represented region,
- evidence for mapping that physical radius to the wall/flaw region, plus phase,
  pressure-source and reconstruction identities.

For each time sample, the adapter linearly samples radius across the retained inner
surface temperature, radial cell-center temperatures and outer surface temperature.
This radial mapping assumption is identified and the sampled position is returned.
Time values are matched exactly; no temporal interpolation or extrapolation is done.
The immutable result retains both source objects and the original typed
`CylinderVesselHistoryBinding`. Passing the result's `history` to the existing
`HelprVesselFailure.predict` API delegates mechanical assessment to the pinned
optional HELPR implementation and existing caller-supplied temperature-dependent
material law.

**Scope of the current bridge:** it maps the radial heat solution to one scalar
wall temperature per time sample. `HelprVesselFailure` uses that temperature
through the supplied material law, while its current native stress-intensity and
reference-stress calls are constructed from the pressure difference and native
flaw geometry. The bridge does not pass a `RadialThermoelasticStressHistory` into
HELPR. Thus it does not include the computed radial-gradient stress contribution
in crack driving force; it is not yet a coupled thermal-stress failure calculation.
For a guarded one-call handoff, use
`binding.predict_failure(helpr_owner, maximum_reconstruction_step_s=...)`. It checks
the binding immediately before and after the original `HelprVesselFailure.predict`
call, returns that same typed `VesselFailurePrediction`, and never reconstructs or
replaces its history. `RadialThermalVesselFailureError` retains this radial binding,
original cause and stage (`pre_evaluation_integrity`, `helpr_evaluation`,
`invalid_prediction` or `post_evaluation_integrity`). If the binding changes after a
successful native call, the prediction is retained on the error instead of discarded.

The returned binding exposes `require_current()`. The `history` and
`wall_temperature_k` accessors call it before exposing mapped results. It checks
that the retained pressure, thermal and vessel-history objects, service context,
pressure loads and loading samples are still the original objects, recomputes the
radial mapping relationship, and fingerprints the retained arrays, geometry,
fluid/reference/spin basis, H2 service fraction,
origin, evidence identities, mapped samples and declared material/boundary callbacks.
The exact-sample route rejects reconstructed or native loading snapshots. Replacing a
nested result, adding a native trace, or changing retained data invalidates later use.
This guard protects Python result provenance; it does not certify callback closure
state or physical model validity.

The chosen radius does not automatically represent a crack tip, weld, heat-affected
zone, or governing location. The caller must establish that mapping from actual
geometry and evidence. The radial heat model remains axisymmetric, constant-property,
small-scope solid conduction; it is not a qualified vessel temperature field. HELPR
initiation is not fatigue life, breach size, rupture dynamics or facility consequence.
No engineering acceptance conclusion follows from this bridge.

The host API now also provides
`bind_radial_thermoelastic_history_to_vessel(vessel_binding, thermomechanical_history, *,
field_convention, field_convention_evidence_id)`. It requires the actual paired heat/stress
history, the exact heat result and pressure geometry/load objects already retained by the
vessel binding, identical clock samples and a full-wall stress radius grid. The only
admitted convention is `total_pressure_plus_thermal`: the radial thermoelastic solve already
uses pressure tractions and thermal strain, so the field must replace a pressure-only stress
input in any future crack-driving calculation. This host binding preserves provenance; it
fingerprints the convention/evidence declaration against later mutation, and does not
provide an SIF/reference-stress solution. The current HELPR adapter remains pressure-driven.

For an exact-clock paired record, call `thermoelastic_binding.sample_at(index)`. The
returned `RadialThermoelasticVesselSample` carries the original `VesselLoading` and typed
stress field together, and `require_current()` checks their time, clock, absolute pressure,
mapped temperature and source identities. An equal-valued replacement loading is rejected.
This makes handoff to a future receiver easier to audit; it still does not evaluate crack
driving force or reconstruct intermediate times.

`evaluate_radial_stress_intensity_samples(binding, calculator, calculation_evidence_id=...)`
is the local evaluation seam for a receiving crack/SIF calculator. It passes each exact
`RadialThermoelasticVesselSample` once, retains the returned finite signed Pa·sqrt(m) values
including zero, and reports the largest signed sampled value and its original index without
absolute-value coercion. A pressure-only HELPR owner
is not accepted as the calculator. The callback must implement the applicable flaw geometry,
SIF/reference-stress law and evidence; the host wrapper does not supply or qualify that law.
This is not an initiation-time interpolation, fatigue solution or failure prediction. It
does not replace Request027's required native HELPR total-stress route, independent SIF
comparison, refinement evidence or accepted crack-growth history.
The returned `RadialFailureSeries.require_current()` also validates its exact finite
sample-time coverage and recomputes the maximum/index summary from its retained values;
changing only the published maximum invalidates the receipt. Directly constructed
series cannot use a boolean in place of the maximum sample index.

`series.first_sample_at_or_above(threshold_pa_sqrt_m, threshold_evidence_id=...)`
returns an evidence-bound `SampledSifThresholdHit` for the first exact retained
sample meeting a caller-provided positive threshold, or `None` if none of the
samples meet it. It preserves the original sample index/time/value and checks the
underlying series for freshness. No interpolation is performed, and this sample
query alone does not establish initiation time, crack growth or failure; threshold
applicability remains caller-owned evidence.

`series.sampled_window(start_time_s, end_time_s)` returns a `RadialFailureWindow`
only when both inclusive bounds are exact points on the original thermal solver
clock. The view reports its unchanged signed values, extrema, source index and
sampled duration. Off-grid endpoints, reversed bounds and post-selection range
edits are rejected. No stress or SIF interpolation, threshold criterion or material
failure rule is introduced; the duration is simply the distance between retained
endpoint samples.

## Receiving-module extension request

[Request027](REQUEST027_HELPR_THERMAL_STRESS.md) specifies the receiving HELPR API,
host-side typed binding, field convention and independent acceptance criteria. Until
that module and evidence exist, the current bridge supports temperature-dependent
material evaluation with pressure-driven crack mechanics only. The new host binding
preserves the total pressure-plus-thermal stress field, but no current crack-driving
calculation consumes it. Thermally driven crack initiation, fatigue life and vessel
failure therefore remain unestablished.

## Deferred evidence

`radial-wall-temperature-vessel-failure-binding` exercises computed radial profile
sampling, retained clocks/pressure/thermal inputs, exact surface matching, evidence
binding, post-return mapping mutation rejection and invalid-radius rejection on Nurion.
It does not test thermoelastic-stress transfer into HELPR. Its example parameters are synthetic
integration diagnostics, not material properties or vessel validation. The case has
not been executed. It also routes the guarded typed history through the actual pinned
HELPR owner and checks that the returned prediction retains the same history object.
Its deferred contract also checks the total-stress binding, pressure boundary tractions,
exact geometry/load identity, full-wall field support and rejection of a thermal-increment
label or changed convention evidence. This still does not test transfer into HELPR or a
thermal-stress SIF.

The binding fingerprint for callable heat-boundary and material-property inputs records
Python code objects, recursively visible defaults and closure contents, bound receiver
state, and ordinary callable-instance attributes/slots. This detects common
post-binding edits to callback configuration without invoking the callback again.
The deferred contract `radial-vessel-callback-integrity-signature` covers keyword-only
defaults, nested closure mutation, bound-method stability/receiver mutation and code
replacement. It does not inspect arbitrary external services or global state outside
the callback's explicit configuration; callers should keep those dependencies stable
for the lifetime of a retained binding.
