# Finite oxygen displacement and explicit exposure criteria

`h2physics.adapters.oxygen_deficiency` composes the existing
`CanteraOpenGasVolume` with actual finite `IntervalMassSource` inputs. Cantera3.2
owns the ideal-gas EOS, species/caloric properties, finite mass/species/temperature
equations and integration. This level calculates homogeneous O2 inventory,
ventilation/recovery and pressure/temperature feedback. It provides no human
response probability, frostbite, respiratory injury, cold-contact model or
cryogenic gas/solid/liquid mixture EOS.

## Native inputs and Python composition

Create a fresh native frozen `ct.Solution` factory with actual O2 and the needed
neutral species, zero reactions and source-reviewed thermochemistry.
`MechanismBasis` declares mechanism source SHA, rights, references and an admitted
T/P envelope; the actual native species fit range is also enforced. Read installed
YAML as unmodified text using Python when the native Windows parser cannot open
the Unicode path. No mechanism or coefficient table is bundled.

```python
from h2physics.adapters.oxygen_deficiency import (
    CanteraOxygenRoom, OxygenFeedAdmission, OxygenRoomRegion, OxygenRoomSettings,
)
from h2physics.core import Origin

region = OxygenRoomRegion(
    region_id="finite-room", receptor_id="declared-homogeneous-receptor",
    frame_id="facility-xyz", clock_id="operation-clock",
    position_m=(1.0, 0.0, 1.5), elevation_m=0.0, volume_m3=1.0,
    mixing_evidence_id="caller-evidenced-complete-mixing",
    single_gas_evidence_id="caller-evidenced-warm-single-gas",
    prescribed_transfer_evidence_id="explicit-feed-and-fan-boundaries",
    origin=Origin.SYNTHETIC,
)
# phase_factory, mechanism_basis and initial are actual previously admitted
# native factory/basis/ReactiveState objects, not a JSON/server contract.
model = CanteraOxygenRoom(phase_factory, mechanism_basis, region)
admission = OxygenFeedAdmission(
    source=finite_source, properties=actual_frozen_native_properties,
    admission_evidence_id="same-native-state-and-caloric-reference",
    outside_support_evidence_id="declared-isolation-through-output-window",
)
result = model.run(
    initial, [100.0, 100.5, 101.0], feeds=(admission,),
    exhausts=actual_shared_gas_vents, heat_boundaries=actual_shared_wall_boundaries,
    settings=OxygenRoomSettings(maximum_time_step_s=0.05),
)
reactor = result.native[0].reactor
network = result.native[0].network
original_source = result.feeds[0].source
```

The source is an actual `IntervalMassSource`, with its original `SourceLocation`,
absolute clock/frame, finite bin masses, termination and `ThermoState`. Its actual
`CanteraFrozenGasProperties` object must identify the same complete native phase
and `MechanismBasis` as the volume. Basis, composition fingerprint, spin identity,
T/P, density, h/u and entropy are checked. No arbitrary CoolProp sensible zero,
para/normal-H2 relabel, source warming or formation-reference offset is inferred.
Only a gas phase with resolved vapor fraction1 is admitted. A source at20K cannot
be admitted by lowering a declared fit bound. The replay uses actual installed
H2/O2/N2/H2O fits in an authored warm300–1000K,50–500kPa envelope.

The admission evidence must also justify a reservoir-enthalpy inlet with negligible
kinetic energy at that boundary. `IntervalMassSource` has no velocity/kinetic-energy
channel; a nozzle-plane static enthalpy is insufficient when unresolved kinetic
energy enters the room. No automatic jet thermalization or momentum dissipation is
assumed. Native ideal-gas `phase_of_matter` and fit admission do not establish
multiphase stability: exclusion of water/air condensation remains the explicit
single-gas application premise, independently of a successful native gas call.

`OxygenFeedAdmission.outside_support_evidence_id` is required when the output
window extends before or after the source support. A `window_end` source still
cannot become zero after its unobserved tail. Declared isolation/depletion and
explicit zero-extension evidence allow a finite source to stop while the room
continues evolving. No source mass is added beyond its bins.

Exhausts are the existing actual `GasVent` objects and stationary heat boundaries
are the existing `GasHeatBoundary` objects. These native MassFlowControllers are
prescribed transfers; positive orientation is not a passive pressure-flow law or
a qualified fan. The caller's transfer evidence must supply that physical boundary.
A live callback can use the existing shared nozzle for pressure-driven extraction;
the replay executes that composition on an independently owned native property
phase, with evolving room pressure and composition. No new choking/EOS equation
is implemented. Boundary clocks must cover the whole physical output window.

## Interval commands and clocks

The wrapper partitions the existing native driver at every source edge and
explicit `event_times_s` entry. Each source bin retains its known constant mean
kg/s representation. It does not reconstruct sub-bin variability. Physical state
is restarted from the actual preceding native endpoint; mass/species/U/H/Q
ledgers are accumulated across the independent native partitions. Command edges
are added to the returned output grid and `requested_time_s` remains separate.

