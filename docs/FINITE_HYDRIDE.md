# Finite gas and hydride inventory

`h2physics.storage.finite_hydride.FiniteHydrideBed` resolves a closed pure-H2 gas
inventory, reversible solid hydrogen loading, gas temperature, solid temperature
and their combined internal energy. Gas pressure and fugacity respond to the
remaining finite gas. The existing `HydrideKinetics`, `VanthoffPlateau`,
`ArrheniusRate` and `HydrideParameters` remain the shared rate/equilibrium and
parameter objects; their correlations are not copied or replaced.

This extends `storage.hydride_dynamic` beyond the existing reservoir-driven
`HydrideBed`, whose prescribed fugacity does not deplete a gas inventory. One
uniform gas and one uniform solid temperature are resolved here. SciPy integrates
the new coupled conservation equations; every gas DU/PT/rho-T state, fugacity and
required derivative comes from injected native thermodynamics. The built-in
composition uses the existing `CoolPropProperties` HEOS provider and actual
native CoolProp fugacity/derivative objects. No gas EOS is implemented here.

## Conserved material and energy

Let capacity be `m_cap` kg H2, molar mass `M` kg/mol H2, loading `x`, free gas
volume `V_g` and positive absorption rate `r = dx/dt` from the existing kinetics.
All mass counts the H2-equivalent hydrogen, including hydrogen bound as atomic
hydrogen in the solid. The metal/skeleton inventory is fixed.

```text
n_cap = m_cap / M
m_g = m_g,0 - m_cap (x - x_0)
rho_g = m_g / V_g
uptake = m_cap r                     [kg/s, signed]
native gas state = DU(rho_g, U_g/m_g)
r = existing_kinetics(x, T_s, native_H2_fugacity)
```

There are no external H2 ports or infinite gas reservoir. `m_g + m_cap*x` stays
constant algebraically. An independently integrated signed uptake row checks the
gas and solid material transfers separately. Fixed free gas volume is an input;
it is not guessed from tank volume or powder mass.

`BoundHydrogenEnergyReference` anchors bound hydrogen to the selected native gas
energy reference at explicit `T_ref`, `P_ref`. Desorption reaction enthalpy is
positive and expressed **per mole H2**. With condensed-phase PV neglected,

```text
e_bound = h_H2,ref * M - DeltaH_des,ref              [J/mol H2]
U_s = C_s (T_s - T_ref) + n_cap x e_bound             [J]
```

At the reference conditions, transferring one mole from gas to solid changes
closed-system internal energy by

```text
DeltaU_abs,ref = e_bound - u_H2,ref*M
              = P_ref*M/rho_H2,ref - DeltaH_des,ref
              = R*T_ref - DeltaH_des,ref             [ideal-gas verification limit]
```

Thus the isobaric sorption heat is not itself the closed-system internal-energy
change. The native normal-H2 verification reference gives about −21504.20 J/mol
for `DeltaH_des=24000 J/mol` at 300 K. The model keeps that pressure-work term.

Interface material enthalpy is taken from the donor: current gas enthalpy during
absorption, and native H2 at solid temperature/current gas pressure during
desorption. This explicitly assumes newly desorbed gas leaves the solid at its
temperature. Let `H_transfer = uptake*h_interface`, positive toward the solid,
and `Q_gs = K_gs*(T_s-T_g)`, positive toward gas. The implemented balances are

```text
dU_g/dt = -H_transfer + Q_gs + Q_g,external
dU_s/dt = +H_transfer - Q_gs + Q_s,external
dT_s/dt = (dU_s/dt - n_cap*r*e_bound) / C_s
d(U_g+U_s)/dt = Q_g,external + Q_s,external
```

`integrated_nominal_reaction_heat_j` records `integral(n_cap*r*DeltaH_des dt)`
for interpretation. It is a diagnostic, never a second heat input. Adding it to
the total-U equation would count binding energy twice. Gas/solid material
enthalpy and interphase heat appear with opposite signs and cancel in total U.

The solid heat capacity is constant and independent of loading in this level.
The caloric and Vanthoff desorption enthalpies must agree at the stated reference.
A constant-enthalpy plateau and this reduced solid caloric model are matched at
that reference; they do not establish exact temperature-dependent free-energy
consistency over a broad alloy domain. Loading-dependent solid heat capacity,
phase-dependent chemical potential and independent material evidence remain
required for a thermodynamically qualified alloy model.

