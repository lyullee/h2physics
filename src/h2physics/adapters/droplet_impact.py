"""Finite surface contact with native phase states; execution is deferred.

Outcome/contact coefficients require caller evidence. Vapor mass is solved from
finite wall heat, latent enthalpy and passive mechanical/recoil accounting.
No universal LH2 impact, splash, Leidenfrost or wetting correlation is supplied.
"""

import dataclasses
import hashlib
import math
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..core import Origin, PropertyBasis, ThermoState, finite
from ..release import SourceLocation
from .droplet_transport import ParcelBoundary, ParcelState, ParcelTrace

STATUS = "implemented_unverified"
_PENDING_SURFACE_TRACE_ISSUERS: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")


def _vector(value, name):
    result = tuple(finite(x, name) for x in value)
    if len(result) != 3:
        raise ValueError(f"{name} needs three finite SI components")
    return result


def _origin(value):
    result = Origin(value)
    if result == Origin.UNRESOLVED:
        raise ValueError("Impact evidence origin cannot be unresolved")
    return result


def _validate(obj, cls):
    if not isinstance(obj, cls):
        raise TypeError(f"Supply an actual {cls.__name__}")
    return cls(**{f.name: getattr(obj, f.name) for f in dataclasses.fields(cls)})


@dataclass(frozen=True, slots=True)
class SurfacePatch:
    location: SourceLocation
    initial_time_s: float
    effective_recoil_mass_kg: float
    heat_capacity_j_k: float
    initial_temperature_k: float
    minimum_temperature_k: float
    maximum_temperature_k: float
    radius_m: float
    material_evidence_id: str
    fixed_mount_arrest_evidence_id: str
    dry_patch_clearing_evidence_id: str
    intercontact_thermal_evidence_id: str
    origin: Origin
    material_owner: Any

    def __post_init__(self):
        _validate(self.location, SourceLocation)
        finite(self.initial_time_s, "initial surface state clock")
        for name in ("effective_recoil_mass_kg", "heat_capacity_j_k", "initial_temperature_k",
                     "minimum_temperature_k", "maximum_temperature_k", "radius_m"):
            finite(getattr(self, name), name, positive=True)
        if not self.minimum_temperature_k <= self.initial_temperature_k <= self.maximum_temperature_k:
            raise ValueError("Surface temperature must lie inside its finite material domain")
        for name in ("material_evidence_id", "fixed_mount_arrest_evidence_id",
                     "dry_patch_clearing_evidence_id", "intercontact_thermal_evidence_id"):
            _text(getattr(self, name), name)
        if self.material_owner is None:
            raise ValueError("Retain the original surface material/capacity owner")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class ImpactQualification:
    evidence_id: str
    origin: Origin
    pressure_bounds_pa: tuple[float, float]
    wall_temperature_bounds_k: tuple[float, float]
    diameter_bounds_m: tuple[float, float]
    normal_speed_bounds_m_s: tuple[float, float]
    impact_weber_bounds: tuple[float, float]
    lumped_capacity_evidence_id: str
    negligible_external_work_evidence_id: str
    phase_equilibrium_evidence_id: str

    def __post_init__(self):
        for name in ("evidence_id", "lumped_capacity_evidence_id",
                     "negligible_external_work_evidence_id", "phase_equilibrium_evidence_id"):
            _text(getattr(self, name), name)
        for name in ("pressure_bounds_pa", "wall_temperature_bounds_k", "diameter_bounds_m",
                     "normal_speed_bounds_m_s", "impact_weber_bounds"):
            bounds = tuple(finite(v, name) for v in getattr(self, name))
            if len(bounds) != 2 or not 0 <= bounds[0] < bounds[1]:
                raise ValueError("Impact qualification bounds must be finite, nonnegative and increasing")
            object.__setattr__(self, name, bounds)
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class ImpactOutcome:
    """Evidence-qualified frozen coefficients, not an inferred impact regime.

    Deposition fraction concerns only liquid remaining after solved evaporation.
    Vapor velocity is relative to the intermediate recoiling patch. Interfacial
    energy is an explicit signed internal-energy change, not a contact-angle fit.
    """

    deposited_fraction_of_remaining_liquid: float
    normal_restitution: float
    tangential_retention: float
    vapor_velocity_relative_to_recoil_m_s: tuple[float, float, float]
    contact_conductance_w_k: float
    contact_duration_s: float
    interfacial_internal_energy_change_j: float
    evidence_id: str
    origin: Origin
    raw_result: Any

    def __post_init__(self):
        for name in ("deposited_fraction_of_remaining_liquid", "normal_restitution",
                     "tangential_retention"):
            if not 0 <= finite(getattr(self, name), name) <= 1:
                raise ValueError("Passive deposition/restitution/retention coefficients lie in [0,1]")
        velocity = _vector(self.vapor_velocity_relative_to_recoil_m_s, "vapor recoil-relative velocity")
        object.__setattr__(self, "vapor_velocity_relative_to_recoil_m_s", velocity)
        if finite(self.contact_conductance_w_k, "finite contact conductance") < 0:
            raise ValueError("Contact conductance cannot be negative")
        finite(self.contact_duration_s, "finite contact duration", positive=True)
        finite(self.interfacial_internal_energy_change_j, "signed interfacial energy")
        _text(self.evidence_id, "original outcome evidence")
        object.__setattr__(self, "origin", _origin(self.origin))
        if self.raw_result is None:
            raise ValueError("Retain the original qualified outcome result/parameter record")


