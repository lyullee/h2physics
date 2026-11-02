"""Read-only reconciliation of explicitly selected deferred cluster records.

Record consistency is distinct from numerical and experimental qualification.
This collector never imports a case entrypoint, runs a model or contacts PBS.
"""

import hashlib
import json
import math
import os
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from .cluster_validation import ClusterProfile, ValidationCase


def _hash(value, length, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{"+str(length)+"}", value):
        raise ValueError(f"Declare the complete lowercase {label}")


def _integer(value, label):
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _package_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Package identity cannot be empty")
    return re.sub(r"[-_.]+", "-", value).lower()


def _versions(values):
    if not isinstance(values, Mapping):
        raise TypeError("Expected native versions use a named mapping")
    result = {}
    for name, version in values.items():
        key = _package_name(name)
        if key in result or not isinstance(version, str) or not version.strip():
            raise ValueError("Package aliases must be unique and exact versions nonempty")
        result[key] = version
    return MappingProxyType(result)


def _freeze(value):
    """Freeze parsed JSON containers without consuming the Python call stack."""
    if not isinstance(value, (dict, list)):
        return value
    pending, frozen = [(value, False)], {}
    while pending:
        item, ready = pending.pop()
        if id(item) in frozen:
            continue
        if ready:
            def child(element):
                return frozen[id(element)] if isinstance(element, (dict, list)) else element
            result = (MappingProxyType({key: child(element) for key, element in item.items()})
                      if isinstance(item, dict) else tuple(child(element) for element in item))
            frozen[id(item)] = result
        else:
            pending.append((item, True))
            children = item.values() if isinstance(item, dict) else item
            pending.extend((element, False) for element in children if isinstance(element, (dict, list)))
    return frozen[id(value)]


def _cluster_path(value):
    if not isinstance(value, str) or any(c in value for c in ("\0", "\n", "\r", "\\")):
        raise ValueError("Supply the actual absolute canonical cluster POSIX path")
    path = PurePosixPath(value)
    if (not path.is_absolute() or path.as_posix() != value or value == "/"
            or ".." in path.parts):
        raise ValueError("Cluster paths must be canonical absolute POSIX paths below root")


@dataclass(frozen=True, slots=True)
class RuntimeExpectation:
    profile: ClusterProfile
    python_version: str
    environment_prefix: str
    package_versions: Mapping[str, str]

    def __post_init__(self):
        if type(self.profile) is not ClusterProfile:
            raise TypeError("Bind the actual ClusterProfile")
        if not isinstance(self.python_version, str) or not self.python_version.strip():
            raise ValueError("Declare the expected complete sys.version record")
        _cluster_path(self.environment_prefix)
        versions = _versions(self.package_versions)
        if not versions:
            raise ValueError("Declare at least the exact critical native package versions")
        object.__setattr__(self, "package_versions", versions)


@dataclass(frozen=True, slots=True)
class CampaignExpectation:
    identifier: str
    cases: tuple[ValidationCase, ...]
    runtimes: Mapping[str, RuntimeExpectation]
    job_ids_by_case: Mapping[str, str]
    revision: str
    plan_sha256: str
    cluster_results_root: str

    def __post_init__(self):
        if not isinstance(self.identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", self.identifier):
            raise ValueError("Declare a simple campaign identifier")
        _hash(self.revision, 40, "Git revision")
        _hash(self.plan_sha256, 64, "plan SHA-256")
        _cluster_path(self.cluster_results_root)
        cases = tuple(self.cases)
        if not cases or any(type(case) is not ValidationCase for case in cases):
            raise TypeError("Use the actual ordered ValidationCase metadata objects")
        identifiers = {case.identifier for case in cases}
        if len(identifiers) != len(cases):
            raise ValueError("Campaign case identifiers must be unique")
        runtimes, jobs = dict(self.runtimes), dict(self.job_ids_by_case)
        if set(jobs) != identifiers:
            raise ValueError("Explicit job selection must cover exactly the expected cases")
        for job in jobs.values():
            if not isinstance(job, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\[\]-]*", job):
                raise ValueError("Supply an actual simple PBS job/array identifier")
        used = {case.profile for case in cases}
        if used-set(runtimes):
            raise ValueError("Every used profile needs an explicit runtime expectation")
        for name in used:
            if type(runtimes[name]) is not RuntimeExpectation or runtimes[name].profile.name != name:
                raise ValueError("Runtime expectations must match actual profile names")
        object.__setattr__(self, "cases", cases)
        object.__setattr__(self, "runtimes", MappingProxyType(runtimes))
        object.__setattr__(self, "job_ids_by_case", MappingProxyType(jobs))


@dataclass(frozen=True, slots=True)
class CollectionBudgets:
    maximum_metadata_bytes: int
    maximum_files_per_case: int
    maximum_artifact_bytes_per_case: int
    maximum_paths_per_case: int

    def __post_init__(self):
        for name in ("maximum_metadata_bytes", "maximum_files_per_case",
                     "maximum_artifact_bytes_per_case", "maximum_paths_per_case"):
            _integer(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class ArtifactDigest:
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    case: ValidationCase
    expected_array_index: int
    expected_job_id: str
    directory: Path
    record_status: str
    diagnostics: tuple[str, ...]
    attempt: Mapping | None
    outcome: Mapping | None
    artifacts: tuple[ArtifactDigest, ...]


@dataclass(frozen=True, slots=True)
class CampaignEvidence:
    expectation: CampaignExpectation
    results_root: Path
    cases: tuple[CaseEvidence, ...]
    counts: Mapping[str, int]
    all_records_complete: bool
    all_cases_reported_passed: bool
    scientific_qualification_established: bool = field(default=False, init=False)
    execution_performed_by_collector: bool = field(default=False, init=False)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate metadata key: {key}")
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError(f"Nonstandard nonfinite metadata number: {value}")


def _finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Overflowed JSON number; original worker labels nonfinite values explicitly")
    return number


def _inside(path, root):
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("A result path escapes the selected result directory")
    return resolved


def _metadata(path, root, limit):
    path = _inside(path, root)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Worker metadata is not a bounded regular file")
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError("Worker metadata changed beyond its size budget")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                       parse_constant=_bad_constant, parse_float=_finite_json_float)
    if not isinstance(value, dict):
        raise ValueError("Worker report must be a named record")
    return value, hashlib.sha256(raw).hexdigest()


def _artifacts(directory, budgets):
    """Hash bytes only: never unpickle, import or interpret native result files."""
    files, total = [], 0

    def paths():
        pending, seen = [directory], 0
        while pending:
            parent = pending.pop()
            with os.scandir(parent) as entries:
                for entry in entries:
                    seen += 1
                    if seen > budgets.maximum_paths_per_case:
                        raise ValueError("Case evidence exceeds the traversal-path budget")
                    path = Path(entry.path)
                    if entry.is_symlink():
                        raise ValueError("Symbolic links are not portable case evidence")
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(_inside(path, directory))
                    else:
                        yield path

    for path in paths():
        if path.is_symlink():
            raise ValueError("Symbolic links are not portable case evidence")
        resolved = _inside(path, directory)
        if resolved.is_dir():
            continue
        if not resolved.is_file():
            raise ValueError("Native evidence must be a regular file")
        if len(files) >= budgets.maximum_files_per_case:
            raise ValueError("Case evidence exceeds the file-count budget")
        before = resolved.stat()
        if total+before.st_size > budgets.maximum_artifact_bytes_per_case:
            raise ValueError("Case evidence exceeds the byte budget")
        digest, consumed = hashlib.sha256(), 0
        with resolved.open("rb") as stream:
            while block := stream.read(1024*1024):
                consumed += len(block)
                if total+consumed > budgets.maximum_artifact_bytes_per_case:
                    raise ValueError("Changing evidence exceeds the byte budget")
                digest.update(block)
        after = resolved.stat()
        if (consumed != before.st_size or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns):
            raise ValueError("Evidence changed while being collected")
        total += consumed
        files.append(ArtifactDigest(path.relative_to(directory).as_posix(), consumed, digest.hexdigest()))
    return tuple(sorted(files, key=lambda item: item.relative_path))


def _identity(record, case, index, job, expectation):
    runtime = expectation.runtimes[case.profile]
    expected = {"case": case.identifier, "profile": case.profile,
        "revision": expectation.revision, "plan_sha256": expectation.plan_sha256,
        "pbs_job_id": job, "array_index": str(index),
        "executable": runtime.profile.python_executable,
        "setup_script_sha256": runtime.profile.setup_sha256,
        "python": runtime.python_version, "environment_prefix": runtime.environment_prefix,
        "case_working_directory": str(PurePosixPath(expectation.cluster_results_root)/job/case.identifier)}
    for name, value in expected.items():
        if record.get(name) != value:
            raise ValueError(f"Worker identity differs from the selected campaign: {name}")
    if record.get("invariants") != list(case.invariants):
        raise ValueError("Recorded acceptance invariants differ from the pinned case")
    if not all(isinstance(record.get(name), str) and record[name].strip()
               for name in ("python", "environment_prefix", "case_working_directory")):
        raise ValueError("Original worker interpreter/environment/directory evidence is missing")
    versions = _versions(record.get("versions"))
    for name, expected_version in runtime.package_versions.items():
        if versions.get(name) != expected_version:
            raise ValueError(f"Critical native package version differs: {name}")


def _collect_case(expectation, case, index, root, budgets):
    job = expectation.job_ids_by_case[case.identifier]
    folder = root/job/case.identifier
    attempt, outcome, artifacts = None, None, ()
    if not folder.exists():
        return CaseEvidence(case, index, job, folder, "missing", ("Selected case directory is absent",),
                            None, None, ())
    try:
        directory = _inside(folder, root)
        if directory != folder or folder.is_symlink() or not directory.is_dir():
            raise ValueError("Selected case directory is redirected or not a directory")
        if not (directory/"attempt.json").exists():
            return CaseEvidence(case, index, job, directory, "incomplete", ("Attempt record is absent",),
                                None, None, ())
        attempt, attempt_sha = _metadata(directory/"attempt.json", directory, budgets.maximum_metadata_bytes)
        _identity(attempt, case, index, job, expectation)
        if attempt.get("status") != "running":
            raise ValueError("Initial worker attempt is not the original running record")
        if not (directory/"outcome.json").exists():
            return CaseEvidence(case, index, job, directory, "incomplete", ("No atomically completed outcome",),
                                _freeze(attempt), None, ())
        outcome, outcome_sha = _metadata(directory/"outcome.json", directory, budgets.maximum_metadata_bytes)
        _identity(outcome, case, index, job, expectation)
        if any(outcome.get(name) != value for name, value in attempt.items() if name != "status"):
            raise ValueError("Final report changed the initial worker identity/environment")
        status = outcome.get("status")
        if status not in {"passed", "rejected", "failed"}:
            raise ValueError("Outcome has no supported terminal case status")
        seconds = outcome.get("seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, (float, int)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Completed case has no finite elapsed-time record")
        if status == "passed" and (not isinstance(outcome.get("metrics"), dict) or not outcome["metrics"]):
            raise ValueError("A reported passing case has no named acceptance metrics")
        if status in {"passed", "rejected"} and not isinstance(outcome.get("limitations"), list):
            raise ValueError("The case's declared limitations were not retained")
        if status == "failed":
            if (not isinstance(outcome.get("exception_message"), str)
                    or not all(isinstance(outcome.get(key), str) and outcome[key]
                               for key in ("exception_type", "traceback"))):
                raise ValueError("Failed case is missing its original error/traceback")
        artifacts = _artifacts(directory, budgets)
        hashes = {record.relative_path: record.sha256 for record in artifacts}
        if hashes.get("attempt.json") != attempt_sha or hashes.get("outcome.json") != outcome_sha:
            raise ValueError("Worker records changed during artifact collection")
        if (directory/"outcome.tmp").exists():
            raise ValueError("An incomplete worker outcome is still present")
        return CaseEvidence(case, index, job, directory, status, (), _freeze(attempt),
                            _freeze(outcome), artifacts)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as error:
        return CaseEvidence(case, index, job, folder, "inconsistent", (str(error),),
                            None if attempt is None else _freeze(attempt),
                            None if outcome is None else _freeze(outcome), artifacts)


def collect_campaign_evidence(expectation: CampaignExpectation, results_root: Path, *,
                              budgets: CollectionBudgets) -> CampaignEvidence:
    """Reconcile selected existing outputs, without executing or polling cases.

    Missing/partial records are never inferred to have succeeded. Caller selects
    actual job IDs explicitly; modification times cannot choose a retry. Package
    pins, setup-script hashes and artifact hashes attest these records only, not
    complete physical validity or independently measured model accuracy.
    """
    if type(expectation) is not CampaignExpectation or type(budgets) is not CollectionBudgets:
        raise TypeError("Supply explicit campaign and collection-budget objects")
    root = Path(results_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Supply the existing copied or mounted campaign results root")
    records = tuple(_collect_case(expectation, case, index, root, budgets)
                    for index, case in enumerate(expectation.cases, 1))
    counts = MappingProxyType(dict(Counter(record.record_status for record in records)))
    complete = all(record.record_status in {"passed", "rejected", "failed"} for record in records)
    passed = all(record.record_status == "passed" for record in records)
    return CampaignEvidence(expectation, root, records, counts, complete, passed)
