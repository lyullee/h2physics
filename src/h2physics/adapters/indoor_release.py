"""HyRAM+ indoor accumulation and ignition-delay-dependent peak pressure.

The separately installed HyRAM+ engine owns layering and combustion. A point
on the returned pressure curve is the peak for ignition at that release age;
it is never a pressure-time waveform after ignition. Native technical reference:
https://www.osti.gov/servlets/purl/2563814 . No native equations are copied here.
"""

import importlib
import importlib.metadata
from dataclasses import dataclass, field
from hashlib import sha256

import numpy as np

from ..core import finite, immutable_array


def _label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty identity")


@dataclass(frozen=True, slots=True)
class IndoorVent:
    area_m2: float
    height_m: float
    discharge_coefficient: float = 1.0
    imposed_volume_flow_m3_s: float = 0.0

    def __post_init__(self):
        for name in ("area_m2", "height_m", "imposed_volume_flow_m3_s"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if not 0 < finite(self.discharge_coefficient, "discharge coefficient") <= 1:
            raise ValueError("Discharge coefficient must lie in (0, 1]")


@dataclass(frozen=True, slots=True)
class IndoorEnclosure:
    height_m: float
    floor_area_m2: float
    release_height_m: float
    release_to_wall_m: float
    ceiling_vent: IndoorVent
    floor_vent: IndoorVent
    geometry_evidence_id: str

    def __post_init__(self):
        for name in ("height_m", "floor_area_m2", "release_to_wall_m"):
            finite(getattr(self, name), name, positive=True)
        if not 0 <= finite(self.release_height_m, "release height") < self.height_m:
            raise ValueError("Release height must be within the enclosure")
        for vent in (self.floor_vent, self.ceiling_vent):
            if not isinstance(vent, IndoorVent):
                raise TypeError("Use an IndoorVent boundary")
            if vent.height_m > self.height_m:
                raise ValueError("Vent height exceeds enclosure height")
        if self.floor_vent.height_m >= self.ceiling_vent.height_m:
            raise ValueError("Floor vent must be below ceiling vent")
        _label(self.geometry_evidence_id, "geometry evidence")


@dataclass(frozen=True, slots=True)
class IndoorHydrogenSource:
    pressure_pa_absolute: float
    temperature_k: float
    vessel_volume_m3: float
    orifice_diameter_m: float
    source_id: str
    boundary_evidence_id: str
    discharge_coefficient: float = 1.0

    def __post_init__(self):
        for name in ("pressure_pa_absolute", "temperature_k", "vessel_volume_m3",
                     "orifice_diameter_m"):
            finite(getattr(self, name), name, positive=True)
        if not 0 < finite(self.discharge_coefficient, "discharge coefficient") <= 1:
            raise ValueError("Discharge coefficient must lie in (0, 1]")
        _label(self.source_id, "source ID")
        _label(self.boundary_evidence_id, "boundary evidence")


@dataclass(frozen=True, slots=True)
class IndoorReleaseSettings:
    duration_s: float
    clock_id: str
    source_start_time_s: float = 0.0
    ambient_pressure_pa_absolute: float = 101325.0
    ambient_temperature_k: float = 293.15
    steady_source: bool = False
    blowdown_steps: int = 100
    steady_steps: int = 5
    jet_relative_tolerance: float = 1e-5
    jet_max_steps: int = 100000
    release_angle_rad: float = 0.0

    def __post_init__(self):
        for name in ("duration_s", "ambient_pressure_pa_absolute", "ambient_temperature_k",
                     "jet_relative_tolerance"):
            finite(getattr(self, name), name, positive=True)
        finite(self.source_start_time_s, "source start time")
        finite(self.release_angle_rad, "release angle")
        if not -np.pi / 2 <= self.release_angle_rad <= np.pi / 2:
            raise ValueError("Declare a release angle between -pi/2 and pi/2")
        if type(self.steady_source) is not bool:
            raise TypeError("steady_source must be a bool")
        for name in ("blowdown_steps", "steady_steps", "jet_max_steps"):
            value = getattr(self, name)
            if type(value) is not int or value < 2:
                raise ValueError(f"{name} must be an integer at least two")
        _label(self.clock_id, "clock ID")


_NATIVE_FIELDS = ("t_layer", "x_layer", "H_layer", "dP_tot", "m_jet", "m_layer")
_ISSUERS = set()


def _native_digest(native):
    digest = sha256()
    for name in _NATIVE_FIELDS:
        values = np.asarray(getattr(native, name), dtype=float)
        digest.update(name.encode())
        digest.update(repr(values.shape).encode())
        digest.update(values.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class IndoorIgnitionDelayPeaks:
    """Snapshots indexed by release age, not by time since explosion.

    ``peak_overpressure_pa_gauge`` is the native conditional enclosure peak.
    Native ``x_layer`` is already a mole fraction; its convenience method
    ``concentration`` uses percent, and is deliberately not used here.
    """

    source: IndoorHydrogenSource
    enclosure: IndoorEnclosure
    settings: IndoorReleaseSettings
    native_version: str
    native: object = field(repr=False, compare=False)
    ignition_delay_s: np.ndarray
    layer_hydrogen_mole_fraction: np.ndarray
    layer_depth_m: np.ndarray
    peak_overpressure_pa_gauge: np.ndarray
    flammable_jet_hydrogen_mass_kg: np.ndarray
    flammable_layer_hydrogen_mass_kg: np.ndarray
    _issuer: object = field(repr=False, compare=False)
    _native_seal: str = field(default="", init=False, repr=False, compare=False)
    axis_kind: str = field(default="release_age_at_hypothetical_ignition", init=False)

    def __post_init__(self):
        if self._issuer not in _ISSUERS:
            raise ValueError("Indoor peak snapshots are issued by the native run function")
        _ISSUERS.remove(self._issuer)
        names = ("ignition_delay_s", "layer_hydrogen_mole_fraction", "layer_depth_m",
                 "peak_overpressure_pa_gauge", "flammable_jet_hydrogen_mass_kg",
                 "flammable_layer_hydrogen_mass_kg")
        for name, native_name in zip(names, _NATIVE_FIELDS, strict=True):
            values = np.asarray(getattr(self, name), dtype=float)
            if values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values)):
                raise ValueError(f"Native {name} must be a finite one-dimensional history")
            if not np.array_equal(values, getattr(self.native, native_name)):
                raise ValueError("Snapshot differs from actual native output")
            object.__setattr__(self, name, immutable_array(values, name=name))
        if len({len(getattr(self, name)) for name in names}) != 1:
            raise ValueError("Native accumulation arrays have inconsistent lengths")
        if self.ignition_delay_s[0] < 0 or np.any(np.diff(self.ignition_delay_s) <= 0):
            raise ValueError("Native release age must be nonnegative and strictly increasing")
        if np.any((self.layer_hydrogen_mole_fraction < 0) |
                  (self.layer_hydrogen_mole_fraction > 1)):
            raise ValueError("Native layer mole fraction is outside [0, 1]")
        if np.any(self.layer_depth_m < 0) or np.any(self.layer_depth_m > self.enclosure.height_m):
            raise ValueError("Native layer lies outside the enclosure")
        for name in names[3:]:
            if np.any(getattr(self, name) < 0):
                raise ValueError(f"Native {name} cannot be negative")
        object.__setattr__(self, "_native_seal", _native_digest(self.native))

    def require_current(self):
        if self._native_seal != _native_digest(self.native):
            raise ValueError("Retained native accumulation output changed after capture")
        return self

    @property
    def ignition_clock_time_s(self):
        return immutable_array(self.ignition_delay_s + self.settings.source_start_time_s)

    @property
    def conditional_peak_pressure_pa_absolute(self):
        return immutable_array(self.peak_overpressure_pa_gauge +
                               self.settings.ambient_pressure_pa_absolute)


