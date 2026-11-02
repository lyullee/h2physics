"""Authored balance/numerical references; synthetic parameters are not PAR data."""

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import CanteraGas, MechanismBasis, ReactiveState
from h2physics.adapters.par_device import PARCapacityLaw, PARDevice, PARDeviceParameters

ct = pytest.importorskip("cantera")


def backend():
    raw = (Path(ct.__file__).parent / "data" / "h2o2.yaml").read_bytes()
    basis = MechanismBasis("Cantera:h2o2:PAR-software-reference",
        hashlib.sha256(raw).hexdigest(), "Cantera-BSD-3-Clause; upstream-mechanism-provenance",
        ("https://cantera.org/3.2/examples/input/h2o2.html",), 250., 3000., 1e4, 1e6)
    return CanteraGas.from_yaml(raw, basis, phase_name="ohmech")


def inlet(h2=.04, o2=.2):
    return ReactiveState(300., 101325., {"H2": h2, "O2": o2, "N2": 1-h2-o2})


def parameters(**changes):
    base = PARDeviceParameters("synthetic:software-reference-only", .5, .001, 4.,
        100., 1., .2, .02, .5, .8, .1, .0001)
    return replace(base, **changes)


def capacity(rate=1e-4, **changes):
    base = PARCapacityLaw("synthetic:constant-capacity-not-measured",
        lambda condition: rate, (250., 1500.), (250., 500.), (1e4, 1e6),
        (0., 1.), (0., 1.), .1)
    return replace(base, **changes)


def device(rate=1e-4, **changes):
    return PARDevice(backend(), parameters(**changes), capacity(rate))


def test_native_device_closes_species_mass_and_combined_energy():
    model = device()
    result = model.evaluate(inlet(), 400.)
    assert result.native_version == ct.__version__
    assert result.inlet_mass_flow_kg_s > model.parameters.background_mass_flow_kg_s
    assert result.outlet.temperature_k > result.inlet.temperature_k
    assert result.buoyancy_pressure_pa > 0
    assert result.hydrogen_removed_mol_s == pytest.approx(1e-4)
    before, after = result.inlet_species_mol_s, result.outlet_species_mol_s
    removed = before["H2"]-after["H2"]
    assert removed == pytest.approx(result.hydrogen_removed_mol_s)
    assert before["O2"]-after["O2"] == pytest.approx(.5*removed)
    assert after["H2O"]-before["H2O"] == pytest.approx(removed)
    assert after["N2"] == before["N2"]
    assert abs(result.mass_residual_kg_s) < 1e-15
    assert abs(result.energy_residual_w) < 1e-6
    assert result.entropy_generation_w_k >= 0
    assert abs(result.momentum_residual_kg_s) < 1e-11
    # Independent native enthalpy evaluation at the returned composition/state.
    native = model.gas.create_phase(result.outlet).native_phase
    assert result.outlet_enthalpy_flow_w == pytest.approx(
        result.outlet_mass_flow_kg_s*native.enthalpy_mass, abs=1e-7)
    with pytest.raises(TypeError):
        result.outlet_species_mol_s["H2"] = 1.


@pytest.mark.parametrize("h2,o2", [(0., .2), (.04, 0.), (.8, .001), (.001, .2)])
def test_feed_limitation_does_not_create_reactants(h2, o2):
    result = device(rate=1e3).evaluate(inlet(h2, o2), 400.)
    assert all(value >= 0 for value in result.outlet_species_mol_s.values())
    assert result.hydrogen_removed_mol_s == pytest.approx(min(
        result.inlet_species_mol_s["H2"], 2*result.inlet_species_mol_s["O2"]))
    assert abs(result.energy_residual_w) < 1e-5


def test_no_exchange_cold_state_does_not_invent_startup():
    result = device(background_mass_flow_kg_s=0.).evaluate(inlet(), 300.)
    assert result.flow_status == "not_started_no_background_exchange"
    assert result.inlet_mass_flow_kg_s == 0.
    assert result.hydrogen_removed_mol_s == 0.
    assert result.reaction_heat_w == 0.
    assert result.outlet.temperature_k == 300.


def test_hot_catalyst_can_drive_natural_flow_without_background():
    model = device(background_mass_flow_kg_s=0.)
    hot = model.evaluate(inlet(), 400.)
    assert hot.inlet_mass_flow_kg_s > 0
    assert hot.flow_status == "hot_catalyst_buoyancy"
    assert hot.buoyancy_pressure_pa > 0
    assert abs(hot.momentum_residual_kg_s) < 1e-11


