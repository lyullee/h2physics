# Finite liquid-carrier and ammonia conversion boundaries

**Status: implemented_unverified.** This increment composes existing finite
reaction and caloric engines. No new model, example or deferred case has run.
It supplies a finite production/conversion interface, without qualifying a
catalyst, equilibrium conversion or industrial process.

`h2physics.adapters.carrier_conversion` reuses
`StoichiometricReaction`, `FiniteThermochemicalCycle` and the existing optional
native Cantera caloric owner. The shared kernel owns all species conversion,
feed/withdrawal, conditioning and reaction enthalpy calculations. No kinetic ODE,
EOS, equilibrium solver, phase-change solver or second solid-storage model is
introduced. The source/result utilities reuse the common producer-content
fingerprint helper.

## Chemical and energy scope

`lohc_pathway` declares a neutral **liquid** rich carrier, neutral liquid lean
carrier and gaseous H2, with `rich -> lean + n H2`. Global provider species may
include spectators with zero reaction coefficient. Existing reaction admission
checks atom, charge and molar-mass conservation. `n` is an explicit stoichiometric
normalization, not a usable vessel capacity or a fitted yield. Reverse extents
consume finite lean carrier and H2.

The existing [QM9-LOHC source](https://zenodo.org/records/10926772), its
[primary descriptor](https://doi.org/10.1038/s41597-025-04468-0) and existing
`data.lohc` audit remain the owners of computed gas-reference records and
molecular checks. Those gas-phase reference heats do not establish liquid
formation enthalpy, heat capacity, latent heat or mixture excess enthalpy.
An original audit may be retained as `pathway.original_source` for context;
this adapter never reads its heat as a liquid parameter. The liquid example's
formula species and common-reference caloric functions are original synthetic
fixtures. They are not measured carrier properties or molecular stability data.

`ammonia_pathway` admits `2 NH3(g) -> N2(g) + 3 H2(g)` with exact named chemical
roles. A negative imposed extent is synthesis material/caloric bookkeeping; it
does not predict Haber-Bosch conversion, compressor work or reactor equilibrium.
The native helper uses actual ideal-gas NH3/N2/H2 molar enthalpies through
`CanteraMultiphaseMolarEnthalpy`, preserving audited source/owned native phases.
The source phase must be caller-created; no mechanism is bundled.
[Cantera's property API](https://cantera.org/3.2/python/thermo.html) owns
thermochemistry and J/kmol-to-J/mol conversion through the existing bridge.
The [NIST ammonia record](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7664417&Mask=208F)
documents the distinction between gas reference properties and other phase
properties; no NIST numeric table or fit is imported here.

The installed GRI example has a selected-species common fit intersection of
300–3500 K. The example additionally declares 0.01–1 MPa; that pressure envelope
is an authored ideal-gas calorimetry limit, not high-pressure accuracy evidence.
Declared mechanism bounds and native selected-species fit bounds still apply.
GRI's gas combustion mechanism is not a qualified ammonia catalyst mechanism.
H2 spin is explicitly unresolved/frozen in this example; no para/ortho energy
conversion is inferred.

All inventories and extents are SI mol, T is K, absolute P is Pa and h is J/mol.
Each provider must supply a common formation/reference basis across every
participating species. Arbitrary pure-fluid sensible zeros cannot establish
reaction heat. `phase_reference_id`, provider `basis_id` and
`hydrogen_partition_id` are retained separately. Label equality alone does not
establish cross-provider caloric equivalence.

## Python composition

```python
from examples.carrier_conversion import liquid_problem

model, initial, stages = liquid_problem()
result = model.run(initial, stages)
assert result.require_current() is result
actual_trace = result.process_trace
actual_provider = result.caloric_source.provider
```

The example executes only when explicitly called. `native_ammonia_caloric`
imports Cantera inside that helper, so the default adapter does not load the
optional engine. `functional_carrier_caloric` binds the existing
`FunctionalMolarEnthalpy`; its caller supplies functions, common zeros and
T/P bounds. A custom `CarrierCaloricSource` requires a nonexecuting
definition probe and explicit source, phase-reference, spin and origin meaning.
Its public `native_objects` retains actual supplied native objects. Hidden
callback state and a custom probe's truthfulness remain caller responsibilities.

`FiniteCarrierConversion(pathway, caloric_source, evidence)` takes existing
`ThermochemicalStage` objects. The only admitted conversion is the original
pathway reaction, with a supplied extent and evidence. Stages may also condition
temperature or withdraw components without conversion. Their windows must be
contiguous on the evidence clock. The shared driver requires a single fixed
absolute pressure, common energy basis and finite nonnegative inventories.

Pre-withdrawals leave at the previous inventory T, at the stage-start event.
Finite feeds retain their own T/P/reference. Each feed packet's `source_id` must
be unique in a run, preventing repeated consumption of the same declared
packet. These are supplied finite packets, not a simulated external reservoir,
replenishment law, flow rate or residence-time model.

Positive `process_trace.net_heat_required_j` means heat enters the material.
It includes sensible conditioning and existing reaction enthalpy once. Negative
values mean heat must leave. This is a constant-P H ledger, with PV work already
inside enthalpy, not rigid-vessel U or a wall-storage balance. There is no shaft,
kinetic/potential, non-PV work, utility capacity, phase-stability, gas/liquid mass
transfer or excess mixing term. A liquid phase label does not verify liquid
stability across the declared range. Those inputs and assumptions need separate
material/phase qualification.

Results separately retain initial/final H2, H2 formed by positive conversion,
H2 consumed by reverse conversion and actual withdrawn H2. A species audit also
includes supplied feed H2. No exported-H2 atom allocation between initial stock
and newly formed H2 is inferred. A generated amount is not automatically a
harvest, pure product, sale or release source.

`CarrierConversionResult.hydrogen_mass_ledger_kg` exposes those retained H2
quantities on a kg basis using the exact molecular mass declared by the pathway's
H2 species. The read-only view reports initial/final inventory, supplied feed,
gross reaction formation/consumption, actual withdrawal and the species-balance
residual. Access revalidates the original result first. It adds no separation,
purity, flow or source-allocation assumptions.

## Actual source packets and original-result admission

`model.verify_result(result)` and `result.require_current()` return the exact
original producer-issued result. They inspect owner definitions, explicit
provider probes, shared-kernel material matrices and cached original trace
content. They do not recompute h, conversion, equilibrium or kinetics. A copied
or `dataclasses.replace` result, altered summary/context/cache, changed kernel
or declared callable/default binding is rejected. The public result retains
actual pathway, caloric source, kernel, shared trace and process evidence.

`model.withdrawal(result, step_index, boundary_id=..., frame_id=...,
evidence_id=...)` requires actual nonzero component takeoff in that accepted
step. It returns a producer-issued `CarrierWithdrawal` containing the original
result, finite named amounts, actual outgoing enthalpy, previous T, absolute P,
energy reference, clock/region, boundary/frame and exact stage-start event time.
`packet.require_current()` returns that original packet. Its enthalpy may have
either sign because formation/reference offsets are retained. Positive amounts
and that enthalpy are oriented from sender into a receiver. No mass flow,
incident waveform, density, opening or separator performance is fabricated.

For direct finite coupling, `feed = packet.as_feed(source_id=...)` returns the
existing `ThermochemicalFeed`. The receiver must call
`run(..., feed_bindings={feed.source_id: packet})` to retain/audit actual source
provenance. This bridge requires the **same actual caloric-source object**, the
same clock and exact receipt/takeoff event, with matching amounts/T/P/reference
and origin. It does not infer storage between times, clock alignment or a
cross-provider reference translation. Receiver results keep the original source
objects; later source admission failure also invalidates the dependent result.
One actual withdrawal cannot be consumed twice within that receiving run,
including when the caller assigns it two different feed IDs. Physical allocation
among separate runs or branches remains the caller's network responsibility.
Unbound feeds remain explicitly supplied inputs, with no computed-producer claim.

The owner registries use weak references and do not retain an unbounded strong
history of discarded results/packets. A packet intentionally retains its sender
result while that packet is used. Native caloric scratch states may be changed
by subsequent property queries: this guard seals **definitions and retained
results**, not an unused scratch T/P. Native phase definition/pointer mutation
is rejected by the existing caloric owner's guard. No historical tamper log,
cryptographic attestation, opaque/private callback-state check or independent
scientific validation is claimed.

`CarrierConversionError` retains the original cause, owner, initial/schedule,
bound source objects, available shared trace, actual completed prefix and any
constructed result. The underlying shared error retains failed stage/inventory,
partial conversions and failed audit objects. `CarrierBindingError` retains the
rejected actual result/packet and chained cause. No alternative engine or
repaired inventory is substituted.

## Deferred evidence

Eight cases are prepared in
`validation/cases/carrier_conversion.py`: seven use profile `carrier-conversion`
and one uses `carrier-conversion-native`. They cover finite liquid material,
authored analytic heat and reference shift, reverse cycle, actual coupled finite
packets, negative domains/failure retention, cached/source binding mutation,
weak lifecycle and actual native ammonia/whole-mixture calorimetry. None has run.
No catalyst data, new measured data, independent material validation, plant
efficiency or industrial operating envelope is supplied by this increment.
