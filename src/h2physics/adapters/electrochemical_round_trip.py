"""Meter-bound electrical accounting across an accepted H2 storage cycle.

This composes existing finite electrolysis, fuel-cell and hydrogen-inventory
receipts. It does not replace either solver or infer storage/compression losses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import fsum

from ..core import finite
from .electrochemical_hydrogen_handoff import HydrogenInventoryHandoff


@dataclass(frozen=True, slots=True)
class ElectricalBoundaryMeter:
    """One integrated, nonnegative electrical-energy reading in joules."""

    meter_id: str
    system_boundary_id: str
    window_id: str
    clock_id: str
    energy_basis_id: str
    evidence_id: str
    start_s: float
    end_s: float
    energy_j: float
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        for name in ("meter_id", "system_boundary_id", "window_id", "clock_id",
                     "energy_basis_id", "evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name} for the electrical meter reading")
        start = finite(self.start_s, "meter window start")
        end = finite(self.end_s, "meter window end")
        if end <= start:
            raise ValueError("Meter windows must have positive duration")
        finite(self.energy_j, "integrated electrical energy", positive=True)
        object.__setattr__(self, "_binding", self._content())

    def _content(self):
        return (
            self.meter_id, self.system_boundary_id, self.window_id, self.clock_id,
            self.energy_basis_id, self.evidence_id, self.start_s, self.end_s,
            self.energy_j,
        )

    def require_current(self) -> ElectricalBoundaryMeter:
        if not self._binding or self._content() != self._binding:
            raise ValueError("Electrical meter reading changed after construction")
        return self


@dataclass(frozen=True, slots=True)
class ElectrochemicalStorageRoundTrip:
    """Auditable electricity in/out ratio for one sequential H2 batch.

    The caller places both meter readings on the same declared electrical
    basis and system boundary. The charge meter covers the entire accepted
    electrolysis trace; the discharge meter covers the entire accepted fuel-cell
    trace. Both are compared with their native trace's electrical ledger, while
    the linked H2 receipt checks production, loss, consumption and inventory.
    """

    inventory_handoff: HydrogenInventoryHandoff
    charge_meter: ElectricalBoundaryMeter
    discharge_meter: ElectricalBoundaryMeter
    stack_electricity_in_j: float = field(init=False)
    stack_electricity_out_j: float = field(init=False)
    meter_electricity_in_j: float = field(init=False)
    meter_electricity_out_j: float = field(init=False)
    round_trip_electricity_ratio: float = field(init=False)
    hydrogen_produced_mol: float = field(init=False)
    hydrogen_delivered_mol: float = field(init=False)
    hydrogen_consumed_mol: float = field(init=False)
    hydrogen_remaining_mol: float = field(init=False)
    hydrogen_transfer_loss_mol: float = field(init=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        handoff = self.inventory_handoff
        if type(handoff) is not HydrogenInventoryHandoff:
            raise TypeError("Supply the existing electrolysis-to-fuel-cell H2 receipt")
        handoff.require_current()
        charge, discharge = self.charge_meter, self.discharge_meter
        if type(charge) is not ElectricalBoundaryMeter or type(discharge) is not ElectricalBoundaryMeter:
            raise TypeError("Supply typed charge and discharge electrical meter readings")
        charge.require_current()
        discharge.require_current()

        producer, consumer = handoff.producer, handoff.consumer
        clock = producer.evidence.clock_id
        if charge.clock_id != clock or discharge.clock_id != clock:
            raise ValueError("Meter and native traces must use the H2 receipt's declared physical clock")
        if charge.system_boundary_id != discharge.system_boundary_id:
            raise ValueError("Charge and discharge readings must share one declared system boundary")
        if charge.energy_basis_id != discharge.energy_basis_id:
            raise ValueError("Charge and discharge readings must use the same electrical-energy basis")
        if charge.end_s > discharge.start_s:
            raise ValueError("The accepted discharge window must follow the charging meter window")
        if (charge.start_s > producer.initial.time_s
                or charge.end_s < producer.final.time_s):
            raise ValueError("Charge meter window must cover the complete electrolysis trace")
        if (not consumer.steps
                or discharge.start_s > consumer.steps[0].command.start_s
                or discharge.end_s < consumer.steps[-1].command.end_s):
            raise ValueError("Discharge meter window must cover the complete fuel-cell trace")

        stack_in = fsum(finite(step.electricity_j, "electrolysis step electricity J")
                         for step in producer.steps)
        stack_out = -finite(consumer.electricity_into_j, "fuel-cell signed electricity J")
        meter_in = finite(charge.energy_j, "metered charge electricity J", positive=True)
        meter_out = finite(discharge.energy_j, "metered discharge electricity J", positive=True)
        if stack_in <= 0. or stack_out <= 0.:
            raise ValueError("Both accepted native traces must transfer positive electrical energy")
        tolerance = max(1e-6, stack_in * 1e-9, stack_out * 1e-9)
        if meter_in + tolerance < stack_in:
            raise ValueError("Charge-boundary meter omits energy consumed by the accepted electrolyzer trace")
        if meter_out > stack_out + tolerance:
            raise ValueError("Discharge-boundary meter exceeds the accepted fuel-cell electrical output")

        object.__setattr__(self, "stack_electricity_in_j", stack_in)
        object.__setattr__(self, "stack_electricity_out_j", stack_out)
        object.__setattr__(self, "meter_electricity_in_j", meter_in)
        object.__setattr__(self, "meter_electricity_out_j", meter_out)
        object.__setattr__(self, "round_trip_electricity_ratio", meter_out / meter_in)
        object.__setattr__(self, "hydrogen_produced_mol", handoff.produced_mol)
        object.__setattr__(self, "hydrogen_delivered_mol", handoff.delivered_mol)
        object.__setattr__(self, "hydrogen_consumed_mol", handoff.consumed_mol)
        object.__setattr__(self, "hydrogen_remaining_mol", handoff.consumer_remaining_mol)
        object.__setattr__(self, "hydrogen_transfer_loss_mol", handoff.transfer_loss_mol)
        object.__setattr__(self, "_binding", self._content())

    def _content(self):
        return (
            id(self.inventory_handoff), id(self.charge_meter), id(self.discharge_meter),
            self.stack_electricity_in_j, self.stack_electricity_out_j,
            self.meter_electricity_in_j, self.meter_electricity_out_j,
            self.round_trip_electricity_ratio, self.hydrogen_produced_mol,
            self.hydrogen_delivered_mol, self.hydrogen_consumed_mol,
            self.hydrogen_remaining_mol, self.hydrogen_transfer_loss_mol,
        )

    def require_current(self) -> ElectrochemicalStorageRoundTrip:
        if not self._binding or self._content() != self._binding:
            raise ValueError("Round-trip accounting receipt changed after construction")
        self.inventory_handoff.require_current()
        self.charge_meter.require_current()
        self.discharge_meter.require_current()
        rebuilt = ElectrochemicalStorageRoundTrip(
            self.inventory_handoff, self.charge_meter, self.discharge_meter,
        )
        if rebuilt._content() != self._content():
            raise ValueError("Round-trip accounting no longer matches its source traces or meter readings")
        return self


def account_electrochemical_storage_round_trip(
    inventory_handoff: HydrogenInventoryHandoff,
    *,
    charge_meter: ElectricalBoundaryMeter,
    discharge_meter: ElectricalBoundaryMeter,
) -> ElectrochemicalStorageRoundTrip:
    """Bind same-basis boundary electricity readings to one admitted H2 cycle.

    The meters must include every electricity import/export inside the chosen
    boundary, including compression, auxiliaries and conversion losses when
    those lie inside it. Their evidence and completeness remain caller-owned.
    """
    return ElectrochemicalStorageRoundTrip(inventory_handoff, charge_meter, discharge_meter)
