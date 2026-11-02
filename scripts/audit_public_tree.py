"""Audit GitHub-bound working-tree files for data and credential exposure.

This is a conservative content inventory, not a copyright or legal review. It
checks tracked files plus non-ignored untracked files and does not follow
symlinks or inspect ignored acquisition caches.
"""

import argparse
import re
import subprocess
from pathlib import Path, PurePosixPath

FORBIDDEN_SUFFIXES = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".csv", ".tsv", ".dat",
    ".raw", ".tdms", ".nc", ".parquet", ".feather", ".arrow", ".bin",
    ".json", ".jsonl",
    ".npy", ".xlsx", ".xls", ".xlsm", ".xlsb", ".mat", ".npz", ".zip",
    ".whl", ".egg", ".h5", ".hdf", ".hdf5", ".pyc", ".pem", ".key",
    ".p12", ".pfx", ".exe", ".dll", ".so", ".dylib",
    ".jpg", ".jpeg", ".tif", ".tiff",
}
FORBIDDEN_PARTS = {
    ".git", ".venv", "__pycache__", "artifacts", "raw", "processed",
    "results", "dist", "build", "tmp", "target", "payload",
}
SUSPICIOUS_BYTES = (
    ("local Windows user path", re.compile(rb"[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]", re.I)),
    ("GitHub token", re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("private key header", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(rb"AKIA[0-9A-Z]{16}")),
)


def git_bound_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root, check=True, stdout=subprocess.PIPE,
    )
    names = result.stdout.split(b"\0")
    paths = []
    for name in names:
        if not name:
            continue
        # Git paths are byte strings on POSIX and UTF-8 on this project's Windows host.
        relative = Path(name.decode("utf-8", errors="strict"))
        candidate = root / relative
        if candidate.is_symlink():
            paths.append(relative)
            continue
        if candidate.is_file():
            paths.append(relative)
    return sorted(set(paths), key=lambda path: path.as_posix().casefold())


def git_index_entries(root: Path) -> list[tuple[Path, bytes, bytes, bytes]]:
    """Return index paths with their object mode, blob ID and merge stage."""
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=root, check=True, stdout=subprocess.PIPE,
    )
    entries = []
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, separator, name = entry.partition(b"\t")
        if not separator:
            raise RuntimeError("Could not parse staged Git path metadata")
        fields = metadata.split()
        if len(fields) != 3:
            raise RuntimeError("Could not parse staged Git object metadata")
        mode, object_id, stage = fields
        relative = Path(name.decode("utf-8", errors="strict"))
        entries.append((relative, mode, object_id, stage))
    return entries


def git_index_blobs(root: Path, entries: list[tuple[Path, bytes, bytes, bytes]]):
    """Read indexed blob contents in one batch, independent of working-tree bytes."""
    blobs = [entry for entry in entries if entry[1] != b"160000"]
    if not blobs:
        return []
    request = b"".join(object_id + b"\n" for _, _, object_id, _ in blobs)
    result = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=root, input=request,
        check=True, stdout=subprocess.PIPE,
    )
    output = result.stdout
    cursor = 0
    records = []
    for relative, _, object_id, stage in blobs:
        header_end = output.find(b"\n", cursor)
        if header_end < 0:
            raise RuntimeError("Git returned a truncated index-object header")
        header = output[cursor:header_end].split()
        if (len(header) != 3 or header[0] != object_id or header[1] != b"blob"):
            raise RuntimeError(f"Git index object is not a readable blob: {relative.as_posix()}")
        try:
            size = int(header[2])
        except ValueError as error:
            raise RuntimeError(f"Git returned an invalid blob size: {relative.as_posix()}") from error
        start = header_end + 1
        end = start + size
        if end >= len(output) or output[end:end + 1] != b"\n":
            raise RuntimeError(f"Git returned a truncated blob: {relative.as_posix()}")
        records.append((relative, stage, output[start:end]))
        cursor = end + 1
    if cursor != len(output):
        raise RuntimeError("Git returned unexpected trailing index-object data")
    return records


def _path_findings(relative: Path) -> list[str]:
    member = PurePosixPath(relative.as_posix())
    failures = []
    if member.is_absolute() or ".." in member.parts:
        failures.append(f"unsafe repository path: {relative.as_posix()}")
    if {part.casefold() for part in member.parts} & FORBIDDEN_PARTS:
        failures.append(f"excluded repository path: {relative.as_posix()}")
    if member.suffix.casefold() in FORBIDDEN_SUFFIXES:
        failures.append(f"excluded repository file type: {relative.as_posix()}")
    if relative.as_posix().casefold().endswith((
        ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst", ".tgz", ".7z", ".rar",
    )):
        failures.append(f"excluded compressed distribution archive: {relative.as_posix()}")
    return failures


def _content_findings(relative: Path, payload: bytes, version: str) -> list[str]:
    return [f"{label} marker in {version} {relative.as_posix()}"
            for label, pattern in SUSPICIOUS_BYTES if pattern.search(payload)]


def audit(root: Path) -> tuple[list[Path], list[str]]:
    indexed = git_index_entries(root)
    checked = sorted(
        set(git_bound_paths(root)) | {entry[0] for entry in indexed},
        key=lambda path: path.as_posix().casefold(),
    )
    failures = []
    for relative, mode, _, stage in indexed:
        failures.extend(_path_findings(relative))
        if mode == b"160000":
            failures.append(
                f"Git submodule reference requires separate source/license review: {relative.as_posix()}"
            )
            continue
        if mode == b"120000":
            failures.append(f"indexed symlink requires manual review: {relative.as_posix()}")
        elif mode not in {b"100644", b"100755"}:
            failures.append(f"unsupported Git index mode {mode.decode('ascii', errors='replace')} at {relative.as_posix()}")
    for relative, stage, payload in git_index_blobs(root, indexed):
        failures.extend(_content_findings(relative, payload, f"index stage {stage.decode('ascii')}"))
    for relative in checked:
        if (root / relative).is_symlink():
            failures.append(f"symlink entry requires manual review: {relative.as_posix()}")
            continue
        failures.extend(_path_findings(relative))
        try:
            payload = (root / relative).read_bytes()
        except OSError as error:
            failures.append(f"cannot read repository file {relative.as_posix()}: {error}")
            continue
        failures.extend(_content_findings(relative, payload, "working tree"))
    return checked, list(dict.fromkeys(failures))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    checked, failures = audit(root)
    print(f"GitHub-bound working-tree audit: {len(checked)} files inspected")
    print("This checks content hygiene only; it does not determine copyright, licenses, or redistribution rights.")
    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
