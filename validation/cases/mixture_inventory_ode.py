"""Deferred adaptive mixture V/U ODE contracts."""

from math import fsum

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Synthetic H2/N2 mixture states are software fixtures, not measured separator data.",
    "SciPy owns adaptive time integration; CoolProp supplies composition-specific V/U equilibrium flashes.",
    "Only a bounded two-phase domain is admitted and accepted quality thresholds terminate the run.",
    "No receiving native engine, phase-appearance model, wall state, or experimental qualification is claimed.",
)


def cases():
    return (
        ValidationCase(
            identifier="finite-mixture-ode-continuous-feed",
            profile="mixture-vle",
            entrypoint=__name__ + ":validate_ode",
            parameters={"scenario": "feed"},
            invariants=("adaptive-states-reflash-current-overall-composition",
                        "species-resolved-mass-and-first-law-ledgers-close",
                        "composition-provider-is-rebuilt-after-inventory-change",
                        "solver-diagnostics-and-accepted-prefix-retained",
                        "solver-state-snapshot-cannot-be-made-writable"),
        ),
        ValidationCase(
            identifier="finite-mixture-ode-no-transfer-invariance",
            profile="mixture-vle",
            entrypoint=__name__ + ":validate_ode",
            parameters={"scenario": "isolated"},
            invariants=("zero-boundary-rates-preserve-component-and-energy-stocks",
                        "quality-events-remain-inactive-inside-declared-domain",
                        "adaptive-trace-is-current-and-conservative"),
        ),
        ValidationCase(
            identifier="finite-mixture-ode-quality-event-localization",
            profile="mixture-vle",
            entrypoint=__name__ + ":validate_ode",
            parameters={"scenario": "quality-event"},
            invariants=("interior-vapor-quality-event-is-terminal",
                        "event-time-matches-final-accepted-flash",
                        "event-prefix-retains-integrated-first-law-ledger"),
        ),
    )


