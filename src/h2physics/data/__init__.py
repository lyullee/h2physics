"""Explicit public-data discovery and reproducible acquisition."""

from importlib import import_module

from .acquire import AcquisitionReport, ReplayBudget, acquire_dataset, replay_receipt
from .ahss1300_permeation import AHSS1300Permeation, load_ahss1300_permeation
from .bam_jet_fire import (
    BAMJetFireTable,
    BAMJetFireUnitProjection,
    BAMRawChannel,
    BAMUnitChannel,
    load_bam_jet_fire_text,
    load_bam_jet_fire_unit_view,
    project_bam_jet_fire_units,
)
from .bath_cryo_kinetics import (
    BathKineticObservation,
    BathKineticSeries,
    load_bath_kinetic_workbook,
)
from .buried_pipeline import (
    BuriedPipelineColumnSeries,
    BuriedPipelineNumericTable,
    load_buried_pipeline_numeric_table,
)
from .catalog import DATASETS, DatasetSeed
from .cryo_mof import CryoMOFIsothermTable, CryoMOFObservation, load_cryo_mof_isotherm
from .embrittlement import EmbrittlementCollection
from .geological_adsorption import (
    GeologicalAdsorptionIsotherm,
    GeologicalAdsorptionPoint,
    GeologicalSurfaceExcessProvider,
    load_geological_adsorption_isotherm,
)
from .grinhy2 import GrInHy2FlowSeries, load_grinhy2_flow
from .sofc_polarization import SOFCPolarizationData, load_sofc_polarization_data
from .geological_calibration import (
    GeologicalCalibrationData,
    GeologicalCalibrationRow,
    ReportedSIQuantity,
    load_geological_calibration,
)
from .hdf5_inventory import HDF5MetadataInventory, HDF5ObjectMetadata, inspect_hdf5_metadata
from .hydrogen_channel import HydrogenChannelCase, load_hydrogen_channel_case
from .hydrogen_core_flood import CoreFloodTable, HydrogenCoreFlood, load_hydrogen_core_flood
from .hydrogen_sound_speed import (
    HydrogenAcousticDataset, HydrogenAcousticFile, load_hydrogen_acoustic_dataset,
)
from .hysam_sampling import HySamWorkbook, load_hysam_workbook
from .h2_stations import H2StationRecord, H2StationWorkbook, load_h2_stations_workbook
from .h2safe_indoor import H2SafeIndoorSeries, H2SafeSensor, load_h2safe_indoor_series
from .ignited_hydrogen_jet import (
    IgnitedHydrogenJetMatrix,
    IgnitedJetExperiment,
    load_ignited_hydrogen_jet_matrix,
)
from .mec_electrodes import (
    MecDataIssue,
    MecElectrodeDataset,
    MecElectrodeSeries,
    MecImpedanceTrace,
    load_cora_mec_electrode_dataset,
)
from .mendeley_permeation import (
    MendeleyPermeationDataset,
    NormalizedPermeationSeries,
    load_mendeley_normalized_permeation,
)
from .models import Dataset, RemoteFile
from .oedi_fatigue import FatigueGrowthSeries, OediFatigueDataset, load_oedi_4130x_fatigue
from .peace_alkaline import (
    PEACEChannelDescription,
    PEACEColumnDescriptionMap,
    PEACEObservationBlock,
    PEACESIObservationBlock,
    PEACESourceSeries,
    PEACEUnitSeries,
    SourceTokenTable,
    load_column_descriptions as load_peace_alkaline_column_descriptions,
    load_raw_file as load_peace_alkaline_raw_file,
    project_source_observations as project_peace_alkaline_observations,
    normalize_unambiguous_channels as normalize_peace_alkaline_channels,
    read_raw_token_table,
)
from .repositories import resolve_dataset, dataset_from_mendeley_bytes, dataset_from_figshare_bytes
from .rodare_alkaline_bubbles import (
    RODAREAlkalineBubbleCondition,
    RODAREAlkalineBubbleIndex,
    load_rodare_alkaline_bubble_index,
)

