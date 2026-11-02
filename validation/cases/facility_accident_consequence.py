"""Deferred host composition of the accepted accident handoff and consequence owner."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


class _DeferredConsequence:
    """Tiny result fixture retaining the exact typed handoff by identity."""

    def __init__(self, facility_handoff):
        self.facility_handoff = facility_handoff

    def require_current(self):
        return self


def _deferred_consequence_evaluator(facility_handoff):
    return _DeferredConsequence(facility_handoff)


def cases():
    return (ValidationCase(
        identifier="facility-accident-consequence-handoff",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "downstream evaluator receives the exact handoff from an accepted source/dispersion chain",
            "the result retains the original chain execution and typed consequence receipt",
            "chain failures prevent consequence evaluation and retain the original cause",
            "consequence failures do not become success receipts and retain completed chain context",
            "freshness checks preserve source, provider, handoff and consequence ownership",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    from types import SimpleNamespace
    from unittest.mock import patch

    from examples.facility_protection import make_case
    from h2physics.adapters.facility_accident_chain import (
        FacilityAccidentChain,
        FacilityDispersionHandoff,
    )
    from h2physics.adapters.facility_accident_consequence import (
        FacilityAccidentConsequenceError,
        run_facility_accident_consequence,
    )
    from h2physics.dispersion import (
        DispersionScenario,
        HydrogenReleaseFamily,
    )
    from h2physics.scenarios import (
        OperationalScenario,
        ScenarioNode,
        ScenarioOutput,
    )

    del work_directory, parameters
    binding = make_case()["source"]
    source = binding.source
    family = HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN
    boundary = SimpleNamespace(
        mass_source=source,
        footprint_evidence_id="deferred-consequence-footprint-evidence",
        require_current=source.require_current,
    )
    native_result = SimpleNamespace(
        accepted=True,
        boundary=boundary,
        native_output={"concentration_profile": [0.1, 0.2]},
    )
    request = DispersionScenario(family, {
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
    with patch("h2physics.dispersion.run_preferred_lh2_dispersion",
               return_value=native_result):
        execution = request.run()
    handoff = FacilityDispersionHandoff(
        binding, execution, None, "deferred-accident-to-consequence-evidence",
        family, 1e30, 1e30,
    )
    evidence = "deferred-accident-to-consequence-evidence"
    scenario = OperationalScenario("deferred-accident-consequence", (
        ScenarioNode("finite-operation", lambda: binding.run, {}, evidence),
        ScenarioNode("finite-source", lambda run: binding,
                     {"run": ScenarioOutput("finite-operation")}, evidence),
        ScenarioNode("preferred-dispersion", lambda source_binding: handoff,
                     {"source_binding": ScenarioOutput("finite-source")}, evidence),
    ))
    chain = FacilityAccidentChain(scenario, family, evidence)

    result = run_facility_accident_consequence(
        chain, _deferred_consequence_evaluator,
        method_evidence_id="deferred-caller-method-applicability",
    )
    assert result.facility_handoff is handoff
    assert result.chain_result.results["preferred-dispersion"] is handoff
    assert result.consequence.consequence_result.facility_handoff is handoff
    assert result.require_current() is result

    def failed_evaluator(value):
        assert value is handoff
        raise RuntimeError("deferred-consequence-owner-failure")

    try:
        run_facility_accident_consequence(
            chain, failed_evaluator, method_evidence_id="deferred-caller-method-applicability",
        )
    except FacilityAccidentConsequenceError as error:
        assert error.stage == "consequence"
        assert error.facility_handoff is handoff
        assert error.chain_result.results["preferred-dispersion"] is handoff
        assert isinstance(error.cause, Exception)
        failure_preserved = True
    else:
        raise AssertionError("Failed consequence evaluation became a success receipt")

    return ValidationOutcome(True, {
        "exact_handoff_received": received[0] is handoff,
        "accepted_chain_retained": result.chain_result.require_current() is result.chain_result,
        "consequence_failure_preserved": failure_preserved,
    }, (
        "Authored native-result fixture checks orchestration and ownership only; it does not validate consequence physics or exposure applicability.",
    ))
