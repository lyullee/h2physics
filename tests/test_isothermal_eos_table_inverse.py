"""Algebraic inversion checks for the existing bounded pressure interpolant."""

import numpy as np
import pytest

from h2physics.thermo.isothermal_eos_table import IsothermalEOSTable


def _table(mode):
    density = np.array([0.2, 0.9, 3.7, 11.0])
    temperature = np.array([270.0, 293.0, 340.0])
    pressure = np.array([[2.0, 9.0, 39.0, 140.0],
                         [3.0, 14.0, 61.0, 220.0],
                         [5.0, 22.0, 97.0, 360.0]])
    return IsothermalEOSTable(density, temperature, pressure,
                              np.full_like(pressure, 100.0),
                              "authored-interpolation-algebra-reference", mode)


def test_log_pressure_interpolation_inverts_in_linear_density_coordinates():
    table = IsothermalEOSTable(
        np.array([1.0, 4.0]), np.array([290.0, 310.0]),
        np.array([[1.0, 16.0], [1.0, 16.0]]), np.ones((2, 2)),
        "authored-inverse-algebra-counterexample", "log_linear",
    )
    assert table.pressure_rho_t(2.5, 300.0) == pytest.approx(4.0)
    assert table.density_pt(4.0, 300.0) == pytest.approx(2.5)


@pytest.mark.parametrize("mode", ["linear", "log_linear"])
def test_roundtrips_preserve_nodes_and_interior_on_nonuniform_grid(mode):
    table = _table(mode)
    for temperature in [270.0, 281.5, 293.0, 319.0, 340.0]:
        for density in [0.2, 0.33, 0.9, 2.1, 3.7, 7.0, 11.0]:
            pressure = table.pressure_rho_t(density, temperature)
            assert table.density_pt(pressure, temperature) == pytest.approx(density, rel=2e-14)
        for pressure in np.geomspace(
                table.pressure_rho_t(0.2, temperature),
                table.pressure_rho_t(11.0, temperature), 17):
            density = table.density_pt(float(pressure), temperature)
            assert table.pressure_rho_t(density, temperature) == pytest.approx(pressure, rel=2e-14)


@pytest.mark.parametrize("mode", ["linear", "log_linear"])
def test_inverse_keeps_pressure_and_temperature_envelope_guards(mode):
    table = _table(mode)
    for temperature in [270.0, 281.5, 340.0]:
        low = table.pressure_rho_t(0.2, temperature)
        high = table.pressure_rho_t(11.0, temperature)
        for pressure in [low * 0.99, high * 1.01]:
            with pytest.raises(ValueError, match="envelope"):
                table.density_pt(pressure, temperature)
    for temperature in [269.0, 341.0]:
        with pytest.raises(ValueError, match="envelope"):
            table.density_pt(50.0, temperature)


@pytest.mark.parametrize("with_receipt", [False, True])
def test_v1_artifact_does_not_carry_old_qualification_into_v2(tmp_path, monkeypatch, with_receipt):
    from h2physics.thermo.isothermal_eos_artifact import (
        load_isothermal_eos_table,
        save_isothermal_eos_table,
    )
    from h2physics.thermo.isothermal_eos_table import IsothermalEOSTableQualification

    table = _table("log_linear")
    current_identity = table.identity
    legacy_identity = current_identity.replace("isothermal-eos-table-v2:", "isothermal-eos-table-v1:", 1)
    artifact = tmp_path / "historical-v1.npz"
    # Emulate the previously released identity when writing this authored
    # persistence fixture. These numbers are fixture metadata, not measured errors.
    with monkeypatch.context() as patch:
        patch.setattr(IsothermalEOSTable, "identity", property(lambda self: legacy_identity))
        receipt = IsothermalEOSTableQualification(
            source_eos_identity=table.source_eos_identity, table_identity=legacy_identity,
            table_sha256=table.table_sha256, validation_point_count=8, seed=1,
            interpolation=table.interpolation, maximum_relative_pressure_error=0.001,
            maximum_relative_density_error=0.001, maximum_relative_sound_speed_error=0.001,
            maximum_relative_error_allowed=0.01, reference_seconds_per_query=0.001,
            table_seconds_per_query=0.002,
        ) if with_receipt else None
        save_isothermal_eos_table(table, artifact, qualification=receipt)
    if with_receipt:
        with pytest.raises(ValueError, match="Historical qualification receipt"):
            load_isothermal_eos_table(artifact)
    else:
        restored, receipt = load_isothermal_eos_table(artifact)
        assert receipt is None
        assert restored.identity == current_identity
        assert restored.table_sha256 == table.table_sha256
        pressure = restored.pressure_rho_t(2.1, 281.5)
        assert restored.density_pt(pressure, 281.5) == pytest.approx(2.1, rel=2e-14)
