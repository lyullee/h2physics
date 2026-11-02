"""Anonymous numeric observations from the public buried-pipeline release.

The publisher supplies headerless UTF-16 tab-separated files without a column
dictionary. This reader therefore preserves positional columns and missing cells
without assigning physical quantities, units, or an observation operator.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from .models import Dataset

_DOI_PREFIX = "10.17632/x8zkds4fyn."
_VERSION = "2"
_LICENSE = "CC-BY-4.0"
_DATASET_KEY = "buried-h2-blend-pipeline"
_METADATA_URL = "https://data.mendeley.com/public-api/datasets/x8zkds4fyn/snapshot/2"
_METADATA_SHA256 = "d2fec89f1eee8916992aec86d6ebc10b5b94dfd1be1aa780c0f93ce541d1fcf8"
_LISTING_URL = ("https://data.mendeley.com/public-api/datasets/x8zkds4fyn/files?"
                "folder_id=root&version=2&$start=0&$limit=1000")
_LISTING_SHA256 = "22732dafaeadf55deca96a08b5448b73dc809284629bfba0038c8b8215616c0e"
_MAX_FILE_BYTES = 100_000
_MAX_ROWS = 10_000
_MAX_COLUMNS = 64
_PENDING_TABLE_ISSUERS: set[object] = set()
_PENDING_COLUMN_ISSUERS: set[object] = set()


def _issue_table(**values):
    token = object()
    _PENDING_TABLE_ISSUERS.add(token)
    try:
        return BuriedPipelineNumericTable(**values, _issuer_token=token)
    except Exception:
        _PENDING_TABLE_ISSUERS.discard(token)
        raise


def _issue_column_series(**values):
    token = object()
    _PENDING_COLUMN_ISSUERS.add(token)
    try:
        return BuriedPipelineColumnSeries(**values, _issuer_token=token)
    except Exception:
        _PENDING_COLUMN_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class BuriedPipelineColumnSeries:
    """One anonymous column with the source row and token lineage retained."""

    source_id: str
    source_file: str
    source_sha256: str
    column_name: str
    row_ids: tuple[str, ...]
    raw_tokens: tuple[str, ...]
    values: NDArray[np.float64]
    valid: NDArray[np.bool_]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _integrity_sha256: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_COLUMN_ISSUERS:
            raise ValueError("Use a loaded buried-pipeline table to issue a source-bound column projection")
        _PENDING_COLUMN_ISSUERS.remove(self._issuer_token)
        rows, tokens = tuple(self.row_ids), tuple(self.raw_tokens)
        values = np.array(self.values, dtype=float, copy=True)
        valid = np.array(self.valid, dtype=bool, copy=True)
        suffix = (self.column_name.removeprefix("source_column_")
                  if isinstance(self.column_name, str) else "")
        if (self.source_id != _DOI_PREFIX + _VERSION
                or not isinstance(self.source_file, str) or not self.source_file.strip()
                or self.source_file.replace("\\", "/").rsplit("/", 1)[-1] != self.source_file
                or not isinstance(self.column_name, str)
                or not suffix.isdecimal() or int(suffix) < 1
                or self.column_name != f"source_column_{int(suffix)}"):
            raise ValueError("Column series must retain the admitted source and anonymous positional identity")
        if (not isinstance(self.source_sha256, str) or len(self.source_sha256) != 64
                or any(character not in "0123456789abcdef" for character in self.source_sha256)):
            raise ValueError("Column series requires the publisher-bound lowercase SHA-256")
        if (not rows or len(set(rows)) != len(rows) or len(tokens) != len(rows)
                or values.shape != (len(rows),) or valid.shape != values.shape):
            raise ValueError("Column values, source tokens, masks and row identities must align")
        if rows != tuple(f"{self.source_id}:{self.source_file}:row-{i}"
                         for i in range(1, len(rows) + 1)):
            raise ValueError("Column series must preserve ordered source row identities")
        rebuilt = np.full(len(rows), np.nan, dtype=float)
        rebuilt_valid = np.zeros(len(rows), dtype=bool)
        for index, token in enumerate(tokens):
            if not isinstance(token, str):
                raise TypeError("Column tokens must retain their exact decoded text")
            if not token.strip():
                continue
            try:
                number = float(token.strip())
            except ValueError as error:
                raise ValueError("Column tokens must remain numeric or blank") from error
            if not math.isfinite(number):
                raise ValueError("Column tokens cannot contain nonfinite numeric values")
            rebuilt[index], rebuilt_valid[index] = number, True
        if (not np.array_equal(values, rebuilt, equal_nan=True)
                or not np.array_equal(valid, rebuilt_valid)):
            raise ValueError("Column values and validity mask must reconstruct from source tokens")
        values = np.frombuffer(values.tobytes(order="C"), dtype=np.float64)
        valid = np.frombuffer(valid.tobytes(order="C"), dtype=np.bool_)
        object.__setattr__(self, "row_ids", rows)
        object.__setattr__(self, "raw_tokens", tokens)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "valid", valid)
        object.__setattr__(self, "_integrity_sha256", self._integrity_digest())

    def _integrity_digest(self):
        digest = hashlib.sha256()
        digest.update(self.values.tobytes(order="C"))
        digest.update(self.valid.tobytes(order="C"))
        digest.update(repr((self.source_id, self.source_file, self.source_sha256,
                            self.column_name, self.row_ids, self.raw_tokens)).encode("utf-8"))
        return digest.hexdigest()

    def require_current(self):
        """Check that the typed column receipt still matches its retained contents."""
        if self._integrity_digest() != self._integrity_sha256:
            raise ValueError("Buried-pipeline column series changed after projection")
        return self


@dataclass(frozen=True, slots=True)
class BuriedPipelineNumericTable:
    """A source-bound table with anonymous positional columns and explicit gaps."""

    source_id: str
    source_file: str
    source_sha256: str
    column_names: tuple[str, ...]
    row_ids: tuple[str, ...]
    raw_fields: tuple[tuple[str, ...], ...]
    values: NDArray[np.float64]
    valid: NDArray[np.bool_]
    encoding: str = "utf-16"
    delimiter: str = "tab"
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _integrity_sha256: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TABLE_ISSUERS:
            raise ValueError("Use the checksum-validating buried-pipeline loader to issue source-bound tables")
        _PENDING_TABLE_ISSUERS.remove(self._issuer_token)
        values = np.array(self.values, dtype=float, copy=True)
        valid = np.array(self.valid, dtype=bool, copy=True)
        columns, rows = tuple(self.column_names), tuple(self.row_ids)
        if isinstance(self.raw_fields, (str, bytes)):
            raise TypeError("Raw table fields must be a sequence of source rows")
        raw_rows = tuple(self.raw_fields)
        if any(isinstance(row, (str, bytes)) for row in raw_rows):
            raise TypeError("Each source row must retain its field sequence")
        raw_fields = tuple(tuple(row) for row in raw_rows)
        if (self.source_id != _DOI_PREFIX + _VERSION
                or not isinstance(self.source_file, str)
                or not self.source_file.strip()
                or self.source_file.replace("\\", "/").rsplit("/", 1)[-1] != self.source_file
                or self.encoding != "utf-16" or self.delimiter != "tab"):
            raise ValueError("Table source/version/file-format identity is not the admitted V2 record")
        digest = self.source_sha256
        if (not isinstance(digest, str) or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise ValueError("Table source digest must be a lowercase SHA-256")
        if values.ndim != 2 or valid.shape != values.shape:
            raise ValueError("Numeric values and validity mask must be matching 2D arrays")
        if (values.shape != (len(rows), len(columns)) or not rows or not columns
                or len(raw_fields) != len(rows)
                or any(not row or len(row) > len(columns) for row in raw_fields)):
            raise ValueError("Anonymous column and source-row identities must match the table")
        if len(set(rows)) != len(rows) or columns != tuple(
            f"source_column_{index}" for index in range(1, len(columns) + 1)
        ):
            raise ValueError("Rows must be unique and columns must remain positional")
        if np.any(valid & ~np.isfinite(values)):
            raise ValueError("Valid source cells must be finite numeric values")
        expected_rows = tuple(
            f"{self.source_id}:{self.source_file}:row-{index}"
            for index in range(1, len(rows) + 1)
        )
        if rows != expected_rows:
            raise ValueError("Table row identities must preserve ordered source line numbers")
        reconstructed = np.full(values.shape, np.nan, dtype=float)
        reconstructed_valid = np.zeros(values.shape, dtype=bool)
        for row_index, record in enumerate(raw_fields):
            if any(not isinstance(token, str) for token in record):
                raise TypeError("Raw table cells must retain their exact decoded source text")
            for column_index, token in enumerate(record):
                if not token.strip():
                    continue
                try:
                    number = float(token.strip())
                except ValueError as error:
                    raise ValueError("Raw source cells must remain numeric or blank") from error
                if not math.isfinite(number):
                    raise ValueError("Raw source cells cannot contain nonfinite numeric values")
                reconstructed[row_index, column_index] = number
                reconstructed_valid[row_index, column_index] = True
        if (not np.array_equal(valid, reconstructed_valid)
                or not np.array_equal(values, reconstructed, equal_nan=True)):
            raise ValueError("Numeric view and validity mask must reconstruct from exact retained source tokens")
        # Back each public view with immutable bytes. Merely clearing NumPy's
        # WRITEABLE flag on an owning array is reversible by a caller.
        values = np.frombuffer(values.tobytes(order="C"), dtype=np.float64).reshape(values.shape)
        valid = np.frombuffer(valid.tobytes(order="C"), dtype=np.bool_).reshape(valid.shape)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "valid", valid)
        object.__setattr__(self, "column_names", columns)
        object.__setattr__(self, "row_ids", rows)
        object.__setattr__(self, "raw_fields", raw_fields)
        object.__setattr__(self, "_integrity_sha256", self._integrity_digest())

    def _integrity_digest(self):
        digest = hashlib.sha256()
        digest.update(self.values.tobytes(order="C"))
        digest.update(self.valid.tobytes(order="C"))
        digest.update(repr((self.source_id, self.source_file, self.source_sha256,
                            self.column_names, self.row_ids, self.raw_fields,
                            self.encoding, self.delimiter)).encode("utf-8"))
        return digest.hexdigest()

    def require_current(self):
        """Reject mutation of the returned numeric view or source receipt."""
        if self._integrity_digest() != self._integrity_sha256:
            raise ValueError("Buried-pipeline table or publisher receipt changed after loading")
        return self

    def column_series(self, column_name: str) -> BuriedPipelineColumnSeries:
        """Project one positional column without discarding its source lineage.

        The returned object retains the anonymous column label, exact decoded
        tokens, publisher file digest, validity mask and original row identities.
        It does not add units, clock semantics or a physical observation mapping.
        """
        self.require_current()
        if not isinstance(column_name, str):
            raise TypeError("Select a column by its anonymous source label")
        try:
            index = self.column_names.index(column_name)
        except ValueError as error:
            raise KeyError(column_name) from error
        tokens = tuple(row[index] if index < len(row) else "" for row in self.raw_fields)
        return _issue_column_series(
            source_id=self.source_id,
            source_file=self.source_file,
            source_sha256=self.source_sha256,
            column_name=column_name,
            row_ids=self.row_ids,
            raw_tokens=tokens,
            values=self.values[:, index],
            valid=self.valid[:, index],
        ).require_current()


def load_buried_pipeline_numeric_table(
    path: str | Path,
    *,
    dataset: Dataset,
    file_name: str,
) -> BuriedPipelineNumericTable:
    """Load one locally acquired V2 CSV after verifying its publisher SHA-256.

    `dataset` should come from the repository metadata API. No network access is
    performed here. Blank cells remain invalid in the returned mask; columns are
    deliberately anonymous because the source release has no field dictionary.
    """
    if (dataset.key != _DATASET_KEY or dataset.doi != _DOI_PREFIX + _VERSION
            or dataset.version != _VERSION or dataset.license_id != _LICENSE
            or dataset.metadata_url != _METADATA_URL
            or dataset.metadata_sha256 != _METADATA_SHA256):
        raise ValueError("Expected the pinned version-2 CC BY 4.0 buried-pipeline metadata receipt")
    if (len(dataset.supporting_metadata) != 1
            or dataset.supporting_metadata[0][0] != _LISTING_URL
            or hashlib.sha256(dataset.supporting_metadata[0][1]).hexdigest() != _LISTING_SHA256):
        raise ValueError("Expected the pinned V2 publisher attachment-listing receipt")
    try:
        listing = json.loads(dataset.supporting_metadata[0][1])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Pinned attachment-listing bytes are not valid JSON") from error
    if not isinstance(listing, list):
        raise ValueError("Pinned publisher attachment listing must be a JSON array")
    listed_files = []
    for entry in listing:
        if not isinstance(entry, dict) or entry.get("status") != "COMPLETED":
            continue
        details = entry.get("content_details")
        if not isinstance(details, dict):
            raise ValueError("Completed publisher attachments need content details")
        listed_files.append((entry.get("filename"), details.get("size"),
                             details.get("download_url"), details.get("sha256_hash", "")))
    resolved_files = [(item.name, item.size_bytes, item.url,
                       item.checksum if item.checksum_algorithm == "sha256" else "")
                      for item in dataset.files]
    if len(listed_files) != 12 or sorted(listed_files) != sorted(resolved_files):
        raise ValueError("Resolved file objects differ from the pinned publisher attachment listing")
    matches = tuple(item for item in dataset.files if item.name == file_name)
    if len(matches) != 1:
        raise ValueError("File name must identify exactly one publisher-listed V2 attachment")
    remote = matches[0]
    if remote.checksum_algorithm != "sha256" or not remote.checksum:
        raise ValueError("File must match a publisher-listed V2 attachment with SHA-256")
    source_path = Path(path)
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("Input must be a regular local CSV file")
    if source_path.stat().st_size > _MAX_FILE_BYTES:
        raise ValueError("Source file exceeds the bounded reader size")
    payload = source_path.read_bytes()
    if len(payload) != remote.size_bytes:
        raise ValueError("Local source byte count does not match the publisher listing")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != remote.checksum:
        raise ValueError("Local source bytes do not match the publisher SHA-256")
    try:
        text = payload.decode("utf-16")
    except UnicodeDecodeError as error:
        raise ValueError("Expected UTF-16 encoded publisher CSV") from error
    records = list(csv.reader(text.splitlines(), delimiter="\t", strict=True))
    if not records or len(records) > _MAX_ROWS:
        raise ValueError("Source table is empty or exceeds the bounded row count")
    width = max(map(len, records))
    if width > _MAX_COLUMNS:
        raise ValueError("Source table exceeds the bounded column count")
    values = np.full((len(records), width), np.nan, dtype=float)
    valid = np.zeros((len(records), width), dtype=bool)
    for row_index, record in enumerate(records):
        for column_index, token in enumerate(record):
            token = token.strip()
            if not token:
                continue
            try:
                value = float(token)
            except ValueError as error:
                raise ValueError(
                    f"Unexpected nonnumeric token at source row {row_index + 1}, "
                    f"column {column_index + 1}"
                ) from error
            if not math.isfinite(value):
                raise ValueError("Nonfinite values are not accepted as source observations")
            values[row_index, column_index] = value
            valid[row_index, column_index] = True
    return _issue_table(
        source_id=dataset.doi,
        source_file=file_name,
        source_sha256=digest,
        column_names=tuple(f"source_column_{index}" for index in range(1, width + 1)),
        row_ids=tuple(f"{dataset.doi}:{file_name}:row-{index}" for index in range(1, len(records) + 1)),
        raw_fields=tuple(tuple(record) for record in records),
        values=values,
        valid=valid,
    ).require_current()
