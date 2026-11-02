"""Bounded ELVHYS LH2 membrane-rupture observations, not premixed CJ data.

Torres de Ritter, Friedrich and Ferraro Porcel de Peralta, DOI:10.18710/M5LOLM,
version 1.0, CC0-1.0. Source exports and supporting text remain external files.
"""

import csv
import json
import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import numpy as np

from ..core import Origin, TimeSeries, immutable_array
from ..observations import ObservationTable, Variable
from ..units import convert_to_si
from .pressure_peaking import file_sha256

PROFILE_ID = "elvhys-lh2-shock-tube-v1-profile-1"
DOI = "10.18710/M5LOLM"
README_NAME = "00_README_ELVHYS_WP_4_3_1.txt"
META_NAME = "ELE431KITMETA.csv"
SUPPORT_ENCODINGS = {README_NAME: "utf-8", META_NAME: "latin-1"}
FILE_PATTERN = re.compile(
    r"ELE431KIT(?P<code>[01][1-4][1-9])(?P<recorder>TEMPL?|PRESS|PRESF|MICR)(?P<date>\d{8})\.csv"
)
HEADERS = {
    "TEMP": (
        "Time (minutes)",
        *(f"T_2{x} (K)" for x in "abcde"),
        "Jet temperature 1 (K)",
        "Jet temperature 2 (K)",
    ),
    "PRESS": (
        "Time (minutes)",
        "p_20 (bar_a)",
        "p_1 (bar_g)",
        "p_3 (bar_g)",
        "Dp_01 (bar)",
        "V_220 (mbar_g)",
        "p_V07 (mbar_g)",
        "p_GFK (mbar_g)",
    ),
    "PRESF": (
        "Time (seconds)",
        *(f"PC{101 + i} - p_2{x} (bar_a)" for i, x in enumerate("abcdef")),
        *(f"PW{i} (bar_a)" for i in range(111, 116)),
    ),
    "MICR": ("Time (seconds)", "SLM - Sound level (dB)"),
}
_PENDING_BLOCK_ISSUERS: set[object] = set()
_PENDING_RUN_ISSUERS: set[object] = set()
_PENDING_STUDY_RECORDER_ISSUERS: set[object] = set()


def _issue_shock_tube_block(*args, **values):
    token = object()
    _PENDING_BLOCK_ISSUERS.add(token)
    try:
        return ShockTubeBlock(*args, **values, _issuer_token=token)
    except Exception:
        _PENDING_BLOCK_ISSUERS.discard(token)
        raise


def _issue_shock_tube_run(*args, **values):
    token = object()
    _PENDING_RUN_ISSUERS.add(token)
    try:
        return ShockTubeRun(*args, **values, _issuer_token=token)
    except Exception:
        _PENDING_RUN_ISSUERS.discard(token)
        raise


def _study_recorder_token():
    token = object()
    _PENDING_STUDY_RECORDER_ISSUERS.add(token)
    return token


def _issue_study_recorder(**values):
    token = _study_recorder_token()
    try:
        return ShockTubeRecorder(**values, _study_issuer_token=token)
    except Exception:
        _PENDING_STUDY_RECORDER_ISSUERS.discard(token)
        raise


