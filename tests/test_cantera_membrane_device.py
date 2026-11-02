"""Actual two-finite-side native integration and authored limit oracles."""

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_membrane import (
    CanteraDustyGasTransport,
    MembraneEndpoint,
    MembraneTransportEvidence,
    PorousTransportGeometry,
)
from h2physics.adapters.cantera_membrane_device import (
    CanteraFiniteMembraneDevice,
    FiniteMembraneIntegrationError,
    FiniteMembraneParameters,
    MembraneIntegrationSettings,
)
from h2physics.core import Origin

ct = pytest.importorskip("cantera")
RAW = (Path(ct.__file__).parent/"data/h2o2.yaml").read_bytes()
SPECIES = ("H2", "N2", "AR")


def factory():
    by_name = {s.name: s for s in ct.Species.list_from_yaml(RAW.decode(), "species")}
    phase = ct.Solution(thermo="ideal-gas", species=[by_name[n] for n in SPECIES],
                        transport_model="multicomponent")
    phase.TPX = 330., 101325., [.7, .2, .1]
    return phase


def setup(*, pressure=101325., area=.005, left_volume=.02, right_volume=.02):
    basis = MechanismBasis("installed-h2o2-authored-H2-N2-Ar", hashlib.sha256(RAW).hexdigest(),
        "Cantera BSD-3-Clause; GRI upstream species/transport provenance",
        ("https://cantera.org/3.2/python/transport.html",), 300., 1000., .001, 2e5)
    evidence = MembraneTransportEvidence("installed-native-transport", "frozen-warm-gas", "neutral-ideal-gas",
        "native-NASA-formation-reference", "native-H2-spin-unresolved")
    transport = CanteraDustyGasTransport(factory, basis, evidence=evidence)
    def endpoint(name, fractions):
        return MembraneEndpoint(330., pressure, SPECIES, fractions, "mole", name, evidence.gas_phase_id,
            "authored-pore", "authored-finite-initial-state", Origin.SYNTHETIC)
    left, right = endpoint("left", [.7, .2, .1]), endpoint("right", [.4, .5, .1])
    geometry = PorousTransportGeometry(.35, 2.5, 50e-9, 0., .001, "authored-pore",
                                      "authored-no-material-validation", Origin.SYNTHETIC)
    parameters = FiniteMembraneParameters(area, left_volume, right_volume, "authored-device-clock",
        100., 140., "separate-fixed-330K-thermostats", "authored-finite-device", Origin.SYNTHETIC)
    return CanteraFiniteMembraneDevice(transport), left, right, geometry, parameters


def run(*, times=(100., 101., 102.), settings=MembraneIntegrationSettings(), **kwargs):
    device, left, right, geometry, parameters = setup(**kwargs)
    return device.run(left, right, geometry, parameters, times, settings=settings)


def test_actual_both_finite_species_pressure_feedback_counterdiffusion_and_each_side_energy():
    trace = run()
    assert len(trace.native.reactors) == 2 and isinstance(trace.native.network, ct.ReactorNet)
    assert all(isinstance(r, ct.ExtensibleIdealGasReactor) for r in trace.native.reactors)
    assert trace.snapshots[0].molar_flux_mol_m2_s[0] > 0 > trace.snapshots[0].molar_flux_mol_m2_s[1]
    assert trace.snapshots[-1].sides[0].pressure_pa < 101325. < trace.snapshots[-1].sides[1].pressure_pa
    assert trace.snapshots[-1].sides[0].mole_fractions["H2"] < .7
    assert trace.snapshots[-1].sides[1].mole_fractions["H2"] > .4
    assert np.max(abs(trace.side_species_residual_kg)) < 1e-12
    assert np.max(abs(trace.combined_species_residual_kg)) < 1e-12
    assert np.max(abs(trace.side_energy_residual_j)) < 1e-7
    assert np.max(abs(trace.combined_internal_energy_residual_j)) < 1e-7
    assert trace.thermostat_heat_j[-1, 0] > 0 > trace.thermostat_heat_j[-1, 1]
    assert trace.thermostat_heat_j.sum(axis=1) == pytest.approx(0., abs=1e-8)
    assert not trace.species_transfer_kg.flags.writeable


