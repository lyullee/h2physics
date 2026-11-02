"""Finite H2 source projection from a completed adsorption-vessel trace."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import fsum, isclose

from ..core import Origin, ThermoState, finite
from ..release import SourceLocation
from ..sources import IntervalMassSource


_PENDING: set[object] = set()


def _projection(trace, location, state, *, clock_alignment_evidence_id,
                state_projection_evidence_id, energy_tolerance_j,
                relative_tolerance):
    from ..storage.adsorption_dynamics import AdsorptionDynamicsTrace

    if type(trace) is not AdsorptionDynamicsTrace:
        raise TypeError("Use an owner-issued AdsorptionDynamicsTrace")
    if type(location) is not SourceLocation or type(state) is not ThermoState:
        raise TypeError("Supply an explicit source location and representative H2 state")
    trace.require_current()
    inputs = trace.inputs
    gas = inputs.vessel.gas
    gas.require_current()
    if trace.status != "completed":
        raise ValueError("Only a completed adsorption window can become a finite source")
    if tuple(gas.species) != ("H2",):
        raise ValueError("This source projection admits only the exact declared H2 gas species")
    if location.source_id != inputs.run_id:
        raise ValueError("Source location must preserve the original adsorption run identity")
    state.basis.require_compatible(gas.property_basis)
    if (state.phase not in {"gas", "supercritical", "supercritical_gas"}
            or state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Representative source state must be gaseous H2 on the vessel property basis")
    for name, value in (("clock alignment evidence", clock_alignment_evidence_id),
                        ("state projection evidence", state_projection_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {name}")
    absolute = finite(energy_tolerance_j, "source enthalpy projection tolerance", positive=True)
    relative = finite(relative_tolerance, "relative source enthalpy tolerance", positive=True)
    if relative > 1e-2:
        raise ValueError("Relative source enthalpy tolerance cannot exceed 1e-2")
    times = tuple(finite(value, "accepted adsorption time") for value in trace.time_s)
    if len(times) < 2 or any(right <= left for left, right in zip(times[:-1], times[1:])):
        raise ValueError("Completed adsorption source needs an increasing accepted time history")
    cumulative = tuple(finite(value, "cumulative adsorption outlet")
                       for value in trace.cumulative_outlet_mol)
    if len(cumulative) != len(times) or abs(cumulative[0]) > 1e-12:
        raise ValueError("Outlet mole ledger must align with the accepted time history and start at zero")
    bins_mol = tuple(right-left for left, right in zip(cumulative[:-1], cumulative[1:]))
    if any(value < -1e-12 for value in bins_mol):
        raise ValueError("Accepted H2 outlet ledger cannot reverse direction")
    bins_mol = tuple(max(0., value) for value in bins_mol)
    molar_mass = finite(gas.mean_molar_mass_kg_mol, "declared H2 molar mass", positive=True)
    mass_bins = tuple(value*molar_mass for value in bins_mol)
    mass = fsum(mass_bins)
    if mass <= 0.:
        raise ValueError("Completed adsorption trace contains no positive H2 outlet batch")
    native_energy = finite(trace.outlet_enthalpy_j[-1], "cumulative native outlet enthalpy")
    if abs(finite(trace.outlet_enthalpy_j[0], "initial outlet enthalpy")) > absolute:
        raise ValueError("Native outlet enthalpy ledger must start at zero")
    projected_energy = mass*state.enthalpy_j_kg
    residual = projected_energy-native_energy
    budget = absolute+relative*max(abs(projected_energy), abs(native_energy), 1.)
    if abs(residual) > budget:
        raise ValueError("Representative H2 state does not conserve native integrated outlet enthalpy")
    if not isclose(cumulative[-1], fsum(bins_mol), rel_tol=relative, abs_tol=1e-12):
        raise ValueError("Accepted source bins do not close to the adsorption outlet mole ledger")
    source = IntervalMassSource(
        location, times, mass_bins, state, Origin.PREDICTED,
        ":".join((inputs.run_id, inputs.rate_evidence_id, inputs.energy_evidence_id,
                   clock_alignment_evidence_id.strip(), state_projection_evidence_id.strip())),
        "window_end",
    )
    return source, mass, native_energy, projected_energy, residual, budget


@dataclass(frozen=True, slots=True)
class AdsorptionDynamicsFiniteSource:
    """Owner-sealed mapping of accepted H2 outlet moles to interval mass bins."""

    trace: object = field(repr=False, compare=False)
    source: IntervalMassSource
    location: SourceLocation = field(repr=False, compare=False)
    representative_state: ThermoState = field(repr=False, compare=False)
    clock_alignment_evidence_id: str
    state_projection_evidence_id: str
    energy_tolerance_j: float
    relative_tolerance: float
    transferred_mass_kg: float
    native_outlet_enthalpy_j: float
    projected_outlet_enthalpy_j: float
    enthalpy_residual_j: float
    enthalpy_budget_j: float
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        expected = _PENDING.pop(self._issuer, None)
        actual = (id(self.trace), id(self.source), id(self.location), id(self.representative_state),
                  self.clock_alignment_evidence_id, self.state_projection_evidence_id,
                  self.energy_tolerance_j, self.relative_tolerance, self.transferred_mass_kg,
                  self.native_outlet_enthalpy_j, self.projected_outlet_enthalpy_j,
                  self.enthalpy_residual_j, self.enthalpy_budget_j)
        if expected is None or expected != actual:
            raise TypeError("Use bind_adsorption_dynamics_to_finite_source to issue a receipt")
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "_seal", actual)

    def require_current(self):
        projection = _projection(
            self.trace, self.location, self.representative_state,
            clock_alignment_evidence_id=self.clock_alignment_evidence_id,
            state_projection_evidence_id=self.state_projection_evidence_id,
            energy_tolerance_j=self.energy_tolerance_j,
            relative_tolerance=self.relative_tolerance,
        )
        source, mass, native_energy, projected_energy, residual, budget = projection
        actual = (id(self.trace), id(self.source), id(self.location), id(self.representative_state),
                  self.clock_alignment_evidence_id, self.state_projection_evidence_id,
                  self.energy_tolerance_j, self.relative_tolerance, self.transferred_mass_kg,
                  self.native_outlet_enthalpy_j, self.projected_outlet_enthalpy_j,
                  self.enthalpy_residual_j, self.enthalpy_budget_j)
        self.source.require_current()
        if (actual != self._seal or self.source.location is not self.location
                or self.source.state is not self.representative_state
                or self.source.origin != Origin.PREDICTED or self.source.end_reason != "window_end"
                or source.edges_s.tolist() != self.source.edges_s.tolist()
                or source.mass_kg.tolist() != self.source.mass_kg.tolist()
                or source.evidence_id != self.source.evidence_id
                or mass != self.transferred_mass_kg or native_energy != self.native_outlet_enthalpy_j
                or projected_energy != self.projected_outlet_enthalpy_j
                or residual != self.enthalpy_residual_j or budget != self.enthalpy_budget_j):
            raise ValueError("Adsorption-to-source projection or retained owner changed")
        return self


def bind_adsorption_dynamics_to_finite_source(
    trace,
    *,
    location: SourceLocation,
    representative_state: ThermoState,
    clock_alignment_evidence_id: str,
    state_projection_evidence_id: str,
    energy_tolerance_j: float = 1e-6,
    relative_tolerance: float = 1e-8,
) -> AdsorptionDynamicsFiniteSource:
    """Project completed single-component adsorption outflow onto finite H2 bins.

    Accepted cumulative outlet moles define interval masses exactly. The caller
    supplies clock alignment and one representative outlet state; the integrated
    enthalpy discrepancy must fit the explicitly declared tolerance. No bed
    breakthrough, valve, downstream pressure-control or dispersion model is added.
    """
    values = _projection(
        trace, location, representative_state,
        clock_alignment_evidence_id=clock_alignment_evidence_id,
        state_projection_evidence_id=state_projection_evidence_id,
        energy_tolerance_j=energy_tolerance_j,
        relative_tolerance=relative_tolerance,
    )
    source, mass, native_energy, projected_energy, residual, budget = values
    token = object()
    _PENDING.add(token)
    record = AdsorptionDynamicsFiniteSource(
        trace, source, location, representative_state,
        clock_alignment_evidence_id.strip(), state_projection_evidence_id.strip(),
        finite(energy_tolerance_j, "source enthalpy projection tolerance", positive=True),
        finite(relative_tolerance, "relative source enthalpy tolerance", positive=True),
        mass, native_energy, projected_energy, residual, budget, _issuer=token,
    )
    return record.require_current()


__all__ = ["AdsorptionDynamicsFiniteSource", "bind_adsorption_dynamics_to_finite_source"]
