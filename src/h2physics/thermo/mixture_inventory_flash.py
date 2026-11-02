"""Bounded single-state V/U equilibrium flash on a native CoolProp PQ branch.

This resolves one fixed-composition equilibrium packet. It does not integrate a
separator, update stream inventories, or locate phase events. Pressure/quality
domains and branch seeds are explicit because a local nonlinear solve cannot
establish global uniqueness.
"""

from dataclasses import dataclass, field
from math import exp, fsum, isclose, log

import numpy as np
from scipy.optimize import least_squares

from ..core import finite
from ..mixtures import GasComposition
from .coolprop_mixture import CoolPropMixtureProperties
from .mixture_phase_partition import (
    MixtureInventoryStateAdmission,
    MixturePhaseAmounts,
    MixturePhasePartition,
)

_PENDING_FLASH_ISSUERS: set[object] = set()


def _issue_flash(**values):
    token = object()
    _PENDING_FLASH_ISSUERS.add(token)
    try:
        return TwoPhaseMixtureInventoryFlash(**values, _issuer=token)
    except Exception:
        _PENDING_FLASH_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class MixtureInventoryFlashSeedResult:
    """One bounded multi-start root outcome and its final native PQ packet."""

    seed_pressure_pa: float
    seed_vapor_mole_fraction: float
    converged: bool
    pressure_pa: float | None
    vapor_mole_fraction: float | None
    volume_residual_m3: float | None
    internal_energy_residual_j: float | None
    function_evaluations: int
    solver_status: int
    solver_message: str
    cost: float | None
    optimality: float | None
    partition: MixturePhasePartition | None = field(default=None, repr=False, compare=False)
    phase_amounts: MixturePhaseAmounts | None = field(default=None, repr=False, compare=False)
    failure_type: str | None = None

    def __post_init__(self):
        finite(self.seed_pressure_pa, "seed pressure", positive=True)
        finite(self.seed_vapor_mole_fraction, "seed vapor mole fraction")
        if not 0. < self.seed_vapor_mole_fraction < 1.:
            raise ValueError("Nonlinear solver seeds must be inside the open quality interval")
        if (isinstance(self.function_evaluations, bool)
                or not isinstance(self.function_evaluations, int)
                or self.function_evaluations < 0
                or isinstance(self.solver_status, bool)
                or not isinstance(self.solver_status, int)):
            raise ValueError("Retain native root solver evaluation and status integers")
        if not isinstance(self.solver_message, str) or not self.solver_message:
            raise ValueError("Retain the nonlinear solver message")
        if self.converged:
            if (self.failure_type is not None or self.partition is None
                    or type(self.partition) is not MixturePhasePartition
                    or self.phase_amounts is None
                    or type(self.phase_amounts) is not MixturePhaseAmounts
                    or self.phase_amounts.partition is not self.partition):
                raise ValueError("A converged seed must retain its native packet and phase amounts")
            self.partition.require_current()
            self.phase_amounts.__post_init__()
            for name in ("pressure_pa", "vapor_mole_fraction", "volume_residual_m3",
                         "internal_energy_residual_j", "cost", "optimality"):
                finite(getattr(self, name), name)
        else:
            if (self.partition is not None or self.phase_amounts is not None
                    or self.failure_type is None or not self.failure_type.strip()):
                raise ValueError("A failed seed retains only an explicit failure summary")
            for name in ("pressure_pa", "vapor_mole_fraction", "volume_residual_m3",
                         "internal_energy_residual_j", "cost", "optimality"):
                if getattr(self, name) is not None:
                    raise ValueError("Failed seeds cannot expose a partial root as an admitted state")


class MixtureInventoryFlashError(RuntimeError):
    """A bounded two-phase V/U solve failed or found multiple seed roots."""

    def __init__(self, status, message, seed_results):
        super().__init__(message)
        self.status = status
        self.seed_results = tuple(seed_results)


