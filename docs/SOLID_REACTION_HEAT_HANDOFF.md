# Solid-reaction heat to utility accounting

`SolidReactionHeatAdapter` exposes one already accepted `SolidReactionTrace`
to the existing `HeatDuty`/`HeatSnapshot` and `account_heat` interfaces. The
adapter reads each original `SolidReactionStep.heat_input_j` command as an
exact signed energy bin. Positive values enter the solid reaction system;
negative values leave it. It does not derive a heat duty correlation or add a
thermal transfer model.

```python
from h2physics.adapters.solid_reaction_heat import SolidReactionHeatAdapter
from h2physics.adapters.thermal_utilities import HeatDuty, HeatWindow

window = HeatWindow(start_s, end_s, clock_id, "heat-window-evidence")
duty = HeatDuty.bind(trace, SolidReactionHeatAdapter(), window)
duty.require_current()
```

The adapter requires the window to match all contiguous accepted reaction
steps on one clock. It preserves the source process ID and caloric-reference
identity, and rechecks signed step heat against the trace heat total. It
reconstructs initial/final inventory enthalpy through the exact provider owned
by the retained finite-cycle kernel. The check binds provider, kernel, species
order and energy-basis identity, then calls the provider at each inventory's
temperature and pressure before applying the producer's mass, elemental and
enthalpy residual budgets. `HeatDuty` retains
the exact source, kernel, kinetics, caloric provider, evidence and accepted
steps; changes invalidate the receipt.

This duty is classified as `external-device-heat`, because the reaction model
receives prescribed heat from its caller. It can serve as a sink profile in
existing finite heat-allocation accounting, where explicit availability,
temperature levels, coincidence, contact, transfer loss and reference
compatibility are provided separately. No heat availability, heater, exchanger
or plant-wide utility performance is inferred. See the existing
[thermal utilities guide](THERMAL_UTILITIES.md).

The deferred Hangang case `solid-reaction-heat-utility-handoff` uses an authored
core-only reaction fixture to check exact signed heat binning, stale-source
rejection, and rejection of substitute providers and reordered species. It is a
software boundary contract, not material kinetics or heat utility validation.
