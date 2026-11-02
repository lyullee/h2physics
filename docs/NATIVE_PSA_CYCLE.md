# Native warm multibed PSA cycles

`h2physics.adapters.psa_cycle.PsaDynaCycle` executes the actual separately
installed PSA-Dyna runner, schedules, valve network, finite-volume bed states
and BDF integration. It adds a native scheduled multibed level beyond the
existing closed warm `PsaDynaBed` relaxation. The host does not implement bed
equations, an isotherm, valves, a cycle integrator or another CSS algorithm.

The checked MIT source is
`a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6`. Optional imports happen explicitly
through `PsaCycleNative.from_installed`, after selecting that installation.

## Native capability and the I/O bridge

At this revision the only integration entry point is
`runner.run_case(case_path, output, resume=..., cycle_budget=..., step_budget=...)`.
Its one `solve_ivp` call is internal. No standalone object/state slot-integrator
helper was found in public or private package APIs. The original integrating
`Network` and SciPy `OdeResult` are not returned.

The public host API accepts a Python case mapping, ordinary parameter/evidence
objects and an explicit managed temporary workspace. Internally it serializes
the mapping in a temporary ignored directory, calls the actual native runner
with its existing one-slot/cycle budgets and resume control, verifies native
input/code/checkpoint hashes and reads each completed slot state. Native
schedule ownership and integration remain unchanged. Users do not need to
produce JSON, use HTTP or adopt a serialized service protocol. This first
bridge accepts the native case's serializable numeric/list/mapping inputs;
arbitrary Python history callbacks require the receiving API below.

The actual native callable, raw returned records, native schedule and
hash-checked checkpoint states are retained. A separate actual native
`audit_network` reuses `PsaDynaBed` for admission/snapshots and inventory audits.
It is **not the original integrating Network**. The result explicitly reports
`original_integrator_objects_available=False`; no original `OdeResult` is
advertised. This distinction cannot be removed by reconstructing another
object with matching parameters.

All managed temporary native files are removed after their states/metadata are
read. Native automatic source-archive bytes are not read into the result or
bundled. Native source is immutable; no module/function monkeypatch is used.
See receiving request018 for the required original-object/accepted-state hook.

## Supported physical level and inputs

This first level requires at least two finite beds, loading-LDF absolute
uptake, native ideal-gas constant-Cp thermodynamics, dynamic lumped walls and
native pressure-driven valve boundaries. A fixed inlet plus a real native
outlet valve is also admitted; controller and source-specific pressure-screen
modes are not silently substituted. Finite product receivers, partial-pressure
pellet states and PR gas models remain outside the admitted level here.

The native case mapping names all geometry, species/molar masses/Cp,
isotherm/binding/LDF coefficients, thermal coefficients, initial conditions,
feed/product/tail pressures, flows, valves, purge sharing and timing. Native
input pressure keys ending in `_bar` mean **bar absolute**; snapshots expose
Pa absolute. Molar transfer is mol/s, inventory mol, Cp J/(mol K), adsorbed
loading mol/kg dry solid and energy J. `AdsorptionBasis.species` must exactly
match native order; `loading_definition` must be `absolute`.
The actual native `reporting_species` must be `H2` because this interface
exposes H₂-specific metrics and native CSS output/recovery tests must check
that same species. Other reporting species are rejected at admission; a
generic reporting contract remains receiving work under request018.

`PsaCycleEvidence` requires source identity, parameter origin, native energy
reference and gas-phase scope. These identities do not validate coefficients.
The native ideal-gas model does not calculate condensation or H₂ spin
equilibration. A caller must justify a warm gas-phase application and the
material domain. The declared `AdsorptionDomain` lies strictly inside the
native100–1000K guard. Cryogenic adsorption is not authorized by lowering a
label or changing a phase name.

Native gas U uses Cv*T with zero at0K; stream enthalpy uses Cp*T from0K.
Solid and wall sensible energy uses298.15K and adsorbed binding energy is
negative storage. This is not a CoolProp/Cantera formation-energy reference.
Native vacuum-work diagnostics are a separate utility estimate; they are
not added again as heat into the bed. Direct connection to another provider
needs an evidenced energy-reference mapping and phase/material contract.

The runner uses explicit augmented component/enthalpy/ambient ledgers, strict
zero accepted negative tolerance and a finite integer cycle limit. Raw
negative gas or loading cannot pass `PsaDynaBed` snapshot admission. Accepted
BDF-node T/wall-T/P extrema are checked through native trajectory diagnostics,
in addition to complete retained slot snapshots. Native probe floors are not
host clipping or experimental-data corrections.

## Python use

The repository replay contains an original small verification case. The
following executable example loads only those authored Python parameters;
replace them with a source-qualified native case mapping for research use.

```python
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path("artifacts/native_packages").resolve()))
from h2physics.adapters.psa_cycle import (
    PsaCycleEvidence, PsaCycleNative, PsaDynaCycle,
)
from h2physics.adsorption import AdsorptionBasis, AdsorptionDomain
from h2physics.core import Origin

case = runpy.run_path("scripts/check_psa_cycle.py")["authored_case"]()
native = PsaCycleNative.from_installed(
    source_id="PSA-Dyna:a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6",
)
basis = AdsorptionBasis(
    "authored-warm-H2-N2", ("H2", "N2"), "mol/kg-dry-solid:absolute",
    native.source_id, "authored-case-not-material-calibration",
    ("https://patents.google.com/patent/US2944627A/en",),
    loading_definition="absolute",
)
model = PsaDynaCycle(
    native, case, basis=basis, domain=AdsorptionDomain(290., 350., 5e5, 5e4),
    evidence=PsaCycleEvidence(
        "authored-native-cycle",
        "native-CvT0/CpT0/solid-wall298.15K/negative-binding;H2-spin-unresolved",
        "warm-ideal-gas-no-condensation", Origin.SYNTHETIC,
    ),
    temporary_workspace=Path("artifacts"),
)
result = model.run(start_time_s=100., clock_id="operation-clock")
last = result.points[-1]
print(last.beds[0].pressure_pa, last.component_residual_mol,
      last.energy_residual_j)
print(result.final_cycle_totals.hydrogen_product_purity)
```

