# Obstacle CFD development checkpoint

Status `implemented_unverified`. No native binary/install/import/execution,
scientific calculation, case discovery invocation, example, pytest or benchmark
was performed. The external FDS runner and original inputs are written, with
strict output admission, but no computed physical acceptance exists.

Source-only investigation identified maintained OpenFOAM14/Foundation and
OpenCFD-v2606 alternatives. The selected narrower owner is NIST FDS6.11.1, release
tag FDS-6.11.1, revision ff928dbf68a2623ced3a007be75391c6dc6c9f90, published2026-07-10.
The native user guide, reader, output writer, quantity/units and numerical sources
were inspected under ignored artifacts/obstacle_provider_review/fds. Rights are
the actual NIST license notice/US government-work statement, with separate binary
and runtime review still needed. No native source/deck/table/coefficient/model
was copied into public files. No binary was downloaded or installed.

Actual integration: author native MESH/OBST/SPEC/SURF/VENT/RAMP/DEVC/SLCF namelists,
call one explicit external FDS executable with subprocess, retain its original
CompletedProcess/timeout/output directory, parse actual native CSV/SMV and enforce
mass/enthalpy/geometry/domain admission. The native engine owns momentum, pressure,
species and thermal transport. There is no transport graph, duplicate PDE/CFD
solver, synthetic output field or HyRAM/SLAB fallback. The high-pressure source
must already have an independently justified expanded gas boundary.

Static inspection established that native mass.csv is interval-averaged. The host
therefore requests separate instantaneous device integrals rather than comparing
that file to endpoint mass. Native HRR/source rates are interval means and are
integrated on their actual clock. Sensible-enthalpy inventory and pressure-work
terms retain their actual native energy meaning; no CoolProp reference/spin
conversion or combustion energy inference is made. Native SMV obstruction bounds
and native free volume are checked against original grid-aligned geometry.

The reference resolves one sealed, connected, warm dry-air/H2 gas domain with
impermeable diagnostic adiabatic obstacles. H2 mass flux, rate clock, injection
temperature, ambient pressure, gravity, model mode, grid, pressure iteration and
audit budgets are explicit. Native field extrema constrain admitted output;
unreported limiter activity/substeps remain unknown. Receptor histories and native
binary slices are retained without reconstructing a fictitious full3D field.

Prepared dormant cases/profile obstacle-dispersion: zero-source, finite-pulse,
obstacle-pair and refinement. Each must call the actual selected binary. Missing
binary/version/output, failed solver, geometry/source drift or failed ledger rejects
and retains evidence, rather than returning a schema-only pass. Their tolerance
and obstacle-effect/refinement assertions are prospective, not executed evidence.

Isolated Nurion native binary/runtime provisioning and complete license receipt
remain pending. Independent hydrogen-obstacle experiments, open boundary/wind,
strong field/time refinement, negative/error runs and facility qualification are
not supplied. Neither model preparation nor future synthetic conservation checks
complete the obstacle dispersion family or an accepted source-to-fire/risk chain.
Final static checks and hashes are reported separately at handoff.

2026-10-28 source-only compatibility change: use existing SciPy integrate.trapezoid for the same quadrature while retaining NumPy1.26 minimum. No replay or numerical acceptance performed.
