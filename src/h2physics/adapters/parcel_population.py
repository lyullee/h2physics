"""Explicit weighted parcel populations using the existing isolated-flight solver.

Population sizes, launch positions and velocities are caller inputs. No breakup,
entrainment, size distribution or deposited fraction is inferred.
"""

from dataclasses import dataclass, field
from math import fsum, isclose
from types import MappingProxyType

from ..core import finite
from .droplet_transport import ParcelInitialFlash, ParcelTrace, SaturatedParcelFlight
from .result_provenance import recorded_content_sha256


def _owner_binding(owner):
    return (id(owner.properties), id(owner.boundary), repr(owner.boundary),
            id(owner.boiling_heat), owner.force_approximation_evidence_id,
            owner.pressure_pa, id(owner.liquid), repr(owner.liquid),
            id(owner.vapor), repr(owner.vapor), owner.latent_heat_j_kg)


def _trace_binding(groups_and_traces):
    return tuple((id(group), repr(group), id(trace), id(trace.boundary),
                  recorded_content_sha256(trace))
                 for group, trace in groups_and_traces)


@dataclass(frozen=True, slots=True)
class ParcelPopulationGroup:
    group_id: str
    count: int
    mass_per_parcel_kg: float
    position_m: tuple
    velocity_m_s: tuple
    distribution_evidence_id: str

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.group_id, self.distribution_evidence_id)):
            raise ValueError("Declare population identity and distribution evidence")
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("Parcel count must be a positive integer")
        finite(self.mass_per_parcel_kg, "mass per parcel", positive=True)
        for name in ("position_m", "velocity_m_s"):
            values = tuple(finite(value, name) for value in getattr(self, name))
            if len(values) != 3:
                raise ValueError("Launch vectors need three SI components")
            object.__setattr__(self, name, values)

    @property
    def total_mass_kg(self):
        return self.count*self.mass_per_parcel_kg


class ParcelPopulationError(RuntimeError):
    def __init__(self, cause, group, completed):
        self.cause = cause
        self.group = group
        self.completed = tuple(completed)
        super().__init__(f"Parcel population group {group.group_id!r} failed")


@dataclass(frozen=True, slots=True)
class ParcelPopulationResult:
    initial_flash: ParcelInitialFlash
    owner: SaturatedParcelFlight
    groups_and_traces: tuple
    distribution_evidence_id: str
    clock_id: str
    frame_id: str
    start_s: float
    end_s: float
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def require_current(self):
        if not self._binding or self._binding != (
                id(self.initial_flash), id(self.owner), _owner_binding(self.owner),
                repr(self.initial_flash), _trace_binding(self.groups_and_traces),
                self.distribution_evidence_id, self.clock_id, self.frame_id,
                self.start_s, self.end_s):
            raise ValueError("Parcel population lost its original states, owner or trace ledger")
        self.initial_flash.__post_init__()
        for _, trace in self.groups_and_traces:
            trace.require_current()
        return self

    @property
    def evaporated_mass_kg(self):
        self.require_current()
        return fsum(group.count*trace.evaporated_mass_kg
                    for group, trace in self.groups_and_traces)

    @property
    def remaining_liquid_mass_kg(self):
        self.require_current()
        return fsum(group.count*trace.states[-1].mass_kg
                    for group, trace in self.groups_and_traces)

    @property
    def incident_liquid_mass_kg(self):
        self.require_current()
        return fsum(group.count*trace.states[-1].mass_kg
                    for group, trace in self.groups_and_traces
                    if trace.end_reason == "incident_ground_crossing")

    @property
    def total_vapor_mass_kg(self):
        return self.initial_flash.flashed_vapor_mass_kg+self.evaporated_mass_kg

    @property
    def mass_residual_kg(self):
        return (self.initial_flash.total_release_mass_kg-self.total_vapor_mass_kg
                -self.remaining_liquid_mass_kg)


