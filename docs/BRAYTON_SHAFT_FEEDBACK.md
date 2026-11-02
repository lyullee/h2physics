# Mapped gas-path feedback into rotor dynamics

Status: implemented, unverified. No model, native import, example or test has
been executed for this coding increment. Only source AST and lint inspection
have been performed.

`integrate_shaft_transient(inputs, gas_path_feedback=feedback)` now obtains
turbine and compressor powers from the existing mapped Brayton calculation at
each rotor ODE trial. The same kinetic-energy integrator and cumulative-work
states are reused. Without `gas_path_feedback`, the existing scheduled-power
route continues to use the supplied piecewise-linear power histories.

The feedback law is quasi-steady: at the current physical speed it selects an
admitted compressor/turbine map operating point and runs the existing native
gas-path calculation. Gas volumes, combustor storage, surge, governor dynamics,
generator dynamics and multispool mechanics are not resolved.

## Python contract

```python
from h2physics.combustion import (
    MapMatchedBraytonShaftFeedback,
    integrate_shaft_transient,
)

feedback = MapMatchedBraytonShaftFeedback(
    phase_factory=phase_factory,
    corrected_speeds=corrected_speeds,
    operating_inputs=operating_inputs,
    feedback_id="native-mapped-gas-path",
    shaft_id=shaft_inputs.shaft_id,
    power_basis_id=shaft_inputs.power_basis_id,
    speed_mapping_evidence_id="physical-speed-to-two-map-coordinates",
    operating_law_evidence_id="declared-fuel-flow-and-pressure-operating-law",
    maximum_evaluations=10000,
)
trace = integrate_shaft_transient(shaft_inputs, gas_path_feedback=feedback)
```

The application provides all three callbacks:

- `phase_factory()` returns a fresh native phase admitted by the existing
  mapped Brayton runner. Reusing one phase object between ODE evaluations is
  rejected before the next native run.
- `corrected_speeds(time_s, omega_rad_s)` returns the two corrected-speed
  coordinates in the compressor and turbine map units. No equality between
  physical rad/s and corrected map speed is inferred.
- `operating_inputs(time_s, omega_rad_s, compressor_speed, turbine_speed)`
  returns `MapMatchedBraytonInputs`, using the mapped coordinates and the same
  speed-mapping evidence identity. The application declares the remaining
  pressure ratio, air flow, hydrogen feed and corrected-flow conventions.

The existing map runner retains flow/efficiency admission and native gas-path
thermochemistry. A callback that ignores the provided speed coordinates cannot
silently substitute a different map point. Hidden state inside user callbacks
remains the application's responsibility; callbacks must describe a repeatable
quasi-steady operating law on the solver's trial clock.

## Energy and results

For rotor inertia `J`, the existing state equation remains

`d(0.5*J*omega**2)/dt = P_turbine - P_compressor - torque_load*omega - P_losses`.

The native cycle's turbine and compressor specific works are scaled by its
declared inlet-air mass flow in the existing map composition. No net shaft
power is substituted for either gross term. The scheduled turbine/compressor
arrays must contain zeros when feedback is selected, preventing simultaneous
schedule and gas-path contributions. Load torque, Coulomb loss and viscous
loss remain accounted for once by the rotor integrator. Any additional
losses or auxiliary consumers must not already be included in those gross
gas-path powers without an explicit separate model contract.

`trace.gas_path_feedback` retains the original feedback object and
`trace.gas_path_evaluations` retains each actual trial time, physical speed,
corrected-speed pair, native phase and `MapMatchedBraytonRun`. Trial evaluations
may be repeated or out of chronological order because they include rejected
adaptive steps. They must not be treated as accepted source/operation samples.
The rotor trace's normal output clock and cumulative work remain authoritative.

Map-domain or native failures propagate as `ShaftFeedbackEvaluationError`,
which retains the original cause and completed *trial* evaluations. It does not
claim an accepted shaft prefix when SciPy aborted inside a callback. The
evaluation budget limits the number of retained native runs. No clipping or
map extrapolation is performed: an internal trial can leave a map's domain
before a speed event is localized, and that remains a failure. Choose time-step
limits and map/speed envelopes appropriate to the application.

## Independent public references

The mechanical power-to-rotor relationship and the separation of dynamic
mechanical losses from turbine/compressor powers are discussed in
[Argonne ANL-ART-154, section 3.2.8.2](https://publications.anl.gov/anlpubs/2018/10/146715.pdf).
Native phase state and equilibrium ownership follow the
[Cantera 3.2 thermodynamic API](https://www.cantera.org/3.2/python/thermo.html).
This project reuses its existing shaft/cycle implementations; no external
software, numerical example or coefficient set is copied.
