"""Deferred authored monitoring/actuator/native-inventory/risk composition.

Not executed locally. The caller selects the reviewed optional native targets
and repository scripts directory in its explicit validation environment.
All sensor/reference, latency, frequency and probability inputs are synthetic.
"""


def prepare_case():
    import numpy as np

    from h2physics.adapters.facility_protection import AlarmEvidence
    from h2physics.adapters.process_monitoring import (
        MonitoringSettings,
        NativeProcessMonitoring,
        NativeResidualMonitor,
        ResidualContext,
        ResidualFeature,
        residual_batch,
    )
    from h2physics.core import Origin, TimeSeries
    from h2physics.observations import Variable
    from scripts.check_finite_supply import make_supply

    assembly = make_supply()
    native = NativeProcessMonitoring.from_installed()
    clock = "authored-facility-local-seconds"
    times = np.arange(81) * 0.001
    prediction = TimeSeries(
        times,
        np.tile([2e5, 310.0], (len(times), 1)),
        ("P", "T"),
        ("Pa", "K"),
        np.ones((len(times), 2), bool),
        clock,
        Origin.SYNTHETIC,
        "authored-prescribed-reference-not-native-solver-output",
        ("pressure", "temperature"),
        ("absolute", ""),
    )
    features = (
        ResidualFeature(
            "P-error",
            "P",
            "P",
            Variable("P", "pressure", "Pa", "absolute"),
            "authored-sensor-plane",
            "authored-sensor-plane",
            10.0,
            "authored-10Pa-scale",
        ),
        ResidualFeature(
            "T-error",
            "T",
            "T",
            Variable("T", "temperature", "K"),
            "authored-sensor-plane",
            "authored-sensor-plane",
            0.01,
            "authored-0.01K-scale",
        ),
    )
    reference_owner = {
        "role": "authored-prescribed-monitor-reference; no physical prediction claim"
    }

    def batch(role, seed, shifted=False):
        noise = np.random.default_rng(seed).normal(size=(len(times), 2))
        if shifted:
            noise[times >= 0.04] += 50.0
        observed = TimeSeries(
            times,
            prediction.values + noise * [10.0, 0.01],
            prediction.channels,
            prediction.units,
            prediction.valid,
            clock,
            Origin.SYNTHETIC,
            "authored-noise-realization:" + str(seed),
            prediction.quantities,
            prediction.basis_ids,
        )
        return residual_batch(
            native,
            observed,
            prediction,
            features,
            context=ResidualContext(
                "authored-partition:" + role,
                role,
                "authored-facility-scope",
                "explicit-observed-running-mode",
                "authored-prescribed-reference",
                "authored-sensor-plane-direct-reference",
                "authored-normal-reference" if role != "evaluation" else "",
            ),
            episodes=("authored-independent-realization:" + str(seed),) * len(times),
            modes=("running",) * len(times),
            prediction_owner=reference_owner,
        )

    owner = NativeResidualMonitor(
        native,
        MonitoringSettings(
            window=4,
            statistics=("mean", "std"),
            principal_components=1,
            maximum_gap_s=0.002,
            false_alarm_fraction=0.1,
        ),
    )
    owner.fit(batch("fitting", 124)).calibrate(batch("calibration", 235))
    evaluation = owner.evaluate(batch("evaluation", 346, True))
    alarm = AlarmEvidence.bind(
        owner,
        evaluation,
        row_index=60,
        observed_mode_id="running",
        sensor_evidence_ids={"P": "authored-P-sensor-evidence", "T": "authored-T-sensor-evidence"},
        decision_evidence_id="authored-selected-row60-deviation-not-leak-identification",
    )
    return assembly, owner, evaluation, alarm


