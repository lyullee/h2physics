"""Line-source thermal radiation composition for an admitted HyRAM jet flame.

This explicit geometric model distributes the existing native HyRAM emitted
radiative power uniformly along the admitted visible centerline and applies the
caller's atmospheric transmissivity. It owns no nozzle, flame, radiant fraction,
atmosphere, view obstruction, surface absorption, or injury correlation.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ..core import immutable_array, finite
from .hyram_flame import HyRAMFlameRun, _native_flame_signature
from .result_provenance import recorded_content_sha256

STATUS = "implemented_unverified"


class _JetRadiationReceiptIssuer:
    """One-result token that prevents direct construction and dataclass cloning."""

    __slots__ = ("owner", "token")

    def __init__(self, token):
        if token not in _PENDING_JET_RADIATION_ISSUERS:
            raise TypeError("Only the native radiation calculation may issue a result token")
        self.token = token
        self.owner = None


_PENDING_JET_RADIATION_ISSUERS: set[object] = set()


def _issue_jet_radiation_field(**values):
    token = object()
    _PENDING_JET_RADIATION_ISSUERS.add(token)
    try:
        return JetRadiationField(**values, _issuer=_JetRadiationReceiptIssuer(token))
    except Exception:
        _PENDING_JET_RADIATION_ISSUERS.discard(token)
        raise


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must identify its evidence or physical frame")
    return value


def _frozen(values, name):
    array = np.asarray(values, dtype=float).copy()
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    array = immutable_array(array, name="array")
    return array


@dataclass(frozen=True, slots=True)
class LineRadiationPolicy:
    minimum_distance_m: float
    relative_power_tolerance: float
    absolute_power_tolerance_w: float
    geometry_frame_id: str
    atmospheric_model_id: str
    application_domain_id: str
    segment_subdivisions: int = 1

    def __post_init__(self):
        if (isinstance(self.segment_subdivisions, bool)
                or not isinstance(self.segment_subdivisions, int) or self.segment_subdivisions < 1):
            raise ValueError("Line quadrature subdivisions must be a positive integer")
        finite(self.minimum_distance_m, "minimum source distance", positive=True)
        finite(self.relative_power_tolerance, "relative power tolerance", positive=True)
        finite(self.absolute_power_tolerance_w, "absolute power tolerance", positive=True)
        for key in ("geometry_frame_id", "atmospheric_model_id", "application_domain_id"):
            _identity(getattr(self, key), key)


@dataclass(frozen=True, slots=True)
class JetRadiationField:
    source: HyRAMFlameRun
    receiver_points_m: np.ndarray
    incident_flux_w_m2: np.ndarray
    segment_transmissivity: np.ndarray
    mean_path_transmissivity: float
    emitted_power_w: float
    atmosphere_weighted_power_w: float
    minimum_distance_m: float
    maximum_transmissivity: float
    line_source_power_w_m: float
    policy: LineRadiationPolicy
    status: str = STATUS
    quantity: str = "isotropic point-receiver incident irradiance; W/m2"
    _issuer: object = field(default=None, repr=False, compare=False)
    _signature: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self._issuer, _JetRadiationReceiptIssuer):
            raise TypeError("Use line_source_irradiance to issue a radiation field")
        if self._issuer.token not in _PENDING_JET_RADIATION_ISSUERS:
            raise TypeError("A radiation-field issuer must be pending from the native calculation")
        _PENDING_JET_RADIATION_ISSUERS.remove(self._issuer.token)
        if self._issuer.owner is not None and self._issuer.owner is not self:
            raise TypeError("A radiation-field receipt token cannot issue a cloned result")
        self._issuer.owner = self
        if type(self.source) is not HyRAMFlameRun or not self.source.accepted:
            raise ValueError("A radiation field must retain an accepted native HyRAM flame")
        if _native_flame_signature(self.source.native) != self.source.native_signature:
            raise ValueError("Native flame fields changed before radiation receipt construction")
        if type(self.policy) is not LineRadiationPolicy:
            raise TypeError("A radiation field must retain its typed line-source policy")
        if self.policy.geometry_frame_id != self.source.location.coordinate_frame_id:
            raise ValueError("Radiation receiver frame differs from the admitted flame frame")
        points = _frozen(self.receiver_points_m, "receiver points")
        flux = _frozen(self.incident_flux_w_m2, "incident flux")
        transmission = _frozen(self.segment_transmissivity, "segment transmissivity")
        if points.ndim != 2 or points.shape[1] != 3 or not len(points):
            raise ValueError("Receiver points must retain a nonempty (n,3) coordinate array")
        if flux.shape != (len(points),) or np.any(flux < 0.0):
            raise ValueError("Incident flux must contain one nonnegative value per receiver")
        centerline = np.asarray(self.source.centreline, dtype=float)
        if centerline.ndim != 2 or centerline.shape[1] < 4 or len(centerline) < 2:
            raise ValueError("The admitted flame needs a complete three-dimensional centerline")
        xyz = centerline[:, 1:4]
        if self.policy.segment_subdivisions > 1:
            fractions = np.arange(self.policy.segment_subdivisions)/self.policy.segment_subdivisions
            xyz = np.vstack(((xyz[:-1, None, :]+fractions[None, :, None]
                              *np.diff(xyz, axis=0)[:, None, :]).reshape(-1, 3), xyz[-1]))
        segment = np.diff(xyz, axis=0)
        lengths = np.linalg.norm(segment, axis=1)
        length = float(np.sum(lengths))
        if np.any(lengths <= 0.0) or not math.isclose(
            length, self.source.native.Lvis, rel_tol=1e-6, abs_tol=1e-8,
        ):
            raise ValueError("Radiation centerline must span the native visible-flame length")
        midpoint = .5*(xyz[:-1]+xyz[1:])
        distances = np.linalg.norm(points[:, None, :]-midpoint[None, :, :], axis=2)
        if (transmission.shape != distances.shape or not np.all(np.isfinite(transmission))
                or np.any(transmission < 0.) or np.any(transmission > 1.)):
            raise ValueError("Retain one unclipped atmospheric transmission per receiver/segment")
        minimum_distance = float(np.min(distances))
        if (minimum_distance < self.policy.minimum_distance_m
                or not math.isclose(self.minimum_distance_m, minimum_distance,
                                    rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError("Radiation minimum distance differs from the admitted geometry")
        emitted = finite(self.source.emitted_radiative_power_w,
                         "native emitted radiative power", positive=True)
        expected_flux = np.sum(
            transmission*(emitted*lengths/length)[None, :]
            /(4.0*math.pi*distances**2), axis=1,
        )
        mean_transmission = float(np.mean(transmission, axis=0) @ (lengths/length))
        weighted_power = emitted*mean_transmission
        line_power = emitted/length
        summaries = (
            (self.emitted_power_w, emitted, "emitted power"),
            (self.mean_path_transmissivity, mean_transmission, "mean transmissivity"),
            (self.maximum_transmissivity, float(np.max(transmission)), "maximum transmissivity"),
            (self.atmosphere_weighted_power_w, weighted_power, "weighted power"),
            (self.line_source_power_w_m, line_power, "line power"),
        )
        for actual, expected, label in summaries:
            actual = finite(actual, f"radiation {label}")
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=0.0):
                raise ValueError(f"Radiation receipt {label} does not reconstruct from retained inputs")
        if not np.allclose(flux, expected_flux, rtol=1e-12, atol=0.0):
            raise ValueError("Incident flux does not reconstruct from source, geometry and transmission")
        if self.status != STATUS or self.quantity != "isotropic point-receiver incident irradiance; W/m2":
            raise ValueError("Radiation quantity/status identity differs from this model level")
        object.__setattr__(self, "receiver_points_m", points)
        object.__setattr__(self, "incident_flux_w_m2", flux)
        object.__setattr__(self, "segment_transmissivity", transmission)
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.source), self.source.native_signature, self.source.centreline,
            self.source.window, self.source.location, self.source.ambient,
            self.source.emitted_radiative_power_w, self.source.accepted, self.source.gates,
            self.receiver_points_m, self.incident_flux_w_m2, self.segment_transmissivity, self.policy,
            self.mean_path_transmissivity, self.emitted_power_w,
            self.atmosphere_weighted_power_w, self.minimum_distance_m,
            self.maximum_transmissivity, self.line_source_power_w_m, self.status, self.quantity,
        ))

    def require_current(self):
        if (not isinstance(self._issuer, _JetRadiationReceiptIssuer)
                or self._issuer.owner is not self
                or not self.source.accepted
                or _native_flame_signature(self.source.native) != self.source.native_signature
                or self._content() != self._signature):
            raise ValueError("Original admitted jet source or radiation field changed")
        return self


class JetRadiationError(RuntimeError):
    def __init__(self, cause, *, source, partial=None):
        super().__init__(str(cause))
        self.cause, self.source, self.partial = cause, source, partial


def line_source_irradiance(source: HyRAMFlameRun, receiver_points_m, *,
                           relative_humidity: float, transmissivity: Callable,
                           policy: LineRadiationPolicy) -> JetRadiationField:
    """Integrate an isotropic finite line source with the caller's transmission.

    ``source`` must pass the complete existing HyRAM source audit. Receiver
    normals are absent by design; returned flux is incident scalar irradiance.
    ``transmissivity(distance, ambient_temperature_k, relative_humidity)`` must
    return a finite dimensionless value in ``[0, 1]`` for every quadrature pair.
    """
    partial = None
    try:
        if not isinstance(source, HyRAMFlameRun) or not source.accepted:
            raise ValueError("A line-source prediction requires an accepted actual HyRAM flame result")
        if _native_flame_signature(source.native) != source.native_signature:
            raise ValueError("Native flame fields changed after their source audit")
        if not isinstance(policy, LineRadiationPolicy) or not callable(transmissivity):
            raise TypeError("Supply a typed radiation policy and transmissivity callable")
        if policy.geometry_frame_id != source.location.coordinate_frame_id:
            raise ValueError("Receiver and admitted flame coordinates must use the exact same frame")
        if not math.isclose(source.native.Lvis, source.native.S[-1], rel_tol=1e-8, abs_tol=1e-10):
            raise ValueError("The accepted native centerline must span its complete visible length")
        points = np.asarray(receiver_points_m, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.all(np.isfinite(points)):
            raise ValueError("Receiver points must be a nonempty finite (n,3) array in global metres")
        humidity = finite(relative_humidity, "relative humidity")
        if not 0.0 <= humidity <= 1.0:
            raise ValueError("Relative humidity must lie in [0,1]")

        centerline = np.asarray(source.centreline, dtype=float)
        if centerline.ndim != 2 or centerline.shape[1] < 4 or len(centerline) < 2:
            raise ValueError("Accepted native result needs at least two full 3-D visible centerline points")
        xyz = centerline[:, 1:4]
        if policy.segment_subdivisions > 1:
            fractions = np.arange(policy.segment_subdivisions)/policy.segment_subdivisions
            xyz = np.vstack(((xyz[:-1, None, :]+fractions[None, :, None]
                              *np.diff(xyz, axis=0)[:, None, :]).reshape(-1, 3), xyz[-1]))
        segment = np.diff(xyz, axis=0)
        ds = np.linalg.norm(segment, axis=1)
        if np.any(ds <= 0.0):
            raise ValueError("Native visible centerline must have positive segment lengths")
        midpoints = 0.5 * (xyz[:-1] + xyz[1:])
        distances = np.linalg.norm(points[:, None, :] - midpoints[None, :, :], axis=2)
        minimum = float(np.min(distances))
        if minimum < policy.minimum_distance_m:
            raise ValueError("A receiver is inside the declared line-source exclusion distance")
        input_signature = recorded_content_sha256((source, policy, points))
        transmission = np.asarray(transmissivity(
            distances, source.ambient.temperature_k, humidity), dtype=float)
        if recorded_content_sha256((source, policy, points)) != input_signature:
            raise ValueError("Radiation callback changed the admitted source, policy or receivers")
        if transmission.shape != distances.shape or not np.all(np.isfinite(transmission)) \
                or np.any(transmission < 0.0) or np.any(transmission > 1.0):
            raise ValueError("Atmospheric transmission must return an unclipped [0,1] array")
        emitted = finite(source.emitted_radiative_power_w, "native emitted radiative power", positive=True)
        length = float(np.sum(ds))
        if not math.isclose(length, source.native.Lvis, rel_tol=1e-6, abs_tol=1e-8):
            raise ValueError("Centerline arc length disagrees with the native visible-flame length")
        # Each segment owns its arclength share of the measured native power.
        segment_power = emitted * ds / length
        kernel = transmission * segment_power[None, :] / (4.0 * math.pi * distances**2)
        flux = np.sum(kernel, axis=1)
        # This receiver-weighted total is a source-power diagnostic; fluxes
        # from distinct observers are not spatially integrated or summed.
        mean_transmission = float(np.mean(transmission, axis=0) @ (ds / length))
        weighted_power = emitted * mean_transmission
        budget = policy.absolute_power_tolerance_w + policy.relative_power_tolerance * emitted
        if weighted_power < 0 or weighted_power > emitted + budget:
            raise ValueError("Atmosphere-weighted power diagnostic exceeds emitted power")
        partial = _issue_jet_radiation_field(
            source=source, receiver_points_m=points, incident_flux_w_m2=flux,
            segment_transmissivity=transmission, mean_path_transmissivity=mean_transmission,
            emitted_power_w=emitted, atmosphere_weighted_power_w=weighted_power,
            minimum_distance_m=minimum, maximum_transmissivity=float(np.max(transmission)),
            line_source_power_w_m=emitted/length, policy=policy,
        )
        return partial.require_current()
    except Exception as cause:
        raise JetRadiationError(cause, source=source, partial=partial) from cause


def incident_history_from_jet_radiation(field, receiver_index, *, start_s, end_s,
                                      clock_id, evidence_id, steady_projection_evidence_id):
    """Hold one original point irradiance over explicit admitted steady support.

    This transfers incident scalar irradiance, not absorbed wall flux. Geometry,
    projection/uniformity and surface absorption remain target-side assumptions.
    No ignition, termination or finite fuel inventory is inferred.
    """
    from ..core import Origin
    from .thermal_target import IncidentHeatHistory

    if type(field) is not JetRadiationField:
        raise TypeError("Retain the original line-source radiation field")
    field.require_current()
    if (isinstance(receiver_index, bool) or not isinstance(receiver_index, int)
            or not 0 <= receiver_index < len(field.incident_flux_w_m2)):
        raise ValueError("Select one existing receiver by integer index")
    for value in (clock_id, evidence_id, steady_projection_evidence_id):
        _identity(value, "steady radiation handoff evidence")
    start, end = finite(start_s, "start_s"), finite(end_s, "end_s")
    window = field.source.window
    if clock_id != window.clock_id or not window.start_s <= start < end <= window.end_s:
        raise ValueError("Radiation history must remain inside the original steady clock support")
    result = IncidentHeatHistory(
        np.asarray([start, end]), np.asarray([field.incident_flux_w_m2[receiver_index]]),
        clock_id, field.policy.geometry_frame_id,
        window.source_evidence_id+":receiver:"+str(receiver_index),
        "jet-incident-radiation:"+steady_projection_evidence_id, evidence_id,
        Origin.PREDICTED, field,
    )
    field.require_current()
    return result
