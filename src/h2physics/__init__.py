"""Composable hydrogen physics with explicit model and evidence boundaries.

Public exports are loaded on first access. Metadata and scheduler tooling can
import their standard-library modules without loading numerical model stacks.
"""

from importlib import import_module as _import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adsorption import AdsorptionSourceObservation, ExtendedLangmuirIsotherm
    from .buoyant_layer import (
        TwoVentHydrogenLayerConfig,
        TwoVentHydrogenLayerResult,
        run_two_vent_hydrogen_layer,
    )
    from .caloric_pipe_finite_wall import (
        FiniteWallCaloricPipeTrace,
        LumpedPipeWall,
        simulate_caloric_pipe_with_finite_wall,
    )
    from .caloric_pipe_network_waves import (
        CaloricPipeNetworkEdge,
        CaloricPipeNetworkNode,
        CaloricPipeNetworkWaveModel,
        CaloricPipeNetworkWaveTrace,
    )
    from .caloric_pipe_nozzle_coupling import CaloricFiniteReservoirNozzleCoupling
    from .caloric_pipe_waves import (
        CaloricDarcyFrictionLaw,
        CaloricGasEOS,
        CaloricPipeReservoirBoundary,
        CaloricPipeWallHeatBoundary,
        CaloricPipeWaveModel,
        CaloricPipeWaveTrace,
        UniformDarcyFriction,
    )
    from .compartment_network import (
        CompartmentMolarTransfer,
        CompartmentNetworkExecutionError,
        CompartmentNetworkModel,
        HydrogenCompartmentNetworkTrace,
        WellMixedCompartment,
        simulate_hydrogen_compartment_network,
    )
    from .cooldown import (
        CooldownSegment,
        CooldownSegmentDuty,
        IsobaricEnthalpyPath,
        LineCooldownEstimate,
        PropertyBackedLineCooldownEstimate,
        estimate_line_cooldown,
        estimate_line_cooldown_with_provider,
    )
    from .core import immutable_array, partial_pressure_pa
    from .detector_reliability import (
        KofNDetectorReliability,
        KofNTrialConfidenceInterval,
        KofNTrialEvidence,
        KofNTrialReliabilityEstimate,
        evaluate_kofn_detector_reliability,
        interval_for_kofn_trials,
        record_kofn_trial_evidence,
        summarize_kofn_trials,
    )
    from .dispersion import (
        DispersionExecution,
        DispersionExecutionError,
        DispersionScenario,
        HydrogenReleaseFamily,
    )
    from .electrochemistry import FuelCellOperatingState, fuel_cell_activity_correction
    from .finite_caloric_pipe_reservoir import FiniteCaloricPipeReservoir
    from .finite_pipe_reservoir import FiniteIsothermalPipeReservoir
    from .isothermal_gas_pipe_network import (
        IsothermalGasPipeNetwork,
        IsothermalGasPipeNetworkTrace,
        IsothermalPipeCell,
        IsothermalPipeLink,
    )
    from .isothermal_pipe_network_waves import (
        IsothermalPipeNetworkEdge,
        IsothermalPipeNetworkNode,
        IsothermalPipeNetworkTrace,
        IsothermalPipeNetworkWaveModel,
    )
    from .isothermal_pipe_waves import (
        IdealHydrogenIsothermalEOS,
        IsothermalPipeWaveModel,
        IsothermalPipeWaveTrace,
    )
    from .mixtures import GasComposition
    from .pipe_nozzle_coupling import FiniteReservoirNozzleCoupling, IsothermalToCaloricStateMapping
    from .pipe_reservoir_boundary import FiniteReservoirPressureBoundary
    from .pipeline_linepack import IsothermalLinepackState, LinepackStepLedger
    from .real_gas_linepack import RealGasLinepackState, RealGasLinepackStepLedger
    from .scenarios import (
        OperationalScenario,
        ScenarioExecutionError,
        ScenarioNode,
        ScenarioNodeResult,
        ScenarioOutput,
        ScenarioResult,
        ScenarioValue,
    )
    from .thermo.isothermal_eos import (
        CoolPropIsothermalEOS,
        CoolPropMixtureIsothermalEOS,
        IsothermalSinglePhaseEOS,
    )

