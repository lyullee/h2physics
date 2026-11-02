"""Explicit protection-event bindings across existing monitoring, inventory and risk.

Implemented_unverified. This contract bridge adds no physical/event solver,
detector, scenario scheduler or probability aggregation algorithm.
"""

import math
import weakref
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from types import MappingProxyType

import numpy as np

from ..core import immutable_array, Origin, finite
from ..dynamics import (
    ConservedInventory,
    InventoryBalance,
    InventoryTolerances,
    ScheduledEquipmentCommand,
)
from ..sources import IntervalMassSource
from .conditional_risk import ConditionalRiskResult, conditional_risk, finite_source_sha256
from .gas_detection import ConcentrationAlarmEvidence, ConcentrationAlarmVotingEvidence
from .lh2dt_dynamics import (
    DynamicEquipmentRun,
    Lh2dtDynamicEquipment,
    SampledEquipmentIntegral,
)
from .lh2dt_relief import ReliefTankTrace, ReliefTransition
from .physical_economics import callable_identity, finite_sum, snapshot_sha256
from .process_monitoring import MonitoringEvaluation, NativeResidualMonitor

STATUS = "implemented_unverified"
_ISSUED = object()
_PENDING_FACILITY_RISK_RESULT_ISSUERS = {}
_PENDING_PROTECTED_RUN_ISSUERS = {}


def _issue_facility_risk_result_token(parents):
    token = object()
    _PENDING_FACILITY_RISK_RESULT_ISSUERS[token] = tuple(id(value) for value in parents)
    return token


def _issue_protected_run_token(native_run, driver, plans, accepted,
                               mode_definition_id, scenario_evidence_id):
    token = object()
    _PENDING_PROTECTED_RUN_ISSUERS[token] = (
        id(native_run), id(driver), tuple(map(id, plans)), tuple(map(id, accepted)),
        mode_definition_id, scenario_evidence_id,
    )
    return token


def _text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare clock, mode, target, mechanism and evidence identities")


def _fields(value):
    return {f.name: getattr(value, f.name) for f in fields(value)}


def _same(left, right):
    return len(left) == len(right) and all(a is b for a, b in zip(left, right, strict=True))


class FacilityProtectionError(RuntimeError):
    """Original failure and any attempted command/native run/result remain available."""

    def __init__(
        self,
        message,
        *,
        stage,
        original,
        owner=None,
        time_s=None,
        native_context=None,
        native_run=None,
        completed=(),
        result=None,
    ):
        super().__init__(message)
        self.stage, self.original_error, self.owner = stage, original, owner
        self.time_s, self.native_context, self.native_run = time_s, native_context, native_run
        self.completed, self.result = tuple(completed), result


def _monitor_material(owner, result):
    if type(owner) is not NativeResidualMonitor or type(result) is not MonitoringEvaluation:
        raise TypeError("Bind an actual native residual-monitor owner and its original evaluation")
    # The existing owner has no public result-verification hook. Reuse its
    # actual admission guard (source/model/settings/partition), never a solve.
    owner._guard()
    if (
        owner.status != "calibrated"
        or not any(v is result for v in owner.evaluations)
        or result.native_model is not owner.native_model
        or result.fitting_data is not owner.fitting_data
        or result.calibration_data is not owner.calibration_data
    ):
        raise ValueError(
            "Monitoring evaluation is not registered to this calibrated original owner"
        )
    for data in (result.fitting_data, result.calibration_data, result.data):
        data.require_unchanged(owner.native)
    if result.data.context.role != "evaluation":
        raise ValueError("An action needs held-out evaluation, never fitting/calibration scores")
    trained = owner.native.digest(tuple(sorted(owner.native_model.monitors.items())))
    if trained != result.trained_state_sha256:
        raise ValueError("Current actual native model/threshold state differs from evaluation")
    native = result.native_result
    n = len(result.data.observed.time_s)
    for name in ("time_s", "scores", "valid", "alarms"):
        a, b = np.asarray(getattr(result, name)), np.asarray(getattr(native, name))
        if a.shape != (n,) or b.shape != (n,) or not np.array_equal(a, b, equal_nan=True):
            raise ValueError("Native decision cache differs from the original copied evaluation")
    if (
        not np.array_equal(result.time_s, result.data.observed.time_s)
        or np.any(result.valid & ~np.isfinite(result.scores))
        or np.any(~result.valid & (result.alarms | ~np.isnan(result.scores)))
        or not np.array_equal(result.alarms, result.valid & (result.scores > native.threshold))
    ):
        raise ValueError("Monitoring time/mask/alarm semantics changed")
    identities = (
        owner,
        owner.native,
        owner.native_model,
        result,
        native,
        result.data,
        result.fitting_data,
        result.calibration_data,
        result.data.prediction_owner,
        result.data.observed,
        result.data.predicted,
        *callable_identity(owner._guard),
    )
    content = owner.native.digest(
        (
            native,
            result.time_s,
            result.scores,
            result.valid,
            result.alarms,
            result.mode_thresholds,
            owner.settings,
            trained,
            result.data.content_sha256,
            result.fitting_data.content_sha256,
            result.calibration_data.content_sha256,
            result.data.features,
            result.data.context,
        )
    )
    owner._guard()
    return identities, content


