"""Stage one verified PEM IV member through the approved Hangang wrapper."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import csv
import gzip
import hashlib
import io
import os
import re
import shlex
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

PARENT_ARCHIVE_SIZE = 90_759_411
PARENT_ARCHIVE_SHA256 = "47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab"
MEMBER_PATH = "PEM_ripple_degradation_data/IV_curves/PEM1/PEM1_Initial.csv"
MEMBER_SIZE = 915_460
MEMBER_SHA256 = "a054dad7a1d5ce1f2154b60a79a1adea4f84d5ec00e23c12ca72639ffcddcf0d"
MEMBER_ROWS = 20_040
MEMBER_HEADER = ("current_A", "voltage_V", "step_index")
GZIP_SIZE = 100_159
GZIP_SHA256 = "46e2e7e08cb5d7eb371df30f7b3b6ee221f9c1e5ae46cd40c544b3c21bccfa90"
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


def _remote_file():
    return _remote_root() + "/data/pem-ripple/2/PEM1_Initial.csv.gz"


CHUNK_BYTES = 18 * 1024
WORKERS = 16


def _hash_file(path: Path) -> tuple[int, str]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return size, digest.hexdigest()


def _remote(target: str, command: str) -> str:
    result = subprocess.run(
        [*_run_args(), target, command],
        check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"run.sh {target} failed ({result.returncode}); no new SSH/authentication was attempted: "
            f"{(result.stderr or result.stdout).strip()}"
        )
    return result.stdout.strip()


def _py(code: str, *args: str) -> str:
    encoded_code = base64.b64encode(code.encode("utf-8")).decode("ascii")
    command = f"printf '%s' {encoded_code} | base64 -d | python3 -"
    return command + "".join(" " + shlex.quote(arg) for arg in args)


def _prepare_member(archive_path: Path) -> Path:
    size, digest = _hash_file(archive_path)
    if size != PARENT_ARCHIVE_SIZE or digest != PARENT_ARCHIVE_SHA256:
        raise ValueError("Local parent ZIP differs from its exact source receipt")
    with zipfile.ZipFile(archive_path, "r") as archive:
        info = archive.getinfo(MEMBER_PATH)
        if info.file_size != MEMBER_SIZE:
            raise ValueError("Selected ZIP member size differs from its source receipt")
        with archive.open(info, "r") as source:
            member = source.read(MEMBER_SIZE + 1)
    if len(member) != MEMBER_SIZE or hashlib.sha256(member).hexdigest() != MEMBER_SHA256:
        raise ValueError("Selected CSV differs from its exact member SHA-256 receipt")
    rows = csv.reader(io.StringIO(member.decode("utf-8-sig"), newline=""), strict=True)
    if tuple(next(rows, ())) != MEMBER_HEADER:
        raise ValueError("Selected CSV header differs from its source schema receipt")
    count = 0
    for row in rows:
        if len(row) != len(MEMBER_HEADER) or any(value == "" for value in row):
            raise ValueError("Selected CSV has a ragged or blank row")
        count += 1
    if count != MEMBER_ROWS:
        raise ValueError(f"Selected CSV has {count} rows; expected {MEMBER_ROWS}")

    output = archive_path.parents[3] / "processed" / "pem-ripple" / "2" / "PEM1_Initial.csv.gz"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        existing_size, existing_sha = _hash_file(output)
        if existing_size != GZIP_SIZE or existing_sha != GZIP_SHA256:
            raise ValueError("Existing local gzip member differs; refusing to overwrite")
        return output
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=6) as zipped:
        zipped.write(member)
    compressed = buffer.getvalue()
    if len(compressed) != GZIP_SIZE or hashlib.sha256(compressed).hexdigest() != GZIP_SHA256:
        raise ValueError("Deterministic gzip output differs from the pinned compressed receipt")
    fd, temp = tempfile.mkstemp(prefix=output.name + ".tmp.", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(compressed)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, output)
        except FileExistsError:
            existing_size, existing_sha = _hash_file(output)
            if existing_size != GZIP_SIZE or existing_sha != GZIP_SHA256:
                raise ValueError("Concurrent local gzip member differs; refusing to overwrite")
    finally:
        os.unlink(temp)
    return output


_PREFLIGHT = r"""
import hashlib,pathlib,sys
dest=pathlib.Path(sys.argv[1]); size=int(sys.argv[2]); expected=sys.argv[3]; parts=pathlib.Path(sys.argv[4])
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
if dest.is_symlink() or parts.is_symlink(): raise SystemExit('REFUSE: symlink destination')
if dest.exists():
 if dest.is_file() and dest.stat().st_size==size and digest(dest)==expected: print('EXACT'); raise SystemExit(0)
 raise SystemExit('REFUSE: destination exists with mismatched bytes')
dest.parent.mkdir(parents=True,exist_ok=True); parts.mkdir(parents=True,exist_ok=True); print('READY')
"""

_WRITE_PART = r"""
import base64,hashlib,os,pathlib,sys,tempfile
p=pathlib.Path(sys.argv[1]); want=sys.argv[2]; n=int(sys.argv[3]); data=base64.b64decode(sys.argv[4],validate=True); side=pathlib.Path(str(p)+'.sha256')
def ok(q): return q.is_file() and q.stat().st_size==n and hashlib.sha256(q.read_bytes()).hexdigest()==want
if len(data)!=n or hashlib.sha256(data).hexdigest()!=want: raise SystemExit('REFUSE: bad part receipt')
p.parent.mkdir(parents=True,exist_ok=True)
if p.exists():
 if not ok(p): raise SystemExit('REFUSE: existing part differs')
