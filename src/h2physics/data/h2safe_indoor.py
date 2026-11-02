"""Source-bound access to the open H2SAFE indoor-release sensor archive.

Values remain raw sensor reports: no calibration, concentration-unit conversion,
clock synchronization, or geometry interpretation is performed here.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile


DATASET_ID = "https://data.openei.org/submissions/8799"
LICENSE_ID = "CC-BY-4.0"
METADATA_SHA256 = "8bbae3bdca015f577d6c06d7d76222f081aa1c67085095b6fae87defc47dfd42"
ARCHIVE_NAME = "1787856683-Dataset.zip"
ARCHIVE_SIZE_BYTES = 3_766_528
ARCHIVE_SHA256 = "f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e"
MAX_ARCHIVE_BYTES = 5_000_000
MAX_EXPANDED_BYTES = 80_000_000
MAX_MEMBERS = 16
MAX_ROWS = 500_000
MAX_COLUMNS = 128

_LABS = ("Lab1_Small", "Lab2_Large")
_EXPERIMENTS = {
    "Lab1_Small": frozenset(("test1.csv",)),
    "Lab2_Large": frozenset((f"test{i}.csv" for i in range(1, 5))),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _allowed_members():
    allowed = set()
    for lab, experiments in _EXPERIMENTS.items():
        allowed.add(f"{lab}/")
        allowed.add(f"{lab}/sensors.csv")
        allowed.update(f"{lab}/{name}" for name in experiments)
        mesh = "Lab1_small" if lab == "Lab1_Small" else "Lab2_Large"
        allowed.update((f"{lab}/{mesh}.STEP", f"{lab}/{mesh}.STL"))
    return frozenset(allowed)


_ALLOWED_MEMBERS = _allowed_members()
_PENDING_SERIES_ISSUERS: set[object] = set()


@dataclass(frozen=True, slots=True)
class H2SafeSensor:
    """One archive sensor row; coordinate basis and units stay source-bound."""

    sensor_id: str
    coordinate_tokens: tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class H2SafeIndoorSeries:
    """Immutable single-experiment records with both raw and numeric views."""

    archive_path: Path
    archive_sha256: str
    metadata_sha256: str
    dataset_id: str
    license_id: str
    experiment: str
    channel_ids: tuple[str, ...]
    sensors: tuple[H2SafeSensor, ...]
    raw_tokens: tuple[tuple[str, ...], ...]
    time_values: tuple[float, ...]
    sensor_values: tuple[tuple[float | None, ...], ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SERIES_ISSUERS:
            raise TypeError("H2SAFE series can only be issued by the checksum-bound reader")
        _PENDING_SERIES_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        path = Path(self.archive_path).resolve()
        if self.archive_sha256 != ARCHIVE_SHA256:
            raise ValueError("H2SAFE archive receipt has an unexpected pinned SHA-256")
        if self.metadata_sha256 != METADATA_SHA256 or self.dataset_id != DATASET_ID:
            raise ValueError("H2SAFE repository identity differs from the reviewed receipt")
        if self.license_id != LICENSE_ID:
            raise ValueError("H2SAFE license identity differs from the reviewed receipt")
        if len(self.raw_tokens) != len(self.time_values) or len(self.raw_tokens) != len(self.sensor_values):
            raise ValueError("H2SAFE time, token and numeric rows must align")
        width = len(self.channel_ids)
        if width == 0 or len(set(self.channel_ids)) != width:
            raise ValueError("H2SAFE channel identifiers must be nonempty and unique")
        if any(len(row) != width + 1 for row in self.raw_tokens):
            raise ValueError("H2SAFE raw rows do not match the declared channel order")
        if any(len(row) != width for row in self.sensor_values):
            raise ValueError("H2SAFE numeric rows do not match the declared channel order")
        object.__setattr__(self, "archive_path", path)

    @property
    def concentration_unit(self) -> str:
        """The archive's sensor value unit is not qualified by this reader."""
        return "source_unit_unresolved"

    @property
    def time_unit(self) -> str:
        """A numeric source clock is retained without inferring a time basis."""
        return "source_time_unit_unresolved"

    def require_current(self):
        if _sha256(self.archive_path) != self.archive_sha256:
            raise RuntimeError("H2SAFE archive changed after the series was loaded")
        return self


def _parse_numeric(token: str, *, row_number: int, column: str, allow_missing: bool):
    stripped = token.strip()
    if allow_missing and (not stripped or stripped.upper() in {"#N/A", "NA", "N/A"}):
        return None
    try:
        value = float(stripped)
    except ValueError as error:
        raise ValueError(f"Non-numeric H2SAFE value at row {row_number}, column {column!r}") from error
    if not math.isfinite(value):
        raise ValueError(f"Non-finite H2SAFE value at row {row_number}, column {column!r}")
    return value


def _parse_sensors(payload: bytes) -> tuple[H2SafeSensor, ...]:
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig", errors="strict"), newline=""))
        if tuple(reader.fieldnames or ()) != ("id", "X", "Y", "Z"):
            raise ValueError("H2SAFE sensor map does not match the reviewed four-column schema")
        sensors = []
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(key) is None for key in ("id", "X", "Y", "Z")):
                raise ValueError(f"Malformed H2SAFE sensor map row {row_number}")
            sensor_id = row["id"].strip()
            coordinates = tuple(row[key].strip() for key in ("X", "Y", "Z"))
            if not sensor_id or not all(coordinates):
                raise ValueError(f"Empty H2SAFE sensor identity/coordinate at row {row_number}")
            # Check that coordinate tokens can be inspected numerically while
            # retaining their exact text and making no length/frame assumption.
            for key, token in zip(("X", "Y", "Z"), coordinates):
                _parse_numeric(token, row_number=row_number, column=key, allow_missing=False)
            sensors.append(H2SafeSensor(sensor_id, coordinates))
        if not sensors or len({item.sensor_id.casefold() for item in sensors}) != len(sensors):
            raise ValueError("H2SAFE sensor identities must be present and unique")
        return tuple(sensors)
    except UnicodeDecodeError as error:
        raise ValueError("H2SAFE sensor map is not UTF-8 text") from error


