# Conditional finite fatigue crack growth — implemented, unverified

This implementation has **not been executed locally**. No native validation,
pytest, benchmark, measured comparison or facility acceptance has been performed.
The user requested coding and parallel Hangang verification. Scientific execution
is deferred to Hangang while local implementation continues. The deferred
cases in `validation/cases/fracture_fatigue.py` are proposed checks, not results.

`h2physics.adapters.fracture_fatigue` composes the actual optional Sandia HELPR2.1.0
constitutive API with the existing SciPy `solve_ivp` integrator. HELPR evaluates
the selected Paris/published hydrogen relation. A caller function evaluates mode-I
stress intensity from crack size and the load block. SciPy integrates crack size
against cycle count and locates explicit terminal events. This is a host numerical
composition of native constitutive calls; it does not use or claim HELPR's complete
pipe-specific `LifeAssessment` trajectory driver.

## Physical boundary

The input is an existing finite crack in a caller-qualified elastic mode-I geometry.
The level excludes initiation, plastic collapse, mixed-mode growth, compression
closure, overload/retardation memory, corrosion/dwell-time crack growth, evolving
crack-front shape and constitutive hydrogen transport. Existing transport and
finite-volume material owners are unchanged. Pressure is not converted into stress
through an invented thin-wall formula. The geometry callback owns that relationship.

`HydrogenCrackEnvironment` records absolute maximum/minimum gas pressure Pa,
temperature K, gas-phase H2 mole fraction, H2 fugacity Pa, its explicit basis,
evidence ID and origin. Fugacity and partial pressure are not interchangeable.
The record is a boundary declaration and does not supply a new EOS or prove phase
stability. A single gaseous exposure and the material's applicability must be
established by the caller's evidence.

`FractureMaterialDomain` binds a particular material/curve and evidence to P/T/
fugacity, Kmin/Kmax ratio, frequency and DeltaK ranges, plus small-scale-yielding
and numerical-extension evidence. Frequency is obtained from the supplied block's
cycle and physical-time endpoints. It is checked against the curve qualification;
no frequency correction is invented. Existing tensile/ductility observations do
not automatically become da/dN data, toughness or Paris coefficients.

## Native law selection and units

