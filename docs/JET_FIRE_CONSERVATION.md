# Unchanged native jet-fire conservation diagnostics

Status: **implemented_unverified diagnostic code; jet-fire remains planned and
rejected**. No new model/native calculation, import, example, case invocation,
test, replay or benchmark was performed in this coding lane. Six deferred
cases belong to profile `jet-fire-conservation`; none has passed. This adds
zero accepted jet-fire families and does not change executed coverage.

The existing [HyRAM Flame integration](NATIVE_JET_FIRE.md) executes the real
preferred HyRAM+ source, expansion, combustion, spatial ODE and radiation. Its
recorded source-to-field mass, transport and direct-EOS caloric failures remain
unchanged. `adapters.hyram_flame_conservation.HyRAMFlameConservation` inspects
that same original `HyRAMFlameRun`. It never rescales its fields, replaces its
Gaussian entry, fits an acceptance coefficient, changes chemistry, injects a
substitute jet or calls a second nozzle.

## Python composition

Supply a dedicated actual shared `CanteraMolarEnthalpy` provider for neutral
ideal-gas H2/O2/H2O/N2/CO2, a `ConservationInterpretation` and explicit
`ConservationQuadrature`. The interpretation declares the expanded-H2 source
plane, native ambient surrogate, normal-H2 versus mechanism-spin-unresolved
assumption, caloric reference, native field ansatz and evidence/origin.
These declarations permit a diagnostic interpretation; they do not validate
the cross-model assumptions.

Call `auditor.audit(original_run, native_section_indices=(...))` with ordered
original station indices including entry and visible endpoint. It checks the
reviewed actual HyRAM6.1 type/source bytes, unchanged native signature, cached
source/ambient correspondence, complete visible endpoint and one common
source/window clock. It reuses the original source gates rather than turning
new numerical bookkeeping into replacement acceptance tests.

The result retains the actual native flame, its original failed gates, native
caloric phase/provider, shared reference reaction/conversion and selected
section quadratures. All flows are kg/s; powers W; thermochemical amounts mol;
native Cantera J/kmol are converted once by the existing shared caloric bridge.
Pressure is absolute Pa, temperature K, geometry m and clocks s.

The native phase is dedicated to these caloric queries: its T/P changes during
calls. Species definitions, provider method binding, molecular/elemental data,
reference reaction and declared scope are guarded. Native flame chemistry and
field state remain unchanged; concurrent external mutation is unsupported.
`JetFireConservationError` retains the original cause, source native result,
auditor, completed sections and failing original index/radial coordinate.

## New flux evidence

Each selected circular section uses its actual native Gaussian mixture fraction
and axial velocity, native product density, native temperature and native
product mass fractions. Independent radial quadrature integrates total mass,
fuel-origin f, individual species, elements, formation-reference enthalpy and
kinetic power. Native fractions are never normalized; a signed simplex defect
is checked against the explicit numerical budget. Species/phase/native-fit
failures are retained rather than extrapolated.

The section energy coordinate is

\[
\mathcal E=\int\rho v\,[h_{common}(Y,T)-h_{air,common}+v^2/2],dA.
\]

Subtracting one declared ambient enthalpy removes the enthalpy of quiescent
entrained ambient material in this two-stream diagnostic. It does not change
native field values. The source comparison uses the **actual native expanded
H2 temperature, velocity and nozzle mass flow** on the same diagnostic caloric
reference. It is not a new expansion calculation, a conversion of CoolProp's
energy zero or proof that an ideal-gas NASA caloric model equals the real-gas
source EOS. Normal/para spin conversion is not solved.

`source_to_entry_common_power_residual_w` compares entry energy with that
source-plane interpretation. Element H provides an independent hydrogen-mass
ledger including product water. The visible-section H change is a signed
unclosed material term. Under a two-stream pure-H2/native-air interpretation,
total mass change minus H change gives the signed required air term; remaining
element residuals are shown separately. Negative terms stay signed and can
denote required removal. They are not silently supplied to the native model.

Fine/coarse quadrature differences are retained independently of physical
failure. The radial cutoff is explicit; tail and order refinement remain
deferred gates. Selected stations do not establish unobserved-section closure;
`sampled_every_native_section` records whether every native output was audited.

## Radiation and unresolved energy

The visible-domain diagnostic records

\[
R_E=\mathcal E_{last}-\mathcal E_{entry}+\dot Q_{rad,native}.
\]

