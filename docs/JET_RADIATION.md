# Jet-flame radiation adapter

`line_source_irradiance` composes an already admitted native HyRAM flame result
with an explicit isotropic finite line-source geometry. The native visible
centerline supplies segment lengths; native emitted radiant power is divided by
total visible arc length and distributed over those segments. A caller supplied
atmospheric transmissivity modifies each segment-to-receiver contribution. The
reported atmosphere-weighted power is an observer-distance-weighted diagnostic,
not a spatial integral of the radiative field.

The result is incident scalar irradiance at point receivers. It does not resolve
surface normals, absorption, reflection, shadowing, plume smoke, flame motion,
wind tilt, target damage, injury or time-varying fire. It accepts only a source
whose existing HyRAM source, mass, caloric and radiation gates pass. Rejected
native flames remain rejected and cannot be promoted through this adapter.

The low-cost numerical representation uses native centerline segment midpoints.
Its independent validation plan requires mesh convergence and comparisons with
published or openly licensed hydrogen-jet radiometer observations before an
engineering prediction status can be assigned. The four `jet-fire-radiation`
deferred cases are not executed during local coding.

The receiver input uses global x/y/z coordinates in metres. Humidity is a
dimensionless fraction in [0,1]. The caller must identify the geometry frame,
transmissivity source, and application domain in `LineRadiationPolicy`.
The receiver frame must exactly match the retained flame source frame; changing
a frame label is not a coordinate transform. Callback execution must preserve
the original source, policy and receiver inputs.

`segment_subdivisions` refines midpoint integration on the same original native
polyline; it does not fabricate another accepted flame. The field retains the
receiver-by-segment transmissivity matrix and reconstructs incident flux, its
distance summary, visible line power and observer-weighted power when directly
constructed. Only `line_source_irradiance()` can issue the field; direct construction
and dataclass replacement cannot reseal a changed result under the original receipt.
`require_current()` also checks the native source signature and retained field
content. The deferred integrity contract mutates direct flux, transmissivity and
power fields; it is not executed locally.

`incident_history_from_jet_radiation(field, receiver_index, start_s=..., end_s=...,
clock_id=..., evidence_id=..., steady_projection_evidence_id=...)` carries one
original point irradiance into a finite held `IncidentHeatHistory`. The explicit
window must lie inside the original flame's steady clock support. It does not infer
ignition or inventory exhaustion. Surface projection, uniformity and absorption
still require target-side evidence. Lumped and radial target runners check the
retained field's freshness. These additions are implemented_unverified.

`run_jet_radiation_radial_wall()` composes the point-irradiance history with the
existing radial wall solver in one source-bound operation. It requires explicit
wall geometry, absorptivity, application and circumferential-uniformity evidence;
it adds no view-factor or fire-dynamics model. See
[HyRAM radiation to radial wall](JET_RADIATION_RADIAL_WALL.md).


Each field is issued once by line_source_irradiance using an internal pending token.
Constructing the private issuer type directly is insufficient; the existing deferred
contract checks this boundary as well as cloning and output mutation.
