"""Prescribed-flow, pressure-valved and shared-nozzle cylinder intervals.

Cantera owns reacting ideal-gas thermodynamics, native flow-device adaptation
and time integration. Caller-specified inlets/outlets, native pressure valves,
and a shared isentropic nozzle feed are coupled to the slider-crank moving wall.
These remain bounded component seams, not complete valve, injector or cycle
physics.
"""

from dataclasses import dataclass, field

import numpy as np

from ..adapters.cantera import MechanismBasis, ReactiveState
from ..adapters.cantera_properties import (
    CanteraFrozenGasProperties,
    _fingerprint as _cantera_fingerprint,
    _phase_identity as _cantera_phase_identity,
)
from ..core import finite
from ..release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleResult
from .closed_charge_engine import (
    EngineBoundarySchedule,
    SliderCrank,
    engine_schedule_from_crank_angle,
)
from .engine_wall import CylinderWallThermal

_PENDING_TRACE_ISSUERS: set[object] = set()


def _readonly(value):
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise ValueError("Open-cylinder histories require numeric arrays")
    data = np.array(raw, dtype=float, copy=True)
    if not np.all(np.isfinite(data)):
        raise ValueError("Open-cylinder histories must be finite")
    return np.frombuffer(data.tobytes(order="C"), dtype=np.float64).reshape(data.shape)


def _issue_trace():
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    return token


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class OpenCylinderInlet:
    """One fixed, source-bound feed state with a scheduled nonnegative rate.

    ``state`` supplies the fixed reservoir composition, temperature and pressure.
    The retained enthalpy reference identifies the caller's interpretation of
    mechanism-relative enthalpy; it is not a license or thermodynamic conversion.
    """

    identifier: str
    state: ReactiveState
    mass_flow: EngineBoundarySchedule
    source_reference: str
    enthalpy_reference: str

    def __post_init__(self):
        object.__setattr__(self, "identifier", _text(self.identifier, "inlet identifier"))
        object.__setattr__(self, "source_reference", _text(self.source_reference, "inlet source reference"))
        object.__setattr__(self, "enthalpy_reference", _text(self.enthalpy_reference, "inlet enthalpy reference"))
        if type(self.state) is not ReactiveState:
            raise TypeError("Inlet state must be a fixed ReactiveState")
        if type(self.mass_flow) is not EngineBoundarySchedule:
            raise TypeError("Inlet rate must be an EngineBoundarySchedule")
        self.mass_flow.require_current()
        if self.mass_flow.quantity != "mass_flow" or self.mass_flow.units != "kg/s":
            raise ValueError("Inlet schedule must declare quantity='mass_flow', units='kg/s'")
        if np.any(self.mass_flow.values < 0):
            raise ValueError("Inlet mass-flow magnitude must be nonnegative")


def open_cylinder_inlet_from_crank_angle(
    *, identifier: str, state: ReactiveState, crank_angle_rad, mass_flow_kg_s,
    geometry: SliderCrank, crank_start_rad: float, absolute_clock_origin_s: float,
    schedule_source_id: str, source_reference: str, enthalpy_reference: str,
) -> OpenCylinderInlet:
    """Bind a fixed-state feed to caller-prescribed flow values on crank angle.

    This maps a crank-angle flow history to the segment's absolute time base and
    creates the existing native-reservoir inlet boundary. It represents a
    prescribed feed (including a fuel feed); it supplies no injector, nozzle,
    spray, valve-timing, or atomization law. The schedule must cover the complete
    segment when admitted by :func:`run_open_cylinder_segment`.
    """
    schedule = engine_schedule_from_crank_angle(
        quantity="mass_flow", units="kg/s", source_id=schedule_source_id,
        clock_origin_s=absolute_clock_origin_s, crank_angle_rad=crank_angle_rad,
        values=mass_flow_kg_s, geometry=geometry, crank_start_rad=crank_start_rad,
    )
    return OpenCylinderInlet(
        identifier=identifier, state=state, mass_flow=schedule,
        source_reference=source_reference, enthalpy_reference=enthalpy_reference,
    )


@dataclass(frozen=True, slots=True)
class OpenCylinderNozzleInlet:
    """Pressure-driven source feed evaluated by the shared isentropic nozzle.

    The source is a fixed native gas reservoir. Its outlet mass flow is obtained
    from the shared phase-aware nozzle at the live Cantera cylinder backpressure;
    the source rate is then supplied through a native MassFlowController. The
    property provider must share the source/cylinder native phase definition.
    """

    identifier: str
    state: ReactiveState
    nozzle: HomogeneousIsentropicNozzle
    opening: NozzleOpening
    opening_schedule: EngineBoundarySchedule
    source_reference: str
    enthalpy_reference: str

    def __post_init__(self):
        for name in ("identifier", "source_reference", "enthalpy_reference"):
            object.__setattr__(self, name, _text(getattr(self, name), name.replace("_", " ")))
        if type(self.state) is not ReactiveState:
            raise TypeError("A nozzle feed requires a fixed caller-declared ReactiveState")
        if type(self.nozzle) is not HomogeneousIsentropicNozzle:
            raise TypeError("Use the shared HomogeneousIsentropicNozzle solver")
        if type(self.nozzle.properties) is not CanteraFrozenGasProperties:
            raise TypeError("Nozzle feed properties must use the native Cantera frozen-gas basis")
        if type(self.opening) is not NozzleOpening:
            raise TypeError("A shared NozzleOpening is required")
        if type(self.opening_schedule) is not EngineBoundarySchedule:
            raise TypeError("A source-bound nozzle opening schedule is required")
        self.opening_schedule.require_current()
        if (self.opening_schedule.quantity != "nozzle_open_fraction"
                or self.opening_schedule.units != "1"):
            raise ValueError("Nozzle opening must declare quantity='nozzle_open_fraction', units='1'")
        if np.any((self.opening_schedule.values < 0.) | (self.opening_schedule.values > 1.)):
            raise ValueError("Nozzle opening fractions must lie in [0, 1]")


@dataclass(frozen=True, slots=True)
class OpenCylinderOutlet:
    """One prescribed extraction of the current, well-mixed cylinder gas."""

    identifier: str
    mass_flow: EngineBoundarySchedule
    source_reference: str

    def __post_init__(self):
        object.__setattr__(self, "identifier", _text(self.identifier, "outlet identifier"))
        object.__setattr__(self, "source_reference", _text(self.source_reference, "outlet source reference"))
        if type(self.mass_flow) is not EngineBoundarySchedule:
            raise TypeError("Outlet rate must be an EngineBoundarySchedule")
        self.mass_flow.require_current()
        if self.mass_flow.quantity != "mass_flow" or self.mass_flow.units != "kg/s":
            raise ValueError("Outlet schedule must declare quantity='mass_flow', units='kg/s'")
        if np.any(self.mass_flow.values < 0):
            raise ValueError("Outlet mass-flow magnitude must be nonnegative")


