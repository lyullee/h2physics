# Stage PEM ripple source for Hangang

The Hangang bridge case reads the selected member gzip at:

`/scratch/CLUSTER_USER/h2physics-jobs/data/pem-ripple/2/PEM1_Initial.csv.gz`

The stager verifies the complete local parent ZIP (90,759,411 bytes; SHA-256
`47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab`) and extracts
only `PEM_ripple_degradation_data/IV_curves/PEM1/PEM1_Initial.csv`. That member is
915,460 bytes with SHA-256
`a054dad7a1d5ce1f2154b60a79a1adea4f84d5ec00e23c12ca72639ffcddcf0d`, header
`current_A,voltage_V,step_index` and 20,040 rows. Deterministic gzip yields 100,159
bytes with SHA-256
`46e2e7e08cb5d7eb371df30f7b3b6ee221f9c1e5ae46cd40c544b3c21bccfa90`.

Only this gzip is transferred, in six 18 KiB-or-smaller parts. The stager keeps at most
16 `wsl.exe` wrapper calls in flight. Each remote part is hash-checked before retention;
assembly checks every part receipt and the final gzip size/SHA. The case checks the
source-bound member bridge only: the full ZIP is not staged to Hangang, and no physical
accuracy is established.
The destination is never overwritten: an exact existing copy is skipped, and any
different existing file causes an error. Interrupted transfers can resume from valid
parts; mismatching parts are refused.

From the repository folder in Windows PowerShell, run:

```powershell
python scripts/stage_pem_ripple_hangang.py --target cpu
```

For every remote operation, the utility invokes the exact wrapper form
`wsl.exe -d Ubuntu-22.04 -u lyullee --exec /bin/bash /home/CLUSTER_USER/.cache/nbcp-hangang/run.sh TARGET 'command'`.
It uses the already open Hangang CPU shared connection, performs no fresh SSH or
authentication, and submits no calculation job. It stops if that shared connection is
unavailable. Use `--target gpu` only if the same scratch path is shared there.

The Hangang plan overrides the case's workstation `source_path` with this staged remote
member path for case `pem-ripple-iv-to-hydrogen-stack-diagnostic`. Staging supplies source
bytes only; it does not run the case or imply scientific validation.

