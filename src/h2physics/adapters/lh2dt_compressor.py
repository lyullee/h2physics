"""Native adiabatic compressor stages and prescribed intercooling boundaries.

LH2DT owns compression and native property flashes; the host checks identity,
phase, declared envelopes and steady mass/enthalpy/power accounting. Intercooler
outlet PT is a supplied boundary, not a predicted heat-exchanger performance law.
References: https://github.com/lyullee/lh2dt_models and
https://www.grc.nasa.gov/www/k-12/airplane/compexp.html.
"""

import hashlib
import inspect
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass, replace
from pathlib import Path
from typing import Any, Literal
from weakref import WeakValueDictionary

from ..core import PropertyBasis, ThermoState, finite
from ..equipment import BoundaryPower, ConnectionTransfer, EquipmentTolerances
from .lh2dt import Lh2dtProperties, from_lh2dt_state, to_lh2dt_state
from .lh2dt_properties import Lh2dtLowLevelProperties

STATUS = "implemented_unverified"
NATIVE_REVISION = "b2f276333c1b1793c39f25763703d196d36742ec"
NATIVE_PACKAGE_SHA256 = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"


def _callable_binding(value):
    function = getattr(value, "__func__", value)
    return function, getattr(function, "__code__", None), id(getattr(value, "__self__", None))


