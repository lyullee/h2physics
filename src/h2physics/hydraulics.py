"""Shared Darcy closures with explicit fluid-property and friction ownership.

The frozen-density level uses supplied upstream properties. The isothermal
compressible level integrates native CoolProp density along pressure, or an
explicitly selected ideal analytical reference. Viscosity is held constant;
neither level adds transient momentum, phase slip or a thermal-state solver.
"""

from collections.abc import Callable
from dataclasses import dataclass
from math import exp, isclose, log, log1p, pi, sqrt

from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq

from .core import finite


@dataclass(frozen=True, slots=True)
class DarcyGeometry:
    length_m: float
    diameter_m: float
    roughness_m: float
    local_loss_coefficient: float = 0.

    def __post_init__(self):
        finite(self.length_m, "length_m", positive=True)
        finite(self.diameter_m, "diameter_m", positive=True)
        for name in ("roughness_m", "local_loss_coefficient"):
            if finite(getattr(self, name), name) < 0.:
                raise ValueError(f"{name} must be nonnegative")
        if self.roughness_m >= self.diameter_m:
            raise ValueError("Roughness must be smaller than the flow diameter")


@dataclass(frozen=True, slots=True)
class DarcyFlowResult:
    mass_flow_kg_s: float
    velocity_m_s: float
    reynolds_number: float
    darcy_friction_factor: float
    driving_pressure_pa: float
    modeled_pressure_drop_pa: float
    momentum_residual_pa: float
    root_converged: bool
    iterations: int


class HydraulicConvergenceError(RuntimeError):
    def __init__(self, result: DarcyFlowResult):
        self.result = result
        super().__init__(f"Darcy constitutive residual {result.momentum_residual_pa:g} Pa "
                         "does not meet the declared pressure gate")


@dataclass(frozen=True, slots=True)
class IsothermalCompressibleGasResult:
    """Steady isothermal flow; viscosity is explicitly held constant.

    Native pressure diagnostics are reconstructed by a differential momentum
    integration, separately from the integral used to determine the flow.
    """

    mass_flow_kg_s: float
    inlet_velocity_m_s: float
    outlet_velocity_m_s: float
    reynolds_number: float
    darcy_friction_factor: float
    upstream_pressure_pa: float
    downstream_pressure_pa: float
    temperature_k: float
    specific_gas_constant_j_kg_k: float | None
    modeled_downstream_pressure_pa: float
    pressure_residual_pa: float
    friction_law_id: str
    eos_identity: str | None = None
    viscosity_model: str = "held-constant"
    density_integral_pa_kg_m3: float | None = None
    density_integral_error_pa_kg_m3: float | None = None
    momentum_integral_residual_pa_kg_m3: float | None = None
    maximum_isothermal_mach_number: float | None = None
    native_path_gate: str | None = None


class CompressibleGasConvergenceError(RuntimeError):
    def __init__(self, result: IsothermalCompressibleGasResult):
        self.result = result
        super().__init__(
            f"Compressible-gas pressure residual {result.pressure_residual_pa:g} Pa "
            "does not meet the declared pressure gate"
        )


def solve_darcy_flow(geometry: DarcyGeometry, *, density_kg_m3: float, viscosity_pa_s: float,
                     driving_pressure_pa: float, friction_law: Callable[[float, float], float],
                     pressure_absolute_tolerance_pa: float = 1e-7,
                     pressure_relative_tolerance: float = 1e-10) -> DarcyFlowResult:
    """Solve positive flow magnitude; the caller owns direction and hydrostatics.

    A scalar root flag alone is insufficient for a discontinuous friction law.
    The returned flow must also close its independently reconstructed loss.
    """
    rho = finite(density_kg_m3, "density_kg_m3", positive=True)
    mu = finite(viscosity_pa_s, "viscosity_pa_s", positive=True)
    drive = finite(driving_pressure_pa, "driving_pressure_pa", positive=True)
    absolute = finite(pressure_absolute_tolerance_pa, "pressure_absolute_tolerance_pa", positive=True)
    relative = finite(pressure_relative_tolerance, "pressure_relative_tolerance", positive=True)
    ratio = geometry.length_m/geometry.diameter_m
    scale = finite(sqrt(2.*drive/(rho*(.02*ratio+geometry.local_loss_coefficient))),
                   "velocity_scale", positive=True)

    def loss(x):
        velocity = x*scale
        reynolds = rho*velocity*geometry.diameter_m/mu
        friction = finite(friction_law(reynolds, geometry.roughness_m/geometry.diameter_m),
                          "darcy_friction_factor", positive=True)
        return (friction*ratio+geometry.local_loss_coefficient)*rho*velocity**2/2., reynolds, friction

    def residual(x):
        return -1. if x == 0. else loss(x)[0]/drive-1.

    upper = 1.
    for _ in range(64):
        if residual(upper) >= 0.:
            break
        upper *= 2.
    else:
        raise RuntimeError("Could not bracket a finite Darcy flow within the expansion limit")
    if residual(upper) == 0.:
        root, converged, iterations = upper, True, 0
    else:
        root, diagnostic = brentq(residual, 0., upper, xtol=1e-13, rtol=1e-14,
                                  full_output=True, disp=False, maxiter=150)
        converged, iterations = diagnostic.converged, diagnostic.iterations
    modeled, reynolds, friction = loss(root)
    velocity = root*scale
    result = DarcyFlowResult(rho*pi*geometry.diameter_m**2/4.*velocity, velocity,
        reynolds, friction, drive, modeled, drive-modeled, converged, iterations)
    if not converged or abs(result.momentum_residual_pa) > max(absolute, relative*drive):
        raise HydraulicConvergenceError(result)
    return result


