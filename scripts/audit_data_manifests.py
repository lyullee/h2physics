"""Read-only stdlib audit of existing curated TOML data acquisition receipts.

Checks recorded metadata only. It neither downloads nor hashes external raw data,
and never interprets a public URL as permission to reuse or redistribute a file.
"""

import argparse
import re
import tomllib
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

LICENSE_URL_IDENTITIES = {
    "CC0-1.0": {("creativecommons.org", "/publicdomain/zero/1.0"),
                ("spdx.org", "/licenses/cc0-1.0.html")},
    "CC-BY-4.0": {("creativecommons.org", "/licenses/by/4.0"),
                  ("creativecommons.org", "/licenses/by/4.0/legalcode"),
                  ("spdx.org", "/licenses/cc-by-4.0.html")},
    "CC-BY-SA-4.0": {("creativecommons.org", "/licenses/by-sa/4.0"),
                     ("creativecommons.org", "/licenses/by-sa/4.0/legalcode"),
                     ("spdx.org", "/licenses/cc-by-sa-4.0.html")},
    "etalab-2.0": {("spdx.org", "/licenses/etalab-2.0.html")},
}


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def license_url_matches(identifier, url):
    if not isinstance(identifier, str) or not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        return False
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or port is not None or parsed.query or parsed.fragment):
        return False
    return (parsed.hostname.lower(), parsed.path.rstrip("/").lower()) in LICENSE_URL_IDENTITIES.get(identifier, set())


def audit_manifest(path):
    with path.open("rb") as stream:
        record = tomllib.load(stream)
    # The KIT BagIt receipt predates the common acquisition shape. Preserve its
    # explicit aliases without inventing missing rights or metadata evidence.
    aliases = {"key": "dataset_id", "license_id": "license", "metadata_url": "record_url",
               "authors": "creators", "version": "archive_version"}
    for target, source in aliases.items():
        if target not in record and source in record:
            record[target] = str(record[source]) if target == "version" else record[source]
    files = record.get("files", [])
    acquired = [item for item in files if str(item.get("status", "")).lower().startswith(("acquired", "cached"))]
    acquisition = record.get("acquisition", {})
    has_acquisition = str(acquisition.get("status", "")).lower().startswith("acquired")
    if str(record.get("status", "")).lower().startswith("acquired") and record.get("archive_sha256"):
        has_acquisition = True
        acquisition = dict(download_url=record.get("archive_url"), relative_path=record.get("tracked_raw_storage"),
                           sha256=record.get("archive_sha256"), size_bytes=record.get("archive_bytes"))
    historical = "supersed" in str(record.get("record_status", "")).lower() or bool(record.get("superseded_by_doi"))
    state = "superseded-acquired" if historical and (acquired or has_acquisition) else (
        "acquired" if acquired or has_acquisition else "withheld" if record.get("rights_permitted") is False else "discovery")
    if state == "discovery" and any(str(item.get("status", "")).lower() == "failed" for item in files):
        state = "acquisition-failed"
    missing, cautions = [], []
    for name in ("key", "title", "version", "license_id", "license_url", "metadata_url"):
        if not nonblank(record.get(name)):
            missing.append(name)
    license_id, license_url = record.get("license_id"), record.get("license_url")
    if license_id in LICENSE_URL_IDENTITIES:
        if not license_url_matches(license_id, license_url):
            missing.append("license URL does not identify declared license")
        elif isinstance(license_url, str) and urlsplit(license_url).scheme != "https":
            cautions.append("historical license locator uses HTTP; canonical HTTPS link recommended")
    elif nonblank(license_id):
        cautions.append("license identifier is not in the host acquisition allowlist")
    if not any(nonblank(record.get(name)) for name in ("doi", "identifier", "metadata_url")):
        missing.append("source identity")
    if not digest(record.get("metadata_sha256")):
        missing.append("metadata_sha256")
    if not record.get("authors") and not nonblank(record.get("publisher")):
        missing.append("authors or publisher attribution")
    if not isinstance(record.get("rights_permitted"), bool):
        if nonblank(record.get("license_evidence")):
            cautions.append("license evidence recorded; no common-schema host rights decision flag")
        else:
            missing.append("explicit rights_permitted decision")
    for index, item in enumerate(acquired):
        label = str(item.get("name", index))
        for name in ("name", "url", "relative_path"):
            if not nonblank(item.get(name)):
                missing.append(label+":"+name)
        if not digest(item.get("sha256")):
            missing.append(label+":sha256")
        if not isinstance(item.get("size_bytes"), int) or isinstance(item.get("size_bytes"), bool) or item.get("size_bytes", 0) <= 0:
            missing.append(label+":positive size_bytes")
        if item.get("publisher_checksum_verified") is not True:
            cautions.append(label+":publisher checksum not recorded verified (may be unavailable)")
    if has_acquisition and not acquired:
        for name in ("download_url", "relative_path"):
            if not nonblank(acquisition.get(name)):
                missing.append("acquisition:"+name)
        if not digest(acquisition.get("sha256")):
            missing.append("acquisition:sha256")
        if acquisition.get("publisher_checksum_verified") is not True:
            cautions.append("archive publisher checksum not recorded verified (may be unavailable)")
    # Alternate archive receipts often repeat the same acquired file in [[files]].
    # Report their forms separately rather than counting a single download twice.
    archive_receipts = int(has_acquisition and not acquired)
    workbook_receipts = record.get("workbooks", [])
    for index, workbook in enumerate(workbook_receipts):
        label = "workbook:"+str(workbook.get("name", index))
        if not nonblank(workbook.get("name")):
            missing.append(label+":name")
        if not digest(workbook.get("sha256")):
            missing.append(label+":sha256")
        size = workbook.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            missing.append(label+":positive bytes")
    if (acquired or has_acquisition) and record.get("rights_permitted") is not True:
        cautions.append("acquired bytes have no affirmative host reuse decision")
    if historical:
        cautions.append("historical/superseded: preserve provenance; do not silently select for model use")
    file_clearance = record.get("third_party_component_rights_reviewed") is True
    if acquired or has_acquisition:
        if not nonblank(record.get("license_scope")):
            cautions.append("file-level/third-party license scope not explicitly summarized")
        if not file_clearance:
            cautions.append("no explicit completed third-party component rights review flag")
    return dict(path=path.name, key=record.get("key", ""), state=state,
        acquired_files=len(acquired), archive_receipts=archive_receipts,
        workbook_receipts=len(workbook_receipts), missing=tuple(missing), cautions=tuple(cautions))


