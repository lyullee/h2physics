# Finite hydride discharge to the shared release nozzle

`nozzle_history_from_hydride_trace()` connects the current output states of an
open-port `FiniteHydrideTrace` to the existing `HomogeneousIsentropicNozzle`.
It requires the original gas-port boundary, outward-only net port mass in every
reported interval, compatible hydride/nozzle property bases, and caller-owned
source location, outlet opening, back pressure, origin and handoff evidence.

The nozzle flow is not assumed to equal the bed's external port flow. The
caller must select a sample-grid quadrature (`left_hold`, `right_hold`, or
`trapezoid`), declare an evidence-backed relative/absolute mass tolerance, and
identify its basis. The adapter integrates every nozzle interval and compares it
against the corresponding accepted bed-port mass; any mismatch is rejected. It
does not rescale either model or overwrite either ledger. For a conservative
coupling, use the same nozzle relation to define the bed's gas-port callback,
then check the accepted output-grid closure with a justified quadrature budget.

The nozzle is evaluated at each exact retained gas state; its `SourceHistory`
keeps those state-dependent results on the bed's absolute clock. A
`HydrideNozzleSource` receipt binds that history to the original storage trace
and detects edits to trace snapshots, integrated port ledgers, and the retained
native integration output and mass-closure audit. The source history can then be projected to the
existing `IntervalMassSource` or used by release/dispersion consumers under
their own rules.

This boundary adds no valve/pressure-flow law to the bed. It does not infer a
source orientation or location, change the hydride property basis, or calculate
atmospheric dispersion. The deferred Hangang case
`finite-hydride-nozzle-source-handoff` uses the existing CoolProp hydrogen
property interface and shared nozzle; no separate provider package is added.
