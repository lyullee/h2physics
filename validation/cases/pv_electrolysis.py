"""PV-electrolysis component cases; discovery constructs metadata only.

Module import and cases() construct metadata only. Native model construction,
root solves and inventory calculations occur solely inside entrypoints.
"""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

STATUS = "component_contracts_not_device_validation"
LIMITS = (
    "Native CoolProp calorimetry with authored electrical settings; no device calibration.",
    "Direct DC ideal wiring/blocking; no MPPT/inverter/AC-DC rectifier.",
    "Held source stages and isothermal native H2 receiver; no continuous feedback.",
    "Declared pressurized source; external pressure work unresolved in this fixture.",
    "Required heat is not available utility; finite water/O2 are enthalpy stocks, not vessel dynamics.",
)


def _model(**parameters):
    from examples.pv_electrolysis import build_model

    return build_model(**parameters)


def _run(model, *, water_mol=2., stages=None):
    from examples.pv_electrolysis import run_example

    return run_example(model, stages, water_mol=water_mol)


def _outcome(trace):
    return ValidationOutcome(accepted=True, metrics={
        "hydrogen_produced_mol": trace.final.amounts_mol["hydrogen"]-trace.initial.amounts_mol["hydrogen"],
        "receiver_final_pressure_pa": trace.final.receiver.pressure_pa,
        "maximum_caloric_residual_j": max(abs(s.caloric_residual_j) for s in trace.steps),
        "maximum_direct_dc_energy_residual_j": max(abs(s.direct_dc_energy_residual_j) for s in trace.steps),
        "maximum_mass_residual_kg": max(abs(s.mass_residual_kg) for s in trace.steps),
        "pressure_work_resolved": trace.pressure_work_resolved,
    }, limitations=LIMITS)


def validate_baseline(*, work_directory, **parameters):
    model = _model(**parameters)
    # Standard reaction heat independently anchors the common formation basis;
    # this reference check is separate from the trace's energy ledger closure.
    h_reference = model.caloric.enthalpies_j_mol(298.15, 101325.0)
    assert abs(-h_reference[0] + h_reference[1] + 0.5 * h_reference[2] - 285830.0) < 1e-7
    trace = _run(model)
    assert trace.status == "implemented_unverified"
    assert trace.final.amounts_mol["hydrogen"] > trace.initial.amounts_mol["hydrogen"]
    assert trace.final.receiver.pressure_pa > trace.initial.receiver.pressure_pa
    for step in trace.steps:
        assert step.point.native_root_result.converged
        assert abs(step.point.load_line_residual_a) <= model.domain.current_residual_a
        assert abs(step.direct_dc_energy_residual_j) <= model.domain.energy_residual_j
        assert abs(step.caloric_residual_j) <= model.domain.energy_residual_j
        assert abs(step.mass_residual_kg) <= model.domain.mass_residual_kg
        assert step.point.pv.native_system is model.system
        assert step.point.pv.native_iv_result is not None
        assert step.point.pv.native_scaled_iv is not None
        assert step.native_conversion.reaction is model.reaction
        assert step.point.undrawn_mpp_headroom_w >= -1e-8
    # Independent held-current charge/Faraday extent and finite stoichiometry.
    from h2physics.constants import FARADAY_C_MOL

    expected = sum(s.point.stack.current_a*model.stack.geometry.series_cells
        *(s.point.stage.end_s-s.point.stage.start_s)/(2*FARADAY_C_MOL) for s in trace.steps)
    assert abs(expected-(trace.final.amounts_mol["hydrogen"]-trace.initial.amounts_mol["hydrogen"])) < 1e-10
    assert abs(trace.initial.amounts_mol["water"]-trace.final.amounts_mol["water"]-expected) < 1e-10
    assert abs(trace.final.amounts_mol["oxygen"]-trace.initial.amounts_mol["oxygen"]-.5*expected) < 1e-10
    assert not trace.full_plant_energy_closed
    assert trace.require_current() is trace
    return _outcome(trace)


