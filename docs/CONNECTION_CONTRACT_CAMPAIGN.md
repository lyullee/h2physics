# Module-connection checks — 2026-11-02

## Latest user scope — basic connection checks only

The user narrowed this stage after the recorded executions. Further deep connection, mutation-hardening, precision, full-chain or external-engine qualification campaigns are stopped. Basic acceptance is successful producer-output delivery to the next API with compatible units, material identity and clock support. The already-executed57-case campaign includes deeper checks and is retained as historical evidence; it must not be relabeled as57 basic-only checks. No further computation or optional interface extension is required to close this stage. Remaining blocked or unavailable paths are recorded, not expanded into new work.

This stage sends genuine calculated producer outputs into existing receiving APIs. It checks material identity, SI units, phase and energy references, clock support, transfer ledgers and result ownership. It does not independently validate existing engines' internal physics or certify an integrated facility. The scope is the same78 topic families used in the previous campaigns; previous native-physics exclusions are not applied to host handoffs.

## Results

57 final cases passed with zero failures/errors/skips in the selected final batch:55 positive producer/consumer cases and2 genuine rejected-boundary cases. A case can connect several families. All78 families were classified as follows; native failures retained outside the healthy batch are not converted to passes.

| Family status | Count |
| --- | ---: |
| Selected normal connection passed | 72 |
| Rejection boundary only | 2 |
| Blocked or unavailable external execution | 2 |
| Terminal result with no existing selected consumer | 2 |

Normal connection coverage is72/78 (92.3%) of this topic list, not overall project completion or model validation.74 families have some passing connection-related check if the2 rejection-only boundaries are included; that must not be described as74 normal handoffs.

| Lane | Passing cases | Scope |
| --- | ---: | --- |
| Equipment/storage | 21 |27own families plus a facility-network handoff; underground remains blocked |
| Production/materials | 11 |15own families;2 terminal outputs have no existing selected consumer |
| Safety/facility | 25 |23positive cases and2rejection gates; facility-network coverage comes from equipment lane |

Examples of actual paths include finite tank/line transfer into product delivery and sensor input; adsorption into finite hydride storage; hydride withdrawal into compressor input; optical input into finite chemical conversion; calculated material flux into an interval source; concentration into radial stress; native shock into a reactor; real pool/impact outputs into finite pool/fire and exposure interfaces; native turbine/compressor maps into a Brayton point; HELPR failure into a fragment-flight boundary. Each row below names its tested path; these are selected handoffs, not complete networks of all optional model levels.

## Boundaries, blockers and terminal outputs

| Family | Actual outcome | Follow-up |
| --- | --- | --- |
| combustion.jet_fire | The selected genuine native flame/radiation baseline is refused; downstream admission also refuses it. No accepted jet-to-exposure path is claimed. | Find an admitted source/native operating point and rerun the handoff; preserve the refusal evidence. |
| dispersion.outdoor | A fresh process actually loads the qualified SciPy1.16.3/HyRAM runtime. The selected native result is refused by existing gates, so its finite-source consumer refuses it. | No version spoofing, synthetic plume or guard relaxation. An admitted native result is needed for a positive handoff. |
| storage.underground | Real uh2sc initialization forwards a one-element root array to CoolProp8's scalar update. No accepted native withdrawal can be issued. | [Receiving-engine request038](../requests/038_uh2sc_coolprop_scalar_compatibility.md); failed receipt equipment-frozen.xml/log is retained. |
| dispersion.obstacle | No genuine FDS runtime/output was available. Export-only or fake field output is not a passing connection. | Supply an actual supported FDS executable and run the receiving-field path. |
| production.biological | Current BiologicalRun is a terminal result; no existing downstream consumer was found in the source inventory. | No extra interface was invented for this campaign. |
| production.gasification | Current multiphase equilibrium output is a terminal result; no existing downstream consumer was found. | Its standalone calculation is not miscounted as a handoff. |

## Product repairs

Eight host source files were corrected; external solver code was not patched.

