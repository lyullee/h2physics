# Real-fluid compressor to finite-hydride gas port

`bind_compressor_to_finite_hydride()` maps one owner-issued CoolProp HEOS
hydrogen compressor operating point onto the existing finite-hydride gas-port
boundary. It does not implement compression, line flow, a valve, pressure
control, or hydride uptake. Those remain owned by the existing compressor,
caller-supplied transfer boundary, and finite-hydride bed.

## Contract

The adapter requires:

- An original `HydrogenRealFluidCompressionRun` using a direct HEOS hydrogen
  provider with a pure-H2 discharge, plus the actual
  `HydrideGasThermodynamics` used by the receiving bed. Fluid, hydrogen spin
  identity, and energy reference must be compatible.
- One native `ThermoState` at the compressor discharge. The state must match
  the compressor's absolute pressure, temperature, density, enthalpy and
  entropy, and must also close against a pressure-temperature replay by the
  receiver's gas-property owner. The property basis must match across both
  components.
- A positive physical-time interval and an explicit shared clock identity.
  The compressor point's accepted H2 mass flow is held constant over this
  interval; transferred mass is `mass_flow * duration`.
- Separate evidence identities for clock alignment, hydraulic transfer and
  the compressor-to-receiver state projection. The caller establishes that the
  chosen line/valve/window is physically valid.
- A bounded specific-enthalpy closure tolerance. The exact accepted discharge
  state supplies the gas-port enthalpy; the adapter does not reflash to adjust
  the mass or energy ledger.

`CompressorFiniteHydridePort.boundary` can be passed as the existing
`gas_port` argument to `FiniteHydrideBed.simulate()`. The bed retains its own
native thermodynamics, inventory, kinetics and energy balance. The adapter's
`require_current()` replays the source/provider state mapping and checks the
issued interval mass and enthalpy ledger. Each gas-port callback also replays
the compressor and receiver-property state mapping before returning the stream,
so the bed cannot consume a state changed after the outer freshness check.

## Scope and verification

Deferred Hangang contract: `hydrogen-compressor-finite-hydride-gas-port-handoff`
in the `finite-hydride` profile. It exercises the native compressor, accepted
port mapping, finite-bed integration, storage ledgers and stale-state rejection.
No execution or physical validation is claimed until that deferred contract is
run and its output is reviewed. This connection does not establish line
pressure drop, valve sizing, transient compressor behavior, a filling protocol,
or independent hydride-bed qualification.
