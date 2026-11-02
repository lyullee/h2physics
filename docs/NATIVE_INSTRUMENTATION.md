# Native sensor response and observation identity

`Lh2dtTransmitter` executes an actual caller-owned native LH2DT
`FirstOrderTransmitter`. The native component owns first-order lag, gain/bias,
range saturation, quantization and stated accuracy bounds. The host preserves
the physical location, variable/unit/reference, parameter provenance, source
clock, actual native states/readings and initial-state meaning. It does not add
another filter solver or assume calibration from a process history.

```python
from lh2dt.instrumentation import FirstOrderTransmitter, TransmitterParameters
from h2physics.adapters.lh2dt_instrumentation import Lh2dtTransmitter, TransmitterEvidence
from h2physics.core import Origin
from h2physics.observations import Variable

native = FirstOrderTransmitter(TransmitterParameters(
    lower_range=0., upper_range=1e6, time_constant_s=2.,
    resolution=100., accuracy_fraction_of_span=.001,
))
evidence = TransmitterEvidence(
    "P1", "headspace-port", Variable("pressure", "pressure", "Pa", "absolute"),
    "authored-calibration", "authored-response", ("synthetic-example",), Origin.SYNTHETIC,
)
instrument = Lh2dtTransmitter(native, evidence=evidence)
trace = instrument.run(
    pressure_series, channel="pressure", initial_native_state=instrument.initialize(1e5),
    initial_time_s=pressure_series.time_s[0], location_id="headspace-port",
)
```

Install the separately pinned native package described in NATIVE_EQUIPMENT.md.
The coefficients above are authored examples, with no manufacturer/measurement
qualification. Every input `TimeSeries` channel must have the exact declared
quantity, unit and basis. Absolute/gauge/differential pressure is explicit; a
reported-pressure channel with unresolved basis is incompatible with absolute
headspace pressure. Unit or location conversion needs a separately qualified
observation map. A pressure transmitter is not a gas EOS or physical gas state.

On the interval `(t[i],t[i+1])`, the process driver is `process[i]`. Each endpoint
prediction is the left limit after that interval, so `process[-1]` does not drive
an additional interval. At the first time, the supplied initial native state is
read directly. This explicit convention also applies to the zero-lag case. A
native initial state can represent known prehistory, or `initialize(value)` can
explicitly request a chosen synthetic initial state. The adapter never infers
sensor stationarity from the first logged process value.

Missing selected-channel values, incompatible quantities/units/references,
different locations, incorrect initial times and changes in parameter ownership
or values fail. There is no interpolation, hidden gap hold, clock alignment,
resampling or extrapolation. To continue another window, pass
`trace.final_native_state` with its actual endpoint time and the same evidence.
The caller remains responsible for relating native state provenance to prehistory.

`trace.prediction` is a predicted `TimeSeries`, with indicated value, filtered
process, raw pre-saturation indication, quantization bound, stated accuracy bound
and saturation flag. Bounds retain the physical unit. They are not standard
deviations, confidence intervals or observed errors; adding them in quadrature
requires additional stochastic evidence. Range saturation is an explicit native
indication effect and remains flagged. It does not constrain the physical process
to the sensor range or authorize a protection success/failure probability.

Run `scripts/check_instrumentation_integration.py` for irregular held-input limits,
sample refinement, threshold delay, range/resolution/bounds and a hash-verified
actual-data incompatibility case. `tests/test_lh2dt_instrumentation.py` also checks
continuation, changed parameters and retained failed native readings. See
[the executed record](../research/native_instrumentation.md). Measured tau/gain/
bias, thermal mounting effects, transport/sample-line delay, cross-sensitivity,
spatial observation kernels, noise/covariance and field calibration remain open.

Primary sources: [native API at the reviewed revision](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/instrumentation.py),
[NIST sensor time-response study](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=909856),
[BIPM definition of measurement uncertainty](https://jcgm.bipm.org/vim/en/2.26.html).
The thermal study provides time-response context; its coefficients are not used
as pressure-transmitter parameters. Comments, fixtures and coupling are authored
independently; native code and external observations remain outside distributions.
