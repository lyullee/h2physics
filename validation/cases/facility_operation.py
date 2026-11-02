"""Deferred common-clock operation ownership rejection contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="facility-operation-foreign-utility-admission", profile="facility-protection",
        entrypoint=__name__+":validate_operation", parameters={}, invariants=(
            "actual native finite source and original utility ledger are separately retained",
            "foreign thermal duty cannot be relabelled as issued by the facility run",
            "rejection preserves original source validity and utility ownership",
        ),
    ), ValidationCase(
        identifier="facility-operation-original-process-report", profile="facility-protection",
        entrypoint=__name__+":validate_report", parameters={
            "fixture_module": "REPLACE_WITH_ADMITTED_FACILITY_OPERATION_FIXTURE",
            "fixture_builder": "build_admitted_facility_operation",
        }, invariants=(
            "report retains the exact original operation and common accepted clock",
            "per-node and per-component residual series reproduce admitted continuity receipts",
            "a selected node exposes both residual series against the exact same clock",
            "net utility quantities and residual preserve the original utility ledger",
            "report adds no product price, process physics, or whole-facility closure claim",
            "optional piecewise-linear trapezoidal residual integrals preserve node/component identity and units",
            "integrated instantaneous residuals remain diagnostics and are not native inventory closure",
        ),
    ), ValidationCase(
        identifier="facility-operation-audit-prefix-retention", profile="facility-protection",
        entrypoint=__name__ + ":validate_audit_prefix_retention", parameters={}, invariants=(
            "a later continuity-frame failure preserves exact earlier completed audit results",
            "the failed frame index, frame, original source, utilities and failure cause remain inspectable",
            "failure retention adds no facility simulation or balance closure",
        ),
    ),)


def validate_operation(*, work_directory, **parameters):
    from examples.facility_protection import make_case
    from examples.thermal_utilities import declared_case
    from h2physics.adapters.facility_operation import bind_facility_operation
    from h2physics.facility_continuity import (
        FacilityContinuityAudit,
        FacilityContinuityFrame,
        FacilityNode,
    )

    source = make_case()["source"]
    ledger = declared_case()[0]
    run = source.run
    audit = FacilityContinuityAudit(tuple(
        FacilityNode(name, state.basis) for name, state in run.initial_equipment.node_states.items()
    ))
    samples = ((run.start_time_s, run.initial_equipment),
               *((step.time_s, step.equipment) for step in run.steps))
    frames = tuple(FacilityContinuityFrame(run.clock_id, time, snapshot.transfers)
                   for time, snapshot in samples)
    try:
        bind_facility_operation(
            source, audit, frames, ledger,
            evidence_id="authored-common-clock-admission",
            instantaneous_rate_evidence_id="authored-ownership-rejection-only",
        )
    except ValueError as error:
        assert "exact finite run" in str(error)
    else:
        raise AssertionError("Foreign declared utilities were relabelled as facility-issued heat")
    assert source.require_current() is source
    assert ledger.require_current() is ledger
    return ValidationOutcome(True, {"foreign_utility_rejections": 1}, (
        "Source and utility models execute in their existing deferred APIs only",
        "No successful whole-facility energy closure is fabricated",
    ))


def validate_audit_prefix_retention(*, work_directory, **parameters):
    from unittest.mock import patch

    from h2physics.adapters.facility_operation import (
        FacilityOperationAuditError, bind_facility_operation,
    )

    del work_directory, parameters
    completed = (object(), object())
    frames = (object(), object(), object())
    failure = ValueError("authored-later-node-frame-failure")

    class Audit:
        def __init__(self):
            self.calls = []

        def audit(self, frame):
            index = len(self.calls)
            self.calls.append(frame)
            if index == 2:
                raise failure
            return completed[index]

    audit = Audit()
    source, utilities = object(), object()
    try:
        with patch("h2physics.adapters.facility_operation._admit"):
            bind_facility_operation(
                source, audit, frames, utilities,
                evidence_id="authored-common-operation",
                instantaneous_rate_evidence_id="authored-explicit-rate-source",
            )
    except FacilityOperationAuditError as error:
        assert error.cause is failure and error.__cause__ is failure
        assert error.finite_source is source and error.utilities is utilities
        assert error.failed_frame_index == 2 and error.failed_frame is frames[2]
        assert error.completed_frames == frames[:2]
        assert error.completed_results == completed
    else:
        raise AssertionError("Later frame failure did not preserve an incomplete audit prefix")
    return ValidationOutcome(True, {
        "failed_frame_index": 2,
        "completed_audit_results_retained": len(completed),
        "original_failure_retained": True,
    }, ("Synthetic receipt-admission failure contract only; no facility physics executed",))


def validate_report(*, work_directory, **parameters):
    import importlib
    from math import fsum

    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name or not isinstance(builder_name, str)
            or not builder_name.isidentifier()):
        raise ValueError("Configure a reviewed fixture returning an admitted FacilityOperationReceipt")
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name, None)
    if not callable(builder):
        raise ValueError("Facility reporting fixture must expose its configured builder")
    operation = builder(work_directory=work_directory, parameters=parameters)
    from h2physics.adapters.facility_operation import (
        FacilityOperationReceipt, integrate_facility_operation_residuals,
        report_facility_operation,
    )
    if type(operation) is not FacilityOperationReceipt:
        raise TypeError("Fixture must return an original admitted FacilityOperationReceipt")
    report = report_facility_operation(operation)
    assert report.require_current() is report
    assert report.operation is operation
    assert report.time_s == tuple(frame.time_s for frame in operation.continuity_frames)
    assert dict(report.net_utility_quantities) == dict(operation.utilities.quantities)
    assert report.utility_energy_residual_j == operation.utilities.energy_residual_j
    node_id = next(iter(report.node_mass_residual_kg_s))
    times, mass, energy = report.node_residual_series(node_id)
    assert times is report.time_s
    assert mass == report.node_mass_residual_kg_s[node_id]
    assert energy == report.node_energy_residual_w[node_id]
    integrated = integrate_facility_operation_residuals(report)
    assert integrated.require_current() is integrated
    assert integrated.report is report
    assert integrated.quadrature == "piecewise-linear trapezoidal"
    expected_mass = {}
    expected_energy = {}
    for key in report.node_mass_residual_kg_s:
        expected_mass[key] = fsum(
            (right-left)*(a+b)*0.5
            for left, right, a, b in zip(
                report.time_s[:-1], report.time_s[1:],
                report.node_mass_residual_kg_s[key],
                report.node_mass_residual_kg_s[key][1:], strict=True,
            )
        )
        expected_energy[key] = fsum(
            (right-left)*(a+b)*0.5
            for left, right, a, b in zip(
                report.time_s[:-1], report.time_s[1:],
                report.node_energy_residual_w[key],
                report.node_energy_residual_w[key][1:], strict=True,
            )
        )
    assert dict(integrated.node_mass_residual_kg) == expected_mass
    assert dict(integrated.node_energy_residual_j) == expected_energy
    components = {
        component for _, component, _ in report.component_energy_residual_w
    }
    assert set(integrated.component_energy_residual_j) == components
    expected_component = {}
    for component in components:
        values = tuple(next(residual for sample_time, item, residual
                            in report.component_energy_residual_w
                            if sample_time == time and item == component)
                       for time in report.time_s)
        expected_component[component] = fsum(
            (right-left)*(a+b)*0.5
            for left, right, a, b in zip(
                report.time_s[:-1], report.time_s[1:], values, values[1:], strict=True,
            )
        )
    assert dict(integrated.component_energy_residual_j) == expected_component
    try:
        report.node_residual_series("__unlisted_facility_node__")
    except KeyError:
        pass
    else:
        raise AssertionError("Unknown node identifiers must not be inferred")
    return ValidationOutcome(True, {
        "accepted_samples": len(report.time_s),
        "reported_nodes": len(report.node_mass_residual_kg_s),
        "utility_quantities": len(report.net_utility_quantities),
        "integrated_node_diagnostics": len(integrated.node_mass_residual_kg),
    }, (
        "Original receipt reporting only; no product price or facility-wide closure is inferred",
        "Fixture must supply a project-qualified operation because no default native facility is fabricated",
    ))
