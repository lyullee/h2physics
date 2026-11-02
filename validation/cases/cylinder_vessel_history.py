"""Deferred Nurion checks for the cylinder-to-vessel-history Python bridge."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="cylinder-pressure-vessel-history-bridge",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_bridge",
            invariants=(
                "pressure sample clock and source evidence retained",
                "absolute pressure and declared H2 PropertyBasis preserved",
                "wall temperature and single phase map samplewise without interpolation",
                "origin and clock mismatch rejected",
            ),
        ),
    )


def validate_bridge(*, work_directory, **parameters):
    from h2physics.adapters.cylinder_vessel_history import bind_cylinder_samples_to_vessel_history
    from h2physics.adapters.vessel_failure import VesselFailureContext
    from h2physics.core import Origin, PropertyBasis
    from h2physics.materials.elastic_cylinder import (
        CylinderGeometry,
        CylinderPressureLoad,
        lame_stress_samples,
    )

    geometry = CylinderGeometry(0.08, 0.16, "closed", "bridge-authored-cylinder")
    loads = (
        CylinderPressureLoad(1.0e6, 1.0e5, "source-pressure-0", Origin.SYNTHETIC),
        CylinderPressureLoad(2.0e6, 1.0e5, "source-pressure-1", Origin.SYNTHETIC),
    )
    stress = lame_stress_samples(
        geometry,
        [0.0, 5.0],
        loads,
        [0.08, 0.12, 0.16],
        clock_id="bridge-clock",
        evidence_id="authored-cylinder-equation",
    )
    context = VesselFailureContext(
        vessel_id="bridge-vessel",
        wall_region_id="bridge-wall",
        frame_id="bridge-frame",
        clock_id="bridge-clock",
        source_id="bridge-pressure-source",
        fluid_basis=PropertyBasis("hydrogen", "bridge-reference", "normal"),
        hydrogen_mole_fraction=1.0,
        hydrogen_service_evidence_id="bridge-H2-evidence",
        wall_temperature_evidence_id="bridge-temperature-source",
        geometry_binding_evidence_id="bridge-geometry-evidence",
        origin=Origin.SYNTHETIC,
    )
    binding = bind_cylinder_samples_to_vessel_history(
        stress,
        context,
        [290.0, 300.0],
        phase_id="single-gas-phase",
        pressure_source_evidence_id="bridge-pressure-source",
        temperature_evidence_id="bridge-temperature-source",
        reconstruction_evidence_id="bridge-authored-clock-map",
    )
    assert binding.history.context is context
    assert binding.pressure_samples is stress
    assert tuple(sample.time_s for sample in binding.history.samples) == (0.0, 5.0)
    assert tuple(sample.internal_pressure_pa_absolute for sample in binding.history.samples) == (
        1.0e6,
        2.0e6,
    )
    assert tuple(sample.external_pressure_pa_absolute for sample in binding.history.samples) == (
        1.0e5,
        1.0e5,
    )
    assert tuple(sample.wall_temperature_k for sample in binding.history.samples) == (290.0, 300.0)
    assert {sample.phase_id for sample in binding.history.samples} == {"single-gas-phase"}

    rejected_clock = False
    try:
        bad_context = replace(context, clock_id="other-clock")
        bind_cylinder_samples_to_vessel_history(
            stress,
            bad_context,
            [290.0, 300.0],
            phase_id="single-gas-phase",
            pressure_source_evidence_id="bridge-pressure-source",
            temperature_evidence_id="bridge-temperature-source",
            reconstruction_evidence_id="bridge-authored-clock-map",
        )
    except ValueError:
        rejected_clock = True
    assert rejected_clock

    rejected_origin = False
    try:
        measured_loads = tuple(
            CylinderPressureLoad(
                load.internal_pressure_pa,
                load.external_pressure_pa,
                load.load_id,
                Origin.MEASURED,
            )
            for load in loads
        )
        measured_stress = lame_stress_samples(
            geometry,
            [0.0, 5.0],
            measured_loads,
            [0.08, 0.12, 0.16],
            clock_id="bridge-clock",
            evidence_id="authored-cylinder-equation",
        )
        bind_cylinder_samples_to_vessel_history(
            measured_stress,
            context,
            [290.0, 300.0],
            phase_id="single-gas-phase",
            pressure_source_evidence_id="bridge-pressure-source",
            temperature_evidence_id="bridge-temperature-source",
            reconstruction_evidence_id="bridge-authored-clock-map",
        )
    except ValueError:
        rejected_origin = True
    assert rejected_origin

    metrics = {
        "mapped_sample_count": len(binding.history.samples),
        "clock_id": binding.history.context.clock_id,
        "source_load_ids": [load.load_id for load in binding.pressure_samples.loads],
        "maximum_wall_temperature_k": float(np.max(binding.wall_temperature_k)),
    }
    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "cylinder_vessel_history.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "This is a record/provenance bridge only; it does not recompute stress intensity, infer crack geometry, interpolate source data, or validate material/vessel performance.",
        ),
    )
