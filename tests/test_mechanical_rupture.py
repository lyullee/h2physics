import numpy as np
import pytest
from scipy.integrate import quad

from h2physics.mechanical_rupture import (
    MechanicalEnergyAllocation,
    MechanicalLoadRequest,
    SphericalAcousticPulse,
    isentropic_expansion_energy,
    mechanical_rupture_load,
)
from h2physics.pressure_loads import PressureTimeHistory
from h2physics.thermo import CoolPropProperties

pytest.importorskip("CoolProp")


def expansion(**kwargs):
    values = dict(source_id="tank-A", inventory_mass_kg=2., initial_pressure_pa=20e6,
                  initial_temperature_k=300., ambient_pressure_pa=101325.)
    values.update(kwargs)
    return isentropic_expansion_energy(CoolPropProperties("Hydrogen"), **values)


def test_expansion_matches_independent_pressure_integral_and_mass_scaling():
    result = expansion()
    properties = CoolPropProperties("Hydrogen")
    s = result.initial_state.entropy_j_kg_k
    v1 = 1/result.initial_state.density_kg_m3
    integral, _ = quad(lambda p: 1/properties.state_ps(p, s).density_kg_m3-v1,
                       result.final_state.pressure_pa, result.initial_state.pressure_pa,
                       epsrel=1e-8)
    assert result.net_mechanical_work_j == pytest.approx(2*integral, rel=2e-7)
    assert expansion(inventory_mass_kg=4).net_mechanical_work_j == pytest.approx(
        2*result.net_mechanical_work_j)
    assert result.gross_expansion_work_j > result.net_mechanical_work_j > 0
    assert abs(result.final_state.entropy_j_kg_k-s) < 1e-6


def test_liquid_initial_stock_retains_native_two_phase_endpoint():
    result = expansion(initial_pressure_pa=1e6, initial_temperature_k=28.)
    assert result.initial_state.phase == "liquid"
    assert result.final_state.phase == "two_phase"
    assert 0 < result.final_state.vapor_mass_fraction < 1
    assert result.net_mechanical_work_j > 0


def test_equal_pressure_has_zero_work_and_partition_conserves_reference():
    assert expansion(initial_pressure_pa=101325.).net_mechanical_work_j == 0
    allocation = MechanicalEnergyAllocation(expansion(), .2, .1, .15, "synthetic allocation")
    assert sum((allocation.shock_energy_j, allocation.fragment_energy_j,
                allocation.wall_energy_j, allocation.remaining_energy_j)) == pytest.approx(
                    allocation.expansion.net_mechanical_work_j)
    with pytest.raises(ValueError):
        MechanicalEnergyAllocation(expansion(), .8, .3, 0, "invalid")
    with pytest.raises(ValueError):
        expansion(initial_pressure_pa=1e4)


def test_pressure_handoff_keeps_mechanical_owner_and_event_clock():
    request = MechanicalLoadRequest(MechanicalEnergyAllocation(expansion(), .1, 0., 0.,
                                                               "test assumption"),
                                    5., "rupture-event", "panel-load")

    class MeasuredWaveform:
        def pressure_history(self, received):
            assert received is request
            return PressureTimeHistory([0., .1, .2], [0., 100., 0.],
                                       received.clock_id, received.load_id, "synthetic waveform")

    response = mechanical_rupture_load(request, MeasuredWaveform())
    assert response.pressure.signed_impulse_pa_s == pytest.approx(10.)
    with pytest.raises(ValueError):
        response.pressure.time_s.setflags(write=True)

    class WrongClock:
        def pressure_history(self, _):
            return PressureTimeHistory([0., 1.], [0., 0.], "wrong", "panel-load", "test")

    with pytest.raises(ValueError, match="clock"):
        mechanical_rupture_load(request, WrongClock())
    assert np.all(response.pressure.at([-1, 1]) == 0)


def test_weak_wave_normalization_conserves_acoustic_energy_and_inverse_distance():
    allocation = MechanicalEnergyAllocation(expansion(), 1e-5, 0., 0., "synthetic weak-wave share")
    provider = SphericalAcousticPulse(CoolPropProperties("Air"), ambient_pressure_pa=101325.,
        ambient_temperature_k=300., time_s=[0., .01, .03], dimensionless_shape=[0., 1., 0.],
        minimum_distance_m=10., maximum_pressure_to_ambient_ratio=.01,
        assumption_evidence_id="synthetic free-field pulse; not a rupture prediction")
    request = MechanicalLoadRequest(allocation, 10., "arrival clock", "weak pulse")
    response = mechanical_rupture_load(request, provider)
    p = response.pressure.differential_pressure_pa
    integral_p2 = sum(np.diff(provider.time_s)*(p[:-1]**2+p[:-1]*p[1:]+p[1:]**2)/3)
    ambient = provider.ambient_state
    energy = 4*np.pi*request.distance_m**2*integral_p2/(
        ambient.density_kg_m3*ambient.speed_of_sound_m_s)
    assert energy == pytest.approx(allocation.shock_energy_j)
    distant = mechanical_rupture_load(MechanicalLoadRequest(allocation, 20., "arrival clock",
                                                           "weak pulse"), provider)
    np.testing.assert_allclose(distant.pressure.differential_pressure_pa, .5*p)
    with pytest.raises(ValueError, match="far-field"):
        mechanical_rupture_load(MechanicalLoadRequest(allocation, 1., "clock", "pulse"), provider)
    with pytest.raises(ValueError, match="pressure gate"):
        mechanical_rupture_load(MechanicalLoadRequest(
            MechanicalEnergyAllocation(expansion(), 1., 0., 0., "too strong"),
            10., "clock", "pulse"), provider)


def test_expansion_to_waveform_to_structural_output():
    from h2physics.materials.sdof import LinearSDOF, solve_linear_sdof

    allocation = MechanicalEnergyAllocation(expansion(), 1e-5, 0., 0., "synthetic energy split")
    wave = SphericalAcousticPulse(CoolPropProperties("Air"), ambient_pressure_pa=101325.,
        ambient_temperature_k=300., time_s=[0., .01, .03], dimensionless_shape=[0., 1., 0.],
        minimum_distance_m=10., maximum_pressure_to_ambient_ratio=.01,
        assumption_evidence_id="synthetic far-field waveform")
    load = mechanical_rupture_load(MechanicalLoadRequest(allocation, 20., "arrival", "panel"), wave)
    output = solve_linear_sdof(LinearSDOF(10., 1e5, 40., 1., "synthetic generalized panel"),
                               load.pressure, np.linspace(0., .5, 51))
    assert np.max(abs(output.displacement_m)) > 0
    assert np.max(abs(output.energy_residual_j)) < 1e-8
