# Native PV/direct-DC electrolysis — implemented, unverified

## Optional finite thermal trace handoff

`h2physics.adapters.bind_electrolysis_thermal_operation()` admits a completed
`PVElectrolysisTrace` beside a completed `FiniteThermalStack` result when both
retain the exact same `HydrogenStack`. It checks each electrolysis interval,
clock, current, caloric reference, declared temperature tolerance and generated
heat against the producer's retained stack heat row. The returned typed receipt
checks freshness of both original results.
The receipt also has one-use issuance and a content seal over both object
identities, the evidence ID, both admission tolerances, the residual and the
captured thermal signature. Direct construction, cloning and edits to those
receipt fields invalidate it.

This is post-run compatibility accounting. It does not alter PV load-line or
hydrogen calculations, feed changing stack temperature back into production,
or resolve heat-utility availability. The tolerance and boundary evidence are
caller supplied; the authored deferred case remains unrun.

`h2physics.adapters.pv_electrolysis.PVElectrolysis` connects an actual optional
pvlib 0.16.1 PVSystem to the existing HydrogenStack polarization/Faraday core,
shared finite stoichiometry and a native H2 receiving inventory. **Status:
implemented_unverified.** No local pytest, validation replay, benchmark or
native production calculation was executed for this increment. Execution is
deferred to the user's Nurion validation workflow.

This is direct DC with ideal wiring and an explicit one-way blocking/isolation
policy. It is not MPPT, an AC inverter, an AC/DC rectifier or a constant
electricity-to-hydrogen efficiency approximation. Native PV I–V and shared
electrochemical voltage determine a coupled operating current.

## Native and shared ownership

- pvlib owns DeSoto parameters, single-diode I–V/MPP and current-at-voltage.
  The actual PVSystem, native parameter tuple, raw I–V object, scaled native
  DataFrame and generic coupling-root result are retained.
- HydrogenStack owns reversible/thermoneutral voltages, supplied polarization
  losses, electricity, Faraday hydrogen rate and isothermal reaction duty.
- StoichiometricReaction.convert owns finite H2O→H2+0.5O2 conversion and
  element/charge/mass consistency. Its reported roundoff correction remains
  inspectable; no additional inventory clipping is introduced.
- The existing HydrideGasThermodynamics contract supplies actual native gas
  EOS flashes. Despite that contract's historical name, its pure-H2 property
  functions are reused directly without a hydride model or new EOS.
- An existing MolarEnthalpyProvider supplies the same ordered reaction species
  and a common formation/caloric reference. The adapter does not invent
  liquid-water/oxygen property functions.

The original optional pvlib wheel and notices remain in a separate ignored
target. No native source, SAM/module database or external numerical dataset
is bundled. [pvlib_dependency.toml](../research/pvlib_dependency.toml) records
the reviewed artifact, license and native source hashes. Source inspection and
installation do not establish runtime compatibility or physics verification.
Importing this adapter does not import pvlib or CoolProp.

## Python objects and source boundary

Construct `NativePV.from_installed()`, then pass an actual single-array
`pvlib.pvsystem.PVSystem`, the existing HydrogenStack, reaction, caloric
provider and native gas thermodynamics to PVElectrolysis. Parameters and
physical callbacks stay caller-owned. Selected native method/function and
instance bindings, source bytes and admitted model definitions are guarded.
Arbitrary callbacks must remain stable during a campaign; the adapter cannot
prove the physical meaning or purity of arbitrary user code.

`PVStage` explicitly supplies a finite absolute interval, clock/source IDs,
effective irradiance W/m2, prescribed PV-cell K, prescribed stack K and origin.
Cell K is converted to native Celsius only at the pvlib boundary. Effective
irradiance already includes the caller's optical/spectral/soiling assumptions.
No location, weather, irradiance or cell temperature is inferred from plant kW.
Each stage holds its supplied conditions and solved current over its duration;
the implementation has no continuous weather, pressure or temperature feedback.

