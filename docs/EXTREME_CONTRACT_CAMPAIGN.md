# Extreme-value and boundary checks — 2026-11-02

This campaign follows representative input checks and nominal equation checks. It tests selected project-owned numerical calculations and host boundary handling. Existing engines' internal physics is excluded. Synthetic extreme magnitudes stress arithmetic and stated limits; they do not define safe plant conditions, valid material extrapolation or experimental accuracy.

## Results

The three independent lanes pass 108 cases across 66 of the 78 scoped topic families. The other12 selected cores are native-owned and excluded, not counted as passes. All78 classifications are reconciled against the preceding input-campaign scope. No selected host check remains pending. This is representative boundary coverage, not exhaustive verification of every equation or parameter.

| Selected check scope | Families |
| --- | ---: |
| Model numerical calculation | 29 |
| Supporting numerical geometry, integration, units or accounting | 31 |
| Calculated-domain underflow rejection only | 1 |
| Exposed endpoint field mapping only | 1 |
| Declared host domain edge only | 4 |
| Existing-engine core excluded | 12 |

The four domain-edge-only families are explicitly marked in the table below and must not be presented as solved numerical extreme cases. The pure-fluid check only retains saturation quality endpoints; it does not test EOS accuracy. Several families use legitimate private accounting helpers with declared inputs; that checks their arithmetic, not public result issuance or end-to-end module connections.

| Lane | Cases passed | Families with checks | Native cores excluded |
| --- | ---: | ---: | ---: |
| Equipment/storage | 26 | 26 | 2 |
| Production/materials | 49 | 17 | 0 |
| Safety/facility | 33 | 23 | 10 |

## Product corrections and retained limits

- The shared electrolyzer/fuel-cell stack could return infinite current, power and hydrogen rates from finite inputs whose products overflow. It now checks computed output quantities and refuses nonfinite arithmetic with a clear ValueError.
- The material solubility law could raise a raw exponent overflow or emit a nonfinite concentration. It now translates exponent overflow into a descriptive ValueError and checks the computed concentration. It does not silently clamp or extrapolate the law.
- Source-affected nominal regressions:14 passed;6 unselected cases were deselected, not included as passes. Evidence is production-regression.xml/log.
- The counterflow heat exchanger still rejects zero positive-direction heat flow and a highly conducting single-cell condition that would reverse an endpoint temperature. A separate accepted1mK inlet-gap case agrees with its independent reference. No production guard or conservation tolerance was relaxed.
- The solid-reaction extreme explicitly selects the existing truncate policy; consumption is bounded by actual available reactant. This is not an implicit change to the default refusal policy.
- Initial fixture mistakes (an absent PSA field, nominal-zero Darcy drive, native flash roundoff at envelope edges and a layered-energy reference) were corrected. Intermediate failed run receipts remain preserved.

## Execution and reproduction

The final campaign uses three separate Python processes concurrently. Numerical library thread counts are1, automatic pytest plugin loading is disabled and plotting uses Agg. The runner records all product Python files and new campaign test-file hashes before execution and confirms that this selected source set is unchanged afterwards. Native dependencies remain separately installed; no substitute results or skipped dependencies count as passes.

Use the existing h2physics-py312 environment:

```powershell
python scripts/run_extreme_contracts.py --output-dir artifacts/extreme-contracts-20261102/replay
python scripts/summarize_extreme_contracts.py artifacts/extreme-contracts-20261102/replay/equipment_storage.xml artifacts/extreme-contracts-20261102/replay/production_materials.xml artifacts/extreme-contracts-20261102/replay/safety_facility.xml --output artifacts/extreme-contracts-20261102/replay/summary.json
```

The output directory must be empty so earlier evidence is preserved. Latest pinned receipts are under artifacts/extreme-contracts-20261102/final-pin/; executed-summary.json holds parsed per-case evidence. Per-lane coverage files retain scenario descriptions, narrower helper scope and exclusions. Native internal-physics qualification, measured-data validation and application qualification are not implied.

## Family classifications

