# Public Cantera factory and material-front API record

2026-10-28. Status: **implemented_unverified API change**, no new physics family.
No native/project module import, scientific calculation, native weak-reference
probe, example/case discovery/invocation, installation, pytest, replay, benchmark
or job was performed. Source/API/license inspection, public primary-document
reading, AST/Ruff and static file-byte checks are the available evidence.

Owned changes: existing `cantera.py`, `flash_front.py`, front documentation/
development record/example/cases, plus new `docs/CANTERA_FACTORY.md` and this
record. No other consumer, native package, global catalog/docs, dependency
environment or external repository was modified.

## Public contract implemented

- Existing `CanteraGas(factory, basis)` stays callable. Callback source bytes
  are declared/unverified; matching runtime definitions are not inferred source
  attestation.
- `CanteraGas.from_yaml(source, basis, phase_name=...)` compares exact original
  top-level UTF-8 bytes to the declared source SHA and uses the actual native
  constructor. Original bytes/name/hash remain inspectable. Referenced auxiliary
  resources and scientific/rights qualification are separate evidence.
- `create_phase(initial)` returns a **NativePhaseHandle**, whose `.native_phase`
  is the original native `Solution`, not a copied/reconstructed phase. It retains
  original basis, requested and native canonical creation state, source role and
  native thermo/kinetic definition fingerprint.
- `snapshot_phase(handle)` admits a current native state with explicit SI mass
  density/enthalpy/internal energy, full ideal-gas role, declared state domain and
  native species-fit intersection. The explicit `density_mass` property removes
  dependence on the native display basis; default mass-basis numerical meaning
  is unchanged. No host EOS, phase imposition or reference reset is introduced.
- Actual `FlameBase.density_mass` vectors supply summaries, front fingerprints,
  mass-flux admission and saved native fields. Native FreeFlame initial guesses
  use the basis-sensitive `gas.density` alias; the shared entry therefore rejects
  molar-display input before native construction and retains that phase/basis.
  Generic create/snapshot APIs accept either display basis without resetting it.
- `bind_phase(handle, freeze_state=True)` records a validated current snapshot
  and exact state seal. Definition-only `freeze_state=False` bindings deliberately
  permit native working-state evolution and label their retained snapshot as
  the validated creation state. Handle/definition guards do not themselves
  certify an evolved physical snapshot; use the public snapshot hook for that.
- Public require methods reject stale factory/callable/bound owner, source/basis/
  domain declarations, loaded definitions, runtime reaction multipliers, copied
  handles/bindings and changed explicitly frozen states. The existing native
  fingerprint implementation is reused through a local internal import; the
  public consumer does not duplicate mechanism/domain/ownership checks.

Native equilibrium, ReactorNet and FreeFlame calls/settings remain their original
implementations. Legacy `_phase(initial)` returns the same bare native type as
before and has no default frozen-state seal. Invalid fresh-storage/fit/source
premises can now fail earlier; this is additional admission, not a changed
physical solver. Current bytes have not inherited old regression passes.

`CanteraPhaseFactoryError`, a ValueError subclass, retains original cause,
owner/stage/request, actual native phase where available, handle/binding and
currently live prefix. Bad source bytes can fail before an owner/native object
exists. Existing native solver exceptions retain their original behavior; a
bounded latest legacy phase context remains publicly inspectable. No failure
restores a state, creates a fallback or invents a completed native result.

## Lifetime design and limits

Static inspection of actual installed Cantera3.2.0 found Solution's Python
`__slots__=()` and no explicit Python `__weakref__` slot in the inspected extension
declaration. No runtime support probe was made and no native weakref behavior is
assumed. The implementation instead makes Python handle/binding classes weakref
capable and tracks them in weak-value owner/cross-owner registries. Those
registries do not strongly retain all phases ever created.

Live identical native Python objects cannot be reused through another public
creation before TPX reassignment, including across owners. Holders must keep the
handle/binding, not only its bare native phase. The compatibility path retains
only the latest legacy handle. Older untracked bare aliases and arbitrary
callback wrappers sharing hidden C++ storage remain callback responsibilities;
there is no claimed universal native-storage alias detector. The verified YAML
factory directly makes fresh native solutions. No destructive alias probe or
private native `_references` hook is used.

Bindings/returned results keep only their relevant handles alive. Failure
objects intentionally retain the available live prefix while the failure itself
is retained. These guards preserve research-input correspondence and are not
a security boundary against deliberate private-field tampering.

## Material-front integration

`FreeFlameResult` adds an optional `native_phase_handle` field after its prior
constructor arguments. The actual native free-flame source phase remains
retained and editable. The front requires that original handle, checks the
native flame gas/inlet association, and binds source definitions without a state
seal because the native flame legitimately updates its working phase.

