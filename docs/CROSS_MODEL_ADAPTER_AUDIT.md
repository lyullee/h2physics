# Cross-model adapter static audit

**Scope:** source-level review of the cross-model handoffs in this workspace's
current safety, production and storage lanes. This audit checks package exports,
producer freshness checks, evidence/limit documentation, and deferred Hangang
case discovery. It does not execute a model, test, package import or cluster job.

## Reviewed handoffs

| Handoff | Public API | Freshness boundary | Deferred Hangang route |
|---|---|---|---|
| Electrolysis batch → fuel-cell inventory | `bind_electrolysis_to_fuel_cell` | Both native traces revalidated; molar identity and inventory closure replayed | `electrolysis-fuel-cell-single-batch-handoff` / `pv-electrolysis` |
| Compressor → finite mixture receiver | `bind_compression_to_mixture_receiver` | Compressor and receiver owners revalidated; interval and transfer mass reconstructed | `hydrogen-compression-finite-mixture-storage-handoff` / `mixture-vle` |
| HyRAM radiation/overpressure → exposure history | `incident_history_from_hyram_radiation`, `pressure_peak_from_hyram_overpressure` | Native field/result acceptance and source identity checked when snapshot is created | HyRAM exposure handoff cases / `jet-fire-conservation`, `hyram-overpressure` |
| Pool-fire radiation → exposure history | `exposure_history_from_pool_fire` | Original pool trace revalidated before projection; output is an immutable evidence-bound snapshot | `pool-fire-exposure-history-handoff` / `pool-fire` |
| Oxygen room → sensor/alarm | `evaluate_oxygen_deficit_alarm` | Room owner, sensor, alarm, aligned signal and trip evidence revalidated | `oxygen-room-deficit-detector-alarm-handoff` / `oxygen-deficiency` |
| Cantera reactor species → sensor/alarm | `evaluate_cantera_species_alarm` | Reactor trace, sensor and alarm revalidated; values are tied to source species and clock | `cantera-reactor-hydrogen-sensor-alarm-handoff` / `counterflow-flame` |
| Cantera catalytic wall → thermal duty | `CanteraCatalyticWallHeatAdapter` | `HeatDuty` revalidates the live native trace, wall and sampled energy ledger | `cantera-catalytic-wall-heat-utility-handoff` / `counterflow-flame` |
| Finite hydride → shared nozzle source history | `nozzle_history_from_hydride_trace` | Owner-issued trace and interval mass ledger are checked against declared closure tolerance | `finite-hydride-nozzle-source-handoff` / `finite-hydride` |
| Finite hydride → HELPR vessel loading history | `history_from_finite_hydride` | Trace rechecks its retained EOS state at each accepted pressure/time; HELPR use rebuilds the history from original snapshots and rejects altered loading rows | `finite-hydride-vessel-failure-history-handoff` / `finite-hydride` |
| PV electrolysis H2 batch → real-fluid compressor inlet | `bind_electrolysis_compressor_inlet` | Electrolyzer trace is revalidated, CoolProp basis/state is matched, and the declared interval withdrawal is bounded by net produced H2 | `pv-electrolysis-real-fluid-compressor-inlet-handoff` / `pv-electrolysis` |
| Synchronized Cantera fuel-cell coolant ledger → thermal duty | `bind_cantera_fuel_cell_coolant_heat` | Original native trace/currentness and exact accepted clock endpoints are checked; interval heat is differenced from the cumulative stack-coolant ledger | `cantera-fuel-cell-coolant-heat-duty-handoff` / `fuel-cell-native` |
| Evaporating parcel → finite vapor source | `vapor_source_from_parcel_trace` | Original parcel trace and finite source bins/state/clock/frame revalidated | `parcel-vapor-interval-source-handoff` / `droplet-transport` |
| Linepack withdrawal → finite source | `advance_linepack_to_source` | Issuer-bound receipt rechecks the original states, port ledger and exact source mass | `hydrogen-linepack-withdrawal-finite-source-handoff` / `gas-compressible-pipe` |
| Solid-reaction heat → thermal duty | `SolidReactionHeatAdapter` | `HeatDuty` snapshots the original trace/kernel/provider/steps; inventory enthalpy requires exact kernel-provider identity, ordered species and common basis before conservation budgets are applied | `solid-reaction-heat-utility-handoff` / `solid-reaction` |
| Solid-reaction H2 takeoff → finite source | `source_from_solid_reaction_hydrogen` | Original trace content digest and finite source fingerprint are revalidated; whole-system enthalpy requires exact kernel-provider identity, ordered species and common basis | `solid-reaction-hydrogen-finite-source-handoff` / `solid-reaction` |
| Slab diffusion outflow → finite H2 source | `source_from_diffusion_result` | Original `DiffusionResult` and source are revalidated; source bins are recomputed from outward integrated flux | `diffusion-outward-h2-finite-source-handoff` / `material-transport` |
| Dynamic adsorption H2 outlet → finite source | `bind_adsorption_dynamics_to_finite_source` | Original completed trace, single H2 species, exact bins and representative-state enthalpy budget are revalidated | `adsorption-dynamics-finite-h2-source-handoff` / `finite-adsorption-vessel` |
| Cantera gas-volume vent → finite H2 source | `bind_cantera_gas_volume_vent` | Frozen pure-H2 single-vent trace, native mass/species/energy residuals, original endpoint and same-mechanism state enthalpy are revalidated | `cantera-gas-volume-vent-finite-source-handoff` / `counterflow-flame` |
| BAM plate temperature → thermal-target observation comparison | `compare_bam_plate_temperature_to_target` | Source table/projection and target trace provenance are retained; comparison is observational and does not alter the target model | `bam-fire-plate-temperature-thermal-target-observation-bridge` / `thermal-target` |
| Hydrogen acoustic observations → CoolProp diagnostic | `compare_acoustic_file_with_eos` | Admitted source file, exact row and state-basis matching are retained; no fitting or extrapolation is used | `hydrogen-acoustic-source-to-coolprop-pointwise-diagnostic` / `source-data-ingestion` |

