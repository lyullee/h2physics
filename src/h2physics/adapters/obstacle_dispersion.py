"""Unverified external FDS CFD with actual geometry/species and native ledgers.

FDS owns the obstacle-resolved low-Mach momentum, species and sensible-enthalpy
equations. This host writes original native inputs, runs the selected binary and
audits original outputs. There is no duplicate CFD solver or HyRAM/SLAB fallback.
"""

from __future__ import annotations

import csv
import hashlib
import math
import os
import re
import subprocess
from collections import deque
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from types import MappingProxyType

import numpy as np

from scipy.integrate import trapezoid

from ..core import immutable_array, Origin, finite

FDS_VERSION = "6.11.1"
FDS_REVISION = "ff928dbf68a2623ced3a007be75391c6dc6c9f90"
FDS_SPECIES_BASIS = "FDS-6.11.1:built-in-HYDROGEN/AIR:spin-unresolved:native-sensible-enthalpy"


class _ObstacleResultIssuer:
    __slots__ = ("owner",)

    def __init__(self):
        self.owner = None


def _obstacle_result_signature(result):
    digest = hashlib.sha256()
    for identity in (result.case, result.engine, result.budgets, result.native_process,
                     result.artifacts, result.device_table, result.energy_table):
        digest.update(str(id(identity)).encode("ascii"))
    digest.update(repr((result.native_git_text, result.resolved_obstacles,
                        result.failures, result.numerically_admitted,
                        result.software_status, result.residual_columns,
                        result.artifacts.directory,
                        tuple(sorted(result.artifacts.files_sha256.items())),
                        getattr(result.native_process, "args", None),
                        getattr(result.native_process, "returncode", None))).encode("utf-8"))
    for array in (result.time_s, result.hydrogen_mass_kg, result.total_mass_kg,
                  result.sensible_enthalpy_j, result.native_integrals, result.residuals,
                  result.receptor_hydrogen_mole_fraction,
                  result.device_table.values, result.energy_table.values):
        contiguous = np.ascontiguousarray(array)
        digest.update(contiguous.dtype.str.encode("ascii"))
        digest.update(repr(contiguous.shape).encode("ascii"))
        digest.update(contiguous.tobytes())
    digest.update(repr((result.device_table.columns, result.device_table.units,
                        result.energy_table.columns, result.energy_table.units)).encode("utf-8"))
    for payload in (getattr(result.native_process, "stdout", b""),
                    getattr(result.native_process, "stderr", b"")):
        if isinstance(payload, bytes):
            digest.update(payload)
        else:
            digest.update(repr(payload).encode("utf-8"))
    return digest.hexdigest()


def _id(value):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", value) is None:
        raise ValueError(
            "Native IDs must be short letters/digits/underscores, beginning with a letter"
        )


def _text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Explicit source/frame/clock/domain/thermal/mesh evidence is required")


def _sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _array(value):
    data = np.array(value, dtype=float, copy=True)
    if not np.all(np.isfinite(data)):
        raise ValueError("Native numerical outputs must remain finite")
    data = immutable_array(data, name="data")
    return data


def _bounds(value):
    result = tuple(finite(v, "Cartesian bound") for v in value)
    if len(result) != 6 or any(result[2 * i + 1] <= result[2 * i] for i in range(3)):
        raise ValueError("Cartesian XB must have three positive ordered extents in m")
    return result


def _numbers(values):
    return ",".join(format(float(v), ".16g") for v in values)


@dataclass(frozen=True, slots=True)
class CartesianObstacle:
    identifier: str
    bounds_m: tuple[float, ...]

    def __post_init__(self):
        _id(self.identifier)
        object.__setattr__(self, "bounds_m", _bounds(self.bounds_m))

    @property
    def volume_m3(self):
        return math.prod(self.bounds_m[2 * i + 1] - self.bounds_m[2 * i] for i in range(3))


