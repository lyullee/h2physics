"""Caller-parameterized finite cylinder-wall thermal boundary.

The module supplies no heat-transfer correlation. Cantera continues to own the
reacting gas and moving-cylinder integration; this object supplies a lumped
wall capacity, one gas-wall UA, and an optional external/coolant heat callback.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import partial
from hashlib import sha256
import marshal

from ..core import finite


def _state_token(value, active=None):
    """Stable-enough in-process token for caller-owned callback configuration."""
    if active is None:
        active = set()
    if value is None or isinstance(value, (str, bool, int, bytes)):
        return (type(value).__qualname__, value)
    if isinstance(value, float):
        return ("float", value.hex())
    identity = id(value)
    if identity in active:
        return ("cycle", type(value).__module__, type(value).__qualname__, identity)
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            entries = [(_state_token(key, active), _state_token(item, active))
                       for key, item in value.items()]
            return ("mapping", type(value).__module__, type(value).__qualname__,
                    tuple(sorted(entries, key=repr)))
        if isinstance(value, (tuple, list)):
            return (type(value).__qualname__, tuple(_state_token(item, active) for item in value))
        if isinstance(value, (set, frozenset)):
            return (type(value).__qualname__, tuple(sorted(
                (_state_token(item, active) for item in value), key=repr)))
        code = getattr(value, "__code__", None)
        if code is not None:
            return ("function", getattr(value, "__module__", None),
                    getattr(value, "__qualname__", None),
                    sha256(marshal.dumps(code)).hexdigest(),
                    _state_token(getattr(value, "__defaults__", None), active),
                    _state_token(getattr(value, "__kwdefaults__", None), active),
                    _state_token(tuple(_cell_token(cell) for cell in (value.__closure__ or ())), active))
        if isinstance(value, partial):
            return ("partial", _state_token(value.func, active),
                    _state_token(value.args, active), _state_token(value.keywords, active))
        if hasattr(value, "__self__") and hasattr(value, "__func__"):
            return ("bound-method", _state_token(value.__func__, active),
                    _state_token(value.__self__, active))
        attributes = getattr(value, "__dict__", None)
        slots = getattr(type(value), "__slots__", ())
        if isinstance(slots, str):
            slots = (slots,)
        if attributes is not None or slots:
            slot_state = tuple((name, _state_token(getattr(value, name), active))
                               for name in slots if hasattr(value, name))
            return ("object", type(value).__module__, type(value).__qualname__, identity,
                    None if attributes is None else _state_token(attributes, active), slot_state,
                    _state_token(getattr(type(value), "__call__", None), active))
        if type(value).__module__.startswith("numpy") and hasattr(value, "tobytes"):
            return ("array", str(value.dtype), tuple(value.shape), sha256(value.tobytes()).hexdigest())
        return ("opaque", type(value).__module__, type(value).__qualname__, identity)
    finally:
        active.remove(identity)


def _cell_token(cell):
    try:
        return cell.cell_contents
    except ValueError:
        return ("empty-closure-cell",)


def _callback_binding(callback):
    return None if callback is None else _state_token(callback)


@dataclass(frozen=True, slots=True)
class CylinderWallThermal:
    """One finite wall node and evidence-bound boundary heat callback.

    ``external_heat_into_wall`` returns signed watts entering the wall from
    every non-cylinder boundary (for example, a coolant stream). The gas-wall
    transfer is ``UA * (Tgas - Twall)`` and is counted with opposite signs in
    the gas and wall energy equations.
    """

    heat_capacity_j_k: float
    reference_temperature_k: float
    initial_temperature_k: float
    conductance_ua_w_k: float
    energy_reference_id: str
    property_evidence_id: str
    boundary_evidence_id: str
    external_heat_into_wall: Callable[[float, float, float], float] | None = field(
        default=None, repr=False, compare=False
    )
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "heat_capacity_j_k", finite(
            self.heat_capacity_j_k, "cylinder wall heat capacity", positive=True))
        for name in ("reference_temperature_k", "initial_temperature_k"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        ua = finite(self.conductance_ua_w_k, "gas-wall conductance UA")
        if ua < 0.:
            raise ValueError("Gas-wall conductance UA cannot be negative")
        object.__setattr__(self, "conductance_ua_w_k", ua)
        for name in ("energy_reference_id", "property_evidence_id", "boundary_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare cylinder-wall {name}")
            object.__setattr__(self, name, value.strip())
        if self.external_heat_into_wall is not None and not callable(self.external_heat_into_wall):
            raise TypeError("External wall heat must be a caller-owned callable or None")
        object.__setattr__(self, "_seal", self._seal_payload())

    def external_heat_rate_w(self, time_s: float, gas_temperature_k: float,
                             wall_temperature_k: float) -> float:
        self.require_current()
        if self.external_heat_into_wall is None:
            return 0.
        return finite(self.external_heat_into_wall(
            finite(time_s, "absolute wall heat time"),
            finite(gas_temperature_k, "cylinder gas temperature", positive=True),
            finite(wall_temperature_k, "wall temperature", positive=True)),
            "external heat into cylinder wall")

    def require_current(self):
        """Recheck the source-bound scalar parameters before reuse."""
        if not self._seal or self._seal_payload() != self._seal:
            raise ValueError("Cylinder-wall parameters or heat callback changed")
        return self

    def _seal_payload(self):
        return (self.heat_capacity_j_k, self.reference_temperature_k,
                self.initial_temperature_k, self.conductance_ua_w_k,
                self.energy_reference_id, self.property_evidence_id,
                self.boundary_evidence_id, _callback_binding(self.external_heat_into_wall))


__all__ = ["CylinderWallThermal"]
