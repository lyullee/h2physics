"""Scheduled thermal hydride compression between actual finite native vessels.

The existing finite hydride core owns bed rates/reference, LH2DT owns vessel
fluid/wall derivatives, HEOS owns properties and the shared nozzle owns flow.
One common SciPy integration orchestrates them; no rate/EOS/valve law is copied.
"""

import importlib
import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from ..adapters.lh2dt import Lh2dtProperties, from_lh2dt_state
from ..adapters.lh2dt_properties import Lh2dtLowLevelProperties
from ..core import Origin, ThermoState, finite, immutable_array
from ..dynamics import ConservedInventory, InventoryBalance, InventoryTolerances
from ..release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleResult
from ..thermo.coolprop import CoolPropProperties
from .finite_hydride import (
    FiniteHydrideBed,
    FiniteHydrideHeatBoundary,
    FiniteHydrideRates,
    FiniteHydrideSnapshot,
    HydrideGasThermodynamics,
)
from .hydride import HydrideState


_PENDING_COMPRESSOR_TRACE_ISSUERS: set[object] = set()


def _issue_compressor_trace_token():
    token = object()
    _PENDING_COMPRESSOR_TRACE_ISSUERS.add(token)
    return token


def _ids(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare source, parameter, inventory and clock identities")


def _hash_trace_value(digest, value, seen):
    """Hash the retained result graph without importing or serializing native owners."""
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        digest.update(type(value).__qualname__.encode())
        digest.update(repr(value).encode("utf-8", errors="backslashreplace"))
        return
    if isinstance(value, Enum):
        digest.update((type(value).__qualname__ + ":" + str(value.value)).encode())
        return
    identity = id(value)
    if identity in seen:
        digest.update(f"ref:{seen[identity]}".encode())
        return
    seen[identity] = len(seen)
    if not isinstance(value, (tuple, list)):
        digest.update(f"identity:{identity}".encode())
    digest.update(type(value).__qualname__.encode())
    if isinstance(value, np.ndarray):
        digest.update(value.dtype.str.encode())
        digest.update(repr(value.shape).encode())
        if value.dtype.hasobject:
            for item in value.flat:
                _hash_trace_value(digest, item, seen)
        else:
            digest.update(np.ascontiguousarray(value).tobytes())
    elif isinstance(value, Mapping):
        for key in sorted(value, key=repr):
            _hash_trace_value(digest, key, seen)
            _hash_trace_value(digest, value[key], seen)
    elif is_dataclass(value) and not isinstance(value, type):
        for item in fields(value):
            digest.update(item.name.encode())
            _hash_trace_value(digest, getattr(value, item.name), seen)
    elif isinstance(value, (tuple, list)):
        digest.update(str(len(value)).encode())
        for item in value:
            _hash_trace_value(digest, item, seen)
    elif hasattr(value, "__dict__"):
        attributes = vars(value)
        for name in sorted(attributes):
            digest.update(name.encode())
            _hash_trace_value(digest, attributes[name], seen)
    elif getattr(type(value), "__slots__", ()):
        slots = getattr(type(value), "__slots__")
        if isinstance(slots, str):
            slots = (slots,)
        for name in sorted(slots):
            if hasattr(value, name):
                digest.update(name.encode())
                _hash_trace_value(digest, getattr(value, name), seen)
    else:
        digest.update(repr(value).encode("utf-8", errors="backslashreplace"))


def _compressor_trace_signature(trace):
    digest = hashlib.sha256()
    _hash_trace_value(digest, (
        id(trace.compressor), trace.evidence, trace.initial_snapshot,
        trace.segments, trace.termination, trace.event_time_s, trace.energy_scale_j,
    ), {})
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class HydrideCompressorNative:
    tank: Any
    properties: Any
    streams: Any
    source_id: str

    @classmethod
    def from_installed(cls, *, source_id: str):
        """Explicit optional native import; no installation or fallback."""
        _ids(source_id)
        return cls(*(importlib.import_module("lh2dt." + name)
                     for name in ("tank", "properties", "streams")), source_id)


@dataclass(frozen=True, slots=True)
class FiniteHydrideGasVessel:
    vessel_id: str
    native_tank: Any
    initial_native_state: Any
    bridge: Lh2dtProperties
    minimum_gas_mass_kg: float
    source_id: str

    def __post_init__(self):
        _ids(self.vessel_id, self.source_id)
        finite(self.minimum_gas_mass_kg, "native vessel inventory floor", positive=True)
        if self.native_tank.properties is not self.bridge.native:
            raise ValueError("Vessel and bridge must retain the same actual native property object")
        if self.initial_native_state.hydrogen_mass_kg <= self.minimum_gas_mass_kg:
            raise ValueError("Initial native vessel mass must exceed its declared floor")

    @classmethod
    def coolprop(cls, native: HydrideCompressorNative, gas: HydrideGasThermodynamics, *,
                 vessel_id: str, native_geometry: Any, pressure_pa: float, temperature_k: float,
                 wall_temperature_k: float, minimum_gas_mass_kg: float, source_id: str):
        """Compose existing property facade and actual native tank/state factories.

        The selected native TankGeometry requires real strictly positive UAs;
        no epsilon replacement for adiabatic/decoupled operation is introduced.
        """
        properties = gas.native_objects[0]
        if not isinstance(properties, CoolPropProperties) or properties.backend != "HEOS":
            raise TypeError("This native vessel factory requires the actual hydride HEOS provider")
        gas.basis.require_compatible(properties.basis)
        if not isinstance(native_geometry, native.tank.TankGeometry):
            raise TypeError("An actual native TankGeometry is required")
        facade = Lh2dtLowLevelProperties(properties, state_factory=native.properties.ThermoState)
        bridge = Lh2dtProperties(facade, reference_id=gas.basis.reference_id)
        component = native.tank.HomogeneousTank(native_geometry, properties=facade)
        initial = gas.state_pt(pressure_pa, temperature_k)
        mass = initial.density_kg_m3 * native_geometry.volume_m3
        state = native.tank.TankState(mass, mass * initial.internal_energy_j_kg, wall_temperature_k)
        return cls(vessel_id, component, state, bridge, minimum_gas_mass_kg, source_id)


@dataclass(frozen=True, slots=True)
class HydrideCompressorEvidence:
    source_id: str
    material_parameter_source_id: str
    thermal_and_geometry_source_id: str
    initial_inventory_source_id: str
    cycle_source_id: str
    clock_id: str
    origin: Origin

    def __post_init__(self):
        _ids(self.source_id, self.material_parameter_source_id, self.thermal_and_geometry_source_id,
             self.initial_inventory_source_id, self.cycle_source_id, self.clock_id)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Unresolved material/apparatus evidence cannot define a compressor run")


@dataclass(frozen=True, slots=True)
class HydrideCompressorStage:
    stage_id: str
    start_time_s: float
    end_time_s: float
    inlet_opening_fraction: float
    outlet_opening_fraction: float
    bed_heat: FiniteHydrideHeatBoundary
    source_bath_temperature_k: float
    receiver_bath_temperature_k: float
    source_wall_heat_w: float = 0.
    receiver_wall_heat_w: float = 0.

    def __post_init__(self):
        _ids(self.stage_id)
        finite(self.start_time_s, "stage start")
        finite(self.end_time_s, "stage end")
        if self.start_time_s >= self.end_time_s:
            raise ValueError("Stage clock must increase")
        for name in ("inlet_opening_fraction", "outlet_opening_fraction"):
            if not 0 <= finite(getattr(self, name), name) <= 1:
                raise ValueError("Scheduled opening fractions must lie in [0,1]")
        if self.inlet_opening_fraction and self.outlet_opening_fraction:
            raise ValueError("This sequential compressor excludes simultaneous inlet/outlet bypass")
        for name in ("source_bath_temperature_k", "receiver_bath_temperature_k"):
            finite(getattr(self, name), name, positive=True)
        for name in ("source_wall_heat_w", "receiver_wall_heat_w"):
            finite(getattr(self, name), name)
        if not self.bed_heat.support_start_s <= self.start_time_s < self.end_time_s <= self.bed_heat.support_end_s:
            raise ValueError("Stage exceeds its actual finite heat-boundary support")


@dataclass(frozen=True, slots=True)
class HydrideCompressorSnapshot:
    time_s: float
    stage_id: str
    bed: FiniteHydrideSnapshot
    source_native_state: Any
    receiver_native_state: Any
    source: ThermoState
    receiver: ThermoState
    bed_inventory: ConservedInventory
    source_inventory: ConservedInventory
    receiver_inventory: ConservedInventory

    @property
    def total_hydrogen_mass_kg(self):
        return math.fsum(s.mass_kg for s in
                         (self.bed_inventory, self.source_inventory, self.receiver_inventory))

    @property
    def total_internal_energy_j(self):
        return math.fsum(s.total_energy_j for s in
                         (self.bed_inventory, self.source_inventory, self.receiver_inventory))


@dataclass(frozen=True, slots=True)
class HydrideCompressorPoint:
    snapshot: HydrideCompressorSnapshot
    inlet_nozzle: NozzleResult
    outlet_nozzle: NozzleResult
    bed_rates: FiniteHydrideRates
    source_native_derivative: Any
    receiver_native_derivative: Any
    integrated: Any
    body_balances: Any
    total_hydrogen_residual_kg: float
    total_energy_residual_j: float
    bed_gas_energy_residual_j: float
    bed_solid_energy_residual_j: float

    def __post_init__(self):
        for name in ("integrated", "body_balances"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True, slots=True)
class HydrideCompressorSegment:
    stage: HydrideCompressorStage
    points: tuple[HydrideCompressorPoint, ...]
    native_solution: Any
    source_receiver_pressure_crossings_s: tuple[float, ...]
    delivered_above_source_mass_kg: float


@dataclass(frozen=True, slots=True)
class HydrideCompressorTrace:
    compressor: Any
    evidence: HydrideCompressorEvidence
    initial_snapshot: HydrideCompressorSnapshot
    segments: tuple[HydrideCompressorSegment, ...]
    termination: str
    event_time_s: float | None
    energy_scale_j: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _signature: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_COMPRESSOR_TRACE_ISSUERS:
            raise TypeError("Create compressor traces only from a completed native coupled integration")
        _PENDING_COMPRESSOR_TRACE_ISSUERS.remove(self._issuer_token)
        if not isinstance(self.compressor, HydrideThermalCompressor):
            raise TypeError("Compressor trace must retain its original coupled model")
        if self.evidence is not self.compressor.evidence:
            raise ValueError("Compressor trace must retain the exact model evidence object")
        if type(self.initial_snapshot) is not HydrideCompressorSnapshot:
            raise TypeError("Compressor trace requires its original initial snapshot")
        segments = tuple(self.segments)
        if not segments or any(type(segment) is not HydrideCompressorSegment for segment in segments):
            raise ValueError("Compressor trace requires completed typed native segments")
        if any(type(point) is not HydrideCompressorPoint
               for segment in segments for point in segment.points):
            raise TypeError("Compressor segments must retain typed native audit points")
        if segments[0].stage.start_time_s != self.initial_snapshot.time_s:
            raise ValueError("Compressor schedule does not begin at the retained initial state")
        if any(left.stage.end_time_s != right.stage.start_time_s
               for left, right in zip(segments, segments[1:])):
            raise ValueError("Completed compressor segments must retain a contiguous command clock")
        if not segments[-1].points:
            raise ValueError("Final compressor segment must retain its accepted points")
        if self.termination == "schedule_end":
            if self.event_time_s is not None:
                raise ValueError("Schedule completion cannot also report a terminal inventory event")
        elif (not isinstance(self.termination, str) or not self.termination.endswith("_inventory_floor")
              or self.event_time_s != segments[-1].points[-1].snapshot.time_s):
            raise ValueError("Compressor event termination must match its retained terminal sample")
        finite(self.energy_scale_j, "integrated compressor energy scale", positive=True)
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "_signature", _compressor_trace_signature(self))

    def require_current(self):
        """Reject edits to native samples, audit points, or derived trace summaries."""
        if (self._issuer_token is None
                or not isinstance(self.compressor, HydrideThermalCompressor)
                or self.evidence is not self.compressor.evidence
                or _compressor_trace_signature(self) != self._signature):
            raise ValueError("Hydride compressor result changed after its native run")
        return self

    @property
    def points(self):
        """Stage endpoints intentionally appear twice with distinct pre/post commands."""
        self.require_current()
        return tuple(p for segment in self.segments for p in segment.points)

    @property
    def delivered_hydrogen_kg(self):
        self.require_current()
        return self.points[-1].integrated["outlet_mass_kg"]

    @property
    def admitted_hydrogen_kg(self):
        self.require_current()
        return self.points[-1].integrated["inlet_mass_kg"]

    @property
    def delivered_above_source_mass_kg(self):
        self.require_current()
        return math.fsum(s.delivered_above_source_mass_kg for s in self.segments)


