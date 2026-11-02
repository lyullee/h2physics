"""Run three host contract lanes in separate, source-pinned processes."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

LANES = ("equipment_storage", "production_materials", "safety_facility")


def source_pins(root):
    paths = sorted((root / "src/h2physics").rglob("*.py"))
    for folder in ("tests", "scripts", "examples", "validation"):
        paths += sorted((root / folder).rglob("*.py"))
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("extreme", "connection"), default="extreme")
    parser.add_argument("--lanes", choices=LANES, nargs="+", default=list(LANES))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=180.)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("Use an empty output directory to preserve previous receipts")
    before = source_pins(root)
    env = os.environ.copy()
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", MPLBACKEND="Agg", PYTHONIOENCODING="utf-8",
               OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               NUMEXPR_NUM_THREADS="1")

    def run(lane):
        command = [sys.executable, "-m", "pytest", f"tests/test_{args.stage}_contract_{lane}.py",
                   "-q", "-o", "junit_family=xunit1",
                   "--junitxml=" + str(output / (lane + ".xml"))]
        started = time.monotonic()
        try:
            with (output / (lane + ".log")).open("w", encoding="utf-8") as log:
                result = subprocess.run(command, cwd=root, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=args.timeout)
            code, error = result.returncode, None
        except subprocess.TimeoutExpired:
            code, error = None, "process_timeout"
        return {"lane": lane, "command": command, "returncode": code, "error": error,
                "elapsed_s": time.monotonic() - started}

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run, dict.fromkeys(args.lanes)))
    unchanged = before == source_pins(root)
    receipt = {"recorded_utc": datetime.now(UTC).isoformat(), "stage": args.stage,
               "source_sha256": before,
               "source_unchanged": unchanged, "results": results,
               "environment": {key: env[key] for key in
                               ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "MPLBACKEND",
                                "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                "NUMEXPR_NUM_THREADS", "PYTHONIOENCODING")}}
    path = output / "run.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    print(json.dumps({"source_unchanged": unchanged, "results": results}))
    return 0 if unchanged and all(row["returncode"] == 0 for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
