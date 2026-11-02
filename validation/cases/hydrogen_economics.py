"""Deferred native economic composition; imports/cases() are metadata-only."""

import copy
import math
from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITATIONS = (
    "Implemented_unverified; these are deferred acceptance definitions, not execution evidence.",
    "Synthetic prices/financial/annual repetition and product-gate assumptions; no investment advice.",
    "Physical source retains unresolved pressure/utility/full-plant/sale boundaries with explicit cost-scope evidence.",
    "Native pyH2A annual gate-production/annual_sales convention, not measured product sales or market value.",
)


def cases():
    entries = (
        (
            "economics-native-direct",
            "validate_native_direct",
            ("actual native DCF identity", "full dict equivalence",
             "result requires one-use issuance; direct and replaced receipts rejected",
             "post-issuance LCOH mutation rejected by require_current"),
        ),
        (
            "economics-finite-link",
            "validate_finite_link",
            ("finite priced energy", "explicit annual linkage"),
        ),
        (
            "economics-undiscounted",
            "validate_undiscounted",
            ("independent finite zero-discount accounting",),
        ),
        (
            "economics-negative",
            "validate_negative",
            ("clock/basis/gaps", "no nearest-year fallback"),
        ),
        (
            "economics-failure-retention",
            "validate_failure_retention",
            ("actual partial native object", "overflow rejection"),
        ),
        (
            "economics-public-projection",
            "validate_public_projection",
            (
                "public SI/boundary registry",
                "legacy PV factory compatibility",
                "no overlapping billing",
            ),
        ),
        (
            "economics-source-cache",
            "validate_source_cache",
            ("actual PV cache/native mutation rejection", "cached source-proof mutation rejection"),
        ),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="hydrogen-economics",
            entrypoint=__name__ + ":" + entry,
            parameters={},
            invariants=invariants,
        )
        for name, entry, invariants in entries
    )


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _problem():
    from examples.hydrogen_economics import problem
    from h2physics.adapters.hydrogen_economics import NativeHydrogenEconomics

    return (*problem(), NativeHydrogenEconomics.from_installed())


