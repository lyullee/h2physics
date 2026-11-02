import hashlib
from pathlib import Path

import numpy as np
import pytest

ct = pytest.importorskip("cantera")

from h2physics.adapters.cantera import (
    CanteraGas,
    MechanismBasis,
    ReactiveState,
    temperature_rise_event,
)


def backend():
    path = Path(ct.__file__).parent / "data/h2o2.yaml"
    raw = path.read_bytes()
    # Read through Python because Cantera 3.2's default Windows data path loses
    # non-ASCII characters in this workspace. No mechanism is copied to the repo.
    basis = MechanismBasis("Cantera:3.2:h2o2:ohmech", hashlib.sha256(raw).hexdigest(),
                           "Cantera-distribution-BSD-3-Clause; upstream-GRI-Mech-provenance",
                           ("https://cantera.org/3.2/examples/input/h2o2.html",),
                           300, 3500, 1e4, 2e6)
    return CanteraGas(lambda: ct.Solution(yaml=raw.decode("utf-8"), name="ohmech"), basis)


def initial(temperature=1000):
    total = 6.76
    return ReactiveState(temperature, 101325, {"H2": 2/total, "O2": 1/total, "N2": 3.76/total})


@pytest.mark.parametrize("constraint", ["HP", "UV"])
def test_reactive_equilibrium_conserves_elements_and_adiabatic_energy(constraint):
    result = backend().equilibrium(initial(), constraint=constraint)
    assert result.final.state.temperature_k > 2000
    assert abs(result.energy_residual_j_kg) < .01
    assert result.maximum_element_mass_fraction_residual < 1e-9


def test_closed_reactor_balances_and_declared_temperature_event():
    provider = backend()
    times = np.linspace(0, .002, 201)
    result = provider.closed_reactor(initial(1001), times, maximum_time_step_s=1e-5)
    assert result.maximum_energy_residual_j_kg < .1
    assert result.maximum_element_mass_fraction_residual < 1e-8
    event = temperature_rise_event(result, 200)
    assert 0 < event.lower_time_s < event.upper_time_s < .002
    assert event.lower_time_s <= event.linearly_estimated_time_s <= event.upper_time_s
    assert temperature_rise_event(result, 5000).linearly_estimated_time_s is None
    assert not result.time_s.flags.writeable


def test_reviewed_mechanism_polynomial_breakpoint_remains_visible_in_energy_diagnostic():
    if ct.__version__ != "3.2.0":
        pytest.skip("Breakpoint regression is specific to the reviewed mechanism distribution")
    provider = backend()
    result = provider.closed_reactor(initial(1000), np.linspace(0, .002, 101),
                                     maximum_time_step_s=1e-5, relative_tolerance=1e-11)
    # Tightening integration tolerance does not remove a thermochemical fit jump.
    # Do not reset energy references or modify the upstream mechanism to conceal it.
    assert .1 < result.maximum_energy_residual_j_kg < .2


def test_composition_and_mechanism_domain_are_not_inferred():
    with pytest.raises(ValueError, match="sum"):
        ReactiveState(300, 1e5, {"H2": 2, "O2": 1})
    with pytest.raises(ValueError, match="domain"):
        backend().equilibrium(initial(20))
