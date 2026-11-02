"""Finite lumped thermal inventory for the shared electrochemical stack.

The module adds one thermal state around :class:`HydrogenStack`; it does not
replace polarization, Faraday or reaction-energy ownership.  Positive stack
``unallocated_energy_rate_w`` is heat generated inside the finite inventory.
Coolant and auxiliary heat are explicit boundary rates.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.integrate import solve_ivp

from .core import ThermoState, finite
from .electrochemistry import HydrogenStack, StackResult

STATUS = "implemented_unverified"
_PENDING_COOLANT_TRACE_ISSUERS: set[object] = set()
_PENDING_THERMAL_TRACE_ISSUERS: dict[object, object] = {}


def _issue_coolant_trace_token():
    token = object()
    _PENDING_COOLANT_TRACE_ISSUERS.add(token)
    return token


def _issue_thermal_trace(owner, *values):
    token = object()
    _PENDING_THERMAL_TRACE_ISSUERS[token] = owner
    try:
        return ThermalStackTrace(*values, _issuer_token=token)
    except Exception:
        _PENDING_THERMAL_TRACE_ISSUERS.pop(token, None)
        raise


@dataclass(frozen=True, slots=True)
class FiniteCoolantReservoir:
    mass_kg: float
    pressure_pa: float
    properties: object
    temperature_bounds_k: tuple
    external_heat_w: Callable
    boundary_id: str
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        finite(self.mass_kg, "coolant mass", positive=True)
        finite(self.pressure_pa, "coolant pressure", positive=True)
        if not isinstance(self.temperature_bounds_k, (tuple, list)) or len(self.temperature_bounds_k) != 2:
            raise ValueError("Declare exactly two coolant temperature limits")
        lower, upper = (finite(value, "coolant temperature bound", positive=True)
                        for value in self.temperature_bounds_k)
        if not lower < upper or not callable(self.external_heat_w):
            raise ValueError("Declare finite coolant temperature domain and external heat callback")
        object.__setattr__(self, "temperature_bounds_k", (lower, upper))
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.boundary_id, self.clock_id, self.evidence_id)):
            raise ValueError("Declare coolant boundary, clock and property/heat evidence")

    def state(self, enthalpy):
        enthalpy = finite(enthalpy, "coolant specific enthalpy J/kg")
        state = self.properties.state_ph(self.pressure_pa, enthalpy)
        if not isinstance(state, ThermoState):
            raise TypeError("Coolant provider must return a typed thermodynamic state")
        self.properties.basis.require_compatible(state.basis)
        if (not isinstance(state, ThermoState) or state.phase != "liquid"
                or state.vapor_mass_fraction is not None
                or state.cp_j_kg_k is None or state.cp_j_kg_k <= 0
                or not self.temperature_bounds_k[0] <= state.temperature_k <= self.temperature_bounds_k[1]
                or not math.isclose(state.pressure_pa, self.pressure_pa, rel_tol=1e-10)
                or not math.isclose(state.enthalpy_j_kg, enthalpy, rel_tol=1e-9, abs_tol=1e-5)):
            raise ValueError("Coolant left its single-liquid prescribed-pressure property domain")
        return state


@dataclass(frozen=True, slots=True)
class ThermalStackBoundary:
    heat_capacity_j_k: float
    conductance_w_k: Callable[[float, float], float]
    temperature_bounds_k: tuple[float, float]
    reference_id: str
    coolant_boundary_id: str

    def __post_init__(self):
        finite(self.heat_capacity_j_k, "stack heat capacity", positive=True)
        if not isinstance(self.temperature_bounds_k, (tuple, list)) or len(self.temperature_bounds_k) != 2:
            raise ValueError("Declare exactly two stack temperature bounds")
        lower, upper = (finite(value, "stack temperature bound", positive=True)
                        for value in self.temperature_bounds_k)
        if not 0 < lower < upper < math.inf:
            raise ValueError("Declare increasing finite stack-temperature bounds")
        if not self.reference_id or not self.coolant_boundary_id:
            raise ValueError("Declare thermal reference and coolant boundary identities")
        if not callable(self.conductance_w_k):
            raise TypeError("Stack/coolant conductance must be an explicit callable")
        object.__setattr__(self, "temperature_bounds_k", (lower, upper))

    def conductance(self, stack_temperature_k, coolant_temperature_k):
        value = finite(
            self.conductance_w_k(stack_temperature_k, coolant_temperature_k),
            "stack-to-coolant conductance",
        )
        if value < 0:
            raise ValueError("Thermal conductance cannot be negative")
        return value


@dataclass(frozen=True, slots=True)
class ThermalStackStage:
    identifier: str
    start_s: float
    end_s: float
    current_density_a_m2: float
    coolant_temperature_k: float
    mode: str
    faradaic_efficiency: float = 1.0
    auxiliary_heat_into_w: float = 0.0

    def __post_init__(self):
        if not self.identifier:
            raise ValueError("Identify each held electrochemical stage")
        if finite(self.start_s, "stage start") >= finite(self.end_s, "stage end"):
            raise ValueError("A thermal stage needs an increasing time interval")
        if finite(self.current_density_a_m2, "current density") < 0:
            raise ValueError("Current density is a nonnegative magnitude")
        finite(self.coolant_temperature_k, "coolant temperature", positive=True)
        finite(self.auxiliary_heat_into_w, "auxiliary heat into stack")
        if self.mode not in {"electrolysis", "fuel_cell"}:
            raise ValueError("Select electrolysis or fuel_cell mode")
        if (isinstance(self.faradaic_efficiency, bool)
                or finite(self.faradaic_efficiency, "Faradaic efficiency") != 1.0):
            raise ValueError(
                "Finite thermal closure requires unity Faradaic efficiency; "
                "declare crossover heat and species fate in a higher-level model"
            )


@dataclass(frozen=True, slots=True)
class ThermalStackStageResult:
    command: ThermalStackStage
    initial_temperature_k: float
    final_temperature_k: float
    generated_heat_j: float
    coolant_heat_out_j: float
    auxiliary_heat_into_j: float
    internal_energy_change_j: float
    energy_residual_j: float
    initial_stack_result: StackResult
    final_stack_result: StackResult
    native_result: object
    initial_coolant_state: ThermoState | None = None
    final_coolant_state: ThermoState | None = None
    external_coolant_heat_j: float = 0.
    coolant_energy_residual_j: float = 0.


@dataclass(frozen=True, slots=True)
class ThermalStackTrace:
    initial_temperature_k: float
    final_temperature_k: float
    stages: tuple[ThermalStackStageResult, ...]
    generated_heat_j: float
    coolant_heat_out_j: float
    auxiliary_heat_into_j: float
    internal_energy_change_j: float
    energy_residual_j: float
    status: str = STATUS
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _source_owner: object = field(default=None, init=False, repr=False, compare=False)
    _integrity_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        owner = _PENDING_THERMAL_TRACE_ISSUERS.pop(self._issuer_token, None)
        if owner is None:
            raise TypeError("ThermalStackTrace is issued only by FiniteThermalStack.run")
        object.__setattr__(self, "stages", tuple(self.stages))
        object.__setattr__(self, "_source_owner", owner)
        object.__setattr__(self, "_integrity_seal", self._current_integrity_seal())

    def _current_integrity_seal(self):
        from .adapters.result_provenance import recorded_content_sha256

        owner = self._source_owner
        return recorded_content_sha256((
            id(owner), owner.stack, owner.boundary, owner.relative_tolerance,
            owner.absolute_tolerance, owner.energy_tolerance_j,
            self.initial_temperature_k, self.final_temperature_k, self.stages,
            self.generated_heat_j, self.coolant_heat_out_j,
            self.auxiliary_heat_into_j, self.internal_energy_change_j,
            self.energy_residual_j, self.status,
        ))

    def require_current(self):
        if (self._source_owner is None or not self._integrity_seal
                or self._current_integrity_seal() != self._integrity_seal):
            raise ValueError("Thermal stack trace or its source owner changed after solver issuance")
        return self


class FiniteThermalStack:
    """Piecewise-held electrical operation with a finite stack heat capacity.

    The coolant law is ``UA(T, T_coolant) * (T - T_coolant)`` and may reverse
    sign.  The solver advances temperature and independent accumulated heat
    ledgers together.  No controller, coolant inventory, crossover, ageing or
    spatial cell temperature is inferred.
    """

    def __init__(self, stack: HydrogenStack, boundary: ThermalStackBoundary, *,
                 relative_tolerance=1e-8, absolute_tolerance=1e-10,
                 energy_tolerance_j=1e-5):
        if type(stack) is not HydrogenStack or not isinstance(boundary, ThermalStackBoundary):
            raise TypeError("Supply the actual shared HydrogenStack and thermal boundary")
        for name, value in (("relative tolerance", relative_tolerance),
                            ("absolute tolerance", absolute_tolerance),
                            ("energy tolerance", energy_tolerance_j)):
            finite(value, name, positive=True)
        self.stack = stack
        self.boundary = boundary
        self.relative_tolerance = relative_tolerance
        self.absolute_tolerance = absolute_tolerance
        self.energy_tolerance_j = energy_tolerance_j

    def run(self, initial_temperature_k: float,
            stages: Sequence[ThermalStackStage]) -> ThermalStackTrace:
        temperature = finite(initial_temperature_k, "initial stack temperature", positive=True)
        commands = tuple(stages)
        if not commands:
            raise ValueError("Supply at least one electrochemical thermal stage")
        for left, right in zip(commands, commands[1:], strict=False):
            if left.end_s != right.start_s:
                raise ValueError("Thermal stages must be contiguous on one clock")
        results = []
        for command in commands:
            results.append(self._advance(temperature, command))
            temperature = results[-1].final_temperature_k
        generated = math.fsum(v.generated_heat_j for v in results)
        coolant = math.fsum(v.coolant_heat_out_j for v in results)
        auxiliary = math.fsum(v.auxiliary_heat_into_j for v in results)
        internal = self.boundary.heat_capacity_j_k * (temperature-initial_temperature_k)
        residual = internal - (generated + auxiliary - coolant)
        if abs(residual) > self.energy_tolerance_j:
            raise ValueError("Finite electrochemical thermal energy ledger did not close")
        return _issue_thermal_trace(self, initial_temperature_k, temperature, tuple(results), generated,
                                    coolant, auxiliary, internal, residual)

    def run_with_coolant(self, initial_temperature_k, initial_coolant_state, stages, *, reservoir):
        """Reuse the stack RHS with one finite constant-P liquid enthalpy state.

        Stage coolant_temperature_k is unused on this explicitly selected route.
        Reservoir mass is fixed, pressure-work is carried by enthalpy storage;
        no boiling, coolant flow, depletion or pressure dynamics are inferred.
        """
        if type(reservoir) is not FiniteCoolantReservoir or not isinstance(initial_coolant_state, ThermoState):
            raise TypeError("Supply typed finite coolant reservoir and initial liquid state")
        if reservoir.boundary_id != self.boundary.coolant_boundary_id:
            raise ValueError("Finite coolant boundary differs from stack heat-transfer boundary")
        original_configuration = _finite_coolant_configuration(self, reservoir)
        reservoir.properties.basis.require_compatible(initial_coolant_state.basis)
        checked = reservoir.state(initial_coolant_state.enthalpy_j_kg)
        if _finite_coolant_configuration(self, reservoir) != original_configuration:
            raise ValueError("Coolant initial flash changed the original configuration")
        if (initial_coolant_state.phase != "liquid"
                or initial_coolant_state.vapor_mass_fraction is not None
                or not math.isclose(checked.pressure_pa, initial_coolant_state.pressure_pa, rel_tol=1e-9)
                or not math.isclose(checked.temperature_k, initial_coolant_state.temperature_k,
                                    rel_tol=1e-9, abs_tol=1e-6)
                or not math.isclose(checked.density_kg_m3, initial_coolant_state.density_kg_m3,
                                    rel_tol=1e-8, abs_tol=1e-8)):
            raise ValueError("Initial coolant state differs from its original property provider")
        commands = tuple(stages)
        if not commands or any(type(command) is not ThermalStackStage for command in commands):
            raise TypeError("Supply explicit original held stack stages")
        for a, b in zip(commands, commands[1:]):
            if a.end_s != b.start_s:
                raise ValueError("Finite coolant stages must be contiguous")
        temperature = finite(initial_temperature_k, "initial stack temperature", positive=True)
        results = []
        coolant = initial_coolant_state
        for command in commands:
            replace(command)
            captures = []
            try:
                result = self._advance(temperature, command, reservoir=reservoir,
                                       initial_coolant=coolant, native_capture=captures)
            except Exception as cause:
                raise FiniteCoolantStackError(cause, command, tuple(results),
                                              captures[-1] if captures else None) from cause
            results.append(result)
            temperature, coolant = result.final_temperature_k, result.final_coolant_state
        return FiniteCoolantStackTrace(
            self, reservoir, initial_coolant_state, coolant, tuple(results),
            _issue_coolant_trace_token(),
        )

    def _advance(self, initial_temperature_k, command, *, reservoir=None, initial_coolant=None,
                 native_capture=None):
        lower, upper = self.boundary.temperature_bounds_k
        if not lower <= initial_temperature_k <= upper:
            raise ValueError("Initial stack temperature lies outside the declared domain")
        from .adapters.result_provenance import recorded_content_sha256
        configuration = _finite_coolant_configuration(self, reservoir)
        source_signature = recorded_content_sha256((command, initial_coolant))

        def guard():
            if _finite_coolant_configuration(self, reservoir) != configuration:
                raise ValueError("Finite coolant source or original thermal configuration changed")
            if recorded_content_sha256((command, initial_coolant)) != source_signature:
                raise ValueError("Original held stage or initial coolant state changed")

        def rates(time, state):
            guard()
            temperature = float(state[0])
            if not lower <= temperature <= upper:
                raise ValueError("Stack temperature left the declared thermal domain")
            stack_result = self.stack.evaluate(
                command.current_density_a_m2,
                temperature,
                mode=command.mode,
                faradaic_efficiency=command.faradaic_efficiency,
            )
            generated_w = finite(stack_result.unallocated_energy_rate_w, "generated stack heat")
            coolant_state = None if reservoir is None else reservoir.state(float(state[3]))
            coolant_temperature = command.coolant_temperature_k if coolant_state is None else coolant_state.temperature_k
            coolant_w = self.boundary.conductance(
                temperature, coolant_temperature
            ) * (temperature-coolant_temperature)
            net_w = generated_w + command.auxiliary_heat_into_w - coolant_w
            result = (net_w/self.boundary.heat_capacity_j_k, generated_w, coolant_w)
            if reservoir is not None:
                external = finite(reservoir.external_heat_w(time_s=time, clock_id=reservoir.clock_id,
                                                          state=coolant_state), "external coolant heat")
                result += ((coolant_w+external)/reservoir.mass_kg, external)
            guard()
            return np.array(result)

        initial_stack = self.stack.evaluate(
            command.current_density_a_m2, initial_temperature_k, mode=command.mode,
            faradaic_efficiency=command.faradaic_efficiency,
        )
        guard()
        native = solve_ivp(
            rates, (command.start_s, command.end_s),
            np.array((initial_temperature_k, 0.0, 0.0) if reservoir is None else
                     (initial_temperature_k, 0., 0., initial_coolant.enthalpy_j_kg, 0.)),
            rtol=self.relative_tolerance, atol=self.absolute_tolerance,
        )
        if native_capture is not None:
            native_capture.append(native)
        guard()
        if not native.success:
            raise ValueError("Electrochemical thermal integration failed: " + native.message)
        expected_rows = 3 if reservoir is None else 5
        if (native.y.ndim != 2 or native.y.shape[0] != expected_rows
                or native.t.ndim != 1 or native.y.shape[1] != len(native.t)
                or not len(native.t) or not np.all(np.isfinite(native.y))
                or not np.all(np.isfinite(native.t)) or np.any(np.diff(native.t) <= 0)
                or native.t[0] != command.start_s or native.t[-1] != command.end_s):
            raise ValueError("Native thermal result does not retain a finite complete stage trajectory")
        final_temperature = finite(native.y[0, -1], "final stack temperature", positive=True)
        if not lower <= final_temperature <= upper:
            raise ValueError("Final stack temperature lies outside the declared domain")
        generated, coolant = (finite(native.y[i, -1], label) for i, label in (
            (1, "integrated generated heat"), (2, "integrated coolant heat")))
        duration = command.end_s-command.start_s
        auxiliary = command.auxiliary_heat_into_w*duration
        internal = self.boundary.heat_capacity_j_k*(final_temperature-initial_temperature_k)
        residual = internal-(generated+auxiliary-coolant)
        if abs(residual) > self.energy_tolerance_j:
            raise ValueError("Electrochemical thermal stage energy ledger did not close")
        final_stack = self.stack.evaluate(
            command.current_density_a_m2, final_temperature, mode=command.mode,
            faradaic_efficiency=command.faradaic_efficiency,
        )
        guard()
        coolant_final = None if reservoir is None else reservoir.state(float(native.y[3, -1]))
        guard()
        external = 0. if reservoir is None else finite(native.y[4, -1], "integrated external coolant heat J")
        coolant_residual = 0. if reservoir is None else (
            reservoir.mass_kg*(coolant_final.enthalpy_j_kg-initial_coolant.enthalpy_j_kg)-coolant-external)
        if abs(coolant_residual) > self.energy_tolerance_j:
            raise ValueError("Finite coolant enthalpy and shared heat-transfer ledger did not close")
        return ThermalStackStageResult(command, initial_temperature_k, final_temperature,
                                       generated, coolant, auxiliary, internal, residual,
                                       initial_stack, final_stack, native,
                                       initial_coolant, coolant_final, external, coolant_residual)


@dataclass(frozen=True, slots=True)
class FiniteCoolantStackTrace:
    owner: FiniteThermalStack
    reservoir: FiniteCoolantReservoir
    initial_coolant_state: ThermoState
    final_coolant_state: ThermoState
    stages: tuple[ThermalStackStageResult, ...]
    _token: object = field(repr=False, compare=False)
    _signature: str = field(init=False, repr=False)

    def __post_init__(self):
        if self._token not in _PENDING_COOLANT_TRACE_ISSUERS:
            raise ValueError("Finite coolant traces must be issued by the native integration path")
        _PENDING_COOLANT_TRACE_ISSUERS.remove(self._token)
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        from .adapters.result_provenance import recorded_content_sha256
        return recorded_content_sha256((
            _finite_coolant_configuration(self.owner, self.reservoir),
            self.initial_coolant_state, self.final_coolant_state, self.stages,
            tuple((stage.native_result.t, stage.native_result.y) for stage in self.stages),
        ))

    def require_current(self):
        if self._content() != self._signature:
            raise ValueError("Original finite coolant trajectory or configuration changed")
        return self

    @property
    def combined_energy_residual_j(self):
        self.require_current()
        return math.fsum(stage.energy_residual_j+stage.coolant_energy_residual_j for stage in self.stages)


def _finite_coolant_configuration(owner, reservoir):
    from .adapters.result_provenance import recorded_content_sha256
    coolant = () if reservoir is None else (
        reservoir, id(reservoir.properties), reservoir.properties.basis,
        getattr(reservoir.properties, "backend", None),
        getattr(reservoir.properties, "version", None),
        getattr(reservoir.properties, "internal_energy_policy", None),
        getattr(reservoir.properties, "state_ph", None),
    )
    return recorded_content_sha256((
        id(owner), id(owner.stack), owner.stack.geometry, owner.stack.thermochemistry,
        owner.stack.losses, owner.boundary, owner.relative_tolerance,
        owner.absolute_tolerance, owner.energy_tolerance_j,
        coolant,
    ))


class FiniteCoolantStackError(RuntimeError):
    def __init__(self, cause, command, completed_stages, native_result):
        super().__init__(str(cause))
        self.cause, self.command = cause, command
        self.completed_stages, self.native_result = completed_stages, native_result
