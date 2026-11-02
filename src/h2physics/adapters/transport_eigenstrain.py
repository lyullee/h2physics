"""Bind native cylindrical diffusion snapshots to the quasi-static stress BVP.

The transport solver owns cell-centered concentration. Surface concentrations,
their mapping evidence, and the transport-to-operation clock join remain explicit
caller inputs; this adapter does not invent boundary values or feedback physics.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from dataclasses import field as dataclass_field

import numpy as np

from ..core import finite, immutable_array
from ..materials.elastic_cylinder import (
    CylinderGeometry,
    CylinderPressureLoad,
    IsotropicThermoelasticMaterial,
)
from ..materials.finite_volume import TransportResult
from ..materials.radial_thermoelastic import (
    HydrogenConcentrationEigenstrainProfile,
    RadialHydrogenEigenstrainStressHistory,
    RadialTemperatureProfile,
    radial_hydrogen_eigenstrain_history,
)

_PENDING_TRANSPORT_EIGENSTRAIN_ISSUERS: set[object] = set()


def _new_issuer():
    token = object()
    _PENDING_TRANSPORT_EIGENSTRAIN_ISSUERS.add(token)
    return token


def _content_signature(transport, history, surface_values, mapping_evidence_id,
                       clock_mapping_evidence_id, axial_uniformity_evidence_id,
                       concentration_basis_id, profile_id):
    transport.require_current()
    history.require_current()
    digest = hashlib.sha256()
    digest.update(repr((id(transport), id(history), mapping_evidence_id,
                        clock_mapping_evidence_id, axial_uniformity_evidence_id,
                        concentration_basis_id, profile_id)).encode("utf-8"))
    for values in (transport.time_s, transport.mesh.face_positions_m,
                   transport.mesh.cell_centers_m, transport.mobile_mol_m3,
                   surface_values, history.time_s):
        array = np.ascontiguousarray(values)
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    for result in history.samples:
        profile = result.hydrogen_profile
        profile.require_current()
        for values in (profile.radius_m, profile.concentration_mol_m3):
            array = np.ascontiguousarray(values)
            digest.update(array.dtype.str.encode("ascii"))
            digest.update(repr(array.shape).encode("ascii"))
            digest.update(array.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class TransportEigenstrainBinding:
    """Retain diffusion source, exact mapped faces and resulting stress history."""

    transport: TransportResult
    stress_history: RadialHydrogenEigenstrainStressHistory
    surface_concentration_mol_m3: np.ndarray
    mapping_evidence_id: str
    clock_mapping_evidence_id: str
    axial_uniformity_evidence_id: str
    concentration_basis_id: str
    profile_id: str
    _issuer: object = dataclass_field(default=None, repr=False, compare=False)
    _signature: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_TRANSPORT_EIGENSTRAIN_ISSUERS:
            raise ValueError("Create transport/eigenstrain bindings through the adapter factory")
        _PENDING_TRANSPORT_EIGENSTRAIN_ISSUERS.remove(self._issuer)
        if type(self.transport) is not TransportResult:
            raise TypeError("Retain the exact native cylindrical transport result")
        if type(self.stress_history) is not RadialHydrogenEigenstrainStressHistory:
            raise TypeError("Retain the exact solver-issued eigenstrain stress history")
        self.transport.require_current()
        self.stress_history.require_current()
        if (self.transport.mesh.geometry != "cylindrical_shell"
                or not np.array_equal(self.transport.time_s, self.stress_history.time_s)
                or self.transport.carrier is not self.stress_history.samples[0].hydrogen_profile.carrier):
            raise ValueError("Transport and stress history must share exact time, cylindrical geometry and carrier")
        for name in ("mapping_evidence_id", "clock_mapping_evidence_id",
                     "axial_uniformity_evidence_id", "concentration_basis_id", "profile_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must identify the caller-owned mapping")
            object.__setattr__(self, name, value.strip())
        raw_surface_values = np.asarray(self.surface_concentration_mol_m3)
        if raw_surface_values.dtype.kind not in "iuf":
            raise TypeError("Surface concentration values must be real numeric values, not booleans")
        surface_values = np.asarray(raw_surface_values, dtype=float)
        expected_shape = (len(self.transport.time_s), 2)
        if (surface_values.shape != expected_shape or not np.all(np.isfinite(surface_values))
                or np.any(surface_values < 0)):
            raise ValueError("Supply finite nonnegative inner/outer surface concentrations at every transport time")
        surface_values = immutable_array(surface_values, name="transport surface concentration mapping")
        object.__setattr__(self, "surface_concentration_mol_m3", surface_values)
        self._validate_profile_mapping(surface_values)
        object.__setattr__(self, "_signature", _content_signature(
            self.transport, self.stress_history, surface_values,
            self.mapping_evidence_id, self.clock_mapping_evidence_id,
            self.axial_uniformity_evidence_id, self.concentration_basis_id, self.profile_id,
        ))

    def _validate_profile_mapping(self, surface_values):
        mesh = self.transport.mesh
        expected_radii = np.r_[mesh.face_positions_m[0], mesh.cell_centers_m,
                               mesh.face_positions_m[-1]]
        for index, result in enumerate(self.stress_history.samples):
            profile = result.hydrogen_profile
            expected_concentration = np.r_[surface_values[index, 0],
                                            self.transport.mobile_mol_m3[index],
                                            surface_values[index, 1]]
            if (profile.carrier is not self.transport.carrier
                    or profile.concentration_basis_id != self.concentration_basis_id
                    or profile.profile_id != f"{self.profile_id}:{index}"
                    or profile.evidence_id != self.mapping_evidence_id
                    or not np.array_equal(profile.radius_m, expected_radii)
                    or not np.array_equal(profile.concentration_mol_m3, expected_concentration)):
                raise ValueError("Eigenstrain profiles no longer reproduce exact transport cells and caller surfaces")

    def require_current(self):
        self.transport.require_current()
        self.stress_history.require_current()
        self._validate_profile_mapping(self.surface_concentration_mol_m3)
        current = _content_signature(
            self.transport, self.stress_history, self.surface_concentration_mol_m3,
            self.mapping_evidence_id, self.clock_mapping_evidence_id,
            self.axial_uniformity_evidence_id, self.concentration_basis_id, self.profile_id,
        )
        if not self._signature or current != self._signature:
            raise ValueError("Transport/eigenstrain binding changed after admission")
        return self


def bind_cylindrical_transport_to_eigenstrain(
    transport: TransportResult,
    surface_concentration_mol_m3,
    geometry: CylinderGeometry,
    loads: tuple[CylinderPressureLoad, ...],
    temperature_profiles: tuple[RadialTemperatureProfile, ...],
    material: IsotropicThermoelasticMaterial,
    radius_m,
    *,
    reference_concentration_mol_m3: float,
    linear_expansion_m3_per_mol: float,
    reference_temperature_k: float,
    concentration_basis_id: str,
    profile_id: str,
    mapping_evidence_id: str,
    clock_mapping_evidence_id: str,
    axial_uniformity_evidence_id: str,
    clock_id: str,
    evidence_id: str,
    axial_restraint: str,
    tolerance: float = 1.0e-7,
    max_nodes: int = 10_000,
) -> TransportEigenstrainBinding:
    """Map cell-center mobile H plus explicit surface values to radial stress.

    The transport result must come from a cylindrical shell whose inner/outer
    faces exactly match ``geometry``. Each sample gets one profile consisting of
    caller-provided surface values and the original cell-center concentrations.
    The stress BVP's existing PCHIP reconstruction is applied to that explicit
    node set. Clock mapping and axial uniformity are separate evidence identities.
    No trapped concentration, surface chemistry, or feedback is inferred.
    """
    if type(transport) is not TransportResult:
        raise TypeError("Pass an admitted native TransportResult")
    transport.require_current()
    if type(geometry) is not CylinderGeometry:
        raise TypeError("Pass an explicit cylinder geometry")
    mesh = transport.mesh
    if (mesh.geometry != "cylindrical_shell"
            or mesh.face_positions_m[0] != geometry.inner_radius_m
            or mesh.face_positions_m[-1] != geometry.outer_radius_m):
        raise ValueError("Transport mesh must be cylindrical and match both stress-cylinder surfaces exactly")
    raw_surfaces = np.asarray(surface_concentration_mol_m3)
    if raw_surfaces.dtype.kind not in "iuf":
        raise TypeError("Surface concentration values must be real numeric values, not booleans")
    surfaces = np.asarray(raw_surfaces, dtype=float)
    if (surfaces.shape != (len(transport.time_s), 2)
            or not np.all(np.isfinite(surfaces)) or np.any(surfaces < 0)):
        raise ValueError("Provide finite nonnegative inner/outer concentration values at every source time")
    for name, value in (("concentration_basis_id", concentration_basis_id),
                        ("profile_id", profile_id), ("mapping_evidence_id", mapping_evidence_id),
                        ("clock_mapping_evidence_id", clock_mapping_evidence_id),
                        ("axial_uniformity_evidence_id", axial_uniformity_evidence_id),
                        ("clock_id", clock_id), ("evidence_id", evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must explicitly identify the caller's source/mapping")
    reference_concentration = finite(reference_concentration_mol_m3,
                                     "reference mobile hydrogen concentration")
    if reference_concentration < 0:
        raise ValueError("Reference concentration cannot be negative")
    coefficient = finite(linear_expansion_m3_per_mol,
                          "caller linear concentration-expansion coefficient")
    reference_temperature = finite(reference_temperature_k,
                                   "hydrogen reference temperature", positive=True)
    radii = np.r_[mesh.face_positions_m[0], mesh.cell_centers_m, mesh.face_positions_m[-1]]
    profiles = tuple(
        HydrogenConcentrationEigenstrainProfile(
                carrier=transport.carrier,
                concentration_basis_id=concentration_basis_id,
                radius_m=radii,
                concentration_mol_m3=np.r_[surfaces[index, 0],
                                           transport.mobile_mol_m3[index], surfaces[index, 1]],
                reference_concentration_mol_m3=reference_concentration,
                linear_expansion_m3_per_mol=coefficient,
                reference_temperature_k=reference_temperature,
                profile_id=f"{profile_id}:{index}",
                evidence_id=mapping_evidence_id,
            )
        for index in range(len(transport.time_s))
    )
    history = radial_hydrogen_eigenstrain_history(
        geometry, loads, temperature_profiles, profiles, material, radius_m,
        transport.time_s, axial_restraint=axial_restraint, clock_id=clock_id,
        evidence_id=evidence_id, tolerance=tolerance, max_nodes=max_nodes,
    )
    return TransportEigenstrainBinding(
        transport, history, surfaces, mapping_evidence_id,
        clock_mapping_evidence_id, axial_uniformity_evidence_id,
        concentration_basis_id, profile_id,
        _issuer=_new_issuer(),
    ).require_current()
