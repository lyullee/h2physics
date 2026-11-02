# Conditional native unconfined peak overpressure

`h2physics.adapters.hyram_overpressure.HyRAMBauwensOverpressure` calls the actual
optional HyRAM+6.1 `Bauwens_method.calc_scaled_overpressure_from_dist` public
static function. It requires an explicitly evidenced participating hydrogen
mass, heat of combustion, ambient absolute pressure, event centre and receptor
coordinates. It returns a conditional peak pressure rise above ambient.

This is an executable blast-correlation level. The participating mass and event
are supplied; the adapter does not predict a detonable cloud, ignition, DDT,
obstacle amplification or frequency. It has no blast waveform, travel/arrival
time, positive-phase duration or impulse. A conditional threshold radius is
not a qualified separation/safe distance or equipment design load.

`BauwensPeakResult` and `BauwensThresholdResult` are issued with one-use tokens
only from the native evaluation paths. Their retained inputs, native correlation
identity, raw native value, pressure projections and converged forward root are
sealed; `require_current()` rejects a changed result or nested input. The deferred
`hyram-bauwens-result-issuer` case uses authored synthetic inputs and the separate
`hyram-overpressure` native profile. This contract is planned and unexecuted.

## Native API inspection and source boundary

The installed native `TNT_method`, `BST_method` and `Bauwens_method` full
constructors require a real `Jet`. TNT/BST obtain flammable fuel mass from its
field; Bauwens additionally computes cell-size gradients and integrates fuel
in its accepted detonation region. The high-level native `compute_overpressure`
also constructs a jet. Their default event centre depends on the jet's
concentration distribution. Those are substantial additional physical inputs.

The existing HyRAM source-to-Gaussian mass gate is failed and remains failed.
No rejected jet is accepted as a cloud here, and there is no jet-to-energy
convenience conversion. No fabricated native instance, Jet or concentration
field is constructed. `evaluate` accepts only the explicit energy/event types
below. A caller must independently justify the participating mass and centre;
total released, flammable and detonable hydrogen masses are distinct quantities.
Giving an input an evidence label does not validate its scientific meaning.

The native standalone Bauwens static function exists independently of those
constructors. The adapter retains its actual class, actual function and raw
returned values. The class is retained as a class, not advertised as a fully
constructed native cloud model. Native TNT also has a static equivalent-mass
helper, but this adapter does not expose TNT/BST pressure tables or claim their
full models ran. Native source and tables remain separately installed.

## Energy, pressure and geometry

