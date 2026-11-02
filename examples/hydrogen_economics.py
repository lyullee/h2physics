"""Synthetic financial/physical scenario, defined but not executed locally.

Quotes, annual representativeness and gate assumptions are authored examples;
they are neither current prices nor a calibrated plant investment assessment.
"""

from h2physics.adapters.hydrogen_economics import (
    AnnualFinancialBasis,
    AnnualFinancialInputs,
    NativeHydrogenEconomics,
    PhysicalCostProjection,
    ReportingWindow,
    UtilityTariff,
    evaluate_hydrogen_economics,
)
from h2physics.core import Origin


def finance_for_projection(projection, *, tariff_multiplier=1.0):
    quote = UtilityTariff(
        "electrical_work_into_j",
        1.3e-8 * tariff_multiplier,
        "USD",
        2010,
        "authored-USD2010-per-J-numerical-fixture",
        "charge-one-direct-DC-boundary-only",
        Origin.SYNTHETIC,
    )
    window_cost = projection.price_window((quote,))
    # These explicit constants assume repetition of a60s operating pattern and
    # an independently declared365-day year. No trajectory-to-year rule is inferred.
    repetitions, annual_seconds = 525600.0, 31536000.0
    generated = projection.quantities["generated_h2_kg"] * repetitions
    stock = projection.quantities["initial_h2_stock_kg"]
    basis = AnnualFinancialBasis(
        currency="USD",
        base_year=2010,
        operating_year_label=2033,
        seconds_in_operating_year=annual_seconds,
        annual_product_kg_at_gate=generated,
        annual_generated_h2_kg=generated,
        annual_initial_h2_inventory_kg=stock,
        annual_final_h2_inventory_kg=stock,
        annual_nonproduct_h2_out_kg=0.0,
        product_grade_id="authored-hypothetical-H2-grade-not-measured",
        product_pressure_pa=1e5,
        product_gate_evidence_id="synthetic-external-transfer-and-grade-assumption",
        representation="explicit_window_repetition",
        representation_evidence_id="authored60s-window-repeated525600-times; not-weather-evidence",
        annual_inventory_reconciliation_id="synthetic-interwindow-feed-and-product-takeoff-resets-stock",
        annual_repetition_evidence_id="same-normal-year-pattern-for-four-financial-years; synthetic",
        capacity_factor=None,
        capacity_factor_evidence_id="not-applied-separately; explicit-annual-production",
        unresolved_cost_resolutions={
            gap: "authored-additional31USD/year-scenario-scope:" + gap
            for gap in projection.unresolved
        },
        window_repetitions=repetitions,
        origin=Origin.SYNTHETIC,
    )
    # All21native financial inputs are explicit original test assumptions. No
    # Default.md or public cost/parameter table is loaded or transcribed.
    values = {
        "ref year": 2010,
        "startup year": 2033,
        "basis year": 2010,
        "current year capital costs": 2010,
        "startup time": 0,
        "plant life": 4,
        "depreciation length": 3,
        "depreciation type": "MACRS",
        "equity": 1.0,
        "interest": 0.017,
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
        depreciable_capital_usd=980.0,
        nondepreciable_capital_usd=20.0,
        fixed_operating_cost_usd_year=17.0,
        variable_operating_cost_usd_year=window_cost.total_usd * repetitions + 31.0,
        additional_variable_cost_usd_year=31.0,
        replacement_usd_by_analysis_year=(0.0,) * 5,
        financial_evidence={k: "authored-undiscounted-fixture:" + k for k in values},
        utility_scope_evidence_id="synthetic-pressure/water/thermal/auxiliary-scope; not-physical-closure",
        variable_cost_annual_basis_id="explicit-priced-window-repetition-plus-independent31USD/year",
        capital_scope_evidence_id="authored-capital-only; not-a-vendor-quotation",
        native_lookup_evidence_id="native-pyH2A-tables; exact2010-year-and3yr-MACRS-admitted",
    )
    return basis, inputs, window_cost


def problem():
    # Actual native PV/electrolysis example owner; no duplicate power/chemistry.
    from examples.pv_electrolysis import build_model, run_example

    trace = run_example(build_model())
    window = ReportingWindow(
        trace.initial.time_s,
        trace.final.time_s,
        trace.evidence.clock_id,
        "authored-full-source-reporting-window",
        "generated_h2_kg",
    )
    projection = PhysicalCostProjection.from_pv_electrolysis(trace, window, hydrogen_id="hydrogen")
    basis, inputs, window_cost = finance_for_projection(projection)
    return projection, basis, inputs, window_cost


def run_example():
    projection, basis, inputs, window_cost = problem()
    return evaluate_hydrogen_economics(
        projection,
        basis,
        inputs,
        native=NativeHydrogenEconomics.from_installed(),
        window_cost=window_cost,
    )


if __name__ == "__main__":
    raise SystemExit(
        "Execution deferred: call run_example() only in the authorized HPC environment."
    )
