"""Finite equilibrium adsorption vessel over existing adsorption and gas owners.

This module adds vessel accounting, not another isotherm or equation of state.
The adsorption provider owns equilibrium loading and the property provider owns
the free-gas density.  This first level is an isothermal endpoint comparison;
it does not integrate filling, heat transfer, pressure drop or adsorption rate.
"""

import hashlib
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from ..adsorption import AdsorptionBasis, AdsorptionState
from ..core import (
    PropertyBasis,
    PropertyProvider,
    ThermoState,
    _real_numeric_array,
    finite,
    immutable_array,
    partial_pressure_pa,
)
from ..mixtures import GasComposition

_PENDING_SNAPSHOT_ISSUERS: set[object] = set()
_PENDING_PRESSURE_SOLUTION_ISSUERS: set[object] = set()
_PENDING_DELIVERY_ISSUERS: set[object] = set()


def _issue_vessel_snapshot(**values):
    token = object()
    _PENDING_SNAPSHOT_ISSUERS.add(token)
    try:
        return AdsorptionVesselSnapshot(**values, _issuer_token=token)
    except Exception:
        _PENDING_SNAPSHOT_ISSUERS.discard(token)
        raise


def _issue_pressure_solution(**values):
    token = object()
    _PENDING_PRESSURE_SOLUTION_ISSUERS.add(token)
    try:
        return AdsorptionPressureSolution(**values, _issuer_token=token)
    except Exception:
        _PENDING_PRESSURE_SOLUTION_ISSUERS.discard(token)
        raise


def _issue_vessel_delivery(**values):
    token = object()
    _PENDING_DELIVERY_ISSUERS.add(token)
    try:
        return AdsorptionVesselDelivery(**values, _issuer_token=token)
    except Exception:
        _PENDING_DELIVERY_ISSUERS.discard(token)
        raise


def _snapshot_digest(payload) -> str:
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _array_payload(value):
    if value is None:
        return None
    array = np.asarray(value)
    return array.dtype.str, array.shape, array.tobytes()


def _vector(value, name, size=None, *, nonnegative=False):
    result = np.array(_real_numeric_array(value, name), dtype=float, copy=True)
    if (result.ndim != 1 or (size is not None and result.shape != (size,))
            or not np.all(np.isfinite(result))
            or (nonnegative and np.any(result < 0))):
        raise ValueError(f"{name} must be a finite one-dimensional vector")
    result = immutable_array(result, name="result")
    return result


