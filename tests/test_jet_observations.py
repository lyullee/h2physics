"""Independent geometric and composition checks using authored native doubles."""

from types import SimpleNamespace

import numpy as np
import pytest

from h2physics.adapters.degali import JetPlane
from h2physics.core import Origin
from h2physics.jet_observations import observe_native_gas_jet


def declared_run():
    section = JetPlane("test-frame", (1., 2., 3.), (1., 0., 0.), (0., 0., 1.), None)
    result = SimpleNamespace(S=np.array([.1, .2, .3]), x=np.array([.1, .2, .3]), y=np.zeros(3),
        state_at_s=lambda distance: np.array([20., .01, .8, .1, 0., distance, 0.]))
    model = SimpleNamespace(ambient_absolute_humidity=0., ambient_pressure=100_000.,
        fuel_molecular_weight=.002, ambient_molecular_weight=.029, radial_limit=5.,
        radial_state=lambda state, radius: (.1*np.exp(-(radius/.1)**2), .8, 280.))
    return SimpleNamespace(native=result, model=model, boundary=SimpleNamespace(section=section),
                           audit=SimpleNamespace(passed=True))


def observe(run, points, **options):
    settings = dict(coordinate_frame_id="test-frame", coordinate_origin=Origin.MEASURED,
                    evidence_id="authored-prediction", radial_tail_policy="native_gaussian_continuation")
    settings.update(options)
    return observe_native_gas_jet(run, points, **settings)


def test_cartesian_projection_radial_symmetry_and_molar_conversion():
    run = declared_run()
    points = np.array([[1.2, 2., 3.], [1.2, 2.1, 3.], [1.2, 2., 3.1]])
    result = observe(run, points)
    table = result.observations
    assert table.column("streamline_distance")[0] == pytest.approx([.2]*3)
    assert table.column("radius")[0] == pytest.approx([0., .1, .1])
    phi, valid = table.column("h2_volume_fraction")
    expected = (.1/.002)/(.1/.002+.9/.029)
    assert phi[0] == pytest.approx(expected)
    assert phi[1] == pytest.approx(phi[2]) and np.all(valid)
    assert table.column("outside_radial_quadrature")[0] == pytest.approx([0., 1., 1.])
    assert table.origins[:3] == (Origin.MEASURED,)*3
    assert not table.values.flags.writeable and result.invalid_reasons == ("", "", "")
    points[:] = 99.
    assert table.column("x")[0][0] == 1.2


def test_radial_tail_mask_and_axial_no_extrapolation_are_explicit():
    result = observe(declared_run(), [[1.2, 2.1, 3.], [1.05, 2., 3.], [1.35, 2., 3.]],
                     radial_tail_policy="mask")
    assert not np.any(result.observations.column("h2_volume_fraction")[1])
    assert result.invalid_reasons == ("outside_native_radial_quadrature",
                                      "outside_computed_axial_window", "outside_computed_axial_window")
    assert result.observations.column("outside_radial_quadrature")[1].tolist() == [True, False, False]


def test_projection_uses_the_curved_path_instead_of_axial_coordinate_as_distance():
    run = declared_run()
    run.native.x = np.array([0., .1, .2])
    run.native.y = np.array([0., .1, .2])
    run.native.S = np.array([0., np.sqrt(.02), np.sqrt(.08)])
    result = observe(run, [[1.1, 2., 3.1]])
    assert result.observations.column("radius")[0][0] == pytest.approx(0., abs=1e-14)
    assert result.observations.column("streamline_distance")[0][0] == pytest.approx(np.sqrt(.02))


@pytest.mark.parametrize("fault", ["humidity", "pressure", "frame", "failed_run", "tail_policy"])
def test_unsupported_observation_meanings_are_rejected(fault):
    run = declared_run()
    options = {}
    if fault == "humidity":
        run.model.ambient_absolute_humidity = .01
    elif fault == "pressure":
        run.model.ambient_pressure = 300_000.
    elif fault == "frame":
        options["coordinate_frame_id"] = "another-frame"
    elif fault == "failed_run":
        run.audit.passed = False
    else:
        options["radial_tail_policy"] = "silent-zero"
    with pytest.raises(ValueError):
        observe(run, [[1.2, 2., 3.]], **options)


def test_condensing_temperature_is_not_renamed_to_a_gas_volume_fraction():
    run = declared_run()
    run.model.radial_state = lambda state, radius: (.1, 1., 100.)
    result = observe(run, [[1.2, 2., 3.]])
    assert not result.observations.column("h2_volume_fraction")[1][0]
    assert result.observations.column("whole_mixture_h2_mass_fraction")[1][0]
    assert result.invalid_reasons == ("outside_reviewed_dry_gas_temperature_envelope",)


def test_failed_conservation_is_retained_as_diagnostic_context():
    run = declared_run()
    run.audit.passed = False
    result = observe(run, [[1.2, 2., 3.]], allow_failed_run=True)
    assert dict(result.observations.context)["native_audit"] == "FAIL"
