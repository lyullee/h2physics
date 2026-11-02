"""Actual reviewed SDToolbox/Cantera wave replay; no measured CJ validation."""

import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.detonation import (
    DetonationAuditError,
    DetonationEvidence,
    DetonationSettings,
    NativeSDToolbox,
    SDToolboxDetonation,
)
from h2physics.core import Origin

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ("src/h2physics/adapters/detonation.py", "tests/test_detonation.py",
          "scripts/check_detonation.py")


def fingerprints():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in INPUTS}


def native_provider():
    target = ROOT/"artifacts/native_detonation_packages"
    if not (target/"sdtoolbox/postshock.py").exists():
        raise RuntimeError("Install the reviewed official SDToolbox artifact in its isolated target")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    return NativeSDToolbox.from_installed()


def evidence():
    return DetonationEvidence("authored-wave-verification", "authored-homogeneous-initial-gas",
        "neutral-warm-gas-only", "authored-static-wave-reference", 100.,
        "stationary-upstream-laboratory", Origin.SYNTHETIC)


def hydrogen_initial(temperature=300., pressure=101325.):
    amounts = {"H2": 2., "O2": 1., "N2": 3.76}
    total = sum(amounts.values())
    return ReactiveState(temperature, pressure, {k: v/total for k, v in amounts.items()})


def _workspace(native_workspace):
    return (ROOT/"artifacts/detonation_workspace"/uuid4().hex
            if native_workspace is None else native_workspace)


def make_case(native=None, *, maximum_temperature=3400., maximum_pressure=5e6,
              native_workspace=None):
    import cantera as ct

    path = Path(ct.__file__).parent/"data/h2o2.yaml"
    text = path.read_text(encoding="utf-8")
    basis = MechanismBasis("installed-Cantera3.2-h2o2-thermochemistry",
        hashlib.sha256(path.read_bytes()).hexdigest(), "BSD-3-Clause",
        ("https://cantera.org/3.2/examples/input/h2o2.html",),
        300., maximum_temperature, 5e4, maximum_pressure)
    return SDToolboxDetonation(native or native_provider(), lambda: ct.Solution(yaml=text),
        basis, native_workspace=_workspace(native_workspace))


def argon_case(native=None, *, native_workspace=None):
    import cantera as ct

    species = ct.Species("AR", {"Ar": 1})
    species.thermo = ct.ConstantCp(200., 6000., 101325.,
                                 [300., 0., 0., 2.5*ct.gas_constant])
    phase = ct.Solution(thermo="ideal-gas", kinetics="none", species=[species])
    phase.name = "authored-native-monatomic-gas"
    basis = MechanismBasis("authored-native-constantCp-argon",
        hashlib.sha256(b"authored monatomic ideal-gas verification definition").hexdigest(),
        "authored-synthetic-input", ("https://www.grc.nasa.gov/www/k-12/airplane/normal.html",),
        250., 5500., 1e4, 2e6)
    return SDToolboxDetonation(native or native_provider(), lambda: phase, basis,
                              native_workspace=_workspace(native_workspace))


