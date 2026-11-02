# Jet-fire common-reference conservation investigation

2026-10-28. Code status: **implemented_unverified diagnostic only**. The physical
jet-fire family remains **planned/rejected**, with zero accepted coverage
increase. The current user instruction defers scientific execution until a
later Nurion connection. No native/project model import, calculation, example,
case discovery/invocation, installation, pytest, replay, benchmark or job was
performed for this increment. Static source/API/license inspection, primary
web reading, AST, Ruff and file-byte checks are the only new evidence.

Owned files are the new adapter, `docs/JET_FIRE_CONSERVATION.md`, this report,
the authored example, six-case deferred catalog and optional dependency receipt.
Original `hyram_flame.py`, other shared sources/docs/catalogs, requirements and
all native/external repositories remain unchanged.

## Actual failed baseline and API findings

The existing `research/native_jet_fire.md` records four actual prior HyRAM6.1
solves. At its 2MPa/300K/2mm source, native nozzle flow was about
0.00309567kg/s while reacting Gaussian entry carried about0.00167863kg/s;
the finest visible endpoint carried about0.00203151kg/s. Those are **previous
executed diagnostic observations**, not computations from this lane. Independent
radial quadrature had already separated the approximately45.77% initial
source/field gap from numerical tails. Its density derivative, direct-EOS
caloric and downstream fuel-origin gates also failed. Prior source stagnation
and emitted-radiant-power identities passed; these did not accept the flame.

Actual installed source inspection confirms:

- `Flame.from_developed_flow(..., chem=...)` is public, but its initial node
  still originates in nonreacting `PlugNode.establish`. Reusing an actual
  developing flow saves native work; it does not establish a conservative
  reacting inlet. Editing its width after a failed solve would be a field
  modification, not evidence of a fixed native model.
- `Combustion` stores pressure as `Preac`; `Flame.solve` and `length` inspect
  `chem.P`. The broad exception path can construct default chemistry. A custom
  chemistry object must not be presumed active merely because it was passed.
- Density uses the native temperature interpolation while its derivative is
  separately approximated. The old recorded derivative/caloric inconsistencies
  remain unresolved. Native mixture calorics also require an explicit mass/
  molar and formation/sensible reference contract.
- `Flame.solve` does not retain the original SciPy `OdeResult`; its returned
  arrays do not expose all solver status/trials. Radiation uses a postprocessed
  native emitted-power correlation and multisource kernel, with no matching
  cooling sink in a solved flame energy equation.

No public native capability inspected here supplies all missing conservative
reacting establishment, consistent chemistry and radiating energy premises.
No subclass override, monkeypatch, altered chemistry table, profile scaling,
normalization, synthetic Jet, duplicated ODE or replacement nozzle was used.

## New diagnostic composition

`HyRAMFlameConservation` consumes the original typed actual native Flame result
and shared `CanteraMolarEnthalpy`. It audits explicitly selected original
stations, including entry and the full visible endpoint. Total/species/element
mass, fuel-origin f, common formation-reference enthalpy and kinetic power are
independently integrated from actual native Gaussian parameters, temperature,
density and product fractions. Fine/coarse and finite radial-cutoff differences
remain separate from physical source/transport failures. Fractions are not
renormalized and temperature/pressure fit excursions retain their cause/prefix.

The common caloric coordinate subtracts the native chemistry model's ambient
surrogate enthalpy from every unit mass. It compares field entry with the actual
native expanded pure-H2 T/v/nozzle-flow on that declared reference. Native
source/expansion calculations are not replaced or choked a second time. It is
not proof of equality between normal-H2 CoolProp and mechanism-spin-unresolved
NASA gas thermodynamics. Ambient O2/N2 surrogate and caloric/spin assumptions
have mandatory interpretation evidence. No real-gas/formation-zero conversion
or fit is silently invented.