All named functions/classes are present in `h2physics.adapters` exports and
`__all__`. The deferred case modules are imported by
`validation/hangang_plan.py`; provider-specific cases retain their profile
requirements instead of silently falling back to a different model.

## Findings and boundaries

- Removed a duplicate `CanteraSpeciesAlarmHandoff` import and duplicate
  `__all__` registration. The API was already reachable; this removes duplicate
  package declarations.
- Removed a duplicated pool-fire exposure handoff paragraph from
  [NATIVE_EXPOSURE.md](NATIVE_EXPOSURE.md).
- HyRAM, pool-fire and linepack conversions are materialized snapshots: their
  source validity is checked at conversion, and output values/evidence are
  preserved. They do not promise that a later source mutation retroactively
  changes an already exported immutable snapshot.
- The diffusion source route carries mass only. The original diffusion result
  does not provide facility clock alignment, product gas EOS/energy state, or
  spatial outlet geometry; each projection is caller-evidenced. Atomic-H
  conversion to H2 requires a separate recombination declaration.
- Solid-reaction product export requires pure H2 withdrawal, matching native
  caloric reference and state enthalpy. Its handoff does not add a separator,
  pressure-control, nozzle or dispersion model.
- Finite hydride/nozzle agreement depends on a caller-declared closure budget;
  a mismatch is rejected without editing either native ledger.
- Finite hydride to HELPR is a pressure-history projection only. Wall
  temperature and geometry must be caller-mapped to the exact shell region;
  solid-bed temperature is not a vessel-wall field, and HELPR remains an
  optional external failure model.
- Electrolysis-to-compressor is a finite batch availability check; it assumes
  the caller-established inlet state remains available across the declared
  steady compressor window and does not model regulation or receiver depletion.
- Fuel-cell coolant HeatDuty preserves heat entering the stack from the
  prescribed coolant boundary; it is not an estimate of exportable waste heat
  or downstream utility supply.
- BAM plate-temperature comparison is a source-bound observation overlay, not
  a recalibration of the thermal target. The source archive/member and unit
  projection remain receipt-bound; no unmeasured plate boundary conditions
  are inferred.
- Hydrogen acoustic/EOS comparison is pointwise diagnostic only. Historical
  EOS training overlap is unresolved, so agreement is not independent EOS
  validation and is not used to fit or extend the EOS.
