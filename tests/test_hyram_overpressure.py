"""Actual native conditional blast checks; no fabricated jet/cloud is used."""

import importlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import scipy  # Load the host runtime before locating the optional native package.

from h2physics.adapters.hyram_overpressure import (
    BauwensCorrelationDomain,
    DetonableHydrogenEnergy,
    HyRAMBauwensOverpressure,
    OverpressureEnvironment,
    OverpressureEvent,
    OverpressureNativeError,
)
from h2physics.core import Origin


@pytest.fixture
def native(monkeypatch):
    path = Path(__file__).resolve().parents[1]/"artifacts/native_hyram_packages"
    if not (path/"hyram").is_dir():
        pytest.skip("Separately reviewed optional HyRAM6.1 is not installed")
    monkeypatch.syspath_prepend(str(path))
    return importlib.import_module("hyram.phys").Bauwens_method


def energy(mass=.01):
    return DetonableHydrogenEnergy(mass, 120e6, "authored-participating-H2-mass",
        "authored-constant-q", "H2-fuel-mass/specified-combustion-products-reference",
        "authored-not-derived-from-a-jet", Origin.SYNTHETIC)


def event(centre=(0., 0., 0.)):
    return OverpressureEvent("authored-conditional-detonation", centre, "global-xyz",
                             "authored-blast-centre", 123.4, "authored-operation-clock")


def environment(pressure=1e5):
    return OverpressureEnvironment(pressure, "authored-absolute-ambient-pressure")


def model(native, **changes):
    domain = BauwensCorrelationDomain(1., 100., 5e4, 2e5, .01, "authored-envelope-not-validation")
    return HyRAMBauwensOverpressure(native, domain=replace(domain, **changes),
                                   native_source_id="HyRAM6.1/GPL-3.0-only")


def sample(native, scaled=(1., 2., 5., 10., 100.), *, mass=.01, pressure=1e5, centre=(0., 0., 0.)):
    source, ambient, origin = energy(mass), environment(pressure), event(centre)
    length = (source.energy_j/pressure)**(1/3)
    xyz = np.array(centre)+np.c_[np.asarray(scaled)*length, np.zeros((len(scaled), 2))]
    return model(native).evaluate(source, origin, ambient, xyz, frame_id="global-xyz")


def test_actual_standalone_native_retained_with_independent_published_anchor(native):
    result = sample(native)
    assert result.native_class is native
    assert result.native_function is native.calc_scaled_overpressure_from_dist
    assert isinstance(result.native_scaled_result, np.ndarray)
    assert result.scaled_overpressure[0] == pytest.approx(.4053, abs=2e-16)
    assert result.peak_overpressure_pa[0] == pytest.approx(40530., abs=2e-10)
    assert result.ambient_plus_peak_overpressure_pa[0] == pytest.approx(140530.)
    assert result.energy.energy_j == 1.2e6
    assert np.all(np.diff(result.peak_overpressure_pa) < 0)
    assert not result.zero_energy_limit
    assert scipy.__version__  # Actual host runtime, not a mocked physical function.


def test_native_direct_multidimensional_sweep_and_pressure_scaling(native):
    for pressure in (8e4, 1e5, 1.2e5):
        result = sample(native, pressure=pressure)
        expected = native.calc_scaled_overpressure_from_dist(result.scaled_distance)
        np.testing.assert_array_equal(result.native_scaled_result, expected)
        np.testing.assert_allclose(result.peak_overpressure_pa/pressure,
                                   result.scaled_overpressure, rtol=2e-16)
        assert result.environment.ambient_pressure_pa_absolute == pressure


def test_cubic_energy_distance_similarity_uses_fuel_mass_without_reflection_multiplier(native):
    first, eight = sample(native), sample(native, mass=.08)
    np.testing.assert_allclose(eight.distance_m, 2*first.distance_m, rtol=3e-16)
    np.testing.assert_allclose(eight.peak_overpressure_pa, first.peak_overpressure_pa, rtol=2e-15)
    assert eight.energy.energy_j == 8*first.energy.energy_j


def test_higher_participating_mass_increases_pressure_at_fixed_physical_receptors(native):
    low = sample(native, scaled=(2., 4., 20.))
    high = model(native).evaluate(energy(.08), event(), environment(), low.receptors_m,
                                  frame_id="global-xyz")
    assert np.all(high.peak_overpressure_pa > low.peak_overpressure_pa)


def test_actual_native_zero_energy_limit_is_zero_without_a_mock_cloud(native):
    result = model(native).evaluate(energy(0.), event(), environment(), [(10., 0., 0.)],
                                    frame_id="global-xyz")
    assert result.zero_energy_limit and np.all(np.isposinf(result.scaled_distance))
    np.testing.assert_array_equal(result.native_scaled_result, [0.])
    np.testing.assert_array_equal(result.peak_overpressure_pa, [0.])
    np.testing.assert_array_equal(result.ambient_plus_peak_overpressure_pa, [1e5])
    with pytest.raises(ValueError, match="zero"):
        model(native).threshold_radius(1e4, energy(0.), event(), environment())


def test_translated_rotated_receptors_share_an_explicit_frame_and_snapshot(native):
    reference = sample(native, scaled=(2., 3., 5., 10., 90.))
    origin = event((20., -3., 15.))
    points = np.array(origin.centre_m)+np.c_[np.zeros((len(reference.distance_m), 2)),
                                                          -reference.distance_m]
    result = model(native).evaluate(energy(), origin, environment(), points, frame_id=origin.frame_id)
    np.testing.assert_allclose(result.peak_overpressure_pa, reference.peak_overpressure_pa, rtol=2e-15)
    assert result.event.snapshot_time_s == 123.4
    assert result.event.clock_id == "authored-operation-clock"
    with pytest.raises(ValueError, match="frame"):
        model(native).evaluate(energy(), origin, environment(), points, frame_id="another-frame")


