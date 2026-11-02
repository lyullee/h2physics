# Finite source projection from dynamic adsorption outflow

`bind_adsorption_dynamics_to_finite_source()` maps a completed, single-species
H2 adsorption-vessel trajectory to the shared `IntervalMassSource` API. The
accepted cumulative outlet-mole ledger defines each interval's mass using the
gas binding's declared H2 molar mass. The result retains the original trace,
source location, state and projection evidence; `require_current()` reconstructs
the bins and integrated enthalpy receipt from those owners.

```python
from h2physics.adapters import bind_adsorption_dynamics_to_finite_source

handoff = bind_adsorption_dynamics_to_finite_source(
    trace,
    location=source_location,
    representative_state=representative_h2_state,
    clock_alignment_evidence_id="case-clock-alignment",
    state_projection_evidence_id="case-mean-outlet-state",
    energy_tolerance_j=caller_budget_j,
)
handoff.require_current()
finite_source = handoff.source
```

The adapter accepts only a completed trace whose declared gas composition is
exactly `("H2",)`. The caller supplies the source clock and must evidence its
alignment to the model's physical-second time coordinate. `IntervalMassSource`
holds one representative state for the complete window, so the native
integrated outlet enthalpy is compared with `total_mass * representative_h`;
the caller declares the allowed absolute and relative discrepancy. A failed
budget, incompatible property basis, missing evidence, nonpositive H2 mass, or
stale model trace is rejected. The representative state is an explicit output
projection, not an assertion that the bed actually held constant pressure or
temperature while discharging.

Deferred Hangang case
`adsorption-dynamics-finite-h2-source-handoff` is registered in the existing
`finite-adsorption-vessel` profile through `validation.cases.adsorption_dynamics`.
It uses the synthetic authored vessel fixture and checks mass bins, enthalpy
budget, basis rejection and stale-owner detection. The profile may also run
other adsorption-vessel cases that require PSA-Dyna. This contract does not add
breakthrough fronts, a product valve, pressure control, conditioning, piping,
nozzle flow, dispersion or experimental qualification.