Native trial calls can extend beyond a partition endpoint. A source rate remains
frozen within that partition's numerical extension; exhaust/wall callback times
are held at its endpoint left limit. The next partition uses the right-side
command. Only the declared physical interval is integrated into source/energy
accounting. The actual native evaluated-clock ranges survive in every raw trace.
No claim is made that every internal trial is a finite-difference probe or an
accepted physical state. Time-varying exhaust or wall discontinuities must be
declared through `event_times_s`; no automatic event detection is supplied.

## Quantities, references and audits

`OxygenRoomResult` retains each actual `GasVolumeTrace`, native reactor/network,
feed/exhaust/environment reservoirs, flow devices, walls, source property phases
and original feed objects. Its explicit source hashes and native source/owned
fingerprints tie the summaries to admitted inputs. Source/provider mutation during
a physical batch is rejected before a result can be returned.

- `species_inventory_kg`, `oxygen_inventory_kg` and `oxygen_inventory_mol` are
  finite inventories. Native kg/kmol molecular weights are converted explicitly.
- `wet_oxygen_mole_fraction` is actual gas-phase X_O2. It is distinct from Y_O2.
- `dry_oxygen_mole_fraction` removes actual gas-phase H2O from the mole denominator.
  Pure-water gas has an invalid dry denominator, represented as NaN with
  `dry_fraction_valid=False`. It is not filled with zero.
- `oxygen_partial_pressure_pa` is wet X_O2 times native absolute gas pressure.
  Dry X_O2 is never multiplied by total wet pressure. This is ambient ideal-gas
  partial pressure, not inspired humidified, alveolar or arterial pressure.
- Cumulative source, exhaust, species, inlet/outlet enthalpy and wall heat integrals
  retain native units converted to SI. Signed U-H-Q residuals, source bin mass and
  native caloric admission, every species and total mass are audited independently.
  A separate ideal inventory P identity checks species-mole/unit/volume meaning.

A fixed-V,T sealed H2 addition lowers X_O2 while leaving O2 moles and pO2 fixed.
The native replay includes the required negative thermostat heat. Thus a chosen
mole-fraction screen is not itself a physiological hypoxia calculation. An actual
matched-molar replacement fixture instead preserves T/P and yields the independent
well-mixed exponential O2 depletion and fresh-air recovery limits.

The declared complete-mixing assumption maps one physical region to a receptor;
it does not resolve buoyancy, stratification or a breathing-height plume. An H2
concentration alone determines O2 only under an independently admitted unchanged-air,
no-reaction/no-condensation and humidity basis. No such inference is automatic.

## Criteria and sampled crossings

`OxygenCriterion` requires the exact wet/dry mole fraction or ambient pO2 quantity,
fraction/Pa threshold, low-side comparator, pressure/elevation domain, authority
reference and applicability evidence. Nothing is selected implicitly.
`evaluate_oxygen_criterion(result, criterion,
interpolation="linear_between_native_output_samples")` reports sample flags/minima,
crossing brackets, linear crossing estimates and the deficit duration of that
explicit interpolant. It does not report native event roots, hidden accepted
steps, unsampled extrema, an exposure beyond support or a physiological dose.
Output-time refinement is required to assess reconstruction error.

`integrate_oxygen_threshold_deficit(screen)` reports the exact positive-part
integral of `max(threshold - selected_oxygen_value(t), 0)` over the screen's
piecewise-linear reconstruction. It retains one contribution per sampled
interval and the total. Mole-fraction criteria yield fraction·s; oxygen partial
pressure criteria yield Pa·s. A crossing contributes only the triangular part
below the threshold. This is a threshold-deficit metric; it is not a physiological
dose, injury probability or harm-response law. The owner-issued screen, selected
quantity, criterion domain and exact window are revalidated before use. Its
deferred Nurion case checks the analytic interval integration without integrating
a room or selecting a new criterion. Implementation pairs adjacent samples as
`(t[i], t[i+1], y[i], y[i+1])`, producing exactly one contribution for each of
the `n-1` intervals from `n` retained samples; the endpoints are neither
extrapolated nor treated as additional intervals.

The evaluator also accepts `sampled_window_s=(start_s, end_s)` to report only a
selected portion of the retained output. Both endpoints must exactly match distinct
native output times in increasing order and remain inside the simulated interval;
the window selector does not interpolate or extrapolate its edges. Deficit duration
inside the selected span still uses the declared piecewise-linear reconstruction.
`OxygenCriterionResult.sampled_times_s` retains the exact samples used for the
minimum and deficit flags. Omitting the argument selects the complete output span. The deferred
`oxygen-criterion-exact-sample-window` contract checks exact selection and rejection
of off-grid, reversed and out-of-range windows; it does not run a room integration.

