"""Actual native finite-O2 inventories and independent authored mixing limits."""

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
from h2physics.adapters.cantera_volume import GasBoundaryRate, GasHeatBoundary, GasVent
from h2physics.adapters.oxygen_deficiency import (
    CanteraOxygenRoom,
    OxygenCriterion,
    OxygenFeedAdmission,
    OxygenResultVerificationError,
    OxygenRoomError,
    OxygenRoomRegion,
    OxygenRoomSettings,
    evaluate_oxygen_criterion,
    verify_oxygen_room_result,
)
from h2physics.core import Origin
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation
from h2physics.sources import IntervalMassSource

ct = pytest.importorskip("cantera")


@pytest.fixture
def setup():
    raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()

    def factory():
        species = {s.name: s for s in ct.Species.list_from_yaml(raw.decode(), "species")}
        return ct.Solution(
            thermo="ideal-gas", species=[species[n] for n in ("H2", "O2", "N2", "H2O")]
        )

    basis = MechanismBasis(
        "installed-h2o2-frozen-oxygen-room",
        hashlib.sha256(raw).hexdigest(),
        "Cantera BSD-3-Clause; installed species provenance",
        ("https://cantera.org/3.2/python/zerodim.html",),
        300.0,
        1000.0,
        50000.0,
        500000.0,
    )
    region = OxygenRoomRegion(
        "room",
        "receptor",
        "global",
        "operation",
        (1.0, 2.0, 1.5),
        0.0,
        1.0,
        "authored-homogeneous-region",
        "warm-single-gas",
        "prescribed-ports",
        Origin.SYNTHETIC,
    )
    return factory, basis, region


