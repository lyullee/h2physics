"""Deferred pinned raw calibration ingestion; no import-time data access."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(identifier="geological-raw-calibration-lineage", profile="adsorption-data",
        entrypoint=__name__+":validate_contract", parameters={}, invariants=(
            "pinned original archive and exact raw table schemas",
            "source strings/member/line identities and explicit pressure roles",
            "missing helium differences remain absent; standard uncertainties converted without propagation")),)


def validate_contract(*, work_directory, **parameters):
    import os
    from dataclasses import FrozenInstanceError
    from pathlib import Path

    from h2physics.data.geological_calibration import load_geological_calibration

    root = os.environ.get("H2_CLUSTER_DATA_RAW_ROOT")
    if not root or not Path(root).is_absolute():
        raise ValueError("Supply the absolute separately staged raw-data snapshot root")
    archive_path = Path(root)/"geological-adsorption/zenodo-22305898/submission_package.zip"
    data = load_geological_calibration(archive_path)
    assert (len(data.hydrogen_rows), len(data.helium_rows), len(data.sample_rows)) == (18, 33, 4)
    assert data.pressure_basis == "reported; absolute-versus-gauge not qualified"
    assert data.hydrogen_rows and data.helium_rows and data.sample_rows
    for row in (*data.hydrogen_rows, *data.helium_rows, *data.sample_rows):
        source = dict(row.raw_fields)
        assert row.line_number >= 2 and source["material"] == row.material
        for quantity in row.quantities:
            token = source[quantity.source_column]
            assert (quantity.value is None) == (token.strip() == "")
            assert (quantity.missing_reason is not None) == (quantity.value is None)
            if quantity.source_column.endswith("_mbar") and quantity.value is not None:
                assert quantity.value == float(token)*100.
    try:
        data.helium_rows[0].material = "changed"
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise AssertionError("Raw calibration source identity was mutable")
    return ValidationOutcome(True, {"hydrogen_rows": len(data.hydrogen_rows),
        "helium_rows": len(data.helium_rows), "sample_rows": len(data.sample_rows)},
        ("Raw observation ingestion only; no calibration fit, EOS or excess-to-absolute correction",))
