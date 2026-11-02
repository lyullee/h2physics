"""Authored miniature compilation records; no external observations bundled."""

import csv
from dataclasses import replace

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.embrittlement import (
    COMPOSITION_FILE,
    COMPOSITION_HEADERS,
    HEADERS,
    MAIN_FILE,
    MAP_FILE,
    MAP_HEADERS,
    EmbrittlementCollection,
    paired_property_check,
)
from h2physics.data.pressure_peaking import file_sha256
from h2physics.observations import split_experiments


def write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def fixture(tmp_path):
    records = []
    for number, (prop, reference, exposed) in enumerate((
            ("reduction of area", "80", "40"), ("elongation", "60", "30"),
            ("tensile strength", "800", "400"), ("notched tensile strength", "900", "450"),
            ("plastic strain to failure", "1.2", ".6"), ("reduction of area", "", "")), 1):
        row = dict.fromkeys(HEADERS, "")
        row.update(record_id=f"authored-{number}", source_id="S1" if number < 4 else "S2",
            source_short="authored table", alloy="authored-steel", heat="heat-A", material_family="authored",
            product_form="plate", is_weld="no", zone="base metal", hydrogen_exposure="gaseous precharge",
            h2_pressure_MPa="12", hydrogen_content_wppm="25", charging_time_h="3",
            test_temperature_K="300", test_temperature_C="26.9", strain_rate_per_s="1e-5",
            test_type="tensile", property_name=prop, reference_environment="air",
            property_reference=reference, property_h2=exposed, relative_ratio=".5",
            embrittlement_flag="source band", C_wt_pct=".08", Cr_wt_pct="20", Ni_wt_pct="12",
            composition_basis="heat_analysis", composition_source="authored primary composition",
            ni_equivalent="30", ni_equivalent_reported="31", md30_calculated="-50",
            derived_assumptions="Mo assumed zero by source calculation", derived="relative_ratio;ni_equivalent;md30_calculated",
            verified="no", notes="authored\nquoted multiline test context")
        records.append(tuple(row[h] for h in HEADERS))
    composition = dict.fromkeys(COMPOSITION_HEADERS, "")
    composition.update(comp_key="authored-composition", material_label="authored material",
        composition_basis="nominal", derive_nieq="yes", derive_md30="yes",
        composition_source="authored linked table", C="0.080", Cr="18", Ni="12")
    write_csv(tmp_path/MAIN_FILE, HEADERS, records)
    write_csv(tmp_path/COMPOSITION_FILE, COMPOSITION_HEADERS, [tuple(composition[h] for h in COMPOSITION_HEADERS)])
    write_csv(tmp_path/MAP_FILE, MAP_HEADERS, [(f"authored-{i}", "authored-composition") for i in range(1, 6)])
    return tmp_path


def opened(directory, **kwargs):
    hashes = {n: file_sha256(directory/n) for n in (MAIN_FILE, COMPOSITION_FILE, MAP_FILE)}
    return EmbrittlementCollection(directory, source_id="authored-compiled-study", expected_sha256=hashes,
                                   require_complete=False, **kwargs)


def test_property_specific_units_pairs_pressure_and_charging_roles_are_separate(tmp_path):
    with opened(fixture(tmp_path)) as source:
        ra = next(source.iter_blocks("reduction of area"))
        table = ra.observations
        assert table.column("property_reference")[0][0] == .8
        assert table.column("property_h2")[0][0] == .4
        assert table.column("exposure_pressure_pa")[0][0] == 12e6
        assert "absolute/gauge" in table.variables[1].basis_id
        assert table.column("material_hydrogen_mass_fraction")[0][0] == pytest.approx(25e-6)
        assert table.column("charging_duration_s")[0][0] == 10800
        assert table.column("test_temperature_k_reported")[0][0] == 300
        assert table.column("test_temperature_k_from_C")[0][0] == pytest.approx(300.05)
        assert table.column("md30_index_k")[0][0] == pytest.approx(223.15)
        assert ra.numeric_source_fields[1] == "h2_pressure_MPa"
        assert table.variables[-1].quantity != table.variables[4].quantity
        assert "not_automatically_test_pressure" in " ".join(ra.records[0].issues)
        stress = next(source.iter_blocks("tensile strength")).observations
        assert stress.column("property_reference")[0][0] == 800e6
        assert stress.variables[7].unit == "Pa"
        plastic = next(source.iter_blocks("plastic strain to failure")).observations
        assert plastic.column("property_reference")[0][0] == 1.2
        assert plastic.variables[7].unit == "source_unit_unresolved"
        assert plastic.origins[7] is Origin.UNRESOLVED
        assert table.origins[-2] is Origin.UNRESOLVED


