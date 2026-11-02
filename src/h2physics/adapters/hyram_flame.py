"""Actual optional HyRAM+ Flame, with independently checked source/field budgets.

The separately installed GPL-3.0-only engine owns nozzle, expansion, combustion,
flame ODE and radiation. This module audits those results, without correcting
native profiles. https://doi.org/10.2172/2563814 describes the native model.
"""

import hashlib
import math
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, ThermoState, finite
from ..release import NozzleOpening, SourceLocation


@dataclass(frozen=True, slots=True)
class SteadyFlameWindow:
    """Caller-evidenced steady premise, not a computed ignition/duration model."""

    clock_id: str
    start_s: float
    end_s: float
    source_evidence_id: str
    steady_evidence_id: str
    origin: Origin

    def __post_init__(self):
        if not all(s.strip() for s in (self.clock_id, self.source_evidence_id,
                                       self.steady_evidence_id)):
            raise ValueError("Clock, source and steady-premise evidence identities are required")
        if finite(self.start_s, "window start") >= finite(self.end_s, "window end"):
            raise ValueError("A steady flame needs increasing finite clock support")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve the source data role explicitly")


@dataclass(frozen=True, slots=True)
class FlameAuditPolicy:
    relative_mass_tolerance: float = 1e-3
    absolute_mass_tolerance_kg_s: float = 1e-9
    relative_source_energy_tolerance: float = 1e-6
    absolute_source_energy_tolerance_w: float = .1
    relative_quadrature_tolerance: float = 1e-7
    relative_caloric_tolerance: float = 1e-3
    absolute_caloric_tolerance_j_kg: float = 1.
    radial_cutoff_widths: float = 8.
    radial_panels: int = 32
    quadrature_order: int = 16

    def __post_init__(self):
        for name in ("relative_mass_tolerance", "absolute_mass_tolerance_kg_s",
                     "relative_source_energy_tolerance", "absolute_source_energy_tolerance_w",
                     "relative_quadrature_tolerance", "relative_caloric_tolerance",
                     "absolute_caloric_tolerance_j_kg", "radial_cutoff_widths"):
            finite(getattr(self, name), name, positive=True)
        if self.radial_cutoff_widths < 5:
            raise ValueError("The independent section audit requires at least five widths")
        if (isinstance(self.quadrature_order, bool) or not isinstance(self.quadrature_order, int)
                or self.quadrature_order < 8):
            raise ValueError("Use an integer section quadrature order of at least eight")
        if isinstance(self.radial_panels, bool) or not isinstance(self.radial_panels, int) or self.radial_panels < 8:
            raise ValueError("Use at least eight independent radial quadrature panels")


def _readonly(values):
    result = np.array(values, dtype=float, copy=True)
    result = immutable_array(result, name="result")
    return result


def _native_flame_signature(native):
    digest = hashlib.sha256()
    for name in ("S", "x", "y", "B", "V_cl", "theta", "f_cl"):
        digest.update(np.asarray(getattr(native, name), dtype=float).tobytes())
    scalars = (native.lamf, native.lamv, native.Lvis, native.Srad, native.Xrad,
               native.mass_flow_rate, native.chem.DHc, native.ambient.T, native.ambient.P)
    digest.update(np.asarray(scalars, dtype=float).tobytes())
    return digest.hexdigest()


def fuel_origin_section_flows(native_flame, *, radial_cutoff_widths=8., quadrature_order=16,
                             radial_panels=32):
    """Integrate actual native rho(f)*f*v over each circular flame section, kg/s.

    f is the conserved fuel-origin mixture fraction, including hydrogen in water;
    it is not residual unburned H2. Density and chemistry are evaluated by the
    actual native object. Gauss quadrature splits at its temperature-table knots.
    This checks the output field rather than re-integrating the flame equations.
    The reported integral ends at an explicit radius cutoff_widths*B.
    """
    finite(radial_cutoff_widths, "radial audit extent", positive=True)
    if isinstance(quadrature_order, bool) or not isinstance(quadrature_order, int) or quadrature_order < 4:
        raise ValueError("Section quadrature order must be an integer of at least four")
    if isinstance(radial_panels, bool) or not isinstance(radial_panels, int) or radial_panels < 8:
        raise ValueError("Section quadrature needs at least eight radial panels")
    nodes, weights = np.polynomial.legendre.leggauss(quadrature_order)
    knots = np.unique(np.asarray(native_flame.chem.T_prod.x))
    values = []
    for width, fraction, velocity in zip(native_flame.B, native_flame.f_cl,
                                         native_flame.V_cl, strict=True):
        if width <= 0 or velocity <= 0 or not 0 < fraction <= 1:
            raise ValueError("Native flame section is outside the positive Gaussian domain")
        inner = knots[(knots > 0) & (knots < fraction)]
        breakpoints = native_flame.lamf*np.sqrt(np.log(fraction/inner))
        bounds = np.unique(np.r_[np.linspace(0., radial_cutoff_widths, radial_panels+1),
                                 breakpoints[breakpoints < radial_cutoff_widths]])
        half = np.diff(bounds)/2
        radius_widths = (bounds[:-1]+half)[:, None]+half[:, None]*nodes
        f = fraction*np.exp(-(radius_widths/native_flame.lamf)**2)
        v = velocity*np.exp(-(radius_widths/native_flame.lamv)**2)
        density = native_flame.chem.rho_prod(f)
        integral = np.sum(half[:, None]*weights*radius_widths*density*f*v)
        values.append(2*math.pi*width**2*integral)
    return _readonly(values)


