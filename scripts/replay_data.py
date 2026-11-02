"""Reproduce exactly the files pinned in public acquisition receipts."""

import argparse
from pathlib import Path

from h2physics.data import DATASETS, resolve_dataset
from h2physics.data.acquire import replay_receipt

parser = argparse.ArgumentParser()
parser.add_argument("keys", nargs="+")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
available = {p.stem: p for p in (root / "research/data").glob("*.toml")}
seeds = {item.key: item for item in DATASETS}
if set(args.keys) - available.keys() or set(args.keys) - seeds.keys():
    parser.error("Unknown recorded dataset")
for key in args.keys:
    dataset = resolve_dataset(seeds[key])
    receipts = replay_receipt(available[key], root / "data/raw", dataset=dataset)
    print(key, len(receipts), "files reproduced with recorded SHA-256", flush=True)
