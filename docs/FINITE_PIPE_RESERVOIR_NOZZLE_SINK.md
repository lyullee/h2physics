# Finite pipe-reservoir nozzle sink

`FiniteReservoirNozzleCoupling` connects one `finite_reservoir` endpoint in the
branched isothermal pipe-wave model to the shared
`HomogeneousIsentropicNozzle`. It adds no nozzle correlation or dispersion
solver. The nozzle property provider is caller supplied.

## Coupled update

At each internal network step, the solver evaluates nozzle outflow from the
current reservoir mass, fixed volume, and declared temperature. It debits that
start-of-step nozzle rate over the same step used by the pipe finite-volume
update:

```text
m_next = m_current - dt * (F_pipe_out + m_dot_nozzle_start)
```

`F_pipe_out` is the signed endpoint Rusanov flux already applied to the pipe;
positive flow leaves the reservoir and enters the pipe. `m_dot_nozzle_start`
is nonnegative outward release. The stock bound is checked on the combined
update. There is no clipping or implicit flow limiter. This is an explicit
first-order time discretization. If either the inventory or network mass
ledger does not close within the model contract, the step is rejected.

The nozzle state is reconstructed from the finite reservoir pressure and fixed
temperature using the supplied caloric provider. The caller must identify the
exact network EOS and caloric basis mapping, provide mapping evidence, and set
both relative and absolute density tolerances. Pressure, temperature, phase,
basis, and density agreement are checked at each sampled reservoir state.
Unsupported phases, density mismatch, wrong node/edge/clock, and EOS identity
mismatch are errors.

The nozzle result after each accepted step is retained at the new endpoint as a
diagnostic sample and reused as the next interval's start value. The accepted
interval rate is therefore the exact cached sample that was debited.
`IsothermalPipeNetworkTrace.project_nozzle_source()` applies
the `left_hold` rule, so its integrated source mass equals the exact leakage
mass debited from the reservoir. That projection also requires explicit
representative-state, quadrature, and state-projection evidence.

## Using the source projection

```python
trace = model.simulate(
    initial_pressure_pa=pressure,
    initial_velocity_m_s=velocity,
    time_samples_s=request_times,
    finite_reservoirs={reservoir.node_id: reservoir},
    finite_reservoir_nozzles={reservoir.node_id: coupling},
)
source_projection = trace.project_nozzle_source(
    reservoir.node_id,
    representative_state=caller_selected_state,
    quadrature_evidence_id="record-of-left-hold-choice",
    state_projection_evidence_id="record-of-representative-state-choice",
)
```

`source_projection` is the existing `NozzleSourceProjection`; it carries the
source clock, location, opening, sampled nozzle energy and mass, and a finite
`IntervalMassSource` projection. The representative state remains a caller
choice because the finite-source consumer uses one state across the window.
The sampled history may vary with reservoir pressure; the state projection
does not reconstruct a time-varying thermodynamic state inside that consumer.

This handoff prepares a finite nozzle-plane source. It does **not** execute
HyRAM dispersion or consequence models. Existing callers may use the projected
state/source contracts where their solver interface supports them; a dynamic
time-varying HyRAM integration is not asserted here.

## Scope

- One fixed-area nozzle per selected finite-reservoir endpoint.
- Fixed reservoir volume and declared isothermal temperature.
- Shared finite-volume pipe solver, Rusanov endpoint exchange, and shared
  nozzle solver.
- Explicit opening fraction, back pressure, source location/frame, clock,
  network EOS identity, caloric basis, mapping evidence, and density tolerance.
- First-order left-hold withdrawal coupling; post-step nozzle samples are
  diagnostic only.

The model does not include reservoir energy depletion, heat transfer, wall
friction inside the reservoir, valve actuation, time-varying opening, a leak
path through pipe wall, pressure regulation, external jet/dispersion, or a
HyRAM run. The isothermal inventory model remains a prescribed-temperature
mass balance, not a vessel blowdown energy model.

The deferred synthetic contract is
`validation.cases.finite_reservoir_nozzle_sink`. It checks leak debit, source
projection closure, network conservation, identity rejection, and retained
provenance when run by the validation harness. No local or remote validation
result is implied by this documentation.

The receiving HyRAM contract for using this finite, potentially time-varying
source is documented in [Request 037](../requests/037_hyram_transient_finite_source.md).
The request keeps stationary native orifice flow separate from an already
debited host source and requires transient plume memory to be identified
separately from independent quasi-steady snapshots.
