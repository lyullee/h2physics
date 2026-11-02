"""Original HDF5 vectors exercise source clocks, units, masks and mismatched exports."""

from dataclasses import replace
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.pressure_peaking import file_sha256
from h2physics.data.thermal_effects import (
    CLOCK_UNIT,
    SOURCE_FIELDS,
    ThermalEffectsFile,
    thermal_location_rows,
)
from h2physics.observations import Variable

h5py = pytest.importorskip("h5py")


def source_fixture(tmp_path, *, name="authored.mat", missing_ts=False, vent_mismatch=True):
    path = tmp_path / name
    with h5py.File(path, "w") as source:
        for group, fields in SOURCE_FIELDS.items():
            if missing_ts and group == "TS":
                continue
            obj = source.create_group(group)
            obj.attrs["MATLAB_class"] = np.bytes_("struct")
            for index, field in enumerate(fields):
                count = 3 if field in ("RHF3", "timech7") else 5
                if vent_mismatch and group == "Vent" and field == "T":
                    count = 7
                values = np.arange(count, dtype=float)
                if field.startswith(("RHF", "THF")):
                    values -= 2.
                elif field == "mfr":
                    values -= 3.
                elif field == "P":
                    values -= 1.
                elif field in ("T", "temp1", "temp2") or field.startswith("TT"):
                    values[:] = 20.
                    values[1] = -300.
                elif field in ("time", "timech7"):
                    values *= .25
                    if group == "MFM":
                        values[:] = (0., .25, .25, np.nan, .1)
                shape = (1, count) if index % 2 else (count, 1)
                dataset = obj.create_dataset(field, data=values.reshape(shape), compression="gzip")
                dataset.attrs["MATLAB_class"] = np.bytes_("double")
    return path


def open_source(path, **kwargs):
    return ThermalEffectsFile(path, source_id="authored-thermal-fixture",
        experiment_id="authored-case", expected_sha256=file_sha256(path), **kwargs)


def recorder(source, identity):
    return next(item for item in source.recorders if item.identity == identity)


def test_native_slicing_units_signed_values_and_thermal_roles(tmp_path):
    with open_source(source_fixture(tmp_path)) as source:
        mfm = next(source.iter_blocks(recorder(source, "/MFM/time"))).observations
        assert mfm.column("mfr")[0][0] == -.003
        assert mfm.column("P")[0][0] == -100000
        assert mfm.column("P")[1][0]
        assert "absolute/gauge" in next(v.basis_id for v in mfm.variables if v.name == "P")
        assert mfm.column("T")[0][0] == 293.15
        assert mfm.column("T")[0][1] == pytest.approx(-26.85)
        assert not mfm.column("T")[1][1]
        assert "not gas temperature" in next(v.basis_id for v in mfm.variables if v.name == "T")
        hf = next(source.iter_blocks(recorder(source, "/HF/time"))).observations
        assert hf.column("RHF1")[0][0] == -2000
        assert hf.column("RHF1")[1][0]
        assert next(v.quantity for v in hf.variables if v.name == "THF1") == "reported_total_heat_flux"
        assert hf.origins[next(i for i,v in enumerate(hf.variables) if v.name == "THF1")] == Origin.UNRESOLVED
        vent = next(source.iter_blocks(recorder(source, "/Vent/time"))).observations
        assert vent.column("ACH")[0][1] == pytest.approx(1 / 3600)
        assert vent.column("vfr")[0][1] == pytest.approx(1 / 3600)


def test_default_rhf3_is_unclocked_even_with_matching_candidate_length(tmp_path):
    with open_source(source_fixture(tmp_path)) as source:
        signal = recorder(source, "/HF/RHF3/unclocked")
        clock = recorder(source, "/HF/timech7/clock-only")
        assert signal.samples == clock.samples == 3
        assert signal.clock_path is None
        assert signal.candidate_clock_paths == ("/HF/timech7",)
        block = next(source.iter_blocks(signal))
        np.testing.assert_array_equal(block.source_indices, (1, 2, 3))
        assert not np.any(block.valid[:, 1])
        assert block.origins[1] == Origin.UNRESOLVED
        assert np.all(next(source.iter_blocks(clock)).valid[:, 1])