@dataclass(frozen=True, slots=True)
class AlarmEvidence:
    owner: NativeResidualMonitor
    evaluation: MonitoringEvaluation
    row_index: int
    observed_mode_id: str
    sensor_evidence_ids: Mapping[str, str]
    decision_evidence_id: str
    clock_id: str
    time_s: float
    episode_id: str
    _identities: tuple = field(repr=False)
    _content: str = field(repr=False)
    _binding_content: str = field(repr=False)
    _token: object = field(repr=False)

    def __post_init__(self):
        if self._token is not _ISSUED:
            raise TypeError("Use AlarmEvidence.bind; metadata alone is not an evaluated alarm")
        object.__setattr__(
            self, "sensor_evidence_ids", MappingProxyType(dict(self.sensor_evidence_ids))
        )

    @classmethod
    def bind(
        cls,
        owner,
        evaluation,
        *,
        row_index,
        observed_mode_id,
        sensor_evidence_ids,
        decision_evidence_id,
    ):
        identities, content = _monitor_material(owner, evaluation)
        if type(row_index) is not int or not 0 <= row_index < len(evaluation.time_s):
            raise ValueError("Choose one explicit existing causal decision row")
        _text(observed_mode_id, decision_evidence_id)
        sensors = dict(sensor_evidence_ids)
        required = {f.observed_channel for f in evaluation.data.features}
        if set(sensors) != required:
            raise ValueError("Every original observed channel needs its sensor evidence")
        _text(*sensors.values())
        mode = str(evaluation.data.native_batch.modes[row_index])
        if mode != observed_mode_id:
            raise ValueError("Chosen observed mode differs from the actual native decision row")
        if not evaluation.valid[row_index] or not evaluation.alarms[row_index]:
            raise ValueError(
                "Invalid, missing, unknown-mode or unalarmed rows cannot trip an action"
            )
        clock = evaluation.data.observed.clock_id
        time = finite(evaluation.time_s[row_index], "decision time")
        episode = str(evaluation.data.native_batch.episodes[row_index])
        binding = snapshot_sha256(
            (row_index, observed_mode_id, sensors, decision_evidence_id, clock, time, episode)
        )
        return cls(
            owner,
            evaluation,
            row_index,
            observed_mode_id,
            sensors,
            decision_evidence_id,
            clock,
            time,
            episode,
            identities,
            content,
            binding,
            _ISSUED,
        )

    def require_current(self):
        identities, content = _monitor_material(self.owner, self.evaluation)
        row = self.row_index
        if (
            self._token is not _ISSUED
            or not _same(identities, self._identities)
            or content != self._content
            or type(row) is not int
            or not 0 <= row < len(self.evaluation.time_s)
            or self.clock_id != self.evaluation.data.observed.clock_id
            or self.time_s != self.evaluation.time_s[row]
            or self.observed_mode_id != str(self.evaluation.data.native_batch.modes[row])
            or self.episode_id != str(self.evaluation.data.native_batch.episodes[row])
            or not self.evaluation.valid[row]
            or not self.evaluation.alarms[row]
        ):
            raise ValueError("Original monitoring decision/source/mode/clock binding changed")
        _text(self.decision_evidence_id, *self.sensor_evidence_ids.values())
        if (
            snapshot_sha256(
                (
                    self.row_index,
                    self.observed_mode_id,
                    dict(self.sensor_evidence_ids),
                    self.decision_evidence_id,
                    self.clock_id,
                    self.time_s,
                    self.episode_id,
                )
            )
            != self._binding_content
        ):
            raise ValueError("Originally selected row/sensor/decision evidence changed")
        if set(self.sensor_evidence_ids) != {
            f.observed_channel for f in self.evaluation.data.features
        }:
            raise ValueError("Sensor-evidence coverage changed")
        return self


@dataclass(frozen=True, slots=True)
class ProtectionAction:
    identifier: str
    mechanism_id: str
    target_id: str
    action_kind: str
    prior_mode_id: str
    resulting_mode_id: str
    latency_s: float
    evidence_id: str
    interpretation: str
    origin: Origin

    def __post_init__(self):
        _text(
            self.identifier,
            self.mechanism_id,
            self.target_id,
            self.prior_mode_id,
            self.resulting_mode_id,
            self.evidence_id,
        )
        if self.action_kind not in {"isolation", "mode_change"}:
            raise ValueError(
                "A command is explicit isolation/mode change; autonomous relief is separate"
            )
        if self.prior_mode_id == self.resulting_mode_id:
            raise ValueError("A protection action must declare an actual change of mode")
        if finite(self.latency_s, "declared decision-to-command latency") < 0:
            raise ValueError("Protection cannot act before its chosen observation")
        if self.interpretation != "prescribed-counterfactual-replay":
            raise ValueError("This offline bridge supports only explicitly prescribed replay")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Declare action provenance; no default sensor/actuator reliability")


@dataclass(frozen=True, slots=True)
class ActionInvocation:
    action: ProtectionAction
    alarm: AlarmEvidence | ConcentrationAlarmEvidence | ConcentrationAlarmVotingEvidence
    time_s: float
    native_context: object
    target: object
    mode_before: str
    mode_after: str
    original_return: object
    interpretation: str = (
        "callback completion only; physical acceptance requires a native transition"
    )


class ScheduledProtection:
    """One explicit alarm/action maps to the existing native command contract."""

    def __init__(self, alarm, action, *, target, native_context, read_mode, apply):
        if type(alarm) not in (
            AlarmEvidence, ConcentrationAlarmEvidence, ConcentrationAlarmVotingEvidence,
        ) or type(action) is not ProtectionAction:
            raise TypeError("Use a source-bound alarm event and explicit ProtectionAction")
        alarm.require_current()
        ProtectionAction(**_fields(action))
        if (
            target is None
            or native_context is None
            or not callable(read_mode)
            or not callable(apply)
        ):
            raise TypeError(
                "Retain actual actuator/context and explicit mode-reader/action callback"
            )
        self.alarm, self.action, self.target, self.native_context = (
            alarm,
            action,
            target,
            native_context,
        )
        self.read_mode, self.apply = read_mode, apply
        self.time_s = finite(alarm.time_s + action.latency_s, "scheduled protection time")
        self.invocation = self.failure = None
        self._identities = (
            alarm,
            action,
            target,
            native_context,
            *callable_identity(read_mode),
            *callable_identity(apply),
        )
        self._content = snapshot_sha256(
            (
                action,
                alarm.clock_id,
                alarm.time_s,
                alarm.observed_mode_id,
                alarm.episode_id,
                dict(alarm.sensor_evidence_ids),
                alarm.decision_evidence_id,
                self.time_s,
            )
        )
        self.command = ScheduledEquipmentCommand(action.identifier, self.time_s, self._invoke)
        self._command = self.command

    def require_current(self):
        self.alarm.require_current()
        ProtectionAction(**_fields(self.action))
        identities = (
            self.alarm,
            self.action,
            self.target,
            self.native_context,
            *callable_identity(self.read_mode),
            *callable_identity(self.apply),
        )
        content = snapshot_sha256(
            (
                self.action,
                self.alarm.clock_id,
                self.alarm.time_s,
                self.alarm.observed_mode_id,
                self.alarm.episode_id,
                dict(self.alarm.sensor_evidence_ids),
                self.alarm.decision_evidence_id,
                self.time_s,
            )
        )
        if (
            not _same(identities, self._identities)
            or content != self._content
            or self.command is not self._command
            or self.command.identifier != self.action.identifier
            or self.command.time_s != self.time_s
            or not _same(callable_identity(self.command.apply), callable_identity(self._invoke))
        ):
            raise ValueError("Original action/callback/target/native command binding changed")
        return self

    def _invoke(self, time_s, context):
        before = None
        try:
            self.require_current()
            if (
                context is not self.native_context
                or time_s != self.time_s
                or self.invocation is not None
                or self.failure is not None
            ):
                raise ValueError("Wrong native context/time or repeated protection invocation")
            before = self.read_mode(self.target)
            if before != self.action.prior_mode_id:
                raise ValueError("Actuator is not in its explicitly declared prior mode")
            returned = self.apply(time_s, context)
            after = self.read_mode(self.target)
            if after != self.action.resulting_mode_id:
                raise ValueError("Callback did not establish its declared actuator mode")
            self.require_current()
            self.invocation = ActionInvocation(
                self.action, self.alarm, time_s, context, self.target, before, after, returned
            )
        except Exception as error:
            self.failure = FacilityProtectionError(
                str(error),
                stage="action-invocation",
                original=error,
                owner=self,
                time_s=time_s,
                native_context=context,
                completed=(() if self.invocation is None else (self.invocation,)),
            )
            self.failure.mode_before = before
            raise self.failure from error


