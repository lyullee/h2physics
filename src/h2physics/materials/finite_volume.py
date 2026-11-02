"""One conservative mobile/trap solver for planar, spherical and cylindrical walls.

Geometry supplies volumes, face areas and integrated diffusion resistances.
All inventories and face integrals use moles of the declared mobile entity.
Temperature is prescribed and spatially uniform; this is not a heat solver.
An optional prescribed solid hydrostatic-stress potential changes the same
conservative face fluxes without introducing a second transport integrator.
"""

import hashlib
import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix

from ..core import finite, immutable_array
from .stress_transport import HydrostaticStressPotential
from .transport import (
    HydrogenCarrier,
    PowerLawSolubilityBoundary,
    SurfaceCondition,
    SurfaceFilmCondition,
    TrapPopulation,
)


def _readonly(value):
    return immutable_array(value, dtype=float, name="finite-volume array")


def _bernoulli_transport(value):
    """Stable x/(exp(x)-1) for the exponentially fitted face equation."""
    value = finite(value, "face stress-potential difference")
    if abs(value) < 1.e-4:
        return 1. - value / 2. + value * value / 12. - value**4 / 720.
    if value > 50.:
        inverse_exponential = math.exp(-value)
        return value * inverse_exponential / (1. - inverse_exponential)
    if value < -50.:
        return -value / (1. - math.exp(value))
    return value / math.expm1(value)


def _stress_face_flow(diffusion_conductance, potential_jump, left_concentration,
                      right_concentration, *, film_conductance=None, film_side=None):
    """Integrate dc/ds-c*dpsi/ds over a constant-resistance face segment.

    ``s`` is the integrated geometric resistance coordinate. Thus this uses
    the same planar/radial conductance and the existing extensive mol/s ledger.
    Potential is piecewise linear in s between sampled points. A film, when
    selected, remains a concentration-driven surface law without an invented
    gas-to-solid stress mapping.
    """
    conductance = finite(diffusion_conductance, "diffusive face conductance", positive=True)
    a = finite(conductance * _bernoulli_transport(-potential_jump),
               "left fitted face coefficient")
    b = finite(conductance * _bernoulli_transport(potential_jump),
               "right fitted face coefficient")
    if film_conductance is not None:
        film = finite(film_conductance, "film conductance")
        if film < 0. or film_side not in {"left", "right"}:
            raise ValueError("Declare a nonnegative film conductance and its face side")
        if film == 0.:
            return 0.
        coefficient = a if film_side == "left" else b
        scale = max(film, coefficient)
        ratio = (film / scale) / (film / scale + coefficient / scale)
        a, b = ratio * a, ratio * b
    return finite(a * left_concentration - b * right_concentration,
                  "stress-driven extensive face flow mol/s")


_TRANSPORT_RESULT_ISSUER = object()


