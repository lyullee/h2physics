"""Reproduce actual pinned compression, independent ideal limits and staging."""

import hashlib
import importlib
import importlib.metadata
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_compressor import (
    CompressionClosureError,
    CompressorEnvelope,
    Lh2dtCompressionTrain,
    Lh2dtCompressorStage,
    PrescribedIntercooling,
)
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "artifacts/native_packages"
PACKAGE_SHA256 = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"
HOST_FILES = (
    "src/h2physics/adapters/lh2dt_compressor.py",
    "tests/test_lh2dt_compressor.py",
    "scripts/check_compressor_integration.py",
)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_package_sha():
    digest = hashlib.sha256()
    for path in sorted((TARGET / "lh2dt").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def native_api():
    if native_package_sha() != PACKAGE_SHA256:
        raise RuntimeError("Install/review the pinned LH2DT source snapshot before this check")
    sys.path.insert(0, str(TARGET))
    module = importlib.import_module("lh2dt.compressor")
    properties = importlib.import_module("lh2dt.properties")
    if Path(module.__file__).resolve() != (TARGET / "lh2dt/compressor.py").resolve():
        raise RuntimeError("The imported native compressor is not the selected installed source")
    return module.Compressor, properties.ThermoState, properties.HydrogenProperties


def envelope():
    return CompressorEnvelope(1e4, 100e6, 80, 1800, 1e-5, 1.,
                               "authored-synthetic-envelope-not-equipment-qualification")


class IdealNativeProperties:
    """Authored verification-only ideal fixture, not a production EOS."""

    fluid = "authored-ideal-gas-verification"
    cp, gas_constant = 12000., 3500.

    def __init__(self, factory):
        self.factory = factory

    def from_pT(self, pressure, temperature):
        h = 2.3e6+self.cp*(temperature-300)
        s = 7000+self.cp*math.log(temperature/300)-self.gas_constant*math.log(pressure/1e5)
        return self.factory(pressure_Pa=pressure, temperature_K=temperature,
            density_kg_m3=pressure/(self.gas_constant*temperature),
            specific_enthalpy_J_kg=h, specific_internal_energy_J_kg=h-self.gas_constant*temperature,
            specific_entropy_J_kgK=s, quality=None, phase="gas")

    def from_ph(self, pressure, enthalpy):
        return self.from_pT(pressure, 300+(enthalpy-2.3e6)/self.cp)

    def from_ps(self, pressure, entropy):
        return self.from_pT(pressure, 300*math.exp((entropy-7000
            + self.gas_constant*math.log(pressure/1e5))/self.cp))


def make_stage(compressor, native_state, native_properties, *, ratio, efficiency, stage_id):
    reference = getattr(native_properties, "basis", None)
    reference_id = reference.reference_id if reference is not None else "authored-ideal-caloric-reference"
    bridge = Lh2dtProperties(native_properties, reference_id=reference_id)
    return Lh2dtCompressorStage(compressor(native_properties, pressure_ratio=ratio,
        isentropic_efficiency=efficiency), bridge, state_factory=native_state,
        stage_id=stage_id, envelope=envelope())


def ideal_checks(compressor, native_state, lines):
    properties = IdealNativeProperties(native_state)
    count = 0
    temperature_error = power_error = energy_error = 0.
    for ratio in (1.05, 2., 5.):
        for efficiency in (.6, .8, 1.):
            stage = make_stage(compressor, native_state, properties, ratio=ratio,
                               efficiency=efficiency, stage_id="ideal")
            for temperature in (250., 300., 600.):
                for flow in (.001, .02):
                    inlet = stage.bridge.state_pt(1e5, temperature)
                    result = stage.evaluate(inlet, flow)
                    ideal_t = temperature*ratio**(3500/12000)
                    expected_t = temperature+(ideal_t-temperature)/efficiency
                    expected_power = flow*12000*(ideal_t-temperature)/efficiency
                    temperature_error = max(temperature_error, abs(result.outlet.temperature_k/expected_t-1))
                    power_error = max(power_error, abs(result.power.shaft_work_w/expected_power-1))
                    energy_error = max(energy_error, abs(result.energy_residual_w))
                    count += 1
    if temperature_error > 1e-12 or power_error > 1e-12 or energy_error > 1e-7:
        raise AssertionError("Independent ideal-gas compression limit failed")
    lines += ["## Independent ideal-gas limit", "",
        "The actual installed native Compressor receives an authored test-only ideal "
        "property fixture with cp=12000 and R=3500 J/(kg K), h(300 K)=2.3e6 J/kg "
        "and s(300 K,100 kPa)=7000 J/(kg K). This synthetic gas is not a hydrogen "
        "property fit and is not exposed as a production provider. The independent "
        "oracle uses T2s=T1*ratio^(R/cp) and fluid work cp*(T2s-T1)/eta.", "",
        f"{count} actual native points: ratios 1.05/2/5, efficiencies 0.6/0.8/1, "
        "inlet temperatures 250/300/600 K and mass flows 0.001/0.02 kg/s.", "",
        "| Maximum diagnostic | Observed |", "|---|---:|",
        f"| Outlet T relative error | {temperature_error:.10g} |",
        f"| Shaft power relative error | {power_error:.10g} |",
        f"| Enthalpy/shaft residual W | {energy_error:.10g} |"]
    print(f"native compressor ideal limit: {count} points passed", flush=True)


def heos_checks(compressor, native_state, lines):
    import CoolProp.CoolProp as cp

    lines += ["", "## Actual HEOS stages", "",
        "Each pure-H2 spin identity has its own shared HEOS provider, native "
        "Lh2dtLowLevelProperties facade and actual native Compressor. Independent "
        "CoolProp high-level PS/PH queries check h2s, h2 and T2; they are the same "
        "EOS implementation through another interface, not an experimental EOS comparison.", "",
        "Grid per fluid: inlet pressures 0.1/1/20 MPa, temperatures 280/400 K, "
        "ratios 2/4 and efficiencies 0.65/0.85 at 0.02 kg/s.", "",
        "| Fluid / spin | Points | Max T relative difference | Max shaft relative difference | "
        "Max energy residual W | Exploratory 1e-5 W subgate |",
        "|---|---:|---:|---:|---:|---|"]
    metadata = []
    for fluid in ("Hydrogen", "ParaHydrogen", "OrthoHydrogen"):
        direct = CoolPropProperties(fluid)
        properties = Lh2dtLowLevelProperties(direct, state_factory=native_state)
        count = 0
        t_error = power_error = energy_error = 0.
        for ratio in (2., 4.):
            for efficiency in (.65, .85):
                stage = make_stage(compressor, native_state, properties, ratio=ratio,
                                   efficiency=efficiency, stage_id="HEOS-stage")
                for pressure in (1e5, 1e6, 20e6):
                    for temperature in (280., 400.):
                        inlet = direct.state_pt(pressure, temperature)
                        result = stage.evaluate(inlet, .02)
                        h2s = cp.PropsSI("Hmass", "P", pressure*ratio,
                                        "Smass", inlet.entropy_j_kg_k, fluid)
                        h2 = inlet.enthalpy_j_kg+(h2s-inlet.enthalpy_j_kg)/efficiency
                        t2 = cp.PropsSI("T", "P", pressure*ratio, "Hmass", h2, fluid)
                        shaft = .02*(h2-inlet.enthalpy_j_kg)
                        t_error = max(t_error, abs(result.outlet.temperature_k/t2-1))
                        power_error = max(power_error, abs(result.power.shaft_work_w/shaft-1))
                        energy_error = max(energy_error, abs(result.energy_residual_w))
                        if result.outlet.basis != direct.basis:
                            raise AssertionError("H2 spin/reference identity changed")
                        count += 1
        if t_error > 1e-9 or power_error > 1e-9 or energy_error > .05:
            raise AssertionError(f"HEOS native compression contract failed: {fluid}: "
                                 f"T relative={t_error:.12g}, shaft relative={power_error:.12g}, "
                                 f"energy residual={energy_error:.12g} W")
        lines.append(f"| {fluid} / {direct.basis.spin_composition} | {count} | "
                     f"{t_error:.10g} | {power_error:.10g} | {energy_error:.10g} | "
                     f"{'passes' if energy_error <= 1e-5 else 'fails; raw residual retained'} |")
        limits = stage.eos_limits
        metadata.append(f"| {fluid} | {limits.minimum_temperature_k:g} | "
                        f"{limits.maximum_temperature_k:g} | {limits.maximum_pressure_pa:g} |")
    lines += ["", "Native EOS metadata limits; accepted states also satisfy the caller envelope.", "",
              "| Fluid | Tmin K | Tmax K | pmax Pa |", "|---|---:|---:|---:|", *metadata]
    lines += ["", "The exploratory 1e-5 W energy subgate is retained independently from "
        "the existing common equipment 0.05 W absolute acceptance budget. The native "
        "PH flash's returned enthalpy is not replaced by its requested value and no "
        "energy-reference correction is applied. A subgate failure therefore remains "
        "visible even where the established common equipment contract passes."]
    print("native compressor HEOS: 72 pressure/temperature/efficiency points passed", flush=True)


def staged_checks(compressor, native_state, lines):
    lines += ["", "## Serial compression and prescribed cooling", "",
        "Three actual native stages each have ratio 3 and eta=0.8. The inlet is "
        "1 MPa, 300 K at 0.025 kg/s. The comparison returns each cooler outlet "
        "to a prescribed 300 K with zero pressure loss; the final aftercooler is "
        "included. These states are supplied thermal boundaries, not predicted "
        "UA/coolant performance. Both layouts end at 27 MPa.", "",
        "| Fluid | Layout | Shaft W | Heat into fluid W | Delivered T K | "
        "Total energy residual W |", "|---|---|---:|---:|---:|---:|"]
    for fluid in ("Hydrogen", "ParaHydrogen"):
        direct = CoolPropProperties(fluid)
        properties = Lh2dtLowLevelProperties(direct, state_factory=native_state)
        stages = tuple(make_stage(compressor, native_state, properties, ratio=3., efficiency=.8,
                                 stage_id=f"stage-{i}") for i in range(3))
        coolers = tuple(PrescribedIntercooling(f"cool-{i}", 300, 0,
                         "authored-prescribed-300K-boundary") for i in range(3))
        cases = (("adiabatic-serial", Lh2dtCompressionTrain(stages, train_id="adiabatic")),
                 ("prescribed-inter-and-aftercooling", Lh2dtCompressionTrain(stages,
                     intercoolers=coolers[:2], aftercooler=coolers[2], train_id="cooled")))
        powers = []
        for label, train in cases:
            result = train.evaluate(direct.state_pt(1e6, 300), .025)
            powers.append(result.power.shaft_work_w)
            if abs(result.energy_residual_w) > 1e-5:
                raise AssertionError("Staged compression total energy failed")
            if any(abs(t.energy_residual_w) > 1e-5 for t in result.transfers):
                raise AssertionError("A stage/cooler local enthalpy ledger failed")
            lines.append(f"| {fluid} | {label} | {result.power.shaft_work_w:.10g} | "
                f"{result.power.heat_w:.10g} | {result.outlet.temperature_k:.10g} | "
                f"{result.energy_residual_w:.10g} |")
        if powers[1] >= powers[0]:
            raise AssertionError("The selected synthetic intercooling case did not reduce shaft duty")
    print("actual native three-stage trains: HEOS duties and serial ledgers passed", flush=True)
    direct = CoolPropProperties("Hydrogen")
    properties = Lh2dtLowLevelProperties(direct, state_factory=native_state)
    stages = tuple(make_stage(compressor, native_state, properties, ratio=3., efficiency=efficiency,
        stage_id=f"loss-stage-{i}") for i, efficiency in enumerate((.8, .75, .7)))
    coolers = tuple(PrescribedIntercooling(f"loss-cool-{i}", temperature, loss,
        "authored-PT-and-pressure-loss-boundary") for i, (temperature, loss) in enumerate(
            ((300, 1e4), (305, 2e4), (310, 3e4))))
    result = Lh2dtCompressionTrain(stages, intercoolers=coolers[:2], aftercooler=coolers[2],
        train_id="prescribed-losses").evaluate(direct.state_pt(1e6, 300), .025)
    if abs(result.outlet.pressure_pa/26.82e6-1) > 1e-12 or abs(result.energy_residual_w) > 1e-5:
        raise AssertionError("Prescribed interstage pressure-loss composition failed")
    lines += ["", "A separate normal-H2 train uses efficiencies 0.8/0.75/0.7, prescribed "
        "cooler outlet temperatures 300/305/310 K and pressure losses 10/20/30 kPa. "
        f"It delivers {result.outlet.pressure_pa:.10g} Pa at {result.outlet.temperature_k:.10g} K; "
        f"shaft={result.power.shaft_work_w:.10g} W, heat={result.power.heat_w:.10g} W, "
        f"energy residual={result.energy_residual_w:.10g} W. Pressure losses are supplied "
        "boundary values, not a calculated exchanger resistance law."]


def guard_checks(compressor, native_state, lines):
    direct = CoolPropProperties("ParaHydrogen")
    properties = Lh2dtLowLevelProperties(direct, state_factory=native_state)
    stage = make_stage(compressor, native_state, properties, ratio=3, efficiency=.75, stage_id="guards")
    good = direct.state_pt(1e6, 300)
    cases = [
        ("reverse flow", lambda: stage.evaluate(good, -.01)),
        ("undeclared zero-flow compression", lambda: stage.evaluate(good, 0)),
        ("isolated nonzero flow", lambda: stage.evaluate(good, .01, mode="isolated")),
        ("liquid inlet", lambda: stage.evaluate(direct.state_pt(3e5, 20), .01)),
        ("wet inlet", lambda: stage.evaluate(direct.saturated(1e5, .99), .01)),
        ("saturated-vapor endpoint", lambda: stage.evaluate(direct.saturated(1e5, 1), .01)),
        ("liquidlike supercritical inlet", lambda: stage.evaluate(direct.state_pt(3e6, 25), .01)),
        ("wrong spin", lambda: stage.evaluate(replace(good,
            basis=replace(good.basis, spin_composition="normal")), .01)),
        ("wrong energy reference", lambda: stage.evaluate(replace(good,
            basis=replace(good.basis, reference_id="another-zero")), .01)),
    ]
    lines += ["", "## Domain/mode/reference rejection evidence", "",
        "| Attempt | Observed rejection |", "|---|---|"]
    for label, callback in cases:
        try:
            callback()
        except ValueError as error:
            lines.append(f"| {label} | {str(error)} |")
        else:
            raise AssertionError(f"Invalid native compression contract was accepted: {label}")
    isolated = stage.evaluate(good, 0, mode="isolated")
    if isolated.outlet is not None or isolated.power.total_w != 0 or isolated.native_result is not None:
        raise AssertionError("Isolation manufactured a transported/native compression state")
    stage.envelope = replace(envelope(), maximum_temperature_k=350)
    try:
        stage.evaluate(good, .01)
    except CompressionClosureError as error:
        lines += ["", "A native point outside the declared 350 K discharge limit is retained "
            f"and rejected: raw outlet T={error.native_result.outlet.temperature_K:.10g} K, "
            f"raw shaft={error.native_result.shaft_power_W:.10g} W. No property/model fallback occurs."]
    else:
        raise AssertionError("Out-of-envelope native point was accepted")
    print("phase, direction, identity, inactive and retained-native rejection checks passed", flush=True)


def timing_check(compressor, native_state, hydrogen_properties, lines):
    direct = CoolPropProperties("Hydrogen")
    low = Lh2dtLowLevelProperties(direct, state_factory=native_state)
    original = hydrogen_properties("Hydrogen")
    measurements, outputs = [], []
    for label, properties in (("shared-low-level-HEOS", low), ("native-high-level-HEOS", original)):
        bridge = Lh2dtProperties(properties, reference_id=direct.basis.reference_id)
        stage = Lh2dtCompressorStage(compressor(properties, pressure_ratio=3,
            isentropic_efficiency=.75), bridge, state_factory=native_state,
            stage_id="timed", envelope=envelope())
        inlet = direct.state_pt(5e6, 300)
        stage.evaluate(inlet, .02)
        start = time.perf_counter()
        for _ in range(12):
            result = stage.evaluate(inlet, .02)
        elapsed = (time.perf_counter()-start)/12
        measurements.append((label, elapsed))
        outputs.append(result)
    if not math.isclose(outputs[0].power.shaft_work_w, outputs[1].power.shaft_work_w, rel_tol=1e-10):
        raise AssertionError("Timing provider paths differ in shaft duty")
    lines += ["", "## Local timings", "",
        "Twelve repeated complete checked stage evaluations after one warmup. "
        "Each includes native stage execution, state/phase/reference checks, an independent "
        "PS audit and the common power ledger. These are local workload timings, not a "
        "general speed guarantee; concurrent jobs and platform affect them.", "",
        "| Path | Mean seconds/stage |", "|---|---:|"]
    lines += [f"| {label} | {elapsed:.10g} |" for label, elapsed in measurements]


def main():
    start = time.perf_counter()
    host_sha = {name: file_sha(ROOT / name) for name in HOST_FILES}
    compressor, native_state, hydrogen_properties = native_api()
    direct_url = json.loads((TARGET / "lh2dt_models-0.1.2.dist-info/direct_url.json").read_text())
    compressor_hash = hashlib.sha256((TARGET / "lh2dt/compressor.py").read_bytes()).hexdigest()
    license_hash = hashlib.sha256(
        (TARGET / "lh2dt_models-0.1.2.dist-info/licenses/LICENSE").read_bytes()).hexdigest()
    lines = ["# Native compressor and staged cooling verification", "",
        "This report contains synthetic thermodynamic and software checks. No compressor "
        "measurement or manufacturer map is fitted or validated.", "",
        f"LH2DT {importlib.metadata.version('lh2dt_models')}; "
        f"CoolProp {importlib.metadata.version('CoolProp')}. Native revision "
        "b2f276333c1b1793c39f25763703d196d36742ec.", "",
        "| Source fingerprint | SHA-256 |", "|---|---|",
        f"| Installed native Python package, ordered filename+bytes | {PACKAGE_SHA256} |",
        f"| Native compressor.py | {compressor_hash} |",
        f"| Installed native MIT license | {license_hash} |",
        f"| Installed archive receipt | {direct_url['archive_info']['hashes']['sha256']} |", ""]
    lines += ["Executed host source/test/script fingerprints, checked again before writing:", "",
              "| Host file | SHA-256 |", "|---|---|"]
    lines += [f"| {name} | {digest} |" for name, digest in host_sha.items()]
    lines.append("")
    ideal_checks(compressor, native_state, lines)
    heos_checks(compressor, native_state, lines)
    staged_checks(compressor, native_state, lines)
    guard_checks(compressor, native_state, lines)
    timing_check(compressor, native_state, hydrogen_properties, lines)
    lines += ["", "## Scope, rights and receiving gaps", "",
        "Actual native components, input/outlet/isentropic state objects, raw compressor "
        "results and prescribed-cooling native states remain available for deep Python "
        "coupling. Throughput is prescribed identically through the train, so zero steady "
        "mass residual is a declared no-leakage/no-inventory topology, not a measured "
        "prediction. Heat and shaft power are positive into the modeled fluid. "
        "Motor/electrical efficiency and utility/chiller power are outside the fluid ledger.", "",
        "A passed thermodynamic point has no native map admissibility evidence: momentum "
        "and operating_point_admissible remain unavailable. No shaft speed, capacity, "
        "surge/choke, reverse operation, bypass, check valve, leakage, startup, casing/rotor "
        "storage or motor dynamics are inferred. Explicit isolated zero flow is an "
        "ideal external isolation boundary, not a resolved machine coast-down.", "",
        "The installed Vaporizer only adds heat, while Reliquefier requires saturated "
        "states and is not a high-pressure gas intercooler. A native bidirectional gas "
        "heat-exchanger contract with coolant/UA/capacity/pressure-loss evidence is a "
        "receiving gap. Native compressor map/admissibility, network capacity closure "
        "and dynamic/isolation contracts are further receiving work. The host does not "
        "duplicate those missing equipment solvers.", "",
        "Primary sources: [native compressor at checked revision]"
        "(https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/compressor.py), "
        "[native MIT license](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE), "
        "[NASA isentropic relation](https://www.grc.nasa.gov/www/k-12/airplane/compexp.html), "
        "[CoolProp HEOS/API](https://coolprop.org/coolprop/LowLevelAPI.html), "
        "[hydrogen EOS reference](https://doi.org/10.1063/1.3160306). "
        "Native source and external data are not bundled; original fixtures and host "
        "integration code are authored here.", "",
        f"Elapsed local script time: {time.perf_counter()-start:.8g} s."]
    if (native_package_sha() != PACKAGE_SHA256
            or any(file_sha(ROOT / name) != digest for name, digest in host_sha.items())):
        raise RuntimeError("Native or host source/test/script bytes changed during replay; report not written")
    lines += ["", "Native and host source/test/script byte guards passed at run start and end."]
    (ROOT / "research/native_compression.md").write_text("\n".join(lines)+"\n", encoding="utf-8",
                                                        newline="\n")
    print("wrote research/native_compression.md", flush=True)


if __name__ == "__main__":
    main()