def test_independent_short_time_derivative_verifies_native_bulk_source_kmol_s_and_gross_area():
    duration = 1e-4
    trace = run(times=(100., 100.+duration), settings=MembraneIntegrationSettings(
        maximum_time_step_s=duration/5, relative_tolerance=1e-11, absolute_tolerance=1e-18))
    observed = (trace.snapshots[-1].species_mass_kg-trace.snapshots[0].species_mass_kg)/duration
    molecular_mass = trace.native.reactors[0].phase.molecular_weights/1000.
    expected = trace.snapshots[0].molar_flux_mol_m2_s*molecular_mass*trace.parameters.area_m2
    np.testing.assert_allclose(observed, np.array([-expected, expected]), rtol=2e-5, atol=1e-12)


def test_equal_states_remain_stationary_with_zero_transport_and_thermostat():
    device, left, _, geometry, parameters = setup()
    trace = device.run(left, replace(left, boundary_id="right"), geometry, parameters, [100., 101., 103.])
    assert trace.snapshots[-1].species_mass_kg == pytest.approx(trace.snapshots[0].species_mass_kg, abs=1e-14)
    assert np.max(abs(trace.species_transfer_kg)) < 1e-20
    assert np.max(abs(trace.thermostat_heat_j)) < 1e-14


def test_reversing_finite_sides_reverses_flux_and_swaps_evolving_inventories():
    device, left, right, geometry, parameters = setup()
    forward = device.run(left, right, geometry, parameters, [100., 102.])
    reverse = device.run(right, left, geometry, parameters, [100., 102.])
    assert reverse.snapshots[0].molar_flux_mol_m2_s == pytest.approx(-forward.snapshots[0].molar_flux_mol_m2_s)
    assert reverse.snapshots[-1].species_mass_kg == pytest.approx(forward.snapshots[-1].species_mass_kg[::-1], abs=1e-11)


def test_area_time_scaling_and_maximum_step_tolerance_refinement():
    base = run(times=(100., 102.))
    doubled = run(area=.01, times=(100., 101.))
    refined = run(times=(100., 102.), settings=MembraneIntegrationSettings(
        maximum_time_step_s=.025, relative_tolerance=2e-11, absolute_tolerance=1e-17))
    assert doubled.snapshots[-1].species_mass_kg == pytest.approx(base.snapshots[-1].species_mass_kg, abs=1e-11)
    assert refined.snapshots[-1].species_mass_kg == pytest.approx(base.snapshots[-1].species_mass_kg, abs=1e-11)


def test_low_pressure_finite_knudsen_exponential_oracle_uses_real_native_transport():
    trace = run(pressure=.01, times=(100., 110., 120.), settings=MembraneIntegrationSettings(
        maximum_time_step_s=.2, relative_tolerance=1e-10, absolute_tolerance=1e-22,
        minimum_side_inventory_kg=(1e-18, 1e-18), energy_ledger_scale_j=1e-3))
    mass = trace.native.reactors[0].phase.molecular_weights/1000.
    initial_mol = trace.snapshots[0].species_mass_kg/mass
    p, g = trace.parameters, trace.geometry
    d = 2/3*g.mean_pore_radius_m*g.porosity/g.tortuosity*np.sqrt(8*(ct.gas_constant/1000)*330/(np.pi*mass))
    rate = p.area_m2*d/g.thickness_m*(1/p.left_volume_m3+1/p.right_volume_m3)
    asymptote = initial_mol.sum(axis=0)*p.left_volume_m3/(p.left_volume_m3+p.right_volume_m3)
    oracle = asymptote+(initial_mol[0]-asymptote)*np.exp(-rate*20.)
    actual = trace.snapshots[-1].species_mass_kg[0]/mass
    assert actual == pytest.approx(oracle, rel=2e-7, abs=1e-15)


