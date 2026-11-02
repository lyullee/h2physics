# Finite fuel-cell integration development record

2026-10-28; status **implemented_unverified**. Only static source/API review and
AST/Ruff/LF checks are permitted in this wave. No model/native/module import,
example, case discovery/execution, test, installation, benchmark or job ran.

## Physical ownership and contract

Five files only: adapters/fuel_cell.py, dedicated manual, this record, example
and deferred case file. Existing shared electrochemistry/reaction/caloric/native
source, catalog and central manuals were not modified.

Actual HydrogenStack fuel_cell mode owns supplied loss functions, reversible
voltage, series/area current, Faraday H2 and signed electric/reaction-energy
rates. Shared finite stoichiometric/thermochemical code owns H2+.5O2→H2O,
finite stocks, conditioning, feeds/takeoff and constant-P H. CarrierCaloricSource
and result_provenance are reused for common property/source/content binding.
The adapter adds finite composition and an independently checked external
electricity/heat ledger, not a replacement physical solver.

Product phase and reference are checked against actual h(T,P), using the
positive splitting enthalpy convention expected by ReactionEnergy. Liquid and
vapor references are not interchanged. Actual stack H2 molar mass must match
the material provider. Gibbs/activity and polarization functions stay supplied
evidence. The T-only stack callback cannot infer evolving finite-inventory
activities; this is an externally maintained operating-point premise.

Explicit unity Faradaic efficiency admits a complete chemical/heat fate. Other
efficiencies reject rather than assigning unallocated energy to heat. Current
commands that exhaust finite H2/O2 reject without truncation. Zero current
retains a zero-reaction mode while temperature/feed/outlet conditioning remains
explicit. No new Nernst, catalyst, EOS, thermal controller or utility model is
implemented.

## Public primary sources and rights

- [US DOE fuel cells](https://www.energy.gov/cmei/fuels/fuel-cells): primary
  process description for H2/oxygen/water/electricity/heat. No efficiency value,
  device parameter, coefficient, example or implementation was copied.
- [Cantera3.2 thermodynamic API](https://cantera.org/3.2/python/thermo.html):
  actual native molar h and chemical potentials, units and phase definitions.
  Existing independently owned CanteraMultiphaseMolarEnthalpy provides the
  native property bridge; all original source/owned phases and copy audits stay
  accessible through caloric_source.provider/native_objects.
- [Cantera community rights statement](https://cantera.org/community.html):
  BSD-3-Clause. Installed source/license were already inspected read-only in
  the preceding carrier lane. No native mechanism, coefficients or source is
  bundled by these five files. Existing chemistry dependency is reused.
- [NIST water phase/property record](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=1):
  primary context distinguishing gas/condensed/phase-change thermochemistry.
  No NIST numeric table or thermochemical fit was imported or reproduced.

Installed gri30.yaml source SHA256:
`06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345`.
Installed Cantera License.txt SHA256:
`e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb`.
The native example reads that separately installed source as unchanged text and
uses native Solution construction, avoiding the known non-ASCII path boundary.
These byte observations do not establish execution or scientific validity.

The original synthetic liquid-water fixture has invented constant-Cp formation
terms, Gibbs input and ohmic coefficient expressly for analytic checks; it is
not a device/material parameter set. The optional native example uses installed
H2/O2/H2O gas fits at authored500–900K/0.05–0.2MPa and resets an authored held
activity composition for native chemical potentials. Neither that activity nor
its ohmic input is a measured fuel-cell operating point. H2 spin is frozen and
unresolved. No experimental dataset was acquired and no dependency changed.

## Finite boundary and provenance

Separate named hydrogen/oxidant inlets, one imposed component outlet and an
explicit frame are admitted. Every finite feed has an explicit receiving port;
reactive H2/O2 cross-port assignment rejects. Stocks are aggregate bookkeeping
over separated material supplies, not an EOS pressure state or a premixed tank.
Actual absolute pressure/common h reference is retained on all packets.

Each actual StackResult and common kernel trace remains in its original step.
The required heat uses existing kernel H duty minus actual electrical input;
no reaction formation heat is counted twice. Native isothermal stack heat is
compared to the reaction-only duty, while feed/temperature conditioning keeps
its own signed contribution. PV work is already in H; rigid-vessel U/wall
storage and transient stack temperature are absent.

Producer methods verify_result/trace.require_current return the exact issued
trace after owner/data/cache checks without a physical replay. Weak admissions
avoid an unbounded owner history. Common callback/default/geometry/kernel and
native definition bindings are guarded; arbitrary hidden globals/private native
state/transitive resources or historical tampering are not attested.

Original nonzero pre-withdrawals produce exact finite event packets with
species/phase, clock/frame/port, T/P and signed caloric reference. Actual carrier
or fuel-cell packets can feed this owner only with identical actual caloric
source, event clock/time/frame and material/state/reference/origin. Renamed
duplicate actual sender-step allocations reject within a run. Cross-provider
translation, inter-event holding/pipe physics and global network allocation
across separate runs remain caller contracts. Product takeoff does not predict
purity, separation work, continuous flow or a release source.

Failures retain original cause, accepted prefix/current inventory, failed actual
stack/kernel attempts, native provider objects, attempted h/extent, command
schedule, source objects and available aggregate candidate. Replaced results,
cached stack values and downstream context do not acquire automatic new seals.

## Deferred verification and remaining research

Eight metadata-only definitions: seven profile fuel-cell and one fuel-cell-native.
They prepare analytic Faraday/stoichiometry; electric/chemical/heat signs and
phase/reference rejection; hot finite feed conditioning; H2/O2 overdraw with
actual successful prefix; zero current/unity-efficiency/domain guards; actual
source packet and cancelling sender/receiver H+electric+Q; original/cache/
geometry/kernel mutation and weak lifetime; actual native mixture-H comparison
and caloric pointer guard. All are unrun. Native consistency is not independent
measured validation; full affected regression remains deferred.

Open requirements include qualified loss/activity/free-energy data, real-fluid
and liquid phase stability, channel transport, reactant pressure/composition
dynamics, humidity/membrane/water management, crossover/degradation, startup,
thermal storage/cooling utility, air compressor/blower/pump power, recuperation
and measured finite system performance. No facility efficiency, pure product,
purge/leak probability, accident waveform or annual availability is inferred.
