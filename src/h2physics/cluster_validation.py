"""Python case contracts and unsubmitted PBS arrays for deferred validation.

Case discovery and script creation do not run a model or connect to a cluster.
Queue, accounting, interpreter and resources must be supplied for the actual site.
"""

import dataclasses
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time
import traceback
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _identifier(value, name):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Declare a simple {name}; whitespace/shell directives are not allowed")


_SLURM_CLI_FILTER_COMMENT = re.compile(
    r"field=[A-Za-z0-9_.-]+;appl=[A-Za-z0-9_.-]+"
)


def _slurm_cli_filter_comment(value):
    if value is not None and (
        not isinstance(value, str) or not _SLURM_CLI_FILTER_COMMENT.fullmatch(value)
    ):
        raise ValueError(
            "Slurm CLI-filter comment must contain only field=<token>;appl=<token>"
        )


@dataclass(frozen=True, slots=True)
class ValidationCase:
    identifier: str
    profile: str
    entrypoint: str
    parameters: Mapping = field(default_factory=dict)
    invariants: tuple[str, ...] = ()

    def __post_init__(self):
        _identifier(self.identifier, "case identifier")
        _identifier(self.profile, "environment profile")
        module, separator, function = self.entrypoint.partition(":")
        if (separator != ":" or not module or not function.isidentifier()
                or any(not p.isidentifier() for p in module.split("."))):
            raise ValueError("A case entrypoint is an explicit module:function")
        if not isinstance(self.parameters, Mapping) or any(not isinstance(k, str) for k in self.parameters):
            raise TypeError("Case parameters use a Python mapping with named arguments")
        if "work_directory" in self.parameters:
            raise ValueError("The scheduler supplies the evidence work_directory")
        if not self.invariants or any(not isinstance(v, str) or not v.strip() for v in self.invariants):
            raise ValueError("Declare the case acceptance invariants before execution")
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, "invariants", tuple(self.invariants))


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    accepted: bool
    metrics: Mapping = field(default_factory=dict)
    limitations: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.accepted) is not bool or not isinstance(self.metrics, Mapping):
            raise TypeError("A validator must return explicit acceptance and named metrics")
        if any(not isinstance(k, str) for k in self.metrics) or (self.accepted and not self.metrics):
            raise ValueError("Accepted cases require named numerical/evidence metrics")
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
        object.__setattr__(self, "limitations", tuple(self.limitations))


@dataclass(frozen=True, slots=True)
class ClusterProfile:
    name: str
    python_executable: str
    setup_script: str
    setup_sha256: str
    numerical_threads: int

    def __post_init__(self):
        _identifier(self.name, "profile name")
        for value in (self.python_executable, self.setup_script):
            remote_path = PurePosixPath(value) if isinstance(value, str) else None
            if (remote_path is None or not remote_path.is_absolute()
                    or remote_path.as_posix() != value or ".." in remote_path.parts
                    or "\\" in value or any(char in value for char in "\n\r\x00")):
                raise ValueError("Supply absolute cluster POSIX interpreter/setup paths")
        if not isinstance(self.setup_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.setup_sha256
        ):
            raise ValueError("Pin the exact setup-script SHA-256 for this environment profile")
        if (isinstance(self.numerical_threads, bool) or not isinstance(self.numerical_threads, int)
                or self.numerical_threads < 1):
            raise ValueError("Supply the numerical thread budget per case")


@dataclass(frozen=True, slots=True)
class PBSResources:
    queue: str
    accounting: str
    nodes: int
    cpus_per_node: int
    walltime: str
    project: str | None = None

    def __post_init__(self):
        _identifier(self.queue, "actual queue")
        _identifier(self.accounting, "actual PBS accounting string")
        if self.project is not None:
            _identifier(self.project, "project name")
        for value in (self.nodes, self.cpus_per_node):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Supply positive integer resource counts")
        if self.nodes != 1:
            raise ValueError("This independent-case worker is single-node; it does not invent an MPI solver")
        if not re.fullmatch(r"\d{2,4}:[0-5]\d:[0-5]\d", self.walltime) or set(self.walltime) <= {"0", ":"}:
            raise ValueError("Supply a positive site-admitted HH:MM:SS walltime")