@dataclass(frozen=True, slots=True)
class ImpactContext:
    incident_trace: ParcelTrace
    incident: ParcelState
    patch: SurfacePatch
    wall_temperature_k: float
    liquid_state: ThermoState
    vapor_state: ThermoState
    impact_weber: float


@dataclass(frozen=True, slots=True)
class IntercontactThermalContext:
    patch: SurfacePatch
    start_time_s: float
    end_time_s: float
    initial_temperature_k: float
    heat_capacity_j_k: float


@dataclass(frozen=True, slots=True)
class IntercontactThermalResult:
    """Integrated external heat over a gap; the caller owns its trajectory."""

    start_time_s: float
    end_time_s: float
    heat_into_patch_j: float
    minimum_temperature_k: float
    maximum_temperature_k: float
    evidence_id: str
    origin: Origin
    raw_result: Any = None

    def __post_init__(self):
        start = finite(self.start_time_s, "intercontact start clock")
        end = finite(self.end_time_s, "intercontact end clock")
        if end < start:
            raise ValueError("Intercontact thermal interval cannot run backward")
        finite(self.heat_into_patch_j, "integrated heat into patch")
        low = finite(self.minimum_temperature_k, "intercontact minimum temperature", positive=True)
        high = finite(self.maximum_temperature_k, "intercontact maximum temperature", positive=True)
        if low > high:
            raise ValueError("Intercontact temperature extrema are reversed")
        _text(self.evidence_id, "intercontact thermal evidence")
        object.__setattr__(self, "origin", _origin(self.origin))
        if end > start and self.raw_result is None:
            raise ValueError("A finite intercontact interval must retain its source calculation/record")
        if end == start and self.heat_into_patch_j != 0.:
            raise ValueError("Zero-duration thermal intervals cannot transfer heat")


@dataclass(frozen=True, slots=True)
class QualifiedImpactClosure:
    qualification: ImpactQualification
    evaluate: Callable[[ImpactContext], ImpactOutcome]
    owner: Any

    def __post_init__(self):
        _validate(self.qualification, ImpactQualification)
        if not callable(self.evaluate) or self.owner is None:
            raise ValueError("A real outcome callback and original evidence/native owner are required")


@dataclass(frozen=True, slots=True)
class ImpactTolerances:
    mass_kg: float = 1e-12
    energy_j: float = 1e-8
    momentum_kg_m_s: float = 1e-11
    position_m: float = 1e-8
    clock_s: float = 1e-9
    property_relative: float = 1e-8
    root_mass_kg: float = 1e-15

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class MechanicalTrial:
    vapor_mass_kg: float
    deposited_mass_kg: float
    rebound_mass_kg: float
    intermediate_recoil_velocity_m_s: tuple
    rebound_velocity_m_s: tuple
    vapor_velocity_m_s: tuple
    initial_kinetic_energy_j: float
    outgoing_kinetic_energy_j: float
    collision_dissipation_j: float
    arrest_dissipation_j: float
    total_heat_into_patch_j: float
    mount_impulse_out_kg_m_s: tuple
    momentum_residual_kg_m_s: tuple
    wall_post_mechanical_temperature_k: float
    available_contact_heat_j: float
    latent_residual_j: float


@dataclass(frozen=True, slots=True)
class DepositedBatch:
    location: SourceLocation
    available_time_s: float
    mass_kg: float
    state: ThermoState
    velocity_m_s: tuple
    evidence_id: str
    incident_trace: ParcelTrace


@dataclass(frozen=True, slots=True)
class ImpactStep:
    context: ImpactContext
    outcome: ImpactOutcome
    mechanical: MechanicalTrial
    intercontact_thermal: IntercontactThermalResult
    contact_end_s: float
    active_boiling_duration_s: float
    dryout: bool
    wall_final_temperature_k: float
    wall_internal_energy_change_j: float
    latent_heat_j: float
    fluid_internal_energy_change_j: float
    ambient_pressure_work_into_j: float
    interfacial_internal_energy_change_j: float
    total_energy_residual_j: float
    mass_residual_kg: float
    native_root_result: Any
    trials: tuple[MechanicalTrial, ...]
    deposited_batch: DepositedBatch


