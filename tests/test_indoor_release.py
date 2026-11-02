"""Basic inputs, native projections and the ignition-delay clock boundary."""

import importlib.util
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.indoor_release import (
    IndoorEnclosure,
    IndoorHydrogenSource,
    IndoorReleaseSettings,
    IndoorVent,
    run_hyram_indoor_release,
)


def inputs():
    return (IndoorHydrogenSource(2e5, 293.15, .01, .001, "authored-H2-source", "authored-SI"),
            IndoorEnclosure(2., 4., .5, 2., IndoorVent(.04, 1.9), IndoorVent(.04, .1),
                            "authored-room"),
            IndoorReleaseSettings(.1, "source-operation-clock", source_start_time_s=42.,
                                   steady_source=True, steady_steps=2))


@pytest.fixture(scope="module")
def native_result():
    optional_path = os.environ.get("H2PHYSICS_HYRAM_PATH")
    if optional_path:
        # Local/native dependency selection is explicit and never copied into distributions.
        import sys
        assert (Path(optional_path) / "hyram").is_dir()
        sys.path.insert(0, optional_path)
    if importlib.util.find_spec("hyram") is None:
        pytest.skip("Separately installed HyRAM+ 6.1 or H2PHYSICS_HYRAM_PATH is required")
    return run_hyram_indoor_release(*inputs())


def test_native_projection_preserves_fraction_pressure_and_clock(native_result):
    result = native_result
    assert result.native_version == "6.1"
    assert result.axis_kind == "release_age_at_hypothetical_ignition"
    assert not hasattr(result, "blast_time_s")
    np.testing.assert_array_equal(result.ignition_delay_s, result.native.t_layer)
    np.testing.assert_array_equal(result.layer_hydrogen_mole_fraction, result.native.x_layer)
    np.testing.assert_array_equal(result.layer_depth_m, result.native.H_layer)
    np.testing.assert_array_equal(result.peak_overpressure_pa_gauge, result.native.dP_tot)
    np.testing.assert_array_equal(result.ignition_clock_time_s, result.native.t_layer + 42.)
    np.testing.assert_array_equal(result.conditional_peak_pressure_pa_absolute,
                                 result.native.dP_tot + 101325.)
    assert result.ignition_delay_s[-1] == pytest.approx(.1)
    assert result.layer_hydrogen_mole_fraction[-1] > 0
    assert result.peak_overpressure_pa_gauge[-1] > 0
    assert result.native.enclosure.H_release == .5
    assert result.require_current() is result
    source, room, settings = inputs()
    with pytest.raises(ValueError, match="single-gas"):
        run_hyram_indoor_release(replace(source, temperature_k=20.), room, settings)


def test_native_snapshots_are_immutable_and_changed_native_is_rejected(native_result):
    result = native_result
    with pytest.raises(ValueError):
        result.ignition_delay_s.setflags(write=True)
    original = result.native.dP_tot.copy()
    try:
        result.native.dP_tot[-1] += 1.
        with pytest.raises(ValueError, match="changed"):
            result.require_current()
    finally:
        result.native.dP_tot[:] = original
    result.require_current()


@pytest.mark.parametrize("changes", [{"duration_s": 0.}, {"steady_steps": True},
    {"ambient_pressure_pa_absolute": -1.}, {"jet_relative_tolerance": float("nan")},
    {"clock_id": ""}, {"release_angle_rad": 4.}])
def test_invalid_settings_rejected_before_native_import(changes):
    with pytest.raises((ValueError, TypeError)):
        replace(inputs()[2], **changes)


def test_source_and_geometry_admission():
    source, room, settings = inputs()
    with pytest.raises(ValueError, match="exceed ambient"):
        run_hyram_indoor_release(replace(source, pressure_pa_absolute=1e4), room, settings)
    with pytest.raises(ValueError, match="within"):
        replace(room, release_height_m=3.)
    with pytest.raises(ValueError, match="below"):
        replace(room, floor_vent=IndoorVent(.1, 1.95))
    with pytest.raises(ValueError, match="negative"):
        IndoorVent(-.1, .2)
    with pytest.raises(ValueError):
        replace(source, orifice_diameter_m=0.)
