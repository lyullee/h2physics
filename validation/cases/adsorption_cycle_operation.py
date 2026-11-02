"""Deferred actual native scheduled endpoint audit, not accepted-step replay."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="adsorption-native-cycle-endpoint-inventory", profile="finite-adsorption-vessel",
        entrypoint=__name__ + ":validate_cycle_operation",
        invariants=("existing native runner owns every integration step",
                    "actual slot/cycle endpoints retain clock and independent inventories",
                    "native energy reference and raw run are retained",
                    "finite product reporting refuses an empty closed-run product window",
                    "changed native checkpoint data invalidates the receipt",
                    "PsaCycleRun cannot be directly fabricated or cloned after owner issuance"),
    ),)


def validate_cycle_operation(*, work_directory, **parameters):
    del parameters
    from dataclasses import fields, replace
    from pathlib import Path

    from h2physics.adapters.adsorption_cycle_operation import (
        adsorption_product_window,
        run_adsorption_cycle_operation,
    )
    from h2physics.adapters.psa_cycle import PsaCycleEvidence, PsaCycleNative, PsaDynaCycle
    from h2physics.adsorption import AdsorptionBasis, AdsorptionDomain
    from h2physics.core import Origin
    from scripts.check_psa_cycle import authored_case

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    native = PsaCycleNative.from_installed(source_id="separately-installed-pinned-psa-dyna")
    basis = AdsorptionBasis("authored-warm-H2-N2", ("H2", "N2"), "mol/kg-dry-solid:absolute",
                            native.source_id, "authored-cycle-parameters", ("authored-software-contract",),
                            loading_definition="absolute")
    owner = PsaDynaCycle(native, authored_case(closed=True), basis=basis,
        domain=AdsorptionDomain(290., 350., 5e5, 5e4),
        evidence=PsaCycleEvidence("authored-native-cycle", "native-bed-original-energy-reference",
                                  "warm-ideal-gas", Origin.SYNTHETIC),
        temporary_workspace=destination)
    receipt = run_adsorption_cycle_operation(
        owner, start_time_s=7., clock_id="authored-cycle-clock",
        period_s=owner.schedule["cycle_time_s"], native_geometry_evidence_id="native-case-cell-geometry",
        component_tolerance_mol=1e-8, energy_tolerance_j=1e-4)
    assert receipt.run.clock_id == receipt.clock_id
    assert len(receipt.checkpoints) > 1
    assert receipt.checkpoints[0].native_point is receipt.run.points[0]
    assert receipt.require_current() is receipt
    run_fields = {item.name: getattr(receipt.run, item.name)
                  for item in fields(receipt.run) if item.init and not item.name.startswith("_")}
    try:
        type(receipt.run)(**run_fields)
    except ValueError:
        pass
    else:
        raise AssertionError("Direct PSA run construction forged a native result")
    try:
        replace(receipt.run)
    except ValueError:
        pass
    else:
        raise AssertionError("Cloned PSA run retained native issuance")
    from h2physics.core import PropertyBasis, ThermoState
    declared = ThermoState(PropertyBasis("authored-product-mixture", "declared-reporting-reference"),
                           1e5, 300., 1., 0., -1e5, 0., "gas")
    try:
        adsorption_product_window(
            receipt, first_checkpoint_index=0, last_checkpoint_index=len(receipt.run.points)-1,
            molar_masses_kg_mol=(0.00201588, 0.0280134), composition_id="closed-reporting-mixture",
            product_state=declared, component_id="native-cycle", port_id="product",
            state_projection_evidence_id="authored-reporting-only-no-EOS-inference")
    except ValueError:
        pass
    else:
        raise AssertionError("Closed no-product run was projected onto a positive product stream")
    original = receipt.run.points[-1].beds[0].loading_mol_kg
    original.setflags(write=True)
    original[0, 0] += 1.
    try:
        receipt.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed native adsorption checkpoint was admitted")
    return ValidationOutcome(True, {"scheduled_checkpoints": len(receipt.checkpoints)},
                             ("Native scheduled endpoints only; accepted internal nodes unavailable",))