def _integer(value, name, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be a positive integer within its declared budget")
    return value


def _number(text):
    if not text.strip():
        return math.nan, "missing"
    if text.lstrip().startswith("="):
        return math.nan, "formula_not_evaluated"
    try:
        value = float(text)
    except ValueError:
        return math.nan, "nonnumeric"
    return (value, "") if math.isfinite(value) else (value, "nonfinite")


@dataclass(frozen=True, slots=True)
class ShockTubePosition:
    """Source coordinates, including the source's unresolved radial convention."""

    sensor_id: str
    reported_r_m: float
    reported_z_m: float
    reported_phi_deg: float
    source_line: int
    source_sha256: str
    reference: str = (
        "README cylindrical coordinates from tube bottom flange; radial value not repaired"
    )


@dataclass(frozen=True, slots=True)
class ShockTubeChannel:
    source_header: str
    source_unit: str
    variable: Variable
    role: str
    position: ShockTubePosition | None = None
    issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ShockTubeRun:
    run_id: str
    code: str
    date: str
    ignition_condition: str
    membrane_description: str
    burst_pressure_pa_reported: float
    containment_oxygen_fraction_reported: float
    containment_temperature_k_reported: float
    metadata_source_line: int
    metadata_sha256: str
    membrane_batch_marker: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_RUN_ISSUERS:
            raise ValueError("Campaign runs must be parsed from a qualified study collection")
        _PENDING_RUN_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)

    @property
    def conditions(self):
        """Reported campaign summaries; they do not define a premixed tube state."""
        variables = (
            Variable(
                "burst_pressure",
                "reported_pressure",
                "Pa",
                "META reported rupture bar_a; summary extraction/estimator unresolved",
            ),
            Variable(
                "containment_oxygen",
                "reported_oxygen_fraction",
                "1",
                "META initial V220 O2%; mole/volume/wet-dry convention unresolved",
            ),
            Variable(
                "containment_temperature",
                "temperature",
                "K",
                "META initial V220 temperature; not initial tube hydrogen temperature",
            ),
        )
        values = np.array(
            [
                [
                    self.burst_pressure_pa_reported,
                    self.containment_oxygen_fraction_reported,
                    self.containment_temperature_k_reported,
                ]
            ]
        )
        return ObservationTable(
            values,
            variables,
            np.isfinite(values),
            (
                f"{DOI}|{META_NAME}|{self.metadata_sha256}|line-{self.metadata_source_line}|{self.run_id}",
            ),
            (self.run_id,),
            (Origin.RECONSTRUCTED,) * 3,
            DOI,
            (
                ("profile", PROFILE_ID),
                ("role", "source-reported campaign summaries, not independent raw measurements"),
                ("membrane_description", self.membrane_description),
                ("batch_marker", self.membrane_batch_marker),
                ("ignition_condition", self.ignition_condition),
            ),
        )


def _channel(header, kind, positions):
    label, unit = header.rsplit(" (", 1)
    unit = unit[:-1]
    sensor = label.split(" - ")[-1]
    if label.startswith("Jet temperature "):
        sensor = "T_jet_" + label[-1]
    if kind == "TEMP":
        role = "point silicon-diode temperature; not a spatially averaged tube or initial premixed-gas temperature"
        variable = Variable(sensor, "temperature", "K", role)
        return ShockTubeChannel(header, unit, variable, role, positions.get(sensor))
    if kind == "MICR":
        role = "reported sound-level meter output; weighting, reference pressure and detector averaging unresolved"
        return ShockTubeChannel(
            header, unit, Variable("sound_level", "reported_sound_level", "dB", role), role
        )
    issues = []
    if kind == "PRESF":
        basis = "CSV labels bar_a; dynamic signed output; baseline/absolute calibration and processing unresolved"
        role = (
            "tube station"
            if label.startswith("PC")
            else "V220 pressure-wave station; exact position requires unavailable D4.8 drawing"
        )
        issues.append("signed_dynamic_output_is_not_qualified_thermodynamic_absolute_pressure")
    else:
        basis = "CSV reported " + unit + "; no gauge-to-absolute offset supplied"
        role = {
            "p_20": "static tube-connected pressure",
            "p_1": "LH2-feed pressure",
            "p_3": "counterpressure-line pressure",
            "Dp_01": "tube differential pressure; sign/elevation convention unresolved",
            "V_220": "containment pressure",
            "p_V07": "vacuum-vessel pressure",
            "p_GFK": "insulating-flange pressure",
        }[label]
        if label == "p_1":
            issues.append("CSV_gauge_and_README_variable_list_absolute_conflict")
        if label == "p_3":
            issues.append("CSV_gauge_and_instrument_absolute_range_conflict")
        if label == "Dp_01":
            issues.append("CSV_bar_and_instrument_mbar_range_require_calibration_review")
    quantity = "pressure_difference" if sensor == "Dp_01" else "reported_pressure"
    return ShockTubeChannel(
        header,
        unit,
        Variable(sensor, quantity, "Pa", basis + "; " + role),
        role,
        positions.get(sensor),
        tuple(issues),
    )


