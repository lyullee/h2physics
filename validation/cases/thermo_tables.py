"""Deferred reference-EOS table qualification and freshness contract.

Import and cases() construct metadata only. Native table construction, property
calls and timing occur solely in the explicitly invoked cluster entrypoint.
"""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="thermo-gas-envelope-input-guard", profile="gas-composition",
        entrypoint=__name__+":validate_envelope_inputs", parameters={}, invariants=(
            "direct envelope queries reject boolean, nonfinite and nonpositive PT inputs",
            "inclusive declared pressure/temperature endpoints remain admitted",
            "malformed CoolProp constructor options fail before importing the optional provider",
        )), ValidationCase(
        identifier="thermo-table-eos-domain-freshness", profile="gas-composition",
        entrypoint=__name__+":validate_contract", parameters={}, invariants=(
            "released tabular PT/PH/PS backend qualifies against direct HEOS within explicit gas envelope",
            "explicit dependent-energy policy retains adjustment and identity diagnostics",
            "independent off-sample states satisfy declared EOS property budgets",
            "out-of-envelope PT/PH/PS pressure and cold phase envelope rejected",
            "post-qualification configuration and nested envelope changes rejected",
            "replaced native CoolProp state object invalidates the qualification binding",
            "TableQualification can only be issued by a completed QualifiedGasTable evaluation",
            "direct construction and dataclass replacement cannot forge or clone a passing report",
            "TableQualificationError retains only the issued report type",
            "the measured timing is compared against an explicit caller speedup target",
            "invalid performance targets are rejected without changing EOS qualification")),)