def make_case(*, fail_action=False):
    from h2physics.adapters.facility_protection import (
        FiniteFacilitySource,
        ProtectionAction,
        ScheduledProtection,
        execute_protected,
        sampled_interval_source,
    )
    from h2physics.core import Origin
    from h2physics.dynamics import InventoryTolerances
    from h2physics.release import SourceLocation

    assembly, owner, evaluation, alarm = prepare_case()
    action = ProtectionAction(
        "authored-feed-isolation",
        "feed-isolation-resolved-path",
        "pump-assembly",
        "isolation",
        "running",
        "isolated",
        0.003,
        "authored-command-latency-and-ideal-mode-change",
        "prescribed-counterfactual-replay",
        Origin.SYNTHETIC,
    )

    def apply(_time, _context):
        assembly.pump.set_mode("isolated")
        if fail_action:
            raise ValueError("authored-partial-actuator-failure")

    plan = ScheduledProtection(
        alarm,
        action,
        target=assembly.pump,
        native_context=assembly.network.native,
        read_mode=lambda target: target.mode_id,
        apply=apply,
    )
    protected = execute_protected(
        assembly.driver,
        (plan,),
        duration_s=0.15,
        time_step_s=0.001,
        start_time_s=0.0,
        clock_id=alarm.clock_id,
        mode_definition_id="authored-feed-isolation-mode",
        scenario_evidence_id="authored-prescribed-protected-path-not-online-control",
    )
    run = protected.native_run
    location = SourceLocation(
        "authored-finite-supply-outlet",
        alarm.clock_id,
        "authored-facility-xyz",
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0),
    )
    source = sampled_interval_source(
        run,
        component_id="outlet-valve",
        location=location,
        state=run.initial_equipment.node_states[assembly.node_ids["delivery"]],
        evidence_id="actual-native-accepted-outlet-sample-quadrature",
    )
    finite_source = FiniteFacilitySource.bind(
        run,
        source,
        component_id="outlet-valve",
        other_net_boundary_mass_kg=0.0,
        reconciliation_evidence_id="authored-complete-closed-supply-node-set-no-other-mass-boundaries",
        state_projection_evidence_id="declared-delivery-state-not-resolved-atmospheric-source-plane",
        tolerances=InventoryTolerances(1e-8, 0.01, 1e-7),
    )
    return {
        "assembly": assembly,
        "owner": owner,
        "evaluation": evaluation,
        "alarm": alarm,
        "plan": plan,
        "protected": protected,
        "source": finite_source,
    }


def risk_inputs(case, native):
    import hashlib
    from pathlib import Path

    from h2physics.adapters.conditional_risk import (
        ConditionalHarmBinding,
        RiskBindingEvidence,
        RiskReceptor,
    )
    from h2physics.adapters.facility_protection import ConditionalDependence
    from h2physics.core import Origin

    source, protected = case["source"], case["protected"]
    clock, frame = source.source.location.clock_id, source.source.location.coordinate_frame_id
    r, c = native.risk_module, native.contracts
    receptor = RiskReceptor(
        "authored-receptor",
        frame,
        clock,
        (5.0, 0.0, 1.0),
        "authored-receptor-position",
        Origin.SYNTHETIC,
    )
    evidence = RiskBindingEvidence(
        "authored-source-binding",
        "unsolved-field-to-harm-assumption",
        "authored-exclusive-partition",
        Origin.SYNTHETIC,
    )
    harm = {
        key: ConditionalHarmBinding(
            probability,
            receptor.receptor_id,
            frame,
            clock,
            (source.source.edges_s[0], source.source.edges_s[-1]),
            source.source.location.source_id,
            "authored-harm-assumption:" + key,
            receptor.position_m,
            ("authored-no-consequence-field:" + key,),
            Origin.SYNTHETIC,
        )
        for key, probability in (("branch-a", 0.4), ("branch-b", 0.0))
    }
    frequency = r.Frequency(
        asset_id="authored-asset",
        scenario_id="authored-LOC",
        operating_case_id="authored-protected-operating-case",
        annual_frequency_per_year=1e-4,
        origin="user_supplied",
        source_digest=c.digest({"role": "synthetic conditional frequency"}),
        source_code_digest=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        evidence_ids=("authored-conditional-annual-frequency",),
    )
    branches = tuple(
        r.Branch(
            id=key,
            conditional_probability=probability,
            probability_basis="authored-partition-probabilities",
            probability_factor_ids=(key + ":path",),
            harm_probability=harm[key].probability,
            harm_factor_id=key + ":harm",
            harm_basis=harm[key].response_model_id,
        )
        for key, probability in (("branch-a", 0.2), ("branch-b", 0.8))
    )
    request = r.RiskInput(
        frequency=frequency,
        receptor_id=receptor.receptor_id,
        branches=branches,
        partition_basis=evidence.partition_evidence_id,
        mutually_exclusive_exhaustive=True,
    )
    dependence = ConditionalDependence(
        frequency.scenario_id,
        frequency.operating_case_id,
        protected.mode_definition_id,
        clock,
        "authored-conditioned-protection-path",
        "authored-probability-factorization-not-independent-evidence",
        "authored-frequency-already-conditional-on-this-path",
        {
            key + ":" + suffix: key + ":" + suffix + ":mechanism"
            for key in harm
            for suffix in ("path", "harm")
        },
        (case["plan"].action.mechanism_id,),
    )
    ids = {
        source.source.evidence_id,
        evidence.source_binding_evidence_id,
        evidence.source_to_harm_assumption_id,
        evidence.partition_evidence_id,
        receptor.position_evidence_id,
        *frequency.evidence_ids,
        "authored-partition-probabilities",
        dependence.conditioning_evidence_id,
        dependence.factorization_evidence_id,
        dependence.frequency_scope_evidence_id,
        protected.scenario_evidence_id,
        source.reconciliation_evidence_id,
        source.state_projection_evidence_id,
        case["plan"].action.evidence_id,
        case["alarm"].decision_evidence_id,
        *case["alarm"].sensor_evidence_ids.values(),
    }
    ids.update(
        item
        for binding in harm.values()
        for item in (*binding.evidence_ids, binding.response_model_id)
    )
    context = c.Context(
        asset_id=frequency.asset_id,
        scenario_id=frequency.scenario_id,
        operating_case_id=frequency.operating_case_id,
        mode="synthetic",
        evidence=tuple(
            c.Evidence(
                id=i,
                kind="synthetic",
                citation="Authored unqualified numerical assumption",
                locator="examples/facility_protection.py",
            )
            for i in sorted(ids)
        ),
    )
    return request, context, dependence, receptor, harm, evidence


