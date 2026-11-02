# Two-vent hydrogen buoyant-layer model

`TwoVentHydrogenLayerConfig` and `run_two_vent_hydrogen_layer()` provide a
parameterized, low-order estimate of upper-layer hydrogen accumulation from a
steady vertical source in a still-air enclosure with one low and one high
vent. The state tracks upper-layer volume and hydrogen mass; outputs include
interface elevation, hydrogen mole/mass fraction, vent flows, pressure
difference and an integrated hydrogen mass residual.

```python
from h2physics.buoyant_layer import (
    TwoVentHydrogenLayerConfig,
    run_two_vent_hydrogen_layer,
)

model = TwoVentHydrogenLayerConfig(
    compartment_height_m=3.0,
    floor_area_m2=36.0,
    source_height_m=0.2,
    lower_vent_area_m2=0.08,
    upper_vent_area_m2=0.08,
    lower_discharge_coefficient=0.65,
    upper_discharge_coefficient=0.65,
    ambient_pressure_pa=101325.0,
    ambient_temperature_k=293.15,
    initial_upper_layer_volume_m3=0.5,
    initial_upper_h2_mole_fraction=0.005,
)
trace = run_two_vent_hydrogen_layer(
    model,
    hydrogen_mass_flow_kg_s=1.0e-5,
    duration_s=120.0,
    maximum_step_s=0.25,
)
```

## Model contract

The plume buoyancy flux is calculated from the imposed pure-H2 mass flow and
native CoolProp HEOS H2/carrier densities at ambient conditions. A Morton-Taylor-Turner style
self-similar plume relation, including a finite virtual-origin offset, gives
the volume flux reaching the layer interface. Upper-layer volume and H2 mass
are advanced with fixed-step fourth-order Runge-Kutta. At each stage, mixture
density follows the native mixture flash at ambient temperature and the solved
enclosure pressure. Lower-inlet and upper-outlet flows use caller vent areas,
discharge coefficients and Bernoulli pressure heads; a bounded scalar solve
enforces mass continuity `rho_air * Q_lower + m_dot_H2 = rho_layer * Q_upper`.
The vent pressure head is `g * (rho_air - rho_layer) * (H - h_interface)` Pa.

The default `CoolPropHydrogenAirProperties` uses normal Hydrogen and a fixed
N2/O2/Ar carrier with mole ratios 0.78084:0.20946:0.00934, normalized by their
sum 0.99964. Water, CO2 and trace gases are absent. Pass
`properties=CoolPropHydrogenAirProperties(dry_air_mole_fractions=(...))` to
declare another normalized, positive N2/O2/Ar ratio. Native molar masses
perform composition conversion; hydrogen stock is inverted against native
mixture density. This replaces the former pseudo-air ideal-density closure.
The result retains `property_backend_id` and `dry_air_mole_fractions`.
CoolProp failures propagate, and nongas phases are rejected; no ideal fallback
exists. This interface supplies density only and introduces no energy model.
See [CoolProp low-level API](https://coolprop.org/coolprop/LowLevelAPI.html)
and [native mixture support](https://coolprop.org/fluid_properties/Mixtures.html).

The coupled composition, buoyancy-head and vent roots use bounded Brent solves
instead of nested fixed-count bisections. No acceleration factor is claimed.
Four local native density/stock, short conservation and rejection tests passed;
the historical 600-second case and measured-data qualification remain pending.
Downstream oxygen projection must declare the same carrier O2 mole fraction.
The binding and later full-carrier-mutation rejection passed a separate focused
integration check (66.47 s), followed by scoped Ruff and diff checks. The
original four native backend tests passed in 55.94 s. Legacy analytical traces
lack native carrier metadata. These checks do not establish measured-data
validation or total upper-layer carrier/energy closure; the retained model
resolves layer volume, H2 mass and algebraic whole-vent mass continuity.

The implementation uses a separately written parameter/state API and its own
conservation bookkeeping. Its plume and two-vent closure are informed by the
published analytical model in Prasad, Yang and Pitts, *Vertical Release of
Hydrogen in a Partially Enclosed Compartment: Role of Wind and Buoyancy*,
International Journal of Hydrogen Energy 36 (2011), DOI
[10.1016/j.ijhydene.2010.08.040](https://doi.org/10.1016/j.ijhydene.2010.08.040).
No paper text, figures, tables, or fitted results are reproduced here.

## Limits

- One steady pure-H2 source, released vertically into an unobstructed room.
- Still ambient air; wind, intermediate vents and multiple sources are not
  modeled.
- A single, uniform, isothermal upper layer and an ambient lower layer are
  assumed. Molecular diffusion, wall heat transfer, humidity and combustion
  are omitted.
- Vent flow is restricted to lower inflow and upper outflow. The solver rejects
  states without a pressure solution in that regime or when the interface
  reaches the source.
- The plume entrainment closure remains a low-pressure buoyant-plume approximation.
  It is not a high-pressure leak/nozzle model; supply the release mass flow
  from an independently selected source model.
- This is not CFD, an alarm/ignition model, a flammability-volume standard or a
  facility qualification. The deferred Hangang case is synthetic and unrun.