@dataclass(frozen=True, slots=True)
class AdsorptionVesselGeometry:
    """Auditable physical volumes and adsorbent mass for one rigid vessel."""

    internal_volume_m3: float
    adsorbent_mass_kg: float
    solid_envelope_volume_m3: float
    inaccessible_volume_m3: float
    volume_basis_id: str

    def __post_init__(self):
        finite(self.internal_volume_m3, "internal volume", positive=True)
        finite(self.adsorbent_mass_kg, "adsorbent mass", positive=True)
        for name in ("solid_envelope_volume_m3", "inaccessible_volume_m3"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError("Solid-envelope and inaccessible volumes cannot be negative")
        if not self.volume_basis_id.strip():
            raise ValueError("Vessel volume measurements need an identity")
        if self.void_volume_m3 <= 0:
            raise ValueError("Declared solid and inaccessible volumes leave no free-gas volume")

    @property
    def void_volume_m3(self):
        return self.internal_volume_m3 - self.solid_envelope_volume_m3 - self.inaccessible_volume_m3


@dataclass(frozen=True, slots=True)
class FrozenGasBinding:
    """Bind one declared gas composition to an existing property provider.

    The provider may be CoolProp for a pure gas or a separately reviewed frozen
    mixture provider. Composition identity remains caller evidence for generic
    providers; providers that expose their own composition metadata are checked
    against the binding before an EOS result can enter the vessel ledger.
    """

    provider: PropertyProvider
    species: tuple[str, ...]
    mole_fractions: np.ndarray
    molar_masses_kg_mol: np.ndarray
    composition_id: str
    property_basis: PropertyBasis
    _provider_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    @classmethod
    def bind(cls, provider, *, species, mole_fractions, molar_masses_kg_mol,
             composition_id):
        composition = GasComposition(
            composition_id, tuple(species), mole_fractions, molar_masses_kg_mol
        )
        if not isinstance(provider, PropertyProvider):
            raise TypeError("Gas binding requires the common PropertyProvider contract")
        return cls(
            provider, composition.species, composition.mole_fractions,
            composition.molar_masses_kg_mol, composition.composition_id, provider.basis,
        )

    def __post_init__(self):
        composition = GasComposition(
            self.composition_id, tuple(self.species), self.mole_fractions,
            self.molar_masses_kg_mol,
        )
        if self.provider.basis != self.property_basis:
            raise ValueError("Property-provider basis changed before binding completed")
        metadata_names = ("composition_id", "species", "mole_fractions", "molar_masses_kg_mol")
        present = tuple(hasattr(self.provider, name) for name in metadata_names)
        if any(present) and not all(present):
            raise TypeError("A provider exposing composition metadata must expose its complete composition binding")
        if all(present):
            if (self.provider.composition_id != composition.composition_id
                    or tuple(self.provider.species) != composition.species
                    or not np.array_equal(np.asarray(self.provider.mole_fractions, dtype=float),
                                          composition.mole_fractions)
                    or not np.array_equal(np.asarray(self.provider.molar_masses_kg_mol, dtype=float),
                                          composition.molar_masses_kg_mol)):
                raise ValueError("Declared vessel gas composition differs from the property-provider composition")
        object.__setattr__(self, "species", composition.species)
        object.__setattr__(self, "mole_fractions", composition.mole_fractions)
        object.__setattr__(self, "molar_masses_kg_mol", composition.molar_masses_kg_mol)
        object.__setattr__(self, "_provider_binding", self._binding_payload())

    def _provider_composition(self):
        names = ("composition_id", "species", "mole_fractions", "molar_masses_kg_mol")
        present = tuple(hasattr(self.provider, name) for name in names)
        if any(present) and not all(present):
            raise TypeError(
                "A provider exposing composition metadata must expose its complete composition binding"
            )
        if not all(present):
            return None
        provider_composition = GasComposition(
            self.provider.composition_id,
            tuple(self.provider.species),
            self.provider.mole_fractions,
            self.provider.molar_masses_kg_mol,
        )
        declared = GasComposition(
            self.composition_id, self.species, self.mole_fractions,
            self.molar_masses_kg_mol,
        )
        if (provider_composition.composition_id != declared.composition_id
                or provider_composition.species != declared.species
                or not np.array_equal(provider_composition.mole_fractions,
                                      declared.mole_fractions)
                or not np.array_equal(provider_composition.molar_masses_kg_mol,
                                      declared.molar_masses_kg_mol)):
            raise ValueError("Property-provider composition changed after gas binding")
        return (
            provider_composition.composition_id,
            provider_composition.species,
            tuple(float(value) for value in provider_composition.mole_fractions),
            tuple(float(value) for value in provider_composition.molar_masses_kg_mol),
        )

    def _binding_payload(self):
        self.property_basis.require_compatible(self.provider.basis)
        return (
            id(self.provider), self.property_basis, self.composition_id,
            tuple(self.species), tuple(float(value) for value in self.mole_fractions),
            tuple(float(value) for value in self.molar_masses_kg_mol),
            self._provider_composition(),
        )

    def require_current(self):
        if not self._provider_binding or self._binding_payload() != self._provider_binding:
            raise ValueError("Frozen gas provider or composition binding changed after admission")
        return self

    @property
    def mean_molar_mass_kg_mol(self):
        self.require_current()
        return GasComposition(
            self.composition_id, self.species, self.mole_fractions,
            self.molar_masses_kg_mol,
        ).molar_mass_kg_mol

    def state_pt(self, pressure_pa, temperature_k):
        self.require_current()
        state = self.provider.state_pt(pressure_pa, temperature_k)
        self.require_current()
        if not isinstance(state, ThermoState):
            raise TypeError("Property provider must return the common ThermoState")
        self.property_basis.require_compatible(state.basis)
        if (not np.isclose(state.pressure_pa, pressure_pa, rtol=1e-10, atol=1e-6)
                or not np.isclose(state.temperature_k, temperature_k, rtol=1e-10, atol=1e-9)
                or state.phase not in {"gas", "supercritical", "supercritical_gas"}):
            raise ValueError("Property result does not retain the requested gas endpoint")
        return state


@dataclass(frozen=True, slots=True)
class AdsorptionVesselSnapshot:
    vessel_id: str
    geometry: AdsorptionVesselGeometry
    adsorption_basis: AdsorptionBasis
    gas_composition_id: str
    gas_state: ThermoState
    equilibrium: AdsorptionState
    free_gas_component_mol: np.ndarray
    adsorbed_component_mol: np.ndarray
    total_component_mol: np.ndarray
    adsorbed_standard_uncertainty_component_mol: np.ndarray | None = None
    uncertainty_semantics: str = "unqualified"
    uncertainty_source_ids: tuple[str, ...] = ()
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SNAPSHOT_ISSUERS:
            raise TypeError("Create vessel snapshots through FiniteAdsorptionVessel.snapshot")
        _PENDING_SNAPSHOT_ISSUERS.remove(self._issuer_token)
        if not self.vessel_id.strip() or not self.gas_composition_id.strip():
            raise ValueError("Snapshot needs vessel and gas-composition identities")
        size = len(self.adsorption_basis.species)
        free = _vector(self.free_gas_component_mol, "free gas inventory", size, nonnegative=True)
        adsorbed = _vector(self.adsorbed_component_mol, "adsorbed inventory", size,
                           nonnegative=True)
        total = _vector(self.total_component_mol, "total inventory", size, nonnegative=True)
        if not np.allclose(total, free + adsorbed, rtol=1e-12, atol=1e-12):
            raise ValueError("Total vessel inventory must equal free plus adsorbed inventory")
        uncertainty = self.adsorbed_standard_uncertainty_component_mol
        if uncertainty is not None:
            uncertainty = _vector(uncertainty, "adsorbed standard uncertainty", size,
                                  nonnegative=True)
        if self.uncertainty_semantics not in {
                "unqualified", "reported_standard_uncertainty",
                "independent_standard_uncertainty", "covariance_matrix_propagated"}:
            raise ValueError("Vessel uncertainty semantics must remain explicit")
        sources = tuple(self.uncertainty_source_ids)
        if any(not isinstance(value, str) or not value.strip() for value in sources):
            raise ValueError("Uncertainty source identities must be nonempty text")
        if (self.uncertainty_semantics != "unqualified") != (uncertainty is not None):
            raise ValueError("Retain a standard uncertainty vector exactly when its semantics are qualified")
        for name, value in (("free_gas_component_mol", free),
                            ("adsorbed_component_mol", adsorbed),
                            ("total_component_mol", total)):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "adsorbed_standard_uncertainty_component_mol", uncertainty)
        object.__setattr__(self, "uncertainty_source_ids", sources)
        object.__setattr__(self, "_seal", _snapshot_digest(self._content_payload()))

    def _content_payload(self):
        return (
            self.vessel_id, id(self.geometry), repr(self.geometry),
            id(self.adsorption_basis), repr(self.adsorption_basis),
            self.gas_composition_id, id(self.gas_state), repr(self.gas_state),
            id(self.equilibrium), repr(self.equilibrium),
            _array_payload(self.free_gas_component_mol),
            _array_payload(self.adsorbed_component_mol),
            _array_payload(self.total_component_mol),
            _array_payload(self.adsorbed_standard_uncertainty_component_mol),
            self.uncertainty_semantics, tuple(self.uncertainty_source_ids),
        )

    def require_current(self):
        if _snapshot_digest(self._content_payload()) != self._seal:
            raise ValueError("Vessel snapshot changed after native property/loading evaluation")
        return self

    @property
    def total_inventory_mol(self):
        return float(self.total_component_mol.sum())


