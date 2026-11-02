"""Closed-charge, moving-volume hydrogen cylinder interval using Cantera.

This is a homogeneous ideal-gas cylinder segment, not a complete engine. Cantera
owns the chemistry, thermodynamics and time integration. A native moving Wall
drives the prescribed slider-crank volume between caller-selected crank angles.
The local model does not add a spark, flame-propagation, valve, injector,
temperature-driven wall-heat transfer or cycle-convergence model. A caller may
provide an explicit imposed piston-face heat-flux schedule.
"""

from dataclasses import dataclass, field

import numpy as np

from ..adapters.cantera import MechanismBasis, ReactiveState
from ..core import finite

_PENDING_TRACE_ISSUERS: set[object] = set()


def _issue_trace_token():
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    return token


def _readonly(array):
    raw = np.asarray(array)
    if raw.dtype.kind not in "iuf":
        raise ValueError("Engine result histories require typed numeric arrays")
    value = np.array(raw, dtype=float, copy=True)
    # A readonly flag on an owning ndarray can be reversed by its recipient.
    # Immutable bytes backing makes the read-only promise enforceable.
    return np.frombuffer(value.tobytes(order="C"), dtype=np.float64).reshape(value.shape)


def _numeric_angles(value):
    """Reject text/object/bool angle arrays before numeric conversion."""
    if isinstance(value, (str, bytes, bytearray)):
        raise ValueError("Crank angles must be numeric values, not text")
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf" or raw.size == 0:
        raise ValueError("Crank angles must be a nonempty integer or floating-point array")
    result = np.asarray(raw, dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError("Crank angles must be finite")
    return result


def _advance_native(network, target_s):
    """Isolate native stepping so deferred failure-prefix checks can inject faults."""
    network.advance(float(target_s))


def _schedule_energy_j(schedule, end_absolute_time_s, area_m2):
    """Integrate a piecewise-linear flux schedule exactly over its support prefix."""
    end = finite(end_absolute_time_s, "scheduled piston heat end time")
    start = schedule.clock_origin_s
    if end < start:
        raise ValueError("Scheduled piston heat end precedes its absolute clock origin")
    lo, hi = schedule.support_s
    if start < lo or end > hi:
        raise ValueError("Piston heat-flux schedule must cover the complete engine interval")
    knots = [start, *(float(value) for value in schedule.time_s if start < value < end), end]
    times = np.asarray(knots, dtype=float)
    rates = np.asarray(schedule.at(times), dtype=float) * area_m2
    return float(np.sum(np.diff(times) * (rates[:-1] + rates[1:]) * .5))


@dataclass(frozen=True, slots=True)
class EngineBoundarySchedule:
    """Source-bound scalar input history on an explicit absolute clock.

    This is schedule bookkeeping only: it does not define a valve, injector,
    spark, heat-transfer, or flow law. Values are interpolated linearly at
    requested absolute clock times, with extrapolation rejected.
    """

    quantity: str
    units: str
    source_id: str
    clock_origin_s: float
    time_s: np.ndarray
    values: np.ndarray
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        for name in ("quantity", "units", "source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Engine schedule {name} must be a nonblank string")
            object.__setattr__(self, name, value.strip())
        origin = finite(self.clock_origin_s, "schedule absolute clock origin")
        times = _readonly(self.time_s)
        values = _readonly(self.values)
        if times.ndim != 1 or values.ndim != 1 or len(times) < 2 or len(times) != len(values):
            raise ValueError("Schedule times and values must be equal-length vectors with at least two points")
        if not np.all(np.isfinite(times)) or not np.all(np.isfinite(values)):
            raise ValueError("Schedule times and values must be finite")
        if np.any(np.diff(times) <= 0):
            raise ValueError("Schedule absolute times must increase strictly")
        if times[0] < origin:
            raise ValueError("Schedule support cannot begin before its declared clock origin")
        object.__setattr__(self, "clock_origin_s", origin)
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "_seal", self._current_content())

    def _current_content(self):
        return (self.quantity, self.units, self.source_id, self.clock_origin_s,
                self.time_s.shape, self.time_s.tobytes(order="C"),
                self.values.shape, self.values.tobytes(order="C"))

    def require_current(self):
        """Reject relabeled or replaced schedule content before downstream use."""
        if not self._seal or self._current_content() != self._seal:
            raise ValueError("Engine boundary schedule changed after source admission")
        return self

    @property
    def support_s(self):
        """Inclusive absolute-time support bounds."""
        self.require_current()
        return float(self.time_s[0]), float(self.time_s[-1])

    def at(self, absolute_time_s):
        """Return linearly interpolated values; reject requests outside support."""
        self.require_current()
        query = np.asarray(absolute_time_s)
        if query.dtype.kind not in "iuf" or not np.all(np.isfinite(query)):
            raise ValueError("Schedule query times must be finite numeric values")
        if np.any(query < self.time_s[0]) or np.any(query > self.time_s[-1]):
            raise ValueError("Schedule query lies outside the declared support")
        return np.interp(query, self.time_s, self.values)