The dimensional definitions follow the independent
[Bauwens and Dorofeev ICHS2019 paper, p10](https://hysafe.info/uploads/papers/2019/279.pdf)
and [Sandia technical reference](https://www.osti.gov/servlets/purl/2563814):

```text
E = participating_H2_mass * supplied_heat_of_combustion
length_scale = (E / ambient_absolute_pressure) ** (1/3)
Rstar = distance_from_event_centre / length_scale
peak_pressure_rise = native_dimensionless_peak_pressure * ambient_absolute_pressure
```

The pressure rise is `peak_overpressure_pa`; `ambient_plus_peak_overpressure_pa`
labels its sum with the ambient absolute pressure separately. No reflected wall
pressure or pressure-time history is inferred. Native correlation coefficients
and their evaluation are not duplicated in the host.

`DetonableHydrogenEnergy` defines **fuel hydrogen mass**, excluding oxidizer,
and requires mass and heat evidence, combustion-product/reference basis, source
identity and parameter origin. The supplied heat is a declared combustion
energy per kg participating H2; it is not an arbitrary EOS enthalpy-zero
difference. No default heat, yield, efficiency, stoichiometric air mass or ground
reflection multiplier is inferred. Positive inputs with underflow/overflow are
rejected. Other fuels and phase-specific latent/chemical partition are not
qualified by this hydrogen-specific boundary.

`BauwensCorrelationDomain` requires explicit ambient-pressure bounds, scaled
distance bounds, a minimum physical standoff and their evidence. These caller
bounds are application assumptions, not measured qualification. The minimum
scaled distance must be at least0.01, the pinned native instance wrapper's
near-origin clamp. The adapter calls the unclamped static function and rejects
outside-domain inputs instead of using that clamp. A domain at or above0.01
does not by itself establish that a receptor is outside the actual source or
that the point-source correlation is accurate there; source geometry and
appropriate far-field standoff require independent evidence. Values very near
strict envelope edges can fail after coordinate-roundoff; no coordinate or
pressure correction is silently applied.

Zero participating mass is an explicitly recorded limiting case: the actual
native static function is called at `Rstar=infinity` and returns zero pressure
rise. The finite positive-energy scaled-distance envelope does not describe
this mathematical limit. Receptor physical standoff and ambient/frame checks
still apply. A positive threshold has no radius in this zero-energy case.

## Direct Python use

Install the reviewed GPL-3.0-only HyRAM separately as described in
PREFERRED_DISPERSION.md. The following values are original synthetic checks,
not measured participation fractions or a qualified facility scenario.

```python
from hyram.phys import Bauwens_method
from h2physics.adapters.hyram_overpressure import (
    BauwensCorrelationDomain, DetonableHydrogenEnergy,
    HyRAMBauwensOverpressure, OverpressureEnvironment, OverpressureEvent,
)
from h2physics.core import Origin

source = DetonableHydrogenEnergy(
    .01, 120e6,
    "authored-participating-H2-mass", "authored-combustion-heat",
    "specified-H2-combustion-products-reference",
    "independent-authored-case-not-a-jet-output", Origin.SYNTHETIC,
)
event = OverpressureEvent(
    "conditional-detonation", (0., 0., 0.), "global-xyz",
    "authored-blast-centre", 100., "operation-clock",
)
ambient = OverpressureEnvironment(100000., "authored-absolute-pressure")
domain = BauwensCorrelationDomain(
    1., 100., 80000., 120000., .1, "authored-numerical-envelope",
)
model = HyRAMBauwensOverpressure(
    Bauwens_method, domain=domain, native_source_id="HyRAM6.1/GPL-3.0-only",
)
result = model.evaluate(source, event, ambient,
    [(10., 0., 0.), (0., 20., 0.)], frame_id="global-xyz")
print(result.peak_overpressure_pa)
conditional_radius = model.threshold_radius(10000., source, event, ambient)
print(conditional_radius.radius_m, conditional_radius.native_solver_result.converged)
```

Coordinates are an explicit common3D frame in metres. `snapshot_time_s` and
`clock_id` identify the supplied event snapshot. They do not align any release
or measurement recorder, select an ignition time, or represent wave propagation.

`BauwensPeakResult` retains energy/event/environment/domain, read-only SI arrays,
actual native class/function, raw native return, source identity and the
zero-energy-limit flag. Raw native output is retained separately from immutable
copied arrays; modifying raw output or native definitions invalidates that raw
record. Post-construction replacement of the bound native function is rejected.
`OverpressureNativeError` retains the actual class and failed raw result when
native shape/finiteness/sign checks fail.

`threshold_radius` uses actual SciPy Brent inversion of the same native
correlation inside the declared radial domain. It requires a bracketed positive
pressure-rise target and records root tolerances, actual `RootResults` and a
native forward evaluation. It returns a radius from the declared centre, with
no arbitrary x-coordinate offset or hidden unbounded extrapolation.

## Verification and continuation

```powershell
.venv\Scripts\python -m pytest tests/test_hyram_overpressure.py -q
.venv\Scripts\python -X utf8 scripts/check_hyram_overpressure.py
```

The replay launches separate processes for the reviewed HyRAM/SciPy1.16.3
target and host SciPy1.18.1. This static route invokes no native ODE; its success
does not resolve full-Jet ODE compatibility or the source-mass failure. The
replay covers729 mass/ambient/distance points per runtime, the independently
published unit-distance pressure anchor, pressure/distance/energy similarity,
conditional threshold inversion/refinement, native zero-energy and mathematical
far-field limits, and retained domain failures. No test uses a fabricated Jet
as physical evidence. Deliberately damaged native functions occur only in
negative contract tests and are restored by pytest.

[research/native_overpressure.md](../research/native_overpressure.md) records
actual results, fixed gates, local calculation timing and native/host/test/script
begin/end byte fingerprints. These are mathematical and interface verification,
not independent measured cloud or blast validation.

A native explicit participating-energy/mass constructor should retain source
provenance, geometry, pressure/energy conventions and a declared model domain
without requiring an unrelated Jet. Full source-to-cloud use additionally needs
the existing conservative-source receiving work, accepted field-mass audits and
justified event centre/participation boundaries. Impulse/waveform/reflection,
confinement and detonation initiation each require their own actual native
capability and applicable experimental evidence. No receiving repository,
catalogue or common document is modified by this adapter task.

HyRAM remains separately installed under GPL-3.0-only. This feature bundles no
native implementation, coefficient table, external observation or mechanism.
Native source: [Sandia public repository](https://github.com/sandialabs/hyram).
