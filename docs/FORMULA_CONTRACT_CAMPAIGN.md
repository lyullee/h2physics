# Nominal calculation checks — 2026-11-02

The resumed campaign checks selected project-owned calculations against independently derived answers. It does not independently validate the internal physics of existing external engines. The 78-topic scope is the same as the completed representative input campaign. Each tested family has a named calculation; this is not an assertion that every equation or optional level is qualified.

## Results

| Classification | Families | Meaning |
| --- | ---: | --- |
| Model equation | 30 | Selected host numerical/physical equation compared with an analytic reference |
| Supporting calculation | 35 | Geometry, integration, stoichiometry, units or accounting checked; native prediction is not thereby validated |
| Thermodynamic identity | 1 | Exposed fields satisfy h−u=P/ρ; not an independent EOS accuracy comparison |
| Existing-engine selected core excluded | 12 | Outside the requested internal-physics validation scope |

67 executed test cases passed across 66 families (the piston-engine family has two cases). Thus 66/78 families have a selected numerical check; 12/78 are excluded selected native cores, not reported passes. There are no remaining pending checks in this selected host campaign. This does not establish complete physics verification for 78 families.

Three lanes run as separate processes so optional native dependencies do not share import state. Final pinned execution receipts and source hashes are in `artifacts/formula-contracts-20261102/final-pin-run.json`; the parsed case evidence is `executed-summary.json`. The production lane received import formatting afterwards and passed again against the final file; `final-format-source.json` and `production-materials-final-format.xml` record that successor. Intermediate runs and failures remain preserved.

## Corrections exposed by execution

- Pool fire: temporary Pydantic serialization dictionaries acquired new identities on every content-seal check. The snapshot now retains the native object identity and deterministic finite JSON values. A genuine unchanged run is accepted and mutation of its native burned mass is rejected.
- Material-frame flash front: the trace seal referenced absent `CellBurn.time_s`; it now reads the declared `arrival_s`. A genuine unchanged trace is accepted and arrival mutation is rejected.
- Test fixtures: replaced an absent saturation API, met the biological minimum sample count, corrected kg/kmol-to-kg/mol conversion, and tightened small-value numerical tolerances. These were test corrections, not product formula corrections.
- The flash test explicitly selects a genuine mixture-averaged/no-Soret native flame satisfying existing admission conditions; no production guard was relaxed.

## Reproduction

Use the existing `h2physics-py312` environment and separately installed reviewed native providers. Run the three `tests/test_formula_contract_*.py` suites in separate Python processes with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `MPLBACKEND=Agg` and numerical-library thread counts set to one. Exact pytest commands are saved in the final execution receipt. Missing providers are failures, not skipped coverage.

Parse the three final XML files with `python scripts/summarize_formula_contracts.py <equipment-xml> <production-xml> <safety-xml> --output <summary.json>`.

## Family evidence