@dataclass(frozen=True, slots=True)
class SliderCrank:
    """Single-cylinder geometry and constant-speed crank timing in SI units."""

    bore_m: float
    stroke_m: float
    connecting_rod_m: float
    compression_ratio: float
    speed_rpm: float

    def __post_init__(self):
        for name in ("bore_m", "stroke_m", "connecting_rod_m", "speed_rpm"):
            finite(getattr(self, name), name.replace("_", " "), positive=True)
        ratio = finite(self.compression_ratio, "compression ratio", positive=True)
        if ratio <= 1:
            raise ValueError("Compression ratio must exceed one")
        if self.connecting_rod_m < self.stroke_m / 2:
            raise ValueError("Connecting rod must be at least the crank radius")

    @property
    def piston_area_m2(self):
        return np.pi * self.bore_m**2 / 4

    @property
    def clearance_volume_m3(self):
        swept = self.piston_area_m2 * self.stroke_m
        return swept / (self.compression_ratio - 1)

    def volume_m3(self, crank_angle_rad):
        theta = _numeric_angles(crank_angle_rad)
        radius = self.stroke_m / 2
        rod = self.connecting_rod_m
        root = np.sqrt(rod**2 - (radius * np.sin(theta))**2)
        displacement = radius * (1 - np.cos(theta)) + rod - root
        return self.clearance_volume_m3 + self.piston_area_m2 * displacement

    def volume_rate_m3_s(self, crank_angle_rad):
        theta = _numeric_angles(crank_angle_rad)
        radius = self.stroke_m / 2
        rod = self.connecting_rod_m
        root = np.sqrt(rod**2 - (radius * np.sin(theta))**2)
        dx_dtheta = radius * np.sin(theta) + (
            radius**2 * np.sin(theta) * np.cos(theta) / root
        )
        omega = 2 * np.pi * self.speed_rpm / 60
        return self.piston_area_m2 * dx_dtheta * omega


def engine_schedule_from_crank_angle(
    *, quantity: str, units: str, source_id: str, clock_origin_s: float,
    crank_angle_rad, values, geometry: SliderCrank, crank_start_rad: float,
) -> EngineBoundarySchedule:
    """Convert an exact crank-angle schedule to the engine's absolute time base.

    This is a coordinate conversion only. It does not turn the scheduled values
    into valve area, mass flow, injector delivery, spark energy or heat transfer.
    The engine is assumed to run at the geometry's constant declared speed.
    """
    if type(geometry) is not SliderCrank:
        raise TypeError("Crank-angle schedule conversion requires SliderCrank geometry")
    start = finite(crank_start_rad, "schedule crank start")
    origin = finite(clock_origin_s, "schedule absolute clock origin")
    angles = _numeric_angles(crank_angle_rad)
    scheduled_values = _numeric_angles(values)
    if angles.ndim != 1 or scheduled_values.ndim != 1 or angles.shape != scheduled_values.shape:
        raise ValueError("Crank-angle schedule coordinates and values must be equal-length vectors")
    if len(angles) < 2 or np.any(np.diff(angles) <= 0):
        raise ValueError("Crank-angle schedule requires at least two strictly increasing samples")
    if start < 0 or start >= 4 * np.pi or angles[0] < start or angles[-1] > 4 * np.pi:
        raise ValueError("Crank schedule must lie within the forward four-stroke interval")
    omega = 2 * np.pi * geometry.speed_rpm / 60
    absolute_times = origin + (angles - start) / omega
    return EngineBoundarySchedule(
        quantity=quantity, units=units, source_id=source_id,
        clock_origin_s=origin, time_s=absolute_times, values=scheduled_values,
    )


