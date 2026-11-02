"""Fit the time constant of the declared first-order concentration sensor.

This module calibrates one dynamic parameter from paired sampled input and
indication histories. It does not estimate gain, offset, dead time, cross-
sensitivity, noise, uncertainty, sensor reliability or safety performance.
"""

from dataclasses import dataclass, field, replace
from math import exp, isclose, log, sqrt

import numpy as np
from scipy.optimize import minimize_scalar

from ..core import Origin, finite, immutable_array
from .gas_detection import (
    FirstOrderConcentrationSensorConfig,
    evaluate_first_order_concentration_sensor,
)


_PENDING_CALIBRATION_ISSUERS: set[object] = set()


def _real_vector(values, name):
    raw = np.asarray(values)
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"{name} must contain real numeric samples")
    vector = np.asarray(raw, dtype=float)
    if vector.ndim != 1 or vector.size < 4 or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite vector with at least four samples")
    return vector


def _calibration_digest(record) -> str:
    import hashlib

    digest = hashlib.sha256(repr((
        record.sensor_config, record.calibration_evidence_id,
        record.truth_series_evidence_id, record.indication_series_evidence_id,
        record.truth_basis_id, record.truth_unit,
        record.indication_basis_id, record.indication_unit,
        record.clock_id, record.origin.value, record.time_constant_bounds_s,
        record.response_time_constant_s, record.residual_rms,
        record.bound_limited,
    )).encode("utf-8"))
    for array in (record.time_s, record.true_concentration,
                  record.measured_indication, record.residual):
        contiguous = np.ascontiguousarray(array)
        digest.update(contiguous.dtype.str.encode("ascii"))
        digest.update(repr(contiguous.shape).encode("ascii"))
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


