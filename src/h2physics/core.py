"""Physical meanings shared by native model providers. All quantities use SI units."""

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


def immutable_array(value, *, dtype=None, name: str = "array") -> np.ndarray:
    """Return an array backed by immutable bytes.

    ``setflags(write=False)`` alone is reversible when the array owns its data.
    This helper copies fixed-width boolean and numeric data into a ``bytes``
    buffer so public receipts cannot be modified by re-enabling NumPy's write
    flag. Object, text, datetime and structured arrays are rejected because
    they are outside this numeric snapshot contract.
    """
    try:
        array = np.asarray(value, dtype=dtype)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a representable array") from exc
    if array.dtype.kind not in "biufc":
        raise TypeError(f"{name} must use a fixed-width numeric or boolean dtype")
    shape = array.shape
    contiguous = np.ascontiguousarray(array)
    frozen = np.frombuffer(contiguous.tobytes(), dtype=contiguous.dtype)
    return frozen.reshape(shape)


def finite(value: float, name: str, *, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite and numeric")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    return float(value)


def _contains_boolean(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return True
    if isinstance(value, np.ndarray):
        if value.dtype.kind == "b":
            return True
        return value.dtype.kind == "O" and any(
            _contains_boolean(item) for item in value.flat
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_boolean(item) for item in value)
    return False


def _real_numeric_array(value, name: str) -> np.ndarray:
    if _contains_boolean(value):
        raise ValueError(f"{name} must contain real numeric values, not booleans")
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"{name} must contain real numeric values")
    return np.asarray(raw, dtype=float)


def partial_pressure_pa(total_absolute_pressure_pa, mole_fraction):
    """Return ideal-mixture Dalton partial pressure in Pa.

    ``total_absolute_pressure_pa`` must be absolute pressure, never gauge or
    differential pressure. This relation does not calculate fugacity or replace
    an equation-of-state chemical-potential model. Inputs broadcast using NumPy;
    scalar inputs return a float and array inputs return a read-only array.
    """
    try:
        pressure = _real_numeric_array(total_absolute_pressure_pa, "Absolute pressure")
        fraction = _real_numeric_array(mole_fraction, "Mole fraction")
        pressure, fraction = np.broadcast_arrays(pressure, fraction)
    except (TypeError, ValueError) as exc:
        raise ValueError("Pressure and mole fraction must be broadcast-compatible numeric values") from exc
    if (not np.all(np.isfinite(pressure)) or np.any(pressure <= 0)
            or not np.all(np.isfinite(fraction))
            or np.any((fraction < 0) | (fraction > 1))):
        raise ValueError("Absolute pressure must be positive and mole fraction must lie in [0, 1]")
    result = pressure * fraction
    if result.ndim == 0:
        return float(result)
    return immutable_array(result, name="partial pressure")


class Origin(StrEnum):
    MEASURED = "measured"
    PREDICTED = "predicted"
    RECONSTRUCTED = "reconstructed"
    SYNTHETIC = "synthetic"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class PropertyBasis:
    fluid: str
    reference_id: str
    spin_composition: str = "unspecified"

    def __post_init__(self):
        if (not isinstance(self.fluid, str) or not self.fluid.strip()
                or not isinstance(self.reference_id, str) or not self.reference_id.strip()
                or not isinstance(self.spin_composition, str) or not self.spin_composition.strip()):
            raise ValueError("Fluid and energy-reference identity must be explicit")

    def require_compatible(self, other: "PropertyBasis") -> None:
        if self != other:
            raise ValueError("Property, spin-composition or energy-reference bases differ")


@dataclass(frozen=True, slots=True)
class ThermoState:
    basis: PropertyBasis
    pressure_pa: float
    temperature_k: float
    density_kg_m3: float
    enthalpy_j_kg: float
    internal_energy_j_kg: float
    entropy_j_kg_k: float
    phase: str
    cp_j_kg_k: float | None = None
    cv_j_kg_k: float | None = None
    viscosity_pa_s: float | None = None
    conductivity_w_m_k: float | None = None
    speed_of_sound_m_s: float | None = None
    vapor_mass_fraction: float | None = None
    raw_vapor_mass_fraction: float | None = None

    def __post_init__(self):
        for name in ("pressure_pa", "temperature_k", "density_kg_m3"):
            finite(getattr(self, name), name, positive=True)
        for name in ("enthalpy_j_kg", "internal_energy_j_kg", "entropy_j_kg_k"):
            finite(getattr(self, name), name)
        for name in ("cp_j_kg_k", "cv_j_kg_k", "viscosity_pa_s",
                     "conductivity_w_m_k", "speed_of_sound_m_s"):
            value = getattr(self, name)
            if value is not None:
                finite(value, name, positive=True)
        if self.vapor_mass_fraction is not None:
            finite(self.vapor_mass_fraction, "vapor_mass_fraction")
            if not 0 <= self.vapor_mass_fraction <= 1:
                raise ValueError("Vapor mass fraction must lie in [0, 1]")
        if self.raw_vapor_mass_fraction is not None:
            finite(self.raw_vapor_mass_fraction, "raw_vapor_mass_fraction")
            if self.vapor_mass_fraction is None:
                raise ValueError("A raw quality diagnostic requires a resolved vapor fraction")

    @property
    def enthalpy_identity_residual_j_kg(self) -> float:
        return self.enthalpy_j_kg - self.internal_energy_j_kg - self.pressure_pa / self.density_kg_m3

    @property
    def heat_capacity_ratio(self) -> float | None:
        """Return cp/cv when both caloric derivatives belong to this state.

        This is an isentropic ideal-gas closure only when the provider's physics
        supports that interpretation. The property reports the ratio; it does not
        assert ideal-gas behavior or authorize its use in a discharge correlation.
        """
        if self.cp_j_kg_k is None or self.cv_j_kg_k is None:
            return None
        return self.cp_j_kg_k / self.cv_j_kg_k


@runtime_checkable
class PropertyProvider(Protocol):
    @property
    def basis(self) -> PropertyBasis: ...
    def state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState: ...
    def state_ph(self, pressure_pa: float, enthalpy_j_kg: float) -> ThermoState: ...
    def state_ps(self, pressure_pa: float, entropy_j_kg_k: float) -> ThermoState: ...


@dataclass(frozen=True, slots=True)
class Stream:
    component_id: str
    port_id: str
    mass_flow_kg_s: float
    state: ThermoState

    def __post_init__(self):
        finite(self.mass_flow_kg_s, "mass_flow_kg_s")
        if (not isinstance(self.component_id, str) or not self.component_id.strip()
                or not isinstance(self.port_id, str) or not self.port_id.strip()):
            raise ValueError("A stream needs component and port identities")

    @property
    def enthalpy_flow_w(self) -> float:
        return self.mass_flow_kg_s * self.state.enthalpy_j_kg


@dataclass(frozen=True, slots=True)
class TimeSeries:
    time_s: NDArray[np.float64]
    values: NDArray[np.float64]
    channels: tuple[str, ...]
    units: tuple[str, ...]
    valid: NDArray[np.bool_]
    clock_id: str
    origin: Origin
    source_id: str
    quantities: tuple[str, ...]
    basis_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("channels", "units", "quantities", "basis_ids"):
            value = getattr(self, name)
            if isinstance(value, (str, bytes)) or not isinstance(value, (tuple, list)):
                raise TypeError(f"{name} must be an explicit sequence of strings")
        channels, units, quantities = tuple(self.channels), tuple(self.units), tuple(self.quantities)
        time = np.array(self.time_s, dtype=np.float64, copy=True)
        values = np.array(self.values, dtype=np.float64, copy=True)
        valid = np.array(self.valid, dtype=bool, copy=True)
        basis_ids = tuple(self.basis_ids) if self.basis_ids else ("",)*len(channels)
        if time.ndim != 1 or not np.all(np.isfinite(time)) or np.any(np.diff(time) <= 0):
            raise ValueError("Time must be a finite, strictly increasing one-dimensional clock")
        expected = (time.size, len(channels))
        if values.shape != expected or valid.shape != expected:
            raise ValueError("Observation values and validity must match time and channels")
        if (not channels or any(not isinstance(item, str) or not item.strip() for item in channels)
                or len(set(channels)) != len(channels)):
            raise ValueError("Channels must be unique nonempty strings")
        if (len(units) != len(channels)
                or any(not isinstance(item, str) or not item.strip() for item in units)):
            raise ValueError("Channels must be unique and each must have a declared unit")
        if (len(quantities) != len(channels)
                or any(not isinstance(q, str) or not q.strip() for q in quantities)):
            raise ValueError("Each channel must retain its physical quantity")
        if (len(basis_ids) != len(channels)
                or any(not isinstance(basis, str) for basis in basis_ids)):
            raise ValueError("Channel reference/measurement bases must match their columns")
        if any(quantity in {"normalized_pressure", "specific_amount", "reference_specific_volume", "reported_pressure"} and not basis.strip()
               for quantity, basis in zip(quantities, basis_ids, strict=True)):
            raise ValueError("This channel quantity requires an explicit reference/measurement basis")
        if (not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not isinstance(self.source_id, str) or not self.source_id.strip()):
            raise ValueError("Clock, source and unit identities cannot be empty")
        if np.any(valid & ~np.isfinite(values)):
            raise ValueError("Nonfinite observations cannot be marked valid")
        time = immutable_array(time, name="time_s")
        values = immutable_array(values, name="values")
        valid = immutable_array(valid, name="valid")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "valid", valid)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "quantities", quantities)
        object.__setattr__(self, "origin", Origin(self.origin))
        object.__setattr__(self, "basis_ids", basis_ids)

    def channel_values(self, name: str, *, quantity: str, basis_id: str | None = None):
        index = self.channels.index(name)
        if self.quantities[index] != quantity:
            raise ValueError("The channel's physical quantity does not match the requested use")
        if quantity in {"normalized_pressure", "specific_amount", "reference_specific_volume", "reported_pressure"} and basis_id is None:
            raise ValueError("Declare the requested channel reference/measurement basis")
        if basis_id is not None and basis_id != self.basis_ids[index]:
            raise ValueError("The channel reference/measurement basis differs")
        return self.values[:, index], self.valid[:, index]


@dataclass(frozen=True, slots=True)
class MassPartition:
    total_kg_s: float
    gas_kg_s: float
    airborne_liquid_kg_s: float
    ground_liquid_kg_s: float
    tolerance_kg_s: float = 1e-10

    def __post_init__(self):
        for name in ("total_kg_s", "gas_kg_s", "airborne_liquid_kg_s", "ground_liquid_kg_s"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError("Phase transfer rates cannot be negative")
        finite(self.tolerance_kg_s, "tolerance_kg_s", positive=True)
        if abs(self.residual_kg_s) > self.tolerance_kg_s:
            raise ValueError("The source phase partition does not conserve mass")

    @property
    def residual_kg_s(self) -> float:
        return self.total_kg_s - self.gas_kg_s - self.airborne_liquid_kg_s - self.ground_liquid_kg_s
