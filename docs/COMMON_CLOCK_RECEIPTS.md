# Common-clock cross-model receipts

## Facility operation

`adapters.bind_operational_scenario()` retains one `Lh2dtSupplyAssembly` and one accepted `DynamicEquipmentRun`, then optionally binds actuator traces, finite-tank relief traces, relief protection records, and prescribed protected-equipment replays. All included items must use the declared clock and remain within the exact dynamic-run window. Declared supply inventory node IDs must occur in the initial and each accepted dynamic inventory. A protected replay must retain the identical `DynamicEquipmentRun` object used by the receipt, so its alarm-scheduled action and accepted native transition remain connected to the same operation result.

`require_current()` seals the receipt declarations and retained dynamic inventory,
transfer and utility ledgers. A later change to the scenario identity, evidence map,
accepted inventories or native transfer snapshot rejects the receipt; restoring
mutable content is required before the retained objects can be reused.
It also fingerprints the supply graph's boundary/junction identities, link
endpoints and component owners, power-reader assignments, inventory readers and
active pump mode. Adding or relinking a native component after receipt issuance
invalidates the receipt. This checks graph identity only; it does not re-solve the
network or prove caller evidence describes a physical route.

The caller provides `binding_evidence_ids` for cross-owner relationships that the native records do not encode. At minimum the supply-to-run binding key is `supply_to_dynamic`; included actuator, relief, relief-protection and protected-run results need their corresponding keyed entries, as described on `OperationalScenarioReceipt`. These values are caller attestations and do not automatically prove flow routing. The receipt runs no solver, introduces no pressure/flow law, and does not localize an event between native output samples. Utility-window coupling and route verification remain separate work.

Actuator, relief and protection components are optional to support different facility configurations. A relief-protection record requires its original relief trace to be included. A protected run is a separate prescribed alarm-to-actuator replay and must point to the receipt's exact accepted dynamic run. Neither form represents autonomous SIS or relief dynamics. The receipt preserves included original objects and their current-content checks where the source API provides them.

An optional `ThermalUtilityLedger` can also be retained. Its profiles must use the exact scenario clock and full accepted run window, and `binding_evidence_ids` must include `utility_to_dynamic`. This closes only an evidence-backed time-window join. It does not prove which native equipment generated the heat, inject utility duty into the dynamic run, or establish a physical utility route.

## Electrolysis to fuel-cell hydrogen handoff

`adapters.bind_electrolysis_to_fuel_cell()` compares an already admitted `PVElectrolysisTrace` with an already admitted `FuelCellTrace`. It requires one evidence clock, an explicit producer source port matching the producer record, an explicit sink port matching the fuel-cell H2 inlet, a producer end no later than the first fuel-cell command, and identical H2 aliases, elemental formula, charge and molar-mass basis. For this single-batch form the producer H2 receiver starts empty; the delivered amount is net production less a caller-declared nonnegative transfer loss and must match the sink's initial H2 stock within an explicit molar tolerance.

The receipt reports produced, transferred, consumed and remaining H2 moles and requires transfer and state-conditioning evidence identifiers. A deferred `electrolysis-fuel-cell-single-batch-handoff` case now builds actual original producer and consumer traces, checks exact source/sink/species identity and common-clock ordering, and rejects a transfer loss inconsistent with the sink's initial stock. It closes only a molar inventory handoff. It does not reconcile pressure, phase, temperature, enthalpy, intermediate storage dynamics, electrical power or thermal utility across the two models, and it does not couple their solvers. The case is registered for the Nurion plan but has not been executed.

## Fuel-cell reaction and thermal replay

`adapters.bind_electrochemical_operation()` admits a completed `FuelCellTrace` against a completed `ThermalStackTrace` from the same `FiniteThermalStack`. It requires one shared `HydrogenStack`, matching thermal boundary and reaction-energy reference, aligned held command windows/current/Faradaic efficiency, and successful native thermal trajectories. The caller declares the shared clock, evidence identity, near-isothermal temperature tolerance and whole-operation heat tolerance.

`ThermalStackTrace` can only be issued by `FiniteThermalStack.run()`. It retains the exact issuing owner and a fingerprint over the accepted stages, native solver arrays, boundary and solver settings. Direct construction, dataclass replacement, mutation, or pairing it with a different thermal owner is rejected before the cross-model receipt is created.

This is a post-run compatibility check: each fuel-cell step is assumed isothermal within the declared tolerance while the thermal model resolves temperature evolution. It does not feed that temperature back into polarization, resolve reactant depletion events on the thermal clock, or prove device/coolant qualification. The registered authored compatibility case is deferred.