def _issue_calibration(**values):
    token = object()
    _PENDING_CALIBRATION_ISSUERS.add(token)
    try:
        return FirstOrderSensorTimeConstantCalibration(
            **values, _issuer_token=token
        )
    except Exception:
        _PENDING_CALIBRATION_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class FirstOrderSensorTimeConstantCalibration:
    """Source-bound estimate from paired input/indication samples.

    The fitted quantity applies only to the selected first-order, unity-gain,
    zero-offset, zero-dead-time model over the declared sample window. The RMS
    residual is in the input concentration unit and is not an uncertainty bound.
    """

    sensor_config: FirstOrderConcentrationSensorConfig
    time_s: np.ndarray
    true_concentration: np.ndarray
    measured_indication: np.ndarray
    initial_indication: float
    calibration_evidence_id: str
    truth_series_evidence_id: str
    indication_series_evidence_id: str
    truth_basis_id: str
    truth_unit: str
    indication_basis_id: str
    indication_unit: str
    clock_id: str
    origin: Origin
    time_constant_bounds_s: tuple[float, float]
    response_time_constant_s: float
    residual: np.ndarray
    residual_rms: float
    bound_limited: bool
    _issuer_token: object = field(repr=False, compare=False)
    _issued_token: object = field(init=False, repr=False, compare=False, default=None)
    _seal: str = field(init=False, repr=False, compare=False, default="")

    def __post_init__(self):
        if self._issuer_token not in _PENDING_CALIBRATION_ISSUERS:
            raise TypeError("Create sensor calibration receipts with fit_first_order_sensor_time_constant")
        _PENDING_CALIBRATION_ISSUERS.remove(self._issuer_token)
        if type(self.sensor_config) is not FirstOrderConcentrationSensorConfig:
            raise TypeError("Retain the exact first-order sensor configuration")
        if not isinstance(self.time_constant_bounds_s, (tuple, list)) or len(self.time_constant_bounds_s) != 2:
            raise ValueError("Retain the increasing two-value time-constant search interval")
        bounds = tuple(finite(value, "time-constant bound", positive=True)
                       for value in self.time_constant_bounds_s)
        if bounds[0] >= bounds[1]:
            raise ValueError("Time-constant search bounds must be strictly increasing")
        tau = finite(self.response_time_constant_s, "fitted response time constant", positive=True)
        if not bounds[0] <= tau <= bounds[1]:
            raise ValueError("Fitted time constant must remain inside its declared bounds")
        if type(self.bound_limited) is not bool:
            raise TypeError("Declare whether the fitted result is bound-limited as a bool")
        for name in ("calibration_evidence_id", "truth_series_evidence_id",
                     "indication_series_evidence_id", "truth_basis_id", "truth_unit",
                     "indication_basis_id", "indication_unit", "clock_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")
        if self.clock_id != self.sensor_config.clock_id:
            raise ValueError("Calibration samples must use the configured sensor clock")
        if (self.truth_basis_id != self.sensor_config.concentration_basis
                or self.indication_basis_id != self.sensor_config.concentration_basis
                or self.truth_unit != self.sensor_config.concentration_unit
                or self.indication_unit != self.sensor_config.concentration_unit):
            raise ValueError("Truth and measured indication must share the configured quantity basis and unit")
        origin = Origin(self.origin)
        if origin in {Origin.UNRESOLVED, Origin.PREDICTED}:
            raise ValueError("Calibration observations must be measured, reconstructed or synthetic")
        time = immutable_array(self.time_s, dtype=float, name="calibration time")
        truth = immutable_array(self.true_concentration, dtype=float, name="true concentration")
        measured = immutable_array(self.measured_indication, dtype=float, name="measured indication")
        residual = immutable_array(self.residual, dtype=float, name="calibration residual")
        if (time.ndim != 1 or len(time) < 4 or truth.shape != time.shape
                or measured.shape != time.shape or residual.shape != time.shape):
            raise ValueError("Calibration arrays must be aligned one-dimensional sample series")
        if (not np.all(np.isfinite(time)) or not np.all(np.isfinite(truth))
                or not np.all(np.isfinite(measured)) or not np.all(np.isfinite(residual))
                or np.any(time < 0) or np.any(truth < 0) or np.any(measured < 0)
                or np.any(np.diff(time) <= 0)
                or np.any(np.diff(time) > self.sensor_config.maximum_input_sample_gap_s)):
            raise ValueError("Calibration samples violate finite, nonnegative or clock-gap constraints")
        if np.ptp(truth) <= np.finfo(float).eps * max(1., float(np.max(truth))):
            raise ValueError("Calibration input must contain an excitation range")
        initial = finite(self.initial_indication, "initial measured indication")
        if initial < 0 or not isclose(initial, float(measured[0]), rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Initial condition must equal the first retained measured indication")
        if (self.sensor_config.response_time_constant_s != tau
                or self.sensor_config.response_parameter_evidence_id != self.calibration_evidence_id):
            raise ValueError("Retained sensor configuration must use the fitted time constant and evidence")
        predicted = evaluate_first_order_concentration_sensor(
            self.sensor_config, time_s=time, true_concentration=truth,
            initial_indication=initial,
            source_evidence_id=self.truth_series_evidence_id,
            operating_mode_id="calibration", episode_id=self.calibration_evidence_id,
            origin=origin,
        ).indicated_concentration
        if (not np.allclose(residual, measured-predicted, rtol=1e-12, atol=1e-15)
                or not isclose(self.residual_rms,
                               sqrt(float(np.mean(np.square(residual)))),
                               rel_tol=1e-12, abs_tol=1e-15)):
            raise ValueError("Calibration residual summary does not reproduce the fitted sensor response")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "true_concentration", truth)
        object.__setattr__(self, "measured_indication", measured)
        object.__setattr__(self, "residual", residual)
        object.__setattr__(self, "initial_indication", initial)
        object.__setattr__(self, "time_constant_bounds_s", bounds)
        object.__setattr__(self, "response_time_constant_s", tau)
        object.__setattr__(self, "residual_rms", finite(self.residual_rms, "calibration RMS"))
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "_issued_token", self._issuer_token)
        object.__setattr__(self, "_seal", _calibration_digest(self))

    def require_current(self):
        if self._issued_token is not self._issuer_token or not self._seal:
            raise ValueError("Sensor time-constant calibration was not issued by the fitter")
        if _calibration_digest(self) != self._seal:
            raise ValueError("Sensor calibration samples or fitted summaries changed after fitting")
        return self


