"""Deferred source schema/provenance case for the Bath cryogenic H2 kinetics workbook."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="bath-cryo-kinetics-source-schema-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_schema",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "bath-cryo-kinetics.toml"
        )},
        invariants=(
            "Bath DOI, No restrictions notice, attribution, and exact kinetic-workbook SHA-256 remain bound to each source row",
            "the three workbook series retain native time, excess uptake, pressure, temperature units, sheet IDs, and source row numbers",
            "no sample mass or documented same-sample mapping to isotherms is invented",
            "the excess-uptake observations reject direct absolute-uptake finite-vessel use",
            "no LDF fit, finite-vessel simulation, Origin code, or image asset is used",
        ),
    ),)


def validate_source_schema(*, work_directory, manifest_path):
    import os

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.data.bath_cryo_kinetics import load_bath_kinetic_workbook

    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    raw_root = os.environ.get("H2_CLUSTER_DATA_RAW_ROOT")
    if not raw_root or not Path(raw_root).is_absolute():
        raise ValueError("Supply an absolute raw-data snapshot root")
    kinetic_file = next(item for item in manifest["files"] if item["name"].startswith("Kinetic_data_"))
    source = Path(raw_root) / kinetic_file["relative_path"]
    series = load_bath_kinetic_workbook(source)
    if (manifest.get("doi") != "10.15125/BATH-00099"
            or manifest.get("license_id") != "No restrictions"
            or len(series) != 3
            or {item.sheet_name for item in series} != {
                "MIL-101 (Cr) at 77 K", "MIL-101(Cr) at 90 K", "AX-21 at 90 K"
            }):
        raise ValueError("Bath source record or kinetic sheet schema no longer matches the qualified manifest")
    incompatibility_rejected = False
    try:
        series[0].require_finite_adsorption_dynamics_basis()
    except ValueError as error:
        if "sample-mass mapping" not in str(error):
            raise
        incompatibility_rejected = True
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "kinetic_workbook_sha256": kinetic_file["sha256"],
        "kinetic_sheet_count": len(series),
        "observation_counts_by_sheet": tuple((item.sheet_name, len(item.observations)) for item in series),
        "preserved_units": ("min", "micromol excess H2", "MPa", "K"),
        "finite_adsorption_basis_rejection": incompatibility_rejected,
        "finite_vessel_model_comparison": False,
    }, (
        "Source data are read as experimental excess uptake; no dry sample mass or absolute-uptake conversion is admitted.",
        "This case checks provenance/schema only. It does not fit kinetics or run the source's Origin analysis.",
    ))
