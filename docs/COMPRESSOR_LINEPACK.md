# Real-fluid compressor to isothermal pipeline linepack

`charge_linepack_from_compressor()` transfers one accepted HEOS hydrogen
compressor operating point into the existing `RealGasLinepackState` or explicit
analytic-reference `IsothermalLinepackState` via its
native `advance()` method. The compressor and linepack remain the sole owners
of their respective calculations.

## Boundary contract

The initial linepack fixes volume, temperature, its fluid/EOS identity and
clock time. The caller supplies a positive transfer duration and maps the
compressor's `process_window_id` to that interval with an explicit clock
evidence identity. The existing compressor flow integrates to the charge mass;
the linepack ledger must preserve it exactly. The compressor discharge pressure
must exceed the final linepack pressure.

The native receiving state uses the existing `CoolPropIsothermalEOS`, with
direct HEOS fluid, hydrogen spin and installed version matched to the
compressor provider. Endpoint densities are checked against that provider.
The legacy ideal-gas state remains an explicitly selected analytic comparison.
The caller supplies one native CoolProp `ThermoState` at the
final linepack pressure and fixed linepack temperature. The adapter replays
that state through the compressor's existing provider and verifies its H2
basis. A signed thermal-conditioning energy receipt must equal
`transferred_mass * (h_conditioned - h_compressor_outlet)` within the declared
budget. Positive energy heats the stream; negative energy removes heat. This
is an inlet-conditioning ledger only; the linepack has no stored-energy state
and the connector makes no storage-energy closure claim. The real-gas state
evaluates inventory pressure from native CoolProp; it does not solve storage
temperature or the control duty needed to maintain that temperature.

Clock mapping, hydrogen identity, hydraulic feasibility and thermal conditioning
evidence are caller-owned. The adapter does not calculate a compressor,
pressure regulator, pipe friction, transient flow, cooling duty or valve law.

## Executed numerical verification — 2026-11-01

The legacy contract `hydrogen-real-fluid-compressor-linepack-charge-handoff`
and native contract
`hydrogen-real-fluid-compressor-native-linepack-charge-handoff` both passed
locally with installed CoolProp 8.0.0. Both remain registered under the
`gas-compressible-pipe` profile for remote replay. They check the existing compressor receipt,
linepack pressure and mass ledger, real-fluid state projection, signed thermal
adjustment and stale/reissued receipt rejection. It does not establish pipeline
qualification or pressure-wave behavior.

The authored case uses a 1 MPa, 300 K inlet, 5 MPa compressor discharge,
0.01 kg/s flow, and a 0.01 m3 receiver initially at 1 MPa and 300 K.
Charging from 20.0 to 20.1 s adds 0.001 kg. Native final pressure was
1,125,281.109224105 Pa; the explicit ideal reference gave
1,123,734.487442009 Pa. Native inlet-conditioning energy was
-3,282.3489534652567 J with zero projection residual. The mass residual was
-8.673617379884035e-19 kg. These are synthetic numerical results, not a measured
compressor or pipeline comparison.

Eight native rejection paths passed: normal/para mismatch, clock mismatch,
conditioning-energy mismatch, receiving pressure-domain exit, EOS native-state
pointer mutation, compressor native-state pointer mutation, EOS method
replacement, and final EOS-owner substitution. Each mutable-definition check
restored the original object and confirmed that the original receipt remained
current. Reissuing the sealed receipt was also rejected. Native pointers and
property methods are captured at issuance; equality of dataclasses whose EOS
field is excluded from comparison is not accepted as ownership evidence.
The two edited Python files also passed scoped Ruff checks.