def test_source_record_line_ids_notes_and_missing_pair_are_preserved(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks("reduction of area"))
        assert len(block.records) == 2
        assert block.records[0].source.record_number == 2
        assert block.records[0].source.first_line == 2 and block.records[0].source.last_line == 3
        assert block.records[0].source.file_sha256 in block.observations.row_ids[0]
        assert "authored-1" in block.observations.row_ids[0]
        assert "\n" in block.records[0].fields["notes"]
        assert not block.observations.valid[1, 7] and not block.observations.valid[1, 8]
        assert block.observations.valid[1, 9]  # Ratio-only observation retained.
        assert "without absolute pair" in block.records[1].numeric_role("relative_ratio")
        assert block.records[1].linked_composition is None
        with pytest.raises(ValueError, match="time history"):
            block.as_time_series()


def test_linked_composition_is_not_an_overwrite_or_an_inferred_zero(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks("reduction of area"))
        record = block.records[0]
        assert record.material_group_id == "authored-composition"
        assert [d.field for d in record.composition_discrepancies] == ["Cr", "composition_basis", "composition_source"]
        assert record.fields["Cr_wt_pct"] == "20"
        linked = source.composition_observations(record.linked_composition)
        assert linked.column("Cr")[0][0] == .18
        assert block.observations.column("Cr_mass_fraction_primary")[0][0] == .2
        assert not linked.column("Mo")[1][0] and not block.observations.column("Mo_mass_fraction_primary")[1][0]
        assert record.fields["derived_assumptions"]
        assert record.linked_composition.row_id != record.composition_mapping.row_id
        assert not linked.values.flags.writeable


def test_dependent_studies_materials_and_property_records_cannot_be_random_holdouts(tmp_path):
    with opened(fixture(tmp_path)) as source:
        records = source.records
        assert {r.reported_source_id for r in records} == {"S1", "S2"}
        block = next(source.iter_blocks("reduction of area"))
        assert len(set(block.observations.experiment_ids)) == 1
        assert records[0].material_group_id == records[1].material_group_id
        with pytest.raises(ValueError, match="proper subset"):
            split_experiments(block.observations, set(block.observations.experiment_ids))


def test_same_export_ratio_operator_preserves_masks_and_detects_disagreement(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks("reduction of area"))
        check = paired_property_check(block)
        assert check.available.tolist() == [True, False]
        assert check.within_tolerance.tolist() == [True, False]
        assert check.calculated_ratio[0] == .5 and check.residual[0] == 0
        values = block.observations.values.copy()
        values[0, 9] = .6
        changed = replace(block, observations=replace(block.observations, values=values))
        result = paired_property_check(changed)
        assert result.residual[0] == pytest.approx(-.1)
        assert result.available[0] and not result.within_tolerance[0]
        assert not result.residual.flags.writeable
        with pytest.raises(ValueError):
            paired_property_check(block, tolerance=float("nan"))


def test_filters_and_block_partitions_preserve_original_source_identity(tmp_path):
    with opened(fixture(tmp_path)) as source:
        whole = next(source.iter_blocks("reduction of area"))
        pieces = tuple(source.iter_blocks("reduction of area", block_rows=1, reference_environment="air",
                                         zone="base metal", hydrogen_exposure="gaseous precharge"))
        np.testing.assert_equal(np.concatenate([b.observations.values for b in pieces]), whole.observations.values)
        assert tuple(i for b in pieces for i in b.observations.row_ids) == whole.observations.row_ids
        assert tuple(source.iter_blocks("reduction of area", reference_environment="helium")) == ()
        for kwargs in ({"block_rows": 0}, {"block_rows": 513}, {"block_rows": True}):
            with pytest.raises(ValueError):
                tuple(source.iter_blocks("reduction of area", **kwargs))
        with pytest.raises(ValueError):
            tuple(source.iter_blocks("fatigue crack growth"))


