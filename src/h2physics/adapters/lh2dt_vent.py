"""Checked native steady vent hydraulics and finite-UA enthalpy transport.

LH2DT owns the stack and heat integration; the existing shared Darcy bridge is
an explicit selectable hydraulic provider. No terminal nozzle/source is inferred.
"""

from collections.abc import Callable
from copy import copy
from dataclasses import dataclass
from math import isclose, pi
from typing import Any

from scipy.integrate import quad

from ..core import ThermoState, finite
from ..equipment import BoundaryPower, ConnectionTransfer, EquipmentTolerances
from .lh2dt import Lh2dtProperties, from_lh2dt_state, to_lh2dt_state
from .lh2dt_hydraulics import Lh2dtDarcyPipe


@dataclass(frozen=True, slots=True)
class VentEnvelope:
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_temperature_k: float
    maximum_temperature_k: float
    maximum_pressure_fraction: float
    maximum_density_change_fraction: float
    maximum_mach_number: float
    evidence_id: str

    def __post_init__(self):
        for lower, upper in ((self.minimum_pressure_pa, self.maximum_pressure_pa),
                             (self.minimum_temperature_k, self.maximum_temperature_k)):
            if finite(lower, "envelope lower", positive=True) >= finite(upper, "envelope upper", positive=True):
                raise ValueError("Vent envelope bounds must increase")
        if not 0. < finite(self.maximum_pressure_fraction, "maximum_pressure_fraction") < 1.:
            raise ValueError("Declare a bounded quasi-steady pressure-fraction envelope")
        if not 0. < finite(self.maximum_density_change_fraction, "maximum_density_change_fraction") < 1.:
            raise ValueError("Declare a bounded upstream-density approximation envelope")
        if not 0. < finite(self.maximum_mach_number, "maximum_mach_number") <= .3:
            raise ValueError("This quasi-steady vent level requires an explicit low-Mach limit <=0.3")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Vent applicability needs explicit evidence")

    def require_state(self, state):
        if not self.minimum_pressure_pa <= state.pressure_pa <= self.maximum_pressure_pa:
            raise ValueError("Vent state pressure is outside the declared envelope")
        if not self.minimum_temperature_k <= state.temperature_k <= self.maximum_temperature_k:
            raise ValueError("Vent state temperature is outside the declared envelope")
        if (state.phase not in {"gas", "supercritical_gas", "supercritical"}
                or state.vapor_mass_fraction is not None):
            raise ValueError("This vent level requires dry single gas; phase boundaries are unsupported")


@dataclass(frozen=True, slots=True)
class VentThermalAudit:
    configured_ua_w_k: float
    reconstructed_ua_w_k: float | None
    residual_w_k: float | None
    quadrature_error_w_k: float | None
    status: str


@dataclass(frozen=True, slots=True)
class VentResult:
    transfer: ConnectionTransfer
    left: ThermoState
    right: ThermoState
    outlet: ThermoState | None
    native_outlet: Any | None
    native_stack: Any
    original_native_stack: Any
    native_result: Any
    hydraulic_result: Any
    friction_law_id: str
    oriented_native_heat_w: float
    independent_momentum_residual_pa: float | None
    thermal_audit: VentThermalAudit
    direction_blocked: bool
    evidence_id: str
    potential_energy_change_j_kg: float | None = None
    upstream_hydraulic_kinetic_energy_j_kg: float | None = None
    upstream_mach_number: float | None = None
    downstream_section_mach_number: float | None = None
    energy_scope: str = "steady enthalpy transport; port kinetic/potential energy changes unresolved"
    mach_scope: str = "upstream hydraulics and same-bore downstream pipe-section estimate; not an atmospheric plane"

    @property
    def power(self):
        return self.transfer.power


class VentClosureError(RuntimeError):
    def __init__(self, native_result, native_stack, hydraulic_result, errors, *, evaluation=None):
        self.native_result, self.native_stack = native_result, native_stack
        self.hydraulic_result, self.evaluation = hydraulic_result, evaluation
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


class _CapturePipe:
    def __init__(self, component):
        self.component, self.result = component, None

    def __getattr__(self, name):
        return getattr(self.component, name)

    def evaluate(self, left, right):
        self.result = self.component.evaluate(left, right)
        return self.result


