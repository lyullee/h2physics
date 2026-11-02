# Finite LH2 separator to HELPR vessel history

`history_from_finite_separator()` maps an owner-issued
`FiniteSeparatorTrace` to the existing `VesselFailureHistory` contract. At each
accepted time, it uses the shared absolute pressure retained by the native
liquid and vapor state rows, after confirming their property basis and pressure
agree. It retains the original separator point, native state, fluid state and
trace owner for freshness checks while HELPR consumes the history.

The caller supplies one shell-wall temperature and one external absolute
pressure for every original accepted sample. The liquid/vapor temperatures are
fluid values; they are never treated as a vessel wall temperature. The caller
also names the shell, exact absolute-pressure basis, geometry mapping,
pressure mapping and external-pressure evidence. The clock and H2 property
basis must match the HELPR context. No pressure interpolation/conversion,
wall heat-transfer model, mechanical failure criterion, breach, or release
model is added.

Deferred Hangang case: `finite-separator-vessel-failure-history-handoff`
under `finite-transfer`. It checks synthetic history construction and replay
only; it does not run HELPR or qualify vessel performance.