The inspected owner is [Sandia HELPR](https://github.com/sandialabs/helpr), pinned to
revision `ae12d20b6608123af41dd9d5f70db6b6547fece5`, version2.1.0, BSD-3-Clause.
The actual source API is:

```python
from helpr.physics.crack_growth import CrackGrowth

native = CrackGrowth(actual_native_environment, explicit_growth_model_specification)
increment_m = native.calc_change_in_crack_size(
    delta_n=1.0, delta_k=delta_k_mpa_sqrt_m, r_ratio=k_min_over_k_max, cycle_index=0)
```

`HelprLawSelection` explicitly chooses `paris_law`, `code_case_2938` or `g_202006`.
`paris_law` requires supplied SI C and exponent, with C in
`m/cycle/(Pa*sqrt(m))**exponent`. The wrapper converts only units to native
MPa*sqrt(m); the native function evaluates growth. A generic supplied curve is
conditional on its material/H2 evidence. It is never labeled a hydrogen correction
of an air curve. No default material C, exponent, threshold or toughness is supplied.

The inspected native increment paths are linear in the supplied cycle increment.
Calling that API at `delta_n=1` therefore supplies the constitutive rate for the
SciPy composition. The deferred cases explicitly check this scaling; it has not
been executed at this checkpoint. This does not reproduce the native pipe driver's
finite stepping or imply identical trajectory algorithms.

The two published native H2 selections keep their actual implementation and branch
coefficients inside HELPR. They require an explicit native reference pressure,
the `HELPR-native-Abel-Noble` fugacity basis, and numerical agreement between the
declared fugacity and the actual native environment. The code calls native
`EnvironmentSpecification` rather than writing another fugacity equation. This
native physical basis is distinct from CoolProp or a supplied fugacity closure;
no silent substitution or reference relabel is allowed. Its native T bounds are
230–330K. The actual constructor bounds H2 fraction to0–1; a source docstring says
percent, so this wrapper follows the inspected code and explicitly admits fractions.

The native published H2 branches include a native air-floor construction. That is
part of the explicitly selected native model, not a new host correction. Material,
alloy, gas-mixture, stress-ratio and loading-frequency suitability still require
evidence. Native published branch coefficients are not copied into host files and
are not independently fitted here. Their general parameter replacement would need
a native API extension; generic supplied Paris C/exponent are replaceable now.

HELPR's official [feature description](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/helpr/)
and [API documentation](https://sandialabs.github.io/helpr/) identify its fatigue/
fracture and hydrogen use. Those statements do not validate this unexecuted
composition. The scientific need for broad material evidence follows the original
[Paris–Erdogan paper](https://doi.org/10.1115/1.3656900); its publisher abstract was
inspected, and no paper coefficient table or example is reproduced. Sandia's
[hydrogen-material references](https://www.sandia.gov/matlstechref/home/references/)
identify pressure/stress-ratio and material-specific work; no code-case conformity
or certified vessel/pipeline assessment is claimed by this adapter.

## Python objects and ordered loading

`LoadCycleHistory` retains ordered `LoadCycleBlock` objects, a separate cycle
coordinate and physical clock, source/stress basis and ordering evidence. Blocks
must meet exactly on both clocks. A histogram is not an ordered variable-amplitude
history. The wrapper does not perform rainflow counting, infer a clock from a cycle
histogram, reorder observations or invent missing dwell periods. Fractional positive
cycle increments are allowed as numerical cycle coordinates.

`CrackGeometryCallback` returns actual `ModeIStressIntensity` objects in Pa*sqrt(m).
The callback receives crack size in m and the original load block. It must admit
its physical crack range and a separately evidenced bounded numerical range for
the SciPy stages used to locate an event. Negative/reversed/nonfinite K values
are rejected. No stress-intensity factor, geometry coefficient or specimen shape
is silently chosen. The reusable example builds original synthetic metadata and
a basic infinite-plate analytic callback; it does not execute at import.

```python
from h2physics.adapters.fracture_fatigue import HelprFatigueLaw, integrate_fatigue_crack

# selection, history, geometry, material_domain and conditions are explicit
# previously admitted Python objects; see examples/fracture_fatigue.py.
law = HelprFatigueLaw(selection, native_growth_factory=None)
result = integrate_fatigue_crack(
    law, history, geometry, material_domain, conditions,
    initial_crack_m=initial_size_m, settings=integration_settings)
actual_growth_object = result.native_owners[0].growth
actual_environment = result.native_owners[0].environment
actual_scipy_result = result.native_solutions[0]
```

The optional injected factory must return the real pinned `CrackGrowth` class,
with the specified environment and arguments. No fake engine or fallback provider
is accepted. Each block uses an independently retained native owner. Native model
arguments and environment definitions are checked around callbacks/native calls;
selected source files are fingerprinted before/after integration. Mutable native
objects must not be reused concurrently without caller synchronization.

## Stops, numerical extensions and retained evidence

`CrackStopConditions` distinguishes maximum crack size, a **peak Kmax** toughness
criterion and an explicitly evidenced cyclic DeltaK arrest threshold. Kmax
toughness is not relabeled DeltaK. A zero cyclic range or supplied arrest criterion
has zero propagation at this level; no static stress-corrosion prediction follows.
Unless `stop_at_arrest=True`, later higher-amplitude blocks can restart growth.
Arrest over supplied blocks is not infinite life or an inspection interval.

SciPy terminal events locate size/fracture/optional arrest crossings. Internal
trial states can lie beyond an event before its root is located. The caller's
bounded geometry and DeltaK trial extension supports that numerical operation;
it does not qualify physical extrapolation. Out-of-range trials fail. No host
clipping, automatic bound expansion or false successful stopping event is used.
Reported output states must remain in the physical size/toughness/growth envelope,
apart from explicitly dimensioned numerical admission budgets.

`FractureGrowthResult` retains original inputs, snapshots, all actual native growth
calls/raw returns, native law/environment objects, every returned SciPy OdeResult,
termination meaning, source/input fingerprints and the unverified software status.
At a block boundary, left/right load contexts can have the same cycle/time and
continuous crack size; each snapshot retains its block ID. A new geometry is not
inferred from the returned crack size.

`FractureGrowthError` retains original history/geometry, completed native objects,
returned numerical results, output prefix, raw-call prefix, last evaluated trial
coordinate and a pending raw native return if result admission fails. The original
cause remains chained. `solve_ivp` does not expose its internal OdeSolver object
when an RHS exception prevents a return; that path has no fabricated OdeResult or
claimed hidden accepted-step prefix. Native environment/model admission errors
retain a constructed object when one exists. Numerical failure is not repaired
by switching engines or relaxing evidence bounds.

## Deferred Hangang validation

`validation.cases.fracture_fatigue:cases` contains metadata only. Its five
`ValidationCase` handlers are prepared to execute later through the parent cluster
runner. Local execution of these cases/examples/native models is intentionally
not performed at this checkpoint. Planned gates include:

- Actual HELPR object/source identity, native units and independent m=2 exponential
  finite-growth oracle for an authored geometry and synthetic curve.
- Analytic size/toughness failure-cycle limits, raw SciPy events and step/tolerance
  refinement, including the cycle-to-time mapping.
- Native H2 model/fugacity point calls, positive finite rates and explicit native
  reference. This checks composition, not independent H2 correlation accuracy.
- Zero-range arrest, subsequent restart, inadmissible ratio/geometry/clock failures
  and preservation of original objects/causes.

Additional qualification must cover negative/nonfinite input units, incomplete or
reordered histories, native source/parameter mutation, insufficient numerical
extension, near-threshold/domain boundaries, event overshoot budgets, crack-front/
geometry validity and independent measured da/dN data under matched material,
P/T/fugacity/R/frequency conditions. None of those checks is reported passed here.

The optional dependency is separately supplied and not bundled. The receipt records
actual inspected source/license hashes. HELPR's transitive installation and runtime
compatibility remain to be resolved on Hangang; the main environment is unchanged.
Py-fatigue2.1.1 was inspected as a candidate but not selected: its actual license is
GPLv3, its Numba constraint needs a separate profile, its integrator hard-codes two
geometries, and its endpoint/index semantics need a retained native audit. There
is no silent fallback to it.

## Pressure and thermal stress inputs from the shared cylinder owner

`h2physics.materials.elastic_cylinder` supplies a separate thick-cylinder
elastic stress reference for caller-declared internal/external pressures and
end support. `lame_stress_samples()` evaluates ordered pressure samples on a
declared radial grid and preserves the source clock. Its uniform-temperature
extension supports free or fixed axial expansion. These results do not
calculate stress intensity; a qualified crack geometry and explicit mode-I
callback remain required by the growth API. See
[`research/elastic_cylinder_development.md`](../research/elastic_cylinder_development.md).

The separate `h2physics.materials.radial_thermoelastic_cylinder` module handles
a caller-supplied radial temperature profile and retains its sampled stress
field. It does not feed temperature or concentration back into the crack-growth
law. A source-bound bridge can map an existing vessel pressure history into
the vessel-failure contract without inventing intermediate fluid states.
Related deferred cases include `elastic-cylinder-pressure-boundaries`,
`elastic-cylinder-pressure-samples`, `elastic-cylinder-uniform-thermoelasticity`,
and `elastic-cylinder-radial-thermoelasticity`; none is a fatigue validation
result. See [`research/radial_thermoelastic_cylinder.md`](../research/radial_thermoelastic_cylinder.md).
