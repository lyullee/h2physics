# Two finite isothermal porous-membrane sides

`CanteraFiniteMembraneDevice` couples two actual finite, well-mixed rigid gas
volumes in one native Cantera3.2 `ReactorNet`. Pressure and composition evolve on
both sides. The existing `CanteraDustyGasTransport` owns the constitutive source:
multicomponent/Knudsen/Darcy species transport relative to the stationary solid.
This level has no fixed infinite feed, invented product composition, second EOS,
transport solver or physical reactor ODE.

Both sides have the **same prescribed temperature**. Native reactor energy is
disabled to impose that constraint, and separate required thermostat heats are
explicit outputs. This is finite isothermal transport, not an adiabatic device,
a resolved membrane temperature or a prediction of thermal conduction.

## Python construction

```python
import hashlib
from pathlib import Path
import cantera as ct
from h2physics.core import Origin
from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_membrane import (
    CanteraDustyGasTransport, MembraneEndpoint, MembraneTransportEvidence,
    PorousTransportGeometry,
)
from h2physics.adapters.cantera_membrane_device import (
    CanteraFiniteMembraneDevice, FiniteMembraneParameters,
    MembraneIntegrationSettings,
)

raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
names = ("H2", "N2", "AR")
def factory():
    selected = {s.name: s for s in ct.Species.list_from_yaml(raw.decode(), "species")}
    phase = ct.Solution(thermo="ideal-gas", species=[selected[n] for n in names],
                        transport_model="multicomponent")
    phase.TPX = 330., 101325., [.7, .2, .1]
    return phase

basis = MechanismBasis(
    "installed-h2o2-authored-frozen-selection", hashlib.sha256(raw).hexdigest(),
    "Cantera BSD-3-Clause; upstream GRI species/transport provenance",
    ("https://cantera.org/3.2/python/transport.html",), 300., 1000., 2e4, 2e5,
)
evidence = MembraneTransportEvidence(
    "installed-native-transport", "warm-frozen-gas", "neutral-ideal-gas",
    "native-NASA-formation-reference", "native-H2-spin-unresolved",
)
transport = CanteraDustyGasTransport(factory, basis, evidence=evidence)
def endpoint(name, fractions):
    return MembraneEndpoint(330., 101325., names, fractions, "mole", name,
        evidence.gas_phase_id, "authored-pore", "authored-operating-state", Origin.SYNTHETIC)
geometry = PorousTransportGeometry(.35, 2.5, 50e-9, 0., .001,
    "authored-pore", "authored-no-material-validation", Origin.SYNTHETIC)
parameters = FiniteMembraneParameters(
    .005, .02, .02, "authored-absolute-clock", 100., 104.,
    "separate-330K-thermostats", "authored-finite-device", Origin.SYNTHETIC,
)
trace = CanteraFiniteMembraneDevice(transport).run(
    endpoint("left", [.7, .2, .1]), endpoint("right", [.4, .5, .1]),
    geometry, parameters, [100., 101., 102.],
    settings=MembraneIntegrationSettings(maximum_time_step_s=.1),
)
native_left, native_right = trace.native.reactors
native_network = trace.native.network
last_left, last_right = trace.snapshots[-1].sides
```

These pore dimensions, area, volumes and states are authored verification inputs,
not measured membrane parameters. Porosity and native tortuosity factor remain
inside the existing DustyGas closure. The device multiplies its molar flux by the
**gross membrane area once**, with no extra porosity, squared tortuosity or
recovery factor. Different species can move in opposite directions while the
total molar or mass flux is nonzero. A signed flux vector is never normalized
into an outgoing product mixture.

## Native ownership and units

The existing constitutive adapter prepares independently owned endpoint phases
and an actual native `DustyGas` once. Those phases become the two reactor phases
with `clone=False`; the private native transport object is reset and reused
during integration. There are no native inlet/outlet reservoirs, MFCs or imposed
infinite gas inventories. Its public `molar_fluxes` consumes the actual current
mass density and raw mass fractions of both reactors. Pressure is consequently
determined by each actual native inventory and volume, not stale initial P.

The documented `after_eval_surfaces(...,sdot)` extension supplies signed bulk
species source amounts in **kmol/s**. It does not create a surface reaction.
Cantera's base reactor owns mass, species fractions and dilution. One native
CVODES network integrates both physical states and the appended boundary
integrals. Host hooks do not overwrite native physical mass/species/T equations.
The short-time derivative test independently verifies this hook's units and area
scaling against the actual initial flux and molecular weights.

Native flux kmol/m2/s times gross area m2 becomes kmol/s. Multiplication by native
kg/kmol weights yields kg/s. Native partial H/U are J/kmol, so dotting with the
signed kmol/s transfer yields W. Integrated boundary species are kg and energies
are J. The exact SI conversion is independent of a phase's reporting basis.

## Explicit isothermal energy boundary

