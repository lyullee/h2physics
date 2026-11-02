# LH2DT dynamic external-heat ledger and accepted-solve contract

Status: concrete local bridge, negative case and corrected coupled verification available;
request prepared, not sent. Target public baseline:
`b2f276333c1b1793c39f25763703d196d36742ec` (lh2dt_models 0.1.2).

## Observed boundary mismatch

`StratifiedTankDerivative` exposes `lower_ambient_heat_W` and `upper_ambient_heat_W`.
The generic `DynamicNetworkSimulator` reads `ambient_heat_W` with a zero default for its
external heat and cumulative energy ledger. The phase equations include the wall heat,
while the generic boundary ledger omits it. A closed 0.1 s native tank case has about
5.5199724 J actual energy change absent from that ledger.

The local `stratified_node_with_heat_ledger` wraps the native derivative and supplies only
the sum of those external terms. Original phase derivatives, advance and RK combination
remain unchanged. The same case then closes to about 5.84e-12 J. The finite-inventory
tank–pump–heated-pipe–valve case also checks an independent external ledger.

## Requested receiving behavior

1. Expose `ambient_heat_W` on the stratified derivative, or a public dynamic-node external
   heat reader. Both wall terms must reach both the boundary energy and ambient sub-ledger.
   Internal wall/interface heat must continue to cancel and must not be counted as external.
2. Add a clear dynamic-node heat capability contract so an unsupported external heat field
   cannot silently become adiabatic. An explicitly adiabatic component can declare zero.
3. Check the final network conservation/operability verdict at every RK stage before using
   its flows. Trial pressure iterations may explore invalid points; a final stage must not
   advance on an inadmissible map/NPSH point or an unconverged network.
4. Expose an accepted-step callback or iterator carrying `time_s`, accepted state, native
   NetworkSolution and component results. Distinguish intermediate/rejected stage diagnostics.
   Do not require consumers to infer accepted points from five calls per step.
5. Retain optional momentum and NPSH/map evidence. Missing information must remain absent;
   numerical optimizer success is not a substitute for a supplied pump requirement.

## Local Python contracts and exact reproduction

`h2physics.equipment.BoundaryPower`, `ConnectionTransfer` and `EquipmentTolerances` define
units/signs. `Lh2dtEquipmentNetwork` supplies `snapshot`, independent ledgers, a checked
structural native view and actual native component results. No JSON/service layer is used.
The source files are `src/h2physics/adapters/lh2dt_equipment.py` and `equipment.py`.

The continuation `Lh2dtDynamicEquipment` now matches accepted rows to checked native
solution objects by identity, avoiding a fixed RK-call count. It also partitions prescribed
closure times and verifies finite line/vaporizer inventories; see DYNAMIC_INVENTORY.md and
`scripts/check_dynamic_inventory.py`. This local composition buffers stage snapshots for
the current command interval. A direct native accepted-step/streaming callback remains
useful and the receiving heat/stage-admissibility requests above remain applicable.

Run `scripts/check_equipment_network.py`; results, exact inputs, code hashes, three time
steps, property-reference comparison and external ledgers are in
`research/native_equipment_network.md`. The current evidence script asserts the exact
native RK4 call grouping, retaining only accepted points for a nozzle-plane SourceHistory.

Acceptance includes zero-flow closed tank heat; independent lower/upper ambient heating;
phase-internal heat cancellation; simultaneous liquid withdrawal and wall heating;
mass/energy under time-step refinement; rejection of a mathematically closed but negative
NPSH-margin case; and accepted-time callbacks with no RK-stage duplication. Preserve all
native state/flow factories and the existing phase-port model. No additional tank physics
solver or third-party coefficient table is required for this boundary correction.
