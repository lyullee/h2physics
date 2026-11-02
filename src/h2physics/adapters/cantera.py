"""Native Cantera composition without copying a reaction solver or mechanism.

API references: https://cantera.org/3.2/python/thermo.html and
https://cantera.org/3.2/python/zerodim.html. Mechanism identity and its applicable
domain are explicit caller inputs; ideal-gas kinetics are not a cryogenic EOS.
"""

import hashlib
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal
from weakref import WeakValueDictionary

import numpy as np

from ..core import immutable_array, finite


@dataclass(frozen=True, slots=True)
class MechanismBasis:
    identifier: str
    source_sha256: str
    license_id: str
    references: tuple[str, ...]
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_pressure_pa: float
    maximum_pressure_pa: float

    def __post_init__(self):
        if not self.identifier or not self.license_id or not self.references:
            raise ValueError("Mechanism identity, rights and scientific references are required")
        if len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256):
            raise ValueError("Declare the mechanism source SHA-256")
        for name in ("minimum_temperature_k", "maximum_temperature_k", "minimum_pressure_pa", "maximum_pressure_pa"):
            finite(getattr(self, name), name, positive=True)
        if (self.minimum_temperature_k >= self.maximum_temperature_k
                or self.minimum_pressure_pa >= self.maximum_pressure_pa):
            raise ValueError("Mechanism envelope bounds must increase")

    def require_state(self, temperature_k, pressure_pa):
        if not self.minimum_temperature_k <= temperature_k <= self.maximum_temperature_k:
            raise ValueError("Temperature is outside the declared mechanism domain")
        if not self.minimum_pressure_pa <= pressure_pa <= self.maximum_pressure_pa:
            raise ValueError("Pressure is outside the declared mechanism domain")


@dataclass(frozen=True, slots=True)
class ReactiveState:
    temperature_k: float
    pressure_pa: float
    mole_fractions: Mapping[str, float]

    def __post_init__(self):
        finite(self.temperature_k, "temperature", positive=True)
        finite(self.pressure_pa, "pressure", positive=True)
        fractions = dict(self.mole_fractions)
        if not fractions or any(not key for key in fractions):
            raise ValueError("Declare the reacting species")
        if any(finite(value, "mole fraction") < 0 for value in fractions.values()):
            raise ValueError("Mole fractions cannot be negative")
        if not math.isclose(sum(fractions.values()), 1, abs_tol=1e-12, rel_tol=0):
            raise ValueError("Mole fractions must sum to one; amounts are not silently normalized")
        object.__setattr__(self, "mole_fractions", MappingProxyType(fractions))


