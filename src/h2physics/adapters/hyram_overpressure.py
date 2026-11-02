"""Conditional unconfined peak pressure from the actual optional HyRAM function.

HyRAM owns the Bauwens correlation. This boundary supplies evidenced participating
fuel energy and SI dimensional scaling, without constructing a jet/cloud surrogate.
Primary description: https://www.osti.gov/servlets/purl/2563814, section 3.4.5.
No native coefficient table, correlation equation or field solver is copied here.
"""

import inspect
import hashlib
import json
import math
from dataclasses import dataclass, field as dataclass_field
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, finite


_PENDING_PEAK_ISSUERS: set[object] = set()
_PENDING_THRESHOLD_ISSUERS: set[object] = set()


def _array_digest(value):
    array = np.asarray(value)
    return (array.dtype.str, array.shape,
            hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest())


def _identity_snapshot(value):
    if isinstance(value, np.ndarray):
        return ("array", *_array_digest(value))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(_identity_snapshot(item) for item in value))
    if isinstance(value, dict):
        return ("dict", tuple(sorted((str(key), _identity_snapshot(item))
                                     for key, item in value.items())))
    if hasattr(value, "__dataclass_fields__"):
        return (type(value).__module__, type(value).__qualname__,
                tuple((name, _identity_snapshot(getattr(value, name)))
                      for name in value.__dataclass_fields__ if not name.startswith("_")))
    if callable(value):
        return ("callable", id(value))
    if isinstance(value, (str, int, float, bool, type(None))):
        return (type(value).__name__, repr(value))
    return (type(value).__module__, type(value).__qualname__, id(value), repr(value))


def _receipt_digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     default=repr).encode("utf-8")).hexdigest()


