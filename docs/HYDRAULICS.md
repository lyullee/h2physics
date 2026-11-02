# Shared Darcy flow and native pipe bridge

## Frozen native mixtures

The same `solve_isothermal_compressible_gas_flow` accepts the existing
`CoolPropMixtureIsothermalEOS`. Density, molar mass and the isothermal pressure
derivative come from its captured CoolProp HEOS mixture. The result reports
total mixture mass flow. It does not report pure-hydrogen mass flow or solve
species transport, changing composition or an evolving hydrogen spin fraction.
Reference, component order, mole fractions and composition identity remain
part of the provider contract. Retained native-state composition changes cannot
silently change the provider's captured molar mass.

This extension retains the shared density integral, Reynolds root, held
viscosity and independent pressure-ODE reconstruction. It adds no mixture EOS
or alternative Darcy solver. Numerical tests of native properties and hydraulic
guards have passed; the full three-level mixture-network calculation has no
collected final outcome and remains unverified. Directly interpolated tables
are not admitted here: the density integral and momentum ODE require a
consistent pressure derivative, beyond pointwise property error alone.

## CoolProp isothermal compressible flow — 2026-11-01

The existing `solve_isothermal_compressible_gas_flow` also accepts
`eos=CoolPropIsothermalEOS("Hydrogen")`. This route evaluates pressure-dependent
density and isothermal derivatives through native CoolProp HEOS. It retains
the same Reynolds root and caller-supplied Darcy correlation. Viscosity is a
declared held constant; using native viscosity at one reference state does not
make it a variable-viscosity calculation. `eos=None` plus an explicit molecular
mass selects the original ideal analytical reference.

