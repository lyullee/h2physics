"""Pinned Hangang first-wave case plan; discovery imports metadata only."""

import os
from dataclasses import replace
from pathlib import PurePosixPath

from h2physics.cluster_validation import ClusterProfile, collect_cases

REPOSITORY = os.environ["H2_HANGANG_ROOT"]
WORKSPACE = str(PurePosixPath(REPOSITORY).parent)
PYTHON = WORKSPACE + "/.venv/bin/python"
SETUP = REPOSITORY + "/scripts/hangang_core_setup.sh"
SETUP_SHA256 = os.environ["H2_HANGANG_SETUP_SHA256"]

PROFILES = {
    name: ClusterProfile(
        name=name,
        python_executable=PYTHON,
        setup_script=SETUP,
        setup_sha256=SETUP_SHA256,
        numerical_threads=1,
    )
    for name in (
        "carrier-conversion",
        "carrier-conversion-native",
        "thermal-target",
        "source-data-ingestion",
        "hydrogen-channel-data",
        "material-transport",
        "preferred-dispersion",
        "finite-hydride",
        "pool-fire",
        "jet-fire-conservation",
        "hyram-overpressure",
        "joint-uncertainty",
        "porous-reservoir",
        "underground-storage",
        "gas-compressible-pipe",
        "photochemistry",
        "fuel-cell-native",
        "fuel-cell",
        "pv-electrolysis",
        "grid-electrolysis",
        "alkaline-electrolysis",
        "isothermal-eos",
        "hydrogen-engine",
        "mixture-vle",
        "pool-energy-contract",
        "finite-relief-lift",
        "finite-adsorption-vessel",
        "adsorption-data",
        "compressor-map",
        "facility-protection",
        "oxygen-deficiency",
        "droplet-impact",
        "droplet-transport",
        "solid-reaction",
        "solid-reaction-native",
        "counterflow-flame",
        "jet-fire-radiation",
        "pump-operation",
        "finite-transfer",
        "fragment-trajectory",
        "fracture-fatigue",
    )
}