@dataclass(frozen=True, slots=True)
class SurfaceImpactTrace:
    patch: SurfacePatch
    closure: QualifiedImpactClosure
    native_property_owner: Any
    steps: tuple[ImpactStep, ...]
    final_wall_temperature_k: float
    total_incident_mass_kg: float
    deposited_mass_kg: float
    rebound_mass_kg: float
    vapor_mass_kg: float
    mass_residual_kg: float
    total_energy_residual_j: float
    regime_prediction_solved: bool = False
    surface_spreading_solved: bool = False
    simultaneous_pool_continuation_solved: bool = False
    measured_hydrogen_validation: bool = False
    status: str = STATUS
    _owner: Any = dataclass_field(default=None, repr=False, compare=False)
    _token: object = dataclass_field(default=None, repr=False, compare=False)
    _issued_token: object = dataclass_field(default=None, init=False, repr=False, compare=False)
    _seal: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING_SURFACE_TRACE_ISSUERS:
            raise TypeError("Use FiniteSurfaceImpact.run to issue a surface impact history")
        _PENDING_SURFACE_TRACE_ISSUERS.remove(self._token)
        if type(self._owner) is not FiniteSurfaceImpact:
            raise TypeError("Retain the original finite impact-history owner")
        if (type(self.steps) is not tuple or not self.steps
                or self.patch is not self._owner.patch
                or self.closure is not self._owner.closure
                or self.native_property_owner is not self._owner.properties):
            raise ValueError("Surface impact history must retain its owner's nonempty contact sequence")
        self._validate_ledger()
        object.__setattr__(self, "_issued_token", self._token)
        object.__setattr__(self, "_seal", self._signature())

    def _validate_ledger(self):
        self._owner._guard()
        if (type(self.steps) is not tuple or not self.steps
                or any(type(step) is not ImpactStep for step in self.steps)):
            raise ValueError("Retain the original ordered finite impact steps")
        for index, step in enumerate(self.steps):
            self._owner.require_original_step(step)
            expected_start = (self.patch.initial_time_s if index == 0
                              else self.steps[index - 1].contact_end_s)
            if (step.intercontact_thermal.start_time_s != expected_start
                    or step.intercontact_thermal.end_time_s != step.context.incident.time_s
                    or step.context.incident.time_s < expected_start
                    or (index and step.context.incident.time_s
                        <= self.steps[index - 1].context.incident.time_s)):
                raise ValueError("Impact history does not preserve its ordered shared-wall intervals")
        incoming = math.fsum(step.context.incident.mass_kg for step in self.steps)
        deposited = math.fsum(step.mechanical.deposited_mass_kg for step in self.steps)
        rebound = math.fsum(step.mechanical.rebound_mass_kg for step in self.steps)
        vapor = math.fsum(step.mechanical.vapor_mass_kg for step in self.steps)
        mass_residual = math.fsum((incoming, -deposited, -rebound, -vapor))
        energy_residual = math.fsum(step.total_energy_residual_j for step in self.steps)
        if (self.total_incident_mass_kg != incoming
                or self.deposited_mass_kg != deposited
                or self.rebound_mass_kg != rebound
                or self.vapor_mass_kg != vapor
                or self.mass_residual_kg != mass_residual
                or self.total_energy_residual_j != energy_residual
                or self.final_wall_temperature_k != self.steps[-1].wall_final_temperature_k
                or abs(mass_residual) > self._owner.tolerances.mass_kg
                or abs(energy_residual) > self._owner.tolerances.energy_j
                or self.regime_prediction_solved or self.surface_spreading_solved
                or self.simultaneous_pool_continuation_solved
                or self.measured_hydrogen_validation or self.status != STATUS):
            raise ValueError("Surface impact history summary differs from its issued contact ledgers")

    def _signature(self):
        return (id(self._owner), id(self.patch), id(self.closure), id(self.native_property_owner),
                tuple(id(step) for step in self.steps), self.final_wall_temperature_k,
                self.total_incident_mass_kg, self.deposited_mass_kg, self.rebound_mass_kg,
                self.vapor_mass_kg, self.mass_residual_kg, self.total_energy_residual_j,
                self.regime_prediction_solved, self.surface_spreading_solved,
                self.simultaneous_pool_continuation_solved,
                self.measured_hydrogen_validation, self.status)

    def require_current(self):
        if (self._token is not self._issued_token or not self._seal
                or self._signature() != self._seal):
            raise ValueError("Surface impact history was forged or changed after issue")
        self._validate_ledger()
        return self


@dataclass(frozen=True, slots=True)
class NativePoolInitialization:
    """Native initial-stock objects, without executing or resetting wall heat."""

    batch: DepositedBatch
    native_config: Any
    native_zero_inflow: Any
    native_runner: Any
    native_module: Any
    absolute_start_s: float
    clock_id: str
    separate_continuation_heat_owner: Any
    continuation_evidence_id: str
    impact_owner: Any
    impact_step: ImpactStep
    finite_patch_thermal_continuation_solved: bool = False


class SurfaceImpactError(RuntimeError):
    def __init__(self, cause, *, model, completed_steps=(), incident=None,
                 context=None, outcome=None, trials=(), native_root_result=None,
                 failed_step=None):
        super().__init__(str(cause))
        self.cause, self.model, self.incident = cause, model, incident
        self.completed_steps = tuple(completed_steps)
        self.context, self.outcome = context, outcome
        self.trials = tuple(trials)
        self.native_root_result, self.failed_step = native_root_result, failed_step


