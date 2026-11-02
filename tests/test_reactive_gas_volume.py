"""Native gas chemistry with independent authored reaction/flow balances."""

import hashlib
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_volume import (
    CanteraOpenGasVolume,
    GasBoundaryRate,
    GasFeed,
    GasVent,
    GasVolumeIntegrationError,
)
from h2physics.core import Origin

ct = pytest.importorskip("cantera")


def factory(*, enthalpy_difference_j_kmol=0., rate_s_inv=.5):
    # A/B are authored fictitious same-mass species, not spin or physical H2 fits.
    species = []
    for name, formation in (("A", 0.), ("B", -enthalpy_difference_j_kmol)):
        item = ct.Species(name, {"H": 2})
        item.thermo = ct.ConstantCp(200., 2500., 101325.,
            [300., formation, 0., 3.5*ct.gas_constant])
        species.append(item)
    reaction = ct.Reaction(equation="A => B", rate=ct.ArrheniusRate(rate_s_inv, 0., 0.))
    return ct.Solution(thermo="ideal-gas", kinetics="bulk", species=species, reactions=[reaction])


def basis():
    return MechanismBasis("authored-gas-reaction-verification", "a"*64,
        "Apache-2.0-original-test-parameters",
        ("https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html",),
        210., 2400., 100., 1e7)


def state(temperature=300., composition=None):
    return ReactiveState(temperature, 101325., {"A": 1.} if composition is None else composition)


def rate(name, value):
    return GasBoundaryRate(name, "reaction-clock", 10., 14.,
        value if callable(value) else lambda t, phase: value, Origin.SYNTHETIC, "authored-flow")


def run(*, phase_factory=factory, feeds=(), vents=(), times=None, step=.01):
    return CanteraOpenGasVolume(phase_factory, basis(), chemistry="finite_rate").run(
        state(), np.linspace(10., 12., 101) if times is None else times,
        volume_m3=.1, clock_id="reaction-clock", feeds=feeds, vents=vents,
        maximum_time_step_s=step, relative_tolerance=1e-11, absolute_tolerance=1e-15)


def assert_ledgers(trace):
    assert np.max(np.abs(trace.mass_residual_kg)) < 1e-10
    assert np.max(np.abs(trace.species_residual_kg)) < 1e-10
    assert np.max(np.abs(trace.element_residual_kg)) < 1e-10
    assert np.max(np.abs(trace.energy_residual_j)) < 1e-5
    assert np.max(np.abs(trace.reaction_species_integrals_kg.sum(axis=1))) < 1e-10


def test_native_closed_first_order_reaction_matches_analytic_and_integrated_production():
    trace = run()
    initial_mass = trace.snapshots[0].mass_kg
    converted = initial_mass*(1-np.exp(-.5*(trace.time_s-10)))
    assert trace.chemistry == "finite_rate"
    assert trace.native.reactor.chemistry_enabled is True
    assert trace.native.reactor.phase.n_reactions == 1
    assert [item.mass_fractions["A"] for item in trace.snapshots] == pytest.approx(
        np.exp(-.5*(trace.time_s-10)), abs=1e-10)
    assert trace.integral("reaction:species:B") == pytest.approx(converted, abs=1e-10)
    assert trace.integral("net:species:A") == pytest.approx(np.zeros(len(converted)), abs=1e-15)
    assert trace.element_names == ("H",)
    assert not trace.reaction_species_integrals_kg.flags.writeable
    assert not trace.element_residual_kg.flags.writeable
    assert_ledgers(trace)


def test_native_formation_energy_heats_without_an_extra_reaction_power_boundary():
    difference = 2e6
    trace = run(phase_factory=lambda: factory(enthalpy_difference_j_kmol=difference))
    # Same molecular mass/cv and one-to-one stoichiometry give this exact UV limit.
    expected = 300.+difference/(2.5*ct.gas_constant)*(1-np.exp(-.5*(trace.time_s-10)))
    assert [item.temperature_k for item in trace.snapshots] == pytest.approx(expected, abs=1e-7)
    assert trace.integral("wall:heat") == pytest.approx(np.zeros(len(expected)), abs=1e-15)
    assert_ledgers(trace)


def test_flowing_native_reactor_matches_first_order_cstr_oracle_and_species_boundary_split():
    sealed = run()
    inventory = sealed.snapshots[0].mass_kg
    turnover = .2
    flow = turnover*inventory
    trace = run(feeds=(GasFeed(rate("feed", flow), state()),),
        vents=(GasVent(rate("vent", flow), state()),))
    decay = turnover+.5
    expected_a = turnover/decay+(1-turnover/decay)*np.exp(-decay*(trace.time_s-10))
    assert [item.mass_fractions["A"] for item in trace.snapshots] == pytest.approx(expected_a, abs=1e-9)
    assert [item.mass_kg for item in trace.snapshots] == pytest.approx(
        [inventory]*len(trace.snapshots), abs=1e-10)
    assert trace.integral("inlet:feed:mass")[-1] == pytest.approx(2*flow, abs=1e-10)
    assert trace.integral("reaction:species:A")[-1] < 0
    assert trace.integral("net:species:A")[-1] > 0
    assert_ledgers(trace)


