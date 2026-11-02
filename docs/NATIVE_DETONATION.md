# Native equilibrium CJ and frozen normal shock

`h2physics.adapters.detonation.SDToolboxDetonation` composes the actual
Caltech SDToolbox wave solvers and Cantera 3.2 thermochemistry. It solves a
steady planar, adiabatic, gas-only equilibrium Chapman–Jouguet wave for an
explicit homogeneous warm H2/O2/N2/Ar initial mixture, and a frozen normal
shock at an explicitly supplied supersonic speed. These are distinct states:
the frozen leading-shock state retains the reactant composition; the CJ
state is the equilibrium product endpoint.

The level does not predict ignition, DDT, detonation initiation or probability,
cell size, losses, reaction-zone length, propagation through a facility, a
transient waveform or a spatial blast pressure field. No ZND calculation is
exposed. The separately reviewed optional SDToolbox artifact supplies native
solvers; no wave/EOS/equilibrium/kinetics implementation or coefficient table
is copied into this repository.

## Native ownership and installation boundary

The official [Caltech distribution](https://shepherd.caltech.edu/EDL/PublicResources/sdt/)
provides `postshock.CJspeed`, `postshock.CJ_calc`, `postshock.shk_calc` and
`thermo.soundspeed_eq`. The official website's archive date is older than the
April 2026 headers inside the acquired ZIP. The exact artifact SHA256 and
individual native source hashes, rather than a guessed PyPI version, identify
this implementation. The [official license](https://shepherd.caltech.edu/EDL/PublicResources/sdt/LICENSE.txt)
contains BSD-3-Clause terms. Its original notice remains beside the separately
installed package; neither the package nor mechanisms/data from its archive
are distributed with this host.

The reviewed development target is
`artifacts/native_detonation_packages/sdtoolbox`; Python 3.12.14,
Cantera 3.2.0, NumPy 2.5.4 and SciPy 1.18.1 were exercised. The source receipt is
[detonation_dependency.toml](../research/detonation_dependency.toml).
Importing the host module loads neither Cantera nor SDToolbox. The explicit
`NativeSDToolbox.from_installed()` factory checks the ten native Python files
against the reviewed aggregate hash, which is rechecked at run boundaries.
An unavailable or changed provider fails; no alternate algorithm is selected.

The host retains the actual source phase, private native upstream/product
phases, native fixed-ratio solver result, complete native CJ fit return value,
native sound phase, independent isentropic phases and neighboring-Hugoniot
phases. Existing native phase-copy helpers preserve actual native thermodynamic
objects and record their copy audits. Source state and thermochemistry are
not changed by a run. Callers may inspect retained mutable native objects;
later mutation does not update the immutable returned snapshots.

## Python contract

The caller supplies an actual `cantera.Solution` factory,
`MechanismBasis`, `ReactiveState`, `DetonationEvidence` and an explicit
managed native workspace. Temperature is K, pressure is **absolute Pa**,
speed is m/s, density kg/m3, mass-specific h/u are J/kg and entropy J/(kg K).
Initial mole fractions must be explicit and sum to one through the existing
`ReactiveState` contract; no composition is inferred from fuel mass or a
failed dispersion field.

`DetonationEvidence` identifies the homogeneous initial gas evidence,
gas-phase scope, source, stationary-upstream laboratory frame and reference
clock/time. The time labels a static wave condition; it is not an integrated
arrival or ignition time. Synthetic inputs remain synthetic.

Example after separately installing the reviewed optional native package:

```python
from pathlib import Path
import hashlib
import sys
import cantera as ct
from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.detonation import (
    DetonationEvidence, NativeSDToolbox, SDToolboxDetonation,
)
from h2physics.core import Origin

sys.path.insert(0, str(Path("artifacts/native_detonation_packages").resolve()))
mechanism = Path(ct.__file__).parent / "data/h2o2.yaml"
text = mechanism.read_text(encoding="utf-8")
basis = MechanismBasis(
    "installed-h2o2-thermochemistry", hashlib.sha256(mechanism.read_bytes()).hexdigest(),
    "BSD-3-Clause", ("https://cantera.org/3.2/examples/input/h2o2.html",),
    300., 3400., 5e4, 5e6,
)
model = SDToolboxDetonation(
    NativeSDToolbox.from_installed(), lambda: ct.Solution(yaml=text), basis,
    native_workspace="artifacts/detonation_workspace",
)
total = 2 + 1 + 3.76
initial = ReactiveState(300., 101325., {"H2": 2/total, "O2": 1/total, "N2": 3.76/total})
evidence = DetonationEvidence(
    "authored-example", "authored-uniform-premix", "warm-neutral-gas",
    "example-reference-clock", 100., "stationary-upstream-laboratory", Origin.SYNTHETIC,
)
cj = model.cj(initial, evidence=evidence)
leading = model.frozen_shock(initial, speed_m_s=cj.speed_m_s, evidence=evidence)
assert cj.native_cj_result[0] is cj.native_cj_phase
print(cj.speed_m_s, cj.final.pressure_pa, leading.final.temperature_k)
```

`CJspeed` requires a filename and creates internal phases without accepting a
caller phase factory. The host uses Cantera's own YAML writer at 17-digit
precision inside a managed temporary subdirectory. The filename is ASCII
relative to the existing working directory, avoiding the observed native
Windows Unicode path lookup failure. It does not change CWD, Cantera search
globals or native code. The YAML is removed after the call. Its hash and the
actual reloaded phase survive in `NativeMechanismBridge`.

Admission requires exact native thermo-model/species identity, coefficients,
reference pressures, elemental atomic weights and fit bounds after that
native round trip. Kinetics/transport are unused by this equilibrium level;
their YAML round-trip equality is not claimed. An actual ConstantCp mechanism
loses declared temperature bounds in the native YAML round trip on this
installation and is rejected for CJ before solving. Direct-object frozen
shocks with that native thermo model work and supply the monatomic ideal
verification. No host reconstruction repairs the changed bridge.

## Conservation and CJ checks

For stationary upstream gas and wave speed D, the shock-frame velocities are
w1=D and w2=(rho1/rho2)D. Laboratory downstream velocity is D−w2. This
shock-frame conversion comes from mass continuity; the reported mass-flux
residual checks that arithmetic identity and is not a separate native velocity
measurement. The independently evaluated pressure and caloric jump residuals
are:

- momentum: P2 + rho2 w2² − P1 − rho1 D²;
- total enthalpy: h2 + w2²/2 − h1 − D²/2;
- Hugoniot: u2 − u1 − (P2+P1)(v1−v2)/2;
- each elemental mass fraction in products minus its upstream value.

These equations are evaluated with actual native state properties. Native
species formation/reference energies are retained; no heat of combustion is
added separately. Species fractions may change across CJ while elemental mass
is conserved. Both shocks must compress and increase entropy.

`CJspeed(fullOutput=True)` supplies the native density-fit minimum and its
R²/curve. The actual `CJ_calc` is then called at that native fitted density
ratio with an explicit tighter thermochemical tolerance. Both returned speeds
are retained; the result speed is the tighter native fixed-ratio solve.
Neighboring native `CJ_calc` states must have larger speeds and pass the same
jump audits. This is a local minimum check, not a replacement host CJ search.

At the final product state, two independent native Cantera SV-equilibrium
states estimate (dP/drho) at fixed entropy and elemental composition.
The result must satisfy w2/a_eq≈1. The native SDToolbox TP-equilibrium sound
helper is also called on a separate private phase and compared to that
estimate. Cantera's native frozen `sound_speed` is reported separately.
The [Caltech jump-condition report](https://shepherd.caltech.edu/EDL/PublicResources/sdt/doc/ShockDetonation/ShockDetonation.pdf)
defines the wave/CJ conditions; the
[Cantera thermodynamic API](https://cantera.org/3.2/python/thermo.html)
owns the equilibrium/property calls.

Default absolute gates are mass-flux 1e-7 kg/(m2 s), momentum 0.1 Pa,
total-H/Hugoniot 0.01 J/kg and elemental mass-fraction 1e-10. Relative gates are
CJ sonic 1e-4 and native-vs-independent sound 2e-4; native fit R² ≥0.99999.
Gates are fixed across baseline/refinement. Settings refine the native
fixed-ratio solve tolerance, independent density difference and neighboring
density check. Native `CJspeed` search-grid/inner tolerances are not exposed
and are not claimed to have been refined.

## Domains, failure evidence and remaining native hooks

Only a neutral native ideal-gas phase is admitted. CJ additionally requires
positive explicit H2 and O2 and only H/O/N/Ar elemental inventory. Hydrogen's
spin partition is the native mechanism's unresolved H2 state, not a normal-
or para-hydrogen cryogenic EOS. No condensed products or dense/nonideal
high-pressure EOS are solved. Caller pressure limits define an explicit
computational envelope; they do not validate that envelope physically.
Equilibrium is constrained to the caller's actual native species set. The
installed h2o2 fixture has ten species and represents nitrogen as N2; it does
not include atomic nitrogen or nitrogen oxides. Its air example is therefore
verification of that restricted thermochemical model, not proof that all
chemically relevant equilibrium products were included.

The declared temperature envelope cannot exceed actual native thermo fit
bounds. Initial/final states, neighboring states and all host-visible
independent SV-equilibrium probes must lie inside that envelope and their
native bounds. The native sound helper's fixed ±1% T/P neighborhood is checked
before calling it. Native `CJspeed` iterations and the sound helper's further
transformed internal probes are not exposed: their complete paths cannot be
certified to stay inside the declared fit envelope by this adapter.

Native failures, invalid fit/minimum, negative/nonfinite returned fractions,
unclosed jumps and out-of-domain accepted states raise
`DetonationAuditError`. The original exception is its cause; attempted actual
phases, copy audits, completed raw native fit/CJ returns, bridge and completed
diagnostics remain accessible. There is no native iteration failure fallback,
clipping or deletion of difficult species/phases.

An improved native object API should accept owned Solution objects and return
all internal fit/sound trial states plus convergence status, configurable
global iteration limits/search-grid controls and thermofit admission hooks.
The current native `CJspeed` outer fit loop has no public global iteration
limit; applications needing hard cancellation should isolate the calculation
in their job process. The host neither monkeypatches that loop nor duplicates
its algorithm.

## Executed verification and experimental boundary

Run from the repository root:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_detonation.py -q
.venv/Scripts/python.exe -X utf8 scripts/check_detonation.py
```

The authored 300 K/101325 Pa H2:O2:N2=2:1:3.76 case gives approximately
D 1976.319 m/s, equilibrium T 2964.680 K and absolute P 1.577915 MPa.
Actual native monatomic ConstantCp argon shocks at Mach 2 and3 match independent
constant-gamma conservation limits. Those analytic
[normal-shock relations](https://www.grc.nasa.gov/www/k-12/airplane/normal.html)
are used only as verification formulas. Warm elevated initial conditions,
native fixed-ratio and sound-difference refinements, domain failure retention,
native YAML bound-loss rejection and private-object preservation are exercised.
Detailed measured results/fingerprints are in
[native_detonation.md](../research/native_detonation.md).

Acquired ELVHYS DOI 10.18710/M5LOLM describes LH2 pressurization and membrane
BLEVE experiments. Its containment oxygen and ambient temperatures do not
define homogeneous tube premix X/T. It supplies no declared detonation
identification or propagation speed. Its dynamic pressure signals are not
promoted to absolute equilibrium CJ states. No direct comparison is
admissible. This model is verified on authored limits and native conservation;
material-specific chemical validation, experimental CJ validation and
facility qualification remain open.

`CJWaveResult` and `FrozenShockResult` require one-use issuance from their
completed native solver paths. Their retained wave states, phase states, native
solver receipts and conservation results are sealed and rechecked by
`require_current()`. The deferred `detonation-result-issuer` contract uses the
synthetic H2/O2/N2 case and the explicit `detonation-native` profile. That contract
has not been executed and does not add experimental validation evidence.
