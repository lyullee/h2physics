# Native temperature-dependent hydrogen spin thermochemistry

`PifiraSpinBridge` calls the actual separately installed MIT pifira0.3.0
`RigidRotorSpinThermo` and `MilenkoCorrelation`. It connects the existing actual
LH2DT `OrthoParaState` to native temperature-dependent rotor U, frozen Cv,
ortho-minus-para conversion energy and its temperature derivative. It also
provides strict natural-conversion rate points, a rotor-bath thermostat power
and energy/capacity tangents for a caller's driver. It adds no EOS, kinetic-rate
formula, exact advance, trajectory solver or duplicate finite calorimeter.
The existing constant-gap spin adapter remains unchanged.

## Python use

```python
from pifira.lh2 import spin
from lh2dt.ortho_para import OrthoParaState
from h2physics.adapters.lh2dt_spin import SpinDomain
from h2physics.adapters.pifira_spin import (
    PifiraSpinBridge, RotorEvidence, RotorEnergyReference, SpinMedium,
)
from h2physics.core import Origin
from h2physics.thermo.coolprop import CoolPropProperties

model = PifiraSpinBridge(
    spin, spin.RigidRotorSpinThermo(), spin.MilenkoCorrelation(), OrthoParaState,
    evidence=RotorEvidence(
        "https://doi.org/10.1016/j.ijhydene.2014.01.205",
        "https://doi.org/10.1007/BF02396837",
        "declared-pure-H2-medium", Origin.PREDICTED),
    domain=SpinDomain(1., 1000., 96, 1e-10, "authored-rotor-cutoff-envelope"),
    energy_reference=RotorEnergyReference("native-common-para-J0-rotor-U"),
)
state = model.state(.3)  # actual LH2DT para state; native ortho fraction is 1-.3
rotor = model.point(state, 100., .02)

frozen_reference = CoolPropProperties("Hydrogen").state_pt(2e5, 20.)
medium = SpinMedium.from_frozen_state(
    frozen_reference,
    density_evidence_id="authored-normal-H2-reference-density",
    phase_evidence_id="actual-single-phase-reference",
    composition_density_assumption_id="authored-fixed-density-approximation",
    origin=Origin.SYNTHETIC,
)
rate = model.rate(state, medium, .02)
```

The adapter imports neither pifira nor LH2DT at host-module import. Actual native
objects, raw scalar results, reference rotor, existing para state and parameter
fingerprint remain available for deep Python work. Supply reviewed native
instances; changing native rotor/correlation parameters requires rebinding
evidence. Source fingerprints are separate from the parameter fingerprint.

## Meaning of U, Cv, H and the reference

Native rotational energy is relative to the para J=0 ground state. Native ortho
and para share that one reference. `RotorEnergyReference` permits a single common
additive shift of both branches. No frozen ParaHydrogen and OrthoHydrogen EOS
energies are subtracted. The shared `SpinEnthalpyReference` is not relabeled as U;
this adapter has its own rotor-U reference and evidence types.
The point's branch energies and mixture energy follow the declared common
reference; `native_results` retains the original native J=0 scalar outputs.

The returned contribution is spectroscopic rotational U, not full fluid U or H.
Its fixed-composition derivative is the weighted native rotational Cv. The
conversion gap varies with temperature; the native gap derivative equals the
ortho/para Cv difference. Native low-temperature zero rotational capacities are
partial rotor limits, not a fabricated zero total fluid heat capacity.

`storage_terms` exposes energy J, frozen capacity J/K and the derivative with
respect to para fraction J. Their chain rule is

```text
dE_rot/dt = C_rot,frozen * dT/dt - mass * gap(T) * dx_para/dt
```

The native functions supply the energies and derivatives. This identity is
energy accounting, not another EOS or conversion law. `energy_kind="rotational_H"`
requires an explicit `SpinPVAssumption`: either no-mole-change ideal-gas PV, or
caller-evidenced spin-independent PV with its phase scope. The ideal-gas argument
cannot be assigned to a liquid. Evidence identity records an assumption; it does
not validate liquid PV behavior. A complete fluid enthalpy, density, pressure,
phase or volume is never returned.

Absolute rotor U/Cv is appropriate only with a nonrotational sensible baseline.
A full fixed-spin EOS already includes rotational storage. To avoid adding it
twice, supply `baseline_para_fraction` and `baseline_evidence_id` to obtain the
native rotor energy/capacity correction relative to that frozen composition.
The correction vanishes when the fractions agree. A correction capacity can be
negative; it is not a total heat capacity. The caller owns the baseline caloric
decomposition, positive total capacity, reference applicability and pressure/
density/phase closure. No correction creates an evolving-spin liquid EOS.

## Strict natural-conversion admission

