"""Genuine producer-to-consumer safety handoffs; native physics is not validated."""

import importlib
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for directory in (
    "native_packages",
    "native_pool_packages",
    "native_risk_packages",
    "native_hyram_packages",
    "native_dispersion_dependencies",
    "native_helpr_packages",
):
    target = ROOT / "artifacts" / directory
    if str(target) not in sys.path:
        sys.path.append(str(target))


def validation_case(module, function):
    outcome = getattr(importlib.import_module("validation.cases." + module), function)(
        work_directory=ROOT / "artifacts/connection-contracts-20261102"
    )
    assert outcome.accepted and outcome.metrics


def nozzle_source(kind):
    from h2physics.release import (
        HomogeneousIsentropicNozzle,
        NozzleOpening,
        SourceHistory,
        SourceLocation,
    )
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    upstream = (
        properties.state_pt(5e5, 300.0)
        if kind == "gas"
        else properties.saturated(2e5, 0.0 if kind == "liquid" else 0.4)
    )
    back = 1e5 if kind == "gas" else 1.9e5
    sample = HomogeneousIsentropicNozzle(properties).solve(
        upstream,
        back_pressure_pa=back,
        opening=NozzleOpening.circular(
            "leak", 0.001, effective_area_factor=0.8, area_basis_id="authored-opening"
        ),
    )
    location = SourceLocation(
        "computed-nozzle-" + kind, "clock", "xyz", (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
    )
    history = SourceHistory(location, (10.0, 11.0, 13.0), (sample, sample, sample), "window_end")
    receipt = history.interval_mass_projection(
        representative_state=upstream,
        flow_rule="left_hold",
        quadrature_evidence_id="held-computed-nozzle",
        state_projection_evidence_id="upstream-static-reference-explicit",
    )
    receipt.require_current()
    source = receipt.source
    assert source.location is location and source.state is upstream
    assert source.total_mass_kg == pytest.approx(3.0 * sample.mass_flow_kg_s, rel=2e-14, abs=0.0)
    assert receipt.interval_withdrawal_energy_j[0] == pytest.approx(
        sample.withdrawal_energy_w, rel=2e-14, abs=0.0
    )
    np.testing.assert_allclose(receipt.nozzle_energy_residual_j, 0.0, atol=1e-7, rtol=0.0)
    rebinned = source.rebin((10.0, 10.5, 12.0, 13.0), clock_id="clock")
    assert rebinned.total_mass_kg == pytest.approx(source.total_mass_kg, rel=2e-14, abs=0.0)
    assert rebinned.state is upstream
    with pytest.raises(ValueError, match="clock"):
        source.rebin((10.0, 13.0), clock_id="wrong-clock")
    with pytest.raises(ValueError, match="basis|reference|fluid"):
        _wrong_nozzle_reference(history, upstream)


def _wrong_nozzle_reference(history, state):
    from h2physics.core import PropertyBasis

    history.interval_mass_projection(
        representative_state=replace(
            state,
            basis=PropertyBasis(
                state.basis.fluid, "different-reference", state.basis.spin_composition
            ),
        ),
        flow_rule="left_hold",
        quadrature_evidence_id="declared",
        state_projection_evidence_id="declared",
    )


def pool_chain():
    from dynamiclh2poolx import FixedAreaPoolConfig, Substrate

    from examples.droplet_impact import build_model, incident_trace
    from h2physics.adapters.parcel_pool_chain import run_deposited_batch_pool

    model = build_model()
    impact = model.run((incident_trace(model),)).steps[0]
    config = FixedAreaPoolConfig(
        area_m2=1e-6,
        initial_liquid_mass_kg=0.0,
        substrate=Substrate("separate-substrate", 0.2, 1e-7),
        ambient_temperature_K=80.0,
        ambient_pressure_Pa=101325.0,
        critical_heat_flux_W_m2=None,
        initial_thermal_age_s=0.01,
    )
    location = replace(impact.deposited_batch.location, direction_unit=(0.0, 0.0, 1.0))
    start = impact.contact_end_s
    result = run_deposited_batch_pool(
        impact,
        config,
        impact_owner=model,
        separate_continuation_heat_owner=config.substrate,
        continuation_evidence_id="independent-stock-continuation",
        reference_properties=model.properties,
        vapor_location=location,
        output_times_s=(start, start + 0.01, start + 0.1),
    )
    result.require_current()
    assert result.vapor_source.location is location
    assert (
        result.vapor_source.total_mass_kg
        == result.native_result.ledger[-1].cumulative_evaporation_kg
    )
    assert result.absolute_times_s[0] == impact.contact_end_s
    seed = result.fire_seed(
        evidence_id="deposited-stock-fire-seed",
        ignition_transition_evidence_id="conditional-ignition",
        temperature_absolute_tolerance_k=1e-5,
        density_relative_tolerance=1e-6,
    )
    seed._require_deposited_continuation()
    assert seed.time_s == result.absolute_times_s[-1]
    assert seed.deposited_pool_continuation is result
    assert seed.preignition_evaporation is result.vapor_source
    assert seed.liquid_mass_kg == result.native_result.ledger[-1].liquid_mass_kg
    original = result.native_result.mass_balance_residual_kg
    try:
        object.__setattr__(result.native_result, "mass_balance_residual_kg", original + 1.0)
        with pytest.raises(ValueError):
            seed._require_deposited_continuation()
    finally:
        object.__setattr__(result.native_result, "mass_balance_residual_kg", original)


def pool_fire_receiving_modules():
    from examples.pool_fire import build_model, run_example
    from examples.thermal_target import authored_model
    from h2physics.adapters.conditional_risk import ConditionalHarmBinding
    from h2physics.adapters.hyram_exposure import (
        HyRAMExposure,
        NativeHarmSelection,
        exposure_history_from_pool_fire,
    )
    from h2physics.adapters.thermal_target import (
        incident_history_from_pool_fire,
        run_thermal_target,
    )
    from h2physics.core import Origin

    model = build_model(native_packages="artifacts/native_risk_packages")
    trace = run_example(model)
    history = incident_history_from_pool_fire(
        trace, "front-3m", evidence_id="native-fire-radiation-to-target"
    )
    assert history.source_owner is trace and history.clock_id == trace.ignition.clock_id
    expected = math.fsum(r.incident_energy_j_m2 for step in trace.steps for r in step.receptors)
    _, target, tolerances = authored_model(emissivity=0.0, convective_coefficient_w_m2_k=0.0)
    target_trace = run_thermal_target(history, target, tolerances, maximum_step_s=0.25)
    assert target_trace.history is history
    assert target_trace.absorbed_incident_j[-1] == pytest.approx(
        expected * target.area_m2 * target.absorptivity, rel=1e-10, abs=1e-5
    )
    exposure = exposure_history_from_pool_fire(
        trace, "front-3m", basis_id="incident", evidence_id="computed-pool-to-exposure"
    )
    assert exposure.clock_id == trace.ignition.clock_id
    engine = HyRAMExposure()
    selection = NativeHarmSelection(
        next(iter(engine.thermal_models)),
        engine.native_normal_mean,
        "explicit-model",
        "supplied-incident-flux-only",
        Origin.SYNTHETIC,
    )
    response = engine.thermal_response(
        exposure, selection, additivity_evidence_id="held-stage-flux"
    )
    assert response.input is exposure
    harm = ConditionalHarmBinding.from_exposure(
        response, binding_evidence_id="computed-harm-to-risk", origin=Origin.SYNTHETIC
    )
    assert harm.exposure_result is response
    assert harm.clock_id == exposure.clock_id and harm.probability == response.probability
    assert response.fluence_j_m2 == pytest.approx(expected, rel=1e-12, abs=0.0)
    harm.require_current()
    target_trace.require_current()


def native_ignition_to_risk():
    from h2physics.adapters.conditional_risk import ConditionalHarmBinding, ConditionalRiskNative
    from h2physics.adapters.hyram_ignition import (
        HyRAMIgnitionTable,
        evaluate_hyram_ignition_probability,
    )
    from h2physics.adapters.hyram_ignition_risk import bind_hyram_ignition_to_risk
    from h2physics.core import Origin

    native = ConditionalRiskNative.from_installed()
    risk, contracts = native.risk_module, native.contracts
    frequency = risk.Frequency(
        asset_id="asset",
        scenario_id="single-LOC",
        operating_case_id="declared-case",
        annual_frequency_per_year=1e-4,
        origin="user_supplied",
        source_digest=contracts.digest({"frequency": 1e-4}),
        source_code_digest="a" * 64,
        evidence_ids=("explicit-frequency",),
    )
    table = HyRAMIgnitionTable(
        "explicit-input-table",
        "h2",
        (0.1,),
        (0.02, 0.06),
        (0.01, 0.04),
        "explicit-table",
        Origin.SYNTHETIC,
    )
    computed = evaluate_hyram_ignition_probability(0.2, table=table)
    ids = {"no_ignition": "none", "immediate_ignition": "immediate", "delayed_ignition": "delayed"}
    harm = {
        name: ConditionalHarmBinding(
            0.1,
            "receptor",
            "xyz",
            "clock",
            (0.0, 1.0),
            "source",
            "declared-harm",
            (0.0, 0.0, 0.0),
            ("explicit-conditional-harm",),
            Origin.SYNTHETIC,
        )
        for name in ids.values()
    }
    receipt = bind_hyram_ignition_to_risk(
        computed,
        native,
        frequency=frequency,
        receptor_id="receptor",
        partition_evidence_id="explicit-LOC-partition",
        outcome_branch_ids=ids,
        probability_factor_ids={key: (key + "-factor",) for key in ids},
        harm_bindings=harm,
        harm_factor_ids={name: name + "-harm" for name in ids.values()},
    )
    receipt.require_current()
    assert receipt.frequency is frequency and receipt.request.frequency is frequency
    assert receipt.native_module_sha256 == computed.native_module_sha256
    observed = {b.id: b.conditional_probability for b in receipt.request.branches}
    assert observed == pytest.approx(
        {
            "none": 1.0 - computed.total_probability,
            "immediate": computed.immediate_probability,
            "delayed": computed.delayed_probability,
        }
    )
    with pytest.raises((TypeError, ValueError)):
        replace(receipt, lineage_sha256="b" * 64)


def flash_flame_connection():
    # Existing authored helper executes genuine native FreeFlame -> checked
    # premixed reference -> material front and verifies retained parent mutation.
    import test_formula_contract_safety_facility as nominal

    nominal._flash_material_travel()


def short_layer_handoff(oxygen=False):
    from h2physics.adapters.buoyant_layer_h2_alarm import evaluate_buoyant_layer_h2_alarm
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig,
        FirstOrderConcentrationSensorConfig,
    )
    from h2physics.buoyant_layer import TwoVentHydrogenLayerConfig, run_two_vent_hydrogen_layer
    from h2physics.core import Origin

    config = TwoVentHydrogenLayerConfig(
        compartment_height_m=3.0,
        floor_area_m2=36.0,
        source_height_m=0.2,
        lower_vent_area_m2=1.0,
        upper_vent_area_m2=1.0,
        lower_discharge_coefficient=0.65,
        upper_discharge_coefficient=0.65,
        ambient_pressure_pa=101325.0,
        ambient_temperature_k=293.15,
        initial_upper_layer_volume_m3=1.0,
        initial_upper_h2_mole_fraction=0.1,
    )
    clock = "short-layer-clock"
    location = "upper-zone"
    basis = "upper-layer-h2-mole-fraction"
    if oxygen:
        from h2physics.adapters.layer_oxygen_alarm_handoff import (
            evaluate_layer_oxygen_deficit_alarm,
            layer_oxygen_deficit_basis,
        )
        from h2physics.adapters.layer_oxygen_projection import project_layer_oxygen

        layer = run_two_vent_hydrogen_layer(
            config, hydrogen_mass_flow_kg_s=1e-5, duration_s=0.2, maximum_step_s=0.1
        )
        projection = project_layer_oxygen(
            layer,
            carrier_basis="fixed_dry_air",
            carrier_oxygen_mole_fraction=layer.dry_air_mole_fractions[1],
        )
        basis = layer_oxygen_deficit_basis("explicit-oxygen-reference")
    sensor = FirstOrderConcentrationSensorConfig(
        "sensor",
        location,
        clock,
        basis,
        "mole_fraction" if oxygen else "mol/mol",
        0.01,
        0.15,
        "sensor",
        "tau",
        "first-order",
    )
    alarm = ConcentrationAlarmConfig(
        "sensor",
        location,
        clock,
        "mode",
        "episode",
        basis,
        "mole_fraction" if oxygen else "mol/mol",
        0.001,
        0.0001,
        1,
        1,
        0.15,
        "sensor",
        "threshold",
        "logic",
        Origin.SYNTHETIC,
    )
    if oxygen:
        result = evaluate_layer_oxygen_deficit_alarm(
            projection,
            sensor_config=sensor,
            alarm_config=alarm,
            reference_oxygen_mole_fraction=0.2095,
            reference_evidence_id="explicit-oxygen-reference",
            initial_sensor_indication=0.0,
            operating_mode_id="mode",
            episode_id="episode",
            projection_clock_id=clock,
            projection_location_id=location,
            reference_clock_id="reference-clock",
            reference_location_id="reference-air",
            clock_mapping_evidence_id="reference-to-layer-clock",
            location_mapping_evidence_id="reference-to-layer-zone",
            source_evidence_id="layer-oxygen",
            origin=Origin.SYNTHETIC,
        )
    else:
        result = evaluate_buoyant_layer_h2_alarm(
            config,
            hydrogen_mass_flow_kg_s=1e-5,
            duration_s=0.2,
            maximum_step_s=0.1,
            clock_id=clock,
            layer_location_id=location,
            source_evidence_id="layer-source",
            zone_mapping_evidence_id="upper-only",
            sensor_config=sensor,
            alarm_config=alarm,
            initial_sensor_indication=0.0,
            operating_mode_id="mode",
            episode_id="episode",
        )
    result.require_current()
    assert result.alarm_trace.sensor_response is result.sensor_response
    assert result.trip_evidence


