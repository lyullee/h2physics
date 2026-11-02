"""Audit a HyRAM-owned expanded-plug to Gaussian-entry source transition.

This module consumes caller/provider-captured radial planes. It does not run
HyRAM, alter its initialization, or infer a missing entrainment, force, or heat
term. Incomplete closures remain incomplete instead of being assigned zero.
"""

from dataclasses import dataclass, field
import hashlib
import math

import numpy as np

from ..core import finite, immutable_array

_PENDING_SNAPSHOT_ISSUERS = set()
_PENDING_AUDIT_ISSUERS = set()


def _token(pool):
    value = object()
    pool.add(value)
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty identity")
    return value.strip()


def _unit_vector(value, name):
    array = np.asarray(value)
    if array.shape != (3,) or array.dtype.kind not in "iuf":
        raise ValueError(f"{name} must contain three real components")
    result = np.asarray(array, dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    norm = float(np.linalg.norm(result))
    if not math.isclose(norm, 1.0, rel_tol=0., abs_tol=1e-10):
        raise ValueError(f"{name} must be a unit vector")
    return tuple(float(x) for x in result)


def _profile_digest(arrays):
    digest = hashlib.sha256()
    for name, value in arrays:
        item = np.asarray(value, dtype="<f8", order="C")
        digest.update(name.encode("ascii"))
        digest.update(b"\0")
        digest.update(np.asarray(item.shape, dtype="<i8").tobytes())
        digest.update(item.tobytes(order="C"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class HyRAMRadialPlaneSnapshot:
    """Immutable same-run native radial plane needed for independent flux checks.

    ``annular_area_weight_m2`` already contains the chosen radial quadrature
    and truncation. The caller remains responsible for proving those weights
    match the native plane geometry and for preserving the native run object.
    """

    run_id: str
    source_revision: str
    plane: str
    plane_id: str
    transition_id: str
    native_source: object = field(repr=False, compare=False)
    axis_unit_vector: tuple[float, float, float]
    plane_normal_unit_vector: tuple[float, float, float]
    radial_coordinate_m: np.ndarray
    annular_area_weight_m2: np.ndarray
    density_kg_m3: np.ndarray
    hydrogen_mass_fraction: np.ndarray
    normal_velocity_m_s: np.ndarray
    axial_velocity_m_s: np.ndarray
    speed_squared_m2_s2: np.ndarray
    pressure_pa: np.ndarray | None
    mixture_enthalpy_j_kg: np.ndarray | None
    ambient_pressure_pa: float
    ambient_enthalpy_j_kg: float
    thermo_model_id: str
    composition_basis_id: str
    profile_definition_id: str
    quadrature_id: str
    radial_cutoff_m: float
    profile_sha256: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_SNAPSHOT_ISSUERS:
            raise TypeError("Capture radial planes with capture_hyram_radial_plane")
        _PENDING_SNAPSHOT_ISSUERS.remove(self._issuer)
        for name in ("run_id", "source_revision", "plane_id", "transition_id",
                     "thermo_model_id", "composition_basis_id",
                     "profile_definition_id", "quadrature_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.plane not in {"expanded_plug_exit", "gaussian_entry"}:
            raise ValueError("Plane must be expanded_plug_exit or gaussian_entry")
        if self.native_source is None:
            raise ValueError("Retain the original native HyRAM source/run object")
        axis = _unit_vector(self.axis_unit_vector, "jet axis")
        normal = _unit_vector(self.plane_normal_unit_vector, "plane normal")
        if float(np.dot(axis, normal)) < 1.-1e-10:
            raise ValueError("The plane normal must point along the declared jet axis")
        object.__setattr__(self, "axis_unit_vector", axis)
        object.__setattr__(self, "plane_normal_unit_vector", normal)

        names = ("radial_coordinate_m", "annular_area_weight_m2", "density_kg_m3",
                 "hydrogen_mass_fraction", "normal_velocity_m_s", "axial_velocity_m_s",
                 "speed_squared_m2_s2")
        arrays = {}
        for name in names:
            raw = np.asarray(getattr(self, name))
            if raw.ndim != 1 or raw.dtype.kind not in "iuf":
                raise ValueError(f"{name} must be a one-dimensional real numeric array")
            value = np.asarray(raw, dtype=float)
            if value.size == 0 or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must contain finite radial samples")
            arrays[name] = value
        n = arrays["radial_coordinate_m"].size
        if any(value.size != n for value in arrays.values()):
            raise ValueError("Every required radial profile must match the quadrature length")
        if (np.any(arrays["radial_coordinate_m"] < 0.)
                or np.any(np.diff(arrays["radial_coordinate_m"]) <= 0.)
                or np.any(arrays["annular_area_weight_m2"] <= 0.)
                or np.any(arrays["density_kg_m3"] <= 0.)
                or np.any((arrays["hydrogen_mass_fraction"] < 0.)
                          | (arrays["hydrogen_mass_fraction"] > 1.))
                or np.any(arrays["speed_squared_m2_s2"] < 0.)):
            raise ValueError("Radial coordinates, weights, density, mass fractions or speed are outside domain")
        if (not np.allclose(arrays["normal_velocity_m_s"], arrays["axial_velocity_m_s"],
                            rtol=0., atol=1e-10)
                or np.any(arrays["speed_squared_m2_s2"]
                          + 1e-10*np.maximum(1., arrays["speed_squared_m2_s2"])
                          < arrays["axial_velocity_m_s"]**2)):
            raise ValueError("Velocity components and full speed-squared profile are inconsistent with the aligned plane")
        for name in ("pressure_pa", "mixture_enthalpy_j_kg"):
            supplied = getattr(self, name)
            if supplied is not None:
                raw = np.asarray(supplied)
                if raw.ndim != 1 or raw.size != n or raw.dtype.kind not in "iuf":
                    raise ValueError(f"{name} must be absent or match the radial profile")
                value = np.asarray(raw, dtype=float)
                if not np.all(np.isfinite(value)):
                    raise ValueError(f"{name} must contain finite values")
                if name == "pressure_pa" and np.any(value <= 0.):
                    raise ValueError("Radial static pressure must be positive absolute pressure")
                arrays[name] = value
        cutoff = finite(self.radial_cutoff_m, "radial cutoff", positive=True)
        if arrays["radial_coordinate_m"][-1] > cutoff:
            raise ValueError("Radial samples must lie within the declared cutoff")
        finite(self.ambient_pressure_pa, "ambient absolute pressure", positive=True)
        finite(self.ambient_enthalpy_j_kg, "ambient specific enthalpy")
        computed_digest = _profile_digest(tuple((name, arrays[name]) for name in sorted(arrays)))
        if self.profile_sha256 != computed_digest:
            raise ValueError("Profile SHA-256 does not match the retained radial arrays")
        for name, value in arrays.items():
            object.__setattr__(self, name, immutable_array(value, name=name))
        object.__setattr__(self, "radial_cutoff_m", cutoff)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (self.run_id, self.source_revision, self.plane, self.plane_id,
                self.transition_id, id(self.native_source), self.axis_unit_vector,
                self.plane_normal_unit_vector, self.ambient_pressure_pa,
                self.ambient_enthalpy_j_kg, self.thermo_model_id,
                self.composition_basis_id, self.profile_definition_id,
                self.quadrature_id, self.radial_cutoff_m, self.profile_sha256)

    def require_current(self):
        """Recheck the immutable profile, geometry and native-source identities."""
        if not self._seal or self._payload() != self._seal:
            raise ValueError("HyRAM radial-plane identity or reference metadata changed after capture")
        arrays = tuple((name, getattr(self, name)) for name in sorted((
            "radial_coordinate_m", "annular_area_weight_m2", "density_kg_m3",
            "hydrogen_mass_fraction", "normal_velocity_m_s", "axial_velocity_m_s",
            "speed_squared_m2_s2", "pressure_pa", "mixture_enthalpy_j_kg",
        )) if getattr(self, name) is not None)
        if _profile_digest(arrays) != self.profile_sha256:
            raise ValueError("HyRAM radial profile changed after capture")
        if (not math.isclose(np.linalg.norm(self.axis_unit_vector), 1., abs_tol=1e-10)
                or not math.isclose(np.linalg.norm(self.plane_normal_unit_vector), 1., abs_tol=1e-10)
                or float(np.dot(self.axis_unit_vector, self.plane_normal_unit_vector)) < 1.-1e-10):
            raise ValueError("HyRAM source-plane geometry changed after capture")
        return self


def capture_hyram_radial_plane(*, run_id, source_revision, plane, plane_id,
        transition_id, native_source, axis_unit_vector, plane_normal_unit_vector,
        radial_coordinate_m, annular_area_weight_m2, density_kg_m3,
        hydrogen_mass_fraction, normal_velocity_m_s, axial_velocity_m_s,
        speed_squared_m2_s2, pressure_pa, mixture_enthalpy_j_kg,
        ambient_pressure_pa, ambient_enthalpy_j_kg, thermo_model_id,
        composition_basis_id, profile_definition_id, quadrature_id,
        radial_cutoff_m):
    """Capture native provider arrays as a sealed host-side radial-plane value.

    This function prevents accidental post-capture edits; it cannot prove that
    a caller truthfully extracted its arrays from HyRAM. Keep the exact native
    source object and source revision alongside the capture.
    """
    values = dict(run_id=run_id, source_revision=source_revision, plane=plane,
        plane_id=plane_id, transition_id=transition_id, native_source=native_source,
        axis_unit_vector=axis_unit_vector, plane_normal_unit_vector=plane_normal_unit_vector,
        radial_coordinate_m=radial_coordinate_m,
        annular_area_weight_m2=annular_area_weight_m2, density_kg_m3=density_kg_m3,
        hydrogen_mass_fraction=hydrogen_mass_fraction,
        normal_velocity_m_s=normal_velocity_m_s, axial_velocity_m_s=axial_velocity_m_s,
        speed_squared_m2_s2=speed_squared_m2_s2, pressure_pa=pressure_pa,
        mixture_enthalpy_j_kg=mixture_enthalpy_j_kg,
        ambient_pressure_pa=ambient_pressure_pa, ambient_enthalpy_j_kg=ambient_enthalpy_j_kg,
        thermo_model_id=thermo_model_id, composition_basis_id=composition_basis_id,
        profile_definition_id=profile_definition_id, quadrature_id=quadrature_id,
        radial_cutoff_m=radial_cutoff_m)
    arrays = []
    for name in ("radial_coordinate_m", "annular_area_weight_m2", "density_kg_m3",
                 "hydrogen_mass_fraction", "normal_velocity_m_s", "axial_velocity_m_s",
                 "speed_squared_m2_s2", "pressure_pa", "mixture_enthalpy_j_kg"):
        value = values[name]
        if value is not None:
            arrays.append((name, np.asarray(value, dtype="<f8", order="C")))
    values["profile_sha256"] = _profile_digest(tuple(sorted(arrays)))
    token = _token(_PENDING_SNAPSHOT_ISSUERS)
    return HyRAMRadialPlaneSnapshot(**values, _issuer=token)


@dataclass(frozen=True, slots=True)
class HyRAMTransitionBudgets:
    h2_residual_kg_s: float
    mixture_residual_kg_s: float
    momentum_residual_n: float
    energy_residual_w: float
    h2_quadrature_error_kg_s: float
    mixture_quadrature_error_kg_s: float
    momentum_quadrature_error_n: float
    energy_quadrature_error_w: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))


@dataclass(frozen=True, slots=True)
class HyRAMTransitionLedger:
    quantity: str
    inlet_flux: float
    outlet_flux: float
    explicit_transfer: float | None
    residual: float | None
    residual_budget: float
    quadrature_error: float | None
    quadrature_error_budget: float
    status: str
    missing_terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HyRAMSourceTransitionAudit:
    run_id: str
    transition_id: str
    source_revision: str
    native_source: object = field(repr=False, compare=False)
    plug: HyRAMRadialPlaneSnapshot = field(repr=False, compare=False)
    gaussian: HyRAMRadialPlaneSnapshot = field(repr=False, compare=False)
    h2: HyRAMTransitionLedger
    mixture: HyRAMTransitionLedger
    axial_momentum: HyRAMTransitionLedger
    excess_energy: HyRAMTransitionLedger
    overall_status: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_AUDIT_ISSUERS:
            raise TypeError("Create transition audits with audit_hyram_source_transition")
        _PENDING_AUDIT_ISSUERS.remove(self._issuer)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (self.run_id, self.transition_id, self.source_revision,
                id(self.native_source), id(self.plug), id(self.gaussian),
                self.h2, self.mixture, self.axial_momentum, self.excess_energy,
                self.overall_status)

    def require_current(self):
        self.plug.require_current()
        self.gaussian.require_current()
        if self._payload() != self._seal:
            raise ValueError("HyRAM source-transition audit changed after issuance")
        if (self.plug.native_source is not self.native_source
                or self.gaussian.native_source is not self.native_source
                or self.plug.run_id != self.run_id or self.gaussian.run_id != self.run_id):
            raise ValueError("HyRAM transition lost its exact same-run native source binding")
        expected = _calculate(self.plug, self.gaussian,
            self.h2.explicit_transfer, self.mixture.explicit_transfer,
            self.axial_momentum.explicit_transfer, self.excess_energy.explicit_transfer,
            _budgets_from_ledgers(self.h2, self.mixture, self.axial_momentum, self.excess_energy),
            (self.h2.quadrature_error, self.mixture.quadrature_error,
             self.axial_momentum.quadrature_error, self.excess_energy.quadrature_error))
        if expected != (self.h2, self.mixture, self.axial_momentum,
                        self.excess_energy, self.overall_status):
            raise ValueError("HyRAM transition fluxes no longer reproduce the issued audit")
        return self


def _budgets_from_ledgers(*ledgers):
    return HyRAMTransitionBudgets(
        *(ledger.residual_budget for ledger in ledgers),
        *(ledger.quadrature_error_budget for ledger in ledgers))


def _fluxes(snapshot):
    rho = snapshot.density_kg_m3
    un = snapshot.normal_velocity_m_s
    area = snapshot.annular_area_weight_m2
    h2 = finite(float(np.sum(rho*snapshot.hydrogen_mass_fraction*un*area)),
                "radial H2 mass flow")
    mixture = finite(float(np.sum(rho*un*area)), "radial mixture mass flow")
    momentum = None
    if snapshot.pressure_pa is not None:
        momentum = finite(float(np.sum((rho*un*snapshot.axial_velocity_m_s
                                 + snapshot.pressure_pa-snapshot.ambient_pressure_pa)*area)),
                          "radial axial momentum flow")
    energy = None
    if snapshot.mixture_enthalpy_j_kg is not None:
        energy = finite(float(np.sum(rho*un*((snapshot.mixture_enthalpy_j_kg
                   - snapshot.ambient_enthalpy_j_kg)
                   + .5*snapshot.speed_squared_m2_s2)*area)),
                       "radial excess energy flow")
    return h2, mixture, momentum, energy


def _ledger(quantity, in_flux, out_flux, transfer, residual_budget,
            quadrature_error, quadrature_budget, *, fields_available=True):
    missing = []
    if transfer is None:
        missing.append("explicit_interplane_transfer")
    if not fields_available:
        missing.append("same_run_plane_properties")
    if quadrature_error is None:
        missing.append("quadrature_error_estimate")
    if missing:
        return HyRAMTransitionLedger(quantity, in_flux, out_flux, transfer, None,
            residual_budget, quadrature_error, quadrature_budget, "incomplete", tuple(missing))
    residual = out_flux-in_flux-transfer
    status = "accepted" if (abs(residual) <= residual_budget
                             and quadrature_error is not None
                             and quadrature_error <= quadrature_budget) else "rejected"
    return HyRAMTransitionLedger(quantity, in_flux, out_flux, transfer, residual,
        residual_budget, quadrature_error, quadrature_budget, status)


def _calculate(plug, gaussian, h2_source, ambient_entrainment, external_force,
               external_energy, budgets, quadrature_errors):
    pflux = _fluxes(plug)
    gflux = _fluxes(gaussian)
    errors = tuple(None if value is None else finite(value, "quadrature error")
                   for value in quadrature_errors)
    if any(value is not None and value < 0. for value in errors):
        raise ValueError("Quadrature error estimates must be nonnegative")
    b = budgets
    h2 = _ledger("hydrogen_mass_flow_kg_s", pflux[0], gflux[0], h2_source,
                 b.h2_residual_kg_s, errors[0], b.h2_quadrature_error_kg_s)
    mixture = _ledger("mixture_mass_flow_kg_s", pflux[1], gflux[1], ambient_entrainment,
                 b.mixture_residual_kg_s, errors[1], b.mixture_quadrature_error_kg_s)
    momentum = _ledger("axial_momentum_flow_n", pflux[2], gflux[2], external_force,
                 b.momentum_residual_n, errors[2], b.momentum_quadrature_error_n,
                 fields_available=pflux[2] is not None and gflux[2] is not None)
    energy = _ledger("excess_enthalpy_and_kinetic_energy_w", pflux[3], gflux[3], external_energy,
                 b.energy_residual_w, errors[3], b.energy_quadrature_error_w,
                 fields_available=pflux[3] is not None and gflux[3] is not None)
    ledgers = (h2, mixture, momentum, energy)
    status = ("incomplete" if any(item.status == "incomplete" for item in ledgers)
              else "rejected" if any(item.status == "rejected" for item in ledgers)
              else "accepted")
    return h2, mixture, momentum, energy, status


def audit_hyram_source_transition(plug, gaussian, *, h2_interstage_source_kg_s,
        ambient_entrainment_kg_s, external_axial_force_n, external_energy_rate_w,
        budgets: HyRAMTransitionBudgets,
        quadrature_errors: tuple[float | None, float | None, float | None, float | None]):
    """Audit same-run expanded-plug and Gaussian-entry radial planes.

    Explicit source/entrainment/force/energy terms may be ``None``; the related
    closure then reports ``incomplete``. No missing term is silently zeroed.
    Quadrature errors are ordered H2 mass, mixture mass, axial momentum, energy.
    A complete accepted transition is a conservation consistency result only.
    """
    if type(plug) is not HyRAMRadialPlaneSnapshot or type(gaussian) is not HyRAMRadialPlaneSnapshot:
        raise TypeError("Supply two captured HyRAM radial-plane snapshots")
    plug.require_current()
    gaussian.require_current()
    if (plug.plane != "expanded_plug_exit" or gaussian.plane != "gaussian_entry"):
        raise ValueError("Snapshots must be ordered expanded plug exit then Gaussian entry")
    if (plug.run_id != gaussian.run_id or plug.source_revision != gaussian.source_revision
            or plug.transition_id != gaussian.transition_id
            or plug.plane_id == gaussian.plane_id
            or plug.native_source is not gaussian.native_source
            or plug.axis_unit_vector != gaussian.axis_unit_vector
            or plug.thermo_model_id != gaussian.thermo_model_id
            or plug.composition_basis_id != gaussian.composition_basis_id
            or plug.quadrature_id != gaussian.quadrature_id
            or plug.ambient_pressure_pa != gaussian.ambient_pressure_pa
            or plug.ambient_enthalpy_j_kg != gaussian.ambient_enthalpy_j_kg):
        raise ValueError("Transition snapshots must share source, run, axis, EOS, composition, quadrature and ambient bases")
    if type(budgets) is not HyRAMTransitionBudgets:
        raise TypeError("Provide separate positive residual and integration-error budgets")
    errors = tuple(quadrature_errors)
    if len(errors) != 4:
        raise ValueError("Provide one quadrature-error estimate per ledger in documented order")
    transfer_values = tuple(None if x is None else finite(x, "interplane transfer")
                            for x in (h2_interstage_source_kg_s,
                                      ambient_entrainment_kg_s,
                                      external_axial_force_n,
                                      external_energy_rate_w))
    result = _calculate(plug, gaussian, *transfer_values, budgets, errors)
    token = _token(_PENDING_AUDIT_ISSUERS)
    return HyRAMSourceTransitionAudit(plug.run_id, plug.transition_id,
        plug.source_revision, plug.native_source, plug, gaussian, *result,
        _issuer=token)


__all__ = ["HyRAMRadialPlaneSnapshot", "capture_hyram_radial_plane",
           "HyRAMTransitionBudgets", "HyRAMTransitionLedger",
           "HyRAMSourceTransitionAudit", "audit_hyram_source_transition"]
