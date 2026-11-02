# Facility accident source-to-dispersion chain

`FacilityAccidentChain` composes an existing finite equipment operation, its
admitted finite hydrogen source, and a selected native dispersion engine. The
chain records the declared release family and a shared coupling evidence ID.
For gaseous hydrogen, the caller also supplies the stationary HyRAM projection
used to check each finite source bin. Liquid-hydrogen-origin cases require the
existing admitted vapor-source boundary and do not accept a gas projection.

```python
chain = assemble_facility_accident_chain(
    scenario_id="case-identifier",
    finite_operation=run_equipment,
    source_binding=bind_source,
    dispersion_request=select_dispersion,
    release_family="liquid_hydrogen_origin",
    evidence_id="documented-source-to-field-coupling",
    mass_absolute_tolerance_kg=mass_budget_kg,
    energy_absolute_tolerance_j=energy_budget_j,
)
result = chain.run()
result.require_current()
```

Preparation captures the scenario graph, release family, coupling identity,
node operations and their declared bindings. `require_current()` checks this
captured configuration; `run()` applies the check before and after execution,
then rechecks the graph-issued result receipt. This prevents a prepared chain
from being reused after its declared coupling identity or graph wiring has
changed. Callback-owned internal state is still the callback owner's
responsibility and should be guarded by its own currentness contract.

The chain enforces identity, source mass and enthalpy budgets and the exact
accepted dispersion receipt. It does not select accident frequencies, infer
release conditions, calculate receptor impacts, choose consequence thresholds,
or establish hazard acceptability. Physical fidelity and applicability must be
validated against suitable experimental or operational evidence. The deferred
Hangang contract case checks graph identity and orchestration behavior only;
it is not a physical validation result.