def validate_envelope_inputs(*, work_directory, **parameters):
    from h2physics.thermo import CoolPropProperties, GasEnvelope

    del work_directory, parameters
    envelope = GasEnvelope(1e5, 1e6, 200., 400.)
    envelope.require_pt(1e5, 200.)
    envelope.require_pt(1e6, 400.)
    rejected = 0
    for pressure, temperature in (
        (True, 300.), (1e5, False), (float("nan"), 300.),
        (1e5, float("inf")), (0., 300.), (1e5, -1.),
    ):
        try:
            envelope.require_pt(pressure, temperature)
        except ValueError:
            rejected += 1
    assert rejected == 6
    constructor_rejections = 0
    for options in (
        {"fluid": ""}, {"backend": []}, {"internal_energy_policy": None},
        {"quality_roundoff_tolerance": True},
    ):
        try:
            CoolPropProperties(**options)
        except (TypeError, ValueError):
            constructor_rejections += 1
        else:
            raise AssertionError("Malformed CoolProp configuration passed constructor admission")
    assert constructor_rejections == 4
    return ValidationOutcome(True, {
        "inclusive_boundaries_admitted": True,
        "invalid_queries_rejected": rejected,
        "malformed_provider_options_rejected_before_optional_import": constructor_rejections,
    }, ("Envelope input checks do not establish an EOS phase or property qualification.",))


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace
    from math import isclose

    from h2physics.thermo import (
        CoolPropProperties,
        GasEnvelope,
        QualifiedGasTable,
    )

    reference = CoolPropProperties("Hydrogen")
    envelope = GasEnvelope(1e5, 90e6, 230., 400.)
    table = QualifiedGasTable(reference, envelope, validation_points=1000,
        timing_repetitions=1, internal_energy_policy="derive_from_h_p_rho")
    report = table.qualification
    assert report.qualification_passed and report.inverse_validation_point_count == 2000
    assert report.internal_energy_policy == "derive_from_h_p_rho"
    assert report.meets_speedup_target(report.measured_speedup)
    assert not report.meets_speedup_target(report.measured_speedup * 2.)
    for invalid_target in (0., -1., float("nan")):
        try:
            report.meets_speedup_target(invalid_target)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid caller performance target was accepted")
    from h2physics.thermo.tables import TableQualification

    direct_values = {
        name: getattr(report, name)
        for name in TableQualification.__dataclass_fields__
        if not name.startswith("_")
    }
    for construct in (
        lambda: TableQualification(**direct_values),
        lambda: replace(report, maximum_relative_errors=()),
        lambda: replace(report, table_seconds_per_call=0.),
    ):
        try:
            construct()
        except TypeError:
            pass
        else:
            raise AssertionError("Direct construction or replacement forged a table qualification report")
    from h2physics.thermo import TableQualificationError
    try:
        TableQualificationError(object())
    except TypeError:
        pass
    else:
        raise AssertionError("TableQualificationError accepted an untyped report payload")
    table.require_current()
    original_native_state = table._table._state
    table._table._state = table._table._cp.AbstractState("HEOS", "Water")
    try:
        table.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Qualified table accepted a replaced native CoolProp fluid state")
    finally:
        table._table._state = original_native_state
    table.require_current()
    maximum_holdout_error = 0.
    for pressure, temperature in ((2.17e5, 251.7), (4.321e6, 317.3), (67.89e6, 371.9)):
        truth = reference.state_pt(pressure, temperature)
        states = (table.state_pt(pressure, temperature),
                  table.state_ph(pressure, truth.enthalpy_j_kg),
                  table.state_ps(pressure, truth.entropy_j_kg_k))
        for state in states:
            for name in ("density_kg_m3", "enthalpy_j_kg", "internal_energy_j_kg",
                         "entropy_j_kg_k", "cp_j_kg_k", "cv_j_kg_k", "speed_of_sound_m_s"):
                error = abs(getattr(state, name)-getattr(truth, name))/abs(getattr(truth, name))
                maximum_holdout_error = max(maximum_holdout_error, error)
                assert error <= report.maximum_relative_error_allowed
            assert isclose(state.enthalpy_j_kg-state.internal_energy_j_kg,
                           state.pressure_pa/state.density_kg_m3, rel_tol=1e-12, abs_tol=1e-8)
    for operation in (lambda: table.state_pt(1e8, 300.),
                      lambda: table.state_ph(1e8, truth.enthalpy_j_kg),
                      lambda: table.state_ps(1e8, truth.entropy_j_kg_k),
                      lambda: QualifiedGasTable(reference, GasEnvelope(1e5, 1e6, 20., 300.))):
        try:
            operation()
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported table envelope/pressure was admitted")
    try:
        table.envelope = GasEnvelope(1e5, 1e9, 230., 400.)
    except AttributeError:
        pass
    else:
        raise AssertionError("Qualified table envelope was replaced")
    original_maximum = envelope.maximum_pressure_pa
    try:
        object.__setattr__(envelope, "maximum_pressure_pa", 1e9)
        try:
            report.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Nested envelope mutation retained report qualification")
        try:
            table.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Nested envelope mutation retained provider qualification")
    finally:
        object.__setattr__(envelope, "maximum_pressure_pa", original_maximum)
    table.require_current()
    original_error_limit = report.maximum_relative_error_allowed
    try:
        object.__setattr__(report, "maximum_relative_error_allowed", original_error_limit * 1000.)
        try:
            report.qualification_passed
        except ValueError:
            pass
        else:
            raise AssertionError("Mutated qualification report retained its passing status")
        try:
            report.meets_speedup_target(1.)
        except ValueError:
            pass
        else:
            raise AssertionError("Mutated qualification report retained its speedup decision")
    finally:
        object.__setattr__(report, "maximum_relative_error_allowed", original_error_limit)
    report.require_current()
    table.require_current()
    return ValidationOutcome(True, {"holdout_maximum_relative_error": maximum_holdout_error,
        "qualified_maximum_relative_identity_error": report.maximum_relative_enthalpy_identity_error,
        "qualification_maximum_relative_errors": dict(report.maximum_relative_errors),
        "maximum_relative_error_allowed": report.maximum_relative_error_allowed,
        "maximum_internal_energy_adjustment_j_kg": report.maximum_internal_energy_adjustment_j_kg,
        "validation_point_count": report.validation_point_count,
        "inverse_validation_point_count": report.inverse_validation_point_count,
        "reference_backend": report.reference_backend, "table_backend": report.table_backend,
        "property_library_version": report.property_library_version,
        "reference_seconds_per_call": report.reference_seconds_per_call,
        "table_seconds_per_call": report.table_seconds_per_call,
        "phase_domain_and_freshness_guards_verified": True,
        "measured_speedup": report.measured_speedup},
        ("Sampled gas envelope only; no phase-changing or independent experimental EOS validation",
         "Measured speedup is reported without assuming the tabular backend is faster"))
