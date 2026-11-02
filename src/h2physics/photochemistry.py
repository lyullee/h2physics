"""Photon-accounted H2 production and finite prescribed-efficiency conversion.

Original optical/stoichiometric composition using the existing reaction core.
Scientific definitions: https://doi.org/10.1351/PAC-REC-09-09-36
SI constants: https://www.bipm.org/en/publications/si-brochure
No catalyst kinetics, optical coefficients or reported quantum-yield fit is bundled.
"""

import hashlib
import math
from dataclasses import dataclass, field as dataclass_field, fields, is_dataclass

import numpy as np
from scipy.constants import Avogadro, Planck, speed_of_light

from .core import Origin, finite, immutable_array
from .reactions import (
    MolarEnthalpyProvider,
    ReactionConversion,
    StoichiometricReaction,
    conversion_heat_j,
)

MOLAR_PHOTON_ENERGY_FACTOR_J_M_PER_MOL = Planck*speed_of_light*Avogadro
ELECTRON_EQUIVALENTS_PER_H2 = 2.


def _array(value, name):
    raw = np.asarray(value)
    if raw.dtype.kind in {"b", "c"}:
        raise ValueError(f"{name} cannot contain booleans or complex values")
    array = np.array(value, dtype=float, copy=True)
    if array.ndim != 1 or not len(array) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite nonempty one-dimensional array")
    return immutable_array(array, name=name)


def _values(value, n, name, lower, upper=np.inf):
    raw = np.asarray(value)
    if raw.ndim == 0:
        finite(raw.item(), name)
        value = np.full(n, float(raw))
    result = _array(value, name)
    if result.shape != (n,) or np.any(result < lower) or np.any(result > upper):
        raise ValueError(f"{name} has an invalid band count or admissible range")
    return result


