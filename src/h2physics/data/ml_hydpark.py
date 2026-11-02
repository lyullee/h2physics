"""Lossless, hash-bound access to the curated ML-HydPARK screening table.

This module preserves the deposited CSV tokens. It does not parse units,
normalize compositions, deduplicate entries, fit a model, or validate storage
physics.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

DOI = "10.5281/zenodo.10680097"
VERSION = "0.0.5"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
SOURCE_URL = "https://zenodo.org/records/10680097"
METADATA_SHA256 = "1e45a2930e47955aeda566eedef8337eeee3786616c5e010b8ba153ee17a6e04"
CSV_NAME = "ML-HYDPARK_v0.0.5.csv"
CSV_SIZE_BYTES = 100_494
CSV_MD5 = "d88e51ae01f93935a214326d3f37c560"
CSV_SHA256 = "41d1549a0b0b72355184cebe19d8da0b1ed18f87c7e1bf5527073a4246421af0"
ATTRIBUTION = (
    "Matthew Witman, Mark Allendorf, and Vitalie Stavila, Database for machine learning "
    "of hydrogen storage materials properties, Zenodo v0.0.5, 2024, "
    "https://doi.org/10.5281/zenodo.10680097. CC BY 4.0."
)

_HEADER = (
    "", "index", "Material_Class", "Composition_Formula", "Hydrogen_Weight_Percent",
    "Heat_of_Formation_kJperMolH2", "Temperature_oC", "Pressure_Atmospheres_Absolute",
    "Entropy_of_Formation_JperMolH2perK", "Equilibrium_Pressure_25C",
    "LnEquilibrium_Pressure_25C", "HtoM", "Reference",
)
_ROW_COUNT = 772
_PENDING_ISSUERS: set[object] = set()


def _issue_table(**values) -> MLHydPARKTable:
    issuer = object()
    _PENDING_ISSUERS.add(issuer)
    try:
        return MLHydPARKTable(**values, _issuer=issuer)
    except Exception:
        _PENDING_ISSUERS.discard(issuer)
        raise


def _has_linklike_component(path: Path) -> bool:
    current = Path(path).absolute()
    while True:
        is_junction = getattr(current, "is_junction", None)
        if current.is_symlink() or (callable(is_junction) and is_junction()):
            return True
        if current.parent == current:
            return False
        current = current.parent


def _digests(path: Path) -> tuple[int, str, str, tuple[int, int, int, int, int]]:
    if _has_linklike_component(path) or not path.is_file():
        raise ValueError("Select a regular local ML-HydPARK source file")
    before = path.stat()
    sha256, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            size += len(block)
            sha256.update(block)
            md5.update(block)
    after = path.stat()
    initial = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    final = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    if initial != final or size != after.st_size:
        raise ValueError("ML-HydPARK source changed while its checksum was being read")
    return size, md5.hexdigest(), sha256.hexdigest(), final


@dataclass(frozen=True, slots=True)
class MLHydPARKRow:
    """One CSV data record with every source cell retained as its original text."""

    source_row_number: int
    raw_tokens: tuple[str, ...] = field(repr=False)
    _header: tuple[str, ...] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if (isinstance(self.source_row_number, bool) or not isinstance(self.source_row_number, int)
                or self.source_row_number < 1 or len(self.raw_tokens) != len(self._header)
                or any(not isinstance(value, str) for value in self.raw_tokens)):
            raise ValueError("ML-HydPARK row must retain one token per source column")

    def token(self, source_column: str) -> str:
        """Return one exact source cell by its unique original header token."""
        matches = [index for index, header in enumerate(self._header) if header == source_column]
        if len(matches) != 1:
            raise ValueError("Select one exact, unique ML-HydPARK source column token")
        return self.raw_tokens[matches[0]]

    @property
    def source_cells(self) -> Mapping[str, str]:
        """An immutable header-to-token view, without numeric or unit conversion."""
        return MappingProxyType(dict(zip(self._header, self.raw_tokens, strict=True)))


@dataclass(frozen=True, slots=True)
class MLHydPARKTable:
    """Pinned curated-property table for material screening only."""

    source_path: Path = field(repr=False, compare=False)
    metadata_path: Path = field(repr=False, compare=False)
    doi: str
    version: str
    license_id: str
    license_url: str
    source_url: str
    attribution: str
    byte_size: int
    publisher_md5: str
    sha256: str
    metadata_sha256: str
    headers: tuple[str, ...]
    rows: tuple[MLHydPARKRow, ...]
    _file_identity: tuple[int, int, int, int, int] = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer not in _PENDING_ISSUERS:
            raise TypeError("Use load_ml_hydpark_screening() to issue source-bound rows")
        _PENDING_ISSUERS.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        source_path, metadata_path = Path(self.source_path).resolve(), Path(self.metadata_path).resolve()
        object.__setattr__(self, "source_path", source_path)
        object.__setattr__(self, "metadata_path", metadata_path)
        object.__setattr__(self, "headers", tuple(self.headers))
        object.__setattr__(self, "rows", tuple(self.rows))
        if (source_path.name != CSV_NAME or self.doi != DOI or self.version != VERSION
                or self.license_id != LICENSE_ID or self.license_url != LICENSE_URL
                or self.source_url != SOURCE_URL or self.attribution != ATTRIBUTION
                or self.byte_size != CSV_SIZE_BYTES or self.publisher_md5 != CSV_MD5
                or self.sha256 != CSV_SHA256 or self.metadata_sha256 != METADATA_SHA256
                or self.headers != _HEADER or len(self.rows) != _ROW_COUNT):
            raise ValueError("ML-HydPARK table differs from its reviewed source receipt")
        if any(row._header != self.headers or row.source_row_number != index
               for index, row in enumerate(self.rows, start=1)):
            raise ValueError("ML-HydPARK row order or source header differs from the parsed table")
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self) -> tuple:
        return (
            self.source_path, self.metadata_path, self.doi, self.version, self.license_id,
            self.license_url, self.source_url, self.attribution, self.byte_size,
            self.publisher_md5, self.sha256, self.metadata_sha256, self.headers,
            tuple((row.source_row_number, row.raw_tokens, row._header) for row in self.rows),
            self._file_identity,
        )

    def require_current(self) -> MLHydPARKTable:
        if self._payload() != self._seal:
            raise ValueError("ML-HydPARK table rows or provenance changed after source admission")
        size, md5, sha256, identity = _digests(self.source_path)
        if (size, md5, sha256, identity) != (
                CSV_SIZE_BYTES, CSV_MD5, CSV_SHA256, self._file_identity):
            raise ValueError("ML-HydPARK CSV no longer matches its source receipt")
        metadata_size, _, metadata_hash, _ = _digests(self.metadata_path)
        if metadata_size <= 0 or metadata_hash != METADATA_SHA256:
            raise ValueError("Zenodo record metadata no longer matches the pinned source receipt")
        return self


def load_ml_hydpark_screening(directory: str | Path) -> MLHydPARKTable:
    """Load the exact acquired CSV and Zenodo receipt without coercing source cells.

    The source describes a cleaned/curated collection of compositions, hydrogen
    capacities, and thermodynamic quantities assembled from the HydPARK
    database/literature. This function exposes tokens for screening workflows;
    its output is not a measured time series or independent validation set.
    """
    supplied_root = Path(directory)
    if _has_linklike_component(supplied_root) or not supplied_root.is_dir():
        raise ValueError("Provide the acquired ML-HydPARK version directory")
    root = supplied_root.resolve()
    source_path, metadata_path = root / CSV_NAME, root / "zenodo-record.json"
    size, md5, sha256, identity = _digests(source_path)
    metadata_size, _, metadata_sha256, _ = _digests(metadata_path)
    if ((size, md5, sha256) != (CSV_SIZE_BYTES, CSV_MD5, CSV_SHA256)
            or metadata_sha256 != METADATA_SHA256):
        raise ValueError("ML-HydPARK file or its publisher metadata differs from the pinned receipt")
    try:
        record = json.loads(metadata_path.read_bytes())
        metadata = record["metadata"]
        licenses = metadata["license"]["id"]
        listed = [item for item in record["files"] if item.get("key") == CSV_NAME]
        if (record.get("doi") != DOI or metadata.get("version") != VERSION
                or metadata.get("access_right") != "open" or licenses != "cc-by-4.0"
                or len(listed) != 1 or listed[0].get("size") != CSV_SIZE_BYTES
                or listed[0].get("checksum") != f"md5:{CSV_MD5}"):
            raise ValueError("Zenodo identity, license, or attachment listing changed")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("Pinned Zenodo metadata is malformed or incomplete") from error

    rows: list[MLHydPARKRow] = []
    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            headers = tuple(next(reader))
            if headers != _HEADER:
                raise ValueError("ML-HydPARK source header tokens differ from the reviewed schema")
            for source_row_number, tokens in enumerate(reader, start=1):
                if len(tokens) != len(headers):
                    raise ValueError(f"CSV data row {source_row_number} has an unexpected field count")
                rows.append(MLHydPARKRow(source_row_number, tuple(tokens), headers))
    except (OSError, UnicodeDecodeError, csv.Error, StopIteration) as error:
        raise ValueError("ML-HydPARK CSV could not be read under its pinned schema") from error
    if len(rows) != _ROW_COUNT:
        raise ValueError("ML-HydPARK data-row count differs from the reviewed source schema")

    table = _issue_table(
        source_path=source_path, metadata_path=metadata_path, doi=DOI, version=VERSION,
        license_id=LICENSE_ID, license_url=LICENSE_URL, source_url=SOURCE_URL,
        attribution=ATTRIBUTION, byte_size=size, publisher_md5=md5, sha256=sha256,
        metadata_sha256=metadata_sha256, headers=headers, rows=tuple(rows),
        _file_identity=identity,
    )
    return table.require_current()


__all__ = ["ATTRIBUTION", "DOI", "LICENSE_ID", "LICENSE_URL", "MLHydPARKRow",
           "MLHydPARKTable", "SOURCE_URL", "VERSION", "load_ml_hydpark_screening"]
