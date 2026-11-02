# Public native Cantera phase factories and bindings

This is an **implemented_unverified API increment**, with no new physics family.
Scientific/module imports, native calculations, examples, tests and benchmarks
were not executed for this change. The existing native equilibrium/reactor/
premixed-flame algorithms and settings are retained. The new guards and current
source bytes await the deferred cluster campaign.

`h2physics.adapters.cantera.CanteraGas` now provides public native phase
creation, current-state snapshots and explicit immutable-reference bindings.
The actual native Cantera `Solution` is retained and exposed; no EOS, kinetics,
mechanism or phase-cloning implementation is copied into the host.

## Source and construction

The existing `CanteraGas(phase_factory, basis)` constructor remains supported.
A callback must return genuinely fresh native ideal-gas storage matching its
declared `MechanismBasis`. Its source SHA is caller-declared:
`source_bytes_verified` remains false. The adapter does not infer source-byte
attestation merely from matching species or a mechanism name.

`CanteraGas.from_yaml(raw_bytes_or_utf8_text, basis, phase_name=...)` is the
source-verifying native constructor path. It compares the supplied top-level
UTF-8 byte SHA with `basis.source_sha256` before importing the optional native
engine, then owns a factory that calls actual `cantera.Solution(yaml=..., name=...)`
fresh. `owner.mechanism_source` retains a `NativeMechanismSource` with the
original bytes/name/hash. No file copy or mandatory input serialization protocol
is introduced. Existing in-memory bytes avoid the known Windows Unicode
mechanism-path issue.

`source_bytes_verified=True` attests only the exact supplied top-level bytes,
not auxiliary files referenced by that YAML, scientific applicability or rights
clearance. Auxiliary-source provenance remains caller evidence. The loaded
native species/thermo/reaction/multiplier definitions are bound separately at
first successful creation and must remain consistent across subsequent calls.

## Handle, snapshot and state seal

`create_phase(initial: ReactiveState) -> NativePhaseHandle` returns a Python
**handle**, not the bare native phase. Keep that handle for public coupling:

```python
handle = owner.create_phase(initial)
native = handle.native_phase          # original native factory result
point = owner.snapshot_phase(handle) # validated current native ReactiveSnapshot
reference = owner.bind_phase(handle, freeze_state=True)
reference.require_current()
```

This snippet is illustrative and was not executed. The handle retains the
original basis, requested state, native canonical creation snapshot, definition
fingerprint, source SHA and verification role. Inputs use K, Pa absolute and
explicit mole fractions. Cantera's TPX setter supplies its canonical composition;
both requested and resulting states remain inspectable. No host normalization,
phase imposition or energy-zero reset is added.

`snapshot_phase` checks current ownership, source/domain identity, full native
ideal-gas role, declared T/P domain, intersection of native species fit bounds,
composition and finite mass-SI properties. Density uses native `density_mass`,
enthalpy/internal energy use the explicit mass properties, and element fractions
are kg/kg. Changing the native display basis to molar does not change these SI
output meanings.

The actual native `FlameBase.density_mass` array likewise supplies kg/m3 at
every grid point. Its public Cantera3.2 API and installed registration were
inspected; no new vector property is assumed. Free-flame summaries and the
material-front consumer use this explicit array, including saved native fields.
Changing a solved phase's display basis does not rescale those physical ledgers.
Native FreeFlame initialization itself uses the basis-sensitive `gas.density`
alias for its mass-flow guess, so `free_flame` requires mass display basis at
entry. A molar-display factory result is rejected before constructing FreeFlame,
with the original phase/basis retained. No automatic basis reset is performed.
Generic phase creation and SI snapshots support either display basis.

Native state evolution remains permitted. `handle.require_current()` checks
live ownership and mechanism/source definitions, and does not certify a current
working-state snapshot. `bind_phase(..., freeze_state=False)` makes the same
definition-only reference. Its `snapshot` is the validated **creation** state,
labelled by `snapshot_role="validated-creation-state"`. Call `snapshot_phase`
to admit an evolved current point. This distinction supports native solver
working objects without an implicit global state lock.

