"""Chunk-transfer a Hangang source delta and build a verified fresh remote tree."""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
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


PART_BYTES = 20_000
WORKERS = 8


def _remote(target: str, command: str) -> str:
    result = subprocess.run([*_run_args(), target, command], check=False,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
    if result.returncode:
        # A CalledProcessError embeds the complete base64 payload in its repr.
        # Report the connection failure without dumping source archive bytes.
        detail = result.stderr.strip()[-800:]
        raise RuntimeError(f"Shared {target} wrapper failed (exit {result.returncode}): {detail}")
    return result.stdout


def _path(value: str) -> str:
    path = PurePosixPath(value)
    if (not value.startswith(_remote_root() + "/")
            or path.as_posix() != value.rstrip("/")
            or any(part in {".", ".."} for part in path.parts) or "\\" in value
            or not re.fullmatch(re.escape(_remote_root()) + r"/[A-Za-z0-9._/-]+", value)):
        raise ValueError("Remote paths must be normalized below the h2physics-jobs scratch root")
    return value.rstrip("/")


def _send(target: str, parts: str, index: int, content: bytes) -> None:
    digest = hashlib.sha256(content).hexdigest()
    encoded = base64.b64encode(content).decode("ascii")
    part = f"{parts}/part-{index:06d}"
    command = (f"set -eu; if [ -e {part} ]; then test $(sha256sum {part} | cut -d ' ' -f 1) = {digest}; "
               f"else printf '%s' '{encoded}' | base64 -d > {part}.tmp; "
               f"test $(sha256sum {part}.tmp | cut -d ' ' -f 1) = {digest}; "
               f"mv -- {part}.tmp {part}; fi; printf 'part={index} sha256={digest}\\n'")
    if f"part={index} sha256={digest}" not in _remote(target, command):
        raise RuntimeError(f"Remote part receipt missing: {index}")


def _apply_code(base: str, destination: str, archive: str, digest: str) -> str:
    import json
    values = tuple(json.dumps(value) for value in (base, destination, archive, digest))
    return r'''import hashlib,json,os,re,shutil,tarfile,tempfile
from pathlib import Path,PurePosixPath
base,dest,bundle,want=VALUES
base,dest,bundle=Path(base),Path(dest),Path(bundle)
def safe(n):
 p=PurePosixPath(n)
 if not n or p.is_absolute() or p.as_posix()!=n or any(x in ('','.','..') for x in p.parts): raise ValueError('unsafe relative path')
 return p
def parse(raw):
 out={}
 for row in raw.decode().splitlines():
  h,sep,n=row.partition('  '); safe(n)
  if not sep or not re.fullmatch('[0-9a-f]{64}',h) or n in out: raise ValueError('bad manifest')
  out[n]=h
 return out
def verify(root,rev,md):
 if (root/'SOURCE_REVISION.txt').read_text().strip()!=rev: raise ValueError('revision mismatch')
 raw=(root/'SOURCE_MANIFEST.sha256').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=md: raise ValueError('manifest digest mismatch')
 expected=parse(raw); actual={}
 for p in root.rglob('*'):
  if p.is_symlink(): raise ValueError('symlink in source tree')
  if p.is_file() and p.name not in ('SOURCE_REVISION.txt','SOURCE_MANIFEST.sha256'):
   n=p.relative_to(root).as_posix(); actual[n]=hashlib.sha256(p.read_bytes()).hexdigest()
 if expected!=actual: raise ValueError('tree differs from complete manifest')
 return raw,expected
if hashlib.sha256(bundle.read_bytes()).hexdigest()!=want: raise ValueError('delta archive SHA mismatch')
if dest.exists(): raise FileExistsError('destination must not exist')
if not base.is_dir() or base==dest or base in dest.parents or dest in base.parents: raise ValueError('invalid base/destination relation')
with tarfile.open(bundle,'r:gz') as tf:
 members=tf.getmembers(); names=[m.name for m in members]
 if len(names)!=len(set(names)) or any(not m.isfile() for m in members): raise ValueError('unexpected archive member')
 for n in names:
  if n not in ('delta/metadata.json','delta/SOURCE_MANIFEST.sha256','delta/SOURCE_REVISION.txt') and not n.startswith('delta/files/'): raise ValueError('unexpected archive path')
 meta=json.load(tf.extractfile('delta/metadata.json'))
 target_manifest=tf.extractfile('delta/SOURCE_MANIFEST.sha256').read()
 target_rev=tf.extractfile('delta/SOURCE_REVISION.txt').read().decode().strip()
 old_rev=(base/'SOURCE_REVISION.txt').read_text().strip(); old_raw=(base/'SOURCE_MANIFEST.sha256').read_bytes(); old_hash=hashlib.sha256(old_raw).hexdigest()
 _,old=parse(old_raw),parse(old_raw)
 if meta.get('format')!='h2physics-hangang-delta-v1' or meta.get('base_revision')!=old_rev or meta.get('base_manifest_sha256')!=old_hash: raise ValueError('delta base pin mismatch')
 if hashlib.sha256(target_manifest).hexdigest()!=meta.get('target_manifest_sha256') or target_rev!=meta.get('target_revision'): raise ValueError('target receipts mismatch')
 new=parse(target_manifest); changed=meta.get('changed'); deleted=meta.get('deleted')
 if not isinstance(changed,dict) or not isinstance(deleted,list) or sorted(deleted)!=sorted(set(deleted)): raise ValueError('bad delta lists')
 if set(changed)!={n for n,h in new.items() if old.get(n)!=h} or set(deleted)!=set(old)-set(new): raise ValueError('delta does not cover manifest transition')
 file_members={m.name[len('delta/files/'):]:m for m in members if m.name.startswith('delta/files/')}
 if set(file_members)!=set(changed): raise ValueError('delta payload does not match changed list')
 data={}
 for n,m in file_members.items():
  safe(n); raw=tf.extractfile(m).read()
  if hashlib.sha256(raw).hexdigest()!=changed[n]: raise ValueError('changed-file digest mismatch')
  data[n]=raw
 # Independently verify the entire previous tree before copying it.
 verify(base,old_rev,old_hash)
 stage=dest.with_name(dest.name+'.staging-'+want[:12])
 if stage.exists(): raise FileExistsError('staging path already exists')
 shutil.copytree(base,stage,symlinks=True)
 try:
  for n in deleted: safe(n); (stage/n).unlink()
  for n,raw in data.items():
   p=stage/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)
  (stage/'SOURCE_REVISION.txt').write_text(target_rev+'\n')
  (stage/'SOURCE_MANIFEST.sha256').write_bytes(target_manifest)
  verify(stage,target_rev,meta['target_manifest_sha256'])
  os.rename(stage,dest)
 except BaseException:
  # Keep failed staging tree for inspection; never expose it as the verified destination.
  raise
print('verified_revision='+target_rev)
print('verified_manifest_sha256='+meta['target_manifest_sha256'])
print('verified_tree='+str(dest))
'''.replace("VALUES", "(" + ",".join(values) + ")")


def transfer_apply(package: Path, *, target: str, incoming_dir: str,
                   base_tree: str, destination_tree: str, workers: int = WORKERS) -> None:
    incoming, base, dest = map(_path, (incoming_dir, base_tree, destination_tree))
    if target not in {"cpu", "gpu"} or not 1 <= workers <= WORKERS:
        raise ValueError("Only cpu/gpu targets and up to eight transfer workers are supported")
    paths = (incoming, base, dest)
    if (len(set(paths)) != 3 or any(a.startswith(b + "/") or b.startswith(a + "/")
                                    for index, a in enumerate(paths)
                                    for b in paths[index + 1:])):
        raise ValueError("Incoming, base and destination paths must be separate")
    data = Path(package).resolve(strict=True).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    chunks = [data[i:i + PART_BYTES] for i in range(0, len(data), PART_BYTES)]
    remote_parts = f"{incoming}/parts-{digest[:12]}"
    remote_archive = f"{incoming}/delta-{digest[:12]}.tar.gz"
    _remote(target, f"set -eu; mkdir -p -- {remote_parts}")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda item: _send(target, remote_parts, *item), enumerate(chunks)))
    combine = ["set -eu", f"test ! -e {remote_archive}", f"test ! -e {remote_archive}.tmp",
               f": > {remote_archive}.tmp"]
    for index in range(len(chunks)):
        combine.append(f"cat -- {remote_parts}/part-{index:06d} >> {remote_archive}.tmp")
    combine.extend((f"test $(sha256sum {remote_archive}.tmp | cut -d ' ' -f 1) = {digest}",
                    f"mv -- {remote_archive}.tmp {remote_archive}"))
    _remote(target, "; ".join(combine))
    code = _apply_code(base, dest, remote_archive, digest)
    encoded = base64.b64encode(code.encode()).decode("ascii")
    receipt = _remote(target, f"python3 -c 'import base64;exec(base64.b64decode(\"{encoded}\"))'")
    if "verified_manifest_sha256=" not in receipt:
        raise RuntimeError("Remote complete-manifest receipt missing")
    print(receipt, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--incoming-dir", required=True)
    parser.add_argument("--base-tree", required=True)
    parser.add_argument("--destination-tree", required=True)
    parser.add_argument("--target", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args()
    transfer_apply(args.archive, target=args.target, incoming_dir=args.incoming_dir,
                   base_tree=args.base_tree, destination_tree=args.destination_tree,
                   workers=args.workers)


if __name__ == "__main__":
    main()