def run_hyram_indoor_release(source: IndoorHydrogenSource, enclosure: IndoorEnclosure,
                             settings: IndoorReleaseSettings) -> IndoorIgnitionDelayPeaks:
    """Run actual separately installed HyRAM+ 6.1 with native CoolProp properties.

    A steady source prescribes constant upstream conditions; its vessel volume
    does not impose a finite depletion limit. Blowdown uses native finite stock.
    No alternate model is used when import, native solving or admission fails.
    """
    if not isinstance(source, IndoorHydrogenSource) or not isinstance(enclosure, IndoorEnclosure):
        raise TypeError("Supply typed hydrogen-source and enclosure boundaries")
    if not isinstance(settings, IndoorReleaseSettings):
        raise TypeError("Supply IndoorReleaseSettings")
    if source.pressure_pa_absolute <= settings.ambient_pressure_pa_absolute:
        raise ValueError("Source absolute pressure must exceed ambient")
    phys = importlib.import_module("hyram.phys")
    version = importlib.metadata.version("hyram")
    if version != "6.1":
        raise ValueError(f"Indoor adapter inspected for HyRAM 6.1; found {version}")
    native_class = importlib.import_module("hyram.phys._indoor_release").IndoorRelease
    if phys.IndoorRelease is not native_class:
        raise TypeError("HyRAM IndoorRelease is not its installed native class")
    fuel = phys.Fluid(species="H2", T=source.temperature_k, P=source.pressure_pa_absolute)
    ambient = phys.Fluid(species="air", T=settings.ambient_temperature_k,
                         P=settings.ambient_pressure_pa_absolute)
    for fluid in (fuel, ambient):
        if fluid.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Indoor gas-release route requires single-gas source and ambient states")
    native_vents = [phys.Vent(v.area_m2, v.height_m, v.discharge_coefficient,
                              v.imposed_volume_flow_m3_s)
                    for v in (enclosure.ceiling_vent, enclosure.floor_vent)]
    room = phys.Enclosure(enclosure.height_m, enclosure.floor_area_m2,
                          enclosure.release_height_m, *native_vents,
                          Xwall=enclosure.release_to_wall_m)
    native = native_class(
        phys.Source(source.vessel_volume_m3, fuel),
        phys.Orifice(source.orifice_diameter_m, source.discharge_coefficient), ambient, room,
        tmax=settings.duration_s, steady=settings.steady_source,
        nmax=settings.blowdown_steps, nsteady=settings.steady_steps,
        tol=settings.jet_relative_tolerance, max_steps=settings.jet_max_steps,
        theta0=settings.release_angle_rad, y0=enclosure.release_height_m)
    issuer = object()
    _ISSUERS.add(issuer)
    try:
        return IndoorIgnitionDelayPeaks(
            source, enclosure, settings, version, native,
            *(getattr(native, name) for name in _NATIVE_FIELDS), _issuer=issuer)
    finally:
        _ISSUERS.discard(issuer)
