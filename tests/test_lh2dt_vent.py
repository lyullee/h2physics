"""Authored interface doubles and independent constant-cp / constant-f limits."""

import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
from h2physics.adapters.lh2dt_vent import Lh2dtVentStack, VentClosureError, VentEnvelope
from h2physics.core import PropertyBasis


class IdealProperties:
    fluid = "AuthoredIdealGas"
    cp, gas_constant = 1000., 200.

    def from_pT(self, pressure, temperature):
        return SimpleNamespace(pressure_Pa=pressure, temperature_K=temperature,
            density_kg_m3=pressure / (self.gas_constant * temperature),
            specific_enthalpy_J_kg=self.cp * temperature,
            specific_internal_energy_J_kg=(self.cp - self.gas_constant) * temperature,
            specific_entropy_J_kgK=self.cp * math.log(temperature) - self.gas_constant * math.log(pressure),
            quality=None, phase="gas")

    def from_ph(self, pressure, enthalpy):
        return self.from_pT(pressure, enthalpy / self.cp)


class PipeDouble:
    length, diameter, roughness, local_k, heat, dz = 2., .01, 1e-6, 0., 0., 0.

    def __init__(self, properties):
        self.properties = properties

    def evaluate(self, left, right):
        forward = left.pressure_Pa >= right.pressure_Pa
        upstream, downstream = (left, right) if forward else (right, left)
        drive = upstream.pressure_Pa - downstream.pressure_Pa
        velocity = math.sqrt(2. * drive / upstream.density_kg_m3 / (.03 * self.length / self.diameter))
        flow = upstream.density_kg_m3 * math.pi * self.diameter**2 / 4. * velocity
        reynolds = upstream.density_kg_m3 * velocity * self.diameter / 1e-5
        return SimpleNamespace(mass_flow_kg_s=flow if forward else -flow,
            outlet_specific_enthalpy_J_kg=upstream.specific_enthalpy_J_kg,
            reynolds_number=reynolds, darcy_friction_factor=.03, heat_into_fluid_W=0.,
            upstream_side=("left" if forward else "right") if flow else None,
            pressure_drop_Pa=drive, momentum_residual_Pa=0.)


class StackDouble:
    ambient_temperature_K, ambient_UA_W_K = 300., .05
    bad_heat, bad_momentum, bad_pressure_drop, clamped = False, False, False, False

    def __init__(self, properties, allow_reverse=False):
        self.properties, self.allow_reverse = properties, allow_reverse
        self.pipe = PipeDouble(properties)

    def evaluate(self, left, right):
        hydraulic = self.pipe.evaluate(left, right)
        rate = hydraulic.mass_flow_kg_s
        if rate < 0. and not self.allow_reverse:
            return SimpleNamespace(mass_flow_kg_s=0., outlet_specific_enthalpy_J_kg=left.specific_enthalpy_J_kg,
                heat_into_fluid_W=0., reynolds_number=0., darcy_friction_factor=0., upstream_side=None,
                pressure_drop_Pa=left.pressure_Pa-right.pressure_Pa, momentum_residual_Pa=None)
        if rate == 0.:
            return hydraulic
        forward = rate > 0.
        upstream = left if forward else right
        outlet = self.ambient_temperature_K + (upstream.temperature_K - self.ambient_temperature_K) * math.exp(
            -self.ambient_UA_W_K / abs(rate) / self.properties.cp)
        if self.clamped:
            outlet = self.ambient_temperature_K
        enthalpy = self.properties.cp * outlet
        heat = abs(rate) * (enthalpy - upstream.specific_enthalpy_J_kg)
        return SimpleNamespace(mass_flow_kg_s=rate, outlet_specific_enthalpy_J_kg=enthalpy,
            heat_into_fluid_W=(heat if forward else -heat) + (1. if self.bad_heat else 0.),
            reynolds_number=hydraulic.reynolds_number,
            darcy_friction_factor=hydraulic.darcy_friction_factor * (2. if self.bad_momentum else 1.),
            upstream_side=hydraulic.upstream_side,
            pressure_drop_Pa=float("nan") if self.bad_pressure_drop else hydraulic.pressure_drop_Pa,
            momentum_residual_Pa=0.)


