# Vessel initiation development checkpoint

Status: `implemented_unverified`. No local native import, model execution, pytest,
replay, benchmark, example or cluster case execution was performed. Only source/API/
license inspection and static syntax/lint preparation are allowed under the latest
user instruction. No measured validation or numerical pass exists for this increment.

The actual native owner is HELPR2.1.0, revision
ae12d20b6608123af41dd9d5f70db6b6547fece5, BSD-3-Clause. The existing fracture receipt
establishes the inspected version, license, dependency list and source-only local
inspection. Additional static mechanical source hashes are recorded in
vessel_failure_dependency.toml. No native package was installed into the main
environment. No source, material curve, table or third-party worked example was
copied into the host package.

## Native API decision

Static inspection established actual Pipe, MaterialSpecification,
DefectSpecification, InternalAxialHoopStress(anderson), FailureAssessment and the
native failure_assessment_diagram_equation callable. Native stress outputs are MPa
and MPa*sqrt(m), while geometry is SI m. The bridge performs unit conversions only.
Native simple reference stress is uncracked hoop stress; the flaw enters the native
Anderson SIF. Native SIF selection and returned shape factors are retained as given.
No API579 table data, full Level2 reference stress, residual/plastic correction or
new stress-intensity model was implemented.

The gas EnvironmentSpecification has a230–330K fugacity domain. It is inappropriate
to invent a gas temperature merely to assess a cold/hot wall. The native stress
code requires only its pressure accessors, so an explicit host mechanical-load
interface supplies instantaneous differential pressure in native MPa. The stress
owner remains the actual native class. This interface makes no gas, EOS, fugacity
or fatigue-cycle claim. Equal pressure exposes a native ratio division in SIF;
the present level admits strictly positive tensile differential pressure only.

The native FAD curve function is located in the plotting module. Optional model
construction imports that module and its native plotting dependencies/settings;
ordinary host adapter import does not. No native curve coefficients are duplicated.
The explicit caller load-ratio cutoff is separate from the native curve and is
not inferred from missing ultimate-strength data. No code certification follows.

## Integration boundary

Existing CryoCompressedTrace provides actual finite native fluid/wall states and
mass/energy audits. The builder checks original state/time identities and rereads
the native tank thermo state instead of trusting replaced cached fields. Context
requires matching clock, original thermal source and pure-H2 property/spin/reference
basis. The original trace and native snapshot objects are retained. No fluid/wall
ODE, EOS, heat law or fatigue growth is copied from prior adapters.

The wall material law is supplied as an explicit temperature/pressure/H2-qualified
callback returning yield strength, fracture resistance, load cutoff and evidence.
The host has no generic steel thermal law, H2 correction, creep damage or implicit
default toughness. A geometry/region binding is necessary because vessel fluid
volume does not identify mechanical shell thickness or a local defect.

Static mechanics is evaluated over finite declared mechanical signal reconstruction.
Pressure and wall temperature are linearly reconstructed between supplied samples;
there is no claim of EOS consistency at intermediate points. First resolved
initiation and fixed-wall-T pressure capacity use actual existing SciPy bracketed
roots over actual native mechanical margin. Arbitrary missed nonmonotonic crossings
and unresolved wall hot spots remain outside this sampled level. Intact-vessel
continuation beyond initiation is not physical rupture evolution.

## Prepared validation, not executed

Four Nurion cases are prepared: native capacity/SI/pressure force balance; synthetic
thermal weakening time root with refinement and native FAD path; actual existing
finite LH2DT integration and conservation/binding; and negative inputs/missing
bracket retention. Synthetic strengths isolate independent analytic limits and
are never called measured hydrogen material data. All handlers are dormant until
the cluster runner explicitly invokes them. The parent cluster profile must resolve
HELPR, its transitive licenses, native LH2DT and CoolProp before these cases run.

Additional planned checks include source/method/parameter mutation, callback raw
response failures, failed native SIF/FAD outputs, near-domain cutoffs, first-sample
failure, safe finite support, bracketed roots near flat boundaries, equivalent
pressure-unit limits and refinement of source thermal histories independently of
mechanical interpolation. No pass/timing is assigned before actual execution.

Primary sources inspected: official Sandia HELPR feature page, public pinned source,
official API docs and Sandia's HELPR project presentation. These establish model
ownership/context, not a material T-law or apparatus validation. No proprietary
API/Anderson table or text was obtained or reproduced. Required future data include
matched alloy/heat treatment K resistance and strength versus wall T, H2 service/
fugacity/time, actual vessel/flaw geometry and independent failure experiments.

The opening/fragment/blast/probability handoff remains a separate caller-evidenced
contract. Effects.rupture must not be called complete from this static initiation
bridge or its future synthetic verification alone. Final LF/static checks and file
hashes are reported at handoff without self-referential report hashes.
