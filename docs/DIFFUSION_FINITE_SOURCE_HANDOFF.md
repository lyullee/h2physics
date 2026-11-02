# Material diffusion to a finite H2 source

`source_from_diffusion_result` adapts the owner-issued slab `DiffusionResult`
to the shared `IntervalMassSource` API. For each accepted time interval it
takes the increment in the native integrated right-face flux per unit area,
multiplies by an explicit membrane area and by the declared mobile-entity molar
mass, and stores the resulting outward hydrogen mass. This is a material
balance projection only; it introduces no new diffusion or release physics.

```python
from h2physics.adapters import source_from_diffusion_result

handoff = source_from_diffusion_result(
    diffusion_result,
    surface_area_m2=area_m2,
    location=outlet_location,
    clock_alignment_evidence_id="case-specific-time-origin-map",
    state_projection_evidence_id="case-specific-H2-state-projection",
    source_evidence_id="case-specific-transport-boundary",
    gas_state=hydrogen_state,
    origin=origin,
)
handoff.require_current()
finite_source = handoff.source
```

For molecular-H2 diffusion, entity moles and H2 moles are identical and the
carrier molar mass must be consistent with the declared H2 molar mass. For
atomic-H diffusion, atomic flux mass is conserved through the projection, but
the adapter requires caller evidence that the exiting atoms form molecular H2.
It rejects any interval with negative integrated outward flux; reverse flow
requires a separate model and boundary representation.

The result's accepted solver clock has no attached facility clock, so callers
must document its mapping to the `SourceLocation` clock. The diffusion model
also carries no gas EOS, temperature/pressure path or energy ledger. Thus the
caller supplies a gaseous H2 `ThermoState` and state-projection evidence. That
state is not inferred from membrane concentrations. Spatial placement is also
caller-owned. The handoff retains the original `DiffusionResult` and
`IntervalMassSource`, rechecks both owners, and verifies every mass bin against
the current integrated-flux increments.

The deferred Hangang case `diffusion-outward-h2-finite-source-handoff` uses a
core-only authored molecular-H2 boundary flux to check area scaling, time-bin
identity and stale-source rejection. It does not qualify membrane properties,
product recombination, downstream piping, nozzle discharge or dispersion.