With mass flux `G = mass_flow/area`, steady mass and momentum conservation give
`G²*(f*L/D + 2*ln(rho_up/rho_down)) = 2*integral(rho(P,T), dP)`. The density
integral comes from CoolProp states. A separately integrated pressure ODE
reconstructs the downstream pressure and checks the subcritical branch at its
adaptive evaluation points. Density, native phase, provider definition and the
isothermal sonic singularity are gated; no ideal replacement is attempted.
The adaptive path check is numerical evidence, not a mathematical global
guarantee. See the [CoolProp derivative API](https://coolprop.org/coolprop/HighLevelAPI.html)
and [Conner and Manousiouthakis, nonideal isothermal pipeline context](https://arxiv.org/abs/2410.20292).
Their cubic thermodynamic model is not implemented here.

The result retains actual reconstructed pressure/residual in Pa and adds
`density_integral_pa_kg_m3`, `density_integral_error_pa_kg_m3`,
`momentum_integral_residual_pa_kg_m3`, `eos_identity`,
`maximum_isothermal_mach_number` and `viscosity_model`. Native
`specific_gas_constant_j_kg_k` is `None`; it is not an effective ideal constant.
Zero local-loss coefficient, a horizontal constant-diameter pipe and fixed
temperature remain required. This does not calculate choking, temperature
evolution, phase change, elevation or calibrated fitting losses.

Final local validation passed six native tests and seven existing hydraulics
tests (13/13 in 43.98 s), plus the existing ideal momentum case. At 300 K and
70→60 MPa across 100 m/0.1 m with authored Darcy factor 0.02 and held viscosity
9e-6 Pa s, native flow was 47.5707708812 kg/s. An independent density-variable
ODE using direct CoolProp derivatives recovered the outlet within 1.12e-7 Pa;
production pressure reconstruction differed by 5.22e-8 Pa. The low-density
ideal-limit flow difference was 8.39e-7 relative. Phase, sonic, definition,
molecular-mass and discontinuous-friction failures were rejected. These are
numerical/native integration checks, not experimental pipeline qualification.

## Evidence for the change

The combined finite-supply heating case exposed a native fixed-iteration inconsistency.
At a retained modeled transition point, the returned Re is about 2296.116 and the native
momentum residual is zero. Reconstructing pressure loss from the reported friction and
actual mass flow instead gives about 44.31 Pa. The original reported zero therefore does
not certify the final constitutive equation. The source point is authored simulation output,
not a copied apparatus record or experimental observation.

There are two distinct issues. A converged pressure root must close the final Darcy loss;
a discontinuous friction law can also leave a pressure-loss interval with no root. The
new bracketed solver rejects the retained native-law gap despite a root flag. The supply
example explicitly chooses a continuous library correlation, with that physical closure
change recorded. Numerical continuity does not establish better experimental accuracy in
transitional two-phase flow.

## Kernel and explicit correlation

`hydraulics.DarcyGeometry(length_m, diameter_m, roughness_m, local_loss_coefficient)`
defines the path. `solve_darcy_flow` receives positive upstream density, viscosity and
driving pressure together with `friction_law(Re, relative_roughness)`. It solves flow
magnitude; the caller owns direction, hydrostatics and thermal transport.

```text
Re = rho * velocity * D / mu
pressure_loss = (f_Darcy * L/D + K) * rho * velocity**2 / 2
mass_flow_magnitude = rho * area * velocity
```

An expanding bracket and SciPy brentq use a dimensionless velocity coordinate. The final
pressure loss is recomputed from the accepted velocity and its friction factor. Defaults
are 1e-7 Pa absolute / 1e-10 relative pressure gates. `DarcyFlowResult` retains velocity,
flow, Re, friction, actual modeled loss, residual and root diagnostics. A failed pressure
gate raises `HydraulicConvergenceError.result`; a scalar root flag cannot override it.
Correlation exceptions propagate. No alternate correlation or clipped solution is chosen.

The explicit supply example uses the direct
[fluids Churchill_1977 function](https://fluids.readthedocs.io/fluids.friction.html#fluids.friction.Churchill_1977).
The [upstream MIT license](https://github.com/CalebBell/fluids/blob/master/LICENSE.txt)
and installed version/module checksum are recorded. No library implementation or roughness
table is copied. The selected function returns Darcy friction; the generic fluids dispatch
interface has its own low-Re policy, so the example injects the direct named function.
No experimental validity range is inferred from an interface that accepts every positive Re.

```python
from fluids.friction import Churchill_1977
from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow

result = solve_darcy_flow(
    DarcyGeometry(1., .001, 1e-6),
    density_kg_m3=72., viscosity_pa_s=1.45e-5,
    driving_pressure_pa=250., friction_law=Churchill_1977,
)
```

## Native state, heat and viscosity ownership

`Lh2dtDarcyPipe(native_pipe, bridge, viscosity_reader=..., friction_law=...,
friction_law_id=..., result_factory=...)` reads native geometry and live heat/elevation
parameters. It retains the exact native property instance and actual native PipeResult
factory. It delegates viscosity to the explicitly supplied reader; a gas provider and a
native HEM phase-weighted reader can use the same flow kernel.

The checked HEM example injects the pinned native `_effective_viscosity` capability.
That private hook is version-specific; request 009 asks for a public capability. Neither
the root solver nor the fluids friction function resolves phase slip or replaces the EOS.
HEM application is an explicit homogeneous-mixture approximation of this correlation.

Direction follows total pressure with declared elevation. For a flowing component,
`h_transmitted = h_upstream + heat/abs(mass_flow)`; reverse transport uses the actual
reverse upstream state. Stagnant nonzero prescribed heat requires a stored thermal
inventory and raises. `DarcyPipeEvaluation` retains the actual `native` result, selected
`friction_law_id` and optional `hydraulic` diagnostics. Native geometry remains accessible.

## Verification and limits

Portable tests check an independent Poiseuille solution, a constant-friction analytic
relation, defined root-endpoint diagnostics, an authored constitutive gap, reverse upstream
heat and live parameter changes. The optional installed correlation is checked through
the transition region. The full supply verification retains the original native failure,
rejects the same discontinuous-law gap, and checks corrected accepted Darcy losses alongside
time refinement and mass/energy inventories. See `scripts/check_finite_supply.py` and
`research/native_finite_supply.md`.

This remains an upstream-density quasi-steady loss model. Large compressibility along a
line, distributed flashing, critical flow, waves, phase slip, fittings data and independent
hydrogen pressure-loss experiments need their appropriate model level and evidence. The
native receiving request delegates this one kernel rather than maintaining duplicate gas
and HEM numerical implementations.

## Steady isothermal compressible ideal-gas pipe reference

`solve_isothermal_compressible_gas_flow()` is a separate steady reference for a straight,
horizontal, constant-diameter, single-phase ideal-gas line. It accepts upstream and
downstream absolute pressures, one temperature, molecular mass, constant dynamic viscosity,
shared `DarcyGeometry` with zero local-loss coefficient, and a caller-owned Darcy friction
law plus its identity. Positive flow goes from the higher upstream pressure to the lower
downstream pressure; swap the endpoints to represent reverse flow. The Reynolds number is
solved with the injected friction law, and the returned mass rate is checked by reconstructing
the downstream pressure.

For area `A`, specific gas constant `Rs`, Darcy factor `f_D`, length `L`, diameter `D`, and
endpoint pressures `p1 > p2`, the steady one-dimensional momentum relation used here is

```text
mdot^2 = A^2 (p1^2 - p2^2) / (Rs T [f_D L/D + 2 ln(p1/p2)])
```

The logarithmic term retains the axial acceleration associated with expansion. The formula
follows the integrated isothermal ideal-gas pipe balance discussed by Kim and Singh,
*A Novel Equation for Isothermal Pipe Flow*, Chemical Engineering 119(6), 66–70 (2012),
and the standard Darcy friction closure. The implementation is original and obtains `f_D`
from the caller rather than reproducing a correlation. The API intentionally excludes
elevation, heat exchange, local losses, real-gas EOS, choking, transient line inventory, and
experimental qualification; it is a reference level, not the high-pressure hydrogen real-gas
answer. Use the CoolProp-backed native equipment path for real-gas station properties where
that provider owns the equipment model.

The `isothermal-compressible-gas-pipe-momentum` case is registered under the Hangang and
Nurion `gas-compressible-pipe` profiles. Its constant-friction analytic contract is deferred
and unexecuted.

### Source

- Kim, J. S. and Singh, N. (2012), “A Novel Equation for Isothermal Pipe Flow,”
  *Chemical Engineering*, 119(6), 66–70. Original implementation is based on the
  independently rederived one-dimensional balance above; no article wording, figure or code
  is included. [Article record](https://www.chemengonline.com/a-novel-equation-for-isothermal-pipe-flow/).
- Kowalczuk, Z. and Tatara, M. S. (2020), “Improved model of isothermal and incompressible
  fluid flow in pipelines versus the Darcy–Weisbach equation and the issue of friction
  factor,” *Journal of Fluid Mechanics*, 891, A5.
  [doi:10.1017/jfm.2020.131](https://doi.org/10.1017/jfm.2020.131).


## Native CoolProp isothermal momentum and independent short-pipe reference

The same `solve_isothermal_compressible_gas_flow()` now accepts
`eos=CoolPropIsothermalEOS("Hydrogen")` for its native real-fluid branch.
The earlier ideal formula describes only the explicit molecular-mass reference
branch. The native branch obtains density and fixed-temperature derivatives
from direct HEOS, uses the same Reynolds/friction root, and reconstructs outlet
pressure through an adaptive steady momentum ODE. Viscosity is an explicit
held value, so Reynolds number and the supplied Darcy factor are constant along
this model's pressure path. This is not a variable-viscosity extension.

For mass flux `G = rho*v`, the native momentum identity is

```text
G^2 [f_D L/D + 2 ln(rho_up/rho_down)] = 2 integral_(P_down)^(P_up) rho(P,T) dP
```

The isothermal singularity uses `c_T^2 = (dP/drho)_T`, rather than the adiabatic
sound speed. Native phase and sonic gates apply at the adaptive pressure-path
stages; rejected states do not fall back to an ideal EOS. The pressure residual
is the reconstructed minus specified downstream pressure in Pa. The integrated
momentum residual has separate units Pa kg/m3. The adaptive gate is a numerical
check, not a mathematical global certificate across arbitrary EOS paths.

A separate reproducible case is
`native-isothermal-real-gas-short-pipe-reference`, with entrypoint
`validation.cases.real_gas_hydraulics:validate_short_pipe_reference`.
It retains the existing long-pipe case and independently solves for mass flux
using density-coordinate integration of the direct native pressure derivative,
then verifies the outlet with a density ODE. It never calls the production
pressure-integral or pressure-ODE functions to construct that reference.

Actual local Python 3.12 / CoolProp 8.0.0 execution passed:

- T=300 K, P_up=70 MPa, P_down=60 MPa, L=0.5 m, D=0.02 m, f_D=0.02,
  viscosity taken from native upstream HEOS and held constant. The friction
  length ratio is 0.5 and the acceleration logarithm is 0.216145566457, so an
  omitted or reversed acceleration term cannot hide inside a much larger
  friction contribution.
- Production mass flow was 10.109942946464903 kg/s; independent flow was
  10.10994294646489 kg/s, relative difference 1.33226762955e-15.
  The independent density-ODE outlet error was 2.98023223877e-8 Pa; production
  reconstructed pressure residual was -2.23517417908e-8 Pa. Maximum observed
  isothermal Mach number was 0.593912202202.
- At the same upstream pressure, 1 Pa and actual 0.00100000202656 Pa drops
  produced 0.00392650330191 and 0.000124167065292 kg/s. Relative differences
  from the constant-friction local native-density small-drop limit were
  1.71423254480e-8 and 1.71420655448e-11; pressure residuals were 0 and
  7.45058059692e-8 Pa. That limit is a test asymptote, not an alternate fluid EOS.
- Direct native derivatives gave critical friction length ratio
  0.0364616794597 for the prescribed endpoints. A ratio of
  0.00911541986493 was rejected as an infeasible sonic branch. Liquid hydrogen
  at 20 K, 1 MPa to 0.9 MPa was rejected. Equal pressures were rejected by the
  positive-direction root contract; zero-flow handling belongs to its caller.

Reproduce only this case with:

```python
from pathlib import Path
from validation.cases.real_gas_hydraulics import validate_short_pipe_reference
outcome = validate_short_pipe_reference(work_directory=Path("."))
```

Executed kernel SHA-256: `123510ccc4f4a103399bf3821e3f152b74d6ce6b1a2d9967d27b97e6e44577ca`.
Executed case SHA-256: `4da6fa2f3f31971ea4cceab862f504503c3ca27cc0954c7c8f6c73f28690a10a`. The independent temporary reference also
checked the kernel hash before/after its calculation and observed no change.
Ruff passed. These results verify numerical momentum consistency against native
HEOS, not measured pipe losses, a friction correlation, real thermal-control
duty, acoustic dynamics, choking flow, or a hydrogen facility.

Primary property API reference:
https://coolprop.org/coolprop/LowLevelAPI.html#partial-derivatives .
