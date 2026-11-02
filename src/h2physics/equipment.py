"""Steady enthalpy-transport ledgers shared by optional native equipment engines.

Heat and shaft work are positive into the modeled fluid. Port kinetic and
potential energy are outside this declared steady enthalpy-only accounting.
No equipment correlation, flow solver or time integrator is implemented here.
"""

from dataclasses import dataclass

from .core import ThermoState, finite


@dataclass(frozen=True, slots=True)
class BoundaryPower:
    heat_w: float = 0.
    shaft_work_w: float = 0.

    def __post_init__(self):
        finite(self.heat_w, "heat_w")
        finite(self.shaft_work_w, "shaft_work_w")

    @property
    def total_w(self):
        return self.heat_w + self.shaft_work_w


@dataclass(frozen=True, slots=True)
class ConnectionTransfer:
    component_id: str
    left_node: str
    right_node: str
    left_port_id: str
    right_port_id: str
    mass_flow_kg_s: float
    upstream: ThermoState | None
    transmitted: ThermoState | None
    power: BoundaryPower
    momentum_residual_pa: float | None
    operating_point_admissible: bool | None

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip() for value in (
                self.component_id, self.left_node, self.right_node,
                self.left_port_id, self.right_port_id)):
            raise ValueError("Component, node and port identities must be explicit")
        if self.left_node == self.right_node or self.left_port_id == self.right_port_id:
            raise ValueError("A connection needs distinct nodes and ports")
        finite(self.mass_flow_kg_s, "mass_flow_kg_s")
        if self.momentum_residual_pa is not None:
            finite(self.momentum_residual_pa, "momentum_residual_pa")
        if self.operating_point_admissible is not None and not isinstance(self.operating_point_admissible, bool):
            raise ValueError("Operating-point admissibility must be bool or unavailable")
        if self.mass_flow_kg_s == 0:
            if self.upstream is not None or self.transmitted is not None:
                raise ValueError("A closed connection carries no transported state")
        elif self.upstream is None or self.transmitted is None:
            raise ValueError("A nonzero connection requires both transport states")
        else:
            self.upstream.basis.require_compatible(self.transmitted.basis)

    @property
    def upstream_node(self):
        if self.mass_flow_kg_s == 0:
            return None
        return self.left_node if self.mass_flow_kg_s > 0 else self.right_node

    @property
    def downstream_node(self):
        if self.mass_flow_kg_s == 0:
            return None
        return self.right_node if self.mass_flow_kg_s > 0 else self.left_node

    @property
    def inlet_enthalpy_flow_w(self):
        return 0. if self.upstream is None else abs(self.mass_flow_kg_s) * self.upstream.enthalpy_j_kg

    @property
    def outlet_enthalpy_flow_w(self):
        return 0. if self.transmitted is None else abs(self.mass_flow_kg_s) * self.transmitted.enthalpy_j_kg

    @property
    def energy_residual_w(self):
        return self.outlet_enthalpy_flow_w - self.inlet_enthalpy_flow_w - self.power.total_w


@dataclass(frozen=True, slots=True)
class EquipmentTolerances:
    mass_absolute_kg_s: float = 1e-8
    energy_absolute_w: float = .05
    momentum_absolute_pa: float = .01
    relative: float = 1e-6

    def __post_init__(self):
        for name in ("mass_absolute_kg_s", "energy_absolute_w", "momentum_absolute_pa", "relative"):
            finite(getattr(self, name), name, positive=True)

    def energy_limit_w(self, *terms):
        return max(self.energy_absolute_w, self.relative * max((abs(x) for x in terms), default=0.))
