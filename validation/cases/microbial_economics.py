"""Deferred actual MEC/native economics cases; metadata construction only."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Implemented_unverified; no local scientific/native execution.",
    "Synthetic microbial/cathode/caloric and economic inputs; no material or economic validation.",
    "Batch H2 generation is not harvest/sale; annual reset/grade/cost scope are explicit scenario assumptions.",
    "Native DCF/annual/tariff laws remain solely in the existing economics owner.",
)


def cases():
    definitions = (
        (
            "mec-economics-owner",
            "validate_owner",
            ("actual MEC/pyH2A identity", "same original economic owner result"),
        ),
        (
            "mec-economics-link",
            "validate_link",
            ("finite MEC electrical pricing", "explicit annual linkage"),
        ),
        (
            "mec-economics-guards",
            "validate_guards",
            ("no harvest/sale inference", "window/reference/mutation guards"),
        ),
        (
            "mec-economics-failure",
            "validate_failure",
            ("actual failed native object", "original exception chain"),
        ),
        (
            "mec-economics-public-projection",
            "validate_public_projection",
            (
                "actual common source-neutral projection",
                "original MEC producer hook",
                "explicit generic boundaries",
            ),
        ),
        (
            "mec-economics-producer-mutation",
            "validate_producer_mutation",
            ("producer root-cache rejection", "actual native phase-state rejection"),
        ),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="microbial-economics",
            entrypoint=__name__ + ":" + entry,
            parameters={},
            invariants=invariants,
        )
        for name, entry, invariants in definitions
    )


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _problem():
    from examples.microbial_economics import problem
    from h2physics.adapters.hydrogen_economics import NativeHydrogenEconomics

    return *problem(), NativeHydrogenEconomics.from_installed()


def validate_owner(*, work_directory, **parameters):
    from h2physics.adapters.hydrogen_economics import evaluate_hydrogen_economics
    from h2physics.adapters.microbial_cell import MicrobialCellTrace
    from h2physics.adapters.microbial_economics import evaluate_microbial_economics

    p, b, f, c, n = _problem()
    actual = evaluate_microbial_economics(p, b, f, native=n, window_cost=c)
    direct = evaluate_hydrogen_economics(p, b, f, native=n, window_cost=c)
    _require(actual.lcoh_usd_kg == direct.lcoh_usd_kg, "No replacement DCF or annual law")
    _require(
        actual.projection is p and type(actual.projection.source) is MicrobialCellTrace,
        "Actual MEC source identity",
    )
    _require(type(actual.native_object) is n.native_class, "Actual pyH2A object")
    _require(
        p.quantities["harvested_h2_kg"] is None and p.quantities["exported_sale_h2_kg"] is None,
        "No harvest/sale inference",
    )
    return ValidationOutcome(
        True,
        {
            "native_lcoh_usd_kg": actual.lcoh_usd_kg,
            "owner_difference_usd_kg": actual.lcoh_usd_kg - direct.lcoh_usd_kg,
            "generated_H2_kg": p.quantities["generated_h2_kg"],
        },
        LIMITS,
    )


def validate_link(*, work_directory, **parameters):
    from examples.microbial_economics import financial_scenario
    from h2physics.adapters.microbial_economics import evaluate_microbial_economics

    p, b, f, c, n = _problem()
    first = evaluate_microbial_economics(p, b, f, native=n, window_cost=c)
    b2, f2, c2 = financial_scenario(p, tariff_multiplier=2.0)
    second = evaluate_microbial_economics(p, b2, f2, native=n, window_cost=c2)
    _require(
        c2.total_usd == 2 * c.total_usd, "Existing finite tariff owner must price actual MEC work"
    )
    _require(
        second.lcoh_usd_kg > first.lcoh_usd_kg, "Explicit tariff reaches native financial input"
    )
    _require(
        p.quantities["cell_initial_h2_kg"] > 0
        and p.quantities["generated_h2_kg"] != p.quantities["cell_final_h2_kg"],
        "Initial H2 stock is separate",
    )
    return ValidationOutcome(
        True,
        {
            "window_cost_usd": c.total_usd,
            "MEC_work_j": p.quantities["stack_electricity_j"],
            "higher_tariff_native_lcoh_usd_kg": second.lcoh_usd_kg,
        },
        LIMITS,
    )


def validate_guards(*, work_directory, **parameters):
    from h2physics.adapters.hydrogen_economics import UtilityTariff
    from h2physics.adapters.microbial_economics import MicrobialCostProjection
    from h2physics.core import Origin

    p, b, f, c, n = _problem()
    rejected = 0
    for operation in (
        lambda: MicrobialCostProjection.from_microbial_cell(
            p.source, replace(p.window, start_s=p.window.start_s + 0.1), hydrogen_id=p.hydrogen_id
        ),
        lambda: MicrobialCostProjection.from_microbial_cell(
            p.source,
            replace(p.window, selected_product_basis="receiver_stock_increase_kg"),
            hydrogen_id=p.hydrogen_id,
        ),
        lambda: replace(b, unresolved_cost_resolutions={}).require(p),
        lambda: p.price_window(
            (
                UtilityTariff(
                    "pv_electricity_j",
                    1e-8,
                    "USD",
                    2010,
                    "fixture",
                    "not-a-MEC-PV-boundary",
                    Origin.SYNTHETIC,
                ),
            )
        ),
        lambda: replace(p, source_fingerprint="0" * 64),
        lambda: replace(
            p, source=replace(p.source, electric_work_into_j=p.source.electric_work_into_j + 1.0)
        ),
    ):
        try:
            operation()
        except (ValueError, TypeError):
            rejected += 1
        else:
            raise AssertionError("Mismatched/unknown MEC reporting boundary accepted")
    _require(p.require_current() is p, "Rejected copies must leave original source intact")
    return ValidationOutcome(True, {"negative_boundary_guards": rejected}, LIMITS)


def validate_failure(*, work_directory, **parameters):
    from h2physics.adapters.hydrogen_economics import HydrogenEconomicsError
    from h2physics.adapters.microbial_economics import (
        MicrobialEconomicsError,
        evaluate_microbial_economics,
    )

    p, b, f, c, n = _problem()
    huge = replace(f, depreciable_capital_usd=1e308, nondepreciable_capital_usd=1e308)
    try:
        evaluate_microbial_economics(p, b, huge, native=n, window_cost=c)
    except MicrobialEconomicsError as error:
        _require(
            isinstance(error.__cause__, HydrogenEconomicsError),
            "Original financial failure must remain the immediate cause",
        )
        _require(
            error.original_error is error.__cause__
            and error.native_object is error.original_error.native_object,
            "Preserve actual attempted native object and original error",
        )
        _require(
            error.native_object is not None and error.source_trace is p.source,
            "Actual native/MEC identity on failure",
        )
        return ValidationOutcome(
            True,
            {
                "original_native_failure_retained": True,
                "original_cause_type": type(error.original_error.__cause__).__name__,
            },
            LIMITS,
        )
    raise AssertionError("Nonfinite native financial result was accepted")


def validate_public_projection(*, work_directory, **parameters):
    from h2physics.adapters.microbial_economics import MicrobialCostProjection
    from h2physics.adapters.physical_economics import (
        QUANTITY_REGISTRY,
        PhysicalCostProjection,
        PhysicalEconomicProjection,
        SourceAuditError,
    )

    p, b, f, c, n = _problem()
    _require(
        type(p) is PhysicalCostProjection and isinstance(p, PhysicalEconomicProjection),
        "MEC must use the real common projection",
    )
    _require(
        p.source.require_current() is p.source
        and p.source.owner.verify_result(p.source) is p.source,
        "Original producer trace identity",
    )
    _require(p.source.geometry is p.source.owner.geometry, "Actual retained electrode geometry")
    _require(
        "producer" in p.verification_kind,
        "Source audit status must preserve the producer-seal meaning",
    )
    _require(
        QUANTITY_REGISTRY["electrical_work_into_j"].unit == "J"
        and p.quantity_boundaries["electrical_work_into_j"].basis_id
        == p.source.evidence.caloric_basis_id,
        "Actual quantity/unit/reference registry",
    )
    _require(
        p.quantities["harvested_h2_kg"] is None and p.quantities["sold_h2_kg"] is None,
        "No harvest/sale promotion",
    )
    forged = replace(p.source, hydrogen_generated_mol=p.source.hydrogen_generated_mol + 1.0)
    try:
        MicrobialCostProjection.from_microbial_cell(forged, p.window, hydrogen_id=p.hydrogen_id)
    except SourceAuditError as error:
        _require(
            error.source is forged and error.original_error is error.__cause__,
            "Retain failing original source and producer exception",
        )
    else:
        raise AssertionError("An unsealed replaced producer result was admitted")
    return ValidationOutcome(
        True,
        {
            "common_projection_and_producer_seal": True,
            "retained_area_m2": p.source.geometry.active_area_m2,
        },
        LIMITS,
    )


def validate_producer_mutation(*, work_directory, **parameters):
    p, b, f, c, n = _problem()
    root = p.source.steps[0].native_root_result
    root.iterations += 1
    rejected = 0
    try:
        p.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Mutated original root cache accepted")
    p2, *_ = _problem()
    native = p2.source.native_cathode.phases[2]
    native.electric_potential += 0.01
    try:
        p2.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed actual native electrode state accepted")
    return ValidationOutcome(True, {"producer_native_cache_mutations_rejected": rejected}, LIMITS)
