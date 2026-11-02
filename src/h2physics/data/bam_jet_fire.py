"""Source-bound intake for BAM hydrogen-jet fire measurement text files.

The reader preserves channel labels, units, metadata and raw cell tokens. It does
not calibrate instruments, infer test conditions, or qualify a fire model.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

import numpy as np
from numpy.typing import NDArray

from ..units import convert_to_si
from .models import Dataset

_DATASET_KEY = "bam-hydrogen-jet-fire"
_DOI = "10.5281/zenodo.21026781"
_LICENSE = "CC-BY-4.0"
_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
_METADATA_URL = "https://zenodo.org/api/records/21026781"
_METADATA_SHA256 = "646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0"
_ARCHIVE_NAME = "H2_Data.zip"
_ARCHIVE_SIZE = 75_221_648
_ARCHIVE_MD5 = "019059edc40e776d6c54d917931e4e39"
_MAX_ARCHIVE_BYTES = 100_000_000
_MAX_ARCHIVE_MEMBERS = 512
_MAX_MEMBER_BYTES = 45_000_000
_MAX_ROWS = 250_000
_MAX_COLUMNS = 64
_ALLOWED_PREFIXES = (
    "H2_Data/FRP_exp/",
    "H2_Data/First_exp_set/Measurement_data/",
)
_PENDING_ISSUERS: set[object] = set()
_PENDING_UNIT_ISSUERS: set[object] = set()
_ISSUED_UNIT_PROJECTIONS: dict[object, int] = {}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _has_link_component(path: Path) -> bool:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError:
            return True
        if stat.S_ISLNK(info.st_mode):
            return True
        attributes = getattr(info, "st_file_attributes", 0)
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            return True
    return False


def _archive_checksums(path: Path) -> tuple[str, str]:
    sha256, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha256.update(block)
            md5.update(block)
    return sha256.hexdigest(), md5.hexdigest()


def _parse_decimal_cell(token: str, *, row_number: int, column_number: int) -> float | None:
    stripped = token.strip()
    if not stripped:
        return None
    if "," in stripped:
        if "." in stripped or stripped.count(",") != 1:
            raise ValueError(
                f"Ambiguous decimal separator at data row {row_number}, column {column_number}"
            )
        stripped = stripped.replace(",", ".")
    try:
        value = float(stripped)
    except ValueError as error:
        raise ValueError(
            f"Non-numeric source token at data row {row_number}, column {column_number}"
        ) from error
    if not math.isfinite(value):
        raise ValueError(
            "Nonfinite source cells are retained only as raw evidence, not numeric data"
        )
    return value


def _parse_measurement_text(text: str):
    """Parse the semicolon/comma-decimal export without unit conversion."""
    lines = text.splitlines()
    marker = next((index for index, line in enumerate(lines) if line.strip() == "Data1"), None)
    if marker is None:
        raise ValueError("BAM measurement export is missing its Data1 section marker")

    metadata_values = []
    for line in lines[:marker]:
        if ":" in line:
            name, value = line.split(":", 1)
            metadata_values.append((name.strip(), value.strip()))
    metadata_names = [name for name, _ in metadata_values]
    if len(metadata_names) != len(set(metadata_names)):
        raise ValueError("BAM measurement metadata contains duplicate field names")

    header_index = None
    columns = None
    for index in range(marker + 1, len(lines)):
        if not lines[index].strip():
            continue
        row = next(csv.reader([lines[index]], delimiter=";", strict=True))
        if "Time [s]" in row:
            header_index, columns = index, tuple(item.strip() for item in row)
            break
    if columns is None or not columns or len(columns) > _MAX_COLUMNS:
        raise ValueError("BAM export has no bounded channel header containing Time [s]")
    if any(not name for name in columns) or len(set(columns)) != len(columns):
        raise ValueError("BAM channel labels must be nonempty and unique")

    declared_channels = dict(metadata_values).get("Number of channels")
    if declared_channels is not None:
        try:
            count = int(declared_channels)
        except ValueError as error:
            raise ValueError("BAM declared channel count is not an integer") from error
        # The publisher's count covers measurement channels; the time
        # coordinate is an additional leading column in the text export.
        if count != len(columns) - 1:
            raise ValueError("BAM declared measurement-channel count differs from the non-time header width")

    values = []
    raw_rows = []
    masks = []
    for physical_line, line in enumerate(lines[header_index + 1:], start=1):
        if not line.strip():
            continue
        if len(values) >= _MAX_ROWS:
            raise ValueError("BAM measurement export exceeds the configured row limit")
        row = next(csv.reader([line], delimiter=";", strict=True))
        if len(row) > len(columns):
            raise ValueError(f"BAM data row {physical_line} exceeds channel header width")
        raw = tuple(row)
        numeric = [math.nan] * len(columns)
        valid = [False] * len(columns)
        for column, token in enumerate(raw):
            parsed = _parse_decimal_cell(token, row_number=physical_line, column_number=column + 1)
            if parsed is not None:
                numeric[column] = parsed
                valid[column] = True
        raw_rows.append(raw)
        values.append(numeric)
        masks.append(valid)
    if not values:
        raise ValueError("BAM export contains no measurement records after its channel header")

    matrix = np.asarray(values, dtype=np.float64)
    valid = np.asarray(masks, dtype=np.bool_)
    matrix = np.frombuffer(matrix.tobytes(order="C"), dtype=np.float64).reshape(matrix.shape)
    valid = np.frombuffer(valid.tobytes(order="C"), dtype=np.bool_).reshape(valid.shape)
    return tuple(lines[:marker]), columns, tuple(raw_rows), matrix, valid


def _issue_table(**values):
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        return BAMJetFireTable(**values, _issuer_token=token)
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class BAMJetFireTable:
    """One source-export text file with raw cells and an unconverted numeric view."""

    dataset_metadata_sha256: str
    source_archive_path: str
    source_archive_size_bytes: int
    source_archive_sha256: str
    publisher_checksum_algorithm: str
    publisher_checksum: str
    member_path: str
    member_sha256: str
    source_metadata: tuple[str, ...]
    column_names: tuple[str, ...]
    raw_rows: tuple[tuple[str, ...], ...]
    row_ids: tuple[str, ...]
    values: NDArray[np.float64]
    valid: NDArray[np.bool_]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise ValueError(
                "BAMJetFireTable instances are issued only by the checksum-validating reader"
            )
        _PENDING_ISSUERS.remove(self._issuer_token)
        if (not isinstance(self.dataset_metadata_sha256, str)
                or len(self.dataset_metadata_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.dataset_metadata_sha256)):
            raise ValueError("Retain the exact resolved source-metadata SHA-256")
        for name in ("source_archive_sha256", "member_sha256"):
            digest = getattr(self, name)
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)):
                raise ValueError(f"{name} must be a lowercase SHA-256")
        if (self.publisher_checksum_algorithm != "md5"
                or self.publisher_checksum != _ARCHIVE_MD5):
            raise ValueError("Retain the publisher-declared Zenodo archive MD5")
        path = PurePosixPath(self.member_path)
        if (path.is_absolute() or ".." in path.parts or "\\" in self.member_path
                or not self.member_path.endswith(".txt")
                or not self.member_path.startswith(_ALLOWED_PREFIXES)):
            raise ValueError("Only safe BAM measurement text members are admitted")
        columns = tuple(self.column_names)
        raw_rows = tuple(tuple(row) for row in self.raw_rows)
        metadata = tuple(self.source_metadata)
        row_ids = tuple(self.row_ids)
        if (not isinstance(self.source_archive_path, str) or not self.source_archive_path
                or not Path(self.source_archive_path).is_absolute()
                or type(self.source_archive_size_bytes) is not int
                or self.source_archive_size_bytes != _ARCHIVE_SIZE):
            raise ValueError("Retain the absolute archive path and publisher-declared byte count")
        if any(not isinstance(item, str) for item in metadata):
            raise ValueError("Source metadata lines must remain raw text")
        values = np.asarray(self.values)
        valid = np.asarray(self.valid)
        if (not columns or len(columns) > _MAX_COLUMNS or len(set(columns)) != len(columns)
                or any(not isinstance(item, str) or not item for item in columns)):
            raise ValueError("BAM channel labels must remain unique source strings")
        if (values.dtype.kind not in "iuf" or valid.dtype.kind != "b"
                or values.shape != valid.shape
                or values.shape != (len(raw_rows), len(columns))
                or not raw_rows or len(raw_rows) > _MAX_ROWS
                or len(row_ids) != len(raw_rows) or len(set(row_ids)) != len(row_ids)
                or any(not isinstance(item, str) or not item for item in row_ids)):
            raise ValueError("BAM numeric values, validity mask, rows and labels must align")
        rebuilt = np.full(values.shape, np.nan)
        rebuilt_valid = np.zeros(values.shape, dtype=bool)
        for row_index, row in enumerate(raw_rows):
            if len(row) > len(columns):
                raise ValueError("Retained BAM raw row exceeds the source header width")
            for column_index, token in enumerate(row):
                parsed = _parse_decimal_cell(
                    token, row_number=row_index + 1, column_number=column_index + 1,
                )
                if parsed is not None:
                    rebuilt[row_index, column_index] = parsed
                    rebuilt_valid[row_index, column_index] = True
        if (not np.array_equal(values, rebuilt, equal_nan=True)
                or not np.array_equal(valid, rebuilt_valid)):
            raise ValueError(
                "BAM numeric values and validity mask must reconstruct from raw source cells"
            )
        values = np.frombuffer(
            np.asarray(rebuilt, dtype="<f8").tobytes(), dtype="<f8",
        ).reshape(values.shape)
        valid = np.frombuffer(rebuilt_valid.tobytes(), dtype=np.bool_).reshape(valid.shape)
        object.__setattr__(self, "column_names", columns)
        object.__setattr__(self, "raw_rows", raw_rows)
        object.__setattr__(self, "row_ids", row_ids)
        object.__setattr__(self, "source_metadata", metadata)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "valid", valid)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        digest = hashlib.sha256()
        digest.update(repr((self.dataset_metadata_sha256, self.source_archive_path,
                            self.source_archive_size_bytes, self.source_archive_sha256,
                            self.publisher_checksum_algorithm, self.publisher_checksum,
                            self.member_path, self.member_sha256, self.source_metadata,
                            self.column_names, self.raw_rows, self.row_ids)).encode("utf-8"))
        digest.update(self.values.tobytes(order="C"))
        digest.update(self.valid.tobytes(order="C"))
        return digest.hexdigest()

    def require_current(self):
        """Reject changed parsed content or changed/deleted source archive bytes."""
        if self._fingerprint() != self._seal:
            raise ValueError("BAM measurement table changed after source-bound admission")
        path = Path(self.source_archive_path)
        if (_has_link_component(path) or not path.is_file()
                or path.stat().st_size != self.source_archive_size_bytes
                or _sha256_path(path) != self.source_archive_sha256):
            raise ValueError("BAM source archive changed or disappeared after loading")
        return self

    @property
    def row_count(self) -> int:
        self.require_current()
        return len(self.raw_rows)

    def column(self, source_label: str) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
        """Return values and validity for an exact publisher channel label.

        The label, including its unit text, remains the only quantity metadata;
        callers own any unit conversion or physical observation mapping.
        """
        self.require_current()
        try:
            index = self.column_names.index(source_label)
        except ValueError as error:
            raise KeyError(source_label) from error
        return self.values[:, index], self.valid[:, index]


@dataclass(frozen=True, slots=True)
class BAMRawChannel:
    """Channel retained as exact source tokens because its meaning/unit is unresolved."""

    source_label: str
    raw_tokens: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class BAMUnitChannel:
    """Explicitly unit-described channel with a normalized numeric view and raw tokens."""

    source_label: str
    quantity: str
    source_unit_text: str
    si_unit: str
    conversion: str
    raw_tokens: tuple[str, ...]
    values_si: tuple[float | None, ...]
    semantic_boundary: str


@dataclass(frozen=True, slots=True)
class BAMJetFireUnitProjection:
    """Hash-bound unit projection; all unrecognized columns remain raw in the parent."""

    source_table: BAMJetFireTable
    normalized_channels: tuple[BAMUnitChannel, ...]
    raw_only_channels: tuple[BAMRawChannel, ...]
    dataset_doi: str
    creator: str
    license_id: str
    license_url: str
    dataset_metadata_sha256: str
    source_archive_sha256: str
    member_path: str
    member_sha256: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_UNIT_ISSUERS:
            raise ValueError("BAM unit projections are issued only by the source-bound projector")
        _PENDING_UNIT_ISSUERS.remove(self._issuer_token)

    def require_current(self):
        if _ISSUED_UNIT_PROJECTIONS.get(self._issuer_token) != id(self.source_table):
            raise ValueError("BAM unit projection is not bound to its issued source table")
        self.source_table.require_current()
        expected = _build_unit_projection_fields(self.source_table)
        for name, value in expected.items():
            if getattr(self, name) != value:
                raise ValueError(f"BAM unit projection field {name!r} differs from its source table")
        return self


def _check_dataset(dataset: Dataset):
    if (type(dataset) is not Dataset or dataset.key != _DATASET_KEY
            or dataset.doi != _DOI or dataset.license_id != _LICENSE
            or dataset.license_url.rstrip("/") != _LICENSE_URL.rstrip("/")
            or dataset.metadata_url != _METADATA_URL or dataset.version != "21026781"
            or dataset.metadata_sha256 != _METADATA_SHA256
            or _sha256_bytes(dataset.metadata_bytes) != _METADATA_SHA256
            or not dataset.acquisition_permitted or dataset.origin != "measured"):
        raise ValueError("Expected the pinned open, measured BAM hydrogen-jet-fire Zenodo record")
    try:
        metadata = json.loads(dataset.metadata_bytes)
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError("Resolved BAM source metadata is not valid JSON") from error
    record_metadata = metadata.get("metadata", {}) if isinstance(metadata, dict) else {}
    if not isinstance(record_metadata, dict):
        raise ValueError("BAM record metadata has an invalid structure")
    license_record = record_metadata.get("license")
    if (not isinstance(license_record, dict)
            or metadata.get("doi") != _DOI or record_metadata.get("doi") != _DOI
            or record_metadata.get("access_right") != "open"
            or license_record.get("id") != "cc-by-4.0"):
        raise ValueError(
            "BAM metadata bytes do not retain the expected DOI, open status and license"
        )
    if len(dataset.files) != 1:
        raise ValueError("BAM record must retain its complete single-file attachment listing")
    remote = dataset.files[0]
    listed = metadata.get("files", [])
    if (len(listed) != 1 or remote.name != _ARCHIVE_NAME
            or listed[0].get("key") != remote.name
            or listed[0].get("size") != remote.size_bytes
            or listed[0].get("checksum") != f"md5:{remote.checksum}"
            or listed[0].get("links", {}).get("self") != remote.url
            or remote.size_bytes != _ARCHIVE_SIZE
            or remote.checksum_algorithm != "md5"
            or remote.checksum != _ARCHIVE_MD5):
        raise ValueError("Resolved BAM attachment differs from the complete pinned Zenodo listing")
    return remote


def load_bam_jet_fire_text(
    archive_path: str | Path,
    *,
    dataset: Dataset,
    member_path: str,
    expected_sha256: str | None = None,
) -> BAMJetFireTable:
    """Load one measurement text member after record, size and checksum checks.

    Only the FRP fire-reference-plate or first-experiment measurement folders are
    admitted. Infrared binaries, images and camera conversion assets are not parsed.
    """
    remote = _check_dataset(dataset)
    if not isinstance(member_path, str):
        raise TypeError("BAM member path must be text")
    member = PurePosixPath(member_path)
    if (member.is_absolute() or ".." in member.parts or "\\" in member_path
            or not member_path.endswith(".txt")
            or not member_path.startswith(_ALLOWED_PREFIXES)):
        raise ValueError("Select a safe BAM measurement text member from an admitted folder")
    path = Path(archive_path)
    if _has_link_component(path) or not path.is_file():
        raise ValueError("BAM archive must be a regular non-symlink file")
    size = path.stat().st_size
    if size != remote.size_bytes or size > _MAX_ARCHIVE_BYTES:
        raise ValueError("BAM archive size differs from the publisher record or configured limit")
    source_sha256, source_md5 = _archive_checksums(path)
    if expected_sha256 is not None:
        if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
                or any(c not in "0123456789abcdef" for c in expected_sha256)
                or source_sha256 != expected_sha256):
            raise ValueError("BAM archive SHA-256 differs from the separate acquisition receipt")
    if source_md5 != remote.checksum:
        raise ValueError("BAM archive bytes do not match the publisher's MD5 checksum")
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > _MAX_ARCHIVE_MEMBERS:
                raise ValueError("BAM archive exceeds the configured member-count limit")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("BAM archive contains duplicate member names")
            for info in infos:
                name = info.filename
                safe_name = PurePosixPath(name)
                mode = (info.external_attr >> 16) & 0xFFFF
                if (safe_name.is_absolute() or ".." in safe_name.parts
                        or "\\" in name or stat.S_ISLNK(mode)):
                    raise ValueError("BAM archive contains an unsafe path or symbolic-link member")
            matches = [info for info in infos if info.filename == member_path]
            if len(matches) != 1:
                raise ValueError("Requested BAM measurement member is absent or duplicated")
            info = matches[0]
            if info.file_size < 1 or info.file_size > _MAX_MEMBER_BYTES or info.is_dir():
                raise ValueError("Requested BAM text member has an invalid size or type")
            member_bytes = archive.read(info)
    except BadZipFile as error:
        raise ValueError("Publisher attachment is not a valid ZIP archive") from error
    try:
        text = member_bytes.decode("cp1252")
    except UnicodeDecodeError as error:
        raise ValueError("BAM measurement export is not decodable as Windows-1252 text") from error
    metadata, columns, raw_rows, values, valid = _parse_measurement_text(text)
    table = _issue_table(
        dataset_metadata_sha256=dataset.metadata_sha256,
        source_archive_path=str(path.resolve()),
        source_archive_size_bytes=size,
        source_archive_sha256=source_sha256,
        publisher_checksum_algorithm=remote.checksum_algorithm,
        publisher_checksum=remote.checksum,
        member_path=member_path,
        member_sha256=_sha256_bytes(member_bytes),
        source_metadata=metadata,
        column_names=columns,
        raw_rows=raw_rows,
        row_ids=tuple(
            f"{_DOI}:{member_path}:record-{index + 1}" for index in range(len(raw_rows))
        ),
        values=values,
        valid=valid,
    )
    return table.require_current()


def _recognized_unit_channel(label: str):
    if label == "Time [s]":
        return "time", "s", "s", "identity", (
            "publisher-labelled time coordinate; origin, trigger and clock synchronization unresolved"
        )
    if label.startswith("Massenstrom") and label.endswith("[kg/h]"):
        return "mass_flow", "kg/h", "kg/s", "divide by 3600", (
            "publisher-labelled mass flow; sign convention, instrument calibration and boundary assignment unresolved"
        )
    if label.endswith("[V]"):
        return "voltage", "V", "V", "identity", (
            "sensor voltage only; sensor transfer function and calibrated physical quantity unresolved"
        )
    if label.lower().endswith("[bar]"):
        return "reported_pressure", label.rsplit("[", 1)[1][:-1], "Pa", (
            "bar_to_Pa dimension only"
        ), "reported pressure; absolute/gauge basis and sensor calibration unresolved"
    return None


def _build_unit_channels(column_names, raw_rows):
    column_indices = {name: index for index, name in enumerate(column_names)}
    normalized = []
    raw_only = []
    for label, column_index in column_indices.items():
        mapping = _recognized_unit_channel(label)
        tokens = tuple(
            row[column_index] if column_index < len(row) else ""
            for row in raw_rows
        )
        if mapping is None:
            reason = (
                "temperature-like label contains an unresolved T-difference marker; absolute versus differential Celsius semantics are not assigned"
                if "°C" in label else
                "unit or measurement interpretation is not admitted from this channel label"
            )
            raw_only.append(BAMRawChannel(label, tokens, reason))
            continue
        quantity, source_unit, si_unit, conversion, boundary = mapping
        parsed_values = tuple(
            _parse_decimal_cell(token, row_number=row_index + 1,
                                column_number=column_index + 1)
            for row_index, token in enumerate(tokens)
        )
        present_positions = tuple(
            index for index, value in enumerate(parsed_values) if value is not None
        )
        converted: list[float | None] = [None] * len(tokens)
        if present_positions:
            values = [parsed_values[index] for index in present_positions]
            with np.errstate(over="ignore", invalid="ignore"):
                if quantity == "reported_pressure":
                    si_values = convert_to_si(values, quantity=quantity, unit="bar",
                                              pressure_basis=None)
                else:
                    si_values = convert_to_si(values, quantity=quantity, unit=source_unit)
            if not np.all(np.isfinite(si_values)):
                raise ValueError(
                    f"BAM channel {label!r} overflows its normalized numeric representation"
                )
            for index, value in zip(present_positions, si_values, strict=True):
                converted[index] = float(value)
        normalized.append(BAMUnitChannel(
            source_label=label,
            quantity=quantity,
            source_unit_text=source_unit,
            si_unit=si_unit,
            conversion=conversion,
            raw_tokens=tokens,
            values_si=tuple(converted),
            semantic_boundary=boundary,
        ))
    return tuple(normalized), tuple(raw_only)


def _build_unit_projection_fields(table: BAMJetFireTable):
    normalized, raw_only = _build_unit_channels(table.column_names, table.raw_rows)
    return {
        "normalized_channels": normalized,
        "raw_only_channels": raw_only,
        "dataset_doi": _DOI,
        "creator": "Maximilian Naster",
        "license_id": _LICENSE,
        "license_url": _LICENSE_URL,
        "dataset_metadata_sha256": table.dataset_metadata_sha256,
        "source_archive_sha256": table.source_archive_sha256,
        "member_path": table.member_path,
        "member_sha256": table.member_sha256,
    }


def project_bam_jet_fire_units(table: BAMJetFireTable) -> BAMJetFireUnitProjection:
    """Build unit-normalized views for explicit label units; retain other channels raw."""
    if type(table) is not BAMJetFireTable:
        raise TypeError("Expected a source-bound BAMJetFireTable")
    table.require_current()
    values = _build_unit_projection_fields(table)
    token = object()
    _PENDING_UNIT_ISSUERS.add(token)
    try:
        projection = BAMJetFireUnitProjection(source_table=table, **values,
                                              _issuer_token=token)
    except Exception:
        _PENDING_UNIT_ISSUERS.discard(token)
        raise
    _ISSUED_UNIT_PROJECTIONS[token] = id(table)
    return projection


def load_bam_jet_fire_unit_view(
    archive_path: str | Path,
    *,
    dataset: Dataset,
    member_path: str,
    expected_sha256: str | None = None,
) -> BAMJetFireUnitProjection:
    """Load and checksum one BAM text member, then expose only explicit-unit channels."""
    table = load_bam_jet_fire_text(
        archive_path,
        dataset=dataset,
        member_path=member_path,
        expected_sha256=expected_sha256,
    )
    return project_bam_jet_fire_units(table)


__all__ = [
    "BAMJetFireTable", "BAMRawChannel", "BAMUnitChannel", "BAMJetFireUnitProjection",
    "load_bam_jet_fire_text", "project_bam_jet_fire_units", "load_bam_jet_fire_unit_view",
]
