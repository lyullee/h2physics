"""Parallel SHA-checked archive transfer through the existing Hangang WSL wrapper."""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath


def _public_config():
    """Read explicit task configuration; never open a new SSH connection."""
    names = ("H2PHYSICS_WSL_USER", "H2PHYSICS_RUN_WRAPPER", "H2PHYSICS_REMOTE_ROOT")
    values = [os.environ.get(name, "") for name in names]
    if not all(values):
        raise ValueError("Set " + ", ".join(names) + " for the existing shared session")
    user, wrapper, root = values
    distribution = os.environ.get("H2PHYSICS_WSL_DISTRIBUTION", "Ubuntu-22.04")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", user) or not re.fullmatch(r"[A-Za-z0-9._-]+", distribution):
        raise ValueError("Use explicit normalized WSL user/distribution identifiers")
    for value in (wrapper, root):
        path = PurePosixPath(value)
        if (not path.is_absolute() or path.as_posix() != value
                or any(part in {".", ".."} for part in path.parts)
                or not re.fullmatch(r"/[A-Za-z0-9._/-]+", value)):
            raise ValueError("Use absolute normalized wrapper and remote-root paths")
    if PurePosixPath(wrapper).name != "run.sh" or not root.startswith("/scratch/"):
        raise ValueError("Use the existing run.sh wrapper and an explicit scratch workspace")
    return (("wsl.exe", "-d", distribution, "-u", user, "--exec", "/bin/bash", wrapper), root)


def _run_args():
    return _public_config()[0]


def _remote_root():
    return _public_config()[1]


MAX_PART_BYTES = 20_000
MAX_WORKERS = 16


def _remote(target: str, command: str) -> str:
    result = subprocess.run(
        [*_run_args(), target, command], check=True, capture_output=True,
        encoding="utf-8", errors="replace",
    )
    return result.stdout


def verify_snapshot(target: str, verified_dir: str, base_revision: str,
                    manifest_sha256: str) -> str:
    verified = _remote_path(verified_dir)
    if not re.fullmatch(r"[0-9a-f]{40}", base_revision):
        raise ValueError("Base revision must be a full lowercase commit hash")
    if not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256):
        raise ValueError("Manifest digest must be a lowercase SHA-256")
    python = _remote_root() + "/.venv/bin/python"
    command = f"""set -eu
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH={verified}/src
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
{python} -c 'from pathlib import Path; from h2physics.cluster_validation import verify_source_manifest; verify_source_manifest(Path("{verified}"), "{base_revision}", "{manifest_sha256}"); print("manifest_verified={manifest_sha256}")'
"""
    output = _remote(target, command)
    if f"manifest_verified={manifest_sha256}" not in output:
        raise RuntimeError("Remote source-manifest receipt is missing")
    return output


def _remote_path(value: str) -> str:
    path = PurePosixPath(value)
    if (not path.is_absolute()
            or not value.startswith(_remote_root() + "/")
            or ".." in path.parts or "\\" in value
            or not re.fullmatch(re.escape(_remote_root()) + r"/[A-Za-z0-9._/-]+", value)):
        raise ValueError("Use a normalized path below the configured scratch workspace")
    return value.rstrip("/")


def _send_part(target, parts_dir, index, payload):
    digest = hashlib.sha256(payload).hexdigest()
    data64 = base64.b64encode(payload).decode("ascii")
    path = f"{parts_dir}/part-{index:06d}"
    temp = f"{path}.tmp"
    command = f"""set -eu
if [ -e {path} ]; then
  test "$(wc -c < {path})" -eq {len(payload)}
  test "$(sha256sum {path} | cut -d ' ' -f 1)" = {digest}
else
  test ! -e {temp}
  printf '%s' '{data64}' | base64 -d > {temp}
  test "$(wc -c < {temp})" -eq {len(payload)}
  test "$(sha256sum {temp} | cut -d ' ' -f 1)" = {digest}
  mv -- {temp} {path}
fi
printf 'part={index} sha256={digest}\n'
"""
    receipt = _remote(target, command)
    if f"part={index} sha256={digest}" not in receipt:
        raise RuntimeError(f"Remote SHA receipt missing for part {index}")
    return index