def _identity(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare nonempty source, reference, event and frame identities")


def _array(values, name):
    result = np.array(values, dtype=float, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite SI coordinates")
    result = immutable_array(result, name="result")
    return result


@dataclass(frozen=True, slots=True)
class DetonableHydrogenEnergy:
    """Supplied participating H2 mass, not released/flammable-cloud mass inferred here."""

    participating_hydrogen_mass_kg: float
    heat_of_combustion_j_kg: float
    mass_evidence_id: str
    heat_evidence_id: str
    combustion_basis_id: str
    source_id: str
    origin: Origin

    def __post_init__(self):
        if finite(self.participating_hydrogen_mass_kg, "participating H2 mass") < 0:
            raise ValueError("Participating hydrogen mass cannot be negative")
        finite(self.heat_of_combustion_j_kg, "heat of combustion", positive=True)
        _identity(self.mass_evidence_id, self.heat_evidence_id,
                  self.combustion_basis_id, self.source_id)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Unresolved participating energy cannot define a blast scenario")
        finite(self.energy_j, "participating combustion energy")
        if self.participating_hydrogen_mass_kg > 0 and self.energy_j <= 0:
            raise ValueError("Positive mass energy underflow cannot become a zero-energy scenario")

    @property
    def energy_j(self):
        return self.participating_hydrogen_mass_kg*self.heat_of_combustion_j_kg


@dataclass(frozen=True, slots=True)
class OverpressureEvent:
    event_id: str
    centre_m: tuple[float, float, float]
    frame_id: str
    centre_evidence_id: str
    snapshot_time_s: float
    clock_id: str

    def __post_init__(self):
        _identity(self.event_id, self.frame_id, self.centre_evidence_id, self.clock_id)
        centre = _array(self.centre_m, "event centre")
        if centre.shape != (3,):
            raise ValueError("An event centre must have three coordinates")
        object.__setattr__(self, "centre_m", tuple(float(value) for value in centre))
        finite(self.snapshot_time_s, "event snapshot time")


@dataclass(frozen=True, slots=True)
class OverpressureEnvironment:
    ambient_pressure_pa_absolute: float
    pressure_evidence_id: str

    def __post_init__(self):
        finite(self.ambient_pressure_pa_absolute, "ambient absolute pressure", positive=True)
        _identity(self.pressure_evidence_id)


@dataclass(frozen=True, slots=True)
class BauwensCorrelationDomain:
    """Caller-declared application envelope, not a measured validation certificate."""

    minimum_scaled_distance: float
    maximum_scaled_distance: float
    minimum_ambient_pressure_pa: float
    maximum_ambient_pressure_pa: float
    minimum_standoff_m: float
    evidence_id: str

    def __post_init__(self):
        low = finite(self.minimum_scaled_distance, "minimum scaled distance", positive=True)
        high = finite(self.maximum_scaled_distance, "maximum scaled distance", positive=True)
        if low < .01 or high <= low:
            raise ValueError("Require 0.01 <= minimum scaled distance < maximum")
        if finite(self.minimum_ambient_pressure_pa, "minimum ambient P", positive=True) >= finite(
                self.maximum_ambient_pressure_pa, "maximum ambient P", positive=True):
            raise ValueError("Ambient absolute-pressure domain bounds must increase")
        finite(self.minimum_standoff_m, "minimum physical standoff", positive=True)
        _identity(self.evidence_id)

    def require_pressure(self, environment):
        if not self.minimum_ambient_pressure_pa <= environment.ambient_pressure_pa_absolute <= (
                self.maximum_ambient_pressure_pa):
            raise ValueError("Ambient absolute pressure is outside the declared domain")

    def require_distance(self, scaled):
        if np.any(scaled < self.minimum_scaled_distance) or np.any(
                scaled > self.maximum_scaled_distance):
            raise ValueError("Scaled distance is outside the declared domain; no clamp/extrapolation")


@dataclass(frozen=True, slots=True)
class BauwensPeakResult:
    energy: DetonableHydrogenEnergy
    event: OverpressureEvent
    environment: OverpressureEnvironment
    domain: BauwensCorrelationDomain
    receptors_m: np.ndarray
    distance_m: np.ndarray
    scaled_distance: np.ndarray
    scaled_overpressure: np.ndarray
    peak_overpressure_pa: np.ndarray
    ambient_plus_peak_overpressure_pa: np.ndarray
    native_class: Any
    native_function: Any
    native_scaled_result: Any
    native_source_id: str
    zero_energy_limit: bool
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PEAK_ISSUERS:
            raise ValueError("Bauwens peak results are issued only by the native evaluator")
        _PENDING_PEAK_ISSUERS.remove(self._issuer_token)
        for name in ("receptors_m", "distance_m", "scaled_overpressure",
                     "peak_overpressure_pa", "ambient_plus_peak_overpressure_pa"):
            object.__setattr__(self, name, _array(getattr(self, name), name))
        scaled = np.array(self.scaled_distance, dtype=float, copy=True)
        scaled = immutable_array(scaled, name="scaled")
        object.__setattr__(self, "scaled_distance", scaled)
        self._validate_projection()
        object.__setattr__(self, "_seal", self._current_digest())

    def _validate_projection(self):
        if (not isinstance(self.energy, DetonableHydrogenEnergy)
                or not isinstance(self.event, OverpressureEvent)
                or not isinstance(self.environment, OverpressureEnvironment)
                or not isinstance(self.domain, BauwensCorrelationDomain)):
            raise TypeError("Native pressure output must retain its typed source/event/domain")
        count = len(self.receptors_m)
        if (self.receptors_m.shape != (count, 3) or count == 0
                or any(np.asarray(getattr(self, name)).shape != (count,) for name in (
                    "distance_m", "scaled_distance", "scaled_overpressure",
                    "peak_overpressure_pa", "ambient_plus_peak_overpressure_pa"))):
            raise ValueError("Native pressure result arrays have inconsistent receptor shapes")
        distance = np.linalg.norm(self.receptors_m - np.asarray(self.event.centre_m), axis=1)
        if not np.allclose(distance, self.distance_m, rtol=1e-12, atol=1e-12):
            raise ValueError("Retained receptor distances do not reproduce the event geometry")
        if self.energy.energy_j == 0:
            if not self.zero_energy_limit or not np.all(np.isposinf(self.scaled_distance)):
                raise ValueError("Zero-energy result does not retain its limiting scaled distance")
        else:
            expected_scaled = self.distance_m / HyRAMBauwensOverpressure._length(
                self.energy, self.environment)
            if self.zero_energy_limit or not np.allclose(expected_scaled, self.scaled_distance,
                                                           rtol=1e-12, atol=1e-12):
                raise ValueError("Scaled distance differs from the retained energy and ambient state")
        native_values = np.asarray(self.native_scaled_result, dtype=float)
        if (native_values.shape != (count,) or not np.all(np.isfinite(native_values))
                or not np.allclose(native_values, self.scaled_overpressure,
                                   rtol=1e-13, atol=1e-14)):
            raise ValueError("Retained scaled pressure differs from the actual native result")
        expected_pressure = self.scaled_overpressure * self.environment.ambient_pressure_pa_absolute
        if (not np.allclose(expected_pressure, self.peak_overpressure_pa, rtol=1e-13, atol=1e-10)
                or not np.allclose(expected_pressure + self.environment.ambient_pressure_pa_absolute,
                                   self.ambient_plus_peak_overpressure_pa,
                                   rtol=1e-13, atol=1e-10)):
            raise ValueError("Dimensional pressure projections differ from retained native output")
        native_method = inspect.getattr_static(self.native_class,
                                               "calc_scaled_overpressure_from_dist", None)
        if (not isinstance(native_method, staticmethod)
                or native_method.__func__ is not self.native_function):
            raise ValueError("Native correlation identity does not match the admitted class")

    def _current_digest(self):
        names = ("energy", "event", "environment", "domain", "receptors_m", "distance_m",
                 "scaled_distance", "scaled_overpressure", "peak_overpressure_pa",
                 "ambient_plus_peak_overpressure_pa", "native_class", "native_function",
                 "native_scaled_result", "native_source_id", "zero_energy_limit")
        return _receipt_digest(tuple((name, _identity_snapshot(getattr(self, name)))
                                     for name in names))

    def require_current(self):
        self._validate_projection()
        if self._current_digest() != self._seal:
            raise ValueError("Bauwens peak result or retained input changed after evaluation")
        return self


@dataclass(frozen=True, slots=True)
class BauwensThresholdResult:
    target_overpressure_pa: float
    radius_m: float
    scaled_radius: float
    forward: BauwensPeakResult
    native_solver_result: Any
    relative_radius_tolerance: float
    scaled_radius_tolerance: float
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_THRESHOLD_ISSUERS:
            raise ValueError("Threshold results are issued only by the native root/forward evaluator")
        _PENDING_THRESHOLD_ISSUERS.remove(self._issuer_token)
        if not isinstance(self.forward, BauwensPeakResult):
            raise TypeError("Threshold result requires its native forward peak receipt")
        self.forward.require_current()
        finite(self.target_overpressure_pa, "target pressure", positive=True)
        finite(self.radius_m, "threshold radius", positive=True)
        finite(self.scaled_radius, "scaled threshold radius", positive=True)
        finite(self.relative_radius_tolerance, "relative radius tolerance", positive=True)
        finite(self.scaled_radius_tolerance, "scaled radius tolerance", positive=True)
        if (not math.isclose(self.forward.peak_overpressure_pa[0], self.target_overpressure_pa,
                             rel_tol=1e-8, abs_tol=1e-8)
                or not math.isclose(self.forward.distance_m[0], self.radius_m,
                                    rel_tol=1e-12, abs_tol=1e-12)
                or not math.isclose(self.forward.scaled_distance[0], self.scaled_radius,
                                    rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError("Threshold summary differs from its retained native forward result")
        if not getattr(self.native_solver_result, "converged", False):
            raise ValueError("Threshold result requires a converged native root receipt")
        object.__setattr__(self, "_seal", self._current_digest())

    def _current_digest(self):
        return _receipt_digest((self.target_overpressure_pa, self.radius_m, self.scaled_radius,
            self.forward._seal, id(self.forward), _identity_snapshot(self.native_solver_result),
            self.relative_radius_tolerance, self.scaled_radius_tolerance))

    def require_current(self):
        self.forward.require_current()
        if self._current_digest() != self._seal:
            raise ValueError("Threshold result or native root changed after evaluation")
        return self


class OverpressureNativeError(ValueError):
    def __init__(self, message, *, native_class, native_result=None):
        self.native_class, self.native_result = native_class, native_result
        super().__init__(message)


class HyRAMBauwensOverpressure:
    """Actual standalone native pressure correlation, without a Jet instance.

    E=m_H2*q; R*=R*(Pambient/E)^(1/3); deltaP=Pambient*Pstar.
    These are the published dimensional boundary definitions, not another blast
    model. E is the participating fuel's combustion energy, with no inferred yield
    or ground/reflection multiplier. All correlation values come from HyRAM.
    """

    def __init__(self, native_bauwens_class, *, domain: BauwensCorrelationDomain,
                 native_source_id: str):
        _identity(native_source_id)
        function = inspect.getattr_static(native_bauwens_class,
                                          "calc_scaled_overpressure_from_dist", None)
        if not isinstance(native_bauwens_class, type) or not isinstance(function, staticmethod):
            raise TypeError("Supply the actual native Bauwens class with its standalone static API")
        if not isinstance(domain, BauwensCorrelationDomain):
            raise TypeError("An explicit Bauwens correlation domain is required")
        self.native_class, self.native_function = native_bauwens_class, function.__func__
        self.native_source_id, self.domain = native_source_id, domain

    def _native(self, scaled):
        current = inspect.getattr_static(self.native_class, "calc_scaled_overpressure_from_dist")
        if not isinstance(current, staticmethod) or current.__func__ is not self.native_function:
            raise OverpressureNativeError("Native correlation changed after construction",
                                          native_class=self.native_class)
        raw = self.native_function(scaled)
        values = np.asarray(raw, dtype=float)
        if values.shape != np.asarray(scaled).shape or not np.all(np.isfinite(values)) or np.any(
                values < 0):
            raise OverpressureNativeError("Native correlation returned invalid pressure values",
                                          native_class=self.native_class, native_result=raw)
        return raw, values

    @staticmethod
    def _length(energy, environment):
        return (energy.energy_j/environment.ambient_pressure_pa_absolute)**(1/3)

    def evaluate(self, energy: DetonableHydrogenEnergy, event: OverpressureEvent,
                 environment: OverpressureEnvironment, receptors_m, *, frame_id: str):
        if not isinstance(energy, DetonableHydrogenEnergy) or not isinstance(event, OverpressureEvent):
            raise TypeError("Supply explicit participating hydrogen energy and an event snapshot")
        if not isinstance(environment, OverpressureEnvironment):
            raise TypeError("Supply an explicit absolute ambient pressure")
        if frame_id != event.frame_id:
            raise ValueError("Receptors and event centre must share the declared coordinate frame")
        self.domain.require_pressure(environment)
        receptors = _array(receptors_m, "receptors")
        if receptors.ndim != 2 or receptors.shape[1:] != (3,) or len(receptors) == 0:
            raise ValueError("Supply a nonempty N by 3 array of receptor coordinates")
        distance = np.linalg.norm(receptors-np.asarray(event.centre_m), axis=1)
        if not np.all(np.isfinite(distance)) or np.any(distance <= 0):
            raise ValueError("Each receptor requires finite positive standoff from the event centre")
        if np.any(distance < self.domain.minimum_standoff_m):
            raise ValueError("Receptor standoff is below the explicitly declared physical domain")
        if energy.energy_j == 0:
            # Native static function has the exact R* -> infinity zero-energy limit.
            scaled = np.full(distance.shape, np.inf)
        else:
            length = finite(self._length(energy, environment), "energy length scale", positive=True)
            scaled = distance/length
            self.domain.require_distance(scaled)
        raw, values = self._native(scaled)
        pressure = values*environment.ambient_pressure_pa_absolute
        token = object()
        _PENDING_PEAK_ISSUERS.add(token)
        try:
            result = BauwensPeakResult(energy, event, environment, self.domain, receptors, distance,
                scaled, values, pressure, environment.ambient_pressure_pa_absolute+pressure,
                self.native_class, self.native_function, raw, self.native_source_id,
                energy.energy_j == 0, _issuer_token=token)
        finally:
            _PENDING_PEAK_ISSUERS.discard(token)
        return result

    def threshold_radius(self, target_overpressure_pa, energy, event, environment, *,
                         scaled_radius_tolerance=1e-12, relative_radius_tolerance=1e-12):
        """Invert the same native correlation within the declared radial domain.

        This is a conditional spherical radius, with no safe-distance, reflection,
        arrival-time or impairment interpretation. SciPy owns the numerical root.
        """
        from scipy.optimize import brentq

        if not isinstance(energy, DetonableHydrogenEnergy) or not isinstance(event, OverpressureEvent):
            raise TypeError("Supply explicit participating hydrogen energy and an event snapshot")
        if not isinstance(environment, OverpressureEnvironment):
            raise TypeError("Supply an explicit absolute ambient pressure")
        target = finite(target_overpressure_pa, "target pressure rise", positive=True)
        xtol = finite(scaled_radius_tolerance, "scaled radius tolerance", positive=True)
        rtol = finite(relative_radius_tolerance, "relative radius tolerance", positive=True)
        if rtol < 4*np.finfo(float).eps:
            raise ValueError("Relative radius tolerance is below the native SciPy root limit")
        self.domain.require_pressure(environment)
        if energy.energy_j <= 0:
            raise ValueError("A positive pressure threshold has no radius at zero participating energy")
        p0 = environment.ambient_pressure_pa_absolute

        def residual(scaled):
            return float(self._native(np.asarray(scaled))[1])*p0-target

        low, high = self.domain.minimum_scaled_distance, self.domain.maximum_scaled_distance
        if residual(low) < 0 or residual(high) > 0:
            raise ValueError("Target pressure is not bracketed within the declared scaled-distance domain")
        root, native = brentq(residual, low, high, xtol=xtol, rtol=rtol, full_output=True)
        length = finite(self._length(energy, environment), "energy length scale", positive=True)
        radius = root*length
        receptor = [tuple(np.asarray(event.centre_m)+np.array([radius, 0., 0.]))]
        forward = self.evaluate(energy, event, environment, receptor, frame_id=event.frame_id)
        if not native.converged or not math.isclose(float(forward.peak_overpressure_pa[0]),
                                                  target, rel_tol=1e-8, abs_tol=1e-8):
            raise OverpressureNativeError("Native correlation inverse failed its forward pressure check",
                                          native_class=self.native_class, native_result=native)
        token = object()
        _PENDING_THRESHOLD_ISSUERS.add(token)
        try:
            result = BauwensThresholdResult(target, radius, root, forward, native, rtol, xtol,
                                            _issuer_token=token)
        finally:
            _PENDING_THRESHOLD_ISSUERS.discard(token)
        return result
