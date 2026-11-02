# Verification and validation strategy

## Evidence levels

| Level | Meaning |
|---|---|
| Planned | Scope exists; no executable scientific claim |
| Implemented | An algorithm and explicit domain can execute |
| Software verified | Analytic limits, invariants and numerical behavior have been checked |
| Externally compared | Results were compared to an identified independent source or experiment |
| Domain qualified | Predeclared application and acceptance criteria pass with appropriate evidence |

No level is inferred from test count, matching object schemas or a successful import.

## Required checks

- Analytic limits, dimensions, signs, monotonicity where physically required and domain errors.
- Mass, species, energy and relevant momentum ledgers across component/coupling boundaries.
- Time/space/domain refinement and solver tolerance studies for dynamic/distributed models.
- Event alignment for switching, isolation and inventory exhaustion.
- Property comparisons at held-out states, phase boundaries and critical-region guards.
- Calibration identifiability and predeclared held-out experiments/observation operators.
- Uncertainty attribution to measured inputs, parameters, numerical error and model structure.
- Regression checks for exact external engine versions, without inheriting broader claims.

Each validation run records source versions/checksums, input parameters, code/dependency
versions, cases, metrics, acceptance criteria, results and limitations. Synthetic examples
exercise interfaces and conservation; they are not experimental validation.

Before importing the selected Hangang case entrypoint, the worker compiles every Python
source under the pinned `src/h2physics` tree in memory. This catches package syntax errors
without importing those modules or executing a model and records the checked file count in
the worker outcome.

## Current release checks

`tests/test_release.py` compares the shared nozzle with independent constant-cp gas
critical-pressure/flux formulas and unchoked back-pressure endpoints, then exercises
CoolProp gas/subcooled/saturated/two-phase paths, energy/reference failures and source
identity/termination. `scripts/check_release_integration.py` uses the separately installed
native LH2DT tank for gas and cryogenic bulk depletion, separate-window isolation and
accepted-node quadrature refinement. Actual results are in `research/native_release.md`.
These checks establish selected numerical/boundary behavior only. Independent discharge
experiments, effective-area coefficients, phase-selective extraction, depletion-event
location, external expansion, droplets and ground transfer remain unqualified.

`scripts/compare_discha_release.py` now applies four public warm DisCha experiments.
Pressure/closed-thermocouple means reconstruct inventory and force the shared nozzle;
one complete run is held out from the effective-area fit. The held-out inventory-fraction
RMSE is about 0.003612. This is a conditional consistency comparison with shared EOS and
temperature forcing, not independent mass-flow or tank-energy validation. Sensor gradients,
metrology, ambient/spin assumptions and pipe/valve effects remain visible. Negative
flat-peak numerical results and unchanged-gate corrections are recorded separately.

## Native equipment and coupled finite inventory

`scripts/check_equipment_network.py` verifies a phase-resolved native tank feeding mapped
pump, heated pipe/vaporizer and shared-kernel valve. It checks native and independent
external mass/energy at every RK stage, three time steps, accepted nozzle-plane history,
declared NPSH/map admissibility, laminar gas/HEM limits and a separate enthalpy-coordinate
vaporizer reference. A converged but inadequate-NPSH graph is rejected. Missing valve
momentum remains unavailable. Port kinetic/potential energy is outside the steady enthalpy ledger.

A closed heat case retains the negative original native ledger result and the explicit
host correction without changing native phase equations. `scripts/check_lh2dt_property_provider.py`
compares actual native state factories across 60 flash queries, transport/saturation and
measured timing. The complete solver also compares the original/accelerated provider at
the same time step. Results and hashes are in `research/native_equipment_network.md` and
`native_property_provider.md`. These are synthetic numerical/interface checks; independent
equipment maps/data, line/vaporizer storage and complete isolation remain unqualified.

## Finite-device isolation continuation

`scripts/check_dynamic_inventory.py` separately exercises native line/vaporizer fluid/wall
storage with prescribed feed/outlet closure at non-grid times. Three step widths check
final node mass/pressure agreement; every stored-device mass and energy balance is checked
individually across interval restarts. After feed closure about 4.66e-6 kg still discharges;
after both external ports close the assembly retains mass and continues heating. Reversed
internal transfer checks actual upstream energy. A warm closed wall-only analytic limit
has about 1.23e-7 K error and verifies absolute ambient clocks across two restarts.

Unsplit 0.1 s discontinuous controls change final mass by about -6.95e-7 kg, although their
computed flux ledgers close. This negative comparison separates timing accuracy from
conservation. Incorrect wall storage and a command that replaces a conserved fluid boundary
are rejected. Unit fixtures independently exercise missing heat, ledger and accepted-identity
failures. No RK-call-count assumption is needed for accepted rows in this driver.

Exact gates, parameters and source fingerprints are in `research/native_dynamic_inventory.md`.
This remains synthetic verification. Independent apparatus data, spatial refinement,
pressure-trigger localization, finite stroke, complete depletion and combined finite
tank/pump/line/vaporizer qualification remain open.

## Combined finite supply and explicit operating modes

`scripts/check_finite_supply.py` now checks one native finite phase-resolved tank/pump/
line/vaporizer/outlet assembly. Three short-sequence steps compare final mass/pressure;
the original and single-flash property paths are compared at one common step. Each stored
device closes its own native integrated mass and fluid/solid energy. A separate external
comparison uses command-aware sampled delivery/shaft integrals and independently recomputed
wall-to-ambient heat. Its quadrature errors decrease under refinement; gates are 1e-8 kg /
0.01 J, distinct from the tighter native inventory ledgers.

Long isolated heating to 1 s reverses the internal transfer. An initial 0.0025/0.00125 s
pair conserved inventory but failed the 1e-6 final-state gate. The 0.00125/0.000625 s
pair passed that unchanged gate, but a finer accepted point failed independent Darcy loss
(about 44.31 Pa despite a reported zero). The corrected common-kernel/explicit continuous
correlation case retains both gates. The Darcy loss is independently recomputed at accepted
points from actual upstream density, signed flow and reported friction, with a 0.01 Pa
gate. The closed assembly preserves mass and changes total energy only through ambient heat.

Mode selection is explicit. Omitted pump work and invalid map points fail without selecting
the isolated branch. The native zero-speed setter remains unsupported, and request 008
specifies resolved stopped/coastdown behavior. A closed-valve branch is an ideal combined
stop/isolation limit, not rotor/casing dynamics. Full inputs, observed positive/negative
results and source fingerprints are in `research/native_finite_supply.md`. Independent
apparatus/plant data, spatial/trigger/depletion and real-machine qualification remain open.

