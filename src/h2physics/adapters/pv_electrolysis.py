"""Native PV I–V/direct-DC electrolysis composition — implemented, unverified.

pvlib owns the diode calculation, HydrogenStack owns polarization/Faraday,
the shared reaction core owns finite conversion and an injected native gas
provider owns receiver states. No local validation has been executed.
"""

import dataclasses
import hashlib
import importlib
import json
import math
import weakref
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import Origin, ThermoState, finite
from ..electrochemistry import HydrogenStack, StackResult
from ..reactions import MolarEnthalpyProvider, StoichiometricReaction
from ..storage.finite_hydride import HydrideGasThermodynamics
from .result_provenance import recorded_content_sha256

STATUS = "implemented_unverified"
_PV_SHA = "ca5be5d34c8afac877fe5755ce57543b360b16da80006998a1614a65704ae5a6"


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")


def _native_hash(module):
    base, digest = Path(module.__file__).parent, hashlib.sha256()
    for path in sorted(base.rglob("*.py")):
        digest.update(path.relative_to(base).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


def _definition(system):
    array = system.arrays[0]
    data = (array.module_parameters, array.modules_per_string, array.strings)
    return hashlib.sha256(json.dumps(_plain(data), sort_keys=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class NativePV:
    package: Any
    pvsystem: Any
    pandas: Any
    source_sha256: str
    call_bindings: tuple

    @staticmethod
    def _calls(module):
        names = ("calcparams_desoto", "singlediode", "i_from_v", "scale_voltage_current_power")
        functions = tuple(getattr(module, n) for n in names)
        functions += tuple(getattr(module.PVSystem, n) for n in names)
        root = Path(module.__file__).parent.resolve()
        result = []
        for function in functions:
            if (not function.__module__.startswith("pvlib.")
                    or not Path(function.__code__.co_filename).resolve().is_relative_to(root)):
                raise ValueError("Native PV call does not originate in the reviewed package")
            wrapped = getattr(function, "__wrapped__", None)
            result.append((function, function.__code__, wrapped,
                           None if wrapped is None else wrapped.__code__))
        return tuple(result)

    @classmethod
    def from_installed(cls):
        """Optional explicit native import. Does not install or modify paths."""
        package = importlib.import_module("pvlib")
        module = importlib.import_module("pvlib.pvsystem")
        if package.__version__ != "0.16.1" or _native_hash(package) != _PV_SHA:
            raise ValueError("Install the reviewed unmodified pvlib0.16.1 artifact")
        return cls(package, module, importlib.import_module("pandas"), _PV_SHA, cls._calls(module))

    def require_current(self):
        if (self.package.__version__ != "0.16.1"
                or _native_hash(self.package) != self.source_sha256 or self.source_sha256 != _PV_SHA
                or self._calls(self.pvsystem) != self.call_bindings):
            raise ValueError("Native PV source or called function/method bindings changed")


@dataclass(frozen=True, slots=True)
class PVBoundaryEvidence:
    source_id: str
    parameter_source_id: str
    irradiance_plane_id: str
    cell_temperature_source_id: str
    clock_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("source_id", "parameter_source_id", "irradiance_plane_id",
                     "cell_temperature_source_id", "clock_id"):
            _text(getattr(self, name), name)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("PV source/temperature/parameter origin is unresolved")


@dataclass(frozen=True, slots=True)
class ProductPressureBoundary:
    source_pressure_pa: float
    evidence_id: str
    included_in_reaction_gibbs: bool

    def __post_init__(self):
        finite(self.source_pressure_pa, "declared pressurized product/source pressure Pa absolute", positive=True)
        _text(self.evidence_id, "electrochemical pressure/activity or external source evidence")
        if not isinstance(self.included_in_reaction_gibbs, bool):
            raise TypeError("Explicitly declare whether product pressure is in reaction Gibbs energy")


@dataclass(frozen=True, slots=True)
class PVStage:
    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    effective_irradiance_w_m2: float
    cell_temperature_k: float
    stack_temperature_k: float
    source_id: str
    origin: Origin
    enabled: bool = True
    source_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("identifier", "clock_id", "source_id"):
            _text(getattr(self, name), name)
        if finite(self.start_s, "source start") >= finite(self.end_s, "source end"):
            raise ValueError("Source stage clock must increase")
        finite(self.end_s-self.start_s, "finite source duration", positive=True)
        if finite(self.effective_irradiance_w_m2, "effective irradiance") < 0:
            raise ValueError("Irradiance cannot be negative")
        finite(self.cell_temperature_k, "prescribed PV cell temperature K", positive=True)
        finite(self.stack_temperature_k, "prescribed stack temperature K", positive=True)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED or not isinstance(self.enabled, bool):
            raise ValueError("Resolve source origin and explicit connected/isolated command")
        if isinstance(self.source_ids, str) or not isinstance(self.source_ids, (tuple, list)):
            raise TypeError("PV source lineage must be an explicit tuple/list of source identities")
        source_ids = tuple(self.source_ids) if self.source_ids else (self.source_id,)
        if not source_ids or any(not isinstance(value, str) or not value.strip() for value in source_ids):
            raise ValueError("Retain one or more explicit source identities for this stage")
        object.__setattr__(self, "source_ids", source_ids)


@dataclass(frozen=True, slots=True)
class PVBoundarySample:
    """One measured or prescribed irradiance/cell-temperature knot (SI units)."""

    time_s: float
    effective_irradiance_w_m2: float
    cell_temperature_k: float
    source_id: str

    def __post_init__(self):
        finite(self.time_s, "PV boundary sample time")
        finite(self.effective_irradiance_w_m2, "effective irradiance")
        if self.effective_irradiance_w_m2 < 0:
            raise ValueError("Effective irradiance cannot be negative")
        finite(self.cell_temperature_k, "PV cell temperature K", positive=True)
        _text(self.source_id, "PV boundary sample source")


@dataclass(frozen=True, slots=True)
class PVBoundaryProfile:
    """Bounded linear interpolation of PV observations into held solver stages.

    Subdivision uses midpoint quadrature: the native load-line model still owns
    each operating point, and no unobserved interval wider than ``maximum_gap_s``
    is silently filled. The stack temperature and on/off command remain explicit
    caller inputs because this profile carries no electrolyzer thermal/control model.
    """

    profile_id: str
    clock_id: str
    origin: Origin
    samples: tuple[PVBoundarySample, ...]

    def __post_init__(self):
        _text(self.profile_id, "PV profile identity")
        _text(self.clock_id, "PV profile clock")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("PV profile origin must be resolved")
        samples = tuple(self.samples)
        if len(samples) < 2 or not all(isinstance(v, PVBoundarySample) for v in samples):
            raise ValueError("At least two typed PV boundary samples are required")
        if any(a.time_s >= b.time_s for a, b in zip(samples[:-1], samples[1:], strict=True)):
            raise ValueError("PV profile times must increase strictly")
        object.__setattr__(self, "samples", samples)

    def stages(self, *, stack_temperature_k: float, maximum_gap_s: float,
               subdivisions_per_gap: int = 1, enabled: bool = True) -> tuple[PVStage, ...]:
        """Create held midpoint stages; caller controls temporal resolution and mode."""
        finite(stack_temperature_k, "prescribed stack temperature K", positive=True)
        finite(maximum_gap_s, "maximum interpolated observation gap", positive=True)
        if isinstance(subdivisions_per_gap, bool) or not isinstance(subdivisions_per_gap, int) or subdivisions_per_gap < 1:
            raise ValueError("Use a positive integer number of subdivisions per observation gap")
        if not isinstance(enabled, bool):
            raise TypeError("Declare the plant connection command as a boolean")
        result = []
        for left, right in zip(self.samples[:-1], self.samples[1:], strict=True):
            gap = right.time_s - left.time_s
            if gap > maximum_gap_s:
                raise ValueError("PV sample gap exceeds the caller's interpolation limit")
            for index in range(subdivisions_per_gap):
                start = left.time_s + gap * index / subdivisions_per_gap
                end = left.time_s + gap * (index + 1) / subdivisions_per_gap
                fraction = (index + 0.5) / subdivisions_per_gap
                irradiance = left.effective_irradiance_w_m2 + fraction * (
                    right.effective_irradiance_w_m2 - left.effective_irradiance_w_m2
                )
                cell_temperature = left.cell_temperature_k + fraction * (
                    right.cell_temperature_k - left.cell_temperature_k
                )
                result.append(PVStage(
                    identifier=f"{self.profile_id}:{left.source_id}->{right.source_id}:{index}",
                    start_s=start,
                    end_s=end,
                    clock_id=self.clock_id,
                    effective_irradiance_w_m2=irradiance,
                    cell_temperature_k=cell_temperature,
                    stack_temperature_k=stack_temperature_k,
                    source_id=f"{left.source_id}|{right.source_id}",
                    origin=self.origin,
                    enabled=enabled,
                    source_ids=(left.source_id, right.source_id),
                ))
        return tuple(result)


@dataclass(frozen=True, slots=True)
class DirectDCDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    maximum_irradiance_w_m2: float
    maximum_array_voltage_v: float
    maximum_array_current_a: float
    maximum_current_density_a_m2: float
    minimum_receiver_pressure_pa: float
    maximum_receiver_pressure_pa: float
    minimum_receiver_mass_kg: float = 1e-12
    current_residual_a: float = 1e-7
    energy_residual_j: float = 1e-5
    enthalpy_match_j_mol: float = 1e-6
    mass_residual_kg: float = 1e-10
    root_current_density_atol: float = 1e-9

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if (self.minimum_temperature_k >= self.maximum_temperature_k
                or self.minimum_receiver_pressure_pa >= self.maximum_receiver_pressure_pa):
            raise ValueError("Temperature/receiver pressure bounds must increase")


@dataclass(frozen=True, slots=True)
class NativePVState:
    native_system: Any
    native_parameters: Any
    native_iv_result: Any
    native_scaled_iv: Any
    available_mpp_w: float
    open_circuit_voltage_v: float
    short_circuit_current_a: float


@dataclass(frozen=True, slots=True)
class LoadLineProbe:
    current_density_a_m2: float
    stack: StackResult
    native_pv_current_a: float
    mismatch_a: float
    inside_generation_branch: bool


@dataclass(frozen=True, slots=True)
class DirectDCPoint:
    stage: PVStage
    pv: NativePVState
    stack: StackResult
    mode: str
    pv_voltage_v: float
    pv_current_a: float
    pv_power_w: float
    load_line_residual_a: float | None
    undrawn_mpp_headroom_w: float
    native_root_result: Any
    probes: tuple[LoadLineProbe, ...]
    topology: str = "direct-DC; ideal wiring and explicit one-way blocking; no MPPT/inverter/rectifier"
    status: str = STATUS


@dataclass(frozen=True, slots=True)
class PVInventoryState:
    time_s: float
    amounts_mol: Mapping[str, float]
    receiver: ThermoState
    receiver_internal_energy_j: float

    def __post_init__(self):
        finite(self.time_s, "inventory clock")
        finite(self.receiver_internal_energy_j, "finite receiver internal energy")
        if not isinstance(self.receiver, ThermoState):
            raise TypeError("Retain the actual native gas ThermoState")
        values = dict(self.amounts_mol)
        if any(finite(v, "finite species mol") < 0 for v in values.values()):
            raise ValueError("Finite inventories cannot be negative")
        object.__setattr__(self, "amounts_mol", MappingProxyType(values))


@dataclass(frozen=True, slots=True)
class PVProductionStep:
    point: DirectDCPoint
    before: PVInventoryState
    after: PVInventoryState
    native_conversion: Any
    extent_mol_h2: float
    electricity_j: float
    pv_electricity_j: float
    direct_dc_energy_residual_j: float
    reaction_enthalpy_j: float
    stack_heat_rejected_j: float
    hydrogen_inlet_enthalpy_j: float
    receiver_heat_into_j: float
    nonreceiver_enthalpy_change_j: float
    reference_energy_change_j: float
    caloric_residual_j: float
    mass_residual_kg: float
    native_inlet_state: ThermoState
    molar_enthalpies_j_mol: tuple[float, ...]

    def __post_init__(self):
        for name in ("extent_mol_h2", "electricity_j", "pv_electricity_j",
                     "direct_dc_energy_residual_j", "reaction_enthalpy_j",
                     "stack_heat_rejected_j", "hydrogen_inlet_enthalpy_j",
                     "receiver_heat_into_j", "nonreceiver_enthalpy_change_j",
                     "reference_energy_change_j", "caloric_residual_j", "mass_residual_kg"):
            finite(getattr(self, name), name)
        if self.extent_mol_h2 < 0:
            raise ValueError("The production reference does not reverse electrolysis")


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PVElectrolysisTrace:
    initial: PVInventoryState
    final: PVInventoryState
    steps: tuple[PVProductionStep, ...]
    native_pv: NativePV
    native_system: Any
    stack: HydrogenStack
    gas: HydrideGasThermodynamics
    caloric_provider: Any
    pressure_boundary: ProductPressureBoundary
    evidence: PVBoundaryEvidence
    pressure_work_resolved: bool
    owner: "PVElectrolysis"
    required_external_pressure_work_j: None = None
    continuous_pressure_feedback: bool = False
    thermal_utility_availability_solved: bool = False
    full_plant_energy_closed: bool = False
    water_oxygen_vessel_dynamics_solved: bool = False
    energy_coordinate: str = "finite H-water/O2 at fixed source P + finite H2 receiver U at fixed V"
    status: str = STATUS
    _admission: "PVResultAdmission | None" = field(default=None, repr=False, compare=False)

    @property
    def admission(self):
        if self._admission is None:
            raise PVResultVerificationError("No producer-issued original-result admission", self, self.owner)
        return self._admission

    def require_current(self):
        if type(self.owner) is not PVElectrolysis:
            raise PVResultVerificationError("No actual PV producer binding", self, self.owner)
        return PVElectrolysis.verify_result(self.owner, self)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PVResultAdmission:
    owner: "PVElectrolysis"
    source_sha256: str
    pv_definition_sha256: str
    owner_configuration_sha256: str
    content_sha256: str
    _original_trace_ref: object = field(repr=False, compare=False)
    verification_scope: str = "producer identity and retained result content; no physical replay"

    @property
    def original_trace(self):
        return self._original_trace_ref()


class PVResultVerificationError(ValueError):
    def __init__(self, message, result, owner):
        super().__init__(message)
        self.result, self.owner = result, owner
        self.admission = getattr(result, "_admission", None)


class PVElectrolysisError(RuntimeError):
    """Actual native results/failed attempt and completed finite campaign retained."""

    def __init__(self, message, *, model, stage=None, pv=None, point=None,
                 probes=(), completed_steps=(), attempted_receiver=None, conversion=None,
                 native_attempt=None, failed_step=None, failure_code=None):
        super().__init__(message)
        self.model, self.stage, self.native_pv_state, self.point = model, stage, pv, point
        self.probes, self.completed_steps = tuple(probes), tuple(completed_steps)
        self.attempted_receiver, self.native_conversion = attempted_receiver, conversion
        self.native_attempt = MappingProxyType(dict(native_attempt or {}))
        self.failed_step = failed_step
        if failure_code not in {None, "unresolved_faradaic_loss_path"}:
            raise ValueError("Unknown PV electrolysis failure code")
        requested_efficiency = getattr(model, "faradaic_efficiency", None)
        self.requested_faradaic_efficiency = requested_efficiency
        self.failure_code = failure_code
        faradaic_path_unresolved = failure_code == "unresolved_faradaic_loss_path"
        self.unresolved_faradaic_loss_fraction = (
            1.0 - self.requested_faradaic_efficiency
            if faradaic_path_unresolved and self.requested_faradaic_efficiency is not None
            and self.requested_faradaic_efficiency < 1.0 else 0.0
        )
        self.unresolved_energy_path = (
            "unallocated Faradaic-loss fate; no heat or side reaction inferred"
            if faradaic_path_unresolved and self.unresolved_faradaic_loss_fraction else None
        )


class PVElectrolysis:
    """Quasi-steady held source stages; finite chemistry and native EOS endpoints.

    Water and oxygen use an explicit isothermal/isobaric additive-enthalpy
    reference. Only the H2 receiver is a fixed-volume native fluid inventory.
    Source pressure support is declared separately; free pressurization is not
    inferred from a mass source. No time integrator is introduced.
    """

    def __init__(self, native: NativePV, system, stack: HydrogenStack,
                 reaction: StoichiometricReaction, caloric: MolarEnthalpyProvider,
                 gas: HydrideGasThermodynamics, *, water_id: str, hydrogen_id: str,
                 oxygen_id: str, pressure: ProductPressureBoundary,
                 evidence: PVBoundaryEvidence, domain: DirectDCDomain,
                 faradaic_efficiency: float = 1.):
        native.require_current()
        if type(system) is not native.pvsystem.PVSystem or len(system.arrays) != 1:
            raise TypeError("Supply one actual native PVSystem with exactly one Array")
        if type(stack) is not HydrogenStack or not isinstance(gas, HydrideGasThermodynamics):
            raise TypeError("Reuse the shared HydrogenStack and native gas thermodynamics")
        if not isinstance(reaction, StoichiometricReaction):
            raise TypeError("Reuse the shared finite stoichiometric reaction")
        for obj, cls in ((pressure, ProductPressureBoundary), (evidence, PVBoundaryEvidence),
                         (domain, DirectDCDomain)):
            if not isinstance(obj, cls):
                raise TypeError(f"Actual {cls.__name__} required")
            cls(**{f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)})
        if not callable(gas.state_rho_t):
            raise ValueError("Receiver requires an actual native density/temperature flash")
        faradaic_efficiency = finite(faradaic_efficiency, "Faradaic efficiency", positive=True)
        if faradaic_efficiency > 1:
            raise ValueError("Faradaic efficiency must lie in (0,1]")
        self.native, self.system, self.stack = native, system, stack
        self.reaction, self.caloric, self.gas = reaction, caloric, gas
        self.water_id, self.hydrogen_id, self.oxygen_id = water_id, hydrogen_id, oxygen_id
        self.pressure, self.evidence, self.domain = pressure, evidence, domain
        self.faradaic_efficiency = faradaic_efficiency
        ids = tuple(s.identifier for s in reaction.species)
        if (set(ids) != {water_id, hydrogen_id, oxygen_id} or len(ids) != 3
                or tuple(caloric.species) != reaction.species):
            raise ValueError("Declare the same ordered water/H2/O2 species in reaction and caloric provider")
        expected = {water_id: -1., hydrogen_id: 1., oxygen_id: .5}
        if any(c != expected[s.identifier] for s, c in zip(reaction.species, reaction.coefficients, strict=True)):
            raise ValueError("The reaction must be H2O -> H2 + 0.5 O2 per mol H2")
        self._indices = {n: ids.index(n) for n in ids}
        species = {s.identifier: s for s in reaction.species}
        if (dict(species[water_id].elements) != {"H": 2, "O": 1}
                or dict(species[hydrogen_id].elements) != {"H": 2}
                or dict(species[oxygen_id].elements) != {"O": 2}):
            raise ValueError("The declared species do not represent neutral water/H2/O2")
        if any(s.charge != 0 for s in reaction.species):
            raise ValueError("Only neutral material inventories are supported")
        if any(species[n].phase not in {"gas", "vapor"} for n in (hydrogen_id, oxygen_id)):
            raise ValueError("Declare H2 and O2 as gas/vapor species")
        self.water_phase = species[water_id].phase
        if self.water_phase not in {"liquid", "vapor"}:
            raise ValueError("Declare water phase as liquid/vapor on the shared ReactionEnergy convention")
        for molar_mass in (species[hydrogen_id].molar_mass_kg_mol, stack.geometry.hydrogen_molar_mass_kg_mol):
            if not math.isclose(molar_mass, gas.molar_mass_kg_mol, rel_tol=1e-10, abs_tol=0.):
                raise ValueError("Hydrogen material/Faraday/native EOS molar-mass bases differ")
        array = system.arrays[0]
        for count in (array.modules_per_string, array.strings):
            if isinstance(count, bool) or not float(count).is_integer() or count <= 0:
                raise ValueError("PV topology requires explicit positive integer module/string counts")
        self._pv_sha = _definition(system)
        self._stack_definition = self._stack_identity()
        self._shared_calls = (HydrogenStack.evaluate, StoichiometricReaction.convert)
        self._configuration = self._configuration_identity()
        self._issued_results = weakref.WeakValueDictionary()

    def _configuration_identity(self):
        return (repr(self.pressure), repr(self.evidence), repr(self.domain),
                repr(self.reaction), self._caloric_identity(),
                self.gas.basis, self.gas.state_pt, self.gas.state_rho_t,
                self.gas.molar_mass_kg_mol, self.faradaic_efficiency)

    def _caloric_identity(self):
        provider = self.caloric
        method = provider.enthalpies_j_mol
        # Record definitions, never mutable native P/T caches. Functional and
        # CoolProp providers expose different configuration fields through the
        # same molar-enthalpy protocol; neither may change under an issued owner.
        fields = ("species", "fluids", "reference_offsets_j_mol", "functions",
                  "temperature_bounds_k", "pressure_bounds_pa", "backend", "version")
        return (id(provider), provider.basis_id, method,
                getattr(method, "__self__", None),
                tuple((name, repr(getattr(provider, name)))
                      for name in fields if hasattr(provider, name)),
                tuple(id(state) for state in getattr(provider, "_states", ())),
                id(getattr(provider, "_cp", None)))

    def _stack_identity(self):
        return (repr(self.stack.geometry), self.stack.thermochemistry,
                repr(tuple(self.stack.losses.items())))

    def _guard(self):
        self.native.require_current()
        for name in ("calcparams_desoto", "singlediode", "i_from_v", "scale_voltage_current_power"):
            bound = getattr(self.system, name)
            if (getattr(bound, "__self__", None) is not self.system
                    or getattr(bound, "__func__", None) is not getattr(self.native.pvsystem.PVSystem, name)):
                raise ValueError("Actual PVSystem instance method ownership changed")
        if (getattr(self.stack.evaluate, "__self__", None) is not self.stack
                or getattr(self.stack.evaluate, "__func__", None) is not HydrogenStack.evaluate):
            raise ValueError("Actual shared stack evaluation method ownership changed")
        if (_definition(self.system) != self._pv_sha or self._stack_identity() != self._stack_definition
                or self._configuration_identity() != self._configuration
                or (HydrogenStack.evaluate, StoichiometricReaction.convert) != self._shared_calls):
            raise ValueError("Admitted PV/stack definitions or shared method bindings changed")

    def _result_configuration(self):
        return (
            self.native,
            self.system,
            self.stack,
            self.reaction,
            self.caloric,
            self.gas,
            self.pressure,
            self.evidence,
            self.domain,
            self._pv_sha,
            self._stack_definition,
            self._configuration,
            self._shared_calls,
        )

    def verify_result(self, result):
        """Admit only this producer's unchanged original trace, without replay."""
        try:
            if type(result) is not PVElectrolysisTrace or result.owner is not self:
                raise ValueError("Only this actual producer's original trace is admissible")
            admission = result._admission
            if (
                admission is None
                or self._issued_results.get(id(result)) is not admission
                or admission.original_trace is not result
                or admission.owner is not self
            ):
                raise ValueError("Result is replaced, unissued or no longer registered")
            self._guard()
            if (
                result.native_pv is not self.native
                or result.native_system is not self.system
                or result.stack is not self.stack
                or result.gas is not self.gas
                or result.caloric_provider is not self.caloric
                or result.pressure_boundary is not self.pressure
                or result.evidence is not self.evidence
                or admission.source_sha256 != self.native.source_sha256
                or admission.pv_definition_sha256 != self._pv_sha
            ):
                raise ValueError("Original native/source/caloric/evidence bindings changed")
            if recorded_content_sha256(self._result_configuration()) != admission.owner_configuration_sha256:
                raise ValueError("Original producer definitions or callable bindings changed")
            if recorded_content_sha256(result) != admission.content_sha256:
                raise ValueError("Retained trace/native cache/material/energy evidence changed")
            return result
        except Exception as cause:
            raise PVResultVerificationError(str(cause), result, self) from cause

    def _issue_result(self, result):
        self._guard()
        admission = PVResultAdmission(
            self,
            self.native.source_sha256,
            self._pv_sha,
            recorded_content_sha256(self._result_configuration()),
            recorded_content_sha256(result),
            weakref.ref(result),
        )
        object.__setattr__(result, "_admission", admission)
        self._issued_results[id(result)] = admission
        return result

    def _temperature(self, temperature):
        if not self.domain.minimum_temperature_k <= temperature <= self.domain.maximum_temperature_k:
            raise ValueError("Temperature is outside the declared native PV/stack/receiver envelope")

    def _pv(self, stage, attempt):
        self._temperature(stage.cell_temperature_k)
        self._temperature(stage.stack_temperature_k)
        if stage.effective_irradiance_w_m2 > self.domain.maximum_irradiance_w_m2:
            raise ValueError("Irradiance exceeds the declared native parameter scope")
        # pvlib implements the zero-irradiance infinite-shunt limit with NumPy
        # arithmetic. A Python float zero would raise before that native limit.
        with np.errstate(divide="ignore"):
            parameters = self.system.calcparams_desoto(np.float64(stage.effective_irradiance_w_m2),
                                                       stage.cell_temperature_k-273.15)
        attempt["native_parameters_result"] = parameters
        parameters = tuple(parameters)
        attempt["native_parameters"] = parameters
        if len(parameters) != 5:
            raise ValueError("Native single-array DeSoto did not return five parameters")
        il, i0, rs, rsh, nvt = (float(v) for v in parameters)
        if (not all(math.isfinite(v) for v in (il, i0, rs, nvt))
                or il < 0 or i0 <= 0 or rs < 0 or rsh <= 0 or math.isnan(rsh) or nvt <= 0):
            raise ValueError("Native DeSoto parameters are inadmissible; positive infinite shunt is permitted")
        raw = self.system.singlediode(*parameters)
        attempt["native_iv_result"] = raw
        frame = raw if isinstance(raw, self.native.pandas.DataFrame) else self.native.pandas.DataFrame([raw])
        scaled = self.system.scale_voltage_current_power(frame)
        attempt["native_scaled_iv"] = scaled
        if len(scaled) != 1:
            raise ValueError("One source stage requires exactly one native I–V result")
        row = scaled.iloc[0]
        pmp, voc, isc = (finite(float(row[n]), n) for n in ("p_mp", "v_oc", "i_sc"))
        if min(pmp, voc, isc) < 0:
            raise ValueError("Native PV MPP/open/short values cannot be negative")
        state = NativePVState(self.system, parameters, raw, scaled, pmp, voc, isc)
        if voc > self.domain.maximum_array_voltage_v or isc > self.domain.maximum_array_current_a:
            raise PVElectrolysisError("Native array exceeds declared hardware voltage/current", model=self, pv=state)
        return state

    def operating_point(self, stage: PVStage) -> DirectDCPoint:
        pv, probes, root_result, attempt = None, [], None, {}
        try:
            self._guard()
            if not isinstance(stage, PVStage):
                raise TypeError("An actual finite PVStage is required")
            stage = PVStage(**{f.name: getattr(stage, f.name) for f in dataclasses.fields(stage)})
            if stage.clock_id != self.evidence.clock_id:
                raise ValueError("PV source and process clocks differ")
            pv = self._pv(stage, attempt)
            area = self.stack.geometry.active_area_m2
            series, parallel = self.system.arrays[0].modules_per_string, self.system.arrays[0].strings

            def probe(j):
                result = self.stack.evaluate(float(j), stage.stack_temperature_k,
                    mode="electrolysis", faradaic_efficiency=self.faradaic_efficiency)
                attempt["last_stack_result"] = result
                attempt["last_current_density_a_m2"] = float(j)
                native_current = self.system.i_from_v(result.stack_voltage_v/series, *pv.native_parameters)
                attempt["last_native_current_result"] = native_current
                current = float(native_current)*parallel
                finite(current, "native PV current")
                value = current-result.current_a
                probes.append(LoadLineProbe(float(j), result, current, value,
                    0 <= result.stack_voltage_v <= pv.open_circuit_voltage_v and current >= 0))
                return value

            zero = self.stack.evaluate(0., stage.stack_temperature_k,
                mode="electrolysis", faradaic_efficiency=self.faradaic_efficiency)
            if not stage.enabled or pv.short_circuit_current_a == 0 or pv.open_circuit_voltage_v <= zero.stack_voltage_v:
                mode = ("isolated" if not stage.enabled else
                        "dark" if pv.short_circuit_current_a == 0 else "blocked-insufficient-voltage")
                self._guard()
                return DirectDCPoint(stage, pv, zero, mode, pv.open_circuit_voltage_v, 0., 0.,
                    None, pv.available_mpp_w, None, tuple(probes))
            upper = min(self.domain.maximum_current_density_a_m2, pv.short_circuit_current_a/area)
            grid = np.linspace(0., upper, 17)
            values = [probe(float(j)) for j in grid]
            voltages = np.array([p.stack.stack_voltage_v for p in probes])
            if np.any(np.diff(voltages) < -1e-10) or np.any(np.diff(values) > self.domain.current_residual_a):
                raise ValueError("The declared direct-DC branch is not monotone on the admission grid")
            if values[0] <= 0 or values[-1] > 0:
                raise ValueError("No direct-DC load-line root inside the supplied current-density envelope")
            from scipy.optimize import brentq

            root, root_result = brentq(probe, 0., upper, xtol=self.domain.root_current_density_atol,
                                      rtol=1e-12, full_output=True, disp=True)
            residual = probe(root)
            last = probes[-1]
            if (not root_result.converged or not last.inside_generation_branch
                    or abs(residual) > self.domain.current_residual_a):
                raise ValueError("Native PV/shared-stack load-line residual or generation branch failed")
            power = last.native_pv_current_a*last.stack.stack_voltage_v
            headroom = pv.available_mpp_w-power
            if headroom < -self.domain.energy_residual_j/(stage.end_s-stage.start_s):
                raise ValueError("Actual direct-load power exceeds native available MPP")
            self._guard()
            return DirectDCPoint(stage, pv, last.stack, "direct-DC", last.stack.stack_voltage_v,
                last.native_pv_current_a, power, residual, headroom, root_result, tuple(probes))
        except Exception as error:
            raise PVElectrolysisError(str(error), model=self, stage=stage,
                pv=pv or getattr(error, "native_pv_state", None), probes=probes,
                native_attempt=attempt) from error

    def _receiver(self, amount, temperature, volume):
        self._temperature(temperature)
        mass = amount*self.gas.molar_mass_kg_mol
        if mass < self.domain.minimum_receiver_mass_kg:
            raise ValueError("An explicit positive seeded receiver inventory is required; no vacuum EOS substitution")
        state = self.gas.state_rho_t(mass/volume, temperature)
        try:
            self.gas.basis.require_compatible(state.basis)
            if (abs(state.density_kg_m3*volume-mass) > self.domain.mass_residual_kg
                    or abs(state.temperature_k-temperature) > 1e-8):
                raise ValueError("Native receiver flash does not preserve its requested finite mass/T")
            if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
                raise ValueError("Receiver native phase is outside the admitted gas scope")
            if not self.domain.minimum_receiver_pressure_pa <= state.pressure_pa <= self.domain.maximum_receiver_pressure_pa:
                raise ValueError("Receiver pressure lies outside its declared native EOS envelope")
        except Exception as error:
            raise PVElectrolysisError(str(error), model=self, attempted_receiver=state) from error
        try:
            energy = finite(mass*state.internal_energy_j_kg, "finite native receiver energy")
        except Exception as error:
            raise PVElectrolysisError(str(error), model=self, attempted_receiver=state) from error
        return state, energy

    def run(self, stages, *, initial_amounts_mol: Mapping[str, float],
            receiver_volume_m3: float, receiver_temperature_k: float) -> PVElectrolysisTrace:
        steps, state, point, conversion, attempted, candidate = [], None, None, None, None, None
        attempt = {}
        stage = None
        try:
            self._guard()
            finite(receiver_volume_m3, "fixed receiver volume", positive=True)
            stages = tuple(stages)
            if not stages or not all(isinstance(s, PVStage) for s in stages):
                raise ValueError("Supply a nonempty explicit finite source schedule")
            stages = tuple(PVStage(**{f.name: getattr(s, f.name) for f in dataclasses.fields(s)})
                           for s in stages)
            identifiers = tuple(stage.identifier for stage in stages)
            if len(set(identifiers)) != len(identifiers):
                raise ValueError("Every source stage needs a unique identifier for trace and ledger lineage")
            if self.faradaic_efficiency != 1.:
                raise PVElectrolysisError(
                    "Finite heat closure requires eta_F=1; missing Faradaic-loss fate is not assigned to heat",
                    model=self, stage=stages[0], failure_code="unresolved_faradaic_loss_path",
                )
            stack_temperature = stages[0].stack_temperature_k
            if any(s.stack_temperature_k != stack_temperature for s in stages):
                raise ValueError("Finite water/O2 reference is isothermal; supplied stack T changes need conditioning physics")
            if any(a.end_s != b.start_s for a, b in zip(stages[:-1], stages[1:], strict=True)):
                raise ValueError("Source intervals must be contiguous on the explicit process clock")
            amounts = self.reaction.amounts(initial_amounts_mol)
            ids = tuple(s.identifier for s in self.reaction.species)
            amounts_map = dict(zip(ids, amounts, strict=True))
            receiver, u = self._receiver(amounts_map[self.hydrogen_id], receiver_temperature_k, receiver_volume_m3)
            state = PVInventoryState(stages[0].start_s, amounts_map, receiver, u)
            initial = state
            for stage in stages:
                point, conversion, attempted, candidate, attempt = None, None, None, None, {}
                point = self.operating_point(stage)
                energy = point.stack.reaction_energy
                if energy.reference_id != self.caloric.basis_id or energy.water_phase != self.water_phase:
                    raise ValueError("Shared stack reaction-energy reference/water phase differs from caloric inventory")
                h = np.array(self.caloric.enthalpies_j_mol(stack_temperature,
                    self.pressure.source_pressure_pa), dtype=float, copy=True)
                attempt["molar_enthalpies_j_mol"] = h
                if h.shape != (3,) or not np.all(np.isfinite(h)):
                    raise ValueError("Caloric provider returned an invalid ordered molar-enthalpy vector")
                native_inlet = self.gas.state_pt(self.pressure.source_pressure_pa, stack_temperature)
                attempt["native_inlet_state"] = native_inlet
                self.gas.basis.require_compatible(native_inlet.basis)
                if (abs(native_inlet.pressure_pa-self.pressure.source_pressure_pa) > 1e-6
                        or abs(native_inlet.temperature_k-stack_temperature) > 1e-8):
                    raise ValueError("Native product state does not match its declared source P/T")
                if native_inlet.phase not in {"gas", "supercritical_gas", "supercritical"}:
                    raise ValueError("Declared product inlet is outside the admitted native gas phase")
                hi = native_inlet.enthalpy_j_kg*self.gas.molar_mass_kg_mol
                delta_h = float(np.dot(np.asarray(self.reaction.coefficients), h))
                if (abs(h[self._indices[self.hydrogen_id]]-hi) > self.domain.enthalpy_match_j_mol
                        or abs(delta_h-energy.enthalpy_j_mol_h2) > self.domain.enthalpy_match_j_mol):
                    raise ValueError("Native H2 material h and reaction deltaH are not on the same declared caloric basis")
                duration = stage.end_s-stage.start_s
                extent = point.stack.hydrogen_production_mol_s*duration
                conversion = self.reaction.convert(state.amounts_mol, extent)
                receiver, receiver_u = self._receiver(
                    conversion.final_amounts[self.hydrogen_id], receiver_temperature_k, receiver_volume_m3)
                attempted = receiver
                if extent > 0 and max(state.receiver.pressure_pa, receiver.pressure_pa) > self.pressure.source_pressure_pa:
                    raise ValueError("Declared source cannot deliver H2 above its product pressure; no free pressurization")
                after = PVInventoryState(stage.end_s, conversion.final_amounts, receiver, receiver_u)
                electrical = point.stack.electric_input_w*duration
                pv_electrical = point.pv_power_w*duration
                dc_residual = pv_electrical-electrical
                reaction_h = extent*delta_h
                heat_rejected = point.stack.isothermal_heat_rejection_w*duration
                inlet_h = extent*hi
                receiver_heat = receiver_u-state.receiver_internal_energy_j-inlet_h
                nonreceiver_h = extent*(.5*h[self._indices[self.oxygen_id]]-h[self._indices[self.water_id]])
                energy_change = nonreceiver_h+receiver_u-state.receiver_internal_energy_j
                residual = electrical-heat_rejected+receiver_heat-energy_change
                candidate = PVProductionStep(point=point, before=state, after=after,
                    native_conversion=conversion, extent_mol_h2=extent, electricity_j=electrical,
                    pv_electricity_j=pv_electrical, direct_dc_energy_residual_j=dc_residual,
                    reaction_enthalpy_j=reaction_h, stack_heat_rejected_j=heat_rejected,
                    hydrogen_inlet_enthalpy_j=inlet_h, receiver_heat_into_j=receiver_heat,
                    nonreceiver_enthalpy_change_j=nonreceiver_h, reference_energy_change_j=energy_change,
                    caloric_residual_j=residual, mass_residual_kg=conversion.mass_residual_kg,
                    native_inlet_state=native_inlet, molar_enthalpies_j_mol=tuple(h))
                if (abs(residual) > self.domain.energy_residual_j
                        or abs(dc_residual) > self.domain.energy_residual_j
                        or abs(conversion.mass_residual_kg) > self.domain.mass_residual_kg):
                    raise ValueError("Finite shared stoichiometry/caloric ledger residual exceeds the declared gate")
                steps.append(candidate)
                state = after
            self._guard()
            result = PVElectrolysisTrace(initial, state, tuple(steps), self.native, self.system,
                self.stack, self.gas, self.caloric, self.pressure, self.evidence,
                self.pressure.included_in_reaction_gibbs, self)
            return self._issue_result(result)
        except Exception as error:
            raise PVElectrolysisError(str(error), model=self, stage=stage,
                pv=point.pv if point else getattr(error, "native_pv_state", None), point=point,
                probes=getattr(error, "probes", ()), completed_steps=steps,
                attempted_receiver=attempted or getattr(error, "attempted_receiver", None),
                conversion=conversion,
                native_attempt={**getattr(error, "native_attempt", {}), **attempt},
                failed_step=candidate,
                failure_code=getattr(error, "failure_code", None)) from error