For each side the positive incoming signed species transfer is used with native
partial molar enthalpy `h_i` to define transferred H. The separate required
thermostat rate is the same signed transfer dotted with native `u_i-h_i`.
Thus `delta_U = integrated_H_transfer + required_thermostat_Q` for each rigid
isothermal side. Positive Q enters that side. This is the heat required by the
prescribed thermal constraint, not a DustyGas thermal-flux prediction.

Identical native thermochemistry and the same T make opposite species H/U
transfers cancel between sides. Combined species, mass and U remain closed;
the two thermostat heats cancel in the ideal-gas isothermal reference. Native
formation energy already belongs to H/U; there is no extra reaction heat.
The inherited phase/evidence records retain common NASA caloric and unresolved
H2 spin identities. No CoolProp sensible zero or para-hydrogen reference is inferred.

Trace arrays separately retain species transfer, transferred H, thermostat Q,
side species/mass/U residuals and combined species/mass/U residuals. Snapshots
reuse the existing `GasVolumeSnapshot` with actual kg, m3, K, Pa absolute and J.
The native integrator ledger is distinct from sampled flux diagnostics.

## Numerical domain, clock and immutable definitions

Public endpoints obey the existing normalization and species/phase contract.
Every sampled accepted state must satisfy its phase/mechanism domain, finite
inventory, nonnegative species, accepted composition-sum budget, exact fixed T
and exact rigid volume. Minimum inventories are separately specified for both
sides. No epsilon gas is added to permit depletion or continue an empty side.

Native reactor trial states use `NoNorm` mass fractions and can leave the exact
composition simplex. They can also perturb a constant T or volume during native
Jacobian/iteration work. **The API does not identify each trial's type**, so the
recorded extrema are not labeled proven finite-difference probes. The numerical
contract admits bounded raw nonnegative Y-sum deviations and bounded T/V
deviations. Raw Y and actual native mass density are passed without host clipping
or normalization. The constitutive operator remains at its prescribed common T
through that extension; volume/density are the actual native trial values.
Accepted sampled states have their own stricter admission check. No claim about
every internal accepted solver step or all hidden native regularization is made.

Default budgets are1e-6 for trial sum deviation and relative T/V deviation,
and1e-10 for sampled accepted sum deviation. Actual observed maxima for sum, T,
V and accepted sums are retained in the trace; no signed composition correction
is applied. Native DustyGas itself uses a Tiny mean-mole-fraction floor inside
its matrix construction. That native numerical regularization does not add gas
to either finite inventory; its per-iteration history is not exposed here.

Every coupling evaluation checks source state/basis, source and owned exact
thermo/transport fingerprints, native phase identity, gas configuration and
the source/evidence binding. All write-only pore parameters are reset before a
new flux evaluation. The private kernel has no user callbacks and is exposed
only after a run or failure; native DustyGas does not expose polynomial getters.
Returned native objects stay inspectable and editable, but edits or manually
advancing their network invalidate the recorded trace. Use separate instances
for concurrent runs.

The device carries one explicit absolute clock and finite support. Output times
increase and the final requested time plus one maximum native step must fit
inside support, because CVODES may overshoot output times for interpolation.
Actual evaluated clock extrema are retained. There is no inferred event clock,
hold-last extrapolation, time rescaling or continuation beyond a domain limit.

## Failure retention, depletion and verification

`FiniteMembraneIntegrationError` retains the actual reactors, ReactorNet,
prepared constitutive result, private native kernel, raw last native states and
ledgers, valid sampled prefix, last sampled time, first triggering time/cause,
and a completed trace if post-run audit failed. A first boundary breach is sticky:
a later shorter native retry cannot erase it. Initial constitutive failures keep
the existing `MembraneTransportError` with its native objects.

An inventory guard is a rejected trial/sample, **not an exact depletion event
root**. The report retains the last accepted sample and first offending native
time; native internal event history is unavailable. Depletion termination,
restart modes, nonisothermal heat transport, membrane storage/sorption, physical
layer resolution, material selectivity and measured calibration remain open.

Run `python scripts/check_membrane_device.py`; see research/finite_membrane_device.md.
Actual native checks include equal-state stationarity, short-time hook units,
counterdiffusion with finite pressure feedback, reversal, area-time scaling,
integration refinement and an independently authored finite two-volume Knudsen
exponential limit at low pressure. These establish software/conservation evidence,
not measured membrane/device validation or production efficiency.

Primary sources: [Cantera extensible reactor API](https://cantera.org/3.2/python/zerodim.html#extensiblereactor),
[native ideal-gas reactor definition](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html),
[DustyGas transport API](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport),
and versioned [native reactor hook units](https://github.com/Cantera/cantera/blob/v3.2.0/src/zeroD/IdealGasReactor.cpp)
and [transport implementation](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/DustyGasTransport.cpp).
Cantera is separately installed BSD-3-Clause software, with upstream species and
transport provenance retained. No native implementation, coefficient table,
mechanism or experimental dataset is copied into these files.
