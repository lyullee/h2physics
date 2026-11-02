from datetime import datetime, timedelta

import numpy as np
import pytest
from openpyxl import Workbook

from h2physics.core import Origin
from h2physics.data.excel import ExcelClock, load_excel_sheet
from h2physics.data.loaders import Column


def test_datetime_excel_clock_and_temperature_with_missing_formula_cache(tmp_path):
    start = datetime(2026, 1, 2, 3)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["recorded_at", "shell", "derived summary"])
    sheet.append([start, 20, 9000])
    sheet.append([start + timedelta(seconds=3), "=1+2", None])
    sheet.append([None, None, None])
    path = tmp_path / "authored.xlsx"
    workbook.save(path)
    loaded = load_excel_sheet(path, "Sheet", columns=(Column("shell", "wall", "temperature", "degC"),),
                               clock=ExcelClock("recorded_at", "datetime", datetime_origin=start),
                               clock_id="authored/local", origin=Origin.SYNTHETIC, source_id="test",
                               omit_missing_time=True)
    np.testing.assert_allclose(loaded.series.time_s, [0, 3])
    assert loaded.series.values[0, 0] == pytest.approx(293.15)
    assert not loaded.series.valid[1, 0]
    assert loaded.report.invalid_measurement_values == 1


def test_datetime_origin_must_be_explicit():
    with pytest.raises(ValueError, match="origin"):
        ExcelClock("date", "datetime")