`bind_phase(..., freeze_state=True)` instead records a validated current snapshot
with `snapshot_role="frozen-current-state"`. `binding.require_current()` rejects
later physical state changes as well as changed source/definitions. It does
not prevent native mutation; it prevents using an altered phase as the same
immutable reference. A new binding may be made at a newly admitted state.

Source/factory/domain identity checks are distinct from mutable state. Replaced
factory callables, method/bound-owner changes, modified basis/source metadata,
different loaded definitions and changed native reaction multipliers fail.
Native transport/Soret choices remain explicit solver settings; the existing
free-flame result/consumer guards retain that responsibility.

## Lifecycle and compatibility

Python handles and bindings explicitly support weak references. Owner and
cross-owner registries hold them weakly, so successful phase creation does not
accumulate a strong-reference history of all native phases. The registries
reject reuse of a live handle's identical native Python object **before** its
TPX is reassigned. Returned bindings keep their relevant handles alive.

This design does not assume native `Solution` supports Python weak references,
and does not use native private `_references` state. It does not certify that an
arbitrary callback avoids distinct Python wrappers sharing hidden C++ storage.
Such callbacks still owe the fresh-native-storage contract. The YAML constructor
path creates fresh native solutions directly. No destructive alias probe or
state-restoration workaround is used.

Retaining only a bare `handle.native_phase` after dropping its handle loses the
public lease; it cannot be implicitly readopted as an owner-issued handle.
`_phase(initial)` remains a compatibility method returning the bare native
`Solution`. The owner retains only the latest legacy handle, including available
failure context. Older externally retained bare aliases remain the legacy
caller's responsibility. Normal repeated fresh legacy calls and their mutable
native state remain supported. There is no default frozen-state seal on those
solver inputs.

`FreeFlameResult` retains its original native input handle and can be consumed
only with the one-use token issued by `CanteraGas.free_flame`. Its currentness
check covers the editable native profile, reported summary, and retained phase
lease. `ReactorTrace` likewise requires native one-use issuance and checks its
captured endpoint before `temperature_rise_event` uses its arrays and snapshots.
The native `FreeFlame` still owns its original `gas` object and physical solve.
`last_legacy_phase_handle` exposes the bounded latest native context for
older equilibrium/reactor/flame paths; it is not an all-history store.

## Failures and current consumer

`CanteraPhaseFactoryError` is a `ValueError` retaining the original cause,
owner, stage, requested state, native phase, handle/binding and available live
prefix. Invalid source bytes can fail before an owner/native object exists.
Native solver exceptions retain their existing behavior; the available latest
legacy phase remains inspectable. Failures never restore or replace a native
state to hide what happened. A copied handle/binding cannot become an original
issued object merely by preserving its cached summary fields. These are
research validity guards, not a security boundary against deliberate private
object tampering.

The [material-front consumer](FLASH_FRONT.md) uses these public hooks, retains
the source handle and frozen unburned/burned bindings, and uses public snapshots
for finite mass/U/PV bookkeeping. It contains no `CanteraGas._phase` call.
Warm ideal-gas material-frame, source/phase/clock and no-injury boundaries remain.
Four deferred front cases remain defined; the existing binding case now also
covers factory/source/definition/domain/state/lifecycle guards. None was run.
It also defines mass/molar snapshot/vector/finite-ledger invariance and rejection
of unsupported molar-display native flame initialization.

Primary native API/source references:
[Solution constructor](https://cantera.org/3.2/python/importing.html#cantera.Solution),
[thermodynamic state API](https://cantera.org/3.2/python/thermo.html),
[explicit mass density](https://cantera.org/3.2/python/thermo.html#cantera.ThermoPhase.density_mass),
[native flame mass-density array](https://cantera.org/3.2/python/onedim.html#cantera.FlameBase.density_mass),
[original Cantera source](https://github.com/Cantera/cantera/tree/v3.2.0/interfaces/cython/cantera).
Existing Cantera licensing/provenance applies; no native source or mechanism
is bundled by this API change.
