"""Generic, caller-thresholded cascade-bank selection for refuelling systems.

This module is a supervisory sequence contract only. It owns no pressure-flow
law, valve actuator, dispenser, vehicle tank, temperature limit, or industry
refuelling schedule.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from ..core import finite


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty identity")
    return value.strip()


def _bank_values(values: Mapping[str, float], name: str) -> Mapping[str, float]:
    if not isinstance(values, Mapping) or not values:
        raise TypeError(f"{name} must map bank IDs to values")
    result = {}
    for key, value in values.items():
        bank_id = _identity(key, f"{name} bank ID")
        if bank_id in result:
            raise ValueError(f"{name} contains duplicate bank IDs")
        result[bank_id] = value
    return MappingProxyType(result)


@dataclass(frozen=True, slots=True)
class CascadeBankStage:
    """One caller-defined bank stage and its switch policy.

    ``switch_receiver_pressure_pa`` advances away from this stage when the
    receiver reaches the declared absolute pressure. It is ``None`` only for
    the final stage. ``minimum_source_headroom_pa`` is a supervisory eligibility
    margin; it is not a predicted flow or a pressure-drop calculation.
    """

    bank_id: str
    switch_receiver_pressure_pa: float | None
    minimum_source_headroom_pa: float

    def __post_init__(self):
        object.__setattr__(self, "bank_id", _identity(self.bank_id, "bank_id"))
        if self.switch_receiver_pressure_pa is not None:
            object.__setattr__(self, "switch_receiver_pressure_pa", finite(
                self.switch_receiver_pressure_pa, "switch_receiver_pressure_pa", positive=True))
        object.__setattr__(self, "minimum_source_headroom_pa", finite(
            self.minimum_source_headroom_pa, "minimum_source_headroom_pa", positive=True))


@dataclass(frozen=True, slots=True)
class CascadeRefillMeasurement:
    """Aligned absolute pressures and explicit sensor lineage at one sample."""

    time_s: float
    receiver_pressure_pa_absolute: float
    bank_pressure_pa_absolute: Mapping[str, float]
    receiver_sensor_id: str
    receiver_sensor_owner_id: str
    bank_sensor_ids: Mapping[str, str]
    bank_sensor_owner_ids: Mapping[str, str]
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        time_s = finite(self.time_s, "time_s")
        if time_s < 0.0:
            raise ValueError("Sample time must be nonnegative")
        object.__setattr__(self, "time_s", time_s)
        object.__setattr__(self, "receiver_pressure_pa_absolute", finite(
            self.receiver_pressure_pa_absolute, "receiver_pressure_pa_absolute", positive=True))
        pressures = _bank_values(self.bank_pressure_pa_absolute, "bank_pressure_pa_absolute")
        sensors = _bank_values(self.bank_sensor_ids, "bank_sensor_ids")
        owners = _bank_values(self.bank_sensor_owner_ids, "bank_sensor_owner_ids")
        if set(pressures) != set(sensors) or set(pressures) != set(owners):
            raise ValueError("Bank pressure samples, sensor IDs and sensor owners must align exactly")
        object.__setattr__(self, "bank_pressure_pa_absolute", MappingProxyType({
            bank: finite(value, f"{bank} absolute pressure", positive=True)
            for bank, value in pressures.items()
        }))
        object.__setattr__(self, "bank_sensor_ids", MappingProxyType({
            bank: _identity(value, f"{bank} sensor ID") for bank, value in sensors.items()
        }))
        object.__setattr__(self, "bank_sensor_owner_ids", MappingProxyType({
            bank: _identity(value, f"{bank} sensor owner ID") for bank, value in owners.items()
        }))
        for name in ("receiver_sensor_id", "receiver_sensor_owner_id", "clock_id", "evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class CascadeRefillState:
    """Monotone stage memory bound to one clock and sensor set."""

    controller_id: str
    time_s: float
    stage_index: int
    receiver_sensor_id: str
    receiver_sensor_owner_id: str
    bank_sensor_ids: tuple[tuple[str, str], ...]
    bank_sensor_owner_ids: tuple[tuple[str, str], ...]
    clock_id: str
    complete: bool = False

    def __post_init__(self):
        for name in ("controller_id", "receiver_sensor_id", "receiver_sensor_owner_id", "clock_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        object.__setattr__(self, "time_s", finite(self.time_s, "time_s"))
        if self.time_s < 0.0:
            raise ValueError("State time must be nonnegative")
        if isinstance(self.stage_index, bool) or not isinstance(self.stage_index, int) or self.stage_index < 0:
            raise ValueError("stage_index must be a nonnegative integer")
        object.__setattr__(self, "bank_sensor_ids", tuple(self.bank_sensor_ids))
        object.__setattr__(self, "bank_sensor_owner_ids", tuple(self.bank_sensor_owner_ids))
        if not isinstance(self.complete, bool):
            raise TypeError("complete must be bool")


class CascadeRefillStatus(StrEnum):
    SELECTED = "selected"
    WAITING_FOR_HEADROOM = "waiting_for_headroom"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class CascadeBankPermit:
    """Exclusive supervisory enable for one source bank."""

    bank_id: str
    enabled: bool

    def __post_init__(self):
        object.__setattr__(self, "bank_id", _identity(self.bank_id, "bank_id"))
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be bool")


@dataclass(frozen=True, slots=True)
class CascadeRefillOutput:
    """One interval's selected-bank status and mutually exclusive permits."""

    measurement: CascadeRefillMeasurement
    start_time_s: float
    end_time_s: float
    selected_bank_id: str | None
    status: CascadeRefillStatus
    permits: tuple[CascadeBankPermit, ...]
    next_state: CascadeRefillState
    controller_evidence_id: str
    transition_reason: str

    def __post_init__(self):
        if type(self.measurement) is not CascadeRefillMeasurement:
            raise TypeError("Retain the typed pressure measurement")
        status = CascadeRefillStatus(self.status)
        object.__setattr__(self, "status", status)
        start, end = finite(self.start_time_s, "start_time_s"), finite(self.end_time_s, "end_time_s")
        if start != self.measurement.time_s or end <= start:
            raise ValueError("Output must start at the sample and span a positive interval")
        object.__setattr__(self, "start_time_s", start)
        object.__setattr__(self, "end_time_s", end)
        permits = tuple(self.permits)
        if any(type(item) is not CascadeBankPermit for item in permits):
            raise TypeError("Retain typed bank permits")
        enabled = tuple(item.bank_id for item in permits if item.enabled)
        if len(enabled) > 1 or enabled != (() if self.selected_bank_id is None else (self.selected_bank_id,)):
            raise ValueError("At most the selected source bank may receive an enable permit")
        if (status == CascadeRefillStatus.COMPLETE) != (self.selected_bank_id is None):
            if status == CascadeRefillStatus.WAITING_FOR_HEADROOM and self.selected_bank_id is None:
                pass
            else:
                raise ValueError("Selected bank and completion status disagree")
        if type(self.next_state) is not CascadeRefillState:
            raise TypeError("Output requires the resulting sequence state")
        object.__setattr__(self, "permits", permits)
        object.__setattr__(self, "controller_evidence_id", _identity(
            self.controller_evidence_id, "controller_evidence_id"))
        object.__setattr__(self, "transition_reason", _identity(self.transition_reason, "transition_reason"))