@dataclass(frozen=True, slots=True)
class ShockTubeBlock:
    recorder: "ShockTubeRecorder"
    source_lines: np.ndarray
    raw_lines: tuple[str, ...]
    raw_cells: tuple[tuple[str, ...], ...]
    raw_values: np.ndarray
    values: np.ndarray
    valid: np.ndarray
    reasons: tuple[tuple[str, ...], ...]
    predecessor_time_s: float | None
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_BLOCK_ISSUERS:
            raise ValueError("Shock-tube blocks must be parsed from their qualified recorder")
        _PENDING_BLOCK_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        for name, dtype in (
            ("source_lines", np.int64),
            ("raw_values", float),
            ("values", float),
            ("valid", bool),
        ):
            value = immutable_array(getattr(self, name), dtype=dtype, name=name)
            object.__setattr__(self, name, value)
        if (
            self.values.shape != (len(self.source_lines), len(self.recorder.header))
            or self.valid.shape != self.values.shape
        ):
            raise ValueError("Source rows and observation columns differ")

    @property
    def observations(self):
        r = self.recorder
        return ObservationTable(
            self.values,
            r.variables,
            self.valid,
            tuple(f"{r.source_id}|{r.source_sha256}|line-{i}" for i in self.source_lines),
            (r.run_id,) * len(self.values),
            (Origin.RECONSTRUCTED,) + (Origin.MEASURED,) * len(r.channels),
            r.source_id,
            (
                ("profile", PROFILE_ID),
                ("source_file_sha256", r.source_sha256),
                ("clock_id", r.clock_id),
                ("clock_epoch", "source-reported signed clock; zero event/offset not defined"),
                ("study_id", r.study_id),
                ("recorder_kind", r.kind),
                (
                    "processing",
                    "publisher-converted export; no baseline, clipping, smoothing or synchronization",
                ),
            ),
        )

    @property
    def series(self):
        """No row removal, sorting or clock repair is allowed when making a series."""
        if not np.all(self.valid[:, 0]):
            raise ValueError("A TimeSeries needs every reported clock value to be valid")
        if (
            len(self.values)
            and self.predecessor_time_s is not None
            and (
                not math.isfinite(self.predecessor_time_s)
                or self.values[0, 0] <= self.predecessor_time_s
            )
        ):
            raise ValueError("Reported clock is not increasing across the source-block boundary")
        r = self.recorder
        return TimeSeries(
            self.values[:, 0],
            self.values[:, 1:],
            tuple(c.variable.name for c in r.channels),
            tuple(c.variable.unit for c in r.channels),
            self.valid[:, 1:],
            r.clock_id,
            Origin.MEASURED,
            r.source_id,
            tuple(c.variable.quantity for c in r.channels),
            tuple(c.variable.basis_id for c in r.channels),
        )