The visible-domain diagnostic adds actual emitted native radiation once to
outgoing-minus-incoming excess enthalpy/kinetic flux. Native formation enthalpy
already accounts for chemistry; LHV is not added a second time. A one-mole
complete H2/O2->H2O reference conversion/heat reuses the existing shared reaction
core and is retained separately from the native flame law.

Required signed fuel/air/element terms are diagnostic interpretations, not
supplied corrective sources. For each element the result records the energy-
reference sensitivity coefficient Delta(element flux)-Delta(total mass flux)*
ambient element fraction. This explains why an energy discrepancy can depend
on the chosen elemental enthalpy reference when material does not close. A
convenient energy zero cannot make it a physically identified heat source.
`required_heat_input_w` stays None. Gravity, lateral enthalpy, pressure/flow
work and radiative cooling are not resolved by this bookkeeping.

Held-steady window integrals use the original finite clock/premise; there is
no transient source/inventory, ignition, blowdown or transit model. Original
HyRAM source gates remain available and are not weakened or overwritten.
The new result's accepted property is always false. Its explicit rejection
retains the actual native flame and original diagnostic result.

Existing `HyRAMFlameRun.irradiance` remains the only radiation runner. Binding
an existing native result checks that it belongs to the same flame, that its
raw native values match its cached flux and that the conservation diagnostic
is the owner's original unchanged result. A cloned cache is rejected. The
result retains the original radiation object and stays unaccepted even if
the native radiation kernel gates pass. Incident scalar irradiance is not
absorbed or signed equipment heat.

Caloric provider/phase definitions, methods including bound owner, atomic data,
reference reaction/conversion, scope and original native fields are guarded.
The runtime native signature includes object ownership and is intentionally
process-local; it is separate from portable source/mechanism SHA256 receipts.
Actual native source fields are never modified by the diagnostic. The dedicated
caloric phase does change T/P during native property calls. These guards preserve
result correspondence and are not a security boundary against deliberate
private-state tampering.

## Concrete native receiving contract

The following is a requested native interface contract, **not an existing or
implemented public Python API**:

1. A retained actual native nozzle/expanded-source object plus an explicit
   plane/state/clock/frame/reference record must define species/element mass,
   momentum including pressure thrust where applicable, and total enthalpy/
   kinetic targets. A shared-nozzle alternative must be a distinct source owner,
   with no second choking solve or hidden flow replacement.
2. A native reacting-establishment operation must solve its profile unknowns
   against those actual targets and declared entrainment/chemistry hypotheses.
   Return native trial/root status and individual residuals. Reject unavailable
   closure; do not multiply a failed final profile by an inferred factor.
3. A documented native chemistry Protocol must expose absolute pressure,
   temperatures, species/molar masses, formation/reference/spin basis, f's
   conserved fuel-origin meaning, property and derivative evaluations, exact
   fit bounds, interpolation errors and original owned native objects. Supplied
   chemistry identity must remain visible; a metadata mismatch must fail rather
   than recreate a default chemistry object through an exception path.
4. The property/density derivative must be consistent with the actual state
   function, with explicit one-sided treatment at stoichiometric kinks and
   holdout direct-EOS checks. Grid/chemistry refinement must preserve source,
   element and energy budgets independently of radial integration errors.
5. Return original native `OdeResult`/events/status/trials and separate signed
   lateral material/enthalpy, work, gravitational and radiative terms. Expose
   adiabatic-geometry/postprocessed-radiation mode separately from a genuinely
   radiating energy equation. Any approximation requires a declared error and
   validation scope; its omitted radiation sink is not a closed energy solution.
6. Keep actual multisource radiation/emitter/transmission/receiver semantics,
   and rerun all existing strict native source/mass/caloric gates after a
   reviewed revision. Empirical radiation qualification, absorbed heat and
   transient finite equipment response remain additional boundaries.

This contract extends the evidence underlying request016. The parent owns any
shared request/catalog integration; no receiving project was edited or contacted.

## Native provenance and deferred cases