def _record_signature(value):
    """Snapshot public records without calling an EOS or altering native state."""
    if is_dataclass(value) and not isinstance(value, type):
        return type(value), tuple((f.name, _record_signature(getattr(value, f.name)))
            for f in fields(value) if not f.name.startswith("_"))
    if isinstance(value, Mapping):
        return tuple((key, _record_signature(item)) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return tuple(_record_signature(item) for item in value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if callable(value):
        return _callable_binding(value)
    return type(value), id(value)


def _property_binding(bridge):
    """Configuration/method identity; mutable native flash working state is allowed."""
    native = bridge.native
    provider = getattr(native, "provider", None)
    backend = getattr(provider, "backend", getattr(native, "backend", None))
    if backend is not None and backend != "HEOS":
        raise ValueError("Equipment requires the reference HEOS path; no tabular-domain qualification is supplied")
    methods = tuple((obj, name, _callable_binding(getattr(obj, name)))
        for obj in (bridge, native, provider) if obj is not None
        for name in ("state_pt", "state_ph", "state_ps", "state_rho_u", "_evaluate", "_update", "_snapshot",
                     "from_pT", "from_ph", "from_ps", "from_rho_u", "_native")
        if callable(getattr(obj, name, None)))
    return (native, _record_signature(bridge.basis), _record_signature(getattr(native, "basis", None)), native.fluid,
        getattr(native, "state_factory", None), provider,
        _record_signature(getattr(provider, "basis", None)), getattr(provider, "backend", None),
        getattr(provider, "internal_energy_policy", None), getattr(provider, "quality_roundoff_tolerance", None),
        getattr(provider, "version", None), id(getattr(provider, "_state", None)),
        getattr(provider, "_cp", None), methods)


@dataclass(frozen=True, slots=True)
class Lh2dtNativeProvenance:
    """Exact installed native source and original public callable bindings.

    Capture reads source bytes only; it never imports the optional engine.
    Caller property facades are bound separately and are not native-source attestation.
    """

    source_directory: Path
    revision: str
    package_sha256: str
    files: tuple
    bindings: tuple = field(repr=False)

    @classmethod
    def capture(cls, *native_objects):
        if not native_objects:
            raise ValueError("Retain actual native equipment objects or public factories")
        directory, bindings = None, []
        for obj in native_objects:
            target = obj if inspect.isclass(obj) or inspect.isfunction(obj) else type(obj)
            module = sys.modules.get(target.__module__)
            if (not target.__module__.startswith("lh2dt.") or module is None
                    or getattr(module, target.__name__, None) is not target):
                raise TypeError("An original loaded LH2DT class/function is required")
            path = Path(inspect.getfile(target)).resolve()
            if directory is not None and directory != path.parent:
                raise ValueError("Native equipment/factories come from different installed sources")
            directory = path.parent
            names = tuple(name for name, member in inspect.getmembers(target)
                          if name in vars(target) and (inspect.isfunction(member) or inspect.ismethod(member)))
            for name in names:
                function = getattr(getattr(obj, name), "__func__", getattr(obj, name))
                if (not (is_dataclass(target) and name.startswith("__"))
                        and Path(inspect.getfile(function)).resolve().parent != path.parent):
                    raise ValueError("Native method was rebound outside the reviewed source")
            bindings.append((module, target.__name__, target, _callable_binding(target), obj,
                tuple((name, _callable_binding(getattr(obj, name))) for name in names)))
        sources = tuple((p.name, hashlib.sha256(p.read_bytes()).hexdigest())
                        for p in sorted(directory.glob("*.py")))
        digest = hashlib.sha256()
        for name, _ in sources:
            digest.update(name.encode())
            digest.update((directory/name).read_bytes())
        if digest.hexdigest() != NATIVE_PACKAGE_SHA256:
            raise ValueError("Installed LH2DT source differs from the reviewed immutable revision")
        return cls(directory, NATIVE_REVISION, digest.hexdigest(), sources, tuple(bindings))

    def require_current(self, *, check_files=True):
        if self.revision != NATIVE_REVISION or self.package_sha256 != NATIVE_PACKAGE_SHA256:
            raise ValueError("Native provenance summary no longer identifies the reviewed revision")
        for module, name, target, target_binding, obj, methods in self.bindings:
            if (sys.modules.get(target.__module__) is not module
                    or getattr(module, name, None) is not target
                    or _callable_binding(target) != target_binding):
                raise ValueError("Original native class/function binding changed")
            for method, binding in methods:
                if _callable_binding(getattr(obj, method)) != binding:
                    raise ValueError("Original native equipment method binding changed")
        if check_files:
            current = tuple((p.name, hashlib.sha256(p.read_bytes()).hexdigest())
                            for p in sorted(self.source_directory.glob("*.py")))
            if current != self.files:
                raise ValueError("Installed native source bytes changed after admission")

    @property
    def source_url(self):
        return f"https://github.com/lyullee/lh2dt_models/tree/{self.revision}"

    @property
    def license_id(self):
        return "MIT"


@dataclass(frozen=True, slots=True, weakref_slot=True)
class CompressorFiniteSource:
    """Caller-declared accepted native snapshot; no acceptance replay or withdrawal."""

    source_id: str
    clock_id: str
    time_s: float
    local_time_origin_s: float
    clock_tolerance_s: float
    node_id: str
    native_owner: object
    native_step: object
    native_state: object
    fluid: ThermoState
    mass_kg: float
    fluid_internal_energy_j: float
    provenance: Lh2dtNativeProvenance
    _owner: object = field(repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        self._owner.require_finite_source(self)


@dataclass(frozen=True, slots=True)
class CompressorEOSLimits:
    minimum_temperature_k: float
    maximum_temperature_k: float
    maximum_pressure_pa: float
    source_id: str

    def __post_init__(self):
        for name in ("minimum_temperature_k", "maximum_temperature_k", "maximum_pressure_pa"):
            finite(getattr(self, name), name, positive=True)
        if self.maximum_temperature_k <= self.minimum_temperature_k or not self.source_id.strip():
            raise ValueError("EOS limits need increasing temperature and original source identity")


@dataclass(frozen=True, slots=True)
class CompressorEnvelope:
    """Declared operating envelope, independent of the EOS validity envelope."""

    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_mass_flow_kg_s: float
    maximum_mass_flow_kg_s: float
    evidence_id: str

    def __post_init__(self):
        if not self.evidence_id.strip():
            raise ValueError("An operating-envelope evidence identity is required")
        for lower, upper in (
            ("minimum_pressure_pa", "maximum_pressure_pa"),
            ("minimum_temperature_k", "maximum_temperature_k"),
            ("minimum_mass_flow_kg_s", "maximum_mass_flow_kg_s"),
        ):
            first = finite(getattr(self, lower), lower, positive=True)
            second = finite(getattr(self, upper), upper, positive=True)
            if first >= second:
                raise ValueError("Operating-envelope bounds must increase")

    def require_state(self, state: ThermoState):
        if not self.minimum_pressure_pa <= state.pressure_pa <= self.maximum_pressure_pa:
            raise ValueError("State pressure is outside the declared compressor envelope")
        if not self.minimum_temperature_k <= state.temperature_k <= self.maximum_temperature_k:
            raise ValueError("State temperature is outside the declared compressor envelope")

    def require_flow(self, mass_flow_kg_s):
        if not self.minimum_mass_flow_kg_s <= mass_flow_kg_s <= self.maximum_mass_flow_kg_s:
            raise ValueError("Mass flow is outside the declared compressor envelope")


def _require_gas(state: ThermoState):
    if (state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or (state.vapor_mass_fraction is not None and state.vapor_mass_fraction != 1.)):
        raise ValueError("Compression requires a single gas-phase state; liquid/two-phase states are rejected")


@dataclass(frozen=True, slots=True, weakref_slot=True)
class CompressorStageResult:
    stage_id: str
    mode: str
    inlet: ThermoState
    outlet: ThermoState | None
    mass_flow_kg_s: float
    pressure_ratio: float
    isentropic_efficiency: float
    isentropic_outlet: ThermoState | None
    transfer: ConnectionTransfer
    native_component: Any
    native_result: Any | None
    native_inlet: Any | None
    native_isentropic_outlet: Any | None
    model_id: str = "lh2dt-native-adiabatic-compressor-operating-point"
    native_provenance: Lh2dtNativeProvenance | None = None
    finite_source: CompressorFiniteSource | None = None
    source_boundary: str = "prescribed-steady-inlet-no-source-inventory"
    pressure_basis: str = "Pa_absolute"
    _owner: object = field(default=None, repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        if self._owner is None:
            raise ValueError("Retain the original owner-issued compressor result")
        self._owner.require_result(self)

    @property
    def power(self) -> BoundaryPower:
        return self.transfer.power

    @property
    def energy_residual_w(self):
        return self.transfer.energy_residual_w


class CompressionClosureError(RuntimeError):
    """Retain failed actual native results for inspection."""

    def __init__(self, result: CompressorStageResult, violations):
        self.result = result
        self.native_result = result.native_result
        self.native_component = result.native_component
        self.violations = tuple(violations)
        super().__init__("; ".join(self.violations))


class CompressorBoundaryError(ValueError):
    """Original failure plus native attempt and completed serial prefix."""

    def __init__(self, cause, *, owner, stage, native_inlet=None, native_result=None,
                 native_isentropic_outlet=None, completed_stages=(), completed_cooling=(),
                 native_source_owner=None, native_source_step=None):
        super().__init__(str(cause))
        self.cause, self.owner, self.stage = cause, owner, stage
        self.native_component = getattr(owner, "native", None)
        self.native_inlet, self.native_result = native_inlet, native_result
        self.native_isentropic_outlet = native_isentropic_outlet
        self.completed_stages, self.completed_cooling = tuple(completed_stages), tuple(completed_cooling)
        self.native_source_owner, self.native_source_step = native_source_owner, native_source_step


class Lh2dtCompressorStage:
    """An actual native fixed-ratio stage with externally prescribed throughput.

    No capacity, speed, surge, choking, motor, leakage, startup or rotor map is
    inferred. Thermodynamic acceptance therefore leaves the equipment contract's
    operating_point_admissible unavailable. Isolation is an explicit ideal
    external boundary, requires zero flow and creates no transported outlet.
    """

    def __init__(self, native_compressor, bridge: Lh2dtProperties, *,
                 state_factory: Callable, stage_id: str, envelope: CompressorEnvelope,
                 tolerances: EquipmentTolerances | None = None):
        if not stage_id.strip():
            raise ValueError("A compressor stage identity is required")
        if getattr(native_compressor, "properties", None) is not bridge.native:
            raise ValueError("Native compressor and bridge must share the same property instance")
        if not callable(getattr(native_compressor, "evaluate", None)) or not callable(state_factory):
            raise TypeError("An actual native operating-point component and state factory are required")
        self.native = native_compressor
        self.bridge, self.state_factory = bridge, state_factory
        self.stage_id, self.envelope = stage_id, envelope
        self.tolerances = tolerances or EquipmentTolerances()
        self._basis = bridge.basis
        self.native_provenance = Lh2dtNativeProvenance.capture(native_compressor)
        self._native_origin, self._provenance_origin = native_compressor, self.native_provenance
        self._property_stamp = _property_binding(bridge)
        self._state_factory_stamp = _callable_binding(state_factory)
        self._results, self._sources = WeakValueDictionary(), WeakValueDictionary()
        self.eos_limits = None
        native_type = type(bridge.native)
        if (isinstance(bridge.native, Lh2dtLowLevelProperties)
                or (native_type.__module__ == "lh2dt.properties"
                    and native_type.__name__ == "HydrogenProperties")):
            import CoolProp.CoolProp as cp

            self.eos_limits = CompressorEOSLimits(cp.PropsSI("Tmin", self.basis.fluid),
                cp.PropsSI("Tmax", self.basis.fluid), cp.PropsSI("pmax", self.basis.fluid),
                self.basis.reference_id)
        self._eos_limits_stamp = _record_signature(self.eos_limits)
        self._require_identity()
        self._parameters()

    @property
    def basis(self) -> PropertyBasis:
        return self._basis

    def _require_identity(self):
        if self.native is not self._native_origin or self.native_provenance is not self._provenance_origin:
            raise ValueError("Original compressor component/provenance ownership changed")
        if _record_signature(self.eos_limits) != self._eos_limits_stamp:
            raise ValueError("Original native EOS metadata limits changed")
        self.basis.require_compatible(self.bridge.basis)
        if self.native.properties is not self.bridge.native:
            raise ValueError("Native compressor property ownership changed")
        native_basis = getattr(self.bridge.native, "basis", None)
        if native_basis is not None:
            self.basis.require_compatible(native_basis)
        if self.bridge.native.fluid != self.basis.fluid:
            raise ValueError("Native fluid identity differs from the declared compressor basis")
        self.native_provenance.require_current(check_files=False)
        if (_property_binding(self.bridge) != self._property_stamp
                or _callable_binding(self.state_factory) != self._state_factory_stamp):
            raise ValueError("Original compressor property/factory configuration or method changed")

    def _result_signature(self, result):
        return (_record_signature(result), self.stage_id, id(self.native), self._parameters(),
            _record_signature(self.envelope), _record_signature(self.eos_limits),
            _record_signature(self.tolerances), _property_binding(self.bridge))

    def _issue_result(self, result, finite_source):
        result = replace(result, native_provenance=result.native_provenance or self.native_provenance,
            finite_source=finite_source,
            source_boundary=("finite-native-accepted-snapshot-not-time-integrated-withdrawal"
                             if finite_source is not None else result.source_boundary), _owner=self)
        object.__setattr__(result, "_seal", self._result_signature(result))
        self._results[id(result)] = result
        return result

    def require_result(self, result: CompressorStageResult):
        if not isinstance(result, CompressorStageResult):
            raise TypeError("Supply an original CompressorStageResult")
        self._require_identity()
        self.native_provenance.require_current()
        if result.native_provenance is not None:
            result.native_provenance.require_current()
        if (self._results.get(id(result)) is not result or result._owner is not self
                or result._seal != self._result_signature(result)):
            raise ValueError("Original compressor result or its operating-point basis became stale")
        if result.finite_source is not None:
            result.finite_source.require_current()

    def bind_finite_source(self, native_owner, native_step, *, node_id: str,
                           local_time_origin_s: float, clock_tolerance_s: float,
                           clock_id: str, source_id: str):
        """Bind an actual accepted DynamicNetwork row, without depleting its tank.

        No finite-duration throughput is authorized. A surrounding native network
        must own withdrawal and receiver/shaft/heat integrals at every solver stage.
        """
        try:
            return self._bind_finite_source(native_owner, native_step, node_id=node_id,
                local_time_origin_s=local_time_origin_s, clock_tolerance_s=clock_tolerance_s,
                clock_id=clock_id, source_id=source_id)
        except Exception as cause:
            raise CompressorBoundaryError(cause, owner=self, stage="finite-source-admission",
                native_source_owner=native_owner, native_source_step=native_step) from cause

    def _bind_finite_source(self, native_owner, native_step, *, node_id, local_time_origin_s,
                            clock_tolerance_s, clock_id, source_id):
        self._require_identity()
        if not all(isinstance(x, str) and x.strip() for x in (node_id, clock_id, source_id)):
            raise ValueError("Declare native source node, inventory identity and absolute clock")
        if native_owner.properties is not self.bridge.native:
            raise ValueError("Finite source and compressor need the same native property instance")
        state = native_step.states[node_id]
        provenance = Lh2dtNativeProvenance.capture(native_owner, native_step, state)
        fluid = from_lh2dt_state(native_step.thermo_states[node_id], basis=self.basis)
        recovered = from_lh2dt_state(native_owner.thermo(state), basis=self.basis)
        self._check_inlet(fluid)
        for name in ("pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg",
                     "internal_energy_j_kg", "entropy_j_kg_k"):
            expected = finite(getattr(fluid, name), "source "+name)
            actual = finite(getattr(recovered, name), "recovered source "+name)
            if abs(expected-actual) > self.tolerances.relative*max(abs(expected), 1.):
                raise ValueError("Accepted source row and original finite native owner disagree")
        mass = getattr(state, "mass_kg", getattr(state, "hydrogen_mass_kg", None))
        energy = getattr(state, "internal_energy_J", getattr(state, "hydrogen_internal_energy_J", None))
        mass, energy = finite(mass, "finite source mass", positive=True), finite(energy, "finite source U")
        origin = finite(local_time_origin_s, "native source local clock origin")
        budget = finite(clock_tolerance_s, "source clock projection budget", positive=True)
        elapsed = finite(native_step.time_s, "native accepted elapsed time")
        time = finite(origin+elapsed, "accepted source absolute clock")
        if (elapsed < 0 or (elapsed > 0 and time <= origin)
                or abs((time-origin)-elapsed) > budget):
            raise ValueError("Absolute source clock loses native elapsed time beyond its budget")
        source = CompressorFiniteSource(source_id, clock_id, time, origin, budget, node_id, native_owner,
            native_step, state, fluid, mass, energy, provenance, self)
        object.__setattr__(source, "_seal", self._source_signature(source))
        self._sources[id(source)] = source
        return source

    @staticmethod
    def _source_signature(source):
        owner = source.native_owner
        return (_record_signature(source), _record_signature(source.native_step),
            _record_signature(getattr(owner, "geometry", None)),
            tuple(getattr(owner, name, None) for name in
                  ("fluid_volume", "wall_heat_capacity", "fluid_wall_UA", "ambient_UA", "maximum_heat")),
            _callable_binding(owner.thermo), id(owner.properties))

    def require_finite_source(self, source):
        if not isinstance(source, CompressorFiniteSource):
            raise TypeError("Supply an original owner-issued CompressorFiniteSource")
        self._require_identity()
        source.provenance.require_current()
        if (self._sources.get(id(source)) is not source or source._owner is not self
                or source.native_step.states.get(source.node_id) is not source.native_state
                or source._seal != self._source_signature(source)):
            raise ValueError("Original accepted finite-source snapshot/clock/state became stale")

    def _parameters(self):
        ratio = finite(self.native.pressure_ratio, "native pressure ratio", positive=True)
        efficiency = finite(self.native.isentropic_efficiency, "native isentropic efficiency", positive=True)
        if ratio <= 1 or efficiency > 1:
            raise ValueError("Native compression requires pressure ratio > 1 and efficiency in (0, 1]")
        return ratio, efficiency

    def _check_inlet(self, inlet):
        self.basis.require_compatible(inlet.basis)
        _require_gas(inlet)
        self._require_state(inlet)
        recovered = self.bridge.state_pt(inlet.pressure_pa, inlet.temperature_k)
        for name in ("pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg",
                     "internal_energy_j_kg", "entropy_j_kg_k"):
            expected = finite(getattr(inlet, name), "inlet "+name)
            actual = finite(getattr(recovered, name), "recovered inlet "+name)
            if abs(expected-actual) > self.tolerances.relative*max(abs(expected), 1.):
                raise ValueError(f"Compressor inlet is inconsistent with the selected provider: {name}")
        _require_gas(recovered)

    def _require_state(self, state):
        self.envelope.require_state(state)
        limits = self.eos_limits
        if limits is not None:
            if not limits.minimum_temperature_k <= state.temperature_k <= limits.maximum_temperature_k:
                raise ValueError("State temperature is outside the native EOS metadata limits")
            if state.pressure_pa > limits.maximum_pressure_pa:
                raise ValueError("State pressure is outside the native EOS metadata limits")

    def evaluate(self, inlet: ThermoState, mass_flow_kg_s: float, *,
                 mode: Literal["compressing", "isolated"] = "compressing",
                 upstream_node: str | None = None, downstream_node: str | None = None,
                 finite_source: CompressorFiniteSource | None = None) -> CompressorStageResult:
        """Evaluate one steady point, retaining any original failed native attempt."""
        attempt = {}
        try:
            self.native_provenance.require_current()
            if finite_source is not None:
                self.require_finite_source(finite_source)
                if inlet != finite_source.fluid:
                    raise ValueError("Compressor inlet must be the bound accepted finite-source state")
            return self._evaluate(inlet, mass_flow_kg_s, mode=mode,
                upstream_node=upstream_node, downstream_node=downstream_node,
                finite_source=finite_source, attempt=attempt)
        except CompressionClosureError:
            raise
        except Exception as cause:
            raise CompressorBoundaryError(cause, owner=self, stage="operating-point",
                native_inlet=attempt.get("inlet"), native_result=attempt.get("result"),
                native_isentropic_outlet=attempt.get("ideal")) from cause

    def _evaluate(self, inlet, mass_flow_kg_s, *, mode, upstream_node, downstream_node,
                  finite_source, attempt):
        self._require_identity()
        ratio, efficiency = self._parameters()
        self.basis.require_compatible(inlet.basis)
        flow = finite(mass_flow_kg_s, "mass_flow_kg_s")
        if flow < 0:
            raise ValueError("Reverse compressor flow is unsupported; no expander or bypass is inferred")
        if mode not in {"compressing", "isolated"}:
            raise ValueError("Choose an explicit compressing or isolated mode")
        left = upstream_node or f"{self.stage_id}:inlet"
        right = downstream_node or f"{self.stage_id}:outlet"
        if mode == "isolated":
            if flow != 0:
                raise ValueError("Ideal isolated mode requires exactly zero flow")
            transfer = ConnectionTransfer(self.stage_id, left, right,
                f"{self.stage_id}/in", f"{self.stage_id}/out", 0., None, None,
                BoundaryPower(), None, None)
            result = CompressorStageResult(self.stage_id, mode, inlet, None, 0., ratio,
                                         efficiency, None, transfer, self.native, None, None, None)
            return self._issue_result(result, finite_source)
        self.envelope.require_flow(flow)
        self._check_inlet(inlet)
        pressure = finite(inlet.pressure_pa*ratio, "outlet pressure", positive=True)
        if not self.envelope.minimum_pressure_pa <= pressure <= self.envelope.maximum_pressure_pa:
            raise ValueError("Requested outlet pressure is outside the declared compressor envelope")
        native_inlet = to_lh2dt_state(inlet, expected_basis=self.basis, factory=self.state_factory)
        attempt["inlet"] = native_inlet
        native_result = self.native.evaluate(native_inlet, flow)
        attempt["result"] = native_result
        outlet = from_lh2dt_state(native_result.outlet, basis=self.basis)
        native_ideal = self.bridge.native.from_ps(pressure, inlet.entropy_j_kg_k)
        attempt["ideal"] = native_ideal
        ideal = from_lh2dt_state(native_ideal, basis=self.basis)
        power = BoundaryPower(shaft_work_w=native_result.shaft_power_W)
        transfer = ConnectionTransfer(self.stage_id, left, right,
            f"{self.stage_id}/in", f"{self.stage_id}/out", flow, inlet, outlet, power, None, None)
        result = CompressorStageResult(self.stage_id, mode, inlet, outlet, flow, ratio,
            efficiency, ideal, transfer, self.native, native_result, native_inlet, native_ideal)
        result = replace(result, native_provenance=Lh2dtNativeProvenance.capture(self.native,
            native_inlet, native_result, native_ideal))
        failures = []
        for state in (ideal, outlet):
            try:
                self._check_inlet(state)
            except ValueError as error:
                failures.append(str(error))
        if not math.isclose(outlet.pressure_pa, pressure, rel_tol=self.tolerances.relative):
            failures.append("Native outlet does not preserve the requested pressure ratio")
        if not math.isclose(native_result.efficiency, efficiency, rel_tol=self.tolerances.relative):
            failures.append("Native result efficiency differs from the selected parameter")
        if (not math.isclose(finite(native_result.pressure_ratio, "native result pressure ratio"), ratio,
                             rel_tol=self.tolerances.relative)
                or not math.isclose(finite(native_result.pressure_rise_Pa, "native pressure rise"),
                                    pressure-inlet.pressure_pa, rel_tol=self.tolerances.relative)):
            failures.append("Native pressure-ratio/rise metadata differs from the actual absolute states")
        ideal_work = flow*(ideal.enthalpy_j_kg-inlet.enthalpy_j_kg)
        if ideal_work <= 0 or power.shaft_work_w <= 0:
            failures.append("Gas compression must require positive isentropic and shaft work")
        if abs(native_result.isentropic_power_W-ideal_work) > self.tolerances.energy_limit_w(ideal_work):
            failures.append("Native isentropic power does not match the independent PS flash")
        if abs(power.shaft_work_w*efficiency-ideal_work) > self.tolerances.energy_limit_w(ideal_work):
            failures.append("Native shaft work does not preserve the selected isentropic efficiency")
        if outlet.entropy_j_kg_k < inlet.entropy_j_kg_k-1e-6:
            failures.append("Adiabatic compression decreases entropy")
        if abs(result.energy_residual_w) > self.tolerances.energy_limit_w(
                transfer.inlet_enthalpy_flow_w, transfer.outlet_enthalpy_flow_w, power.total_w):
            failures.append("Native compressor enthalpy/shaft-power balance does not close")
        if failures:
            raise CompressionClosureError(result, failures)
        self._require_identity()
        return self._issue_result(result, finite_source)


@dataclass(frozen=True, slots=True)
class PrescribedIntercooling:
    """Specified outlet PT and pressure loss; no exchanger/utility prediction."""

    boundary_id: str
    outlet_temperature_k: float
    pressure_drop_pa: float
    evidence_id: str

    def __post_init__(self):
        if not self.boundary_id.strip() or not self.evidence_id.strip():
            raise ValueError("Cooling boundary and prescribed-state evidence identities are required")
        finite(self.outlet_temperature_k, "cooling outlet temperature", positive=True)
        if finite(self.pressure_drop_pa, "cooling pressure loss") < 0:
            raise ValueError("Cooling pressure loss cannot be negative")


@dataclass(frozen=True, slots=True)
class IntercoolingResult:
    specification: PrescribedIntercooling
    inlet: ThermoState
    outlet: ThermoState
    mass_flow_kg_s: float
    transfer: ConnectionTransfer
    native_outlet: Any
    native_properties: Any

    @property
    def power(self):
        return self.transfer.power

    @property
    def energy_residual_w(self):
        return self.transfer.energy_residual_w


@dataclass(frozen=True, slots=True, weakref_slot=True)
class CompressionTrainResult:
    train_id: str
    mode: str
    inlet: ThermoState
    outlet: ThermoState | None
    mass_flow_kg_s: float
    stages: tuple[CompressorStageResult, ...]
    intercooling: tuple[IntercoolingResult, ...]
    transfers: tuple[ConnectionTransfer, ...]
    power: BoundaryPower
    pressure_basis: str = "Pa_absolute"
    _owner: object = field(default=None, repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        if self._owner is None:
            raise ValueError("Retain the original owner-issued serial compression result")
        self._owner.require_result(self)

    @property
    def mass_residual_kg_s(self):
        # One prescribed steady throughflow, without leakage or inventory.
        return 0.

    @property
    def energy_residual_w(self):
        return (0. if self.outlet is None else self.mass_flow_kg_s
                *(self.outlet.enthalpy_j_kg-self.inlet.enthalpy_j_kg)-self.power.total_w)

    @property
    def native_components(self):
        return tuple(stage.native_component for stage in self.stages)

    @property
    def native_stage_results(self):
        return tuple(stage.native_result for stage in self.stages)


class Lh2dtCompressionTrain:
    """Serial native stages with explicitly prescribed inter/aftercooling."""

    def __init__(self, stages: Sequence[Lh2dtCompressorStage], *,
                 intercoolers: Sequence[PrescribedIntercooling | None] = (),
                 aftercooler: PrescribedIntercooling | None = None,
                 train_id: str):
        self.stages = tuple(stages)
        if not self.stages or not train_id.strip():
            raise ValueError("A compression train needs stages and an identity")
        if len({stage.stage_id for stage in self.stages}) != len(self.stages):
            raise ValueError("Compressor stage identities must be unique")
        first = self.stages[0]
        for stage in self.stages:
            first.basis.require_compatible(stage.basis)
            if stage.bridge.native is not first.bridge.native:
                raise ValueError("All stages must share the same native property instance")
        self.intercoolers = tuple(intercoolers) if intercoolers else (None,)*(len(self.stages)-1)
        if len(self.intercoolers) != len(self.stages)-1:
            raise ValueError("Declare one intercooling boundary or None between consecutive stages")
        self.aftercooler, self.train_id = aftercooler, train_id
        self._results = WeakValueDictionary()
        cooling = [item for item in (*self.intercoolers, aftercooler) if item is not None]
        if any(not isinstance(item, PrescribedIntercooling) for item in cooling):
            raise TypeError("Intercooling must be a PrescribedIntercooling boundary or None")
        ids = [stage.stage_id for stage in self.stages]+[item.boundary_id for item in cooling]
        if len(set(ids)) != len(ids):
            raise ValueError("Compression and cooling component identities must be unique")

    @property
    def basis(self):
        return self.stages[0].basis

    def _cool(self, specification, inlet, flow, stage, left, right):
        attempt = {}
        try:
            return self._cool_point(specification, inlet, flow, stage, left, right, attempt)
        except Exception as cause:
            raise CompressorBoundaryError(cause, owner=self, stage="prescribed-cooling",
                native_result=attempt.get("outlet")) from cause

    def _cool_point(self, specification, inlet, flow, stage, left, right, attempt):
        pressure = finite(inlet.pressure_pa-specification.pressure_drop_pa,
                          "intercooler outlet pressure", positive=True)
        if specification.outlet_temperature_k > inlet.temperature_k:
            raise ValueError("A prescribed intercooler cannot request a hotter outlet")
        native = stage.bridge.native.from_pT(pressure, specification.outlet_temperature_k)
        attempt["outlet"] = native
        outlet = from_lh2dt_state(native, basis=self.basis)
        stage._require_state(outlet)
        _require_gas(outlet)
        heat = flow*(outlet.enthalpy_j_kg-inlet.enthalpy_j_kg)
        if heat > 0:
            raise ValueError("Prescribed cooling must remove heat from the fluid")
        transfer = ConnectionTransfer(specification.boundary_id, left, right,
            f"{specification.boundary_id}/in", f"{specification.boundary_id}/out",
            flow, inlet, outlet, BoundaryPower(heat_w=heat), None, None)
        return IntercoolingResult(specification, inlet, outlet, flow, transfer, native, stage.bridge.native)

    def _result_signature(self, result):
        return (_record_signature(result), tuple(id(stage) for stage in self.stages),
            _record_signature(self.intercoolers), _record_signature(self.aftercooler), self.train_id)

    def require_result(self, result):
        if not isinstance(result, CompressionTrainResult):
            raise TypeError("Supply an original CompressionTrainResult")
        if (self._results.get(id(result)) is not result or result._owner is not self
                or result._seal != self._result_signature(result)):
            raise ValueError("Original serial compression/cooling result or topology became stale")
        for stage in result.stages:
            stage.require_current()

    def evaluate(self, inlet: ThermoState, mass_flow_kg_s: float, *,
                 mode: Literal["compressing", "isolated"] = "compressing",
                 finite_source: CompressorFiniteSource | None = None) -> CompressionTrainResult:
        completed = ([], [])
        try:
            return self._evaluate(inlet, mass_flow_kg_s, mode=mode,
                                  finite_source=finite_source, completed=completed)
        except Exception as cause:
            raise CompressorBoundaryError(cause, owner=self, stage="serial-compression",
                native_result=getattr(cause, "native_result", None),
                completed_stages=completed[0], completed_cooling=completed[1]) from cause

    def _evaluate(self, inlet, mass_flow_kg_s, *, mode, finite_source, completed):
        self.basis.require_compatible(inlet.basis)
        flow = finite(mass_flow_kg_s, "mass_flow_kg_s")
        stage_results, cooling_results = completed
        transfers = []
        current = inlet
        node_index = 0
        for index, stage in enumerate(self.stages):
            left, right = f"{self.train_id}:node-{node_index}", f"{self.train_id}:node-{node_index+1}"
            result = stage.evaluate(current, flow, mode=mode, upstream_node=left, downstream_node=right,
                                    finite_source=finite_source if index == 0 else None)
            stage_results.append(result)
            transfers.append(result.transfer)
            node_index += 1
            if mode == "isolated":
                continue
            current = result.outlet
            specification = self.aftercooler if index == len(self.stages)-1 else self.intercoolers[index]
            if specification is not None:
                left, right = f"{self.train_id}:node-{node_index}", f"{self.train_id}:node-{node_index+1}"
                cooled = self._cool(specification, current, flow, stage, left, right)
                cooling_results.append(cooled)
                transfers.append(cooled.transfer)
                current = cooled.outlet
                node_index += 1
        power = BoundaryPower(sum(item.power.heat_w for item in transfers),
                              sum(item.power.shaft_work_w for item in transfers))
        result = CompressionTrainResult(self.train_id, mode, inlet,
            None if mode == "isolated" else current, flow, tuple(stage_results),
            tuple(cooling_results), tuple(transfers), power)
        tolerance = self.stages[0].tolerances
        if abs(result.energy_residual_w) > tolerance.energy_limit_w(
                flow*inlet.enthalpy_j_kg, power.total_w):
            raise RuntimeError("Serial compression/cooling boundary enthalpy ledger does not close")
        result = replace(result, _owner=self)
        object.__setattr__(result, "_seal", self._result_signature(result))
        self._results[id(result)] = result
        return result
