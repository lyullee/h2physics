import io

import numpy as np
import pytest
from openpyxl import Workbook

from h2physics.data.preslhy import load_discha_workbook


def workbook_bytes(*, wrong_unit=False):
    workbook = Workbook()
    workbook.remove(workbook.active)
    definitions = [
        ("run-Press", ["diameter", "pressure recorder", "PVes", "PNoz"],
         [None, None, "bar", "bar"], [1., None, None, None, None, 10.], [8., 7.]),
        ("run-cH2-Amb", [None, "ambient recorder", "PVessel", "PNozzle", "F", "Tamb", "RHamb"],
         [None, None, "bar", "bar", "N", "Grad C", "Rel. Feuchte"], [], [8., 7., 2., 20., 50.]),
        ("other-time-Temp", [None, "temperature recorder", "T1", "T2", "T3", "T4", "TNz"],
         [None, None, *(('degC' if wrong_unit else 'Kelvin',)*5)], [], [300., 302., 304., 280., 290.]),
        ("run-Weight", [None, "weight recorder", "Weight"], [None, None, "kg"], [], [100.]),
    ]
    for title, header, units, meta, data in definitions:
        sheet = workbook.create_sheet(title)
        sheet.append(header)
        sheet.append(meta)
        sheet.append([])
        sheet.append(units)
        sheet.append([])
        sheet.append(["Time [s]", "recorder clock"])
        sheet.append([0., 12., *data])
        sheet.append([1., 13., *data])
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_discha_profile_uses_declared_units_and_separate_recorders():
    result = load_discha_workbook(workbook_bytes(), source_id="authored-case", clock_id="shared",
                                  pressure_basis="gauge", reference_pressure_pa=1e5,
                                  relative_humidity_unit="%",
                                  include_fast_pressure=True)
    assert result.nominal_nozzle_diameter_m == .001
    assert result.initial_pressure_pa == 1.1e6
    np.testing.assert_allclose(result.ambient.series.values[:, 0], 9e5)
    np.testing.assert_allclose(result.ambient.series.values[:, 3], 293.15)
    np.testing.assert_allclose(result.ambient.series.values[:, 4], .5)
    np.testing.assert_allclose(result.temperatures.series.values[:, 0], 300.)
    np.testing.assert_allclose(result.weight.series.values[:, -1], [12., 13.])
    assert result.fast_pressure.series.clock_id == result.temperatures.series.clock_id == "shared"
    assert len(result.workbook_sha256) == 64


def test_discha_rejects_undeclared_reference_and_changed_units():
    with pytest.raises(ValueError, match="explicit reference"):
        load_discha_workbook(workbook_bytes(), source_id="a", clock_id="c",
                            pressure_basis="gauge", reference_pressure_pa=None)
    with pytest.raises(ValueError, match="header/unit"):
        load_discha_workbook(workbook_bytes(wrong_unit=True), source_id="a", clock_id="c",
                            pressure_basis="absolute", reference_pressure_pa=None)