def compartment_sensor():
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig,
        FirstOrderConcentrationSensorConfig,
        evaluate_concentration_alarm_from_sensor,
        evaluate_first_order_concentration_sensor,
    )
    from h2physics.compartment_network import (
        CompartmentMolarTransfer,
        CompartmentNetworkModel,
        WellMixedCompartment,
        simulate_hydrogen_compartment_network,
    )
    from h2physics.core import Origin

    room = WellMixedCompartment("source-room", 1.0, 101325.0, 300.0, 0.0, "authored", "fixed-state")
    streams = (
        CompartmentMolarTransfer(
            "feed", None, "source-room", (1.0, 1.0), "source", "pure-H2", "clock", 1.0
        ),
        CompartmentMolarTransfer(
            "out", "source-room", None, (1.0, 1.0), "exhaust", "wellmixed", "clock"
        ),
    )
    trace = simulate_hydrogen_compartment_network(
        CompartmentNetworkModel((room,), streams, "clock"), time_samples_s=(0.0, 1.0, 2.0)
    )
    sensor = FirstOrderConcentrationSensorConfig(
        "sensor",
        "source-room",
        "clock",
        "H2-mole-fraction",
        "1",
        0.1,
        1.1,
        "sensor",
        "tau",
        "first-order",
    )
    response = evaluate_first_order_concentration_sensor(
        sensor,
        time_s=trace.time_s,
        true_concentration=trace.hydrogen_mole_fraction[:, 0],
        initial_indication=0.0,
        source_evidence_id="actual-compartment-trace-zone-projection",
        operating_mode_id="mode",
        episode_id="episode",
        origin=Origin.SYNTHETIC,
    )
    config = ConcentrationAlarmConfig(
        "sensor",
        "source-room",
        "clock",
        "mode",
        "episode",
        "H2-mole-fraction",
        "1",
        0.001,
        0.0001,
        1,
        1,
        1.1,
        "sensor",
        "threshold",
        "logic",
        Origin.SYNTHETIC,
    )
    alarm = evaluate_concentration_alarm_from_sensor(config, response)
    np.testing.assert_array_equal(response.time_s, trace.time_s)
    np.testing.assert_array_equal(response.true_concentration, trace.hydrogen_mole_fraction[:, 0])
    assert alarm.sensor_response is response and any(t.alarm_active for t in alarm.transitions)


