# Native instrument and observation verification

Native LH2DT0.1.2, pinned revision b2f276333c1b1793c39f25763703d196d36742ec, MIT. Ordered native Python tree SHA-256: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.

All instrument parameters are authored verification values, not device calibration. LH2DT owns the exact held-input lag and indication effects. The host preserves units, pressure/reference/location and clocks, native states/readings, and parameter evidence. There is no new response integrator, stochastic noise, safety credit or historian clock repair.

Input is held on the left of each interval; output at each endpoint is a left limit. The first reading uses an explicit initial native state. The last process value does not drive an invented later interval. Native states can continue a subsequent window.

| Check | Value |
|---|---|
| Step analytic errors at1/.1/.01s sampling | [5.820766091346741e-11, 1.1641532182693481e-10, 6.402842700481415e-10] Pa |
| Endpoint spread over three samplings | 5.23868948221e-10 Pa |
| Continuous / sampled indicated400kPa crossing | 9.77258872224 / 9.78 s |
| Maximum quantization error after explicit saturation | 62.4987608427 Pa |

Synthetic step:100 to500kPa at absolute7s, tau2s, up to12s. Separate bounded run: 100 to700kPa, range0–400kPa, scale1.01, bias−700Pa, resolution125Pa, accuracy fraction of span .001. The resulting bounds are62.5Pa quantization and400Pa stated accuracy. These are deterministic reported bounds, not Gaussian sigma, measured residuals or confidence intervals. No probability distribution or coverage factor is inferred.

## Actual data boundary

Lach and Gaathaug's [USN data v1](https://doi.org/10.23642/usn.17932439.v1), CC BY4.0, is loaded only from locally acquired hash-verified bytes. The selected meter pressure has unresolved absolute/gauge basis and a different physical location. Automatic use as absolute headspace pressure is rejected: Observation quantity, unit or measurement/reference basis differs. No measured sensor time constant, uncertainty, process truth or calibration fit is claimed. This gate does not infer anything about other experiments or channels.

| Gate | Pass |
|---|---|
| exact native constant-hold step error <1e-7 Pa | True |
| native endpoint refinement difference <1e-7 Pa | True |
| sampled threshold follows analytic lag within one declared sample | True |
| native quantization error <=62.5 Pa after explicit range saturation | True |
| native bounds remain span-based, not standard deviations | True |
| native saturation diagnostic and actual object types retained | True |
| actual measured pressure is rejected without a qualified basis/location map | True |
| host/native source bytes unchanged during replay | True |

Primary references: [pinned native instrument API](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/instrumentation.py), [NIST sensor time-response study](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=909856), [BIPM measurement uncertainty definition](https://jcgm.bipm.org/vim/en/2.26.html). The thermal study motivates careful time-constant meaning, not a universal pressure transmitter calibration. No source parameter table or implementation is bundled.

## Executed host fingerprints

- `src/h2physics/adapters/lh2dt_instrumentation.py`: `76e188110e73cac2369eaed6c4835951e3a49d6be4a7bd7ed88b4ebed0154111`
- `tests/test_lh2dt_instrumentation.py`: `2d50b1f923b4a12f054c97c8105fd368f8a07bba5062e76575ee80c752d3deb0`
- `scripts/check_instrumentation_integration.py`: `3ae4f98d1cc6c52082e06f1c961bada90bf572bd872ec0617f38201f3486c79d`

Local replay wall time: 5.92347s.