def test_threshold_root_retains_actual_scipy_result_and_native_forward_state(native):
    method = model(native)
    first = method.threshold_radius(1e4, energy(), event(), environment())
    second = method.threshold_radius(1e4, energy(.08), event(), environment())
    assert first.native_solver_result.converged
    assert first.forward.native_class is native
    assert first.forward.peak_overpressure_pa[0] == pytest.approx(1e4, abs=1e-7)
    assert second.radius_m == pytest.approx(2*first.radius_m, rel=2e-15)
    assert first.relative_radius_tolerance == 1e-12


def test_root_refinement_and_unbracketed_threshold_are_explicit(native):
    method = model(native)
    coarse = method.threshold_radius(5000., energy(), event(), environment(),
                                    scaled_radius_tolerance=1e-8, relative_radius_tolerance=1e-8)
    fine = method.threshold_radius(5000., energy(), event(), environment(),
                                  scaled_radius_tolerance=1e-13, relative_radius_tolerance=1e-13)
    assert abs(coarse.radius_m-fine.radius_m) < 1e-7
    for target in (1e-12, 1e8):
        with pytest.raises(ValueError, match="bracketed"):
            method.threshold_radius(target, energy(), event(), environment())
    with pytest.raises(ValueError, match="SciPy"):
        method.threshold_radius(5000., energy(), event(), environment(),
                                relative_radius_tolerance=1e-20)


def test_independent_far_field_power_limit_is_mathematical_only(native):
    # Published leading exponent is -4/3. This is outside the application fixture.
    first = native.calc_scaled_overpressure_from_dist(1e9)
    second = native.calc_scaled_overpressure_from_dist(2e9)
    exponent = math.log(second/first)/math.log(2)
    assert abs(exponent+4/3) < 1e-6


def test_domain_bounds_no_native_near_origin_clamp_or_silent_far_extrapolation(native):
    method = model(native)
    length = (energy().energy_j/1e5)**(1/3)
    for scaled in (.001, .5, 100.1):
        with pytest.raises(ValueError, match="domain"):
            method.evaluate(energy(), event(), environment(), [(scaled*length, 0., 0.)],
                            frame_id="global-xyz")
    with pytest.raises(ValueError, match="0.01"):
        model(native, minimum_scaled_distance=.009)
    with pytest.raises(ValueError, match="absolute pressure"):
        sample(native, pressure=3e5)
    with pytest.raises(ValueError, match="physical domain"):
        model(native, minimum_standoff_m=10.).evaluate(energy(), event(), environment(),
                                                       [(3., 0., 0.)], frame_id="global-xyz")


def test_invalid_evidence_energy_origin_clock_and_coordinates_are_rejected(native):
    for change in ({"participating_hydrogen_mass_kg": -.1}, {"heat_of_combustion_j_kg": 0},
                   {"mass_evidence_id": ""}, {"origin": Origin.UNRESOLVED},
                   {"participating_hydrogen_mass_kg": 1e300, "heat_of_combustion_j_kg": 1e300},
                   {"participating_hydrogen_mass_kg": 1e-300, "heat_of_combustion_j_kg": 1e-300}):
        with pytest.raises(ValueError):
            replace(energy(), **change)
    for change in ({"clock_id": ""}, {"snapshot_time_s": float("nan")}, {"centre_m": (0., 0.)}):
        with pytest.raises(ValueError):
            replace(event(), **change)
    for points in ([], [1., 2., 3.], [(0., 0., 0.)], [(float("nan"), 0., 0.)]):
        with pytest.raises(ValueError):
            model(native).evaluate(energy(), event(), environment(), points, frame_id="global-xyz")


def test_results_copy_coordinates_and_expose_immutable_si_arrays(native):
    points = np.array([(10., 1., 0.)])
    result = model(native).evaluate(energy(), event(), environment(), points, frame_id="global-xyz")
    points[:] = 0
    assert result.receptors_m[0, 0] == 10.
    for name in ("receptors_m", "distance_m", "scaled_distance", "scaled_overpressure",
                 "peak_overpressure_pa", "ambient_plus_peak_overpressure_pa"):
        assert not getattr(result, name).flags.writeable


def test_native_definition_mutation_and_invalid_results_fail_with_raw_result(native, monkeypatch):
    method = model(native)
    monkeypatch.setattr(native, "calc_scaled_overpressure_from_dist", staticmethod(lambda x: x))
    with pytest.raises(OverpressureNativeError, match="changed") as error:
        method.evaluate(energy(), event(), environment(), [(10., 0., 0.)], frame_id="global-xyz")
    assert error.value.native_class is native
    # A deliberately broken native capability is a negative contract case only.
    monkeypatch.setattr(native, "calc_scaled_overpressure_from_dist",
                        staticmethod(lambda x: np.full_like(x, np.nan)))
    method = model(native)
    with pytest.raises(OverpressureNativeError, match="invalid") as error:
        method.evaluate(energy(), event(), environment(), [(10., 0., 0.)], frame_id="global-xyz")
    assert np.isnan(error.value.native_result).all()
    with pytest.raises(TypeError, match="native"):
        HyRAMBauwensOverpressure(object, domain=method.domain, native_source_id="absent")