def test_only_explicit_evidence_opt_in_connects_candidate_clock(tmp_path):
    with open_source(source_fixture(tmp_path)) as source:
        with pytest.raises(ValueError, match="evidence"):
            source.associate_clock("/HF/RHF3", "/HF/timech7", evidence_id="")
        linked = source.associate_clock("/HF/RHF3", "/HF/timech7", evidence_id="authored-declaration-1")
        block = next(source.iter_blocks(linked))
        assert np.all(block.valid[:, 1])
        assert block.origins[1] == Origin.RECONSTRUCTED
        assert "authored-declaration-1" in block.variables[1].basis_id
        assert block.variables[1].unit == CLOCK_UNIT
        with pytest.raises(ValueError, match="TimeSeries"):
            block.as_time_series()
        with pytest.raises(ValueError, match="lengths differ"):
            source.associate_clock("/Vent/T", "/Vent/time", evidence_id="cannot-repair-length")


def test_descriptor_cannot_forge_measured_clock_pairing(tmp_path):
    with open_source(source_fixture(tmp_path)) as source:
        original = recorder(source, "/HF/RHF3/unclocked")
        forged = replace(original, clock_path="/HF/timech7", clock_origin=Origin.MEASURED)
        with pytest.raises(ValueError, match="relationship"):
            next(source.iter_blocks(forged))


def test_mismatched_vent_temperature_survives_in_full_without_clock_borrowing(tmp_path):
    with open_source(source_fixture(tmp_path)) as source:
        unclocked = recorder(source, "/Vent/T/unclocked")
        block = next(source.iter_blocks(unclocked))
        assert len(block.values) == 7
        assert np.all(np.isnan(block.raw_values[:, 0]))
        assert not np.any(block.valid[:, 1])
        assert source._file["/Vent/T"].size == len(block.values)
        assert len(next(source.iter_blocks(recorder(source, "/Vent/time"))).values) == 5


def test_clock_anomalies_and_unknown_trigger_unit_retained(tmp_path):
    with open_source(source_fixture(tmp_path)) as source:
        blocks = list(source.iter_blocks(recorder(source, "/MFM/time"), block_rows=2))
        assert sum(issue.count for b in blocks for issue in b.issues if issue.code == "nonincreasing_clock_retained") == 2
        assert not blocks[1].valid[1, 1]
        assert all(b.variables[1].unit == CLOCK_UNIT for b in blocks)
        ts = next(source.iter_blocks(recorder(source, "/TS/time"))).observations
        assert next(v.unit for v in ts.variables if v.name == "trig") == "unresolved"


def test_blocks_windows_raw_orientation_and_row_identity(tmp_path):
    path = source_fixture(tmp_path)
    with open_source(path) as source:
        spec = recorder(source, "/HF/time")
        whole = next(source.iter_blocks(spec))
        streamed = list(source.iter_blocks(spec, block_rows=2))
        np.testing.assert_equal(np.concatenate([b.values for b in streamed]), whole.values)
        np.testing.assert_equal(np.concatenate([b.raw_values for b in streamed]), whole.raw_values)
        window = next(source.iter_blocks(spec, first_index=2, last_index=4))
        np.testing.assert_equal(window.values, whole.values[1:4])
        assert window.observations.row_ids == whole.observations.row_ids[1:4]
        assert source.sha256 in whole.observations.row_ids[0]
        assert "/HF/time" in whole.observations.row_ids[0]
        assert any(shape == (1, 5) for _,shape,_,_ in source.inventory)
        assert any(shape == (5, 1) for _,shape,_,_ in source.inventory)
        with pytest.raises(ValueError):
            whole.values[0, 0] = 100