def collect_cases(*modules: str) -> tuple[ValidationCase, ...]:
    """Import metadata-only case catalogs; never call a scientific entrypoint."""
    cases = []
    for module in modules:
        values = importlib.import_module(module).cases()
        for value in values:
            if type(value) is not ValidationCase:
                raise TypeError("Case catalogs must return actual ValidationCase records")
            cases.append(value)
    if not cases or len({v.identifier for v in cases}) != len(cases):
        raise ValueError("Declare nonempty unique deferred cases")
    return tuple(cases)


def _source_manifest_member(relative: str) -> bool:
    """Share receipt/runtime exclusions between full manifests and deltas."""
    parts = PurePosixPath(relative).parts
    return (".git" not in parts and "__pycache__" not in parts
            and relative not in {"SOURCE_MANIFEST.sha256", "SOURCE_REVISION.txt"}
            and not relative.startswith(("artifacts/", ".venv/", "venv/")))


def source_manifest(repository: Path) -> bytes:
    """Hash every tracked source/document file without requiring Git on workers."""
    root = Path(repository).resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        # Snapshot receipts are generated per campaign; newline conversion must not
        # make a source checkout appear different from its pinned payload.
        if not _source_manifest_member(relative):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {relative}")
    return ("\n".join(rows) + "\n").encode("utf-8")


def verify_source_manifest(repository: Path, expected_revision: str,
                           expected_manifest_sha256: str) -> None:
    """Require matching snapshot receipt, manifest hash and every listed file hash."""
    root = Path(repository).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_revision):
        raise ValueError("Expected revision must be a full lowercase Git object id")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256):
        raise ValueError("Expected source manifest must be a SHA-256 digest")
    receipt = root / "SOURCE_REVISION.txt"
    manifest_path = root / "SOURCE_MANIFEST.sha256"
    if not receipt.is_file() or receipt.read_text(encoding="utf-8").strip() != expected_revision:
        raise ValueError("Source snapshot revision receipt differs from campaign pin")
    if not manifest_path.is_file():
        raise ValueError("Source snapshot manifest is missing")
    manifest = manifest_path.read_bytes()
    if hashlib.sha256(manifest).hexdigest() != expected_manifest_sha256:
        raise ValueError("Source snapshot manifest does not match campaign pin")
    seen = set()
    expected_by_path = {}
    for row in manifest.decode("utf-8").splitlines():
        digest, separator, relative = row.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Source manifest contains an invalid row")
        relative_path = PurePosixPath(relative)
        if (not relative or relative_path.is_absolute()
                or any(part in {"", ".", ".."} for part in relative_path.parts)
                or relative_path.as_posix() != relative):
            raise ValueError("Source manifest paths must be normalized repository-relative POSIX paths")
        if relative in expected_by_path:
            raise ValueError("Source manifest contains a duplicate path")
        expected_by_path[relative] = digest
        candidate = (root / relative).resolve()
        if root not in candidate.parents or relative in seen or not candidate.is_file():
            raise ValueError("Source manifest contains an invalid or duplicate path")
        seen.add(relative)
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Pinned source file changed: {relative}")
    actual_by_path = {
        row.partition("  ")[2]: row.partition("  ")[0]
        for row in source_manifest(root).decode("utf-8").splitlines()
    }
    if actual_by_path != expected_by_path:
        raise ValueError("Source snapshot file set differs from the pinned manifest")


