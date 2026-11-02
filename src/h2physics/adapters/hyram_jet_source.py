"""Finite-window source projection from an admitted stationary HyRAM gas jet.

This adapter records a caller-selected steady interval as the shared Python
source type. It does not change, rescale, or re-run the native HyRAM solution.
"""

import math
from dataclasses import dataclass
from dataclasses import field as dataclass_field

import numpy as np

from ..core import immutable_array, Origin, ThermoState, finite
from ..mixtures import GasComposition
from ..sources import IntervalMassSource
from .hyram import HyRAMJetRun


@dataclass(frozen=True, slots=True)
class HyRAMFiniteSourceProjection:
    """Auditable link between one accepted steady jet and a finite source."""

    jet: HyRAMJetRun
    source: IntervalMassSource
    start_s: float
    end_s: float
    h2_rate_residual_kg_s: float
    upstream_enthalpy_rate_w: float
    projected_enthalpy_rate_w: float
    enthalpy_rate_residual_w: float
    mass_budget_kg_s: float
    enthalpy_budget_w: float
    accepted: bool
    _identity_bindings: tuple = dataclass_field(
        default=(), init=False, repr=False, compare=False,
    )
    _receipt_binding: tuple = dataclass_field(
        default=(), init=False, repr=False, compare=False,
    )

    def __post_init__(self):
        self.jet.require_current()
        self.source.require_current()
        if type(self.jet) is not HyRAMJetRun or type(self.source) is not IntervalMassSource:
            raise TypeError("Retain the actual admitted HyRAM jet and finite-source objects")
        if not self.jet.accepted:
            raise ValueError("A rejected native HyRAM jet cannot be projected")
        if self.source.location is not self.jet.location:
            raise ValueError("Finite source must retain the original HyRAM location object")
        start = finite(self.start_s, "finite-source start")
        end = finite(self.end_s, "finite-source end")
        if start >= end:
            raise ValueError("The projected source window must have positive duration")
        if (not isinstance(self.source.state, ThermoState)
                or self.source.state.basis != self.jet.upstream.basis):
            raise ValueError("Finite source state must use the admitted hydrogen property basis")
        for name in (
            "h2_rate_residual_kg_s", "upstream_enthalpy_rate_w",
            "projected_enthalpy_rate_w", "enthalpy_rate_residual_w",
        ):
            finite(getattr(self, name), name)
        if type(self.accepted) is not bool:
            raise TypeError("Finite-source acceptance must be a boolean gate result")
        if self.source.origin is Origin.UNRESOLVED or not self.source.evidence_id.strip():
            raise ValueError("Finite source must retain resolved origin and state evidence")
        if (self.source.edges_s[0] != start or self.source.edges_s[-1] != end
                or len(self.source.mass_kg) != 1):
            raise ValueError("The finite source must retain the declared single steady interval")
        expected_mass = self.jet.mass_flow_kg_s*(end-start)
        if not math.isclose(self.source.total_mass_kg, expected_mass, rel_tol=1e-12,
                            abs_tol=1e-14):
            raise ValueError("Finite source mass does not match the admitted HyRAM rate")
        if not math.isclose(self.source.mean_rates_kg_s[0], self.jet.mass_flow_kg_s,
                            rel_tol=1e-12, abs_tol=1e-14):
            raise ValueError("Finite source mean rate does not match the admitted HyRAM rate")
        expected_upstream_power = self.jet.mass_flow_kg_s*self.jet.upstream.enthalpy_j_kg
        source_rate = self.source.mean_rates_kg_s[0]
        expected_projection_power = source_rate*self.source.state.enthalpy_j_kg
        if (self.upstream_enthalpy_rate_w != expected_upstream_power
                or self.projected_enthalpy_rate_w != expected_projection_power
                or self.enthalpy_rate_residual_w != expected_projection_power-expected_upstream_power):
            raise ValueError("The enthalpy projection receipt is not reproducible")
        finite(self.mass_budget_kg_s, "HyRAM mass budget", positive=True)
        finite(self.enthalpy_budget_w, "enthalpy projection budget", positive=True)
        if (self.h2_rate_residual_kg_s != source_rate-self.jet.mass_flow_kg_s
                or not math.isclose(self.mass_budget_kg_s, self.jet.mass_budget_kg_s,
                                    rel_tol=0., abs_tol=0.)
                or self.accepted != (
                    abs(self.h2_rate_residual_kg_s) <= self.mass_budget_kg_s
                    and abs(self.enthalpy_rate_residual_w) <= self.enthalpy_budget_w
                )):
            raise ValueError("The finite-source acceptance gate is inconsistent")
        object.__setattr__(self, "start_s", start)
        object.__setattr__(self, "end_s", end)
        object.__setattr__(self, "_identity_bindings", (
            self.jet, self.jet.native, self.source, self.source.location,
            self.source.edges_s, self.source.mass_kg, self.source.state,
        ))
        object.__setattr__(self, "_receipt_binding", self._receipt_payload())

    def _receipt_payload(self):
        return (
            float(self.start_s), float(self.end_s),
            float(self.h2_rate_residual_kg_s),
            float(self.upstream_enthalpy_rate_w),
            float(self.projected_enthalpy_rate_w),
            float(self.enthalpy_rate_residual_w),
            float(self.mass_budget_kg_s), float(self.enthalpy_budget_w),
            self.accepted,
        )

    def require_current(self) -> "HyRAMFiniteSourceProjection":
        """Recheck the retained source, clock, and native snapshot after capture."""
        self.source.require_current()
        self.jet.require_current()
        self.jet_centreline_check()
        current = (
            self.jet, self.jet.native, self.source, self.source.location,
            self.source.edges_s, self.source.mass_kg, self.source.state,
        )
        if (not self._identity_bindings
                or any(value is not original for value, original in zip(
                    current, self._identity_bindings, strict=True,
                ))
                or self._receipt_payload() != self._receipt_binding):
            raise ValueError("HyRAM finite-source projection bindings or receipt changed")
        if not self.jet.accepted or self.source.location is not self.jet.location:
            raise ValueError("The captured native HyRAM source admission or location changed")
        duration = self.end_s-self.start_s
        source_rate = self.source.mean_rates_kg_s[0]
        rate_residual = source_rate-self.jet.mass_flow_kg_s
        if (self.source.edges_s[0] != self.start_s or self.source.edges_s[-1] != self.end_s
                or self.source.total_mass_kg != self.jet.mass_flow_kg_s*duration
                or self.h2_rate_residual_kg_s != rate_residual
                or abs(rate_residual) > self.mass_budget_kg_s):
            raise ValueError("The captured HyRAM finite-source projection was modified")
        if (self.upstream_enthalpy_rate_w
                != self.jet.mass_flow_kg_s*self.jet.upstream.enthalpy_j_kg
                or self.projected_enthalpy_rate_w
                != source_rate*self.source.state.enthalpy_j_kg
                or self.enthalpy_rate_residual_w
                != self.projected_enthalpy_rate_w-self.upstream_enthalpy_rate_w):
            raise ValueError("The captured HyRAM source energy ledger was modified")
        if (self.source.state.basis != self.jet.upstream.basis
                or self.source.location.clock_id != self.jet.location.clock_id):
            raise ValueError("The captured source property basis or clock changed")
        if (not math.isclose(self.mass_budget_kg_s, self.jet.mass_budget_kg_s,
                             rel_tol=0., abs_tol=0.)
                or self.accepted != (
                    abs(rate_residual) <= self.mass_budget_kg_s
                    and abs(self.enthalpy_rate_residual_w) <= self.enthalpy_budget_w
                )
                or self.source.origin is Origin.UNRESOLVED
                or not self.source.evidence_id.strip()):
            raise ValueError("The captured HyRAM finite-source gate or provenance changed")
        return self

    def jet_centreline_check(self) -> None:
        self.jet.require_current()
        current = np.c_[self.jet.native.S, self.jet.native.x, self.jet.native.y,
                        self.jet.native.Y_cl, self.jet.native.X_cl]
        if not np.array_equal(current, self.jet.centreline):
            raise ValueError("The native HyRAM centreline changed after admission")

    @property
    def total_enthalpy_projection_residual_j(self) -> float:
        return self.enthalpy_rate_residual_w*(self.end_s-self.start_s)

    def component_flow(self, composition: GasComposition):
        """Place the conserved HyRAM hydrogen flow in an explicit mixture basis.

        The source remains pure-H2 mass flow. ``GasComposition`` allocates the
        caller-declared accompanying gas components; no ambient entrainment is
        inferred from the jet profile or its centerline concentration.
        """
        self.require_current()
        if type(composition) is not GasComposition:
            raise TypeError("Supply an explicit gas composition and molar-mass basis")
        try:
            hydrogen_index = composition.species.index("H2")
        except ValueError as error:
            raise ValueError("Gas composition must include an explicit H2 species") from error
        mass_fractions = composition.mass_fractions
        hydrogen_fraction = float(mass_fractions[hydrogen_index])
        if hydrogen_fraction <= 0.:
            raise ValueError("Gas composition must assign a positive mass fraction to H2")
        total_rate = self.jet.mass_flow_kg_s/hydrogen_fraction
        component_rates = composition.component_mass_flows(total_rate)
        if not math.isclose(float(component_rates[hydrogen_index]), self.jet.mass_flow_kg_s,
                            rel_tol=1e-12, abs_tol=1e-14):
            raise ArithmeticError("Composition allocation failed to preserve the HyRAM H2 rate")
        return HyRAMComponentFlowProjection(
            projection=self,
            composition=composition,
            total_mixture_rate_kg_s=total_rate,
            component_mass_rates_kg_s=component_rates,
            hydrogen_component_index=hydrogen_index,
        )