- The SOE fault-operation schema case and TiO2 AQY link-gap case are
  metadata/provenance contracts, not admitted physical-model handoffs. The
  former has no acquired MAT payload or channel schema; the latter lacks
  row-matched photon supply and yield-basis evidence. Their no-linkage status
  is recorded in the source manifests and qualification documentation.
- Dynamic adsorption outflow can be converted to finite H2 mass intervals
  only after the original completed trace is current and the caller supplies
  clock/state evidence whose single-state enthalpy projection fits a declared
  budget. This output boundary does not predict a valve or downstream release.
- No additional electrolysis-to-vessel inlet adapter is defined. The existing
  electrolysis-to-fuel-cell bridge closes an isolated H2 *molar batch* and
  explicitly requires separate transfer and conditioning evidence. The PV
  electrolysis trace's H2 receiver is represented by its retained native gas
  thermodynamics and fixed-volume internal-energy state, while the finite
  mixture vessel requires a CoolProp component mapping and inlet enthalpy
  expressed on the vessel template's energy-reference basis. A product amount
  alone cannot supply that stream enthalpy or prove transfer timing, pressure
  compatibility, heat/work, or conditioning. Reusing the compressor handoff
  would additionally assume a compressor stream that the electrolysis run did
  not calculate. Until a shared provider/reference and measured or modeled
  transfer boundary are available, linking these models would overstate energy
  closure; keep the native outputs separate and report only the existing batch
  molar reconciliation where its evidence is supplied.

No local tests/calculations or HPC dispatch were performed for this audit.

## Adsorption product to H2 linepack

`charge_linepack_from_adsorption_product` composes the accepted finite
adsorption-vessel H2 product-mass receipt with the lumped ideal-H2 linepack
inventory ledger. It requires exact product species selection, matching H2
molar-mass basis, and caller-mapped common interval evidence. It adds no
purification, compression, pressure-matching or transient-flow closure. The
deferred synthetic case is `adsorption-product-h2-linepack-charge-handoff`;
Hangang execution and physical process qualification are pending.

### Adsorption/linepack evidence requirement

The product-to-linepack adapter also requires a caller-supplied transfer-boundary
evidence identifier covering the external injection path and its pressure/
thermal interface. The identifier is not independently qualified by this
library.

## Adsorption outlet to finite-hydride inlet

`bind_adsorption_to_finite_hydride` reuses the accepted H2 interval outlet
ledger from `AdsorptionDynamicsTrace` and the existing
`FiniteHydrideGasPortBoundary`. It checks one caller-supplied gas state and
state-projection evidence per exact source interval, requires exact source-row
pressure/temperature, molar-mass and enthalpy closure, and requires caller-owned
clock/hydraulic evidence. It does not calculate line pressure loss, valves or
pressure evolution. The deferred
case `adsorption-to-finite-hydride-gas-port-handoff` is synthetic software
contract coverage only; execution and physical validation are pending.


## Reliquefier product to native separator inlet

`bind_reliquefier_product_to_separator` maps the owner-issued collected
all-liquid reliquefier product receipt to a native separator liquid
`MassEnergyFlow`, preserving product mass, enthalpy and exact collection
window. The caller must provide clock, receiving-region, and pressure/thermal
transfer-boundary evidence. The adapter does not calculate transfer hydraulics,
flashing or conditioning; its synthetic Hangang contract is not facility
qualification.

## Finite separator to HELPR vessel history

`history_from_finite_separator` projects exact accepted pure-H2 separator
pressure/time rows into the existing HELPR vessel-history API. Caller-supplied
shell-wall temperature, external absolute pressure, clock, geometry, and
pressure-basis mappings are retained and replayed during HELPR currentness
checks. No liquid temperature is used as a wall temperature and no failure,
breach, or release physics are added. The deferred case is synthetic interface
coverage only.

## HyRAM radiation to lumped thermal target

`incident_heat_history_from_hyram_radiation` composes accepted HyRAM observer
irradiance with the existing incident heat-history and lumped target APIs.
Target-surface mapping, any irradiance projection, target properties and
external heat-transfer evidence remain caller-owned. It adds no radiation,
view-factor or target solver. Its deferred case is synthetic interface
coverage, not target or fire qualification.
