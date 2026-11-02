"""Bind native HELPR initiation to an explicitly conditional fragment-flight case."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core import Origin, finite
from .vessel_failure import VesselFailurePrediction
from ..fragment_trajectory import FragmentFlightEnvironment, FragmentFlightSettings, FragmentLaunch
from ..materials.elastic_cylinder import CylinderGeometry, CylinderPressureLoad
from .elastic_fragment_flight import (
    ElasticBoundFragmentFlight,
    run_elastic_bound_fragment_flight,
)
from .result_provenance import recorded_content_sha256

_PENDING = set()


def _content(value):
    return recorded_content_sha256((
        id(value.prediction), value.bound_flight, value.geometry, value.pressure_load,
        value.shell_to_cylinder_evidence_id, value.end_condition,
        value.cylinder_length_m, value.youngs_modulus_pa, value.poisson_ratio,
        value.material_evidence_id, value.launch_mapping_evidence_id,
    ))


@dataclass(frozen=True, slots=True)
class VesselFailureFragmentFlight:
    """Source-bound conditional flight following one issued HELPR initiation."""

    prediction: VesselFailurePrediction = field(repr=False, compare=False)
    bound_flight: ElasticBoundFragmentFlight = field(repr=False, compare=False)
    geometry: CylinderGeometry = field(repr=False, compare=False)
    pressure_load: CylinderPressureLoad = field(repr=False, compare=False)
    shell_to_cylinder_evidence_id: str
    end_condition: str
    cylinder_length_m: float
    youngs_modulus_pa: float
    poisson_ratio: float
    material_evidence_id: str
    launch_mapping_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use run_vessel_failure_fragment_flight to issue this receipt")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_seal", _content(self))

    @property
    def flight(self):
        return self.bound_flight.flight

    def require_current(self):
        if (type(self.prediction) is not VesselFailurePrediction
                or type(self.bound_flight) is not ElasticBoundFragmentFlight
                or type(self.geometry) is not CylinderGeometry
                or type(self.pressure_load) is not CylinderPressureLoad):
            raise TypeError("Retain the issued HELPR event and existing typed fragment-flight receipt")
        self.prediction.require_current()
        event = self.prediction.initiation
        if event is None or not event.failed:
            raise ValueError("This chain requires an issued failure-initiation event")
        context, flaw, loading = self.prediction.history.context, self.prediction.geometry, event.loading
        outer = flaw.outer_diameter_m/2.0
        inner = outer-flaw.wall_thickness_m
        expected_geometry_id = f"{context.vessel_id}:{flaw.geometry_id}:elastic-bound-cylinder"
        expected_load_id = f"{context.vessel_id}:{context.clock_id}:{loading.time_s}:failure-pressure-difference"
        self.bound_flight.require_current()
        launch, settings, environment = (
            self.flight.launch, self.flight.settings, self.flight.environment)
        if (self.geometry.geometry_id != expected_geometry_id
                or self.geometry.inner_radius_m != inner
                or self.geometry.outer_radius_m != outer
                or self.geometry.end_condition != self.end_condition
                or self.pressure_load.load_id != expected_load_id
                or self.pressure_load.internal_pressure_pa != loading.pressure_difference_pa
                or self.pressure_load.external_pressure_pa != 0.0
                or launch.frame_id != context.frame_id
                or environment.frame_id != context.frame_id
                or settings.clock_id != context.clock_id
                or settings.time_s[0] != loading.time_s
                or self.bound_flight.event_time_s != loading.time_s
                or self.bound_flight.geometry is not self.geometry
                or self.bound_flight.pressure_load is not self.pressure_load
                or self.bound_flight.event_evidence_id != self.prediction.criterion_evidence_id
                or self.bound_flight.launch_mapping_evidence_id != self.launch_mapping_evidence_id
                or self.bound_flight.cylinder_length_m != self.cylinder_length_m
                or self.bound_flight.youngs_modulus_pa != self.youngs_modulus_pa
                or self.bound_flight.poisson_ratio != self.poisson_ratio
                or self.bound_flight.material_evidence_id != self.material_evidence_id
                or not self.shell_to_cylinder_evidence_id.strip()
                or not self.material_evidence_id.strip()
                or not self.launch_mapping_evidence_id.strip()
                or self._seal != _content(self)):
            raise ValueError("HElPR initiation and conditional flight lost their declared source/clock/basis mapping")
        return self


def run_vessel_failure_fragment_flight(
    prediction: VesselFailurePrediction,
    *,
    end_condition: str,
    cylinder_length_m: float,
    shell_to_cylinder_evidence_id: str,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    fragment_energy_fraction: float,
    material_evidence_id: str,
    launch: FragmentLaunch,
    environment: FragmentFlightEnvironment,
    settings: FragmentFlightSettings,
    launch_mapping_evidence_id: str,
) -> VesselFailureFragmentFlight:
    """Project HELPR's failed load to the existing elastic-energy/flight chain.

    HELPR supplies the exact owner-issued initiation time and differential
    pressure. The caller evidences the shell-to-long-cylinder geometry mapping,
    end support, length, elastic constants, fragment mass/energy share, location
    and launch vector. No failure opening, fragmentation or launch state is
    computed by this facade.
    """
    if type(prediction) is not VesselFailurePrediction:
        raise TypeError("Supply an original owner-issued HELPR VesselFailurePrediction")
    prediction.require_current()
    event = prediction.initiation
    if event is None or not event.failed:
        raise ValueError("No failure initiation is present in this prediction")
    context, flaw, loading = prediction.history.context, prediction.geometry, event.loading
    if end_condition not in {"closed", "open"}:
        raise ValueError("Declare the mapped cylinder end condition explicitly")
    for value, name in (
        (shell_to_cylinder_evidence_id, "shell-to-cylinder geometry mapping"),
        (material_evidence_id, "elastic property basis"),
        (launch_mapping_evidence_id, "failure-event to caller launch mapping"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {name} evidence")
    length = finite(cylinder_length_m, "mapped cylinder length", positive=True)
    outer = flaw.outer_diameter_m/2.0
    inner = outer-flaw.wall_thickness_m
    if inner <= 0:
        raise ValueError("HELPR shell dimensions do not define a positive cylinder bore")
    geometry = CylinderGeometry(
        inner, outer, end_condition,
        f"{context.vessel_id}:{flaw.geometry_id}:elastic-bound-cylinder",
    )
    pressure = CylinderPressureLoad(
        loading.pressure_difference_pa, 0.0,
        f"{context.vessel_id}:{context.clock_id}:{loading.time_s}:failure-pressure-difference",
        Origin(context.origin),
    )
    if (type(launch) is not FragmentLaunch
            or type(environment) is not FragmentFlightEnvironment
            or type(settings) is not FragmentFlightSettings):
        raise TypeError("Supply typed caller launch, environment and flight clock")
    if (launch.frame_id != context.frame_id or environment.frame_id != context.frame_id
            or settings.clock_id != context.clock_id
            or settings.time_s[0] != loading.time_s):
        raise ValueError("HELPR failure, launch, environment and first flight sample must share frame/clock/time")
    flight = run_elastic_bound_fragment_flight(
        geometry, pressure, cylinder_length_m=length,
        youngs_modulus_pa=youngs_modulus_pa, poisson_ratio=poisson_ratio,
        fragment_energy_fraction=fragment_energy_fraction,
        material_evidence_id=material_evidence_id,
        launch=launch, environment=environment, settings=settings,
        event_time_s=loading.time_s,
        event_evidence_id=prediction.criterion_evidence_id,
        launch_mapping_evidence_id=launch_mapping_evidence_id,
    )
    token = object()
    _PENDING.add(token)
    try:
        result = VesselFailureFragmentFlight(
            prediction, flight, geometry, pressure,
            shell_to_cylinder_evidence_id.strip(), end_condition, length,
            youngs_modulus_pa, poisson_ratio, material_evidence_id.strip(),
            launch_mapping_evidence_id.strip(), token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    prediction.require_current()
    return result.require_current()


__all__ = ["VesselFailureFragmentFlight", "run_vessel_failure_fragment_flight"]


