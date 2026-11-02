"""Finite normal-LH2 consumption and actual native fire radiation; unverified.

PRCT owns finite pool consumption and the restricted sphere/view-factor model.
The shared reaction core owns finite H2/O2 conversion. No burning correlation,
pool-spreading/heat-feedback solver or ignition model is implemented here.
"""

import dataclasses
import importlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import Origin, PropertyBasis, ThermoState, finite
from ..reactions import StoichiometricReaction
from ..release import SourceLocation
from ..sources import IntervalMassSource
from .conditional_risk import ConditionalRiskNative, finite_source_sha256
from .pool import NativePoolRun
from .result_provenance import recorded_content_sha256

STATUS = "implemented_unverified"
_PENDING_POOL_FIRE_TRACE_ISSUERS: set[object] = set()


def _native_result_snapshot(value):
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        # model_dump returns a fresh mapping. The generic retained-content seal
        # includes mapping identity, so hash its canonical values rather than
        # the identity of this temporary serialization container.
        return (id(value), json.dumps(dump(mode="json"), sort_keys=True,
            separators=(",", ":"), allow_nan=False))
    if dataclasses.is_dataclass(value):
        return value
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return (id(value), attributes)
    return (id(value),)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")


def _origin(value):
    result = Origin(value)
    if result == Origin.UNRESOLVED:
        raise ValueError("Source/parameter origin must be explicit")
    return result


def _state(value):
    if not isinstance(value, ThermoState):
        raise TypeError("An actual thermodynamic state is required")
    ThermoState(**{f.name: getattr(value, f.name) for f in dataclasses.fields(value)})
    if not isinstance(value.basis, PropertyBasis):
        raise TypeError("Declare the actual fluid/energy/spin PropertyBasis")
    PropertyBasis(**{f.name: getattr(value.basis, f.name) for f in dataclasses.fields(value.basis)})
    if value.basis.fluid != "Hydrogen" or value.basis.spin_composition != "normal":
        raise ValueError("This level admits explicitly normal pure H2; no spin/fluid conversion")


@dataclass(frozen=True, slots=True)
class PoolFireNative:
    toolkit: ConditionalRiskNative
    fire: Any
    bindings: tuple

    @staticmethod
    def _bindings(module):
        functions = (module.pool, module.sphere, module.solid_flame)
        path = Path(module.__file__).resolve()
        for function in functions:
            if (function.__module__ != "ccps_consequence.fire"
                    or Path(function.__code__.co_filename).resolve() != path):
                raise ValueError("Native fire calls do not originate in the reviewed source")
        return tuple((f, f.__code__) for f in functions)+(module.PoolInput, module.PoolOutput,
            module.SphereInput, module.SphereOutput, module.SolidFlameInput, module.FluxOutput)

    @classmethod
    def from_installed(cls):
        """Reuse the reviewed PRCT artifact loader; no physics executed here."""
        toolkit = ConditionalRiskNative.from_installed()
        fire = importlib.import_module("ccps_consequence.fire")
        return cls(toolkit, fire, cls._bindings(fire))

    def require_current(self):
        self.toolkit.require_current()
        if self._bindings(self.fire) != self.bindings:
            raise ValueError("Actual native fire function/class bindings changed")


