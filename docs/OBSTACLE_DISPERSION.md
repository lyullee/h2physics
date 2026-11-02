# Native obstacle-resolved dispersion — implemented, unverified

No CFD binary was installed, imported or executed locally. No scientific case,
example, benchmark or test was run. Hangang is the active target for parallel
scientific verification; this module remains unverified.
Four cases are prepared under profile `obstacle-dispersion`; none is a pass.

The optional runner calls the actual external NIST Fire Dynamics Simulator6.11.1,
release revision `ff928dbf68a2623ced3a007be75391c6dc6c9f90`. FDS owns the 3D low-Mach
momentum, species, pressure and sensible-enthalpy solution around actual solid
obstacles. The host generates original native inputs and audits actual process/
file outputs. It adds no CFD transport, turbulence, EOS, nozzle or combustion
solver. This is a separate obstacle-resolved level and never a fallback for the
preferred HyRAM gaseous release/dispersion or SLAB liquid-origin chain. A supplied
expanded gas boundary does not verify its upstream accident/source/fire chain.

## Selected native API and rights

The official [NIST download page](https://pages.nist.gov/fds/downloads.html) and
[release repository](https://github.com/firemodels/fds/releases/tag/FDS-6.11.1)
identify the selected maintained release. The official user and technical guides
are release assets there. Source inspection used the pinned user guide, native
namelist reader, output writer, output quantities/units and numerical source.
No native source, guide prose, tutorial deck, figures or property coefficient
tables are bundled. See the separate source/rights receipt for exact hashes.

The [native license notice](https://github.com/firemodels/fds/blob/FDS-6.11.1/LICENSE.md)
permits use/copy/distribution under its notice and identifies NIST employee work
as unprotected by US copyright. This is recorded as the NIST notice, rather than
assuming a worldwide MIT/GPL license. The executable/runtime is separately
provisioned and needs its own binary SHA and transitive-runtime rights review.
No compiled binary is part of this package.

OpenFOAM14/Foundation and OpenCFD-v2606 were identified as maintained alternatives.
They are not installed or selected as hidden fallbacks. This increment concentrates
on one inspected native API and its directly exposed mass/enthalpy/geometry outputs.

```python
engine = FDSEngine(
    absolute_native_binary, reviewed_binary_sha256,
    executable_evidence_id, threads=declared_threads, timeout_s=declared_timeout)
result = run_obstacle_dispersion(case, engine, audit_budgets, work_directory=workspace)
actual_completed_process = result.native_process
actual_output_bytes = result.artifacts.read_bytes(native_file_name)
native_device_table = result.device_table
```

`render_fds(case)` supplies reviewable native namelist text. The runner creates
a new isolated case directory, writes that text and executes the selected binary
with an argument list and no shell. It verifies executable SHA before/after,
unchanged input, native normal-completion message and native compiled git/version
output. A missing binary, error, timeout, unsupported output or failed audit remains
an error with actual process/timeout cause, directory, artifacts and rejected
result where one exists. No zero/fabricated output or alternative engine is supplied.

## Geometry, source, species and boundary scope

`CFDMesh` is one truly3D uniform Cartesian mesh. Positive rectangular impermeable
obstacles must be inside its domain, nonoverlapping and aligned with grid faces
within the explicit geometry tolerance. The native SMV obstacle IDs/count/bounds
are checked after execution; declared geometry is not silently snapped by the host.
Native fluid volume is independently requested and compared with domain volume
minus the declared solids. The host's six-neighbor connectivity check admits one
connected fluid pressure zone; it is geometry validation, not a transport solver.

`HydrogenCFDSource` specifies a finite nonnegative piecewise-linear kg/s history,
post-expansion temperature in K, an x-min boundary patch in m, source evidence,
clock/frame and native species/reference identity. The patch area sets native
species mass flux. FDS receives its actual `SPEC`/`SURF`/`VENT`/`RAMP` inputs and
computes the resulting velocity/density/thermodynamics. No high-pressure choking,
flashing, liquid hydrogen or para-H2 conversion is inferred. The source must be
an independently admitted warm subsonic gas boundary. Native source temperature
uses Celsius at the interface; the Python API converts K explicitly. Its face
heat-transfer coefficient is explicitly zero, so there is no separate prescribed
hot-wall convective heat source in addition to source enthalpy.

FDS built-in HYDROGEN and dry background AIR provide the caloric/property data.
Spin thermochemistry is unresolved. Their native sensible-enthalpy reference is
not relabeled CoolProp HEOS, para-hydrogen or an arbitrary user caloric zero.
Native species coefficients remain inside the selected engine. No `REAC`, solid
fuel, radiation transport or chemical ignition model is activated by this deck.
Unrequested native combustion is an admission failure.

The first reference is a sealed diagnostic enclosure with explicit native
adiabatic wall/obstacle boundaries and finite H2 injection. It is not an atmospheric
wind/open-boundary model or a qualified facility heat-transfer boundary. NIST's
user guide identifies adiabatic surfaces as diagnostic approximations. The native
pressure work associated with the closed pressure zone remains in the energy
ledger. Native zone topology, pressure variation, speed and temperature limits
are checked. The all-gas warm domain is250–400K, with tighter caller limits allowed.
Relative pressure and low-speed budgets require application evidence; FDS does not
resolve shocks or supersonic jets.

`simulation_mode` explicitly selects native `DNS` or `LES`; there is no automatic
switch. In this release, LES selects the native Deardorff model and native flux
numerics; DNS selects its native molecular/numerical options. Grid convergence,
wall resolution, buoyancy, molecular transport and turbulence qualification remain
necessary. An engine selection or obstacle picture does not establish resolved
DNS/LES accuracy. Initial native velocity noise is explicitly disabled for the
authored reference; no wind is silently inferred.

## Native output clocks and independent admission

Native `mass.csv` values are interval means in the inspected writer. They are
retained as artifacts and are not treated as instantaneous inventories. Separate
native `DEVC` outputs with instantaneous temporal statistics provide H2 and total
mass, sensible enthalpy, fluid volume, species extrema, speed, temperature and
receptor H2 mole fractions. Native headers and units are checked exactly.

The `hrr.csv` outputs are means over the preceding native output interval. Their
mass flow and heat terms are integrated using those actual interval widths and
right-endpoint mean values. Device and energy clocks must align and cover the
complete native0..end support; the runner does not silently interpolate one ledger
onto another. Native relative time and the explicit Python clock origin remain
distinct. Receptor coordinates use the declared frame and must lie in fluid cells.

The strict residuals compare: H2 inventory versus actual native source mass;
background-air mass conservation; actual source mass versus the original finite
rate history; instantaneous native sensible-enthalpy change versus integrated
native total source terms; native enthalpy-change-rate integral versus those same
terms; and native versus declared free volume. The native total terms retain
pressure work, source convection/diffusion, wall conduction and other reported
terms. A sensible-enthalpy ledger is not stored total internal or chemical energy.
This audit does not assign a combustion yield or explosive energy.

All original CSV tables and scalar slice files remain available. The runner
requests native binary H2 slices on three planes and retains them with the SMV
geometry and process output. It does not invent a NumPy3D field from receptor
samples. Actual native FDS/Smokeview or separately reviewed readers can consume
those files through Python paths/bytes. Native internal positivity limiting and
unreported substeps are not observable from these outputs; sampled extrema or a
closed global ledger do not prove their absence. No host clipping/normalization
of negative results occurs.

## Deferred checks and limitations

The four dormant handlers prepare zero source, finite pulse, obstacle/no-obstacle
comparison and mesh refinement. They use original inputs and actual executable
results, record host/binary/output provenance and re-raise rejected native cases.
Comparison-only interpolation across different runs is explicitly labeled and is
not native output. The supplied thresholds are prospective numerical gates, not
results. Source/geometry/clock and native failure negatives, stronger field-based
mesh/time studies and matched hydrogen-obstacle experiments remain follow-up work.

This first closed-enclosure reference excludes validated open terrain/wind,
compressible near-field release, cryogenic multiphase flow, chemistry/fire,
complex CAD/cut-cell geometry, multiple meshes/MPI decomposition, moving obstacles,
deposition, injury, ignition probability and quantitative risk. These are not
completed by preparing an external runner or its unexecuted cases.
