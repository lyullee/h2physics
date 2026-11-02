"""Checkpoint verified completed files without restarting or duplicating downloads."""

import argparse
from pathlib import Path

from h2physics.data import DATASETS, resolve_dataset
from h2physics.data.acquire import audit_cached_dataset
from h2physics.data.reporting import summarize_receipts, write_receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys", nargs="+", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    seeds = [x for x in DATASETS if x.key in args.keys]
    if set(args.keys) != {x.key for x in seeds}:
        parser.error("Unknown dataset key")
    for seed in seeds:
        dataset = resolve_dataset(seed)
        report = audit_cached_dataset(dataset, root / "data/raw")
        write_receipt(report, root / "research/data" / (seed.key + ".toml"))
        print(seed.key, len([f for f in report.files if f.status == "cached"]),
              "complete verified files; bytes", report.acquired_bytes, flush=True)
    summarize_receipts(root / "research/data", root / "docs/DATA_INVENTORY.md")


if __name__ == "__main__":
    main()
