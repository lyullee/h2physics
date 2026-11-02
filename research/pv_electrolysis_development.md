# PV/electrolysis development record — not executed

2026-10-28. Model status: **implemented_unverified**. The user explicitly
prioritized parallel coding and deferred tests, validation replays and
benchmarks until a Nurion connection is available. No such local run was
started for this increment. Static syntax/lint checks are the only code
checks permitted here; they do not establish runtime or scientific acceptance.

Owned files:

- src/h2physics/adapters/pv_electrolysis.py
- docs/PV_ELECTROLYSIS.md
- research/pv_electrolysis_development.md
- research/pvlib_dependency.toml
- examples/pv_electrolysis.py
- validation/cases/pv_electrolysis.py

No shared physical source, requirements, catalog or general documentation was
edited by this lane. Parent-owned cluster_validation supplies deferred job
contracts. The preceding read-only survey remains under
artifacts/energy_coupling_feasibility/READ_ONLY_PLAN.md.

## Implemented composition and boundaries

The source defines an actual optional pvlib PVSystem owner, direct-DC
load-line root and retained native I–V/MPP parameters/results. The shared
HydrogenStack computes voltage, electrical power, Faraday production and
isothermal duty. Shared StoichiometricReaction.convert applies the resulting
finite held-current extent to water/H2/O2. Existing HydrideGasThermodynamics
supplies actual native H2 receiver flashes and retains its original native
objects. No PV/electrolysis/EOS/thermal ODE or kinetic correlation is copied or
duplicated.

The first finite reference holds source conditions and current within each
explicit clock interval. It uses an isothermal fixed-volume seeded H2
receiver and finite water/O2 isothermal/isobaric enthalpy stocks. It does not
predict continuous pressure/temperature feedback, water/O2 vessel dynamics,
thermal utility availability, startup hardware or MPPT. It has no AC inverter
or absent rectifier hidden in an efficiency constant.

The actual coupling root calls native PV current at the shared stack voltage.
Unavailable/bracketless roots, current/voltage/phase/pressure scope, finite
water depletion and mismatched caloric references fail explicitly with the
completed prefix and attempted native state/results preserved. The 17-point
branch admission is a sampled check, not a mathematical uniqueness proof for
arbitrary user polarization functions.

Finite receiver energy uses its native U. Entering H2 carries actual native h
at the declared production pressure/temperature. That h must match the
caloric provider's H2 molar enthalpy, and shared ReactionEnergy deltaH/reference/
water phase must match the same provider. The composite caloric coordinate
is nonreceiver H plus receiver U: H2 material enthalpy cancels once, and
reaction deltaH is not added again as heat. Required signed stack/receiver
heat is returned without an invented utility.

A separate ProductPressureBoundary states whether the product pressure/activity
is in the actual reaction Gibbs input. Otherwise the model records a
declared pressurized source and unresolved additional pressure work, with
required_external_pressure_work_j=None. Both receiver endpoints must remain
below that source pressure during delivery. This is not free compression,
a solved valve or a qualified pressure-dependent electrochemical model.
The authored example deliberately retains the unresolved-work status.

For incomplete Faradaic heat-fate information the finite campaign rejects
eta_F<1 rather than turning all missing current into heat. No silent partial
depletion interval, refill or temperature/EOS substitution is introduced.

## Optional dependency action actually performed

The official pvlib 0.16.1 wheel was downloaded once and its actual 19368848 bytes
verified against the publisher SHA256:
4e61b5228a13f782413d7cf8cc48eb6e62e7bf55d155958fa9fd72420b63603d.
It was installed with --no-deps into artifacts/native_pvlib_packages.
The main environment was not upgraded or modified.

Original native LICENSE SHA256:
a02e12ddaada3cf0d5dbdd8affdd577c2eec640758a95842a304f7513b8c0be4.
The BSD-3-Clause notice remains in the separate target. Original 67 Python
files yield the aggregate
ca5be5d34c8afac877fe5755ce57543b360b16da80006998a1614a65704ae5a6.
The source receipt records all native file hashes, official artifact URL,
release revision and dependencies. No native runtime model was imported or
executed to claim a result.

Only short static native API/source inspection was performed, confirming that
PVSystem.single-diode/current calls are native wrappers and its scaling
requires a DataFrame. The adapter creates a native pandas-compatible row for
that public scaling API rather than reproducing native scaling logic.
Native implementation/parameter-database files stay outside host source.
Manufacturer parameter selection/data rights are not supplied by this example.

## Deferred Nurion cases, all unexecuted

The common Python ValidationCase/ValidationOutcome definitions cover:

1. Actual native load-line, independent held-charge/Faraday stoichiometry and
   finite receiver/caloric/DC energy ledgers.
2. Dark and isolated no-current/no-production modes.
3. A supplied current envelope with no root, retaining native I–V/probes.
4. Finite water depletion rejection.
5. Source pressure below receiver pressure, without free delivery.
6. Out-of-domain receiver state and its retained native snapshot.
7. Missing Faradaic-loss heat fate.
8. Held-stage subdivision/refinement of charge and receiver heat.
9. Unrelated reaction/material enthalpy reference rejection.

