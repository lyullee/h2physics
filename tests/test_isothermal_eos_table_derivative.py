"""Pressure-interpolant algebra and policy-bound persistence, not fluid validation."""

from dataclasses import replace

import numpy as np
import pytest

from h2physics.thermo.isothermal_eos_artifact import (
    load_isothermal_eos_table,
    save_isothermal_eos_table,
)
from h2physics.thermo.isothermal_eos_table import (
    IsothermalEOSTable,
    IsothermalEOSTableQualification,
    qualify_isothermal_eos_table,
)


def _table(interpolation="linear", sound_speed_mode="pressure_derivative"):
    return IsothermalEOSTable(
        np.array([0.2, 0.9, 3.7, 11.0]), np.array([270., 293., 340.]),
        np.array([[2., 9., 39., 140.], [3., 14., 61., 220.], [5., 22., 97., 360.]]),
        np.full((3, 4), 100.), "authored-pressure-interpolation-algebra",
        interpolation, sound_speed_mode,
    )


@pytest.mark.parametrize("interpolation", ["linear", "log_linear"])
def test_derivative_matches_pressure_finite_difference_and_preserves_inverse(interpolation):
    table = _table(interpolation)
    sampled = replace(table, sound_speed_mode="sampled")
    for temperature in [270., 281.5, 293., 319., 340.]:
        for density in [0.33, 2.1, 7.]:
            step = density * 1.e-5
            numerical = (table.pressure_rho_t(density + step, temperature)
                         - table.pressure_rho_t(density - step, temperature)) / (2 * step)
            assert table.isothermal_sound_speed_rho_t(density, temperature) ** 2 == pytest.approx(
                numerical, rel=1.e-8,
            )
            pressure = table.pressure_rho_t(density, temperature)
            assert table.density_pt(pressure, temperature) == pytest.approx(density, rel=2.e-14)
            assert pressure == sampled.pressure_rho_t(density, temperature)
    assert table.table_sha256 == sampled.table_sha256
    assert table.identity != sampled.identity
    assert sampled.identity == (
        f"isothermal-eos-table-v2:{interpolation}:{sampled.source_eos_identity}:"
        f"{sampled.table_sha256}"
    )


@pytest.mark.parametrize("interpolation", ["linear", "log_linear"])
def test_knot_convention_and_no_extrapolation(interpolation):
    table = _table(interpolation)
    for density, direction in [(0.2, 1), (0.9, 1), (3.7, 1), (11., -1)]:
        step = direction * density * 1.e-7
        one_sided = (table.pressure_rho_t(density + step, 300.)
                     - table.pressure_rho_t(density, 300.)) / step
        assert table.isothermal_sound_speed_rho_t(density, 300.) ** 2 == pytest.approx(
            one_sided, rel=1.e-6,
        )
    for density, temperature in [(0.19, 300.), (11.1, 300.), (1., 269.), (1., 341.)]:
        with pytest.raises(ValueError, match="envelope"):
            table.isothermal_sound_speed_rho_t(density, temperature)
    with pytest.raises(ValueError, match="sound_speed_mode"):
        replace(table, sound_speed_mode="unreviewed")


def _receipt(table):
    # Authored persistence metadata only; these are not measured qualification errors.
    return IsothermalEOSTableQualification(
        table.source_eos_identity, table.identity, table.table_sha256, 8, 1,
        table.interpolation, .001, .001, .001, .01, .001, .002,
    )


@pytest.mark.parametrize("mode", ["sampled", "pressure_derivative"])
def test_policy_artifact_roundtrip_and_cross_policy_receipt_rejection(tmp_path, mode):
    table = _table("log_linear", mode)
    path = tmp_path / "table.npz"
    receipt = _receipt(table)
    save_isothermal_eos_table(table, path, qualification=receipt)
    restored, historical = load_isothermal_eos_table(path)
    assert restored.identity == table.identity
    assert restored.sound_speed_mode == mode
    assert historical == receipt
    assert restored.isothermal_sound_speed_rho_t(2.1, 319.) == table.isothermal_sound_speed_rho_t(2.1, 319.)
    with np.load(path, allow_pickle=False) as contents:
        manifest = contents["metadata_toml"].tobytes().decode("utf-8")
    if mode == "sampled":
        assert "schema_version = 1\n" in manifest
        assert "sound_speed_mode" not in manifest
    else:
        assert "schema_version = 2\n" in manifest
        assert 'sound_speed_mode = "pressure_derivative"\n' in manifest
    other = replace(table, sound_speed_mode=("sampled" if mode == "pressure_derivative"
                                            else "pressure_derivative"))
    with pytest.raises(ValueError, match="Historical qualification receipt"):
        save_isothermal_eos_table(other, tmp_path / "wrong.npz", qualification=receipt)


def test_native_coolprop_derivative_table_requires_its_own_qualification():
    pytest.importorskip("CoolProp")
    from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS

    source = CoolPropIsothermalEOS("Hydrogen")
    table = IsothermalEOSTable.from_eos(
        source, density_axis_kg_m3=np.linspace(1., 2., 12),
        temperature_axis_k=(290., 300., 310.),
        interpolation="linear", sound_speed_mode="pressure_derivative",
    )
    receipt = qualify_isothermal_eos_table(
        table, source, validation_point_count=16, seed=20261101,
        maximum_relative_error=.01,
    )
    assert receipt.error_gate_passed
    assert receipt.table_identity == table.identity
    assert receipt.source_eos_identity == source.identity
    assert "pressure-derivative:" in receipt.table_identity
