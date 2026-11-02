"""Checked gas-plane and steady calm-jet boundaries for optional native DEGALI.

The native package owns expansion, mixture profiles, entrainment and integration.
This module imports no native solver. Factories and actual objects are supplied
by the caller; the explicit body-force policy below changes one native source.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, PropertyProvider, ThermoState, finite
from ..observations import ObservationTable, Variable
from ..release import NozzleResult, SourceLocation

SHARED_AREA = "shared_effective_stream_and_pressure_area"
PROFILE_FORCE = "native_profile_integrated_buoyancy_v1"


def _gas(state: ThermoState):
    if state.vapor_mass_fraction is not None:
        accepted = state.vapor_mass_fraction == 1.
    else:
        accepted = state.phase in {"gas", "supercritical_gas", "supercritical"}
    if not accepted:
        raise ValueError("This gas-plane boundary does not resolve liquid, droplets or rainout")


def _close(actual, expected, label, *, relative=1e-8, absolute=0.):
    finite(actual, label)
    if not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute):
        raise ValueError(f"{label} differs: {actual!r} versus {expected!r}")


@dataclass(frozen=True, slots=True)
class ExpandedGasPlane:
    native: Any
    nozzle: NozzleResult
    state: ThermoState
    location: SourceLocation
    location_basis_id: str
    pressure_area_policy: str
    origin: Origin = field(default=Origin.PREDICTED, init=False)

    @property
    def mass_flow_kg_s(self):
        return self.nozzle.mass_flow_kg_s

    @property
    def velocity_m_s(self):
        return self.native.velocity

    @property
    def diameter_m(self):
        return self.native.diameter


def expand_nozzle_gas(
    nozzle: NozzleResult, properties: PropertyProvider, *, expander: Callable,
    location: SourceLocation, location_basis_id: str, pressure_area_policy: str,
) -> ExpandedGasPlane:
    """Delegate the supplied throat to an actual native ambient-plane expander.

    The selected area closure treats the shared kernel's effective area as both
    stream area and pressure-force area. It does not identify a physical vena
    contracta or predict the axial position of the receiving virtual plane.
    """
    if pressure_area_policy != SHARED_AREA or not location_basis_id.strip():
        raise ValueError("Declare the shared effective pressure area and virtual-plane position basis")
    if nozzle.exit_state is None:
        raise ValueError("A closed nozzle has no forward gas plane")
    properties.basis.require_compatible(nozzle.upstream_stagnation.basis)
    properties.basis.require_compatible(nozzle.exit_state.basis)
    if properties.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}:
        raise ValueError("The reviewed native boundary accepts explicit pure hydrogen spin species")
    _gas(nozzle.exit_state)
    finite(nozzle.mass_flow_kg_s, "forward mass flow", positive=True)
    finite(nozzle.velocity_m_s, "throat velocity", positive=True)
    finite(nozzle.effective_area_m2, "effective area", positive=True)
    throat = nozzle.exit_state
    if throat.pressure_pa < nozzle.back_pressure_pa*(1-1e-10):
        raise ValueError("This boundary cannot repair a throat below ambient pressure")
    _close(throat.density_kg_m3*nozzle.velocity_m_s*nozzle.effective_area_m2,
           nozzle.mass_flow_kg_s, "throat continuity")
    _close(throat.enthalpy_j_kg+.5*nozzle.velocity_m_s**2,
           nozzle.upstream_stagnation.enthalpy_j_kg, "throat total specific energy", absolute=1e-6)
    native = expander(
        fluid=properties.basis.fluid, mass_flow=nozzle.mass_flow_kg_s,
        throat_diameter=math.sqrt(4*nozzle.effective_area_m2/math.pi),
        throat_pressure=throat.pressure_pa, throat_temperature=throat.temperature_k,
        throat_density=throat.density_kg_m3, throat_velocity=nozzle.velocity_m_s,
        throat_enthalpy=throat.enthalpy_j_kg, ambient_pressure=nozzle.back_pressure_pa,
    )
    for name in ("velocity", "density", "temperature", "diameter"):
        finite(getattr(native, name), f"native expanded {name}", positive=True)
    state = properties.state_ph(nozzle.back_pressure_pa, native.enthalpy)
    properties.basis.require_compatible(state.basis)
    _gas(state)
    for name, value in (("pressure", state.pressure_pa), ("enthalpy", state.enthalpy_j_kg),
                        ("density", state.density_kg_m3), ("temperature", state.temperature_k)):
        supplied = nozzle.back_pressure_pa if name == "pressure" else getattr(native, name)
        _close(supplied, value, f"receiving PH {name}")
    mass = state.density_kg_m3*native.velocity*math.pi*native.diameter**2/4
    _close(native.mass_flow, nozzle.mass_flow_kg_s, "native declared mass")
    _close(mass, nozzle.mass_flow_kg_s, "expanded continuity")
    _close(nozzle.mass_flow_kg_s*native.velocity, nozzle.effective_area_thrust_n,
           "expanded advective momentum")
    _close(native.momentum_flux, nozzle.effective_area_thrust_n, "native declared momentum")
    _close(state.enthalpy_j_kg+.5*native.velocity**2,
           nozzle.upstream_stagnation.enthalpy_j_kg, "expanded total specific energy", absolute=1e-6)
    _close(native.total_specific_energy, nozzle.upstream_stagnation.enthalpy_j_kg,
           "native declared total specific energy", absolute=1e-6)
    return ExpandedGasPlane(native, nozzle, state, location, location_basis_id, pressure_area_policy)


@dataclass(frozen=True, slots=True)
class JetPlane:
    """An orthonormal vertical section in a declared global Cartesian frame.

    Horizontal and vertical vectors define the native coordinates. The default
    ground is at vertical coordinate zero. None explicitly selects an unbounded
    free-field comparison, without inventing a physical source height.
    """

    coordinate_frame_id: str
    origin_m: tuple[float, float, float]
    horizontal_unit: tuple[float, float, float]
    vertical_unit: tuple[float, float, float]
    ground_vertical_coordinate_m: float | None = 0.

    def __post_init__(self):
        if not self.coordinate_frame_id.strip():
            raise ValueError("A jet section needs its coordinate frame")
        if self.ground_vertical_coordinate_m is not None:
            finite(self.ground_vertical_coordinate_m, "declared ground vertical coordinate")
        for name in ("origin_m", "horizontal_unit", "vertical_unit"):
            values = tuple(finite(v, name) for v in getattr(self, name))
            if len(values) != 3:
                raise ValueError("Jet-plane vectors need three components")
            object.__setattr__(self, name, values)
        for direction in (self.horizontal_unit, self.vertical_unit):
            _close(float(np.linalg.norm(direction)), 1., "jet-plane unit vector", absolute=1e-12)
        _close(float(np.dot(self.horizontal_unit, self.vertical_unit)), 0.,
               "orthogonal section axes", absolute=1e-12)

    def project(self, location: SourceLocation):
        if location.coordinate_frame_id != self.coordinate_frame_id:
            raise ValueError("Jet/source coordinate frames differ")
        offset = np.array(location.position_m)-self.origin_m
        direction = np.array(location.direction_unit)
        normal = np.cross(self.horizontal_unit, self.vertical_unit)
        if abs(offset@normal) > 1e-9 or abs(direction@normal) > 1e-10:
            raise ValueError("The source is outside the declared axisymmetric vertical section")
        return (float(offset@self.horizontal_unit), float(offset@self.vertical_unit),
                math.atan2(direction@self.vertical_unit, direction@self.horizontal_unit))


@dataclass(frozen=True, slots=True)
class NativeJetBoundary:
    native: Any
    gas_plane: ExpandedGasPlane
    section: JetPlane
    ambient_reference_state: ThermoState


def axisymmetric_boundary(
    plane: ExpandedGasPlane, properties: PropertyProvider, *, section: JetPlane,
    ambient_temperature_k: float, source_factory: Callable, enthalpy_factory: Callable,
) -> NativeJetBoundary:
    """Transfer static HEOS enthalpy through the native component-reference ledger."""
    properties.basis.require_compatible(plane.state.basis)
    reference = properties.state_pt(plane.state.pressure_pa, ambient_temperature_k)
    properties.basis.require_compatible(reference.basis)
    _gas(reference)
    x, z, theta = section.project(plane.location)
    enthalpy = enthalpy_factory(
        specific_enthalpy=plane.state.enthalpy_j_kg-reference.enthalpy_j_kg,
        ambient_temperature=reference.temperature_k, hydrogen_species=properties.basis.fluid,
        hydrogen_reference_enthalpy=reference.enthalpy_j_kg,
    )
    native = source_factory(
        diameter=plane.diameter_m, velocity=plane.velocity_m_s,
        density=plane.state.density_kg_m3, temperature=plane.state.temperature_k,
        mass_fraction=1., theta=theta, x=x, y=z, enthalpy_boundary=enthalpy,
    )
    _close(native.mass_flow, plane.mass_flow_kg_s, "native plug mass flow")
    return NativeJetBoundary(native, plane, section, reference)


def profile_integrated_buoyancy_type(native_type: type) -> type:
    """Return an explicit native subclass using its actual radial buoyancy integral.

    This bridge depends on the checked revision's protected five-flux Jacobian.
    It retains native integration, profiles, entrainment and all other sources.
    Calm surroundings are required because a coflow adds its own momentum term.
    No global patch, automatic profile fallback or coefficient fit is performed.
    """
    for method in ("derivatives", "_flux_jacobian", "buoyancy_force"):
        if not callable(getattr(native_type, method, None)):
            raise TypeError(f"Native profile-force contract lacks {method}")

    class ProfileIntegratedJet(native_type):
        h2physics_body_force_policy = PROFILE_FORCE

        def derivatives(self, distance, state):
            if self.ambient_coflow_velocity != 0.:
                raise ValueError("The profile-force bridge is qualified only for calm surroundings")
            original = np.asarray(super().derivatives(distance, state), dtype=float)
            jacobian = np.asarray(self._flux_jacobian(state), dtype=float)
            if (original.shape != (7,) or jacobian.shape != (5, 5)
                    or not np.all(np.isfinite(original)) or not np.all(np.isfinite(jacobian))):
                raise ValueError("Native derivative/Jacobian capability differs from the checked contract")
            sources = jacobian@original[:5]
            sources[2] = finite(self.buoyancy_force(state), "profile buoyancy")
            return np.r_[np.linalg.solve(jacobian, sources), original[5:]]

    return ProfileIntegratedJet


def hydrogen_energy_gauge_type(native_type: type, *, shift_j_kg_h2: float) -> type:
    """Express native flux energy as E + C*H2_mass_flux for numerical conditioning.

    The H2 mass balance makes this an exact constant reference transformation.
    Native source energy receives the same shift per kg of source H2. Native
    thermodynamic tables, profiles, source state and the root solver are retained.
    The host audit converts energy back before applying its unchanged budgets.
    """
    shift = finite(shift_j_kg_h2, "explicit H2 flux-energy reference shift")
    for method in ("_fluxes", "source_specific_enthalpy"):
        if not callable(getattr(native_type, method, None)):
            raise TypeError(f"Native flux-energy gauge contract lacks {method}")
    if getattr(native_type, "h2physics_hydrogen_energy_gauge_shift_j_kg", 0.) != 0.:
        raise ValueError("Compose one explicit flux-energy gauge, rather than stacking shifts")

    class HydrogenEnergyGauge(native_type):
        h2physics_hydrogen_energy_gauge_shift_j_kg = shift

        def source_specific_enthalpy(self):
            return super().source_specific_enthalpy()+shift*self.source.mass_fraction

        def _fluxes(self, state):
            original = np.array(super()._fluxes(state), dtype=float, copy=True)
            if original.shape != (5,) or not np.all(np.isfinite(original)):
                raise ValueError("Native five-flux order differs from the reviewed energy-gauge contract")
            original[4] += shift*original[3]
            return original

    return HydrogenEnergyGauge


@dataclass(frozen=True, slots=True)
class JetTolerances:
    relative_species: float = 1e-6
    relative_horizontal_momentum: float = 1e-6
    relative_energy: float = 1e-5
    relative_establishment: float = 1e-7
    reference_enthalpy_j_kg: float = 1.

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class JetAudit:
    maximum_relative_species_error: float
    maximum_relative_horizontal_momentum_error: float
    source_total_energy_flux_w: float
    maximum_energy_error_w: float
    energy_scale_w: float
    reference_enthalpy_error_j_kg: float
    initial_entrained_air_kg_s: float
    minimum_ground_clearance_m: float | None
    failures: tuple[str, ...]
    native_energy_gauge_shift_j_kg_h2: float = 0.

    @property
    def passed(self):
        return not self.failures


@dataclass(frozen=True, slots=True)
class NativeJetRun:
    model: Any
    native: Any
    boundary: NativeJetBoundary
    audit: JetAudit
    validation_qualified: bool = False

    @property
    def physical_energy_flux_w(self):
        energy = (np.asarray(self.native.energy_flux)
                  -self.audit.native_energy_gauge_shift_j_kg_h2*np.asarray(self.native.species_flux))
        result = np.array(energy, dtype=float, copy=True)
        result = immutable_array(result, name="result")
        return result

    def radial_observations(self, distances_m, radii_m, *, evidence_id: str):
        """Sample the native profile as whole-mixture mass fraction, density and T.

        This is not a gas-phase mole-fraction or probe-volume observation operator.
        The native solver's state interpolation is retained and not conservative.
        """
        if not evidence_id.strip():
            raise ValueError("Predicted section observations need an evidence identity")
        radii_m = tuple(radii_m)
        rows = []
        for distance in distances_m:
            finite(distance, "streamline distance")
            state = self.native.state_at_s(distance)
            for radius in radii_m:
                if finite(radius, "radial distance") < 0.:
                    raise ValueError("Radial distances must be nonnegative")
                if radius > self.model.radial_limit*state[1]:
                    raise ValueError("Observation lies outside the evaluated radial envelope")
                fraction, density, temperature = self.model.radial_state(state, radius)
                if (not 0. <= finite(fraction, "whole-mixture fraction") <= 1.
                        or finite(density, "profile density", positive=True) <= 0.
                        or finite(temperature, "profile temperature", positive=True) <= 0.):
                    raise ValueError("Native radial observation is outside the physical domain")
                rows.append((distance, radius, fraction, density, temperature))
        if not rows:
            raise ValueError("Select at least one section and radius")
        variables = (Variable("streamline_distance", "length", "m"),
                     Variable("radius", "length", "m"),
                     Variable("hydrogen_whole_mixture_mass_fraction", "mass_fraction", "1",
                              "H2 mass / complete gas-plus-condensate mixture mass"),
                     Variable("bulk_density", "density", "kg/m3"),
                     Variable("temperature", "temperature", "K"))
        return ObservationTable(np.array(rows), variables, np.ones((len(rows), 5), dtype=bool),
            tuple(f"section-{index}" for index in range(len(rows))), (evidence_id,)*len(rows),
            (Origin.PREDICTED,)*5, evidence_id,
            (("coordinate_frame", self.boundary.section.coordinate_frame_id),
             ("representation", "native interpolated steady axisymmetric profile")))


class JetCouplingError(RuntimeError):
    def __init__(self, message, *, model, boundary, run=None, native=None):
        super().__init__(message)
        self.model, self.boundary, self.run = model, boundary, run
        self.native = run.native if run is not None else native


def run_axisymmetric_jet(
    model, boundary: NativeJetBoundary, *, ideal_reference_enthalpy_j_kg: float,
    solver_options: dict, tolerances: JetTolerances = JetTolerances(),
    require_closed: bool = True,
) -> NativeJetRun:
    """Run and audit the actual native steady model; retain failed raw results.

    Energy uses the native ambient-component gauge and includes resolved KE.
    Its scale is mdot*(abs(h_source_model)+KE), avoiding cancellation in net E.
    The selected calm model has no explicit gravitational potential-energy flux.
    """
    if model.source is not boundary.native:
        raise ValueError("The native model must retain the exact declared source object")
    reference = boundary.ambient_reference_state
    plane = boundary.gas_plane
    _close(model.ambient_pressure, plane.state.pressure_pa, "native ambient pressure")
    _close(model.ambient_temperature, reference.temperature_k, "native ambient temperature")
    if (model.hydrogen_enthalpy_species != plane.state.basis.fluid
            or model.ambient_coflow_velocity != 0. or model.energy_transport != "total"
            or model.establishment != "entrained_mass"
            or not model.equilibrium_air_condensation
            or not model.temperature_dependent_phase_enthalpy
            or not model.consistent_phase_ambient
            or model.hydrogen_nonideal_volume_correction):
        raise ValueError("Declare the reviewed calm, four-flux, consistent phase-enthalpy model")
    if (model.thermodynamic_profile == "temperature_mass_fraction"
            and getattr(model, "h2physics_body_force_policy", None) != PROFILE_FORCE):
        raise ValueError("An independent thermal profile requires its explicit integrated-force policy")
    ideal_reference = finite(ideal_reference_enthalpy_j_kg, "ideal reference enthalpy")
    energy_shift = finite(getattr(model, "h2physics_hydrogen_energy_gauge_shift_j_kg", 0.),
                          "native H2 energy gauge")
    source_h = finite(model.source_specific_enthalpy(), "model source enthalpy")-energy_shift
    reference_error = source_h-(plane.state.enthalpy_j_kg-ideal_reference)
    if abs(reference_error) > tolerances.reference_enthalpy_j_kg:
        raise ValueError("The native source enthalpy gauge differs from the independent reference")
    try:
        result = model.solve(**solver_options)
    except (RuntimeError, ValueError, np.linalg.LinAlgError) as error:
        raise JetCouplingError(str(error), model=model, boundary=boundary) from error
    names = ("S", "velocity", "width", "density", "mass_fraction", "theta", "x", "y",
             "temperature", "mass_flux", "species_flux", "momentum_flux", "energy_flux",
             "radiative_heat_added")
    try:
        arrays = {name: np.asarray(getattr(result, name), dtype=float) for name in names}
    except (AttributeError, TypeError, ValueError) as error:
        raise JetCouplingError("Invalid native solution fields", model=model,
                               boundary=boundary, native=result) from error
    if (arrays["S"].ndim != 1 or len(arrays["S"]) < 2
            or any(v.shape != arrays["S"].shape or not np.all(np.isfinite(v))
                   for v in arrays.values()) or np.any(np.diff(arrays["S"]) <= 0.)):
        raise JetCouplingError("Invalid native solution arrays", model=model,
                               boundary=boundary, native=result)
    failures = []
    if (any(np.any(arrays[name] <= 0.) for name in
            ("velocity", "width", "density", "temperature", "mass_flux", "momentum_flux"))
            or np.any((arrays["mass_fraction"] < 0.) | (arrays["mass_fraction"] > 1.))):
        failures.append("nonphysical profile state")
    mass = plane.mass_flow_kg_s
    species_error = float(np.max(abs(arrays["species_flux"]-mass))/mass)
    horizontal = arrays["momentum_flux"]*np.cos(arrays["theta"])
    expected_horizontal = mass*plane.velocity_m_s*math.cos(boundary.native.theta)
    momentum_error = float(np.max(abs(horizontal-expected_horizontal))/(mass*plane.velocity_m_s))
    target_energy = mass*(source_h+.5*plane.velocity_m_s**2)
    scale = mass*(abs(source_h)+.5*plane.velocity_m_s**2)
    physical_energy = arrays["energy_flux"]-energy_shift*arrays["species_flux"]
    energy_error = float(np.max(abs(physical_energy-target_energy-arrays["radiative_heat_added"])))
    ground = boundary.section.ground_vertical_coordinate_m
    clearance = None
    if ground is not None:
        clearance = float(np.min(arrays["y"]-ground
            -model.radial_limit*arrays["width"]*abs(np.cos(arrays["theta"]))))
    initial_air = float(arrays["mass_flux"][0]-mass)
    residuals = getattr(model, "establishment_residuals", {})
    if (not isinstance(residuals, dict)
            or set(residuals) != {"mass", "species", "momentum", "energy"}
            or any(not math.isfinite(v) or abs(v) > tolerances.relative_establishment
                   for v in residuals.values())):
        failures.append("four-flux establishment")
    if abs(physical_energy[0]-target_energy) > scale*tolerances.relative_establishment:
        failures.append("physical-reference establishment energy")
    for failed, label in (
        (species_error > tolerances.relative_species, "hydrogen species conservation"),
        (momentum_error > tolerances.relative_horizontal_momentum, "horizontal momentum conservation"),
        (energy_error > scale*tolerances.relative_energy, "total enthalpy plus kinetic energy conservation"),
        (initial_air < -mass*tolerances.relative_establishment, "negative initial ambient entrainment"),
        (np.any(np.diff(arrays["mass_flux"]) < -mass*tolerances.relative_species), "decreasing entrained mass flux"),
        (clearance is not None and clearance < 0., "evaluated profile intersects the ground"),
    ):
        if failed:
            failures.append(label)
    audit = JetAudit(species_error, momentum_error, target_energy, energy_error, scale, reference_error,
                     initial_air, clearance, tuple(failures), energy_shift)
    run = NativeJetRun(model, result, boundary, audit)
    if require_closed and failures:
        raise JetCouplingError("; ".join(failures), model=model, boundary=boundary, run=run)
    return run