@dataclass(frozen=True, slots=True)
class HyRAMComponentFlowProjection:
    """Component-flow allocation that preserves, and identifies, the H2 basis."""

    projection: HyRAMFiniteSourceProjection
    composition: GasComposition
    total_mixture_rate_kg_s: float
    component_mass_rates_kg_s: np.ndarray
    hydrogen_component_index: int

    def __post_init__(self):
        if type(self.projection) is not HyRAMFiniteSourceProjection:
            raise TypeError("Retain the admitted HyRAM source projection")
        self.projection.require_current()
        if type(self.composition) is not GasComposition:
            raise TypeError("Retain an explicit GasComposition")
        rates = np.array(self.component_mass_rates_kg_s, dtype=float, copy=True)
        total = finite(self.total_mixture_rate_kg_s, "total mixture rate", positive=True)
        index = self.hydrogen_component_index
        if (rates.shape != self.composition.mole_fractions.shape or not np.all(np.isfinite(rates))
                or np.any(rates < 0.) or type(index) is not int
                or not 0 <= index < len(rates)):
            raise ValueError("Component rates must align to the declared mixture species")
        h2_index = self.composition.species.index("H2")
        if index != h2_index:
            raise ValueError("Retain the exact H2 species index")
        expected = self.composition.component_mass_flows(total)
        if (not np.allclose(rates, expected, rtol=1e-12, atol=1e-14)
                or not math.isclose(float(rates[index]),
                                    self.projection.jet.mass_flow_kg_s,
                                    rel_tol=1e-12, abs_tol=1e-14)):
            raise ValueError("Mixture component allocation does not preserve the HyRAM H2 flow")
        rates = immutable_array(rates, name="rates")
        object.__setattr__(self, "total_mixture_rate_kg_s", total)
        object.__setattr__(self, "component_mass_rates_kg_s", rates)

    def require_current(self):
        self.projection.require_current()
        expected = self.composition.component_mass_flows(self.total_mixture_rate_kg_s)
        if (not np.array_equal(expected, self.component_mass_rates_kg_s)
                or not math.isclose(float(expected[self.hydrogen_component_index]),
                                    self.projection.jet.mass_flow_kg_s,
                                    rel_tol=1e-12, abs_tol=1e-14)):
            raise ValueError("The retained gas component-flow allocation changed")
        return self


