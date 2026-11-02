"""Hash-pinned observation reader for published Pd leaky-coating sorption traces."""

from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

SOURCE_DOI = "10.5281/zenodo.6670268"
SOURCE_URL = "https://zenodo.org/records/6670268"
SOURCE_LICENSE = "CC-BY-4.0"
_PINS = {
    "Fig4a_deltap_f.txt": (56082, "953db55792ad0dc329ba1d424face23e", "992fcadc72fd30396c2094f2e1f573aa9a79e32bcf522bcd6ccd79dc18460cd4"),
    "Fig4a_pUHV.txt": (211933, "221f4f79c67d7589dc5430379e9e496e", "3acf2f492fe715a84de724ef059532d8ee8255680ed74d114fd7802140013f18"),
    "Fig4c_deltap_f.txt": (58697, "cc652265e9cdf807323db95c626f1bee", "8a5749998f1d57e27b67758af8116259430528e581d8becbad1d5d47ebe414f1"),
    "Fig4c_pUHV.txt": (141697, "9075e77cfc586c19ee89b0e07327a35b", "4f026f852b2ba4a5804efd7898382b0a6540f6befe23b69dbf2981b9fa83f23d"),
}


@dataclass(frozen=True, slots=True)
class SorptionSourcePair:
    """Exact source time/value tokens before optional numeric projection."""

    source_row: int
    time_token: str
    value_token: str

    @property
    def has_numeric_pair(self) -> bool:
        return _number_or_none(self.time_token) is not None and _number_or_none(self.value_token) is not None


def _number_or_none(token: str) -> float | None:
    text = token.strip()
    if text in {"", "--"}:
        return None
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError(f"Unexpected nonnumeric source token: {token!r}") from error
    if not math.isfinite(value):
        raise ValueError(f"Unexpected non-finite source token: {token!r}")
    return value


@dataclass(frozen=True, slots=True)
class SorptionTrace:
    figure: str
    signal: str
    channel: str
    source_header: str
    time_s: tuple[float, ...]
    value_tokens: tuple[str, ...]
    source_pairs: tuple[SorptionSourcePair, ...]
    value_unit: str = "mbar"

    def __post_init__(self):
        times = tuple(float(value) for value in self.time_s)
        tokens = tuple(self.value_tokens)
        pairs = tuple(self.source_pairs)
        if len(times) != len(tokens):
            raise ValueError("A sorption trace needs aligned time/value samples")
        if not pairs:
            raise ValueError("Retain the raw source time/value pairs for every trace")
        complete = tuple(pair for pair in pairs if pair.has_numeric_pair)
        if len(complete) != len(times) or tuple(pair.value_token for pair in complete) != tokens:
            raise ValueError("Numeric samples must be exactly the complete raw source pairs")
        if tuple(float(pair.time_token) for pair in complete) != times:
            raise ValueError("Numeric time samples differ from retained source time tokens")
        if any(not (left < right) for left, right in zip(times, times[1:])):
            raise ValueError("Source time tokens must be strictly increasing within each trace")
        for token in tokens:
            float(token)
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "value_tokens", tokens)
        object.__setattr__(self, "source_pairs", pairs)

    @property
    def values_mbar(self) -> tuple[float, ...]:
        return tuple(float(token) for token in self.value_tokens)


@dataclass(frozen=True, slots=True)
class LeakyCoatingSorptionData:
    root: Path
    traces: tuple[SorptionTrace, ...]
    file_sha256: tuple[tuple[str, str], ...]
    license: str = SOURCE_LICENSE
    doi: str = SOURCE_DOI

    @property
    def source_pair_count(self) -> int:
        return sum(len(trace.source_pairs) for trace in self.traces)

    @property
    def missing_time_token_count(self) -> int:
        return sum(1 for trace in self.traces for pair in trace.source_pairs
                   if _number_or_none(pair.time_token) is None)

    @property
    def missing_value_token_count(self) -> int:
        return sum(1 for trace in self.traces for pair in trace.source_pairs
                   if _number_or_none(pair.value_token) is None)

    @property
    def incomplete_pair_count(self) -> int:
        return sum(1 for trace in self.traces for pair in trace.source_pairs
                   if not pair.has_numeric_pair)

    def require_current(self) -> None:
        fresh = read_leaky_coating_sorption_data(self.root)
        if fresh.traces != self.traces or fresh.file_sha256 != self.file_sha256:
            raise ValueError("Leaky-coating source data changed after ingestion")
        if self.license != SOURCE_LICENSE or self.doi != SOURCE_DOI:
            raise ValueError("Leaky-coating source rights or DOI receipt changed")


def _read_table(path: Path, figure: str, signal: str) -> tuple[SorptionTrace, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    if not rows or not rows[0]:
        raise ValueError(f"Empty leaky-coating source table: {path.name}")
    header = tuple(rows[0])
    if any(not row for row in rows[1:]):
        rows = [rows[0], *(row for row in rows[1:] if row)]
    if "time" not in header[0].lower():
        raise ValueError(f"First source column is not a time axis: {path.name}")
    if any(len(row) not in {len(header), 2 * (len(header) - 1)} for row in rows[1:]):
        raise ValueError(f"Ragged rows in leaky-coating source table: {path.name}")
    alternating = len(rows) > 1 and len(rows[1]) == 2 * (len(header) - 1)
    if alternating:
        traces = []
        for channel_index, header_value in enumerate(header[1:]):
            pairs = tuple(SorptionSourcePair(row_number, row[2 * channel_index].strip(),
                                             row[2 * channel_index + 1].strip())
                          for row_number, row in enumerate(rows[1:], start=2))
            complete = tuple(pair for pair in pairs if pair.has_numeric_pair)
            traces.append(SorptionTrace(
                figure, signal, header_value, f"source time / {header_value}",
                tuple(float(pair.time_token) for pair in complete),
                tuple(pair.value_token for pair in complete), pairs,
            ))
        return tuple(traces)
    if "time" not in header[0].lower():
        raise ValueError(f"First source column is not a time axis: {path.name}")
    traces = []
    for index, column in enumerate(header[1:], start=1):
        pairs = tuple(SorptionSourcePair(row_number, row[0].strip(), row[index].strip())
                      for row_number, row in enumerate(rows[1:], start=2))
        samples = tuple(pair for pair in pairs if pair.has_numeric_pair)
        traces.append(SorptionTrace(figure, signal, column,
                                    f"{header[0]} / {column}",
                                    tuple(float(item.time_token) for item in samples),
                                    tuple(item.value_token for item in samples), pairs))
    return tuple(traces)


def read_leaky_coating_sorption_data(root: str | Path) -> LeakyCoatingSorptionData:
    """Read only the four reviewed measured Figure 4 text files; preserve source channels."""
    data_root = Path(root)
    all_traces = []
    receipts = []
    for filename, (expected_size, expected_md5, expected_sha256) in _PINS.items():
        path = data_root / filename
        raw = path.read_bytes()
        md5 = hashlib.md5(raw).hexdigest()
        sha256 = hashlib.sha256(raw).hexdigest()
        if len(raw) != expected_size or md5 != expected_md5 or sha256 != expected_sha256:
            raise ValueError(f"Leaky-coating source revision does not match Zenodo pin: {filename}")
        figure = filename.split("_", 1)[0][3:]
        signal = "feed_pressure_delta" if "deltap_f" in filename else "ultra_high_vacuum_ms_pressure"
        all_traces.extend(_read_table(path, figure, signal))
        receipts.append((filename, sha256))
    return LeakyCoatingSorptionData(data_root, tuple(all_traces), tuple(receipts))
