# Finite surface-impact coding record

2026-10-28. Status: **implemented_unverified**. No model/module import,
calculation, example/case invocation, native installation, local pytest,
scientific replay or benchmark was performed. Native source, metadata and
license inspection, public primary-source reading, AST parsing and Ruff are
the only checks in this lane. Scientific execution is deferred until the user
later connects Nurion. No cluster job was submitted.

Owned new files: adapter `droplet_impact.py`, documentation `DROPLET_IMPACT.md`,
this record, example, deferred case catalog and optional dependency receipt
`droplet_impact_dependency.toml`. No shared physical source, general
documentation, catalog, requirements or external repository was modified.

## API findings and substantive new boundary

The existing `SaturatedParcelFlight` returns an actual native SciPy result,
accepted phase/mass/velocity states, integrated conservation residuals and
`incident_ground_crossing`. It deliberately supplies no deposition fraction.
The inspected existing DEGALI rainout path identifies ground-reaching mass;
it does not supply a qualified LH2 collision/thermal/outcome closure. No such
correlation was fabricated or borrowed from water/hydrocarbon experiments.

The new model is an original **conditional finite thermo-mechanical boundary**.
It reuses actual normal-H2 saturation EOS objects/states and native SciPy generic
roots. Caller-qualified deposition/restitution/velocity/conductance/contact-time
parameters have explicit domain/evidence/origin and an original owner/result.
Synthetic numerical parameters remain visibly unqualified.

Vapor mass is not a supplied splitter fraction. A bracketed finite-mass root
couples native latent enthalpy, finite patch capacity/conductance, outgoing
rebound/vapor kinetic energy, intermediate recoil and dissipative mount arrest.
The finite patch cools and is not refilled with external heat. Liquid remaining
after this solved evaporation is divided using the supplied liquid-outcome
closure. A closed-form finite-capacity dryout event stops phase heat when the
incident stock ends. No infeasible requested vapor mass is clipped.

The patch's finite recoil mass and thermal capacity serve different physical
roles. A fixed mount receives explicit impulse and does zero work; it is not
a thermal reservoir. Recoil arrest heat remains in the finite patch. Signed
interfacial internal-energy change is explicit. Passive mechanics is checked
within the stated numerical energy budget; absent active work is rejected.
Fluid stored energy uses native U, with ambient pressure work -P DeltaV for
the phase expansion. The total-U, mass and momentum residuals are retained.

The event is lumped/impulsive, with constant qualified coefficients. Mechanical
trajectory, gravity/support work over that trajectory, evolving contact shape,
splash, wetting/Leidenfrost regime, secondary droplets, air condensation, RPT,
dispersion, combustion and independent H2 validation remain unresolved. The
evidence contract must justify the approximations in its intended domain.
No material calibration follows merely from finite conservation.

Sequences retain finite wall temperature. Deposited liquid is cleared through
an explicit ideal at-rest receiver boundary; a wet-pool impact is excluded.
The default intercontact boundary is adiabatic and requires evidence. An
optional callback can instead return a caller-calculated finite integrated
heat input, actual interval, source record and interval temperature extrema.
This updates the wall state before the next contact. The trace-wide energy
ledger sums each contact balance from its post-gap wall state, accounting for
the gap input once; no intercontact trajectory is solved.
Both boundary ownership and clearing require evidence. Contacts
cannot overlap or precede the patch's explicit initial-state clock. Absolute
contact/dryout spans must be representable on the
incident clock; unresolved spans fail rather than becoming instantaneous.
Failures preserve the original cause/incident/native result, completed prefix,
phase-root trials and available failing-state context.

## Actual native pool connection and receiving gap

Actual installed DynamicLH2PoolX 0.2.0rc2 is MIT and already reviewed at
revision 6a700e8e183039bbb81803bacc416f6c9117ed71. Its spreading
`DynamicPoolConfig` explicitly rejects nonzero initial inventory. Its
`FixedAreaPoolConfig` accepts a finite initial stock. The new helper creates
that actual initial-stock config, actual zero native continuing inflow and
retains `run_fixed_area_pool`, the native module and original deposited batch.
It does not run the native pool during initialization.

No arbitrary pulse duration or delayed rate history is invented for a deposit
already on the ground. The native fixed-area substrate heat is a separate
explicit continuation owner. It does not silently restart this finite wall
as an infinite substrate, and the returned finite-patch continuation flag is
false. A native restart accepting deposited inventory/radial state and this
finite surface energy/state remains required for simultaneous conservative
pool continuation. Current handoff is a batch initial condition with an
explicitly different thermal boundary, not that missing capability.

The dependency receipt records actual installed source/license/metadata SHA256
values. There is no new dependency installation or redistributed native source.
Native API source bytes were unchanged between inspection and static freeze.

A static integration review found that accepting an `ImpactStep` by type alone
could admit a replaced cached deposited mass. The helper now requires the
actual impact owner and its exact originally accepted step object. The owner
retains a physical-field snapshot plus a digest of the original native incident
arrays at acceptance. Clones or changed step/batch/phase/native-incident values
fail before native pool access. This is result-correspondence admission, not
an independent physical validation or protection against deliberate private-
registry tampering. The returned native initialization retains the actual
impact owner and original step. The existing native-pool case defines clone
rejection and actual native incident-array mutation/restoration rejection. A
ninth case defines callback-driven intercontact heat and trace-wide wall-energy
accounting. None of these checks was executed locally.