def run_parcel_population(initial_flash, owner, groups, *, distribution_evidence_id,
                          flight_options):
    """Run one representative flight per explicitly weighted identical group.

    All groups share the owner's clock/frame and one start/end window. Supply
    ordinary flight integration options explicitly; mass and launch vectors come
    from each group. Incident liquid remains an impact boundary, not deposition.
    """
    if type(initial_flash) is not ParcelInitialFlash or type(owner) is not SaturatedParcelFlight:
        raise TypeError("Supply the original initial flash and isolated-flight owner")
    initial_flash.__post_init__()
    if not isinstance(distribution_evidence_id, str) or not distribution_evidence_id.strip():
        raise ValueError("Declare evidence for the population approximation")
    groups = tuple(groups)
    if not groups or any(type(group) is not ParcelPopulationGroup for group in groups):
        raise TypeError("Supply explicit parcel population groups")
    if len({group.group_id for group in groups}) != len(groups):
        raise ValueError("Population group identities must be unique")
    if not isclose(fsum(group.total_mass_kg for group in groups),
                   initial_flash.launch_liquid_mass_kg, rel_tol=1e-12, abs_tol=1e-15):
        raise ValueError("Population liquid mass must account for all post-flash liquid")
    owner.properties.basis.require_compatible(initial_flash.saturated_liquid_state.basis)
    if owner.pressure_pa != initial_flash.saturated_liquid_state.pressure_pa:
        raise ValueError("Flight saturation pressure must equal the downstream flash pressure")
    if (owner.liquid != initial_flash.saturated_liquid_state
            or owner.vapor != initial_flash.saturated_vapor_state):
        raise ValueError("Flight phase endpoints must equal the retained flash endpoints")
    options = MappingProxyType(dict(flight_options))
    if {"position_m", "velocity_m_s", "mass_kg"} & options.keys():
        raise ValueError("Population groups own the launch vectors and per-parcel mass")
    completed = []
    start = finite(options["start_s"], "start_s")
    end = finite(options["end_s"], "end_s")
    binding = _owner_binding(owner)
    flash_binding = repr(initial_flash)
    launch_binding = recorded_content_sha256((groups, options))
    for group in groups:
        try:
            if (_owner_binding(owner) != binding or repr(initial_flash) != flash_binding
                    or recorded_content_sha256((groups, options)) != launch_binding):
                raise ValueError("Population owner or initial flash changed during grouped flight")
            trace = owner.run(position_m=group.position_m, velocity_m_s=group.velocity_m_s,
                              mass_kg=group.mass_per_parcel_kg, **options)
            if (_owner_binding(owner) != binding or repr(initial_flash) != flash_binding
                    or recorded_content_sha256((groups, options)) != launch_binding):
                raise ValueError("Population owner or initial flash changed during grouped flight")
            if type(trace) is not ParcelTrace or trace.boundary is not owner.boundary or not trace.states:
                raise TypeError("Retain typed native flight trace on the common population boundary")
            first, last = trace.states[0], trace.states[-1]
            if any(b.time_s <= a.time_s for a, b in zip(trace.states, trace.states[1:])):
                raise ValueError("Representative flight accepted clock must be strictly increasing")
            if (first.time_s != start or not start <= last.time_s <= end
                    or first.mass_kg != group.mass_per_parcel_kg
                    or first.position_m != group.position_m or first.velocity_m_s != group.velocity_m_s):
                raise ValueError("Representative flight differs from its population launch contract")
            finite(trace.evaporated_mass_kg, "evaporated mass")
            if (trace.evaporated_mass_kg < 0. or last.mass_kg < 0.
                    or not isclose(last.mass_kg+trace.evaporated_mass_kg, first.mass_kg,
                                   abs_tol=1e-15, rel_tol=1e-12)
                    or not isclose(last.mass_kg+trace.evaporated_mass_kg-first.mass_kg,
                                   trace.mass_residual_kg, abs_tol=1e-15, rel_tol=1e-12)):
                raise ValueError("Representative parcel mass ledger is inconsistent")
        except Exception as cause:
            raise ParcelPopulationError(cause, group, completed) from cause
        completed.append((group, trace))
    result = ParcelPopulationResult(initial_flash, owner, tuple(completed), distribution_evidence_id,
                                    owner.boundary.clock_id, owner.boundary.frame_id, start, end)
    object.__setattr__(result, "_binding", (
        id(initial_flash), id(owner), binding, repr(initial_flash), _trace_binding(result.groups_and_traces),
        distribution_evidence_id, result.clock_id, result.frame_id, start, end))
    return result.require_current()
