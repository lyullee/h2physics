# Native multisegment thermal response in ordinary air

`h2physics.adapters.jos3_thermal` reuses the actual JOS3 implementation in
pythermalcomfort4.7.0. Its 85 thermal nodes resolve 17 body parts, blood and
different tissue layers. The native engine owns body capacities, conductances,
blood transport, metabolic/regulatory heat and implicit integration. The host
supplies a typed finite environmental campaign and independently audits heat.
No physiological coefficients, anatomical parameter table or native source is
redistributed. The native provider remains an optional MIT dependency.

This is a conditional thermal-state model in explicitly declared ordinary air
at the native101325Pa reference. It is not a hydrogen-rich-gas convection,
cryogenic impingement/contact, boiling, tissue freezing, respiratory injury,
oxygen-deficiency or damage-probability model. It is distinct from the finite
room O2 model: temperatures from that H2/air room are not automatically valid
environmental inputs for this ordinary-air physiology. Clothing/contact and
gas properties cannot be transferred just because temperatures share units.

## Install and preserve native ownership

The exact three artifacts, original installed members, notices and source
aggregate are in [thermal_dependency.toml](../research/thermal_dependency.toml).
The checked profile uses NumPy2.5.4, SciPy1.18.1 or the separately exercised
compatible profile, numba0.68.1 and llvmlite0.50.0. Install into a separate
target and keep the original dependency notices. Core imports load no physiology
or compiler. The factory checks exact reviewed versions, native source bytes,
actual class/method origins, function bindings and node/channel definitions.

```powershell
.venv/Scripts/python.exe -m pip install --no-deps --no-compile --target artifacts/native_thermal_packages pythermalcomfort==4.7.0 numba==0.68.1 llvmlite==0.50.0
```

Native JIT must be enabled. Direct native import under NUMBA_DISABLE_JIT=1
failed with a compiler/dispatcher AttributeError in the reviewed environment;
the adapter explicitly rejects that configuration. It does not patch native
decorators or route to another model. Compilation caches stay ignored.

## Explicit Python campaign

The following subject and environmental values are authored numerical examples,
not observed people or qualified exposure conditions. All constructor inputs
are explicit: height m, mass kg, fat percent, integer age, native sex convention,
cardiac index L/(min m2), metabolism equation and surface-area equation.

```python
from pathlib import Path
import sys
sys.path.append(str(Path("artifacts/native_thermal_packages").resolve()))

from h2physics.core import Origin
from h2physics.adapters.jos3_thermal import (
    NativeJOS3, ThermalSubject, OrdinaryAirEnvironment, ThermalInterval,
    ThermalRunEvidence, ThermalDomain, JOS3ThermalResponse,
)

native = NativeJOS3.from_installed()
subject = ThermalSubject(1.74, 72., 18., 35, "male", 2.59,
                         "harris-benedict", "dubois")
prepared = native.prepare_neutral(subject)
environment = OrdinaryAirEnvironment(
    air_temperature_k=283.15, radiant_temperature_k=283.15,
    air_speed_m_s=.3, relative_humidity_percent=40., clothing_clo=.7,
    clothing_vapor_efficiency=.45, activity_ratio=1.3,
    posture="standing", evidence_id="authored-ordinary-air",
)
evidence = ThermalRunEvidence(
    clock_id="campaign-clock", frame_id="local-ENU", receptor_id="reference",
    position_m=(1., 0., 1.5), source_id="supplied-air-history",
    subject_evidence_id="authored-subject", initialization_evidence_id="native-neutral",
    applicability_evidence_id="authored-numerical-domain", medium="ordinary-air",
    reference_pressure_pa=101325., origin=Origin.SYNTHETIC,
)
domain = ThermalDomain(273.15, 313.15, 283.15, 315.15, 10., 1e-6)
result = JOS3ThermalResponse(native, domain).run(
    prepared, (ThermalInterval(100., 160., environment),), evidence=evidence,
)
skin_k = result.steps[-1].skin_temperature_k
actual_output = result.native_outputs[-1]
actual_integrated_model = result.native_model
```