@dataclass(frozen=True, slots=True)
class AdsorptionVesselDelivery:
    charged: AdsorptionVesselSnapshot
    discharged: AdsorptionVesselSnapshot
    free_gas_change_mol: np.ndarray
    adsorbed_change_mol: np.ndarray
    total_change_mol: np.ndarray
    delivery_species: tuple[str, ...]
    delivered_product_mol: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_DELIVERY_ISSUERS:
            raise TypeError("Create delivery receipts through FiniteAdsorptionVessel.delivery")
        _PENDING_DELIVERY_ISSUERS.remove(self._issuer_token)
        if (type(self.charged) is not AdsorptionVesselSnapshot
                or type(self.discharged) is not AdsorptionVesselSnapshot):
            raise TypeError("Delivery receipts require native vessel snapshots")
        self.charged.require_current()
        self.discharged.require_current()
        self.charged.adsorption_basis.require_compatible(self.discharged.adsorption_basis)
        if (self.charged.vessel_id != self.discharged.vessel_id
                or self.charged.geometry != self.discharged.geometry
                or self.charged.gas_composition_id != self.discharged.gas_composition_id):
            raise ValueError("Delivery endpoints must share vessel, geometry and gas composition")
        size = len(self.charged.adsorption_basis.species)
        product = tuple(self.delivery_species)
        free = _vector(self.free_gas_change_mol, "free gas change", size)
        adsorbed = _vector(self.adsorbed_change_mol, "adsorbed change", size)
        total = _vector(self.total_change_mol, "total change", size)
        if (not np.allclose(free, self.charged.free_gas_component_mol
                            - self.discharged.free_gas_component_mol,
                            rtol=1e-12, atol=1e-12)
                or not np.allclose(adsorbed, self.charged.adsorbed_component_mol
                                   - self.discharged.adsorbed_component_mol,
                                   rtol=1e-12, atol=1e-12)
                or not np.allclose(total, free + adsorbed, rtol=1e-12, atol=1e-12)
                or not np.allclose(total, self.charged.total_component_mol
                                   - self.discharged.total_component_mol,
                                   rtol=1e-12, atol=1e-12)
                or not product or len(set(product)) != len(product)
                or any(name not in self.charged.adsorption_basis.species
                       for name in product)):
            raise ValueError("Delivery changes or selected product species are inconsistent")
        selected = [self.charged.adsorption_basis.species.index(name)
                    for name in product]
        expected = float(total[selected].sum())
        if (not np.isclose(self.delivered_product_mol, expected, rtol=1e-12, atol=1e-12)
                or self.delivered_product_mol <= 0):
            raise ValueError("Selected product must have a positive finite delivered amount")
        for name, value in (("free_gas_change_mol", free),
                            ("adsorbed_change_mol", adsorbed),
                            ("total_change_mol", total)):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "delivery_species", product)
        object.__setattr__(self, "_seal", _snapshot_digest(self._content_payload()))

    def _content_payload(self):
        return (
            id(self.charged), self.charged._seal,
            id(self.discharged), self.discharged._seal,
            _array_payload(self.free_gas_change_mol),
            _array_payload(self.adsorbed_change_mol),
            _array_payload(self.total_change_mol),
            tuple(self.delivery_species), self.delivered_product_mol,
        )

    def require_current(self):
        self.charged.require_current()
        self.discharged.require_current()
        if _snapshot_digest(self._content_payload()) != self._seal:
            raise ValueError("Adsorption delivery receipt changed after owner admission")
        return self


