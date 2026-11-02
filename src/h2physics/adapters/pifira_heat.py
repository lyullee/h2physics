"""Native pressure-rise contents heat and explicitly conditional effective area.

The optional MIT pifira package owns the pressure-energy and angular-fit models.
The host guards physical scope, references, observations and returned quantities.
"""

import math
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

from ..core import immutable_array, Origin, ThermoState, TimeSeries, finite


_PENDING_EFFECTIVE_AREA_ISSUERS: set[object] = set()


def _effective_area_signature(result) -> str:
    module = result.native_module
    native = (
        id(module), getattr(module, "__name__", None), getattr(module, "__version__", None),
        id(getattr(module, "effective_arc", None)),
        id(getattr(module, "radiative_driving_force", None)),
        id(getattr(module, "effective_height", None)),
        id(getattr(module, "effective_area", None)),
    )
    payload = (
        native, tuple(sorted(dict(result.native_fit).items())), result.evidence,
        result.area_m2, result.height_m, result.diameter_m,
        result.normalized_fit_error, result.fitted_amplitude_k4,
        result.angles_deg.dtype.str, result.angles_deg.shape, result.angles_deg.tobytes(),
        result.wall_temperature_k.dtype.str, result.wall_temperature_k.shape,
        result.wall_temperature_k.tobytes(), result.ambient_temperature_k,
        result.axial_geometry, result.maximum_normalized_fit_error,
        result.minimum_tail_sigma,
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _issue_effective_area(**values):
    token = object()
    _PENDING_EFFECTIVE_AREA_ISSUERS.add(token)
    try:
        return EffectiveAreaResult(**values, _issuer_token=token)
    except Exception:
        _PENDING_EFFECTIVE_AREA_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class ClosedHeatEvidence:
    source_id: str
    constant_mass_evidence_id: str
    rigid_volume_evidence_id: str
    phase_equilibrium_evidence_id: str
    energy_scope_id: str
    origin: Origin

    def __post_init__(self):
        for key in ("source_id", "constant_mass_evidence_id", "rigid_volume_evidence_id",
                    "phase_equilibrium_evidence_id", "energy_scope_id"):
            if not getattr(self, key).strip():
                raise ValueError("Closed contents heat needs explicit mass/volume/equilibrium/energy evidence")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("The declared closed-heat input origin must be resolved")


@dataclass(frozen=True, slots=True)
class ClosedHeatDomain:
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_quality: float = 1e-8
    maximum_quality: float = 1.-1e-8
    absolute_energy_tolerance_j: float = 1e-4
    relative_energy_tolerance: float = 1e-8

    def __post_init__(self):
        finite(self.minimum_pressure_pa, "minimum pressure", positive=True)
        if finite(self.maximum_pressure_pa, "maximum pressure") <= self.minimum_pressure_pa:
            raise ValueError("Pressure domain must increase")
        if not 0 <= self.minimum_quality < self.maximum_quality <= 1:
            raise ValueError("Declare a finite two-phase quality domain")
        for key in ("absolute_energy_tolerance_j", "relative_energy_tolerance"):
            finite(getattr(self, key), key, positive=True)


@dataclass(frozen=True, slots=True)
class ContentsHeatTrace:
    native_module: object
    native_tank: object
    properties: object
    evidence: ClosedHeatEvidence
    pressure_history: TimeSeries
    pressure_channel: str
    mass_kg: float
    mass_evidence_id: str
    states: tuple[ThermoState, ...]
    native_energy_j: np.ndarray
    native_minus_eos_energy_j: np.ndarray
    interval_heat_w: np.ndarray
    interval_energy_residual_j: np.ndarray
    native_gauge_zero_pa: float
    interpretation: str = "signed-fluid-internal-energy-increase; wall/fire/other-energy scope separate"

    def __post_init__(self):
        for key in ("native_energy_j", "native_minus_eos_energy_j", "interval_heat_w",
                    "interval_energy_residual_j"):
            a = np.array(getattr(self, key), dtype=float, copy=True)
            a = immutable_array(a, name="a")
            object.__setattr__(self, key, a)


class PifiraClosedVesselHeat:
    """Fixed-mass/volume equilibrium contents U change through actual native APIs.

    Pressure is absolute SI. The native gauge zero is only a reversible API unit
    conversion; it is never an inferred measured atmosphere. No wall storage,
    external work, inlet/outlet or spin-conversion energy is inferred.
    """

    def __init__(self, native_module, native_tank, properties, *,
                 evidence: ClosedHeatEvidence, domain: ClosedHeatDomain):
        if native_module.__name__ != "pifira" or native_module.__version__ != "0.3.0":
            raise ValueError("This adapter is checked with actual native pifira0.3.0")
        if not isinstance(native_tank, native_module.TankSpec):
            raise ValueError("Supply an actual native TankSpec")
        finite(native_tank.volume, "native tank volume", positive=True)
        if not 0 < finite(native_tank.fill, "native liquid volume fill") < 1:
            raise ValueError("The declared native initial fill must be strictly two-phase")
        if native_tank.fluid != "HEOS::"+properties.basis.fluid:
            raise ValueError("Declare the same explicit pure HEOS fluid/spin in both native providers")
        if getattr(properties, "backend", None) != "HEOS":
            raise ValueError("The independent reference must use direct HEOS")
        self.native, self.tank, self.properties = native_module, native_tank, properties
        self.evidence, self.domain = evidence, domain
        self._tank_definition = (native_tank.volume, native_tank.fluid, native_tank.fill)
        self._basis = properties.basis
        self._zero = finite(native_module.pressure_rise.P_ATM_BAR,
                            "native gauge zero", positive=True)*1e5

    def _require_definition(self):
        if (self.tank.volume, self.tank.fluid, self.tank.fill) != self._tank_definition:
            raise ValueError("The native tank definition changed after construction")
        self._basis.require_compatible(self.properties.basis)
        if self.native.pressure_rise.P_ATM_BAR*1e5 != self._zero:
            raise ValueError("The native gauge API reference changed")

    def _gauge(self, pressure_pa):
        p = finite(pressure_pa, "absolute pressure", positive=True)
        if not self.domain.minimum_pressure_pa <= p <= self.domain.maximum_pressure_pa:
            raise ValueError("Pressure lies outside the declared closed-heat domain")
        return (p-self._zero)/1e5

    def derive_initial_mass(self, pressure_pa: float) -> float:
        """Explicitly request native mass from the stated initial liquid volume fill."""
        self._require_definition()
        return finite(self.native.TankSpec.initial_mass(self.tank, self._gauge(pressure_pa)),
                      "native derived initial mass", positive=True)

    def run(self, pressure: TimeSeries, channel: str, *, mass_kg: float,
            mass_evidence_id: str) -> ContentsHeatTrace:
        self._require_definition()
        mass = finite(mass_kg, "fixed total mass", positive=True)
        if not mass_evidence_id.strip():
            raise ValueError("Fixed mass needs a source/evidence identity")
        values, valid = pressure.channel_values(channel, quantity="pressure")
        index = pressure.channels.index(channel)
        if (pressure.units[index] != "Pa" or not pressure.basis_ids
                or pressure.basis_ids[index] != "absolute"):
            raise ValueError("The selected pressure channel must explicitly be Pa absolute")
        if pressure.origin == Origin.UNRESOLVED or not np.all(valid) or len(values) < 2:
            raise ValueError("Closed-heat inversion requires resolved complete pressure observations")
        if pressure.source_id != self.evidence.source_id:
            raise ValueError("Pressure and closed-boundary evidence source identities differ")
        states, energies, errors, gauge = [], [], [], []
        density = mass/self.tank.volume
        for p in values:
            g = self._gauge(p)
            state = self.properties.state_prho(float(p), density)
            self._basis.require_compatible(state.basis)
            q = state.vapor_mass_fraction
            if (state.phase != "two_phase" or q is None or state.raw_vapor_mass_fraction is not None
                    or not self.domain.minimum_quality <= q <= self.domain.maximum_quality):
                raise ValueError("Fixed mass/volume state has left the declared two-phase domain")
            native_u = finite(self.native.internal_energy(g, mass, self.tank), "native contents U")
            eos_u = mass*state.internal_energy_j_kg
            error = native_u-eos_u
            budget = self.domain.absolute_energy_tolerance_j+self.domain.relative_energy_tolerance*max(
                abs(native_u), abs(eos_u))
            if abs(error) > budget:
                raise ValueError("Native/EOS contents energy or reference mismatch")
            states.append(state)
            energies.append(native_u)
            errors.append(error)
            gauge.append(g)
        heat = np.array([finite(self.native.heat_input(gauge[i], gauge[i+1], float(dt),
            self.tank, m_tot=mass), "native signed contents heat")
            for i, dt in enumerate(np.diff(pressure.time_s))])
        residual = heat*np.diff(pressure.time_s)-np.diff(energies)
        if np.max(abs(residual)) > self.domain.absolute_energy_tolerance_j:
            raise ValueError("Native heat intervals do not close native contents energy")
        self._require_definition()
        return ContentsHeatTrace(self.native, self.tank, self.properties, self.evidence,
            pressure, channel, mass, mass_evidence_id, tuple(states), energies, errors,
            heat, residual, self._zero)


@dataclass(frozen=True, slots=True)
class EffectiveAreaEvidence:
    source_id: str
    clock_id: str
    start_s: float
    end_s: float
    flame_centre_evidence_id: str
    radiation_shape_evidence_id: str
    axial_wetted_scope_id: str
    temperature_statistic: str
    origin: Origin

    def __post_init__(self):
        if any(not getattr(self, k).strip() for k in ("source_id", "clock_id",
            "flame_centre_evidence_id", "radiation_shape_evidence_id", "axial_wetted_scope_id")):
            raise ValueError("Angular inversion needs explicit shape/geometry/clock evidence")
        if finite(self.end_s, "area end") <= finite(self.start_s, "area start"):
            raise ValueError("Area observation support must increase")
        if self.temperature_statistic not in {"instantaneous", "fourth-power-equivalent"}:
            raise ValueError("Ordinary mean temperatures do not establish mean T^4 driving force")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Angular observation origin must be resolved")


@dataclass(frozen=True, slots=True)
class AxialContactGeometry:
    flame_start_m: float
    flame_end_m: float
    wetted_start_m: float
    wetted_end_m: float
    axis_frame_id: str

    def __post_init__(self):
        for key in ("flame_start_m", "flame_end_m", "wetted_start_m", "wetted_end_m"):
            finite(getattr(self, key), key)
        if (self.flame_end_m <= self.flame_start_m or self.wetted_end_m <= self.wetted_start_m
                or not self.axis_frame_id.strip()):
            raise ValueError("Declare positive axial intervals on one explicit common coordinate frame")


@dataclass(frozen=True, slots=True)
class EffectiveAreaResult:
    native_module: object
    native_fit: Mapping
    evidence: EffectiveAreaEvidence
    area_m2: float
    height_m: float
    diameter_m: float
    normalized_fit_error: float
    fitted_amplitude_k4: float
    angles_deg: np.ndarray
    wall_temperature_k: np.ndarray
    ambient_temperature_k: float
    axial_geometry: AxialContactGeometry
    maximum_normalized_fit_error: float
    minimum_tail_sigma: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_EFFECTIVE_AREA_ISSUERS:
            raise ValueError("Effective-area results are issued only by the native fit adapter")
        _PENDING_EFFECTIVE_AREA_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "native_fit", MappingProxyType(dict(self.native_fit)))
        for key in ("angles_deg", "wall_temperature_k"):
            a = np.array(getattr(self, key), dtype=float, copy=True)
            a = immutable_array(a, name="a")
            object.__setattr__(self, key, a)
        object.__setattr__(self, "_seal", _effective_area_signature(self))

    def require_current(self):
        if self._effective_seal() != self._seal:
            raise ValueError("Effective-area native result or admitted geometry changed")
        return self

    def _effective_seal(self):
        return _effective_area_signature(self)