Environmental scalar values explicitly denote spatially uniform conditions;
arrays carry 17 entries in `result.body_part_names` order. Temperatures enter
in K and are converted only at the native degC boundary. Humidity and fat are
percent; activity is the native activity/basal-metabolism ratio, not a met value.
Air speed is m/s, clothing is clo and vapor permeability is a dimensionless
efficiency. `node_index_map` binds all 85 unrounded node temperatures to the
actual native body/layer definitions. Native output structures retain their
native units/rounding; host temperature snapshots are unrounded K arrays.

Intervals are contiguous, finite and held constant. Every declared command
edge becomes an integration boundary, including noninteger times. Missing gaps
are rejected, never interpolated or extended. Use explicit discretization and
evidence for measured changing histories. Native elapsed time has microsecond
resolution; the host retains the separate absolute clock offset. Each step is
at most the declared maximum. Integer microsecond offsets prevent repeated floating-point
epoch additions from drifting. An absolute clock that cannot represent a forward
step or its native duration is rejected before that step. A domain is a caller-declared admission envelope,
not proof of native validation throughout that envelope.

## Initial state, energy and failures

The caller can pass an actual prepared native JOS3 object with a prior history.
The adapter deep-copies that object's complete definition/state; original
input and copied native objects remain inspectable. The source stays unchanged.
`prepare_neutral` invokes the native neutral-setpoint initialization. Only its
final raw output is retained by the native implementation; the internal warmup
trajectory is unavailable. It is not a measured initial human state. Keep the
initialization evidence distinct from experimental preconditioning.

Native heat-storage changes are independently computed from the actual native
capacities and unrounded node temperature changes. The native displayed sensible
heat loss uses previous-state skin temperature, whereas its implicit update
uses new skin temperature with the beginning-state native resistance/operative
temperature. The host retains both and uses the latter in its energy audit.
It does not replace native outputs. Native total thermogenesis, respiration
and 17 latent heat outputs each have0.01W precision: their combined maximum
rounding error is0.095W multiplied by step duration, plus an explicitly declared
numerical energy budget. This precision allowance cannot be a fitted heat source.
Metabolic heat is a native prescribed physiological source; there is no separate
finite nutrient, body-water or chemical-energy inventory closure here.

The native previous-shivering value is a module global. Its before/after values
are retained; `native_global_memory_isolated` is false. Enabling the native
rate limiter that depends on that global is rejected. Interleaving with external
rate-limited native models is outside this level. No global value or physical
equation is patched. The native unused `shivering` switch cannot declare that
shivering is absent. Custom hc/hr and external ex_q heat sources require an
additional audited energy boundary and are rejected here.

`ThermalResponseError` preserves the actual source/copied native model,
original cause and completed host-admitted steps. A failed native step can have
advanced its elapsed clock or updated internal state; those actual objects
remain available. The host does not invent hidden native intermediate steps.
Snapshots are immutable historical arrays; mutating a returned native object
does not update prior snapshots. There is no computed injury probability.

## Verification and remaining evidence

The native replay compares an unmodified direct campaign, copy/state invariance,
native output identity, exact environment switches, storage/heat precision and
10/5/2.5s refinement. It retains failed body-domain, global-memory and heat-source
cases. See [jos3_thermal.md](../research/jos3_thermal.md). No independent human
dataset or cryogenic injury calibration has been qualified.

Primary implementation/API references:
[native4.7.0 distribution](https://pypi.org/project/pythermalcomfort/4.7.0/),
[native documentation](https://pythermalcomfort.readthedocs.io/en/latest/documentation/models.html),
[source and MIT notice](https://github.com/pythermalcomfort/pythermalcomfort),
[JOS3 original bibliographic record](https://doi.org/10.1016/j.enbuild.2020.110575).
The publisher full-text endpoint returned403 during this review; that does not
establish inspection or replication of its original validation experiments.
