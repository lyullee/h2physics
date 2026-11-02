"""Sequence unit-count population contacts through one finite surface owner.

This reuses the existing flight and impact solvers. It does not multiply a
representative trajectory into multiple contacts or model simultaneous impacts.
"""

from dataclasses import dataclass, field
from math import fsum

from .droplet_impact import FiniteSurfaceImpact, SurfaceImpactTrace
from .parcel_population import ParcelPopulationResult

_PENDING_SEQUENCE_ISSUERS: set[object] = set()


def _incident_pairs(population):
    return tuple((group, trace) for group, trace in population.groups_and_traces
                 if trace.end_reason == "incident_ground_crossing")


def _sequence_signature(population, owner, result, pairs):
    return (
        id(population), id(owner), id(result), id(result.patch), id(result.closure),
        id(result.native_property_owner),
        tuple((id(group), id(trace), trace.states[-1].time_s) for group, trace in pairs),
        tuple(id(step) for step in result.steps),
        result.total_incident_mass_kg, result.deposited_mass_kg,
        result.rebound_mass_kg, result.vapor_mass_kg,
        result.mass_residual_kg, result.total_energy_residual_j,
        result.final_wall_temperature_k, result.regime_prediction_solved,
        result.surface_spreading_solved, result.simultaneous_pool_continuation_solved,
        result.measured_hydrogen_validation, result.status,
    )


def _issue_sequence(**values):
    token = object()
    _PENDING_SEQUENCE_ISSUERS.add(token)
    try:
        return PopulationImpactSequence(**values, _issuer=token)
    except Exception:
        _PENDING_SEQUENCE_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class PopulationImpactSequence:
    """Accepted distinct parcel contacts retaining one shared wall history."""

    population: ParcelPopulationResult = field(repr=False, compare=False)
    impact_owner: FiniteSurfaceImpact = field(repr=False, compare=False)
    impact_result: SurfaceImpactTrace = field(repr=False, compare=False)
    group_ids: tuple[str, ...]
    event_times_s: tuple[float, ...]
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_SEQUENCE_ISSUERS:
            raise TypeError("Impact sequences are issued only by the owner-composition function")
        _PENDING_SEQUENCE_ISSUERS.remove(self._issuer)
        if (type(self.population) is not ParcelPopulationResult
                or type(self.impact_owner) is not FiniteSurfaceImpact
                or type(self.impact_result) is not SurfaceImpactTrace):
            raise TypeError("Retain the original population, finite impact owner and returned trace")
        self.population.require_current()
        self.impact_result.require_current()
        pairs = _incident_pairs(self.population)
        expected_ids = tuple(group.group_id for group, _ in sorted(
            pairs, key=lambda pair: pair[1].states[-1].time_s))
        expected_times = tuple(trace.states[-1].time_s for _, trace in sorted(
            pairs, key=lambda pair: pair[1].states[-1].time_s))
        if (not pairs or any(group.count != 1 for group, _ in pairs)
                or len(set(expected_times)) != len(expected_times)
                or self.group_ids != expected_ids or self.event_times_s != expected_times):
            raise ValueError("Retain all distinct unit-count incident groups in event-time order")
        if len(self.impact_result.steps) != len(pairs):
            raise ValueError("One original finite-wall step is required for each incident parcel")
        for step, (group, trace) in zip(self.impact_result.steps, sorted(
                pairs, key=lambda pair: pair[1].states[-1].time_s), strict=True):
            self.impact_owner.require_original_step(step)
            if (step.context.incident_trace is not trace
                    or step.context.incident.mass_kg != group.mass_per_parcel_kg):
                raise ValueError("Finite-wall sequence step lost its original unit-count parcel")
        if (self.impact_result.patch is not self.impact_owner.patch
                or self.impact_result.closure is not self.impact_owner.closure
                or self.impact_result.native_property_owner is not self.impact_owner.properties):
            raise ValueError("Impact sequence returned from a different native owner definition")
        expected_incoming = fsum(group.count*trace.states[-1].mass_kg
                                 for group, trace in pairs)
        if self.impact_result.total_incident_mass_kg != expected_incoming:
            raise ValueError("Impact result incident stock differs from all admitted population contacts")
        if (abs(self.impact_result.mass_residual_kg) > self.impact_owner.tolerances.mass_kg
                or abs(self.impact_result.total_energy_residual_j)
                   > self.impact_owner.tolerances.energy_j):
            raise ValueError("Combined finite-surface mass or energy ledger failed its owner budget")
        object.__setattr__(self, "group_ids", expected_ids)
        object.__setattr__(self, "event_times_s", expected_times)
        object.__setattr__(self, "_seal", _sequence_signature(
            self.population, self.impact_owner, self.impact_result, pairs,
        ))
        self.require_current()

    def require_current(self):
        if not self._seal:
            raise ValueError("Impact sequence lacks its original owner issuance seal")
        self.population.require_current()
        self.impact_result.require_current()
        pairs = _incident_pairs(self.population)
        current = _sequence_signature(self.population, self.impact_owner,
                                      self.impact_result, pairs)
        if current != self._seal:
            raise ValueError("Population or finite-surface output changed after sequence admission")
        ordered = tuple(sorted(pairs, key=lambda pair: pair[1].states[-1].time_s))
        if (tuple(group.group_id for group, _ in ordered) != self.group_ids
                or tuple(trace.states[-1].time_s for _, trace in ordered) != self.event_times_s
                or len(self.impact_result.steps) != len(ordered)):
            raise ValueError("Incident event ordering or owner step count changed")
        for step, (_, trace) in zip(self.impact_result.steps, ordered, strict=True):
            self.impact_owner.require_original_step(step)
            if step.context.incident_trace is not trace:
                raise ValueError("Impact owner step no longer retains its original flight trace")
        if self.impact_result.total_incident_mass_kg != fsum(
                group.count*trace.states[-1].mass_kg for group, trace in pairs):
            raise ValueError("Impact sequence total does not equal the incident population stock")
        if (abs(self.impact_result.mass_residual_kg) > self.impact_owner.tolerances.mass_kg
                or abs(self.impact_result.total_energy_residual_j)
                   > self.impact_owner.tolerances.energy_j):
            raise ValueError("Finite-wall sequence ledger changed beyond its owner budgets")
        return self