@dataclass(frozen=True, slots=True)
class AcceptedProtection:
    plan: ScheduledProtection
    invocation: ActionInvocation
    run: DynamicEquipmentRun
    native_transition: object

    def require_current(self):
        self.plan.require_current()
        transition = self.native_transition
        if (
            self.plan.invocation is not self.invocation
            or self.plan.failure is not None
            or self.invocation.action is not self.plan.action
            or self.invocation.alarm is not self.plan.alarm
            or self.invocation.native_context is not self.plan.native_context
            or self.invocation.target is not self.plan.target
            or self.invocation.time_s != self.plan.time_s
            or self.invocation.mode_before != self.plan.action.prior_mode_id
            or self.invocation.mode_after != self.plan.action.resulting_mode_id
            or self.run.clock_id != self.plan.alarm.clock_id
            or not any(v is transition for v in self.run.transitions)
            or transition.time_s != self.plan.time_s
            or self.plan.action.identifier not in transition.identifiers
        ):
            raise ValueError(
                "Command invocation is not bound to its original accepted native transition"
            )
        return self


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ProtectedEquipmentRun:
    native_run: DynamicEquipmentRun
    driver: object
    plans: tuple[ScheduledProtection, ...]
    accepted: tuple[AcceptedProtection, ...]
    mode_definition_id: str
    scenario_evidence_id: str
    _issuer_token: object = field(default=None, repr=False, compare=False)
    interpretation: str = (
        "prescribed replay; no online detection/actuator dynamics or reliability proof"
    )
    _original_ref: object = field(default=None, init=False, repr=False, compare=False)
    _bindings: tuple = field(default=(), init=False, repr=False, compare=False)
    _evidence_sha256: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        expected = (
            id(self.native_run), id(self.driver), tuple(map(id, self.plans)),
            tuple(map(id, self.accepted)), self.mode_definition_id,
            self.scenario_evidence_id,
        )
        if _PENDING_PROTECTED_RUN_ISSUERS.get(self._issuer_token) != expected:
            raise TypeError("Use execute_protected to issue an accepted native protection replay")
        _PENDING_PROTECTED_RUN_ISSUERS.pop(self._issuer_token)
        object.__setattr__(self, "plans", tuple(self.plans))
        object.__setattr__(self, "accepted", tuple(self.accepted))

    def require_current(self):
        _text(self.mode_definition_id, self.scenario_evidence_id)
        if (
            self._original_ref is None
            or self._original_ref() is not self
            or not _same(
                (
                    self.native_run,
                    self.driver,
                    self.plans,
                    self.accepted,
                    *self.plans,
                    *self.accepted,
                ),
                self._bindings,
            )
            or snapshot_sha256(
                (self.mode_definition_id, self.scenario_evidence_id, self.interpretation)
            )
            != self._evidence_sha256
        ):
            raise ValueError(
                "Use the unchanged original protected result issued after actual native return"
            )
        if len(self.accepted) != len(self.plans):
            raise ValueError("Every prescribed action needs its actual accepted transition")
        for plan, accepted in zip(self.plans, self.accepted, strict=True):
            if (
                accepted.plan is not plan
                or accepted.run is not self.native_run
                or self.driver.network.native is not plan.native_context
            ):
                raise ValueError("Accepted action lost its original driver/run/context ownership")
            accepted.require_current()
        return self


def execute_protected(
    driver,
    plans,
    *,
    duration_s,
    time_step_s,
    start_time_s,
    clock_id,
    mode_definition_id,
    scenario_evidence_id,
):
    """Delegate one explicit replay to the existing LH2DT driver; no new scheduler."""
    plans, run, accepted = tuple(plans), None, []
    try:
        if type(driver) is not Lh2dtDynamicEquipment:
            raise TypeError("Delegate to the actual existing native finite-equipment driver")
        _text(clock_id, mode_definition_id, scenario_evidence_id)
        start, duration = (
            finite(start_time_s, "replay start"),
            finite(duration_s, "duration", positive=True),
        )
        if not plans or len({p.action.identifier for p in plans}) != len(plans):
            raise ValueError("Declare nonempty distinct prescribed protection actions")
        for plan in plans:
            if type(plan) is not ScheduledProtection:
                raise TypeError("Use actual ScheduledProtection plans")
            plan.require_current()
            if (
                plan.native_context is not driver.network.native
                or plan.alarm.clock_id != clock_id
                or not start <= plan.alarm.time_s <= plan.time_s <= start + duration
                or plan.invocation is not None
                or plan.failure is not None
            ):
                raise ValueError(
                    "Replay clock/support/context differs or plan was already attempted"
                )
        run = driver.run(
            duration,
            time_step_s,
            clock_id=clock_id,
            start_time_s=start,
            commands=tuple(p.command for p in plans),
        )
        for plan in plans:
            matches = tuple(
                t
                for t in run.transitions
                if plan.action.identifier in t.identifiers and t.time_s == plan.time_s
            )
            if len(matches) != 1 or plan.invocation is None:
                raise ValueError(
                    "Native replay did not retain the exact prescribed accepted transition"
                )
            accepted.append(AcceptedProtection(plan, plan.invocation, run, matches[0]))
        accepted = tuple(accepted)
        token = _issue_protected_run_token(
            run, driver, plans, accepted, mode_definition_id, scenario_evidence_id
        )
        result = ProtectedEquipmentRun(
            run, driver, plans, accepted, mode_definition_id, scenario_evidence_id,
            _issuer_token=token,
        )
        object.__setattr__(result, "_original_ref", weakref.ref(result))
        object.__setattr__(
            result,
            "_bindings",
            (run, driver, result.plans, result.accepted, *result.plans, *result.accepted),
        )
        object.__setattr__(
            result,
            "_evidence_sha256",
            snapshot_sha256((mode_definition_id, scenario_evidence_id, result.interpretation)),
        )
        return result.require_current()
    except Exception as error:
        failure = FacilityProtectionError(
            str(error),
            stage="native-protected-replay",
            original=error,
            owner=driver,
            native_run=run,
            completed=accepted,
        )
        failure.attempted_plans = plans
        failure.completed_invocations = tuple(
            p.invocation
            for p in plans
            if type(p) is ScheduledProtection and p.invocation is not None
        )
        raise failure from error


