"""Common-clock admission of original finite source, node and utility receipts.

Node accumulation rates remain caller-declared instantaneous inputs; matching
accepted times does not make them derivatives of the finite inventory solver.
"""

from dataclasses import dataclass, field
from math import fsum
from types import MappingProxyType

from ..facility_continuity import FacilityContinuityAudit, FacilityContinuityFrame
from .facility_protection import FiniteFacilitySource, ProtectedEquipmentRun
from .result_provenance import recorded_content_sha256
from .thermal_utilities import ThermalUtilityLedger


@dataclass(frozen=True, slots=True)
class FacilityOperationReceipt:
    finite_source: FiniteFacilitySource
    continuity_owner: FacilityContinuityAudit
    continuity_frames: tuple
    continuity_results: tuple
    utilities: ThermalUtilityLedger
    protection: ProtectedEquipmentRun | None
    evidence_id: str
    instantaneous_rate_evidence_id: str
    _signature: str

    def require_current(self):
        self.finite_source.require_current()
        self.utilities.require_current()
        if self.protection is not None:
            self.protection.require_current()
        _admit(self.finite_source, self.continuity_owner, self.continuity_frames,
               self.utilities, self.protection)
        if _signature(self) != self._signature:
            raise ValueError("Original common-clock operation declarations or results changed")
        for frame, retained in zip(self.continuity_frames, self.continuity_results, strict=True):
            if self.continuity_owner.audit(frame) != retained:
                raise ValueError("Original instantaneous node audit no longer reproduces")
        return self


def _signature(receipt):
    return recorded_content_sha256((
        id(receipt.finite_source), id(receipt.utilities), id(receipt.protection),
        receipt.continuity_owner.nodes, receipt.continuity_owner.tolerances,
        receipt.continuity_frames, receipt.continuity_results,
        receipt.evidence_id, receipt.instantaneous_rate_evidence_id,
    ))


def _admit(source, audit, frames, utilities, protection):
    if type(source) is not FiniteFacilitySource or type(audit) is not FacilityContinuityAudit:
        raise TypeError("Retain the original finite source and node-continuity auditor")
    source.require_current()
    if type(utilities) is not ThermalUtilityLedger:
        raise TypeError("Retain the original finite thermal utility ledger")
    utilities.require_current()
    run = source.run
    if not run.steps:
        raise ValueError("Common-clock operation requires an accepted finite trajectory")
    references = {inventory.basis.reference_id for inventory in run.initial_inventories.values()}
    for profile in utilities.profiles:
        window = profile.snapshot.window
        if (profile.source is not run or profile.snapshot.source is not run
                or window.clock_id != run.clock_id or window.start_s != run.start_time_s
                or window.end_s != run.steps[-1].time_s
                or profile.snapshot.energy_basis_id not in references):
            raise ValueError("Utility profile must retain this exact finite run, window and energy reference")
    samples = ((run.start_time_s, run.initial_equipment),
               *((step.time_s, step.equipment) for step in run.steps))
    if len(frames) != len(samples):
        raise ValueError("Supply node-continuity declarations for every accepted finite sample")
    for frame, (time, snapshot) in zip(frames, samples, strict=True):
        if (type(frame) is not FacilityContinuityFrame or frame.clock_id != run.clock_id
                or frame.time_s != time or len(frame.transfers) != len(snapshot.transfers)
                or any(a is not b for a, b in zip(frame.transfers, snapshot.transfers, strict=True))):
            raise ValueError("Node frames must retain exact accepted times and original equipment transfers")
        for node in audit.nodes:
            if node.node_id not in snapshot.node_states:
                raise ValueError("Continuity node is absent from the original finite equipment snapshot")
            node.basis.require_compatible(snapshot.node_states[node.node_id].basis)
    if protection is not None:
        if type(protection) is not ProtectedEquipmentRun or protection.native_run is not run:
            raise ValueError("Protection must retain this exact finite operation")
        protection.require_current()


class FacilityOperationAuditError(RuntimeError):
    """Retain completed continuity-frame audits when a later frame fails."""

    def __init__(self, cause, *, finite_source, continuity_owner, frames, utilities,
                 protection, failed_frame_index, completed_results):
        super().__init__("Facility operation continuity audit failed before receipt binding")
        self.cause = cause
        self.finite_source = finite_source
        self.continuity_owner = continuity_owner
        self.continuity_frames = tuple(frames)
        self.utilities = utilities
        self.protection = protection
        self.failed_frame_index = failed_frame_index
        self.failed_frame = self.continuity_frames[failed_frame_index]
        self.completed_frames = self.continuity_frames[:failed_frame_index]
        self.completed_results = tuple(completed_results)


