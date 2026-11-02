# Native ortho/para hydrogen and finite enthalpy coupling

Lh2dtOrthoPara executes the actual optional LH2DT rigid-rotor equilibrium,
first-order conversion rate, exact constant-temperature advance and conversion
heat functions. It retains the native module, parameters and composition states.
A thermostat path and a finite constant-pressure calorimeter make the heat
meaning explicit without inventing an evolving-spin fluid EOS.

The checked native source is lh2dt_models 0.1.2 at revision
b2f276333c1b1793c39f25763703d196d36742ec:
[ortho_para.py](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/ortho_para.py).
At that revision the homogeneous, stratified and layered tank implementations
and dynamic network do not consume its para-fraction state or conversion-heat
functions. Native standalone spin functions exist; native tank spin coupling
does not. The finite calorimeter below is an explicit host enthalpy coupling.

## Native model and evidence

The native rotor assigns statistical spin weight one to even rotational J
(para) and three to odd J (ortho), in addition to rotational degeneracy 2J+1.
Its rigid-rotor level scale is explicitly supplied as rotational_temperature_K.
The para fraction approaches one at low temperature and one quarter in the
high-temperature statistical limit. A finite rotational cutoff is a numerical
choice and must be checked against a larger cutoff.

This level is narrower than a full molecular partition/thermochemistry model.
The [molecular-H2 partition-function study](https://doi.org/10.1051/0004-6361/201527209)
discusses spin statistics, excited states and energy-reference choices.
[Leachman et al.](https://srd.nist.gov/jpcrdreprint/1.3160306.pdf) describe
separate normal, para and ortho EOS. Their distinct fixed-composition surfaces
and reference choices cannot be treated as an arbitrary evolving-spin mixture
by changing a fluid name.

SpinEvidence requires identities for the rate and conversion-enthalpy sources,
phase scope, source references and parameter origin. No catalyst, spontaneous
rate, conversion time scale or heat gap is inferred. Native k=0 is frozen
composition. Native q=0 evolves composition without conversion-heat coupling.
Both choices remain explicit inputs.

SpinDomain bounds temperature and declares a larger reference cutoff and
absolute para-fraction convergence budget. Each equilibrium/rate/advance query
compares the selected and reference native sums. SpinCutoffError retains both
actual targets and their difference on failure. This is a finite-cutoff
comparison, not a rigorous bound on an infinite rotor sum or proof that the
rigid rotor is a qualified liquid or high-temperature dissociation model.

## Exact native thermostat path

All parameters in this example are authored synthetic verification inputs.
They are not measured catalyst or calorimetry values.

~~~python
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path("artifacts/native_packages").resolve()))
import lh2dt.ortho_para as native

from h2physics.adapters.lh2dt_spin import (
    Lh2dtOrthoPara, Lh2dtSpinCalorimeter, SpinDomain,
    SpinEnthalpyReference, SpinEvidence,
)
from h2physics.core import Origin

parameters = native.OrthoParaKineticsParameters(
    conversion_rate_constant_s=1e-5,
    conversion_enthalpy_J_kg=600000.,
    rotational_temperature_K=85.4,
    maximum_rotational_level=24,
)
evidence = SpinEvidence(
    "authored-constant-rate-not-a-catalyst-fit",
    "authored-constant-conversion-enthalpy-gap",
    "dilute-molecular-H2-rigid-rotor/reference-calorimeter",
    ("authored-synthetic-example",), Origin.SYNTHETIC,
)
kinetics = Lh2dtOrthoPara(
    native, parameters, evidence=evidence,
    domain=SpinDomain(10., 40., 96, 1e-10, "declared-low-T-example-domain"),
)
initial = kinetics.state(0.25)
reference = SpinEnthalpyReference(
    reference_para_fraction=1.,
    reference_specific_enthalpy_j_kg=0.,
    reference_id="independent-relative-spin-enthalpy-zero",
)
times = np.linspace(10., 1000010., 101)
trace = kinetics.thermostat(
    initial, temperature_k=20., mass_kg=0.01, pressure_pa=1000.,
    time_s=times, clock_id="absolute-operation-clock",
    pressure_evidence_id="held-low-pressure-reference",
    enthalpy_reference=reference,
)
final_native_state = trace.samples[-1].native_state
thermostat_heat_j = trace.samples[-1].cumulative_external_heat_j
~~~

Despite its native field name, conversion_rate_constant_s has rate units s^-1.
Para fraction is the native dimensionless population fraction; ortho and para
are assigned the same molecular mass in this reduced model. Time is s,
temperature K, held pressure Pa absolute, mass kg and heat/enthalpy W or J.

The thermostat path holds temperature and pressure fixed. Sensible enthalpy
stays fixed, and its irrelevant constant is represented as zero in this trace.
The separate spin enthalpy is defined by

~~~text
H_spin = M * [h_ref + q * (x_ref - x_para)]
~~~

