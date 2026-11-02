# Fixed-flaw vessel initiation — implemented, unverified

No native model, pytest, replay, benchmark, example or validation handler was run
locally for this increment. The user requested implementation first and deferred
parallel validation on Hangang. Static syntax/lint results do not establish physical
acceptance. The public status is `implemented_unverified`.

This level composes actual optional HELPR cylindrical-shell mechanics with a
caller-supplied wall-temperature/material law and an existing finite fluid/wall
history. It predicts a conditional static failure-initiation boundary. It adds no
fatigue growth law, vessel ODE, fluid EOS, fire heat-transfer law or material table.
An initiation boundary does not prescribe a hole, opening time, fragments, blast,
BLEVE participation, ignition, probability, annual frequency or continued intact
vessel motion. Those require separate caller-evidenced post-initiation models.

## Physical and native owners

[Sandia's HELPR description](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/helpr/)
identifies pressurized cylindrical shells, stress-intensity calculations and failure
assessment diagrams. The inspected [native source](https://github.com/sandialabs/helpr/tree/ae12d20b6608123af41dd9d5f70db6b6547fece5)
is version2.1.0, BSD-3-Clause, pinned to the same revision as the fracture/fatigue
adapter. The [official API documentation](https://sandialabs.github.io/helpr/)
provides API context. No demonstrated parameter set, coefficient table or native
worked example was copied. No standard-conforming fitness-for-service assessment
or hydrogen-vessel certification is claimed.

The actual native calls are:

```python
pipe = helpr.physics.pipe.Pipe(outer_diameter_m, wall_thickness_m)
material = helpr.physics.material.MaterialSpecification(yield_mpa, resistance_mpa_sqrt_m)
defect = helpr.physics.crack_initiation.DefectSpecification(
    flaw_depth_percent, flaw_length_m, surface="inside", location_factor=explicit_factor)
stress = helpr.physics.stress_state.InternalAxialHoopStress(
    pipe, mechanical_pressure_load, material, defect, stress_intensity_method="anderson")
raw_k = stress.calc_stress_intensity_factor(depth_m, length_m, cycle_index=0)
raw_reference = stress.calc_stress_solution(crack_depth=0.0)
assessment = helpr.physics.fracture.FailureAssessment(resistance_mpa_sqrt_m, yield_mpa, "simple")
raw_ratios = assessment.assess_failure_state(raw_k[0], raw_reference)
```

`native_2016_fad` additionally calls the existing native
`helpr.utilities.plots.failure_assessment_diagram_equation`. Its equation and
coefficients stay inside HELPR. Importing this optional native module also imports
its plotting dependencies and applies its native matplotlib setting. The host
adapter's ordinary import does not import HELPR or execute mechanics.

The uncracked native hoop stress matches HELPR's actual `simple` FAD reference
path. The native Anderson SIF still resolves the supplied internal axial elliptical
part-through flaw. The returned native Kmax is the native selection of its finite
and long-flaw candidates; native returned shape factors are retained without
relabeling them as necessarily belonging to the governing candidate. This is not
the native API579 Level2 reference-stress/table solution or a complete elastic-
plastic, residual-stress, weld, creep, buckling or thermal-stress assessment.

The native pressure interface is an explicitly labeled host mechanical load
adapter: it supplies the same instantaneous differential pressure to both native
pressure accessors, converting Pa to MPa. It is not a gas environment or fabricated
fugacity object. HELPR's gas `EnvironmentSpecification` would impose its own
230–330K fugacity domain, which is unrelated to hot or cryogenic wall temperatures.
No arbitrary gas temperature is inserted to bypass that domain. No hydrogen EOS
or fugacity relation is evaluated in this mechanical bridge.

## Geometry, pressure and material contracts

`HelprAxialFlaw` requires positive outer diameter, thickness, fixed flaw depth and
full flaw length, location factor and geometry/defect evidence. This first level is
restricted to inside axial flaws, `5 <= inner_radius/thickness <= 20`,
`0 < depth/thickness <= 0.8` and an explicitly restricted elliptical `a/c <= 1`.
The native geometry warning bounds are enforced as admission errors. The selected
native approximation uses its own outer-diameter pressure convention; the adapter
does not substitute an inner-radius or von-Mises model.

The public inputs use Pa absolute internally and externally. Only
`Pinside-Poutside` is sent to the tensile native mechanical model, in MPa.
`Pinside>Poutside>=0` is required. The native SIF computes a pressure ratio and
does not support its zero-pressure endpoint directly; no epsilon pressure or fake
successful result is supplied. Equal-pressure, external-pressure buckling and
compressive loading are excluded at this checkpoint. Pressure capacity is returned
as internal **absolute** pressure together with its original exterior pressure.

`VesselMaterialLaw` is a deterministic pure Python callable of the actual loading
and context. It supplies positive yield strength in Pa, fracture resistance in
Pa*sqrt(m), an explicit maximum load ratio and point evidence. Its wall-T,
internal-absolute-P and H2-fraction validity bounds are mandatory. There are no
default steel strengths, toughness values, thermal weakening factors or hydrogen
corrections. Native scalar material objects receive SI-to-MPa conversions only.
Alloy, heat treatment, specimen/size, wall-T representation, strain rate, H2
pressure/fugacity/service exposure and fracture-resistance relevance need actual
qualification. Pressure and H2 fraction alone do not infer dissolved hydrogen or
material degradation. Existing tensile data do not automatically establish KIC.

`separate_yield_and_toughness` checks the two native ratios against the supplied
load cutoff and unit toughness ratio. `native_2016_fad` uses the actual native
FAD ordinate within the caller-evidenced load-ratio interval and separately enforces
the supplied cutoff. Above that cutoff the failure is explicitly a load failure;
the FAD curve is not evaluated or clipped. An invalid/nonpositive native ordinate
inside the requested interval is retained as an admission failure. The dimensionless
margin and governing criterion are recorded; neither selection implies rupture
probability or automatically qualifies a standard cutoff.

## Finite history, clocks and roots

`VesselFailureContext` fixes vessel, wall region, reference frame, operation clock,
source, actual fluid/reference/spin `PropertyBasis`, H2 mole fraction and the wall,
service and geometry-binding evidence. The fluid caloric zero is preserved as
context; mechanics does not use it as material fracture energy or energy released.
`VesselLoading` records time, inside/outside pressure, represented wall temperature,
phase label and any actual native snapshot/state/fluid objects.

`VesselFailureHistory` has at least two strictly ordered finite samples. A single
wall region and constant supplied phase label are required; split phase-label
transitions into separately admitted histories. Its explicit linear reconstruction
is of the mechanical Pinside/Poutside/wall-T signals only. Intermediate states
have their actual parent samples and no fabricated native fluid/state object.
They are not an EOS-consistent continuation, native hidden accepted states, a
spatial temperature field or a fully resolved thermal-stress solution.

```python
owner = HelprVesselFailure(
    geometry, material_law, criterion="native_2016_fad",
    criterion_evidence_id=explicit_criterion_evidence)
prediction = owner.predict(history, maximum_reconstruction_step_s=declared_step_s)
capacity = owner.pressure_capacity(
    history.samples[0], history.context,
    bracket_pressure_pa_absolute=(safe_internal_pa, failed_internal_pa),
    continuation_evidence_id=explicit_fixed_wall_T_pressure_path)
```

`predict` evaluates the source endpoints and explicitly subdivided mechanical
intervals. The first resolved safe-to-failed bracket is passed to actual SciPy
`root_scalar(..., method="brentq")`, repeatedly calling native mechanics. A
first-sample failure is reported without inventing an earlier time. No bracket
means `no_resolved_initiation_within_support`, not infinite life or a guarantee
against hidden nonmonotonic excursions. Time/mesh refinement remains necessary.
The root's signed margin can lie slightly on either side of zero at finite root
tolerance; the individual point's `failed` flag retains that actual sign.

`pressure_capacity` uses the same native margin and actual SciPy root at fixed
wall temperature on a caller-specified counterfactual pressure path. Its bracket
must contain an admitted safe-to-failed boundary. Material pressure dependence is
reevaluated at every trial. There is no automatic scanning, EOS/phase extrapolation
or silent repair of a missing bracket. Root pressure states retain their original
loading parent and do not carry a fabricated native thermodynamic state.

## Existing finite LH2DT coupling

`history_from_cryo_compressed` accepts an actual `CryoCompressedTrace`, retained
native tank and native states. It checks exact state/time identities against the
original native trace and rereads each fluid through that same native tank and
existing property bridge. Cached fluid fields must agree. Operation clock,
thermal-boundary source and pure-H2 property/reference/spin identities must match.
Computed history cannot be relabeled measured data. The original trace, snapshots,
native states and newly read native fluid objects remain available.
The prediction consumer repeats this binding before and after mechanics, including
comparison of the supplied sampled pressure/wall-T fields with actual native states.
A replaced computed summary retaining the original trace is therefore rejected.

The builder uses the actual native lumped wall temperature. A caller must bind that
region to the assessed cylindrical section explicitly; the fluid control-volume
size alone does not supply shell diameter, wall thickness, head shape or local
defect geometry. A lumped temperature cannot resolve a flame hot spot, material
thermal gradient or differential expansion. Other existing wall partitions can
feed explicitly constructed region histories, with their own admissibility and
geometry evidence. No ODE or caloric law is reimplemented here.

The supplied storage history is a continuation under an intact rigid-vessel model.
Interpret it only through the predicted initiation time. The adapter does not
change the source integrator, restart it after rupture or infer an opening area.

## Deep objects and failure evidence

Every evaluation retains the actual native pipe, material, defect, stress and
FailureAssessment, raw native K tuple, reference stress, ratios, FAD return and
construction warnings. A factory may return only the real pinned native stress
class with the declared physical-object bindings; instance method substitutions
are rejected. Definitions and method bindings are guarded, and native source
bytes are checked before/after execution. The selected source hashes and revision
are recorded in the separate dependency receipt.

History prediction copies mechanical coordinates before callbacks and checks the
complete original evidence fingerprint again before returning. Mutating caller
callbacks cannot produce an accepted result with changed provenance. Native
objects remain usable for deeper Python work after the calculation; concurrent
mutation needs caller synchronization. No independently authenticated measured
data or arbitrary closure-state purity can be inferred from a callable identity.

`VesselFailureError` retains the original source/history, completed evaluations,
constructed native objects, pending native raw returns, last actual loading and
returned SciPy root object if one exists. Original exceptions are chained. If a
native constructor or SciPy callback raises before returning an object, that
unreturned object is not fabricated. Native source/domain/numerical failures
remain failures and do not trigger another mechanics engine.

## Deferred validation

Four `validation.cases.vessel_failure:cases()` entries are metadata only. Their
unrun handlers prepare: independent pressure-force/yield capacity and unit limits;
an authored thermal-strength crossing with refinement; actual finite LH2DT
fluid/wall/ledger and binding checks; and negative geometry/clock/bracket retention.
The native FAD path is also exercised conditionally by its remote handler. Source
bytes are recorded by the cluster runner and the capacity case. No case is claimed
passed now. The transitive HELPR/CoolProp/LH2DT runtime profile still needs isolated
resolution on Hangang. Independent hot/cryogenic H2 vessel failure data, material
T-law calibration and geometry/FAD qualification remain open.

## Conditional fragment-flight handoff

`run_vessel_failure_fragment_flight()` binds an original issued HELPR failure
event to the existing elastic-cylinder energy bound and fragment-trajectory
owner. It carries the exact failure time, pressure difference, shell geometry
and clock into that boundary. The caller supplies the shell-to-cylinder mapping,
end support, represented length, elastic properties, fragment mass/energy share,
launch location and velocity, and the environment. The adapter rejects a flight
whose first sample does not equal the initiation time or whose kinetic energy
exceeds the declared bound. It does not compute an opening, fragment count,
fragment mass or launch velocity. Deferred Hangang case
`vessel-failure-fragment-flight-handoff` covers this contract; it is not a
fragmentation or breach-physics validation.
