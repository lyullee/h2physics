# Pump-operation development record

Date: 2026-10-28. Status: implemented_unverified.

The repository already composes the original LH2DT mapped pump into steady and
finite supply networks and retains its mass flow, pressure residual, shaft power,
NPSH fields and physical-validity flag. This increment does not reproduce that
solver. It adds a finite speed schedule and compares original results with a
caller-owned normalized evidence curve.

The map carries source URI, license, file checksum, fluid/pressure/flow bases and
an explicit prediction-qualification flag. Curve support is bounded and never
extrapolated. A zero-speed point is rejected instead of pretending that a running
pump becomes a closed valve. NPSH admission reads the native available/required
values; no bubble dynamics or cavitation correction is inferred.

Seven deferred cases cover finite asymmetric ramping, normalized map agreement,
capacity rejection, insufficient NPSH, unqualified evidence, exact schedule
boundaries and stale native/result ownership. No module import, model, example,
case or test was executed. AST, Ruff and whitespace checks are static only.
