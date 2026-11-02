# HyRAM plug-to-Gaussian source closure: receiving implementation plan

## Scope and owner

The unresolved high-pressure gas-source discontinuity is inside the native HyRAM
plug-establishment transition. Keep choking, notional expansion, and jet physics
owned by the selected HyRAM provider. The host package must continue rejecting a
source that fails its mass gate; it must not fit `lambda`, rescale a concentration
field, or relabel a rejected result as accepted.

This plan specifies a receiving-side native change and a host verification path.
It is not a new plume solver or a claim that the existing Gaussian solution has
been corrected.

## Required source snapshots

The native provider should expose immutable, same-run snapshots at the expanded
plug exit and Gaussian entry. Each snapshot must retain the exact source object,
plane identifier, thermodynamic model/reference, mixture fractions, radial profile
definition, integration cutoff, geometry, and numerical quadrature identity. The
host should be able to calculate diagnostics from those snapshots without rerunning
the source or relying on mutable native internals.

For each plane, report these SI fluxes with sign convention and ambient reference
stated explicitly:

- Hydrogen mass: `integral(rho * Y_H2 * u_n dA)`.
- Mixture mass: `integral(rho * u_n dA)`.
- Axial momentum: `integral((rho * u_n^2) + (p - p_ambient)) dA` over the declared
  control section. If the profile does not define pressure over that section, mark
  the momentum ledger unavailable instead of substituting centerline pressure.
- Excess enthalpy and kinetic-energy transport relative to the declared ambient
  reference: `integral(rho * u_n * ((h_mix - h_ambient) + 0.5 * |u|^2)) dA`,
  with mixture enthalpy computed by the same declared native caloric model at each
  radial state. Record whether potential energy is excluded.

The provider must retain both the original default result and any new
mass-conservative initialization as separate versioned results. No correction may
change the original result in place.

## Acceptance gates

1. Pin the exact HyRAM source revision and dependency versions used for every run;
   the public `master` review is not evidence for the installed 6.1 implementation.
2. Reproduce the current 2 MPa, 300 K, 2 mm opening case and preserve the current
   original-result fingerprints and approximately 23.31% Gaussian-entry H2 deficit.
3. For a candidate initialization, compare both planes' H2 mass, total mass, axial
   momentum, and total-energy flux under one explicit set of caller-approved
   budgets. Missing pressure/caloric fields fail the corresponding gate closed.
4. Halve radial quadrature spacing and tighten the tail cutoff independently.
   Each ledger change must be below its own predeclared numerical-integration budget;
   report truncation and quadrature errors separately from plane-to-plane residuals.
5. Run an unchanged downstream integration from the Gaussian entry. Separate the
   initial plane jump from subsequent ODE transport drift and retain raw native
   outputs on both success and rejection.
6. Cover low/high pressure, opening size, ambient state, and at least one case with
   a substantially different pressure ratio in separate parallel jobs. A result
   that closes only the authored case is not a general source-closure result.
7. Compare the accepted candidate against independent applicable observations
   before assigning validation status. Numerical conservation alone is a software
   gate, not experimental validation.

## Host integration contract

After the native owner exposes the above snapshots, the host may add a read-only
receipt that checks their identities and recomputes the four integrals. Until then,
there is no defensible host-side transformation that can repair the missing source
mass without duplicating or changing native jet physics. Existing strict rejection
remains the correct behavior.