def test_absent_ts_is_not_invented(tmp_path):
    with open_source(source_fixture(tmp_path, missing_ts=True)) as source:
        assert not any(item.identity.startswith("/TS/") for item in source.recorders)


@pytest.mark.parametrize("kwargs", ({"block_rows": 0}, {"block_rows": True},
    {"block_rows": 100001}, {"first_index": 0}, {"last_index": 100}))
def test_invalid_windows_rejected(tmp_path, kwargs):
    with open_source(source_fixture(tmp_path)) as source, pytest.raises(ValueError):
        next(source.iter_blocks(recorder(source, "/HF/time"), **kwargs))


def test_source_hash_preflight_and_context_stability(tmp_path, monkeypatch):
    path = source_fixture(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        with ThermalEffectsFile(path, source_id="x", experiment_id="x", expected_sha256="0" * 64):
            pass
    with pytest.raises(ValueError, match="budget"):
        with open_source(path, maximum_total_array_bytes=10):
            pass
    with pytest.raises(ValueError, match="changed"):
        with open_source(path):
            # Native Windows HDF5 locks prevent concurrent byte mutation. Inject
            # the changed end digest to independently exercise the stability gate.
            monkeypatch.setattr("h2physics.data.thermal_effects.file_sha256", lambda _: "0" * 64)


def test_external_dataset_link_and_unreviewed_dtype_rejected(tmp_path):
    path = source_fixture(tmp_path)
    with h5py.File(path, "a") as source:
        del source["HF/RHF1"]
        source["HF/RHF1"] = h5py.ExternalLink("outside.mat", "/anything")
    with pytest.raises(ValueError, match="links"):
        with open_source(path):
            pass
    path = source_fixture(tmp_path, name="integer.mat")
    with h5py.File(path, "a") as source:
        del source["HF/RHF1"]
        source["HF"].create_dataset("RHF1", data=np.ones((5, 1), dtype=int))
    with pytest.raises(ValueError, match="double"):
        with open_source(path):
            pass


def test_model_quantity_clock_and_sensor_basis_require_evidence(tmp_path):
    with open_source(source_fixture(tmp_path)) as source:
        mfm = next(source.iter_blocks(recorder(source, "/MFM/time"))).observations
        with pytest.raises(ValueError, match="basis differs"):
            mfm.column("reported_clock", expected=Variable("time", "time", "s"))
        with pytest.raises(ValueError, match="basis differs"):
            mfm.column("P", expected=Variable("p", "pressure", "Pa", "absolute"))
        with pytest.raises(ValueError, match="basis differs"):
            mfm.column("T", expected=Variable("gas", "temperature", "K", "bulk gas"))
        hf = next(source.iter_blocks(recorder(source, "/HF/time"))).observations
        with pytest.raises(ValueError, match="basis differs"):
            hf.column("RHF1", expected=Variable("total", "reported_total_heat_flux", "W/m2"))
        assert mfm.variables[1].basis_id != hf.variables[1].basis_id


def test_source_location_table_order_is_runtime_metadata_not_reordered_geometry(tmp_path):
    path = tmp_path / "authored.docx"
    rows = (("Location parameters [mm]",), ("", "y", "x", "z"),
            ("authored-probe", "12", "34", "56"), ("authored-incomplete", "inside"))
    body = "".join("<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{value}</w:t></w:r></w:p></w:tc>"
        for value in row) + "</w:tr>" for row in rows)
    xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f'<w:body><w:tbl>{body}</w:tbl></w:body></w:document>')
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
    assert thermal_location_rows(path, expected_sha256=file_sha256(path)) == rows


def test_zero_radiometer_is_retained_without_inventing_sensor_failure(tmp_path):
    path = source_fixture(tmp_path)
    with h5py.File(path, "a") as source:
        source["HF/RHF1"][...] = 0
    with open_source(path) as source:
        field = next(source.iter_blocks(recorder(source, "/HF/time"))).observations
        assert np.all(field.column("RHF1")[0] == 0)
        assert np.all(field.column("RHF1")[1])