`tests/test_hydraulics.py` separately verifies Poiseuille, analytic fixed friction, explicit
root-endpoint metadata and a discontinuous-law gap that has a scalar root flag but no
closed constitutive solution. The retained native state reproduces the actual fixed-point
failure and a same-native-law bracketed rejection. Only the explicitly selected continuous
correlation plus converged kernel closes it. This distinguishes numerical correction from
empirical model selection. HYDRAULICS.md and request 009 record the decision and limitations.

## Measured PEM frequency-domain continuation

Six portable tests exercise full-stream hashes, caller stream ownership, SI conversions,
zero/missing masks, GC protocol restriction, ragged input rejection, DC-tail separation,
frequency direction/reset, rejected acquisition gaps, complex origins and native order/
component contracts. The full suite at this checkpoint has 117 passing tests. The actual
impedance 1.7.1 CustomCircuit additionally agrees with an independent alpha=1 RC analytic
limit within 3.47e-18 ohm in the standalone measured replay.

The full four-member hash audit covers 23764321 rows; the explicitly selected initial
two POL_GEIS counters retain 14971 rows and 144 spectra/3312 complex readings. The 120 s
DC-context gate leaves 28 sweeps without a reconstructed operating point. Actual extra
14 A/repeated 12 A sweeps are retained despite the nominal 17-level description.

One complete 12 A counter-1 sweep per cell is fitted, without point rejection, to the
same preselected native five-parameter circuit/bounds/starts. Complex fitting RMSE is
approximately 0.079–0.614 milliohm. Four of eight complete held-out repeats fail the
unchanged illustrative 1 milliohm target; failures reach 4.23 milliohm. All three fixed
Reference-to-other-cell predictions fail (approximately 4.57–14.61 milliohm). Scaled
condition numbers are about 3209–69680, and Reference inductance reaches its lower bound.
Those findings restrict physical parameter interpretation despite small fitted residuals.
Exact groups, fingerprints, bounds, SVD and positive/negative results are in
`research/pem_impedance.md`.

These are measured same-source conditional comparisons. Real/imaginary components are
correlated; repeated protocols are not independent cells, and separate cells from one
source do not supply independent-source qualification. Linear/time-invariant behavior,
Kramers–Kronig consistency, source uncertainty, low-frequency mechanisms, thermochemical
activities and true reaction temperature remain unqualified. No crossover/degradation
law or facility safety validation is claimed. This is an additional small-signal level
inside the existing production family, without creating duplicate static stack models.

## Native pool, input clocks and emitted mass

Ten portable contract/source tests bring the full suite to 127 passing tests. They
cover finite windows, clock/reference identity, nonuniform interval integration/rebinning,
continued evaporation after input isolation, zero reported footprint with inventory,
native object retention, explicit event-time corrections and failed mass/mean/property/
adjustment/escape/nonfinite claims. These fixtures do not implement a pool solver.

The actual dynamiclh2poolx 0.2.0rc2 source bytes match the exact reviewed GitHub revision.
An authored case inputs 0.025 kg/s until 1.13 s, then zero to 8 s. Independent input
integration first exposed a native extra 0.00025 kg step, despite a reported residual
about 7e-18 kg. Positive checks explicitly use a 1e-10 s event-clock budget, recording
a maximum finest-run correction about 4.44e-15 s. Mass gates remain unchanged at
1e-10 kg + 1e-8 times supplied mass, with zero allowed numerical adjustment/domain escape.

Three coupled coarse pairs fail the fixed 1% inventory/supply agreement target. The
dr=0.0025/0.00125 m, maximum-dt=0.00125/0.000625 s pair passes at about 0.734%, with
0.00125 m reported-radius change. Separate fixed-grid time comparisons are below 0.2%
but nonmonotone; no asymptotic order or Richardson uncertainty is claimed. Enlarging
the domain from 1.5 to 3 m leaves the checked values unchanged. A 0.3 m domain loses
about 0.01408 kg and is rejected. Zero thermal-driving inventory error is about
1.28e-16 kg; independent capped-conduction quadrature agrees at displayed precision.

The finest case emits 0.0282498734 kg, including 0.0244166527 kg after supply isolation.
Conservative source regrouping changes total mass by about -3.47e-18 kg. Sparse endpoint
rate trapezoids instead give 0.0319561560 kg. Reported radius becomes zero while inventory
and evaporation remain nonzero, and a tiny positive dry-depth residual remains at 8 s.
No depletion or source termination is inferred from input isolation or detection radius.

All inputs are authored; no experimental pool validation is claimed. Restricted data,
para-Hydrogen properties, initial radial inventory/restarts, atmospheric geometry/momentum,
independent heat ledgers and unresolved impact/terrain/air-condensation physics remain
explicit. Exact settings, failed gates and hashes are in `research/native_pool.md`.

## Native gas-plane and calm-jet continuation

Twenty-three new portable boundary/accounting tests bring the full suite to 150. They check
effective-area transfer, predicted origin and static/absolute enthalpy separation;
phase/basis/closed/mass/energy rejection, including very small flow; coordinate frames;
the isolated body-force source change; failed native result retention; and whole-mixture
spatial observation meanings. Malformed shape/nonfinite/missing native outputs retain
the actual completed result without constructing a false audit. Test doubles check
contracts, not native physical accuracy.

The actual MIT DEGALI 0.3.0 source snapshot is version and module-byte checked separately.
The one shared nozzle feeds its actual supplied-throat expander. Both normal/para gas
planes preserve mass, effective-area momentum and h+KE with HEOS PH consistency. The
native density-profile initial roots fail and are retained. Explicit temperature/
composition profiles close the initial balances without fitting entrainment parameters.
An original actual-native subclass changes only the vertical force to the actual profile
integral, retaining native profiles, Jacobian and spatial solver.

The short normal-H2 case passes at 321 radial points: species and horizontal momentum
errors are about 1.1e-8 and 1.2e-8; maximum energy error about 0.025 W against a
0.118 W budget. The 161/321 endpoint Y change is about 9.1e-5 relative and T change
6.6e-6 K. Independently sampled vertical momentum/force-integral difference is about
1.2e-7 relative. Coarse failures remain in the report.

The cold para-H2 energy gate fails at all four recorded grids, including about 0.346 W
at 641 points against an unchanged 0.238 W budget. Species/horizontal momentum, endpoint
Y/T agreement and sampled vertical force agreement do not override that failure. A
preliminary tighter DOP853 diagnostic was interrupted without a completed cold result.
The two-fluid research check therefore exits nonzero after preserving its full report.
The default host rejects the cold prediction while retaining its actual native objects.

No coefficients were fitted; no independent gas-jet observations were acquired/applied
in this continuation. Mixture-phase EOS/enthalpy, gas-phase probe operators, source
clocks, ground/crosswind and gravitational-energy approximations remain explicit limits.
Read NATIVE_JETS.md, request 011 and `research/native_degali.md` before composing a case.

