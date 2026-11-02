"""Native conditional risk, source/receptor identity and credit-boundary checks."""

import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.conditional_risk import (
    ConditionalHarmBinding,
    ConditionalRiskError,
    ConditionalRiskNative,
    RiskBindingEvidence,
    RiskReceptor,
    conditional_risk,
    finite_source_sha256,
)
from h2physics.core import Origin, PropertyBasis, ThermoState
from h2physics.release import SourceLocation
from h2physics.sources import IntervalMassSource


@pytest.fixture(scope="module")
def native():
    target = Path(__file__).resolve().parents[1] / "artifacts/native_risk_packages"
    if not target.exists():
        pytest.skip("Reviewed native conditional-risk engine is separately installed")
    sys.path.insert(0, str(target))
    return ConditionalRiskNative.from_installed()


def authored_source():
    state = ThermoState(
        PropertyBasis("Hydrogen", "authored-test-reference", "normal"),
        1e5,
        300.0,
        1.0,
        1e5,
        0.0,
        0.0,
        "gas",
    )
    return IntervalMassSource(
        SourceLocation(
            "authored-source", "absolute-test-clock", "local-ENU", (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
        ),
        np.array([100.0, 101.0, 102.0]),
        np.array([0.01, 0.02]),
        state,
        Origin.SYNTHETIC,
        "authored-source-boundary",
        "isolation",
    )


def authored_case(native):
    r, c = native.risk_module, native.contracts
    evidence = RiskBindingEvidence(
        "source-binding", "conditional-field-assumption", "branch-partition", Origin.SYNTHETIC
    )
    receptor = RiskReceptor(
        "receptor",
        "local-ENU",
        "absolute-test-clock",
        (10.0, 0.0, 1.0),
        "receptor-position",
        Origin.SYNTHETIC,
    )
    bindings = {
        "ignited": ConditionalHarmBinding(
            0.3,
            "receptor",
            "local-ENU",
            "absolute-test-clock",
            (100.0, 110.0),
            "authored-incident-field",
            "declared-thermal-harm",
            (10.0, 0.0, 1.0),
            ("thermal-harm-evidence",),
            Origin.SYNTHETIC,
        ),
        "unignited": ConditionalHarmBinding(
            0.0,
            "receptor",
            "local-ENU",
            "absolute-test-clock",
            (100.0, 110.0),
            "authored-no-exposure",
            "declared-zero-harm",
            (10.0, 0.0, 1.0),
            ("zero-harm-evidence",),
            Origin.SYNTHETIC,
        ),
    }
    frequency = r.Frequency(
        asset_id="tank",
        scenario_id="leak",
        operating_case_id="operation",
        annual_frequency_per_year=1e-4,
        origin="user_supplied",
        source_digest="a" * 64,
        source_code_digest="b" * 64,
        evidence_ids=("frequency-evidence",),
    )
    branches = tuple(
        r.Branch(
            id=k,
            conditional_probability=p,
            probability_basis="partition-probabilities",
            probability_factor_ids=("ignition" if k == "ignited" else "nonignition",),
            harm_probability=bindings[k].probability,
            harm_factor_id=k + "-harm",
            harm_basis=bindings[k].response_model_id,
        )
        for k, p in (("ignited", 0.2), ("unignited", 0.8))
    )
    request = r.RiskInput(
        frequency=frequency,
        receptor_id=receptor.receptor_id,
        branches=branches,
        partition_basis=evidence.partition_evidence_id,
        mutually_exclusive_exhaustive=True,
    )
    ids = (
        "source-binding",
        "conditional-field-assumption",
        "branch-partition",
        "receptor-position",
        "thermal-harm-evidence",
        "zero-harm-evidence",
        "frequency-evidence",
        "partition-probabilities",
        "declared-thermal-harm",
        "declared-zero-harm",
    )
    context = c.Context(
        asset_id="tank",
        scenario_id="leak",
        operating_case_id="operation",
        mode="synthetic",
        evidence=tuple(
            c.Evidence(
                id=i,
                kind="synthetic",
                citation="Original hypothetical verification input",
                locator="tests/test_conditional_risk.py",
            )
            for i in ids
        ),
    )
    return request, context, authored_source(), receptor, bindings, evidence


def run(native, case):
    request, context, source, receptor, bindings, evidence = case
    return conditional_risk(
        native,
        request,
        context,
        source=source,
        receptor=receptor,
        harm_bindings=bindings,
        evidence=evidence,
    )


def test_actual_native_objects_and_exact_independent_rational_risk(native):
    case = authored_case(native)
    result = run(native, case)
    assert result.annual_harm_frequency_per_year == pytest.approx(
        float(Fraction(1, 10000) * Fraction(1, 5) * Fraction(3, 10)), abs=1e-20
    )
    assert result.original_request is case[0] and result.original_context is case[1]
    assert result.native_request is not case[0] and result.native_context is not case[1]
    assert isinstance(result.native_output, native.risk_module.RiskOutput)
    assert isinstance(result.native_receipt, native.contracts.Receipt)
    assert result.native_output.model_dump(mode="json") == result.native_receipt.outputs
    assert native.package.verify_receipt(result.native_receipt) == result.native_receipt
    assert not result.native_receipt.complete_facility_qra_claim
    assert result.source is case[2] and result.source_sha256 == finite_source_sha256(case[2])
    assert result.harm_bindings["ignited"] is case[4]["ignited"]


def test_native_upstream_and_branch_credit_cannot_be_applied_twice(native):
    request, context, *rest = authored_case(native)
    invalid_freq = request.frequency.model_copy(update={"included_factor_ids": ("ignition",)})
    request = request.model_copy(update={"frequency": invalid_freq})
    with pytest.raises(ConditionalRiskError, match="duplicate probability credit") as failure:
        run(native, (request, context, *rest))
    assert failure.value.original_request is request
    assert failure.value.native_receipt is None and failure.value.__cause__ is not None


def test_native_invalid_partition_revalidates_model_copy(native):
    request, context, *rest = authored_case(native)
    bad = request.branches[0].model_copy(update={"conditional_probability": 0.9})
    request = request.model_copy(update={"branches": (bad, request.branches[1])})
    with pytest.raises(ConditionalRiskError, match="sum to one"):
        run(native, (request, context, *rest))


def test_original_frequency_context_identity_is_native_admitted(native):
    request, context, *rest = authored_case(native)
    context = context.model_copy(update={"asset_id": "other-tank"})
    with pytest.raises(ConditionalRiskError, match="identity mismatch") as failure:
        run(native, (request, context, *rest))
    assert failure.value.stage == "native-risk-evaluation"
    assert failure.value.native_context.asset_id == "other-tank"


@pytest.mark.parametrize(
    "change",
    (
        {"clock_id": "other-clock"},
        {"frame_id": "other-frame"},
        {"receptor_id": "other-person"},
        {"position_m": (20.0, 0.0, 1.0)},
    ),
)
def test_receptor_meanings_cannot_be_changed_by_same_dimensions(native, change):
    case = list(authored_case(native))
    case[3] = replace(case[3], **change)
    with pytest.raises(ConditionalRiskError, match="differ"):
        run(native, case)


def test_harm_probability_and_model_must_match_actual_branch_binding(native):
    case = list(authored_case(native))
    case[4]["ignited"] = replace(case[4]["ignited"], probability=0.4)
    with pytest.raises(ConditionalRiskError, match="probability/model"):
        run(native, case)
    case = list(authored_case(native))
    case[4]["ignited"] = replace(case[4]["ignited"], response_model_id="other-model")
    with pytest.raises(ConditionalRiskError, match="probability/model"):
        run(native, case)


def test_no_missing_branch_or_unresolved_binding_evidence_is_filled(native):
    case = list(authored_case(native))
    case[4].pop("unignited")
    with pytest.raises(ConditionalRiskError, match="exactly one"):
        run(native, case)
    case = list(authored_case(native))
    case[1] = case[1].model_copy(update={"evidence": case[1].evidence[:-1]})
    with pytest.raises(ConditionalRiskError, match="does not resolve"):
        run(native, case)


def test_native_factor_reduces_harm_without_changing_branch_LOC_frequency(native):
    case = list(authored_case(native))
    r, c = native.risk_module, native.contracts
    factor = r.Factor(id="occupancy", probability=0.5, kind="occupancy", basis="explicit-occupancy")
    first = case[0].branches[0].model_copy(update={"factors": (factor,)})
    case[0] = case[0].model_copy(update={"branches": (first, case[0].branches[1])})
    ev = c.Evidence(
        id="explicit-occupancy",
        kind="synthetic",
        citation="Authored occupancy assumption",
        locator="test",
    )
    case[1] = case[1].model_copy(update={"evidence": (*case[1].evidence, ev)})
    result = run(native, case)
    assert result.annual_harm_frequency_per_year == pytest.approx(3e-6)
    assert result.native_output.branches[0].annual_frequency_per_year == pytest.approx(2e-5)


def test_source_actual_interval_contents_and_meanings_both_bind(native):
    case = authored_case(native)
    source = case[2]
    assert finite_source_sha256(source) != finite_source_sha256(
        replace(source, mass_kg=np.array([0.02, 0.01]))
    )
    assert finite_source_sha256(source) != finite_source_sha256(
        replace(source, end_reason="window_end")
    )
    with pytest.raises(ValueError, match="resolved"):
        finite_source_sha256(replace(source, origin=Origin.UNRESOLVED))


@pytest.mark.parametrize("value", (-0.1, 1.1, np.nan, True))
def test_missing_or_nonprobability_harm_is_not_promoted(value):
    with pytest.raises(ValueError):
        ConditionalHarmBinding(
            value,
            "r",
            "f",
            "clock",
            (0.0, 1.0),
            "source",
            "model",
            (0.0, 0.0, 0.0),
            ("evidence",),
            Origin.SYNTHETIC,
        )


def test_native_runtime_rebinding_rejects_without_replacing_engine(native, monkeypatch):
    case = authored_case(native)
    monkeypatch.setattr(native.risk_module, "risk", lambda x: None)
    with pytest.raises(ConditionalRiskError, match="functions/classes/source changed") as failure:
        run(native, case)
    assert failure.value.original_request is case[0]
    assert failure.value.native_output is None


def test_plain_mappings_do_not_masquerade_as_native_typed_inputs(native):
    case = list(authored_case(native))
    case[0] = case[0].model_dump(mode="python")
    with pytest.raises(ConditionalRiskError, match="Actual native"):
        run(native, case)


@pytest.mark.parametrize(
    "change", ({"state": None}, {"location": None}, {"state": {"pressure_pa": 1e5}})
)
def test_interval_wrapper_cannot_admit_missing_physical_state_or_location(native, change):
    case = list(authored_case(native))
    case[2] = replace(case[2], **change)
    with pytest.raises(ConditionalRiskError, match="Physical source") as failure:
        run(native, case)
    assert failure.value.source is case[2]
    assert isinstance(failure.value.__cause__, TypeError)


def test_mutated_nested_physical_state_is_not_promoted_as_valid_source():
    source = authored_source()
    object.__setattr__(source.state, "pressure_pa", -1.0)
    with pytest.raises(ValueError):
        finite_source_sha256(source)


@pytest.fixture(scope="module")
def actual_exposure_case(native):
    target = Path(__file__).resolve().parents[1] / "artifacts/native_hyram_packages"
    if not target.exists():
        pytest.skip("The separately reviewed native HyRAM is optional")
    sys.path.insert(0, str(target))
    from scripts.check_conditional_risk import authored_case as actual_case

    return actual_case(native)


def test_actual_native_exposure_risk_composition_preserves_originals(native, actual_exposure_case):
    result = run(native, actual_exposure_case[:6])
    exposure = actual_exposure_case[6]
    assert result.harm_bindings["ignited"].exposure_result is exposure
    assert 0 < exposure.probability < 1
    assert result.annual_harm_frequency_per_year == pytest.approx(
        1e-4 * 0.2 * 0.5 * exposure.probability
    )
    assert result.source.edges_s[-1] == 102.0 and exposure.support_s[-1] == 110.0


def test_changed_computed_probability_does_not_reuse_actual_native_provenance(actual_exposure_case):
    from h2physics.adapters.hyram_exposure import ExposureVerificationError

    exposure = actual_exposure_case[6]
    forged = replace(exposure, probability=0.9)
    with pytest.raises(ExposureVerificationError) as failure:
        ConditionalHarmBinding.from_exposure(
            forged, binding_evidence_id="altered", origin=Origin.SYNTHETIC
        )
    assert failure.value.supplied is forged
    assert failure.value.replayed.probability == exposure.probability
    assert failure.value.__cause__ is not None


def test_changed_computed_model_or_mean_cannot_keep_old_probability(actual_exposure_case):
    from h2physics.adapters.hyram_exposure import ExposureVerificationError

    exposure = actual_exposure_case[6]
    for selection in (
        replace(exposure.selection, model_id="tno"),
        replace(exposure.selection, normal_distribution_mean=4.0),
    ):
        forged = replace(exposure, selection=selection)
        with pytest.raises(ExposureVerificationError):
            ConditionalHarmBinding.from_exposure(
                forged, binding_evidence_id="altered", origin=Origin.SYNTHETIC
            )
