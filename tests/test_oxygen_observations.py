"""Original cryogenic-room record fixtures; no external numerical data copied."""

import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.oxygen_observations import (
    CLOCK_UNIT,
    META_NAME,
    README_NAME,
    SENSOR_NAME,
    CryogenicRoomCase,
    CryogenicRoomCollection,
    CryogenicRoomPosition,
    CryogenicRoomRecorder,
)
from h2physics.observations import Variable


def case(invalid=False):
    return CryogenicRoomCase(
        7,
        20,
        ("7", "3 barg", "0.8 mm", "Passive"),
        3e5,
        0.0008,
        "Passive Dispersion Horizontal" + (" - Invalid test" if invalid else ""),
        invalid,
        "a" * 64,
    )


def positions():
    return {
        name: CryogenicRoomPosition(name, (0.15, 0.25, 0.35), "T,C", 40, "a" * 64)
        for name in ("Bottom1_Front", "Side1_Top", "PeenedBottomFrontTemp")
    }


def recorder(tmp_path, kind, header, rows, *, invalid=False, date="2025119", code="007"):
    path = tmp_path / f"ELE402HSE{code}{kind}{date}.csv"
    path.write_text(
        ",".join(header) + "\n" + "".join(",".join(map(str, row)) + "\n" for row in rows),
        encoding="utf-8",
    )
    return CryogenicRoomRecorder(
        path,
        case=case(invalid),
        positions=positions(),
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        directory_label="Dispersion",
    )


def test_source_processed_h2_is_neither_oxygen_nor_room_average(tmp_path):
    r = recorder(
        tmp_path, "CONC", ("Time", "H2Bottom1", "H2Side1"), [(0.0, 20.0, 80.0), (0.05, 25.0, 75.0)]
    )
    b = next(r.iter_blocks())
    np.testing.assert_array_equal(b.values, [[1.0, 0.0, 0.2, 0.8], [2.0, 0.05, 0.25, 0.75]])
    assert r.channels[1].position == positions()["Bottom1_Front"]
    assert r.channels[1].origin == Origin.RECONSTRUCTED
    assert "20m" in r.channels[1].variable.basis_id
    assert "not O2 or room average" in r.channels[1].role
    with pytest.raises(ValueError, match="differs"):
        b.observations.column(
            "H2Bottom1", expected=Variable("O2", "mole_fraction", "1", "whole-room oxygen")
        )
    assert b.observations.row_ids[0].endswith("|line-2")
    assert b.observations.experiment_ids == (case().experiment_id,) * 2
    assert b.observations.origins == (Origin.RECONSTRUCTED,) * 4


def test_clock_unit_epoch_are_not_inferred_from_grid_or_20hz_description(tmp_path):
    b = next(recorder(tmp_path, "FLMT", ("Time",), [(0.0,), (0.05,), (0.1,)]).iter_blocks())
    assert b.observations.variables[1].unit == CLOCK_UNIT
    assert b.values[-1, 1] == 0.1
    with pytest.raises(ValueError, match="unit, epoch"):
        b.as_time_series()


def test_independent_blast_and_primary_clock_columns_remain_distinct(tmp_path):
    r = recorder(
        tmp_path,
        "PRES",
        ("Time", "PT2Nozzle", "BlastTime", "BottomRightBPT"),
        [(0.0, 1.0, -0.01, -0.1), (0.05, 2.0, 0.0, 0.2), ("NaN", "NaN", 0.00001, 0.3)],
    )
    b = next(r.iter_blocks())
    assert r.channels[1].reported_clock_column == "Time"
    assert r.channels[3].reported_clock_column == "BlastTime"
    assert b.values[0, -1] == -10000.0
    assert b.valid[0, -1] and not b.valid[2, 1]
    assert b.raw_cells[-1] == ("NaN", "NaN", "1e-05", "0.3")
    assert r.channels[1].variable.quantity == "gauge_pressure"