@dataclass(frozen=True, slots=True)
class OpenCylinderValveInlet:
    """Pressure-driven inlet through Cantera Valve with caller-specified opening.

    Cantera's native linear valve law is mdot = K * opening(t) * max(dP, 0).
    The coefficient is source-bound and expressed in kg/s/Pa; this API does not
    infer a discharge coefficient, area, compressible-flow law, or valve timing.
    """

    identifier: str
    state: ReactiveState
    opening: EngineBoundarySchedule
    coefficient_kg_s_pa: float
    coefficient_reference: str
    source_reference: str
    enthalpy_reference: str

    def __post_init__(self):
        for name in ("identifier", "coefficient_reference", "source_reference", "enthalpy_reference"):
            object.__setattr__(self, name, _text(getattr(self, name), name.replace("_", " ")))
        if type(self.state) is not ReactiveState or type(self.opening) is not EngineBoundarySchedule:
            raise TypeError("Valve inlet requires a fixed ReactiveState and opening schedule")
        self.opening.require_current()
        if self.opening.quantity != "valve_open_fraction" or self.opening.units != "1":
            raise ValueError("Valve opening must declare quantity='valve_open_fraction', units='1'")
        if np.any((self.opening.values < 0) | (self.opening.values > 1)):
            raise ValueError("Valve opening fractions must lie in [0, 1]")
        coefficient = finite(self.coefficient_kg_s_pa, "valve coefficient")
        if coefficient < 0:
            raise ValueError("Valve coefficient must be nonnegative")
        object.__setattr__(self, "coefficient_kg_s_pa", coefficient)


@dataclass(frozen=True, slots=True)
class OpenCylinderValveOutlet:
    """Pressure-driven exhaust from the well-mixed cylinder through Cantera Valve."""

    identifier: str
    opening: EngineBoundarySchedule
    coefficient_kg_s_pa: float
    coefficient_reference: str
    source_reference: str

    def __post_init__(self):
        for name in ("identifier", "coefficient_reference", "source_reference"):
            object.__setattr__(self, name, _text(getattr(self, name), name.replace("_", " ")))
        if type(self.opening) is not EngineBoundarySchedule:
            raise TypeError("Valve outlet requires an opening schedule")
        self.opening.require_current()
        if self.opening.quantity != "valve_open_fraction" or self.opening.units != "1":
            raise ValueError("Valve opening must declare quantity='valve_open_fraction', units='1'")
        if np.any((self.opening.values < 0) | (self.opening.values > 1)):
            raise ValueError("Valve opening fractions must lie in [0, 1]")
        coefficient = finite(self.coefficient_kg_s_pa, "valve coefficient")
        if coefficient < 0:
            raise ValueError("Valve coefficient must be nonnegative")
        object.__setattr__(self, "coefficient_kg_s_pa", coefficient)


@dataclass(frozen=True, slots=True)
class OpenCylinderBoundary:
    """Collection of fixed-state inlet feeds and bulk-mixture outlet schedules."""

    inlets: tuple[OpenCylinderInlet, ...]
    outlets: tuple[OpenCylinderOutlet, ...]
    valve_inlets: tuple[OpenCylinderValveInlet, ...] = ()
    valve_outlets: tuple[OpenCylinderValveOutlet, ...] = ()
    nozzle_inlets: tuple[OpenCylinderNozzleInlet, ...] = ()

    def __post_init__(self):
        inlets, outlets = tuple(self.inlets), tuple(self.outlets)
        valve_inlets, valve_outlets = tuple(self.valve_inlets), tuple(self.valve_outlets)
        nozzle_inlets = tuple(self.nozzle_inlets)
        if not inlets and not outlets and not valve_inlets and not valve_outlets and not nozzle_inlets:
            raise ValueError("Declare at least one open-cylinder inlet or outlet")
        if any(type(item) is not OpenCylinderInlet for item in inlets):
            raise TypeError("Open-cylinder inlets must be OpenCylinderInlet objects")
        if any(type(item) is not OpenCylinderOutlet for item in outlets):
            raise TypeError("Open-cylinder outlets must be OpenCylinderOutlet objects")
        if any(type(item) is not OpenCylinderValveInlet for item in valve_inlets):
            raise TypeError("Valve inlets must be OpenCylinderValveInlet objects")
        if any(type(item) is not OpenCylinderValveOutlet for item in valve_outlets):
            raise TypeError("Valve outlets must be OpenCylinderValveOutlet objects")
        if any(type(item) is not OpenCylinderNozzleInlet for item in nozzle_inlets):
            raise TypeError("Nozzle inlets must be OpenCylinderNozzleInlet objects")
        ids = [item.identifier for item in (*inlets, *outlets, *valve_inlets,
                                             *valve_outlets, *nozzle_inlets)]
        if len(ids) != len(set(ids)):
            raise ValueError("Open-cylinder boundary identifiers must be unique")
        refs = {item.enthalpy_reference for item in (*inlets, *valve_inlets, *nozzle_inlets)}
        if len(refs) > 1:
            raise ValueError("All inlet feeds must declare one common enthalpy reference")
        object.__setattr__(self, "inlets", inlets)
        object.__setattr__(self, "outlets", outlets)
        object.__setattr__(self, "valve_inlets", valve_inlets)
        object.__setattr__(self, "valve_outlets", valve_outlets)
        object.__setattr__(self, "nozzle_inlets", nozzle_inlets)


def _schedule_fingerprint(boundary):
    return tuple(
        ("in", item.identifier, item.state.temperature_k, item.state.pressure_pa,
         tuple(sorted(item.state.mole_fractions.items())), item.source_reference,
         item.enthalpy_reference, item.mass_flow._current_content())
        for item in boundary.inlets
    ) + tuple(
        ("out", item.identifier, item.source_reference, item.mass_flow._current_content())
        for item in boundary.outlets
    ) + tuple(
        ("valve-in", item.identifier, item.state.temperature_k, item.state.pressure_pa,
         tuple(sorted(item.state.mole_fractions.items())), item.coefficient_kg_s_pa,
         item.coefficient_reference, item.source_reference, item.enthalpy_reference,
         item.opening._current_content()) for item in boundary.valve_inlets
    ) + tuple(
        ("valve-out", item.identifier, item.coefficient_kg_s_pa,
         item.coefficient_reference, item.source_reference, item.opening._current_content())
        for item in boundary.valve_outlets
    ) + tuple(
        ("nozzle-in", item.identifier, item.state.temperature_k, item.state.pressure_pa,
         tuple(sorted(item.state.mole_fractions.items())), item.source_reference,
         item.enthalpy_reference, item.opening, item.opening_schedule._current_content(),
         id(item.nozzle), id(item.nozzle.properties), item.nozzle.search,
         item.nozzle.properties.mechanism_basis, item.nozzle.properties.phase_sha256,
         item.nozzle.properties.composition_sha256)
        for item in boundary.nozzle_inlets
    )


