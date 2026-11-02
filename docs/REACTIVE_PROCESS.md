# Finite native gas conversion and process boundaries

`CanteraOpenGasVolume` has an explicit `chemistry="finite_rate"` mode. The same
finite inventory, boundary objects and native integration used by the frozen
volume now support actual homogeneous gas reactions. No second reaction solver,
EOS or process-specific kinetic law is introduced. Default `chemistry="frozen"`
still requires zero reactions and preserves the existing interface.

Cantera 3.2 owns the ideal-gas EOS, physical mass/species/temperature equations,
formation-energy reference, production rates and CVODES integration. The host
appends numerical boundary and reaction integrals through the documented native
ExtensibleIdealGasReactor hooks. These integrals audit the physical solution;
they do not replace its native derivatives.

## Direct Python use

Install the optional chemistry extra. The following is an authored numerical
carbon/steam reference, not a catalyst or apparatus calibration. A real process
must supply its own qualified mechanism, domain, inputs and observation operator.

```python
import hashlib
from pathlib import Path
import cantera as ct
import numpy as np

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_volume import (
    CanteraOpenGasVolume, GasBoundaryRate, GasFeed, GasVent,
)
from h2physics.core import Origin

raw = (Path(ct.__file__).parent / "data/gri30.yaml").read_bytes()
def factory():
    return ct.Solution(yaml=raw.decode("utf-8"), name="gri30")

basis = MechanismBasis(
    "installed-GRI30-gas-reference", hashlib.sha256(raw).hexdigest(),
    "Separately installed Cantera BSD-3-Clause; upstream mechanism provenance",
    ("https://cantera.org/3.2/examples/input/gri30.html",),
    500., 3000., 2e4, 2e6,
)
def rate(name):
    return GasBoundaryRate(
        name, "operation-clock", 0., .5, lambda t: .0001,
        Origin.SYNTHETIC, "authored-prescribed-throughput",
        phase_access="time_only",
    )

initial = ReactiveState(1500., 101325., {"N2": 1.})
feed = ReactiveState(1500., 2e5, {"CH4": .2, "H2O": .5, "N2": .3})
trace = CanteraOpenGasVolume(factory, basis, chemistry="finite_rate").run(
    initial, np.linspace(0., .2, 41), volume_m3=.001,
    clock_id="operation-clock", maximum_time_step_s=.0025,
    relative_tolerance=1e-10, absolute_tolerance=1e-15,
    feeds=(GasFeed(rate("feed"), feed),),
    vents=(GasVent(rate("outlet"), initial),),
)
chemical_h2_kg = trace.integral("reaction:species:H2")
boundary_h2_kg = trace.integral("net:species:H2")
native_reactor = trace.native.reactor
native_network = trace.native.network
```

MechanismBasis is caller evidence, not automatic license clearance or proof of
scientific applicability. The factory must return fresh native full ideal-gas
phases with equal species thermochemistry and reaction definitions. Runtime
multipliers are part of that definition. No mechanism is bundled. Reading the
installed bytes through Python also preserves Unicode Windows paths.

## Material, reaction and energy ledgers

`net:species:<name>` remains boundary transport only. In finite-rate mode the
additional `reaction:species:<name>` integral is native production in
kmol/(m3 s) times native molecular weight in kg/kmol times current native volume.
`reaction_species_integrals_kg` exposes those same numerical integrals.

For species k and element e, the independent inventory defects are

```text
R_k = m*Y_k - m0*Y_k0 - integral(boundary species k) - integral(reaction species k)
R_e = element_inventory_e - initial_element_inventory_e - boundary_element_e
R_U = U - U0 - inlet_enthalpy_integral + outlet_enthalpy_integral - wall_heat_integral
```

Element inventories use native atomic weights and stoichiometry by element name.
`element_names` declares their output order; `element_residual_kg` records the
defects without subtracting a fictitious reaction element source. All returned
ledger arrays are immutable SI arrays. Native formation energies already belong
to U and h. Adding a nominal reaction heat as another external power would count
that energy twice.