def audit_collection(directory):
    rows, failures = [], []
    for path in sorted(directory.glob("*.toml")):
        try:
            rows.append(audit_manifest(path))
        except (OSError, tomllib.TOMLDecodeError, TypeError, AttributeError) as error:
            failures.append((path.name, str(error)))
    return rows, failures


def render_report(rows, failures):
    counts = Counter(row["state"] for row in rows)
    lines = ["# Data manifest metadata audit", "",
        "Recorded TOML metadata only; no downloads, native/model imports, raw-file reads or scientific execution.",
        "A complete metadata record is not file-level copyright clearance or permission to redistribute.", "",
        "File receipts, archive-only receipts and workbook-member receipts are separate forms. "
        "Workbook members are not additional downloads; counts are not added into dataset totals.", "",
        "States: "+", ".join(f"{key}={value}" for key, value in sorted(counts.items())), "",
        "| Manifest | State | File receipts | Archive-only receipts | Workbook members | Missing metadata | Rights/provenance follow-up |",
        "|---|---|---:|---:|---:|---|---|"]
    for row in rows:
        lines.append("| "+" | ".join((row["path"], row["state"], str(row["acquired_files"]),
            str(row["archive_receipts"]), str(row["workbook_receipts"]),
            "; ".join(row["missing"]) or "none in checked fields",
            "; ".join(row["cautions"]) or "none in checked flags"))+" |")
    if failures:
        lines.extend(("", "Parse/read failures:"))
        lines.extend(f"- {name}: {error}" for name, error in failures)
    return "\n".join(lines)+"\n"


def report(directory):
    return render_report(*audit_collection(directory))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1]/"research"/"data")
    parser.add_argument("--output", type=Path, help="Optional metadata report destination")
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--check-metadata", action="store_true",
                        help="Fail on parse errors, empty collection or missing checked metadata; rights follow-up is not clearance")
    checks.add_argument("--check-acquired", action="store_true",
                        help="Require checked metadata on acquired/historical acquired records; unresolved withheld candidates remain reported")
    args = parser.parse_args()
    rows, failures = audit_collection(args.directory)
    text = render_report(rows, failures)
    if args.output is not None:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    required = rows if args.check_metadata else [row for row in rows if row["state"].endswith("acquired")]
    if (args.check_metadata or args.check_acquired) and (
            not required or failures or any(row["missing"] for row in required)):
        raise SystemExit("Data manifest metadata incomplete; inspect report (rights review is a separate condition)")


if __name__ == "__main__":
    main()
