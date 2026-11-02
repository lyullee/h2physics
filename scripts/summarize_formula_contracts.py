"""Summarize executed known-answer cases without equating support with physics."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree


def summarize(paths):
    cases = []
    for path in paths:
        for case in ElementTree.parse(path).getroot().iter("testcase"):
            props = {p.attrib["name"]: p.attrib.get("value", "")
                     for p in case.findall("./properties/property")}
            if not props.get("family"):
                raise ValueError(f"Missing family evidence: {path}: {case.attrib}")
            scope = props.get("scope_kind", props.get("formula_scope", props.get("scope")))
            if not scope:
                raise ValueError(f"Missing formula scope: {path}: {props}")
            if props.get("oracle_kind") == "identity_check":
                scope = "thermodynamic_identity_only"
            status = next((kind for kind in ("failure", "error", "skipped")
                           if case.find(kind) is not None), "passed")
            cases.append({"case": case.attrib["name"], "status": status,
                          "family": props["family"], "scope": scope,
                          "target": props.get("formula_target"),
                          "oracle": props.get("oracle_description"),
                          "xml": str(path)})
    keys = [(c["family"], c["case"]) for c in cases]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate case evidence; do not combine repeated suite runs")
    return {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "scope": "Named nominal host calculations only; no native-engine physics validation",
        "case_count": len(cases),
        "passed_case_count": sum(c["status"] == "passed" for c in cases),
        "passed_family_count": len({c["family"] for c in cases if c["status"] == "passed"}),
        "passed_families_by_scope": {
            scope: sorted({c["family"] for c in cases
                           if c["status"] == "passed" and c["scope"] == scope})
            for scope in sorted({c["scope"] for c in cases})},
        "evidence_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "test_source_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path("tests").glob("test_formula_contract_*.py"))},
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.xml)
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(args.output)
    print(json.dumps({k: result[k] for k in
                      ("case_count", "passed_case_count", "passed_family_count")}))
