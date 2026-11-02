"""Actual optional native compression, ideal limits and conserved staging."""

import importlib
import math
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_compressor import (
    CompressionClosureError,
    CompressorEnvelope,
    Lh2dtCompressionTrain,
    Lh2dtCompressorStage,
    PrescribedIntercooling,
)
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.core import PropertyBasis


def native_api():
    pytest.importorskip("CoolProp")
    target = Path(__file__).resolve().parents[1] / "artifacts/native_packages"
    if not (target / "lh2dt/compressor.py").is_file():
        pytest.skip("Separately installed optional LH2DT snapshot is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    module = importlib.import_module("lh2dt.compressor")
    assert Path(module.__file__).resolve() == (target / "lh2dt/compressor.py").resolve()
    return module.Compressor, importlib.import_module("lh2dt.properties").ThermoState


def envelope(**changes):
    result = CompressorEnvelope(1e4, 100e6, 80, 1800, 1e-5, 1.,
                                "authored-synthetic-envelope-not-manufacturer-data")
    return replace(result, **changes)


class IdealNativeProperties:
    """Test-only constant-cp caloric/EOS oracle, never a production provider."""

    fluid = "authored-ideal-gas-verification"
    cp, gas_constant = 12000., 3500.
    basis = PropertyBasis(fluid, "authored-h0=2300000-at-300K-s0=7000-at-100kPa", "not-applicable")

    def __init__(self, state_factory):
        self.state_factory = state_factory

    def from_pT(self, pressure, temperature):
        h = 2.3e6+self.cp*(temperature-300)
        s = 7000+self.cp*math.log(temperature/300)-self.gas_constant*math.log(pressure/1e5)
        return self.state_factory(pressure_Pa=pressure, temperature_K=temperature,
            density_kg_m3=pressure/(self.gas_constant*temperature),
            specific_enthalpy_J_kg=h, specific_internal_energy_J_kg=h-self.gas_constant*temperature,
            specific_entropy_J_kgK=s, quality=None, phase="gas")

    def from_ph(self, pressure, enthalpy):
        return self.from_pT(pressure, 300+(enthalpy-2.3e6)/self.cp)

    def from_ps(self, pressure, entropy):
        return self.from_pT(pressure, 300*math.exp((entropy-7000
            + self.gas_constant*math.log(pressure/1e5))/self.cp))


def ideal_stage(*, ratio=3., efficiency=.75, stage_id="ideal-stage"):
    compressor, native_state = native_api()
    native = IdealNativeProperties(native_state)
    bridge = Lh2dtProperties(native, reference_id=native.basis.reference_id)
    # The original Lh2dtProperties names an unknown synthetic fluid "unspecified";
    # use that same explicit fixture basis without asserting hydrogen spin data.
    native.basis = bridge.basis
    component = compressor(native, pressure_ratio=ratio, isentropic_efficiency=efficiency)
    stage = Lh2dtCompressorStage(component, bridge, state_factory=native_state,
                               stage_id=stage_id, envelope=envelope())
    return stage, bridge.state_pt(1e5, 300)


def heos_stages(*, ratios=(2.,), efficiencies=None, fluid="Hydrogen"):
    compressor, native_state = native_api()
    from h2physics.thermo import CoolPropProperties

    direct = CoolPropProperties(fluid)
    native = Lh2dtLowLevelProperties(direct, state_factory=native_state)
    bridge = Lh2dtProperties(native, reference_id=direct.basis.reference_id)
    efficiencies = efficiencies or (.75,)*len(ratios)
    stages = tuple(Lh2dtCompressorStage(
        compressor(native, pressure_ratio=ratio, isentropic_efficiency=efficiency),
        bridge, state_factory=native_state, stage_id=f"stage-{i}", envelope=envelope())
        for i, (ratio, efficiency) in enumerate(zip(ratios, efficiencies, strict=True)))
    return direct, stages


@pytest.mark.parametrize("ratio,efficiency", [(1.01, 1.), (2., .9), (5., .6)])
def test_actual_native_compressor_matches_independent_ideal_gas_limit(ratio, efficiency):
    stage, inlet = ideal_stage(ratio=ratio, efficiency=efficiency)
    flow = .03
    result = stage.evaluate(inlet, flow)
    cp, gas_constant = 12000., 3500.
    ideal_t = 300*ratio**(gas_constant/cp)
    expected_t = 300+(ideal_t-300)/efficiency
    expected_power = flow*cp*(ideal_t-300)/efficiency
    assert result.outlet.pressure_pa == pytest.approx(1e5*ratio, rel=1e-13)
    assert result.outlet.temperature_k == pytest.approx(expected_t, rel=1e-13)
    assert result.power.shaft_work_w == pytest.approx(expected_power, rel=1e-13)
    assert result.native_result.isentropic_power_W == pytest.approx(flow*cp*(ideal_t-300), rel=1e-13)
    assert result.power.heat_w == 0
    assert abs(result.energy_residual_w) < 1e-8
    assert result.transfer.momentum_residual_pa is None
    assert result.transfer.operating_point_admissible is None
    assert result.native_component is stage.native
    assert type(result.native_result).__module__ == "lh2dt.compressor"
    assert type(result.native_inlet).__module__ == "lh2dt.properties"
    assert type(result.native_isentropic_outlet).__module__ == "lh2dt.properties"


@pytest.mark.parametrize("fluid,spin", [("Hydrogen", "normal"), ("ParaHydrogen", "para"),
                                      ("OrthoHydrogen", "ortho")])
def test_actual_heos_compression_preserves_reference_spin_entropy_and_shaft_sign(fluid, spin):
    cp = pytest.importorskip("CoolProp.CoolProp")
    direct, (stage,) = heos_stages(fluid=fluid)
    inlet = direct.state_pt(2e6, 300)
    result = stage.evaluate(inlet, .02)
    ideal_h = cp.PropsSI("Hmass", "P", 4e6, "Smass", inlet.entropy_j_kg_k, fluid)
    expected_h = inlet.enthalpy_j_kg+(ideal_h-inlet.enthalpy_j_kg)/.75
    expected_t = cp.PropsSI("T", "P", 4e6, "Hmass", expected_h, fluid)
    assert result.outlet.temperature_k == pytest.approx(expected_t, rel=2e-11)
    assert result.outlet.enthalpy_j_kg == pytest.approx(expected_h, rel=2e-11)
    assert result.power.shaft_work_w == pytest.approx(.02*(expected_h-inlet.enthalpy_j_kg), rel=2e-11)
    assert result.outlet.entropy_j_kg_k > inlet.entropy_j_kg_k
    assert result.outlet.basis == direct.basis
    assert result.outlet.basis.spin_composition == spin
    assert abs(result.energy_residual_w) < 1e-6
    assert stage.eos_limits.maximum_temperature_k == 1000


def test_actual_native_stages_and_prescribed_intercooling_close_total_heos_duty():
    direct, stages = heos_stages(ratios=(3., 3., 3.), efficiencies=(.8, .75, .7))
    cooling = (PrescribedIntercooling("cool-1", 300, 1e4, "supplied-target-1"),
               PrescribedIntercooling("cool-2", 305, 2e4, "supplied-target-2"))
    after = PrescribedIntercooling("after", 310, 3e4, "supplied-aftercool-target")
    train = Lh2dtCompressionTrain(stages, intercoolers=cooling, aftercooler=after, train_id="three-stage")
    inlet = direct.state_pt(1e6, 300)
    result = train.evaluate(inlet, .025)
    assert len(result.stages) == len(result.intercooling) == 3
    expected_pressure = ((1e6*3-1e4)*3-2e4)*3-3e4
    assert result.outlet.pressure_pa == pytest.approx(expected_pressure, rel=1e-12)
    assert result.outlet.temperature_k == pytest.approx(310, rel=1e-12)
    assert result.power.shaft_work_w > 0
    assert result.power.heat_w < 0
    assert result.power.shaft_work_w == pytest.approx(sum(s.native_result.shaft_power_W for s in result.stages))
    independent_heat = sum(.025*(c.outlet.enthalpy_j_kg-c.inlet.enthalpy_j_kg) for c in result.intercooling)
    assert result.power.heat_w == pytest.approx(independent_heat, abs=1e-8)
    assert result.mass_residual_kg_s == 0
    assert abs(result.energy_residual_w) < 1e-6
    assert all(abs(t.energy_residual_w) < 1e-6 for t in result.transfers)
    assert result.native_components == tuple(stage.native for stage in stages)
    assert all(type(c.native_outlet).__module__ == "lh2dt.properties" for c in result.intercooling)
    for left, right in zip(result.transfers, result.transfers[1:]):
        assert left.right_node == right.left_node
        assert left.transmitted == right.upstream


def test_equal_ratio_ideal_stages_with_return_cooling_match_analytic_total_work():
    stage1, inlet = ideal_stage(ratio=3., efficiency=.8, stage_id="one")
    compressor, native_state = native_api()
    stage2 = Lh2dtCompressorStage(
        compressor(stage1.bridge.native, pressure_ratio=3., isentropic_efficiency=.8),
        stage1.bridge, state_factory=native_state, stage_id="two", envelope=envelope())
    cooler = PrescribedIntercooling("between", 300, 0, "ideal-prescribed-return-temperature")
    after = PrescribedIntercooling("after", 300, 0, "ideal-prescribed-return-temperature")
    train = Lh2dtCompressionTrain((stage1, stage2), intercoolers=(cooler,), aftercooler=after,
                                  train_id="analytic")
    result = train.evaluate(inlet, .03)
    work = 2*.03*12000*300*(3**(3500/12000)-1)/.8
    assert result.outlet.pressure_pa == pytest.approx(9e5)
    assert result.outlet.temperature_k == pytest.approx(300)
    assert result.power.shaft_work_w == pytest.approx(work, rel=1e-13)
    assert result.power.heat_w == pytest.approx(-work, rel=1e-13)
    assert abs(result.energy_residual_w) < 1e-8
    no_cooling = Lh2dtCompressionTrain((stage1, stage2), train_id="no-cooling").evaluate(inlet, .03)
    assert no_cooling.power.shaft_work_w > result.power.shaft_work_w


@pytest.mark.parametrize("flow,mode", [(0, "compressing"), (-.01, "compressing"),
                                     (.01, "isolated"), (True, "compressing"),
                                     (float("nan"), "compressing"), (.01, "stopped")])
def test_flow_direction_and_inactive_mode_are_not_inferred(flow, mode):
    stage, inlet = ideal_stage()
    with pytest.raises(ValueError):
        stage.evaluate(inlet, flow, mode=mode)


def test_ideal_isolation_has_no_fake_compressed_outlet_or_native_point():
    direct, stages = heos_stages(ratios=(3., 3.))
    train = Lh2dtCompressionTrain(stages, train_id="isolated-train")
    result = train.evaluate(direct.state_pt(1e6, 300), 0, mode="isolated")
    assert result.outlet is None
    assert result.power.total_w == result.energy_residual_w == 0
    assert all(stage.native_result is None and stage.outlet is None for stage in result.stages)
    assert all(t.upstream is None and t.transmitted is None for t in result.transfers)


def test_native_parameters_remain_replaceable_operating_point_inputs():
    stage, inlet = ideal_stage(efficiency=.8)
    first = stage.evaluate(inlet, .01)
    stage.native.isentropic_efficiency = .6
    second = stage.evaluate(inlet, .01)
    assert second.isentropic_efficiency == .6
    assert second.power.shaft_work_w/first.power.shaft_work_w == pytest.approx(.8/.6)
    stage.native.pressure_ratio = 1.
    with pytest.raises(ValueError, match="pressure ratio"):
        stage.evaluate(inlet, .01)


def test_liquid_wet_gas_liquidlike_supercritical_and_forged_inlets_are_rejected():
    direct, (stage,) = heos_stages(fluid="ParaHydrogen")
    for inlet in (direct.state_pt(3e5, 20), direct.saturated(1e5, .99),
                  direct.saturated(1e5, 1), direct.state_pt(3e6, 25)):
        with pytest.raises(ValueError, match="single gas"):
            stage.evaluate(inlet, .01)
    good = direct.state_pt(1e6, 300)
    with pytest.raises(ValueError, match="inconsistent"):
        stage.evaluate(replace(good, enthalpy_j_kg=good.enthalpy_j_kg+1e5), .01)
    with pytest.raises(ValueError, match="EOS metadata"):
        stage.evaluate(replace(good, temperature_k=1100), .01)
    for basis in (replace(good.basis, reference_id="different-zero"),
                  replace(good.basis, spin_composition="normal")):
        with pytest.raises(ValueError, match="bases differ"):
            stage.evaluate(replace(good, basis=basis), .01)


def test_declared_limits_and_failed_native_power_are_retained_without_fallback():
    stage, inlet = ideal_stage(ratio=5)
    stage.envelope = envelope(maximum_temperature_k=400)
    with pytest.raises(CompressionClosureError, match="envelope") as failure:
        stage.evaluate(inlet, .03)
    assert failure.value.native_result.outlet.temperature_K > 400
    stage.envelope = envelope()
    evaluate = stage.native.evaluate
    stage.native.evaluate = lambda *args: replace(evaluate(*args), shaft_power_W=1.)
    with pytest.raises(CompressionClosureError, match="balance") as failure:
        stage.evaluate(inlet, .03)
    assert failure.value.native_result.shaft_power_W == 1.


def test_property_ownership_reference_and_train_components_cannot_be_mislabeled():
    direct, (stage,) = heos_stages()
    _, (other,) = heos_stages()
    other.stage_id = "other-stage"
    with pytest.raises(ValueError, match="same native property"):
        Lh2dtCompressionTrain((stage, other), train_id="mismatched-properties")
    wrong = Lh2dtProperties(stage.bridge.native, reference_id="wrong-reference")
    with pytest.raises(ValueError, match="bases differ"):
        Lh2dtCompressorStage(stage.native, wrong, state_factory=stage.state_factory,
                             stage_id="mislabeled", envelope=envelope())
    stage.native.properties = SimpleNamespace(fluid="ParaHydrogen")
    with pytest.raises(ValueError, match="ownership changed"):
        stage.evaluate(direct.state_pt(1e6, 300), .01)


@pytest.mark.parametrize("cooling", [
    PrescribedIntercooling("hotter", 1000, 0, "authored-invalid"),
    PrescribedIntercooling("negative-pressure", 300, 100e6, "authored-invalid"),
    PrescribedIntercooling("condensed", 20, 0, "authored-invalid"),
])
def test_prescribed_cooling_cannot_heat_erase_pressure_or_enter_a_condensed_state(cooling):
    direct, stages = heos_stages()
    train = Lh2dtCompressionTrain(stages, aftercooler=cooling, train_id="invalid-cooling")
    with pytest.raises(ValueError):
        train.evaluate(direct.state_pt(1e6, 300), .01)
