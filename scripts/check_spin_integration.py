"""Execute actual native spin functions and explicit enthalpy couplings."""

import hashlib
import importlib
import importlib.metadata
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from h2physics.adapters.lh2dt_spin import (
    Lh2dtOrthoPara,
    Lh2dtSpinCalorimeter,
    SpinCutoffError,
    SpinDomain,
    SpinEnthalpyReference,
    SpinEvidence,
)
from h2physics.core import Origin

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "artifacts/native_packages"
NATIVE_SHA = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"
HOST_FILES = ("src/h2physics/adapters/lh2dt_spin.py", "tests/test_lh2dt_spin.py",
              "scripts/check_spin_integration.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_sha():
    digest = hashlib.sha256()
    for path in sorted((TARGET / "lh2dt").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def model(native, *, rate=1e-5, gap=600000., cutoff=24):
    return Lh2dtOrthoPara(native, native.OrthoParaKineticsParameters(rate, gap, 85.4, cutoff),
        evidence=SpinEvidence("authored-constant-rate-no-catalyst-fit", "authored-constant-conversion-gap",
            "dilute-molecular-H2-rigid-rotor/reference-calorimeter",
            ("authored-synthetic-parameters", "https://doi.org/10.1051/0004-6361/201527209"),
            Origin.SYNTHETIC),
        domain=SpinDomain(1, 1000, 96, 1e-10, "authored-temperature-and-cutoff-envelope"))


def reference(offset=0.):
    return SpinEnthalpyReference(1., offset, "explicit-relative-spin-enthalpy-reference")


def calorimeter(kinetics, *, capacity=1000., offset=0., sensible_zero=0.):
    return Lh2dtSpinCalorimeter(kinetics, mass_kg=.01, pressure_pa=1000,
        pressure_evidence_id="held-dilute-gas-calorimeter-pressure",
        sensible_heat_capacity_j_k=capacity, sensible_evidence_id="authored-frozen-sensible-Cp",
        enthalpy_reference=reference(offset), reference_temperature_k=20,
        sensible_reference_enthalpy_j=sensible_zero)


def native_limits(native, lines):
    kinetics = model(native)
    low = kinetics.equilibrium(10)
    low_oracle = 1/(1+9*math.exp(-2*85.4/10))
    high = native.equilibrium_para_fraction(10000, rotational_temperature_K=85.4,
                                             maximum_rotational_level=96)
    if abs(low.para_fraction-low_oracle) > 2e-15 or abs(high-.25) > 2e-15:
        raise AssertionError("Independent low/high rotor-limit gate failed")
    lines += ["## Native rotor sums and independent limits", "",
        "The actual native module uses even-J spin weight 1 and odd-J weight 3. "
        "The independent low-T two-level oracle is x_para=1/[1+9*exp(-2*theta/T)]; "
        "the 9 combines J=1 rotational degeneracy 3 with nuclear-spin weight 3. "
        "The high-T statistical limit is 1/4. The 10000 K row is a mathematical "
        "rotor limit only, outside the adapter's declared 1–1000 K domain and "
        "without a molecular-gas/dissociation applicability claim.", "",
        "| Limit | Native para fraction | Independent absolute error |",
        "|---|---:|---:|",
        f"| 10 K, low-T two-level limit | {low.para_fraction:.14g} | {abs(low.para_fraction-low_oracle):.8g} |",
        f"| 10000 K, mathematical high-T / Jmax96 | {high:.14g} | {abs(high-.25):.8g} |", "",
        "| T K | Native Jmax24 | Native Jmax96 | Absolute difference |",
        "|---:|---:|---:|---:|"]
    for temperature in (10, 20, 50, 100, 300, 1000):
        point = kinetics.equilibrium(temperature)
        lines.append(f"| {temperature} | {point.para_fraction:.14g} | "
                     f"{point.reference_para_fraction:.14g} | {point.cutoff_difference:.8g} |")
    coarse = model(native, cutoff=1)
    try:
        coarse.equilibrium(300)
    except SpinCutoffError as error:
        lines += ["", f"Retained cutoff rejection: Jmax1 at300 K gives "
            f"{error.result.para_fraction:.14g}, larger-cutoff target "
            f"{error.result.reference_para_fraction:.14g}; difference="
            f"{error.result.cutoff_difference:.12g} exceeds the fixed1e-10 gate."]
    else:
        raise AssertionError("Insufficient native rotor cutoff was accepted")
    print("native rotor/even-odd limits and retained cutoff rejection passed", flush=True)


def thermostat_checks(native, lines):
    kinetics = model(native)
    times = np.array([10., 110., 10010., 100010., 1000010.])
    lines += ["", "## Exact native thermostat kinetics and heat", "",
        "Synthetic k=1e-5 s^-1 and conversion enthalpy q=600000 J/kg per unit para "
        "fraction increase; mass0.01 kg, held pressure1000 Pa. These inputs are authored "
        "verification parameters, not catalyst or calorimetric data. x is the native "
        "mass-independent population fraction; equal isomer molar masses make it "
        "numerically the model's mass fraction.", "",
        "A constant-pressure, constant-temperature thermostat keeps sensible H fixed. "
        "H_spin=M*[h_ref+q*(x_ref-x)]. Positive native conversion heat is an internal "
        "transfer. The required external thermostat heat is its negative, counted once. "
        "No frozen pure-fluid EOS zero participates in this ledger.", "",
        "| T K | Initial para | Final para | Final native heat W | External heat integral J | "
        "Max analytic fraction error | Max H-ledger residual J |",
        "|---:|---:|---:|---:|---:|---:|---:|"]
    for temperature, fraction in ((20., .25), (300., 1.)):
        trace = kinetics.thermostat(kinetics.state(fraction), temperature_k=temperature,
            mass_kg=.01, pressure_pa=1000, time_s=times, clock_id="absolute-thermostat",
            pressure_evidence_id="held-dilute-gas-reference", enthalpy_reference=reference())
        target = kinetics.equilibrium(temperature).para_fraction
        error = max(abs(s.native_state.para_fraction
            -(target+(fraction-target)*math.exp(-1e-5*(s.time_s-10)))) for s in trace.samples)
        residual = max(abs(s.enthalpy_balance_residual_j) for s in trace.samples)
        if error > 3e-15 or residual > 1e-9:
            raise AssertionError("Exact native thermostat kinetic/enthalpy gate failed")
        last = trace.samples[-1]
        lines.append(f"| {temperature:g} | {fraction:g} | {last.native_state.para_fraction:.14g} | "
            f"{last.conversion_heat_w:.12g} | {last.cumulative_external_heat_j:.12g} | "
            f"{error:.8g} | {residual:.8g} |")
    frozen = model(native, rate=0)
    state = frozen.state(.25)
    zero = frozen.rate(state, 20, .01)
    if zero.para_fraction_rate_s != 0 or zero.conversion_heat_w != 0:
        raise AssertionError("Frozen native rate/heat gate failed")
    final = frozen.advance(state, 20, 1e7)
    if final.para_fraction != .25:
        raise AssertionError("Frozen native composition changed")
    lines += ["", "The reverse 300 K para-to-ortho case has negative conversion heat "
        "and requires positive thermostat heat. k=0 gives frozen native composition/rate "
        "and zero heat over1e7 s without inferring a different catalyst. Exact native "
        "constant-T advances also pass sample refinement and continuation checks in tests."]
    print("native exact constant-T, frozen/reverse and thermostat enthalpy checks passed", flush=True)


def coupled_checks(native, lines):
    kinetics = model(native)
    lines += ["", "## Finite constant-pressure enthalpy calorimeter", "",
        "Mass0.01 kg, held pressure1000 Pa, effective frozen-composition sensible "
        "Cp=1000 J/K, initial T20 K and para fraction0.25. This is a finite lumped "
        "calorimeter, not a rigid vessel, liquid-mixture EOS or pressure/volume solver. "
        "Constant q is a caller-evidenced reduced enthalpy gap; Cp excludes conversion "
        "enthalpy. The adiabatic algebraic constraint is H_sensible+H_spin=constant. "
        "Native kinetics supplies dx/dt at the resulting T; SciPy integrates that "
        "coupling, without copying a native rotor/rate solver.", "",
        "| Maximum step s | rtol | Final para | Final T K | Max H residual J | RHS calls |",
        "|---:|---:|---:|---:|---:|---:|"]
    runs = []
    for step, tolerance in ((20000, 1e-8), (10000, 1e-10), (5000, 1e-12)):
        trace = calorimeter(kinetics).adiabatic(kinetics.state(.25), temperature_k=20,
            time_s=np.linspace(10, 2000010, 101), clock_id="absolute-calorimeter",
            maximum_time_step_s=step, relative_tolerance=tolerance, absolute_tolerance=1e-13)
        residual = max(abs(s.enthalpy_balance_residual_j) for s in trace.samples)
        if residual > 1e-9:
            raise AssertionError("Finite adiabatic spin enthalpy ledger failed")
        last = trace.samples[-1]
        lines.append(f"| {step} | {tolerance:g} | {last.native_state.para_fraction:.14g} | "
            f"{last.temperature_k:.14g} | {residual:.8g} | {trace.native_solver_result.nfev} |")
        runs.append(trace)
    root = brentq(lambda x: kinetics.equilibrium(20+6*(x-.25)).para_fraction-x, .25, 1.)
    equilibrium_error = abs(runs[-1].samples[-1].native_state.para_fraction-root)
    refinement = abs(runs[-1].samples[-1].temperature_k-runs[-2].samples[-1].temperature_k)
    if equilibrium_error > 3e-9 or refinement > 1e-7:
        raise AssertionError("Coupled equilibrium/refinement gate failed")
    base = calorimeter(kinetics).adiabatic(kinetics.state(1), temperature_k=300,
        time_s=np.linspace(100, 500100, 51), clock_id="reverse-adiabatic",
        maximum_time_step_s=5000, relative_tolerance=1e-11)
    shifted = calorimeter(kinetics, offset=2.3e7, sensible_zero=-8e5).adiabatic(
        kinetics.state(1), temperature_k=300, time_s=np.linspace(100, 500100, 51),
        clock_id="reverse-adiabatic", maximum_time_step_s=5000, relative_tolerance=1e-11)
    zero_difference = max(abs(a.temperature_k-b.temperature_k)
        for a, b in zip(base.samples, shifted.samples, strict=True))
    if zero_difference != 0:
        raise AssertionError("Arbitrary sensible/spin enthalpy-zero shift changed dynamics")
    zero_gap = model(native, gap=0)
    isothermal = calorimeter(zero_gap).adiabatic(zero_gap.state(.25), temperature_k=20,
        time_s=np.linspace(0, 5e5, 31), clock_id="zero-gap-reference", maximum_time_step_s=10000)
    target = zero_gap.equilibrium(20).para_fraction
    zero_gap_error = max(abs(s.native_state.para_fraction
        -(target+(.25-target)*math.exp(-1e-5*s.time_s))) for s in isothermal.samples)
    if zero_gap_error > 2e-10 or any(s.temperature_k != 20 for s in isothermal.samples):
        raise AssertionError("Zero-gap independent native kinetic reference failed")
    lines += ["", f"Independent final equilibrium root={root:.14g}; finite-time difference="
        f"{equilibrium_error:.12g}. Finest-two final T difference={refinement:.12g} K. "
        f"Zero-conversion-gap reference analytic error={zero_gap_error:.12g}. "
        f"Reverse adiabatic conversion cools to {base.samples[-1].temperature_k:.12g} K. "
        f"Shifting spin h_ref by2.3e7 J/kg and sensible H by-8e5 J changes T by "
        f"{zero_difference:g} K; compositions also remain identical."]
    print("finite constant-pressure spin enthalpy/reference/refinement checks passed", flush=True)


def negative_checks(native, lines):
    kinetics = model(native)
    calls = (
        ("Boolean native rotational cutoff", lambda: model(native, cutoff=True)),
        ("Negative native rate constructor", lambda: native.OrthoParaKineticsParameters(-1, 0)),
        ("Out-of-domain temperature", lambda: kinetics.equilibrium(1001)),
        ("Out-of-range fraction", lambda: kinetics.state(1.1)),
        ("Negative native advance duration", lambda: kinetics.advance(kinetics.state(.25), 20, -1)),
        ("Finite coupling exceeds declared T scope", lambda: calorimeter(kinetics, capacity=.01).adiabatic(
             kinetics.state(.25), temperature_k=20, time_s=[0, 1000], clock_id="rejected-T",
             maximum_time_step_s=1)),
    )
    lines += ["", "## Retained rejection evidence", "", "| Attempt | Rejection |", "|---|---|"]
    for label, callback in calls:
        try:
            callback()
        except ValueError as error:
            lines.append(f"| {label} | {' '.join(str(error).split())} |")
        else:
            raise AssertionError(f"Invalid spin scope accepted: {label}")
    tokens = ("para_fraction", "conversion_heat_rate_W", "OrthoParaState")
    inspected = ("tank.py", "stratified_tank.py", "layered_tank.py", "dynamic_network.py")
    coupled_files = [name for name in inspected if any(
        token in (TARGET/"lh2dt"/name).read_text("utf-8") for token in tokens)]
    if coupled_files:
        raise AssertionError("Reviewed native tank spin-coupling ownership changed")
    lines += ["", "Read-only inspection of the pinned homogeneous/stratified/layered "
        "tank and dynamic-network files finds no use of the native spin state/rate/heat "
        "symbols. The ortho_para module exports standalone functions; native tank spin "
        "coupling is not implemented at this revision. The new calorimeter is explicitly "
        "an enthalpy coupling, not a claimed native tank capability."]


def main():
    start = time.perf_counter()
    host_sha = {name: sha(ROOT/name) for name in HOST_FILES}
    if native_sha() != NATIVE_SHA:
        raise RuntimeError("Install/review the pinned LH2DT source snapshot")
    sys.path.insert(0, str(TARGET))
    native = importlib.import_module("lh2dt.ortho_para")
    if Path(native.__file__).resolve() != (TARGET/"lh2dt/ortho_para.py").resolve():
        raise RuntimeError("Imported native spin module differs from selected source")
    lines = ["# Native ortho/para conversion and enthalpy coupling", "",
        "Synthetic mathematical/native software checks; no catalyst, measured conversion "
        "rate, caloric mixture model or liquid-spin EOS is qualified.", "",
        f"LH2DT {importlib.metadata.version('lh2dt_models')}, pinned revision "
        "b2f276333c1b1793c39f25763703d196d36742ec; "
        f"SciPy {importlib.metadata.version('scipy')}.", "",
        "| Native source | SHA-256 |", "|---|---|",
        f"| Ordered top-level native filename+bytes | {NATIVE_SHA} |",
        f"| ortho_para.py | {sha(TARGET/'lh2dt/ortho_para.py')} |",
        f"| tank.py | {sha(TARGET/'lh2dt/tank.py')} |",
        f"| Installed MIT license | {sha(TARGET/'lh2dt_models-0.1.2.dist-info/licenses/LICENSE')} |",
        "", "Executed host source/test/script bytes:", "", "| File | SHA-256 |", "|---|---|"]
    lines += [f"| {name} | {digest} |" for name, digest in host_sha.items()]
    lines.append("")
    native_limits(native, lines)
    thermostat_checks(native, lines)
    coupled_checks(native, lines)
    negative_checks(native, lines)
    lines += ["", "## References, rights and limits", "",
        "Primary statistical/energy context: [Popovas and Jorgensen, molecular-H2 "
        "partition functions](https://doi.org/10.1051/0004-6361/201527209), "
        "[Leachman et al., separate para/normal/ortho EOS]"
        "(https://srd.nist.gov/jpcrdreprint/1.3160306.pdf), "
        "[pinned native API]"
        "(https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/ortho_para.py). "
        "The native source is separately installed under [MIT]"
        "(https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE); "
        "no third-party tables, coefficients, examples or implementation are copied.", "",
        "The native rigid rotor omits centrifugal distortion, vibrational/electronic "
        "excitation, dissociation and phase-dependent conversion thermochemistry. "
        "The first-order rate and constant enthalpy gap are explicit supplied closures. "
        "Sensible Cp must be frozen-composition storage and must not include conversion "
        "heat a second time. Held pressure defines a constant-pressure H/heat path; "
        "no rigid-volume U, density, volume, phase split or boundary-work prediction is "
        "returned. A delta-U coupling would need an explicit spin-dependent delta-PV "
        "assumption/provider. A no-mole-change ideal-gas delta-PV=0 limit cannot be "
        "promoted to a general liquid result.", "",
        "Actual native module/functions, parameters and composition states plus the "
        "actual SciPy coupled result remain available. Native exact-step endpoint "
        "roundoff clipping is retained; the host does not clip invalid fractions, infer "
        "a catalyst, relabel frozen CoolProp pure-fluid states, subtract arbitrary "
        "pure-fluid enthalpy zeros or silently select an evolving-spin EOS.", "",
        f"Elapsed local replay time: {time.perf_counter()-start:.8g} s."]
    if native_sha() != NATIVE_SHA or any(sha(ROOT/name) != digest for name, digest in host_sha.items()):
        raise RuntimeError("Native/host/test/script source changed during replay; report not written")
    lines += ["", "Native and host/test/script begin/end byte guards passed."]
    (ROOT/"research/native_spin.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    print("wrote research/native_spin.md", flush=True)


if __name__ == "__main__":
    main()