| Family | Scope | Selected target / scenario |
| --- | --- | --- |
| `combustion.detonation` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `combustion.equilibrium` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `combustion.flash_fire` | supporting_geometry_or_accounting | run_material_front |
| `combustion.gas_turbine` | model_equation | integrate_shaft_transient |
| `combustion.jet_fire` | supporting_geometry_or_accounting | HyRAMFlameRun.irradiance host geometry guard |
| `combustion.kinetics` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `combustion.laminar_flame` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `combustion.overpressure` | supporting_geometry_or_accounting | DetonableHydrogenEnergy.energy_j |
| `combustion.piston_engine` | supporting_geometry_or_accounting | SliderCrank |
| `combustion.pool_fire` | supporting_geometry_or_accounting | FinitePoolFire.run |
| `dispersion.buoyant_layer` | model_equation | _plume_coefficient |
| `dispersion.compartment_network` | model_equation | simulate_hydrogen_compartment_network |
| `dispersion.enclosure` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `dispersion.obstacle` | supporting_geometry_or_accounting | CFDMesh.fluid_volume_m3/solid_mask |
| `dispersion.outdoor` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `effects.cryogenic` | supporting_geometry_or_accounting | _integrate_positive_threshold_deficit |
| `effects.exposure` | supporting_geometry_or_accounting | HyRAMExposure host fluence |
| `effects.fragment_trajectory` | model_equation | integrate_fragment_flight |
| `effects.heat_input` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `effects.rupture` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `equipment.compressor` | host_domain_edge_only | CompressorEnvelope.require_flow/require_state |
| `equipment.gas_pipe` | model_numerics | solve_darcy_flow |
| `equipment.gas_tank` | supporting_numerics | InventoryBalance used by native tank host audit |
| `equipment.heat_exchanger` | model_numerics | CounterflowHeatExchanger.solve |
| `equipment.instrument` | native_core_excluded | Selected instrument/adsorption-thermal core is native-owned; internal physics excluded |
| `equipment.insulation` | supporting_numerics | layered_inventory_reader |
| `equipment.lh2_tank` | supporting_numerics | stratified_inventory_reader |
| `equipment.pump` | model_numerics | PumpSpeedActuator.advance |
| `equipment.relief` | model_numerics | FiniteLiftRelief.advance |
| `equipment.reliquefier` | supporting_numerics | LiquefactionBenchmark properties |
| `equipment.two_phase_pipe` | model_numerics | Lh2dtDarcyPipe.evaluate |
| `equipment.valve` | model_numerics | StrokeActuator.advance |
| `equipment.vaporizer` | supporting_numerics | lumped_inventory_reader |
| `equipment.vent` | host_domain_edge_only | VentEnvelope.require_state |
| `facility.detector_reliability` | model_equation | evaluate_kofn_detector_reliability |
| `facility.isolation` | supporting_geometry_or_accounting | alarm_valve_isolation._compose |
| `facility.monitoring` | model_equation | evaluate_first_order_concentration_sensor |
| `facility.network` | supporting_geometry_or_accounting | FacilityContinuityAudit.audit |
| `facility.risk` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `materials.diffusion` | model_equation | DiffusionDomain.simulate |
| `materials.integrity` | model_equation | lame_stress_field |
| `materials.permeation` | model_equation | steady_permeation |
| `materials.solubility` | model_equation | PowerLawSolubility.concentration_mol_m3 |
| `production.biological` | supporting_geometry_or_accounting | QsdSanAdm1Digester._point |
| `production.electrolyzer` | model_equation | HydrogenStack.evaluate |
| `production.energy_coupling` | supporting_geometry_or_accounting | PVBoundaryProfile.stages |
| `production.fuel_cell` | model_equation | HydrogenStack.evaluate |
| `production.gasification` | supporting_geometry_or_accounting | cantera_multiphase._snapshot |
| `production.microbial_cell` | model_equation | FiniteMicrobialCell.run |
| `production.photo` | model_equation | BeerLambertPath.absorbed_fraction |
| `production.reforming` | supporting_geometry_or_accounting | _surface_internal_energy_j |
| `production.thermochemical` | model_equation | FiniteThermochemicalCycle.run |
| `release.blowdown` | native_core_excluded | Selected internal physics belongs to existing native engine, outside this campaign; no test pass is inferred. |
| `release.droplets` | model_equation | SaturatedParcelFlight.run |
| `release.gas` | model_equation | HomogeneousIsentropicNozzle.solve |
| `release.impact` | model_equation | FiniteSurfaceImpact._trial |
| `release.liquid` | model_equation | HomogeneousIsentropicNozzle.solve |
| `release.near_field` | supporting_geometry_or_accounting | JetPlane.project |
| `release.two_phase` | model_equation | HomogeneousIsentropicNozzle.solve |
| `research.economics` | supporting_geometry_or_accounting | PhysicalCostProjection.price_window |
| `research.uncertainty` | supporting_geometry_or_accounting | PropagationResult.summarize |
| `separation.membrane` | supporting_geometry_or_accounting | CanteraDustyGasTransport.flux host unit conversion |
| `separation.psa` | supporting_geometry_or_accounting | PsaDynaCycle._totals |
| `storage.adsorption` | supporting_numerics | loading_working_capacity |
| `storage.adsorption_thermal` | native_core_excluded | Selected instrument/adsorption-thermal core is native-owned; internal physics excluded |
| `storage.carrier_reaction` | model_numerics | StoichiometricReaction.convert |
| `storage.cryo_compressed` | host_domain_edge_only | CryoCompressedDomain.require |
| `storage.hydride_compressor` | supporting_numerics | FiniteHydrideGasVessel.coolprop extensive conversion |
| `storage.hydride_dynamic` | model_numerics | HydrideKinetics.fraction_rate_s_inv |
| `storage.hydride_equilibrium` | computed_domain_rejection | VanthoffPlateau.fugacity_pa |
| `storage.microsphere` | host_domain_edge_only | MicrosphereStorage.gas_state |
| `storage.porous_reservoir` | supporting_numerics | PorousReservoirGeometry.pore_volume_m3 |
| `storage.solid_reaction` | model_numerics | FiniteSolidReactionReactor.run |
| `storage.underground` | supporting_numerics | _integrate_withdrawal |
| `surface.pool` | supporting_geometry_or_accounting | DeclaredGroundInflow.cumulative_mass_kg |
| `thermo.mixtures` | supporting_numerics | GasComposition.component_mass_flows |
| `thermo.pure_fluid` | host_field_mapping | CoolPropProperties.saturated exposed quality |
| `thermo.spin` | supporting_numerics | SpinEnthalpyReference.enthalpy_j |

## Stage boundaries

Representative input and nominal calculation campaigns remain recorded separately. Module-connection checks have not started in this wave. The new finite-output guards do not change the implementation census or establish experimental qualification.
