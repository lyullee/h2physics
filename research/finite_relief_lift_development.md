# Finite relief lift development record

Date: 2026-10-28. Status: `implemented_unverified`.

## Decision

The checked relief level used a native binary latch and homogeneous bulk tank
withdrawal. Its catalog explicitly left lift, seat leakage and phase-selective
pickup open. This increment does not modify that checked level. It composes a new
accepted-sample travel state with its actual native thresholds and shared nozzle.

The travel law is intentionally small: bounded constant opening and closing rates
plus a declared residual effective-area fraction. This is materially different
from binary actuation but does not claim vendor mechanics. More detailed disk
dynamics should be another justified model level, not hidden coefficients here.

Phase selection remains an injected owner because a homogeneous bulk tank cannot
prove a vapor or liquid pickup. Exact native object identity, phase identity,
selectable mass, pressure and property basis are retained in every result.

## Deferred evidence

Six Nurion cases are defined:

1. finite opening and closing travel with native set/reseat hysteresis;
2. nonzero declared seat leakage and zero-lift effective area;
3. distinct explicit vapor/liquid pickup admission and wrong-phase rejection;
4. finite selectable inventory rejection without flow clipping;
5. clock support and accepted-sample crossing limitations;
6. original-result/native-owner mutation and copy rejection.

They are definitions, not passes. No module import, example, nozzle solve, native
model, test, benchmark or case discovery was executed during this coding wave.
Static AST/Ruff/diff review is the only local evidence.

## Remaining work

- execute the new cases and the original relief/tank/nozzle regressions on Nurion;
- compare against source-qualified lift, leakage and discharge measurements;
- add event localization only with a native tank integrator that exposes safe
  dense output or bracketed accepted states;
- qualify a phase-resolved tank port before claiming cryogenic vapor/liquid duty;
- keep sizing, certification, chatter and structural mechanics separate.
