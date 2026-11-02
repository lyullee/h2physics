"""Evidence-bound conservative reactant inventory current limiting.

This is a caller-selected feedback policy for the synchronized fuel-cell
driver. It prevents a closed gas compartment from being depleted below explicit
H2/O2 reserves by tapering current; it does not localize or report a solver event.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from math import isclose

from ..core import finite
from ..constants import FARADAY_C_MOL
from ..electrochemistry import HydrogenStack


@dataclass(frozen=True, slots=True)
class FuelCellCurrentLimitDecision:
    time_s: float
    clock_id: str
    requested_current_density_a_m2: float
    available_current_density_a_m2: float
    applied_current_density_a_m2: float
    hydrogen_inventory_above_reserve_mol: float
    oxygen_inventory_above_reserve_mol: float
    limiting_reactant: str
    hydrogen_reserve_mol: float
    oxygen_reserve_mol: float
    response_horizon_s: float
    hydrogen_moles_per_electron: float
    oxygen_moles_per_electron: float
    stoichiometry_evidence_id: str
    policy_evidence_id: str


@dataclass(frozen=True, slots=True)
class FuelCellReactantCurrentLimit:
    """Callable live-state current taper protecting finite H2/O2 reserves.

    `requested_current_density` is the unmodified caller demand. The cap assumes
    the existing fuel-cell stoichiometry H2 + 0.5 O2 -> H2O, unit Faradaic
    utilization in the synchronized driver, no external withdrawal from either
    compartment, and a declared response horizon. It is conservative when
    nonnegative feed is later added. Each reserve must lie strictly above the
    native driver's independent failure floor.
    """

    stack: HydrogenStack
    requested_current_density: Callable = field(repr=False, compare=False)
    hydrogen_reserve_mol: float
    oxygen_reserve_mol: float
    solver_inventory_floor_mol: float
    response_horizon_s: float
    hydrogen_moles_per_electron: float
    oxygen_moles_per_electron: float
    stoichiometry_evidence_id: str
    policy_evidence_id: str

    def __post_init__(self):
        if type(self.stack) is not HydrogenStack:
            raise TypeError("Reuse the HydrogenStack passed to the coupled driver")
        if not callable(self.requested_current_density):
            raise TypeError("Supply an explicit caller current-demand callback")
        floor = finite(self.solver_inventory_floor_mol, "solver inventory floor", positive=True)
        for name in ("hydrogen_reserve_mol", "oxygen_reserve_mol"):
            value = finite(getattr(self, name), name, positive=True)
            if value <= floor:
                raise ValueError("Reactant reserves must be strictly above the native solver floor")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "solver_inventory_floor_mol", floor)
        object.__setattr__(self, "response_horizon_s",
                           finite(self.response_horizon_s, "response horizon", positive=True))
        hydrogen_per_e = finite(self.hydrogen_moles_per_electron,
                                "hydrogen moles per electron", positive=True)
        oxygen_per_e = finite(self.oxygen_moles_per_electron,
                              "oxygen moles per electron", positive=True)
        if (not isclose(hydrogen_per_e, 0.5, rel_tol=0., abs_tol=1e-14)
                or not isclose(oxygen_per_e, 0.25, rel_tol=0., abs_tol=1e-14)):
            raise ValueError("This limiter only admits the declared H2/O2-to-vapor stoichiometry")
        object.__setattr__(self, "hydrogen_moles_per_electron", hydrogen_per_e)
        object.__setattr__(self, "oxygen_moles_per_electron", oxygen_per_e)
        for name in ("stoichiometry_evidence_id", "policy_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")

    def require_driver_compatibility(self, stack, solver_floor_mol):
        if stack is not self.stack:
            raise ValueError("Current limiter and coupled driver must retain the same HydrogenStack")
        floor = finite(solver_floor_mol, "driver inventory floor", positive=True)
        if floor != self.solver_inventory_floor_mol:
            raise ValueError("Current limiter reserve must bind the driver's exact reactant floor")
        if (self.hydrogen_reserve_mol <= floor or self.oxygen_reserve_mol <= floor):
            raise ValueError("Current limiter reserves must remain above the driver's floor")
        return self

    def decision(self, view) -> FuelCellCurrentLimitDecision:
        """Return an auditable cap at one synchronized native trial state."""
        required = ("time_s", "clock_id", "channels")
        if any(not hasattr(view, name) for name in required):
            raise TypeError("Supply the live synchronized fuel-cell trial view")
        channels = view.channels
        if set(channels) != {"hydrogen", "oxygen", "water_vapor"}:
            raise ValueError("Current limiting needs separated H2/O2/water trial channels")
        hydrogen, oxygen = channels["hydrogen"], channels["oxygen"]
        for role, state in (("hydrogen", hydrogen), ("oxygen", oxygen)):
            if getattr(state, "role", None) != role:
                raise ValueError("Fuel-cell trial channel roles are inconsistent")
            state.require_current()
            if state.time_s != view.time_s or state.clock_id != view.clock_id:
                raise ValueError("Current limiter requires an exact shared channel time and clock")
        h2_available = max(0., hydrogen.species_moles_mol - self.hydrogen_reserve_mol)
        o2_available = max(0., oxygen.species_moles_mol - self.oxygen_reserve_mol)
        cells = self.stack.geometry.series_cells
        area = self.stack.geometry.active_area_m2
        horizon = self.response_horizon_s
        h2_current_cap = (h2_available * FARADAY_C_MOL
                          / (self.hydrogen_moles_per_electron * cells * horizon * area))
        o2_current_cap = (o2_available * FARADAY_C_MOL
                          / (self.oxygen_moles_per_electron * cells * horizon * area))
        if h2_current_cap <= o2_current_cap:
            available, limiting = h2_current_cap, "hydrogen"
        else:
            available, limiting = o2_current_cap, "oxygen"
        requested = finite(self.requested_current_density(view),
                           "requested current density")
        if requested < 0.:
            raise ValueError("Requested current density cannot be negative")
        applied = min(requested, available)
        return FuelCellCurrentLimitDecision(
            finite(view.time_s, "trial time"), view.clock_id,
            requested, available, applied, h2_available, o2_available,
            limiting if applied < requested else "none",
            self.hydrogen_reserve_mol, self.oxygen_reserve_mol,
            self.response_horizon_s, self.hydrogen_moles_per_electron,
            self.oxygen_moles_per_electron, self.stoichiometry_evidence_id,
            self.policy_evidence_id,
        )

    def __call__(self, view) -> float:
        """Return the applied nonnegative current density for the native RHS."""
        return self.decision(view).applied_current_density_a_m2


__all__ = ["FuelCellCurrentLimitDecision", "FuelCellReactantCurrentLimit"]