def test_native_trial_extension_is_recorded_without_host_normalization():
    trace = run()
    assert 1e-10 < trace.maximum_native_trial_sum_deviation < trace.settings.trial_sum_deviation_budget
    assert trace.maximum_accepted_sum_deviation < 1e-12
    assert trace.maximum_native_trial_temperature_deviation_k > 0
    assert trace.maximum_native_trial_relative_volume_deviation > 0
    with pytest.raises(FiniteMembraneIntegrationError) as caught:
        run(settings=MembraneIntegrationSettings(trial_sum_deviation_budget=1e-16))
    assert caught.value.native.connection.first_error is not None
    assert caught.value.triggering_time_s is not None


def test_inventory_limit_failure_retains_actual_native_states_and_accepted_prefix():
    device, left, right, geometry, parameters = setup()
    native_right = factory()
    native_right.TPX = right.temperature_k, right.pressure_pa_absolute, right.fractions
    minimum = native_right.density_mass*parameters.right_volume_m3*.9999
    with pytest.raises(FiniteMembraneIntegrationError) as caught:
        device.run(left, right, geometry, parameters, [100., 100.001, 102.],
            settings=MembraneIntegrationSettings(maximum_time_step_s=.02,
                                                minimum_side_inventory_kg=(1e-12, minimum)))
    failure = caught.value
    assert len(failure.snapshots) >= 2
    assert failure.last_accepted_time_s == 100.001
    assert failure.triggering_time_s > failure.last_accepted_time_s
    assert len(failure.native_states) == 2 and not failure.native_states[0].flags.writeable
    assert failure.native.connection.first_error is not None
    assert failure.__cause__ is not None


def test_post_run_audit_failure_preserves_completed_trace_and_real_integrator():
    with pytest.raises(FiniteMembraneIntegrationError) as caught:
        run(settings=MembraneIntegrationSettings(species_audit_absolute_kg=1e-30,
            energy_audit_absolute_j=1e-30, audit_relative=1e-30))
    assert caught.value.trace is not None
    assert len(caught.value.snapshots) == 3
    assert caught.value.native is caught.value.trace.native


def test_private_native_pore_reset_and_source_transport_definition_guard():
    trace = run()
    connection = trace.native.connection
    connection.kernel.permeability = 1e-8
    connection.kernel.mean_pore_radius = 1e-4
    rate = connection.rates(102.001)
    assert rate/trace.parameters.area_m2*1000. == pytest.approx(trace.snapshots[-1].molar_flux_mol_m2_s)
    source = trace.native.initial_transport_result.source_phase
    source.set_binary_diff_coeffs_polynomial(0, 1, source.get_binary_diff_coeffs_polynomial(0, 1)*1.01)
    with pytest.raises(ValueError, match="source state/definition"):
        connection.rates(102.002)
    assert connection.first_error is not None and len(connection.first_error_native_states) == 2


@pytest.mark.parametrize("change", [dict(area_m2=0.), dict(left_volume_m3=-1.), dict(right_volume_m3=True),
    dict(clock_id=""), dict(origin=Origin.UNRESOLVED), dict(support_end_s=100.)])
def test_invalid_device_geometry_clock_and_role_are_rejected(change):
    *_, parameters = setup()
    with pytest.raises(ValueError):
        replace(parameters, **change)


def test_clock_support_and_nonisothermal_endpoints_are_rejected_before_integration():
    device, left, right, geometry, parameters = setup()
    for times in ([99., 100.], [100., 140.], [100., 100.], [100., float("nan")]):
        with pytest.raises(ValueError):
            device.run(left, right, geometry, parameters, times)
    with pytest.raises(ValueError, match="isothermal"):
        device.run(left, replace(right, temperature_k=331.), geometry, parameters, [100., 101.])
