"""Create a small byte-pinned delta between two verified Hangang source trees."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def _manifest_map(payload: bytes) -> dict[str, str]:
    result = {}
    for row in payload.decode("utf-8").splitlines():
        digest, sep, relative = row.partition("  ")
        path = PurePosixPath(relative)
        if (not sep or not re.fullmatch(r"[0-9a-f]{64}", digest) or path.is_absolute()
                or path.as_posix() != relative
                or any(part in {"", ".", ".."} for part in path.parts)
                or relative in result):
            raise ValueError("Invalid source manifest row")
        result[relative] = digest
    return result


def prepare_delta(base_repository: Path, repository: Path, destination: Path) -> dict[str, str | int]:
    import sys
    sys.path.insert(0, str(ROOT))
    from h2physics.cluster_validation import _source_manifest_member, verify_source_manifest
    from scripts.audit_public_tree import _content_findings
    from scripts.prepare_hangang_worktree_snapshot import _git, _safe_worktree_paths

    base = Path(base_repository).resolve(strict=True)
    base_revision = (base / "SOURCE_REVISION.txt").read_text(encoding="utf-8").strip()
    base_bytes = (base / "SOURCE_MANIFEST.sha256").read_bytes()
    base_digest = hashlib.sha256(base_bytes).hexdigest()
    verify_source_manifest(base, base_revision, base_digest)
    root = Path(_git(Path(repository).resolve(), "rev-parse", "--show-toplevel")).resolve()
    revision = _git(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Git must report a full lowercase base-commit hash")
    paths = _safe_worktree_paths(root)
    output = Path(destination).resolve()
    if output.exists() or not output.parent.is_dir():
        raise FileExistsError("Delta output must be a new path under an existing directory")
    if output == root or output in root.parents or root in output.parents:
        raise ValueError("Delta output must be outside and separate from the repository")

    temporary = Path(tempfile.mkdtemp(prefix=".hangang-delta-", dir=output.parent)).resolve()
    if temporary.parent != output.parent or not temporary.name.startswith(".hangang-delta-"):
        raise ValueError("Temporary delta directory must stay inside the chosen staging parent")
    try:
        before = _manifest_map(base_bytes)
        after = {}
        payloads = {}
        # Capture each source once. Keep only changed bytes, rather than writing
        # and re-reading a complete temporary checkout for every small delta.
        # Path sorting matches source_manifest on the current host.
        for relative in sorted(paths):
            if not _source_manifest_member(relative.as_posix()):
                continue
            candidate = root / relative
            resolved = candidate.resolve(strict=True)
            if candidate.is_symlink() or root not in resolved.parents:
                raise ValueError(f"Source path changed to an unsafe target: {relative.as_posix()}")
            payload = candidate.read_bytes()
            findings = _content_findings(relative, payload, "captured delta")
            if findings:
                raise ValueError("Captured source hygiene failed: " + "; ".join(findings))
            name = relative.as_posix()
            digest = hashlib.sha256(payload).hexdigest()
            after[name] = digest
            if before.get(name) != digest:
                payloads[name] = payload
        manifest = ("\n".join(f"{digest}  {name}" for name, digest in after.items()) + "\n").encode("utf-8")
        if _manifest_map(manifest) != after:
            raise ValueError("Captured paths do not form a valid source manifest")
        manifest_digest = hashlib.sha256(manifest).hexdigest()
        changed = sorted(payloads)
        deleted = sorted(set(before) - set(after))
        metadata = {
            "format": "h2physics-hangang-delta-v1",
            "base_revision": base_revision,
            "base_manifest_sha256": base_digest,
            "target_revision": revision,
            "target_manifest_sha256": manifest_digest,
            "changed": {name: after[name] for name in sorted(changed)},
            "deleted": deleted,
        }
        package_dir = temporary / "package"
        package_dir.mkdir()
        bundle = package_dir / "delta.tar.gz"
        with bundle.open("wb") as stream, gzip.GzipFile(
                filename="", fileobj=stream, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                _add_bytes(archive, "delta/metadata.json", json.dumps(metadata, sort_keys=True).encode())
                _add_bytes(archive, "delta/SOURCE_MANIFEST.sha256", manifest)
                _add_bytes(archive, "delta/SOURCE_REVISION.txt", (revision + "\n").encode())
                for name in changed:
                    _add_bytes(archive, "delta/files/" + name, payloads[name])
        # Validate the packaged bytes, not a second read of a moving worktree.
        # The full independently verified base plus this exact transition pins
        # every target member; remote apply still reconstructs and verifies it.
        reconstructed = {name: digest for name, digest in before.items() if name not in deleted}
        with tarfile.open(bundle, "r:gz") as archive:
            for name in changed:
                member = archive.extractfile("delta/files/" + name)
                if member is None:
                    raise ValueError("Delta payload member is missing")
                reconstructed[name] = hashlib.sha256(member.read()).hexdigest()
        if reconstructed != after:
            raise ValueError("Packaged delta does not reconstruct its target manifest")
        receipt = {
            **{key: value for key, value in metadata.items() if key not in {"changed", "deleted"}},
            "changed_files": len(changed), "deleted_files": len(deleted),
            "archive_bytes": bundle.stat().st_size,
            "archive_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        }
        (package_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        package_dir.rename(output)
        return receipt
    except BaseException:
        raise
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def _tar_info(name: str, payload: bytes) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = 0o644
    return info


def _add_bytes(archive: tarfile.TarFile, name: str, payload: bytes) -> None:
    archive.addfile(_tar_info(name, payload), io.BytesIO(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-repository", required=True, type=Path,
                        help="repository/ directory from the previous verified snapshot")
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    result = prepare_delta(args.base_repository, args.repository, args.destination)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