class HydrideCompressorIntegrationError(RuntimeError):
    def __init__(self, message, *, compressor, completed_segments, native_solution,
                 audited_points, trial_time_s, trial_values, audit_time_s=None, audit_values=None):
        super().__init__(message)
        self.compressor = compressor
        self.completed_segments = tuple(completed_segments)
        self.native_solution = native_solution
        self.audited_points = tuple(audited_points)
        self.trial_time_s = trial_time_s
        self.trial_values = immutable_array(trial_values, dtype=float, name="trial values")
        self.audit_time_s = audit_time_s
        self.audit_values = (
            None if audit_values is None
            else immutable_array(audit_values, dtype=float, name="audit values")
        )


class HydrideThermalCompressor:
    """One bed, finite source/receiver and staged ports in one coupled solve.

    Heating/cooling baths are explicit external utilities, not finite H2
    reservoirs. Receiver mixing retains donor stagnation enthalpy, including
    nozzle kinetic energy that dissipates inside the receiving control volume.
    """

    _ledger_names = (
        "bed_gas_heat_j", "bed_solid_heat_j", "source_external_heat_j", "receiver_external_heat_j",
        "inlet_mass_kg", "outlet_mass_kg", "inlet_enthalpy_j", "outlet_enthalpy_j",
        "material_enthalpy_to_solid_j", "gas_solid_heat_to_gas_j", "nominal_reaction_heat_j",
        "hydrogen_uptake_kg", "positive_bed_thermal_duty_j", "negative_bed_thermal_duty_j",
        "source_wall_to_fluid_heat_j", "receiver_wall_to_fluid_heat_j",
    )
    _mass_ledgers = {"inlet_mass_kg", "outlet_mass_kg", "hydrogen_uptake_kg"}

    def __init__(self, native: HydrideCompressorNative, *, bed: FiniteHydrideBed,
                 source: FiniteHydrideGasVessel, receiver: FiniteHydrideGasVessel,
                 nozzle: HomogeneousIsentropicNozzle, inlet_opening: NozzleOpening,
                 outlet_opening: NozzleOpening, evidence: HydrideCompressorEvidence,
                 tolerances: InventoryTolerances | None = None):
        bed.gas.basis.require_compatible(source.bridge.basis)
        bed.gas.basis.require_compatible(receiver.bridge.basis)
        bed.gas.basis.require_compatible(nozzle.properties.basis)
        if source.vessel_id == receiver.vessel_id or source.native_tank is receiver.native_tank:
            raise ValueError("Source and receiver require distinct finite native tank identities")
        for vessel in (source, receiver):
            if (not isinstance(vessel.native_tank, native.tank.HomogeneousTank)
                    or not isinstance(vessel.initial_native_state, native.tank.TankState)):
                raise TypeError("Actual native tank and native initial state are required")
        self.native, self.bed, self.source, self.receiver = native, bed, source, receiver
        self.nozzle, self.inlet_opening, self.outlet_opening = nozzle, inlet_opening, outlet_opening
        self.evidence = evidence
        self.tolerances = tolerances or InventoryTolerances(1e-12, 1e-5, 1e-9)

    def _snapshot(self, time, values, stage, scale):
        if not np.all(np.isfinite(values)):
            raise ValueError("Compressor trial inventory/ledger is nonfinite")
        bed = self.bed.snapshot_from_inventory(time, values[0], values[1], values[2]*scale, values[3])
        snapshots, states, inventories = [], [], []
        tref = self.bed.energy_reference.gas_reference_state.temperature_k
        for vessel, offset in ((self.source, 4), (self.receiver, 7)):
            state = self.native.tank.TankState(float(values[offset]), float(values[offset+1]*scale),
                                               float(values[offset+2]))
            thermo = from_lh2dt_state(vessel.native_tank.thermo(state), basis=vessel.bridge.basis)
            self.bed._require_gas(thermo)
            if not self.bed.domain.minimum_temperature_k <= state.wall_temperature_K <= self.bed.domain.maximum_temperature_k:
                raise ValueError("Finite source/receiver wall temperature exceeds the declared domain")
            inventory = ConservedInventory(vessel.bridge.basis, state.hydrogen_mass_kg,
                state.hydrogen_internal_energy_J,
                vessel.native_tank.geometry.wall_heat_capacity_J_K*(state.wall_temperature_K-tref))
            snapshots.append(thermo)
            states.append(state)
            inventories.append(inventory)
        bed_inventory = ConservedInventory(self.bed.gas.basis, bed.total_hydrogen_mass_kg,
                                           bed.gas_internal_energy_j, bed.solid_internal_energy_j)
        return HydrideCompressorSnapshot(float(time), stage.stage_id, bed, states[0], states[1],
            snapshots[0], snapshots[1], bed_inventory, inventories[0], inventories[1])

    def _evaluate(self, time, values, stage, scale):
        s = self._snapshot(time, values, stage, scale)
        inlet = self.nozzle.solve(s.source, back_pressure_pa=s.bed.gas.pressure_pa,
            opening=self.inlet_opening, opening_fraction=stage.inlet_opening_fraction)
        outlet = self.nozzle.solve(s.bed.gas, back_pressure_pa=s.receiver.pressure_pa,
            opening=self.outlet_opening, opening_fraction=stage.outlet_opening_fraction)
        if min(inlet.mass_flow_kg_s, outlet.mass_flow_kg_s) < 0:
            raise ValueError("A one-way scheduled compressor port returned reverse flow")
        heat = stage.bed_heat.value(time, s.bed)
        rates = self.bed.rates(s.bed, heat,
            gas_mass_flow_kg_s=inlet.mass_flow_kg_s-outlet.mass_flow_kg_s,
            gas_enthalpy_flow_w=inlet.withdrawal_energy_w-outlet.withdrawal_energy_w)
        flow = self.native.streams.MassEnergyFlow
        source_derivative = self.source.native_tank.derivative(s.source_native_state,
            (flow(-inlet.mass_flow_kg_s, inlet.upstream_stagnation.enthalpy_j_kg, "source-to-bed"),),
            stage.source_bath_temperature_k, stage.source_wall_heat_w)
        receiver_derivative = self.receiver.native_tank.derivative(s.receiver_native_state,
            (flow(outlet.mass_flow_kg_s, outlet.upstream_stagnation.enthalpy_j_kg, "bed-to-receiver"),),
            stage.receiver_bath_temperature_k, stage.receiver_wall_heat_w)
        for derivative in (source_derivative, receiver_derivative):
            for name in ("mass_kg_s", "internal_energy_W", "wall_temperature_K_s",
                         "ambient_heat_W", "wall_to_fluid_heat_W"):
                finite(getattr(derivative, name), "actual native vessel derivative " + name)
        actual_source_transport = source_derivative.internal_energy_W-source_derivative.wall_to_fluid_heat_W
        if not math.isclose(actual_source_transport, -inlet.withdrawal_energy_w,
                            rel_tol=1e-10, abs_tol=1e-8):
            raise ValueError("Actual source tank withdrawal enthalpy differs from shared nozzle reference")
        return s, inlet, outlet, rates, source_derivative, receiver_derivative

    def _point(self, time, values, stage, scale, initial):
        s, inlet, outlet, rates, ds, dr = self._evaluate(time, values, stage, scale)
        integrated = {name: float(value if name in self._mass_ledgers else value*scale)
                      for name, value in zip(self._ledger_names, values[10:], strict=True)}
        q = integrated
        qbed = q["bed_gas_heat_j"]+q["bed_solid_heat_j"]
        port = q["inlet_enthalpy_j"]-q["outlet_enthalpy_j"]
        balances = {
            "bed": InventoryBalance(initial.bed_inventory, s.bed_inventory,
                q["inlet_mass_kg"]-q["outlet_mass_kg"], port+qbed, port, qbed),
            "source": InventoryBalance(initial.source_inventory, s.source_inventory,
                -q["inlet_mass_kg"], -q["inlet_enthalpy_j"]+q["source_external_heat_j"],
                -q["inlet_enthalpy_j"], q["source_external_heat_j"]),
            "receiver": InventoryBalance(initial.receiver_inventory, s.receiver_inventory,
                q["outlet_mass_kg"], q["outlet_enthalpy_j"]+q["receiver_external_heat_j"],
                q["outlet_enthalpy_j"], q["receiver_external_heat_j"]),
        }
        for name, balance in balances.items():
            if balance.violations(self.tolerances):
                raise ValueError(f"{name} finite mass/U ledger failed: {balance.violations(self.tolerances)}")
        global_mass = s.total_hydrogen_mass_kg-initial.total_hydrogen_mass_kg
        global_energy = (s.total_internal_energy_j-initial.total_internal_energy_j-qbed
                         -q["source_external_heat_j"]-q["receiver_external_heat_j"])
        gas_error = (s.bed.gas_internal_energy_j-initial.bed.gas_internal_energy_j-port
                     +q["material_enthalpy_to_solid_j"]-q["gas_solid_heat_to_gas_j"]-q["bed_gas_heat_j"])
        solid_error = (s.bed.solid_internal_energy_j-initial.bed.solid_internal_energy_j
                      -q["material_enthalpy_to_solid_j"]+q["gas_solid_heat_to_gas_j"]-q["bed_solid_heat_j"])
        if (abs(global_mass) > self.tolerances.mass_absolute_kg
                or max(abs(global_energy), abs(gas_error), abs(solid_error)) > self.tolerances.energy_absolute_j):
            raise ValueError("All-body mass/U or separate bed gas/solid energy ledger failed")
        return HydrideCompressorPoint(s, inlet, outlet, rates, ds, dr, integrated, balances,
                                       float(global_mass), float(global_energy), float(gas_error), float(solid_error))

    def run(self, stages: Sequence[HydrideCompressorStage], *, initial_solid: HydrideState,
            initial_bed_gas: ThermoState, sample_interval_s: float,
            maximum_step_s: float, relative_tolerance: float = 1e-8,
            energy_scale_j: float = 1e3) -> HydrideCompressorTrace:
        stages = tuple(stages)
        if not stages or len({s.stage_id for s in stages}) != len(stages):
            raise ValueError("A nonempty schedule needs unique stage identifiers")
        if any(a.end_time_s != b.start_time_s for a, b in zip(stages, stages[1:])):
            raise ValueError("Absolute stages must be contiguous; gaps/overlaps are not inferred")
        if any(s.bed_heat.clock_id != self.evidence.clock_id for s in stages):
            raise ValueError("Heat and compressor operation clocks differ")
        for value, name in ((sample_interval_s, "sample interval"), (maximum_step_s, "maximum step"),
                            (energy_scale_j, "energy scale")):
            finite(value, name, positive=True)
        if not 0 < finite(relative_tolerance, "relative tolerance") < 1:
            raise ValueError("Relative tolerance must lie in (0,1)")
        self.bed._require_gas(initial_bed_gas)
        mbed = initial_bed_gas.density_kg_m3*self.bed.free_gas_volume_m3
        source, receiver = self.source.initial_native_state, self.receiver.initial_native_state
        if mbed <= self.bed.domain.minimum_gas_mass_kg:
            raise ValueError("Initial bed free gas must exceed its positive finite inventory floor")
        values = np.array([initial_solid.fraction, mbed, mbed*initial_bed_gas.internal_energy_j_kg/energy_scale_j,
            initial_solid.temperature_k, source.hydrogen_mass_kg, source.hydrogen_internal_energy_J/energy_scale_j,
            source.wall_temperature_K, receiver.hydrogen_mass_kg, receiver.hydrogen_internal_energy_J/energy_scale_j,
            receiver.wall_temperature_K]+[0.]*len(self._ledger_names))
        initial = self._snapshot(stages[0].start_time_s, values, stages[0], energy_scale_j)
        for name in ("pressure_pa", "temperature_k"):
            if not math.isclose(getattr(initial.bed.gas, name), getattr(initial_bed_gas, name), rel_tol=1e-8):
                raise ValueError("Initial bed gas does not roundtrip through its actual native DU provider")
        completed = []
        termination, event_time = "schedule_end", None
        for stage in stages:
            solution, points = None, []
            last_time, last_values = stage.start_time_s, values.copy()
            audit_time, audit_values = None, None

            def rhs(time, vector):
                nonlocal last_time, last_values
                last_time, last_values = float(time), vector.copy()
                _s, inlet, outlet, r, ds, dr = self._evaluate(time, vector, stage, energy_scale_j)
                ledgers = [r.external_gas_heat_w, r.external_solid_heat_w, ds.ambient_heat_W, dr.ambient_heat_W,
                    inlet.mass_flow_kg_s, outlet.mass_flow_kg_s, inlet.withdrawal_energy_w, outlet.withdrawal_energy_w,
                    r.material_enthalpy_to_solid_w, r.gas_solid_heat_to_gas_w, r.nominal_reaction_heat_w,
                    r.hydrogen_uptake_kg_s,
                    max(r.external_gas_heat_w, 0.)+max(r.external_solid_heat_w, 0.),
                    min(r.external_gas_heat_w, 0.)+min(r.external_solid_heat_w, 0.),
                    ds.wall_to_fluid_heat_W, dr.wall_to_fluid_heat_W]
                result = [r.fraction_s_inv, r.gas_mass_kg_s, r.gas_internal_energy_w/energy_scale_j,
                    r.solid_temperature_k_s, ds.mass_kg_s, ds.internal_energy_W/energy_scale_j,
                    ds.wall_temperature_K_s, dr.mass_kg_s, dr.internal_energy_W/energy_scale_j, dr.wall_temperature_K_s]
                result.extend(v if name in self._mass_ledgers else v/energy_scale_j
                              for name, v in zip(self._ledger_names, ledgers, strict=True))
                if not np.all(np.isfinite(result)):
                    raise ValueError("Native coupled compressor derivative is nonfinite")
                return result

            events = []
            for index, floor in ((1, self.bed.domain.minimum_gas_mass_kg),
                                  (4, self.source.minimum_gas_mass_kg), (7, self.receiver.minimum_gas_mass_kg)):
                def floor_event(time, vector, index=index, floor=floor):
                    return vector[index]-floor
                floor_event.terminal, floor_event.direction = True, -1
                events.append(floor_event)

            def pressure_crossing(time, vector):
                s = self._snapshot(time, vector, stage, energy_scale_j)
                return s.receiver.pressure_pa-s.source.pressure_pa
            pressure_crossing.terminal, pressure_crossing.direction = False, 0
            events.append(pressure_crossing)
            try:
                atol = [1e-11, 1e-13, 1e-11, 1e-7, 1e-13, 1e-11, 1e-7, 1e-13, 1e-11, 1e-7]
                atol.extend(1e-13 if name in self._mass_ledgers else 1e-11 for name in self._ledger_names)
                solution = solve_ivp(rhs, (stage.start_time_s, stage.end_time_s), values,
                    method="DOP853", dense_output=True, events=events,
                    rtol=relative_tolerance, atol=atol, max_step=maximum_step_s)
                if not solution.success:
                    raise RuntimeError(solution.message)
                end = float(solution.t[-1])
                times = np.linspace(stage.start_time_s, end,
                                    max(2, math.ceil((end-stage.start_time_s)/sample_interval_s)+1))
                times = np.unique(np.r_[times, *solution.t_events])
                for time in times:
                    vector = solution.sol(time)
                    audit_time, audit_values = float(time), vector.copy()
                    points.append(self._point(float(time), vector, stage, energy_scale_j, initial))
                crossings = tuple(float(t) for t in solution.t_events[3])
                partitions = sorted({stage.start_time_s, end, *crossings})
                lifted = 0.
                out_index = 10+self._ledger_names.index("outlet_mass_kg")
                for left, right in zip(partitions, partitions[1:]):
                    audit_time = (left+right)/2
                    audit_values = solution.sol(audit_time).copy()
                    middle = self._snapshot((left+right)/2, solution.sol((left+right)/2), stage, energy_scale_j)
                    if middle.receiver.pressure_pa > middle.source.pressure_pa:
                        lifted += float(solution.sol(right)[out_index]-solution.sol(left)[out_index])
                completed.append(HydrideCompressorSegment(stage, tuple(points), solution, crossings, lifted))
                values = solution.y[:, -1].copy()
                for index, name in enumerate(("bed_gas_inventory_floor", "source_inventory_floor", "receiver_inventory_floor")):
                    if len(solution.t_events[index]):
                        termination, event_time = name, float(solution.t_events[index][0])
                if event_time is not None:
                    break
            except Exception as exc:
                raise HydrideCompressorIntegrationError(f"Finite hydride compressor failed: {exc}",
                    compressor=self, completed_segments=completed, native_solution=solution,
                    audited_points=points, trial_time_s=last_time, trial_values=last_values,
                    audit_time_s=audit_time, audit_values=audit_values) from exc
        return HydrideCompressorTrace(self, self.evidence, initial, tuple(completed), termination,
                                       event_time, energy_scale_j, _issue_compressor_trace_token())