def validate_original_result_admission(*, work_directory, **parameters):
    from h2physics.adapters.pv_electrolysis import PVResultVerificationError

    model = _model(**parameters)
    trace = _run(model)
    assert model.verify_result(trace) is trace
    assert trace.admission.original_trace is trace
    try:
        replace(trace).require_current()
    except PVResultVerificationError as error:
        assert error.result is not trace and error.owner is model
    else:
        raise AssertionError("A reconstructed PV trace acquired original producer admission")
    caloric = model.caloric
    mutations = {
        "reference_offsets_j_mol": tuple(x + 1.0 for x in caloric.reference_offsets_j_mol),
        "species": tuple(reversed(caloric.species)),
        "fluids": tuple(reversed(caloric.fluids)),
        "temperature_bounds_k": (279.0, 361.0),
        "pressure_bounds_pa": (1e4, 6e5),
        "backend": "altered-backend",
        "version": "altered-version",
        "_states": tuple(reversed(caloric._states)),
        "_cp": None,
    }
    rejected = 0
    for name, changed in mutations.items():
        original = getattr(caloric, name)
        try:
            setattr(caloric, name, changed)
            try:
                trace.require_current()
            except PVResultVerificationError:
                rejected += 1
            else:
                raise AssertionError(f"Changed caloric definition {name} retained admission")
        finally:
            setattr(caloric, name, original)
        assert trace.require_current() is trace
    return ValidationOutcome(accepted=True, metrics={"original_result_admitted": True,
        "caloric_definition_mutations_rejected": rejected},
                             limitations=LIMITS)


def validate_dark_and_isolation(*, work_directory, **parameters):
    from examples.pv_electrolysis import source_stages

    model = _model(**parameters)
    stages = source_stages()
    dark = _run(model, stages=(replace(stages[0], effective_irradiance_w_m2=0.),))
    isolated = _run(model, stages=(replace(stages[0], enabled=False),))
    for trace in (dark, isolated):
        assert trace.final.amounts_mol == trace.initial.amounts_mol
        assert trace.steps[0].point.stack.electric_input_w == 0
        assert trace.steps[0].point.native_root_result is None
        assert trace.steps[0].point.load_line_residual_a is None
    return ValidationOutcome(accepted=True, metrics={"dark_mode": dark.steps[0].point.mode,
        "isolation_mode": isolated.steps[0].point.mode}, limitations=LIMITS)


def validate_current_envelope_failure(*, work_directory, **parameters):
    from examples.pv_electrolysis import source_stages
    from h2physics.adapters.pv_electrolysis import PVElectrolysisError

    model = _model(maximum_current_density=.001, **parameters)
    try:
        model.operating_point(source_stages()[0])
    except PVElectrolysisError as error:
        assert error.failure_code is None
        assert error.unresolved_faradaic_loss_fraction == 0.0
        assert error.unresolved_energy_path is None
        assert error.__cause__ is not None
        assert error.native_pv_state is not None and error.probes
        assert "No direct-DC" in str(error)
        return ValidationOutcome(accepted=True, metrics={"retained_root_probes": len(error.probes)},
                                 limitations=LIMITS)
    raise AssertionError("A current-limited no-root case was silently accepted")


def validate_finite_water_failure(*, work_directory, **parameters):
    from h2physics.adapters.pv_electrolysis import PVElectrolysisError

    model = _model(**parameters)
    try:
        _run(model, water_mol=1e-9)
    except PVElectrolysisError as error:
        assert error.point is not None and error.point.pv.native_iv_result is not None
        assert error.__cause__ is not None
        assert "finite" in str(error).lower()
        return ValidationOutcome(accepted=True, metrics={"completed_steps": len(error.completed_steps)},
                                 limitations=LIMITS)
    raise AssertionError("An unsupported water depletion was clipped or replenished")


def validate_pressure_and_phase_guard(*, work_directory, **parameters):
    from h2physics.adapters.pv_electrolysis import PVElectrolysisError

    model = _model(source_pressure_pa=3e4, **parameters)
    try:
        _run(model)
    except PVElectrolysisError as error:
        assert error.attempted_receiver is not None and error.native_conversion is not None
        assert "source cannot deliver" in str(error)
        assert error.__cause__ is not None
        return ValidationOutcome(accepted=True, metrics={"attempted_receiver_pa":
            error.attempted_receiver.pressure_pa}, limitations=LIMITS)
    raise AssertionError("Production bypassed the declared delivery-pressure head")


def validate_receiver_domain_failure(*, work_directory, **parameters):
    from h2physics.adapters.pv_electrolysis import PVElectrolysisError

    model = _model(maximum_receiver_pressure_pa=3e4, **parameters)
    try:
        _run(model)
    except PVElectrolysisError as error:
        assert error.attempted_receiver is not None
        assert error.__cause__ is not None
        assert error.attempted_receiver.pressure_pa > model.domain.maximum_receiver_pressure_pa
        return ValidationOutcome(accepted=True, metrics={"retained_native_pressure_pa":
            error.attempted_receiver.pressure_pa}, limitations=LIMITS)
    raise AssertionError("An out-of-domain receiver state was accepted")