def case(*, reverse=False, shared=False):
    properties = IdealProperties()
    bridge = Lh2dtProperties(properties, reference_id="authored-ideal-reference")
    native = StackDouble(properties, reverse)
    envelope = VentEnvelope(50_000., 200_000., 200., 500., .05, .4, .3, "authored gas-only envelope")
    pipe = Lh2dtDarcyPipe(native.pipe, bridge, viscosity_reader=lambda _: 1e-5,
        friction_law=lambda _re, _rough: .03, friction_law_id="authored constant Darcy f=.03",
        result_factory=SimpleNamespace) if shared else None
    adapter = Lh2dtVentStack(native, bridge, state_factory=SimpleNamespace, envelope=envelope,
        component_id="authored-vent", evidence_id="authored geometry/UA",
        allow_reverse=reverse, viscosity_reader=lambda _: 1e-5,
        sound_speed_reader=lambda _: 400., sound_speed_capability_id="authored test-provider sound speed",
        hydraulic_pipe=pipe)
    return adapter, native, bridge


def evaluate(adapter, left, right):
    return adapter.evaluate(left, right, left_node="vessel", right_node="remote-header",
        left_port_id="vent/base", right_port_id="vent/terminal")


@pytest.mark.parametrize("shared", [False, True])
def test_native_objects_and_resolved_transport_outlet_are_preserved(shared):
    adapter, native, bridge = case(shared=shared)
    left, right = bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 450.)
    result = evaluate(adapter, left, right)
    assert native.pipe is adapter.original_pipe  # Per-evaluation selection did not mutate input.
    assert result.original_native_stack is native and result.native_stack is not native
    assert result.native_result is not None and result.hydraulic_result is not None
    assert result.outlet.pressure_pa == right.pressure_pa
    assert 280. < result.outlet.temperature_k < 300. and result.outlet.temperature_k != right.temperature_k
    assert result.transfer.upstream_node == "vessel" and result.transfer.downstream_node == "remote-header"
    assert result.power.heat_w > 0. and result.power.shaft_work_w == 0.
    assert abs(result.transfer.energy_residual_w) < 1e-10
    assert abs(result.independent_momentum_residual_pa) < 1e-10
    assert result.transfer.operating_point_admissible is None
    assert abs(result.thermal_audit.residual_w_k) < 1e-10
    assert result.potential_energy_change_j_kg == 0.
    assert result.upstream_hydraulic_kinetic_energy_j_kg > 0.
    assert "kinetic/potential" in result.energy_scope
    assert 0. < result.upstream_mach_number < .3 and result.downstream_section_mach_number < .3
    assert not hasattr(result, "source_plane")


@pytest.mark.parametrize("inlet_temperature", [280., 340.])
def test_reverse_native_heat_orientation_maps_explicitly_to_common_physical_heat(inlet_temperature):
    adapter, _native, bridge = case(reverse=True)
    result = evaluate(adapter, bridge.state_pt(101_325., 450.), bridge.state_pt(101_425., inlet_temperature))
    assert result.transfer.mass_flow_kg_s < 0.
    assert result.transfer.upstream_node == "remote-header"
    assert result.power.heat_w == -result.oriented_native_heat_w
    assert (result.power.heat_w > 0.) == (inlet_temperature < 300.)
    assert abs(result.transfer.energy_residual_w) < 1e-10


def test_one_way_block_and_static_zero_flow_do_not_fabricate_transport_or_momentum():
    adapter, _native, bridge = case()
    left, right = bridge.state_pt(101_325., 280.), bridge.state_pt(101_425., 300.)
    blocked = evaluate(adapter, left, right)
    assert blocked.direction_blocked and blocked.outlet is None
    assert blocked.transfer.mass_flow_kg_s == 0. and blocked.transfer.momentum_residual_pa is None
    assert blocked.transfer.upstream is None and blocked.power.heat_w == 0.
    static = evaluate(adapter, left, left)
    assert not static.direction_blocked and static.transfer.momentum_residual_pa == 0.


@pytest.mark.parametrize("fault", ["bad_heat", "bad_momentum", "bad_pressure_drop", "clamped"])
def test_retained_native_failures_cannot_become_accepted_boundaries(fault):
    adapter, native, bridge = case()
    setattr(native, fault, True)
    with pytest.raises(VentClosureError) as error:
        evaluate(adapter, bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 450.))
    assert error.value.native_result is not None and error.value.hydraulic_result is not None
    if fault == "clamped":
        assert "clamping" in str(error.value)
    if fault == "bad_momentum":
        assert "momentum" in str(error.value)


