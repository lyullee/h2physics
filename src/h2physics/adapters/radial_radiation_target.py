"""Finite wall response to explicitly uniform absorbed incident irradiation.

Reuses the radial conduction owner once per exact incident-source interval.
Outer-face convection and reradiation are excluded by this prescribed net-input
boundary; callers must not interpret the result as damage or injury.
"""

from dataclasses import dataclass, replace
from math import fsum, pi
from types import MappingProxyType

import numpy as np

from ..core import immutable_array, finite
from ..materials.radial_heat import RadialThermalBoundary, radial_cylinder_heat_history
from .result_provenance import recorded_content_sha256
from .thermal_target import IncidentHeatHistory


def _signature(history, segments):
    return recorded_content_sha256((
        history,
        tuple((segment, np.asarray(segment.native_solution.t),
               np.asarray(segment.native_solution.y)) for segment in segments),
    ))


class RadialRadiationTargetError(RuntimeError):
    def __init__(self, cause, *, history, completed_segments, failed_result=None):
        super().__init__(str(cause))
        self.cause = cause
        self.history = history
        self.completed_segments = tuple(completed_segments)
        self.failed_result = failed_result
        self.native_solution = getattr(cause, "native_solution", None)


def _receipt_signature(result):
    return recorded_content_sha256((
        _signature(result.incident, result.segments), result.inputs,
        result.absorptivity, result.outer_area_m2, result.absorbed_incident_j,
        result.outer_heat_residual_j, result.evidence_id, result.geometry_evidence_id,
        result.uniform_circumference_evidence_id, result.status,
    ))


@dataclass(frozen=True, slots=True)
class RadialRadiationTargetTrace:
    incident: IncidentHeatHistory
    segments: tuple
    absorptivity: float
    outer_area_m2: float
    absorbed_incident_j: float
    outer_heat_residual_j: float
    evidence_id: str
    geometry_evidence_id: str
    uniform_circumference_evidence_id: str
    inputs: MappingProxyType
    _source_signature: str
    status: str = "implemented_unverified"

    def require_current(self):
        guard = getattr(self.incident.source_owner, "require_current", None)
        if callable(guard):
            guard()
        if _receipt_signature(self) != self._source_signature:
            raise ValueError("Incident source or retained radial thermal results changed")
        return self


def run_radial_radiation_target(history, *, inner_radius_m, outer_radius_m, length_m,
                                material, initial_temperature_k, inner_boundary,
                                absorptivity, geometry_evidence_id, evidence_id,
                                uniform_circumference_evidence_id, cells=40,
                                relative_tolerance=1e-7, absolute_tolerance_k=1e-7,
                                maximum_step_s, energy_tolerance_j):
    """Apply interval-held absorbed flux over the complete outer cylinder area.

    Source flux must already describe the declared cylinder surface, including
    any projection/shadowing. The explicit uniformity evidence admits the 1-D
    radial approximation; this function derives no view factor or fire field.
    Every discontinuity starts a new native solve with the preceding wall state.
    """
    if type(history) is not IncidentHeatHistory:
        raise TypeError("Supply the retained incident heat history")
    guard = getattr(history.source_owner, "require_current", None)
    if callable(guard):
        guard()
    for value in (geometry_evidence_id, evidence_id, uniform_circumference_evidence_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Declare geometry, radial applicability and uniformity evidence")
    fraction = finite(absorptivity, "absorptivity")
    if not 0 <= fraction <= 1:
        raise ValueError("Absorptivity must lie in [0, 1]")
    radius = finite(outer_radius_m, "outer radius", positive=True)
    length = finite(length_m, "cylinder length", positive=True)
    tolerance = finite(energy_tolerance_j, "energy tolerance", positive=True)
    step = finite(maximum_step_s, "maximum step", positive=True)
    area = 2*pi*radius*length
    source_signature = _signature(history, ())
    initial = np.array(initial_temperature_k, dtype=float, copy=True)
    initial = immutable_array(initial, name="initial")
    inputs = MappingProxyType(dict(
        inner_radius_m=inner_radius_m, outer_radius_m=radius, length_m=length,
        material=material, initial_temperature_k=initial, inner_boundary=inner_boundary,
        cells=cells, relative_tolerance=relative_tolerance,
        absolute_tolerance_k=absolute_tolerance_k, maximum_step_s=step,
        energy_tolerance_j=tolerance,
    ))
    segments = []
    temperature = initial_temperature_k
    for index, flux in enumerate(history.incident_flux_w_m2):
        if _signature(history, ()) != source_signature:
            cause = ValueError("Incident source changed during radial integration")
            raise RadialRadiationTargetError(
                cause, history=history, completed_segments=segments,
            ) from cause
        outer = RadialThermalBoundary(
            "heat_flux", fraction*float(flux),
            evidence_id+":"+uniform_circumference_evidence_id,
        )
        try:
            result = radial_cylinder_heat_history(
                inner_radius_m, radius, length, material, temperature,
                history.edges_s[index:index+2], inner_boundary, outer, cells=cells,
                maximum_step_s=step, relative_tolerance=relative_tolerance,
                absolute_tolerance_k=absolute_tolerance_k,
                history_id=f"{history.source_id}:radial-target:{index}",
                clock_id=history.clock_id, evidence_id=evidence_id,
            )
        except Exception as cause:
            raise RadialRadiationTargetError(
                cause, history=history, completed_segments=segments,
            ) from cause
        if np.max(np.abs(result.energy_residual_j)) > tolerance:
            cause = ValueError("Radial target energy residual exceeds the declared budget")
            raise RadialRadiationTargetError(
                cause, history=history, completed_segments=segments, failed_result=result,
            ) from cause
        segments.append(result)
        temperature = result.temperature_k[-1]
    if _signature(history, ()) != source_signature:
        cause = ValueError("Incident source changed during radial integration")
        raise RadialRadiationTargetError(
            cause, history=history, completed_segments=segments,
        ) from cause
    if callable(guard):
        try:
            guard()
        except Exception as cause:
            raise RadialRadiationTargetError(
                cause, history=history, completed_segments=segments,
            ) from cause
    absorbed = area*fraction*float(np.dot(
        np.diff(history.edges_s), history.incident_flux_w_m2,
    ))
    residual = fsum(float(v.outer_heat_into_solid_j[-1]) for v in segments)-absorbed
    if abs(residual) > tolerance:
        cause = ValueError("Radial outer heat differs from the absorbed incident inventory")
        raise RadialRadiationTargetError(
            cause, history=history, completed_segments=segments,
        ) from cause
    segments = tuple(segments)
    result = RadialRadiationTargetTrace(
        history, segments, fraction, area, absorbed, residual, evidence_id,
        geometry_evidence_id, uniform_circumference_evidence_id, inputs, "",
    )
    return replace(result, _source_signature=_receipt_signature(result))