def _transport_result_signature(result):
    digest = hashlib.sha256(repr((result.carrier, result.mesh.geometry,
                                  result.native_solution.success,
                                  result.native_solution.status,
                                  result.native_solution.message,
                                  result.native_solution.nfev,
                                  result.stress_potential)).encode("utf-8"))
    for value in (
        result.mesh.face_positions_m, result.mesh.cell_centers_m,
        result.mesh.face_areas_m2, result.mesh.cell_volumes_m3,
        result.mesh.conductance_m, result.time_s, result.mobile_mol_m3,
        result.trapped_mol_m3, result.left_integrated_mol,
        result.right_integrated_mol, result.wall_inventory_mol,
        result.wall_residual_mol, result.total_residual_mol,
        result.left_inventory_mol, result.right_inventory_mol,
        result.native_solution.t, result.native_solution.y,
    ):
        if value is None:
            digest.update(b"none")
            continue
        array = np.ascontiguousarray(value)
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class DiffusionMesh:
    """Positive-area one-dimensional control volumes with oriented faces.

    ``conductance_m`` multiplies D times a concentration difference to give
    mol/s. Its first/last entries connect a surface to the adjacent center;
    interior entries connect centers. No solid sphere origin is supported.
    """

    face_positions_m: np.ndarray
    cell_centers_m: np.ndarray
    face_areas_m2: np.ndarray
    cell_volumes_m3: np.ndarray
    conductance_m: np.ndarray
    geometry: str

    def _steady_series_resistance(self):
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            segments = 1.0 / self.conductance_m
        if not np.all(np.isfinite(segments)) or np.any(segments <= 0.0):
            raise ValueError("Steady mesh face resistances are outside floating-point range")
        try:
            total = math.fsum(float(value) for value in segments)
        except OverflowError as error:
            raise ValueError("Total steady mesh resistance is outside floating-point range") from error
        if not math.isfinite(total) or total <= 0.0:
            raise ValueError("Total steady mesh resistance is outside floating-point range")
        return segments, total

    def steady_transport_rate_mol_s(self, diffusivity_m2_s: float,
                                    left_concentration_mol_m3: float,
                                    right_concentration_mol_m3: float) -> float:
        """Return signed constant-D steady transport through this mesh's geometry.

        The series resistance uses the same center-to-face conductances as the
        transient owner. Positive rate is left-to-right; traps, transient storage,
        concentration-dependent diffusivity and surface kinetics are excluded.
        """
        diffusivity = finite(diffusivity_m2_s, "steady diffusivity", positive=True)
        left = finite(left_concentration_mol_m3, "left concentration")
        right = finite(right_concentration_mol_m3, "right concentration")
        if min(left, right) < 0.0:
            raise ValueError("Steady boundary concentrations cannot be negative")
        _, resistance = self._steady_series_resistance()
        return finite(diffusivity * (left - right) / resistance,
                      "steady transport rate")

    def steady_concentration_profile_mol_m3(
        self,
        left_concentration_mol_m3: float,
        right_concentration_mol_m3: float,
    ) -> np.ndarray:
        """Return the constant-D steady solution at cell centers.

        The profile is reconstructed from the same integrated face resistances
        used by the transient finite-volume solver. It is suitable as an initial
        condition or an analytic reference, not as a transient state. A fresh
        read-only array is returned on every call.
        """
        left = finite(left_concentration_mol_m3, "left concentration")
        right = finite(right_concentration_mol_m3, "right concentration")
        if min(left, right) < 0.0:
            raise ValueError("Steady boundary concentrations cannot be negative")
        segment_resistance, total_resistance = self._steady_series_resistance()
        center_resistance = np.cumsum(segment_resistance[:-1])
        profile = left - (left - right) * (center_resistance / total_resistance)
        if not np.all(np.isfinite(profile)):
            raise ValueError("Steady concentration profile is outside floating-point range")
        return _readonly(profile)

    def __post_init__(self):
        names = ("face_positions_m", "cell_centers_m", "face_areas_m2",
                 "cell_volumes_m3", "conductance_m")
        for name in names:
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        n = len(self.cell_centers_m)
        if n < 3 or any(getattr(self, key).shape != shape for key, shape in (
                ("face_positions_m", (n+1,)), ("cell_centers_m", (n,)),
                ("face_areas_m2", (n+1,)), ("cell_volumes_m3", (n,)),
                ("conductance_m", (n+1,)))):
            raise ValueError("Diffusion mesh needs at least three consistent cells")
        if any(not np.all(np.isfinite(getattr(self, key))) for key in names):
            raise ValueError("Diffusion mesh arrays must be finite")
        if (np.any(np.diff(self.face_positions_m) <= 0)
                or np.any(self.cell_centers_m <= self.face_positions_m[:-1])
                or np.any(self.cell_centers_m >= self.face_positions_m[1:])
                or any(np.any(getattr(self, key) <= 0) for key in names[2:])):
            raise ValueError("Mesh volumes, areas, conductances and center placement are invalid")
        if not self.geometry.strip():
            raise ValueError("Declare diffusion geometry")

    @classmethod
    def planar(cls, thickness_m: float, cells: int, *, area_m2: float = 1.):
        length = finite(thickness_m, "thickness", positive=True)
        area = finite(area_m2, "membrane area", positive=True)
        cls._cells(cells)
        faces = np.linspace(0., length, cells+1)
        centers = (faces[:-1]+faces[1:])/2
        distances = np.diff(np.r_[faces[0], centers, faces[-1]])
        return cls(faces, centers, np.full(cells+1, area),
                   area*np.diff(faces), area/distances, "planar")

    @classmethod
    def spherical_shell(cls, inner_radius_m: float, outer_radius_m: float, cells: int):
        inner = finite(inner_radius_m, "inner radius", positive=True)
        outer = finite(outer_radius_m, "outer radius", positive=True)
        cls._cells(cells)
        if outer <= inner:
            raise ValueError("Outer shell radius must exceed inner radius")
        faces = np.linspace(inner, outer, cells+1)
        centers = (faces[:-1]+faces[1:])/2
        nodes = np.r_[inner, centers, outer]
        # Integral dr/(4*pi*r^2), using a stable algebraic difference.
        conductance = 4*np.pi*nodes[:-1]*nodes[1:]/np.diff(nodes)
        volumes = 4*np.pi/3*np.diff(faces)*(faces[1:]**2+faces[:-1]*faces[1:]+faces[:-1]**2)
        return cls(faces, centers, 4*np.pi*faces**2, volumes, conductance, "spherical_shell")

    @classmethod
    def cylindrical_shell(
        cls, inner_radius_m: float, outer_radius_m: float, length_m: float, cells: int,
    ):
        """Build an axisymmetric radial mesh for a finite-length hollow cylinder.

        End-face transport and axial gradients are excluded. The retained lateral
        shell volume and face areas include the declared cylinder length; the
        center-to-center resistance integrates ``dr / (2*pi*L*r*D)`` exactly for
        piecewise-constant D. Use a separate 2-D/3-D owner when end effects matter.
        """
        inner = finite(inner_radius_m, "inner radius", positive=True)
        outer = finite(outer_radius_m, "outer radius", positive=True)
        length = finite(length_m, "cylinder length", positive=True)
        cls._cells(cells)
        if outer <= inner:
            raise ValueError("Outer radius must exceed inner radius")
        faces = np.linspace(inner, outer, cells + 1)
        centers = (faces[:-1] + faces[1:]) / 2
        nodes = np.r_[inner, centers, outer]
        logarithmic_span = np.log1p(np.diff(nodes) / nodes[:-1])
        conductance = 2 * np.pi * length / logarithmic_span
        areas = 2 * np.pi * length * faces
        volumes = np.pi * length * np.diff(faces) * (faces[1:] + faces[:-1])
        return cls(faces, centers, areas, volumes, conductance, "cylindrical_shell")

    @staticmethod
    def _cells(cells):
        if isinstance(cells, bool) or not isinstance(cells, int) or cells < 3:
            raise ValueError("Diffusion needs at least three integer cells")


