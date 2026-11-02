"""Curated discovery targets, not a claim that every file has been acquired."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatasetSeed:
    key: str
    provider: str
    identifier: str
    families: tuple[str, ...]
    origin: str = "measured"

    def __post_init__(self):
        for name in ("key", "provider", "identifier", "origin"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Dataset seed {name} must be a nonempty string")
        families = self.families
        if isinstance(families, (str, bytes)) or not isinstance(families, (tuple, list)):
            raise TypeError("Dataset seed families must be a sequence of names")
        families = tuple(families)
        if not families or any(not isinstance(value, str) or not value.strip() for value in families):
            raise ValueError("Dataset seed needs explicit physical-family tags")
        if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in self.key):
            raise ValueError("Dataset seed key must be a safe lowercase identifier")
        if "/" in self.provider or "\\" in self.provider:
            raise ValueError("Dataset seed provider must be a repository identifier")
        object.__setattr__(self, "families", families)


DATASETS = (
    DatasetSeed("hydrogen-channel", "figshare", "26117989", ("dispersion", "release")),
    DatasetSeed("large-scale-open-hydrogen-explosion", "dataverse", "10.18710/WSKBIJ",
                ("combustion", "open_field_explosion", "jet_release", "overpressure")),
    DatasetSeed("wasserstoffatlas-facility-inventory", "zenodo", "10548190",
                ("facility_inventory", "hydrogen_supply_chain", "geospatial_screening"), "compiled_inventory"),
    DatasetSeed("clashach-h2-microct", "zenodo", "10500728",
                ("underground_storage", "pore_scale_imaging", "multiphase_flow"), "measured"),
    DatasetSeed("leaky-coating-hydride-sorption", "zenodo", "6670268",
                ("hydride_kinetics", "hydrogen_diffusion", "sorption_observations"), "measured"),
    DatasetSeed("cryo-neutron-phase-change", "mendeley", "z5zc7kk76g/2",
                ("liquid_hydrogen", "cryogenic_phase_change", "neutron_imaging"), "measured"),
    DatasetSeed("ignited-hydrogen-jet-x044qk", "dataverse", "10.18710/X044QK",
                ("hydrogen_release", "underexpanded_jet", "delayed_ignition", "overpressure")),
    DatasetSeed("grinhy2-electrolysis-transient", "zenodo", "7612826",
                ("electrolysis", "plant_operation", "transient_hydrogen_flow")),
    DatasetSeed("soe-fault-operation", "zenodo", "10648884",
                ("electrolysis", "solid_oxide_electrolysis", "fault_operation", "process_monitoring")),
    DatasetSeed("hydelta-outflow-closed-spaces", "zenodo", "8154318",
                ("hydrogen_release", "enclosure_dispersion", "ventilation", "concentration_build_up")),
    DatasetSeed("hydelta-pressure-station-ventilation", "zenodo", "8164602",
                ("hydrogen_release", "pressure_reducing_station", "cabinet_ventilation", "concentration"), "mixed"),
    DatasetSeed("hysam-sampling-system", "zenodo", "20590842",
                ("hydrogen_transfer", "fuel_sampling", "high_pressure_measurement", "thermal_transient")),
    DatasetSeed("h2-stations-hrs-inventory", "clean-hydrogen-ju", "map-export-2026-10-31",
                ("facility_inventory", "hydrogen_refuelling_stations", "operational_metadata"),
                "compiled_inventory"),
    DatasetSeed("buried-h2-blend-pipeline", "mendeley", "x8zkds4fyn/2",
                ("buried_pipeline_release", "dispersion", "flammable_cloud")),
    DatasetSeed("mechanical-ventilation", "zenodo", "4668554", ("ventilation", "dispersion")),
    DatasetSeed("carpark-unignited", "figshare", "14405903", ("ventilation", "dispersion")),
    DatasetSeed("pressure-unignited", "figshare", "17932439", ("enclosure", "release")),
    DatasetSeed("pressure-ignited", "figshare", "17934047", ("enclosure", "combustion")),
    DatasetSeed("carpark-thermal", "figshare", "17695082", ("fire", "exposure")),
    DatasetSeed("bam-hydrogen-jet-fire", "zenodo", "21026781",
                ("combustion", "jet_flame", "thermal_target")),
    DatasetSeed("elvhys-shock-tube", "dataverse", "10.18710/M5LOLM", ("cryogenic", "rupture", "combustion")),
    DatasetSeed("elvhys432-fireline", "dataverse", "10.18710/HDZLJ1",
                ("cryogenic", "transfer_line", "thermal_observation", "fire_exposure")),
    DatasetSeed("elvhys-cold-room", "dataverse", "10.18710/JXJP0H", ("cryogenic", "enclosure", "dispersion", "ventilation", "sensors")),
    DatasetSeed("oxygen-hypoxia-chamber", "dryad", "10.5061/dryad.t1g1jwtg9", ("oxygen_dilution", "monitoring")),
    DatasetSeed("pem-crossover", "zenodo", "19361280", ("electrolysis", "crossover", "degradation")),
    DatasetSeed("aem-water-electrolysis-crossover", "zenodo", "20068087",
                ("electrolysis", "aem", "crossover", "polarization")),
    DatasetSeed("pem-ripple-degradation", "mendeley", "93jz2rgy4d/2",
                ("electrolysis", "pem", "current_ripple", "polarization", "degradation")),
    DatasetSeed("pemwe-ast-hannover", "luis", "10.25835/yun7znp0",
                ("electrolysis", "pem", "accelerated_stress_test", "operation")),
    DatasetSeed("alkaline-electrolyte-purity-candidate", "4tu", "10.4121/badcd93d-0428-4f18-a3b7-a08da74f1c1c",
                ("electrolysis", "alkaline", "cathode_polarization", "electrolyte_purity")),
    DatasetSeed("lohc-enthalpies", "zenodo", "10926772", ("lohc", "reaction"), "computed"),
    DatasetSeed("pv-pem-dispatch", "zenodo", "22900353", ("electrolysis", "solar"), "mixed"),
    DatasetSeed("pem-grid-system", "dryad", "10.5061/dryad.8931zcs64", ("electrolysis", "system"), "mixed"),
    DatasetSeed("bath-cryo-kinetics", "bath", "BATH-00099",
                ("hydrogen_storage", "adsorption", "cryo_kinetics")),
    DatasetSeed("alkaline-bubble-observations", "mendeley", "r6np4f7gmf/2",
                ("electrolysis", "alkaline", "bubble_diagnostics")),
    DatasetSeed("peace-alkaline-short-stack", "zenodo", "19605474",
                ("electrolysis", "alkaline", "pressurized_stack")),
    DatasetSeed("ab2-hydride-tank", "mendeley", "8km9z62tct/1", ("hydride", "thermal")),
    DatasetSeed("hydrogen-sound-speed", "zenodo", "21355851", ("thermodynamics", "sound_speed"), "compiled_measurements"),
    DatasetSeed("austenite-embrittlement", "zenodo", "23107780", ("materials", "embrittlement"), "compiled_measurements"),
    DatasetSeed("oedi-hydrogen-materials", "openei", "277", ("materials", "fatigue", "fracture"), "compiled_measurements"),
    DatasetSeed("hydrogen-diffusivity-ms1700-qp1180", "mendeley", "zj7zh24frt/1",
                ("materials", "hydrogen_transport", "permeation")),
    DatasetSeed("hydrogen-permeation-ms-ahss-1300", "mendeley", "tnsgf7v76z/1",
                ("materials", "hydrogen_transport", "permeation", "advanced_high_strength_steel")),
    DatasetSeed("hydrogen-core-flood", "mendeley", "rfhf7wjydn/1",
                ("underground_storage", "two_phase_flow", "relative_permeability")),
    DatasetSeed("geological-adsorption", "zenodo", "22305898", ("adsorption", "metrology")),
    DatasetSeed("hydride-pct-simulation", "mendeley", "trpnk55pmz/1", ("hydride", "equilibrium"), "simulated"),
    DatasetSeed("ml-hydpark-screening", "zenodo", "10680097",
                ("hydrogen_storage", "hydride", "materials_screening"), "curated"),
    DatasetSeed("carbon-chemisorption", "mendeley", "vyp4wbhxzr/1", ("adsorption", "chemisorption")),
    DatasetSeed("sofc-polarization", "mendeley", "j8b9v4cb9d/1", ("fuel_cell", "electrochemistry"), "mixed"),
    DatasetSeed("h2safe-indoor", "openei", "8799", ("tracer_dispersion", "ventilation", "sensors")),
    DatasetSeed("hydride-compressor", "zenodo", "19036733", ("hydride", "compression", "thermal")),
    DatasetSeed("dark-fermentation", "mendeley", "2nwcdx9hst/2", ("biological", "fermentation")),
    DatasetSeed("microbial-nutrient-recovery", "zenodo", "13981041", ("microbial_cell", "electrochemistry", "nutrient_recovery"), "mixed"),
    DatasetSeed("tio2-photo-evolution", "zenodo", "15277951", ("photocatalysis", "reaction")),
    DatasetSeed("cds-photo-screen", "zenodo", "7056972", ("photocatalysis", "materials"), "computed"),
    DatasetSeed("cryo-mof-dormancy", "dataverse-fr", "10.57745/FCV2R0", ("adsorption", "cryogenic", "boiloff")),
    DatasetSeed("preslhy-discharge", "radar-kit", "10.35097/1187", ("release", "cryogenic", "blowdown")),
    DatasetSeed("preslhy-pool", "radar-kit", "10.35097/1319", ("pool", "evaporation", "cryogenic")),
    DatasetSeed("nh3-h2-counterflow-flame", "radar-kit", "10.35097/bnpe6n1ppv92yjw4",
                ("combustion", "counterflow_flame", "hydrogen_transport")),
    DatasetSeed("hydrogen-engine-flame-wall", "tudatalib", "dbec6035-12f9-4ba6-b776-7b4ec4b11979",
                ("piston_engine", "combustion", "heat_transfer")),
)
