# Mixture state consumer audit — 2026-10-29

Static source inspection only; no model or validation case was executed.

`MixtureThermoState` subclasses `ThermoState` and stores native CoolProp molar
quality separately. Its `vapor_mass_fraction` is intentionally unset, including
on saturation endpoints. An exact-class check therefore rejects it before a
physical applicability check. Replacing every exact-class check with `isinstance`
would not establish composition, phase or energy-reference compatibility.

| Consumer | Existing contract | Recommendation |
|---|---|---|
| `oxygen_deficiency._source_digest` | Exact `ThermoState`, then source/state reconstruction | The digest is generic provenance machinery and could admit a validated subclass. Physical admission still requires the explicit Cantera frozen-gas provider, matching native mechanism, composition, basis and caloric state. A CoolProp HEOS mixture state cannot replace this native Cantera state by changing only a type check. |
| `oxygen_deficiency` source admission | Cantera provider, phase `gas`, mass quality 1 | Preserve this engine/reference gate. CoolProp single-gas states have no mass quality; a separate explicit state projection and evidence would be required. Do not infer compatibility from a gas label. |
| `slabx_lh2.SLABLH2SnapshotCondition` and snapshot bin checks | Exact `ThermoState` | Preserve the existing pure-normal-H2 vapor boundary. The actual source builder additionally requires fluid `Hydrogen`, normal spin and mass quality 1. A mixture state does not satisfy that physical contract; widening the type alone provides no supported capability. |
| `underground_storage` withdrawal projection and receipt | Exact dry-H2 representative state with basis equality to each native dry-H2 sample | Preserve dry-component semantics. Wet cavern mixture and dry hydrogen withdrawal are distinct boundaries. Do not accept a CoolProp mixture as the dry-component state or relabel its property basis. |

## Source digest constructor defect — statically corrected

`oxygen_deficiency._source_digest` now reconstructs `IntervalMassSource` and its
nested dataclasses using only fields with `init=True`, so fingerprint bookkeeping
fields are not passed to constructors. The deferred
`validation/cases/oxygen_source_digest.py` contract exercises that code path on a
finite source and checks for a stable-length digest. Neither this contract nor a
full oxygen-volume scenario was executed in this development turn. Preserve the
source integrity, clock/frame, composition and thermochemical-reference checks.
