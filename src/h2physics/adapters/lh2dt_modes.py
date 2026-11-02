"""Explicit equipment modes that delegate to actual native components.

No branch is selected because a solver failed. An isolated pump assembly may
select an existing closed valve, representing an explicitly declared ideal
instantaneous shutdown/isolation limit, not a rotor or casing transient.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ..equipment import BoundaryPower
from .lh2dt import Lh2dtProperties


@dataclass(frozen=True, slots=True)
class Lh2dtEquipmentMode:
    component: Any
    power_reader: Callable[[Any], BoundaryPower]


@dataclass(frozen=True, slots=True)
class EquipmentModeEvaluation:
    native: Any
    mode_id: str
    boundary_power: BoundaryPower

    def __getattr__(self, name):
        return getattr(self.native, name)


class Lh2dtModeSwitch:
    """Select one declared native two-port component and its power reader."""

    def __init__(self, bridge: Lh2dtProperties, modes: Mapping[str, Lh2dtEquipmentMode], *, mode_id: str):
        if not modes or any(not name.strip() for name in modes):
            raise ValueError("Equipment modes require nonempty identities")
        for mode in modes.values():
            if getattr(mode.component, "properties", None) is not bridge.native:
                raise ValueError("Every mode must share the declared native property instance")
            if not callable(mode.power_reader):
                raise TypeError("Every mode requires its own explicit power reader")
        self.properties = bridge.native
        self.modes = MappingProxyType(dict(modes))
        self.set_mode(mode_id)

    def set_mode(self, mode_id: str):
        if mode_id not in self.modes:
            raise ValueError(f"Unknown equipment mode {mode_id!r}")
        self._mode_id = mode_id

    @property
    def mode_id(self):
        return self._mode_id

    def evaluate(self, left, right):
        mode_id = self._mode_id
        branch = self.modes[mode_id]
        native = branch.component.evaluate(left, right)
        power = branch.power_reader(native)
        if not isinstance(power, BoundaryPower):
            raise TypeError("A mode power reader must return BoundaryPower")
        return EquipmentModeEvaluation(native, mode_id, power)

    def evaluate_mass_flow(self, left, right):
        return self.evaluate(left, right).mass_flow_kg_s