@dataclass(frozen=True, slots=True)
class AdsorptionPressureSolution:
    """Pressure matching one species inventory within a caller-declared domain."""

    snapshot: AdsorptionVesselSnapshot
    species_id: str
    target_inventory_mol: float
    achieved_inventory_mol: float
    residual_mol: float
    lower_pressure_pa: float
    upper_pressure_pa: float
    sampled_pressure_count: int
    inventory_tolerance_mol: float
    pressure_tolerance_pa: float
    sampled_pressures_pa: np.ndarray
    sampled_species_inventory_mol: np.ndarray
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PRESSURE_SOLUTION_ISSUERS:
            raise TypeError("Create pressure solutions through FiniteAdsorptionVessel.pressure_for_inventory")
        _PENDING_PRESSURE_SOLUTION_ISSUERS.remove(self._issuer_token)
        if (type(self.snapshot) is not AdsorptionVesselSnapshot
                or not isinstance(self.species_id, str)
                or self.species_id not in self.snapshot.adsorption_basis.species):
            raise ValueError("Pressure solution species is absent from its vessel snapshot")
        for name in ("target_inventory_mol", "achieved_inventory_mol"):
            finite(getattr(self, name), name, positive=True)
        finite(self.residual_mol, "inventory residual")
        finite(self.inventory_tolerance_mol, "inventory tolerance", positive=True)
        finite(self.pressure_tolerance_pa, "pressure tolerance", positive=True)
        finite(self.lower_pressure_pa, "lower pressure bound", positive=True)
        finite(self.upper_pressure_pa, "upper pressure bound", positive=True)
        sampled_pressures = _vector(self.sampled_pressures_pa, "sampled pressure grid")
        sampled_inventory = _vector(self.sampled_species_inventory_mol,
                                    "sampled species inventory", nonnegative=True)
        if (self.lower_pressure_pa >= self.upper_pressure_pa
                or not self.lower_pressure_pa <= self.snapshot.gas_state.pressure_pa <= self.upper_pressure_pa
                or isinstance(self.sampled_pressure_count, bool)
                or not isinstance(self.sampled_pressure_count, int)
                or self.sampled_pressure_count < 3
                or sampled_pressures.shape != (self.sampled_pressure_count,)
                or sampled_inventory.shape != (self.sampled_pressure_count,)
                or not np.isclose(sampled_pressures[0], self.lower_pressure_pa,
                                  rtol=1e-12, atol=1e-9)
                or not np.isclose(sampled_pressures[-1], self.upper_pressure_pa,
                                  rtol=1e-12, atol=1e-9)
                or np.any(np.diff(sampled_pressures) <= 0.)):
            raise ValueError("Pressure solution must retain an ordered sampled bracket")
        monotonic_tolerance = max(
            self.inventory_tolerance_mol,
            1e-12 * max(float(sampled_inventory.max()), 1.0),
        )
        if np.any(np.diff(sampled_inventory) < -monotonic_tolerance):
            raise ValueError("Pressure receipt has a sampled nonmonotone inventory curve")
        sampled_residuals = sampled_inventory - self.target_inventory_mol
        exact = np.flatnonzero(np.abs(sampled_residuals) <= self.inventory_tolerance_mol)
        crossings = np.flatnonzero(
            (sampled_residuals[:-1] < 0.) & (sampled_residuals[1:] > 0.)
        )
        if ((exact.size == 1 and crossings.size != 0)
                or (exact.size == 0 and crossings.size != 1)
                or exact.size > 1):
            raise ValueError("Pressure receipt does not retain one sampled target crossing")
        pressure_index = int(exact[0]) if exact.size else None
        if pressure_index is not None:
            if not np.isclose(self.snapshot.gas_state.pressure_pa,
                              sampled_pressures[pressure_index], rtol=1e-12, atol=1e-9):
                raise ValueError("Exact sampled pressure differs from the endpoint snapshot")
        else:
            left = int(crossings[0])
            if not sampled_pressures[left] <= self.snapshot.gas_state.pressure_pa <= sampled_pressures[left + 1]:
                raise ValueError("Solved pressure is outside its retained local inventory bracket")
        index = self.snapshot.adsorption_basis.species.index(self.species_id)
        actual = float(self.snapshot.total_component_mol[index])
        if (not np.isclose(actual, self.achieved_inventory_mol, rtol=1e-12, atol=1e-12)
                or not np.isclose(actual - self.target_inventory_mol, self.residual_mol,
                                  rtol=1e-12, atol=1e-12)
                or abs(self.residual_mol) > self.inventory_tolerance_mol):
            raise ValueError("Pressure solution inventory receipt differs from its snapshot")
        if (pressure_index is not None
                and not np.isclose(sampled_inventory[pressure_index], actual,
                                   rtol=1e-12, atol=self.inventory_tolerance_mol)):
            raise ValueError("Exact sampled inventory differs from the endpoint snapshot")
        object.__setattr__(self, "sampled_pressures_pa", sampled_pressures)
        object.__setattr__(self, "sampled_species_inventory_mol", sampled_inventory)

    @property
    def pressure_pa(self):
        """Solved absolute pressure from the retained endpoint state."""
        return self.snapshot.gas_state.pressure_pa