@dataclass(frozen=True, slots=True)
class CFDMesh:
    bounds_m: tuple[float, ...]
    cells: tuple[int, int, int]
    obstacles: tuple[CartesianObstacle, ...]
    geometry_evidence_id: str
    grid_evidence_id: str
    geometry_tolerance_m: float

    def __post_init__(self):
        bounds, cells = _bounds(self.bounds_m), tuple(self.cells)
        if len(cells) != 3 or any(type(n) is not int or n < 4 for n in cells):
            raise ValueError("Use a genuinely 3D mesh with at least four cells on every axis")
        _text(self.geometry_evidence_id, self.grid_evidence_id)
        finite(self.geometry_tolerance_m, "geometry alignment tolerance", positive=True)
        obstacles = tuple(self.obstacles)
        if any(type(o) is not CartesianObstacle for o in obstacles):
            raise TypeError("Use actual impermeable Cartesian obstacle records")
        if len({o.identifier for o in obstacles}) != len(obstacles):
            raise ValueError("Obstacle IDs must be unique")
        object.__setattr__(self, "bounds_m", bounds)
        object.__setattr__(self, "cells", cells)
        object.__setattr__(self, "obstacles", obstacles)
        for obstacle in obstacles:
            for axis in range(3):
                lo, hi = obstacle.bounds_m[2 * axis : 2 * axis + 2]
                if lo < bounds[2 * axis] or hi > bounds[2 * axis + 1]:
                    raise ValueError("An obstacle lies outside the native mesh")
                if self.face_index(hi, axis) <= self.face_index(lo, axis):
                    raise ValueError(
                        "A volume obstacle must span at least one native cell on every axis"
                    )
        for i, a in enumerate(obstacles):
            for b in obstacles[i + 1 :]:
                if all(
                    min(a.bounds_m[2 * k + 1], b.bounds_m[2 * k + 1])
                    > max(a.bounds_m[2 * k], b.bounds_m[2 * k])
                    for k in range(3)
                ):
                    raise ValueError(
                        "Overlapping obstacle volumes are unsupported; do not double-count solids"
                    )

    @property
    def spacing_m(self):
        return tuple(
            (self.bounds_m[2 * i + 1] - self.bounds_m[2 * i]) / self.cells[i] for i in range(3)
        )

    @property
    def fluid_volume_m3(self):
        return math.prod(self.bounds_m[2 * i + 1] - self.bounds_m[2 * i] for i in range(3)) - sum(
            o.volume_m3 for o in self.obstacles
        )

    def face_index(self, coordinate, axis):
        index = round((coordinate - self.bounds_m[2 * axis]) / self.spacing_m[axis])
        reconstructed = self.bounds_m[2 * axis] + index * self.spacing_m[axis]
        if (
            abs(reconstructed - coordinate) > self.geometry_tolerance_m
            or not 0 <= index <= self.cells[axis]
        ):
            raise ValueError(
                "Obstacle/source faces must align exactly with the declared grid; no silent snapping"
            )
        return index

    def solid_mask(self):
        mask = np.zeros(self.cells, dtype=bool)
        for box in self.obstacles:
            limits = [
                slice(
                    self.face_index(box.bounds_m[2 * i], i),
                    self.face_index(box.bounds_m[2 * i + 1], i),
                )
                for i in range(3)
            ]
            mask[tuple(limits)] = True
        return mask

    def connected_fluid(self):
        """Geometry admission only, not a flow/dispersion solver."""
        mask = self.solid_mask()
        free = np.argwhere(~mask)
        if not len(free):
            raise ValueError("No fluid cells remain")
        seen = {tuple(free[0])}
        queue = deque(seen)
        while queue:
            cell = queue.popleft()
            for axis in range(3):
                for sign in (-1, 1):
                    target = tuple(v + sign if i == axis else v for i, v in enumerate(cell))
                    if (
                        all(0 <= v < n for v, n in zip(target, self.cells, strict=True))
                        and not mask[target]
                        and target not in seen
                    ):
                        seen.add(target)
                        queue.append(target)
        if len(seen) != len(free):
            raise ValueError(
                "This sealed one-pressure-zone reference requires connected fluid cells"
            )
        return tuple(
            self.bounds_m[2 * i] + (int(free[0, i]) + 0.5) * self.spacing_m[i] for i in range(3)
        )


