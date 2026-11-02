"""Explicit finite-operation/source/preferred-dispersion scenario assembly.

Existing scenario scheduling and domain adapters retain their responsibilities.
No accident opening, deposited fraction or source thermodynamic state is inferred.
"""

from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from ..dispersion import DispersionExecution, DispersionScenario, HydrogenReleaseFamily
from ..scenarios import OperationalScenario, ScenarioNode, ScenarioOutput
from .facility_protection import FiniteFacilitySource
from .hyram_jet_source import HyRAMFiniteSourceProjection


class FacilityChainAdmissionError(ValueError):
    def __init__(self, message, *, execution, finite_source, projection=None):
        super().__init__(message)
        self.result = execution
        self.finite_source = finite_source
        self.projection = projection


@dataclass(frozen=True, slots=True)
class FacilityDispersionHandoff:
    finite_source: FiniteFacilitySource
    execution: object
    gas_source_projection: HyRAMFiniteSourceProjection | None
    evidence_id: str
    family: HydrogenReleaseFamily
    mass_absolute_tolerance_kg: float
    energy_absolute_tolerance_j: float
    _seal: tuple = field(init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Facility handoff needs an explicit coupling evidence identity")
        if type(self.finite_source) is not FiniteFacilitySource or type(self.execution) is not DispersionExecution:
            raise TypeError("Retain actual finite source and preferred dispersion receipts")
        if self.family is not self.execution.family:
            raise ValueError("Handoff family must retain the exact selected execution family")
        if (self.family is HydrogenReleaseFamily.HIGH_PRESSURE_GAS
                and type(self.gas_source_projection) is not HyRAMFiniteSourceProjection):
            raise TypeError("Gas handoff requires its original finite HyRAM projection")
        if (self.family is HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN
                and self.gas_source_projection is not None):
            raise ValueError("LH2 handoff cannot retain a gas-origin source projection")
        finite(self.mass_absolute_tolerance_kg, "source mass budget", positive=True)
        finite(self.energy_absolute_tolerance_j, "source energy budget", positive=True)
        object.__setattr__(self, "_seal", self._content())
        self.require_current()

    def _content(self):
        return (id(self.finite_source), id(self.execution), id(self.execution.result),
                id(self.gas_source_projection), self.evidence_id, self.family,
                self.mass_absolute_tolerance_kg, self.energy_absolute_tolerance_j,
                self.execution.accepted, self.execution.provider_id,
                self.execution.source_evidence_ids)

    def require_current(self):
        if self._content() != self._seal:
            raise ValueError("Facility handoff identity, evidence or tolerance changed")
        if type(self.execution) is not DispersionExecution:
            raise TypeError("Retain an actual preferred dispersion execution")
        self.execution.require_current()
        if self.execution.family is not self.family or self.execution.accepted is not True:
            raise ValueError("Facility handoff lost its admitted provider family or acceptance")
        self.finite_source.require_current()
        if any(abs(value) > self.energy_absolute_tolerance_j
               for value in self.finite_source.energy_projection().residual_j):
            raise ValueError("Source enthalpy projection exceeds its retained per-bin budget")
        if self.gas_source_projection is not None:
            self.gas_source_projection.require_current()
            projected, source = self.gas_source_projection, self.finite_source.source
            if projected.accepted is not True:
                raise ValueError("Facility handoff cannot promote a rejected HyRAM source projection")
            if (projected.jet is not self.execution.result
                    or projected.source.location != source.location
                    or projected.start_s != source.edges_s[0]
                    or projected.end_s != source.edges_s[-1]):
                raise ValueError("Gas source window or exact native execution changed")
            expected = np.diff(source.edges_s)*projected.jet.mass_flow_kg_s
            if np.any(np.abs(expected-source.mass_kg) > self.mass_absolute_tolerance_kg):
                raise ValueError("Gas source mass differs from the retained per-bin budget")
            source.state.basis.require_compatible(projected.source.state.basis)
            if np.any(np.abs(source.mass_kg*(source.state.enthalpy_j_kg
                    -projected.source.state.enthalpy_j_kg)) > self.energy_absolute_tolerance_j):
                raise ValueError("Gas source enthalpy differs from the retained per-bin budget")
        else:
            self.execution.result.boundary.require_current()
            if self.execution.result.boundary.mass_source is not self.finite_source.source:
                raise ValueError("LH2 handoff lost its exact admitted source")
        return self


@dataclass(frozen=True, slots=True)
class FacilityAccidentChain:
    """Prepared existing-operation graph with an explicit source admission path."""

    scenario: OperationalScenario
    family: HydrogenReleaseFamily
    evidence_id: str
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.scenario) is not OperationalScenario:
            raise TypeError("A facility accident chain must retain an OperationalScenario")
        if not isinstance(self.family, HydrogenReleaseFamily):
            raise TypeError("Declare the selected hydrogen release family")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare the facility chain source-to-field evidence")
        expected_nodes = ("finite-operation", "finite-source", "preferred-dispersion")
        if self.scenario.execution_order != expected_nodes:
            raise ValueError("Facility chain graph must contain the ordered source-to-dispersion path")
        if any(node.evidence_id != self.evidence_id for node in self.scenario.nodes):
            raise ValueError("Facility chain node evidence must retain the chain evidence identity")
        object.__setattr__(self, "_seal", (id(self.scenario), self.family, self.evidence_id,
            self.scenario.scenario_id, self.scenario.execution_order,
            tuple((id(node), id(node.inputs), node.node_id, node.evidence_id, id(node.operation),
                   tuple((name, type(binding), getattr(binding, "node_id", None),
                          id(getattr(binding, "value", None)), id(getattr(binding, "select", None)))
                         for name, binding in node.inputs.items()))
                  for node in self.scenario.nodes)))

    def require_current(self):
        """Reject a chain whose declared scenario or coupling identity changed."""
        if not self._seal:
            raise ValueError("Facility accident chain has no original prepared configuration")
        current = (id(self.scenario), self.family, self.evidence_id,
            self.scenario.scenario_id, self.scenario.execution_order,
            tuple((id(node), id(node.inputs), node.node_id, node.evidence_id, id(node.operation),
                   tuple((name, type(binding), getattr(binding, "node_id", None),
                          id(getattr(binding, "value", None)), id(getattr(binding, "select", None)))
                         for name, binding in node.inputs.items()))
                  for node in self.scenario.nodes))
        if current != self._seal:
            raise ValueError("Facility accident chain scenario or coupling identity changed")
        return self

    def run(self):
        self.require_current()
        result = self.scenario.run()
        self.require_current()
        result.require_current()
        outputs = result.results
        finite_run = outputs["finite-operation"]
        source = outputs["finite-source"]
        handoff = outputs["preferred-dispersion"]
        if (type(source) is not FiniteFacilitySource or source.run is not finite_run
                or type(handoff) is not FacilityDispersionHandoff
                or handoff.finite_source is not source):
            raise ValueError("Facility chain outputs lost their exact operation/source/handoff lineage")
        handoff.require_current()
        if handoff.family is not self.family or handoff.evidence_id != self.evidence_id:
            raise ValueError("Facility chain final handoff changed its declared family/evidence")
        return result


