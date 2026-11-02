# External extension requests

Requests will specify the native Python types, physical responsibility, exact version,
required inputs/outputs, conservation checks, evidence and acceptance examples needed by
this library. A request is not a claim that the receiving change has been implemented.

Receiving repositories are not modified by this project. Keep requests independently
actionable so another development session can implement and verify them.

- [001 — LH2DT native properties/equipment contracts](001_lh2dt_native_contract.md)
- [002 — Compatible dispersion-engine versions](002_dispersion_engine_versions.md)
- [003 — Derived frequency and credited barriers](003_derived_frequency_and_barriers.md)
- [004 — Station/SAGA and observation contracts](004_station_saga_and_observations.md)
- [005 — Cryogenic adsorption and native bed providers](005_psa_cryogenic_adsorption.md)
- [006 — PRISM shared equilibrium nozzle and source history](006_prism_shared_release_kernel.md)
- [007 — LH2DT dynamic heat ledger and accepted-step contract](007_lh2dt_dynamic_heat_and_acceptance.md)
- [008 — LH2DT stopped-machine and isolated-assembly modes](008_lh2dt_stopped_machine_modes.md)
- [009 — LH2DT shared Darcy solver and friction-law convergence](009_lh2dt_darcy_convergence.md)
- [010 — Dynamic pool properties, event clocks and source intervals](010_dynamic_pool_properties_clock_and_sources.md)
- [011 — DEGALI profile forces, conserved fluxes and gas sources](011_degali_profile_flux_and_source_contracts.md)
- [012 — Preferred HyRAM / SLABx-LH2 boundaries and compatibility](012_preferred_dispersion_boundaries.md)

- [013 — Native insulation, property capabilities and compression boundaries](013_insulation_compression_native_boundaries.md)

- [014 — Protection, vent, recovery and observation capabilities](014_protection_vent_recovery_observation.md)
- [015 — Spin, thermal groups and reactive process boundaries](015_spin_thermal_groups_and_reacting_boundaries.md)
- [016 — Fire conservation, inverse heat and qualified observations](016_fire_conservation_heat_and_qualified_observations.md)
- [017 — Cryogenic storage, spin calorics, spherical materials and biological process contracts](017_cryo_spin_spherical_and_biological_contracts.md)
- [018 — Native cyclic separation, multiphase conversion and photon boundaries](018_native_cycles_multiphase_and_photon_boundaries.md)

- [019 — Membrane, staged thermal cycles and biological boundaries](019_membrane_thermal_cycles_and_biological_boundaries.md)

- [020 — Finite devices, material evidence and uncertainty](020_finite_devices_materials_and_uncertainty.md)

- [021 — Native waves, exposure, source evidence and conditional-risk objects](021_waves_exposure_and_conditional_risk.md)

- [022 — Oxygen, thermal physiology, learned monitoring and cold-room evidence](022_oxygen_thermal_monitoring_and_cold_room.md)

- [023 — Direct DC, solid-phase and fracture API follow-up](023_direct_dc_solid_and_fracture_api.md)

- [024 — Fire, vessel failure, parcel and economic integration](024_fire_failure_parcel_and_economics.md)

- [025 — Cavern, microbial cell, finite impact and material front](025_cavern_microbial_impact_and_front.md)

- [026 — CFD, jet-fire, economics and campaign evidence contracts](026_obstacle_fire_economic_and_campaign_contracts.md)

- [027 — Equipment, carrier and protection boundaries](027_equipment_carrier_protection_boundaries.md)

- [028 — Fuel cell, finite transfer, thermal and selection contracts](028_fuel_transfer_thermal_selection_contracts.md)
- [029 — Adsorption vessel, valve, relief and facility contracts](029_adsorption_valve_relief_facility_contracts.md)
- [030 — Rotating equipment, flowing heat and recovery contracts](030_rotating_heat_and_recovery_contracts.md)
- [031 — Fuel-cell pressure, activity and multivolume coupling](031_fuel_cell_pressure_coupling.md)
- [032 — Finite mixture separator inventory and phase withdrawals](032_finite_mixture_separator.md)
- [033 — Native pool energy ledger and finite-wall continuation](033_pool_energy_ledger.md)
- [034 — Hydrogen reciprocating engine cycle boundary](034_hydrogen_engine_cycle.md)
- [035 — Hydrogen gas-turbine cycle and combustor boundary](035_hydrogen_gas_turbine_cycle.md)
- [036 — Licensed hydrogen pipeline pressure/flow transient data](036_hydrogen_pipeline_transient_data.md)
- [037 — Native HyRAM input for finite time-varying hydrogen sources](037_hyram_transient_finite_source.md)

## Supplemental implementation contracts

The canonical requests above remain the receiving-project work items. These linked
notes expand native result fields, conservation signatures and parallel acceptance
matrices without changing the ownership or applicability boundaries:

- [Request012 — HyRAM plug-to-Gaussian flux closure](../research/integration_request_012.md)
- [Request031 — synchronized finite fuel-cell plant](../research/integration_request_031.md)
- [Request032 — evolving-mixture separator](../research/integration_request_032.md)
- [Request033 — accepted-clock pool energy](../research/integration_request_033.md)
- [Requests034/035 — piston engine and gas turbine](../research/integration_request_034_035.md)
- [Hydrogen engine figure-data semantic mapping request](hydrogen_engine_figure_data_mapping.md) (prepared, not sent)
- [Brookite photocatalysis AQY condition-mapping request](photocatalysis_aqy_condition_mapping.md) (prepared, not sent)
- [SOE fault-operation schema and targeted-acquisition request](soe_fault_operation_data_request.md) (prepared, not sent)
- [Dark-fermentation gas basis and reactor-state request](dark_fermentation_gas_basis_request.md) (prepared, not sent)
- [Nanoporous-carbon H2 chemisorption basis request](carbon_h2_chemisorption_basis_request.md) (prepared, not sent)

- [uh2sc scalar CoolProp runtime compatibility](038_uh2sc_coolprop_scalar_compatibility.md): observed native initialization blocker for the underground-to-compressor connection; no external solver patch is included.
