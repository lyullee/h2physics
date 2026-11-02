"""Forward comparison of source-bound SOFC curves with the shared stack core."""

from dataclasses import dataclass

from ..core import finite
from ..data.sofc_polarization import SOFCPolarizationData
from ..electrochemistry import HydrogenStack, StackResult

_PENDING_TRACE_TOKENS: set[object] = set()


@dataclass(frozen=True, slots=True)
class SOFCFuelCellPoint:
    row_id: str
    current_density_a_m2: float
    temperature_k: float
    reported_voltage_v: float
    stack_result: StackResult

    @property
    def voltage_residual_v(self):
        """Shared stack prediction minus the source-reported curve voltage."""
        return self.stack_result.cell_voltage_v - self.reported_voltage_v


@dataclass(frozen=True, slots=True)
class SOFCFuelCellCurveTrace:
    source: SOFCPolarizationData
    model_owner: HydrogenStack
    temperature_k: float
    faradaic_efficiency: float
    model_evidence_id: str
    points: tuple[SOFCFuelCellPoint, ...]
    _model_signature: tuple
    _issuer_token: object = None
    _binding: tuple = ()

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRACE_TOKENS:
            raise TypeError("Issue SOFC comparison traces only through the source/model binding API")
        _PENDING_TRACE_TOKENS.remove(self._issuer_token)
        object.__setattr__(self, "_binding", self._current_binding())

    def _current_binding(self):
        return (id(self.source), id(self.model_owner), self.temperature_k,
                self.faradaic_efficiency, self.model_evidence_id, self.points,
                self._model_signature)

    def require_current(self):
        self.source.require_current()
        if self._current_binding() != self._binding:
            raise ValueError("SOFC trace lost its source/model evidence or result bindings")
        if (type(self.model_owner) is not HydrogenStack
                or _signature(self.model_owner) != self._model_signature):
            raise ValueError("SOFC trace lost its exact HydrogenStack geometry or callbacks")
        if (not isinstance(self.model_evidence_id, str) or not self.model_evidence_id.strip()
                or self.points != _evaluate(self.source, self.model_owner, self.temperature_k,
                                            self.faradaic_efficiency)):
            raise ValueError("SOFC model outputs no longer reproduce from their source/model owners")
        return self

    @property
    def source_sha256(self):
        return self.source.source_sha256

    @property
    def source_doi(self):
        from ..data.sofc_polarization import DOI
        return DOI


def _signature(stack):
    return (id(stack), stack.geometry, id(stack.thermochemistry), tuple(stack.losses.items()))


def _evaluate(source, stack, temperature_k, faradaic_efficiency):
    selected = next((curve for curve in source.curves
                     if len(curve.values) and curve.values[0, 1] == temperature_k), None)
    if selected is None:
        raise ValueError("Select one exact temperature condition present in this source file")
    if (selected.variables[0].name, selected.variables[1].name, selected.variables[2].name) != (
            "current_density", "temperature", "voltage"):
        raise ValueError("SOFC table schema differs from the reviewed current/temperature/voltage contract")
    mask = selected.complete_rows("current_density", "temperature", "voltage")
    rows = []
    for index in range(len(selected.values)):
        if not mask[index]:
            continue
        current_density, temperature, observed = selected.values[index]
        if current_density < 0. or temperature != temperature_k or observed <= 0.:
            raise ValueError(f"Invalid SOFC polarization point at {selected.row_ids[index]}")
        result = stack.evaluate(
            current_density, temperature, mode="fuel_cell",
            faradaic_efficiency=faradaic_efficiency,
        )
        rows.append(SOFCFuelCellPoint(
            selected.row_ids[index], float(current_density), float(temperature),
            float(observed), result,
        ))
    if not rows:
        raise ValueError("Selected SOFC curve has no complete current/temperature/voltage rows")
    return tuple(rows)


def compare_sofc_curve_with_hydrogen_stack(
    source: SOFCPolarizationData, stack: HydrogenStack, *, temperature_k: float,
    model_evidence_id: str, faradaic_efficiency: float = 1.0,
) -> SOFCFuelCellCurveTrace:
    """Evaluate only one observed SOFC condition through the existing stack core.

    The data publisher explicitly says the archive mixes experimental and
    multiphysics-generated curves; all voltage values stay source-reported and
    their origin remains unresolved. This function does not fit parameters or
    claim experimental validation. Caller thermochemistry/loss callbacks must
    encode the applicable SOFC gas state; the archive's nominal feed fractions
    are not local reaction activities.
    """
    if type(source) is not SOFCPolarizationData:
        raise TypeError("Supply a source-hash-verified SOFCPolarizationData reader result")
    if type(stack) is not HydrogenStack:
        raise TypeError("Supply an existing HydrogenStack model owner")
    source.require_current()
    temperature = finite(temperature_k, "selected source temperature", positive=True)
    efficiency = finite(faradaic_efficiency, "Faradaic efficiency", positive=True)
    if efficiency > 1.:
        raise ValueError("Faradaic efficiency must lie in (0, 1]")
    if not isinstance(model_evidence_id, str) or not model_evidence_id.strip():
        raise ValueError("Identify the caller-supplied SOFC thermochemistry and loss model")
    points = _evaluate(source, stack, temperature, efficiency)
    token = object()
    _PENDING_TRACE_TOKENS.add(token)
    return SOFCFuelCellCurveTrace(
        source, stack, temperature, efficiency, model_evidence_id,
        points, _signature(stack), token,
    )


__all__ = [
    "SOFCFuelCellCurveTrace", "SOFCFuelCellPoint",
    "compare_sofc_curve_with_hydrogen_stack",
]
