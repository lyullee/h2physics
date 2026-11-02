"""Authored recorder fixtures; no external observations are redistributed."""

import numpy as np
import pytest
from scipy.io import savemat

from h2physics.core import Origin
from h2physics.data.pressure_peaking import (
    CONCENTRATION_HEADERS,
    GEN_DIMENSIONS,
    GEN_LABELS,
    METER_BASIS,
    P1_BASIS,
    SIGMA_DIMENSIONS,
    SIGMA_LABELS,
    file_sha256,
    load_pressure_concentration,
    load_pressure_mat,
)

openpyxl = pytest.importorskip("openpyxl")


def mat_file(tmp_path, **changes):
    payload = {"SIGMA": np.array([[.1, -2., -1.], [.2, 0., 3.], [.3, 4., np.nan]]),
        "GEN3i": np.array([[0., -.002], [.04, .005], [.08, np.nan], [.12, .1]]),
        "SIGMAdimensions": np.array([SIGMA_DIMENSIONS], dtype=object),
        "SIGMAunits": np.array([SIGMA_LABELS], dtype=object),
        "GENdimensions": np.array([GEN_DIMENSIONS], dtype=object),
        "GENunits": np.array([GEN_LABELS], dtype=object)}
    payload.update(changes)
    path = tmp_path / "authored.mat"
    savemat(path, payload, do_compression=True)
    return path


def load_mat(path, **kwargs):
    return load_pressure_mat(path, source_id="authored/mat", experiment_id="authored-case", **kwargs)


def workbook_file(tmp_path, *, headers=CONCENTRATION_HEADERS, rows=None, device="authored-device"):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Authored"
    sheet.append(["Device ID", "Factory Device ID", "Firmware", "Measurement mode"] + [None] * 13)
    sheet.append([device, "authored-device", "authored-firmware", "H2"] + [None] * 13)
    sheet.append(headers)
    if rows is None:
        rows = [[4, "12:01:00.25", -2., 20., 20., 25., 50., 1.5, 1., 20., 2., 700., 1., 3., 4., 99., 7],
                [4, "12:01:00.55", None, 20., -274., 25., 101., 1.5, 1., 20., 2., 700., 1., 3., 4., 99., 0],
                [5, "12:01:01.00", 4., 20., 20., 25., 50., 1.5, 1., 20., 2., 700., 1., 3., 4., 99., 0]]
    for row in rows:
        sheet.append(row)
    path = tmp_path / "authored.xlsx"
    workbook.save(path)
    return path


def load_workbook(path, **kwargs):
    return load_pressure_concentration(path, source_id="authored/xlsx", experiment_id="authored-case", **kwargs)


def test_actual_units_and_metadata_are_distinct_from_misnamed_mat_variables(tmp_path):
    path = mat_file(tmp_path)
    run = load_mat(path, expected_sha256=file_sha256(path))
    assert run.sigma.dimension_labels == SIGMA_DIMENSIONS
    assert run.sigma.channel_labels == SIGMA_LABELS
    assert run.gen3i.dimension_labels == GEN_DIMENSIONS
    assert run.gen3i.channel_labels == GEN_LABELS and len(GEN_LABELS) == 35
    sigma = list(run.sigma.iter_blocks(block_rows=2))
    series = sigma[0].series
    assert series.values[:, 0] == pytest.approx([-.002, 0.])
    assert series.values[:, 1] == pytest.approx([-100_000., 300_000.])
    assert np.all(series.valid)  # Signed instrument output is not clipped/declared release flow.
    assert series.basis_ids[1] == METER_BASIS
    assert not sigma[1].series.valid[0, 1] and np.isnan(sigma[1].series.values[0, 1])
    assert sigma[0].observations.row_ids == ("authored/mat|SIGMA|row-1", "authored/mat|SIGMA|row-2")
    assert sigma[1].observations.row_ids == ("authored/mat|SIGMA|row-3",)
    assert sigma[1].observations.origins == (Origin.MEASURED,) * 3
    assert not run.sigma.raw.flags.writeable
    assert not series.values.flags.writeable and not sigma[0].source_rows.flags.writeable
    p1 = next(run.gen3i.iter_blocks()).series
    assert p1.values[[0, 1, 3], 0] == pytest.approx([-2., 5., 100.])
    assert p1.basis_ids == (P1_BASIS,)
    assert p1.clock_id != series.clock_id
    assert any(issue.code.startswith("guide_overpressure_column_3") for issue in run.issues)
    with pytest.raises(ValueError, match="quantity"):
        p1.channel_values(p1.channels[0], quantity="pressure")
    with pytest.raises(ValueError, match="basis"):
        p1.channel_values(p1.channels[0], quantity="reported_pressure")


def test_closed_windows_and_original_rows_survive_block_selection(tmp_path):
    run = load_mat(mat_file(tmp_path))
    blocks = list(run.gen3i.iter_blocks(first_row=2, last_row=4, time_window_s=(.04, .08), block_rows=1))
    assert [b.source_rows.tolist() for b in blocks] == [[2], [3]]
    assert [b.series.time_s[0] for b in blocks] == [.04, .08]
    assert not list(run.gen3i.iter_blocks(time_window_s=(3., 4.)))
    for options in ({"block_rows": 0}, {"first_row": True}, {"last_row": 6},
                    {"time_window_s": (.2, .1)}, {"time_window_s": (0., np.nan)}):
        with pytest.raises(ValueError):
            list(run.gen3i.iter_blocks(**options))