def test_original_spaced_blast_clock_is_not_borrowed_from_slow_time(tmp_path):
    r = recorder(tmp_path, "PRES", ("Time", "Blast Time", "BottomRightBPT"), [(0.0, -0.01, 0.2)])
    assert r.channels[1].variable.name == "Blast Time"
    assert r.channels[1].variable.quantity == "reported_time_coordinate"
    assert r.channels[2].reported_clock_column == "Blast Time"
    ambiguous = recorder(
        tmp_path,
        "PRES",
        ("Time", "BlastTime", "Blast Time", "BottomRightBPT"),
        [(0.0, 0.0, 0.0, 0.2)],
    )
    assert ambiguous.channels[-1].reported_clock_column is None


def test_T_only_station_is_a_candidate_not_a_concentration_location(tmp_path):
    r = recorder(tmp_path, "CONC", ("Time", "H2Bottom1"), [(0.0, 10.0)])
    p = positions()
    p["Bottom1_Front"] = replace(p["Bottom1_Front"], sensor_roles="T")
    r = CryogenicRoomRecorder(
        r.path,
        case=case(),
        positions=p,
        expected_sha256=r.source_sha256,
        directory_label="Dispersion",
    )
    channel = r.channels[1]
    assert channel.variable.quantity == "volume_fraction" and channel.variable.unit == "1"
    assert channel.position is None and channel.candidate_position is p["Bottom1_Front"]
    assert channel.issues == ("concentration_header_conflicts_with_T_only_station_role",)


def test_ventilation_litres_per_minute_are_not_hydrogen_mass_flow(tmp_path):
    b = next(
        recorder(
            tmp_path, "FLMT", ("Time", "FanFlowMeter", "DPT"), [(0.0, -60.0, 17.0)]
        ).iter_blocks()
    )
    assert b.values[0, 2] == -0.001
    assert b.recorder.channels[1].variable.quantity == "volume_flow"
    assert "not hydrogen release mass flow" in b.recorder.channels[1].role
    assert b.recorder.channels[2].variable.unit == "source_unit_unresolved"
    assert b.observations.origins[-1] == Origin.UNRESOLVED


def test_weather_pressure_and_box_gauge_scaling_are_separate(tmp_path):
    weather = recorder(
        tmp_path,
        "MISC",
        ("Time", "AmbientTemperature", "Humidity", "Pressure", "WindDirection", "WindSpeed"),
        [(0.0, 20.0, 50.0, 990.0, 180.0, 2.0)],
    )
    b = next(weather.iter_blocks())
    np.testing.assert_allclose(b.values[0, 2:], [293.15, 0.5, 99000.0, np.pi, 2.0])
    assert weather.channels[3].variable.quantity == "pressure"
    gauge = recorder(
        tmp_path, "PRES", ("Time", "PTBox1_TopLeft", "PT1ReleaseRig"), [(0.0, -2.0, 0.5)]
    )
    b = next(gauge.iter_blocks())
    np.testing.assert_allclose(b.values[0, 2:], [-200.0, 50000.0])
    assert b.valid.all()
    assert gauge.channels[1].variable.quantity == "gauge_pressure"


def test_unphysical_and_source_range_fields_remain_raw_and_masked(tmp_path):
    b = next(
        recorder(
            tmp_path, "CONC", ("Time", "H2Bottom1", "H2Side1"), [(0.0, -1.0, 101.0)]
        ).iter_blocks()
    )
    np.testing.assert_array_equal(b.raw_values, [[0.0, -1.0, 101.0]])
    np.testing.assert_allclose(b.values, [[1.0, 0.0, -0.01, 1.01]])
    np.testing.assert_array_equal(b.valid, [[True, True, False, False]])
    assert all("reported_H2_range" in r for r in b.reasons[0][1:])
    t = next(
        recorder(
            tmp_path, "TEMP", ("Time", "NozzleTemp", "PeenedBottomFrontTemp"), [(0.0, 20.0, 0.0)]
        ).iter_blocks()
    )
    # Below the conflicting reported 77K instrument bound remains a positive
    # measured output with its calibration issue, never an invented correction.
    assert t.valid[0, 2] and t.values[0, 2] == 20.0
    assert not t.valid[0, 3] and t.values[0, 3] == 0.0


