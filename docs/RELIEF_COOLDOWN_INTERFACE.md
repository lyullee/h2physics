# Relief to line cooldown interface

`bind_relief_to_line_cooldown()` connects two already computed native histories: a `ReliefTankTrace` and a `DynamicLineCooldownAudit`. Both must identify the same clock, and the requested interface times must fit within both records.

The caller supplies cumulative mass and enthalpy at the line inlet on the interface time grid, plus a boundary identifier, evidence identifiers, and absolute closure tolerances. Both ends now require a `ReliefCooldownPort` carrying port ID, native `PropertyBasis`, phase, absolute-pressure convention and evidence ID. Port phases and property/spin/energy-reference bases must match; the relief port must match its native provider basis, and the line port must match the cooldown inventory basis. A single receipt represents one declared phase over its window; split the receipt at any evidenced phase change. The requested times must be retained relief samples; interpolation across valve-event transitions is refused. Receipt construction independently checks that its release totals match those native samples, the line mass history is nonnegative and nondecreasing, and both tolerance values are finite and nonnegative. `require_current()` rechecks the native traces, typed ports and boundary histories.

The receipt also fingerprints its admitted evidence IDs, port identities, caller
boundary histories and closure tolerances. Post-bind relabeling or tolerance
relaxation is rejected rather than treated as a newly admitted interface; create a
new receipt when those declarations legitimately change. The deferred contract
includes mutation/restore coverage for these fields. Evidence IDs must be supplied
as a sequence of complete IDs; a string cannot be mistaken for a sequence of
single-character identities.

This interface does not run or couple either solver, infer pipe routing, or transform thermodynamic states. Port phase and basis remain caller attestations, checked for consistency against the relief provider and cooldown inventory but not independently inferred from a coupled line state. Passing this receipt establishes only that the supplied totals close within the caller's declared tolerances; it does not establish that relief flow caused the line cooldown. Event jumps still need a native event-resolved source representation before the receipt can support a complete operational scenario.

`bind_relief_cooldown_sequence()` composes multiple phase-specific receipts when
the caller has segmented a known phase transition. Every segment must retain the
same original relief and cooldown traces, boundary and port identities/bases.
Adjacent windows must meet at the same retained event-time sample, and cumulative
mass and enthalpy totals must be continuous across that boundary. The combined
time view removes only the repeated shared endpoint. This groups admitted
accounting intervals; port phase remains caller-qualified and it does not infer
or model the transition.

The registered contracts are in `validation/cases/relief_cooldown_interface.py` and remain deferred for the later Nurion batch.
