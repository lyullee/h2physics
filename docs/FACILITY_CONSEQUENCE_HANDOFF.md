# Caller-owned facility consequence handoff

`h2physics.adapters.facility_consequence.evaluate_facility_consequence` is a
typed connection from an admitted `FacilityDispersionHandoff` to an existing
caller-owned consequence model. The evaluator receives the original handoff,
which retains the finite operation/source, selected HyRAM or SLABx-LH2 execution,
and native provider result. No field is copied through JSON or reconstructed by
the host. `FacilityDispersionHandoff.require_current()` rechecks the original finite
source and its energy projection, then validates the exact accepted provider
execution. That execution is issued only by `DispersionScenario.run()`, so a caller
cannot fabricate an accepted provider wrapper around a matching-looking object.
For high-pressure gas, the retained `HyRAMFiniteSourceProjection` must itself be
accepted by its mass/enthalpy gate; a looser facility-level comparison budget cannot
promote a diagnostic projection that failed that gate.
`assemble_facility_accident_chain()` requires the gas-only projection callback on the
high-pressure path and rejects a non-`None` callback on the LH2-origin path before
the finite operation is invoked. This prevents a gas source projection from being
silently supplied to the liquid-origin branch.
This is process-local provenance and mutation protection; it does not validate the
provider's physics or replace Request012's unresolved native source conservation.

The receiver returns its own result object. That result must expose
`facility_handoff` pointing to the exact input handoff and implement
`require_current()`. The receipt calls the handoff integrity guard before and
after receiver execution and retains the receiver result and method/applicability
evidence identity. Failures retain the original cause and are staged as
`pre_evaluation_integrity`, `evaluator`, `post_evaluation_integrity`, or
`invalid_result`.
The evaluator's Python code and ordinary captured configuration (including
bound-object state and partial arguments) are checked before and after execution.
If that configuration changes while the result is being produced, receipt issuance
is rejected; a later change also invalidates the receipt. Opaque external resources
and global state remain the caller's evidence responsibility.

This boundary does not inspect plume data or calculate concentration thresholds,
flammability, ignition, thermal dose, overpressure, injury, risk or protection
credit. The receiving model owns those choices, units, transformations, source
evidence and validity checks. The deferred contract
`facility-accident-chain-source-prefix` includes an authored handoff check and a
callback-mutation rejection during evaluation and after receipt issuance. It is not
an executed physical validation.