def _step_binding(step):
    """Freeze quantitative summaries and original native incident bytes.

    Raw closure/material owners remain original references. They are not used
    as a substitute for the separately captured physical field values.
    """
    def record(value, exclude=()):
        if dataclasses.is_dataclass(value):
            return (type(value), tuple((f.name, record(getattr(value, f.name)))
                for f in dataclasses.fields(value) if f.name not in exclude))
        if isinstance(value, tuple):
            return tuple(record(v) for v in value)
        if isinstance(value, list):
            return tuple(record(v) for v in value)
        if isinstance(value, dict):
            return tuple(sorted(((record(k), record(v)) for k, v in value.items()), key=repr))
        return value

    context, incident = step.context, step.context.incident_trace
    digest = hashlib.sha256()
    for array in (incident.native_result.t, incident.native_result.y, *incident.native_result.t_events):
        digest.update(repr((array.shape, str(array.dtype))).encode())
        digest.update(array.tobytes())
    digest.update(repr((incident.end_reason, incident.evaporated_mass_kg,
        incident.heat_into_liquid_j, incident.drag_work_j, incident.vapor_total_energy_out_j,
        incident.vapor_momentum_out_kg_m_s, incident.ambient_pressure_work_into_j,
        incident.mass_residual_kg, incident.total_energy_residual_j,
        incident.momentum_residual_kg_m_s, incident.native_result.success)).encode())
    return (id(context), id(context.patch), id(incident), id(incident.native_result),
        record(incident.boundary), record(context.incident), context.wall_temperature_k,
        record(context.liquid_state), record(context.vapor_state), context.impact_weber,
        digest.hexdigest(), id(step.outcome), record(step.outcome, ("raw_result",)),
        id(step.outcome.raw_result), record(step.mechanical),
        tuple((f.name, record(getattr(step, f.name))) for f in dataclasses.fields(step)
              if f.name not in {"context", "outcome", "mechanical", "native_root_result", "trials", "deposited_batch"}),
        id(step.intercontact_thermal), id(step.intercontact_thermal.raw_result),
        id(step.native_root_result), tuple(record(t) for t in step.trials),
        id(step.deposited_batch), record(step.deposited_batch, ("incident_trace",)),
        id(step.deposited_batch.incident_trace))


