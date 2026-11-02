"""Fixed-temperature radial porous-reservoir inventory model with injected properties.

This finite-volume model advances a single gas phase in concentric annular cells
with fixed cell temperatures that may vary radially. Density and dynamic
viscosity are supplied by the caller. It does not supply a geological
constitutive law, multiphase flow, capillarity, salt
creep, geomechanics, thermal prediction, or a site-specific well model.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
import hashlib
import math

import numpy as np
from scipy.optimize import least_squares

from ..core import PropertyBasis, PropertyProvider, ThermoState, finite, immutable_array


_PENDING_RESULT_ISSUERS: set[object] = set()


def _issue_result(**values):
    token = object()
    _PENDING_RESULT_ISSUERS.add(token)
    try:
        return PorousReservoirResult(**values, _issuer_token=token)
    except Exception:
        _PENDING_RESULT_ISSUERS.discard(token)
        raise


def _update_array_digest(digest, value):
    array = np.asarray(value)
    digest.update(repr((array.dtype.str, array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _vector(value, *, name: str, positive: bool = False, nonnegative: bool = False):
    array = np.asarray(value, dtype=float)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a nonempty finite one-dimensional array")
    if positive and np.any(array <= 0.0):
        raise ValueError(f"{name} must be positive")
    if nonnegative and np.any(array < 0.0):
        raise ValueError(f"{name} must be nonnegative")
    return array


@dataclass(frozen=True, slots=True)
class PorousReservoirGeometry:
    """Caller-defined concentric-cell geometry and uniform rock properties."""

    radial_faces_m: np.ndarray
    thickness_m: float
    porosity: np.ndarray
    permeability_m2: np.ndarray
    temperature_k: np.ndarray
    evidence_id: str

    def __post_init__(self):
        faces = _vector(self.radial_faces_m, name="radial faces", positive=True)
        porosity = _vector(self.porosity, name="porosity", positive=True)
        permeability = _vector(self.permeability_m2, name="permeability", positive=True)
        temperature = _vector(self.temperature_k, name="temperature", positive=True)
        cells = faces.size - 1
        if cells < 1 or np.any(np.diff(faces) <= 0.0):
            raise ValueError("radial faces must increase and define at least one cell")
        if any(array.size != cells for array in (porosity, permeability, temperature)):
            raise ValueError("porosity, permeability and temperature must match cell count")
        if np.any(porosity >= 1.0):
            raise ValueError("porosity must be below one")
        finite(self.thickness_m, "thickness_m", positive=True)
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("evidence_id must identify the supplied geometry/property basis")
        for name, value in (("radial_faces_m", faces), ("porosity", porosity),
                            ("permeability_m2", permeability), ("temperature_k", temperature)):
            object.__setattr__(self, name, immutable_array(value, name=name))

    @property
    def cell_count(self) -> int:
        return self.porosity.size

    @property
    def pore_volume_m3(self) -> np.ndarray:
        values = math.pi * self.thickness_m * np.diff(self.radial_faces_m**2) * self.porosity
        return immutable_array(values, name="pore_volume_m3")

    @property
    def radial_centers_m(self) -> np.ndarray:
        return immutable_array(np.sqrt(self.radial_faces_m[:-1] * self.radial_faces_m[1:]),
                               name="radial_centers_m")


@dataclass(frozen=True, slots=True)
class PorousReservoirSchedule:
    """Sampled pressure boundaries and signed well flow on one declared clock.

    Positive well flow injects mass; negative flow withdraws it. Select exactly
    one of a prescribed well-flow series or a well-pressure series. Pressure
    samples use the same clock and bounds as the reservoir and act at the inner
    radial face through the model's single-phase Darcy transmissibility.
    """

    time_s: np.ndarray
    initial_pressure_pa: np.ndarray
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    well_mass_flow_kg_s: np.ndarray | None
    clock_id: str
    well_pressure_pa: np.ndarray | None = None

    def __post_init__(self):
        time = _vector(self.time_s, name="time_s", nonnegative=True)
        pressure = _vector(self.initial_pressure_pa, name="initial_pressure_pa", positive=True)
        if (self.well_mass_flow_kg_s is None) == (self.well_pressure_pa is None):
            raise ValueError("select exactly one of prescribed well mass flow or well pressure")
        flow = None if self.well_mass_flow_kg_s is None else _vector(
            self.well_mass_flow_kg_s, name="well_mass_flow_kg_s")
        well_pressure = None if self.well_pressure_pa is None else _vector(
            self.well_pressure_pa, name="well_pressure_pa", positive=True)
        if time.size < 2 or np.any(np.diff(time) <= 0.0):
            raise ValueError("time_s must have at least two strictly increasing samples")
        if flow is not None and flow.size != time.size:
            raise ValueError("well-flow schedule must match time_s")
        if well_pressure is not None and well_pressure.size != time.size:
            raise ValueError("well-pressure schedule must match time_s")
        finite(self.minimum_pressure_pa, "minimum_pressure_pa", positive=True)
        finite(self.maximum_pressure_pa, "maximum_pressure_pa", positive=True)
        if self.minimum_pressure_pa >= self.maximum_pressure_pa:
            raise ValueError("pressure bounds must increase")
        if np.any(pressure < self.minimum_pressure_pa) or np.any(pressure > self.maximum_pressure_pa):
            raise ValueError("initial pressure lies outside the declared pressure bounds")
        if well_pressure is not None and (np.any(well_pressure < self.minimum_pressure_pa)
                                          or np.any(well_pressure > self.maximum_pressure_pa)):
            raise ValueError("well pressure lies outside the declared pressure bounds")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("clock_id is required")
        object.__setattr__(self, "time_s", immutable_array(time, name="time_s"))
        object.__setattr__(self, "initial_pressure_pa", immutable_array(pressure, name="initial_pressure_pa"))
        if flow is not None:
            object.__setattr__(self, "well_mass_flow_kg_s",
                               immutable_array(flow, name="well_mass_flow_kg_s"))
        if well_pressure is not None:
            object.__setattr__(self, "well_pressure_pa",
                               immutable_array(well_pressure, name="well_pressure_pa"))


@dataclass(frozen=True, slots=True)
class PorousReservoirResult:
    """Implicit-step pressure and mass ledger for a single-phase radial run."""

    time_s: np.ndarray
    pressure_pa: np.ndarray
    cell_gas_mass_kg: np.ndarray
    cumulative_well_mass_kg: np.ndarray
    cumulative_outer_boundary_mass_kg: np.ndarray
    per_step_mass_residual_kg: np.ndarray
    geometry: PorousReservoirGeometry
    schedule: PorousReservoirSchedule
    property_evidence_id: str
    outer_boundary_temperature_k: float
    well_boundary_temperature_k: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_RESULT_ISSUERS:
            raise ValueError("Use PorousReservoir.run() to issue a reservoir result")
        _PENDING_RESULT_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        if type(self.geometry) is not PorousReservoirGeometry or type(self.schedule) is not PorousReservoirSchedule:
            raise TypeError("Reservoir results require the original typed geometry and schedule")
        time = _vector(self.time_s, name="time_s", nonnegative=True)
        pressure = np.asarray(self.pressure_pa, dtype=float)
        mass = np.asarray(self.cell_gas_mass_kg, dtype=float)
        cumulative = _vector(self.cumulative_well_mass_kg, name="cumulative_well_mass_kg")
        cumulative_outer = _vector(self.cumulative_outer_boundary_mass_kg,
                                   name="cumulative_outer_boundary_mass_kg")
        residual = _vector(self.per_step_mass_residual_kg, name="per_step_mass_residual_kg")
        expected = (time.size, self.geometry.cell_count)
        if pressure.shape != expected or mass.shape != expected:
            raise ValueError("pressure and cell mass arrays must have shape (time, cell)")
        if not np.all(np.isfinite(pressure)) or not np.all(np.isfinite(mass)) or np.any(mass < 0.0):
            raise ValueError("pressure/mass results must be finite and mass nonnegative")
        if np.any(pressure < self.schedule.minimum_pressure_pa) or np.any(
                pressure > self.schedule.maximum_pressure_pa):
            raise ValueError("result pressure lies outside its declared bounds")
        if cumulative.size != time.size or cumulative_outer.size != time.size or residual.size != time.size - 1:
            raise ValueError("cumulative mass and step residual axes are inconsistent")
        if not np.array_equal(time, self.schedule.time_s):
            raise ValueError("result and schedule clocks differ")
        if not isinstance(self.property_evidence_id, str) or not self.property_evidence_id.strip():
            raise ValueError("property_evidence_id is required")
        boundary_temperature = finite(
            self.outer_boundary_temperature_k, "outer_boundary_temperature_k", positive=True)
        well_temperature = finite(
            self.well_boundary_temperature_k, "well_boundary_temperature_k", positive=True)
        for name, value in (("time_s", time), ("pressure_pa", pressure), ("cell_gas_mass_kg", mass),
                            ("cumulative_well_mass_kg", cumulative),
                            ("cumulative_outer_boundary_mass_kg", cumulative_outer),
                            ("per_step_mass_residual_kg", residual)):
            object.__setattr__(self, name, immutable_array(value, name=name))
        object.__setattr__(self, "outer_boundary_temperature_k", boundary_temperature)
        object.__setattr__(self, "well_boundary_temperature_k", well_temperature)
        object.__setattr__(self, "_seal", self._content_digest())

    def _content_digest(self) -> str:
        digest = hashlib.sha256()
        digest.update(repr((
            id(self.geometry), id(self.schedule), self.property_evidence_id,
            self.outer_boundary_temperature_k, self.well_boundary_temperature_k,
            self.geometry.thickness_m,
            self.geometry.evidence_id, self.schedule.minimum_pressure_pa,
            self.schedule.maximum_pressure_pa, self.schedule.clock_id,
        )).encode("utf-8"))
        for value in (
            self.geometry.radial_faces_m, self.geometry.porosity,
            self.geometry.permeability_m2, self.geometry.temperature_k,
            self.schedule.time_s, self.schedule.initial_pressure_pa,
            self.schedule.well_mass_flow_kg_s, self.schedule.well_pressure_pa,
            self.time_s, self.pressure_pa,
            self.cell_gas_mass_kg, self.cumulative_well_mass_kg,
            self.cumulative_outer_boundary_mass_kg, self.per_step_mass_residual_kg,
        ):
            if value is None:
                digest.update(b"<none>")
            else:
                _update_array_digest(digest, value)
        return digest.hexdigest()

    def require_current(self) -> "PorousReservoirResult":
        """Reject altered result arrays or changed retained input content."""
        if not self._seal or self._content_digest() != self._seal:
            raise ValueError("Porous-reservoir result or retained input changed after the run")
        return self


class PorousReservoir:
    """One-dimensional fixed-temperature single-gas Darcy reservoir.

    Cell temperatures are prescribed and do not evolve. An implicit
    backward-Euler mass balance is solved per interval. The well
    source may be a prescribed signed mass rate or an inner-face pressure
    boundary connected by the same single-phase radial Darcy closure. An
    optional sampled outer pressure adds another pressure boundary. No
    wellbore, skin, multiphase or site law is inferred.
    """

    def __init__(self, *, geometry: PorousReservoirGeometry,
                 density_kg_m3: Callable[[float, float], float] | None = None,
                 viscosity_pa_s: Callable[[float, float], float] | None = None,
                 property_provider: PropertyProvider | None = None,
                 property_evidence_id: str):
        if property_provider is not None:
            if density_kg_m3 is not None or viscosity_pa_s is not None:
                raise ValueError("Select either a PropertyProvider or separate density/viscosity callbacks")
            if not isinstance(property_provider, PropertyProvider):
                raise TypeError("property_provider must implement the explicit PropertyProvider contract")
            provider_basis = property_provider.basis
            if type(provider_basis) is not PropertyBasis:
                raise TypeError("PropertyProvider.basis must be a package PropertyBasis")
            self._property_basis = provider_basis
        else:
            if not callable(density_kg_m3) or not callable(viscosity_pa_s):
                raise TypeError("Supply a PropertyProvider or both density and viscosity callbacks")
            self._property_basis = None
        if not isinstance(property_evidence_id, str) or not property_evidence_id.strip():
            raise ValueError("property_evidence_id must identify the property source and basis")
        self.geometry = geometry
        self.density_kg_m3 = density_kg_m3
        self.viscosity_pa_s = viscosity_pa_s
        self.property_provider = property_provider
        self.property_evidence_id = property_evidence_id

    @classmethod
    def from_property_provider(cls, *, geometry: PorousReservoirGeometry,
                               property_provider: PropertyProvider,
                               property_evidence_id: str) -> "PorousReservoir":
        """Bind a shared PT property owner without extracting parallel callbacks.

        This accepts the package ``PropertyProvider`` protocol, including
        ``CoolPropProperties``. The model still admits only single gas-like
        states; an EOS phase flash does not supply porous multiphase physics.
        """
        return cls(
            geometry=geometry, property_provider=property_provider,
            property_evidence_id=property_evidence_id,
        )

    def _properties(self, pressure_pa: float, temperature_k: float) -> tuple[float, float]:
        if self.property_provider is not None:
            if self.property_provider.basis != self._property_basis:
                raise ValueError("PropertyProvider basis changed after reservoir binding")
            state = self.property_provider.state_pt(pressure_pa, temperature_k)
            if type(state) is not ThermoState:
                raise TypeError("PropertyProvider.state_pt must return the package ThermoState")
            self._property_basis.require_compatible(state.basis)
            if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
                raise ValueError(
                    f"Single-gas Darcy reservoir does not admit EOS phase {state.phase!r}"
                )
            density = finite(state.density_kg_m3, "gas density", positive=True)
            if state.viscosity_pa_s is None:
                raise ValueError("PropertyProvider state has no single-phase gas viscosity")
            viscosity = finite(state.viscosity_pa_s, "gas viscosity", positive=True)
            return density, viscosity
        density = finite(self.density_kg_m3(pressure_pa, temperature_k), "gas density", positive=True)
        viscosity = finite(self.viscosity_pa_s(pressure_pa, temperature_k), "gas viscosity", positive=True)
        return density, viscosity

    def run(self, schedule: PorousReservoirSchedule, *, outer_pressure_pa=None,
            outer_temperature_k: float | None = None,
            well_temperature_k: float | None = None,
            max_nfev: int = 300, xtol: float = 1e-10, ftol: float = 1e-10,
            gtol: float = 1e-10) -> PorousReservoirResult:
        """Solve the sampled schedule; failed convergence raises ``RuntimeError``."""
        geometry = self.geometry
        n = geometry.cell_count
        if schedule.initial_pressure_pa.size != n:
            raise ValueError("one initial pressure is required per radial cell")
        if schedule.well_pressure_pa is None:
            if well_temperature_k is not None:
                raise ValueError("well_temperature_k requires a pressure-driven well boundary")
            well_boundary_temperature = float(geometry.temperature_k[0])
        else:
            well_boundary_temperature = finite(
                geometry.temperature_k[0] if well_temperature_k is None else well_temperature_k,
                "well_temperature_k", positive=True)
        if isinstance(max_nfev, bool) or not isinstance(max_nfev, int) or max_nfev < 1:
            raise ValueError("max_nfev must be a positive integer")
        for name, value in (("xtol", xtol), ("ftol", ftol), ("gtol", gtol)):
            finite(value, name, positive=True)
        if outer_pressure_pa is None:
            outer_pressure = None
            if outer_temperature_k is not None:
                raise ValueError("outer_temperature_k requires an outer pressure boundary")
            boundary_temperature = float(geometry.temperature_k[-1])
        else:
            outer_pressure = _vector(outer_pressure_pa, name="outer_pressure_pa", positive=True)
            if outer_pressure.size != schedule.time_s.size:
                raise ValueError("outer pressure must match the schedule clock")
            if np.any(outer_pressure < schedule.minimum_pressure_pa) or np.any(
                    outer_pressure > schedule.maximum_pressure_pa):
                raise ValueError("outer pressure lies outside declared pressure bounds")
            boundary_temperature = finite(
                geometry.temperature_k[-1] if outer_temperature_k is None else outer_temperature_k,
                "outer_temperature_k", positive=True)

        lo, hi = schedule.minimum_pressure_pa, schedule.maximum_pressure_pa
        pressure = np.empty((schedule.time_s.size, n), dtype=float)
        mass = np.empty_like(pressure)
        cumulative = np.zeros(schedule.time_s.size, dtype=float)
        cumulative_outer = np.zeros(schedule.time_s.size, dtype=float)
        step_residual = np.empty(schedule.time_s.size - 1, dtype=float)
        pressure[0] = schedule.initial_pressure_pa
        volume = geometry.pore_volume_m3
        centers = geometry.radial_centers_m
        for j in range(n):
            mass[0, j] = volume[j] * self._properties(
                pressure[0, j], geometry.temperature_k[j])[0]

        def interface_flow(state, left_idx, right_idx):
            """Positive mass rate is from the outer cell toward the inner cell."""
            p_inner, p_outer = state[left_idx], state[right_idx]
            donor = right_idx if p_outer >= p_inner else left_idx
            rho, mu = self._properties(state[donor], geometry.temperature_k[donor])
            k_harm = 2.0 * geometry.permeability_m2[left_idx] * geometry.permeability_m2[right_idx] / (
                geometry.permeability_m2[left_idx] + geometry.permeability_m2[right_idx])
            trans = 2.0 * math.pi * geometry.thickness_m * k_harm / math.log(
                centers[right_idx] / centers[left_idx])
            return trans * rho / mu * (p_outer - p_inner)

        def well_flow(state, boundary_pressure, step_index):
            """Positive mass rate is from the inner-face boundary into cell zero."""
            if schedule.well_mass_flow_kg_s is not None:
                return 0.5 * (schedule.well_mass_flow_kg_s[step_index]
                              + schedule.well_mass_flow_kg_s[step_index + 1])
            if boundary_pressure >= state[0]:
                donor_pressure, donor_temperature = boundary_pressure, well_boundary_temperature
            else:
                donor_pressure, donor_temperature = state[0], geometry.temperature_k[0]
            rho, mu = self._properties(donor_pressure, donor_temperature)
            conductance = (2.0 * math.pi * geometry.thickness_m
                           * geometry.permeability_m2[0]
                           / math.log(centers[0] / geometry.radial_faces_m[0]))
            return conductance * rho / mu * (boundary_pressure - state[0])

        for step, dt in enumerate(np.diff(schedule.time_s)):
            left, right = pressure[step], pressure[step].copy()
            if schedule.well_pressure_pa is not None:
                well_boundary_pressure = 0.5 * (
                    schedule.well_pressure_pa[step] + schedule.well_pressure_pa[step + 1])
            else:
                well_boundary_pressure = None
            if outer_pressure is not None:
                p_boundary = 0.5 * (outer_pressure[step] + outer_pressure[step + 1])

            def residual(state):
                new_mass = np.empty(n, dtype=float)
                for cell in range(n):
                    rho, _ = self._properties(state[cell], geometry.temperature_k[cell])
                    new_mass[cell] = volume[cell] * rho
                flows = np.array([interface_flow(state, cell, cell + 1)
                                  for cell in range(n - 1)])
                net = np.zeros(n, dtype=float)
                net[0] += well_flow(state, well_boundary_pressure, step)
                for cell, flow in enumerate(flows):
                    net[cell] += flow
                    net[cell + 1] -= flow
                if outer_pressure is not None:
                    if p_boundary >= state[-1]:
                        donor_pressure, donor_temperature = p_boundary, boundary_temperature
                    else:
                        donor_pressure, donor_temperature = state[-1], geometry.temperature_k[-1]
                    rho, mu = self._properties(donor_pressure, donor_temperature)
                    conductance = 2.0 * math.pi * geometry.thickness_m * geometry.permeability_m2[-1]
                    conductance /= math.log(geometry.radial_faces_m[-1] / centers[-1])
                    # Positive outer flow enters the reservoir.
                    net[-1] += conductance * rho / mu * (p_boundary - state[-1])
                return new_mass - mass[step] - dt * net

            solved = least_squares(residual, right, bounds=(np.full(n, lo), np.full(n, hi)),
                                   max_nfev=max_nfev, xtol=xtol, ftol=ftol, gtol=gtol)
            final_residual = residual(solved.x)
            candidate_mass = np.empty(n, dtype=float)
            for cell in range(n):
                candidate_mass[cell] = volume[cell] * self._properties(
                    solved.x[cell], geometry.temperature_k[cell])[0]
            # A total-system scale can hide a poor local balance in a small cell,
            # and a fixed 1 kg floor is too loose for core-scale geometries.
            cell_scale = np.maximum(mass[step], candidate_mass)
            cell_budget = 1e-8 * cell_scale
            if not solved.success or np.any(np.abs(final_residual) > cell_budget):
                raise RuntimeError(
                    f"porous-reservoir step {step} did not converge: {solved.message}; "
                    f"max cell mass residual={np.max(np.abs(final_residual)):.6g} kg")
            pressure[step + 1] = solved.x
            mass[step + 1] = candidate_mass
            qwell = well_flow(solved.x, well_boundary_pressure, step)
            injected = qwell * dt
            cumulative[step + 1] = cumulative[step] + injected
            outer_inflow = 0.0
            if outer_pressure is not None:
                if p_boundary >= solved.x[-1]:
                    donor_pressure, donor_temperature = p_boundary, boundary_temperature
                else:
                    donor_pressure, donor_temperature = solved.x[-1], geometry.temperature_k[-1]
                rho, mu = self._properties(donor_pressure, donor_temperature)
                conductance = 2.0 * math.pi * geometry.thickness_m * geometry.permeability_m2[-1]
                conductance /= math.log(geometry.radial_faces_m[-1] / centers[-1])
                outer_inflow = conductance * rho / mu * (p_boundary - solved.x[-1])
            boundary_mass = outer_inflow * dt
            cumulative_outer[step + 1] = cumulative_outer[step] + boundary_mass
            step_residual[step] = float(np.sum(mass[step + 1] - mass[step]) - injected - boundary_mass)
        return _issue_result(
            time_s=schedule.time_s, pressure_pa=pressure, cell_gas_mass_kg=mass,
            cumulative_well_mass_kg=cumulative,
            cumulative_outer_boundary_mass_kg=cumulative_outer,
            per_step_mass_residual_kg=step_residual,
            geometry=geometry, schedule=schedule, property_evidence_id=self.property_evidence_id,
            outer_boundary_temperature_k=boundary_temperature,
            well_boundary_temperature_k=well_boundary_temperature)