For sampled inputs, `PVBoundaryProfile` accepts typed time/irradiance/cell-
temperature knots with source identities. `stages()` linearly interpolates
within each adjacent knot pair and evaluates the midpoint of each caller-sized
subinterval. A required `maximum_gap_s` prevents silently filling a wider gap;
no extrapolation is performed. The profile retains clock and origin, plus the
two original knot identities in the immutable `PVStage.source_ids` tuple. The
older joined `source_id` text remains available for compatibility. Midpoint subdivision
integrates the linearly interpolated input exactly, while the nonlinear PV and
stack response remains a numerical quadrature that should be refined for the
chosen data. Stack temperature and enabled/isolated state remain caller inputs.
This is a sample-and-hold forcing convenience, not a weather model, thermal
state solver, MPPT controller, or continuous feedback system.

Each run requires unique `PVStage.identifier` values across its complete source
schedule. Duplicates are rejected before the first native load-line or receiver
calculation so trace rows and ledger entries cannot share an ambiguous stage
key. This checks lineage uniqueness only; it does not authenticate
caller-supplied source identifiers or measurements.

The module/reference parameters and integer series/parallel topology must be
explicit. The parameter domain includes irradiance, temperature, array
voltage/current, stack current density and receiver pressure/mass limits.
Native array scaling is retained. A positive infinite shunt resistance is
admissible at a native dark limit; an invalid native I–V output is preserved
as a failure rather than repaired into a successful zero-power result.

`operating_point(stage)` solves
I_PV(V_stack(j)/PV_series)×PV_parallel = j×cell_area
using native current-at-voltage and HydrogenStack.evaluate. A sampled
monotonic-branch admission and bounded generic root are used. The sampling is
not a proof of uniqueness between samples; callers must qualify the supplied
polarization branch/domain. No copied diode or electrochemical equation is
used by the coupling root.

For an isolated, dark or insufficient-voltage source, an explicit open/off
state produces zero external current and hydrogen. The load-line residual is
None because the disconnected nodes do not share a load-line equation.
Numerical bracketing probes can lie outside the generating branch; they are
retained as probes. An accepted connected root must be inside the generating
branch and satisfy the declared current and integrated DC energy residuals.
Undrawn MPP headroom is retained as unused availability, not conversion heat.

The authored [example](../examples/pv_electrolysis.py) defines `build_model`,
`source_stages` and `run_example`. These functions are available for the
later worker to invoke; they have not been run locally. Example diode,
polarization and caloric parameters are synthetic and have no manufacturer
qualification or measured calibration.

## Finite chemistry, receiver and energy coordinate

`run(stages, initial_amounts_mol=..., receiver_volume_m3=...,
receiver_temperature_k=...)` advances finite source stages. Water, H2 and O2
amounts are mol. Initial H2 must explicitly seed a positive native receiver
state; vacuum is not replaced with an ideal-gas guess. The receiver has fixed
volume and prescribed temperature, with actual native P/U/phase snapshots.
Only gas/supercritical-gas H2 states are admitted.

Water and oxygen are finite **isothermal/isobaric enthalpy stocks** at the
declared production pressure. Their vessel volume, pressure dynamics and
thermal capacitance are not solved. Stack temperature must remain constant
within this finite reference campaign; temperature conditioning is a separate
physical requirement.

Generated H2 is a controlled inlet at the explicitly declared product
pressure, temperature and native enthalpy. Both receiver endpoints must be
below the source pressure when material is delivered. This is an ideal
controlled material port, not a solved nozzle/valve/compressor.

`ProductPressureBoundary` records whether that pressure/activity basis is
actually included in the supplied reaction Gibbs energy. Without that basis,
the model is a declared pressurized-source requirement; additional pressure
support/work remains unresolved and `required_external_pressure_work_j=None`.
No free pressurization or zero required work is inferred. The example openly
uses this unresolved-pressure status. A pressure-head check alone is not an
electrochemical pressure-work model.

