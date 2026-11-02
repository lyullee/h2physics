# Native protection, vent, recovery and observation capabilities

Status: local receiving specification. It does not claim that the receiving engine
has implemented these changes. Keep the host's retained negative cases as regression
inputs and review the final reports before choosing the receiving API names.

Target: separately installed MIT
[LH2DT revision b2f276333c1b1793c39f25763703d196d36742ec](https://github.com/lyullee/lh2dt_models/tree/b2f276333c1b1793c39f25763703d196d36742ec).
Native source remains outside the host distribution. Structural Python contracts may
use receiving-native dataclasses and callables without importing this host library.

## Pressure protection: pure trials and committed transitions

The native `PressureReliefValve.evaluate` updates its internal latch on evaluation,
and its constructor requires a native `Valve`. The current host therefore delegates
public `Valve.evaluate` through a thin actual-native subclass to the existing shared
nozzle, and separates trial evaluations from accepted native latch transitions.
This avoids modifying the original source or introducing a second choking law.

Provide a public immutable protection state with open/closed latch and a pure
two-port evaluation taking that state. Return a separate proposed next state and
reason, so rejected solver/network/RK probes cannot change accepted equipment
state. Support public initial-state construction and state restore without access
to protected fields. Accept a structural native two-port flow provider, preserving
actual states, results and source-plane ownership; callers should not need
inheritance solely to satisfy a nominal type check.

Expose event functions and transition semantics for opening and reseat, including
physical upstream absolute pressure, downstream blocking, equality/tolerance policy
and explicit clock. Distinguish a latched-open device from blocked/zero transported
flow. The direct spring-relief model uses physical pressure. Sensor lag/PLC feedback
requires an explicitly separate externally controlled policy.

Acceptance cases:

- An authored device opens at210kPa absolute, stays open at200kPa and reseats at
  180kPa. Equality, initially above-set conditions and reverse blocking are explicit.
- Any permutation/repetition of trial pressures gives the same accepted latch and
  subsequent physical trajectory when accepted transitions are unchanged.
- Localized heat-driven opening and discharge-driven reseat retain distinct pre/post
  event transfer states, finite mass/energy ledgers and refinement evidence.
- Report the first-crossing assumptions. An endpoint sign check alone must not claim
  detection of an arbitrary nonmonotonic excursion within a large integration step.
- A failed native/property/nozzle evaluation retains the failure and cannot promote
  a proposed latch or silently choose a different flow model.

See NATIVE_RELIEF.md and research/native_relief.md for the implemented host boundary,
actual native replay and remaining event/domain limitations.

## Vents: signed heat, public composition and thermal diagnostics

Native `VentStack` evaluates its hydraulic pipe and integrates a downstream-pressure
finite-UA enthalpy path. Native reverse heat has a left-to-right orientation, while
the host's `BoundaryPower` is positive into the actually transported fluid. Expose
both meanings under distinct field names, including the upstream side and units.
Blocked one-way flow must keep momentum/source quantities unavailable as appropriate.

Accept a public hydraulic provider/factory so an explicitly selected existing shared
Darcy closure does not require a per-evaluation stack copy with a replaced pipe.
Retain native results/provider identity and distinguish a selected shared closure
from the original native fixed-iteration baseline. Do not automatically retry with
another friction law after a failed residual.

Return thermal integration diagnostics: configured UA, segment count, native path
enthalpy extrema, any stage/final clipping, accepted refinement/error estimate and
ambient endpoint status. The present host independently reconstructs conductance
with quadrature and retains coarse/native-clamping failures. A clamped ambient
endpoint alone does not prove that finite-UA integration is resolved.

Acceptance cases:

- Forward and explicitly allowed reverse flow have the same physical heat sign for
  equivalent inlet/environment conditions, while oriented native heat remains raw.
- A constant-cp authored gas satisfies the independently derived finite-UA exponential
  limit. Adiabatic and equal-temperature limits preserve the transport state.
- Refinement can qualify a previously rejected coarse thermal calculation without
  changing a gate or rewriting its raw result. Retain both outcomes.
- Final Darcy/gravity pressure loss and flow/viscosity Reynolds numbers close using
  the actual returned flow, rather than a previous iteration's velocity.
- Require actual-provider sound speed and a declared low-Mach limit, including the
  upstream hydraulic section and any explicitly identified downstream same-bore
  estimate. A tiny-loss/high-velocity counterexample must fail even at small pressure
  and density change. Missing acoustic capability cannot certify subsonic flow.
- An enthalpy-only transport ledger is labelled accordingly. Gravity momentum does
  not by itself close kinetic/potential total energy. Expose omitted specific-energy
  diagnostics; require another qualified level when those terms matter.

A downstream PH transport state is not an atmospheric source plane. Velocity,
effective exit area, kinetic enthalpy, choking and dispersion handoff require their
own explicit physical owner. See NATIVE_VENT.md and research/native_vent.md.

## Recovery: distinguish heat paths, net condensation and collected product

The existing native steady `Reliquefier` caps removed heat toward an explicitly
chosen subcritical saturation-quality target. Its finite counterpart retains fluid
mass/internal energy and wall storage through the shared dynamic-vaporizer core.
Expose which heat path each capacity limits: fluid-to-wall and cold-reservoir-to-wall
power are distinct. A cap on the former does not establish a cap on the latter or
an electrical refrigeration rating.

Provide a public absolute-clock cold-side callable through the native recovery node,
retaining actual native component/state/derivatives and accepted power ledgers. The
current host explicitly selects the existing generic native node path when the
specialized recovery factory freezes a boundary temperature. Reject overlapping
boundary ownership or unsupported history support rather than mutating coefficients
from unrelated logger samples.

Acceptance cases:

- Capacity-limited and sufficient-capacity steady cases preserve requested/actual
  duty, outlet PH/quality and the common signed enthalpy ledger.
- Native finite fluid plus wall energy changes equal inlet/outlet enthalpy transport
  plus actual cold-reservoir boundary heat, with isolation and refinement checks.
- Zero hydraulic flow does not imply that stored fluid/wall cooling has stopped.
  Cooling-off and hydraulic isolation are separate supported modes.
- Report incoming liquid, outgoing liquid and net liquid increase independently.
  A sealed vessel's liquid inventory is not collected product without a physical
  withdrawal/separator boundary. Include pressure-change effects in the interpretation.
- Refrigeration electrical power/COP is unavailable unless independently specified
  through a thermodynamically supported cycle or measured equipment map.

See NATIVE_RELIQUEFACTION.md and research/native_reliquefaction.md. No cycle
performance, manufacturer qualification or new refrigeration solver is implied.

## Instruments: unit identity, history and uncertainty meaning

The host `Lh2dtTransmitter` keeps actual native transmitter/state/reading objects,
`TransmitterEvidence` and a quantity/unit/reference/location-qualified `TimeSeries`.
Its interval driver is explicitly left held, with endpoint left-limit predictions.
Initial native state and its clock time are supplied, preserving prehistory rather
than assuming stationarity from the first recorded value.

Expose a native description for variable, unit, pressure/reference basis, physical
location, parameter/calibration revision, response model and quantizer policy. A
state/continuation record should retain that identity and its last accepted time.
Parameter changes require explicit state-transfer/reinitialization policy. Keep
exact held-input response separate from any proposed interpolation of process data.

Acceptance cases:

- Irregular constant-held samples match the analytic first-order limit; splitting
  and continuing a trajectory preserves the final native state.
- Absolute Pa, gauge Pa, differential Pa and unresolved reported Pa are distinct;
  equal numerical units cannot authorize a missing basis or physical location map.
- Missing data and unsupported clocks fail without a hidden hold, interpolation or
  extrapolation. A recorded instrument indication is not silently renamed process
  truth or passed through its own response model again by an automatic adapter.
- Preserve filtered state, pre-saturation indication, saturation flag, resolution
  bound and stated accuracy bound. Native NumPy scalar diagnostics remain usable.
- Span/resolution bounds are not automatically standard deviations, confidence
  intervals or safety probabilities. Noise/covariance and calibration need evidence.

This extends the generic observation responsibility in request004 with concrete
native response/state semantics. See NATIVE_INSTRUMENTATION.md and the executed
research/native_instrumentation.md record, including actual-data incompatibility.
