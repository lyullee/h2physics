import pytest

from h2physics.thermo import (
    CoolPropProperties,
    GasEnvelope,
    QualifiedGasTable,
    TableQualificationError,
)


def test_table_rejects_phase_change_envelope_before_building():
    reference = CoolPropProperties("Hydrogen")
    with pytest.raises(ValueError, match="critical"):
        QualifiedGasTable(reference, GasEnvelope(1e5, 1e6, 20, 300))


def test_released_table_qualifies_and_enforces_pt_ph_domain():
    reference = CoolPropProperties("Hydrogen")
    table = QualifiedGasTable(reference, GasEnvelope(1e5, 80e6, 250, 400), validation_points=40)
    assert table.qualification.error_gate_passed
    state = reference.state_pt(5e6, 317.3)
    assert table.state_ph(5e6, state.enthalpy_j_kg).temperature_k == pytest.approx(317.3, rel=.002)
    with pytest.raises(ValueError, match="envelope"):
        table.state_pt(1e8, 300)
    cold = reference.state_pt(5e6, 210)
    with pytest.raises(ValueError, match="envelope"):
        table.state_ph(5e6, cold.enthalpy_j_kg)


def test_dense_pt_ph_ps_gate_rejects_native_energy_inconsistency_on_reviewed_version():
    reference = CoolPropProperties("Hydrogen")
    if reference.version != "8.0.0":
        pytest.skip("The negative regression records the reviewed CoolProp 8.0.0 tables")
    with pytest.raises(TableQualificationError) as failure:
        QualifiedGasTable(reference, GasEnvelope(1e5, 90e6, 230, 400), validation_points=1000,
                          timing_repetitions=1)
    report = failure.value.report
    assert report.error_gate_passed
    assert report.maximum_relative_enthalpy_identity_error > 1e-7
    assert report.maximum_internal_energy_adjustment_j_kg == 0


def test_explicit_dependent_energy_policy_preserves_identity_and_eos_error_gate():
    reference = CoolPropProperties("Hydrogen")
    table = QualifiedGasTable(reference, GasEnvelope(1e5, 90e6, 230, 400), validation_points=1000,
                              timing_repetitions=1, internal_energy_policy="derive_from_h_p_rho")
    report = table.qualification
    assert report.qualification_passed
    assert report.maximum_internal_energy_adjustment_j_kg > 0
    assert report.maximum_relative_enthalpy_identity_error < 1e-14
    assert report.inverse_validation_point_count == 2000
