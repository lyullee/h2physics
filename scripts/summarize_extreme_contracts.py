"""Reconcile actual extreme-case receipts against the existing 78-topic scope."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree


def summarize(paths, scope_file):
    admitted = set(json.loads(scope_file.read_text(encoding="utf-8"))["families"])
    cases = []
    seen = set()
    for path in paths:
        for test in ElementTree.parse(path).getroot().iter("testcase"):
            props = {p.attrib["name"]: p.attrib.get("value", "")
                     for p in test.findall("./properties/property")}
            required = ("family", "extreme_scenario", "extreme_target", "scope_kind")
            if any(not props.get(key) for key in required):
                raise ValueError(f"Missing case evidence in {path}: {test.attrib}")
            if props["family"] not in admitted:
                raise ValueError(f"Unknown family: {props['family']}")
            key = (props["family"], test.attrib["name"])
            if key in seen:
                raise ValueError(f"Duplicate receipt: {key}")
            seen.add(key)
            status = next((kind for kind in ("failure", "error", "skipped")
                           if test.find(kind) is not None), "passed")
            cases.append({**props, "case": test.attrib["name"], "status": status,
                          "seconds": float(test.attrib.get("time", 0)), "xml": str(path)})
    passed = {c["family"] for c in cases if c["status"] == "passed"}
    return {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "scope": "Selected host extreme/boundary cases; existing engine internal physics excluded",
        "admitted_families": len(admitted), "case_count": len(cases),
        "passed_cases": sum(c["status"] == "passed" for c in cases),
        "failed_cases": sum(c["status"] in ("failure", "error") for c in cases),
        "skipped_cases": sum(c["status"] == "skipped" for c in cases),
        "families_with_passes": len(passed),
        "families_without_passes": sorted(admitted - passed),
        "families_by_scope": {
            scope: sorted({c["family"] for c in cases
                           if c["status"] == "passed" and c["scope_kind"] == scope})
            for scope in sorted({c["scope_kind"] for c in cases})},
        "evidence_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "test_source_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path("tests").glob("test_extreme_contract_*.py"))},
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
