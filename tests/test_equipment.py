from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt import Lh2dtProperties, to_lh2dt_state
from h2physics.adapters.lh2dt_equipment import (
    EquipmentNetworkSnapshot,
    Lh2dtEquipmentNetwork,
    Lh2dtSharedValve,
    stratified_node_with_heat_ledger,
)
from h2physics.core import PropertyBasis, ThermoState
from h2physics.equipment import BoundaryPower, ConnectionTransfer, EquipmentTolerances
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening


def state(enthalpy=1000.):
    return ThermoState(PropertyBasis("test-fluid", "authored-reference"), 1e5, 300., 1.,
                       enthalpy, enthalpy-1e5, 100., "gas")


def transfer():
    return ConnectionTransfer("unit", "left", "right", "left/out", "right/in", .1,
                              state(), state(1600.), BoundaryPower(40., 20.), None, None)


def test_heat_shaft_and_reverse_transport_use_the_actual_upstream_state():
    forward = transfer()
    assert forward.energy_residual_w == 0.
    assert forward.upstream_node == "left" and forward.downstream_node == "right"
    reverse = replace(forward, mass_flow_kg_s=-.1, upstream=state(1600.), transmitted=state(1500.),
                      power=BoundaryPower(-10., 0.))
    assert reverse.upstream_node == "right" and reverse.downstream_node == "left"
    assert reverse.energy_residual_w == 0.
    assert reverse.inlet_enthalpy_flow_w == 160.


def test_closed_transfer_has_no_fake_transport_state_or_reference_conversion():
    closed = replace(transfer(), mass_flow_kg_s=0., upstream=None, transmitted=None, power=BoundaryPower())
    assert closed.upstream_node is None and closed.energy_residual_w == 0.
    with pytest.raises(ValueError, match="no transported state"):
        replace(closed, upstream=state())
    with pytest.raises(ValueError, match="bases differ"):
        replace(transfer(), transmitted=replace(state(), basis=PropertyBasis("other", "other")))


def test_network_checks_power_even_when_mass_closes_and_retains_unknown_momentum():
    snapshot = EquipmentNetworkSnapshot({"left": state(), "right": state(1600.)}, (transfer(),),
        {}, {}, .1, .1, 100., 160., True, object())
    assert not snapshot.violations(EquipmentTolerances())
    assert snapshot.missing_momentum_components == ("unit",)
    with pytest.raises(TypeError):
        snapshot.node_states["extra"] = state()
    broken = replace(snapshot, transfers=(replace(transfer(), power=BoundaryPower()),))
    assert any("enthalpy/power" in issue for issue in broken.violations(EquipmentTolerances()))
    inadmissible = replace(snapshot, transfers=(replace(transfer(), operating_point_admissible=False),))
    assert any("inadmissible" in issue for issue in inadmissible.violations(EquipmentTolerances()))


def test_native_valve_contains_actual_factory_result_and_preserves_source_regime():
    pytest.importorskip("CoolProp")
    from h2physics.thermo import CoolPropProperties

    props = CoolPropProperties("Hydrogen")
    bridge = Lh2dtProperties(SimpleNamespace(fluid="Hydrogen"), reference_id=props.basis.reference_id)
    valve = Lh2dtSharedValve(HomogeneousIsentropicNozzle(props), bridge,
        NozzleOpening.circular("valve-A", .001, effective_area_factor=.8, area_basis_id="authored"),
        result_factory=SimpleNamespace, opening_fraction=1., allow_reverse=True)
    high = to_lh2dt_state(props.state_pt(1e6, 300.), expected_basis=props.basis, factory=SimpleNamespace)
    low = to_lh2dt_state(props.state_pt(2e5, 300.), expected_basis=props.basis, factory=SimpleNamespace)
    forward, reverse = valve.evaluate(high, low), valve.evaluate(low, high)
    assert isinstance(forward.native, SimpleNamespace)
    assert forward.mass_flow_kg_s == pytest.approx(-reverse.mass_flow_kg_s)
    assert reverse.upstream_side == "right"
    assert forward.outlet_specific_enthalpy_J_kg == high.specific_enthalpy_J_kg
    assert forward.nozzle.exit_state.enthalpy_j_kg < forward.outlet_specific_enthalpy_J_kg
    valve.set_opening(0.)
    closed = valve.evaluate(high, low)
    assert closed.mass_flow_kg_s == 0. and closed.upstream_side is None
    assert closed.nozzle.regime == "closed" and closed.nozzle.exit_state is None


def test_stratified_heat_bridge_preserves_native_derivative_and_hooks():
    @dataclass(frozen=True)
    class Node:
        derivative: object
        advance: object
        combine_derivatives: object

    raw = SimpleNamespace(lower_ambient_heat_W=12., upper_ambient_heat_W=18.,
                          liquid_mass_kg_s=-.01, vapor_mass_kg_s=.001)
    original = Node(lambda *_: raw, object(), object())
    bridged = stratified_node_with_heat_ledger(original)
    result = bridged.derivative(None, (), 0.)
    assert result.native is raw
    assert result.ambient_heat_W == 30.
    assert result.liquid_mass_kg_s == raw.liquid_mass_kg_s
    assert bridged.advance is original.advance
    assert bridged.combine_derivatives is original.combine_derivatives


def test_declared_reference_cannot_override_a_known_different_native_fluid():
    owner = SimpleNamespace(fluid="ParaHydrogen")
    bridge = Lh2dtProperties(owner, reference_id="test-reference")
    graph = SimpleNamespace(properties=owner)
    adapter = Lh2dtEquipmentNetwork(graph, bridge, state_factory=SimpleNamespace)
    wrong = SimpleNamespace(properties=SimpleNamespace(fluid="Hydrogen"))
    with pytest.raises(ValueError, match="contradictory native fluid"):
        adapter.add_link("wrong", "left", "right", wrong, power_reader=lambda _: BoundaryPower(),
                         source_port_id="left/out", target_port_id="right/in", declared_basis=bridge.basis)
