# Concurrent cases in one Hangang allocation

`generate_hangang_parallel_allocation.py` creates one PBS script for an explicit
set of cases from the current pinned plan. It is useful when an array request is
denied but a single allocation can reserve enough CPUs. It never submits.

```powershell
python scripts/generate_hangang_parallel_allocation.py `
  --queue QUEUE --accounting ACCOUNT --name h2-batch --walltime 02:00:00 `
  --destination .\campaigns\h2-parallel.pbs `
  --results /scratch/CLUSTER_USER/h2physics-jobs/results `
  --cluster-repository /scratch/CLUSTER_USER/h2physics-jobs/snapshots/source/repository `
  --cluster-plan-file /scratch/CLUSTER_USER/h2physics-jobs/snapshots/source/repository/validation/hangang_plan.py `
  --slurm-cli-filter-comment 'field=FIELD;appl=APPLICATION' `
  --case-id CASE_ONE --case-id CASE_TWO
```

The generator allocates the sum of selected profile thread counts, unless a
larger CPU count is requested. Inside the allocation it obtains the job's
allowed CPU IDs and pins every worker process to a disjoint CPU set with
`taskset`. Each case runs in its own subshell, profile environment, temporary
directory, log and `cluster_validation` result directory. Each child repeats
the source-manifest, revision, plan, profile and setup-script checks and writes
its own outcome receipt. A case failure does not prevent the other selected
cases from finishing; the overall PBS job exits nonzero if any child fails.

The worker refuses to launch if the allowed CPU set is too small or `taskset` is
unavailable. Profile setup scripts are checked before and after sourcing. The
generator does not change `write_pbs_array`, run validation locally, or submit a
job; resource admission remains the scheduler's decision.
