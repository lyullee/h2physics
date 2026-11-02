# Byte-pinned Hangang worktree snapshots

Use `scripts/prepare_hangang_worktree_snapshot.py` when an authorized remote
contract must include current uncommitted code. The script records the current
Git `HEAD` as the base revision and uses a generated SHA-256 source manifest to
identify the exact copied worktree bytes. The revision alone does not identify
uncommitted changes; always retain the archive SHA-256 and manifest SHA-256.

```powershell
python scripts/prepare_hangang_worktree_snapshot.py `
  --destination 'C:\work\hydrogen-hangang-snapshots\run-2026-11-01'
```

The destination parent must already exist, the destination must be new, and the
destination must be outside the repository. The output contains
`repository/` plus `source.tar.gz`. Before writing either, the script applies
the existing GitHub-bound content-hygiene audit, selects tracked and
non-ignored working-tree files, rejects symlinks and reserved campaign receipt
names, writes `SOURCE_REVISION.txt` and `SOURCE_MANIFEST.sha256`, and verifies
all bytes against that manifest. Ignored acquisition caches such as `data/raw`
are intentionally excluded; a case that reads such a source needs its own
rights-bound receipt and an independently verified remote source attachment.

After transferring the archive through the already-open authorized KISTI
connection, verify the archive digest, extracted file set, manifest digest and
every manifest entry on the remote tree. Only then generate a campaign using
that pinned tree's absolute POSIX repository and plan paths. `--destination`
generation and remote source verification do not submit a job. Preserve the
snapshot directory and all receipts alongside campaign scripts and terminal
case results.

The source-manifest check is a content-integrity gate, not a scientific test,
license grant, rights review or model qualification. Raw external data remains
outside code snapshots unless separately cleared and deliberately staged.

For parallel chunk transfer, `scripts/transfer_hangang_snapshot.py` sends only
through the existing `run.sh` WSL wrapper and permits at most twelve workers:

```powershell
python scripts/transfer_hangang_snapshot.py `
  --archive 'C:\work\hydrogen-hangang-snapshots\run-2026-11-01\source.tar.gz' `
  --target cpu `
  --incoming-dir '/scratch/CLUSTER_USER/h2physics-jobs/incoming-run-2026-11-01' `
  --verified-dir '/scratch/CLUSTER_USER/h2physics-jobs/verified-run-2026-11-01'
```

Existing parts are reused only when their remote byte count and SHA-256 match;
otherwise the helper stops without overwriting them. It verifies the assembled
archive size/digest, extracts only to a new tree, then calls the project's
source-manifest verifier remotely. It does not submit or wait for a scheduler
job.
