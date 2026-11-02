"""Actual MEC -> existing native pyH2A composition with synthetic economics.

Not executed locally. Annual reset/takeoff/grade and all financial/price inputs
are explicit hypothetical assumptions, not measured harvest or investment data.
"""

from h2physics.adapters.hydrogen_economics import (
    AnnualFinancialBasis,
    AnnualFinancialInputs,
    NativeHydrogenEconomics,
    ReportingWindow,
    UtilityTariff,
)
from h2physics.adapters.microbial_economics import (
    MicrobialCostProjection,
    evaluate_microbial_economics,
)
from h2physics.core import Origin


def financial_scenario(projection, *, tariff_multiplier=1.0):
    quote = UtilityTariff(
        "electrical_work_into_j",
        1.7e-8 * tariff_multiplier,
        "USD",
        2010,
        "authored-MEC-electric-charge; not-a-market-price",
        "MEC-external-applied-work-only",
        Origin.SYNTHETIC,
    )
    cost = projection.price_window((quote,))
    # Explicit authored2s-window repetition. This is NOT inferred from duration.
    repetitions, annual_seconds = 15768000.0, 31536000.0
    generated = projection.quantities["generated_h2_kg"] * repetitions
    stock = projection.quantities["initial_h2_stock_kg"]
    basis = AnnualFinancialBasis(
        currency="USD",
        base_year=2010,
        operating_year_label=2034,
        seconds_in_operating_year=annual_seconds,
        annual_product_kg_at_gate=generated,
        annual_generated_h2_kg=generated,
        annual_initial_h2_inventory_kg=stock,
        annual_final_h2_inventory_kg=stock,
        annual_nonproduct_h2_out_kg=0.0,
        product_grade_id="authored-hypothetical-conditioned-H2-not-observed",
        product_pressure_pa=1e5,
        product_gate_evidence_id="synthetic-gate-assumption; no-MEC-harvest-model",
        representation="explicit_window_repetition",
        representation_evidence_id="authored2s-pattern-repeated15768000-times; no-annual-kinetic-validation",
        annual_inventory_reconciliation_id="hypothetical-interwindow-substrate/nutrient/feed-biomass-and-gas-reset",
        annual_repetition_evidence_id="hypothetical-same-normal-year-through-four-year-finance-life",
        capacity_factor=None,
        capacity_factor_evidence_id="not-reapplied-to-explicit-annual-kg",
        unresolved_cost_resolutions={
            gap: "authored-extra37USD/year-financial-scope-only:" + gap
            for gap in projection.unresolved
        },
        window_repetitions=repetitions,
        origin=Origin.SYNTHETIC,
    )
    values = {
        "ref year": 2010,
        "startup year": 2034,
        "basis year": 2010,
        "current year capital costs": 2010,
        "startup time": 0,
        "plant life": 4,
        "depreciation length": 3,
        "depreciation type": "MACRS",
        "equity": 1.0,
        "interest": 0.013,
        "debt": "Constant",
        "startup cost fixed": 1.0,
        "startup revenues": 1.0,
        "startup cost variable": 1.0,
        "decommissioning": 0.0,
        "salvage": 0.0,
        "inflation": 0.0,
        "irr": 0.0,
        "state tax": 0.0,
        "federal tax": 0.0,
        "working capital": 0.0,
    }
    inputs = AnnualFinancialInputs(
        financial_values=values,
        construction_fractions=(1.0,),
        depreciable_capital_usd=760.0,
        nondepreciable_capital_usd=40.0,
        fixed_operating_cost_usd_year=23.0,
        variable_operating_cost_usd_year=cost.total_usd * repetitions + 37.0,
        additional_variable_cost_usd_year=37.0,
        replacement_usd_by_analysis_year=(0.0,) * 5,
        financial_evidence={k: "authored-MEC-financial-fixture:" + k for k in values},
        utility_scope_evidence_id="synthetic-feed/activities/anode/conditioning/heat/auxiliary allowance; unresolved-physics",
        variable_cost_annual_basis_id="explicit-existing-owner-priced-MEC-work-repetition-plus37USD/year",
        capital_scope_evidence_id="authored-capital-allowance; not-vendor-or-scale-qualified",
        native_lookup_evidence_id="existing-pyH2A-exact2010-year-and3yr-MACRS-envelope",
    )
    return basis, inputs, cost


def problem():
    from examples.microbial_cell import build_problem

    model, initial, stages = build_problem()
    trace = model.run(initial, stages)
    window = ReportingWindow(
        stages[0].start_s,
        stages[-1].end_s,
        trace.evidence.clock_id,
        "authored-complete-MEC-source-window",
        "generated_h2_kg",
    )
    projection = MicrobialCostProjection.from_microbial_cell(trace, window, hydrogen_id="hydrogen")
    return projection, *financial_scenario(projection)


def run_example():
    projection, basis, inputs, cost = problem()
    return evaluate_microbial_economics(
        projection, basis, inputs, native=NativeHydrogenEconomics.from_installed(), window_cost=cost
    )


if __name__ == "__main__":
    raise SystemExit(
        "Scientific execution deferred to the authorized microbial-economics HPC entrypoint."
    )
