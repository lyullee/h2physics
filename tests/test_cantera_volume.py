"""Original constant-cp limits, independent inventories and actual native objects."""

import hashlib
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
from h2physics.adapters.cantera_volume import (
    CanteraOpenGasVolume,
    GasBoundaryRate,
    GasFeed,
    GasHeatBoundary,
    GasVent,
    GasVolumeIntegrationError,
    sampled_gas_rate,
)
from h2physics.core import Origin, TimeSeries
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

ct = pytest.importorskip("cantera")


def phase_factory():
    # Authored constant-cp verification properties; not fitted hydrogen data.
    species = []
    cp = 3.5*ct.gas_constant
    for name, atoms in (("H2", {"H": 2}), ("N2", {"N": 2})):
        item = ct.Species(name, atoms)
        item.thermo = ct.ConstantCp(200., 2000., 101325., [300., cp*300., 0., cp])
        species.append(item)
    return ct.Solution(thermo="ideal-gas", kinetics=None, species=species)


def basis(**kwargs):
    fields = dict(identifier="authored-constant-cp-H2-N2-verification",
        source_sha256="a"*64, license_id="Apache-2.0-original-test-parameters",
        references=("https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html",),
        minimum_temperature_k=210., maximum_temperature_k=1900.,
        minimum_pressure_pa=100., maximum_pressure_pa=1e7)
    fields.update(kwargs)
    return MechanismBasis(**fields)


def state(temperature=300., pressure=101325., species="N2"):
    return ReactiveState(temperature, pressure, {species: 1.})


def rate(value, name="flow", *, start=10., end=12., clock="operation"):
    return GasBoundaryRate(name, clock, start, end,
                           value if callable(value) else lambda t, p: value,
                           Origin.SYNTHETIC, "authored-positive-boundary")


def run(*, initial=None, times=None, feeds=(), vents=(), heat=(), step=.01,
        provider=None, **kwargs):
    return (provider or CanteraOpenGasVolume(phase_factory, basis())).run(
        initial or state(), [10., 10.5, 11.] if times is None else times,
        volume_m3=.5, clock_id="operation", feeds=feeds, vents=vents,
        heat_boundaries=heat, maximum_time_step_s=step, **kwargs)


def assert_balances(result, *, mass=1e-10, energy=1e-3):
    assert max(abs(result.mass_residual_kg)) < mass
    assert np.max(abs(result.species_residual_kg)) < mass
    assert max(abs(result.energy_residual_j)) < energy


def test_sealed_native_volume_keeps_inventory_and_actual_objects():
    result = run()
    first, last = result.snapshots[0], result.snapshots[-1]
    assert last.mass_kg == pytest.approx(first.mass_kg, abs=1e-14)
    assert last.temperature_k == pytest.approx(first.temperature_k, abs=1e-11)
    assert last.pressure_pa == pytest.approx(first.pressure_pa, abs=1e-8)
    assert isinstance(result.native.reactor, ct.ExtensibleIdealGasReactor)
    assert isinstance(result.native.network, ct.ReactorNet)
    assert result.native.reactor.chemistry_enabled is False
    assert result.native.reactor.phase.n_reactions == 0
    assert result.native.reactor.n_vars == 3+len(result.species_names)+len(result.ledger_names)
    assert not result.boundary_integrals.flags.writeable
    assert not result.time_s.flags.writeable
    assert not result.ledger_native_scale_to_si.flags.writeable
    assert np.array_equal(result.ledger_native_scale_to_si[-3:], np.full(3, 1e6))
    with pytest.raises(TypeError):
        last.mass_fractions["H2"] = 1.
    assert_balances(result)


def test_constant_feed_analytic_finite_species_energy_and_pressure():
    feed_state = state(400., species="H2")
    result = run(feeds=(GasFeed(rate(.01), feed_state),), relative_tolerance=1e-11)
    before, after = result.snapshots[0], result.snapshots[-1]
    phase = phase_factory()
    phase.TPX = 400., 101325., {"H2": 1.}
    expected_energy = before.internal_energy_j+.01*phase.enthalpy_mass
    mw_h2, mw_n2 = phase.molecular_weights
    expected_moles = before.mass_kg/mw_n2+.01/mw_h2
    expected_temperature = expected_energy/(2.5*ct.gas_constant*expected_moles)
    assert after.mass_kg == pytest.approx(before.mass_kg+.01, abs=1e-11)
    assert after.mass_fractions["H2"] == pytest.approx(.01/after.mass_kg, abs=2e-11)
    assert after.temperature_k == pytest.approx(expected_temperature, rel=1e-9)
    expected_pressure = expected_moles*ct.gas_constant*expected_temperature/.5
    assert after.pressure_pa == pytest.approx(expected_pressure, rel=1e-9)
    assert result.integral("inlet:flow:mass")[-1] == pytest.approx(.01, abs=1e-12)
    assert result.integral("inlet:enthalpy")[-1] == pytest.approx(.01*phase.enthalpy_mass, rel=1e-10)
    assert isinstance(result.native.feed_devices[0], ct.MassFlowController)
    assert isinstance(result.native.feed_reservoirs[0], ct.Reservoir)
    assert result.native.feed_devices[0].upstream is result.native.feed_reservoirs[0]
    assert_balances(result)
    unscaled = run(feeds=(GasFeed(rate(.01), feed_state),), relative_tolerance=1e-11,
                   energy_ledger_scale_j=1.)
    assert_balances(unscaled)
    assert abs(after.temperature_k-unscaled.snapshots[-1].temperature_k) < 1e-6
    assert abs(after.pressure_pa-unscaled.snapshots[-1].pressure_pa) < .001
    assert np.max(abs(result.boundary_integrals-unscaled.boundary_integrals)) < .001


