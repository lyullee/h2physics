"""Native adsorption identities and loading-only working capacity."""

import math
from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np

from .core import finite, immutable_array


@dataclass(frozen=True, slots=True)
class AdsorptionBasis:
    material_id: str
    species: tuple[str, ...]
    amount_basis_id: str
    engine_id: str
    parameter_id: str
    references: tuple[str, ...]
    loading_definition: Literal["absolute", "surface_excess", "source_defined"] = "source_defined"

    def __post_init__(self):
        species, references = tuple(self.species), tuple(self.references)
        if (not species or len(set(species)) != len(species) or any(not name for name in species)
                or any(not value for value in (self.material_id, self.amount_basis_id,
                                               self.engine_id, self.parameter_id)) or not references):
            raise ValueError("Adsorption needs material, species order, amount basis, engine and parameter evidence")
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "references", references)
        if self.loading_definition not in {"absolute", "surface_excess", "source_defined"}:
            raise ValueError("Declare absolute, surface-excess or source-defined uptake")

    def require_compatible(self, other: "AdsorptionBasis"):
        if self != other:
            raise ValueError("Material, species, uptake basis or model/parameter identity differs")


@dataclass(frozen=True, slots=True)
class AdsorptionDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    maximum_total_pressure_pa: float
    minimum_total_pressure_pa: float = 0.

    def __post_init__(self):
        for name in ("minimum_temperature_k", "maximum_temperature_k", "maximum_total_pressure_pa"):
            finite(getattr(self, name), name, positive=True)
        if finite(self.minimum_total_pressure_pa, "minimum total pressure") < 0:
            raise ValueError("Minimum total pressure cannot be negative")
        if (self.minimum_temperature_k > self.maximum_temperature_k
                or self.minimum_total_pressure_pa >= self.maximum_total_pressure_pa):
            raise ValueError("Adsorption domain bounds are invalid")

    def require_state(self, partial_pressures_pa, temperature_k):
        finite(temperature_k, "temperature", positive=True)
        pressures = np.asarray(partial_pressures_pa, dtype=float)
        if pressures.ndim != 1 or not np.all(np.isfinite(pressures)) or np.any(pressures < 0):
            raise ValueError("Partial pressures must be a finite, nonnegative vector")
        if not self.minimum_total_pressure_pa <= pressures.sum() <= self.maximum_total_pressure_pa:
            raise ValueError("Total pressure is outside the declared adsorption domain")
        if not self.minimum_temperature_k <= temperature_k <= self.maximum_temperature_k:
            raise ValueError("Temperature is outside the declared adsorption domain")


@dataclass(frozen=True, slots=True)
class AdsorptionSourceObservation:
    """One weighted, species-qualified source-row receipt for an adsorption site."""

    species: str
    source_row: int
    interpolation_weight: float
    source_loading_mol_kg: float
    standard_uncertainty_mol_kg: float | None = None
    detection_limit_mol_kg: float | None = None
    quantification_limit_mol_kg: float | None = None
    source_dataset_id: str | None = None
    source_sha256: str | None = None
    uncertainty_kind: str = "unqualified"
    covariance_group_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.species, str) or not self.species.strip():
            raise ValueError("Source observation needs a species identity")
        for name in ("source_dataset_id", "source_sha256", "covariance_group_id"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be nonempty text when supplied")
        if self.source_sha256 is not None and (
                len(self.source_sha256) != 64
                or any(char not in "0123456789abcdef" for char in self.source_sha256)):
            raise ValueError("Source observation checksum must be lowercase SHA-256")
        if self.uncertainty_kind not in {
                "unqualified", "reported_standard_uncertainty", "independent_standard_uncertainty",
                "covariance_matrix_propagated"}:
            raise ValueError("Declare the uncertainty semantics without inferring independence")
        if self.uncertainty_kind == "covariance_matrix_propagated":
            raise ValueError("Use a covariance-derived state receipt; a row observation is not a covariance result")
        if self.uncertainty_kind == "independent_standard_uncertainty" and not self.covariance_group_id:
            raise ValueError("Independent errors require an explicit independence evidence identity")
        if (isinstance(self.source_row, bool) or not isinstance(self.source_row, int)
                or self.source_row < 1):
            raise ValueError("Source observation needs a positive integer row identity")
        weight = self.interpolation_weight
        if (isinstance(weight, bool) or not isinstance(weight, (int, float))
                or not math.isfinite(weight) or not 0. <= weight <= 1.):
            raise ValueError("Source interpolation weight must be finite and in [0, 1]")
        object.__setattr__(self, "interpolation_weight", float(weight))
        for name in ("source_loading_mol_kg", "standard_uncertainty_mol_kg",
                     "detection_limit_mol_kg", "quantification_limit_mol_kg"):
            value = getattr(self, name)
            if name != "source_loading_mol_kg" and value is None:
                continue
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or (name != "source_loading_mol_kg" and value < 0.)):
                raise ValueError(f"{name} must be finite; reported statistics are nonnegative")
            object.__setattr__(self, name, float(value))