def solve_isothermal_compressible_gas_flow(
    geometry: DarcyGeometry, *, upstream_pressure_pa: float,
    downstream_pressure_pa: float, temperature_k: float,
    molecular_mass_kg_mol: float | None = None, viscosity_pa_s: float,
    friction_law: Callable[[float, float], float], friction_law_id: str,
    pressure_absolute_tolerance_pa: float = 1e-5,
    pressure_relative_tolerance: float = 1e-9,
    eos=None,
) -> IsothermalCompressibleGasResult:
    """Solve steady horizontal isothermal flow between two absolute pressures.

    The 1-D momentum balance retains both wall friction and the pressure-driven
    velocity change. The explicit analytic branch uses the perfect-gas density
    relation; the native branch uses CoolProp density. Dynamic viscosity
    and temperature are caller-declared constants. The caller supplies a Darcy
    friction correlation. Elevation, heat exchange, local losses, choking,
    and transient line inventory are outside this level. With ``eos=None`` an
    explicit molecular mass selects the analytic ideal-gas reference. A native
    CoolProp isothermal EOS instead supplies density and its derivative; no
    ideal fallback or effective compressibility factor is used. Native flow
    must remain below its isothermal sonic singularity along an adaptive
    momentum-ODE trajectory. This is a numerical domain gate, not a global
    mathematical proof or a choked-flow model.

    The independent implementation integrates steady mass/momentum conservation:
    G**2*(f*L/D + 2*log(rho_up/rho_down)) = 2*integral(rho(P,T), dP).
    The relation follows the differential momentum balance, with held viscosity
    and hence constant Re/f along the pipe. Scientific context:
    https://dwsim.org/help/main/24-unit-operations.html (momentum balance)
    https://coolprop.org/coolprop/HighLevelAPI.html (homogeneous derivatives).
    https://arxiv.org/abs/2410.20292 (nonideal isothermal pipeline context;
    its cubic EOS is not implemented here).
    Positive flow is from the higher upstream pressure to the lower downstream
    pressure; reverse flow is represented by swapping the endpoint pressures.
    """
    if not isinstance(geometry, DarcyGeometry):
        raise TypeError("geometry must be the shared DarcyGeometry")
    if geometry.local_loss_coefficient != 0.0:
        raise ValueError("isothermal compressible level currently requires zero local-loss coefficient")
    p_up = finite(upstream_pressure_pa, "upstream_pressure_pa", positive=True)
    p_down = finite(downstream_pressure_pa, "downstream_pressure_pa", positive=True)
    if p_up <= p_down:
        raise ValueError("upstream pressure must exceed downstream pressure; swap endpoints for reverse flow")
    temp = finite(temperature_k, "temperature_k", positive=True)
    viscosity = finite(viscosity_pa_s, "viscosity_pa_s", positive=True)
    absolute = finite(pressure_absolute_tolerance_pa,
                      "pressure_absolute_tolerance_pa", positive=True)
    relative = finite(pressure_relative_tolerance,
                      "pressure_relative_tolerance", positive=True)
    if not callable(friction_law):
        raise TypeError("friction_law must be callable")
    if not isinstance(friction_law_id, str) or not friction_law_id.strip():
        raise ValueError("friction_law_id must identify the supplied Darcy correlation")
    area = pi * geometry.diameter_m**2 / 4.0
    definitions = None
    integral_error = None
    if eos is None:
        if molecular_mass_kg_mol is None:
            raise ValueError("An analytic ideal-gas reference requires explicit molecular mass")
        molar_mass = finite(molecular_mass_kg_mol, "molecular_mass_kg_mol", positive=True)
        gas_constant = 8.31446261815324 / molar_mass
        rho_up, rho_down = p_up/(gas_constant*temp), p_down/(gas_constant*temp)
        density_integral = (p_up-p_down)*(p_up+p_down)/(2.*gas_constant*temp)
    else:
        from .thermo.isothermal_eos import CoolPropIsothermalEOS, CoolPropMixtureIsothermalEOS
        if type(eos) is CoolPropIsothermalEOS:
            if eos.backend != "HEOS":
                raise ValueError("Native isothermal hydraulics requires direct HEOS")

            def definition():
                return (eos.identity, eos.fluid, eos.backend, eos.version,
                        id(eos._state), id(eos._cp), eos.density_pt,
                        eos.pressure_rho_t, eos.isothermal_sound_speed_rho_t,
                        eos._allowed_phases, eos._require_homogeneous_gas,
                        eos._update_pt, eos._update_rho_t,
                        tuple(eos._state.fluid_names()))

            definitions = definition()
            expected_phases = frozenset((eos._cp.iphase_gas,
                                        eos._cp.iphase_supercritical_gas,
                                        eos._cp.iphase_supercritical))
            if definitions[-1] != (eos.fluid,) or eos._allowed_phases != expected_phases:
                raise ValueError("Native EOS fluid identity or homogeneous-gas admission differs")
            native_owner = eos
        elif type(eos) is CoolPropMixtureIsothermalEOS:
            native_owner = eos.properties
            if native_owner.backend != "HEOS":
                raise ValueError("Native frozen-mixture hydraulics requires direct HEOS")
            for name in ("density_pt", "pressure_rho_t", "isothermal_sound_speed_rho_t"):
                if getattr(getattr(eos, name), "__func__", None) is not getattr(CoolPropMixtureIsothermalEOS, name):
                    raise ValueError("Use the original frozen-mixture native EOS methods")
            if eos._require_gas is not CoolPropMixtureIsothermalEOS._require_gas:
                raise ValueError("Retain the native frozen-mixture homogeneous-gas admission")

            def definition():
                return (eos.identity, eos._definition_snapshot(), id(eos),
                        eos.density_pt, eos.pressure_rho_t,
                        eos.isothermal_sound_speed_rho_t, eos._require_gas,
                        type(native_owner).molar_mass_kg_mol.fget)

            definitions = definition()
        else:
            raise TypeError("Use the original direct CoolPropIsothermalEOS or CoolPropMixtureIsothermalEOS provider")

        def require_definition():
            if definition() != definitions:
                raise ValueError("Native hydraulic EOS definition changed during evaluation")

        def native_density(pressure):
            require_definition()
            density = finite(eos.density_pt(float(pressure), temp), "native density", positive=True)
            require_definition()
            return density

        if molecular_mass_kg_mol is not None:
            supplied_mass = finite(molecular_mass_kg_mol, "molecular_mass_kg_mol", positive=True)
            if type(eos) is CoolPropMixtureIsothermalEOS:
                native_mass = native_owner.molar_mass_kg_mol
            else:
                with native_owner._lock:
                    native_mass = native_owner._state.molar_mass()
            if not isclose(supplied_mass, native_mass, rel_tol=1e-10):
                raise ValueError("Supplied molecular mass differs from native EOS")
        gas_constant = None
        rho_up, rho_down = native_density(p_up), native_density(p_down)
        # Normalize the integration coordinate to retain small pressure drops.
        mean_density, mean_error = quad(
            lambda z: native_density(p_down+(p_up-p_down)*z), 0., 1.,
            epsabs=1e-10*min(rho_up, rho_down), epsrel=1e-11, limit=150,
        )
        density_integral = finite((p_up-p_down)*mean_density, "density integral", positive=True)
        integral_error = finite((p_up-p_down)*mean_error, "density integral error estimate")
        if integral_error < 0. or integral_error > 1e-8*density_integral:
            raise RuntimeError("Native density quadrature did not meet its integration budget")
    if rho_up <= rho_down:
        raise ValueError("Isothermal density must increase across the admitted pressure path")
    pressure_ratio_log = log1p((rho_up-rho_down)/rho_down)
    target = 2.*density_integral*geometry.diameter_m**2/viscosity**2
    ratio_length = geometry.length_m / geometry.diameter_m

    def logarithmic_balance(log_reynolds):
        if eos is not None:
            require_definition()
        reynolds = exp(log_reynolds)
        factor = finite(
            friction_law(reynolds, geometry.roughness_m / geometry.diameter_m),
            "Darcy friction factor", positive=True,
        )
        resistance = factor * ratio_length + 2.0 * pressure_ratio_log
        return 2.0 * log_reynolds + log(resistance) - log(target)

    low = log(1e-12)
    low_value = logarithmic_balance(low)
    high = log(1e-6)
    high_value = logarithmic_balance(high)
    for _ in range(64):
        if high_value >= 0.0:
            break
        high += log(2.0)
        high_value = logarithmic_balance(high)
    else:
        raise RuntimeError("Could not bracket the compressible-gas pipe Reynolds number")
    if low_value >= 0.0:
        raise RuntimeError("Friction law did not admit a positive compressible-gas flow root")
    log_reynolds = brentq(logarithmic_balance, low, high,
                          xtol=1e-12, rtol=1e-12, maxiter=200)
    reynolds = exp(log_reynolds)
    friction = finite(
        friction_law(reynolds, geometry.roughness_m / geometry.diameter_m),
        "Darcy friction factor", positive=True,
    )
    mass_flow = reynolds * area * viscosity / geometry.diameter_m
    mass_flux = mass_flow/area
    momentum_residual = (2.*density_integral-mass_flux**2*(
        friction*ratio_length+2.*pressure_ratio_log))
    maximum_mach = None
    if eos is None:
        predicted_square = p_up**2-mass_flux**2*gas_constant*temp*(
            friction*ratio_length+2.*pressure_ratio_log)
        if predicted_square <= 0.0:
            raise RuntimeError("Compressible-gas momentum solution predicts nonpositive outlet pressure")
        predicted_downstream = sqrt(predicted_square)
    else:
        mach_samples = []

        def path_state(pressure):
            density = native_density(pressure)
            speed = finite(eos.isothermal_sound_speed_rho_t(density, temp),
                           "native isothermal characteristic speed", positive=True)
            require_definition()
            mach = mass_flux/(density*speed)
            mach_samples.append(mach)
            if mach >= 1.-1e-8:
                raise ValueError("Native hydraulic path reaches the isothermal sonic singularity")
            return density, mach

        # Endpoint checks reject an infeasible boundary pair before shooting.
        path_state(p_down)
        path_state(p_up)

        def momentum_rhs(_distance, pressure):
            density, mach = path_state(float(pressure[0]))
            return [-friction*mass_flux**2/(2.*geometry.diameter_m*density*(1.-mach**2))]

        pressure_budget = max(absolute, relative*(p_up-p_down))
        path = solve_ivp(
            momentum_rhs, (0., geometry.length_m), [p_up], method="DOP853",
            rtol=max(2.3e-14, min(1e-10, pressure_budget/(100.*p_up))),
            atol=pressure_budget/100., max_step=geometry.length_m/16.,
        )
        if not path.success or path.t[-1] != geometry.length_m:
            raise RuntimeError("Native momentum path did not reach the pipe outlet")
        predicted_downstream = finite(path.y[0, -1], "reconstructed downstream pressure", positive=True)
        require_definition()
        maximum_mach = max(mach_samples)
    residual = predicted_downstream - p_down
    result = IsothermalCompressibleGasResult(
        mass_flow_kg_s=mass_flow,
        inlet_velocity_m_s=mass_flow / (rho_up * area),
        outlet_velocity_m_s=mass_flow / (rho_down * area),
        reynolds_number=reynolds,
        darcy_friction_factor=friction,
        upstream_pressure_pa=p_up,
        downstream_pressure_pa=p_down,
        temperature_k=temp,
        specific_gas_constant_j_kg_k=gas_constant,
        modeled_downstream_pressure_pa=predicted_downstream,
        pressure_residual_pa=residual,
        friction_law_id=friction_law_id,
        eos_identity=None if eos is None else definitions[0],
        density_integral_pa_kg_m3=density_integral,
        density_integral_error_pa_kg_m3=integral_error,
        momentum_integral_residual_pa_kg_m3=momentum_residual,
        maximum_isothermal_mach_number=maximum_mach,
        native_path_gate=None if eos is None else "adaptive-momentum-ode",
    )
    if abs(residual) > max(absolute, relative * (p_up - p_down)):
        raise CompressibleGasConvergenceError(result)
    return result
