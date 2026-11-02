"""Deferred actual finite coolant heat observation and billing-scope contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="electrochemical-coolant-external-utility-scope", profile="fuel-cell",
        entrypoint=__name__+":validate_utility", parameters={}, invariants=(
            "finite-coolant trace is issued only by the original integration path",
            "external coolant heat profile retains actual shared-RHS integral and source clock",
            "stage duties preserve contiguous native intervals and matching coolant property basis",
            "already settled stack-to-coolant heat remains internal-transfer",
            "utility accounting excludes internal exchange from external duty quantities",
            "foreign reporting clock is rejected",
        ),
    ),)


def validate_utility(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.fuel_cell import synthetic_problem
    from h2physics.adapters.electrochemical_coolant_utility import ElectrochemicalCoolantHeatAdapter
    from h2physics.adapters.thermal_utilities import HeatDuty, HeatWindow, account_heat
    from h2physics.electrochemical_thermal import (
        FiniteCoolantReservoir,
        FiniteThermalStack,
        ThermalStackBoundary,
        ThermalStackStage,
    )
    from h2physics.thermo import CoolPropProperties

    model, initial, _ = synthetic_problem()
    properties = CoolPropProperties("Water")
    reservoir = FiniteCoolantReservoir(
        1., 101325., properties, (280., 350.), lambda **kwargs: 10.,
        model.boundary.thermal_boundary_id, model.evidence.clock_id,
        "authored-finite-coolant-boundary",
    )
    owner = FiniteThermalStack(model.stack, ThermalStackBoundary(
        1000., lambda ts, tc: 5., (280., 430.), initial.energy_basis_id,
        model.boundary.thermal_boundary_id,
    ))
    source = owner.run_with_coolant(
        320., properties.state_pt(101325., 300.),
        (ThermalStackStage("heat", 0., 1., 200., 300., "fuel_cell"),), reservoir=reservoir,
    )
    try:
        replace(source)
    except ValueError:
        pass
    else:
        raise AssertionError("A cloned coolant trace must not reseal the native result")
    window = HeatWindow(0., 1., reservoir.clock_id, "authored-full-coolant-window")
    external, internal = tuple(HeatDuty.bind(
        source, ElectrochemicalCoolantHeatAdapter(kind, "authored-boundary-scope"), window,
    ) for kind in ("external-coolant", "internal-stack-to-coolant"))
    assert external.snapshot.scope == "external-device-heat"
    assert internal.snapshot.scope == "internal-transfer"
    assert abs(sum(external.snapshot.heat_into_process_j)-10.) < 1e-8
    ledger = account_heat((external, internal), (), evidence_id="authored-external-only-duty",
                          energy_tolerance_j=1e-5)
    assert abs(ledger.quantities["required_heat_input_j"]-10.) < 1e-8
    assert ledger.quantities["required_heat_rejection_j"] == 0.
    ledger.require_current()
    try:
        external.adapter.snapshot(source, HeatWindow(0., 1., "foreign-clock", "authored-rejection"))
    except ValueError:
        pass
    else:
        raise AssertionError("Foreign clock admitted as original finite coolant heat duty")
    return ValidationOutcome(True, {"external_heat_j": float(sum(external.snapshot.heat_into_process_j))},
                             ("Authored constant external heat only; no purchased/recovered utility claim",
                              "No measured electrochemical thermal qualification"))
