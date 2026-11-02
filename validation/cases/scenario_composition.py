"""Deferred dependency composition contract; no operation runs during discovery."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="operational-scenario-dependency-composition",
        profile="model-selection",
        entrypoint=__name__ + ":validate_composition",
        invariants=(
            "lazy construction and deterministic dependency order",
            "target selection executes requested ancestors only",
            "original result identity and explicit input binding survive composition",
            "selector failure preserves original exception and completed prefix",
            "cycles and unknown targets fail before any operation",
            "configuration maps and result maps are copied and read-only",
            "scenario result receipts require a one-use graph-run issuer",
            "there is no module-level scenario result token factory callable by clients",
            "post-issue node, binding, parent or output substitution is rejected before result exposure",
        ),
    ),)


def validate_composition(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import FrozenInstanceError
    from dataclasses import replace

    from h2physics.scenarios import (
        OperationalScenario,
        ScenarioExecutionError,
        ScenarioNode,
        ScenarioResult,
        ScenarioOutput,
        ScenarioValue,
    )
    import h2physics.scenarios as scenarios_module

    assert not hasattr(scenarios_module, "_issue_scenario_result_token")

    calls = []
    original = object()

    def source():
        calls.append("source")
        return original

    def receiver(value):
        calls.append("receiver")
        assert value is original
        return value

    def unrelated():
        calls.append("unrelated")
        return object()

    mutable_bindings = {"value": ScenarioOutput("source")}
    receive = ScenarioNode("receiver", receiver, mutable_bindings, "receiver-evidence")
    mutable_bindings.clear()
    graph = OperationalScenario("composition", (
        receive,
        ScenarioNode("unrelated", unrelated, {}, "unrelated-evidence"),
        ScenarioNode("source", source, {}, "source-evidence"),
    ))
    assert calls == []
    assert graph.execution_order == ("unrelated", "source", "receiver")
    partial = graph.run(targets=("receiver",))
    for forged in (
        lambda: ScenarioResult(partial.scenario_id, partial.nodes),
        lambda: replace(partial, scenario_id="forged-scenario"),
    ):
        try:
            forged()
        except TypeError:
            pass
        else:
            raise AssertionError("A fabricated or cloned scenario result receipt was admitted")
    assert calls == ["source", "receiver"]
    assert partial.results["receiver"] is original
    assert partial.nodes[-1].resolved_inputs["value"] is original
    output_record = partial.nodes[-1]
    original_output = output_record.result
    object.__setattr__(output_record, "result", object())
    try:
        partial.results
    except ValueError as error:
        assert "lineage" in str(error)
    else:
        raise AssertionError("Scenario result exposed a substituted graph output")
    finally:
        object.__setattr__(output_record, "result", original_output)
    assert partial.require_current() is partial
    original_nodes = partial.nodes
    object.__setattr__(partial, "nodes", ())
    try:
        partial.results
    except ValueError as error:
        assert "lineage" in str(error)
    else:
        raise AssertionError("Scenario result exposed a detached node sequence")
    finally:
        object.__setattr__(partial, "nodes", original_nodes)
    assert partial.require_current() is partial
    calls.clear()
    full = graph.run()
    assert calls == ["unrelated", "source", "receiver"]
    assert full.results["source"] is original
    for mapping in (receive.inputs, full.results, full.nodes[-1].resolved_inputs):
        try:
            mapping["extra"] = ScenarioValue(1)
        except TypeError:
            pass
        else:
            raise AssertionError("Scenario configuration/result mapping was mutable")
    try:
        receive.node_id = "relabelled"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Scenario node was mutable")

    calls.clear()
    for targets in ((), ("missing",), "receiver"):
        try:
            graph.run(targets=targets)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("Invalid targets were admitted")
    assert calls == []
    cause = ValueError("original selector failure")

    def broken_selector(value):
        assert value is original
        raise cause

    failing = OperationalScenario("failure", (
        ScenarioNode("source", source, {}, "source-evidence"),
        ScenarioNode("receiver", receiver,
                     {"value": ScenarioOutput("source", broken_selector)}, "receiver-evidence"),
    ))
    try:
        failing.run()
    except ScenarioExecutionError as error:
        assert error.cause is cause and error.__cause__ is cause
        assert error.stage == "input binding"
        assert len(error.completed) == 1
        assert error.completed[0].result is original
        assert error.node.node_id == "receiver"
    else:
        raise AssertionError("Selector failure did not preserve execution failure")
    try:
        OperationalScenario("cycle", (
            ScenarioNode("a", receiver, {"value": ScenarioOutput("b")}, "a-evidence"),
            ScenarioNode("b", receiver, {"value": ScenarioOutput("a")}, "b-evidence"),
        ))
    except ValueError:
        pass
    else:
        raise AssertionError("Cyclic dependency graph was admitted")
    return ValidationOutcome(True, {"executed_nodes_full": len(full.nodes),
                                    "executed_nodes_target": len(partial.nodes)}, (
        "Dependency composition is software behavior only; no physical validity is inferred",
    ))
