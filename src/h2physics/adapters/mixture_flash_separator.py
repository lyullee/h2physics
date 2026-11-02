"""Finite equilibrium mixture separation through the native PQ branch inverse.

Actual equilibrium phase properties come from the same native flash's phase
keyed outputs, rather than a second flash with the unchanged total composition.
"""

from dataclasses import dataclass, field
from math import fsum, isclose

from ..core import finite
from ..thermo.coolprop_mixture import CoolPropMixtureProperties, MixtureThermoState
from ..thermo.mixture_phase_partition import MixturePartitionInverse, MixturePhaseAmounts, MixturePhasePartition


_PENDING_SEPARATION_ISSUERS = set()


def _issue_separation_token():
    token = object()
    _PENDING_SEPARATION_ISSUERS.add(token)
    return token


class MixtureFlashSeparationError(RuntimeError):
    def __init__(self, cause, properties, upstream_state, inverse=None, amounts=None,
                 phase_energy_j=None, enthalpy_residual_j=None):
        super().__init__(str(cause))
        self.cause = cause
        self.properties = properties
        self.upstream_state = upstream_state
        self.inverse = inverse
        self.amounts = amounts
        self.phase_energy_j = phase_energy_j
        self.enthalpy_residual_j = enthalpy_residual_j


@dataclass(frozen=True, slots=True)
class MixtureFlashSeparation:
    upstream_state: MixtureThermoState
    inverse: object
    amounts: object
    component_mass_residuals_kg: tuple
    total_enthalpy_residual_j: float
    equilibrium_throttle_evidence_id: str
    negligible_kinetic_potential_evidence_id: str
    component_mass_absolute_tolerance_kg: float
    enthalpy_absolute_tolerance_j: float
    _issuer_token: object = field(repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SEPARATION_ISSUERS:
            raise TypeError("Create mixture separation receipts through an admitted native PH run")
        _PENDING_SEPARATION_ISSUERS.remove(self._issuer_token)
        if (type(self.upstream_state) is not MixtureThermoState
                or type(self.inverse) is not MixturePartitionInverse
                or type(self.amounts) is not MixturePhaseAmounts):
            raise TypeError("Retain the original upstream state, native PH inverse and finite phase amounts")
        partition = self.inverse.partition
        if type(partition) is not MixturePhasePartition or self.amounts.partition is not partition:
            raise ValueError("Mixture separation must retain one exact native phase partition")
        partition.__post_init__()
        self.amounts.__post_init__()
        provider = partition.provider
        provider.basis.require_compatible(self.upstream_state.basis)
        self.upstream_state.__post_init__()
        for evidence in (self.equilibrium_throttle_evidence_id,
                         self.negligible_kinetic_potential_evidence_id,
                         self.inverse.branch_evidence_id):
            if not isinstance(evidence, str) or not evidence.strip():
                raise ValueError("Mixture separation retains explicit branch and process evidence")
        if partition.state.phase != "two_phase":
            raise ValueError("Native downstream packet lost its admitted two-phase basis")
        if (self.upstream_state.pressure_pa <= partition.state.pressure_pa
                or not isclose(self.inverse.target_enthalpy_j_kg,
                               self.upstream_state.enthalpy_j_kg, rel_tol=1e-12, abs_tol=1e-9)):
            raise ValueError("Native PH inverse no longer matches the declared lower-pressure upstream state")
        if partition.liquid_enthalpy_j_kg is None or partition.vapor_enthalpy_j_kg is None:
            raise ValueError("Both native phase enthalpies are required to admit a finite split")
        mass = finite(self.amounts.total_mass_kg, "separated finite mass", positive=True)
        mass_budget = finite(self.component_mass_absolute_tolerance_kg,
                             "component mass budget", positive=True)
        energy_budget = finite(self.enthalpy_absolute_tolerance_j,
                               "total enthalpy budget", positive=True)
        molar_mass = fsum(z*m for z, m in zip(provider.mole_fractions,
            provider.coolprop_molar_masses_kg_mol, strict=True))
        residuals = tuple(mass*z*m/molar_mass-liquid-vapor
            for z, m, liquid, vapor in zip(provider.mole_fractions,
                provider.coolprop_molar_masses_kg_mol, self.amounts.liquid_component_mass_kg,
                self.amounts.vapor_component_mass_kg, strict=True))
        phase_energy = fsum((
            fsum(self.amounts.liquid_component_mass_kg)*partition.liquid_enthalpy_j_kg,
            fsum(self.amounts.vapor_component_mass_kg)*partition.vapor_enthalpy_j_kg,
        ))
        enthalpy_residual = mass*self.upstream_state.enthalpy_j_kg-phase_energy
        native_phase_residual = mass*partition.state.enthalpy_j_kg-phase_energy
        retained_residuals = tuple(finite(value, "component mass residual")
                                   for value in self.component_mass_residuals_kg)
        if (len(retained_residuals) != len(residuals)
                or any(not isclose(observed, expected, rel_tol=1e-12, abs_tol=1e-15)
                       for observed, expected in zip(retained_residuals, residuals, strict=True))
                or not isclose(finite(self.total_enthalpy_residual_j, "enthalpy residual"),
                               enthalpy_residual, rel_tol=1e-12, abs_tol=1e-9)
                or any(abs(value) > mass_budget for value in residuals)
                or abs(enthalpy_residual) > energy_budget
                or abs(native_phase_residual) > energy_budget):
            raise ValueError("Mixture separation summaries do not reproduce native component and enthalpy ledgers")
        object.__setattr__(self, "component_mass_residuals_kg", retained_residuals)
        object.__setattr__(self, "component_mass_absolute_tolerance_kg", mass_budget)
        object.__setattr__(self, "enthalpy_absolute_tolerance_j", energy_budget)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        partition = self.inverse.partition
        provider = partition.provider
        return (
            id(self.upstream_state), repr(self.upstream_state), id(self.inverse), repr(self.inverse),
            id(self.amounts), repr(self.amounts), id(partition), id(partition.provider),
            id(partition._provider_token), provider.composition_sha256, provider.basis,
            tuple(provider.species), tuple(provider.mole_fractions),
            tuple(provider.coolprop_molar_masses_kg_mol), self.component_mass_residuals_kg,
            self.total_enthalpy_residual_j, self.equilibrium_throttle_evidence_id,
            self.negligible_kinetic_potential_evidence_id,
            self.component_mass_absolute_tolerance_kg, self.enthalpy_absolute_tolerance_j,
        )

    def require_current(self):
        if not self._seal or self._fingerprint() != self._seal:
            raise ValueError("Mixture separation receipt changed after native admission")
        self.inverse.partition.__post_init__()
        self.amounts.__post_init__()
        return self


def separate_equilibrium_mixture(properties, upstream_state, *, total_mass_kg,
                                 downstream_pressure_pa, quality_bounds,
                                 component_mole_balance_tolerance,
                                 component_mass_absolute_tolerance_kg,
                                 enthalpy_absolute_tolerance_j,
                                 inverse_enthalpy_absolute_tolerance_j_kg,
                                 quality_absolute_tolerance, branch_evidence_id,
                                 equilibrium_throttle_evidence_id,
                                 negligible_kinetic_potential_evidence_id,
                                 upstream_state_relative_tolerance=1e-10):
    """Separate a finite same-composition mixture after an explicit PH throttle."""
    if type(properties) is not CoolPropMixtureProperties or type(upstream_state) is not MixtureThermoState:
        raise TypeError("Use the native fixed-composition provider and its typed upstream state")
    properties.basis.require_compatible(upstream_state.basis)
    upstream_state.__post_init__()
    for identity in (equilibrium_throttle_evidence_id, negligible_kinetic_potential_evidence_id):
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("Declare equilibrium throttling and neglected mechanical-energy evidence")
    mass = finite(total_mass_kg, "total mass", positive=True)
    mass_budget = finite(component_mass_absolute_tolerance_kg, "component mass budget", positive=True)
    energy_budget = finite(enthalpy_absolute_tolerance_j, "total enthalpy budget", positive=True)
    pressure = finite(downstream_pressure_pa, "downstream pressure", positive=True)
    if pressure >= upstream_state.pressure_pa:
        raise ValueError("Equilibrium separator requires an explicitly lower downstream pressure")
    state_tolerance = finite(upstream_state_relative_tolerance, "upstream reconstruction relative tolerance", positive=True)
    if upstream_state.phase == "two_phase":
        reconstructed = properties.phase_partition_pq(upstream_state.pressure_pa,
            upstream_state.vapor_mole_fraction,
            component_mole_balance_tolerance=component_mole_balance_tolerance).state
    else:
        reconstructed = properties.state_pt(upstream_state.pressure_pa, upstream_state.temperature_k)
    if reconstructed.phase != upstream_state.phase:
        raise ValueError("Upstream state phase differs from its native reconstruction")
    for name in ("pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg",
                 "internal_energy_j_kg", "entropy_j_kg_k"):
        if not isclose(getattr(upstream_state, name), getattr(reconstructed, name),
                       rel_tol=state_tolerance, abs_tol=1e-10):
            raise ValueError("Upstream mixture state differs from the immutable provider reconstruction")
    inverse = properties.phase_partition_ph(pressure, upstream_state.enthalpy_j_kg,
        quality_bounds=quality_bounds, component_mole_balance_tolerance=component_mole_balance_tolerance,
        enthalpy_absolute_tolerance_j_kg=inverse_enthalpy_absolute_tolerance_j_kg,
        quality_absolute_tolerance=quality_absolute_tolerance, branch_evidence_id=branch_evidence_id)
    amounts = phase_energy = residual = None
    try:
        return _complete_separation(properties, upstream_state, inverse, mass, mass_budget,
            energy_budget, equilibrium_throttle_evidence_id, negligible_kinetic_potential_evidence_id)
    except MixtureFlashSeparationError:
        raise
    except Exception as cause:
        raise MixtureFlashSeparationError(cause, properties, upstream_state, inverse,
                                         amounts, phase_energy, residual) from cause


def _complete_separation(properties, upstream_state, inverse, mass, mass_budget,
                         energy_budget, equilibrium_throttle_evidence_id,
                         negligible_kinetic_potential_evidence_id):
    partition = inverse.partition
    amounts = partition.split_mass(mass)
    overall_molar_mass = fsum(z*m for z, m in zip(properties.mole_fractions,
        properties.coolprop_molar_masses_kg_mol, strict=True))
    residuals = tuple(mass*z*m/overall_molar_mass-liquid-vapor
        for z, m, liquid, vapor in zip(properties.mole_fractions,
            properties.coolprop_molar_masses_kg_mol, amounts.liquid_component_mass_kg,
            amounts.vapor_component_mass_kg, strict=True))
    for value in residuals:
        finite(value, "finite component mass residual")
    if any(abs(value) > mass_budget for value in residuals):
        cause = ValueError("Finite native phase separation exceeds component mass budgets")
        raise MixtureFlashSeparationError(cause, properties, upstream_state, inverse, amounts) from cause
    if partition.liquid_enthalpy_j_kg is None or partition.vapor_enthalpy_j_kg is None:
        cause = ValueError("Native equilibrium phase enthalpies are required")
        raise MixtureFlashSeparationError(cause, properties, upstream_state, inverse, amounts) from cause
    phase_energy = (fsum(amounts.liquid_component_mass_kg)*partition.liquid_enthalpy_j_kg
                    +fsum(amounts.vapor_component_mass_kg)*partition.vapor_enthalpy_j_kg)
    residual = mass*upstream_state.enthalpy_j_kg-phase_energy
    native_phase_residual = mass*partition.state.enthalpy_j_kg-phase_energy
    try:
        finite(phase_energy, "finite separated phase enthalpy")
        finite(residual, "finite isenthalpic residual")
        finite(native_phase_residual, "finite native phase enthalpy residual")
    except ValueError as cause:
        raise MixtureFlashSeparationError(cause, properties, upstream_state, inverse,
            amounts, phase_energy, residual) from cause
    if abs(residual) > energy_budget or abs(native_phase_residual) > energy_budget:
        cause = ValueError("Finite phase split exceeds its isenthalpic or native phase-weighted energy budget")
        raise MixtureFlashSeparationError(cause, properties, upstream_state, inverse,
            amounts, phase_energy, residual) from cause
    return MixtureFlashSeparation(upstream_state, inverse, amounts, residuals, residual,
        equilibrium_throttle_evidence_id, negligible_kinetic_potential_evidence_id,
        mass_budget, energy_budget, _issue_separation_token())
