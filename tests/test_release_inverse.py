"""Round trips reuse the independently verified nozzle; no second flow kernel."""

import pytest

from h2physics.core import Origin
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.release_inverse import infer_nozzle_stagnation_pressure


@pytest.fixture
def properties():
    pytest.importorskip("CoolProp")
    from h2physics.thermo import CoolPropProperties
    return CoolPropProperties("Hydrogen")


@pytest.mark.parametrize("pressure", [110_000., 200_000., 2e6, 12e6])
def test_measured_flow_conditioning_recovers_the_declared_equivalent_inlet(properties, pressure):
    opening = NozzleOpening.circular("test", .004, effective_area_factor=1., area_basis_id="test-nominal-area")
    forward = HomogeneousIsentropicNozzle(properties).solve(properties.state_pt(pressure, 290.),
        back_pressure_pa=100_000., opening=opening)
    inferred = infer_nozzle_stagnation_pressure(properties,
        observed_mass_flow_kg_s=forward.mass_flow_kg_s, stagnation_temperature_k=290.,
        temperature_basis_id="authored test temperature", evidence_id="authored flow target",
        back_pressure_pa=100_000., opening=opening, pressure_bounds_pa=(100_000., 15e6))
    assert inferred.equivalent_stagnation_pressure_pa == pytest.approx(pressure, rel=1e-7)
    assert abs(inferred.relative_mass_error) < 1e-7
    assert inferred.origin == Origin.RECONSTRUCTED
    assert inferred.forward_evaluations >= 17
    assert all(b > a for a, b in zip(inferred.sampled_mass_flow_kg_s,
                                    inferred.sampled_mass_flow_kg_s[1:]))


@pytest.mark.parametrize("fault", ["zero", "outside", "bounds", "temperature_basis", "liquid"])
def test_unsupported_inverse_conditions_are_rejected(properties, fault):
    options = dict(observed_mass_flow_kg_s=.001, stagnation_temperature_k=290.,
        temperature_basis_id="test T0", evidence_id="test target", back_pressure_pa=100_000.,
        opening=NozzleOpening.circular("test", .001, effective_area_factor=1., area_basis_id="test-area"),
        pressure_bounds_pa=(100_000., 200_000.))
    if fault == "zero":
        options["observed_mass_flow_kg_s"] = 0.
    elif fault == "outside":
        options["observed_mass_flow_kg_s"] = 1000.
    elif fault == "bounds":
        options["pressure_bounds_pa"] = (90_000., 200_000.)
    elif fault == "temperature_basis":
        options["temperature_basis_id"] = ""
    else:
        options["stagnation_temperature_k"] = 20.
    with pytest.raises(ValueError):
        infer_nozzle_stagnation_pressure(properties, **options)
