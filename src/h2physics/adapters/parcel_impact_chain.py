"""Original population-member admission to the existing finite impact owner.

One representative trajectory represents one actual parcel here. A weighted
population cannot multiply contact heat or apply simultaneous impacts to the
same finite wall through this interface.
"""

from dataclasses import dataclass, field
from typing import Any

from .droplet_impact import FiniteSurfaceImpact
from .parcel_population import ParcelPopulationResult


class PopulationImpactError(RuntimeError):
    def __init__(self, cause, population, group_id, impact_owner, impact_result=None):
        super().__init__(str(cause))
        self.cause = cause
        self.population = population
        self.group_id = group_id
        self.impact_owner = impact_owner
        self.impact_result = impact_result


@dataclass(frozen=True, slots=True)
class PopulationMemberImpact:
    population: ParcelPopulationResult
    group: Any
    incident_trace: Any
    impact_owner: FiniteSurfaceImpact
    impact_result: Any
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def require_current(self):
        if self._binding != (id(self.population), id(self.group), id(self.incident_trace),
                             id(self.impact_owner), id(self.impact_result)):
            raise ValueError("Impact bridge must retain the original issuing objects")
        self.population.require_current()
        if not any(group is self.group and trace is self.incident_trace
                   for group, trace in self.population.groups_and_traces):
            raise ValueError("Impact trace is detached from its original population group")
        if len(self.impact_result.steps) != 1:
            raise ValueError("Member impact bridge requires exactly one original contact")
        step = self.impact_result.steps[0]
        self.impact_owner.require_original_step(step)
        if step.context.incident_trace is not self.incident_trace:
            raise ValueError("Impact result belongs to a different incident trajectory")
        return self


def impact_population_member(population, group_id, impact_owner):
    """Admit a unit-count incident member to one finite dry-patch contact.

    A group with count greater than one requires separately resolved incident
    trajectories and an explicit physical schedule; this function refuses to
    scale a representative trajectory into a simultaneous wall load.
    """
    if type(population) is not ParcelPopulationResult or type(impact_owner) is not FiniteSurfaceImpact:
        raise TypeError("Use the original population and finite surface impact owner")
    result = None
    try:
        population.require_current()
        matching = tuple((group, trace) for group, trace in population.groups_and_traces
                         if group.group_id == group_id)
        if len(matching) != 1:
            raise ValueError("Select one existing uniquely identified population group")
        group, incident = matching[0]
        if group.count != 1:
            raise ValueError("A representative multi-parcel group cannot reuse one finite wall contact")
        if incident.end_reason != "incident_ground_crossing" or not incident.states:
            raise ValueError("Impact requires an original accepted ground-crossing trajectory")
        patch = impact_owner.patch
        if (population.clock_id != patch.location.clock_id
                or population.frame_id != patch.location.coordinate_frame_id
                or incident.states[-1].time_s < patch.initial_time_s):
            raise ValueError("Population incident and finite wall require one clock/frame and ordered time")
        if incident.states[0].mass_kg != group.mass_per_parcel_kg:
            raise ValueError("Population launch mass differs from its original incident trace")
        result = impact_owner.run((incident,))
        population.require_current()
        receipt = PopulationMemberImpact(population, group, incident, impact_owner, result)
        object.__setattr__(receipt, "_binding", (id(population), id(group), id(incident),
                                               id(impact_owner), id(result)))
        return receipt.require_current()
    except Exception as cause:
        raise PopulationImpactError(cause, population, group_id, impact_owner, result) from cause