@pytest.mark.parametrize("fault", ["time", "shape", "labels", "extra"])
def test_mat_schema_clock_and_semantic_faults_fail_before_use(tmp_path, fault):
    changes = {"time": {"SIGMA": np.array([[.1, 1., 2.], [.1, 1., 2.]])},
        "shape": {"GEN3i": np.ones((4, 3))},
        "labels": {"GENdimensions": np.array([["s", "bar", "V", ""]], dtype=object)},
        "extra": {"unsupported": np.ones((1, 1))}}[fault]
    with pytest.raises(ValueError):
        load_mat(mat_file(tmp_path, **changes))


def test_source_hash_and_memory_budgets_are_gates(tmp_path):
    path = mat_file(tmp_path)
    for options in ({"expected_sha256": "0" * 64}, {"maximum_bytes": 1}, {"maximum_array_bytes": 8}):
        with pytest.raises(ValueError):
            load_mat(path, **options)
    with pytest.raises(ValueError, match="identities"):
        load_pressure_mat(path, source_id="", experiment_id="case")


def test_workbook_streams_all_channels_and_retains_negative_missing_and_alarm_rows(tmp_path):
    path = workbook_file(tmp_path, device="different-configured-device")
    source = load_workbook(path, expected_sha256=file_sha256(path))
    assert source.headers == CONCENTRATION_HEADERS
    assert source.metadata_values[0] == "different-configured-device"
    assert any(i.code == "device_factory_identity_mismatch" for i in source.issues)
    blocks = list(source.iter_blocks(block_rows=2))
    table = blocks[0].observations
    assert table.values.shape == (2, 17)
    assert table.row_ids[0] == "authored/xlsx|Authored|row-4"
    assert blocks[1].observations.row_ids == ("authored/xlsx|Authored|row-6",)
    assert table.column("iteration")[0].tolist() == [4., 4.]
    values, valid = table.column("reported_h2_concentration")
    assert values[0] == -.02 and not np.any(valid) and np.isnan(values[1])
    assert table.column("pt100_temperature")[0] == pytest.approx([293.15, -.85])
    assert table.column("pt100_temperature")[1].tolist() == [True, False]
    assert table.column("relative_humidity")[1].tolist() == [True, False]
    assert table.column("ah_reported_pressure")[0][0] == 1500.
    assert table.column("utp")[0][0] == .02 and table.column("ih")[0][0] == .002
    assert table.column("uh")[0][0] == pytest.approx(.7)
    assert table.column("ph")[0][0] == .001
    assert table.column("alarm")[0].tolist() == [7., 0.]
    assert blocks[0].raw_clock_strings == ("12:01:00.25", "12:01:00.55")
    series = blocks[0].as_time_series()
    assert series.time_s == pytest.approx([43260.25, 43260.55])
    assert series.channels[0] == "iteration"
    assert all(origin == Origin.MEASURED for origin in table.origins)
    selected = list(source.iter_blocks(first_row=5, last_row=5))
    assert selected[0].observations.row_ids == ("authored/xlsx|Authored|row-5",)


@pytest.mark.parametrize("clock", ["malformed", "24:00:00.00", "12:01:00.25", "00:00:00.01"])
def test_invalid_duplicate_or_midnight_clocks_stay_in_table_and_do_not_auto_unwrap(tmp_path, clock):
    row = [1, "23:59:59.99", 1., 20., 20., 25., 50., 1., 1., 20., 2., 700., 1., 3., 4., 99., 0]
    row[1] = "12:01:00.25" if clock == "12:01:00.25" else row[1]
    following = list(row)
    following[1] = clock
    source = load_workbook(workbook_file(tmp_path, rows=[row, following]))
    blocks = list(source.iter_blocks(block_rows=1))  # Boundary fault must survive streaming.
    assert len(blocks) == 2 and blocks[1].raw_clock_strings == (clock,)
    with pytest.raises(ValueError, match="clock"):
        blocks[1].as_time_series()
    assert blocks[1].issues


def test_workbook_unit_header_changes_and_hash_changes_are_not_guessed(tmp_path):
    headers = list(CONCENTRATION_HEADERS)
    headers[2] = "Output (ppm)"
    with pytest.raises(ValueError, match="headers"):
        load_workbook(workbook_file(tmp_path, headers=headers))
    path = workbook_file(tmp_path)
    source = load_workbook(path)
    workbook = openpyxl.load_workbook(path)
    workbook.active["C4"] = 30.
    workbook.save(path)
    with pytest.raises(ValueError, match="changed"):
        list(source.iter_blocks())


def test_supported_temperature_glyph_variant_retains_literal_headers(tmp_path):
    headers = tuple(h.replace("°C", "ｰC") for h in CONCENTRATION_HEADERS)
    source = load_workbook(workbook_file(tmp_path, headers=headers))
    assert source.headers == headers
    assert next(source.iter_blocks()).observations.column("pt100_temperature")[0][0] == 293.15
