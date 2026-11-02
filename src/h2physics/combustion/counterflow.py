"""Opposed-flow nonpremixed flames through Cantera's native 1D solver.

This module owns input admission and result identity. Cantera owns the reacting
flow equations, transport and nonlinear solve. Mechanism applicability, external
validation and extinction interpretation remain explicit caller responsibilities.

Cantera API: https://cantera.org/3.2/python/onedim.html
Primary method example: https://cantera.org/3.2/examples/python/onedim/diffusion_flame.html
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from types import MappingProxyType
from typing import Literal

import numpy as np

from ..adapters.cantera import (
    CanteraGas,
    MechanismBasis,
    NativePhaseHandle,
    ReactiveState,
)
from ..core import finite, immutable_array


_PENDING_COUNTERFLOW_RESULT_ISSUERS: set[object] = set()


def _issue_counterflow_result(*args, **kwargs):
    """Issue a result only while the native solver is completing its run."""
    token = object()
    _PENDING_COUNTERFLOW_RESULT_ISSUERS.add(token)
    try:
        return CounterflowFlameResult(*args, _issuer_token=token, **kwargs)
    except Exception:
        _PENDING_COUNTERFLOW_RESULT_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class CounterflowBoundary:
    """One physical inlet, with a fresh composition and declared mass flux."""

    state: ReactiveState
    mass_flux_kg_m2_s: float

    def __post_init__(self):
        if type(self.state) is not ReactiveState:
            raise TypeError("Use an explicit ReactiveState for each inlet")
        ReactiveState(self.state.temperature_k, self.state.pressure_pa, self.state.mole_fractions)
        finite(self.mass_flux_kg_m2_s, "inlet mass flux", positive=True)


@dataclass(frozen=True, slots=True)
class CounterflowFlameSettings:
    width_m: float = 0.02
    transport_model: Literal["mixture-averaged", "multicomponent"] = "multicomponent"
    soret_enabled: bool = True
    radiation_enabled: bool = False
    refinement_ratio: float = 4.0
    refinement_slope: float = 0.1
    refinement_curve: float = 0.2
    refinement_prune: float = 0.0
    maximum_grid_points: int = 1000
    loglevel: int = 0

    def __post_init__(self):
        finite(self.width_m, "inlet separation", positive=True)
        if self.transport_model not in {"mixture-averaged", "multicomponent"}:
            raise ValueError("Select a supported Cantera gas transport model")
        if self.soret_enabled and self.transport_model != "multicomponent":
            raise ValueError("Soret transport requires the multicomponent model")
        if finite(self.refinement_ratio, "grid refinement ratio") <= 2:
            raise ValueError("Grid refinement ratio must exceed two")
        for name in ("refinement_slope", "refinement_curve"):
            if not 0 < finite(getattr(self, name), name) <= 1:
                raise ValueError("Grid slope and curvature criteria must lie in (0, 1]")
        if not 0 <= finite(self.refinement_prune, "grid pruning criterion") < 1:
            raise ValueError("Grid pruning criterion must lie in [0, 1)")
        if (
            isinstance(self.maximum_grid_points, bool)
            or not isinstance(self.maximum_grid_points, int)
            or self.maximum_grid_points < 10
        ):
            raise ValueError("Maximum grid points must be an integer of at least ten")
        if (
            isinstance(self.loglevel, bool)
            or not isinstance(self.loglevel, int)
            or self.loglevel < 0
        ):
            raise ValueError("Cantera loglevel must be a nonnegative integer")


@dataclass(frozen=True, slots=True)
class CounterflowFlameResult:
    """Owner-issued summary retaining the exact editable native solution."""

    gas_owner: CanteraGas = field(repr=False, compare=False)
    mechanism_basis: MechanismBasis
    phase_handle: NativePhaseHandle = field(repr=False, compare=False)
    fuel: CounterflowBoundary
    oxidizer: CounterflowBoundary
    settings: CounterflowFlameSettings
    pressure_pa: float
    grid_points: int
    peak_temperature_k: float
    peak_temperature_position_m: float
    maximum_velocity_gradient_s_inv: float
    extinct: bool
    native_solution: object = field(repr=False, compare=False)
    solution_sha256: str
    _seal: object = field(default=None, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_COUNTERFLOW_RESULT_ISSUERS:
            raise ValueError("Counterflow results are issued only by the native solver")
        _PENDING_COUNTERFLOW_RESULT_ISSUERS.remove(self._issuer_token)


@dataclass(frozen=True, slots=True)
class CounterflowProfile:
    """Immutable columnar copy of an admitted native flame profile.

    Species arrays use ``(species, axial_point)`` ordering. They are suitable
    for measurements, parameter studies and downstream Python model coupling;
    the originating Cantera solution remains available on the result object.
    """

    solution_sha256: str
    pressure_pa: float
    species_names: tuple[str, ...]
    axial_position_m: np.ndarray
    temperature_k: np.ndarray
    velocity_m_s: np.ndarray
    density_kg_m3: np.ndarray
    mole_fractions: np.ndarray
    mass_fractions: np.ndarray
    heat_release_rate_w_m3: np.ndarray
    strain_rates_s_inv: Mapping[str, float]

    def __post_init__(self):
        if not self.solution_sha256 or not self.species_names:
            raise ValueError("A profile needs its native-solution digest and species order")
        finite(self.pressure_pa, "profile absolute pressure", positive=True)
        names = tuple(self.species_names)
        if len(set(names)) != len(names) or any(not name for name in names):
            raise ValueError("Profile species names must be unique and nonempty")
        object.__setattr__(self, "species_names", names)
        n_points = len(np.asarray(self.axial_position_m))
        if n_points < 3:
            raise ValueError("A counterflow profile needs at least three axial points")
        for name in (
            "axial_position_m",
            "temperature_k",
            "velocity_m_s",
            "density_kg_m3",
            "heat_release_rate_w_m3",
        ):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != (n_points,) or np.any(~np.isfinite(values)):
                raise ValueError(f"{name} must be a finite one-dimensional profile")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        if np.any(np.diff(self.axial_position_m) <= 0):
            raise ValueError("Axial positions must be strictly increasing")
        for name in ("mole_fractions", "mass_fractions"):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != (len(names), n_points) or np.any(~np.isfinite(values)):
                raise ValueError(f"{name} must have one finite row per species")
            if np.any(values < 0):
                raise ValueError(f"{name} cannot contain negative fractions")
            if not np.allclose(np.sum(values, axis=0), 1.0, rtol=1e-8, atol=1e-10):
                raise ValueError(f"{name} columns must sum to one")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        rates = {
            str(name): finite(value, f"{name} strain rate", positive=True)
            for name, value in dict(self.strain_rates_s_inv).items()
        }
        object.__setattr__(self, "strain_rates_s_inv", MappingProxyType(rates))

    def species_mole_fraction(self, species: str) -> np.ndarray:
        """Return a read-only axial mole-fraction view for one exact species."""
        try:
            return self.mole_fractions[self.species_names.index(species)]
        except ValueError as exc:
            raise KeyError(species) from exc

    def species_mass_fraction(self, species: str) -> np.ndarray:
        """Return a read-only axial mass-fraction view for one exact species."""
        try:
            return self.mass_fractions[self.species_names.index(species)]
        except ValueError as exc:
            raise KeyError(species) from exc

    def integrate_heat_release(self, lower_position_m=None, upper_position_m=None) -> float:
        """Integrate the retained volumetric heat-release profile over an axial span.

        The result is a signed per-unit-area integral in W/m², evaluated by
        trapezoidal quadrature of the immutable native-grid samples. Optional
        bounds are clipped only by rejection: neither endpoint may lie outside
        the solved mesh. This is a profile diagnostic, not total flame power;
        no burner area or axisymmetric correction is inferred.
        """
        z = self.axial_position_m
        lower = float(z[0] if lower_position_m is None else finite(
            lower_position_m, "lower integration position"
        ))
        upper = float(z[-1] if upper_position_m is None else finite(
            upper_position_m, "upper integration position"
        ))
        if lower < z[0] or upper > z[-1]:
            raise ValueError("Heat-release integration cannot extrapolate outside the native grid")
        if upper < lower:
            raise ValueError("Upper integration position must not precede lower position")
        if upper == lower:
            return 0.0
        interior = (z > lower) & (z < upper)
        points = np.concatenate(([lower], z[interior], [upper]))
        rates = np.interp(points, z, self.heat_release_rate_w_m3)
        return float(np.sum(0.5 * (rates[:-1] + rates[1:]) * np.diff(points)))

    def sample(self, axial_positions_m) -> Mapping[str, np.ndarray]:
        """Linearly sample the recorded mesh without extrapolating past it.

        This is a measurement-alignment convenience, not a sub-grid flame
        solution. Species entries are exposed as ``X:<name>`` and ``Y:<name>``.
        """
        positions = np.asarray(axial_positions_m, dtype=float)
        if positions.ndim == 0:
            positions = positions.reshape(1)
        if positions.ndim != 1 or not positions.size or np.any(~np.isfinite(positions)):
            raise ValueError("Sample positions must be a nonempty finite vector in metres")
        if np.any(positions < self.axial_position_m[0]) or np.any(
            positions > self.axial_position_m[-1]
        ):
            raise ValueError("Profile sampling cannot extrapolate outside the native grid")

        def readonly(values):
            result = np.array(values, dtype=float, copy=True)
            return immutable_array(result, name="sampled flame profile")

        sampled = {
            "axial_position_m": readonly(positions),
            "temperature_k": readonly(
                np.interp(positions, self.axial_position_m, self.temperature_k)
            ),
            "velocity_m_s": readonly(
                np.interp(positions, self.axial_position_m, self.velocity_m_s)
            ),
            "density_kg_m3": readonly(
                np.interp(positions, self.axial_position_m, self.density_kg_m3)
            ),
            "heat_release_rate_w_m3": readonly(
                np.interp(positions, self.axial_position_m, self.heat_release_rate_w_m3)
            ),
        }
        for index, species in enumerate(self.species_names):
            sampled[f"X:{species}"] = readonly(
                np.interp(positions, self.axial_position_m, self.mole_fractions[index])
            )
            sampled[f"Y:{species}"] = readonly(
                np.interp(positions, self.axial_position_m, self.mass_fractions[index])
            )
        return MappingProxyType(sampled)


def _solution_signature(flame) -> str:
    """Hash the actual native profile and selected solver inputs, not a copy."""
    digest = hashlib.sha256()
    for values in (
        flame.grid,
        flame.T,
        flame.velocity,
        flame.density_mass,
        flame.X,
        flame.Y,
        flame.heat_release_rate,
    ):
        array = np.ascontiguousarray(values, dtype="<f8")
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    for values in (flame.fuel_inlet.X, flame.oxidizer_inlet.X):
        array = np.ascontiguousarray(values, dtype="<f8")
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    for value in (
        flame.P,
        flame.fuel_inlet.mdot,
        flame.oxidizer_inlet.mdot,
        flame.fuel_inlet.T,
        flame.oxidizer_inlet.T,
        flame.transport_model,
        flame.soret_enabled,
        flame.radiation_enabled,
        flame.gas.name,
        CanteraGas._definition(flame.gas),
        tuple(flame.gas.species_names),
    ):
        digest.update(repr(value).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _expected_seal(result: CounterflowFlameResult):
    return (
        id(result.gas_owner),
        id(result.mechanism_basis),
        id(result.phase_handle),
        id(result.native_solution),
        result.solution_sha256,
        result.pressure_pa,
        result.grid_points,
        result.peak_temperature_k,
        result.peak_temperature_position_m,
        result.maximum_velocity_gradient_s_inv,
        result.extinct,
        id(result.fuel),
        id(result.oxidizer),
        id(result.settings),
    )


def solve_counterflow_diffusion_flame(
    gas_owner: CanteraGas,
    fuel: CounterflowBoundary,
    oxidizer: CounterflowBoundary,
    *,
    settings: CounterflowFlameSettings = CounterflowFlameSettings(),
) -> CounterflowFlameResult:
    """Solve one steady opposed-flow flame through the original Cantera owner.

    Inlet mass fluxes are caller inputs, not inferred from a release source.
    The two inlets must share an absolute pressure and the selected mechanism
    must cover both inlet states and the resulting temperature profile.
    """
    if not isinstance(gas_owner, CanteraGas):
        raise TypeError("Pass the actual CanteraGas mechanism owner")
    if type(fuel) is not CounterflowBoundary or type(oxidizer) is not CounterflowBoundary:
        raise TypeError("Use explicit counterflow inlet boundary objects")
    if type(settings) is not CounterflowFlameSettings:
        raise TypeError("Use an explicit CounterflowFlameSettings record")
    settings = CounterflowFlameSettings(
        **{item.name: getattr(settings, item.name) for item in fields(settings)}
    )
    fuel = CounterflowBoundary(fuel.state, fuel.mass_flux_kg_m2_s)
    oxidizer = CounterflowBoundary(oxidizer.state, oxidizer.mass_flux_kg_m2_s)
    basis = gas_owner.basis
    if not isinstance(basis, MechanismBasis):
        raise TypeError("The native mechanism owner must retain a MechanismBasis")
    pressure = finite(fuel.state.pressure_pa, "fuel absolute pressure", positive=True)
    if not math.isclose(pressure, oxidizer.state.pressure_pa, rel_tol=1e-12, abs_tol=1e-8):
        raise ValueError("Opposed inlets must use the same absolute pressure")
    for state in (fuel.state, oxidizer.state):
        basis.require_state(state.temperature_k, pressure)

    # The fuel inlet initializes the source-bound native phase; Cantera owns the
    # subsequent boundary assignment and counterflow solution.
    handle = gas_owner.create_phase(fuel.state)
    flame = gas_owner.ct.CounterflowDiffusionFlame(handle.native_phase, width=settings.width_m)
    flame.P = pressure
    flame.fuel_inlet.mdot = fuel.mass_flux_kg_m2_s
    flame.fuel_inlet.T = fuel.state.temperature_k
    flame.fuel_inlet.X = dict(fuel.state.mole_fractions)
    flame.oxidizer_inlet.mdot = oxidizer.mass_flux_kg_m2_s
    flame.oxidizer_inlet.T = oxidizer.state.temperature_k
    flame.oxidizer_inlet.X = dict(oxidizer.state.mole_fractions)
    flame.transport_model = settings.transport_model
    flame.soret_enabled = settings.soret_enabled
    flame.radiation_enabled = settings.radiation_enabled
    flame.set_refine_criteria(
        ratio=settings.refinement_ratio,
        slope=settings.refinement_slope,
        curve=settings.refinement_curve,
        prune=settings.refinement_prune,
    )
    flame.set_max_grid_points(flame.flame, settings.maximum_grid_points)
    flame.solve(loglevel=settings.loglevel, auto=True)

    temperature = np.asarray(flame.T, dtype=float)
    grid = np.asarray(flame.grid, dtype=float)
    velocity = np.asarray(flame.velocity, dtype=float)
    if (
        temperature.ndim != 1
        or grid.shape != temperature.shape
        or velocity.shape != temperature.shape
        or len(grid) < 3
        or np.any(~np.isfinite(temperature))
        or np.any(~np.isfinite(grid))
        or np.any(~np.isfinite(velocity))
        or np.any(np.diff(grid) <= 0)
    ):
        raise ValueError("Cantera returned an invalid counterflow profile")
    for value in temperature:
        basis.require_state(float(value), pressure)
    peak = int(np.argmax(temperature))
    gradient = np.gradient(velocity, grid, edge_order=2)
    maximum_gradient = float(np.max(np.abs(gradient)))
    finite(maximum_gradient, "maximum axial velocity gradient")
    digest = _solution_signature(flame)
    result = _issue_counterflow_result(
        gas_owner,
        basis,
        handle,
        fuel,
        oxidizer,
        settings,
        pressure,
        len(grid),
        float(temperature[peak]),
        float(grid[peak]),
        maximum_gradient,
        bool(flame.extinct()),
        flame,
        digest,
    )
    object.__setattr__(result, "_seal", _expected_seal(result))
    return result


def verify_counterflow_diffusion_flame(result: CounterflowFlameResult):
    """Reject changed inputs, native source, solver object or summary fields."""
    if type(result) is not CounterflowFlameResult:
        raise TypeError("Verify an owner-issued CounterflowFlameResult")
    if result._seal != _expected_seal(result):
        raise ValueError("Counterflow result owner, input or summary identity changed")
    result.phase_handle.require_current()
    flame = result.native_solution
    if not isinstance(flame, result.gas_owner.ct.CounterflowDiffusionFlame):
        raise TypeError("The retained result is not the original native Cantera solution")
    actual = _solution_signature(flame)
    if actual != result.solution_sha256:
        raise ValueError("The original native counterflow solution has changed")
    temperature = np.asarray(flame.T, dtype=float)
    grid = np.asarray(flame.grid, dtype=float)
    velocity = np.asarray(flame.velocity, dtype=float)
    peak = int(np.argmax(temperature))
    gradient = float(np.max(np.abs(np.gradient(velocity, grid, edge_order=2))))
    observed = (
        float(flame.P),
        len(grid),
        float(temperature[peak]),
        float(grid[peak]),
        gradient,
        bool(flame.extinct()),
    )
    expected = (
        result.pressure_pa,
        result.grid_points,
        result.peak_temperature_k,
        result.peak_temperature_position_m,
        result.maximum_velocity_gradient_s_inv,
        result.extinct,
    )
    if observed != expected:
        raise ValueError("Counterflow summary no longer matches the retained native solution")
    return result


def counterflow_profile(result: CounterflowFlameResult) -> CounterflowProfile:
    """Copy native thermochemical profiles and Cantera strain definitions.

    Native axial strain-rate definitions are retained by name because their
    values are not interchangeable. Cantera owns each calculation.
    """
    verify_counterflow_diffusion_flame(result)
    flame = result.native_solution
    rates = {
        definition: float(flame.strain_rate(definition))
        for definition in ("mean", "max", "potential_flow_fuel", "potential_flow_oxidizer")
    }
    return CounterflowProfile(
        solution_sha256=result.solution_sha256,
        pressure_pa=result.pressure_pa,
        species_names=tuple(flame.gas.species_names),
        axial_position_m=flame.grid,
        temperature_k=flame.T,
        velocity_m_s=flame.velocity,
        density_kg_m3=flame.density_mass,
        mole_fractions=flame.X,
        mass_fractions=flame.Y,
        heat_release_rate_w_m3=flame.heat_release_rate,
        strain_rates_s_inv=rates,
    )
