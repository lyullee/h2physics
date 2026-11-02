"""Native finite gas/ideal-surface kinetics at prescribed common temperature.

Cantera Interface, ReactorSurface and ReactorNet own every kinetic equation and
integration step. Gas and adsorbate elemental inventory are audited together.
Endpoint internal-energy change is thermostat demand, not predicted heat transfer.
References: https://cantera.org/3.2/python/zerodim.html and
https://cantera.org/3.2/python/thermo.html
"""

import hashlib
from dataclasses import dataclass, field

import numpy as np

from ..core import immutable_array, finite
from .cantera import MechanismBasis, NativeMechanismSource, ReactiveState
from .result_provenance import recorded_content_sha256


def _readonly(value):
    result = np.array(value, dtype=float, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError("Native surface-reactor observation must be finite")
    result = immutable_array(result, name="result")
    return result


def _surface_internal_energy_j(surface, species_amount_mol):
    """Return ideal-surface U from Cantera's supported partial molar enthalpies.

    Cantera's ideal surface has no pressure-volume contribution, so H equals U.
    The property is J/kmol; inventories are supplied as mol and converted to kmol.
    """
    partial_enthalpy_j_kmol = np.asarray(surface.partial_molar_enthalpies, dtype=float)
    amount = np.asarray(species_amount_mol, dtype=float)
    if (partial_enthalpy_j_kmol.shape != amount.shape
            or not np.all(np.isfinite(partial_enthalpy_j_kmol))
            or not np.all(np.isfinite(amount))):
        raise ValueError("Native surface enthalpy and species inventory arrays must be finite and aligned")
    return float(np.dot(amount/1000., partial_enthalpy_j_kmol))


@dataclass(frozen=True, slots=True)
class CatalyticSurfacePoint:
    time_s: float
    pressure_pa: float
    temperature_k: float
    gas_species_mol: object
    surface_species_mol: object
    coverages: object
    element_inventory_mol: object
    combined_internal_energy_j: float
    required_thermostat_heat_into_j: float | None
    maximum_element_residual_mol: float
    site_fraction_residual: float
    wall_heat_rate_into_w: float | None = None
    wall_heat_integral_into_j: float | None = None
    wall_energy_residual_j: float | None = None


@dataclass(frozen=True, slots=True)
class CatalyticThermalBoundary:
    """Fixed-temperature external wall coupled to a nonisothermal native reactor."""

    evidence_id: str
    wall_temperature_k: float
    area_m2: float
    heat_transfer_w_m2_k: float
    energy_residual_absolute_tolerance_j: float
    energy_residual_relative_tolerance: float = 1e-6

    def __post_init__(self):
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify the fixed-wall thermal boundary evidence")
        for name in ("wall_temperature_k", "area_m2", "heat_transfer_w_m2_k",
                     "energy_residual_absolute_tolerance_j",
                     "energy_residual_relative_tolerance"):
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class CatalyticFlowBoundary:
    """Fixed gas feed and pressure-controlled discharge for a stirred reactor.

    The inlet composition and thermodynamic state are held by a native Cantera
    Reservoir. The native mass-flow controller fixes the feed rate; a native
    PressureController discharges to the declared outlet pressure. This is a
    stirred control volume, not a plug-flow or pressure-drop model.
    """

    evidence_id: str
    feed_state: ReactiveState
    feed_mass_flow_kg_s: float
    outlet_pressure_pa: float
    pressure_controller_kg_s_pa: float
    mass_balance_tolerance_kg: float
    element_balance_tolerance_mol: float
    energy_balance_tolerance_j: float

    def __post_init__(self):
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify the feed/outlet boundary evidence")
        if type(self.feed_state) is not ReactiveState:
            raise TypeError("feed_state must be the shared ReactiveState")
        for name in ("feed_mass_flow_kg_s", "outlet_pressure_pa",
                     "pressure_controller_kg_s_pa", "mass_balance_tolerance_kg",
                     "element_balance_tolerance_mol", "energy_balance_tolerance_j"):
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class CatalyticFlowPoint:
    """Accepted native stirred-reactor state and sampled cumulative port ledger."""

    time_s: float
    pressure_pa: float
    temperature_k: float
    gas_species_mol: object
    surface_species_mol: object
    element_inventory_mol: object
    site_fraction_residual: float
    cumulative_inlet_element_mol: object
    cumulative_outlet_element_mol: object
    element_residual_mol: object
    inlet_mass_flow_kg_s: float
    outlet_mass_flow_kg_s: float
    cumulative_inlet_mass_kg: float
    cumulative_outlet_mass_kg: float
    mass_residual_kg: float
    combined_internal_energy_j: float
    cumulative_inlet_enthalpy_j: float
    cumulative_outlet_enthalpy_j: float
    wall_heat_rate_into_w: float
    cumulative_wall_heat_into_j: float
    energy_residual_j: float


@dataclass(frozen=True, slots=True)
class CatalyticFlowTrace:
    """Native finite-flow catalytic CSTR history with sampled flux closure."""

    owner: object
    clock_id: str
    evidence_id: str
    flow_boundary: CatalyticFlowBoundary
    thermal_boundary: CatalyticThermalBoundary
    surface_area_m2: float
    gas_volume_m3: float
    site_fraction_tolerance: float
    points: tuple
    native_gas: object
    native_interface: object
    native_reactor: object
    native_surface: object
    native_network: object
    native_inlet_reservoir: object
    native_outlet_reservoir: object
    native_inlet_controller: object
    native_outlet_controller: object
    native_wall: object
    native_thermal_reservoir: object
    _issuer_token: object = field(repr=False, compare=False)
    _signature: str = field(init=False, repr=False)

    def __post_init__(self):
        if type(self.owner) is not CanteraCatalyticSurfaceReactor:
            raise TypeError("Retain the original catalytic native owner")
        if not self.owner._consume_trace_token(self._issuer_token):
            raise TypeError("Create flow traces only through a completed native run")
        if type(self.flow_boundary) is not CatalyticFlowBoundary or type(
                self.thermal_boundary) is not CatalyticThermalBoundary:
            raise TypeError("Retain the exact typed flow and thermal boundary inputs")
        site_budget = finite(self.site_fraction_tolerance,
                             "site_fraction_tolerance", positive=True)
        points = tuple(self.points)
        if len(points) < 2 or any(type(point) is not CatalyticFlowPoint for point in points):
            raise TypeError("Retain every accepted catalytic flow observation")
        if any(points[i].time_s >= points[i + 1].time_s for i in range(len(points) - 1)):
            raise ValueError("Flow observation times must increase")
        for point in points:
            if (np.max(np.abs(point.element_residual_mol))
                    > self.flow_boundary.element_balance_tolerance_mol
                    or abs(point.site_fraction_residual) > site_budget
                    or abs(point.mass_residual_kg) > self.flow_boundary.mass_balance_tolerance_kg
                    or abs(point.energy_residual_j)
                    > self.flow_boundary.energy_balance_tolerance_j):
                raise ValueError("Sampled finite-flow material or energy ledger exceeds its budget")
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        return recorded_content_sha256((
            self.owner._configuration(), self.clock_id, self.evidence_id,
            self.flow_boundary, self.thermal_boundary, self.surface_area_m2,
            self.gas_volume_m3, self.site_fraction_tolerance, self.points,
            tuple(id(value) for value in (self.native_gas, self.native_interface,
                  self.native_reactor, self.native_surface, self.native_network,
                  self.native_inlet_reservoir, self.native_outlet_reservoir,
                  self.native_inlet_controller, self.native_outlet_controller,
                  self.native_wall, self.native_thermal_reservoir)),
            tuple(float(value) for value in self.native_gas.state),
            tuple(float(value) for value in self.native_interface.state),
            tuple(float(value) for value in self.native_surface.coverages),
            self.native_reactor.mass, self.native_reactor.volume, self.native_network.time,
            self.native_inlet_controller.mass_flow_rate,
            self.native_outlet_controller.mass_flow_rate, self.native_wall.heat_rate,
            self.native_outlet_controller.primary is self.native_inlet_controller,
            self.native_outlet_reservoir.phase.P,
            tuple(float(value) for value in self.native_inlet_reservoir.phase.state),
            tuple(float(value) for value in self.native_outlet_reservoir.phase.state),
            tuple(float(value) for value in self.native_thermal_reservoir.phase.state),
            self.native_outlet_controller.pressure_coeff,
            self.native_wall.area, self.native_wall.heat_transfer_coeff,
        ))

    def require_current(self):
        if (self._content() != self._signature
                or self.native_surface.reactor is not self.native_reactor
                or self.native_reactor.phase is not self.native_gas
                or self.native_surface.phase is not self.native_interface
                or self.native_inlet_controller.upstream is not self.native_inlet_reservoir
                or self.native_inlet_controller.downstream is not self.native_reactor
                or self.native_outlet_controller.upstream is not self.native_reactor
                or self.native_outlet_controller.downstream is not self.native_outlet_reservoir
                or self.native_outlet_controller.primary is not self.native_inlet_controller
                or self.native_wall.left_reactor is not self.native_reactor
                or self.native_wall.right_reactor is not self.native_thermal_reservoir):
            raise ValueError("Native catalytic flow objects or accepted ledger changed")
        return self


@dataclass(frozen=True, slots=True)
class CatalyticSurfaceSpeciesSeries:
    """One exact phase/species inventory projected from native accepted points."""

    trace: object
    phase: str
    species_id: str
    time_s: object
    amount_mol: object
    _signature: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.trace) is not CatalyticSurfaceTrace:
            raise TypeError("A species series must retain its original catalytic trace")
        self.trace.require_current()
        if self.phase not in {"gas", "surface"}:
            raise ValueError("Select the native gas or surface species inventory")
        native = self.trace.native_gas if self.phase == "gas" else self.trace.native_interface
        names = tuple(native.species_names)
        if not isinstance(self.species_id, str) or self.species_id not in names:
            raise KeyError(f"Unknown {self.phase} species identity: {self.species_id}")
        index = names.index(self.species_id)
        points = self.trace.points
        expected_time = np.asarray([point.time_s for point in points], dtype=float)
        source_values = ("gas_species_mol" if self.phase == "gas"
                         else "surface_species_mol")
        expected_amount = np.asarray(
            [getattr(point, source_values)[index] for point in points], dtype=float,
        )
        time = _readonly(self.time_s)
        amount = _readonly(self.amount_mol)
        if (time.shape != expected_time.shape or amount.shape != expected_amount.shape
                or not np.array_equal(time, expected_time)
                or not np.array_equal(amount, expected_amount)):
            raise ValueError("Species series must reconstruct exactly from original native observations")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "amount_mol", amount)
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.trace), self.phase, self.species_id,
            self.time_s.tobytes(order="C"), self.amount_mol.tobytes(order="C"),
        ))

    def require_current(self):
        self.trace.require_current()
        native = self.trace.native_gas if self.phase == "gas" else self.trace.native_interface
        names = tuple(native.species_names)
        if self.species_id not in names:
            raise ValueError("Original catalytic species identity is no longer available")
        index = names.index(self.species_id)
        source_values = ("gas_species_mol" if self.phase == "gas"
                         else "surface_species_mol")
        expected = np.asarray(
            [getattr(point, source_values)[index] for point in self.trace.points], dtype=float,
        )
        expected_time = np.asarray([point.time_s for point in self.trace.points], dtype=float)
        if (self._content() != self._signature
                or not np.array_equal(self.time_s, expected_time)
                or not np.array_equal(self.amount_mol, expected)):
            raise ValueError("Catalytic species series no longer matches its original native trace")
        return self