__all__ = [
    "AcquisitionReport",
    "DATASETS",
    "Dataset",
    "DatasetSeed",
    "RODAREAlkalineBubbleCondition",
    "RODAREAlkalineBubbleIndex",
    "load_rodare_alkaline_bubble_index",
    "CryoMOFIsothermTable",
    "CryoMOFObservation",
    "load_cryo_mof_isotherm",
    "AHSS1300Permeation",
    "load_ahss1300_permeation",
    "BAMJetFireTable",
    "BathKineticObservation",
    "BathKineticSeries",
    "load_bath_kinetic_workbook",
    "BAMJetFireUnitProjection",
    "BAMRawChannel",
    "BAMUnitChannel",
    "load_bam_jet_fire_text",
    "load_bam_jet_fire_unit_view",
    "project_bam_jet_fire_units",
    "HDF5MetadataInventory",
    "HDF5ObjectMetadata",
    "inspect_hdf5_metadata",
    "BuriedPipelineNumericTable",
    "BuriedPipelineColumnSeries",
    "load_buried_pipeline_numeric_table",
    "EmbrittlementCollection",
    "GeologicalAdsorptionIsotherm",
    "GeologicalAdsorptionPoint",
    "GeologicalSurfaceExcessProvider",
    "GrInHy2FlowSeries",
    "load_grinhy2_flow",
    "SOFCPolarizationData",
    "load_sofc_polarization_data",
    "GeologicalCalibrationData",
    "GeologicalCalibrationRow",
    "ReportedSIQuantity",
    "load_geological_calibration",
    "HydrogenChannelCase",
    "load_hydrogen_channel_case",
    "CoreFloodTable",
    "HydrogenCoreFlood",
    "load_hydrogen_core_flood",
    "HydrogenAcousticDataset",
    "HydrogenAcousticFile",
    "load_hydrogen_acoustic_dataset",
    "HySamWorkbook",
    "load_hysam_workbook",
    "H2SafeIndoorSeries",
    "H2SafeSensor",
    "load_h2safe_indoor_series",
    "IgnitedHydrogenJetMatrix",
    "IgnitedJetExperiment",
    "load_ignited_hydrogen_jet_matrix",
    "RemoteFile",
    "ReplayBudget",
    "MendeleyPermeationDataset",
    "NormalizedPermeationSeries",
    "load_mendeley_normalized_permeation",
    "acquire_dataset",
    "replay_receipt",
    "resolve_dataset",
    "dataset_from_mendeley_bytes",
    "dataset_from_figshare_bytes",
    "MecDataIssue",
    "MecElectrodeDataset",
    "MecElectrodeSeries",
    "MecImpedanceTrace",
    "load_cora_mec_electrode_dataset",
    "FatigueGrowthSeries",
    "OediFatigueDataset",
    "load_oedi_4130x_fatigue",
    "SourceTokenTable",
    "PEACEChannelDescription",
    "PEACEColumnDescriptionMap",
    "PEACEObservationBlock",
    "PEACESIObservationBlock",
    "PEACESourceSeries",
    "PEACEUnitSeries",
    "load_peace_alkaline_raw_file",
    "load_peace_alkaline_column_descriptions",
    "project_peace_alkaline_observations",
    "normalize_peace_alkaline_channels",
    "read_raw_token_table",
    "load_geological_adsorption_isotherm",
    "OediFatigueComparison",
    "OediFatigueComparisonError",
    "OediFatiguePoint",
    "compare_oedi_fatigue_series",
]

_OEDI_COMPARISON_EXPORTS = frozenset({
    "OediFatigueComparison",
    "OediFatigueComparisonError",
    "OediFatiguePoint",
    "compare_oedi_fatigue_series",
})

_PEM_RIPPLE_EXPORTS = frozenset({
    "PemRippleArchive", "PemRippleContinuousTrace", "PemRippleFitRecord", "PemRippleFitTable",
    "PemRippleIVCurve", "load_pem_ripple_archive", "load_pem_ripple_continuous_trace",
    "load_pem_ripple_fit_table", "load_pem_ripple_iv_curve",
})
__all__ += sorted(_PEM_RIPPLE_EXPORTS)

_ML_HYDPARK_EXPORTS = frozenset({
    "MLHydPARKRow", "MLHydPARKTable", "load_ml_hydpark_screening",
})
__all__ += sorted(_ML_HYDPARK_EXPORTS)