def replay():
    start = time.perf_counter()
    before = fingerprints()
    native = native_provider()
    model = make_case(native)
    initial = hydrogen_initial()
    source_state = model.source_phase.state.copy()
    cj = model.cj(initial, evidence=evidence())
    tight = model.cj(initial, evidence=evidence(), settings=DetonationSettings(
        native_jump_relative_tolerance=1e-10, sound_density_relative_step=1e-4,
        local_density_ratio_relative_step=5e-4))
    frozen = model.frozen_shock(initial, speed_m_s=cj.speed_m_s, evidence=evidence())
    elevated = model.cj(hydrogen_initial(350., 2e5), evidence=evidence())
    argon = argon_case(native)
    argon.source_phase.TPX = 300., 101325., "AR:1"
    analytic_errors = []
    for mach in (2., 3.):
        shock = argon.frozen_shock(ReactiveState(300., 101325., {"AR": 1.}),
            speed_m_s=mach*argon.source_phase.sound_speed, evidence=evidence(),
            settings=DetonationSettings(native_jump_relative_tolerance=1e-10))
        gamma = 5/3
        pressure = 1+2*gamma/(gamma+1)*(mach**2-1)
        density = (gamma+1)*mach**2/((gamma-1)*mach**2+2)
        analytic_errors.append(max(abs(shock.final.pressure_pa/101325./pressure-1),
            abs(shock.conservation.density_ratio/density-1),
            abs(shock.final.temperature_k/300./(pressure/density)-1)))
    domain_failure = None
    try:
        make_case(native, maximum_temperature=2800.).cj(initial, evidence=evidence())
    except DetonationAuditError as exc:
        domain_failure = exc
    gates = {
        "actual_native_phase_and_solver_results": cj.native_cj_result[0] is cj.native_cj_phase
            and frozen.native_solver_result is frozen.native_downstream,
        "private_source_state_unchanged": bool((source_state == model.source_phase.state).all()),
        "exact_bridge_thermochemistry": cj.native_bridge.source_thermo_sha256
            == cj.native_bridge.reloaded_thermo_sha256,
        "native_fit_and_local_minimum": cj.native_fit_r_squared >= .99999
            and all(v >= cj.speed_m_s for _, v in cj.local_density_speed_results),
        "momentum": abs(cj.conservation.momentum_residual_pa) < .1,
        "total_enthalpy_and_hugoniot": max(abs(cj.conservation.total_enthalpy_residual_j_kg),
            abs(cj.conservation.hugoniot_residual_j_kg)) < .01,
        "element_mass": cj.conservation.maximum_element_mass_fraction_residual < 1e-10,
        "entropy_compression": cj.conservation.entropy_increase_j_kg_k > 0
            and cj.conservation.density_ratio > 1,
        "independent_native_SV_sonic": cj.cj_sonic_relative_residual < 1e-4,
        "native_sound_crosscheck": cj.native_sound_relative_difference < 2e-4,
        "fixed_ratio_thermochemical_refinement": abs(tight.speed_m_s/cj.speed_m_s-1) < 1e-7,
        "isentropic_difference_refinement": abs(tight.independent_equilibrium_sound_m_s
            /cj.independent_equilibrium_sound_m_s-1) < 1e-7,
        "native_frozen_vs_equilibrium_distinct": frozen.final.temperature_k < cj.final.temperature_k
            and frozen.final.pressure_pa > cj.final.pressure_pa,
        "elevated_initial_native_case": elevated.final.pressure_pa > elevated.initial.pressure_pa,
        "independent_ideal_monatomic_limits": max(analytic_errors) < 1e-9,
        "domain_failure_retains_actual_state": domain_failure is not None
            and domain_failure.native_fit_result is not None
            and domain_failure.native_cj_result is not None
            and len(domain_failure.native_phases) >= 3
            and domain_failure.__cause__ is not None,
        "native_mechanism_files_removed": not any(model.workspace.glob("native-cj-*")),
        "input_bytes_unchanged": before == fingerprints(),
    }
    report = {"scope": "authored homogeneous warm-gas CJ and frozen shock verification only",
        "initial": {"temperature_k": initial.temperature_k, "pressure_pa_absolute": initial.pressure_pa,
                    "mole_fractions": dict(initial.mole_fractions)},
        "speed_m_s": cj.speed_m_s, "native_fitted_speed_m_s": cj.native_fitted_speed_m_s,
        "final_temperature_k": cj.final.temperature_k, "final_pressure_pa_absolute": cj.final.pressure_pa,
        "conservation": asdict(cj.conservation),
        "independent_equilibrium_sound_m_s": cj.independent_equilibrium_sound_m_s,
        "cj_sonic_relative_residual": cj.cj_sonic_relative_residual,
        "native_sound_relative_difference": cj.native_sound_relative_difference,
        "fixed_ratio_speed_refinement_m_s": tight.speed_m_s-cj.speed_m_s,
        "sound_refinement_m_s": tight.independent_equilibrium_sound_m_s-cj.independent_equilibrium_sound_m_s,
        "argon_analytic_relative_errors": analytic_errors,
        "domain_failure": str(domain_failure),
        "native_source_sha256_begin": native.source_sha256,
        "native_source_sha256_end": NativeSDToolbox.from_installed().source_sha256,
        "input_sha256_begin": before, "input_sha256_end": fingerprints(),
        "gates": {k: bool(v) for k, v in gates.items()},
        "elapsed_s": time.perf_counter()-start}
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    if not all(gates.values()):
        raise RuntimeError("Actual native detonation replay gate failed")
    return report


if __name__ == "__main__":
    replay()
