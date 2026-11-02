# Request 030 — rotating equipment, flowing heat and recovery contracts

The host has source-only integration contracts. Receiving repositories remain
unchanged and all new validation profiles are unexecuted.

## Pumps and compressors

Publish original native operating-point results with explicit speed, inlet
absolute state, throughput, pressure ratio/rise, efficiency, shaft power and
physical-validity flags. Admit evidence-bearing map lines with stated corrected
coordinate, pressure and flow bases. Extrapolation, missing NPSH, reverse flow
and failed native points must remain failures. Rotor/motor/cavitation/surge
dynamics require separate models and data.

The source-only compressor-map layer now rejects operating points below its
caller-supplied lower-flow envelope. A distinct `CompressorAntiSurgeGuard` adds
an explicit static margin check when a source specifically identifies a surge
boundary: it interpolates only across supplied corrected-speed points, requires
the requested flow excess, retains failed native points and rejects extrapolation.
It does not estimate a surge line, add a recycle/controller law or model rotating
stall dynamics. Its deferred `compressor-anti-surge-boundary-support` and
`compressor-anti-surge-margin-native-replay` cases are unexecuted; the latter
requires genuine native mapped traces and separately reviewed surge/margin data.

Acceptance requires `pump-operation`, `compressor-map`, original native
equipment/property suites and independent manufacturer/apparatus observations.

## Flowing heat exchangers

Expose two original process `ConnectionTransfer` objects and a finite wall/fluid
hold-up witness on the same energy reference. Declared pressure loss is evidence,
not a correlation. A closed-side trace is not a flowing integrator. Spatial
counterflow, leakage, phase maldistribution and measured performance remain
separate levels.

The host repository now has two deliberately distinct contracts. The steady
`FlowingHeatExchangerAdmission` binds original process transfers to a point in a
finite native trace; this point is only a hold-up witness. The separate
`Lh2dtTransientFlowingExchanger` advances both fluid/wall inventories through
the native integrator with explicit stage-wise inlet/outlet streams, accepted
time points, and cumulative mass/energy ledgers. It does not infer pressure-loss
laws or spatial counterflow. Their focused deferred cases are
`flowing-heat-exchanger` and `native-transient-flowing-exchanger-holdup`; neither
has been scientifically executed in this campaign.

Acceptance requires `flowing-heat-exchanger`, original exchanger/equipment
suites and source-qualified process data.

## Reliquefier product boundaries

Expose feed, liquid product, return and vent identities, original saturation
state/duty, collected mass and transported enthalpy, plus finite cold-budget
debit. Do not infer a separator, product purity, cycle COP, controller or
depletion root.

Acceptance requires `reliquefier-product`, original steady/dynamic recovery
suites and independent recovery-apparatus evidence.
