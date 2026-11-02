"""Remaining FDS/explosion model-link gap after selected summary acquisition."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

DOI = "10.18710/WSKBIJ"
EXPECTED = {
    "00_Readme.txt": ("doi:10.18710/WSKBIJ/X2UO8B", "6.6 KB", "5642ccb734e8449bf52c0be83e4d0f23"),
    "Experimental_results_.xlsx": (
        "doi:10.18710/WSKBIJ/NHJV9H", "20.7 KB", "73ee4f29ca08612f46b7a37980cbe4df",
    ),
    "Test001.txt": (
        "doi:10.18710/WSKBIJ/PIQIIP", "207.9 MB", "6a2b1e93513c33d9400ba8abf4b9d082",
    ),
}


def cases():
    return (ValidationCase(
        identifier="large-scale-h2-explosion-fds-observation-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "large-scale-open-hydrogen-explosion.toml"
        )},
        invariants=(
            "the official CC0 dataset identity and acquired README/workbook/Test001 receipts remain source-bound",
            "the workbook supplies summary pressure values but not time-resolved channels, sensor coordinates or complete per-test source histories",
            "the existing FDS boundary does not claim nozzle expansion, flame acceleration or explosion overpressure",
            "no model comparison is made from workbook summary values",
        ),
    ),)


def validate_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    candidates = record.get("selected_candidates", ())
    if (record.get("doi") != DOI or record.get("version") != "1.0"
            or record.get("license_id") != "CC0-1.0"
            or record.get("rights_permitted") is not True
            or record.get("listed_file_count") != 59
            or record.get("listed_total_bytes") != 96_861_179_314
            or record.get("acquisition_status") != "readme_summary_and_test001_trace_acquired"
            or record.get("acquired_bytes") != 207_881_806
            or record.get("model_linkage_status")
            != "raw_single_trace_ingested_no_quantitative_model_comparison"
            or record.get("model_link_case") != "large-scale-h2-explosion-fds-observation-link-gap"
            or len(candidates) != len(EXPECTED)):
        raise ValueError("DataverseNO record identity, CC0 status, or acquired scope changed")
    by_name = {entry.get("name"): entry for entry in candidates}
    if set(by_name) != set(EXPECTED):
        raise ValueError("Selected small DataverseNO file metadata changed")
    expected_shas = {
        "00_Readme.txt": "cb7d4651d700cbd8da67cb69c3cec63ebabc4ffadbf6d5e1a2a38d63b622fb99",
        "Experimental_results_.xlsx": "5ca3813fd7e9ade6c0d1aa623d2a7f5346760334b1c8b014a4ea3235ae5dbd34",
        "Test001.txt": "c5f2a991c611dff77f3f2c027da2a1505e1c7843b212cdddd90b0eb9b44ec703",
    }
    expected_sizes = {
        "00_Readme.txt": 6_753,
        "Experimental_results_.xlsx": 21_165,
        "Test001.txt": 207_853_888,
    }
    for name, (persistent_id, reported_size, md5) in EXPECTED.items():
        item = by_name[name]
        if (item.get("persistent_id") != persistent_id
                or item.get("size_bytes_reported") != reported_size
                or item.get("size_bytes") != expected_sizes[name]
                or item.get("publisher_md5") != md5
                or item.get("status") != "acquired"
                or item.get("sha256") != expected_shas[name]):
            raise ValueError("Selected small file no longer matches its acquired publisher/local receipt")
    missing = tuple(record.get("missing_model_link_evidence", ()))
    if len(missing) != 6:
        raise ValueError("DataverseNO FDS-link evidence gap changed")
    return ValidationOutcome(True, {
        "doi": DOI,
        "license_id": record["license_id"],
        "listed_file_count": record["listed_file_count"],
        "listed_bytes": record["listed_total_bytes"],
        "acquired_bytes": record["acquired_bytes"],
        "selected_candidate_files": tuple(sorted(EXPECTED)),
        "selected_candidate_bytes": record["acquired_bytes"],
        "summary_and_trace_are_separate_ingestion_contracts": True,
        "model_link_target": record["model_link_target"],
        "model_linkage_admitted": False,
        "missing_evidence": missing,
    }, (
        "The CC0 README, workbook summary, and one Test001 trace were acquired; no other test trace or video was selected.",
        "The workbook's four pressure summaries lack sensor coordinates and a physical clock; no pressure, dispersion or combustion comparison is claimed.",
    ))
