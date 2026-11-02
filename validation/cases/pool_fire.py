"""Deferred pool-fire cases; metadata/import does not execute native physics."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

STATUS = "defined_not_executed"
LIMITATIONS = (
    "Synthetic H2 net burn flux/LHV/radiative/convective fractions; no qualification.",
    "Uniform supplied ground-tangent sphere and facing ground-level vertical receptor only.",
    "Finite external conditioning budget; no fire-to-pool heat feedback or postignition spreading.",
    "Complete combustion with supplied finite O2; no mixing/ignition/dispersion prediction.",
)


def _model(**parameters):
    from examples.pool_fire import build_model

    return build_model(**parameters)


def _run(model, **parameters):
    from examples.pool_fire import run_example

    return run_example(model, **parameters)


def validate_baseline(*, work_directory, **parameters):
    model = _model(**parameters)
    trace = _run(model)
    assert trace.require_current() is trace
    from h2physics.adapters.pool_fire import PoolFireTrace

    try:
        PoolFireTrace(
            trace.seed, trace.ignition, trace.reference, trace.conditioning,
            trace.steps, trace.native_provider, trace.reaction,
            trace.initial_oxygen_mol, trace.initial_water_mol, trace.fuel_to_flame,
            _issuer=object(),
        )
    except TypeError:
        direct_issuer_rejected = True
    else:
        raise AssertionError("A caller-created token minted a pool-fire trace")
    try:
        replace(trace)
    except TypeError:
        trace_clone_rejected = True
    else:
        raise AssertionError("A copied pool-fire trace minted a second current receipt")
    from h2physics.adapters.thermal_target import incident_history_from_pool_fire
    history = incident_history_from_pool_fire(
        trace, trace.steps[0].receptors[0].receptor.identifier,
        evidence_id="authored-pool-to-target-handoff",
    )
    original_status = trace.status
    object.__setattr__(trace, "status", "stale-fixture")
    try:
        history.source_owner.require_current()
    except ValueError:
        stale_trace_rejected = True
    else:
        raise AssertionError("Thermal-target owner accepted a stale pool-fire trace")
    finally:
        object.__setattr__(trace, "status", original_status)
    assert trace.require_current() is trace
    step = trace.steps[0]
    assert trace.status == "implemented_unverified"
    assert step.native_pool_result.burned_mass_kg == model.seed.liquid_mass_kg
    assert step.remaining_liquid_kg == 0.
    assert step.active_end_s < step.stage.end_s
    assert abs(step.native_energy_residual_j) <= model.tolerances.energy_j
    assert abs(step.native_power_energy_residual_j) <= model.tolerances.energy_j
    assert abs(step.energy_partition_residual_j) <= model.tolerances.energy_j
    assert abs(step.mass_residual_kg) <= model.tolerances.mass_kg
    assert trace.fuel_to_flame.total_mass_kg == step.vaporized_and_combusted_kg
    assert trace.fuel_to_flame.mean_rates_kg_s[-1] == 0.
    assert step.receptors[0].native_sphere_result.view_factor > 0.
    assert step.receptors[0].convective_flux_w_m2 is None
    assert not trace.heat_feedback_solved and not trace.full_cryogenic_fire_chain_validated
    return ValidationOutcome(accepted=True, metrics={"burned_mass_kg": step.vaporized_and_combusted_kg,
        "active_duration_s": step.native_pool_result.effective_duration_s,
        "radiation_export_j": step.radiation_export_j,
        "receptor_incident_j_m2": step.receptors[0].incident_energy_j_m2,
        "pool_fire_trace_clone_rejected": trace_clone_rejected,
        "pool_fire_direct_issuer_rejected": direct_issuer_rejected,
        "thermal_handoff_rejects_stale_trace": stale_trace_rejected}, limitations=LIMITATIONS)


def validate_exposure_handoff(*, work_directory, **parameters):
    del work_directory
    from h2physics.adapters.hyram_exposure import exposure_history_from_pool_fire

    trace = _run(_model(**parameters))
    receptor_id = trace.steps[0].receptors[0].receptor.identifier
    history = exposure_history_from_pool_fire(trace, receptor_id,
        basis_id="native-pool-fire-incident-scalar-flux-on-declared-receptor",
        evidence_id="hangang-pool-fire-to-exposure-adapter-contract")
    assert history.interpolation == "left_hold"
    assert history.quantity == "incident_radiant_flux" and history.unit == "W/m2"
    assert history.clock_id == trace.seed.location.clock_id
    assert history.source_id == trace.seed.location.source_id
    assert history.receptor.position_m == tuple(trace.steps[0].receptors[0].receptor.position_m)
    assert len(history.values) == len(history.time_s)-1
    assert history.input_evidence_ids[0] == "hangang-pool-fire-to-exposure-adapter-contract"
    assert history.input_evidence_ids[1] == trace.seed.evidence_id
    assert trace.require_current() is trace
    return ValidationOutcome(True, {"interval_count": len(history.values),
        "history_sha256": history.content_sha256,
        "evidence_count": len(history.input_evidence_ids)},
        LIMITATIONS + ("Exposure history transfer only; no injury dose/probit or complete cryogenic fire-chain claim.",))


def validate_native_geometry_and_transmission(*, work_directory, **parameters):
    from examples.pool_fire import receptors

    model = _model(**parameters)
    first = receptors(model)[0]
    mirrored = replace(first, identifier="mirror", position_m=(-3., 0., 0.), normal_unit=(1., 0., 0.))
    clear = replace(first, identifier="clear", transmissivity=1.)
    opaque = replace(first, identifier="opaque", transmissivity=0.)
    trace = _run(model, target_receptors=(first, mirrored, clear, opaque))
    a, b, c, d = trace.steps[0].receptors
    assert abs(a.incident_flux_w_m2-b.incident_flux_w_m2) <= model.tolerances.flux_w_m2
    assert abs(a.incident_flux_w_m2-first.transmissivity*c.incident_flux_w_m2) <= model.tolerances.flux_w_m2
    assert d.incident_flux_w_m2 == 0.
    assert a.native_solid_result.heat_flux_w_m2 == a.native_sphere_result.heat_flux_w_m2
    return ValidationOutcome(accepted=True, metrics={"native_view_factor": a.native_sphere_result.view_factor,
        "opaque_flux_w_m2": d.incident_flux_w_m2}, limitations=LIMITATIONS)


def validate_deferred_stage_refinement(*, work_directory, **parameters):
    from examples.pool_fire import stages

    model = _model(**parameters)
    full = _run(model)
    original = stages(model)[0]
    refined = tuple(replace(original, identifier=f"part-{i}", start_s=100.+5*i,
                            end_s=105.+5*i) for i in range(6))
    fine = _run(model, schedule=refined)
    assert abs(full.fuel_to_flame.total_mass_kg-fine.fuel_to_flame.total_mass_kg) <= model.tolerances.mass_kg
    assert abs(sum(s.radiation_export_j for s in full.steps)
               -sum(s.radiation_export_j for s in fine.steps)) <= model.tolerances.energy_j
    assert abs(sum(s.receptors[0].incident_energy_j_m2 for s in full.steps)
               -sum(s.receptors[0].incident_energy_j_m2 for s in fine.steps)) <= 1e-5
    return ValidationOutcome(accepted=True, metrics={"refined_steps": len(fine.steps)}, limitations=LIMITATIONS)


def validate_conditioning_failure(*, work_directory, **parameters):
    from h2physics.adapters.pool_fire import PoolFireError

    model = _model(**parameters)
    try:
        _run(model, conditioning_energy_j=1., conditioning_power_w=1.)
    except PoolFireError as error:
        assert error.__cause__ is not None
        assert "native_pool_result" in error.native_attempt
        assert error.native_attempt["required_conditioning_energy_j"] > 1.
        return ValidationOutcome(accepted=True, metrics={"conditioning_rejected": True}, limitations=LIMITATIONS)
    raise AssertionError("Fire consumption silently acquired unavailable external conditioning heat")


def validate_oxygen_failure(*, work_directory, **parameters):
    from h2physics.adapters.pool_fire import PoolFireError

    model = _model(**parameters)
    try:
        _run(model, oxygen_mol=1e-9)
    except PoolFireError as error:
        assert error.__cause__ is not None and "native_pool_result" in error.native_attempt
        return ValidationOutcome(accepted=True, metrics={"finite_oxygen_rejected": True}, limitations=LIMITATIONS)
    raise AssertionError("Complete combustion consumed an unavailable oxidizer inventory")


def validate_unsupported_receptor(*, work_directory, **parameters):
    from examples.pool_fire import receptors
    from h2physics.adapters.pool_fire import PoolFireError

    model = _model(**parameters)
    raised = replace(receptors(model)[0], position_m=(3., 0., 1.))
    try:
        _run(model, target_receptors=(raised,))
    except PoolFireError as error:
        assert "ground-level" in str(error) and error.__cause__ is not None
        assert "native_pool_result" in error.native_attempt
        return ValidationOutcome(accepted=True, metrics={"unsupported_geometry_rejected": True}, limitations=LIMITATIONS)
    raise AssertionError("Native ground-level correlation was extended to an unsupported receptor")


def validate_completed_prefix_failure(*, work_directory, **parameters):
    from examples.pool_fire import stages
    from h2physics.adapters.pool_fire import PoolFireError

    model = _model(**parameters)
    original = stages(model)[0]
    first = replace(original, end_s=101.)
    second = replace(original, identifier="unsupported-second", start_s=101., sphere_diameter_m=10.)
    try:
        _run(model, schedule=(first, second))
    except PoolFireError as error:
        assert len(error.completed_steps) == 1 and error.__cause__ is not None
        assert "native_pool_result" in error.native_attempt
        return ValidationOutcome(accepted=True, metrics={"completed_prefix": len(error.completed_steps)}, limitations=LIMITATIONS)
    raise AssertionError("Inside-sphere receptor was silently accepted or completed prefix lost")


def validate_native_pool_handoff(*, work_directory, **parameters):
    from examples.pool_fire import build_native_preignition_seed

    seed = build_native_preignition_seed()
    model = _model(seed=seed, **parameters)
    trace = _run(model)
    assert trace.seed.native_pool_run is seed.native_pool_run
    assert trace.seed.preignition_evaporation is seed.preignition_evaporation
    assert trace.seed.preignition_evaporation.edges_s[-1] == trace.ignition.time_s
    assert trace.fuel_to_flame.total_mass_kg <= seed.liquid_mass_kg
    original_evidence = seed.evidence_id
    try:
        object.__setattr__(seed, "evidence_id", "changed-pool-source-evidence")
        try:
            model._guard()
        except ValueError:
            pass
        else:
            raise AssertionError("Changed pool seed provenance retained fire model admission")
    finally:
        object.__setattr__(seed, "evidence_id", original_evidence)
    assert trace.steps[-1].remaining_liquid_kg+trace.fuel_to_flame.total_mass_kg == seed.liquid_mass_kg
    return ValidationOutcome(accepted=True, metrics={"native_preignition_mass_kg": seed.liquid_mass_kg,
        "preignition_evaporated_not_reburned_kg": seed.preignition_evaporation.total_mass_kg}, limitations=LIMITATIONS)


def cases():
    definitions = (
        ("pool-fire-baseline", "validate_baseline", ("finite-native-consumption", "burnout-clock", "phase-energy", "radiation", "one-use-trace-owner", "stale-pool-to-target-source-rejected")),
        ("pool-fire-geometry", "validate_native_geometry_and_transmission", ("native-sphere-viewfactor", "transmission-symmetry")),
        ("pool-fire-refinement", "validate_deferred_stage_refinement", ("finite-stage-energy-refinement",)),
        ("pool-fire-heat-budget", "validate_conditioning_failure", ("no-invented-heat-feedback", "failure-retention")),
        ("pool-fire-oxygen", "validate_oxygen_failure", ("finite-complete-combustion",)),
        ("pool-fire-geometry-rejection", "validate_unsupported_receptor", ("native-receptor-scope",)),
        ("pool-fire-prefix", "validate_completed_prefix_failure", ("native-failure-prefix",)),
        ("pool-fire-native-pool", "validate_native_pool_handoff", ("actual-preignition-native-pool", "no-double-consumption")),
        ("pool-fire-radial-wall-handoff", "validate_radial_wall_handoff",
         ("accepted receiver clock and source owner retained", "surface projection factor and evidence retained", "radial energy closure stays within declared tolerance")),
        ("pool-fire-exposure-history-handoff", "validate_exposure_handoff",
         ("exact-receptor-clock-and-intervals", "zero-after-receptor-activity", "origin-and-input-evidence-retained")),
    )
    return tuple(ValidationCase(identifier=name, profile="pool-fire",
        entrypoint=f"validation.cases.pool_fire:{entry}", parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)



def validate_radial_wall_handoff(*, work_directory, **parameters):
    """Deferred source-specific composition contract for Hangang execution."""
    del work_directory
    from h2physics.adapters.pool_fire_radial_wall import run_pool_fire_radial_wall
    from h2physics.materials import RadialSolidMaterial, RadialThermalBoundary

    fire = _run(_model(**parameters))
    receptor_id = fire.steps[0].receptors[0].receptor.identifier
    material = RadialSolidMaterial(
        7800.0, lambda temperature: 500.0, lambda temperature: 16.0,
        "authored-pool-fire-radial-wall-steel",
        "authored-synthetic-constant-wall-properties",
    )
    result = run_pool_fire_radial_wall(
        fire, receptor_id, surface_projection_factor=0.8,
        surface_projection_evidence_id="authored-receiver-to-cylinder-surface-map",
        inner_radius_m=0.020, outer_radius_m=0.025, length_m=0.20,
        material=material, initial_temperature_k=295.0,
        inner_boundary=RadialThermalBoundary("adiabatic", 0.0,
            "authored-inner-insulation-boundary"),
        absorptivity=0.75,
        geometry_evidence_id="authored-synthetic-cylinder-geometry",
        evidence_id="hangang-pool-fire-radial-wall-contract",
        uniform_circumference_evidence_id="authored-radial-uniformity-premise",
        maximum_step_s=2.0, energy_tolerance_j=100.0, cells=8,
    )
    result.require_current()
    assert result.fire is fire
    assert result.radial_trace.incident.source_owner is fire
    assert result.radial_trace.incident.clock_id == fire.seed.location.clock_id
    assert result.radial_trace.incident.incident_flux_w_m2[0] == (
        result.incident_history.incident_flux_w_m2[0]*0.8)
    assert result.radial_trace.geometry_evidence_id == "authored-synthetic-cylinder-geometry"
    return ValidationOutcome(True, {
        "receptor_id": receptor_id,
        "interval_count": len(result.projected_history.incident_flux_w_m2),
        "absorbed_wall_j": result.radial_trace.absorbed_incident_j,
        "outer_heat_residual_j": result.radial_trace.outer_heat_residual_j,
    }, LIMITATIONS + (
        "Pool-fire receiver-to-radial-wall projection is caller supplied; no fire-wall view factor or damage model.",))
