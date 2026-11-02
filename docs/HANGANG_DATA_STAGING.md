# Checksum-pinned Hangang data staging

Use `scripts/stage_verified_data_hangang.py` to stage one already acquired,
rights-reviewed data file through the user's existing Hangang `run.sh` shared
connection. It transfers fixed 16 KiB pieces concurrently, verifies each remote
piece, assembles through an atomic same-filesystem link, and checks the final
SHA-256 before reporting success. A rerun accepts an already present file only
when its size and digest match exactly.

The remote destination must be beneath
`/scratch/CLUSTER_USER/h2physics-jobs/data/`. The tool uses only the `cpu` or `gpu`
selector passed to `run.sh`; it does not open a new SSH connection, authenticate,
submit a scheduler job, or place raw data in a source archive. A failed transfer
leaves its checksum-scoped parts directory for inspection and safe continuation.

Example for a file whose repository receipt has already been reviewed:

```powershell
.\.venv\Scripts\python.exe scripts/stage_verified_data_hangang.py `
  data\raw\ml-hydpark-screening\0.0.5\ML-HYDPARK_v0.0.5.csv `
  /scratch/CLUSTER_USER/h2physics-jobs/data/ml-hydpark-screening/0.0.5/ML-HYDPARK_v0.0.5.csv `
  --sha256 41d1549a0b0b72355184cebe19d8da0b1ed18f87c7e1bf5527073a4246421af0 `
  --target cpu
```

Stage each auxiliary metadata snapshot as a separate file with its own recorded
size and SHA-256. Dataset license, DOI, attribution and allowed use remain in its
source manifest; remote byte identity alone does not extend the source grant.
