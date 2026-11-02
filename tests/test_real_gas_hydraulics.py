"""Generalized native momentum closure and unchanged analytic selection."""

import pytest

from h2physics.hydraulics import (
    CompressibleGasConvergenceError,
    DarcyGeometry,
    solve_isothermal_compressible_gas_flow,
)
from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS


def _arguments():
    return dict(geometry=DarcyGeometry(100., .1, 1.e-5),
                upstream_pressure_pa=1.e6, downstream_pressure_pa=.9e6,
                temperature_k=300., viscosity_pa_s=9.e-6,
                friction_law=lambda re, rr: .02, friction_law_id="authored-constant-factor")


def test_native_momentum_independent_ode_and_analytic_limit():
    from validation.cases.real_gas_hydraulics import validate_native_momentum
    assert validate_native_momentum(work_directory=None).accepted


def test_frozen_mixture_momentum_matches_independent_native_density_ode():
    from validation.cases.real_gas_hydraulics import validate_native_mixture_momentum
    assert validate_native_mixture_momentum(work_directory=None).accepted


def test_native_phase_and_sonic_domain_reject_without_substitution():
    args = _arguments()
    eos = CoolPropIsothermalEOS()
    with pytest.raises(ValueError, match="homogeneous"):
        solve_isothermal_compressible_gas_flow(**dict(args, temperature_k=20.), eos=eos)
    with pytest.raises(ValueError, match="sonic"):
        solve_isothermal_compressible_gas_flow(
            **dict(args, geometry=DarcyGeometry(.001, .1, 1.e-5), downstream_pressure_pa=.1e6), eos=eos,
        )


def test_native_provider_type_and_molecular_mass_are_not_silently_inferred():
    args = _arguments()
    with pytest.raises(TypeError, match="CoolPropIsothermalEOS"):
        solve_isothermal_compressible_gas_flow(**args, eos=object())
    with pytest.raises(ValueError, match="molecular mass"):
        solve_isothermal_compressible_gas_flow(**args, eos=CoolPropIsothermalEOS(),
                                             molecular_mass_kg_mol=.028)
    with pytest.raises(ValueError, match="explicit molecular mass"):
        solve_isothermal_compressible_gas_flow(**args)


@pytest.mark.parametrize("attribute", ["_state", "_allowed_phases"])
def test_eos_definition_mutation_during_friction_root_is_rejected(attribute):
    eos = CoolPropIsothermalEOS()
    original = getattr(eos, attribute)
    replacement = CoolPropIsothermalEOS()._state if attribute == "_state" else frozenset()

    def mutating_factor(re, rr):
        setattr(eos, attribute, replacement)
        return .02

    try:
        with pytest.raises(ValueError, match="definition changed"):
            solve_isothermal_compressible_gas_flow(
                **dict(_arguments(), friction_law=mutating_factor), eos=eos,
            )
    finally:
        setattr(eos, attribute, original)


def test_discontinuous_friction_root_must_close_independent_pressure_path():
    args = _arguments()
    eos = CoolPropIsothermalEOS()
    baseline = solve_isothermal_compressible_gas_flow(**args, eos=eos)
    transition = baseline.reynolds_number

    def discontinuous(re, rr):
        return .005 if re < transition else .08

    with pytest.raises(CompressibleGasConvergenceError):
        solve_isothermal_compressible_gas_flow(
            **dict(args, friction_law=discontinuous), eos=eos,
        )
