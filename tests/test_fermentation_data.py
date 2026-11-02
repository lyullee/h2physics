"""Authored miniature reactor records; no external observations are redistributed."""

from dataclasses import replace
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.fermentation import (
    HEADERS,
    LITRE_PER_DAY_TO_M3_PER_S,
    FermentationWorkbook,
    component_production_check,
)
from h2physics.data.pressure_peaking import file_sha256
from h2physics.observations import Variable, split_experiments

openpyxl = pytest.importorskip("openpyxl")


def fixture(tmp_path, *, formula=False, wrong_header=False):
    path = tmp_path / "authored.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(HEADERS)
    for number, reactor, day in ((1, 1, 2), (3, 1, 2), (4, 1, 4), (5, 2, 2), (6, 2, 3)):
        sheet.append((number, reactor, day, 33., 6., 2., 12., 50., 20., 30., 3.6, 2., .08,
            2.4, .04, 1.2, "1.25", "--", "0.0", None, "--", "0.5", None, "1.5"))
    sheet["K4"] = 40.  # Deliberate source algebra inconsistency is retained.
    if formula:
        sheet["K2"] = "=G2*J2/100"
        sheet["Q2"] = "=1+2"
    if wrong_header:
        sheet["M1"] = "HPR (1/d)"
    workbook.save(path)
    return path


def opened(path, **kwargs):
    return FermentationWorkbook(path, source_id="authored-study-source", study_id="one-study",
                                expected_sha256=file_sha256(path), **kwargs)


def test_units_gas_liquid_and_reported_productivity_remain_distinct(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks())
        table = block.observations
        assert table.column("duration_s")[0][0] == 2 * 86400
        assert table.column("temperature")[0][0] == 306.15
        assert table.column("HRT_s")[0][0] == 2 * 86400
        assert table.column("BP")[0][0] == 12 * LITRE_PER_DAY_TO_M3_PER_S
        assert table.column("H2")[0][0] == .3
        assert table.column("HY")[0][0] == 2.
        assert table.column("COD_in")[0][0] == 1.25
        assert table.column("OLR_COD")[0][0] == pytest.approx(1.2 / 86400)
        assert table.variables[12].unit == "source L/(L/d)"
        assert "unresolved" in table.variables[11].basis_id
        assert table.variables[16].unit == "kg_COD/m3"
        assert table.variables[6].unit == "m3_reported/s"
        with pytest.raises(ValueError, match="basis differs"):
            table.column("BP", expected=Variable("gas", "mass_flow", "kg/s"))
        with pytest.raises(ValueError, match="basis differs"):
            table.column("H2", expected=Variable("H2", "mole_fraction", "1"))
        with pytest.raises(ValueError, match="basis differs"):
            table.column("COD_in", expected=Variable("substrate", "mass_concentration", "kg/m3", "glucose"))


def test_numeric_strings_missing_placeholders_and_zero_are_preserved(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks())
        table = block.observations
        assert block.raw_cells[0][16:20] == ("1.25", "--", "0.0", None)
        assert not table.column("COD_out")[1][0]
        assert block.invalid_reasons[0][17] == "source_missing_placeholder"
        assert block.invalid_reasons[0][19] == "source_blank"
        assert table.column("Hac")[1][0]
        assert table.column("Hac")[0][0] == 0.


def test_reactor_clocks_remain_separate_without_replication_claim(tmp_path):
    with opened(fixture(tmp_path)) as source:
        blocks = list(source.iter_blocks(block_rows=2))
        assert [b.reactor_id for b in blocks] == ["R-1", "R-1", "R-2"]
        assert blocks[0].observations.variables[2].basis_id != blocks[-1].observations.variables[2].basis_id
        assert {e for block in blocks for e in block.observations.experiment_ids} == {"one-study"}
        assert sum(len(b.issues) for b in blocks) == 1
        assert blocks[0].issues[0].source_row == 3
        assert blocks[0].observations.column("duration_s")[1][1]
        with pytest.raises(ValueError, match="TimeSeries"):
            blocks[-1].as_time_series()
        with pytest.raises(ValueError):
            split_experiments(blocks[0].observations, {"R-1"})


def test_derived_targets_and_source_algebra_are_not_independent_measurements(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks())
        table = block.observations
        assert table.origins[10:15] == (Origin.RECONSTRUCTED,) * 5
        assert table.origins[5] == table.origins[15] == Origin.UNRESOLVED
        check = component_production_check(block)
        assert check.row_ids == table.row_ids
        assert check.experiment_ids == table.experiment_ids
        assert set(check.origins) == {Origin.RECONSTRUCTED}
        assert abs(check.column("HP_residual")[0][0]) < 1e-20
        assert check.column("HP_residual")[0][2] == pytest.approx((40 - 3.6) * LITRE_PER_DAY_TO_M3_PER_S)
        assert table.column("HP")[0][2] == 40 * LITRE_PER_DAY_TO_M3_PER_S
        assert np.max(np.abs(check.column("listed_gas_fraction_closure")[0])) < 1e-15


