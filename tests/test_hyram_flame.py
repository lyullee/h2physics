"""Actual-native Flame evidence; known mass/caloric failures are expected failures of gates."""

import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest

from h2physics.adapters.hyram_flame import (
    FlameAuditPolicy,
    HyRAMFlameAdmissibilityError,
    SteadyFlameWindow,
    fuel_origin_section_flows,
    run_hyram_flame,
)
from h2physics.core import Origin
from h2physics.release import NozzleOpening, SourceLocation
from h2physics.thermo.coolprop import CoolPropProperties


@pytest.fixture(scope="module")
def native_arguments():
    pytest.importorskip("hyram", reason="HyRAM+ is a separately installed optional engine")
    from hyram.phys import Flame, Fluid, Orifice
    from hyram.phys._flame import calc_transmissivity

    return dict(fluid_factory=Fluid, orifice_factory=Orifice, flame_factory=Flame,
        transmissivity_function=calc_transmissivity,
        upstream=CoolPropProperties("Hydrogen").state_pt(2e6, 300.),
        ambient=CoolPropProperties("Air").state_pt(101325., 293.15),
        opening=NozzleOpening.circular("authored-2mm", .002, effective_area_factor=.8,
                                      area_basis_id="native-Cd-times-geometric-area"),
        location=SourceLocation("authored-steady-flame", "authored", "global-xz",
                                (0., 2., 2.), (1., 0., 0.)),
        window=SteadyFlameWindow("authored-absolute-clock", 10., 20., "authored-source",
                                "fixed-reservoir-premise", Origin.SYNTHETIC),
        solver_options={"Smax": 20., "tol": 1e-6, "n_pts_integral": 100})


@pytest.fixture(scope="module")
def native_run(native_arguments):
    return run_hyram_flame(**native_arguments, require_accepted=False)