def assemble_facility_accident_chain(*, scenario_id, finite_operation,
                                     source_binding, dispersion_request,
                                     release_family, evidence_id,
                                     mass_absolute_tolerance_kg,
                                     energy_absolute_tolerance_j,
                                     gas_projection=None):
    """Prepare lazy finite run -> admitted source -> preferred engine execution.

    ``source_binding(run)`` must return a ``FiniteFacilitySource`` retaining that
    exact run. ``dispersion_request(binding)`` returns the caller's complete
    preferred ``DispersionScenario``. LH2 requires its exact vapor source; liquid
    release to pool deposition is outside this graph. Gas additionally requires
    ``gas_projection(execution, binding)`` to return the admitted stationary HyRAM
    finite-window projection for comparison against the operation's source bins.
    """
    family = HydrogenReleaseFamily(release_family)
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Declare the facility source-to-field coupling evidence")
    for operation in (finite_operation, source_binding, dispersion_request):
        if not callable(operation):
            raise TypeError("Supply explicit existing finite/source/dispersion operations")
    if family is HydrogenReleaseFamily.HIGH_PRESSURE_GAS and not callable(gas_projection):
        raise TypeError("Gas operation needs an explicit admitted HyRAM window projection")
    if family is HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN and gas_projection is not None:
        raise TypeError("An LH2-origin chain cannot accept the gas-only HyRAM projection callback")
    mass_budget = finite(mass_absolute_tolerance_kg, "source mass budget", positive=True)
    energy_budget = finite(energy_absolute_tolerance_j, "source energy budget", positive=True)

    def bind_source(run):
        binding = source_binding(run)
        if type(binding) is not FiniteFacilitySource or binding.run is not run:
            raise ValueError("Source binding must retain this exact finite operation result")
        binding.require_current()
        projection = binding.energy_projection()
        if any(abs(value) > energy_budget for value in projection.residual_j):
            raise ValueError("Finite-source state projection exceeds its per-bin enthalpy budget")
        return binding

    def execute_dispersion(binding):
        binding.require_current()
        request = dispersion_request(binding)
        if type(request) is not DispersionScenario or request.family is not family:
            raise ValueError("Declare the matching preferred dispersion scenario")
        if family is HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN:
            if request.inputs.get("source") is not binding.source:
                raise ValueError("LH2 dispersion must retain this exact admitted vapor source")
        execution = request.run()
        if execution.accepted is not True:
            raise FacilityChainAdmissionError(
                "Rejected preferred dispersion cannot complete the facility chain",
                execution=execution, finite_source=binding,
            )
        binding.require_current()
        projected = None
        if family is HydrogenReleaseFamily.HIGH_PRESSURE_GAS:
            try:
                projected = gas_projection(execution, binding)
            except Exception as cause:
                raise FacilityChainAdmissionError(
                    "Caller gas projection failed after preferred dispersion returned",
                    execution=execution, finite_source=binding,
                ) from cause
            if (type(projected) is not HyRAMFiniteSourceProjection
                    or projected.jet is not execution.result):
                raise FacilityChainAdmissionError(
                    "Retain this exact admitted HyRAM execution and source projection",
                    execution=execution, finite_source=binding, projection=projected,
                )
            projected.require_current()
            if projected.accepted is not True:
                raise FacilityChainAdmissionError(
                    "Rejected HyRAM finite-source projection cannot complete the facility chain",
                    execution=execution, finite_source=binding, projection=projected,
                )
            source = binding.source
            if (projected.source.location != source.location
                    or projected.start_s != source.edges_s[0]
                    or projected.end_s != source.edges_s[-1]):
                raise FacilityChainAdmissionError(
                    "HyRAM and facility sources differ in clock, location or window",
                    execution=execution, finite_source=binding, projection=projected,
                )
            expected = np.diff(source.edges_s)*projected.jet.mass_flow_kg_s
            if np.any(np.abs(expected-source.mass_kg) > mass_budget):
                raise FacilityChainAdmissionError(
                    "Stationary HyRAM mass flow differs from finite facility source bins",
                    execution=execution, finite_source=binding, projection=projected,
                )
            source.state.basis.require_compatible(projected.source.state.basis)
            if np.any(np.abs(source.mass_kg*(source.state.enthalpy_j_kg
                    -projected.source.state.enthalpy_j_kg)) > energy_budget):
                raise FacilityChainAdmissionError(
                    "HyRAM and facility source enthalpy projections differ",
                    execution=execution, finite_source=binding, projection=projected,
                )
        return FacilityDispersionHandoff(
            binding, execution, projected, evidence_id, family, mass_budget, energy_budget,
        ).require_current()

    scenario = OperationalScenario(scenario_id, (
        ScenarioNode("finite-operation", finite_operation, {}, evidence_id),
        ScenarioNode("finite-source", bind_source,
                     {"run": ScenarioOutput("finite-operation")}, evidence_id),
        ScenarioNode("preferred-dispersion", execute_dispersion,
                     {"binding": ScenarioOutput("finite-source")}, evidence_id),
    ))
    return FacilityAccidentChain(scenario, family, evidence_id)
