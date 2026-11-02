# Accepted-edge relief withdrawal ledger

`h2physics.adapters.relief_withdrawal_ledger` composes two adjacent
`ReliefLiftResult` objects into an explicit finite phase withdrawal receipt. It
reuses the existing tank phase selector, native relief identity and shared
nozzle results. It does not add another flow calculation or alter the relief
latch.

## API contract

Call `integrate_relief_withdrawal_edge(owner, left, right, *,
other_phase_inventory_change_kg, evidence_id)` with two original results issued
by the same `FiniteLiftRelief` owner. Their times must form one contiguous edge,
the clock and physical source identity must match, and the selected phase and
pickup rule must remain the same across the edge. The initial and final phase
stocks are supplied by the existing pickup owner through those results.

Mass and transported enthalpy use a linear interpolation of endpoint rates:

`integral(rate, t0, t1) = 0.5 * (rate0 + rate1) * (t1 - t0)`.

The caller supplies signed net additions to that phase from all other processes
over the same edge. The receipt checks `stock_after = stock_before + other_change
- relief_withdrawal` within the declared tolerance. Enthalpy can be signed
because its zero is reference-dependent. A change in the accepted set/reseat
demand requires an edge split; the trapezoid does not span that discontinuity.

## Limits and evidence

This is accepted-edge trapezoidal accounting, not native solver quadrature, a
continuous depletion event locator, a vessel integrator, or a guarantee that
inventory stayed nonnegative between samples. The caller must choose a clock
resolution adequate for the source dynamics and provide phase-stock boundary
evidence. A phase change inside an edge is rejected rather than blended. The
contract requires independent verification against the receiving tank's native
inventory and native nozzle/relief suites before use for safety conclusions.

The implementation is original project code. It contains no copied vendor
tables, figures, or prose.
