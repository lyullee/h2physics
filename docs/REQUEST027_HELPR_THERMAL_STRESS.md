# Request027 — HELPR nonuniform thermal-stress crack driving

**Receiving project:** `sandialabs/helpr` (or the receiving fracture-mechanics owner
selected by that project). **Current host pin:** HELPR 2.1.0, revision
`ae12d20b6608123af41dd9d5f70db6b6547fece5`, BSD-3-Clause. This request proposes an
additive native capability; it does not ask the host adapter to reimplement a missing
fracture equation.

## Current contract and gap

`h2physics.adapters.radial_failure_history` samples a computed radial wall-temperature
field at an explicitly identified radius and builds the existing typed
`VesselFailureHistory`. Its `predict_failure()` method guards that source binding and
passes the original history to `HelprVesselFailure.predict()`.

The current HELPR adapter constructs its native stress object from pressure difference
and the fixed internal axial flaw geometry. The supplied scalar temperature enters the
caller material law only. A separately calculated `RadialThermoelasticStressHistory`
is not consumed by that SIF/reference-stress route. Therefore the current handoff is
temperature-dependent material evaluation with pressure-driven crack mechanics; it does
not predict crack driving from a radial thermal-stress gradient.

The host has an exact-clock callback seam,
`evaluate_radial_stress_intensity_samples(binding, calculator, ...)`, which supplies each
`RadialThermoelasticVesselSample` to a caller-owned calculator and retains its signed
finite mode-I SIF result at the original loading times. `RadialFailureSeries` is a
diagnostic receipt only. It is not accepted by `VesselFailureHistory` or
`HelprVesselFailure.predict()`, and its SIF values are not inserted into HELPR's native
failure evaluations. A scalar SIF sequence alone also does not provide the independent
reference-stress quantity needed by the existing FAD assessment. A caller must not
relabel these samples as a native vessel-failure prediction or bypass HELPR's
reference-stress calculation with a K-only injection.

## Required exact-clock receiving path

The receiving native owner must add an additive prediction entry point that consumes the
original `VesselFailureHistory` together with the actual `RadialThermoelasticStressHistory`
and its exact-clock source binding. For each accepted sample it must retain a paired
native crack-driving result containing at least the applicable signed SIF and reference
stress, the original `VesselLoading`, total-stress field, flaw geometry/orientation,
material point and native method identity. The receiver, not the host adapter, owns the
nonuniform-field SIF and reference-stress calculations and their applicability evidence.
The exact clock ID and time vector must match; each result must remain linked to its
original sample and native owner. Pressure must not be added again to a total
pressure-plus-thermal field. If an externally supplied SIF callback is accepted, it must
not stand in for the receiver's independent reference-stress calculation. Failure to
admit the stress field or crack method must fail closed without falling back to the
pressure-only route.

Between-sample initiation search also needs a receiver-owned, named reconstruction rule
with bounded support and diagnostics. Exact-time SIF samples must not be interpolated or
treated as a cycle history implicitly. The host will add the native prediction bridge
only after the receiving API can retain both crack-driving quantities and their exact
source records.

## Requested receiving API

Add an optional native stress-field evaluation path without changing the established
pressure-only API. A candidate shape is
`InternalAxialHoopStress.from_stress_history(...)` or an equivalent typed native
result/function, with the following inputs:

- One native/host-agnostic ordered total Cauchy-stress field on the declared cylinder
  radius grid and operation clock, with radial, hoop and axial components in Pa.
- Explicit closed/open axial end condition, cylinder geometry and absolute pressure
  loads, source/material/equation evidence, temperature reference and restraint.
- An explicit flaw surface, location, plane/orientation, dimensions and geometry
  admissibility domain. The current inside axial surface flaw must remain the only
  admitted orientation until other native geometry cases are implemented.
- An explicit field convention: total pressure-plus-thermal stress or thermal
  increment. For the host radial thermoelastic solver's total field, the receiving
  route must replace pressure-derived stress for crack-driving calculations. It must
  never add the pressure field a second time.
- The existing selected FAD/yield/toughness criterion and material point, kept separate
  from the SIF/reference-stress method.

The receiving implementation must provide the applicable SIF and reference-stress
calculation for the nonuniform field and declared flaw. It should retain its native
method/version identity, accepted assumptions, diagnostics and evidence. The host must
not synthesize an undocumented weight function, reinterpret a scalar pressure as stress,
or silently fall back to the pressure-only method when field admission fails.
The host's sample ledger preserves the SIF callback's signed finite values, including
zero; the declared receiving mode/sign convention belongs to the callback evidence.
The host must not replace signed mode-I results with magnitudes.

For initiation search between sampled stress fields, require a named bounded time
reconstruction rule and controls. It must retain the two parent fields, prohibit
extrapolation outside their support, and expose radial/time refinement diagnostics.
Linear interpolation must not be assumed valid for crack-driving force without an
explicit receiving-method contract.

## Host-side Python contract

The source `RadialThermoelasticStressHistory` now offers `require_current()` to detect
post-construction changes to its result arrays, retained pressure/material/profile objects
and their content. `bind_radial_thermoelastic_history_to_vessel` now checks exact heat,
geometry, pressure-load and clock identity, full-wall support, and the total pressure-plus-
thermal convention. A receiver-facing adapter must still bind the specific flaw and its
evidence, preserve any reconstruction/native roots, and pass the actual field into a native
SIF/reference-stress implementation.
`RadialThermoelasticVesselBinding.sample_at(index)` now joins an exact field snapshot with
the original pressure/temperature `VesselLoading` record and guards their source identity,
clock and loads. The HELPR-facing stress-field consumer described below is still absent.

The host adapter should accept the actual
`RadialThermoelasticStressHistory` (or the receiving project's provider-neutral typed
equivalent) and call `require_current()` before and after native evaluation. It must
check exact clock identity/times, cylinder surfaces and query radii, pressure-load
identity, stress material, temperature-profile evidence, axial restraint, flaw
location/orientation and total-versus-increment convention. It should retain the
original thermal and stress histories, selected sample/reconstruction parents, actual
native objects, native result, source hashes and any original failure/root evidence.
Physical identity mismatch is an error; it is not repaired by interpolation or a
different provider.

## Receiving acceptance criteria

1. With zero thermal gradient, the native total-field route reduces to the existing
   pressure-only result within a declared numerical tolerance.
2. A pressure-plus-thermal field matches the independently calculated total response
   without pressure double counting; a thermal-only increment follows its separately
   declared contract.
3. Stress sign, axial restraint/end condition, inside flaw location and orientation are
   admitted and independently checked. Unsupported flaw configurations reject.
4. At least one nonuniform-stress SIF comparison is checked against an independent
   analytical/numerical reference or an applicable measured specimen, with source and
   rights recorded.
5. Radial-grid and temporal-step refinement report SIF/reference-stress and initiation
   time changes; failed convergence remains a rejection.
6. Mismatched clocks, dimensions, material identity, load identity, flaw location,
   evidence, field convention and parent history are rejected without fallback.
7. Original native results, root brackets, evaluation count, partial failures and
   limitation/status fields survive serialization or the receiver's chosen audit API.

These criteria establish only this stress-field fracture interface. They do not by
themselves establish vessel-life prediction, fatigue, plastic collapse, finite-length
effects, crack initiation physics, post-breach dynamics or facility risk.