_EXPORT_MODULES = {
    'AdsorptionSourceObservation': '.adsorption',
    'ExtendedLangmuirIsotherm': '.adsorption',
    'TwoVentHydrogenLayerConfig': '.buoyant_layer',
    'TwoVentHydrogenLayerResult': '.buoyant_layer',
    'run_two_vent_hydrogen_layer': '.buoyant_layer',
    'FiniteWallCaloricPipeTrace': '.caloric_pipe_finite_wall',
    'LumpedPipeWall': '.caloric_pipe_finite_wall',
    'simulate_caloric_pipe_with_finite_wall': '.caloric_pipe_finite_wall',
    'CaloricPipeNetworkEdge': '.caloric_pipe_network_waves',
    'CaloricPipeNetworkNode': '.caloric_pipe_network_waves',
    'CaloricPipeNetworkWaveModel': '.caloric_pipe_network_waves',
    'CaloricPipeNetworkWaveTrace': '.caloric_pipe_network_waves',
    'CaloricFiniteReservoirNozzleCoupling': '.caloric_pipe_nozzle_coupling',
    'CaloricDarcyFrictionLaw': '.caloric_pipe_waves',
    'CaloricGasEOS': '.caloric_pipe_waves',
    'CaloricPipeReservoirBoundary': '.caloric_pipe_waves',
    'CaloricPipeWallHeatBoundary': '.caloric_pipe_waves',
    'CaloricPipeWaveModel': '.caloric_pipe_waves',
    'CaloricPipeWaveTrace': '.caloric_pipe_waves',
    'UniformDarcyFriction': '.caloric_pipe_waves',
    'CompartmentMolarTransfer': '.compartment_network',
    'CompartmentNetworkExecutionError': '.compartment_network',
    'CompartmentNetworkModel': '.compartment_network',
    'HydrogenCompartmentNetworkTrace': '.compartment_network',
    'WellMixedCompartment': '.compartment_network',
    'simulate_hydrogen_compartment_network': '.compartment_network',
    'CooldownSegment': '.cooldown',
    'CooldownSegmentDuty': '.cooldown',
    'IsobaricEnthalpyPath': '.cooldown',
    'LineCooldownEstimate': '.cooldown',
    'PropertyBackedLineCooldownEstimate': '.cooldown',
    'estimate_line_cooldown': '.cooldown',
    'estimate_line_cooldown_with_provider': '.cooldown',
    'immutable_array': '.core',
    'partial_pressure_pa': '.core',
    'KofNDetectorReliability': '.detector_reliability',
    'KofNTrialEvidence': '.detector_reliability',
    'KofNTrialConfidenceInterval': '.detector_reliability',
    'KofNTrialReliabilityEstimate': '.detector_reliability',
    'evaluate_kofn_detector_reliability': '.detector_reliability',
    'interval_for_kofn_trials': '.detector_reliability',
    'record_kofn_trial_evidence': '.detector_reliability',
    'summarize_kofn_trials': '.detector_reliability',
    'DispersionExecution': '.dispersion',
    'DispersionExecutionError': '.dispersion',
    'DispersionScenario': '.dispersion',
    'HydrogenReleaseFamily': '.dispersion',
    'FuelCellOperatingState': '.electrochemistry',
    'fuel_cell_activity_correction': '.electrochemistry',
    'FiniteCaloricPipeReservoir': '.finite_caloric_pipe_reservoir',
    'FiniteIsothermalPipeReservoir': '.finite_pipe_reservoir',
    'IsothermalGasPipeNetwork': '.isothermal_gas_pipe_network',
    'IsothermalGasPipeNetworkTrace': '.isothermal_gas_pipe_network',
    'IsothermalPipeCell': '.isothermal_gas_pipe_network',
    'IsothermalPipeLink': '.isothermal_gas_pipe_network',
    'IsothermalPipeNetworkEdge': '.isothermal_pipe_network_waves',
    'IsothermalPipeNetworkNode': '.isothermal_pipe_network_waves',
    'IsothermalPipeNetworkTrace': '.isothermal_pipe_network_waves',
    'IsothermalPipeNetworkWaveModel': '.isothermal_pipe_network_waves',
    'IdealHydrogenIsothermalEOS': '.isothermal_pipe_waves',
    'IsothermalPipeWaveModel': '.isothermal_pipe_waves',
    'IsothermalPipeWaveTrace': '.isothermal_pipe_waves',
    'GasComposition': '.mixtures',
    'FiniteReservoirNozzleCoupling': '.pipe_nozzle_coupling',
    'IsothermalToCaloricStateMapping': '.pipe_nozzle_coupling',
    'FiniteReservoirPressureBoundary': '.pipe_reservoir_boundary',
    'IsothermalLinepackState': '.pipeline_linepack',
    'LinepackStepLedger': '.pipeline_linepack',
    'RealGasLinepackState': '.real_gas_linepack',
    'RealGasLinepackStepLedger': '.real_gas_linepack',
    'OperationalScenario': '.scenarios',
    'ScenarioExecutionError': '.scenarios',
    'ScenarioNode': '.scenarios',
    'ScenarioNodeResult': '.scenarios',
    'ScenarioOutput': '.scenarios',
    'ScenarioResult': '.scenarios',
    'ScenarioValue': '.scenarios',
    'CoolPropIsothermalEOS': '.thermo.isothermal_eos',
    'CoolPropMixtureIsothermalEOS': '.thermo.isothermal_eos',
    'IsothermalSinglePhaseEOS': '.thermo.isothermal_eos',
}
_SUBMODULES = ('adsorption', 'buoyant_layer', 'caloric_pipe_finite_wall', 'caloric_pipe_network_waves', 'caloric_pipe_nozzle_coupling', 'caloric_pipe_waves', 'compartment_network', 'cooldown', 'core', 'detector_reliability', 'dispersion', 'electrochemistry', 'finite_caloric_pipe_reservoir', 'finite_pipe_reservoir', 'isothermal_gas_pipe_network', 'isothermal_pipe_network_waves', 'isothermal_pipe_waves', 'mixtures', 'pipe_nozzle_coupling', 'pipe_reservoir_boundary', 'pipeline_linepack', 'real_gas_linepack', 'scenarios', 'thermo')

