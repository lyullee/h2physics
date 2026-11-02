"""Source-bound measured-point bridge to the existing hydrogen stack model.

This module does not fit a stack or infer cell/stack sensor semantics. It
provides caller-selected, same-row electrical and temperature inputs to an
existing ``HydrogenStack`` and retains measured voltage for comparison.
"""

from dataclasses import dataclass

from ..core import finite
from ..data.peace_alkaline import PEACESIObservationBlock
from ..electrochemistry import HydrogenStack, StackResult


@dataclass(frozen=True, slots=True)
class PEACEElectrolysisPoint:
    """One source-row operating point; source clock remains an unparsed token."""

    row_index: int
    time_token: str
    current_a: float
    temperature_k: float
    measured_voltage_v: float
    stack_result: StackResult

    @property
    def voltage_residual_v(self) -> float:
        """Model stack voltage minus the publisher's reported total voltage."""
        return self.stack_result.stack_voltage_v - self.measured_voltage_v


@dataclass(frozen=True, slots=True)
class PEACEElectrolysisProfile:
    """Explicit caller mapping of source channels to existing model inputs."""

    source: PEACESIObservationBlock
    temperature_channel_id: str
    electrical_scope_evidence_id: str
    temperature_mapping_evidence_id: str
    omitted_rows: tuple[tuple[int, str], ...]

    def require_current(self):
        self.source.require_current()
        if (not isinstance(self.electrical_scope_evidence_id, str)
                or not self.electrical_scope_evidence_id.strip()
                or not isinstance(self.temperature_mapping_evidence_id, str)
                or not self.temperature_mapping_evidence_id.strip()):
            raise ValueError("Profile lost its explicit electrical or temperature mapping evidence")
        series = next((item for item in self.source.temperatures
                       if item.source.description.source_channel_id == self.temperature_channel_id), None)
        if series is None:
            raise ValueError("Profile temperature channel is absent from the retained source projection")
        expected = _omitted_rows(self.source, series)
        if self.omitted_rows != expected:
            raise ValueError("Profile missing-row receipt differs from its source projection")
        return self

    def evaluate(self, stack: HydrogenStack, *, faradaic_efficiency: float = 1.0):
        """Evaluate only measured rows; no interpolation or extrapolation occurs.

        The caller must provide a stack whose geometry and series-cell count
        match the interpretation identified by ``electrical_scope_evidence_id``.
        The selected publisher temperature is passed directly as the model
        temperature; its physical representativeness is caller-owned evidence.
        """
        self.require_current()
        if type(stack) is not HydrogenStack:
            raise TypeError("Supply an existing HydrogenStack model owner")
        efficiency = finite(faradaic_efficiency, "Faradaic efficiency", positive=True)
        if efficiency > 1:
            raise ValueError("Faradaic efficiency must lie in (0, 1]")
        points = _evaluate_points(self, stack, efficiency)
        return PEACEElectrolysisTrace(
            profile=self,
            model_owner=stack,
            faradaic_efficiency=efficiency,
            model_signature=_model_signature(stack),
            points=points,
        )


@dataclass(frozen=True, slots=True)
class PEACEElectrolysisTrace:
    """Freshness-checkable snapshots tied to source profile and exact model owner."""

    profile: PEACEElectrolysisProfile
    model_owner: HydrogenStack
    faradaic_efficiency: float
    model_signature: tuple
    points: tuple[PEACEElectrolysisPoint, ...]

    @property
    def source_sha256(self):
        return self.profile.source.source.source_sha256

    @property
    def description_sha256(self):
        return self.profile.source.source.description_sha256

    def require_current(self):
        self.profile.require_current()
        if type(self.model_owner) is not HydrogenStack or _model_signature(self.model_owner) != self.model_signature:
            raise ValueError("PEACE evaluation model owner or stack geometry changed")
        if (not 0 < self.faradaic_efficiency <= 1
                or self.points != _evaluate_points(self.profile, self.model_owner,
                                                   self.faradaic_efficiency)):
            raise ValueError("PEACE evaluation output no longer reproduces from its bound inputs")
        return self


def _model_signature(stack):
    """Identity seal for caller-owned geometry, thermochemistry and losses."""
    return (id(stack), stack.geometry, id(stack.thermochemistry), tuple(stack.losses.items()))


def _evaluate_points(profile, stack, faradaic_efficiency):
    current = profile.source.total_current.values_si
    voltage = profile.source.total_voltage.values_si
    temp_series = next(item for item in profile.source.temperatures
                       if item.source.description.source_channel_id == profile.temperature_channel_id)
    points = []
    for row_index, (amps, volts, temperature, time_token) in enumerate(zip(
            current, voltage, temp_series.values_si, profile.source.source.time.values,
            strict=True)):
        if amps is None or volts is None or temperature is None:
            continue
        if amps < 0 or volts <= 0 or temperature <= 0:
            raise ValueError(f"Nonphysical measured model input at source row {row_index}")
        result = stack.evaluate(
            amps / stack.geometry.active_area_m2,
            temperature,
            mode="electrolysis",
            faradaic_efficiency=faradaic_efficiency,
        )
        points.append(PEACEElectrolysisPoint(
            row_index=row_index,
            time_token=time_token,
            current_a=amps,
            temperature_k=temperature,
            measured_voltage_v=volts,
            stack_result=result,
        ))
    if not points:
        raise ValueError("No source rows contain aligned current, voltage and selected temperature")
    return tuple(points)


def bind_peace_alkaline_electrolysis_profile(
    source: PEACESIObservationBlock, *, temperature_channel_id: str,
    electrical_scope_evidence_id: str, temperature_mapping_evidence_id: str,
) -> PEACEElectrolysisProfile:
    """Bind measured same-row PEACE channels without assigning unresolved semantics."""
    if type(source) is not PEACESIObservationBlock:
        raise TypeError("Supply a loader-issued PEACE SI observation projection")
    source.require_current()
    for label, value in (("electrical scope evidence", electrical_scope_evidence_id),
                         ("temperature mapping evidence", temperature_mapping_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {label}; no cell/stack meaning is inferred")
    available = {item.source.description.source_channel_id for item in source.temperatures}
    if temperature_channel_id not in available:
        raise ValueError("Select one exact publisher temperature channel ID")
    selected_temperature = next(item for item in source.temperatures
                                if item.source.description.source_channel_id == temperature_channel_id)
    return PEACEElectrolysisProfile(
        source=source,
        temperature_channel_id=temperature_channel_id,
        electrical_scope_evidence_id=electrical_scope_evidence_id,
        temperature_mapping_evidence_id=temperature_mapping_evidence_id,
        omitted_rows=_omitted_rows(source, selected_temperature),
    )


def _omitted_rows(source, selected_temperature):
    omitted = []
    aligned = zip(source.total_current.values_si, source.total_voltage.values_si,
                  selected_temperature.values_si, strict=True)
    for index, (amps, volts, temperature) in enumerate(aligned):
        missing = tuple(name for name, value in (("current", amps), ("voltage", volts),
                                                  ("temperature", temperature)) if value is None)
        if missing:
            omitted.append((index, "missing:" + ",".join(missing)))
    return tuple(omitted)


__all__ = [
    "PEACEElectrolysisPoint", "PEACEElectrolysisProfile", "PEACEElectrolysisTrace",
    "bind_peace_alkaline_electrolysis_profile",
]
