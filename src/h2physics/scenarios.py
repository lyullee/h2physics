"""Lazy Python dependency composition; no solver, registry or engine fallback.

Nodes call existing selected model APIs. The graph schedules dependencies only;
physical clocks, conservation, phase and reference admission remain those APIs'
responsibility. Construction performs no model calculation.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


_PENDING_SCENARIO_RESULT_ISSUERS = set()


def _name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare a nonblank {label}")
    return value


@dataclass(frozen=True, slots=True)
class ScenarioValue:
    """Explicit caller input retaining the original Python object's identity."""

    value: object = field(repr=False)


@dataclass(frozen=True, slots=True)
class ScenarioOutput:
    """Bind an upstream result, optionally through an explicit caller selector."""

    node_id: str
    select: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        _name(self.node_id, "upstream node ID")
        if self.select is not None and not callable(self.select):
            raise TypeError("An output selector must be callable when supplied")


@dataclass(frozen=True, slots=True)
class ScenarioNode:
    node_id: str
    operation: object = field(repr=False, compare=False)
    inputs: Mapping = field(repr=False)
    evidence_id: str

    def __post_init__(self):
        _name(self.node_id, "node ID")
        _name(self.evidence_id, "node evidence ID")
        if not callable(self.operation):
            raise TypeError("A scenario node requires an explicit callable operation")
        if not isinstance(self.inputs, Mapping):
            raise TypeError("Node inputs must map keyword names to explicit bindings")
        inputs = dict(self.inputs)
        for name, binding in inputs.items():
            if (not isinstance(name, str) or not name.isidentifier()
                    or not isinstance(binding, (ScenarioValue, ScenarioOutput))):
                raise ValueError("Each keyword needs a ScenarioValue or ScenarioOutput binding")
        object.__setattr__(self, "inputs", MappingProxyType(inputs))

    @property
    def dependencies(self):
        return tuple(dict.fromkeys(binding.node_id for binding in self.inputs.values()
                                   if isinstance(binding, ScenarioOutput)))


@dataclass(frozen=True, slots=True)
class ScenarioNodeResult:
    node: ScenarioNode
    resolved_inputs: Mapping = field(repr=False)
    result: object = field(repr=False)

    def __post_init__(self):
        if type(self.node) is not ScenarioNode:
            raise TypeError("A node result must retain its ScenarioNode")
        if not isinstance(self.resolved_inputs, Mapping):
            raise TypeError("Resolved inputs must be a keyword mapping")
        if set(self.resolved_inputs) != set(self.node.inputs):
            raise ValueError("Resolved input names must match the node bindings")
        object.__setattr__(self, "resolved_inputs", MappingProxyType(dict(self.resolved_inputs)))


def _scenario_result_bindings(nodes):
    """Capture graph-record and object lineage without inspecting domain payloads."""
    def binding_signature(binding):
        if isinstance(binding, ScenarioValue):
            return (ScenarioValue, id(binding.value))
        if isinstance(binding, ScenarioOutput):
            return (ScenarioOutput, binding.node_id, id(binding.select))
        return (type(binding), id(binding))

    return tuple(
        (
            id(record), id(record.node), record.node.node_id, record.node.evidence_id,
            id(record.node.operation),
            tuple(sorted((name, binding_signature(value))
                         for name, value in record.node.inputs.items())),
            id(record.resolved_inputs),
            tuple(sorted((name, id(value)) for name, value in record.resolved_inputs.items())),
            id(record.result),
        )
        for record in nodes
    )


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario_id: str
    nodes: tuple[ScenarioNodeResult, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _bindings: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SCENARIO_RESULT_ISSUERS:
            raise TypeError("Create scenario results through OperationalScenario.run()")
        _PENDING_SCENARIO_RESULT_ISSUERS.remove(self._issuer_token)
        _name(self.scenario_id, "scenario ID")
        nodes = tuple(self.nodes)
        if not nodes or any(type(record) is not ScenarioNodeResult for record in nodes):
            raise TypeError("A scenario result requires executed node receipts")
        if len({record.node.node_id for record in nodes}) != len(nodes):
            raise ValueError("Scenario result node IDs must be unique")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "_bindings", (
            self.scenario_id, id(self._issuer_token), _scenario_result_bindings(nodes),
        ))

    def require_current(self):
        """Ensure graph-issued node/parent/input/output identities still match.

        Domain result contents remain the responsibility of each returned
        owner's own freshness contract.
        """
        try:
            current = _scenario_result_bindings(self.nodes)
        except Exception as cause:
            raise ValueError(
                "Scenario result lost its original graph-issued node or object lineage"
            ) from cause
        if (not self._bindings or self.scenario_id != self._bindings[0]
                or id(self._issuer_token) != self._bindings[1]
                or current != self._bindings[2]):
            raise ValueError("Scenario result lost its original graph-issued node or object lineage")
        return self

    @property
    def results(self):
        """Original returned objects indexed in deterministic execution order."""
        self.require_current()
        return MappingProxyType({record.node.node_id: record.result for record in self.nodes})