@dataclass(frozen=True, slots=True)
class TransportBoundary:
    """Use None at a face owned by a finite surface inventory."""

    left: SurfaceCondition | SurfaceFilmCondition | None
    right: SurfaceCondition | SurfaceFilmCondition | None


@dataclass(frozen=True, slots=True)
class FiniteSurfaceInventory:
    """An amount in mol(mobile entity), exchanging only through its own face.

    The callback receives time in seconds and the current amount in moles.
    It may prescribe concentration or signed coordinate flux. A positive
    floor guards property callbacks; crossing it rejects the integration
    window, without clipping mass or claiming a localized depletion event.
    """

    initial_mol: float
    minimum_mol: float
    condition: Callable[[float, float], SurfaceCondition]
    evidence: str

    def __post_init__(self):
        finite(self.initial_mol, "initial surface inventory", positive=True)
        floor = finite(self.minimum_mol, "minimum surface inventory")
        if floor < 0 or self.initial_mol <= floor:
            raise ValueError("Initial inventory must exceed its nonnegative floor")
        if not self.evidence.strip():
            raise ValueError("Finite surface inventory needs boundary evidence")


@dataclass(frozen=True, slots=True)
class TransportResult:
    carrier: HydrogenCarrier
    mesh: DiffusionMesh
    time_s: np.ndarray
    mobile_mol_m3: np.ndarray
    trapped_mol_m3: np.ndarray
    left_integrated_mol: np.ndarray
    right_integrated_mol: np.ndarray
    wall_inventory_mol: np.ndarray
    wall_residual_mol: np.ndarray
    total_residual_mol: np.ndarray
    left_inventory_mol: np.ndarray | None
    right_inventory_mol: np.ndarray | None
    native_solution: object
    _issuer: object = field(repr=False, compare=False)
    _signature: str = field(init=False, repr=False, compare=False)
    stress_potential: HydrostaticStressPotential | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer is not _TRANSPORT_RESULT_ISSUER:
            raise TypeError("Use DiffusionDomain.simulate to issue a transport result")
        for name in ("time_s", "mobile_mol_m3", "trapped_mol_m3", "left_integrated_mol",
                     "right_integrated_mol", "wall_inventory_mol", "wall_residual_mol",
                     "total_residual_mol", "left_inventory_mol", "right_inventory_mol"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, _readonly(getattr(self, name)))
        self._validate_native_projection()
        object.__setattr__(self, "_signature", _transport_result_signature(self))

    def _validate_native_projection(self):
        solution = self.native_solution
        n = len(self.mesh.cell_centers_m)
        if not solution.success or not np.array_equal(self.time_s, solution.t):
            raise ValueError("Transport result must retain a successful original integration grid")
        if self.trapped_mol_m3.ndim != 3:
            raise ValueError("Trapped concentration must retain time, trap, and cell axes")
        nt = self.trapped_mol_m3.shape[1]
        field_size = (nt + 1) * n
        if (self.mobile_mol_m3.shape != (len(self.time_s), n)
                or self.trapped_mol_m3.shape[0] != len(self.time_s)
                or solution.y.shape != (field_size + int(self.left_inventory_mol is not None)
                                        + int(self.right_inventory_mol is not None) + 2,
                                        len(self.time_s))):
            raise ValueError("Transport histories do not match the native state layout")
        if (not np.array_equal(self.mobile_mol_m3, solution.y[:n].T)
                or not np.array_equal(
                    self.trapped_mol_m3,
                    solution.y[n:field_size].T.reshape(len(self.time_s), nt, n),
                )
                or not np.array_equal(self.left_integrated_mol, solution.y[-2])
                or not np.array_equal(self.right_integrated_mol, solution.y[-1])):
            raise ValueError("Transport fields must reproduce the original native state")
        inventory = (self.mobile_mol_m3 + self.trapped_mol_m3.sum(axis=1)) @ self.mesh.cell_volumes_m3
        if not np.array_equal(self.wall_inventory_mol, inventory):
            raise ValueError("Wall inventory must reproduce the native volume integral")
        wall_residual = inventory - inventory[0] - self.left_integrated_mol + self.right_integrated_mol
        if not np.array_equal(self.wall_residual_mol, wall_residual):
            raise ValueError("Wall residual must reproduce inventory and face ledgers")
        total_residual = inventory - inventory[0]
        next_inventory_index = field_size
        for name, amounts, face_integral in (
            ("left", self.left_inventory_mol, self.left_integrated_mol),
            ("right", self.right_inventory_mol, self.right_integrated_mol),
        ):
            if amounts is None:
                total_residual += -face_integral if name == "left" else face_integral
            else:
                if not np.array_equal(amounts, solution.y[next_inventory_index]):
                    raise ValueError(f"{name} surface inventory differs from the native state")
                total_residual += amounts - amounts[0]
                next_inventory_index += 1
        if not np.array_equal(self.total_residual_mol, total_residual):
            raise ValueError("Total residual must reproduce wall and surface inventories")

    def require_current(self):
        self._validate_native_projection()
        if self._signature != _transport_result_signature(self):
            raise ValueError("Original native material-transport result changed after capture")
        return self

    @property
    def function_evaluations(self):
        self.require_current()
        return self.native_solution.nfev


