# Native derived frequency and credited protection contract

Status: actionable receiving-extension request.

Targets: PRISM and the PHA host. Keep consequence physics independent from frequency estimation.

## Observed integration boundary

The reviewed PHA worker imports `lh2_tno.derived_frequency` and `derived_campaign`.
The reviewed public PRISM tree does not include those modules. The PHA project retains
a reproduction patch implementing the extension. Establish an explicitly released compatible
receiving version rather than treating an arbitrary PRISM checkout as equivalent.

## Required native event meaning

- A scenario/component/port identifier and an unambiguous event definition.
- Initiating or LOC frequency in inverse years, with its evidence/denominator.
- Conditional probabilities already applied, including their barrier and transition identities.
- Ignition, occupancy and weather credits that remain downstream.
- Mutually exclusive branch identities and probabilities with a complete partition check.
- Source, calculation and baseline identities; no annual-frequency inference from an anomaly score.

The existing `DerivedFrequencyEvent`, `bind_derived_event` and campaign extension are the
receiving work's starting point. Preserve the native Python call surface; serialization
can remain an optional application concern.

## Acceptance cases

1. Run the PHA example against the exact released PRISM revision without local source patching.
2. Reject duplicate barrier credit and an outcome rate that already contains downstream ignition
   when the receiver expects pre-ignition LOC frequency.
3. Preserve repeated-event dependence and exclusive branch sums.
4. Keep a selected-event contribution separate from an assertion of exhaustive facility risk.
5. Test native objects and real consequence invocation separately from synthetic interface cases.
