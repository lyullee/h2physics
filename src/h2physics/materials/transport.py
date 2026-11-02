"""Planar Fick transport with finite-capacity reversible kinetic traps.

Original finite-volume implementation. Public scientific context:
https://ntrs.nasa.gov/citations/20190030498 (bulk permeation)
https://doi.org/10.1016/j.ijhydene.2024.03.184 (hydrogen transport/traps).
No material-specific coefficient or fitted correlation is included. Concentrations
are moles of the explicitly declared mobile entity, not particles or moles H2 by default.
The default law excludes stress drift; an explicit prescribed hydrostatic
potential can be forwarded to the shared owner. Mechanical feedback, fracture,
evolving microstructure and nonlinear surface kinetics are not modeled here.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from ..core import finite, immutable_array

_PENDING_DIFFUSION_RESULT_ISSUERS: set[object] = set()


def _diffusion_result_fingerprint(result) -> str:
    digest = hashlib.sha256(repr((result.carrier, id(result._source_result))).encode("utf-8"))
    for name in (
        "time_s", "cell_centers_m", "mobile_mol_m3", "trapped_mol_m3",
        "left_integrated_flux_mol_m2", "right_integrated_flux_mol_m2",
        "inventory_residual_mol_m2",
    ):
        array = np.ascontiguousarray(getattr(result, name))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    digest.update(str(result.function_evaluations).encode("ascii"))
    return digest.hexdigest()


def _issue_diffusion_result(source_result, **values):
    token = object()
    _PENDING_DIFFUSION_RESULT_ISSUERS.add(token)
    try:
        return DiffusionResult(**values, _source_result=source_result, _issuer_token=token)
    except Exception:
        _PENDING_DIFFUSION_RESULT_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class HydrogenCarrier:
    identity: Literal["atomic_hydrogen", "molecular_hydrogen"]
    molar_mass_kg_mol: float

    def __post_init__(self):
        if self.identity not in {"atomic_hydrogen", "molecular_hydrogen"}:
            raise ValueError("Declare whether the mobile entity is H or H2")
        finite(self.molar_mass_kg_mol, "carrier molar mass", positive=True)

    @property
    def hydrogen_atoms_per_entity(self):
        return 1 if self.identity == "atomic_hydrogen" else 2


@dataclass(frozen=True, slots=True)
class PowerLawSolubility:
    """Surface concentration = coefficient(T) × hydrogen fugacity**exponent.

    coefficient(T) has units mol(entity) / (m³ Pa**exponent). An exponent of
    0.5 represents a Sieverts-type equilibrium and 1 a Henry-type equilibrium;
    choosing either requires appropriate material and surface evidence.
    """

    carrier: HydrogenCarrier
    coefficient: Callable[[float], float]
    exponent: float

    def __post_init__(self):
        finite(self.exponent, "fugacity exponent", positive=True)

    def concentration_mol_m3(self, hydrogen_fugacity_pa: float, temperature_k: float):
        finite(temperature_k, "temperature", positive=True)
        fugacity = finite(hydrogen_fugacity_pa, "hydrogen fugacity")
        coefficient = finite(self.coefficient(temperature_k), "solubility coefficient")
        if min(fugacity, coefficient) < 0:
            raise ValueError("Fugacity and solubility coefficient cannot be negative")
        try:
            concentration = coefficient * fugacity ** self.exponent
        except OverflowError as error:
            raise ValueError("Solubility concentration exceeds finite numerical representation") from error
        return finite(concentration, "computed solubility concentration")


@dataclass(frozen=True, slots=True)
class PermeationResult:
    carrier: HydrogenCarrier
    mobile_entity_flux_mol_m2_s: float
    hydrogen_mass_flux_kg_m2_s: float
    h2_equivalent_flux_mol_m2_s: float


@dataclass(frozen=True, slots=True)
class SurfaceResistancePermeationResult:
    """Steady planar flux with separately reported linear film/bulk resistances."""

    carrier: HydrogenCarrier
    mobile_entity_flux_mol_m2_s: float
    hydrogen_mass_flux_kg_m2_s: float
    h2_equivalent_flux_mol_m2_s: float
    upstream_equilibrium_concentration_mol_m3: float
    downstream_equilibrium_concentration_mol_m3: float
    upstream_surface_concentration_mol_m3: float
    downstream_surface_concentration_mol_m3: float
    upstream_film_resistance_s_m: float
    bulk_diffusion_resistance_s_m: float
    downstream_film_resistance_s_m: float
    boundary_evidence_id: str
    surface_resistance_evidence_id: str

    def __post_init__(self):
        if type(self.carrier) is not HydrogenCarrier:
            raise TypeError("Retain the exact mobile hydrogen carrier")
        for name in (
            "mobile_entity_flux_mol_m2_s", "hydrogen_mass_flux_kg_m2_s",
            "h2_equivalent_flux_mol_m2_s", "upstream_equilibrium_concentration_mol_m3",
            "downstream_equilibrium_concentration_mol_m3",
            "upstream_surface_concentration_mol_m3", "downstream_surface_concentration_mol_m3",
        ):
            finite(getattr(self, name), name)
        for name in (
            "upstream_film_resistance_s_m", "bulk_diffusion_resistance_s_m",
            "downstream_film_resistance_s_m",
        ):
            finite(getattr(self, name), name, positive=True)
        if min(
            self.upstream_equilibrium_concentration_mol_m3,
            self.downstream_equilibrium_concentration_mol_m3,
            self.upstream_surface_concentration_mol_m3,
            self.downstream_surface_concentration_mol_m3,
        ) < 0:
            raise ValueError("Equilibrium and membrane-side concentrations must be nonnegative")
        total_resistance = (
            self.upstream_film_resistance_s_m + self.bulk_diffusion_resistance_s_m
            + self.downstream_film_resistance_s_m
        )
        potential_drop = (
            self.upstream_equilibrium_concentration_mol_m3
            - self.downstream_equilibrium_concentration_mol_m3
        )
        if not np.isclose(
            self.mobile_entity_flux_mol_m2_s * total_resistance,
            potential_drop, rtol=2e-12, atol=1e-24,
        ):
            raise ValueError("Flux does not close across the declared series resistance")
        flux = self.mobile_entity_flux_mol_m2_s
        drops = (
            (self.upstream_equilibrium_concentration_mol_m3
             - self.upstream_surface_concentration_mol_m3,
             flux * self.upstream_film_resistance_s_m),
            (self.upstream_surface_concentration_mol_m3
             - self.downstream_surface_concentration_mol_m3,
             flux * self.bulk_diffusion_resistance_s_m),
            (self.downstream_surface_concentration_mol_m3
             - self.downstream_equilibrium_concentration_mol_m3,
             flux * self.downstream_film_resistance_s_m),
        )
        if any(not np.isclose(observed, expected, rtol=2e-12, atol=1e-24)
               for observed, expected in drops):
            raise ValueError("Membrane-side concentrations do not reproduce film and bulk drops")
        if not np.isclose(
            self.hydrogen_mass_flux_kg_m2_s,
            self.mobile_entity_flux_mol_m2_s * self.carrier.molar_mass_kg_mol,
            rtol=2e-12, atol=1e-24,
        ) or not np.isclose(
            self.h2_equivalent_flux_mol_m2_s,
            self.mobile_entity_flux_mol_m2_s * self.carrier.hydrogen_atoms_per_entity / 2,
            rtol=2e-12, atol=1e-24,
        ):
            raise ValueError("Mass and H2-equivalent fluxes disagree with the mobile carrier")
        for name in ("boundary_evidence_id", "surface_resistance_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")


def steady_permeation(solubility: PowerLawSolubility, *, diffusivity_m2_s: float,
                       thickness_m: float, upstream_fugacity_pa: float,
                       downstream_fugacity_pa: float, temperature_k: float) -> PermeationResult:
    """Signed bulk-limited flux across a homogeneous, isothermal planar membrane."""
    finite(diffusivity_m2_s, "diffusivity", positive=True)
    finite(thickness_m, "thickness", positive=True)
    upstream = solubility.concentration_mol_m3(upstream_fugacity_pa, temperature_k)
    downstream = solubility.concentration_mol_m3(downstream_fugacity_pa, temperature_k)
    flux = diffusivity_m2_s * (upstream - downstream) / thickness_m
    return PermeationResult(solubility.carrier, flux, flux * solubility.carrier.molar_mass_kg_mol,
                             flux * solubility.carrier.hydrogen_atoms_per_entity / 2)


def steady_permeation_with_surface_resistance(
    solubility: PowerLawSolubility, *, diffusivity_m2_s: float, thickness_m: float,
    upstream_fugacity_pa: float, downstream_fugacity_pa: float, temperature_k: float,
    upstream_transfer_velocity_m_s: float, downstream_transfer_velocity_m_s: float,
    boundary_evidence_id: str, surface_resistance_evidence_id: str,
) -> SurfaceResistancePermeationResult:
    """Solve a linear steady film/bulk/film resistance chain on one carrier basis.

    Fugacity is first mapped to equilibrium mobile-entity concentration by the
    declared solubility law. Both external films and the membrane bulk then use
    that same concentration potential; no dissociation/recombination mechanism
    is inferred. Transfer velocities have units m/s.
    """
    diffusivity = finite(diffusivity_m2_s, "diffusivity", positive=True)
    thickness = finite(thickness_m, "thickness", positive=True)
    upstream_velocity = finite(upstream_transfer_velocity_m_s,
                               "upstream film transfer velocity", positive=True)
    downstream_velocity = finite(downstream_transfer_velocity_m_s,
                                 "downstream film transfer velocity", positive=True)
    for name, value in (("boundary_evidence_id", boundary_evidence_id),
                        ("surface_resistance_evidence_id", surface_resistance_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {name}")
    upstream = finite(solubility.concentration_mol_m3(upstream_fugacity_pa, temperature_k),
                      "upstream equilibrium concentration")
    downstream = finite(solubility.concentration_mol_m3(downstream_fugacity_pa, temperature_k),
                        "downstream equilibrium concentration")
    upstream_resistance = finite(1.0 / upstream_velocity, "upstream film resistance", positive=True)
    bulk_resistance = finite(thickness / diffusivity, "bulk diffusion resistance", positive=True)
    downstream_resistance = finite(1.0 / downstream_velocity,
                                   "downstream film resistance", positive=True)
    total_resistance = finite(upstream_resistance + bulk_resistance + downstream_resistance,
                              "total permeation resistance", positive=True)
    flux = finite((upstream - downstream) / total_resistance,
                  "steady mobile-entity permeation flux")
    upstream_surface = finite(upstream - flux * upstream_resistance,
                              "upstream membrane surface concentration")
    downstream_surface = finite(downstream + flux * downstream_resistance,
                                "downstream membrane surface concentration")
    if min(upstream_surface, downstream_surface) < 0:
        raise ValueError("Linear surface-resistance solution left the nonnegative concentration domain")
    carrier = solubility.carrier
    return SurfaceResistancePermeationResult(
        carrier, flux, flux * carrier.molar_mass_kg_mol,
        flux * carrier.hydrogen_atoms_per_entity / 2, upstream, downstream,
        upstream_surface, downstream_surface, upstream_resistance, bulk_resistance,
        downstream_resistance, boundary_evidence_id, surface_resistance_evidence_id,
    )


@dataclass(frozen=True, slots=True)
class QuasiSteadyPermeationHistory:
    """Sampled planar flux with an integrated per-area hydrogen mass ledger."""

    carrier: HydrogenCarrier
    time_s: np.ndarray
    mobile_entity_flux_mol_m2_s: np.ndarray
    hydrogen_mass_flux_kg_m2_s: np.ndarray
    h2_equivalent_flux_mol_m2_s: np.ndarray
    cumulative_hydrogen_mass_kg_m2: np.ndarray
    thickness_m: float
    clock_id: str
    boundary_evidence_id: str
    quasi_steady_evidence_id: str

    def __post_init__(self):
        if type(self.carrier) is not HydrogenCarrier:
            raise TypeError("Permeation history must retain its explicit mobile carrier")
        thickness = finite(self.thickness_m, "membrane thickness", positive=True)
        for name in ("clock_id", "boundary_evidence_id", "quasi_steady_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Permeation history requires {name}")
        arrays = {}
        for name in (
            "time_s", "mobile_entity_flux_mol_m2_s", "hydrogen_mass_flux_kg_m2_s",
            "h2_equivalent_flux_mol_m2_s", "cumulative_hydrogen_mass_kg_m2",
        ):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.ndim != 1 or value.size < 2 or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must be a finite vector with at least two samples")
            arrays[name] = immutable_array(value, name=name)
        if len({array.size for array in arrays.values()}) != 1:
            raise ValueError("Permeation fluxes and cumulative ledger need one common sample axis")
        time = arrays["time_s"]
        if np.any(np.diff(time) <= 0):
            raise ValueError("Permeation history clock must be strictly increasing")
        expected_mass_flux = (
            arrays["mobile_entity_flux_mol_m2_s"] * self.carrier.molar_mass_kg_mol
        )
        if not np.allclose(
            arrays["hydrogen_mass_flux_kg_m2_s"], expected_mass_flux,
            rtol=2e-12, atol=1e-18,
        ):
            raise ValueError("Hydrogen mass flux does not match the declared carrier basis")
        expected_h2_flux = (
            arrays["mobile_entity_flux_mol_m2_s"]
            * self.carrier.hydrogen_atoms_per_entity / 2
        )
        if not np.allclose(
            arrays["h2_equivalent_flux_mol_m2_s"], expected_h2_flux,
            rtol=2e-12, atol=1e-18,
        ):
            raise ValueError("H2-equivalent flux does not match the mobile carrier basis")
        expected = np.concatenate((
            [0.0],
            np.cumsum(0.5 * (
                arrays["hydrogen_mass_flux_kg_m2_s"][1:]
                + arrays["hydrogen_mass_flux_kg_m2_s"][:-1]
            ) * np.diff(time)),
        ))
        if not np.allclose(
            arrays["cumulative_hydrogen_mass_kg_m2"], expected, rtol=2e-12, atol=1e-14
        ):
            raise ValueError("Cumulative permeated mass does not reconstruct from sampled flux")
        for name, value in arrays.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "thickness_m", thickness)


def quasi_steady_permeation_history(
    solubility: PowerLawSolubility, *, time_s, upstream_fugacity_pa,
    downstream_fugacity_pa, temperature_k, diffusivity_m2_s,
    thickness_m: float, clock_id: str, boundary_evidence_id: str,
    quasi_steady_evidence_id: str,
) -> QuasiSteadyPermeationHistory:
    """Evaluate the existing steady slab law at samples and integrate its flux.

    This is a caller-selected quasi-steady approximation. It does not solve a
    transient concentration field or assert that the membrane relaxation time
    is small relative to the supplied history clock.
    """
    if type(solubility) is not PowerLawSolubility:
        raise TypeError("An explicit power-law solubility relation is required")
    time = np.asarray(time_s, dtype=float)
    if time.ndim != 1 or time.size < 2 or not np.all(np.isfinite(time)):
        raise ValueError("Permeation clock must contain at least two finite samples")
    if np.any(np.diff(time) <= 0):
        raise ValueError("Permeation clock must be strictly increasing")

    def samples(values, name, *, nonnegative=False, positive=False):
        array = np.asarray(values, dtype=float)
        if array.ndim != 1 or array.shape != time.shape or not np.all(np.isfinite(array)):
            raise ValueError(f"{name} must be finite samples aligned to the clock")
        if positive and np.any(array <= 0):
            raise ValueError(f"{name} samples must be positive")
        if nonnegative and np.any(array < 0):
            raise ValueError(f"{name} samples cannot be negative")
        return array

    upstream = samples(upstream_fugacity_pa, "upstream fugacity", nonnegative=True)
    downstream = samples(downstream_fugacity_pa, "downstream fugacity", nonnegative=True)
    temperature = samples(temperature_k, "temperature", positive=True)
    if callable(diffusivity_m2_s):
        diffusivity = np.asarray([
            finite(diffusivity_m2_s(float(value)), "diffusivity", positive=True)
            for value in temperature
        ])
    else:
        diffusivity = np.full(time.shape, finite(
            diffusivity_m2_s, "diffusivity", positive=True
        ))
    thickness = finite(thickness_m, "membrane thickness", positive=True)
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("Permeation history requires an absolute clock identity")
    if not isinstance(boundary_evidence_id, str) or not boundary_evidence_id.strip():
        raise ValueError("Permeation history requires surface-boundary evidence")
    if not isinstance(quasi_steady_evidence_id, str) or not quasi_steady_evidence_id.strip():
        raise ValueError("Permeation history requires caller evidence for the quasi-steady assumption")

    rows = [steady_permeation(
        solubility, diffusivity_m2_s=float(d_value), thickness_m=thickness,
        upstream_fugacity_pa=float(up_value), downstream_fugacity_pa=float(down_value),
        temperature_k=float(t_value),
    ) for d_value, up_value, down_value, t_value in zip(
        diffusivity, upstream, downstream, temperature, strict=True,
    )]
    mass_flux = np.asarray([row.hydrogen_mass_flux_kg_m2_s for row in rows])
    cumulative = np.concatenate((
        [0.0], np.cumsum(0.5 * (mass_flux[1:] + mass_flux[:-1]) * np.diff(time)),
    ))
    return QuasiSteadyPermeationHistory(
        solubility.carrier, time,
        np.asarray([row.mobile_entity_flux_mol_m2_s for row in rows]),
        mass_flux,
        np.asarray([row.h2_equivalent_flux_mol_m2_s for row in rows]),
        cumulative, thickness, clock_id, boundary_evidence_id, quasi_steady_evidence_id,
    )


@dataclass(frozen=True, slots=True)
class SurfaceCondition:
    kind: Literal["concentration", "flux"]
    value: float

    def __post_init__(self):
        finite(self.value, "surface boundary value")
        if self.kind not in {"concentration", "flux"}:
            raise ValueError("Surface condition must prescribe concentration or flux")
        if self.kind == "concentration" and self.value < 0:
            raise ValueError("Surface concentration cannot be negative")


@dataclass(frozen=True, slots=True)
class SurfaceFilmCondition:
    """Linear surface-transfer resistance against a declared solid-basis concentration.

    ``bulk_concentration_mol_m3`` is the mobile-entity concentration that would
    be in equilibrium with the adjacent external phase, already mapped onto
    the same carrier and concentration basis as the solid. The coefficient has
    units m/s. Neither quantity is inferred from gas pressure or fugacity.
    Callbacks receive ``(time_s, temperature_k)``.
    """

    bulk_concentration_mol_m3: float | Callable[[float, float], float]
    transfer_velocity_m_s: float | Callable[[float, float], float]
    evidence_id: str

    def __post_init__(self):
        for name in ("bulk_concentration_mol_m3", "transfer_velocity_m_s"):
            value = getattr(self, name)
            if not callable(value):
                result = finite(value, name)
                if result < 0:
                    raise ValueError(f"{name} cannot be negative")
                object.__setattr__(self, name, result)
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Surface-film boundary needs caller evidence")

    def at(self, time_s: float, temperature_k: float) -> tuple[float, float]:
        """Return external solid-basis concentration and transfer velocity."""
        time = finite(time_s, "surface-film time")
        temperature = finite(temperature_k, "surface-film temperature", positive=True)
        concentration = (self.bulk_concentration_mol_m3(time, temperature)
                         if callable(self.bulk_concentration_mol_m3)
                         else self.bulk_concentration_mol_m3)
        velocity = (self.transfer_velocity_m_s(time, temperature)
                    if callable(self.transfer_velocity_m_s)
                    else self.transfer_velocity_m_s)
        concentration = finite(concentration, "surface-film bulk concentration")
        velocity = finite(velocity, "surface transfer velocity")
        if concentration < 0 or velocity < 0:
            raise ValueError("Surface-film concentration and transfer velocity cannot be negative")
        return concentration, velocity


@dataclass(frozen=True, slots=True)
class SlabBoundary:
    left: SurfaceCondition
    right: SurfaceCondition


@dataclass(frozen=True, slots=True)
class PowerLawSolubilityBoundary:
    """Equilibrium concentration boundary driven by caller fugacity histories.

    The finite-volume solver supplies the same time and spatially uniform
    temperature used by its diffusivity model. This object applies only the
    declared ``PowerLawSolubility`` relation; it adds no surface kinetics.
    """

    solubility: PowerLawSolubility
    upstream_hydrogen_fugacity_pa: float | Callable[[float], float]
    downstream_hydrogen_fugacity_pa: float | Callable[[float], float]
    evidence_id: str

    def __post_init__(self):
        if type(self.solubility) is not PowerLawSolubility:
            raise TypeError("Retain an explicit PowerLawSolubility parameterization")
        for name in ("upstream_hydrogen_fugacity_pa", "downstream_hydrogen_fugacity_pa"):
            value = getattr(self, name)
            if not callable(value):
                fugacity = finite(value, name)
                if fugacity < 0:
                    raise ValueError(f"{name} cannot be negative")
                object.__setattr__(self, name, fugacity)
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify the caller's gas/surface-equilibrium mapping evidence")

    @staticmethod
    def _fugacity(value, time_s, label):
        result = value(time_s) if callable(value) else value
        result = finite(result, label)
        if result < 0:
            raise ValueError(f"{label} cannot be negative")
        return result

    def at_temperature(self, time_s: float, temperature_k: float) -> SlabBoundary:
        """Evaluate both prescribed equilibrium surface concentrations."""
        time = finite(time_s, "surface-boundary time")
        temperature = finite(temperature_k, "surface-boundary temperature", positive=True)
        upstream = self._fugacity(
            self.upstream_hydrogen_fugacity_pa, time, "upstream hydrogen fugacity"
        )
        downstream = self._fugacity(
            self.downstream_hydrogen_fugacity_pa, time, "downstream hydrogen fugacity"
        )
        return SlabBoundary(
            SurfaceCondition(
                "concentration",
                self.solubility.concentration_mol_m3(upstream, temperature),
            ),
            SurfaceCondition(
                "concentration",
                self.solubility.concentration_mol_m3(downstream, temperature),
            ),
        )


@dataclass(frozen=True, slots=True)
class PowerLawSolubilityFilmBoundary:
    """Fugacity-driven external films on a common solid-carrier basis.

    This composes the caller's gas fugacity, equilibrium solubility map and
    linear surface-transfer coefficient with the existing finite-volume film
    boundary. It does not add surface reaction kinetics or infer coefficients.
    """

    solubility: PowerLawSolubility
    upstream_hydrogen_fugacity_pa: float | Callable[[float], float]
    downstream_hydrogen_fugacity_pa: float | Callable[[float], float]
    upstream_transfer_velocity_m_s: float | Callable[[float, float], float]
    downstream_transfer_velocity_m_s: float | Callable[[float, float], float]
    boundary_evidence_id: str
    surface_resistance_evidence_id: str

    def __post_init__(self):
        if type(self.solubility) is not PowerLawSolubility:
            raise TypeError("Retain an explicit PowerLawSolubility parameterization")
        for name in ("upstream_hydrogen_fugacity_pa", "downstream_hydrogen_fugacity_pa"):
            value = getattr(self, name)
            if not callable(value):
                value = finite(value, name)
                if value < 0:
                    raise ValueError(f"{name} cannot be negative")
                object.__setattr__(self, name, value)
        for name in ("boundary_evidence_id", "surface_resistance_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")

    def at_temperature(self, time_s: float, temperature_k: float) -> SlabBoundary:
        """Resolve fugacities using the solver's current temperature."""
        time = finite(time_s, "surface-film time")
        temperature = finite(temperature_k, "surface-film temperature", positive=True)

        def film(fugacity_source, velocity_source, label):
            fugacity = PowerLawSolubilityBoundary._fugacity(
                fugacity_source, time, f"{label} hydrogen fugacity"
            )
            concentration = self.solubility.concentration_mol_m3(fugacity, temperature)
            return SurfaceFilmCondition(
                concentration,
                velocity_source,
                self.surface_resistance_evidence_id,
            )

        return SlabBoundary(
            film(self.upstream_hydrogen_fugacity_pa,
                 self.upstream_transfer_velocity_m_s, "upstream"),
            film(self.downstream_hydrogen_fugacity_pa,
                 self.downstream_transfer_velocity_m_s, "downstream"),
        )