## Measured spatial gas-jet continuation

Thirty-three new tests bring the full suite to 183 passing tests. Authored workbooks
check spatial/statistic/source units, original cells, repeated moved grids, literal
ambient-header conflicts, evidenced corrections, He/H2 conflict, valid zeros, negative/
missing readings and statistic order. Shared-nozzle inverse tests recover known gas
inlets across subsonic/choked cases and reject unbracketed, zero, liquid or unqualified
inputs. Geometric tests independently check Cartesian projection, radial symmetry,
molar conversion, axial/tail/domain masks and diagnostic-only failed audits. The linear
component energy-reference test checks E+C*H2_mass_flux and unchanged physical budgets;
unbounded geometry does not invent a ground clearance.

The actual four licensed concentration workbooks yield 42 worksheets and 5256 spatial
rows. Source pressure/temperature ambiguity, one He/H2 title conflict and inconsistent
statistics are not silently corrected. The fifth workbook's airflow map is not promoted
to a uniform wind. Data counts are not independent experiment counts.

Five unambiguous calm configurations use measured mean flow, declared nominal area and
T0=mean ambient to invert the existing nozzle for an equivalent inlet pressure. Source
conditioning is separate from flow-prediction validation. Explicit source-relative
unbounded geometry, virtual-plane colocation, dry gas and a point-probe approximation
remain assumptions. Native coefficients are not fitted to concentration.

A native flux/source energy reference shift with C=specific source KE resolves two
unshifted initial root failures. C/2C initial states agree near 1e-15. Full trajectory/
gas-observer RMSE changes are about 5.2e-12 and 3.4e-12 for low-flow and held-out cases;
their physical audit classifications are unchanged. Host energy is converted back before
applying the original budgets. Native root/ODE/profiles/tables remain the same.

Four of five finest numerical cases pass. The 4 mm / 1 g/s case still has a physical-
reference energy defect about 0.131 W against 0.00764 W. All five fail at least one
authored field target. Measured/predicted RMSE spans about 0.91-2.90 volume-percentage
points, maximum error 6.49-18.07 points. The held-out 4 mm / 5 g/s case has about 2.90
points RMSE and 18.07 points maximum error. Complete valid coverage and fine-pair agreement
do not override a numerical/accuracy failure or qualify the source/probe assumptions.

`compare_hytunnel_jets.py` deliberately exits nonzero after preserving the full record.
Restricted quick/case reports do not overwrite it. Start/end source fingerprints detect
edits during a run. The original authored normal/para native checks were also rerun;
their cold energy failure remains. See HYTUNNEL_JETS.md, request 011 and the complete
`research/hytunnel_jets.md` evidence before drawing predictive conclusions.

## Finite carrier and prescribed-conversion calorimetry checkpoint

Twenty-one added tests cover finite forward/reverse inventories, mass/element/charge
constraints, an analytic Cp enthalpy balance, conserved-element reference invariance,
empty-product rejection, exact reaction-heat normalization, source/phase/domain guards,
archive exclusions, contradictory pair heats and actual native caloric accounting.
The full suite at this checkpoint is 204 passing tests. Read CARRIER_REACTIONS.md and
research/carrier_reactions.md for reproducible qualification and limitations.

The actual 10373-row table closes molecular element/charge/mass checks. The 28 repeated
canonical pairs have differing computed heats, so all 56 rows' heats are withheld by the
dataset-level path. Nine reported capacities differ beyond the declared 0.01 percentage-
point reporting threshold. Those are source qualification outcomes, not repaired values
or measured validation. Single-reference heats reject other T/P or phases.

Native installed GRI thermochemistry gives about 205.895 kJ/mol extent for the authored
steam-reforming stoichiometry at 298.15 K. Independent native whole-mixture and species
enthalpy accounting differ by about 3.49e-10 J. At imposed extent 0.2 mol for initially
1 mol CH4 and 3 mol steam at 1200 K/101325 Pa, zero-heat product temperature is about
980.324 K, with about 1.16e-10 J residual. This imposes conversion and retains the native
fit behavior; it does not validate reforming kinetics or compute equilibrium conversion.

## Parallel preferred-provider, pressure-data and finite-mixture checkpoint

The full integrated suite passes 263 tests, with Ruff and dependency checks. Eight
preferred-provider/source contract cases and 51 pressure-data/frozen-mixture/open-volume
cases extend the prior 204-test checkpoint. Native scripts preserve explicit source and
applicability failures; test success is not blanket engine or experimental qualification.

Pressure data inspection verifies all 19 acquired attachment hashes/metadata and fully
consumes 8 MAT / 9 XLSX exports: 7999992 SIGMA, 33310586 GEN3i and 78272 workbook rows.
Signed/negative/missing cells, independent clocks, unresolved pressure/concentration
bases and guide/export conflicts remain in the loader/qualification records.

Frozen properties exercise72 independent constant-Cp PT states, native PH/PS reset and
roundtrip cases,9 analytic shared-nozzle conditions,4 installed-mechanism nozzle cases
and an evolving native gas-volume/shared-nozzle connection. Native Jacobian probe sum
corrections are explicit and recorded separately from accepted-state ulps. Open-volume
checks include independent source integrals, UVY/SV limits, signed boundary ledgers,
wall/extraction energy quadrature and temporal refinement. Existing acceptance budgets
remain fixed. Appended energy ledger states are conditioned in 1e6 J/native unit and
returned in SI; an explicit raw-J reference verifies unchanged physical solutions.

The actual HyRAM source case retains its Gaussian-entry H2 mass-gap rejection, distinct
from near-constant subsequent transport. Actual SLAB source/premise checks pass at 5 m/s
and reject 0.2 m/s. A fresh compatible native environment reproduces both outcomes and
passes pip checks; 20 observed runtime packages are separately recorded. Read the four
new detailed guides and research records for inputs, clocks, source hashes and limits.

## Parallel equipment and finite hydride integration

The current default source suite passes331 tests, adding68 tests to the earlier263:
21 insulation,22 compression,16 finite hydride and9 AB2 profile cases. Full lint
and dependency checks pass. The three actual-native replay reports record source
fingerprints, uncorrected outputs, fixed gates and retained failures. Data profile
qualification scans all365402 source rows of7 sheets against all3 acquired receipts.

Native insulation independently closes supplied heat with fluid plus declared wall
storage; wrong wall capacities fail. Compressor ideal limits and real EOS native
PS/PH states are checked without treating a second interface to the same EOS as
experimental evidence. The small para-H2 PH residual fails a stricter exploratory
subgate; established common equipment acceptance remains unchanged. Compression
flow and cooling PT are prescribed; measured map/utility validation remains open.
Finite hydride verifies conserved total H2/U, independent integrated transfers and
native PT reconstruction, analytic isothermal/ideal-work limits, a consistent
energy-zero shift and finite-gas termination. It reuses the existing kinetics and
native EOS; source-specific material/free-energy/spatial/port validation is open.

