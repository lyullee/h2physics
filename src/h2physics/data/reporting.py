"""Text acquisition receipts for scientific attribution and replay."""

import hashlib
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from .acquire import AcquisitionReport


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _inventory_file_count(record: dict) -> int:
    """Count acquired files from versioned current or legacy receipt fields.

    Older source manifests used ``downloaded`` booleans instead of per-file
    ``status`` strings. Selected archive-member receipts can have neither field
    because acquisition is declared once at the top level.
    """
    for field in ("acquired_file_count", "selected_member_count"):
        value = record.get(field)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"Invalid {field} in acquisition receipt")
        return value

    files = record.get("files", [])
    if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):
        raise ValueError("Acquisition receipt file entries must be tables")
    count = 0
    for item in files:
        if "status" in item:
            status = item["status"]
            if not isinstance(status, str):
                raise ValueError("Per-file acquisition status must be text")
            # Some older receipts carry qualification suffixes such as
            # ``acquired_and_publisher_md5_verified``.
            count += status in {"acquired", "cached"} or status.startswith("acquired_")
            continue
        if "downloaded" in item:
            downloaded = item["downloaded"]
            if not isinstance(downloaded, bool):
                raise ValueError("Legacy downloaded field must be a boolean")
            count += downloaded
    if (files and count == 0 and record.get("_inventory_acquired_bytes", 0) > 0
            and not any("status" in item or "downloaded" in item for item in files)):
        # Legacy receipts sometimes list only acquired payload rows and omit
        # per-file status. Explicit selected-member counts take precedence above.
        count = len(files)
    return count


def write_receipt(report: AcquisitionReport, destination: Path) -> None:
    dataset = report.dataset
    entries = {
        "key": dataset.key, "title": dataset.title, "doi": dataset.doi,
        "version": dataset.version, "origin": dataset.origin,
        "source_updated_at": dataset.source_updated_at,
        "license_id": dataset.license_id, "license_url": dataset.license_url,
        "metadata_url": dataset.metadata_url, "metadata_sha256": dataset.metadata_sha256,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
    }
    lines = [f"{key} = {_string(value)}" for key, value in entries.items()]
    lines.extend([
        "authors = [" + ", ".join(_string(x) for x in dataset.authors) + "]",
        "families = [" + ", ".join(_string(x) for x in dataset.families) + "]",
        f"rights_permitted = {str(report.rights_permitted).lower()}",
        "validation_qualified = false",
        f"listed_file_count = {len(dataset.files)}",
        f"acquired_bytes = {report.acquired_bytes}",
        "omitted_files = [" + ", ".join(_string(x) for x in report.omitted_files) + "]",
    ])
    for url, payload in dataset.supporting_metadata:
        lines += ["", "[[supporting_metadata]]", f"url = {_string(url)}",
                  f"sha256 = {_string(hashlib.sha256(payload).hexdigest())}"]
    remote = {x.name: x for x in dataset.files}
    for file in report.files:
        source = remote[file.name]
        lines += ["", "[[files]]", f"name = {_string(file.name)}",
                  f"url = {_string(source.url)}", f"relative_path = {_string(file.relative_path)}",
                  f"size_bytes = {file.size_bytes}", f"sha256 = {_string(file.sha256)}",
                  f"publisher_checksum_algorithm = {_string(source.checksum_algorithm)}",
                  f"publisher_checksum = {_string(source.checksum)}",
                  f"publisher_checksum_verified = {str(file.publisher_checksum_verified).lower()}",
                  f"status = {_string(file.status)}", f"error = {_string(file.error)}"]
    text = "\n".join(lines) + "\n"
    tomllib.loads(text)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def summarize_receipts(directory: Path, destination: Path) -> None:
    records = []
    for path in sorted(directory.glob("*.toml")):
        record = tomllib.loads(path.read_text(encoding="utf-8"))
        if "listed_file_count" not in record:
            continue
        if "rights_permitted" not in record:
            raise ValueError(f"Incomplete acquisition receipt fields in {path}")
        acquired_bytes = record.get("acquired_bytes")
        if acquired_bytes is None:
            acquired_bytes = record.get("selected_member_bytes")
        if (isinstance(acquired_bytes, bool) or not isinstance(acquired_bytes, int)
                or acquired_bytes < 0):
            raise ValueError(f"Acquisition receipt has no valid acquired-byte total in {path}")
        record["_inventory_acquired_bytes"] = acquired_bytes
        records.append(record)
    lines = ["# Public data acquisition inventory", "",
             "Acquisition and rights status do not establish independent validation. Origin labels",
             "describe collections; mixed records need per-file and per-column qualification.", "",
             "| Dataset | Origin | License | Files acquired / listed source items | Acquired MB |",
             "|---|---|---|---:|---:|"]
    for record in records:
        count = _inventory_file_count(record)
        link = (f"https://doi.org/{record['doi']}" if record["doi"] else record["metadata_url"])
        if "selected_member_count" in record:
            acquisition_scope = (f"{count} selected / "
                                 f"{record['listed_file_count']} listed")
        else:
            acquisition_scope = f"{count} / {record['listed_file_count']}"
        acquired_mb = record["_inventory_acquired_bytes"] / 1e6
        mb_display = f"{acquired_mb:.3f}" if 0 < acquired_mb < 0.01 else f"{acquired_mb:.2f}"
        lines.append(f"| [{record['key']}]({link}) | {record['origin']} | "
                     f"{record['license_id']} | {acquisition_scope} | {mb_display} |")
    lines += ["", "## Interpretation", "",
              "Omissions, failed acquisitions, attribution and hashes are in `research/data/*.toml`.",
              "External attachments and source metadata are ignored under `data/raw`.",
              "Independent experiment counts and unit/geometry suitability require a separate audit.", ""]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
