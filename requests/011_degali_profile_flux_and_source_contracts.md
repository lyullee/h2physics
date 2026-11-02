# DEGALI profile forces, conserved fluxes and gas-source contracts

Status: actionable request following the implemented host gas/jet adapter.
Target: `lyullee/degali`. No receiving repository was edited or messaged.

## Checked native state and reproduction

MIT revision `6ead182dc19039725a0b40811b48c6d39f947790` declares version 0.3.0.
Its Python path/byte fingerprint is
`f84bb2c38e26a507a3e495005f38d8fed097d312f6a47932fe10d3cdb587220a`.
The checked PyPI 0.1.0 release is not equivalent. Actual native objects are exercised by
`scripts/check_degali_integration.py`; inputs, residuals and refinement are preserved in
`research/native_degali.md`. No external observation or coefficient fit is used.

The common host nozzle supplies 2 MPa gas through a 2 mm opening, area factor 0.8,
to 101325 Pa ambient. Native expansion preserves its effective-area pressure thrust
and source total enthalpy. Source gas is normal H2 at 300 K or para-H2 at 100 K before
the nozzle. The caller places the virtual ambient plug horizontally 2 m above ground.
Ambient is dry phase air including Ar, 293.15 K. All remaining settings are in the script.

Both default density-profile four-flux initializations fail; the normal case's relative
species error is about -0.296 and the para case's about -0.00471. Independent temperature/
composition profiles close all four initial fluxes without fitting coefficients. However,
`derivatives` still uses the analytic Gaussian-density force rather than the actual
non-Gaussian density integral available through `buoyancy_force`. This is an internal
force/profile consistency issue. It is not evidence of experimental superiority of a
different profile. The host explicitly subclasses the actual engine to replace only
that source, using the native Jacobian and radial integral.

Cold phase-profile energy also needs explicit refinement/admissibility evidence. The
original 81/161/321 sequence has maximum energy errors about 2.525/2.769/0.524 W against
a fixed 0.238 W budget; species and horizontal momentum pass at finer grids. Extra cold
refinement is recorded rather than raising the budget. Read the current report for the
latest result. An extreme DOP853 tolerance diagnostic remained incomplete when interrupted
after more than 300 observed CPU seconds; it is not a successful integration or a
recommended cure. Preserve these negative cases.
The additional 641-point run reduces the energy error to about 0.346 W and still fails
the same 0.238 W budget, despite small endpoint and species/momentum differences.

## Host contracts already available

- `expand_nozzle_gas`: actual injected expander, one existing nozzle result, explicit
  effective pressure-area closure, receiving PH/basis/phase checks and native retention.
- `ExpandedGasPlane`: native expansion, shared nozzle, pure-fluid state, predicted origin,
  explicit virtual-plane location/frame/clock and position basis.
- `JetPlane` and `axisymmetric_boundary`: explicit global section, exact native source and
  enthalpy factories, separate static relative enthalpy and absolute ambient H2 reference.
- `profile_integrated_buoyancy_type`: original optional calm-only host source correction;
  no solver copy, coefficient fit, native file modification or global property patch.
- `run_axisymmetric_jet`, `JetTolerances`, `JetAudit`: source identity, model policy,
  reference, establishment, species, horizontal momentum, energy and ground-envelope gates.
  Failed completed runs retain actual native objects through `JetCouplingError.run`.
  Malformed output schemas retain the actual object through `error.native` without a false audit.
- `NativeJetRun.radial_observations`: immutable spatial observations of complete-mixture
  Y, bulk density and T. No all-gas gas-mole-fraction interpretation or fake time axis.

## Requested receiving capabilities

1. Make the vertical source consistent with the actual selected profile. Retain any
   historical analytic-density option explicitly. Test both profile ansatzes against
   their own radial integrals. Entrainment and coflow contributions must stay separate.
2. Expose typed public section fluxes and their order/units, Jacobian or inversion,
   integrated body-force/heat/mass sources and establishment targets/residuals. Avoid
   requiring consumers to reconstruct these through protected methods or magnitude-only
   momentum. Include vector momentum and energy-reference identifiers in results.
3. Offer a robust conservative integration/projection option across phase transitions,
   with a declared residual budget and failed-step diagnostics. Consider evolving
   conserved fluxes with a native admissible profile inversion. A projection must solve
   the complete physical constraints and report adjustments; editing reported energy or
   clipping mass fraction is not a remedy. No particular numerical method is mandated.
