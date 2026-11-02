"""Boundary rejection and flux accounting; fake objects do not validate DEGALI."""

import math
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from h2physics.adapters.degali import (
    SHARED_AREA,
    JetCouplingError,
    JetPlane,
    axisymmetric_boundary,
    expand_nozzle_gas,
    hydrogen_energy_gauge_type,
    profile_integrated_buoyancy_type,
    run_axisymmetric_jet,
)
from h2physics.core import Origin
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation


@pytest.fixture
def declared():
    pytest.importorskip("CoolProp")
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    nozzle = HomogeneousIsentropicNozzle(properties).solve(
        properties.state_pt(2e6, 300.), back_pressure_pa=101325.,
        opening=NozzleOpening.circular("test", .002, effective_area_factor=.8,
                                      area_basis_id="test-effective-stream-pressure-area"))
    location = SourceLocation("test-plane", "test-clock", "test-frame", (0., 0., 2.), (1., 0., 0.))
    calls = []

    def expander(**kwargs):
        # Structural test double only: an energy/momentum-consistent receiving state.
        calls.append(kwargs)
        velocity = nozzle.effective_area_thrust_n/nozzle.mass_flow_kg_s
        state = properties.state_ph(101325., nozzle.upstream_stagnation.enthalpy_j_kg-.5*velocity**2)
        return SimpleNamespace(velocity=velocity, enthalpy=state.enthalpy_j_kg,
            density=state.density_kg_m3, temperature=state.temperature_k,
            diameter=math.sqrt(4*nozzle.mass_flow_kg_s/(math.pi*state.density_kg_m3*velocity)),
            mass_flow=nozzle.mass_flow_kg_s, momentum_flux=nozzle.effective_area_thrust_n,
            total_specific_energy=nozzle.upstream_stagnation.enthalpy_j_kg)

    options = dict(expander=expander, location=location, location_basis_id="authored-position",
                   pressure_area_policy=SHARED_AREA)
    return properties, nozzle, options, calls


def make_boundary(declared):
    properties, nozzle, options, _ = declared
    plane = expand_nozzle_gas(nozzle, properties, **options)
    section = JetPlane("test-frame", (0., 0., 0.), (1., 0., 0.), (0., 0., 1.))

    def source_factory(**kwargs):
        return SimpleNamespace(**kwargs, mass_flow=plane.mass_flow_kg_s)

    boundary = axisymmetric_boundary(plane, properties, section=section,
        ambient_temperature_k=293.15, source_factory=source_factory,
        enthalpy_factory=SimpleNamespace)
    return boundary


def test_effective_area_and_predicted_reference_ledger(declared):
    properties, nozzle, options, calls = declared
    boundary = make_boundary(declared)
    assert calls[0]["throat_diameter"] == pytest.approx(math.sqrt(4*nozzle.effective_area_m2/math.pi))
    assert calls[0]["throat_diameter"] != pytest.approx(.002)
    assert boundary.gas_plane.origin == Origin.PREDICTED
    assert boundary.gas_plane.nozzle is nozzle
    ledger = boundary.native.enthalpy_boundary
    assert ledger.specific_enthalpy+ledger.hydrogen_reference_enthalpy == pytest.approx(
        boundary.gas_plane.state.enthalpy_j_kg)
    assert ledger.hydrogen_species == properties.basis.fluid
    assert boundary.native.theta == 0.
    assert boundary.native.y == 2.
    assert options["location"].clock_id == "test-clock"


@pytest.mark.parametrize("fault", ["area", "position", "closed", "liquid", "reference", "mass", "energy"])
def test_gas_plane_rejects_ambiguous_or_inconsistent_input(declared, fault):
    properties, nozzle, options, _ = declared
    if fault == "area":
        options["pressure_area_policy"] = "nominal-hole-area"
    elif fault == "position":
        options["location_basis_id"] = ""
    elif fault == "closed":
        nozzle = replace(nozzle, exit_state=None, mass_flow_kg_s=0.)
    elif fault == "liquid":
        nozzle = replace(nozzle, exit_state=replace(nozzle.exit_state, vapor_mass_fraction=.5))
    elif fault == "reference":
        nozzle = replace(nozzle, exit_state=replace(nozzle.exit_state,
            basis=replace(nozzle.exit_state.basis, reference_id="other-zero")))
    elif fault == "mass":
        nozzle = replace(nozzle, mass_flow_kg_s=nozzle.mass_flow_kg_s*1.01)
    elif fault == "energy":
        nozzle = replace(nozzle, velocity_m_s=nozzle.velocity_m_s*1.01)
    with pytest.raises(ValueError):
        expand_nozzle_gas(nozzle, properties, **options)


