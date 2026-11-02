"""Deferred actual transient interwall utility-scope contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="transient-exchanger-interwall-utility-scope", profile="flowing-heat-exchanger",
        entrypoint=__name__+":validate_utility", parameters={}, invariants=(
            "actual native transient per-side interwall integrals retain equal opposite increments",
            "original heat-duty profiles retain internal-transfer scope and source clock",
            "already settled internal heat is excluded from external utility billing quantities",
            "foreign heat window rejected without rerunning native model",
        ),
    ),)


def validate_utility(*, work_directory, **parameters):
    import numpy as np

    from h2physics.adapters.thermal_utilities import HeatDuty, HeatWindow, account_heat
    from h2physics.adapters.transient_exchanger_utility import (
        TransientExchangerInterwallHeatAdapter,
    )
    from validation.cases.transient_flowing_exchanger import build_trace

    trace = build_trace()
    window = HeatWindow(trace.points[0].time_s, trace.points[-1].time_s,
                        trace.clock_id, "authored-full-transient-window")
    base = trace.owner.finite_owner
    profiles = tuple(HeatDuty.bind(
        trace, TransientExchangerInterwallHeatAdapter(side.side_id, "authored-internal-heat-observation"),
        window,
    ) for side in (base.left, base.right))
    assert all(profile.snapshot.scope == "internal-transfer" for profile in profiles)
    assert all(profile.source is trace for profile in profiles)
    assert all(profile.snapshot.window is window for profile in profiles)
    tolerance = base.tolerances.energy_absolute_j
    mismatch = profiles[0].snapshot.heat_into_process_j+profiles[1].snapshot.heat_into_process_j
    assert np.max(np.abs(mismatch)) <= tolerance
    ledger = account_heat(profiles, (), evidence_id="authored-no-extra-internal-heat-credit",
                          energy_tolerance_j=tolerance)
    assert ledger.quantities["required_heat_input_j"] == 0.
    assert ledger.quantities["required_heat_rejection_j"] == 0.
    ledger.require_current()
    adapter = profiles[0].adapter
    try:
        adapter.snapshot(trace, HeatWindow(window.start_s, window.end_s, "foreign-clock",
                                           "authored-clock-rejection"))
    except ValueError:
        pass
    else:
        raise AssertionError("Foreign clock admitted as original internal heat window")
    return ValidationOutcome(True, {
        "maximum_interwall_increment_residual_j": float(np.max(np.abs(mismatch))),
        "external_heating_billed_j": ledger.quantities["required_heat_input_j"],
        "external_rejection_billed_j": ledger.quantities["required_heat_rejection_j"],
    }, ("Original transient model remains unverified; no measured HX validation",
        "No recoverable heat availability, external utility cost or performance inferred"))