ReactionEnergy's reference ID, water phase and deltaH must match the caloric
provider. Provider H2 molar enthalpy must match native inlet h×molar_mass on
the actual gas reference. No reference offset is silently fitted. Finite heat
closure currently requires eta_F=1; the shared core's unknown parasitic
chemical/thermal fate at lower Faradaic efficiency is rejected.

For each held interval:

- Stack electricity minus stack heat rejection equals reaction deltaH.
  Negative heat rejection means required stack heat input.
- Receiver heat into the inventory equals receiver deltaU minus incoming H2
  material enthalpy.
- The recorded combined coordinate is deltaH_water/O2 + deltaU_H2receiver.
  Its external heat is −stack_heat_rejected + receiver_heat_into.

The H2 transfer enthalpy cancels once when these boundaries are combined.
Reaction deltaH is not added again as heat after counting the same product
enthalpy. The coordinate uses nonreceiver enthalpy and receiver internal
energy; it is not total U of three rigid vessels. Pressure displacement work
in the isobaric stocks belongs to their enthalpy convention. The output
therefore keeps `full_plant_energy_closed=False`,
`water_oxygen_vessel_dynamics_solved=False` and
`thermal_utility_availability_solved=False`.

Required signed duties are returned, not a predicted cooling/heating utility
capacity. No new thermal ODE or artificial electrolyzer wall is introduced.
Finite water depletion, pressure limits, missing heat fate, reference mismatch
or unavailable root fail with the completed prefix and attempted native
objects/results retained. A failed interval is not silently shortened or
replenished; future depletion-event support would be a distinct extension.

## Deferred execution and current evidence

[validation/cases/pv_electrolysis.py](../validation/cases/pv_electrolysis.py)
defines eleven deferred cases through the common ValidationCase/ValidationOutcome API.
Module import and `cases()` construct metadata only. Actual native model
construction and calculations occur only when a future worker invokes a
validation entrypoint.

The definitions cover native load-line/Faraday/finite ledgers, dark/isolation,
unavailable root, water depletion, delivery-pressure and receiver-domain
failures, missing Faradaic heat fate, held-stage refinement and caloric
reference mismatch, producer-result admission, and bounded-profile/midpoint
forcing. These are **not passing-test claims**. Native result shapes,
dark behavior, load-line conditioning, runtime compatibility and acceptance
budgets remain unexecuted gates. Additional measured validation remains open.

The acquired PV/PEM dispatch figures contain reconstructed/simulated power and
H2 summaries, without an admitted weather/module/inverter/thermal parameter
set. Dryad PEM/grid attachments remain unacquired in the current receipt.
Neither is used here as independent PV/PEM validation.

Primary sources:
[official pvlib release](https://pypi.org/project/pvlib/0.16.1/),
[DeSoto native API](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.calcparams_desoto.html),
[single-diode native API](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.singlediode.html),
[current-at-voltage](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.i_from_v.html)
and the shared electrochemistry core's
[NREL water-electrolysis reference](https://www.nrel.gov/docs/fy23osti/83155.pdf).
The existing [reaction/inventory contract](THERMOCHEMICAL_CYCLES.md) and
[native finite gas scope](OPEN_GAS_VOLUME.md) remain separate resolved levels.

## Original-result admission increment

The producer now issues every successful trace with a weakly registered
`PVResultAdmission`. `trace.require_current()` admits only that exact original
trace, its retained native result tables and the current producer/source
bindings. A dataclass copy or reconstructed trace does not inherit admission.
The check reads stored content and definitions without replaying a diode,
electrochemical, EOS or caloric calculation; it is provenance evidence rather
than numerical validation. The source-neutral economics adapter requires this
producer check before and after its own structural quantity snapshot.

A tenth deferred case covers original trace admission and reconstructed-copy
rejection. It has not been executed.

An accepted finite production trace can also be mapped into the existing
isothermal pipeline inventory by
[`charge_linepack_from_electrolysis`](ELECTROLYSIS_LINEPACK.md). The handoff
requires matching H2 mass basis, clock, product/linepack temperature, and
sufficient source pressure. It adds no compressor or thermal solver and remains
unverified until its deferred Hangang case runs.