@dataclass(frozen=True, slots=True)
class ReliefProtectionRecord:
    trace: ReliefTankTrace
    transition: ReliefTransition
    target_id: str
    mechanism_id: str
    evidence_id: str
    _identities: tuple = field(repr=False)
    _content: str = field(repr=False)

    @classmethod
    def bind(cls, trace, transition, *, target_id, mechanism_id, evidence_id):
        if type(trace) is not ReliefTankTrace or type(transition) is not ReliefTransition:
            raise TypeError("Retain the actual native relief trace and original transition")
        _text(target_id, mechanism_id, evidence_id)
        identities = (
            trace,
            transition,
            trace.native_tank,
            transition.native_before,
            transition.native_after,
            transition.native_tank_state,
            transition.source_before,
            transition.source_after,
        )
        result = cls(
            trace,
            transition,
            target_id,
            mechanism_id,
            evidence_id,
            identities,
            snapshot_sha256(
                (_relief_material(trace, transition), target_id, mechanism_id, evidence_id)
            ),
        )
        return result.require_current()

    def require_current(self):
        _text(self.target_id, self.mechanism_id, self.evidence_id)
        t = self.transition
        identities = (
            self.trace,
            t,
            self.trace.native_tank,
            t.native_before,
            t.native_after,
            t.native_tank_state,
            t.source_before,
            t.source_after,
        )
        if (
            not _same(identities, self._identities)
            or snapshot_sha256(
                (
                    _relief_material(self.trace, t),
                    self.target_id,
                    self.mechanism_id,
                    self.evidence_id,
                )
            )
            != self._content
        ):
            raise ValueError("Original native relief latch/threshold/state evidence changed")
        return self


def _relief_material(trace, transition):
    for value in (
        transition.pressure_pa,
        transition.threshold_pa,
        transition.native_before.set_pressure_Pa,
        transition.native_before.reseat_pressure_Pa,
        transition.native_after.set_pressure_Pa,
        transition.native_after.reseat_pressure_Pa,
    ):
        finite(value, "recorded native relief absolute pressure", positive=True)
    if not any(t is transition for t in trace.transitions):
        raise ValueError("Relief transition is not retained by this actual native trace")
    if (
        transition.kind not in {"open", "reseat", "initial_open", "initial_reseat"}
        or not transition.lower_bracket_time_s
        <= transition.time_s
        <= transition.upper_bracket_time_s
        or not trace.time_s[0] <= transition.time_s <= trace.time_s[-1]
        or transition.native_before.is_open == transition.native_after.is_open
        or transition.native_after.is_open != (transition.kind in {"open", "initial_open"})
    ):
        raise ValueError("Relief transition lacks its ordered accepted latch change")
    return (
        trace.clock_id,
        trace.time_s,
        trace.event_settings,
        transition.kind,
        transition.time_s,
        transition.pressure_pa,
        transition.threshold_pa,
        transition.lower_bracket_time_s,
        transition.upper_bracket_time_s,
        transition.native_before.is_open,
        transition.native_after.is_open,
        transition.native_before.set_pressure_Pa,
        transition.native_before.reseat_pressure_Pa,
        transition.native_after.set_pressure_Pa,
        transition.native_after.reseat_pressure_Pa,
        transition.native_tank_state,
        transition.source_before.nozzle,
        transition.source_after.nozzle,
    )


def _snapshot_content(snapshot):
    return (
        snapshot.node_states,
        snapshot.transfers,
        snapshot.native_success,
        snapshot.junction_mass_residuals_kg_s,
        snapshot.junction_energy_residuals_w,
        snapshot.boundary_inlet_kg_s,
        snapshot.boundary_outlet_kg_s,
        snapshot.boundary_inlet_enthalpy_w,
        snapshot.boundary_outlet_enthalpy_w,
    )


def _transfer(snapshot, component_id, stored_nodes):
    matches = tuple(t for t in snapshot.transfers if t.component_id == component_id)
    if len(matches) != 1:
        raise ValueError("One explicit source component must exist in every accepted native sample")
    transfer = matches[0]
    if (
        transfer.left_node not in stored_nodes
        or transfer.right_node in stored_nodes
        or transfer.mass_flow_kg_s < 0
    ):
        raise ValueError(
            "Source must be an outward one-way external boundary of the selected finite inventories"
        )
    return transfer


def _segment_integral(run, index, previous, component_id, nodes, *,
                      rate_reader=None, rate_unit="kg/s", integral_unit="kg"):
    run.require_current()
    start = run.start_time_s if index == 0 else run.steps[index - 1].time_s
    row = run.steps[index]
    transitions = tuple(t for t in run.transitions if start <= t.time_s <= row.time_s)
    for event in transitions:
        _transfer(event.before, component_id, nodes)
        _transfer(event.after, component_id, nodes)
    reader = rate_reader or (
        lambda snapshot: _transfer(snapshot, component_id, nodes).mass_flow_kg_s
    )
    points = [(start, 0, previous), (row.time_s, 0, row.equipment)]
    for event in transitions:
        points.extend(((event.time_s, 0, event.before), (event.time_s, 1, event.after)))
    points.sort(key=lambda item: (item[0], item[1]))
    samples = tuple(
        (at, finite(reader(snapshot), "sampled rate"))
        for at, _side, snapshot in points
    )
    areas = tuple(
        (right_time - left_time) * (left_rate + right_rate) / 2.0
        for (left_time, left_rate), (right_time, right_rate)
        in zip(samples, samples[1:])
        if right_time > left_time
    )
    basis = next(iter(run.initial_inventories.values())).basis
    integral = SampledEquipmentIntegral(
        math.fsum(areas), basis, rate_unit, integral_unit, run.clock_id,
        start, row.time_s, len(areas),
    )
    return integral, transitions


def sampled_interval_source(run, *, component_id, location, state, evidence_id):
    """Project accepted native samples through existing mass quadrature only.

    The caller supplies the fixed source-state/location evidence; resolved exit
    enthalpy, momentum, atmospheric/ground partition and substep shape are absent.
    Use FiniteFacilitySource.bind to require finite-inventory reconciliation.
    """
    if type(run) is not DynamicEquipmentRun or not run.steps:
        raise TypeError("An actual accepted finite native run is required")
    if location.clock_id != run.clock_id:
        raise ValueError("Source and native accepted run clocks must agree exactly")
    nodes, previous, masses = set(run.initial_inventories), run.initial_equipment, []
    for index, row in enumerate(run.steps):
        _transfer(previous, component_id, nodes)
        _transfer(row.equipment, component_id, nodes)
        integral, _ = _segment_integral(run, index, previous, component_id, nodes)
        masses.append(integral.value)
        previous = row.equipment
    return IntervalMassSource(
        location,
        [run.start_time_s, *(row.time_s for row in run.steps)],
        masses,
        state,
        Origin.PREDICTED,
        evidence_id,
        "window_end",
    )