4. Expose restartable/injectable established state, development-zone target/source fluxes,
   and an optional dense-output state evaluator with admissibility/error checks. Do not
   require an external second ODE/phase solver to continue the actual native state.
5. Add a supplied-throat expansion contract with distinct optional stream and pressure-
   force areas and explicit area basis. Preserve source static h, total energy, spin,
   quality and property reference. Accept a native property facade/callback when its
   gauge is compatible. Do not run another choking calculation for an injected throat.
6. Expose gas/condensed species mass, volume and mole fractions and phase temperature,
   plus declared probe-volume/response operators. Whole-mixture Y must remain available
   separately. State the validity/continuation of phase and enthalpy tables and reject
   unsupported states rather than silently presenting a continued table as qualified EOS.
7. Supply an explicit finite-source material clock, development transit, source start/end
   semantics and conserved puff/jet handoff. For pool sources require actual launch
   geometry, momentum, phase enthalpy and interval mass before constructing a plug.
   A source identifier or a prescribed zero after isolation is not a material cutoff.
8. Publish a compatible release/API capability declaration with narrow optional imports.
   Core integral-jet imports should not need unrelated elliptic/PyAMG modules. Retain
   exact source hashes and dependency bounds for the tested composition.

## Acceptance evidence

Run the original positive/negative host cases unchanged, with the same predeclared
budgets. Demonstrate source mass, effective-area momentum and h+KE transfer; all four
establishment balances; full momentum-vector change versus integrated forces; species
and total-energy closure across declared radial/spatial refinements. Preserve failed
coarse results and demonstrate the native correction agrees with the host profile-force
bridge on the checked domain. Include normal/para identity and source-reference mismatch
rejections, no-coflow and ground-envelope limits, and source area/phase guards.

Add independent analytic limits and licensed experimental tests with explicit source,
phase/probe semantics and uncertainty. Numerical conservation is not field qualification.
Do not transfer validation from another release pressure, spin, phase profile or geometry
without evidence. The host can remove its protected hook when the public native policy
and flux contract reproduce the relevant balances and failures transparently.

## Additional measured-source and energy-reference evidence

The host now supplies an executable conditional comparison against the actual licensed
HyTunnel-CS spatial concentration workbooks: `scripts/compare_hytunnel_jets.py`,
`docs/HYTUNNEL_JETS.md` and `research/hytunnel_jets.md`. The shared nozzle is inverted for
equivalent inlet pressure at measured flow and declared T0/nominal area; instrumented
pipe pressure is not assumed to be the nozzle stagnation pressure. Per-source header,
tracer, mask and repeated-grid conflicts remain visible rather than entering the engine
as repaired measured facts. No receiving edits/messages were made.

Two unshifted four-flux initial roots fail for the low-momentum 4 mm source conditions.
`hydrogen_energy_gauge_type` is a thin actual-native subclass that transforms five-flux
energy to E+C*H2_mass_flux and source specific energy to h+C*Y_H2, with C=source specific
KE. The native root/ODE/tables/physical profiles and coefficients are retained. The
physical equation is recovered by subtracting C times the conserved H2 species balance.
C/2C initial states agree near 1e-15; full low-flow/held-out observer RMSE changes are
about 5.2e-12/3.4e-12 without changing the physical audit classification. Host conversion
back to the original energy keeps its budgets, scale and initial energy check unchanged.

Please expose a public energy-reference or residual-scaling option that is consistent
across source targets, section fluxes, Jacobian/inversion and returned result identity.
Report raw native and original-component-reference energy separately; never remove an
energy defect by a gauge-dependent denominator or by editing only reported output.
The current 4 mm / 1 g/s path still fails original-reference energy after refinement:
about 0.131 W against 0.00764 W. Inspect caloric lookup/derivative and conservative flux
integration rather than inferring closure from stable concentration curves. The other
four finest measured-source cases pass numerical budgets but all five retain failed
field-accuracy targets, with unchanged fixed coefficients and source/probe assumptions.

The host also exposes explicit unbounded relative geometry and a dry 200-300 K /
<=200 kPa Cartesian gas point observer, with native radial tails or masks declared and
no axial extrapolation. A public native trajectory/phase/probe contract should reproduce
these observation definitions before comparison. The actual airflow map is spatially
varying; a constant fan-speed label is not its boundary. Vector wind/reversal and suction
sampling/wall/temperature assumptions require additional receiving research, not an
automatic extension of the calm-case acceptance status.
