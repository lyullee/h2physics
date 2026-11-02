# Gas-state derived diagnostics

`h2physics.thermo.GasStateDiagnostics.from_state()` computes convenient
dimensionless and transport combinations from an existing `ThermoState`. Supply
the specific gas constant in J/(kg K) explicitly. This makes the composition and
mass-basis choice visible for frozen mixtures, and keeps the property provider as
the owner of density, heat capacity, viscosity and conductivity.

The result exposes compressibility factor `p/(rho R T)`, the state's existing
`cp/cv` ratio, Prandtl number `mu cp/k`, thermal diffusivity `k/(rho cp)`, and
kinematic viscosity `mu/rho`. A quantity remains `None` when the state lacks one
or more required transport/caloric fields. Only the `gas`, `supercritical`, and
`supercritical_gas` phase labels are admitted; a two-phase mixture must first be
handled by a phase-aware owner. No ideal-gas behavior is asserted by reporting
compressibility, and these combinations do not establish a discharge, heat-transfer
or safety correlation.

The diagnostic retains a signature over its source state, gas constant and
derived fields. Call `require_current()` before passing a saved diagnostic to
another module; copied or edited projections are rejected. This protects object
consistency but does not authenticate the caller's state or qualify its provider.

The definitions follow the property conventions documented in the
[NIST REFPROP manual](https://www.nist.gov/system/files/documents/srd/REFPROP8_manua3.htm),
including `Z=p/(rho R T)`, thermal diffusivity `k/(rho cp)`, and Prandtl number
`mu cp/k`. This package calculates only these definitions from an already supplied
native state; it neither copies a property model nor selects coefficients.

The deferred contract `thermo-gas-state-derived-diagnostics` is registered for
Nurion. It has not been run and does not qualify any underlying EOS or transport
property.