def fit_first_order_sensor_time_constant(
    sensor_config, *, time_s, true_concentration, measured_indication,
    initial_indication, time_constant_bounds_s, calibration_evidence_id,
    truth_series_evidence_id, indication_series_evidence_id,
    truth_basis_id, truth_unit, indication_basis_id, indication_unit, origin,
):
    """Estimate only ``tau`` from aligned sampled truth and measured indication.

    The input is modeled as piecewise linear and the indicator as a first-order
    unity-gain response, matching :func:`evaluate_first_order_concentration_sensor`.
    Sensor bias, gain, dead time, sample delay and uncertainty are not estimated.
    """
    if type(sensor_config) is not FirstOrderConcentrationSensorConfig:
        raise TypeError("Supply the existing explicit first-order concentration sensor config")
    time = _real_vector(time_s, "Calibration time")
    truth = _real_vector(true_concentration, "True concentration")
    measured = _real_vector(measured_indication, "Measured indication")
    if time.shape != truth.shape or time.shape != measured.shape:
        raise ValueError("Truth and indication samples must exactly share one clock")
    if (np.any(time < 0) or np.any(truth < 0) or np.any(measured < 0)
            or np.any(np.diff(time) <= 0)
            or np.any(np.diff(time) > sensor_config.maximum_input_sample_gap_s)):
        raise ValueError("Calibration samples violate time, concentration or declared-gap bounds")
    if np.ptp(truth) <= np.finfo(float).eps * max(1., float(np.max(truth))):
        raise ValueError("Calibration input must contain an excitation range")
    initial = finite(initial_indication, "initial measured indication")
    if initial < 0 or not isclose(initial, float(measured[0]), rel_tol=1e-12, abs_tol=1e-15):
        raise ValueError("Initial indication must equal the first measured sample")
    if not isinstance(time_constant_bounds_s, (tuple, list)) or len(time_constant_bounds_s) != 2:
        raise ValueError("Declare lower and upper positive time-constant bounds")
    lower, upper = (finite(value, "time-constant bound", positive=True)
                    for value in time_constant_bounds_s)
    if lower >= upper:
        raise ValueError("Time-constant bounds must be strictly increasing")
    for name, value in (("calibration evidence", calibration_evidence_id),
                        ("truth-series evidence", truth_series_evidence_id),
                        ("indication-series evidence", indication_series_evidence_id),
                        ("truth basis", truth_basis_id), ("truth unit", truth_unit),
                        ("indication basis", indication_basis_id), ("indication unit", indication_unit)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {name}")
    if (truth_basis_id != sensor_config.concentration_basis
            or indication_basis_id != sensor_config.concentration_basis
            or truth_unit != sensor_config.concentration_unit
            or indication_unit != sensor_config.concentration_unit):
        raise ValueError("Truth and indication basis/units must match the sensor configuration")
    source_origin = Origin(origin)
    if source_origin in {Origin.UNRESOLVED, Origin.PREDICTED}:
        raise ValueError("Use measured, reconstructed or synthetic paired calibration samples")

    def objective(log_tau):
        tau = exp(float(log_tau))
        trial_config = replace(
            sensor_config,
            response_time_constant_s=tau,
            response_parameter_evidence_id=calibration_evidence_id,
        )
        trace = evaluate_first_order_concentration_sensor(
            trial_config, time_s=time, true_concentration=truth,
            initial_indication=initial,
            source_evidence_id=truth_series_evidence_id,
            operating_mode_id="calibration", episode_id=calibration_evidence_id,
            origin=source_origin,
        )
        residual = measured-trace.indicated_concentration
        return float(np.mean(np.square(residual)))

    fit = minimize_scalar(
        objective, bounds=(log(lower), log(upper)), method="bounded",
        options={"xatol": 1e-10, "maxiter": 500},
    )
    if not fit.success or not np.isfinite(fit.fun):
        raise RuntimeError("Bounded sensor time-constant fit did not converge")
    tau = exp(float(fit.x))
    bound_limited = min(abs(log(tau/lower)), abs(log(upper/tau))) <= 1e-6
    calibrated_config = replace(
        sensor_config, response_time_constant_s=tau,
        response_parameter_evidence_id=calibration_evidence_id,
    )
    predicted = evaluate_first_order_concentration_sensor(
        calibrated_config, time_s=time, true_concentration=truth,
        initial_indication=initial,
        source_evidence_id=truth_series_evidence_id,
        operating_mode_id="calibration", episode_id=calibration_evidence_id,
        origin=source_origin,
    ).indicated_concentration
    residual = measured-predicted
    return _issue_calibration(
        sensor_config=calibrated_config,
        time_s=time, true_concentration=truth, measured_indication=measured,
        initial_indication=initial,
        calibration_evidence_id=calibration_evidence_id,
        truth_series_evidence_id=truth_series_evidence_id,
        indication_series_evidence_id=indication_series_evidence_id,
        truth_basis_id=truth_basis_id, truth_unit=truth_unit,
        indication_basis_id=indication_basis_id, indication_unit=indication_unit,
        clock_id=sensor_config.clock_id, origin=source_origin,
        time_constant_bounds_s=(lower, upper),
        response_time_constant_s=tau, residual=residual,
        residual_rms=sqrt(float(np.mean(np.square(residual)))),
        bound_limited=bound_limited,
    )


__all__ = [
    "FirstOrderSensorTimeConstantCalibration",
    "fit_first_order_sensor_time_constant",
]