class Lh2dtVentStack:
    """Actual native stack evaluation with independent pressure/thermal gates.

    Returned outlet is a downstream-pressure PH transport state. It has no
    inferred discharge velocity, source plane, choking state or atmospheric area.
    """

    def __init__(self, native_stack, bridge: Lh2dtProperties, *, state_factory: Callable,
                 envelope: VentEnvelope, component_id: str, evidence_id: str,
                 allow_reverse: bool, viscosity_reader: Callable[[Any], float],
                 sound_speed_reader: Callable[[Any], float], sound_speed_capability_id: str,
                 hydraulic_pipe: Lh2dtDarcyPipe | None = None,
                 tolerances: EquipmentTolerances | None = None,
                 thermal_ua_relative_tolerance: float = 1e-5,
                 thermal_ua_absolute_tolerance_w_k: float = 1e-8):
        if any(not isinstance(value, str) or not value.strip() for value in (component_id, evidence_id)):
            raise ValueError("Declare vent component and geometry/UA/source evidence identities")
        if not isinstance(allow_reverse, bool) or native_stack.allow_reverse != allow_reverse:
            raise ValueError("Explicit reverse-flow policy must match the selected native stack")
        if not callable(state_factory) or not callable(viscosity_reader) or not callable(sound_speed_reader):
            raise TypeError("Supply native state factory, phase viscosity and actual provider sound-speed capabilities")
        if not isinstance(sound_speed_capability_id, str) or not sound_speed_capability_id.strip():
            raise ValueError("Declare the actual sound-speed provider/state basis")
        if native_stack.properties is not bridge.native or native_stack.pipe.properties is not bridge.native:
            raise ValueError("Native vent, hydraulic pipe and bridge must share the property instance")
        if hydraulic_pipe is not None and (not isinstance(hydraulic_pipe, Lh2dtDarcyPipe)
                or hydraulic_pipe.native_pipe is not native_stack.pipe
                or hydraulic_pipe.properties is not bridge.native):
            raise ValueError("Select the existing shared Darcy bridge over this exact native pipe/provider")
        self.native, self.bridge, self.state_factory = native_stack, bridge, state_factory
        self.original_pipe, self.hydraulic_pipe = native_stack.pipe, hydraulic_pipe
        self.envelope, self.component_id, self.evidence_id = envelope, component_id, evidence_id
        self.allow_reverse, self.viscosity_reader = allow_reverse, viscosity_reader
        self.sound_speed_reader, self.sound_speed_capability_id = sound_speed_reader, sound_speed_capability_id
        self.tolerances = tolerances or EquipmentTolerances()
        self.ua_relative = finite(thermal_ua_relative_tolerance, "thermal_ua_relative_tolerance", positive=True)
        self.ua_absolute = finite(thermal_ua_absolute_tolerance_w_k, "thermal_ua_absolute_tolerance_w_k", positive=True)
        self.friction_law_id = (hydraulic_pipe.friction_law_id if hydraulic_pipe is not None
            else "native-HEMPipe-fixed-iteration-laminar-Haaland")
        self._basis = bridge.basis

    def _state(self, state):
        self._basis.require_compatible(state.basis)
        self.envelope.require_state(state)
        recovered = self.bridge.state_pt(state.pressure_pa, state.temperature_k)
        self.envelope.require_state(recovered)
        for name in ("pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg",
                     "internal_energy_j_kg", "entropy_j_kg_k"):
            expected, actual = getattr(state, name), getattr(recovered, name)
            if abs(expected - actual) > self.tolerances.relative * max(1., abs(expected)):
                raise ValueError(f"Vent port state disagrees with the selected property reference: {name}")
        return to_lh2dt_state(state, expected_basis=self._basis, factory=self.state_factory)

    def _thermal(self, upstream, downstream_pressure, outlet_h, mass):
        ua = finite(self.native.ambient_UA_W_K, "native ambient_UA_W_K")
        if ua < 0.:
            raise ValueError("Native ambient UA must be nonnegative")
        if ua == 0.:
            return VentThermalAudit(ua, None, None, None, "adiabatic")
        start = self.bridge.state_ph(downstream_pressure, upstream.enthalpy_j_kg)
        target = self.bridge.state_pt(downstream_pressure, self.native.ambient_temperature_K)
        self.envelope.require_state(start)
        self.envelope.require_state(target)
        if mass <= 1e-14:
            raise ValueError("Native near-zero-flow thermal shortcut cannot resolve a finite-UA transported state")
        if abs(start.temperature_k - target.temperature_k) <= 1e-8:
            if abs(outlet_h - start.enthalpy_j_kg) > 1e-6:
                raise ValueError("Native equilibrium thermal limit changed transport enthalpy")
            return VentThermalAudit(ua, None, None, None, "equal-temperature limit; UA not identifiable")
        lower, upper = sorted((upstream.enthalpy_j_kg, target.enthalpy_j_kg))
        if not lower < outlet_h < upper:
            raise ValueError("Finite-UA outlet reaches/crosses an ambient endpoint; native clamping/resolution unresolved")

        def inverse_rhs(enthalpy):
            state = self.bridge.state_ph(downstream_pressure, enthalpy)
            self.envelope.require_state(state)
            return 1. / (target.temperature_k - state.temperature_k)

        integral, error = quad(inverse_rhs, upstream.enthalpy_j_kg, outlet_h,
                               epsabs=self.ua_absolute / max(mass, 1e-30) / 10.,
                               epsrel=min(1e-9, self.ua_relative / 10.), limit=150)
        required = mass * integral
        residual = required - ua
        budget = max(self.ua_absolute, ua * self.ua_relative)
        if not abs(residual) + mass * error <= budget:
            raise ValueError(f"Native finite-UA integration fails independent conductance audit: {residual:.12g} W/K")
        return VentThermalAudit(ua, required, residual, mass * error, "independent inverse-UA quadrature")

    def evaluate(self, left: ThermoState, right: ThermoState, *, left_node: str,
                 right_node: str, left_port_id: str, right_port_id: str) -> VentResult:
        self._basis.require_compatible(self.bridge.basis)
        native_basis = getattr(self.bridge.native, "basis", None)
        if native_basis is not None:
            self._basis.require_compatible(native_basis)
        if self.bridge.native.fluid != self._basis.fluid:
            raise ValueError("Native vent fluid identity differs from the declared property basis")
        if (self.native.properties is not self.bridge.native or self.native.pipe is not self.original_pipe
                or self.original_pipe.properties is not self.bridge.native
                or self.native.allow_reverse != self.allow_reverse):
            raise ValueError("Native vent provider/pipe/direction policy changed; bind the new configuration explicitly")
        if self.original_pipe.heat != 0.:
            raise ValueError("Native vent hydraulic pipe must not add a second hidden heat boundary")
        left_native, right_native = self._state(left), self._state(right)
        fraction = abs(left.pressure_pa - right.pressure_pa) / max(left.pressure_pa, right.pressure_pa)
        if fraction > self.envelope.maximum_pressure_fraction:
            raise ValueError("Vent pressure difference exceeds the declared quasi-steady upstream-density envelope")
        selected = copy(self.native)
        captured = _CapturePipe(self.hydraulic_pipe or self.original_pipe)
        selected.pipe = captured  # Per-evaluation composition; supplied object/source remain untouched.
        raw = selected.evaluate(left_native, right_native)
        errors = []
        try:
            rate = finite(raw.mass_flow_kg_s, "native vent mass_flow_kg_s")
            oriented_heat = finite(raw.heat_into_fluid_W, "native oriented heat_into_fluid_W")
            hydraulic = captured.result
            hydraulic_rate = finite(hydraulic.mass_flow_kg_s, "native hydraulic mass_flow_kg_s")
            blocked = not self.allow_reverse and hydraulic_rate < 0.
            if blocked and (rate != 0. or raw.upstream_side is not None or raw.momentum_residual_Pa is not None):
                raise ValueError("One-way blocked vent must retain unavailable momentum and no transported state")
            if not blocked and abs(rate - hydraulic_rate) > self.tolerances.mass_absolute_kg_s:
                raise ValueError("Native vent changed the selected hydraulic flow")
            if rate == 0.:
                if oriented_heat != 0.:
                    raise ValueError("A stagnant steady vent cannot carry external heat without thermal storage")
                residual = None if blocked else finite(raw.momentum_residual_Pa, "stagnant momentum residual")
                if residual is not None and abs(residual) > self.tolerances.momentum_absolute_pa:
                    raise ValueError("Stagnant vent has an unresolved hydraulic momentum deficit")
                transfer = ConnectionTransfer(self.component_id, left_node, right_node, left_port_id,
                    right_port_id, 0., None, None, BoundaryPower(), residual, None)
                thermal = VentThermalAudit(self.native.ambient_UA_W_K, None, None, None, "no transported flow")
                return VentResult(transfer, left, right, None, None, selected, self.native, raw,
                    hydraulic, self.friction_law_id, oriented_heat, residual, thermal, blocked, self.evidence_id)
            forward = rate > 0.
            upstream, downstream = (left, right) if forward else (right, left)
            upstream_native = left_native if forward else right_native
            if raw.upstream_side != ("left" if forward else "right"):
                raise ValueError("Native vent upstream-side label disagrees with its signed flow")
            magnitude = abs(rate)
            diameter = finite(self.original_pipe.diameter, "native diameter", positive=True)
            velocity = magnitude / (upstream.density_kg_m3 * pi * diameter**2 / 4.)
            upstream_sound = finite(self.sound_speed_reader(upstream_native), "provider upstream sound speed_m_s", positive=True)
            upstream_mach = velocity / upstream_sound
            if upstream_mach > self.envelope.maximum_mach_number:
                errors.append("Upstream hydraulic Mach exceeds the declared low-Mach vent envelope")
            viscosity = finite(self.viscosity_reader(upstream_native), "selected viscosity", positive=True)
            reynolds = upstream.density_kg_m3 * velocity * diameter / viscosity
            if not isclose(finite(raw.reynolds_number, "native Reynolds number"), reynolds,
                           rel_tol=self.tolerances.relative, abs_tol=1e-8):
                errors.append("Native reported Reynolds number disagrees with actual flow/viscosity")
            friction = finite(raw.darcy_friction_factor, "native Darcy friction", positive=True)
            dz = self.original_pipe.dz * (1. if forward else -1.)
            modeled_drop = (upstream.density_kg_m3 * 9.80665 * dz
                + (friction * self.original_pipe.length / diameter + self.original_pipe.local_k)
                * upstream.density_kg_m3 * velocity**2 / 2.)
            residual = upstream.pressure_pa - downstream.pressure_pa - modeled_drop
            reported_residual = finite(raw.momentum_residual_Pa, "native momentum residual")
            reported_drop = finite(raw.pressure_drop_Pa, "native pressure drop")
            pressure_budget = max(self.tolerances.momentum_absolute_pa,
                                  self.tolerances.relative * max(abs(modeled_drop), 1.))
            if (abs(residual) > pressure_budget or abs(reported_residual - residual) > pressure_budget
                    or abs(reported_drop - modeled_drop) > pressure_budget):
                errors.append("Independent final Darcy/gravity momentum audit fails")
            outlet_h = finite(raw.outlet_specific_enthalpy_J_kg, "native outlet enthalpy")
            native_outlet = self.bridge.native.from_ph(downstream.pressure_pa, outlet_h)
            outlet = from_lh2dt_state(native_outlet, basis=self._basis)
            self.envelope.require_state(outlet)
            outlet_sound = finite(self.sound_speed_reader(native_outlet), "provider downstream sound speed_m_s", positive=True)
            # Same native bore only: this is a section estimate, not a source-plane velocity.
            section_velocity = magnitude / (outlet.density_kg_m3 * pi * diameter**2 / 4.)
            section_mach = section_velocity / outlet_sound
            if section_mach > self.envelope.maximum_mach_number:
                errors.append("Downstream same-bore section Mach exceeds the declared low-Mach vent envelope")
            density_change = abs(outlet.density_kg_m3 / upstream.density_kg_m3 - 1.)
            if density_change > self.envelope.maximum_density_change_fraction:
                errors.append("Vent outlet density change exceeds declared upstream-density approximation envelope")
            # Native reverse heat is left-to-right oriented; common heat is into the actual fluid.
            physical_heat = oriented_heat * (1. if forward else -1.)
            transfer = ConnectionTransfer(self.component_id, left_node, right_node, left_port_id,
                right_port_id, rate, upstream, outlet, BoundaryPower(heat_w=physical_heat), residual, None)
            energy_budget = self.tolerances.energy_limit_w(transfer.inlet_enthalpy_flow_w,
                transfer.outlet_enthalpy_flow_w, physical_heat)
            if abs(transfer.energy_residual_w) > energy_budget:
                errors.append("Resolved native outlet fails the common enthalpy/heat ledger")
            thermal = self._thermal(upstream, downstream.pressure_pa, outlet_h, magnitude)
        except (ValueError, TypeError, AttributeError, ZeroDivisionError) as error:
            raise VentClosureError(raw, selected, captured.result, (*errors, str(error))) from error
        result = VentResult(transfer, left, right, outlet, native_outlet, selected, self.native,
            raw, hydraulic, self.friction_law_id, oriented_heat, residual, thermal, False, self.evidence_id,
            potential_energy_change_j_kg=9.80665 * dz,
            upstream_hydraulic_kinetic_energy_j_kg=velocity**2 / 2.,
            upstream_mach_number=upstream_mach, downstream_section_mach_number=section_mach)
        if errors:
            raise VentClosureError(raw, selected, hydraulic, errors, evaluation=result)
        return result