def _input_fingerprint(boundary, geometry, mechanism_basis, origin, wall_thermal=None):
    return (_schedule_fingerprint(boundary),
            (geometry.bore_m, geometry.stroke_m, geometry.connecting_rod_m,
             geometry.compression_ratio, geometry.speed_rpm),
            (mechanism_basis.identifier, mechanism_basis.source_sha256,
             mechanism_basis.license_id, mechanism_basis.references,
             mechanism_basis.minimum_temperature_k, mechanism_basis.maximum_temperature_k,
             mechanism_basis.minimum_pressure_pa, mechanism_basis.maximum_pressure_pa),
            float(origin), None if wall_thermal is None else wall_thermal._seal_payload())


def _array_fingerprint(trace):
    names = ("crank_angle_rad", "time_s", "volume_m3", "pressure_pa", "temperature_k",
             "mass_kg", "internal_energy_j", "mass_fractions", "species_transfer_kg",
             "inlet_enthalpy_transfer_j", "outlet_enthalpy_transfer_j",
             "pressure_volume_work_j", "mass_balance_residual_kg",
             "sampled_first_law_residual_j")
    values = (("species_names", trace.species_names),) + tuple(
        (name, getattr(trace, name).shape, getattr(trace, name).tobytes(order="C"))
        for name in names
    )
    wall_names = ("wall_temperature_k", "wall_internal_energy_j",
                  "gas_wall_heat_into_gas_j", "wall_boundary_heat_j")
    if trace.wall_thermal is not None:
        values += tuple((name, getattr(trace, name).shape,
                         getattr(trace, name).tobytes(order="C"))
                        for name in wall_names)
    if trace.boundary.nozzle_inlets:
        values += (("nozzle_results", trace.nozzle_results),)
    return values


