"""Actual native steady and finite-volume cold-side recovery contracts.

LH2DT owns cooling, EOS calls, mass/U/wall derivatives and RK integration.
Host heat is signed into the fluid-plus-wall system; it is not chiller power.
Primary APIs: https://github.com/lyullee/lh2dt_models and
https://coolprop.org/coolprop/HighLevelAPI.html.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field as dataclass_field, replace
from typing import Any

from ..core import Origin, ThermoState, finite
from ..equipment import BoundaryPower, ConnectionTransfer, EquipmentTolerances
from .lh2dt import Lh2dtProperties, from_lh2dt_state, to_lh2dt_state
from .lh2dt_dynamics import Lh2dtInventoryNode, lumped_inventory_reader
from .result_provenance import recorded_content_sha256


_PENDING_RELIQUEFIER_RESULT_ISSUERS: set[object] = set()


def _issue_result(result_type, **values):
    """Issue a one-use constructor token to an actual native result path."""
    token = object()
    _PENDING_RELIQUEFIER_RESULT_ISSUERS.add(token)
    try:
        return result_type(**values, _issuer_token=token)
    except Exception:
        _PENDING_RELIQUEFIER_RESULT_ISSUERS.discard(token)
        raise


def _result_content(value):
    return tuple((name, getattr(value, name)) for name in value.__dataclass_fields__
                 if name not in {"_issuer_token", "_seal"})


@dataclass(frozen=True, slots=True)
class ReliquefactionDomain:
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_temperature_k: float
    maximum_temperature_k: float
    evidence_id: str

    def __post_init__(self):
        if not self.evidence_id.strip():
            raise ValueError("A declared property/operating-domain evidence identity is required")
        for lower, upper in (("minimum_pressure_pa", "maximum_pressure_pa"),
                             ("minimum_temperature_k", "maximum_temperature_k")):
            if finite(getattr(self, lower), lower, positive=True) >= finite(
                    getattr(self, upper), upper, positive=True):
                raise ValueError("Reliquefaction domain bounds must increase")

    def require_state(self, state):
        if not self.minimum_pressure_pa <= state.pressure_pa <= self.maximum_pressure_pa:
            raise ValueError("Pressure is outside the declared reliquefaction domain")
        if not self.minimum_temperature_k <= state.temperature_k <= self.maximum_temperature_k:
            raise ValueError("Temperature is outside the declared reliquefaction domain")


@dataclass(frozen=True, slots=True)
class ColdSideBoundary:
    clock_id: str
    support_start_s: float
    support_end_s: float
    temperature_k: float | Callable[[float], float]
    source_id: str
    origin: Origin

    def __post_init__(self):
        if (not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not isinstance(self.source_id, str) or not self.source_id.strip()):
            raise ValueError("Cold-side source and absolute clock identities are required")
        if finite(self.support_start_s, "support start") >= finite(self.support_end_s, "support end"):
            raise ValueError("Cold-side clock support must increase")
        if not callable(self.temperature_k):
            finite(self.temperature_k, "cold-side temperature", positive=True)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Cold-side parameter/observation origin must be resolved")

    def value(self, time_s):
        time = finite(time_s, "absolute cold-side time")
        if not self.support_start_s <= time <= self.support_end_s:
            raise ValueError("Cold-side boundary evaluated outside declared absolute clock support")
        value = self.temperature_k(time) if callable(self.temperature_k) else self.temperature_k
        return finite(value, "cold-side reservoir temperature", positive=True)


def liquid_mass_fraction(state: ThermoState) -> float | None:
    """Resolved equilibrium liquid fraction; supercritical identity stays unavailable."""
    if state.vapor_mass_fraction is not None:
        return 1-state.vapor_mass_fraction
    if state.phase == "liquid":
        return 1.
    if state.phase in {"gas", "supercritical_gas"}:
        return 0.
    if state.phase in {"supercritical", "supercritical_liquid"}:
        return None
    raise ValueError("The selected state does not resolve an admitted fluid phase")


class _ReliquefierProperties:
    def __init__(self, native, bridge, state_factory, domain):
        import CoolProp.CoolProp as cp

        if native.properties is not bridge.native:
            raise ValueError("Reliquefier and bridge must share the exact native property instance")
        if bridge.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}:
            raise ValueError("This checked recovery level requires an explicit pure-H2 spin provider")
        self.native, self.bridge, self.state_factory, self.domain = native, bridge, state_factory, domain
        self.basis = bridge.basis
        fluid = self.basis.fluid
        self.triple_pressure_pa, self.critical_pressure_pa = cp.PropsSI("ptriple", fluid), cp.PropsSI("pcrit", fluid)
        self.eos_minimum_temperature_k = cp.PropsSI("Tmin", fluid)
        self.eos_maximum_temperature_k = cp.PropsSI("Tmax", fluid)
        self.eos_maximum_pressure_pa = cp.PropsSI("pmax", fluid)
        self._identity()

    def _identity(self):
        self.basis.require_compatible(self.bridge.basis)
        if self.native.properties is not self.bridge.native or self.bridge.native.fluid != self.basis.fluid:
            raise ValueError("Reliquefier property ownership or pure-H2 identity changed")
        basis = getattr(self.bridge.native, "basis", None)
        if basis is not None:
            self.basis.require_compatible(basis)

    def _state(self, native):
        result = from_lh2dt_state(native, basis=self.basis)
        self.domain.require_state(result)
        if (not self.eos_minimum_temperature_k <= result.temperature_k <= self.eos_maximum_temperature_k
                or result.pressure_pa > self.eos_maximum_pressure_pa):
            raise ValueError("State is outside the native EOS metadata limits")
        liquid_mass_fraction(result)
        return result

    def _input(self, state):
        self._identity()
        self.basis.require_compatible(state.basis)
        raw = to_lh2dt_state(state, expected_basis=self.basis, factory=self.state_factory)
        self._state(raw)
        recovered = self.bridge.state_ph(state.pressure_pa, state.enthalpy_j_kg)
        for name in ("temperature_k", "density_kg_m3", "internal_energy_j_kg", "entropy_j_kg_k"):
            if abs(getattr(recovered, name)-getattr(state, name)) > 1e-7*max(abs(getattr(state, name)), 1.):
                raise ValueError(f"Inlet is inconsistent with the selected native provider: {name}")
        if recovered.phase != state.phase:
            raise ValueError("Inlet phase identity differs from its native PH reconstruction")
        if ((recovered.vapor_mass_fraction is None) != (state.vapor_mass_fraction is None)
                or (state.vapor_mass_fraction is not None and abs(
                    recovered.vapor_mass_fraction-state.vapor_mass_fraction) > 1e-7)):
            raise ValueError("Inlet vapor quality differs from its native PH reconstruction")
        return raw


@dataclass(frozen=True, slots=True)
class SteadyReliquefierResult:
    inlet: ThermoState
    outlet: ThermoState
    target_quality: float
    transfer: ConnectionTransfer
    inlet_liquid_mass_fraction: float | None
    outlet_liquid_mass_fraction: float
    net_liquid_production_kg_s: float | None
    native_component: Any
    native_inlet: Any
    native_result: Any
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_RELIQUEFIER_RESULT_ISSUERS:
            raise ValueError("Steady reliquefier results must be issued by the native evaluator")
        _PENDING_RELIQUEFIER_RESULT_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_seal", recorded_content_sha256(_result_content(self)))

    def require_current(self):
        if self.inlet is not self.transfer.upstream or self.outlet is not self.transfer.transmitted:
            raise ValueError("Steady reliquefier result lost its native transfer state ownership")
        if recorded_content_sha256(_result_content(self)) != self._seal:
            raise ValueError("Native steady reliquefier result changed after issuance")
        return self

    @property
    def power(self):
        return self.transfer.power

    @property
    def liquid_outflow_kg_s(self):
        return self.transfer.mass_flow_kg_s*self.outlet_liquid_mass_fraction

    @property
    def capacity_limited(self):
        return self.native_result.capacity_limited

    @property
    def energy_residual_w(self):
        return self.transfer.energy_residual_w


class ReliquefierClosureError(RuntimeError):
    def __init__(self, native, violations):
        self.native = native
        self.violations = tuple(violations)
        super().__init__("; ".join(self.violations))


class Lh2dtSteadyReliquefier(_ReliquefierProperties):
    """Capacity-limited native cooling point; no hydraulic/cycle performance law."""

    def __init__(self, native, bridge: Lh2dtProperties, *, state_factory: Callable,
                 domain: ReliquefactionDomain, component_id: str,
                 tolerances: EquipmentTolerances | None = None):
        super().__init__(native, bridge, state_factory, domain)
        if not component_id.strip():
            raise ValueError("A reliquefier component identity is required")
        self.component_id, self.tolerances = component_id, tolerances or EquipmentTolerances()

    def evaluate(self, inlet: ThermoState, *, outlet_pressure_pa: float,
                 mass_flow_kg_s: float, target_quality: float = 0.) -> SteadyReliquefierResult:
        native_inlet = self._input(inlet)
        flow = finite(mass_flow_kg_s, "forward mass flow", positive=True)
        pressure = finite(outlet_pressure_pa, "outlet pressure", positive=True)
        quality = finite(target_quality, "target vapor quality")
        if not 0 <= quality <= 1:
            raise ValueError("Target vapor quality must lie in [0, 1]")
        if not self.triple_pressure_pa < pressure < self.critical_pressure_pa:
            raise ValueError("The steady native saturation target needs pressure between triple and critical")
        if (pressure > inlet.pressure_pa
                and not math.isclose(pressure, inlet.pressure_pa, rel_tol=1e-12)):
            raise ValueError("A passive cooling point cannot supply an unmodeled pressure increase")
        capacity = finite(self.native.cooling_capacity, "native cooling capacity", positive=True)
        raw = self.native.evaluate(native_inlet, pressure, flow, target_quality=quality)
        try:
            outlet = self._state(raw.outlet)
        except ValueError as error:
            raise ReliquefierClosureError(raw, (str(error),)) from error
        before, after = liquid_mass_fraction(inlet), liquid_mass_fraction(outlet)
        if after is None:
            raise ReliquefierClosureError(raw, ("Native outlet liquid fraction is unresolved",))
        power = BoundaryPower(heat_w=-finite(raw.heat_removed_W, "native removed heat"))
        transfer = ConnectionTransfer(self.component_id, f"{self.component_id}:inlet",
            f"{self.component_id}:outlet", f"{self.component_id}/in", f"{self.component_id}/out",
            flow, inlet, outlet, power, None, None)
        result = _issue_result(SteadyReliquefierResult, inlet=inlet, outlet=outlet,
            target_quality=quality, transfer=transfer, inlet_liquid_mass_fraction=before,
            outlet_liquid_mass_fraction=after,
            net_liquid_production_kg_s=None if before is None else flow*(after-before),
            native_component=self.native, native_inlet=native_inlet, native_result=raw)
        violations = []
        if (raw.heat_removed_W < 0 or raw.heat_removed_W > capacity
                or raw.heat_removed_W > raw.requested_heat_removal_W+1e-9):
            violations.append("Native cooling duty exceeds its capacity or requested nonnegative duty")
        if abs(raw.liquefied_mass_fraction-after) > 1e-7:
            violations.append("Native total liquid fraction differs from the actual outlet phase")
        if not math.isclose(outlet.pressure_pa, pressure, rel_tol=1e-8):
            violations.append("Native cooling outlet pressure differs from the selected boundary")
        if abs(result.energy_residual_w) > self.tolerances.energy_limit_w(
                transfer.inlet_enthalpy_flow_w, transfer.outlet_enthalpy_flow_w, power.total_w):
            violations.append("Native steady enthalpy/cold-duty ledger does not close")
        if violations:
            raise ReliquefierClosureError(raw, violations)
        return result


@dataclass(frozen=True, slots=True)
class ReliquefierDerivative:
    fluid: ThermoState
    external_power: BoundaryPower
    fluid_wall_heat_w: float
    total_storage_rate_w: float
    energy_residual_w: float
    native: Any


@dataclass(frozen=True, slots=True)
class ReliquefierStep:
    fluid: ThermoState
    inventory: Any
    liquid_inventory_kg: float | None
    final_rates: ReliquefierDerivative
    native: Any
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_RELIQUEFIER_RESULT_ISSUERS:
            raise ValueError("Dynamic reliquefier steps must be issued by the native integrator")
        _PENDING_RELIQUEFIER_RESULT_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_seal", recorded_content_sha256(_result_content(self)))

    def require_current(self):
        if recorded_content_sha256(_result_content(self)) != self._seal:
            raise ValueError("Native dynamic reliquefier result changed after issuance")
        return self


@dataclass(frozen=True, slots=True)
class ReliquefierInventoryBinding:
    inventory_node: Lh2dtInventoryNode
    original_native_node: Any
    native_component: Any
    cold_boundary: ColdSideBoundary


class Lh2dtDynamicReliquefier(_ReliquefierProperties):
    """Native finite fluid/wall dynamics with an explicit cold-reservoir clock."""

    def __init__(self, native, bridge: Lh2dtProperties, *, state_factory: Callable,
                 domain: ReliquefactionDomain, cold_boundary: ColdSideBoundary):
        super().__init__(native, bridge, state_factory, domain)
        self.cold_boundary = cold_boundary
        self._wall_capacity = native.wall_heat_capacity
        self.inventory_reader = lumped_inventory_reader(native.wall_heat_capacity, self.basis)

    def _identity(self):
        super()._identity()
        if hasattr(self, "_wall_capacity") and self.native.wall_heat_capacity != self._wall_capacity:
            raise ValueError("Wall heat capacity changed outside the declared stored-energy contract")

    def initialize(self, fluid: ThermoState, *, wall_temperature_k: float):
        return self.native.initialize(self._input(fluid),
            wall_temperature_K=finite(wall_temperature_k, "wall temperature", positive=True))

    def fluid(self, state):
        self._identity()
        return self._state(self.native.thermo(state))

    def inventory(self, state):
        self.fluid(state)
        return self.inventory_reader(state)

    def _rates(self, state, derivative):
        fluid = self.fluid(state)
        total = derivative.internal_energy_W+self.native.wall_heat_capacity*derivative.wall_temperature_K_s
        residual = (total-derivative.inlet_enthalpy_flow_W+derivative.outlet_enthalpy_flow_W
                    - derivative.heat_from_ambient_W)
        if abs(residual) > 1e-8:
            raise ReliquefierClosureError(derivative, ("Native fluid+wall instantaneous energy does not close",))
        return ReliquefierDerivative(fluid, BoundaryPower(heat_w=derivative.heat_from_ambient_W),
                                     derivative.heat_from_wall_W, total, residual, derivative)

    def derivative(self, state, inlet: ThermoState, mass_flow_in_kg_s, mass_flow_out_kg_s, *, time_s):
        raw_inlet = self._input(inlet)
        self.fluid(state)
        incoming, outgoing = finite(mass_flow_in_kg_s, "inlet flow"), finite(mass_flow_out_kg_s, "outlet flow")
        if incoming < 0 or outgoing < 0:
            raise ValueError("Forward inlet/outlet rates cannot be negative or silently reversed")
        raw = self.native.derivative(state, raw_inlet, incoming, outgoing,
                                    ambient_temperature_K=self.cold_boundary.value(time_s))
        return self._rates(state, raw)

    def step(self, state, inlet: ThermoState, mass_flow_in_kg_s, mass_flow_out_kg_s, *,
             time_s, time_step_s):
        if callable(self.cold_boundary.temperature_k):
            raise ValueError("Time-varying cold-side forcing requires the native inventory-node integrator")
        width = finite(time_step_s, "time step", positive=True)
        self.cold_boundary.value(time_s+width)
        self.derivative(state, inlet, mass_flow_in_kg_s, mass_flow_out_kg_s, time_s=time_s)
        raw = self.native.step(state, self._input(inlet), mass_flow_in_kg_s,
            mass_flow_out_kg_s, width, ambient_temperature_K=self.cold_boundary.value(time_s))
        try:
            fluid = self._state(raw.fluid)
            fraction = liquid_mass_fraction(fluid)
            inventory, rates = self.inventory(raw.state), self._rates(raw.state, raw.derivative)
        except (ValueError, ReliquefierClosureError) as error:
            raise ReliquefierClosureError(raw, (str(error),)) from error
        return _issue_result(ReliquefierStep, fluid=fluid, inventory=inventory,
            liquid_inventory_kg=None if fraction is None else raw.state.mass_kg*fraction,
            final_rates=rates, native=raw)

    def inventory_binding(self, name, initial_state, *, node_factory: Callable):
        """Reuse native dynamic_vaporizer_node and existing accepted-step host driver."""
        self.inventory(initial_state)
        original = node_factory(name, self.native, initial_state,
                                ambient_temperature_K=self.cold_boundary.value)

        def thermo(state):
            raw = self.native.thermo(state)
            self._state(raw)
            return raw

        def derivative(state, flows, time_s):
            self.fluid(state)
            raw = original.derivative(state, flows, time_s)
            self._rates(state, raw)
            return raw

        checked = replace(original, thermo=thermo, derivative=derivative)
        return ReliquefierInventoryBinding(Lh2dtInventoryNode(checked, self.inventory),
                                           original, self.native, self.cold_boundary)
