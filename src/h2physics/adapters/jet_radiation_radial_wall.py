"""Source-bound HyRAM line-radiation to finite radial-wall thermal response."""

from dataclasses import dataclass, replace

import numpy as np

from .radiation_radial_wall_core import (
    RadiationRadialWallCore,
    run_radiation_radial_wall_core,
)
from .result_provenance import recorded_content_sha256


@dataclass(frozen=True, slots=True)
class JetRadiationRadialWallTrace:
    radiation_field: object
    receiver_index: int
    receiver_point_m: tuple[float, float, float]
    receiver_frame_id: str
    surface_projection_factor: float
    surface_projection_evidence_id: str
    absorptivity: float
    geometry_evidence_id: str
    application_evidence_id: str
    uniform_circumference_evidence_id: str
    radial_trace: object
    core_receipt: RadiationRadialWallCore
    _seal: str

    def require_current(self):
        from .jet_radiation import JetRadiationField
        from .radial_radiation_target import RadialRadiationTargetTrace

        if type(self.radiation_field) is not JetRadiationField:
            raise TypeError("Retain the original issued HyRAM line-radiation field")
        if type(self.radial_trace) is not RadialRadiationTargetTrace:
            raise TypeError("Retain the original radial wall response")
        if type(self.core_receipt) is not RadiationRadialWallCore:
            raise TypeError("Retain the shared radiation-to-wall core receipt")
        self.radiation_field.require_current()
        self.core_receipt.require_current()
        self.radial_trace.require_current()
        if (self.core_receipt.radial_trace is not self.radial_trace
                or self.core_receipt.surface_projection_factor != self.surface_projection_factor
                or self.core_receipt.surface_projection_evidence_id != self.surface_projection_evidence_id):
            raise ValueError("Shared radial-wall core receipt differs from the source facade")
        if (isinstance(self.receiver_index, bool) or not isinstance(self.receiver_index, int)
                or not 0 <= self.receiver_index < len(self.radiation_field.receiver_points_m)):
            raise ValueError("The retained receiver index is outside the source radiation field")
        if (self.radial_trace.incident.source_owner is not self.radiation_field
                or self.radial_trace.incident.clock_id != self.radiation_field.source.window.clock_id
                or self.receiver_frame_id != self.radiation_field.policy.geometry_frame_id
                or self.receiver_point_m != tuple(
                    float(v) for v in
                    self.radiation_field.receiver_points_m[self.receiver_index]
                )
                or self.radial_trace.absorptivity != self.absorptivity
                or self.radial_trace.incident.incident_flux_w_m2[0]
                    != self.radiation_field.incident_flux_w_m2[self.receiver_index]
                    *self.surface_projection_factor
                or not self.surface_projection_evidence_id.strip()
                or not np.array_equal(self.radial_trace.incident.edges_s,
                    np.asarray([self.radiation_field.source.window.start_s,
                                self.radiation_field.source.window.end_s]))
                or self.radial_trace.geometry_evidence_id != self.geometry_evidence_id
                or self.radial_trace.evidence_id != self.application_evidence_id
                or self.radial_trace.uniform_circumference_evidence_id
                    != self.uniform_circumference_evidence_id):
            raise ValueError("Radial wall response no longer matches its selected radiation receiver/boundary")
        expected = recorded_content_sha256((
            id(self.radiation_field), self.receiver_index, self.receiver_point_m,
            self.receiver_frame_id, self.surface_projection_factor,
            self.surface_projection_evidence_id, self.absorptivity, self.geometry_evidence_id,
            self.application_evidence_id, self.uniform_circumference_evidence_id,
            self.radial_trace, self.core_receipt,
        ))
        if expected != self._seal:
            raise ValueError("HyRAM radiation-to-wall response receipt changed after issue")
        return self


def run_jet_radiation_radial_wall(
    field, receiver_index: int, *, inner_radius_m, outer_radius_m, length_m,
    material, initial_temperature_k, inner_boundary, absorptivity,
    surface_projection_factor: float, surface_projection_evidence_id: str,
    geometry_evidence_id: str, application_evidence_id: str,
    uniform_circumference_evidence_id: str, cells=40,
    relative_tolerance=1e-7, absolute_tolerance_k=1e-7,
    maximum_step_s, energy_tolerance_j,
) -> JetRadiationRadialWallTrace:
    """Run the shared radial wall core from one admitted HyRAM receiver."""
    from .jet_radiation import JetRadiationField, incident_history_from_jet_radiation
    from ..core import finite

    if type(field) is not JetRadiationField:
        raise TypeError("Use an original owner-issued HyRAM radiation field")
    field.require_current()
    if isinstance(receiver_index, bool) or not isinstance(receiver_index, int) or not (
            0 <= receiver_index < len(field.receiver_points_m)):
        raise ValueError("Select exactly one existing global receiver point")
    projection = finite(surface_projection_factor, "surface projection factor")
    if not 0 <= projection <= 1:
        raise ValueError("Surface projection factor must be in [0, 1]")
    for value, name in ((geometry_evidence_id, "geometry"),
                        (application_evidence_id, "application"),
                        (uniform_circumference_evidence_id, "uniform circumference"),
                        (surface_projection_evidence_id, "surface projection")):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {name} evidence is required")
    history = incident_history_from_jet_radiation(
        field, receiver_index, start_s=field.source.window.start_s,
        end_s=field.source.window.end_s, clock_id=field.source.window.clock_id,
        evidence_id=application_evidence_id + ":incident-history",
        steady_projection_evidence_id=application_evidence_id + ":steady-window")
    core = run_radiation_radial_wall_core(
        history, surface_projection_factor=projection,
        surface_projection_evidence_id=surface_projection_evidence_id,
        absorptivity=absorptivity, inner_radius_m=inner_radius_m,
        outer_radius_m=outer_radius_m, length_m=length_m, material=material,
        initial_temperature_k=initial_temperature_k, inner_boundary=inner_boundary,
        geometry_evidence_id=geometry_evidence_id,
        application_evidence_id=application_evidence_id,
        uniform_circumference_evidence_id=uniform_circumference_evidence_id,
        cells=cells, relative_tolerance=relative_tolerance,
        absolute_tolerance_k=absolute_tolerance_k, maximum_step_s=maximum_step_s,
        energy_tolerance_j=energy_tolerance_j)
    radial = core.radial_trace
    result = JetRadiationRadialWallTrace(
        field, receiver_index,
        tuple(float(v) for v in field.receiver_points_m[receiver_index]),
        field.policy.geometry_frame_id, projection, surface_projection_evidence_id,
        float(absorptivity), geometry_evidence_id, application_evidence_id,
        uniform_circumference_evidence_id, radial, core, "")
    result = replace(result, _seal=recorded_content_sha256((
        id(field), receiver_index, result.receiver_point_m, result.receiver_frame_id,
        projection, surface_projection_evidence_id, result.absorptivity,
        geometry_evidence_id, application_evidence_id,
        uniform_circumference_evidence_id, radial, core)))
    field.require_current()
    return result.require_current()


__all__ = ["JetRadiationRadialWallTrace", "run_jet_radiation_radial_wall"]