def test_default_frozen_mode_still_rejects_reactions_and_explicit_mode_requires_them():
    with pytest.raises(ValueError, match="zero reactions"):
        CanteraOpenGasVolume(factory, basis()).run(state(), [10., 11.], volume_m3=.1,
            clock_id="reaction-clock", maximum_time_step_s=.01)
    def no_reactions():
        donor = factory()
        return ct.Solution(thermo="ideal-gas", species=donor.species())
    with pytest.raises(ValueError, match="actual native gas reactions"):
        run(phase_factory=no_reactions)


def test_reaction_multiplier_mutation_is_not_hidden_by_a_native_retry():
    def mutated(t, phase):
        phase.set_multiplier(.25)
        return .0001
    with pytest.raises(GasVolumeIntegrationError, match="kinetics") as failed:
        run(feeds=(GasFeed(rate("mutator", mutated), state()),))
    assert failed.value.native.reactor.phase.multiplier(0) == .25


def test_different_reservoir_kinetics_rejected_even_with_equal_species_thermochemistry():
    calls = []
    def changed():
        calls.append(True)
        return factory(rate_s_inv=.5 if len(calls) == 1 else .7)
    with pytest.raises(ValueError, match="kinetics differ"):
        run(phase_factory=changed, feeds=(GasFeed(rate("feed", .001), state()),))


def test_actual_installed_gas_mechanism_matches_existing_native_closed_reactor():
    from h2physics.adapters.cantera import CanteraGas

    raw_bytes = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
    raw = raw_bytes.decode("utf-8")
    def real():
        return ct.Solution(yaml=raw, name="ohmech")
    native_basis = MechanismBasis("installed-h2o2-native-reaction-reference",
        hashlib.sha256(raw_bytes).hexdigest(),
        "Cantera-BSD-3-Clause; source thermochemistry provenance",
        ("https://cantera.org/3.2/examples/input/h2o2.html",), 400., 3000., 1e4, 1e7)
    initial = ReactiveState(1100., 101325., {"H2": .2, "O2": .1, "N2": .7})
    times = np.linspace(0., .0002, 21)
    trace = CanteraOpenGasVolume(real, native_basis, chemistry="finite_rate").run(initial, times,
        volume_m3=.001, clock_id="native-reference", maximum_time_step_s=1e-5,
        relative_tolerance=1e-10, absolute_tolerance=1e-17)
    reference = CanteraGas(real, native_basis).closed_reactor(initial, times,
        maximum_time_step_s=1e-5, relative_tolerance=1e-10, absolute_tolerance=1e-17)
    assert trace.snapshots[-1].temperature_k == pytest.approx(
        reference.snapshots[-1].state.temperature_k, abs=1e-5)
    assert trace.source_phase_fingerprint == trace.phase_copy_audits[0].source_fingerprint
    assert trace.phase_fingerprint == trace.phase_copy_audits[0].owned_fingerprint
    assert trace.phase_copy_audits[0].maximum_relative_roundtrip < 2e-15
    assert set(trace.element_names) == set(trace.phase_copy_audits[0].source_element_names)
    assert_ledgers(trace)


def test_time_only_callbacks_use_private_native_clones_without_factory_alias_mutation():
    phases = []
    def captured_factory():
        phase = factory()
        phases.append(phase)
        return phase
    def external_source_edit(time):
        phases[0].set_multiplier(20.)
        reaction = phases[0].reaction(0)
        reaction.rate = ct.ArrheniusRate(30., 0., 0.)
        phases[0].modify_reaction(0, reaction)
        return 0.
    boundary = GasBoundaryRate("time-only", "reaction-clock", 10., 14., external_source_edit,
        Origin.SYNTHETIC, "authored-time-only-boundary", phase_access="time_only")
    trace = run(phase_factory=captured_factory, feeds=(GasFeed(boundary, state()),))
    assert trace.definition_guard == "private-native-clones-and-accepted-output"
    assert trace.native.reactor.phase is not phases[0]
    assert trace.native.feed_reservoirs[0].phase is not phases[1]
    assert trace.native.reactor.phase.multiplier(0) == 1.
    assert trace.native.reactor.phase.reaction(0).rate.pre_exponential_factor == .5
    assert trace.native.reactor.phase.min_temp == 200.
    assert trace.native.reactor.phase.max_temp == 2500.
    assert trace.snapshots[-1].mass_fractions["A"] == pytest.approx(np.exp(-1.), abs=1e-9)
    assert_ledgers(trace)


def test_private_native_copy_preserves_nondefault_runtime_reaction_multiplier():
    def scaled():
        phase = factory()
        phase.set_multiplier(2.)
        return phase
    trace = run(phase_factory=scaled)
    assert trace.native.reactor.phase.multiplier(0) == 2.
    assert trace.snapshots[-1].mass_fractions["A"] == pytest.approx(np.exp(-2.), abs=1e-9)
    assert_ledgers(trace)