class HyRAMFiniteSourceError(ValueError):
    """Raised when the native or caller-selected source boundary fails a gate."""

    def __init__(self, projection: HyRAMFiniteSourceProjection):
        self.projection = projection
        self.jet = projection.jet
        super().__init__("HyRAM finite-source projection failed its rate/enthalpy gate")


def project_hyram_jet_to_finite_source(
    jet: HyRAMJetRun,
    *,
    start_s: float,
    end_s: float,
    clock_id: str,
    source_state: ThermoState,
    source_state_evidence_id: str,
    origin: Origin,
    end_reason: str = "window_end",
    relative_enthalpy_tolerance: float = 1e-8,
    absolute_enthalpy_tolerance_w: float = 1e-6,
    require_accepted: bool = True,
) -> HyRAMFiniteSourceProjection:
    """Project an accepted stationary native leak over caller-declared time.

    The source state is caller supplied because a steady HyRAM solution does
    not establish a transient thermodynamic path. Its basis must match the
    upstream hydrogen basis. The enthalpy difference is exposed and gated;
    this function never adjusts the native flow or source state to close it.
    """
    if type(require_accepted) is not bool:
        raise TypeError("require_accepted must be an explicit bool")
    if not isinstance(jet, HyRAMJetRun):
        raise TypeError("Pass the actual HyRAMJetRun returned by run_hyram_gas_jet")
    if not jet.accepted:
        raise ValueError("A rejected native HyRAM jet cannot feed a finite-source projection")
    start, end = finite(start_s, "finite-source start"), finite(end_s, "finite-source end")
    if start >= end:
        raise ValueError("The projected time window must have positive duration")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("Declare the source clock identity")
    if clock_id != jet.location.clock_id:
        raise ValueError("The declared projection clock must match the HyRAM source clock")
    if not isinstance(source_state, ThermoState) or source_state.basis != jet.upstream.basis:
        raise ValueError("The projected state must use the HyRAM upstream hydrogen basis")
    if source_state.phase not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError("This steady high-pressure source projection requires a gas state")
    if not isinstance(source_state_evidence_id, str) or not source_state_evidence_id.strip():
        raise ValueError("Identify the evidence for the caller-selected source state")
    relative = finite(relative_enthalpy_tolerance, "relative enthalpy tolerance", positive=True)
    absolute = finite(absolute_enthalpy_tolerance_w, "absolute enthalpy tolerance", positive=True)
    if not isinstance(origin, Origin) or origin == Origin.UNRESOLVED:
        raise ValueError("Resolve the source origin explicitly")
    duration = end-start
    mass = jet.mass_flow_kg_s*duration
    source = IntervalMassSource(
        location=jet.location,
        edges_s=np.asarray([start, end]),
        mass_kg=np.asarray([mass]),
        state=source_state,
        origin=origin,
        evidence_id=source_state_evidence_id,
        end_reason=end_reason,
    )
    source_rate = source.mean_rates_kg_s[0]
    mass_residual = source_rate-jet.mass_flow_kg_s
    upstream_power = jet.mass_flow_kg_s*jet.upstream.enthalpy_j_kg
    projected_power = source_rate*source_state.enthalpy_j_kg
    residual_power = projected_power-upstream_power
    budget_power = absolute+relative*max(abs(upstream_power), abs(projected_power))
    budget_mass = jet.mass_budget_kg_s
    # The rate/enthalpy terms can originate from NumPy-backed native results;
    # normalize their combined gate to the exact public bool contract.
    accepted = bool(abs(mass_residual) <= budget_mass
                    and abs(residual_power) <= budget_power)
    result = HyRAMFiniteSourceProjection(
        jet=jet,
        source=source,
        start_s=start,
        end_s=end,
        h2_rate_residual_kg_s=mass_residual,
        upstream_enthalpy_rate_w=upstream_power,
        projected_enthalpy_rate_w=projected_power,
        enthalpy_rate_residual_w=residual_power,
        mass_budget_kg_s=budget_mass,
        enthalpy_budget_w=budget_power,
        accepted=accepted,
    )
    if require_accepted and not result.accepted:
        raise HyRAMFiniteSourceError(result)
    return result


__all__ = [
    "HyRAMFiniteSourceProjection",
    "HyRAMComponentFlowProjection",
    "HyRAMFiniteSourceError",
    "project_hyram_jet_to_finite_source",
]