def _dynamic_source_material(run, source, component_id, other_mass, tolerances, reconciliation):
    if type(run) is not DynamicEquipmentRun or not run.steps:
        raise TypeError("Bind the original nonempty finite native DynamicEquipmentRun")
    finite_source_sha256(source)
    finite(other_mass, "explicit other net external mass")
    _text(component_id, reconciliation)
    nodes = set(run.initial_inventories)
    edges = np.array([run.start_time_s, *(row.time_s for row in run.steps)])
    if (
        source.location.clock_id != run.clock_id
        or not np.array_equal(source.edges_s, edges)
        or source.end_reason != "window_end"
    ):
        raise ValueError(
            "Dynamic source requires exact accepted edges/clock and explicit window_end; no inferred termination"
        )
    for inventory in run.initial_inventories.values():
        ConservedInventory(**_fields(inventory))
        inventory.basis.require_compatible(source.state.basis)
    records, identities, previous = (
        [],
        [run, source, source.location, source.state],
        run.initial_equipment,
    )
    for index, row in enumerate(run.steps):
        if (
            set(row.inventories) != nodes
            or set(row.balances) != nodes
            or row.time_s <= edges[index]
        ):
            raise ValueError("Finite native inventory rows/clock are incomplete")
        for name, balance in row.balances.items():
            ConservedInventory(**_fields(row.inventories[name]))
            InventoryBalance(**_fields(balance))
            if (
                balance.initial is not run.initial_inventories[name]
                or balance.current is not row.inventories[name]
            ):
                raise ValueError("Native balances lost their original inventory pointers")
            if balance.violations(tolerances):
                raise ValueError("Existing native inventory/enthalpy/heat ledger does not close")
        if row.native.network_solution is not row.equipment.native:
            raise ValueError(
                "Accepted native solution lost its original checked equipment snapshot"
            )
        finite(row.native.time_s, "native accepted local time", positive=True)
        for name in (
            "cumulative_boundary_mass_kg",
            "cumulative_boundary_energy_J",
            "cumulative_boundary_transport_energy_J",
            "cumulative_boundary_ambient_heat_J",
        ):
            values = getattr(row.native, name)
            if set(values) != nodes:
                raise ValueError("Native accepted external ledgers lost their node identities")
            for value in values.values():
                finite(value, "native accepted external ledger")
        _transfer(previous, component_id, nodes)
        _transfer(row.equipment, component_id, nodes)
        # Reuse the existing accepted-sample quadrature including both command
        # limits. This is not a new mass-flow law or native RK-stage integral.
        integral, transitions = _segment_integral(run, index, previous, component_id, nodes)
        if abs(integral.value - source.mass_kg[index]) > tolerances.mass_absolute_kg:
            raise ValueError(
                "Source bin differs from the existing accepted-sample boundary integral"
            )
        records.append(
            (
                row.time_s,
                row.inventories,
                row.balances,
                _snapshot_content(row.equipment),
                row.native.states,
                row.native.time_s,
                {
                    name: getattr(row.native, name)
                    for name in (
                        "cumulative_boundary_mass_kg",
                        "cumulative_boundary_energy_J",
                        "cumulative_boundary_transport_energy_J",
                        "cumulative_boundary_ambient_heat_J",
                    )
                },
                integral,
                tuple(
                    (
                        t.time_s,
                        t.identifiers,
                        _snapshot_content(t.before),
                        _snapshot_content(t.after),
                    )
                    for t in transitions
                ),
            )
        )
        identities.extend(
            (
                row,
                row.native,
                row.equipment,
                row.native.network_solution,
                *row.native.states.values(),
                *row.inventories.values(),
                *row.balances.values(),
            )
        )
        previous = row.equipment
    net = finite_sum(
        (b.boundary_mass_kg for b in run.steps[-1].balances.values()), "native net boundary mass"
    )
    # Caller identifies all remaining external mass transfers, including feeds.
    # Internal device transfers cancel in this selected complete inventory set.
    if abs(net - (other_mass - source.total_mass_kg)) > tolerances.mass_absolute_kg:
        raise ValueError(
            "Source plus explicit other external mass does not reconcile with finite inventories"
        )
    return (
        finite_source_sha256(source),
        component_id,
        other_mass,
        tolerances,
        reconciliation,
        run.clock_id,
        run.initial_inventories,
        _snapshot_content(run.initial_equipment),
        records,
    ), tuple(identities)