def test_native_wrong_density_is_not_accepted_by_its_own_residual(declared):
    properties, nozzle, options, _ = declared
    original = options["expander"]

    def changed(**kwargs):
        result = original(**kwargs)
        result.density *= 1.01
        result.relative_mass_residual = 0.
        return result

    options["expander"] = changed
    with pytest.raises(ValueError, match="PH density"):
        expand_nozzle_gas(nozzle, properties, **options)


def test_small_flow_does_not_bypass_relative_continuity_gate(declared):
    properties, nozzle, options, calls = declared
    nozzle = replace(nozzle, effective_area_m2=nozzle.effective_area_m2*1e-12,
                     mass_flow_kg_s=nozzle.mass_flow_kg_s*1.01e-12)
    with pytest.raises(ValueError, match="throat continuity"):
        expand_nozzle_gas(nozzle, properties, **options)
    assert not calls


def test_section_coordinates_and_out_of_plane_rejection():
    section = JetPlane("frame", (2., 3., 4.), (0., 1., 0.), (0., 0., 1.))
    source = SourceLocation("source", "clock", "frame", (2., 5., 7.), (0., 0., 1.))
    assert section.project(source) == pytest.approx((2., 3., math.pi/2))
    for wrong in (replace(source, coordinate_frame_id="other"),
                  replace(source, position_m=(3., 5., 7.)),
                  replace(source, direction_unit=(1., 0., 0.))):
        with pytest.raises(ValueError):
            section.project(wrong)
    with pytest.raises(ValueError):
        JetPlane("frame", (0., 0., 0.), (1., 0., 0.), (1., 0., 0.))


def test_body_force_changes_only_one_flux_source_and_retains_native_class():
    jacobian = np.array([[2., .1, 0., 0., 0.], [0., 3., .1, 0., 0.],
                         [0., 0., 4., .1, 0.], [0., 0., 0., 5., .1], [0., 0., 0., 0., 6.]])
    derivative = np.arange(1., 8.)

    class NativeDouble:
        ambient_coflow_velocity = 0.

        def derivatives(self, _distance, _state):
            return derivative.copy()

        def _flux_jacobian(self, _state):
            return jacobian

        def buoyancy_force(self, _state):
            return -7.

    model = profile_integrated_buoyancy_type(NativeDouble)()
    actual = model.derivatives(0., np.ones(7))
    expected_sources = jacobian@derivative[:5]
    expected_sources[2] = -7.
    assert isinstance(model, NativeDouble)
    assert jacobian@actual[:5] == pytest.approx(expected_sources)
    assert actual[5:] == pytest.approx(derivative[5:])
    assert NativeDouble().derivatives(0., None) == pytest.approx(derivative)
    model.ambient_coflow_velocity = 1.
    with pytest.raises(ValueError, match="calm"):
        model.derivatives(0., np.ones(7))
    with pytest.raises(TypeError):
        profile_integrated_buoyancy_type(object)


def fake_run(declared):
    boundary = make_boundary(declared)
    source = boundary.native
    mass, speed = source.mass_flow, source.velocity
    ideal_reference = 1e6
    model_h = boundary.gas_plane.state.enthalpy_j_kg-ideal_reference
    energy = mass*(model_h+.5*speed**2)
    arrays = dict(S=np.array([.02, .1, .2]), velocity=np.full(3, 50.),
        width=np.full(3, .001), density=np.full(3, .8), mass_fraction=np.full(3, .1),
        theta=np.zeros(3), x=np.array([.02, .1, .2]), y=np.full(3, 2.),
        temperature=np.full(3, 200.), mass_flux=np.array([mass*2, mass*3, mass*4]),
        species_flux=np.full(3, mass), momentum_flux=np.full(3, mass*speed),
        energy_flux=np.full(3, energy), radiative_heat_added=np.zeros(3))
    native = SimpleNamespace(**arrays)

    def state_at_s(distance):
        if not .02 <= distance <= .2:
            raise ValueError("outside computed range")
        return np.array([50., .001, .8, .1, 0., distance, 2.])

    native.state_at_s = state_at_s
    model = SimpleNamespace(source=source, ambient_pressure=101325., ambient_temperature=293.15,
        hydrogen_enthalpy_species="Hydrogen", ambient_coflow_velocity=0., energy_transport="total",
        establishment="entrained_mass", equilibrium_air_condensation=True,
        temperature_dependent_phase_enthalpy=True, consistent_phase_ambient=True,
        hydrogen_nonideal_volume_correction=False, thermodynamic_profile="density", radial_limit=5.,
        source_specific_enthalpy=lambda: model_h, solve=lambda **kwargs: native,
        radial_state=lambda state, radius: (.1, .8, 200.),
        establishment_residuals=dict(mass=0., species=0., momentum=0., energy=0.))
    return model, boundary, native, ideal_reference