@dataclass(frozen=True, slots=True)
class ReactiveSnapshot:
    state: ReactiveState
    density_kg_m3: float
    enthalpy_j_kg: float
    internal_energy_j_kg: float
    elemental_mass_fractions: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class NativeMechanismSource:
    """Original caller-supplied YAML bytes; no file or transport protocol needed.

    The hash verifies these top-level bytes only. Referenced resources and
    scientific/rights qualification remain caller evidence; actual loaded native
    definitions are bound separately.
    """

    source_bytes: bytes = field(repr=False)
    phase_name: str

    def __post_init__(self):
        if not isinstance(self.source_bytes, bytes) or not self.source_bytes:
            raise ValueError("Supply original nonempty UTF-8 YAML bytes")
        self.source_bytes.decode("utf-8")
        if not isinstance(self.phase_name, str) or not self.phase_name.strip():
            raise ValueError("Declare the native YAML phase name")

    @property
    def sha256(self):
        return hashlib.sha256(self.source_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class _YamlPhaseFactory:
    constructor: Callable
    source: NativeMechanismSource

    def __call__(self):
        return self.constructor(yaml=self.source.source_bytes.decode("utf-8"),
                                name=self.source.phase_name)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class NativePhaseHandle:
    """A retained live lease on an original native phase, not a state lock."""

    owner: object
    basis: MechanismBasis
    native_phase: object
    requested_state: ReactiveState
    creation_snapshot: ReactiveSnapshot
    definition_sha256: str
    source_sha256: str
    source_bytes_verified: bool
    source_phase_name: str | None
    _seal: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        CanteraGas.require_phase_handle(self.owner, self)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class NativePhaseBinding:
    """Definition binding plus an optional exact native-state seal."""

    handle: NativePhaseHandle
    snapshot: ReactiveSnapshot
    freeze_state: bool
    state_sha256: str | None
    _seal: object = field(default=None, repr=False, compare=False)

    @property
    def native_phase(self):
        return self.handle.native_phase

    @property
    def basis(self):
        return self.handle.basis

    @property
    def snapshot_role(self):
        return "frozen-current-state" if self.freeze_state else "validated-creation-state"

    def require_current(self):
        CanteraGas.require_phase_binding(self.handle.owner, self)


class CanteraPhaseFactoryError(ValueError):
    """Original factory/admission failure with its available native context."""

    def __init__(self, cause, *, owner, stage, requested_state=None,
                 native_phase=None, handle=None, binding=None):
        super().__init__(str(cause))
        self.cause, self.owner, self.stage = cause, owner, stage
        self.requested_state, self.native_phase = requested_state, native_phase
        self.handle, self.binding = handle, binding
        self.live_handles = tuple(owner._phase_handles.values())


# Python handles support weak references explicitly; native Solution need not.
# No global registry retains every native phase ever created.
_LIVE_PHASE_HANDLES = WeakValueDictionary()

_PENDING_EQUILIBRIUM_RESULT_ISSUERS: set[object] = set()
_PENDING_REACTOR_TRACE_ISSUERS: set[object] = set()
_PENDING_FREE_FLAME_RESULT_ISSUERS: set[object] = set()


def _issue_equilibrium_result(*args, **kwargs):
    token = object()
    _PENDING_EQUILIBRIUM_RESULT_ISSUERS.add(token)
    try:
        return EquilibriumResult(*args, _issuer_token=token, **kwargs)
    except Exception:
        _PENDING_EQUILIBRIUM_RESULT_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class EquilibriumResult:
    basis: MechanismBasis
    constraint: str
    initial: ReactiveSnapshot
    final: ReactiveSnapshot
    energy_residual_j_kg: float
    maximum_element_mass_fraction_residual: float
    _owner: object = field(default=None, repr=False, compare=False)
    _phase_handle: NativePhaseHandle | None = field(default=None, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_EQUILIBRIUM_RESULT_ISSUERS:
            raise ValueError("Equilibrium results are issued only by the native solver")
        _PENDING_EQUILIBRIUM_RESULT_ISSUERS.remove(self._issuer_token)
        if self._owner is None or self._phase_handle is None:
            raise ValueError("Equilibrium result must retain its native owner and phase")
        object.__setattr__(self, "_seal", self._content_seal())

    def _content_seal(self):
        return (id(self._owner), id(self._phase_handle), id(self.basis), self.constraint,
                _snapshot_signature(self.initial), _snapshot_signature(self.final),
                self.energy_residual_j_kg, self.maximum_element_mass_fraction_residual)

    def require_current(self):
        if self._seal != self._content_seal():
            raise ValueError("Equilibrium result content changed after native issuance")
        self._owner.require_phase_handle(self._phase_handle)
        if _snapshot_signature(_snapshot(self._phase_handle.native_phase)) != _snapshot_signature(self.final):
            raise ValueError("Native equilibrium phase changed after the result was recorded")
        return self


@dataclass(frozen=True, slots=True)
class ReactorTrace:
    basis: MechanismBasis
    constraint: str
    time_s: np.ndarray
    snapshots: tuple[ReactiveSnapshot, ...]
    maximum_energy_residual_j_kg: float
    maximum_element_mass_fraction_residual: float
    _owner: object = field(default=None, repr=False, compare=False)
    _native_reactor: object = field(default=None, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_REACTOR_TRACE_ISSUERS:
            raise ValueError("Reactor traces are issued only by the native solver")
        _PENDING_REACTOR_TRACE_ISSUERS.remove(self._issuer_token)
        if self._owner is None or self._native_reactor is None:
            raise ValueError("Reactor trace must retain its native owner and reactor")
        times = np.array(self.time_s, dtype=float, copy=True)
        times = immutable_array(times, name="times")
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "_seal", self._content_seal())

    def _content_seal(self):
        return (id(self._owner), id(self._native_reactor), _basis_signature(self.basis),
                self.constraint, self.time_s.tobytes(),
                tuple(_snapshot_signature(s) for s in self.snapshots),
                self.maximum_energy_residual_j_kg,
                self.maximum_element_mass_fraction_residual)

    def require_current(self):
        if self._seal != self._content_seal():
            raise ValueError("Reactor trace content changed after native issuance")
        if _snapshot_signature(_snapshot(self._native_reactor.phase)) != _snapshot_signature(self.snapshots[-1]):
            raise ValueError("Native reactor state changed after the trace was recorded")
        return self


@dataclass(frozen=True, slots=True)
class TemperatureRiseEvent:
    rise_k: float
    lower_time_s: float | None
    upper_time_s: float | None
    linearly_estimated_time_s: float | None


@dataclass(frozen=True, slots=True)
class FlameSettings:
    width_m: float
    refinement_ratio: float = 3.0
    refinement_slope: float = 0.08
    refinement_curve: float = 0.12
    transport_model: Literal["mixture-averaged", "multicomponent"] = "multicomponent"
    soret_enabled: bool = True
    maximum_grid_points: int = 1000

    def __post_init__(self):
        finite(self.width_m, "flame domain width", positive=True)
        if finite(self.refinement_ratio, "refinement ratio") <= 2:
            raise ValueError("The grid refinement ratio must exceed two")
        if not (0 < self.refinement_slope <= 1 and 0 < self.refinement_curve <= 1):
            raise ValueError("Flame slope and curvature criteria must lie in (0, 1]")
        if self.transport_model not in {"mixture-averaged", "multicomponent"}:
            raise ValueError("Select a reviewed reacting-flow transport model")
        if self.soret_enabled and self.transport_model != "multicomponent":
            raise ValueError("This adapter level enables Soret only with multicomponent transport")
        if isinstance(self.maximum_grid_points, bool) or self.maximum_grid_points < 10:
            raise ValueError("A flame solve needs at least ten available grid points")


@dataclass(frozen=True, slots=True)
class FreeFlameResult:
    basis: MechanismBasis
    settings: FlameSettings
    speed_m_s: float
    grid_points: int
    relative_mass_flux_span: float
    native_solution: object
    native_phase_handle: NativePhaseHandle | None = None
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_FREE_FLAME_RESULT_ISSUERS:
            raise ValueError("Free-flame results are issued only by the native solver")
        _PENDING_FREE_FLAME_RESULT_ISSUERS.remove(self._issuer_token)
        if self.native_phase_handle is None:
            raise ValueError("Free-flame result must retain its native source phase handle")
        object.__setattr__(self, "_seal", self._content_seal())

    def _content_seal(self):
        flame = self.native_solution
        digest = hashlib.sha256()
        digest.update(repr((id(self.basis), self.settings, self.speed_m_s,
                            self.grid_points, self.relative_mass_flux_span,
                            id(flame), id(self.native_phase_handle),
                            flame.transport_model, flame.soret_enabled)).encode("utf-8"))
        for values in (flame.grid, flame.T, flame.velocity, flame.X, flame.density_mass,
                       (flame.P, flame.inlet.T), flame.inlet.X):
            array = np.asarray(values, dtype="<f8")
            digest.update(repr(array.shape).encode("utf-8"))
            digest.update(array.tobytes())
        return digest.digest()

    def require_current(self):
        if self._seal != self._content_seal():
            raise ValueError("Native free-flame solution changed after result issuance")
        self.native_phase_handle.require_current()
        return self


def temperature_rise_event(trace: ReactorTrace, rise_k: float) -> TemperatureRiseEvent:
    """A user-defined temperature-rise marker with its observation-grid bracket.

    This is not a universal ignition definition. A missing crossing is reported
    as None, rather than substituting the final integration time.
    """
    if not isinstance(trace, ReactorTrace):
        raise TypeError("A native Cantera ReactorTrace is required")
    trace.require_current()
    finite(rise_k, "temperature rise", positive=True)
    temperatures = np.array([s.state.temperature_k for s in trace.snapshots])
    threshold = temperatures[0] + rise_k
    hits = np.flatnonzero(temperatures >= threshold)
    if not len(hits):
        return TemperatureRiseEvent(rise_k, None, None, None)
    upper = hits[0]
    lower = upper - 1
    fraction = (threshold - temperatures[lower]) / (temperatures[upper] - temperatures[lower])
    estimate = trace.time_s[lower] + fraction * (trace.time_s[upper] - trace.time_s[lower])
    return TemperatureRiseEvent(rise_k, float(trace.time_s[lower]), float(trace.time_s[upper]), float(estimate))


def _snapshot(phase):
    state = ReactiveState(phase.T, phase.P, dict(zip(phase.species_names, phase.X, strict=True)))
    return ReactiveSnapshot(state, phase.density_mass, phase.enthalpy_mass, phase.int_energy_mass,
                            tuple((element, phase.elemental_mass_fraction(element)) for element in phase.element_names))


def _basis_signature(basis):
    return (basis.identifier, basis.source_sha256, basis.license_id, tuple(basis.references),
        basis.minimum_temperature_k, basis.maximum_temperature_k,
        basis.minimum_pressure_pa, basis.maximum_pressure_pa)


def _state_signature(state):
    return state.temperature_k, state.pressure_pa, tuple(sorted(state.mole_fractions.items()))


def _snapshot_signature(snapshot):
    return (_state_signature(snapshot.state), snapshot.density_kg_m3, snapshot.enthalpy_j_kg,
            snapshot.internal_energy_j_kg, tuple(snapshot.elemental_mass_fractions))


def _callable_signature(value):
    function = getattr(value, "__func__", value)
    code = getattr(function, "__code__", None)
    call = getattr(type(value), "__call__", None) if code is None else None
    return id(value) if call is not None else function, code, id(getattr(value, "__self__", None)), call, getattr(call, "__code__", None)


def _element_error(initial, final):
    before, after = dict(initial.elemental_mass_fractions), dict(final.elemental_mass_fractions)
    if before.keys() != after.keys():
        raise ValueError("Chemical element identities changed")
    return max(abs(after[key] - before[key]) for key in before)


class CanteraGas:
    """Own a fresh native phase for each solve; expose native factories for deep coupling.

    Public create_phase returns a retained NativePhaseHandle. Live handles guard
    reuse and definitions without retaining all historical native objects.
    Legacy callback source bytes remain unverified. from_yaml binds the original
    supplied top-level bytes to the declared SHA; it does not qualify a mechanism.
    """

    def __init__(self, phase_factory: Callable, basis: MechanismBasis):
        import cantera as ct

        if not callable(phase_factory) or not isinstance(basis, MechanismBasis):
            raise TypeError("Supply an actual native phase factory and MechanismBasis")
        MechanismBasis(**{f.name: getattr(basis, f.name) for f in basis.__dataclass_fields__.values()})
        self.ct, self.phase_factory, self.basis = ct, phase_factory, basis
        source = phase_factory.source if type(phase_factory) is _YamlPhaseFactory else None
        if source is not None and (phase_factory.constructor is not ct.Solution or source.sha256 != basis.source_sha256):
            raise ValueError("Native YAML constructor/source SHA differs from declared mechanism evidence")
        self._source = source
        self._factory_binding = (phase_factory, _callable_signature(phase_factory), basis,
            _basis_signature(basis), ct, ct.Solution, ct.__version__)
        self._source_binding = None if source is None else (source, source.sha256, source.phase_name)
        self._definition_sha256 = None
        self._phase_handles, self._phase_bindings = WeakValueDictionary(), WeakValueDictionary()
        self._legacy_handle = None

    @classmethod
    def from_yaml(cls, source: bytes | str, basis: MechanismBasis, *, phase_name: str):
        """Use original UTF-8 YAML through the native constructor; no file copy."""
        if not isinstance(basis, MechanismBasis):
            raise TypeError("Declare a MechanismBasis for these original source bytes")
        raw = source.encode("utf-8") if isinstance(source, str) else source
        original = NativeMechanismSource(raw, phase_name)
        if original.sha256 != basis.source_sha256:
            raise ValueError("Original native YAML source SHA does not match MechanismBasis")
        import cantera as ct

        return cls(_YamlPhaseFactory(ct.Solution, original), basis)

    @property
    def mechanism_source(self):
        return self._source

    @property
    def source_bytes_verified(self):
        self._guard_factory()
        return self._source is not None

    @property
    def live_phase_handle_count(self):
        return len(self._phase_handles)

    @property
    def last_legacy_phase_handle(self):
        """At most one retained legacy bare-phase context, including failures."""
        return self._legacy_handle

    def _guard_factory(self):
        factory, signature, basis, basis_signature, ct, constructor, version = self._factory_binding
        if (self.phase_factory is not factory or _callable_signature(factory) != signature
                or self.basis is not basis or _basis_signature(self.basis) != basis_signature
                or self.ct is not ct or self.ct.Solution is not constructor or self.ct.__version__ != version):
            raise ValueError("Native factory/source/domain ownership or method binding changed")
        if self._source_binding is not None:
            source, sha, name = self._source_binding
            if (self._source is not source or factory.source is not source
                    or factory.constructor is not constructor or source.sha256 != sha
                    or source.phase_name != name or sha != self.basis.source_sha256):
                raise ValueError("Original native YAML source/phase identity changed")
        elif self._source is not None:
            raise ValueError("A legacy callback cannot acquire source-byte attestation")

    def _definition(self, phase):
        # Reuse the existing native species/reaction/multiplier fingerprint.
        # Import is local to avoid a module-definition dependency cycle.
        from .cantera_volume import _phase_fingerprint

        return hashlib.sha256(repr((phase.name, self.ct.__version__,
            _phase_fingerprint(phase, include_reactions=True))).encode()).hexdigest()

    def _require_native_state(self, phase):
        if (not isinstance(phase, self.ct.Solution) or phase.thermo_model != "ideal-gas"
                or phase.n_selected_species != phase.n_species):
            raise ValueError("This adapter requires a full original native ideal-gas Solution")
        self.basis.require_state(finite(phase.T, "native temperature", positive=True),
                                 finite(phase.P, "native pressure", positive=True))
        lower = max(s.thermo.min_temp for s in phase.species())
        upper = min(s.thermo.max_temp for s in phase.species())
        if not lower <= phase.T <= upper:
            raise ValueError("Native state is outside the species thermochemistry fit domain")
        snapshot = _snapshot(phase)
        finite(snapshot.density_kg_m3, "native mass density", positive=True)
        finite(snapshot.enthalpy_j_kg, "native mass enthalpy")
        finite(snapshot.internal_energy_j_kg, "native mass internal energy")
        if any(not 0 <= finite(x, "native element fraction") <= 1 for _, x in snapshot.elemental_mass_fractions):
            raise ValueError("Invalid native elemental composition")
        return snapshot

    @staticmethod
    def _handle_seal(handle):
        return (id(handle.owner), id(handle.basis), _basis_signature(handle.basis),
            id(handle.native_phase), _state_signature(handle.requested_state),
            _snapshot_signature(handle.creation_snapshot), handle.definition_sha256,
            handle.source_sha256, handle.source_bytes_verified, handle.source_phase_name)

    def _require_handle(self, handle):
        self._guard_factory()
        if (not isinstance(handle, NativePhaseHandle) or handle.owner is not self
                or self._phase_handles.get(id(handle.native_phase)) is not handle
                or _LIVE_PHASE_HANDLES.get(id(handle.native_phase)) is not handle
                or handle._seal != self._handle_seal(handle)):
            raise ValueError("Retain the original owner-issued live native phase handle")
        if self._definition(handle.native_phase) != handle.definition_sha256:
            raise ValueError("Owned native phase definition or source identity changed")
        return handle

    def create_phase(self, initial: ReactiveState) -> NativePhaseHandle:
        """Return a fresh actual native phase in a caller-retained Python handle."""
        phase = None
        try:
            self._guard_factory()
            if not isinstance(initial, ReactiveState):
                raise TypeError("Supply a ReactiveState with explicit SI state/composition")
            requested = ReactiveState(initial.temperature_k, initial.pressure_pa, initial.mole_fractions)
            self.basis.require_state(requested.temperature_k, requested.pressure_pa)
            phase = self.phase_factory()
            if id(phase) in _LIVE_PHASE_HANDLES:
                raise ValueError("Native factory reused a phase with a live handle; TPX was not reassigned")
            if (not isinstance(phase, self.ct.Solution) or phase.thermo_model != "ideal-gas"
                    or phase.n_selected_species != phase.n_species):
                raise ValueError("This adapter requires a full native ideal-gas Solution")
            if self._source is not None and phase.name != self._source.phase_name:
                raise ValueError("Native factory returned a different source phase identity")
            definition = self._definition(phase)
            if self._definition_sha256 is not None and definition != self._definition_sha256:
                raise ValueError("Native factory returned stale or different mechanism definitions")
            if set(requested.mole_fractions)-set(phase.species_names):
                raise ValueError("The mechanism does not contain all declared species")
            phase.TPX = requested.temperature_k, requested.pressure_pa, dict(requested.mole_fractions)
            snapshot = self._require_native_state(phase)
            self._guard_factory()
            handle = NativePhaseHandle(self, self.basis, phase, requested, snapshot, definition,
                self.basis.source_sha256, self._source is not None,
                None if self._source is None else self._source.phase_name)
            object.__setattr__(handle, "_seal", self._handle_seal(handle))
            self._definition_sha256 = definition
            self._phase_handles[id(phase)] = handle
            _LIVE_PHASE_HANDLES[id(phase)] = handle
            return handle
        except Exception as cause:
            raise CanteraPhaseFactoryError(cause, owner=self, stage="create_phase",
                requested_state=initial, native_phase=phase) from cause

    def require_phase_handle(self, handle: NativePhaseHandle):
        try:
            self._require_handle(handle)
        except Exception as cause:
            raise CanteraPhaseFactoryError(cause, owner=self, stage="require_phase_handle",
                handle=handle, native_phase=getattr(handle, "native_phase", None)) from cause

    def snapshot_phase(self, handle: NativePhaseHandle) -> ReactiveSnapshot:
        """Read native mass-SI state; permitted native state evolution is retained."""
        try:
            self._require_handle(handle)
            return self._require_native_state(handle.native_phase)
        except Exception as cause:
            raise CanteraPhaseFactoryError(cause, owner=self, stage="snapshot_phase",
                handle=handle, native_phase=getattr(handle, "native_phase", None)) from cause

    def bind_phase(self, handle: NativePhaseHandle, *, freeze_state: bool = True) -> NativePhaseBinding:
        try:
            if not isinstance(freeze_state, bool):
                raise TypeError("Declare whether this reference freezes the native state")
            self._require_handle(handle)
            snapshot = self._require_native_state(handle.native_phase) if freeze_state else handle.creation_snapshot
            state_sha = hashlib.sha256(repr(_snapshot_signature(snapshot)).encode()).hexdigest() if freeze_state else None
            binding = NativePhaseBinding(handle, snapshot, freeze_state, state_sha)
            object.__setattr__(binding, "_seal", (id(handle), _snapshot_signature(snapshot), freeze_state, state_sha))
            self._phase_bindings[id(binding)] = binding
            return binding
        except Exception as cause:
            raise CanteraPhaseFactoryError(cause, owner=self, stage="bind_phase",
                handle=handle, native_phase=getattr(handle, "native_phase", None)) from cause

    def require_phase_binding(self, binding: NativePhaseBinding):
        try:
            if (not isinstance(binding, NativePhaseBinding) or self._phase_bindings.get(id(binding)) is not binding
                    or binding._seal != (id(binding.handle), _snapshot_signature(binding.snapshot),
                                         binding.freeze_state, binding.state_sha256)):
                raise ValueError("Retain the original owner-issued native phase binding")
            self._require_handle(binding.handle)
            if binding.freeze_state:
                snapshot = self._require_native_state(binding.native_phase)
                if hashlib.sha256(repr(_snapshot_signature(snapshot)).encode()).hexdigest() != binding.state_sha256:
                    raise ValueError("Frozen native phase state changed after its reference binding")
        except Exception as cause:
            raise CanteraPhaseFactoryError(cause, owner=self, stage="require_phase_binding",
                binding=binding, handle=getattr(binding, "handle", None),
                native_phase=getattr(binding, "native_phase", None)) from cause

    def _phase(self, initial: ReactiveState):
        """Compatibility bare phase; only the latest legacy handle is retained."""
        handle = self.create_phase(initial)
        self._legacy_handle = handle
        return handle.native_phase

    def equilibrium(self, initial: ReactiveState, *, constraint: Literal["HP", "UV"] = "HP",
                    relative_tolerance: float = 1e-9) -> EquilibriumResult:
        if constraint not in {"HP", "UV"}:
            raise ValueError("This adiabatic model supports HP or UV equilibrium")
        phase = self._phase(initial)
        handle = self._legacy_handle
        before = _snapshot(phase)
        phase.equilibrate(constraint, rtol=relative_tolerance)
        self.basis.require_state(phase.T, phase.P)
        after = _snapshot(phase)
        energy = "enthalpy_j_kg" if constraint == "HP" else "internal_energy_j_kg"
        return _issue_equilibrium_result(self.basis, constraint, before, after,
                                 getattr(after, energy) - getattr(before, energy),
                                 _element_error(before, after), _owner=self, _phase_handle=handle)

    def closed_reactor(self, initial: ReactiveState, time_s, *,
                       constraint: Literal["HP", "UV"] = "UV", maximum_time_step_s: float,
                       relative_tolerance: float = 1e-9,
                       absolute_tolerance: float = 1e-18) -> ReactorTrace:
        times = np.asarray(time_s, dtype=float)
        if (times.ndim != 1 or len(times) < 2 or times[0] != 0
                or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0)):
            raise ValueError("Reactor output times must start at zero and increase strictly")
        finite(maximum_time_step_s, "maximum time step", positive=True)
        phase = self._phase(initial)
        if constraint == "HP":
            reactor = self.ct.IdealGasConstPressureReactor(phase, energy="on", clone=True)
        elif constraint == "UV":
            reactor = self.ct.IdealGasReactor(phase, energy="on", clone=True)
        else:
            raise ValueError("This closed adiabatic reactor supports HP or UV constraints")
        network = self.ct.ReactorNet([reactor])
        network.rtol, network.atol = relative_tolerance, absolute_tolerance
        network.max_time_step = maximum_time_step_s
        snapshots = [_snapshot(reactor.phase)]
        for time in times[1:]:
            network.advance(float(time))
            self.basis.require_state(reactor.T, reactor.phase.P)
            snapshots.append(_snapshot(reactor.phase))
        energy = "enthalpy_j_kg" if constraint == "HP" else "internal_energy_j_kg"
        before = snapshots[0]
        token = object()
        _PENDING_REACTOR_TRACE_ISSUERS.add(token)
        try:
            return ReactorTrace(self.basis, constraint, times, tuple(snapshots),
                                max(abs(getattr(s, energy) - getattr(before, energy)) for s in snapshots),
                                max(_element_error(before, s) for s in snapshots),
                                _owner=self, _native_reactor=reactor, _issuer_token=token)
        except Exception:
            _PENDING_REACTOR_TRACE_ISSUERS.discard(token)
            raise

    def free_flame(self, initial: ReactiveState, settings: FlameSettings) -> FreeFlameResult:
        """Return an actual native freely propagating, premixed 1D flame solution.

        Grid/domain refinement and experimental comparison are caller research
        tasks. The returned object stays editable; changing it invalidates the
        recorded summary. This is not an enclosure explosion or a detonation.
        """
        handle = self.create_phase(initial)
        self._legacy_handle = handle
        phase = handle.native_phase
        if phase.basis != "mass":
            cause = ValueError("Native FreeFlame setup requires mass display basis; no automatic basis reset")
            raise CanteraPhaseFactoryError(cause, owner=self, stage="free_flame_basis",
                requested_state=initial, native_phase=phase, handle=handle) from cause
        flame = self.ct.FreeFlame(phase, width=settings.width_m)
        flame.set_refine_criteria(ratio=settings.refinement_ratio, slope=settings.refinement_slope,
                                  curve=settings.refinement_curve)
        flame.transport_model = settings.transport_model
        flame.soret_enabled = settings.soret_enabled
        flame.set_max_grid_points(flame.flame, settings.maximum_grid_points)
        flame.solve(loglevel=0, auto=True)
        for temperature in flame.T:
            self.basis.require_state(float(temperature), initial.pressure_pa)
        mass_flux = flame.density_mass * flame.velocity
        relative_span = float(np.ptp(mass_flux) / max(abs(mass_flux)))
        token = object()
        _PENDING_FREE_FLAME_RESULT_ISSUERS.add(token)
        try:
            return FreeFlameResult(self.basis, settings, float(flame.velocity[0]), len(flame.grid),
                                   relative_span, flame, handle, _issuer_token=token)
        except Exception:
            _PENDING_FREE_FLAME_RESULT_ISSUERS.discard(token)
            raise