@dataclass(frozen=True, slots=True)
class HydrogenCFDSource:
    identifier: str
    time_s: tuple[float, ...]
    mass_rate_kg_s: tuple[float, ...]
    inlet_yz_m: tuple[float, float, float, float]
    temperature_k: float
    clock_id: str
    frame_id: str
    source_evidence_id: str
    post_expansion_admission_id: str
    species_basis: str
    origin: Origin

    def __post_init__(self):
        _id(self.identifier)
        _text(
            self.clock_id, self.frame_id, self.source_evidence_id, self.post_expansion_admission_id
        )
        times = tuple(finite(t, "source relative time") for t in self.time_s)
        rates = tuple(finite(r, "source H2 rate") for r in self.mass_rate_kg_s)
        inlet = tuple(finite(v, "source patch coordinate") for v in self.inlet_yz_m)
        if (
            len(times) < 2
            or len(times) != len(rates)
            or times[0] != 0
            or min(rates) < 0
            or any(b <= a for a, b in zip(times[:-1], times[1:], strict=True))
        ):
            raise ValueError(
                "Use an ordered finite nonnegative H2 mass-rate history starting at native t=0"
            )
        if len(inlet) != 4 or inlet[0] >= inlet[1] or inlet[2] >= inlet[3]:
            raise ValueError("Specify a positive inlet patch on the mesh x-min boundary")
        finite(self.temperature_k, "prescribed post-expansion source T", positive=True)
        if self.species_basis != FDS_SPECIES_BASIS:
            raise ValueError(
                "Do not relabel CoolProp/para-H2 caloric data as FDS built-in thermochemistry"
            )
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Source origin must be resolved")
        for name, value in (
            ("time_s", times),
            ("mass_rate_kg_s", rates),
            ("inlet_yz_m", inlet),
            ("origin", origin),
        ):
            object.__setattr__(self, name, value)

    @property
    def area_m2(self):
        return (self.inlet_yz_m[1] - self.inlet_yz_m[0]) * (self.inlet_yz_m[3] - self.inlet_yz_m[2])

    def integrated_mass_kg(self, time_s):
        if not self.time_s[0] <= time_s <= self.time_s[-1]:
            raise ValueError("No source extrapolation")
        knots = np.r_[0.0, [t for t in self.time_s if 0 < t < time_s], time_s]
        return float(trapezoid(np.interp(knots, self.time_s, self.mass_rate_kg_s), knots))


@dataclass(frozen=True, slots=True)
class CFDReceptor:
    identifier: str
    position_m: tuple[float, float, float]

    def __post_init__(self):
        _id(self.identifier)
        xyz = tuple(finite(v, "receptor coordinate") for v in self.position_m)
        if len(xyz) != 3:
            raise ValueError("A receptor needs three coordinates in the declared frame")
        object.__setattr__(self, "position_m", xyz)


@dataclass(frozen=True, slots=True)
class ObstacleDispersionCase:
    identifier: str
    mesh: CFDMesh
    source: HydrogenCFDSource
    receptors: tuple[CFDReceptor, ...]
    end_time_s: float
    start_time_s: float
    ambient_temperature_k: float
    ambient_pressure_pa_absolute: float
    gravity_m_s2: tuple[float, float, float]
    simulation_mode: str
    output_interval_s: float
    initial_time_step_s: float
    pressure_velocity_tolerance_m_s: float
    maximum_pressure_iterations: int
    low_mach_domain_evidence_id: str
    diagnostic_adiabatic_boundary_evidence_id: str

    def __post_init__(self):
        _id(self.identifier)
        _text(self.low_mach_domain_evidence_id, self.diagnostic_adiabatic_boundary_evidence_id)
        if type(self.mesh) is not CFDMesh or type(self.source) is not HydrogenCFDSource:
            raise TypeError("Use actual native geometry and qualified source objects")
        for name in (
            "end_time_s",
            "ambient_temperature_k",
            "ambient_pressure_pa_absolute",
            "output_interval_s",
            "initial_time_step_s",
            "pressure_velocity_tolerance_m_s",
        ):
            finite(getattr(self, name), name, positive=True)
        finite(self.start_time_s, "operation clock origin")
        if not all(
            250.0 <= t <= 400.0 for t in (self.ambient_temperature_k, self.source.temperature_k)
        ):
            raise ValueError("This all-gas warm-reference source/ambient domain is250..400K")
        gravity = tuple(finite(v, "gravity component") for v in self.gravity_m_s2)
        if len(gravity) != 3 or self.simulation_mode not in {"DNS", "LES"}:
            raise ValueError("Select a native DNS or LES model and three gravity components")
        if (
            type(self.maximum_pressure_iterations) is not int
            or self.maximum_pressure_iterations < 1
            or self.source.time_s[-1] < self.end_time_s
            or self.output_interval_s > self.end_time_s
        ):
            raise ValueError("Source/output support and pressure iteration count must be explicit")
        receptors = tuple(self.receptors)
        if (
            not receptors
            or any(type(r) is not CFDReceptor for r in receptors)
            or len({r.identifier for r in receptors}) != len(receptors)
        ):
            raise ValueError("Use unique explicit receptor objects")
        object.__setattr__(self, "receptors", receptors)
        object.__setattr__(self, "gravity_m_s2", gravity)
        for coordinate, axis in zip(self.source.inlet_yz_m, (1, 1, 2, 2), strict=True):
            self.mesh.face_index(coordinate, axis)
        mask = self.mesh.solid_mask()
        j0, j1 = (self.mesh.face_index(v, 1) for v in self.source.inlet_yz_m[:2])
        k0, k1 = (self.mesh.face_index(v, 2) for v in self.source.inlet_yz_m[2:])
        if j1 <= j0 or k1 <= k0:
            raise ValueError("The native inlet must cover a positive cell-face patch")
        if mask[0, j0:j1, k0:k1].any():
            raise ValueError("A declared solid covers part of the inlet")
        for receptor in receptors:
            indices = tuple(
                math.floor((v - self.mesh.bounds_m[2 * i]) / self.mesh.spacing_m[i])
                for i, v in enumerate(receptor.position_m)
            )
            if (
                not all(0 <= value < n for value, n in zip(indices, self.mesh.cells, strict=True))
                or mask[indices]
            ):
                raise ValueError("A receptor is outside the fluid domain or inside an obstacle")


