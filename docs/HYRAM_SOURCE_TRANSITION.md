# HyRAM source-transition audit

`h2physics.adapters.hyram_transition` audits two radial planes returned by one
HyRAM run: the expanded plug exit and the established Gaussian entry. It does
not execute or modify HyRAM. The host measures a possible source transition and
keeps the original native result available to the caller.

## Inputs and assumptions

Capture each plane with `capture_hyram_radial_plane()`. The caller supplies the
annular area weights chosen for that plane, source revision/run/transition IDs,
native source object, radial profiles, axis and normal, common ambient pressure
and enthalpy, thermodynamic/composition identities, profile identity, quadrature
identity and radial cutoff. Capture copies numeric profiles into immutable
storage and hashes them. The exact native source object is retained by identity.

The host cannot prove that a caller copied values from the claimed native run.
The caller's native integration must supply trustworthy same-run snapshots and
quadrature/error estimates. The audit does not derive annular weights, the
ambient entrainment, momentum force or energy transfer. Those inputs must be
declared independently or their affected balance remains `incomplete`.

The supported scalar momentum expression requires the plane normal aligned with
the declared jet axis. `normal_velocity_m_s` and `axial_velocity_m_s` must agree;
`speed_squared_m2_s2` may include a resolved radial component. Full vector stress
or off-axis planes are outside this contract. Static pressure is absolute, the
momentum reference is common ambient pressure, and specific enthalpy is measured
against the same ambient caloric reference on both planes. Potential energy is
not included. These simplifications are explicit input contracts, not automatic
assumptions about a HyRAM result.

## Fluxes and closures

For each captured radial quadrature row `i`, the audit calculates

```text
H2 mass flow = sum(rho_i * Y_H2_i * u_n_i * delta_A_i)
mixture mass flow = sum(rho_i * u_n_i * delta_A_i)
axial momentum flow = sum((rho_i * u_n_i * u_x_i + p_i - p_ambient) * delta_A_i)
excess energy flow = sum(rho_i * u_n_i * ((h_i - h_ambient) + speed_i^2/2) * delta_A_i)
```

Each plug-to-Gaussian balance is `outflow - inflow - declared_transfer`.
H2 inter-plane reaction/source, ambient-air entrainment, external axial force,
and external energy transfer are separately supplied. A missing transfer,
pressure profile or enthalpy profile cannot silently become zero. Every closure
has a residual budget and a separate quadrature-error budget. A ledger is
`accepted` only when both pass, `rejected` when a complete check exceeds either
budget, and `incomplete` when required evidence or an error estimate is absent.
The overall state is incomplete if any ledger is incomplete, rejected if all
are complete and any fail, and accepted only if every balance passes.

```python
from h2physics.adapters.hyram_transition import (
    HyRAMTransitionBudgets,
    audit_hyram_source_transition,
)

budgets = HyRAMTransitionBudgets(
    h2_residual_kg_s=1e-7,
    mixture_residual_kg_s=1e-7,
    momentum_residual_n=1e-5,
    energy_residual_w=1e-3,
    h2_quadrature_error_kg_s=1e-8,
    mixture_quadrature_error_kg_s=1e-8,
    momentum_quadrature_error_n=1e-6,
    energy_quadrature_error_w=1e-4,
)

audit = audit_hyram_source_transition(
    plug_snapshot,
    gaussian_snapshot,
    h2_interstage_source_kg_s=0.0,
    ambient_entrainment_kg_s=measured_or_native_entrainment,
    external_axial_force_n=declared_axial_force,
    external_energy_rate_w=declared_energy_transfer,
    budgets=budgets,
    quadrature_errors=(h2_error, mixture_error, momentum_error, energy_error),
)
audit.require_current()
```

Budget values above are illustrative units only and are not recommended
acceptance values. They must be declared before evaluating an actual case.

## Scope and validation

The conservation forms follow the control-volume treatments of mass, momentum,
and energy described in the NASA Glenn [mass-flow rate](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/mass-flow-rate-equations/),
[momentum](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/conservation-of-momentum-2/),
and [energy](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/conservation-of-energy/)
references. The pressure correction uses the declared common ambient reference.
The implementation does not fit jet-spread parameters, rescale Gaussian
concentrations or produce a corrected initialization.

The deferred `hyram-plug-to-gaussian-transition-ledger` case checks synthetic
identity, signs, incomplete terms, missing property profiles and independent
budgets. It has not been executed. A passing synthetic contract is not a native
HyRAM reproduction or an independent experimental comparison. See
[Request 012](../requests/012_preferred_dispersion_boundaries.md) for the pending
native snapshots, source fingerprints, quadrature refinement and parameter
matrix. No failure or acceptance status upgrades HyRAM field accuracy.
