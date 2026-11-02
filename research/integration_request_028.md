# Integration request 028: equipment, carrier and protection evidence

This repository now defines source-only contracts for three receiving fronts.
They are implemented but unexecuted and do not change another repository.

## Native LH2 equipment

Expose stable public producer verification for original compressor stage/train
results and finite heat-exchanger traces. Preserve exact native object and
source provenance, accepted inventory rows, explicit clock and failure prefix.
A future capacity/map level must accept a source-qualified map with units,
speed/flow coordinates, interpolation domain and surge/choke boundaries. Do not
derive a map from the present prescribed ratio/efficiency solver. A flowing
heat-exchanger level needs explicit material ports, pressure loss and spatial
flow ownership rather than reinterpreting the closed two-inventory reference.

Acceptance requires the new `compressor-boundaries` and
`heat-exchanger-boundaries` profiles plus the original equipment regressions,
native package/source audit and installed-artifact replay.

## Carrier conversion

The host API preserves finite rich/lean/NH3/N2/H2 inventories, common caloric
reference, imposed conversion extent and actual withdrawal packets. Receiving
modules should provide source-qualified liquid LOHC thermochemistry, catalyst
kinetics/equilibrium and explicit separation/product ports as distinct levels.
Gas-reference QM9 heats cannot qualify liquid operation. Do not infer a release,
purity, pressure work, heat recovery or industrial capacity from a generated-H2
quantity.

Acceptance requires both carrier profiles, native caloric definition checks and
independent material/reactor evidence appropriate to the selected level.

## Facility protection

Add a public `verify_result(result) -> same original result` hook to the native
monitor owner. It must check the registered evaluation, held-out role, trained
state, source partitions, masks, clock/mode rows and unchanged original caches
without rerunning fitting or inference. The current host bridge must temporarily
use the owner's read-only private guard because that public hook is absent.

Protection reliability, detection coverage, actuator failure and common-cause
dependence require explicit source evidence. A resolved alarm-to-action path
must not receive a second renamed reliability credit. Online control, fault
causation, mechanical stroke and source-to-field coupling remain separate
levels. Acceptance requires the `facility-protection` profile together with the
original monitoring, dynamic equipment, relief and conditional-risk suites.

No listed profile has been executed in this coding wave. Historical results do
not validate these new source bytes or contracts.