def validate_missing_faradaic_heat(*, work_directory, **parameters):
    from h2physics.adapters.pv_electrolysis import PVElectrolysisError

    model = _model(faradaic_efficiency=.9, **parameters)
    try:
        _run(model)
    except PVElectrolysisError as error:
        assert error.failure_code == "unresolved_faradaic_loss_path"
        assert error.__cause__ is not None and "eta_F=1" in str(error)
        assert error.requested_faradaic_efficiency == .9
        assert abs(error.unresolved_faradaic_loss_fraction - .1) < 1e-14
        assert error.unresolved_energy_path == (
            "unallocated Faradaic-loss fate; no heat or side reaction inferred")
        return ValidationOutcome(accepted=True, metrics={
            "missing_heat_fate_rejected": True,
            "requested_faradaic_efficiency": error.requested_faradaic_efficiency,
            "unresolved_faradaic_loss_fraction": error.unresolved_faradaic_loss_fraction,
            "unresolved_energy_path_retained": True,
        }, limitations=LIMITS)
    raise AssertionError("Faradaic loss acquired an invented heat fate")


def validate_faradaic_efficiency_bounds(*, work_directory, **parameters):
    del work_directory
    from h2physics.adapters.pv_electrolysis import PVElectrolysis

    accepted = _model(faradaic_efficiency=1.0, **parameters)
    assert type(accepted) is PVElectrolysis and accepted.faradaic_efficiency == 1.0
    rejected = 0
    for value in (0.0, -0.1, 1.0001, float("nan"), float("inf")):
        try:
            _model(faradaic_efficiency=value, **parameters)
        except (TypeError, ValueError):
            rejected += 1
    assert rejected == 5
    return ValidationOutcome(accepted=True, metrics={
        "unity_efficiency_admitted": True,
        "invalid_efficiency_values_rejected": rejected,
    }, limitations=LIMITS)


def validate_stage_refinement(*, work_directory, **parameters):
    from examples.pv_electrolysis import source_stages

    first = _run(_model(**parameters))
    fine_stages = []
    for stage in source_stages():
        mid = stage.start_s+(stage.end_s-stage.start_s)/2
        fine_stages += [replace(stage, identifier=stage.identifier+"-a", end_s=mid),
                        replace(stage, identifier=stage.identifier+"-b", start_s=mid)]
    fine = _run(_model(**parameters), stages=tuple(fine_stages))
    assert abs(first.final.amounts_mol["hydrogen"]-fine.final.amounts_mol["hydrogen"]) < 1e-10
    assert abs(first.final.receiver.pressure_pa-fine.final.receiver.pressure_pa) < .01
    assert abs(sum(s.receiver_heat_into_j for s in first.steps)
               -sum(s.receiver_heat_into_j for s in fine.steps)) < 1e-5
    return ValidationOutcome(accepted=True, metrics={"refined_steps": len(fine.steps)}, limitations=LIMITS)


def validate_caloric_basis_mismatch(*, work_directory, **parameters):
    from h2physics.adapters.pv_electrolysis import PVElectrolysisError
    from h2physics.thermo import CoolPropMolarEnthalpy

    model = _model(**parameters)
    # Rebuild a legitimate owner with an incompatible caloric reference.
    original = model.caloric
    foreign = CoolPropMolarEnthalpy(
        original.species, original.fluids, original.reference_offsets_j_mol,
        basis_id="deliberately-other-reference",
        temperature_bounds_k=original.temperature_bounds_k,
        pressure_bounds_pa=original.pressure_bounds_pa,
    )
    model = type(model)(model.native, model.system, model.stack, model.reaction,
        foreign, model.gas,
        water_id=model.water_id, hydrogen_id=model.hydrogen_id, oxygen_id=model.oxygen_id,
        pressure=model.pressure, evidence=model.evidence, domain=model.domain)
    try:
        _run(model)
    except PVElectrolysisError as error:
        assert error.point is not None and error.__cause__ is not None
        assert "reference/water phase" in str(error)
        return ValidationOutcome(accepted=True, metrics={"reference_mismatch_rejected": True}, limitations=LIMITS)
    raise AssertionError("Unrelated reaction/stream energy references were combined")