@dataclass(frozen=True, slots=True)
class TwoPhaseMixtureInventoryFlash:
    """One admitted fixed-volume/internal-energy two-phase equilibrium state.

    ``seed_unique_within_search`` means every caller-supplied start converged to
    the same root within declared clustering tolerances. It is not a proof that
    no other root exists elsewhere inside the pressure/quality rectangle.
    """

    provider: CoolPropMixtureProperties = field(repr=False, compare=False)
    admission: MixtureInventoryStateAdmission = field(repr=False, compare=False)
    component_moles: tuple[float, ...]
    target_volume_m3: float
    target_internal_energy_j: float
    pressure_bounds_pa: tuple[float, float]
    quality_bounds: tuple[float, float]
    seed_results: tuple[MixtureInventoryFlashSeedResult, ...]
    volume_absolute_tolerance_m3: float
    energy_absolute_tolerance_j: float
    component_mole_absolute_tolerance: float
    root_pressure_relative_tolerance: float
    root_quality_absolute_tolerance: float
    phase_mole_balance_tolerance: float
    branch_evidence_id: str
    monotonicity_is_sampled_only: bool
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_FLASH_ISSUERS:
            raise TypeError("Two-phase inventory flash results are issued by the bounded native solver")
        _PENDING_FLASH_ISSUERS.remove(self._issuer)
        if (type(self.provider) is not CoolPropMixtureProperties
                or type(self.admission) is not MixtureInventoryStateAdmission
                or self.admission.provider is not self.provider):
            raise TypeError("Retain the exact fixed-composition native provider and admitted inventory packet")
        self.admission.require_current()
        moles = tuple(finite(value, "component inventory moles") for value in self.component_moles)
        if moles != self.admission.total_component_moles:
            raise ValueError("Flash component inventory differs from its independently admitted packet")
        if (self.target_volume_m3 != self.admission.vessel_volume_m3
                or self.target_internal_energy_j != self.admission.target_internal_energy_j):
            raise ValueError("Flash targets differ from the independently admitted V/U packet")
        pressure_bounds = tuple(finite(value, "pressure bound", positive=True)
                                for value in self.pressure_bounds_pa)
        quality_bounds = tuple(finite(value, "quality bound") for value in self.quality_bounds)
        if (len(pressure_bounds) != 2 or pressure_bounds[0] >= pressure_bounds[1]
                or len(quality_bounds) != 2 or not 0. <= quality_bounds[0] < quality_bounds[1] <= 1.):
            raise ValueError("Flash needs ordered pressure and quality branch bounds")
        for name in ("target_volume_m3", "volume_absolute_tolerance_m3",
                     "energy_absolute_tolerance_j", "component_mole_absolute_tolerance",
                     "root_pressure_relative_tolerance", "root_quality_absolute_tolerance",
                     "phase_mole_balance_tolerance"):
            finite(getattr(self, name), name, positive=True)
        finite(self.target_internal_energy_j, "target internal energy")
        if (not isinstance(self.seed_results, tuple) or len(self.seed_results) < 2
                or any(type(item) is not MixtureInventoryFlashSeedResult for item in self.seed_results)
                or any(not item.converged for item in self.seed_results)):
            raise ValueError("An admitted result needs at least two successful branch-search seeds")
        root = self.admission.partition.state
        if (not pressure_bounds[0] <= root.pressure_pa <= pressure_bounds[1]
                or not quality_bounds[0] <= self.admission.partition.vapor_mole_fraction <= quality_bounds[1]
                or root.phase != "two_phase"):
            raise ValueError("The admitted packet is outside the declared two-phase branch domain")
        for candidate in self.seed_results:
            candidate.partition.require_current()
            if (not isclose(candidate.pressure_pa, root.pressure_pa,
                            rel_tol=self.root_pressure_relative_tolerance, abs_tol=0.)
                    or abs(candidate.vapor_mole_fraction
                           - self.admission.partition.vapor_mole_fraction)
                       > self.root_quality_absolute_tolerance):
                raise ValueError("Seed results do not identify one common native flash root")
            if (abs(candidate.volume_residual_m3) > self.volume_absolute_tolerance_m3
                    or abs(candidate.internal_energy_residual_j) > self.energy_absolute_tolerance_j):
                raise ValueError("A converged seed failed the declared V/U closure budgets")
        if self.monotonicity_is_sampled_only is not True:
            raise ValueError("The result must disclose that bounded multi-start search is not a global uniqueness proof")
        if not isinstance(self.branch_evidence_id, str) or not self.branch_evidence_id.strip():
            raise ValueError("Declare branch/domain evidence for the selected two-phase region")
        object.__setattr__(self, "component_moles", moles)
        object.__setattr__(self, "pressure_bounds_pa", pressure_bounds)
        object.__setattr__(self, "quality_bounds", quality_bounds)
        object.__setattr__(self, "seed_results", tuple(self.seed_results))
        object.__setattr__(self, "_seal", self._payload())

    @property
    def partition(self):
        self.require_current()
        return self.admission.partition

    @property
    def phase_amounts(self):
        self.require_current()
        return self.admission.phase_amounts

    @property
    def pressure_pa(self):
        return self.partition.state.pressure_pa

    @property
    def temperature_k(self):
        return self.partition.state.temperature_k

    @property
    def volume_residual_m3(self):
        self.require_current()
        return self.admission.volume_residual_m3

    @property
    def internal_energy_residual_j(self):
        self.require_current()
        return self.admission.internal_energy_residual_j

    @property
    def seed_unique_within_search(self):
        self.require_current()
        return True

    @property
    def total_native_evaluations(self):
        self.require_current()
        return sum(item.function_evaluations for item in self.seed_results)

    def _payload(self):
        return (
            id(self.provider), id(self.admission), self.admission._payload(),
            self.component_moles, self.target_volume_m3, self.target_internal_energy_j,
            self.pressure_bounds_pa, self.quality_bounds,
            tuple((item.seed_pressure_pa, item.seed_vapor_mole_fraction,
                   item.converged, item.pressure_pa, item.vapor_mole_fraction,
                   item.volume_residual_m3, item.internal_energy_residual_j,
                   item.function_evaluations, item.solver_status, item.solver_message,
                   item.cost, item.optimality, id(item.partition), id(item.phase_amounts))
                  for item in self.seed_results),
            self.volume_absolute_tolerance_m3, self.energy_absolute_tolerance_j,
            self.component_mole_absolute_tolerance, self.root_pressure_relative_tolerance,
            self.root_quality_absolute_tolerance, self.phase_mole_balance_tolerance,
            self.branch_evidence_id, self.monotonicity_is_sampled_only,
        )

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Two-phase mixture inventory flash changed after solver admission")
        self.admission.require_current()
        for result in self.seed_results:
            result.partition.require_current()
            result.phase_amounts.__post_init__()
        return self


