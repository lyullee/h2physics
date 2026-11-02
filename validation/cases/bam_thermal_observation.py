"""Deferred BAM plate-temperature to existing thermal-target comparison case."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


_ATTACHMENT_ROOT = "/scratch/r1021a02/h2physics-source-attachments/bam-hydrogen-jet-fire/21026781"


def cases():
    return (ValidationCase(
        identifier="bam-fire-plate-temperature-thermal-target-observation-bridge",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_observation_bridge",
        parameters={
            "archive_path": _ATTACHMENT_ROOT + "/H2_Data.zip",
            "metadata_path": _ATTACHMENT_ROOT + "/zenodo-record.json",
        },
        invariants=(
            "BAM archive/member and Zenodo CC BY 4.0 metadata receipts remain hash-bound",
            "exact selected FRP plate thermocouple tokens are interpreted as absolute Celsius only under synthetic caller evidence",
            "source clock offset and sensor-to-target mapping remain explicit caller inputs",
            "source temperatures compare to an existing target trace with bounded interpolation and no extrapolation",
            "the synthetic target trace does not establish fire flux or validate the fire/target model",
        ),
    ),)


def validate_observation_bridge(*, work_directory, **parameters):
    import hashlib
    import json
    from pathlib import Path

    from h2physics.adapters.bam_thermal_observation import compare_bam_plate_temperature_to_target
    from h2physics.adapters.thermal_target import (
        IncidentHeatHistory, LumpedThermalTarget, ThermalTargetTolerances, run_thermal_target,
    )
    from h2physics.core import Origin
    from h2physics.data import DATASETS
    from h2physics.data.bam_jet_fire import load_bam_jet_fire_text, project_bam_jet_fire_units
    from h2physics.data.models import Dataset, RemoteFile

    archive_path = parameters.get("archive_path")
    metadata_path = parameters.get("metadata_path")
    if not all(isinstance(item, str) and item.strip() for item in (archive_path, metadata_path)):
        raise ValueError("Stage the BAM archive and exact captured Zenodo metadata JSON")
    payload = Path(metadata_path).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    expected_metadata_sha256 = "646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0"
    if digest != expected_metadata_sha256:
        raise ValueError("Staged BAM Zenodo metadata differs from its pinned source response")
    metadata = json.loads(payload)
    metadata_block = metadata["metadata"]
    file_record = metadata["files"][0]
    remote = RemoteFile(file_record["key"], file_record["links"]["self"],
                        file_record["size"], "md5", file_record["checksum"].removeprefix("md5:"))
    seed = next(item for item in DATASETS if item.key == "bam-hydrogen-jet-fire")
    if seed.key != "bam-hydrogen-jet-fire":
        raise ValueError("Resolved BAM metadata must bind to the admitted data-catalog record")
    # Dataset.origin is a repository classification string; the BAM reader
    # deliberately admits only the exact "measured" representation.
    dataset = Dataset("bam-hydrogen-jet-fire", metadata_block["title"], metadata["doi"], "21026781",
        tuple(item["name"] for item in metadata_block["creators"]), "CC-BY-4.0",
        "https://creativecommons.org/licenses/by/4.0/", "https://zenodo.org/api/records/21026781",
        digest, "measured", seed.families, (remote,), payload)
    source = load_bam_jet_fire_text(archive_path, dataset=dataset,
        member_path="H2_Data/FRP_exp/BAM6_H2_1590_04.txt",
        expected_sha256="c4e199a20960174845f27dbbb6521b65c797740ba3f503463ee96073cf2d8bed")
    projection = project_bam_jet_fire_units(source)

    history = IncidentHeatHistory(
        edges_s=(0., 1.), incident_flux_w_m2=(0.,), clock_id="synthetic-bam-clock",
        frame_id="synthetic-target-frame", source_id="synthetic-target-input",
        boundary_id="synthetic-zero-flux-boundary", evidence_id="synthetic-only",
        origin=Origin.SYNTHETIC, source_owner=object())
    target = LumpedThermalTarget(area_m2=0.01, heat_capacity_j_k=100.,
        initial_temperature_k=300., absorptivity=0., emissivity=0.,
        convective_coefficient_w_m2_k=0., ambient_temperature_k=300.,
        radiant_surroundings_temperature_k=300., minimum_temperature_k=250.,
        maximum_temperature_k=800., material_evidence_id="synthetic-target-material",
        geometry_evidence_id="synthetic-target-geometry",
        convection_evidence_id="synthetic-zero-convection",
        radiation_evidence_id="synthetic-zero-radiation", origin=Origin.SYNTHETIC)
    model = run_thermal_target(history, target,
        ThermalTargetTolerances(1e-8, 1e-8, 1e-10), maximum_step_s=0.005)
    comparison = compare_bam_plate_temperature_to_target(projection, model,
        channel_label="T_10_Platte - T [°C]", source_window_s=(0., 0.05),
        clock_offset_s=0., temperature_interpretation_evidence_id="synthetic-case-assumes-absolute-Celsius",
        target_sensor_mapping_evidence_id="synthetic-case-plate-channel-mapped-to-uniform-target",
        clock_alignment_evidence_id="synthetic-case-zero-clock-offset",
        interpolation_evidence_id="synthetic-case-linear-between-retained-model-samples")
    return ValidationOutcome(True, {
        "dataset_doi": projection.dataset_doi,
        "license_id": projection.license_id,
        "archive_sha256": projection.source_archive_sha256,
        "member_sha256": projection.member_sha256,
        "channel": comparison.channel_label,
        "compared_rows": len(comparison.points),
        "first_source_time_s": comparison.points[0].source_time_s,
        "first_observation_k": comparison.points[0].observed_temperature_k,
        "first_synthetic_prediction_k": comparison.points[0].predicted_temperature_k,
        "flux_inferred_from_measurement": False,
        "physical_validation_claimed": False,
    }, (
        "The model history and material/target coefficients are synthetic; comparison tests the typed observation interface only.",
        "Source Celsius channels require caller interpretation as absolute temperatures; thermocouple calibration and exact plate mapping are not established.",
        "This case does not infer incident flux, reproduce the experiment, or validate fire/thermal-target physics.",
    ))
