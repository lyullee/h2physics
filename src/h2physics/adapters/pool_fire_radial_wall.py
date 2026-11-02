"""Source-bound pool-fire receiver radiation to the shared radial-wall core."""

from dataclasses import dataclass, field

from .pool_fire import PoolFireTrace
from .thermal_target import incident_history_from_pool_fire
from .radiation_radial_wall_core import (
    RadiationRadialWallCore,
    run_radiation_radial_wall_core,
)


@dataclass(frozen=True, slots=True)
class PoolFireRadialWallTrace:
    fire: PoolFireTrace = field(repr=False, compare=False)
    receptor_id: str
    surface_projection_evidence_id: str
    core_receipt: RadiationRadialWallCore
    _identity: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.fire) is not PoolFireTrace or type(self.core_receipt) is not RadiationRadialWallCore:
            raise TypeError("Retain the original pool-fire trace and shared wall receipt")
        if not isinstance(self.receptor_id, str) or not self.receptor_id.strip():
            raise ValueError("Retain the selected pool-fire receptor identity")
        if not isinstance(self.surface_projection_evidence_id, str) or not self.surface_projection_evidence_id.strip():
            raise ValueError("Retain caller evidence for receptor-to-wall surface projection")
        self.require_current()
        object.__setattr__(self, "_identity", (
            self.fire, self.receptor_id, self.surface_projection_evidence_id,
            self.core_receipt,
        ))

    @property
    def radial_trace(self):
        return self.core_receipt.radial_trace

    @property
    def incident_history(self):
        return self.core_receipt.incident_history

    @property
    def projected_history(self):
        return self.core_receipt.projected_history

    def require_current(self):
        self.fire.require_current()
        self.core_receipt.require_current()
        expected = incident_history_from_pool_fire(
            self.fire, self.receptor_id,
            evidence_id=self.surface_projection_evidence_id,
        )
        source = self.core_receipt.incident_history
        if (source.source_owner is not self.fire
                or source.clock_id != expected.clock_id
                or source.frame_id != expected.frame_id
                or source.source_id != expected.source_id
                or source.evidence_id != expected.evidence_id
                or not (source.edges_s == expected.edges_s).all()
                or not (source.incident_flux_w_m2 == expected.incident_flux_w_m2).all()):
            raise ValueError("Pool-fire radial boundary is detached from the selected receptor trace")
        if (self._identity and any(current is not original for current, original in zip(
                (self.fire, self.receptor_id, self.surface_projection_evidence_id,
                 self.core_receipt), self._identity, strict=True))):
            raise ValueError("Pool-fire radial wall receipt lost its original binding")
        self.fire.require_current()
        self.core_receipt.require_current()
        return self


def run_pool_fire_radial_wall(
    fire: PoolFireTrace,
    receptor_id: str,
    *,
    surface_projection_factor: float,
    surface_projection_evidence_id: str,
    inner_radius_m: float,
    outer_radius_m: float,
    length_m: float,
    material,
    initial_temperature_k,
    inner_boundary,
    absorptivity: float,
    geometry_evidence_id: str,
    evidence_id: str,
    uniform_circumference_evidence_id: str,
    maximum_step_s: float,
    energy_tolerance_j: float,
    cells: int = 40,
    relative_tolerance: float = 1e-7,
    absolute_tolerance_k: float = 1e-7,
) -> PoolFireRadialWallTrace:
    """Project one admitted pool-fire receptor onto a caller-identified wall.

    Receptor heat flux is retained in W/m². The dimensionless surface factor,
    wall geometry/material and radial-uniformity premise are caller-owned. No
    cylinder view factor, obstruction, fire evolution or damage model is added.
    """
    if type(fire) is not PoolFireTrace:
        raise TypeError("Supply an original owner-issued PoolFireTrace")
    fire.require_current()
    history = incident_history_from_pool_fire(
        fire, receptor_id, evidence_id=surface_projection_evidence_id,
    )
    core = run_radiation_radial_wall_core(
        history, surface_projection_factor=surface_projection_factor,
        surface_projection_evidence_id=surface_projection_evidence_id,
        absorptivity=absorptivity, inner_radius_m=inner_radius_m,
        outer_radius_m=outer_radius_m, length_m=length_m, material=material,
        initial_temperature_k=initial_temperature_k, inner_boundary=inner_boundary,
        geometry_evidence_id=geometry_evidence_id, application_evidence_id=evidence_id,
        uniform_circumference_evidence_id=uniform_circumference_evidence_id,
        maximum_step_s=maximum_step_s, energy_tolerance_j=energy_tolerance_j,
        cells=cells, relative_tolerance=relative_tolerance,
        absolute_tolerance_k=absolute_tolerance_k,
    )
    fire.require_current()
    return PoolFireRadialWallTrace(
        fire, receptor_id, surface_projection_evidence_id, core,
    ).require_current()


__all__ = ["PoolFireRadialWallTrace", "run_pool_fire_radial_wall"]
