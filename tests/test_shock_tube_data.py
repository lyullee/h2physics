"""Original small recorder fixtures; no external numerical records copied."""

import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.shock_tube import (
    HEADERS,
    ShockTubeCollection,
    ShockTubeRecorder,
)
from h2physics.observations import Variable


def recorder(tmp_path, kind="PRESS", rows=None, name=None):
    name = name or f"ELE431KIT021{kind}20260102.csv"
    path = tmp_path / name
    if rows is None:
        rows = (
            (-0.5, 2.0, -0.1, 0.2, 0.001, -3.0, 4.0, 5.0),
            (0.0, 3.0, -0.2, 0.3, -0.002, 6.0, -7.0, 8.0),
        )
    delimiter = "," if kind == "MICR" else ";"
    header = HEADERS["TEMP" if kind == "TEMPL" else kind]
    path.write_text(
        delimiter.join(header)
        + "\n"
        + "".join(delimiter.join(map(str, row)) + "\n" for row in rows),
        encoding="utf-8",
    )
    return ShockTubeRecorder(path)


def test_engineering_units_signed_fields_and_pressure_meaning(tmp_path):
    r = recorder(tmp_path)
    b = next(r.iter_blocks())
    np.testing.assert_array_equal(b.values[:, 0], [-30.0, 0.0])
    np.testing.assert_array_equal(b.values[0, 1:], [2e5, -1e4, 2e4, 100.0, -300.0, 400.0, 500.0])
    assert b.valid.all()
    assert r.channels[1].variable.quantity == "reported_pressure"
    assert "conflict" in r.channels[1].issues[0]
    assert r.channels[3].variable.quantity == "pressure_difference"
    with pytest.raises(ValueError, match="differs"):
        b.observations.column("p_1", expected=Variable("p_1", "pressure", "Pa", "absolute"))
    assert b.series.origin == Origin.MEASURED
    assert b.series.clock_id == r.clock_id
    assert b.observations.origins[0] == Origin.RECONSTRUCTED
    assert b.raw_cells[0][2] == "-0.1"
    assert b.raw_lines[0].endswith("\n")
    assert b.observations.row_ids[0].endswith("|line-2")
    assert not b.values.flags.writeable


def test_temperature_range_masks_preserve_zero_and_negative_raw_values(tmp_path):
    r = recorder(tmp_path, "TEMP", [(-1.0, 25.0, 0.0, -2.0, 501.0, "", "NaN", "=3+4")])
    b = next(r.iter_blocks())
    np.testing.assert_array_equal(b.valid, [[True, True, False, False, False, False, False, False]])
    assert b.raw_values[0, 2] == b.values[0, 2] == 0.0
    assert b.values[0, 3] == -2.0
    assert b.reasons[0][5:] == ("missing", "nonfinite", "formula_not_evaluated")
    assert b.raw_cells[0][-1] == "=3+4"
    assert b.series.valid[0, 1] == 0


def test_fast_dynamic_signed_pressure_is_not_silently_rebased(tmp_path):
    r = recorder(tmp_path, "PRESF", [(-0.001, *([-0.03] * 11)), (0.0, *([0.02] * 11))])
    b = next(r.iter_blocks())
    assert b.valid.all()
    assert b.values[0, 7] == -3000.0
    assert r.channels[6].variable.quantity == "reported_pressure"
    assert "dynamic signed" in r.channels[6].variable.basis_id
    assert b.series.time_s[0] == -0.001


def test_sound_keeps_logarithmic_output_and_unresolved_weighting(tmp_path):
    b = next(recorder(tmp_path, "MICR", [(0.0, 55.0), (0.001, 70.0)]).iter_blocks())
    assert b.recorder.delimiter == ","
    assert b.series.units == ("dB",)
    assert b.series.quantities == ("reported_sound_level",)
    assert "weighting" in b.series.basis_ids[0]


def test_same_code_different_date_or_recorder_has_distinct_clock_and_rows(tmp_path):
    a = recorder(tmp_path)
    b = recorder(tmp_path, name="ELE431KIT021PRESS20260103.csv")
    c = recorder(tmp_path, "TEMP", [(0.0, *([20.0] * 7)), (1.0, *([21.0] * 7))])
    assert len({a.clock_id, b.clock_id, c.clock_id}) == 3
    assert a.run_id != b.run_id and a.run_id == c.run_id
    assert (
        next(a.iter_blocks()).observations.row_ids[0]
        != next(b.iter_blocks()).observations.row_ids[0]
    )


def test_templ_suffix_preserves_original_filename(tmp_path):
    r = recorder(tmp_path, "TEMPL", [(0.0, *([20.0] * 7))])
    assert r.kind == "TEMP" and "TEMPL" in r.source_id


def test_blocks_and_source_line_windows_are_stable(tmp_path):
    r = recorder(tmp_path, rows=[(i / 60, *([i] * 7)) for i in range(9)])
    a = tuple(r.iter_blocks(block_rows=2))
    b = tuple(r.iter_blocks(block_rows=5))
    np.testing.assert_array_equal(
        np.concatenate([x.values for x in a]), np.concatenate([x.values for x in b])
    )
    assert sum((x.observations.row_ids for x in a), ()) == sum(
        (x.observations.row_ids for x in b), ()
    )
    w = tuple(r.iter_blocks(source_line_start=4, source_line_stop=8, block_rows=3))
    np.testing.assert_array_equal(np.concatenate([x.source_lines for x in w]), [4, 5, 6, 7])
    assert w[0].predecessor_time_s == 1.0


