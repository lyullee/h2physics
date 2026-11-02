# Sampled hydrogen concentration sensor time-constant fitting

`h2physics.adapters.sensor_calibration.fit_first_order_sensor_time_constant()`
fits one parameter of the existing first-order concentration-sensor response.
It takes paired sampled true concentration and measured indication values on the
same strictly increasing clock. The caller declares the clock, concentration
basis and unit, truth and indication source records, calibration evidence,
initial measured indication, origin, maximum sample gap and positive search
bounds. Both series must use the exact basis and unit in the existing
`FirstOrderConcentrationSensorConfig`.

The fitter minimizes unweighted mean squared concentration residuals in log of
the positive response-time-constant interval. It uses the same exact response
law as `evaluate_first_order_concentration_sensor`: a piecewise-linear input and
a first-order, unity-gain, zero-offset, zero-dead-time output. The result retains
the aligned raw samples, fitted configuration, bounds, residual series and RMS;
`bound_limited` signals an estimate at a declared search boundary. The returned
configuration can be passed directly to the existing response evaluator.

This is a one-parameter fit over the supplied episode. It does not estimate gain,
bias, initial-state error, transport or communication delay, saturation,
cross-sensitivity, noise, covariance, confidence intervals, detection reliability
or an alarm threshold. The RMS residual describes this sample set and is not a
measurement-uncertainty estimate. A fitted parameter is only as representative as
the caller's calibration episode and source-to-channel mapping. No public
calibration dataset is bundled or inferred.

The deferred `sensor-time-constant-calibration` case exercises recovery from a
synthetic analytic response, basis/unit and clock guards, non-exciting input,
bounded-fit behavior, and receipt integrity. It has not been executed. Measured
calibration and field qualification remain necessary before using a fitted value
as a sensor specification.