@dataclass(frozen=True, slots=True)
class TrapPopulation:
    site_concentration_mol_m3: float
    capture_m3_mol_s: Callable[[float], float]
    release_s_inv: Callable[[float], float]

    def __post_init__(self):
        finite(self.site_concentration_mol_m3, "trap site concentration", positive=True)


@dataclass(frozen=True, slots=True)
class DiffusionResult:
    carrier: HydrogenCarrier
    time_s: np.ndarray
    cell_centers_m: np.ndarray
    mobile_mol_m3: np.ndarray
    trapped_mol_m3: np.ndarray
    left_integrated_flux_mol_m2: np.ndarray
    right_integrated_flux_mol_m2: np.ndarray
    inventory_residual_mol_m2: np.ndarray
    function_evaluations: int
    _source_result: object = field(repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _fingerprint: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_DIFFUSION_RESULT_ISSUERS:
            raise ValueError("Use DiffusionSlab.simulate to issue a diffusion result")
        _PENDING_DIFFUSION_RESULT_ISSUERS.remove(self._issuer_token)
        for name in ("time_s", "cell_centers_m", "mobile_mol_m3", "trapped_mol_m3",
                     "left_integrated_flux_mol_m2", "right_integrated_flux_mol_m2",
                     "inventory_residual_mol_m2"):
            value = np.array(getattr(self, name), dtype=float, copy=True)
            value = immutable_array(value, name=name)
            object.__setattr__(self, name, value)
        self._validate_source_projection()
        object.__setattr__(self, "_fingerprint", _diffusion_result_fingerprint(self))

    def _validate_source_projection(self):
        from .finite_volume import TransportResult

        source = self._source_result
        if type(source) is not TransportResult:
            raise TypeError("A slab diffusion result must retain its finite-volume owner result")
        source.require_current()
        expected = (
            (self.carrier, source.carrier),
            (self.time_s, source.time_s),
            (self.cell_centers_m, source.mesh.cell_centers_m),
            (self.mobile_mol_m3, source.mobile_mol_m3),
            (self.trapped_mol_m3, source.trapped_mol_m3),
            (self.left_integrated_flux_mol_m2, source.left_integrated_mol),
            (self.right_integrated_flux_mol_m2, source.right_integrated_mol),
            (self.inventory_residual_mol_m2, source.wall_residual_mol),
            (self.function_evaluations, source.function_evaluations),
        )
        for actual, native in expected:
            if isinstance(actual, np.ndarray):
                if not np.array_equal(actual, native):
                    raise ValueError("Slab diffusion result differs from its finite-volume owner")
            elif actual != native:
                raise ValueError("Slab diffusion metadata differs from its finite-volume owner")

    def require_current(self):
        self._validate_source_projection()
        if self._fingerprint != _diffusion_result_fingerprint(self):
            raise ValueError("Original slab diffusion result changed after capture")
        return self


class DiffusionSlab:
    """One-dimensional finite-volume mobile/trapped concentration model.

    Fluxes are positive in the left-to-right coordinate direction at both faces.
    Integrating each boundary flux alongside the concentrations provides an
    independent quadrature for inventory closure. Temperature and diffusivity
    are spatially uniform, prescribed functions; no heat equation is implied.
    """

    def __init__(self, carrier: HydrogenCarrier, thickness_m: float, cells: int,
                 diffusivity_m2_s: Callable[[float], float], *,
                 traps: tuple[TrapPopulation, ...] = ()):
        self.carrier = carrier
        self.thickness_m = finite(thickness_m, "thickness", positive=True)
        if isinstance(cells, bool) or not isinstance(cells, int) or cells < 3:
            raise ValueError("A slab needs at least three integer finite-volume cells")
        self.cells, self.diffusivity, self.traps = cells, diffusivity_m2_s, tuple(traps)

    def simulate(self, time_s, initial_mobile_mol_m3, *,
                 boundary: Callable[[float], SlabBoundary] | PowerLawSolubilityBoundary,
                 temperature_k: Callable[[float], float], initial_trapped_mol_m3=None,
                 stress_potential=None,
                 relative_tolerance: float = 1e-8, absolute_tolerance_mol_m3: float = 1e-10,
                 maximum_step_s: float = np.inf) -> DiffusionResult:
        from .finite_volume import DiffusionDomain, DiffusionMesh

        mesh = DiffusionMesh.planar(self.thickness_m, self.cells)
        result = DiffusionDomain(self.carrier, mesh, self.diffusivity, traps=self.traps).simulate(
            time_s, initial_mobile_mol_m3, boundary=boundary, temperature_k=temperature_k,
            initial_trapped_mol_m3=initial_trapped_mol_m3,
            stress_potential=stress_potential,
            relative_tolerance=relative_tolerance,
            absolute_tolerance_mol_m3=absolute_tolerance_mol_m3,
            maximum_step_s=maximum_step_s)
        # The legacy slab uses unit area, retaining its mol/m² result contract.
        return _issue_diffusion_result(
            result, carrier=self.carrier, time_s=result.time_s,
            cell_centers_m=mesh.cell_centers_m,
            mobile_mol_m3=result.mobile_mol_m3,
            trapped_mol_m3=result.trapped_mol_m3,
            left_integrated_flux_mol_m2=result.left_integrated_mol,
            right_integrated_flux_mol_m2=result.right_integrated_mol,
            inventory_residual_mol_m2=result.wall_residual_mol,
            function_evaluations=result.function_evaluations,
        )


class HydrogenDiffusionShell:
    """Radial hydrogen transport through a finite cylindrical or spherical shell.

    The wrapper owns geometry construction and delegates integration, traps,
    boundary conditions and native-result lineage to ``DiffusionDomain``.
    Cylinders require a finite length; spheres represent a complete shell and
    therefore reject a length. Returned inventories and face integrals are
    extensive (mol and mol/s), unlike the legacy unit-area ``DiffusionSlab``.
    Axial/end transport and heat transfer are not modeled. Prescribed stress
    drift is optional through the shared finite-volume owner; feedback is absent.
    """

    def __init__(self, carrier: HydrogenCarrier, *, inner_radius_m: float,
                 outer_radius_m: float, cells: int,
                 diffusivity_m2_s: Callable[[float], float],
                 geometry: Literal["cylindrical", "spherical"],
                 length_m: float | None = None,
                 traps: tuple[TrapPopulation, ...] = ()):
        from .finite_volume import DiffusionMesh

        if type(carrier) is not HydrogenCarrier:
            raise TypeError("Retain an explicit HydrogenCarrier")
        inner = finite(inner_radius_m, "inner radius", positive=True)
        outer = finite(outer_radius_m, "outer radius", positive=True)
        if outer <= inner:
            raise ValueError("Outer radius must exceed inner radius")
        if isinstance(cells, bool) or not isinstance(cells, int) or cells < 3:
            raise ValueError("A diffusion shell needs at least three integer cells")
        if not callable(diffusivity_m2_s):
            raise TypeError("Diffusivity must be a temperature callback")
        resolved_length = None
        if geometry == "cylindrical":
            if length_m is None:
                raise ValueError("A cylindrical shell requires finite length")
            length = finite(length_m, "cylinder length", positive=True)
            resolved_length = length
            mesh = DiffusionMesh.cylindrical_shell(inner, outer, length, cells)
        elif geometry == "spherical":
            if length_m is not None:
                raise ValueError("A spherical shell has no cylinder length")
            mesh = DiffusionMesh.spherical_shell(inner, outer, cells)
        else:
            raise ValueError("Shell geometry must be cylindrical or spherical")
        if not isinstance(traps, tuple) or any(type(item) is not TrapPopulation for item in traps):
            raise TypeError("traps must be a tuple of TrapPopulation parameters")
        self.carrier = carrier
        self.geometry = geometry
        self.inner_radius_m = inner
        self.outer_radius_m = outer
        self.length_m = resolved_length
        self.mesh = mesh
        self.diffusivity_m2_s = diffusivity_m2_s
        self.traps = traps

    def simulate(self, time_s, initial_mobile_mol_m3, *, boundary,
                 temperature_k: Callable[[float], float], initial_trapped_mol_m3=None,
                 left_inventory=None, right_inventory=None,
                 stress_potential=None,
                 relative_tolerance: float = 1e-8,
                 absolute_tolerance_mol_m3: float = 1e-10,
                 maximum_step_s: float = np.inf):
        """Integrate the shell using the shared conservative finite-volume solver."""
        from .finite_volume import DiffusionDomain

        return DiffusionDomain(
            self.carrier, self.mesh, self.diffusivity_m2_s, traps=self.traps,
        ).simulate(
            time_s, initial_mobile_mol_m3, boundary=boundary,
            temperature_k=temperature_k,
            initial_trapped_mol_m3=initial_trapped_mol_m3,
            left_inventory=left_inventory, right_inventory=right_inventory,
            stress_potential=stress_potential,
            relative_tolerance=relative_tolerance,
            absolute_tolerance_mol_m3=absolute_tolerance_mol_m3,
            maximum_step_s=maximum_step_s,
        )
