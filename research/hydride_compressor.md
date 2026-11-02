# Finite hydride compressor verification — 2026-10-27

Frozen scope: one thermally driven lumped hydride bed between actual finite
source and receiving native gas/wall vessels. This advances delivered compression
beyond the earlier closed heated bed. It is synthetic numerical verification,
not a material/apparatus calibration, cyclic steady state or manufacturer
qualification. No measured logger pressure/flow/reference/clock omission was
invented. No source code, coefficient table, dataset or worked example was
copied from a third party.

## Reused physical owners and approved shared increment

The parent approved the narrow finite_hydride.py extraction before edits. Its
existing closed simulate API now delegates state reconstruction and instantaneous
conserved rates to public snapshot_from_inventory and rates. All16 original
closed tests pass unchanged. Existing HydrideKinetics/VanthoffPlateau/Arrhenius
objects retain ownership of uptake/release/equilibrium; BoundHydrogenEnergyReference
retains the native gas enthalpy zero and bound-H energy. No second rate law or
bed equation is implemented in the compressor.

Two actual LH2DT HomogeneousTank cores own source/receiver fluid and wall
derivatives; their TankState and TankDerivative objects are retained. The
existing HEOS gas provider is shared through Lh2dtLowLevelProperties. Actual
native CoolProp objects remain in HydrideGasThermodynamics.native_objects. The
existing HomogeneousIsentropicNozzle solves both forward-only ports. One common
SciPy DOP853 solve orchestrates all bodies and integrated ledgers simultaneously;
there is no copied tank ODE/EOS/valve/choking solver, stale independent reservoir
stepping or prescribed receiver pressure. Optional native imports remain lazy.

