"""Actual Caltech SDToolbox CJ/frozen shocks with native thermochemical audits.

No CJ, shock, equilibrium, kinetics or EOS solver is implemented here. Native
SDToolbox owns wave solves; Cantera owns all thermochemistry and isentropes.
The host composes native objects, checks domains and measures conservation.
"""

import hashlib
import importlib
import math
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import Origin, finite
from .cantera import MechanismBasis, ReactiveState
from .cantera_properties import _fingerprint, _phase_identity
from .cantera_volume import _phase_fingerprint, _private_native_phase

_NATIVE_SHA = "fc28928f1c4320a7307559c55d5ca834ea4eee53464b8f58bac45c3765adbe7f"
_PENDING_WAVE_ISSUERS: set[object] = set()


def _wave_value(value):
    """Stable receipt projection that includes mutable native phase state."""
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        return ("array", array.dtype.str, array.shape,
                hashlib.sha256(array.tobytes()).hexdigest())
    if isinstance(value, Mapping):
        return ("mapping", tuple(sorted((repr(key), _wave_value(item))
                                        for key, item in value.items())))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(_wave_value(item) for item in value))
    if (hasattr(value, "thermo_model") and hasattr(value, "state")
            and hasattr(value, "species_names")):
        return ("native-phase", id(value), _phase_fingerprint(value, include_reactions=True),
                _wave_value(np.asarray(value.state, dtype=float)))
    if (hasattr(value, "postshock") and hasattr(value, "thermo")
            and hasattr(value, "source_sha256")):
        provider_functions = tuple(
            (module_name, function_name,
             id(getattr(getattr(value, module_name), function_name, None)))
            for module_name, function_name in (
                ("postshock", "CJspeed"), ("postshock", "CJ_calc"),
                ("postshock", "shk_calc"), ("thermo", "soundspeed_eq"),
                ("config", "volumeBoundRatio")))
        current_source = _native_hash(Path(value.postshock.__file__).parent)
        return ("native-sdtoolbox", value.source_id, value.source_sha256,
                current_source, provider_functions)
    if hasattr(value, "__dataclass_fields__"):
        return (type(value).__module__, type(value).__qualname__,
                tuple((name, _wave_value(getattr(value, name)))
                      for name in value.__dataclass_fields__
                      if not name.startswith("_")))
    if callable(value) or isinstance(value, type):
        return ("callable", id(value))
    if isinstance(value, (str, int, float, bool, type(None))):
        return (type(value).__name__, repr(value))
    return (type(value).__module__, type(value).__qualname__, id(value), repr(value))