@dataclass(frozen=True, slots=True)
class CatalyticSurfaceTrace:
    owner: object
    clock_id: str
    evidence_id: str
    mechanism_basis: MechanismBasis
    surface_area_m2: float
    gas_volume_m3: float
    points: tuple
    native_gas: object
    native_interface: object
    native_reactor: object
    native_surface: object
    native_network: object
    _issuer_token: object = field(repr=False, compare=False)
    thermal_scope: str = "prescribed-isothermal; endpoint thermostat demand; no catalyst bulk thermal storage"
    thermal_boundary: CatalyticThermalBoundary | None = None
    native_wall: object | None = field(default=None, repr=False, compare=False)
    native_reservoir: object | None = field(default=None, repr=False, compare=False)
    _signature: str = field(init=False, repr=False)

    def __post_init__(self):
        if type(self.owner) is not CanteraCatalyticSurfaceReactor:
            raise TypeError("Retain the original native catalytic reactor owner")
        if not self.owner._consume_trace_token(self._issuer_token):
            raise TypeError("Create catalytic traces through a completed native run")
        if (not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not isinstance(self.evidence_id, str) or not self.evidence_id.strip()
                or type(self.mechanism_basis) is not MechanismBasis):
            raise ValueError("A native catalytic trace needs its original basis, clock and evidence")
        points = tuple(self.points)
        if len(points) < 2 or any(type(point) is not CatalyticSurfacePoint for point in points):
            raise TypeError("Retain every accepted native catalytic observation point")
        if any(points[index].time_s >= points[index + 1].time_s
               for index in range(len(points) - 1)):
            raise ValueError("Catalytic observation times must remain strictly increasing")
        if self.thermal_boundary is None:
            if self.native_wall is not None or self.native_reservoir is not None:
                raise ValueError("A native wall and reservoir require a declared thermal boundary")
        else:
            if (type(self.thermal_boundary) is not CatalyticThermalBoundary
                    or self.native_wall is None or self.native_reservoir is None
                    or self.native_wall.left_reactor is not self.native_reactor
                    or self.native_wall.right_reactor is not self.native_reservoir
                    or self.native_wall.area != self.thermal_boundary.area_m2
                    or self.native_wall.heat_transfer_coeff
                       != self.thermal_boundary.heat_transfer_w_m2_k
                    or self.native_reservoir.phase.T
                       != self.thermal_boundary.wall_temperature_k):
                raise ValueError("Thermal trace must retain its exact native wall/reservoir boundary")
            cumulative = 0.0
            for index, point in enumerate(points):
                if (point.required_thermostat_heat_into_j is not None
                        or point.wall_heat_rate_into_w is None
                        or point.wall_heat_integral_into_j is None
                        or point.wall_energy_residual_j is None):
                    raise ValueError("A wall-coupled point must retain wall heat, not thermostat demand")
                for name in ("wall_heat_rate_into_w", "wall_heat_integral_into_j",
                             "wall_energy_residual_j"):
                    finite(getattr(point, name), name)
                if index:
                    left, right = points[index-1], point
                    cumulative += (right.time_s-left.time_s) * (
                        left.wall_heat_rate_into_w+right.wall_heat_rate_into_w) * .5
                delta_u = point.combined_internal_energy_j-points[0].combined_internal_energy_j
                if (point.wall_heat_integral_into_j != cumulative
                        or point.wall_energy_residual_j != delta_u-cumulative):
                    raise ValueError("Wall energy series does not reconstruct from retained points")
        if self.thermal_boundary is None and any(point.wall_heat_rate_into_w is not None
                 or point.wall_heat_integral_into_j is not None
                 or point.wall_energy_residual_j is not None
                 for point in points):
            raise ValueError("An isothermal trace cannot carry a native wall-energy ledger")
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        return recorded_content_sha256((
            self.owner._configuration(), self.clock_id, self.evidence_id,
            self.mechanism_basis, self.surface_area_m2, self.gas_volume_m3, self.points,
            tuple(id(value) for value in (self.native_gas, self.native_interface,
                  self.native_reactor, self.native_surface, self.native_network)),
            tuple(float(value) for value in self.native_gas.state),
            tuple(float(value) for value in self.native_interface.state),
            tuple(float(value) for value in self.native_surface.coverages), self.native_surface.area,
            self.native_reactor.mass, self.native_reactor.volume, self.native_network.time,
            self.thermal_scope, self.thermal_boundary,
            id(self.native_wall), id(self.native_reservoir),
            None if self.native_wall is None else self.native_wall.heat_rate,
            None if self.native_wall is None else self.native_wall.area,
            None if self.native_wall is None else self.native_wall.heat_transfer_coeff,
            None if self.native_reservoir is None else tuple(float(v) for v in self.native_reservoir.phase.state),
        ))

    def require_current(self):
        if (self._content() != self._signature or self.native_surface.reactor is not self.native_reactor
                or self.native_reactor.phase is not self.native_gas
                or self.native_surface.phase is not self.native_interface):
            raise ValueError("Original catalytic native owner, terminal state or output ledger changed")
        return self

    def species_inventory_series(self, species_id: str, *, phase: str):
        """Project one gas or adsorbate species along the exact accepted clock."""
        self.require_current()
        if phase not in {"gas", "surface"}:
            raise ValueError("Select phase='gas' or phase='surface'")
        native = self.native_gas if phase == "gas" else self.native_interface
        names = tuple(native.species_names)
        if not isinstance(species_id, str) or species_id not in names:
            raise KeyError(f"Unknown {phase} species identity: {species_id}")
        index = names.index(species_id)
        source_values = "gas_species_mol" if phase == "gas" else "surface_species_mol"
        return CatalyticSurfaceSpeciesSeries(
            self, phase, species_id,
            [point.time_s for point in self.points],
            [getattr(point, source_values)[index] for point in self.points],
        ).require_current()


