"""Optional actual-native HyRAM+ high-pressure gas jets, with source checks.

The separately installed GPL-3.0-only engine owns its release and jet physics.
This module contains no native solver or copied implementation.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

import numpy as np

from ..core import ThermoState, finite
from ..release import NozzleOpening, SourceLocation


_PENDING_HYRAM_JET_ISSUERS: set[object] = set()


def _issue_hyram_jet_run(**values):
    """Issue an admitted jet receipt only from the checked native run path."""
    token = object()
    _PENDING_HYRAM_JET_ISSUERS.add(token)
    try:
        return HyRAMJetRun(**values, _issuer_token=token)
    except Exception:
        _PENDING_HYRAM_JET_ISSUERS.discard(token)
        raise


def _h2_gaussian_section_flux(native: Any) -> np.ndarray:
    """Reconstruct native H2 mass transport from its Gaussian section fields."""
    try:
        density = np.asarray(native.rho_cl, dtype=float)
        fraction = np.asarray(native.Y_cl, dtype=float)
        velocity = np.asarray(native.V_cl, dtype=float)
        radius = np.asarray(native.B, dtype=float)
        lam = finite(native.lam, "HyRAM Gaussian lambda", positive=True)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Native HyRAM result lacks valid Gaussian H2 flux fields") from exc
    arrays = (density, fraction, velocity, radius)
    if (any(value.ndim != 1 for value in arrays)
            or len({value.shape for value in arrays}) != 1
            or not density.size
            or any(not np.all(np.isfinite(value)) for value in arrays)):
        raise ValueError("Native HyRAM Gaussian H2 flux fields have invalid shape or values")
    flux = math.pi*density*fraction*velocity*radius**2/(1.+1./lam**2)
    if not np.all(np.isfinite(flux)):
        raise ValueError("Native HyRAM Gaussian H2 flux is not finite")
    return flux


def _gaussian_domain_valid(native: Any) -> bool:
    density = np.asarray(native.rho_cl, dtype=float)
    fraction = np.asarray(native.Y_cl, dtype=float)
    velocity = np.asarray(native.V_cl, dtype=float)
    radius = np.asarray(native.B, dtype=float)
    return bool(
        np.all(density > 0.) and np.all((fraction >= 0.) & (fraction <= 1.))
        and np.all(velocity >= 0.) and np.all(radius > 0.)
    )


@dataclass(frozen=True, slots=True)
class HyRAMJetRun:
    native: Any
    upstream: ThermoState
    ambient: ThermoState
    opening: NozzleOpening
    location: SourceLocation
    evidence_id: str
    mass_flow_kg_s: float
    gaussian_entry_h2_flow_kg_s: float
    maximum_transport_h2_residual_kg_s: float
    maximum_h2_flux_residual_kg_s: float
    mass_budget_kg_s: float
    accepted: bool
    centreline: np.ndarray
    _identity_binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _receipt_binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _native_binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_HYRAM_JET_ISSUERS:
            raise ValueError("HyRAM jet receipts are issued only by the checked native run path")
        _PENDING_HYRAM_JET_ISSUERS.remove(self._issuer_token)
        flow = finite(self.mass_flow_kg_s, "mass_flow_kg_s", positive=True)
        native_flow = finite(self.native.mass_flow_rate, "native mass_flow_rate", positive=True)
        if flow != native_flow:
            raise ValueError("HyRAM receipt flow differs from the retained native source flow")
        native_centreline = np.c_[self.native.S, self.native.x, self.native.y,
                                  self.native.Y_cl, self.native.X_cl]
        values = np.array(self.centreline, dtype=float, copy=True)
        if values.ndim != 2 or values.shape[1] != 5 or len(values) < 2:
            raise ValueError("Retain the five-column native HyRAM centreline")
        if (values.shape != native_centreline.shape
                or not np.array_equal(values, native_centreline)
                or not np.all(np.isfinite(values)) or np.any(np.diff(values[:, 0]) <= 0)):
            raise ValueError("HyRAM centreline coordinates must be finite and increasing")
        flux = _h2_gaussian_section_flux(self.native)
        expected_entry = float(flux[0])
        expected_transport = float(np.max(np.abs(flux-expected_entry)))
        expected_flux_residual = float(np.max(np.abs(flux-flow)))
        if (self.gaussian_entry_h2_flow_kg_s != expected_entry
                or self.maximum_transport_h2_residual_kg_s != expected_transport
                or self.maximum_h2_flux_residual_kg_s != expected_flux_residual):
            raise ValueError("HyRAM flux summaries differ from retained native Gaussian section fields")
        # A NumPy write flag alone is reversible when the array owns its
        # storage. Back the public snapshot with immutable bytes so callers
        # cannot reopen writes and silently alter a captured admission receipt.
        values = np.frombuffer(values.tobytes(order="C"), dtype=values.dtype).reshape(values.shape)
        object.__setattr__(self, "centreline", values)
        for name in (
            "mass_flow_kg_s", "gaussian_entry_h2_flow_kg_s",
            "maximum_transport_h2_residual_kg_s", "maximum_h2_flux_residual_kg_s",
            "mass_budget_kg_s",
        ):
            finite(getattr(self, name), name, positive=name in {
                "mass_flow_kg_s", "mass_budget_kg_s",
            })
        if type(self.accepted) is not bool:
            raise TypeError("HyRAM acceptance must be an explicit bool")
        expected_acceptance = bool(
            np.all(values[:, 3:5] >= 0.) and np.all(values[:, 3:5] <= 1.)
            and _gaussian_domain_valid(self.native)
            and expected_flux_residual <= self.mass_budget_kg_s
        )
        if self.accepted != expected_acceptance:
            raise ValueError("HyRAM accepted flag does not follow the retained source mass gate")
        object.__setattr__(self, "_identity_binding", (
            self.native, self.upstream, self.ambient, self.opening, self.location, values,
        ))
        object.__setattr__(self, "_receipt_binding", self._receipt_payload())
        object.__setattr__(self, "_native_binding", self._native_payload())

    @staticmethod
    def _array_signature(value):
        array = np.ascontiguousarray(np.asarray(value))
        return array.shape, array.dtype.str, sha256(array.tobytes()).hexdigest()

    def _native_payload(self):
        # Flow and Gaussian cross-section arrays determine whether the retained
        # host acceptance still describes the native result being consumed.
        names = ("mass_flow_rate", "S", "x", "y", "Y_cl", "X_cl", "rho_cl",
                 "V_cl", "B", "lam")
        payload = []
        for name in names:
            if not hasattr(self.native, name):
                payload.append((name, None))
                continue
            value = getattr(self.native, name)
            if name == "mass_flow_rate":
                payload.append((name, float(value)))
            else:
                payload.append((name, self._array_signature(value)))
        return tuple(payload)

    def _receipt_payload(self):
        return (
            self._array_signature(self.centreline),
            self.evidence_id, float(self.mass_flow_kg_s),
            float(self.gaussian_entry_h2_flow_kg_s),
            float(self.maximum_transport_h2_residual_kg_s),
            float(self.maximum_h2_flux_residual_kg_s), float(self.mass_budget_kg_s),
            self.accepted,
        )

    def require_current(self):
        """Reject native output or receipt mutation after its admission gate."""
        current = (self.native, self.upstream, self.ambient, self.opening,
                   self.location, self.centreline)
        if any(value is not original for value, original in zip(
            current, self._identity_binding, strict=True,
        )):
            raise ValueError("HyRAM result lost its original native or boundary objects")
        if (self._receipt_payload() != self._receipt_binding
                or self._native_payload() != self._native_binding):
            raise ValueError("HyRAM native output or acceptance receipt changed after capture")
        return self


class HyRAMJetError(ValueError):
    def __init__(self, result: HyRAMJetRun):
        self.result, self.native = result, result.native
        super().__init__("Native HyRAM gas-jet output failed its host material/finite-state gate")


def run_hyram_gas_jet(*, fluid_factory: Callable, orifice_factory: Callable, jet_factory: Callable,
                       upstream: ThermoState, ambient: ThermoState, opening: NozzleOpening,
                       location: SourceLocation, evidence_id: str,
                       solver_options: Mapping[str, Any], require_accepted: bool = True,
                       relative_mass_tolerance: float = 1e-4,
                       absolute_mass_tolerance_kg_s: float = 1e-8) -> HyRAMJetRun:
    """Pass upstream stagnation conditions to the one selected native pipeline.

    This path does not pass an already choked shared-nozzle result through a
    second nozzle. Ambient is calm air; native coordinates map to global x/z.
    The injected factories and native object remain available to Python callers.
    """
    if type(require_accepted) is not bool:
        raise TypeError("require_accepted must be an explicit bool")
    if (upstream.basis.fluid != "Hydrogen" or upstream.basis.spin_composition != "normal"
            or ambient.basis.fluid != "Air"):
        raise ValueError("This checked HyRAM route requires normal Hydrogen and Air bases")
    for state in (upstream, ambient):
        if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("The high-pressure gas route requires single gas states")
    if upstream.pressure_pa <= 2*ambient.pressure_pa:
        raise ValueError("This declared high-pressure route requires P0 > 2 Pambient")
    if abs(location.direction_unit[1]) > 1e-12 or not evidence_id.strip():
        raise ValueError("Declare a source in the global x/z plane and source evidence")
    options = dict(solver_options)
    if {"fluid", "orifice", "ambient", "mdot", "developing_flow", "theta0", "x0", "y0"} & options.keys():
        raise ValueError("Source/plane ownership cannot be overridden through solver options")
    finite(options.get("Smax", math.nan), "finite native arclength request", positive=True)
    for value in (relative_mass_tolerance, absolute_mass_tolerance_kg_s):
        finite(value, "mass tolerance", positive=True)
    fuel = fluid_factory("H2", T=upstream.temperature_k, P=upstream.pressure_pa)
    air = fluid_factory("AIR", T=ambient.temperature_k, P=ambient.pressure_pa)
    for native, state in ((fuel, upstream), (air, ambient)):
        if not math.isclose(native.rho, state.density_kg_m3, rel_tol=1e-7, abs_tol=1e-10):
            raise ValueError("Native and declared source/ambient density bases differ")
        enthalpy = native.therm.get_property("H", T=state.temperature_k, P=state.pressure_pa)
        if not math.isclose(enthalpy, state.enthalpy_j_kg, rel_tol=1e-7, abs_tol=1e-4):
            raise ValueError("Native and declared enthalpy references differ")
    orifice = orifice_factory(math.sqrt(4*opening.nominal_area_m2/math.pi),
                               Cd=opening.effective_area_factor)
    native = jet_factory(fuel, orifice, air,
        theta0=math.atan2(location.direction_unit[2], location.direction_unit[0]),
        x0=location.position_m[0], y0=location.position_m[2], **options)
    flow = finite(native.mass_flow_rate, "native gas flow", positive=True)
    # Integral of rho*Y*V over the native Gaussian section. This checks H2
    # transport; it does not assert a constant-cp energy closure is qualified.
    flux = _h2_gaussian_section_flux(native)
    centreline = np.c_[native.S, native.x, native.y, native.Y_cl, native.X_cl]
    residual = float(np.max(abs(flux-flow))) if flux.size else math.inf
    budget = absolute_mass_tolerance_kg_s + relative_mass_tolerance*flow
    accepted = bool(len(centreline) >= 2 and np.all(np.isfinite(centreline))
        and np.all(np.diff(centreline[:, 0]) > 0) and np.all(centreline[:, 3:5] >= 0)
        and np.all(centreline[:, 3:5] <= 1) and _gaussian_domain_valid(native)
        and residual <= budget)
    entry = float(flux[0]) if flux.size else math.nan
    transport = float(np.max(abs(flux-entry))) if flux.size else math.inf
    result = _issue_hyram_jet_run(
        native=native, upstream=upstream, ambient=ambient, opening=opening,
        location=location, evidence_id=evidence_id, mass_flow_kg_s=flow,
        gaussian_entry_h2_flow_kg_s=entry,
        maximum_transport_h2_residual_kg_s=transport,
        maximum_h2_flux_residual_kg_s=residual, mass_budget_kg_s=budget,
        accepted=accepted, centreline=centreline,
    )
    if require_accepted and not accepted:
        raise HyRAMJetError(result)
    return result