def test_optional_module_import_does_not_import_hyram():
    result = subprocess.run([sys.executable, "-c",
        "import sys; import h2physics.adapters.hyram_flame; assert 'hyram' not in sys.modules"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_actual_full_flame_exposes_mass_and_energy_defects_without_repair(native_run):
    from hyram.phys import Flame

    assert isinstance(native_run.native, Flame)
    assert not native_run.accepted
    assert native_run.gates["finite positive full-visible native flame"]
    assert native_run.gates["native source expansion mass"]
    assert native_run.gates["native throat and expansion stagnation energy"]
    assert native_run.gates["independent section quadrature"]
    assert native_run.gates["emitted radiation within native chemical-power budget"]
    assert not native_run.gates["source to conserved fuel-origin field mass"]
    assert not native_run.gates["conserved fuel-origin transport along flame"]
    assert not native_run.gates["direct EOS check of native combustion caloric equation"]
    assert native_run.fuel_origin_flows_kg_s[0]/native_run.mass_flow_kg_s < .6
    assert native_run.maximum_transport_mass_residual_kg_s/native_run.mass_flow_kg_s > .05
    assert abs(native_run.throat_energy_residual_w) < .01
    assert abs(native_run.expansion_energy_residual_w) < .01
    assert not native_run.centreline.flags.writeable
    assert not native_run.fuel_origin_flows_kg_s.flags.writeable


def test_default_api_rejects_actual_native_defects_and_retains_result(native_arguments):
    with pytest.raises(HyRAMFlameAdmissibilityError) as caught:
        run_hyram_flame(**native_arguments)
    assert caught.value.native is caught.value.result.native
    assert caught.value.result.mass_flow_kg_s > 0
    assert not caught.value.result.accepted


def test_f_is_conserved_fuel_origin_including_water_not_unburned_h2(native_run):
    chemistry = native_run.native.chem
    fractions = np.array([.005, chemistry.fstoich, .1, .4, .8])
    products = chemistry._Yprod(fractions)
    equivalent = products[chemistry.reac]+products["H2O"]*chemistry.MW[chemistry.reac]/chemistry.MW["H2O"]
    assert equivalent == pytest.approx(fractions, abs=5e-8)
    assert products[chemistry.reac][0] == pytest.approx(0., abs=1e-15)
    assert native_run.combustion_caloric_audit[:, 0] == pytest.approx(fractions)
    assert np.max(abs(native_run.combustion_caloric_audit[:, 6])) > 1e4


def test_independent_section_quadrature_order_and_tail_refinement(native_run):
    refined = fuel_origin_section_flows(native_run.native, radial_cutoff_widths=10.,
                                        quadrature_order=24, radial_panels=48)
    assert refined == pytest.approx(native_run.fuel_origin_flows_kg_s, abs=1e-12)
    assert native_run.maximum_section_quadrature_difference_kg_s < 1e-12


def test_native_ode_refinement_does_not_remove_entry_defect(native_arguments, native_run):
    fine = run_hyram_flame(**{**native_arguments,
        "solver_options": {"Smax": 20., "tol": 1e-8, "n_pts_integral": 600}},
        require_accepted=False)
    assert fine.fuel_origin_flows_kg_s[0] == pytest.approx(native_run.fuel_origin_flows_kg_s[0], abs=1e-14)
    assert fine.maximum_source_mass_residual_kg_s/fine.mass_flow_kg_s > .4
    assert fine.maximum_transport_mass_residual_kg_s/fine.mass_flow_kg_s > .05
    assert abs(fine.fuel_origin_flows_kg_s[-1]-native_run.fuel_origin_flows_kg_s[-1]) < 1e-5
    assert fine.native.S[-1] == pytest.approx(fine.native.Lvis)


def test_native_radiation_stays_diagnostic_even_when_kernel_budget_passes(native_run):
    with pytest.raises(HyRAMFlameAdmissibilityError):
        native_run.irradiance([[0, 5, 2]], relative_humidity=.5, minimum_source_distance_m=.1)
    result = native_run.irradiance([[0, 5, 2], [1, 5, 2], [1, -1, 2]],
        relative_humidity=.5, minimum_source_distance_m=.1, allow_rejected_flame=True)
    assert result.kernel_accepted
    assert not result.accepted
    assert result.status == "diagnostic-unaccepted-flame"
    assert result.irradiance_w_m2[1] == pytest.approx(result.irradiance_w_m2[2], rel=1e-13)
    direct = native_run.native.Qrad_multi(np.array([0, 1, 1]), np.array([2, 2, 2]),
                                         np.array([3, 3, -3]), .5)
    assert result.irradiance_w_m2 == pytest.approx(direct)
    assert np.all(result.irradiance_w_m2 >= result.minimum_flux_bound_w_m2)
    assert np.all(result.irradiance_w_m2 <= result.maximum_flux_bound_w_m2)


def test_actual_radiation_far_field_power_limit_and_source_count_refinement(native_run):
    native = native_run.native
    centre = np.array([(native.x.min()+native.x.max())/2, 2., (native.y.min()+native.y.max())/2])
    radius = 100*native.Lvis
    point = centre+np.array([0., radius, 0.])
    results = [native_run.irradiance([point], relative_humidity=.5, minimum_source_distance_m=.1,
        number_of_sources=count, allow_rejected_flame=True) for count in (25, 50, 100)]
    transmission = native_run.transmissivity_function(radius, native.ambient.T, .5)
    expected = native_run.emitted_radiative_power_w*transmission/(4*np.pi*radius**2)
    assert results[-1].irradiance_w_m2[0] == pytest.approx(expected, rel=1e-4)
    assert abs(results[-1].irradiance_w_m2[0]-results[-2].irradiance_w_m2[0])/expected < 1e-6


def test_actual_global_translation_preserves_radiation(native_arguments, native_run):
    delta = np.array([11., -7., 4.])
    shifted = run_hyram_flame(**{**native_arguments,
        "location": replace(native_arguments["location"], position_m=tuple(np.array([0, 2, 2])+delta))},
        require_accepted=False)
    points = np.array([[0., 5., 2.], [1., 5., 2.]])
    a = native_run.irradiance(points, relative_humidity=.5, minimum_source_distance_m=.1,
                              allow_rejected_flame=True)
    b = shifted.irradiance(points+delta, relative_humidity=.5, minimum_source_distance_m=.1,
                           allow_rejected_flame=True)
    assert a.irradiance_w_m2 == pytest.approx(b.irradiance_w_m2, rel=1e-5)


@pytest.mark.parametrize("changes", [
    {"upstream": "wrong_spin"}, {"upstream": "wrong_reference"},
    {"upstream": "no_pressure_head"}, {"location": "out_of_plane"},
    {"solver_options": {"Smax": 20., "mdot": .1}},
    {"solver_options": {"Smax": 20., "developing_flow": object()}},
    {"solver_options": {"Smax": 20., "wind_speed": 1.}},
    {"solver_options": {"Smax": float("inf")}},
    {"window": None},
])
def test_source_basis_geometry_and_solver_ownership_guards(native_arguments, changes):
    args = dict(native_arguments)
    if changes.get("upstream") == "wrong_spin":
        changes = {"upstream": replace(args["upstream"],
                    basis=replace(args["upstream"].basis, spin_composition="para"))}
    elif changes.get("upstream") == "wrong_reference":
        changes = {"upstream": replace(args["upstream"], enthalpy_j_kg=args["upstream"].enthalpy_j_kg+1e5)}
    elif changes.get("upstream") == "no_pressure_head":
        changes = {"upstream": CoolPropProperties("Hydrogen").state_pt(101325., 300.)}
    elif changes.get("location") == "out_of_plane":
        changes = {"location": replace(args["location"], direction_unit=(0., 1., 0.))}
    args.update(changes)
    with pytest.raises(ValueError):
        run_hyram_flame(**args)


@pytest.mark.parametrize("settings", [
    {"relative_humidity": 0., "minimum_source_distance_m": .1},
    {"relative_humidity": 1.1, "minimum_source_distance_m": .1},
    {"relative_humidity": .5, "minimum_source_distance_m": .1, "number_of_sources": 2},
    {"relative_humidity": .5, "minimum_source_distance_m": .1, "waist_fraction": 1.},
])
def test_radiation_domain_guards(native_run, settings):
    with pytest.raises(ValueError):
        native_run.irradiance([[0., 5., 2.]], allow_rejected_flame=True, **settings)


def test_radiation_singularity_and_unphysical_transmission_are_not_clipped(native_run):
    source_point = [native_run.native.x[0], 2., native_run.native.y[0]]
    with pytest.raises(ValueError, match="excluded"):
        native_run.irradiance([source_point], relative_humidity=.5,
                              minimum_source_distance_m=.1, allow_rejected_flame=True)
    # Native Wayne log correlation leaves [0,1] on this nearly dry short path.
    with pytest.raises(ValueError, match="transmission"):
        native_run.irradiance([[0., 2.01, 2.]], relative_humidity=1e-10,
                              minimum_source_distance_m=.001, allow_rejected_flame=True)


def test_clock_and_audit_numerics_are_explicit():
    with pytest.raises(ValueError):
        SteadyFlameWindow("", 1., 2., "source", "steady", Origin.SYNTHETIC)
    with pytest.raises(ValueError):
        SteadyFlameWindow("clock", 2., 1., "source", "steady", Origin.SYNTHETIC)
    with pytest.raises(ValueError):
        SteadyFlameWindow("clock", 1., 2., "source", "steady", Origin.UNRESOLVED)
    with pytest.raises(ValueError):
        FlameAuditPolicy(radial_panels=2)