def test_source_invalid_case_masks_physical_fields_without_deleting_rows(tmp_path):
    r = recorder(
        tmp_path, "FLMT", ("Time", "FanFlowMeter"), [(0.0, 100.0), (0.05, 90.0)], invalid=True
    )
    b = next(r.iter_blocks())
    assert b.numeric_valid.all()
    np.testing.assert_array_equal(b.valid, [[True, True, False], [True, True, False]])
    assert b.raw_values[0, 1] == 100.0
    assert dict(b.observations.context)["source_declared_invalid_case"] == "True"


def test_finite_source_overflow_after_conversion_is_retained_and_masked(tmp_path):
    r = recorder(tmp_path, "PRES", ("Time", "PT2Nozzle"), [(0.0, 1e308)])
    with np.errstate(over="ignore"):
        b = next(r.iter_blocks())
    assert b.raw_values[0, 1] == 1e308 and b.numeric_valid[0, 1]
    assert np.isinf(b.values[0, 2]) and not b.valid[0, 2]
    assert b.reasons[0][1] == "nonfinite_after_unit_conversion"
    assert not b.observations.valid[0, 2]


@pytest.mark.parametrize(
    "raw,reason",
    [
        ("", "missing"),
        ("#N/A", "nonnumeric"),
        ("NaN", "nonfinite"),
        ("=1+1", "formula_not_evaluated"),
    ],
)
def test_missing_nonnumeric_formula_fields_do_not_become_zero(tmp_path, raw, reason):
    b = next(recorder(tmp_path, "PRES", ("Time", "Var4"), [(0.0, raw)]).iter_blocks())
    assert b.raw_cells[0][1] == raw
    assert np.isnan(b.values[0, 2]) and not b.valid[0, 2]
    assert b.reasons[0][1] == reason
    assert b.recorder.channels[1].variable.quantity == "reported_unknown"


def test_existing_bounded_reader_source_lines_windows_and_hash_guard(tmp_path):
    r = recorder(tmp_path, "FLMT", ("Time", "FanFlowMeter"), [(i, i * 10.0) for i in range(10)])
    small = tuple(r.iter_blocks(block_rows=2))
    large = tuple(r.iter_blocks(block_rows=7))
    np.testing.assert_array_equal(
        np.concatenate([b.values for b in small]), np.concatenate([b.values for b in large])
    )
    assert sum((b.observations.row_ids for b in small), ()) == sum(
        (b.observations.row_ids for b in large), ()
    )
    w = next(r.iter_blocks(source_line_start=4, source_line_stop=7))
    np.testing.assert_array_equal(w.source_lines, [4, 5, 6])
    assert not w.raw_values.flags.writeable and not w.valid.flags.writeable
    r.path.write_text(r.path.read_text() + "11,110\n")
    with pytest.raises(ValueError, match="changed"):
        tuple(r.iter_blocks())


def test_leading_zero_and_date_tokens_are_not_rewritten(tmp_path):
    r = recorder(tmp_path, "FLMT", ("Time",), [(0.0,)], code="0007")
    assert "HSE0007" in r.source_id and r.date_token == "2025119"
    with pytest.raises(ValueError, match="test identity"):
        CryogenicRoomRecorder(
            r.path,
            case=replace(case(), number=8),
            positions=positions(),
            expected_sha256=r.source_sha256,
            directory_label="Dispersion",
        )


