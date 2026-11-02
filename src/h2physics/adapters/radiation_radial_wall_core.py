"""Shared provenance and execution core for incident-radiation radial targets."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from .result_provenance import recorded_content_sha256
from .thermal_target import IncidentHeatHistory
from .radial_radiation_target import RadialRadiationTargetTrace, run_radial_radiation_target

_PENDING = set()


@dataclass(frozen=True, slots=True)
class RadiationRadialWallCore:
    """Common receipt for caller-projected incident radiation on a radial wall."""

    incident_history: IncidentHeatHistory = field(repr=False, compare=False)
    projected_history: IncidentHeatHistory = field(repr=False, compare=False)
    radial_trace: RadialRadiationTargetTrace = field(repr=False, compare=False)
    surface_projection_factor: float
    surface_projection_evidence_id: str
    absorptivity: float
    geometry_evidence_id: str
    application_evidence_id: str
    uniform_circumference_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use run_radiation_radial_wall_core to issue this receipt")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            self.incident_history, self.projected_history, self.radial_trace,
            self.surface_projection_factor, self.surface_projection_evidence_id,
            self.absorptivity, self.geometry_evidence_id,
            self.application_evidence_id, self.uniform_circumference_evidence_id,
        ))

    def require_current(self):
        if (type(self.incident_history) is not IncidentHeatHistory
                or type(self.projected_history) is not IncidentHeatHistory
                or type(self.radial_trace) is not RadialRadiationTargetTrace):
            raise TypeError("Retain the original typed incident history and radial response")
        guard = getattr(self.incident_history.source_owner, "require_current", None)
        if callable(guard):
            guard()
        self.radial_trace.require_current()
        projection = finite(self.surface_projection_factor, "surface projection factor")
        if not 0 <= projection <= 1:
            raise ValueError("Surface projection factor must be in [0,1]")
        if (self.radial_trace.incident is not self.projected_history
                or self.projected_history.source_owner is not self.incident_history.source_owner
                or self.projected_history.clock_id != self.incident_history.clock_id
                or self.projected_history.frame_id != self.incident_history.frame_id
                or self.projected_history.source_id != self.incident_history.source_id
                or not np.array_equal(self.projected_history.edges_s, self.incident_history.edges_s)
                or not np.array_equal(
                    self.projected_history.incident_flux_w_m2,
                    self.incident_history.incident_flux_w_m2*projection,
                )
                or self.radial_trace.absorptivity != self.absorptivity
                or self.radial_trace.geometry_evidence_id != self.geometry_evidence_id
                or self.radial_trace.evidence_id != self.application_evidence_id
                or self.radial_trace.uniform_circumference_evidence_id
                    != self.uniform_circumference_evidence_id
                or not self.surface_projection_evidence_id.strip()
                or self._content() != self._seal):
            raise ValueError("Incident radiation and radial wall receipt no longer agree")
        if callable(guard):
            guard()
        return self


def run_radiation_radial_wall_core(
    history: IncidentHeatHistory, *, surface_projection_factor: float,
    surface_projection_evidence_id: str, absorptivity: float,
    inner_radius_m: float, outer_radius_m: float, length_m: float, material,
    initial_temperature_k, inner_boundary, geometry_evidence_id: str,
    application_evidence_id: str, uniform_circumference_evidence_id: str,
    cells: int = 40, relative_tolerance: float = 1e-7,
    absolute_tolerance_k: float = 1e-7, maximum_step_s: float,
    energy_tolerance_j: float,
) -> RadiationRadialWallCore:
    """Project source flux onto the declared surface, then reuse radial conduction."""
    if type(history) is not IncidentHeatHistory:
        raise TypeError("Supply a typed finite incident-radiation history")
    projection = finite(surface_projection_factor, "surface projection factor")
    if not 0 <= projection <= 1:
        raise ValueError("Surface projection factor must be in [0,1]")
    for value, label in (
        (surface_projection_evidence_id, "surface projection"),
        (geometry_evidence_id, "geometry"),
        (application_evidence_id, "application"),
        (uniform_circumference_evidence_id, "uniform circumference"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {label} evidence")
    guard = getattr(history.source_owner, "require_current", None)
    if callable(guard):
        guard()
    projected = IncidentHeatHistory(
        history.edges_s, history.incident_flux_w_m2*projection,
        history.clock_id, history.frame_id, history.source_id,
        history.boundary_id+":surface:"+surface_projection_evidence_id,
        application_evidence_id+":"+surface_projection_evidence_id,
        history.origin, history.source_owner,
    )
    radial = run_radial_radiation_target(
        projected, inner_radius_m=inner_radius_m, outer_radius_m=outer_radius_m,
        length_m=length_m, material=material,
        initial_temperature_k=initial_temperature_k, inner_boundary=inner_boundary,
        absorptivity=absorptivity, geometry_evidence_id=geometry_evidence_id,
        evidence_id=application_evidence_id,
        uniform_circumference_evidence_id=uniform_circumference_evidence_id,
        cells=cells, relative_tolerance=relative_tolerance,
        absolute_tolerance_k=absolute_tolerance_k, maximum_step_s=maximum_step_s,
        energy_tolerance_j=energy_tolerance_j,
    )
    token = object()
    _PENDING.add(token)
    try:
        receipt = RadiationRadialWallCore(
            history, projected, radial, projection, surface_projection_evidence_id,
            float(absorptivity), geometry_evidence_id, application_evidence_id,
            uniform_circumference_evidence_id, token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    if callable(guard):
        guard()
    return receipt.require_current()


__all__ = ["RadiationRadialWallCore", "run_radiation_radial_wall_core"]