These checks do not close independent validation or facility qualification. The
preferred HyRAM Gaussian source failure and SLAB low-wind rejection are unaffected.
Raw CVODE warnings remain visible in explicitly retained reference/negative tests.

Final default SciPy1.18.1 result:331 passed in96.94s. Compatible SciPy1.16.3 passed
all330 earlier cases in129.60s, followed by all9 final AB2-profile cases after adding
file hashes to row identity. That correction preserves physical experiment groups
across distinct workbooks and has an authored cross-file collision regression.
The7-sheet365402-row receipt/schema scan was rerun against final source bytes;
13 new executed-host report fingerprints and27 checkpoint source entries match.

## Protection, vent, recovery and instrument integration

Final unchanged source suites pass406 cases in each runtime: SciPy1.18.1 default
159.07s and compatible1.16.3 152.76s, computed as independent local processes. Ruff,
dependency and diff checks pass.75 new tests comprise12 relief,24 vent,27 recovery
and12 instrument cases. Native and executed-host source bytes are fingerprinted;
the four new reports verify26 scoped host source entries, including shared dependencies.

Relief verifies pure accepted-mode probes, transactional native commits, pressure
opening/reseat, finite inventory, source jumps, heat/enthalpy ledgers and refinement.
Fine event errors are below6.92e-5Pa /7.45e-9s bracket; energy defect about2.89e-11J
in the authored case. It is an ideal binary homogeneous-bulk protection reference,
not a sizing/certification or arbitrary-event-completeness result.

Vent independent inverse-UA gates retain coarse/clamped failures.20/100 original
native transition cases fail final momentum, worst about24.731Pa although the raw
native residual reports zero. An explicitly selected shared closure retains its own
identity. Actual native acoustic capability and low-Mach gates reject tiny-loss
counterexamples; small pressure/density change alone is insufficient. Signed heat
and PH transport close only the declared enthalpy scope, without invented source
velocity/area or full mechanical-energy qualification.

Recovery verifies24 authored latent/capacity points across3 H2 spin references,
finite condensation/refinement, analytic cold-side/heat-cap limits and actual flowing
mass/U/wall/reservoir conservation. Native zero steady-flow/capacity, above-critical
saturation target, over-withdrawal, callback/support and completed out-of-domain
step failures remain visible. Product collection and cycle power remain separate.

Instrument verifies exact native held-input limits, continuation, indication/bounds,
NumPy scalar diagnostics, incompatible quantities/bases/locations and explicit data
gaps. The actual-data rejection does not calibrate tau or establish process truth.
Independent field/calibration/measured model validation remains incomplete across
these families. Existing preferred-provider and native CVODE reference/negative
warnings are preserved; they are not hidden by this checkpoint.

## Spin, finite two-side thermal and reactive process evidence

Native spin verification covers rigid-rotor low/high limits, cutoff failure,
exact held-temperature conversion/continuation, frozen rate, reverse heat sign,
enthalpy-zero invariance, thermostat heat and a finite constant-pressure
calorimeter. The authored0.01kg /1000J/(kg K) /600kJ/kg-gap case reaches about
24.450454K with total-H defect2.73e-12J. The finite-time final fraction is compared
with a separate native-equilibrium/enthalpy root, not called exact asymptotic
equilibrium. It does not validate a catalyst, liquid-spin EOS or rigid-vessel U.

The finite heat exchanger uses seven simultaneous native integrations with two
actual fluids and two walls. Side/global energy defects are below1.4e-10J,
opposite interwall heat closes, and an independent native four-inventory
equilibrium root gives307.264634441K. An analytic two-wall limit, fresh native PT
inventory reconstruction, direction reversal, three step sizes and separate
accepted-sample heat quadrature pass. Native heat caps/domain/parameter mutations
and unqualified material-network additions are rejected. Zero interwall conductance
does not remove a side's own fluid-wall heat path.

Reactive gas extends the existing native volume and preserves frozen defaults.
Independent authored first-order closed/CSTR solutions and formation-energy
warming pass. Actual installed H2/O2 chemistry agrees with the existing native
closed reactor. Source/owned definition audits preserve thermo bounds/runtime
multipliers, reject altered definitions and isolate factory aliases. A coefficient
roundtrip gate is distinct from rate/state accuracy. Native callback failures
cannot disappear through a successful retry.

The carbon/steam replay adds three native host runs and one unextended native
IdealGasReactor trajectory. Steam-only gas produces about6.64918e-8kg net chemical
H2 over0.2s; the boundary H2 integral remains separate. Maximum energy defect is
3.75e-8J, element defect3.89e-17kg, plain-native full-trajectory T difference
2.67e-8K and Y difference1.25e-12. Coarse/fine T difference is8.45e-7K. Requested
output species minima are reported without clipping; this sampled check is not
a minimum over every internal native trial. No external reaction heat is added.

These are authored numerical, interface and native-reference checks. They do not
establish measured industrial yields, catalyst/surface/coke behavior, spatial
counterflow or flowing heat-exchanger hardware, nor full spin/tank coupling.
Detailed source identities, gates and limits remain in the three research reports
and the corresponding manuals. Existing frozen-volume checks were rerun after
the shared native core changed; preferred dispersion failures remain retained.

Final source integration:472 tests pass in both default SciPy1.18.1 (226.68s)
and compatible SciPy1.16.3 (221.01s), using independent local processes. The66
added tests are15 spin,12 two-side thermal,9 reactive gas and30 compressor-data
cases. Ruff, dependency and whitespace checks pass. Six final clock regressions
cover schema-qualified Excel serial/1904/ISO/German encodings and rejection of
unqualified scalar elapsed/time-of-day values. Previously passed466-case runs
preceded that final decoding correction and do not replace these final suites.

The final complete MHC replay verifies35 members and29 experiments/186 worksheets,
including all182 recorder export groups. It preserves520726 populated recorder
rows,4420 active missing clocks and17 nonincreasing edges. Script/loader/test
begin/end hashes match final LF source. An earlier terminal-linked audit process
vanished before completion and its partial output was not counted. A bounded
detached run with durable per-experiment checkpoints completed, then the actual
clock-encoding correction was independently replayed across the entire archive.
Only that final311.92s report is current. This is container/schema/observation
qualification, with no hydride parameter fit or independent model validation.

## Fire diagnostics, conditional blast and contents-heat verification

Final native-enabled full suites pass552 cases: main SciPy1.18.1 takes124.21s,
compatible1.16.3 takes164.73s. The main run imports its original SciPy before
explicitly adding the separate HyRAM target. An earlier default run without that
target passed530 and skipped22 native-Flame cases; it is not used as evidence that
those cases executed. New cases are24 flame,13 blast,25 inverse heat and18 thermal
data. Ruff/dependency checks pass. The native flat angular-fit covariance warning
and prior native CVODES warnings remain visible; they are not suppressed.