Native q is positive per unit para-fraction increase. Forward ortho-to-para
conversion releases positive internal conversion heat, lowers spin enthalpy
and requires negative external thermostat heat. Reverse conversion absorbs
heat and needs positive thermostat heat to maintain temperature. The exact
integrated external heat follows the actual native fraction change.

BoundaryPower contains only the external thermostat duty. Conversion heat is
an internal transfer and must not be added again as an external source. The
trace separately reports native conversion_heat_w, external_power,
cumulative_external_heat_j and enthalpy_balance_residual_j.

The native exact constant-T step retains its own roundoff endpoint projection
onto [0,1]. The host rejects invalid fractions and never repairs observations.
Native state/parameter types and parameter values remain available; changes
to bound parameter values require a newly evidenced model.

## Finite constant-pressure adiabatic calorimeter

Using the same native functions and enthalpy reference:

~~~python
calorimeter = Lh2dtSpinCalorimeter(
    kinetics,
    mass_kg=0.01, pressure_pa=1000.,
    pressure_evidence_id="held-low-pressure-calorimeter",
    sensible_heat_capacity_j_k=1000.,
    sensible_evidence_id="authored-frozen-composition-sensible-Cp",
    enthalpy_reference=reference,
    reference_temperature_k=20.,
)
adiabatic = calorimeter.adiabatic(
    initial, temperature_k=20., time_s=times,
    clock_id="absolute-operation-clock",
    maximum_time_step_s=5000.,
)
temperature = adiabatic.samples[-1].temperature_k
native_solver_result = adiabatic.native_solver_result
~~~

This is a finite mass calorimeter with a caller-declared total sensible Cp in
J/K. It can include an explicitly declared surrounding calorimeter heat
capacity. Cp must describe frozen-composition sensible storage; a heat capacity
that already incorporates equilibrium conversion would count the same heat
twice. Constant q is a separately evidenced reduced enthalpy increment, rather
than a complete temperature-dependent isomer thermochemical fit.

The adiabatic constraint is constant total H=H_sensible+H_spin. The resulting
temperature is evaluated algebraically from the finite enthalpy balance.
Native kinetics then supplies the para-fraction derivative at that temperature;
SciPy integrates this new coupling and its actual solver result is retained.
No native partition function or kinetic equation is copied.

The held pressure defines a constant-pressure enthalpy/heat path with ordinary
pressure-volume work implicit in that constraint. The model returns no volume,
density, phase split, EOS state or boundary-work prediction. It is not a rigid
tank internal-energy model. A delta-U or fixed-volume coupling would require
an explicit spin-dependent delta-PV assumption/provider. No change in molecule
count gives delta-PV=0 for an ideal-gas isomer conversion at the same T/P; that
authored limit cannot establish the same result for a general liquid mixture.

The arbitrary spin h_ref and sensible reference enthalpy may be shifted without
changing temperature or composition. They do not become CoolProp pure-fluid
zeros. No frozen ParaHydrogen, Hydrogen or OrthoHydrogen state is relabeled as
an evolving spin mixture.

## Executed evidence and limitations

~~~powershell
.venv/Scripts/python.exe -m pytest -q tests/test_lh2dt_spin.py
.venv/Scripts/python.exe -X utf8 scripts/check_spin_integration.py
~~~

[native_spin.md](../research/native_spin.md) records executed native/module,
test/script and license fingerprints with begin/end source-byte guards.
Checks include independent low/high rotor limits, finite-cutoff rejection,
exact constant-T kinetics and continuation, frozen rate, reverse heat sign,
long absolute clocks, thermostat heat, coupled adiabatic final equilibrium,
zero-gap analytic reference, time/tolerance refinement, and enthalpy-zero
invariance. Native states and actual SciPy results remain inspectable.

The 10000 K high-T calculation is a mathematical rotor limit outside the
declared adapter domain. At finite 1000 K, the native rotor still differs from
one quarter by about 2.01e-12; this is distinguished from the asymptotic limit.
The q=600000 J/kg fixtures, including the 300 K reverse-conversion case, verify
signed numerical accounting. They are not measured or full temperature-dependent
H2 isomer enthalpy differences. Temperature/phase-dependent conversion enthalpy,
actual catalyst kinetics, calorimeter Cp and heat-transfer coefficients require
their own evidence and valid domain.

The rigid rotor omits centrifugal distortion, vibrational/electronic excitation
and dissociation. The supplied native constant rate/gap and fixed sensible Cp
do not qualify a liquid-spin mixture, heat/mass transport, catalyst bed, tank
pressure/boiloff or facility operating envelope. Native tank coupling remains a
receiving gap. Future coupling must define enthalpy/internal energy, composition,
PV work, phase and heat ownership before connecting an evolving-spin provider.

Native LH2DT remains separately installed under its checked
[MIT license](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE).
No external property tables, kinetic coefficients, worked examples or native
implementation are bundled by this feature.
