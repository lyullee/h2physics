"""Authored workbook edge cases, without redistributed experimental data."""

from datetime import datetime, timedelta

import pytest

from h2physics.core import Origin
from h2physics.data.hydride_tank import (
    FLOW_BASIS,
    HEADERS,
    hydride_summary_cells,
    iter_hydride_tank_blocks,
)
from h2physics.data.pressure_peaking import file_sha256
from h2physics.observations import Variable

openpyxl = pytest.importorskip("openpyxl")
START = datetime(2026, 1, 1)


def fixture(tmp_path):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Authored"
    sheet.append([*HEADERS, None, "authored derived total"])
    sheet.append([1, START, 0, 6, -2, 20, 21, 22, 23, 24, 0, 0, None, "=L3"])
    sheet.append([2, START + timedelta(seconds=2), "=(B3-B2)*86400", -3, 3,
                  -274, None, 22, "bad", 24, "=D3/60", "=L2+K3"])
    sheet.append([3, None, 4, None, "unknown", 20, 21, 22, 23, 24])
    sheet.append([4, START + timedelta(seconds=1), 1, 0, 0, 20, 21, 22, 23, 24])
    path = tmp_path / "authored.xlsx"
    workbook.save(path)
    return path


def load(path, **kwargs):
    return iter_hydride_tank_blocks(path, "Authored", source_id="authored", experiment_id="run",
        clock_id="local", datetime_origin=START, **kwargs)


def test_basis_and_source_rows_survive_missing_and_reversed_clocks(tmp_path):
    path = fixture(tmp_path)
    blocks = list(load(path, block_rows=2, expected_sha256=file_sha256(path)))
    assert [b.source_rows for b in blocks] == [(2, 3), (4, 5)]
    first = blocks[0].observations
    assert first.column("mfc_reference_volume_flow")[0] == pytest.approx([1e-4, -5e-5])
    assert first.column("instrument_pressure")[0] == pytest.approx([-2, 3])
    assert first.column("shell_1")[0] == pytest.approx([293.15, -.85])
    assert first.column("shell_1")[1].tolist() == [True, False]
    assert not first.column("shell_2")[1][1]
    assert not first.column("exported_elapsed")[1][1]  # Formula has no cached value.
    assert not blocks[1].observations.column("datetime_elapsed")[1][0]
    assert blocks[1].observations.column("datetime_elapsed")[0][1] == 1
    assert blocks[1].raw_cells[0][1] is None
    assert first.origins[3] == Origin.MEASURED
    assert first.origins[-1] == Origin.RECONSTRUCTED
    assert first.variables[3].basis_id == FLOW_BASIS
    digest = file_sha256(path)
    assert first.row_ids == tuple(f"authored|{digest}|run|Authored|row-{row}" for row in (2, 3))
    assert not first.values.flags.writeable
    with pytest.raises(ValueError, match="quantity"):
        first.column("mfc_reference_volume_flow", expected=Variable("flow", "mass_flow", "kg/s"))


def test_summary_formulas_are_retained_and_never_executed(tmp_path):
    summary = hydride_summary_cells(fixture(tmp_path), "Authored")
    assert len(summary) == 1
    assert summary[0].coordinate == "N2" and summary[0].formula == "=L3"
    assert summary[0].cached_value is None


def test_distinct_workbooks_keep_common_experiment_group_and_distinct_rows(tmp_path):
    path = fixture(tmp_path)
    original = next(load(path)).observations
    workbook = openpyxl.load_workbook(path)
    workbook.active["E2"] = 4
    other = tmp_path / "other.xlsx"
    workbook.save(other)
    changed = next(load(other)).observations
    assert original.experiment_ids == changed.experiment_ids
    assert not set(original.row_ids) & set(changed.row_ids)
    assert dict(original.context)["file_sha256"] != dict(changed.context)["file_sha256"]


@pytest.mark.parametrize("kwargs", [{"block_rows": True}, {"block_rows": 0},
    {"maximum_bytes": 1}, {"expected_sha256": "0" * 64}])
def test_invalid_budgets_and_hashes_fail(tmp_path, kwargs):
    with pytest.raises(ValueError):
        list(load(fixture(tmp_path), **kwargs))


def test_changed_schema_rejected(tmp_path):
    path = fixture(tmp_path)
    workbook = openpyxl.load_workbook(path)
    workbook.active["D1"] = "renamed"
    workbook.save(path)
    with pytest.raises(ValueError, match="schema"):
        list(load(path))


def test_mutation_during_iteration_is_detected(tmp_path):
    path = fixture(tmp_path)
    iterator = load(path, block_rows=2)
    next(iterator)
    with path.open("ab") as stream:
        stream.write(b"changed")
    next(iterator)
    with pytest.raises(ValueError, match="changed"):
        next(iterator)