Actual Flame diagnostic verification passes15 gates while physical acceptance
passes only6/9. Four complete visible paths retain failed native caloric,
source-to-field fuel-origin and downstream transport checks under100/300/600
radial points and1e-6/1e-7/1e-8 tolerances. Independent knot-split8/10width
quadratures agree to below1e-12kg/s. The2MPa/2mm source has about45.77% initial
fuel-origin deficit. The actual native density derivative and its own caloric
equation are inconsistent with independently evaluated native functions/EOS.
Default rejection, raw native/result retention and diagnostic-only radiation
are tested. Source energy and radiant-power/kernel checks passing do not close
the whole flame. The replay intentionally returns exit1 and adds no accepted family.

Actual public standalone Bauwens evaluation passes12 gates in each runtime over
729 points. Independent published anchors, energy/pressure scaling, frame/source
identities, zero-energy limit and forward/inverse roots are checked. This uses
explicit participating H2 energy, with no fabricated native Jet/cloud. It does
not qualify source participation, ignition/DDT, waveform/impulse, reflections or
facility distances.

Actual pifira heat inversion agrees with independently prescribed direct-EOS
forward power for normal/para/ortho H2 and two output grids. Maximum interval
power error is below2.4e-9W and contents-U discrepancy below1.5e-10J in the authored
cases. The native Gaussian fit agrees with independent analytic geometry;
temperature scaling, offset/disjoint axial intervals and SI flux conversion pass.
Mass/phase/reference, corrupted-ledger, mask/unit/source and exact clock/window
rejections pass. Contents ΔU/Δt is distinct from incident heat and wall/loss/work.

Final eight-MAT thermal audit verifies10 attachments and all245 vectors/
157964002 scalar elements against the final LF receipt. It retains source clocks,
original vector orientation/index, negative signals, unclocked vectors and151
masked nonphysical temperatures. The final42.42s all-file run supersedes the
earlier same-data audit before receipt LF normalization. No physical clock unit,
time shift, sensor temperature inversion, noise calibration or fire/dose validation
is inferred. Data acquisition totals now268 attachments/4588753807bytes.

## Cryogenic storage, rotor constitutive terms and finite spherical transport

Final main SciPy1.18.1 and compatible1.16.3 full suites each pass629 cases,
with the separately located actual native HyRAM target. Local parallel runtime
is130.60s and130.08s respectively. Source/test/script begin/end bytes match for
all194 Python files. New77 cases comprise20 cryogenic storage,28 rotor terms,
12 shared radial/microsphere and17 fermentation cases. The existing planar
Fourier/trap tests pass through the shared core. Ruff/dependency checks pass.
The existing native angular-fit covariance and CVODES warnings remain visible.

Actual cryogenic replay completes15 native driver integrations:12 accepted
cases and3 deliberately rejected post-run audit regressions, passing18 gates.
Normal/para/ortho warming uses the same EOS/ODE, with separate physical
mass/energy, native PT/Prho inversion, event refinement and positive-floor
budgets. Read-only cross-review found a missing failure object on post-run
exceptions; smooth-ramp endpoint and independent PT/Prho failure regressions
now retain the complete native trace, failing accepted state/time, audited
prefix and original cause. A second review confirmed the correction.

Actual rotor replay passes18 gates. Native cutoff and finite differences
qualify temperature-dependent U/Cv/gap/gap derivative. All24 strict rate points
retain actual frozen single-phase density references with explicit composition
approximations. A generic external driver, not a new library ODE, agrees with
an independent constant-T closed form to3.8e-14 fraction and rotor energy/heat
to4.1e-12J in the authored path. Native92 versus primary90kg/m3 density and
low-ortho/detailed-balance limits remain explicit. An evolving-spin liquid EOS
and a general finite-energy driver remain unimplemented.

The shared spherical replay passes14 gates. Independent series errors reduce
by approximately four under20/40/80 cells, and finite-cavity refinement ratio
is4.00056. Across normal/para charge/release, closed outer wall and prescribed
warming cases, maximum gas/wall/exterior inventory defect is approximately
1.1e-13 of initial gas. Independent actual-EOS pressure-to-inventory inversion
is below6.1e-16 relative error. Prescribed uniform temperature does not establish
a heat duty, stress, glass fit or optical response. These are numerical checks.

The complete fermentation audit consumes830x24 source cells:13980 valid numeric
observations,3893 blanks and2047 source placeholders, with no source formulas
or cache errors. Repeated per-reactor day coordinates and the two row239
component-production discrepancies are preserved. Gas volume reference,
productivity normalization, substrate/COD/biomass and independent replicate
meaning remain unresolved. This is observation qualification, not biological
kinetic fitting or independent validation. Data acquisition totals stay unchanged.

## Spectral production, native gas/solid equilibrium and cyclic separation

Final full suites pass705 cases in both main SciPy1.18.1 (127.44s) and
compatible1.16.3 (126.92s), with the actual separately located native HyRAM
package. All206 Python source/test/script bytes are unchanged across the two
runs. Added76 tests are28 photon,13 multiphase,16 PSA cycle and19 photocatalysis
data cases. Ruff/dependency/whitespace checks pass. Existing native CVODES and
flat-fit covariance warnings remain visible; physical fire rejection is retained.

Photon replay passes14 gates. Independent continuous spectral quadrature and
12/24/48/96-band refinement show the expected second-order approach; finest
H2 rate2.43704536633e-7mol/s differs from the continuous reference by about
1.04e-5 relative. Optical/photon partition, per-band electron/H2 counting,
incident/absorbed yield equivalence, finite reactants and independent actual
native mixture enthalpy are checked. Cross-review found an unbound optical
wavelength grid: the path now retains exact grid/representation identity;
changed wavelengths or lines/bands cannot pass by matching vector length.
New regressions and a second read-only review confirm this correction.

Multiphase replay passes14 gates for five accepted native equilibrium/reference
solves plus retained failure probes. Independent Boudouard extent agrees to
2.22e-16mol, gas-only equal-element TP composition to4.29e-11, and tightened
HP temperature to2.33e-7K. Source/owned thermochemistry, solid density, SI
amount/element/mass and extensive H/U/PV are audited. Chemical-potential KKT
checks apply to stated populated/element thresholds and feasible absent pure
solids. Internal HP trial temperatures are not observable. Native one-step,
zero-carbon candidate HP and completed-but-host-domain failures retain actual
objects/cause; no candidate deletion or automatic alternate solver is used.