def bind_facility_operation(finite_source, continuity_owner, continuity_frames, utilities, *,
                            protection=None, evidence_id, instantaneous_rate_evidence_id):
    """Join compatible receipts without solving a network or allocating more heat.

    Utilities must be extracted from this exact run. Generic external heat
    declarations are not admitted as if issued by the facility model. Every
    instantaneous external/storage rate remains covered by explicit caller
    evidence; integrated closure remains the finite-source owner's responsibility.
    """
    for value in (evidence_id, instantaneous_rate_evidence_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Declare common-operation and instantaneous-rate evidence")
    frames = tuple(continuity_frames)
    _admit(finite_source, continuity_owner, frames, utilities, protection)
    results = []
    for index, frame in enumerate(frames):
        try:
            results.append(continuity_owner.audit(frame))
        except Exception as cause:
            raise FacilityOperationAuditError(
                cause, finite_source=finite_source, continuity_owner=continuity_owner,
                frames=frames, utilities=utilities, protection=protection,
                failed_frame_index=index, completed_results=results,
            ) from cause
    results = tuple(results)
    receipt = FacilityOperationReceipt(
        finite_source, continuity_owner, frames, results, utilities, protection,
        evidence_id, instantaneous_rate_evidence_id, "",
    )
    from dataclasses import replace
    return replace(receipt, _signature=_signature(receipt)).require_current()


def _report_values(operation):
    operation.require_current()
    nodes = tuple(node.node_id for node in operation.continuity_owner.nodes)
    times = tuple(frame.time_s for frame in operation.continuity_frames)
    by_result = tuple({row.node_id: row for row in result.nodes}
                      for result in operation.continuity_results)
    if any(set(result) != set(nodes) for result in by_result):
        raise ValueError("Original continuity results do not retain the auditor node set")
    mass = {node: tuple(result[node].mass_residual_kg_s for result in by_result)
            for node in nodes}
    energy = {node: tuple(result[node].energy_residual_w for result in by_result)
              for node in nodes}
    component = tuple((result.time_s, component_id, residual)
                      for result in operation.continuity_results
                      for component_id, residual in result.component_energy_residual_w)
    return (times, mass, energy, component, dict(operation.utilities.quantities),
            operation.utilities.energy_residual_j)


@dataclass(frozen=True, slots=True)
class FacilityOperationReport:
    """Read-only process report composed from an admitted original operation."""

    operation: FacilityOperationReceipt = field(repr=False)
    time_s: tuple[float, ...]
    node_mass_residual_kg_s: object
    node_energy_residual_w: object
    component_energy_residual_w: tuple[tuple[float, str, float], ...]
    net_utility_quantities: object
    utility_energy_residual_j: float
    _seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "time_s", tuple(self.time_s))
        object.__setattr__(self, "node_mass_residual_kg_s", MappingProxyType(
            {key: tuple(value) for key, value in self.node_mass_residual_kg_s.items()}))
        object.__setattr__(self, "node_energy_residual_w", MappingProxyType(
            {key: tuple(value) for key, value in self.node_energy_residual_w.items()}))
        object.__setattr__(self, "component_energy_residual_w", tuple(self.component_energy_residual_w))
        object.__setattr__(self, "net_utility_quantities", MappingProxyType(dict(self.net_utility_quantities)))
        if type(self.operation) is not FacilityOperationReceipt:
            raise TypeError("Report must retain an admitted original facility operation")
        if _report_values(self.operation) != (
                self.time_s, dict(self.node_mass_residual_kg_s),
                dict(self.node_energy_residual_w), self.component_energy_residual_w,
                dict(self.net_utility_quantities), self.utility_energy_residual_j):
            raise ValueError("Report fields must reproduce from the retained original operation receipt")
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.operation), self.time_s, dict(self.node_mass_residual_kg_s),
            dict(self.node_energy_residual_w), self.component_energy_residual_w,
            dict(self.net_utility_quantities), self.utility_energy_residual_j,
        ))

    def require_current(self):
        if self._content() != self._seal:
            raise ValueError("Facility operation report content changed")
        if _report_values(self.operation) != (
                self.time_s, dict(self.node_mass_residual_kg_s),
                dict(self.node_energy_residual_w), self.component_energy_residual_w,
                dict(self.net_utility_quantities), self.utility_energy_residual_j):
            raise ValueError("Reported process series no longer matches its original operation")
        return self

    def node_residual_series(self, node_id: str):
        """Return one node's mass/energy residuals on the exact accepted clock.

        This accessor is intended for direct Python consumers that need one
        facility node without rebuilding a time alignment from separate maps.
        It performs no interpolation or balance recomputation.
        """
        self.require_current()
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Select a nonempty facility node identity")
        try:
            mass = self.node_mass_residual_kg_s[node_id]
            energy = self.node_energy_residual_w[node_id]
        except KeyError as exc:
            raise KeyError(f"Unknown reported facility node: {node_id}") from exc
        if len(mass) != len(self.time_s) or len(energy) != len(self.time_s):
            raise ValueError("Node residuals no longer share the report's accepted clock")
        return self.time_s, mass, energy


