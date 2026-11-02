"""Source-bound diagnostic bridge from PEM ripple IV curves to HydrogenStack."""

from dataclasses import dataclass

from ..core import finite
from ..data.pem_ripple import PemRippleIVCurve
from ..data.pem_ripple_member import PemRippleIVMemberCurve
from ..electrochemistry import HydrogenStack, StackResult

_PENDING_TRACE_TOKENS: set[object] = set()


@dataclass(frozen=True, slots=True)
class PemRippleStackPoint:
    """One measured IV row projected onto caller-declared cell conditions."""

    row_number: int
    source_step_index: int
    measured_current_a: float
    current_density_a_m2: float
    temperature_k: float
    reported_voltage_v: float
    stack_result: StackResult

    @property
    def voltage_residual_v(self) -> float:
        """Existing HydrogenStack cell-voltage result minus source voltage."""
        return self.stack_result.cell_voltage_v - self.reported_voltage_v


@dataclass(frozen=True, slots=True)
class PemRippleStackTrace:
    """Immutable, reproducible diagnostic mapping for one source IV curve."""

    source: PemRippleIVCurve | PemRippleIVMemberCurve
    model_owner: HydrogenStack
    temperature_k: float
    active_area_evidence_id: str
    temperature_evidence_id: str
    model_evidence_id: str
    points: tuple[PemRippleStackPoint, ...]
    _model_signature: tuple
    _issuer_token: object = None
    _binding: tuple = ()

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRACE_TOKENS:
            raise TypeError("Issue PEM ripple model traces only through the source/model bridge")
        _PENDING_TRACE_TOKENS.remove(self._issuer_token)
        object.__setattr__(self, "_binding", self._current_binding())

    def _current_binding(self):
        return (id(self.source), id(self.model_owner), self.temperature_k,
                self.active_area_evidence_id, self.temperature_evidence_id,
                self.model_evidence_id, self.points, self._model_signature)

    def require_current(self):
        self.source.require_current()
        if self._current_binding() != self._binding:
            raise ValueError("PEM ripple trace lost its source or caller evidence binding")
        if type(self.model_owner) is not HydrogenStack or _signature(self.model_owner) != self._model_signature:
            raise ValueError("PEM ripple trace lost its HydrogenStack geometry or callbacks")
        if (not _evidence(self.active_area_evidence_id, "active-area evidence")
                or not _evidence(self.temperature_evidence_id, "temperature evidence")
                or not _evidence(self.model_evidence_id, "electrochemical model evidence")
                or self.points != _evaluate(self.source, self.model_owner, self.temperature_k)):
            raise ValueError("PEM ripple bridge no longer reproduces from its source and model owners")
        return self

    @property
    def source_sha256(self) -> str:
        return _parent_archive_sha256(self.source)

    @property
    def source_member_sha256(self) -> str:
        return self.source.source_member_sha256


def _evidence(value: str, label: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Identify caller-supplied {label}")
    return True


def _signature(stack: HydrogenStack) -> tuple:
    return (id(stack), stack.geometry, id(stack.thermochemistry), tuple(stack.losses.items()))


def _parent_archive_sha256(source: PemRippleIVCurve | PemRippleIVMemberCurve) -> str:
    if type(source) is PemRippleIVMemberCurve:
        return source.parent_archive_sha256
    return source._archive.sha256


def _evaluate(
    source: PemRippleIVCurve | PemRippleIVMemberCurve,
    stack: HydrogenStack,
    temperature_k: float,
) -> tuple[PemRippleStackPoint, ...]:
    source.require_current()
    if stack.geometry.series_cells != 1:
        raise ValueError("A single-cell IV curve requires a one-cell HydrogenStack geometry")
    area = finite(stack.geometry.active_area_m2, "caller-declared active area", positive=True)
    rows = []
    for offset, (current, observed, step) in enumerate(
        zip(source.current_a, source.voltage_v, source.step_index, strict=True), 1,
    ):
        current_a = finite(float(current), "source cell current")
        if current_a < 0.0:
            raise ValueError(f"Source current is not a nonnegative magnitude at row {offset}")
        current_density = current_a / area
        result = stack.evaluate(current_density, temperature_k, mode="electrolysis")
        rows.append(PemRippleStackPoint(
            offset, int(step), current_a, current_density, temperature_k,
            float(observed), result,
        ))
    if not rows:
        raise ValueError("Selected PEM ripple IV curve contains no rows")
    return tuple(rows)


def compare_pem_ripple_curve_with_hydrogen_stack(
    source: PemRippleIVCurve | PemRippleIVMemberCurve,
    stack: HydrogenStack,
    *,
    temperature_k: float,
    active_area_evidence_id: str,
    temperature_evidence_id: str,
    model_evidence_id: str,
) -> PemRippleStackTrace:
    """Map one measured single-cell curve to the existing electrolysis kernel.

    The publisher reports current in amperes and voltage in volts but does not
    provide active electrode area or cell temperature. Those are supplied by the
    caller and attached to the returned trace as evidence identifiers. The method
    does not fit callbacks, infer missing state, or claim independent validation.
    """
    if type(source) not in {PemRippleIVCurve, PemRippleIVMemberCurve}:
        raise TypeError("Supply a source-hash-verified PEM ripple IV curve")
    if type(stack) is not HydrogenStack:
        raise TypeError("Supply an existing HydrogenStack model owner")
    source.require_current()
    temperature = finite(temperature_k, "caller-selected source temperature", positive=True)
    _evidence(active_area_evidence_id, "active-area evidence")
    _evidence(temperature_evidence_id, "temperature evidence")
    _evidence(model_evidence_id, "electrochemical model evidence")
    if stack.geometry.series_cells != 1:
        raise ValueError("A single-cell IV curve requires a one-cell HydrogenStack geometry")
    points = _evaluate(source, stack, temperature)
    token = object()
    _PENDING_TRACE_TOKENS.add(token)
    return PemRippleStackTrace(
        source, stack, temperature, active_area_evidence_id, temperature_evidence_id,
        model_evidence_id, points, _signature(stack), token,
    )


__all__ = [
    "PemRippleStackPoint",
    "PemRippleStackTrace",
    "compare_pem_ripple_curve_with_hydrogen_stack",
]