else:
 fd,t=tempfile.mkstemp(prefix=p.name+'.tmp.',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
  try: os.link(t,p)
  except FileExistsError:
   if not ok(p): raise SystemExit('REFUSE: concurrent part differs')
 finally:
  try: os.unlink(t)
  except FileNotFoundError: pass
if side.exists():
 if side.read_text().strip()!=want: raise SystemExit('REFUSE: part sidecar differs')
else:
 try:
  with side.open('x') as f: f.write(want+'\n')
 except FileExistsError:
  if side.read_text().strip()!=want: raise SystemExit('REFUSE: concurrent sidecar differs')
print('PART_OK')
"""

_ASSEMBLE = r"""
import hashlib,os,pathlib,sys,tempfile
parts=pathlib.Path(sys.argv[1]); dest=pathlib.Path(sys.argv[2]); count,total,chunk=map(int,sys.argv[3:6]); want=sys.argv[6]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
if dest.is_symlink() or parts.is_symlink(): raise SystemExit('REFUSE: symlink destination')
if dest.exists():
 if dest.is_file() and dest.stat().st_size==total and digest(dest)==want: print('EXACT'); raise SystemExit(0)
 raise SystemExit('REFUSE: destination exists with mismatched bytes')
fd,t=tempfile.mkstemp(prefix='.'+dest.name+'.assembling.',dir=dest.parent); all_hash=hashlib.sha256(); written=0
try:
 with os.fdopen(fd,'wb') as out:
  for i in range(count):
   p=parts/f'{i:06d}.bin'; side=pathlib.Path(str(p)+'.sha256')
   if not side.is_file(): raise SystemExit(f'REFUSE: missing part receipt {i}')
   data=p.read_bytes(); ph=side.read_text().strip(); exp=min(chunk,total-i*chunk)
   if len(data)!=exp or hashlib.sha256(data).hexdigest()!=ph: raise SystemExit(f'REFUSE: part mismatch {i}')
   out.write(data); all_hash.update(data); written+=len(data)
  out.flush(); os.fsync(out.fileno())
 if written!=total or all_hash.hexdigest()!=want: raise SystemExit('REFUSE: assembled checksum mismatch')
 os.chmod(t,0o644)
 try: os.link(t,dest)
 except FileExistsError:
  if not dest.is_file() or dest.stat().st_size!=total or digest(dest)!=want: raise SystemExit('REFUSE: concurrent destination differs')
 if dest.stat().st_size!=total or digest(dest)!=want: raise SystemExit('REFUSE: final remote checksum mismatch')
finally:
 try: os.unlink(t)
 except FileNotFoundError: pass
for i in range(count):
 p=parts/f'{i:06d}.bin'
 for q in (pathlib.Path(str(p)+'.sha256'),p):
  try: q.unlink()
  except FileNotFoundError: pass
try: parts.rmdir()
except OSError: pass
print('FINAL_OK')
"""


def _stage(target: str, archive: Path) -> int:
    payload = _prepare_member(archive)
    count = (GZIP_SIZE + CHUNK_BYTES - 1) // CHUNK_BYTES
    # Each staging attempt gets its own immutable scratch namespace. Failed
    # prior attempts are left untouched for inspection and cannot poison retry.
    parts = _remote_file() + f".parts.{GZIP_SHA256[:12]}.attempt2"
    print(f"Parent archive SHA-256 verified: {PARENT_ARCHIVE_SHA256}", flush=True)
    print(f"Source member SHA-256 verified: {MEMBER_SHA256}", flush=True)
    hello = _remote(target, "hostname; whoami")
    print(f"Shared connection: {hello.replace(chr(10), ' / ')}", flush=True)
    response = _remote(target, _py(_PREFLIGHT, _remote_file(), str(GZIP_SIZE), GZIP_SHA256, parts))
    if response == "EXACT":
        print(f"Remote member already matches SHA-256 {GZIP_SHA256}", flush=True)
        return 0
    if response != "READY":
        raise RuntimeError(f"Unexpected preflight response: {response!r}")

    with payload.open("rb") as stream, concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        pending = []
        for index in range(count):
            block = stream.read(CHUNK_BYTES)
            if not block:
                raise OSError("Compressed member ended before its receipted size")
            part_sha = hashlib.sha256(block).hexdigest()
            command = _py(
                _WRITE_PART, f"{parts}/{index:06d}.bin", part_sha, str(len(block)),
                base64.b64encode(block).decode("ascii"),
            )
            pending.append(pool.submit(_remote, target, command))
            if len(pending) == WORKERS or index == count - 1:
                for future in pending:
                    if future.result() != "PART_OK":
                        raise RuntimeError("Unexpected per-part response")
                pending.clear()
        if stream.read(1):
            raise OSError("Compressed member grew while staging")

    result = _remote(target, _py(
        _ASSEMBLE, parts, _remote_file(), str(count), str(GZIP_SIZE),
        str(CHUNK_BYTES), GZIP_SHA256,
    ))
    if result not in {"FINAL_OK", "EXACT"}:
        raise RuntimeError(f"Unexpected final assembly response: {result!r}")
    print(f"Staged {GZIP_SIZE} bytes at {_remote_file()}", flush=True)
    print(f"Remote gzip SHA-256: {GZIP_SHA256}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("cpu", "gpu"), default="cpu")
    args = parser.parse_args()
    if os.name != "nt":
        raise OSError("Run from Windows Python; each remote command uses the exact wsl.exe run.sh wrapper")
    archive = Path(__file__).resolve().parents[1] / "data" / "raw" / "pem-ripple-degradation" / "2" / "PEM_ripple_degradation_data.zip"
    if archive.is_symlink() or not archive.is_file():
        raise FileNotFoundError(f"Verified parent archive is not present: {archive}")
    return _stage(args.target, archive.resolve(strict=True))


if __name__ == "__main__":
    raise SystemExit(main())