def report_facility_operation(operation):
    """Compose common-clock node/component residuals and net utilities for reporting.

    This is a view over retained receipts. It adds no source, cost, balance closure,
    process rates or physics beyond the admitted operation.
    """
    if type(operation) is not FacilityOperationReceipt:
        raise TypeError("Supply an admitted FacilityOperationReceipt")
    values = _report_values(operation)
    return FacilityOperationReport(operation, *values).require_current()


def _integrated_report_values(report):
    """Integrate sampled residual rates under an explicit linear-segment rule."""
    report.require_current()
    times = report.time_s
    if len(times) < 2 or any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("Residual integration requires at least two increasing accepted samples")
    widths = tuple(right-left for left, right in zip(times, times[1:]))

    def integrate(values):
        if len(values) != len(times):
            raise ValueError("Residual samples must span the complete accepted clock")
        return fsum(width*(left+right)*0.5
                    for width, left, right in zip(widths, values[:-1], values[1:], strict=True))

    node_mass = {node: integrate(report.node_mass_residual_kg_s[node])
                 for node in report.node_mass_residual_kg_s}
    node_energy = {node: integrate(report.node_energy_residual_w[node])
                   for node in report.node_energy_residual_w}
    component_rows = tuple(
        {component: residual for sample_time, component, residual
         in report.component_energy_residual_w if sample_time == time}
        for time in times
    )
    component_ids = tuple(sorted(component_rows[0]))
    if (any(len(row) != len(component_ids) or set(row) != set(component_ids)
            for row in component_rows)
            or any(len(row) != sum(1 for t, _, _ in report.component_energy_residual_w
                                   if t == time)
                   for row, time in zip(component_rows, times, strict=True))):
        raise ValueError("Component residual identities must be unique and stable at every sample")
    component_energy = {
        component: integrate(tuple(row[component] for row in component_rows))
        for component in component_ids
    }
    return node_mass, node_energy, component_energy


@dataclass(frozen=True, slots=True)
class FacilityOperationIntegratedResiduals:
    """Sampled residual integrals under piecewise-linear interpolation.

    These are quadrature diagnostics over reported instantaneous residuals;
    they are not native cumulative inventory changes or facility closure.
    """

    report: FacilityOperationReport = field(repr=False)
    node_mass_residual_kg: object
    node_energy_residual_j: object
    component_energy_residual_j: object
    quadrature: str = "piecewise-linear trapezoidal"
    _seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.report) is not FacilityOperationReport:
            raise TypeError("Integrated residuals must retain an original facility report")
        if self.quadrature != "piecewise-linear trapezoidal":
            raise ValueError("Declare the supported piecewise-linear trapezoidal quadrature")
        for name in ("node_mass_residual_kg", "node_energy_residual_j",
                     "component_energy_residual_j"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        expected = _integrated_report_values(self.report)
        actual = (dict(self.node_mass_residual_kg), dict(self.node_energy_residual_j),
                  dict(self.component_energy_residual_j))
        if actual != expected:
            raise ValueError("Integrated residual fields must reproduce from the retained report")
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.report), self.quadrature, dict(self.node_mass_residual_kg),
            dict(self.node_energy_residual_j), dict(self.component_energy_residual_j),
        ))

    def require_current(self):
        self.report.require_current()
        if self._content() != self._seal:
            raise ValueError("Integrated facility residual diagnostics changed")
        if (dict(self.node_mass_residual_kg), dict(self.node_energy_residual_j),
                dict(self.component_energy_residual_j)) != _integrated_report_values(self.report):
            raise ValueError("Integrated residual diagnostics no longer match their source report")
        return self


def integrate_facility_operation_residuals(report):
    """Integrate sampled node/component residual rates over an admitted report.

    The piecewise-linear trapezoidal rule is explicit. No inventory or energy
    state is reconstructed, and this diagnostic does not claim native closure.
    """
    if type(report) is not FacilityOperationReport:
        raise TypeError("Supply an admitted FacilityOperationReport")
    node_mass, node_energy, component_energy = _integrated_report_values(report)
    return FacilityOperationIntegratedResiduals(
        report, node_mass, node_energy, component_energy,
    ).require_current()
