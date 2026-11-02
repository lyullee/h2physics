"""Source-bound cryogenic hydrogen phase-change observations.

The reader retains three publisher CSV tables from one NIST/Mendeley test.
DAQ and neutron-image clocks remain independent; the phase-rate label keeps
its source spelling because its unit is not established by the table schema.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


SOURCE_DOI = "10.17632/z5zc7kk76g.2"
SOURCE_DATASET_ID = "z5zc7kk76g"
SOURCE_VERSION = 2
SOURCE_LICENSE = "CC-BY-4.0"
SOURCE_METADATA_SHA256 = "bcf8178e8fefaF7d3ee93a7b5e05810cea2e097f442eb7342381d4c9cba32060".lower()
SOURCE_FILE_LIST_SHA256 = "e1531696823824e32e1d0049c876b061aa1a07b3e172ea5d347f5c1a1f6f582b"
SOURCE_ARCHIVE_FILENAME = "CryoNeutronExpData.zip"
SOURCE_ARCHIVE_SIZE_BYTES = 4_511_372_825
SOURCE_ARCHIVE_SHA256 = "46301398eeed7c93d7c522581422f45ff5664a844abd412a2d40bcdd175cbbed"
SOURCE_ARCHIVE_SHA256_IS_PUBLISHER_DECLARED = True

RUN_RELATIVE_PATH = "Jan(H2)/jan_tc1/jan_tc1_run1"
RUN_ID = "jan_tc1_run1_exp"
CELL_TYPE = "conical cell"
REPORTED_CONDITIONS = {
    "pressure_psia": 17.9,
    "saturation_temperature_k": 21.0,
    "condensation_subcool_temperature_k": (20.8, 20.6),
    "evaporation_superheat_temperature_k": (22.0, 23.0),
}

DAQ_MEMBER = "Jan(H2)/jan_tc1/jan_tc1_run1/jan_tc1_run1_exp_daq.csv"
IMAGE_MEMBER = "Jan(H2)/jan_tc1/jan_tc1_run1/jan_tc1_run1_exp_img.csv"
RATE_MEMBER = "Jan(H2)/jan_tc1/jan_tc1_run1/jan_tc1_run1_exp_img_rate.csv"

_DAQ_NAME = "jan_tc1_run1_exp_daq.csv"
_IMAGE_NAME = "jan_tc1_run1_exp_img.csv"
_RATE_NAME = "jan_tc1_run1_exp_img_rate.csv"
_FILE_PINS = {
    _DAQ_NAME: (302_376, "0589fedf062cf036993fd48ffbed81c8b4a1ee502cd19b6a23935839aab37851", "ABF820A8"),
    _IMAGE_NAME: (195_985, "abfbb4fc35f7008ca4224daed6e27ae5cb182901140f93aab4100ae5162768e0", "E2FB6E85"),
    _RATE_NAME: (905, "dd62eabc62a15c32f3ed0457649240b9f5990e57db1d45e5d829b8f0808aad16", "09054FD9"),
}
_DAQ_HEADER = (
    "daq_time", "daq_s1", "daq_s2", "daq_s3", "daq_s4", "daq_htr",
    "daq_stick", "daq_p_kpa", "daq_htr_pow",
)
_IMAGE_HEADER = (
    "img_no", "img_filename", "img_timestamp", "img_time", "img_s1",
    "img_s2", "img_s3", "img_s4", "img_htr", "img_stick", "img_p_kpa",
    "img_htr_pow", "vol_it_mm3", "vol_od_mm3", "thickness_um", "apex",
)
_RATE_HEADER = (
    "tcrun", "temp_k", "press_kpa", "rate_od_mug", "od_error",
    "start_img", "stop_img", "temp_dev_k", "press_dev_kpa",
)
_PENDING_ISSUERS: set[object] = set()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _number(token: str, *, row: int, column: str) -> float | None:
    text = token.strip()
    if not text or text.upper() in {"NAN", "NA", "N/A"}:
        return None
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError(f"Non-numeric source token in row {row}, column {column!r}") from error
    if not math.isfinite(value):
        raise ValueError(f"Non-finite source token in row {row}, column {column!r}")
    return value


def _integer(token: str, *, row: int, column: str) -> int:
    value = _number(token, row=row, column=column)
    if value is None or not value.is_integer():
        raise ValueError(f"Expected an integer source token in row {row}, column {column!r}")
    return int(value)


def _read_table(path: Path, expected_name: str, expected_header: tuple[str, ...]):
    if path.is_symlink() or path.name != expected_name:
        raise ValueError("Select a regular file with the reviewed source-member basename")
    size, expected_sha, _ = _FILE_PINS[expected_name]
    if path.stat().st_size != size or _sha256(path) != expected_sha:
        raise ValueError(f"Source member {expected_name!r} differs from its pinned size/hash")
    payload = path.read_bytes()
    try:
        reader = csv.reader(io.StringIO(payload.decode("utf-8-sig", errors="strict"), newline=""), strict=True)
        header = next(reader, None)
        if tuple(header or ()) != expected_header:
            raise ValueError(f"Source columns changed for {expected_name!r}")
        rows = []
        for row_number, row in enumerate(reader, start=2):
            if not row or all(not token.strip() for token in row):
                continue
            if len(row) != len(expected_header):
                raise ValueError(f"Wrong column count in {expected_name!r} row {row_number}")
            rows.append(tuple(token.strip() for token in row))
        if not rows:
            raise ValueError(f"Source member {expected_name!r} has no observations")
        return payload, tuple(rows)
    except UnicodeDecodeError as error:
        raise ValueError(f"Source member {expected_name!r} is not UTF-8 text") from error
    except csv.Error as error:
        raise ValueError(f"Malformed CSV source member {expected_name!r}") from error


@dataclass(frozen=True, slots=True)
class CryoNeutronDAQPoint:
    time_s: float
    temperatures_k: tuple[float | None, float | None, float | None, float | None, float | None, float | None]
    pressure_kpa: float | None
    heater_power_percent_of_5w: float | None
    raw_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CryoNeutronImagePoint:
    image_number: int
    filename: str
    timestamp_token: str
    image_elapsed_time_s: float
    temperatures_k: tuple[float | None, float | None, float | None, float | None, float | None, float | None]
    pressure_kpa: float | None
    heater_power_percent_of_5w: float | None
    volume_interface_tracking_mm3: float | None
    volume_optical_density_mm3: float | None
    film_thickness_um: float | None
    apex_pixel_token: str
    raw_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CryoNeutronRateWindow:
    test_run_token: str
    mean_temperature_k: float | None
    mean_pressure_kpa: float | None
    rate_od_mug_value: float | None
    reported_error_value: float | None
    start_image_number: int
    stop_image_number: int
    temperature_deviation_k: float | None
    pressure_deviation_kpa: float | None
    raw_tokens: tuple[str, ...]

    rate_unit: ClassVar[str] = "unresolved_source_label:rate_od_mug"
    error_unit: ClassVar[str] = "unresolved_source_label:od_error"


_SOURCE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CryoNeutronPhaseChangeRun:
    source_doi: str
    dataset_id: str
    version: int
    license_id: str
    publisher_archive_sha256: str
    selected_member_crcs: tuple[tuple[str, str], ...]
    daq_path: Path
    image_path: Path
    rate_path: Path
    daq_sha256: str
    image_sha256: str
    rate_sha256: str
    daq_points: tuple[CryoNeutronDAQPoint, ...]
    image_points: tuple[CryoNeutronImagePoint, ...]
    rate_windows: tuple[CryoNeutronRateWindow, ...]
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_ISSUERS:
            raise TypeError("A source run can only be issued by the hash-bound member reader")
        _PENDING_ISSUERS.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        if (self.source_doi != SOURCE_DOI or self.dataset_id != SOURCE_DATASET_ID
                or self.version != SOURCE_VERSION or self.license_id != SOURCE_LICENSE
                or self.publisher_archive_sha256 != SOURCE_ARCHIVE_SHA256):
            raise ValueError("Dataset identity, version, rights, or archive receipt changed")
        if set(self.selected_member_crcs) != {
            (DAQ_MEMBER, "ABF820A8"), (IMAGE_MEMBER, "E2FB6E85"), (RATE_MEMBER, "09054FD9"),
        }:
            raise ValueError("Selected source-member CRC receipt changed")
        if not self.daq_points or not self.image_points or not self.rate_windows:
            raise ValueError("The selected experiment requires all three nonempty source tables")
        for name in ("daq_path", "image_path", "rate_path"):
            object.__setattr__(self, name, Path(getattr(self, name)).resolve())

    @property
    def daq_time_unit(self) -> str:
        return "s"

    @property
    def image_time_unit(self) -> str:
        return "s"

    @property
    def image_timestamp_timezone(self) -> str:
        return "unresolved_source_local_time"

    @property
    def rate_source_label(self) -> str:
        return "rate_od_mug"

    def require_current(self):
        for path, digest in ((self.daq_path, self.daq_sha256),
                             (self.image_path, self.image_sha256),
                             (self.rate_path, self.rate_sha256)):
            if _sha256(path) != digest:
                raise RuntimeError("A selected cryogenic source CSV changed after loading")
        return self


def load_cryo_neutron_phase_change_run(run_directory: str | Path) -> CryoNeutronPhaseChangeRun:
    """Read the three CC BY 4.0 CSV members for ``Jan(H2)/jan_tc1/run1``.

    The outer 4.51 GB ZIP is not needed locally. The selected member bytes must
    match pinned extracted-file hashes; their ZIP CRC32 values bind the partial
    HTTP-range extraction to the publisher's version-2 archive directory.
    """
    root = Path(run_directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Supply a regular run directory containing the three selected CSVs")
    daq_path, image_path, rate_path = root / _DAQ_NAME, root / _IMAGE_NAME, root / _RATE_NAME
    daq_bytes, daq_rows = _read_table(daq_path, _DAQ_NAME, _DAQ_HEADER)
    image_bytes, image_rows = _read_table(image_path, _IMAGE_NAME, _IMAGE_HEADER)
    rate_bytes, rate_rows = _read_table(rate_path, _RATE_NAME, _RATE_HEADER)

    daq = tuple(CryoNeutronDAQPoint(
        time_s=_number(row[0], row=index, column="daq_time"),
        temperatures_k=tuple(_number(row[i], row=index, column=_DAQ_HEADER[i]) for i in range(1, 7)),
        pressure_kpa=_number(row[7], row=index, column="daq_p_kpa"),
        heater_power_percent_of_5w=_number(row[8], row=index, column="daq_htr_pow"),
        raw_tokens=row,
    ) for index, row in enumerate(daq_rows, start=2))
    images = tuple(CryoNeutronImagePoint(
        image_number=_integer(row[0], row=index, column="img_no"),
        filename=row[1], timestamp_token=row[2],
        image_elapsed_time_s=_number(row[3], row=index, column="img_time"),
        temperatures_k=tuple(_number(row[i], row=index, column=_IMAGE_HEADER[i]) for i in range(4, 10)),
        pressure_kpa=_number(row[10], row=index, column="img_p_kpa"),
        heater_power_percent_of_5w=_number(row[11], row=index, column="img_htr_pow"),
        volume_interface_tracking_mm3=_number(row[12], row=index, column="vol_it_mm3"),
        volume_optical_density_mm3=_number(row[13], row=index, column="vol_od_mm3"),
        film_thickness_um=_number(row[14], row=index, column="thickness_um"),
        apex_pixel_token=row[15], raw_tokens=row,
    ) for index, row in enumerate(image_rows, start=2))
    rates = tuple(CryoNeutronRateWindow(
        test_run_token=row[0],
        mean_temperature_k=_number(row[1], row=index, column="temp_k"),
        mean_pressure_kpa=_number(row[2], row=index, column="press_kpa"),
        rate_od_mug_value=_number(row[3], row=index, column="rate_od_mug"),
        reported_error_value=_number(row[4], row=index, column="od_error"),
        start_image_number=_integer(row[5], row=index, column="start_img"),
        stop_image_number=_integer(row[6], row=index, column="stop_img"),
        temperature_deviation_k=_number(row[7], row=index, column="temp_dev_k"),
        pressure_deviation_kpa=_number(row[8], row=index, column="press_dev_kpa"),
        raw_tokens=row,
    ) for index, row in enumerate(rate_rows, start=2))

    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        return CryoNeutronPhaseChangeRun(
            SOURCE_DOI, SOURCE_DATASET_ID, SOURCE_VERSION, SOURCE_LICENSE,
            SOURCE_ARCHIVE_SHA256,
            ((DAQ_MEMBER, "ABF820A8"), (IMAGE_MEMBER, "E2FB6E85"), (RATE_MEMBER, "09054FD9")),
            daq_path, image_path, rate_path,
            hashlib.sha256(daq_bytes).hexdigest(), hashlib.sha256(image_bytes).hexdigest(),
            hashlib.sha256(rate_bytes).hexdigest(), daq, images, rates, token,
        )
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
