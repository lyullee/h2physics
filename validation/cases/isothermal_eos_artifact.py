"""Deferred persistence integrity case for reusable EOS table artifacts."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="isothermal-eos-table-artifact-roundtrip-integrity",
        profile="isothermal-eos",
        entrypoint=__name__ + ":validate_artifact",
        parameters={
            "density_nodes": 5,
            "temperature_nodes": 4,
            "maximum_artifact_bytes": 1_000_000,
            "corruption_byte_offset": 64,
        },
        invariants=(
            "a bounded table artifact contains only numeric NumPy arrays and canonical TOML metadata",
            "single-file publication is atomic and the source EOS identity, schema, axes, interpolation mode and checksums survive reload",
            "round-trip table and grid identities are unchanged without regenerating any EOS properties",
            "tampered payloads and source-identity mismatches are rejected before use",
            "out-of-envelope pressure and rho-T queries remain rejected after reload",
            "this storage integrity case does not qualify thermodynamic accuracy or a physical model",
        ),
    ),)


def validate_artifact(*, work_directory, density_nodes, temperature_nodes,
                      maximum_artifact_bytes, corruption_byte_offset):
    import io
    import zipfile
    from pathlib import Path

    from h2physics.thermo.isothermal_eos_artifact import (
        load_isothermal_eos_table,
        save_isothermal_eos_table,
    )
    from h2physics.thermo.isothermal_eos_table import (
        IsothermalEOSTable,
        IsothermalEOSTableQualification,
    )

    if (type(density_nodes) is not int or density_nodes < 2
            or type(temperature_nodes) is not int or temperature_nodes < 2
            or type(corruption_byte_offset) is not int or corruption_byte_offset < 0):
        raise ValueError("Artifact case dimensions and corruption offset must be bounded integers")
    density = np.geomspace(0.1, 10.0, density_nodes)
    temperature = np.linspace(250.0, 350.0, temperature_nodes)
    gas_constant = 4_124.0
    pressure = np.asarray([
        density * gas_constant * value for value in temperature
    ])
    sound = np.asarray([
        np.full_like(density, (gas_constant * value) ** 0.5)
        for value in temperature
    ])
    table = IsothermalEOSTable(
        density, temperature, pressure, sound,
        "synthetic-artifact-case:eos-v1", "log_linear",
    )
    artifact = Path(work_directory) / "isothermal-eos-table.npz"
    save_isothermal_eos_table(
        table, artifact, maximum_artifact_bytes=maximum_artifact_bytes,
    )
    restored, restored_receipt = load_isothermal_eos_table(
        artifact, expected_source_eos_identity=table.source_eos_identity,
        maximum_artifact_bytes=maximum_artifact_bytes,
    )
    if (restored_receipt is not None or restored.table_sha256 != table.table_sha256
            or restored.identity != table.identity):
        raise AssertionError("EOS table identity changed during artifact round-trip")
    sample_rho = float(density[1])
    sample_temperature = float(temperature[1])
    if restored.pressure_rho_t(sample_rho, sample_temperature) != table.pressure_rho_t(
            sample_rho, sample_temperature):
        raise AssertionError("EOS table query changed during artifact round-trip")
    historical_receipt = IsothermalEOSTableQualification(
        source_eos_identity=table.source_eos_identity,
        table_identity=table.identity,
        table_sha256=table.table_sha256,
        validation_point_count=32,
        seed=20301031,
        interpolation=table.interpolation,
        maximum_relative_pressure_error=0.001,
        maximum_relative_density_error=0.001,
        maximum_relative_sound_speed_error=0.001,
        maximum_relative_error_allowed=0.01,
        reference_seconds_per_query=0.0001,
        table_seconds_per_query=0.00001,
    )
    qualified_artifact = Path(work_directory) / "isothermal-eos-table-with-receipt.npz"
    save_isothermal_eos_table(
        table, qualified_artifact, qualification=historical_receipt,
        maximum_artifact_bytes=maximum_artifact_bytes,
    )
    qualified_table, loaded_receipt = load_isothermal_eos_table(
        qualified_artifact,
        expected_source_eos_identity=table.source_eos_identity,
        maximum_artifact_bytes=maximum_artifact_bytes,
    )
    if (qualified_table.identity != table.identity or loaded_receipt is None
            or loaded_receipt.table_identity != table.identity
            or not loaded_receipt.error_gate_passed):
        raise AssertionError("Matching historical qualification receipt did not survive round-trip")
    mismatched_receipt = IsothermalEOSTableQualification(
        source_eos_identity=table.source_eos_identity,
        table_identity="different-table-identity",
        table_sha256=table.table_sha256,
        validation_point_count=32,
        seed=20301031,
        interpolation=table.interpolation,
        maximum_relative_pressure_error=0.001,
        maximum_relative_density_error=0.001,
        maximum_relative_sound_speed_error=0.001,
        maximum_relative_error_allowed=0.01,
        reference_seconds_per_query=0.0001,
        table_seconds_per_query=0.00001,
    )
    try:
        save_isothermal_eos_table(
            table, Path(work_directory) / "isothermal-eos-mismatched-receipt.npz",
            qualification=mismatched_receipt,
            maximum_artifact_bytes=maximum_artifact_bytes,
        )
    except ValueError:
        mismatched_receipt_rejected = True
    else:
        raise AssertionError("Artifact accepted a qualification receipt for another table")
    try:
        load_isothermal_eos_table(
            artifact, expected_source_eos_identity="different-source-eos",
            maximum_artifact_bytes=maximum_artifact_bytes,
        )
    except ValueError:
        source_identity_rejected = True
    else:
        raise AssertionError("Artifact accepted a mismatched source EOS identity")
    # Offset is relative to numeric pressure-array bytes, not ZIP headers.
    # Rewriting with the normal ZIP writer refreshes CRCs while preserving the
    # original canonical manifest and all array/table qualification hashes.
    with zipfile.ZipFile(qualified_artifact) as container:
        members = {name: container.read(name) for name in container.namelist()}
    pressure_payload = np.load(io.BytesIO(members["pressure_pa.npy"]), allow_pickle=False)
    altered_pressure = pressure_payload.copy()
    numeric_bytes = altered_pressure.view(np.uint8).reshape(-1)
    if corruption_byte_offset >= numeric_bytes.size:
        raise ValueError("corruption_byte_offset lies outside the numeric pressure-array bytes")
    numeric_bytes[corruption_byte_offset] ^= 0x01
    altered_member = io.BytesIO()
    np.save(altered_member, altered_pressure, allow_pickle=False)
    members["pressure_pa.npy"] = altered_member.getvalue()
    corrupted = Path(work_directory) / "isothermal-eos-table-corrupted.npz"
    with zipfile.ZipFile(corrupted, "w", compression=zipfile.ZIP_STORED) as container:
        for name, payload in members.items():
            container.writestr(name, payload)
    with zipfile.ZipFile(corrupted) as container:
        if container.testzip() is not None:
            raise AssertionError("Corruption fixture must retain valid ZIP member CRCs")
    try:
        load_isothermal_eos_table(
            corrupted, maximum_artifact_bytes=maximum_artifact_bytes,
        )
    except ValueError as error:
        if str(error) != "EOS artifact checksum mismatch for pressure_pa":
            raise AssertionError("Expected semantic pressure-array checksum rejection") from error
        corruption_rejected = True
    else:
        raise AssertionError("Changed pressure-array data with stale hashes was accepted")
    for query in (
        lambda: restored.pressure_rho_t(float(density[0]) * 0.99,
                                        float(temperature[0])),
        lambda: restored.density_pt(float(restored.pressure_pa[-1, -1]) * 1.01,
                                    float(temperature[-1])),
    ):
        try:
            query()
        except ValueError:
            pass
        else:
            raise AssertionError("Reloaded EOS table permitted extrapolation")
    return ValidationOutcome(True, {
        "table_identity": restored.identity,
        "table_sha256": restored.table_sha256,
        "shape_temperature_density": restored.shape,
        "source_identity_rejected": source_identity_rejected,
        "corruption_rejected": corruption_rejected,
        "corruption_target": "pressure_pa numeric bytes; valid ZIP CRCs; original semantic hashes",
        "corruption_array_byte_offset": corruption_byte_offset,
        "historical_receipt_roundtrip": loaded_receipt is not None,
        "mismatched_receipt_rejected": mismatched_receipt_rejected,
        "no_extrapolation_verified": True,
        "artifact_size_bytes": artifact.stat().st_size,
    }, (
        "This is a synthetic storage-integrity case; it does not compare values to CoolProp.",
        "The artifact retains a source EOS identity and array/table hashes, but thermodynamic accuracy still requires a separate held-out EOS qualification.",
    ))