## Python use

The reservoir-driven `HydrideBed` returns a reduced trajectory tied to the
material parameters and initial state that produced it. The trajectory checks
that its sample vectors share one finite, increasing time axis, that stored
hydrogen agrees with the loading capacity, and that the reduced energy ledger
reconstructs from retained values. Only the integration path may issue a
trajectory receipt; copying or directly constructing an output is rejected.
This protects API provenance and bookkeeping consistency; it does not qualify
the chosen material correlations or substitute for independent validation.

`HydrideParameters.swing_capacity_kg(lower_fraction, upper_fraction)` reports
the nominal hydrogen mass between two explicitly selected loading fractions.
Fractions must lie in `[0, 1]`, and the upper endpoint cannot be below the lower
one. For example, a declared 0.1-to-0.8 window spans 70% of the parameter's
nominal capacity. This arithmetic does not establish that operating pressure,
temperature, kinetics or degradation allow either endpoint to be reached; use
the dynamic trajectory or finite-vessel model for those questions.

The following coefficients are original synthetic verification inputs, with no
claim that they represent a measured alloy. `HydrideParameters` uses the native
H2 molar mass rather than a rounded 0.002 kg/mol conversion.

```python
import numpy as np

from h2physics.storage.hydride import (
    ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState, VanthoffPlateau,
)
from h2physics.storage.finite_hydride import (
    BoundHydrogenEnergyReference, FiniteHydrideBed, FiniteHydrideDomain,
    FiniteHydrideHeatBoundary, FiniteHydrideHeatInput, HydrideGasThermodynamics,
)

gas = HydrideGasThermodynamics.coolprop("Hydrogen")  # explicit normal-H2 choice
parameters = HydrideParameters(
    hydrogen_capacity_kg=.002,
    heat_capacity_j_k=1000.,
    reaction_heat_j_mol_h2=24000.,
    hydrogen_molar_mass_kg_mol=gas.molar_mass_kg_mol,
    ambient_conductance_w_k=0.,
)
kinetics = HydrideKinetics(
    VanthoffPlateau(24000., 80., 1e5),
    ArrheniusRate(.01, 0., 300.),
    ArrheniusRate(.02, 0., 300.),
)
reference = BoundHydrogenEnergyReference.from_gas(
    gas, temperature_k=300., pressure_pa=1e5,
    desorption_enthalpy_j_mol_h2=24000.,
    evidence_id="authored-synthetic-verification-heat",
)
bed = FiniteHydrideBed(
    parameters, kinetics, gas, reference,
    FiniteHydrideDomain(200., 600., 1e3, 1e7, minimum_gas_mass_kg=1e-7),
    free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
)
heat = FiniteHydrideHeatBoundary(
    "authored-operation-clock", 100., 200.,
    lambda t, state: FiniteHydrideHeatInput(300.),
    "authored-adiabatic-boundary",  # zero conductances and zero prescribed heat
)
trace = bed.simulate(
    np.linspace(100., 200., 201), HydrideState(.1, 300.),
    gas.state_pt(3e5, 300.), boundary=heat,
    clock_id="authored-operation-clock", maximum_step_s=.5,
)
last = trace.snapshots[-1]
print(last.fraction, last.gas_mass_kg, last.solid_temperature_k, last.gas.pressure_pa)
print(trace.termination, max(abs(trace.total_energy_residual_j)))
```

The example ends near `x=0.439688`, solid 307.208 K, gas 307.096 K and 134561 Pa.
The gas is not held at its starting pressure. `gas.state_pt` and all pressures
use Pa absolute. Heat signs are positive into the named inventory. Baths enter
through the existing solid ambient conductance and the separately declared gas
ambient conductance; prescribed gas/solid heat is additional explicit boundary
power. A zero-conductance/zero-power boundary is adiabatic.

Normal `Hydrogen` and `ParaHydrogen` are explicit native choices. They retain
their distinct `PropertyBasis` spin identity and native energy zero. Reference,
capacity and gas molar masses must agree, as must native/reference density,
enthalpy and internal energy. No normal↔para or gas-reference transformation is
inferred. A test explicitly translates both native gas energies and bound-H
energy by the same declared zero shift and verifies identical physical paths;
altering only one side is not a valid reference conversion.