@dataclass(frozen=True, slots=True)
class ClosedChargeEngineTrace:
    """Native-state history and sampled first-law diagnostics for one interval."""

    crank_angle_rad: np.ndarray
    time_s: np.ndarray
    volume_m3: np.ndarray
    pressure_pa: np.ndarray
    temperature_k: np.ndarray
    mass_kg: np.ndarray
    internal_energy_j: np.ndarray
    species_names: tuple[str, ...]
    mass_fractions: np.ndarray
    indicated_boundary_work_j: float
    first_law_residual_j: float
    native_reactor: object
    native_network: object
    _issuer_token: object = field(repr=False, compare=False)
    native_piston_wall: object = field(default=None, repr=False, compare=False)
    piston_heat_flux_schedule: EngineBoundarySchedule | None = None
    piston_heat_area_m2: float | None = None
    piston_heat_input_j: np.ndarray | None = None

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRACE_ISSUERS:
            raise TypeError("Create engine traces through a completed native Cantera run")
        _PENDING_TRACE_ISSUERS.remove(self._issuer_token)
        vectors = ("crank_angle_rad", "time_s", "volume_m3", "pressure_pa",
                   "temperature_k", "mass_kg", "internal_energy_j")
        for name in (*vectors, "mass_fractions"):
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        if any(getattr(self, name).ndim != 1 for name in vectors):
            raise ValueError("Every scalar engine history must be a one-dimensional array")
        if len(self.time_s) < 2 or any(len(getattr(self, name)) != len(self.time_s) for name in vectors):
            raise ValueError("Engine scalar histories must have one shared sample dimension")
        if (not np.all(np.isfinite(self.time_s)) or np.any(np.diff(self.time_s) <= 0)
                or np.any(np.diff(self.crank_angle_rad) <= 0)):
            raise ValueError("Engine trace time and crank-angle clocks must increase strictly")
        if (not isinstance(self.species_names, tuple) or not self.species_names
                or any(not isinstance(name, str) or not name.strip() for name in self.species_names)
                or len(set(self.species_names)) != len(self.species_names)):
            raise ValueError("Engine trace species order must contain unique nonblank names")
        if self.mass_fractions.shape != (len(self.time_s), len(self.species_names)):
            raise ValueError("Engine species history does not match sample/species dimensions")
        for name in ("crank_angle_rad", "volume_m3", "pressure_pa", "temperature_k",
                     "mass_kg", "internal_energy_j", "mass_fractions"):
            if not np.all(np.isfinite(getattr(self, name))):
                raise ValueError(f"Engine trace {name} must contain only finite values")
        if (np.any(self.volume_m3 <= 0) or np.any(self.pressure_pa <= 0)
                or np.any(self.temperature_k <= 0) or np.any(self.mass_kg <= 0)
                or np.any(self.mass_fractions < 0)
                or not np.allclose(self.mass_fractions.sum(axis=1), 1., rtol=1e-8, atol=1e-10)):
            raise ValueError("Engine trace contains nonphysical state summaries")
        finite(self.indicated_boundary_work_j, "indicated boundary work")
        finite(self.first_law_residual_j, "sampled first-law residual")
        if self.piston_heat_flux_schedule is None:
            if self.piston_heat_input_j is not None or self.piston_heat_area_m2 is not None:
                raise ValueError("Piston heat history requires an explicit flux schedule")
            heat_input = np.zeros(len(self.time_s), dtype=float)
        else:
            if type(self.piston_heat_flux_schedule) is not EngineBoundarySchedule:
                raise TypeError("Use an admitted EngineBoundarySchedule for piston heat")
            self.piston_heat_flux_schedule.require_current()
            if (self.piston_heat_flux_schedule.quantity != "heat_flux"
                    or self.piston_heat_flux_schedule.units != "W/m2"):
                raise ValueError("Piston schedule must declare quantity='heat_flux', units='W/m2'")
            area = finite(self.piston_heat_area_m2, "piston heat-transfer area", positive=True)
            heat_input = _readonly(self.piston_heat_input_j)
            if heat_input.shape != self.time_s.shape:
                raise ValueError("Piston heat history must share the native engine output clock")
            expected_heat = np.asarray([
                _schedule_energy_j(self.piston_heat_flux_schedule,
                                   self.piston_heat_flux_schedule.clock_origin_s + float(elapsed),
                                   area)
                for elapsed in self.time_s
            ])
            if not np.allclose(heat_input, expected_heat, rtol=1e-12, atol=1e-12):
                raise ValueError("Piston heat history does not reconstruct from its schedule and face area")
            object.__setattr__(self, "piston_heat_area_m2", area)
        object.__setattr__(self, "piston_heat_input_j", None if self.piston_heat_flux_schedule is None
                           else heat_input)
        expected_work = float(np.trapz(self.pressure_pa, self.volume_m3))
        expected_residual = float(self.internal_energy_j[-1] - self.internal_energy_j[0]
                                  + expected_work - heat_input[-1])
        if not np.isclose(self.indicated_boundary_work_j, expected_work, rtol=1e-12, atol=1e-12):
            raise ValueError("Reported pressure-volume work does not reconstruct from retained histories")
        if not np.isclose(self.first_law_residual_j, expected_residual, rtol=1e-12, atol=1e-12):
            raise ValueError("Reported sampled first-law residual does not reconstruct from retained histories")
        import cantera as ct

        if (not isinstance(self.native_reactor, ct.IdealGasReactor)
                or not isinstance(self.native_network, ct.ReactorNet)):
            raise ValueError("Engine trace must retain its native Cantera reactor and network")
        if (not isinstance(self.native_piston_wall, ct.Wall)
                or self.native_piston_wall.right_reactor is not self.native_reactor):
            raise ValueError("Engine trace must retain the original native piston wall")
        if (self.piston_heat_flux_schedule is not None
                and not np.isclose(self.native_piston_wall.area, self.piston_heat_area_m2,
                                   rtol=1e-12, atol=1e-12)):
            raise ValueError("Piston heat schedule area must match the native moving-wall area")

    def require_current(self):
        """Reject a trace whose retained native reactor has since advanced or changed."""
        import cantera as ct

        if (not isinstance(self.native_reactor, ct.IdealGasReactor)
                or not isinstance(self.native_network, ct.ReactorNet)
                or not isinstance(self.native_piston_wall, ct.Wall)
                or self.native_piston_wall.right_reactor is not self.native_reactor):
            raise ValueError("Engine trace lost its native Cantera owners")
        phase = self.native_reactor.phase
        terminal = (
            float(phase.P), float(phase.T), float(self.native_reactor.mass),
            float(self.native_reactor.mass * phase.int_energy_mass),
        )
        expected = (self.pressure_pa[-1], self.temperature_k[-1], self.mass_kg[-1],
                    self.internal_energy_j[-1])
        if any(not np.isclose(actual, retained, rtol=1e-12, atol=1e-12)
               for actual, retained in zip(terminal, expected)):
            raise ValueError("Native engine state changed after the trace was issued")
        if not np.array_equal(np.asarray(phase.Y), self.mass_fractions[-1]):
            raise ValueError("Native engine composition changed after the trace was issued")
        if self.piston_heat_flux_schedule is not None:
            self.piston_heat_flux_schedule.require_current()
            if (not np.isclose(self.native_network.time, self.time_s[-1], rtol=1e-12, atol=1e-12)
                    or not np.isclose(self.native_reactor.volume, self.volume_m3[-1],
                                      rtol=1e-10, atol=1e-13)):
                raise ValueError("Native engine clock or moving volume changed after trace issuance")
            expected_rate = (float(self.piston_heat_flux_schedule.at(
                self.piston_heat_flux_schedule.clock_origin_s + float(self.time_s[-1])))
                * self.piston_heat_area_m2)
            if (not np.isclose(self.native_piston_wall.area, self.piston_heat_area_m2,
                               rtol=1e-12, atol=1e-12)
                    or not np.isclose(self.native_piston_wall.heat_rate, expected_rate,
                                      rtol=1e-10, atol=1e-10)):
                raise ValueError("Native piston heat boundary changed after trace issuance")
            expected_heat = np.asarray([
                _schedule_energy_j(self.piston_heat_flux_schedule,
                                   self.piston_heat_flux_schedule.clock_origin_s + float(elapsed),
                                   self.piston_heat_area_m2)
                for elapsed in self.time_s
            ])
            if not np.array_equal(expected_heat, self.piston_heat_input_j):
                raise ValueError("Piston heat ledger changed after native trace issuance")
        return self