@dataclass(frozen=True, slots=True)
class FiniteFacilitySource:
    source: IntervalMassSource
    run: DynamicEquipmentRun
    component_id: str
    other_net_boundary_mass_kg: float
    reconciliation_evidence_id: str
    state_projection_evidence_id: str
    tolerances: InventoryTolerances
    _identities: tuple = field(repr=False)
    _content: str = field(repr=False)
    verification_scope: str = "original finite run and accepted-sample mass binding; fixed source-state evidence supplied; no field/enthalpy-plane validation"

    @classmethod
    def bind(
        cls,
        run,
        source,
        *,
        component_id,
        other_net_boundary_mass_kg,
        reconciliation_evidence_id,
        state_projection_evidence_id,
        tolerances,
    ):
        if type(tolerances) is not InventoryTolerances:
            raise TypeError("Declare source-bin/inventory audit tolerances explicitly")
        InventoryTolerances(**_fields(tolerances))
        other = finite(other_net_boundary_mass_kg, "explicit other net external mass")
        _text(state_projection_evidence_id)
        content, identities = _dynamic_source_material(
            run, source, component_id, other, tolerances, reconciliation_evidence_id
        )
        return cls(
            source,
            run,
            component_id,
            other,
            reconciliation_evidence_id,
            state_projection_evidence_id,
            tolerances,
            identities,
            snapshot_sha256((content, state_projection_evidence_id)),
        )

    def require_current(self):
        InventoryTolerances(**_fields(self.tolerances))
        _text(self.state_projection_evidence_id)
        content, identities = _dynamic_source_material(
            self.run,
            self.source,
            self.component_id,
            self.other_net_boundary_mass_kg,
            self.tolerances,
            self.reconciliation_evidence_id,
        )
        if (
            not _same(identities, self._identities)
            or snapshot_sha256((content, self.state_projection_evidence_id)) != self._content
        ):
            raise ValueError(
                "Original finite source/inventory/native accepted-state binding changed"
            )
        return self

    def energy_projection(self):
        """Compare caller-declared fixed source-state enthalpy with native port transport.

        The native transmitted-state enthalpy flow is integrated over every
        accepted sample interval using the same command-aware quadrature as the
        source mass bins. This is a diagnostic; a good mass closure does not
        make an independently projected source state thermodynamically equal
        to the component outlet plane.
        """
        self.require_current()
        nodes = set(self.run.initial_inventories)
        previous = self.run.initial_equipment
        integrals = []
        for index, row in enumerate(self.run.steps):
            integral, _ = _segment_integral(
                self.run,
                index,
                previous,
                self.component_id,
                nodes,
                rate_reader=lambda snapshot: _transfer(
                    snapshot, self.component_id, nodes
                ).outlet_enthalpy_flow_w,
                rate_unit="W",
                integral_unit="J",
            )
            integrals.append(integral)
            previous = row.equipment
        projected = tuple(
            float(mass) * self.source.state.enthalpy_j_kg for mass in self.source.mass_kg
        )
        residuals = tuple(
            integral.value - expected for integral, expected in zip(integrals, projected, strict=True)
        )
        return FiniteSourceEnergyProjection(
            finite_source_sha256(self.source),
            self.component_id,
            self.state_projection_evidence_id,
            tuple(integrals),
            projected,
            residuals,
        )

    def ledger_history(self):
        """Expose the bound source and whole-system mass/energy ledgers over time.

        Native balance values are cumulative from the original finite initial
        inventories. The source trace uses the exact accepted bins, and the
        whole-system mass balance separates the selected outward source from
        the residual net boundary transfer. The energy view includes stored
        fluid/solid energy, native boundary transport and ambient heat.
        """
        self.require_current()
        energy_projection = self.energy_projection()
        initial_mass = finite_sum(
            (item.mass_kg for item in self.run.initial_inventories.values()),
            "initial selected inventory mass",
        )
        initial_energy = finite_sum(
            (item.total_energy_j for item in self.run.initial_inventories.values()),
            "initial selected inventory energy",
        )
        times = [self.run.start_time_s]
        source_mass = [0.]
        inventory_mass = [0.]
        boundary_mass = [0.]
        other_boundary_mass = [0.]
        inventory_energy = [0.]
        boundary_energy = [0.]
        transported_enthalpy = [0.]
        ambient_heat = [0.]
        native_source_enthalpy = [0.]
        projected_source_enthalpy = [0.]
        source_mass_total = native_source_energy_total = projected_source_energy_total = 0.
        for index, row in enumerate(self.run.steps):
            balances = tuple(row.balances.values())
            current_mass = finite_sum(
                (item.mass_kg for item in row.inventories.values()),
                "accepted selected inventory mass",
            )
            current_energy = finite_sum(
                (item.total_energy_j for item in row.inventories.values()),
                "accepted selected inventory energy",
            )
            native_boundary_mass = finite_sum(
                (item.boundary_mass_kg for item in balances),
                "accepted external boundary mass",
            )
            native_boundary_energy = finite_sum(
                (item.boundary_energy_j for item in balances),
                "accepted external boundary energy",
            )
            native_transport = finite_sum(
                (item.transported_enthalpy_j for item in balances),
                "accepted external transport enthalpy",
            )
            native_heat = finite_sum(
                (item.external_heat_j for item in balances),
                "accepted ambient heat",
            )
            source_mass_total = finite_sum(
                (source_mass_total, float(self.source.mass_kg[index])),
                "cumulative selected source mass",
            )
            native_source_energy_total = finite_sum(
                (native_source_energy_total, energy_projection.native_integrals[index].value),
                "cumulative native source outlet enthalpy",
            )
            projected_source_energy_total = finite_sum(
                (projected_source_energy_total,
                 energy_projection.projected_enthalpy_j[index]),
                "cumulative projected source enthalpy",
            )
            times.append(row.time_s)
            source_mass.append(source_mass_total)
            inventory_mass.append(current_mass - initial_mass)
            boundary_mass.append(native_boundary_mass)
            other_boundary_mass.append(native_boundary_mass + source_mass_total)
            inventory_energy.append(current_energy - initial_energy)
            boundary_energy.append(native_boundary_energy)
            transported_enthalpy.append(native_transport)
            ambient_heat.append(native_heat)
            native_source_enthalpy.append(native_source_energy_total)
            projected_source_enthalpy.append(projected_source_energy_total)
        return FiniteFacilityLedgerHistory(
            finite_source_sha256(self.source),
            self.component_id,
            self.run.clock_id,
            self.state_projection_evidence_id,
            np.asarray(times),
            np.asarray(source_mass),
            np.asarray(inventory_mass),
            np.asarray(boundary_mass),
            np.asarray(other_boundary_mass),
            np.asarray(inventory_energy),
            np.asarray(boundary_energy),
            np.asarray(transported_enthalpy),
            np.asarray(ambient_heat),
            np.asarray(native_source_enthalpy),
            np.asarray(projected_source_enthalpy),
            _source_binding=self,
        )


@dataclass(frozen=True, slots=True)
class FiniteSourceEnergyProjection:
    """Accepted native outlet-enthalpy quadrature versus fixed-state projection."""

    source_sha256: str
    component_id: str
    state_projection_evidence_id: str
    native_integrals: tuple[SampledEquipmentIntegral, ...]
    projected_enthalpy_j: tuple[float, ...]
    residual_j: tuple[float, ...]

    def __post_init__(self):
        _text(self.component_id, self.state_projection_evidence_id)
        if (not isinstance(self.source_sha256, str) or len(self.source_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.source_sha256)):
            raise ValueError("A lowercase source SHA-256 identity is required")
        integrals = tuple(self.native_integrals)
        projected = tuple(finite(value, "projected source enthalpy")
                          for value in self.projected_enthalpy_j)
        residuals = tuple(finite(value, "source enthalpy projection residual")
                          for value in self.residual_j)
        if not integrals or len(integrals) != len(projected) or len(integrals) != len(residuals):
            raise ValueError("Every source interval needs native, projected and residual enthalpy")
        clock = integrals[0].clock_id if type(integrals[0]) is SampledEquipmentIntegral else None
        previous_end = None
        for integral, expected, residual in zip(integrals, projected, residuals, strict=True):
            if (type(integral) is not SampledEquipmentIntegral
                    or integral.rate_unit != "W" or integral.integral_unit != "J"
                    or integral.clock_id != clock
                    or (previous_end is not None and integral.start_time_s != previous_end)
                    or not math.isclose(integral.value - expected, residual,
                                        rel_tol=1e-12, abs_tol=1e-10)):
                raise ValueError("Projection residual must match its accepted native interval integral")
            previous_end = integral.end_time_s
        object.__setattr__(self, "native_integrals", integrals)
        object.__setattr__(self, "projected_enthalpy_j", projected)
        object.__setattr__(self, "residual_j", residuals)

    @property
    def native_transport_enthalpy_j(self):
        return tuple(integral.value for integral in self.native_integrals)

    @property
    def total_residual_j(self):
        return finite_sum(self.residual_j, "total source enthalpy projection residual")


