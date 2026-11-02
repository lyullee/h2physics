"""Finite cryogenic high-pressure storage by existing native tank composition.

LH2DT owns fluid/wall derivatives and integration; the existing relief driver
owns events and the shared nozzle owns discharge. HEOS owns every property.
No new tank ODE, EOS, heat law, event solver or choking closure is introduced.
"""

import importlib
from dataclasses import dataclass
from typing import Any

from ..core import Origin, ThermoState, finite
from ..dynamics import ConservedInventory, InventoryBalance, InventoryTolerances
from ..release import HomogeneousIsentropicNozzle, NozzleOpening
from ..thermo.coolprop import CoolPropProperties
from .lh2dt import Lh2dtProperties, from_lh2dt_state
from .lh2dt_properties import Lh2dtLowLevelProperties
from .lh2dt_relief import (
    Lh2dtReliefTankDriver,
    ReliefEventSettings,
    ReliefTankBoundary,
    shared_native_relief,
)


def _ids(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare initial-state, geometry, thermal, protection and domain evidence")


@dataclass(frozen=True, slots=True)
class CryoCompressedNative:
    tank_module: Any
    valve_module: Any
    properties_module: Any
    streams_module: Any
    source_id: str

    @classmethod
    def from_installed(cls, *, source_id: str):
        """Explicit optional import after the caller selects its native installation."""
        _ids(source_id)
        modules = [importlib.import_module("lh2dt."+name)
                   for name in ("tank", "valve", "properties", "streams")]
        return cls(*modules, source_id)


@dataclass(frozen=True, slots=True)
class CryoCompressedGeometry:
    volume_m3: float
    wall_heat_capacity_j_k: float
    ambient_ua_w_k: float
    fluid_wall_ua_w_k: float

    def __post_init__(self):
        for name in ("volume_m3", "wall_heat_capacity_j_k", "ambient_ua_w_k", "fluid_wall_ua_w_k"):
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class CryoCompressedEvidence:
    initial_state_source_id: str
    geometry_source_id: str
    heat_transfer_source_id: str
    protection_source_id: str
    phase_and_solid_exclusion_id: str
    origin: Origin

    def __post_init__(self):
        _ids(self.initial_state_source_id, self.geometry_source_id, self.heat_transfer_source_id,
             self.protection_source_id, self.phase_and_solid_exclusion_id)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Unresolved parameters do not define a cryogenic storage case")


@dataclass(frozen=True, slots=True)
class CryoCompressedDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_pressure_pa_absolute: float
    maximum_pressure_pa_absolute: float
    minimum_inventory_kg: float
    maximum_initial_temperature_k: float
    minimum_initial_pressure_to_critical_ratio: float
    allowed_phases: tuple[str, ...]
    evidence_id: str

    def __post_init__(self):
        for low, high in ((self.minimum_temperature_k, self.maximum_temperature_k),
                          (self.minimum_pressure_pa_absolute, self.maximum_pressure_pa_absolute)):
            if finite(low, "domain minimum", positive=True) >= finite(high, "domain maximum", positive=True):
                raise ValueError("Thermal/absolute-pressure domain bounds must increase")
        finite(self.minimum_inventory_kg, "inventory floor", positive=True)
        if not self.minimum_temperature_k <= finite(self.maximum_initial_temperature_k,
                "maximum cryogenic initial T", positive=True) <= self.maximum_temperature_k:
            raise ValueError("Initial cryogenic temperature limit must lie inside the domain")
        if finite(self.minimum_initial_pressure_to_critical_ratio, "initial P/Pcritical") <= 1:
            raise ValueError("Cryo-compressed initial pressure must explicitly exceed critical pressure")
        phases = tuple(self.allowed_phases)
        supported = {"supercritical_liquid", "supercritical", "supercritical_gas", "liquid", "gas"}
        if not phases or not set(phases) <= supported:
            raise ValueError("Declare supported single-fluid phases; coexistence/critical-point states are excluded")
        object.__setattr__(self, "allowed_phases", phases)
        _ids(self.evidence_id)

    def require(self, fluid: ThermoState, mass_kg: float, wall_temperature_k=None, *,
                inventory_minimum_kg=None):
        minimum = self.minimum_inventory_kg if inventory_minimum_kg is None else inventory_minimum_kg
        if (not self.minimum_temperature_k <= fluid.temperature_k <= self.maximum_temperature_k
                or not self.minimum_pressure_pa_absolute <= fluid.pressure_pa <= self.maximum_pressure_pa_absolute
                or fluid.phase not in self.allowed_phases or fluid.vapor_mass_fraction is not None
                or finite(mass_kg, "native inventory", positive=True) <= minimum):
            raise ValueError("Native cryo-compressed state is outside its declared T/P/phase/inventory domain")
        if wall_temperature_k is not None and not self.minimum_temperature_k <= finite(
                wall_temperature_k, "native wall T", positive=True) <= self.maximum_temperature_k:
            raise ValueError("Native wall temperature is outside the declared domain")


@dataclass(frozen=True, slots=True)
class CryoCompressedPoint:
    time_s: float
    native_state: Any
    fluid: ThermoState
    independent_pt: ThermoState
    independent_prho: ThermoState
    inventory: ConservedInventory
    balance: InventoryBalance
    pt_mass_residual_kg: float
    pt_energy_residual_j: float
    prho_energy_residual_j: float
    prho_temperature_residual_k: float


@dataclass(frozen=True, slots=True)
class CryoCompressedTrace:
    storage: Any
    points: tuple[CryoCompressedPoint, ...]
    native_trace: Any
    native_driver: Any
    protection: Any
    independent_properties: Any
    boundary: ReliefTankBoundary
    inventory_tolerances: InventoryTolerances
    critical_temperature_k: float
    critical_pressure_pa: float
    domain: CryoCompressedDomain
    evidence: CryoCompressedEvidence
    geometry: CryoCompressedGeometry
    eos_mass_tolerance_kg: float
    eos_energy_tolerance_j: float
    eos_temperature_tolerance_k: float

    @property
    def time_s(self):
        return self.native_trace.time_s


class CryoCompressedAuditError(ValueError):
    """A completed native run whose accepted output failed a host audit.

    ``point`` is None when failure precedes construction of that audited point.
    The actual accepted native state and already audited prefix remain available
    in every case; the original exception is retained through exception chaining.
    """

    def __init__(self, message, *, native_trace, native_state, accepted_time_s,
                 audited_points, point=None):
        self.native_trace, self.native_state = native_trace, native_state
        self.accepted_time_s, self.audited_points = accepted_time_s, tuple(audited_points)
        self.point = point
        super().__init__(message)


class _DomainCheckedProtection:
    """Host guard around the actual existing transactional protection, no new latch."""

    def __init__(self, actual, storage):
        self.actual, self.storage = actual, storage
        for name in ("bridge", "opening", "set_pressure_pa", "reseat_pressure_pa"):
            setattr(self, name, getattr(actual, name))

    @property
    def native_origin(self):
        return self.actual.native_origin

    @property
    def native(self):
        return self.actual.native

    @property
    def is_open(self):
        return self.actual.is_open

    def evaluate(self, left, right):
        self.storage._check_native(left)
        return self.actual.evaluate(left, right)

    def commit(self, time_s, left, right, *, clock_id):
        self.storage._check_native(left)
        return self.actual.commit(time_s, left, right, clock_id=clock_id)


class CryoCompressedStorage:
    """Reusable native homogeneous fluid/wall + existing pressure-protection driver.

    Each run creates fresh native protection state. A window below set pressure
    is sealed. If set pressure is reached, the existing real native relief and
    shared nozzle act; this is not a stop-at-threshold or an ideal isolation.
    """

    def __init__(self, native: CryoCompressedNative, *, properties: CoolPropProperties,
                 geometry: CryoCompressedGeometry, domain: CryoCompressedDomain,
                 evidence: CryoCompressedEvidence, initial_pressure_pa_absolute: float,
                 initial_temperature_k: float, initial_wall_temperature_k: float,
                 opening: NozzleOpening, set_pressure_pa_absolute: float,
                 reseat_pressure_pa_absolute: float,
                 independent_properties_factory=CoolPropProperties,
                 inventory_tolerances: InventoryTolerances | None = None,
                 eos_mass_tolerance_kg: float = 1e-10,
                 eos_energy_tolerance_j: float = 1e-4,
                 eos_temperature_tolerance_k: float = 1e-7,
                 event_settings: ReliefEventSettings | None = None):
        _ids(native.source_id)
        if (not isinstance(properties, CoolPropProperties) or properties.backend != "HEOS"
                or properties.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}
                or properties.internal_energy_policy != "library"
                or properties.quality_roundoff_tolerance != 0.):
            raise ValueError("Select explicit pure normal/para/ortho direct HEOS with strict native energy/phase")
        if not callable(independent_properties_factory):
            raise TypeError("Supply an independent direct-HEOS provider factory")
        self.native, self.properties, self.geometry = native, properties, geometry
        self.domain, self.evidence = domain, evidence
        self.critical_temperature_k = properties.critical_temperature_k
        self.critical_pressure_pa = properties.critical_pressure_pa
        initial = properties.state_pt(initial_pressure_pa_absolute, initial_temperature_k)
        mass = initial.density_kg_m3*geometry.volume_m3
        domain.require(initial, mass, initial_wall_temperature_k)
        if (initial.temperature_k > domain.maximum_initial_temperature_k
                or initial.pressure_pa < domain.minimum_initial_pressure_to_critical_ratio*self.critical_pressure_pa):
            raise ValueError("Initial state is outside the explicit cryogenic/high-pressure storage scope")
        for value in (set_pressure_pa_absolute, reseat_pressure_pa_absolute):
            finite(value, "absolute protection pressure", positive=True)
        if not domain.minimum_pressure_pa_absolute <= reseat_pressure_pa_absolute < (
                set_pressure_pa_absolute) <= domain.maximum_pressure_pa_absolute:
            raise ValueError("Protection thresholds must lie strictly inside the declared pressure scope")
        if initial.pressure_pa >= set_pressure_pa_absolute:
            raise ValueError("This builder requires a closed initial valve below its set pressure")
        self.opening, self.set_pressure_pa = opening, set_pressure_pa_absolute
        self.reseat_pressure_pa = reseat_pressure_pa_absolute
        self.native_properties = Lh2dtLowLevelProperties(properties,
            state_factory=native.properties_module.ThermoState)
        self.bridge = Lh2dtProperties(self.native_properties, reference_id=properties.basis.reference_id)
        g = native.tank_module.TankGeometry(geometry.volume_m3, geometry.wall_heat_capacity_j_k,
                                          geometry.ambient_ua_w_k, geometry.fluid_wall_ua_w_k)
        self.native_tank = native.tank_module.HomogeneousTank(g, self.native_properties)
        self.initial_native_state = native.tank_module.TankState(mass,
            mass*initial.internal_energy_j_kg, initial_wall_temperature_k)
        self.initial_fluid = initial
        self._native_geometry = g
        self._basis = properties.basis
        self.independent_properties_factory = independent_properties_factory
        self.tolerances = inventory_tolerances or InventoryTolerances(1e-12, 1e-5, 1e-10)
        self.eos_mass_tolerance_kg = finite(eos_mass_tolerance_kg,
                                           "independent EOS mass tolerance", positive=True)
        self.eos_energy_tolerance_j = finite(eos_energy_tolerance_j,
                                             "independent EOS energy tolerance", positive=True)
        self.eos_temperature_tolerance_k = finite(eos_temperature_tolerance_k,
                                                  "independent EOS temperature tolerance", positive=True)
        self.event_settings = event_settings or ReliefEventSettings()

    def _require_configuration(self):
        self._basis.require_compatible(self.properties.basis)
        self._basis.require_compatible(self.native_properties.basis)
        if (self.native_tank.geometry is not self._native_geometry
                or self.native_tank.properties is not self.native_properties
                or self.native_properties.provider is not self.properties):
            raise ValueError("Native storage geometry/property ownership changed")

    def _check_native(self, native_thermo, wall_temperature_k=None):
        self._require_configuration()
        fluid = from_lh2dt_state(native_thermo, basis=self._basis)
        # Positive native trial inventory may cross the configured floor while
        # the existing event driver brackets it. No sub-floor trial is accepted.
        self.domain.require(fluid, fluid.density_kg_m3*self.geometry.volume_m3, wall_temperature_k,
                            inventory_minimum_kg=0.)
        return fluid

    def run(self, *, duration_s: float, maximum_step_s: float, start_time_s: float,
            clock_id: str, boundary: ReliefTankBoundary) -> CryoCompressedTrace:
        self._require_configuration()
        reference = self.independent_properties_factory(self._basis.fluid)
        if reference is self.properties or not isinstance(reference, CoolPropProperties) or reference.backend != "HEOS":
            raise ValueError("Independent EOS reconstruction requires a separate direct-HEOS provider")
        self._basis.require_compatible(reference.basis)
        actual = shared_native_relief(native_valve_type=self.native.valve_module.Valve,
            native_relief_factory=self.native.valve_module.PressureReliefValve,
            result_factory=self.native.valve_module.ValveResult,
            nozzle=HomogeneousIsentropicNozzle(self.properties), bridge=self.bridge, opening=self.opening,
            set_pressure_pa_absolute=self.set_pressure_pa, reseat_pressure_pa_absolute=self.reseat_pressure_pa,
            native_source_id=self.native.source_id)
        checked = _DomainCheckedProtection(actual, self)
        driver = Lh2dtReliefTankDriver(self.native_tank, checked,
            flow_factory=self.native.streams_module.MassEnergyFlow,
            state_factory=self.native.properties_module.ThermoState, event_settings=self.event_settings)

        def heat(time, native_thermo, wall):
            self._check_native(native_thermo, wall)
            return boundary.direct_wall_heat_w(time, native_thermo, wall)

        guarded = ReliefTankBoundary(boundary.clock_id, boundary.support_start_s, boundary.support_end_s,
            boundary.downstream, boundary.ambient_temperature_k, heat, boundary.source_id)
        raw = driver.run(self.initial_native_state, duration_s=duration_s, maximum_step_s=maximum_step_s,
            start_time_s=start_time_s, clock_id=clock_id, boundary=guarded,
            minimum_inventory_kg=self.domain.minimum_inventory_kg)
        points = []
        state, accepted_time, point = self.initial_native_state, float(raw.time_s[0]), None
        try:
            states = (self.initial_native_state, *(row.native_step.state for row in raw.intervals))
            for i, state in enumerate(states):
                accepted_time, point = float(raw.time_s[i]), None
                fluid = self._check_native(self.native_tank.thermo(state), state.wall_temperature_K)
                minimum = self.domain.minimum_inventory_kg
                if raw.inventory_event is not None and i == len(states)-1:
                    minimum -= self.event_settings.mass_tolerance_kg
                self.domain.require(fluid, state.hydrogen_mass_kg, state.wall_temperature_K,
                                    inventory_minimum_kg=minimum)
                inventory = ConservedInventory(self._basis, state.hydrogen_mass_kg,
                    state.hydrogen_internal_energy_J, self.geometry.wall_heat_capacity_j_k*state.wall_temperature_K)
                initial_inventory = inventory if i == 0 else points[0].inventory
                balance = InventoryBalance(initial_inventory, inventory, -float(raw.released_mass_kg[i]),
                    float(raw.external_heat_j[i]-raw.released_enthalpy_j[i]),
                    -float(raw.released_enthalpy_j[i]), float(raw.external_heat_j[i]))
                pt = reference.state_pt(fluid.pressure_pa, fluid.temperature_k)
                prho = reference.state_prho(fluid.pressure_pa, state.hydrogen_mass_kg/self.geometry.volume_m3)
                point = CryoCompressedPoint(accepted_time, state, fluid, pt, prho, inventory, balance,
                    pt.density_kg_m3*self.geometry.volume_m3-state.hydrogen_mass_kg,
                    state.hydrogen_mass_kg*pt.internal_energy_j_kg-state.hydrogen_internal_energy_J,
                    state.hydrogen_mass_kg*prho.internal_energy_j_kg-state.hydrogen_internal_energy_J,
                    prho.temperature_k-fluid.temperature_k)
                if (balance.violations(self.tolerances)
                        or abs(point.pt_mass_residual_kg) > self.eos_mass_tolerance_kg
                        or max(abs(point.pt_energy_residual_j), abs(point.prho_energy_residual_j)) > self.eos_energy_tolerance_j
                        or abs(point.prho_temperature_residual_k) > self.eos_temperature_tolerance_k):
                    raise ValueError("Independent native EOS/inventory audit failed")
                points.append(point)
            point = None
            self._require_configuration()
            return CryoCompressedTrace(self, tuple(points), raw, driver, actual, reference, boundary,
                self.tolerances, self.critical_temperature_k, self.critical_pressure_pa, self.domain,
                self.evidence, self.geometry, self.eos_mass_tolerance_kg, self.eos_energy_tolerance_j,
                self.eos_temperature_tolerance_k)
        except Exception as error:
            raise CryoCompressedAuditError(f"Post-run cryo-compressed audit failed: {error}",
                native_trace=raw, native_state=state, accepted_time_s=accepted_time,
                audited_points=points, point=point) from error
