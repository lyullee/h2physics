"""Deferred actual finite-source orchestration and rejection contracts."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


class _SyntheticConsequenceResult:
    def __init__(self, facility_handoff, marker="caller-owned"):
        self.facility_handoff = facility_handoff
        self.marker = marker

    def require_current(self):
        self.facility_handoff.require_current()
        if self.marker != "caller-owned":
            raise ValueError("authored consequence result binding changed")
        return self


class _SyntheticConsequenceOwner:
    def __init__(self, configuration):
        self.configuration = configuration

    def __call__(self, facility_handoff):
        marker = "caller-owned" if self.configuration[0] == 1.0 else "changed"
        return _SyntheticConsequenceResult(facility_handoff, marker)


def cases():
    return (ValidationCase(
        identifier="facility-accident-chain-source-prefix", profile="facility-protection",
        entrypoint=__name__+":validate_chain", parameters={}, invariants=(
            "actual native finite-operation result retained by source node",
            "source projection admitted before preferred provider selection",
            "wrong release-family request rejected without calling its native engine",
            "gas and liquid scenarios require complete family-specific provider inputs",
            "provider-specific keys cannot cross release-family boundaries",
            "LH2-origin chains reject unused gas-only projection callbacks before operation execution",
            "caller failure preserves original cause and completed finite/source prefix",
            "downstream facility handoff rechecks provider receipt freshness without resealing it",
            "prepared chain rejects post-assembly changes to its scenario wiring, family or evidence identity",
            "a current but unaccepted HyRAM finite-source diagnostic cannot be promoted by looser facility budgets",
            "chain failure retains the rejected HyRAM projection and accepted native jet receipt",
            "caller consequence owner receives and returns the exact typed source/provider handoff",
            "synthetic preferred-provider execution is issued only through DispersionScenario.run",
            "callback-side mutation of accepted dispersion output is rejected after evaluation",
            "consequence evaluator code and captured mutable configuration remain current after evaluation",
            "consequence evaluator configuration changed during the callback is rejected before receipt issuance",
            "nested solver-option edits after scenario construction are rejected before provider invocation",
        ),
    ),)


def validate_chain(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.facility_protection import make_case
    from h2physics.adapters.facility_accident_chain import assemble_facility_accident_chain
    from h2physics.dispersion import DispersionScenario
    from h2physics.scenarios import ScenarioExecutionError

    binding = make_case()["source"]
    binding.require_current()
    sentinel = RuntimeError("authored-dispersion-boundary-unavailable")

    try:
        assemble_facility_accident_chain(
            scenario_id="authored-lh2-rejects-gas-projection",
            finite_operation=lambda: binding.run,
            source_binding=lambda run: binding,
            dispersion_request=lambda source: None,
            release_family="liquid_hydrogen_origin",
            evidence_id="authored-family-boundary",
            mass_absolute_tolerance_kg=1.0,
            energy_absolute_tolerance_j=1.0,
            gas_projection=lambda execution, source: None,
        )
    except TypeError:
        family_callback_rejected = True
    else:
        raise AssertionError("LH2-origin chains must reject the gas-only projection callback")

    def unavailable(source):
        assert source is binding
        raise sentinel

    def wrong_family(source):
        assert source is binding
        return DispersionScenario("high_pressure_gas", {"evidence_id": "unused-family-rejection"})

    rejected = 1
    for request, expected_cause in ((unavailable, sentinel), (wrong_family, None)):
        chain = assemble_facility_accident_chain(
            scenario_id="authored-finite-source-chain",
            finite_operation=lambda: binding.run,
            source_binding=lambda run: binding,
            dispersion_request=request, release_family="liquid_hydrogen_origin",
            evidence_id="authored-orchestration-only",
            mass_absolute_tolerance_kg=binding.tolerances.mass_absolute_kg,
            energy_absolute_tolerance_j=max(
                1., 2*max(abs(value) for value in binding.energy_projection().residual_j),
            ),
        )
        try:
            chain.run()
        except ScenarioExecutionError as error:
            assert error.node.node_id == "preferred-dispersion"
            assert tuple(row.node.node_id for row in error.completed) == (
                "finite-operation", "finite-source",
            )
            assert error.completed[0].result is binding.run
            assert error.completed[1].result is binding
            if expected_cause is not None:
                assert error.cause is expected_cause
            else:
                assert isinstance(error.cause, ValueError)
            rejected += 1
        else:
            raise AssertionError("Incomplete or incompatible dispersion request was admitted")

    from types import SimpleNamespace

    from h2physics.adapters.facility_accident_chain import (
        FacilityAccidentChain,
        FacilityDispersionHandoff,
    )
    from h2physics.dispersion import DispersionScenario, HydrogenReleaseFamily
    from h2physics.scenarios import OperationalScenario, ScenarioNode, ScenarioOutput

    source = binding.source
    boundary = SimpleNamespace(
        mass_source=source,
        footprint_evidence_id="authored-footprint-evidence",
        require_current=source.require_current,
    )
    provider_result = SimpleNamespace(
        accepted=True,
        boundary=boundary,
        native_output={"concentration_profile": [0.1, 0.2]},
    )
    selected_family = HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN
    request = DispersionScenario(selected_family, {
        "source": source,
        "native_pool_factory": lambda **kwargs: None,
        "substance": object(),
        "area_m2": 1.0,
        "footprint_evidence_id": boundary.footprint_evidence_id,
        "ambient_pressure_pa": 101325.0,
        "atmosphere": object(),
        "emission_thermo": object(),
        "water_thermo": object(),
        "runner": lambda **kwargs: None,
        "premise_check": lambda **kwargs: None,
        "width_context": lambda **kwargs: None,
        "width_coupling": False,
        "x_max_m": 10.0,
    })
    from unittest.mock import patch
    with patch("h2physics.dispersion.run_preferred_lh2_dispersion",
               return_value=provider_result):
        execution = request.run()
    handoff = FacilityDispersionHandoff(
        binding,
        execution,
        None,
        "authored-facility-coupling-evidence",
        HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
        1e30,
        1e30,
    )
    from h2physics.adapters.facility_consequence import (
        FacilityConsequenceEvaluationError,
        evaluate_facility_consequence,
    )

    evaluator_config = [1.0]
    consequence_owner = _SyntheticConsequenceOwner(evaluator_config)

    consequence = evaluate_facility_consequence(
        handoff, consequence_owner,
        method_evidence_id="authored-caller-consequence-method",
    )
    assert consequence.require_current() is consequence
    assert consequence.consequence_result.facility_handoff is handoff
    evaluator_config[0] = 2.0
    try:
        consequence.require_current()
    except ValueError as error:
        assert "evaluator code or captured configuration changed" in str(error)
        evaluator_mutation_rejected = True
    else:
        raise AssertionError("A consequence receipt retained changed evaluator configuration")
    evaluator_config[0] = 1.0
    assert consequence.require_current() is consequence

    def mutating_evaluator_config(received):
        evaluator_config[0] = 2.0
        return _SyntheticConsequenceResult(received)

    try:
        evaluate_facility_consequence(
            handoff, mutating_evaluator_config,
            method_evidence_id="authored-in-call-evaluator-mutation",
        )
    except FacilityConsequenceEvaluationError as error:
        assert error.stage == "post_evaluation_integrity"
        assert "evaluator changed" in str(error.__cause__).lower()
        evaluator_in_call_mutation_rejected = True
    else:
        raise AssertionError("An evaluator changed configuration while producing a consequence")
    evaluator_config[0] = 1.0

    def mutating_consequence_owner(received):
        provider_result.native_output["concentration_profile"].append(0.3)
        return _SyntheticConsequenceResult(received)

    try:
        evaluate_facility_consequence(
            handoff, mutating_consequence_owner,
            method_evidence_id="authored-mutation-rejection",
        )
    except FacilityConsequenceEvaluationError as error:
        assert error.stage == "post_evaluation_integrity"
        assert error.facility_handoff is handoff
        mutation_rejected = True
    else:
        raise AssertionError("Consequence callback mutation was admitted")
    provider_result.native_output["concentration_profile"].pop()
    handoff.require_current()

    provider_result.native_output["concentration_profile"].append(0.3)
    try:
        handoff.require_current()
    except ValueError as error:
        assert "changed after capture" in str(error)
    else:
        raise AssertionError("Downstream handoff resealed a mutated provider receipt")
    provider_result.native_output["concentration_profile"].pop()
    handoff.require_current()

    chain_evidence = "authored-chain-evidence"
    unrelated_handoff_scenario = OperationalScenario("unrelated-handoff", (
        ScenarioNode("finite-operation", lambda: binding.run, {}, chain_evidence),
        ScenarioNode("finite-source", lambda run: binding,
                     {"run": ScenarioOutput("finite-operation")}, chain_evidence),
        ScenarioNode("preferred-dispersion", lambda source: handoff,
                     {"source": ScenarioOutput("finite-source")}, chain_evidence),
    ))
    unrelated_handoff = FacilityAccidentChain(
        unrelated_handoff_scenario, HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
        chain_evidence,
    )
    try:
        unrelated_handoff.run()
    except ValueError as error:
        assert "family/evidence" in str(error)
    else:
        raise AssertionError("A facility chain accepted a handoff with unrelated evidence")
    rejected += 1

    try:
        replace(handoff, evidence_id=" ")
    except ValueError as error:
        assert "coupling evidence" in str(error)
    else:
        raise AssertionError("A directly constructed facility handoff accepted blank evidence")
    rejected += 1

    # Keep a source projection that is internally current but failed its own
    # strict energy gate. An outer facility budget must not promote it.
    import numpy as np
    from types import SimpleNamespace
    from h2physics.adapters.facility_accident_chain import FacilityChainAdmissionError
    from h2physics.adapters.hyram import HyRAMJetRun, _issue_hyram_jet_run
    from h2physics.adapters.hyram_jet_source import project_hyram_jet_to_finite_source
    from h2physics.core import ThermoState, PropertyBasis, Origin
    from h2physics.dispersion import HydrogenReleaseFamily
    from h2physics.release import NozzleOpening

    gas_basis = source.state.basis
    gas_upstream = ThermoState(
        gas_basis, source.state.pressure_pa, source.state.temperature_k,
        source.state.density_kg_m3, source.state.enthalpy_j_kg,
        source.state.internal_energy_j_kg, source.state.entropy_j_kg_k, "gas",
    )
    ambient = ThermoState(
        PropertyBasis("Air", "facility-chain-diagnostic-contract"),
        101325., 298., 1.2, 3.e5, 2.14e5, 6.8e3, "gas",
    )
    start, end = float(source.edges_s[0]), float(source.edges_s[-1])
    rate = source.total_mass_kg/(end-start)
    native_jet = SimpleNamespace(
        S=np.array([0., 1.]), x=np.array([0., 1.]), y=np.array([0., 0.]),
        Y_cl=np.array([1., .5]), X_cl=np.array([1., .4]),
        rho_cl=np.ones(2), V_cl=np.array([2*rate/np.pi, 4*rate/np.pi]),
        B=np.ones(2), lam=1., mass_flow_rate=rate,
    )
    centreline = np.c_[native_jet.S, native_jet.x, native_jet.y,
                       native_jet.Y_cl, native_jet.X_cl]
    flux = np.pi*native_jet.rho_cl*native_jet.Y_cl*native_jet.V_cl*native_jet.B**2/2.
    jet = _issue_hyram_jet_run(
        native=native_jet, upstream=gas_upstream, ambient=ambient,
        opening=NozzleOpening.circular("authored-gas-source", .01,
                                       effective_area_factor=1., area_basis_id="fixture"),
        location=source.location, evidence_id="authored-chain-gas-evidence",
        mass_flow_kg_s=rate, gaussian_entry_h2_flow_kg_s=float(flux[0]),
        maximum_transport_h2_residual_kg_s=float(np.max(np.abs(flux-flux[0]))),
        maximum_h2_flux_residual_kg_s=float(np.max(np.abs(flux-rate))),
        mass_budget_kg_s=1e-9, accepted=True, centreline=centreline,
    )
    incompatible_state = ThermoState(
        gas_basis, gas_upstream.pressure_pa, gas_upstream.temperature_k,
        gas_upstream.density_kg_m3, gas_upstream.enthalpy_j_kg+1.e12,
        gas_upstream.internal_energy_j_kg, gas_upstream.entropy_j_kg_k, "gas",
    )
    diagnostic = project_hyram_jet_to_finite_source(
        jet, start_s=start, end_s=end, clock_id=source.location.clock_id,
        source_state=incompatible_state,
        source_state_evidence_id="authored-rejected-projection-state",
        origin=Origin.SYNTHETIC, relative_enthalpy_tolerance=1e-12,
        absolute_enthalpy_tolerance_w=1e-12, require_accepted=False,
    )
    assert diagnostic.require_current() is diagnostic and diagnostic.accepted is False
    request = DispersionScenario(HydrogenReleaseFamily.HIGH_PRESSURE_GAS, {
        "fluid_factory": lambda *args, **kwargs: None,
        "orifice_factory": lambda *args, **kwargs: None,
        "jet_factory": lambda *args, **kwargs: None,
        "upstream": gas_upstream,
        "ambient": ambient,
        "opening": jet.opening,
        "location": source.location,
        "evidence_id": jet.evidence_id,
        "solver_options": {"Smax": 1.},
    })
    from unittest.mock import patch
    chain = assemble_facility_accident_chain(
        scenario_id="authored-rejected-gas-projection-chain",
        finite_operation=lambda: binding.run,
        source_binding=lambda run: binding,
        dispersion_request=lambda _binding: request,
        release_family=HydrogenReleaseFamily.HIGH_PRESSURE_GAS,
        evidence_id="authored-rejected-gas-projection-evidence",
        mass_absolute_tolerance_kg=1e30,
        energy_absolute_tolerance_j=1e30,
        gas_projection=lambda execution, _binding: diagnostic,
    )
    with patch("h2physics.dispersion.run_preferred_gas_dispersion", return_value=jet):
        try:
            chain.run()
        except ScenarioExecutionError as error:
            assert isinstance(error.cause, FacilityChainAdmissionError)
            assert error.cause.execution.result is jet
            assert error.cause.projection is diagnostic
            rejected_projection_preserved = True
        else:
            raise AssertionError("Unaccepted HyRAM projection was promoted by the outer budget")
    rejected += 1

    nested_options = {"integrator": {"rtol": 1e-6}}
    immutable_request = DispersionScenario(HydrogenReleaseFamily.HIGH_PRESSURE_GAS, {
        "fluid_factory": lambda *args, **kwargs: None,
        "orifice_factory": lambda *args, **kwargs: None,
        "jet_factory": lambda *args, **kwargs: None,
        "upstream": gas_upstream,
        "ambient": ambient,
        "opening": jet.opening,
        "location": source.location,
        "evidence_id": jet.evidence_id,
        "solver_options": nested_options,
    })
    nested_options["integrator"]["rtol"] = 1e-3
    with patch("h2physics.dispersion.run_preferred_gas_dispersion") as provider:
        try:
            immutable_request.run()
        except ValueError as error:
            assert "changed after scenario construction" in str(error)
            provider_not_called = not provider.called
        else:
            raise AssertionError("Mutated nested solver options reached the provider")
    assert provider_not_called
    rejected += 1
    original_chain_evidence = unrelated_handoff.evidence_id
    object.__setattr__(unrelated_handoff, "evidence_id", "changed-after-chain-assembly")
    try:
        unrelated_handoff.require_current()
    except ValueError as error:
        assert "scenario or coupling identity changed" in str(error)
        chain_reconfiguration_rejected = True
    else:
        raise AssertionError("A prepared accident chain accepted a changed coupling identity")
    object.__setattr__(unrelated_handoff, "evidence_id", original_chain_evidence)
    assert unrelated_handoff.require_current() is unrelated_handoff
    rejected += 1
    return ValidationOutcome(True, {"preserved_failure_prefixes": rejected,
                                   "chain_handoff_evidence_rejections": 1,
                                   "post_assembly_chain_reconfiguration_rejected": chain_reconfiguration_rejected,
                                   "consequence_handoff_retained": consequence.require_current() is consequence,
                                   "consequence_callback_mutation_rejected": mutation_rejected,
                                   "evaluator_in_call_mutation_rejected": evaluator_in_call_mutation_rejected,
                                   "rejected_gas_projection_preserved": rejected_projection_preserved,
                                   "nested_solver_options_mutation_rejected": provider_not_called}, (
        "Actual finite-operation source only; no successful dispersion run is fabricated",
        "No facility source-to-field physics validation is established",
    ))
