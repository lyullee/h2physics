"""Molar inventory handoff from finite PV electrolysis to finite fuel-cell use."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose

from ..core import finite


class HydrogenHandoffError(ValueError):
    """Raised when production and consumption inventories do not form one batch."""


@dataclass(frozen=True, slots=True)
class HydrogenInventoryHandoff:
    """Reconcile one isolated H2 batch between two already-run native models.

    This receipt closes hydrogen *moles* only. The caller must provide evidence
    for transport/storage and any state conditioning between the producer's gas
    receiver and the fuel-cell inventory. It does not claim full plant energy
    closure or couple the two solvers.
    """

    producer: object
    consumer: object
    transfer_loss_mol: float
    source_id: str
    sink_id: str
    transfer_evidence_id: str
    conditioning_evidence_id: str
    closure_tolerance_mol: float
    produced_mol: float = field(init=False)
    delivered_mol: float = field(init=False)
    consumed_mol: float = field(init=False)
    consumer_inventory_residual_mol: float = field(init=False)
    consumer_remaining_mol: float = field(init=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        from .fuel_cell import FuelCellTrace
        from .pv_electrolysis import PVElectrolysisTrace

        if type(self.producer) is not PVElectrolysisTrace:
            raise TypeError("producer must be an admitted PVElectrolysisTrace")
        if type(self.consumer) is not FuelCellTrace:
            raise TypeError("consumer must be an admitted FuelCellTrace")
        self.producer.require_current()
        self.consumer.require_current()
        for name in ("source_id", "sink_id", "transfer_evidence_id", "conditioning_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be an explicit nonempty identity")
        tolerance = finite(self.closure_tolerance_mol, "closure_tolerance_mol", positive=True)
        loss = finite(self.transfer_loss_mol, "transfer_loss_mol")
        if loss < 0:
            raise ValueError("Declared transfer loss cannot be negative")

        producer, consumer = self.producer, self.consumer
        clock_id = producer.evidence.clock_id
        if consumer.evidence.clock_id != clock_id:
            raise HydrogenHandoffError("Producer and consumer use different physical clocks")
        if (self.source_id != producer.evidence.source_id
                or self.sink_id != consumer.boundary.hydrogen_inlet_id):
            raise HydrogenHandoffError("Handoff IDs must match the original producer and consumer ports")
        if not producer.steps or not consumer.steps:
            raise HydrogenHandoffError("Both native traces must contain at least one accepted operation")
        producer_end = finite(producer.final.time_s, "producer end time")
        consumer_start = finite(consumer.steps[0].command.start_s, "consumer start time")
        if consumer.steps[0].command.clock_id != clock_id or consumer_start < producer_end:
            raise HydrogenHandoffError("Consumer operation must start after production on the shared clock")

        hydrogen_id = producer.owner.hydrogen_id
        consumer_hydrogen_id = consumer.owner.hydrogen_id
        if hydrogen_id != consumer_hydrogen_id:
            raise HydrogenHandoffError("Producer and consumer hydrogen species identities differ")
        producer_species = next(s for s in producer.owner.reaction.species
                                if s.identifier == hydrogen_id)
        consumer_species = next(s for s in consumer.owner.reaction.species
                                if s.identifier == consumer_hydrogen_id)
        if (dict(producer_species.elements) != dict(consumer_species.elements)
                or producer_species.charge != consumer_species.charge
                or not isclose(producer_species.molar_mass_kg_mol,
                               consumer_species.molar_mass_kg_mol, rel_tol=1e-9, abs_tol=0.)):
            raise HydrogenHandoffError(
                "Producer and consumer H2 aliases disagree in elemental, charge or molar-mass basis"
            )
        initial_product = finite(producer.initial.amounts_mol.get(hydrogen_id, 0.),
                                 "initial producer hydrogen inventory")
        final_product = finite(producer.final.amounts_mol.get(hydrogen_id, 0.),
                               "final producer hydrogen inventory")
        produced = final_product-initial_product
        if produced <= 0.:
            raise HydrogenHandoffError("Producer trace contains no net positive hydrogen batch")
        delivered = produced-loss
        if delivered < -tolerance:
            raise HydrogenHandoffError("Declared transfer loss exceeds the produced hydrogen")
        delivered = max(0., delivered)

        consumer_initial = finite(consumer.initial.amounts_mol.get(consumer_hydrogen_id, 0.),
                                  "initial consumer hydrogen inventory")
        residual = consumer_initial-delivered
        if abs(residual) > tolerance:
            raise HydrogenHandoffError(
                "Consumer initial hydrogen inventory does not match the delivered producer batch"
            )
        consumed = finite(consumer.hydrogen_consumed_mol, "consumer hydrogen consumption")
        remaining = consumer_initial-consumed
        if remaining < -tolerance:
            raise HydrogenHandoffError("Consumer withdrawal exceeds the handed-off batch")
        object.__setattr__(self, "transfer_loss_mol", loss)
        object.__setattr__(self, "closure_tolerance_mol", tolerance)
        object.__setattr__(self, "produced_mol", produced)
        object.__setattr__(self, "delivered_mol", delivered)
        object.__setattr__(self, "consumed_mol", consumed)
        object.__setattr__(self, "consumer_inventory_residual_mol", residual)
        object.__setattr__(self, "consumer_remaining_mol", max(0., remaining))
        object.__setattr__(self, "_binding", self._content())

    def _content(self):
        return (
            id(self.producer), id(self.consumer), self.transfer_loss_mol,
            self.source_id, self.sink_id, self.transfer_evidence_id,
            self.conditioning_evidence_id, self.closure_tolerance_mol,
            self.produced_mol, self.delivered_mol, self.consumed_mol,
            self.consumer_inventory_residual_mol, self.consumer_remaining_mol,
        )

    def require_current(self) -> HydrogenInventoryHandoff:
        if not self._binding or self._content() != self._binding:
            raise HydrogenHandoffError("Handoff identity or ledger changed after construction")
        self.producer.require_current()
        self.consumer.require_current()
        recreated = HydrogenInventoryHandoff(
            self.producer, self.consumer, self.transfer_loss_mol, self.source_id,
            self.sink_id, self.transfer_evidence_id, self.conditioning_evidence_id,
            self.closure_tolerance_mol,
        )
        for name in ("produced_mol", "delivered_mol", "consumed_mol",
                     "consumer_inventory_residual_mol", "consumer_remaining_mol"):
            if getattr(recreated, name) != getattr(self, name):
                raise HydrogenHandoffError("Handoff ledger changed after construction")
        return self


def bind_electrolysis_to_fuel_cell(
    producer,
    consumer,
    *,
    transfer_loss_mol: float,
    source_id: str,
    sink_id: str,
    transfer_evidence_id: str,
    conditioning_evidence_id: str,
    closure_tolerance_mol: float,
) -> HydrogenInventoryHandoff:
    """Create a molar H2 inventory bridge without replacing either native run."""
    return HydrogenInventoryHandoff(
        producer, consumer, transfer_loss_mol, source_id, sink_id,
        transfer_evidence_id, conditioning_evidence_id, closure_tolerance_mol,
    )
