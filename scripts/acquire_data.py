"""Reproduce bounded acquisition using the package's native Python API."""

import argparse
import concurrent.futures
from pathlib import Path

from h2physics.data import DATASETS, acquire_dataset, resolve_dataset
from h2physics.data.reporting import summarize_receipts, write_receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--maximum-mb", type=float, default=500)
    parser.add_argument("--maximum-file-mb", type=float, default=250)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--include-suffixes", nargs="+",
                        help="Explicit permitted attachment suffixes; dataset rights still apply")
    parser.add_argument("--minimum-download-interval-s", type=float, default=0.,
                        help="Minimum spacing between new download request starts within each dataset")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    seeds = [x for x in DATASETS if not args.keys or x.key in args.keys]
    if args.keys and set(args.keys) - {x.key for x in DATASETS}:
        parser.error("Unknown dataset key")

    def run(seed):
        try:
            dataset = resolve_dataset(seed)
            options = ({"suffixes": tuple(args.include_suffixes)} if args.include_suffixes else {})
            report = acquire_dataset(dataset, root / "data/raw",
                                     maximum_total_bytes=int(args.maximum_mb * 1e6),
                                     maximum_file_bytes=int(args.maximum_file_mb * 1e6),
                                     minimum_download_interval_s=args.minimum_download_interval_s, **options)
            write_receipt(report, root / "research/data" / f"{seed.key}.toml")
            count = sum(x.status in {"acquired", "cached"} for x in report.files)
            failed = [x.name + ": " + x.error for x in report.files if x.status in {"failed", "deferred"}]
            return (bool(failed), f"{seed.key}: {dataset.license_id}, {count}/{len(dataset.files)} "
                    f"files, {report.acquired_bytes/1e6:.2f} MB, "
                    f"{len(report.omitted_files)} omitted, failures={failed}")
        except Exception as error:
            path = root / "research/acquisition_failures.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            message = f"{seed.key}: {type(error).__name__}: {error}"
            with path.open("a", encoding="utf-8") as target:
                target.write(message + "\n")
            return True, message

    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4))) as pool:
        for future in concurrent.futures.as_completed([pool.submit(run, seed) for seed in seeds]):
            failed, result = future.result()
            failures += failed
            print(result, flush=True)
    summarize_receipts(root / "research/data", root / "docs/DATA_INVENTORY.md")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
