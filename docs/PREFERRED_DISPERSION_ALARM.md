# Preferred dispersion receptor alarm adapter

This adapter connects an already admitted `FacilityDispersionHandoff` to the
existing sampled first-order gas sensor and concentration alarm engines. It
does not reproduce either preferred dispersion provider's physics or add a
detector model.

## Boundary and ownership

The caller selects the required `HydrogenReleaseFamily`, identifies the source
domain using the source location's `source_id`, and supplies a receptor with
the exact source coordinate frame and clock. The adapter rejects mismatches
before issuing a receptor field. The provider execution and finite source remain
the original typed receipts; they are never copied into a surrogate provider
result.

The caller extracts one hydrogen mole fraction at the explicit receptor from
the provider's accepted field and records the mapping evidence. Spatial
sampling, interpolation, receptor-height interpretation, terrain mapping, and
applicability remain caller-owned. The caller also supplies evidence that the
selected value represents a steady field throughout the finite source window.
This bridge holds that value on the exact source time edges only if every source
bin has the same positive mean rate within the handoff's retained mass budget.
It refuses varying source rates; it does not invent a transient plume.

The existing sensor and alarm configuration are required verbatim as typed
inputs. Their location, clock, concentration basis, units, sensor evidence,
operating mode, episode, and source origin must match the receptor binding. An
active alarm transition is retained as the original `ConcentrationAlarmEvidence`.

## API sketch

```python
from h2physics.adapters.preferred_dispersion_alarm import (
    PreferredDispersionReceptor,
    bind_preferred_dispersion_receptor_field,
    evaluate_preferred_dispersion_alarm,
)

receptor = PreferredDispersionReceptor(
    receptor_id="detector-A",
    frame_id=source.location.coordinate_frame_id,
    clock_id=source.location.clock_id,
    position_m=(12.0, 0.0, 1.5),
    position_evidence_id="site-layout-revision-7",
)
field = bind_preferred_dispersion_receptor_field(
    handoff, receptor, caller_sampled_h2_mole_fraction,
    expected_family=handoff.family,
    expected_source_domain_id=source.location.source_id,
    clock_id=source.location.clock_id,
    receptor_mapping_evidence_id="provider-grid-to-receptor-method-v2",
    steady_window_evidence_id="steady-field-applicability-study-4",
)
alarm_handoff = evaluate_preferred_dispersion_alarm(
    field,
    sensor_config=existing_sensor_config,
    alarm_config=existing_alarm_config,
    initial_sensor_indication=0.0,
    operating_mode_id="normal-operation",
    episode_id="release-2026-01",
)
```

Use `HydrogenReleaseFamily.HIGH_PRESSURE_GAS` for the HyRAM+ route and
`HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN` for the SLABx-LH2 route. A
provider rejection remains a rejection; this adapter provides no fallback.

## Limits

The output is sampled detector/alarm behavior for the supplied concentration
and assumptions. It does not represent plume startup, plume memory, a safety
instrumented function, facility protection, risk reduction, or safety credit.
Those require separately scoped evidence and models.
