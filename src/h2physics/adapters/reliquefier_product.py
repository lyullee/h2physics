"""Finite collected-product and cold-budget boundaries for native reliquefiers.

The native steady/dynamic reliquefier remains the owner of phase state, cooling
and stored fluid/wall energy.  This module only partitions an accepted outlet or
post-step inventory and debits an explicit finite cold-energy budget.
"""

from dataclasses import dataclass, field as dataclass_field
from math import isclose

from ..core import Origin, PropertyBasis, ThermoState, finite
from ..dynamics import ConservedInventory
from ..equipment import EquipmentTolerances
from .lh2dt_reliquefier import ReliquefierStep, SteadyReliquefierResult, liquid_mass_fraction
from .result_provenance import recorded_content_sha256


_PENDING_PRODUCT_RECEIPT_ISSUERS: set[object] = set()


def _product_receipt_content(receipt):
    return tuple((name, getattr(receipt, name)) for name in receipt.__dataclass_fields__
                 if name not in {"_issuer_token", "_receipt_seal"})


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty identity")
    return value


@dataclass(frozen=True, slots=True)
class ReliquefierProductPorts:
    feed_port_id: str
    product_port_id: str
    return_port_id: str
    vent_port_id: str

    def __post_init__(self):
        values = tuple(_identity(getattr(self, name), name) for name in (
            "feed_port_id", "product_port_id", "return_port_id", "vent_port_id"))
        if len(set(values)) != len(values):
            raise ValueError("Feed, product, return and vent ports must be distinct")


@dataclass(frozen=True, slots=True)
class ProductWindow:
    clock_id: str
    start_time_s: float
    end_time_s: float

    def __post_init__(self):
        _identity(self.clock_id, "clock_id")
        finite(self.start_time_s, "start_time_s")
        finite(self.end_time_s, "end_time_s")
        if self.end_time_s <= self.start_time_s:
            raise ValueError("A product window needs positive duration")

    @property
    def duration_s(self) -> float:
        return self.end_time_s - self.start_time_s


@dataclass(frozen=True, slots=True)
class ProductAllocation:
    feed_mass_kg: float
    collected_product_mass_kg: float
    returned_mass_kg: float
    vented_mass_kg: float
    device_accumulation_kg: float = 0.0

    def __post_init__(self):
        for name in ("feed_mass_kg", "collected_product_mass_kg", "returned_mass_kg",
                     "vented_mass_kg"):
            finite(getattr(self, name), name)
            if getattr(self, name) < 0.0:
                raise ValueError("Feed and outlet allocation masses cannot be negative")
        finite(self.device_accumulation_kg, "device_accumulation_kg")

    @property
    def mass_residual_kg(self) -> float:
        return (self.feed_mass_kg - self.collected_product_mass_kg - self.returned_mass_kg
                - self.vented_mass_kg - self.device_accumulation_kg)


@dataclass(frozen=True, slots=True)
class CollectedProductInventory:
    basis: PropertyBasis
    mass_kg: float
    transported_enthalpy_j: float

    def __post_init__(self):
        if not isinstance(self.basis, PropertyBasis):
            raise TypeError("Product inventory requires a PropertyBasis")
        finite(self.mass_kg, "mass_kg")
        finite(self.transported_enthalpy_j, "transported_enthalpy_j")
        if self.mass_kg < 0.0:
            raise ValueError("Collected product mass cannot be negative")
        if self.mass_kg == 0.0 and self.transported_enthalpy_j != 0.0:
            raise ValueError("An empty collection cannot retain transported enthalpy")

    def receive(self, mass_kg: float, state: ThermoState) -> "CollectedProductInventory":
        mass = finite(mass_kg, "received product mass")
        if mass < 0.0:
            raise ValueError("Received product mass cannot be negative")
        self.basis.require_compatible(state.basis)
        return CollectedProductInventory(
            self.basis,
            self.mass_kg + mass,
            self.transported_enthalpy_j + mass * state.enthalpy_j_kg,
        )