def test_balances_and_section_observations_use_whole_mixture_basis(declared):
    model, boundary, native, reference = fake_run(declared)
    run = run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference,
                               solver_options={"maximum_distance": .2})
    assert run.native is native and run.model is model
    assert run.audit.passed and not run.validation_qualified
    table = run.radial_observations((.05, .15), iter([0., .001]), evidence_id="test-prediction")
    assert table.values.shape == (4, 5)
    assert all(origin == Origin.PREDICTED for origin in table.origins)
    assert "gas-plus-condensate" in table.variables[2].basis_id
    for distance, radius in ((.3, 0.), (.1, .01), (.1, -1.)):
        with pytest.raises(ValueError):
            run.radial_observations([distance], [radius], evidence_id="test")


@pytest.mark.parametrize("fault", ["species", "energy", "horizontal", "ground", "gauge", "uncorrected", "initialization"])
def test_failed_native_results_are_retained_without_false_qualification(declared, fault):
    model, boundary, native, reference = fake_run(declared)
    if fault == "gauge":
        reference += 10.
    elif fault == "uncorrected":
        model.thermodynamic_profile = "temperature_mass_fraction"
    else:
        if fault == "species":
            native.species_flux[-1] *= 1.001
        elif fault == "energy":
            native.energy_flux[-1] += 10.
        elif fault == "horizontal":
            native.momentum_flux[-1] *= 1.001
        elif fault == "ground":
            native.y[-1] = .001
        elif fault == "initialization":
            model.establishment_residuals = None
        with pytest.raises(JetCouplingError) as captured:
            run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference,
                                 solver_options={})
        assert captured.value.run.native is native
        assert not captured.value.run.audit.passed
        return
    with pytest.raises(ValueError):
        run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference, solver_options={})


@pytest.mark.parametrize("fault", ["shape", "nan", "missing"])
def test_invalid_completed_native_output_remains_available_without_an_audit(declared, fault):
    model, boundary, native, reference = fake_run(declared)
    if fault == "shape":
        native.S = np.array([[.02, .1, .2]])
    elif fault == "nan":
        native.energy_flux[-1] = np.nan
    else:
        del native.energy_flux
    with pytest.raises(JetCouplingError, match="Invalid native solution") as captured:
        run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference,
                             solver_options={})
    assert captured.value.native is native
    assert captured.value.run is None
    assert captured.value.model is model and captured.value.boundary is boundary


def test_flux_energy_gauge_is_an_exact_species_reference_transformation():
    original = np.array([2., 3., 4., .5, -6.])

    class NativeDouble:
        source = SimpleNamespace(mass_fraction=.25)

        def _fluxes(self, state):
            return original

        def source_specific_enthalpy(self):
            return -10.

    shifted = hydrogen_energy_gauge_type(NativeDouble, shift_j_kg_h2=20.)
    model = shifted()
    assert isinstance(model, NativeDouble)
    assert model._fluxes(None) == pytest.approx([2., 3., 4., .5, 4.])
    assert model.source_specific_enthalpy() == -5.
    assert original[4] == -6.
    with pytest.raises(ValueError, match="stacking"):
        hydrogen_energy_gauge_type(shifted, shift_j_kg_h2=1.)


def test_shifted_native_energy_is_audited_in_the_original_reference(declared):
    model, boundary, native, reference = fake_run(declared)
    original_h = model.source_specific_enthalpy()
    original_energy = native.energy_flux.copy()
    shift = 2e6
    model.h2physics_hydrogen_energy_gauge_shift_j_kg = shift
    model.source_specific_enthalpy = lambda: original_h+shift
    native.energy_flux += shift*native.species_flux
    run = run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference, solver_options={})
    assert run.audit.passed and run.audit.native_energy_gauge_shift_j_kg_h2 == shift
    assert run.physical_energy_flux_w == pytest.approx(original_energy)
    assert not run.physical_energy_flux_w.flags.writeable
    assert run.audit.source_total_energy_flux_w == pytest.approx(original_energy[0])
    native.energy_flux[-1] += 10.
    with pytest.raises(JetCouplingError, match="energy conservation"):
        run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference, solver_options={})


def test_unbounded_section_does_not_invent_a_ground_clearance(declared):
    model, boundary, native, reference = fake_run(declared)
    native.y[:] = 0.
    boundary = replace(boundary, section=replace(boundary.section, ground_vertical_coordinate_m=None))
    run = run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference, solver_options={})
    assert run.audit.passed and run.audit.minimum_ground_clearance_m is None
    assert not run.validation_qualified
