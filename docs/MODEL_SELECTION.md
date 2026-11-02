# Explicit model level and provider selection

`h2physics.model_selection` is a caller-owned registry for deep Python
composition. It contains no physical equation and imports no optional engine.
Every executable factory is registered under an exact triple:

`(family_id, level_id, provider_id)`

A `ModelRequest` repeats that exact identity and explicitly admits status,
required capabilities and evidence identities. Missing providers, capabilities,
evidence or statuses raise an error. Selection never retries another level or
provider. This preserves the project rule that a failed preferred HyRAM gas or
SLABx-LH2 liquid-origin path cannot silently become another dispersion model.

`ProviderBinding.bind(...)` captures the real factory/callable identity and its
revision. `ModelRegistry.register(...)` rejects duplicate exact keys and unknown
catalog families. `registry.select(request)` returns a `ModelSelection` without
constructing the model. `selection.build(*args, **kwargs)` calls only that exact
factory and returns a `BuiltModel` retaining the selection evidence.

The status gate admits `implemented`, `native_adapter_verified` and, only when
the caller explicitly lists it, `implemented_unverified`. Planned rows cannot
bind factories. These labels still describe implementation evidence rather than
fitness for a particular plant. Capability/evidence tags are exact declared
identities; they do not prove physics, data quality or licensing by themselves.

Registries are intentionally local Python objects. The project supplies no
global singleton, JSON service, plugin discovery, installation or automatic
factory import. Applications may maintain separate registries for production,
research comparisons and unverified development. Optional providers should be
imported and bound by the application only after its dependency and rights gates
are satisfied.

`DispersionScenario` is the direct lazy-use option when an application does
not need a registry. It stores the declared release family and a named mapping
of Python provider inputs; `scenario.provider_id` exposes the exact preferred
engine and `scenario.run()` dispatches only to its dedicated adapter route.
`run()` returns a `DispersionExecution` receipt containing the family/provider,
source evidence IDs, reported acceptance and raw adapter result. If dispatch or
the provider fails, `DispersionExecutionError` retains that identity and chains
the original exception, including any failed result it exposes.
Any `collections.abc.Mapping` is copied into a read-only proxy at construction,
so later changes to the caller's mapping cannot change the scenario's keyword
set; the declared inputs also participate in scenario equality.
Referenced physical objects and callbacks remain caller-owned and may themselves
be mutable. Build a fresh scenario when changing its declared inputs.

Five deferred cases cover exact selection, no fallback, capability/status/
evidence gates, duplicate registration and callable staleness; a sixth covers
preferred-dispersion routing, and a seventh rejects forged native SLAB run receipts.
They have not been executed.

The deferred `selection-preferred-dispersion` case composes
`dispersion.preferred_dispersion_provider` with exact registry `provider_id`
bindings for high-pressure gas (`hyram`) and LH2-origin releases (`slabx-lh2`).
It checks that a gas provider requested for the LH2-origin level fails with no
cross-origin fallback, and that `run_preferred_gas_dispersion` forwards a
high-pressure call to the existing HyRAM adapter. LH2-origin input is rejected
before entering that gas adapter; the caller must provide the explicit liquid
source/pool boundary to the SLABx-LH2 interface. Call sentinels verify callable
input forwarding. `run_preferred_lh2_dispersion` also binds the explicit,
steady pure-vapor `IntervalMassSource` to a footprint, passes through the
width context/runner/applicability gate and retains the returned run object, whose receipt can only be issued by the actual adapter;
it
refuses high-pressure-gas origin. Variable vapor bins remain unsupported by the
native steady source boundary. The deferred case registers only
`implemented_unverified` stubs and does not run or qualify either native engine
or plume prediction.
