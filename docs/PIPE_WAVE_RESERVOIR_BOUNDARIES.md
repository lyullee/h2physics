# Time-varying reservoir boundaries for isothermal pipe waves

`FiniteReservoirPressureBoundary` binds an externally modeled reservoir's
pressure history to one end of `IsothermalPipeWaveModel`. At each requested
pipe simulation step, the solver interpolates the caller's pressure history
within its declared time support, maps pressure to density with the same
isothermal EOS used by the pipe, and couples the reservoir's incoming
characteristic with the pipe's outgoing characteristic. The pipe model then
uses its existing Rusanov face flux.

```python
import numpy as np
from h2physics.core import Origin
from h2physics import IsothermalPipeWaveModel, IdealHydrogenIsothermalEOS
from h2physics.pipe_reservoir_boundary import FiniteReservoirPressureBoundary

eos = IdealHydrogenIsothermalEOS()
left = FiniteReservoirPressureBoundary(
    identifier="upstream-reservoir",
    state_owner_id="caller-reservoir-model",
    state_evidence_id="upstream-pressure-history-v1",
    clock_id="plant-clock",
    eos_identity=eos.identity,
    temperature_k=300.0,
    time_s=(0.0, 1.0, 2.0),
    pressure_pa=(5.1e6, 5.0e6, 4.9e6),
    origin=Origin.SYNTHETIC,
)
model = IsothermalPipeWaveModel(
    length_m=100.0, internal_diameter_m=0.1, cell_count=40,
    temperature_k=300.0, eos=eos, maximum_cfl=0.35,
)
trace = model.simulate(
    initial_pressure_pa=np.full(40, 5.0e6),
    initial_velocity_m_s=np.zeros(40),
    time_samples_s=(0.0, 0.5, 1.0, 2.0),
    left_reservoir=left,
    clock_id="plant-clock",
)
```

## Reservoir state ownership

The boundary object stores a unique reservoir ID, state-owner ID, pressure
evidence ID, time clock, EOS identity, temperature, pressure knots and
provenance. Histories must cover the complete pipe run. Pressure interpolation
is piecewise linear and never extrapolates. Each knot's pressure/density state
must be admitted and replayed by the pipe EOS. Both reservoirs, when supplied,
must use the same clock, temperature and EOS identity as the pipe.

The reservoir's pressure history represents the output of a caller-owned
finite inventory or process model. The pipe solver does not evolve reservoir
mass, energy, regulator position, valve flow or an orifice law. A boundary's
signed mass flow is determined by its characteristic/Rusanov coupling and is
retained at output times; cumulative total inflow and outflow close the pipe's
total-mass history.

## Characteristic and numerical limits

At a subsonic open boundary, the incoming isothermal characteristic is taken
from the zero-velocity reservoir state while the outgoing characteristic is
extrapolated from the adjacent pipe cell. The resulting ghost state is passed
to the same Rusanov flux used for interior faces. EOS-derived density and
isothermal sound speed must remain positive, the mixed state must be bracketed
by the local pipe and reservoir densities, and supersonic boundary states are
rejected. The boundary is not a resolved connector/nozzle.

The numerical level remains one constant-area pipe, fixed temperature and
composition, one-dimensional isothermal Euler dynamics, first-order Rusanov
flux and caller Darcy friction. It has no pressure waves in the reservoir,
reservoir depletion, pipe wall energy, valve/orifice flow coefficient,
network junction, wind, or field-data qualification. The deferred Hangang
contract `hydrogen-pipeline-isothermal-wave-finite-reservoir-boundaries` is a
synthetic software check and remains unrun.