PSA replay passes14 gates across actual startup, refinement, closed-valve and
CSS campaigns. The authored two-bed/four-slot model reaches the fixed native
CSS criterion after56 cycles with worst scaled state change7.38884e-5 and
three-cycle streak. Maximum component defect1.03e-15mol and energy defect
7.49e-7J remain within declared budgets. Step refinement changes product
integral by9.74e-8 relative and pressure by0.00984Pa. CSS H2 fraction0.7953
remains below the0.8 feed. Cross-review found native N2 reporting could qualify
host H2 metrics; the H2-specific API now requires actual native H2 reporting
and tests rejection of other species. Original integrator Network/OdeResult
remains unavailable; a separate audit Network is explicitly labeled.

The photocatalysis source audit consumes all37 TXT members twice at different
block sizes with equal canonical identities/values/masks:42856 retained rows,
241264 source cells,196397 finite numbers,35604 blanks,9243 placeholders and
20 categorical cells. Negative numbers, all missing/padded rows, independent
axes, source line/header roles, duplicate members and repeated controls survive.
Specific-rate/AQY views preserve reconstructed origin and reviewed mapping
limits. This is observation qualification, not catalyst or apparatus validation.

Final staging found one trailing whitespace in the multiphase replay script.
Its cleanup preserves the parsed Python AST; all production and test bytes
remain identical to the705-case full suites. The native replay was repeated
with the final script bytes and its source identities regenerated.

## Membrane and staged thermal verification

The native membrane replay checks equal-state zero flux, sign reversal, X/Y
agreement, exact SI conversion, immutable source objects and Darcy contribution.
Its low-pressure sweep keeps the same80nm pore while approaching the independent
Knudsen limit; the lowest-pressure relative error is6.067236e-8. A separate
Darcy-increment defect is2.1684e-19mol/(m2 s). These authored limits do not
qualify pore coefficients or a complete separator. Native polynomial changes
that cannot survive phase reconstruction are deliberately rejected.

Native gas/pure-solid calorimetry is independently reconstructed with native
Mixture H/U/PV and finite-difference Cp. Fit bounds, authored density evidence,
common formation energy and mutable source/provider binding guards are checked.
The staged finite cycle independently reconstructs each heat from fresh native
phase objects, returns carrier amounts and T without resetting them, and
retains water feed plus separate hot H2/O2 takeoff. Its0.1mol authored campaign
requires27105.6185471J net,255159.258069J positive stage heat and228053.639522J
rejection. These are calorimetric accounting results, not feasible operating
points, efficiency or predicted yield. Regression checks cover reused property
buffers, finite arithmetic overflow and accepted-prefix failure retention.

See research/native_membrane_transport.md, research/multiphase_calorimetry.md
and research/thermochemical_cycle.md for actual runtimes, source hashes and
individual gates. Experimental membrane/solid/cycle qualification remains open.

## Final integrated verification profile

Host verification uses two disjoint shards on final immutable inputs:781
non-biological cases plus7 passed/11 optional-native skipped biological cases,
for788 passed/11 skipped in each main SciPy1.18.1 and compatible1.16.3 profile.
The isolated native biological stack executes all18 biological cases; its own
SciPy1.18.1 is not represented as a1.16.3 biological compatibility result.
All218 final Python inputs match the combined shard snapshots. Source native
reports preserve actual versions and before/end hashes. Installed-wheel native
cases and exact archive member/source checks are recorded after the final build
in the excluded research/release_audit.md. These numerical checks do not replace
independent experimental or facility qualification.

## Reproducing the sharded host profiles

Install the reviewed optional providers from DEPENDENCIES and their immutable
receipts first. These commands use existing ignored native targets; unavailable
providers visibly skip and cannot reproduce the recorded executed counts.
In a fresh PowerShell process, run the main profile without prepending another
SciPy target, then run compatibility in a separate process:

```powershell
.venv\Scripts\python -X utf8 -c "import sys, scipy; assert scipy.__version__ == '1.18.1'; sys.path.extend(['artifacts/native_packages', 'artifacts/native_fire_packages', 'artifacts/native_hyram_packages']); import pytest; raise SystemExit(pytest.main(['-q', '--ignore=tests/test_biological.py']))"
$env:PYTHONPATH = (Join-Path $PWD 'artifacts/native_hyram_packages')
.venv\Scripts\python -X utf8 -c "import scipy; assert scipy.__version__ == '1.16.3'; import pytest; raise SystemExit(pytest.main(['-q', '--ignore=tests/test_biological.py']))"
.venv\Scripts\python -X utf8 -m pytest tests/test_biological.py -q
Remove-Item Env:PYTHONPATH
.venv\Scripts\python -X utf8 -m pytest tests/test_biological.py -q
```

Run the actual native biological subset separately using the isolated commands
in NATIVE_BIOLOGICAL_PROCESS.md. Its dependency target must never be prepended
to the two host processes above. The full unsharded pytest command is also
available; sharding here overlaps local computation with disjoint development.

The native18-case biological suite passed54.10s before a one-test Windows
subprocess UTF8 repair. The repaired case then passed separately under the
native profile; parsed-AST comparison proves the other17 cases/fixtures/imports
unchanged. Production source remains identical. The final actual native replay
binds the final source/test/script hashes, rather than presenting the earlier
whole-file test hash as a final-byte full-suite run.

Final native biological replay passes18/18 gates in53.3952s, including actual
positive-throughput finite cases and retained closed/coarse/pressure failures.
COD/C/N maximum defects are1.43162e-9/3.58931e-10/6.44e-19 native-basis kg.
The zero-rate analytic concentration error is2.59e-12kg/m3; tightened-solve
exported-H2 change is1.68645e-6 relative. Actual low dry-H2 export remains a
result, not a purification claim. All host/native begin/end source identities
in research/native_biological_process.md match final files.

## Finite membrane, thermal compression, material observations and uncertainty

First executable family coverage advances52/72 to54/72, about72% to75%:
21 partial implementations,33 checked native adapters and18 planned families.
The uncertain full-programme effort estimate remains30-40%. Actual finite
thermal compression and native independent-input uncertainty add two families.
Finite two-side membrane composition deepens the existing transport family;
material observation qualification does not create a fracture-law family.

Both unsharded host profiles pass870 cases with11 explicit optional-native
biological skips: main SciPy1.18.1,216.34s; compatible1.16.3,216.22s. Added82
cases cover17 finite-membrane,18 compressor,13 material-profile and34 uncertainty
checks. All230 Python source/test/script inputs remain unchanged across both
full runs and equal the final source snapshots. Previously executed isolated
biological cases are not presented as newly run by these optional skips.

Finite membrane replay passes17 gates: native two-side species/U/H/thermostat
ledgers, independent hook units/area, reversal/refinement and finite Knudsen
limit. Maximum side energy defect is3.842e-12J. The same prescribed T is explicit;
raw native numerical extensions, sampled admission and hidden native internal
steps differ. An inventory rejection is not an exact stopping-root prediction.