def _parse_series(payload: bytes, *, archive_path: Path, archive_sha256: str,
                  experiment: str, sensors: tuple[H2SafeSensor, ...]) -> H2SafeIndoorSeries:
    try:
        reader = csv.reader(io.StringIO(payload.decode("utf-8-sig", errors="strict"), newline=""), strict=True)
        header = next(reader, None)
        if not header or len(header) < 2 or header[0].strip() != "time":
            raise ValueError("H2SAFE experiment CSV must begin with the source time column")
        channels = tuple(item.strip() for item in header[1:])
        if (len(channels) > MAX_COLUMNS or any(not item for item in channels)
                or len(set(item.casefold() for item in channels)) != len(channels)):
            raise ValueError("H2SAFE experiment channel labels must be bounded and unique")
        sensor_map = {item.sensor_id.casefold() for item in sensors}
        if any(channel.casefold() not in sensor_map for channel in channels):
            raise ValueError("H2SAFE experiment channel is absent from its sensor-position map")
        raw_rows, times, values = [], [], []
        for row_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(f"H2SAFE experiment row {row_number} has the wrong number of columns")
            if len(raw_rows) >= MAX_ROWS:
                raise ValueError("H2SAFE experiment exceeds the configured row budget")
            tokens = tuple(item.strip() for item in row)
            time = _parse_numeric(tokens[0], row_number=row_number, column="time", allow_missing=False)
            channels_numeric = tuple(
                _parse_numeric(token, row_number=row_number, column=channel, allow_missing=True)
                for channel, token in zip(channels, tokens[1:])
            )
            raw_rows.append(tokens)
            times.append(time)
            values.append(channels_numeric)
        if not raw_rows:
            raise ValueError("H2SAFE experiment contains no observations")
        token = object()
        _PENDING_SERIES_ISSUERS.add(token)
        try:
            return H2SafeIndoorSeries(
                archive_path, archive_sha256, METADATA_SHA256, DATASET_ID, LICENSE_ID,
                experiment, channels, sensors, tuple(raw_rows), tuple(times), tuple(values), token,
            )
        except Exception:
            _PENDING_SERIES_ISSUERS.discard(token)
            raise
    except UnicodeDecodeError as error:
        raise ValueError("H2SAFE experiment is not UTF-8 text") from error
    except csv.Error as error:
        raise ValueError("Malformed H2SAFE experiment CSV") from error


def load_h2safe_indoor_series(path, *, experiment: str,
                              expected_sha256: str = ARCHIVE_SHA256) -> H2SafeIndoorSeries:
    """Load one named experiment after verifying the complete CC BY archive.

    ``experiment`` is a repository-relative name such as
    ``Lab1_Small/test1.csv`` or ``Lab2_Large/test3.csv``. Sensor readings and
    source clock numbers are not calibrated or unit-converted.
    """
    supplied_path = Path(path)
    if supplied_path.is_symlink():
        raise ValueError("H2SAFE archive path cannot be a symbolic link")
    source = supplied_path.resolve(strict=True)
    if expected_sha256 != ARCHIVE_SHA256:
        raise ValueError("Caller checksum must match the reviewed H2SAFE archive receipt")
    if source.stat().st_size != ARCHIVE_SIZE_BYTES or source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("H2SAFE archive byte size differs from the pinned repository asset")
    digest = _sha256(source)
    if digest != expected_sha256:
        raise ValueError("H2SAFE archive SHA-256 differs from the declared receipt")
    normalized = PurePosixPath(experiment)
    if normalized.is_absolute() or ".." in normalized.parts or len(normalized.parts) != 2:
        raise ValueError("H2SAFE experiment must be a safe Lab/test CSV name")
    lab, filename = normalized.parts
    if lab not in _EXPERIMENTS or filename not in _EXPERIMENTS[lab]:
        raise ValueError("Requested H2SAFE experiment is not part of the reviewed archive")
    sensor_name = f"{lab}/sensors.csv"
    try:
        with ZipFile(source, "r") as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(infos) > MAX_MEMBERS or len(names) != len(set(names)):
                raise ValueError("H2SAFE archive member list is duplicated or exceeds its budget")
            if set(names) != _ALLOWED_MEMBERS:
                raise ValueError("H2SAFE archive members differ from the reviewed allowlist")
            expanded = 0
            for info in infos:
                member = PurePosixPath(info.filename)
                if (member.is_absolute() or ".." in member.parts
                        or info.compress_type not in (ZIP_STORED, ZIP_DEFLATED)
                        or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK):
                    raise ValueError("Unsafe or unsupported H2SAFE archive member")
                expanded += info.file_size
            if expanded > MAX_EXPANDED_BYTES:
                raise ValueError("H2SAFE expanded archive exceeds the configured byte budget")
            sensor_info = archive.getinfo(sensor_name)
            experiment_info = archive.getinfo(normalized.as_posix())
            if sensor_info.file_size > 2_000_000 or experiment_info.file_size > 32_000_000:
                raise ValueError("H2SAFE CSV member exceeds its individual byte budget")
            sensors = _parse_sensors(archive.read(sensor_info))
            payload = archive.read(experiment_info)
    except BadZipFile as error:
        raise ValueError("H2SAFE source is not the expected ZIP archive") from error
    return _parse_series(payload, archive_path=source, archive_sha256=digest,
                         experiment=normalized.as_posix(), sensors=sensors)
