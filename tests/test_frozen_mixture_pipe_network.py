"""Frozen-mixture basis admission through the existing network and Darcy APIs."""

from dataclasses import replace

import pytest

from h2physics.hydraulics import DarcyGeometry, solve_isothermal_compressible_gas_flow
from h2physics.isothermal_gas_pipe_network import (
    IsothermalGasPipeNetwork,
    IsothermalPipeCell,
    IsothermalPipeLink,
)
from h2physics.mixtures import GasComposition
from h2physics.thermo import CoolPropMixtureIsothermalEOS, CoolPropMixtureProperties


def _eos(*, name="mixture-network-guards", fractions=(.1, .9), reference_suffix=""):
    properties = CoolPropMixtureProperties(GasComposition(
        name, ("Hydrogen", "Nitrogen"), fractions, (.00201588, .0280134),
    ))
    if reference_suffix:
        object.__setattr__(properties, "_basis", replace(properties.basis,
            reference_id=properties.basis.reference_id+reference_suffix))
    return CoolPropMixtureIsothermalEOS(properties)


def _cell(name, eos, temperature=300.):
    return IsothermalPipeCell.from_pressure(cell_id=name, volume_m3=.001,
        temperature_k=temperature, pressure_pa=5.e6, eos=eos)


def _network(cells):
    return IsothermalGasPipeNetwork(cells,
        (IsothermalPipeLink("link", DarcyGeometry(10., .001, 1.e-6), 1.8e-5),),
        lambda re, rr: .03, "authored-mixture-guard-factor")


def test_closed_mixture_network_mass_and_real_step_refinement():
    from validation.cases.isothermal_gas_pipe_network import validate_native_mixture_network
    assert validate_native_mixture_network(work_directory=None).accepted


@pytest.mark.parametrize("variant", ["composition", "composition_id", "reference", "temperature"])
def test_cells_reject_different_frozen_mixture_meanings(variant):
    first = _cell("first", _eos())
    options = {
        "composition": dict(fractions=(.2, .8)),
        "composition_id": dict(name="different-source-composition"),
        "reference": dict(reference_suffix=":other-reference"),
        "temperature": {},
    }
    second = _cell("second", _eos(**options[variant]),
                   temperature=310. if variant == "temperature" else 300.)
    with pytest.raises(ValueError):
        _network((first, second))


@pytest.mark.parametrize("attribute", ["_state", "mole_fractions", "_basis"])
def test_network_rejects_native_mixture_owner_and_basis_mutations(attribute):
    eos = _eos()
    network = _network((_cell("first", eos), _cell("second", _eos())))
    properties = eos.properties
    original = getattr(properties, attribute)
    replacements = {
        "_state": _eos().properties._state,
        "mole_fractions": (.2, .8),
        "_basis": replace(properties.basis, spin_composition="authored-other-spin"),
    }
    try:
        object.__setattr__(properties, attribute, replacements[attribute])
        with pytest.raises(ValueError, match="definition changed"):
            network.require_current()
    finally:
        object.__setattr__(properties, attribute, original)
    network.require_current()


def test_native_mixture_hydraulics_rejects_mid_root_reference_mutation_and_cold_phase():
    eos = _eos()
    basis = eos.properties.basis
    original = basis.reference_id

    def mutating_factor(re, rr):
        object.__setattr__(basis, "reference_id", original+":mutated")
        return .02

    arguments = dict(geometry=DarcyGeometry(.5, .02, 1.e-6), upstream_pressure_pa=7.e6,
        downstream_pressure_pa=6.e6, temperature_k=300., viscosity_pa_s=1.8e-5,
        eos=eos, friction_law=mutating_factor, friction_law_id="authored-mutating-mixture-factor")
    try:
        with pytest.raises(ValueError, match="definition changed"):
            solve_isothermal_compressible_gas_flow(**arguments)
    finally:
        object.__setattr__(basis, "reference_id", original)
    with pytest.raises(ValueError):
        solve_isothermal_compressible_gas_flow(**dict(arguments,
            temperature_k=20., upstream_pressure_pa=1.e5, downstream_pressure_pa=.9e5,
            friction_law=lambda re, rr: .02))
