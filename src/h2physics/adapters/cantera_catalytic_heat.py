"""Heat-duty view of the original Cantera catalytic fixed-wall energy ledger."""

from dataclasses import dataclass

import numpy as np

from .thermal_utilities import HeatComponent, HeatSnapshot, HeatWindow


@dataclass(frozen=True, slots=True)
class CanteraCatalyticWallHeatAdapter:
    """Project audited native wall heat into the existing finite utility ledger."""

    identifier: str = "original-cantera-catalytic-fixed-wall-heat"

    def snapshot(self, source, window: HeatWindow) -> HeatSnapshot:
        from .cantera_surface_reactor import CatalyticSurfaceTrace

        if type(source) is not CatalyticSurfaceTrace:
            raise TypeError("Use the original owner-issued Cantera catalytic surface trace")
        if type(window) is not HeatWindow:
            raise TypeError("Use an explicit exact-sample thermal reporting window")
        source.require_current()
        if source.thermal_boundary is None:
            raise ValueError("An imposed isothermal/thermostat trace has no native wall-duty series")
        if window.clock_id != source.clock_id:
            raise ValueError("Thermal reporting and native reactor clocks differ")
        times = np.asarray([point.time_s for point in source.points], dtype=float)
        start = np.flatnonzero(times == window.start_s)
        end = np.flatnonzero(times == window.end_s)
        if len(start) != 1 or len(end) != 1 or start[0] >= end[0]:
            raise ValueError("Select increasing exact accepted native output samples")
        points = source.points[int(start[0]):int(end[0])+1]
        if any(point.wall_heat_integral_into_j is None or point.wall_heat_rate_into_w is None
               for point in points):
            raise ValueError("Every selected sample must retain the native wall-energy ledger")
        edges = np.asarray([point.time_s for point in points], dtype=float)
        cumulative = np.asarray([point.wall_heat_integral_into_j for point in points], dtype=float)
        heat = np.diff(cumulative)
        if (len(heat) != len(edges)-1 or not np.all(np.isfinite(heat))
                or not np.all(np.diff(edges) > 0)):
            raise ValueError("Native wall heat does not map to finite ordered interval duties")
        boundary_id = "catalytic-fixed-wall:" + source.thermal_boundary.evidence_id
        basis_id = "native-wall-energy-j-into-reactor:" + source.mechanism_basis.identifier
        snapshot = HeatSnapshot(source, window, source.evidence_id, boundary_id, basis_id,
            edges, heat, (HeatComponent(source.owner, "catalytic-fixed-wall"),),
            tuple((left.temperature_k, right.temperature_k)
                  for left, right in zip(points[:-1], points[1:], strict=True)),
            "external-device-heat",
            (window.evidence_id, source.evidence_id, source.thermal_boundary.evidence_id),
            (source.owner, source.native_wall, source.native_reservoir, source.native_network,
             *points),
            "actual-native-fixed-wall-integral-into-catalytic-reactor; external wall is imposed")
        source.require_current()
        return snapshot