def test_negative_and_nonfinite_reported_values_survive_with_explicit_masks(tmp_path):
    directory = fixture(tmp_path)
    lines = list(csv.reader((directory/MAIN_FILE).open(encoding="utf-8", newline="")))
    lines[1][HEADERS.index("property_h2")] = "-40"
    lines[1][HEADERS.index("h2_pressure_MPa")] = "1e308"
    lines[1][HEADERS.index("test_temperature_C")] = "-300"
    write_csv(directory/MAIN_FILE, HEADERS, lines[1:])
    with opened(directory) as source:
        block = next(source.iter_blocks("reduction of area"))
        assert block.observations.column("property_h2")[0][0] == -.4
        assert not block.observations.column("property_h2")[1][0]
        assert np.isinf(block.observations.column("exposure_pressure_pa")[0][0])
        assert block.invalid_reasons[0][1] == "unit_conversion_nonfinite"
        assert block.invalid_reasons[0][5] == "source_nonpositive_temperature"
        assert not paired_property_check(block).available[0]


def test_native_workbook_formulas_missing_caches_and_source_cells_are_not_calculated(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from scripts.check_embrittlement_data import workbook_audit

    directory = fixture(tmp_path)
    primary = list(csv.reader((directory/MAIN_FILE).open(encoding="utf-8", newline="")))[1:]
    path = directory/"authored.xlsx"
    workbook = openpyxl.Workbook()
    data = workbook.active
    data.title = "Data"
    data.append((*HEADERS, "authored helper A", "authored helper B"))
    for row in primary:
        data.append((*[v or None for v in row], "=1+2", "=2+3"))
    summary = workbook.create_sheet("Summary")
    summary.append(("Authored summary", "=3+4"))
    workbook.save(path)
    audit = workbook_audit(path, primary)
    assert audit["formula_cells"] == audit["missing_formula_caches"] == 13
    assert audit["formula_error_caches"] == 0
    assert audit["main_csv_xlsx_differences"] == []
    assert audit["sheets"][0]["source_rows"] == 7
    assert all(m["sha256"] for m in audit["members"])


def test_native_schema_hash_and_complete_scope_are_not_silently_repaired(tmp_path):
    directory = fixture(tmp_path)
    with pytest.raises(ValueError, match="every admitted"):
        EmbrittlementCollection(directory, source_id="test", expected_sha256={MAIN_FILE:"wrong"})
    with pytest.raises(ValueError, match="SHA-256"):
        hashes = {n:file_sha256(directory/n) for n in (MAIN_FILE, COMPOSITION_FILE, MAP_FILE)}
        hashes[MAIN_FILE] = "wrong"
        with EmbrittlementCollection(directory, source_id="test", expected_sha256=hashes, require_complete=False):
            pass
    lines = list(csv.reader((directory/MAIN_FILE).open(encoding="utf-8", newline="")))
    lines[0][0] = "specimen_id"
    write_csv(directory/MAIN_FILE, lines[0], lines[1:])
    with pytest.raises(ValueError, match="header identity"):
        with opened(directory):
            pass


@pytest.mark.parametrize("issue", ["duplicate_record", "dangling_record", "dangling_composition"])
def test_original_join_keys_must_be_unique_and_present(tmp_path, issue):
    directory = fixture(tmp_path)
    name = MAIN_FILE if issue == "duplicate_record" else MAP_FILE
    lines = list(csv.reader((directory/name).open(encoding="utf-8", newline="")))
    if issue == "duplicate_record":
        lines.append(lines[1])
    else:
        lines[1][0 if issue == "dangling_record" else 1] = "absent-key"
    write_csv(directory/name, lines[0], lines[1:])
    with pytest.raises(ValueError):
        with opened(directory):
            pass


def test_file_row_budgets_source_mutation_and_context_are_explicit(tmp_path):
    directory = fixture(tmp_path)
    for kwargs in ({"maximum_file_bytes": 1}, {"maximum_rows": 2}):
        with pytest.raises(ValueError):
            with opened(directory, **kwargs):
                pass
    source = opened(directory)
    with pytest.raises(ValueError, match="inside"):
        next(source.iter_blocks("elongation"))
    with pytest.raises(ValueError, match="changed during"):
        with opened(directory):
            with (directory/MAIN_FILE).open("ab") as stream:
                stream.write(b"\n")