class FiniteSurfaceImpact:
    """Conditional dry-patch impact with finite heat/recoil and a fixed mount.

    Contact is a lumped event: passive collision/recoil, inelastic grounding,
    then finite-G contact boiling. Coefficients are held over the event; the
    vapor mass and mechanical heat are solved together. No impact regime or
    empirical LH2 deposition fraction is inferred by this model.
    """

    def __init__(self, properties, patch: SurfacePatch, closure: QualifiedImpactClosure,
                 *, tolerances: ImpactTolerances = ImpactTolerances(),
                 intercontact_heat: Callable[[IntercontactThermalContext], IntercontactThermalResult] | None = None):
        _validate(patch, SurfacePatch)
        _validate(closure, QualifiedImpactClosure)
        _validate(tolerances, ImpactTolerances)
        if not callable(getattr(properties, "saturated", None)):
            raise TypeError("Supply the actual native saturation provider")
        if intercontact_heat is not None and not callable(intercontact_heat):
            raise TypeError("Intercontact heat must be a callable interval provider")
        self.properties, self.patch, self.closure, self.tolerances = properties, patch, closure, tolerances
        self.intercontact_heat = intercontact_heat
        self._binding = (properties, patch, closure, closure.evaluate, closure.owner, intercontact_heat)
        self._definition = (repr(patch), repr(closure.qualification), repr(tolerances))
        self._issued_steps = {}

    def _guard(self):
        current = (self.properties, self.patch, self.closure, self.closure.evaluate, self.closure.owner,
                   self.intercontact_heat)
        if (any(a is not b for a, b in zip(current, self._binding, strict=True))
                or (repr(self.patch), repr(self.closure.qualification), repr(self.tolerances)) != self._definition):
            raise ValueError("Admitted surface/property/outcome ownership or definitions changed")

    def require_original_step(self, step):
        """Require this owner's unchanged accepted object, never a cached clone."""
        self._guard()
        entry = self._issued_steps.get(id(step))
        if entry is None or entry[0] is not step:
            raise ValueError("Native pool handoff requires the original owner-issued accepted ImpactStep")
        if _step_binding(step) != entry[1]:
            raise ValueError("Owner-issued impact summaries, batch or native incident evidence changed")

    def _context(self, trace, temperature):
        if not isinstance(trace, ParcelTrace) or trace.end_reason != "incident_ground_crossing":
            raise ValueError("Supply an actual incident_ground_crossing ParcelTrace, not deposited mass")
        trace.require_current()
        if not trace.states or not isinstance(trace.states[-1], ParcelState) or trace.native_result is None:
            raise ValueError("Original accepted parcel states and native integration result are required")
        _validate(trace.boundary, ParcelBoundary)
        from scipy.integrate._ivp.ivp import OdeResult

        if not isinstance(trace.native_result, OdeResult) or not trace.native_result.success:
            raise ValueError("The incident must retain its actual successful native OdeResult")
        state, native = trace.states[-1], trace.native_result
        finite(state.time_s, "actual accepted incident clock")
        finite(state.mass_kg, "incident positive mass", positive=True)
        finite(state.diameter_m, "incident diameter", positive=True)
        position, velocity = _vector(state.position_m, "incident position"), _vector(state.velocity_m_s, "incident velocity")
        if (native.t[-1] != state.time_s or len(native.t_events) != 2
                or state.time_s not in native.t_events[1]
                or tuple(native.y[:3, -1]) != position or tuple(native.y[3:6, -1]) != velocity
                or native.y[6, -1] != state.mass_kg):
            raise ValueError("Incident state differs from the original accepted native ground event")
        location, tol = self.patch.location, self.tolerances
        if trace.boundary.clock_id != location.clock_id or trace.boundary.frame_id != location.coordinate_frame_id:
            raise ValueError("Surface and incident need one actual clock and Cartesian z-up frame")
        if (abs(position[2]-location.position_m[2]) > tol.position_m
                or math.hypot(position[0]-location.position_m[0], position[1]-location.position_m[1]) > self.patch.radius_m
                or velocity[2] >= 0):
            raise ValueError("Incident does not enter the admitted horizontal finite surface patch")
        if (abs(finite(trace.mass_residual_kg, "flight mass residual")) > tol.mass_kg
                or abs(finite(trace.total_energy_residual_j, "flight energy residual")) > tol.energy_j
                or max(abs(x) for x in _vector(trace.momentum_residual_kg_m_s, "flight momentum residual")) > tol.momentum_kg_m_s):
            raise ValueError("Original parcel conservation is outside impact admission budgets")
        for phase in (state.liquid_state, state.vapor_state):
            _validate(phase, ThermoState)
            _validate(phase.basis, PropertyBasis)
        liquid = self.properties.saturated(state.liquid_state.pressure_pa, 0.)
        vapor = self.properties.saturated(state.liquid_state.pressure_pa, 1.)
        self._guard()
        for expected, actual in ((liquid, state.liquid_state), (vapor, state.vapor_state)):
            expected.basis.require_compatible(actual.basis)
            if expected.basis.fluid != "Hydrogen" or expected.basis.spin_composition != "normal":
                raise ValueError("This native-pool boundary currently admits pure normal Hydrogen only")
            for name in ("pressure_pa", "temperature_k", "enthalpy_j_kg", "internal_energy_j_kg", "density_kg_m3"):
                if abs(getattr(actual, name)-getattr(expected, name)) > tol.property_relative*max(1., abs(getattr(expected, name))):
                    raise ValueError("Incident phase state differs from the actual native saturation EOS")
            if actual.vapor_mass_fraction != expected.vapor_mass_fraction:
                raise ValueError("Incident saturation quality differs from the native EOS endpoint")
        finite(vapor.enthalpy_j_kg-liquid.enthalpy_j_kg, "native latent enthalpy", positive=True)
        diameter = (6*state.mass_kg/(math.pi*liquid.density_kg_m3))**(1/3)
        if abs(diameter-state.diameter_m) > tol.property_relative*diameter:
            raise ValueError("Incident spherical diameter is inconsistent with its native liquid mass/density")
        if temperature < liquid.temperature_k:
            raise ValueError("Finite patch has no positive boiling heat; subcooling/condensation is unsupported")
        sigma = finite(trace.boundary.surface_tension_n_m, "evidenced incident surface tension", positive=True)
        weber = liquid.density_kg_m3*velocity[2]**2*state.diameter_m/sigma
        q = self.closure.qualification
        for value, bounds in ((liquid.pressure_pa, q.pressure_bounds_pa),
                (temperature, q.wall_temperature_bounds_k), (state.diameter_m, q.diameter_bounds_m),
                (-velocity[2], q.normal_speed_bounds_m_s), (weber, q.impact_weber_bounds)):
            if not bounds[0] <= value <= bounds[1]:
                raise ValueError("Incident/contact leaves the explicit outcome qualification domain")
        trace.require_current()
        return ImpactContext(trace, state, self.patch, temperature, liquid, vapor, weber)

    def _intercontact_exchange(self, start, end, temperature):
        context = IntercontactThermalContext(self.patch, start, end, temperature,
                                             self.patch.heat_capacity_j_k)
        if self.intercontact_heat is None:
            result = IntercontactThermalResult(start, end, 0., temperature, temperature,
                self.patch.intercontact_thermal_evidence_id, self.patch.origin,
                (self.patch, self.patch.intercontact_thermal_evidence_id))
        else:
            result = self.intercontact_heat(context)
            self._guard()
            _validate(result, IntercontactThermalResult)
            if result.start_time_s != start or result.end_time_s != end:
                raise ValueError("Intercontact heat result must match the actual event-clock interval")
        expected_temperature = finite(temperature + result.heat_into_patch_j/self.patch.heat_capacity_j_k,
                                      "post-intercontact wall temperature", positive=True)
        tolerance = finite(self.tolerances.property_relative*max(1., abs(expected_temperature)),
                           "intercontact temperature tolerance", positive=True)
        if not result.minimum_temperature_k-tolerance <= temperature <= result.maximum_temperature_k+tolerance:
            raise ValueError("Intercontact thermal extrema omit the interval's initial wall state")
        if not result.minimum_temperature_k-tolerance <= expected_temperature <= result.maximum_temperature_k+tolerance:
            raise ValueError("Intercontact thermal extrema omit the interval's final wall state")
        if end == start and (result.minimum_temperature_k != temperature
                             or result.maximum_temperature_k != temperature):
            raise ValueError("Zero-duration intervals cannot contain thermal excursions")
        if (result.minimum_temperature_k < self.patch.minimum_temperature_k
                or result.maximum_temperature_k > self.patch.maximum_temperature_k):
            raise ValueError("Intercontact thermal path leaves the finite surface material domain")
        bounds = self.closure.qualification.wall_temperature_bounds_k
        if (result.minimum_temperature_k < bounds[0] or result.maximum_temperature_k > bounds[1]):
            raise ValueError("Intercontact thermal path leaves the admitted impact qualification")
        return result, expected_temperature

    def _trial(self, context, outcome, vapor_mass):
        m, patch = context.incident.mass_kg, context.patch
        x = finite(vapor_mass, "trial vapor mass")
        if not 0 <= x <= m:
            raise ValueError("Vapor root cannot leave the finite incident mass")
        remaining = m-x
        deposited = remaining*outcome.deposited_fraction_of_remaining_liquid
        rebound = remaining-deposited
        v = context.incident.velocity_m_s
        relative_rebound = (outcome.tangential_retention*v[0], outcome.tangential_retention*v[1],
                            -outcome.normal_restitution*v[2])
        relative_vapor = outcome.vapor_velocity_relative_to_recoil_m_s
        recoil = tuple((m*u-rebound*r-x*w)/(patch.effective_recoil_mass_kg+m)
                       for u, r, w in zip(v, relative_rebound, relative_vapor, strict=True))
        rebound_velocity = tuple(u+r for u, r in zip(recoil, relative_rebound, strict=True))
        vapor_velocity = tuple(u+w for u, w in zip(recoil, relative_vapor, strict=True))
        if (rebound > 0 and rebound_velocity[2] < 0) or (x > 0 and vapor_velocity[2] < 0):
            raise ValueError("Qualified rebound/vapor exits into the solid rather than away from it")
        kinetic_in = .5*m*math.fsum(u*u for u in v)
        outgoing = .5*rebound*math.fsum(u*u for u in rebound_velocity)+.5*x*math.fsum(u*u for u in vapor_velocity)
        arrest = .5*(patch.effective_recoil_mass_kg+deposited)*math.fsum(u*u for u in recoil)
        collision = math.fsum((kinetic_in, -outgoing, -arrest, -outcome.interfacial_internal_energy_change_j))
        if collision < -self.tolerances.energy_j:
            raise ValueError("Outcome requires unprovided active mechanical work before grounding")
        heat = collision+arrest
        mount = tuple((patch.effective_recoil_mass_kg+deposited)*u for u in recoil)
        momentum_error = tuple(m*u-rebound*r-x*w-j for u, r, w, j in zip(v, rebound_velocity, vapor_velocity, mount, strict=True))
        temperature = context.wall_temperature_k+heat/patch.heat_capacity_j_k
        if not patch.minimum_temperature_k <= temperature <= patch.maximum_temperature_k:
            raise ValueError("Mechanical heating leaves the finite patch material temperature domain")
        bounds = self.closure.qualification.wall_temperature_bounds_k
        if not bounds[0] <= temperature <= bounds[1]:
            raise ValueError("Mechanical heating leaves the original impact/contact qualification")
        if temperature < context.liquid_state.temperature_k:
            raise ValueError("Outcome leaves no admissible positive wall-to-liquid phase heat")
        exposure = finite(outcome.contact_conductance_w_k*outcome.contact_duration_s/patch.heat_capacity_j_k,
                          "finite contact conductance exposure")
        contact_heat = patch.heat_capacity_j_k*(temperature-context.liquid_state.temperature_k)*(-math.expm1(-exposure))
        latent = context.vapor_state.enthalpy_j_kg-context.liquid_state.enthalpy_j_kg
        residual = x*latent-contact_heat
        values = (kinetic_in, outgoing, collision, arrest, heat, contact_heat, residual, *recoil,
                  *mount, *momentum_error)
        if not all(math.isfinite(z) for z in values):
            raise ValueError("Nonfinite mechanical/finite-contact phase trial")
        return MechanicalTrial(x, deposited, rebound, recoil, rebound_velocity, vapor_velocity,
            kinetic_in, outgoing, collision, arrest, heat, mount, momentum_error,
            temperature, contact_heat, residual)

    def run(self, incidents) -> SurfaceImpactTrace:
        """Sequence on a thermally finite patch with an explicit gap boundary.

        The dry-patch clearing boundary sends each deposited batch to a separate
        at-rest receiver. It carries liquid energy; it does not erase heat or
        pool inventory. A wet-pool impact is outside this model.
        """
        completed, trials, incident, context, outcome, root, candidate = [], [], None, None, None, None, None
        try:
            from scipy.optimize import brentq

            self._guard()
            incidents = tuple(incidents)
            if not incidents:
                raise ValueError("Supply at least one original finite incident trace")
            wall = self.patch.initial_temperature_k
            last_end = self.patch.initial_time_s
            for incident in incidents:
                trials, context, outcome, root, candidate = [], None, None, None, None
                if not incident.states:
                    raise ValueError("Incident parcel trace must retain its accepted event state")
                gap, wall = self._intercontact_exchange(last_end, incident.states[-1].time_s, wall)
                context = self._context(incident, wall)
                if context.incident.time_s < last_end:
                    raise ValueError("Surface contacts overlap or arrive out of clock order")
                outcome = self.closure.evaluate(context)
                self._guard()
                _validate(outcome, ImpactOutcome)
                end = finite(context.incident.time_s+outcome.contact_duration_s, "absolute contact endpoint")
                if (end <= context.incident.time_s
                        or abs((end-context.incident.time_s)-outcome.contact_duration_s) > self.tolerances.clock_s):
                    raise ValueError("Absolute clock cannot resolve the qualified finite contact duration")

                def residual(vapor_mass):
                    self._guard()
                    trial = self._trial(context, outcome, vapor_mass)
                    trials.append(trial)
                    return trial.latent_residual_j

                zero = residual(0.)
                full = None if zero == 0 else residual(context.incident.mass_kg)
                dryout = full is not None and full <= 0
                if zero == 0:
                    vapor_mass = 0.
                    dryout = False
                elif dryout:
                    vapor_mass = context.incident.mass_kg
                elif full is not None and zero < 0 < full:
                    vapor_mass, root = brentq(residual, 0., context.incident.mass_kg,
                        xtol=self.tolerances.root_mass_kg, rtol=4*math.ulp(1.), full_output=True)
                    if not root.converged:
                        raise RuntimeError("Native generic root did not converge on finite phase mass")
                else:
                    raise ValueError("Finite contact/phase energy has no admissible bracket")
                mechanical = self._trial(context, outcome, vapor_mass)
                trials.append(mechanical)
                latent = vapor_mass*(context.vapor_state.enthalpy_j_kg-context.liquid_state.enthalpy_j_kg)
                final_wall = mechanical.wall_post_mechanical_temperature_k-latent/self.patch.heat_capacity_j_k
                active = outcome.contact_duration_s
                if dryout:
                    capacity = self.patch.heat_capacity_j_k*(mechanical.wall_post_mechanical_temperature_k-context.liquid_state.temperature_k)
                    if (outcome.contact_conductance_w_k <= 0 or not 0 < latent < capacity):
                        raise ValueError("Dryout requires a finite positive, strictly available contact heat capacity")
                    active = -self.patch.heat_capacity_j_k/outcome.contact_conductance_w_k*math.log1p(-latent/capacity)
                    if not 0 < active <= outcome.contact_duration_s:
                        raise ValueError("Dryout time is outside the original finite contact window")
                elif abs(mechanical.latent_residual_j) > self.tolerances.energy_j:
                    raise ValueError("Finite phase root exceeds the explicit latent-energy acceptance budget")
                if not self.patch.minimum_temperature_k <= final_wall <= self.patch.maximum_temperature_k:
                    raise ValueError("Final surface temperature leaves the original material domain")
                bounds = self.closure.qualification.wall_temperature_bounds_k
                if not bounds[0] <= final_wall <= bounds[1]:
                    raise ValueError("Contact cooling leaves the original outcome qualification")
                if dryout:
                    end = finite(context.incident.time_s+active, "absolute dryout endpoint")
                    if (end <= context.incident.time_s
                            or abs((end-context.incident.time_s)-active) > self.tolerances.clock_s):
                        raise ValueError("Absolute clock cannot resolve the finite dryout event")
                fluid_u = vapor_mass*(context.vapor_state.internal_energy_j_kg-context.liquid_state.internal_energy_j_kg)
                pressure_work = -context.liquid_state.pressure_pa*vapor_mass*(
                    1/context.vapor_state.density_kg_m3-1/context.liquid_state.density_kg_m3)
                wall_u = self.patch.heat_capacity_j_k*(final_wall-wall)
                energy = math.fsum((fluid_u, wall_u, mechanical.outgoing_kinetic_energy_j,
                    -mechanical.initial_kinetic_energy_j, outcome.interfacial_internal_energy_change_j, -pressure_work))
                mass_error = context.incident.mass_kg-mechanical.deposited_mass_kg-mechanical.rebound_mass_kg-vapor_mass
                batch = DepositedBatch(self.patch.location, end, mechanical.deposited_mass_kg,
                    context.liquid_state, (0., 0., 0.), outcome.evidence_id, incident)
                candidate = ImpactStep(context, outcome, mechanical, gap, end, active, dryout, final_wall,
                    wall_u, latent, fluid_u, pressure_work, outcome.interfacial_internal_energy_change_j,
                    energy, mass_error, root, tuple(trials), batch)
                values = (wall_u, latent, fluid_u, pressure_work, energy, mass_error, active, final_wall)
                if (not all(math.isfinite(value) for value in values)
                        or abs(energy) > self.tolerances.energy_j or abs(mass_error) > self.tolerances.mass_kg
                        or max(abs(x) for x in mechanical.momentum_residual_kg_m_s) > self.tolerances.momentum_kg_m_s):
                    raise ValueError("Finite surface total-U/pressure-work/mass/momentum audit failed")
                self._guard()
                self._issued_steps[id(candidate)] = (candidate, _step_binding(candidate))
                completed.append(candidate)
                wall, last_end = final_wall, end
            incoming = math.fsum(s.context.incident.mass_kg for s in completed)
            deposited = math.fsum(s.mechanical.deposited_mass_kg for s in completed)
            rebound = math.fsum(s.mechanical.rebound_mass_kg for s in completed)
            vapor = math.fsum(s.mechanical.vapor_mass_kg for s in completed)
            token = object()
            _PENDING_SURFACE_TRACE_ISSUERS.add(token)
            try:
                return SurfaceImpactTrace(
                    self.patch, self.closure, self.properties, tuple(completed), wall,
                    incoming, deposited, rebound, vapor,
                    math.fsum((incoming, -deposited, -rebound, -vapor)),
                    math.fsum(s.total_energy_residual_j for s in completed),
                    _owner=self, _token=token,
                )
            except Exception:
                _PENDING_SURFACE_TRACE_ISSUERS.discard(token)
                raise
        except Exception as cause:
            raise SurfaceImpactError(cause, model=self, completed_steps=completed, incident=incident,
                context=context, outcome=outcome, trials=trials, native_root_result=root,
                failed_step=candidate) from cause