def test_adiabatic_vent_analytic_cooling_and_outlet_enthalpy():
    reference = run().snapshots[0]
    flow = .1*reference.mass_kg
    result = run(vents=(GasVent(rate(flow, "extract"), state()),), relative_tolerance=1e-11)
    before, after = result.snapshots[0], result.snapshots[-1]
    ratio = .9
    assert after.mass_kg == pytest.approx(before.mass_kg*ratio, rel=1e-11)
    assert after.temperature_k == pytest.approx(before.temperature_k*ratio**.4, rel=2e-9)
    assert after.pressure_pa == pytest.approx(before.pressure_pa*ratio**1.4, rel=2e-9)
    assert result.integral("outlet:enthalpy")[-1] == pytest.approx(
        before.internal_energy_j-after.internal_energy_j, abs=.001)
    assert_balances(result)


def test_fixed_mass_mixing_is_exponential_in_native_mass_fractions():
    initial = state(400.)
    inventory = run(initial=initial).snapshots[0].mass_kg
    flow = inventory*.2
    result = run(initial=initial, feeds=(GasFeed(rate(flow, "feed"), state(400., species="H2")),),
        vents=(GasVent(rate(flow, "vent"), state()),), relative_tolerance=1e-11)
    last = result.snapshots[-1]
    assert last.mass_kg == pytest.approx(inventory, rel=1e-11)
    assert last.mass_fractions["H2"] == pytest.approx(1-np.exp(-.2), abs=2e-10)
    assert last.mass_fractions["N2"] == pytest.approx(np.exp(-.2), abs=2e-10)
    assert_balances(result, energy=.01)


@pytest.mark.parametrize("heat_flux", [100., -100.])
def test_sealed_prescribed_native_wall_heat_signed_energy(heat_flux):
    heat = GasHeatBoundary("external", "operation", 10., 12., state(), 2.,
                           heat_flux_w_m2=lambda t: heat_flux)
    result = run(heat=(heat,), relative_tolerance=1e-11)
    first, last = result.snapshots[0], result.snapshots[-1]
    phase = phase_factory()
    phase.TPX = first.temperature_k, first.pressure_pa, {"N2": 1.}
    assert last.temperature_k == pytest.approx(first.temperature_k+2*heat_flux/(first.mass_kg*phase.cv_mass),
                                             abs=1e-7)
    assert result.integral("wall:heat")[-1] == pytest.approx(2*heat_flux, abs=1e-9)
    assert isinstance(result.native.walls[0], ct.Wall)
    assert result.native.walls[0].left_reactor is result.native.environment_reservoirs[0]
    assert_balances(result)


def test_native_wall_conduction_exponential_temperature():
    heat = GasHeatBoundary("conducting", "operation", 10., 12., state(500.), 2., 10.)
    result = run(heat=(heat,), relative_tolerance=1e-11)
    first, last = result.snapshots[0], result.snapshots[-1]
    phase = phase_factory()
    phase.TPX = first.temperature_k, first.pressure_pa, {"N2": 1.}
    expected = 500.+(first.temperature_k-500.)*np.exp(-20./(first.mass_kg*phase.cv_mass))
    assert last.temperature_k == pytest.approx(expected, abs=2e-7)
    assert_balances(result)


def test_absolute_clock_callback_and_independent_time_integral():
    calls = []

    def callback(t, phase):
        calls.append(t)
        return .001*(t-9.)

    result = run(feeds=(GasFeed(rate(callback), state(400., species="H2")),))
    assert min(calls) == 10.
    assert result.integral("inlet:flow:mass")[-1] == pytest.approx(.0015, abs=1e-12)
    assert result.evaluated_clock_bounds_s == (min(calls), max(calls))
    assert result.clock_id == "operation"
    assert_balances(result)


def test_negative_rate_is_not_silently_clipped_by_native_controller():
    with pytest.raises(GasVolumeIntegrationError, match="Negative oriented") as error:
        run(feeds=(GasFeed(rate(-.01), state()),))
    assert isinstance(error.value.native.network, ct.ReactorNet)


