"""ELVHYS4.2 cryogenic-room observations, without fabricated oxygen histories.

Rattigan, Welch and Vizma, DOI10.18710/JXJP0H, version1.1, CC0-1.0.
The source measures processed H2 concentrations, temperatures and boundary
indications. It does not measure room-average O2 depletion or H2 mass flow.
"""

import csv
import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import numpy as np

from ..core import Origin, immutable_array
from ..observations import ObservationTable, Variable
from ..units import convert_to_si
from .pressure_peaking import _positive_integer, file_sha256
from .shock_tube import ShockTubeRecorder, _number

PROFILE_ID = "elvhys-cryogenic-room-v1.1-profile-1"
DOI = "10.18710/JXJP0H"
CLOCK_UNIT = "source_time_unit_unresolved"
README_NAME = "00_ELVHYSWP4_2 README.txt"
META_NAME = "ELE402HSEMETA.csv"
SENSOR_NAME = "ELVHYS WP4.2 TCS Sensor Details.pdf"
FRAME_ID = "ELVHYS4.2-bottom-right-front-looking-from-LH2-inlet;X-streamwise-Y-lateral-Z-vertical"
FILE_PATTERN = re.compile(
    r"ELE402HSE(?P<case>\d{3,4})(?P<kind>CONC|FLMT|MISC|PRES|TEMP)(?P<date>\d{7,8})\.csv"
)
_PENDING_ROOM_BLOCK_ISSUERS: set[object] = set()


def _issue_room_block(*args):
    token = object()
    _PENDING_ROOM_BLOCK_ISSUERS.add(token)
    try:
        return CryogenicRoomBlock(*args, _issuer_token=token)
    except Exception:
        _PENDING_ROOM_BLOCK_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class CryogenicRoomCase:
    number: int
    source_line: int
    source_fields: tuple[str, ...]
    nominal_tanker_gauge_pressure_pa: float
    nominal_nozzle_diameter_m: float
    description: str
    source_declared_invalid: bool
    source_sha256: str

    @property
    def experiment_id(self):
        return f"{DOI}|reported-test-{self.number}"


@dataclass(frozen=True, slots=True)
class CryogenicRoomPosition:
    source_label: str
    position_m: tuple[float, float, float]
    sensor_roles: str
    source_line: int
    source_sha256: str
    frame_id: str = FRAME_ID


@dataclass(frozen=True, slots=True)
class CryogenicRoomChannel:
    source_header: str
    source_unit: str
    variable: Variable
    origin: Origin
    role: str
    reported_clock_column: str | None
    position: CryogenicRoomPosition | None = None
    candidate_position: CryogenicRoomPosition | None = None
    issues: tuple[str, ...] = ()


