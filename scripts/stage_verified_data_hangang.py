"""Stage one checksum-pinned data file through the existing Hangang wrapper."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
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


def _data_root():
    return _remote_root() + "/data"
CHUNK_BYTES = 16 * 1024
MAX_WORKERS = 8


def _digest(path: Path) -> tuple[int, str]:
    is_junction = getattr(path, "is_junction", lambda: False)
    if path.is_symlink() or is_junction() or not path.is_file():
        raise ValueError("Source must be a regular, non-symlink file")
    before = path.stat()
    checksum = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            size += len(block)
            checksum.update(block)
    after = path.stat()
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or size != after.st_size):
        raise ValueError("Source changed while its digest was calculated")
    return size, checksum.hexdigest()


def _remote(target: str, command: str) -> str:
    result = subprocess.run(
        [*_run_args(), target, command], check=True, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout.strip()


def _remote_python(code: str, *arguments: str) -> str:
    encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
    command = f"printf '%s' {shlex.quote(encoded)} | base64 -d | python3 -"
    command += "".join(" " + shlex.quote(argument) for argument in arguments)
    return command


def _remote_path(value: str) -> str:
    path = PurePosixPath(value)
    prefix = _data_root() + "/"
    if (not value.startswith(prefix) or path.as_posix() != value
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in value
            or not re.fullmatch(re.escape(_data_root()) + r"/[A-Za-z0-9._/-]+", value)):
        raise ValueError(f"Remote file must be a normalized path below {_data_root()}")
    return value


_PREFLIGHT = r"""
import hashlib,pathlib,sys
root=pathlib.Path(sys.argv[4])
dest=pathlib.Path(sys.argv[1]); size=int(sys.argv[2]); want=sys.argv[3]
parts=pathlib.Path(str(dest)+'.parts.'+want[:12])
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
if root not in dest.parents: raise SystemExit('REFUSE: destination outside data root')
for p in (dest,*dest.parents):
 if p==root.parent: break
 if p.is_symlink(): raise SystemExit('REFUSE: symlink path component')
if dest.exists():
 if dest.is_file() and not dest.is_symlink() and dest.stat().st_size==size and digest(dest)==want:
  print('EXACT'); raise SystemExit(0)
 raise SystemExit('REFUSE: destination exists with different type or bytes')
if parts.is_symlink(): raise SystemExit('REFUSE: staging directory is a symlink')
dest.parent.mkdir(parents=True,exist_ok=True); parts.mkdir(parents=True,exist_ok=True)
print('READY')
"""

_WRITE_PART = r"""
import base64,hashlib,os,pathlib,sys,tempfile
p=pathlib.Path(sys.argv[1]); want=sys.argv[2]; n=int(sys.argv[3])
data=base64.b64decode(sys.argv[4],validate=True)
if len(data)!=n or hashlib.sha256(data).hexdigest()!=want: raise SystemExit('REFUSE: bad part digest')
if p.is_symlink() or p.parent.is_symlink(): raise SystemExit('REFUSE: symlink part path')
p.parent.mkdir(parents=True,exist_ok=True)
side=pathlib.Path(str(p)+'.sha256')
if p.exists():
 if not p.is_file() or p.stat().st_size!=n or hashlib.sha256(p.read_bytes()).hexdigest()!=want: raise SystemExit('REFUSE: existing part differs')
else:
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.tmp.',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
  try: os.link(tmp,p)
  except FileExistsError:
   if p.stat().st_size!=n or hashlib.sha256(p.read_bytes()).hexdigest()!=want: raise SystemExit('REFUSE: concurrent part differs')
 finally:
  try: os.unlink(tmp)
  except FileNotFoundError: pass
if side.exists():
 if side.is_symlink() or side.read_text().strip()!=want: raise SystemExit('REFUSE: sidecar differs')
else:
 try:
  with side.open('x') as f: f.write(want+'\n')
 except FileExistsError:
  if side.read_text().strip()!=want: raise SystemExit('REFUSE: concurrent sidecar differs')
print('PART_OK')
"""

_ASSEMBLE = r"""
import hashlib,os,pathlib,shutil,sys,tempfile
dest=pathlib.Path(sys.argv[1]); parts=pathlib.Path(sys.argv[2])
total,chunk,count=map(int,sys.argv[3:6]); want=sys.argv[6]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
if dest.is_symlink() or parts.is_symlink(): raise SystemExit('REFUSE: symlink destination')
if dest.exists():
 if dest.is_file() and dest.stat().st_size==total and digest(dest)==want: print('EXACT'); raise SystemExit(0)
 raise SystemExit('REFUSE: destination differs')