def pifira_effective_area(native_module, *, angles_deg, wall_temperature_k,
        ambient_temperature_k: float, diameter_m: float, axial_geometry: AxialContactGeometry,
        evidence: EffectiveAreaEvidence,
        maximum_normalized_fit_error: float, minimum_tail_sigma: float = 2.5) -> EffectiveAreaResult:
    """Conditional centered local Gaussian equivalent area through native fitting.

    This geometry is an inverse interpretation of declared wall observations,
    not a predictive fire footprint or an incident heat-flux measurement.
    """
    if native_module.__name__ != "pifira" or native_module.__version__ != "0.3.0":
        raise ValueError("Supply the reviewed actual native pifira0.3.0")
    theta, temperatures = np.asarray(angles_deg, float), np.asarray(wall_temperature_k, float)
    if (theta.ndim != 1 or temperatures.shape != theta.shape or len(theta) < 5
            or not np.all(np.isfinite(theta)) or not np.all(np.isfinite(temperatures))
            or len(np.unique(theta)) != len(theta) or np.min(theta) < -180 or np.max(theta) >= 180
            or not np.any(theta == 0.) or not np.any(theta < 0) or not np.any(theta > 0)):
        raise ValueError("Provide distinct centered wall angles in [-180,180), with both tails and >=5 sensors")
    ambient = finite(ambient_temperature_k, "ambient absolute temperature", positive=True)
    if np.any(temperatures < ambient) or np.max(temperatures) <= ambient:
        raise ValueError("This positive radiation-shape fit requires wall T>=ambient and some positive drive")
    finite(diameter_m, "diameter", positive=True)
    fit_budget = finite(maximum_normalized_fit_error, "fit error budget", positive=True)
    tail = finite(minimum_tail_sigma, "tail coverage", positive=True)
    native_fit = native_module.effective_arc(theta, temperatures-273.15, T_amb_C=ambient-273.15)
    sigma = finite(native_fit["sigma"], "native angular sigma", positive=True)
    arc = finite(native_fit["arc_deg"], "native angular arc", positive=True)
    if arc > 360. or min(-np.min(theta), np.max(theta)) < tail*sigma:
        raise ValueError("Native angular fit exceeds circumference or declared tail coverage")
    # Independent residual audit of the selected native centered-Gaussian model.
    # No second optimizer, temperature fit or replacement area is introduced.
    drive = native_module.radiative_driving_force(temperatures-273.15, ambient-273.15)
    weights = np.exp(-.5*(theta/sigma)**2)
    amplitude = float(np.dot(weights, drive)/np.dot(weights, weights))
    error = float(np.sqrt(np.mean((drive-amplitude*weights)**2))/max(drive))
    if not math.isfinite(error) or error > fit_budget:
        raise ValueError("Native angular radiation-shape fit fails the declared residual budget")
    # Translate both supplied intervals to their common overlap start before
    # delegating native min-height. Unequal lower coordinates are not discarded.
    g = axial_geometry
    lower = max(g.flame_start_m, g.wetted_start_m)
    remaining = (g.flame_end_m-lower, g.wetted_end_m-lower)
    height = (finite(native_module.effective_height(*remaining), "native overlap height", positive=True)
              if min(remaining) > 0. else 0.)
    area = finite(native_module.effective_area(diameter_m, arc, height), "native effective area")
    if area < 0:
        raise ValueError("Native effective area cannot be negative")
    return _issue_effective_area(
        native_module=native_module, native_fit=native_fit, evidence=evidence,
        area_m2=area, height_m=height, diameter_m=diameter_m,
        normalized_fit_error=error, fitted_amplitude_k4=amplitude,
        angles_deg=theta, wall_temperature_k=temperatures,
        ambient_temperature_k=ambient, axial_geometry=g,
        maximum_normalized_fit_error=fit_budget, minimum_tail_sigma=tail,
    )