@dataclass(frozen=True, slots=True)
class PoolFireSeed:
    time_s: float
    liquid_mass_kg: float
    area_m2: float
    location: SourceLocation
    liquid_state: ThermoState
    vapor_state: ThermoState
    thermodynamic_owner: Any
    evidence_id: str
    origin: Origin
    native_pool_run: NativePoolRun | None = None
    preignition_evaporation: IntervalMassSource | None = None
    preignition_source_sha256: str | None = None
    deposited_pool_continuation: Any = None
    ignition_transition_evidence_id: str | None = None
    continuation_temperature_tolerance_k: float | None = None
    continuation_density_relative_tolerance: float | None = None

    def __post_init__(self):
        finite(self.time_s, "seed clock")
        if finite(self.liquid_mass_kg, "finite LH2 mass") < 0:
            raise ValueError("Pool mass cannot be negative")
        finite(self.area_m2, "fixed pool area", positive=True)
        if not isinstance(self.location, SourceLocation):
            raise TypeError("Declare physical source location/frame/clock")
        SourceLocation(**{f.name: getattr(self.location, f.name) for f in dataclasses.fields(self.location)})
        _state(self.liquid_state)
        _state(self.vapor_state)
        self.liquid_state.basis.require_compatible(self.vapor_state.basis)
        if (self.liquid_state.vapor_mass_fraction != 0.
                or self.vapor_state.vapor_mass_fraction != 1.
                or abs(self.liquid_state.temperature_k-self.vapor_state.temperature_k) > 1e-7
                or abs(self.liquid_state.pressure_pa-self.vapor_state.pressure_pa) > 1e-6
                or self.vapor_state.enthalpy_j_kg <= self.liquid_state.enthalpy_j_kg):
            raise ValueError("Native saturated liquid/vapor states on one pressure/reference are required")
        if self.thermodynamic_owner is None:
            raise ValueError("Retain the actual native thermodynamic/pool owner")
        _text(self.evidence_id, "seed evidence")
        object.__setattr__(self, "origin", _origin(self.origin))
        if self.preignition_evaporation is not None:
            self.preignition_evaporation.require_current()
            if finite_source_sha256(self.preignition_evaporation) != self.preignition_source_sha256:
                raise ValueError("Original preignition source contents changed")
            if self.preignition_evaporation.edges_s[-1] != self.time_s:
                raise ValueError("Preignition source must end at the exact ignition handoff")
        if self.deposited_pool_continuation is not None:
            self._require_deposited_continuation()

    def _require_deposited_continuation(self):
        from .parcel_pool_chain import ParcelPoolContinuation

        parent = self.deposited_pool_continuation
        if type(parent) is not ParcelPoolContinuation or self.thermodynamic_owner is not parent:
            raise TypeError("Retain the exact deposited-stock pool continuation")
        parent.require_current()
        _text(self.ignition_transition_evidence_id, "pool-to-fire transition evidence")
        t_budget = finite(self.continuation_temperature_tolerance_k, "pool temperature budget", positive=True)
        rho_budget = finite(self.continuation_density_relative_tolerance, "pool density relative budget", positive=True)
        last = parent.native_result.ledger[-1]
        batch = parent.initialization.batch
        endpoint_temperature = finite(last.pool_temperature_K, "native pool endpoint temperature K", positive=True)
        endpoint_density = finite(last.liquid_density_kg_m3, "native pool endpoint density kg/m3", positive=True)
        native_pressure = finite(parent.initialization.native_config.ambient_pressure_Pa,
                                 "native pool ambient pressure Pa", positive=True)
        if (self.time_s != parent.absolute_times_s[-1]
                or self.liquid_mass_kg != last.liquid_mass_kg
                or self.area_m2 != last.area_m2
                or self.area_m2 != parent.initialization.native_config.area_m2
                or self.location is not parent.vapor_source.location
                or self.liquid_state is not batch.state
                or self.vapor_state is not parent.vapor_source.state
                or self.preignition_evaporation is not parent.vapor_source):
            raise ValueError("Fire seed differs from original remaining pool stock/state/geometry/clock")
        if (not math.isclose(native_pressure, self.liquid_state.pressure_pa,
                             rel_tol=1e-10, abs_tol=1e-6)
                or abs(endpoint_temperature-self.liquid_state.temperature_k) > t_budget
                or not math.isclose(endpoint_density, self.liquid_state.density_kg_m3,
                                    rel_tol=rho_budget, abs_tol=0.)):
            raise ValueError("Native pool endpoint differs from the declared saturated fire fuel state")

    @classmethod
    def from_native_pool(cls, run: NativePoolRun, *, evidence_id: str):
        """Transfer only the final admissible preignition stock, not future outputs."""
        if not isinstance(run, NativePoolRun) or not run.admissible:
            raise ValueError("Supply the original admissible native preignition pool result")
        if run.inflow.schedule_rates_kg_s[-1] != 0.:
            raise ValueError("Native fire/pool-energy does not support replenishment")
        sample = run.samples[-1]
        source = run.evaporation_source()
        return cls(sample.time_s, sample.native.liquid_mass_kg, sample.native.area_m2,
            run.inflow.location, run.liquid_state, run.vapor_state, run,
            evidence_id, Origin.PREDICTED, run, source, finite_source_sha256(source))

    @classmethod
    def from_deposited_pool(cls, continuation, *, evidence_id,
                            ignition_transition_evidence_id,
                            temperature_absolute_tolerance_k, density_relative_tolerance):
        """Transfer exact final deposited-pool stock under an explicit fire transition.

        Caller must still supply DeclaredIgnition, burn flux, conditioning budget,
        oxygen stock and fire geometry. No postignition pool heat law is inferred.
        """
        from .parcel_pool_chain import ParcelPoolContinuation

        if type(continuation) is not ParcelPoolContinuation:
            raise TypeError("Supply the original deposited-stock pool continuation")
        continuation.require_current()
        last = continuation.native_result.ledger[-1]
        source = continuation.vapor_source
        return cls(
            continuation.absolute_times_s[-1], last.liquid_mass_kg, last.area_m2,
            source.location, continuation.initialization.batch.state, source.state,
            continuation, evidence_id, Origin.PREDICTED,
            preignition_evaporation=source, preignition_source_sha256=finite_source_sha256(source),
            deposited_pool_continuation=continuation,
            ignition_transition_evidence_id=ignition_transition_evidence_id,
            continuation_temperature_tolerance_k=temperature_absolute_tolerance_k,
            continuation_density_relative_tolerance=density_relative_tolerance,
        )