def test_thermal_transient_matches_independent_exponential_cooling_and_energy():
    model = device(rate=0., catalyst_to_gas_ua_w_k=0., catalyst_to_room_ua_w_k=2.,
                   radiating_area_m2=0., emissivity=0.)
    times = np.linspace(10., 30., 5)
    trace = model.integrate(inlet(), initial_catalyst_temperature_k=400.,
        time_s=times, clock_id="test:seconds-from-explicit-epoch", maximum_step_s=2.)
    for sample in trace.samples:
        elapsed = sample.time_s-times[0]
        expected = 300.+100.*math.exp(-2./100.*elapsed)
        assert sample.point.catalyst_temperature_k == pytest.approx(expected, abs=2e-7)
        assert abs(sample.energy_residual_j) < 1e-6
        assert sample.cumulative_hydrogen_removed_mol == 0.
    assert trace.clock_id == "test:seconds-from-explicit-epoch"


def test_reacting_coupled_transient_refinement_and_cumulative_ports():
    model = device()
    coarse = model.integrate(inlet(), initial_catalyst_temperature_k=340.,
        time_s=[0., 1., 2.], clock_id="PAR-test", maximum_step_s=.5)
    fine = model.integrate(inlet(), initial_catalyst_temperature_k=340.,
        time_s=[0., 1., 2.], clock_id="PAR-test", maximum_step_s=.1,
        relative_tolerance=1e-9)
    assert coarse.samples[-1].point.catalyst_temperature_k == pytest.approx(
        fine.samples[-1].point.catalyst_temperature_k, abs=1e-6)
    assert fine.samples[-1].cumulative_hydrogen_removed_mol == pytest.approx(2e-4, abs=1e-12)
    assert abs(fine.samples[-1].energy_residual_j) < 1e-5
    # Ordinary Python state coupling preserves the explicit outlet composition.
    downstream = model.evaluate(fine.samples[-1].point.outlet, 340.)
    assert downstream.inlet is fine.samples[-1].point.outlet


@pytest.mark.parametrize("changes", [
    {"loss_coefficient": 0.}, {"catalyst_heat_capacity_j_k": -1.},
    {"emissivity": 1.01}, {"background_mass_flow_kg_s": -.1},
    {"reaction_heat_to_catalyst_fraction": float("nan")},
])
def test_device_inputs_are_not_silently_clipped(changes):
    with pytest.raises(ValueError):
        parameters(**changes)


def test_missing_capacity_evidence_and_out_of_domain_states_reject():
    with pytest.raises(ValueError, match="evidence"):
        capacity(evidence_id="")
    with pytest.raises(ValueError, match="domain"):
        device().evaluate(inlet(), 1501.)
    with pytest.raises(ValueError, match="capacity"):
        device(rate=-1.).evaluate(inlet(), 400.)
    with pytest.raises(ValueError, match="species"):
        device().evaluate(ReactiveState(300., 101325., {"H2": .04, "O2": .2, "H": .76}), 400.)


def test_solver_owns_fresh_native_phases_and_snapshots_domain_inputs():
    model = device()
    original = model.gas.create_phase(inlet())
    before = np.array(original.native_phase.TPX[2])
    model.evaluate(inlet(), 400.)
    model.gas.snapshot_phase(original)
    assert original.native_phase.T == 300.
    np.testing.assert_array_equal(original.native_phase.X, before)
    mutable_bounds = [250., 1500.]
    declared = capacity(catalyst_temperature_bounds_k=mutable_bounds)
    mutable_bounds[1] = 9000.
    assert declared.catalyst_temperature_bounds_k == (250., 1500.)


def test_inconsistent_forward_capacity_in_steam_rich_hot_gas_fails_second_law():
    # A constant synthetic forward map is intentionally inappropriate for this
    # near-product-rich state. Native thermochemistry exposes its direction error
    # even though atom/mass/enthalpy balances can still close exactly.
    model = PARDevice(backend(), parameters(catalyst_to_gas_ua_w_k=0.,
        catalyst_to_room_ua_w_k=0., radiating_area_m2=0.,
        reaction_heat_to_catalyst_fraction=1., background_mass_flow_kg_s=.001),
        capacity(1., inlet_temperature_bounds_k=(250., 2000.)))
    steam_rich = ReactiveState(1500., 101325., {"H2": 1e-6, "O2": .01, "H2O": .989999})
    with pytest.raises(ValueError, match="entropy"):
        model.evaluate(steam_rich, 1500.)


@pytest.mark.parametrize("times", [[0., 0.], [1., 0.], [-1., 1.], [0., math.inf]])
def test_clock_support_rejects_invalid_times(times):
    with pytest.raises(ValueError, match="times"):
        device().integrate(inlet(), initial_catalyst_temperature_k=400.,
                           time_s=times, clock_id="test")
