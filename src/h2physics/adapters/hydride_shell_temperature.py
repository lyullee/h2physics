"""Evidence-gated bridge from AB2 tank shell thermocouples to a bed heat boundary."""

from dataclasses import dataclass, field

import numpy as np

from ..data.hydride_tank import HydrideTankBlock
from ..storage.finite_hydride import FiniteHydrideHeatBoundary, FiniteHydrideHeatInput

_PENDING_ISSUERS: set[object] = set()


@dataclass(frozen=True, slots=True)
class HydrideShellTemperatureBoundary:
    """Caller-authorized, in-domain shell-temperature forcing for a hydride bed.

    The source measures external-shell temperatures, not bed or bath temperature.
    ``mapping_evidence_id`` is the caller's explicit evidence that the selected
    shell sensor is applicable as the model's bath boundary for this use.
    """

    source: HydrideTankBlock
    boundary: FiniteHydrideHeatBoundary
    sensor_name: str
    mapping_evidence_id: str
    times_s: tuple[float, ...]
    temperatures_k: tuple[float, ...]
    _binding: tuple = field(default=(), repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise TypeError("Issue shell-temperature boundaries through the source binding API")
        _PENDING_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        object.__setattr__(self, "_binding", _binding(self))

    def require_current(self):
        self.source.require_current()
        expected = _source_values(self.source, self.sensor_name)
        if expected != (self.times_s, self.temperatures_k):
            raise ValueError("Hydride shell source rows changed after boundary issuance")
        if _binding(self) != self._binding:
            raise ValueError("Hydride shell boundary lost its source/evidence binding")
        return self


def _source_values(source, sensor_name):
    source.require_current()
    if not isinstance(sensor_name, str) or sensor_name not in {
        f"shell_{i}" for i in range(1, 6)
    }:
        raise ValueError("Select one reviewed shell thermocouple shell_1 through shell_5")
    table = source.observations
    try:
        column = next(i for i, variable in enumerate(table.variables)
                      if variable.name == sensor_name)
    except (AttributeError, ValueError, StopIteration) as exc:
        raise ValueError("Source block does not contain the selected shell sensor") from exc
    try:
        time_column = next(i for i, variable in enumerate(table.variables)
                           if variable.name == "datetime_elapsed")
    except StopIteration as exc:
        raise ValueError("Source block has no reviewed elapsed-time column") from exc
    times = np.asarray(table.values[:, time_column], dtype=float)
    temps = np.asarray(table.values[:, column], dtype=float)
    valid = table.valid[:, time_column] & table.valid[:, column]
    times, temps = times[valid], temps[valid]
    if len(times) < 2 or not np.all(np.isfinite(times)) or not np.all(np.isfinite(temps)):
        raise ValueError("At least two valid source-clock shell readings are required")
    if np.any(np.diff(times) <= 0.) or np.any(temps <= 0.):
        raise ValueError("Shell source clock must increase and temperatures must be positive")
    if table.variables[column].unit != "K" or table.variables[time_column].unit != "s":
        raise ValueError("Reviewed source units must remain K and s")
    return tuple(float(x) for x in times), tuple(float(x) for x in temps)


def _binding(trace):
    return (id(trace.source), id(trace.boundary), trace.sensor_name,
            trace.mapping_evidence_id, trace.times_s, trace.temperatures_k)


def bind_hydride_shell_temperature(source: HydrideTankBlock, *, sensor_name: str,
                                   clock_id: str, mapping_evidence_id: str
                                   ) -> HydrideShellTemperatureBoundary:
    """Create a piecewise-linear finite bed heat boundary from one AB2 sheet block.

    No interpolation beyond the first/last valid shell sample is allowed. The
    source reader's flow, volume and pressure channels are deliberately unused.
    """
    if type(source) is not HydrideTankBlock:
        raise TypeError("Use an issued HydrideTankBlock from the qualified reader")
    if not isinstance(mapping_evidence_id, str) or not mapping_evidence_id.strip():
        raise ValueError("Explicit evidence for shell-sensor-to-bath mapping is required")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("Declare the hydride model clock identity")
    times, temps = _source_values(source, sensor_name)
    time_variable = next(v for v in source.observations.variables
                         if v.name == "datetime_elapsed")
    if time_variable.basis_id != clock_id:
        raise ValueError("Model clock identity must exactly match the source elapsed-time basis")
    context = dict(source.observations.context)
    file_hash = context.get("file_sha256")
    if not isinstance(file_hash, str) or len(file_hash) != 64:
        raise ValueError("AB2 reader context must retain the exact workbook SHA-256")
    source_id = f"{source.observations.source_id}:{file_hash}"

    # The callback rechecks source ownership on every evaluation and is restricted
    # by FiniteHydrideHeatBoundary to the exact measured support.
    def heat_input(time_s, snapshot):
        source.require_current()
        temperature = float(np.interp(time_s, times, temps))
        return FiniteHydrideHeatInput(bath_temperature_k=temperature)

    boundary = FiniteHydrideHeatBoundary(clock_id, times[0], times[-1], heat_input,
                                         f"{source_id}|mapping:{mapping_evidence_id.strip()}")
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        return HydrideShellTemperatureBoundary(source, boundary, sensor_name,
            mapping_evidence_id.strip(), times, temps, _issuer_token=token)
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