`HydrideGasThermodynamics` also accepts caller-supplied native functions and
actual native objects. Its public functions are `state_rho_u`, `state_pt`,
`fugacity_pa` and, for the isothermal reference, `state_rho_t` plus
`isothermal_mass_energy_derivative`. The latter returns
`d[m*u(m/V,T)]/dm = u + rho*(du/drho)_T` in J/kg, from the selected native EOS.
Source identity, explicit basis and native objects remain available in the trace.
The injected provider must truly describe pure H2 in that declared basis;
matching a string alone cannot establish its scientific or provenance claims.

## Clock, limits and numerical results

The heat callback receives absolute seconds and an immutable physical snapshot.
Its clock must match the simulation clock, and its finite support must contain
the requested window. This is a continuous-boundary integration level; split
runs at known discontinuities and carry the actual ending gas/solid states.
No sensor clock alignment or extrapolation is performed.

`FiniteHydrideBed.simulate(..., gas_port=...)` optionally accepts a
`FiniteHydrideGasPortBoundary` on the same clock. Its callback supplies a signed
H2 mass flow and a native stream state through `FiniteHydrideGasPortInput`.
Positive mass enters the finite gas inventory; negative mass exits. Incoming
enthalpy uses the supplied inlet state. For discharge, the port must use the
exact current gas state so outlet enthalpy cannot be selected independently of
the inventory. The trace retains cumulative external H2 mass and stream
enthalpy, and the gas/total mass and energy residuals include those two ledgers.
With `gas_port=None`, the existing closed-inventory behavior and zero port
ledgers remain.

This port boundary consumes a caller-supplied mass-flow history; it does not
derive flow from pressure, valves, leaks or a transfer protocol. It permits only
a single gas-phase H2 stream on the bed's native property basis. A station
controller, hose inventory, pressure-flow law and vehicle-tank validation remain
separate models. A ported trace conserves its declared inlet/outlet ledger but
does not by itself establish a qualified refuelling process.

The gas density/internal-energy flash and gas/solid temperatures must remain
inside the declared domain; gas must stay single gas/supercritical H2. Liquid,
two-phase inventory and freezing are outside the model. Trial loadings and gas
masses are never clipped. An invalid trial raises `FiniteHydrideIntegrationError`
with its trial time, raw solver vector and native thermodynamics. It is not
misrepresented as an accepted physical state. Refining the maximum time step or
using a more appropriate constitutive/domain model is a caller decision.

A terminal root locates `m_g = minimum_gas_mass_kg` from above. It preserves the
positive mass and actual root time at `trace.event_time_s`, appends that root to
the returned trace, and reports `termination="gas_inventory_floor"`. The result
may end before the requested last output. This is an explicit guard level, not
a claim of exact gas exhaustion or an additional rate-limiting correlation.
Normal kinetics can approach equilibrium before reaching that floor. Solid
capacity endpoints retain the existing rate-law behavior; there is no loading
repair or invented completion time.

`trace.native_solution` is the actual SciPy `OdeResult`, including event arrays;
`trace.gas_thermodynamics.native_objects` retains the actual native objects.
Returned arrays are immutable. Mutating native objects or the solver result
afterwards invalidates their correspondence with the recorded trace. Internal
integrated energies use `energy_scale_j` for conditioning and always return SI J.
The actual solver is DOP853 with explicit relative tolerance and maximum step.

Direct `FiniteHydrideTrace` construction checks that the native snapshots and
clock share one ordered sample axis, all cumulative ledgers have matching finite
vectors, every H2 gas/energy basis agrees, the inferred free-gas volume and solid
capacity remain constant, and the reported mass/energy residuals reconstruct from
the retained snapshots and integrated terms. A malformed receipt cannot establish
its own fabricated residual baseline. This is an integrity check on the declared
trace fields; it does not rerun the ODE or establish numerical accuracy.

Gas, solid and total-U residuals are separate. Integrated material enthalpy,
interphase heat, external heat and H2 uptake are inspectable. Mass conservation
from the algebraic total and independent transfer quadratures, numerical ledger
closure, time refinement and independent measured validation are distinct checks.
The API returns diagnostics; applications must declare acceptance budgets.