@dataclass(frozen=True, slots=True)
class AdsorptionState:
    basis: AdsorptionBasis
    partial_pressures_pa: np.ndarray
    temperature_k: float
    site_loadings_mol_kg: np.ndarray
    site_pressure_derivatives_mol_kg_pa: np.ndarray | None = None
    site_temperature_derivatives_mol_kg_k: np.ndarray | None = None
    source_observations: tuple[tuple[AdsorptionSourceObservation, ...], ...] = ()
    propagated_standard_uncertainty_mol_kg: np.ndarray | None = None
    uncertainty_semantics: str = "unqualified"
    uncertainty_source_ids: tuple[str, ...] = ()

    def __post_init__(self):
        finite(self.temperature_k, "temperature", positive=True)
        species = len(self.basis.species)
        pressures = np.array(self.partial_pressures_pa, dtype=float, copy=True)
        loading = np.array(self.site_loadings_mol_kg, dtype=float, copy=True)
        if pressures.shape != (species,) or not np.all(np.isfinite(pressures)) or np.any(pressures < 0):
            raise ValueError("State partial pressures must match the declared species order")
        if (loading.ndim != 2 or loading.shape[0] != species or loading.shape[1] < 1
                or not np.all(np.isfinite(loading))
                or (self.basis.loading_definition == "absolute" and np.any(loading < 0))):
            raise ValueError("Site loadings must match species/site axes; absolute uptake cannot be negative")
        for name, values, shape in (
            ("partial_pressures_pa", pressures, (species,)),
            ("site_loadings_mol_kg", loading, loading.shape),
            ("site_pressure_derivatives_mol_kg_pa", self.site_pressure_derivatives_mol_kg_pa,
             (loading.shape[1], species, species)),
            ("site_temperature_derivatives_mol_kg_k", self.site_temperature_derivatives_mol_kg_k, loading.shape),
        ):
            if values is None:
                continue
            array = np.array(values, dtype=float, copy=True)
            if array.shape != shape or not np.all(np.isfinite(array)):
                raise ValueError("Adsorption derivative axes or values are invalid")
            array = immutable_array(array, name=name)
            object.__setattr__(self, name, array)
        if not isinstance(self.source_observations, (tuple, list)):
            raise ValueError("Source observations must be a sequence indexed by adsorption site")
        observations = tuple(self.source_observations)
        if observations and len(observations) != loading.shape[1]:
            raise ValueError("Source observation receipts must match the site axis")
        normalized_observations = []
        for site_index, site in enumerate(observations):
            if not isinstance(site, (tuple, list)):
                raise ValueError("Source observations must be a sequence of per-site receipts")
            receipts = tuple(site)
            if not receipts or any(type(item) is not AdsorptionSourceObservation for item in receipts):
                raise ValueError("Each source site needs immutable source-row receipt objects")
            by_species = {}
            for item in receipts:
                if item.species not in self.basis.species:
                    raise ValueError("Source observation species is absent from the adsorption basis")
                if (self.basis.loading_definition == "absolute"
                        and item.source_loading_mol_kg < 0.):
                    raise ValueError("Absolute-uptake source observations cannot be negative")
                by_species.setdefault(item.species, []).append(item)
            for source_species, species_receipts in by_species.items():
                if len({item.source_row for item in species_receipts}) != len(species_receipts):
                    raise ValueError("Source row identities must be unique within one site/species")
                if not math.isclose(sum(item.interpolation_weight for item in species_receipts),
                                    1., rel_tol=0., abs_tol=1e-12):
                    raise ValueError("Per-site/species source interpolation weights must sum to one")
                source_index = self.basis.species.index(source_species)
                reconstructed = sum(item.interpolation_weight*item.source_loading_mol_kg
                                    for item in species_receipts)
                if not math.isclose(reconstructed, loading[source_index, site_index],
                                    rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError("Weighted source-row loading does not match the site loading")
            normalized_observations.append(receipts)
        observations = tuple(normalized_observations)
        object.__setattr__(self, "source_observations", observations)
        uncertainty = self.propagated_standard_uncertainty_mol_kg
        if uncertainty is not None:
            array = np.array(uncertainty, dtype=float, copy=True)
            if (array.shape != (species,) or not np.all(np.isfinite(array))
                    or np.any(array < 0.)):
                raise ValueError("Propagated total-loading uncertainty must be a finite nonnegative species vector")
            array = immutable_array(array, name=name)
            object.__setattr__(self, "propagated_standard_uncertainty_mol_kg", array)
        if self.uncertainty_semantics not in {
                "unqualified", "reported_standard_uncertainty",
                "independent_standard_uncertainty", "covariance_matrix_propagated"}:
            raise ValueError("Declare uncertainty semantics without inferring independence")
        if uncertainty is not None and self.uncertainty_semantics != "covariance_matrix_propagated":
            raise ValueError(
                "A propagated state uncertainty array requires covariance-derived semantics"
            )
        if (self.uncertainty_semantics == "covariance_matrix_propagated") != (uncertainty is not None):
            raise ValueError("Covariance-propagated loading requires its explicit propagated uncertainty array")
        sources = tuple(self.uncertainty_source_ids)
        if any(not isinstance(value, str) or not value.strip() for value in sources):
            raise ValueError("Uncertainty source identities must be nonempty text")
        if self.uncertainty_semantics != "unqualified" and not sources:
            raise ValueError("Qualified state uncertainty requires source/dependence evidence identities")
        object.__setattr__(self, "uncertainty_source_ids", sources)

    @property
    def loadings_mol_kg(self):
        values = self.site_loadings_mol_kg.sum(axis=1)
        values = immutable_array(values, name="adsorption loadings")
        return values


class AdsorptionProvider(Protocol):
    @property
    def basis(self) -> AdsorptionBasis: ...
    def equilibrium(self, partial_pressures_pa, temperature_k: float) -> AdsorptionState: ...


@dataclass(frozen=True, slots=True)
class ExtendedLangmuirIsotherm:
    """Competitive multicomponent Langmuir equilibrium on explicit sites.

    `affinity_pa_inv(T)` returns a species-by-site matrix. The equilibrium
    loading on each site is shared competitively among all declared species.
    This idealized closure requires absolute uptake and remains caller
    parameterized; it is not a universal porous-material equation of state.
    """

    basis: AdsorptionBasis
    domain: AdsorptionDomain
    site_capacity_mol_kg: np.ndarray
    affinity_pa_inv: object
    evidence_id: str
    affinity_temperature_derivative_pa_inv_k: object | None = None

    def __post_init__(self):
        if self.basis.loading_definition != "absolute":
            raise ValueError("Competitive Langmuir loading requires an absolute-uptake basis")
        if not callable(self.affinity_pa_inv):
            raise TypeError("Supply a temperature-dependent species-by-site affinity provider")
        if (self.affinity_temperature_derivative_pa_inv_k is not None
                and not callable(self.affinity_temperature_derivative_pa_inv_k)):
            raise TypeError("Affinity temperature derivative must be callable when supplied")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify the material-specific isotherm evidence or synthetic fixture")
        raw_capacity = np.asarray(self.site_capacity_mol_kg)
        if raw_capacity.dtype.kind not in "iuf":
            raise ValueError("Site capacities must be real numeric amounts")
        capacity = np.asarray(raw_capacity, dtype=float)
        if (capacity.ndim != 1 or capacity.size == 0 or not np.all(np.isfinite(capacity))
                or np.any(capacity <= 0)):
            raise ValueError("Each declared site needs a finite positive absolute capacity")
        object.__setattr__(self, "site_capacity_mol_kg",
                           immutable_array(capacity, name="site_capacity_mol_kg"))

    def _affinity(self, temperature_k):
        species = len(self.basis.species)
        sites = len(self.site_capacity_mol_kg)
        raw_input = np.asarray(self.affinity_pa_inv(temperature_k))
        if raw_input.dtype.kind not in "iuf":
            raise ValueError("Affinity values must be real numeric quantities")
        raw = np.asarray(raw_input, dtype=float)
        if raw.shape != (species, sites) or not np.all(np.isfinite(raw)) or np.any(raw < 0):
            raise ValueError("Affinity must be a finite nonnegative species-by-site matrix")
        return raw

    def equilibrium(self, partial_pressures_pa, temperature_k: float) -> AdsorptionState:
        temperature = finite(temperature_k, "temperature", positive=True)
        if isinstance(partial_pressures_pa, (bool, np.bool_)):
            raise ValueError("Partial pressures must be real numeric values")
        pressures = np.asarray(partial_pressures_pa)
        if pressures.dtype.kind not in "iuf" or pressures.shape != (len(self.basis.species),):
            raise ValueError("Partial pressures must match the declared species order")
        pressures = np.asarray(pressures, dtype=float)
        self.domain.require_state(pressures, temperature)
        affinity = self._affinity(temperature)
        denominator = 1.0 + pressures @ affinity
        if not np.all(np.isfinite(denominator)):
            raise ValueError("Competitive site denominators exceed finite arithmetic")
        loading = (self.site_capacity_mol_kg[None, :] * affinity * pressures[:, None]
                   / denominator[None, :])
        # d q_i / d p_k for each site, retaining the declared species ordering.
        derivative = np.empty((len(self.site_capacity_mol_kg), len(pressures), len(pressures)))
        for site in range(len(self.site_capacity_mol_kg)):
            b = affinity[:, site]
            denominator_site = denominator[site]
            derivative[site] = self.site_capacity_mol_kg[site] * (
                np.diag(b / denominator_site)
                - np.outer(b * pressures, b) / denominator_site**2
            )
        temperature_derivative = None
        if self.affinity_temperature_derivative_pa_inv_k is not None:
            raw_db = np.asarray(self.affinity_temperature_derivative_pa_inv_k(temperature))
            if raw_db.dtype.kind not in "iuf":
                raise ValueError("Affinity temperature derivative must use real numeric quantities")
            db = np.asarray(raw_db, dtype=float)
            if db.shape != affinity.shape or not np.all(np.isfinite(db)):
                raise ValueError("Affinity temperature derivative has an invalid shape or nonfinite value")
            temperature_derivative = np.empty_like(loading)
            for site in range(len(self.site_capacity_mol_kg)):
                b, db_site = affinity[:, site], db[:, site]
                d = denominator[site]
                temperature_derivative[:, site] = (
                    self.site_capacity_mol_kg[site] * pressures
                    * (db_site*d - b*np.dot(pressures, db_site)) / d**2
                )
        return AdsorptionState(
            self.basis, pressures, temperature, loading,
            site_pressure_derivatives_mol_kg_pa=derivative,
            site_temperature_derivatives_mol_kg_k=temperature_derivative,
        )


def loading_working_capacity(charged: AdsorptionState, discharged: AdsorptionState):
    """Signed loading difference; no unobserved free-gas/pore-volume correction."""
    charged.basis.require_compatible(discharged.basis)
    capacity = charged.loadings_mol_kg - discharged.loadings_mol_kg
    return immutable_array(capacity, name="working adsorption capacity")
