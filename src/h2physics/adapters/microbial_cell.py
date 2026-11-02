"""Finite microbial/electrode composition using native Cantera surface kinetics.

Implemented_unverified. No empirical MEC rate, yield or aqueous property is
provided. The water-splitting HydrogenStack thermochemistry is not used for
substrate oxidation. Native cathode kinetics and shared finite conversion own
their respective equations; this module assembles their charge/material ledger.
"""

import hashlib
import math
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from types import MappingProxyType, ModuleType

import numpy as np

from scipy.optimize import brentq

from ..constants import FARADAY_C_MOL
from ..core import immutable_array, Origin, finite
from ..electrochemistry import StackGeometry
from ..reactions import StoichiometricReaction
from ..thermochemical import (
    FiniteThermochemicalCycle,
    PrescribedConversion,
    ThermochemicalEvidence,
    ThermochemicalInventory,
    ThermochemicalStage,
    ThermochemicalTolerances,
)
from .cantera import MechanismBasis
from .cantera_volume import _phase_fingerprint
from .result_provenance import recorded_content_sha256 as _recorded_sha
from .result_provenance import recorded_content_token as _recorded_token

STATUS = "implemented_unverified"


def _ids(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare reaction, kinetic, electrode/reference and clock evidence")


def _array(value):
    a = np.array(value, dtype=float, copy=True)
    if not np.all(np.isfinite(a)):
        raise ValueError("Native and finite-cell arrays must be finite")
    a = immutable_array(a, name="a")
    return a


def _sum(values, label):
    try:
        return finite(math.fsum(float(v) for v in values), label)
    except OverflowError as error:
        raise ValueError(f"{label} exceeds finite arithmetic") from error


def _stored_native_state(cathode):
    """Read native stored state/definitions, not currents or production rates."""
    result = []
    for phase in cathode._graph:
        result.append(
            (
                id(phase),
                _phase_fingerprint(phase, include_reactions=True),
                tuple(float(v).hex() for v in phase.state),
                float(phase.electric_potential).hex(),
                (float(phase.site_density).hex(), tuple(float(v).hex() for v in phase.coverages))
                if isinstance(phase, cathode.native_module.Interface)
                else None,
            )
        )
    return tuple(result)


def _caloric_binding(caloric, native_module, seen=None):
    """Declared/public caloric bindings and exposed native states, without h calls.

    This does not infer hidden state in arbitrary opaque providers or callbacks.
    """
    seen = set() if seen is None else seen
    if id(caloric) in seen:
        return ("reference", id(caloric))
    seen.add(id(caloric))
    if isinstance(caloric, (native_module.Solution, native_module.Interface)):
        return (
            "native-phase",
            id(caloric),
            _phase_fingerprint(caloric, include_reactions=True),
            tuple(float(v).hex() for v in caloric.state),
            float(caloric.electric_potential).hex(),
            (float(caloric.site_density).hex(), tuple(float(v).hex() for v in caloric.coverages))
            if isinstance(caloric, native_module.Interface)
            else None,
        )
    if isinstance(caloric, Mapping):
        return (
            "mapping",
            id(caloric),
            tuple((str(k), _caloric_binding(v, native_module, seen)) for k, v in caloric.items()),
        )
    if isinstance(caloric, (tuple, list)):
        return (
            type(caloric).__name__,
            tuple(_caloric_binding(v, native_module, seen) for v in caloric),
        )
    if is_dataclass(caloric):
        return (
            type(caloric).__qualname__,
            id(caloric),
            tuple(
                (f.name, _caloric_binding(getattr(caloric, f.name), native_module, seen))
                for f in fields(caloric)
            ),
        )
    if (
        hasattr(caloric, "__dict__")
        and not callable(caloric)
        and not isinstance(caloric, ModuleType)
    ):
        return (
            type(caloric).__module__,
            type(caloric).__qualname__,
            id(caloric),
            tuple(
                (k, _caloric_binding(v, native_module, seen))
                for k, v in vars(caloric).items()
                if not k.startswith("_")
            ),
        )
    return _recorded_token(caloric)


@dataclass(frozen=True, slots=True)
class CathodeEvidence:
    mechanism_basis: MechanismBasis
    electrode_reference_id: str
    phase_activity_source_id: str
    cathode_rate_source_id: str
    caloric_reference_id: str
    origin: Origin

    def __post_init__(self):
        if not isinstance(self.mechanism_basis, MechanismBasis):
            raise TypeError("Supply an actual native mechanism/domain/rights basis")
        _ids(
            self.electrode_reference_id,
            self.phase_activity_source_id,
            self.cathode_rate_source_id,
            self.caloric_reference_id,
        )
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Native cathode parameters need source or explicit synthetic identity")


@dataclass(frozen=True, slots=True)
class MicrobialRateState:
    time_s: float
    clock_id: str
    inventory: ThermochemicalInventory
    liquid_volume_m3: float
    substrate_id: str
    biomass_id: str


@dataclass(frozen=True, slots=True)
class MicrobialRates:
    catabolic_extent_mol_s: float
    growth_extent_mol_s: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            if finite(getattr(self, name), name) < 0:
                raise ValueError("Forward microbial extents cannot be negative")


@dataclass(frozen=True, slots=True)
class MicrobialKinetics:
    callback: Callable
    source_id: str
    parameter_source_id: str
    origin: Origin
    parameters: Mapping[str, float]
    temperature_bounds_k: tuple[float, float]
    substrate_concentration_bounds_mol_m3: tuple[float, float]
    biomass_concentration_bounds_mol_m3: tuple[float, float]
    native_model: object | None = None

    def __post_init__(self):
        if not callable(self.callback):
            raise TypeError("Supply an explicit microbial catabolism/growth callable")
        _ids(self.source_id, self.parameter_source_id)
        values = {}
        for key, value in self.parameters.items():
            _ids(key)
            values[key] = finite(value, "explicit microbial parameter")
        object.__setattr__(self, "parameters", MappingProxyType(values))
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError(
                "Qualified kinetic source or an explicit synthetic fixture is required"
            )
        for name in (
            "temperature_bounds_k",
            "substrate_concentration_bounds_mol_m3",
            "biomass_concentration_bounds_mol_m3",
        ):
            bounds = tuple(getattr(self, name))
            if (
                len(bounds) != 2
                or finite(bounds[0], name) < 0
                or bounds[0] >= finite(bounds[1], name)
            ):
                raise ValueError("Declare finite increasing kinetic-state bounds")
            if name == "temperature_bounds_k" and bounds[0] <= 0:
                raise ValueError("Kinetic temperature bounds must be positive")
            object.__setattr__(self, name, bounds)

    def require_state(self, state):
        values = (
            state.inventory.temperature_k,
            state.inventory.amounts_mol.get(state.substrate_id, 0.0) / state.liquid_volume_m3,
            state.inventory.amounts_mol.get(state.biomass_id, 0.0) / state.liquid_volume_m3,
        )
        bounds = (
            self.temperature_bounds_k,
            self.substrate_concentration_bounds_mol_m3,
            self.biomass_concentration_bounds_mol_m3,
        )
        if any(
            not lo <= finite(value, "kinetic state") <= hi
            for value, (lo, hi) in zip(values, bounds, strict=True)
        ):
            raise ValueError(
                "Finite microbial state lies outside the explicitly supplied kinetic domain"
            )


@dataclass(frozen=True, slots=True)
class MicrobialCellEvidence:
    process_id: str
    stoichiometry_source_id: str
    electron_equivalent_source_id: str
    caloric_basis_id: str
    electrode_reference_id: str
    anode_potential_source_id: str
    fixed_activity_boundary_id: str
    isothermal_fixed_pressure_boundary_id: str
    noncathode_losses_source_id: str
    clock_id: str
    origin: Origin

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            if name != "origin":
                _ids(getattr(self, name))
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError(
                "Resolve microbial cell assumptions or label an authored synthetic case"
            )


@dataclass(frozen=True, slots=True)
class MicrobialCellStage:
    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    anode_potential_v: float
    electrolyte_potential_v: float
    cathode_potential_bracket_v: tuple[float, float]
    native_phase_mole_fractions: Mapping[str, Mapping[str, float]]
    evidence_id: str
    connected: bool

    def __post_init__(self):
        _ids(self.identifier, self.clock_id, self.evidence_id)
        if finite(self.start_s, "stage start") >= finite(self.end_s, "stage end"):
            raise ValueError("Use increasing explicit seconds")
        finite(self.end_s - self.start_s, "stage duration", positive=True)
        finite(self.anode_potential_v, "anode potential in declared reference")
        finite(self.electrolyte_potential_v, "electrolyte potential in same reference")
        bracket = tuple(self.cathode_potential_bracket_v)
        if len(bracket) != 2 or finite(bracket[0], "lower potential") >= finite(
            bracket[1], "upper potential"
        ):
            raise ValueError("Supply an increasing cathode potential bracket")
        if type(self.connected) is not bool:
            raise TypeError("Declare circuit connection explicitly")
        groups = {}
        for phase, values in self.native_phase_mole_fractions.items():
            _ids(phase)
            composition = dict(values)
            if not composition or any(not isinstance(k, str) or not k for k in composition):
                raise ValueError("Declare full phase/species composition names")
            if any(finite(v, "native mole fraction") < 0 for v in composition.values()):
                raise ValueError("Native composition cannot be negative")
            if not math.isclose(
                _sum(composition.values(), "composition sum"), 1.0, abs_tol=1e-12, rel_tol=0
            ):
                raise ValueError(
                    "Explicit native phase composition must sum to one; no normalization"
                )
            groups[phase] = MappingProxyType(composition)
        object.__setattr__(self, "native_phase_mole_fractions", MappingProxyType(groups))
        object.__setattr__(self, "cathode_potential_bracket_v", bracket)


@dataclass(frozen=True, slots=True)
class CathodePoint:
    potential_v: float
    current_density_a_m2: float
    hydrogen_rate_mol_m2_s: float
    electron_consumption_mol_m2_s: float
    phase_current_a_m2: Mapping[str, float]
    native_production_rates_kmol_m2_s: Mapping[str, np.ndarray]
    native_phase_states: Mapping[str, np.ndarray]
    native_interface: object


class CanteraMicrobialCathode:
    """Actual caller-defined one-reaction H+/electron -> H2 native surface.

    A fresh privately owned graph is parsed independently from the same exact
    caller YAML; no unrelated gas/water mechanism is substituted. Surface
    coverages are held, not integrated. Full-cell biology stays outside Cantera.
    """

    def __init__(
        self,
        yaml_text,
        interface_name,
        *,
        gas_phase,
        electrolyte_phase,
        electron_phase,
        hydrogen_species,
        electron_species,
        proton_species,
        evidence: CathodeEvidence,
    ):
        import cantera as ct

        if tuple(int(v) for v in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("This source contract selects actual Cantera3.2")
        if not isinstance(evidence, CathodeEvidence) or not isinstance(yaml_text, str):
            raise TypeError("Supply actual cathode evidence and exact native YAML text")
        if hashlib.sha256(yaml_text.encode()).hexdigest() != evidence.mechanism_basis.source_sha256:
            raise ValueError("Native YAML differs from its declared source SHA256")
        self.native_module, self.evidence = ct, evidence
        self.source_interface = ct.Interface(yaml=yaml_text, name=interface_name)
        self.interface = ct.Interface(yaml=yaml_text, name=interface_name)
        self.phase_names = (gas_phase, electrolyte_phase, electron_phase)
        self.hydrogen_species, self.electron_species, self.proton_species = (
            hydrogen_species,
            electron_species,
            proton_species,
        )
        if (
            set(self.interface.adjacent) != set(self.phase_names)
            or self.interface.thermo_model != "ideal-surface"
        ):
            raise ValueError(
                "Declare exactly gas/electrolyte/electron adjacency and a native surface"
            )
        self.phases = tuple(self.interface.adjacent[n] for n in self.phase_names)
        source_phases = tuple(self.source_interface.adjacent[n] for n in self.phase_names)
        if self.interface is self.source_interface or any(
            a is b for a, b in zip(self.phases, source_phases, strict=True)
        ):
            raise ValueError("Original and owned native phase graphs must not alias")
        gas, electrolyte, electron = self.phases
        if (
            gas.thermo_model != "ideal-gas"
            or gas.species_names != [hydrogen_species]
            or electron.thermo_model != "electron-cloud"
            or electron.species_names != [electron_species]
            or electrolyte.thermo_model
            not in {"ideal-condensed", "ideal-molal-solution", "HMW-electrolyte", "Debye-Huckel"}
        ):
            raise ValueError(
                "Use pure native H2 gas, explicit condensed electrolyte and electron cloud"
            )
        if (
            dict(gas.species(hydrogen_species).composition) != {"H": 2.0}
            or electron.charges[0] != -1
        ):
            raise ValueError("Native H2/electron identities differ")
        proton = electrolyte.species(proton_species)
        if proton.charge != 1 or proton.composition.get("H") != 1:
            raise ValueError("Identify native H+ explicitly")
        if self.interface.n_reactions != 1:
            raise ValueError(
                "This cathode scope requires one explicit H2-producing reaction, no hidden side reactions"
            )
        reaction = self.interface.reaction(0)
        if dict(reaction.reactants) != {proton_species: 2.0, electron_species: 2.0} or dict(
            reaction.products
        ) != {hydrogen_species: 1.0}:
            raise ValueError("The actual native cathode must be exactly 2H+ +2e <=>H2")
        self.faraday_c_mol = ct.faraday / 1000.0
        if not math.isclose(self.faraday_c_mol, FARADAY_C_MOL, rel_tol=1e-9):
            raise ValueError("Native/shared Faraday constants use incompatible units/basis")
        self._source_phases = source_phases
        self._graph = (self.source_interface, *source_phases, self.interface, *self.phases)
        self._hashes = tuple(_phase_fingerprint(p, include_reactions=True) for p in self._graph)
        self._coverages = _array(self.interface.coverages)
        self._site_density = self.interface.site_density
        self._labels = (self.phase_names, hydrogen_species, electron_species, proton_species)
        self._evidence_fields = self._evidence_signature()
        self._faraday = self.faraday_c_mol

    def _evidence_signature(self):
        return (
            tuple(
                getattr(self.evidence, n)
                for n in self.evidence.__dataclass_fields__
                if n != "mechanism_basis"
            ),
            tuple(
                getattr(self.evidence.mechanism_basis, n)
                for n in self.evidence.mechanism_basis.__dataclass_fields__
            ),
        )

    def require_current(self):
        if (
            (self.phase_names, self.hydrogen_species, self.electron_species, self.proton_species)
            != self._labels
            or self._evidence_signature() != self._evidence_fields
            or self.faraday_c_mol != self._faraday
            or self.source_interface is not self._graph[0]
            or self.interface is not self._graph[4]
            or tuple(self.interface.adjacent[n] for n in self.phase_names) != self.phases
            or any(p is not q for p, q in zip(self.phases, self._graph[5:], strict=True))
            or tuple(_phase_fingerprint(p, include_reactions=True) for p in self._graph)
            != self._hashes
            or self.interface.site_density != self._site_density
        ):
            raise ValueError("Native cathode definitions/phase identities changed; rebind evidence")

    def evaluate(self, stage, inventory, cathode_potential_v):
        self.require_current()
        basis = self.evidence.mechanism_basis
        basis.require_state(inventory.temperature_k, inventory.pressure_pa)
        if set(stage.native_phase_mole_fractions) != set(self.phase_names):
            raise ValueError("Supply every actual adjacent phase composition")
        for name, phase in zip(self.phase_names, self.phases, strict=True):
            fractions = stage.native_phase_mole_fractions[name]
            if set(fractions) != set(phase.species_names):
                raise ValueError("Supply complete explicit native species fractions")
            for species in phase.species():
                if (
                    not species.thermo.min_temp
                    <= inventory.temperature_k
                    <= species.thermo.max_temp
                ):
                    raise ValueError("Native species fit domain exceeded")
            phase.TPX = inventory.temperature_k, inventory.pressure_pa, dict(fractions)
            if not np.allclose(
                phase.X, [fractions[n] for n in phase.species_names], rtol=0, atol=1e-12
            ):
                raise ValueError("Native composition normalization changed declared fractions")
            phase.electric_potential = (
                cathode_potential_v
                if name == self.phase_names[2]
                else stage.electrolyte_potential_v
            )
        self.interface.TP = inventory.temperature_k, inventory.pressure_pa
        self.interface.electric_potential = stage.electrolyte_potential_v
        self.interface.coverages = self._coverages
        currents, rates, states = {}, {}, {}
        for name, phase in zip(self.phase_names, self.phases, strict=True):
            currents[name] = finite(
                self.interface.interface_current(phase), "actual native phase current A/m2"
            )
            rates[name] = _array(self.interface.get_net_production_rates(phase))
            states[name] = _array(phase.state)
        gas_rate = finite(rates[self.phase_names[0]][0] * 1000.0, "native H2 mol/m2/s")
        electron_rate = finite(
            -rates[self.phase_names[2]][0] * 1000.0, "native electron consumption mol/m2/s"
        )
        result = CathodePoint(
            cathode_potential_v,
            currents[self.phase_names[2]],
            gas_rate,
            electron_rate,
            MappingProxyType(currents),
            MappingProxyType(rates),
            MappingProxyType(states),
            self.interface,
        )
        self.require_current()
        return result


@dataclass(frozen=True, slots=True)
class MicrobialCellStep:
    stage: MicrobialCellStage
    before: ThermochemicalInventory
    after: ThermochemicalInventory
    rate_state: MicrobialRateState
    rates: MicrobialRates
    cathode: CathodePoint | None
    native_root_result: object | None
    cathode_trials: tuple[CathodePoint, ...]
    kernel_trace: object
    current_a: float
    applied_voltage_v: float
    noncathode_loss_voltages_v: tuple
    transferred_electrons_mol: float
    hydrogen_generated_mol: float
    biomass_generated_mol: float
    electric_work_into_j: float
    isothermal_heat_required_into_j: float
    current_residual_a: float
    electron_residual_mol: float
    energy_residual_j: float


@dataclass(frozen=True, slots=True, weakref_slot=True)
class MicrobialCellTrace:
    initial: ThermochemicalInventory
    final: ThermochemicalInventory
    steps: tuple[MicrobialCellStep, ...]
    electron_equivalent_residual_mol: float
    hydrogen_generated_mol: float
    transferred_electrons_mol: float
    electric_work_into_j: float
    isothermal_heat_required_into_j: float
    hydrogen_residual_mol: float
    mass_residual_kg: float
    enthalpy_residual_j: float
    evidence: MicrobialCellEvidence
    native_cathode: CanteraMicrobialCathode
    kinetics: MicrobialKinetics
    caloric_provider: object
    kernel: FiniteThermochemicalCycle
    geometry: StackGeometry
    owner: "FiniteMicrobialCell"
    status: str = STATUS
    _admission: "MicrobialResultAdmission | None" = field(default=None, repr=False, compare=False)

    @property
    def admission(self):
        if self._admission is None:
            raise MicrobialResultVerificationError(
                "No producer-issued original-result admission", self, self.owner
            )
        return self._admission

    def require_current(self):
        # Dispatch the actual producer implementation, not an arbitrary object's
        # structural verify_result method supplied through a replaced owner field.
        if type(self.owner) is not FiniteMicrobialCell:
            raise MicrobialResultVerificationError(
                "No actual finite-cell producer binding", self, self.owner
            )
        return FiniteMicrobialCell.verify_result(self.owner, self)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class MicrobialResultAdmission:
    owner: "FiniteMicrobialCell"
    geometry: StackGeometry
    tolerances: ThermochemicalTolerances
    current_absolute_tolerance_a: float
    current_relative_tolerance: float
    maximum_root_iterations: int
    evidence: MicrobialCellEvidence
    native_cathode: CanteraMicrobialCathode
    kinetics: MicrobialKinetics
    caloric_provider: object
    kernel: FiniteThermochemicalCycle
    content_sha256: str
    owner_configuration_sha256: str
    native_state_sha256: str
    _original_trace_ref: object = field(repr=False, compare=False)
    verification_scope: str = (
        "producer identity and retained content/current native state; no model replay"
    )

    @property
    def original_trace(self):
        return self._original_trace_ref()


class MicrobialResultVerificationError(ValueError):
    def __init__(self, message, result, owner):
        super().__init__(message)
        self.result, self.owner = result, owner
        self.admission = getattr(result, "_admission", None)


class MicrobialCellError(ValueError):
    def __init__(
        self,
        message,
        *,
        stage,
        current,
        completed_steps,
        cathode,
        rate_state=None,
        raw_rates=None,
        trials=(),
        kernel_trace=None,
        point=None,
        trace=None,
    ):
        super().__init__(message)
        self.stage, self.current, self.completed_steps = stage, current, tuple(completed_steps)
        self.native_cathode, self.rate_state, self.raw_rates = cathode, rate_state, raw_rates
        self.cathode_trials, self.kernel_trace, self.cathode_point = (
            tuple(trials),
            kernel_trace,
            point,
        )
        self.trace = trace


class FiniteMicrobialCell:
    """Isothermal fixed-P batch, caller microbiology and native cathode current.

    Growth is applied first, then current-coupled catabolism. No aqueous pH,
    methanogenesis, gas transfer, electrical capacitance or anode-potential law
    is invented. Connected stages require a positive qualified catabolic rate;
    explicitly disconnected stages require zero catabolic rate.
    """

    def __init__(
        self,
        cathode,
        catabolism,
        growth,
        kinetics,
        caloric,
        geometry,
        evidence,
        *,
        substrate_id,
        biomass_id,
        hydrogen_id,
        liquid_volume_m3,
        electron_equivalents_mol_per_mol,
        noncathode_losses,
        tolerances=ThermochemicalTolerances(),
        current_absolute_tolerance_a=1e-9,
        current_relative_tolerance=1e-8,
        maximum_root_iterations=100,
    ):
        if not isinstance(cathode, CanteraMicrobialCathode) or not isinstance(
            kinetics, MicrobialKinetics
        ):
            raise TypeError("Use actual native cathode and explicit microbial kinetics")
        if not isinstance(geometry, StackGeometry) or geometry.series_cells != 1:
            raise ValueError(
                "This microbial model requires one explicit cell using shared StackGeometry"
            )
        if not isinstance(evidence, MicrobialCellEvidence):
            raise TypeError("Supply actual microbial/electrochemical boundary evidence")
        if (
            type(catabolism) is not StoichiometricReaction
            or type(growth) is not StoichiometricReaction
        ):
            raise TypeError(
                "Use actual shared StoichiometricReaction objects for both microbial paths"
            )
        if not isinstance(tolerances, ThermochemicalTolerances):
            raise TypeError("Use explicit common finite thermochemical tolerances")
        tolerances = ThermochemicalTolerances(
            **{n: getattr(tolerances, n) for n in tolerances.__dataclass_fields__}
        )
        reactions = tuple(
            StoichiometricReaction(r.identifier, r.species, r.coefficients)
            for r in (catabolism, growth)
        )
        if (
            reactions[0].species != reactions[1].species
            or tuple(caloric.species) != reactions[0].species
        ):
            raise ValueError(
                "Both actual reactions and caloric provider must share exact species/order/phases"
            )
        self.species = reactions[0].species
        self.names = tuple(s.identifier for s in self.species)
        if len({substrate_id, biomass_id, hydrogen_id}) != 3 or not {
            substrate_id,
            biomass_id,
            hydrogen_id,
        } <= set(self.names):
            raise ValueError(
                "Identify distinct actual substrate, biomass formula-unit and H2 species"
            )
        si, bi, hi = (self.names.index(n) for n in (substrate_id, biomass_id, hydrogen_id))
        if (
            reactions[0].coefficients[si] >= 0
            or reactions[0].coefficients[bi] != 0
            or reactions[0].coefficients[hi] <= 0
            or reactions[1].coefficients[si] >= 0
            or reactions[1].coefficients[bi] <= 0
            or reactions[1].coefficients[hi] != 0
        ):
            raise ValueError(
                "Declare substrate-consuming H2 catabolism and separate explicit biomass synthesis"
            )
        hydrogen = self.species[hi]
        if (
            dict(hydrogen.elements) != {"H": 2}
            or hydrogen.charge
            or hydrogen.phase not in {"gas", "ideal-gas", "vapor"}
            or hydrogen.molar_mass_kg_mol != geometry.hydrogen_molar_mass_kg_mol
        ):
            raise ValueError("Shared geometry and actual gas-phase H2 material bases differ")
        if hydrogen.molar_mass_kg_mol != cathode.phases[0].molecular_weights[0] / 1000.0:
            raise ValueError("Native cathode and finite H2 atomic-weight bases differ")
        if self.species[si].phase not in {"aqueous", "liquid"} or not (
            self.species[bi].phase in {"biomass", "solid"}
            or self.species[bi].phase.startswith("biomass:")
        ):
            raise ValueError("Declare actual condensed substrate and biomass formula-unit phases")
        if any(
            dict(s.elements) == {"H": 2, "O": 1} and s.phase not in {"aqueous", "liquid"}
            for s in self.species
        ):
            raise ValueError(
                "Do not substitute vapor/gas water for the declared aqueous microbial medium"
            )
        if (
            evidence.caloric_basis_id != caloric.basis_id
            or cathode.evidence.caloric_reference_id != caloric.basis_id
            or evidence.electrode_reference_id != cathode.evidence.electrode_reference_id
        ):
            raise ValueError("Declare common actual caloric and electrode potential references")
        gamma = dict(electron_equivalents_mol_per_mol)
        if set(gamma) != set(self.names) or gamma[hydrogen_id] != 2.0:
            raise ValueError(
                "Explicit complete species electron-equivalent basis must assign H2 two electrons/mol"
            )
        for name, value in gamma.items():
            if finite(value, name + " electron equivalents") < 0:
                raise ValueError(
                    "This conditional basis admits nonnegative explicit reduction equivalents"
                )
        self._gamma = _array([gamma[n] for n in self.names])
        for reaction in reactions:
            if (
                abs(
                    _sum(
                        self._gamma * np.array(reaction.coefficients),
                        "stoichiometric electron residual",
                    )
                )
                > tolerances.amount_mol
            ):
                raise ValueError(
                    "Declared biochemical reaction does not conserve the supplied electron-equivalent basis"
                )
        finite(liquid_volume_m3, "declared liquid kinetic volume m3", positive=True)
        finite(current_absolute_tolerance_a, "current tolerance", positive=True)
        finite(current_relative_tolerance, "relative current tolerance", positive=True)
        if (
            isinstance(maximum_root_iterations, bool)
            or not isinstance(maximum_root_iterations, int)
            or maximum_root_iterations < 2
        ):
            raise ValueError("Bound the native cathode root iterations explicitly")
        losses = dict(noncathode_losses)
        if any(not name or not callable(value) for name, value in losses.items()):
            raise ValueError(
                "Supply named existing noncathode loss callables and their source evidence"
            )
        self.cathode, self.catabolism, self.growth = cathode, catabolism, growth
        self.kinetics, self.caloric, self.geometry, self.evidence = (
            kinetics,
            caloric,
            geometry,
            evidence,
        )
        self.substrate_id, self.biomass_id, self.hydrogen_id = substrate_id, biomass_id, hydrogen_id
        self.liquid_volume_m3 = liquid_volume_m3
        self.electron_equivalents = MappingProxyType(gamma)
        self.losses = MappingProxyType(losses)
        self.tolerances = tolerances
        self.current_absolute_tolerance_a, self.current_relative_tolerance = (
            current_absolute_tolerance_a,
            current_relative_tolerance,
        )
        self.maximum_root_iterations = maximum_root_iterations
        kernel_evidence = ThermochemicalEvidence(
            evidence.process_id,
            evidence.isothermal_fixed_pressure_boundary_id,
            "closed-batch-no-takeoff",
            evidence.isothermal_fixed_pressure_boundary_id,
            evidence.origin,
        )
        self.kernel = FiniteThermochemicalCycle(caloric, kernel_evidence, tolerances=tolerances)
        self._binding = (
            cathode,
            catabolism,
            growth,
            kinetics,
            caloric,
            geometry,
            evidence,
            kinetics.callback,
            self.kernel,
            self.tolerances,
        )
        self._definition = self._signature()
        self._definition_sha256 = _recorded_sha(self._signature())
        self._kernel_definition_sha256 = _recorded_sha(self._kernel_data())
        # The trace owns its admission. Registration is weak, so the producer
        # does not keep every past native trace alive for its whole lifetime.
        self._issued_results = weakref.WeakValueDictionary()

    def _signature(self):
        return (
            self.names,
            tuple(
                (
                    s.identifier,
                    tuple(sorted(s.elements.items())),
                    s.molar_mass_kg_mol,
                    s.phase,
                    s.charge,
                )
                for s in self.caloric.species
            ),
            self.catabolism.species,
            self.catabolism.coefficients,
            self.growth.species,
            self.growth.coefficients,
            tuple(self.kinetics.parameters.items()),
            tuple(self.electron_equivalents.items()),
            self.caloric.basis_id,
            tuple(getattr(self.evidence, n) for n in self.evidence.__dataclass_fields__),
            (
                self.geometry.series_cells,
                self.geometry.active_area_m2,
                self.geometry.hydrogen_molar_mass_kg_mol,
            ),
            tuple(self.losses.items()),
            tuple(getattr(self.caloric, "functions", ())),
            self.kinetics.source_id,
            self.kinetics.parameter_source_id,
            self.kinetics.origin,
            self.kinetics.temperature_bounds_k,
            self.kinetics.substrate_concentration_bounds_mol_m3,
            self.kinetics.biomass_concentration_bounds_mol_m3,
            id(self.kinetics.native_model),
            tuple(getattr(self.tolerances, n) for n in self.tolerances.__dataclass_fields__),
            self.current_absolute_tolerance_a,
            self.current_relative_tolerance,
            self.maximum_root_iterations,
            self.substrate_id,
            self.biomass_id,
            self.hydrogen_id,
            self.liquid_volume_m3,
            getattr(self.caloric, "temperature_bounds_k", None),
            getattr(self.caloric, "pressure_bounds_pa", None),
            self.caloric.enthalpies_j_mol,
            self._gamma,
            self.cathode.evaluate,
            self.cathode.require_current,
            self.cathode.native_module,
            self.cathode._coverages,
        )

    def _kernel_data(self):
        return (
            self.kernel,
            self.kernel.enthalpy,
            self.kernel.tolerances,
            self.kernel.evidence,
            self.kernel.species,
            self.kernel.names,
            self.kernel.elements,
            self.kernel.energy_basis_id,
            self.kernel._atoms,
            self.kernel._masses,
            self.kernel.run,
            self.kernel._h,
        )

    def _result_configuration(self):
        return (
            self._signature(),
            self._kernel_data(),
            _caloric_binding(self.caloric, self.cathode.native_module),
            self.cathode.native_module,
            self.cathode._coverages,
            self.kinetics.callback,
            self.kinetics.native_model,
            self.geometry,
            self.tolerances,
            self.evidence,
        )

    def _result_native_state(self):
        return (_stored_native_state(self.cathode), self.cathode._coverages)

    def _guard(self):
        if (
            any(
                current is not prior
                for current, prior in zip(
                    (
                        self.cathode,
                        self.catabolism,
                        self.growth,
                        self.kinetics,
                        self.caloric,
                        self.geometry,
                        self.evidence,
                        self.kinetics.callback,
                        self.kernel,
                        self.tolerances,
                    ),
                    self._binding,
                    strict=True,
                )
            )
            or _recorded_sha(self._signature()) != self._definition_sha256
            or self.kernel.enthalpy is not self.caloric
            or self.kernel.tolerances is not self.tolerances
            or _recorded_sha(self._kernel_data()) != self._kernel_definition_sha256
        ):
            raise ValueError(
                "Native/biological/reaction/reference binding changed; construct a newly evidenced cell"
            )
        self.cathode.require_current()

    def require_current(self):
        """Check admitted owner definitions only, without rate/property solves."""
        self._guard()
        return self

    def verify_result(self, result):
        """Return only the original issued trace with unchanged retained evidence.

        No cathode current/rate, kinetic callback, caloric query, conversion,
        root or material/energy solve is replayed. Native stored-state getters
        and definition serialization are read for the strict current-state seal.
        """
        try:
            if type(result) is not MicrobialCellTrace or result.owner is not self:
                raise ValueError(
                    "Only this actual producer's original MicrobialCellTrace is admissible"
                )
            admission = result._admission
            if (
                admission is None
                or self._issued_results.get(id(result)) is not admission
                or admission.original_trace is not result
                or admission.owner is not self
            ):
                raise ValueError(
                    "Result is replaced, unissued or no longer registered to its producer"
                )
            self._guard()
            if (
                result.geometry is not self.geometry
                or admission.geometry is not self.geometry
                or admission.tolerances is not self.tolerances
                or result.evidence is not self.evidence
                or result.native_cathode is not self.cathode
                or result.kinetics is not self.kinetics
                or result.caloric_provider is not self.caloric
                or result.kernel is not self.kernel
                or admission.evidence is not self.evidence
                or admission.native_cathode is not self.cathode
                or admission.kinetics is not self.kinetics
                or admission.caloric_provider is not self.caloric
                or admission.kernel is not self.kernel
                or admission.current_absolute_tolerance_a != self.current_absolute_tolerance_a
                or admission.current_relative_tolerance != self.current_relative_tolerance
                or admission.maximum_root_iterations != self.maximum_root_iterations
            ):
                raise ValueError(
                    "Original geometry/admission/caloric/kinetic/evidence bindings changed"
                )
            if _recorded_sha(self._result_configuration()) != admission.owner_configuration_sha256:
                raise ValueError("Original producer parameter/callable/caloric bindings changed")
            if _recorded_sha(self._result_native_state()) != admission.native_state_sha256:
                raise ValueError(
                    "Retained native scratch phase/state changed since this result was issued"
                )
            if _recorded_sha(result) != admission.content_sha256:
                raise ValueError(
                    "Retained trace/native cache/root/material/charge/thermal evidence changed"
                )
            return result
        except Exception as cause:
            raise MicrobialResultVerificationError(str(cause), result, self) from cause

    def _issue_result(self, result):
        self._guard()
        admission = MicrobialResultAdmission(
            self,
            self.geometry,
            self.tolerances,
            self.current_absolute_tolerance_a,
            self.current_relative_tolerance,
            self.maximum_root_iterations,
            self.evidence,
            self.cathode,
            self.kinetics,
            self.caloric,
            self.kernel,
            _recorded_sha(result),
            _recorded_sha(self._result_configuration()),
            _recorded_sha(self._result_native_state()),
            weakref.ref(result),
        )
        object.__setattr__(result, "_admission", admission)
        self._issued_results[id(result)] = admission
        return result

    def run(self, initial, stages):
        self._guard()
        if not isinstance(initial, ThermochemicalInventory):
            raise TypeError("Supply actual finite phase-resolved molar inventory")
        current = ThermochemicalInventory(
            initial.amounts_mol, initial.temperature_k, initial.pressure_pa, initial.energy_basis_id
        )
        initial = current
        if current.energy_basis_id != self.caloric.basis_id:
            raise ValueError("Initial caloric reference differs")
        self.catabolism.amounts(current.amounts_mol)
        schedule = tuple(stages)
        if not schedule or not all(isinstance(s, MicrobialCellStage) for s in schedule):
            raise ValueError("Supply an explicit nonempty microbial stage schedule")
        schedule = tuple(
            MicrobialCellStage(**{n: getattr(s, n) for n in s.__dataclass_fields__})
            for s in schedule
        )
        if len({s.identifier for s in schedule}) != len(schedule):
            raise ValueError("Stage identities must be unique")
        for a, b in zip(schedule[:-1], schedule[1:], strict=True):
            if a.end_s != b.start_s or a.clock_id != b.clock_id:
                raise ValueError(
                    "Microbial stages require contiguous physical seconds and one clock"
                )
        results = []
        for stage in schedule:
            before, state, raw, point, kernel_trace = current, None, None, None, None
            trials = []
            try:
                self._guard()
                if stage.clock_id != self.evidence.clock_id:
                    raise ValueError("Microbial kinetic and electrical clocks differ")
                state = MicrobialRateState(
                    stage.start_s,
                    stage.clock_id,
                    before,
                    self.liquid_volume_m3,
                    self.substrate_id,
                    self.biomass_id,
                )
                self.kinetics.require_state(state)
                raw = self.kinetics.callback(state, self.kinetics.parameters)
                if not isinstance(raw, MicrobialRates):
                    raise TypeError("Kinetic callback must return actual explicit MicrobialRates")
                rates = MicrobialRates(raw.catabolic_extent_mol_s, raw.growth_extent_mol_s)
                self._guard()
                if (
                    rates.catabolic_extent_mol_s > 0 or rates.growth_extent_mol_s > 0
                ) and before.amounts_mol.get(self.biomass_id, 0.0) <= 0:
                    raise ValueError(
                        "Active microbial rates require a finite positive biomass inoculum"
                    )
                if stage.connected and before.amounts_mol.get(self.hydrogen_id, 0.0) <= 0:
                    raise ValueError(
                        "Prescribed pure-H2 gas activity requires a finite positive initial gas inventory"
                    )
                dt = stage.end_s - stage.start_s
                growth_extent = finite(rates.growth_extent_mol_s * dt, "growth extent")
                requested_extent = finite(
                    rates.catabolic_extent_mol_s * dt, "requested catabolic extent"
                )
                first = self.growth.convert(before.amounts_mol, growth_extent)
                self.catabolism.convert(first.final_amounts, requested_extent)
                if stage.connected != (rates.catabolic_extent_mol_s > 0):
                    raise ValueError(
                        "Connected stages require positive catabolism; stopped stages must explicitly disconnect"
                    )
                root_result, losses, current_a, voltage, accepted_extent = None, (), 0.0, 0.0, 0.0
                current_residual, electron_residual = 0.0, 0.0
                if stage.connected:
                    target = finite(
                        2
                        * self.catabolism.coefficients[self.names.index(self.hydrogen_id)]
                        * rates.catabolic_extent_mol_s
                        * self.cathode.faraday_c_mol,
                        "target current",
                    )

                    def residual(potential):
                        trial = self.cathode.evaluate(stage, before, potential)
                        trials.append(trial)
                        return finite(
                            trial.current_density_a_m2 * self.geometry.active_area_m2 - target,
                            "native current residual",
                        )

                    potential, root_result = brentq(
                        residual,
                        *stage.cathode_potential_bracket_v,
                        xtol=1e-12,
                        rtol=4 * np.finfo(float).eps,
                        maxiter=self.maximum_root_iterations,
                        full_output=True,
                        disp=True,
                    )
                    residual(potential)
                    point = trials[-1]
                    current_a = finite(
                        point.current_density_a_m2 * self.geometry.active_area_m2,
                        "native current A",
                    )
                    current_residual = current_a - target
                    budget = (
                        self.current_absolute_tolerance_a
                        + self.current_relative_tolerance * abs(target)
                    )
                    if (
                        not root_result.converged
                        or abs(current_residual) > budget
                        or min(
                            current_a,
                            point.hydrogen_rate_mol_m2_s,
                            point.electron_consumption_mol_m2_s,
                        )
                        < 0
                    ):
                        raise ValueError("Native cathode current/forward-H2/root gate failed")
                    if (
                        abs(_sum(point.phase_current_a_m2.values(), "native phase charge current"))
                        * self.geometry.active_area_m2
                        > budget
                    ):
                        raise ValueError("Native interphase current does not close")
                    accepted_extent = finite(
                        point.hydrogen_rate_mol_m2_s
                        * self.geometry.active_area_m2
                        * dt
                        / self.catabolism.coefficients[self.names.index(self.hydrogen_id)],
                        "native-coupled extent",
                    )
                    electron_residual = finite(
                        (point.electron_consumption_mol_m2_s - 2 * point.hydrogen_rate_mol_m2_s)
                        * self.geometry.active_area_m2
                        * dt,
                        "native H2/electron residual",
                    )
                    if abs(electron_residual) > self.tolerances.amount_mol:
                        raise ValueError("Native cathode electron/H2 material balance failed")
                    losses = tuple(
                        (
                            name,
                            finite(
                                fn(point.current_density_a_m2, before.temperature_k),
                                name + " voltage loss",
                            ),
                        )
                        for name, fn in self.losses.items()
                    )
                    if any(value < 0 for _, value in losses):
                        raise ValueError("Noncathode loss cannot be negative")
                    voltage = finite(
                        stage.anode_potential_v
                        - point.potential_v
                        + _sum((v for _, v in losses), "voltage losses"),
                        "applied external cell voltage",
                    )
                    if voltage < 0:
                        raise ValueError(
                            "This production level excludes power-generating/reverse operation"
                        )
                kernel_trace = self.kernel.run(
                    before,
                    (
                        ThermochemicalStage(
                            stage.identifier,
                            stage.start_s,
                            stage.end_s,
                            stage.clock_id,
                            before.temperature_k,
                            (
                                PrescribedConversion(self.growth, growth_extent, stage.evidence_id),
                                PrescribedConversion(
                                    self.catabolism, accepted_extent, stage.evidence_id
                                ),
                            ),
                            stage.evidence_id,
                        ),
                    ),
                    carrier_species=(self.biomass_id,),
                    require_carrier_closed=False,
                    require_temperature_closed=True,
                )
                if point is not None:
                    native_h2_h = self.cathode.phases[0].partial_molar_enthalpies[0] / 1000.0
                    host_h = self.kernel._h(before.temperature_k, before.pressure_pa)[
                        self.names.index(self.hydrogen_id)
                    ]
                    if abs(host_h - native_h2_h) > self.tolerances.energy_j:
                        raise ValueError(
                            "Native cathode and net-reaction H2 enthalpy references differ"
                        )
                work = finite(current_a * voltage * dt, "external electrical work")
                heat = finite(
                    kernel_trace.net_heat_required_j - work, "required isothermal heat into cell"
                )
                hydrogen = finite(
                    accepted_extent
                    * self.catabolism.coefficients[self.names.index(self.hydrogen_id)],
                    "generated H2 mol",
                )
                electrons = finite(
                    current_a * dt / self.cathode.faraday_c_mol, "transferred electron mol"
                )
                if abs(electrons - 2 * hydrogen) > self.tolerances.amount_mol:
                    raise ValueError("Actual current charge and generated H2 differ")
                after = kernel_trace.final
                gamma_residual = _sum(
                    self._gamma
                    * (
                        self.catabolism.amounts(after.amounts_mol)
                        - self.catabolism.amounts(before.amounts_mol)
                    ),
                    "finite electron-equivalent residual",
                )
                if abs(gamma_residual) > self.tolerances.amount_mol:
                    raise ValueError(
                        "Finite substrate/biomass/products electron equivalents do not close"
                    )
                energy_residual = finite(
                    kernel_trace.net_heat_required_j - work - heat,
                    "electrical/thermal enthalpy residual",
                )
                self._guard()
                results.append(
                    MicrobialCellStep(
                        stage,
                        before,
                        after,
                        state,
                        rates,
                        point,
                        root_result,
                        tuple(trials),
                        kernel_trace,
                        current_a,
                        voltage,
                        losses,
                        electrons,
                        hydrogen,
                        growth_extent * self.growth.coefficients[self.names.index(self.biomass_id)],
                        work,
                        heat,
                        current_residual,
                        electron_residual,
                        energy_residual,
                    )
                )
                current = after
            except Exception as error:
                raise MicrobialCellError(
                    str(error),
                    stage=stage,
                    current=before,
                    completed_steps=results,
                    cathode=self.cathode,
                    rate_state=state,
                    raw_rates=raw,
                    trials=trials,
                    kernel_trace=kernel_trace,
                    point=point,
                ) from error
        result = None
        try:
            n0 = self.catabolism.amounts(initial.amounts_mol)
            nf = self.catabolism.amounts(current.amounts_mol)
            delta = _array(nf - n0)
            electron_error = _sum(self._gamma * delta, "global electron-equivalent residual")
            hydrogen = _sum((s.hydrogen_generated_mol for s in results), "total H2")
            electrons = _sum((s.transferred_electrons_mol for s in results), "total electrons")
            work = _sum((s.electric_work_into_j for s in results), "total electrical work")
            heat = _sum((s.isothermal_heat_required_into_j for s in results), "required heat")
            h2_error = finite(
                delta[self.names.index(self.hydrogen_id)] - hydrogen, "finite H2 stock residual"
            )
            if (
                max(abs(electron_error), abs(h2_error), abs(electrons - 2 * hydrogen))
                > self.tolerances.amount_mol
            ):
                raise ValueError("Global H2/current/electron-equivalent ledger failed")
            h0 = self.kernel._h(initial.temperature_k, initial.pressure_pa)
            hf = self.kernel._h(current.temperature_k, current.pressure_pa)
            before_h = _sum(n0 * h0, "initial enthalpy")
            after_h = _sum(nf * hf, "final enthalpy")
            energy_error = _sum((after_h, -before_h, -work, -heat), "global enthalpy residual")
            mass = _sum(delta * self.kernel._masses, "global mass residual")
            self.kernel._check_balance(
                self.kernel._atoms @ delta,
                mass,
                energy_error,
                _sum(n0, "initial amount scale"),
                max(abs(before_h), abs(after_h), abs(work), abs(heat)),
            )
            self._guard()
            result = MicrobialCellTrace(
                initial,
                current,
                tuple(results),
                electron_error,
                hydrogen,
                electrons,
                work,
                heat,
                h2_error,
                mass,
                energy_error,
                self.evidence,
                self.cathode,
                self.kinetics,
                self.caloric,
                self.kernel,
                self.geometry,
                self,
            )
            return self._issue_result(result)
        except Exception as error:
            raise MicrobialCellError(
                str(error),
                stage=schedule[-1],
                current=current,
                completed_steps=results,
                cathode=self.cathode,
                kernel_trace=results[-1].kernel_trace,
                trace=result,
            ) from error
