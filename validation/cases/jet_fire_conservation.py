"""Six unexecuted diagnostic cases; discovery invokes no native calculation."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

STATUS = "defined_not_executed"
LIMITATIONS = (
    "Native original jet-fire mass/caloric rejection remains; no corrected or accepted field.",
    "Common NASA caloric reference is a diagnostic interpretation, with explicit H2 spin/air-surrogate assumptions.",
    "No missing material/energy source is supplied; unresolved power is not identified as heat.",
    "Native radiation stays diagnostic; no absorbed equipment heat or measured qualification.",
)


def _source(**parameters):
    from examples.jet_fire_conservation import build_source

    return build_source(**parameters)


def _audit(source, **parameters):
    from examples.jet_fire_conservation import build_auditor

    auditor = build_auditor(**parameters)
    last = len(source.native.S)-1
    return auditor, auditor.audit(source, native_section_indices=(0, last//2, last))


def validate_retained_rejection(*, work_directory, **parameters):
    from examples.jet_fire_conservation import build_source

    baseline = build_source(native_packages=parameters.get("native_packages"),
                            upstream_temperature_k=300., ambient_temperature_k=293.15)
    assert not baseline.accepted
    assert not baseline.gates["source to conserved fuel-origin field mass"]
    assert not baseline.gates["direct EOS check of native combustion caloric equation"]
    source = _source(**parameters)
    original_fluxes = source.fuel_origin_flows_kg_s.copy()
    original_gates = dict(source.gates)
    auditor, result = _audit(source)
    assert result.source_flame is source and not result.accepted
    assert dict(source.gates) == original_gates
    assert (source.fuel_origin_flows_kg_s == original_fluxes).all()
    assert result.shared_reference_reaction is auditor.reference_reaction
    assert result.reference_reaction_delta_h_j_mol_h2 < 0
    assert all(s.fine.maximum_native_fraction_sum_defect <= result.quadrature.native_fraction_sum_budget
               for s in result.sections)
    assert not result.sampled_every_native_section
    return ValidationOutcome(True, {"prior_300K_baseline_accepted": bool(baseline.accepted),
        "warm_source_original_gates_accepted": bool(source.accepted),
        "new_accepted": result.accepted, "reference_delta_h_j_mol_h2": result.reference_reaction_delta_h_j_mol_h2,
        "source_entry_H_defect_kg_s": result.source_to_entry_hydrogen_mass_residual_kg_s}, LIMITATIONS)


def validate_quadrature(*, work_directory, **parameters):
    source = _source(**parameters)
    _, a = _audit(source, cutoff_widths=8., order=16)
    _, b = _audit(source, cutoff_widths=10., order=24)
    assert all(s.quadrature_within_budget for s in a.sections+b.sections)
    mass = max(abs(x.fine.total_mass_kg_s-y.fine.total_mass_kg_s)
               for x, y in zip(a.sections, b.sections, strict=True))
    power = max(abs(x.fine.total_excess_power_w-y.fine.total_excess_power_w)
                for x, y in zip(a.sections, b.sections, strict=True))
    assert mass <= 1e-8 and power <= 1.
    assert not a.accepted and not b.accepted
    return ValidationOutcome(True, {"cutoff_mass_difference_kg_s": mass,
        "cutoff_power_difference_w": power}, LIMITATIONS)


def validate_caloric_domain_failure(*, work_directory, **parameters):
    from examples.jet_fire_conservation import build_auditor
    from h2physics.adapters.hyram_flame_conservation import JetFireConservationError

    source = _source(**parameters)
    auditor = build_auditor(minimum_temperature_k=400.)
    last = len(source.native.S)-1
    try:
        auditor.audit(source, native_section_indices=(0, last))
    except JetFireConservationError as error:
        assert error.source_flame is source and error.cause is error.__cause__
        assert not error.completed_sections and "domain" in str(error)
        return ValidationOutcome(True, {"declared_caloric_domain_rejected": True}, LIMITATIONS)
    raise AssertionError("A direct native caloric query silently extrapolated")


def validate_owner_binding(*, work_directory, **parameters):
    from examples.jet_fire_conservation import build_auditor
    from h2physics.adapters.hyram_flame_conservation import JetFireConservationError

    source = _source(**parameters)
    auditor = build_auditor()
    last = len(source.native.S)-1
    original = auditor.caloric.enthalpies_j_mol
    auditor.caloric.enthalpies_j_mol = lambda *args: None
    try:
        try:
            auditor.audit(source, native_section_indices=(0, last))
        except JetFireConservationError as error:
            assert "ownership" in str(error) and not error.completed_sections
        else:
            raise AssertionError("Changed native caloric method binding was accepted")
    finally:
        auditor.caloric.enthalpies_j_mol = original
    changed = replace(source, mass_flow_kg_s=2*source.mass_flow_kg_s)
    try:
        auditor.audit(changed, native_section_indices=(0, last))
    except JetFireConservationError as error:
        assert "cached" in str(error) and error.source_flame is changed
    else:
        raise AssertionError("Cached source mass was silently substituted for actual native flow")
    return ValidationOutcome(True, {"method_rebinding_rejected": True,
        "changed_source_cache_rejected": True}, LIMITATIONS)


def validate_radiation_stays_diagnostic(*, work_directory, **parameters):
    source = _source(**parameters)
    auditor, result = _audit(source)
    radiation = source.irradiance([[0., 3., 2.], [1., 3., 2.]], relative_humidity=.5,
        minimum_source_distance_m=.1, allow_rejected_flame=True)
    bound = auditor.bind_native_radiation(result, radiation)
    assert bound.original_native_radiation is radiation
    assert bound.kernel_accepted and not bound.accepted
    try:
        auditor.bind_native_radiation(replace(result, unclosed_visible_energy_rate_w=0.), radiation)
    except ValueError as error:
        assert "owner-issued" in str(error)
    else:
        raise AssertionError("A replaced diagnostic cache was promoted to original evidence")
    return ValidationOutcome(True, {"native_kernel_accepted": bool(bound.kernel_accepted),
        "whole_chain_accepted": bound.accepted}, LIMITATIONS)


def validate_native_radiation_exposure_handoff(*, work_directory, **parameters):
    from h2physics.adapters.hyram_exposure import incident_history_from_hyram_radiation

    source = _source(**parameters)
    radiation = source.irradiance([[0., 3., 2.], [1., 3., 2.]], relative_humidity=.5,
        minimum_source_distance_m=.1)
    start, end = source.window.start_s, source.window.end_s
    history = incident_history_from_hyram_radiation(radiation, observer_index=1,
        start_s=start, end_s=end, receptor_id="hangang-native-radiation-receiver",
        basis_id="native-scalar-irradiance-no-absorptivity-or-plane-projection")
    assert history.source_id == source.location.source_id
    assert history.clock_id == source.window.clock_id
    assert history.support_s == (start, end)
    assert history.interpolation == "left_hold" and history.values.shape == (1,)
    assert history.values[0] == radiation.irradiance_w_m2[1]
    assert history.receptor.position_m == tuple(radiation.points_m[1])
    assert history.input_evidence_ids == (source.window.source_evidence_id,
                                           source.window.steady_evidence_id)
    return ValidationOutcome(True, {"source_native_accepted": source.accepted,
        "radiation_native_accepted": radiation.accepted,
        "history_sha256": history.content_sha256},
        ("Maps one native steady scalar irradiance to a caller-bounded held exposure interval.",
         "No transient flame, receptor projection, absorption, or injury probability is inferred."))


def validate_unclosed_power_is_not_heat(*, work_directory, **parameters):
    from h2physics.adapters.hyram_flame_conservation import JetFireConservationAdmissibilityError

    source = _source(**parameters)
    _, result = _audit(source)
    assert result.required_heat_input_w is None
    assert not result.gravitational_and_pressure_work_resolved
    assert abs(result.visible_energy_reference_sensitivities_kg_s["H"]
               -result.visible_hydrogen_flux_change_kg_s) < 1e-12
    assert abs(result.unclosed_visible_energy_rate_w-result.visible_excess_power_change_w
               -result.native_emitted_radiative_power_w) < 1e-8
    duration = source.window.end_s-source.window.start_s
    budgets = result.held_steady_window_budgets
    assert budgets["native_emitted_radiation_j"] == duration*source.emitted_radiative_power_w
    try:
        result.require_accepted()
    except JetFireConservationAdmissibilityError as error:
        assert error.result is result and error.native is source.native
    else:
        raise AssertionError("Diagnostic common-reference bookkeeping accepted a jet fire")
    return ValidationOutcome(True, {"unclosed_power_w": result.unclosed_visible_energy_rate_w,
        "native_emitted_radiation_j": budgets["native_emitted_radiation_j"]}, LIMITATIONS)


def cases():
    definitions = (
        ("jet-conservation-rejection", "validate_retained_rejection", ("unchanged-failed-native-path", "native-common-reference-reaction")),
        ("jet-conservation-quadrature", "validate_quadrature", ("independent-element-enthalpy-kinetic-quadrature", "cutoff-refinement")),
        ("jet-conservation-domain", "validate_caloric_domain_failure", ("declared-caloric-domain", "original-failure-retention")),
        ("jet-conservation-binding", "validate_owner_binding", ("native-method-and-cached-source-binding",)),
        ("jet-conservation-radiation", "validate_radiation_stays_diagnostic", ("actual-existing-native-radiation", "no-acceptance-promotion")),
        ("hyram-native-radiation-exposure-handoff", "validate_native_radiation_exposure_handoff",
         ("accepted-native-radiation-observer", "exact-steady-window-clock", "source-and-window-evidence-retained")),
        ("jet-conservation-energy", "validate_unclosed_power_is_not_heat", ("emitted-radiation-counted-once", "no-invented-heat-source")),
    )
    return tuple(ValidationCase(identifier=name, profile="jet-fire-conservation",
        entrypoint=f"validation.cases.jet_fire_conservation:{entry}", parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)
