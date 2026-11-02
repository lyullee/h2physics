"""Product-custody receipt from an owner-issued finite LH2 transfer run."""

from dataclasses import dataclass, field

import numpy as np

from ..core import Origin, TimeSeries, finite, immutable_array
from .result_provenance import recorded_content_sha256


@dataclass(frozen=True, slots=True)
class FiniteTransferProductDelivery:
    trace: object
    receiver_node_id: str
    receiver_source_id: str
    clock_id: str
    product_boundary_evidence_id: str
    fluid_basis_id: str
    edge_time_s: np.ndarray
    cumulative_received_mass_kg: np.ndarray
    interval_received_mass_kg: np.ndarray
    interval_average_mass_rate_kg_s: np.ndarray
    rate_series: TimeSeries
    _seal: str = field(repr=False)

    def require_current(self):
        from .lh2dt_finite_transfer import FiniteTransferTrace

        if type(self.trace) is not FiniteTransferTrace:
            raise TypeError("Retain the exact owner-issued finite transfer trace")
        self.trace.require_current()
        receiver = self.trace.bodies[-1]
        if (receiver.node_id != self.receiver_node_id
                or receiver.source_id != self.receiver_source_id
                or self.clock_id != self.trace.clock_id
                or self.fluid_basis_id != self.trace._owner.bridge.basis.reference_id):
            raise ValueError("Original product receiver, source, clock or fluid basis changed")
        edges = np.asarray((self.trace.requested_start_s,
                            *(point.time_s for point in self.trace.points)), dtype=float)
        cumulative = np.asarray((0., *(point.receiver_net_received_kg for point in self.trace.points)), dtype=float)
        intervals = np.diff(cumulative)
        rates = intervals/np.diff(edges)
        if (not np.array_equal(self.edge_time_s, edges)
                or not np.array_equal(self.cumulative_received_mass_kg, cumulative)
                or not np.array_equal(self.interval_received_mass_kg, intervals)
                or not np.array_equal(self.interval_average_mass_rate_kg_s, rates)
                or self.rate_series.clock_id != self.clock_id
                or self.rate_series.source_id != self.receiver_source_id + ":" + self.product_boundary_evidence_id
                or self.rate_series.basis_ids != (self.fluid_basis_id,)
                or not np.array_equal(self.rate_series.time_s, edges[1:])
                or not np.array_equal(self.rate_series.values[:, 0], rates)):
            raise ValueError("Product receipt no longer equals the accepted receiver mass ledger")
        content = recorded_content_sha256((
            id(self.trace), self.receiver_node_id, self.receiver_source_id, self.clock_id,
            self.product_boundary_evidence_id, self.fluid_basis_id, self.edge_time_s,
            self.cumulative_received_mass_kg, self.interval_received_mass_kg,
            self.interval_average_mass_rate_kg_s, self.rate_series))
        if content != self._seal:
            raise ValueError("Product delivery receipt changed after issue")
        return self


def product_delivery_from_finite_transfer(
    trace, *, receiver_node_id: str, product_boundary_evidence_id: str,
) -> FiniteTransferProductDelivery:
    """Project internal receiver accumulation as a declared custody delivery.

    The named receiver must be the final finite inventory node. Caller evidence
    declares that node as the product custody boundary. Only nondecreasing net
    received mass is admitted; reverse-flow/return periods require a separately
    modeled product-accounting contract and are never clipped into delivery.
    """
    from .lh2dt_finite_transfer import FiniteTransferTrace

    if type(trace) is not FiniteTransferTrace:
        raise TypeError("Use the original issued finite transfer trace")
    trace.require_current()
    if not isinstance(receiver_node_id, str) or not receiver_node_id.strip():
        raise ValueError("Declare the receiver node at the product custody boundary")
    if not isinstance(product_boundary_evidence_id, str) or not product_boundary_evidence_id.strip():
        raise ValueError("Evidence is required to designate the receiver as a product boundary")
    if not trace.points or trace.bodies[-1].node_id != receiver_node_id:
        raise ValueError("Selected product boundary must be the trace's terminal receiver inventory")
    edges = np.asarray((trace.requested_start_s, *(point.time_s for point in trace.points),), dtype=float)
    cumulative = np.asarray((0., *(point.receiver_net_received_kg for point in trace.points)), dtype=float)
    if (np.any(np.diff(edges) <= 0) or edges[-1] != trace.actual_end_s
            or not np.all(np.isfinite(cumulative))):
        raise ValueError("Finite transfer ledger must cover exact increasing physical-second support")
    intervals = np.diff(cumulative)
    if np.any(intervals < 0.):
        raise ValueError("Net reverse transfer cannot be relabeled as product delivery")
    if not np.any(intervals > 0.):
        raise ValueError("The declared receiver boundary has no positive product delivery")
    rates = intervals/np.diff(edges)
    receiver = trace.bodies[-1]
    basis_id = trace._owner.bridge.basis.reference_id
    source_id = receiver.source_id + ":" + product_boundary_evidence_id
    series = TimeSeries(
        edges[1:], rates[:, None], ("receiver-product-mass-rate",), ("kg/s",),
        np.ones((len(rates), 1), dtype=bool), trace.clock_id, Origin.PREDICTED,
        source_id, ("interval_average_product_mass_rate",), (basis_id,))
    arrays = tuple(immutable_array(a, name=name) for a, name in zip(
        (edges, cumulative, intervals, rates),
        ("edge_time_s", "cumulative_received_mass_kg", "interval_received_mass_kg",
         "interval_average_mass_rate_kg_s"), strict=True))
    result = FiniteTransferProductDelivery(
        trace, receiver.node_id, receiver.source_id, trace.clock_id,
        product_boundary_evidence_id, basis_id, *arrays, series, "")
    from dataclasses import replace
    seal = recorded_content_sha256((id(trace), receiver.node_id, receiver.source_id,
        trace.clock_id, product_boundary_evidence_id, basis_id, *arrays, series))
    result = replace(result, _seal=seal)
    trace.require_current()
    return result.require_current()