Finite compression replay passes20 gates in105.044s. It admits
0.00144023053kg and delivers0.00105626799kg
above evolving finite source pressure; maximum total-H2 defect is
6.93889e-18kg and total-U defect2.69836e-10J.
Final solid loading0.0948648585 differs from initial0.01 despite
returning to300.000064K. Startup inventory, non-CSS
loading and finite bath/thermal duties remain visible. Shared closed-bed and
microsphere replays pass again after the rate-core extraction; their current
source identities are refreshed. No native EOS/kinetics/tank/nozzle is duplicated.

Uncertainty replay passes13 gates in each native SciPy profile,37.8503/34.4667s.
Actual normal-H2 inventory QMC mean/variance defects versus independent tensor
quadrature are6.19e-9/1.62e-6relative. Independent seed/base2 index change is
3.24e-5. Input distributions and independence are authored. Coordinate mutation
and invalid-returned-raw retention defects found in review have regressions;
native1x1 shape failure, constant variance and numerical overflow/underflow stay
distinct. No measured law/covariance, facility frequency or model validation
is inferred from numerical statistical convergence.

All9 acquired austenitic compilation attachments are qualified, including
113condition/property records, five properties,31linked composition rows and
102mappings. Forty elemental disagreements remain separate;103absolute pairs
and10ratio-only records preserve source roles. Pressure/purity/strain definitions
and specimen/study dependence remain unresolved where source evidence is missing.
Acquisition totals stay268 files/4,588,753,807bytes. Request020 specifies receiving
capabilities. Full experimental, remaining model-level and facility/accident
qualification keeps the original programme active; no remote publication occurred.

The full runs use the reviewed native targets already described above:

```powershell
.venv\Scripts\python -X utf8 -c "import sys, scipy; assert scipy.__version__ == '1.18.1'; sys.path.extend(['artifacts/native_packages', 'artifacts/native_fire_packages', 'artifacts/native_hyram_packages']); import pytest; raise SystemExit(pytest.main(['-q']))"
$env:PYTHONPATH = (Join-Path $PWD 'artifacts/native_hyram_packages')
.venv\Scripts\python -X utf8 -c "import sys, scipy; assert scipy.__version__ == '1.16.3'; sys.path.extend(['artifacts/native_packages', 'artifacts/native_fire_packages']); import pytest; raise SystemExit(pytest.main(['-q']))"
Remove-Item Env:PYTHONPATH
```

Missing optional providers produce explicit skips and cannot reproduce the
recorded execution counts. Statistical and physical native cases retain their
actual source identities, inputs, failure objects and limitations. Installed
wheel/source archive content and actual installed-native replay are checked
after the final build and recorded in excluded research/release_audit.md.

## Native wave, supplied-exposure and conditional-risk checkpoint — 2026-10-28

First executable coverage advances54/72 to57/72, about79%:21 partial implemented
families,36 checked native-adapter first levels and15 still planned. The uncertain
full-programme effort estimate remains30-40%. Independent calibration/experiments,
remaining physics and a qualified full facility accident chain are incomplete.

Both unsharded host profiles pass970 cases with11 explicit optional biological
skips: main SciPy1.18.1 in258.49s and compatible SciPy1.16.3
in258.57s (NumPy2.5.4). All242 final Python source/test/script
fingerprints match at run start/end and current source. Skips are not newly
executed biological evidence; the previous isolated native biological record
remains separately scoped. Native Sundials warnings in deliberately difficult
existing event cases remain in the ignored logs, not silently rewritten results.

Actual native HyRAM supplied-field exposure passes22 gates; SDToolbox/Cantera
CJ/frozen-shock replay passes18; native conditional-risk composition passes15
in both numerical profiles. These establish the stated numerical/API boundaries,
not experimental harm calibration, a source-to-field chain or total-facility QRA.
A replaced cached native probability/model is rejected by the exposure owner's
replay; absent/invalid source state is rejected before conditional risk.

A real simultaneous native YAML bridge reproduces an initial global cleanup
assertion failure. Verification factories now use separate ASCII UUID workspaces,
and a real two-owner regression checks that one open bridge does not invalidate
another owner's cleanup. Production native wave algorithms are unchanged. The
initial failed main run and its full passing compatible peer remain in ignored
logs; the two final runs above execute the corrected frozen inputs.

All42 acquired ELVHYS assets (38 recorder signals) and534609893bytes are
hash-verified. Complete scan:4886225 rows,48526984 finite numeric cells,
48034198 valid and492786 invalid T2e dummy cells, with27 duplicate/nonincreasing
temperature clocks retained. BLEVE/membrane-rupture observations lack homogeneous
premixed initial-state/CJ-speed evidence; direct CJ validation is inadmissible.
Pressure-reference, sampling and synchronization conflicts remain explicit.
Overall acquisition stays268attachments/4588753807bytes; no new raw data
were needed for this checkpoint.

Exact inputs, native raw objects/diagnostics, acceptance and limits are in
research/native_exposure.md, native_detonation.md, conditional_risk.md and
shock_tube_data.md. Request021 specifies source data/native state/search,
calibration and direct risk-object capabilities for receiving projects. No
receiving repository was edited and no publication occurred.


Each model has separate acceptance: restricted ideal-gas CJ/shock jump and sonic
conditions; actual native exposure and independent integration/CDF checks;
explicit single-LOC risk product and credit/source/receptor integrity; complete
raw-data qualification with no repaired clocks or pressure-reference guesses.
The existing rejected HyRAM source-to-Flame mass/caloric chain stays rejected.
Wheel/source archives and actual installed-native/full-data execution are the
final deployment check; see the post-build research/release_audit.md.

## Finite O2, ordinary-air thermal state, monitoring and new enclosure data — 2026-10-28

First executable coverage advances57/72 to59/72, about82%:21 partial implemented
families,38 checked native-adapter first levels and13 planned families. O2 and
ordinary-air thermal state are distinct portions of effects.cryogenic, counted
once. Native learned residual monitoring adds the other first level. Full-programme
effort remains an uncertain30-40%; independent validation, remaining physics
and the accepted full facility/accident chain are incomplete.

The two unsharded final profiles each pass1088 cases with11 explicit optional
biological skips: NumPy2.5.4/mainSciPy1.18.1 in306.49s and compatible
SciPy1.16.3 in306.49s. All255 final Python source/test/script hashes
match at start/end and current source. Biological skips are not new execution
evidence. Existing native difficult-event warnings and the inverse-fit warning
remain in ignored logs. They do not turn a rejected physical case into a result.