| Family | Classification | Named calculation |
| --- | --- | --- |
| `combustion.detonation` | native_core_excluded | SDToolboxDetonation |
| `combustion.equilibrium` | native_core_excluded | CanteraGas |
| `combustion.flash_fire` | supporting_geometry_or_accounting | run_material_front host material travel/contact |
| `combustion.gas_turbine` | model_equation | integrate_shaft_transient |
| `combustion.jet_fire` | supporting_geometry_or_accounting | run_hyram_flame host power accounting |
| `combustion.kinetics` | native_core_excluded | CanteraGas |
| `combustion.laminar_flame` | native_core_excluded | CanteraGas; solve_counterflow_diffusion_flame |
| `combustion.overpressure` | supporting_geometry_or_accounting | DetonableHydrogenEnergy.energy_j |
| `combustion.piston_engine` | supporting_geometry_or_accounting | integrate_engine_boundary_streams |
| `combustion.pool_fire` | supporting_geometry_or_accounting | FinitePoolFire.run host ledgers |
| `dispersion.buoyant_layer` | model_equation | _plume_coefficient |
| `dispersion.compartment_network` | model_equation | simulate_hydrogen_compartment_network |
| `dispersion.enclosure` | native_core_excluded | CanteraOpenGasVolume |
| `dispersion.obstacle` | supporting_geometry_or_accounting | CFDMesh.fluid_volume_m3/solid_mask/spacing_m |
| `dispersion.outdoor` | native_core_excluded | run_preferred_gas_dispersion; run_preferred_lh2_dispersion |
| `effects.cryogenic` | supporting_geometry_or_accounting | _integrate_positive_threshold_deficit |
| `effects.exposure` | supporting_geometry_or_accounting | HyRAMExposure.thermal_dose host fluence |
| `effects.fragment_trajectory` | model_equation | integrate_fragment_flight |
| `effects.heat_input` | native_core_excluded | PifiraClosedVesselHeat; pifira_effective_area |
| `effects.rupture` | native_core_excluded | HelprVesselFailure |
| `equipment.compressor` | supporting_geometry_or_accounting | ConnectionTransfer enthalpy-flow and residual accounting |
| `equipment.gas_pipe` | model_equation | solve_darcy_flow |
| `equipment.gas_tank` | supporting_geometry_or_accounting | Lh2dtReliefTankDriver host cumulative ledger |
| `equipment.heat_exchanger` | model_equation | CounterflowHeatExchanger.solve |
| `equipment.instrument` | native_core_excluded | Selected physical law belongs to native engine |
| `equipment.insulation` | supporting_geometry_or_accounting | layered_inventory_reader |
| `equipment.lh2_tank` | supporting_geometry_or_accounting | stratified_inventory_reader |
| `equipment.pump` | model_equation | NormalizedPumpMap.admit/PumpSpeedActuator.advance |
| `equipment.relief` | model_equation | FiniteLiftRelief.advance |
| `equipment.reliquefier` | supporting_geometry_or_accounting | LiquefactionBenchmark exergy/work properties |
| `equipment.two_phase_pipe` | supporting_geometry_or_accounting | Lh2dtDarcyPipe.evaluate |
| `equipment.valve` | model_equation | StrokeActuator.advance |
| `equipment.vaporizer` | supporting_geometry_or_accounting | lumped_inventory_reader |
| `equipment.vent` | supporting_geometry_or_accounting | Lh2dtVentStack.evaluate host hydraulics/accounting |
| `facility.detector_reliability` | model_equation | evaluate_kofn_detector_reliability |
| `facility.isolation` | supporting_geometry_or_accounting | alarm_valve_isolation._compose |
| `facility.monitoring` | model_equation | evaluate_first_order_concentration_sensor |
| `facility.network` | supporting_geometry_or_accounting | FacilityContinuityAudit.audit |
| `facility.risk` | native_core_excluded | conditional_risk; evaluate_facility_risk |
| `materials.diffusion` | model_equation | DiffusionDomain.simulate |
| `materials.integrity` | model_equation | lame_stress_field |
| `materials.permeation` | model_equation | steady_permeation |
| `materials.solubility` | model_equation | PowerLawSolubility.concentration_mol_m3 |
| `production.biological` | supporting_geometry_or_accounting | BiologicalPoint headspace hydrogen conversion |
| `production.electrolyzer` | model_equation | HydrogenStack.evaluate |
| `production.energy_coupling` | supporting_geometry_or_accounting | PVBoundaryProfile.stages |
| `production.fuel_cell` | model_equation | HydrogenStack.evaluate |
| `production.gasification` | supporting_geometry_or_accounting | MultiphaseSnapshot mass projection |
| `production.microbial_cell` | model_equation | FiniteMicrobialCell.run Faraday material accounting |
| `production.photo` | model_equation | PhotonSupply.from_lines |
| `production.reforming` | supporting_geometry_or_accounting | CatalyticSurfacePoint combined energy projection |
| `production.thermochemical` | model_equation | FiniteThermochemicalCycle.run |
| `release.blowdown` | native_core_excluded | Lh2dtBulkNozzleOutflow |
| `release.droplets` | model_equation | SaturatedParcelFlight.run |
| `release.gas` | model_equation | HomogeneousIsentropicNozzle.solve |
| `release.impact` | model_equation | FiniteSurfaceImpact._trial |
| `release.liquid` | model_equation | HomogeneousIsentropicNozzle.solve |
| `release.near_field` | supporting_geometry_or_accounting | JetPlane.project |
| `release.two_phase` | model_equation | HomogeneousIsentropicNozzle.solve |
| `research.economics` | supporting_geometry_or_accounting | PhysicalCostProjection.price_window |
| `research.uncertainty` | supporting_geometry_or_accounting | PropagationResult.summarize |
| `separation.membrane` | supporting_geometry_or_accounting | CanteraDustyGasTransport.flux host unit projection |
| `separation.psa` | supporting_geometry_or_accounting | PsaCycleTotals purity and product/feed arithmetic |
| `storage.adsorption` | supporting_geometry_or_accounting | loading_working_capacity |
| `storage.adsorption_thermal` | native_core_excluded | Selected physical law belongs to native engine |
| `storage.carrier_reaction` | model_equation | StoichiometricReaction.convert |
| `storage.cryo_compressed` | supporting_geometry_or_accounting | CryoCompressedStorage initial extensive conversion |
| `storage.hydride_compressor` | supporting_geometry_or_accounting | FiniteHydrideGasVessel.coolprop extensive conversion |
| `storage.hydride_dynamic` | model_equation | HydrideBed.simulate |
| `storage.hydride_equilibrium` | model_equation | VanthoffPlateau.fugacity_pa |
| `storage.microsphere` | supporting_geometry_or_accounting | MicrosphereStorage.gas_state |
| `storage.porous_reservoir` | model_equation | PorousReservoir.run |
| `storage.solid_reaction` | model_equation | FiniteSolidReactionReactor.run |
| `storage.underground` | supporting_geometry_or_accounting | _integrate_withdrawal |
| `surface.pool` | supporting_geometry_or_accounting | DeclaredGroundInflow.cumulative_mass_kg |
| `thermo.mixtures` | supporting_geometry_or_accounting | GasComposition mass/mole conversions |
| `thermo.pure_fluid` | thermodynamic_identity_only | CoolPropProperties.state_pt exposed fields |
| `thermo.spin` | supporting_geometry_or_accounting | SpinEnthalpyReference.enthalpy_j |

## Next stages

Extreme-value checks and module-connection checks have not begun. Experimental validation, plant qualification and external-engine internal-physics validation are separate from this nominal known-answer campaign.