class ShockTubeRecorder:
    """One original recorder file; O(block_rows * columns) working memory."""

    def __init__(self, path, *, expected_sha256=None, positions=None, maximum_bytes=50_000_000,
                 _study_issuer_token=None):
        study_verified = _study_issuer_token in _PENDING_STUDY_RECORDER_ISSUERS
        if study_verified:
            _PENDING_STUDY_RECORDER_ISSUERS.remove(_study_issuer_token)
        self.path = Path(path)
        match = FILE_PATTERN.fullmatch(self.path.name)
        if match is None:
            raise ValueError("A date-qualified, reviewed ELVHYS recorder filename is required")
        _integer(maximum_bytes, "maximum_bytes", 600_000_000)
        if self.path.stat().st_size > maximum_bytes:
            raise ValueError("Recorder exceeds its byte budget")
        self.source_sha256 = file_sha256(self.path)
        if expected_sha256 is not None and expected_sha256 != self.source_sha256:
            raise ValueError("Recorder SHA-256 differs from receipt")
        self.code, self.date = match["code"], match["date"]
        self.kind = "TEMP" if match["recorder"] == "TEMPL" else match["recorder"]
        self.study_id = DOI if study_verified else "caller-supplied-local-file"
        self.run_id = (f"ELE431KIT{self.code}:{self.date}" if study_verified
                       else f"local-file:{self.path.name}")
        self.source_id = (f"{DOI}|v1.0|{self.path.name}" if study_verified
                          else f"local-file|{self.path.name}")
        self.clock_id = self.source_id + "|reported-clock-epoch-unresolved"
        self.delimiter = "," if self.kind == "MICR" else ";"
        with self.path.open(encoding="utf-8-sig", newline="") as stream:
            self.raw_header = stream.readline(8193)
        if len(self.raw_header) > 8192:
            raise ValueError("Recorder header exceeds its line budget")
        self.header = tuple(next(csv.reader([self.raw_header], delimiter=self.delimiter)))
        if self.header != HEADERS[self.kind]:
            raise ValueError("Unreviewed recorder schema or unit header")
        self.channels = tuple(_channel(h, self.kind, positions or {}) for h in self.header[1:])
        self.variables = (
            Variable("reported_time", "time", "s", self.clock_id),
            *(c.variable for c in self.channels),
        )

    def _block(self, lines, cells, numbers, predecessor):
        raw = np.empty((len(cells), len(self.header)))
        reasons = []
        for i, row in enumerate(cells):
            parsed = [_number(value) for value in row]
            raw[i] = [p[0] for p in parsed]
            reasons.append([p[1] for p in parsed])
        values = raw.copy()
        values[:, 0] = convert_to_si(
            raw[:, 0], quantity="time", unit="min" if self.kind in {"TEMP", "PRESS"} else "s"
        )
        for j, channel in enumerate(self.channels, 1):
            if self.kind == "TEMP":
                for i in np.flatnonzero(
                    np.isfinite(raw[:, j]) & ((raw[:, j] < 2.0) | (raw[:, j] > 500.0))
                ):
                    reasons[i][j] = "outside_reported_diode_range_2_to_500_K"
            elif self.kind != "MICR":
                unit = channel.source_unit
                scale = 0.001 if unit.startswith("mbar") else 1.0
                quantity = channel.variable.quantity
                values[:, j] = convert_to_si(
                    raw[:, j] * scale,
                    quantity=quantity,
                    unit="bar",
                    pressure_basis="differential" if quantity == "pressure_difference" else None,
                )
        valid = np.array([[not reason for reason in row] for row in reasons], dtype=bool)
        return _issue_shock_tube_block(
            self,
            np.array(numbers),
            tuple(lines),
            tuple(cells),
            raw,
            values,
            valid,
            tuple(tuple(row) for row in reasons),
            predecessor,
        )

    def iter_blocks(
        self,
        *,
        block_rows=4096,
        source_line_start=2,
        source_line_stop=None,
        maximum_rows=1_000_000,
        maximum_line_characters=8192,
    ):
        _integer(block_rows, "block_rows", 65_536)
        _integer(maximum_rows, "maximum_rows", 10_000_000)
        _integer(maximum_line_characters, "maximum_line_characters", 65_536)
        _integer(source_line_start, "source_line_start", maximum_rows + 1)
        if source_line_start < 2 or (
            source_line_stop is not None
            and (
                isinstance(source_line_stop, bool)
                or not isinstance(source_line_stop, int)
                or source_line_stop <= source_line_start
                or source_line_stop > maximum_rows + 2
            )
        ):
            raise ValueError("Select ordered physical source lines, starting at line 2")
        if file_sha256(self.path) != self.source_sha256:
            raise ValueError("Recorder changed since source admission")
        previous, predecessor = None, None
        lines, cells, numbers = [], [], []
        with self.path.open(encoding="utf-8-sig", newline="") as stream:
            if stream.readline(maximum_line_characters + 1) != self.raw_header:
                raise ValueError("Source header changed since admission")
            for line_number in range(2, maximum_rows + 3):
                if source_line_stop is not None and line_number >= source_line_stop:
                    break
                line = stream.readline(maximum_line_characters + 1)
                if not line:
                    break
                if line_number > maximum_rows + 1 or len(line) > maximum_line_characters:
                    raise ValueError(
                        f"Source line/row budget exceeded at physical line {line_number}"
                    )
                row = tuple(next(csv.reader([line], delimiter=self.delimiter, strict=True)))
                if len(row) != len(self.header):
                    raise ValueError(f"Source column count differs at physical line {line_number}")
                time, _ = _number(row[0])
                time *= 60.0 if self.kind in {"TEMP", "PRESS"} else 1.0
                if line_number >= source_line_start:
                    if not cells:
                        predecessor = previous
                    lines.append(line)
                    cells.append(row)
                    numbers.append(line_number)
                    if len(cells) == block_rows:
                        yield self._block(lines, cells, numbers, predecessor)
                        lines, cells, numbers = [], [], []
                previous = time
            if cells:
                yield self._block(lines, cells, numbers, predecessor)
        if file_sha256(self.path) != self.source_sha256:
            raise ValueError("Recorder changed during source reading")


