# Isothermal pipeline-wave observation mapping

`h2physics.adapters.isothermal_pipe_observations` compares caller-owned
pressure and mass-flow histories with an existing
`IsothermalPipeWaveTrace`. It adds an observation operator only; it does not
introduce another pipe solver or acquire/interpret a publisher dataset.

## Python contract

Create one `PipelinePressureHistory` per absolute-pressure tap and one
`PipelineMassFlowHistory` per flow meter. Inputs are immutable one-dimensional
NumPy-compatible arrays:

- pressure and standard uncertainty are absolute Pa and must be positive;
- flow and its standard uncertainty are kg/s; signed flow is positive toward
  increasing pipe coordinate `x`;
- times are strictly increasing seconds already expressed on one declared
  clock;
- channel, clock, source-evidence and sensor-mapping identities are required;
- sensor positions are axial metres in the same frame as the pipe model.

Call `compare_isothermal_pipe_observations(trace, pressure, flow, ...)` with
the model clock identity and an identity for the evidence aligning the clocks.
The operator requires every measurement time to exactly match a retained trace
sample. It performs no temporal interpolation, time offset, clock conversion or
resampling. Pressure is linearly interpolated between retained cell-centre
values and flow between retained face values; spatial extrapolation beyond the
represented cells/faces is rejected. Weighted RMS values divide pointwise
residuals by the caller-supplied standard uncertainties. They are descriptive
metrics, not hypothesis tests or acceptance gates.

```python
from h2physics.adapters import (
    PipelineMassFlowHistory,
    PipelinePressureHistory,
    compare_isothermal_pipe_observations,
)

pressure = PipelinePressureHistory(
    time_s=measurement_time_s,
    pressure_pa=absolute_pressure_pa,
    standard_uncertainty_pa=pressure_sigma_pa,
    tap_position_m=25.0,
    channel_id="tap-2-pressure",
    clock_id="campaign-clock-1",
    source_evidence_id="dataset-and-file-digest",
    sensor_mapping_evidence_id="tap-survey-record",
)
flow = PipelineMassFlowHistory(
    time_s=flow_time_s,
    mass_flow_kg_s=measured_mass_flow_kg_s,
    standard_uncertainty_kg_s=flow_sigma_kg_s,
    meter_position_m=0.0,
    channel_id="inlet-flow",
    clock_id="campaign-clock-1",
    source_evidence_id="dataset-and-file-digest",
    sensor_mapping_evidence_id="meter-installation-record",
)
comparison = compare_isothermal_pipe_observations(
    native_trace, pressure, flow,
    model_clock_id="campaign-clock-1",
    clock_alignment_evidence_id="approved-common-clock-map",
)
```

## Scope and evidence boundary

This API accepts already parsed, rights-reviewed observations. It is not a
checksum-verifying source reader, does not determine channel units or gauge vs
absolute pressure from headers, and cannot establish that a provided clock or
sensor mapping is correct. Do not attach publisher file identity to values
unless the caller has independently verified the source file and schema.

The deferred Hangang case `hydrogen-pipeline-wave-observation-operator` checks
synthetic array admission, spatial mapping and rejection of off-grid times. It
does not compare to a real experiment, estimate parameters, account for sensor
response, propagate covariance, or validate the EOS/pipe-wave method. The model
formulation and its public governing-equation source are documented in
[ISOTHERMAL_PIPE_WAVES.md](ISOTHERMAL_PIPE_WAVES.md). Request036 remains open
until a rights-cleared H2 pipe dataset with identified channels and calibration
metadata is acquired and independently compared using held-out runs.