`case_parameters()` returns an independent copy. Initial states are admitted
through the existing bed adapter; arbitrary seeded process/restart arrays need
a separate admission contract. Native timing inputs must be consistent and
unambiguous. The native schedule distinguishes physical bed count from global
slot count. In the authored Skarstrom case two beds share four global slots;
each takes feed pressurization, adsorption/product, blowdown and countercurrent
purge in the native phase relation. Timings are authored, not a reproduction
of a particular valve log or apparatus.

## Clocks, inventories and exports

Every point contains the original native serialized flat state, separate bed
snapshots, global component inventory, stored U, cumulative external feed,
net product and tail component amounts, their enthalpies, signed ambient heat,
vacuum-work diagnostic and independent conservation defects. Original native
slot/cycle checkpoint counters and native elapsed time remain distinct from
the caller's absolute operation clock. A cycle-finalization runner call does
not introduce an extra physical time step or alter the state. No recorder
alignment or within-slot source interpolation is inferred.

For each component and the whole stored system the host checks

```text
N - N_initial = feed_integral - net_product_integral - tail_integral
U - U_initial = feed_enthalpy - product_enthalpy - tail_enthalpy + ambient_heat
```

Native internal purge/equalization cancels in the whole-system boundary.
Product means external export after native diversion to purge; using gross
adsorption flow would overcount product. Default independent budgets are
1e-8mol per component and1e-4J. Those are software-verification budgets,
not material or measured process accuracy.

`hydrogen_product_purity` is the actual H₂ product integral divided by all
product components. `hydrogen_product_to_feed_ratio` uses H₂ export/feed
integrals over the stated window, without clipping. Initial finite inventories
can contribute to startup exports, so this is not feed-origin tracer recovery.
`css_hydrogen_recovery` is populated only for the native-confirmed final CSS
cycle. Whole-startup-window recovery remains unset even when its final cycle
eventually becomes CSS. Zero feed/product leaves the relevant metric `None`.

CSS means the native declared full-state/pressure/temperature/output-change
and conservation tests, minimum cycle count and consecutive-cycle streak
passed. It does not establish a valid material fit, an optimum process or
experimental accuracy. Native `training_eligible=False` and the closed
dataset-release gate are preserved. The native `mean_stream_bridge` also
requires independent resolution/source/release qualifications; this adapter
does not invoke or bypass it. Numerical CSS alone does not create a qualified
downstream source or mean stream.

Native call results/checkpoint metadata are retained as independent copies;
their nested native dictionaries remain inspectable and mutable. Physical
state/ledger arrays and bed snapshots are read-only copies. External mutation
of a native audit object invalidates its parameter correspondence. Failed
post-run admission/conservation retains actual checkpoint state, metadata,
audited prefix and chained exception at `PsaCycleError`; a native runner
failure also retains its native failure record where available. The pinned
runner cannot expose internal failed-slot solver states that it never saved.

## Executed checks and receiving work

```powershell
.venv\Scripts\python -m pytest tests/test_psa_cycle.py -q
.venv\Scripts\python -X utf8 scripts/check_psa_cycle.py
```

The replay records two physical startup cycles, native timestep/tolerance
refinement, exact closed-valve equilibrium, a separately executed native CSS
campaign, independent component/U ledgers and purity/recovery from final-cycle
integrals. Source/native/test/script begin/end hashes and actual runtimes are
in [research/native_psa_cycle.md](../research/native_psa_cycle.md).

The synthetic CSS H₂ product can be poorer than its0.8H₂ feed; that result is
retained. Initial transient enrichment does not qualify a purifier. No
manufactured purity target, fitted material coefficients, experimental
comparison or source-grade process performance is claimed.

Receiving request018 should provide an object-based native integration API
accepting/returning the original `Network`, state, `OdeResult` and accepted
step/slot callbacks; an absolute-clock/source boundary; explicit cumulative
stream/ambient/work ledgers; strict species/phase/reference admission; and
CSS/mean-stream qualification evidence. That is required for deep Python
co-simulation without the temporary bridge. No receiving source is edited
or patched here.

Primary context: [Skarstrom original cyclic adsorption patent](https://patents.google.com/patent/US2944627A/en)
and [actual native PSA-Dyna](https://github.com/lyullee/psa-dyna/tree/a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6).
Original composition and numerical cases include no copied native solver,
published parameter table, proprietary example or external observations.
# Run receipt integrity

`PsaCycleRun` is issued only after `PsaDynaCycle.run()` completes its native
scheduled execution and endpoint audit. A caller-created or dataclass-replaced run
cannot claim native execution. Before cycle-operation accounting reads checkpoints,
the receipt rechecks its retained point/totals, native metadata, case and schedule,
owner identities, and pinned runner code hash. The existing deferred
`adsorption-native-cycle-endpoint-inventory` contract covers direct construction,
clone rejection and post-issuance checkpoint mutation. It remains unexecuted.