def flash_two_phase_inventory_vu(
    provider: CoolPropMixtureProperties,
    component_moles,
    *,
    vessel_volume_m3: float,
    internal_energy_j: float,
    pressure_bounds_pa,
    quality_bounds=(0.0, 1.0),
    initial_guesses,
    volume_absolute_tolerance_m3: float,
    energy_absolute_tolerance_j: float,
    component_mole_absolute_tolerance: float,
    phase_mole_balance_tolerance: float,
    branch_evidence_id: str,
    root_pressure_relative_tolerance: float = 1e-7,
    root_quality_absolute_tolerance: float = 1e-8,
    maximum_function_evaluations: int = 200,
):
    """Resolve one bounded two-phase equilibrium from fixed V, total U and N_i.

    The native CoolProp PQ flash supplies each candidate phase packet. Two or
    more caller-selected starts must converge to the same root. This is a local
    bounded branch resolver only; it does not advance inventories or prove
    global root uniqueness.
    """
    if type(provider) is not CoolPropMixtureProperties:
        raise TypeError("Use the native fixed-composition CoolProp mixture provider")
    moles = tuple(finite(value, "component inventory moles") for value in component_moles)
    total_moles = fsum(moles)
    if (len(moles) != len(provider.species) or total_moles <= 0.
            or any(value < 0. for value in moles)):
        raise ValueError("Component mole inventory must be nonnegative and follow provider species order")
    mole_tolerance = finite(component_mole_absolute_tolerance,
                            "component mole tolerance", positive=True)
    if any(abs(amount - total_moles*fraction) > mole_tolerance
           for amount, fraction in zip(moles, provider.mole_fractions, strict=True)):
        raise ValueError("Fixed-composition provider does not match the target component inventory")
    target_volume = finite(vessel_volume_m3, "vessel volume", positive=True)
    target_energy = finite(internal_energy_j, "target internal energy")
    volume_tolerance = finite(volume_absolute_tolerance_m3,
                              "volume absolute tolerance", positive=True)
    energy_tolerance = finite(energy_absolute_tolerance_j,
                              "energy absolute tolerance", positive=True)
    phase_tolerance = finite(phase_mole_balance_tolerance,
                             "native phase mole-balance tolerance", positive=True)
    pressure_bounds = tuple(finite(value, "pressure bound", positive=True)
                            for value in pressure_bounds_pa)
    quality_bounds = tuple(finite(value, "quality bound") for value in quality_bounds)
    if len(pressure_bounds) != 2 or pressure_bounds[0] >= pressure_bounds[1]:
        raise ValueError("Pressure branch bounds must be an increasing positive pair")
    if (len(quality_bounds) != 2 or not 0. <= quality_bounds[0] < quality_bounds[1] <= 1.):
        raise ValueError("Quality branch bounds must be an increasing interval in [0, 1]")
    if not isinstance(branch_evidence_id, str) or not branch_evidence_id.strip():
        raise ValueError("Declare why the pressure/quality branch bounds apply")
    pressure_merge = finite(root_pressure_relative_tolerance,
                            "root pressure merge tolerance", positive=True)
    quality_merge = finite(root_quality_absolute_tolerance,
                           "root quality merge tolerance", positive=True)
    if pressure_merge > 1. or quality_merge > 1.:
        raise ValueError("Root clustering tolerances must not exceed their normalized coordinate range")
    if (isinstance(maximum_function_evaluations, bool)
            or not isinstance(maximum_function_evaluations, int)
            or maximum_function_evaluations < 10):
        raise ValueError("Nonlinear flash needs at least ten integer function evaluations per seed")
    guesses = tuple(tuple(finite(value, "initial root guess") for value in guess)
                    for guess in initial_guesses)
    if len(guesses) < 2 or any(len(guess) != 2 for guess in guesses):
        raise ValueError("Supply at least two (pressure, vapor mole fraction) branch seeds")
    if len(set(guesses)) != len(guesses):
        raise ValueError("Branch-search seeds must be distinct")
    p_lo, p_hi = pressure_bounds
    q_lo, q_hi = quality_bounds
    for pressure, quality in guesses:
        if not p_lo < pressure < p_hi or not q_lo < quality < q_hi:
            raise ValueError("Each branch seed must lie strictly inside its pressure and quality bounds")

    attempts = []
    candidate_values = []
    for seed_pressure, seed_quality in guesses:
        evaluations = {}

        def evaluate(x):
            key = (float(x[0]), float(x[1]))
            if key not in evaluations:
                pressure = exp(key[0])
                partition = provider.phase_partition_pq(
                    pressure, key[1],
                    component_mole_balance_tolerance=phase_tolerance,
                )
                if partition.state.phase != "two_phase":
                    raise ValueError("Native PQ evaluation left the declared two-phase branch")
                amounts = partition.split_moles(total_moles)
                volume = fsum(amounts.phase_volumes_m3)
                energy = amounts.total_internal_energy_j
                evaluations[key] = (partition, amounts, volume-target_volume,
                                    energy-target_energy)
            return evaluations[key]

        try:
            initial = np.asarray((log(seed_pressure), seed_quality), dtype=float)
            lower = np.asarray((log(p_lo), q_lo), dtype=float)
            upper = np.asarray((log(p_hi), q_hi), dtype=float)

            def residual(x):
                _, _, volume_error, energy_error = evaluate(x)
                return np.asarray((volume_error/volume_tolerance,
                                   energy_error/energy_tolerance), dtype=float)

            solved = least_squares(
                residual, initial, bounds=(lower, upper), method="trf",
                x_scale=np.asarray((1.0, max(q_hi-q_lo, 1e-3))),
                ftol=1e-11, xtol=1e-11, gtol=1e-11,
                max_nfev=maximum_function_evaluations,
            )
            pressure = exp(float(solved.x[0]))
            quality = float(solved.x[1])
            partition, amounts, volume_error, energy_error = evaluate(solved.x)
            success = bool(solved.success and np.all(np.isfinite(solved.x))
                           and abs(volume_error) <= volume_tolerance
                           and abs(energy_error) <= energy_tolerance)
            candidate = MixtureInventoryFlashSeedResult(
                seed_pressure_pa=seed_pressure,
                seed_vapor_mole_fraction=seed_quality,
                converged=success,
                pressure_pa=pressure if success else None,
                vapor_mole_fraction=quality if success else None,
                volume_residual_m3=volume_error if success else None,
                internal_energy_residual_j=energy_error if success else None,
                function_evaluations=int(solved.nfev),
                solver_status=int(solved.status),
                solver_message=str(solved.message),
                cost=float(solved.cost) if success else None,
                optimality=float(solved.optimality) if success else None,
                partition=partition if success else None,
                phase_amounts=amounts if success else None,
                failure_type=None if success else "nonconverged_or_closure_outside_budget",
            )
        except Exception as error:
            candidate = MixtureInventoryFlashSeedResult(
                seed_pressure_pa=seed_pressure,
                seed_vapor_mole_fraction=seed_quality,
                converged=False,
                pressure_pa=None,
                vapor_mole_fraction=None,
                volume_residual_m3=None,
                internal_energy_residual_j=None,
                function_evaluations=len(evaluations),
                solver_status=-1,
                solver_message=f"{type(error).__name__}: {error}",
                cost=None,
                optimality=None,
                failure_type=type(error).__name__,
            )
        attempts.append(candidate)
        if candidate.converged:
            candidate_values.append(candidate)

    if len(candidate_values) != len(guesses):
        raise MixtureInventoryFlashError(
            "seed_failure", "Every declared branch seed must converge and close V/U", attempts,
        )
    reference = candidate_values[0]
    for other in candidate_values[1:]:
        same_pressure = isclose(other.pressure_pa, reference.pressure_pa,
                                rel_tol=pressure_merge, abs_tol=0.)
        same_quality = abs(other.vapor_mole_fraction-reference.vapor_mole_fraction) <= quality_merge
        if not same_pressure or not same_quality:
            raise MixtureInventoryFlashError(
                "multiple_roots",
                "Declared branch seeds converged to distinct V/U roots inside the search bounds",
                attempts,
            )
    partition = reference.partition
    admission = MixtureInventoryStateAdmission(
        provider=provider,
        partition=partition,
        total_component_moles=moles,
        target_internal_energy_j=target_energy,
        vessel_volume_m3=target_volume,
        component_mole_tolerance=mole_tolerance,
        volume_absolute_tolerance_m3=volume_tolerance,
        energy_absolute_tolerance_j=energy_tolerance,
        evidence_id=branch_evidence_id,
    )
    return _issue_flash(
        provider=provider,
        admission=admission,
        component_moles=moles,
        target_volume_m3=target_volume,
        target_internal_energy_j=target_energy,
        pressure_bounds_pa=pressure_bounds,
        quality_bounds=quality_bounds,
        seed_results=tuple(attempts),
        volume_absolute_tolerance_m3=volume_tolerance,
        energy_absolute_tolerance_j=energy_tolerance,
        component_mole_absolute_tolerance=mole_tolerance,
        root_pressure_relative_tolerance=pressure_merge,
        root_quality_absolute_tolerance=quality_merge,
        phase_mole_balance_tolerance=phase_tolerance,
        branch_evidence_id=branch_evidence_id,
        monotonicity_is_sampled_only=True,
    )


__all__ = [
    "MixtureInventoryFlashError",
    "MixtureInventoryFlashSeedResult",
    "TwoPhaseMixtureInventoryFlash",
    "flash_two_phase_inventory_vu",
]