class ScenarioExecutionError(RuntimeError):
    """Preserve the original failure, resolved inputs and completed node prefix."""

    def __init__(self, scenario_id, node, stage, cause, completed, resolved_inputs,
                 operation_result=None):
        self.scenario_id = scenario_id
        self.node = node
        self.stage = stage
        self.cause = cause
        self.completed = tuple(completed)
        self.resolved_inputs = MappingProxyType(dict(resolved_inputs))
        self.provider_result = getattr(cause, "result", None)
        self.operation_result = operation_result
        super().__init__(f"Scenario {scenario_id!r} node {node.node_id!r} failed during {stage}")


@dataclass(frozen=True, slots=True)
class OperationalScenario:
    """Named acyclic dependency graph with deterministic, sequential evaluation.

    Independent ready nodes follow declaration order. Calls are never retried or
    replaced. Explicit output selectors adapt existing Python receipts without
    introducing a second model registry. Mutable domain inputs retain their caller
    identity; this graph makes no input immutability or physical-validity claim.
    """

    scenario_id: str
    nodes: tuple[ScenarioNode, ...]
    execution_order: tuple[str, ...] = field(init=False)

    def __post_init__(self):
        _name(self.scenario_id, "scenario ID")
        nodes = tuple(self.nodes)
        if not nodes or any(type(node) is not ScenarioNode for node in nodes):
            raise TypeError("Supply one or more ScenarioNode objects")
        index = {node.node_id: node for node in nodes}
        if len(index) != len(nodes):
            raise ValueError("Scenario node IDs must be unique")
        for node in nodes:
            missing = set(node.dependencies)-index.keys()
            if missing:
                raise ValueError(f"Node {node.node_id!r} references missing nodes {sorted(missing)}")
        remaining = list(nodes)
        order = []
        while remaining:
            ready = next((node for node in remaining
                          if set(node.dependencies) <= set(order)), None)
            if ready is None:
                raise ValueError("Scenario dependencies contain a cycle")
            order.append(ready.node_id)
            remaining.remove(ready)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "execution_order", tuple(order))

    def run(self, *, targets=None):
        """Execute all nodes or only requested outputs and their ancestors.

        ``targets`` is a nonempty sequence of declared node IDs. Selecting a
        subset preserves declaration-based dependency order and avoids invoking
        unrelated operations. Every call starts a fresh execution; results from
        earlier calls are never silently reused.
        """
        index = {node.node_id: node for node in self.nodes}
        if targets is None:
            selected = set(index)
        else:
            if isinstance(targets, (str, bytes)):
                raise TypeError("Targets must be a sequence of node IDs, not one string")
            requested = tuple(targets)
            if not requested:
                raise ValueError("Declare at least one target node")
            for node_id in requested:
                _name(node_id, "target node ID")
                if node_id not in index:
                    raise ValueError(f"Unknown scenario target node {node_id!r}")
            selected = set()
            pending = list(requested)
            while pending:
                node_id = pending.pop()
                if node_id not in selected:
                    selected.add(node_id)
                    pending.extend(index[node_id].dependencies)
        outputs = {}
        completed = []
        for node_id in self.execution_order:
            if node_id not in selected:
                continue
            node = index[node_id]
            resolved = {}
            result = None
            stage = "input binding"
            try:
                for name, binding in node.inputs.items():
                    if isinstance(binding, ScenarioValue):
                        resolved[name] = binding.value
                    else:
                        value = outputs[binding.node_id]
                        resolved[name] = value if binding.select is None else binding.select(value)
                stage = "operation"
                result = node.operation(**resolved)
                stage = "result recording"
                record = ScenarioNodeResult(node, resolved, result)
            except Exception as cause:
                raise ScenarioExecutionError(self.scenario_id, node, stage, cause,
                                             completed, resolved, result) from cause
            outputs[node_id] = result
            completed.append(record)
        token = object()
        _PENDING_SCENARIO_RESULT_ISSUERS.add(token)
        try:
            return ScenarioResult(self.scenario_id, tuple(completed), token)
        except Exception:
            _PENDING_SCENARIO_RESULT_ISSUERS.discard(token)
            raise


__all__ = ["ScenarioValue", "ScenarioOutput", "ScenarioNode", "ScenarioNodeResult",
           "ScenarioResult", "ScenarioExecutionError", "OperationalScenario"]