@dataclass(frozen=True, slots=True)
class H2CombustionReference:
    lower_heating_value_j_kg: float
    reference_hydrogen: ThermoState
    lhv_evidence_id: str
    hydrogen_applicability_id: str
    oxidizer_reference_id: str
    origin: Origin
    water_product_phase: str
    combustion_efficiency: float

    def __post_init__(self):
        finite(self.lower_heating_value_j_kg, "caller-evidenced H2 LHV", positive=True)
        _state(self.reference_hydrogen)
        if self.reference_hydrogen.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("LHV reference fuel must be native gas-phase H2")
        for name in ("lhv_evidence_id", "hydrogen_applicability_id", "oxidizer_reference_id"):
            _text(getattr(self, name), name)
        finite(self.combustion_efficiency, "explicit complete-combustion efficiency")
        if self.water_product_phase != "vapor" or self.combustion_efficiency != 1.:
            raise ValueError("First level requires LHV/water vapor and complete combustion; no missing chemical fate")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class ExternalConditioningBudget:
    clock_id: str
    available_energy_j: float
    maximum_power_w: float
    evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("clock_id", "evidence_id"):
            _text(getattr(self, name), name)
        for name in ("available_energy_j", "maximum_power_w"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError("Declared external conditioning capacities cannot be negative")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class DeclaredIgnition:
    time_s: float
    clock_id: str
    evidence_id: str
    origin: Origin

    def __post_init__(self):
        finite(self.time_s, "explicit ignition clock")
        _text(self.clock_id, "ignition clock")
        _text(self.evidence_id, "ignition/support evidence")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class PoolFireStage:
    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    burning_flux_kg_m2_s: float
    burning_flux_evidence_id: str
    sphere_diameter_m: float
    sphere_geometry_evidence_id: str
    radiative_fraction: float
    convective_export_fraction: float
    energy_partition_evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("identifier", "clock_id", "burning_flux_evidence_id",
                     "sphere_geometry_evidence_id", "energy_partition_evidence_id"):
            _text(getattr(self, name), name)
        if finite(self.end_s, "stage end") <= finite(self.start_s, "stage start"):
            raise ValueError("A finite increasing fire window is required")
        finite(self.end_s-self.start_s, "finite stage duration", positive=True)
        if finite(self.burning_flux_kg_m2_s, "caller-supplied H2 net burning flux") < 0:
            raise ValueError("Burning flux cannot be negative")
        finite(self.sphere_diameter_m, "supplied uniform sphere diameter", positive=True)
        for fraction in (self.radiative_fraction, self.convective_export_fraction):
            if not 0 <= finite(fraction, "explicit energy fraction") <= 1:
                raise ValueError("Radiation/convective export fractions lie in [0,1]")
        if self.radiative_fraction+self.convective_export_fraction > 1:
            raise ValueError("Radiative plus convective export exceeds released energy")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class GroundVerticalReceptor:
    identifier: str
    clock_id: str
    frame_id: str
    position_m: tuple[float, float, float]
    normal_unit: tuple[float, float, float]
    transmissivity: float
    geometry_evidence_id: str
    transmissivity_evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("identifier", "clock_id", "frame_id", "geometry_evidence_id",
                     "transmissivity_evidence_id"):
            _text(getattr(self, name), name)
        for name in ("position_m", "normal_unit"):
            vector = tuple(finite(v, name) for v in getattr(self, name))
            if len(vector) != 3:
                raise ValueError("Receptor position/normal require three coordinates")
            object.__setattr__(self, name, vector)
        if not math.isclose(math.sqrt(sum(v*v for v in self.normal_unit)), 1., abs_tol=1e-10):
            raise ValueError("Receptor normal must already be unit length")
        if not 0 <= finite(self.transmissivity, "caller atmospheric transmissivity") <= 1:
            raise ValueError("Transmissivity must lie in [0,1]")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class PoolFireTolerances:
    mass_kg: float = 1e-10
    energy_j: float = 1e-5
    flux_w_m2: float = 1e-8
    geometry_m: float = 1e-9
    clock_s: float = 1e-9

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class ReceptorRadiation:
    receptor: GroundVerticalReceptor
    native_sphere_input: Any
    native_sphere_result: Any
    native_solid_input: Any
    native_solid_result: Any
    active_start_s: float
    active_end_s: float
    incident_flux_w_m2: float
    incident_energy_j_m2: float
    convective_flux_w_m2: None = None


@dataclass(frozen=True, slots=True)
class PoolFireStep:
    stage: PoolFireStage
    native_pool_input: Any
    native_pool_result: Any
    reaction_conversion: Any
    initial_liquid_kg: float
    remaining_liquid_kg: float
    vaporized_and_combusted_kg: float
    active_end_s: float
    oxygen_remaining_mol: float
    water_product_mol: float
    latent_conditioning_j: float
    sensible_conditioning_j: float
    chemical_energy_j: float
    radiation_export_j: float
    convective_export_j: float
    unallocated_release_j: float
    remaining_conditioning_budget_j: float
    emitted_surface_power_w_m2: float
    mass_residual_kg: float
    energy_partition_residual_j: float
    native_energy_residual_j: float
    native_power_energy_residual_j: float
    receptors: tuple[ReceptorRadiation, ...]


@dataclass(frozen=True, slots=True)
class PoolFireTrace:
    seed: PoolFireSeed
    ignition: DeclaredIgnition
    reference: H2CombustionReference
    conditioning: ExternalConditioningBudget
    steps: tuple[PoolFireStep, ...]
    native_provider: PoolFireNative
    reaction: StoichiometricReaction
    initial_oxygen_mol: float
    initial_water_mol: float
    fuel_to_flame: IntervalMassSource
    heat_feedback_solved: bool = False
    postignition_spreading_solved: bool = False
    ignition_probability_solved: bool = False
    dispersion_solved: bool = False
    total_pool_flame_internal_energy_solved: bool = False
    external_conditioning_heat_transfer_solved: bool = False
    full_cryogenic_fire_chain_validated: bool = False
    status: str = STATUS
    _issuer: object = dataclasses.field(default=None, repr=False, compare=False)
    _receipt_owner: object = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _signature: str = dataclasses.field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_POOL_FIRE_TRACE_ISSUERS:
            raise TypeError("Create pool-fire traces through a completed finite native run")
        _PENDING_POOL_FIRE_TRACE_ISSUERS.remove(self._issuer)
        object.__setattr__(self, "_receipt_owner", self)
        if (type(self.seed) is not PoolFireSeed
                or type(self.ignition) is not DeclaredIgnition
                or type(self.reference) is not H2CombustionReference
                or type(self.conditioning) is not ExternalConditioningBudget
                or type(self.native_provider) is not PoolFireNative
                or type(self.reaction) is not StoichiometricReaction
                or type(self.fuel_to_flame) is not IntervalMassSource
                or not self.steps):
            raise TypeError("Retain the original typed finite fire inputs, outputs and source")
        if self.status != STATUS or any((
            self.heat_feedback_solved, self.postignition_spreading_solved,
            self.ignition_probability_solved, self.dispersion_solved,
            self.total_pool_flame_internal_energy_solved,
            self.external_conditioning_heat_transfer_solved,
            self.full_cryogenic_fire_chain_validated,
        )):
            raise ValueError("A pool-fire trace cannot claim an unimplemented model level")
        object.__setattr__(self, "_signature", self._content())
        self.require_current()

    def _content(self):
        native_records = tuple((
            _native_result_snapshot(step.native_pool_input),
            _native_result_snapshot(step.native_pool_result),
            tuple((
                _native_result_snapshot(row.native_sphere_input),
                _native_result_snapshot(row.native_sphere_result),
                _native_result_snapshot(row.native_solid_input),
                _native_result_snapshot(row.native_solid_result),
            ) for row in step.receptors),
        ) for step in self.steps)
        return recorded_content_sha256((
            self.seed, self.ignition, self.reference, self.conditioning, self.steps,
            self.native_provider, self.reaction, self.initial_oxygen_mol,
            self.initial_water_mol, self.fuel_to_flame, native_records,
            self.heat_feedback_solved, self.postignition_spreading_solved,
            self.ignition_probability_solved, self.dispersion_solved,
            self.total_pool_flame_internal_energy_solved,
            self.external_conditioning_heat_transfer_solved,
            self.full_cryogenic_fire_chain_validated, self.status,
        ))

    def require_current(self):
        if self._receipt_owner is not self:
            raise ValueError("Pool-fire trace is not the original owner-issued result")
        if self.status != STATUS or any((
            self.heat_feedback_solved, self.postignition_spreading_solved,
            self.ignition_probability_solved, self.dispersion_solved,
            self.total_pool_flame_internal_energy_solved,
            self.external_conditioning_heat_transfer_solved,
            self.full_cryogenic_fire_chain_validated,
        )):
            raise ValueError("Pool-fire trace status or scope flags changed")
        self.native_provider.require_current()
        self.fuel_to_flame.require_current()
        if self._content() != self._signature:
            raise ValueError("Pool-fire source, accepted native outputs or retained audit changed")
        return self


class PoolFireError(RuntimeError):
    def __init__(self, message, *, model, stage=None, completed_steps=(), native_attempt=None,
                 failed_step=None):
        super().__init__(message)
        self.model, self.stage = model, stage
        self.completed_steps = tuple(completed_steps)
        self.native_attempt = MappingProxyType(dict(native_attempt or {}))
        self.failed_step = failed_step


class FinitePoolFire:
    """Fixed-area complete H2 burning reference with supplied flame geometry.

    No replenishment or additional evaporation sink is supported after the seed.
    Each consumed kilogram is explicitly gasified, conditioned and combusted.
    External conditioning capacity is declared; fire feedback is not inferred.
    """

    def __init__(self, native: PoolFireNative, seed: PoolFireSeed,
                 reference: H2CombustionReference, reaction: StoichiometricReaction, *,
                 hydrogen_id: str, oxygen_id: str, water_id: str,
                 tolerances: PoolFireTolerances = PoolFireTolerances()):
        if not isinstance(native, PoolFireNative) or not isinstance(reaction, StoichiometricReaction):
            raise TypeError("Actual reviewed native fire provider and shared reaction are required")
        for obj, cls in ((seed, PoolFireSeed), (reference, H2CombustionReference),
                         (tolerances, PoolFireTolerances)):
            if not isinstance(obj, cls):
                raise TypeError(f"An actual {cls.__name__} is required")
            cls(**{f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)})
        native.require_current()
        seed.liquid_state.basis.require_compatible(reference.reference_hydrogen.basis)
        if abs(seed.liquid_state.pressure_pa-reference.reference_hydrogen.pressure_pa) > 1e-6:
            raise ValueError("Fuel phase conditioning/LHV reference must share a pressure")
        if reference.reference_hydrogen.enthalpy_j_kg < seed.vapor_state.enthalpy_j_kg:
            raise ValueError("This external-conditioning level does not infer a cooling/recondensation path")
        ids = tuple(s.identifier for s in reaction.species)
        if set(ids) != {hydrogen_id, oxygen_id, water_id} or len(ids) != 3:
            raise ValueError("Declare only H2/O2/water in the same shared reaction")
        expected = {hydrogen_id: (-1., {"H": 2}, {"gas", "vapor"}),
                    oxygen_id: (-.5, {"O": 2}, {"gas", "vapor"}),
                    water_id: (1., {"H": 2, "O": 1}, {"vapor"})}
        for species, coefficient in zip(reaction.species, reaction.coefficients, strict=True):
            count, atoms, phases = expected[species.identifier]
            if coefficient != count or dict(species.elements) != atoms or species.phase not in phases or species.charge != 0:
                raise ValueError("Use neutral H2+0.5O2->H2O(vapor) on a consistent molar-mass basis")
        self.native, self.seed, self.reference, self.reaction = native, seed, reference, reaction
        self.hydrogen_id, self.oxygen_id, self.water_id = hydrogen_id, oxygen_id, water_id
        self.tolerances = tolerances
        self._hydrogen_molar_mass = next(s.molar_mass_kg_mol for s in reaction.species if s.identifier == hydrogen_id)
        self._configuration = self._definition()

    def _definition(self):
        return (repr(self.reference), repr(self.reaction), repr(self.tolerances),
            self.seed.time_s, self.seed.liquid_mass_kg, self.seed.area_m2, repr(self.seed.location),
            repr(self.seed.liquid_state), repr(self.seed.vapor_state), self.seed.preignition_source_sha256,
            id(self.seed.deposited_pool_continuation), self.seed.ignition_transition_evidence_id,
            self.seed.continuation_temperature_tolerance_k, self.seed.continuation_density_relative_tolerance,
            self.seed.evidence_id, self.seed.origin, id(self.seed.thermodynamic_owner),
            id(self.seed.native_pool_run), id(self.seed.preignition_evaporation),
            self.hydrogen_id, self.oxygen_id, self.water_id, self._hydrogen_molar_mass)

    def _guard(self):
        self.native.require_current()
        if self._definition() != self._configuration:
            raise ValueError("Admitted fire/source/thermochemical definitions changed")
        if self.seed.deposited_pool_continuation is not None:
            self.seed._require_deposited_continuation()
        if self.seed.preignition_evaporation is not None:
            self.seed.preignition_evaporation.require_current()
        if self.seed.preignition_evaporation is not None:
            if finite_source_sha256(self.seed.preignition_evaporation) != self.seed.preignition_source_sha256:
                raise ValueError("Preignition evaporation source changed after the handoff")

    def _radiation(self, stage, receptor, surface_power, active_end, duration, attempt):
        location, tol = self.seed.location, self.tolerances
        if receptor.clock_id != location.clock_id or receptor.frame_id != location.coordinate_frame_id:
            raise ValueError("Receptor/source frame or clock differs")
        dx = location.position_m[0]-receptor.position_m[0]
        dy = location.position_m[1]-receptor.position_m[1]
        distance = math.hypot(dx, dy)
        if abs(receptor.position_m[2]-location.position_m[2]) > tol.geometry_m or distance <= 0:
            raise ValueError("Native sphere requires a ground-level receptor outside the source")
        expected_normal = (dx/distance, dy/distance, 0.)
        if any(abs(a-b) > 1e-9 for a, b in zip(receptor.normal_unit, expected_normal, strict=True)):
            raise ValueError("Native sphere requires the supplied vertical receptor to face the flame")
        fire = self.native.fire
        x = fire.SphereInput(diameter_m=stage.sphere_diameter_m, horizontal_distance_m=distance,
            surface_emissive_power_w_m2=surface_power, transmissivity=receptor.transmissivity,
            emissive_power_basis=stage.energy_partition_evidence_id,
            geometry="ground_tangent_sphere_ground_level_vertical_receptor")
        attempt["native_sphere_input"] = x
        result = fire.sphere(x)
        attempt["native_sphere_result"] = result
        solid = fire.SolidFlameInput(surface_emissive_power_w_m2=surface_power,
            view_factor=result.view_factor, transmissivity=receptor.transmissivity,
            emissive_power_basis=stage.energy_partition_evidence_id,
            view_factor_basis=stage.sphere_geometry_evidence_id,
            applicability="supplied_solid_flame_geometry")
        attempt["native_solid_input"] = solid
        check = fire.solid_flame(solid)
        attempt["native_solid_result"] = check
        flux = finite(float(result.heat_flux_w_m2), "native receptor incident radiation")
        if flux < 0 or abs(flux-check.heat_flux_w_m2) > tol.flux_w_m2:
            raise ValueError("Actual native geometry/solid-flame radiation results disagree")
        return ReceptorRadiation(receptor, x, result, solid, check, stage.start_s,
            active_end, flux, finite(flux*duration, "finite receptor radiant exposure J/m2"))

    def run(self, stages, receptors, *, ignition: DeclaredIgnition,
            conditioning: ExternalConditioningBudget, initial_oxygen_mol: float,
            initial_water_mol: float = 0.) -> PoolFireTrace:
        completed, candidate, attempt, stage = [], None, {}, None
        try:
            self._guard()
            for obj, cls in ((ignition, DeclaredIgnition), (conditioning, ExternalConditioningBudget)):
                if not isinstance(obj, cls):
                    raise TypeError(f"An actual {cls.__name__} is required")
                cls(**{f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)})
            stages, receptors = tuple(stages), tuple(receptors)
            if not stages or not all(isinstance(s, PoolFireStage) for s in stages):
                raise ValueError("Declare nonempty finite established-burning stages")
            if not receptors or not all(isinstance(r, GroundVerticalReceptor) for r in receptors):
                raise ValueError("Declare actual source-facing ground-level receptors")
            stages = tuple(PoolFireStage(**{f.name: getattr(s, f.name) for f in dataclasses.fields(s)}) for s in stages)
            receptors = tuple(GroundVerticalReceptor(**{f.name: getattr(r, f.name) for f in dataclasses.fields(r)}) for r in receptors)
            if len({r.identifier for r in receptors}) != len(receptors):
                raise ValueError("Receptor identities must be unique")
            clock = self.seed.location.clock_id
            if (ignition.time_s != self.seed.time_s or stages[0].start_s != ignition.time_s
                    or ignition.clock_id != clock or conditioning.clock_id != clock
                    or any(s.clock_id != clock for s in stages)):
                raise ValueError("The final preignition seed and fire/conditioning clocks must meet exactly")
            if any(a.end_s != b.start_s for a, b in zip(stages[:-1], stages[1:], strict=True)):
                raise ValueError("Fire stages must be contiguous; no unmodelled intervening evaporation")
            for amount in (initial_oxygen_mol, initial_water_mol):
                if finite(amount, "finite oxygen/water amount") < 0:
                    raise ValueError("Finite chemical inventories cannot be negative")
            oxygen, water, mass = initial_oxygen_mol, initial_water_mol, self.seed.liquid_mass_kg
            budget = conditioning.available_energy_j
            edges, masses = [stages[0].start_s], []
            for stage in stages:
                candidate, attempt = None, {}
                fire = self.native.fire
                x = fire.PoolInput(area_m2=self.seed.area_m2,
                    burning_flux_kg_m2_s=stage.burning_flux_kg_m2_s, inventory_kg=mass,
                    duration_s=stage.end_s-stage.start_s,
                    heat_of_combustion_j_kg=self.reference.lower_heating_value_j_kg,
                    combustion_efficiency=self.reference.combustion_efficiency,
                    burning_flux_basis=stage.burning_flux_evidence_id,
                    applicability="constant_area_constant_burning_flux_no_replenishment")
                attempt["native_pool_input"] = x
                result = fire.pool(x)
                attempt["native_pool_result"] = result
                burned = finite(float(result.burned_mass_kg), "native fuel consumption")
                duration = finite(float(result.effective_duration_s), "native active flame duration")
                active_end = stage.start_s+duration
                if (burned < 0 or duration < 0 or not stage.start_s <= active_end <= stage.end_s
                        or (duration > 0 and active_end <= stage.start_s)
                        or abs((active_end-stage.start_s)-duration) > self.tolerances.clock_s):
                    raise ValueError("Native burnout clock cannot represent this source window")
                remaining = finite(float(result.remaining_mass_kg), "native remaining LH2")
                mass_error = mass-burned-remaining
                if (abs(mass_error) > self.tolerances.mass_kg or remaining < 0
                        or abs(burned-result.mass_rate_kg_s*duration) > self.tolerances.mass_kg):
                    raise ValueError("Actual native finite fuel mass/duration ledger does not close")
                vapor_mol = burned/self._hydrogen_molar_mass
                conversion = self.reaction.convert({self.hydrogen_id: vapor_mol,
                    self.oxygen_id: oxygen, self.water_id: water}, vapor_mol)
                attempt["reaction_conversion"] = conversion
                latent = burned*(self.seed.vapor_state.enthalpy_j_kg-self.seed.liquid_state.enthalpy_j_kg)
                sensible = burned*(self.reference.reference_hydrogen.enthalpy_j_kg-self.seed.vapor_state.enthalpy_j_kg)
                duty = latent+sensible
                required_power = result.mass_rate_kg_s*(
                    self.reference.reference_hydrogen.enthalpy_j_kg-self.seed.liquid_state.enthalpy_j_kg)
                attempt["required_conditioning_energy_j"] = duty
                attempt["required_conditioning_power_w"] = required_power
                if duty > budget or required_power > conditioning.maximum_power_w:
                    raise ValueError("Declared finite external conditioning energy/power cannot support this consumption")
                released = finite(float(result.released_energy_j), "actual native combustion energy")
                native_error = released-burned*self.reference.lower_heating_value_j_kg
                native_power_error = result.heat_release_rate_w*duration-released
                radiant = released*stage.radiative_fraction
                convective = released*stage.convective_export_fraction
                unallocated = released-radiant-convective
                area = math.pi*stage.sphere_diameter_m**2
                surface = finite(float(result.heat_release_rate_w)*stage.radiative_fraction/area,
                                 "uniform sphere emissive power")
                radiation = []
                attempt["completed_receptor_results"] = radiation
                for receptor in receptors:
                    radiation.append(self._radiation(stage, receptor, surface, active_end, duration, attempt))
                oxygen_after = conversion.final_amounts[self.oxygen_id]
                water_after = conversion.final_amounts[self.water_id]
                candidate = PoolFireStep(stage, x, result, conversion, mass, remaining, burned,
                    active_end, oxygen_after, water_after, latent, sensible, released, radiant,
                    convective, unallocated, budget-duty, surface,
                    mass_error+conversion.mass_residual_kg, released-radiant-convective-unallocated,
                    native_error, native_power_error, tuple(radiation))
                values = (latent, sensible, duty, released, radiant, convective, unallocated,
                          candidate.mass_residual_kg, candidate.energy_partition_residual_j,
                          native_error, native_power_error)
                if (not all(math.isfinite(v) for v in values)
                        or abs(candidate.mass_residual_kg) > self.tolerances.mass_kg
                        or abs(conversion.mass_residual_kg) > self.tolerances.mass_kg
                        or abs(candidate.energy_partition_residual_j) > self.tolerances.energy_j
                        or abs(native_error) > self.tolerances.energy_j
                        or abs(native_power_error) > self.tolerances.energy_j):
                    raise ValueError("Finite chemistry/phase/combustion energy audit failed")
                if duration > 0:
                    edges.append(active_end)
                    masses.append(burned)
                if active_end < stage.end_s or duration == 0:
                    edges.append(stage.end_s)
                    masses.append(0.)
                completed.append(candidate)
                mass, oxygen, water, budget = remaining, oxygen_after, water_after, budget-duty
                self._guard()
            location = dataclasses.replace(self.seed.location, source_id=self.seed.location.source_id+"-flame-reactant")
            source = IntervalMassSource(location, np.array(edges), np.array(masses),
                self.reference.reference_hydrogen, Origin.PREDICTED,
                self.reference.hydrogen_applicability_id+":conditioned-reactant-not-atmospheric-release",
                "depleted" if mass == 0 else "window_end")
            issuer = object()
            _PENDING_POOL_FIRE_TRACE_ISSUERS.add(issuer)
            try:
                trace = PoolFireTrace(
                    self.seed, ignition, self.reference, conditioning, tuple(completed),
                    self.native, self.reaction, initial_oxygen_mol, initial_water_mol, source,
                    _issuer=issuer,
                )
            except Exception:
                _PENDING_POOL_FIRE_TRACE_ISSUERS.discard(issuer)
                raise
            return trace.require_current()
        except Exception as error:
            raise PoolFireError(str(error), model=self, stage=stage, completed_steps=completed,
                                native_attempt=attempt, failed_step=candidate) from error
