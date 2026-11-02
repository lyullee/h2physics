# Flowing heat-exchanger development record

Date: 2026-10-28. Status: implemented_unverified.

The existing finite exchanger intentionally has no material ports. This
increment does not weaken that boundary or alter the native integration. It
admits two separately produced `ConnectionTransfer` records and binds them to a
single original finite trace point as a hold-up/capacity witness.

Original design decisions:

- inlet/outlet enthalpy and signed flow remain owned by existing equipment
  transfer objects;
- pressure loss is caller supplied, source identified and checked against the
  original states;
- no shaft work is admitted at this heat-exchanger level;
- side heat duties must each close their transfer and must close together with
  an explicit external heat boundary;
- the closed native trace is never reinterpreted as an open-flow derivative;
- original trace, point, native state and transfer identities are sealed.

Six deferred cases cover balanced two-side duties, external heat, pressure-loss
guards, finite witness identity, stale results and explicit rejection of a
flowing-storage claim. They have not been imported, discovered or executed.
