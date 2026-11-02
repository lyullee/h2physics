# Finite incident-heat target

Status: **implemented_unverified**. The variable-capacity extension and its
synthetic analytic contract are deferred to the cluster campaign; this source
change has not been run as a model calculation or scientific test.

`h2physics.adapters.thermal_target` turns an explicitly supplied incident heat
flux history into the temperature of one uniform finite-capacity target. It is
a boundary-response composition, not a fire, heat-transfer-correlation, damage
or injury model. The existing pool-fire/native radiation owner remains
responsible for flame geometry, view factor and incident flux.

## Python API

- `IncidentHeatHistory` contains increasing SI time edges and one nonnegative
  incident flux per interval. Clock, frame, source, boundary, evidence, origin
  and the original source owner are mandatory.
- `LumpedThermalTarget` declares exposed area, total heat capacity, initial and
  admitted temperature range, absorptivity, emissivity, a held convection
  coefficient and held ambient/radiant-surroundings temperatures. All material,
  geometry and coefficient evidence stays caller-owned. Total heat capacity may
  be a positive constant in J/K or a caller-supplied `C(T)` callback in J/K;
  the callback is evaluated inside the declared target-temperature domain.
  Callable capacity is checked at both domain endpoints and the initial
  temperature, then at adaptive ODE and enthalpy-quadrature evaluation points.
- `incident_history_from_pool_fire(...)` extracts exact active/zero-tail
  intervals from an original `PoolFireTrace` receptor. It keeps that trace as
  `source_owner`; it requires the trace's current one-use native receipt before
  and after extraction, and later target-result checks revalidate that trace. It
  does not replay or approximate the native fire calculation.
- `incident_history_from_exposure(...)` accepts an existing left-held
  `ExposureHistory` only when it represents valid incident radiant flux in W/m².
  It carries the original clock, receptor frame, source/basis identities, values
  and origin unchanged. It rejects absorbed-flux series, pressure histories,
  linearly interpolated samples and missing intervals rather than changing their
  meaning or interpolation. An input still has to satisfy its own representation
  contract first: a left-held series has one value per interval, while a linear
  series has one value per edge. The deferred handoff contract supplies a
  correctly shaped linear history before checking that this adapter rejects its
  interpolation semantics.
- `run_thermal_target(...)` uses SciPy `solve_ivp` on each flux interval and
  returns the actual native segment objects plus temperature and cumulative
  SI-energy arrays. `ThermalTargetError` retains completed native segments.

For a constant or temperature-dependent total heat capacity `C(T)`, the balance is

\[
C(T)\dot T=A\alpha q''_{inc}-Ah(T-T_a)
-A\epsilon\sigma(T^4-T_r^4).
\]

The returned stored-energy change is `integral(T0 to T, C(theta) dtheta)`;
the residual compares it with absorbed incident energy less signed convective
and radiative export. For a constant capacity this reduces to `C(T-T0)`.
Negative export represents heat entering from a warmer environment and is
retained rather than clipped. A variable-capacity callback must be deterministic,
positive throughout the admitted temperature range, and supported by the
caller-retained material evidence.
The target receipt binds the callback object and its ordinary function definition,
but cannot observe mutable values hidden in closure cells or external globals; the
caller must keep such state fixed and the callback deterministic for the whole run.

## Applicability boundaries

The target is spatially uniform. It has no through-thickness gradient, internal
heat generation, phase change, ablation, contact resistance, temperature-dependent
optical/external-transfer coefficients, structural capacity, ignition, failure
probability, biological dose or injury conversion. The total heat capacity may
vary with temperature; the callback does not supply material mass, infer a
specific-heat law, or qualify that law. Held external coefficients and optical
properties require independent evidence for every use. Temperatures outside the
declared material domain are rejected with native integration context retained.

The authored example uses synthetic numbers only. It is an energy-accounting
fixture, not a recommended hydrogen-fire design case.

## Deferred checks

`validation.cases.thermal_target` defines seven metadata-only cases under the
`thermal-target` profile: finite pulse/cooldown and energy closure, lossless
constant- and temperature-dependent-capacity analytic responses, interval-refinement
invariance and explicit temperature-domain rejection, exact incident-exposure
handoff, and source-result checks. The variable-capacity case compares the native
ODE against the independently rearranged enthalpy integral for a synthetic linear
`C(T)`. These cases are deferred; the future cluster profile needs SciPy only.

`ThermalTargetTrace.require_current()` checks retained incident-source freshness,
history/target/tolerance content, native integration arrays and reported energy
ledgers. Source/configuration checks also apply during integration and before
return. They prevent changed retained output from being consumed as the original
response; they do not establish experimental validation. The trace can only be
constructed with a one-use token issued after the native integration completes,
so `dataclasses.replace()` cannot establish a new integrity baseline for edited
summary values. The deferred pulse case records clone rejection. Bytes-backed
output arrays may refuse write-enabling outright; the deferred contract accepts
that stronger immutability behavior and otherwise requires stale-ledger rejection.
The case remains unexecuted.

If target temperature crosses its declared domain during an ODE right-hand-side
evaluation, the capacity callback is not evaluated outside that domain. SciPy
does not return a partial `OdeResult` when the right-hand side raises, so
`ThermalTargetError` retains the cause and only previously completed interval
segments; it cannot include the in-progress segment's native object. A failure in
the later stored-enthalpy quadrature retains the completed integration segments.
