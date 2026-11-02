import math
from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
import pytest

from h2physics.adapters.hyram import HyRAMJetError, run_hyram_gas_jet
from h2physics.adapters.slabx_lh2 import (
    SLABLH2Error,
    run_slabx_lh2,
    steady_vapor_pool_boundary,
)
from h2physics.core import Origin, PropertyBasis, ThermoState
from h2physics.dispersion import preferred_dispersion_provider
from h2physics.release import NozzleOpening, SourceLocation
from h2physics.sources import IntervalMassSource


def state(fluid="Hydrogen", spin="normal", quality=1.):
    return ThermoState(PropertyBasis(fluid, "authored", spin), 101325., 300., 1.,
                        101325., 0., 0., "gas", vapor_mass_fraction=quality)


def source(rates=(.001, .001)):
    return IntervalMassSource(SourceLocation("test", "clock", "ground-relative",
        (0, 0, 0), (0, 0, 1)), np.array([10., 20., 30.]), np.array(rates)*10,
        state(), Origin.SYNTHETIC, "authored-source", "isolation")


def boundary(rates=(.001, .001)):
    return steady_vapor_pool_boundary(source(rates), native_pool_factory=lambda **kw:
        SimpleNamespace(**kw), substance=SimpleNamespace(mw=.002016), area_m2=1.,
        footprint_evidence_id="authored-area", ambient_pressure_pa=101325.)


def test_origin_based_preferences_reject_unknown_routes():
    assert preferred_dispersion_provider("high_pressure_gas") == "hyram"
    assert preferred_dispersion_provider("liquid_hydrogen_origin") == "slabx-lh2"
    with pytest.raises(ValueError):
        preferred_dispersion_provider("choose_from_current_vapor_phase")


def test_variable_source_is_not_replaced_by_its_mean():
    with pytest.raises(ValueError, match="Variable"):
        boundary((.001, .002))
    b = boundary()
    assert b.native_source.rate*b.native_source.duration == pytest.approx(.02)
    assert b.native_source.duration == 20  # absolute final time is 30 s
    assert b.native_source.T_source == b.mass_source.state.temperature_k


def test_pool_boundary_does_not_accept_liquid_or_other_pressure():
    s = source()
    liquid = IntervalMassSource(s.location, s.edges_s, s.mass_kg, state(quality=0.),
                                s.origin, s.evidence_id, s.end_reason)
    for value, pressure in ((liquid, 101325.), (s, 1e5)):
        with pytest.raises(ValueError):
            steady_vapor_pool_boundary(value, native_pool_factory=lambda **kw: None,
                substance=SimpleNamespace(mw=.002016), area_m2=1,
                footprint_evidence_id="authored", ambient_pressure_pa=pressure)


@pytest.mark.parametrize("maximum,violated,accepted", [(0.1, False, True), (2., True, False),
                                                     (math.nan, False, False)])
def test_post_run_premise_is_fail_closed_and_preserves_native(maximum, violated, accepted):
    b = boundary()
    native = SimpleNamespace(x=np.array([1., 2.]))
    result = run_slabx_lh2(boundary=b, atmosphere=SimpleNamespace(p=101325),
        emission_thermo=SimpleNamespace(substance=b.native_source.substance), water_thermo=object(),
        runner=lambda *a, **k: (native, b.native_source),
        premise_check=lambda t: {"max": maximum, "violated": violated},
        width_context=lambda enabled: nullcontext(), width_coupling=True, x_max_m=10,
        require_accepted=False)
    assert result.native is native and result.accepted == accepted
    if not accepted:
        with pytest.raises(SLABLH2Error) as caught:
            run_slabx_lh2(boundary=b, atmosphere=SimpleNamespace(p=101325),
                emission_thermo=SimpleNamespace(substance=b.native_source.substance), water_thermo=object(),
                runner=lambda *a, **k: (native, b.native_source),
                premise_check=lambda t: {"max": maximum, "violated": violated},
                width_context=lambda enabled: nullcontext(), width_coupling=False, x_max_m=10)
        assert caught.value.native is native


def test_hyram_initialization_loss_is_distinct_from_ode_drift():
    # Authored factory fixtures exercise source ownership, without implementing a jet.
    up = ThermoState(PropertyBasis("Hydrogen", "authored", "normal"), 2e6, 300., 1.,
                     2e6, 0., 0., "gas")
    lam = 1.
    native = SimpleNamespace(mass_flow_rate=1., lam=lam, rho_cl=np.ones(2), Y_cl=np.ones(2),
        V_cl=np.ones(2), B=np.full(2, math.sqrt(1.5/math.pi)), S=np.array([1., 2.]),
        x=np.array([1., 2.]), y=np.zeros(2), X_cl=np.ones(2))
    kwargs = dict(fluid_factory=lambda *a, **k: SimpleNamespace(rho=1.,
        therm=SimpleNamespace(get_property=lambda label, **kw: kw["P"])),
        orifice_factory=lambda *a, **k: object(), jet_factory=lambda *a, **k: native,
        upstream=up, ambient=state("Air", "unspecified"),
        opening=NozzleOpening.circular("authored", .002, effective_area_factor=.8, area_basis_id="test"),
        location=SourceLocation("test", "clock", "xz", (0, 0, 2), (1, 0, 0)),
        evidence_id="authored", solver_options={"Smax": 2.})
    result = run_hyram_gas_jet(**kwargs, require_accepted=False)
    assert result.native is native and not result.accepted
    assert result.gaussian_entry_h2_flow_kg_s == pytest.approx(.75)
    assert result.maximum_transport_h2_residual_kg_s == 0
    assert result.maximum_h2_flux_residual_kg_s == pytest.approx(.25)
    assert not result.centreline.flags.writeable
    with pytest.raises(HyRAMJetError) as caught:
        run_hyram_gas_jet(**kwargs)
    assert caught.value.native is native


def test_source_physics_cannot_be_overridden_through_solver_options():
    up = ThermoState(PropertyBasis("Hydrogen", "authored", "normal"), 2e6, 300, 1, 2e6, 0, 0, "gas")
    with pytest.raises(ValueError, match="ownership"):
        run_hyram_gas_jet(fluid_factory=lambda: None, orifice_factory=lambda: None,
            jet_factory=lambda: None, upstream=up, ambient=state("Air", "unspecified"),
            opening=NozzleOpening.circular("a", .001, effective_area_factor=1, area_basis_id="test"),
            location=SourceLocation("a", "clock", "xz", (0, 0, 0), (1, 0, 0)),
            evidence_id="authored", solver_options={"Smax": 1, "mdot": 1})