Native emitted power appears exactly once. Formation enthalpies already contain
chemical reference energy; LHV and reference reaction heat are not added again.
The shared one-mole H2 oxidation heat is retained as a separate caloric-reference
diagnostic, never a replacement flame law.

`R_E` is **unclosed net energy rate**, not an identified wall heat or an available
thermal correction. Material flux already fails, and lateral enthalpy, gravity,
pressure/flow work and a radiatively cooled flame energy equation are missing.
The result also records each element's energy-reference sensitivity coefficient
Delta(element flux)-Delta(total mass flux)*ambient element fraction (kg/s).
Multiplying it by an elemental enthalpy-zero shift (J/kg-element) gives the
change in this energy residual (W). Thus material nonclosure can make a supposed
"heat correction" depend on the reference gauge; that is diagnosed, not used to
choose a convenient zero or repair the field.
`required_heat_input_w` therefore remains `None` and
`gravitational_and_pressure_work_resolved` is false. No scalar subtraction from
temperature or radiant power is used to manufacture closure.

`held_steady_window_budgets` multiplies recorded rates by the caller's existing
finite established-steady window. These are conditional integrals, not finite
reservoir/blowdown, ignition, transit-time or source-duration predictions.

The original `HyRAMFlameRun.irradiance` owns all radiation calls. For an original
rejected flame the user must still explicitly request diagnostic radiation.
`auditor.bind_native_radiation(result, radiation)` only binds an existing result
of that same flame, checks original owner-issued conservation correspondence
and raw native flux/cache agreement, and retains it. It does not rerun or copy
the kernel. The binding's `accepted` is always false, even if the original
radiation kernel gates pass. Incident scalar irradiance is not specified-normal
absorbed or signed equipment heat.

`result.accepted` is always false; `require_accepted()` raises with the original
native flame and diagnostic result attached. A cloned/changed conservation
cache cannot be bound as original owner-issued evidence. These are validity
guards, not a security boundary against deliberate private-state tampering.

## Why the accepted gap remains open

Static source inspection confirms that native reacting Flame takes the Gaussian
entry from the nonreacting developing-flow establishment. Its public
`from_developed_flow(..., chem=...)` exists, but native chemistry metadata uses
`Preac` while Flame initialization/length reads `P`; an exception path can
recreate default chemistry. The recorded density-derivative and caloric-table
defects remain, and native radiation is postprocessed without a corresponding
energy sink. Changing one width or reference constant would not repair these
independent contracts.

A future native extension must expose a source-matched reacting establishment
solve with separate total/fuel/element mass, momentum and common-reference
enthalpy/kinetic budgets; stable documented chemistry metadata/injection;
consistent direct/derivative/interpolated thermodynamics with fit/error bounds;
and the original solver status/trials. It must distinguish adiabatic geometry
plus radiation postprocessing from a fully radiating energy equation with signed
lateral material/enthalpy and gravity/pressure-work terms. The existing strict
acceptance gates must be rerun on that reviewed engine revision. The detailed
contract is in the development report; no receiving repository was modified.

## Evidence and examples

The [authored example](../examples/jet_fire_conservation.py) defines a 500 K
source/310 K ambient diagnostic fixture, not a repair or replay of the earlier
300 K source failures. It uses actual separately installed Cantera species from
`nasa_gas.yaml` through native APIs, with the five selected fits bounded at
200–6000 K. The original GRI N2 fit starts at300 K, so it is not silently
extrapolated for a cold expanded source. The new fixture and every native API
assumption remain unexecuted. A native domain failure is an admissible retained
failure, not a reason to alter temperatures to force acceptance.

The [six deferred cases](../validation/cases/jet_fire_conservation.py) cover
retained rejection, order/tail quadrature, caloric-domain failure, method/source
binding, diagnostic radiation, and energy/reference bookkeeping without heat
identification. These are future compatibility/numerical diagnostics, not H2
flame validation or facility fire qualification.

Primary sources: [official Sandia HyRAM+](https://hyram.sandia.gov/),
[official native source](https://github.com/sandialabs/hyram),
[HyRAM technical reference](https://doi.org/10.2172/2563814),
[Cantera native thermodynamics](https://cantera.org/3.2/python/thermo.html), and
[NASA TM-4513](https://ntrs.nasa.gov/citations/19940013151) for the separately
installed species thermochemistry. The existing HyRAM GPL-3.0-only and Cantera
BSD-3-Clause owners stay separate; no native code, mechanism, coefficient table
or third-party worked example is bundled by this increment.