## Deferred case inventory

Nine metadata-only definitions use profile **droplet-impact** and the shared
`ValidationCase`/`ValidationOutcome` contract. Case import/discovery defines
entrypoints but does not solve a model. Actual native parcel traces are built
inside the deferred entrypoints; no fake/mock incident is used as physics
evidence.

| Definition | Intended future gate, not a result |
| --- | --- |
| impact-baseline | Coupled finite heat/phase/mass/U/pressure-work/momentum and original native object retention |
| impact-elastic | Independent two-body restitution-one velocity/recoil limit, followed by finite recoil arrest |
| impact-zero-contact | G=0 gives no vapor, preserves finite liquid and records mechanical heat |
| impact-dryout | Full finite vapor event localized before the maximum contact time |
| impact-refinement | Actual parcel step and phase-root tolerance refinement |
| impact-missing-heat | Cold finite patch fails without invented heat |
| impact-prefix | Unprovided vapor kinetic work rejects with a completed prior contact retained |
| impact-intercontact-heat | Finite integrated heat updates the next wall state and closes the trace-wide energy ledger |
| impact-native-pool | Owner-issued step/native-array binding, rejection of changed stock, actual native initial-stock config/runner and separate pool mass closure |

The profile reuses existing NumPy/SciPy, CoolProp and the reviewed
DynamicLH2PoolX dependency. All nine physical/runtime gates remain unexecuted.
Static parsing and Ruff passed for the adapter/example/case files. LF and
receipt/hash checks are file-byte checks; no scientific acceptance is inferred.

## Primary sources and input freeze

The [official CoolProp saturation API](https://coolprop.org/coolprop/HighLevelAPI.html)
defines native endpoint/latent-state queries, and the existing
[hydrogen EOS reference](https://doi.org/10.1063/1.3160306) retains the shared
property ownership. [MIT transient heat-transfer notes](https://web.mit.edu/16.unified/www/FALL/thermodynamics/notes/node129.html)
support the lumped finite-capacity energy balance and its spatial-uniformity
assumption. These are independent equations, not copied implementations.
[Primary impact-regime work](https://arxiv.org/abs/1111.0435) motivates retaining
the regime/outcome boundary explicitly; its other-fluid correlations are not
imported into this LH2 level. The [official native pool repository](https://github.com/lyullee/DynamicLH2PoolX)
defines the reused native initialization/continuation contract.

Before this increment all six owned paths were absent. Final Python/doc input
SHA256 values are listed below. The report/receipt hashes are sent to the
parent after final writing, avoiding self-referential hashes.

| Input | SHA256 |
| --- | --- |
| src/h2physics/adapters/droplet_impact.py | `6b26ddd6047db0fad16cdb5186941e13b5db90f58d3faaee239d802ef903999e` |
| examples/droplet_impact.py | `06dccf722aaf524f574fda8aebaa4762d6a8e1413042de1657f78a759fbb83a4` |
| validation/cases/droplet_impact.py | `c9fa57e49c197a31a253af8f6811d7739951be644e6b94dc5d72fccba3a73936` |
| docs/DROPLET_IMPACT.md | `77594cfc66e1029f54b33da03e7cc367872e7b1d032ff56ac55aa6cb18493aad` |

Before the owner-binding correction, source/case/doc SHA256 values were
8bfd3843a3a66ceb8c5612291291739aa55072469f1ccf4810ee99ac1b5fed7c,
dcf3716db28c9c70e18deff595f3573aa4cba270b463580308516c44b4da9013 and
2d492c3ff67d8f6438633405c9faf6a1a1ce22f06253e1031f1918d5c4fc41b5.
That earlier correction changed admission/retention only; the subsequent
intercontact increment below adds a caller-owned thermal boundary. Final
syntax/lint checks passed; the new gates remain deferred, not passing-test claims.

## Finite intercontact thermal boundary — 2026-10-29

`FiniteSurfaceImpact` now accepts an optional Python callback for integrated
net heat over each actual gap from the patch's initial-state clock or previous
contact endpoint to the next accepted incident. The result retains exact clocks,
heat, path temperature extrema, origin and source record. The callback owns its
thermal calculation; this level checks interval identity, endpoint consistency,
material/impact-domain limits and finite energy-to-temperature conversion.
With no callback, the patch's evidence-bound adiabatic condition remains the
default. Each new `ImpactStep` retains the result, and the sequence trace sums
contact residuals from post-gap states so energy is accounted once. A ninth
deferred Nurion case covers a two-contact prescribed heat reference. It is not
an executed result or independently qualified heat-transfer model.

Only Python byte compilation, Ruff on the changed Python files and `git diff
--check` were run after this increment. No module import, test case, scientific
calculation, benchmark or local replay was run.

This is one implemented_unverified increment, not an executed or independently
validated first level. No passing test count or scientific runtime is assigned.
