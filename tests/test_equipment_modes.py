from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt_modes import Lh2dtEquipmentMode, Lh2dtModeSwitch
from h2physics.equipment import BoundaryPower


class Device:
    def __init__(self, properties, result):
        self.properties, self.result, self.calls = properties, result, []

    def evaluate(self, left, right):
        self.calls.append((left, right))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_modes_preserve_actual_native_objects_and_use_the_selected_power_contract():
    props = object()
    running = Device(props, SimpleNamespace(mass_flow_kg_s=.02, shaft_power_W=30.,
        operating_point_physical_valid=True, cavitation_margin_m=4.))
    isolated = Device(props, SimpleNamespace(mass_flow_kg_s=0.))
    switch = Lh2dtModeSwitch(SimpleNamespace(native=props), {
        "running": Lh2dtEquipmentMode(running, lambda raw: BoundaryPower(shaft_work_w=raw.shaft_power_W)),
        "isolated": Lh2dtEquipmentMode(isolated, lambda raw: BoundaryPower()),
    }, mode_id="running")
    left, right = object(), object()
    result = switch.evaluate(left, right)
    assert result.native is running.result and result.mode_id == "running"
    assert result.cavitation_margin_m == 4. and result.boundary_power.total_w == 30.
    switch.set_mode("isolated")
    closed = switch.evaluate(left, right)
    assert closed.native is isolated.result and closed.mass_flow_kg_s == 0.
    assert closed.boundary_power.total_w == 0.
    assert running.calls == isolated.calls == [(left, right)]
    with pytest.raises(TypeError):
        switch.modes["other"] = switch.modes["running"]


def test_a_failed_mode_never_selects_a_different_physical_component():
    props = object()
    running = Device(props, ValueError("outside supplied map"))
    isolated = Device(props, SimpleNamespace(mass_flow_kg_s=0.))
    switch = Lh2dtModeSwitch(SimpleNamespace(native=props), {
        "running": Lh2dtEquipmentMode(running, lambda raw: BoundaryPower()),
        "isolated": Lh2dtEquipmentMode(isolated, lambda raw: BoundaryPower()),
    }, mode_id="running")
    with pytest.raises(ValueError, match="outside supplied map"):
        switch.evaluate(object(), object())
    assert switch.mode_id == "running" and not isolated.calls
    with pytest.raises(ValueError, match="Unknown"):
        switch.set_mode("automatic-fallback")
    assert switch.mode_id == "running"


def test_modes_require_consistent_properties_and_real_boundary_power_results():
    props = object()
    with pytest.raises(ValueError, match="property instance"):
        Lh2dtModeSwitch(SimpleNamespace(native=props), {
            "wrong": Lh2dtEquipmentMode(Device(object(), object()), lambda raw: BoundaryPower()),
        }, mode_id="wrong")
    switch = Lh2dtModeSwitch(SimpleNamespace(native=props), {
        "wrong-power": Lh2dtEquipmentMode(Device(props, object()), lambda raw: 0.),
    }, mode_id="wrong-power")
    with pytest.raises(TypeError, match="BoundaryPower"):
        switch.evaluate(object(), object())
