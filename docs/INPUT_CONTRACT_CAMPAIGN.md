# Representative input-rejection campaign

Executed: 2026-11-02T17:09:49.097998+09:00.

**78/78 scoped families passed.** The final combined run passed 161 malformed-input cases and one family-manifest check: 162 passed, zero failures/errors/skips. Each family has at least two distinct malformed-input scenarios. Pytest reported 10.37 s; the retained enclosing process measured 12.20 s.

These are specific public input-object, parameter and pre-calculation checks. They do not cover every argument or prove physical accuracy, overflow safety for all numbers, successful full simulations, or complete validation of an external engine. Unit/basis checks apply where the API carries an explicit label; a number passed to an SI-named argument cannot reveal a caller’s unlabelled engineering unit.

Normal parameter baselines are constructed before mutation where supported. The malformed call must raise the relevant TypeError/ValueError and match its intended diagnostic. Dependency failures and unrelated errors are not passes. No skip or xfail is accepted.

The three nozzle input families use actual CoolProp gas, liquid and two-phase states. Four equipment families use the installed LH2DT parameter constructors; no tank/pipe/vaporizer simulation or native physical-prediction comparison is run. Other cases use the project’s public model input objects and early parameter guards.

## Reproduction

Use the research environment and the separately reviewed LH2DT installation at `artifacts/native_packages/lh2dt`. An unavailable dependency causes a failure rather than a skipped or fabricated pass. Set optional numerical-library thread counts to one and disable unrelated auto-loaded pytest plugins for this targeted campaign.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
python -m pytest -q --tb=short -o junit_family=xunit1 --junitxml=artifacts/input-contracts-20261102/all-78.xml tests/test_input_contract_equipment_storage.py tests/test_input_contract_production_materials.py tests/test_input_contract_safety_facility.py
```

## Retained results

- `artifacts/input-contracts-20261102/all-78.log`: final combined terminal output.
- `artifacts/input-contracts-20261102/all-78.xml`: individual test outcomes, family, API and malformed-input scenario.
- `artifacts/input-contracts-20261102/all-78-run.json`: command, clock, source hashes and unchanged-source result.
- `artifacts/input-contracts-20261102/coverage-78.json`: per-family executed-case reconciliation.

All 419 pinned project/native/test Python files were unchanged across the final run. Earlier split-run diagnostic-message mismatches are retained in the initial logs. Those inputs were already rejected correctly; test regular expressions were corrected. No production input guard was changed in this campaign. The executed files include earlier source changes without claiming their new physical behavior was verified.

## Executed families

| Family | Passed malformed inputs | Public input target(s) | Scenarios |
|---|---:|---|---|
| `combustion.detonation` | 2 | `h2physics.adapters.detonation.DetonationSettings` | sound_density_relative_step; native_jump_relative_tolerance |
| `combustion.equilibrium` | 2 | `h2physics.adapters.cantera.ReactiveState` | temperature_k; mole_fractions |
| `combustion.flash_fire` | 2 | `h2physics.adapters.flash_front.FrontAdmission` | low_temperature_progress; minimum_temperature_rise_k |
| `combustion.gas_turbine` | 2 | `h2physics.combustion.open_brayton.OpenBraytonInputs` | compressor_pressure_ratio; turbine_isentropic_efficiency |
| `combustion.jet_fire` | 2 | `h2physics.adapters.hyram_flame.SteadyFlameWindow` | end_s; source_evidence_id |
| `combustion.kinetics` | 2 | `h2physics.adapters.cantera.ReactiveState` | pressure_pa; mole_fractions |
| `combustion.laminar_flame` | 2 | `h2physics.adapters.cantera.FlameSettings` | width_m; transport_model |
| `combustion.overpressure` | 2 | `h2physics.adapters.hyram_overpressure.DetonableHydrogenEnergy` | participating_hydrogen_mass_kg; heat_of_combustion_j_kg |
| `combustion.piston_engine` | 2 | `h2physics.combustion.closed_charge_engine.SliderCrank` | connecting_rod_m; compression_ratio |
| `combustion.pool_fire` | 2 | `h2physics.adapters.pool_fire.PoolFireStage` | burning_flux_kg_m2_s; radiative_fraction |
| `dispersion.buoyant_layer` | 2 | `h2physics.buoyant_layer.TwoVentHydrogenLayerConfig` | source_height_m; upper_discharge_coefficient |
| `dispersion.compartment_network` | 2 | `h2physics.compartment_network.WellMixedCompartment` | volume_m3; initial_hydrogen_mole_fraction |
| `dispersion.enclosure` | 2 | `h2physics.adapters.cantera_volume.GasHeatBoundary` | area_m2; emissivity |
| `dispersion.obstacle` | 2 | `h2physics.adapters.obstacle_dispersion.CFDMesh` | cells; bounds_m |
| `dispersion.outdoor` | 2 | `h2physics.release.SourceLocation` | position_m; direction_unit |
| `effects.cryogenic` | 2 | `h2physics.adapters.oxygen_deficiency.OxygenCriterion` | threshold; maximum_pressure_pa |
| `effects.exposure` | 2 | `h2physics.adapters.hyram_exposure.ExposureHistory` | unit; time_s |
| `effects.fragment_trajectory` | 2 | `h2physics.fragment_trajectory.FragmentLaunch` | mass_kg; position_m |
| `effects.heat_input` | 2 | `h2physics.adapters.pifira_heat.ClosedHeatDomain` | maximum_pressure_pa; maximum_quality |
| `effects.rupture` | 2 | `h2physics.adapters.vessel_failure.HelprAxialFlaw` | wall_thickness_m; flaw_depth_m |
| `equipment.compressor` | 2 | `h2physics.adapters.lh2dt_compressor.CompressorEnvelope` | inverted-compressor-pressure; nonfinite-compressor-flow |
| `equipment.gas_pipe` | 2 | `h2physics.hydraulics.DarcyGeometry` | negative-pipe-length; nonfinite-bore |
| `equipment.gas_tank` | 2 | `lh2dt.TankState` | negative-tank-inventory; nonfinite-wall-temperature |
| `equipment.heat_exchanger` | 2 | `h2physics.adapters.counterflow_heat_exchanger.CounterflowBoundary` | negative-hot-flow; nonfinite-cold-pressure |
| `equipment.instrument` | 2 | `h2physics.adapters.lh2dt_instrumentation.TransmitterEvidence` | missing-pressure-reference; missing-sensor-location |
| `equipment.insulation` | 3 | `h2physics.adapters.lh2dt_insulation.InsulationEvidence`; `h2physics.adapters.lh2dt_insulation.WallHeatAllocation` | gauge-vacuum-pressure-basis; missing-geometry-evidence; unnormalized-area-fractions |
| `equipment.lh2_tank` | 2 | `lh2dt.TankGeometry` | zero-vessel-volume; nonfinite-wall-capacity |
| `equipment.pump` | 3 | `h2physics.adapters.lh2dt_pump_operation.PumpSpeedActuator`; `h2physics.adapters.lh2dt_pump_operation.PumpSpeedCommand` | reversed-pump-clock; invalid-stop-speed; negative-speed-ramp |
| `equipment.relief` | 2 | `h2physics.adapters.lh2dt_relief.ReliefEventSettings` | negative-pressure-tolerance; noninteger-event-count |
| `equipment.reliquefier` | 2 | `h2physics.adapters.lh2dt_reliquefier.ReliquefactionDomain` | reversed-cold-pressure-domain; negative-cold-temperature |
| `equipment.two_phase_pipe` | 2 | `lh2dt.HEMPipe` | zero-hem-bore; negative-hem-roughness |
| `equipment.valve` | 3 | `h2physics.adapters.lh2dt_valve_actuator.StrokeActuator`; `h2physics.adapters.lh2dt_valve_actuator.ValveCommand` | reversed-valve-clock; overfull-stroke; negative-opening-rate |
| `equipment.vaporizer` | 2 | `lh2dt.DynamicVaporizer` | negative-vaporizer-volume; nonfinite-vaporizer-wall-capacity |
| `equipment.vent` | 2 | `h2physics.adapters.lh2dt_vent.VentEnvelope` | supersonic-scope-for-low-mach-vent; invalid-pressure-fraction |
| `facility.detector_reliability` | 2 | `h2physics.detector_reliability.evaluate_kofn_detector_reliability` | outside_probability; duplicate_detector |
| `facility.isolation` | 2 | `h2physics.adapters.facility_protection.ProtectionAction` | latency_s; resulting_mode_id |
| `facility.monitoring` | 2 | `h2physics.adapters.gas_detection.FirstOrderConcentrationSensorConfig` | response_time_constant_s; concentration_unit |
| `facility.network` | 2 | `h2physics.facility_continuity.FacilityStorageRate` | mass_accumulation_kg_s; energy_accumulation_w |
| `facility.risk` | 2 | `h2physics.adapters.conditional_risk.ConditionalHarmBinding` | probability; support_s |
| `materials.diffusion` | 2 | `DiffusionDomain.simulate` | duplicate-output-time; negative-initial-mobile-concentration |
| `materials.integrity` | 2 | `CylinderGeometry` | negative-inner-radius; inverted-wall-radii |
| `materials.permeation` | 2 | `steady_permeation` | negative-diffusivity; zero-wall-thickness |
| `materials.solubility` | 2 | `PowerLawSolubility.concentration_mol_m3` | negative-fugacity; zero-temperature |
| `production.biological` | 2 | `Adm1Geometry` | zero-liquid-volume; outside-biological-temperature-domain |
| `production.electrolyzer` | 2 | `HydrogenStack.evaluate` | negative-current; nonfinite-current |
| `production.energy_coupling` | 2 | `PVStage` | negative-irradiance; reversed-source-clock |
| `production.fuel_cell` | 2 | `HydrogenStack.evaluate` | zero-temperature; invalid-faradaic-efficiency |
| `production.gasification` | 2 | `MultiphaseFeed` | zero-feed-pressure; negative-feed-moles |
| `production.microbial_cell` | 2 | `MicrobialCellStage` | reversed-electrode-bracket; unnormalized-native-composition |
| `production.photo` | 2 | `PhotonSupply.from_lines` | negative-wavelength; negative-optical-power |
| `production.reforming` | 2 | `CatalyticThermalBoundary` | negative-wall-area; nonfinite-wall-temperature |
| `production.thermochemical` | 2 | `ThermochemicalInventory` | negative-species-stock; missing-energy-basis |
| `release.blowdown` | 2 | `h2physics.adapters.lh2dt.Lh2dtBulkNozzleOutflow.sample` | nonfinite_clock; negative_back_pressure |
| `release.droplets` | 2 | `h2physics.adapters.droplet_transport.ParcelBoundary` | carrier_viscosity_pa_s; carrier_velocity_m_s |
| `release.gas` | 2 | `h2physics.release.HomogeneousIsentropicNozzle.solve` | negative_back_pressure; excess_opening_fraction |
| `release.impact` | 2 | `h2physics.adapters.droplet_impact.ImpactQualification` | diameter_bounds_m; normal_speed_bounds_m_s |
| `release.liquid` | 2 | `h2physics.release.HomogeneousIsentropicNozzle.solve` | negative_back_pressure; excess_opening_fraction |
| `release.near_field` | 2 | `h2physics.adapters.degali.JetPlane` | horizontal_unit; vertical_unit |
| `release.two_phase` | 2 | `h2physics.release.HomogeneousIsentropicNozzle.solve` | negative_back_pressure; excess_opening_fraction |
| `research.economics` | 2 | `AnnualFinancialBasis` | zero-annual-duration; nonfinite-product-pressure |
| `research.uncertainty` | 2 | `JointParameterDomain` | reversed-physical-domain; nonfinite-physical-domain |
| `separation.membrane` | 2 | `PorousTransportGeometry` | impossible-porosity; zero-membrane-thickness |
| `separation.psa` | 2 | `PsaCycleEvidence` | negative-component-audit-budget; missing-native-energy-reference |
| `storage.adsorption` | 2 | `h2physics.adapters.finite_adsorption_vessel.AdsorptionVesselGeometry` | negative-adsorbent-mass; no-free-gas-volume |
| `storage.adsorption_thermal` | 2 | `h2physics.adapters.psa.BedFaceTransfers` | bed-species-axis-mismatch; nonfinite-bed-enthalpy |
| `storage.carrier_reaction` | 2 | `h2physics.adapters.carrier_conversion.CarrierProcessEvidence` | missing-carrier-phase-reference; unresolved-carrier-source |
| `storage.cryo_compressed` | 2 | `h2physics.adapters.cryo_compressed.CryoCompressedDomain` | critical-pressure-not-exceeded; unmodelled-two-phase-scope |
| `storage.hydride_compressor` | 2 | `h2physics.storage.hydride_compressor.HydrideCompressorStage` | invalid-bed-inlet-opening; nonpositive-receiver-bath |
| `storage.hydride_dynamic` | 2 | `h2physics.storage.finite_hydride.FiniteHydrideDomain` | negative-bed-gas-mass-floor; inverted-bed-temperature-domain |
| `storage.hydride_equilibrium` | 2 | `VanthoffPlateau.fugacity_pa` | nonpositive-equilibrium-temperature; impossible-stored-fraction |
| `storage.microsphere` | 2 | `h2physics.storage.microsphere.MicrosphereDomain` | negative-cavity-inventory-floor; inverted-cavity-pressure-envelope |
| `storage.porous_reservoir` | 2 | `h2physics.storage.porous_reservoir.PorousReservoirGeometry` | nonphysical-unit-porosity; permeability-cell-axis-mismatch |
| `storage.solid_reaction` | 2 | `h2physics.storage.solid_reaction.SolidReactionStep` | reversed-solid-temperature-bracket; nonfinite-solid-heat |
| `storage.underground` | 2 | `h2physics.adapters.underground_storage.UndergroundDomain` | nonpositive-cavern-pressure; unsupported-cold-cavern |
| `surface.pool` | 2 | `h2physics.adapters.pool.NativeDynamicPool.__init__` | unsupported_spin; missing_engine_identity |
| `thermo.mixtures` | 2 | `h2physics.mixtures.GasComposition` | unnormalized-fractions; mismatched-species-axis |
| `thermo.pure_fluid` | 4 | `CoolPropProperties.state_pt`; `h2physics.core.ThermoState` | negative-pressure; nonfinite-temperature; negative-provider-pressure; nonfinite-provider-temperature |
| `thermo.spin` | 2 | `h2physics.adapters.lh2dt_spin.SpinDomain` | inverted-temperature-domain; noninteger-rotational-cutoff |
