"""Generate, but never submit, one pinned PBS allocation running several cases concurrently."""

from __future__ import annotations

import argparse
import hashlib
import re
import shlex
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from h2physics.cluster_validation import (  # noqa: E402
    PBSResources,
    ValidationCase,
    verify_source_manifest,
)
from validation.hangang_plan import CASES, PROFILES  # noqa: E402


def _remote_path(value: str, label: str) -> str:
    path = PurePosixPath(value)
    if (not path.is_absolute() or path.as_posix() != value
            or PureWindowsPath(value).drive or "\\" in value
            or any(part in {".", ".."} for part in path.parts)
            or any(char in value for char in "\n\r\x00")):
        raise ValueError(f"{label} must be a normalized absolute POSIX path")
    return value


def _pins() -> tuple[str, bytes, str, str]:
    manifest = (ROOT / "SOURCE_MANIFEST.sha256").read_bytes()
    revision = (ROOT / "SOURCE_REVISION.txt").read_text(encoding="utf-8").strip()
    plan = ROOT / "validation/hangang_plan.py"
    plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
    manifest_sha = hashlib.sha256(manifest).hexdigest()
    rows = manifest.decode("utf-8").splitlines()
    entries = [line.partition("  ") for line in rows]
    if len([row for row in entries if row[2] == "validation/hangang_plan.py"]) != 1:
        raise ValueError("Pinned source manifest must include one campaign plan")
    if next(row[0] for row in entries if row[2] == "validation/hangang_plan.py") != plan_sha:
        raise ValueError("Campaign plan bytes differ from the source manifest")
    verify_source_manifest(ROOT, revision, manifest_sha)
    return revision, manifest, manifest_sha, plan_sha