fd,tmp=tempfile.mkstemp(prefix='.'+dest.name+'.assembling.',dir=dest.parent)
all_hash=hashlib.sha256(); written=0
try:
 with os.fdopen(fd,'wb') as out:
  for i in range(count):
   part=parts/f'{i:06d}.bin'; side=pathlib.Path(str(part)+'.sha256')
   block=part.read_bytes(); expected=min(chunk,total-i*chunk)
   if (part.is_symlink() or side.is_symlink() or not side.is_file()
       or len(block)!=expected or hashlib.sha256(block).hexdigest()!=side.read_text().strip()):
    raise SystemExit(f'REFUSE: part {i} receipt mismatch')
   out.write(block); all_hash.update(block); written+=len(block)
  out.flush(); os.fsync(out.fileno())
 if written!=total or all_hash.hexdigest()!=want: raise SystemExit('REFUSE: final file digest mismatch')
 os.chmod(tmp,0o644)
 try: os.link(tmp,dest)
 except FileExistsError:
  if not dest.is_file() or dest.stat().st_size!=total or digest(dest)!=want: raise SystemExit('REFUSE: concurrent file differs')
 if dest.stat().st_size!=total or digest(dest)!=want: raise SystemExit('REFUSE: installed digest mismatch')
finally:
 try: os.unlink(tmp)
 except FileNotFoundError: pass
shutil.rmtree(parts)
print('FINAL_OK')
"""


def stage_verified_file(
    source: str | Path,
    remote_file: str,
    expected_sha256: str,
    *,
    target: str = "cpu",
) -> dict[str, str | int]:
    if target not in {"cpu", "gpu"}:
        raise ValueError("Only the existing Hangang cpu or gpu wrapper target is allowed")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("expected_sha256 must be a lowercase SHA-256")
    remote_file = _remote_path(remote_file)
    supplied_path = Path(source).absolute()
    for component in (supplied_path, *supplied_path.parents):
        is_junction = getattr(component, "is_junction", lambda: False)
        if component.is_symlink() or is_junction():
            raise ValueError("Source path must not traverse symlinks or junctions")
    path = supplied_path.resolve(strict=True)
    size, sha256 = _digest(path)
    if size <= 0 or sha256 != expected_sha256:
        raise ValueError("Local source size/digest does not match the declared receipt")

    parts_dir = remote_file + ".parts." + sha256[:12]
    response = _remote(target, _remote_python(_PREFLIGHT, remote_file, str(size), sha256, _data_root()))
    if response == "EXACT":
        return {"remote_file": remote_file, "size_bytes": size,
                "sha256": sha256, "status": "already_exact"}
    if response != "READY":
        raise RuntimeError(f"Unexpected remote preflight response: {response!r}")

    count = (size + CHUNK_BYTES - 1) // CHUNK_BYTES

    def upload(index: int, block: bytes) -> None:
        part_sha = hashlib.sha256(block).hexdigest()
        remote_part = f"{parts_dir}/{index:06d}.bin"
        command = _remote_python(
            _WRITE_PART, remote_part, part_sha, str(len(block)),
            base64.b64encode(block).decode("ascii"),
        )
        if _remote(target, command) != "PART_OK":
            raise RuntimeError(f"Remote data part {index} was not acknowledged")

    with path.open("rb") as stream, ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for first in range(0, count, MAX_WORKERS):
            futures = []
            for index in range(first, min(first + MAX_WORKERS, count)):
                block = stream.read(CHUNK_BYTES)
                if not block:
                    raise OSError("Source ended before its verified size")
                futures.append(pool.submit(upload, index, block))
            for future in futures:
                future.result()
        if stream.read(1):
            raise OSError("Source grew after its checksum was verified")

    assemble = _remote_python(
        _ASSEMBLE, remote_file, parts_dir, str(size), str(CHUNK_BYTES),
        str(count), sha256,
    )
    result = _remote(target, assemble)
    if result != "FINAL_OK":
        raise RuntimeError(f"Remote assembly did not return FINAL_OK: {result!r}")
    return {"remote_file": remote_file, "size_bytes": size,
            "sha256": sha256, "status": "staged"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("remote_file")
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--target", choices=("cpu", "gpu"), default="cpu")
    args = parser.parse_args()
    result = stage_verified_file(args.source, args.remote_file, args.sha256,
                                 target=args.target)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