def engine_wall_handoff():
    from h2physics.combustion import run_open_cylinder_segment
    from validation.cases.engine_wall_thermal import _run_arguments, cases

    parameters = dict(cases()[0].parameters)
    parameters["samples_per_revolution"] = 72
    args = _run_arguments(parameters, wall=True)

    # The prescribed boundary explicitly covers native trial-time overshoot;
    # this extends the authored input support, not a receiving-domain guard.
    def extend(item):
        schedule = item.mass_flow
        extended = replace(
            schedule,
            time_s=np.r_[schedule.time_s - 100.0, schedule.time_s[-1] - 100.0 + 0.001],
            values=np.r_[schedule.values, schedule.values[-1]],
            clock_origin_s=0.0,
        )
        return replace(item, mass_flow=extended)

    args["boundary"] = replace(
        args["boundary"],
        inlets=tuple(extend(x) for x in args["boundary"].inlets),
        outlets=tuple(extend(x) for x in args["boundary"].outlets),
    )
    args["absolute_clock_origin_s"] = 0.0
    args["relative_tolerance"] = 1e-11
    args["absolute_tolerance"] = 1e-15
    args["initial"] = replace(args["initial"], temperature_k=400.0)
    args["crank_end_rad"] = args["crank_start_rad"] + 0.001
    trace = run_open_cylinder_segment(**args)
    trace.require_current()
    assert trace.wall_thermal is args["wall_thermal"]
    assert (
        trace.piston_geometry is args["geometry"]
        if hasattr(trace, "piston_geometry")
        else trace.geometry is args["geometry"]
    )
    np.testing.assert_allclose(
        np.diff(trace.wall_internal_energy_j),
        -np.diff(trace.gas_wall_heat_into_gas_j) + np.diff(trace.wall_boundary_heat_j),
        rtol=1e-8,
        atol=1e-7,
    )
    assert np.any(np.diff(trace.wall_temperature_k) != 0.0)