def transfer_snapshot(archive, *, target="cpu", incoming_dir, verified_dir,
                      part_bytes=MAX_PART_BYTES, workers=MAX_WORKERS):
    source = Path(archive).resolve(strict=True)
    incoming = _remote_path(incoming_dir)
    verified = _remote_path(verified_dir)
    if incoming == verified:
        raise ValueError("Incoming and verified paths must differ")
    if not 1 <= part_bytes <= MAX_PART_BYTES or not 1 <= workers <= MAX_WORKERS:
        raise ValueError("Chunk size or worker count exceeds the safe Windows transfer limit")
    payload = source.read_bytes()
    archive_sha = hashlib.sha256(payload).hexdigest()
    base_revision = (source.parent / "repository" / "SOURCE_REVISION.txt").read_text(
        encoding="utf-8"
    ).strip()
    manifest = (source.parent / "repository" / "SOURCE_MANIFEST.sha256").read_bytes()
    manifest_sha = hashlib.sha256(manifest).hexdigest()

    incoming = incoming.rstrip("/")
    verified = verified.rstrip("/")
    parts_dir = f"{incoming}/parts-{archive_sha[:12]}"
    remote_archive = f"{incoming}/source-{archive_sha[:12]}.tar.gz"
    _remote(target, f"set -eu\nmkdir -p -- {parts_dir}\n")

    chunks = [payload[i:i + part_bytes] for i in range(0, len(payload), part_bytes)]
    futures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, chunk in enumerate(chunks):
            futures.append(pool.submit(_send_part, target, parts_dir, index, chunk))
        completed = 0
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 25 == 0 or completed == len(chunks):
                print(f"verified_parts={completed}/{len(chunks)}", flush=True)

    archive_temp = f"{remote_archive}.tmp"
    combine = f"""set -eu
test ! -e {remote_archive}
test ! -e {archive_temp}
for index in $(seq 0 {len(chunks) - 1}); do
  part=$(printf '%s/part-%06d' {parts_dir} "$index")
  test -f "$part"
  cat -- "$part"
done > {archive_temp}
test "$(wc -c < {archive_temp})" -eq {len(payload)}
test "$(sha256sum {archive_temp} | cut -d ' ' -f 1)" = {archive_sha}
mv -- {archive_temp} {remote_archive}
test ! -e {verified}
mkdir -- {verified}
tar -xzf {remote_archive} -C {verified}
"""
    _remote(target, combine)
    verify_snapshot(target, verified, base_revision, manifest_sha)
    return {
        "archive_bytes": len(payload),
        "archive_sha256": archive_sha,
        "archive_parts": len(chunks),
        "base_revision": base_revision,
        "manifest_sha256": manifest_sha,
        "remote_archive": remote_archive,
        "remote_verified_tree": verified,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--incoming-dir")
    parser.add_argument("--verified-dir", required=True)
    parser.add_argument("--target", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--part-bytes", type=int, default=MAX_PART_BYTES)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--base-revision")
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    if args.verify_only:
        if args.archive is not None or args.base_revision is None or args.manifest_sha256 is None:
            parser.error("--verify-only requires --verified-dir, --base-revision and --manifest-sha256; omit --archive")
        print(verify_snapshot(args.target, args.verified_dir, args.base_revision,
                              args.manifest_sha256), end="")
        return
    if args.archive is None:
        parser.error("--archive is required unless --verify-only is selected")
    if args.incoming_dir is None:
        parser.error("--incoming-dir is required for archive transfer")
    result = transfer_snapshot(
        args.archive, target=args.target, incoming_dir=args.incoming_dir,
        verified_dir=args.verified_dir, part_bytes=args.part_bytes, workers=args.workers,
    )
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

