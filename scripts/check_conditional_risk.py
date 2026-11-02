"""Actual native exposure-to-conditional-risk composition on authored inputs."""

import argparse
import hashlib
import sys
from pathlib import Path
from time import perf_counter


def authored_case(native):
    from h2physics.adapters.conditional_risk import (
        ConditionalHarmBinding,
        RiskBindingEvidence,
        RiskReceptor,
    )
    from h2physics.adapters.hyram_exposure import (
        ExposureHistory,
        ExposureReceptor,
        HyRAMExposure,
        NativeHarmSelection,
    )
    from h2physics.core import Origin
    from h2physics.release import SourceLocation
    from h2physics.sources import IntervalMassSource
    from h2physics.thermo.coolprop import CoolPropProperties

    provider = CoolPropProperties("Hydrogen")
    state = provider.state_pt(3e5, 300.0)
    source = IntervalMassSource(
        SourceLocation(
            "authored-finite-source",
            "authored-absolute-clock",
            "global-xyz",
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 0.0),
        ),
        [100.0, 101.0, 102.0],
        [0.0001, 0.0002],
        state,
        Origin.SYNTHETIC,
        "authored-declared-mass-budget",
        "isolation",
    )
    receptor = RiskReceptor(
        "authored-receptor",
        "global-xyz",
        "authored-absolute-clock",
        (4.0, -1.0, 1.5),
        "authored-receptor-location",
        Origin.SYNTHETIC,
    )
    field = ExposureHistory(
        ExposureReceptor(
            receptor.receptor_id,
            receptor.frame_id,
            receptor.position_m,
            "authored-local-incident-plane",
        ),
        [100.0, 105.0, 110.0],
        [40000.0, 0.0],
        "incident_radiant_flux",
        "W/m2",
        "left_hold",
        receptor.clock_id,
        "authored-conditional-incident-field",
        "author-declared-local-radiant-input",
        Origin.SYNTHETIC,
    )
    exposure = HyRAMExposure().thermal_response(
        field,
        NativeHarmSelection(
            "eise",
            5.0,
            "explicit-native-model-choice",
            "author-declared-applicability-not-calibrated",
            Origin.SYNTHETIC,
        ),
        additivity_evidence_id="author-declared-additive-dose-no-recovery",
    )
    harm = ConditionalHarmBinding.from_exposure(
        exposure, binding_evidence_id="actual-native-exposure-binding", origin=Origin.SYNTHETIC
    )
    no_harm = ConditionalHarmBinding(
        0.0,
        receptor.receptor_id,
        receptor.frame_id,
        receptor.clock_id,
        (100.0, 110.0),
        "declared-complement-branch",
        "author-declared-zero-harm",
        receptor.position_m,
        ("explicit-zero-harm-assumption",),
        Origin.SYNTHETIC,
    )
    evidence = RiskBindingEvidence(
        "declared-finite-source-binding",
        "conditional-field-independent-of-unsolved-source-transport",
        "authored-exclusive-partition",
        Origin.SYNTHETIC,
    )
    r, c = native.risk_module, native.contracts
    script = Path(__file__)
    frequency = r.Frequency(
        asset_id="authored-hydrogen-asset",
        scenario_id="authored-LOC",
        operating_case_id="authored-operating-state",
        annual_frequency_per_year=1e-4,
        origin="user_supplied",
        source_digest=c.digest({"rate_per_year": 1e-4, "role": "unmeasured-authored-rate"}),
        source_code_digest=hashlib.sha256(script.read_bytes()).hexdigest(),
        evidence_ids=("author-declared-annual-LOC-frequency",),
    )
    occupancy = r.Factor(
        id="occupancy", probability=0.5, kind="occupancy", basis="author-declared-occupancy"
    )
    branches = (
        r.Branch(
            id="ignited",
            conditional_probability=0.2,
            probability_basis="author-declared-partition-probabilities",
            probability_factor_ids=("ignition",),
            harm_probability=harm.probability,
            harm_factor_id="native-thermal-harm",
            harm_basis=harm.response_model_id,
            factors=(occupancy,),
        ),
        r.Branch(
            id="complement",
            conditional_probability=0.8,
            probability_basis="author-declared-partition-probabilities",
            probability_factor_ids=("nonignition",),
            harm_probability=0.0,
            harm_factor_id="declared-zero-harm",
            harm_basis=no_harm.response_model_id,
        ),
    )
    request = r.RiskInput(
        frequency=frequency,
        receptor_id=receptor.receptor_id,
        branches=branches,
        partition_basis=evidence.partition_evidence_id,
        mutually_exclusive_exhaustive=True,
    )
    # These entries are expressly authored numerical assumptions. This helper
    # does not turn a missing engineering citation into retrieved evidence.
    ids = (
        source.evidence_id,
        evidence.source_binding_evidence_id,
        evidence.source_to_harm_assumption_id,
        evidence.partition_evidence_id,
        receptor.position_evidence_id,
        *harm.evidence_ids,
        *no_harm.evidence_ids,
        *frequency.evidence_ids,
        "author-declared-partition-probabilities",
        harm.response_model_id,
        no_harm.response_model_id,
        occupancy.basis,
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
                citation="Authored numerical verification assumption",
                locator="scripts/check_conditional_risk.py",
            )
            for i in dict.fromkeys(ids)
        ),
    )
    return (
        request,
        context,
        source,
        receptor,
        {"ignited": harm, "complement": no_harm},
        evidence,
        exposure,
        provider,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--risk-packages", type=Path, default=Path("artifacts/native_risk_packages")
    )
    parser.add_argument(
        "--hyram-packages", type=Path, default=Path("artifacts/native_hyram_packages")
    )
    parser.add_argument("--use-main-scipy", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("research/conditional_risk.md"))
    args = parser.parse_args()
    if args.use_main_scipy:
        import scipy
    sys.path[:0] = [str(args.risk_packages.resolve()), str(args.hyram_packages.resolve())]
    from dataclasses import replace

    import scipy

    from h2physics.adapters.conditional_risk import (
        ConditionalHarmBinding,
        ConditionalRiskError,
        ConditionalRiskNative,
        conditional_risk,
    )

    root = Path(__file__).resolve().parents[1]
    paths = (
        "src/h2physics/adapters/conditional_risk.py",
        "tests/test_conditional_risk.py",
        "scripts/check_conditional_risk.py",
        "docs/CONDITIONAL_RISK.md",
        "research/risk_dependency.toml",
        "src/h2physics/adapters/hyram_exposure.py",
        "src/h2physics/sources.py",
    )

    def hashes():
        return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}

    before = hashes()
    start = perf_counter()
    native = ConditionalRiskNative.from_installed()
    case = authored_case(native)
    request, context, source, receptor, bindings, evidence, exposure, provider = case
    result = conditional_risk(
        native,
        request,
        context,
        source=source,
        receptor=receptor,
        harm_bindings=bindings,
        evidence=evidence,
    )
    expected = 1e-4 * 0.2 * 0.5 * exposure.probability

    def rejected(req=request, ctx=context, src=source, rec=receptor, bind=bindings):
        try:
            conditional_risk(
                native, req, ctx, source=src, receptor=rec, harm_bindings=bind, evidence=evidence
            )
        except ConditionalRiskError as error:
            return error.original_request is req and error.__cause__ is not None
        return False

    invalid_freq = request.frequency.model_copy(update={"included_factor_ids": ("ignition",)})
    bad_partition = request.branches[0].model_copy(update={"conditional_probability": 0.9})
    clone_context = context.model_copy(update={"asset_id": "different-asset"})
    forged_probability_rejected = forged_model_rejected = False
    try:
        ConditionalHarmBinding.from_exposure(
            replace(exposure, probability=0.9),
            binding_evidence_id="forged",
            origin=exposure.input.origin,
        )
    except Exception:
        forged_probability_rejected = True
    try:
        ConditionalHarmBinding.from_exposure(
            replace(exposure, selection=replace(exposure.selection, model_id="tno")),
            binding_evidence_id="forged",
            origin=exposure.input.origin,
        )
    except Exception:
        forged_model_rejected = True
    gates = {
        "actual native source/typed request/output/receipt preserved": result.source is source
        and result.original_request is request
        and isinstance(result.native_output, native.risk_module.RiskOutput),
        "actual exposure and native dose/probit/CDF retained": result.harm_bindings[
            "ignited"
        ].exposure_result
        is exposure
        and len(exposure.native_calls) > 0,
        "actual native risk agrees with independent explicit product below1e-20/year": abs(
            result.annual_harm_frequency_per_year - expected
        )
        < 1e-20,
        "all exclusive branch LOC frequencies sum to supplied rate": abs(
            sum(b.annual_frequency_per_year for b in result.native_output.branches) - 1e-4
        )
        < 1e-20,
        "native reproducible receipt verification": native.package.verify_receipt(
            result.native_receipt
        )
        == result.native_receipt,
        "source window and exposure support stay distinct without extension": tuple(
            source.edges_s[[0, -1]]
        )
        == (100.0, 102.0)
        and exposure.support_s == (100.0, 110.0),
        "native duplicate upstream credit rejects": rejected(
            request.model_copy(update={"frequency": invalid_freq})
        ),
        "native incomplete probability partition rejects": rejected(
            request.model_copy(update={"branches": (bad_partition, request.branches[1])})
        ),
        "native frequency/context mismatch rejects": rejected(ctx=clone_context),
        "receptor coordinate identity mismatch rejects": rejected(
            rec=replace(receptor, position_m=(14.0, -1.0, 1.5))
        ),
        "physical source missing state rejects": rejected(src=replace(source, state=None)),
        "changed computed exposure probability rejects": forged_probability_rejected,
        "changed computed exposure model rejects": forged_model_rejected,
        "complete facility/physical validation claims remain false": not result.native_receipt.complete_facility_qra_claim
        and not result.native_receipt.physical_validation_claim,
    }
    after = hashes()
    gates["executed source fingerprints unchanged"] = before == after
    elapsed = perf_counter() - start
    rows = [
        "# Native conditional single-LOC risk composition",
        "",
        f"Actual PRCT{native.version}, SciPy{scipy.__version__}; {elapsed:.9g}s.",
        "",
        "All masses, rates, branch/occupancy assumptions, fields and receptor positions are original verification inputs. "
        "The source has declared interval masses0.0001/0.0002kg in[100,101,102]s, an actual normal-H2 HEOS state "
        "at300K/300kPa and declared isolation. This is a supplied finite mass budget, not a new release prediction. "
        "The incident40000W/m2 for5s followed byzero5s at(4,-1,1.5)m is independently supplied. "
        "No source/transport/Flame calculation produces that field here; source-to-field linkage is an explicit conditional assumption.",
        "",
        f"Actual chosen native eise/mean5 exposure probability={exposure.probability:.12g}; "
        f"dose={exposure.thermal_dose:.12g}(W/m2)^(4/3)s. Supplied unmeasured LOC frequency=1e-4/year, "
        f"exclusive branch probabilities0.2/0.8 and conditional occupancy0.5. Actual native annual harm frequency="
        f"{result.annual_harm_frequency_per_year:.12g}/year; independent product={expected:.12g}/year.",
        "",
        "Frequency is an explicit rate, not inferred from alarms, source mass or dose and not converted to annual occurrence probability. "
        "Original/owned typed native request/context, actual typed native output, native receipt, finite source and actual exposure objects are retained. "
        "Native receipt normalization is internal; no user JSON, HTTP or file interface is required. "
        "The actual direct native output is cross-checked with the native receipt. "
        "No risk equation, probit coefficient or physical source engine is duplicated.",
        "",
        "Native/source guards reject duplicate credit, incomplete partitions, identity/provenance mismatch and replaced computed harm summaries. "
        "Native dependencies remain separate; no native source, raw process data or calibrated frequency database is bundled. "
        "This is not independent physical validation or complete facility QRA.",
        "",
        "| Gate | Pass |",
        "|---|---|",
        *(f"| {k} | {bool(v)} |" for k, v in gates.items()),
        "",
        f"Actual native code digest: `{native.source_sha256}`; frozen dependency artifact/license receipts are in risk_dependency.toml.",
        "",
        "| Executed host input | Begin SHA256 | End SHA256 |",
        "|---|---|---|",
        *(f"| `{p}` | `{v}` | `{after[p]}` |" for p, v in before.items()),
        "",
        "Primary native contract: [Process Risk Consequence Toolkit](https://github.com/lyullee/process-risk-consequence-toolkit). "
        "Installed optional code is Apache-2.0; the separately used HyRAM engine is GPL-3.0-only. "
        "Public native contracts and reviewed source/notice hashes do not establish engineering qualification.",
        "",
    ]
    destination = args.report if args.report.is_absolute() else root / args.report
    destination.write_text("\n".join(rows), encoding="utf-8", newline="\n")
    for k, v in gates.items():
        print(f"{'PASS' if v else 'FAIL'} {k}", flush=True)
    print(f"Actual native conditional-risk replay {elapsed:.6g}s; {destination.name}", flush=True)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    code = main()
    # Rejected-case traceback cycles can retain the local optional EOS object.
    # Collect unreachable replay frames before native interpreter shutdown.
    import gc

    gc.collect()
    raise SystemExit(code)
