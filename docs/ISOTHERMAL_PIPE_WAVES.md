# Isothermal pipeline pressure waves

## Purpose

`h2physics.isothermal_pipe_waves.IsothermalPipeWaveModel` represents transient
momentum storage and pressure-wave travel in one straight, constant-area,
closed-ended hydrogen pipe segment. It fills a fidelity gap between existing
steady Darcy flow and fixed-volume quasi-steady linepack. It does not replace
or silently alter either model.

The formulation follows the one-dimensional isothermal Euler equations with
a pluggable single-phase EOS and Darcy-Weisbach momentum loss. The public equation source
is Gugat, Krug and Martin, “Transient gas pipeline flow: analytical examples,
numerical simulation and a comparison to the quasi-static approach,”
*Optimization and Engineering* 24 (2023),
[DOI 10.1007/s11081-021-09690-4](https://doi.org/10.1007/s11081-021-09690-4).
The implementation is independently written and cites the source for model
formulation only; the citation does not imply validation against that paper.

## Equations and numerics

Cell averages store density `rho` and axial momentum per volume `rho*u`:

```text
partial_t(rho)     + partial_x(rho*u)       = 0
partial_t(rho*u)   + partial_x(rho*u*u + p) = - f_D/(2 D) * rho*u*abs(u)
p = p(rho, T) ; c_T^2 = (partial p / partial rho)_T
```

Temperature and composition are fixed. The default EOS is ideal hydrogen with
molar mass 0.00201588 kg/mol. For high-pressure hydrogen, pass a real-fluid or
qualified table provider through the shared `IsothermalSinglePhaseEOS` contract.
The `CoolPropIsothermalEOS` adapter supplies `p(rho,T)`, `rho(p,T)`, and
`c_T=sqrt(1/(rho*kappa_T))` from the isothermal compressibility. It never
substitutes CoolProp's adiabatic speed of sound. Its homogeneous gas/supercritical
phase envelope is enforced by the provider. With no boundary object, pipe ends
remain impermeable walls: boundary mass flux is zero and wall momentum flux is
the adjacent cell pressure. `FiniteReservoirPressureBoundary` optionally
supplies a caller-owned time/pressure history at either end. Its EOS-mapped
reservoir state provides the incoming subsonic characteristic; the adjacent
pipe cell provides the outgoing characteristic. The state is passed through a
Rusanov ghost face, and cumulative boundary inflow/outflow closes total pipe
mass. The pressure history must cover the run and use the pipe EOS, temperature
and declared clock. Reservoir depletion and connector/nozzle flow remain
caller-owned; see [reservoir boundary contract](PIPE_WAVE_RESERVOIR_BOUNDARIES.md).

The spatial discretization is first-order finite volume with local Rusanov
fluxes. The explicit timestep obeys `dt <= CFL * dx / max(abs(u) + c)`, where
the caller chooses `0 < CFL <= 0.5` and the isothermal sound speed is
`c = c_T(rho,T)`. The code rejects nonpositive/nonfinite density after
each flux update; it does not clip states. Darcy drag uses the exact local
momentum decay map over each substep, so friction does not introduce a second
explicit stability limit. Requested output times are reached by substeps
without temporal interpolation. `maximum_internal_steps` prevents an
unbounded run if a caller requests infeasible resolution.

## Python API

```python
import numpy as np
from h2physics import IsothermalPipeWaveModel
from h2physics.thermo import CoolPropIsothermalEOS

n = 40
model = IsothermalPipeWaveModel(
    length_m=100.0, internal_diameter_m=0.1, cell_count=n,
    temperature_k=300.0, eos=CoolPropIsothermalEOS(fluid="Hydrogen"),
    darcy_friction_factor=0.015, maximum_cfl=0.35,
)
trace = model.simulate(
    initial_pressure_pa=np.full(n, 5.0e6),
    initial_velocity_m_s=np.zeros(n),
    time_samples_s=(0.0, 0.02, 0.05, 0.10),
)
```

Pressure input is absolute Pa, velocity m/s, time s, length/diameter m,
temperature K; the EOS provider owns its composition and mass basis. The result carries immutable sampled
pressure, velocity, density, face mass flow, total mass and mass residual
arrays. Interior face mass flow at each sample is the final accepted numerical
mass flux multiplied by cross-sectional area; both closed-end flows are exactly
zero. With open boundaries, signed flow is positive toward the pipe's right;
traces retain pressure histories, cumulative total inflow/outflow and the
boundary-adjusted mass residual. `maximum_cfl` reports the largest actually used substep CFL, while
`cfl_limit` records the requested upper bound.

The deferred Hangang contract is
`hydrogen-pipeline-isothermal-pressure-wave-dynamics` under
`gas-compressible-pipe`. It checks equilibrium preservation, pulse response,
positive states, CFL bound, closed-end mass conservation and result immutability.
It is a synthetic software contract, not model validation.

## Scope and next evidence

This model does not include an energy or wall heat-storage equation, elevation,
variable friction, network junctions, compressors, reservoir inventory
depletion, valve motion, leak/nozzle law, rupture or measured-pipeline
qualification. Strong discontinuities are numerically diffused by the
first-order Rusanov method; timestep and grid refinement are necessary before
interpreting wave peaks. Applications requiring surge design or qualified
transfer behavior need independently established boundary data and validation.

## Frozen gas-mixture EOS

The same solver accepts `CoolPropMixtureIsothermalEOS` without changing its
pipe equations. The adapter supplies mass-density closure and the mixture's
native isothermal characteristic speed under one immutable, declared gas
composition. Callers construct a `GasComposition`, wrap it in
`CoolPropMixtureProperties`, then pass
`CoolPropMixtureIsothermalEOS(properties)` as `eos=` when creating
`IsothermalPipeWaveModel`. Component names, mole fractions, molar masses and
the CoolProp HEOS version remain part of the provider identity; no ideal-gas
fallback is applied. The gas-phase guard rejects liquid or two-phase
evaluations. Composition is held fixed during a simulation.

Deferred Hangang case
`hydrogen-pipeline-isothermal-mixture-pressure-wave` composes a synthetic H2/N2
blend with the existing pipe solver and checks pressure-density replay,
sampled homogeneous closure, positive isothermal sound speed, CFL limit and
closed-end mass ledger. It also confirms that a reservoir boundary carrying a
different frozen-mixture EOS identity is rejected. This is provider/solver
interface evidence only, not a blend-pipeline measurement or validation
result. No local model execution is claimed.
