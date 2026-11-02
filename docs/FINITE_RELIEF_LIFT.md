# Finite relief lift and phase-selective pickup

`h2physics.adapters.relief_lift` adds an accepted-sample lift state around the
existing native pressure-relief thresholds and the shared homogeneous nozzle.
It does not replace the native relief, tank equations, property provider or
nozzle search.

## Ownership

- `Lh2dtReliefProtection` retains the actual native set/reseat pressures, native
  origin/current objects and opening identity.
- `HomogeneousIsentropicNozzle` retains all flow, choking, phase-equilibrium and
  energy-split calculations.
- `PhasePickupOwner` is supplied by the tank/phase model. It must return the exact
  accepted native tank object, an explicit admitted phase, selectable mass and a
  `ThermoState` on the same pressure/property basis.
- `ReliefLiftLaw` contains caller-supplied opening/closing travel rates, a closed
  leakage area fraction and maximum accepted clock step. Its evidence identifier
  prevents those numbers from looking like built-in vendor data.

`FiniteLiftRelief.initialize` creates the first owner-issued result.
`advance` applies set/reseat hysteresis at the new accepted pressure sample and
moves lift linearly by the bounded declared rate. The effective fraction is

`closed_leakage + (1 - closed_leakage) * lift`.

The returned nozzle result is an endpoint rate. The fields ending in
`_if_held` are only endpoint-rate-times-step diagnostics and are deliberately not
accepted tank inventory integration. A caller must use a separate native tank
integrator and adequate quadrature, then provide its next actual state.

## Guards

- pressure crossings hidden within a time step are not found;
- a step outside the declared clock support is rejected;
- pressure, energy-reference and phase-owner bases must agree;
- a copied, edited or non-owner-issued previous result is rejected;
- the selected phase must have enough declared mass for even the endpoint-held
  diagnostic, otherwise the step is rejected rather than clipped;
- reverse flow remains the shared nozzle's explicit no-forward-pressure result.

## Limits

The travel and leakage deferred cases can construct an authored fixture around
the actual reviewed LH2DT protection, shared nozzle and native property-state
objects. Fixture pressures, inventory, lift coefficients and downstream
conditions are synthetic contract inputs, not equipment data. No host relief
substitute is used. The failure-prefix case uses the same native tank and
protection owners, accepts one valid interval, then supplies an invalid ambient
temperature on the next interval so the native tank rejects its physical
boundary input. The raised error must retain the original cause and exactly the
accepted prefix. This is an injected input-guard path, not a spontaneous EOS or
equipment failure. Accepted-edge withdrawal cases also use owner-issued native
endpoints and synthetic inventory closure; the invalid-edge case separates two
real accepted endpoints to exercise the nonadjacency guard.

This is not valve sizing, spring/disk mechanics, chatter, two-way fluid-structure
interaction, certified leakage classification or a rated capacity model. Linear
travel rates and leakage fraction require equipment-specific evidence. Vapor,
liquid or bulk pickup is only as valid as the injected phase owner. No default
phase is inferred. Independent cryogenic relief measurements and device maps are
still required.

The implementation and deferred cases are original project code under Apache-2.0.
They copy no vendor coefficient table or supplied-document content. The native
LH2DT package and property/nozzle dependencies retain their separately reviewed
licenses and revisions.


## 2026-11-01 native finite-relief execution

All ten finite-relief-lift cases passed across the executed local runs. Nine
passed initially; the failure-prefix fixture incorrectly required one legacy
ambient-temperature error spelling. It now checks the ValueError type and the
ambient/temperature/positive meaning while retaining every accepted-prefix,
trial, state and protection-history assertion. Its replay passed with one
accepted interval, two native trials and final accepted time 5.005 s.

The installed LH2DT revision is b2f276333c1b1793c39f25763703d196d36742ec;
reviewed native source SHA-256 5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61
matched the expected pin. Native protection and the actual CoolProp-backed
shared nozzle executed: peak authored travel 0.4, leakage fraction 1e-4,
accepted withdrawal 1.882338474e-6 kg and 7.451657758 J. The mass balance
residual was zero; finite-source enthalpy projection diagnostic was about
-0.0008447 J. These are admitted component results with authored stock/pressure
samples. The failure-prefix branch also advances the real native tank over a
closed 5 ms interval before rejecting the next invalid ambient input.
No certified relief capacity, chatter, device coefficient or measured leakage
classification follows. Existing independent cryogenic relief-data gaps remain.
