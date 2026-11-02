"""Reversible-flow benchmark for an explicitly bounded hydrogen liquefaction step.

This module evaluates state data supplied by the caller. It does not model a
refrigeration cycle, compressor, ortho-para conversion, or process heat network.
"""

from dataclasses import dataclass
import math

from ..core import finite


@dataclass(frozen=True, slots=True)
class HydrogenFlowState:
    """Mass-specific state properties on one caller-declared property basis."""

    enthalpy_j_kg: float
    entropy_j_kg_k: float
    property_basis_id: str
    evidence_id: str

    def __post_init__(self):
        object.__setattr__(self, "enthalpy_j_kg", finite(self.enthalpy_j_kg, "Enthalpy"))
        object.__setattr__(self, "entropy_j_kg_k", finite(self.entropy_j_kg_k, "Entropy"))
        if not isinstance(self.property_basis_id, str) or not self.property_basis_id.strip():
            raise ValueError("Declare the property-basis identity")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare source evidence for the state properties")


@dataclass(frozen=True, slots=True)
class LiquefactionBenchmark:
    """Ideal minimum work and measured-boundary specific work for pure H2.

    The process boundary must have equal feed and liquid product masses; vent,
    purge, ortho-para conversion and external heat exergy need separate modeling.
    """

    feed: HydrogenFlowState
    liquid_product: HydrogenFlowState
    feed_mass_kg: float
    product_mass_kg: float
    external_work_j: float
    environment_temperature_k: float
    process_window_id: str
    process_evidence_id: str

    def __post_init__(self):
        if not isinstance(self.feed, HydrogenFlowState) or not isinstance(
            self.liquid_product, HydrogenFlowState
        ):
            raise TypeError("Feed and product must be typed hydrogen flow states")
        if self.feed.property_basis_id != self.liquid_product.property_basis_id:
            raise ValueError("Feed and product states need the same property reference")
        feed_mass = finite(self.feed_mass_kg, "Feed mass", positive=True)
        product_mass = finite(self.product_mass_kg, "Product mass", positive=True)
        if not math.isclose(feed_mass, product_mass, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("This benchmark requires a loss-free feed/product mass boundary")
        object.__setattr__(self, "feed_mass_kg", feed_mass)
        object.__setattr__(self, "product_mass_kg", product_mass)
        object.__setattr__(
            self, "external_work_j", finite(self.external_work_j, "External work", positive=True)
        )
        object.__setattr__(
            self,
            "environment_temperature_k",
            finite(self.environment_temperature_k, "Environment temperature", positive=True),
        )
        if not isinstance(self.process_window_id, str) or not self.process_window_id.strip():
            raise ValueError("Declare the process-window identity")
        if not isinstance(self.process_evidence_id, str) or not self.process_evidence_id.strip():
            raise ValueError("Declare evidence for the process work and mass boundary")
        if self.minimum_reversible_work_j_kg <= 0.0:
            raise ValueError("The declared feed/product states do not define positive minimum work")

    @property
    def minimum_reversible_work_j_kg(self) -> float:
        """Flow-exergy increase, (h_product-h_feed)-T0(s_product-s_feed)."""
        return (
            self.liquid_product.enthalpy_j_kg - self.feed.enthalpy_j_kg
            - self.environment_temperature_k
            * (self.liquid_product.entropy_j_kg_k - self.feed.entropy_j_kg_k)
        )

    @property
    def minimum_reversible_work_j(self) -> float:
        return self.minimum_reversible_work_j_kg * self.product_mass_kg

    @property
    def specific_external_work_kwh_kg(self) -> float:
        return self.external_work_j / self.product_mass_kg / 3_600_000.0

    @property
    def reversible_work_fraction(self) -> float:
        """Ratio of ideal minimum to declared external work; diagnostic only."""
        return self.minimum_reversible_work_j / self.external_work_j


def benchmark_hydrogen_liquefaction(
    *, feed, liquid_product, feed_mass_kg, product_mass_kg,
    external_work_j, environment_temperature_k, process_window_id, process_evidence_id,
) -> LiquefactionBenchmark:
    """Construct a source-bound reversible-work benchmark from caller states."""
    return LiquefactionBenchmark(
        feed, liquid_product, feed_mass_kg, product_mass_kg, external_work_j,
        environment_temperature_k, process_window_id, process_evidence_id,
    )
