# Model-selection development record

Date: 2026-10-28. Status: `implemented_unverified` infrastructure; no new
physical family or solver.

The consolidated catalog previously documented ownership and status, while
provider choice was domain-specific. The new caller-owned registry adds one
source-neutral selection contract without importing optional packages or
changing domain adapters. Exact family, model level and provider identity are
required. Status, capabilities and evidence are separate explicit gates.

No provider ranking, fallback, dependency installation, entry-point discovery,
configuration serialization or global registry was introduced. A provider
factory is called only through `ModelSelection.build`; failures propagate from
that factory without retry. Callable identity is checked before and after the
call. The resulting `BuiltModel` proves only the selected factory relationship,
not scientific acceptance of the returned model.

The five validation definitions are metadata until a later Nurion campaign.
AST/Ruff/whitespace review is the only intended local evidence for this coding
increment. No registry example, case, factory or optional model is executed.