@dataclass(frozen=True, slots=True)
class ContentsEquivalentFlux:
    heat_trace: ContentsHeatTrace
    interval: int
    area: EffectiveAreaResult
    allocation_evidence_id: str
    flux_w_m2: float


def contents_equivalent_heat_flux(trace: ContentsHeatTrace, interval: int,
                                 area: EffectiveAreaResult, *, allocation_evidence_id: str
                                 ) -> ContentsEquivalentFlux:
    """W/m2 equivalent contents-energy rate over a matched explicit area interval.

    This is not incident fire flux without separate wall/loss/work allocation.
    """
    if type(area) is not EffectiveAreaResult:
        raise TypeError("Use an actual native-issued PIFIRA effective-area result")
    area.require_current()
    if not allocation_evidence_id.strip():
        raise ValueError("Contents energy/area allocation needs an explicit evidence identity")
    if area.area_m2 <= 0:
        raise ValueError("A zero axial overlap has no finite area-based heat flux")
    if isinstance(interval, bool) or not isinstance(interval, int) or not 0 <= interval < len(trace.interval_heat_w):
        raise ValueError("Choose an existing contents heat interval")
    e = area.evidence
    if (e.clock_id != trace.pressure_history.clock_id or e.source_id != trace.evidence.source_id
            or e.start_s != trace.pressure_history.time_s[interval]
            or e.end_s != trace.pressure_history.time_s[interval+1]):
        raise ValueError("Area and heat source/clock/interval identities must match explicitly")
    flux = finite(trace.native_module.heat_flux(trace.interval_heat_w[interval], area.area_m2)*1000.,
                  "native equivalent contents heat flux")
    return ContentsEquivalentFlux(trace, interval, area, allocation_evidence_id, flux)
