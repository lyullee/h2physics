"""Storage models whose parameters and physical closures are supplied explicitly."""

from importlib import import_module

from .hydride import (
    ArrheniusRate,
    HydrideBed,
    HydrideBoundary,
    HydrideKinetics,
    HydrideParameters,
    HydrideState,
    VanthoffPlateau,
)
from .microsphere import MicrosphereDomain, MicrosphereResult, MicrosphereStorage
from .product_delivery import AdsorptionProductMassFlow

__all__ = ["ArrheniusRate", "HydrideBed", "HydrideBoundary", "HydrideKinetics",
           "HydrideParameters", "HydrideState", "VanthoffPlateau", "MicrosphereDomain",
           "MicrosphereResult", "MicrosphereStorage", "AdsorptionProductMassFlow"]

_LAZY_EXPORTS = {
    "BoundHydrogenEnergyReference": (".finite_hydride", "BoundHydrogenEnergyReference"),
    "FiniteHydrideBed": (".finite_hydride", "FiniteHydrideBed"),
    "FiniteHydrideDomain": (".finite_hydride", "FiniteHydrideDomain"),
    "FiniteHydrideGasPortBoundary": (".finite_hydride", "FiniteHydrideGasPortBoundary"),
    "FiniteHydrideGasPortInput": (".finite_hydride", "FiniteHydrideGasPortInput"),
    "FiniteHydrideHeatBoundary": (".finite_hydride", "FiniteHydrideHeatBoundary"),
    "FiniteHydrideHeatInput": (".finite_hydride", "FiniteHydrideHeatInput"),
    "FiniteHydrideIntegrationError": (".finite_hydride", "FiniteHydrideIntegrationError"),
    "FiniteHydrideRates": (".finite_hydride", "FiniteHydrideRates"),
    "FiniteHydrideSnapshot": (".finite_hydride", "FiniteHydrideSnapshot"),
    "FiniteHydrideTrace": (".finite_hydride", "FiniteHydrideTrace"),
    "HydrideGasThermodynamics": (".finite_hydride", "HydrideGasThermodynamics"),
    "PorousReservoir": (".porous_reservoir", "PorousReservoir"),
    "PorousReservoirGeometry": (".porous_reservoir", "PorousReservoirGeometry"),
    "PorousReservoirResult": (".porous_reservoir", "PorousReservoirResult"),
    "PorousReservoirSchedule": (".porous_reservoir", "PorousReservoirSchedule"),
    "HydrideCompressorEvidence": (".hydride_compressor", "HydrideCompressorEvidence"),
    "HydrideCompressorIntegrationError": (".hydride_compressor", "HydrideCompressorIntegrationError"),
    "HydrideCompressorNative": (".hydride_compressor", "HydrideCompressorNative"),
    "HydrideCompressorPoint": (".hydride_compressor", "HydrideCompressorPoint"),
    "HydrideCompressorSegment": (".hydride_compressor", "HydrideCompressorSegment"),
    "HydrideCompressorSnapshot": (".hydride_compressor", "HydrideCompressorSnapshot"),
    "HydrideCompressorStage": (".hydride_compressor", "HydrideCompressorStage"),
    "HydrideCompressorTrace": (".hydride_compressor", "HydrideCompressorTrace"),
    "FiniteHydrideGasVessel": (".hydride_compressor", "FiniteHydrideGasVessel"),
    "HydrideThermalCompressor": (".hydride_compressor", "HydrideThermalCompressor"),
    "AdsorptionBoundaryRates": (".adsorption_dynamics", "AdsorptionBoundaryRates"),
    "AdsorptionDynamicState": (".adsorption_dynamics", "AdsorptionDynamicState"),
    "AdsorptionDynamicsInputs": (".adsorption_dynamics", "AdsorptionDynamicsInputs"),
    "AdsorptionDynamicsTrace": (".adsorption_dynamics", "AdsorptionDynamicsTrace"),
    "integrate_adsorption_dynamics": (".adsorption_dynamics", "integrate_adsorption_dynamics"),
}

__all__ += list(_LAZY_EXPORTS)


def __getattr__(name: str):
    """Load finite/native storage models only when a caller requests them."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = _LAZY_EXPORTS[name]
    value = getattr(import_module(module, __name__), attribute)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY_EXPORTS))