def nozzle_native_nearfield():
    from h2physics.adapters.degali import (
        SHARED_AREA,
        JetPlane,
        axisymmetric_boundary,
        expand_nozzle_gas,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation
    from h2physics.thermo import CoolPropProperties

    folder = ROOT / "artifacts/native_dispersion_packages"
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    from degali.addons.axisymmetric_jet import AxisymmetricJetSource, SourceEnthalpyBoundary
    from degali.addons.notional import expand_measured_throat_to_ambient

    props = CoolPropProperties("Hydrogen")
    nozzle = HomogeneousIsentropicNozzle(props).solve(
        props.state_pt(2e6, 300.0),
        back_pressure_pa=101325.0,
        opening=NozzleOpening.circular(
            "leak", 0.002, effective_area_factor=0.8, area_basis_id="effective-area"
        ),
    )
    location = SourceLocation("source", "clock", "xyz", (0.0, 0.0, 2.0), (1.0, 0.0, 0.0))
    plane = expand_nozzle_gas(
        nozzle,
        props,
        expander=expand_measured_throat_to_ambient,
        location=location,
        location_basis_id="declared-plane",
        pressure_area_policy=SHARED_AREA,
    )
    boundary = axisymmetric_boundary(
        plane,
        props,
        section=JetPlane("xyz", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        ambient_temperature_k=293.15,
        source_factory=AxisymmetricJetSource,
        enthalpy_factory=SourceEnthalpyBoundary,
    )
    assert plane.nozzle is nozzle and boundary.gas_plane is plane
    assert plane.mass_flow_kg_s == nozzle.mass_flow_kg_s
    assert (
        boundary.native.enthalpy_boundary.specific_enthalpy
        + boundary.native.enthalpy_boundary.hydrogen_reference_enthalpy
        == pytest.approx(plane.state.enthalpy_j_kg, rel=1e-12, abs=0.0)
    )


def native_pressure_exposure():
    from hyram.phys import Bauwens_method

    from h2physics.adapters.hyram_exposure import pressure_peak_from_hyram_overpressure
    from h2physics.adapters.hyram_overpressure import (
        BauwensCorrelationDomain,
        DetonableHydrogenEnergy,
        HyRAMBauwensOverpressure,
        OverpressureEnvironment,
        OverpressureEvent,
    )
    from h2physics.core import Origin

    domain = BauwensCorrelationDomain(0.01, 100.0, 8e4, 1.2e5, 0.1, "explicit-domain")
    model = HyRAMBauwensOverpressure(
        Bauwens_method, domain=domain, native_source_id="installed-HyRAM"
    )
    energy = DetonableHydrogenEnergy(
        0.01, 120e6, "mass-evidence", "heat-evidence", "LHV", "source", Origin.SYNTHETIC
    )
    event = OverpressureEvent("event", (0.0, 0.0, 0.0), "xyz", "centre", 10.0, "clock")
    result = model.evaluate(
        energy,
        event,
        OverpressureEnvironment(101325.0, "ambient"),
        ((20.0, 0.0, 0.0),),
        frame_id="xyz",
    )
    peak = pressure_peak_from_hyram_overpressure(
        result,
        receptor_index=0,
        support_s=(9.0, 11.0),
        receptor_id="receptor",
        basis_id="gauge-peak",
    )
    assert peak.overpressure_pa == result.peak_overpressure_pa[0]
    assert peak.clock_id == event.clock_id and peak.positive_impulse_pa_s is None
    assert (
        domain.evidence_id in peak.input_evidence_ids
        and result.native_source_id in peak.input_evidence_ids
    )
    assert peak.receptor.position_m == tuple(result.receptors_m[0])
    with pytest.raises(ValueError):
        pressure_peak_from_hyram_overpressure(
            result,
            receptor_index=0,
            support_s=(0.0, 1.0),
            receptor_id="receptor",
            basis_id="gauge-peak",
        )


def detector_to_native_risk():
    from h2physics.adapters.conditional_risk import ConditionalRiskNative
    from h2physics.detector_reliability import evaluate_kofn_detector_reliability

    r = evaluate_kofn_detector_reliability(
        ("a", "b"),
        (0.01, 0.02),
        votes_required=1,
        common_cause_failure_probability=0.001,
        mission_duration_s=60.0,
        system_id="detectors",
        mission_id="explicit-demand-mission",
        voting_logic_id="1oo2",
        independent_probability_evidence_ids=("a-failure", "b-failure"),
        common_cause_evidence_id="common-outage",
    )
    native = ConditionalRiskNative.from_installed()
    risk = native.risk_module
    q = r.total_vote_failure_probability
    frequency = risk.Frequency(
        asset_id="asset",
        scenario_id="declared-demand-LOC",
        operating_case_id="declared",
        annual_frequency_per_year=1e-4,
        origin="user_supplied",
        source_digest="a" * 64,
        source_code_digest="b" * 64,
        evidence_ids=("caller-frequency",),
    )
    branches = tuple(
        risk.Branch(
            id=name,
            conditional_probability=p,
            probability_basis="explicit-mission-outcomes",
            probability_factor_ids=(name + "-mission-probability",),
            harm_probability=0.5,
            harm_factor_id=name + "-harm",
            harm_basis="caller-harm",
        )
        for name, p in (("miss", q), ("alarm", 1.0 - q))
    )
    request = risk.RiskInput(
        frequency=frequency,
        receptor_id="receptor",
        branches=branches,
        partition_basis="explicit-mission-outcomes",
        mutually_exclusive_exhaustive=True,
    )
    result = risk.risk(request)
    assert request.frequency is frequency and request.branches[0].conditional_probability == q
    assert result.receptor_id == request.receptor_id
    assert result.branches[0].applied_factor_ids == ("miss-mission-probability", "miss-harm")
    assert not result.complete_facility_qra_claim
    # This fixture explicitly partitions an authored demand mission. It never
    # converts mission duration/probability into annual frequency or SIS credit.


def jet_radiation_gate():
    from examples.jet_fire_conservation import build_source
    from h2physics.adapters.hyram_exposure import incident_history_from_hyram_radiation

    source = build_source(native_packages="artifacts/native_hyram_packages")
    radiation = source.irradiance(
        [[0.0, 3.0, 2.0]],
        relative_humidity=0.5,
        minimum_source_distance_m=0.1,
        allow_rejected_flame=True,
    )
    assert radiation.flame is source and np.all(np.isfinite(radiation.irradiance_w_m2))
    assert not radiation.accepted
    with pytest.raises(ValueError, match="accepted"):
        incident_history_from_hyram_radiation(
            radiation,
            observer_index=0,
            start_s=10.0,
            end_s=20.0,
            receptor_id="receptor",
            basis_id="incident",
        )
    return {"scope_kind": "genuine_rejected_connection_gate", "accepted": False}


def qualified_outdoor_connection():
    import json
    import subprocess

    worker = r"""
import sys,json
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'artifacts/native_hyram_packages'))
import scipy
assert scipy.__version__=='1.16.3'
from hyram.phys import Fluid,Jet,Orifice
from h2physics.dispersion import DispersionScenario,HydrogenReleaseFamily
from h2physics.adapters.hyram_jet_source import project_hyram_jet_to_finite_source,HyRAMFiniteSourceError
from h2physics.release import SourceLocation,NozzleOpening
from h2physics.thermo import CoolPropProperties
from h2physics.core import Origin
p=CoolPropProperties('Hydrogen');up=p.state_pt(2e6,300.);ambient=CoolPropProperties('Air').state_pt(101325.,293.15)
location=SourceLocation('source','clock','xyz',(0.,0.,2.),(1.,0.,0.))
scenario=DispersionScenario(HydrogenReleaseFamily.HIGH_PRESSURE_GAS,dict(fluid_factory=Fluid,orifice_factory=Orifice,jet_factory=Jet,upstream=up,ambient=ambient,opening=NozzleOpening.circular('leak',.002,effective_area_factor=.8,area_basis_id='effective-area'),location=location,evidence_id='real-native-gas-provider',solver_options={'Smax':2.,'numpts':100},require_accepted=False))
execution=scenario.run();execution.require_current();jet=execution.result
assert execution.provider_id=='hyram' and jet.location is location and jet.upstream is up
if jet.accepted:
 projection=project_hyram_jet_to_finite_source(jet,start_s=10.,end_s=11.,clock_id='clock',source_state=up,source_state_evidence_id='explicit-upstream-projection',origin=Origin.PREDICTED,end_reason='window_end')
 projection.require_current();assert abs(projection.source.total_mass_kg-jet.mass_flow_kg_s)<=1e-12
else:
 try:project_hyram_jet_to_finite_source(jet,start_s=10.,end_s=11.,clock_id='clock',source_state=up,source_state_evidence_id='explicit-upstream-projection',origin=Origin.PREDICTED,end_reason='window_end')
 except (HyRAMFiniteSourceError,ValueError):pass
 else:raise AssertionError('Rejected native jet entered finite source')
result={'accepted':jet.accepted,'mass_flow_kg_s':jet.mass_flow_kg_s,'provider_id':execution.provider_id,'scipy_version':scipy.__version__,'scope_kind':'genuine_computed_handoff' if jet.accepted else 'genuine_rejected_connection_gate'}
(root/'artifacts/connection-contracts-20261102/safety-outdoor-worker.json').write_text(json.dumps(result),encoding='utf-8')
"""
    output = subprocess.run(
        [sys.executable, "-c", worker],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=90.0,
    )
    (ROOT / "artifacts/connection-contracts-20261102/safety-outdoor-worker.log").write_text(
        output.stdout + output.stderr, encoding="utf-8"
    )
    assert output.returncode == 0, output.stdout + output.stderr
    return json.loads(
        (ROOT / "artifacts/connection-contracts-20261102/safety-outdoor-worker.json").read_text(
            encoding="utf-8"
        )
    )


def helpr_fragment_connection():
    from examples.vessel_failure import authored_case
    from h2physics.adapters.vessel_failure import HelprVesselFailure
    from h2physics.adapters.vessel_failure_fragment_flight import run_vessel_failure_fragment_flight
    from h2physics.core import Origin
    from h2physics.fragment_energy_bound import bound_fragment_speed_from_elastic_energy
    from h2physics.fragment_trajectory import (
        FragmentFlightEnvironment,
        FragmentFlightSettings,
        FragmentLaunch,
    )
    from h2physics.materials.elastic_cylinder import CylinderGeometry, CylinderPressureLoad

    flaw, law, history = authored_case()
    # Authored already-overlimit input, distinct from the retained refined-root
    # baseline whose failed flag was false and correctly barred continuation.
    history = replace(
        history,
        samples=tuple(
            replace(x, wall_temperature_k=700.0, internal_pressure_pa_absolute=3.1e6)
            for x in history.samples
        ),
    )
    owner = HelprVesselFailure(
        flaw,
        law,
        criterion="separate_yield_and_toughness",
        criterion_evidence_id="explicit-initiation-limit",
    )
    prediction = owner.predict(history, maximum_reconstruction_step_s=50.0)
    event = prediction.initiation
    assert event is not None and event.failed
    outer = flaw.outer_diameter_m / 2
    inner = outer - flaw.wall_thickness_m
    cylinder = CylinderGeometry(inner, outer, "closed", "explicit-shell-map")
    load = CylinderPressureLoad(
        event.loading.pressure_difference_pa, 0.0, "native-initiation-load", Origin.SYNTHETIC
    )
    bound = bound_fragment_speed_from_elastic_energy(
        cylinder,
        load,
        cylinder_length_m=1.0,
        youngs_modulus_pa=2e11,
        poisson_ratio=0.3,
        fragment_mass_kg=2.0,
        fragment_energy_fraction=0.1,
        fragment_id="fragment",
        material_evidence_id="explicit-elastic",
    )
    launch = FragmentLaunch(
        "fragment",
        2.0,
        0.02,
        0.8,
        (0.0, 0.0, 2.0),
        (0.2 * bound.maximum_speed_m_s, 0.0, 0.2 * bound.maximum_speed_m_s),
        0.0,
        history.context.frame_id,
        "caller-launch-below-ceiling",
    )
    start = event.loading.time_s
    settings = FragmentFlightSettings(
        history.context.clock_id,
        np.linspace(start, start + 2.0, 81),
        maximum_step_s=0.02,
        momentum_tolerance_kg_m_s=1e-4,
        mechanical_energy_tolerance_j=1e-3,
    )
    environment = FragmentFlightEnvironment(
        lambda z: 1.2,
        lambda p, t: np.zeros(3),
        np.array((0.0, 0.0, -9.80665)),
        history.context.frame_id,
        "environment",
        "density",
        "wind",
    )
    result = run_vessel_failure_fragment_flight(
        prediction,
        end_condition="closed",
        cylinder_length_m=1.0,
        shell_to_cylinder_evidence_id="explicit-shell-map",
        youngs_modulus_pa=2e11,
        poisson_ratio=0.3,
        fragment_energy_fraction=0.1,
        material_evidence_id="explicit-elastic",
        launch=launch,
        environment=environment,
        settings=settings,
        launch_mapping_evidence_id="explicit-conditional-launch",
    )
    result.require_current()
    assert result.prediction is prediction and result.flight.launch is launch
    assert result.flight.time_s[0] == event.loading.time_s


def detonation_to_reactor():
    from h2physics.adapters.cantera import CanteraGas, ReactiveState
    from scripts.check_detonation import evidence, hydrogen_initial, make_case

    model = make_case(
        native_workspace=ROOT / "artifacts/connection-contracts-20261102/safety-native-wave-work"
    )
    shock = model.frozen_shock(hydrogen_initial(), speed_m_s=1500.0, evidence=evidence())
    shock.require_current()
    final = shock.final
    initial = ReactiveState(final.temperature_k, final.pressure_pa, dict(final.mole_fractions))
    receiver = CanteraGas(model.phase_factory, model.basis)
    trace = receiver.closed_reactor(
        initial, (0.0, 1e-7, 2e-7), constraint="UV", maximum_time_step_s=1e-8
    )
    trace.require_current()
    assert trace.basis is shock.mechanism_basis
    assert trace.snapshots[0].state.temperature_k == pytest.approx(
        final.temperature_k, rel=1e-13, abs=0.0
    )
    assert trace.snapshots[0].enthalpy_j_kg == pytest.approx(
        final.enthalpy_j_kg, rel=1e-13, abs=0.0
    )
    assert trace.snapshots[0].state.mole_fractions == pytest.approx(
        dict(final.mole_fractions), abs=1e-15
    )
    # The receiving reactor uses a declared local clock anchored at the static
    # wave evidence time; this is no inferred shock arrival/ignition history.
    assert trace.time_s[0] == 0.0 and shock.evidence.event_time_s == 100.0


def maps_and_seals():
    validation_case("brayton_compressor_map", "validate_map_pair")
    from h2physics.combustion.turbine_map import TurbineComponentMap, interpolate_turbine_map

    mapping = TurbineComponentMap(
        "authored-map",
        "explicit-grid",
        "urn:authored",
        "authored-input",
        "1" * 64,
        "caller-speed",
        "inlet-over-exit-total-pressure",
        "caller-corrected-mass-flow",
        (0.5, 1.0),
        (7.0, 9.0),
        ((1.0, 1.0), (1.0, 1.0)),
        ((0.8, 0.8), (0.9, 0.9)),
    )
    assert mapping.require_current() is mapping
    point = interpolate_turbine_map(mapping, corrected_speed=0.75, expansion_pressure_ratio=8.0)
    assert point.require_current() is point
    original = point.isentropic_efficiency
    try:
        object.__setattr__(point, "isentropic_efficiency", original + 0.001)
        with pytest.raises(ValueError, match="efficiency"):
            point.require_current()
    finally:
        object.__setattr__(point, "isentropic_efficiency", original)
    point.require_current()


@dataclass(frozen=True)
class Case:
    name: str
    families: tuple[str, ...]
    producer: str
    consumer: str
    scenario: str
    invoke: object


CASES = [
    Case(
        "nozzle-" + kind,
        ("release." + kind,),
        "HomogeneousIsentropicNozzle.solve",
        "SourceHistory.interval_mass_projection / IntervalMassSource.rebin",
        "actual nozzle mass/energy values and reference/clock retained",
        lambda k=kind: nozzle_source(k),
    )
    for kind in ("gas", "liquid", "two_phase")
]
for name, families, module, function, producer, consumer in (
    (
        "native-reactor-alarm",
        ("combustion.kinetics", "facility.monitoring"),
        "cantera_species_alarm",
        "validate_handoff",
        "CanteraGas.closed_reactor",
        "evaluate_cantera_species_alarm",
    ),
    (
        "native-volume-source",
        ("dispersion.enclosure", "release.blowdown"),
        "cantera_gas_volume_source",
        "validate_handoff",
        "CanteraOpenGasVolume.run",
        "bind_cantera_gas_volume_vent",
    ),
    (
        "h2-layer-alarm",
        ("dispersion.buoyant_layer", "facility.monitoring"),
        "buoyant_layer_h2_alarm",
        "validate_layer_alarm",
        "run_two_vent_hydrogen_layer",
        "evaluate_buoyant_layer_h2_alarm",
    ),
    (
        "layer-oxygen-alarm",
        ("dispersion.buoyant_layer", "effects.cryogenic", "facility.monitoring"),
        "layer_oxygen_alarm_handoff",
        "validate_handoff",
        "project_layer_oxygen",
        "evaluate_layer_oxygen_deficit_alarm",
    ),
    (
        "oxygen-room-alarm",
        ("dispersion.enclosure", "effects.cryogenic", "facility.monitoring"),
        "oxygen_alarm_handoff",
        "validate_handoff",
        "CanteraOxygenRoom.run",
        "evaluate_oxygen_deficit_alarm",
    ),
    (
        "alarm-isolation",
        ("facility.monitoring", "facility.isolation"),
        "alarm_valve_isolation",
        "validate_alarm_valve_isolation",
        "evaluate_concentration_alarm",
        "schedule_alarm_valve_isolation",
    ),
    (
        "population-impact",
        ("release.droplets", "release.impact", "release.liquid"),
        "parcel_impact_chain",
        "validate_contract",
        "run_parcel_population",
        "impact_population_member",
    ),
    (
        "elastic-flight",
        ("effects.fragment_trajectory",),
        "fragment_energy_bound",
        "validate_elastic_bound_flight",
        "bound_fragment_speed_from_elastic_energy",
        "run_elastic_bound_fragment_flight",
    ),
):
    CASES.append(
        Case(
            name,
            families,
            producer,
            consumer,
            "original calculated output enters actual downstream owner; identity/clock/ledger checks",
            (lambda: short_layer_handoff())
            if name == "h2-layer-alarm"
            else (
                (lambda: short_layer_handoff(True))
                if name == "layer-oxygen-alarm"
                else (lambda m=module, f=function: validation_case(m, f))
            ),
        )
    )
CASES.extend(
    (
        Case(
            "impact-pool-seed",
            ("release.impact", "surface.pool", "combustion.pool_fire"),
            "FiniteSurfaceImpact.run",
            "run_deposited_batch_pool / PoolFireSeed",
            "absolute-clock deposited mass to genuine native pool and ignition seed",
            pool_chain,
        ),
        Case(
            "pool-exposure-target",
            ("combustion.pool_fire", "effects.exposure", "effects.heat_input", "facility.risk"),
            "FinitePoolFire.run",
            "HyRAMExposure / run_thermal_target / ConditionalHarmBinding.from_exposure",
            "actual radiation intervals drive heat/fluence/harm receiving modules",
            pool_fire_receiving_modules,
        ),
        Case(
            "native-ignition-risk",
            ("facility.risk",),
            "evaluate_hyram_ignition_probability",
            "bind_hyram_ignition_to_risk",
            "native computed probabilities preserve release basis and exact caller frequency",
            native_ignition_to_risk,
        ),
        Case(
            "native-flame-front",
            ("combustion.laminar_flame", "combustion.equilibrium", "combustion.flash_fire"),
            "CanteraGas.free_flame",
            "premixed_reference / run_material_front",
            "actual native flame state/speed into material coordinate propagation",
            flash_flame_connection,
        ),
    )
)


CASES.extend(
    (
        Case(
            "compartment-sensor-alarm",
            ("dispersion.compartment_network", "facility.monitoring"),
            "simulate_hydrogen_compartment_network",
            "sensor/alarm public APIs",
            "explicit original zone samples/clock to existing response",
            compartment_sensor,
        ),
        Case(
            "native-engine-wall",
            ("combustion.piston_engine",),
            "OpenCylinder native gas/geometry",
            "finite CylinderWallThermal",
            "original wall configuration and equal/opposite gas-wall ledger",
            engine_wall_handoff,
        ),
        Case(
            "native-maps-cycle",
            ("combustion.gas_turbine",),
            "compressor/turbine map interpolation",
            "run_map_matched_brayton",
            "actual mapped efficiencies and flows passed into native cycle",
            maps_and_seals,
        ),
        Case(
            "native-pressure-exposure",
            ("combustion.overpressure", "effects.exposure"),
            "HyRAMBauwensOverpressure.evaluate",
            "pressure_peak_from_hyram_overpressure",
            "native gauge peak/receptor/time/energy evidence preserved",
            native_pressure_exposure,
        ),
        Case(
            "native-nozzle-nearfield",
            ("release.near_field", "release.gas"),
            "HomogeneousIsentropicNozzle.solve",
            "expand_nozzle_gas / axisymmetric_boundary",
            "actual native expansion retains flow and enthalpy reference",
            nozzle_native_nearfield,
        ),
    )
)


CASES.extend(
    (
        Case(
            "detector-native-risk",
            ("facility.detector_reliability", "facility.risk"),
            "evaluate_kofn_detector_reliability",
            "native RiskInput / risk.risk",
            "explicit demand-outcome probabilities passed without annual-rate conversion",
            detector_to_native_risk,
        ),
        Case(
            "native-jet-radiation-gate",
            ("combustion.jet_fire", "effects.exposure"),
            "actual HyRAM flame/radiation",
            "incident_history_from_hyram_radiation",
            "rejected real native radiation is barred from exposure",
            jet_radiation_gate,
        ),
        Case(
            "qualified-outdoor",
            ("dispersion.outdoor", "release.gas"),
            "DispersionScenario.run with actual HyRAM",
            "project_hyram_jet_to_finite_source",
            "qualified native runtime preserves source boundary and admission status",
            qualified_outdoor_connection,
        ),
        Case(
            "helpr-fragment",
            ("effects.rupture", "effects.fragment_trajectory"),
            "HelprVesselFailure.predict",
            "run_vessel_failure_fragment_flight",
            "native initiation time/load/frame to bounded conditional fragment launch",
            helpr_fragment_connection,
        ),
    )
)


CASES.append(
    Case(
        "native-shock-reactor",
        ("combustion.detonation", "combustion.kinetics"),
        "SDToolboxDetonation.frozen_shock",
        "CanteraGas.closed_reactor",
        "actual postshock state and identical mechanism enthalpy reference seed a local-time reactor",
        detonation_to_reactor,
    )
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_module_connection(case, record_property):
    record_property("family", case.families[0])
    record_property("connected_families", ",".join(case.families))
    record_property("connection_target", case.consumer)
    record_property("connection_scenario", case.scenario)
    record_property("producer", case.producer)
    record_property("consumer", case.consumer)
    record_property(
        "scope_kind",
        "genuine_rejected_connection_gate"
        if case.name in {"native-jet-radiation-gate", "qualified-outdoor"}
        else "genuine_computed_handoff",
    )
    print("START", case.name, flush=True)
    details = case.invoke()
    if isinstance(details, dict) and details.get("scope_kind"):
        record_property("connection_acceptance", str(details.get("accepted")))
        record_property("actual_scope_kind", details["scope_kind"])
    print("DONE", case.name, flush=True)