def validate_profile_midpoint_stages(*, work_directory, **parameters):
    from examples.pv_electrolysis import source_profile
    from h2physics.adapters.pv_electrolysis import PVBoundaryProfile

    profile = source_profile()
    coarse = profile.stages(stack_temperature_k=298.15, maximum_gap_s=30.)
    fine = profile.stages(stack_temperature_k=298.15, maximum_gap_s=30., subdivisions_per_gap=4)
    assert len(coarse) == 2 and len(fine) == 8
    assert coarse[0].effective_irradiance_w_m2 == 800.
    assert coarse[1].effective_irradiance_w_m2 == 825.
    assert fine[0].start_s == 100. and fine[-1].end_s == 160.
    # Midpoint quadrature integrates each linear input exactly across each knot gap.
    weighted = sum(stage.effective_irradiance_w_m2 * (stage.end_s-stage.start_s) for stage in fine)
    expected = sum((a.effective_irradiance_w_m2+b.effective_irradiance_w_m2)/2
                   * (b.time_s-a.time_s) for a, b in zip(profile.samples[:-1], profile.samples[1:], strict=True))
    assert abs(weighted-expected) < 1e-9
    assert all(stage.source_id == "profile-knot-1|profile-knot-2"
               for stage in fine[:4])
    assert all(stage.source_ids == ("profile-knot-1", "profile-knot-2")
               for stage in fine[:4])
    assert all(stage.source_ids == ("profile-knot-2", "profile-knot-3")
               for stage in fine[4:])
    assert all(stage.origin == profile.origin and stage.clock_id == profile.clock_id for stage in fine)
    trace = _run(_model(**parameters), stages=fine)
    assert len(trace.steps) == len(fine) and trace.final.amounts_mol["hydrogen"] > trace.initial.amounts_mol["hydrogen"]
    try:
        PVBoundaryProfile(profile.profile_id, profile.clock_id, profile.origin,
            (profile.samples[0], profile.samples[1], profile.samples[2])).stages(
                stack_temperature_k=298.15, maximum_gap_s=29.)
    except ValueError as error:
        assert "gap" in str(error).lower()
    else:
        raise AssertionError("A wider-than-declared observation gap was interpolated")
    return ValidationOutcome(accepted=True, metrics={
        "coarse_intervals": len(coarse), "fine_intervals": len(fine),
        "irradiance_integral_wh_m2": weighted/3600.,
    }, limitations=LIMITS + ("Piecewise-linear midpoint forcing is not measured weather or continuous plant feedback.",))


def validate_duplicate_stage_identity(*, work_directory, **parameters):
    """Reject ambiguous source-stage lineage before any native solve begins."""
    from examples.pv_electrolysis import source_stages
    from h2physics.adapters.pv_electrolysis import PVElectrolysisError

    model = _model(**parameters)
    stages = source_stages()
    duplicate = (stages[0], replace(stages[1], identifier=stages[0].identifier))
    try:
        _run(model, stages=duplicate)
    except PVElectrolysisError as error:
        assert isinstance(error.__cause__, ValueError)
        assert "unique identifier" in str(error)
        assert not error.completed_steps
        return ValidationOutcome(accepted=True,
            metrics={"duplicate_stage_identity_rejected_before_solve": True},
            limitations=LIMITS + ("This is a trace-lineage contract, not process validation.",))
    raise AssertionError("Duplicate stage identifiers were admitted into the physical trace")


def cases():
    """Pure metadata. Not a verification result."""
    definitions = (
        ("pv-baseline", "validate_baseline", ("native-load-line", "charge-stoichiometry", "native-receiver", "caloric-ledger")),
        ("pv-dark-isolated", "validate_dark_and_isolation", ("no-current-no-production", "retained-off-mode")),
        ("pv-no-root", "validate_current_envelope_failure", ("finite-current-envelope", "native-failure-retention")),
        ("pv-water-depletion", "validate_finite_water_failure", ("finite-water", "no-clipping")),
        ("pv-delivery-pressure", "validate_pressure_and_phase_guard", ("no-free-pressurization", "native-state-retention")),
        ("pv-receiver-domain", "validate_receiver_domain_failure", ("native-phase-pressure-domain",)),
        ("pv-faradaic-heat", "validate_missing_faradaic_heat", ("no-invented-parasitic-heat",)),
        ("pv-faradaic-efficiency-bounds", "validate_faradaic_efficiency_bounds",
         ("unity-admitted", "zero-negative-above-unity-and-nonfinite-rejected")),
        ("pv-held-stage-refinement", "validate_stage_refinement", ("finite-charge-refinement", "receiver-energy-refinement")),
        ("pv-caloric-reference", "validate_caloric_basis_mismatch", ("reaction-stream-reference-identity",)),
        ("pv-original-result", "validate_original_result_admission", ("producer-issued-trace", "copy-rejected")),
        ("pv-profile-midpoint-stages", "validate_profile_midpoint_stages", ("bounded-input-interpolation", "midpoint-integral", "original-source-identities", "finite-ledgers")),
        ("pv-duplicate-stage-identity", "validate_duplicate_stage_identity", ("unique-trace-stage-lineage", "rejected-before-native-solve")),
    )
    return tuple(ValidationCase(identifier=name, profile="pv-electrolysis",
        entrypoint=f"validation.cases.pv_electrolysis:{entry}", parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)
