"""Mass-flow receipts from an existing finite adsorption-vessel endpoint ledger.

This adapter adds only a unit-bearing material-flow view. The vessel's native
adsorption and gas-property owners remain responsible for endpoint inventories;
no equilibrium, flow, or timing law is supplied here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from ..core import _real_numeric_array, finite, immutable_array

if TYPE_CHECKING:
    from ..adapters.finite_adsorption_vessel import AdsorptionVesselDelivery


@dataclass(frozen=True, slots=True)
class AdsorptionProductMassFlow:
    """Signed species mass changes and interval-average delivery rates.

    ``molar_masses_kg_mol`` must follow the exact species order in the accepted
    vessel ledger. ``elapsed_s`` is supplied by the caller and defines only the
    averaging interval; this receipt does not imply a time-resolved flow profile.
    """

    delivery: AdsorptionVesselDelivery
    species: tuple[str, ...]
    molar_masses_kg_mol: np.ndarray
    elapsed_s: float
    component_mass_change_kg: np.ndarray = field(init=False)
    component_average_mass_rate_kg_s: np.ndarray = field(init=False)
    delivered_product_mass_kg: float = field(init=False)
    delivered_product_average_mass_rate_kg_s: float = field(init=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        # The adapters package also imports this receipt. Defer the concrete
        # class lookup until construction, after both module namespaces exist.
        from ..adapters.finite_adsorption_vessel import AdsorptionVesselDelivery

        if type(self.delivery) is not AdsorptionVesselDelivery:
            raise TypeError("Mass-flow conversion requires an accepted adsorption-vessel delivery")
        self.delivery.require_current()
        species = tuple(self.species)
        expected = tuple(self.delivery.charged.adsorption_basis.species)
        if species != expected:
            raise ValueError("Molar-mass species order must match the vessel delivery basis exactly")
        molar_masses = np.array(
            _real_numeric_array(self.molar_masses_kg_mol, "molar masses"),
            dtype=float, copy=True,
        )
        if (molar_masses.shape != (len(species),) or not np.all(np.isfinite(molar_masses))
                or np.any(molar_masses <= 0)):
            raise ValueError("Every delivered species needs a positive finite molar mass")
        elapsed = finite(self.elapsed_s, "delivery averaging interval", positive=True)
        mass = np.asarray(self.delivery.total_change_mol, dtype=float) * molar_masses
        rate = mass / elapsed
        selected = [species.index(name) for name in self.delivery.delivery_species]
        product_mass = float(mass[selected].sum())
        product_rate = product_mass / elapsed
        if product_mass <= 0:
            raise ValueError("Selected product mass delivery must be positive")
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "molar_masses_kg_mol", immutable_array(molar_masses))
        object.__setattr__(self, "elapsed_s", elapsed)
        object.__setattr__(self, "component_mass_change_kg", immutable_array(mass))
        object.__setattr__(self, "component_average_mass_rate_kg_s", immutable_array(rate))
        object.__setattr__(self, "delivered_product_mass_kg", product_mass)
        object.__setattr__(self, "delivered_product_average_mass_rate_kg_s", product_rate)
        self.delivery.require_current()
        object.__setattr__(self, "_seal", self._content_digest())

    def _content_digest(self) -> str:
        digest = hashlib.sha256()
        digest.update(repr((
            id(self.delivery), self.species, tuple(float(x) for x in self.molar_masses_kg_mol),
            self.elapsed_s, self.delivered_product_mass_kg,
            self.delivered_product_average_mass_rate_kg_s,
        )).encode("utf-8"))
        for array in (self.component_mass_change_kg, self.component_average_mass_rate_kg_s):
            values = np.asarray(array, dtype=np.float64)
            digest.update(repr(values.shape).encode("ascii"))
            digest.update(values.tobytes(order="C"))
        return digest.hexdigest()

    def require_current(self) -> AdsorptionProductMassFlow:
        """Revalidate source delivery and derived mass/rate ledgers before downstream use."""
        self.delivery.require_current()
        if not self._seal or self._content_digest() != self._seal:
            raise ValueError("Product mass-flow receipt changed after projection")
        expected_mass = np.asarray(self.delivery.total_change_mol, dtype=float) * np.asarray(
            self.molar_masses_kg_mol, dtype=float
        )
        expected_rate = expected_mass / self.elapsed_s
        selected = [self.species.index(name) for name in self.delivery.delivery_species]
        expected_product = float(expected_mass[selected].sum())
        if (not np.array_equal(self.component_mass_change_kg, expected_mass)
                or not np.array_equal(self.component_average_mass_rate_kg_s, expected_rate)
                or expected_product != self.delivered_product_mass_kg
                or expected_product / self.elapsed_s
                != self.delivered_product_average_mass_rate_kg_s):
            raise ValueError("Product mass-flow projection no longer matches the accepted delivery")
        return self
