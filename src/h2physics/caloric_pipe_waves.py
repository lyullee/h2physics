"""Energy-conserving one-dimensional gas-pipe pressure waves.

The solver advances the compressible Euler mass, momentum and total-energy
balances with first-order Rusanov face fluxes. Thermodynamics are supplied by
an object exposing ``basis``, ``state_pt`` and ``state_rho_u``, plus either a
caller-declared stable ``identity`` or a JSON-compatible ``configuration``
mapping; the CoolProp provider's public settings are fingerprinted directly.
Only homogeneous
single-phase gas/supercritical states are admitted. This is a separate
non-isothermal fidelity level from the fixed-temperature pipe-wave solver.

The conservative Euler balance and Rusanov flux are implemented independently
from the source code of any external package. The numerical scheme follows
Rusanov's original shock-capturing approach:
https://doi.org/10.1016/0041-5553(62)90062-9
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

import numpy as np

from .core import PropertyBasis, ThermoState, finite, immutable_array

_PENDING_TRACE_ISSUERS: set[object] = set()


def _issue_caloric_trace(**values):
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    try:
        return CaloricPipeWaveTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_TRACE_ISSUERS.discard(token)
        raise


class CaloricGasEOS(Protocol):
    """Property closure required by the conservative caloric pipe solver."""

    @property
    def basis(self) -> PropertyBasis: ...

    def state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState: ...

    def state_rho_u(self, density_kg_m3: float,
                    internal_energy_j_kg: float) -> ThermoState: ...


class CaloricDarcyFrictionLaw(Protocol):
    """Caller-owned Darcy friction factor provider for each pipe cell."""

    identity: str
    state_owner_id: str
    evidence_id: str
    clock_id: str

    def darcy_factor(self, state: ThermoState, velocity_m_s: float,
                     internal_diameter_m: float) -> float: ...


@dataclass(frozen=True, slots=True)
class UniformDarcyFriction:
    """Uniform, caller-supplied Darcy-Weisbach factor (not a correlation)."""

    factor: float
    identity: str
    state_owner_id: str
    evidence_id: str
    clock_id: str

    def __post_init__(self) -> None:
        value = finite(self.factor, "Darcy friction factor")
        if value < 0.:
            raise ValueError("Darcy friction factor must be nonnegative")
        for name in ("identity", "state_owner_id", "evidence_id", "clock_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Declare friction {name}")

    def darcy_factor(self, state: ThermoState, velocity_m_s: float,
                     internal_diameter_m: float) -> float:
        return self.factor


@dataclass(frozen=True, slots=True)
class CaloricPipeWallHeatBoundary:
    """Fixed-temperature wall heat boundary; positive heat flows into the gas."""

    identifier: str
    state_owner_id: str
    state_evidence_id: str
    clock_id: str
    wall_temperature_k: float
    heat_transfer_coefficient_w_m2_k: float

    def __post_init__(self) -> None:
        for name in ("identifier", "state_owner_id", "state_evidence_id", "clock_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Declare wall heat {name}")
        object.__setattr__(self, "wall_temperature_k",
                           finite(self.wall_temperature_k, "wall_temperature_k", positive=True))
        coefficient = finite(self.heat_transfer_coefficient_w_m2_k,
                             "heat_transfer_coefficient_w_m2_k")
        if coefficient < 0.:
            raise ValueError("Heat-transfer coefficient must be nonnegative")
        object.__setattr__(self, "heat_transfer_coefficient_w_m2_k", coefficient)


def _eos_identity(eos: CaloricGasEOS) -> str:
    explicit = getattr(eos, "identity", None)
    basis = getattr(eos, "basis", None)
    if not isinstance(basis, PropertyBasis):
        raise TypeError("EOS closure must expose a PropertyBasis")
    if explicit is not None and (not isinstance(explicit, str) or not explicit.strip()):
        raise ValueError("EOS identity, when declared, must be a nonempty stable string")
    provider = f"{type(eos).__module__}.{type(eos).__qualname__}"
    configuration = getattr(eos, "configuration", None)
    if configuration is None and provider == "h2physics.thermo.coolprop.CoolPropProperties":
        # CoolPropProperties does not expose a generic identity API. Its current
        # constructor configuration is reconstructed from these public fields.
        configuration = {
            "fluid": basis.fluid,
            "backend": getattr(eos, "backend", None),
            "version": getattr(eos, "version", None),
            "internal_energy_policy": getattr(eos, "internal_energy_policy", None),
            "quality_roundoff_tolerance": getattr(eos, "quality_roundoff_tolerance", None),
        }
    if not isinstance(configuration, Mapping) or not configuration:
        if explicit is None:
            raise ValueError(
                "EOS closure must declare a stable identity or nonempty configuration mapping"
            )
        config_digest = "identity-only"
    else:
        try:
            canonical = json.dumps(
                configuration, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            ).encode("ascii")
        except (TypeError, ValueError) as error:
            raise ValueError("EOS configuration must be stable JSON-compatible data") from error
        config_digest = hashlib.sha256(canonical).hexdigest()
    if explicit is None:
        explicit = "configuration-fingerprint"
    backend = getattr(eos, "backend", "provider-defined")
    version = getattr(eos, "version", "provider-defined")
    energy_policy = getattr(eos, "internal_energy_policy", "provider-defined")
    return (
        f"{provider}:{explicit}:{basis.fluid}:{basis.reference_id}:{basis.spin_composition}:"
        f"{backend}:{version}:{energy_policy}:sha256={config_digest}"
    )


def _require_gas_state(state: ThermoState, eos: CaloricGasEOS, label: str) -> ThermoState:
    if not isinstance(state, ThermoState):
        raise TypeError(f"{label} property closure must return ThermoState")
    eos.basis.require_compatible(state.basis)
    if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError(f"{label} reached unsupported phase {state.phase!r}; no phase fallback is applied")
    finite(state.speed_of_sound_m_s, f"{label} speed_of_sound_m_s", positive=True)
    return state


def _positive_cv(states: Sequence[ThermoState], label: str) -> np.ndarray:
    try:
        values = np.asarray([state.cv_j_kg_k for state in states], dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} requires positive finite EOS cv_j_kg_k") from error
    if not np.all(np.isfinite(values)) or np.any(values <= 0.):
        raise ValueError(f"{label} requires positive finite EOS cv_j_kg_k")
    return values


@dataclass(frozen=True, slots=True)
class CaloricPipeReservoirBoundary:
    """Fixed, explicitly evidenced ghost state representing a large reservoir.

    This boundary does not deplete or evolve a reservoir inventory. Its
    exchanged mass and total energy are retained in the pipe trace ledgers.
    """

    identifier: str
    state_owner_id: str
    state_evidence_id: str
    clock_id: str
    state: ThermoState
    velocity_m_s: float = 0.0

    def __post_init__(self) -> None:
        for name in ("identifier", "state_owner_id", "state_evidence_id", "clock_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare boundary {name}")
        if not isinstance(self.state, ThermoState):
            raise TypeError("A reservoir boundary requires a caller-owned ThermoState")
        if self.state.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Reservoir boundary must remain a homogeneous gas/supercritical state")
        object.__setattr__(self, "velocity_m_s", finite(self.velocity_m_s, "boundary velocity_m_s"))

    def require_compatible(self, *, eos: CaloricGasEOS, clock_id: str,
                           start_time_s: float, end_time_s: float) -> None:
        if self.clock_id != clock_id:
            raise ValueError("Boundary and pipe use different clock identities")
        if end_time_s <= start_time_s:
            raise ValueError("Boundary support window must have positive duration")
        eos.basis.require_compatible(self.state.basis)
        _require_gas_state(self.state, eos, "Reservoir boundary")
        replay = _require_gas_state(
            eos.state_rho_u(self.state.density_kg_m3, self.state.internal_energy_j_kg),
            eos, "Reservoir boundary rho-u replay",
        )
        if (not np.isclose(replay.pressure_pa, self.state.pressure_pa, rtol=2.e-6, atol=1.e-2)
                or not np.isclose(replay.temperature_k, self.state.temperature_k, rtol=2.e-6, atol=1.e-8)):
            raise ValueError("Reservoir boundary ThermoState does not replay through the selected rho-u EOS")


@dataclass(frozen=True, slots=True)
class CaloricPipeWaveTrace:
    """Immutable states, boundary fluxes, and global mass/energy ledgers."""

    time_s: np.ndarray = field(repr=False, compare=False)
    cell_center_m: np.ndarray = field(repr=False, compare=False)
    pressure_pa: np.ndarray = field(repr=False, compare=False)
    temperature_k: np.ndarray = field(repr=False, compare=False)
    density_kg_m3: np.ndarray = field(repr=False, compare=False)
    velocity_m_s: np.ndarray = field(repr=False, compare=False)
    internal_energy_j_kg: np.ndarray = field(repr=False, compare=False)
    face_mass_flow_kg_s: np.ndarray = field(repr=False, compare=False)
    face_energy_flow_w: np.ndarray = field(repr=False, compare=False)
    total_mass_kg: np.ndarray = field(repr=False, compare=False)
    total_energy_j: np.ndarray = field(repr=False, compare=False)
    cumulative_boundary_mass_in_kg: np.ndarray = field(repr=False, compare=False)
    cumulative_boundary_energy_in_j: np.ndarray = field(repr=False, compare=False)
    cumulative_wall_heat_in_j: np.ndarray = field(repr=False, compare=False)
    darcy_factor_mean_by_interval: np.ndarray = field(repr=False, compare=False)
    darcy_factor_max_by_interval: np.ndarray = field(repr=False, compare=False)
    internal_steps_by_interval: np.ndarray = field(repr=False, compare=False)
    mass_balance_residual_kg: np.ndarray = field(repr=False, compare=False)
    energy_balance_residual_j: np.ndarray = field(repr=False, compare=False)
    sound_speed_m_s: np.ndarray = field(repr=False, compare=False)
    eos_identity: str
    property_basis: PropertyBasis
    pipe_length_m: float
    internal_diameter_m: float
    area_m2: float
    maximum_cfl: float
    cfl_limit: float
    left_boundary_id: str | None = None
    right_boundary_id: str | None = None
    left_boundary_state_owner_id: str | None = None
    right_boundary_state_owner_id: str | None = None
    left_boundary_state_evidence_id: str | None = None
    right_boundary_state_evidence_id: str | None = None
    clock_id: str | None = None
    friction_law_id: str | None = None
    friction_state_owner_id: str | None = None
    friction_evidence_id: str | None = None
    friction_scheme: str | None = None
    wall_heat_boundary_id: str | None = None
    wall_heat_state_owner_id: str | None = None
    wall_heat_evidence_id: str | None = None
    wall_temperature_k: float | None = None
    heat_transfer_coefficient_w_m2_k: float | None = None
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer_token not in _PENDING_TRACE_ISSUERS:
            raise ValueError("Caloric pipe traces are issued only by a completed model run")
        _PENDING_TRACE_ISSUERS.remove(self._issuer_token)
        one_d_names = (
            "time_s", "cell_center_m", "total_mass_kg", "total_energy_j",
            "cumulative_boundary_mass_in_kg", "cumulative_boundary_energy_in_j",
            "cumulative_wall_heat_in_j", "mass_balance_residual_kg", "energy_balance_residual_j",
        )
        two_d_names = (
            "pressure_pa", "temperature_k", "density_kg_m3", "velocity_m_s",
            "internal_energy_j_kg", "face_mass_flow_kg_s", "face_energy_flow_w",
            "sound_speed_m_s",
        )
        for name in one_d_names:
            value = immutable_array(getattr(self, name), dtype=float, name=name)
            object.__setattr__(self, name, value)
        for name in two_d_names:
            value = immutable_array(getattr(self, name), dtype=float, name=name)
            object.__setattr__(self, name, value)
        time, centers = self.time_s, self.cell_center_m
        if (time.ndim != 1 or len(time) < 2 or time[0] != 0.
                or not np.all(np.isfinite(time)) or np.any(np.diff(time) <= 0.)):
            raise ValueError("Trace time samples must start at zero and increase strictly")
        if centers.ndim != 1 or len(centers) < 2 or not np.all(np.isfinite(centers)):
            raise ValueError("Trace cell centers must contain at least two finite values")
        n_time, n_cell = len(time), len(centers)
        for name in two_d_names:
            value = getattr(self, name)
            expected = (n_time, n_cell + 1) if name.startswith("face_") else (n_time, n_cell)
            if value.shape != expected or not np.all(np.isfinite(value)):
                raise ValueError(f"Trace {name} has invalid dimensions or nonfinite values")
        for name in ("darcy_factor_mean_by_interval", "darcy_factor_max_by_interval"):
            value = immutable_array(getattr(self, name), dtype=float, name=name)
            object.__setattr__(self, name, value)
            if value.shape != (n_time - 1, n_cell) or not np.all(np.isfinite(value)) or np.any(value < 0.):
                raise ValueError(f"Trace {name} has invalid dimensions or values")
        steps = immutable_array(self.internal_steps_by_interval, dtype=np.int64,
                                name="internal_steps_by_interval")
        object.__setattr__(self, "internal_steps_by_interval", steps)
        if steps.shape != (n_time - 1,) or np.any(steps < 1):
            raise ValueError("Trace internal-step counts must match output intervals")
        for name in one_d_names[2:]:
            value = getattr(self, name)
            if value.shape != (n_time,) or not np.all(np.isfinite(value)):
                raise ValueError(f"Trace {name} has invalid dimensions or nonfinite values")
        if any(np.any(getattr(self, name) <= 0.) for name in
               ("pressure_pa", "temperature_k", "density_kg_m3", "sound_speed_m_s", "total_mass_kg")):
            raise ValueError("Caloric trace thermodynamic states and total mass must be positive")
        if not isinstance(self.eos_identity, str) or not self.eos_identity.strip():
            raise ValueError("Trace must retain the property closure identity")
        if not isinstance(self.property_basis, PropertyBasis):
            raise TypeError("Trace must retain a PropertyBasis")
        length = finite(self.pipe_length_m, "pipe_length_m", positive=True)
        diameter = finite(self.internal_diameter_m, "internal_diameter_m", positive=True)
        area = finite(self.area_m2, "area_m2", positive=True)
        if not np.isclose(area, np.pi * diameter**2 / 4., rtol=1.e-12, atol=1.e-15):
            raise ValueError("Trace area does not match its retained internal diameter")
        if centers[0] <= 0. or centers[-1] >= length or np.any(np.diff(centers) <= 0.):
            raise ValueError("Trace cell centers do not lie in order inside the retained pipe length")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Trace must retain its caller-declared absolute clock identity")
        cfl, limit = finite(self.maximum_cfl, "maximum_cfl"), finite(self.cfl_limit, "cfl_limit", positive=True)
        if cfl < 0. or cfl > limit + 1.e-12 or limit > 0.5:
            raise ValueError("Trace violates the declared explicit Rusanov CFL limit")
        for identifier, owner_id, evidence_id in (
            (self.left_boundary_id, self.left_boundary_state_owner_id,
             self.left_boundary_state_evidence_id),
            (self.right_boundary_id, self.right_boundary_state_owner_id,
             self.right_boundary_state_evidence_id),
        ):
            if identifier is None:
                if owner_id is not None or evidence_id is not None:
                    raise ValueError("Closed boundary cannot retain partial state provenance")
            elif (not isinstance(identifier, str) or not identifier.strip()
                  or not isinstance(owner_id, str) or not owner_id.strip()
                  or not isinstance(evidence_id, str) or not evidence_id.strip()):
                raise ValueError("Open boundary must retain owner and state evidence IDs")
        friction_fields = (self.friction_law_id, self.friction_state_owner_id,
                           self.friction_evidence_id, self.friction_scheme)
        if all(value is None for value in friction_fields):
            if np.any(self.darcy_factor_mean_by_interval) or np.any(self.darcy_factor_max_by_interval):
                raise ValueError("Trace without a friction law cannot report applied factors")
        elif any(not isinstance(value, str) or not value.strip() for value in friction_fields):
            raise ValueError("Friction trace must retain complete provider and scheme identity")
        wall_fields = (self.wall_heat_boundary_id, self.wall_heat_state_owner_id,
                       self.wall_heat_evidence_id, self.wall_temperature_k,
                       self.heat_transfer_coefficient_w_m2_k)
        if all(value is None for value in wall_fields):
            if np.any(self.cumulative_wall_heat_in_j):
                raise ValueError("Trace without a wall boundary cannot report wall heat")
        else:
            for value in wall_fields[:3]:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("Wall heat trace must retain complete boundary provenance")
            finite(self.wall_temperature_k, "wall_temperature_k", positive=True)
            coefficient = finite(self.heat_transfer_coefficient_w_m2_k,
                                 "heat_transfer_coefficient_w_m2_k")
            if coefficient < 0.:
                raise ValueError("Trace wall heat coefficient cannot be negative")


@dataclass(frozen=True, slots=True)
class CaloricPipeWaveModel:
    """First-order finite-volume caloric gas pipe with a pluggable EOS.

    The model uses uniform-area, horizontal, inviscid one-dimensional Euler
    equations and a local Lax-Friedrichs/Rusanov flux. Closed ends are
    reflective. Optional reservoir boundaries are caller-supplied fixed
    ghost states and are not finite inventories. Optional Darcy friction and
    fixed-wall heat sources are caller-evidenced; gravity, junctions and valves
    remain outside this level.
    """

    length_m: float
    internal_diameter_m: float
    cell_count: int
    eos: CaloricGasEOS = field(repr=False, compare=False)
    maximum_cfl: float = 0.35
    maximum_internal_steps: int = 1_000_000

    def __post_init__(self) -> None:
        finite(self.length_m, "length_m", positive=True)
        finite(self.internal_diameter_m, "internal_diameter_m", positive=True)
        if isinstance(self.cell_count, bool) or not isinstance(self.cell_count, int) or self.cell_count < 2:
            raise ValueError("cell_count must be an integer of at least two")
        cfl = finite(self.maximum_cfl, "maximum_cfl", positive=True)
        if cfl > 0.5:
            raise ValueError("maximum_cfl must not exceed 0.5 for this explicit solver")
        if (isinstance(self.maximum_internal_steps, bool)
                or not isinstance(self.maximum_internal_steps, int)
                or self.maximum_internal_steps < 1):
            raise ValueError("maximum_internal_steps must be a positive integer")
        for method in ("state_pt", "state_rho_u"):
            if not callable(getattr(self.eos, method, None)):
                raise TypeError(f"EOS closure must implement {method}(...)")
        if not isinstance(getattr(self.eos, "basis", None), PropertyBasis):
            raise TypeError("EOS closure must expose a PropertyBasis")
        _eos_identity(self.eos)

    @property
    def eos_identity(self) -> str:
        return _eos_identity(self.eos)

    @property
    def area_m2(self) -> float:
        return float(np.pi * self.internal_diameter_m**2 / 4.)

    @property
    def cell_length_m(self) -> float:
        return self.length_m / self.cell_count

    @staticmethod
    def _primitive(conserved: np.ndarray, eos: CaloricGasEOS) -> tuple[np.ndarray, list[ThermoState]]:
        rho, momentum, total_energy_density = conserved
        if np.any(~np.isfinite(conserved)) or np.any(rho <= 0.):
            raise FloatingPointError("Caloric pipe update produced nonfinite or nonpositive density")
        velocity = momentum / rho
        internal_energy = total_energy_density / rho - 0.5 * velocity**2
        if np.any(~np.isfinite(internal_energy)):
            raise FloatingPointError("Caloric pipe update produced nonfinite internal energy")
        states = [_require_gas_state(eos.state_rho_u(float(r), float(u)), eos, "Pipe cell")
                  for r, u in zip(rho, internal_energy, strict=True)]
        if any(not np.isclose(state.density_kg_m3, float(rho[i]), rtol=2.e-6, atol=1.e-10)
               for i, state in enumerate(states)):
            raise ValueError("Property closure changed density in its rho-u state call")
        if any(not np.isclose(state.internal_energy_j_kg, float(internal_energy[i]),
                              rtol=2.e-6, atol=1.e-2)
               for i, state in enumerate(states)):
            raise ValueError("Property closure changed internal energy in its rho-u state call")
        pressure = np.asarray([state.pressure_pa for state in states])
        sound = np.asarray([state.speed_of_sound_m_s for state in states])
        if not np.all(np.isfinite(pressure)) or np.any(pressure <= 0.):
            raise FloatingPointError("Caloric pipe EOS returned invalid pressure")
        return np.vstack((rho, velocity, internal_energy, pressure, sound)), states

    @staticmethod
    def _flux(conserved: np.ndarray, primitive: np.ndarray) -> np.ndarray:
        rho, velocity, internal_energy, pressure, _sound = primitive
        total_energy = rho * (internal_energy + 0.5 * velocity**2)
        return np.vstack((rho * velocity,
                          rho * velocity**2 + pressure,
                          velocity * (total_energy + pressure)))

    @staticmethod
    def _rusanov(left: np.ndarray, right: np.ndarray,
                 primitive_left: np.ndarray, primitive_right: np.ndarray) -> np.ndarray:
        speed = np.maximum(np.abs(primitive_left[1]) + primitive_left[4],
                           np.abs(primitive_right[1]) + primitive_right[4])
        return 0.5 * (CaloricPipeWaveModel._flux(left, primitive_left)
                      + CaloricPipeWaveModel._flux(right, primitive_right)
                      - speed[None, :] * (right - left))

    @staticmethod
    def _boundary_conserved(state: ThermoState, velocity: float) -> np.ndarray:
        rho = state.density_kg_m3
        total = rho * (state.internal_energy_j_kg + 0.5 * velocity**2)
        return np.asarray((rho, rho * velocity, total), dtype=float)

    def simulate(self, *, initial_pressure_pa: Sequence[float],
                 initial_temperature_k: Sequence[float], initial_velocity_m_s: Sequence[float],
                 time_samples_s: Sequence[float], clock_id: str,
                 left_reservoir: CaloricPipeReservoirBoundary | None = None,
                 right_reservoir: CaloricPipeReservoirBoundary | None = None,
                 darcy_friction_law: CaloricDarcyFrictionLaw | None = None,
                 wall_heat_boundary: CaloricPipeWallHeatBoundary | None = None,
                 ) -> CaloricPipeWaveTrace:
        """Advance cell-average conserved states to requested absolute times.

        The explicit time step obeys ``dt <= CFL*dx/max(|u|+a)``. Boundary
        fluxes are integrated using the exact face flux used by the finite-
        volume update, producing signed mass and total-energy closure ledgers.
        Optional friction uses the Darcy convention and an exact frozen-factor
        momentum relaxation; it does not remove total energy. Wall heat is
        positive into the gas and is included exactly in the energy ledger.
        No positivity clipping or silent EOS/phase substitution is performed.
        """
        for side, boundary in (("left", left_reservoir), ("right", right_reservoir)):
            if boundary is not None and type(boundary) is not CaloricPipeReservoirBoundary:
                raise TypeError(f"{side} boundary must be CaloricPipeReservoirBoundary")
        if darcy_friction_law is not None:
            for name in ("identity", "state_owner_id", "evidence_id", "clock_id"):
                if not isinstance(getattr(darcy_friction_law, name, None), str) or not getattr(darcy_friction_law, name).strip():
                    raise ValueError(f"Friction law must declare {name}")
            if not callable(getattr(darcy_friction_law, "darcy_factor", None)):
                raise TypeError("Friction law must implement darcy_factor(state, velocity, diameter)")
        if wall_heat_boundary is not None and type(wall_heat_boundary) is not CaloricPipeWallHeatBoundary:
            raise TypeError("wall_heat_boundary must be CaloricPipeWallHeatBoundary")
        try:
            pressure0 = np.asarray(tuple(initial_pressure_pa), dtype=float)
            temperature0 = np.asarray(tuple(initial_temperature_k), dtype=float)
            velocity0 = np.asarray(tuple(initial_velocity_m_s), dtype=float)
            times = np.asarray(tuple(time_samples_s), dtype=float)
        except (TypeError, ValueError) as error:
            raise TypeError("Initial fields and time samples must be numeric sequences") from error
        shape = (self.cell_count,)
        if any(value.shape != shape for value in (pressure0, temperature0, velocity0)):
            raise ValueError("Initial pressure, temperature and velocity require one value per pipe cell")
        if (not np.all(np.isfinite(pressure0)) or np.any(pressure0 <= 0.)
                or not np.all(np.isfinite(temperature0)) or np.any(temperature0 <= 0.)
                or not np.all(np.isfinite(velocity0))):
            raise ValueError("Initial primitive fields must be finite with positive pressure and temperature")
        if (times.ndim != 1 or len(times) < 2 or times[0] != 0.
                or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0.)):
            raise ValueError("time_samples_s must start at zero and increase strictly")
        has_boundary = left_reservoir is not None or right_reservoir is not None
        if not isinstance(clock_id, str) or not clock_id.strip():
            raise ValueError("Every run requires a caller-declared absolute clock identity")
        if darcy_friction_law is not None and darcy_friction_law.clock_id != clock_id:
            raise ValueError("Friction law and pipe use different clock identities")
        friction_provenance = (None if darcy_friction_law is None else tuple(
            getattr(darcy_friction_law, name) for name in
            ("identity", "state_owner_id", "evidence_id", "clock_id")
        ))
        if wall_heat_boundary is not None and wall_heat_boundary.clock_id != clock_id:
            raise ValueError("Wall heat boundary and pipe use different clock identities")
        for boundary in (left_reservoir, right_reservoir):
            if boundary is not None:
                boundary.require_compatible(eos=self.eos, clock_id=clock_id,
                                            start_time_s=float(times[0]), end_time_s=float(times[-1]))
        states0 = [_require_gas_state(self.eos.state_pt(float(p), float(t)), self.eos, "Initial cell")
                   for p, t in zip(pressure0, temperature0, strict=True)]
        density0 = np.asarray([state.density_kg_m3 for state in states0])
        internal0 = np.asarray([state.internal_energy_j_kg for state in states0])
        conserved = np.vstack((density0, density0 * velocity0,
                               density0 * (internal0 + 0.5 * velocity0**2)))
        dx, area = self.cell_length_m, self.area_m2
        centers = (np.arange(self.cell_count, dtype=float) + 0.5) * dx
        primitive, states = self._primitive(conserved, self.eos)
        initial_mass = float(np.sum(conserved[0]) * area * dx)
        initial_energy = float(np.sum(conserved[2]) * area * dx)
        cumulative_mass_in = cumulative_energy_in = 0.0
        cumulative_wall_heat = 0.0
        max_observed_cfl = 0.0
        out = {name: [] for name in (
            "pressure", "temperature", "density", "velocity", "internal_energy", "sound",
        )}
        face_mass_samples, face_energy_samples = [], []
        total_mass_samples, total_energy_samples = [], []
        mass_in_samples, energy_in_samples = [], []
        mass_residual_samples, energy_residual_samples = [], []
        wall_heat_samples = []
        factor_mean_samples, factor_max_samples, step_count_samples = [], [], []
        interval_factor_integral = np.zeros(self.cell_count)
        interval_factor_max = np.zeros(self.cell_count)
        interval_steps = 0
        current_time = 0.0
        elapsed_steps = 0

        def save(sample_time: float, flux: np.ndarray) -> None:
            nonlocal cumulative_mass_in, cumulative_energy_in
            for key, index, attribute in (
                ("pressure", 3, "pressure_pa"), ("temperature", None, "temperature_k"),
                ("density", 0, "density_kg_m3"), ("velocity", 1, None),
                ("internal_energy", 2, "internal_energy_j_kg"), ("sound", 4, "speed_of_sound_m_s"),
            ):
                if key == "temperature":
                    out[key].append(np.asarray([state.temperature_k for state in states]))
                elif key == "velocity":
                    out[key].append(primitive[1].copy())
                elif key in {"pressure", "sound"}:
                    out[key].append(primitive[index].copy())
                elif key == "density":
                    out[key].append(conserved[0].copy())
                else:
                    out[key].append(primitive[index].copy())
            face_mass_samples.append(flux[0] * area)
            face_energy_samples.append(flux[2] * area)
            mass = float(np.sum(conserved[0]) * area * dx)
            energy = float(np.sum(conserved[2]) * area * dx)
            total_mass_samples.append(mass)
            total_energy_samples.append(energy)
            mass_in_samples.append(cumulative_mass_in)
            energy_in_samples.append(cumulative_energy_in)
            wall_heat_samples.append(cumulative_wall_heat)
            mass_residual_samples.append(mass - initial_mass - cumulative_mass_in)
            energy_residual_samples.append(energy - initial_energy - cumulative_energy_in - cumulative_wall_heat)

        def calculate_faces() -> np.ndarray:
            left = np.empty((3, self.cell_count + 1), dtype=float)
            right = np.empty_like(left)
            left[:, 1:] = conserved
            right[:, :-1] = conserved
            left[:, 0] = (self._boundary_conserved(left_reservoir.state, left_reservoir.velocity_m_s)
                          if left_reservoir is not None else
                          np.asarray((conserved[0, 0], -conserved[1, 0], conserved[2, 0])))
            right[:, -1] = (self._boundary_conserved(right_reservoir.state, right_reservoir.velocity_m_s)
                            if right_reservoir is not None else
                            np.asarray((conserved[0, -1], -conserved[1, -1], conserved[2, -1])))
            pleft, _ = self._primitive(left, self.eos)
            pright, _ = self._primitive(right, self.eos)
            return self._rusanov(left, right, pleft, pright)

        flux = calculate_faces()
        save(0., flux)
        for sample_time in times[1:]:
            interval_factor_integral.fill(0.)
            interval_factor_max.fill(0.)
            interval_steps = 0
            while current_time < float(sample_time):
                primitive, states = self._primitive(conserved, self.eos)
                maximum_speed = float(np.max(np.abs(primitive[1]) + primitive[4]))
                for boundary in (left_reservoir, right_reservoir):
                    if boundary is not None:
                        boundary_sound = finite(
                            boundary.state.speed_of_sound_m_s,
                            "reservoir boundary sound speed", positive=True,
                        )
                        maximum_speed = max(
                            maximum_speed, abs(boundary.velocity_m_s) + boundary_sound,
                        )
                dt = min(self.maximum_cfl * dx / maximum_speed, float(sample_time) - current_time)
                if wall_heat_boundary is not None and wall_heat_boundary.heat_transfer_coefficient_w_m2_k > 0.:
                    cv = _positive_cv(states, "Wall heat transfer")
                    thermal_rate = (4. * wall_heat_boundary.heat_transfer_coefficient_w_m2_k
                                    / self.internal_diameter_m / (conserved[0] * cv))
                    dt = min(dt, 0.5 / float(np.max(thermal_rate)))
                if not np.isfinite(dt) or dt <= 0.:
                    raise FloatingPointError("Caloric pipe CFL produced a nonpositive time step")
                observed_cfl = dt * maximum_speed / dx
                if observed_cfl > self.maximum_cfl + 1.e-12:
                    raise RuntimeError("Caloric pipe internal time step exceeded its CFL limit")
                max_observed_cfl = max(max_observed_cfl, observed_cfl)
                flux = calculate_faces()
                next_conserved = conserved - (dt / dx) * (flux[:, 1:] - flux[:, :-1])
                if not np.all(np.isfinite(next_conserved)) or np.any(next_conserved[0] <= 0.):
                    raise FloatingPointError("Caloric pipe finite-volume update produced invalid conserved states")
                left_into_pipe = area * flux[0, 0]
                right_into_pipe = -area * flux[0, -1]
                left_energy_into_pipe = area * flux[2, 0]
                right_energy_into_pipe = -area * flux[2, -1]
                cumulative_mass_in += dt * (left_into_pipe + right_into_pipe)
                cumulative_energy_in += dt * (left_energy_into_pipe + right_energy_into_pipe)
                if darcy_friction_law is not None:
                    primitive_next, states_next = self._primitive(next_conserved, self.eos)
                    factors = np.asarray([
                        finite(darcy_friction_law.darcy_factor(state, float(velocity), self.internal_diameter_m),
                               "Darcy friction factor")
                        for state, velocity in zip(states_next, primitive_next[1], strict=True)
                    ])
                    if np.any(factors < 0.):
                        raise ValueError("Darcy friction factors must be nonnegative")
                    velocity = primitive_next[1]
                    relaxed_velocity = velocity / (1. + factors * np.abs(velocity) * dt
                                                     / (2. * self.internal_diameter_m))
                    next_conserved[1] = next_conserved[0] * relaxed_velocity
                    interval_factor_integral += factors * dt
                    interval_factor_max = np.maximum(interval_factor_max, factors)
                if wall_heat_boundary is not None:
                    primitive_next, states_next = self._primitive(next_conserved, self.eos)
                    if wall_heat_boundary.heat_transfer_coefficient_w_m2_k > 0.:
                        cv_next = _positive_cv(states_next, "Wall heat transfer")
                        proposed_thermal_rate = (
                            4. * wall_heat_boundary.heat_transfer_coefficient_w_m2_k
                            / self.internal_diameter_m / (next_conserved[0] * cv_next)
                        )
                        if dt * float(np.max(proposed_thermal_rate)) > 0.5 + 1.e-12:
                            raise RuntimeError(
                                "Proposed source step violates the fixed-wall heat stability bound"
                            )
                    heat_rate_density = (4. * wall_heat_boundary.heat_transfer_coefficient_w_m2_k
                                         / self.internal_diameter_m
                                         * (wall_heat_boundary.wall_temperature_k
                                            - np.asarray([state.temperature_k for state in states_next])))
                    next_conserved[2] += dt * heat_rate_density
                    cumulative_wall_heat += dt * area * dx * float(np.sum(heat_rate_density))
                conserved = next_conserved
                primitive, states = self._primitive(conserved, self.eos)
                current_time = min(float(sample_time), current_time + dt)
                elapsed_steps += 1
                interval_steps += 1
                if elapsed_steps > self.maximum_internal_steps:
                    raise RuntimeError("maximum_internal_steps reached before requested output times")
            flux = calculate_faces()
            duration = float(sample_time) - float(times[len(step_count_samples)])
            factor_mean_samples.append(interval_factor_integral / max(duration, np.finfo(float).tiny))
            factor_max_samples.append(interval_factor_max.copy())
            step_count_samples.append(interval_steps)
            save(float(sample_time), flux)
        if darcy_friction_law is not None and friction_provenance != tuple(
            getattr(darcy_friction_law, name) for name in
            ("identity", "state_owner_id", "evidence_id", "clock_id")
        ):
            raise ValueError("Friction provider changed its declared provenance during the run")
        return _issue_caloric_trace(
            time_s=times, cell_center_m=centers,
            pressure_pa=np.asarray(out["pressure"]), temperature_k=np.asarray(out["temperature"]),
            density_kg_m3=np.asarray(out["density"]), velocity_m_s=np.asarray(out["velocity"]),
            internal_energy_j_kg=np.asarray(out["internal_energy"]),
            face_mass_flow_kg_s=np.asarray(face_mass_samples),
            face_energy_flow_w=np.asarray(face_energy_samples),
            total_mass_kg=np.asarray(total_mass_samples), total_energy_j=np.asarray(total_energy_samples),
            cumulative_boundary_mass_in_kg=np.asarray(mass_in_samples),
            cumulative_boundary_energy_in_j=np.asarray(energy_in_samples),
            cumulative_wall_heat_in_j=np.asarray(wall_heat_samples),
            darcy_factor_mean_by_interval=np.asarray(factor_mean_samples),
            darcy_factor_max_by_interval=np.asarray(factor_max_samples),
            internal_steps_by_interval=np.asarray(step_count_samples, dtype=np.int64),
            mass_balance_residual_kg=np.asarray(mass_residual_samples),
            energy_balance_residual_j=np.asarray(energy_residual_samples),
            sound_speed_m_s=np.asarray(out["sound"]), eos_identity=self.eos_identity,
            property_basis=self.eos.basis, pipe_length_m=self.length_m,
            internal_diameter_m=self.internal_diameter_m, area_m2=area,
            maximum_cfl=max_observed_cfl, cfl_limit=self.maximum_cfl,
            left_boundary_id=None if left_reservoir is None else left_reservoir.identifier,
            right_boundary_id=None if right_reservoir is None else right_reservoir.identifier,
            left_boundary_state_owner_id=(None if left_reservoir is None
                                          else left_reservoir.state_owner_id),
            right_boundary_state_owner_id=(None if right_reservoir is None
                                           else right_reservoir.state_owner_id),
            left_boundary_state_evidence_id=(None if left_reservoir is None
                                             else left_reservoir.state_evidence_id),
            right_boundary_state_evidence_id=(None if right_reservoir is None
                                              else right_reservoir.state_evidence_id),
            clock_id=clock_id,
            friction_law_id=None if darcy_friction_law is None else darcy_friction_law.identity,
            friction_state_owner_id=None if darcy_friction_law is None else darcy_friction_law.state_owner_id,
            friction_evidence_id=None if darcy_friction_law is None else darcy_friction_law.evidence_id,
            friction_scheme=None if darcy_friction_law is None else "Darcy-Weisbach; frozen-factor exact momentum relaxation",
            wall_heat_boundary_id=None if wall_heat_boundary is None else wall_heat_boundary.identifier,
            wall_heat_state_owner_id=None if wall_heat_boundary is None else wall_heat_boundary.state_owner_id,
            wall_heat_evidence_id=None if wall_heat_boundary is None else wall_heat_boundary.state_evidence_id,
            wall_temperature_k=None if wall_heat_boundary is None else wall_heat_boundary.wall_temperature_k,
            heat_transfer_coefficient_w_m2_k=(None if wall_heat_boundary is None else
                                               wall_heat_boundary.heat_transfer_coefficient_w_m2_k),
        )


__all__ = ["CaloricGasEOS", "CaloricDarcyFrictionLaw", "UniformDarcyFriction",
           "CaloricPipeWallHeatBoundary", "CaloricPipeReservoirBoundary",
           "CaloricPipeWaveTrace", "CaloricPipeWaveModel"]
