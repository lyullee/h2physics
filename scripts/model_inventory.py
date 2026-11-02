"""Generate a coverage view from the single Python ownership catalog."""

from collections import Counter
from pathlib import Path

from h2physics.catalog import model_catalog

root = Path(__file__).resolve().parents[1]
models = model_catalog()
assert len({x.identifier for x in models}) == len(models)
counts = Counter(model.status for model in models)
implementation_classified = counts["implemented"] + counts["native_adapter_verified"]
lines = ["# Model coverage and ownership", "",
         f"Current catalog: {len(models)} families; "
         f"{counts['implemented']} implemented, "
         f"{counts['native_adapter_verified']} native-adapter-verified, "
         f"{counts['implemented_unverified']} implemented-unverified and "
         f"{counts['planned']} planned.",
         "These are implementation-status labels, not a measure of scientific or facility qualification.",
         f"Implementation-classified families: {implementation_classified}/{len(models)} ({implementation_classified/len(models):.0%}); this is a catalog-status ratio, not overall project completion.",
         "ModelSpec restricts status values and hierarchy identifiers; catalog filtering validates selectors and rejects duplicate family identities.",
         "Last accepted execution coverage is maintained separately in PROGRESS.md and the pinned HPC evidence records; deferred case counts are plans, not execution evidence.", "",
         "Each row is a consolidated physical family or a distinct fidelity/transport boundary.",
         "Ownership identifies reuse candidates, not a completed adapter or transferred validation.",
         "Implemented rows still require their stated verification and validation evidence.", "",
         "A partial executable level does not complete every model level within the family.", "",
         "| Identifier | Physical purpose / implemented level | Owner or candidate | Status | Remaining evidence or scope |",
         "|---|---|---|---|---|"]
lines += [f"| `{x.identifier}` | {x.purpose} | {x.owner} | {x.status} | {x.evidence_needed} |" for x in models]
(root / "docs/MODEL_CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{len(models)} model families; "
      f"{sum(x.status == 'implemented' for x in models)} implemented")
