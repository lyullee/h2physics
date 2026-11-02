"""Pointwise comparison of admitted acoustic observations with an EOS provider."""

import math
from dataclasses import dataclass

from ..data.hydrogen_sound_speed import HydrogenAcousticDataset, HydrogenAcousticFile
from ..data.pif import acoustic_columns
from ..thermo.coolprop import CoolPropProperties


@dataclass(frozen=True, slots=True)
class AcousticEOSPoint:
    row_id: str
    temperature_k: float
    pressure_pa: float
    observed_speed_m_s: float
    predicted_speed_m_s: float
    source_phase: str = "unspecified"
    predicted_phase: str = "unknown"

    @property
    def phase_matches(self):
        """Compare liquid/gas families; None leaves unclassified phases unresolved."""
        source = {"liquid": "liquid", "gas": "gas", "vapor": "gas"}.get(self.source_phase)
        predicted = {"liquid": "liquid", "supercritical_liquid": "liquid",
                     "gas": "gas", "supercritical_gas": "gas"}.get(self.predicted_phase)
        if source is None or predicted is None:
            return None
        return source == predicted

    @property
    def residual_m_s(self):
        return self.predicted_speed_m_s - self.observed_speed_m_s

    @property
    def relative_error_percent(self):
        return 100. * self.residual_m_s / self.observed_speed_m_s


@dataclass(frozen=True, slots=True)
class AcousticEOSExclusion:
    row_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class AcousticEOSTrace:
    dataset: HydrogenAcousticDataset
    source_file: HydrogenAcousticFile
    provider: CoolPropProperties
    provider_signature: tuple
    points: tuple[AcousticEOSPoint, ...]
    exclusions: tuple[AcousticEOSExclusion, ...]
    _binding: tuple

    def require_current(self):
        self.dataset.require_current()
        if self._binding != (id(self.dataset), id(self.source_file), id(self.provider),
                             self.provider_signature, self.points, self.exclusions):
            raise ValueError("Acoustic comparison lost its source or result binding")
        if _provider_signature(self.provider) != self.provider_signature:
            raise ValueError("Acoustic comparison provider identity or settings changed")
        points, exclusions = _evaluate(self.dataset, self.source_file, self.provider)
        if points != self.points or exclusions != self.exclusions:
            raise ValueError("Acoustic comparison no longer reproduces from its owners")
        return self


def _provider_signature(provider):
    basis = provider.basis
    return (id(provider), type(provider).__module__, type(provider).__qualname__,
            basis.fluid, basis.spin_composition, basis.reference_id,
            provider.backend, provider.version, provider.internal_energy_policy)


def _evaluate(dataset, source_file, provider):
    metadata = source_file.property_file.metadata
    composition = metadata.get("_exptl_material_composition", "").strip().casefold()
    expected_spin = {"normal-h2": "normal", "para-h2": "para"}.get(composition)
    if expected_spin is None:
        raise ValueError("Source spin composition is absent or unsupported; no EOS comparison is admitted")
    if provider.basis.spin_composition != expected_spin:
        raise ValueError("Source spin composition does not match the EOS provider basis")
    points, exclusions = [], []
    source_phase = metadata.get("_exptl_material_state", "unspecified").strip().casefold()
    row_offset = 0
    for loop in source_file.property_file.loops:
        temperatures, pressures, speeds = acoustic_columns(source_file.property_file, loop)
        for index, (temperature, pressure, observed) in enumerate(zip(temperatures, pressures, speeds)):
            row_id = source_file.source_rows[row_offset]
            row_offset += 1
            if not all(math.isfinite(float(v)) for v in (temperature, pressure, observed)):
                exclusions.append(AcousticEOSExclusion(row_id, "missing or non-finite T, p, or sound speed"))
                continue
            if temperature <= 0. or pressure <= 0. or observed <= 0.:
                exclusions.append(AcousticEOSExclusion(row_id, "non-positive T, p, or sound speed"))
                continue
            try:
                state = provider.state_pt(float(pressure), float(temperature))
                predicted = state.speed_of_sound_m_s
                if predicted is None or not math.isfinite(float(predicted)) or predicted <= 0.:
                    exclusions.append(AcousticEOSExclusion(row_id, "EOS did not return a finite positive speed of sound"))
                    continue
                points.append(AcousticEOSPoint(row_id, float(temperature), float(pressure),
                                               float(observed), float(predicted),
                                               source_phase, state.phase))
            except (ValueError, RuntimeError, OverflowError) as exc:
                exclusions.append(AcousticEOSExclusion(row_id, f"EOS state unavailable: {type(exc).__name__}"))
    if row_offset != len(source_file.source_rows):
        raise ValueError("Acoustic row identifiers do not align with parsed source tables")
    return tuple(points), tuple(exclusions)


def compare_acoustic_file_with_eos(dataset: HydrogenAcousticDataset, member_path: str,
                                   provider: CoolPropProperties) -> AcousticEOSTrace:
    """Compare one exact source member pointwise; does not fit or extrapolate."""
    if type(dataset) is not HydrogenAcousticDataset:
        raise TypeError("Supply a hash-verified admitted acoustic dataset")
    if type(provider) is not CoolPropProperties:
        raise TypeError("Supply the existing CoolPropProperties provider")
    dataset.require_current()
    source_file = dataset.file(member_path)
    signature = _provider_signature(provider)
    points, exclusions = _evaluate(dataset, source_file, provider)
    binding = (id(dataset), id(source_file), id(provider), signature, points, exclusions)
    return AcousticEOSTrace(dataset, source_file, provider, signature, points, exclusions, binding)


__all__ = ["AcousticEOSExclusion", "AcousticEOSPoint", "AcousticEOSTrace",
           "compare_acoustic_file_with_eos"]