@dataclass(frozen=True, slots=True)
class GenericCascadeRefillSequencer:
    """Caller-parameterized monotone bank-selection state machine.

    It never computes a standard-specific tank pressure ramp, target gas
    temperature, flow, heat transfer, or fueling time. Caller-selected absolute
    pressure thresholds and source headroom margins define all stage changes.
    """

    controller_id: str
    target_receiver_pressure_pa_absolute: float
    stages: tuple[CascadeBankStage, ...]
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        for name in ("controller_id", "clock_id", "evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        object.__setattr__(self, "target_receiver_pressure_pa_absolute", finite(
            self.target_receiver_pressure_pa_absolute,
            "target_receiver_pressure_pa_absolute", positive=True))
        stages = tuple(self.stages)
        if not stages or any(type(item) is not CascadeBankStage for item in stages):
            raise TypeError("Supply one or more explicit CascadeBankStage entries")
        if len({item.bank_id for item in stages}) != len(stages):
            raise ValueError("Each bank may occur only once in the ordered cascade")
        thresholds = []
        for index, item in enumerate(stages):
            threshold = item.switch_receiver_pressure_pa
            if index == len(stages) - 1:
                if threshold is not None:
                    raise ValueError("The final stage has no switch threshold")
            else:
                if threshold is None or threshold >= self.target_receiver_pressure_pa_absolute:
                    raise ValueError("Non-final switch thresholds must lie below the receiver target")
                thresholds.append(threshold)
        if any(right <= left for left, right in zip(thresholds, thresholds[1:])):
            raise ValueError("Receiver-pressure switch thresholds must increase strictly")
        object.__setattr__(self, "stages", stages)

    @property
    def bank_ids(self) -> tuple[str, ...]:
        return tuple(item.bank_id for item in self.stages)

    def initial_state(self, *, time_s: float, receiver_sensor_id: str,
                      receiver_sensor_owner_id: str, bank_sensor_ids: Mapping[str, str],
                      bank_sensor_owner_ids: Mapping[str, str]) -> CascadeRefillState:
        """Bind one refuelling run to its sensors and ordered bank set."""
        sensors = _bank_values(bank_sensor_ids, "bank_sensor_ids")
        owners = _bank_values(bank_sensor_owner_ids, "bank_sensor_owner_ids")
        if set(sensors) != set(self.bank_ids) or set(owners) != set(self.bank_ids):
            raise ValueError("State sensor sets must match the configured banks exactly")
        return CascadeRefillState(
            self.controller_id, time_s, 0, receiver_sensor_id, receiver_sensor_owner_id,
            tuple((bank, _identity(sensors[bank], f"{bank} sensor ID")) for bank in self.bank_ids),
            tuple((bank, _identity(owners[bank], f"{bank} sensor owner")) for bank in self.bank_ids),
            self.clock_id,
        )

    def step(self, state: CascadeRefillState, measurement: CascadeRefillMeasurement,
             *, end_time_s: float) -> CascadeRefillOutput:
        """Advance one sampled sequencing interval; no valves or flow are simulated."""
        if type(state) is not CascadeRefillState or type(measurement) is not CascadeRefillMeasurement:
            raise TypeError("step requires its typed state and measurement")
        if state.controller_id != self.controller_id or state.clock_id != self.clock_id:
            raise ValueError("Sequence state belongs to another controller or clock")
        if measurement.clock_id != self.clock_id or measurement.time_s != state.time_s:
            raise ValueError("Measurement must use the configured clock and exact state time")
        if (measurement.receiver_sensor_id != state.receiver_sensor_id
                or measurement.receiver_sensor_owner_id != state.receiver_sensor_owner_id):
            raise ValueError("Receiver sensor identity changed during the filling run")
        if set(measurement.bank_pressure_pa_absolute) != set(self.bank_ids):
            raise ValueError("Pressure measurements must contain exactly the configured banks")
        if dict(measurement.bank_sensor_ids) != dict(state.bank_sensor_ids):
            raise ValueError("Bank sensor identity changed during the filling run")
        if dict(measurement.bank_sensor_owner_ids) != dict(state.bank_sensor_owner_ids):
            raise ValueError("Bank sensor owner changed during the filling run")
        if state.stage_index >= len(self.stages):
            raise ValueError("Sequence state stage is outside the configured bank list")
        if state.complete:
            raise ValueError("A completed refill sequence cannot be resumed")
        end = finite(end_time_s, "end_time_s", positive=True)
        if end <= measurement.time_s:
            raise ValueError("Output interval must have positive duration")

        receiver_pressure = measurement.receiver_pressure_pa_absolute
        index = state.stage_index
        reason = "bank_selected"
        if receiver_pressure >= self.target_receiver_pressure_pa_absolute:
            selected, status, reason = None, CascadeRefillStatus.COMPLETE, "receiver_target_reached"
        else:
            while index < len(self.stages) - 1:
                stage = self.stages[index]
                source_pressure = measurement.bank_pressure_pa_absolute[stage.bank_id]
                if (receiver_pressure >= stage.switch_receiver_pressure_pa):
                    index += 1
                    reason = "receiver_switch_threshold_reached"
                elif (source_pressure - receiver_pressure
                      <= stage.minimum_source_headroom_pa):
                    index += 1
                    reason = "source_headroom_exhausted"
                else:
                    break
            current = self.stages[index]
            headroom = (measurement.bank_pressure_pa_absolute[current.bank_id]
                        - receiver_pressure)
            if headroom > current.minimum_source_headroom_pa:
                selected, status = current.bank_id, CascadeRefillStatus.SELECTED
            else:
                selected, status, reason = None, CascadeRefillStatus.WAITING_FOR_HEADROOM, "no_bank_has_required_headroom"

        permits = tuple(CascadeBankPermit(bank_id, bank_id == selected)
                        for bank_id in self.bank_ids)
        next_state = CascadeRefillState(
            self.controller_id, end, index, state.receiver_sensor_id,
            state.receiver_sensor_owner_id, state.bank_sensor_ids,
            state.bank_sensor_owner_ids, self.clock_id,
            complete=(status == CascadeRefillStatus.COMPLETE),
        )
        return CascadeRefillOutput(
            measurement, measurement.time_s, end, selected, status, permits, next_state,
            self.evidence_id, reason,
        )


__all__ = [
    "CascadeBankPermit",
    "CascadeBankStage",
    "CascadeRefillMeasurement",
    "CascadeRefillOutput",
    "CascadeRefillState",
    "CascadeRefillStatus",
    "GenericCascadeRefillSequencer",
]