def _channel(name, kind, headers, positions):
    blast_clocks = tuple(h for h in headers if h in {"BlastTime", "Blast Time"})
    clock = (
        (blast_clocks[0] if len(blast_clocks) == 1 else None) if name.endswith("BPT") else "Time"
    )
    basis = f"ELVHYS4.2 original {kind}/{name}"
    if name in {"Time", "BlastTime", "Blast Time"}:
        role = "publisher-reported clock coordinate; physical unit/epoch and cross-recorder alignment unresolved"
        return CryogenicRoomChannel(
            name,
            CLOCK_UNIT,
            Variable(name, "reported_time_coordinate", CLOCK_UNIT, basis + "; " + role),
            Origin.RECONSTRUCTED if kind == "CONC" else Origin.MEASURED,
            role,
            name,
        )
    if name.startswith("H2"):
        label = name[2:]
        label = {"Bottom1": "Bottom1_Front", "Side1": "Side1_Top"}.get(label, label)
        if label not in positions:
            return _unknown(name, basis, clock)
        role = "point sampled-gas H2 vol%; publisher-normalized and delay-aligned; 20m sampling line; not O2 or room average"
        position = positions[label]
        if "C" not in position.sensor_roles:
            role += "; header matches a T-only station label; concentration location unresolved"
            return CryogenicRoomChannel(
                name,
                "vol%H2",
                Variable(name, "volume_fraction", "1", basis + "; " + role),
                Origin.RECONSTRUCTED,
                role,
                clock,
                None,
                position,
                ("concentration_header_conflicts_with_T_only_station_role",),
            )
        return CryogenicRoomChannel(
            name,
            "vol%H2",
            Variable(name, "volume_fraction", "1", basis + "; " + role),
            Origin.RECONSTRUCTED,
            role,
            clock,
            positions[label],
        )
    if name.endswith("Temp"):
        label = name if name in positions else name[:-4].rstrip("_")
        if name != "NozzleTemp" and label not in positions:
            return _unknown(name, basis, clock)
        role = (
            (
                "nozzle point thermocouple, publisher voltage-to-temperature calibration; not bulk stagnation/phase state"
                if name == "NozzleTemp"
                else "point thermocouple; peened wall and sampled-flow roles remain distinct"
            )
            + "; published instrument/range/error descriptions disagree; no calibration accuracy gate imposed"
        )
        return CryogenicRoomChannel(
            name,
            "K",
            Variable(name, "temperature", "K", basis + "; " + role),
            Origin.MEASURED,
            role,
            clock,
            positions.get(label),
        )
    if name in {
        "PT1ReleaseRig",
        "PT2Nozzle",
        "PTBox1_TopLeft",
        "PTBox2_BottomRight",
        "TopLeftBPT",
        "BottomRightBPT",
    }:
        unit = "mbarg" if name.startswith("PTBox") else "barg"
        role = (
            "release rig/nozzle gauge pressure; not upstream vessel inventory"
            if name in {"PT1ReleaseRig", "PT2Nozzle"}
            else "local box gauge/blast pressure; not absolute thermodynamic pressure"
        )
        return CryogenicRoomChannel(
            name,
            unit,
            Variable(name, "gauge_pressure", "Pa", basis + "; " + role),
            Origin.MEASURED,
            role,
            clock,
            positions.get(name),
        )
    if name == "FanFlowMeter":
        role = "ventilation fan air volume flow; actual/reference P/T unresolved; not hydrogen release mass flow"
        return CryogenicRoomChannel(
            name,
            "L/min",
            Variable(name, "volume_flow", "m3/s", basis + "; " + role),
            Origin.MEASURED,
            role,
            clock,
        )
    weather = {
        "AmbientTemperature": ("degC", "temperature", "K"),
        "Humidity": ("%RH", "relative_humidity", "1"),
        "Pressure": ("mbara", "pressure", "Pa"),
        "WindDirection": ("deg", "wind_direction", "rad"),
        "WindSpeed": ("m/s", "wind_speed", "m/s"),
    }
    if name in weather:
        unit, quantity, si = weather[name]
        role = "ambient weather station; publisher labels indication only"
        return CryogenicRoomChannel(
            name,
            unit,
            Variable(name, quantity, si, basis + "; " + role),
            Origin.MEASURED,
            role,
            clock,
        )
    return _unknown(name, basis, clock)


def _unknown(name, basis, clock):
    return CryogenicRoomChannel(
        name,
        "source_unit_unresolved",
        Variable(
            name, "reported_unknown", "source_unit_unresolved", basis + "; role/unit unresolved"
        ),
        Origin.UNRESOLVED,
        "unreviewed field including DPT/Var placeholders; no pressure or control meaning inferred",
        clock,
    )


