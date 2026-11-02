"""Authored workbook fixtures; no external table is embedded in the test suite."""

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.hytunnel import AmbientColumnOverride, load_hytunnel_jet_workbook

openpyxl = pytest.importorskip("openpyxl")


def workbook(tmp_path, *, swapped=False, repeated=False, title="authored H2"):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = title
    offsets = (-200, -150, -100, -50, 0, 50, 100, 150, 200)

    def header(row, shift=0):
        for column, label in ((4, "Pu/mbar"), (5, "Tu / °C"), (6, "[g/s]"),
                              (7, "nach V [bar]"), (8, "Nozzle / mm")):
            sheet.cell(row, column, label)
        for xcol in (10, 22, 34):
            sheet.cell(row, xcol, "x/ mm")
            for index, offset in enumerate(offsets):
                sheet.cell(row-1, xcol+index+1, f"{index+1} (y / mm)")
                sheet.cell(row, xcol+index+1, offset+shift)

    for column, statistic in ((11, "average value"), (22, "maximum value"), (34, "minimum value")):
        sheet.cell(1, column, "H2-concentration / %")
        sheet.cell(2, column, statistic)
    header(4)

    def data(row, x):
        for column, value in ((4, 20. if swapped else 1000.), (5, 1000. if swapped else 20.),
                              (6, 1.), (7, 3.), (8, 4.)):
            sheet.cell(row, column, value)
        for xcol, value in ((10, 10.), (22, 12.), (34, 8.)):
            sheet.cell(row, xcol, x)
            for j in range(9):
                sheet.cell(row, xcol+j+1, value)
    data(5, 125.)
    data(6, 250.)
    if repeated:
        header(8, shift=-100)
        data(9, 375.)
    return book, sheet


def save_load(tmp_path, book, **options):
    path = tmp_path/"authored.xlsx"
    book.save(path)
    return load_hytunnel_jet_workbook(path, source_id="authored-source", **options)


def test_spatial_statistics_source_conditions_and_cell_provenance(tmp_path):
    book, _ = workbook(tmp_path, repeated=True)
    loaded = save_load(tmp_path, book)
    sheet = loaded.sheets[0]
    table = sheet.observations
    assert table.values.shape == (27, 13)
    assert table.column("x")[0][[0, 9, 18]] == pytest.approx([.125, .25, .375])
    assert table.column("y")[0][[0, 18]] == pytest.approx([-.2, -.3])
    assert table.column("ambient_pressure")[0][0] == 100_000.
    assert table.column("ambient_temperature")[0][0] == 293.15
    assert table.column("source_mass_flow")[0][0] == .001
    assert table.column("source_reported_pressure")[0][0] == 400_000.
    assert table.column("mean_h2_volume_fraction")[0][0] == .1
    assert sheet.mean_cells[0] == "K5" and sheet.mean_cells[18] == "K9"
    assert table.column("scan_row")[0][18] == 9.
    assert len(set(table.experiment_ids)) == 1 and not table.values.flags.writeable
    assert not sheet.issues and len(loaded.source_sha256) == 64


def test_label_conflict_is_masked_and_only_explicitly_overridden(tmp_path):
    book, _ = workbook(tmp_path, swapped=True)
    loaded = save_load(tmp_path, book)
    sheet = loaded.sheets[0]
    for name in ("ambient_pressure", "ambient_temperature", "source_reported_pressure"):
        assert not np.any(sheet.observations.column(name)[1])
    assert np.all(sheet.observations.column("mean_h2_volume_fraction")[1])
    assert sheet.observations.column("ambient_pressure")[0][0] == 2000.
    override = AmbientColumnOverride("E", "D", "authored test correction")
    corrected = save_load(tmp_path, book, ambient_overrides={sheet.sheet_name: override}).sheets[0]
    assert corrected.observations.column("ambient_pressure")[0][0] == 100_000.
    assert corrected.observations.column("ambient_temperature")[0][0] == 293.15
    assert corrected.observations.origins[5] == Origin.RECONSTRUCTED
    assert corrected.ambient_override is override
    with pytest.raises(ValueError):
        AmbientColumnOverride("E", "D", "")
    with pytest.raises(ValueError):
        save_load(tmp_path, book, ambient_overrides={"absent": override})


@pytest.mark.parametrize("fault", ["negative_minimum", "missing_mean", "order", "zero"])
def test_instrument_offsets_missingness_and_summary_order_are_distinct(tmp_path, fault):
    book, sheet = workbook(tmp_path)
    if fault == "negative_minimum":
        sheet["AI5"] = -.01
    elif fault == "missing_mean":
        sheet["K5"] = None
    elif fault == "order":
        sheet["K5"] = 15.
    else:
        sheet["K5"], sheet["W5"], sheet["AI5"] = 0., 0., 0.
    loaded = save_load(tmp_path, book).sheets[0]
    table = loaded.observations
    if fault == "negative_minimum":
        assert table.column("minimum_h2_volume_fraction")[0][0] == -.0001
        assert not table.column("minimum_h2_volume_fraction")[1][0]
        assert table.column("mean_h2_volume_fraction")[1][0]
    elif fault == "missing_mean":
        assert np.isnan(table.column("mean_h2_volume_fraction")[0][0])
        assert not table.column("mean_h2_volume_fraction")[1][0]
    elif fault == "order":
        assert not any(table.column(name)[1][0] for name in
                       ("mean_h2_volume_fraction", "minimum_h2_volume_fraction", "maximum_h2_volume_fraction"))
        assert any(issue.code == "inconsistent_statistic_order" for issue in loaded.issues)
    else:
        assert table.column("mean_h2_volume_fraction")[0][0] == 0.
        assert table.column("mean_h2_volume_fraction")[1][0]


def test_conflicting_tracer_identity_is_not_renamed_to_hydrogen(tmp_path):
    book, _ = workbook(tmp_path, title="authored He")
    sheet = save_load(tmp_path, book).sheets[0]
    assert not np.any(sheet.observations.column("mean_h2_volume_fraction")[1])
    assert sheet.observations.column("mean_h2_volume_fraction")[0][0] == .1
    assert any("gas_identity_conflict" in issue.code for issue in sheet.issues)


@pytest.mark.parametrize("fault", ["coordinate", "offset", "unit", "condition_header"])
def test_unsupported_layouts_do_not_silently_mix_measurements(tmp_path, fault):
    book, sheet = workbook(tmp_path)
    if fault == "coordinate":
        sheet["V5"] = 126.
    elif fault == "offset":
        sheet["W4"] = -150.
    elif fault == "unit":
        sheet["K1"] = "H2-concentration / ppm"
    else:
        sheet["H4"] = "Nozzle / inches"
    with pytest.raises(ValueError):
        save_load(tmp_path, book)
