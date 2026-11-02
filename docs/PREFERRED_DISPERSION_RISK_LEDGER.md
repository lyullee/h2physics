# Preferred gas dispersion to ignition-risk ledger

`h2physics.adapters.preferred_dispersion_risk_ledger` adds a lineage check
between an accepted high-pressure-gas `FacilityDispersionHandoff` and the
the structural `IgnitionRiskBinding` interface implemented by the native
`HyRAMIgnitionRiskBinding`. It does not call HyRAM, evaluate dispersion,
construct risk branches, or calculate frequency, harm, or risk.

The link requires the exact admitted HyRAM finite-source projection, exact
native jet retained by the preferred dispersion execution, an accepted risk
branch binding, and a HyRAM ignition-table release rate whose interval mass
matches every finite source bin within the facility handoff's retained mass
budget. It preserves the caller's original frequency object and both source and
table/provider lineage. Source origin and ignition-table origin remain separate
fields; matching origins are not inferred.

These checks establish accepted projection/jet identity and release-rate
consistency only. They do not prove that the ignition-risk binding refers to the
same event, time interval, receptor, or scenario as the dispersion handoff. The
caller owns and must supply evidence for that association.

This is limited to the user's preferred HyRAM high-pressure-gas route. It does
not link SLABx-LH2 vapor snapshots: a gas ignition-rate table alone does not
establish liquid-origin cloud ignition applicability. Nor does the ledger
assert that its ignition probabilities were calculated from the retained
dispersion field. They remain release-rate table probabilities and require
their own applicability evidence. A receptor-specific harm result, exposure,
annual frequency, safety credit or facility qualification is not created.

The synthetic Hangang contract builds an accepted mock-provider source/jet
handoff and uses a caller-owned structural risk-binding fixture. It does not
import or exercise `process-risk-consequence-toolkit`, construct native risk
branches, or calculate a risk metric. Production callers should pass the
original typed `HyRAMIgnitionRiskBinding`. Native provider execution and
scientific validation remain deferred.
