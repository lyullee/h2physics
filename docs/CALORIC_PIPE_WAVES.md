# Caloric compressible pipe waves

`CaloricPipeWaveModel` is an energy-conserving one-dimensional finite-volume
model for transient gas flow in a uniform pipe. It is a separate numerical and
physical level from `IsothermalPipeWaveModel`: the state advances in density,
momentum density and total-energy density, and the equation of state returns
pressure, temperature and acoustic speed from `(density, internal energy)`.

## Governing balance

For a constant-area horizontal pipe, the conserved state and inviscid flux are

```text
U = [rho, rho*u, rho*(e + u*u/2)]
F = [rho*u, rho*u*u + p, u*(rho*(e + u*u/2) + p)]
```

Cell averages advance by the conservative finite-volume difference of adjacent
face fluxes. Each face uses the local Lax-Friedrichs/Rusanov flux, with
wave-speed bound `max(|u| + a)` from the two adjacent states. The explicit
substep obeys `dt <= CFL * dx / max(|u| + a)` and requires `CFL <= 0.5`.
Closed ends use reflective ghost states, giving zero end mass and energy flux
and wall pressure traction. Internal fluxes telescope; the trace checks global
mass and total-energy changes against the signed boundary flux integrals.

The conservative equations are the one-dimensional compressible Euler
balances; the first-order Rusanov face flux follows the shock-capturing method
introduced by Rusanov ([original paper](https://doi.org/10.1016/0041-5553(62)90062-9)).
The equations and flux are implemented independently in this project.

### Optional distributed sources

An optional `CaloricDarcyFrictionLaw` supplies one nonnegative **Darcy** factor
per cell from the current EOS state, velocity and diameter. The built-in
`UniformDarcyFriction` is a caller-supplied constant; the module does not infer
a factor from Reynolds number, roughness, viscosity or a borrowed correlation.
The convention is Darcy-Weisbach ([Moody, 1944](https://doi.org/10.1115/1.4018140));
the momentum source is `-f_D*rho*u*abs(u)/(2*D)`. A frozen factor over each
internal substep uses the exact relaxation solution for this source. For a
stationary adiabatic wall, momentum changes while total energy remains
constant: lost kinetic energy remains in the fluid as internal energy. It is
not entered as an external energy sink.

`CaloricPipeWallHeatBoundary` represents a constant caller-evidenced wall
temperature `T_w` and heat-transfer coefficient `h`. For a circular pipe, the
volumetric source is `q''' = (4*h/D)*(T_w-T)` W/m³; positive heat flows into the
gas. Only total energy receives this external source. The exact signed integral
is retained as `cumulative_wall_heat_in_j` and included in the global energy
residual. This boundary assumes prescribed wall temperature, no wall heat
capacity, and caller-supplied `h`. Positive finite EOS `cv` is required to
bound the explicit thermal-source time step. No clipping or state repair is
applied.

Friction diagnostics retain output-interval time-weighted mean and maximum
factor per cell, interval internal-step count, provider identity, evidence,
owner and applied scheme. This bounds diagnostic memory by requested outputs
times cells; internal-substep histories are not retained. Heat-boundary
provenance and configuration are also present on the trace.

## Property closure

Pass any provider with `basis`, `state_pt(P, T)` and
`state_rho_u(rho, e)` methods. Returned objects must be the repository's
`ThermoState`, with compatible basis and a finite positive speed of sound.
The included `CoolPropProperties` provider implements `state_rho_u`; use an
explicitly selected backend and single-phase hydrogen basis. CoolProp's
hydrogen equations of state are described by Leachman et al.
([DOI 10.1063/1.3160306](https://doi.org/10.1063/1.3160306)); CoolProp is an
optional dependency installed with `h2physics[thermo]`.

The solver rejects liquid, two-phase, unknown, or otherwise unsupported states.
It does not force a gas state, extrapolate an EOS, or switch providers after an
EOS failure. The default `CoolPropProperties` instance is mutable and
stateful; run a model with its own provider instance and do not share one
instance concurrently between separate calculations.

## Usage

```python
import numpy as np

from h2physics.caloric_pipe_waves import CaloricPipeWaveModel
from h2physics.thermo.coolprop import CoolPropProperties

properties = CoolPropProperties("Hydrogen")
model = CaloricPipeWaveModel(
    length_m=100.0,
    internal_diameter_m=0.10,
    cell_count=80,
    eos=properties,
    maximum_cfl=0.3,
)
trace = model.simulate(
    initial_pressure_pa=np.full(80, 8.0e6),
    initial_temperature_k=np.full(80, 295.0),
    initial_velocity_m_s=np.zeros(80),
    time_samples_s=(0.0, 0.001, 0.002),
    clock_id="process-run-clock-17",
)
```

The initial arrays are cell-centered state values; they are not a boundary
condition. Requested output times must start at zero and increase strictly.
The time step is internally bounded by the explicit CFL condition and every
EOS evaluation must remain in its admitted phase domain. No result is
interpolated to requested output times; the solver shortens a final step to
land exactly on each sample.

## Optional source inputs

`CaloricDarcyFrictionLaw` supplies one nonnegative **Darcy** factor per cell
from its current EOS state, velocity and diameter. `UniformDarcyFriction` is a
caller-supplied constant; the module does not derive a factor from Reynolds
number, roughness, viscosity or a borrowed correlation. The convention is
Darcy-Weisbach ([Moody, 1944](https://doi.org/10.1115/1.4018140)); the momentum
source is `-f_D*rho*u*abs(u)/(2*D)`. With a frozen factor during each internal
substep, the momentum source uses its exact relaxation solution. For a
stationary adiabatic wall, lost kinetic energy remains internal: friction does
not remove total energy or appear as an external energy sink.

`CaloricPipeWallHeatBoundary` specifies a fixed, caller-evidenced wall
temperature `T_w` and heat-transfer coefficient `h`. For a circular pipe the
volumetric source is `q'''=(4*h/D)*(T_w-T)` W/m³; positive heat flows into the
gas. The signed integral `cumulative_wall_heat_in_j` enters the energy balance
residual exactly. The wall has no thermal storage or axial conduction. The
explicit source requires positive finite EOS `cv`; the pre-step bound is
checked again against the proposed post-flux state, and an over-limit step is
rejected without clipping.

Friction diagnostics retain time-weighted mean and maximum factor per cell and
internal-step count per requested output interval, plus provider/evidence
identity and applied scheme. Memory scales with output intervals times cells,
not internal substeps.

Both sources are optional arguments to the same `simulate` call. Custom
friction providers implement `darcy_factor(state, velocity_m_s,
internal_diameter_m)` and expose stable `identity`, `state_owner_id`,
`evidence_id`, and `clock_id` strings.

## Reservoir boundaries

An optional `CaloricPipeReservoirBoundary` is a fixed full thermodynamic ghost
state with caller-supplied identity, source evidence, clock and velocity. The
exact Rusanov boundary flux is integrated into signed net mass and total-energy
ledgers. This object represents a prescribed large reservoir state; it has no
finite stock, depletion, pressure history, valve, or actuator. The closed-wall
mode is preferable when a caller cannot justify a fixed external state. A
finite reservoir should use a separate coupled inventory model with one shared
accepted boundary rate.

## Scope and limitations

- Single-component, homogeneous, single-phase gas/supercritical states only.
- One-dimensional, constant-area, horizontal pipe and first-order spatial
  reconstruction; no limiter or higher-order shock scheme.
- Euler mass, axial momentum, and total-energy transport with Rusanov flux.
- Optional caller-specified Darcy momentum friction and fixed-wall heat only;
  no unsteady friction, transient wall conduction/storage, or elastic response.
- No gravity, junctions, valves, two-phase transition, leaks,
  finite reservoir depletion, or atmospheric dispersion.
- The current boundary is a fixed prescribed ghost state, not a characteristic
  finite-inventory boundary. Boundary conditions and upstream inventories must
  not be inferred from nominal process values.
- Numerical conservation and synthetic contract checks do not establish
  hydrogen EOS accuracy, a pipeline decompression benchmark, fracture-arrest
  performance, or facility qualification.

The three deferred Hangang cases are registered in
`validation/cases/caloric_pipe_waves.py` under `gas-compressible-pipe`. They
exercise synthetic closure, pulse propagation, CFL, boundary identity,
mass/energy ledgers, and EOS configuration provenance only. They remain
unexecuted until a pinned cluster campaign. A measured pipeline/decompression
source is separately required for independent validation.

## Property-state replay and boundary provenance

Each cell's `state_rho_u` response must reproduce the submitted density within
2e-6 relative and 1e-10 kg/m3 absolute, and reproduce internal energy within
2e-6 relative and 1e-2 J/kg absolute. These explicit closure budgets reject a
property provider that returns a different state from the conservative
variables; they do not qualify the EOS against independent reference data.

For each open end, the trace retains the boundary ID, state-owner ID,
state-evidence ID and run clock as a complete set. Closed ends retain none of
those fields. The EOS identity requires either a caller-declared stable `identity`
or an exposed nonempty JSON-compatible `configuration` mapping. When a mapping
is exposed, its canonical representation is SHA-256 fingerprinted and combined
with the provider class, property basis and any public backend, version and
internal-energy policy. `CoolPropProperties` has no generic identity field, so
its fingerprint is derived from its public fluid basis, backend, version,
internal-energy policy and quality-roundoff tolerance. Custom providers must
expose their identity-bearing settings in `configuration`, or supply an
`identity` string that the caller keeps unique across configurations. An
identity-only provider remains accountable for not reusing that string after
changing EOS settings; a fingerprint does not prove that the implementation
itself is unchanged.

The caller supplies `clock_id` for every run, including closed-wall runs. The
trace retains that clock together with pipe length, internal diameter and
cross-sectional area. A downstream model can therefore reconstruct integrated
mass and energy from the reported face rates without inferring geometry or
clock origin.

The trace preserves `pipe_length_m`, `internal_diameter_m`, and `area_m2` so
cell states and integrated ledgers retain the geometry needed for downstream
interpretation. Every run requires an explicit `clock_id`, including a closed
wall run; this lets subsequent boundary or process models reuse the caller's
time basis. EOS identity, both boundary identifiers, and open-boundary state
owner/evidence identifiers are also retained in the immutable trace.