class PopulationImpactSequenceError(RuntimeError):
    """Preserve the original failure and any contacts already completed by the owner."""

    def __init__(self, message, *, cause, population, impact_owner, impact_result=None):
        super().__init__(message)
        self.cause = cause
        self.population = population
        self.impact_owner = impact_owner
        self.impact_result = impact_result
        self.completed_steps = tuple(getattr(cause, "completed_steps", ()))


def impact_population_sequence(population, impact_owner):
    """Pass distinct unit-count ground events to one sequential finite surface.

    All ground-crossing groups are included exactly once and ordered by their
    accepted event time. The existing owner evolves one finite patch through the
    sequence, including its declared intercontact heat. Duplicate event times,
    multi-count representative groups and overlapping contacts fail closed.
    """
    if (type(population) is not ParcelPopulationResult
            or type(impact_owner) is not FiniteSurfaceImpact):
        raise TypeError("Supply the original parcel population and finite surface owner")
    result = None
    try:
        population.require_current()
        pairs = _incident_pairs(population)
        if not pairs:
            raise ValueError("Population contains no accepted ground-crossing parcel events")
        if any(group.count != 1 for group, _ in pairs):
            raise ValueError("A representative multi-parcel group cannot be multiplied into wall contacts")
        for _, trace in pairs:
            if not trace.states or trace.states[-1].time_s < impact_owner.patch.initial_time_s:
                raise ValueError("Every incident trajectory must retain an ordered accepted contact state")
            if (trace.boundary.clock_id != population.clock_id
                    or trace.boundary.frame_id != population.frame_id
                    or population.clock_id != impact_owner.patch.location.clock_id
                    or population.frame_id != impact_owner.patch.location.coordinate_frame_id):
                raise ValueError("Population, incident traces and finite patch need one clock/frame")
        ordered = tuple(sorted(pairs, key=lambda pair: pair[1].states[-1].time_s))
        event_times = tuple(trace.states[-1].time_s for _, trace in ordered)
        if len(set(event_times)) != len(event_times):
            raise ValueError("Equal-time contacts need a simultaneous-impact owner, which is unavailable")
        result = impact_owner.run(tuple(trace for _, trace in ordered))
        population.require_current()
        receipt = _issue_sequence(
            population=population,
            impact_owner=impact_owner,
            impact_result=result,
            group_ids=tuple(group.group_id for group, _ in ordered),
            event_times_s=event_times,
        )
        return receipt.require_current()
    except Exception as cause:
        raise PopulationImpactSequenceError(
            "Sequential population-to-finite-wall impact admission failed",
            cause=cause, population=population, impact_owner=impact_owner,
            impact_result=result,
        ) from cause


__all__ = [
    "PopulationImpactSequence",
    "PopulationImpactSequenceError",
    "impact_population_sequence",
]
