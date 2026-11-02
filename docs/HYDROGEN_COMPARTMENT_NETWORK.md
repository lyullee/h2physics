# Fixed-state hydrogen compartment network

`CompartmentNetworkModel` advances H2 mole fractions in a caller-defined graph
of well-mixed gas compartments. It is an indoor network mixing layer for
composing source, room-to-room transfer, and exhaust histories before a separate
exposure or risk calculation. It extends the spatial scope of a single-zone
layer without treating rooms as CFD cells.

## Equations and units

Each room has fixed volume `V`, absolute pressure `P`, and temperature `T`. Its
constant total ideal-gas molar inventory is
`n = P V / (R T)`. For room `i`, the H2 mole fraction `x_i` follows

```
n_i dx_i/dt = sum_j(F_ji x_j) + sum_external(F_in x_feed)
              - x_i sum_out(F_out)
```

All `F` values are mol/s and use a directed stream convention. An external
inlet supplies its explicitly declared H2 mole fraction. Inter-room transfer
uses the source room's instantaneous well-mixed fraction. Exhaust carries the
current fraction of its source room. Each room's total molar inlet and outlet
must balance on every interval so the prescribed constant P/T inventory is
consistent. Piecewise-constant stream rates yield a linear system; a matrix
exponential advances its species state and external H2 ledgers exactly for each
interval.

The non-hydrogen carrier fraction is `1 - x_i` and follows the corresponding
species transport equation. The trace retains separate cumulative exterior
in/out amounts and mole residuals for both H2 and the carrier.

## Python API

```python
from h2physics.compartment_network import (
    CompartmentMolarTransfer,
    CompartmentNetworkModel,
    WellMixedCompartment,
    simulate_hydrogen_compartment_network,
)

rooms = (
    WellMixedCompartment(
        identifier="equipment-room", volume_m3=180.0,
        absolute_pressure_pa=101_325.0, temperature_k=293.15,
        initial_hydrogen_mole_fraction=0.0,
        state_owner_id="site-model", state_evidence_id="room-survey-v3",
    ),
    WellMixedCompartment(
        identifier="adjacent-room", volume_m3=90.0,
        absolute_pressure_pa=101_325.0, temperature_k=293.15,
        initial_hydrogen_mole_fraction=0.0,
        state_owner_id="site-model", state_evidence_id="room-survey-v3",
    ),
)
clock_id = "facility-run-clock"
flow = (0.02, 0.015)  # one molar-flow value per output interval, mol/s
streams = (
    CompartmentMolarTransfer(
        "h2-release", None, "equipment-room", flow,
        "release-owner", "release-history-v2", clock_id,
        external_hydrogen_mole_fraction=1.0,
    ),
    CompartmentMolarTransfer(
        "doorway-mixing", "equipment-room", "adjacent-room", flow,
        "opening-model", "measured-transfer-history", clock_id,
    ),
    CompartmentMolarTransfer(
        "mechanical-exhaust", "adjacent-room", None, flow,
        "ventilation-owner", "fan-history-v1", clock_id,
    ),
)
network = CompartmentNetworkModel(rooms, streams, clock_id)
trace = simulate_hydrogen_compartment_network(
    network, time_samples_s=(0.0, 10.0, 20.0),
)
```

`HydrogenCompartmentNetworkTrace` retains room ordering, fixed-state provenance,
stream schedules, common clock, H2/carrier mole fractions and inventories,
external H2/carrier input and exhaust ledgers, and separate whole-network
species residuals. Traces are issued
by the completed solver path and validate their residual against retained
states and transfers. Room-to-room streams cancel from the global external
ledger by construction.

## Scope and limitations

The caller supplies every directed molar-flow schedule. The package does not
derive opening flow from pressure difference, buoyancy, vent area, discharge
coefficient, wind, or a fan curve. It also does not solve room pressure or
temperature, heat transfer, combustion, additional species, spatial gradients,
stratification, sensor response, exposure dose, ignition, or consequence. The
perfectly mixed assumption applies separately to each room; doorway jets and
plume entrainment are unresolved. Fixed room pressure and temperature are
compatible only with intervals where each room's declared total molar inflow
matches its outflow. Invalid schedules reject before advancement; no hidden
pressure controller or inventory clipping is applied.
If numerical advancement fails after one or more output intervals,
`CompartmentNetworkExecutionError` retains the failed interval and the completed
prefix trace. Invalid input schedules reject during preflight before any
advancement.

This level transports only the hydrogen mole fraction against one inert
carrier-gas remainder. It is a configurable source/vent network for screening
and code composition, not an independent safe-concentration limit or a
validated building-ventilation prediction. Caller evidence IDs should identify
geometry and every flow schedule. Do not infer validation from a synthetic
contract.

## Deferred Hangang contract

`hydrogen-fixed-state-compartment-network-mixing-closure` is registered under
the `oxygen-deficiency` execution profile. It checks transfer through two
compartments, external species-ledger closure, clock/schedule coverage, and
rejection of unbalanced room flows. It is synthetic software verification and
has not been run.