@dataclass(frozen=True, slots=True)
class FDSEngine:
    executable: Path
    executable_sha256: str
    executable_evidence_id: str
    threads: int
    timeout_s: float

    def __post_init__(self):
        _text(self.executable_evidence_id)
        path = Path(self.executable)
        if not path.is_absolute() or re.fullmatch(r"[0-9a-f]{64}", self.executable_sha256) is None:
            raise ValueError(
                "Supply the actual absolute binary path and reviewed SHA256; no discovered fallback"
            )
        if type(self.threads) is not int or self.threads < 1:
            raise ValueError("Native OpenMP thread count must be explicit")
        finite(self.timeout_s, "external native timeout", positive=True)
        object.__setattr__(self, "executable", path)


@dataclass(frozen=True, slots=True)
class CFDAuditBudgets:
    mass_kg: float
    energy_j: float
    relative: float
    clock_s: float
    geometry_m: float
    volume_m3: float
    species_fraction: float
    maximum_speed_m_s: float
    maximum_pressure_change_fraction: float
    maximum_velocity_error_m_s: float
    minimum_temperature_k: float
    maximum_temperature_k: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if max(self.relative, self.species_fraction, self.maximum_pressure_change_fraction) >= 1:
            raise ValueError("Dimensionless audit/domain budgets must be below one")
        if not 250 <= self.minimum_temperature_k < self.maximum_temperature_k <= 400:
            raise ValueError("Declare warm all-gas temperature bounds within250..400K")


@dataclass(frozen=True, slots=True)
class NativeCSV:
    columns: tuple[str, ...]
    units: tuple[str, ...]
    values: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "values", _array(self.values))

    def column(self, name, unit):
        index = self.columns.index(name)
        if self.units[index] != unit:
            raise ValueError(f"Native {name} unit is {self.units[index]!r}, expected {unit!r}")
        return self.values[:, index]


@dataclass(frozen=True, slots=True)
class NativeFDSArtifacts:
    directory: Path
    files_sha256: object

    def __post_init__(self):
        object.__setattr__(self, "files_sha256", MappingProxyType(dict(self.files_sha256)))

    @classmethod
    def capture(cls, directory):
        root = Path(directory)
        files = {
            p.relative_to(root).as_posix(): _sha(p)
            for p in root.rglob("*")
            if p.is_file() and not p.is_symlink()
        }
        return cls(root, files)

    def require_current(self):
        """Verify the complete captured native artifact tree, not just its manifest."""
        root = Path(self.directory)
        if root.is_symlink() or not root.is_dir():
            raise ValueError("Native artifact directory was removed or replaced")
        current = {}
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError("Native artifact tree cannot contain symbolic links")
            if path.is_file():
                current[path.relative_to(root).as_posix()] = _sha(path)
        if current != dict(self.files_sha256):
            raise ValueError("Native artifact file set or bytes changed after capture")
        return self

    def read_bytes(self, name):
        self.require_current()
        path = (self.directory / name).resolve()
        if (
            path.parent != self.directory
            or name not in self.files_sha256
            or _sha(path) != self.files_sha256[name]
        ):
            raise ValueError("Native artifact identity/path/content changed")
        return path.read_bytes()


