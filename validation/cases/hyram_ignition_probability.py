"""Deferred contract check for the optional HyRAM+ ignition-rate kernel."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hyram-hydrogen-ignition-probability-native-contract",
        profile="hyram-overpressure",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "the adapter calls the installed native HyRAM+ rate-bin function",
            "custom thresholds and immediate/delayed probabilities reach the native function unchanged",
            "immediate and delayed probabilities remain absolute relative to one release",
            "the exact threshold boundary follows the native engine bin convention",
            "the result captures the HyRAM version and native module SHA-256",
            "the installed default hydrogen table is captured without copying its values into this project",
            "a result does not establish ignition occurrence, event frequency or facility risk",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    from math import isclose
    from unittest.mock import patch

    from h2physics.adapters.hyram_ignition import (
        HyRAMIgnitionTable,
        evaluate_hyram_ignition_probability,
        hyram_default_hydrogen_ignition_table,
    )
    from h2physics.core import Origin

    table = HyRAMIgnitionTable(
        table_id="synthetic-rate-bins-v1", fuel_species="h2",
        flow_thresholds_kg_s=(0.1,),
        immediate_probability=(0.01, 0.05), delayed_probability=(0.02, 0.04),
        evidence_id="synthetic-contract-table", origin=Origin.SYNTHETIC,
    )
    low = evaluate_hyram_ignition_probability(0.05, table=table)
    edge = evaluate_hyram_ignition_probability(0.1, table=table)
    high = evaluate_hyram_ignition_probability(2.0, table=table)
    if (low.immediate_probability, low.delayed_probability) != (0.01, 0.02):
        raise AssertionError("Native lower-bin selection changed")
    if (edge.immediate_probability, edge.delayed_probability) != (0.05, 0.04):
        raise AssertionError("Native exact-threshold selection changed")
    if (high.immediate_probability, high.delayed_probability) != (0.05, 0.04):
        raise AssertionError("Native upper-bin selection changed")
    for result in (low, edge, high):
        if not result.hyram_version or len(result.native_module_sha256) != 64:
            raise AssertionError("Native provider identity was not retained")
        if not isclose(result.total_probability,
                       result.immediate_probability + result.delayed_probability,
                       rel_tol=0., abs_tol=1e-15):
            raise AssertionError("Absolute ignition branch accounting does not close")
    for bad_rate in (-0.1, float("nan")):
        try:
            evaluate_hyram_ignition_probability(bad_rate, table=table)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid release-rate input was accepted")
    try:
        HyRAMIgnitionTable(
            table_id="invalid-total", fuel_species="h2", flow_thresholds_kg_s=(),
            immediate_probability=(0.7,), delayed_probability=(0.4,),
            evidence_id="invalid synthetic table", origin=Origin.SYNTHETIC,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Mutually exclusive ignition branches above unity were admitted")
    try:
        HyRAMIgnitionTable(
            table_id="nonhydrogen", fuel_species="ch4", flow_thresholds_kg_s=(),
            immediate_probability=(0.,), delayed_probability=(0.,),
            evidence_id="nonhydrogen synthetic table", origin=Origin.SYNTHETIC,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A non-hydrogen table was admitted")
    with patch("h2physics.adapters.hyram_ignition.importlib.import_module",
               side_effect=ModuleNotFoundError("synthetic missing optional HyRAM+")):
        try:
            evaluate_hyram_ignition_probability(0.05, table=table)
        except ModuleNotFoundError:
            pass
        else:
            raise AssertionError("Missing optional HyRAM+ dependency did not fail explicitly")
    defaults = hyram_default_hydrogen_ignition_table()
    if defaults.fuel_species.lower() not in {"h2", "hydrogen"}:
        raise AssertionError("Installed HyRAM default table is not hydrogen-specific")
    return ValidationOutcome(True, {
        "low_rate_immediate_probability": low.immediate_probability,
        "threshold_immediate_probability": edge.immediate_probability,
        "captured_default_table_sha256": defaults.content_sha256,
    }, ("Synthetic table checks API routing only; the native correlation is not independently validated.",))