_DISCOVERED_CASES = collect_cases(
    "validation.cases.pv_electrolysis",
    "validation.cases.fuel_cell",
    "validation.cases.fuel_cell_inventory_event",
    "validation.cases.real_gas_linepack_fuel_cell_feed",
    "validation.cases.carrier_conversion",
    "validation.cases.thermal_target",
    "validation.cases.bam_jet_fire_data",
    "validation.cases.grinhy2_ingest",
    "validation.cases.hydrogen_channel_data",
    "validation.cases.sofc_polarization_bridge",
    "validation.cases.hydrogen_acoustic_eos",
    "validation.cases.hydrogen_engine_link_gap",
    "validation.cases.fermentation_model_link_gap",
    "validation.cases.carbon_h2_model_link_gap",
    "validation.cases.hydride_shell_boundary",
    "validation.cases.cryo_mof_langmuir",
    "validation.cases.ignited_jet_finite_source",
    "validation.cases.bam_thermal_observation",
    "validation.cases.pem_grid_system_gap",
    "validation.cases.alkaline_bubble_data_gap",
    "validation.cases.alkaline_bubble_model",
    "validation.cases.hydride_pct_model_link_gap",
    "validation.cases.soe_fault_operation_gap",
    "validation.cases.h2safe_indoor_ingest",
    "validation.cases.ignited_hydrogen_jet_data",
    # Includes the metadata-only axial annulus geometry contract.
    "validation.cases.material_transport",
    "validation.cases.material_surface_film",
    "validation.cases.hydrogen_core_flood",
    "validation.cases.slabx_parallel_snapshots",
    "validation.cases.hyram_transition",
    "validation.cases.hyram_fixed_flow_snapshots",
    "validation.cases.jet_fire_conservation",
    "validation.cases.hyram_overpressure",
    "validation.cases.hyram_ignition_probability",
    "validation.cases.hyram_ignition_risk_handoff",
    "validation.cases.pool_fire",
    "validation.cases.uncertainty_joint_scenarios",
    "validation.cases.facility_accident_uncertainty",
    "validation.cases.two_vent_hydrogen_layer",
    "validation.cases.buoyant_layer_h2_alarm",
    "validation.cases.layer_oxygen_projection",
    "validation.cases.layer_oxygen_alarm_handoff",
    "validation.cases.hydrogen_compartment_network",
    "validation.cases.porous_reservoir",
    "validation.cases.underground_storage",
    "validation.cases.underground_compressor_inlet",
    "validation.cases.compressible_gas_pipe",
    "validation.cases.real_gas_hydraulics",
    "validation.cases.isothermal_gas_pipe_network",
    "validation.cases.isothermal_pipe_waves",
    "validation.cases.pipeline_wave_observations",
    "validation.cases.caloric_pipe_waves",
    "validation.cases.caloric_pipe_finite_wall",
    "validation.cases.caloric_pipe_network_waves",
    "validation.cases.caloric_reservoir_nozzle",
    "validation.cases.finite_reservoir_nozzle_sink",
    # One discovered module expands into five separately schedulable network-wave cases.
    "validation.cases.isothermal_pipe_network_waves",
    "validation.cases.isothermal_pipe_network_reservoir",
    "validation.cases.finite_pipe_reservoir_network",
    "validation.cases.finite_isothermal_pipe_reservoir",
    "validation.cases.finite_reservoir_pipe_wave",
    "validation.cases.pipeline_linepack",
    "validation.cases.real_gas_linepack",
    "validation.cases.compressor_linepack",
    "validation.cases.linepack_compressor_inlet",
    "validation.cases.linepack_fuel_cell_feed",
    "validation.cases.electrolysis_linepack",
    "validation.cases.grid_electrolysis_dispatch",
    "validation.cases.coolprop_isothermal_eos",
    "validation.cases.coolprop_isothermal_mixture_linepack",
    "validation.cases.coolprop_isothermal_mixture_pipe_waves",
    "validation.cases.pressure_regulator",
    "validation.cases.hysam_sampling",
    "validation.cases.h2_stations_inventory",
    "validation.cases.isothermal_eos_table",
    "validation.cases.isothermal_eos_artifact",
    "validation.cases.compressor_discharge_source",
    "validation.cases.solid_reaction",
    "validation.cases.fuel_cell_trial",
    "validation.cases.electrochemical_hydrogen_handoff",
    "validation.cases.electrochemical_storage_round_trip",
    "validation.cases.brayton_compressor_map",
    "validation.cases.engine_boundary_ledger",
    "validation.cases.open_cylinder_engine",
    "validation.cases.engine_wall_thermal",
    "validation.cases.steady_map_solver",
    "validation.cases.cantera_fuel_cell_coupled",
    "validation.cases.fuel_cell_current_limit",
    "validation.cases.cooled_brayton",
    "validation.cases.staged_turbine_cooling",
    "validation.cases.brayton_shaft_transient",
    "validation.cases.hydrogen_fuel_compression",
    "validation.cases.finite_hydride",
    "validation.cases.finite_hydride_vessel_failure",
    "validation.cases.finite_hydride_compressor_inlet",
    "validation.cases.finite_hydride_fuel_cell_feed",
    "validation.cases.adsorption_finite_hydride_port",
    "validation.cases.compressor_finite_hydride_port",
    "validation.cases.reliquefier_separator_inlet",
    "validation.cases.finite_separator_vessel_failure",
    "validation.cases.hyram_thermal_target",
    "validation.cases.finite_mixture_inventory",
    "validation.cases.mixture_inventory_ode",
    "validation.cases.pool_native_energy_contract",
    "validation.cases.finite_relief_lift",
    "validation.cases.adsorption_dynamics",
    "validation.cases.storage_product_delivery",
    "validation.cases.geological_adsorption",
    "validation.cases.bath_cryo_kinetics",
    "validation.cases.mhc_compressor_temperature",
    "validation.cases.pressure_peaking_source",
    "validation.cases.pressure_ignited_source",
    "validation.cases.pv_pem_dispatch_model_link_gap",
    "validation.cases.oxygen_hypoxia_chamber_link_gap",
    "validation.cases.carpark_unignited_fds_link_gap",
    "validation.cases.large_scale_h2_explosion_link_gap",
    "validation.cases.residential_h2_pilot_gap",
    "validation.cases.hfcev_fleet_data",
    "validation.cases.elvhys41_concentration",
    "validation.cases.elvhys432_thermal",
    "validation.cases.large_scale_explosion_summary",
    "validation.cases.large_scale_explosion_trace",
    "validation.cases.wskbij_test001",
    "validation.cases.wasserstoffatlas_inventory",
    "validation.cases.clashach_h2_pnm_gap",
    "validation.cases.leaky_coating_sorption",
    "validation.cases.cryo_neutron_phase_change_ingest",
    "validation.cases.am316l_workbooks",
    "validation.cases.ml_hydpark_screening",
    "validation.cases.aem_water_electrolysis_ingest",
    "validation.cases.elvhys_model_link_gap",
    "validation.cases.compressor_anti_surge",
    "validation.cases.facility_accident_chain",
    "validation.cases.preferred_dispersion_alarm_contract",
    "validation.cases.preferred_dispersion_grid_contract",
    "validation.cases.preferred_dispersion_risk_ledger",
    "validation.cases.facility_accident_consequence",
    "validation.cases.detector_reliability",
    "validation.cases.alarm_valve_isolation",
    "validation.cases.alarm_valve_actuation",
    "validation.cases.sensor_calibration",
    "validation.cases.oxygen_threshold_integral",
    "validation.cases.oxygen_alarm_handoff",
    "validation.cases.peace_alkaline_ingest",
    "validation.cases.rodare_alkaline_bubble_index",
    "validation.cases.pem_ripple_ingest",
    "validation.cases.pem_ripple_model_bridge",
    "validation.cases.cryo_mof_data",
    "validation.cases.droplet_impact",
    "validation.cases.droplet_transport",
    "validation.cases.cantera_surface_reactor",
    "validation.cases.cantera_catalytic_pfr",
    "validation.cases.cantera_gas_volume_source",
    "validation.cases.cantera_membrane_heat",
    "validation.cases.jet_radiation",
    "validation.cases.pump_operation",
    "validation.cases.finite_transfer",
    "validation.cases.cascade_refill_sequence",
    "validation.cases.cantera_species_alarm",
    "validation.cases.parcel_population_impact_sequence",
    "validation.cases.fragment_trajectory",
    "validation.cases.fragment_energy_bound",
    "validation.cases.vessel_failure_fragment_flight",
    "validation.cases.photochemistry",
    "validation.cases.photocatalysis_aqy_gap",
)

