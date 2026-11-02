"""Build a hash-pinned source archive from one immutable Git commit.

This tool packages a clean committed checkout. It never connects to a cluster,
submits a job, installs software, or runs a scientific case.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _members(archive: bytes) -> tuple[tarfile.TarInfo, ...]:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
        values = tuple(source.getmembers())
    names = set()
    for member in values:
        normalized_name = member.name.rstrip("/") if member.isdir() else member.name
        relative = PurePosixPath(normalized_name)
        windows_path = PureWindowsPath(normalized_name)
        if (
            not normalized_name
            or relative.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.as_posix() != normalized_name
            or member.name not in {normalized_name, normalized_name + "/"}
            or normalized_name in names
            or not (member.isfile() or member.isdir())
        ):
            raise ValueError(f"Unsafe or unsupported Git archive member: {member.name!r}")
        names.add(normalized_name)
    return values


def prepare_snapshot(repository: Path, revision: str, destination: Path) -> dict[str, str | int]:
    root = Path(_git(repository.resolve(), "rev-parse", "--show-toplevel")).resolve()
    selected_revision = _git(root, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if not re.fullmatch(r"[0-9a-f]{40}", selected_revision):
        raise ValueError("Git must resolve the requested source to a full commit hash")
    head_revision = _git(root, "rev-parse", "HEAD")
    if (selected_revision == head_revision
            and _git(root, "status", "--porcelain", "--untracked-files=all")):
        raise ValueError(
            "The selected revision is HEAD but the worktree is dirty; pin an explicit commit "
            "that contains the intended changes"
        )

    target = Path(destination).expanduser().resolve()
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing destination: {target}")
    if not target.parent.is_dir():
        raise FileNotFoundError(f"Destination parent must already exist: {target.parent}")
    if target == root or target in root.parents or root in target.parents:
        raise ValueError("Snapshot destination and repository must be separate, non-nested paths")

    archive = subprocess.run(
        ["git", "-C", str(root), "archive", "--format=tar", selected_revision],
        check=True,
        capture_output=True,
    ).stdout
    members = _members(archive)

    # Make the existing manifest implementation importable from this checkout.
    sys.path.insert(0, str(root / "src"))
    from h2physics.cluster_validation import source_manifest, verify_source_manifest

    temporary = Path(tempfile.mkdtemp(prefix=".h2physics-snapshot-", dir=target.parent))
    try:
        snapshot = temporary / "repository"
        snapshot.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
            source.extractall(snapshot, members=members, filter="data")

        if any(
            (snapshot / receipt).exists()
            for receipt in ("SOURCE_REVISION.txt", "SOURCE_MANIFEST.sha256")
        ):
            raise ValueError("Committed source already contains a reserved campaign receipt name")

        tracked = set(_git(root, "ls-tree", "-r", "--name-only", selected_revision).splitlines())
        archived = {member.name.rstrip("/") for member in members if member.isfile()}
        if tracked != archived:
            omitted = sorted(tracked - archived)
            extra = sorted(archived - tracked)
            raise ValueError(
                f"Git archive file list differs from commit; omitted={omitted}, extra={extra}"
            )

        (snapshot / "SOURCE_REVISION.txt").write_text(selected_revision + "\n", encoding="utf-8")
        manifest = source_manifest(snapshot)
        (snapshot / "SOURCE_MANIFEST.sha256").write_bytes(manifest)
        manifest_sha256 = hashlib.sha256(manifest).hexdigest()
        verify_source_manifest(snapshot, selected_revision, manifest_sha256)

        packaged_archive = temporary / "source.tar.gz"
        with tarfile.open(packaged_archive, mode="w:gz") as output:
            for path in sorted(snapshot.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Source snapshot unexpectedly contains a symlink: {path}")
                output.add(path, arcname=path.relative_to(snapshot).as_posix(), recursive=False)
        archive_sha256 = hashlib.sha256(packaged_archive.read_bytes()).hexdigest()
        metadata = {
            "revision": selected_revision,
            "manifest_sha256": manifest_sha256,
            "manifest_entries": len(manifest.decode("utf-8").splitlines()),
            "archive_sha256": archive_sha256,
        }
        temporary.rename(target)
        return metadata
    except BaseException:
        # This path was freshly created by this function and is not user data.
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Git worktree to archive (defaults to this script's repository)",
    )
    parser.add_argument("--revision", default="HEAD", help="Committed Git revision to pin")
    parser.add_argument(
        "--destination",
        required=True,
        type=Path,
        help="New directory outside the repository; it will contain repository/ and source.tar.gz",
    )
    arguments = parser.parse_args()
    result = prepare_snapshot(arguments.repository, arguments.revision, arguments.destination)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
