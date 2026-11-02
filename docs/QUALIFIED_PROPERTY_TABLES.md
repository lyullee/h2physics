# Qualified CoolProp gas tables

`GasEnvelope` is the admitted pressure-temperature domain for
`QualifiedGasTable`. Its `require_pt()` method accepts the closed bounds and
rejects nonfinite, boolean, zero, or negative state inputs before checking the
declared interval. This keeps direct envelope queries consistent with the
positive-pressure and positive-temperature contract of the CoolProp provider.

The guard is input validation only. It does not query an EOS, admit a phase, or
qualify interpolation accuracy. Table qualification and physical validation
remain separate requirements; see the deferred contract in
`validation/cases/thermo_tables.py`.

`TableQualification` is an issued receipt rather than a caller-constructible
claim. Only `QualifiedGasTable` can issue a report after running the reference
and table comparisons; direct construction and `dataclasses.replace()` cloning
are rejected. The deferred table case retains these issuance checks.

Each report query also rechecks the issued numeric summary and the four original
gas-envelope bounds. This detects post-issuance edits to the report or its nested
envelope before returning an error gate, pass flag or measured-speedup decision.
The existing deferred table case covers both direct report mutation and nested
envelope mutation; it has not been executed.