class DiffusionDomain:
    """Shared BDF finite-volume integration, including optional finite faces."""

    def __init__(self, carrier: HydrogenCarrier, mesh: DiffusionMesh,
                 diffusivity_m2_s: Callable[[float], float], *,
                 traps: tuple[TrapPopulation, ...] = ()):
        self.carrier, self.mesh = carrier, mesh
        self.diffusivity, self.traps = diffusivity_m2_s, tuple(traps)

    def simulate(self, time_s, initial_mobile_mol_m3, *,
                 boundary: Callable[[float], TransportBoundary] | PowerLawSolubilityBoundary,
                 temperature_k: Callable[[float], float], initial_trapped_mol_m3=None,
                 left_inventory: FiniteSurfaceInventory | None = None,
                 right_inventory: FiniteSurfaceInventory | None = None,
                 stress_potential: HydrostaticStressPotential | None = None,
                 relative_tolerance: float = 1e-8, absolute_tolerance_mol_m3: float = 1e-10,
                 maximum_step_s: float = np.inf) -> TransportResult:
        times = np.asarray(time_s, dtype=float)
        if stress_potential is not None:
            if type(stress_potential) is not HydrostaticStressPotential:
                raise TypeError("Use an explicit HydrostaticStressPotential for solid drift")
            if stress_potential.carrier != self.carrier:
                raise ValueError("Stress partial molar volume and diffusion must share the mobile carrier")
        n, nt = len(self.mesh.cell_centers_m), len(self.traps)
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or np.any(np.diff(times) <= 0)):
            raise ValueError("Diffusion output times must be finite and increasing")
        mobile = np.asarray(initial_mobile_mol_m3, dtype=float)
        trapped = (np.zeros((nt, n)) if initial_trapped_mol_m3 is None
                   else np.asarray(initial_trapped_mol_m3, dtype=float))
        if mobile.shape != (n,) or trapped.shape != (nt, n):
            raise ValueError("Initial mobile/trapped concentrations must match cells and traps")
        if (not np.all(np.isfinite(mobile)) or not np.all(np.isfinite(trapped))
                or min(mobile.min(), trapped.min(initial=0)) < 0):
            raise ValueError("Initial concentrations must be finite and nonnegative")
        for i, trap in enumerate(self.traps):
            if np.any(trapped[i] > trap.site_concentration_mol_m3):
                raise ValueError("Initial trapped concentration exceeds site capacity")
        if (isinstance(boundary, PowerLawSolubilityBoundary)
                and boundary.solubility.carrier != self.carrier):
            raise ValueError("Surface solubility carrier must match the diffusion domain carrier")
        if not callable(boundary) and not isinstance(boundary, PowerLawSolubilityBoundary):
            raise TypeError("Boundary must be a callback or explicit PowerLawSolubilityBoundary")
        finite(relative_tolerance, "relative tolerance", positive=True)
        finite(absolute_tolerance_mol_m3, "absolute concentration tolerance", positive=True)
        if maximum_step_s <= 0 or np.isnan(maximum_step_s):
            raise ValueError("Maximum diffusion step must be positive")
        field_size = (nt+1)*n
        stores = (("left", left_inventory), ("right", right_inventory))
        indices = {}
        initial = list(np.r_[mobile, trapped.ravel()])
        for name, store in stores:
            if store is not None:
                indices[name] = len(initial)
                initial.append(store.initial_mol)
        initial.extend((0., 0.))
        volumes, conductance = self.mesh.cell_volumes_m3, self.mesh.conductance_m
        stress_positions = _readonly(np.r_[self.mesh.face_positions_m[0],
                                          self.mesh.cell_centers_m,
                                          self.mesh.face_positions_m[-1]])

        def rhs(time, values):
            c = values[:n]
            trapped_c = values[n:field_size].reshape(nt, n)
            temperature = finite(temperature_k(time), "prescribed temperature", positive=True)
            diffusion = finite(self.diffusivity(temperature), "diffusivity", positive=True)
            faces = (boundary.at_temperature(time, temperature)
                     if isinstance(boundary, PowerLawSolubilityBoundary)
                     else boundary(time))
            conditions = []
            for name, store in stores:
                face = getattr(faces, name)
                if store is not None:
                    if face is not None:
                        raise ValueError("Finite inventory and imposed face cannot both own a boundary")
                    amount = values[indices[name]]
                    if not np.isfinite(amount) or amount <= store.minimum_mol:
                        raise ValueError(f"{name} surface inventory reached its floor; window rejected")
                    face = store.condition(time, float(amount))
                if not isinstance(face, (SurfaceCondition, SurfaceFilmCondition)):
                    raise ValueError("Every face needs a surface condition, film condition or a finite inventory")
                conditions.append(face)
            left, right = conditions
            flow = np.empty(n+1)
            jumps = None
            if stress_potential is not None:
                potential = stress_potential.dimensionless_potential(time, stress_positions, temperature)
                with np.errstate(over="ignore", invalid="ignore"):
                    jumps = np.diff(potential)
                if not np.all(np.isfinite(jumps)):
                    raise ValueError("Solid stress-potential differences exceed finite arithmetic")
            # Uniform stress preserves the original Fick/film evaluation path.
            if jumps is None or not np.any(jumps != 0.):
                flow[1:-1] = -diffusion*conductance[1:-1]*np.diff(c)
                if isinstance(left, SurfaceFilmCondition):
                    bulk, velocity = left.at(time, temperature)
                    film = velocity * self.mesh.face_areas_m2[0]
                    solid = diffusion * conductance[0]
                    low, high = min(film, solid), max(film, solid)
                    effective = 0.0 if low == 0.0 else low / (1.0 + low / high)
                    flow[0] = effective * (bulk - c[0])
                else:
                    flow[0] = (self.mesh.face_areas_m2[0]*left.value if left.kind == "flux"
                               else diffusion*conductance[0]*(left.value-c[0]))
                if isinstance(right, SurfaceFilmCondition):
                    bulk, velocity = right.at(time, temperature)
                    film = velocity * self.mesh.face_areas_m2[-1]
                    solid = diffusion * conductance[-1]
                    low, high = min(film, solid), max(film, solid)
                    effective = 0.0 if low == 0.0 else low / (1.0 + low / high)
                    flow[-1] = effective * (c[-1] - bulk)
                else:
                    flow[-1] = (self.mesh.face_areas_m2[-1]*right.value if right.kind == "flux"
                                else diffusion*conductance[-1]*(c[-1]-right.value))
            else:
                for face in range(1, n):
                    flow[face] = _stress_face_flow(
                        diffusion * conductance[face], jumps[face], c[face-1], c[face])
                for index, condition, side in ((0, left, "left"), (-1, right, "right")):
                    if isinstance(condition, SurfaceCondition) and condition.kind == "flux":
                        flow[index] = finite(self.mesh.face_areas_m2[index] * condition.value,
                                             "imposed extensive surface flow mol/s")
                        continue
                    if isinstance(condition, SurfaceFilmCondition):
                        bulk, velocity = condition.at(time, temperature)
                        film = finite(velocity * self.mesh.face_areas_m2[index], "film face conductance")
                    else:
                        bulk, film = condition.value, None
                    concentrations = (bulk, c[0]) if side == "left" else (c[-1], bulk)
                    flow[index] = _stress_face_flow(
                        diffusion * conductance[index], jumps[index], *concentrations,
                        film_conductance=film, film_side=side if film is not None else None)
            trap_rates = np.empty((nt, n))
            for i, trap in enumerate(self.traps):
                capture = finite(trap.capture_m3_mol_s(temperature), "trap capture coefficient")
                release = finite(trap.release_s_inv(temperature), "trap release rate")
                if min(capture, release) < 0:
                    raise ValueError("Trap capture/release callbacks must be nonnegative")
                trap_rates[i] = capture*c*(trap.site_concentration_mol_m3-trapped_c[i])-release*trapped_c[i]
            derivative = np.empty(len(initial))
            derivative[:n] = -np.diff(flow)/volumes-trap_rates.sum(axis=0)
            derivative[n:field_size] = trap_rates.ravel()
            if left_inventory is not None:
                derivative[indices["left"]] = -flow[0]
            if right_inventory is not None:
                derivative[indices["right"]] = flow[-1]
            derivative[-2:] = flow[[0, -1]]
            return derivative

        amount_atol = absolute_tolerance_mol_m3*volumes.min()
        atol = np.r_[np.full(field_size, absolute_tolerance_mol_m3),
                     np.full(len(initial)-field_size, amount_atol)]
        pattern = lil_matrix((len(initial), len(initial)), dtype=int)
        for cell in range(n):
            pattern[cell, max(0, cell-1):min(n, cell+2)] = 1
            for i in range(nt):
                index = (i+1)*n+cell
                pattern[cell, index] = 1
                pattern[index, [cell, index]] = 1
        for name, cell, ledger in (("left", 0, len(initial)-2),
                                   ("right", n-1, len(initial)-1)):
            pattern[ledger, cell] = 1
            if name in indices:
                index = indices[name]
                pattern[cell, index] = 1
                pattern[index, [cell, index]] = 1
                pattern[ledger, index] = 1
        solution = solve_ivp(rhs, (times[0], times[-1]), initial, method="BDF", t_eval=times,
                             rtol=relative_tolerance, atol=atol, max_step=maximum_step_s,
                             jac_sparsity=pattern.tocsr())
        if not solution.success or solution.y.shape[1] != len(times):
            raise RuntimeError(f"Material transport failed: {solution.message}")
        mobile = solution.y[:n].T
        trapped = solution.y[n:field_size].T.reshape(len(times), nt, n)
        allowance = 10*absolute_tolerance_mol_m3
        if mobile.min() < -allowance or trapped.min(initial=0) < -allowance:
            raise RuntimeError("Transport left the declared nonnegative concentration tolerance")
        for i, trap in enumerate(self.traps):
            if np.any(trapped[:, i] > trap.site_concentration_mol_m3+allowance):
                raise RuntimeError("Transport exceeded finite trap capacity")
        inventory = (mobile+trapped.sum(axis=1)) @ volumes
        qleft, qright = solution.y[-2:]
        wall_residual = inventory-inventory[0]-qleft+qright
        total_residual = inventory-inventory[0]
        amounts = {}
        for name, store in stores:
            amounts[name] = None if store is None else solution.y[indices[name]]
            if store is not None:
                total_residual += amounts[name]-amounts[name][0]
            else:
                total_residual += -qleft if name == "left" else qright
        return TransportResult(self.carrier, self.mesh, times, mobile, trapped, qleft, qright,
                               inventory, wall_residual, total_residual,
                               amounts["left"], amounts["right"], solution,
                               _TRANSPORT_RESULT_ISSUER, stress_potential=stress_potential)