def _wave_result_digest(result):
    payload = tuple((name, _wave_value(getattr(result, name)))
                    for name in result.__dataclass_fields__
                    if not name.startswith("_"))
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _native_hash(directory):
    digest = hashlib.sha256()
    for path in sorted(Path(directory).glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _thermo_identity(phase):
    return _fingerprint({"thermo": _phase_identity(phase),
                         "atomic_weights": sorted((e, phase.atomic_weight(e)) for e in phase.element_names)})


@dataclass(frozen=True, slots=True)
class NativeSDToolbox:
    postshock: Any
    thermo: Any
    config: Any
    source_id: str
    source_sha256: str

    @classmethod
    def from_installed(cls):
        """Explicit optional import of the reviewed official native artifact."""
        module = importlib.import_module("sdtoolbox.postshock")
        digest = _native_hash(Path(module.__file__).parent)
        if digest != _NATIVE_SHA:
            raise ValueError("SDToolbox source differs from the reviewed official Caltech archive")
        return cls(module, importlib.import_module("sdtoolbox.thermo"),
                   importlib.import_module("sdtoolbox.config"),
                   "Caltech-SDToolbox:official-archive:c3de67d95e1586a1", digest)


@dataclass(frozen=True, slots=True)
class DetonationEvidence:
    source_id: str
    initial_state_source_id: str
    gas_phase_scope_id: str
    clock_id: str
    event_time_s: float
    frame_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("source_id", "initial_state_source_id", "gas_phase_scope_id", "clock_id", "frame_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError("Declare homogeneous initial gas, source, clock and stationary-upstream frame")
        finite(self.event_time_s, "wave reference time")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Unresolved mixture/phase evidence does not define an initial wave state")


@dataclass(frozen=True, slots=True)
class DetonationSettings:
    native_jump_relative_tolerance: float = 1e-8
    sound_density_relative_step: float = 1e-3
    sound_equilibrium_relative_tolerance: float = 1e-11
    local_density_ratio_relative_step: float = 1e-3

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            if not 0 < finite(getattr(self, name), name) < .1:
                raise ValueError("Native/audit perturbations and tolerances must lie in (0,.1)")


@dataclass(frozen=True, slots=True)
class DetonationTolerances:
    mass_flux_absolute_kg_m2_s: float = 1e-7
    momentum_absolute_pa: float = .1
    total_enthalpy_absolute_j_kg: float = .01
    elemental_mass_fraction: float = 1e-10
    sonic_relative: float = 1e-4
    native_sound_relative: float = 2e-4
    minimum_native_fit_r_squared: float = .99999

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if self.minimum_native_fit_r_squared > 1:
            raise ValueError("Native fit R squared cannot exceed one")


@dataclass(frozen=True, slots=True)
class WaveSnapshot:
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    enthalpy_j_kg: float
    internal_energy_j_kg: float
    entropy_j_kg_k: float
    mole_fractions: Mapping[str, float]
    mass_fractions: Mapping[str, float]
    elemental_mass_fractions: Mapping[str, float]

    def __post_init__(self):
        for name in ("temperature_k", "pressure_pa", "density_kg_m3"):
            finite(getattr(self, name), name, positive=True)
        for name in ("enthalpy_j_kg", "internal_energy_j_kg", "entropy_j_kg_k"):
            finite(getattr(self, name), name)
        for name in ("mole_fractions", "mass_fractions", "elemental_mass_fractions"):
            values = dict(getattr(self, name))
            if any(finite(v, name) < 0 for v in values.values()):
                raise ValueError("Native wave composition is negative; no host clipping")
            object.__setattr__(self, name, MappingProxyType(values))


@dataclass(frozen=True, slots=True)
class WaveConservation:
    upstream_relative_velocity_m_s: float
    downstream_relative_velocity_m_s: float
    downstream_lab_velocity_m_s: float
    density_ratio: float
    mass_flux_residual_kg_m2_s: float
    momentum_residual_pa: float
    total_enthalpy_residual_j_kg: float
    hugoniot_residual_j_kg: float
    maximum_element_mass_fraction_residual: float
    entropy_increase_j_kg_k: float


@dataclass(frozen=True, slots=True)
class NativeMechanismBridge:
    yaml_sha256: str
    source_thermo_sha256: str
    reloaded_thermo_sha256: str
    actual_reloaded_phase: Any
    kinetics_and_transport_used: bool = False


@dataclass(frozen=True, slots=True)
class FrozenShockResult:
    mechanism_basis: MechanismBasis
    evidence: DetonationEvidence
    initial: WaveSnapshot
    final: WaveSnapshot
    conservation: WaveConservation
    native_upstream: Any
    native_downstream: Any
    native_solver_result: Any
    source_phase: Any
    native_provider: NativeSDToolbox
    copy_audits: tuple
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_WAVE_ISSUERS:
            raise ValueError("Frozen shock results require issuance by the native shock calculation")
        _PENDING_WAVE_ISSUERS.remove(self._issuer_token)
        if not isinstance(self.mechanism_basis, MechanismBasis) or not isinstance(
                self.evidence, DetonationEvidence):
            raise TypeError("Frozen shock result requires its admitted mechanism and evidence")
        if not isinstance(self.native_provider, NativeSDToolbox):
            raise TypeError("Frozen shock result requires its issuing native provider")
        object.__setattr__(self, "copy_audits", tuple(self.copy_audits))
        object.__setattr__(self, "_seal", _wave_result_digest(self))

    def require_current(self):
        if _wave_result_digest(self) != self._seal:
            raise ValueError("Frozen shock result or native phases changed after the audited run")
        return self


@dataclass(frozen=True, slots=True)
class CJWaveResult:
    mechanism_basis: MechanismBasis
    evidence: DetonationEvidence
    settings: DetonationSettings
    initial: WaveSnapshot
    final: WaveSnapshot
    speed_m_s: float
    native_fitted_speed_m_s: float
    native_fit_r_squared: float
    native_density_ratio: float
    conservation: WaveConservation
    independent_equilibrium_sound_m_s: float
    toolbox_equilibrium_sound_m_s: float
    frozen_sound_m_s: float
    cj_sonic_relative_residual: float
    native_sound_relative_difference: float
    local_density_speed_results: tuple
    native_upstream: Any
    native_cj_phase: Any
    native_fit_result: Any
    native_cj_result: Any
    native_sound_phase: Any
    native_isentropic_phases: tuple
    native_local_density_phases: tuple
    local_density_conservation: tuple
    native_bridge: NativeMechanismBridge
    native_provider: NativeSDToolbox
    source_phase: Any
    copy_audits: tuple
    native_fit_internal_phases_available: bool = False
    native_fit_controls_exposed: bool = False
    hydrogen_partition_id: str = "mechanism-H2-spin-unresolved"
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_WAVE_ISSUERS:
            raise ValueError("CJ results require issuance by the native CJ calculation")
        _PENDING_WAVE_ISSUERS.remove(self._issuer_token)
        if (not isinstance(self.mechanism_basis, MechanismBasis)
                or not isinstance(self.evidence, DetonationEvidence)
                or not isinstance(self.settings, DetonationSettings)):
            raise TypeError("CJ result requires its admitted mechanism, evidence and settings")
        object.__setattr__(self, "local_density_speed_results", tuple(self.local_density_speed_results))
        object.__setattr__(self, "native_isentropic_phases", tuple(self.native_isentropic_phases))
        object.__setattr__(self, "native_local_density_phases", tuple(self.native_local_density_phases))
        object.__setattr__(self, "local_density_conservation", tuple(self.local_density_conservation))
        object.__setattr__(self, "copy_audits", tuple(self.copy_audits))
        object.__setattr__(self, "_seal", _wave_result_digest(self))

    def require_current(self):
        if _wave_result_digest(self) != self._seal:
            raise ValueError("CJ result or native phases changed after the audited run")
        return self


class DetonationAuditError(RuntimeError):
    """Retain attempted actual phases/native results and completed audit fields."""

    def __init__(self, message, *, adapter, native_phases, native_fit_result=None,
                 native_cj_result=None, bridge=None, diagnostics=None, copy_audits=()):
        super().__init__(message)
        self.adapter = adapter
        self.native_phases = tuple(native_phases)
        self.native_fit_result = native_fit_result
        self.native_cj_result = native_cj_result
        self.bridge = bridge
        self.diagnostics = MappingProxyType(dict(diagnostics or {}))
        self.copy_audits = tuple(copy_audits)


class SDToolboxDetonation:
    """Stationary homogeneous neutral ideal gas: equilibrium CJ/frozen shocks.

    Native CJspeed requires a mechanism filename. A managed, explicitly supplied
    ASCII-relative workspace bridges an actual source phase without altering
    native code, CWD or input-file search globals. Only identical thermochemistry
    is admitted; kinetics/transport are not used by this equilibrium level.
    """

    def __init__(self, native: NativeSDToolbox, phase_factory: Callable, basis: MechanismBasis, *,
                 native_workspace: Path | str, tolerances: DetonationTolerances = DetonationTolerances()):
        import cantera as ct

        if tuple(map(int, ct.__version__.split(".")[:2])) != (3, 2):
            raise ValueError("This native jump/phase contract is checked with Cantera3.2")
        self.ct, self.native, self.phase_factory, self.basis = ct, native, phase_factory, basis
        self.source_phase = phase_factory()
        phase = self.source_phase
        if not isinstance(phase, ct.Solution) or phase.thermo_model != "ideal-gas" or np.any(phase.charges):
            raise ValueError("An actual neutral native ideal-gas Solution is required")
        if basis.minimum_temperature_k < phase.min_temp or basis.maximum_temperature_k > phase.max_temp:
            raise ValueError("Declared mechanism envelope exceeds actual native thermo fit bounds")
        self._thermo_sha = _thermo_identity(phase)
        self._source_full_sha = _phase_fingerprint(phase, include_reactions=True)
        self.workspace = Path(native_workspace).resolve()
        cwd = Path.cwd().resolve()
        if not self.workspace.is_relative_to(cwd) or not self.workspace.relative_to(cwd).as_posix().isascii():
            raise ValueError("Native CJ file bridge needs an ASCII-relative workspace below the current directory")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.tolerances = tolerances
        self._native_functions = (native.postshock.CJspeed, native.postshock.CJ_calc,
                                  native.postshock.shk_calc, native.thermo.soundspeed_eq)
        self._volume_bound = native.config.volumeBoundRatio

    def _check_definition(self):
        if _thermo_identity(self.source_phase) != self._thermo_sha:
            raise ValueError("Actual source thermochemistry/bounds/reference changed after admission")
        if (self._native_functions != (self.native.postshock.CJspeed, self.native.postshock.CJ_calc,
                                      self.native.postshock.shk_calc, self.native.thermo.soundspeed_eq)
                or self.native.config.volumeBoundRatio != self._volume_bound):
            raise ValueError("Admitted native solver/configuration changed during the calculation")
        if _native_hash(Path(self.native.postshock.__file__).parent) != self.native.source_sha256:
            raise ValueError("Native provider source bytes changed after admission")

    def _owned(self, source, phases, audits):
        owned, audit = _private_native_phase(source, self.ct)
        owned.basis = "mass"
        phases.append(owned)
        audits.append(audit)
        return owned

    def _initial(self, state, phases, audits):
        self._check_definition()
        self.basis.require_state(state.temperature_k, state.pressure_pa)
        if set(state.mole_fractions)-set(self.source_phase.species_names):
            raise ValueError("Mechanism lacks an explicitly supplied upstream species")
        gas = self._owned(self.source_phase, phases, audits)
        gas.TPX = state.temperature_k, state.pressure_pa, dict(state.mole_fractions)
        return gas

    @staticmethod
    def _evidence(evidence):
        if not isinstance(evidence, DetonationEvidence):
            raise TypeError("Actual DetonationEvidence is required before a native wave solve")
        # Validate current fields and retain a fresh value, including for objects changed
        # through Python's explicit frozen-dataclass escape hatch.
        return DetonationEvidence(evidence.source_id, evidence.initial_state_source_id,
            evidence.gas_phase_scope_id, evidence.clock_id, evidence.event_time_s,
            evidence.frame_id, evidence.origin)

    def _snapshot(self, phase):
        self.basis.require_state(phase.T, phase.P)
        if not phase.min_temp <= phase.T <= phase.max_temp:
            raise ValueError("Native wave state is outside its actual thermo fit bounds")
        if _thermo_identity(phase) != self._thermo_sha:
            raise ValueError("Native returned phase thermochemistry changed")
        return WaveSnapshot(phase.T, phase.P, phase.density, phase.enthalpy_mass,
            phase.int_energy_mass, phase.entropy_mass,
            dict(zip(phase.species_names, phase.X, strict=True)),
            dict(zip(phase.species_names, phase.Y, strict=True)),
            {e: phase.elemental_mass_fraction(e) for e in phase.element_names})

    def _conservation(self, before, after, speed):
        j = before.density_kg_m3*speed
        u2 = j/after.density_kg_m3
        mass = after.density_kg_m3*u2-j
        momentum = after.pressure_pa+after.density_kg_m3*u2*u2-before.pressure_pa-j*speed
        enthalpy = after.enthalpy_j_kg+.5*u2*u2-before.enthalpy_j_kg-.5*speed*speed
        hugoniot = (after.internal_energy_j_kg-before.internal_energy_j_kg
                     -.5*(after.pressure_pa+before.pressure_pa)
                     *(1/before.density_kg_m3-1/after.density_kg_m3))
        if before.elemental_mass_fractions.keys() != after.elemental_mass_fractions.keys():
            raise ValueError("Native wave element identities changed")
        element = max(abs(after.elemental_mass_fractions[e]-v)
                      for e, v in before.elemental_mass_fractions.items())
        result = WaveConservation(speed, u2, speed-u2, after.density_kg_m3/before.density_kg_m3,
            mass, momentum, enthalpy, hugoniot, element, after.entropy_j_kg_k-before.entropy_j_kg_k)
        if not all(math.isfinite(getattr(result, f)) for f in result.__dataclass_fields__):
            raise ValueError("Native shock jump audit is nonfinite")
        t = self.tolerances
        if (abs(mass) > t.mass_flux_absolute_kg_m2_s or abs(momentum) > t.momentum_absolute_pa
                or max(abs(enthalpy), abs(hugoniot)) > t.total_enthalpy_absolute_j_kg
                or element > t.elemental_mass_fraction):
            raise ValueError(f"Native wave conservation audit failed: {result}")
        if result.density_ratio <= 1 or after.pressure_pa <= before.pressure_pa or result.entropy_increase_j_kg_k < 0:
            raise ValueError("Native wave is not an admissible compressive entropy-increasing shock")
        return result

    @contextmanager
    def _mechanism_bridge(self, upstream, phases, diagnostics):
        with TemporaryDirectory(dir=self.workspace, prefix="native-cj-") as directory:
            path = Path(directory)/"phase.yaml"
            text = upstream.write_yaml(precision=17)
            path.write_text(text, encoding="utf-8", newline="\n")
            relative = path.relative_to(Path.cwd().resolve()).as_posix()
            loaded = self.ct.Solution(relative)
            phases.append(loaded)
            bridge = NativeMechanismBridge(hashlib.sha256(path.read_bytes()).hexdigest(),
                _thermo_identity(upstream), _thermo_identity(loaded), loaded)
            diagnostics["mechanism_bridge"] = bridge
            if _thermo_identity(upstream) != _thermo_identity(loaded):
                raise ValueError("Native file API cannot preserve exact source thermo coefficients/bounds/reference")
            yield relative, bridge

    def frozen_shock(self, initial: ReactiveState, *, speed_m_s: float,
                     evidence: DetonationEvidence, settings: DetonationSettings = DetonationSettings()):
        speed = finite(speed_m_s, "shock speed relative to stationary upstream", positive=True)
        phases, audits, result = [], [], None
        try:
            evidence = self._evidence(evidence)
            upstream = self._initial(initial, phases, audits)
            if speed <= upstream.sound_speed:
                raise ValueError("Frozen compression shock requires speed above native upstream frozen sound")
            before = self._snapshot(upstream)
            downstream = self._owned(upstream, phases, audits)
            result = self.native.postshock.shk_calc(speed, downstream, upstream,
                settings.native_jump_relative_tolerance, settings.native_jump_relative_tolerance)
            if result is not downstream:
                raise ValueError("Native frozen shock did not return its actual attempted phase")
            after = self._snapshot(downstream)
            balance = self._conservation(before, after, speed)
            if max(abs(after.mass_fractions[k]-v) for k, v in before.mass_fractions.items()) > self.tolerances.elemental_mass_fraction:
                raise ValueError("Native frozen shock changed chemical composition")
            self._check_definition()
            token = object()
            _PENDING_WAVE_ISSUERS.add(token)
            try:
                wave = FrozenShockResult(self.basis, evidence, before, after, balance, upstream,
                    downstream, result, self.source_phase, self.native, tuple(audits),
                    _issuer_token=token)
            finally:
                _PENDING_WAVE_ISSUERS.discard(token)
            return wave
        except Exception as exc:
            raise DetonationAuditError(str(exc), adapter=self, native_phases=phases,
                                        native_cj_result=result, copy_audits=audits) from exc

    def cj(self, initial: ReactiveState, *, evidence: DetonationEvidence,
           settings: DetonationSettings = DetonationSettings()):
        phases, audits, diagnostics = [], [], {}
        fit = local = bridge = None
        try:
            evidence = self._evidence(evidence)
            upstream = self._initial(initial, phases, audits)
            before = self._snapshot(upstream)
            if (initial.mole_fractions.get("H2", 0) <= 0 or initial.mole_fractions.get("O2", 0) <= 0
                    or any(v > 0 and e not in {"H", "O", "N", "Ar"}
                           for e, v in before.elemental_mass_fractions.items())):
                raise ValueError("This gas-only CJ level requires explicit H2/O2 with H/O/N/Ar elements")
            with self._mechanism_bridge(upstream, phases, diagnostics) as (filename, bridge):
                fit = self.native.postshock.CJspeed(initial.pressure_pa, initial.temperature_k,
                    dict(initial.mole_fractions), filename, fullOutput=True)
            if not isinstance(fit, (tuple, list)) or len(fit) != 3:
                raise ValueError("Native CJ fit did not return its complete result")
            fitted_speed, r_squared, curve = fit
            rr, speeds, ratio, a, b, c = curve
            numeric = np.r_[fitted_speed, r_squared, rr, speeds, ratio, a, b, c]
            if (not np.all(np.isfinite(numeric)) or r_squared < self.tolerances.minimum_native_fit_r_squared
                    or ratio <= 1 or a <= 0 or min(rr) > ratio or max(rr) < ratio
                    or np.any(np.asarray(rr) <= 1) or np.any(np.asarray(speeds) <= 0)):
                raise ValueError("Native CJ minimum/fit is inadmissible or did not converge")
            diagnostics.update(native_fitted_speed_m_s=float(fitted_speed), native_density_ratio=float(ratio),
                               native_fit_r_squared=float(r_squared))
            downstream = self._owned(upstream, phases, audits)
            local = self.native.postshock.CJ_calc(downstream, upstream,
                settings.native_jump_relative_tolerance, settings.native_jump_relative_tolerance, float(ratio))
            if not isinstance(local, (list, tuple)) or len(local) != 2 or local[0] is not downstream:
                raise ValueError("Native fixed-ratio CJ thermochemical solve did not return its attempted phase")
            speed = finite(float(local[1]), "native closed CJ speed", positive=True)
            if speed <= upstream.sound_speed:
                raise ValueError("Native CJ wave is not supersonic into the unreacted gas")
            after = self._snapshot(downstream)
            conservation = self._conservation(before, after, speed)
            diagnostics["conservation"] = conservation
            sound_phase = self._owned(downstream, phases, audits)
            # Native sound helper perturbs T/P by1%; do not allow those observable probes outside fit scope.
            self.basis.require_state(.99*after.temperature_k, .99*after.pressure_pa)
            self.basis.require_state(1.01*after.temperature_k, 1.01*after.pressure_pa)
            toolbox_sound = finite(float(self.native.thermo.soundspeed_eq(sound_phase)),
                                   "native equilibrium sound", positive=True)
            independent_phases, pressure = [], []
            for sign in (-1, 1):
                gas = self._owned(downstream, phases, audits)
                density = after.density_kg_m3*(1+sign*settings.sound_density_relative_step)
                gas.SVX = after.entropy_j_kg_k, 1/density, downstream.X
                gas.equilibrate("SV", solver="element_potential",
                    rtol=settings.sound_equilibrium_relative_tolerance, max_steps=5000)
                self._snapshot(gas)
                independent_phases.append(gas)
                pressure.append(gas.P)
            dpdrho = (pressure[1]-pressure[0])/(2*after.density_kg_m3*settings.sound_density_relative_step)
            independent_sound = math.sqrt(finite(dpdrho, "native isentropic equilibrium derivative", positive=True))
            sonic = abs(conservation.downstream_relative_velocity_m_s/independent_sound-1)
            sound_error = abs(toolbox_sound/independent_sound-1)
            diagnostics.update(independent_equilibrium_sound_m_s=independent_sound,
                               cj_sonic_relative_residual=sonic, native_sound_relative_difference=sound_error)
            if sonic > self.tolerances.sonic_relative or sound_error > self.tolerances.native_sound_relative:
                raise ValueError("Native CJ equilibrium-sonic audit failed")
            local_states, local_speeds, local_balances = [], [], []
            for factor in (1-settings.local_density_ratio_relative_step, 1+settings.local_density_ratio_relative_step):
                gas = self._owned(upstream, phases, audits)
                native = self.native.postshock.CJ_calc(gas, upstream,
                    settings.native_jump_relative_tolerance, settings.native_jump_relative_tolerance, float(ratio*factor))
                if not isinstance(native, (list, tuple)) or len(native) != 2 or native[0] is not gas:
                    raise ValueError("Native neighboring Hugoniot solve failed")
                local_after = self._snapshot(gas)
                if not math.isfinite(native[1]) or native[1] < speed:
                    raise ValueError("Native reported CJ density is not a verified local speed minimum")
                local_balances.append(self._conservation(before, local_after, float(native[1])))
                local_states.append(gas)
                local_speeds.append((float(ratio*factor), float(native[1])))
            self._check_definition()
            token = object()
            _PENDING_WAVE_ISSUERS.add(token)
            try:
                wave = CJWaveResult(self.basis, evidence, settings, before, after, speed, float(fitted_speed),
                float(r_squared), float(ratio), conservation, independent_sound, toolbox_sound,
                float(downstream.sound_speed), sonic, sound_error, tuple(local_speeds), upstream,
                downstream, fit, local, sound_phase, tuple(independent_phases), tuple(local_states),
                tuple(local_balances), bridge, self.native, self.source_phase, tuple(audits),
                _issuer_token=token)
            finally:
                _PENDING_WAVE_ISSUERS.discard(token)
            return wave
        except Exception as exc:
            raise DetonationAuditError(str(exc), adapter=self, native_phases=phases,
                native_fit_result=fit, native_cj_result=local,
                bridge=bridge or diagnostics.get("mechanism_bridge"), diagnostics=diagnostics,
                copy_audits=audits) from exc
