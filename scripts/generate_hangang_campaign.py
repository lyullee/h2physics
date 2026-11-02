"""Generate, but never submit, one pinned Hangang PBS array."""

import argparse
import hashlib
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from h2physics.cluster_validation import (  # noqa: E402
    PBSResources,
    verify_source_manifest,
    write_pbs_array,
)
from validation.hangang_plan import CASES, PROFILES  # noqa: E402


def _manifest_digest(manifest: bytes, relative_path: str) -> str:
    """Return the unique SHA-256 recorded for one source-relative path."""
    try:
        rows = manifest.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("SOURCE_MANIFEST.sha256 must be UTF-8 text") from exc
    matches = []
    for row in rows:
        digest, separator, path = row.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("SOURCE_MANIFEST.sha256 contains a malformed entry")
        if path == relative_path:
            matches.append(digest)
    if len(matches) != 1:
        raise ValueError(
            f"SOURCE_MANIFEST.sha256 must contain exactly one entry for {relative_path}"
        )
    return matches[0]


def _cluster_posix_path(parser: argparse.ArgumentParser, value: str, option: str) -> str:
    path = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        not path.is_absolute()
        or windows.drive
        or "\\" in value
        or any(char in value for char in "\n\r\x00")
    ):
        parser.error(f"{option} must be an absolute remote POSIX path")
    return path.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--accounting", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--walltime", required=True)
    parser.add_argument("--slurm-cli-filter-comment", required=True,
                        help="Pinned field=<token>;appl=<token> metadata for Slurm showappl")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument(
        "--cluster-repository", required=True,
        help="Absolute POSIX path of the pinned repository on the remote cluster",
    )
    parser.add_argument(
        "--cluster-plan-file", required=True,
        help="Absolute POSIX path of validation/hangang_plan.py on the remote cluster",
    )
    parser.add_argument(
        "--case-id", action="append", dest="case_ids",
        help="Select a case from the pinned Hangang plan; repeat to make a smaller batch",
    )
    args = parser.parse_args()

    try:
        manifest = (ROOT / "SOURCE_MANIFEST.sha256").read_bytes()
        revision = (ROOT / "SOURCE_REVISION.txt").read_text(encoding="utf-8").strip()
        plan = ROOT / "validation/hangang_plan.py"
        plan_hash = hashlib.sha256(plan.read_bytes()).hexdigest()
        manifest_plan_hash = _manifest_digest(manifest, "validation/hangang_plan.py")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if plan_hash != manifest_plan_hash:
        parser.error(
            "local validation/hangang_plan.py bytes do not match the pinned source manifest"
        )
    manifest_hash = hashlib.sha256(manifest).hexdigest()
    try:
        verify_source_manifest(ROOT, revision, manifest_hash)
    except (OSError, ValueError) as exc:
        parser.error(f"pinned source snapshot failed verification: {exc}")
    cluster_repository = _cluster_posix_path(
        parser, args.cluster_repository, "--cluster-repository"
    )
    cluster_plan_file = _cluster_posix_path(
        parser, args.cluster_plan_file, "--cluster-plan-file"
    )
    resources = PBSResources(
        queue=args.queue,
        accounting=args.accounting,
        nodes=1,
        cpus_per_node=1,
        walltime=args.walltime,
    )
    if args.case_ids:
        by_id = {case.identifier: case for case in CASES}
        if len(set(args.case_ids)) != len(args.case_ids):
            parser.error("--case-id values must be unique")
        unknown = [case_id for case_id in args.case_ids if case_id not in by_id]
        if unknown:
            parser.error("unknown --case-id value(s): " + ", ".join(unknown))
        cases = tuple(by_id[case_id] for case_id in args.case_ids)
    else:
        cases = CASES
    path = write_pbs_array(
        cases,
        PROFILES,
        resources,
        destination=args.destination,
        cluster_repository=cluster_repository,
        cluster_plan_file=cluster_plan_file,
        cluster_result_directory=args.results,
        expected_revision=revision,
        expected_source_manifest_sha256=manifest_hash,
        expected_plan_sha256=plan_hash,
        name=args.name,
        slurm_cli_filter_comment=args.slurm_cli_filter_comment,
    )
    print(f"cases={len(cases)}")
    print("case_ids=" + ",".join(case.identifier for case in cases))
    print(f"pbs_script={path}")
    print(f"slurm_cli_filter_comment={args.slurm_cli_filter_comment}")
    print(f"plan_sha256={plan_hash}")
    print(f"source_manifest_sha256={manifest_hash}")


if __name__ == "__main__":
    main()
