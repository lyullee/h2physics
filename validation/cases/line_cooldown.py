"""Deferred contract for the energy-only hydrogen transfer-line cooldown estimate."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="line-cooldown-energy-bound",
        profile="thermal-utilities",
        entrypoint=__name__ + ":validate_energy_bound",
        invariants=(
            "constant solid heat capacity integrates to the exact lumped wall duty",
            "contained-fluid enthalpy change is accounted separately from wall duty",
            "minimum coolant mass closes the declared enthalpy-only energy balance",
            "additional heat and design factor are explicit and retained",
            "invalid warming targets and nonpositive coolant enthalpy rise are rejected",
            "segment IDs and evidence IDs remain explicit",
            "the result retains ordered source segments beside their per-segment duties",
            "the shared property-provider path binds pressure, basis, phase and enthalpy reference",
            "provider-backed cooldown retains exact coolant states and provider evidence",
            "a retained cooldown ledger rejects changed wall or contained-fluid callback outputs",
            "post-estimation edits to duty rows, evidence IDs or ledger fields are rejected",
            "public duty and coolant-mass property reads automatically require a current receipt",
            "provider path declarations and endpoint result bindings reject post-estimation mutation",
        ),
    ), ValidationCase(
        identifier="native-dynamic-line-coolant-audit",
        profile="thermal-utilities",
        entrypoint=__name__ + ":validate_dynamic_coolant_audit",
        invariants=(
            "the accepted native line inventory and energy balance close independently",
            "coolant mass integration uses the same operation clock and full run window",
            "native enthalpy transport and measured coolant mass imply a separate energy residual",
            "the receipt retains both native mass and energy closure residuals",
            "coolant mass refinement reports signed, absolute, normalized and interval-count changes",
            "coarse/fine comparison requires nested accepted times and a shared trajectory identity",
            "the refinement decision records the caller tolerance outcome",
            "post-comparison sample mutation invalidates the refinement and dynamic audit receipts",
            "wall ambient heat remains separate from coolant enthalpy removal",
            "negative cooling duty, incompatible basis and nonclosing native balance are rejected",
            "sampled flow reversal and caller rejection of coolant-only transport premise are rejected",
            "accepted run objects cannot be fabricated directly or mutated after native issuance",
        ),
    ))


def validate_dynamic_coolant_audit(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.adapters.lh2dt_dynamics import (
        DynamicEquipmentRun,
        DynamicEquipmentStep,
        _issue_dynamic_run,
        audit_dynamic_line_cooldown,
        compare_unidirectional_equipment_integrals,
        integrate_unidirectional_equipment_rate,
    )
    from h2physics.core import PropertyBasis
    from h2physics.dynamics import (
        ConservedInventory,
        InventoryBalance,
    )

    basis = PropertyBasis("hydrogen", "synthetic-coolant-audit", "normal")
    initial = ConservedInventory(basis, 1.0, 80_000.0, 20_000.0)
    final = ConservedInventory(basis, 1.0, 71_000.0, 18_000.0)
    balance = InventoryBalance(
        initial, final, 0.0, -11_000.0, -10_000.0, -1_000.0,
    )
    step = DynamicEquipmentStep(
        1.0, {"line": final}, {"line": balance}, object(), object(),
    )
    run_values = dict(clock_id="synthetic-line-clock", start_time_s=0.0,
                      initial_inventories={"line": initial}, initial_equipment=object(),
                      steps=(step,), transitions=())
    try:
        DynamicEquipmentRun(**run_values)
    except ValueError:
        pass
    else:
        raise AssertionError("A caller-fabricated native dynamic run was admitted")
    run = _issue_dynamic_run(**run_values)
    run.require_current()
    object.__setattr__(run, "clock_id", "mutated-clock")
    try:
        run.require_current()
    except ValueError as error:
        assert "contents changed" in str(error)
    else:
        raise AssertionError("Mutation after native run issuance was not detected")
    object.__setattr__(run, "clock_id", "synthetic-line-clock")
    run.require_current()
    mass = integrate_unidirectional_equipment_rate(
        run, lambda snapshot: 1.0, rate_unit="kg/s", integral_unit="kg",
        trajectory_id="synthetic-line-trajectory-v1",
    )
    result = audit_dynamic_line_cooldown(
        run, "line", mass, coolant_enthalpy_rise_j_kg=10_000.0,
        coolant_only_energy_transport=True,
        evidence_ids=("synthetic-native-transport-ledger", "synthetic-mass-integral"),
    )
    assert result.required_coolant_mass_kg == 1.0
    assert result.coolant_mass_residual_kg == 0.0
    assert result.coolant_energy_residual_j == 0.0
    assert result.stored_energy_drop_j == 11_000.0
    assert result.inventory_mass_residual_kg == 0.0
    assert result.inventory_energy_residual_j == 0.0
    assert result.start_time_s == 0.0 and result.end_time_s == 1.0
    assert result.ambient_heat_j == -1_000.0
    try:
        audit_dynamic_line_cooldown(
            run, "line", replace(mass, integral=replace(mass.integral, clock_id="other-clock")),
            coolant_enthalpy_rise_j_kg=10_000.0,
            coolant_only_energy_transport=True,
            evidence_ids=("synthetic-mismatch",),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A coolant integral on another clock was admitted")
    try:
        audit_dynamic_line_cooldown(
            run, "line", mass, coolant_enthalpy_rise_j_kg=10_000.0,
            coolant_only_energy_transport=False,
            evidence_ids=("synthetic-multiple-streams",),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A multiple-stream boundary was admitted as coolant-only")
    try:
        replace(result, coolant_energy_residual_j=1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("A forged cooldown energy residual was admitted")
    try:
        integrate_unidirectional_equipment_rate(
            run,
            lambda snapshot: -1.0 if snapshot is step.equipment else 1.0,
            rate_unit="kg/s", integral_unit="kg",
            trajectory_id="synthetic-line-trajectory-v1",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A reversing coolant path was admitted")
    from h2physics.adapters.lh2dt_equipment import EquipmentNetworkSnapshot

    def sampled_run(times, rates):
        samples = [EquipmentNetworkSnapshot((), index, "H2", basis.phase, 0.0, 0.0,
                                             "synthetic", "synthetic", basis)
                   for index, _time in enumerate(times)]
        steps = tuple(DynamicEquipmentStep(
            time, {"line": final}, {"line": balance}, sample, object(),
        ) for time, sample in zip(times[1:], samples[1:]))
        trajectory = _issue_dynamic_run(
            clock_id="synthetic-line-clock", start_time_s=times[0],
            initial_inventories={"line": initial}, initial_equipment=samples[0],
            steps=steps, transitions=(),
        )
        rate_by_sample = dict(zip(samples, rates))
        integral = integrate_unidirectional_equipment_rate(
            trajectory, rate_by_sample.__getitem__, rate_unit="kg/s", integral_unit="kg",
            trajectory_id="synthetic-line-trajectory-v1",
        )
        return trajectory, integral

    _coarse_run, coarse = sampled_run((0.0, 1.0), (0.0, 1.0))
    _fine_run, fine = sampled_run((0.0, 0.5, 1.0), (0.0, 0.25, 1.0))
    refinement = compare_unidirectional_equipment_integrals(
        coarse, fine, normalized_tolerance=0.3,
    )
    assert refinement.signed_change == -0.125
    assert refinement.absolute_change == 0.125
    assert refinement.normalized_change == 0.25
    assert refinement.interval_refinement_ratio == 2.0
    assert refinement.within_tolerance is True
    assert compare_unidirectional_equipment_integrals(
        coarse, fine, normalized_tolerance=0.2,
    ).within_tolerance is False
    try:
        compare_unidirectional_equipment_integrals(
            replace(coarse, trajectory_id="different-trajectory"), fine,
            normalized_tolerance=0.3,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Different physical trajectories were compared as a refinement pair")
    coarse_mid_run, coarse_mid = sampled_run(
        (0.0, 0.5, 1.0), (0.0, 0.5, 1.0),
    )
    _non_nested_run, non_nested = sampled_run(
        (0.0, 0.4, 1.0), (0.0, 0.15, 1.0),
    )
    try:
        compare_unidirectional_equipment_integrals(
            coarse_mid, non_nested, normalized_tolerance=0.3,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Non-nested time grids were admitted as refinement")
    try:
        audit_dynamic_line_cooldown(
            coarse_mid_run, "line", coarse_mid, coolant_enthalpy_rise_j_kg=10_000.0,
            coolant_only_energy_transport=True,
            evidence_ids=("synthetic-native-transport-ledger", "synthetic-wrong-run"),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("An integral from another accepted run was admitted")
    refined_audit = audit_dynamic_line_cooldown(
        run, "line", fine, coolant_enthalpy_rise_j_kg=10_000.0,
        coolant_only_energy_transport=True,
        evidence_ids=("synthetic-native-transport-ledger", "synthetic-grid-refinement"),
        coolant_mass_refinement=refinement,
    )
    assert refined_audit.coolant_mass_refinement == refinement
    object.__setattr__(fine, "sample_rates", (0.0, 0.5, 1.0))
    for stale_receipt in (fine, refinement, refined_audit):
        try:
            stale_receipt.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("A receipt accepted mutated coarse/fine sample lineage")
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Audit accepted a replaced accepted run snapshot")
    return ValidationOutcome(True, {
        "coolant_mass_kg": result.coolant_mass.value,
        "required_coolant_mass_kg": result.required_coolant_mass_kg,
        "stored_energy_drop_j": result.stored_energy_drop_j,
        "coolant_energy_residual_j": result.coolant_energy_residual_j,
        "coolant_mass_refinement_normalized_change": refinement.normalized_change,
    }, ("Typed synthetic ledger fixture only; not executed locally.",
        "Native LH2DT and accepted-sample quadrature verification remain pending."))


def validate_energy_bound(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.cooldown import (
        CooldownSegment,
        IsobaricEnthalpyPath,
        estimate_line_cooldown,
        estimate_line_cooldown_with_provider,
    )
    from h2physics.core import PropertyBasis, ThermoState

    class SyntheticGasProvider:
        basis = PropertyBasis("hydrogen", "synthetic-provider-reference", "normal")

        def state_pt(self, pressure_pa, temperature_k):
            enthalpy = 1_000.0 * temperature_k
            density = 1.0
            return ThermoState(
                self.basis, pressure_pa, temperature_k, density, enthalpy,
                enthalpy-pressure_pa/density, 1_000.0, "gas", cp_j_kg_k=1_000.0,
            )

        def state_ph(self, pressure_pa, enthalpy_j_kg):
            raise NotImplementedError

        def state_ps(self, pressure_pa, entropy_j_kg_k):
            raise NotImplementedError

    provider = SyntheticGasProvider()
    path = IsobaricEnthalpyPath(
        provider, 2.0e5, "synthetic-property-path", allowed_phases=("gas",),
    )
    assert path.basis is provider.basis
    assert path.enthalpy_j_kg(300.0, 2.0e5) == 300_000.0
    try:
        path.enthalpy_j_kg(300.0, 1.0e5)
    except ValueError:
        pass
    else:
        raise AssertionError("Isobaric path admitted a different pressure")
    wrong_phase = IsobaricEnthalpyPath(
        provider, 2.0e5, "synthetic-wrong-phase-path", allowed_phases=("liquid",),
    )
    try:
        wrong_phase.state_at(300.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Isobaric path admitted an undeclared property phase")

    segment = CooldownSegment(
        segment_id="synthetic-line-section",
        wall_mass_kg=10.0,
        solid_cp_j_kg_k=lambda temperature: 500.0,
        wall_initial_temperature_k=300.0,
        wall_target_temperature_k=30.0,
        fluid_mass_kg=2.0,
        fluid_pressure_pa=2.0e5,
        fluid_initial_temperature_k=300.0,
        fluid_target_temperature_k=30.0,
        fluid_enthalpy_j_kg=lambda temperature, pressure: 1000.0 * temperature,
    )
    property_result = estimate_line_cooldown_with_provider(
        (segment,), coolant_path=path,
        coolant_inlet_temperature_k=100.0,
        coolant_outlet_temperature_k=300.0,
        evidence_ids=("synthetic-property-cooldown-contract",),
    )
    assert property_result.require_current() is property_result
    assert property_result.inlet_state.temperature_k == 100.0
    assert property_result.outlet_state.temperature_k == 300.0
    assert property_result.estimate.coolant_enthalpy_rise_j_kg == 200_000.0
    assert "synthetic-property-path" in property_result.estimate.evidence_ids
    from dataclasses import replace
    shifted_reference_estimate = estimate_line_cooldown(
        property_result.estimate.segments,
        coolant_inlet_enthalpy_j_kg=200_000.0,
        coolant_outlet_enthalpy_j_kg=400_000.0,
        additional_heat_j=property_result.estimate.additional_heat_j,
        design_factor=property_result.estimate.design_factor,
        evidence_ids=property_result.estimate.evidence_ids,
    )
    try:
        replace(property_result, estimate=shifted_reference_estimate)
    except ValueError:
        pass
    else:
        raise AssertionError("Provider-backed cooldown accepted shifted scalar endpoints with the same enthalpy rise")
    forged_provider_result = object.__new__(type(property_result))
    for field_name in property_result.__dataclass_fields__:
        object.__setattr__(forged_provider_result, field_name,
                           getattr(property_result, field_name))
    object.__setattr__(forged_provider_result, "outlet_state", property_result.inlet_state)
    try:
        _ = forged_provider_result.minimum_hydrogen_mass_kg
    except ValueError:
        pass
    else:
        raise AssertionError("Mutated provider-backed endpoint receipt was admitted")
    result = estimate_line_cooldown(
        (segment,), coolant_inlet_enthalpy_j_kg=100.0,
        coolant_outlet_enthalpy_j_kg=10_000.0, additional_heat_j=5000.0,
        design_factor=1.2, evidence_ids=("synthetic-contract-fixture",),
    )
    assert abs(result.wall_energy_j - 1_350_000.0) < 1e-7
    assert abs(result.contained_fluid_energy_j - 540_000.0) < 1e-7
    assert result.required_cooling_energy_j == (1_350_000.0 + 540_000.0 + 5000.0) * 1.2
    assert abs(result.minimum_hydrogen_mass_kg - result.required_cooling_energy_j / 9900.0) < 1e-12
    assert result.segments == (segment,)
    assert result.segment_duties[0].segment_id == result.segments[0].segment_id
    assert result.require_current() is result
    forged_ledger = object.__new__(type(result))
    for field_name in result.__dataclass_fields__:
        object.__setattr__(forged_ledger, field_name, getattr(result, field_name))
    object.__setattr__(forged_ledger, "evidence_ids", ("substituted-evidence",))
    try:
        forged_ledger.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Post-estimation evidence substitution was admitted")
    try:
        _ = forged_ledger.minimum_hydrogen_mass_kg
    except ValueError:
        pass
    else:
        raise AssertionError("Public coolant-mass access skipped receipt verification")
    for enthalpies in ((100.0, 100.0), (100.0, 90.0)):
        try:
            estimate_line_cooldown((segment,),
                coolant_inlet_enthalpy_j_kg=enthalpies[0],
                coolant_outlet_enthalpy_j_kg=enthalpies[1],
                evidence_ids=("synthetic-contract-fixture",))
        except ValueError:
            pass
        else:
            raise AssertionError("nonpositive coolant enthalpy rise was admitted")
    return ValidationOutcome(True, {
        "wall_energy_j": result.wall_energy_j,
        "contained_fluid_energy_j": result.contained_fluid_energy_j,
        "required_cooling_energy_j": result.required_cooling_energy_j,
        "minimum_hydrogen_mass_kg": result.minimum_hydrogen_mass_kg,
    }, ("Synthetic contract fixture only; not executed locally.",
        "No dynamic heat-transfer or equipment qualification is implied."))
