"""Bounded immutable lookup tables for a single-phase isothermal EOS.

Tables support bounded repeated density/temperature property queries. Actual
query speed must be measured. Construction samples a caller-selected source EOS;
construction alone is not an accuracy qualification. Compare the table with
its source on held-out states before relying on it for a particular envelope.
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from ..core import finite, immutable_array
from .isothermal_eos import IsothermalSinglePhaseEOS

_INTERPOLATION_MODES = frozenset(("linear", "log_linear"))
_SOUND_SPEED_MODES = frozenset(("sampled", "pressure_derivative"))


def _axis(values: Sequence[float], name: str, *, minimum_count: int = 2) -> np.ndarray:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a numeric one-dimensional sequence")
    try:
        result = np.asarray(tuple(values), dtype=float)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must be a numeric one-dimensional sequence") from error
    if (result.ndim != 1 or len(result) < minimum_count
            or not np.all(np.isfinite(result)) or np.any(result <= 0.)
            or np.any(np.diff(result) <= 0.)):
        raise ValueError(f"{name} must contain at least {minimum_count} positive, finite, increasing values")
    return result


def _bracket(axis: np.ndarray, query: float, name: str) -> tuple[int, float]:
    query = finite(query, name, positive=True)
    if query < axis[0] or query > axis[-1]:
        raise ValueError(f"{name} is outside the tabulated envelope; extrapolation is disabled")
    left = int(np.searchsorted(axis, query, side="right") - 1)
    left = min(max(left, 0), len(axis) - 2)
    right = left + 1
    if query == axis[left]:
        return left, 0.
    if query == axis[right]:
        return left, 1.
    return left, (query - axis[left]) / (axis[right] - axis[left])


def _bilinear(values: np.ndarray, rho_axis: np.ndarray, temperature_axis: np.ndarray,
              rho_kg_m3: float, temperature_k: float, interpolation: str) -> float:
    ir, wr = _bracket(rho_axis, rho_kg_m3, "density kg/m^3")
    it, wt = _bracket(temperature_axis, temperature_k, "temperature K")
    raw = values[np.ix_((it, it + 1), (ir, ir + 1))]
    if interpolation == "linear":
        lower = raw[0, 0] * (1. - wr) + raw[0, 1] * wr
        upper = raw[1, 0] * (1. - wr) + raw[1, 1] * wr
        result = lower * (1. - wt) + upper * wt
    else:
        # Log-linear interpolation preserves positivity for pressure and c_T.
        logged = np.log(raw)
        lower = logged[0, 0] * (1. - wr) + logged[0, 1] * wr
        upper = logged[1, 0] * (1. - wr) + logged[1, 1] * wr
        result = math.exp(lower * (1. - wt) + upper * wt)
    return finite(float(result), "interpolated EOS property", positive=True)


@dataclass(frozen=True, slots=True)
class IsothermalEOSTable:
    """Immutable rectangular rho-T table implementing ``IsothermalSinglePhaseEOS``.

    Property arrays use shape ``(n_temperature, n_density)``. Density and
    temperature axes must be positive, strictly increasing and explicitly
    bounded. Pressure must increase strictly with density at every tabulated
    temperature so the p-T to rho-T inverse remains single-valued.
    """

    density_axis_kg_m3: np.ndarray = field(repr=False, compare=False)
    temperature_axis_k: np.ndarray = field(repr=False, compare=False)
    pressure_pa: np.ndarray = field(repr=False, compare=False)
    isothermal_sound_speed_m_s: np.ndarray = field(repr=False, compare=False)
    source_eos_identity: str
    interpolation: str = "linear"
    sound_speed_mode: str = "sampled"
    table_sha256: str = field(init=False)

    def __post_init__(self):
        density_axis = immutable_array(self.density_axis_kg_m3, dtype=float,
                                       name="density_axis_kg_m3")
        temperature_axis = immutable_array(self.temperature_axis_k, dtype=float,
                                           name="temperature_axis_k")
        pressure = immutable_array(self.pressure_pa, dtype=float, name="pressure_pa")
        sound = immutable_array(self.isothermal_sound_speed_m_s, dtype=float,
                                name="isothermal_sound_speed_m_s")
        if (density_axis.ndim != 1 or len(density_axis) < 2
                or temperature_axis.ndim != 1 or len(temperature_axis) < 2
                or not np.all(np.isfinite(density_axis))
                or not np.all(np.isfinite(temperature_axis))
                or np.any(density_axis <= 0.) or np.any(temperature_axis <= 0.)
                or np.any(np.diff(density_axis) <= 0.)
                or np.any(np.diff(temperature_axis) <= 0.)):
            raise ValueError("EOS table axes must be positive, finite, one-dimensional and strictly increasing")
        expected_shape = (len(temperature_axis), len(density_axis))
        if pressure.shape != expected_shape or sound.shape != expected_shape:
            raise ValueError("EOS property tables must have shape (n_temperature, n_density)")
        if (not np.all(np.isfinite(pressure)) or not np.all(np.isfinite(sound))
                or np.any(pressure <= 0.) or np.any(sound <= 0.)):
            raise ValueError("EOS table pressure and isothermal sound speed must be positive and finite")
        if np.any(np.diff(pressure, axis=1) <= 0.):
            raise ValueError("EOS table pressure must increase strictly with density at every temperature")
        if (not isinstance(self.source_eos_identity, str)
                or not self.source_eos_identity.strip()):
            raise ValueError("Retain the source EOS identity used to build this table")
        if self.interpolation not in _INTERPOLATION_MODES:
            raise ValueError(f"Select interpolation from {sorted(_INTERPOLATION_MODES)}")
        if self.sound_speed_mode not in _SOUND_SPEED_MODES:
            raise ValueError(f"Select sound_speed_mode from {sorted(_SOUND_SPEED_MODES)}")
        digest = hashlib.sha256()
        digest.update(b"h2physics-isothermal-eos-table-v1\0")
        digest.update(self.source_eos_identity.encode("utf-8"))
        digest.update(b"\0" + self.interpolation.encode("ascii") + b"\0")
        for array in (density_axis, temperature_axis, pressure, sound):
            contiguous = np.ascontiguousarray(array, dtype="<f8")
            digest.update(np.asarray(contiguous.shape, dtype="<u8").tobytes())
            digest.update(contiguous.tobytes(order="C"))
        object.__setattr__(self, "density_axis_kg_m3", density_axis)
        object.__setattr__(self, "temperature_axis_k", temperature_axis)
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "isothermal_sound_speed_m_s", sound)
        object.__setattr__(self, "table_sha256", digest.hexdigest())

    @classmethod
    def from_eos(cls, eos: IsothermalSinglePhaseEOS, *,
                 density_axis_kg_m3: Sequence[float],
                 temperature_axis_k: Sequence[float],
                 interpolation: str = "linear",
                 sound_speed_mode: str = "sampled") -> IsothermalEOSTable:
        """Sample an EOS on caller-defined axes; perform no extrapolation.

        This method performs direct source-EOS queries at every grid node. Run
        table generation on the intended compute resource, then use a separate
        held-out case to measure interpolation error before qualification.
        """
        if interpolation not in _INTERPOLATION_MODES:
            raise ValueError(f"Select interpolation from {sorted(_INTERPOLATION_MODES)}")
        if sound_speed_mode not in _SOUND_SPEED_MODES:
            raise ValueError(f"Select sound_speed_mode from {sorted(_SOUND_SPEED_MODES)}")
        identity = getattr(eos, "identity", None)
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("The source EOS must have a stable identity")
        for method in ("pressure_rho_t", "isothermal_sound_speed_rho_t"):
            if not callable(getattr(eos, method, None)):
                raise TypeError(f"The source EOS must implement {method}(...)")
        density_axis = _axis(density_axis_kg_m3, "density_axis_kg_m3")
        temperature_axis = _axis(temperature_axis_k, "temperature_axis_k")
        pressure = np.empty((len(temperature_axis), len(density_axis)), dtype=float)
        sound = np.empty_like(pressure)
        for temperature_index, temperature in enumerate(temperature_axis):
            for density_index, density in enumerate(density_axis):
                pressure[temperature_index, density_index] = eos.pressure_rho_t(
                    float(density), float(temperature),
                )
                sound[temperature_index, density_index] = eos.isothermal_sound_speed_rho_t(
                    float(density), float(temperature),
                )
        return cls(density_axis, temperature_axis, pressure, sound, identity,
                   interpolation, sound_speed_mode)

    @property
    def identity(self) -> str:
        policy = ("" if self.sound_speed_mode == "sampled"
                  else "pressure-derivative:")
        return (f"isothermal-eos-table-v2:{policy}{self.interpolation}:"
                f"{self.source_eos_identity}:{self.table_sha256}")

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.temperature_axis_k), len(self.density_axis_kg_m3))

    def pressure_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        return _bilinear(self.pressure_pa, self.density_axis_kg_m3,
                         self.temperature_axis_k, rho_kg_m3, t_k,
                         self.interpolation)

    def isothermal_sound_speed_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        """Query sampled c_T, or sqrt of the exact pressure-interpolant derivative.

        Derivative mode uses the interval to the right of an interior density
        knot, and the left interval at the upper endpoint. Piecewise derivatives
        may jump at knots; no smooth or native derivative is claimed there.
        The sampled native c_T grid remains retained for provenance in both modes.
        """
        if self.sound_speed_mode == "pressure_derivative":
            ir, _ = _bracket(self.density_axis_kg_m3, rho_kg_m3, "density kg/m^3")
            it, wt = _bracket(self.temperature_axis_k, t_k, "temperature K")
            pressure = self.pressure_pa[np.ix_((it, it + 1), (ir, ir + 1))]
            if self.interpolation == "log_linear":
                pressure = np.log(pressure)
            width = self.density_axis_kg_m3[ir + 1] - self.density_axis_kg_m3[ir]
            slope = ((pressure[0, 1] - pressure[0, 0]) * (1. - wt)
                     + (pressure[1, 1] - pressure[1, 0]) * wt) / width
            if self.interpolation == "log_linear":
                slope *= self.pressure_rho_t(rho_kg_m3, t_k)
            derivative = finite(float(slope), "pressure-interpolant derivative", positive=True)
            return math.sqrt(derivative)
        return _bilinear(self.isothermal_sound_speed_m_s,
                         self.density_axis_kg_m3, self.temperature_axis_k,
                         rho_kg_m3, t_k, self.interpolation)

    def density_pt(self, p_pa: float, t_k: float) -> float:
        pressure_query = finite(p_pa, "pressure Pa", positive=True)
        temperature_query = finite(t_k, "temperature K", positive=True)
        it, wt = _bracket(self.temperature_axis_k, temperature_query,
                          "temperature K")
        p0 = self.pressure_pa[it]
        p1 = self.pressure_pa[it + 1]
        if self.interpolation == "linear":
            p_at_t = p0 * (1. - wt) + p1 * wt
            pressure_lookup = pressure_query
            density_lookup = self.density_axis_kg_m3
        else:
            p_at_t = np.exp(np.log(p0) * (1. - wt) + np.log(p1) * wt)
            pressure_lookup = math.log(pressure_query)
            # Forward log(P) interpolation uses linear density coordinates.
            # Its inverse therefore interpolates density, never log(density).
            density_lookup = self.density_axis_kg_m3
            p_at_t = np.log(p_at_t)
        if pressure_lookup < p_at_t[0] or pressure_lookup > p_at_t[-1]:
            raise ValueError("Pressure is outside the interpolated p-T table envelope; extrapolation is disabled")
        density = np.interp(pressure_lookup, p_at_t, density_lookup)
        return finite(float(density), "interpolated EOS mass density", positive=True)


@dataclass(frozen=True, slots=True)
class IsothermalEOSTableQualification:
    """Held-out direct-EOS interpolation and timing receipt, not model validation."""

    source_eos_identity: str
    table_identity: str
    table_sha256: str
    validation_point_count: int
    seed: int
    interpolation: str
    maximum_relative_pressure_error: float
    maximum_relative_density_error: float
    maximum_relative_sound_speed_error: float
    maximum_relative_error_allowed: float
    reference_seconds_per_query: float
    table_seconds_per_query: float

    def __post_init__(self):
        for name in ("source_eos_identity", "table_identity", "table_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Qualification receipt requires {name}")
        if (type(self.validation_point_count) is not int or self.validation_point_count < 1
                or type(self.seed) is not int or self.seed < 0):
            raise ValueError("Qualification sample count and seed must be nonnegative explicit integers")
        if self.interpolation not in _INTERPOLATION_MODES:
            raise ValueError("Qualification receipt has an unsupported interpolation mode")
        for name in ("maximum_relative_pressure_error", "maximum_relative_density_error",
                     "maximum_relative_sound_speed_error"):
            if finite(getattr(self, name), name) < 0.:
                raise ValueError("Observed interpolation errors cannot be negative")
        finite(self.maximum_relative_error_allowed, "maximum_relative_error_allowed", positive=True)
        finite(self.reference_seconds_per_query, "reference_seconds_per_query", positive=True)
        finite(self.table_seconds_per_query, "table_seconds_per_query", positive=True)

    @property
    def maximum_relative_error(self) -> float:
        return max(self.maximum_relative_pressure_error,
                   self.maximum_relative_density_error,
                   self.maximum_relative_sound_speed_error)

    @property
    def error_gate_passed(self) -> bool:
        return self.maximum_relative_error <= self.maximum_relative_error_allowed

    @property
    def measured_speedup(self) -> float:
        return self.reference_seconds_per_query / self.table_seconds_per_query


def qualify_isothermal_eos_table(table: IsothermalEOSTable,
                                 reference: IsothermalSinglePhaseEOS, *,
                                 validation_point_count: int = 256,
                                 seed: int = 20261031,
                                 maximum_relative_error: float = 0.01
                                 ) -> IsothermalEOSTableQualification:
    """Compare table queries with its identified source EOS on held-out states.

    The random sample is log-uniform in density and uniform in temperature.
    Timing summaries are retained for workload comparison but are not accuracy
    evidence. A returned receipt does not mark a physical model as validated.
    """
    if type(table) is not IsothermalEOSTable:
        raise TypeError("Qualify an issued IsothermalEOSTable")
    identity = getattr(reference, "identity", None)
    if identity != table.source_eos_identity:
        raise ValueError("The qualification source EOS identity must match the table's builder")
    if (type(validation_point_count) is not int or validation_point_count < 1
            or type(seed) is not int or seed < 0):
        raise ValueError("Supply a positive validation count and nonnegative integer seed")
    budget = finite(maximum_relative_error, "maximum_relative_error", positive=True)
    rng = random.Random(seed)
    rho_min, rho_max = map(float, (table.density_axis_kg_m3[0],
                                   table.density_axis_kg_m3[-1]))
    temperature_min, temperature_max = map(float, (table.temperature_axis_k[0],
                                                   table.temperature_axis_k[-1]))
    samples = tuple((math.exp(rng.uniform(math.log(rho_min), math.log(rho_max))),
                     rng.uniform(temperature_min, temperature_max))
                    for _ in range(validation_point_count))
    pressure_error = density_error = sound_error = 0.
    reference_started = time.perf_counter()
    reference_values = tuple((reference.pressure_rho_t(rho, temperature),
                              reference.isothermal_sound_speed_rho_t(rho, temperature))
                             for rho, temperature in samples)
    reference_seconds = (time.perf_counter() - reference_started) / validation_point_count
    table_started = time.perf_counter()
    table_values = tuple((table.pressure_rho_t(rho, temperature),
                          table.isothermal_sound_speed_rho_t(rho, temperature))
                         for rho, temperature in samples)
    table_seconds = (time.perf_counter() - table_started) / validation_point_count
    for (rho, temperature), (expected_p, expected_c), (actual_p, actual_c) in zip(
            samples, reference_values, table_values, strict=True):
        pressure_error = max(pressure_error, abs(actual_p - expected_p) / abs(expected_p))
        sound_error = max(sound_error, abs(actual_c - expected_c) / abs(expected_c))
        expected_rho = reference.density_pt(expected_p, temperature)
        actual_rho = table.density_pt(expected_p, temperature)
        density_error = max(density_error, abs(actual_rho - expected_rho) / abs(expected_rho))
    # Include inverse-query work in both timing readings, with equal samples.
    inverse_reference_started = time.perf_counter()
    for (rho, temperature), (expected_p, _) in zip(samples, reference_values, strict=True):
        reference.density_pt(expected_p, temperature)
    reference_seconds += (time.perf_counter() - inverse_reference_started) / validation_point_count
    inverse_table_started = time.perf_counter()
    for (rho, temperature), (expected_p, _) in zip(samples, reference_values, strict=True):
        table.density_pt(expected_p, temperature)
    table_seconds += (time.perf_counter() - inverse_table_started) / validation_point_count
    return IsothermalEOSTableQualification(
        identity, table.identity, table.table_sha256, validation_point_count, seed,
        table.interpolation, pressure_error, density_error, sound_error, budget,
        reference_seconds, table_seconds,
    )


__all__ = ["IsothermalEOSTable", "IsothermalEOSTableQualification",
           "qualify_isothermal_eos_table"]