def _ids(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare source, geometry, catalyst, medium and boundary evidence identities")


def _fingerprint(value) -> str:
    """Content and object-lineage digest for nested photochemical receipts."""
    digest = hashlib.sha256()

    def add(item):
        if isinstance(item, np.ndarray):
            digest.update(b"array\0")
            digest.update(item.dtype.str.encode()+b"\0")
            digest.update(repr(item.shape).encode()+b"\0")
            digest.update(np.ascontiguousarray(item).tobytes())
        elif is_dataclass(item) and not isinstance(item, type):
            digest.update((type(item).__module__+"."+type(item).__qualname__).encode()+b"\0")
            digest.update(str(id(item)).encode()+b"\0")
            for definition in fields(item):
                if definition.name in {"_seal", "_issuer_token"}:
                    continue
                digest.update(definition.name.encode()+b"\0")
                add(getattr(item, definition.name))
        elif isinstance(item, dict) or hasattr(item, "items"):
            digest.update(b"mapping\0")
            for key, val in sorted(item.items(), key=lambda pair: repr(pair[0])):
                add(key)
                add(val)
        elif isinstance(item, (tuple, list)):
            digest.update(b"sequence\0")
            digest.update(str(len(item)).encode()+b"\0")
            for part in item:
                add(part)
        else:
            digest.update((type(item).__module__+"."+type(item).__qualname__).encode()+b"\0")
            digest.update(repr(item).encode("utf-8", errors="backslashreplace")+b"\0")

    add(value)
    return digest.hexdigest()


_PENDING_PHOTO_CONVERSION_TOKENS: set[object] = set()
_PENDING_PHOTO_OPERATION_TOKENS: set[object] = set()
_PENDING_PHOTO_GIBBS_TOKENS: set[object] = set()


def _issue_photo_conversion(**values):
    token = object()
    _PENDING_PHOTO_CONVERSION_TOKENS.add(token)
    try:
        return PhotoConversion(**values, _issuer_token=token)
    except Exception:
        _PENDING_PHOTO_CONVERSION_TOKENS.discard(token)
        raise


def _issue_photo_operation(**values):
    token = object()
    _PENDING_PHOTO_OPERATION_TOKENS.add(token)
    try:
        return PhotoOperationTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_PHOTO_OPERATION_TOKENS.discard(token)
        raise


def _issue_photo_gibbs_budget(**values):
    token = object()
    _PENDING_PHOTO_GIBBS_TOKENS.add(token)
    try:
        return PhotoGibbsEnergyBudget(**values, _issuer_token=token)
    except Exception:
        _PENDING_PHOTO_GIBBS_TOKENS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class PhotonSupply:
    """Immutable finite-band/line optical input at one declared incident plane.

    Bands have flat power density per wavelength; line inputs are discrete.
    Mean wavelength converts total optical power to exact photon amount for
    either declared representation, without a guessed source bandwidth.
    """

    representative_wavelength_m: np.ndarray
    incident_power_w: np.ndarray
    incident_photons_mol_s: np.ndarray
    wavelength_edges_m: np.ndarray | None
    geometry_id: str
    source_id: str
    representation: str

    def __post_init__(self):
        for name in ("representative_wavelength_m", "incident_power_w", "incident_photons_mol_s"):
            object.__setattr__(self, name, _array(getattr(self, name), name))
        n = len(self.incident_power_w)
        if (self.representative_wavelength_m.shape != (n,)
                or self.incident_photons_mol_s.shape != (n,)
                or np.any(self.representative_wavelength_m <= 0)
                or np.any(np.diff(self.representative_wavelength_m) <= 0)
                or np.any(self.incident_power_w < 0) or np.any(self.incident_photons_mol_s < 0)):
            raise ValueError("Optical wavelengths/powers/amounts have incompatible axes or signs")
        _ids(self.geometry_id, self.source_id)
        if self.representation not in {"flat-power-density-bands", "discrete-lines"}:
            raise ValueError("Declare the supplied optical spectral representation")
        if self.wavelength_edges_m is not None:
            edges = _array(self.wavelength_edges_m, "wavelength edges")
            if (self.representation != "flat-power-density-bands" or edges.shape != (n+1,)
                    or edges[0] <= 0 or np.any(np.diff(edges) <= 0)
                    or not np.array_equal((edges[:-1]+edges[1:])/2,
                                          self.representative_wavelength_m)):
                raise ValueError("Band edges and representative wavelengths do not agree")
            object.__setattr__(self, "wavelength_edges_m", edges)
        elif self.representation != "discrete-lines":
            raise ValueError("A finite-band spectrum needs explicit wavelength edges")
        expected = (self.incident_power_w*self.representative_wavelength_m
                    /MOLAR_PHOTON_ENERGY_FACTOR_J_M_PER_MOL)
        if not np.allclose(expected, self.incident_photons_mol_s, rtol=2e-15, atol=0.):
            raise ValueError("Incident photon amounts do not match the supplied optical power")

    @property
    def spectral_grid_sha256(self):
        """Wavelength/representation identity, independent of incident power."""
        digest = hashlib.sha256(self.representation.encode()+b"\0")
        for array in (self.representative_wavelength_m, self.wavelength_edges_m):
            digest.update(b"none" if array is None else np.asarray(array, dtype="<f8").tobytes())
            digest.update(b"\0")
        return digest.hexdigest()

    @property
    def content_sha256(self):
        digest = hashlib.sha256()
        for value in (self.representation, self.geometry_id, self.source_id):
            digest.update(value.encode()+b"\0")
        for array in (self.representative_wavelength_m, self.incident_power_w,
                      self.incident_photons_mol_s, self.wavelength_edges_m):
            digest.update(b"none" if array is None else np.asarray(array, dtype="<f8").tobytes())
            digest.update(b"\0")
        return digest.hexdigest()

    @classmethod
    def from_bands(cls, wavelength_edges_m, irradiance_w_m2_per_m, *,
                   illuminated_area_m2: float, geometry_id: str, source_id: str):
        edges = _array(wavelength_edges_m, "wavelength edges")
        if len(edges) < 2 or edges[0] <= 0 or np.any(np.diff(edges) <= 0):
            raise ValueError("Supply positive increasing finite wavelength-bin edges")
        density = _values(irradiance_w_m2_per_m, len(edges)-1, "spectral irradiance", 0.)
        area = finite(illuminated_area_m2, "illuminated projected area", positive=True)
        power = density*np.diff(edges)*area
        wavelength = (edges[:-1]+edges[1:])/2
        photons = power*wavelength/MOLAR_PHOTON_ENERGY_FACTOR_J_M_PER_MOL
        return cls(wavelength, power, photons, edges, geometry_id, source_id,
                   "flat-power-density-bands")

    @classmethod
    def from_nanometer_bands(cls, wavelength_edges_nm, irradiance_w_m2_per_nm, **kwargs):
        """Explicit nm→m and per-nm→per-m changes; no unknown bandwidth inference."""
        edges = _array(wavelength_edges_nm, "nanometre wavelength edges")
        density = _values(irradiance_w_m2_per_nm, len(edges)-1, "per-nm irradiance", 0.)
        return cls.from_bands(edges*1e-9, density*1e9, **kwargs)

    @classmethod
    def from_lines(cls, wavelength_m, optical_power_w, *, geometry_id: str, source_id: str):
        wavelength = _array(wavelength_m, "line wavelengths")
        power = _values(optical_power_w, len(wavelength), "line optical power", 0.)
        photons = power*wavelength/MOLAR_PHOTON_ENERGY_FACTOR_J_M_PER_MOL
        return cls(wavelength, power, photons, None, geometry_id, source_id, "discrete-lines")


@dataclass(frozen=True, slots=True)
class PhotoConditions:
    catalyst_id: str
    medium_id: str
    catalyst_mass_kg: float
    temperature_k: float
    pressure_pa_absolute: float
    geometry_id: str
    evidence_id: str

    def __post_init__(self):
        _ids(self.catalyst_id, self.medium_id, self.geometry_id, self.evidence_id)
        for name in ("catalyst_mass_kg", "temperature_k", "pressure_pa_absolute"):
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class BeerLambertPath:
    """Uniform nonscattering path, with constant alpha/reflectance in each band.

    Reflection is at the input plane. No diffuse scattering, multiple reflection,
    refraction, catalyst loading law or optical-to-reactor-area conversion is inferred.
    """

    depth_m: float
    absorption_coefficient_m_inv: np.ndarray
    reflectance: np.ndarray
    geometry_id: str
    evidence_id: str
    spectral_grid_sha256: str

    def __post_init__(self):
        if finite(self.depth_m, "optical path depth") < 0:
            raise ValueError("Optical path depth cannot be negative")
        alpha = _array(self.absorption_coefficient_m_inv, "absorption coefficients")
        reflection = _values(self.reflectance, len(alpha), "reflectance", 0., 1.)
        if np.any(alpha < 0):
            raise ValueError("Absorption coefficients cannot be negative")
        if self.depth_m > 1 and np.any(alpha > np.finfo(float).max/self.depth_m):
            raise ValueError("Optical depth exceeds the finite numerical representation")
        object.__setattr__(self, "absorption_coefficient_m_inv", alpha)
        object.__setattr__(self, "reflectance", reflection)
        _ids(self.geometry_id, self.evidence_id)
        if (not isinstance(self.spectral_grid_sha256, str) or len(self.spectral_grid_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.spectral_grid_sha256)):
            raise ValueError("Bind optical coefficients to an explicit wavelength grid and representation")

    @classmethod
    def uniform(cls, supply: PhotonSupply, *, depth_m, absorption_coefficient_m_inv,
                reflectance=0., evidence_id):
        n = len(supply.incident_power_w)
        return cls(depth_m, _values(absorption_coefficient_m_inv, n, "absorption", 0.),
                   _values(reflectance, n, "reflectance", 0., 1.), supply.geometry_id, evidence_id,
                   supply.spectral_grid_sha256)

    @property
    def absorbed_fraction(self):
        optical_depth = self.absorption_coefficient_m_inv*self.depth_m
        return (1-self.reflectance)*(-np.expm1(-optical_depth))

    @property
    def transmitted_fraction(self):
        return (1-self.reflectance)*np.exp(-self.absorption_coefficient_m_inv*self.depth_m)


@dataclass(frozen=True, slots=True)
class PhotonYield:
    """Electron-equivalent yield with its exact optical input and conditions.

    Values are mol productive electron equivalents per mol incident or absorbed
    photons. This level assumes at most one productive electron per absorbed
    photon. H2 requires two electron equivalents. Values are fractions, not %.
    """

    values: np.ndarray
    basis: str
    supply_sha256: str
    conditions: PhotoConditions
    evidence_id: str
    origin: Origin

    def __post_init__(self):
        values = _array(self.values, "quantum yield")
        if np.any(values < 0) or np.any(values > 1):
            raise ValueError("This single-electron photon model requires yield fractions in [0,1]")
        if self.basis not in {"incident_electron_equivalents", "absorbed_electron_equivalents"}:
            raise ValueError("Declare incident versus absorbed electron-equivalent yield")
        if (len(self.supply_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.supply_sha256)):
            raise ValueError("Bind the quantum yield to an actual photon supply fingerprint")
        _ids(self.evidence_id)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Unresolved yield meaning cannot drive a photochemical conversion")
        object.__setattr__(self, "values", values)

    @classmethod
    def bind(cls, supply: PhotonSupply, values, *, basis, conditions, evidence_id, origin):
        return cls(_values(values, len(supply.incident_power_w), "quantum yield", 0., 1.),
                   basis, supply.content_sha256, conditions, evidence_id, origin)


@dataclass(frozen=True, slots=True)
class PhotoRate:
    supply: PhotonSupply
    optical_path: BeerLambertPath
    quantum_yield: PhotonYield
    reflected_power_w: np.ndarray
    absorbed_power_w: np.ndarray
    transmitted_power_w: np.ndarray
    absorbed_photons_mol_s: np.ndarray
    productive_electrons_mol_s: np.ndarray
    energy_residual_w: np.ndarray
    photon_residual_mol_s: np.ndarray
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        for name in ("reflected_power_w", "absorbed_power_w", "transmitted_power_w",
                     "absorbed_photons_mol_s", "productive_electrons_mol_s",
                     "energy_residual_w", "photon_residual_mol_s"):
            object.__setattr__(self, name, _array(getattr(self, name), name))
        n = len(self.supply.incident_power_w)
        names = ("reflected_power_w", "absorbed_power_w", "transmitted_power_w",
                 "absorbed_photons_mol_s", "productive_electrons_mol_s",
                 "energy_residual_w", "photon_residual_mol_s")
        if (self.optical_path.absorption_coefficient_m_inv.shape != (n,)
                or self.quantum_yield.values.shape != (n,)
                or any(getattr(self, name).shape != (n,) for name in names)):
            raise ValueError("Photochemical result fields must share the actual input band axes")
        if (self.supply.content_sha256 != self.quantum_yield.supply_sha256
                or self.supply.geometry_id != self.optical_path.geometry_id
                or self.supply.geometry_id != self.quantum_yield.conditions.geometry_id):
            raise ValueError("Photochemical result identities differ from their source objects")
        if self.supply.spectral_grid_sha256 != self.optical_path.spectral_grid_sha256:
            raise ValueError("Photochemical optical spectral grid/representation differs")
        p, photons = self.supply.incident_power_w, self.supply.incident_photons_mol_s
        a, t, r = (self.optical_path.absorbed_fraction,
                   self.optical_path.transmitted_fraction, self.optical_path.reflectance)
        electrons = (photons*self.quantum_yield.values
            if self.quantum_yield.basis == "incident_electron_equivalents"
            else photons*a*self.quantum_yield.values)
        expected = (p*r, p*a, p*t, photons*a, electrons, p*(r+a+t-1), photons*(r+a+t-1))
        if any(not np.array_equal(getattr(self, name), value)
               for name, value in zip(names, expected, strict=True)):
            raise ValueError("Photochemical result does not match its actual optical/yield inputs")
        object.__setattr__(self, "_seal", _fingerprint(self))

    def require_current(self):
        if _fingerprint(self) != self._seal:
            raise ValueError("Photochemical rate or one of its input objects changed after calculation")
        return self

    @property
    def photon_budget_admitted(self):
        self.require_current()
        return bool(self.quantum_yield.basis != "incident_electron_equivalents" or np.all(
            self.quantum_yield.values <= self.optical_path.absorbed_fraction+8*np.finfo(float).eps))

    @property
    def hydrogen_mol_s(self):
        self.require_current()
        return float(np.sum(self.productive_electrons_mol_s)/ELECTRON_EQUIVALENTS_PER_H2)

    @property
    def specific_hydrogen_mol_kg_s(self):
        self.require_current()
        return self.hydrogen_mol_s/self.quantum_yield.conditions.catalyst_mass_kg


class PhotoAdmissibilityError(ValueError):
    def __init__(self, message, result):
        self.result = result
        super().__init__(message)


def photon_hydrogen_rate(supply: PhotonSupply, path: BeerLambertPath,
                         quantum_yield: PhotonYield) -> PhotoRate:
    """Resolve each declared band/line; do not attenuate incident AQY twice."""
    if supply.geometry_id != path.geometry_id or supply.geometry_id != quantum_yield.conditions.geometry_id:
        raise ValueError("Light plane, optical path and catalyst geometry identities differ")
    if supply.content_sha256 != quantum_yield.supply_sha256:
        raise ValueError("Yield was qualified for a different optical input; rebind with explicit evidence")
    if supply.spectral_grid_sha256 != path.spectral_grid_sha256:
        raise ValueError("Optical coefficients belong to another spectral grid/representation")
    if (path.absorption_coefficient_m_inv.shape != supply.incident_power_w.shape
            or quantum_yield.values.shape != supply.incident_power_w.shape):
        raise ValueError("Optical/yield band axes do not match the photon supply")
    absorbed, transmitted = path.absorbed_fraction, path.transmitted_fraction
    power, photons = supply.incident_power_w, supply.incident_photons_mol_s
    productive = (photons*quantum_yield.values if quantum_yield.basis == "incident_electron_equivalents"
                  else photons*absorbed*quantum_yield.values)
    result = PhotoRate(supply, path, quantum_yield, power*path.reflectance,
        power*absorbed, power*transmitted, photons*absorbed, productive,
        power*(path.reflectance+absorbed+transmitted-1),
        photons*(path.reflectance+absorbed+transmitted-1))
    # The one-electron assumption applies in every declared constant-response
    # band, including a dark band; it is not just an integrated positivity gate.
    if not result.photon_budget_admitted:
        raise PhotoAdmissibilityError("Incident yield exceeds absorbed-photon electron budget", result)
    return result


@dataclass(frozen=True, slots=True)
class SteadyPhotoWindow:
    start_s: float
    end_s: float
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        if finite(self.start_s, "start time") >= finite(self.end_s, "end time"):
            raise ValueError("Steady photochemical exposure needs an increasing finite window")
        _ids(self.clock_id, self.evidence_id)

    @property
    def duration_s(self):
        return self.end_s-self.start_s


@dataclass(frozen=True, slots=True)
class PhotoConversion:
    rate: PhotoRate
    window: SteadyPhotoWindow
    conversion: ReactionConversion
    incident_optical_energy_j: float
    absorbed_optical_energy_j: float
    reaction_enthalpy_change_j: float | None
    required_isothermal_heat_j: float | None
    energy_basis_id: str | None
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PHOTO_CONVERSION_TOKENS:
            raise ValueError("Photochemical conversions are issued only by the finite exposure function")
        _PENDING_PHOTO_CONVERSION_TOKENS.remove(self._issuer_token)
        if type(self.rate) is not PhotoRate or type(self.window) is not SteadyPhotoWindow:
            raise TypeError("A conversion must retain its computed rate and declared window")
        self.rate.require_current()
        if type(self.conversion) is not ReactionConversion:
            raise TypeError("A conversion must retain the shared stoichiometric reaction result")
        for name in ("incident_optical_energy_j", "absorbed_optical_energy_j"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError(f"{name} cannot be negative")
        duration = self.window.duration_s
        incident = float(np.sum(self.rate.supply.incident_power_w)*duration)
        absorbed = float(np.sum(self.rate.absorbed_power_w)*duration)
        if (not math.isclose(self.incident_optical_energy_j, incident, rel_tol=2e-14, abs_tol=1e-15)
                or not math.isclose(self.absorbed_optical_energy_j, absorbed,
                                    rel_tol=2e-14, abs_tol=1e-15)):
            raise ValueError("Photochemical conversion energy totals do not reconstruct from its rate/window")
        if self.reaction_enthalpy_change_j is None:
            if self.required_isothermal_heat_j is not None or self.energy_basis_id is not None:
                raise ValueError("Caloric heat and basis must be absent together when no provider was used")
        else:
            finite(self.reaction_enthalpy_change_j, "reaction enthalpy change")
            finite(self.required_isothermal_heat_j, "required isothermal heat")
            if not isinstance(self.energy_basis_id, str) or not self.energy_basis_id.strip():
                raise ValueError("Computed caloric results require their declared enthalpy basis")
            if not math.isclose(self.required_isothermal_heat_j,
                                self.reaction_enthalpy_change_j-absorbed,
                                rel_tol=2e-14, abs_tol=1e-12):
                raise ValueError("Caloric boundary heat does not close against absorbed optical energy")
        object.__setattr__(self, "_seal", _fingerprint(self))

    def require_current(self):
        self.rate.require_current()
        if _fingerprint(self) != self._seal:
            raise ValueError("Photochemical conversion or one of its retained inputs changed after issue")
        return self


@dataclass(frozen=True, slots=True)
class PhotoGibbsEnergyBudget:
    """Photon-only necessary energy bound along one finite reaction extent.

    The caller supplies reaction affinities (J/mol reaction) at monotone extent
    samples from its thermodynamic model. The integral uses piecewise-linear
    interpolation in extent. It is a necessary photon-energy check only; a pass
    does not establish usable radiation exergy, kinetics, or reactor feasibility.
    """

    conversion: PhotoConversion
    reaction_extent_mol: np.ndarray
    reaction_gibbs_j_mol: np.ndarray
    thermodynamic_state_id: str
    thermodynamic_source_id: str
    path_evidence_id: str
    energy_tolerance_j: float = 1e-12
    reaction_gibbs_change_j: float = dataclass_field(default=0., init=False)
    absorbed_optical_energy_j: float = dataclass_field(default=0., init=False)
    photon_energy_margin_j: float = dataclass_field(default=0., init=False)
    photon_energy_necessary_condition_met: bool = dataclass_field(default=False, init=False)
    sampled_species_amounts_mol: np.ndarray = dataclass_field(default_factory=lambda: np.empty((0, 0)), init=False,
                                                               repr=False, compare=False)
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PHOTO_GIBBS_TOKENS:
            raise ValueError("Photo Gibbs budgets are issued only by assess_photo_gibbs_energy")
        _PENDING_PHOTO_GIBBS_TOKENS.remove(self._issuer_token)
        if type(self.conversion) is not PhotoConversion:
            raise TypeError("Retain one issued finite photochemical conversion")
        self.conversion.require_current()
        extents = _array(self.reaction_extent_mol, "reaction extent path")
        affinities = _array(self.reaction_gibbs_j_mol, "reaction Gibbs path")
        conversion = self.conversion.conversion
        if (len(extents) < 2 or extents.shape != affinities.shape
                or not math.isclose(float(extents[0]), 0., rel_tol=0., abs_tol=0.)
                or not math.isclose(float(extents[-1]), conversion.extent_mol,
                                    rel_tol=1e-12, abs_tol=1e-14)):
            raise ValueError("Gibbs path samples must span the exact finite conversion from zero extent")
        direction = math.copysign(1., conversion.extent_mol)
        if conversion.extent_mol == 0. or np.any(direction*np.diff(extents) <= 0.):
            raise ValueError("Gibbs path extents must increase strictly in the conversion direction")
        reaction = conversion.reaction
        amounts = np.stack([
            conversion.initial_mol + extent*np.asarray(reaction.coefficients, dtype=float)
            for extent in extents
        ])
        initial_scale = max(np.finfo(float).tiny, float(np.max(conversion.initial_mol)))
        tolerance = 1e-12*initial_scale
        if np.any(amounts < -tolerance):
            raise ValueError("A Gibbs path sample leaves the admitted finite species inventory")
        amounts = immutable_array(np.maximum(amounts, 0.), name="sampled species amounts")
        if not np.allclose(amounts[-1], conversion.final_mol, rtol=1e-12, atol=tolerance):
            raise ValueError("Gibbs path endpoint does not match the issued conversion inventory")
        conditions = self.conversion.rate.quantum_yield.conditions
        _ids(self.thermodynamic_state_id, self.thermodynamic_source_id, self.path_evidence_id)
        if self.thermodynamic_state_id != conditions.evidence_id:
            raise ValueError("Gibbs path state identity differs from the conversion's declared condition evidence")
        energy_tolerance = finite(self.energy_tolerance_j, "photon energy comparison tolerance")
        if energy_tolerance < 0.:
            raise ValueError("Photon energy comparison tolerance cannot be negative")
        integrated = math.fsum(
            0.5*(float(affinities[i])+float(affinities[i+1]))
            * (float(extents[i+1])-float(extents[i]))
            for i in range(len(extents)-1)
        )
        absorbed = self.conversion.absorbed_optical_energy_j
        required = max(0., integrated)
        margin = absorbed-required
        object.__setattr__(self, "reaction_extent_mol", extents)
        object.__setattr__(self, "reaction_gibbs_j_mol", affinities)
        object.__setattr__(self, "reaction_gibbs_change_j", integrated)
        object.__setattr__(self, "absorbed_optical_energy_j", absorbed)
        object.__setattr__(self, "photon_energy_margin_j", margin)
        object.__setattr__(self, "photon_energy_necessary_condition_met",
                           required <= absorbed+energy_tolerance)
        object.__setattr__(self, "sampled_species_amounts_mol", amounts)
        object.__setattr__(self, "_seal", _fingerprint(self))

    @property
    def minimum_photon_energy_required_j(self) -> float:
        """Positive integrated Gibbs increase; not an exergy or efficiency result."""
        return max(0., self.reaction_gibbs_change_j)

    def require_current(self):
        self.conversion.require_current()
        if _fingerprint(self) != self._seal:
            raise ValueError("Photo Gibbs budget or its thermodynamic path changed after issue")
        return self


def assess_photo_gibbs_energy(conversion: PhotoConversion, *, reaction_extent_mol,
                              reaction_gibbs_j_mol, thermodynamic_state_id: str,
                              thermodynamic_source_id: str, path_evidence_id: str,
                              energy_tolerance_j: float = 1e-12) -> PhotoGibbsEnergyBudget:
    """Integrate caller reaction affinity over the exact finite photochemical extent.

    ``reaction_gibbs_j_mol`` is ΔrG at each sampled composition along the path;
    the caller owns chemical-potential provenance, phase/mixture model, and path
    resolution. This function only performs a piecewise-linear extent integral.
    """
    return _issue_photo_gibbs_budget(
        conversion=conversion,
        reaction_extent_mol=reaction_extent_mol,
        reaction_gibbs_j_mol=reaction_gibbs_j_mol,
        thermodynamic_state_id=thermodynamic_state_id,
        thermodynamic_source_id=thermodynamic_source_id,
        path_evidence_id=path_evidence_id,
        energy_tolerance_j=energy_tolerance_j,
    )


class PhotoInventoryError(ValueError):
    def __init__(self, message, *, rate, window, demanded_extent_mol):
        self.rate, self.window = rate, window
        self.demanded_extent_mol = demanded_extent_mol
        super().__init__(message)


class PhotoOperationError(ValueError):
    """A finite staged photochemical operation failed after a retained prefix."""

    def __init__(self, message, *, completed_segments, failed_rate, failed_window, cause):
        self.completed_segments = tuple(completed_segments)
        self.failed_rate = failed_rate
        self.failed_window = failed_window
        self.cause = cause
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PhotoOperationTrace:
    """Sequential piecewise-constant photon exposures over one finite reaction.

    Each segment keeps its original spectrum/yield/window and reaction receipt.
    This composition supplies no kinetics, dynamic optics, or automatic light
    shutoff; all changes occur only at caller-declared adjacent segment edges.
    """

    reaction: StoichiometricReaction
    hydrogen_species_id: str
    clock_id: str
    segments: tuple[PhotoConversion, ...]
    initial_mol: np.ndarray
    final_mol: np.ndarray
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PHOTO_OPERATION_TOKENS:
            raise ValueError("Photochemical operation traces are issued only by run_photochemical_operation")
        _PENDING_PHOTO_OPERATION_TOKENS.remove(self._issuer_token)
        segments = tuple(self.segments)
        if type(self.reaction) is not StoichiometricReaction:
            raise TypeError("A photo operation must retain one exact stoichiometric reaction")
        if not isinstance(self.hydrogen_species_id, str) or not self.hydrogen_species_id.strip():
            raise ValueError("Declare the molecular-H2 product identity")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip() or not segments:
            raise ValueError("A photo operation needs segments and one absolute clock identity")
        if any(type(segment) is not PhotoConversion for segment in segments):
            raise TypeError("Photo operation segments must be original PhotoConversion objects")
        product_index = next((index for index, species in enumerate(self.reaction.species)
                              if species.identifier == self.hydrogen_species_id), None)
        if product_index is None:
            raise ValueError("The declared molecular-H2 product is absent from the reaction")
        product = self.reaction.species[product_index]
        coefficient = self.reaction.coefficients[product_index]
        if dict(product.elements) != {"H": 2} or product.charge != 0 or coefficient <= 0:
            raise ValueError("The selected operation product must be neutral molecular H2")
        first = segments[0]
        if first.window.clock_id != self.clock_id:
            raise ValueError("The first exposure window does not share the operation clock")
        expected_initial = self.reaction.amounts(dict(zip(
            (species.identifier for species in self.reaction.species),
            np.asarray(self.initial_mol, dtype=float), strict=True)))
        if not np.array_equal(first.conversion.initial_mol, expected_initial):
            raise ValueError("The first segment does not start from the declared operation inventory")
        previous = first
        for segment in segments:
            segment.require_current()
            if (type(segment.rate) is not PhotoRate
                    or type(segment.window) is not SteadyPhotoWindow
                    or not segment.rate.photon_budget_admitted):
                raise ValueError("Every segment must retain an admitted photon rate and finite window")
            if segment.conversion.reaction is not self.reaction:
                raise ValueError("Every segment must retain the operation's exact reaction object")
            if segment.window.clock_id != self.clock_id:
                raise ValueError("Every exposure segment must share the operation clock")
            if segment.rate.hydrogen_mol_s < 0:
                raise ValueError("Hydrogen production rate cannot be negative")
            expected_extent = segment.rate.hydrogen_mol_s * segment.window.duration_s / coefficient
            if not math.isclose(segment.conversion.extent_mol, expected_extent,
                                rel_tol=2e-13, abs_tol=1e-18):
                raise ValueError("Segment conversion does not follow its retained photon rate and window")
            expected_incident = float(np.sum(segment.rate.supply.incident_power_w)
                                      * segment.window.duration_s)
            expected_absorbed = float(np.sum(segment.rate.absorbed_power_w)
                                      * segment.window.duration_s)
            if (not math.isclose(segment.incident_optical_energy_j, expected_incident,
                                 rel_tol=2e-14, abs_tol=1e-15)
                    or not math.isclose(segment.absorbed_optical_energy_j, expected_absorbed,
                                        rel_tol=2e-14, abs_tol=1e-15)):
                raise ValueError("Segment optical-energy totals do not reconstruct from its photon rate")
            if segment is not first and not np.array_equal(
                    segment.conversion.initial_mol, previous.conversion.final_mol):
                raise ValueError("Segment inventories are not continuous across the operation")
            if segment is not first and segment.window.start_s != previous.window.end_s:
                raise ValueError("Photon windows must be adjacent; represent dark intervals explicitly")
            previous = segment
        final = np.asarray(self.final_mol, dtype=float)
        if final.shape != previous.conversion.final_mol.shape or not np.array_equal(
                final, previous.conversion.final_mol):
            raise ValueError("Operation endpoint does not match its final retained conversion")
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "initial_mol", immutable_array(expected_initial, name="photo initial inventory"))
        object.__setattr__(self, "final_mol", immutable_array(final, name="photo final inventory"))
        object.__setattr__(self, "_seal", _fingerprint(self))

    def require_current(self):
        for segment in self.segments:
            segment.require_current()
        if _fingerprint(self) != self._seal:
            raise ValueError("Photochemical operation trace changed after issue")
        return self

    @property
    def incident_optical_energy_j(self) -> float:
        self.require_current()
        return math.fsum(segment.incident_optical_energy_j for segment in self.segments)

    @property
    def absorbed_optical_energy_j(self) -> float:
        self.require_current()
        return math.fsum(segment.absorbed_optical_energy_j for segment in self.segments)

    @property
    def reaction_enthalpy_change_j(self) -> float | None:
        self.require_current()
        values = tuple(segment.reaction_enthalpy_change_j for segment in self.segments)
        return None if any(value is None for value in values) else math.fsum(values)

    @property
    def required_isothermal_heat_j(self) -> float | None:
        self.require_current()
        values = tuple(segment.required_isothermal_heat_j for segment in self.segments)
        return None if any(value is None for value in values) else math.fsum(values)


def run_photochemical_operation(segments, *, reaction: StoichiometricReaction,
                                initial_mol, hydrogen_species_id: str,
                                enthalpy: MolarEnthalpyProvider | None = None) -> PhotoOperationTrace:
    """Apply explicit adjacent photon windows to one finite stoichiometric batch.

    Each item is ``(PhotoRate, SteadyPhotoWindow)``. Spectra, optical paths,
    yields and conditions may change between caller-defined windows. Chemistry
    remains owned by ``StoichiometricReaction``. Inventory failure preserves
    every completed segment and the original failure as ``PhotoOperationError``.
    """
    if type(reaction) is not StoichiometricReaction:
        raise TypeError("Supply one admitted StoichiometricReaction")
    rows = tuple(segments)
    if not rows:
        raise ValueError("A staged photochemical operation needs at least one segment")
    if any(not isinstance(row, (tuple, list)) or len(row) != 2
           or type(row[0]) is not PhotoRate or type(row[1]) is not SteadyPhotoWindow
           for row in rows):
        raise TypeError("Each photochemical segment must contain a PhotoRate and SteadyPhotoWindow")
    clock_id = rows[0][1].clock_id
    for index, (_, window) in enumerate(rows):
        if window.clock_id != clock_id:
            raise ValueError("All exposure windows must share one absolute clock")
        if index and window.start_s != rows[index-1][1].end_s:
            raise ValueError("Exposure windows must be adjacent; include explicit dark windows")
    product_index = next((index for index, species in enumerate(reaction.species)
                          if species.identifier == hydrogen_species_id), None)
    if product_index is None:
        raise ValueError("The declared molecular-H2 product is absent from the reaction")
    coefficient = reaction.coefficients[product_index]
    species = reaction.species[product_index]
    if dict(species.elements) != {"H": 2} or species.charge != 0 or coefficient <= 0:
        raise ValueError("The selected operation product must be neutral molecular H2")
    current = reaction.amounts(initial_mol)
    first_initial = current.copy()
    completed = []
    for rate, window in rows:
        try:
            conversion = convert_photon_exposure(
                rate, window, reaction=reaction,
                initial_mol=dict(zip((item.identifier for item in reaction.species),
                                     current, strict=True)),
                hydrogen_species_id=hydrogen_species_id, enthalpy=enthalpy,
            )
        except PhotoInventoryError as error:
            raise PhotoOperationError(
                "Photochemical inventory failed; completed segment prefix is retained",
                completed_segments=completed, failed_rate=rate,
                failed_window=window, cause=error,
            ) from error
        completed.append(conversion)
        current = conversion.conversion.final_mol.copy()
    return _issue_photo_operation(
        reaction=reaction, hydrogen_species_id=hydrogen_species_id, clock_id=clock_id,
        segments=tuple(completed), initial_mol=first_initial, final_mol=current,
    )


def convert_photon_exposure(rate: PhotoRate, window: SteadyPhotoWindow, *,
                            reaction: StoichiometricReaction, initial_mol,
                            hydrogen_species_id: str,
                            enthalpy: MolarEnthalpyProvider | None = None) -> PhotoConversion:
    """Fixed spectrum/yield/path/temperature finite batch through the shared core.

    Extent is constrained by supplied quantum yield, not predicted kinetics.
    An exhausted feed rejects the requested window; light/valves are not
    silently stopped and extent is not capped to available reactants.
    """
    if not rate.photon_budget_admitted:
        raise PhotoAdmissibilityError("Rejected optical/yield diagnostics cannot drive conversion", rate)
    index = next((i for i, s in enumerate(reaction.species) if s.identifier == hydrogen_species_id), None)
    if index is None:
        raise ValueError("Declare the reaction's molecular-H2 product species")
    species, coefficient = reaction.species[index], reaction.coefficients[index]
    if dict(species.elements) != {"H": 2} or species.charge != 0 or coefficient <= 0:
        raise ValueError("The selected product must be neutral molecular H2 with positive coefficient")
    extent = rate.hydrogen_mol_s*window.duration_s/coefficient
    try:
        conversion = reaction.convert(initial_mol, extent)
    except ValueError as error:
        raise PhotoInventoryError("Finite photochemical inventory rejects the requested exposure",
            rate=rate, window=window, demanded_extent_mol=extent) from error
    incident = float(np.sum(rate.supply.incident_power_w)*window.duration_s)
    absorbed = float(np.sum(rate.absorbed_power_w)*window.duration_s)
    heat, boundary, basis = None, None, None
    if enthalpy is not None:
        conditions = rate.quantum_yield.conditions
        heat = conversion_heat_j(conversion, enthalpy,
            inlet_temperature_k=conditions.temperature_k,
            outlet_temperature_k=conditions.temperature_k,
            pressure_pa=conditions.pressure_pa_absolute)
        # Constant P, no shaft/kinetic work: Hout-Hin = absorbed optical + heat.
        boundary, basis = heat-absorbed, enthalpy.basis_id
    return _issue_photo_conversion(
        rate=rate, window=window, conversion=conversion,
        incident_optical_energy_j=incident, absorbed_optical_energy_j=absorbed,
        reaction_enthalpy_change_j=heat, required_isothermal_heat_j=boundary,
        energy_basis_id=basis,
    )