def generate_parallel_allocation(*, selected_cases, profiles, destination,
                                 queue, accounting, name, walltime,
                                 cluster_repository, cluster_plan_file,
                                 cluster_result_directory, slurm_cli_filter_comment,
                                 launcher_python="/usr/bin/python3", cpus_per_node=None):
    revision, _manifest, manifest_sha, plan_sha = _pins()
    cases = tuple(selected_cases)
    if not cases or any(type(case) is not ValidationCase for case in cases):
        raise TypeError("Select a nonempty set of pinned ValidationCase records")
    if len({case.identifier for case in cases}) != len(cases):
        raise ValueError("Selected case IDs must be unique")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise ValueError("PBS name must be a simple scheduler identifier")
    if not re.fullmatch(r"field=[A-Za-z0-9_.-]+;appl=[A-Za-z0-9_.-]+",
                        slurm_cli_filter_comment):
        raise ValueError("Supply the pinned field=...;appl=... comment format")
    repo = _remote_path(cluster_repository, "repository")
    plan = _remote_path(cluster_plan_file, "plan file")
    results = _remote_path(cluster_result_directory, "result directory")
    launcher = _remote_path(launcher_python, "system Python launcher")
    profiles = dict(profiles)
    assigned = []
    for case in cases:
        profile = profiles.get(case.profile)
        if profile is None:
            raise ValueError(f"Missing environment profile {case.profile}")
        assigned.append((case, profile))
    required_cpus = sum(profile.numerical_threads for _, profile in assigned)
    cpus = required_cpus if cpus_per_node is None else cpus_per_node
    resources = PBSResources(queue=queue, accounting=accounting, nodes=1,
                             cpus_per_node=cpus, walltime=walltime)
    if cpus < required_cpus:
        raise ValueError("CPU allocation must cover every concurrently assigned numerical thread")

    lines = [
        "#!/bin/bash", f"#PBS -N {name}", f"#PBS -q {resources.queue}",
        f"#PBS -A {resources.accounting}",
        f"#PBS -l select=1:ncpus={resources.cpus_per_node}:mpiprocs=1",
        f"#PBS -l walltime={resources.walltime}",
        f"#SBATCH --comment={slurm_cli_filter_comment}", "#PBS -j oe", "",
        "set -euo pipefail", "export PYTHONDONTWRITEBYTECODE=1",
        'export PBS_JOBID="${PBS_JOBID:-${SLURM_JOB_ID:-}}"',
        'test -n "${PBS_JOBID:-}"',
        'if [[ -z "${TMPDIR:-}" ]]; then export TMPDIR="/tmp/h2physics-${USER:-user}-${PBS_JOBID}"; fi',
        'mkdir -p -- "$TMPDIR"',
        f"cd -- {shlex.quote(repo)}",
        f"export PYTHONPATH={shlex.quote(str(PurePosixPath(repo) / 'src'))}:"
        f"{shlex.quote(str(PurePosixPath(repo) / 'scripts'))}${{PYTHONPATH:+:$PYTHONPATH}}",
        'command -v taskset >/dev/null 2>&1 || { echo "taskset is required for disjoint CPU pinning" >&2; exit 69; }',
        f"command -v {shlex.quote(launcher)} >/dev/null 2>&1",
        f"mapfile -t ALLOWED_CPUS < <({shlex.quote(launcher)} -c 'import os; print(*sorted(os.sched_getaffinity(0)), sep=\"\\n\")')",
        f"test \"${{#ALLOWED_CPUS[@]}}\" -ge {required_cpus}",
        f"PLAN={shlex.quote(plan)}", f"RESULTS={shlex.quote(results)}",
        'test -f "$PLAN"',
        f"test \"$(sha256sum -- \"$PLAN\" | cut -d ' ' -f 1)\" = {plan_sha}",
        'ALLOC="$RESULTS/${PBS_JOBID}/allocation"', 'mkdir -p -- "$RESULTS/${PBS_JOBID}"',
        'mkdir -- "$ALLOC"', 'declare -a PIDS=()', 'declare -a IDS=()', 'CPU_OFFSET=0',
    ]
    for index, (case, profile) in enumerate(assigned, 1):
        cpu_count = profile.numerical_threads
        lines += [
            f"CPUSET_{index}=\"$(printf '%s,' \"${{ALLOWED_CPUS[@]:$CPU_OFFSET:{cpu_count}}}\")\"",
            f"CPUSET_{index}=\"${{CPUSET_{index}%,}}\"",
            f"test \"$(awk -F, '{{print NF}}' <<< \"$CPUSET_{index}\")\" -eq {cpu_count}",
            f"CASE_TMP=\"$TMPDIR/h2physics-${{PBS_JOBID}}-{index}\"",
            "mkdir -- \"$CASE_TMP\"",
            "(",
            "  command -v sha256sum >/dev/null 2>&1",
            f"  test \"$(sha256sum -- {shlex.quote(profile.setup_script)})\" = {shlex.quote(profile.setup_sha256 + '  ' + profile.setup_script)}",
            f"  source {shlex.quote(profile.setup_script)}",
            f"  test \"$(sha256sum -- {shlex.quote(profile.setup_script)})\" = {shlex.quote(profile.setup_sha256 + '  ' + profile.setup_script)}",
            f"  export PBS_ARRAY_INDEX={index}",
            f"  export OMP_NUM_THREADS={cpu_count} OPENBLAS_NUM_THREADS={cpu_count}",
            f"  export MKL_NUM_THREADS={cpu_count} NUMBA_NUM_THREADS={cpu_count}",
            "  export NUMBA_CACHE_DIR=\"$CASE_TMP/numba-cache\"",
            f"  exec taskset -c \"$CPUSET_{index}\" {shlex.quote(profile.python_executable)}"
            f" -m h2physics.cluster_validation --plan \"$PLAN\" --index {index}"
            f" --expected-case {shlex.quote(case.identifier)} --expected-profile {shlex.quote(case.profile)}"
            f" --expected-plan-sha256 {plan_sha} --expected-revision {revision}"
            f" --expected-source-manifest-sha256 {manifest_sha} --results \"$RESULTS\"",
            f") > \"$ALLOC/{case.identifier}.log\" 2>&1 &",
            f"PIDS+=($!) IDS+=({shlex.quote(case.identifier)})",
            f"CPU_OFFSET=$((CPU_OFFSET+{cpu_count}))",
        ]
    lines += [
        "FAILED=0", "for i in \"${!PIDS[@]}\"; do",
        "  if wait \"${PIDS[$i]}\"; then echo \"case=${IDS[$i]} status=finished\";",
        "  else rc=$?; echo \"case=${IDS[$i]} status=failed exit=$rc\"; FAILED=1; fi",
        "done", 'echo "allocation_result_directory=$ALLOC"', "exit \"$FAILED\"", "",
    ]
    target = Path(destination)
    if target.exists():
        raise FileExistsError("Refuse to overwrite an existing allocation script")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return target, revision, manifest_sha, plan_sha, required_cpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("queue", "accounting", "name", "walltime", "destination",
                   "results", "cluster-repository", "cluster-plan-file",
                   "slurm-cli-filter-comment"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--launcher-python", default="/usr/bin/python3")
    parser.add_argument("--cpus-per-node", type=int)
    parser.add_argument("--case-id", action="append", required=True)
    args = parser.parse_args()
    by_id = {case.identifier: case for case in CASES}
    if len(set(args.case_id)) != len(args.case_id):
        parser.error("--case-id values must be unique")
    unknown = [value for value in args.case_id if value not in by_id]
    if unknown:
        parser.error("unknown --case-id value(s): " + ", ".join(unknown))
    path, revision, manifest_sha, plan_sha, cpus = generate_parallel_allocation(
        selected_cases=tuple(by_id[value] for value in args.case_id), profiles=PROFILES,
        destination=args.destination, queue=args.queue, accounting=args.accounting,
        name=args.name, walltime=args.walltime,
        cluster_repository=args.cluster_repository,
        cluster_plan_file=args.cluster_plan_file,
        cluster_result_directory=args.results,
        slurm_cli_filter_comment=args.slurm_cli_filter_comment,
        launcher_python=args.launcher_python, cpus_per_node=args.cpus_per_node,
    )
    print(f"pbs_script={path}")
    print(f"case_count={len(args.case_id)}")
    print(f"allocated_case_cpus={cpus}")
    print(f"expected_revision={revision}")
    print(f"source_manifest_sha256={manifest_sha}")
    print(f"plan_sha256={plan_sha}")
    print("submission=not_performed")


if __name__ == "__main__":
    main()
