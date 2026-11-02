# Native Python scenario composition

`h2physics.scenarios.OperationalScenario` composes existing Python model calls
as a named acyclic dependency graph. It schedules operations and carries their
original Python objects; each selected model remains responsible for its own
units, evidence, clock, phase, conservation and freshness rules. Creating a
graph performs no model calculation. Execution is sequential and deterministic
within one process; parallel scientific campaigns belong to the external
validation runner.

## Typed bindings

Each `ScenarioNode` has a unique node ID, callable operation, evidence ID and
keyword input bindings. Use `ScenarioValue(value)` for an explicit caller-owned
input. Use `ScenarioOutput(node_id, select=None)` to pass an earlier node's
original return value, optionally through an explicit selector. Unknown nodes,
duplicate IDs and dependency cycles fail during graph construction. Independent
ready nodes follow their declaration order.

```python
from h2physics.scenarios import (
    OperationalScenario,
    ScenarioNode,
    ScenarioOutput,
    ScenarioValue,
)

scenario = OperationalScenario("facility-example", (
    ScenarioNode("source", make_source,
                 {"inputs": ScenarioValue(source_inputs)}, "source-contract"),
    ScenarioNode("dispersion", run_dispersion,
                 {"source": ScenarioOutput("source")}, "dispersion-contract"),
))
result = scenario.run(targets=("dispersion",))
result.require_current()
```

Selecting target nodes executes only those nodes and their ancestors; each call
starts fresh and does not reuse cached results. A selector is caller code and
can itself fail before the receiving operation is invoked.

## Results, failures and integrity

`ScenarioResult` retains graph-issued `ScenarioNodeResult` records and original
operation outputs. Its one-use issuer rejects direct construction and cloned
receipts. `require_current()` checks that node records, bindings, resolved
inputs and output identities remain attached to the graph result; domain object
freshness still belongs to each model's own guard.

`ScenarioExecutionError` preserves the original exception and identifies the
failing node and stage (`input binding`, `operation`, or `result recording`).
It also retains the successfully completed prefix, resolved inputs and any
operation return that existed before result-recording failed. No retry or
fallback model is substituted.

The deferred Hangang contract
`operational-scenario-dependency-composition` covers lazy construction,
deterministic order, target/ancestor selection, original object identity,
failure-prefix retention, cycle/unknown-target rejection, immutable maps and
forged/stale result-receipt rejection. It is software-contract evidence only,
not physical validation. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for composition boundaries.