def test_clock_mismatch_unsupported_clock_and_depletion_are_errors():
    with pytest.raises(ValueError, match="clock identities"):
        run(feeds=(GasFeed(rate(.01, clock="different-recorder"), state()),))
    with pytest.raises(ValueError, match="clock support"):
        run(feeds=(GasFeed(rate(.01, end=10.9), state()),))
    # Reserve one maximum native step for trial times past the output end.
    with pytest.raises(ValueError, match="clock support"):
        run(feeds=(GasFeed(rate(.01, end=11.), state()),))
    inventory = run().snapshots[0].mass_kg
    with pytest.raises(GasVolumeIntegrationError, match="declared minimum"):
        run(vents=(GasVent(rate(.3*inventory), state()),), minimum_inventory_kg=.8*inventory)


def test_native_bounds_phase_factory_and_mutation_guards():
    with pytest.raises(ValueError, match="domain"):
        run(initial=state(200.))
    shared = phase_factory()
    with pytest.raises(ValueError, match="fresh independent"):
        run(provider=CanteraOpenGasVolume(lambda: shared, basis()),
            feeds=(GasFeed(rate(.01), state()),))

    def changed(t, phase):
        phase.TP = 350., phase.P
        return .01

    with pytest.raises(GasVolumeIntegrationError, match="mutated"):
        run(feeds=(GasFeed(rate(changed), state()),))
    narrow = CanteraOpenGasVolume(phase_factory, basis(maximum_pressure_pa=101400.))
    with pytest.raises(GasVolumeIntegrationError, match="domain"):
        run(provider=narrow, feeds=(GasFeed(rate(.01), state()),))


def test_actual_reactive_mechanism_is_rejected_and_frozen_subset_is_native():
    raw = (Path(ct.__file__).parent/"data/h2o2.yaml").read_bytes()
    provenance = basis(source_sha256=hashlib.sha256(raw).hexdigest())
    def reactive_factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
    with pytest.raises(ValueError, match="zero reactions"):
        run(provider=CanteraOpenGasVolume(reactive_factory, provenance))

    def frozen():
        donor = reactive_factory()
        return ct.Solution(thermo="ideal-gas", kinetics=None,
                           species=[donor.species("H2"), donor.species("N2")])

    result = run(provider=CanteraOpenGasVolume(frozen, provenance),
                 feeds=(GasFeed(rate(.001), state(species="H2")),))
    assert result.snapshots[-1].mass_fractions["H2"] > 0
    assert_balances(result, energy=.01)


def test_existing_shared_nozzle_can_drive_native_pure_gas_vent():
    # This physical case has exactly fixed N2 composition. No conversion of
    # an evolving composition or finite-difference Jacobian trial is implied.
    dedicated_phase = phase_factory()
    properties = CanteraFrozenGasProperties(dedicated_phase, basis(), {"N2": 1.})
    nozzle = HomogeneousIsentropicNozzle(properties)
    opening = NozzleOpening("authored-vent", 1e-6, 1., "declared-effective-area")
    actual_nozzles = []

    def outward(t, phase):
        upstream = properties.state_pt(phase.P, phase.T)
        solved = nozzle.solve(upstream, back_pressure_pa=9e4, opening=opening)
        actual_nozzles.append(solved)
        return solved.mass_flow_kg_s

    result = run(times=[10., 10.05], step=.01,
        vents=(GasVent(rate(outward, "shared-nozzle"), state(pressure=9e4)),),
        relative_tolerance=1e-8)
    assert actual_nozzles and all(n.mass_flow_kg_s > 0 for n in actual_nozzles)
    assert result.snapshots[-1].mass_kg < result.snapshots[0].mass_kg
    assert result.snapshots[-1].temperature_k < result.snapshots[0].temperature_k
    assert dedicated_phase is not result.native.reactor.phase
    assert_balances(result, energy=.01)


def test_sampled_source_clock_masks_units_sign_and_no_extrapolation():
    def series(values, **kwargs):
        fields = dict(time_s=np.array([10., 10.5, 12.]), values=np.array(values)[:, None],
            valid=np.ones((3, 1), dtype=bool), channels=("feed",), units=("kg/s",),
            clock_id="operation", origin=Origin.SYNTHETIC, source_id="authored-positive-source",
            quantities=("mass_flow",))
        fields.update(kwargs)
        return TimeSeries(**fields)

    sampled = sampled_gas_rate(series([.001, .002, .005]), "feed", boundary_id="sampled")
    result = run(feeds=(GasFeed(sampled, state(species="H2")),))
    assert result.integral("inlet:sampled:mass")[-1] == pytest.approx(.002, abs=2e-10)
    with pytest.raises(ValueError, match="support"):
        sampled.value(12.1, phase_factory())
    with pytest.raises(ValueError, match="signed measurements"):
        sampled_gas_rate(series([.001, -.002, .003]), "feed", boundary_id="bad")
    with pytest.raises(ValueError, match="masked gaps"):
        sampled_gas_rate(series([.001, .002, .003], valid=np.array([[True], [False], [True]])),
                         "feed", boundary_id="bad")
    with pytest.raises(ValueError, match="kg/s"):
        sampled_gas_rate(series([.001, .002, .003], units=("g/s",)), "feed", boundary_id="bad")
