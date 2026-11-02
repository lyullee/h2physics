# Isothermal single-phase EOS closure

`h2physics.thermo.isothermal_eos` defines the `IsothermalSinglePhaseEOS`
protocol and a lazy `CoolPropIsothermalEOS` implementation. It supplies three
mass-basis operations in SI units:

- `density_pt(p_pa, t_k)`
- `pressure_rho_t(rho_kg_m3, t_k)`
- `isothermal_sound_speed_rho_t(rho_kg_m3, t_k)`

The final quantity is the isothermal characteristic speed
`c_T = sqrt((∂p/∂ρ)_T) = sqrt(1 / (ρ κ_T))`. CoolProp defines its
`AbstractState.isothermal_compressibility()` as
`κ_T = (1/ρ)(∂ρ/∂p)_T` in inverse pascals. The provider derives `c_T` from
that derivative and does not use `speed_sound()`, which describes the distinct
isentropic derivative. The CoolProp API reference documents the derivative and
phase methods; see the [AbstractState reference](https://coolprop.org/_static/doxygen/html/class_cool_prop_1_1_abstract_state.html)
and [high-level phase behavior](https://coolprop.org/coolprop/HighLevelAPI.html).

Construction imports CoolProp only when requested and currently admits direct
`HEOS`. Every query checks that its returned state is classified as gas or
supercritical gas/fluid; liquid, saturation, two-phase and unknown states are
rejected. The mutable CoolProp state is protected by a reentrant lock. The
provider makes no assertion about phase-domain accuracy beyond CoolProp's own
EOS. Callers remain responsible for checking fluid identity and operating
envelope against their application.

For an immutable fixed-composition blend, `CoolPropMixtureIsothermalEOS`
adapts `CoolPropMixtureProperties` to this protocol. The mixture provider now
supports the mass-basis `state_rho_t` input pair and computes isothermal
characteristic speed from the native mixture compressibility. The adapter
retains the mixture composition fingerprint and rejects phase states outside
homogeneous gas/supercritical conditions. HEOS interaction parameters remain
those of the installed CoolProp release. This does not evolve species or spin
composition. Deferred case `coolprop-isothermal-mixture-linepack` exercises
the provider through the linepack consumer; it is not measured blend-pipeline
validation.

This closure is intended for pressure-wave or gas-characteristic equations
whose thermal path is explicitly isothermal. It is not a real-gas energy
equation, a two-phase closure or a replacement for adiabatic sound speed in
isentropic nozzle calculations. The plant-side finite-volume wave adapter uses
this Protocol to keep EOS selection replaceable. Runtime comparisons against
CoolProp state derivatives and the wave solver are deferred to Hangang.

Isothermal EOS source check: the current CoolProp 8.0.0 AbstractState reference
exposes `isothermal_compressibility()` in inverse pascals with definition
`kappa_T=(1/rho)(partial rho/partial p)_T`; the provider derives the reciprocal
pressure-density derivative for `c_T`. It does not use `speed_sound()`.

## Deferred provider-specific contract

`validation/cases/coolprop_isothermal_eos.py` registers
`coolprop-isothermal-single-phase-eos` under the Hangang `isothermal-eos`
profile. It checks pressure/density round trips, compares `c_T^2` with a
centered fixed-temperature finite difference of pressure with respect to density,
and checks liquid, unresolved-mixture, backend and invalid-input rejection.
It is registered and unrun. Passing this provider case would not verify the
finite-volume wave solver or validate hydrogen pipeline measurements.
