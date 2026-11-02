"""Native isothermal Darcy momentum checks, distinct from property calibration."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="native-isothermal-real-gas-darcy-momentum",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_native_momentum",
        invariants=(
            "density-integral-and-independent-density-ODE-close-high-pressure-endpoints",
            "low-density-native-flow-approaches-the-explicit-analytic-reference",
            "viscosity-is-held-constant-and-native-EOS-identity-is-retained",
            "near-zero-pressure-drop-retains-positive-flow-and-true-pressure-diagnostics",
        ),
    ), ValidationCase(
        identifier="native-isothermal-real-gas-short-pipe-reference",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_short_pipe_reference",
        invariants=(
            "short-friction-length-exposes-acceleration-log-sign-and-factor-errors",
            "independent-native-density-derivative-quadrature-and-ODE-reproduce-the-mass-root",
            "small-pressure-drop-approaches-the-local-native-density-limit",
            "native-derived-infeasible-sonic-branch-and-liquid-state-reject",
            "isothermal-derivative-is-used-instead-of-adiabatic-sound-speed",
        ),
    ), ValidationCase(
        identifier="native-frozen-mixture-isothermal-darcy-momentum",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_native_mixture_momentum",
        invariants=(
            "frozen-H2-N2-native-momentum-retains-composition-reference-and-unresolved-spin",
            "independent-native-density-ODE-reproduces-the-requested-downstream-pressure",
            "held-viscosity-and-adaptive-subcritical-path-admission-are-explicit",
        ),
    ))


def validate_native_momentum(*, work_directory, **parameters):
    del work_directory, parameters
    import CoolProp.CoolProp as cp
    from scipy.integrate import solve_ivp

    from h2physics.hydraulics import DarcyGeometry, solve_isothermal_compressible_gas_flow
    from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS

    eos = CoolPropIsothermalEOS("Hydrogen")
    geometry = DarcyGeometry(100., .1, 1.e-5)
    common = dict(geometry=geometry, temperature_k=300., viscosity_pa_s=9.e-6,
                  friction_law=lambda re, rr: .02, friction_law_id="authored-constant-Darcy-factor")
    high = solve_isothermal_compressible_gas_flow(
        **common, upstream_pressure_pa=70.e6, downstream_pressure_pa=60.e6, eos=eos,
    )
    area = 3.141592653589793*geometry.diameter_m**2/4.
    flux = high.mass_flow_kg_s/area
    initial_density = cp.PropsSI("Dmass", "P", 70.e6, "T", 300., "HEOS::Hydrogen")

    def density_momentum(_distance, value):
        # Independent dependent variable and native derivative API; no use of
        # production density quadrature or production pressure RHS.
        rho = float(value[0])
        dp_drho = cp.PropsSI("d(P)/d(Dmass)|T", "Dmass", rho, "T", 300., "HEOS::Hydrogen")
        return [-.02*flux**2/(2.*geometry.diameter_m*rho*(dp_drho-flux**2/rho**2))]

    independent = solve_ivp(density_momentum, (0., geometry.length_m), [initial_density],
                            method="DOP853", rtol=1.e-11, atol=1.e-12,
                            max_step=geometry.length_m/20.)
    assert independent.success
    independent_outlet = cp.PropsSI("P", "Dmass", independent.y[0, -1],
                                   "T", 300., "HEOS::Hydrogen")
    assert abs(independent_outlet-60.e6) < .01
    assert abs(high.pressure_residual_pa) < .01
    assert high.specific_gas_constant_j_kg_k is None
    assert high.eos_identity == eos.identity
    assert high.viscosity_model == "held-constant"
    assert 0. < high.maximum_isothermal_mach_number < 1.

    low_args = dict(common, upstream_pressure_pa=100., downstream_pressure_pa=90.)
    native_low = solve_isothermal_compressible_gas_flow(**low_args, eos=eos)
    analytic_low = solve_isothermal_compressible_gas_flow(
        **low_args, molecular_mass_kg_mol=.00201588,
    )
    relative_limit_error = abs(native_low.mass_flow_kg_s/analytic_low.mass_flow_kg_s-1.)
    assert relative_limit_error < 1.e-5
    tiny = solve_isothermal_compressible_gas_flow(
        **common, upstream_pressure_pa=1.e6, downstream_pressure_pa=1.e6-.001, eos=eos,
    )
    assert tiny.mass_flow_kg_s > 0. and abs(tiny.pressure_residual_pa) < 1.e-5
    return ValidationOutcome(True, {
        "native_mass_flow_kg_s": high.mass_flow_kg_s,
        "independent_density_ode_outlet_error_pa": independent_outlet-60.e6,
        "reconstructed_pressure_residual_pa": high.pressure_residual_pa,
        "native_momentum_integral_residual_pa_kg_m3": high.momentum_integral_residual_pa_kg_m3,
        "maximum_observed_isothermal_mach_number": high.maximum_isothermal_mach_number,
        "density_integral_error_estimate_pa_kg_m3": high.density_integral_error_pa_kg_m3,
        "low_density_analytic_limit_relative_error": relative_limit_error,
        "small_pressure_drop_flow_kg_s": tiny.mass_flow_kg_s,
    }, (
        "Numerical momentum and EOS consistency only; no measured pipeline comparison.",
        "Constant caller viscosity and Darcy factor; no thermal-control duty, choking solution, or wave dynamics.",
        "Adaptive path admission is a numerical gate, not a global mathematical bound over the EOS.",
    ))


def validate_short_pipe_reference(*, work_directory, **parameters):
    """Independent short-pipe reference with a significant acceleration term."""
    del work_directory, parameters
    from math import log, pi, sqrt

    import CoolProp
    import CoolProp.CoolProp as cp
    from scipy.integrate import quad, solve_ivp
    from scipy.optimize import brentq

    from h2physics.hydraulics import DarcyGeometry, solve_isothermal_compressible_gas_flow
    from h2physics.thermo import CoolPropIsothermalEOS

    temperature, upstream, downstream = 300., 70e6, 60e6
    diameter, length, friction = .02, .5, .02
    area = pi*diameter**2/4.
    native = CoolProp.AbstractState("HEOS", "Hydrogen")
    native.update(cp.PT_INPUTS, upstream, temperature)
    rho_up, viscosity = native.rhomass(), native.viscosity()
    native.update(cp.PT_INPUTS, downstream, temperature)
    rho_down = native.rhomass()
    c_down_squared = native.first_partial_deriv(cp.iP, cp.iDmass, cp.iT)

    def native_pressure_derivative(density):
        native.update(cp.DmassT_INPUTS, density, temperature)
        assert native.phase() in {cp.iphase_gas, cp.iphase_supercritical, cp.iphase_supercritical_gas}
        return native.first_partial_deriv(cp.iP, cp.iDmass, cp.iT)

    # Independent integration variable and derivative API. Integrating
    # dx/drho from steady mass/momentum gives the travel length for a trial G.
    density_integral, _error = quad(
        lambda z: (rho_down+(rho_up-rho_down)*z)*native_pressure_derivative(
            rho_down+(rho_up-rho_down)*z),
        0., 1., epsabs=1e-6, epsrel=1e-11)
    density_integral *= rho_up-rho_down
    critical_flux_at_outlet = rho_down*sqrt(c_down_squared)

    def length_residual(flux):
        return (2.*diameter/(friction*flux**2)
                *(density_integral-flux**2*log(rho_up/rho_down))-length)

    reference_flux = brentq(length_residual, .01*critical_flux_at_outlet,
                            .95*critical_flux_at_outlet, xtol=1e-8, rtol=1e-12)

    def independent_density_ode(_distance, value):
        density = float(value[0])
        derivative = native_pressure_derivative(density)
        return [-friction*reference_flux**2/(2.*diameter*density
                    *(derivative-reference_flux**2/density**2))]

    path = solve_ivp(independent_density_ode, (0., length), [rho_up], method="DOP853",
                     rtol=3e-12, atol=1e-12, max_step=length/32.)
    assert path.success
    native.update(cp.DmassT_INPUTS, float(path.y[0, -1]), temperature)
    independent_outlet_error = native.p()-downstream
    assert abs(independent_outlet_error) < .01

    def solve(p_up, p_down, *, pipe_length=length, temp=temperature):
        return solve_isothermal_compressible_gas_flow(
            DarcyGeometry(pipe_length, diameter, 0.), upstream_pressure_pa=p_up,
            downstream_pressure_pa=p_down, temperature_k=temp, viscosity_pa_s=viscosity,
            friction_law=lambda re, rr: friction,
            friction_law_id="authored-short-pipe-held-Darcy-factor",
            eos=CoolPropIsothermalEOS("Hydrogen"))

    actual = solve(upstream, downstream)
    reference_mass_flow = reference_flux*area
    relative_mass_error = abs(actual.mass_flow_kg_s/reference_mass_flow-1.)
    assert relative_mass_error < 5e-10
    assert abs(actual.pressure_residual_pa) < .01
    assert 0. < actual.maximum_isothermal_mach_number < 1.
    small_drop_results = []
    for requested_drop in (1., 1e-3):
        p_down = upstream-requested_drop
        actual_drop = upstream-p_down
        native.update(cp.PT_INPUTS, p_down, temperature)
        # The low-delta-P limit uses local native density, not an ideal EOS.
        limit = sqrt(2.*native.rhomass()*actual_drop/(friction*length/diameter))*area
        result = solve(upstream, p_down)
        limit_error = abs(result.mass_flow_kg_s/limit-1.)
        assert limit_error < 1e-5
        assert abs(result.pressure_residual_pa) < 1e-5
        small_drop_results.append({"pressure_drop_pa": actual_drop,
            "mass_flow_kg_s": result.mass_flow_kg_s,
            "local_native_limit_mass_flow_kg_s": limit,
            "relative_limit_error": limit_error,
            "pressure_residual_pa": result.pressure_residual_pa})

    critical_lambda = (2.*density_integral/(rho_down**2*c_down_squared)
                       -2.*log(rho_up/rho_down))
    assert critical_lambda > 0.
    try:
        solve(upstream, downstream, pipe_length=.25*critical_lambda*diameter/friction)
    except ValueError as error:
        assert "sonic" in str(error)
    else:
        raise AssertionError("An infeasible native isothermal sonic root was admitted")
    try:
        solve(1e6, .9e6, temp=20.)
    except ValueError as error:
        assert "phase" in str(error) or "gas" in str(error)
    else:
        raise AssertionError("Liquid hydrogen was admitted into the homogeneous gas level")
    try:
        solve(upstream, upstream)
    except ValueError as error:
        assert "exceed" in str(error)
    else:
        raise AssertionError("An equal-pressure pair was admitted as a positive-direction root")
    return ValidationOutcome(True, {
        "coolprop_version": CoolProp.__version__,
        "friction_length_ratio": friction*length/diameter,
        "acceleration_log_term": 2.*log(rho_up/rho_down),
        "native_mass_flow_kg_s": actual.mass_flow_kg_s,
        "independent_mass_flow_kg_s": reference_mass_flow,
        "relative_mass_flow_error": relative_mass_error,
        "independent_density_ode_outlet_error_pa": independent_outlet_error,
        "production_outlet_residual_pa": actual.pressure_residual_pa,
        "maximum_observed_isothermal_mach_number": actual.maximum_isothermal_mach_number,
        "small_pressure_drop_results": tuple(small_drop_results),
        "native_critical_friction_length_ratio": critical_lambda,
        "tested_infeasible_friction_length_ratio": .25*critical_lambda,
        "sonic_liquid_and_equal_pressure_rejected": True,
    }, (
        "Native-EOS numerical momentum reference; no measured pipe or friction calibration",
        "Constant caller viscosity and Darcy factor, fixed temperature, homogeneous gas only",
        "The local-density small-drop expression is a test limit, not a production fluid EOS",
    ))


def validate_native_mixture_momentum(*, work_directory, **parameters):
    del work_directory, parameters
    import CoolProp
    import CoolProp.CoolProp as cp
    from scipy.integrate import solve_ivp

    from h2physics.hydraulics import DarcyGeometry, solve_isothermal_compressible_gas_flow
    from h2physics.mixtures import GasComposition
    from h2physics.thermo import CoolPropMixtureIsothermalEOS, CoolPropMixtureProperties

    properties = CoolPropMixtureProperties(GasComposition(
        "frozen-H2-N2-momentum", ("Hydrogen", "Nitrogen"), (.1, .9), (.00201588, .0280134),
    ))
    eos = CoolPropMixtureIsothermalEOS(properties)
    viscosity = properties.state_pt(7.e6, 300.).viscosity_pa_s
    geometry = DarcyGeometry(.5, .02, 1.e-6)
    result = solve_isothermal_compressible_gas_flow(
        geometry, upstream_pressure_pa=7.e6, downstream_pressure_pa=6.e6,
        temperature_k=300., viscosity_pa_s=viscosity,
        molecular_mass_kg_mol=properties.molar_mass_kg_mol, eos=eos,
        friction_law=lambda re, rr: .02, friction_law_id="authored-constant-mixture-factor",
    )
    native = CoolProp.AbstractState("HEOS", "Hydrogen&Nitrogen")
    native.set_mole_fractions([.1, .9])
    native.update(cp.PT_INPUTS, 7.e6, 300.)
    rho_initial = native.rhomass()
    area = 3.141592653589793*geometry.diameter_m**2/4.
    flux = result.mass_flow_kg_s/area

    def density_rhs(_distance, values):
        rho = float(values[0])
        native.update(cp.DmassT_INPUTS, rho, 300.)
        derivative = native.first_partial_deriv(cp.iP, cp.iDmass, cp.iT)
        return [-.02*flux**2/(2.*geometry.diameter_m*rho*(derivative-flux**2/rho**2))]

    reference = solve_ivp(density_rhs, (0., geometry.length_m), [rho_initial],
                          method="DOP853", rtol=1.e-11, atol=1.e-11,
                          max_step=geometry.length_m/32.)
    assert reference.success
    native.update(cp.DmassT_INPUTS, float(reference.y[0, -1]), 300.)
    independent_error = native.p()-6.e6
    assert abs(independent_error) < .01
    assert abs(result.pressure_residual_pa) < .001
    assert result.eos_identity == eos.identity
    assert "mixture-H2-spin-unresolved" in result.eos_identity
    assert result.specific_gas_constant_j_kg_k is None
    assert result.viscosity_model == "held-constant"
    assert 0. < result.maximum_isothermal_mach_number < 1.
    return ValidationOutcome(True, {
        "composition_sha256": properties.composition_sha256,
        "mixture_mass_flow_kg_s": result.mass_flow_kg_s,
        "independent_density_ode_outlet_error_pa": independent_error,
        "reconstructed_pressure_residual_pa": result.pressure_residual_pa,
        "maximum_observed_isothermal_mach_number": result.maximum_isothermal_mach_number,
        "held_viscosity_pa_s": viscosity,
        "native_molar_mass_kg_mol": properties.molar_mass_kg_mol,
    }, (
        "Synthetic fixed-composition native momentum verification, not blend-pipeline measurements.",
        "Native viscosity at the upstream reference is held constant along the isothermal link.",
        "Composition and unresolved H2 spin retain the original provider meaning; no species transport is solved.",
    ))
