"""Native density and conserved-layer checks; no measured-data qualification."""

import pytest

from h2physics.buoyant_layer import (
    CoolPropHydrogenAirProperties,
    TwoVentHydrogenLayerConfig,
    _layer_composition,
    run_two_vent_hydrogen_layer,
)


def _config():
    return TwoVentHydrogenLayerConfig(
        3., 36., .2, 1., 1., .65, .65, 101325., 293.15, 1., .1,
    )


def test_density_and_stock_use_native_composition():
    cp = pytest.importorskip("CoolProp.CoolProp")
    properties = CoolPropHydrogenAirProperties()
    native = cp.AbstractState("HEOS", "Hydrogen&Nitrogen&Oxygen&Argon")
    for x in (.01, .1, .8):
        native.set_mole_fractions([x, *((1.-x)*a for a in properties.dry_air_mole_fractions)])
        native.update(cp.PT_INPUTS, 101325., 293.15)
        rho = properties.density_ptx(101325., 293.15, x)
        assert rho == pytest.approx(native.rhomass(), rel=1.e-13)
        mass = rho*properties.mass_fraction(x)*1.7
        actual_x, actual_y = _layer_composition(1.7, mass, 101325., 293.15, properties)
        assert actual_x == pytest.approx(x, rel=1.e-10)
        assert actual_y == pytest.approx(properties.mass_fraction(x), rel=1.e-10)


def test_short_layer_conserves_hydrogen_with_native_density():
    pytest.importorskip("CoolProp")
    properties = CoolPropHydrogenAirProperties()
    trace = run_two_vent_hydrogen_layer(
        _config(), hydrogen_mass_flow_kg_s=1.e-5,
        duration_s=.05, maximum_step_s=.05, properties=properties,
    )
    assert trace.property_backend_id == properties.identity
    assert trace.dry_air_mole_fractions == properties.dry_air_mole_fractions
    from h2physics.adapters.layer_oxygen_projection import project_layer_oxygen

    projection = project_layer_oxygen(
        trace, carrier_basis="fixed_dry_air",
        carrier_oxygen_mole_fraction=trace.dry_air_mole_fractions[1],
    )
    assert projection.require_current() is projection
    assert projection.carrier_dry_air_mole_fractions == trace.dry_air_mole_fractions
    with pytest.raises(ValueError, match="differs from the native layer carrier"):
        project_layer_oxygen(trace, carrier_basis="fixed_dry_air",
                             carrier_oxygen_mole_fraction=.2095)
    object.__setattr__(trace, "dry_air_mole_fractions", (.78, .21, .01))
    with pytest.raises(ValueError, match="differs from the native layer carrier"):
        projection.require_current()
    object.__setattr__(trace, "dry_air_mole_fractions", properties.dry_air_mole_fractions)
    oxygen = properties.dry_air_mole_fractions[1]
    object.__setattr__(trace, "dry_air_mole_fractions", (.77, oxygen, 1.-.77-oxygen))
    with pytest.raises(ValueError, match="carrier composition changed"):
        projection.require_current()
    object.__setattr__(trace, "dry_air_mole_fractions", properties.dry_air_mole_fractions)
    assert max(abs(r) for r in trace.hydrogen_mass_residual_kg) < 1.e-12
    assert max(abs(r) for r in trace.vent_mass_continuity_residual_kg_s) < 1.e-9
    for pressure, x, rho in zip(trace.compartment_overpressure_pa,
                               trace.upper_h2_mole_fraction,
                               trace.upper_layer_density_kg_m3, strict=True):
        assert rho == pytest.approx(properties.density_ptx(101325.+pressure, 293.15, x),
                                   rel=1.e-12)


def test_phase_composition_and_configuration_guards():
    pytest.importorskip("CoolProp")
    with pytest.raises(ValueError, match="normalized"):
        CoolPropHydrogenAirProperties(dry_air_mole_fractions=(.7, .2, .01))
    properties = CoolPropHydrogenAirProperties()
    with pytest.raises(ValueError, match="native gas"):
        properties.density_ptx(1.e6, 20., 1.)
    with pytest.raises(AttributeError, match="immutable"):
        properties._fractions = (.8, .19, .01)
    with pytest.raises(ValueError, match="range"):
        _layer_composition(1., 1., 101325., 293.15, properties)


def test_native_failure_propagates_without_ideal_fallback(monkeypatch):
    import h2physics.buoyant_layer as layer

    def unavailable():
        raise ImportError("authored missing native dependency")

    monkeypatch.setattr(layer, "CoolPropHydrogenAirProperties", unavailable)
    with pytest.raises(ImportError, match="missing native dependency"):
        run_two_vent_hydrogen_layer(
            _config(), hydrogen_mass_flow_kg_s=1.e-5,
            duration_s=.05, maximum_step_s=.05,
        )
