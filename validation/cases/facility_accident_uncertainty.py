"""Synthetic deferred contract for source-bound consequence uncertainty rows."""

from functools import partial

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


class _SyntheticConsequence:
    def __init__(self, facility_handoff, scale):
        self.facility_handoff = facility_handoff
        self.scale = scale
        self.synthetic_metric = scale*0.125

    def require_current(self):
        self.facility_handoff.require_current()
        if self.synthetic_metric != self.scale*0.125:
            raise ValueError("Synthetic consequence response changed")
        return self


def _synthetic_consequence_evaluator(facility_handoff, *, scale):
    return _SyntheticConsequence(facility_handoff, scale)


def cases():
    return (ValidationCase(
        identifier="facility-accident-source-bound-uncertainty",
        profile="joint-uncertainty",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "each joint sample runs through the existing typed accident and consequence owners",
            "the scalar reader retains the exact source, dispersion and consequence receipt",
            "existing joint QMC propagation rejects post-capture mutation of source-bound outputs",
            "caller-supplied synthetic outputs do not imply exposure physics or event frequency",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from types import SimpleNamespace

    from scipy.stats import uniform

    from examples.facility_protection import make_case
    from h2physics.adapters.facility_accident_chain import (
        FacilityAccidentChain,
        FacilityDispersionHandoff,
    )
    from h2physics.adapters.facility_accident_uncertainty import (
        FacilityAccidentUncertaintyResponse,
        facility_accident_consequence_uncertain_model,
    )
    from h2physics.core import Origin
    from h2physics.dispersion import DispersionScenario, HydrogenReleaseFamily
    from h2physics.observations import Variable
    from h2physics.research.joint_uncertainty import (
        JointParameter,
        JointParameterSpace,
        joint_qmc_design,
        propagate_joint,
    )
    from h2physics.scenarios import OperationalScenario, ScenarioNode, ScenarioOutput
    from h2physics.uncertainty import (
        IndependentParameterSpace,
        ParameterDistribution,
        UncertaintyEvidence,
    )

    binding = make_case()["source"]
    family = HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN
    evidence_id = "synthetic-facility-uncertainty-evidence"
    boundary = SimpleNamespace(
        mass_source=binding.source,
        footprint_evidence_id="synthetic-footprint-evidence",
        require_current=binding.source.require_current,
    )
    native_result = SimpleNamespace(
        accepted=True, boundary=boundary,
        native_output={"synthetic_profile": [0.1, 0.2]},
    )
    request = DispersionScenario(family, {
        "source": binding.source,
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
               return_value=native_result):
        execution = request.run()
    handoff = FacilityDispersionHandoff(
        binding, execution, None, evidence_id, family, 1e30, 1e30,
    )

    def chain_factory(_parameters):
        scenario = OperationalScenario("synthetic-facility-uncertainty", (
            ScenarioNode("finite-operation", lambda: binding.run, {}, evidence_id),
            ScenarioNode("finite-source", lambda run: binding,
                         {"run": ScenarioOutput("finite-operation")}, evidence_id),
            ScenarioNode("preferred-dispersion", lambda source: handoff,
                         {"source": ScenarioOutput("finite-source")}, evidence_id),
        ))
        return FacilityAccidentChain(scenario, family, evidence_id)

    def evaluator_factory(values):
        scale = values["response_scale"]
        return partial(_synthetic_consequence_evaluator, scale=scale)

    model = facility_accident_consequence_uncertain_model(
        chain_factory=chain_factory,
        evaluator_factory=evaluator_factory,
        output_reader=lambda run: {
            "synthetic_metric": run.consequence.consequence_result.synthetic_metric,
        },
        outputs=(Variable("synthetic_metric", "synthetic_consequence_output", "1",
                          basis_id="nonphysical-authored-contract"),),
        evidence=UncertaintyEvidence(
            "synthetic-accident-consequence", "authored-contract-revision",
            "fresh-deterministic-owner-per-row", "software-contract-only", Origin.SYNTHETIC,
        ),
        method_evidence_id="authored-nonphysical-consequence-method",
    )
    latent = IndependentParameterSpace((ParameterDistribution(
        Variable("u", "latent_coordinate", "1"), uniform(), "synthetic-uniform-v1",
        "authored-latent-law", Origin.SYNTHETIC, 0.0, 1.0,
    ),), "synthetic-latent-space", "synthetic-reference")
    space = JointParameterSpace(
        latent,
        (JointParameter(Variable("response_scale", "synthetic_scale", "1"),
                        1.0, 2.0, "authored-response-scale-law"),),
        lambda values: {"response_scale": 1.0+values["u"]},
        "authored-one-dimensional-joint-law", "synthetic-dependence-evidence",
        "authored-transform-v1",
    )
    design = joint_qmc_design(space, power=2, seed=17)
    result = propagate_joint(space, design, model, scenario_id="synthetic-accident-consequence")
    responses = []
    for evaluation in result.evaluations:
        original = evaluation.raw.original_response
        receipt = original.raw
        assert type(receipt) is FacilityAccidentUncertaintyResponse
        assert receipt.require_current() is receipt
        assert evaluation.outputs["synthetic_metric"] == evaluation.parameters["response_scale"]*0.125
        assert receipt.run.facility_handoff is receipt.run.chain_result.results["preferred-dispersion"]
        responses.append(receipt)

    mutated = responses[0].reader_response
    old_value = mutated["synthetic_metric"]
    mutated["synthetic_metric"] = old_value+1.0
    try:
        result.require_current()
    except ValueError:
        stale_output_rejected = True
    else:
        raise AssertionError("Joint propagation failed to recheck a source-bound consequence response")
    mutated["synthetic_metric"] = old_value
    result.require_current()
    return ValidationOutcome(True, {
        "accepted_rows": len(result.evaluations),
        "source_bound_receipts": len(responses),
        "stale_output_rejected": stale_output_rejected,
    }, (
        "Entire fixture is synthetic; it validates only ownership/plumbing, not exposure, consequence laws, risk or event frequency.",
    ))
