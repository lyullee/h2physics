"""Actual native multibed scheduled execution, ledgers and honest object scope."""

import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.psa_cycle import (
    PsaCycleError,
    PsaCycleEvidence,
    PsaCycleNative,
    PsaDynaCycle,
)
from h2physics.adsorption import AdsorptionBasis, AdsorptionDomain
from h2physics.core import Origin

ROOT = Path(__file__).resolve().parents[1]


def bindings():
    target = ROOT/"artifacts/native_packages"
    if not (target/"psa_dynamic/runner.py").is_file():
        pytest.skip("Separately installed pinned PSA-Dyna is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    return PsaCycleNative.from_installed(source_id="PSA-Dyna:a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6")


def authored_case(*, cycles=2, step=.1, closed=False):
    material = {"name": "authored-warm-H2-N2", "end_fraction": 1.,
        "a1": [[.3], [.8]], "b0_per_bar": [[.02], [.08]],
        "binding_energy_j_mol": [[2000.], [3000.]], "ldf_per_s": [.2, .1]}
    return {"schema": "dynamic-psa-case/v1", "case_id": "authored-multibed-cycle",
        "species": [{"name": "H2", "mw_kg_mol": .00201588, "cp_j_mol_k": 29.},
                    {"name": "N2", "mw_kg_mol": .0280134, "cp_j_mol_k": 29.}],
        "bed": {"n_cells": 3, "diameter_m": .03, "length_m": .15,
            "void_fraction": .4, "particle_diameter_m": .002, "bulk_density_kg_m3": 500.,
            "solid_cp_j_kg_k": 700., "ambient_k": 300., "materials": [material],
            "wall_thickness_m": .003, "wall_density_kg_m3": 7800., "wall_cp_j_kg_k": 500.,
            "wall_k_w_m_k": 10., "bed_k_w_m_k": .25, "h_bed_wall_w_m2_k": 10.,
            "h_ambient_w_m2_k": 1., "wall_model": "dynamic_lumped",
            "energy_mode": "internal_energy", "kinetics": "loading_ldf"},
        "feed": {"mole_fractions": [.8, .2], "temperature_k": 300.,
                 "pressure_bar": 3., "molar_flow_mol_s": .001},
        "high_pressure_bar": 3., "low_pressure_bar": 1., "product_pressure_bar": 1.5,
        "initial_pressure_bar": 1.2, "initial_mole_fractions": [.8, .2],
        "purge_to_feed_ratio": .1, "purge_gain_mol_s_bar": .001,
        "valves": {name: {"gain_mol_s_bar": 0. if closed else .001}
                   for name in ("feed", "product", "tail", "equalization")},
        "schedule": {"name": "skarstrom_4step", "pressurization_s": 1., "adsorption_s": 2.},
        "solver": {"rtol": 1e-8, "max_step_s": step, "maximum_cycles": cycles,
            "minimum_cycles": 2, "css_tolerance": 1e-5, "css_consecutive_cycles": 2,
            "mass_balance_tolerance": 1e-7, "energy_balance_tolerance": 1e-7,
            "jacobian_method": "scipy_fd", "ledger_integration": "augmented",
            "negative_tolerance": 0., "record_trace": True, "trace_interval_s": .5,
            "maximum_step_wall_s": 30.},
        "provenance": {"origin": "authored-synthetic-not-an-adsorbent-fit"},
        "claim": "Authored warm native cycle and conservation check only"}


def basis():
    return AdsorptionBasis("authored-warm-H2-N2", ("H2", "N2"), "mol/kg-dry-solid:absolute",
        "PSA-Dyna:0.1.0:a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6", "authored-cycle-parameters",
        ("https://patents.google.com/patent/US2944627A/en",), loading_definition="absolute")


def adapter(parameters=None, **changes):
    kwargs = dict(basis=basis(), domain=AdsorptionDomain(290., 350., 5e5, 5e4),
        evidence=PsaCycleEvidence("authored-native-cycle",
            "native-gas-CvT0/stream-CpT0/solid-wall298.15K/negative-binding;H2-spin-unresolved",
            "authored-warm-ideal-gas-no-condensation", Origin.SYNTHETIC),
        temporary_workspace=ROOT/"artifacts")
    kwargs.update(changes)
    return PsaDynaCycle(bindings(), authored_case() if parameters is None else parameters, **kwargs)


@pytest.fixture(scope="module")
def completed():
    return adapter().run(start_time_s=100., clock_id="authored-operation-clock")


def test_actual_two_bed_four_slot_pressure_composition_cycle_and_native_identity(completed):
    assert len(completed.points) == 9
    assert completed.native_result["completed_cycles"] == 2
    assert completed.native_result["number_of_beds"] == 2
    assert completed.native_result["number_of_cycle_steps"] == 4
    assert completed.native_bindings.runner.run_case.__module__ == "psa_dynamic.runner"
    assert completed.audit_network.__class__ is completed.native_bindings.core.Network
    assert completed.bed_adapter.native_bed is completed.audit_network.bed
    pressure = np.array([[bed.pressure_pa.mean() for bed in p.beds] for p in completed.points])
    assert np.ptp(pressure[:, 0]) > 5e4 and np.ptp(pressure[:, 1]) > 5e4
    assert completed.final_cycle_totals.hydrogen_product_purity > .8
    assert not completed.original_integrator_objects_available
    assert not hasattr(completed, "native_solver_network")


def test_independent_species_inventory_and_signed_energy_ledgers_close_at_each_slot(completed):
    first = completed.points[0]
    for point in completed.points:
        np.testing.assert_allclose(point.inventory_mol-first.inventory_mol,
            point.feed_mol-point.product_mol-point.tail_mol, rtol=0, atol=1e-8)
        energy_change = point.feed_enthalpy_j-point.product_enthalpy_j-point.tail_enthalpy_j+point.ambient_heat_j
        assert abs(point.stored_energy_j-first.stored_energy_j-energy_change) < 1e-4
        assert np.max(abs(point.component_residual_mol)) < 1e-8
        assert abs(point.energy_residual_j) < 1e-4
        assert point.vacuum_work_j >= 0  # External utility estimate, not bed heat.


def test_only_actual_component_integrals_define_purity_and_startup_ratio(completed):
    last = completed.points[-1]
    totals = completed.totals
    assert totals.hydrogen_product_purity == pytest.approx(last.product_mol[0]/sum(last.product_mol))
    assert totals.hydrogen_product_to_feed_ratio == pytest.approx(last.product_mol[0]/last.feed_mol[0])
    assert totals.css_hydrogen_recovery is None
    assert completed.final_cycle_totals.css_hydrogen_recovery is None
    assert not completed.native_result["state_css_converged"]
    assert completed.native_result["dataset_release_gate"].startswith("closed_")
    assert completed.native_result["training_eligible"] is False


def test_native_cycle_slots_keep_actual_finite_state_and_absolute_clock(completed):
    elapsed = np.array([p.native_elapsed_s for p in completed.points])
    np.testing.assert_array_equal(elapsed, [0., 1., 3., 4., 6., 7., 9., 10., 12.])
    assert [p.time_s for p in completed.points] == list(elapsed+100.)
    assert completed.clock_id == "authored-operation-clock"
    assert completed.native_checkpoint_metadata["cycle_index"] == 2
    assert len(completed.native_call_results) == 10  # Native finalizes each cycle itself.
    for p in completed.points:
        assert not p.native_state.flags.writeable
        assert np.all(p.inventory_mol > 0)
        assert all(b.energy_reference_id == completed.evidence.energy_reference_id for b in p.beds)


def test_closed_native_valves_recover_stationary_multibed_equilibrium_and_undefined_purity():
    result = adapter(authored_case(cycles=1, closed=True)).run(start_time_s=500., clock_id="closed-clock")
    for p in result.points:
        np.testing.assert_allclose(p.native_state, result.points[0].native_state, rtol=0, atol=1e-9)
    assert result.totals.hydrogen_product_purity is None
    assert result.totals.hydrogen_product_to_feed_ratio is None
    assert result.totals.css_hydrogen_recovery is None
    assert np.all(result.totals.feed_mol == 0.) and np.all(result.totals.product_mol == 0.)


def test_native_maximum_step_refinement_preserves_cycle_exports_and_pressures(completed):
    parameters = authored_case(step=.05)
    parameters["solver"]["rtol"] = 2e-9
    fine = adapter(parameters).run(start_time_s=100., clock_id="authored-operation-clock")
    np.testing.assert_allclose(fine.totals.product_mol, completed.totals.product_mol, rtol=1e-5)
    assert abs(fine.final_cycle_totals.hydrogen_product_purity-completed.final_cycle_totals.hydrogen_product_purity) < 1e-6
    for left, right in zip(fine.points[-1].beds, completed.points[-1].beds, strict=True):
        np.testing.assert_allclose(left.pressure_pa, right.pressure_pa, rtol=1e-5)


def test_owned_case_and_native_state_snapshots_are_not_mutable_aliases():
    parameters = authored_case(cycles=1)
    model = adapter(parameters)
    parameters["feed"]["mole_fractions"][0] = .1
    copied = model.case_parameters()
    copied["species"][0]["name"] = "invented"
    assert model.case_parameters()["feed"]["mole_fractions"] == [.8, .2]
    assert model.case_parameters()["species"][0]["name"] == "H2"
    model.audit_network.case["feed"]["temperature_k"] = 320.
    with pytest.raises(ValueError, match="definition changed"):
        model.run(start_time_s=0., clock_id="owned-identity")


@pytest.mark.parametrize("change", ["source_sensible", "partial_pressure_ldf", "peng_robinson"])
def test_unchecked_energy_loading_or_gas_modes_are_not_silently_renamed(change):
    parameters = authored_case()
    key = {"source_sensible": "energy_mode", "partial_pressure_ldf": "kinetics", "peng_robinson": "equation_of_state"}[change]
    parameters["bed"][key] = change
    with pytest.raises(ValueError):
        adapter(parameters)


def test_species_amount_phase_domain_and_solver_admission_are_explicit():
    with pytest.raises(ValueError, match="species order"):
        adapter(basis=replace(basis(), species=("N2", "H2")))
    with pytest.raises(ValueError, match="absolute-uptake"):
        adapter(basis=replace(basis(), loading_definition="surface_excess"))
    with pytest.raises(ValueError, match="warm domain"):
        adapter(domain=AdsorptionDomain(20., 350., 5e5))
    parameters = authored_case()
    parameters["solver"]["ledger_integration"] = "quadrature"
    with pytest.raises(ValueError, match="augmented"):
        adapter(parameters)
    parameters = authored_case()
    parameters["solver"].pop("negative_tolerance")
    with pytest.raises(ValueError, match="positivity"):
        adapter(parameters)
    with pytest.raises(ValueError, match="Unresolved"):
        PsaCycleEvidence("source", "energy", "phase", Origin.UNRESOLVED)


def test_post_native_domain_failure_retains_real_checkpoint_state_and_audited_prefix():
    model = adapter(domain=AdsorptionDomain(299.99, 300.01, 5e5, 5e4))
    with pytest.raises(PsaCycleError) as error:
        model.run(start_time_s=100., clock_id="narrow-domain")
    failure = error.value
    assert failure.native_result is not None
    assert failure.native_state is not None and not failure.native_state.flags.writeable
    assert failure.native_checkpoint_metadata["slot_index"] >= 1
    assert len(failure.audited_points) >= 1
    assert failure.audit_network is model.audit_network
    assert failure.__cause__ is not None


def test_clock_and_unsupported_single_bed_are_rejected():
    with pytest.raises(ValueError, match="clock"):
        adapter().run(start_time_s=0., clock_id="")
    parameters = deepcopy(authored_case())
    parameters["schedule"] = {"name": "closed", "duration_s": 2.}
    with pytest.raises(ValueError, match="multibed"):
        adapter(parameters)


def test_native_runner_failure_record_survives_managed_workspace_cleanup():
    parameters = authored_case(cycles=1)
    parameters["solver"]["jacobian_method"] = "unsupported-authored-negative-case"
    model = adapter(parameters)
    with pytest.raises(PsaCycleError, match="Unknown Jacobian") as error:
        model.run(start_time_s=100., clock_id="native-failure-clock")
    assert error.value.native_failure_record["error_type"] == "ValueError"
    assert error.value.native_failure_record["training_eligible"] is False
    assert error.value.native_failure_record["checkpoint_available"] is False
    assert error.value.audit_network is model.audit_network
    assert error.value.__cause__ is not None


def test_finite_cycle_controls_native_heat_capacity_and_timing_are_not_coerced():
    parameters = authored_case()
    parameters["solver"]["maximum_cycles"] = 1.5
    with pytest.raises(ValueError, match="positive integers"):
        adapter(parameters)
    parameters = authored_case()
    parameters["species"][0]["cp_j_mol_k"] = 1.
    with pytest.raises(ValueError, match="caloric"):
        adapter(parameters)
    parameters = authored_case()
    parameters["schedule"]["slot_s"] = 200.
    with pytest.raises(ValueError, match="timing"):
        adapter(parameters)


def test_hydrogen_metric_interface_rejects_native_css_reporting_another_species():
    parameters = authored_case()
    parameters["reporting_species"] = "N2"
    with pytest.raises(ValueError, match="reporting_species='H2'"):
        adapter(parameters)