| Source | Correction and check |
| --- | --- |
| adapters/facility_consequence.py | Stable semantic code fingerprints replace marshal intern-state-sensitive hashes. Class configuration snapshots ignore temporary mappingproxy identities but detect method/default/closure changes, including captured normal/static/class methods.8focused regression cases pass. |
| storage/adsorption_dynamics.py | A bound callback retains its actual function and owner configuration rather than ephemeral method/metaclass wrapper identity. Genuine adsorption output remains current. |
| storage/finite_hydride.py | Native reflash fields can differ by a few ulps; numeric comparison uses relative1e-12 and zero absolute tolerance, with exact basis/phase/quality/capability checks. A separate issued-state content hash still rejects post-issuance changes, including5e-13pressure changes. |
| adapters/adsorption_finite_hydride_port.py | The same numerical P/T reflash tolerance admits an unchanged native source; independent state-content hashes retain exact post-issuance mutation detection. Wrong material/reference/clock and1%wrong states remain rejected. |
| adapters/cantera_fuel_cell.py | Cantera callback buffers require indexed scalar writes; assigning Python lists to their slices failed during actual native RHS execution. Actual synchronized channel/stack coupling passes. |
| adapters/diffusion_finite_source.py | Admission and recheck both recognize the explicit Hydrogen/H2 aliases and gas/supercritical_gas phase family. Actual CoolProp H2 passes; nitrogen and liquid are rejected. The original basis and caloric reference are retained. |
| materials/radial_thermoelastic.py | Free-axial BVP states contain an extra axial state. Displacement/derivative extraction and boundary stress evaluation now select the intended first two components. Actual diffusion-to-stress and existing eigenstrain checks pass. |
| combustion/turbine_map.py | Restore unreachable component-map seal initialization and place point-currentness on TurbineMapPoint. Actual native cycle input, fresh map/point acceptance and changed-map/point refusal pass. |

## Retained numerical and admission limits

The original broad radial stress reference case still fails its field-accuracy assertions at its default solver tolerance1e-7; it is not reported as a pass. Separate explicit1e-10free/fixed runs meet the same reference assertions (maximum radial errors0.00233/0.00808Pa). Existing hydrogen-eigenstrain free/fixed/history regression passes. This numerical-accuracy diagnostic is distinct from the passing selected module handoff.

The original broad engine interval crossed native trial-clock/volume admission limits. The final interface case explicitly provides wider input support, a short crank interval and tighter native solver settings; no production gate was relaxed. The original deposited pool dried out and was correctly marked input-limited; the accepted test uses a caller-declared smaller footprint. The accepted HELPR-to-fragment case uses explicit already-overlimit initial loading; a refined-root baseline that did not carry a failed flag remains refused. These selected cases do not qualify full operating ranges.

## Execution evidence and reproduction

The final safety lane was already running when the final equipment and production processes were launched. All three worked concurrently; its56.35sresult was reused instead of starting a duplicate safety job. The877pinned authored Python files still match after all lanes finish. Equipment/production have a root pre/post source pin. Safety has start/mtime and completion hashes matching that same frozen source; a separate global hash snapshot before safety start was not captured. See combined-run.json, final-pin/run.json and safety-run.json for the exact distinction.

Source-affected focused regression evidence is retained separately and is not added to the57connection cases: callback-regression-final.xml(8passed), equipment-seal-fixed.xml(3passed), equipment-regression.xml(1passed), and the production radial/eigenstrain diagnostics. Original failed/interrupted receipts remain preserved. The previous input, nominal and extreme records refer to their recorded source revisions; this campaign does not relabel them as new replays.

Use the existing h2physics-py312environment and the reviewed native-provider installations:

```powershell
python scripts/run_extreme_contracts.py --stage connection --output-dir artifacts/connection-contracts-20261102/replay
python scripts/summarize_connection_contracts.py artifacts/connection-contracts-20261102/replay/equipment_storage.xml artifacts/connection-contracts-20261102/replay/production_materials.xml artifacts/connection-contracts-20261102/replay/safety_facility.xml --output artifacts/connection-contracts-20261102/replay/summary.json
```

The output directory must be empty. The historical runner filename is retained for backward compatibility; --stage selects the contract campaign. It runs separate processes with one numerical-library thread each, no automatic pytest plugins and Agg plotting. Native packages, optional runtime files and their own licenses remain separate from public source distribution. The outdoor case uses its genuine isolated qualified runtime; the main environment is not downgraded.

## All78family classifications

