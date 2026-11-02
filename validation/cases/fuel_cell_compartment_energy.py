"""Deferred independently integrated native compartment extent audit."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="fuel-cell-native-reaction-port-energy-audit", profile="fuel-cell-native",
        entrypoint=__name__+":validate_extent", parameters={}, invariants=(
            "native H2/O2/water mass integrals compared as independent H2-equivalent extents",
            "caller kg and mol budgets retained without forcing native stoichiometric equality",
            "missing original finite electrical and thermal histories cannot imply combined energy closure",
        ),
    ),)


def validate_extent(*, work_directory, **parameters):
    from dataclasses import fields

    from h2physics.adapters.fuel_cell_compartment_energy import (
        FuelCellCompartmentEnergyLedger,
        audit_fuel_cell_compartment_energy,
        compartment_reaction_extent_audit,
    )
    from validation.cases.fuel_cell_compartments import _run, build_problem
    trace = _run(build_problem())
    audit = compartment_reaction_extent_audit(
        trace, mass_budget_kg=1e-10, mole_budget_mol=1e-8,
        deterministic_command_evidence_id="authored-shared-constant-command",
    )
    assert set(audit["native_mass_and_extent"]) == {"hydrogen", "oxygen", "water_vapor"}
    assert all(row[0] > 0. for row in audit["native_mass_and_extent"].values())
    assert audit["within_declared_budgets"]
    assert audit["mass_budget_kg"] == 1e-10
    assert audit["mole_budget_mol"] == 1e-8
    assert set(audit["mass_residual_kg"]) == set(audit["extent_residual_mol"])
    trace.require_current()
    try:
        audit_fuel_cell_compartment_energy(
            trace, None, None, mass_budget_kg=1e-10, mole_budget_mol=1e-8,
            deterministic_command_evidence_id="authored-command",
            reference_allocation_evidence_id="authored-no-energy-claim",
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Missing original electrical/thermal histories established energy closure")
    assert not trace.combined_reaction_energy_closed
    for receipt_type, names in (
        (type(trace), {"combined_reaction_energy_closed", "pressure_feedback_resolved"}),
        (FuelCellCompartmentEnergyLedger, {"combined_reaction_energy_closed"}),
    ):
        assert all(not item.init and item.default is False
                   for item in fields(receipt_type) if item.name in names)
    return ValidationOutcome(True, {
        "maximum_native_extent_mismatch_mol": max(abs(v) for v in audit["extent_residual_mol"].values()),
    }, ("Independent native reaction-port quadrature audit only",
        "No combined reaction-energy, membrane/solid or caloric-reference validation"))
