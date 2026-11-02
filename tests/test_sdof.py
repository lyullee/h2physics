import numpy as np
import pytest

from h2physics.materials.sdof import LinearSDOF, solve_linear_sdof
from h2physics.pressure_loads import PressureTimeHistory


def test_rectangular_load_matches_closed_form_including_free_tail():
    model = LinearSDOF(2., 800., 0., 3., "synthetic panel")
    duration = .075
    load = PressureTimeHistory([0., duration], [100., 100.], "event", "pulse", "synthetic")
    time = np.linspace(0, 1, 201)
    result = solve_linear_sdof(model, load, time)
    omega = model.natural_angular_frequency_rad_s
    expected = 300/800*(1-np.cos(omega*time))
    tail = time > duration
    expected[tail] -= 300/800*(1-np.cos(omega*(time[tail]-duration)))
    np.testing.assert_allclose(result.displacement_m, expected, atol=2e-10)
    assert np.max(np.abs(result.energy_residual_j)) < 2e-8
    assert result.input_work_j[-1] == pytest.approx(result.input_work_j[16], abs=1e-9)


def test_triangular_load_matches_ramp_superposition_with_sparse_output():
    model = LinearSDOF(10., 4000., 0., .5, "synthetic support")
    rise = .013
    load = PressureTimeHistory([0., rise, 2*rise], [0., 1e4, 0.],
                               "event", "triangular", "synthetic")
    time = np.linspace(0, .8, 17)  # Pulse is shorter than output sampling.
    result = solve_linear_sdof(model, load, time)
    omega = model.natural_angular_frequency_rad_s

    def ramp(age):
        age = np.maximum(age, 0.)
        return .5e4/rise/4000*(age-np.sin(omega*age)/omega)

    expected = ramp(time)-2*ramp(time-rise)+ramp(time-2*rise)
    np.testing.assert_allclose(result.displacement_m, expected, atol=1e-10)
    assert np.max(np.abs(result.energy_residual_j)) < 1e-7


def test_damped_free_vibration_and_energy_dissipation():
    model = LinearSDOF(1., 100., 4., 1., "oscillator")
    time = np.linspace(0, 2, 51)
    load = PressureTimeHistory([0., 2.], [0., 0.], "clock", "zero", "synthetic")
    result = solve_linear_sdof(model, load, time, initial_displacement_m=.1)
    wd = np.sqrt(100-4)
    expected = .1*np.exp(-2*time)*(np.cos(wd*time)+2/wd*np.sin(wd*time))
    np.testing.assert_allclose(result.displacement_m, expected, atol=2e-11)
    assert np.all(np.diff(result.damping_dissipation_j) >= -1e-14)
    assert np.max(np.abs(result.energy_residual_j)) < 1e-9
    with pytest.raises(ValueError):
        result.displacement_m.setflags(write=True)


def test_load_contract_rejects_wrong_axis_and_nonmonotone_time():
    with pytest.raises(ValueError):
        PressureTimeHistory([0., 0.], [0., 1.], "c", "l", "e")
    with pytest.raises(ValueError):
        PressureTimeHistory([False, 1], [0., 1.], "c", "l", "e")
    model = LinearSDOF(1., 1., 0., 1., "test")
    with pytest.raises(TypeError, match="actual-event"):
        solve_linear_sdof(model, object(), [0, 1])
    load = PressureTimeHistory([1., 2.], [0, 1], "c", "l", "e")
    with pytest.raises(ValueError):
        solve_linear_sdof(model, load, [0., 2.])