@dataclass(frozen=True, slots=True)
class FiniteColdReservoir:
    reservoir_id: str
    initial_available_cooling_j: float
    remaining_available_cooling_j: float
    energy_reference_id: str

    def __post_init__(self):
        _identity(self.reservoir_id, "reservoir_id")
        _identity(self.energy_reference_id, "energy_reference_id")
        finite(self.initial_available_cooling_j, "initial_available_cooling_j")
        finite(self.remaining_available_cooling_j, "remaining_available_cooling_j")
        if not 0.0 <= self.remaining_available_cooling_j <= self.initial_available_cooling_j:
            raise ValueError("Remaining cooling must lie inside the finite initial budget")

    def debit(self, removed_heat_j: float) -> "FiniteColdReservoir":
        draw = finite(removed_heat_j, "removed_heat_j")
        if draw < 0.0:
            raise ValueError("A cold-reservoir debit cannot be negative")
        remaining = self.remaining_available_cooling_j - draw
        if remaining < -1e-12 * max(self.initial_available_cooling_j, 1.0):
            raise ValueError("Requested cooling exceeds the finite cold reservoir")
        return FiniteColdReservoir(self.reservoir_id, self.initial_available_cooling_j,
                                   max(0.0, remaining), self.energy_reference_id)


@dataclass(frozen=True, slots=True)
class IntegratedColdDuty:
    removed_heat_j: float
    source_id: str
    origin: Origin

    def __post_init__(self):
        finite(self.removed_heat_j, "removed_heat_j")
        if self.removed_heat_j < 0.0:
            raise ValueError("Integrated removed heat cannot be negative")
        _identity(self.source_id, "source_id")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Integrated cold duty needs resolved provenance")


@dataclass(frozen=True, slots=True)
class DynamicInventoryWitness:
    initial: ConservedInventory
    final: ConservedInventory

    def __post_init__(self):
        if not isinstance(self.initial, ConservedInventory) or not isinstance(self.final, ConservedInventory):
            raise TypeError("Dynamic inventory witness requires original ConservedInventory values")
        self.initial.basis.require_compatible(self.final.basis)

    @property
    def accumulation_kg(self) -> float:
        return self.final.mass_kg - self.initial.mass_kg


@dataclass(frozen=True, slots=True)
class ReliquefierProductReceipt:
    mode: str
    ports: ReliquefierProductPorts
    window: ProductWindow
    allocation: ProductAllocation
    product_state: ThermoState
    cold_duty: IntegratedColdDuty
    product_before: CollectedProductInventory
    product_after: CollectedProductInventory
    cold_before: FiniteColdReservoir
    cold_after: FiniteColdReservoir
    original_result: SteadyReliquefierResult | ReliquefierStep
    dynamic_inventory: DynamicInventoryWitness | None
    _owner: object
    _result_seal: str
    _product_seal: str
    _cold_seal: str
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _receipt_seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PRODUCT_RECEIPT_ISSUERS:
            raise ValueError("Product receipts must be issued by the collection owner")
        _PENDING_PRODUCT_RECEIPT_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_receipt_seal",
                           recorded_content_sha256(_product_receipt_content(self)))

    def require_current(self) -> "ReliquefierProductReceipt":
        self.original_result.require_current()
        if recorded_content_sha256(_product_receipt_content(self)) != self._receipt_seal:
            raise ValueError("Reliquefier product receipt changed after collection")
        if self.original_result is not self._owner:
            raise ValueError("Reliquefier product receipt lost its original result owner")
        if recorded_content_sha256(self.original_result) != self._result_seal:
            raise ValueError("Original reliquefier result changed after product admission")
        if recorded_content_sha256(self.product_before) != self._product_seal:
            raise ValueError("Initial collected-product inventory changed after admission")
        if recorded_content_sha256(self.cold_before) != self._cold_seal:
            raise ValueError("Initial cold reservoir changed after admission")
        return self