def validate_native_direct(*, work_directory, **parameters):
    import dataclasses

    from h2physics.adapters.hydrogen_economics import (
        HydrogenEconomicsResult,
        evaluate_hydrogen_economics,
        native_input_dictionary,
    )

    projection, basis, inputs, window_cost, native = _problem()
    result = evaluate_hydrogen_economics(
        projection, basis, inputs, native=native, window_cost=window_cost
    )
    direct = native.native_class(
        copy.deepcopy(native_input_dictionary(basis, inputs)),
        print_info=False,
        check_processing=False,
    )
    _require(
        math.isclose(result.lcoh_usd_kg, direct.h2_cost, abs_tol=1e-10, rel_tol=1e-12),
        "Host bridge must return actual native LCOH without a replacement finance law",
    )
    _require(
        type(result.native_object) is native.native_class and result.native_provider is native,
        "Actual native object/provider identity",
    )
    _require(
        result.projection.source is projection.source
        and result.projection.quantities["exported_sale_h2_kg"] is None,
        "Original physical trace and unavailable sale ledger must survive",
    )
    _require(
        result.annual_arrays["annual_sales"].flags.writeable is False,
        "Caller output array isolation",
    )
    forged = {
        field.name: getattr(result, field.name)
        for field in dataclasses.fields(result)
        if field.init and field.name != "_issuer_token"
    }
    try:
        HydrogenEconomicsResult(**forged)
    except ValueError:
        pass
    else:
        raise AssertionError("Direct LCOH result construction bypassed native issuance")
    try:
        replace(result, lcoh_usd_kg=result.lcoh_usd_kg + 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Replacing an issued LCOH receipt reused its consumed token")
    result.require_current()
    old_lcoh = result.lcoh_usd_kg
    object.__setattr__(result, "lcoh_usd_kg", old_lcoh + 1.0)
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Post-issuance LCOH mutation remained current")
    finally:
        object.__setattr__(result, "lcoh_usd_kg", old_lcoh)
    return ValidationOutcome(
        True,
        {
            "native_lcoh_usd_kg": result.lcoh_usd_kg,
            "native_tree_sha256": native.source_sha256,
            "direct_difference_usd_kg": result.lcoh_usd_kg - direct.h2_cost,
        },
        LIMITATIONS,
    )


def validate_finite_link(*, work_directory, **parameters):
    from examples.hydrogen_economics import finance_for_projection
    from h2physics.adapters.hydrogen_economics import evaluate_hydrogen_economics

    projection, basis, inputs, cost, native = _problem()
    first = evaluate_hydrogen_economics(projection, basis, inputs, native=native, window_cost=cost)
    other_basis, other_inputs, other_cost = finance_for_projection(
        projection, tariff_multiplier=2.0
    )
    second = evaluate_hydrogen_economics(
        projection, other_basis, other_inputs, native=native, window_cost=other_cost
    )
    _require(
        math.isclose(other_cost.total_usd, 2 * cost.total_usd, rel_tol=1e-12),
        "Finite physical tariff linkage",
    )
    _require(
        second.lcoh_usd_kg > first.lcoh_usd_kg,
        "A higher explicit utility charge must reach native economics",
    )
    _require(
        projection.quantities["receiver_initial_h2_kg"] > 0
        and projection.quantities["generated_h2_kg"]
        != projection.quantities["receiver_final_h2_kg"],
        "Startup gas stock must not become generated H2",
    )
    return ValidationOutcome(
        True,
        {
            "finite_window_cost_usd": cost.total_usd,
            "annual_variable_cost_usd": inputs.variable_operating_cost_usd_year,
            "higher_tariff_lcoh_usd_kg": second.lcoh_usd_kg,
        },
        LIMITATIONS,
    )


def validate_undiscounted(*, work_directory, **parameters):
    from h2physics.adapters.hydrogen_economics import evaluate_hydrogen_economics

    projection, basis, inputs, cost, native = _problem()
    result = evaluate_hydrogen_economics(projection, basis, inputs, native=native, window_cost=cost)
    # Independent finite accounting only: zero discount/inflation/tax/debt,
    # no salvage/working capital/replacement. No general finance formula copied.
    lifetime_cost = 1000.0 + 4 * (17.0 + inputs.variable_operating_cost_usd_year)
    lifetime_kg = 4 * basis.annual_product_kg_at_gate
    expected = lifetime_cost / lifetime_kg
    _require(
        math.isclose(result.lcoh_usd_kg, expected, rel_tol=1e-10, abs_tol=1e-8),
        "Native zero-discount result differs from independent finite lifetime cost/mass accounting",
    )
    return ValidationOutcome(
        True,
        {
            "native_lcoh_usd_kg": result.lcoh_usd_kg,
            "undiscounted_difference_usd_kg": result.lcoh_usd_kg - expected,
        },
        LIMITATIONS,
    )


def validate_negative(*, work_directory, **parameters):
    from h2physics.adapters.hydrogen_economics import (
        PhysicalCostProjection,
        UtilityTariff,
        evaluate_hydrogen_economics,
    )
    from h2physics.core import Origin

    projection, basis, inputs, cost, native = _problem()
    rejected = 0
    operations = (
        lambda: PhysicalCostProjection.from_pv_electrolysis(
            projection.source,
            replace(projection.window, start_s=projection.window.start_s + 1),
            hydrogen_id=projection.hydrogen_id,
        ),
        lambda: replace(basis, unresolved_cost_resolutions={}).require(projection),
        lambda: replace(
            basis, annual_final_h2_inventory_kg=basis.annual_initial_h2_inventory_kg + 1.0
        ),
        lambda: evaluate_hydrogen_economics(
            projection,
            basis,
            replace(
                inputs,
                variable_operating_cost_usd_year=inputs.variable_operating_cost_usd_year + 1.0,
            ),
            native=native,
            window_cost=cost,
        ),
        lambda: projection.price_window(
            (
                UtilityTariff(
                    "stack_electricity_j", 1e-8, "USD", 2010, "fixture", "DC", Origin.SYNTHETIC
                ),
                UtilityTariff(
                    "pv_electricity_j", 1e-8, "USD", 2010, "fixture", "same-DC", Origin.SYNTHETIC
                ),
            )
        ),
    )
    for operation in operations:
        try:
            operation()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("An unresolved/mismatched annual boundary was accepted")
    values = dict(inputs.financial_values)
    for key in ("ref year", "basis year", "current year capital costs"):
        values[key] = 2017
    try:
        native.require_lookup_domain(
            replace(basis, base_year=2017), replace(inputs, financial_values=values)
        )
    except ValueError as error:
        _require(
            "nearest-year" in str(error),
            "Actual missing native lookup year must reject, not select2016",
        )
        rejected += 1
    else:
        raise AssertionError("Native historical nearest-year extrapolation was silently admitted")
    return ValidationOutcome(True, {"negative_boundaries_rejected": rejected}, LIMITATIONS)


def validate_failure_retention(*, work_directory, **parameters):
    from h2physics.adapters.hydrogen_economics import (
        HydrogenEconomicsError,
        evaluate_hydrogen_economics,
    )

    projection, basis, inputs, cost, native = _problem()
    huge = replace(inputs, depreciable_capital_usd=1e308, nondepreciable_capital_usd=1e308)
    try:
        evaluate_hydrogen_economics(projection, basis, huge, native=native, window_cost=cost)
    except HydrogenEconomicsError as error:
        _require(
            error.__cause__ is not None and error.native_object is not None,
            "Native overflow/failure must retain its original object and cause",
        )
        _require(
            type(error.native_object) is native.native_class and error.native_input is not None,
            "Retain actual attempted native DCF input/object",
        )
        return ValidationOutcome(
            True,
            {"actual_native_failure_retained": True, "cause_type": type(error.__cause__).__name__},
            LIMITATIONS,
        )
    raise AssertionError("A nonfinite native financial result was accepted")


def validate_public_projection(*, work_directory, **parameters):
    from types import SimpleNamespace

    from h2physics.adapters.hydrogen_economics import PhysicalCostProjection as LegacyProjection
    from h2physics.adapters.physical_economics import (
        QUANTITY_REGISTRY,
        PhysicalCostProjection,
        PhysicalEconomicProjection,
        QuantityDefinition,
        require_validated_projection,
    )

    p, b, f, c, n = _problem()
    _require(
        type(p) is PhysicalCostProjection and isinstance(p, PhysicalEconomicProjection),
        "Actual common public projection",
    )
    legacy = LegacyProjection.from_pv_electrolysis(p.source, p.window, hydrogen_id=p.hydrogen_id)
    _require(legacy.source is p.source, "Old PV factory retains original source")
    quote = c.line_items[0][0]
    _require(p.price_window((quote,)).line_items[0][0] is quote, "Retain original actual quote")
    old = replace(quote, quantity="stack_electricity_j")
    _require(
        legacy.price_window((old,)).total_usd == c.total_usd, "Legacy USD/J tariff correspondence"
    )
    c.require_current()
    stale_quote_cost = p.price_window((quote,))
    original_rate = quote.usd_per_j
    object.__setattr__(quote, "usd_per_j", original_rate * 1.5)
    try:
        stale_quote_cost.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A cost receipt accepted a mutated original tariff quote")
    object.__setattr__(quote, "usd_per_j", original_rate)
    _require(QUANTITY_REGISTRY["electrical_work_into_j"].unit == "J", "Explicit physical SI unit")
    rejected = 0
    for operation in (
        lambda: p.price_window((quote, old)),
        lambda: QuantityDefinition("invalid", "energy", "kWh", "wrong-unit"),
        lambda: require_validated_projection(SimpleNamespace()),
        lambda: LegacyProjection.from_pv_electrolysis(
            p.source,
            replace(p.window, selected_product_basis="harvested_h2_kg"),
            hydrogen_id=p.hydrogen_id,
        ),
    ):
        try:
            operation()
        except (ValueError, TypeError):
            rejected += 1
        else:
            raise AssertionError(
                "Unvalidated unit/source/unknown-product/overlap boundary accepted"
            )
    return ValidationOutcome(
        True,
        {"public_contract_negative_gates": rejected, "legacy_window_cost_usd": c.total_usd},
        LIMITATIONS,
    )


def validate_source_cache(*, work_directory, **parameters):
    from h2physics.adapters.hydrogen_economics import PhysicalCostProjection

    rejected = 0
    p, *_ = _problem()
    frame = p.source.steps[0].point.pv.native_scaled_iv
    frame.iloc[0, 0] = float(frame.iloc[0, 0]) + 1.0
    try:
        p.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed original native PV cache accepted")
    p2, *_ = _problem()
    cached = p2.source_binding.cached_snapshot
    object.__setattr__(
        cached,
        "quantities",
        {
            **cached.quantities,
            "electrical_work_into_j": cached.quantities["electrical_work_into_j"] + 1.0,
        },
    )
    try:
        p2.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed cached source proof accepted")
    fresh = PhysicalCostProjection.from_pv_electrolysis(
        p2.source, p2.window, hydrogen_id=p2.hydrogen_id
    )
    _require(fresh.source is p2.source, "Cache rejection must not mutate the actual source")
    fresh.source.native_system.arrays[0].module_parameters["R_s"] *= 2.0
    try:
        fresh.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed actual native PV system definition accepted")
    return ValidationOutcome(True, {"actual_source_cache_guards": rejected}, LIMITATIONS)