@dataclass(frozen=True, slots=True)
class CryogenicRoomBlock:
    recorder: "CryogenicRoomRecorder"
    source_lines: np.ndarray
    raw_lines: tuple[str, ...]
    raw_cells: tuple[tuple[str, ...], ...]
    raw_values: np.ndarray
    numeric_valid: np.ndarray
    values: np.ndarray
    valid: np.ndarray
    reasons: tuple[tuple[str, ...], ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ROOM_BLOCK_ISSUERS:
            raise ValueError("Use the checked cryogenic-room recorder to issue source blocks")
        _PENDING_ROOM_BLOCK_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        for name, dtype in (
            ("source_lines", np.int64),
            ("raw_values", float),
            ("numeric_valid", bool),
            ("values", float),
            ("valid", bool),
        ):
            value = immutable_array(getattr(self, name), dtype=dtype, name=name)
            object.__setattr__(self, name, value)
        shape = (len(self.source_lines), len(self.recorder.header))
        if (
            self.raw_values.shape != shape
            or self.numeric_valid.shape != shape
            or self.values.shape != (shape[0], shape[1] + 1)
            or self.valid.shape != self.values.shape
        ):
            raise ValueError("Actual source lines, clocks, channels and masks must align")

    @property
    def observations(self):
        r = self.recorder
        return ObservationTable(
            self.values,
            r.variables,
            self.valid,
            tuple(f"{r.source_id}|{r.source_sha256}|line-{n}" for n in self.source_lines),
            (r.case.experiment_id,) * len(self.values),
            (Origin.RECONSTRUCTED,) + tuple(c.origin for c in r.channels),
            r.source_id,
            (
                ("profile", PROFILE_ID),
                ("source_sha256", r.source_sha256),
                ("source_directory", r.directory_label),
                ("source_date_token", r.date_token),
                ("source_case_row", str(r.case.source_line)),
                ("source_declared_invalid_case", str(r.case.source_declared_invalid)),
                ("clock_units", CLOCK_UNIT),
                (
                    "cross_recorder_clock_mapping",
                    "unresolved; equal rows or values do not establish physical synchronization",
                ),
                (
                    "hydrogen_processing",
                    "source-normalized and source-delay-aligned; original raw sensor/delay not available",
                ),
                ("oxygen", "not measured; no O2 history reconstructed"),
                ("study_id", DOI),
            ),
        )

    def as_time_series(self):
        raise ValueError(
            "Source Time/BlastTime physical unit, epoch and mapping remain unresolved; explicit independent evidence is required"
        )


class CryogenicRoomRecorder(ShockTubeRecorder):
    """Reuse existing bounded CSV iteration/hash checks; retain this source's schema.

    The inherited reader delegates block construction and does not select a
    physical clock unit for this distinct source kind. No second CSV reader is
    introduced. Time and BlastTime are independent reported columns by default.
    """

    def __init__(
        self, path, *, case, positions, expected_sha256, directory_label, maximum_bytes=150_000_000
    ):
        _positive_integer(maximum_bytes, "maximum_bytes")
        self.path = Path(path)
        match = FILE_PATTERN.fullmatch(self.path.name)
        if match is None or int(match["case"]) != case.number:
            raise ValueError("Actual source filename and nominal test identity differ")
        if self.path.stat().st_size > maximum_bytes:
            raise ValueError("Recorder exceeds the declared byte budget")
        self.source_sha256 = file_sha256(self.path)
        if expected_sha256 != self.source_sha256:
            raise ValueError("Recorder SHA256 differs from receipt")
        self.case, self.directory_label = case, directory_label
        self.recorder_kind, self.date_token = match["kind"], match["date"]
        self.kind = "ELVHYS4.2-reported-coordinate"  # Not the other source's minute/second schema.
        self.delimiter = ","
        self.source_id = f"{DOI}|v1.1|{directory_label}|{self.path.name}"
        with self.path.open(encoding="utf-8-sig", newline="") as stream:
            self.raw_header = stream.readline(16385)
        if len(self.raw_header) > 16384:
            raise ValueError("Source header exceeds its line budget")
        self.header = tuple(next(csv.reader([self.raw_header], strict=True)))
        if (
            not self.header
            or self.header[0] != "Time"
            or len(self.header) > 64
            or len(set(self.header)) != len(self.header)
            or any(not h for h in self.header)
        ):
            raise ValueError("Unreviewed source header/duplicate-column schema")
        self.channels = tuple(
            _channel(h, self.recorder_kind, self.header, positions) for h in self.header
        )
        self.variables = (
            Variable(
                "source_index",
                "source_index",
                "1",
                "one-based data row; physical source line minus one",
            ),
            *(c.variable for c in self.channels),
        )

    def _block(self, lines, cells, numbers, predecessor):
        raw = np.empty((len(cells), len(self.header)))
        reasons = []
        for i, row in enumerate(cells):
            parsed = [_number(v) for v in row]
            raw[i] = [p[0] for p in parsed]
            reasons.append([p[1] for p in parsed])
        numeric = np.isfinite(raw)
        si = raw.copy()
        for j, c in enumerate(self.channels):
            quantity, unit = c.variable.quantity, c.source_unit
            if quantity == "volume_fraction":
                si[:, j] = convert_to_si(raw[:, j], quantity=quantity, unit="%")
                for i in np.flatnonzero(numeric[:, j] & ((raw[:, j] < 0) | (raw[:, j] > 100))):
                    reasons[i][j] = "outside_source_reported_H2_range_0_to_100_volpct"
            elif quantity == "temperature":
                si[:, j] = convert_to_si(raw[:, j], quantity=quantity, unit=unit)
                for i in np.flatnonzero(numeric[:, j] & (si[:, j] <= 0)):
                    reasons[i][j] = "nonphysical_absolute_temperature"
            elif quantity == "gauge_pressure":
                si[:, j] = convert_to_si(
                    raw[:, j] * (0.001 if unit == "mbarg" else 1.0),
                    quantity="reported_pressure",
                    unit="bar",
                )
            elif quantity == "pressure":
                si[:, j] = convert_to_si(
                    raw[:, j] * 0.001, quantity="pressure", unit="bar", pressure_basis="absolute"
                )
                for i in np.flatnonzero(numeric[:, j] & (si[:, j] <= 0)):
                    reasons[i][j] = "nonphysical_absolute_pressure"
            elif quantity == "relative_humidity":
                si[:, j] = convert_to_si(raw[:, j], quantity=quantity, unit="%")
            elif quantity == "volume_flow":
                si[:, j] = raw[:, j] * (0.001 / 60.0)
            elif quantity == "wind_direction":
                si[:, j] = np.deg2rad(raw[:, j])
            for i in np.flatnonzero(numeric[:, j] & ~np.isfinite(si[:, j])):
                reasons[i][j] = "nonfinite_after_unit_conversion"
            if self.case.source_declared_invalid and quantity != "reported_time_coordinate":
                for row in reasons:
                    row[j] = (
                        row[j] + ";source_declared_invalid_case"
                        if row[j]
                        else "source_declared_invalid_case"
                    )
        valid = np.array([[not r for r in row] for row in reasons], dtype=bool)
        return _issue_room_block(
            self,
            np.asarray(numbers),
            tuple(lines),
            tuple(cells),
            raw,
            numeric,
            np.column_stack((np.asarray(numbers) - 1, si)),
            np.column_stack((np.ones(len(cells), dtype=bool), valid)),
            tuple(tuple(r) for r in reasons),
        )


class CryogenicRoomCollection:
    """Exact acquired receipt, native version/rights and runtime source descriptions."""

    def __init__(self, receipt_path, raw_root, *, maximum_total_bytes=1_500_000_000):
        _positive_integer(maximum_total_bytes, "maximum_total_bytes")
        self.receipt_path, self.raw_root = Path(receipt_path), Path(raw_root).resolve()
        if self.receipt_path.stat().st_size > 500_000:
            raise ValueError("Receipt exceeds its byte budget")
        self.receipt_sha256 = file_sha256(self.receipt_path)
        r = self.receipt = tomllib.loads(self.receipt_path.read_text(encoding="utf-8"))
        if (
            r.get("key") != "elvhys-cold-room"
            or r.get("doi") != DOI
            or r.get("version") != "1.1"
            or r.get("license_id") != "CC0-1.0"
            or r.get("rights_permitted") is not True
        ):
            raise ValueError("Pinned source identity/version or explicit rights differ")
        self.directory = self.raw_root / "elvhys-cold-room/1.1"
        self.metadata_path = self.directory / f"repository-metadata-{r['metadata_sha256']}.json"
        if (
            self.metadata_path.stat().st_size > 5_000_000
            or file_sha256(self.metadata_path) != r["metadata_sha256"]
        ):
            raise ValueError("Native repository metadata differs from pinned receipt")
        self.metadata_sha256 = r["metadata_sha256"]
        native = json.loads(self.metadata_path.read_text(encoding="utf-8"))["data"]["latestVersion"]
        if (native.get("versionNumber"), native.get("versionMinorNumber")) != (1, 1) or native.get(
            "license", {}
        ).get("rightsIdentifier") != "CC0-1.0":
            raise ValueError("Native version/rights do not confirm acquisition")
        self.native_files = {f["dataFile"]["filename"]: f for f in native["files"]}
        if len(self.native_files) != r["listed_file_count"] or r.get("omitted_files"):
            raise ValueError("Incomplete acquisition cannot claim the complete source profile")
        self.files, names = [], set()
        for entry in r["files"]:
            relative = PurePosixPath(entry["relative_path"])
            if (
                entry["status"] not in {"acquired", "cached"}
                or relative.is_absolute()
                or ".." in relative.parts
                or "\\" in entry["relative_path"]
                or ":" in entry["relative_path"]
                or relative.name != entry["name"]
                or entry["name"] in names
                or not re.fullmatch("[0-9a-f]{64}", entry["sha256"])
            ):
                raise ValueError("Incomplete, unsafe, duplicate or unhashed source attachment")
            path = (self.raw_root / Path(*relative.parts)).resolve()
            source = self.native_files[entry["name"]]
            if (
                not path.is_relative_to(self.directory.resolve())
                or path.stat().st_size != entry["size_bytes"]
                or source.get("restricted", False)
                or source["dataFile"]["filesize"] != entry["size_bytes"]
                or source["dataFile"]["checksum"]["value"] != entry["publisher_checksum"]
            ):
                raise ValueError("Actual source path/size/publisher checksum/access differs")
            names.add(entry["name"])
            self.files.append((entry, path))
        if (
            names != set(self.native_files)
            or sum(e["size_bytes"] for e, _ in self.files) > maximum_total_bytes
        ):
            raise ValueError("Acquisition scope or byte budget differs")
        self.files = tuple(self.files)
        by_name = {e["name"]: (e, p) for e, p in self.files}
        for name in (README_NAME, META_NAME, SENSOR_NAME):
            if name not in by_name or file_sha256(by_name[name][1]) != by_name[name][0]["sha256"]:
                raise ValueError("Required supporting source changed or absent")
        self.readme_sha256 = by_name[README_NAME][0]["sha256"]
        self.cases, self.positions = {}, {}
        for number, line in enumerate(
            by_name[README_NAME][1].read_text(encoding="utf-8").splitlines(), 1
        ):
            fields = tuple(line.split("\t"))
            match = re.match(r"^(\d{1,2})\t+([\d.]+) barg\t+([\d.]+) mm(.*)$", line)
            if match:
                n, pressure, diameter, description = match.groups()
                n = int(n)
                if n in self.cases:
                    raise ValueError("Duplicate nominal test identity")
                self.cases[n] = CryogenicRoomCase(
                    n,
                    number,
                    fields,
                    float(pressure) * 1e5,
                    float(diameter) * 0.001,
                    description,
                    "Invalid test" in description,
                    self.readme_sha256,
                )
            position = re.match(r"^(.+?)\t+(\d+)\t+(\d+)\t+(\d+)(?:\t(.*))?$", line)
            if position:
                name, x, y, z, roles = position.groups()
                p = CryogenicRoomPosition(
                    name,
                    tuple(float(v) * 0.001 for v in (x, y, z)),
                    roles or "",
                    number,
                    self.readme_sha256,
                )
                for alias in name.split(" / "):
                    if alias in self.positions:
                        raise ValueError("Duplicate source sensor identity")
                    self.positions[alias] = p
        self.recorders = tuple(
            CryogenicRoomRecorder(
                path,
                case=self.cases[int(match["case"])],
                positions=self.positions,
                expected_sha256=e["sha256"],
                directory_label=self.native_files[e["name"]].get("directoryLabel", ""),
            )
            for e, path in self.files
            if (match := FILE_PATTERN.fullmatch(e["name"]))
        )
        self.observed_case_numbers = tuple(sorted({r.case.number for r in self.recorders}))
        self.absent_case_numbers = tuple(sorted(set(self.cases) - set(self.observed_case_numbers)))

    def verify_sources(self):
        checked = {}
        for e, p in self.files:
            actual = file_sha256(p)
            if actual != e["sha256"] or p.stat().st_size != e["size_bytes"]:
                raise ValueError("Source SHA/size changed: " + e["name"])
            checked[e["name"]] = actual
        if (
            file_sha256(self.receipt_path) != self.receipt_sha256
            or file_sha256(self.metadata_path) != self.metadata_sha256
        ):
            raise ValueError("Pinned receipt/repository metadata changed")
        return checked
