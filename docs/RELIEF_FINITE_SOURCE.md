# Finite relief withdrawal source handoff

`relief_source_from_accepted_withdrawals()` projects an existing `FiniteLiftRelief` accepted-sample sequence into the shared `IntervalMassSource` API. Every interval must have an original adjacent endpoint pair and a matching `ReliefWithdrawalReceipt` from `integrate_relief_withdrawal_edge()`. The receipt is accepted only when its trapezoidal mass and enthalpy integrals close against the caller-declared phase inventory change.

The bridge preserves exact edge times, interval masses, source clock, location/frame, outlet `PropertyBasis`, phase, source owner, native relief identity, and the original accepted receipts. The common source type permits one representative `ThermoState`; the caller must explain that projection and its enthalpy must reproduce the total accepted withdrawal enthalpy within the explicit joule tolerance. It will reject a mismatch instead of adding an enthalpy offset.

```python
from h2physics.adapters import (
    integrate_relief_withdrawal_edge,
    relief_source_from_accepted_withdrawals,
)

edge = integrate_relief_withdrawal_edge(
    relief_owner, left, right,
    other_phase_inventory_change_kg=declared_phase_change_kg,
    evidence_id="phase-balance-evidence",
)
handoff = relief_source_from_accepted_withdrawals(
    relief_owner, (left, right), (edge,),
    location=source_location,
    representative_state=outlet_state,
    origin=origin,
    projection_evidence_id="why-one-state-represents-this-window",
    enthalpy_tolerance_j=declared_energy_tolerance_j,
)
finite_source = handoff.require_current().source
```

This is a reporting/typing boundary only. It does not predict relief flow, locate unobserved threshold crossings, perform blowdown, calculate flashing, transform enthalpy references, or model atmospheric dispersion/fire. The downstream dispersion choice remains model-specific: high-pressure gas uses HyRAM and liquid-hydrogen vapor clouds use SLABx-LH2 under their respective native admission contracts. The bridge does not make a liquid stream admissible to a gas dispersion solver.

Deferred Hangang contract: `relief-withdrawal-finite-source-handoff` under the existing `finite-relief-lift` profile. This case is planned, not execution evidence.
