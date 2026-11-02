"""Common-clock receipt for results from the existing LH2DT operation adapters.

This module audits ownership and alignment only. It does not execute equipment,
apply actuator outputs to a native network, or add event localization.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from ..core import finite
from .facility_protection import ProtectedEquipmentRun, ReliefProtectionRecord
from .lh2dt_dynamics import DynamicEquipmentRun
from .lh2dt_relief import ReliefTankTrace
from .lh2dt_supply import Lh2dtSupplyAssembly
from .lh2dt_valve_actuator import ActuatedValveTrace
from .result_provenance import recorded_content_sha256
from .thermal_utilities import ThermalUtilityLedger


class OperationalScenarioError(ValueError):
    """The supplied native operation pieces do not form an admitted clock window."""


def _supply_topology_digest(supply: Lh2dtSupplyAssembly) -> str:
    """Fingerprint the retained host/native supply graph without solving it."""
    network = supply.network
    driver = supply.driver
    if driver.network is not network:
        raise OperationalScenarioError("Supply driver no longer owns the retained equipment network")
    native = network.native
    try:
        links = tuple((
            str(link.name), str(link.left), str(link.right),
            id(link.component), str(link.source_port_id), str(link.target_port_id),
        ) for link in native.links)
        boundaries = tuple(sorted(str(name) for name in native.boundaries))
        junctions = tuple(sorted(str(name) for name in native.junctions))
        power_readers = tuple(sorted((str(name), id(reader))
                                     for name, reader in network._power_readers.items()))
        inventory_nodes = tuple(sorted((str(name), id(binding.native_node), id(binding.inventory_reader))
                                       for name, binding in driver.nodes.items()))
        modes = tuple(sorted((str(name), id(mode.component), id(mode.power_reader))
                             for name, mode in supply.pump.modes.items()))
        models = tuple(sorted((str(name), id(model))
                              for name, model in supply.native_models.items()))
    except (AttributeError, TypeError) as error:
        raise OperationalScenarioError("Supply assembly does not expose an inspectable native graph") from error
    return recorded_content_sha256((
        id(network), id(native), id(driver), id(driver.network),
        id(network.bridge), id(network.bridge.native), id(network.state_factory),
        boundaries, junctions, links, power_readers,
        inventory_nodes, id(driver.simulator_factory), id(driver.tolerances),
        id(supply.pump), id(supply.pump.properties), supply.pump.mode_id, modes,
        id(supply.outlet), models, tuple(sorted((str(key), str(value))
                                                for key, value in supply.node_ids.items())),
    ))


@dataclass(frozen=True, slots=True)
class OperationalScenarioReceipt:
    """Retain operation results whose declared identities and time windows agree.

    `binding_evidence_ids` must include `supply_to_dynamic`, `actuator:<actuator_id>`,
    `relief:<zero-based-index>`, `protection:<zero-based-index>`, and
    `protected_run:<zero-based-index>` entries. These
    attest cross-owner links that native result records do not encode. Protection
    records must also refer by identity to one of the retained relief traces.
    When `utility_ledger` is supplied, `utility_to_dynamic` attests the external
    relationship; every utility profile must use this exact clock and full
    operation window. This is an evidence/time join, not thermal coupling.
    """

    scenario_id: str
    binding_evidence_ids: Mapping[str, str]
    clock_id: str
    supply: Lh2dtSupplyAssembly
    dynamic_run: DynamicEquipmentRun
    actuator_traces: tuple[ActuatedValveTrace, ...]
    relief_traces: tuple[ReliefTankTrace, ...]
    protection_records: tuple[ReliefProtectionRecord, ...]
    start_time_s: float
    end_time_s: float
    protected_runs: tuple[ProtectedEquipmentRun, ...] = ()
    utility_ledger: ThermalUtilityLedger | None = None
    _identity_binding: tuple[Any, ...] = field(init=False, repr=False, compare=False)
    _content_sha256: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for value, name in ((self.scenario_id, "scenario_id"),
                            (self.clock_id, "clock_id")):
            if not isinstance(value, str) or not value.strip():
                raise OperationalScenarioError(f"{name} must be explicitly identified")
        bindings = dict(self.binding_evidence_ids)
        if any(not isinstance(key, str) or not key.strip()
               or not isinstance(value, str) or not value.strip()
               for key, value in bindings.items()):
            raise OperationalScenarioError("Every cross-owner binding needs a nonempty evidence ID")
        if type(self.supply) is not Lh2dtSupplyAssembly:
            raise TypeError("supply must be an Lh2dtSupplyAssembly")
        if type(self.dynamic_run) is not DynamicEquipmentRun:
            raise TypeError("dynamic_run must be an accepted DynamicEquipmentRun")
        self.dynamic_run.require_current()
        if self.dynamic_run.clock_id != self.clock_id:
            raise OperationalScenarioError("Dynamic run clock identity does not match the scenario")
        if not self.dynamic_run.steps:
            raise OperationalScenarioError("An operation receipt requires at least one accepted native step")
        start = finite(self.start_time_s, "start_time_s")
        end = finite(self.end_time_s, "end_time_s")
        native_start = finite(self.dynamic_run.start_time_s, "native run start")
        native_end = finite(self.dynamic_run.steps[-1].time_s, "native run end")
        if start != native_start or end != native_end or end <= start:
            raise OperationalScenarioError("Receipt window must exactly match the accepted dynamic run")

        topology_nodes = tuple(self.supply.node_ids.values())
        if not topology_nodes or len(set(topology_nodes)) != len(topology_nodes):
            raise OperationalScenarioError("Supply topology must expose unique native inventory node IDs")
        if not set(topology_nodes).issubset(self.dynamic_run.initial_inventories):
            raise OperationalScenarioError("Dynamic run lacks one or more declared supply inventory nodes")
        for step in self.dynamic_run.steps:
            if step.time_s < start or step.time_s > end:
                raise OperationalScenarioError("Accepted dynamic step lies outside the declared run window")
            if not set(topology_nodes).issubset(step.inventories):
                raise OperationalScenarioError("A dynamic step omits a declared supply inventory node")
        for transition in self.dynamic_run.transitions:
            if not start <= transition.time_s <= end:
                raise OperationalScenarioError("Equipment command transition lies outside the run window")

        actuators = tuple(self.actuator_traces)
        reliefs = tuple(self.relief_traces)
        protections = tuple(self.protection_records)
        protected_runs = tuple(self.protected_runs)
        utilities = self.utility_ledger
        if any(type(trace) is not ActuatedValveTrace for trace in actuators):
            raise TypeError("Every actuator trace must be an ActuatedValveTrace")
        if any(type(trace) is not ReliefTankTrace for trace in reliefs):
            raise TypeError("Every relief result must be a ReliefTankTrace")
        if any(type(record) is not ReliefProtectionRecord for record in protections):
            raise TypeError("Protection records must be ReliefProtectionRecord instances")
        if any(type(run) is not ProtectedEquipmentRun for run in protected_runs):
            raise TypeError("Prescribed protection runs must be ProtectedEquipmentRun instances")
        required_bindings = {"supply_to_dynamic"}
        required_bindings.update(f"actuator:{trace.actuator.actuator_id}" for trace in actuators)
        required_bindings.update(f"relief:{index}" for index in range(len(reliefs)))
        required_bindings.update(f"protection:{index}" for index in range(len(protections)))
        required_bindings.update(f"protected_run:{index}" for index in range(len(protected_runs)))
        if utilities is not None:
            if type(utilities) is not ThermalUtilityLedger:
                raise TypeError("utility_ledger must be an accepted ThermalUtilityLedger")
            required_bindings.add("utility_to_dynamic")
        missing_bindings = required_bindings-set(bindings)
        if missing_bindings:
            raise OperationalScenarioError(
                "Missing explicit cross-owner binding evidence: " + ", ".join(sorted(missing_bindings))
            )
        if len({trace.actuator.actuator_id for trace in actuators}) != len(actuators):
            raise OperationalScenarioError("Actuator identities must be unique within the receipt")
        for trace in actuators:
            trace.require_current()
            if trace.actuator.clock_id != self.clock_id:
                raise OperationalScenarioError("Actuator trace uses a different clock identity")
            if not trace.points:
                raise OperationalScenarioError("Actuator trace contains no accepted output points")
            sample_times = tuple(finite(point.time_s, "actuator sample time") for point in trace.points)
            if (any(right <= left for left, right in zip(sample_times, sample_times[1:]))
                    or sample_times[0] < start or sample_times[-1] > end):
                raise OperationalScenarioError("Actuator output times must increase inside the dynamic run")
            for command in trace.commands:
                if command.start_s < start or command.end_s > end:
                    raise OperationalScenarioError("Actuator command exceeds the native operation window")

        if len({id(trace) for trace in reliefs}) != len(reliefs):
            raise OperationalScenarioError("Duplicate native relief trace references are not allowed")
        for trace in reliefs:
            trace.require_current()
            if trace.clock_id != self.clock_id:
                raise OperationalScenarioError("Relief trace uses a different clock identity")
            if trace.time_s[0] < start or trace.time_s[-1] > end:
                raise OperationalScenarioError("Relief trace samples exceed the dynamic operation window")
        relief_ids = {id(trace) for trace in reliefs}
        for record in protections:
            record.require_current()
            if id(record.trace) not in relief_ids:
                raise OperationalScenarioError("Protection record refers to an unretained relief trace")
            if record.trace.clock_id != self.clock_id:
                raise OperationalScenarioError("Protection and operation clock identities differ")
            if not start <= record.transition.time_s <= end:
                raise OperationalScenarioError("Protection transition lies outside the operation window")

        for protected in protected_runs:
            protected.require_current()
            if protected.native_run is not self.dynamic_run:
                raise OperationalScenarioError(
                    "Protected replay must retain this exact accepted dynamic run"
                )
            if protected.native_run.clock_id != self.clock_id:
                raise OperationalScenarioError("Protected replay uses a different clock identity")
            if any(not start <= accepted.invocation.time_s <= end
                   for accepted in protected.accepted):
                raise OperationalScenarioError("Protected action lies outside the operation window")

        if utilities is not None:
            utilities.require_current()
            if not utilities.profiles:
                raise OperationalScenarioError("A linked utility ledger must retain at least one heat profile")
            for profile in utilities.profiles:
                window = profile.snapshot.window
                if (window.clock_id != self.clock_id or window.start_s != start
                        or window.end_s != end):
                    raise OperationalScenarioError(
                        "Utility profiles must match the scenario clock and full operation window"
                    )

        object.__setattr__(self, "start_time_s", start)
        object.__setattr__(self, "end_time_s", end)
        object.__setattr__(self, "actuator_traces", actuators)
        object.__setattr__(self, "relief_traces", reliefs)
        object.__setattr__(self, "protection_records", protections)
        object.__setattr__(self, "protected_runs", protected_runs)
        object.__setattr__(self, "binding_evidence_ids", MappingProxyType(bindings))
        object.__setattr__(self, "_identity_binding", (
            id(self.supply), id(self.dynamic_run),
            tuple(map(id, actuators)), tuple(map(id, reliefs)), tuple(map(id, protections)),
            tuple(map(id, protected_runs)),
            id(utilities),
        ))
        object.__setattr__(self, "_content_sha256", self._current_content_sha256())

    def _current_content_sha256(self) -> str:
        """Seal receipt declarations and stored result records without re-running models."""
        return recorded_content_sha256((
            self.scenario_id, self.binding_evidence_ids, self.clock_id,
            self.start_time_s, self.end_time_s,
            self.supply.node_ids, id(self.supply.network), id(self.supply.driver),
            id(self.supply.pump), id(self.supply.outlet),
            _supply_topology_digest(self.supply),
            self.dynamic_run, self.actuator_traces, self.relief_traces,
            self.protection_records, self.utility_ledger,
            self.protected_runs,
        ))

    def require_current(self) -> OperationalScenarioReceipt:
        expected = (
            id(self.supply), id(self.dynamic_run),
            tuple(map(id, self.actuator_traces)), tuple(map(id, self.relief_traces)),
            tuple(map(id, self.protection_records)), tuple(map(id, self.protected_runs)),
            id(self.utility_ledger),
        )
        if expected != self._identity_binding:
            raise OperationalScenarioError("Scenario receipt lost its original native result objects")
        if self._current_content_sha256() != self._content_sha256:
            raise OperationalScenarioError(
                "Scenario declarations or retained dynamic inventory/transfer ledgers changed"
            )
        self.dynamic_run.require_current()
        for trace in self.actuator_traces:
            trace.require_current()
        for trace in self.relief_traces:
            trace.require_current()
        for record in self.protection_records:
            record.require_current()
        for protected in self.protected_runs:
            protected.require_current()
        if self.utility_ledger is not None:
            self.utility_ledger.require_current()
        return self


def bind_operational_scenario(
    *,
    scenario_id: str,
    binding_evidence_ids: Mapping[str, str],
    clock_id: str,
    supply: Lh2dtSupplyAssembly,
    dynamic_run: DynamicEquipmentRun,
    actuator_traces: Sequence[ActuatedValveTrace],
    relief_traces: Sequence[ReliefTankTrace],
    protection_records: Sequence[ReliefProtectionRecord] = (),
    protected_runs: Sequence[ProtectedEquipmentRun] = (),
    utility_ledger: ThermalUtilityLedger | None = None,
) -> OperationalScenarioReceipt:
    """Bind accepted operation outputs without executing another physical model."""
    if type(dynamic_run) is not DynamicEquipmentRun or type(supply) is not Lh2dtSupplyAssembly:
        raise TypeError("Use original supply topology and accepted native dynamic run")
    if not dynamic_run.steps:
        raise OperationalScenarioError("Dynamic run has no accepted output window")
    return OperationalScenarioReceipt(
        scenario_id=scenario_id,
        binding_evidence_ids=binding_evidence_ids,
        clock_id=clock_id,
        supply=supply,
        dynamic_run=dynamic_run,
        actuator_traces=tuple(actuator_traces),
        relief_traces=tuple(relief_traces),
        protection_records=tuple(protection_records),
        protected_runs=tuple(protected_runs),
        utility_ledger=utility_ledger,
        start_time_s=dynamic_run.start_time_s,
        end_time_s=dynamic_run.steps[-1].time_s,
    ).require_current()