@dataclass(frozen=True, slots=True)
class FiniteFacilityLedgerHistory:
    """Time-aligned cumulative conservation ledgers for the selected inventories."""

    source_sha256: str
    component_id: str
    clock_id: str
    state_projection_evidence_id: str
    time_s: np.ndarray
    source_mass_kg: np.ndarray
    inventory_mass_change_kg: np.ndarray
    native_boundary_mass_kg: np.ndarray
    other_net_boundary_mass_kg: np.ndarray
    inventory_energy_change_j: np.ndarray
    native_boundary_energy_j: np.ndarray
    transported_enthalpy_j: np.ndarray
    ambient_heat_j: np.ndarray
    native_source_enthalpy_j: np.ndarray
    projected_source_enthalpy_j: np.ndarray
    _source_binding: FiniteFacilitySource | None = field(default=None, repr=False, compare=False)
    mass_residual_kg: np.ndarray = field(init=False, repr=False)
    energy_residual_j: np.ndarray = field(init=False, repr=False)
    boundary_energy_partition_residual_j: np.ndarray = field(init=False, repr=False)
    source_enthalpy_projection_residual_j: np.ndarray = field(init=False, repr=False)
    _fingerprint: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        _text(self.component_id, self.clock_id, self.state_projection_evidence_id)
        if (not isinstance(self.source_sha256, str) or len(self.source_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.source_sha256)):
            raise ValueError("A lowercase source SHA-256 identity is required")
        names = (
            "time_s", "source_mass_kg", "inventory_mass_change_kg",
            "native_boundary_mass_kg", "other_net_boundary_mass_kg",
            "inventory_energy_change_j", "native_boundary_energy_j",
            "transported_enthalpy_j", "ambient_heat_j", "native_source_enthalpy_j",
            "projected_source_enthalpy_j",
        )
        arrays = {}
        for name in names:
            array = np.array(getattr(self, name), dtype=float, copy=True)
            if array.ndim != 1 or not np.all(np.isfinite(array)):
                raise ValueError(f"Ledger history {name} must be a finite one-dimensional series")
            array = immutable_array(array, name="array")
            arrays[name] = array
        size = len(arrays["time_s"])
        if size < 2 or any(len(array) != size for array in arrays.values()):
            raise ValueError("Every cumulative ledger must share the accepted time axis")
        if np.any(np.diff(arrays["time_s"]) <= 0.):
            raise ValueError("Ledger history clock must be strictly increasing")
        for name in ("source_mass_kg", "inventory_mass_change_kg", "native_boundary_mass_kg",
                     "other_net_boundary_mass_kg", "inventory_energy_change_j",
                     "native_boundary_energy_j", "transported_enthalpy_j", "ambient_heat_j",
                     "native_source_enthalpy_j", "projected_source_enthalpy_j"):
            if arrays[name][0] != 0.:
                raise ValueError(f"Cumulative ledger {name} must start at zero")
        mass_residual = arrays["inventory_mass_change_kg"] - arrays["native_boundary_mass_kg"]
        energy_residual = arrays["inventory_energy_change_j"] - arrays["native_boundary_energy_j"]
        energy_partition = (arrays["native_boundary_energy_j"]
                            - arrays["transported_enthalpy_j"] - arrays["ambient_heat_j"])
        source_projection = (arrays["native_source_enthalpy_j"]
                            - arrays["projected_source_enthalpy_j"])
        for name, values in (
            ("mass_residual_kg", mass_residual),
            ("energy_residual_j", energy_residual),
            ("boundary_energy_partition_residual_j", energy_partition),
            ("source_enthalpy_projection_residual_j", source_projection),
        ):
            values = np.array(values, dtype=float, copy=True)
            values = immutable_array(values, name="values")
            object.__setattr__(self, name, values)
        for name, array in arrays.items():
            object.__setattr__(self, name, array)
        if not np.allclose(arrays["other_net_boundary_mass_kg"],
                           arrays["native_boundary_mass_kg"] + arrays["source_mass_kg"],
                           rtol=1e-12, atol=1e-12):
            raise ValueError("Residual external mass must equal native boundary mass plus source outflow")
        if self._source_binding is not None:
            self._source_binding.require_current()
            if (self.source_sha256 != finite_source_sha256(self._source_binding.source)
                    or self.component_id != self._source_binding.component_id
                    or self.clock_id != self._source_binding.run.clock_id
                    or self.state_projection_evidence_id
                    != self._source_binding.state_projection_evidence_id):
                raise ValueError("Ledger history is detached from its finite-source binding")
        object.__setattr__(self, "_fingerprint", self._current_fingerprint())

    def _current_fingerprint(self):
        names = (
            "time_s", "source_mass_kg", "inventory_mass_change_kg", "native_boundary_mass_kg",
            "other_net_boundary_mass_kg", "inventory_energy_change_j", "native_boundary_energy_j",
            "transported_enthalpy_j", "ambient_heat_j", "native_source_enthalpy_j",
            "projected_source_enthalpy_j", "mass_residual_kg", "energy_residual_j",
            "boundary_energy_partition_residual_j", "source_enthalpy_projection_residual_j",
        )
        content = tuple(
            (name, snapshot_sha256(getattr(self, name))) for name in names
        )
        binding = self._source_binding
        binding_identity = None if binding is None else (
            id(binding), id(binding.run), id(binding.source), binding._content,
        )
        return snapshot_sha256((self.source_sha256, self.component_id, self.clock_id,
                                self.state_projection_evidence_id, content, binding_identity))

    def require_current(self):
        if self._source_binding is not None:
            self._source_binding.require_current()
        if self._current_fingerprint() != self._fingerprint:
            raise ValueError("Finite facility ledger history changed after capture")
        return self


@dataclass(frozen=True, slots=True)
class ConditionalDependence:
    scenario_id: str
    operating_case_id: str
    operating_mode_id: str
    clock_id: str
    conditioning_evidence_id: str
    factorization_evidence_id: str
    frequency_scope_evidence_id: str
    mechanism_by_factor_id: Mapping[str, str]
    resolved_protection_mechanism_ids: tuple[str, ...]
    interpretation: str = (
        "conditional on this resolved protection trajectory; no additional reliability credit"
    )

    def __post_init__(self):
        _text(
            self.scenario_id,
            self.operating_case_id,
            self.operating_mode_id,
            self.clock_id,
            self.conditioning_evidence_id,
            self.factorization_evidence_id,
            self.frequency_scope_evidence_id,
        )
        mapping, resolved = (
            dict(self.mechanism_by_factor_id),
            tuple(self.resolved_protection_mechanism_ids),
        )
        if (
            self.interpretation
            != "conditional on this resolved protection trajectory; no additional reliability credit"
        ):
            raise ValueError("Keep the explicit resolved-path conditional interpretation")
        _text(*mapping.keys(), *mapping.values(), *resolved)
        if not resolved or len(set(resolved)) != len(resolved):
            raise ValueError(
                "Declare distinct protection mechanisms already resolved by this physical path"
            )
        if set(mapping.values()) & set(resolved):
            raise ValueError(
                "An already resolved protection path cannot receive additional numerical reliability credit"
            )
        object.__setattr__(self, "mechanism_by_factor_id", MappingProxyType(mapping))
        object.__setattr__(self, "resolved_protection_mechanism_ids", resolved)


