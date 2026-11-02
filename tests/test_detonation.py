"""Actual native waves, independent ideal limits and explicit failure retention."""

import hashlib
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.detonation import (
    DetonationAuditError,
    DetonationEvidence,
    DetonationSettings,
    SDToolboxDetonation,
)
from h2physics.core import Origin
from scripts.check_detonation import (
    argon_case,
    evidence,
    hydrogen_initial,
    make_case,
    native_provider,
)


@pytest.fixture(scope="module")
def native():
    pytest.importorskip("cantera")
    if not (Path(__file__).resolve().parents[1]
            /"artifacts/native_detonation_packages/sdtoolbox/postshock.py").exists():
        pytest.skip("Reviewed separately installed official SDToolbox is optional")
    return native_provider()


@pytest.fixture(scope="module")
def wave(native):
    model = make_case(native)
    state = model.source_phase.state.copy()
    result = model.cj(hydrogen_initial(), evidence=evidence())
    return model, state, result


def test_optional_import_does_not_load_cantera_or_sdtoolbox():
    result = subprocess.run([sys.executable, "-X", "utf8", "-c",
        "import sys; import h2physics.adapters.detonation; "
        "assert 'cantera' not in sys.modules; assert 'sdtoolbox' not in sys.modules"],
        capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == 0, result.stderr


def test_explicit_evidence_and_settings():
    with pytest.raises(ValueError, match="Unresolved"):
        replace(evidence(), origin=Origin.UNRESOLVED)
    with pytest.raises(ValueError, match="clock"):
        replace(evidence(), clock_id="")
    with pytest.raises(ValueError, match="finite"):
        replace(evidence(), event_time_s=float("nan"))
    with pytest.raises(ValueError, match="lie"):
        DetonationSettings(sound_density_relative_step=0)
    with pytest.raises(ValueError, match="lie"):
        DetonationSettings(native_jump_relative_tolerance=.5)


def test_actual_native_objects_and_private_state(wave):
    model, state, result = wave
    assert result.native_provider is model.native
    assert result.source_phase is model.source_phase
    assert result.native_cj_result[0] is result.native_cj_phase
    assert result.native_upstream is not result.native_cj_phase
    assert result.native_sound_phase is not result.native_cj_phase
    assert all(p is not result.native_cj_phase for p in result.native_isentropic_phases)
    assert np.array_equal(model.source_phase.state, state)
    assert result.copy_audits
    assert not result.native_fit_internal_phases_available
    assert not result.native_fit_controls_exposed
    assert result.hydrogen_partition_id == "mechanism-H2-spin-unresolved"


def test_actual_exact_thermo_file_bridge_and_cleanup(wave):
    model, _, result = wave
    bridge = result.native_bridge
    assert bridge.source_thermo_sha256 == bridge.reloaded_thermo_sha256
    assert bridge.actual_reloaded_phase is not result.native_upstream
    assert len(bridge.yaml_sha256) == 64
    assert not bridge.kinetics_and_transport_used
    assert not any(model.workspace.glob("native-cj-*"))


def test_independent_wave_jump_energy_and_elements(wave):
    _, _, result = wave
    a, b, c = result.initial, result.final, result.conservation
    j = a.density_kg_m3*result.speed_m_s
    assert b.density_kg_m3*c.downstream_relative_velocity_m_s == pytest.approx(j, abs=1e-10)
    assert abs((b.pressure_pa-a.pressure_pa)-j*(result.speed_m_s
        -c.downstream_relative_velocity_m_s)) < .1
    assert abs(b.enthalpy_j_kg-a.enthalpy_j_kg+.5
        *(c.downstream_relative_velocity_m_s**2-result.speed_m_s**2)) < .01
    assert abs(b.internal_energy_j_kg-a.internal_energy_j_kg
        -.5*(a.pressure_pa+b.pressure_pa)*(1/a.density_kg_m3-1/b.density_kg_m3)) < .01
    assert c.maximum_element_mass_fraction_residual < 1e-10
    assert b.entropy_j_kg_k > a.entropy_j_kg_k
    assert result.final.mole_fractions["H2O"] > .2
    assert len(result.local_density_conservation) == 2
    assert all(abs(v.total_enthalpy_residual_j_kg) < .01 for v in result.local_density_conservation)


def test_cj_sonic_equilibrium_and_native_local_minimum(wave):
    _, _, result = wave
    assert result.cj_sonic_relative_residual < 1e-4
    assert result.native_sound_relative_difference < 2e-4
    assert result.frozen_sound_m_s > result.independent_equilibrium_sound_m_s
    assert result.native_fit_r_squared >= .99999
    assert all(v > result.speed_m_s for _, v in result.local_density_speed_results)
    assert len(result.native_isentropic_phases) == 2


def test_fixed_ratio_thermochemical_and_sonic_difference_refinement(wave):
    model, _, first = wave
    second = model.cj(hydrogen_initial(), evidence=evidence(), settings=DetonationSettings(
        native_jump_relative_tolerance=1e-10, sound_density_relative_step=1e-4,
        local_density_ratio_relative_step=5e-4))
    assert abs(second.speed_m_s-first.speed_m_s) < 1e-4
    assert abs(second.independent_equilibrium_sound_m_s-first.independent_equilibrium_sound_m_s) < 1e-3
    assert abs(second.conservation.total_enthalpy_residual_j_kg) < abs(
        first.conservation.total_enthalpy_residual_j_kg)
    assert second.native_density_ratio == first.native_density_ratio


@pytest.mark.parametrize("mach", [2., 3.])
def test_native_frozen_monatomic_shock_independent_analytic_limit(native, mach):
    model = argon_case(native)
    model.source_phase.TPX = 300., 101325., "AR:1"
    speed = mach*model.source_phase.sound_speed
    result = model.frozen_shock(ReactiveState(300., 101325., {"AR": 1.}),
        speed_m_s=speed, evidence=evidence(),
        settings=DetonationSettings(native_jump_relative_tolerance=1e-10))
    gamma = 5/3
    pressure_ratio = 1+2*gamma/(gamma+1)*(mach*mach-1)
    density_ratio = (gamma+1)*mach*mach/((gamma-1)*mach*mach+2)
    assert result.final.pressure_pa/result.initial.pressure_pa == pytest.approx(pressure_ratio, rel=1e-10)
    assert result.conservation.density_ratio == pytest.approx(density_ratio, rel=1e-10)
    assert result.final.temperature_k/300. == pytest.approx(pressure_ratio/density_ratio, rel=1e-10)
    assert result.native_solver_result is result.native_downstream
    assert result.final.mass_fractions == result.initial.mass_fractions


def test_frozen_reacting_mixture_is_distinct_from_equilibrium(wave):
    model, _, cj = wave
    frozen = model.frozen_shock(hydrogen_initial(), speed_m_s=cj.speed_m_s, evidence=evidence())
    assert frozen.final.mass_fractions == frozen.initial.mass_fractions
    assert frozen.final.temperature_k < cj.final.temperature_k
    assert frozen.final.pressure_pa > cj.final.pressure_pa
    assert abs(frozen.conservation.total_enthalpy_residual_j_kg) < .01


def test_elevated_initial_state_actual_native(native):
    result = make_case(native).cj(hydrogen_initial(350., 2e5), evidence=evidence())
    assert result.initial.temperature_k == pytest.approx(350.)
    assert result.final.pressure_pa > 2e5
    assert result.final.temperature_k > 2500.
    assert result.cj_sonic_relative_residual < 1e-4


def test_accepted_native_domain_failure_retains_completed_attempt(native):
    model = make_case(native, maximum_temperature=2800.)
    with pytest.raises(DetonationAuditError, match="Temperature") as caught:
        model.cj(hydrogen_initial(), evidence=evidence())
    error = caught.value
    assert isinstance(error.__cause__, ValueError)
    assert error.native_fit_result is not None
    assert error.native_cj_result[0] is error.native_phases[-1]
    assert error.native_phases[-1].T > 2800.
    assert error.bridge.actual_reloaded_phase in error.native_phases
    assert error.copy_audits
    assert error.diagnostics["native_fit_r_squared"] >= .99999
    assert not any(model.workspace.glob("native-cj-*"))


def test_actual_open_bridge_does_not_break_another_model_failure_cleanup(native):
    owner = make_case(native)
    other = make_case(native, maximum_temperature=2800.)
    argon = argon_case(native)
    assert len({owner.workspace, other.workspace, argon.workspace}) == 3
    phases, audits, diagnostics = [], [], {}
    upstream = owner._initial(hydrogen_initial(), phases, audits)
    with owner._mechanism_bridge(upstream, phases, diagnostics) as (filename, bridge):
        active = Path(filename)
        assert active.exists()
        assert bridge.source_thermo_sha256 == bridge.reloaded_thermo_sha256
        with pytest.raises(DetonationAuditError, match="Temperature") as caught:
            other.cj(hydrogen_initial(), evidence=evidence())
        assert caught.value.native_cj_result[0].T > 2800.
        assert not any(other.workspace.glob("native-cj-*"))
        assert active.exists()
        assert any(owner.workspace.glob("native-cj-*"))
    assert not active.exists()
    assert not any(owner.workspace.glob("native-cj-*"))


def test_basis_and_initial_domain_and_composition_are_not_invented(native):
    with pytest.raises(ValueError, match="actual native"):
        make_case(native, maximum_temperature=6000.)
    model = make_case(native)
    with pytest.raises(DetonationAuditError, match="Temperature"):
        model.cj(hydrogen_initial(20.), evidence=evidence())
    with pytest.raises(DetonationAuditError, match="H2/O2"):
        model.cj(ReactiveState(300., 101325., {"H2": .3, "N2": .7}), evidence=evidence())
    with pytest.raises(DetonationAuditError, match="lacks"):
        model.cj(ReactiveState(300., 101325., {"missing": 1.}), evidence=evidence())
    with pytest.raises(ValueError, match="sum"):
        ReactiveState(300., 101325., {"H2": 2., "O2": 1.})


def test_subsonic_and_reverse_shocks_rejected(native):
    model = argon_case(native)
    with pytest.raises(DetonationAuditError, match="above"):
        model.frozen_shock(ReactiveState(300., 101325., {"AR": 1.}),
            speed_m_s=100., evidence=evidence())
    with pytest.raises(ValueError, match="positive"):
        model.frozen_shock(ReactiveState(300., 101325., {"AR": 1.}),
            speed_m_s=-100., evidence=evidence())


def test_actual_thermo_definition_mutation_rejected(native):
    model = argon_case(native)
    species = model.source_phase.species(0)
    ct = model.ct
    species.thermo = ct.ConstantCp(200., 6000., 101325.,
                                 [300., 100., 0., 2.5*ct.gas_constant])
    model.source_phase.modify_species(0, species)
    with pytest.raises(DetonationAuditError, match="thermochemistry"):
        model.frozen_shock(ReactiveState(300., 101325., {"AR": 1.}),
            speed_m_s=700., evidence=evidence())


def test_actual_constant_cp_file_api_bound_loss_is_retained(native):
    import cantera as ct

    species = [ct.Species("H2", {"H": 2}), ct.Species("O2", {"O": 2})]
    for item in species:
        item.thermo = ct.ConstantCp(200., 6000., 101325.,
                                   [300., 0., 0., 3.5*ct.gas_constant])
    source = ct.Solution(thermo="ideal-gas", kinetics="none", species=species)
    basis = MechanismBasis("authored-file-bound-retention-test",
        hashlib.sha256(b"authored constant Cp bounds").hexdigest(), "authored-input",
        ("https://cantera.org/3.2/python/thermo.html",), 250., 5500., 1e4, 5e6)
    model = SDToolboxDetonation(native, lambda: source, basis,
                               native_workspace="artifacts/detonation_workspace")
    with pytest.raises(DetonationAuditError, match="preserve exact") as caught:
        model.cj(ReactiveState(300., 101325., {"H2": 2/3, "O2": 1/3}), evidence=evidence())
    error = caught.value
    assert error.native_fit_result is None
    assert error.bridge is not None
    assert error.bridge.actual_reloaded_phase is error.native_phases[-1]
    assert error.bridge.source_thermo_sha256 != error.bridge.reloaded_thermo_sha256
    assert error.bridge.actual_reloaded_phase.min_temp != source.min_temp
    assert error.__cause__ is not None


def test_native_yaml_bridge_requires_explicit_ascii_relative_workspace(native, tmp_path):
    model = make_case(native)
    with pytest.raises(ValueError, match="ASCII-relative"):
        SDToolboxDetonation(native, lambda: model.source_phase, model.basis, native_workspace=tmp_path)


def test_evidence_fields_preserved(wave):
    _, _, result = wave
    assert isinstance(result.evidence, DetonationEvidence)
    assert result.evidence.event_time_s == 100.
    assert result.evidence.clock_id == "authored-static-wave-reference"
    assert result.evidence.origin == Origin.SYNTHETIC
    with pytest.raises(TypeError):
        result.final.mole_fractions["H2"] = 0.


@pytest.mark.parametrize("method", ["cj", "frozen_shock"])
def test_actual_evidence_required_and_current_fields_validated(native, method):
    model = make_case(native)
    kwargs = {"speed_m_s": 1800.} if method == "frozen_shock" else {}
    call = getattr(model, method)
    with pytest.raises(DetonationAuditError, match="Actual DetonationEvidence") as absent:
        call(hydrogen_initial(), evidence=None, **kwargs)
    assert isinstance(absent.value.__cause__, TypeError)
    assert absent.value.native_phases == ()
    changed = evidence()
    object.__setattr__(changed, "clock_id", "")
    with pytest.raises(DetonationAuditError, match="clock") as invalid:
        call(hydrogen_initial(), evidence=changed, **kwargs)
    assert invalid.value.native_phases == ()
    assert invalid.value.native_fit_result is None
