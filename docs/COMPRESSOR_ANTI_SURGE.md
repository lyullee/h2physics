# Static compressor surge-margin admission

`CompressorAntiSurgeGuard` checks an original `MappedCompressorTrace` against a
caller-supplied, source-hashed surge boundary and a separately declared minimum
corrected-flow margin. It provides an auditable static feasibility gate for
integration with an existing native compressor result.

The surge boundary is a sequence of corrected speed and corrected inlet mass
flow points. Linear interpolation is restricted to the declared speed support;
the guard rejects extrapolation. Each active trace point receives a margin
`corrected_flow - surge_boundary_flow`. A point is admitted only when this value
meets the caller's declared minimum within its explicit numerical tolerance.
Isolated points are marked not applicable and are carried through unchanged.

```python
from h2physics.adapters.compressor_anti_surge import (
    AntiSurgeMarginPolicy,
    CompressorAntiSurgeGuard,
    SurgeBoundary,
    SurgeBoundaryEvidence,
    SurgeLinePoint,
)

boundary = SurgeBoundary(
    "compressor-a-surge-line",
    (SurgeLinePoint(100.0, 0.012), SurgeLinePoint(200.0, 0.024)),
    SurgeBoundaryEvidence(
        evidence_id="reviewed-map-revision-4",
        source_uri="https://example.org/licensed-map",
        license_id="reviewed-license-id",
        source_sha256="<64 lowercase hexadecimal characters>",
    ),
)
policy = AntiSurgeMarginPolicy(
    "site-operating-margin", 0.002, "approved-protection-basis-revision-2"
)
receipt = CompressorAntiSurgeGuard(boundary, policy).evaluate(mapped_trace)
if receipt.feasible:
    receipt.require_feasible()
```

Supply the surge line and minimum margin from data or an independently reviewed
operating policy. This module does not generate a compressor characteristic,
recycle-valve capacity, controller response, rotating-stall threshold or transient
surge dynamics. It cannot establish that a supplied line is valid for a particular
gas, machine, speed, inlet condition or operating life. The receipt retains and
rechecks the original map trace, native results, boundary and policy. A failed
point is kept in the receipt; `require_feasible()` raises instead of silently
discarding it.

The synthetic support/interpolation case is only a contract check. The deferred
native replay needs two genuine traces from the pinned native compressor API and
independent evidence for both the line and its required margin. This source-only
level is `implemented_unverified`; no local scientific execution was performed.