def collection_fixture(tmp_path):
    directory = tmp_path / "elvhys-cold-room/1.1"
    directory.mkdir(parents=True)
    (directory / README_NAME).write_text(
        "Authored fixture\n7\t3 barg\t0.8 mm\tPassive\tDispersion Horizontal\n"
        "8\t3 barg\t0.8 mm\tPassive\tDispersion Horizontal - Invalid test\n"
        "Bottom1_Front\t150\t250\t350\tT,C\n",
        encoding="utf-8",
    )
    (directory / META_NAME).write_text("Title,Authored metadata\n", encoding="utf-8")
    (directory / SENSOR_NAME).write_bytes(
        b"%PDF-1.4\nAuthored hash-only supporting fixture\n%%EOF\n"
    )
    r = recorder(directory, "CONC", ("Time", "H2Bottom1"), [(0.0, 10.0), (0.05, 20.0)])
    files = []
    for p in (directory / README_NAME, directory / META_NAME, directory / SENSOR_NAME, r.path):
        files.append(
            {
                "restricted": False,
                "directoryLabel": "Dispersion" if p == r.path else "",
                "dataFile": {
                    "filename": p.name,
                    "filesize": p.stat().st_size,
                    "checksum": {"type": "MD5", "value": hashlib.md5(p.read_bytes()).hexdigest()},
                },
            }
        )
    metadata = json.dumps(
        {
            "data": {
                "latestVersion": {
                    "versionNumber": 1,
                    "versionMinorNumber": 1,
                    "license": {"rightsIdentifier": "CC0-1.0"},
                    "files": files,
                }
            }
        }
    ).encode()
    sha = hashlib.sha256(metadata).hexdigest()
    (directory / f"repository-metadata-{sha}.json").write_bytes(metadata)
    text = (
        'key="elvhys-cold-room"\ndoi="10.18710/JXJP0H"\nversion="1.1"\nlicense_id="CC0-1.0"\n'
        'rights_permitted=true\nmetadata_sha256="'
        + sha
        + '"\nlisted_file_count=4\nomitted_files=[]\n'
    )
    for f in files:
        p = directory / f["dataFile"]["filename"]
        text += (
            '\n[[files]]\nname="'
            + p.name
            + '"\nrelative_path="'
            + p.relative_to(tmp_path).as_posix()
            + '"\n'
            'status="cached"\nsize_bytes='
            + str(p.stat().st_size)
            + '\nsha256="'
            + hashlib.sha256(p.read_bytes()).hexdigest()
            + '"\n'
            'publisher_checksum="' + f["dataFile"]["checksum"]["value"] + '"\n'
        )
    receipt = tmp_path / "receipt.toml"
    receipt.write_text(text, encoding="utf-8")
    return receipt


def test_full_source_scope_and_runtime_cases_positions(tmp_path):
    receipt = collection_fixture(tmp_path)
    c = CryogenicRoomCollection(receipt, tmp_path)
    assert c.observed_case_numbers == (7,) and c.absent_case_numbers == (8,)
    assert c.cases[8].source_declared_invalid
    assert c.cases[7].nominal_tanker_gauge_pressure_pa == 300000.0
    assert c.cases[7].nominal_nozzle_diameter_m == 0.0008
    assert c.positions["Bottom1_Front"].position_m == pytest.approx((0.15, 0.25, 0.35))
    assert len(c.verify_sources()) == 4
    assert len(c.recorders) == 1
    assert c.recorders[0].channels[1].position.source_line == 4


def test_incomplete_acquisition_and_rights_cannot_claim_profile(tmp_path):
    receipt = collection_fixture(tmp_path)
    original = receipt.read_text()
    receipt.write_text(original.replace("omitted_files=[]", 'omitted_files=["unfinished.csv"]'))
    with pytest.raises(ValueError, match="Incomplete"):
        CryogenicRoomCollection(receipt, tmp_path)
    receipt.write_text(original.replace("rights_permitted=true", "rights_permitted=false"))
    with pytest.raises(ValueError, match="rights"):
        CryogenicRoomCollection(receipt, tmp_path)
    receipt.write_text(original)
    c = CryogenicRoomCollection(receipt, tmp_path)
    receipt.write_text(original + "\n# changed\n")
    with pytest.raises(ValueError, match="receipt"):
        c.verify_sources()
