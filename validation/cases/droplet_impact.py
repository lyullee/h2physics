"""Ten deferred impact cases; import/discovery executes no native physics."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

STATUS = "defined_not_executed"
LIMITATIONS = (
    "Authored coefficients/capacity; no qualified LH2 impact or material fit.",
    "Lumped saturated contact, passive collision, finite recoil and fixed zero-work mount.",
    "Dry patch clears to a separate receiver; wetting/film/splash/condensation not solved.",
    "Pool handoff uses a separate explicitly owned thermal continuation, not this finite patch.",
)


def _make(**parameters):
    from examples.droplet_impact import build_model, incident_trace

    model = build_model(**parameters)
    return model, incident_trace(model)


def _check(model, trace):
    assert trace.status == "implemented_unverified" and trace.native_property_owner is model.properties
    assert abs(trace.mass_residual_kg) <= model.tolerances.mass_kg
    assert abs(trace.total_energy_residual_j) <= model.tolerances.energy_j
    for step in trace.steps:
        assert step.context.incident_trace.native_result.success
        assert abs(step.total_energy_residual_j) <= model.tolerances.energy_j
        assert max(abs(x) for x in step.mechanical.momentum_residual_kg_m_s) <= model.tolerances.momentum_kg_m_s
        assert step.wall_final_temperature_k >= step.context.liquid_state.temperature_k
        assert step.deposited_batch.velocity_m_s == (0., 0., 0.)
        assert step.ambient_pressure_work_into_j <= 0.
    assert not trace.regime_prediction_solved and not trace.simultaneous_pool_continuation_solved


def validate_baseline(*, work_directory, **parameters):
    model, incident = _make(**parameters)
    trace = model.run((incident,))
    _check(model, trace)
    step = trace.steps[0]
    assert 0 < trace.vapor_mass_kg < incident.states[-1].mass_kg
    assert 0 < trace.deposited_mass_kg < trace.total_incident_mass_kg
    assert trace.rebound_mass_kg > 0
    assert step.native_root_result.converged and step.trials
    assert step.context.incident_trace is incident
    m, s = step.mechanical, step.context
    expected_wall = (m.total_heat_into_patch_j-step.latent_heat_j)/model.patch.heat_capacity_j_k
    assert abs((step.wall_final_temperature_k-s.wall_temperature_k)-expected_wall) < 1e-10
    return ValidationOutcome(True, {"vapor_mass_kg": trace.vapor_mass_kg,
        "deposited_mass_kg": trace.deposited_mass_kg, "wall_final_k": trace.final_wall_temperature_k,
        "total_U_residual_j": trace.total_energy_residual_j}, LIMITATIONS)


def validate_elastic_limit(*, work_directory, **parameters):
    from examples.droplet_impact import authored_outcome

    outcome = authored_outcome(conductance_w_k=0., deposited_fraction=0., normal_restitution=1.)
    model, incident = _make(outcome=outcome, **parameters)
    trace = model.run((incident,))
    _check(model, trace)
    step, mass, effective_mass = trace.steps[0], incident.states[-1].mass_kg, model.patch.effective_recoil_mass_kg
    expected_rebound = (effective_mass-mass)/(effective_mass+mass)
    expected_recoil = -2*mass/(effective_mass+mass)
    assert trace.vapor_mass_kg == 0. and trace.deposited_mass_kg == 0.
    assert abs(step.mechanical.rebound_velocity_m_s[2]-expected_rebound) < 1e-12
    assert abs(step.mechanical.intermediate_recoil_velocity_m_s[2]-expected_recoil) < 1e-12
    assert abs(step.mechanical.collision_dissipation_j) <= model.tolerances.energy_j
    assert step.mechanical.arrest_dissipation_j > 0
    return ValidationOutcome(True, {"rebound_m_s": expected_rebound,
        "recoil_m_s": expected_recoil, "ground_arrest_heat_j": step.mechanical.arrest_dissipation_j}, LIMITATIONS)


def validate_zero_contact_heat(*, work_directory, **parameters):
    from examples.droplet_impact import authored_outcome

    outcome = replace(authored_outcome(conductance_w_k=0.),
                      vapor_velocity_relative_to_recoil_m_s=(0., 0., 0.))
    model, incident = _make(outcome=outcome, **parameters)
    trace = model.run((incident,))
    _check(model, trace)
    step = trace.steps[0]
    assert trace.vapor_mass_kg == 0. and step.latent_heat_j == 0.
    assert step.wall_final_temperature_k >= model.patch.initial_temperature_k
    assert trace.deposited_mass_kg+trace.rebound_mass_kg == trace.total_incident_mass_kg
    return ValidationOutcome(True, {"zero_G_vapor_kg": trace.vapor_mass_kg,
        "mechanical_heat_j": step.mechanical.total_heat_into_patch_j}, LIMITATIONS)


def validate_dryout(*, work_directory, **parameters):
    from examples.droplet_impact import authored_outcome

    model, incident = _make(outcome=authored_outcome(conductance_w_k=1., contact_duration_s=1.),
                            heat_capacity_j_k=1., **parameters)
    trace = model.run((incident,))
    _check(model, trace)
    step = trace.steps[0]
    assert step.dryout and step.active_boiling_duration_s < step.outcome.contact_duration_s
    assert trace.vapor_mass_kg == trace.total_incident_mass_kg
    assert trace.deposited_mass_kg == trace.rebound_mass_kg == 0.
    assert step.contact_end_s < step.context.incident.time_s+step.outcome.contact_duration_s
    return ValidationOutcome(True, {"dryout_duration_s": step.active_boiling_duration_s,
        "remaining_wall_k": step.wall_final_temperature_k}, LIMITATIONS)


def validate_refinement(*, work_directory, **parameters):
    from examples.droplet_impact import incident_trace
    from h2physics.adapters.droplet_impact import ImpactTolerances

    coarse, incident = _make(tolerances=ImpactTolerances(root_mass_kg=2e-15), **parameters)
    fine, _ = _make(tolerances=ImpactTolerances(root_mass_kg=1e-17), **parameters)
    a = coarse.run((incident,))
    b = fine.run((incident_trace(fine, maximum_step_s=.005),))
    _check(coarse, a)
    _check(fine, b)
    error = abs(a.vapor_mass_kg-b.vapor_mass_kg)
    assert error < 1e-12
    assert abs(a.final_wall_temperature_k-b.final_wall_temperature_k) < 1e-5
    return ValidationOutcome(True, {"refined_vapor_difference_kg": error}, LIMITATIONS)


def validate_missing_heat(*, work_directory, **parameters):
    from h2physics.adapters.droplet_impact import SurfaceImpactError

    model, incident = _make(wall_temperature_k=18., **parameters)
    try:
        model.run((incident,))
    except SurfaceImpactError as error:
        assert error.cause is error.__cause__ and error.incident is incident
        assert "heat" in str(error) and not error.completed_steps
        return ValidationOutcome(True, {"cold_wall_rejected": True}, LIMITATIONS)
    raise AssertionError("Missing finite wall heat was silently supplied")


def validate_prefix_failure(*, work_directory, **parameters):
    from examples.droplet_impact import authored_outcome, incident_trace
    from h2physics.adapters.droplet_impact import QualifiedImpactClosure, SurfaceImpactError

    model, first = _make(**parameters)
    original = model.closure
    overspeed = replace(authored_outcome(), vapor_velocity_relative_to_recoil_m_s=(0., 0., 1e3))
    def callback(context):
        return authored_outcome() if context.incident.time_s < 103. else overspeed

    closure = QualifiedImpactClosure(original.qualification, callback, (original, overspeed))
    modified, _ = _make(closure=closure, **parameters)
    second = incident_trace(modified, start_s=103.)
    try:
        modified.run((first, second))
    except SurfaceImpactError as error:
        assert len(error.completed_steps) == 1 and error.incident is second
        assert error.outcome is overspeed and error.cause is error.__cause__
        assert error.trials and "mechanical work" in str(error)
        return ValidationOutcome(True, {"completed_prefix": len(error.completed_steps)}, LIMITATIONS)
    raise AssertionError("Unprovided active vapor kinetic energy was accepted")


def validate_intercontact_energy(*, work_directory, **parameters):
    from examples.droplet_impact import authored_intercontact_heat, incident_trace

    model, first = _make(intercontact_heat=authored_intercontact_heat, **parameters)
    second = incident_trace(model, start_s=103.)
    trace = model.run((first, second))
    _check(model, trace)
    first_step, second_step = trace.steps
    capacity = model.patch.heat_capacity_j_k
    expected_second_start = first_step.wall_final_temperature_k + 0.001/capacity
    assert first_step.intercontact_thermal.heat_into_patch_j == 0.001
    assert second_step.intercontact_thermal.heat_into_patch_j == 0.001
    assert abs(second_step.context.wall_temperature_k-expected_second_start) < 1e-10
    assert abs(trace.total_energy_residual_j) <= model.tolerances.energy_j
    assert abs(sum(step.total_energy_residual_j for step in trace.steps)
               - trace.total_energy_residual_j) <= model.tolerances.energy_j
    return ValidationOutcome(True, {"intercontact_heat_into_j": sum(
        step.intercontact_thermal.heat_into_patch_j for step in trace.steps),
        "global_total_U_residual_j": trace.total_energy_residual_j}, LIMITATIONS)


def validate_history_issuer(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.droplet_impact import SurfaceImpactTrace

    model, incident = _make(**parameters)
    trace = model.run((incident,))
    assert trace.require_current() is trace
    try:
        replace(trace, deposited_mass_kg=trace.deposited_mass_kg + 1e-9)
    except TypeError:
        cloned_history_rejected = True
    else:
        raise AssertionError("A used impact-history issuer token admitted a replacement summary")
    try:
        SurfaceImpactTrace(
            trace.patch, trace.closure, trace.native_property_owner, trace.steps,
            trace.final_wall_temperature_k, trace.total_incident_mass_kg,
            trace.deposited_mass_kg, trace.rebound_mass_kg, trace.vapor_mass_kg,
            trace.mass_residual_kg, trace.total_energy_residual_j,
        )
    except TypeError:
        direct_history_rejected = True
    else:
        raise AssertionError("Direct construction admitted a caller-authored impact summary")
    try:
        object.__setattr__(trace, "deposited_mass_kg", trace.deposited_mass_kg + 1e-9)
        trace.require_current()
    except ValueError:
        post_issue_mutation_rejected = True
    else:
        raise AssertionError("Freshness check accepted a mutated impact-history summary")
    return ValidationOutcome(True, {
        "original_history_current": True,
        "replacement_rejected": cloned_history_rejected,
        "direct_construction_rejected": direct_history_rejected,
        "post_issue_mutation_rejected": post_issue_mutation_rejected,
    }, LIMITATIONS)


def validate_native_pool_initialization(*, work_directory, **parameters):
    try:
        from dynamiclh2poolx import FixedAreaPoolConfig, Substrate
    except ModuleNotFoundError as error:
        if error.name != "dynamiclh2poolx":
            raise
        raise RuntimeError(
            "impact-native-pool requires the declared optional 'pool' extra "
            "(install h2physics[pool]); no internal or alternate pool solver is substituted"
        ) from error

    from h2physics.adapters.droplet_impact import prepare_native_fixed_area_pool

    model, incident = _make(**parameters)
    trace = model.run((incident,))
    _check(model, trace)
    config = FixedAreaPoolConfig(area_m2=.01, initial_liquid_mass_kg=0.,
        substrate=Substrate("authored-separate-pool-substrate", .2, 1e-7),
        ambient_temperature_K=80., ambient_pressure_Pa=101325.,
        critical_heat_flux_W_m2=None, initial_thermal_age_s=.01)
    original = trace.steps[0]
    changed = replace(original, deposited_batch=replace(original.deposited_batch,
        mass_kg=2*original.deposited_batch.mass_kg))
    try:
        prepare_native_fixed_area_pool(changed, config, impact_owner=model,
            separate_continuation_heat_owner=config.substrate,
            continuation_evidence_id="reject-changed-cached-stock")
    except ValueError as error:
        assert "original owner-issued" in str(error)
    else:
        raise AssertionError("A cloned cached step promoted unrelated initial pool stock")
    saved_native_mass = incident.native_result.y[6, -1]
    try:
        incident.native_result.y[6, -1] = 2*saved_native_mass
        try:
            prepare_native_fixed_area_pool(original, config, impact_owner=model,
                separate_continuation_heat_owner=config.substrate,
                continuation_evidence_id="reject-changed-native-incident-cache")
        except ValueError as error:
            assert "native incident evidence changed" in str(error)
        else:
            raise AssertionError("Changed native incident arrays retained an accepted pool handoff")
    finally:
        incident.native_result.y[6, -1] = saved_native_mass
    prepared = prepare_native_fixed_area_pool(trace.steps[0], config,
        impact_owner=model,
        separate_continuation_heat_owner=config.substrate,
        continuation_evidence_id="authored-distinct-substrate-heat-owner-not-impact-wall-reset")
    assert prepared.native_config.initial_liquid_mass_kg == trace.deposited_mass_kg
    assert prepared.native_config is not config
    assert prepared.batch.incident_trace is incident
    assert prepared.impact_owner is model and prepared.impact_step is original
    assert not prepared.finite_patch_thermal_continuation_solved
    native = prepared.native_runner(prepared.native_config, prepared.native_zero_inflow, (0., .01, .1))
    last = native.ledger[-1]
    residual = trace.deposited_mass_kg-last.liquid_mass_kg-last.cumulative_evaporation_kg
    assert abs(residual) < 1e-12 and abs(native.mass_balance_residual_kg) < 1e-12
    assert prepared.absolute_start_s == trace.steps[0].contact_end_s
    return ValidationOutcome(True, {"changed_cached_stock_rejected": True,
        "changed_native_incident_rejected": True,
        "native_pool_initial_stock_kg": trace.deposited_mass_kg,
        "native_pool_mass_residual_kg": residual}, LIMITATIONS)


def cases():
    definitions = (
        ("impact-baseline", "validate_baseline", ("finite-wall-phase-energy", "mount-impulse", "incident-not-deposited")),
        ("impact-elastic", "validate_elastic_limit", ("independent-two-body-elastic-limit", "finite-recoil-arrest")),
        ("impact-zero-contact", "validate_zero_contact_heat", ("zero-conductance-no-vapor",)),
        ("impact-dryout", "validate_dryout", ("finite-full-vapor-event", "latent-heat-no-clipping")),
        ("impact-refinement", "validate_refinement", ("native-flight-and-phase-root-refinement",)),
        ("impact-missing-heat", "validate_missing_heat", ("finite-wall-missing-heat-failure",)),
        ("impact-prefix", "validate_prefix_failure", ("passive-mechanical-domain", "failure-prefix-retention")),
        ("impact-intercontact-heat", "validate_intercontact_energy",
         ("explicit-integrated-gap-heat", "global-finite-wall-energy-accounting")),
        ("impact-history-issuer-integrity", "validate_history_issuer",
         ("owner-issued-sequential-history", "aggregate-ledger-recomputed-from-original-steps",
          "direct-clone-and-post-issue-mutation-rejected")),
        ("impact-native-pool", "validate_native_pool_initialization", ("actual-native-initial-stock", "separate-thermal-owner")),
    )
    return tuple(ValidationCase(identifier=name, profile="droplet-impact",
        entrypoint=f"validation.cases.droplet_impact:{entry}", parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)