# This source-only campaign uses the separately staged, hash-checked publisher
# attachments on Hangang. The path is intentionally absent from the Nurion
# example plan, whose source staging remains deferred.
_CORE_FLOOD_SOURCE = "/scratch/r1021a02/h2physics-core-flood-20261031-8759d1a8054c"
_HYDROGEN_CHANNEL_SOURCE = "/scratch/r1021a02/h2physics-source-attachments/hydrogen-channel/2"
_H2SAFE_SOURCE_ARCHIVE = (
    "/scratch/r1021a02/h2physics-source-attachments/h2safe-indoor/2026-10-05/"
    "1787856683-Dataset.zip"
)
_ACOUSTIC_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/hydrogen-sound-speed/1.0.0"
_PRESSURE_UNIGNITED_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments"
_PRESSURE_IGNITED_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments"
_HFCEV_FLEET_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/hfcev-fleet/1"
_ELVHYS41_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/elvhys-condensed-explosion/1"
_ELVHYS432_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/elvhys-fireline/1"
_WSKBIJ_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/wskbij-explosion/1"
_WASSERSTOFFATLAS_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/wasserstoffatlas/1"
_LEAKY_COATING_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/leaky-coating-hydride-sorption/1"
_H2_STATIONS_SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/h2-stations/2026-10-31"
_CRYO_NEUTRON_SOURCE_RUN = (
    "/scratch/r1021a02/h2physics-source-attachments/cryo-neutron-phase-change/2/"
    "Jan(H2)/jan_tc1/jan_tc1_run1"
)
_PEM_RIPPLE_SOURCE_MEMBER = (
    "/scratch/r1021a02/h2physics-jobs/data/pem-ripple/2/"
    "PEM1_Initial.csv.gz"
)
CASES = tuple(
    replace(case, parameters={**case.parameters, "source_directory": _CORE_FLOOD_SOURCE})
    if case.identifier == "mendeley-hydrogen-core-flood-source-bound-kr-tables"
    else replace(case, parameters={**case.parameters, "source_directory": _HYDROGEN_CHANNEL_SOURCE})
    if case.identifier in {"hydrogen-channel-v2-source-bound-table",
                           "hydrogen-channel-measured-finite-source-bridge"}
    else replace(case, parameters={**case.parameters,
                                   "source_archive_path": _H2SAFE_SOURCE_ARCHIVE})
    if case.identifier == "h2safe-indoor-source-bound-experiment-ingestion"
    else replace(case, parameters={**case.parameters,
                                   "archive_path": _ACOUSTIC_SOURCE_ROOT + "/H2_speedofsound_dataset.zip",
                                   "metadata_path": _ACOUSTIC_SOURCE_ROOT + "/repository-metadata.json"})
    if case.identifier in {"hydrogen-acoustic-source-to-coolprop-pointwise-diagnostic",
                           "hydrogen-acoustic-source-phase-mismatch-diagnostic"}
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _PRESSURE_UNIGNITED_SOURCE_ROOT})
    if case.identifier == "usn-unignited-measured-flow-finite-source-contract"
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _PRESSURE_IGNITED_SOURCE_ROOT})
    if case.identifier == "usn-ignited-measured-flow-finite-source-contract"
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _HFCEV_FLEET_SOURCE_ROOT})
    if case.identifier == "hfcev-fleet-hydrogen-consumption-model-comparator"
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _ELVHYS41_SOURCE_ROOT})
    if case.identifier == "elvhys41-vent-composition-source-ingest"
    else replace(case, parameters={**case.parameters,
                                   "native_packages": os.environ["H2_HANGANG_HYRAM_PACKAGES"]})
    if case.identifier.startswith(("jet-conservation-", "hyram-native-radiation-exposure-",
                                   "hyram-bauwens-"))
       and "H2_HANGANG_HYRAM_PACKAGES" in os.environ
    else replace(case, parameters={**case.parameters,
                                   "native_packages": os.environ["H2_HANGANG_POOL_PACKAGES"]})
    if case.identifier.startswith("pool-fire-") and "H2_HANGANG_POOL_PACKAGES" in os.environ
    else replace(case, parameters={**case.parameters,
                                   "native_packages": os.environ["H2_HANGANG_HELPR_PACKAGES"]})
    if case.identifier == "vessel-failure-fragment-flight-handoff"
       and "H2_HANGANG_HELPR_PACKAGES" in os.environ
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _ELVHYS432_SOURCE_ROOT})
    if case.identifier == "elvhys432-pipe-surface-temperature-source-ingest"
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _WSKBIJ_SOURCE_ROOT})
    if case.identifier == "large-scale-h2-explosion-summary-source-ingest"
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _WSKBIJ_SOURCE_ROOT})
    if case.identifier == "large-scale-h2-explosion-test001-source-ingestion"
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _WASSERSTOFFATLAS_SOURCE_ROOT})
    if case.identifier == "wasserstoffatlas-facility-inventory-source-ingest"
    else replace(case, parameters={**case.parameters,
                                   "raw_data_root": _LEAKY_COATING_SOURCE_ROOT})
    if case.identifier == "pd-leaky-coating-sorption-source-ingest"
    else replace(case, parameters={**case.parameters,
                                   "workbook_path": _H2_STATIONS_SOURCE_ROOT
                                   + "/hrs-list-2026-10-31.xlsx"})
    if case.identifier == "h2-stations-source-inventory-schema"
    else replace(case, parameters={**case.parameters,
                                   "run_directory": _CRYO_NEUTRON_SOURCE_RUN})
    if case.identifier == "cryo-neutron-lh2-phase-change-source-ingestion"
    else replace(case, parameters={**case.parameters,
                                   "source_path": _PEM_RIPPLE_SOURCE_MEMBER})
    if case.identifier == "pem-ripple-iv-to-hydrogen-stack-diagnostic"
    else case
    for case in _DISCOVERED_CASES
)

