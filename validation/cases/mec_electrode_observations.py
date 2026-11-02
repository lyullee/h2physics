"""Deferred source/schema checks for the CORA MEC electrode observations.

These checks are not electrochemical model validation. They verify the pinned
publisher files, source coordinates, declared unit conversions and unresolved
schema fields without fitting a model or interpreting performance.
"""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

EXPECTED_HASHES = {
    "LSV_Catalysts_CarbonCloth.ods": (
        "22116a643f43ef981835550c04a9fac14341420bd7a0da751c6e9d1539f98256"
    ),
    "EIS_Catalysts_Electrodes.ods": (
        "2ae4220f58c02fb7f29a882281c3006990bf6cffd75f9395ee5f14f6f12ca1f3"
    ),
    "Current density_Alloys.ods": (
        "940b8ba42266774077cc488c19f1700e9fec921fa00b9d3ed7f8790830993996"
    ),
}


def cases():
    return (
        ValidationCase(
            identifier="mec-electrode-data-provenance",
            profile="microbial-observations",
            entrypoint=__name__ + ":validate_provenance",
            invariants=(
                "publisher ODS hashes and source DOI are retained",
                "LSV source rows and potential/current units are preserved",
                "source-row tokens reconstruct the retained numeric values and masks",
                "a copied series cannot reseal substituted observation values under the original source hash",
                "source-bound series and dataset objects are issued only by the checksum-validating reader",
                "current-density rows retain the incomplete terminal record diagnostic",
                "EIS paired components retain their source header and have no frequency axis",
                "no whole-cell H2 yield or electrochemical performance validation is inferred",
            ),
        ),
        ValidationCase(
            identifier="mec-electrode-data-integrity",
            profile="microbial-observations",
            entrypoint=__name__ + ":validate_integrity",
            invariants=(
                "changed source bytes are rejected before ODS parsing",
                "directly constructed traces cannot claim a different reviewed workbook hash",
                "the original local raw snapshot remains unchanged",
            ),
        ),
    )


def _root():
    import os
    from pathlib import Path

    value = os.environ.get("H2_CLUSTER_DATA_RAW_ROOT")
    if not value:
        raise ValueError("Supply the actual cluster licensed raw-data snapshot root")
    root = Path(value)
    if not root.is_absolute():
        raise ValueError("The cluster raw-data snapshot path must be absolute")
    return root


def _numeric_pair_trace(trace):
    import math

    assert trace.frequency_hz is None
    assert len(trace.source_rows) == 38
    assert len(trace.real_impedance_ohm) == len(trace.reported_second_component_ohm) == 38
    assert all(math.isfinite(value) for value in trace.real_impedance_ohm)
    assert all(math.isfinite(value) for value in trace.reported_second_component_ohm)
    assert trace.source_second_header == "#NAME?"


def validate_provenance(*, work_directory):
    from dataclasses import replace
    import json
    from pathlib import Path

    import numpy as np

    from h2physics.core import Origin
    from h2physics.data.mec_electrodes import load_cora_mec_electrode_dataset

    dataset = load_cora_mec_electrode_dataset(_root())
    assert dataset.source_doi == "10.34810/data2866"
    assert dataset.archive_version == "1.0"
    assert dict(dataset.source_sha256) == EXPECTED_HASHES
    assert len(dataset.lsv_series) == 6
    assert len(dataset.current_density_series) == 6
    assert len(dataset.impedance_traces) == 8

    source_series = dataset.lsv_series[0]
    altered_values = source_series.observations.values.copy()
    altered_values[0, 1] += 1.
    altered_table = replace(source_series.observations, values=altered_values)
    forged_values_rejected = False
    try:
        replace(source_series, observations=altered_table)
    except ValueError:
        forged_values_rejected = True
    assert forged_values_rejected

    lsv_rows = tuple(f"Hoja1!{row}" for row in range(2, 3003))
    lsv_counts = []
    for series in dataset.lsv_series:
        table = series.observations
        assert table.row_ids == lsv_rows
        assert tuple(variable.name for variable in table.variables) == (
            "potential_v",
            "current_a",
        )
        assert tuple(variable.unit for variable in table.variables) == ("V", "A")
        assert table.origins == (Origin.MEASURED, Origin.MEASURED)
        assert np.all(table.valid)
        assert series.source_column in range(2, 8)
        assert table.values.shape == (3001, 2)
        lsv_counts.append(table.values.shape[0])

    current_rows = tuple(f"Hoja1!{row}" for row in range(2, 3676))
    current_counts = []
    for series in dataset.current_density_series:
        table = series.observations
        assert table.row_ids == current_rows
        assert tuple(variable.name for variable in table.variables) == (
            "reported_time_s",
            "current_density_a_m2",
        )
        assert tuple(variable.unit for variable in table.variables) == ("s", "A/m2")
        assert table.origins == (Origin.MEASURED, Origin.MEASURED)
        assert np.all(table.valid[:-1])
        assert table.valid[-1, 0] and not table.valid[-1, 1]
        assert np.isnan(table.values[-1, 1])
        assert table.values.shape == (3674, 2)
        assert series.source_column in range(2, 8)
        current_counts.append(int(np.count_nonzero(table.valid[:, 1])))

    for trace in dataset.impedance_traces:
        _numeric_pair_trace(trace)
        assert trace.source_rows == tuple(range(3, 41))

    issue_signatures = {
        (
            issue.source_file,
            issue.worksheet,
            issue.source_row,
            issue.source_column,
            issue.raw_token,
        )
        for issue in dataset.issues
    }
    for column in range(2, 8):
        assert (
            "Current density_Alloys.ods",
            "Hoja1",
            3675,
            column,
            "",
        ) in issue_signatures
    for column in range(2, 17, 2):
        assert (
            "EIS_Catalysts_Electrodes.ods",
            "Hoja1",
            2,
            column,
            "#NAME?",
        ) in issue_signatures

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    metrics = {
        "source_doi": dataset.source_doi,
        "archive_version": dataset.archive_version,
        "source_file_count": len(dataset.source_sha256),
        "lsv_series": len(dataset.lsv_series),
        "lsv_rows_per_series": lsv_counts,
        "current_density_series": len(dataset.current_density_series),
        "current_density_complete_response_rows_per_series": current_counts,
        "current_density_total_rows_per_series": [
            series.observations.values.shape[0] for series in dataset.current_density_series
        ],
        "impedance_traces": len(dataset.impedance_traces),
        "unresolved_source_issues": len(dataset.issues),
        "substituted_series_values_rejected": forged_values_rejected,
    }
    (destination / "mec-electrode-observations.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Source/schema/unit checks only; no parameter fit, circuit identification, "
            "or performance ranking.",
            "The EIS records contain no frequency coordinates; whole-cell H2 production, "
            "Faradaic efficiency, microbial activity and validation remain unavailable.",
        ),
    )


