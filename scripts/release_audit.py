"""Inspect real source/wheel archives for excluded data, private paths and credentials."""

import argparse
import hashlib
import re
import tarfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("dist"),
                        help="Built distribution directory (relative paths resolve from repository root)")
    parser.add_argument("--report", type=Path, default=Path("research/release_audit.md"),
                        help="Audit report destination (relative paths resolve from repository root)")
    args = parser.parse_args()
    directory = args.directory if args.directory.is_absolute() else root/args.directory
    report = args.report if args.report.is_absolute() else root/args.report
    directory, report = directory.resolve(), report.resolve()
    forbidden_suffixes = {
        ".pdf", ".xlsx", ".xls", ".mat", ".npz", ".zip", ".h5", ".hdf5",
        ".csv", ".tsv", ".json", ".jsonl", ".dat", ".raw", ".nc", ".parquet",
        ".feather", ".arrow", ".pyc", ".pem", ".key", ".jpg", ".jpeg", ".tif", ".tiff",
    }
    forbidden_parts = {".venv", "artifacts", "raw", "processed", ".git", "__pycache__", "payload"}
    patterns = [re.compile(rb"[A-Za-z]:[\\/]Users[\\/]", re.I),
                re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
                re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")]
    reports, failures, coherence = [], [], []
    package_root = root/"src"/"h2physics"
    expected_sources = {
        "h2physics/"+item.relative_to(package_root).as_posix(): item.read_bytes()
        for item in package_root.rglob("*.py")
    }
    if not expected_sources:
        raise RuntimeError("No package Python sources found for archive/source comparison")
    wheels = sorted(directory.glob("*.whl"))
    sources = sorted(directory.glob("*.tar.gz"))
    if not wheels or not sources:
        missing = ", ".join(name for name, present in (("wheel (.whl)", wheels),
                                                     ("source (.tar.gz)", sources)) if not present)
        raise RuntimeError(f"Build both distributions in the selected directory before auditing; missing {missing}")
    paths = wheels+sources
    for path in paths:
        if path.suffix == ".whl":
            with ZipFile(path) as archive:
                contents = [(item.filename, archive.read(item)) for item in archive.infolist() if not item.is_dir()]
        else:
            with tarfile.open(path, "r:gz") as archive:
                contents = []
                for item in archive.getmembers():
                    if not item.isfile():
                        if not item.isdir():
                            failures.append(f"{path.name}: unexpected special archive member {item.name}")
                        continue
                    with archive.extractfile(item) as source:
                        contents.append((item.name, source.read()))
        names = []
        archived_sources = {}
        for name, payload in contents:
            member = PurePosixPath(name)
            names.append(name)
            if member.is_absolute() or ".." in member.parts:
                failures.append(f"{path.name}: unsafe archive path {name}")
            if forbidden_parts.intersection(member.parts) or member.suffix.lower() in forbidden_suffixes:
                failures.append(f"{path.name}: excluded content {name}")
            if any(pattern.search(payload) for pattern in patterns):
                failures.append(f"{path.name}: private path or credential marker in {name}")
            parts = member.parts
            if path.suffix == ".whl":
                package_name = name if parts and parts[0] == "h2physics" else None
            else:
                package_name = "/".join(parts[2:]) if len(parts) >= 4 and parts[1:3] == ("src", "h2physics") else None
            if package_name is not None and member.suffix == ".py":
                archived_sources[package_name] = payload
        if len(names) != len(set(names)):
            failures.append(f"{path.name}: duplicate archive member names")
        missing_sources = expected_sources.keys()-archived_sources.keys()
        extra_sources = archived_sources.keys()-expected_sources.keys()
        changed_sources = sorted(name for name in expected_sources.keys() & archived_sources.keys()
                                 if expected_sources[name] != archived_sources[name])
        for kind, entries in (("missing", sorted(missing_sources)), ("unexpected", sorted(extra_sources)),
                              ("different bytes", changed_sources)):
            failures.extend(f"{path.name}: package source {kind}: {name}" for name in entries)
        coherence.append((path.name, len(archived_sources), len(missing_sources),
                          len(extra_sources), len(changed_sources)))
        for required in ("LICENSE", "NOTICE"):
            if not any(PurePosixPath(name).name == required for name in names):
                failures.append(f"{path.name}: missing {required}")
        if path.suffix == ".whl" and not any(
                PurePosixPath(name).name == "WHEEL" and ".dist-info" in name for name in names):
            failures.append(f"{path.name}: missing wheel distribution metadata")
        if path.name.endswith(".tar.gz"):
            if not any(PurePosixPath(name).name == "PKG-INFO" for name in names):
                failures.append(f"{path.name}: missing source distribution metadata")
            if any(name.endswith("/research/release_audit.md") for name in names):
                failures.append(f"{path.name}: post-build audit report must remain outside the audited archive")
            for required in ("AGENTS.md", "HANDOFF.md", "USER_GUIDE_KO.md"):
                if not any(PurePosixPath(name).name == required for name in names):
                    failures.append(f"{path.name}: missing continuation document {required}")
        reports.append((path.name, len(contents), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()))
    lines = ["# Distribution content audit", "",
             "This records a development build, not a publication or a legal clearance. "
             "Actual archive members were inspected without extraction. The checks cover "
             "external data/cache exclusions, unsafe paths, local user paths, common credential "
             "markers, license notices and source-distribution continuation documents.", "",
             "| Archive | Files | Bytes | SHA-256 |", "|---|---:|---:|---|"]
    lines += [f"| {name} | {count} | {size} | `{digest}` |" for name, count, size, digest in reports]
    lines += ["", "## Current package source comparison", "",
              "Every package Python member is compared byte-for-byte with the working source, "
              "including files not yet tracked by Git. No package import or scientific execution occurs.", "",
              "| Archive | Package Python files | Missing | Unexpected | Different bytes |",
              "|---|---:|---:|---:|---:|"]
    lines += [f"| {name} | {count} | {missing} | {extra} | {changed} |"
              for name, count, missing, extra, changed in coherence]
    lines += ["", f"Result: {'FAIL' if failures else 'PASS'}."]
    lines += ["", *failures] if failures else []
    lines += ["", "The audit report is produced after the audited build and deliberately excluded "
              "from the source archive to avoid embedding a stale or self-referential record. "
              "It remains a public Git research record. Rebuilding after source "
              "or documentation edits produces different archive hashes and requires another audit."]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("distribution content audit", "FAIL" if failures else "PASS", reports)
    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