@dataclass(frozen=True, slots=True)
class ObstacleDispersionResult:
    case: ObstacleDispersionCase
    engine: FDSEngine
    budgets: CFDAuditBudgets
    native_process: object
    artifacts: NativeFDSArtifacts
    native_git_text: str
    device_table: NativeCSV
    energy_table: NativeCSV
    time_s: np.ndarray
    hydrogen_mass_kg: np.ndarray
    total_mass_kg: np.ndarray
    sensible_enthalpy_j: np.ndarray
    native_integrals: np.ndarray
    residuals: np.ndarray
    receptor_hydrogen_mole_fraction: np.ndarray
    resolved_obstacles: tuple
    failures: tuple[str, ...]
    numerically_admitted: bool
    software_status: str = "implemented_unverified"
    residual_columns: tuple = (
        "hydrogen_mass_kg",
        "background_air_mass_kg",
        "source_mass_kg",
        "sensible_enthalpy_j",
        "native_enthalpy_rate_integral_j",
        "fluid_volume_m3",
    )
    _issuer: object = dataclass_field(default=None, repr=False, compare=False)
    _signature: str = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self._issuer, _ObstacleResultIssuer):
            raise TypeError("Use run_obstacle_dispersion to issue an FDS result")
        if self._issuer.owner is not None and self._issuer.owner is not self:
            raise TypeError("An FDS result issuer cannot be reused for a copied receipt")
        self._issuer.owner = self
        for name in (
            "time_s",
            "hydrogen_mass_kg",
            "total_mass_kg",
            "sensible_enthalpy_j",
            "native_integrals",
            "residuals",
            "receptor_hydrogen_mole_fraction",
        ):
            object.__setattr__(self, name, _array(getattr(self, name)))
        object.__setattr__(self, "resolved_obstacles", tuple(self.resolved_obstacles))
        object.__setattr__(self, "failures", tuple(self.failures))
        if type(self.numerically_admitted) is not bool:
            raise TypeError("Native admission status must be boolean")
        if self.numerically_admitted == bool(self.failures):
            raise ValueError("Numerical admission must agree with the retained audit failures")
        object.__setattr__(self, "_signature", _obstacle_result_signature(self))

    def require_current(self):
        """Ensure the accepted or rejected result still matches its native snapshot."""
        if (not isinstance(self._issuer, _ObstacleResultIssuer)
                or self._issuer.owner is not self
                or self._signature != _obstacle_result_signature(self)):
            raise ValueError("Native obstacle-dispersion result changed after capture")
        self.artifacts.require_current()
        return self


class ObstacleDispersionError(RuntimeError):
    def __init__(
        self, message, *, case, engine, directory, native_process=None, artifacts=None, result=None
    ):
        super().__init__(message)
        self.case, self.engine, self.directory = case, engine, directory
        self.native_process, self.artifacts, self.result = native_process, artifacts, result


def _csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = [row for row in csv.reader(stream) if row and any(v.strip() for v in row)]
    if len(rows) < 3:
        raise ValueError("Native CSV is incomplete")
    units, columns = tuple(v.strip() for v in rows[0]), tuple(v.strip() for v in rows[1])
    values = _array([[float(v.replace("D", "E")) for v in row] for row in rows[2:]])
    if (
        len(units) != len(columns)
        or len(set(columns)) != len(columns)
        or values.shape[1] != len(columns)
    ):
        raise ValueError("Native CSV headers/units/data do not match")
    return NativeCSV(columns, units, values)


