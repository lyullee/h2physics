# DynamicLH2PoolX property, event-clock and source contracts

Status: actionable request following the implemented host pool/source API.
Target: `lyullee/DynamicLH2PoolX`. No receiving repository was edited or messaged.

## Checked receiving state and reproduced failures

Version 0.2.0rc2 / revision `6a700e8e183039bbb81803bacc416f6c9117ed71` is MIT.
Its GitHub and PyPI Python module bytes match SHA-256
`bac236e164f144a4269615a83fc6e3d994fa02ab06b853a43e386cfc2bbc8fd4`
(sorted relative paths plus bytes). `dynamic_pool.py` hard-codes CoolProp normal
Hydrogen. It cannot accept a para-Hydrogen facility boundary through a name conversion.

The native loop's `next_change > time + 1e-12` test and strict `DeclaredInflow.rate_at`
comparison can disagree just before a supply change. The authored 0.025 kg/s, 1.13 s
input with host clock origin 200 s supplies 0.00025 kg too much in the retained coarse
case, despite an internal final mass residual about 6.94e-18 kg. A separately integrated
input history detects it. Both absolute-origin subtraction and accumulated stepping
can expose this class of failure.

The native result also lacks restartable radial state, interval-resolved emission area
and independent substrate heat accounting. Its reported front can be zero while liquid
and vapor generation persist. `substrate_heat_flux_W_m2` is constructed using an interval
mean and endpoint wet area; it must not be mistaken for an instantaneous surface flux.

## Host implementation available now

- `h2physics.adapters.pool.DeclaredGroundInflow`: actual native step object, saturated
  liquid state/basis, finite absolute window, source/clock/frame, origin and evidence.
- `NativeDynamicPool`: actual injected runner/config, independent step-input and mass
  checks, phase-property guards and actual result retention. Normal Hydrogen only.
- `PoolTolerances.event_clock_roundoff_s`: default zero. An explicit bounded structural
  input proxy delegates the actual native rate function at known knots and records every
  correction. The positive profile chooses 1e-10 s; the largest finest-run correction
  is 4.44e-15 s. No native equation or global function is patched.
- `NativePoolRun.evaporation_source()` and `h2physics.sources.IntervalMassSource`:
  cumulative evaporation differences, read-only edges/masses, declared constant-mean
  representation, saturation state and finite-window conservative rebinning.

The receiving library need not import h2physics. Equivalent Python Protocols/dataclasses
are sufficient. Retain native objects and ndarray access rather than requiring JSON.

## Requested native changes

1. Unify time comparison, event location and one-sided boundary evaluation. Reach each
   representable input knot exactly or apply an explicit recorded time-roundoff policy.
   Never skip a nearby event while continuing to use its old rate for a full step.
   Reject event spacing below the chosen numerical clock resolution.
2. Accept an explicit fluid/spin/reference property provider. It must supply pressure/
   quality saturation temperature, density, viscosity and liquid/vapor enthalpies with
   identity metadata. Preserve the existing normal-Hydrogen default as a versioned
   reproduction route; allow qualified para-Hydrogen explicitly. Reject reference or
   phase mismatches without renaming fluids or changing a global property state.
3. Return immutable accepted radial snapshots/checkpoints with cell faces/areas, depth,
   radial momentum, local wet-contact age, cumulative mass ledgers, property basis,
   configuration and clock. Restart from that state, not an invented distribution of a
   scalar initial mass. Keep reporting/dry thresholds separate from physical inventory.
4. Expose source intervals as actual integrated vapor mass and clearly identified area/
   spatial distributions. Return per-cell/annulus integrated emission or a stated
   area-time quadrature so a downstream dispersion consumer can preserve both mass and
   source geometry. Endpoint observation radius is not an interval footprint.
5. Add independently accumulated substrate heat supplied to the active evaporating
   liquid, latent energy removed and unused thermal capacity. State the isothermal
   constant-pressure assumptions and whether mechanical/potential energy is omitted.
   A derived vapor-mass-times-latent number alone is not independent energy evidence.
6. Retain numerical adjustments, domain escape, unresolved residual liquid, accepted
   step/event diagnostics and distinct interval/last-step rates. Do not silently clip
   the final liquid to declare depletion. Preserve current warning/status semantics
   or provide a versioned migration.

## Acceptance cases

1. Run `scripts/check_pool_integration.py` and `tests/test_pool_sources.py` from this host.
   Preserve its fixed bounds and retained failed coarse cases. Use both 0 and 200 s
   origins with 1.13 s and 0.17 s stops, including nearly coincident output knots.
   Independent input integration must agree without a whole extra supply step.
2. After the native time fix, the exact new revision must pass the original independent
   gate with the host clock budget zero. Compare original/corrected native results and
   retain the 0.00025 kg failure as a regression record; do not relax mass tolerances.
3. Exercise normal and para hydrogen against the explicit provider at multiple saturation
   pressures. Check density, temperature, viscosity and latent difference and reject
   incompatible property references. Include a para-Hydrogen facility-to-pool case only
   after ground input/state is independently declared; no automatic rainout fraction.
4. Preserve positive evaporation when the reported front is zero. Source interval sums
   must match cumulative evaporation, and regrouping bins must preserve total mass.
   Reject treating input isolation as vapor-source isolation.
5. Compare checkpoint restart with an unsplit native calculation across input changes,
   contact-age memory and near dryout. Report numerical and source-output refinement
   separately; fixed output spacing must not imply a known instantaneous flux.
6. Check liquid/evaporation/escape/adjustment and independent heat ledgers at each accepted
   step. Domain truncation, excess adjustment, mismatched phases and unresolved event
   spacing must fail with preserved native diagnostics.
7. Record all new versions, settings, module hashes, positive/negative results and
   applicability limits. Source observations and their rights need a separate review;
   the current host verification is synthetic and is not independent pool validation.