@pytest.mark.parametrize("bad", ["", "NaN", "=1+1"])
def test_invalid_clocks_stay_in_observations_and_block_series(tmp_path, bad):
    b = next(recorder(tmp_path, rows=[(bad, *([1.0] * 7))]).iter_blocks())
    assert not b.observations.valid[0, 0]
    with pytest.raises(ValueError, match="clock"):
        _ = b.series


def test_nonincreasing_clock_across_block_boundary_is_not_hidden(tmp_path):
    a, b = tuple(
        recorder(tmp_path, rows=[(0.0, *([1.0] * 7)), (0.0, *([2.0] * 7))]).iter_blocks(
            block_rows=1
        )
    )
    assert a.series.time_s[0] == 0.0
    assert b.observations.valid.all()
    with pytest.raises(ValueError, match="boundary"):
        _ = b.series


def test_source_hash_schema_row_and_line_budgets(tmp_path):
    r = recorder(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        ShockTubeRecorder(r.path, expected_sha256="0" * 64)
    with pytest.raises(ValueError, match="row budget"):
        tuple(r.iter_blocks(maximum_rows=1))
    with pytest.raises(ValueError, match="byte budget"):
        ShockTubeRecorder(r.path, maximum_bytes=1)
    with pytest.raises(ValueError, match="block_rows"):
        tuple(r.iter_blocks(block_rows=True))
    r.path.write_text(r.path.read_text() + "1;2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        tuple(r.iter_blocks())
    changed = ShockTubeRecorder(r.path)
    with pytest.raises(ValueError, match="physical line 4"):
        tuple(changed.iter_blocks())


def test_unreviewed_unit_header_and_filename_fail(tmp_path):
    r = recorder(tmp_path)
    r.path.write_text(r.path.read_text().replace("bar_a", "psi"), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        ShockTubeRecorder(r.path)
    with pytest.raises(ValueError, match="filename"):
        ShockTubeRecorder(tmp_path / "arbitrary.csv")


def collection_fixture(tmp_path):
    raw = tmp_path / "elvhys-shock-tube/1.0"
    raw.mkdir(parents=True)
    r = recorder(raw)
    (raw / "00_README_ELVHYS_WP_4_3_1.txt").write_text(
        "Authored fixture: L = 700 mm and ID (internal diameter) = 42 mm.\n"
        "p_2a\t42\t600\t0\tP\nT_2a\t42\t600\t180\tT\n",
        encoding="utf-8",
    )
    (raw / "ELE431KITMETA.csv").write_text(
        'Experimental Data;"Authored fixture\nELE431KIT021DATA20260102 [0.2 mm,6.5 bar_a, 7.0%, 19C]**"\n',
        encoding="utf-8",
    )
    metadata = {
        "data": {
            "latestVersion": {
                "versionNumber": 1,
                "versionMinorNumber": 0,
                "license": {"rightsIdentifier": "CC0-1.0"},
            }
        }
    }
    p = raw / "repository-metadata.json"
    p.write_text(json.dumps(metadata), encoding="utf-8")
    receipt = tmp_path / "receipt.toml"
    text = (
        'key="elvhys-shock-tube"\ndoi="10.18710/M5LOLM"\nversion="1.0"\n'
        'license_id="CC0-1.0"\nrights_permitted=true\nmetadata_sha256="'
        + hashlib.sha256(p.read_bytes()).hexdigest()
        + '"\n'
    )
    for p in (raw / "00_README_ELVHYS_WP_4_3_1.txt", raw / "ELE431KITMETA.csv", r.path):
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
        )
    receipt.write_text(text, encoding="utf-8")
    return receipt


def test_collection_native_rights_conditions_geometry_and_lineage(tmp_path):
    path = collection_fixture(tmp_path)
    c = ShockTubeCollection(path, tmp_path)
    run = c.runs["ELE431KIT021:20260102"]
    np.testing.assert_allclose(run.conditions.values, [[650000.0, 0.07, 292.15]])
    assert run.conditions.origins == (Origin.RECONSTRUCTED,) * 3
    assert "not initial tube" in run.conditions.variables[-1].basis_id
    assert run.ignition_condition == "unignited/inert-labelled"
    assert run.metadata_source_line == 2
    assert c.reported_tube_geometry_m == pytest.approx((0.7, 0.042))
    assert c.positions["p_2a"].reported_r_m == 0.042
    assert c.positions["p_2a"].reported_z_m == 0.6
    assert len(c.verify_sources()) == 3


def test_collection_rejects_rights_changes_path_escape_and_stale_metadata(tmp_path):
    path = collection_fixture(tmp_path)
    original = path.read_text()
    path.write_text(original.replace("rights_permitted=true", "rights_permitted=false"))
    with pytest.raises(ValueError, match="rights"):
        ShockTubeCollection(path, tmp_path)
    path.write_text(original.replace('relative_path="elvhys', 'relative_path="../elvhys'))
    with pytest.raises(ValueError, match="Unsafe"):
        ShockTubeCollection(path, tmp_path)
    path.write_text(original)
    c = ShockTubeCollection(path, tmp_path)
    path.write_text(original + "\n# changed\n")
    with pytest.raises(ValueError, match="changed"):
        c.verify_sources()


def test_direct_block_immutable_rows_and_variable_identity(tmp_path):
    b = next(recorder(tmp_path).iter_blocks())
    with pytest.raises(ValueError, match="columns"):
        replace(b, values=b.values[:, :-1])
    assert b.observations.variables == b.recorder.variables
