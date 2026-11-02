"""USN thermal exports as bounded HDF5 observations, with unresolved clocks explicit.

Lach and Gaathaug, https://doi.org/10.23642/usn.17695082.v1, CC BY 4.0.
The profile reads native datasets; it supplies no thermal inversion or clock repair.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np

from ..core import Origin, immutable_array
from ..observations import ObservationTable, Variable
from ..units import convert_to_si
from .pressure_peaking import file_sha256

PROFILE_ID = "usn-carpark-thermal-v1-profile-1"
DESCRIPTION_SHA256 = "39f1cf8519babccaa9f9b4edb7ffc0380853a9280bcf1a3315af07f30487770b"
CLOCK_UNIT = "source_time_unit_unresolved"
SOURCE_FIELDS = {
    "HF": ("RHF1", "RHF2", "RHF3", "RHF4", "THF1", "THF2", "temp1", "temp2", "time", "timech7"),
    "MFM": ("mfr", "P", "T", "time"),
    "TS": (*tuple(f"TT{i}" for i in range(1, 10)), "trig", "time"),
    "Tank": ("T", "P", "time"),
    "Vent": ("T", "ACH", "vfr", "time"),
}

_PENDING_THERMAL_BLOCK_ISSUERS: set[object] = set()


def _issue_thermal_block(**values):
    token = object()
    _PENDING_THERMAL_BLOCK_ISSUERS.add(token)
    try:
        return ThermalBlock(**values, _issuer_token=token)
    except Exception:
        _PENDING_THERMAL_BLOCK_ISSUERS.discard(token)
        raise


def _integer(value, name, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or (maximum and value > maximum):
        raise ValueError(f"{name} must be a positive integer within its declared budget")
    return value


@dataclass(frozen=True, slots=True)
class ThermalChannel:
    path: str
    source_unit: str
    variable: Variable
    origin: Origin
    role: str


def _channel(group, field):
    path, basis = f"/{group}/{field}", f"USN {group}/{field}; source description {DESCRIPTION_SHA256}"
    if group == "HF" and field.startswith("RHF"):
        return ThermalChannel(path, "kW/m2", Variable(field, "radiative_heat_flux", "W/m2",
            basis + "; point radiometer; incident/net/absorbed and response unresolved"), Origin.MEASURED,
            "reported radiative heat-flux sensor; no total-flux or wall-load substitution")
    if group == "HF" and field.startswith("THF"):
        return ThermalChannel(path, "kW/m2", Variable(field, "reported_total_heat_flux", "W/m2",
            basis + "; convective/radiative plate-associated export; processing/response unresolved"),
            Origin.UNRESOLVED, "reported combined flux; independent-measurement/plate inversion provenance unresolved")
    if field in ("temp1", "temp2", "T") or field.startswith("TT"):
        role = {"HF": "steel-plate surface thermocouple; not gas temperature",
                "MFM": "Coriolis instrument/gas composite thermal reading; not gas temperature",
                "Tank": "bolt-installed thermocouple; not exact tank gas temperature",
                "Vent": "ventilation-pipe thermocouple; response/bulk-flow observation operator unresolved",
                "TS": "point thermocouple; source location table; response/averaging unresolved"}[group]
        return ThermalChannel(path, "degC", Variable(field, "temperature", "K", basis + "; " + role),
                              Origin.MEASURED, role)
    if field == "P":
        return ThermalChannel(path, "bar", Variable(field, "reported_pressure", "Pa",
            basis + ("; meter outlet" if group == "MFM" else "; tank outlet")
            + "; absolute/gauge reference unresolved"), Origin.MEASURED,
            "reported pressure; absolute/gauge reference unresolved")
    if field == "mfr":
        return ThermalChannel(path, "g/s", Variable(field, "mass_flow", "kg/s",
            basis + "; signed Coriolis output; no baseline subtraction or negative clipping"),
            Origin.MEASURED, "signed measured mass-flow output; direction/zero offset not repaired")
    if field == "ACH":
        return ThermalChannel(path, "1/h", Variable(field, "air_change_rate", "1/s", basis),
                              Origin.MEASURED, "reported air changes per hour; no room volume inferred")
    if field == "vfr":
        return ThermalChannel(path, "m3/h", Variable(field, "volume_flow", "m3/s", basis),
                              Origin.MEASURED, "ventilation volume-flow output; not mass flow")
    if field == "trig":
        return ThermalChannel(path, "unresolved", Variable(field, "reported_trigger", "unresolved", basis),
                              Origin.MEASURED, "trigger amplitude; unit/event/ignition mapping unresolved")
    raise ValueError("Unreviewed thermal channel")


@dataclass(frozen=True, slots=True)
class ThermalRecorder:
    identity: str
    clock_path: str | None
    channels: tuple[ThermalChannel, ...]
    samples: int
    clock_relationship: str
    candidate_clock_paths: tuple[str, ...] = ()
    clock_origin: Origin = Origin.MEASURED


@dataclass(frozen=True, slots=True)
class ThermalIssue:
    code: str
    channel: str
    count: int
    first_source_index: int | None = None


@dataclass(frozen=True, slots=True)
class ThermalBlock:
    values: np.ndarray
    valid: np.ndarray
    raw_values: np.ndarray
    source_indices: np.ndarray
    variables: tuple[Variable, ...]
    origins: tuple[Origin, ...]
    recorder: ThermalRecorder
    source_id: str
    source_sha256: str
    experiment_id: str
    context: tuple[tuple[str, str], ...]
    issues: tuple[ThermalIssue, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_THERMAL_BLOCK_ISSUERS:
            raise ValueError("Source-bound thermal blocks are issued only by the checked reader")
        _PENDING_THERMAL_BLOCK_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        for name, dtype in (("values", float), ("valid", bool), ("raw_values", float), ("source_indices", np.int64)):
            array = immutable_array(getattr(self, name), dtype=dtype, name=name)
            object.__setattr__(self, name, array)

    @property
    def observations(self):
        """Materialize immutable arrays/long row identities only for this requested block."""
        return ObservationTable(self.values, self.variables, self.valid,
            tuple(f"{self.source_id}|{self.experiment_id}|{self.source_sha256}|{self.recorder.identity}|vector-index-{i}"
                  for i in self.source_indices), (self.experiment_id,) * len(self.source_indices),
            self.origins, self.source_id, self.context)

    def as_time_series(self):
        raise ValueError("Source time unit/zero is unresolved; no automatic TimeSeries conversion")


class ThermalEffectsFile:
    """Read-only native HDF5 slicing, sharing existing hashes and unit/observation contracts.

    Default RHF3 and timech7 are separate vectors. Numeric equality/length never
    establishes synchronization. Source time units are not documented as seconds.
    """

    def __init__(self, path: str | Path, *, source_id: str, experiment_id: str,
                 expected_sha256: str, maximum_bytes: int = 150_000_000,
                 maximum_vector_samples: int = 2_000_000,
                 maximum_total_array_bytes: int = 300_000_000):
        if not all(isinstance(value, str) and value.strip() for value in (source_id, experiment_id, expected_sha256)):
            raise ValueError("Declare source, experiment and expected source SHA-256")
        self.path, self.source_id, self.experiment_id = Path(path), source_id, experiment_id
        self.expected_sha256 = expected_sha256
        self.maximum_bytes = _integer(maximum_bytes, "maximum_bytes")
        self.maximum_vector_samples = _integer(maximum_vector_samples, "maximum_vector_samples")
        self.maximum_total_array_bytes = _integer(maximum_total_array_bytes, "maximum_total_array_bytes")
        self._file = None
        self._explicit_associations = []

    def __enter__(self):
        import h5py

        if self.path.stat().st_size > self.maximum_bytes:
            raise ValueError("HDF5 source exceeds its compressed byte budget")
        self.sha256 = file_sha256(self.path)
        if self.sha256 != self.expected_sha256:
            raise ValueError("Thermal source SHA-256 differs from receipt")
        self._file = h5py.File(self.path, "r")
        try:
            required = {"HF", "MFM", "Tank", "Vent"}
            if not required <= set(self._file) or set(self._file) - required - {"TS", "#refs#"}:
                raise ValueError("Unreviewed thermal MAT root schema")
            if any(not isinstance(self._file.get(name, getlink=True), h5py.HardLink) for name in self._file):
                raise ValueError("External/soft HDF5 root links are forbidden")
            inventory, total = [], 0
            for group in self._file:
                if group == "#refs#":
                    continue
                if not isinstance(self._file.get(group, getlink=True), h5py.HardLink):
                    raise ValueError("External/soft HDF5 links are forbidden")
                obj = self._file[group]
                if (not isinstance(obj, h5py.Group) or set(obj) != set(SOURCE_FIELDS[group])
                        or obj.attrs.get("MATLAB_class") != b"struct"):
                    raise ValueError("Unreviewed native thermal struct fields")
                for field in obj:
                    if not isinstance(obj.get(field, getlink=True), h5py.HardLink):
                        raise ValueError("External/soft HDF5 dataset links are forbidden")
                    dataset = obj[field]
                    if (not isinstance(dataset, h5py.Dataset) or dataset.ndim != 2
                            or 1 not in dataset.shape or not dataset.size
                            or dataset.dtype.kind != "f" or dataset.dtype.itemsize != 8
                            or dataset.attrs.get("MATLAB_class") != b"double"
                            or dataset.is_virtual or dataset.external
                            or dataset.compression not in (None, "gzip")):
                        raise ValueError("Unreviewed native double vector/storage schema")
                    if dataset.size > self.maximum_vector_samples:
                        raise ValueError("Source vector exceeds its sample budget")
                    total += dataset.size * 8
                    inventory.append((dataset.name, dataset.shape, str(dataset.dtype), dataset.compression))
            if total > self.maximum_total_array_bytes:
                raise ValueError("Source numeric inventory exceeds its expanded budget")
            self.inventory = tuple(inventory)
            self.total_array_bytes = total
            self.recorders = self._recorders()
            return self
        except Exception:
            self._file.close()
            self._file = None
            raise

    def __exit__(self, *args):
        self._file.close()
        self._file = None
        if file_sha256(self.path) != self.sha256:
            raise ValueError("Thermal source changed while streaming")

    def _recorders(self):
        recorders = []
        for group in SOURCE_FIELDS:
            if group not in self._file:
                continue
            clock = f"/{group}/time"
            count = self._file[clock].size
            channels = []
            for field in SOURCE_FIELDS[group]:
                if field in ("time", "timech7"):
                    continue
                channel = _channel(group, field)
                size = self._file[channel.path].size
                if field == "RHF3":
                    recorders.append(ThermalRecorder(channel.path + "/unclocked", None, (channel,), size,
                        "RHF3 physical clock association unresolved; equal lengths are not evidence",
                        ("/HF/timech7",), Origin.UNRESOLVED))
                elif size != count:
                    recorders.append(ThermalRecorder(channel.path + "/unclocked", None, (channel,), size,
                        "source group clock/vector length mismatch; no truncation or borrowed clock",
                        (clock,), Origin.UNRESOLVED))
                else:
                    channels.append(channel)
            recorders.append(ThermalRecorder(clock, clock, tuple(channels), count,
                "documented source group clock; physical time unit/zero and inter-recorder mapping unresolved"))
            if group == "HF":
                recorders.append(ThermalRecorder("/HF/timech7/clock-only", "/HF/timech7", (),
                    self._file["/HF/timech7"].size, "independent source clock vector; no default sensor pairing"))
        return tuple(recorders)

    def associate_clock(self, channel_path: str, clock_path: str, *, evidence_id: str):
        """Explicit caller association, not a default measured clock relationship."""
        if self._file is None:
            raise ValueError("Declare a clock association inside its source context")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("A caller clock association requires explicit evidence identity")
        available = {channel.path: channel for recorder in self.recorders for channel in recorder.channels}
        clocks = {recorder.clock_path for recorder in self.recorders if recorder.clock_path}
        if channel_path not in available or clock_path not in clocks:
            raise ValueError("Declare an existing source signal and existing source clock")
        if self._file[channel_path].size != self._file[clock_path].size:
            raise ValueError("Clock/vector lengths differ; no automatic repair")
        recorder = ThermalRecorder(f"{channel_path}/caller-clock-{clock_path}", clock_path,
            (available[channel_path],), self._file[channel_path].size,
            f"caller reconstructed association: {evidence_id}; physical time unit remains unresolved",
            (), Origin.RECONSTRUCTED)
        self._explicit_associations.append(recorder)
        return recorder

    def _slice(self, path, first, stop):
        dataset = self._file[path]
        return np.asarray(dataset[first:stop, 0] if dataset.shape[1] == 1 else dataset[0, first:stop], dtype=float)

    def iter_blocks(self, recorder: ThermalRecorder, *, block_rows: int = 16_384,
                    first_index: int = 1, last_index: int | None = None) -> Iterator[ThermalBlock]:
        if self._file is None:
            raise ValueError("Consume observations inside the source context manager")
        if recorder not in self.recorders and recorder not in self._explicit_associations:
            raise ValueError("Recorder clock relationship was not qualified or explicitly declared")
        _integer(block_rows, "block_rows", 100_000)
        _integer(first_index, "first_index")
        last = recorder.samples if last_index is None else _integer(last_index, "last_index")
        if first_index > last or last > recorder.samples:
            raise ValueError("Source vector window lies outside the native export")
        # A public descriptor must not turn arbitrary datasets into physical fields.
        known = {channel.path: channel for item in self.recorders for channel in item.channels}
        if (any(known.get(c.path) != c or self._file[c.path].size != recorder.samples for c in recorder.channels)
                or (recorder.clock_path and self._file[recorder.clock_path].size != recorder.samples)):
            raise ValueError("Recorder descriptor differs from the qualified source vectors")
        clock_id = f"{self.source_id}|{self.sha256}|{recorder.identity}|{recorder.clock_relationship}"
        variables = (Variable("source_index", "source_vector_index", "1"),
                     Variable("reported_clock", "reported_time_coordinate", CLOCK_UNIT, clock_id),
                     *(channel.variable for channel in recorder.channels))
        origins = (Origin.RECONSTRUCTED, recorder.clock_origin, *(c.origin for c in recorder.channels))
        previous = None
        paths = ([recorder.clock_path] if recorder.clock_path else []) + [c.path for c in recorder.channels]
        shapes = ";".join(f"{path}:{self._file[path].shape}" for path in paths)
        for first in range(first_index - 1, last, block_rows):
            stop = min(first + block_rows, last)
            indices = np.arange(first + 1, stop + 1)
            clock = self._slice(recorder.clock_path, first, stop) if recorder.clock_path else np.full(stop - first, np.nan)
            raw = np.column_stack((clock, *(self._slice(c.path, first, stop) for c in recorder.channels)))
            values = np.column_stack((indices, raw))
            for column, channel in enumerate(recorder.channels, 2):
                if channel.source_unit in ("g/s", "degC", "bar"):
                    values[:, column] = convert_to_si(raw[:, column - 1],
                        quantity=channel.variable.quantity, unit=channel.source_unit)
                elif channel.source_unit == "kW/m2":
                    values[:, column] *= 1000.
                elif channel.source_unit in ("1/h", "m3/h"):
                    values[:, column] /= 3600.
            valid = np.isfinite(values)
            issues = []
            for column, variable in enumerate(variables):
                bad = ~valid[:, column]
                if variable.quantity == "temperature":
                    invalid_temperature = np.isfinite(values[:, column]) & (values[:, column] <= 0)
                    valid[:, column] &= ~invalid_temperature
                    if np.any(invalid_temperature):
                        issues.append(ThermalIssue("nonpositive_absolute_temperature", variable.name,
                            int(invalid_temperature.sum()), int(indices[np.flatnonzero(invalid_temperature)[0]])))
                if np.any(bad):
                    issues.append(ThermalIssue("missing_nonfinite_or_unresolved_clock", variable.name,
                        int(bad.sum()), int(indices[np.flatnonzero(bad)[0]])))
            if recorder.clock_path:
                finite = clock[np.isfinite(clock)]
                backwards = int(np.count_nonzero(np.diff(finite) <= 0))
                if len(finite):
                    backwards += int(previous is not None and finite[0] <= previous)
                    previous = finite[-1]
                if backwards:
                    issues.append(ThermalIssue("nonincreasing_clock_retained", "reported_clock", backwards))
            context = (("profile", PROFILE_ID), ("source_sha256", self.sha256),
                ("source_file", self.path.name),
                ("description_sha256", DESCRIPTION_SHA256), ("recorder_export", recorder.identity),
                ("clock_path", recorder.clock_path or "unresolved"),
                ("clock_relationship", recorder.clock_relationship),
                ("candidate_clock_paths", ";".join(recorder.candidate_clock_paths)),
                ("source_vector_shapes", shapes), ("clock_unit", "unresolved; not assumed seconds"),
                ("source_index", "1-based native vector element; original HDF5 orientation retained in schema"))
            yield _issue_thermal_block(
                values=values, valid=valid, raw_values=raw, source_indices=indices,
                variables=variables, origins=origins, recorder=recorder,
                source_id=self.source_id, source_sha256=self.sha256,
                experiment_id=self.experiment_id, context=context, issues=tuple(issues))


def thermal_location_rows(path: str | Path, *, expected_sha256: str = DESCRIPTION_SHA256):
    """Read original location-table cells as local runtime metadata, without copying a public table.

    The source order is y,x,z in mm. The last ventilation row is incomplete/non-Cartesian;
    no origin, coordinate permutation or missing coordinate is invented.
    """
    path = Path(path)
    if path.stat().st_size > 1_000_000 or file_sha256(path) != expected_sha256:
        raise ValueError("Location description exceeds budget or differs from receipt")
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(path) as archive:
        if (len(archive.infolist()) > 100 or sum(i.file_size for i in archive.infolist()) > 5_000_000
                or archive.getinfo("word/document.xml").file_size > 1_000_000):
            raise ValueError("DOCX metadata expansion exceeds budget")
        root = ET.fromstring(archive.read("word/document.xml"))
    tables = root.findall(".//w:tbl", namespace)
    if len(tables) != 1:
        raise ValueError("Location table schema differs from the reviewed source")
    rows = tuple(tuple("".join(text.text or "" for text in cell.findall(".//w:t", namespace))
                 for cell in row.findall("w:tc", namespace)) for row in tables[0].findall("w:tr", namespace))
    if len(tables) != 1 or rows[:2] != (("Location parameters [mm]",), ("", "y", "x", "z")):
        raise ValueError("Location table schema differs from the reviewed source")
    if file_sha256(path) != expected_sha256:
        raise ValueError("Location description changed during decoding")
    return rows
