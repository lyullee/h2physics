"""Exact positive-part threshold deficit integral on an admitted linear sample trace.

This is a sampled engineering metric, not a physiological dose or injury model.
"""

from dataclasses import dataclass, field
from math import fsum, isfinite

from ..core import finite
from .oxygen_deficiency import (
    OxygenCriterionResult,
    verify_oxygen_room_result,
)

_PENDING_THRESHOLD_INTEGRAL_ISSUERS: set[object] = set()


def _integrate_positive_threshold_deficit(times_s, values, threshold):
    """Integrate max(threshold - value(t), 0) for piecewise-linear samples."""
    times = tuple(finite(value, "sample time") for value in times_s)
    samples = tuple(finite(value, "criterion sample") for value in values)
    level = finite(threshold, "criterion threshold", positive=True)
    if len(times) < 2 or len(samples) != len(times):
        raise ValueError("Supply matching time/value samples with at least one interval")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("Sample times must increase strictly")
    areas = []
    for left_t, right_t, left_v, right_v in zip(
            times[:-1], times[1:], samples[:-1], samples[1:], strict=True):
        delta_t = right_t-left_t
        left_deficit = level-left_v
        right_deficit = level-right_v
        if left_deficit >= 0. and right_deficit >= 0.:
            area = 0.5*(left_deficit+right_deficit)*delta_t
        elif left_deficit <= 0. and right_deficit <= 0.:
            area = 0.
        elif left_deficit > 0.:
            positive_fraction = left_deficit/(left_deficit-right_deficit)
            area = 0.5*left_deficit*(delta_t*positive_fraction)
        else:
            positive_fraction = right_deficit/(right_deficit-left_deficit)
            area = 0.5*right_deficit*(delta_t*positive_fraction)
        if not isfinite(area) or area < 0.:
            raise ValueError("Threshold-deficit integration produced an invalid interval")
        areas.append(float(area))
    return tuple(areas)


def _parent_values(screen):
    screen.require_current()
    room = screen.room_result
    verify_oxygen_room_result(room)
    start = int(next(index for index, time in enumerate(room.time_s)
                     if time == screen.sampled_times_s[0]))
    stop = start+len(screen.sampled_times_s)
    if not (stop <= len(room.time_s)
            and tuple(room.time_s[start:stop]) == tuple(screen.sampled_times_s)):
        raise ValueError("Criterion screen times are no longer original consecutive room outputs")
    values = tuple(getattr(room, screen.criterion.quantity)[start:stop])
    return tuple(screen.sampled_times_s), values, screen.criterion.threshold


@dataclass(frozen=True, slots=True)
class OxygenThresholdDeficitIntegral:
    """Retain interval and total positive oxygen-criterion deficit integrals."""

    criterion_result: OxygenCriterionResult = field(repr=False, compare=False)
    interval_integrals: tuple[float, ...]
    total_integral: float
    quantity: str
    units: str
    status: str = "sampled-linear-threshold-deficit-integral;not-human-dose"
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_THRESHOLD_INTEGRAL_ISSUERS:
            raise TypeError("Threshold integrals are issued from an admitted oxygen criterion result")
        _PENDING_THRESHOLD_INTEGRAL_ISSUERS.remove(self._issuer)
        if type(self.criterion_result) is not OxygenCriterionResult:
            raise TypeError("Retain the actual issued oxygen criterion result")
        self.criterion_result.require_current()
        times, values, threshold = _parent_values(self.criterion_result)
        expected = _integrate_positive_threshold_deficit(times, values, threshold)
        areas = tuple(finite(value, "interval deficit integral") for value in self.interval_integrals)
        total = finite(self.total_integral, "total deficit integral")
        if (areas != expected or len(areas) != len(times)-1
                or total != fsum(expected)):
            raise ValueError("Reported interval and total integrals must reproduce the sampled parent trace")
        expected_quantity = self.criterion_result.criterion.quantity
        expected_units = ("mole_fraction*s" if "mole_fraction" in expected_quantity else "Pa*s")
        if self.quantity != expected_quantity or self.units != expected_units:
            raise ValueError("Integrated quantity and units must follow the selected oxygen criterion")
        if self.status != "sampled-linear-threshold-deficit-integral;not-human-dose":
            raise ValueError("Do not promote the sampled deficit metric to physiological dose")
        object.__setattr__(self, "interval_integrals", areas)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (id(self.criterion_result), self.interval_integrals, self.total_integral,
                self.quantity, self.units, self.status)

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Oxygen threshold deficit integral changed after issuance")
        self.criterion_result.require_current()
        times, values, threshold = _parent_values(self.criterion_result)
        expected = _integrate_positive_threshold_deficit(times, values, threshold)
        if (self.interval_integrals != expected or self.total_integral != fsum(expected)):
            raise ValueError("Oxygen threshold integral no longer reproduces its source samples")
        return self


def integrate_oxygen_threshold_deficit(screen: OxygenCriterionResult):
    """Integrate the selected oxygen-value deficit below its declared threshold.

    The caller's already-admitted linear reconstruction is used between original
    output samples. The result is fraction·s for mole-fraction screens or Pa·s for
    partial-pressure screens; it is not a dose-response or probability.
    """
    if type(screen) is not OxygenCriterionResult:
        raise TypeError("Use an issued OxygenCriterionResult")
    times, values, threshold = _parent_values(screen)
    areas = _integrate_positive_threshold_deficit(times, values, threshold)
    token = object()
    _PENDING_THRESHOLD_INTEGRAL_ISSUERS.add(token)
    try:
        result = OxygenThresholdDeficitIntegral(
            criterion_result=screen,
            interval_integrals=areas,
            total_integral=fsum(areas),
            quantity=screen.criterion.quantity,
            units=("mole_fraction*s" if "mole_fraction" in screen.criterion.quantity
                   else "Pa*s"),
            _issuer=token,
        )
        return result.require_current()
    except Exception:
        _PENDING_THRESHOLD_INTEGRAL_ISSUERS.discard(token)
        raise


__all__ = [
    "OxygenThresholdDeficitIntegral",
    "integrate_oxygen_threshold_deficit",
]
