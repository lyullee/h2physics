# Conditional rupture-fragment flight

`h2physics.fragment_trajectory` provides a deterministic point-mass flight model
for one rigid fragment after another owner has supplied its launch conditions.
This fills only the flight-to-ground segment identified as absent from the
current rupture capability. It does not predict how a vessel fractures, how many
pieces form, their mass/shape/launch-velocity distribution, or whether a failure
occurs.

## Physics and inputs

The state is inertial position `r` and velocity `v`, with a caller-defined
gravity vector `g`. The relative air speed is `u = v - wind(r,t)`. For the
declared constant reference area and drag coefficient, the aerodynamic force is

```text
F_drag = -0.5 * rho(z) * Cd * A * |u| * u
dr/dt = v
dv/dt = g + F_drag / m
```

The quadratic drag form follows NASA Glenn's [drag equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/);
the fragment-specific drag coefficient and projected reference area remain
caller-supplied inputs. Density and wind are replaceable Python callbacks with
separate evidence identifiers. No standard atmosphere, terrain model, fragment
orientation law, variable Reynolds-dependent drag, lift, tumbling or breakup is
silently selected.

`FragmentLaunch` declares mass, area, drag coefficient, initial position and
velocity, a horizontal ground elevation, and a coordinate `frame_id`.
`FragmentFlightEnvironment` declares density, wind, gravity, the same frame ID
and evidence IDs. Mismatched frames are rejected. `FragmentFlightSettings`
declares a `clock_id`, output times, solver controls and balance budgets. The integrator stops
at a descending crossing of the explicit ground plane or at the final requested
time. An absent crossing is represented by `impact_time_s is None`; it does not
extrapolate beyond the supplied horizon.

The solver augments the trajectory with integrated aerodynamic impulse and
aerodynamic work. It reports the momentum residual
`m*(v-v0) - m*g*dt - integral(F_drag dt)` and the mechanical-energy residual
`delta(K - m*g dot r) - integral(F_drag dot v dt)`. The work term uses the
fragment's inertial velocity, so moving wind may transfer mechanical energy to
the fragment. These checks verify numerical integration of the declared model;
they do not establish that the chosen `Cd`, density, wind, launch state or rigid
point-mass approximation represent a particular rupture.

`HydrostaticIdealGasDensityProfile` supplies one optional parametric density
callback for the trajectory. The caller sets a base altitude, pressure and
temperature, a constant temperature gradient, molecular mass, gravity, an
evidence ID, and a closed altitude domain. For a nonzero gradient, temperature
is linear in altitude and pressure follows hydrostatic balance with the ideal-gas
law; the zero-gradient branch gives the isothermal barometric relation. The
profile checks positive temperature and finite positive pressure over its
declared bounds and raises outside them. It can be passed directly as
`FragmentFlightEnvironment.density_kg_m3`.

For caller lapse rate `L`, base state `(z0, p0, T0)`, specific gas constant
`Rs`, and constant gravity `g`, the layer uses

```text
T(z) = T0 - L (z - z0)
p(z) = p0 [T(z)/T0] ** [g/(Rs L)]   if L != 0
p(z) = p0 exp[-g (z - z0)/(Rs T0)]  if L == 0
rho(z) = p(z)/(Rs T(z))
```

This helper is an authored single-layer ideal-gas relation, not a U.S. Standard
Atmosphere implementation. The [U.S. Standard Atmosphere 1976 report](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19770009539.pdf)
is a reference for layered hydrostatic atmosphere equations and reported
constants. No standard pressure, temperature, lapse rate, humidity correction,
or weather data is bundled. The `fragment-flight-hydrostatic-density-profile`
case exercises the helper and its direct trajectory callback on synthetic inputs;
it does not qualify an atmosphere or fragment hazard.

## Python use

```python
import numpy as np
from h2physics.fragment_trajectory import (
    FragmentFlightEnvironment,
    FragmentFlightSettings,
    FragmentLaunch,
    integrate_fragment_flight,
)

launch = FragmentLaunch(
    fragment_id="caller-defined-piece-01",
    mass_kg=0.8,
    reference_area_m2=0.02,
    drag_coefficient=0.9,
    position_m=np.array([0.0, 0.0, 4.0]),
    velocity_m_s=np.array([10.0, 2.0, 8.0]),
    ground_z_m=0.0,
    frame_id="facility-local-ENU",
    evidence_id="reviewed-fragment-launch-input",
)
environment = FragmentFlightEnvironment(
    density_kg_m3=lambda height_m: 1.2,
    wind_velocity_m_s=lambda position_m, time_s: np.zeros(3),
    gravity_m_s2=np.array([0.0, 0.0, -9.80665]),
    frame_id="facility-local-ENU",
    evidence_id="site-weather-and-gravity-boundary",
    density_evidence_id="declared-air-density-profile",
    wind_evidence_id="declared-wind-profile",
)
settings = FragmentFlightSettings(
    clock_id="rupture-event-clock",
    time_s=np.linspace(0.0, 5.0, 101),
)
result = integrate_fragment_flight(launch, environment, settings)
result.require_current()
```

The deferred `conditional-fragment-flight-impact` case is assigned to the
`fragment-trajectory` profile for both Hangang and Nurion. It uses synthetic
launch and atmosphere inputs to check impact localization, wind response, and
momentum/energy integration residuals. It is not a rupture experiment or a
fragment hazard qualification.

## Deliberate boundaries

This is a conditional transport model, not a complete vessel-burst or risk
model. It assumes one rigid point mass with constant `Cd` and area in a continuum
air field. It excludes rupture initiation, fragment generation, shape evolution,
rotation, fragmentation cascades, collision/rebound, structures, terrain beyond a
flat plane, blast loading during flight, injury, equipment damage, probability
and annual frequency. Couple only to an accepted rupture result when that
separate result actually provides a fragment launch state and matching clock,
frame and evidence. No such launch state is inferred here.

## Elastic energy ceiling to conditional fragment flight

`h2physics.adapters.run_elastic_bound_fragment_flight()` composes the existing Lamé elastic-energy speed ceiling with the existing rigid-fragment flight integrator. It computes the ceiling only through `bound_fragment_speed_from_elastic_energy()`, then checks the caller-provided launch's fragment identity, mass, speed and kinetic energy before integrating. The flight clock must begin at the declared event time; fragment, environment and cylinder all retain the caller's coordinate frame and evidence.

The caller remains responsible for deciding whether a pressure event occurred, identifying one fragment and its mass, supplying its position and velocity, and mapping that launch state to the cylinder. This adapter does not model vessel rupture, fragment creation, energy partition, launch direction, injury or risk probability. Deferred Hangang contract: `elastic-bound-fragment-flight-handoff` under `fragment-trajectory`.

For a native HELPR failure event, `h2physics.adapters.run_vessel_failure_fragment_flight()` can bind the exact initiation time and pressure to the existing elastic speed ceiling and rigid-fragment trajectory. Caller-owned shell mapping, fragment selection, launch state, environment and evidence remain explicit. See [vessel failure handoff](VESSEL_FAILURE.md); the deferred case is `vessel-failure-fragment-flight-handoff` under `fracture-fatigue`.