__version__ = "0.1.0.dev0"

__all__ = ["AdsorptionSourceObservation", "ExtendedLangmuirIsotherm",
           "TwoVentHydrogenLayerConfig", "TwoVentHydrogenLayerResult",
           "run_two_vent_hydrogen_layer", "CooldownSegment", "CooldownSegmentDuty",
           "KofNDetectorReliability", "KofNTrialEvidence", "KofNTrialReliabilityEstimate",
           "KofNTrialConfidenceInterval", "evaluate_kofn_detector_reliability",
           "interval_for_kofn_trials", "record_kofn_trial_evidence", "summarize_kofn_trials",
           "WellMixedCompartment", "CompartmentMolarTransfer", "CompartmentNetworkModel",
           "HydrogenCompartmentNetworkTrace", "CompartmentNetworkExecutionError",
           "simulate_hydrogen_compartment_network",
           "DispersionExecution", "DispersionExecutionError", "DispersionScenario",
           "FuelCellOperatingState", "GasComposition", "HydrogenReleaseFamily",
           "IsothermalGasPipeNetwork", "IsothermalGasPipeNetworkTrace",
           "IsothermalPipeCell", "IsothermalPipeLink",
           "IsothermalPipeWaveModel", "IsothermalPipeWaveTrace",
           "CaloricGasEOS", "CaloricDarcyFrictionLaw", "UniformDarcyFriction",
           "CaloricPipeWallHeatBoundary", "CaloricPipeReservoirBoundary",
           "CaloricPipeWaveModel", "CaloricPipeWaveTrace",
           "LumpedPipeWall", "FiniteWallCaloricPipeTrace",
           "simulate_caloric_pipe_with_finite_wall",
           "CaloricPipeNetworkEdge", "CaloricPipeNetworkNode",
           "CaloricPipeNetworkWaveModel", "CaloricPipeNetworkWaveTrace",
           "IsothermalPipeNetworkEdge", "IsothermalPipeNetworkNode",
           "IsothermalPipeNetworkTrace", "IsothermalPipeNetworkWaveModel",
           "FiniteReservoirPressureBoundary",
           "FiniteIsothermalPipeReservoir",
           "FiniteCaloricPipeReservoir",
           "CaloricFiniteReservoirNozzleCoupling",
           "FiniteReservoirNozzleCoupling", "IsothermalToCaloricStateMapping",
           "IdealHydrogenIsothermalEOS", "IsothermalSinglePhaseEOS",
           "CoolPropIsothermalEOS", "CoolPropMixtureIsothermalEOS",
           "OperationalScenario", "ScenarioExecutionError", "ScenarioNode",
           "ScenarioNodeResult", "ScenarioOutput", "ScenarioResult", "ScenarioValue",
           "IsobaricEnthalpyPath",
           "LineCooldownEstimate", "PropertyBackedLineCooldownEstimate",
           "IsothermalLinepackState", "LinepackStepLedger",
           "RealGasLinepackState", "RealGasLinepackStepLedger",
           "estimate_line_cooldown", "estimate_line_cooldown_with_provider",
           "fuel_cell_activity_correction",
           "partial_pressure_pa",
           "immutable_array",
           "__version__"]


def __getattr__(name):
    module = _EXPORT_MODULES.get(name)
    if module is not None:
        value = getattr(_import_module(module, __name__), name)
    elif name in _SUBMODULES:
        value = _import_module('.' + name, __name__)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__) | set(_SUBMODULES))