@pytest.mark.parametrize("fault", ["spin", "reference", "enthalpy", "phase", "pressure"])
def test_port_reference_eos_phase_and_approximation_gates(fault):
    adapter, _native, bridge = case()
    left, right = bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 450.)
    if fault == "spin":
        left = replace(left, basis=PropertyBasis("ParaHydrogen", left.basis.reference_id, "para"))
    elif fault == "reference":
        left = replace(left, basis=replace(left.basis, reference_id="other"))
    elif fault == "enthalpy":
        left = replace(left, enthalpy_j_kg=left.enthalpy_j_kg + 10.)
    elif fault == "phase":
        left = replace(left, phase="two_phase", vapor_mass_fraction=.5)
    else:
        left = bridge.state_pt(150_000., 280.)
    with pytest.raises(ValueError):
        evaluate(adapter, left, right)


def test_configuration_replacement_and_hidden_pipe_heat_are_rejected():
    adapter, native, bridge = case()
    left, right = bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 300.)
    native.pipe.heat = 1.
    with pytest.raises(ValueError, match="hidden heat"):
        evaluate(adapter, left, right)
    native.pipe.heat = 0.
    native.allow_reverse = True
    with pytest.raises(ValueError, match="changed"):
        evaluate(adapter, left, right)


@pytest.mark.parametrize("ua", [0., .05])
def test_adiabatic_and_equal_temperature_limits_do_not_invent_ua_information(ua):
    adapter, native, bridge = case()
    native.ambient_UA_W_K = ua
    result = evaluate(adapter, bridge.state_pt(101_425., 300.), bridge.state_pt(101_325., 450.))
    assert result.outlet.temperature_k == 300. and result.power.heat_w == 0.
    assert result.thermal_audit.reconstructed_ua_w_k is None


def test_explicit_density_approximation_envelope_is_enforced_after_native_execution():
    adapter, native, bridge = case()
    adapter.envelope = replace(adapter.envelope, maximum_density_change_fraction=.001)
    native.ambient_UA_W_K = .5
    with pytest.raises(VentClosureError, match="density change") as error:
        evaluate(adapter, bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 300.))
    assert error.value.evaluation.outlet is not None


def test_adiabatic_limit_does_not_consume_an_unused_ambient_property_state():
    adapter, native, bridge = case()
    native.ambient_UA_W_K = 0.
    native.ambient_temperature_K = 2.  # Outside the declared gas envelope, but unused at UA=0.
    result = evaluate(adapter, bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 300.))
    assert result.outlet.temperature_k == 280. and result.thermal_audit.status == "adiabatic"


def test_tiny_loss_high_velocity_is_rejected_despite_small_pressure_density_changes():
    adapter, native, bridge = case()
    native.pipe.length = 1e-8
    native.ambient_UA_W_K = 0.
    with pytest.raises(VentClosureError, match="Mach") as error:
        evaluate(adapter, bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 300.))
    result = error.value.evaluation
    assert result.upstream_mach_number > 1. and result.downstream_section_mach_number > 1.
    assert result.native_result is error.value.native_result


@pytest.mark.parametrize("value", [None, float("nan"), 0.])
def test_missing_or_invalid_sound_speed_does_not_imply_subsonic_applicability(value):
    adapter, native, bridge = case()
    adapter.sound_speed_reader = lambda _state: value
    native.ambient_UA_W_K = 0.
    with pytest.raises(VentClosureError) as error:
        evaluate(adapter, bridge.state_pt(101_425., 280.), bridge.state_pt(101_325., 300.))
    assert error.value.native_result is not None


def test_constructor_requires_an_actual_sound_speed_capability():
    adapter, native, bridge = case()
    with pytest.raises(TypeError, match="sound-speed"):
        Lh2dtVentStack(native, bridge, state_factory=SimpleNamespace, envelope=adapter.envelope,
            component_id="vent", evidence_id="authored", allow_reverse=False,
            viscosity_reader=lambda _: 1e-5, sound_speed_reader=None,
            sound_speed_capability_id="unavailable")
