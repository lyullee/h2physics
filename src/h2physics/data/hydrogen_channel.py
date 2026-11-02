"""Lossless, source-bound numeric table intake for the open-channel release.

The release has a two-row header, several independent instrument clocks and
unresolved concentration-channel details. This module preserves its content and
does not create a TimeSeries or infer clock alignment.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

import numpy as np
from numpy.typing import NDArray

from .models import Dataset

_DOI = "10.23642/usn.26117989.v2"
_LICENSE = "CC-BY-4.0"
_DATASET_KEY = "hydrogen-channel"
_METADATA_URL = "https://api.figshare.com/v2/articles/26117989"
_METADATA_SHA256 = "ecfb5690fe87b9c8ad9293a0783e33a24818556d38446e97e1103c8d3c1eb2dc"
_MAX_ARCHIVE_BYTES = 10_000_000
_MAX_CSV_BYTES = 4_000_000
_MAX_ROWS = 50_000
_MAX_COLUMNS = 64
# Publisher's short experiment labels as listed in the acquired ReadMe.txt.
# The source asset is pinned by this digest; these identifiers carry no physical
# interpretation and are intentionally separate from all channel fields.
_CASE_LABEL_SOURCE_SHA256 = "c474c05b9c3983c609030755c8f6e9d854fa53a8531b81425da87e206e837b04"
_PUBLISHER_EXPERIMENT_LABELS = {
    "23_FFI_P101_T00014": "test-01-0",
    "23_FFI_P101_T00012": "test-02-0A",
    "23_FFI_P101_T00013": "test-02-0B",
    "23_FFI_P101_T00026": "test-03-0",
    "23_FFI_P101_T00006": "test-04-0",
    "23_FFI_P101_T00003": "test-05-0A",
    "23_FFI_P101_T00004": "test-05-0B",
    "23_FFI_P101_T00005": "test-05-0C",
    "23_FFI_P101_T00008": "test-06-0A",
    "23_FFI_P101_T00009": "test-06-0B",
    "23_FFI_P101_T00007": "test-07-0",
    "23_FFI_P101_T00011": "test-08-0",
    "23_FFI_P101_T00027": "test-02-1A",
    "23_FFI_P101_T00028": "test-02-1B",
    "23_FFI_P101_T00029": "test-05-1A",
    "23_FFI_P101_T00030": "test-05-1B",
    "23_FFI_P101_T00031": "test-08-1",
    "23_FFI_P101_T00040": "test-02-2A",
    "23_FFI_P101_T00041": "test-02-2B",
    "23_FFI_P101_T00042": "test-05-2",
    "23_FFI_P101_T00045": "test-02-3",
    "23_FFI_P101_T00044": "test-05-3",
}
_PENDING_CASE_ISSUERS: set[object] = set()


def _issue_hydrogen_channel_case(**values):
    token = object()
    _PENDING_CASE_ISSUERS.add(token)
    try:
        return HydrogenChannelCase(**values, _issuer_token=token)
    except Exception:
        _PENDING_CASE_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class HydrogenChannelCase:
    """One publisher-hashed case, retaining its two header rows and source tokens."""

    source_doi: str
    source_file: str
    source_sha256: str
    publisher_checksum_algorithm: str
    publisher_checksum: str
    csv_member: str
    member_sha256: str
    column_names: tuple[str, ...]
    channel_descriptions: tuple[str, ...]
    row_ids: tuple[str, ...]
    raw_fields: tuple[tuple[str, ...], ...]
    values: NDArray[np.float64]
    valid: NDArray[np.bool_]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_CASE_ISSUERS:
            raise ValueError("Use the checksum-validating archive loader to issue a source-bound case")
        _PENDING_CASE_ISSUERS.remove(self._issuer_token)
        if (self.source_doi != _DOI or not isinstance(self.source_file, str)
                or not self.source_file.strip()
                or self.source_file.replace("\\", "/").rsplit("/", 1)[-1] != self.source_file):
            raise ValueError("Case must identify the admitted hydrogen-channel V2 record and file")
        for name in ("source_sha256", "member_sha256"):
            value = getattr(self, name)
            if (not isinstance(value, str) or len(value) != 64
                    or any(character not in "0123456789abcdef" for character in value)):
                raise ValueError(f"{name} must be a lowercase SHA-256")
        algorithm = self.publisher_checksum_algorithm
        checksum = self.publisher_checksum
        expected_lengths = {"md5": 32, "sha256": 64}
        if (algorithm not in expected_lengths or not isinstance(checksum, str)
                or len(checksum) != expected_lengths[algorithm]
                or any(character not in "0123456789abcdef" for character in checksum)):
            raise ValueError("Retain the exact supported publisher checksum receipt")
        member = PurePosixPath(self.csv_member)
        if (member.is_absolute() or ".." in member.parts or "\\" in self.csv_member
                or ":" in self.csv_member or not self.csv_member.lower().endswith(".csv")):
            raise ValueError("CSV member must be a safe archive-relative path")
        for name in ("column_names", "channel_descriptions", "row_ids", "raw_fields"):
            if isinstance(getattr(self, name), (str, bytes)):
                raise TypeError(f"{name} must be a sequence, not text")
        columns, descriptions = tuple(self.column_names), tuple(self.channel_descriptions)
        if (not columns or len(columns) > _MAX_COLUMNS or len(set(columns)) != len(columns)
                or len(descriptions) != len(columns)
                or any(not isinstance(item, str) for item in (*columns, *descriptions))):
            raise ValueError("Both retained header rows must match the unique source columns")
        rows = tuple(self.row_ids)
        if any(isinstance(row, (str, bytes)) for row in self.raw_fields):
            raise TypeError("Each raw source record must be a field sequence, not text")
        raw = tuple(tuple(row) for row in self.raw_fields)
        raw_values, raw_valid = np.asarray(self.values), np.asarray(self.valid)
        if raw_values.dtype.kind not in "iuf" or raw_valid.dtype.kind != "b":
            raise TypeError("Numeric values and boolean validity mask must have explicit dtypes")
        values = np.array(raw_values, dtype=float, copy=True)
        valid = np.array(raw_valid, dtype=bool, copy=True)
        if (not rows or len(rows) > _MAX_ROWS or len(rows) != len(raw)
                or values.shape != (len(rows), len(columns)) or valid.shape != values.shape):
            raise ValueError("Case rows, source tokens, values and mask must align")
        if (any(not isinstance(row, str) or not row.strip() for row in rows)
                or len(set(rows)) != len(rows) or any(len(row) > len(columns) for row in raw)):
            raise ValueError("Source row identities must be unique and rows cannot exceed header width")
        rebuilt = np.full(values.shape, np.nan)
        rebuilt_valid = np.zeros(values.shape, dtype=bool)
        for r, source_row in enumerate(raw):
            for c, token in enumerate(source_row):
                if not isinstance(token, str):
                    raise TypeError("Raw CSV cells must retain their original decoded text")
                if not token.strip():
                    continue
                try:
                    number = float(token.strip())
                except ValueError as error:
                    raise ValueError("Observation rows may contain only finite numerics or blank cells") from error
                if not math.isfinite(number):
                    raise ValueError("Nonfinite tokens remain raw evidence and are not admitted as numeric values")
                rebuilt[r, c] = number
                rebuilt_valid[r, c] = True
        if (not np.array_equal(values, rebuilt, equal_nan=True)
                or not np.array_equal(valid, rebuilt_valid)):
            raise ValueError("Numeric view and validity mask must reconstruct from retained source tokens")
        # Use immutable bytes backing so the WRITEABLE flag cannot be restored.
        values = np.frombuffer(values.tobytes(order="C"), dtype=np.float64).reshape(values.shape)
        valid = np.frombuffer(valid.tobytes(order="C"), dtype=np.bool_).reshape(valid.shape)
        object.__setattr__(self, "column_names", columns)
        object.__setattr__(self, "channel_descriptions", descriptions)
        object.__setattr__(self, "row_ids", rows)
        object.__setattr__(self, "raw_fields", raw)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "valid", valid)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        digest = hashlib.sha256()
        digest.update(self.values.tobytes(order="C"))
        digest.update(self.valid.tobytes(order="C"))
        digest.update(repr((self.source_doi, self.source_file, self.source_sha256,
                            self.publisher_checksum_algorithm, self.publisher_checksum,
                            self.csv_member, self.member_sha256, self.column_names,
                            self.channel_descriptions, self.row_ids, self.raw_fields)).encode())
        return digest.hexdigest()

    def require_current(self):
        """Recheck captured table and source identity before applying an operator."""
        if self._fingerprint() != self._seal:
            raise ValueError("Hydrogen-channel source receipt changed after loading")
        return self

    @property
    def publisher_experiment_label(self) -> str | None:
        """Return the publisher's ReadMe label, or None for unmapped attachments.

        This is an exact file-to-label lookup from the ReadMe asset identified by
        ``_CASE_LABEL_SOURCE_SHA256``. It does not decode any sensor channel or
        assign experimental conditions.
        """
        if self.source_doi != _DOI:
            return None
        stem = PurePosixPath(self.source_file).stem
        return _PUBLISHER_EXPERIMENT_LABELS.get(stem)


def load_hydrogen_channel_case(
    archive_path: str | Path,
    *,
    dataset: Dataset,
    file_name: str,
    expected_sha256: str | None = None,
) -> HydrogenChannelCase:
    """Read one admitted Figshare ZIP without aligning its clocks or naming quantities.

    The ZIP's single CSV is interpreted as a two-row header followed by numeric
    source records. Flow and sensor-time labels remain ordinary source text here;
    callers must use a separate evidence-backed adapter to assign units/clocks.
    """
    if (dataset.key != _DATASET_KEY or dataset.doi != _DOI or dataset.version != "2"
            or dataset.license_id != _LICENSE or dataset.validation_qualified
            or dataset.metadata_url != _METADATA_URL
            or dataset.metadata_sha256 != _METADATA_SHA256
            or hashlib.sha256(dataset.metadata_bytes).hexdigest() != _METADATA_SHA256):
        raise ValueError("Expected the admitted, not-yet-qualified hydrogen-channel V2 record")
    try:
        source_metadata = json.loads(dataset.metadata_bytes)
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError("Pinned Figshare metadata bytes are not valid JSON") from error
    source_files = source_metadata.get("files") if isinstance(source_metadata, dict) else None
    if not isinstance(source_files, list) or len(source_files) != 23:
        raise ValueError("Pinned Figshare metadata must retain its complete 23-file listing")
    try:
        expected_files = tuple(sorted((
            entry["name"], entry["download_url"], entry["size"], "md5",
            entry["computed_md5"].lower(),
        ) for entry in source_files))
        resolved_files = tuple(sorted((
            item.name, item.url, item.size_bytes, item.checksum_algorithm, item.checksum,
        ) for item in dataset.files))
    except (KeyError, AttributeError, TypeError) as error:
        raise ValueError("Figshare metadata or resolved attachment records are incomplete") from error
    if resolved_files != expected_files:
        raise ValueError("Resolved attachment records differ from the pinned Figshare metadata bytes")
    matches = tuple(item for item in dataset.files if item.name == file_name)
    if len(matches) != 1:
        raise ValueError("ZIP name must identify exactly one publisher-listed attachment")
    remote = matches[0]
    if remote.checksum_algorithm not in {"md5", "sha256"} or not remote.checksum:
        raise ValueError("A supported publisher checksum is required for source-bound ZIP loading")
    path = Path(archive_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Input must be a regular local ZIP file")
    if path.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP exceeds the bounded hydrogen-channel reader size")
    payload = path.read_bytes()
    source_digest = hashlib.sha256(payload).hexdigest()
    if (len(payload) != remote.size_bytes
            or hashlib.new(remote.checksum_algorithm, payload).hexdigest() != remote.checksum):
        raise ValueError("Local ZIP size or publisher checksum differs from the source listing")
    if expected_sha256 is not None:
        if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
                or any(character not in "0123456789abcdef" for character in expected_sha256)
                or source_digest != expected_sha256):
            raise ValueError("Local ZIP SHA-256 differs from the separately pinned source receipt")
    try:
        with ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            if len(infos) > 16:
                raise ValueError("Unexpected archive member count")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("Archive contains duplicate member paths")
            for name in names:
                item = PurePosixPath(name)
                if item.is_absolute() or ".." in item.parts or "\\" in name:
                    raise ValueError("Archive contains an unsafe member path")
            csv_infos = [info for info in infos if info.filename.lower().endswith(".csv")]
            if len(csv_infos) != 1:
                raise ValueError("Each release case archive must contain exactly one CSV table")
            csv_info = csv_infos[0]
            if csv_info.file_size > _MAX_CSV_BYTES:
                raise ValueError("CSV member exceeds the bounded source-table size")
            member_payload = archive.read(csv_info)
    except BadZipFile as error:
        raise ValueError("Publisher attachment is not a valid ZIP archive") from error
    try:
        text = member_payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Expected a UTF-8 CSV member") from error
    records = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    if len(records) < 3:
        raise ValueError("CSV must preserve two header rows and at least one data record")
    header, descriptions, source_rows = tuple(records[0]), tuple(records[1]), records[2:]
    width = len(header)
    if width == 0 or width > _MAX_COLUMNS or len(descriptions) != width:
        raise ValueError("Two header rows must have the same bounded column count")
    if len(source_rows) > _MAX_ROWS:
        raise ValueError("CSV exceeds the bounded source row count")
    values = np.full((len(source_rows), width), np.nan)
    valid = np.zeros((len(source_rows), width), dtype=bool)
    raw_fields = []
    for row_index, row in enumerate(source_rows):
        if len(row) > width:
            raise ValueError(f"Source record {row_index + 3} exceeds header width")
        raw_fields.append(tuple(row))
        for column_index, token in enumerate(row):
            if not token.strip():
                continue
            try:
                number = float(token.strip())
            except ValueError as error:
                raise ValueError(f"Nonnumeric source value at CSV record {row_index + 3}") from error
            if not math.isfinite(number):
                raise ValueError("Nonfinite source cells are rejected from the numeric view")
            values[row_index, column_index] = number
            valid[row_index, column_index] = True
    csv_member = csv_info.filename
    table = _issue_hydrogen_channel_case(
        source_doi=dataset.doi,
        source_file=file_name,
        source_sha256=source_digest,
        publisher_checksum_algorithm=remote.checksum_algorithm,
        publisher_checksum=remote.checksum,
        csv_member=csv_member,
        member_sha256=hashlib.sha256(member_payload).hexdigest(),
        column_names=header,
        channel_descriptions=descriptions,
        row_ids=tuple(f"{dataset.doi}:{csv_member}:record-{index + 3}" for index in range(len(source_rows))),
        raw_fields=tuple(raw_fields),
        values=values,
        valid=valid,
    )
    return table.require_current()


__all__ = ["HydrogenChannelCase", "load_hydrogen_channel_case"]