def feed(
    setup,
    *,
    edges=(100.0, 101.0),
    mass=(0.001,),
    fractions=None,
    name="H2-source",
    outside=None,
    end="isolation",
    temperature=330.0,
    frame="global",
    clock="operation",
):
    factory, basis, _ = setup
    phase = factory()
    phase.TPX = temperature, 200000.0, fractions or {"H2": 1.0}
    properties = CanteraFrozenGasProperties(
        phase,
        basis,
        dict(zip(phase.species_names, phase.Y)),
        composition_sum_tolerance=1e-14,
        composition_correction_id="native-accepted-state-ulps",
    )
    state = properties.state_pt(200000.0, temperature)
    source = IntervalMassSource(
        SourceLocation(name, clock, frame, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        edges,
        mass,
        state,
        Origin.SYNTHETIC,
        "authored-finite-feed",
        end,
    )
    return OxygenFeedAdmission(source, properties, "native-caloric-admission", outside)


def run(
    setup,
    *,
    times=(100.0, 101.0),
    initial=None,
    feeds=(),
    exhausts=(),
    heat=(),
    settings=None,
    events=(),
):
    factory, basis, region = setup
    return CanteraOxygenRoom(factory, basis, region).run(
        initial or ReactiveState(330.0, 101325.0, {"O2": 0.21, "N2": 0.79}),
        times,
        feeds=feeds,
        exhausts=exhausts,
        heat_boundaries=heat,
        event_times_s=events,
        settings=settings or OxygenRoomSettings(maximum_time_step_s=0.1),
    )


def vent(callback, *, clock="operation", start=100.0, end=102.0, name="exhaust"):
    return GasVent(
        GasBoundaryRate(
            name,
            clock,
            start,
            end,
            callback,
            Origin.SYNTHETIC,
            "authored-extraction-not-passive-valve",
        ),
        ReactiveState(330.0, 101325.0, {"N2": 1.0}),
    )


def criterion(**changes):
    values = dict(
        criterion_id="authored-screen",
        quantity="wet_oxygen_mole_fraction",
        threshold=0.195,
        comparator="below",
        minimum_pressure_pa=50000.0,
        maximum_pressure_pa=500000.0,
        minimum_elevation_m=-100.0,
        maximum_elevation_m=100.0,
        authority_reference="authored-test",
        applicability_evidence_id="no-facility-or-human-response-claim",
    )
    values.update(changes)
    return OxygenCriterion(**values)


def assert_ledgers(result):
    assert np.max(abs(result.mass_residual_kg)) < 1e-9
    assert np.max(abs(result.species_residual_kg)) < 1e-9
    assert np.max(abs(result.energy_residual_j)) < 0.001
    assert np.max(abs(result.pressure_identity_residual_pa)) < 1e-5
    assert np.max(abs(result.source_enthalpy_residual_j)) < 0.001


def test_native_sealed_finite_inventory_objects_and_no_harm_probability(setup):
    result = run(setup)
    assert result.oxygen_inventory_kg[-1] == pytest.approx(result.oxygen_inventory_kg[0], abs=1e-14)
    assert result.wet_oxygen_mole_fraction == pytest.approx([0.21, 0.21])
    assert result.oxygen_partial_pressure_pa == pytest.approx([21278.25, 21278.25])
    assert result.probability is None
    assert isinstance(result.native[0].reactor, ct.ExtensibleIdealGasReactor)
    assert isinstance(result.native[0].network, ct.ReactorNet)
    assert result.native[0] is result.native_traces[0].native
    assert result.native[0].reactor.chemistry_enabled is False
    assert not result.oxygen_inventory_kg.flags.writeable
    assert_ledgers(result)


def test_native_finite_feed_matches_source_mass_species_caloric_pressure_and_adiabatic_oracle(
    setup,
):
    admission = feed(setup)
    result = run(
        setup,
        feeds=(admission,),
        settings=OxygenRoomSettings(relative_tolerance=1e-12, absolute_tolerance=1e-16),
    )
    first, last = result.snapshots[0], result.snapshots[-1]
    assert last.mass_kg - first.mass_kg == pytest.approx(0.001, abs=1e-12)
    assert result.oxygen_inventory_kg[-1] == pytest.approx(result.oxygen_inventory_kg[0], abs=1e-12)
    assert last.internal_energy_j - first.internal_energy_j == pytest.approx(
        0.001 * admission.source.state.enthalpy_j_kg, abs=1e-5
    )
    phase = setup[0]()
    # Independent native UV state from directly summed species masses and U;
    # no second finite-volume derivative or integrator is implemented.
    inventory = result.species_inventory_kg[0].copy()
    inventory[result.species_names.index("H2")] += 0.001
    phase.Y = inventory / inventory.sum()
    phase.UV = (
        (first.internal_energy_j + 0.001 * admission.source.state.enthalpy_j_kg) / inventory.sum(),
        1 / inventory.sum(),
    )
    assert last.temperature_k == pytest.approx(phase.T, rel=1e-9)
    assert last.pressure_pa == pytest.approx(phase.P, rel=1e-9)
    assert result.oxygen_partial_pressure_pa[-1] == pytest.approx(
        result.oxygen_partial_pressure_pa[0] * last.temperature_k / first.temperature_k, rel=1e-9
    )
    assert_ledgers(result)


def test_actual_interval_events_isolation_and_exact_source_enthalpy(setup):
    admission = feed(
        setup,
        edges=(100.0, 100.3, 100.6),
        mass=(0.0002, 0.0004),
        outside="declared-isolated-through-window",
    )
    result = run(setup, feeds=(admission,), times=(100.0, 100.2, 100.7, 101.0))
    assert len(result.native_traces) == 3
    assert result.time_s == pytest.approx([100.0, 100.2, 100.3, 100.6, 100.7, 101.0])
    assert result.integral("inlet:feed:H2-source:mass")[-1] == pytest.approx(0.0006, abs=1e-12)
    assert result.snapshots[-1].mass_kg == pytest.approx(result.snapshots[-2].mass_kg, abs=1e-12)
    assert np.max(abs(result.source_mass_residual_kg)) < 1e-12
    assert result.feeds[0].source is admission.source
    assert result.admission_native_phases[0] is admission.properties.native_phase
    assert_ledgers(result)


def test_native_equal_molar_displacement_matches_exponential_oxygen_and_purge(setup):
    phase = setup[0]()
    phase.TPX = 330.0, 101325.0, {"O2": 0.21, "N2": 0.79}
    n_total = phase.density_mole
    h2_mw = phase.molecular_weights[phase.species_index("H2")]
    ndot = 0.1 * n_total
    incoming = feed(setup, mass=(ndot * h2_mw,))
    exhaust = vent(lambda t, p: ndot * p.mean_molecular_weight)
    result = run(setup, feeds=(incoming,), exhausts=(exhaust,), times=np.linspace(100.0, 101.0, 6))
    assert result.wet_oxygen_mole_fraction == pytest.approx(
        0.21 * np.exp(-0.1 * (result.time_s - 100)), rel=2e-8
    )
    assert [s.temperature_k for s in result.snapshots] == pytest.approx([330.0] * 6, abs=2e-6)
    assert [s.pressure_pa for s in result.snapshots] == pytest.approx([101325.0] * 6, abs=0.001)
    assert result.oxygen_inventory_kg[-1] < result.oxygen_inventory_kg[0]
    initial = ReactiveState(330.0, 101325.0, result.snapshots[-1].mole_fractions)
    phase.TPX = 330.0, 200000.0, {"O2": 0.21, "N2": 0.79}
    air = feed(
        setup,
        fractions={"O2": 0.21, "N2": 0.79},
        mass=(ndot * phase.mean_molecular_weight,),
        name="fresh-air",
    )
    recovered = run(setup, initial=initial, feeds=(air,), exhausts=(exhaust,))
    expected = 0.21 + (initial.mole_fractions["O2"] - 0.21) * math.exp(-0.1)
    assert recovered.wet_oxygen_mole_fraction[-1] == pytest.approx(expected, rel=2e-8)
    assert_ledgers(result)
    assert_ledgers(recovered)


def test_sealed_isothermal_hydrogen_addition_lowers_fraction_but_not_partial_pressure(setup):
    admission = feed(setup)
    phase = admission.properties.native_phase
    required_heat = 0.001 * (
        admission.source.state.internal_energy_j_kg - admission.source.state.enthalpy_j_kg
    )
    wall = GasHeatBoundary(
        "declared-thermostat",
        "operation",
        100.0,
        101.0,
        ReactiveState(330.0, 101325.0, {"N2": 1.0}),
        1.0,
        heat_flux_w_m2=lambda t: required_heat,
    )
    result = run(setup, feeds=(admission,), heat=(wall,))
    assert result.snapshots[-1].temperature_k == pytest.approx(330.0, abs=1e-7)
    assert result.wet_oxygen_mole_fraction[-1] < result.wet_oxygen_mole_fraction[0]
    assert result.oxygen_partial_pressure_pa[-1] == pytest.approx(
        result.oxygen_partial_pressure_pa[0], abs=1e-4
    )
    assert result.integral("wall:heat")[-1] == pytest.approx(required_heat, abs=1e-8)
    assert required_heat < 0
    assert isinstance(phase, ct.Solution)
    assert_ledgers(result)


def test_actual_shared_nozzle_observes_evolving_pressure_and_composition(setup):
    factory, basis, _ = setup
    independent_phase = factory()
    opening = NozzleOpening("authored-room-outlet", 1e-6, 1.0, "declared-effective-area")
    actual_calls, corrections = [], []

    def pressure_driven(t, phase):
        properties = CanteraFrozenGasProperties(
            independent_phase,
            basis,
            dict(zip(phase.species_names, phase.Y, strict=True)),
            composition_sum_tolerance=1e-7,
            composition_correction_id="caller-declared-native-off-manifold-trial-extension;trial-type-unobservable",
        )
        corrections.append(properties.composition_correction)
        solved = HomogeneousIsentropicNozzle(properties).solve(
            properties.state_pt(phase.P, phase.T), back_pressure_pa=100000.0, opening=opening
        )
        actual_calls.append((float(phase.P), tuple(phase.Y), solved))
        return solved.mass_flow_kg_s

    incoming = feed(setup, edges=(100.0, 100.001), mass=(1e-7,))
    result = run(
        setup,
        feeds=(incoming,),
        exhausts=(vent(pressure_driven),),
        times=(100.0, 100.001),
        settings=OxygenRoomSettings(
            maximum_time_step_s=0.0005, relative_tolerance=1e-8, absolute_tolerance=1e-13
        ),
    )
    assert actual_calls and all(c[2].mass_flow_kg_s > 0 for c in actual_calls)
    assert len({c[0] for c in actual_calls}) > 1
    assert len({c[1] for c in actual_calls}) > 1
    assert independent_phase is not result.native[0].reactor.phase
    assert max(abs(c[2].energy_residual_w) for c in actual_calls) < 1e-6
    assert result.oxygen_inventory_kg[-1] < result.oxygen_inventory_kg[0]
    assert corrections  # Actual signed corrections, when present, are native trial extensions.
    assert_ledgers(result)


def test_wet_dry_fraction_and_ambient_partial_pressure_are_separate(setup):
    result = run(
        setup, initial=ReactiveState(330.0, 101325.0, {"O2": 0.19, "N2": 0.76, "H2O": 0.05})
    )
    assert result.wet_oxygen_mole_fraction == pytest.approx([0.19, 0.19])
    assert result.dry_oxygen_mole_fraction == pytest.approx([0.20, 0.20])
    assert result.oxygen_partial_pressure_pa == pytest.approx([0.19 * 101325.0] * 2)
    wet = evaluate_oxygen_criterion(
        result, criterion(), interpolation="linear_between_native_output_samples"
    )
    dry = evaluate_oxygen_criterion(
        result,
        criterion(quantity="dry_oxygen_mole_fraction"),
        interpolation="linear_between_native_output_samples",
    )
    assert wet.reconstructed_deficit_duration_s == 1.0
    assert dry.reconstructed_deficit_duration_s == 0.0
    assert wet.probability is None


def test_pure_water_has_explicit_undefined_dry_fraction(setup):
    result = run(setup, initial=ReactiveState(500.0, 101325.0, {"H2O": 1.0}))
    assert not result.dry_fraction_valid.any()
    assert np.isnan(result.dry_oxygen_mole_fraction).all()
    with pytest.raises(ValueError, match="undefined"):
        evaluate_oxygen_criterion(
            result,
            criterion(quantity="dry_oxygen_mole_fraction"),
            interpolation="linear_between_native_output_samples",
        )


def test_linear_output_crossing_brackets_and_refinement_of_analytic_crossing(setup):
    phase = setup[0]()
    phase.TPX = 330.0, 101325.0, {"O2": 0.21, "N2": 0.79}
    ndot = 0.2 * phase.density_mole
    incoming = feed(setup, mass=(ndot * phase.molecular_weights[phase.species_index("H2")],))
    exhaust = vent(lambda t, p: ndot * p.mean_molecular_weight)
    reports = []
    for n in (5, 17):
        result = run(
            setup, feeds=(incoming,), exhausts=(exhaust,), times=np.linspace(100.0, 101.0, n)
        )
        reports.append(
            evaluate_oxygen_criterion(
                result, criterion(), interpolation="linear_between_native_output_samples"
            )
        )
    exact = 100.0 + math.log(0.21 / 0.195) / 0.2
    coarse, fine = (r.crossings[0] for r in reports)
    assert fine.lower_time_s <= exact <= fine.upper_time_s
    assert abs(fine.linearly_estimated_time_s - exact) < abs(
        coarse.linearly_estimated_time_s - exact
    )
    assert abs(reports[-1].reconstructed_deficit_duration_s - (101 - exact)) < 0.0002
    assert reports[-1].room_result.native_traces


@pytest.mark.parametrize(
    "changes",
    [
        dict(quantity="mass_fraction"),
        dict(threshold=19.5),
        dict(comparator="above"),
        dict(maximum_pressure_pa=1.0),
        dict(authority_reference=""),
    ],
)
def test_criterion_quantity_units_comparator_and_scope_are_explicit(changes):
    with pytest.raises(ValueError):
        criterion(**changes)


def test_criterion_elevation_pressure_and_interpolation_cannot_be_inferred(setup):
    result = run(setup)
    with pytest.raises(ValueError, match="elevation"):
        evaluate_oxygen_criterion(
            result,
            criterion(minimum_elevation_m=10.0),
            interpolation="linear_between_native_output_samples",
        )
    with pytest.raises(ValueError, match="pressure"):
        evaluate_oxygen_criterion(
            result,
            criterion(maximum_pressure_pa=100000.0),
            interpolation="linear_between_native_output_samples",
        )
    with pytest.raises(ValueError, match="explicitly"):
        evaluate_oxygen_criterion(result, criterion(), interpolation="native-exact-events")


@pytest.mark.parametrize(
    "mutation",
    ["enthalpy", "basis", "phase", "cold", "clock", "frame", "window", "no-zero-evidence"],
)
def test_source_reference_phase_clock_and_unobserved_tails_reject(setup, mutation):
    admission = feed(setup)
    if mutation == "enthalpy":
        admission = replace(
            admission,
            source=replace(
                admission.source,
                state=replace(
                    admission.source.state,
                    enthalpy_j_kg=admission.source.state.enthalpy_j_kg + 100.0,
                ),
            ),
        )
    elif mutation == "basis":
        admission = replace(
            admission,
            source=replace(
                admission.source,
                state=replace(
                    admission.source.state,
                    basis=replace(admission.source.state.basis, spin_composition="para"),
                ),
            ),
        )
    elif mutation == "phase":
        admission = replace(
            admission,
            source=replace(
                admission.source,
                state=replace(admission.source.state, phase="liquid", vapor_mass_fraction=0.0),
            ),
        )
    elif mutation == "cold":
        admission = replace(
            admission,
            source=replace(
                admission.source, state=replace(admission.source.state, temperature_k=20.0)
            ),
        )
    elif mutation in {"clock", "frame"}:
        admission = feed(setup, **{mutation: "different"})
    else:
        admission = feed(
            setup,
            edges=(100.0, 100.5),
            outside=None if mutation == "no-zero-evidence" else "declared-zero",
            end="window_end" if mutation == "window" else "isolation",
        )
    with pytest.raises(OxygenRoomError) as error:
        run(setup, feeds=(admission,))
    assert error.value.feeds[0] is admission
    assert error.value.__cause__ is not None


def test_source_actual_type_and_missing_state_reject(setup):
    admission = feed(setup)
    with pytest.raises(TypeError, match="actual finite"):
        replace(admission, source=replace(admission.source, state=None))


def test_cached_factory_phase_cannot_alias_prior_native_partitions(setup):
    actual = setup[0]()
    cached = (lambda: actual, setup[1], setup[2])
    with pytest.raises(OxygenRoomError, match="fresh across") as error:
        run(cached, events=(100.5,))
    assert error.value.native_phases[0] is actual


def test_provider_reference_cannot_be_relabelled_even_with_matching_source_label(setup):
    admission = feed(setup)
    false_basis = replace(admission.properties.basis, reference_id="unrelated-sensible-zero")
    admission.properties._basis = false_basis
    admission = replace(
        admission,
        source=replace(admission.source, state=replace(admission.source.state, basis=false_basis)),
    )
    with pytest.raises(OxygenRoomError, match="relabeled"):
        run(setup, feeds=(admission,))


def test_live_callback_mutation_is_rejected_with_actual_native_owner(setup):
    def bad(t, phase):
        phase.TP = 340.0, phase.P
        return 0.0

    with pytest.raises(OxygenRoomError, match="mutated") as error:
        run(setup, exhausts=(vent(bad),))
    assert isinstance(error.value.failed_native.network, ct.ReactorNet)
    assert error.value.native_state is not None
    assert error.value.failure_time_s is not None
    assert error.value.__cause__.native is error.value.failed_native


def test_source_mutation_after_actual_physical_batch_cannot_return_mislabeled_result(setup):
    admission = feed(setup)

    def mutate_source(t, phase):
        admission.source.mass_kg.setflags(write=True)
        admission.source.mass_kg[0] = 0.5
        return 0.0

    with pytest.raises(OxygenRoomError, match="Source contents") as error:
        run(setup, feeds=(admission,), exhausts=(vent(mutate_source),))
    assert len(error.value.completed_traces) == 1
    assert error.value.completed_traces[0].integral("inlet:feed:H2-source:mass")[
        -1
    ] == pytest.approx(0.001, abs=1e-12)
    assert isinstance(error.value.failed_native.reactor, ct.ExtensibleIdealGasReactor)


def test_second_partition_native_domain_failure_retains_first_real_trace_and_failure_state(setup):
    admission = feed(setup, edges=(100.0, 100.5, 101.0), mass=(0.0, 1.0))
    narrow = (setup[0], replace(setup[1], maximum_pressure_pa=102000.0), setup[2])
    # The source uses the same narrow mechanism declaration and remains at its
    # admitted feed pressure, within this version's envelope.
    phase = narrow[0]()
    properties = CanteraFrozenGasProperties(phase, narrow[1], {"H2": 1.0})
    source = replace(admission.source, state=properties.state_pt(101500.0, 330.0))
    admission = OxygenFeedAdmission(source, properties, "declared-native-source")
    with pytest.raises(OxygenRoomError, match="domain") as error:
        run(narrow, feeds=(admission,))
    assert len(error.value.completed_traces) == 1
    assert error.value.completed_traces[0].time_s[-1] == 100.5
    assert isinstance(error.value.failed_native.network, ct.ReactorNet)


def test_post_run_audit_failure_retains_completed_result_and_original_objects(setup):
    settings = OxygenRoomSettings(
        mass_absolute_budget_kg=1e-30,
        energy_absolute_budget_j=1e-30,
        pressure_absolute_budget_pa=1e-30,
        relative_audit_budget=1e-30,
    )
    with pytest.raises(OxygenRoomError, match="gate failed") as error:
        run(setup, feeds=(feed(setup),), settings=settings)
    assert error.value.completed_result is not None
    assert error.value.completed_result.native[0] is error.value.failed_native
    assert error.value.completed_traces


def test_result_verification_returns_actual_original_and_preserves_criterion_input(setup):
    result = run(setup)
    assert verify_oxygen_room_result(result) is result
    screen = evaluate_oxygen_criterion(
        result, criterion(), interpolation="linear_between_native_output_samples"
    )
    assert screen.room_result is result
    assert screen.reconstructed_deficit_duration_s == 0.0


@pytest.mark.parametrize(
    "field_name",
    [
        "wet_oxygen_mole_fraction",
        "dry_oxygen_mole_fraction",
        "oxygen_partial_pressure_pa",
        "oxygen_inventory_kg",
        "time_s",
        "requested_time_s",
        "frame",
        "clock",
        "receptor",
        "snapshots",
        "binding",
    ],
)
def test_criterion_rejects_replaced_summary_clock_context_or_native_snapshot(setup, field_name):
    actual = run(setup)
    if field_name in {"frame", "clock", "receptor"}:
        changed = replace(
            actual,
            region=replace(actual.region, **{field_name + "_id": "different-declared-context"}),
        )
    elif field_name == "snapshots":
        changed = replace(actual, snapshots=(replace(actual.snapshots[0]), *actual.snapshots[1:]))
    elif field_name == "binding":
        changed = replace(actual, _binding=None)
    else:
        values = getattr(actual, field_name)
        changed = replace(
            actual, **{field_name: values + 10 if "time" in field_name else np.zeros_like(values)}
        )
    with pytest.raises(OxygenResultVerificationError) as error:
        evaluate_oxygen_criterion(
            changed, criterion(), interpolation="linear_between_native_output_samples"
        )
    assert error.value.supplied is changed
    assert error.value.native_traces is actual.native_traces
    assert error.value.__cause__ is not None


def test_current_criterion_fields_are_revalidated_after_mutation(setup):
    actual, screen = run(setup), criterion()
    object.__setattr__(screen, "threshold", float("nan"))
    with pytest.raises(ValueError, match="finite"):
        evaluate_oxygen_criterion(
            actual, screen, interpolation="linear_between_native_output_samples"
        )


def test_inplace_summary_change_and_different_actual_native_trace_are_rejected(setup):
    actual, other = run(setup), run(setup)
    with pytest.raises(OxygenResultVerificationError, match="trace identities"):
        verify_oxygen_room_result(replace(actual, native_traces=other.native_traces))
    actual.wet_oxygen_mole_fraction.setflags(write=True)
    actual.wet_oxygen_mole_fraction[:] = 0.0
    with pytest.raises(OxygenResultVerificationError, match="summary"):
        verify_oxygen_room_result(actual)