def native_combustion_caloric_audit(native_flame):
    """Direct-EOS self-consistency check of the native caloric convention.

    Columns: mixture_fraction, native_T_K, released_heat_J_kg, native_MW_factor,
    reactant_h_J_kg, product_h_J_kg, native_equation_residual_J_kg,
    unscaled_mass_specific_reference_residual_J_kg, product_fuel_origin_fraction.
    The final reference residual is diagnostic: no common formation-energy zero
    or new physical combustion caloric convention is inferred from these fluids.
    """
    chemistry = native_flame.chem
    rows = []
    for fraction in (.005, float(chemistry.fstoich), .1, .4, .8):
        reactants, products = chemistry._Yreac(fraction), chemistry._Yprod(fraction)
        temperature = float(chemistry.T_prod(fraction))
        h_reactants = sum(float(y)*chemistry.therm[k].get_property(
            "H", T=chemistry.Treac, P=chemistry.Preac) for k, y in reactants.items())
        h_products = sum(float(y)*chemistry.therm[k].get_property(
            "H", T=temperature, P=chemistry.Preac) for k, y in products.items())
        water_equivalent = float(products["H2O"])*chemistry.MW[chemistry.reac]/chemistry.MW["H2O"]
        released_heat = water_equivalent*chemistry.DHc
        native_factor = float(chemistry._MWmix(reactants)/chemistry._MWmix(products))
        rows.append((fraction, temperature, released_heat, native_factor, h_reactants, h_products,
            h_products-native_factor*h_reactants-released_heat,
            h_products-h_reactants-released_heat, float(products[chemistry.reac])+water_equivalent))
    return _readonly(rows)


@dataclass(frozen=True, slots=True)
class HyRAMRadiationRun:
    """Positive incident scalar irradiance, not absorbed/signed equipment heat."""

    flame: Any
    native_flux: Any
    points_m: np.ndarray
    irradiance_w_m2: np.ndarray
    emitter_points_m: np.ndarray
    relative_humidity: float
    minimum_path_m: float
    minimum_transmissivity: float
    maximum_transmissivity: float
    minimum_flux_bound_w_m2: np.ndarray
    maximum_flux_bound_w_m2: np.ndarray
    gates: Mapping[str, bool]
    accepted: bool
    status: str

    def __post_init__(self):
        for name in ("points_m", "irradiance_w_m2", "emitter_points_m",
                     "minimum_flux_bound_w_m2", "maximum_flux_bound_w_m2"):
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        object.__setattr__(self, "gates", MappingProxyType(dict(self.gates)))

    @property
    def kernel_accepted(self):
        return all(self.gates.values())


class HyRAMFlameAdmissibilityError(ValueError):
    def __init__(self, result):
        self.result, self.native = result, result.native
        failed = ", ".join(name for name, passed in result.gates.items() if not passed)
        super().__init__("Native HyRAM Flame failed: "+failed)


class HyRAMRadiationAdmissibilityError(ValueError):
    def __init__(self, result):
        self.result, self.native = result, result.flame.native
        super().__init__("Native radiation failed its path/power/finite-output audit")


