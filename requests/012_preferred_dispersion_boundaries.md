# Preferred HyRAM / SLABx-LH2 source and compatibility contracts

Status: actionable local request after actual preferred-engine execution.
Targets: caller's HyRAM integration/fork, SLABx-LH2 and PRISM. No external changes/messages.

## Actual reproduction

Run `scripts/check_preferred_dispersion.py` with the separate native targets described
in docs/PREFERRED_DISPERSION.md and requirements/native-preferred-dispersion.txt.
Versions and full Python-tree/host fingerprints are in research/preferred_dispersion.md.
Keep GPL-3.0-only HyRAM and MIT SLAB-family rights/ownership distinct; do not copy native
solvers into this host. Actual native objects and factories are the Python boundary.

HyRAM 6.1 with SciPy 1.18.1 raises `dopri5._solout()` positional-argument TypeError.
The checked SciPy 1.16.3 target executes without a callback patch. Publish compatible
requirements or adapt the native integrator using an upstream-supported API; verify
numerical results across the change instead of broadly silencing version errors.

For normal H2 at 2 MPa/300 K through a 2 mm native Cd=0.8 orifice, calm air at
101325 Pa/293.15 K, native default lambda=1.16, the expanded plug carries
0.00309566981064 kg/s. The established Gaussian carries 0.00237396473540 kg/s;
its subsequent maximum drift is approximately 1.63e-10 kg/s. The host definition is
the integral of rho*Y*V over the native Gaussian radial section, consistent with the
native species transport equation. The initialization gap is about 23.31%.

Request an independently checked plug-to-established-profile closure preserving H2 mass,
momentum including pressure thrust where appropriate, total energy and the actual
thermodynamic/geometry basis. Return stage ledgers. Do not fit lambda or multiply final
concentrations to hide the source mismatch. Retain both the original default and corrected
source under versioned identities for scientific comparison. The host currently rejects
the failing original source case; this is distinct from a general field-accuracy claim.

### Version-pinned mass-gap investigation update — 2026-10-29

A read-only review of official HyRAM public `master` suggests the plug-to-Gaussian
`PlugNode.establish()` conversion as a plausible place to investigate: the reviewed
conversion derives Gaussian state from plug and ambient fields without an evident explicit
solve for integrated mass, axial momentum, or total energy. This is not a confirmed diagnosis
for installed HyRAM 6.1 because its exact source revision has not been pinned against that
branch. Keep the host fail-closed mass gate. First identify and inspect the precise 6.1 source;
then test any candidate initialization against independently computed mass, momentum and
total-energy ledgers under declared profile and thermodynamic assumptions. Do not tune lambda
or scale downstream concentration to force agreement.

## Cross-engine source boundary

- One selected owner performs choking and near-field expansion. Accept a declared native
  physical plane without re-choking it, or explicitly own the entire upstream pipeline.
- Preserve composition, phase/spin/reference, pressure basis, velocity/momentum, enthalpy
  plus kinetic energy, effective/geometric areas and coordinate transformation.
- Keep actual source/trajectory/profile objects available without a serialization step.
  Coordinate and observation operators must not replace whole-mixture mass with gas mole
  fraction silently. Preserve error/termination and raw diagnostic results.

## SLABx-LH2 finite-source work

The current host steady-vapor bridge preserves constant rate, fixed footprint and finite
duration from IntervalMassSource. Request a native nonstationary interface for arbitrary
interval integrals, changing area/state, absolute clock and isolated residual emissions.
Do not average a variable source, invent a ground deposition fraction or double-count the
terminal endpoint. Return material/energy/momentum accounting and native plume/puff clock
meaning. Expose source initial-state/used-area changes independently of numerical success.

Review native SourceLedger.to_evaporating_pool: the reviewed implementation checks varying
area and unresolved liquid but does not reject differing state mass rates and does not pass
the stored temperature into its pool constructor. The host therefore does not use that
conversion for a variable or thermally inconsistent history. Add negative acceptance cases
for both so a successful constructor cannot discard physically required inputs.

### Host-side interim screening route

The host now exposes `dispersion.run_preferred_lh2_quasi_steady_slices` and
`adapters.slabx_lh2.run_slabx_lh2_quasi_steady_slices`. They map every positive-mass
finite vapor bin to an independent native steady run, retain original bin edges and mass,
and leave zero-mass bins without a native run. Shared or per-bin footprints and caller-supplied
thermodynamic-state projections are retained with evidence identities. The result explicitly
reports that plume memory is absent and verifies that source/native outputs remain unchanged.
Each native run now keeps a dimensioned requested/constructed/used audit for rate, duration,
area, effective temperature and mass, with caller-configurable acceptance tolerances. Native
boiling-temperature clamps are exposed and rejected under the default gate rather than silently
relabeling the source state.
This route is only for per-bin screening and does not satisfy this
request's transient-source requirement; the receiving native implementation must still
preserve evolving plume/puff state, source clock, footprint and material/energy/momentum
ledgers across release changes and isolation.

The host now exposes `SLABLH2SnapshotSeries.source_bin_ledger` as a typed, freshness-
checked view of each parent source interval and its corresponding independent native-run
slot, including zero-mass intervals. This improves handoff of source timing/mass/status
to caller-owned analysis without adding concentration-time interpolation or plume memory;
the native transient-source requirement remains open.

The host receipt now rejects a forged or shifted native snapshot window even when its
rate, duration and mass still match the parent bin. Every positive-mass run must retain
the parent's exact absolute interval edges. The deferred contract is authored but has
not been executed. This clock-alignment guard does not add plume memory or upgrade the
snapshot series into a transient solution.

### Host-side plug-to-Gaussian balance audit — 2026-10-30

`h2physics.adapters.hyram_transition` now captures immutable caller-supplied radial
snapshots for the expanded-plug exit and Gaussian entry, retains the original native
source/run identity, and independently recomputes hydrogen and total-mixture mass,
axial momentum including ambient-referenced pressure thrust, and excess enthalpy plus
kinetic-energy flux. Separate budgets are required for each closure and its numerical
quadrature error. Missing interplane source, entrainment, force, energy or required
property data remain `incomplete`; source values are never substituted with zero.
The module does not call HyRAM, produce trusted same-run snapshots, change its
initialization or repair the observed mass mismatch. The deferred synthetic case
`hyram-plug-to-gaussian-transition-ledger` is listed in both cluster plans and has
not run. Same-run native provider support, radial quadrature refinement, source
parameter matrix and independent applicable observations remain open.

The HyRAM finite-source receipt now also binds its mass/enthalpy budgets and ledger
scalars after admission. A changed tolerance cannot silently become the new receipt
baseline; nonfinite enthalpy ledger entries are rejected at construction. This closes a
host metadata-integrity gap only and does not alter native mass or energy results. Its
negative contract is deferred.

## Acceptance

1. Reproduce the original positive/negative cases and fingerprints before changing code.
2. Run a fresh compatible environment and preserve native result identities/units.
3. Check mass, momentum and energy across every source stage and the downstream profile;
   resolve the authored Gaussian-entry mismatch within declared fixed budgets.
4. Preserve finite total mass and source timing during rate/area/state changes and isolation.
5. Apply the completed SLAB w_c/u premise gate; nonfinite diagnostics fail closed.
   The authored 5 m/s source case passes this gate; 0.2 m/s is rejected, without fallback.
6. Compare independent applicable gas/cold-cloud observations with predeclared targets.
   Numerical gates or an old library validation record alone do not qualify the new boundary.