class ShockTubeCollection:
    """Pinned local receipt plus actual metadata, conditions, stations and recorders."""

    def __init__(self, receipt_path, raw_root, *, maximum_total_bytes=600_000_000):
        self.receipt_path, self.raw_root = Path(receipt_path), Path(raw_root).resolve()
        if self.receipt_path.stat().st_size > 200_000:
            raise ValueError("Receipt exceeds metadata budget")
        self.receipt_sha256 = file_sha256(self.receipt_path)
        self.receipt = tomllib.loads(self.receipt_path.read_text(encoding="utf-8"))
        record = self.receipt
        if (
            record.get("key") != "elvhys-shock-tube"
            or record.get("doi") != DOI
            or record.get("version") != "1.0"
            or record.get("license_id") != "CC0-1.0"
            or record.get("rights_permitted") is not True
        ):
            raise ValueError("Pinned dataset identity/version or explicit rights differ")
        _integer(maximum_total_bytes, "maximum_total_bytes", 1_000_000_000)
        self.files, names = [], set()
        for entry in record["files"]:
            if entry["status"] not in {"acquired", "cached"}:
                continue
            relative = PurePosixPath(entry["relative_path"])
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or "\\" in entry["relative_path"]
                or ":" in entry["relative_path"]
                or relative.name != entry["name"]
                or entry["name"].casefold() in names
                or not re.fullmatch("[0-9a-f]{64}", entry["sha256"])
            ):
                raise ValueError("Unsafe, duplicate or unfingerprinted source identity")
            path = (self.raw_root / Path(*relative.parts)).resolve()
            if not path.is_relative_to(self.raw_root) or path.stat().st_size != entry["size_bytes"]:
                raise ValueError("Source path/size differs from receipt")
            names.add(entry["name"].casefold())
            self.files.append((entry, path))
        if sum(e["size_bytes"] for e, _ in self.files) > maximum_total_bytes:
            raise ValueError("Acquired source collection exceeds total byte budget")
        self.files = tuple(self.files)
        by_name = {e["name"]: (e, p) for e, p in self.files}
        if README_NAME not in by_name or META_NAME not in by_name:
            raise ValueError("Actual pinned README and campaign metadata are required")
        support = {}
        for name in (README_NAME, META_NAME):
            e, path = by_name[name]
            if e["size_bytes"] > 100_000 or file_sha256(path) != e["sha256"]:
                raise ValueError("Supporting source size/hash differs")
            # META contains non-UTF8 degree/micro bytes. Latin-1 is a reversible
            # byte mapping, not a claim of a publisher-declared character set.
            support[name] = path.read_text(encoding=SUPPORT_ENCODINGS[name])
        metadata_path = self.raw_root / "elvhys-shock-tube/1.0/repository-metadata.json"
        if (
            metadata_path.stat().st_size > 2_000_000
            or file_sha256(metadata_path) != record["metadata_sha256"]
        ):
            raise ValueError("Repository metadata size/hash differs from receipt")
        native = json.loads(metadata_path.read_text(encoding="utf-8"))["data"]["latestVersion"]
        if (native.get("versionNumber"), native.get("versionMinorNumber")) != (1, 0) or native.get(
            "license", {}
        ).get("rightsIdentifier") != "CC0-1.0":
            raise ValueError("Native repository version/license does not confirm receipt")
        self.metadata_sha256 = record["metadata_sha256"]
        self.support_encodings = dict(SUPPORT_ENCODINGS)
        self.observation_notes = tuple(
            (e["name"], p.read_text(encoding="utf-8"))
            for e, p in self.files
            if e["name"].startswith("Observation") and e["size_bytes"] < 10_000
        )
        geometry = re.search(
            r"L\s*=\s*([\d.]+)\s*mm\s+and\s+ID\s*\(internal diameter\)\s*=\s*([\d.]+)\s*mm",
            support[README_NAME],
        )
        self.reported_tube_geometry_m = (
            None if geometry is None else tuple(float(v) * 0.001 for v in geometry.groups())
        )
        self.positions = {}
        for number, line in enumerate(support[README_NAME].splitlines(), 1):
            match = re.match(
                r"^(p_2[a-f]|T_2[a-e])\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+",
                line,
            )
            if match:
                sensor, r, z, phi = match.groups()
                if sensor in self.positions:
                    raise ValueError("Duplicate station coordinate definition")
                self.positions[sensor] = ShockTubePosition(
                    sensor,
                    float(r) * 0.001,
                    float(z) * 0.001,
                    float(phi),
                    number,
                    by_name[README_NAME][0]["sha256"],
                )
        self.runs = {}
        pattern = re.compile(
            r"^ELE431KIT([01][1-4][1-9])DATA(\d{8})\s+\[([^,]+),\s*([\d.]+) bar_a,\s*([\d.]+)%,\s*([\d.]+)[^\]]*\](\*+)"
        )
        for number, line in enumerate(support[META_NAME].splitlines(), 1):
            match = pattern.match(line)
            if not match:
                continue
            code, date, membrane, burst, oxygen, temp, marker = match.groups()
            identity = f"ELE431KIT{code}:{date}"
            if identity in self.runs:
                raise ValueError("Duplicate date-qualified campaign identity")
            self.runs[identity] = _issue_shock_tube_run(
                identity,
                code,
                date,
                "unignited/inert-labelled" if code[0] == "0" else "ignited/oxidizing-labelled",
                membrane,
                float(burst) * 1e5,
                float(oxygen) * 0.01,
                float(temp) + 273.15,
                number,
                by_name[META_NAME][0]["sha256"],
                marker,
            )
        if not self.runs or not self.positions:
            raise ValueError("Source campaign/station schema could not be qualified")
        self.recorders = tuple(
            _issue_study_recorder(path=path, expected_sha256=e["sha256"], positions=self.positions)
            for e, path in self.files
            if FILE_PATTERN.fullmatch(e["name"])
        )
        if any(r.run_id not in self.runs for r in self.recorders):
            raise ValueError("Recorder lacks its date-qualified metadata run")
        allowed_support = {
            README_NAME,
            META_NAME,
            "ObservationELE431KIT011.txt",
            "ObservationELE431KIT041.txt",
        }
        if any(
            e["name"] not in allowed_support and not FILE_PATTERN.fullmatch(e["name"])
            for e, _ in self.files
        ):
            raise ValueError("Acquired attachment lacks a reviewed role")

    def verify_sources(self):
        """All acquired files and pinned metadata; no download or source writes."""
        checked = {}
        for entry, path in self.files:
            digest = file_sha256(path)
            if digest != entry["sha256"] or path.stat().st_size != entry["size_bytes"]:
                raise ValueError("Acquired source bytes changed: " + entry["name"])
            checked[entry["name"]] = digest
        metadata = self.raw_root / "elvhys-shock-tube/1.0/repository-metadata.json"
        if (
            file_sha256(metadata) != self.metadata_sha256
            or file_sha256(self.receipt_path) != self.receipt_sha256
        ):
            raise ValueError("Pinned receipt/repository metadata changed")
        return checked