## Isothermal reference and evidence

Pass `isothermal_temperature_k=T` only when both initial temperatures are exactly
that value and the native derivative functions are available. This holds finite
gas and solid at the selected temperature with **explicit thermostat heat**. It
does not introduce an infinite H2 reservoir. Separate integrated gas/solid
thermostat heat is included in external heat and total-U accounting.

For an authored pure ideal gas at fixed T, the existing plateau/kinetics produce
a finite-gas analytic limit. Writing native `P=alpha*m_g`, `b=alpha*m_cap/P_eq`
and `x_eq=(alpha*m_total/P_eq-1)/b`, the absorption-only limit obeys
`dx/dt=k*b*(x_eq-x)*(1-x)`. Its ratio
`(x_eq-x)/(1-x)` decays exponentially with rate `k*b*(1-x_eq)`. The source tests
derive this reference independently and run actual native Cantera constant-cp
H2; no ideal-gas EOS or separate kinetic implementation is added to the library.
The same test checks total thermostat heat per mole equals `RT-DeltaH_des`,
including the gas pressure-work term.

The native integration issues a one-use trace-construction token. A copied or
directly reconstructed `FiniteHydrideTrace` cannot reseal altered history as a new
native result; the deferred constructor case records clone rejection. The trace
constructor also validates ordered snapshot clocks,
compatible native gas/reference bases, fixed free volume and capacity, and
reconstructed gas/solid transfer and energy ledgers before retaining caller arrays.
`HydrideGasThermodynamics` additionally requires typed native property basis/source
identity, actual retained native objects and callable advertised capabilities;
`BoundHydrogenEnergyReference` requires a typed gas state and textual evidence ID.
The deferred `finite-hydride-trace-constructor-integrity` case checks forged energy,
clock and uptake entries plus malformed provider/reference identities on Nurion; it
has not been executed.

```powershell
.venv\Scripts\python -m pytest tests/test_finite_hydride.py -q
.venv\Scripts\python scripts/check_finite_hydride.py
```

The replay uses actual native normal/para hydrogen, three time steps, zero
kinetics, absorption/desorption, thermally induced rate reversal, a localized
positive gas floor, and independently sampled native thermostat heat. A fresh
native PT provider reconstructs total mass/U from reported pressures,
temperatures and loading without using model-stored masses/energies. Fixed gates
are 1e-13 kg transfer/mass, 1e-5 J gas/solid/total energy, and independent source/
refinement targets. Exact run values, versions, local timing and source hashes
are in [research/finite_hydride.md](../research/finite_hydride.md).

Acquired AB2 shell-temperature records are not used to infer alloy parameters.
Their pressure unit/basis, MFC standard conditions, free gas volume/porosity and
bed-versus-shell temperature roles remain unresolved. No shell thermocouple is
renamed a bed temperature or fitted against this model by implication.

Remaining work includes qualified material PCT/caloric functions, porous gas
transport, powder/porosity evolution, wall storage, spatial thermal gradients,
external process ports, controlled-cycle boundaries and independent apparatus
comparisons. This checkpoint advances a finite lumped level, not complete hydride
storage qualification. No receiving repository or external record is changed.

If accepted SciPy integration succeeds but later hydride snapshot/result assembly
fails, `FiniteHydrideIntegrationError` retains the exact native solution object,
the most recent trial state and the original exception chain. The deferred
`finite-hydride-postsolve-failure-retention` contract induces that boundary after
the solver returns; it has not been run.

Primary sources: [Brown et al., 2006](https://doi.org/10.1115/FUELCELL2006-97140)
([accessible primary paper](https://escholarship.org/content/qt67p6w2p3/qt67p6w2p3.pdf)),
[Krane et al., 2021 primary preprint](https://arxiv.org/abs/2107.06095),
[Leachman et al. hydrogen EOS](https://doi.org/10.1063/1.3160306), and
[CoolProp native low-level API](https://coolprop.org/coolprop/LowLevelAPI.html).
The conservation derivation, coupling, documentation, parameters and tests are
original; paper prose, coefficient tables, figures and implementations are not
reproduced. Existing optional native packages retain their own terms.
