"""Bind two already-run hydrogen models with an evidence-bearing batch receipt.

This example neither runs electrolysis nor executes the fuel-cell model. The
application supplies their original, current native traces and its own transfer,
conditioning, and tolerance evidence.
"""


def reconcile_completed_hydrogen_batch(
    producer_trace,
    fuel_cell_trace,
    *,
    transfer_loss_mol: float,
    source_port_id: str,
    hydrogen_inlet_id: str,
    transfer_evidence_id: str,
    conditioning_evidence_id: str,
    closure_tolerance_mol: float,
):
    """Return a live receipt after checking one finite H2 batch across two runs.

    ``producer_trace`` must be the original ``PVElectrolysisTrace`` and
    ``fuel_cell_trace`` the original ``FuelCellTrace``. Both traces must use the
    same clock and H2 species basis. The producer receiver begins empty, and the
    receiving run begins with the declared delivered batch. Physical transport
    and state conditioning are represented by caller-owned evidence identities.
    """
    from h2physics.adapters import bind_electrolysis_to_fuel_cell

    receipt = bind_electrolysis_to_fuel_cell(
        producer_trace,
        fuel_cell_trace,
        transfer_loss_mol=transfer_loss_mol,
        source_id=source_port_id,
        sink_id=hydrogen_inlet_id,
        transfer_evidence_id=transfer_evidence_id,
        conditioning_evidence_id=conditioning_evidence_id,
        closure_tolerance_mol=closure_tolerance_mol,
    )
    receipt.require_current()
    return receipt


def hydrogen_batch_ledger(receipt) -> tuple[tuple[str, float], ...]:
    """Return a small Python-native ledger after checking retained run freshness."""
    receipt.require_current()
    return (
        ("produced_mol", receipt.produced_mol),
        ("declared_transfer_loss_mol", receipt.transfer_loss_mol),
        ("delivered_mol", receipt.delivered_mol),
        ("consumed_mol", receipt.consumed_mol),
        ("remaining_mol", receipt.consumer_remaining_mol),
        ("consumer_initial_inventory_residual_mol", receipt.consumer_inventory_residual_mol),
    )


__all__ = ["reconcile_completed_hydrogen_batch", "hydrogen_batch_ledger"]
