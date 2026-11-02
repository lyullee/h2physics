# Bounded two-phase mixture V/U flash

`h2physics.thermo.flash_two_phase_inventory_vu()` resolves one fixed-composition
equilibrium state from species inventories, rigid vessel volume and total fluid
internal energy. It uses the existing `CoolPropMixtureProperties` provider and its
native PQ flash packets. It does not implement a second EOS, transport rule, vessel
ODE, or phase-event locator.

## State equations

For the declared component mole vector `N_i`, the provider composition must match
`N_i / sum(N_i)` within the supplied absolute component-mole budget. At a trial
pressure `P` and vapor mole quality `beta`, the native PQ packet supplies both
phase compositions and properties. Existing `MixturePhaseAmounts` converts that
packet and the total moles into phase component masses. The flash balances are:

```text
Vcalc(P, beta) = sum_j m_j(P, beta) / rho_j(P, beta)
Ucalc(P, beta) = sum_j m_j(P, beta) * [h_j(P, beta) - P / rho_j(P, beta)]
rV = Vcalc - Vtarget
rU = Ucalc - Utarget
```

Occupied phases require native density and enthalpy; absent endpoint phases
contribute zero. The solver scales `rV` and `rU` by caller tolerances and searches
in `(log(P), beta)` with SciPy's bounded trust-region least-squares routine. Each
candidate uses the exact native phase partition, then
`MixtureInventoryStateAdmission` independently checks component moles, total phase
volume and total phase internal energy against the original targets.

## Branch and failure handling

Callers must provide pressure/quality bounds, at least two distinct interior seeds,
branch-selection evidence and positive absolute closure tolerances. All seeds must
converge within their bounds and close both balances. The solver rejects the result
if any seed fails, if different seeds find distinct roots, if the final native phase
packet is not two-phase, if the provider composition does not match the inventory,
or if component/volume/energy closure exceeds its limit. The error retains one
diagnostic result per attempted seed.

`seed_unique_within_search` reports only that the caller-supplied starts converged
to the same clustered root. It does not prove global uniqueness or full branch
monotonicity. A user must choose the physical bounds from applicable phase and
apparatus evidence. No root is extrapolated outside those bounds, and a single-phase
state is not silently returned as a VLE result.

## Use boundary

This is a **single-state thermodynamic resolver**. For a changing component
inventory, construct a matching immutable `GasComposition` and native provider for
each queried inventory state; do not reuse a provider whose fractions differ from
the current `N_i`. This helper does not provide the time-dependent provider factory
or accepted-state integration. It does not apply inlets/outlets, heat, work, finite
wall storage, event handling or solver failure-prefix semantics. Request032 still
requires the owning native engine to couple evolving component moles and energy,
flash each state, apply phase-specific ports and retain accepted steps and events.

## Deferred cluster contract

`validation/cases/mixture_inventory_flash.py` builds a target from one native PQ
packet and asks the bounded V/U resolver to recover it from multiple starts. It
checks the native phase identity, pressure/quality root, independent component,
volume and energy closure, result currentness, provider-composition rejection and
seed-count requirement. It is registered in the existing `gas-composition` Nurion
profile and has not been executed. This authored round-trip is numerical/API
verification only; it does not validate a real separator mixture or close Request032.

## References

- [CoolProp mixture thermodynamic model and supported flashes](https://coolprop.org/fluid_properties/Mixtures.html)
- [CoolProp low-level `AbstractState` interface](https://coolprop.org/apidoc/CoolProp.AbstractState.html)
- [SciPy `least_squares` bounded solver API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