class CatalyticSurfaceError(RuntimeError):
    def __init__(self, cause, owner, completed, native_objects):
        self.cause, self.owner = cause, owner
        self.completed_points = tuple(completed)
        self.native_objects = native_objects
        super().__init__("Native finite gas/surface kinetic integration failed")


class CanteraCatalyticSurfaceReactor:
    """Closed finite gas and evolving adsorbate stock on a native ideal surface."""

    def __init__(self, source, mechanism_basis, *, surface_phase_name, gas_phase_name):
        if type(source) is not NativeMechanismSource or type(mechanism_basis) is not MechanismBasis:
            raise TypeError("Supply original mechanism bytes and explicit rights/domain basis")
        if hashlib.sha256(source.source_bytes).hexdigest() != mechanism_basis.source_sha256:
            raise ValueError("Native mechanism source differs from the declared SHA-256")
        for value in (surface_phase_name, gas_phase_name):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Declare actual surface and adjacent gas phase names")
        if source.phase_name != gas_phase_name:
            raise ValueError("Native source gas phase identity differs from the requested adjacency")
        self.source, self.basis = source, mechanism_basis
        self.surface_phase_name, self.gas_phase_name = surface_phase_name, gas_phase_name
        self._pending_trace_tokens = set()

    def _configuration(self):
        return recorded_content_sha256((id(self), self.source, self.basis,
                                        self.surface_phase_name, self.gas_phase_name))

    def _issue_trace_token(self):
        token = object()
        self._pending_trace_tokens.add(token)
        return token

    def _consume_trace_token(self, token):
        if token not in self._pending_trace_tokens:
            return False
        self._pending_trace_tokens.remove(token)
        return True

    def run(self, initial, time_s, *, initial_coverages, surface_area_m2, gas_volume_m3,
            clock_id, evidence_id, maximum_time_step_s, relative_tolerance,
            absolute_tolerance, element_absolute_tolerance_mol,
            site_fraction_tolerance, minimum_gas_mass_kg,
            thermal_boundary: CatalyticThermalBoundary | None = None):
        """Advance native surface kinetics, optionally coupled to fixed-wall heat exchange.

        Without ``thermal_boundary`` this retains the original isothermal level.
        When supplied, Cantera solves the gas energy equation and one finite-area,
        fixed-temperature external wall; its thermal reservoir has no stored state.
        """
        import cantera as ct

        if tuple(int(v) for v in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("This source contract admits native Cantera 3.2")
        if type(initial) is not ReactiveState:
            raise TypeError("Use the common explicit ReactiveState")
        times = _readonly(time_s)
        if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0):
            raise ValueError("Declare strictly increasing physical output times")
        for value in (clock_id, evidence_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Declare physical clock and isothermal/kinetic applicability evidence")
        area = finite(surface_area_m2, "surface area m2", positive=True)
        volume = finite(gas_volume_m3, "gas volume m3", positive=True)
        dt = finite(maximum_time_step_s, "maximum native step s", positive=True)
        element_budget = finite(element_absolute_tolerance_mol, "element budget mol", positive=True)
        site_budget = finite(site_fraction_tolerance, "site normalization budget", positive=True)
        mass_floor = finite(minimum_gas_mass_kg, "gas mass floor kg", positive=True)
        rtol = finite(relative_tolerance, "relative tolerance", positive=True)
        atol = finite(absolute_tolerance, "absolute tolerance", positive=True)
        self.basis.require_state(initial.temperature_k, initial.pressure_pa)
        if thermal_boundary is not None:
            if type(thermal_boundary) is not CatalyticThermalBoundary:
                raise TypeError("thermal_boundary must be a CatalyticThermalBoundary")
            self.basis.require_state(thermal_boundary.wall_temperature_k, initial.pressure_pa)
        original_configuration = self._configuration()
        completed, native_objects = [], None
        try:
            surface = ct.Interface(yaml=self.source.source_bytes.decode("utf-8"), name=self.surface_phase_name)
            native_objects = (None, surface)
            if (surface.thermo_model != "ideal-surface" or set(surface.adjacent) != {self.gas_phase_name}):
                raise ValueError("This level admits one ideal surface adjacent to one gas phase only")
            gas = surface.adjacent[self.gas_phase_name]
            native_objects = (gas, surface)
            if gas.thermo_model != "ideal-gas":
                raise ValueError("Use the native ideal-gas finite-volume reactor domain")
            gas.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
            surface.TP = initial.temperature_k, initial.pressure_pa
            coverage = dict(initial_coverages)
            if (set(coverage) != set(surface.species_names)
                    or any(finite(v, "surface coverage") < 0 for v in coverage.values())
                    or abs(sum(coverage.values())-1.) > site_budget):
                raise ValueError("Declare complete nonnegative normalized native surface coverages")
            surface.coverages = coverage
            reservoir = wall = None
            owner = self
            domain_errors = []
            class DomainReactor(ct.ExtensibleIdealGasReactor):
                def after_eval(self, time, lhs, rhs):
                    try:
                        if owner._configuration() != original_configuration:
                            raise ValueError("Catalytic source/domain changed during native RHS evaluation")
                        owner.basis.require_state(self.T, self.phase.P)
                        if finite(self.mass, "native trial gas mass kg", positive=True) <= mass_floor:
                            raise ValueError("Native catalytic gas inventory reached its explicit floor")
                    except Exception as cause:
                        domain_errors.append(cause)
                        raise

            reactor = DomainReactor(gas, energy="on" if thermal_boundary is not None else "off",
                                    volume=volume, clone=False)
            native_objects = (gas, surface, reactor)
            native_surface = ct.ReactorSurface(surface, reactor, A=area, clone=False)
            native_objects = (gas, surface, reactor, native_surface)
            if thermal_boundary is not None:
                reservoir_gas = ct.Solution(yaml=self.source.source_bytes.decode("utf-8"),
                                            name=self.gas_phase_name)
                reservoir_gas.TPX = (thermal_boundary.wall_temperature_k,
                                     initial.pressure_pa, dict(initial.mole_fractions))
                reservoir = ct.Reservoir(reservoir_gas, name="catalyst-thermal-boundary",
                                         clone=False)
                wall = ct.Wall(reactor, reservoir, A=thermal_boundary.area_m2,
                               U=thermal_boundary.heat_transfer_w_m2_k)
                native_objects = (*native_objects, wall, reservoir)
            network = ct.ReactorNet([reactor])
            native_objects = (gas, surface, reactor, native_surface, network,
                              *((wall, reservoir) if wall is not None else ()))
            network.initial_time = float(times[0])
            network.max_time_step, network.rtol, network.atol = dt, rtol, atol
            native_objects = (gas, surface, reactor, native_surface, network,
                              *((wall, reservoir) if wall is not None else ()))
            site_density = finite(surface.site_density, "native site density kmol/m2", positive=True)
            sizes = _readonly([surface.species(k).size for k in range(surface.n_species)])
            if np.any(sizes <= 0):
                raise ValueError("Native species site occupancies must be positive")
            elements = tuple(dict.fromkeys((*gas.element_names, *surface.element_names)))
            gas_atoms = np.array([[gas.n_atoms(k, e) if e in gas.element_names else 0.
                                   for k in range(gas.n_species)] for e in elements])
            surface_atoms = np.array([[surface.n_atoms(k, e) if e in surface.element_names else 0.
                                       for k in range(surface.n_species)] for e in elements])
            initial_elements = initial_energy = None
            previous_time = float(times[0])
            cumulative_wall_heat = 0.0
            previous_wall_heat = (-float(wall.heat_rate) if wall is not None else None)
            for time in times:
                if self._configuration() != original_configuration:
                    raise ValueError("Original catalytic mechanism/domain configuration changed")
                if float(time) != float(times[0]):
                    network.advance(float(time))
                if domain_errors:
                    raise ValueError("Native solver retried a rejected catalytic domain evaluation") from domain_errors[0]
                # Read the accepted integrator state through the native
                # reactor and ReactorSurface restoration APIs before checking
                # thermal agreement; the Python phase handles may otherwise
                # still expose their previous sampled state.
                reactor.restore_thermo_state()
                _ = native_surface.phase
                self.basis.require_state(gas.T, gas.P)
                finite(reactor.mass, "native gas mass kg", positive=True)
                finite(reactor.volume, "native volume m3", positive=True)
                finite(gas.T, "native gas temperature K", positive=True)
                finite(gas.P, "native gas pressure Pa", positive=True)
                if (reactor.mass <= mass_floor or abs(reactor.volume-volume) > 1e-12*volume
                        or (thermal_boundary is None
                            and abs(gas.T-initial.temperature_k) > 1e-10*initial.temperature_k)
                        or abs(surface.T-gas.T) > 1e-10*initial.temperature_k
                        or not np.isclose(surface.site_density, site_density, rtol=1e-12, atol=0.)):
                    raise ValueError("Native finite isothermal gas/surface domain changed")
                gas_mol = _readonly(reactor.mass*gas.Y/gas.molecular_weights*1000.)
                theta = _readonly(native_surface.coverages)
                surface_mol = _readonly(theta*site_density*area/sizes*1000.)
                site_residual = finite(float(np.sum(theta)-1.),
                                       "native surface site-fraction residual")
                if (np.any(gas_mol < -element_budget)
                        or np.any(theta < -site_budget)
                        or abs(site_residual) > site_budget):
                    raise ValueError("Native gas/surface state failed nonnegative/site-closure bounds")
                element_mol = _readonly(gas_atoms@gas_mol+surface_atoms@surface_mol)
                energy = finite(reactor.mass*gas.int_energy_mass
                    +_surface_internal_energy_j(surface, surface_mol), "combined gas/adsorbate U J")
                if initial_elements is None:
                    initial_elements, initial_energy = element_mol, energy
                element_error = float(np.max(np.abs(element_mol-initial_elements)))
                site_error = float(theta.sum()-1.)
                if np.any(gas_mol < -element_budget) or np.any(theta < -site_budget):
                    raise ValueError("Native finite gas/surface state became negative")
                if element_error > element_budget or abs(site_error) > site_budget:
                    raise ValueError("Native combined element or surface site balance failed")
                if wall is None:
                    completed.append(CatalyticSurfacePoint(float(time), gas.P, gas.T, gas_mol,
                        surface_mol, theta, element_mol, energy,
                        finite(energy-initial_energy, "required thermostat heat J"),
                        element_error, site_error))
                else:
                    wall_heat_into = finite(-float(wall.heat_rate), "wall heat into reactor W")
                    if previous_wall_heat is not None:
                        cumulative_wall_heat += (float(time)-previous_time) * (
                            previous_wall_heat + wall_heat_into) * 0.5
                    energy_change = finite(energy-initial_energy, "combined gas/adsorbate energy change J")
                    wall_residual = finite(energy_change-cumulative_wall_heat,
                                           "sampled wall-energy residual J")
                    allowed = (thermal_boundary.energy_residual_absolute_tolerance_j
                               + thermal_boundary.energy_residual_relative_tolerance
                               * max(abs(energy_change), abs(cumulative_wall_heat)))
                    if abs(wall_residual) > allowed:
                        raise ValueError("Sampled native wall heat does not close the gas/adsorbate energy ledger")
                    completed.append(CatalyticSurfacePoint(float(time), gas.P, gas.T, gas_mol,
                        surface_mol, theta, element_mol, energy, None,
                        element_error, site_error, wall_heat_into, cumulative_wall_heat,
                        wall_residual))
                    previous_wall_heat = wall_heat_into
                    previous_time = float(time)
            if self._configuration() != original_configuration:
                raise ValueError("Original catalytic source changed during native integration")
            token = self._issue_trace_token()
            gas, surface, reactor, native_surface, network = native_objects[:5]
            wall, reservoir = native_objects[5:] if len(native_objects) == 7 else (None, None)
            scope = ("prescribed-isothermal; endpoint thermostat demand; no catalyst bulk thermal storage"
                     if thermal_boundary is None else
                     "native gas/surface temperature feedback; fixed-temperature external wall; no wall/catalyst bulk thermal storage")
            return CatalyticSurfaceTrace(
                self, clock_id, evidence_id, self.basis, area, volume, tuple(completed),
                gas, surface, reactor, native_surface, network, token,
                thermal_scope=scope, thermal_boundary=thermal_boundary,
                native_wall=wall, native_reservoir=reservoir,
            ).require_current()
        except Exception as cause:
            raise CatalyticSurfaceError(cause, self, completed, native_objects) from cause

    def run_flowing_cstr(self, initial, time_s, *, initial_coverages,
                         surface_area_m2, gas_volume_m3, flow_boundary,
                         thermal_boundary, clock_id, evidence_id,
                         maximum_time_step_s, relative_tolerance,
                         absolute_tolerance, site_fraction_tolerance,
                         minimum_gas_mass_kg):
        """Run a native finite-feed, pressure-controlled, well-mixed reactor.

        Feed and exhaust are actual Cantera flow devices. The thermal boundary
        is required so the open-system energy balance includes native gas energy
        dynamics. Port integrals use the requested output grid and trapezoidal
        quadrature; refine that grid to reduce ledger quadrature error.
        """
        import cantera as ct

        if tuple(int(v) for v in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("This source contract admits native Cantera 3.2")
        if type(initial) is not ReactiveState:
            raise TypeError("Use the common explicit ReactiveState")
        if type(flow_boundary) is not CatalyticFlowBoundary:
            raise TypeError("Declare a CatalyticFlowBoundary")
        if type(thermal_boundary) is not CatalyticThermalBoundary:
            raise TypeError("A finite-flow catalytic run requires an explicit thermal boundary")
        times = _readonly(time_s)
        if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0.):
            raise ValueError("Declare strictly increasing physical output times")
        for value in (clock_id, evidence_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Declare physical clock and flow/mechanism evidence")
        area = finite(surface_area_m2, "surface area m2", positive=True)
        volume = finite(gas_volume_m3, "gas volume m3", positive=True)
        dt = finite(maximum_time_step_s, "maximum native step s", positive=True)
        rtol = finite(relative_tolerance, "relative tolerance", positive=True)
        atol = finite(absolute_tolerance, "absolute tolerance", positive=True)
        site_budget = finite(site_fraction_tolerance, "site normalization budget", positive=True)
        mass_floor = finite(minimum_gas_mass_kg, "gas mass floor kg", positive=True)
        self.basis.require_state(initial.temperature_k, initial.pressure_pa)
        self.basis.require_state(flow_boundary.feed_state.temperature_k,
                                 flow_boundary.feed_state.pressure_pa)
        self.basis.require_state(initial.temperature_k, flow_boundary.outlet_pressure_pa)
        self.basis.require_state(thermal_boundary.wall_temperature_k, initial.pressure_pa)
        if flow_boundary.outlet_pressure_pa >= initial.pressure_pa:
            raise ValueError("Initial reactor pressure must exceed the explicit outlet pressure")
        original_configuration = self._configuration()
        completed, native_objects = [], None
        try:
            surface = ct.Interface(yaml=self.source.source_bytes.decode("utf-8"),
                                    name=self.surface_phase_name)
            native_objects = (None, surface)
            if (surface.thermo_model != "ideal-surface"
                    or set(surface.adjacent) != {self.gas_phase_name}):
                raise ValueError("This level admits one ideal surface adjacent to one gas phase")
            gas = surface.adjacent[self.gas_phase_name]
            if gas.thermo_model != "ideal-gas":
                raise ValueError("Use the native ideal-gas stirred-reactor domain")
            gas.TPX = initial.temperature_k, initial.pressure_pa, dict(initial.mole_fractions)
            surface.TP = initial.temperature_k, initial.pressure_pa
            coverage = dict(initial_coverages)
            if (set(coverage) != set(surface.species_names)
                    or any(finite(v, "surface coverage") < 0. for v in coverage.values())
                    or abs(sum(coverage.values()) - 1.) > site_budget):
                raise ValueError("Declare complete normalized nonnegative native surface coverages")
            surface.coverages = coverage

            inlet_gas = ct.Solution(yaml=self.source.source_bytes.decode("utf-8"),
                                    name=self.gas_phase_name)
            inlet = flow_boundary.feed_state
            inlet_gas.TPX = inlet.temperature_k, inlet.pressure_pa, dict(inlet.mole_fractions)
            inlet_reservoir = ct.Reservoir(inlet_gas, name="catalytic-feed", clone=False)
            outlet_gas = ct.Solution(yaml=self.source.source_bytes.decode("utf-8"),
                                     name=self.gas_phase_name)
            outlet_gas.TPX = (initial.temperature_k, flow_boundary.outlet_pressure_pa,
                              dict(initial.mole_fractions))
            outlet_reservoir = ct.Reservoir(outlet_gas, name="catalytic-outlet", clone=False)
            thermal_gas = ct.Solution(yaml=self.source.source_bytes.decode("utf-8"),
                                       name=self.gas_phase_name)
            thermal_gas.TPX = (thermal_boundary.wall_temperature_k, initial.pressure_pa,
                               dict(initial.mole_fractions))
            thermal_reservoir = ct.Reservoir(thermal_gas,
                                              name="catalytic-thermal-boundary", clone=False)
            owner = self
            domain_errors = []

            class DomainReactor(ct.ExtensibleIdealGasReactor):
                def after_eval(self, time, lhs, rhs):
                    try:
                        if owner._configuration() != original_configuration:
                            raise ValueError("Catalytic mechanism changed during native integration")
                        owner.basis.require_state(self.T, self.phase.P)
                        if finite(self.mass, "native gas mass kg", positive=True) <= mass_floor:
                            raise ValueError("Native catalytic flow reactor reached its gas-mass floor")
                    except Exception as cause:
                        domain_errors.append(cause)
                        raise

            reactor = DomainReactor(gas, energy="on", volume=volume, clone=False)
            native_surface = ct.ReactorSurface(surface, reactor, A=area, clone=False)
            inlet_controller = ct.MassFlowController(
                inlet_reservoir, reactor, mdot=flow_boundary.feed_mass_flow_kg_s)
            outlet_controller = ct.PressureController(
                reactor, outlet_reservoir, primary=inlet_controller,
                K=flow_boundary.pressure_controller_kg_s_pa)
            wall = ct.Wall(reactor, thermal_reservoir, A=thermal_boundary.area_m2,
                           U=thermal_boundary.heat_transfer_w_m2_k)
            network = ct.ReactorNet([reactor])
            network.initial_time = float(times[0])
            network.max_time_step, network.rtol, network.atol = dt, rtol, atol
            # FlowDevice mass_flow_rate is defined only after ReactorNet has
            # initialized its reactor and flow-device graph. Initialize at the
            # declared first physical time without advancing the solution.
            network.initialize()
            native_objects = (gas, surface, reactor, native_surface, network,
                              inlet_reservoir, outlet_reservoir, inlet_controller,
                              outlet_controller, wall, thermal_reservoir)

            site_density = finite(surface.site_density, "native site density kmol/m2", positive=True)
            sizes = _readonly([surface.species(k).size for k in range(surface.n_species)])
            elements = tuple(dict.fromkeys((*gas.element_names, *surface.element_names)))
            gas_atoms = np.array([[gas.n_atoms(k, e) if e in gas.element_names else 0.
                                   for k in range(gas.n_species)] for e in elements])
            surf_atoms = np.array([[surface.n_atoms(k, e) if e in surface.element_names else 0.
                                    for k in range(surface.n_species)] for e in elements])
            feed_atoms = np.array([[inlet_gas.n_atoms(k, e) if e in inlet_gas.element_names else 0.
                                    for k in range(inlet_gas.n_species)] for e in elements])
            if np.any(sizes <= 0.):
                raise ValueError("Native surface species require positive site occupancies")
            cumulative_in_atoms = np.zeros(len(elements))
            cumulative_out_atoms = np.zeros(len(elements))
            cumulative_in_mass = cumulative_out_mass = 0.
            cumulative_in_h = cumulative_out_h = cumulative_wall = 0.
            prior_rates = None
            initial_elements = initial_energy = initial_total_mass = None
            previous_state = None
            for time in times:
                if self._configuration() != original_configuration:
                    raise ValueError("Original catalytic mechanism changed during integration")
                if float(time) != float(times[0]):
                    network.advance(float(time))
                if domain_errors:
                    raise ValueError("Native solver retried a rejected flow-domain evaluation") from domain_errors[0]
                # Cantera's ExtensibleReactor retains its integrator state
                # separately from the Python ThermoPhase handles. Restore the
                # gas phase from the accepted reactor state and use the
                # ReactorSurface.phase property to invoke its native restore
                # operation and publish accepted coverages and reactor
                # temperature to Interface.
                reactor.restore_thermo_state()
                _ = native_surface.phase
                # Check the shared native phase views without writing over
                # either integrated state.
                reactor_gas_temperature_error = abs(reactor.T-gas.T)
                if reactor_gas_temperature_error > 1e-10*reactor.T:
                    raise ValueError(
                        "Native catalytic CSTR reactor/gas temperature mismatch: "
                        f"reactor={reactor.T:.17g} K, gas={gas.T:.17g} K, "
                        f"difference={reactor_gas_temperature_error:.17g} K"
                    )
                self.basis.require_state(gas.T, gas.P)
                if abs(reactor.volume-volume) > 1e-12*volume:
                    raise ValueError(
                        "Native catalytic CSTR reactor volume changed: "
                        f"expected {volume:.17g} m3, received {reactor.volume:.17g} m3"
                    )
                if not np.isclose(surface.site_density, site_density, rtol=1e-12, atol=0.):
                    raise ValueError(
                        "Native catalytic CSTR surface site density changed: "
                        f"expected {site_density:.17g} kmol/m2, "
                        f"received {surface.site_density:.17g} kmol/m2"
                    )
                surface_temperature_error = abs(surface.T-gas.T)
                if surface_temperature_error > 1e-10*gas.T:
                    raise ValueError(
                        "Native catalytic CSTR surface and gas temperatures diverged: "
                        f"surface={surface.T:.17g} K, gas={gas.T:.17g} K, "
                        f"absolute difference={surface_temperature_error:.17g} K"
                    )
                gas_mol = _readonly(reactor.mass*gas.Y/gas.molecular_weights*1000.)
                theta = _readonly(native_surface.coverages)
                surface_mol = _readonly(theta*site_density*area/sizes*1000.)
                site_residual = finite(float(np.sum(theta)-1.),
                                       "native surface site-fraction residual")
                if (np.any(gas_mol < -flow_boundary.element_balance_tolerance_mol)
                        or np.any(theta < -site_budget)
                        or abs(site_residual) > site_budget):
                    raise ValueError("Native gas/surface state failed nonnegative/site-closure bounds")
                elements_now = _readonly(gas_atoms@gas_mol+surf_atoms@surface_mol)
                total_mass = finite(float(np.dot(gas_mol, gas.molecular_weights)
                                           + np.dot(surface_mol, surface.molecular_weights))/1000.,
                                     "gas plus adsorbate mass kg", positive=True)
                energy = finite(reactor.mass*gas.int_energy_mass
                                + _surface_internal_energy_j(surface, surface_mol),
                                "gas plus adsorbate internal energy J")
                inlet_rate = finite(inlet_controller.mass_flow_rate, "native inlet mass flow")
                outlet_rate = finite(outlet_controller.mass_flow_rate, "native outlet mass flow")
                if inlet_rate <= 0. or outlet_rate < 0.:
                    raise ValueError("The admitted CSTR path requires positive feed and nonreversing exhaust flow")
                inlet_element_rate = feed_atoms @ (
                    inlet_rate*inlet_gas.Y/inlet_gas.molecular_weights*1000.)
                outlet_element_rate = gas_atoms @ (
                    outlet_rate*gas.Y/gas.molecular_weights*1000.)
                inlet_h_rate = finite(inlet_rate*inlet_gas.enthalpy_mass,
                                      "native inlet enthalpy rate")
                outlet_h_rate = finite(outlet_rate*gas.enthalpy_mass,
                                       "native outlet enthalpy rate")
                wall_rate = finite(-float(wall.heat_rate), "wall heat into reactor")
                rates = (inlet_element_rate, outlet_element_rate, inlet_rate,
                         outlet_rate, inlet_h_rate, outlet_h_rate, wall_rate)
                if initial_elements is None:
                    initial_elements, initial_energy, initial_total_mass = (
                        elements_now.copy(), energy, total_mass)
                elif previous_state is not None:
                    elapsed = float(time)-previous_state[0]
                    for index in range(2):
                        prior, current = prior_rates[index], rates[index]
                        (cumulative_in_atoms if index == 0 else cumulative_out_atoms)[:] += (
                            .5*elapsed*(prior+current))
                    cumulative_in_mass += .5*elapsed*(prior_rates[2]+rates[2])
                    cumulative_out_mass += .5*elapsed*(prior_rates[3]+rates[3])
                    cumulative_in_h += .5*elapsed*(prior_rates[4]+rates[4])
                    cumulative_out_h += .5*elapsed*(prior_rates[5]+rates[5])
                    cumulative_wall += .5*elapsed*(prior_rates[6]+rates[6])
                element_residual = _readonly(
                    elements_now-initial_elements-cumulative_in_atoms+cumulative_out_atoms)
                mass_residual = finite(total_mass-initial_total_mass-cumulative_in_mass
                                       + cumulative_out_mass, "sampled total-mass residual kg")
                energy_residual = finite(energy-initial_energy-cumulative_wall
                                         - cumulative_in_h+cumulative_out_h,
                                         "sampled open-reactor energy residual J")
                energy_allowed = min(
                    flow_boundary.energy_balance_tolerance_j,
                    thermal_boundary.energy_residual_absolute_tolerance_j
                    + thermal_boundary.energy_residual_relative_tolerance
                    * max(abs(energy-initial_energy), abs(cumulative_wall),
                          abs(cumulative_in_h), abs(cumulative_out_h)),
                )
                if (np.max(np.abs(element_residual))
                        > flow_boundary.element_balance_tolerance_mol
                        or abs(mass_residual) > flow_boundary.mass_balance_tolerance_kg
                        or abs(energy_residual) > energy_allowed):
                    raise ValueError("Sampled finite-flow catalytic ledger exceeds an explicit budget")
                completed.append(CatalyticFlowPoint(
                    float(time), finite(gas.P, "reactor pressure Pa", positive=True),
                    finite(gas.T, "reactor temperature K", positive=True), gas_mol,
                    surface_mol, elements_now, site_residual, _readonly(cumulative_in_atoms),
                    _readonly(cumulative_out_atoms), element_residual, inlet_rate,
                    outlet_rate, cumulative_in_mass, cumulative_out_mass, mass_residual,
                    energy, cumulative_in_h, cumulative_out_h, wall_rate,
                    cumulative_wall, energy_residual,
                ))
                previous_state, prior_rates = (float(time), energy), rates
            if self._configuration() != original_configuration:
                raise ValueError("Original catalytic mechanism changed during integration")
            token = self._issue_trace_token()
            return CatalyticFlowTrace(
                self, clock_id, evidence_id, flow_boundary, thermal_boundary, area, volume,
                site_budget, tuple(completed), gas, surface, reactor, native_surface, network,
                inlet_reservoir, outlet_reservoir, inlet_controller, outlet_controller,
                wall, thermal_reservoir, token,
            ).require_current()
        except Exception as cause:
            raise CatalyticSurfaceError(cause, self, completed, native_objects) from cause


__all__ = ["CanteraCatalyticSurfaceReactor", "CatalyticSurfacePoint", "CatalyticSurfaceTrace",
           "CatalyticThermalBoundary", "CatalyticFlowBoundary", "CatalyticFlowPoint",
           "CatalyticFlowTrace",
           "CatalyticSurfaceError"]