class FiniteAdsorptionVessel:
    """Endpoint inventory and usable-capacity accounting for a finite vessel."""

    def __init__(self, *, vessel_id, geometry, adsorption, gas):
        if not isinstance(vessel_id, str) or not vessel_id.strip():
            raise ValueError("Finite adsorption vessel needs an identity")
        if not isinstance(geometry, AdsorptionVesselGeometry):
            raise TypeError("Use AdsorptionVesselGeometry")
        if (not hasattr(adsorption, "basis")
                or not callable(getattr(adsorption, "equilibrium", None))):
            raise TypeError("Use the structural AdsorptionProvider contract")
        if not isinstance(gas, FrozenGasBinding):
            raise TypeError("Use FrozenGasBinding")
        if adsorption.basis.loading_definition != "absolute":
            raise ValueError("Finite inventory requires absolute uptake; excess uptake needs a correction model")
        if adsorption.basis.species != gas.species:
            raise ValueError("Adsorption and free-gas species order differs")
        self.vessel_id = vessel_id
        self.geometry = geometry
        self.adsorption = adsorption
        self.gas = gas
        self.adsorption_basis = adsorption.basis

    def snapshot(self, pressure_pa, temperature_k):
        pressure = finite(pressure_pa, "vessel pressure", positive=True)
        temperature = finite(temperature_k, "vessel temperature", positive=True)
        if self.adsorption.basis != self.adsorption_basis:
            raise ValueError("Adsorption provider basis changed after vessel construction")
        partial = partial_pressure_pa(pressure, self.gas.mole_fractions)
        equilibrium = self.adsorption.equilibrium(partial, temperature)
        if type(equilibrium) is not AdsorptionState:
            raise TypeError("Adsorption provider must return the common AdsorptionState")
        self.adsorption_basis.require_compatible(equilibrium.basis)
        if (not np.allclose(equilibrium.partial_pressures_pa, partial, rtol=1e-12, atol=1e-6)
                or not np.isclose(equilibrium.temperature_k, temperature, rtol=1e-12, atol=1e-9)):
            raise ValueError("Adsorption result changed the requested endpoint")
        gas_state = self.gas.state_pt(pressure, temperature)
        free_total = gas_state.density_kg_m3 * self.geometry.void_volume_m3 / self.gas.mean_molar_mass_kg_mol
        free = free_total * self.gas.mole_fractions
        adsorbed = equilibrium.loadings_mol_kg * self.geometry.adsorbent_mass_kg
        if np.any(adsorbed < 0):
            raise ValueError("Absolute adsorption produced a negative component inventory")
        source_observations = equilibrium.source_observations
        uncertainty = None
        uncertainty_kind = "unqualified"
        uncertainty_sources = ()
        if equilibrium.propagated_standard_uncertainty_mol_kg is not None:
            uncertainty_kind = equilibrium.uncertainty_semantics
            uncertainty = (equilibrium.propagated_standard_uncertainty_mol_kg
                           * self.geometry.adsorbent_mass_kg)
            uncertainty_sources = equilibrium.uncertainty_source_ids
        elif equilibrium.uncertainty_semantics != "unqualified":
            raise ValueError("Qualified adsorption uncertainty lacks a propagated state array")
        elif source_observations:
            uncertainties = np.zeros(len(self.adsorption_basis.species), dtype=float)
            independent_variances = np.zeros(len(self.adsorption_basis.species), dtype=float)
            kinds, source_ids = set(), set()
            qualified_site_species = set()
            for site_index, site in enumerate(source_observations):
                for observation in site:
                    if observation.source_dataset_id and observation.source_sha256:
                        source_ids.add(observation.source_dataset_id + ":" + observation.source_sha256)
                    if observation.covariance_group_id:
                        source_ids.add("dependence:" + observation.covariance_group_id)
                    kinds.add(observation.uncertainty_kind)
                    if observation.uncertainty_kind == "unqualified":
                        continue
                    if observation.standard_uncertainty_mol_kg is None:
                        raise ValueError("Qualified uncertainty semantics require a source standard uncertainty")
                    species_index = equilibrium.basis.species.index(observation.species)
                    # A site's interpolated standard uncertainty is not inferred from
                    # multiple rows until their covariance is supplied. Only a single
                    # unit-weight row can pass through this scalar path without a law.
                    if observation.uncertainty_kind == "covariance_matrix_propagated":
                        raise ValueError("Covariance-propagated uncertainty requires a covariance matrix, not row scalars")
                    if observation.uncertainty_kind == "independent_standard_uncertainty":
                        independent_variances[species_index] += (
                            observation.interpolation_weight*observation.standard_uncertainty_mol_kg)**2
                    else:
                        if observation.interpolation_weight != 1.:
                            raise ValueError("Interpolated reported uncertainty requires covariance evidence")
                        uncertainties[species_index] += observation.standard_uncertainty_mol_kg
                    qualified_site_species.add((site_index, species_index))
            if any(kind == "reported_standard_uncertainty" for kind in kinds):
                if len(source_observations) != 1:
                    raise ValueError(
                        "Reported row uncertainty only passes through one un-interpolated source observation per species"
                    )
                for species in self.adsorption_basis.species:
                    rows = [item for item in source_observations[0]
                            if item.species == species]
                    if len(rows) != 1 or rows[0].interpolation_weight != 1.:
                        raise ValueError(
                            "Reported row uncertainty only passes through one un-interpolated source observation per species"
                        )
            if len(kinds) == 1 and next(iter(kinds)) != "unqualified":
                expected_site_species = {
                    (site_index, species_index)
                    for site_index in range(len(source_observations))
                    for species_index in range(len(self.adsorption_basis.species))
                }
                if qualified_site_species != expected_site_species:
                    raise ValueError(
                        "Source uncertainty must cover every species at every adsorption site"
                    )
                uncertainty_kind = next(iter(kinds))
                loading_sigma = (np.sqrt(independent_variances)
                                 if uncertainty_kind == "independent_standard_uncertainty"
                                 else uncertainties)
                uncertainty = loading_sigma*self.geometry.adsorbent_mass_kg
            elif any(kind != "unqualified" for kind in kinds):
                raise ValueError("Mixed source uncertainty semantics cannot be combined implicitly")
            uncertainty_sources = tuple(sorted(source_ids))
        return _issue_vessel_snapshot(
            vessel_id=self.vessel_id, geometry=self.geometry,
            adsorption_basis=self.adsorption_basis,
            gas_composition_id=self.gas.composition_id, gas_state=gas_state,
            equilibrium=equilibrium, free_gas_component_mol=free,
            adsorbed_component_mol=adsorbed, total_component_mol=free + adsorbed,
            adsorbed_standard_uncertainty_component_mol=uncertainty,
            uncertainty_semantics=uncertainty_kind,
            uncertainty_source_ids=tuple(sorted(uncertainty_sources)),
        )

    def delivery(self, charged_pressure_pa, charged_temperature_k,
                 discharged_pressure_pa, discharged_temperature_k, *, delivery_species):
        charged = self.snapshot(charged_pressure_pa, charged_temperature_k)
        discharged = self.snapshot(discharged_pressure_pa, discharged_temperature_k)
        if (charged.gas_composition_id != discharged.gas_composition_id
                or charged.geometry != discharged.geometry):
            raise ValueError("Working capacity requires one unchanged vessel and gas composition")
        free = charged.free_gas_component_mol - discharged.free_gas_component_mol
        adsorbed = charged.adsorbed_component_mol - discharged.adsorbed_component_mol
        total = charged.total_component_mol - discharged.total_component_mol
        product = tuple(delivery_species)
        indices = [self.adsorption_basis.species.index(name) for name in product]
        delivered = float(total[indices].sum())
        return _issue_vessel_delivery(
            charged=charged, discharged=discharged,
            free_gas_change_mol=free, adsorbed_change_mol=adsorbed,
            total_change_mol=total, delivery_species=product,
            delivered_product_mol=delivered,
        )

    def pressure_for_inventory(
        self,
        target_inventory_mol,
        species_id,
        temperature_k,
        pressure_bounds_pa,
        *,
        samples=33,
        inventory_tolerance_mol=1e-8,
        pressure_tolerance_pa=1e-3,
    ) -> AdsorptionPressureSolution:
        """Invert equilibrium vessel inventory over a sampled, monotone pressure bracket.

        This is an isothermal frozen-composition endpoint calculation. The caller
        supplies the pressure domain; sampled monotonicity is a guard, not a proof
        between samples. No root is accepted outside the evaluated bracket.
        """
        target = finite(target_inventory_mol, "target species inventory", positive=True)
        temperature = finite(temperature_k, "vessel temperature", positive=True)
        if not isinstance(species_id, str) or species_id not in self.adsorption_basis.species:
            raise ValueError("Select one species in the declared vessel composition")
        bounds = _vector(pressure_bounds_pa, "pressure bounds", 2, nonnegative=True)
        lower, upper = map(float, bounds)
        if lower <= 0 or lower >= upper:
            raise ValueError("Pressure inversion needs positive, ordered pressure bounds")
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 3:
            raise ValueError("Sample at least three pressures before inverting inventory")
        inventory_tolerance = finite(inventory_tolerance_mol, "inventory tolerance")
        pressure_tolerance = finite(pressure_tolerance_pa, "pressure tolerance", positive=True)
        if inventory_tolerance <= 0:
            raise ValueError("Inventory tolerance must be positive")

        species_index = self.adsorption_basis.species.index(species_id)
        pressures = np.linspace(lower, upper, samples)
        snapshots = tuple(self.snapshot(float(p), temperature) for p in pressures)
        inventories = np.array(
            [snapshot.total_component_mol[species_index] for snapshot in snapshots],
            dtype=float,
        )
        monotonic_tolerance = max(inventory_tolerance, 1e-12 * max(float(inventories.max()), 1.0))
        if np.any(np.diff(inventories) < -monotonic_tolerance):
            raise ValueError("Sampled species inventory is nonmonotone across the pressure bracket")
        if target < inventories[0] - inventory_tolerance or target > inventories[-1] + inventory_tolerance:
            raise ValueError("Target species inventory is outside the sampled pressure bracket")

        residuals = inventories - target
        exact = np.flatnonzero(np.abs(residuals) <= inventory_tolerance)
        if exact.size:
            if exact.size > 1:
                raise ValueError("Target inventory maps to multiple sampled pressures; inverse is ambiguous")
            pressure_solution = float(pressures[int(exact[0])])
        else:
            crossings = np.flatnonzero((residuals[:-1] < 0.) & (residuals[1:] > 0.))
            if not len(crossings):
                raise ValueError("Target inventory has no bracketed pressure root")
            if len(crossings) > 1:
                raise ValueError("Target inventory has multiple sampled pressure brackets")
            left = int(crossings[0])
            right = left + 1
            pressure_solution = float(brentq(
                lambda p: float(self.snapshot(float(p), temperature).total_component_mol[species_index])
                - target,
                float(pressures[left]), float(pressures[right]),
                xtol=min(pressure_tolerance, max((upper - lower) * 1e-12,
                                                 np.finfo(float).tiny)),
                rtol=4 * np.finfo(float).eps,
            ))
        snapshot = self.snapshot(pressure_solution, temperature)
        achieved = float(snapshot.total_component_mol[species_index])
        residual = achieved - target
        if abs(residual) > inventory_tolerance:
            raise ValueError("Pressure inversion residual exceeds the caller inventory tolerance")
        return _issue_pressure_solution(
            snapshot=snapshot, species_id=species_id,
            target_inventory_mol=target, achieved_inventory_mol=achieved,
            residual_mol=residual, lower_pressure_pa=lower,
            upper_pressure_pa=upper, sampled_pressure_count=samples,
            inventory_tolerance_mol=inventory_tolerance,
            pressure_tolerance_pa=pressure_tolerance,
            sampled_pressures_pa=pressures,
            sampled_species_inventory_mol=inventories,
        )
