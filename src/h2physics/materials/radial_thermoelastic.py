"""Axisymmetric thermoelastic response to caller-supplied radial temperatures.

The calculation assumes a long homogeneous isotropic cylinder, small strain,
constant properties and static axisymmetric loading. Finite-length end fields,
plasticity, creep and temperature-dependent material data are outside this model.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from dataclasses import field as dataclass_field

import numpy as np
from scipy.integrate import simpson, solve_bvp
from scipy.interpolate import PchipInterpolator

from ..core import finite, immutable_array
from .elastic_cylinder import (
    CylinderGeometry,
    CylinderPressureLoad,
    IsotropicThermoelasticMaterial,
)
from .transport import HydrogenCarrier

_PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_ISSUERS: set[object] = set()
_PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_HISTORY_ISSUERS: set[object] = set()


def _new_issuer(pending):
    token = object()
    pending.add(token)
    return token


def _hydrogen_mapping_key(profile):
    profile.require_current()
    return (
        profile.carrier,
        profile.concentration_basis_id,
        profile.reference_concentration_mol_m3,
        profile.linear_expansion_m3_per_mol,
        profile.reference_temperature_k,
    )


def _stress_field_source_fingerprint(field):
    geometry, load, material, temperature = (
        field.geometry, field.load, field.material, field.temperature,
    )
    digest = hashlib.sha256(repr((
        (id(geometry), id(load), id(material), id(temperature)),
        (geometry.inner_radius_m, geometry.outer_radius_m,
         geometry.end_condition, geometry.geometry_id),
        (load.internal_pressure_pa, load.external_pressure_pa,
         load.load_id, str(load.origin)),
        (material.young_modulus_pa, material.poisson_ratio,
         material.linear_expansion_per_k, material.material_id,
         material.property_evidence_id),
        (temperature.reference_temperature_k, temperature.profile_id,
         temperature.evidence_id),
    )).encode("utf-8"))
    for values in (temperature.radius_m, temperature.temperature_k):
        array = np.ascontiguousarray(values)
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def _von_mises_stress(radial, hoop, axial):
    return np.sqrt(
        0.5 * ((hoop - radial) ** 2 + (radial - axial) ** 2 + (axial - hoop) ** 2)
    )


@dataclass(frozen=True, slots=True)
class RadialTemperatureProfile:
    """Absolute temperatures sampled from the inner to outer cylinder surface."""

    radius_m: np.ndarray
    temperature_k: np.ndarray
    reference_temperature_k: float
    profile_id: str
    evidence_id: str

    def __post_init__(self):
        radii = np.array(self.radius_m, dtype=float, copy=True)
        temperatures = np.array(self.temperature_k, dtype=float, copy=True)
        reference = finite(self.reference_temperature_k, "reference temperature", positive=True)
        if radii.ndim != 1 or radii.size < 3 or not np.all(np.isfinite(radii)):
            raise ValueError("Temperature radii must be a finite vector of at least three nodes")
        if temperatures.shape != radii.shape or not np.all(np.isfinite(temperatures)):
            raise ValueError("One finite temperature is required at every radial node")
        if np.any(np.diff(radii) <= 0):
            raise ValueError("Temperature radii must be strictly increasing")
        if np.any(temperatures <= 0):
            raise ValueError("Temperatures must be positive absolute kelvin")
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ValueError("A temperature-profile identity is required")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("A temperature-profile evidence identity is required")
        radii = immutable_array(radii, name="temperature radii")
        temperatures = immutable_array(temperatures, name="temperature values")
        object.__setattr__(self, "radius_m", radii)
        object.__setattr__(self, "temperature_k", temperatures)
        object.__setattr__(self, "reference_temperature_k", reference)


@dataclass(frozen=True, slots=True)
class HydrogenConcentrationEigenstrainProfile:
    """Caller-mapped isotropic linear strain from radial hydrogen concentration.

    Concentration is in mol of the explicitly declared carrier entity per m3.
    ``linear_expansion_m3_per_mol`` maps a concentration difference to linear
    eigenstrain; no concentration basis, hydrogen partition or coefficient is
    inferred. The constant coefficient applies at the declared reference
    temperature only; callers must not assume it is temperature-independent
    outside that range without separate evidence.
    """

    carrier: HydrogenCarrier
    concentration_basis_id: str
    radius_m: np.ndarray
    concentration_mol_m3: np.ndarray
    reference_concentration_mol_m3: float
    linear_expansion_m3_per_mol: float
    reference_temperature_k: float
    profile_id: str
    evidence_id: str
    _signature: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.carrier) is not HydrogenCarrier:
            raise TypeError("Retain the exact hydrogen carrier and molar basis")
        for name in ("concentration_basis_id", "profile_id", "evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be an explicit nonblank identity")
            object.__setattr__(self, name, value.strip())
        radii = np.asarray(self.radius_m)
        concentration = np.asarray(self.concentration_mol_m3)
        if (radii.ndim != 1 or radii.size < 3 or radii.dtype.kind not in "iuf"
                or not np.all(np.isfinite(radii)) or np.any(np.diff(radii) <= 0)):
            raise ValueError("Hydrogen concentration radii must be finite and strictly increasing")
        if (concentration.ndim != 1 or concentration.shape != radii.shape
                or concentration.dtype.kind not in "iuf"
                or not np.all(np.isfinite(concentration)) or np.any(concentration < 0)):
            raise ValueError("Hydrogen concentration needs one finite nonnegative value per radius")
        reference = finite(self.reference_concentration_mol_m3,
                           "reference hydrogen concentration")
        if reference < 0:
            raise ValueError("Reference hydrogen concentration cannot be negative")
        coefficient = finite(self.linear_expansion_m3_per_mol,
                             "linear concentration-expansion coefficient")
        temperature = finite(self.reference_temperature_k,
                             "hydrogen strain reference temperature", positive=True)
        object.__setattr__(self, "radius_m", immutable_array(radii, name="hydrogen radii"))
        object.__setattr__(self, "concentration_mol_m3",
                           immutable_array(concentration, name="hydrogen concentration"))
        object.__setattr__(self, "reference_concentration_mol_m3", reference)
        object.__setattr__(self, "linear_expansion_m3_per_mol", coefficient)
        object.__setattr__(self, "reference_temperature_k", temperature)
        object.__setattr__(self, "_signature", self._current_signature())

    def _current_signature(self):
        digest = hashlib.sha256()
        digest.update(repr((self.carrier, self.concentration_basis_id,
                           self.reference_concentration_mol_m3,
                           self.linear_expansion_m3_per_mol,
                           self.reference_temperature_k, self.profile_id,
                           self.evidence_id)).encode("utf-8"))
        for values in (self.radius_m, self.concentration_mol_m3):
            digest.update(values.dtype.str.encode("ascii"))
            digest.update(repr(values.shape).encode("ascii"))
            digest.update(values.tobytes())
        return digest.hexdigest()

    def require_current(self):
        """Reject later source-array or reference-metadata edits."""
        if not self._signature or self._current_signature() != self._signature:
            raise ValueError("Hydrogen concentration eigenstrain profile changed after admission")
        return self

    def eigenstrain(self, concentration_mol_m3):
        """Return linear isotropic free strain at supplied mobile-entity concentration."""
        self.require_current()
        values = np.asarray(concentration_mol_m3, dtype=float)
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError("Hydrogen concentration must be finite and nonnegative")
        result = self.linear_expansion_m3_per_mol * (
            values - self.reference_concentration_mol_m3
        )
        if not np.all(np.isfinite(result)):
            raise ValueError("Hydrogen eigenstrain is nonfinite")
        return result


@dataclass(frozen=True, slots=True)
class RadialHydrogenEigenstrainResult:
    """Pressure/thermal baseline, combined stress and hydrogen-only stress increment."""

    baseline: RadialThermoelasticStressField
    combined: RadialThermoelasticStressField
    hydrogen_profile: HydrogenConcentrationEigenstrainProfile
    hydrogen_radial_stress_pa: np.ndarray
    hydrogen_hoop_stress_pa: np.ndarray
    hydrogen_axial_stress_pa: np.ndarray
    hydrogen_axial_strain: float
    hydrogen_support_reaction_n: float
    evidence_id: str
    _issuer: object = dataclass_field(default=None, repr=False, compare=False)
    _signature: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_ISSUERS:
            raise ValueError("Construct eigenstrain results through radial_hydrogen_eigenstrain_cylinder")
        _PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_ISSUERS.remove(self._issuer)
        if (type(self.baseline) is not RadialThermoelasticStressField
                or type(self.combined) is not RadialThermoelasticStressField
                or type(self.hydrogen_profile) is not HydrogenConcentrationEigenstrainProfile):
            raise TypeError("Retain exact pressure/thermal, combined, and hydrogen input records")
        left, right = self.baseline, self.combined
        if any((getattr(left, name) is not getattr(right, name)) for name in (
                "geometry", "load", "material", "temperature")) or left.axial_restraint != right.axial_restraint:
            raise ValueError("Baseline and combined fields must share identical physical inputs")
        if (not np.array_equal(left.radius_m, right.radius_m)
                or left.evidence_id != right.evidence_id
                or left.evidence_id != self.evidence_id):
            raise ValueError("Baseline and combined fields must use the same radial grid and equation identity")
        if (self.hydrogen_profile.radius_m[0] != left.geometry.inner_radius_m
                or self.hydrogen_profile.radius_m[-1] != left.geometry.outer_radius_m
                or self.hydrogen_profile.reference_temperature_k
                != left.temperature.reference_temperature_k):
            raise ValueError("Hydrogen profile must span the wall and share the thermal reference temperature")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Hydrogen stress result requires equation/applicability evidence")
        for name, base_name, combined_name in (
            ("hydrogen_radial_stress_pa", "radial_stress_pa", "radial_stress_pa"),
            ("hydrogen_hoop_stress_pa", "hoop_stress_pa", "hoop_stress_pa"),
            ("hydrogen_axial_stress_pa", "axial_stress_pa", "axial_stress_pa"),
        ):
            delta = np.asarray(getattr(self, name), dtype=float)
            if delta.shape != left.radius_m.shape or not np.all(np.isfinite(delta)):
                raise ValueError(f"{name} must be finite on the retained stress radius grid")
            if not np.allclose(getattr(left, base_name) + delta,
                               getattr(right, combined_name), rtol=5e-5, atol=10.0):
                raise ValueError("Hydrogen stress increments do not reconstruct the combined field")
            object.__setattr__(self, name, immutable_array(delta, name=name))
        object.__setattr__(self, "hydrogen_axial_strain",
                           finite(self.hydrogen_axial_strain, "hydrogen axial strain"))
        object.__setattr__(self, "hydrogen_support_reaction_n",
                           finite(self.hydrogen_support_reaction_n,
                                  "hydrogen axial support reaction"))
        if not np.isclose(left.axial_strain + self.hydrogen_axial_strain,
                          right.axial_strain, rtol=5e-5, atol=1e-10):
            raise ValueError("Hydrogen axial strain increment does not reconstruct the combined result")
        if not np.isclose(left.axial_support_reaction_n + self.hydrogen_support_reaction_n,
                          right.axial_support_reaction_n, rtol=5e-5, atol=10.0):
            raise ValueError("Hydrogen support-reaction increment does not reconstruct the combined result")
        object.__setattr__(self, "_signature", self._current_signature())

    def _current_signature(self):
        digest = hashlib.sha256()
        digest.update(repr((id(self.baseline), id(self.combined), id(self.hydrogen_profile),
                            self.hydrogen_axial_strain, self.hydrogen_support_reaction_n,
                            self.evidence_id)).encode("utf-8"))
        self.hydrogen_profile.require_current()
        for field in (self.baseline, self.combined):
            digest.update(repr((field.axial_strain, field.axial_support_reaction_n,
                                field.max_bvp_rms_residual,
                                field.max_normalized_boundary_residual,
                                field.bvp_iterations, field.axial_restraint,
                                field.evidence_id)).encode("utf-8"))
            digest.update(_stress_field_source_fingerprint(field).encode("ascii"))
            for name in ("radius_m", "radial_stress_pa", "hoop_stress_pa",
                         "axial_stress_pa", "von_mises_stress_pa"):
                values = np.ascontiguousarray(getattr(field, name))
                digest.update(values.dtype.str.encode("ascii"))
                digest.update(repr(values.shape).encode("ascii"))
                digest.update(values.tobytes())
        for values in (self.hydrogen_radial_stress_pa, self.hydrogen_hoop_stress_pa,
                       self.hydrogen_axial_stress_pa):
            digest.update(values.dtype.str.encode("ascii"))
            digest.update(repr(values.shape).encode("ascii"))
            digest.update(values.tobytes())
        return digest.hexdigest()

    def require_current(self):
        """Reject altered stress deltas, baseline links, or profile provenance."""
        if not self._signature or self._current_signature() != self._signature:
            raise ValueError("Hydrogen eigenstrain result changed after admission")
        return self

    @property
    def combined_von_mises_stress_pa(self):
        """Return combined von Mises stress; von Mises increments are not additive."""
        self.require_current()
        return self.combined.von_mises_stress_pa


@dataclass(frozen=True, slots=True)
class RadialHydrogenEigenstrainStressHistory:
    """Exact-sample quasi-static hydrogen eigenstrain fields on one clock."""

    time_s: np.ndarray
    samples: tuple[RadialHydrogenEigenstrainResult, ...]
    clock_id: str
    _issuer: object = dataclass_field(default=None, repr=False, compare=False)
    _signature: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_HISTORY_ISSUERS:
            raise ValueError("Construct eigenstrain histories through radial_hydrogen_eigenstrain_history")
        _PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_HISTORY_ISSUERS.remove(self._issuer)
        times = np.asarray(self.time_s, dtype=float)
        samples = tuple(self.samples)
        if times.ndim != 1 or times.size < 2 or not np.all(np.isfinite(times)):
            raise ValueError("Eigenstrain history requires at least two finite clock samples")
        if np.any(np.diff(times) <= 0) or len(samples) != times.size:
            raise ValueError("Eigenstrain samples must match a strictly increasing clock")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Identify the physical clock shared by all eigenstrain samples")
        if any(type(sample) is not RadialHydrogenEigenstrainResult for sample in samples):
            raise TypeError("History samples must retain solver-issued eigenstrain results")
        for sample in samples:
            sample.require_current()
        first = samples[0]
        first_mapping = _hydrogen_mapping_key(first.hydrogen_profile)
        for sample in samples[1:]:
            if _hydrogen_mapping_key(sample.hydrogen_profile) != first_mapping:
                raise ValueError("Every history sample must use the same carrier, concentration basis, reference and eigenstrain coefficient")
            if (sample.evidence_id != first.evidence_id
                    or sample.baseline.axial_restraint != first.baseline.axial_restraint
                    or sample.baseline.geometry is not first.baseline.geometry
                    or sample.baseline.material is not first.baseline.material
                    or not np.array_equal(sample.combined.radius_m, first.combined.radius_m)):
                raise ValueError("Eigenstrain snapshots must share equation, restraint, material, geometry and radial grid")
        object.__setattr__(self, "time_s", immutable_array(times, name="eigenstrain history time"))
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "clock_id", self.clock_id.strip())
        object.__setattr__(self, "_signature", self._current_signature())

    def _current_signature(self):
        digest = hashlib.sha256()
        digest.update(self.clock_id.encode("utf-8"))
        digest.update(self.time_s.tobytes())
        digest.update(repr(tuple(id(sample) for sample in self.samples)).encode("ascii"))
        for sample in self.samples:
            sample.require_current()
        return digest.hexdigest()

    def require_current(self):
        """Reject changed clock values or any stale exact-sample result."""
        if not self._signature or self._current_signature() != self._signature:
            raise ValueError("Hydrogen eigenstrain history changed after admission")
        return self

    def sample_at(self, sample_index: int) -> RadialHydrogenEigenstrainResult:
        """Return one exact sample; no temporal interpolation is performed."""
        self.require_current()
        if isinstance(sample_index, bool) or not isinstance(sample_index, (int, np.integer)):
            raise TypeError("Eigenstrain sample index must be an integer, not a boolean")
        index = int(sample_index)
        if not 0 <= index < len(self.samples):
            raise ValueError("Eigenstrain sample index lies outside the retained history")
        return self.samples[index]


class RadialHydrogenEigenstrainHistoryError(RuntimeError):
    """A failed exact-time solve with the accepted prefix and original cause retained."""

    def __init__(self, message, *, failed_index, completed_samples, cause):
        super().__init__(message)
        self.failed_index = failed_index
        self.completed_samples = tuple(completed_samples)
        self.cause = cause


@dataclass(frozen=True, slots=True)
class RadialThermoelasticStressField:
    """Pressure and radial-temperature stresses at requested wall radii."""

    radius_m: np.ndarray
    radial_stress_pa: np.ndarray
    hoop_stress_pa: np.ndarray
    axial_stress_pa: np.ndarray
    von_mises_stress_pa: np.ndarray
    axial_strain: float
    axial_support_reaction_n: float
    max_bvp_rms_residual: float
    max_normalized_boundary_residual: float
    bvp_iterations: int
    geometry: CylinderGeometry
    load: CylinderPressureLoad
    material: IsotropicThermoelasticMaterial
    temperature: RadialTemperatureProfile
    axial_restraint: str
    evidence_id: str

    def __post_init__(self):
        if (
            type(self.geometry) is not CylinderGeometry
            or type(self.load) is not CylinderPressureLoad
        ):
            raise TypeError("Stress result must retain the admitted geometry and pressure load")
        if type(self.material) is not IsotropicThermoelasticMaterial:
            raise TypeError("Stress result must retain the admitted material properties")
        if type(self.temperature) is not RadialTemperatureProfile:
            raise TypeError("Stress result must retain the source temperature profile")
        if (
            self.temperature.radius_m[0] != self.geometry.inner_radius_m
            or self.temperature.radius_m[-1] != self.geometry.outer_radius_m
        ):
            raise ValueError("Stress result temperature profile must span both cylinder surfaces")
        if self.axial_restraint not in {"free", "fixed"}:
            raise ValueError("Axial restraint must be explicitly 'free' or 'fixed'")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("A model equation/applicability identity is required")
        arrays = []
        for name in (
            "radius_m",
            "radial_stress_pa",
            "hoop_stress_pa",
            "axial_stress_pa",
            "von_mises_stress_pa",
        ):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
                raise ValueError(f"{name} must be a nonempty finite vector")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
            arrays.append(values)
        if any(values.shape != arrays[0].shape for values in arrays[1:]):
            raise ValueError("Stress and radius result vectors must share one shape")
        expected_von_mises = _von_mises_stress(
            self.radial_stress_pa, self.hoop_stress_pa, self.axial_stress_pa
        )
        if not np.allclose(
            self.von_mises_stress_pa, expected_von_mises, rtol=2e-12, atol=1e-8
        ):
            raise ValueError("Von Mises output does not match the principal stress components")
        if np.any(np.diff(self.radius_m) <= 0):
            raise ValueError("Requested wall radii must be strictly increasing")
        if (
            self.radius_m[0] < self.geometry.inner_radius_m
            or self.radius_m[-1] > self.geometry.outer_radius_m
        ):
            raise ValueError("Requested stress radii must lie inside the cylinder wall")
        object.__setattr__(self, "axial_strain", finite(self.axial_strain, "axial strain"))
        object.__setattr__(
            self,
            "axial_support_reaction_n",
            finite(self.axial_support_reaction_n, "axial support reaction"),
        )
        residual = finite(self.max_bvp_rms_residual, "maximum BVP residual")
        if residual < 0:
            raise ValueError("Maximum BVP residual must be nonnegative")
        object.__setattr__(self, "max_bvp_rms_residual", residual)
        boundary_residual = finite(
            self.max_normalized_boundary_residual,
            "maximum normalized boundary residual",
        )
        if boundary_residual < 0:
            raise ValueError("Maximum normalized boundary residual must be nonnegative")
        object.__setattr__(self, "max_normalized_boundary_residual", boundary_residual)
        if type(self.bvp_iterations) is not int or self.bvp_iterations < 1:
            raise ValueError("BVP iteration count must be a positive integer")


@dataclass(frozen=True, slots=True)
class RadialThermoelasticStressSample:
    """One exact-clock stress field with a guarded link to its source history."""

    sample_index: int
    time_s: float
    clock_id: str
    stress_field: RadialThermoelasticStressField
    history: RadialThermoelasticStressHistory
    _identity_bindings: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if isinstance(self.sample_index, bool) or not isinstance(self.sample_index, (int, np.integer)):
            raise TypeError("Stress sample index must be an integer, not a boolean")
        object.__setattr__(self, "sample_index", int(self.sample_index))
        object.__setattr__(self, "time_s", finite(self.time_s, "stress sample time"))
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Stress sample requires its physical clock identity")
        if type(self.stress_field) is not RadialThermoelasticStressField:
            raise TypeError("Stress sample must retain an actual thermoelastic field")
        if type(self.history) is not RadialThermoelasticStressHistory:
            raise TypeError("Stress sample must retain its actual thermoelastic history")
        self._validate_relationships()
        field = self.stress_field
        object.__setattr__(self, "_identity_bindings", (
            self.history, field, field.radius_m, field.radial_stress_pa,
            field.hoop_stress_pa, field.axial_stress_pa, field.von_mises_stress_pa,
        ))

    def _validate_relationships(self):
        self.history.require_current()
        if not 0 <= self.sample_index < self.history.time_s.size:
            raise ValueError("Stress sample index lies outside the retained history")
        index = self.sample_index
        field = self.stress_field
        if (self.clock_id != self.history.clock_id
                or self.time_s != self.history.time_s[index]):
            raise ValueError("Stress sample time/clock does not match its source history")
        if (field.geometry is not self.history.geometry
                or field.load is not self.history.loads[index]
                or field.material is not self.history.material
                or field.temperature is not self.history.temperature_profiles[index]
                or field.axial_restraint != self.history.axial_restraint
                or field.evidence_id != self.history.evidence_id):
            raise ValueError("Stress field lost its source geometry/load/material/profile identity")
        for name in (
            "radius_m", "radial_stress_pa", "hoop_stress_pa",
            "axial_stress_pa", "von_mises_stress_pa",
        ):
            if not np.array_equal(getattr(field, name), (
                self.history.radius_m if name == "radius_m"
                else getattr(self.history, name)[index]
            )):
                raise ValueError(f"Stress field {name} differs from the retained history sample")
        scalar_pairs = (
            (field.axial_strain, self.history.axial_strain[index]),
            (field.axial_support_reaction_n, self.history.axial_support_reaction_n[index]),
            (field.max_bvp_rms_residual, self.history.max_bvp_rms_residual[index]),
            (field.max_normalized_boundary_residual,
             self.history.max_normalized_boundary_residual[index]),
            (field.bvp_iterations, self.history.bvp_iterations[index]),
        )
        if any(actual != expected for actual, expected in scalar_pairs):
            raise ValueError("Stress field diagnostics differ from the retained history sample")

    def require_current(self):
        current = (
            self.history, self.stress_field, self.stress_field.radius_m,
            self.stress_field.radial_stress_pa, self.stress_field.hoop_stress_pa,
            self.stress_field.axial_stress_pa, self.stress_field.von_mises_stress_pa,
        )
        if (not self._identity_bindings
                or any(value is not original for value, original in zip(
                    current, self._identity_bindings, strict=True,
                ))):
            raise ValueError("Stress sample lost its original source/result objects")
        self._validate_relationships()
        return self

    def stress_path(self, radius_m) -> RadialThermoelasticStressPath:
        """Sample the exact-time total stress tensor along a caller radial path.

        PCHIP is used only to evaluate the already-computed radial field at the
        requested wall coordinates. No time interpolation, extrapolation, crack
        weight function, or stress-intensity calculation is implied.
        """
        self.require_current()
        return RadialThermoelasticStressPath(self, radius_m)


@dataclass(frozen=True, slots=True)
class RadialThermoelasticStressPath:
    """Immutable radial samples of one exact-time total thermoelastic stress field."""

    sample: RadialThermoelasticStressSample
    radius_m: np.ndarray
    radial_stress_pa: np.ndarray = dataclass_field(init=False)
    hoop_stress_pa: np.ndarray = dataclass_field(init=False)
    axial_stress_pa: np.ndarray = dataclass_field(init=False)
    von_mises_stress_pa: np.ndarray = dataclass_field(init=False)
    field_convention: str = dataclass_field(
        default="total_pressure_plus_thermal", init=False,
    )
    _identity_bindings: tuple = dataclass_field(
        default=(), init=False, repr=False, compare=False,
    )
    _content_sha256: str = dataclass_field(
        default="", init=False, repr=False, compare=False,
    )

    def __post_init__(self):
        if type(self.sample) is not RadialThermoelasticStressSample:
            raise TypeError("Stress paths require an exact typed stress-history sample")
        self.sample.require_current()
        raw = np.asarray(self.radius_m)
        if (raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in "iuf"
                or not np.all(np.isfinite(raw))):
            raise ValueError("Stress-path radii must be a finite numeric vector with >=2 points")
        radii = np.array(raw, dtype=float, copy=True)
        field = self.sample.stress_field
        if np.any(np.diff(radii) <= 0):
            raise ValueError("Stress-path radii must increase strictly")
        if (radii[0] < field.geometry.inner_radius_m
                or radii[-1] > field.geometry.outer_radius_m):
            raise ValueError("Stress-path evaluation cannot extrapolate outside the cylinder wall")
        radii = immutable_array(radii, name="stress-path radii")
        object.__setattr__(self, "radius_m", radii)
        for name in ("radial_stress_pa", "hoop_stress_pa", "axial_stress_pa"):
            values = np.asarray(
                PchipInterpolator(field.radius_m, getattr(field, name), extrapolate=False)(radii),
                dtype=float,
            )
            if not np.all(np.isfinite(values)):
                raise ValueError("Stress-path interpolation returned a nonfinite value")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        von_mises = _von_mises_stress(
            self.radial_stress_pa, self.hoop_stress_pa, self.axial_stress_pa,
        )
        von_mises = immutable_array(von_mises, name="von Mises stress")
        object.__setattr__(self, "von_mises_stress_pa", von_mises)
        object.__setattr__(self, "_identity_bindings", (
            self.sample, self.sample.stress_field, self.radius_m,
            self.radial_stress_pa, self.hoop_stress_pa, self.axial_stress_pa,
            self.von_mises_stress_pa,
        ))
        object.__setattr__(self, "_content_sha256", self._content_fingerprint())

    def _content_fingerprint(self):
        digest = hashlib.sha256()
        digest.update(self.field_convention.encode("ascii"))
        digest.update(self.sample.clock_id.encode("utf-8"))
        digest.update(repr((self.sample.sample_index, self.sample.time_s)).encode("ascii"))
        for name in (
            "radius_m", "radial_stress_pa", "hoop_stress_pa", "axial_stress_pa",
            "von_mises_stress_pa",
        ):
            values = np.ascontiguousarray(getattr(self, name))
            digest.update(values.dtype.str.encode("ascii"))
            digest.update(repr(values.shape).encode("ascii"))
            digest.update(values.tobytes())
        return digest.hexdigest()

    def require_current(self):
        """Verify exact source linkage and reject post-creation path edits."""
        self.sample.require_current()
        current = (
            self.sample, self.sample.stress_field, self.radius_m,
            self.radial_stress_pa, self.hoop_stress_pa, self.axial_stress_pa,
            self.von_mises_stress_pa,
        )
        if (not self._identity_bindings
                or any(value is not original for value, original in zip(
                    current, self._identity_bindings, strict=True,
                ))):
            raise ValueError("Stress path lost its exact source/result objects")
        if self.field_convention != "total_pressure_plus_thermal":
            raise ValueError("Stress-path field convention changed after sampling")
        if self._content_fingerprint() != self._content_sha256:
            raise ValueError("Stress-path values changed after sampling")
        return self


@dataclass(frozen=True, slots=True)
class RadialThermoelasticStressHistory:
    """Quasi-static stress samples linked to one physical clock and input history."""

    time_s: np.ndarray
    radius_m: np.ndarray
    radial_stress_pa: np.ndarray
    hoop_stress_pa: np.ndarray
    axial_stress_pa: np.ndarray
    von_mises_stress_pa: np.ndarray
    axial_strain: np.ndarray
    axial_support_reaction_n: np.ndarray
    bvp_iterations: np.ndarray
    max_bvp_rms_residual: np.ndarray
    max_normalized_boundary_residual: np.ndarray
    geometry: CylinderGeometry
    loads: tuple[CylinderPressureLoad, ...]
    material: IsotropicThermoelasticMaterial
    temperature_profiles: tuple[RadialTemperatureProfile, ...]
    axial_restraint: str
    clock_id: str
    evidence_id: str
    _identity_bindings: tuple = dataclass_field(
        default=(), init=False, repr=False, compare=False,
    )
    _content_sha256: str = dataclass_field(
        default="", init=False, repr=False, compare=False,
    )

    def __post_init__(self):
        times = np.array(self.time_s, dtype=float, copy=True)
        radii = np.array(self.radius_m, dtype=float, copy=True)
        if times.ndim != 1 or times.size < 2 or not np.all(np.isfinite(times)):
            raise ValueError("Thermoelastic history needs at least two finite times")
        if np.any(np.diff(times) <= 0):
            raise ValueError("Thermoelastic history times must increase strictly")
        if radii.ndim != 1 or radii.size == 0 or not np.all(np.isfinite(radii)):
            raise ValueError("Thermoelastic history needs a finite radial query grid")
        if np.any(np.diff(radii) <= 0):
            raise ValueError("Thermoelastic history radii must increase strictly")
        if type(self.geometry) is not CylinderGeometry:
            raise TypeError("History must retain the actual cylinder geometry")
        if type(self.material) is not IsotropicThermoelasticMaterial:
            raise TypeError("History must retain the actual isotropic material")
        if self.axial_restraint not in {"free", "fixed"}:
            raise ValueError("History axial restraint must be explicit")
        if (
            not isinstance(self.clock_id, str)
            or not self.clock_id.strip()
            or not isinstance(self.evidence_id, str)
            or not self.evidence_id.strip()
        ):
            raise ValueError("History requires clock and equation/evidence identities")
        loads = tuple(self.loads)
        profiles = tuple(self.temperature_profiles)
        if len(loads) != times.size or len(profiles) != times.size:
            raise ValueError("Every clock sample must retain one load and temperature profile")
        if any(type(load) is not CylinderPressureLoad for load in loads):
            raise TypeError("History must retain admitted cylinder pressure loads")
        if any(type(profile) is not RadialTemperatureProfile for profile in profiles):
            raise TypeError("History must retain admitted radial temperature profiles")
        if any(
            profile.radius_m[0] != self.geometry.inner_radius_m
            or profile.radius_m[-1] != self.geometry.outer_radius_m
            for profile in profiles
        ):
            raise ValueError("Every history temperature profile must span both cylinder surfaces")
        if any(profile.reference_temperature_k != profiles[0].reference_temperature_k for profile in profiles):
            raise ValueError("History temperature profiles must share one reference temperature")
        if np.any(radii < self.geometry.inner_radius_m) or np.any(
            radii > self.geometry.outer_radius_m
        ):
            raise ValueError("History query radii must lie inside the wall")
        shape = (times.size, radii.size)
        for name in (
            "radial_stress_pa",
            "hoop_stress_pa",
            "axial_stress_pa",
            "von_mises_stress_pa",
        ):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != shape or not np.all(np.isfinite(values)):
                raise ValueError(f"History {name} must be a finite (time,radius) array")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        expected_von_mises = _von_mises_stress(
            self.radial_stress_pa, self.hoop_stress_pa, self.axial_stress_pa
        )
        if not np.allclose(
            self.von_mises_stress_pa, expected_von_mises, rtol=2e-12, atol=1e-8
        ):
            raise ValueError("History von Mises stress must match all stress components")
        for name in (
            "axial_strain",
            "axial_support_reaction_n",
            "max_bvp_rms_residual",
            "max_normalized_boundary_residual",
        ):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != times.shape or not np.all(np.isfinite(values)):
                raise ValueError(f"History {name} must have one finite value per clock sample")
            if name.startswith("max_") and np.any(values < 0):
                raise ValueError(f"History {name} cannot be negative")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        raw_iterations = np.asarray(self.bvp_iterations)
        if (raw_iterations.dtype.kind not in "iu"
                or raw_iterations.shape != times.shape
                or np.any(raw_iterations < 1)
                or (raw_iterations.dtype.kind == "u"
                    and np.any(raw_iterations > np.iinfo(np.int64).max))):
            raise ValueError("Every stress-history BVP iteration count must be a positive integer")
        iterations = np.array(raw_iterations, dtype=np.int64, copy=True)
        iterations = immutable_array(iterations, name="BVP iterations")
        object.__setattr__(self, "bvp_iterations", iterations)
        times = immutable_array(times, name="history time")
        radii = immutable_array(radii, name="history radii")
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "radius_m", radii)
        object.__setattr__(self, "loads", loads)
        object.__setattr__(self, "temperature_profiles", profiles)
        object.__setattr__(self, "_identity_bindings", self._object_bindings())
        object.__setattr__(self, "_content_sha256", self._content_fingerprint())

    def _object_bindings(self):
        return (
            self.time_s, self.radius_m, self.radial_stress_pa, self.hoop_stress_pa,
            self.axial_stress_pa, self.von_mises_stress_pa, self.axial_strain,
            self.axial_support_reaction_n, self.bvp_iterations, self.max_bvp_rms_residual,
            self.max_normalized_boundary_residual, self.geometry, *self.loads,
            self.material, *self.temperature_profiles,
            *(array for profile in self.temperature_profiles
              for array in (profile.radius_m, profile.temperature_k)),
        )

    def _content_fingerprint(self):
        digest = hashlib.sha256()
        for name in (
            "time_s", "radius_m", "radial_stress_pa", "hoop_stress_pa",
            "axial_stress_pa", "von_mises_stress_pa", "axial_strain",
            "axial_support_reaction_n", "bvp_iterations", "max_bvp_rms_residual",
            "max_normalized_boundary_residual",
        ):
            values = np.ascontiguousarray(getattr(self, name))
            digest.update(name.encode("ascii"))
            digest.update(values.dtype.str.encode("ascii"))
            digest.update(repr(values.shape).encode("ascii"))
            digest.update(values.tobytes())
        geometry = self.geometry
        material = self.material
        metadata = (
            (geometry.inner_radius_m, geometry.outer_radius_m,
             geometry.end_condition, geometry.geometry_id),
            tuple((load.internal_pressure_pa, load.external_pressure_pa,
                   load.load_id, str(load.origin)) for load in self.loads),
            (material.young_modulus_pa, material.poisson_ratio,
             material.linear_expansion_per_k, material.material_id,
             material.property_evidence_id),
            tuple((profile.profile_id, profile.evidence_id,
                   profile.reference_temperature_k,
                   tuple(profile.radius_m), tuple(profile.temperature_k))
                  for profile in self.temperature_profiles),
            self.axial_restraint, self.clock_id, self.evidence_id,
        )
        digest.update(repr(metadata).encode("utf-8"))
        return digest.hexdigest()

    def require_current(self):
        """Reject replaced or mutated fields before a downstream model consumes them."""
        current = self._object_bindings()
        if (not self._identity_bindings
                or any(value is not original for value, original in zip(
                    current, self._identity_bindings, strict=True,
                ))):
            raise ValueError("Thermoelastic stress history lost its original source objects")
        if self._content_fingerprint() != self._content_sha256:
            raise ValueError("Thermoelastic stress history content changed after calculation")
        return self

    def stress_field_at(self, sample_index: int) -> RadialThermoelasticStressSample:
        """Return a typed, identity-linked field for one exact history sample.

        This performs no temporal interpolation or extrapolation. Callers needing
        an intermediate time require a separate, explicitly validated reconstruction.
        """
        self.require_current()
        if isinstance(sample_index, bool) or not isinstance(sample_index, (int, np.integer)):
            raise TypeError("Stress sample index must be an integer, not a boolean")
        index = int(sample_index)
        if not 0 <= index < self.time_s.size:
            raise ValueError("Stress sample index lies outside the retained history")
        field = RadialThermoelasticStressField(
            radius_m=self.radius_m,
            radial_stress_pa=self.radial_stress_pa[index],
            hoop_stress_pa=self.hoop_stress_pa[index],
            axial_stress_pa=self.axial_stress_pa[index],
            von_mises_stress_pa=self.von_mises_stress_pa[index],
            axial_strain=float(self.axial_strain[index]),
            axial_support_reaction_n=float(self.axial_support_reaction_n[index]),
            max_bvp_rms_residual=float(self.max_bvp_rms_residual[index]),
            max_normalized_boundary_residual=float(
                self.max_normalized_boundary_residual[index]
            ),
            bvp_iterations=int(self.bvp_iterations[index]),
            geometry=self.geometry,
            load=self.loads[index],
            material=self.material,
            temperature=self.temperature_profiles[index],
            axial_restraint=self.axial_restraint,
            evidence_id=self.evidence_id,
        )
        return RadialThermoelasticStressSample(
            sample_index=index,
            time_s=float(self.time_s[index]),
            clock_id=self.clock_id,
            stress_field=field,
            history=self,
        )

    def stress_path_at(self, sample_index: int, radius_m) -> RadialThermoelasticStressPath:
        """Return radial stress components on a caller grid at one exact time."""
        return self.stress_field_at(sample_index).stress_path(radius_m)


def _solve_radial_thermoelastic_cylinder(
    geometry: CylinderGeometry,
    load: CylinderPressureLoad,
    temperature: RadialTemperatureProfile,
    material: IsotropicThermoelasticMaterial,
    radius_m: float | np.ndarray,
    *,
    axial_restraint: str,
    evidence_id: str,
    hydrogen_profile: HydrogenConcentrationEigenstrainProfile | None = None,
    tolerance: float = 1.0e-7,
    max_nodes: int = 10_000,
) -> RadialThermoelasticStressField:
    """Solve pressure plus a supplied radial temperature field in a long cylinder.

    Temperature samples are interpolated with non-extrapolating PCHIP. The radial
    displacement solves isotropic axisymmetric equilibrium; radial traction is
    fixed to minus absolute pressure at both surfaces. A free cylinder solves its
    uniform axial strain from net axial force balance: closed ends carry the
    pressure thrust and open ends carry zero resultant. A fixed cylinder imposes
    zero axial strain and returns the corresponding net support reaction. The
    equation is a static long-cylinder model, not a finite-length vessel solve.
    Boundary residuals are divided by representative stress and stress-times-area
    scales before applying SciPy's dimensionless tolerance.
    """
    if type(geometry) is not CylinderGeometry or type(load) is not CylinderPressureLoad:
        raise TypeError("Pass explicit cylinder geometry and pressure-load records")
    if type(temperature) is not RadialTemperatureProfile:
        raise TypeError("Pass an explicit radial temperature profile")
    if type(material) is not IsotropicThermoelasticMaterial:
        raise TypeError("Pass explicit homogeneous isotropic material properties")
    if (hydrogen_profile is not None
            and type(hydrogen_profile) is not HydrogenConcentrationEigenstrainProfile):
        raise TypeError("Pass a typed hydrogen concentration eigenstrain profile")
    if axial_restraint not in {"free", "fixed"}:
        raise ValueError("Axial restraint must be explicitly 'free' or 'fixed'")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("A model equation/applicability identity is required")
    tolerance = finite(tolerance, "BVP tolerance", positive=True)
    if type(max_nodes) is not int or max_nodes < len(temperature.radius_m):
        raise ValueError("BVP maximum node count must cover all temperature samples")
    ri, ro = geometry.inner_radius_m, geometry.outer_radius_m
    profile_r = temperature.radius_m
    if profile_r[0] != ri or profile_r[-1] != ro:
        raise ValueError("Temperature profile must include both cylinder wall surfaces")
    if np.any(np.diff(profile_r) <= 0):
        raise ValueError("Temperature profile radii must increase strictly")
    radii = np.asarray(radius_m, dtype=float)
    if radii.ndim == 0:
        radii = radii.reshape(1)
    if radii.ndim != 1 or radii.size == 0 or not np.all(np.isfinite(radii)):
        raise ValueError("Requested stress radii must be a finite scalar or vector")
    if np.any(np.diff(radii) <= 0) or np.any((radii < ri) | (radii > ro)):
        raise ValueError("Requested radii must increase strictly inside the cylinder wall")

    temperature_curve = PchipInterpolator(profile_r, temperature.temperature_k, extrapolate=False)

    if hydrogen_profile is not None:
        if (hydrogen_profile.radius_m[0] != ri
                or hydrogen_profile.radius_m[-1] != ro
                or hydrogen_profile.reference_temperature_k != temperature.reference_temperature_k):
            raise ValueError("Hydrogen concentration profile must share wall and temperature references")
        hydrogen_profile.require_current()
        concentration_curve = PchipInterpolator(
            hydrogen_profile.radius_m,
            hydrogen_profile.concentration_mol_m3,
            extrapolate=False,
        )
        def chemical_eigenstrain(radius):
            return hydrogen_profile.eigenstrain(concentration_curve(radius))

        def chemical_eigenstrain_gradient(radius):
            return (hydrogen_profile.linear_expansion_m3_per_mol
                    * concentration_curve.derivative()(radius))
    else:
        def chemical_eigenstrain(radius):
            return np.zeros_like(np.asarray(radius, dtype=float))

        def chemical_eigenstrain_gradient(radius):
            return np.zeros_like(np.asarray(radius, dtype=float))

    def delta_temperature(radius):
        return temperature_curve(radius) - temperature.reference_temperature_k

    delta_temperature_gradient = temperature_curve.derivative()
    young = material.young_modulus_pa
    poisson = material.poisson_ratio
    alpha = material.linear_expansion_per_k
    shear = young / (2.0 * (1.0 + poisson))
    lame = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    bulk = young / (3.0 * (1.0 - 2.0 * poisson))
    eigenstrain_modulus = 3.0 * bulk
    def total_eigenstrain(radius):
        return alpha * delta_temperature(radius) + chemical_eigenstrain(radius)

    def total_eigenstrain_gradient(radius):
        return (alpha * delta_temperature_gradient(radius)
                + chemical_eigenstrain_gradient(radius))
    temperature_span = float(
        np.max(np.abs(temperature.temperature_k - temperature.reference_temperature_k))
    )
    hydrogen_concentration_span = (
        float(np.max(np.abs(hydrogen_profile.concentration_mol_m3
                            - hydrogen_profile.reference_concentration_mol_m3)))
        if hydrogen_profile is not None else 0.0
    )
    stress_scale = max(
        load.internal_pressure_pa,
        load.external_pressure_pa,
        young * abs(alpha) * temperature_span,
        young * abs(hydrogen_profile.linear_expansion_m3_per_mol)
        * hydrogen_concentration_span if hydrogen_profile is not None else 0.0,
        1.0,
    )
    axial_force_scale = stress_scale * ro**2
    pressure_end_force = (
        np.pi * (load.internal_pressure_pa * ri**2 - load.external_pressure_pa * ro**2)
        if geometry.end_condition == "closed"
        else 0.0
    )

    def radial_stress(radius, displacement, derivative, axial_strain):
        return (
            (lame + 2.0 * shear) * derivative
            + lame * displacement / radius
            + lame * axial_strain
            - eigenstrain_modulus * total_eigenstrain(radius)
        )

    def axial_stress(radius, displacement, derivative, axial_strain):
        return (
            lame * (derivative + displacement / radius)
            + (lame + 2.0 * shear) * axial_strain
            - eigenstrain_modulus * total_eigenstrain(radius)
        )

    def radial_equilibrium(radius, displacement, derivative):
        return (
            -derivative / radius
            + displacement / radius**2
            + eigenstrain_modulus / (lame + 2.0 * shear)
            * total_eigenstrain_gradient(radius)
        )

    start = np.zeros((2, profile_r.size), dtype=float)
    free = axial_restraint == "free"
    if free:
        initial = np.zeros((3, profile_r.size), dtype=float)

        def equation(radius, state, parameter):
            strain = parameter[0]
            derivative = radial_equilibrium(radius, state[0], state[1])
            axial = axial_stress(radius, state[0], state[1], strain)
            return np.vstack((state[1], derivative, axial * radius))

        def boundary(left, right, parameter):
            strain = parameter[0]
            return np.array(
                [
                    (radial_stress(ri, left[0], left[1], strain) + load.internal_pressure_pa)
                    / stress_scale,
                    (radial_stress(ro, right[0], right[1], strain) + load.external_pressure_pa)
                    / stress_scale,
                    left[2] / axial_force_scale,
                    (right[2] - (pressure_end_force / (2.0 * np.pi))) / axial_force_scale,
                ]
            )

        result = solve_bvp(
            equation,
            boundary,
            profile_r,
            initial,
            p=np.array(
                [
                    float(np.mean(
                        alpha * (temperature.temperature_k
                                 - temperature.reference_temperature_k)
                        + (hydrogen_profile.eigenstrain(
                            hydrogen_profile.concentration_mol_m3
                        ) if hydrogen_profile is not None else 0.0)
                    ))
                ]
            ),
            tol=tolerance,
            max_nodes=max_nodes,
        )
        axial_strain = float(result.p[0])
    else:
        axial_strain = 0.0
        initial = start

        def equation(radius, state):
            derivative = radial_equilibrium(radius, state[0], state[1])
            return np.vstack((state[1], derivative))

        def boundary(left, right):
            return np.array(
                [
                    (
                        radial_stress(ri, left[0], left[1], axial_strain)
                        + load.internal_pressure_pa
                    )
                    / stress_scale,
                    (
                        radial_stress(ro, right[0], right[1], axial_strain)
                        + load.external_pressure_pa
                    )
                    / stress_scale,
                ]
            )

        result = solve_bvp(
            equation,
            boundary,
            profile_r,
            initial,
            tol=tolerance,
            max_nodes=max_nodes,
        )

    if not result.success:
        raise RuntimeError(f"Radial thermoelastic BVP did not converge: {result.message}")
    # The free-axial BVP also retains an integrated axial-force state.
    displacement, derivative = result.sol(radii)[:2]
    radial = radial_stress(radii, displacement, derivative, axial_strain)
    hoop = (
        lame * derivative
        + (lame + 2.0 * shear) * displacement / radii
        + lame * axial_strain
        - eigenstrain_modulus * total_eigenstrain(radii)
    )
    axial = axial_stress(radii, displacement, derivative, axial_strain)
    vm = _von_mises_stress(radial, hoop, axial)
    axial_force = (
        2.0 * np.pi * float(result.sol(ro)[2])
        if free
        else 2.0
        * np.pi
        * float(
            simpson(
                axial_stress(result.x, *result.sol(result.x)[:2], axial_strain) * result.x,
                x=result.x,
            )
        )
    )
    reaction = 0.0 if free else axial_force - pressure_end_force
    normalized_boundary_residuals = [
        (
            radial_stress(ri, *result.sol(ri)[:2], axial_strain)
            + load.internal_pressure_pa
        )
        / stress_scale,
        (
            radial_stress(ro, *result.sol(ro)[:2], axial_strain)
            + load.external_pressure_pa
        )
        / stress_scale,
    ]
    if free:
        normalized_boundary_residuals.extend(
            (
                result.sol(ri)[2] / axial_force_scale,
                (result.sol(ro)[2] - pressure_end_force / (2.0 * np.pi))
                / axial_force_scale,
            )
        )
    return RadialThermoelasticStressField(
        radii,
        radial,
        hoop,
        axial,
        vm,
        axial_strain,
        reaction,
        float(np.max(result.rms_residuals)),
        float(np.max(np.abs(normalized_boundary_residuals))),
        int(result.niter),
        geometry,
        load,
        material,
        temperature,
        axial_restraint,
        evidence_id,
    )


def radial_thermoelastic_cylinder(
    geometry: CylinderGeometry,
    load: CylinderPressureLoad,
    temperature: RadialTemperatureProfile,
    material: IsotropicThermoelasticMaterial,
    radius_m: float | np.ndarray,
    *,
    axial_restraint: str,
    evidence_id: str,
    tolerance: float = 1.0e-7,
    max_nodes: int = 10_000,
) -> RadialThermoelasticStressField:
    """Solve the original pressure-plus-temperature long-cylinder problem."""
    return _solve_radial_thermoelastic_cylinder(
        geometry, load, temperature, material, radius_m,
        axial_restraint=axial_restraint, evidence_id=evidence_id,
        tolerance=tolerance, max_nodes=max_nodes,
    )


def radial_hydrogen_eigenstrain_cylinder(
    geometry: CylinderGeometry,
    load: CylinderPressureLoad,
    temperature: RadialTemperatureProfile,
    material: IsotropicThermoelasticMaterial,
    hydrogen_profile: HydrogenConcentrationEigenstrainProfile,
    radius_m: float | np.ndarray,
    *,
    axial_restraint: str,
    evidence_id: str,
    tolerance: float = 1.0e-7,
    max_nodes: int = 10_000,
) -> RadialHydrogenEigenstrainResult:
    """Return pressure/thermal and hydrogen-eigenstrain stress contributions.

    This runs two static BVP solves using the same constitutive kernel. The first
    is the pressure/thermal baseline; the second adds the caller-declared scalar
    isotropic hydrogen eigenstrain. It does not feed stress back into diffusion.
    """
    if type(hydrogen_profile) is not HydrogenConcentrationEigenstrainProfile:
        raise TypeError("Pass an explicit hydrogen concentration/eigenstrain profile")
    if (hydrogen_profile.radius_m[0] != geometry.inner_radius_m
            or hydrogen_profile.radius_m[-1] != geometry.outer_radius_m
            or hydrogen_profile.reference_temperature_k
            != temperature.reference_temperature_k):
        raise ValueError("Hydrogen profile must share the wall bounds and temperature reference")
    hydrogen_profile.require_current()
    baseline = _solve_radial_thermoelastic_cylinder(
        geometry, load, temperature, material, radius_m,
        axial_restraint=axial_restraint, evidence_id=evidence_id,
        tolerance=tolerance, max_nodes=max_nodes,
    )
    combined = _solve_radial_thermoelastic_cylinder(
        geometry, load, temperature, material, radius_m,
        axial_restraint=axial_restraint, evidence_id=evidence_id,
        hydrogen_profile=hydrogen_profile, tolerance=tolerance, max_nodes=max_nodes,
    )
    return RadialHydrogenEigenstrainResult(
        baseline=baseline,
        combined=combined,
        hydrogen_profile=hydrogen_profile,
        hydrogen_radial_stress_pa=combined.radial_stress_pa-baseline.radial_stress_pa,
        hydrogen_hoop_stress_pa=combined.hoop_stress_pa-baseline.hoop_stress_pa,
        hydrogen_axial_stress_pa=combined.axial_stress_pa-baseline.axial_stress_pa,
        hydrogen_axial_strain=combined.axial_strain-baseline.axial_strain,
        hydrogen_support_reaction_n=(combined.axial_support_reaction_n
                                     - baseline.axial_support_reaction_n),
        evidence_id=evidence_id,
        _issuer=_new_issuer(_PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_ISSUERS),
    )


def radial_hydrogen_eigenstrain_history(
    geometry: CylinderGeometry,
    loads: tuple[CylinderPressureLoad, ...],
    temperature_profiles: tuple[RadialTemperatureProfile, ...],
    hydrogen_profiles: tuple[HydrogenConcentrationEigenstrainProfile, ...],
    material: IsotropicThermoelasticMaterial,
    radius_m: float | np.ndarray,
    time_s: np.ndarray,
    *,
    axial_restraint: str,
    clock_id: str,
    evidence_id: str,
    tolerance: float = 1.0e-7,
    max_nodes: int = 10_000,
) -> RadialHydrogenEigenstrainStressHistory:
    """Solve supplied pressure, temperature and H-concentration snapshots exactly.

    Every clock sample is an independent static BVP. This is quasi-static
    composition, not diffusion/stress time integration, and no temporal
    interpolation or extrapolation is added.
    """
    times = np.asarray(time_s, dtype=float)
    loads = tuple(loads)
    temperature_profiles = tuple(temperature_profiles)
    hydrogen_profiles = tuple(hydrogen_profiles)
    if type(geometry) is not CylinderGeometry:
        raise TypeError("Pass an explicit cylinder geometry")
    if type(material) is not IsotropicThermoelasticMaterial:
        raise TypeError("Pass explicit homogeneous isotropic material properties")
    if times.ndim != 1 or times.size < 2 or not np.all(np.isfinite(times)):
        raise ValueError("Supply at least two finite physical clock samples")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Physical sample times must increase strictly")
    if not (len(loads) == len(temperature_profiles) == len(hydrogen_profiles) == times.size):
        raise ValueError("Each time sample needs one pressure load, temperature and concentration profile")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("Identify the physical clock shared by all inputs")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Identify the quasi-static equation/application evidence")
    if any(type(load) is not CylinderPressureLoad for load in loads):
        raise TypeError("Every history load must be an admitted cylinder pressure record")
    if any(type(profile) is not RadialTemperatureProfile for profile in temperature_profiles):
        raise TypeError("Every temperature input must be an admitted radial profile")
    if any(type(profile) is not HydrogenConcentrationEigenstrainProfile
           for profile in hydrogen_profiles):
        raise TypeError("Every concentration input must be an admitted eigenstrain profile")
    mapping_keys = tuple(_hydrogen_mapping_key(profile) for profile in hydrogen_profiles)
    if any(key != mapping_keys[0] for key in mapping_keys[1:]):
        raise ValueError("Every history sample must use one carrier, basis, reference concentration, coefficient and reference temperature")
    references = {profile.reference_temperature_k for profile in temperature_profiles}
    if len(references) != 1:
        raise ValueError("Temperature profiles must share one reference temperature")

    completed = []
    for index, (load, temperature, hydrogen) in enumerate(zip(
            loads, temperature_profiles, hydrogen_profiles, strict=True)):
        try:
            completed.append(radial_hydrogen_eigenstrain_cylinder(
                geometry, load, temperature, material, hydrogen, radius_m,
                axial_restraint=axial_restraint, evidence_id=evidence_id,
                tolerance=tolerance, max_nodes=max_nodes,
            ))
        except Exception as error:
            raise RadialHydrogenEigenstrainHistoryError(
                f"Hydrogen eigenstrain history failed at sample {index} (t={times[index]:g} s)",
                failed_index=index, completed_samples=completed, cause=error,
            ) from error
    return RadialHydrogenEigenstrainStressHistory(
        times, tuple(completed), clock_id.strip(),
        _issuer=_new_issuer(_PENDING_RADIAL_HYDROGEN_EIGENSTRAIN_HISTORY_ISSUERS),
    ).require_current()


class RadialThermoelasticHistoryError(RuntimeError):
    """A failed time sample with previously completed static fields retained."""

    def __init__(self, message, *, failed_index, completed_fields, cause):
        super().__init__(message)
        self.failed_index = failed_index
        self.completed_fields = tuple(completed_fields)
        self.cause = cause


def radial_thermoelastic_history(
    geometry: CylinderGeometry,
    loads: tuple[CylinderPressureLoad, ...],
    temperature_profiles: tuple[RadialTemperatureProfile, ...],
    material: IsotropicThermoelasticMaterial,
    radius_m: float | np.ndarray,
    time_s: np.ndarray,
    *,
    axial_restraint: str,
    clock_id: str,
    evidence_id: str,
    tolerance: float = 1.0e-7,
    max_nodes: int = 10_000,
) -> RadialThermoelasticStressHistory:
    """Evaluate a supplied pressure/temperature sequence as quasi-static snapshots.

    This composition has no thermal or mechanical time integration and inserts
    no intermediate states. Each independent profile/load pair uses the same
    static BVP as :func:`radial_thermoelastic_cylinder`.
    """
    times = np.asarray(time_s, dtype=float)
    loads = tuple(loads)
    temperature_profiles = tuple(temperature_profiles)
    if type(geometry) is not CylinderGeometry:
        raise TypeError("Pass an explicit cylinder geometry")
    if type(material) is not IsotropicThermoelasticMaterial:
        raise TypeError("Pass explicit homogeneous isotropic material properties")
    if times.ndim != 1 or times.size < 2 or not np.all(np.isfinite(times)):
        raise ValueError("Supply at least two finite clock samples")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Physical sample times must increase strictly")
    if len(loads) != times.size or len(temperature_profiles) != times.size:
        raise ValueError("Each time sample needs one pressure load and radial temperature profile")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("Identify the physical clock shared by all input snapshots")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Identify the quasistatic equation/application evidence")
    if any(type(load) is not CylinderPressureLoad for load in loads):
        raise TypeError("Every history load must be an admitted cylinder pressure record")
    if any(type(profile) is not RadialTemperatureProfile for profile in temperature_profiles):
        raise TypeError("Every history temperature must be a radial profile record")
    references = {profile.reference_temperature_k for profile in temperature_profiles}
    if len(references) != 1:
        raise ValueError("All temperature profiles must share one reference temperature")

    fields = []
    for index, (load, profile) in enumerate(zip(loads, temperature_profiles, strict=True)):
        try:
            fields.append(
                radial_thermoelastic_cylinder(
                    geometry,
                    load,
                    profile,
                    material,
                    radius_m,
                    axial_restraint=axial_restraint,
                    evidence_id=evidence_id,
                    tolerance=tolerance,
                    max_nodes=max_nodes,
                )
            )
        except Exception as error:
            raise RadialThermoelasticHistoryError(
                f"Radial thermoelastic history failed at sample {index} (t={times[index]:g} s)",
                failed_index=index,
                completed_fields=fields,
                cause=error,
            ) from error

    first = fields[0]
    if any(not np.array_equal(result.radius_m, first.radius_m) for result in fields[1:]):
        raise RuntimeError("A static solve changed the caller's requested query radii")
    return RadialThermoelasticStressHistory(
        time_s=times,
        radius_m=first.radius_m,
        radial_stress_pa=np.stack([result.radial_stress_pa for result in fields]),
        hoop_stress_pa=np.stack([result.hoop_stress_pa for result in fields]),
        axial_stress_pa=np.stack([result.axial_stress_pa for result in fields]),
        von_mises_stress_pa=np.stack([result.von_mises_stress_pa for result in fields]),
        axial_strain=np.array([result.axial_strain for result in fields]),
        axial_support_reaction_n=np.array(
            [result.axial_support_reaction_n for result in fields]
        ),
        bvp_iterations=np.array([result.bvp_iterations for result in fields], dtype=np.int64),
        max_bvp_rms_residual=np.array([result.max_bvp_rms_residual for result in fields]),
        max_normalized_boundary_residual=np.array(
            [result.max_normalized_boundary_residual for result in fields]
        ),
        geometry=geometry,
        loads=loads,
        material=material,
        temperature_profiles=temperature_profiles,
        axial_restraint=axial_restraint,
        clock_id=clock_id,
        evidence_id=evidence_id,
    )
