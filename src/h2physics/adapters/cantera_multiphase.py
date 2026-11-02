"""Native Cantera multiphase equilibrium with extensive SI material/energy audits.

One ideal gas and neutral constant-volume stoichiometric solids are supported.
Cantera Mixture owns Gibbs minimization and HP temperature iteration. No kinetic
ODE, gasification reaction solver or EOS is implemented here.
https://cantera.org/3.2/python/thermo.html#cantera.Mixture
"""

import math
import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, finite
from .cantera import MechanismBasis
from .cantera_volume import NativePhaseCopyAudit, _phase_fingerprint, _private_native_phase


def _array(values):
    result = np.array(values, dtype=float, copy=True)
    result = immutable_array(result, name="result")
    return result


_PENDING_EQUILIBRIUM_RESULT_ISSUERS: set[object] = set()


def _issue_equilibrium_result(**values):
    token = object()
    _PENDING_EQUILIBRIUM_RESULT_ISSUERS.add(token)
    try:
        return MultiphaseEquilibriumResult(**values, _issuer_token=token)
    except Exception:
        _PENDING_EQUILIBRIUM_RESULT_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class EquilibriumPhase:
    phase_id: str
    role: str
    factory: Callable
    mechanism_basis: MechanismBasis
    energy_reference_id: str
    hydrogen_partition_id: str

    def __post_init__(self):
        if not all(isinstance(s, str) and s.strip() for s in (
                self.phase_id, self.energy_reference_id, self.hydrogen_partition_id)):
            raise ValueError("Declare phase, common caloric-reference and hydrogen-partition identities")
        if self.role not in {"gas", "solid"} or not callable(self.factory):
            raise ValueError("Declare a native gas/solid phase and its factory")


@dataclass(frozen=True, slots=True)
class MultiphaseFeed:
    temperature_k: float
    pressure_pa: float
    species_mol: Mapping[str, Mapping[str, float]]
    source_id: str
    origin: Origin

    def __post_init__(self):
        finite(self.temperature_k, "feed temperature", positive=True)
        finite(self.pressure_pa, "feed absolute pressure", positive=True)
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("Declare finite-feed provenance")
        amounts = {p: dict(values) for p, values in self.species_mol.items()}
        if not amounts or any(not p for p in amounts):
            raise ValueError("Declare every candidate phase, including zero initial solids")
        values = []
        for species in amounts.values():
            for name, amount in species.items():
                if not name or finite(amount, "SI species amount mol") < 0:
                    raise ValueError("Finite species amounts must be nonnegative; they are not normalized")
                values.append(amount)
        finite(math.fsum(values), "total finite feed mol", positive=True)
        object.__setattr__(self, "species_mol", MappingProxyType(
            {key: MappingProxyType(value) for key, value in amounts.items()}))
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve the feed data role")


