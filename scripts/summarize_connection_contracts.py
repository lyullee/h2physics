"""Summarize genuine producer/consumer handoff receipts and topic coverage."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree


def summarize(paths, scope_file):
    admitted = set(json.loads(scope_file.read_text(encoding="utf-8"))["families"])
    cases, seen = [], set()
    for path in paths:
        for test in ElementTree.parse(path).getroot().iter("testcase"):
            props = {p.attrib["name"]: p.attrib.get("value", "")
                     for p in test.findall("./properties/property")}
            if props.get("actual_scope_kind"):
                props["declared_scope_kind"] = props.get("scope_kind")
                props["scope_kind"] = props["actual_scope_kind"]
            required = ("family", "connection_scenario", "connection_target",
                        "producer", "consumer", "scope_kind")
            if any(not props.get(key) for key in required):
                raise ValueError(f"Missing connection evidence: {path}: {test.attrib}")
            families = {props["family"]}
            families.update(value.strip() for value in props.get("connected_families", "").split(",")
                            if value.strip())
            if families - admitted:
                raise ValueError(f"Unknown topic families: {families - admitted}")
            key = (test.attrib.get("classname"), test.attrib["name"])
            if key in seen:
                raise ValueError(f"Duplicate case receipt: {key}")
            seen.add(key)
            status = next((kind for kind in ("failure", "error", "skipped")
                           if test.find(kind) is not None), "passed")
            cases.append({**props, "families": sorted(families), "status": status,
                          "case": test.attrib["name"], "xml": str(path),
                          "seconds": float(test.attrib.get("time", 0.))})
    passed = {family for case in cases if case["status"] == "passed" for family in case["families"]}
    positive_scopes = {"actual_host_handoff", "actual_producer_consumer_contract",
                       "genuine_computed_handoff"}
    rejection_scopes = {"genuine_rejected_connection_gate"}
    unknown = {c["scope_kind"] for c in cases} - positive_scopes - rejection_scopes
    if unknown:
        raise ValueError(f"Unclassified connection scopes: {unknown}")
    if any(c.get("connection_acceptance") == "False" and c["scope_kind"] in positive_scopes
           for c in cases):
        raise ValueError("A rejected receiving path cannot be counted as a positive handoff")
    positive_cases = [c for c in cases if c["status"] == "passed"
                      and c["scope_kind"] in positive_scopes]
    positive_families = {family for case in positive_cases for family in case["families"]}
    return {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "scope": "Named host module connections; native internal physics and plant qualification excluded",
        "admitted_families": len(admitted), "case_count": len(cases),
        "passed_cases": sum(c["status"] == "passed" for c in cases),
        "failed_cases": sum(c["status"] in ("failure", "error") for c in cases),
        "skipped_cases": sum(c["status"] == "skipped" for c in cases),
        "families_with_passes": len(passed), "families_without_passes": sorted(admitted - passed),
        "positive_case_count": len(positive_cases),
        "positive_family_count": len(positive_families),
        "positive_families": sorted(positive_families),
        "boundary_only_families": sorted(passed - positive_families),
        "rejected_gate_case_count": sum(c["status"] == "passed"
                                       and c["scope_kind"] in rejection_scopes for c in cases),
        "passed_edges": sorted({(c["producer"], c["consumer"], c["connection_target"])
                                for c in positive_cases}),
        "evidence_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "test_source_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path("tests").glob("test_connection_contract_*.py"))},
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", nargs="+", type=Path)
    parser.add_argument("--scope", type=Path,
                        default=Path("artifacts/input-contracts-20261102/coverage-78.json"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.xml, args.scope)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({k: result[k] for k in
                      ("case_count", "passed_cases", "failed_cases", "families_with_passes")}))
