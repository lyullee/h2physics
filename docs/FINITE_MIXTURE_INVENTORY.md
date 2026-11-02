# Fixed-volume finite mixture inventory

## What this level computes

`h2physics.thermo.run_finite_mixture_vu_intervals()` advances a vessel through
caller-specified finite transfer intervals. The extensive state is the ordered
component mole vector, total fluid internal energy, and a fixed vessel volume.
At the beginning and end of each interval, a composition-specific
`CoolPropMixtureProperties` object supplies equilibrium phase packets to the
existing bounded V/U flash. A fresh provider is built whenever the overall
component inventory changes; a frozen-composition provider is never reused as
if it accepted dynamic composition.

Each interval explicitly supplies liquid and vapor inlet component moles and
their total enthalpy transfers. Liquid and vapor outlet requests are phase-total
moles. Their species withdrawals and exported enthalpies are evaluated from the
left-end accepted phase compositions and phase enthalpies. Heat and work are
signed energy transfers into the vessel. The finite-volume energy identity is

```text
U_next = U_current + H_in,liquid + H_in,vapor + Q_into + W_into - H_out,liquid - H_out,vapor
```

and species inventories follow the corresponding species-resolved inlet and
phase-selective outlet amounts. The run retains every exact accepted packet,
cumulative ledgers, flash diagnostics and the interval inputs; `require_current()`
rechecks nested admissions and all interval closures.

## Numerical meaning and limitations

This is explicit first-order finite-volume marching on caller-chosen time
endpoints. Outlet composition and enthalpy are sampled from the preceding
accepted equilibrium state. The caller must refine intervals until trajectory
changes are resolved. The present level admits only a bounded two-phase branch;
phase appearance/disappearance, branch switching, wall storage, valve laws,
continuous rate interpolation and automatic event localization are not modeled.
If a component is depleted, a phase outlet exceeds available phase stock, a
flash leaves the branch, or any interval fails, the call raises and does not
fabricate later accepted states.

The equilibrium/property engine is CoolProp HEOS. The interval update and
trajectory orchestration are Python code, not a third-party native adaptive
integrator. `energy_reference_id` must identify the common enthalpy/internal-
energy convention used by inlet data and the selected HEOS setup. The run also
checks a stable CoolProp version/backend/spin signature across changing
composition providers. The caller remains responsible for establishing that
the declared energy reference matches external stream data.

This implementation is a composable research-level owner for finite intervals,
not evidence of separator qualification. It does not qualify binary interaction
parameters, transport, heat-transfer coefficients, residence-time closures or
experimental performance. The deferred case is `finite-mixture-vu-accepted-steps`
and is intended for the configured Hangang campaign; it has not been executed.

## API sketch

```python
from h2physics.thermo import (
    MixtureProviderTemplate,
    MixtureVesselInterval,
    run_finite_mixture_vu_intervals,
)

template = MixtureProviderTemplate(
    species=("H2", "N2"),
    molar_masses_kg_mol=(2.01588e-3, 28.0134e-3),
    coolprop_fluids=("Hydrogen", "Nitrogen"),
    energy_reference_id="caller-defined-common-reference-v1",
)
```

Populate a `MixtureVesselInterval` for each positive end time, with species-
ordered inlet mole transfers, integrated inlet enthalpies, phase-total outlet
moles, and signed heat/work. Then pass explicit V/U tolerances, pressure and
quality bounds, multiple branch seeds, and the branch evidence identity to the
runner. The returned `FiniteMixtureVesselRun` exposes `accepted`, `intervals`,
and `require_current()` directly as Python objects; serialization is optional
application code.

## Deferred evidence

Cluster verification must cover at least: no-transfer invariance; small
composition-changing feeds; liquid-only/vapor-only withdrawal component and
enthalpy ledgers; failed branch and depleted-phase rejection; accepted-history
staleness; and step-refinement behavior. Independent mixture data and comparison
with a suitable finite-vessel reference remain necessary before application
claims. No local scientific calculations or tests were run while authoring this
module.