No dependency was installed. Actual HyRAM6.1 remains separately installed under
GPL-3.0-only, with its unchanged native Python tree digest
d5865e1ae7b5c77b985e06b45d7a5607543703c1834fc50f7c5d96f32a0c22de.
The optional receipt rechecks native source/license/metadata and existing shared
provider bytes. Cantera3.2.0 remains BSD-3-Clause. The example selects actual
native species through its installed `nasa_gas.yaml`, SHA256
4de6199d65d2d3db782e30573720c723130953707336add59713b02d8667e4db.
No NASA data, coefficients, native implementation or mechanism is bundled.

The installed file attributes its data to NASA-TM-4513. The authoritative
[NTRS record](https://ntrs.nasa.gov/citations/19940013151) identifies public
distribution and permitted public use of that US-government work. The five
selected native species have200–6000K fits. This avoids silently extending the
installed GRI N2 fit, whose lower bound is300K, for cold diagnostic source states.
The new 500K-source/310K-ambient example is an authored domain fixture, not a
repaired300K baseline. If actual expanded states or native APIs violate the
declared domain, the future run must fail with its original evidence.

Six metadata definitions use profile **jet-fire-conservation**:

| Deferred definition | Intended future diagnostic gate, not an executed result |
| --- | --- |
| jet-conservation-rejection | Prior300K failed baseline retained; new warm-field values/gates unchanged; common-reference reaction retained |
| jet-conservation-quadrature | Native selected-section mass/element/energy order and8/10-width tail checks |
| jet-conservation-domain | Declared caloric-domain failure retains original native source and cause |
| jet-conservation-binding | Caloric method/owner and changed source-cache rejection |
| jet-conservation-radiation | Actual original native radiation remains diagnostic; changed conservation cache rejected |
| jet-conservation-energy | Formation/reference/kinetic/radiation identity, finite steady budget and refusal to identify missing heat or accept the flame |

The profile reuses the existing isolated HyRAM/SciPy1.16.3 environment plus
Cantera3.2.0/CoolProp8 and host NumPy/SciPy. Actual Nurion versions, runtimes,
fit domains, tolerance budgets and native results remain unexecuted. `cases()`
was not called locally. AST counted six literal definitions, and AST/Ruff passed
for the three Python files. LF and receipt hashes were checked statically.
No scientific runtime or passing-test count is assigned.

Primary references: [official HyRAM+](https://hyram.sandia.gov/),
[official source](https://github.com/sandialabs/hyram),
[native technical reference](https://doi.org/10.2172/2563814),
[Cantera thermodynamics](https://cantera.org/3.2/python/thermo.html), and
[NASA-TM-4513](https://ntrs.nasa.gov/citations/19940013151). No secondary table,
vendor data or unqualified experimental calibration was used.

## Static input freeze

Before this lane all six owned paths were absent. Source/native file hashes
were read before and after static work; the original failed adapter and native
bytes remain unchanged. Final input hashes follow. This report's own hash is
sent separately after writing it.

| Host input | Final SHA256 |
| --- | --- |
| src/h2physics/adapters/hyram_flame_conservation.py | `971b222fc85113eab24d04e82ced539731d9fda671023f0fa69cf5a796f24e9f` |
| examples/jet_fire_conservation.py | `0f461822c16397f232bf7605093fcc321a4d955e65ab5b6dbabe71d9a69cf79b` |
| validation/cases/jet_fire_conservation.py | `e7c123f95621417255418fd475f63797539686cb711ee53562b61c8be3bad686` |
| docs/JET_FIRE_CONSERVATION.md | `3ac73fc3f68f8f902fd5c3bfaa48d02303f9b732829875aa79c73054003c3dcc` |
| research/jet_fire_conservation_dependency.toml | `117646b94f400e3554c02642c0f6eab9ba2f6bb7cf61716409753abaa53df86b` |

Original `hyram_flame.py` remains
3bd001f56174fccbfca6ca5ec2a882af3ffb45b656fae0f9f496b5670e7dae39.
This increment supplies better unresolved-boundary evidence. It does not fix
or approve the source flame, add an accepted first level or complete jet fire.