def write_pbs_array(cases, profiles, resources: PBSResources, *, destination,
                    cluster_repository: str, cluster_plan_file: str, cluster_result_directory: str,
                    expected_revision: str, expected_source_manifest_sha256: str,
                    expected_plan_sha256: str, name: str,
                    slurm_cli_filter_comment: str | None = None) -> Path:
    """Write, never submit, one whole scientific case per PBS worker.

    Multiple cases use an array; a single case uses a regular PBS job because some
    schedulers reject the degenerate array range ``1-1``. Resource/queue/account
    admission and the cluster environment are not verified by producing this text.
    Case definitions are a Python file loaded later.
    """
    _identifier(name, "batch name")
    _slurm_cli_filter_comment(slurm_cli_filter_comment)
    if not re.fullmatch(r"[0-9a-f]{40}", expected_revision):
        raise ValueError("Pin an actual full Git commit before creating a cluster campaign")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_source_manifest_sha256):
        raise ValueError("Pin the complete source snapshot manifest before creating a cluster campaign")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_plan_sha256):
        raise ValueError("Pin the exact Python plan bytes before generating its scheduler array")
    cluster_paths = (cluster_repository, cluster_plan_file, cluster_result_directory)
    for value in cluster_paths:
        # These strings are interpreted by Bash on the remote POSIX host. In
        # particular, pathlib.Path follows the *generator's* host OS and can
        # silently turn a Windows path into a backslash-delimited PYTHONPATH.
        remote_path = PurePosixPath(value) if isinstance(value, str) else None
        if (remote_path is None or not remote_path.is_absolute()
                or remote_path.as_posix() != value or ".." in remote_path.parts
                or "\\" in value or any(char in value for char in "\n\r\x00")):
            raise ValueError("Supply actual absolute cluster POSIX paths")
    values = tuple(cases)
    if not values or any(type(c) is not ValidationCase for c in values):
        raise TypeError("Supply a nonempty explicit case catalog")
    if len({c.identifier for c in values}) != len(values):
        raise ValueError("Cluster case identifiers must be unique")
    profiles = dict(profiles)
    for case in values:
        profile = profiles[case.profile]
        if type(profile) is not ClusterProfile or profile.name != case.profile:
            raise ValueError("Every case requires an explicitly named interpreter profile")
        if profile.numerical_threads > resources.cpus_per_node:
            raise ValueError("Numerical threads exceed the requested node CPU allocation")
    lines = ["#!/bin/bash", f"#PBS -N {name}", f"#PBS -q {resources.queue}",
        f"#PBS -A {resources.accounting}",
        f"#PBS -l select={resources.nodes}:ncpus={resources.cpus_per_node}:mpiprocs=1",
        f"#PBS -l walltime={resources.walltime}"]
    if slurm_cli_filter_comment is not None:
        # PBS ignores this scheduler comment; Slurm deployments can consume the
        # same pinned value through their CLI-filter/showappl integration.
        lines.append(f"#SBATCH --comment={slurm_cli_filter_comment}")
    if len(values) > 1:
        lines.append(f"#PBS -J 1-{len(values)}")
    lines.append("#PBS -j oe")
    if resources.project is not None:
        lines.append(f"#PBS -P {resources.project}")
    lines += [
        "",
        "set -euo pipefail",
        # Imported modules live inside the immutable source tree. Prevent the
        # worker interpreter from creating unmanifested __pycache__ files
        # before the source-manifest currentness check runs.
        "export PYTHONDONTWRITEBYTECODE=1",
        'export PBS_JOBID="${PBS_JOBID:-${SLURM_JOB_ID:-}}"',
        'export PBS_ARRAY_INDEX="${PBS_ARRAY_INDEX:-${SLURM_ARRAY_TASK_ID:-}}"',
        'if [[ -z "${TMPDIR:-}" ]]; then '
        'export TMPDIR="/tmp/h2physics-${USER:-user}-${PBS_JOBID:-$$}"; fi',
        'mkdir -p -- "$TMPDIR"',
        'test -n "${PBS_JOBID:-}"',
    ]
    if len(values) > 1:
        lines.append('test -n "${PBS_ARRAY_INDEX:-}"')
    else:
        lines.append("export PBS_ARRAY_INDEX=1")
    lines += [
        f"cd -- {shlex.quote(cluster_repository)}",
        f'export PYTHONPATH={shlex.quote(str(PurePosixPath(cluster_repository) / "src"))}:'
        f'{shlex.quote(str(PurePosixPath(cluster_repository) / "scripts"))}'
        '${PYTHONPATH:+:$PYTHONPATH}',
        'case "$PBS_ARRAY_INDEX" in',
    ]
    for index, case in enumerate(values, 1):
        profile = profiles[case.profile]
        setup_command = shlex.quote(profile.setup_script)
        setup_record = shlex.quote(f"{profile.setup_sha256}  {profile.setup_script}")
        lines += [f"  {index})",
            '    command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required for setup pin verification" >&2; exit 69; }',
            f"    test \"$(sha256sum -- {setup_command})\" = {setup_record}",
            f"    source {setup_command}",
            f"    test \"$(sha256sum -- {setup_command})\" = {setup_record}",
            f"    export OMP_NUM_THREADS={profile.numerical_threads}",
            f"    export OPENBLAS_NUM_THREADS={profile.numerical_threads}",
            f"    export MKL_NUM_THREADS={profile.numerical_threads}",
            f"    export NUMBA_NUM_THREADS={profile.numerical_threads}",
            '    export NUMBA_CACHE_DIR="${TMPDIR:?compute-local TMPDIR required}/h2physics-numba-${PBS_JOBID}-${PBS_ARRAY_INDEX}"',
            f"    exec {shlex.quote(profile.python_executable)} -m h2physics.cluster_validation"
            f" --plan {shlex.quote(cluster_plan_file)} --index {index}"
            f" --expected-case {shlex.quote(case.identifier)} --expected-profile {shlex.quote(case.profile)}"
            f" --expected-plan-sha256 {expected_plan_sha256}"
            f" --expected-revision {expected_revision}"
            f" --expected-source-manifest-sha256 {expected_source_manifest_sha256}"
            f" --results {shlex.quote(cluster_result_directory)}",
            "    ;;"]
    lines += ['  *) echo "Unknown PBS array index" >&2; exit 64 ;;', "esac", ""]
    path = Path(destination)
    if path.exists():
        raise FileExistsError("Refuse to overwrite an existing campaign script")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _portable(value):
    """Log values without pickle or converting missing/nonfinite values to zero."""
    if dataclasses.is_dataclass(value):
        return {f.name: _portable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(k): _portable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": str(value)}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if type(value).__module__.split(".")[0] == "numpy":
        return _portable(value.tolist() if hasattr(value, "tolist") else value.item())
    raise TypeError("Persist native objects through a case-specific audit; metrics need portable values")


def _file_sha256(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _compile_package_sources(repository: Path) -> int:
    """Syntax-check every pinned package Python file without importing it."""
    source_root = repository / "src" / "h2physics"
    sources = tuple(sorted(source_root.rglob("*.py")))
    if not sources:
        raise RuntimeError("Pinned package source tree has no Python files")
    for path in sources:
        compile(path.read_bytes(), str(path), "exec", dont_inherit=True)
    return len(sources)


def _main():
    import argparse
    import runpy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--expected-case", required=True)
    parser.add_argument("--expected-profile", required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--expected-source-manifest-sha256")
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    # The explicit snapshot pin is the authoritative source identity in Git-free
    # worker mode as well as the fallback expected revision for legacy jobs.
    revision = args.expected_revision
    if not os.environ.get("PBS_JOBID") or not os.environ.get("PBS_ARRAY_INDEX"):
        raise SystemExit("Validation execution is deferred to an explicit scheduler allocation")
    if (not re.fullmatch(r"[A-Za-z0-9_.\[\]-]+", os.environ["PBS_JOBID"])
            or not os.environ["PBS_ARRAY_INDEX"].isdigit()
            or int(os.environ["PBS_ARRAY_INDEX"]) != args.index):
        raise SystemExit("Invalid/misaligned scheduler case identity")
    if args.expected_source_manifest_sha256:
        if not re.fullmatch(r"[0-9a-f]{64}", args.expected_source_manifest_sha256):
            raise SystemExit("Invalid explicit source-manifest SHA-256")
        repository = Path(__file__).resolve().parents[2]
        try:
            verify_source_manifest(repository, args.expected_revision,
                                   args.expected_source_manifest_sha256)
        except (OSError, UnicodeError, ValueError) as error:
            raise SystemExit(str(error)) from error
    else:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        if revision != args.expected_revision:
            raise SystemExit("Cluster source revision differs from the explicit campaign revision")
        if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip():
            raise SystemExit("Tracked cluster source changed after the campaign revision")
        repository = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
        revision = args.expected_revision
    if Path(__file__).resolve() != (repository/"src/h2physics/cluster_validation.py").resolve():
        raise SystemExit("Worker imported another installed checkout; select the pinned source environment")
    plan = args.plan.resolve()
    if hashlib.sha256(plan.read_bytes()).hexdigest() != args.expected_plan_sha256:
        raise SystemExit("Python campaign plan bytes changed after scheduler generation")
    values = runpy.run_path(str(plan))
    cases = tuple(values["CASES"])
    by_identifier = {case.identifier: case for case in cases
                     if type(case) is ValidationCase}
    if len(by_identifier) != len(cases):
        raise SystemExit("Pinned plan contains duplicate or invalid case identities")
    case = by_identifier.get(args.expected_case)
    if case is None or case.profile != args.expected_profile:
        raise SystemExit("Campaign case/profile is absent from the pinned plan")
    profiles = values["PROFILES"]
    profile = profiles[case.profile]
    if Path(sys.executable).absolute() != Path(profile.python_executable).absolute():
        raise SystemExit("Actual worker interpreter differs from the selected native profile")
    if _file_sha256(Path(profile.setup_script)) != profile.setup_sha256:
        raise SystemExit("Environment setup script differs from the selected profile SHA-256")
    output = (args.results/str(os.environ["PBS_JOBID"])/case.identifier).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"case": case.identifier, "profile": case.profile, "status": "running",
        "revision": revision, "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
        "setup_script_sha256": profile.setup_sha256,
        "python": sys.version, "executable": sys.executable, "environment_prefix": sys.prefix,
        "pbs_job_id": os.environ["PBS_JOBID"],
        "array_index": os.environ["PBS_ARRAY_INDEX"], "invariants": case.invariants,
        "case_working_directory": str(output),
        "versions": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}}
    (output/"attempt.json").write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
    start = time.perf_counter()
    exitcode = 1
    original_directory = Path.cwd()
    try:
        # One worker process owns one case. Native relative outputs must not
        # collide in the shared checkout when array jobs run concurrently.
        if str(repository) not in sys.path:
            sys.path.insert(0, str(repository))
        os.chdir(output)
        report["package_python_syntax_files_checked"] = _compile_package_sources(repository)
        module, function = case.entrypoint.split(":")
        result = getattr(importlib.import_module(module), function)(
            work_directory=output, **case.parameters)
        if type(result) is not ValidationOutcome:
            raise TypeError("The case did not return explicit ValidationOutcome acceptance")
        report.update(status="passed" if result.accepted else "rejected",
                      metrics=_portable(result.metrics), limitations=_portable(result.limitations))
        exitcode = 0 if result.accepted else 1
    except BaseException as error:
        report.update(status="failed", exception_type=type(error).__name__,
                      exception_message=str(error), traceback=traceback.format_exc())
    finally:
        os.chdir(original_directory)
        report["seconds"] = time.perf_counter()-start
        temporary = output/"outcome.tmp"
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False),
                             encoding="utf-8", newline="\n")
        os.replace(temporary, output/"outcome.json")
    return exitcode


if __name__ == "__main__":
    # `python -m` executes this file as `__main__`; expose that same module under
    # its importable package name before a case imports ValidationOutcome.
    _executing_module = sys.modules[__name__]
    sys.modules["h2physics.cluster_validation"] = _executing_module
    _package = sys.modules.get("h2physics")
    if _package is not None:
        setattr(_package, "cluster_validation", _executing_module)
    raise SystemExit(_executing_module._main())