Native trial/output mass fractions are not clipped or silently renormalized.
Small negative numerical species remain visible with the replay's declared
acceptance budget. Mechanism-specific temperature/pressure domains and the
positive inventory floor remain active; a failed native run retains actual
objects through GasVolumeIntegrationError.

## Callback ownership and speed

The default rate interface is `callback(time_s, native_phase)`. It supports
state-dependent extraction, including the shared nozzle through a separate
frozen property phase. The callback must treat the native phase as read-only.
Exact thermochemistry/kinetics fingerprints are checked at each native RHS and
accepted output. Native callback failures are retained even if CVODES retries.

Explicit `phase_access="time_only"` calls `callback(time_s)` instead. If every
mass boundary uses it, no callback receives a native phase. Independently owned
native thermochemistry can then avoid the expensive per-RHS definition
serialization while keeping exact accepted-output checks. `definition_guard`
records the chosen policy. Heat callbacks already receive only time. Factory
aliases cannot mutate the owned species or reactions in either reactive path.

The thermochemistry copy is audited once at construction. Exact native thermo
class, coefficients, fit bounds, reference pressure, molecular/atomic data,
species order and runtime reaction multipliers are preserved. Native reaction
reconstruction can round coefficients during SI unit conversion. A structural
gate admits at most2e-15 relative coefficient error, with no absolute allowance;
changes to descriptive `note` metadata are counted separately. This coefficient
limit is not a guarantee on reaction-rate or state error. Both element orders
are recorded; atomic weights are matched by name. Native transport model and
phase name are preserved, although transport is not used by this 0D reactor.

`phase_copy_audits` records source/owned exact fingerprints, maximum coefficient
roundtrip, changed numeric/note counts and both element orders. The owned hash
is checked exactly after construction, with no mutation tolerance.
`source_phase_fingerprint` and `phase_fingerprint` distinguish the two identities.
Native objects returned after completion remain editable; editing them invalidates
the run's recorded evidence. Concurrent native mutation is unsupported.

An exploratory 53-species/325-reaction gas case needed197.5 s with phase-exposing
callbacks and full per-RHS checks. The independently owned time-only case took
9.05 s on a separate run, with final T differing by8.89e-7 K and H2 mole fraction
by4.31e-11. Timings depend on workload and are not a fixed speed guarantee.
The reproducible current check takes a separate plain-native reference and
coarse/fine comparison rather than relying on those exploratory timings.

## Evidence and scope

Run `python scripts/check_reactive_process.py`; see research/reactive_process.md.
It exercises steam-only carbon conversion, a separate oxidative feed, numerical
refinement, source/element/species/U ledgers and a plain native IdealGasReactor
without appended variables. Tests add independent first-order closed/CSTR
oracles, formation-energy warming, multiplier/alias handling and actual installed
H2/O2 closed-reactor comparison. Existing frozen-volume replays remain separate.

This advances one gas-phase production/reforming reference level. It does not
qualify industrial catalytic reforming, a shift bed, coke/solids, porous transport,
surface coverage, a spatial flow reactor, phase change, wall storage or measured
hydrogen yield. Feed thermo is fixed during a run; rates must be continuous with
the declared clock support. Capacity and pressure-driven feed/outlet hardware
require their own qualified closures. H2 spin remains mechanism-specific and
unresolved. No CoolProp or normal/para enthalpy-zero conversion is implicit.

The primary basis is Cantera's [ideal-gas control-volume equations](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html),
[extension and flow APIs](https://cantera.org/3.2/python/zerodim.html),
[reaction APIs](https://cantera.org/3.2/python/kinetics.html), and separately installed
[GRI30 provenance](https://cantera.org/3.2/examples/input/gri30.html). Original
adapter code, cases and tests are provided here; external implementations,
mechanisms and coefficient tables remain separately installed.
