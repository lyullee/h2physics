# Finite fuel-cell material, electricity and heat boundaries

**Status: implemented_unverified.** This composition and its eight deferred
cases have not run. It connects the existing `HydrogenStack` fuel-cell mode to
finite H2/O2/H2O stocks and the existing thermochemical driver. It does not
introduce another polarization, EOS, reaction-rate or thermal-utility law.

The [US Department of Energy fuel-cell description](https://www.energy.gov/cmei/fuels/fuel-cells)
provides primary context for hydrogen/oxygen conversion to water, electricity
and heat. No published performance number, coefficient or device example is
used as a parameter. The caller supplies qualified thermochemistry, polarization
loss functions, operating domain and evidence, or explicitly synthetic fixtures.

## Actual owners and finite process

`FiniteFuelCell(stack, caloric_source, boundary, evidence)` requires the actual
shared `HydrogenStack`. Its original `evaluate(..., mode="fuel_cell")` owns
voltage/loss/Faraday and signed electrical/H2 rates. Geometry retains actual
series-cell count, active area and the H2 molar-mass basis. That mass must match
the finite material provider.

The deferred synchronized Cantera case derives `StackGeometry`'s H2 molar mass
from the native `H2` species `molecular_weights` entry, converting Cantera's
kg/kmol to kg/mol by dividing by 1000. This keeps the exact native mechanism
mass convention at the channel/stack boundary; the coupling does not widen its
molar-mass comparison to accept independently rounded constants.

The material reaction is `H2 + 0.5 O2 -> H2O` per mol H2. Existing balanced
`StoichiometricReaction` and `FiniteThermochemicalCycle` own finite conversion,
atom/charge/mass checks, phase enthalpy, feed conditioning and imposed component
takeoff. Other explicitly declared provider species may remain spectators.
This is an aggregate material/caloric boundary over separate reactant supplies;
it is not a premixed H2/O2 tank, an anode/cathode flow-field model or a predicted
stack gas composition.

`FuelCellBoundary` explicitly declares absolute pressure, water product phase,
T/current domain, reaction-enthalpy matching tolerance, activity/pressure/thermal
evidence, frame and separate hydrogen/oxidant inlet and component-outlet IDs.
`FuelCellStep` supplies a finite interval/clock, imposed T, nonnegative current
density, explicitly unity Faradaic efficiency and evidence. It may also retain a
`FuelCellOperatingState` with explicit anode/cathode pressure, dimensionless
species activities, water phase, reference IDs and evidence ID. When supplied,
the finite driver applies `fuel_cell_activity_correction` to the original shared
reaction-energy law for that step and evaluates the existing `HydrogenStack`
with the corrected Gibbs energy. The enthalpy remains on the original common
caloric basis. The state temperature must match the step exactly and its water
phase must match the stack boundary. Existing schedules without an operating
state retain the temperature-only behavior. A zero current is
an imposed idle command, not an independently solved open-circuit state.

Every step calls the actual shared fuel-cell mode. Consumed H2 extent is taken
from that actual negative H2-production rate and the interval duration; O2 and
water follow the shared balanced reaction. A separate current/series/Faraday
check audits the H2 extent. Finite depletion rejects the requested step instead
of silently reducing current, shortening the interval or repairing inventory.
Completed earlier steps remain available in the failure.

Only `eta_F=1` is admitted. The shared stack's nonunity Faradaic option leaves
chemical/thermal loss fate unallocated; this composition does not assign that
missing fate to heat or invent side-reaction stoichiometry. No catalyst aging,
fuel crossover, internal leakage, reactant starvation transient or power-demand
controller is introduced.

## Phase, caloric reference and activity meaning

The reused `CarrierCaloricSource` is a generic actual common-reference provider
binding; its use here does not invoke any LOHC/ammonia pathway. It retains
source/origin, formation/phase reference, H2 partition, optional actual native
objects and a read-only definition probe. `FunctionalMolarEnthalpy` remains
caller-owned. An optional example reuses actual
`CanteraMultiphaseMolarEnthalpy` and its independently owned source/gas phases.
The [Cantera property API](https://cantera.org/3.2/python/thermo.html) owns native
h and chemical potentials. No native mechanism or coefficients are bundled.

H2/O2 are explicit gas material species. Water's caloric species must match the
declared `ReactionEnergy.water_phase`: liquid or vapor. The
[NIST water record](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=1)
distinguishes gas/condensed and phase-change properties; no numeric NIST table
is imported. The adapter does not convert arbitrary sensible-energy zeros into
reaction formation enthalpies or silently replace one water phase with another.

Each actual stack result's energy reference must equal the provider basis, and
its positive water-splitting enthalpy per mol H2 must match
`h_H2 + 0.5 h_O2 - h_H2O` at the actual imposed T/P. The reverse material
reaction then has negative reaction enthalpy. These phase/reference checks do
not establish that a supplied Gibbs function or polarization curve is accurate.

`HydrogenStack.thermochemistry(T)` has no finite-composition argument. Activities
and pressure are therefore an explicit externally maintained boundary supplied
either by the existing callback or by each step's `FuelCellOperatingState`; they
are not inferred from remaining stocks. The operating state names the liquid or
vapor product-water phase; `fuel_cell_activity_correction` rejects a water
activity whose phase differs from the shared `ReactionEnergy` reference. The
operating-state pressure and activities remain caller-supplied values: this check
does not derive fugacity from pressure or establish a pressure/activity law.
The native example resets a declared nonzero ideal-gas composition for its
chemical-potential query on every callback. That fixed activity calculation is
distinct from the aggregate inventory composition. Arbitrary hidden callback
state, transitive resources and private biological/electrode internals remain
outside producer-content verification.

The native example declares 500–900 K and 0.05–0.2 MPa with a vapor product,
inside the selected installed GRI species fits. These are authored ideal-gas
calorimetry limits, not a validated fuel-cell device operating envelope. Native
species fit and mechanism bounds still apply. H2 spin is explicitly unresolved
and frozen; no para/ortho reference translation is inferred. Liquid-water phase
stability, saturation/condensation, humidity/water transport and electrolyte
activity require separate evidence/models.

## Signed energy ledger

Amounts are mol, geometry is m2, current density A/m2, current A, T K, absolute
P Pa, time s, h J/mol, powers W and integrated duties J. Shared-stack electricity
is signed **into** the material: fuel-cell power and integrated electricity are
negative. Positive required heat enters; negative required heat must leave.

The existing kernel's enthalpy duty includes reaction formation/sensible terms
once. The composition computes required heat as that duty minus actual stack
electrical input. Thus the ledger is
`H_final - H_initial = H_feed - H_out + electricity_into + required_heat_into`.
Shared stack isothermal heat rejection is checked against the reaction-only
part; hot feeds or temperature conditioning add their own signed duty. The
adapter does not add the shared stack's reaction-enthalpy rate a second time.

Each stage conditions the carried material/feed to its imposed operating T,
then uses that held T for the current command over the interval. Conditioning
is a finite packet operation with explicit duty, not a resolved heating-time
trajectory or a prediction that the thermal boundary can reach the setpoint.

This is constant-P H accounting: PV work is already in h. No rigid-volume U,
thermal wall state, transient temperature solve, cooling-system capacity,
compressor/shaft work, gas kinetic energy, mixture excess h, energy recovery or
utility efficiency is claimed. Initial, feed, final and actually withdrawn H2
remain distinguishable in the retained shared traces; fuel-cell H2 is consumed,
not counted as newly produced hydrogen. Water formation and actual water
takeoff are separate quantities.

## Inlets, original results and downstream packets

Steps accept finite `ThermochemicalFeed` packets, each with its own T/P/common
reference and unique packet ID. `feed_ports` explicitly maps each packet ID to
one admitted hydrogen or oxidant inlet. Reactive O2 cannot enter through the
hydrogen port and reactive H2 cannot enter through the oxidant port. Humidity
or spectator components still require their actual supplied phase properties;
no air or water composition is inferred. Feed pressure/reference mismatch is
rejected by the shared driver; compression or pressure recovery is not free.

`trace.require_current()` and `model.verify_result(trace)` return only the exact
original producer-issued trace, retaining actual stack/geometry, source/kernel,
per-step raw `StackResult`, shared traces, original command and all ledgers.
Common result-content seals and actual owner bindings reject copies/replacements
and changed cached results, geometry, declared callback/defaults, kernel or
native phase definitions. Verification does not replay polarization, enthalpy,
kinetics or conversion. Native caloric scratch T/P may change without changing
definitions or old cached results. This is current content correspondence, not
historical tamper proof, predictive reproducibility or independent validation.

`model.withdrawal(trace, step_index, boundary_id=..., frame_id=...,
evidence_id=...)` requires nonzero actual pre-withdrawal in that accepted step
and the admitted component outlet/frame. Its original `FuelCellWithdrawal`
retains actual species/phase definitions, amounts, signed outgoing enthalpy,
previous T, absolute P, common energy/phase/spin reference, exact stage-start
event, clock/region/frame/port and original trace. `packet.require_current()`
returns that exact packet. The outlet is an imposed finite component takeoff;
it is not a separator, purge-valve law, continuous flow, saleable purity or an
accident opening/source waveform.

For same-reference finite composition, `packet.as_feed(source_id=...)` creates
the existing feed type. The receiver must retain the source via
`run(..., feed_bindings={feed.source_id: packet})`. Direct inputs accept actual
carrier or fuel-cell withdrawal objects, with the same actual caloric source,
clock/event/frame, matched amounts/T/P/reference/origin and explicit receiving
port. One sender-step withdrawal cannot be reused twice in a receiving run,
even under renamed feed IDs. No holding period, pipe dynamics, frame transform,
cross-provider reference translation or global allocation among separate runs
is inferred. Unbound inputs remain explicitly supplied finite packets.

Owner registries are weak; discarded traces/packets are not retained forever.
An intentionally used packet retains its original sender trace. Failed runs
raise `FuelCellError` with original cause, owner, initial/current inventory,
schedule, failed command, completed prefix, actual shared stack/kernel attempt,
attempted h/extent, bound sources and any constructed aggregate trace. Invalid
result/packet checks raise `FuelCellBindingError` retaining rejected objects.

## Deferred examples and cases

`examples/fuel_cell.py` contains an authored constant-Cp fixture and an optional
actual native gas property path. `validation/cases/fuel_cell.py` declares eight
unrun cases: seven `fuel-cell`, one `fuel-cell-native`. They prepare independent
Faraday/count, signed analytic heat, feed conditioning, finite failure, idle and
domain, source/coupled-H, mutation/lifecycle and native mixture-H checks. These
definitions are not passes or measured device validation.

## Separated native gas compartments

`adapters.fuel_cell_compartments` runs distinct frozen pure-H2, pure-O2 and water-
vapor native gas volumes using prescribed shared-stack Faraday rates, explicit
volumes and separate thermal boundaries. Each volume evolves its own pressure,
temperature, species and internal-energy ledger. The compartments never share a
reactor. This level does not close combined reaction-energy allocation or feed
pressure back into voltage. Request031 specifies the actual missing pressure/
activity-sensitive stack and simultaneous multivolume driver. The authored native
case and all physical execution remain pending on the cluster. The detailed
receiving API and parallel acceptance matrix are in
[`integration_request_031.md`](../research/integration_request_031.md).

`adapters.fuel_cell_compartment_energy` compares actual independently integrated
native reaction-port masses as H2-equivalent extents. Shared callbacks alone do not
prove identical adaptive quadratures. The complete-window diagnostic retains actual
compartment internal-energy changes, conversion-plane enthalpy, compartment heat,
solid/coolant storage, original electrical energy and external thermal heat. A
signed unresolved combined energy residual remains explicit; the diagnostic does
not infer a missing membrane/caloric coupling term or declare reaction energy closed.
Exact common stack, clock/window and allocation evidence are required.
The unresolved pressure-feedback and reaction-energy status fields are fixed
non-constructor fields. Callers cannot turn these unsupported capabilities into
positive claims by passing boolean flags when constructing a receipt.

`FuelCellOperatingState` and `fuel_cell_activity_correction()` now expose the
shared reaction's ideal dimensionless-activity correction with separate channel
pressures, explicit activity reference identities and a state evidence identity.
This lets a caller build the existing `HydrogenStack` thermochemistry callback
from a typed state. It is still an algebraic callback seam: an external operating
schedule must supply its values, and the separate compartment integrators do not
feed their evolving pressures into it. Request031's native simultaneous solve,
activity/fugacity owners and combined heat balance remain unimplemented.
`ReactionEnergy` exposes its own reversible and thermoneutral voltages, and the
deferred case `fuel-cell-activity-corrected-stack-operating-point` records the
synthetic activity-to-shared-stack algebra contract. It is authored only, not run.
The PV-to-fuel-cell batch receipt also seals its original source/sink identities,
transfer and conditioning evidence IDs, loss/tolerance and derived molar ledger.
Post-admission evidence relabeling now invalidates that handoff. Its adversarial
contract is deferred; this remains a stoichiometric bridge rather than the
simultaneous pressure/activity/thermal solve in Request031.

`adapters.fuel_cell_activity_receipt.sample_fuel_cell_activity_receipt()` adds a
post-run bridge for one exact common accepted time in the separate native H2, O2
and water-vapor pressure traces. By default, it converts each pure ideal-gas
pressure to a dimensionless activity using an explicitly supplied reference
pressure and reference identity. For a non-ideal calculation, pass a
`FuelCellFugacityActivityProvider` whose callback delegates to the caller's chosen
property service and returns fugacity in Pa for `(species_id, absolute_pressure_pa,
temperature_k)`. The adapter evaluates both sample and reference fugacity at the
same explicit temperature and uses their ratio as activity; it adds no EOS or
fugacity correlation. Provider identity/evidence and its returned activities are
bound to the receipt, and provider changes that alter those retained activities are
rejected on revalidation. The caller remains responsible for model validity,
reference-state selection and callback hidden-state provenance.

Both routes apply the existing reaction correction and evaluate the shared stack at
explicitly supplied temperature and current. The sealed receipt retains the
compartment trace and cannot claim pressure feedback or simultaneous energy closure.
Its deferred contract is authored but unexecuted; this bridge does not implement
Request031's native coupled driver.

`sample_fuel_cell_activity_series()` extends the post-run bridge over the complete
shared accepted-time grid. The caller supplies one explicit
`(time, stack_temperature, current_density, ReactionEnergy)` row per native time;
the adapter creates a sealed receipt per sample and requires a common channel
reference and caloric basis. `FuelCellActivitySeries.operating_states` can be
attached to finite schedule steps as held operating states. It does not interpolate
between samples, feed pressure into the compartment integrators, or close combined
energy. Its integrity contract is authored for deferred execution.

The solver-neutral `FuelCellSynchronizedTrial` copies the supplied H2/O2/H2O
channel map and retains it as a `MappingProxyType`. Its currentness seal binds
both that proxy identity and its ordered channel entries. Changing the caller's
original mapping after admission has no effect; replacing the retained proxy,
even with an equivalent mapping, invalidates the trial. The deferred trial
contract records both behaviors.


FuelCellCompartmentTrace can only be created by the separated native-compartment
run. Its previous private binding tuple was self-computable and could be attached to
a caller-created trace; the deferred fuel-cell-native contract now checks direct
construction rejection. This receipt boundary does not change pressure feedback or
energy-closure limits.


Staged electrochemical operation receipts are issued only after the existing thermal
and finite-reactant owners complete every declared interval. The receipt cannot be
constructed from caller-selected held temperatures or heat summaries, and a
dataclass-replaced copy does not retain issuance. This guards native result provenance;
it does not add simultaneous pressure or energy coupling.


## Executed native caloric path — 2026-11-01

The installed Cantera 3.2.0 native_gas_problem and validate_native paths passed
locally using the real gas enthalpies/chemical potentials and shared stack.
Mixture enthalpy discrepancy was 1.14e-13 J; electricity into the material
boundary was -377.218062464 J and energy residual -1.14e-13 J. Replacing the
native caloric pointer was rejected, and restoring it reinstated admission.
The installed gri30.yaml SHA-256 was
06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345.
No mechanism asset is redistributed, and this check does not extend its rights
or establish measured electrochemical-device validation.