Actual native O2/thermal/monitoring replays pass23/15/18 gates in both profiles.
The source-specific new data tests pass18cases. Native O2 source/room/nozzle
and caloric references, actual source partitions and U/species/pressure ledgers
are retained. Owner-built results are verified against original native traces
before criteria use their summaries; replaced O2/clock/context records reject.
Native JOS3 owns17segments/85nodes; actual implicit heat storage/rounding and
10/5/2.5s refinement pass within the declared ordinary-air/nonfreezing domain.
Integer-microsecond stepping rejects nonadvancing absolute clocks before execution.
The native global shivering limiter and unsupported custom heat boundaries remain
out of scope. Native learned causal PCA/mode models retain independent whole-run
fitting/calibration/evaluation and native trained state; method/signal rebinding
is rejected. Scores do not identify faults, trigger controls or infer annual risk.

New ELVHYS4.2v1.1 acquisition is198/198assets/1429209739bytes, zero omissions.
Complete195CSV audit covers40actual versus48nominal cases,8150693rows and
89332905sourcecells:85607986finite numeric,72078446ingestion-valid and
17254459masked. All source/MD5/SHA/metadata/receipt/code and alternate-block
checks pass in195.0913613s. These correlated cells are not independent experiments.
No O2 time history or qualified H2 mass release is supplied. Source-normalized/
delay-aligned H2, unresolved clocks/sensor roles/locations and invalid27/28 stay
explicit. The separate Dryad O2 discovery has two HTTP401 attachments and zero
acquired observations. Overall28collections have466successful attachments/
6017963546bytes,25collections with acquired files.

A separately reproduced original SLABx-LH2 diagnostic has positive O2 condensate
with4.3197363% excess remaining-gas saturation and different feed/gas H2 bases.
Its7negative-evidence gates retain the original failure; no host phase repair,
new accepted family or O2/source/dispersion qualification is inferred. Existing
preferred-provider failed physical premises remain rejected.

Current detailed contracts and evidence are OXYGEN_DEFICIENCY.md, JOS3_THERMAL.md,
PROCESS_MONITORING.md, OXYGEN_OBSERVATION_DATA.md and their research reports.
Request022 states native/source-data receiving changes. No receiving repository
was modified and no publication was performed. The full goal remains active.


Independent numerical oracles include finite oxygen exponential displacement,
O2 elemental/material and ideal-gas pressure identities, caloric closure,
sampled crossing refinement, native thermal capacity/implicit heat balance with
an explicit output-precision bound, and native trained PCA covariance/calibration/
causal reset behavior. Raw processed experimental data qualification is separate
from all those authored checks. No measured fault/human injury/cold-room field
validation or full qualified physical source-to-risk path is claimed.

## Parallel coding priority; deferred validation — 2026-10-28

The latest user direction supersedes the earlier local-testing workflow: code
models in parallel and run tests later after connecting Nurion. No additional
local pytest, native simulation/replay, benchmark, example or scientific case
execution was performed for the new wave. Only static syntax/lint/TOML/source
and licensing inspection supported development. No scheduler job was submitted.

Three model families now have implemented_unverified source: native PV/directDC
nonlinear electrolysis coupling and finite production/receiver inventory;
actual HELPR hydrogen/Paris constitutive laws with SI mode-I geometry and finite
cycle/events; and shared-kernel finite solid decomposition/hydrolysis with
finite supplies, prescribed takeoff and thermal endpoints. No duplicate PV,
growth, fugacity, reaction or EOS solver was introduced. Their original objects,
raw return/failure evidence and unresolved scopes are in their manuals/development
records. Native API inspection and written cases are not runtime acceptance.

The new increment has22 deferred scientific cases:9PV,4fracture and9solid,
including separate native-caloric solid coverage. Python cases/parameters/outcomes
and an unsubmitted PBS array generator are implemented. The helper and scheduler
integration are themselves unexecuted. Actual cluster paths, native Linux
environments, queue/account/resources and source/plan revision are future inputs;
no credentials or connection are assumed.

Coding inventory:62/72 (about86%) including3unverified; last actually executed
first-level evidence:59/72 (about82%),1088passes/11optional biological skips in
each recorded profile at6eae06c. Full-programme effort remains an uncertain30-40%
with independent validation and a qualified full accident chain unfinished.
Historical source hashes for6eae06c are retained in research/checkpoints/6eae06c.toml.
The current parallel_checkpoint.toml records static development bytes only;
it must not be read as a fresh test pass. The preceding6eae06c build also has
post-build content/installed checks deferred, and the last fully inspected
installed-artifact checkpoint remains785dae7.

## Alarm-linked finite-stroke valve execution

The deferred case `concentration-alarm-finite-stroke-valve-actuation-trace`
composes confirmed synthetic concentration-alarm evidence, the explicit
alarm-to-isolation schedule and the existing finite-stroke valve model. Its
contract checks preservation of alarm and trace identity, exact clock and
sensor-location applicability, sample-grid coverage of command boundaries and
the schedule horizon, and rejection of mismatched clock/location/grid inputs.
The actuator trace remains the output of `FiniteStrokeValve`; the adapter adds
no motion or flow equations. AST parsing and Ruff checks passed for the new
adapter and deferred case. This case has not been executed locally or remotely.
Its authored actuator inputs are synthetic and unqualified, so the case cannot
support detector credit, valve qualification, flow safety, SIS performance or
facility risk claims.


## 2026-11-01 exact-grid and actuator contracts

The following Hangang metadata cases are registered under the refreshed plan and source manifest, but remain unexecuted because the corrected array was refused by QOS and had no job ID:

- preferred-dispersion-receptor-alarm-contract
- preferred-dispersion-exact-receptor-grid-contract
- concentration-alarm-finite-stroke-valve-actuation-trace

They are software/API contracts. The exact-grid case checks declarations for exact sampling with explicit coordinates; it does not verify a provider's internal grid extraction. The actuator case composes existing alarm and finite-stroke models; it does not establish online SIS response or safety credit. Their first PBS campaign was generated from the pinned tree; the rejected submit is not a failed model result.

## Newly registered composition contracts — 2026-11-01

- `two-vent-hydrogen-layer-concentration-alarm-handoff` — synthetic bridge from reduced upper-layer H2 to existing sensor/alarm models; no detector qualification or protection credit.
- `pem-ripple-iv-to-hydrogen-stack-diagnostic` — synthetic source/lineage bridge using the acquired CC BY 4.0 PEM ZIP; requires staging that raw archive on Hangang and does not qualify the electrochemical model.
- `preferred-gas-dispersion-hyram-ignition-risk-ledger` — synthetic HyRAM source-rate consistency handoff to an existing risk branch; it calculates no risk metric and does not claim SLABx-LH2 ignition-table applicability.

All three are registered but unexecuted. The current source revision needs a refreshed immutable snapshot; only the earlier priority 2–7 pin has remote manifest-verification evidence.