def relief_case():
    """Separate actual native initial-latch example; never joined by clock alone."""
    from pathlib import Path

    import lh2dt
    from lh2dt.properties import ThermoState as NativeState
    from lh2dt.streams import MassEnergyFlow
    from lh2dt.tank import HomogeneousTank, TankGeometry, TankState
    from lh2dt.valve import PressureReliefValve, Valve, ValveResult

    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.adapters.lh2dt_relief import (
        Lh2dtReliefTankDriver,
        ReliefTankBoundary,
        shared_native_relief,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties
    from scripts.check_relief_integration import NATIVE_SOURCE_SHA256, REVISION, native_hash

    if native_hash(Path(lh2dt.__file__).parent) != NATIVE_SOURCE_SHA256:
        raise ValueError("Use the existing reviewed immutable native LH2DT target")
    provider = CoolPropProperties("Hydrogen")
    facade = Lh2dtLowLevelProperties(provider, state_factory=NativeState)
    bridge = Lh2dtProperties(facade, reference_id=provider.basis.reference_id)
    protection = shared_native_relief(
        native_valve_type=Valve,
        native_relief_factory=PressureReliefValve,
        result_factory=ValveResult,
        nozzle=HomogeneousIsentropicNozzle(provider),
        bridge=bridge,
        opening=NozzleOpening(
            "authored-separate-relief-orifice", 4e-7, 1.0, "explicit-authored-effective-area"
        ),
        set_pressure_pa_absolute=2.2e5,
        reseat_pressure_pa_absolute=1.9e5,
        native_source_id="LH2DT:" + REVISION,
    )
    tank = HomogeneousTank(TankGeometry(0.02, 80.0, 0.5, 20.0), facade)
    state = facade.from_pT(2.3e5, 305.0)
    mass = state.density_kg_m3 * tank.geometry.volume_m3
    initial = TankState(mass, mass * state.specific_internal_energy_J_kg, 305.0)
    boundary = ReliefTankBoundary(
        "authored-separate-relief-clock",
        5.0,
        5.01,
        provider.state_pt(1e5, 305.0),
        lambda _t: 305.0,
        lambda _t, _s, _w: 0.0,
        "authored-prescribed-relief-thermal-boundary",
    )
    driver = Lh2dtReliefTankDriver(
        tank, protection, flow_factory=MassEnergyFlow, state_factory=NativeState
    )
    return driver.run(
        initial,
        duration_s=0.01,
        maximum_step_s=0.005,
        start_time_s=5.0,
        clock_id=boundary.clock_id,
        boundary=boundary,
        minimum_inventory_kg=mass * 0.01,
    )


def main():
    from h2physics.adapters.conditional_risk import ConditionalRiskNative
    from h2physics.adapters.facility_protection import evaluate_facility_risk

    case = make_case()
    native = ConditionalRiskNative.from_installed()
    request, context, dependence, receptor, harm, evidence = risk_inputs(case, native)
    result = evaluate_facility_risk(
        native,
        request,
        context,
        finite_source=case["source"],
        protected_run=case["protected"],
        dependence=dependence,
        receptor=receptor,
        harm_bindings=harm,
        evidence=evidence,
    )
    print(result.status)
    print(result.native_conditional_result.native_output)


if __name__ == "__main__":
    main()
