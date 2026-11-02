# Shared converged Darcy closure and explicit friction-law contract

Status: original common kernel, native-result adapter and retained negative point available;
request prepared, not sent. Target MIT LH2DT 0.1.2 revision
`b2f276333c1b1793c39f25763703d196d36742ec`.

## Reproduced boundary failure

The native pipe methods iterate a friction estimate a fixed maximum of 30 times. A result
can report zero momentum residual using the previous loss coefficient, while its final
friction coefficient and returned velocity do not satisfy the same Darcy equation.

A retained authored-model state has left P/rho=820206.1092360109 Pa / 71.97923609619494
kg/m3 and right P/rho=819947.6847660368 Pa / 27.69354626133448 kg/m3, HEOS ParaHydrogen.
For L=1 m, D=0.001 m, roughness=1e-6 m, K=0 and dz=0, the native output has Re about
2296.116 and reported residual 0 Pa. Recomputing loss from its actual mass flow, upstream
density and reported friction gives about 44.3086 Pa residual.

The native friction law also changes abruptly at Re=2300. Bracketing that same law does
not create a root inside its pressure-loss gap: the retained point has about 43.9464 Pa
residual despite a scalar-root convergence flag. The host explicitly rejects it.

## Implemented host boundary

`h2physics.hydraulics.solve_darcy_flow` is one bracketed magnitude solver with an injected
Darcy friction law and explicit pressure residual gate. `Lh2dtDarcyPipe` retains native
geometry, the caller's viscosity reader, live heat/elevation parameters and actual native
PipeResult factory. Direction uses total pressure including hydrostatics. No phase viscosity
or thermal storage model is invented. Native HEM viscosity remains the checked closure.

The full supply case explicitly selects the separately installed MIT fluids 1.3.1 direct
`Churchill_1977` Darcy function. This is an empirical correlation change as well as a
numerical correction; no improved experimental two-phase accuracy is claimed. The retained
point then closes near machine precision. The library source is not copied. The native
correlation is retained only as a declared regression/comparison choice, never as fallback.

## Requested receiving behavior

1. Expose a public friction-law callable and public single-phase/HEM viscosity capability.
   Preserve correlation identity, applicable domain and Darcy/Fanning convention. Keep the
   current native piecewise law explicitly selectable for historical comparisons.
2. Delegate both Pipe and HEMPipe to one pressure-loss magnitude solver; only viscosity/
   state closures should differ. A typed optional `flow_solver` callback can delegate the
   existing host kernel and avoids another equivalent implementation.
3. Check final friction/flow/geometry loss consistency, not only a reused intermediate
   coefficient. Expose iterations, convergence and a recomputed momentum residual. A
   discontinuous-law gap must fail rather than becoming a closed point.
4. Preserve actual native result/state types, signed upstream ownership, heat, hydrostatics
   and missing diagnostics. A stagnant prescribed-heat component needs explicit storage;
   do not hide heat by setting a small flow or silently dropping it.
5. Keep correlation/model selection explicit before solving. No native failure should
   change friction, phase, EOS or operating mode. Preserve the independent inventory checks.

## Acceptance and reproduction

Run `scripts/check_finite_supply.py`; the retained point and whole short/long assembly
records are in `research/native_finite_supply.md`. HYDRAULICS.md explains the independent
Poiseuille limit, analytic fixed-friction relation, discontinuous-law rejection, direct
library convention, reverse heat transport and pressure-loss gates. Longer heating reverses
internal flow and crosses the transition region. Check conservation, time refinement and
constitutive loss independently; passing one does not establish the others.
