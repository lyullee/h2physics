"""Execute pinned native terminal vents and retain failed hydraulic/UA cases."""

import argparse
import hashlib
import importlib
import importlib.metadata
import math
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.adapters.lh2dt_vent import Lh2dtVentStack, VentClosureError, VentEnvelope
from h2physics.hydraulics import HydraulicConvergenceError
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
REVISION = "b2f276333c1b1793c39f25763703d196d36742ec"
NATIVE_SHA = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"
HOST_FILES = ("src/h2physics/adapters/lh2dt_vent.py", "tests/test_lh2dt_vent.py",
    "scripts/check_vent_integration.py", "src/h2physics/adapters/lh2dt_hydraulics.py",
    "src/h2physics/hydraulics.py", "src/h2physics/adapters/lh2dt_properties.py",
    "src/h2physics/adapters/lh2dt.py", "src/h2physics/core.py", "src/h2physics/equipment.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_sha(target):
    digest = hashlib.sha256()
    for path in sorted((target / "lh2dt").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class IdealVerificationGas:
    """Authored caloric oracle input for actual native execution; not a production EOS."""

    fluid = "AuthoredIdealVerificationGas"
    cp, gas_constant, viscosity = 12_000., 3500., 1e-5

    def __init__(self, state_factory):
        self.state_factory = state_factory

    def from_pT(self, pressure, temperature):
        return self.state_factory(pressure_Pa=pressure, temperature_K=temperature,
            density_kg_m3=pressure / self.gas_constant / temperature,
            specific_enthalpy_J_kg=self.cp * temperature,
            specific_internal_energy_J_kg=(self.cp - self.gas_constant) * temperature,
            specific_entropy_J_kgK=self.cp * math.log(temperature) - self.gas_constant * math.log(pressure),
            quality=None, phase="gas")

    def from_ph(self, pressure, enthalpy):
        return self.from_pT(pressure, enthalpy / self.cp)

    def viscosity_Pa_s(self, _state):
        return self.viscosity

    def speed_of_sound_m_s(self, state):
        # Exact sound speed for this authored test gas only, never production estimation.
        return math.sqrt(self.cp / (self.cp - self.gas_constant) * self.gas_constant * state.temperature_K)


def build(modules, provider, bridge, *, ua, segments=64, reverse=False, dz=0.,
          shared=True, law=None, law_id=None, length=3., local_loss=1.2):
    vent, pipe, properties, friction = modules
    stack = vent.VentStack(length, .02, 2e-6, local_loss_coefficient=local_loss, elevation_change_m=dz,
        ambient_temperature_K=310., ambient_UA_W_K=ua, properties=provider,
        integration_segments=segments, allow_reverse=reverse)
    selected = (Lh2dtDarcyPipe(stack.pipe, bridge, viscosity_reader=stack.pipe._effective_viscosity,
        friction_law=law or friction.Churchill_1977,
        friction_law_id=law_id or "fluids direct Churchill_1977; declared single-gas closure",
        result_factory=pipe.PipeResult) if shared else None)
    if isinstance(provider, IdealVerificationGas):
        sound_reader = provider.speed_of_sound_m_s
        sound_id = "authored verification gas exact caloric sound speed"
    else:
        if not isinstance(provider, Lh2dtLowLevelProperties):
            raise TypeError("Declare a sound-speed capability for the selected actual provider")

        def sound_reader(state):
            return provider.provider.state_ph(state.pressure_Pa,
                state.specific_enthalpy_J_kg).speed_of_sound_m_s

        sound_id = f"same selected {provider.fluid} HEOS provider PH speed_of_sound_m_s"
    adapter = Lh2dtVentStack(stack, bridge, state_factory=properties.ThermoState,
        envelope=VentEnvelope(50_000., 500_000., 80., 600., .05, .5, .3,
            "authored low-pressure-difference dry-gas verification; no installed stack qualification"),
        component_id="authored-native-vent", evidence_id="authored 3m/.02m/K1.2/dz/UA/reservoir conditions",
        allow_reverse=reverse, viscosity_reader=stack.pipe._effective_viscosity,
        sound_speed_reader=sound_reader, sound_speed_capability_id=sound_id, hydraulic_pipe=selected)
    return adapter


def evaluate(adapter, left, right):
    return adapter.evaluate(left, right, left_node="upstream-vessel", right_node="remote-header",
        left_port_id="vent/base", right_port_id="vent/terminal")


def ideal_checks(modules):
    provider = IdealVerificationGas(modules[2].ThermoState)
    bridge = Lh2dtProperties(provider, reference_id="authored constant-cp ideal-gas thermal reference")
    left, right = bridge.state_pt(102_325., 270.), bridge.state_pt(101_325., 450.)
    def constant_f(_re, _ed):
        return .03
    adapter = build(modules, provider, bridge, ua=0., law=constant_f, law_id="authored Darcy f=.03")
    adapter.native.ambient_temperature_K = 310.
    base = evaluate(adapter, left, right)
    area = math.pi * .02**2 / 4.
    expected_flow = left.density_kg_m3 * area * math.sqrt(2. * 1000. / left.density_kg_m3 / (.03 * 3. / .02 + 1.2))
    flow_error = abs(base.transfer.mass_flow_kg_s / expected_flow - 1.)
    assert flow_error < 1e-12
    mass_cp = expected_flow * provider.cp
    rows = []
    for ntu in (0., .2, 1.):
        adapter = build(modules, provider, bridge, ua=ntu * mass_cp,
            law=constant_f, law_id="authored Darcy f=.03")
        result = evaluate(adapter, left, right)
        expected = 310. + (270. - 310.) * math.exp(-ntu)
        error = abs(result.outlet.temperature_k - expected)
        assert error < 1e-6 and abs(result.transfer.energy_residual_w) < 1e-7
        rows.append((ntu, result.outlet.temperature_k, expected, error,
                     result.power.heat_w, result.thermal_audit.residual_w_k))
    refinement = []
    for segments in (8, 16, 32, 64, 128):
        adapter = build(modules, provider, bridge, ua=8. * mass_cp, segments=segments,
            law=constant_f, law_id="authored Darcy f=.03")
        expected = 310. + (270. - 310.) * math.exp(-8.)
        try:
            result = evaluate(adapter, left, right)
        except VentClosureError as error:
            raw = error.native_result
            temperature = provider.from_ph(right.pressure_pa, raw.outlet_specific_enthalpy_J_kg).temperature_K
            refinement.append((segments, temperature, abs(temperature - expected), "rejected", str(error)))
        else:
            refinement.append((segments, result.outlet.temperature_k,
                abs(result.outlet.temperature_k - expected), "accepted", result.thermal_audit.residual_w_k))
    assert refinement[0][3] == "rejected" and refinement[-1][3] == "accepted"
    assert refinement[-1][2] < 1e-6
    clamped = build(modules, provider, bridge, ua=20. * mass_cp, segments=8,
        law=constant_f, law_id="authored Darcy f=.03")
    try:
        evaluate(clamped, left, right)
    except VentClosureError as error:
        clamp_message = str(error)
        clamp_temperature = provider.from_ph(right.pressure_pa,
            error.native_result.outlet_specific_enthalpy_J_kg).temperature_K
        assert clamp_temperature == 310. and "clamping" in clamp_message
    else:
        raise AssertionError("Native exact-ambient clamping was accepted as a resolved finite-UA outlet")
    clamp_reference = 310. + (270. - 310.) * math.exp(-20.)
    return rows, refinement, flow_error, clamp_temperature, clamp_reference, clamp_message


def heos_checks(modules):
    rows, negative = [], []
    for fluid, temperature, ambient in (("Hydrogen", 270., 310.), ("ParaHydrogen", 340., 295.)):
        direct = CoolPropProperties(fluid, quality_roundoff_tolerance=1e-8)
        provider = Lh2dtLowLevelProperties(direct, state_factory=modules[2].ThermoState)
        bridge = Lh2dtProperties(provider, reference_id=direct.basis.reference_id)
        left, right = bridge.state_pt(102_325., temperature), bridge.state_pt(101_325., 450.)
        for ua in (0., 5., 20.):
            adapter = build(modules, provider, bridge, ua=ua, dz=2.)
            adapter.native.ambient_temperature_K = ambient
            started = time.perf_counter()
            result = evaluate(adapter, left, right)
            assert abs(result.transfer.energy_residual_w) < .05
            assert abs(result.independent_momentum_residual_pa) < .01
            assert result.outlet.temperature_k != right.temperature_k
            assert adapter.native.pipe is adapter.original_pipe
            rows.append((fluid, ua, result.transfer.mass_flow_kg_s, result.outlet.temperature_k,
                result.power.heat_w, result.transfer.energy_residual_w,
                result.independent_momentum_residual_pa, result.thermal_audit.residual_w_k,
                result.potential_energy_change_j_kg, result.upstream_hydraulic_kinetic_energy_j_kg,
                result.upstream_mach_number, result.downstream_section_mach_number,
                time.perf_counter() - started))
        one_way = build(modules, provider, bridge, ua=5., dz=4.)
        equal = bridge.state_pt(101_325., temperature)
        blocked = evaluate(one_way, equal, equal)
        assert blocked.direction_blocked and blocked.transfer.mass_flow_kg_s == 0.
        assert blocked.transfer.momentum_residual_pa is None and blocked.outlet is None
        reverse = build(modules, provider, bridge, ua=5., reverse=True, dz=4.)
        try:
            evaluate(reverse, equal, equal)
        except VentClosureError as error:
            negative.append((fluid + " reverse gravity / 64 segments", str(error)))
        # A separately declared finer native case, with the same fixed audit budget.
        reverse_fine = build(modules, provider, bridge, ua=5., reverse=True, dz=4., segments=256)
        backward = evaluate(reverse_fine, equal, equal)
        assert backward.transfer.mass_flow_kg_s < 0.
        assert backward.power.heat_w == -backward.oriented_native_heat_w
        assert backward.power.heat_w > 0. if temperature < 310. else backward.power.heat_w < 0.
        downhill = build(modules, provider, bridge, ua=0., dz=-4.)
        downward = evaluate(downhill, bridge.state_pt(101_324., temperature), equal)
        assert downward.transfer.mass_flow_kg_s > 0.
        negative.append((fluid + " one-way gravity block", "0 kg/s; momentum unavailable; no outlet state"))
        rows.append((fluid + " reverse gravity / 256 segments", 5., backward.transfer.mass_flow_kg_s,
            backward.outlet.temperature_k, backward.power.heat_w, backward.transfer.energy_residual_w,
            backward.independent_momentum_residual_pa, backward.thermal_audit.residual_w_k,
            backward.potential_energy_change_j_kg, backward.upstream_hydraulic_kinetic_energy_j_kg,
            backward.upstream_mach_number, backward.downstream_section_mach_number, None))
        tiny_loss = build(modules, provider, bridge, ua=0., length=1e-8, local_loss=0.)
        try:
            evaluate(tiny_loss, left, right)
        except VentClosureError as error:
            assert "Mach" in str(error) and error.evaluation.upstream_mach_number > 1.
            negative.append((fluid + " tiny-loss / small-pressure-drop high velocity",
                f"{error}; raw upstream Mach {error.evaluation.upstream_mach_number:.12g}, "
                f"downstream same-bore Mach {error.evaluation.downstream_section_mach_number:.12g}"))
        else:
            raise AssertionError("Small pressure fraction incorrectly certified a supersonic Darcy point")
        cases = (
            ("wrong reference", replace(left, basis=replace(left.basis, reference_id="wrong")), right),
            ("inconsistent enthalpy", replace(left, enthalpy_j_kg=left.enthalpy_j_kg + 1e5), right),
            ("excess pressure ratio", bridge.state_pt(400_000., temperature), right),
            ("wet inlet", replace(left, phase="two_phase", vapor_mass_fraction=.5), right))
        for label, invalid_left, valid_right in cases:
            try:
                evaluate(one_way, invalid_left, valid_right)
            except ValueError as error:
                negative.append((fluid + " " + label, str(error)))
            else:
                raise AssertionError("Unsupported vent port/domain was accepted: " + label)
    return rows, negative


def transition_checks(modules):
    direct = CoolPropProperties("Hydrogen")
    provider = Lh2dtLowLevelProperties(direct, state_factory=modules[2].ThermoState)
    bridge = Lh2dtProperties(provider, reference_id=direct.basis.reference_id)
    native_adapter = build(modules, provider, bridge, ua=0., shared=False)
    right = bridge.state_pt(101_325., 300.)
    failures = []
    for drive in np.linspace(1., 100., 100):
        left = bridge.state_pt(101_325. + float(drive), 300.)
        try:
            evaluate(native_adapter, left, right)
        except VentClosureError as error:
            if "momentum" in str(error):
                failures.append((float(drive), left, error))
    if not failures:
        raise AssertionError("Re-review the retained native transition: no independently failing point found")
    drive, left, failed = max(failures, key=lambda row: abs(row[2].evaluation.independent_momentum_residual_pa))
    original = failed.evaluation
    continuous = build(modules, provider, bridge, ua=0.)
    accepted = evaluate(continuous, left, right)
    assert abs(accepted.independent_momentum_residual_pa) < .01
    gap_adapter = build(modules, provider, bridge, ua=0.,
        law=native_adapter.original_pipe._friction_factor,
        law_id="explicit original native piecewise laminar/Haaland friction")
    try:
        evaluate(gap_adapter, left, right)
    except HydraulicConvergenceError as error:
        gap_residual, gap_message = error.result.momentum_residual_pa, str(error)
    else:
        gap_residual, gap_message = None, "This selected driving point has an original-law root; native iteration still failed."
    return len(failures), drive, original, accepted, gap_residual, gap_message


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", type=Path, default=ROOT / "artifacts/native_packages")
    args = parser.parse_args()
    target = args.native_packages.resolve()
    if native_sha(target) != NATIVE_SHA:
        raise SystemExit("Install the exact LH2DT native revision documented in HANDOFF.md")
    begin = {name: sha(ROOT / name) for name in HOST_FILES}
    sys.path.insert(0, str(target))
    modules = (importlib.import_module("lh2dt.vent_stack"), importlib.import_module("lh2dt.pipe"),
        importlib.import_module("lh2dt.properties"), importlib.import_module("fluids.friction"))
    native_files = ("vent_stack.py", "pipe.py", "properties.py")
    external = {f"lh2dt/{name}": target / "lh2dt" / name for name in native_files}
    external["native MIT license"] = target / "lh2dt_models-0.1.2.dist-info/licenses/LICENSE"
    external["fluids.friction module"] = Path(modules[-1].__file__)
    external_begin = {name: sha(path) for name, path in external.items()}
    started = time.perf_counter()
    ideal = ideal_checks(modules)
    print("actual native ideal thermal/refinement checks completed", flush=True)
    heos, negative = heos_checks(modules)
    print("actual native HEOS heat/direction/domain checks completed", flush=True)
    transition = transition_checks(modules)
    elapsed = time.perf_counter() - started
    end = {name: sha(ROOT / name) for name in HOST_FILES}
    external_end = {name: sha(path) for name, path in external.items()}
    if begin != end or external_begin != external_end or native_sha(target) != NATIVE_SHA:
        raise RuntimeError("Executed source/dependency changed; report not finalized")
    ideal_rows, refinement, flow_error, clamp_t, clamp_ref, clamp_message = ideal
    count, drive, failed, accepted, gap_residual, gap_message = transition
    lines = ["# Native terminal vent verification", "",
        f"Completed UTC: {datetime.now(UTC).isoformat()}. Native LH2DT 0.1.2 MIT revision "
        f"`{REVISION}`; aggregate module SHA-256 `{NATIVE_SHA}`. Existing fluids "
        f"{importlib.metadata.version('fluids')} direct Churchill_1977 is an explicitly selected "
        "hydraulic closure, with its MIT dependency review already recorded in HYDRAULICS.md.", "",
        "All cases use authored geometry/UA/operating conditions and actual native VentStack, "
        "HEMPipe/PipeResult and ThermoState objects. Native code is not modified, and evaluation "
        "leaves the caller's configured input stack/property objects unchanged. It copies the native stack configuration and "
        "binds a recording proxy over the explicitly selected original pipe or existing shared "
        "Lh2dtDarcyPipe. The actual native finite-UA implementation still executes. No alternative "
        "pipe, EOS, nozzle or thermal solver is installed or silently selected.", "",
        "## Independent authored limits", "",
        "A test-only ideal gas supplies cp=12000 J/(kg K), R=3500 J/(kg K), mu=1e-5 Pa s, "
        "h=cp*T and matching entropy/U. It is not a measured hydrogen fit or production provider. "
        "The native stack is 3 m long, .02 m diameter, roughness 2e-6 m, K=1.2, zero elevation, "
        "left 102325 Pa/270 K, remote right 101325 Pa/450 K and ambient reservoir 310 K. "
        "The declared constant Darcy f=.03 limit has an independent closed flow expression. "
        f"Relative flow error {flow_error:.3g}. The independent caloric limit is "
        "Tout=Ta+(Tin-Ta)*exp(-UA/(abs(mdot)*cp)); numerical integration is owned by native LH2DT.", "",
        "| NTU | Native outlet K | Analytic outlet K | Absolute T error K | Physical heat W | Inverse-UA residual W/K |",
        "|---:|---:|---:|---:|---:|---|"]
    for ntu, temperature, expected, error, heat, residual in ideal_rows:
        lines.append(f"| {ntu} | {temperature:.12g} | {expected:.12g} | {error:.3g} | {heat:.12g} | {residual} |")
    lines += ["", "Native UA integration has internal/final enthalpy clamps. Enthalpy/heat "
        "bookkeeping alone can close despite an inaccurate ODE trajectory. The host therefore "
        "independently reconstructs UA by inverse quadrature using actual PH states along the "
        "native outlet enthalpy interval; it does not integrate a replacement forward solution. "
        "Configured-UA agreement requires max(1e-8 W/K, 1e-5*UA), including quadrature uncertainty. "
        "There is no automatic segment refinement or acceptance-budget relaxation.", "",
        "| NTU=8 native segments | Raw/accepted outlet K | Analytic T error K | Gate | Diagnostic |",
        "|---:|---:|---:|---|---|"]
    for segments, temperature, error, status, message in refinement:
        lines.append(f"| {segments} | {temperature:.12g} | {error:.3g} | {status} | {message} |")
    lines += ["", f"At NTU=20 / 8 native segments the raw outlet is exactly {clamp_t:.12g} K; "
        f"the authored analytic outlet is {clamp_ref:.15g} K. It is retained and rejected: "
        f"`{clamp_message}`. Exactly reaching the ambient endpoint is not silently accepted "
        "as evidence of finite-UA resolution. At an actual equal-temperature input, UA is "
        "unidentifiable from zero heat; this separate analytic limit remains available.", "",
        "## Actual HEOS stack cases", "",
        "Normal/para hydrogen use separate explicitly identified host HEOS providers, existing "
        "low-level native facades and matching state factories. These share the original EOS "
        "rather than claiming independent experimental property validation. Geometry is the same "
        "3 m/.02 m/roughness2e-6 m/K1.2; heating/cooling cases have elevation +2 m, pressures "
        "102325/101325 Pa and remote port T=450 K. Normal gas inlet/ambient are 270/310 K; "
        "para gas inlet/ambient are 340/295 K. Heat is finite-UA, not prescribed outlet T. "
        "The resolved transport outlet is a PH state at the actual downstream pressure; "
        "remote header temperature is not substituted for it.", "",
        "| Fluid / case | UA W/K | Signed flow kg/s | Resolved outlet K | Physical heat W | "
        "Enthalpy residual W | Independent momentum residual Pa | Inverse-UA residual W/K | "
        "g*dz J/kg | Upstream hydraulic v2/2 J/kg | Upstream Mach | Downstream section Mach | Runtime s |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|"]
    for fluid, ua, rate, temperature, heat, energy, momentum, thermal, potential, kinetic, mach_up, mach_down, timing in heos:
        lines.append(f"| {fluid} | {ua} | {rate:.12g} | {temperature:.12g} | {heat:.12g} | "
            f"{energy:.3g} | {momentum:.3g} | {thermal} | {potential:.12g} | {kinetic:.12g} | "
            f"{mach_up:.12g} | {mach_down:.12g} | {timing} |")
    lines += ["", "Native reverse-flow heat_into_fluid_W is left-to-right oriented. "
        "The original field remains available as oriented_native_heat_w; common BoundaryPower "
        "explicitly multiplies it by the actual flow direction so heat is positive into the "
        "transported fluid. Common ConnectionTransfer checks enthalpy using absolute throughput. "
        "At equal port pressures, +4 m elevation drives reverse gravity flow: one-way mode "
        "returns zero flow, unavailable momentum and no transported state; explicitly enabled "
        "reverse mode retains negative flow and its real upstream port. Reverse cases use a "
        "310 K ambient reservoir and 256 native segments; separately attempted 64-segment "
        "failures remain listed below under the unchanged UA audit budget. At -4 m elevation, "
        "forward flow is possible even with left pressure 1 Pa below the right pressure.", "",
        "Declared dry-gas verification bounds are 50-500 kPa, 80-600 K, pressure difference "
        "<=5% of maximum port pressure and outlet/upstream density change <=50%. These are "
        "authored numerical-domain assumptions, not construction/experimental applicability "
        "qualification. An additional explicit Mach<=0.3 gate checks upstream hydraulic "
        "velocity and a same-bore downstream pipe-section estimate against sound speed from "
        "the actual selected HEOS provider. Small pressure/density changes do not imply this "
        "gate. The authored ideal-gas sound relation is confined to the verification fixture; "
        "production requires an injected provider capability and rejects absent/nonfinite sound. "
        "Tiny-loss actual-native cases at the same approximately 1% pressure drop are retained "
        "and rejected for supersonic hydraulic velocity. The downstream estimate is not a "
        "resolved atmospheric plane or an assurance about every unmodeled interior station. "
        "The upstream-density hydraulic and downstream-pressure thermal "
        "approximations remain separate. Existing common budgets are .01 Pa momentum and "
        ".05 W / 1e-6 relative enthalpy power; the independent final Darcy/friction loss is "
        "reconstructed even when the original native result reports a zero residual.", "",
        "## Retained native transition and explicit correlation selection", "",
        f"A 100-point authored 1-100 Pa drive scan finds {count} original-native vent points "
        "failing the independent final momentum gate. The largest retained case has "
        f"drive {drive:.12g} Pa, native Re {failed.native_result.reynolds_number:.12g}, reported "
        f"momentum {failed.native_result.momentum_residual_Pa:.12g} Pa, while the independently "
        f"reconstructed residual is {failed.independent_momentum_residual_pa:.12g} Pa. "
        "Original flow/friction/raw stack and hydraulic results remain in the failed exception.", "",
        f"The explicitly selected existing shared Darcy root with direct Churchill_1977 gives "
        f"{accepted.transfer.mass_flow_kg_s:.12g} kg/s and residual "
        f"{accepted.independent_momentum_residual_pa:.3g} Pa at the same port states. "
        "This is a declared numerical/empirical closure selection, not a fallback or evidence "
        f"of improved measured transition accuracy. Using the original discontinuous native "
        f"friction law in the shared root gives residual {gap_residual}: `{gap_message}`.", "",
        "## Other negative gates", ""]
    lines += [f"- {label}: `{message}`." for label, message in negative]
    lines += ["", "## Boundary meaning and unfinished work", "",
        "This is a steady enthalpy-transport equipment boundary. Native stack hydraulics "
        "uses declared diameter/length/loss/elevation and upstream density/viscosity; "
        "its thermal ODE uses downstream pressure. Gravity direction is checked in the "
        "momentum equation, while port kinetic/potential energies remain excluded from the "
        "existing enthalpy-only ledger. Results explicitly report this energy_scope, signed "
        "g*dz and upstream constitutive hydraulic v2/2 diagnostics. These are not an outlet-plane "
        "velocity or a bound on its unresolved kinetic-energy change. Cases where elevation "
        "or velocity changes matter require a separately qualified mechanical-energy model; "
        "a small h/Q residual cannot certify them. No complete mechanical/total-energy source-plane "
        "closure, exit speed/momentum, critical discharge, stagnation-to-static conversion, "
        "atmospheric expansion, discharge coefficient, rainout or dispersion source is inferred. "
        "The native accident exporter is not used. A downstream low-pressure boundary does "
        "not make an unchoked Darcy result a qualified atmospheric nozzle history.", "",
        "Receiving work: expose public hydraulic-provider/phase-viscosity injection and "
        "native iteration diagnostics; expose UA integration error/clamp counts/refinement "
        "instead of accepting hidden endpoint clamps; give raw heat a documented direction "
        "basis; define compressible/critical and kinetic/potential-energy ownership at a "
        "separately qualified outlet plane. Do not introduce another copy of the shared "
        "Darcy/nozzle solver. Installed roughness, local-loss/UA values, phase applicability "
        "and measured vent performance remain unqualified.", "",
        "Primary implementation references: "
        f"[pinned native VentStack](https://github.com/lyullee/lh2dt_models/blob/{REVISION}/src/lh2dt/vent_stack.py), "
        f"[native pipe](https://github.com/lyullee/lh2dt_models/blob/{REVISION}/src/lh2dt/pipe.py), "
        f"[native MIT license](https://github.com/lyullee/lh2dt_models/blob/{REVISION}/LICENSE), "
        "[direct Churchill API and Darcy convention](https://fluids.readthedocs.io/fluids.friction.html#fluids.friction.Churchill_1977). "
        "No third-party code or experimental table was copied into this repository.", "",
        f"Completed local computation time: {elapsed:.9g} s. No measured/vendor/dispersion "
        "qualification, external writes/messages, source mutation, dependency installation or publication.", "",
        "## Begin/end executed-source fingerprints", "",
        "| Host source/test/script | Begin SHA-256 | End SHA-256 |", "|---|---|---|"]
    lines += [f"| {name} | `{digest}` | `{end[name]}` |" for name, digest in begin.items()]
    lines += ["", "| External dependency source | Begin SHA-256 | End SHA-256 |", "|---|---|---|"]
    lines += [f"| {name} | `{digest}` | `{external_end[name]}` |" for name, digest in external_begin.items()]
    lines += ["", f"Aggregate native module SHA-256 at begin and end: `{NATIVE_SHA}`."]
    (ROOT / "research/native_vent.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote research/native_vent.md; native source/thermal failures retained", flush=True)


if __name__ == "__main__":
    main()