| Family | Status | Selected producer to consumer |
| --- | --- | --- |
| `combustion.detonation` | normal_connection_passed | SDToolboxDetonation.frozen_shock → CanteraGas.closed_reactor |
| `combustion.equilibrium` | normal_connection_passed | CanteraGas.free_flame → premixed_reference / run_material_front |
| `combustion.flash_fire` | normal_connection_passed | CanteraGas.free_flame → premixed_reference / run_material_front |
| `combustion.gas_turbine` | normal_connection_passed | compressor/turbine map interpolation → run_map_matched_brayton |
| `combustion.jet_fire` | rejection_boundary_only | actual HyRAM flame/radiation → incident_history_from_hyram_radiation |
| `combustion.kinetics` | normal_connection_passed | CanteraGas.closed_reactor → evaluate_cantera_species_alarm; SDToolboxDetonation.frozen_shock → CanteraGas.closed_reactor |
| `combustion.laminar_flame` | normal_connection_passed | CanteraGas.free_flame → premixed_reference / run_material_front |
| `combustion.overpressure` | normal_connection_passed | HyRAMBauwensOverpressure.evaluate → pressure_peak_from_hyram_overpressure |
| `combustion.piston_engine` | normal_connection_passed | OpenCylinder native gas/geometry → finite CylinderWallThermal |
| `combustion.pool_fire` | normal_connection_passed | FiniteSurfaceImpact.run → run_deposited_batch_pool / PoolFireSeed; FinitePoolFire.run → HyRAMExposure / run_thermal_target / ConditionalHarmBinding.from_exposure |
| `dispersion.buoyant_layer` | normal_connection_passed | run_two_vent_hydrogen_layer → evaluate_buoyant_layer_h2_alarm; project_layer_oxygen → evaluate_layer_oxygen_deficit_alarm |
| `dispersion.compartment_network` | normal_connection_passed | simulate_hydrogen_compartment_network → sensor/alarm public APIs |
| `dispersion.enclosure` | normal_connection_passed | CanteraOpenGasVolume.run → bind_cantera_gas_volume_vent; CanteraOxygenRoom.run → evaluate_oxygen_deficit_alarm |
| `dispersion.obstacle` | not_executed_missing_native_fds_runtime | See boundary/blocker/terminal table above |
| `dispersion.outdoor` | rejection_boundary_only | DispersionScenario.run with actual HyRAM → project_hyram_jet_to_finite_source |
| `effects.cryogenic` | normal_connection_passed | project_layer_oxygen → evaluate_layer_oxygen_deficit_alarm; CanteraOxygenRoom.run → evaluate_oxygen_deficit_alarm |
| `effects.exposure` | normal_connection_passed | FinitePoolFire.run → HyRAMExposure / run_thermal_target / ConditionalHarmBinding.from_exposure; HyRAMBauwensOverpressure.evaluate → pressure_peak_from_hyram_overpressure; actual HyRAM flame/radiation → incident_history_from_hyram_radiation |
| `effects.fragment_trajectory` | normal_connection_passed | bound_fragment_speed_from_elastic_energy → run_elastic_bound_fragment_flight; HelprVesselFailure.predict → run_vessel_failure_fragment_flight |
| `effects.heat_input` | normal_connection_passed | FinitePoolFire.run → HyRAMExposure / run_thermal_target / ConditionalHarmBinding.from_exposure |
| `effects.rupture` | normal_connection_passed | HelprVesselFailure.predict → run_vessel_failure_fragment_flight |
| `equipment.compressor` | normal_connection_passed | accepted native tank source → Lh2dtCompressorStage.evaluate; accepted finite hydride withdrawal → actual compressor runs + bind_finite_hydride_to_compressor |
| `equipment.gas_pipe` | normal_connection_passed | CoolProp real-gas finite linepack withdrawal → fuel cell feed conditioning adapter |
| `equipment.gas_tank` | normal_connection_passed | actual finite two-tank run → product_delivery_from_finite_transfer; accepted native tank source → Lh2dtCompressorStage.evaluate |
| `equipment.heat_exchanger` | normal_connection_passed | actual two-side finite heat exchanger → wall_transfer_series |
| `equipment.instrument` | normal_connection_passed | computed finite receiver tank pressure → Lh2dtTransmitter.run |
| `equipment.insulation` | normal_connection_passed | actual native insulation heat → layered tank wall callback and inventory reader |
| `equipment.lh2_tank` | normal_connection_passed | native finite tank/pump/pipe/vaporizer → shared supply network + accepted inventory/rate ledgers; actual native insulation heat → layered tank wall callback and inventory reader |
| `equipment.pump` | normal_connection_passed | native finite tank/pump/pipe/vaporizer → shared supply network + accepted inventory/rate ledgers |
| `equipment.relief` | normal_connection_passed | owner-issued relief withdrawal ledger → finite source handoff |
| `equipment.reliquefier` | normal_connection_passed | actual native steady reliquefier → FiniteReliquefierProduct.collect_steady |
| `equipment.two_phase_pipe` | normal_connection_passed | native finite tank/pump/pipe/vaporizer → shared supply network + accepted inventory/rate ledgers |
| `equipment.valve` | normal_connection_passed | native finite tank/pump/pipe/vaporizer → shared supply network + accepted inventory/rate ledgers; actual finite two-tank run → product_delivery_from_finite_transfer |
| `equipment.vaporizer` | normal_connection_passed | native finite tank/pump/pipe/vaporizer → shared supply network + accepted inventory/rate ledgers |
| `equipment.vent` | normal_connection_passed | actual native vent and shared hydraulic transfer → FacilityContinuityAudit.audit |
| `facility.detector_reliability` | normal_connection_passed | evaluate_kofn_detector_reliability → native RiskInput / risk.risk |
| `facility.isolation` | normal_connection_passed | evaluate_concentration_alarm → schedule_alarm_valve_isolation |
| `facility.monitoring` | normal_connection_passed | CanteraGas.closed_reactor → evaluate_cantera_species_alarm; run_two_vent_hydrogen_layer → evaluate_buoyant_layer_h2_alarm; project_layer_oxygen → evaluate_layer_oxygen_deficit_alarm; CanteraOxygenRoom.run → evaluate_oxygen_deficit_alarm; evaluate_concentration_alarm → schedule_alarm_valve_isolation; simulate_hydrogen_compartment_network → sensor/alarm public APIs |
| `facility.network` | normal_connection_passed | actual native vent and shared hydraulic transfer → FacilityContinuityAudit.audit |
| `facility.risk` | normal_connection_passed | FinitePoolFire.run → HyRAMExposure / run_thermal_target / ConditionalHarmBinding.from_exposure; evaluate_hyram_ignition_probability → bind_hyram_ignition_to_risk; evaluate_kofn_detector_reliability → native RiskInput / risk.risk |
| `materials.diffusion` | normal_connection_passed | PowerLawSolubility/steady_permeation/DiffusionSlab → source_from_diffusion_result; DiffusionDomain.simulate → radial_hydrogen_eigenstrain_cylinder |
| `materials.integrity` | normal_connection_passed | DiffusionDomain.simulate → radial_hydrogen_eigenstrain_cylinder |
| `materials.permeation` | normal_connection_passed | PowerLawSolubility/steady_permeation/DiffusionSlab → source_from_diffusion_result |
| `materials.solubility` | normal_connection_passed | PowerLawSolubility/steady_permeation/DiffusionSlab → source_from_diffusion_result |
| `production.biological` | terminal_result_no_existing_consumer | See boundary/blocker/terminal table above |
| `production.electrolyzer` | normal_connection_passed | PhotovoltaicElectrolysis.run → charge_linepack_from_electrolysis; HydrogenStack.evaluate → UncertainModel/propagate/PropagationResult.summarize |
| `production.energy_coupling` | normal_connection_passed | PhotovoltaicElectrolysis.run → charge_linepack_from_electrolysis |
| `production.fuel_cell` | normal_connection_passed | Cantera native channel state → run_cantera_synchronized_fuel_cell |
| `production.gasification` | terminal_result_no_existing_consumer | See boundary/blocker/terminal table above |
| `production.microbial_cell` | normal_connection_passed | FiniteMicrobialCell.run → MicrobialCostProjection/price_window |
| `production.photo` | normal_connection_passed | PhotonSupply/PhotoRate → run_photochemical_operation/StoichiometricReaction |
| `production.reforming` | normal_connection_passed | CanteraCatalyticSurfaceReactor.run → CanteraCatalyticWallHeatAdapter/HeatDuty |
| `production.thermochemical` | normal_connection_passed | FiniteThermochemicalCycle.run → FiniteSolidReactionReactor.run |
| `release.blowdown` | normal_connection_passed | CanteraOpenGasVolume.run → bind_cantera_gas_volume_vent |
| `release.droplets` | normal_connection_passed | run_parcel_population → impact_population_member |
| `release.gas` | normal_connection_passed | HomogeneousIsentropicNozzle.solve → SourceHistory.interval_mass_projection / IntervalMassSource.rebin; HomogeneousIsentropicNozzle.solve → expand_nozzle_gas / axisymmetric_boundary; DispersionScenario.run with actual HyRAM → project_hyram_jet_to_finite_source |
| `release.impact` | normal_connection_passed | run_parcel_population → impact_population_member; FiniteSurfaceImpact.run → run_deposited_batch_pool / PoolFireSeed |
| `release.liquid` | normal_connection_passed | HomogeneousIsentropicNozzle.solve → SourceHistory.interval_mass_projection / IntervalMassSource.rebin; run_parcel_population → impact_population_member |
| `release.near_field` | normal_connection_passed | HomogeneousIsentropicNozzle.solve → expand_nozzle_gas / axisymmetric_boundary |
| `release.two_phase` | normal_connection_passed | HomogeneousIsentropicNozzle.solve → SourceHistory.interval_mass_projection / IntervalMassSource.rebin |
| `research.economics` | normal_connection_passed | FiniteMicrobialCell.run → MicrobialCostProjection/price_window |
| `research.uncertainty` | normal_connection_passed | HydrogenStack.evaluate → UncertainModel/propagate/PropagationResult.summarize |
| `separation.membrane` | normal_connection_passed | CanteraFiniteMembraneDevice.run → bind_cantera_membrane_thermostat_heat |
| `separation.psa` | normal_connection_passed | PsaDynaCycle.run → audit_adsorption_cycle |
| `storage.adsorption` | normal_connection_passed | computed CoolProp-backed adsorption dynamics → bind_adsorption_to_finite_hydride + FiniteHydrideBed |
| `storage.adsorption_thermal` | normal_connection_passed | computed CoolProp-backed adsorption dynamics → bind_adsorption_to_finite_hydride + FiniteHydrideBed; genuine accepted finite bed and admitted adsorption callbacks → trace/input require_current guards |
| `storage.carrier_reaction` | normal_connection_passed | completed carrier reaction actual prewithdrawal → receiver CarrierConversion.run |
| `storage.cryo_compressed` | normal_connection_passed | native cryo tank relief integration → cryo state and energy audit |
| `storage.hydride_compressor` | normal_connection_passed | finite hydride bed and actual native source/receiver vessels → HydrideThermalCompressor.run |
| `storage.hydride_dynamic` | normal_connection_passed | computed CoolProp-backed adsorption dynamics → bind_adsorption_to_finite_hydride + FiniteHydrideBed; accepted finite hydride withdrawal → actual compressor runs + bind_finite_hydride_to_compressor; genuine accepted finite bed and admitted adsorption callbacks → trace/input require_current guards |
| `storage.hydride_equilibrium` | normal_connection_passed | computed CoolProp-backed adsorption dynamics → bind_adsorption_to_finite_hydride + FiniteHydrideBed |
| `storage.microsphere` | normal_connection_passed | CoolProp finite cavity state → shared spherical DiffusionDomain + cavity feedback |
| `storage.porous_reservoir` | normal_connection_passed | computed CoolProp-backed porous pressure history → Lh2dtTransmitter.run |
| `storage.solid_reaction` | normal_connection_passed | completed finite solid reaction → HeatDuty.bind + SolidReactionHeatAdapter |
| `storage.underground` | blocked_external_native_compatibility | See boundary/blocker/terminal table above |
| `surface.pool` | normal_connection_passed | FiniteSurfaceImpact.run → run_deposited_batch_pool / PoolFireSeed |
| `thermo.mixtures` | normal_connection_passed | actual CoolProp mixture dew-endpoint partition → MixtureInventoryStateAdmission |
| `thermo.pure_fluid` | normal_connection_passed | actual finite two-tank run → product_delivery_from_finite_transfer |
| `thermo.spin` | normal_connection_passed | actual native spin kinetic state → thermostat enthalpy calorimeter |

## Next scope

No new whole-system regression or complete end-to-end campaign was started. Remaining work is the explicit rejected/blocked paths above and any separately requested subsequent stage; no independent validation of existing engines has been added.