@dataclass(frozen=True, slots=True)
class MultiphaseSettings:
    solver: str = "vcs"
    relative_tolerance: float = 1e-10
    maximum_steps: int = 2000
    maximum_iterations: int = 300
    estimate_equilibrium: int = 0

    def __post_init__(self):
        if self.solver not in {"vcs", "gibbs"}:
            raise ValueError("Choose the actual native equilibrium solver explicitly")
        if not 0 < finite(self.relative_tolerance, "native equilibrium tolerance") < 1:
            raise ValueError("Native equilibrium tolerance must lie in (0,1)")
        for name in ("maximum_steps", "maximum_iterations"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Native iteration limits must be positive integers")
        if isinstance(self.estimate_equilibrium, bool) or self.estimate_equilibrium not in {-1, 0, 1}:
            raise ValueError("Use a documented native estimate_equil flag")


@dataclass(frozen=True, slots=True)
class MultiphaseTolerances:
    element_absolute_mol: float = 1e-9
    mass_absolute_kg: float = 1e-10
    energy_absolute_j: float = 1e-5
    relative: float = 1e-8
    chemical_potential_over_rt: float = 1e-5
    active_species_relative: float = 1e-10
    active_species_absolute_mol: float = 1e-14

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class MultiphaseSnapshot:
    temperature_k: float
    pressure_pa: float
    species_mol: np.ndarray
    phase_mol: np.ndarray
    element_mol: np.ndarray
    mass_kg: float
    enthalpy_j: float
    internal_energy_j: float
    entropy_j_k: float
    gibbs_energy_j: float
    volume_m3: float
    chemical_potentials_j_mol: np.ndarray

    def __post_init__(self):
        for name in ("species_mol", "phase_mol", "element_mol", "chemical_potentials_j_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class ChemicalPotentialAudit:
    element_potentials_j_mol: Mapping[str, float]
    populated_species_count: int
    feasible_trace_species_count: int
    active_amount_threshold_mol: float
    maximum_populated_affinity_over_rt: float
    absent_solid_affinity_over_rt: Mapping[str, float]
    element_matrix_rank: int

    def __post_init__(self):
        for name in ("element_potentials_j_mol", "absent_solid_affinity_over_rt"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True, slots=True)
class MultiphaseEquilibriumResult:
    phases: tuple[EquilibriumPhase, ...]
    feed: MultiphaseFeed
    constraint: str
    settings: MultiphaseSettings
    tolerances: MultiphaseTolerances
    species_keys: tuple[tuple[str, str], ...]
    element_names: tuple[str, ...]
    initial: MultiphaseSnapshot
    final: MultiphaseSnapshot
    heat_into_j: float
    pressure_volume_work_out_j: float
    energy_balance_residual_j: float
    enthalpy_constraint_residual_j: float
    mass_residual_kg: float
    element_residual_mol: np.ndarray
    chemical_audit: ChemicalPotentialAudit
    native_mixture: Any
    source_phases: tuple
    owned_phases: tuple
    phase_copy_audits: tuple
    gates: Mapping[str, bool]
    accepted: bool
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _signature: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_EQUILIBRIUM_RESULT_ISSUERS:
            raise ValueError("Multiphase equilibrium results require native solver issuance")
        _PENDING_EQUILIBRIUM_RESULT_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "element_residual_mol", _array(self.element_residual_mol))
        object.__setattr__(self, "gates", MappingProxyType(dict(self.gates)))
        object.__setattr__(self, "_signature", self._current_signature())

    def _current_signature(self):
        snapshots = tuple(tuple((name, getattr(snapshot, name)) for name in (
            "temperature_k", "pressure_pa", "mass_kg", "enthalpy_j", "internal_energy_j",
            "entropy_j_k", "gibbs_energy_j", "volume_m3")) + tuple(
            (name, np.asarray(getattr(snapshot, name)).tobytes()) for name in (
                "species_mol", "phase_mol", "element_mol", "chemical_potentials_j_mol"))
            for snapshot in (self.initial, self.final))
        phase_states = tuple(_phase_fingerprint(phase, include_reactions=True)
                             for phase in (*self.source_phases, *self.owned_phases))
        native_state = (float(self.native_mixture.T), float(self.native_mixture.P),
                        np.asarray(self.native_mixture.species_moles).tobytes(),
                        np.asarray(self.native_mixture.phase_moles()).tobytes())
        payload = (tuple(id(phase) for phase in self.phases), id(self.feed), self.constraint,
                   self.settings, self.tolerances, self.species_keys, self.element_names,
                   snapshots, self.heat_into_j, self.pressure_volume_work_out_j,
                   self.energy_balance_residual_j, self.enthalpy_constraint_residual_j,
                   self.mass_residual_kg, np.asarray(self.element_residual_mol).tobytes(),
                   self.chemical_audit, id(self.native_mixture), native_state, phase_states,
                   tuple(id(value) for value in self.source_phases),
                   tuple(id(value) for value in self.owned_phases), self.phase_copy_audits,
                   tuple(self.gates.items()), self.accepted)
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def require_current(self):
        try:
            current = self._current_signature()
        except Exception as error:
            raise ValueError("Native multiphase result state is no longer readable") from error
        if current != self._signature:
            raise ValueError("Native multiphase equilibrium result changed after issuance")
        return self

    def amount_mol(self, phase_id, species_name):
        self.require_current()
        return float(self.final.species_mol[self.species_keys.index((phase_id, species_name))])


class MultiphaseEquilibriumError(RuntimeError):
    """Retains actual partial/completed native objects and the original cause."""

    def __init__(self, message, *, native_mixture, source_phases, owned_phases,
                 phase_copy_audits, initial, final, native_solver_completed, result=None):
        self.native_mixture = native_mixture
        self.source_phases, self.owned_phases = tuple(source_phases), tuple(owned_phases)
        self.phase_copy_audits = tuple(phase_copy_audits)
        self.initial, self.final = initial, final
        self.native_solver_completed, self.result = native_solver_completed, result
        super().__init__(message)


def _solid_copy(source, ct):
    # Native serialization creates independent native objects. The original
    # thermo object is never reused; exact fit bounds/coefficients are restored.
    source.density_mass
    owned = ct.Solution(yaml=source.write_yaml(precision=17), name=source.name)
    original, replacement = source.species(0), owned.species(0)
    thermo = original.thermo
    replacement.thermo = type(thermo)(thermo.min_temp, thermo.max_temp,
                                     thermo.reference_pressure, thermo.coeffs)
    owned.modify_species(0, replacement)
    owned.state, owned.basis = source.state, source.basis
    a, b = original.thermo, owned.species(0).thermo
    if (type(a) is not type(b) or a.min_temp != b.min_temp or a.max_temp != b.max_temp
            or a.reference_pressure != b.reference_pressure or not np.array_equal(a.coeffs, b.coeffs)
            or original.composition != owned.species(0).composition
            or set(source.element_names) != set(owned.element_names)
            or any(source.atomic_weight(e) != owned.atomic_weight(e) for e in source.element_names)
            or not np.array_equal(source.molecular_weights, owned.molecular_weights)
            or not np.array_equal(source.charges, owned.charges)
            or source.density_mass != owned.density_mass):
        raise ValueError("Native solid copy changed its constant-volume/thermo definition")
    for phase in (source, owned):
        eos = dict(phase.species(0).input_data).get("equation-of-state", {})
        if eos.get("model") != "constant-volume" or set(eos)-{"model", "density", "molar-volume"}:
            raise ValueError("Only an explicit constant-volume pure-solid EOS is checked")
    source_data, owned_data = dict(original.input_data), dict(owned.species(0).input_data)
    omitted_notes = int(source_data.get("note") != owned_data.get("note"))+int(
        source_data["thermo"].get("note") != owned_data["thermo"].get("note"))
    return owned, NativePhaseCopyAudit(_phase_fingerprint(source, include_reactions=True),
        _phase_fingerprint(owned, include_reactions=True), 0., 0, omitted_notes,
        tuple(source.element_names), tuple(owned.element_names))


def _snapshot(mixture, elements):
    mu = np.asarray(mixture.chemical_potentials)/1000.
    phase_amounts = np.array(mixture.phase_moles())
    phases = [mixture.phase(i) for i in range(mixture.n_phases)]
    mass = sum(n*p.mean_molecular_weight for n, p in zip(phase_amounts, phases, strict=True))
    properties = [sum(n*getattr(p, name) for n, p in zip(phase_amounts, phases, strict=True))
                  for name in ("enthalpy_mole", "int_energy_mole", "entropy_mole", "gibbs_mole")]
    volume = sum(n*p.mean_molecular_weight/p.density_mass
                 for n, p in zip(phase_amounts, phases, strict=True))
    return MultiphaseSnapshot(mixture.T, mixture.P, np.asarray(mixture.species_moles)*1000.,
        phase_amounts*1000., [mixture.element_moles(e)*1000. for e in elements], mass,
        *properties, volume, mu)


def _chemical_audit(before, after, atom_matrix, elements, phases, phase_sizes, tolerances, gas_constant):
    threshold = max(tolerances.active_species_absolute_mol,
                    tolerances.active_species_relative*float(before.species_mol.sum()))
    active_elements = before.element_mol > tolerances.element_absolute_mol
    feasible = np.all(atom_matrix[~active_elements] == 0, axis=0)
    populated = feasible & (after.species_mol > threshold)
    matrix = atom_matrix[active_elements][:, populated].T
    potentials, _, rank, _ = np.linalg.lstsq(matrix, after.chemical_potentials_j_mol[populated], rcond=None)
    affinity = after.chemical_potentials_j_mol-atom_matrix[active_elements].T@potentials
    rt = gas_constant*after.temperature_k/1000.
    maximum = float(np.max(abs(affinity[populated]))/rt) if np.any(populated) else math.inf
    absent, offset = {}, 0
    for i, (phase, size) in enumerate(zip(phases, phase_sizes, strict=True)):
        if phase.role == "solid" and after.phase_mol[i] <= threshold and feasible[offset]:
            absent[phase.phase_id] = float(affinity[offset]/rt)
        offset += size
    return ChemicalPotentialAudit(dict(zip(np.asarray(elements)[active_elements], potentials, strict=True)),
        int(populated.sum()), int((feasible & ~populated).sum()), threshold, maximum, absent, int(rank))


class CanteraMultiphaseEquilibrium:
    def __init__(self, phases, *, tolerances: MultiphaseTolerances = MultiphaseTolerances()):
        import cantera as ct

        if tuple(int(v) for v in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("This multiphase native copy/equilibrium level is checked with Cantera3.2")
        self.ct, self.phases, self.tolerances = ct, tuple(phases), tolerances
        if (not self.phases or len({p.phase_id for p in self.phases}) != len(self.phases)
                or sum(p.role == "gas" for p in self.phases) != 1):
            raise ValueError("Declare one unique gas and explicit candidate solid phases")
        if len({p.energy_reference_id for p in self.phases}) != 1:
            raise ValueError("All phases require one explicit compatible formation-energy reference")
        if len({p.hydrogen_partition_id for p in self.phases}) != 1:
            raise ValueError("All phases must retain the same declared hydrogen-partition identity")
        self._source_fingerprints = {}

    def equilibrate(self, feed: MultiphaseFeed, *, constraint="TP", settings=MultiphaseSettings(),
                    require_accepted=True):
        if constraint not in {"TP", "HP"}:
            raise ValueError("This native multiphase level supports TP or HP, not a kinetic trajectory")
        if set(feed.species_mol) != {p.phase_id for p in self.phases}:
            raise ValueError("Feed must explicitly name every candidate phase, including initially absent solids")
        sources, owned, audits = [], [], []
        mixture, before, after, result, completed = None, None, None, None, False
        try:
            for specification in self.phases:
                specification.mechanism_basis.require_state(feed.temperature_k, feed.pressure_pa)
                source = specification.factory()
                sources.append(source)
                expected_model = "ideal-gas" if specification.role == "gas" else "fixed-stoichiometry"
                if (not isinstance(source, self.ct.Solution) or source.thermo_model != expected_model
                        or source.n_selected_species != source.n_species
                        or np.any(source.charges != 0)
                        or (specification.role == "solid" and source.n_species != 1)):
                    raise ValueError("Supply a full neutral native ideal-gas or pure stoichiometric-solid phase")
                if any(source is earlier for earlier in sources[:-1]):
                    raise ValueError("Phase factories returned the same native object for different phases")
                if set(feed.species_mol[specification.phase_id])-set(source.species_names):
                    raise ValueError("Feed names a species absent from its declared phase")
                if specification.role == "gas" and math.fsum(feed.species_mol[specification.phase_id].values()) <= 0:
                    raise ValueError("This first multiphase level requires a positive initial gas inventory")
                copy, audit = (_private_native_phase(source, self.ct) if specification.role == "gas"
                               else _solid_copy(source, self.ct))
                owned.append(copy)
                audits.append(audit)
                old = self._source_fingerprints.setdefault(specification.phase_id, audit.source_fingerprint)
                if old != audit.source_fingerprint:
                    raise ValueError("A native phase definition changed without rebinding source evidence")
            weights = {}
            for phase in owned:
                for name in phase.element_names:
                    weight = phase.atomic_weight(name)
                    if name in weights and weights[name] != weight:
                        raise ValueError("Element atomic weights differ between phases")
                    weights[name] = weight
            mixture = self.ct.Mixture([(phase, 0.) for phase in owned])
            mixture.T, mixture.P = feed.temperature_k, feed.pressure_pa
            amounts = np.array([feed.species_mol[spec.phase_id].get(name, 0.)
                for spec, phase in zip(self.phases, owned, strict=True) for name in phase.species_names])
            mixture.species_moles = amounts/1000.
            elements = tuple(sorted(weights, key=mixture.element_index))
            keys = tuple((spec.phase_id, name) for spec, phase in zip(self.phases, owned, strict=True)
                         for name in phase.species_names)
            sizes = [phase.n_species for phase in owned]
            atom_matrix = np.array([[mixture.n_atoms(k, mixture.element_index(e))
                for k in range(mixture.n_species)] for e in elements])
            for spec, phase in zip(self.phases, owned, strict=True):
                if not phase.min_temp <= mixture.T <= phase.max_temp:
                    raise ValueError("Feed exceeds the native species-fit temperature intersection")
            before = _snapshot(mixture, elements)
            mixture.equilibrate(constraint, solver=settings.solver, rtol=settings.relative_tolerance,
                max_steps=settings.maximum_steps, max_iter=settings.maximum_iterations,
                estimate_equil=settings.estimate_equilibrium, log_level=0)
            completed = True
            after = _snapshot(mixture, elements)
            for spec, phase, audit in zip(self.phases, owned, audits, strict=True):
                spec.mechanism_basis.require_state(after.temperature_k, after.pressure_pa)
                if not phase.min_temp <= after.temperature_k <= phase.max_temp:
                    raise ValueError("Equilibrium exceeds native species-fit temperature bounds")
                if _phase_fingerprint(phase, include_reactions=True) != audit.owned_fingerprint:
                    raise ValueError("Native owned phase definition changed during equilibrium")
            chemical = _chemical_audit(before, after, atom_matrix, elements, self.phases,
                                        sizes, self.tolerances, self.ct.gas_constant)
            mass_error, element_error = after.mass_kg-before.mass_kg, after.element_mol-before.element_mol
            heat = after.enthalpy_j-before.enthalpy_j if constraint == "TP" else 0.
            work = before.pressure_pa*(after.volume_m3-before.volume_m3)
            energy_error = after.internal_energy_j-before.internal_energy_j+work-heat
            enthalpy_error = after.enthalpy_j-before.enthalpy_j-heat
            t = self.tolerances
            energy_limit = t.energy_absolute_j+t.relative*max(abs(before.enthalpy_j), abs(after.enthalpy_j))
            absent_stable = all(value >= -t.chemical_potential_over_rt
                                for value in chemical.absent_solid_affinity_over_rt.values())
            gates = {
                "finite nonnegative native amounts": bool(np.all(np.isfinite(after.species_mol))
                    and np.all(after.species_mol >= 0) and np.all(np.isfinite(after.chemical_potentials_j_mol))),
                "populated gas phase retained": bool(after.phase_mol[next(i for i, p in enumerate(self.phases)
                    if p.role == "gas")] > chemical.active_amount_threshold_mol),
                "absolute SI feed retained": bool(np.max(abs(before.species_mol-amounts))
                    <= t.element_absolute_mol+t.relative*float(amounts.sum())),
                "elemental mol and mass conservation": bool(abs(mass_error) <= t.mass_absolute_kg+t.relative*before.mass_kg
                    and np.all(abs(element_error) <= t.element_absolute_mol+t.relative*abs(before.element_mol))),
                "TP or HP constraint": bool(math.isclose(after.pressure_pa, before.pressure_pa, rel_tol=1e-10)
                    and (constraint == "HP" or math.isclose(after.temperature_k, before.temperature_k, rel_tol=1e-10))),
                "enthalpy and first-law ledger": bool(max(abs(energy_error), abs(enthalpy_error)) <= energy_limit),
                "populated chemical-potential stationarity": bool(chemical.element_matrix_rank
                    == int((before.element_mol > t.element_absolute_mol).sum())
                    and chemical.maximum_populated_affinity_over_rt <= t.chemical_potential_over_rt),
                "absent feasible pure-solid stability": absent_stable,
                "TP Gibbs decrease or HP entropy increase": bool(
                    after.gibbs_energy_j <= before.gibbs_energy_j+energy_limit if constraint == "TP"
                    else after.entropy_j_k >= before.entropy_j_k-energy_limit/after.temperature_k),
            }
            result = _issue_equilibrium_result(phases=self.phases, feed=feed, constraint=constraint,
                settings=settings, tolerances=t, species_keys=keys, element_names=elements,
                initial=before, final=after, heat_into_j=heat, pressure_volume_work_out_j=work,
                energy_balance_residual_j=energy_error, enthalpy_constraint_residual_j=enthalpy_error,
                mass_residual_kg=mass_error, element_residual_mol=element_error,
                chemical_audit=chemical, native_mixture=mixture, source_phases=tuple(sources),
                owned_phases=tuple(owned), phase_copy_audits=tuple(audits), gates=gates,
                accepted=all(gates.values()))
            if require_accepted and not result.accepted:
                raise ValueError("Native equilibrium failed independent host acceptance: "+
                                 ", ".join(name for name, passed in gates.items() if not passed))
            return result
        except Exception as error:
            raise MultiphaseEquilibriumError(str(error), native_mixture=mixture, source_phases=sources,
                owned_phases=owned, phase_copy_audits=audits, initial=before, final=after,
                native_solver_completed=completed, result=result) from error
