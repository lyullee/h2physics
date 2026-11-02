# Hydrogen fuel compression reference

**Status: implemented_unverified.** This source-level module and its deferred
acceptance contracts have not been executed. No numerical result or hardware
qualification is claimed.

`h2physics.combustion.run_hydrogen_compression(phase, inputs)` computes one
steady, adiabatic, pure-gas-H2 compression point. It delegates the isentropic
reference state to Cantera's `SPY` state setter, then applies a caller-supplied
isentropic efficiency to the native enthalpy rise and obtains the actual outlet
through `HPY`. Cantera documents these state pairs and their mass-specific units
in its [3.2 thermodynamic property API](https://www.cantera.org/3.2/python/thermo.html).
The equations are

\[
h_{2s}=h(T_1,s_1,p_2),\qquad
h_2=h_1+\frac{h_{2s}-h_1}{\eta_{is}},\qquad
\dot W_{shaft,in}=\dot m_{H_2}(h_2-h_1).
\]

The compression energy ledger is the steady adiabatic enthalpy balance. It has
no ambient heat term; callers should not interpret this single stage as an
intercooled or polytropic compressor train. `HydrogenCompressionInputs` makes
the absolute source and discharge pressures, inlet temperature, H2 mass flow,
efficiency, process window and evidence identities explicit. The caller provides
an actual Cantera ideal-gas phase with H2. No mechanism, efficiency, source state,
or rate is supplied as a calibrated default.

`couple_hydrogen_compression_to_brayton()` can compose this stage with an actual
`OpenBraytonRun` when mechanism/window labels match, fuel discharge pressure and
temperature match the cycle fuel-feed station, and H2 mass flow matches the
declared fuel-to-air ratio times caller air flow. The resulting ledger subtracts
fuel compression shaft demand from gas-path net power. It does not match a real
shaft, solve an operating point, include mechanical/generator losses, or infer
fuel-pipeline pressure loss. See [the gas-turbine request](../requests/035_hydrogen_gas_turbine_cycle.md)
for receiving-model work and [the deferred acceptance cases](../validation/cases/hydrogen_fuel_compression.py).

The ideal-gas boundary is intentionally narrow. For pure hydrogen requiring a
real-fluid reference, inject `h2physics.thermo.CoolPropProperties("Hydrogen",
backend="HEOS")` into
`run_real_fluid_hydrogen_compression(provider, inputs)`. This path calls native
CoolProp `PT` for the inlet, `PS` for the isentropic reference and `PH` for the
efficiency-adjusted outlet. It shares the immutable station summary and adiabatic
shaft ledger with the Cantera route while using separate input and result types
to make provider responsibility explicit.

`HydrogenRealFluidCompressionInputs` requires provider/window identifiers,
absolute pressure, temperature, H2 mass flow, efficiency, a caller-declared T/P
application envelope and evidence IDs. The result retains the CoolProp version,
HEOS backend, exact `PropertyBasis`, provider identity, station states and signed
energy residual. Its `require_current()` rejects changed result payloads and
provider, version, backend or basis substitutions.
The state-pair names follow the [CoolProp low-level API](https://coolprop.org/coolprop/LowLevelAPI.html)
already wrapped by `CoolPropProperties`; the compressor calls no CoolProp API
outside that provider.

The CoolProp route admits only direct HEOS with a Hydrogen, ParaHydrogen or
OrthoHydrogen basis. Liquid and two-phase states fail. Gas and supercritical gas
states pass only as single-phase states; a `supercritical` label is accepted
only when both coordinates are above the provider's critical point. The caller's
domain envelope is checked at every station and CoolProp flash errors fail the
stage. That caller envelope is not itself an independently qualified operating
limit. Tabular backends are not admitted because this compressor API has no
attached table error qualification. The Cantera Brayton link remains restricted
to the Cantera result so no property-reference conversion is inferred between
engines.

Manufacturer maps, compressor cooling, multistage staging, seals, surge/choke
limits, startup/control and measured machine data remain future work. Neither
single-stage route is a compressor design or safety basis. The real-fluid
acceptance contracts are in
[validation/cases/hydrogen_fuel_compression.py](../validation/cases/hydrogen_fuel_compression.py)
and remain unexecuted.
