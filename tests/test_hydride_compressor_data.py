"""Original miniature exports exercise identities, clocks and unresolved source fields."""

import hashlib
import re
from datetime import datetime, time
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.hydride_compressor import (
    LABVIEW_ALIASES,
    LABVIEW_UNITS,
    ArchiveLimits,
    HydrideCompressorArchive,
    HydrideCompressorWorkbook,
)

openpyxl = pytest.importorskip("openpyxl")


def workbook_bytes(experiment=1, *, formula=False, missing_unit=False):
    """Small authored values; source format headings identify the reviewed schema."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for raw in (True, False):
        sheet = workbook.create_sheet(f"Cycle {'Definition' if raw else 'Data'} Exp.{experiment}")
        group, alias = (44, 46) if raw else (10, 11)
        labels = list(LABVIEW_ALIASES)
        units = list(LABVIEW_UNITS)
        special = experiment in (6, 7)
        if special:
            labels[12:] = (["Time", "Flow-3", None if experiment == 6 else "MFC-3"] if raw
                else [None, "Flow-3", "MFC-3" if experiment == 6 else None])
            units[9:] = [None, "ln/min", "ln/min" if experiment == 6 else None]
        sheet.cell(group, 1, "Labview")
        for column, value in enumerate(("hh:mm:ss", "s", *units), 2):
            if value is not None:
                sheet.cell(group, column, value)
        for column, value in enumerate(labels, 1):
            if value is not None:
                sheet.cell(alias, column, value)
                if raw:
                    sheet.cell(alias - 1, column, f"hardware-{column}")
        if missing_unit and not raw:
            sheet.cell(group, 4).value = "psi"
        starts = [(17, "Graphtec Pt100 Probes", 12 if raw else 10),
                  (33 if raw else 29, "Picolog Thermometer", 12)]
        if raw and experiment == 2:
            starts.append((48, "Picolog Thermometer", 12))
        for column, name, count in starts:
            sheet.cell(group, column, name)
            sheet.cell(group, column + 1, "°C")
            sheet.cell(alias, column, "Date & Time")
            for i in range(count):
                label = f"T-{2 if i < 6 else 1}_{i % 6 + 1}" if name.startswith("Picolog") else f"Pt-{i + 1}"
                sheet.cell(alias, column + i + 1, label)
                if raw:
                    sheet.cell(alias - 1, column + i + 1, f"CH{i + 1}")
        for index in range(3):
            row = alias + index + 1
            values = [20250203, time(10, 0, index), index, -.2, -.3, -60., 20., 6., 30., 2., 3., 4., -30., 12., 0.]
            if special:
                values[12:] = [f"10:00:0{index}" if raw else None, "1,234", 0.]
            for column, value in enumerate(values, 1):
                if value is not None:
                    sheet.cell(row, column, value)
            for column, _, count in starts:
                stamp = datetime(2025, 2, 3, 10, 0, 2 if index < 2 else 4)
                if column == 48:
                    stamp = datetime(2025, 2, 2, 9, 0, index)
                if index != 2:
                    sheet.cell(row, column, stamp)
                for i in range(count):
                    sheet.cell(row, column + i + 1, 10 + i)
            if index == 2:
                sheet.cell(row, 7, -300)
        if raw and formula:
            sheet.cell(alias + 1, 4, "=1+2")
        # Preserve an all-empty source grid row represented only by formatting.
        sheet.cell(alias + 4, 1).number_format = "0"
    derived = workbook.create_sheet("H2 Mass Balance Exp.fixture")
    derived["A1"], derived["A2"], derived["B1"] = 6, "=A1/2", "not a measurement"
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def snapshot(payload, experiment=1, *, archive_sha="a" * 64, member="source/Dataset/Experiment 1.xlsx"):
    return HydrideCompressorWorkbook(payload, experiment=experiment, archive_sha256=archive_sha,
        member_name=member, member_sha256=hashlib.sha256(payload).hexdigest())


def blocks(workbook, sheet=None, **kwargs):
    return list(workbook.iter_blocks(sheet or workbook.raw_sheet,
                                    datetime_origin=datetime(2025, 2, 3), **kwargs))


def test_units_masks_and_argon_context():
    with snapshot(workbook_bytes()) as workbook:
        lab, graph, pico = blocks(workbook)[0]
        table = lab.observations
        assert table.column("P-4")[0][0] == -20000
        assert table.column("P-4")[1][0]
        assert table.column("MF-1")[0][0] == pytest.approx(-.001)
        assert table.column("MFC-1")[0][0] == pytest.approx(-.0005)
        assert table.variables[-3].quantity == "reference_volume_flow"
        assert table.variables[-3].unit == "m3_ref/s"
        assert "unresolved" in table.variables[2].basis_id
        assert table.column("T_HTF-1")[0][0] == 293.15
        assert not table.column("T_HTF-1")[1][2]
        assert np.all(~table.valid[-1])
        assert "argon" in dict(table.context)["gas_context"]
        assert pico.observations.values[0, 1] == 283.15
        assert not pico.observations.valid[0, 1]
        assert "defective" in pico.invalid_reasons[0][1]
        assert graph.observations.valid[0, 1]
        assert table.origins[0] == Origin.RECONSTRUCTED
        assert table.origins[1] == Origin.MEASURED


def test_independent_clocks_and_duplicate_stamps_are_retained():
    with snapshot(workbook_bytes()) as workbook:
        lab, graph, pico = blocks(workbook)[0]
        assert lab.observations.values[0, 0] == 36000
        assert graph.observations.values[0, 0] == 36002
        assert graph.observations.values[1, 0] == 36002
        assert not graph.observations.valid[2, 0]
        assert len({b.observations.variables[0].basis_id for b in (lab, graph, pico)}) == 3
        assert graph.raw_cells[0][0] == datetime(2025, 2, 3, 10, 0, 2)


def test_selected_data_share_experiment_but_not_row_identity():
    with snapshot(workbook_bytes()) as workbook:
        raw = blocks(workbook)[0][0].observations
        selected = blocks(workbook, workbook.selected_sheets[0])[0][0].observations
        assert raw.experiment_ids == selected.experiment_ids
        assert set(raw.row_ids).isdisjoint(selected.row_ids)
        assert set(selected.origins) == {Origin.RECONSTRUCTED}


def test_row_identity_includes_archive_member_hash_and_path():
    payload = workbook_bytes()
    with snapshot(payload) as first, snapshot(payload, archive_sha="b" * 64) as other_archive:
        assert blocks(first)[0][0].observations.row_ids != blocks(other_archive)[0][0].observations.row_ids
    with snapshot(payload, member="other/Dataset/Experiment 1.xlsx") as other_member:
        assert "other/Dataset" in blocks(other_member)[0][0].observations.row_ids[0]
    changed = payload + b"trailing authored bytes"
    with snapshot(changed) as other_bytes:
        assert hashlib.sha256(changed).hexdigest() in blocks(other_bytes)[0][0].observations.row_ids[0]


def test_blocks_and_windows_preserve_source_rows_and_values():
    with snapshot(workbook_bytes()) as workbook:
        whole = blocks(workbook)[0]
        streamed = blocks(workbook, block_rows=2)
        for logger in range(3):
            np.testing.assert_equal(whole[logger].observations.values,
                np.concatenate([part[logger].observations.values for part in streamed]))
            assert whole[logger].source_rows == tuple(r for part in streamed for r in part[logger].source_rows)
        window = blocks(workbook, start_row=48, stop_row=49)[0][0]
        assert window.source_rows == (48, 49)
        np.testing.assert_equal(window.observations.values, whole[0].observations.values[1:3])


def test_formula_caches_are_never_executed_and_are_not_measurements():
    with snapshot(workbook_bytes(formula=True)) as workbook:
        block = blocks(workbook)[0][0]
        assert np.isnan(block.observations.column("P-4")[0][0])
        assert not block.observations.column("P-4")[1][0]
        assert block.formula_cells[0].coordinate == "D47"
        assert block.formula_cells[0].value == "1+2"
        audit = {s.sheet: s for s in workbook.audit()}
        assert audit[workbook.raw_sheet].formula_cells == 1
        assert audit[workbook.raw_sheet].missing_formula_caches == 1
        assert audit["H2 Mass Balance Exp.fixture"].numeric_cells == 1
        assert audit["H2 Mass Balance Exp.fixture"].formula_cells == 1


def test_numeric_formula_cache_retained_but_masked_as_raw_measurement():
    original = workbook_bytes(formula=True)
    stream = BytesIO()
    replacements = 0
    with ZipFile(BytesIO(original)) as source, ZipFile(stream, "w", ZIP_DEFLATED) as destination:
        for member in source.infolist():
            payload = source.read(member.filename)
            payload, count = re.subn(rb"<f>1\+2</f><v\s*(?:/>|></v>)",
                                     b"<f>1+2</f><v>3</v>", payload)
            replacements += count
            destination.writestr(member.filename, payload)
    assert replacements == 1
    with snapshot(stream.getvalue()) as workbook:
        block = blocks(workbook)[0][0]
        assert block.observations.column("P-4")[0][0] == 300000
        assert not block.observations.column("P-4")[1][0]
        assert block.raw_cells[0][3] == 3


def test_separate_calibration_export_keeps_its_calendar():
    with snapshot(workbook_bytes(2), 2) as workbook:
        result = blocks(workbook)[0]
        assert len(result) == 4
        assert result[3].schema.identity.endswith("@AV")
        assert result[3].observations.values[0, 0] == -54000
        assert "calibration" in result[3].schema.role
        assert "without hydrogen" in workbook.gas_context


@pytest.mark.parametrize("experiment", (6, 7))
def test_loading_station_clock_and_decimal_strings_remain_unresolved(experiment):
    with snapshot(workbook_bytes(experiment), experiment) as workbook:
        result = blocks(workbook)[0]
        station = next(b for b in result if b.schema.identity.startswith("Loading"))
        assert station.schema.clock_kind == "source-time-of-day"
        assert station.observations.values[0, 0] == 36000
        assert station.raw_cells[0][1] == "1,234"
        assert not station.observations.valid[0, 1]
        selected = blocks(workbook, workbook.selected_sheets[0])[0]
        selected_station = next(b for b in selected if b.schema.identity.startswith("Loading"))
        assert not selected_station.observations.valid[0, 0]


def test_unknown_units_and_derived_sheet_rejected():
    with snapshot(workbook_bytes(missing_unit=True)) as workbook:
        with pytest.raises(ValueError, match="unit"):
            workbook.schemas(workbook.raw_sheet)
    with snapshot(workbook_bytes()) as workbook:
        with pytest.raises(ValueError, match="observation profiles"):
            blocks(workbook, "H2 Mass Balance Exp.fixture")


@pytest.mark.parametrize("kwargs", ({"block_rows": 0}, {"block_rows": True},
    {"start_row": 1}, {"stop_row": 1000}, {"start_row": 49, "stop_row": 48}))
def test_invalid_stream_windows_rejected(kwargs):
    with snapshot(workbook_bytes()) as workbook, pytest.raises(ValueError):
        blocks(workbook, **kwargs)


def archive_fixture(path, payload, *, member="authored/Dataset/Experiment 1.xlsx"):
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(member, payload)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_archive_receipt_crc_and_stability(tmp_path):
    path = tmp_path / "fixture.zip"
    digest = archive_fixture(path, workbook_bytes())
    with HydrideCompressorArchive(path, expected_sha256=digest, expected_bytes=path.stat().st_size) as archive:
        assert tuple(archive.experiments) == (1,)
        with archive.experiment(1) as workbook:
            assert len(blocks(workbook)[0]) == 3
    with pytest.raises(ValueError, match="SHA-256"):
        with HydrideCompressorArchive(path, expected_sha256="0" * 64, expected_bytes=None):
            pass
    with pytest.raises(ValueError, match="changed"):
        with HydrideCompressorArchive(path, expected_sha256=digest, expected_bytes=None):
            with path.open("ab") as output:
                output.write(b"changed")


@pytest.mark.parametrize("member", ("../escape.xlsx", "/absolute.xlsx", "C:/drive.xlsx", "folder\\file.xlsx"))
def test_unsafe_archive_paths_rejected(tmp_path, member):
    path = tmp_path / "unsafe.zip"
    digest = archive_fixture(path, b"authored", member=member)
    if "\\" in member:
        # Windows ZipInfo normalizes separators when authoring; replace both
        # on-disk names to exercise an actually hostile imported ZIP directory.
        path.write_bytes(path.read_bytes().replace(member.replace("\\", "/").encode(), member.encode()))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Unsafe"):
        with HydrideCompressorArchive(path, expected_sha256=digest, expected_bytes=None):
            pass


def test_expansion_and_workbook_budgets_enforced(tmp_path):
    path = tmp_path / "large.zip"
    digest = archive_fixture(path, workbook_bytes())
    with pytest.raises(ValueError, match="budget"):
        with HydrideCompressorArchive(path, expected_sha256=digest, expected_bytes=None,
                                      limits=ArchiveLimits(member_bytes=10)):
            pass
    with pytest.raises(ValueError, match="budget"):
        payload = workbook_bytes()
        HydrideCompressorWorkbook(payload, experiment=1, archive_sha256="a" * 64,
            member_name="fixture.xlsx", member_sha256=hashlib.sha256(payload).hexdigest(),
            limits=ArchiveLimits(workbook_expanded_bytes=10))


def test_iso_source_calendar_string_is_decoded_without_shift():
    payload = workbook_bytes(3)
    workbook = openpyxl.load_workbook(BytesIO(payload))
    workbook["Cycle Definition Exp.3"]["Q47"] = "2025-02-03 10:00:02"
    stream = BytesIO()
    workbook.save(stream)
    with snapshot(stream.getvalue(), 3) as source:
        assert blocks(source)[0][1].observations.values[0, 0] == 36002


def test_calendar_origins_are_part_of_clock_compatibility_basis():
    with snapshot(workbook_bytes()) as workbook:
        first = blocks(workbook)[0][0].observations
        second = next(workbook.iter_blocks(workbook.raw_sheet,
            datetime_origin=datetime(2025, 2, 2)))[0].observations
        assert second.values[0, 0] - first.values[0, 0] == 86400
        with pytest.raises(ValueError, match="basis differs"):
            first.variables[0].require_compatible(second.variables[0])


@pytest.mark.parametrize("encoding", ("serial-date-and-time", "serial-datetime", "day.month.year", "1904-epoch"))
def test_reviewed_excel_and_recorder_calendar_encodings(encoding):
    from openpyxl.utils.datetime import CALENDAR_MAC_1904, to_excel

    workbook = openpyxl.load_workbook(BytesIO(workbook_bytes(3)))
    if encoding == "1904-epoch":
        workbook.epoch = CALENDAR_MAC_1904
    sheet = workbook["Cycle Definition Exp.3"]
    if encoding == "serial-date-and-time":
        sheet["A47"] = to_excel(datetime(2025, 2, 3), epoch=workbook.epoch)
        sheet["B47"] = 10 / 24
        sheet["B47"].number_format = "General"
    elif encoding == "day.month.year":
        sheet["Q47"] = "03.02.2025  10:00:02"
    else:
        sheet["Q47"] = to_excel(datetime(2025, 2, 3, 10, 0, 2), epoch=workbook.epoch)
        sheet["Q47"].number_format = "General"
    stream = BytesIO()
    workbook.save(stream)
    with snapshot(stream.getvalue(), 3) as source:
        result = blocks(source)[0]
        assert result[0].observations.values[0, 0] == 36000
        assert result[1].observations.values[0, 0] == 36002
        assert result[0].observations.valid[0, 0]
        assert result[1].observations.valid[0, 0]
        assert dict(result[1].observations.context)["workbook_excel_epoch"] == workbook.epoch.isoformat()


def test_numeric_elapsed_header_is_not_an_excel_datetime_contract():
    workbook = openpyxl.load_workbook(BytesIO(workbook_bytes(3)))
    sheet = workbook["Cycle Definition Exp.3"]
    sheet["Q46"], sheet["Q47"] = "Elapsed seconds", 45000
    stream = BytesIO()
    workbook.save(stream)
    with snapshot(stream.getvalue(), 3) as source, pytest.raises(ValueError, match="Date/Time header"):
        blocks(source)


def test_loading_station_numeric_scalar_is_not_a_calendar_serial():
    workbook = openpyxl.load_workbook(BytesIO(workbook_bytes(6)))
    workbook["Cycle Definition Exp.6"]["M47"] = 45000
    stream = BytesIO()
    workbook.save(stream)
    with snapshot(stream.getvalue(), 6) as source:
        station = next(b for b in blocks(source)[0] if b.schema.identity.startswith("Loading"))
        assert np.isnan(station.observations.values[0, 0])
        assert not station.observations.valid[0, 0]
