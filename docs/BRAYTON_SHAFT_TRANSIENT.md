# Transient single-spool shaft response

`h2physics.combustion.integrate_shaft_transient()` advances a finite rotor
kinetic-energy state from explicit time-varying turbine and compressor shaft
powers, external load torque, Coulomb-like mechanical drag, viscous drag, and
rotor inertia. Turbine/compressor powers and load torque are linearly sampled
between caller-declared time knots. The API retains cumulative work channels,
the rotor energy residual, SciPy solver diagnostics and a terminal speed event.

```python
import numpy as np
from h2physics.combustion import (
    ShaftTransientInputs,
    integrate_shaft_transient,
)

inputs = ShaftTransientInputs(
    time_s=np.array([0., 1., 2.]),
    turbine_power_w=np.array([1.2e6, 1.25e6, 1.3e6]),
    compressor_power_w=np.array([0.8e6, 0.82e6, 0.84e6]),
    load_torque_nm=np.array([250., 260., 270.]),
    output_time_s=np.linspace(0., 2., 41),
    rotor_inertia_kg_m2=8.0,
    initial_speed_rad_s=300.,
    minimum_speed_rad_s=100.,
    maximum_speed_rad_s=600.,
    coulomb_loss_torque_nm=3.,
    viscous_loss_nm_per_rad_s=0.002,
    relative_tolerance=1e-8,
    absolute_energy_tolerance_j=1e-4,
    maximum_step_s=0.02,
    shaft_id="shaft-1",
    power_basis_id="cycle-power-v1",
    load_basis_id="generator-torque-v1",
    inertia_evidence_id="rotor-inertia-record-v1",
)
trace = integrate_shaft_transient(inputs)
trace.require_current()
```

The balance convention is

`Δ(0.5 J ω²) = W_turbine − W_compressor − W_load − W_coulomb − W_viscous`.

The speed floor and ceiling are terminal events. A speed excursion is never
clipped; the trace ends at the event and labels the reason. Solver failure
retains its dense-output prefix and a failure status. Schedule arrays are
immutable and their content signature is checked before reuse.

## Model boundary

The optional [mapped gas-path feedback](BRAYTON_SHAFT_FEEDBACK.md) now replaces
the two scheduled powers using an actual map/Cantera calculation at every
rotor trial speed. It reuses this energy ODE and its work ledgers. That new
path is implemented but unexecuted; its physical-to-corrected-speed mapping
and remaining operating law must be explicitly supplied. The scheduled route
described below retains its original scope.

This is rotor mechanics only. It does not predict turbine/compressor powers,
map operation, fuel flow, reaction, pressure, temperature, shaft coupling among
multiple spools, governor action, generator electrical dynamics, or machine
surge/choke. Couple its power inputs to a separately admitted component/cycle
model over a common clock and preserve that model's map, thermodynamic state,
and evidence. It is not a machine qualification or operating recommendation.

The chosen coordinate is kinetic energy rather than angular velocity, which
avoids a power-over-speed singularity near a stall. Cumulative energy channels
are integrated as states of the same ODE as the rotor inventory so the
reported first-law residual is independently auditable. They remain numerical
integration outputs; acceptance limits and independent physical comparisons
are still required.

## Verification status

`hydrogen-brayton-transient-shaft-balance` and
`hydrogen-brayton-transient-shaft-speed-event` are synthetic deferred Hangang
contracts. They check energy/work signs, steady balance and explicit speed-limit
termination. They are not experimental validation. The prescribed power/load
histories and inertia must be supplied with applicable source records before
any real installation is analyzed.