def validate_ode(*, work_directory, scenario="isolated", **parameters):
    del work_directory, parameters

    from h2physics.thermo import MixtureODEDiagnostics

    for status, event_name, event_time in (
        ("completed", "quality-lower-bound", 0.5),
        ("event", None, None),
        ("event", "", 0.5),
        ("rhs_failure", "quality-lower-bound", 0.5),
    ):
        try:
            MixtureODEDiagnostics(status, "synthetic admission", "BDF", 0, 0, 0, 0,
                                  event_name, event_time)
        except ValueError:
            pass
        else:
            raise AssertionError("Contradictory mixture event diagnostics were admitted")

    from h2physics.mixtures import GasComposition
    from h2physics.thermo import (
        CoolPropMixtureProperties,
        MixtureBoundaryRates,
        MixtureODEInputs,
        MixtureProviderTemplate,
        run_mixture_vessel_ode,
    )

    species = ("H2", "N2")
    masses = (2.01588e-3, 28.0134e-3)
    composition = GasComposition("synthetic-mixture-ode-start", species, (.5, .5), masses)
    initial_provider = CoolPropMixtureProperties(
        composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    partition = initial_provider.phase_partition_pq(
        5.0e6, .5, component_mole_balance_tolerance=1e-7)
    initial_amounts = partition.split_moles(2.0)
    volume = fsum(initial_amounts.phase_volumes_m3)
    initial_u = initial_amounts.total_internal_energy_j
    template = MixtureProviderTemplate(
        species, masses, ("Hydrogen", "Nitrogen"),
        energy_reference_id="synthetic-coolprop-heos-common-reference",
    )
    feed_rate = 1e-6 if scenario == "feed" else 0.
    heat_rate = -100. if scenario == "quality-event" else 0.
    vapor_feed_composition = partition.vapor_mole_fractions
    feed_molar_mass = fsum(x * mw for x, mw in zip(vapor_feed_composition, masses, strict=True))
    feed_h_w = feed_rate * feed_molar_mass * partition.vapor_enthalpy_j_kg

    def boundary_rates(_state):
        return MixtureBoundaryRates(
            liquid_feed_mol_s=(0., 0.),
            vapor_feed_mol_s=tuple(feed_rate * x for x in vapor_feed_composition),
            liquid_feed_enthalpy_w=0.,
            vapor_feed_enthalpy_w=feed_h_w,
            liquid_outlet_mol_s=0., vapor_outlet_mol_s=0.,
            heat_into_vessel_w=heat_rate, work_into_vessel_w=0.,
            evidence_id="synthetic-fixed-hydrogen-feed-v1",
            energy_reference_id="synthetic-coolprop-heos-common-reference",
        )

    inputs = MixtureODEInputs(
        template=template,
        initial_component_moles=initial_amounts.component_moles,
        initial_internal_energy_j=initial_u,
        vessel_volume_m3=volume,
        start_time_s=0., end_time_s=1.,
        integration_boundaries_s=(0., .5, 1.),
        pressure_bounds_pa=(4.0e6, 6.0e6),
        flash_quality_bounds=(.2, .8),
        terminal_quality_bounds=((.499, .75) if scenario == "quality-event" else (.25, .75)),
        initial_guesses=((4.9e6, .45), (5.1e6, .55)),
        boundary_rates=boundary_rates,
        boundary_rate_evidence_id="synthetic-fixed-hydrogen-feed-v1",
        branch_evidence_id="synthetic-bounded-two-phase-neighborhood-v1",
        run_id="synthetic-adaptive-mixture-vu",
        minimum_component_moles=1e-8,
        maximum_step_s=.1,
        relative_tolerance=1e-6,
        component_mole_absolute_tolerance=1e-9,
        energy_absolute_tolerance_j=1e-3,
        volume_absolute_tolerance_m3=1e-9,
        phase_mole_balance_tolerance=1e-7,
    )
    trace = run_mixture_vessel_ode(inputs)
    assert trace.require_current() is trace
    assert not trace.solver_values.flags.writeable
    try:
        trace.solver_values.setflags(write=True)
    except ValueError:
        pass
    else:
        raise AssertionError("The public solver snapshot must be bytes-backed read-only")
    assert trace.require_current() is trace
    assert trace.accepted[0].cumulative_inlet_component_moles == (0., 0.)
    assert trace.accepted[0].cumulative_outlet_component_moles == (0., 0.)
    assert trace.accepted[0].cumulative_energy_into_vessel_j == 0.
    assert trace.diagnostics.attempted_rhs_calls > 0
    inventories = trace.component_inventory_history()
    energies = trace.boundary_energy_history()
    assert inventories["species"] == species
    assert inventories["component_moles"].shape == (len(trace.accepted), len(species))
    assert tuple(inventories["component_moles"][-1]) == trace.accepted[-1].admission.total_component_moles
    assert energies["net_energy_into_vessel_j"][-1] == trace.accepted[-1].cumulative_energy_into_vessel_j
    assert not inventories["component_moles"].flags.writeable
    for index, molar_mass in enumerate(masses):
        assert inventories["component_mass_kg"][-1, index] == (
            inventories["component_moles"][-1, index] * molar_mass)
    if scenario == "quality-event":
        assert trace.diagnostics.status == "event"
        assert trace.diagnostics.event_name == "quality-lower-bound"
        assert trace.diagnostics.event_time_s == trace.accepted[-1].time_s
        assert 0. < trace.diagnostics.event_time_s < inputs.end_time_s
    else:
        assert trace.diagnostics.status == "completed"
    assert trace.diagnostics.accepted_step_count == len(trace.accepted) - 1
    final = trace.accepted[-1]
    if scenario == "feed":
        assert final.admission.total_component_moles[0] > initial_amounts.component_moles[0]
        assert final.admission.total_component_moles[1] > initial_amounts.component_moles[1]
        assert final.provider is not trace.accepted[0].provider
        assert final.provider.composition_sha256 != trace.accepted[0].provider.composition_sha256
    elif scenario == "isolated":
        from dataclasses import replace

        try:
            run_mixture_vessel_ode(replace(inputs, terminal_quality_bounds=(.21, .3)))
        except ValueError as error:
            assert "Initial vapor quality" in str(error)
        else:
            raise AssertionError("A run started outside its terminal quality interval")
        for before, after in zip(initial_amounts.component_moles,
                                 final.admission.total_component_moles, strict=True):
            assert abs(after - before) <= inputs.component_mole_absolute_tolerance
        assert abs(final.admission.target_internal_energy_j - initial_u) <= inputs.energy_absolute_tolerance_j
    return ValidationOutcome(True, {
        "status": trace.diagnostics.status,
        "accepted_steps": trace.diagnostics.accepted_step_count,
        "function_evaluations": trace.diagnostics.function_evaluations,
        "initial_pressure_pa": trace.accepted[0].flash.pressure_pa,
        "final_pressure_pa": final.flash.pressure_pa,
        "final_internal_energy_j": final.admission.target_internal_energy_j,
        "final_component_moles": final.admission.total_component_moles,
    }, LIMITS)