Unburned/burned reference phases use public create/bind hooks with frozen state
bindings. Public snapshot density/internal energy feed the existing finite
mass/U/PV ledger; actual native phases remain available for species mass fractions
and deep Python coupling. No `CanteraGas._phase` call remains in `flash_front.py`.
HP failures retain the existing phase/HP prefix and available public legacy
handle in PremixedReferenceError.

Warm ideal-gas mechanism/material-frame scope, all previous source/energy/element/
mass-flux rejection, and the explicit absolute-clock projection guard remain.
There is no new kinetics, speed, lattice path, equilibrium or clock algorithm.
There is no cold-release-to-reactive-cloud bridge, laboratory flame prediction,
heat-injury model or physical family promotion.

## Deferred checks

Four `flash-front` metadata cases remain. The existing binding case is extended,
not split into additional case-count credit. Its future checks use real native
factory phases and define:

- source-byte match versus modified source rejection;
- native SI snapshot independent of display basis;
- solved native mass-density vector and finite mass/U/PV ledger invariant under
  mass/molar display changes, plus unsupported molar flame-setup rejection;
- permitted mutable state versus explicit frozen-state rejection;
- copied binding and singleton/cross-owner live native reuse rejection;
- repeated fresh bare `_phase` compatibility with one retained legacy handle;
- current native state-domain and reaction-definition/multiplier rejection;
- changed owner basis/factory rejection before another native phase is produced;
- Python-handle weak lifecycle without retaining temporary native phases.

These definitions are **unexecuted**. Their GC/native behavior and compatibility
must be checked in the later cluster profile. All previous native flame width/
grid, HP/mass/U/PV, disconnected-path and clock definitions are retained. The
binding case's deliberate compatibility calls to `_phase` do not reintroduce
private coupling in the production front module.

AST parsing and Ruff passed for the four changed Python inputs. AST counted
four front case definitions and zero private `_phase` calls in the front source.
All owned files are LF. This is static evidence only, with no scientific runtime
or passing-test claim.

## Native rights/API evidence

Existing Cantera3.2.0 BSD-3-Clause and installed mechanism provenance continue to
apply. No dependency was installed and no native source/mechanism/coefficient
table was copied into the host. The actual installed files inspected for the
lifetime/source association design had these SHA256 values:

| Installed source | SHA256 |
| --- | --- |
| cantera/solutionbase.pxd | `22ada176a65c09f7809179631b67c8eae561fbaf8924ca6ec21719d331098738` |
| cantera/composite.py | `001cb8d2e6f362e99f1c39db2f8181f0348d31f3536b4548178a1acfdaf82460` |
| cantera/onedim.py | `59b968938254ceb789edd943e5cee0541edb69ce9efab7e7c5e76859c75ff39b` |

The installed onedim source explicitly retains the original gas object and
registers real `density_mass` array access through its native scalar property.
Its FreeFlame initial-guess routine uses `gas.density`, establishing the input
display-basis guard. It was read, not executed or copied. Primary API references:
[Solution and YAML constructor](https://cantera.org/3.2/python/importing.html#cantera.Solution),
[native thermodynamics](https://cantera.org/3.2/python/thermo.html),
[explicit scalar mass density](https://cantera.org/3.2/python/thermo.html#cantera.ThermoPhase.density_mass),
[native flame mass-density vector](https://cantera.org/3.2/python/onedim.html#cantera.FlameBase.density_mass),
[official source](https://github.com/Cantera/cantera/tree/v3.2.0/interfaces/cython/cantera).

## Before/after inputs

The first two source rows change shared API bytes, so previous executed native
reports apply to their original hashes. The new factory/front guard definitions
await execution. Existing other-consumer source files were not edited.

| Python input | Before SHA256 | Final SHA256 |
| --- | --- | --- |
| src/h2physics/adapters/cantera.py | `19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184` | `106e2caffe719c11c2af4568930f4bb4791912e10ff086d3789c1a4adf1bde8c` |
| src/h2physics/adapters/flash_front.py | `435c9bfab050322b0945e98546db15b2777a29c8c9aa42ce24577a56bd949140` | `5e7d9753f6d49b43c6a5e48dc3b18b62b645b3adf6de0daebb71dbcfa7138af7` |
| examples/flash_front.py | `af26e6af423eb356a81717d6f3ee5c035ac9ed0e24c92b472e75581cb6a3be5c` | `25f1f9e38db9f16334af000f621bcbbb04d9dbcfd43a780a53cc3968f0ee2b24` |
| validation/cases/flash_front.py | `423cc0b20eb2b2aa59ac2de6401cee3aeda2c846cb884406ffcb7c7027abcb2b` | `ffafb4918cd2bf0f77e1318a211b3a287d3cc97a780f5cd7844be4497681f2bc` |

The final documentation/report hashes are sent separately after writing this
record, avoiding a self-referential report hash. No additional family or deferred
case count is claimed by the API cleanup.
