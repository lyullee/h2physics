"""Bound a caller-described rigid fragment flight by existing cylinder strain energy."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core import finite
from ..fragment_energy_bound import (
    FragmentElasticEnergyBound,
    bound_fragment_speed_from_elastic_energy,
)
from ..fragment_trajectory import (
    FragmentFlightEnvironment,
    FragmentFlightResult,
    FragmentFlightSettings,
    FragmentLaunch,
    integrate_fragment_flight,
)
from ..materials.elastic_cylinder import CylinderGeometry, CylinderPressureLoad
from .result_provenance import recorded_content_sha256

_PENDING = set()


def _receipt_content(value):
    return recorded_content_sha256((
        id(value.energy_bound), value.flight, value.geometry, value.pressure_load,
        value.cylinder_length_m, value.youngs_modulus_pa, value.poisson_ratio,
        value.material_evidence_id, value.fragment_energy_fraction,
        value.event_time_s, value.clock_id, value.event_evidence_id,
        value.launch_mapping_evidence_id,
    ))


@dataclass(frozen=True, slots=True)
class ElasticBoundFragmentFlight:
    """Receipt linking an elastic speed ceiling to one conditional trajectory."""

    energy_bound: FragmentElasticEnergyBound = field(repr=False, compare=False)
    flight: FragmentFlightResult = field(repr=False, compare=False)
    geometry: CylinderGeometry = field(repr=False, compare=False)
    pressure_load: CylinderPressureLoad = field(repr=False, compare=False)
    cylinder_length_m: float
    youngs_modulus_pa: float
    poisson_ratio: float
    material_evidence_id: str
    fragment_energy_fraction: float
    event_time_s: float
    clock_id: str
    event_evidence_id: str
    launch_mapping_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use run_elastic_bound_fragment_flight to issue this receipt")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_seal", _receipt_content(self))

    def require_current(self):
        if (type(self.energy_bound) is not FragmentElasticEnergyBound
                or type(self.flight) is not FragmentFlightResult
                or type(self.geometry) is not CylinderGeometry
                or type(self.pressure_load) is not CylinderPressureLoad):
            raise TypeError("Retain the actual elastic bound and original typed flight inputs")
        replay = bound_fragment_speed_from_elastic_energy(
            self.geometry, self.pressure_load,
            cylinder_length_m=self.cylinder_length_m,
            youngs_modulus_pa=self.youngs_modulus_pa,
            poisson_ratio=self.poisson_ratio,
            fragment_mass_kg=self.flight.launch.mass_kg,
            fragment_energy_fraction=self.fragment_energy_fraction,
            fragment_id=self.flight.launch.fragment_id,
            material_evidence_id=self.material_evidence_id,
        )
        self.flight.require_current()
        launch, settings, environment = self.flight.launch, self.flight.settings, self.flight.environment
        speed_sq = float(launch.velocity_m_s @ launch.velocity_m_s)
        kinetic = 0.5*launch.mass_kg*speed_sq
        if (replay != self.energy_bound
                or launch.fragment_id != self.energy_bound.fragment_id
                or launch.mass_kg != self.energy_bound.fragment_mass_kg
                or launch.frame_id != environment.frame_id
                or settings.clock_id != self.clock_id
                or settings.time_s[0] != self.event_time_s
                or settings.time_s[0] != self.flight.time_s[0]
                or speed_sq > self.energy_bound.maximum_speed_m_s**2*(1.+1e-12)
                or kinetic > self.energy_bound.available_fragment_energy_j*(1.+1e-12)
                or not self.event_evidence_id.strip()
                or not self.launch_mapping_evidence_id.strip()
                or self._seal != _receipt_content(self)):
            raise ValueError("Fragment flight exceeds or lost its original elastic-bound event contract")
        return self


def run_elastic_bound_fragment_flight(
    geometry: CylinderGeometry,
    pressure_load: CylinderPressureLoad,
    *,
    cylinder_length_m: float,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    fragment_energy_fraction: float,
    material_evidence_id: str,
    launch: FragmentLaunch,
    environment: FragmentFlightEnvironment,
    settings: FragmentFlightSettings,
    event_time_s: float,
    event_evidence_id: str,
    launch_mapping_evidence_id: str,
) -> ElasticBoundFragmentFlight:
    """Run existing flight dynamics only after an explicit energy-ceiling gate.

    Vessel geometry/load and fragment mass determine only the existing
    linear-elastic speed envelope. The caller supplies fragment orientation-free
    launch position/velocity, launch mapping evidence, environment and flight
    clock. This does not predict vessel failure, fragmentation or launch state.
    """
    if type(geometry) is not CylinderGeometry or type(pressure_load) is not CylinderPressureLoad:
        raise TypeError("Supply the existing typed cylinder geometry and pressure load")
    if (type(launch) is not FragmentLaunch
            or type(environment) is not FragmentFlightEnvironment
            or type(settings) is not FragmentFlightSettings):
        raise TypeError("Supply original typed fragment, environment and flight settings")
    event_time = finite(event_time_s, "event_time_s")
    if not all(isinstance(value, str) and value.strip() for value in (
            material_evidence_id, event_evidence_id, launch_mapping_evidence_id)):
        raise ValueError("Material, event and cylinder-to-launch evidence are required")
    if (launch.frame_id != environment.frame_id
            or settings.clock_id.strip() == ""
            or settings.time_s[0] != event_time):
        raise ValueError("Launch, environment and exact event time/frame must align")
    bound = bound_fragment_speed_from_elastic_energy(
        geometry, pressure_load, cylinder_length_m=cylinder_length_m,
        youngs_modulus_pa=youngs_modulus_pa, poisson_ratio=poisson_ratio,
        fragment_mass_kg=launch.mass_kg,
        fragment_energy_fraction=fragment_energy_fraction,
        fragment_id=launch.fragment_id, material_evidence_id=material_evidence_id,
    )
    launch_speed_sq = float(launch.velocity_m_s @ launch.velocity_m_s)
    launch_energy = 0.5*launch.mass_kg*launch_speed_sq
    if (launch_speed_sq > bound.maximum_speed_m_s**2*(1.+1e-12)
            or launch_energy > bound.available_fragment_energy_j*(1.+1e-12)):
        raise ValueError("Caller launch state exceeds the declared elastic fragment-energy ceiling")
    flight = integrate_fragment_flight(launch, environment, settings)
    flight.require_current()
    token = object()
    _PENDING.add(token)
    try:
        receipt = ElasticBoundFragmentFlight(
            bound, flight, geometry, pressure_load, cylinder_length_m,
            youngs_modulus_pa, poisson_ratio, material_evidence_id.strip(),
            fragment_energy_fraction, event_time, settings.clock_id,
            event_evidence_id.strip(), launch_mapping_evidence_id.strip(), token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    return receipt.require_current()


__all__ = ["ElasticBoundFragmentFlight", "run_elastic_bound_fragment_flight"]