def test_formula_and_missing_caches_are_not_executed(tmp_path):
    with opened(fixture(tmp_path, formula=True)) as source:
        block = next(source.iter_blocks())
        assert block.formula_cells == (("K2", "=G2*J2/100"), ("Q2", "=1+2"))
        assert np.isnan(block.observations.column("HP")[0][0])
        assert not block.observations.column("HP")[1][0]
        assert block.invalid_reasons[0][10] == "source_formula_cache_missing"
        assert block.invalid_reasons[0][16] == "source_formula_cache_missing"


def test_stored_formula_cache_preserves_value_without_independent_measurement_claim(tmp_path):
    path = fixture(tmp_path, formula=True)
    output = BytesIO()
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with ZipFile(path) as source, ZipFile(output, "w", ZIP_DEFLATED) as destination:
        for member in source.infolist():
            payload = source.read(member.filename)
            if member.filename == "xl/worksheets/sheet1.xml":
                xml = ET.fromstring(payload)
                for cell in xml.iter(ns + "c"):
                    if cell.attrib.get("r") in ("K2", "Q2"):
                        cell.find(ns + "v").text = "3.6" if cell.attrib["r"] == "K2" else "3"
                payload = ET.tostring(xml, encoding="utf-8")
            destination.writestr(member.filename, payload)
    path.write_bytes(output.getvalue())
    with opened(path) as source:
        block = next(source.iter_blocks())
        assert block.observations.column("HP")[1][0]
        assert block.observations.column("HP")[0][0] == 3.6 * LITRE_PER_DAY_TO_M3_PER_S
        assert block.raw_cells[0][16] == 3.
        assert not block.observations.column("COD_in")[1][0]
        assert block.invalid_reasons[0][16] == "source_formula_cache_not_independent_measurement"


def test_invalid_domains_and_unrecognized_numeric_strings_are_masked_without_repair(tmp_path):
    path = fixture(tmp_path)
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["Data"]
    sheet["D2"], sheet["F2"], sheet["J2"], sheet["Q2"] = -300, 0, 120, "1,234"
    workbook.save(path)
    with opened(path) as source:
        block = next(source.iter_blocks())
        assert block.observations.values[0, 3] == pytest.approx(-26.85)
        assert block.observations.values[0, 9] == 1.2
        assert not np.any(block.observations.valid[0, (3, 5, 9, 16)])
        check = component_production_check(block)
        assert not check.column("H2_from_BP_fraction")[1][0]
        assert block.raw_cells[0][16] == "1,234"


def test_streaming_windows_and_row_identity_are_stable(tmp_path):
    with opened(fixture(tmp_path)) as source:
        full = list(source.iter_blocks())
        small = list(source.iter_blocks(block_rows=1))
        np.testing.assert_equal(np.concatenate([b.observations.values for b in full]),
                                np.concatenate([b.observations.values for b in small]))
        window = list(source.iter_blocks(first_row=3, last_row=5))
        assert tuple(row for b in window for row in b.source_rows) == (3, 4, 5)
        ids = tuple(row for b in full for row in b.observations.row_ids)
        assert tuple(row for b in window for row in b.observations.row_ids) == ids[1:4]
        assert source.sha256 in ids[0]
        assert [b.raw_cells[0][0] for b in small] == [1, 3, 4, 5, 6]


def test_declared_blank_row_is_not_forward_filled_or_dropped(tmp_path):
    path = fixture(tmp_path)
    workbook = openpyxl.load_workbook(path)
    workbook["Data"]["A7"].number_format = "0"
    workbook.save(path)
    with opened(path) as source:
        blocks = list(source.iter_blocks())
        assert blocks[-1].source_rows == (7,)
        assert blocks[-1].reactor_id == "R-unresolved"
        assert not np.any(blocks[-1].observations.valid)


def test_formula_operator_requires_declared_variable_contract(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks())
        table = block.observations
        variables = list(table.variables)
        variables[6] = Variable("BP", "volume_flow", "m3/s", "liquid feed")
        changed = replace(table, variables=tuple(variables))
        with pytest.raises(ValueError, match="contracts"):
            component_production_check(replace(block, observations=changed))


@pytest.mark.parametrize("kwargs", ({"block_rows": 0}, {"block_rows": True},
    {"block_rows": 1001}, {"first_row": 1}, {"last_row": 100}, {"first_row": 4, "last_row": 3}))
def test_invalid_block_and_source_row_windows(tmp_path, kwargs):
    with opened(fixture(tmp_path)) as source, pytest.raises(ValueError):
        list(source.iter_blocks(**kwargs))


def test_profile_header_hash_budgets_and_end_stability(tmp_path, monkeypatch):
    path = fixture(tmp_path, wrong_header=True)
    with pytest.raises(ValueError, match="headers"):
        with opened(path):
            pass
    path = fixture(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        with FermentationWorkbook(path, source_id="x", study_id="x", expected_sha256="0" * 64):
            pass
    with pytest.raises(ValueError, match="budget"):
        with opened(path, maximum_expanded_bytes=10):
            pass
    with pytest.raises(ValueError, match="changed"):
        with opened(path):
            monkeypatch.setattr("h2physics.data.fermentation.file_sha256", lambda _: "0" * 64)