LH2DT is separately installed under MIT at
`b2f276333c1b1793c39f25763703d196d36742ec`, source aggregate
`5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
The existing [native receipt](native_lh2dt.toml) remains authoritative. This
increment installed no new dependency and changed no main environment.
Measured local stack: Python3.12.14, CoolProp8.0.0, NumPy2.5.4, SciPy1.18.1;
the parent also executed the complete suite with compatible SciPy1.16.3.
Native source/receiving walls have actual positive capacities and UAs because
the pinned TankGeometry rejects zeroUA. No epsilon-UA adiabatic workaround is
used. Prescribed baths are external thermal utilities, with actual signed duty
recorded; no finite HTF/heat-recovery circuit is claimed.

## Conservation and reference boundary

External gas mass flow into the bed and its total gas derivative after uptake
are distinct. Donor stagnation enthalpy enters the receiver/bed; outlet kinetic
energy from the shared nozzle thermalizes inside the receiving well-mixed volume.
The native source tank owns its actual withdrawal enthalpy, checked against the
shared nozzle. Source and receiver use the same explicit pure-H2/spin/reference
basis as the bed. Normal/para are separate native choices; no conversion is
inferred from a name.

Solid energy is its declared sensible capacity plus bound-H chemical energy.
The bound increment is h_gas_ref*M_H2−DeltaH_des_ref, so reference closed
absorption has DeltaU=P*v_molar−DeltaH_des (ideal limit RT−DeltaH_des).
Nominal reaction heat is recorded but not added again. The variable-mass
isothermal reference correctly includes net external mass and material enthalpy
in its thermostat duty. A consistent gas-U/H plus bound-H zero shift preserves
open-port physical thermal rates; shifting only one side would be invalid.

All-body hydrogen includes source gas, bed free gas, bound H2 and receiver gas.
All-body U includes those gases, bed sensible/binding energy and both actual
native walls. Internal mass, stagnation-enthalpy transport, material sorption
enthalpy and gas/solid heat cancel globally. Bed gas, bed solid and each complete
native vessel also have separate ledgers. Signed bed heat and actual native
external wall/bath heat remain as external energy; wall/fluid heat stays internal.
Gross positive/negative bed duty sums separate heat channels without implicit
heat-recovery credit. The native PT reconstruction below independently reads
reported P/T/loading/wall temperatures using a fresh HEOS instance; it is an
independent calculation path, not independent experimental EOS validation.

The constant-enthalpy Vanthoff plateau and loading-independent solid heat
capacity remain reduced constitutive assumptions. Reference desorption enthalpy
is not asserted to be the same caloric heat at every T/P. Source-qualified
mutually consistent PCT, loading-dependent calorics and entropy/free-energy
evidence are needed before a second-law or efficiency claim.

## Explicit authored sequence

These values are synthetic verification choices, not parameters fitted or
reconstructed from the MHC workbook. Pure normal HEOS H2; hydride capacity.005kg,
solid C50J/K, reference DeltaH_des24000J/molH2, DeltaS80J/(molH2K),
reference fugacity1e5Pa, existing absorption/desorption coefficients.02/.05s^-1
with zero activation energies, no imposed hysteresis gap/slope. Bed gas volume
.0005m3, gas/solid conductance1W/K, solid/bath conductance20W/K, gas/bathUA0.
Initial bedx.01, gas2e5Pa/300K, solid300K. Each native external vessel has
volume.03m3, wall C500J/K, ambientUA2W/K, fluid/wallUA10W/K, initial wall300K.
Source starts5e5Pa/300K; receiver starts1e6Pa/300K. Both are actual finite H2
inventories; no pressure regulator or refill exists. Effective port area1e-7m2
with factor1 and native one-way shared-nozzle flow; no measured Cd/Kv is claimed.

Absolute clock100→300s, one declared clock ID. Cold admission50s/bath300K;
isolated heating40s/bath450K; hot delivery60s/bath450K; isolated cooling50s/
bath300K. Native vessel baths300K throughout, direct wall powers0. Output every
2s with both pre/post command endpoint observations. Baseline maximum step1s,
rtol1e-8; refinement.5s/2e-9. Internal energies/ledgers use conditioning
scale1000J and are returned in SI J. Declared gas/solid domain200–600K,
10Pa–10MPa, pure single gas/supercritical gas only; it is a numerical envelope,
not a qualified alloy operating range. Inventory floors are positive1e-7kg
unless deliberately raised for a localized-floor test.

| Observed quantity | Actual result |
|---|---:|
| Admitted source H2 kg | 0.0014402305261444013 |
| Delivered receiver H2 kg | 0.0010562679906164936 |
| Delivered above evolving source pressure kg | 0.0010562679906164936 |
| Initial complete bed H2 kg | 0.00013072373106295823 |
| Source pressure initial/final Pa | 500000.0 / 437780.6023974555 |
| Receiver pressure initial/final Pa | 1000000.0000000001 / 1057429.0247998731 |
| Minimum delivery receiver/source pressure ratio | 2.2900645256376233 |
| Final bed loading | 0.0948648585160289 |
| Final solid temperature K | 300.0000641651783 |
| Gross supplied bed heat J | 23596.768234523326 |
| Signed removed bed heat J | -26553.797348661767 |
| Maximum all-body H2 residual kg | 6.938893903907228e-18 |
| Maximum all-body U residual J | 2.6983570933225565e-10 |
| Fresh native PT mass reconstruction error kg | 6.938893903907228e-18 |
| Fresh native PT U reconstruction error J | 2.9103830456733704e-11 |
| Refined delivered-mass difference kg | 5.204959727111991e-13 |
| Refined final-loading difference | 1.0409932638122399e-10 |
| Refined final-solid-T difference K | 1.7053025658242404e-13 |
| Positive bed-floor root time s | 100.0090865982427 |
| Native dilute ideal thermostat relative error | 1.9474970634077918e-06 |

| Stage | Final bed P Pa | Final solid T K | Final loading | Actual RHS evaluations |
|---|---:|---:|---:|---:|
| cold-admission | 225051.53644816755 | 316.04204077843406 | 0.2966257889142638 | 992 |
| isolated-heating | 2232057.008823824 | 447.9535117619107 | 0.19626285778952945 | 839 |
| hot-delivery | 1066597.3061925592 | 445.4505093269418 | 0.045094542218583306 | 1184 |
| isolated-cooling | 99941.83901988094 | 300.0000641651783 | 0.0948648585160289 | 1418 |

The bed ends with more retained hydrogen than it initially held: admitted and
delivered amounts need not match. That difference is explicitly inventoried, not
called a feed-origin recovery or corrected to force cyclic closure. Delivering
more than the complete initial bed inventory confirms the finite source is
necessary. Returning solid temperature close to300K does not establish returned
loading or cyclic steady state. No efficiency is computed from the nonperiodic
sequence's net/gross heat.

A separate longer720s/Csolid300J/K authored probe completed all four stages in
151.36s:4.29737g admission,4.43535g actual delivery above finite source pressure,
maximum closed heating pressure24.3186bar, finalT300.00048K/x.08048 fromx.1,
global mass2.78e-17kg andU6.73e-10J. This is additional pre-final-guard numerical
evidence, not the final fingerprint replay. The shorter substantive full sequence
keeps repeatable regressions bounded.

## Actual acceptance evidence

- Scoped tests: **34passed in78.36s** — all18new tests and all16unchanged closed finite-bed tests.
- Independent read-only review found no remaining concrete P1/P2; three direct shared-core/reference tests passed3/15deselected in8.83s without rerunning a cycle.
- Final actual native replay: **20/20gates**, 105.04435259999809s. The5host inputs and native source aggregate match at begin/end and final on-disk bytes.
- Parent integrated main and compatible suites: **870passed/11explicit optional skips**,216.34s and216.22s respectively, all230Python fingerprints unchanged. Optional skips are not execution evidence.
- Parent also replayed existing finite-hydride and microsphere checks successfully with the updated shared core.
- Ruff, whitespace and UTF-8/LF checks pass. No shared catalogue/general docs/metadata were edited by this task.

Checks cover actual finite admission/high-pressure delivery, native object and
NozzleResult retention, isolated port stages, thermal rate reversal, separate
body/gas/solid and all-body U/mass, fresh native PT reconstruction, full-sequence
refinement, consistent reference translation, low-density ideal variable-mass
thermostat pressure work, normal/para zero-kinetic limits, reverse-pressure
blocking, positive bed/source floor localization, phase/reference/clock/domain
rejection and runtime/post-run error retention. The isolated-heating limit
exceeds1MPa bed pressure while its actual delivered mass remains exactly0.
Fixed physical acceptance budgets were not relaxed:1e-12kg mass,1e-5J U;
fresh PT reconstruction1e-10kg/1e-4J; delivered-mass refinement1e-8kg,
loading1e-6, final solidT.001K; dilute ideal thermostat1e-4relative.

The final replay contains five common native-coupled runs (baseline, refined,
isolated heating, positive floor, zero/reverse limit) plus a direct native
isothermal reference-rate evaluation. Actual reference/rate/callback fault
injection belongs to tests and is not claimed as physical validation.

## Events and retained limitations

Three positive inventory-floor functions stop the common solver and return the
actual root state/time. This is an operational numerical guard, not exact zero
exhaustion, a new limiting correlation or valve closure. No post-event flow
termination history is invented. Loading remains governed by existing kinetics;
no negative state or signed measurement is clipped. A phase/domain/trial failure
may occur before a floor and is retained rather than repaired.

Delivered-above-source mass partitions the integrated outlet-mass ledger at
localized roots of receiver minus source pressure. This is a bracketed-crossing
contract with step refinement, not arbitrary hidden within-step nonmonotonic
event completeness. The authored sequence has persistent receiver>Psource and
all delivery is above that evolving finite pressure. No peak or average pressure
is substituted for actual delivered mass.

Failures preserve completed segments, the current original OdeResult if SciPy
returned one, audited points, last actual trial time/vector and separate failing
audit time/vector, plus the original native/callback cause. A failed RHS may
prevent any partial accepted OdeResult being returned; no such history is
fabricated. Body objects and original results are retained and mutable; changing
native/model parameters during a run invalidates recorded correspondence.

This level has one bed pressure, gasT and solidT, fixed free volume/capacity,
constant sensible capacity and the chosen reduced PCT/kinetics. No porous
transport, powder/porosity change, bed spatial gradient/separate wall, heat
recovery circuit, cycle-closure solver or qualified entropy/exergy performance
is supplied. MHC logger normal-volume/gauge-reference and clock/calibration
gaps remain open; shell/HTF observations are not renamed solid-bed temperature.

## Reproduction, source fingerprints and primary basis

```powershell
.venv\Scripts\python -m pytest tests/test_hydride_compressor.py tests/test_finite_hydride.py -q
.venv\Scripts\python -X utf8 scripts/check_hydride_compressor.py --native-target artifacts/native_packages
```

Native path setup is explicit in the script/test fixture; the public API takes
Python/native objects directly and requires no JSON/files/server. Durable ignored
logs: artifacts/hydride_compressor_feasibility.log, hydride_refactor_tests.log,
hydride_compressor_probe.log (longer probe), hydride_compressor_short_probe2.log,
hydride_compressor_tests.log and hydride_compressor_replay_final.log.

| Final replay input | SHA256 |
|---|---|
| src/h2physics/storage/hydride_compressor.py | `af1cb4f1ce1c35ec7651144740db5f8ef4e0a92a7d7dd96184110913891314d1` |
| src/h2physics/storage/finite_hydride.py | `9fa148a4b1680bf2deccca71cad4d518973bd2c9a6b146bd7a48764ce86ea989` |
| tests/test_hydride_compressor.py | `87f3b7570ce006be1d392df7b696a9cf0873c8f7f2ea2af4c5af1605f8695d3d` |
| scripts/check_hydride_compressor.py | `e430f4f5a334a106b26e8feaea937ff4df7a84d6a5d4f85cbb3d3c2e528b9305` |
| docs/HYDRIDE_COMPRESSOR.md | `963be419680e989d4dc3c7af05565b3230804a96dc12c8bb411874342aa3a6c4` |
| native:lh2dt | `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61` |

The report's own hash is captured externally in the final freeze notice.
[API and physical boundary](../docs/HYDRIDE_COMPRESSOR.md) documents direct native
composition and units. The parent owns request020 and the general catalogue/API
connections. No native repository, remote state or Git commit was changed.

Primary context: [Brown etal.2006 finite hydride mass/energy](https://escholarship.org/uc/item/67p6w2p3),
[Krane etal.2021 coupled hydride reactors](https://arxiv.org/abs/2107.06095),
[Fleming etal. thermal compression concept](https://pmc.ncbi.nlm.nih.gov/articles/PMC12988172/),
[Leachman pure-H2 EOS](https://doi.org/10.1063/1.3160306),
[CoolProp native API](https://coolprop.org/coolprop/LowLevelAPI.html) and
[NASA analytic nozzle reference](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html).
Only original conservation composition, interface code, parameters and tests are
provided. Independent material PCT/calorimetry/kinetics, source-qualified geometry,
finite HTF/utility capability, multibed/CSS operation and held-out apparatus
comparisons remain receiving work.