class ClosedChargeEngineError(RuntimeError):
    """Retain the accepted native state prefix if integration or result assembly fails."""

    def __init__(self, cause, *, native_reactor, native_network, native_wall,
                 accepted_angles, accepted_times, accepted_states, failed_target_s):
        super().__init__(f"Native closed-charge engine segment failed: {cause}")
        self.cause = cause
        self.__cause__ = cause
        self.native_reactor = native_reactor
        self.native_network = native_network
        self.native_wall = native_wall
        self.accepted_crank_angle_rad = _readonly(accepted_angles)
        self.accepted_time_s = _readonly(accepted_times)
        self.accepted_states = tuple(
            (float(p), float(t), float(m), float(u), _readonly(y))
            for p, t, m, u, y in accepted_states
        )
        self.failed_target_s = float(failed_target_s)
        self.last_accepted_time_s = (
            float(self.accepted_time_s[-1]) if len(self.accepted_time_s) else None
        )


def run_closed_charge_engine_segment(
    phase_factory,
    mechanism_basis: MechanismBasis,
    initial: ReactiveState,
    geometry: SliderCrank,
    *,
    crank_start_rad: float,
    crank_end_rad: float,
    piston_heat_flux_schedule: EngineBoundarySchedule | None = None,
    samples_per_revolution: int = 720,
    relative_tolerance: float = 1e-9,
    absolute_tolerance: float = 1e-13,
) -> ClosedChargeEngineTrace:
    """Integrate a premixed H2 charge through a caller-selected crank interval.

    ``phase_factory`` returns a fresh Cantera ideal-gas ``Solution``. ``initial``
    supplies the uniform chamber mixture at ``crank_start_rad``. The interval is
    strictly shorter than one four-stroke cycle; its endpoints are not interpreted
    as valve events. A static ambient reservoir on the other side of a native Wall
    supplies the reference pressure for piston work. No mass crosses the chamber
    boundary. An optional ``piston_heat_flux_schedule`` imposes a caller-specified
    W/m2 heat flux through the piston face, positive into the cylinder. Cantera
    applies it on the same native Wall as the prescribed motion; no heat-transfer
    correlation is inferred. Hydrogen and oxygen must both exist in the phase and have
    positive initial mole fractions. Finite-rate reaction is delegated to the
    native phase mechanism; no spark or ignition delay is prescribed.

    ``indicated_boundary_work_j`` is positive for work delivered by the gas and is
    estimated from the returned samples. The optional piston-face flux is signed
    positive into the gas and integrated over the geometry-derived face area. The
    first-law residual is a sampled diagnostic, not a native accepted-step
    conservation certificate.
    """
    import cantera as ct

    if tuple(int(value) for value in ct.__version__.split(".")[:2]) != (3, 2):
        raise ValueError("Closed-charge moving-wall support requires Cantera 3.2.x")
    if not callable(phase_factory):
        raise ValueError("A native Cantera phase factory is required")
    if not isinstance(mechanism_basis, MechanismBasis) or not isinstance(initial, ReactiveState):
        raise ValueError("MechanismBasis and ReactiveState inputs are required")
    start = finite(crank_start_rad, "crank start")
    end = finite(crank_end_rad, "crank end")
    cycle = 4 * np.pi
    if not (0 <= start < end <= cycle):
        raise ValueError("Crank interval must increase within [0, 4*pi]")
    if end - start >= cycle:
        raise ValueError("A single closed-charge segment must be shorter than one cycle")
    heat_schedule = piston_heat_flux_schedule
    if heat_schedule is not None:
        if type(heat_schedule) is not EngineBoundarySchedule:
            raise TypeError("piston_heat_flux_schedule must be an EngineBoundarySchedule or None")
        heat_schedule.require_current()
        if heat_schedule.quantity != "heat_flux" or heat_schedule.units != "W/m2":
            raise ValueError("Piston heat schedule must declare quantity='heat_flux', units='W/m2'")
        heat_duration = (end-start) / (2 * np.pi * geometry.speed_rpm / 60)
        _schedule_energy_j(heat_schedule,
                           heat_schedule.clock_origin_s + heat_duration,
                           geometry.piston_area_m2)
    if isinstance(samples_per_revolution, bool) or not isinstance(samples_per_revolution, int):
        raise ValueError("Samples per revolution must be an integer")
    if samples_per_revolution < 36:
        raise ValueError("At least 36 samples per revolution are required")
    for name, value in (("relative tolerance", relative_tolerance),
                        ("absolute tolerance", absolute_tolerance)):
        if not 0 < finite(value, name) < 1:
            raise ValueError(f"{name.capitalize()} must lie in (0, 1)")

    mechanism_basis.require_state(initial.temperature_k, initial.pressure_pa)
    phase = phase_factory()
    if not isinstance(phase, ct.Solution) or phase.thermo_model != "ideal-gas":
        raise ValueError("Factory must return a Cantera ideal-gas Solution")
    if phase.phase_of_matter != "gas" or phase.n_reactions == 0:
        raise ValueError("A reacting gas phase is required for this combustion segment")
    if phase.n_selected_species != phase.n_species:
        raise ValueError("Selected-species Cantera views are not supported")
    if not {"H2", "O2"} <= set(phase.species_names):
        raise ValueError("Native mechanism must include H2 and O2 species")
    if not set(initial.mole_fractions) <= set(phase.species_names):
        raise ValueError("Initial charge contains species absent from the native phase")
    if initial.mole_fractions.get("H2", 0.) <= 0 or initial.mole_fractions.get("O2", 0.) <= 0:
        raise ValueError("Initial charge needs positive H2 and O2 mole fractions")
    if not phase.min_temp <= initial.temperature_k <= phase.max_temp:
        raise ValueError("Initial temperature is outside native thermo limits")
    phase.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
    initial_volume = float(geometry.volume_m3(start))
    reactor = ct.IdealGasReactor(phase, clone=True, name="h2_closed_charge_cylinder")
    reactor.volume = initial_volume
    ambient_phase = phase_factory()
    if not isinstance(ambient_phase, ct.Solution) or ambient_phase.thermo_model != "ideal-gas":
        raise ValueError("Ambient reference factory must return an ideal-gas Solution")
    ambient_phase.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
    ambient = ct.Reservoir(ambient_phase, clone=True, name="piston_reference")
    heat_flux = (None if heat_schedule is None else
                 lambda time_s: float(heat_schedule.at(
                     heat_schedule.clock_origin_s + float(time_s))))
    piston = (ct.Wall(ambient, reactor, name="prescribed_slider_crank")
              if heat_flux is None else
              ct.Wall(ambient, reactor, name="prescribed_slider_crank", Q=heat_flux))
    piston.area = geometry.piston_area_m2
    omega = 2 * np.pi * geometry.speed_rpm / 60
    piston.velocity = lambda time_s: -float(
        geometry.volume_rate_m3_s(start + omega * time_s)
    ) / geometry.piston_area_m2

    network = ct.ReactorNet([reactor])
    network.rtol = float(relative_tolerance)
    network.atol = float(absolute_tolerance)
    angle_step = 2 * np.pi / samples_per_revolution
    angles = np.linspace(start, end, max(2, int(np.ceil((end - start) / angle_step)) + 1))
    times = (angles - start) / omega
    if heat_schedule is not None:
        origin = heat_schedule.clock_origin_s
        knots = [float(value-origin) for value in heat_schedule.time_s
                 if origin < value < origin+float(times[-1])]
        times = np.asarray(sorted({*(float(value) for value in times), *knots}), dtype=float)
        angles = start + omega * times
    states = []
    target = float(times[0])
    try:
        for target_value in times:
            target = float(target_value)
            _advance_native(network, target)
            native = reactor.phase
            states.append((native.P, native.T, reactor.mass, reactor.mass * native.int_energy_mass,
                           np.array(native.Y, copy=True)))
        values = np.asarray([row[:4] for row in states], dtype=float)
        fractions = np.vstack([row[4] for row in states])
        volumes = np.asarray(geometry.volume_m3(angles), dtype=float)
        heat_input = (None if heat_schedule is None else np.asarray([
            _schedule_energy_j(heat_schedule, heat_schedule.clock_origin_s + float(elapsed),
                               geometry.piston_area_m2)
            for elapsed in times
        ], dtype=float))
        # Signed trapezoidal integration preserves compression/expansion work direction.
        work = float(np.trapz(values[:, 0], volumes))
        residual = float(values[-1, 3] - values[0, 3] + work
                         - (0. if heat_input is None else heat_input[-1]))
        token = _issue_trace_token()
        return ClosedChargeEngineTrace(
            angles, times, volumes, values[:, 0], values[:, 1], values[:, 2], values[:, 3],
            tuple(reactor.phase.species_names), fractions, work, residual, reactor, network, token,
            native_piston_wall=piston,
            piston_heat_flux_schedule=heat_schedule,
            piston_heat_area_m2=(None if heat_schedule is None else geometry.piston_area_m2),
            piston_heat_input_j=heat_input,
        )
    except Exception as cause:
        count = len(states)
        raise ClosedChargeEngineError(
            cause, native_reactor=reactor, native_network=network, native_wall=piston,
            accepted_angles=angles[:count], accepted_times=times[:count],
            accepted_states=states, failed_target_s=target,
        ) from cause
