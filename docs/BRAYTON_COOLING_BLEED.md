# Single-point Brayton compressor cooling bleed

`h2physics.combustion.run_cooled_brayton_point()` composes the existing Cantera
open-Brayton reference with the existing compressor and turbine map interpolation.
It resolves one explicit compressor-discharge air bleed that bypasses combustion
and mixes once at the turbine inlet.

## Inputs and balance

`CoolingBleedInputs` retains actual inlet-air and hydrogen mass rates, compressor
and turbine corrected speeds, component maps, actual-to-corrected-flow factors,
the numerical corrected-speed link, bleed fraction, cooling-path pressure drop,
shaft loss and target, and evidence IDs for each caller-owned convention.
Corrected flow must lie on the supplied map points. The bleed fraction is bounded
to `[0, 1)` and the declared cooling-path pressure drop must terminate at the
compressor-outlet pressure after the same pressure recovery used at the combustor
outlet. If those pressure stations do not match, the case is rejected.

The remaining primary air and the explicitly supplied hydrogen rate are passed
to `run_open_cycle_brayton()` with a fuel-to-primary-air ratio. The compressor
outlet state comes from that same native Cantera run. A fresh Cantera phase mixes
the combustor stream and bled compressor air at the turbine inlet using total
mass, species mass fractions and specific enthalpy. Cantera then evaluates the
frozen-composition isentropic expansion; the selected turbine map efficiency sets
actual exhaust enthalpy. Compressor power uses total inlet-air flow. Turbine power
uses primary air, hydrogen and the bleed stream, which must sum to total air plus
fuel. The result retains mass-map residuals, mixer energy residual, elemental
mass residuals and the explicit shaft residual.

Before returning a balance field, `CoolingBleedBraytonRun.require_current()`
rechecks the compressor and turbine map points against their source maps and
original corrected coordinates, then rechecks the native cycle and composed
result. `TurbineMapPoint.require_current()` validates its retained component
map by re-interpolation without running a cycle.

## Scope limits

This is a station-level single-injection boundary. For discrete caller-specified
stage expansion and injection accounting, see
[staged turbine cooling](BRAYTON_STAGED_TURBINE_COOLING.md). Neither module solves
blade-film heat transfer, internal passages, local aerodynamic flow, nozzle
capacity, pressure-loss prediction, off-design control or a qualified machine.
The caller owns map correction conventions, speed linkage, cooling split,
pressure drop, shaft loss and target. Synthetic deferred cases do not validate a
real gas turbine.
