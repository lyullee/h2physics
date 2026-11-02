"""Source-bound recorder access for the public USN ignited-release MAT files.

SIGMA and GEN3i retain their independent clocks. Only the documented SIGMA
hydrogen mass-flow channel is prepared for a finite-source boundary; no pressure
alignment, ignition-time inference, or enclosure model validation is performed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..core import Origin, TimeSeries
from ._mat_export import decode_recorded_mat

DOI = "10.23642/usn.17934047.v1"
LICENSE_ID = "CC-BY-4.0"
PROFILE_ID = "usn-pressure-ignited-v1-profile-1"
SOURCE_FILE = "HTE341USN0015READ191111.mat"
SOURCE_SIZE_BYTES = 40_666_968
SOURCE_SHA256 = "3c03a1fbc0164622e0354505b9272d0deb44dffbfe1baaf33e591533b83be5a4"
SOURCE_ID = f"{DOI}:{SOURCE_FILE}"
SIGMA_SHAPE = (999_999, 7)
GEN3I_SHAPE = (78_894, 3)
SIGMA_DIMENSIONS = ("[s]", "[g/s]", "[bar]", "[oC]", "[oC]", "[oC]", "[oC]")
SIGMA_LABELS = (
    "time", "Mass Flow", "Pressure at Coriolis", "Temperature", "Temperature",
    "Temperature", "Temperature",
)
GEN3I_DIMENSIONS = ("s", "v", "kPa")
GEN3I_LABELS = ("Time", "T1", "P1")
TAVG_SHAPE = (999_999, 1)
SIGMA_CHANNELS = (
    "mass_flow_g_s", "meter_outlet_pressure_bar", "T1_degC", "T2_degC",
    "T3_degC", "T4_degC",
)
GEN3I_CHANNELS = ("unresolved_gen3i_channel_2", "reported_overpressure_kPa")
_PENDING_RUNS: set[object] = set()
_PENDING_BLOCKS: set[object] = set()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_cells(array):
    return tuple("".join(np.asarray(item).ravel().astype(str)) for item in np.asarray(array).ravel())


def _issue_block(**values):
    token = object()
    _PENDING_BLOCKS.add(token)
    try:
        return IgnitedFlowBlock(**values, _issuer=token)
    except Exception:
        _PENDING_BLOCKS.discard(token)
        raise


def _issue_run(**values):
    token = object()
    _PENDING_RUNS.add(token)
    try:
        return PressureIgnitedRun(**values, _issuer=token)
    except Exception:
        _PENDING_RUNS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class IgnitedFlowBlock:
    """A bounded, row-preserving view of the SIGMA flow channel in raw g/s."""

    series: TimeSeries
    source_rows: tuple[int, ...]
    experiment_id: str
    source_sha256: str
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_BLOCKS:
            raise ValueError("Use the checksum-bound ignited MAT reader to issue flow blocks")
        _PENDING_BLOCKS.remove(self._issuer)
        rows = tuple(self.source_rows)
        if (self.series.origin is not Origin.MEASURED
                or self.series.channels != ("mass_flow_g_s",)
                or self.series.units != ("g/s",)
                or self.series.quantities != ("mass_flow",)
                or self.series.source_id != SOURCE_ID
                or len(rows) != len(self.series.time_s)
                or any(type(row) is not int or row < 1 for row in rows)
                or any(b <= a for a, b in zip(rows, rows[1:]))
                or self.source_sha256 != SOURCE_SHA256):
            raise ValueError("Ignited measured-flow block differs from the pinned source profile")
        object.__setattr__(self, "source_rows", rows)
        object.__setattr__(self, "_issuer", None)


@dataclass(frozen=True, slots=True)
class PressureIgnitedRun:
    """Pinned MAT export retaining both recorders without aligning their clocks."""

    source_path: Path
    source_sha256: str
    experiment_id: str
    sigma_raw: np.ndarray
    gen3i_raw: np.ndarray
    tavg_raw: np.ndarray
    sigma_labels: tuple[str, ...]
    gen3i_labels: tuple[str, ...]
    sigma_dimensions: tuple[str, ...]
    gen3i_dimensions: tuple[str, ...]
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_RUNS:
            raise ValueError("Use load_pressure_ignited_mat() to issue a source run")
        _PENDING_RUNS.remove(self._issuer)
        path = Path(self.source_path)
        sigma = np.array(self.sigma_raw, dtype=float, copy=True)
        gen3i = np.array(self.gen3i_raw, dtype=float, copy=True)
        tavg = np.array(self.tavg_raw, dtype=float, copy=True)
        if (not path.is_absolute() or path.is_symlink() or path.name != SOURCE_FILE
                or self.source_sha256 != SOURCE_SHA256 or not self.experiment_id.strip()
                or sigma.shape != SIGMA_SHAPE or gen3i.shape != GEN3I_SHAPE
                or tavg.shape != TAVG_SHAPE
                or tuple(self.sigma_labels) != SIGMA_LABELS
                or tuple(self.gen3i_labels) != GEN3I_LABELS
                or tuple(self.sigma_dimensions) != SIGMA_DIMENSIONS
                or tuple(self.gen3i_dimensions) != GEN3I_DIMENSIONS):
            raise ValueError("Ignited MAT run identity or matrix schema differs from its receipt")
        for name, values in (("SIGMA time", sigma[:, 0]), ("GEN3i time", gen3i[:, 0])):
            if not np.all(np.isfinite(values)) or np.any(np.diff(values) <= 0.):
                raise ValueError(f"{name} must be finite and strictly increasing on its own clock")
        sigma.setflags(write=False)
        gen3i.setflags(write=False)
        tavg.setflags(write=False)
        object.__setattr__(self, "source_path", path)
        object.__setattr__(self, "sigma_raw", sigma)
        object.__setattr__(self, "gen3i_raw", gen3i)
        object.__setattr__(self, "tavg_raw", tavg)
        object.__setattr__(self, "sigma_labels", tuple(self.sigma_labels))
        object.__setattr__(self, "gen3i_labels", tuple(self.gen3i_labels))
        object.__setattr__(self, "sigma_dimensions", tuple(self.sigma_dimensions))
        object.__setattr__(self, "gen3i_dimensions", tuple(self.gen3i_dimensions))
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        digest = hashlib.sha256()
        digest.update(repr((self.source_sha256, self.experiment_id,
                            self.sigma_labels, self.gen3i_labels,
                            self.sigma_dimensions, self.gen3i_dimensions)).encode("utf-8"))
        for array in (self.sigma_raw, self.gen3i_raw):
            digest.update(np.ascontiguousarray(array).tobytes())
        digest.update(b"Tavg\0")
        digest.update(np.ascontiguousarray(self.tavg_raw).tobytes())
        return digest.hexdigest()

    def require_current(self):
        path = Path(self.source_path)
        if (path.is_symlink() or not path.is_file()
                or path.stat().st_size != SOURCE_SIZE_BYTES
                or _file_sha256(path) != SOURCE_SHA256
                or self._seal != self._fingerprint()):
            raise ValueError("Ignited source MAT or retained recorder rows changed")
        return self

    def iter_flow_blocks(self, *, block_rows: int = 100_000, time_window_s=None):
        self.require_current()
        if isinstance(block_rows, bool) or not isinstance(block_rows, int) or block_rows < 1:
            raise ValueError("block_rows must be a positive integer")
        first, stop = 0, len(self.sigma_raw)
        if time_window_s is not None:
            window = np.asarray(time_window_s, dtype=float)
            if window.shape != (2,) or not np.all(np.isfinite(window)) or window[1] < window[0]:
                raise ValueError("Declare a finite ordered SIGMA time window")
            first = int(np.searchsorted(self.sigma_raw[:, 0], window[0], side="left"))
            stop = int(np.searchsorted(self.sigma_raw[:, 0], window[1], side="right"))
        clock_id = f"{SOURCE_ID}|SIGMA|independent-recorder-clock"
        for start in range(first, stop, block_rows):
            end = min(start + block_rows, stop)
            raw = self.sigma_raw[start:end]
            values = raw[:, 1:2]
            valid = np.isfinite(values)
            series = TimeSeries(
                raw[:, 0], values, ("mass_flow_g_s",), ("g/s",), valid,
                clock_id, Origin.MEASURED, SOURCE_ID, ("mass_flow",),
                ("source-defined Coriolis mass-flow channel; negative values retained",),
            )
            yield _issue_block(series=series,
                source_rows=tuple(range(start + 1, end + 1)),
                experiment_id=self.experiment_id, source_sha256=self.source_sha256)


def load_pressure_ignited_mat(path: str | Path, *, experiment_id: str,
                              expected_sha256: str = SOURCE_SHA256,
                              maximum_array_bytes: int = 80_000_000) -> PressureIgnitedRun:
    """Decode one exact admitted MAT export and preserve SIGMA/GEN3i separately."""
    supplied = Path(path)
    if supplied.is_symlink() or not supplied.is_absolute():
        raise ValueError("Ignited source path must be absolute and cannot be a symbolic link")
    source = supplied.resolve()
    if source.name != SOURCE_FILE or expected_sha256 != SOURCE_SHA256:
        raise ValueError("MAT file differs from the pinned USN ignited-release attachment")
    if type(maximum_array_bytes) is not int or maximum_array_bytes < 1:
        raise ValueError("maximum_array_bytes must be a positive integer")
    source, data, shapes = decode_recorded_mat(
        source, expected_sha256=SOURCE_SHA256,
        expected_file_bytes=SOURCE_SIZE_BYTES, maximum_file_bytes=SOURCE_SIZE_BYTES,
        maximum_array_bytes=maximum_array_bytes,
        numeric_columns={"SIGMA": 7, "GEN3i": 3, "Tavg": 1},
        metadata_names=("SIGMAdimensions", "SIGMAunits", "GENdimensions", "GENunits"),
    )
    if (shapes["SIGMA"][0] != SIGMA_SHAPE or shapes["GEN3i"][0] != GEN3I_SHAPE
            or shapes["SIGMAdimensions"][0] != (1, 7)
            or shapes["SIGMAunits"][0] != (1, 7)
            or shapes["GENdimensions"][0] != (1, 3)
            or shapes["GENunits"][0] != (1, 3)
            or shapes["Tavg"][0] != TAVG_SHAPE):
        raise ValueError("Ignited MAT dimensions or metadata-cell schema differs from reviewed profile")
    sigma_dimensions = _text_cells(data["SIGMAdimensions"])
    sigma_labels = _text_cells(data["SIGMAunits"])
    gen3i_dimensions = _text_cells(data["GENdimensions"])
    gen3i_labels = _text_cells(data["GENunits"])
    if (sigma_dimensions != SIGMA_DIMENSIONS or sigma_labels != SIGMA_LABELS
            or gen3i_dimensions != GEN3I_DIMENSIONS or gen3i_labels != GEN3I_LABELS):
        raise ValueError("Source dimension/unit labels differ from the reviewed recorder profile")
    return _issue_run(
        source_path=source, source_sha256=SOURCE_SHA256, experiment_id=experiment_id,
        sigma_raw=data["SIGMA"], gen3i_raw=data["GEN3i"],
        tavg_raw=data["Tavg"],
        sigma_labels=sigma_labels, gen3i_labels=gen3i_labels,
        sigma_dimensions=sigma_dimensions, gen3i_dimensions=gen3i_dimensions,
    )


__all__ = [
    "DOI", "GEN3I_CHANNELS", "GEN3I_DIMENSIONS", "GEN3I_LABELS", "LICENSE_ID",
    "PROFILE_ID", "PressureIgnitedRun",
    "SOURCE_FILE", "SOURCE_ID", "SOURCE_SHA256", "SOURCE_SIZE_BYTES",
    "SIGMA_CHANNELS", "SIGMA_DIMENSIONS", "SIGMA_LABELS", "load_pressure_ignited_mat",
]
