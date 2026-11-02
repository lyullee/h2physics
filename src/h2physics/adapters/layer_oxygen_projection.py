"""Composition-only projection from an H2/fixed-dry-air upper layer.

This adapter does not create a homogeneous-room or human-response result.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ..buoyant_layer import TwoVentHydrogenLayerResult


@dataclass(frozen=True, slots=True)
class LayerOxygenProjection:
    """O2 mole-fraction samples derived from one retained upper-layer trace."""

    layer_trace: TwoVentHydrogenLayerResult
    carrier_basis: str
    carrier_oxygen_mole_fraction: float
    time_s: tuple[float, ...]
    upper_oxygen_mole_fraction: tuple[float, ...]
    carrier_dry_air_mole_fractions: tuple[float, ...] = ()

    def __post_init__(self):
        if type(self.layer_trace) is not TwoVentHydrogenLayerResult:
            raise TypeError("Retain the original two-vent layer result")
        if self.carrier_basis != "fixed_dry_air":
            raise ValueError("Only a fixed-composition dry-air carrier is supported")
        x_air = _oxygen_fraction(self.carrier_oxygen_mole_fraction)
        if self.carrier_dry_air_mole_fractions != _require_carrier_binding(self.layer_trace, x_air):
            raise ValueError("Retain the complete native N2/O2/Ar carrier composition")
        if self.time_s is not self.layer_trace.time_s:
            raise ValueError("Keep the exact timestamp tuple from the source layer result")
        if len(self.time_s) != len(self.layer_trace.upper_h2_mole_fraction):
            raise ValueError("Layer timestamps and H2 samples must have equal lengths")
        expected = tuple(
            (1.0 - _h2_fraction(x_h2)) * x_air
            for x_h2 in self.layer_trace.upper_h2_mole_fraction
        )
        if self.upper_oxygen_mole_fraction != expected:
            raise ValueError("O2 samples must follow the retained binary-composition projection")

    def require_current(self) -> LayerOxygenProjection:
        """Recheck trace identity and every projected composition sample."""
        if type(self.layer_trace) is not TwoVentHydrogenLayerResult:
            raise TypeError("Retain the original two-vent layer result")
        if self.carrier_basis != "fixed_dry_air":
            raise ValueError("Only a fixed-composition dry-air carrier is supported")
        x_air = _oxygen_fraction(self.carrier_oxygen_mole_fraction)
        if self.carrier_dry_air_mole_fractions != _require_carrier_binding(self.layer_trace, x_air):
            raise ValueError("Retained native N2/O2/Ar carrier composition changed")
        if self.time_s is not self.layer_trace.time_s:
            raise ValueError("The source trace clock identity changed")
        if len(self.time_s) != len(self.layer_trace.upper_h2_mole_fraction):
            raise ValueError("Layer timestamps and H2 samples must have equal lengths")
        if len(self.time_s) < 2 or any(
            not isfinite(float(t)) for t in self.time_s
        ) or any(right <= left for left, right in zip(self.time_s[:-1], self.time_s[1:], strict=True)):
            raise ValueError("Source timestamps must be finite and strictly increasing")
        expected = tuple(
            (1.0 - _h2_fraction(x_h2)) * x_air
            for x_h2 in self.layer_trace.upper_h2_mole_fraction
        )
        if self.upper_oxygen_mole_fraction != expected:
            raise ValueError("Projected O2 composition no longer matches its source trace")
        return self


def _require_carrier_binding(trace, oxygen_fraction):
    fractions = trace.dry_air_mole_fractions
    if not trace.property_backend_id and not fractions:
        # Historical analytical traces carry no independently declared carrier.
        return ()
    if (not isinstance(trace.property_backend_id, str)
            or not trace.property_backend_id.startswith("CoolProp:")
            or len(fractions) != 3
            or any(not isfinite(float(value)) or value <= 0. for value in fractions)
            or abs(sum(fractions)-1.) > 1.e-12):
        raise ValueError("Native layer trace needs its normalized N2/O2/Ar carrier basis")
    if abs(oxygen_fraction-fractions[1]) > 1.e-12:
        raise ValueError("Declared O2 fraction differs from the native layer carrier")
    return tuple(fractions)


def _oxygen_fraction(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("Declare carrier O2 as a mole fraction")
    result = float(value)
    if not isfinite(result) or not 0.0 < result <= 1.0:
        raise ValueError("Carrier O2 mole fraction must lie in (0, 1]")
    return result


def _h2_fraction(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("Layer H2 composition must be a mole fraction")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError("Layer H2 mole fraction must lie in [0, 1]")
    return result


def project_layer_oxygen(
    layer_trace: TwoVentHydrogenLayerResult,
    *,
    carrier_basis: str,
    carrier_oxygen_mole_fraction: float,
) -> LayerOxygenProjection:
    """Project upper-layer O2 for the declared binary H2 + fixed dry-air case.

    The complement of H2 is assumed to retain exactly the caller-provided dry
    air composition. No oxygen threshold, partial pressure, exposure duration,
    room-average value or physiological response is inferred.
    """
    if type(layer_trace) is not TwoVentHydrogenLayerResult:
        raise TypeError("Use an actual two-vent upper-layer result")
    if carrier_basis != "fixed_dry_air":
        raise ValueError("Only a fixed dry-air carrier is currently represented")
    x_air = _oxygen_fraction(carrier_oxygen_mole_fraction)
    carrier_fractions = _require_carrier_binding(layer_trace, x_air)
    time = layer_trace.time_s
    if len(time) < 2 or any(
        not isfinite(float(t)) for t in time
    ) or any(right <= left for left, right in zip(time[:-1], time[1:], strict=True)):
        raise ValueError("Source timestamps must be finite and strictly increasing")
    oxygen = tuple(
        (1.0 - _h2_fraction(x_h2)) * x_air
        for x_h2 in layer_trace.upper_h2_mole_fraction
    )
    if len(oxygen) != len(time):
        raise ValueError("Layer timestamps and H2 samples must have equal lengths")
    return LayerOxygenProjection(
        layer_trace,
        carrier_basis,
        x_air,
        time,
        oxygen,
        carrier_fractions,
    ).require_current()
