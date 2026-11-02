"""Bind collected reliquefier liquid product to a native separator inlet."""

from dataclasses import dataclass, field
from math import isclose

from ..core import finite
from .lh2dt import Lh2dtProperties
from .reliquefier_product import ReliquefierProductReceipt, liquid_mass_fraction

_PENDING: set[object] = set()


@dataclass(frozen=True, slots=True)
class ReliquefierSeparatorInlet:
    """Evidence-bound, constant-rate liquid stream for one exact collection window."""

    receipt: ReliquefierProductReceipt = field(repr=False, compare=False)
    bridge: Lh2dtProperties = field(repr=False, compare=False)
    clock_id: str
    receiver_id: str
    clock_alignment_evidence_id: str
    receiver_assignment_evidence_id: str
    transfer_boundary_evidence_id: str
    mass_flow_kg_s: float
    specific_enthalpy_j_kg: float
    start_time_s: float
    end_time_s: float
    _token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Issue separator inlets through bind_reliquefier_product_to_separator")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_token", None)
        if type(self.receipt) is not ReliquefierProductReceipt or type(self.bridge) is not Lh2dtProperties:
            raise TypeError("Use the exact reliquefier product receipt and LH2DT property bridge")
        self.receipt.require_current()
        self.bridge.basis.require_compatible(self.receipt.product_state.basis)
        if not all(isinstance(v, str) and v.strip() for v in (
                self.clock_id, self.receiver_id, self.clock_alignment_evidence_id,
                self.receiver_assignment_evidence_id, self.transfer_boundary_evidence_id)):
            raise ValueError("Declare clock, receiver, alignment, receiver assignment and transfer-boundary identities")
        if self.clock_id != self.receipt.window.clock_id:
            raise ValueError("Storage inlet clock must match the reliquefier product window")
        if not isclose(liquid_mass_fraction(self.receipt.product_state) or 0.0,
                        1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("Only the collected all-liquid product can enter this liquid phase port")
        expected = self.receipt.allocation.collected_product_mass_kg / self.receipt.window.duration_s
        if (self.mass_flow_kg_s != expected or self.mass_flow_kg_s <= 0.
                or self.specific_enthalpy_j_kg != self.receipt.product_state.enthalpy_j_kg
                or self.start_time_s != self.receipt.window.start_time_s
                or self.end_time_s != self.receipt.window.end_time_s):
            raise ValueError("Inlet rate, enthalpy or support differs from the collected product receipt")
        object.__setattr__(self, "_seal", (
            id(self.receipt), id(self.bridge), self.clock_id, self.receiver_id,
            self.clock_alignment_evidence_id, self.receiver_assignment_evidence_id,
            self.transfer_boundary_evidence_id,
            self.mass_flow_kg_s, self.specific_enthalpy_j_kg,
            self.start_time_s, self.end_time_s,
        ))

    def require_current(self):
        self.receipt.require_current()
        self.bridge.basis.require_compatible(self.receipt.product_state.basis)
        if (self._seal != (
                id(self.receipt), id(self.bridge), self.clock_id, self.receiver_id,
                self.clock_alignment_evidence_id, self.receiver_assignment_evidence_id,
                self.transfer_boundary_evidence_id,
                self.mass_flow_kg_s, self.specific_enthalpy_j_kg,
                self.start_time_s, self.end_time_s)
                or not isclose(liquid_mass_fraction(self.receipt.product_state) or 0.0,
                               1.0, rel_tol=0.0, abs_tol=1e-12)
                or self.clock_id != self.receipt.window.clock_id
                or self.mass_flow_kg_s != self.receipt.allocation.collected_product_mass_kg / self.receipt.window.duration_s
                or self.specific_enthalpy_j_kg != self.receipt.product_state.enthalpy_j_kg
                or self.start_time_s != self.receipt.window.start_time_s
                or self.end_time_s != self.receipt.window.end_time_s):
            raise ValueError("Reliquefier-to-separator inlet no longer matches its source receipt")
        return self

    def phase_flows(self, absolute_time_s, _native_thermo):
        """Return the accepted product as one native liquid MassEnergyFlow."""
        self.require_current()
        time = finite(absolute_time_s, "separator inlet absolute time")
        if not self.start_time_s <= time <= self.end_time_s:
            raise ValueError("Separator queried outside the exact reliquefier collection window")
        from lh2dt.streams import MassEnergyFlow
        return ((MassEnergyFlow(self.mass_flow_kg_s, self.specific_enthalpy_j_kg),), ())


def bind_reliquefier_product_to_separator(
    receipt: ReliquefierProductReceipt,
    bridge: Lh2dtProperties,
    *,
    receiver_id: str,
    clock_alignment_evidence_id: str,
    receiver_assignment_evidence_id: str,
    transfer_boundary_evidence_id: str,
) -> ReliquefierSeparatorInlet:
    """Project collected liquid mass/state into an existing tank liquid inlet.

    The caller is responsible for aligning the receipt's collection window to
    the target operation clock, identifying the receiving phase port, and
    supplying evidence that the external transfer boundary accounts for
    pressure and thermal feasibility. No line loss, flashing, throttling, tank
    pressure response or heat exchange is inferred here.
    """
    if type(receipt) is not ReliquefierProductReceipt:
        raise TypeError("Supply the original owner-issued reliquefier product receipt")
    if type(bridge) is not Lh2dtProperties:
        raise TypeError("Supply the target tank's exact LH2DT property bridge")
    receipt.require_current()
    bridge.basis.require_compatible(receipt.product_state.basis)
    mass = finite(receipt.allocation.collected_product_mass_kg, "collected liquid product mass", positive=True)
    window = receipt.window
    token = object()
    _PENDING.add(token)
    try:
        result = ReliquefierSeparatorInlet(
            receipt, bridge, window.clock_id, receiver_id,
            clock_alignment_evidence_id, receiver_assignment_evidence_id,
            transfer_boundary_evidence_id,
            mass / window.duration_s, receipt.product_state.enthalpy_j_kg,
            window.start_time_s, window.end_time_s, _token=token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    return result.require_current()


__all__ = ["ReliquefierSeparatorInlet", "bind_reliquefier_product_to_separator"]
