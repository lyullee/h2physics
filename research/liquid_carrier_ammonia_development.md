# Liquid-carrier/ammonia integration development record

Date: 2026-10-28. Status: **implemented_unverified**. Development is static-only
under the user's deferred-execution priority. No module, example, case discovery,
native model, test, benchmark, installation or cluster job has been executed.

## Ownership and reuse

The five owned files are the carrier_conversion adapter, dedicated manual,
this record, original Python example and deferred case file. Shared catalog,
central manuals, existing solid_reaction/data.lohc and native sources are not
edited. Parent integration owns consolidated family/coverage claims.

The shared finite thermochemical driver supplies material conversion,
conditioning, imposed component takeoff and constant-P H accounting. The native
ammonia helper reuses CanteraMultiphaseMolarEnthalpy's actual independent
source/owned gas phase and definition guards. Common result-content hashing is
imported from adapters.result_provenance. No new ODE, rate law, thermochemistry,
equilibrium or solid-storage physical solver is introduced.

LOHC liquid roles and NH3/N2/H2 ideal-gas roles are checked even when a
CarrierPathway dataclass is constructed directly. A forward extent forms H2;
reverse extent consumes finite products. Other provider species are explicit
zero-coefficient spectators. Global formation/reference, atomic-weight, phase
and H2 partition evidence remains required. Computed duty is not conversion
achievability, catalyst rate, liquid stability or utility availability.

## Primary sources, rights and static source review

- [Cantera3.2 thermodynamic API](https://cantera.org/3.2/python/thermo.html),
  actual phase objects, partial molar h and native species fit bounds. The
  [Cantera community license statement](https://cantera.org/community.html)
  identifies BSD-3-Clause. Installed License.txt was read; no native code,
  coefficients, mechanisms or examples are bundled into these five files.
- The separately installed `cantera/data/gri30.yaml` was inspected as text.
  NH3, N2 and H2 exist; selected fit intersection is300–3500K. The native helper
  retains the existing copy audits/source hashes and original actual objects.
  The authored pressure bound0.01–1MPa is an input applicability restriction,
  not a claim of measured ideal-gas accuracy. No native call established
  runtime compatibility or endpoint calorimetry in this wave.
- Installed gri30.yaml SHA256:
  `06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345`.
  Installed Cantera License.txt SHA256:
  `e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb`.
  These are source/license-byte observations, not execution evidence.
- Hassan Harb's [QM9-LOHC release](https://zenodo.org/records/10926772), existing
  rights receipt `research/data/lohc-enthalpies.toml` (CC-BY-4.0), existing
  source SHA256
  `9f89ee72586dd00e5be58c0650b11d2e135e993873f90da23c8094c5265ee242`,
  and [primary descriptor](https://doi.org/10.1038/s41597-025-04468-0).
  Existing audited gas-reference semantics remain298.15K/101325Pa and per-H2
  normalization. The new code does not load that archive, repeat its data audit,
  select a row, copy its records or use its gas heat as liquid h(T,P).
- [NIST ammonia gas-property record](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7664417&Mask=208F)
  and [NIST-JANAF ammonia reference description](https://janaf.nist.gov/tables/H-083.html)
  supply primary context on species/phase/reference meaning. No numeric table,
  coefficient, worked example or new NIST dataset is imported or reproduced.

Native source/rights were inspected read-only. No dependency was installed or
updated. The optional ammonia path needs the existing separately installed
Cantera3.2 chemistry dependency; synthetic common-reference cases use existing
NumPy/SciPy core through the shared driver. This adapter adds no dependency.

## API and source ownership

CarrierCaloricSource retains the actual provider, origin/source, phase-reference,
H2 partition, actual native objects and a nonexecuting definition probe. The
functional helper records existing functions/defaults and bounds. The native
helper calls only the existing definition guard during producer checks. Custom
probes must not solve or mutate; arbitrary hidden callback/private/model state
is not discoverable from ordinary Python identity.

FiniteCarrierConversion returns only producer-issued CarrierConversionResult;
verify_result and result.require_current return that exact object. Summary H2 is
partitioned into formed, consumed, initial, final and actually withdrawn, with
feed included in the species residual. Cached shared/native/energy data and
original kernel/provider/pathway/evidence bindings are retained and sealed.
No physical calculation is replayed by verification. Exact restoration can pass;
the contract is current content, not tamper history or independent qualification.

The actual pre-withdrawal packet additionally retains frame/port/clock/region,
event time, material and outgoing H. Direct receiver composition requires the
same actual caloric-source object and identical event clock/time; no equal-label
reference translation or unmodeled holding period is inferred. Original source
objects stay attached to downstream results and are checked before/after run and
when results are consumed. Packet IDs cannot be consumed twice in one run.
Binding the same actual sender-step withdrawal under two different feed names
also rejects, so renaming cannot bypass a finite packet allocation.
The caller remains responsible for allocating a physical packet among different
independent runs/branches; there is no global transactional network reservoir.

## Deferred cases and unresolved domains

Eight metadata-only cases are authored: finite material; constant-Cp heat with
elemental-zero invariance and hot feed; reverse cycle; finite sender/receiver
packet with cancelling H; actual failure/negative boundaries; original result,
caloric and kernel mutations; weak lifecycle; native ammonia whole-mixture H and
actual alternate native phase pointer rejection. Profiles are carrier-conversion
(seven) and carrier-conversion-native (one). All remain unrun and no pass is
claimed. Native path and reference-shift results are planned checks, not reported
numbers.

The liquid example is an original hypothetical C/H/O constant-Cp fixture.
Real liquid LOHC formation/reference properties, excess heat, vapor pressure,
gas/liquid partition, composition-dependent h, catalysis/deactivation, mass/heat
transfer and measured reversible-cycle evidence are missing. Ammonia liquid
storage/vaporization, real-fluid high-pressure properties, catalytic rates,
equilibrium extent, reactor design, purification/residual NH3, compression and
plant heat recovery are excluded. Neither source packet predicts a leak,
opening, continuous waveform, ignition, accident frequency or saleable product.
