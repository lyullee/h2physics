"""Deferred finite native-bed accounting contract; no calculation on discovery."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="adsorption-bed-finite-inventory-audit", profile="finite-adsorption-vessel",
        entrypoint=__name__ + ":validate_inventory",
        invariants=("cell absolute uptake weights actual adsorbent mass",
                    "gas moles are not rescaled by free volume",
                    "native energy reference and original snapshot survive accounting",
                    "native inventory discrepancy remains visible",
                    "surface-excess and invalid geometry are rejected"),
    ),)


def validate_inventory(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.adapters.adsorption_operation import audit_bed_inventory
    from h2physics.adapters.psa import BedSnapshot
    from h2physics.adsorption import AdsorptionBasis

    basis = AdsorptionBasis("authored-material", ("H2",), "mol/kg-absolute",
                            "authored-native-bed", "reference-v1", ("authored-contract",), "absolute")
    snapshot = BedSnapshot(basis, "native-energy-reference", np.array([[1.], [2.]]),
                           np.array([[3.], [4.]]), np.array([300., 300.]),
                           np.array([300., 300.]), np.array([1e5, 1e5]),
                           np.ones((2, 1)), np.array([14.]), -42.)
    kwargs = dict(adsorbent_mass_kg_by_cell=(1., 2.), free_volume_m3_by_cell=(0.01, 0.02),
                  geometry_evidence_id="cell-geometry", molar_tolerance=1e-12)
    receipt = audit_bed_inventory(snapshot, **kwargs)
    assert receipt.snapshot is snapshot
    assert receipt.gas_component_mol[0] == 3.
    assert receipt.adsorbed_component_mol[0] == 11.
    assert receipt.inventory_within_tolerance
    assert receipt.native_stored_energy_j == -42.
    assert receipt.native_energy_reference_id == snapshot.energy_reference_id
    assert receipt.require_current() is receipt
    try:
        replace(receipt, total_component_mol=np.array([999.]))
    except ValueError as error:
        assert "does not reconstruct" in str(error)
    else:
        raise AssertionError("A directly constructed inventory receipt accepted forged totals")
    try:
        replace(receipt, native_energy_reference_id="another-reference")
    except ValueError as error:
        assert "energy identities" in str(error)
    else:
        raise AssertionError("A direct receipt changed the native energy reference")
    mismatch = audit_bed_inventory(replace(snapshot, total_inventory_mol=np.array([15.])), **kwargs)
    assert not mismatch.inventory_within_tolerance
    assert mismatch.native_inventory_residual_mol[0] == 1.
    for bad in (replace(snapshot, basis=replace(basis, loading_definition="surface_excess")),):
        try:
            audit_bed_inventory(bad, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Surface-excess loading was treated as absolute inventory")
    try:
        audit_bed_inventory(snapshot, **(kwargs | {"free_volume_m3_by_cell": (0., 0.02)}))
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid free-volume geometry was admitted")
    snapshot.loading_mol_kg.setflags(write=True)
    snapshot.loading_mol_kg[0, 0] += 1.
    try:
        receipt.inventory_within_tolerance
    except ValueError:
        pass
    else:
        raise AssertionError("Changed nested native loading was accepted by the receipt")
    return ValidationOutcome(True, {"inventory_mol": float(receipt.total_component_mol[0])},
                             ("Inventory accounting only; no native thermal/dynamic qualification",))