def validate_integrity(*, work_directory):
    import hashlib
    from dataclasses import replace
    from pathlib import Path

    from h2physics.data.mec_electrodes import (
        CURRENT_DENSITY_FILE,
        EIS_FILE,
        LSV_FILE,
        MecElectrodeDataset,
        MecElectrodeSeries,
        SOURCE_DIRECTORY,
        SOURCE_SHA256,
        load_cora_mec_electrode_dataset,
    )

    source_root = _root()
    original_directory = source_root / SOURCE_DIRECTORY
    source_files = (LSV_FILE, EIS_FILE, CURRENT_DENSITY_FILE)
    original_bytes = {name: (original_directory / name).read_bytes() for name in source_files}
    for name, payload in original_bytes.items():
        assert hashlib.sha256(payload).hexdigest() == EXPECTED_HASHES[name]

    dataset = load_cora_mec_electrode_dataset(source_root)
    series = dataset.lsv_series[0]
    direct_series_rejected = False
    try:
        MecElectrodeSeries(
            series.series_id, series.electrode_label, series.source_file,
            series.source_sha256, series.source_column, series.observations,
            series.raw_coordinate_tokens, series.raw_response_tokens,
        )
    except ValueError:
        direct_series_rejected = True
    assert direct_series_rejected
    direct_dataset_rejected = False
    try:
        MecElectrodeDataset(
            dataset.source_doi, dataset.archive_version, dataset.dataset_license,
            dataset.lsv_series, dataset.impedance_traces,
            dataset.current_density_series, dataset.issues, dataset.source_sha256,
        )
    except ValueError:
        direct_dataset_rejected = True
    assert direct_dataset_rejected
    try:
        replace(series, source_sha256=SOURCE_SHA256[EIS_FILE])
    except ValueError as error:
        assert "checksum-validating" in str(error)
    else:
        raise AssertionError("A copied loader-issued LSV series accepted a substituted source hash")

    altered_values = series.observations.values.copy()
    altered_values[0, 1] += 1.
    altered_table = replace(series.observations, values=altered_values)
    try:
        replace(series, observations=altered_table)
    except ValueError as error:
        assert "checksum-validating" in str(error)
    else:
        raise AssertionError("A copied source series resealed substituted measurement values")

    trace = dataset.impedance_traces[0]
    try:
        replace(trace, source_rows=(1, *trace.source_rows[1:]))
    except ValueError as error:
        assert "source row" in str(error)
    else:
        raise AssertionError("An impedance trace accepted a header as an observation row")

    forged_eis = replace(trace, source_rows=tuple(range(4, 42)))
    try:
        replace(dataset, impedance_traces=(forged_eis, *dataset.impedance_traces[1:]))
    except ValueError as error:
        assert "checksum-validating" in str(error)
    else:
        raise AssertionError("A copied loader-issued dataset accepted changed EIS row identities")

    alternate_root = Path(work_directory) / "tampered-raw-root"
    alternate_directory = alternate_root / SOURCE_DIRECTORY
    alternate_directory.mkdir(parents=True, exist_ok=True)
    for name, payload in original_bytes.items():
        (alternate_directory / name).write_bytes(payload)
    lsv_path = alternate_directory / LSV_FILE
    payload = lsv_path.read_bytes()
    lsv_path.write_bytes(payload[:-1] + bytes((payload[-1] ^ 1,)))

    try:
        load_cora_mec_electrode_dataset(alternate_root)
    except ValueError as error:
        assert "SHA-256" in str(error)
    else:
        raise AssertionError("Changed ODS bytes were accepted")

    for name, payload in original_bytes.items():
        path = original_directory / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_HASHES[name]
        assert path.read_bytes() == payload
    return ValidationOutcome(
        accepted=True,
        metrics={
            "tampered_source_rejected": 1,
            "forged_series_identity_rejected": 1,
            "duplicate_source_row_rejected": 1,
            "invalid_impedance_row_rejected": 1,
            "shifted_eis_source_group_rejected": 1,
            "direct_series_constructor_rejected": int(direct_series_rejected),
            "direct_dataset_constructor_rejected": int(direct_dataset_rejected),
            "substituted_series_values_rejected": 1,
            "original_sources_unchanged": 1,
        },
        limitations=("Dataset integrity guard only; no electrochemical model or accuracy test.",),
    )