@dataclass(frozen=True, slots=True)
class FacilityRiskResult:
    native_conditional_result: object
    finite_source: FiniteFacilitySource
    protected_run: ProtectedEquipmentRun
    dependence: ConditionalDependence
    status: str = "conditional prescribed-path result; no complete facility risk or protection reliability qualification"
    _issuer: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _dependence_sha256: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        expected_issuer = tuple(id(value) for value in (
            self.native_conditional_result, self.finite_source,
            self.protected_run, self.dependence,
        ))
        if _PENDING_FACILITY_RISK_RESULT_ISSUERS.get(self._issuer) != expected_issuer:
            raise TypeError("Create facility-risk receipts through evaluate_facility_risk")
        _PENDING_FACILITY_RISK_RESULT_ISSUERS.pop(self._issuer)
        object.__setattr__(self, "_binding", self._object_bindings())
        object.__setattr__(self, "_dependence_sha256", snapshot_sha256(self.dependence))
        self.require_current()

    def _object_bindings(self):
        return (self.native_conditional_result, self.finite_source, self.protected_run, self.dependence)

    def require_current(self):
        if self.status != "conditional prescribed-path result; no complete facility risk or protection reliability qualification":
            raise ValueError("Facility-risk scope label cannot be changed")
        if not self._binding or any(current is not original for current, original in
                                    zip(self._object_bindings(), self._binding, strict=True)):
            raise ValueError("Facility-risk receipt lost its original result/source/protection/dependence objects")
        if type(self.native_conditional_result) is not ConditionalRiskResult:
            raise TypeError("Retain the original native conditional-risk result")
        if type(self.finite_source) is not FiniteFacilitySource:
            raise TypeError("Retain the original admitted finite facility source")
        if type(self.protected_run) is not ProtectedEquipmentRun:
            raise TypeError("Retain the original accepted protected equipment run")
        if type(self.dependence) is not ConditionalDependence:
            raise TypeError("Retain the original conditional dependence declaration")
        if snapshot_sha256(self.dependence) != self._dependence_sha256:
            raise ValueError("Original conditional-dependence evidence/content changed")
        self.native_conditional_result.require_current()
        self.finite_source.require_current()
        self.protected_run.require_current()
        ConditionalDependence(**_fields(self.dependence))
        result = self.native_conditional_result
        if (result.source is not self.finite_source.source
                or self.finite_source.run is not self.protected_run.native_run):
            raise ValueError("Native risk, finite source and accepted protection run no longer share their original source")
        mechanisms = {plan.action.mechanism_id for plan in self.protected_run.plans}
        if (set(self.dependence.resolved_protection_mechanism_ids) != mechanisms
                or self.dependence.clock_id != self.finite_source.run.clock_id
                or self.dependence.operating_mode_id != self.protected_run.mode_definition_id
                or result.original_request.frequency.scenario_id != self.dependence.scenario_id
                or result.original_request.frequency.operating_case_id != self.dependence.operating_case_id):
            raise ValueError("Native conditional result no longer matches the accepted source/protection path")
        required = {
            self.dependence.conditioning_evidence_id,
            self.dependence.factorization_evidence_id,
            self.dependence.frequency_scope_evidence_id,
        }
        if not required <= {item.id for item in result.native_context.evidence}:
            raise ValueError("Native risk context no longer retains dependence evidence")
        return self


def evaluate_facility_risk(
    native,
    request,
    context,
    *,
    finite_source,
    protected_run,
    dependence,
    receptor,
    harm_bindings,
    evidence,
):
    """Audit declared dependence, then delegate all probability/receipt math."""
    result = None
    try:
        if (
            type(finite_source) is not FiniteFacilitySource
            or type(protected_run) is not ProtectedEquipmentRun
            or type(dependence) is not ConditionalDependence
        ):
            raise TypeError(
                "Use actual finite-source, accepted protection and dependence contracts"
            )
        finite_source.require_current()
        protected_run.require_current()
        if finite_source.run is not protected_run.native_run:
            raise ValueError(
                "Risk source and protection actions came from different actual finite runs"
            )
        ConditionalDependence(**_fields(dependence))
        mechanisms = {p.action.mechanism_id for p in protected_run.plans}
        if (
            set(dependence.resolved_protection_mechanism_ids) != mechanisms
            or dependence.clock_id != finite_source.run.clock_id
            or dependence.operating_mode_id != protected_run.mode_definition_id
        ):
            raise ValueError(
                "Conditional mode/clock/resolved mechanism set differs from the actual protection path"
            )
        native.require_current()
        r, c = native.risk_module, native.contracts
        if type(request) is not r.RiskInput or type(context) is not c.Context:
            raise TypeError("Use original actual native risk input/context")
        owned = r.RiskInput.model_validate(request.model_dump(mode="python"), strict=True)
        owned_context = c.Context.model_validate(context.model_dump(mode="python"), strict=True)
        if (
            owned.frequency.scenario_id != dependence.scenario_id
            or owned.frequency.operating_case_id != dependence.operating_case_id
        ):
            raise ValueError("Supplied annual LOC frequency scenario/operating-case differs")
        all_factors = set(owned.frequency.included_factor_ids)
        for branch in owned.branches:
            factors = (
                *owned.frequency.included_factor_ids,
                *branch.probability_factor_ids,
                branch.harm_factor_id,
                *(f.id for f in branch.factors),
            )
            all_factors.update(factors)
            if set(factors) - set(dependence.mechanism_by_factor_id):
                raise ValueError(
                    "Every upstream/branch/harm/post-factor needs explicit mechanism ownership"
                )
            physical = tuple(dependence.mechanism_by_factor_id[f] for f in factors)
            if len(physical) != len(set(physical)):
                raise ValueError(
                    "Renamed factor IDs would credit the same physical mechanism twice"
                )
        if set(dependence.mechanism_by_factor_id) != all_factors:
            raise ValueError("Probability ownership must exactly cover this native request")
        required = {
            dependence.conditioning_evidence_id,
            dependence.factorization_evidence_id,
            dependence.frequency_scope_evidence_id,
            protected_run.scenario_evidence_id,
            finite_source.reconciliation_evidence_id,
            finite_source.state_projection_evidence_id,
        }
        required.update(p.action.evidence_id for p in protected_run.plans)
        required.update(p.alarm.decision_evidence_id for p in protected_run.plans)
        required.update(
            v for p in protected_run.plans for v in p.alarm.sensor_evidence_ids.values()
        )
        if not required <= {item.id for item in owned_context.evidence}:
            raise ValueError(
                "Native context must preserve source/action/sensor/dependence/frequency evidence"
            )
        before = snapshot_sha256(dependence)
        result = conditional_risk(
            native,
            request,
            context,
            source=finite_source.source,
            receptor=receptor,
            harm_bindings=harm_bindings,
            evidence=evidence,
        )
        finite_source.require_current()
        protected_run.require_current()
        if snapshot_sha256(dependence) != before:
            raise ValueError(
                "Conditional mechanism/dependence declaration changed during native risk"
            )
        receipt = FacilityRiskResult(
            result,
            finite_source,
            protected_run,
            dependence,
            _issuer=_issue_facility_risk_result_token(
                (result, finite_source, protected_run, dependence)
            ),
        )
        return receipt.require_current()
    except Exception as error:
        failure = FacilityProtectionError(
            str(error),
            stage="conditional-risk-binding",
            original=error,
            owner=protected_run,
            result=result,
        )
        failure.original_request, failure.original_context = request, context
        failure.finite_source, failure.dependence = finite_source, dependence
        failure.receptor, failure.harm_bindings, failure.evidence = (
            receptor,
            harm_bindings,
            evidence,
        )
        raise failure from error