@dataclass(frozen=True, slots=True)
class OpenCylinderEngineTrace:
    """Native Cantera output samples and sampled boundary/conservation ledgers."""

    crank_angle_rad: np.ndarray
    time_s: np.ndarray
    volume_m3: np.ndarray
    pressure_pa: np.ndarray
    temperature_k: np.ndarray
    mass_kg: np.ndarray
    internal_energy_j: np.ndarray
    species_names: tuple[str, ...]
    mass_fractions: np.ndarray
    species_transfer_kg: np.ndarray
    inlet_enthalpy_transfer_j: np.ndarray
    outlet_enthalpy_transfer_j: np.ndarray
    pressure_volume_work_j: np.ndarray
    mass_balance_residual_kg: np.ndarray
    sampled_first_law_residual_j: np.ndarray
    mechanism_basis: MechanismBasis
    geometry: SliderCrank
    boundary: OpenCylinderBoundary
    absolute_clock_origin_s: float
    native_reactor: object = field(repr=False, compare=False)
    native_network: object = field(repr=False, compare=False)
    native_wall: object = field(repr=False, compare=False)
    native_flow_devices: tuple = field(repr=False, compare=False)
    native_reservoirs: tuple = field(repr=False, compare=False)
    _issuer_token: object = field(repr=False, compare=False)
    wall_thermal: CylinderWallThermal | None = field(default=None, repr=False, compare=False)
    wall_temperature_k: np.ndarray | None = None
    wall_internal_energy_j: np.ndarray | None = None
    gas_wall_heat_into_gas_j: np.ndarray | None = None
    wall_boundary_heat_j: np.ndarray | None = None
    nozzle_results: tuple[tuple[NozzleResult, ...], ...] = field(default=(), repr=False)
    _array_seal: tuple = field(default=(), repr=False, compare=False)
    _source_seal: tuple = field(default=(), repr=False, compare=False)
    _terminal_seal: tuple = field(default=(), repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRACE_ISSUERS:
            raise TypeError("Create open-cylinder traces through a native Cantera run")
        _PENDING_TRACE_ISSUERS.remove(self._issuer_token)
        vector_names = ("crank_angle_rad", "time_s", "volume_m3", "pressure_pa",
                        "temperature_k", "mass_kg", "internal_energy_j",
                        "inlet_enthalpy_transfer_j", "outlet_enthalpy_transfer_j",
                        "pressure_volume_work_j", "mass_balance_residual_kg",
                        "sampled_first_law_residual_j")
        for name in (*vector_names, "mass_fractions", "species_transfer_kg"):
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        n = len(self.time_s)
        if n < 2 or any(getattr(self, name).shape != (n,) for name in vector_names):
            raise ValueError("Open-cylinder scalar outputs must share at least two samples")
        if (not np.all(np.diff(self.time_s) > 0) or not np.all(np.diff(self.crank_angle_rad) > 0)
                or not np.all(self.volume_m3 > 0) or not np.all(self.mass_kg > 0)
                or not np.all(self.pressure_pa > 0) or not np.all(self.temperature_k > 0)):
            raise ValueError("Open-cylinder histories violate time, geometry or state bounds")
        if self.mass_fractions.shape != (n, len(self.species_names)):
            raise ValueError("Open-cylinder composition dimensions do not match its species list")
        if (not isinstance(self.species_names, tuple) or not self.species_names
                or len(set(self.species_names)) != len(self.species_names)
                or any(not isinstance(name, str) or not name.strip() for name in self.species_names)):
            raise ValueError("Open-cylinder species names must be unique nonblank strings")
        if self.species_transfer_kg.shape != (n, len(self.species_names)):
            raise ValueError("Open-cylinder species ledger dimensions are inconsistent")
        if np.any(self.mass_fractions < 0) or not np.allclose(
                self.mass_fractions.sum(axis=1), 1., rtol=1e-8, atol=1e-10):
            raise ValueError("Open-cylinder mass fractions are not normalized")
        wall_names = ("wall_temperature_k", "wall_internal_energy_j",
                      "gas_wall_heat_into_gas_j", "wall_boundary_heat_j")
        if self.wall_thermal is None:
            if any(getattr(self, name) is not None for name in wall_names):
                raise ValueError("Wall histories require an explicit finite wall model")
        else:
            if type(self.wall_thermal) is not CylinderWallThermal:
                raise TypeError("Use the explicit CylinderWallThermal boundary")
            self.wall_thermal.require_current()
            for name in wall_names:
                array = _readonly(getattr(self, name))
                if array.shape != (n,):
                    raise ValueError("Cylinder wall histories must share the native accepted clock")
                object.__setattr__(self, name, array)
            if (np.any(self.wall_temperature_k <= 0.)
                    or not np.isclose(self.wall_temperature_k[0],
                                      self.wall_thermal.initial_temperature_k,
                                      rtol=0., atol=1e-12)):
                raise ValueError("Wall temperature history must retain its declared positive initial state")
            expected_wall_u = self.wall_thermal.heat_capacity_j_k * (
                self.wall_temperature_k - self.wall_thermal.reference_temperature_k)
            if not np.allclose(self.wall_internal_energy_j, expected_wall_u, rtol=1e-12, atol=1e-9):
                raise ValueError("Wall energy history differs from the declared lumped heat capacity")
            wall_terminal = (self.native_reactor._h2_wall_temperature_k,
                             self.native_reactor._h2_wall_heat_into_wall_j,
                             self.native_reactor._h2_wall_boundary_heat_j)
            wall_history_terminal = (self.wall_temperature_k[-1],
                                     -self.gas_wall_heat_into_gas_j[-1],
                                     self.wall_boundary_heat_j[-1])
            if not np.allclose(wall_terminal, wall_history_terminal, rtol=1e-12, atol=1e-12):
                raise ValueError("Accepted wall histories do not match the native reactor terminal state")
        nozzle_rows = tuple(tuple(row) for row in self.nozzle_results)
        if not self.boundary.nozzle_inlets:
            if nozzle_rows:
                raise ValueError("Nozzle histories require an explicit nozzle-inlet boundary")
        else:
            if len(nozzle_rows) != n or any(len(row) != len(self.boundary.nozzle_inlets)
                                             for row in nozzle_rows):
                raise ValueError("Every accepted clock point needs one result per nozzle inlet")
            for sample_index, row in enumerate(nozzle_rows):
                absolute_time = float(self.time_s[sample_index])
                for item, result in zip(self.boundary.nozzle_inlets, row, strict=True):
                    if (type(result) is not NozzleResult or result.opening != item.opening
                            or not np.isclose(result.back_pressure_pa, self.pressure_pa[sample_index],
                                              rtol=1e-12, atol=1e-8)):
                        raise ValueError("Nozzle result is not bound to its accepted cylinder pressure")
                    fraction = float(item.opening_schedule.at(absolute_time))
                    if not np.isclose(result.effective_area_m2,
                                      item.opening.effective_area_m2(fraction),
                                      rtol=1e-12, atol=1e-14):
                        raise ValueError("Nozzle result area differs from its accepted opening schedule")
            object.__setattr__(self, "nozzle_results", nozzle_rows)
        object.__setattr__(self, "absolute_clock_origin_s",
                           finite(self.absolute_clock_origin_s, "absolute clock origin"))
        object.__setattr__(self, "_array_seal", _array_fingerprint(self))
        object.__setattr__(self, "_source_seal", _input_fingerprint(
            self.boundary, self.geometry, self.mechanism_basis,
            self.absolute_clock_origin_s, self.wall_thermal))
        object.__setattr__(self, "_terminal_seal", self._native_terminal())

    def _native_terminal(self):
        phase = self.native_reactor.phase
        return (float(self.native_network.time), float(self.native_reactor.mass),
                float(self.native_reactor.volume),
                float(phase.P), float(phase.T), np.asarray(phase.Y, dtype=float).tobytes(),
                getattr(self.native_reactor, "_h2_wall_temperature_k", None),
                getattr(self.native_reactor, "_h2_wall_heat_into_wall_j", None),
                getattr(self.native_reactor, "_h2_wall_boundary_heat_j", None),
                tuple(float(device.mass_flow_rate) for device in self.native_flow_devices))

    def require_current(self):
        """Recheck the issued history, schedules and live native terminal state."""
        for item in (*self.boundary.inlets, *self.boundary.outlets):
            item.mass_flow.require_current()
        for item in (*self.boundary.valve_inlets, *self.boundary.valve_outlets):
            item.opening.require_current()
        for item in self.boundary.nozzle_inlets:
            item.opening_schedule.require_current()
            item.nozzle.properties._check_definition()
        if _array_fingerprint(self) != self._array_seal:
            raise ValueError("Open-cylinder trace arrays changed after native issuance")
        if _input_fingerprint(self.boundary, self.geometry, self.mechanism_basis,
                              self.absolute_clock_origin_s, self.wall_thermal) != self._source_seal:
            raise ValueError("Open-cylinder boundary inputs changed after native issuance")
        if self.wall_thermal is not None:
            self.wall_thermal.require_current()
        if self._native_terminal() != self._terminal_seal:
            raise ValueError("Native cylinder state advanced or changed after trace issuance")
        return self


class OpenCylinderEngineError(RuntimeError):
    """Failed native interval retaining its accepted sample prefix and owners."""

    def __init__(self, cause, *, native_reactor, native_network, native_wall,
                 native_flow_devices, native_reservoirs, accepted_prefix, failed_target_s):
        super().__init__(f"Native open-cylinder interval failed: {cause}")
        self.cause = cause
        self.__cause__ = cause
        self.native_reactor = native_reactor
        self.native_network = native_network
        self.native_wall = native_wall
        self.native_flow_devices = tuple(native_flow_devices)
        self.native_reservoirs = tuple(native_reservoirs)
        self.accepted_prefix = tuple(tuple(_readonly(value) if isinstance(value, np.ndarray) else value
                                           for value in row) for row in accepted_prefix)
        self.failed_target_s = float(failed_target_s)
        self.last_accepted_time_s = (float(accepted_prefix[-1][0]) if accepted_prefix else None)


def _snapshot(reactor, geometry, angle, time_s, species_names):
    phase = reactor.phase
    return (float(angle), float(time_s), float(reactor.volume), float(phase.P),
            float(phase.T), float(reactor.mass),
            float(reactor.mass * phase.int_energy_mass), np.array(phase.Y, dtype=float))


def _flow_rates(boundary, devices, inlet_reservoirs, reactor, species_names):
    species_index = {name: i for i, name in enumerate(species_names)}
    species_rate = np.zeros(len(species_names), dtype=float)
    inlet_enthalpy_rate = 0.0
    outlet_enthalpy_rate = 0.0
    inlet_mass_rate = 0.0
    outlet_mass_rate = 0.0
    n_in = len(boundary.inlets) + len(boundary.valve_inlets) + len(boundary.nozzle_inlets)
    for device, reservoir in zip(
            devices[:n_in], inlet_reservoirs, strict=True):
        rate = float(device.mass_flow_rate)
        inlet_mass_rate += rate
        for species, fraction in zip(species_names, reservoir.phase.Y, strict=True):
            species_rate[species_index[species]] += rate * float(fraction)
        inlet_enthalpy_rate += rate * float(reservoir.phase.enthalpy_mass)
    for device in devices[n_in:]:
        rate = float(device.mass_flow_rate)
        outlet_mass_rate += rate
        species_rate -= rate * np.asarray(reactor.phase.Y, dtype=float)
        outlet_enthalpy_rate += rate * float(reactor.phase.enthalpy_mass)
    return (species_rate, inlet_mass_rate, outlet_mass_rate,
            inlet_enthalpy_rate, outlet_enthalpy_rate)


def _cumulative(times, values):
    out = np.zeros(len(times), dtype=float)
    if len(times) > 1:
        out[1:] = np.cumsum(np.diff(times) * (values[:-1] + values[1:]) / 2.)
    return out


def run_open_cylinder_segment(
    phase_factory,
    mechanism_basis: MechanismBasis,
    initial: ReactiveState,
    geometry: SliderCrank,
    boundary: OpenCylinderBoundary,
    *,
    absolute_clock_origin_s: float,
    crank_start_rad: float,
    crank_end_rad: float,
    samples_per_revolution: int = 720,
    relative_tolerance: float = 1e-9,
    absolute_tolerance: float = 1e-13,
    wall_thermal: CylinderWallThermal | None = None,
) -> OpenCylinderEngineTrace:
    """Run a moving-volume cylinder segment with prescribed, valve or nozzle feeds.

    Each inlet composition, temperature and pressure are fixed over the run.
    Multiple feeds permit independently scheduled species or carrier streams;
    the resulting species feed rates are the sum of each reservoir's mass rate
    times its native composition. Prescribed outlets remove the current mixture
    at their declared rate; pressure-valved ports use Cantera's one-way linear
    law ``mdot = K * opening(t) * max(P_up-P_down, 0)``. Valve coefficients and
    opening histories are caller-owned and evidence-tagged; the native law does
    not represent measured valve-seat flow. Optional shared-nozzle inlets use
    ``HomogeneousIsentropicNozzle`` with live cylinder pressure as backpressure;
    Cantera's ``MassFlowController`` only adapts its resulting nonnegative rate.
    No spark is included. With ``wall_thermal`` supplied, one finite wall
    temperature is coupled to the same native network through caller-owned UA
    and heat inputs.

    Returned source/energy residuals are sampled trapezoidal diagnostics over
    exact requested clock points, including all input schedule knots. They do
    not replace Cantera's accepted-step energy equations or certify a complete
    cycle. Any failure raises ``OpenCylinderEngineError`` with native owners and
    the last accepted requested-sample prefix.
    """
    import cantera as ct

    if tuple(int(value) for value in ct.__version__.split(".")[:2]) != (3, 2):
        raise ValueError("Open-cylinder moving-wall support requires Cantera 3.2.x")
    if not callable(phase_factory):
        raise ValueError("A native Cantera phase factory is required")
    if (type(mechanism_basis) is not MechanismBasis or type(initial) is not ReactiveState
            or type(geometry) is not SliderCrank or type(boundary) is not OpenCylinderBoundary):
        raise TypeError("MechanismBasis, ReactiveState, SliderCrank and OpenCylinderBoundary are required")
    if wall_thermal is not None:
        if type(wall_thermal) is not CylinderWallThermal:
            raise TypeError("wall_thermal must be a CylinderWallThermal or None")
        wall_thermal.require_current()
        inlet_references = {item.enthalpy_reference
                            for item in (*boundary.inlets, *boundary.valve_inlets,
                                         *boundary.nozzle_inlets)}
        if inlet_references and inlet_references != {wall_thermal.energy_reference_id}:
            raise ValueError("Wall, inlet streams and declared energy balance must use one reference ID")
    origin = finite(absolute_clock_origin_s, "absolute clock origin")
    start = finite(crank_start_rad, "crank start")
    end = finite(crank_end_rad, "crank end")
    if not (0 <= start < end <= 4 * np.pi) or end - start >= 4 * np.pi:
        raise ValueError("Crank interval must increase and be shorter than one four-stroke cycle")
    if isinstance(samples_per_revolution, bool) or not isinstance(samples_per_revolution, int):
        raise ValueError("Samples per revolution must be an integer")
    if samples_per_revolution < 36:
        raise ValueError("At least 36 samples per revolution are required")
    for label, value in (("relative tolerance", relative_tolerance),
                         ("absolute tolerance", absolute_tolerance)):
        if not 0 < finite(value, label) < 1:
            raise ValueError(f"{label.capitalize()} must lie in (0, 1)")
    mechanism_basis.require_state(initial.temperature_k, initial.pressure_pa)

    omega = 2. * np.pi * geometry.speed_rpm / 60.
    duration = (end - start) / omega
    end_time = origin + duration
    schedules = (tuple(item.mass_flow for item in (*boundary.inlets, *boundary.outlets)) + tuple(
        item.opening for item in (*boundary.valve_inlets, *boundary.valve_outlets)) + tuple(
        item.opening_schedule for item in boundary.nozzle_inlets))
    for schedule in schedules:
        schedule.require_current()
        lo, hi = schedule.support_s
        if lo > origin or hi < end_time:
            raise ValueError("Every open-cylinder boundary schedule must cover the full run clock")

    # Regular crank sampling is supplemented with every source knot so rate
    # callbacks remain continuous on each native integration interval.
    angle_step = 2. * np.pi / samples_per_revolution
    angles = np.linspace(start, end, max(2, int(np.ceil((end - start) / angle_step)) + 1))
    target_times = origin + (angles - start) / omega
    all_knots = {float(v) for v in target_times}
    for schedule in schedules:
        all_knots.update(float(v) for v in schedule.time_s if origin < v < end_time)
    times = np.asarray(sorted(all_knots), dtype=float)
    angles = start + omega * (times - origin)

    phase = phase_factory()
    if not isinstance(phase, ct.Solution) or phase.thermo_model != "ideal-gas":
        raise ValueError("Factory must return a Cantera ideal-gas Solution")
    if phase.phase_of_matter != "gas" or phase.n_reactions == 0:
        raise ValueError("A reacting gas phase is required for the open-cylinder interval")
    if phase.n_selected_species != phase.n_species:
        raise ValueError("Selected-species Cantera views are not supported")
    if not {"H2", "O2"} <= set(phase.species_names):
        raise ValueError("Native hydrogen mechanism must include H2 and O2")
    if not set(initial.mole_fractions) <= set(phase.species_names):
        raise ValueError("Initial charge contains species absent from the native phase")
    phase.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
    if not phase.min_temp <= phase.T <= phase.max_temp:
        raise ValueError("Initial temperature is outside native thermo limits")

    boundary_error = None
    if wall_thermal is None:
        reactor = ct.IdealGasReactor(phase, clone=True, energy="on", name="h2_open_cylinder")
    else:
        class WallCoupledIdealGasReactor(ct.ExtensibleIdealGasReactor):
            def __init__(self, gas_phase):
                self._h2_wall_base_size = 0
                self._h2_wall_temperature_k = wall_thermal.initial_temperature_k
                self._h2_wall_heat_into_wall_j = 0.
                self._h2_wall_boundary_heat_j = 0.
                super().__init__(gas_phase, clone=True, energy="on", name="h2_open_cylinder")

            def after_initialize(self, t0):
                self._h2_wall_base_size = self.n_vars
                self.n_vars += 3

            def after_get_state(self, y):
                base = self._h2_wall_base_size
                # Cantera's extensible state vector proxy accepts scalar item
                # writes; slice assignment can be interpreted as one tuple
                # value by some supported callback paths.
                y[base] = float(self._h2_wall_temperature_k)
                y[base+1] = float(self._h2_wall_heat_into_wall_j)
                y[base+2] = float(self._h2_wall_boundary_heat_j)

            def after_update_state(self, y):
                base = self._h2_wall_base_size
                self._h2_wall_temperature_k = float(y[base])
                self._h2_wall_heat_into_wall_j = float(y[base+1])
                self._h2_wall_boundary_heat_j = float(y[base+2])

            def before_component_name(self, index):
                base = self._h2_wall_base_size
                if index == base:
                    return "cylinder_wall_temperature_k"
                if index == base+1:
                    return "cylinder_wall_gas_contact_energy_j"
                if index == base+2:
                    return "cylinder_wall_boundary_energy_j"

            def before_component_index(self, name):
                names = ("cylinder_wall_temperature_k", "cylinder_wall_gas_contact_energy_j",
                         "cylinder_wall_boundary_energy_j")
                if name in names:
                    return self._h2_wall_base_size + names.index(name)

            def after_eval(self, time, lhs, rhs):
                nonlocal boundary_error
                try:
                    base = self._h2_wall_base_size
                    wall_thermal.require_current()
                    wall_temperature = finite(self._h2_wall_temperature_k,
                                              "trial cylinder-wall temperature", positive=True)
                    gas_to_wall_w = wall_thermal.conductance_ua_w_k * (self.T-wall_temperature)
                    boundary_w = wall_thermal.external_heat_rate_w(
                        float(time), float(self.T), wall_temperature)
                    wall_thermal.require_current()
                    # Cantera retains the ideal-gas reactor U equation and the
                    # mechanical piston wall; these added terms are internal
                    # gas/wall heat exchange plus an explicit external boundary.
                    # IdealGasReactor's state vector starts with mass, volume,
                    # then temperature; index 2 is its temperature equation.
                    rhs[2] -= gas_to_wall_w
                    lhs[base] = wall_thermal.heat_capacity_j_k
                    rhs[base] = gas_to_wall_w + boundary_w
                    lhs[base+1:base+3] = 1.
                    rhs[base+1] = gas_to_wall_w
                    rhs[base+2] = boundary_w
                except Exception as exc:
                    boundary_error = exc
                    raise

        reactor = WallCoupledIdealGasReactor(phase)
    reactor.volume = float(geometry.volume_m3(start))
    ambient_phase = phase_factory()
    if not isinstance(ambient_phase, ct.Solution) or ambient_phase.thermo_model != "ideal-gas":
        raise ValueError("Moving-wall reference factory must return an ideal-gas Solution")
    ambient_phase.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
    ambient = ct.Reservoir(ambient_phase, clone=True, name="piston_reference")
    wall = ct.Wall(ambient, reactor, name="prescribed_slider_crank")
    wall.area = geometry.piston_area_m2
    wall.velocity = lambda time_s: -float(
        geometry.volume_rate_m3_s(start + omega * (float(time_s) - origin))
    ) / geometry.piston_area_m2

    inlet_reservoirs = []
    inlet_devices = []
    nozzle_upstream_states = {}
    nozzle_cache = {}
    outlet_reservoirs = []
    outlet_devices = []
    for item in boundary.inlets:
        feed_phase = phase_factory()
        if not isinstance(feed_phase, ct.Solution) or feed_phase.thermo_model != "ideal-gas":
            raise ValueError("Inlet factory must return a native ideal-gas Solution")
        if (feed_phase.n_species != phase.n_species or tuple(feed_phase.species_names) != tuple(phase.species_names)
                or tuple(feed_phase.element_names) != tuple(phase.element_names)):
            raise ValueError("Inlet and cylinder phases must use identical species and element order")
        if not set(item.state.mole_fractions) <= set(feed_phase.species_names):
            raise ValueError(f"Inlet {item.identifier!r} declares unavailable native species")
        mechanism_basis.require_state(item.state.temperature_k, item.state.pressure_pa)
        feed_phase.TPX = item.state.temperature_k, item.state.pressure_pa, dict(item.state.mole_fractions)
        if not feed_phase.min_temp <= feed_phase.T <= feed_phase.max_temp:
            raise ValueError(f"Inlet {item.identifier!r} temperature is outside native thermo limits")
        reservoir = ct.Reservoir(feed_phase, clone=True, name=f"feed-{item.identifier}")
        def feed_rate(time_s, schedule=item.mass_flow):
            nonlocal boundary_error
            try:
                return float(schedule.at(time_s))
            except Exception as exc:
                boundary_error = exc
                raise

        device = ct.MassFlowController(
            reservoir, reactor,
            mdot=feed_rate,
            name=f"feed-rate-{item.identifier}",
        )
        inlet_reservoirs.append(reservoir)
        inlet_devices.append(device)

    for item in boundary.valve_inlets:
        feed_phase = phase_factory()
        if not isinstance(feed_phase, ct.Solution) or feed_phase.thermo_model != "ideal-gas":
            raise ValueError("Valve-inlet factory must return a native ideal-gas Solution")
        if (feed_phase.n_species != phase.n_species
                or tuple(feed_phase.species_names) != tuple(phase.species_names)
                or tuple(feed_phase.element_names) != tuple(phase.element_names)):
            raise ValueError("Valve inlet and cylinder phases must use identical species and element order")
        if not set(item.state.mole_fractions) <= set(feed_phase.species_names):
            raise ValueError(f"Valve inlet {item.identifier!r} declares unavailable native species")
        mechanism_basis.require_state(item.state.temperature_k, item.state.pressure_pa)
        feed_phase.TPX = item.state.temperature_k, item.state.pressure_pa, dict(item.state.mole_fractions)
        if not feed_phase.min_temp <= feed_phase.T <= feed_phase.max_temp:
            raise ValueError(f"Valve inlet {item.identifier!r} temperature is outside native thermo limits")
        reservoir = ct.Reservoir(feed_phase, clone=True, name=f"valve-feed-{item.identifier}")

        def valve_opening(time_s, schedule=item.opening):
            nonlocal boundary_error
            try:
                return float(schedule.at(time_s))
            except Exception as exc:
                boundary_error = exc
                raise

        device = ct.Valve(reservoir, reactor, name=f"pressure-valve-in-{item.identifier}")
        device.valve_coeff = item.coefficient_kg_s_pa
        device.time_function = valve_opening
        inlet_reservoirs.append(reservoir)
        inlet_devices.append(device)

    for item in boundary.nozzle_inlets:
        properties = item.nozzle.properties
        properties._check_definition()
        if properties.mechanism_basis != mechanism_basis:
            raise ValueError("Nozzle and reacting cylinder must use the same declared Cantera mechanism basis")
        feed_phase = phase_factory()
        if not isinstance(feed_phase, ct.Solution) or feed_phase.thermo_model != "ideal-gas":
            raise ValueError("Nozzle source factory must return a native ideal-gas Solution")
        if (feed_phase.n_species != phase.n_species
                or tuple(feed_phase.species_names) != tuple(phase.species_names)
                or tuple(feed_phase.element_names) != tuple(phase.element_names)):
            raise ValueError("Nozzle source and cylinder phases must use identical species and element order")
        if not set(item.state.mole_fractions) <= set(feed_phase.species_names):
            raise ValueError(f"Nozzle source {item.identifier!r} declares unavailable native species")
        mechanism_basis.require_state(item.state.temperature_k, item.state.pressure_pa)
        feed_phase.TPX = item.state.temperature_k, item.state.pressure_pa, dict(item.state.mole_fractions)
        if not feed_phase.min_temp <= feed_phase.T <= feed_phase.max_temp:
            raise ValueError(f"Nozzle source {item.identifier!r} is outside native thermo limits")
        if _cantera_fingerprint(_cantera_phase_identity(feed_phase)) != properties.phase_sha256:
            raise ValueError("Nozzle property phase differs from the source/cylinder native thermochemistry")
        declared_y = np.asarray([properties.mass_fractions.get(name, 0.)
                                 for name in feed_phase.species_names], dtype=float)
        if not np.allclose(feed_phase.Y, declared_y, rtol=1e-12, atol=1e-14):
            raise ValueError("Nozzle frozen-property composition differs from the fixed native source state")
        upstream_state = properties.state_pt(item.state.pressure_pa, item.state.temperature_k)
        if (upstream_state.phase != "gas"
                or not np.isclose(upstream_state.density_kg_m3, feed_phase.density_mass,
                                  rtol=1e-10, atol=1e-12)
                or not np.isclose(upstream_state.enthalpy_j_kg, feed_phase.enthalpy_mass,
                                  rtol=1e-10, atol=1e-7)):
            raise ValueError("Nozzle source state differs from the native reservoir property basis")
        reservoir = ct.Reservoir(feed_phase, clone=True, name=f"nozzle-feed-{item.identifier}")
        nozzle_upstream_states[item.identifier] = upstream_state

        def nozzle_rate(time_s, source=item):
            nonlocal boundary_error
            try:
                current_time = finite(time_s, "nozzle callback time")
                back_pressure = finite(reactor.phase.P, "native cylinder backpressure", positive=True)
                cached = nozzle_cache.get(source.identifier)
                if (cached is not None and cached[0] == current_time
                        and cached[1] == back_pressure):
                    return float(cached[2].mass_flow_kg_s)
                fraction = float(source.opening_schedule.at(current_time))
                result = source.nozzle.solve(
                    nozzle_upstream_states[source.identifier],
                    back_pressure_pa=back_pressure,
                    opening=source.opening,
                    opening_fraction=fraction,
                )
                nozzle_cache[source.identifier] = (current_time, back_pressure, result)
                return float(result.mass_flow_kg_s)
            except Exception as exc:
                boundary_error = exc
                raise

        device = ct.MassFlowController(
            reservoir, reactor, mdot=nozzle_rate,
            name=f"shared-nozzle-inlet-{item.identifier}",
        )
        inlet_reservoirs.append(reservoir)
        inlet_devices.append(device)

    for item in boundary.outlets:
        sink_phase = phase_factory()
        if not isinstance(sink_phase, ct.Solution) or sink_phase.thermo_model != "ideal-gas":
            raise ValueError("Outlet sink factory must return an ideal-gas Solution")
        if (sink_phase.n_species != phase.n_species
                or tuple(sink_phase.species_names) != tuple(phase.species_names)):
            raise ValueError("Outlet sink and cylinder phases must use identical species order")
        sink_phase.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
        reservoir = ct.Reservoir(sink_phase, clone=True, name=f"sink-{item.identifier}")
        def outlet_rate(time_s, schedule=item.mass_flow):
            nonlocal boundary_error
            try:
                return float(schedule.at(time_s))
            except Exception as exc:
                boundary_error = exc
                raise

        device = ct.MassFlowController(
            reactor, reservoir,
            mdot=outlet_rate,
            name=f"outlet-rate-{item.identifier}",
        )
        outlet_reservoirs.append(reservoir)
        outlet_devices.append(device)

    for item in boundary.valve_outlets:
        sink_phase = phase_factory()
        if not isinstance(sink_phase, ct.Solution) or sink_phase.thermo_model != "ideal-gas":
            raise ValueError("Valve-outlet factory must return a native ideal-gas Solution")
        if (sink_phase.n_species != phase.n_species
                or tuple(sink_phase.species_names) != tuple(phase.species_names)):
            raise ValueError("Valve sink and cylinder phases must use identical species order")
        sink_phase.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
        reservoir = ct.Reservoir(sink_phase, clone=True, name=f"valve-sink-{item.identifier}")

        def valve_opening(time_s, schedule=item.opening):
            nonlocal boundary_error
            try:
                return float(schedule.at(time_s))
            except Exception as exc:
                boundary_error = exc
                raise

        device = ct.Valve(reactor, reservoir, name=f"pressure-valve-out-{item.identifier}")
        device.valve_coeff = item.coefficient_kg_s_pa
        device.time_function = valve_opening
        outlet_reservoirs.append(reservoir)
        outlet_devices.append(device)

    flow_devices = tuple((*inlet_devices, *outlet_devices))
    reservoirs = tuple((*inlet_reservoirs, *outlet_reservoirs, ambient))
    network = ct.ReactorNet([reactor])
    network.initial_time = origin
    # Reactor volume is itself an integrated state driven by the moving wall.
    # Integrate more tightly than the caller-facing geometry-consistency
    # budget so accumulated wall-volume error stays inside that declared bound.
    network.rtol = float(relative_tolerance) * 0.1
    network.atol = float(absolute_tolerance) * 0.1
    samples = []

    def add_sample(target_time, angle):
        nonlocal boundary_error
        if boundary_error is not None:
            raise ValueError("A native flow callback rejected its input") from boundary_error
        mechanism_basis.require_state(reactor.T, reactor.phase.P)
        if not reactor.phase.min_temp <= reactor.T <= reactor.phase.max_temp:
            raise ValueError("Accepted engine state exceeded native species thermodynamic limits")
        expected_volume = float(geometry.volume_m3(angle))
        volume_residual = float(reactor.volume - expected_volume)
        volume_tolerance = float(absolute_tolerance
                                + relative_tolerance * abs(expected_volume))
        if abs(volume_residual) > volume_tolerance:
            raise ValueError(
                "Accepted native cylinder volume differs from slider-crank geometry: "
                f"native={reactor.volume:.17g} m^3, geometry={expected_volume:.17g} m^3, "
                f"residual={volume_residual:.6g} m^3, solver-scaled allowance="
                f"{volume_tolerance:.6g} m^3 (rtol={relative_tolerance:.3g}, "
                f"atol={absolute_tolerance:.3g})"
            )
        rate = _flow_rates(boundary, flow_devices, inlet_reservoirs,
                           reactor, tuple(reactor.phase.species_names))
        row = (*_snapshot(reactor, geometry, angle, target_time,
                          tuple(reactor.phase.species_names)), *rate)
        if wall_thermal is not None:
            wall_temperature = float(reactor._h2_wall_temperature_k)
            row += (wall_temperature,
                    wall_thermal.heat_capacity_j_k * (
                        wall_temperature-wall_thermal.reference_temperature_k),
                    float(reactor._h2_wall_heat_into_wall_j),
                    float(reactor._h2_wall_boundary_heat_j))
        if boundary.nozzle_inlets:
            accepted_nozzles = []
            nozzle_device_start = len(boundary.inlets) + len(boundary.valve_inlets)
            current_pressure = float(reactor.phase.P)
            for offset, item in enumerate(boundary.nozzle_inlets):
                cached = nozzle_cache.get(item.identifier)
                if (cached is None or cached[0] != float(target_time)
                        or cached[1] != current_pressure):
                    fraction = float(item.opening_schedule.at(float(target_time)))
                    result = item.nozzle.solve(
                        nozzle_upstream_states[item.identifier],
                        back_pressure_pa=current_pressure,
                        opening=item.opening,
                        opening_fraction=fraction,
                    )
                    nozzle_cache[item.identifier] = (float(target_time), current_pressure, result)
                else:
                    result = cached[2]
                device_rate = float(inlet_devices[nozzle_device_start+offset].mass_flow_rate)
                if not np.isclose(device_rate, result.mass_flow_kg_s, rtol=1e-12, atol=1e-14):
                    raise ValueError("Native nozzle mass-flow adapter differs from the shared nozzle result")
                source_energy_rate = (device_rate
                                      * float(inlet_reservoirs[nozzle_device_start+offset].phase.enthalpy_mass))
                if not np.isclose(source_energy_rate, result.withdrawal_energy_w,
                                  rtol=1e-10, atol=1e-7):
                    raise ValueError("Native nozzle feed enthalpy differs from the shared source energy rate")
                accepted_nozzles.append(result)
            row += (tuple(accepted_nozzles),)
        samples.append(row)

    try:
        network.advance(float(times[0]))
        add_sample(times[0], angles[0])
        for target_time, angle in zip(times[1:], angles[1:], strict=True):
            try:
                network.advance(float(target_time))
            except Exception as exc:
                boundary_error = boundary_error or exc
                raise
            add_sample(target_time, angle)
    except Exception as cause:
        raise OpenCylinderEngineError(
            cause, native_reactor=reactor, native_network=network, native_wall=wall,
            native_flow_devices=flow_devices, native_reservoirs=reservoirs,
            accepted_prefix=tuple(samples),
            failed_target_s=float(times[min(len(samples), len(times) - 1)]),
        ) from cause

    data = tuple(zip(*samples, strict=True))
    # Snapshot columns 0..7 are state, column 8 is species transfer rate,
    # followed by inlet/outlet mass and enthalpy rates.
    state = [np.asarray(data[index]) for index in range(7)]
    species_rate = np.vstack(data[8])
    inlet_mass_rate = np.asarray(data[9])
    outlet_mass_rate = np.asarray(data[10])
    inlet_h_rate = np.asarray(data[11])
    outlet_h_rate = np.asarray(data[12])
    sample_times = state[1]
    species_transfer = np.column_stack([
        _cumulative(sample_times, species_rate[:, index])
        for index in range(species_rate.shape[1])
    ])
    inlet_h = _cumulative(sample_times, inlet_h_rate)
    outlet_h = _cumulative(sample_times, outlet_h_rate)
    work_rate = state[3] * np.asarray(geometry.volume_rate_m3_s(state[0]), dtype=float)
    work = _cumulative(sample_times, work_rate)
    mass_transfer = _cumulative(sample_times, inlet_mass_rate - outlet_mass_rate)
    mass_residual = state[5] - state[5][0] - mass_transfer
    if wall_thermal is None:
        wall_temperature = wall_internal_energy = gas_wall_into_gas = wall_boundary_heat = None
        energy_residual = state[6] - state[6][0] + work - inlet_h + outlet_h
    else:
        wall_temperature = np.asarray(data[13], dtype=float)
        wall_internal_energy = np.asarray(data[14], dtype=float)
        gas_wall_into_gas = -np.asarray(data[15], dtype=float)
        wall_boundary_heat = np.asarray(data[16], dtype=float)
        energy_residual = (state[6] - state[6][0]
                           + wall_internal_energy-wall_internal_energy[0]
                           + work - inlet_h + outlet_h - wall_boundary_heat)
    if boundary.nozzle_inlets:
        nozzle_column = 13 + (4 if wall_thermal is not None else 0)
        nozzle_history = tuple(data[nozzle_column])
    else:
        nozzle_history = ()
    token = _issue_trace()
    return OpenCylinderEngineTrace(
        crank_angle_rad=state[0], time_s=sample_times, volume_m3=state[2],
        pressure_pa=state[3], temperature_k=state[4], mass_kg=state[5],
        internal_energy_j=state[6], species_names=tuple(reactor.phase.species_names),
        mass_fractions=np.vstack(data[7]), species_transfer_kg=species_transfer,
        inlet_enthalpy_transfer_j=inlet_h, outlet_enthalpy_transfer_j=outlet_h,
        pressure_volume_work_j=work, mass_balance_residual_kg=mass_residual,
        sampled_first_law_residual_j=energy_residual, mechanism_basis=mechanism_basis,
        geometry=geometry, boundary=boundary, absolute_clock_origin_s=origin,
        native_reactor=reactor, native_network=network, native_wall=wall,
        native_flow_devices=flow_devices, native_reservoirs=reservoirs,
        _issuer_token=token,
        wall_thermal=wall_thermal, wall_temperature_k=wall_temperature,
        wall_internal_energy_j=wall_internal_energy,
        gas_wall_heat_into_gas_j=gas_wall_into_gas,
        wall_boundary_heat_j=wall_boundary_heat,
        nozzle_results=nozzle_history,
    )