class FiniteReliquefierProduct:
    """Partition accepted native results and update finite product/cold ledgers."""

    def __init__(self, ports: ReliquefierProductPorts, *, tolerances: EquipmentTolerances | None = None):
        if not isinstance(ports, ReliquefierProductPorts):
            raise TypeError("Finite product collection requires ReliquefierProductPorts")
        self.ports = ports
        self.tolerances = tolerances or EquipmentTolerances()

    def _admit(self, *, mode, result, window, allocation, state, duty,
               product, cold, dynamic_inventory=None):
        if not isinstance(window, ProductWindow) or not isinstance(allocation, ProductAllocation):
            raise TypeError("Collection requires a ProductWindow and ProductAllocation")
        if not isinstance(product, CollectedProductInventory) or not isinstance(cold, FiniteColdReservoir):
            raise TypeError("Collection requires finite product and cold inventories")
        if not isinstance(duty, IntegratedColdDuty):
            raise TypeError("Collection requires an IntegratedColdDuty")
        product.basis.require_compatible(state.basis)
        if abs(allocation.mass_residual_kg) > max(
                self.tolerances.mass_absolute_kg_s * window.duration_s,
                self.tolerances.relative * max(allocation.feed_mass_kg, 1.0)):
            raise ValueError("Feed, product, return, vent and device accumulation do not close")
        if allocation.collected_product_mass_kg > 0.0:
            fraction = liquid_mass_fraction(state)
            if fraction is None or not isclose(fraction, 1.0, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError("Collected product requires an original all-liquid native state")
        after_product = product.receive(allocation.collected_product_mass_kg, state)
        after_cold = cold.debit(duty.removed_heat_j)
        token = object()
        _PENDING_PRODUCT_RECEIPT_ISSUERS.add(token)
        try:
            receipt = ReliquefierProductReceipt(
                mode, self.ports, window, allocation, state, duty, product, after_product,
                cold, after_cold, result, dynamic_inventory, result,
                recorded_content_sha256(result), recorded_content_sha256(product),
                recorded_content_sha256(cold), token,
            )
        except Exception:
            _PENDING_PRODUCT_RECEIPT_ISSUERS.discard(token)
            raise
        receipt.require_current()
        return receipt

    def collect_steady(self, result: SteadyReliquefierResult, window: ProductWindow, *,
                       collected_product_kg: float, returned_kg: float, vented_kg: float,
                       product: CollectedProductInventory, cold: FiniteColdReservoir):
        if type(result) is not SteadyReliquefierResult:
            raise TypeError("collect_steady requires an original SteadyReliquefierResult")
        result.require_current()
        if result.outlet is not result.transfer.transmitted or result.inlet is not result.transfer.upstream:
            raise ValueError("Steady product collection requires original transfer state ownership")
        feed = result.transfer.mass_flow_kg_s * window.duration_s
        if feed < 0.0:
            raise ValueError("Steady product collection does not infer reverse reliquefier operation")
        allocation = ProductAllocation(feed, collected_product_kg, returned_kg, vented_kg, 0.0)
        removed = max(0.0, -result.power.heat_w) * window.duration_s
        duty = IntegratedColdDuty(removed, f"{result.transfer.component_id}:native-steady-duty",
                                  Origin.PREDICTED)
        return self._admit(mode="steady", result=result, window=window,
            allocation=allocation, state=result.outlet, duty=duty, product=product, cold=cold)

    def collect_dynamic(self, result: ReliquefierStep, window: ProductWindow, *,
                        feed_kg: float, collected_product_kg: float, returned_kg: float,
                        vented_kg: float, inventory: DynamicInventoryWitness,
                        cold_duty: IntegratedColdDuty, product: CollectedProductInventory,
                        cold: FiniteColdReservoir):
        if type(result) is not ReliquefierStep:
            raise TypeError("collect_dynamic requires an original ReliquefierStep")
        result.require_current()
        if not isinstance(inventory, DynamicInventoryWitness) or inventory.final is not result.inventory:
            raise ValueError("Dynamic product collection requires the original final inventory object")
        result.fluid.basis.require_compatible(inventory.final.basis)
        allocation = ProductAllocation(feed_kg, collected_product_kg, returned_kg,
                                       vented_kg, inventory.accumulation_kg)
        return self._admit(mode="dynamic-post-step", result=result, window=window,
            allocation=allocation, state=result.fluid, duty=cold_duty, product=product,
            cold=cold, dynamic_inventory=inventory)