@dataclass(frozen=True, slots=True)
class HyRAMFlameRun:
    native: Any
    native_signature: str
    upstream: ThermoState
    ambient: ThermoState
    opening: NozzleOpening
    location: SourceLocation
    window: SteadyFlameWindow
    solver_options: Mapping[str, Any]
    policy: FlameAuditPolicy
    transmissivity_function: Callable
    mass_flow_kg_s: float
    expanded_mass_flow_kg_s: float
    fuel_origin_flows_kg_s: np.ndarray
    maximum_section_quadrature_difference_kg_s: float
    maximum_source_mass_residual_kg_s: float
    maximum_transport_mass_residual_kg_s: float
    throat_energy_residual_w: float
    expansion_energy_residual_w: float
    native_heat_of_combustion_j_kg: float
    chemical_power_w: float
    emitted_radiative_power_w: float
    radiant_fraction: float
    radiant_power_residual_w: float
    combustion_caloric_audit: np.ndarray
    centreline: np.ndarray
    warning_messages: tuple[str, ...]
    gates: Mapping[str, bool]
    accepted: bool

    def __post_init__(self):
        for name in ("fuel_origin_flows_kg_s", "centreline", "combustion_caloric_audit"):
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        object.__setattr__(self, "solver_options", MappingProxyType(dict(self.solver_options)))
        object.__setattr__(self, "gates", MappingProxyType(dict(self.gates)))

    def irradiance(self, points_m, *, relative_humidity: float,
                   minimum_source_distance_m: float, number_of_sources: int = 50,
                   waist_fraction: float = .75, allow_rejected_flame: bool = False,
                   require_kernel_accepted: bool = True) -> HyRAMRadiationRun:
        """Call actual native multisource radiation with explicit geometry guards.

        Global coordinates are x/y/z with z upward. Native radiation treats each
        emitter as facing each observer separately; this is not a fixed receiver
        normal, an absorbed flux, reflection or a wall heat boundary. A rejected
        flame requires explicit diagnostic opt-in and can never yield an accepted
        source-to-radiation result, even if this radiation kernel's gates pass.
        """
        if type(allow_rejected_flame) is not bool:
            raise TypeError("allow_rejected_flame must be an explicit bool")
        if type(require_kernel_accepted) is not bool:
            raise TypeError("require_kernel_accepted must be an explicit bool")
        if not self.accepted and not allow_rejected_flame:
            raise HyRAMFlameAdmissibilityError(self)
        if _native_flame_signature(self.native) != self.native_signature:
            raise ValueError("Native flame fields changed after the recorded audit")
        if not self.gates["finite positive full-visible native flame"]:
            raise ValueError("Radiation requires the complete visible native flame geometry")
        points = np.asarray(points_m, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.all(np.isfinite(points)):
            raise ValueError("Radiation observers must be a nonempty finite (n,3) global-m array")
        if not 0 < finite(relative_humidity, "relative humidity") <= 1:
            raise ValueError("Native log-transmission requires 0 < relative humidity <= 1")
        finite(minimum_source_distance_m, "emitter exclusion distance", positive=True)
        if (isinstance(number_of_sources, bool) or not isinstance(number_of_sources, int)
                or number_of_sources < 5):
            raise ValueError("Use an integer radiation source count of at least five")
        nleft = int(finite(waist_fraction, "radiation waist fraction")*number_of_sources)
        if not 2 <= nleft <= number_of_sources-2:
            raise ValueError("Native triangular source weights require an interior waist")
        s = np.linspace(self.native.S[0], min(self.native.S[-1], self.native.Lvis), number_of_sources)
        emitters = np.c_[np.interp(s, self.native.S, self.native.x),
                         np.full(len(s), self.location.position_m[1]),
                         np.interp(s, self.native.S, self.native.y)]
        distances = np.linalg.norm(points[:, None, :]-emitters[None, :, :], axis=2)
        minimum_path = float(distances.min())
        if minimum_path < minimum_source_distance_m:
            raise ValueError("Observer enters the explicitly excluded native emitter neighborhood")
        transmission = np.asarray(self.transmissivity_function(distances, self.ambient.temperature_k,
                                                               relative_humidity), dtype=float)
        if (transmission.shape != distances.shape or not np.all(np.isfinite(transmission))
                or np.any(transmission < 0) or np.any(transmission > 1)):
            raise ValueError("Native atmospheric transmission is outside [0,1]; it is not clipped")
        raw = self.native.Qrad_multi(points[:, 0], points[:, 2],
            points[:, 1]-self.location.position_m[1], relative_humidity,
            WaistLoc=waist_fraction, N=number_of_sources)
        flux = np.asarray(raw, dtype=float).reshape(-1)
        # Positive normalized emitter weights imply these independent convex
        # bounds, without reproducing the native source-weight/radiation solver.
        kernels = self.emitted_radiative_power_w/(4*math.pi)*transmission/distances**2
        lower, upper = kernels.min(axis=1), kernels.max(axis=1)
        gates = {"finite nonnegative scalar irradiance": bool(flux.shape == (len(points),)
                    and np.all(np.isfinite(flux)) and np.all(flux >= 0)),
                 "positive normalized-emitter power bounds": bool(np.all(flux >= lower*(1-1e-12))
                    and np.all(flux <= upper*(1+1e-12)))}
        result = HyRAMRadiationRun(self, raw, points, flux, emitters, relative_humidity,
            minimum_path, float(transmission.min()), float(transmission.max()), lower, upper,
            gates, self.accepted and all(gates.values()),
            "accepted-steady-flame" if self.accepted else "diagnostic-unaccepted-flame")
        if require_kernel_accepted and not all(gates.values()):
            raise HyRAMRadiationAdmissibilityError(result)
        return result


def run_hyram_flame(*, fluid_factory: Callable, orifice_factory: Callable,
                    flame_factory: Callable, transmissivity_function: Callable,
                    upstream: ThermoState, ambient: ThermoState, opening: NozzleOpening,
                    location: SourceLocation, window: SteadyFlameWindow,
                    solver_options: Mapping[str, Any], policy: FlameAuditPolicy = FlameAuditPolicy(),
                    require_accepted: bool = True) -> HyRAMFlameRun:
    """Execute native Flame from a reservoir, then audit its complete visible field.

    Supply actual HyRAM+ 6.1 factories/functions. No optional engine is imported
    at module import. The native pipeline owns the only choking/expansion solve;
    no shared-nozzle exit, prescribed mdot, developed-flow surrogate or chemistry
    object can replace it through solver_options. Calm normal gaseous H2/air is
    the checked level. Native warnings and inadmissible fields remain visible.
    """
    if type(require_accepted) is not bool:
        raise TypeError("require_accepted must be an explicit bool")
    if not isinstance(window, SteadyFlameWindow):
        raise ValueError("Supply an explicit validated steady flame clock/premise")
    if not isinstance(policy, FlameAuditPolicy):
        raise ValueError("Supply an explicit flame audit policy")
    if not all(callable(factory) for factory in (fluid_factory, orifice_factory, flame_factory,
                                                 transmissivity_function)):
        raise ValueError("Actual native factories and transmissivity callable are required")
    if (upstream.basis.fluid != "Hydrogen" or upstream.basis.spin_composition != "normal"
            or ambient.basis.fluid != "Air"):
        raise ValueError("This native flame level requires normal Hydrogen and Air bases")
    for state in (upstream, ambient):
        if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Native high-pressure flame inputs must be single gas states")
    if upstream.pressure_pa <= 2*ambient.pressure_pa:
        raise ValueError("This declared high-pressure route requires P0 > 2 Pambient")
    if abs(location.direction_unit[1]) > 1e-12:
        raise ValueError("The native 2D flame direction must lie in the global x/z plane")
    options = dict(solver_options)
    allowed = {"Smax", "dS", "tol", "numB", "n_pts_integral", "verbose", "lamf", "lamv",
               "betaA", "alpha_buoy", "T_establish_min", "nn_conserve_momentum", "nn_T"}
    if options.keys()-allowed:
        raise ValueError("Source, chemistry and calm-flame ownership cannot be overridden")
    finite(options.get("Smax", math.nan), "finite requested flame extent", positive=True)
    for key in ("dS", "tol", "numB", "lamf", "lamv", "betaA", "alpha_buoy"):
        if key in options and options[key] is not None:
            finite(options[key], key, positive=True)
    if "n_pts_integral" in options and (isinstance(options["n_pts_integral"], bool)
            or not isinstance(options["n_pts_integral"], int) or options["n_pts_integral"] < 20):
        raise ValueError("Use at least twenty native radial integration points")
    fuel = fluid_factory("H2", T=upstream.temperature_k, P=upstream.pressure_pa)
    air = fluid_factory("AIR", T=ambient.temperature_k, P=ambient.pressure_pa)
    for native, declared in ((fuel, upstream), (air, ambient)):
        if not math.isclose(native.rho, declared.density_kg_m3, rel_tol=1e-7, abs_tol=1e-10):
            raise ValueError("Native and declared density bases differ")
        h = native.therm.get_property("H", T=declared.temperature_k, P=declared.pressure_pa)
        if not math.isclose(h, declared.enthalpy_j_kg, rel_tol=1e-7, abs_tol=1e-4):
            raise ValueError("Native and declared enthalpy references differ")
    orifice = orifice_factory(math.sqrt(4*opening.nominal_area_m2/math.pi),
                              Cd=opening.effective_area_factor)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        native = flame_factory(fuel, orifice, air,
            theta0=math.atan2(location.direction_unit[2], location.direction_unit[0]),
            x0=location.position_m[0], y0=location.position_m[2], **options)
    warning_messages = tuple(str(item.message) for item in caught)
    flow = finite(native.mass_flow_rate, "native mass flow", positive=True)
    df = native.developing_flow
    expanded = df.fluid_exp
    expanded_flow = expanded.rho*expanded.v*math.pi*df.orifice_exp.d**2/4*df.orifice_exp.Cd
    throat = df.orifice_flow.fluid
    h_throat = throat.therm.get_property("H", T=throat.T, D=throat.rho)
    h_expanded = expanded.therm.get_property("H", T=expanded.T, D=expanded.rho)
    throat_energy = flow*(h_throat+throat.v**2/2-upstream.enthalpy_j_kg)
    expanded_energy = flow*(h_expanded+expanded.v**2/2-upstream.enthalpy_j_kg)
    sections = fuel_origin_section_flows(native, radial_cutoff_widths=policy.radial_cutoff_widths,
        quadrature_order=policy.quadrature_order, radial_panels=policy.radial_panels)
    coarse = fuel_origin_section_flows(native, radial_cutoff_widths=policy.radial_cutoff_widths,
        quadrature_order=policy.quadrature_order//2, radial_panels=policy.radial_panels)
    quadrature_error = float(np.max(abs(sections-coarse)))
    source_error = max(float(np.max(abs(sections-flow))), abs(expanded_flow-flow))
    transport_error = float(np.max(abs(sections-sections[0])))
    heat = finite(native.chem.DHc, "native heat of combustion", positive=True)
    chemical_power = flow*heat
    radiative_power = finite(native.Srad, "native emitted radiation power", positive=True)
    radiant_fraction = finite(native.Xrad, "native radiant fraction", positive=True)
    radiation_residual = radiative_power-radiant_fraction*chemical_power
    caloric = native_combustion_caloric_audit(native)
    centreline = np.c_[native.S, native.x, np.full(len(native.S), location.position_m[1]),
        native.y, native.V_cl, native.B, native.theta, native.f_cl, native.chem.T_prod(native.f_cl)]
    mass_budget = policy.absolute_mass_tolerance_kg_s+policy.relative_mass_tolerance*flow
    energy_budget = (policy.absolute_source_energy_tolerance_w
                     + policy.relative_source_energy_tolerance*abs(flow*upstream.enthalpy_j_kg))
    gates = {
        "finite positive full-visible native flame": bool(len(centreline) >= 2
            and np.all(np.isfinite(centreline)) and np.all(np.diff(native.S) > 0)
            and np.all(centreline[:, 4:6] > 0) and np.all(centreline[:, 8] > 0)
            and np.all((native.f_cl > 0) & (native.f_cl <= 1))
            and math.isclose(native.S[-1], native.Lvis, rel_tol=1e-8, abs_tol=1e-10)),
        "native source expansion mass": bool(abs(expanded_flow-flow) <= mass_budget),
        "native throat and expansion stagnation energy": bool(max(abs(throat_energy),
                                                                  abs(expanded_energy)) <= energy_budget),
        "independent section quadrature": bool(quadrature_error <= policy.relative_quadrature_tolerance*flow),
        "direct EOS check of native combustion caloric equation": bool(np.all(abs(caloric[:, 6])
            <= policy.absolute_caloric_tolerance_j_kg+policy.relative_caloric_tolerance*abs(caloric[:, 2]))),
        "source to conserved fuel-origin field mass": bool(source_error <= mass_budget),
        "conserved fuel-origin transport along flame": bool(transport_error <= mass_budget),
        "emitted radiation within native chemical-power budget": bool(0 < radiant_fraction <= 1
            and 0 < radiative_power <= chemical_power and abs(radiation_residual) <= 1e-10*chemical_power),
        "no native warning hidden": not warning_messages,
    }
    result = HyRAMFlameRun(native, _native_flame_signature(native), upstream, ambient, opening, location,
        window, options, policy,
        transmissivity_function, flow, expanded_flow, sections, quadrature_error, source_error,
        transport_error, throat_energy, expanded_energy, heat, chemical_power, radiative_power,
        radiant_fraction, radiation_residual, caloric, centreline, warning_messages, gates, all(gates.values()))
    if require_accepted and not result.accepted:
        raise HyRAMFlameAdmissibilityError(result)
    return result
