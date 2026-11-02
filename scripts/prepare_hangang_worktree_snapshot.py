"""Create a byte-pinned Hangang source archive from the current worktree.

The Git revision records the base commit. The generated source manifest pins
the actual tracked and non-ignored untracked working-tree bytes, including
uncommitted edits. Ignored acquisition caches are not included. This script
never connects to a cluster, submits a job, installs software, or runs a model.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    ).stdout.strip()


def _safe_worktree_paths(repository: Path) -> tuple[Path, ...]:
    from scripts.audit_public_tree import audit, git_bound_paths

    checked, findings = audit(repository)
    if findings:
        raise ValueError(
            "GitHub-bound source hygiene audit failed; repair findings before pinning: "
            + "; ".join(findings[:8])
        )
    paths = tuple(git_bound_paths(repository))
    if not paths:
        raise ValueError("The worktree contains no source files to archive")
    checked_set = set(checked)
    if not set(paths).issubset(checked_set):
        raise ValueError("Worktree inventory changed during the source hygiene audit")
    for relative in paths:
        posix = PurePosixPath(relative.as_posix())
        windows = PureWindowsPath(relative.as_posix())
        if (
            posix.is_absolute()
            or windows.drive
            or any(part in {"", ".", ".."} for part in posix.parts)
            or posix.as_posix() != relative.as_posix()
        ):
            raise ValueError(f"Unsafe source path: {relative.as_posix()}")
        candidate = repository / relative
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError(f"Source member is not a regular file: {relative.as_posix()}")
        if relative.as_posix() in {"SOURCE_REVISION.txt", "SOURCE_MANIFEST.sha256"}:
            raise ValueError(f"Reserved campaign receipt already exists: {relative.as_posix()}")
    return paths


def prepare_snapshot(repository: Path, destination: Path) -> dict[str, str | int]:
    root = Path(_git(Path(repository).resolve(), "rev-parse", "--show-toplevel")).resolve()
    revision = _git(root, "rev-parse", "HEAD")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("Git must report a full lowercase base-commit hash")
    paths = _safe_worktree_paths(root)

    target = Path(destination).expanduser().resolve()
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing destination: {target}")
    if not target.parent.is_dir():
        raise FileNotFoundError(f"Destination parent must already exist: {target.parent}")
    if target == root or target in root.parents or root in target.parents:
        raise ValueError("Snapshot destination and repository must be separate, non-nested paths")

    temporary = Path(tempfile.mkdtemp(prefix=".h2physics-worktree-snapshot-", dir=target.parent))
    try:
        snapshot = temporary / "repository"
        snapshot.mkdir()
        for relative in paths:
            source = root / relative
            destination_file = snapshot / relative
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination_file)

        (snapshot / "SOURCE_REVISION.txt").write_text(revision + "\n", encoding="utf-8")

        from h2physics.cluster_validation import source_manifest, verify_source_manifest

        manifest = source_manifest(snapshot)
        (snapshot / "SOURCE_MANIFEST.sha256").write_bytes(manifest)
        manifest_sha256 = hashlib.sha256(manifest).hexdigest()
        verify_source_manifest(snapshot, revision, manifest_sha256)

        archive = temporary / "source.tar.gz"
        with tarfile.open(archive, mode="w:gz") as output:
            for path in sorted(snapshot.rglob("*"), key=lambda item: item.relative_to(snapshot).as_posix()):
                if path.is_symlink():
                    raise ValueError(f"Snapshot unexpectedly contains a symlink: {path}")
                output.add(path, arcname=path.relative_to(snapshot).as_posix(), recursive=False)
        archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
        result = {
            "base_revision": revision,
            "manifest_sha256": manifest_sha256,
            "manifest_entries": len(manifest.decode("utf-8").splitlines()),
            "archive_bytes": archive.stat().st_size,
            "archive_sha256": archive_sha256,
        }
        temporary.rename(target)
        return result
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=ROOT,
        help="Git worktree to snapshot (defaults to this script's repository)",
    )
    parser.add_argument(
        "--destination",
        required=True,
        type=Path,
        help="New directory outside the repository; contains repository/ and source.tar.gz",
    )
    arguments = parser.parse_args()
    result = prepare_snapshot(arguments.repository, arguments.destination)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
