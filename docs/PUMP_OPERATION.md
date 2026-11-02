# Finite-speed pump operation

`FiniteSpeedPump` adds a declared shaft-speed clock and an evidence-bearing
normalized map around one original native mapped pump. The native object remains
the pressure, mass-flow, outlet-enthalpy, shaft-power and NPSH owner.

`NormalizedPumpMap` contains a reference speed, flow, pressure rise and NPSH plus
dimensionless curve points. Interpolation is limited to the supplied flow range.
Affinity scaling is used only as an independent admission check on a retained
native result; it never supplies a network flow or pressure solution.

`PumpSpeedActuator` has explicit initial speed and separate finite ramp-up/down
rates. `PumpSpeedCommand` accepts only `operate`, `hold` or `stop`; unknown mode
labels are rejected, and `stop` requires zero target speed. Command intervals are
contiguous on one named clock and every
boundary must be sampled. Each elapsed interval uses the command active at its
left edge, so a command change affects speed only after its exact start-time
sample. A command active at a boundary is retained on that boundary point without
applying its ramp retroactively. Zero speed is rejected because the existing native
pump has no stopped-flow, bypass or casing-storage physics; a separately declared
component/mode is required.

Every point retains the original native result. `PumpOperationTrace` can only be
issued by `FiniteSpeedPump.run()` after native evaluations; direct construction
and dataclass replacement are rejected. Capacity admission requires the
native pressure rise and required NPSH to match the caller's evidence map within
its declared tolerance, the native operating point to be physically valid, and
the native NPSH margin to be nonnegative. Unqualified authored maps may be used
only when predictive qualification is not requested.

This source-only level does not model torque, rotor inertia, motor current,
deadhead heat, casing inventory, cavitation growth, two-phase ingestion, controls,
check valves or a refuelling protocol. Real manufacturer maps and independent
cryogenic-pump observations remain required. The `pump-operation` Nurion profile
and original native equipment/property suites have not been executed for it. A
deferred case covers runtime rejection of unknown command modes.