_AEM_ELECTROLYSIS_EXPORTS = frozenset({
    "AEMElectrolysisWorkbook", "AEMWorkbookCell", "AEMWorksheetSnapshot",
    "load_aem_electrolysis_workbook",
})
__all__ += sorted(_AEM_ELECTROLYSIS_EXPORTS)


def __getattr__(name: str):
    """Load comparison/source facades only when a caller requests them."""
    if name in _OEDI_COMPARISON_EXPORTS:
        module = import_module("..adapters.oedi_fatigue", __name__)
    elif name in _PEM_RIPPLE_EXPORTS:
        module = import_module(".pem_ripple", __name__)
    elif name in _ML_HYDPARK_EXPORTS:
        module = import_module(".ml_hydpark", __name__)
    elif name in _AEM_ELECTROLYSIS_EXPORTS:
        module = import_module(".aem_water_electrolysis", __name__)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | _OEDI_COMPARISON_EXPORTS | _PEM_RIPPLE_EXPORTS
                  | _ML_HYDPARK_EXPORTS)


from .pressure_ignited import IgnitedFlowBlock, PressureIgnitedRun, load_pressure_ignited_mat

__all__ += ["IgnitedFlowBlock", "PressureIgnitedRun", "load_pressure_ignited_mat"]

from .hfcev_fleet import HFCEVOperationRow, HFCEVOperationSample, read_hfcev_operation_sample

__all__ += ["HFCEVOperationRow", "HFCEVOperationSample", "read_hfcev_operation_sample"]

from .elvhys41 import (
    ELVHYS41ConcentrationRow, ELVHYS41ConcentrationSample,
    load_elvhys41_concentration_csv,
)

__all__ += ["ELVHYS41ConcentrationRow", "ELVHYS41ConcentrationSample",
            "load_elvhys41_concentration_csv"]

from .elvhys432 import (
    ELVHYS432TemperatureRow, ELVHYS432TemperatureSample,
    load_elvhys432_temperature_csv,
)

__all__ += ["ELVHYS432TemperatureRow", "ELVHYS432TemperatureSample",
            "load_elvhys432_temperature_csv"]

from .wskbij_summary import (
    WSKBIJExperimentSummaryRow, WSKBIJExperimentSummary,
    read_wskbij_experiment_summary,
)

__all__ += ["WSKBIJExperimentSummaryRow", "WSKBIJExperimentSummary",
            "read_wskbij_experiment_summary"]

from .wskbij_test001 import (
    WSKBIJTest001Sample, WSKBIJTest001Trace, read_wskbij_test001_trace,
)

__all__ += ["WSKBIJTest001Sample", "WSKBIJTest001Trace",
            "read_wskbij_test001_trace"]

from .hydrogen_map import HydrogenMapFacility, HydrogenMapInventory, read_hydrogen_map_inventory

__all__ += ["HydrogenMapFacility", "HydrogenMapInventory", "read_hydrogen_map_inventory"]

from .leaky_coating_sorption import (
    LeakyCoatingSorptionData, SorptionSourcePair, SorptionTrace,
    read_leaky_coating_sorption_data,
)

__all__ += ["LeakyCoatingSorptionData", "SorptionSourcePair", "SorptionTrace",
            "read_leaky_coating_sorption_data"]

from .cryo_neutron_phase_change import (
    CryoNeutronDAQPoint, CryoNeutronImagePoint, CryoNeutronRateWindow,
    CryoNeutronPhaseChangeRun, load_cryo_neutron_phase_change_run,
)

__all__ += ["CryoNeutronDAQPoint", "CryoNeutronImagePoint", "CryoNeutronRateWindow",
            "CryoNeutronPhaseChangeRun", "load_cryo_neutron_phase_change_run"]

from .am316l_workbooks import (
    AM316LWorksheetSnapshot,
    AM316LWorkbookSnapshot,
    read_am316l_workbook,
)

__all__ += ["AM316LWorksheetSnapshot", "AM316LWorkbookSnapshot", "read_am316l_workbook"]

__all__ += ["H2StationRecord", "H2StationWorkbook", "load_h2_stations_workbook"]