def _smv_obstacles(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    sections = [i for i, line in enumerate(lines) if line.strip() == "OBST"]
    if len(sections) != 1:
        raise ValueError("Expected one actual mesh obstruction section")
    start = sections[0]
    count = int(lines[start + 1])
    result = []
    for line in lines[start + 2 : start + 2 + count]:
        coordinates, separator, label = line.partition("!")
        if not separator:
            raise ValueError("Native SMV obstruction has no retained ID")
        result.append((label.strip(), tuple(float(v) for v in coordinates.split()[:6])))
    return tuple(result)


def render_fds(case: ObstacleDispersionCase):
    """Original native deck; no native execution or copied tutorial input."""
    zone = case.mesh.connected_fluid()
    xb = _numbers(case.mesh.bounds_m)
    lines = [
        f"&HEAD CHID='{case.identifier}', TITLE='Authored obstacle dispersion' /",
        f"&MESH IJK={','.join(str(n) for n in case.mesh.cells)}, XB={xb} /",
        f"&TIME T_END={case.end_time_s:.16g}, DT={case.initial_time_step_s:.16g} /",
        f"&MISC TMPA={case.ambient_temperature_k - 273.15:.16g}, P_INF={case.ambient_pressure_pa_absolute:.16g}, "
        f"HUMIDITY=0.0, GVEC={_numbers(case.gravity_m_s2)}, NOISE=.FALSE., SIMULATION_MODE='{case.simulation_mode}' /",
        "&RADI RADIATION=.FALSE. /",
        "&SPEC ID='HYDROGEN' /",
        "&SURF ID='audit_wall', ADIABATIC=.TRUE., DEFAULT=.TRUE. /",
        f"&ZONE ID='audit_zone', XYZ={_numbers(zone)} /",
        f"&PRES VELOCITY_TOLERANCE={case.pressure_velocity_tolerance_m_s:.16g}, "
        f"MAX_PRESSURE_ITERATIONS={case.maximum_pressure_iterations} /",
        f"&DUMP DT_DEVC={case.output_interval_s:.16g}, DT_HRR={case.output_interval_s:.16g}, "
        f"DT_MASS={case.output_interval_s:.16g}, DT_SLCF={case.output_interval_s:.16g}, MASS_FILE=.TRUE., SIG_FIGS=12 /",
    ]
    for obstacle in case.mesh.obstacles:
        lines.append(
            f"&OBST ID='{obstacle.identifier}', XB={_numbers(obstacle.bounds_m)}, SURF_ID='audit_wall' /"
        )
    peak = max(case.source.mass_rate_kg_s)
    if peak > 0:
        lines.append(
            f"&SURF ID='audit_source', SPEC_ID(1)='HYDROGEN', MASS_FLUX(1)={peak / case.source.area_m2:.16g}, "
            f"RAMP_MF(1)='audit_rate', TMP_FRONT={case.source.temperature_k - 273.15:.16g}, HEAT_TRANSFER_COEFFICIENT=0.0 /"
        )
        lines.append(
            f"&VENT XB={case.mesh.bounds_m[0]:.16g},{case.mesh.bounds_m[0]:.16g},{_numbers(case.source.inlet_yz_m)}, SURF_ID='audit_source' /"
        )
        for time, rate in zip(case.source.time_s, case.source.mass_rate_kg_s, strict=True):
            lines.append(f"&RAMP ID='audit_rate', T={time:.16g}, F={rate / peak:.16g} /")
    for identifier, quantity, statistic, species in (
        ("audit_h2_mass", "DENSITY", "VOLUME INTEGRAL", True),
        ("audit_total_mass", "DENSITY", "VOLUME INTEGRAL", False),
        ("audit_hs", "SENSIBLE ENTHALPY", "VOLUME INTEGRAL", False),
        ("audit_fluid_volume", "DENSITY", "VOLUME", False),
        ("audit_ymin", "MASS FRACTION", "MIN", True),
        ("audit_ymax", "MASS FRACTION", "MAX", True),
        ("audit_max_speed", "VELOCITY", "MAX", False),
        ("audit_Tmin", "TEMPERATURE", "MIN", False),
        ("audit_Tmax", "TEMPERATURE", "MAX", False),
    ):
        extra = ", SPEC_ID='HYDROGEN'" if species else ""
        if statistic == "VOLUME":
            extra += ", QUANTITY_RANGE=0.0,1.E20"
        lines.append(
            f"&DEVC ID='{identifier}', XB={xb}, QUANTITY='{quantity}', SPATIAL_STATISTIC='{statistic}', "
            f"TEMPORAL_STATISTIC='INSTANT VALUE'{extra} /"
        )
    lines.append(
        f"&DEVC ID='audit_velocity_error', XYZ={_numbers(zone)}, QUANTITY='MAXIMUM VELOCITY ERROR', TIME_AVERAGED=.FALSE. /"
    )
    for receptor in case.receptors:
        lines.append(
            f"&DEVC ID='r_{receptor.identifier}', XYZ={_numbers(receptor.position_m)}, QUANTITY='VOLUME FRACTION', "
            "SPEC_ID='HYDROGEN', TIME_AVERAGED=.FALSE. /"
        )
    # Native binary scalar slices remain available to actual FDS/Smokeview readers.
    for axis, label in enumerate(("PBX", "PBY", "PBZ")):
        position = (case.mesh.bounds_m[2 * axis] + case.mesh.bounds_m[2 * axis + 1]) / 2
        lines.append(
            f"&SLCF {label}={position:.16g}, QUANTITY='MASS FRACTION', SPEC_ID='HYDROGEN' /"
        )
    lines.append("&TAIL /")
    return "\n".join(lines) + "\n"


def run_obstacle_dispersion(
    case: ObstacleDispersionCase, engine: FDSEngine, budgets: CFDAuditBudgets, *, work_directory
):
    """Actual optional external solve; called only in the later selected profile."""
    directory = Path(work_directory).resolve() / case.identifier
    process, artifacts, result = None, None, None
    try:
        if (
            type(case) is not ObstacleDispersionCase
            or type(engine) is not FDSEngine
            or type(budgets) is not CFDAuditBudgets
        ):
            raise TypeError("Explicit actual case/native binary/audit objects are required")
        before = _sha(engine.executable)
        if before != engine.executable_sha256:
            raise ValueError("Native executable differs from the declared binary receipt")
        deck = render_fds(case)
        directory.mkdir(parents=True, exist_ok=False)
        input_path = directory / (case.identifier + ".fds")
        input_path.write_text(deck, encoding="ascii", newline="\n")
        input_sha = _sha(input_path)
        environment = os.environ.copy()
        environment["OMP_NUM_THREADS"] = str(engine.threads)
        process = subprocess.run(
            [str(engine.executable), input_path.name],
            cwd=directory,
            env=environment,
            capture_output=True,
            check=False,
            timeout=engine.timeout_s,
        )
        (directory / "native_stdout.bin").write_bytes(process.stdout)
        (directory / "native_stderr.bin").write_bytes(process.stderr)
        artifacts = NativeFDSArtifacts.capture(directory)
        output_path = directory / (case.identifier + ".out")
        output = (
            process.stdout
            + process.stderr
            + (output_path.read_bytes() if output_path.exists() else b"")
        )
        if process.returncode != 0 or b"STOP: FDS completed successfully" not in output:
            raise ValueError("Actual FDS did not report normal completion")
        git_text = (directory / (case.identifier + "_git.txt")).read_text(encoding="utf-8").strip()
        if "FDS-" + FDS_VERSION not in git_text or FDS_REVISION[:7] not in git_text:
            raise ValueError(
                "Native compiled git/version metadata differs from the selected FDS release"
            )
        device = _csv(directory / (case.identifier + "_devc.csv"))
        energy = _csv(directory / (case.identifier + "_hrr.csv"))
        times = device.column("Time", "s")
        hrr_time = energy.column("Time", "s")
        if (
            len(times) < 2
            or np.any(np.diff(times) <= 0)
            or hrr_time.shape != times.shape
            or np.max(abs(times - hrr_time)) > budgets.clock_s
            or abs(times[0]) > budgets.clock_s
            or abs(times[-1] - case.end_time_s) > budgets.clock_s
        ):
            raise ValueError(
                "Native instantaneous-device and interval-mean energy clocks do not align over full support"
            )
        h2 = device.column("audit_h2_mass", "kg")
        total = device.column("audit_total_mass", "kg")
        enthalpy = device.column("audit_hs", "kJ") * 1000
        volume = device.column("audit_fluid_volume", "m3")
        mlr = energy.column("MLR_HYDROGEN", "kg/s")
        q_total = energy.column("Q_TOTAL", "kW") * 1000
        q_enthalpy = energy.column("Q_ENTH", "kW") * 1000
        # Native HRR/MLR columns are means over preceding print intervals.
        integral = np.vstack(
            (
                np.zeros(3),
                np.cumsum(
                    np.diff(hrr_time)[:, None] * np.column_stack((mlr, q_total, q_enthalpy))[1:],
                    axis=0,
                ),
            )
        )
        requested = np.array([case.source.integrated_mass_kg(float(t)) for t in times])
        residual = np.column_stack(
            (
                h2 - h2[0] - integral[:, 0],
                (total - h2) - (total[0] - h2[0]),
                integral[:, 0] - requested,
                enthalpy - enthalpy[0] - integral[:, 1],
                integral[:, 2] - integral[:, 1],
                volume - case.mesh.fluid_volume_m3,
            )
        )
        obstacles = _smv_obstacles(directory / (case.identifier + ".smv"))
        failures = []
        actual = {identifier: bounds for identifier, bounds in obstacles}
        if len(actual) != len(obstacles) or set(actual) != {
            o.identifier for o in case.mesh.obstacles
        }:
            failures.append("native obstacle ID/count differs from the declared geometry")
        else:
            for obstacle in case.mesh.obstacles:
                if (
                    max(
                        abs(a - b)
                        for a, b in zip(actual[obstacle.identifier], obstacle.bounds_m, strict=True)
                    )
                    > budgets.geometry_m
                ):
                    failures.append("native obstacle bounds changed/snapped")
        mass_limit = budgets.mass_kg + budgets.relative * max(
            float(np.max(abs(requested))), float(np.max(abs(h2 - h2[0])))
        )
        energy_limit = budgets.energy_j + budgets.relative * max(
            float(np.max(abs(integral[:, 1:]))), float(np.max(abs(enthalpy - enthalpy[0])))
        )
        limits = (mass_limit, mass_limit, mass_limit, energy_limit, energy_limit, budgets.volume_m3)
        for column, limit in enumerate(limits):
            if np.max(abs(residual[:, column])) > limit:
                failures.append(f"mass/enthalpy/geometry ledger column {column} exceeds {limit} SI")
        if np.min(h2) < -budgets.mass_kg or np.min(total - h2) < -budgets.mass_kg:
            failures.append("native species inventory left its nonnegative budget")
        if (
            np.min(device.column("audit_ymin", "kg/kg")) < -budgets.species_fraction
            or np.max(device.column("audit_ymax", "kg/kg")) > 1 + budgets.species_fraction
        ):
            failures.append("native H2 field fraction outside the admitted budget")
        receptors = np.column_stack(
            [device.column("r_" + r.identifier, "mol/mol") for r in case.receptors]
        )
        if (
            np.min(receptors) < -budgets.species_fraction
            or np.max(receptors) > 1 + budgets.species_fraction
        ):
            failures.append("native receptor mole fraction outside the admitted budget")
        if np.max(device.column("audit_max_speed", "m/s")) > budgets.maximum_speed_m_s:
            failures.append("native flow left the caller's low-speed applicability boundary")
        if (
            np.min(device.column("audit_Tmin", "C")) + 273.15 < budgets.minimum_temperature_k
            or np.max(device.column("audit_Tmax", "C")) + 273.15 > budgets.maximum_temperature_k
        ):
            failures.append("native field left the warm all-gas temperature domain")
        if (
            np.max(device.column("audit_velocity_error", "m/s"))
            > budgets.maximum_velocity_error_m_s
        ):
            failures.append("native obstacle/pressure-solver velocity error exceeds budget")
        pressure_columns = [
            name for name, unit in zip(energy.columns, energy.units, strict=True) if unit == "Pa"
        ]
        if pressure_columns != ["audit_zone"]:
            failures.append(
                "native pressure-zone topology differs from the connected sealed reference"
            )
        elif (
            np.max(abs(energy.column("audit_zone", "Pa"))) / case.ambient_pressure_pa_absolute
            > budgets.maximum_pressure_change_fraction
        ):
            failures.append(
                "native pressure departed from the supplied near-ambient low-Mach domain"
            )
        if (
            max(np.max(abs(energy.column("HRR", "kW"))), np.max(abs(energy.column("HRR_OX", "kW"))))
            * 1000
            > budgets.energy_j / case.end_time_s
        ):
            failures.append("unrequested native combustion/solid oxidation appeared")
        if _sha(input_path) != input_sha or _sha(engine.executable) != before:
            failures.append("native input/binary bytes changed")
        result = ObstacleDispersionResult(
            case,
            engine,
            budgets,
            process,
            artifacts,
            git_text,
            device,
            energy,
            times + case.start_time_s,
            h2,
            total,
            enthalpy,
            integral,
            residual,
            receptors,
            obstacles,
            tuple(failures),
            not failures,
            _issuer=_ObstacleResultIssuer(),
        )
        if failures:
            raise ValueError("; ".join(failures))
        return result.require_current()
    except Exception as cause:
        if artifacts is None and directory.exists():
            artifacts = NativeFDSArtifacts.capture(directory)
        if isinstance(cause, subprocess.TimeoutExpired):
            process = cause
        raise ObstacleDispersionError(
            f"Unverified actual obstacle CFD rejected: {cause}",
            case=case,
            engine=engine,
            directory=directory,
            native_process=process,
            artifacts=artifacts,
            result=result,
        ) from cause