The actual Milenko/Petitpas native law uses **ortho** fraction; the existing state
uses para fraction. They have equal molecular masses, so mass/mole fraction
mapping is `c_ortho = 1-x_para`. `PifiraSpinRate.shared_rate` reuses the existing
`SpinRate` record with actual native state/parameter objects. Native conversion
power is positive when ortho-to-para relaxation releases rotational energy and
negative for reverse absorption. It is an internal exchange, not a second
external heat source to add to a total-energy equation.

All physical rate calls retain native `strict=True`: liquid17–32K, gas40–120K,
primary ortho fraction0.62–0.75 and the native density envelope. Native domain
parameters may narrow their installed bounds but cannot widen them through this
adapter. The native maximum density is92kg/m3; the public Milenko publisher
abstract states0.09g/cm3=90kg/m3. `MilenkoAdmission` conservatively caps90 until
the additional interval has source-specific evidence. The native rate function
performs its own density and time-unit conversion; no printed rate coefficients
are reproduced here.

`SpinMedium` requires temperature K, pure-H2 density kg/m3, explicit native phase
branch, density/phase evidence and data role. A directly prescribed medium is a
caller state declaration; native envelope checks alone cannot prove its physical
phase. `from_frozen_state` checks an existing single-phase Hydrogen/ParaHydrogen/
OrthoHydrogen state, retains its actual basis, and requires the composition-
density approximation explicitly. It rejects mixed-phase and other-fluid states.
Fixed-spin density is not silently promoted to density of a changing spin mixture.
The gas branch includes the native dense/supercritical temperature range;
no ideal-gas PV assumption follows from that branch name.

`detailed_balance_probe` is a separately labeled mathematical native extension
for explicit probe fractions. The medium is still strictly admitted and the
rotor cutoff checked, but low-ortho probe rates are **not admitted kinetic paths**.
Native zero at thermal equilibrium and nearby forward/reverse signs do not
validate a general reverse law. Exact pure para is an absorbing state of this
native rate formula. The separate native Petitpas threshold records are retained
in the native module; they are not copied or used to override the primary bounds.
No catalyst, unmeasured impurity effect or low-ortho fallback is inferred.

## Thermostat and driver contract

`thermostat_power` requires an absolute time, clock identity, finite support and
rotor-bath boundary evidence. At prescribed T it returns the actual native rate,
rotor energy rate and `BoundaryPower(heat_w=-conversion_heat_w)`. Heat into the
rotor subsystem is positive; forward relaxation therefore has negative external
thermostat heat. This is a partial energy exchange. It is not a full liquid-vessel
heat boundary, pressure-rise or dormant-time prediction without the other storage
and PV constraints.

pifira provides no exact advance. The library does not synthesize one. A generic
caller driver can integrate `rate.para_fraction_rate_s` and the thermostat power
while enforcing the strict medium/composition domain. Tests/replay inject these
native callbacks into SciPy for a short constant-T case and compare with an
independently integrated closed form. This verification stays above the lower
primary ortho bound and does not predict complete low-ortho equilibration.

The existing `Lh2dtSpinCalorimeter` assumes a constant conversion gap and its
algebraic temperature/fraction relation; it cannot silently receive this model.
A shared general driver would need the supplied energy/capacity/fraction tangents,
an evidenced sensible baseline, temperature/density/phase closure, positive total
capacity, supported absolute clocks, kinetic-domain events and an integrated
total energy ledger. Those integration requirements remain explicit rather than
duplicating the old calorimeter or constructing another trajectory solver.

## Evidence and reproduction

Run `python scripts/check_pifira_spin.py`. It records native/host/test/script/docs
begin/end hashes and LF checks, low/high mathematical limits, cutoff rejection,
direct energy derivatives, existing para-state mapping,24 strict rate points on
actual fixed-spin single-phase density references, density-bound discrepancy,
detailed-balance signs, thermostat integration/refinement, reference-zero and
baseline-correction limits, and PV admission. The high20000K calculation is a
mathematical rigid-rotor limit; it is outside the kinetic domain and establishes
no real molecular/dense-fluid applicability there.

This improves constitutive spin physics within the existing family. There is no
independent measured apparatus comparison, evolving-spin liquid EOS, catalytic
fit, general reverse-conversion validation or coupled finite tank prediction.
The native and receiving-driver limitations remain separate from numerical
verification.

Primary sources are [Petitpas et al.2014](https://doi.org/10.1016/j.ijhydene.2014.01.205),
[Milenko et al.1997 and its publisher domain statement](https://link.springer.com/article/10.1007/BF02396837),
and the [actual public pifira source/release](https://github.com/lyullee/pifira).
The existing review is research/pifira_dependency.toml. MIT covers the separately
installed implementation; no original paper, printed coefficient table, reverse-
threshold table, worked example or measured history is copied or redistributed.
