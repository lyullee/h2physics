"""Construction sketch only; execution is deferred to Nurion."""

from h2physics.adapters.reliquefier_product import (
    CollectedProductInventory,
    FiniteColdReservoir,
    FiniteReliquefierProduct,
    ProductWindow,
    ReliquefierProductPorts,
)
from h2physics.core import PropertyBasis

basis = PropertyBasis("Hydrogen", "example-reference", "normal")
ports = ReliquefierProductPorts("feed", "liquid-product", "gas-return", "vent")
collector = FiniteReliquefierProduct(ports)
window = ProductWindow("accepted-native-clock", 0.0, 10.0)
product = CollectedProductInventory(basis, 0.0, 0.0)
cold = FiniteColdReservoir("cold-store", 2.0e8, 2.0e8, "cold-duty-joule")

# An original SteadyReliquefierResult is required; no fake result is constructed.
# receipt = collector.collect_steady(original, window,
#     collected_product_kg=..., returned_kg=..., vented_kg=...,
#     product=product, cold=cold)
