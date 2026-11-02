# Incremental Hangang source snapshots

Use this only when the remote base tree is the exact previous verified snapshot.
The builder verifies the previous snapshot locally, copies current public source
bytes into a fresh manifest, and packages only changed/new files plus deletions.
The refreshed full manifest is always included.

```powershell
python scripts/prepare_hangang_delta.py `
  --base-repository .\previous-snapshot\repository `
  --destination .\delta-2026-11-01

python scripts/transfer_apply_hangang_delta.py `
  --archive .\delta-2026-11-01\delta.tar.gz `
  --incoming-dir /scratch/CLUSTER_USER/h2physics-jobs/incoming `
  --base-tree /scratch/CLUSTER_USER/h2physics-jobs/snapshots/previous/repository `
  --destination-tree /scratch/CLUSTER_USER/h2physics-jobs/snapshots/refreshed/repository `
  --target cpu
```

The receiver uses only the existing WSL `run.sh` wrapper. It checks each chunk,
the assembled archive hash, prior base revision/manifest and full base file set;
then it creates a separate staging copy, applies the delta, and checks every file
against the refreshed full manifest before atomically promoting the new tree.
Both the final destination and staging path must be new. Failed staging data is
left for inspection and is never treated as verified. This transfers code only;
it does not run tests or submit jobs. Use the full snapshot transfer when the
previous remote tree cannot be proven to match the supplied base snapshot.