The criterion consumer first revalidates the current criterion fields and calls
`verify_oxygen_room_result(result)`. This public verification function returns the
same supplied result object when it matches the actual retained native traces.
It checks the flattened original snapshot identities, native clock/phase/basis,
output times, wet/dry O2, partial pressure and finite O2 inventories. An owner-built
in-process binding also preserves the original region/receptor/frame, requested
clock, source/context and summary contents. Its constructor consumes a one-use token
created only after `CanteraOxygenRoom.run()` completes, so a caller cannot attach a
self-computed signature to a fabricated wrapper around native traces. Dataclass
`__post_init__` and `dataclasses.replace` never refresh the binding. Replacing a cached
wet fraction with zeros, changing a clock/frame, forging a binding, or attaching
cloned snapshots therefore raises `OxygenResultVerificationError`, retaining the
offending result, actual native traces and cause. Verification does not integrate
the physical ODE again. It is an object-correspondence guard, not a portable digital
signature or a claim of authenticity for deliberately fabricated private records.

OSHA's below19.5% by-volume definition is an occupational respiratory-protection
criterion with specific altitude/respirator provisions. It is not a fatality curve.
The official interpretation discusses partial pressure and acclimatization.
([OSHA1910.134](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.134),
[April2,2007 interpretation](https://www.osha.gov/laws-regs/standardinterpretations/2007-04-02-0))
Washington's sea-level volume/partial-pressure rule has its own elevation/site
qualifications; it is not an interchangeable universal physiological threshold.
([WAC296-62-135](https://app.leg.wa.gov/wac/default.aspx?cite=296-62-135))
Jurisdiction, atmospheric basis, elevation and individual/work circumstances remain
caller evidence. `probability` is always None; criteria cannot be passed as a native
HyRAM human-response probability or a completed annual risk calculation.

## Failures, evidence and remaining cold boundary

`OxygenRoomError` retains original feeds/region, completed native command traces,
actual failing native objects, native phase state/network time and original cause.
A case-wide fresh-phase guard prevents source/template/prior-partition aliasing;
`native_phases` also retains factory outputs when admission fails before a reactor
or network exists. All retained factory definitions are checked between partitions.
A post-run audit error also retains `completed_result`. The shared native driver
does not expose output prefixes within a failed partition or the first hidden
failing trial. `completed_traces` means completed partitions; `failure_time_s` is
the retained network time after the failed attempt, which can differ from trial
or requested-output times. No inaccessible steps are labeled accepted observations.

Run `python scripts/check_oxygen_deficiency.py` and the scoped test module. The replay
records actual native/analytic limits, refinement, signed trial corrections in the
nozzle coupling, original failures, local timing and begin/end host/test/script/docs,
mechanism/native-binary/license hashes. The research report is generated from these
actual checks; it is numerical verification, not a measured room/human validation.

The installed SLABx-LH2 standalone air-condensation diagnostic is **not used**.
Read-only inspection found a fixed-total-mole saturation-cap discrepancy and two
different feed/gas H2 mole-fraction bases; those failed native identities remain in
ignored research notes. No native engine is patched, normalized or bypassed.
Existing rejected HyRAM source/flame chains remain rejected. No LH2 source is
automatically warmed, mixed or promoted into an accepted room boundary.

Cold contact, tissue freezing, H2-rich convection, droplets/air condensation and
respiratory injury need independently supported physical models. NASA identifies
cold contact, asphyxiation and oxygen enrichment as distinct cryogenic hazards;
the1997 handbook is historical public technical context, not a new regulatory
approval. ([NASA hydrogen handbook](https://ntrs.nasa.gov/citations/19970033338),
[NASA cryogenics](https://ntrs.nasa.gov/citations/20150000199))
NIOSH's cold-stress guidance likewise distinguishes several cold-related conditions;
an O2 flag cannot substitute for them. ([NIOSH](https://www.cdc.gov/niosh/cold-stress/about/))
Ordinary-air thermal physiology, if separately admitted, remains a separate physical
prediction and does not supply missing cryogenic contact or hypoxia biology.

Cantera is separately installed with its BSD-3-Clause notice and upstream species
provenance. Primary API/physical ownership:
[native reactors](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html),
[flow/wall Python API](https://cantera.org/3.2/python/zerodim.html),
[native thermochemistry](https://cantera.org/3.2/reference/thermo/species-thermo.html).
Only original composition/audit/test code and citations are added. No external
mechanism, software implementation, coefficient table or measured calibration data
are bundled or relicensed by this host.


OxygenCriterionResult is issued only by evaluate_oxygen_criterion after validating
the retained room result and declared criterion. It seals the exact input identities,
sample flags, minima, interpolated crossing estimates and duration; require_current()
rechecks the room-result binding and criterion before a downstream consumer relies
on the summary. Direct construction and dataclass replacement cannot create a second
screening receipt. The existing oxygen-room-result-issuer deferred contract checks
direct and arbitrary-token construction without running Cantera.
