"""Bounded native-mixture mass-quality inversion diagnostics.

Phase compositions and properties remain owned by CoolProp. This module only
retains the result of changing the quality coordinate from mole to mass basis.
"""

from dataclasses import dataclass, field
from math import isclose

from ..core import finite
from .mixture_phase_partition import MixturePhasePartition


@dataclass(frozen=True, slots=True)
class MixtureMassQualityInverse:
    """One selected PQ/TQ branch; sampled monotonicity is not global uniqueness."""

    partition: MixturePhasePartition
    target_vapor_mass_fraction: float
    native_mole_quality_bounds: tuple[float, float]
    mass_quality_absolute_tolerance: float
    branch_evidence_id: str
    fixed_coordinate: str
    fixed_coordinate_value: float
    evaluations: tuple[MixturePhasePartition, ...] = field(repr=False)
    native_root: object = field(repr=False)
    mass_quality_residual: float
    monotonicity_is_sampled_only: bool = True
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def _payload(self):
        root_values = tuple((name, getattr(self.native_root, name, None)) for name in (
            "converged", "iterations", "function_calls", "flag", "root"))
        return (id(self.partition), self.target_vapor_mass_fraction,
                self.native_mole_quality_bounds, self.mass_quality_absolute_tolerance,
                self.branch_evidence_id, self.fixed_coordinate, self.fixed_coordinate_value,
                tuple(id(p) for p in self.evaluations), id(self.native_root), root_values,
                self.mass_quality_residual, self.monotonicity_is_sampled_only)

    def __post_init__(self):
        target = finite(self.target_vapor_mass_fraction, "target vapor mass fraction")
        tolerance = finite(self.mass_quality_absolute_tolerance,
                           "mass-quality absolute tolerance", positive=True)
        residual = finite(self.mass_quality_residual, "mass-quality residual")
        bounds = tuple(finite(q, "native mole-quality bound")
                       for q in self.native_mole_quality_bounds)
        if (not 0. <= target <= 1. or not 0. < tolerance < 1.
                or len(bounds) != 2 or not 0. <= bounds[0] < bounds[1] <= 1.
                or self.fixed_coordinate not in {"pressure_pa", "temperature_k"}
                or not isinstance(self.branch_evidence_id, str)
                or not self.branch_evidence_id.strip()
                or self.monotonicity_is_sampled_only is not True):
            raise ValueError("Retain an explicit bounded native mass-quality branch")
        fixed = finite(self.fixed_coordinate_value, self.fixed_coordinate, positive=True)
        evaluations = tuple(self.evaluations)
        if (type(self.partition) is not MixturePhasePartition or not evaluations
                or evaluations[-1] is not self.partition
                or any(type(p) is not MixturePhasePartition for p in evaluations)
                or getattr(self.native_root, "converged", False) is not True):
            raise ValueError("Retain the converged native partition and actual evaluations")
        provider = self.partition.provider
        for part in evaluations:
            part.require_current()
            coordinate = getattr(part.state, self.fixed_coordinate)
            if (part.provider is not provider
                    or not bounds[0] <= part.vapor_mole_fraction <= bounds[1]
                    or not isclose(coordinate, fixed, rel_tol=1e-8, abs_tol=1e-8)):
                raise ValueError("Native evaluations differ from the selected quality branch")
        actual = self.partition.vapor_mass_fraction-target
        if abs(actual) > tolerance or actual != residual:
            raise ValueError("The native partition exceeds its mass-quality residual budget")
        object.__setattr__(self, "native_mole_quality_bounds", bounds)
        object.__setattr__(self, "evaluations", evaluations)
        if self._seal and self._payload() != self._seal:
            raise ValueError("Retained mass-quality inverse diagnostics changed")
        if not self._seal:
            object.__setattr__(self, "_seal", self._payload())

    @property
    def state(self):
        """Native state keeps mole quality; use partition for derived mass quality."""
        self.require_current()
        return self.partition.state

    def require_current(self):
        self.__post_init__()
        return self
