"""Deferred synthetic parser contract for the BAM measurement export format."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="bam-jet-fire-text-parser",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_text_parser",
        invariants=(
            "synthetic BAM-style metadata and Data1 table are separated "
            "without losing source labels",
            "semicolon-delimited source rows preserve raw decimal-comma tokens",
            "numeric view and blank-cell mask reconstruct exactly from retained tokens",
            "declared channel-count mismatch and ambiguous numeric tokens are rejected",
            "temperature, flow and clock labels remain raw evidence without unit conversion "
            "or clock inference",
            "parser contract is ingestion evidence only, not validation of a fire or thermal model",
        ),
    ), ValidationCase(
        identifier="bam-jet-fire-unit-boundary-projection",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_unit_projection",
        invariants=(
            "seconds, voltage, kg/h mass flow and bar pressure labels produce only their explicit unit views",
            "pressure conversion remains dimensional and does not declare absolute/gauge basis",
            "Celsius and dimensionless/uncalibrated channels remain raw when the label semantics are ambiguous",
            "all normalized numeric channels retain their original source tokens",
            "unit normalization rejects finite source tokens whose converted values overflow",
            "synthetic channel projection is ingestion behavior and not fire-model validation",
        ),
    ),)


def validate_text_parser(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.data.bam_jet_fire import _parse_measurement_text

    source = (
        "Data info\n"
        "File name: synthetic.d7d\n"
        "Number of channels: 3\n"
        "Sample rate: 100\n"
        "\n"
        "Data1\n"
        "\n"
        "Time [s];Massenstrom H2 [kg/h];T_10_Platte - T [°C]\n"
        "0,00;0,500;23,4\n"
        "0,01;;24,2\n"
    )
    metadata, columns, raw_rows, values, valid = _parse_measurement_text(source)
    assert "Sample rate: 100" in metadata
    assert columns == (
        "Time [s]", "Massenstrom H2 [kg/h]", "T_10_Platte - T [°C]",
    )
    assert raw_rows == (("0,00", "0,500", "23,4"), ("0,01", "", "24,2"))
    assert np.allclose(values[0], (0.0, 0.5, 23.4))
    assert np.array_equal(valid, ((True, True, True), (True, False, True)))

    rejected = 0
    for invalid in (
        source.replace("Number of channels: 3", "Number of channels: 2"),
        source.replace("0,500", "0,5.00"),
        source.replace("T_10_Platte - T [°C]", "Massenstrom H2 [kg/h]"),
    ):
        try:
            _parse_measurement_text(invalid)
        except ValueError:
            rejected += 1
    assert rejected == 3
    return ValidationOutcome(True, {
        "synthetic_rows": len(raw_rows),
        "source_columns_preserved": len(columns),
        "invalid_schema_or_decimal_cases_rejected": rejected,
    }, (
        "Synthetic parser behavior only; the acquired publisher archive is not loaded "
        "by this case.",
        "Source labels remain unconverted and do not establish instrument calibration "
        "or thermal boundary conditions.",
    ))


def validate_unit_projection(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.data.bam_jet_fire import _build_unit_channels

    columns = (
        "Time [s]", "GG01 sensor [V]", "S1 [Bar]", "Massenstrom H2 [kg/h]",
        "T_10_Platte - T [°C]", "T_Platte_Avg [-]", "GG01 compensated [-]",
    )
    raw_rows = (
        ("0", "2,5E-6", "1,2", "3,6", "23,4", "22,1", "0,1"),
        ("0,01", "", "1,25", "", "23,5", "22,2", "0,2"),
    )
    normalized, raw_only = _build_unit_channels(columns, raw_rows)
    by_label = {channel.source_label: channel for channel in normalized}
    raw_by_label = {channel.source_label: channel for channel in raw_only}
    assert by_label["Time [s]"].values_si == (0.0, 0.01)
    assert by_label["GG01 sensor [V]"].values_si[0] == 2.5e-6
    assert by_label["S1 [Bar]"].values_si == (120000.0, 125000.0)
    assert by_label["Massenstrom H2 [kg/h]"].values_si == (0.001, None)
    assert by_label["Massenstrom H2 [kg/h]"].raw_tokens == ("3,6", "")
    assert by_label["S1 [Bar]"].semantic_boundary.startswith("reported pressure")
    assert raw_by_label["T_10_Platte - T [°C]"].raw_tokens == ("23,4", "23,5")
    assert raw_by_label["T_Platte_Avg [-]"].raw_tokens == ("22,1", "22,2")
    assert raw_by_label["GG01 compensated [-]"].raw_tokens == ("0,1", "0,2")
    overflow_rejected = False
    try:
        _build_unit_channels(("S1 [Bar]",), (("1e308",),))
    except ValueError:
        overflow_rejected = True
    assert overflow_rejected
    return ValidationOutcome(True, {
        "synthetic_source_rows": len(raw_rows),
        "normalized_channels": len(normalized),
        "raw_only_channels": len(raw_only),
        "raw_tokens_retained": True,
        "normalized_overflow_rejected": overflow_rejected,
    }, (
        "Synthetic unit projection only; no acquired BAM measurements are opened.",
        "Pressure basis, sensor calibration, temperature semantics and fire/target model inputs remain unresolved.",
    ))