def prepare_native_fixed_area_pool(step: ImpactStep, native_config, *, impact_owner: FiniteSurfaceImpact,
                                   separate_continuation_heat_owner,
                                   continuation_evidence_id: str) -> NativePoolInitialization:
    """Prepare actual native initial-stock objects, without running a pool.

    Dynamic spreading presently refuses initial stock. Never smear this batch
    into a fabricated arrival interval. The fixed-area native kernel admits
    initial stock, but its separately declared substrate heat is not this finite
    patch's continuation. No coupled continuation/global heat closure is claimed.
    """
    import importlib
    from importlib import metadata

    if not isinstance(step, ImpactStep):
        raise TypeError("Use the original audited ImpactStep")
    if not isinstance(impact_owner, FiniteSurfaceImpact):
        raise TypeError("Retain the actual finite impact owner for native stock admission")
    FiniteSurfaceImpact.require_original_step(impact_owner, step)
    if separate_continuation_heat_owner is None:
        raise ValueError("Declare the separate pool heat owner; no finite-patch reset is inferred")
    _text(continuation_evidence_id, "separate pool continuation evidence")
    if metadata.version("dynamiclh2poolx") != "0.2.0rc2":
        raise ValueError("Use the existing reviewed DynamicLH2PoolX version")
    native = importlib.import_module("dynamiclh2poolx")
    reviewed = {"dynamic_fixed_area.py": "f73dcb2ddbeb16e27b98600fdf6b1ee91c083602d8528e7e27eddc32d68bfc43",
                "inflow.py": "e48527d39315167f2f1f03098725453133c16191eefd372fc733bbf76718dce6",
                "__init__.py": "e9980ba436db5ce32f2214397319f6fa44d724d5cda8a14e1588979620e34ef6"}
    directory = Path(native.__file__).resolve().parent
    if any(hashlib.sha256((directory/name).read_bytes()).hexdigest() != digest
           for name, digest in reviewed.items()):
        raise ValueError("Reviewed native initial-stock API source changed")
    if (native.run_fixed_area_pool.__module__ != "dynamiclh2poolx.dynamic_fixed_area"
            or Path(native.run_fixed_area_pool.__code__.co_filename).resolve() != directory/"dynamic_fixed_area.py"
            or native.FixedAreaPoolConfig.__module__ != "dynamiclh2poolx.dynamic_fixed_area"
            or native.DeclaredInflow.__module__ != "dynamiclh2poolx.inflow"):
        raise ValueError("Use the original native initial-stock API bindings")
    if type(native_config) is not native.FixedAreaPoolConfig:
        raise TypeError("Supply the actual native fixed-area config with explicitly chosen substrate")
    if step.context.liquid_state.basis.fluid != "Hydrogen" or step.context.liquid_state.basis.spin_composition != "normal":
        raise ValueError("Actual native pool requires normal Hydrogen")
    if step.deposited_batch.velocity_m_s != (0., 0., 0.):
        raise ValueError("Native pool accepts at-rest deposited liquid only")
    config = dataclasses.replace(native_config, initial_liquid_mass_kg=step.deposited_batch.mass_kg,
                                ambient_pressure_Pa=step.deposited_batch.state.pressure_pa)
    inflow = native.DeclaredInflow((0.,), (0.,))
    return NativePoolInitialization(step.deposited_batch, config, inflow, native.run_fixed_area_pool,
        native, step.contact_end_s, step.deposited_batch.location.clock_id,
        separate_continuation_heat_owner, continuation_evidence_id, impact_owner, step)


def failure_snapshot(error: SurfaceImpactError):
    """Inspect original failure objects without a serialization protocol."""
    if not isinstance(error, SurfaceImpactError):
        raise TypeError("Use an actual retained surface-impact failure")
    return MappingProxyType({"cause": error.cause, "completed_steps": error.completed_steps,
        "incident": error.incident, "context": error.context, "outcome": error.outcome,
        "trials": error.trials, "native_root_result": error.native_root_result,
        "failed_step": error.failed_step})