Module import and cases() do not instantiate native models or solve a case.
Entry points are keyword-only validate_...(*,work_directory,**parameters)
and return common ValidationOutcome objects only when a future worker invokes
them. Their accepted=True branches are future acceptance logic, not present
evidence. None is labelled passed here.

Before execution, stage the repository, its examples/validation modules and
compatible optional pvlib/CoolProp dependencies on the worker. Native PV
source/version/bindings, raw result shapes and dark behavior remain actual
runtime gates. Do not adjust a failing threshold after viewing those results;
retain the failed native attempt and revise scope or implementation explicitly.
No new measured performance/plant-validation claim can follow from these
synthetic cases alone.

## Data and scientific evidence limit

The PV/PEM dispatch collection contains reconstructed/simulated power/H2 figure
tables on relative hours, without admitted weather/module/inverter/
polarization/thermal input histories. The local Dryad PEM/grid receipt has no
acquired attachments. Neither is used as an independent validation dataset.

The example's diode, ohmic and caloric functions are original authored inputs.
Its water/oxygen caloric functions are an explicit synthetic common-reference
construction using actual native H2 h; they are not a liquid-water/oxygen EOS.
No data fitting, device selection, irradiation inference, HHV/LHV calibration,
manufacturer rating or facility qualification is claimed.

Primary API context:
https://pypi.org/project/pvlib/0.16.1/
https://github.com/pvlib/pvlib-python/tree/ba161f9962f7a95fb8bd052fe646ba8234e99d95
https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.calcparams_desoto.html
https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.singlediode.html
https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.i_from_v.html
https://www.nrel.gov/docs/fy23osti/83155.pdf

Final static-check/source fingerprints are appended after syntax/lint
inspection. This record's own hash is reported separately to avoid recursion.

## Static handoff fingerprints

AST parsing of the three Python files and Ruff static lint completed. TOML syntax and LF/whitespace were inspected. No adapter/example/case module was imported to run physics, and no local test/replay/benchmark was started. These checks are not execution validation.

| File | SHA256 |
|---|---|
| src/h2physics/adapters/pv_electrolysis.py | 04f3c8035f3b63b6c8a2121b4a1a432daeafb8285c9badf463f068eed701988a |
| examples/pv_electrolysis.py | a36a93775a3707912cad37b6eb5c8884bc0289dfb69faad20587596732505c8f |
| validation/cases/pv_electrolysis.py | 4fc71b5a116811953fa808de6aff33ff700f85fcfe9f8045332227041afaab44 |
| docs/PV_ELECTROLYSIS.md | e342004c4d819a84e480a68b145c83cc500aeb58e2bc7fdbec9a9b991c764c05 |
| research/pvlib_dependency.toml | 6bf331bb48e59bd8ffa1a090631c909762e712bd534f52810c62e78851096ed1 |

## 2026-10-28 original-result admission increment

The successful trace now retains its actual producer and a weakly registered
producer-issued admission. Read-only verification checks exact result identity,
stored native tables/arrays, source definition and producer bindings without
calling any physical solver or user callback. Reconstructed dataclass copies
are rejected. The economics source adapter consumes this admission on both
sides of its structural snapshot. One deferred case was added; no case, model,
native import or test was executed locally.

## 2026-10-29 bounded sampled-input profile increment

`PVBoundaryProfile` converts caller-owned irradiance and PV-cell temperature
knots into the existing held `PVStage` interface. Each adjacent pair is
linearly interpolated and evaluated at a midpoint; the caller sets a maximum
permitted knot gap and integer subdivision count. Clock, origin, and both
source-knot identities remain on every generated stage. No extrapolation or
weather reconstruction is supplied. Stack temperature and enabled/isolated
command remain explicit inputs.

Deferred Nurion case `pv-profile-midpoint-stages` checks stage boundaries,
source identity retention, exact integration of linear irradiance under the
midpoint rule, rejection of a larger-than-declared gap, and finite-ledger
execution at two resolutions. It has not been run. Exact integration of linear
forcing does not guarantee convergence of the nonlinear PV/load-line response;
refine the chosen series before relying on its integrated production.

Static checks for the bounded profile increment: Ruff and Python compileall pass; diff whitespace check passes. No model, native import, scientific test, or cluster execution was run for this change.

| Updated file | SHA256 |
|---|---|
| src/h2physics/adapters/pv_electrolysis.py | 4aa16295193ea0bcc823ea740e9204f71ff77f4bbd3ee6a99023cebe8e21e5fe |
| examples/pv_electrolysis.py | 6381536ec6a616096add234b001bce8d34b962bab8279d4191024f122f83e0e4 |
| validation/cases/pv_electrolysis.py | 01815f274e5260dca375502d6cac6d400611dd826a05bb5546ab2a37370b27c3 |
| docs/PV_ELECTROLYSIS.md | 807456b7ad6f8b83d41d6b4f3c32871410f81af376575b7cca1cb2022f5ba315 |
