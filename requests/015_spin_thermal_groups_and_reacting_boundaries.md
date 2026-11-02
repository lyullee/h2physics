# 015 — Spin thermochemistry, finite thermal groups and reacting boundaries

Status: local receiving specification; no receiving repository has been changed
or contacted. LH2DT baseline is0.1.2 at
`b2f276333c1b1793c39f25763703d196d36742ec`; native Cantera baseline is3.2.0.
The executable host examples are NATIVE_SPIN.md, NATIVE_HEAT_EXCHANGER.md and
REACTIVE_PROCESS.md with their check scripts and research records.

## Spin state and energy capability

LH2DT's native ortho_para.py supplies equilibrium, rate, held-temperature advance
and scalar conversion heat. At the reviewed revision no native tank consumes
the para state. The host therefore exposes a constant-pressure enthalpy reference
calorimeter, without claiming rigid-volume tank pressure or arbitrary liquid-spin EOS.

Receiving capability should expose direct Python functions/objects:

```python
spin_state = SpinThermoState(para_fraction=..., phase=..., reference_id=...)
thermo = provider.evaluate(temperature_k=..., density_kg_m3=..., spin_state=spin_state)
rate = kinetics.evaluate(temperature_k=..., pressure_pa=..., spin_state=spin_state)
```

Names are a proposed contract, not existing native types. Results must retain
the actual provider/state and expose U, H, P, composition derivative and validity
domain on one evidenced material/energy zero. Declare whether the conversion
energy is ΔU or ΔH and how pressure work is included. Rate/catalyst parameters,
temperature dependence, phase scope, source/license and uncertainty must be explicit.
An external power and an internal spin-energy change cannot both count the same heat.

Acceptance evidence:

- Frozen k=0 and zero-gap cases recover the existing native state/energy paths.
- Held T agrees with the exact native conversion solution and signed thermostat H.
- An adiabatic rigid vessel closes total U while a held-pressure calorimeter
  closes total H, including their different pressure-work terms.
- Native composition-dependent derivatives agree with independent bounded EOS
  perturbations; cutoff, phase/domain and reference failures propagate.
- Normal/para fixed-composition limits are compared with applicable independently
  qualified EOS/calorimetry, without a name-only energy-zero conversion.

No scalar heat gap or arbitrary interpolation between pure-fluid names satisfies
the complete evolving-spin capability. A narrower supported subset should declare
that capability explicitly rather than masquerading as the full provider.

## Native composite thermal group and process ports

The host now advances two actual DynamicVaporizer fluid/wall states in one native
DynamicNetworkSimulator using a composite DynamicNodeModel. Native ambient-UA
fields are explicitly the conservative interwall path. The generic network still
requires a representative thermodynamic state even though the group is closed.
This is sufficient for the checked closed level but does not supply process ports.

Receiving native API should provide a thermal group with named independent side
states/bases and heat ports, without requiring one aggregate hydraulic state.
Expose signed internal exchange separately from external ambient/bath heat and
each native fluid-wall cap. A process side should accept its own actual material
ports with per-port composition, phase, pressure basis and native enthalpy reference.
The existing shared nozzle/Darcy machinery remains the flow owner; do not add a
second hydraulic closure to the thermal component.

Require native accepted-step streaming or a callback carrying accepted state
identity/time/step status. Trial/probe evaluation must not be counted as accepted
heat or mutate isolation/protection state. The host currently buffers trials and
matches actual accepted composite identity, which does not offer bounded-memory
streaming for arbitrarily long runs.

Acceptance fixtures:

- Reproduce the closed two-fluid/two-wall analytic, independent native equilibrium,
  heat reversal, side/global U and refinement cases in check_heat_exchanger_integration.py.
- Zero interwall conductance conserves each side's mass and total fluid-plus-wall
  energy independently. Stationary temperatures additionally require initial
  fluid-wall equilibrium or zero fluid-wall conductance. Unequal internal opposite
  heat or incompatible cross-material transfer is rejected.
- For each flowing side close Δmass, Δspecies and Δ(Ufluid+Ewall) against accepted
  port transport plus external heat. Internal exchange must sum to zero globally.
- Retain finite line residual inventory and actual closing/opening command clocks;
  do not infer zero post-isolation heat or a prescribed cooling outlet.
- Qualify pressure loss, spatial/counterflow behavior and manufacturer performance
  only after supplying the corresponding physics/data and observation operator.

## Reactive gas boundaries and native definition identity

CanteraOpenGasVolume now supports frozen and finite-rate gas through one native
physical core. GasBoundaryRate declares native-phase or explicit time-only callback
access. Reactive phases own independent native species/reaction definitions; copy
audits retain exact source/owned hashes, exact thermo coefficients/bounds/reference
pressure and runtime multipliers, plus bounded native coefficient roundtrip.

Cantera3.2's generic clone/YAML reconstruction was observed to change an authored
ConstantCp200–2500K validity range. Reusing Species/Reaction objects left mutable
definition aliases. The host uses native Species/Reaction reconstruction with a
one-time coefficient gate and exact owned-definition guards. A future native
definition identity/version or faithful independent thermochemistry-copy API
could remove repeated serialization for phase-exposing callbacks. It must not
cache through mutation or ignore runtime reaction multipliers/thermo bounds.

Receiving gas/process providers should accept explicit current native state,
boundary identity/time/support and actual mechanism basis. Return separate native
chemical species production and material-boundary species/enthalpy flux. Use
formation-inclusive native U/h exactly once. A fixed reservoir and prescribed
flow do not imply finite upstream supply or solved capacity.

Acceptance fixtures:

- Independent first-order closed/CSTR limits, native formation-energy warming,
  multiplier/definition mutation and factory-alias isolation from
  tests/test_reactive_gas_volume.py.
- Reproduce the actual installed GRI30 steam/oxidative references and plain-native
  trajectory, species/element/U defects and refinement in check_reactive_process.py.
- Preserve reference/domain and original mechanism-byte identity across native
  copies; quantify state/rate differences separately from coefficient roundtrip.
- Any catalytic extension must retain actual surface/coverage/solid state and
  source-qualified mechanism/geometry. Gas-only GRI30 success is not a catalyst
  qualification or an industrial hydrogen-yield benchmark.

## MHC observation prerequisites

The MHCv1.2 loader preserves independent recorders, raw/selected experiment groups,
calendar origins, gauge/reference-volume fields and masks. Before a hydride
compressor fit, resolve gauge atmosphere, MFC reference T/P/composition, each
sensor's physical position, shell/bed averaging, recorder synchronization and
material/geometry/heat-transfer provenance. Selected-cycle copies cannot be an
independent test set against their raw parent. The actual argon/thermal cases
need their own gas identity. No coefficient, missing clock or flow basis should
be invented to force a comparison.

Public rights records and original numeric cases remain in this repository.
Raw observations, external mechanisms and native code remain separately installed
or ignored; neither source availability nor these acceptance fixtures guarantees
facility qualification or a publication outcome.
