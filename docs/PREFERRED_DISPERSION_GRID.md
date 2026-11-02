# Exact preferred-dispersion receptor grid handoff

`h2physics.adapters.preferred_dispersion_grid` samples one node from an
explicit caller-exported static 3D hydrogen mole-fraction grid. It preserves the
accepted `FacilityDispersionHandoff` and requires `provider_result` to be the
same object retained by that handoff's `DispersionExecution`.

## Required field contract

The caller exports three strictly increasing coordinate axes in metres and a
finite concentration array with shape `(len(x_m), len(y_m), len(z_m))`. Values
must be H2 mole fractions in `[0, 1]`. The caller declares the exact source
coordinate frame, clock, grid-export evidence, and evidence that the steady
field applies over the finite source interval. The bridge checks frame and
clock against the admitted source and requires the caller to declare the
expected `HydrogenReleaseFamily` and `SourceLocation.source_id`.

Sampling accepts only exact coordinate equality on every axis. It rejects
nearest-node selection, tolerance-based matching, interpolation, extrapolation,
unsupported units, provider family/domain mismatches, source frame/clock
mismatches and nonconstant source-rate windows. The resulting scalar field is
passed to the existing alarm handoff; no sensor or alarm physics is duplicated.

```python
from h2physics.adapters.preferred_dispersion_grid import (
    PreferredDispersionConcentrationGrid,
    sample_preferred_dispersion_receptor_exact,
)

grid = PreferredDispersionConcentrationGrid(
    handoff=accepted_handoff,
    provider_result=accepted_handoff.execution.result,
    x_m=provider_x_m,
    y_m=provider_y_m,
    z_m=provider_z_m,
    h2_mole_fraction=exported_h2_mole_fraction,
    frame_id=source.location.coordinate_frame_id,
    clock_id=source.location.clock_id,
    grid_evidence_id="provider-export-record-12",
    steady_window_evidence_id="steady-field-assessment-3",
)
field = sample_preferred_dispersion_receptor_exact(
    grid,
    receptor,
    expected_family=accepted_handoff.family,
    expected_source_domain_id=source.location.source_id,
    receptor_mapping_evidence_id="site-layout-revision-7",
)
```

The adapter does not parse or reinterpret native provider schemas. The caller
must separately establish that the exported arrays correspond to the accepted
native result, that coordinates have the declared units/frame, and that the
steady assumption is suitable. A provider without a compatible finite 3D grid
cannot use this exact-node bridge; it needs a separate typed extractor with
provider-specific coordinate semantics. There is no time axis, plume-memory
model, safety-instrumented function, risk-reduction claim or safety credit.

The deferred Hangang case checks only API contract metadata. It does not run a
native provider, sample a scientific field, or establish physical validation.
