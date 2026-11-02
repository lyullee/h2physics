# Native stopped-machine and isolated-assembly modes

Status: local explicit mode composition and finite-supply verification available;
request prepared, not sent. Target MIT LH2DT revision
`b2f276333c1b1793c39f25763703d196d36742ec` (0.1.2).

## Concrete current behavior

The mapped pump's speed setter requires a strictly positive speed; a zero-rpm stop is
unsupported. A supplied head map describes running hydraulics, shaft power and NPSH
admissibility. It does not define stopped passive flow, rotor energy, motor losses,
trapped casing inventory or heat during a deadhead/stop transient.

The host `Lh2dtModeSwitch` selects an explicitly named native component and power reader.
The finite supply assembly selects the actual mapped pump in `running` mode and an actual
closed shared-kernel valve in `isolated` mode. Both actual results remain available; native
failure never selects another mode. This is an ideal simultaneous stop/isolation limit.
It does not claim that stopping an unisolated pump closes a flow path.

`scripts/check_finite_supply.py` connects the finite phase-resolved tank, pump assembly,
stored line, restriction and stored vaporizer. The ideal switch occurs at 0.037 s, outlet
closure at 0.073 s. The downstream inventories continue discharging between those times.
The public builder accepts actual native objects/states/factories and explicit power readers.
See FINITE_SUPPLY.md and `research/native_finite_supply.md` for inputs, checks and failures.

## Requested receiving API

1. Expose declared machine modes separately from commanded speed. Distinguish running,
   coastdown, stopped-but-open and isolated behavior. Do not silently assign passive
   hydraulic resistance, reverse flow, valve leakage or loss power when inputs are absent.
2. Keep a strictly positive map envelope for the running model; make a zero-speed command
   either an explicit supported mode transition or a clear unsupported-capability result.
   A failed map/NPSH point must remain a failed operating point, without automatic isolation.
3. For a resolved shutdown, require caller-supplied rotor inertia/loss torque, motor power,
   fluid/casing inventory and thermal paths as applicable. Expose rotor/fluid/solid energy
   terms and their external work/heat boundaries. Mark ideal zero-storage modes separately.
4. Preserve actual native component results, operating mode, mode-transition clock and
   missing momentum/operability diagnostics. Keep per-port identity and enthalpy reference.
5. Support phase-port and finite-device network composition through native Python objects;
   no serialization/service layer is required. Keep the common nozzle delegated rather
   than adding an equivalent discharge implementation.

## Host contracts and acceptance

The implemented boundary is `Lh2dtEquipmentMode(component, power_reader)` with
`Lh2dtModeSwitch(bridge, modes, mode_id=...)`. Each mode shares the declared property
instance and returns `EquipmentModeEvaluation(native, mode_id, boundary_power)`.
`assemble_lh2dt_supply` demonstrates a concrete receiving topology. These interfaces
can delegate a new receiving mode without replacing the inventory integrator.

Acceptance requires explicit mode selection, zero-speed behavior, unknown-mode rejection,
retained map/NPSH failures, no hidden alternate component, declared passive/reverse-flow
behavior, and mass/energy under command/time-step refinement. A resolved rotor case must
close rotor plus fluid/casing energy against shaft/electrical power, transported enthalpy
and ambient heat. An ideal isolated case must identify its omitted storage/loss terms.
No manufacturer curve, stopped-flow coefficient or apparatus parameter is supplied here.
