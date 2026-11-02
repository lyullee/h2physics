"""Deferred source-preservation case for the simulated hydride PCT workbooks."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydride-pct-xlsx-source-preservation",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_workbooks",
        invariants=(
            "each local workbook matches its reviewed exact filename, byte count and SHA-256",
            "ABS and DES sheets retain their source dimensions and raw first three rows",
            "streamed rows preserve formulas and one-based workbook row positions",
            "source pressure and concentration values are not converted or fitted",
            "simulated source replay is not independent equilibrium validation",
        ),
    ),)


def validate_source_workbooks(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.data.hydride_pct import load_hydride_pct_workbook

    root = Path(__file__).resolve().parents[2]
    source_dir = root / "data" / "raw" / "hydride-pct-simulation" / "1"
    workbook_count = 0
    sheet_count = 0
    streamed_rows = 0
    formula_cells = 0
    for source_path in sorted(source_dir.glob("*.xlsx")):
        workbook = load_hydride_pct_workbook(source_path)
        workbook_count += 1
        for sheet in workbook.sheet_infos:
            sheet_count += 1
            assert len(sheet.initial_rows) == 3
            assert len(sheet.initial_rows[0]) == sheet.max_column
            last_row = 0
            for row in workbook.iter_rows(sheet.name):
                assert row.row_number == last_row + 1
                assert len(row.values) == sheet.max_column
                formula_cells += sum(
                    isinstance(value, str) and value.startswith("=")
                    for value in row.values
                )
                streamed_rows += 1
                last_row = row.row_number
            assert last_row == sheet.max_row
        workbook.require_current()

    if workbook_count != 5 or sheet_count != 10:
        raise ValueError("Expected the five receipted PCT workbooks and ten worksheets")
    return ValidationOutcome(True, {
        "workbooks": workbook_count,
        "worksheets": sheet_count,
        "streamed_rows": streamed_rows,
        "formula_cells_preserved": formula_cells,
        "pressure_or_loading_conversion": False,
        "independent_validation_claim": False,
    }, (
        "Source-reader integrity evidence only; no isotherm values are fitted or compared.",
        "The source is simulated and its pressure and uptake bases remain unresolved.",
    ))
