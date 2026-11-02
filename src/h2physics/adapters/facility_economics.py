"""Bind original facility operation and physical-window tariff accounting.

The physical projection supplies its own explicitly identified product role.
An accident release source is never interpreted as manufactured or sold H2.
"""

from dataclasses import dataclass

from .facility_operation import FacilityOperationReceipt
from .physical_economics import (
    WindowUtilityCost,
    price_projection_window,
    require_validated_projection,
)
from .result_provenance import recorded_content_sha256


def _admit(operation, projection):
    if type(operation) is not FacilityOperationReceipt:
        raise TypeError("Retain an admitted common-clock FacilityOperationReceipt")
    operation.require_current()
    require_validated_projection(projection)
    run = operation.finite_source.run
    if projection.source is not run and projection.source is not operation:
        raise ValueError("Economic projection must retain this exact operation or its issuing finite run")
    window = projection.window
    if (window.clock_id != run.clock_id or window.start_s != run.start_time_s
            or window.end_s != run.steps[-1].time_s):
        raise ValueError("Economic and physical operation windows or clocks differ")
    product = window.selected_product_basis
    if projection.quantities.get(product) is None:
        raise ValueError("An explicitly audited product boundary is required")
    # Recovered heat has already been allocated by the original utility owner.
    # A projected raw/gross duty must not be billed as a remaining external duty.
    snapshot = projection.source_binding.cached_snapshot
    for quantity, amount in operation.utilities.quantities.items():
        if quantity not in projection.quantities:
            continue
        if projection.quantities[quantity] != amount:
            raise ValueError("Projected thermal costs differ from original net utility quantities")
        expected = operation.utilities.quantity_boundaries[quantity]
        observed = snapshot.boundaries[quantity]
        if (set(observed.billing_components) != set(expected.billing_components)
                or observed.basis_id != expected.basis_id):
            raise ValueError("Thermal tariff boundary must preserve original utility components and basis")


@dataclass(frozen=True, slots=True)
class FacilityWindowCost:
    operation: FacilityOperationReceipt
    window_cost: WindowUtilityCost
    selected_product_basis: str
    product_boundary_id: str
    evidence_id: str
    _signature: str

    def _content(self):
        projection = self.window_cost.projection
        return recorded_content_sha256((
            id(self.operation), id(self.window_cost), id(projection),
            self.selected_product_basis, self.product_boundary_id, self.evidence_id,
            projection.source_fingerprint,
        ))

    def require_current(self):
        if self._content() != self._signature:
            raise ValueError("Facility priced-window source, product role or evidence changed")
        self.window_cost.require_current()
        _admit(self.operation, self.window_cost.projection)
        return self


def price_facility_operation(operation, projection, tariffs, *, evidence_id):
    """Use the existing tariff owner with an exact operation/product/window binding.

    Prices, USD year and billable boundaries come from explicit UtilityTariff
    objects. No annualization, sales allocation, prices or DCF are derived here.
    """
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Declare the operation-to-cost boundary evidence")
    _admit(operation, projection)
    cost = price_projection_window(projection, tariffs)
    selected = projection.window.selected_product_basis
    boundary = projection.source_binding.cached_snapshot.boundaries[selected]
    result = FacilityWindowCost(operation, cost, selected, boundary.boundary_id, evidence_id, "")
    from dataclasses import replace
    return replace(result, _signature=result._content()).require_current()
