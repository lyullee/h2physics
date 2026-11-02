"""Deferred Nurion validation for sampled facility continuity."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = (
        ("facility-continuity-closed-forward", "validate_closed_forward", ("two finite nodes", "mass/enthalpy closure")),
        ("facility-continuity-external-boundaries", "validate_external_boundaries", ("signed feed/takeoff", "finite accumulation")),
        ("facility-continuity-finite-accumulation", "validate_finite_accumulation", ("explicit storage derivative",)),
        ("facility-continuity-heat-and-work", "validate_heat_and_work", ("nonmaterial boundaries",)),
        ("facility-continuity-reverse-flow", "validate_reverse_flow", ("upstream identity follows sign",)),
        ("facility-continuity-identity-rejection", "validate_identity_rejection", ("unique ports", "compatible basis")),
        ("facility-continuity-retained-nonclosure", "validate_retained_nonclosure", ("diagnostic residual retained", "strict rejection")),
    )
    return tuple(ValidationCase(identifier=name, profile="facility-continuity",
        entrypoint=__name__+":"+entry, parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)


def _objects():
    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.facility_continuity import FacilityContinuityAudit, FacilityNode

    basis = PropertyBasis("Hydrogen", "facility-case-reference", "normal")
    state = ThermoState(basis, 2.0e6, 300.0, 1.6, 4.0e6, 2.75e6, 5.0e4, "gas")
    audit = FacilityContinuityAudit((FacilityNode("left", basis), FacilityNode("right", basis)))
    return basis, state, audit


def _transfer(state, rate=0.01):
    from h2physics.equipment import BoundaryPower, ConnectionTransfer

    return ConnectionTransfer("device", "left", "right", "left:p", "right:p",
                              rate, state, state, BoundaryPower(), 0.0, True)


def validate_closed_forward(*, work_directory, **parameters):
    from h2physics.facility_continuity import FacilityContinuityFrame, FacilityStorageRate

    basis, state, audit = _objects()
    frame = FacilityContinuityFrame("case-clock", 1.0, (_transfer(state),), (), (
        FacilityStorageRate("left", basis, -0.01, -40000.0),
        FacilityStorageRate("right", basis, 0.01, 40000.0)))
    result = audit.audit(frame)
    assert result.mass_residual_kg_s == 0.0 and result.node_energy_residual_w == 0.0
    return ValidationOutcome(True, {"nodes": len(result.nodes)}, ("Authored continuity frame.",))


def validate_external_boundaries(*, work_directory, **parameters):
    from h2physics.facility_continuity import (
        ExternalFacilityRate,
        FacilityContinuityAudit,
        FacilityContinuityFrame,
        FacilityNode,
        FacilityStorageRate,
    )

    basis, state, _ = _objects()
    audit = FacilityContinuityAudit((FacilityNode("left", basis),))
    boundaries = (ExternalFacilityRate("feed", "left", "feed:p", 0.10, state),
                  ExternalFacilityRate("takeoff", "left", "takeoff:p", -0.04, state))
    frame = FacilityContinuityFrame("case-clock", 2.0, (), boundaries,
        (FacilityStorageRate("left", basis, 0.06, 240000.0),))
    result = audit.audit(frame)
    assert not result.violations(audit.tolerances)
    return ValidationOutcome(True, {"boundaries": 2}, ("Signed rates are caller supplied.",))


def validate_finite_accumulation(*, work_directory, **parameters):
    result = validate_closed_forward(work_directory=work_directory, **parameters)
    return ValidationOutcome(result.accepted, {"finite_nodes": 2}, result.limitations)


def validate_heat_and_work(*, work_directory, **parameters):
    from h2physics.facility_continuity import (
        ExternalFacilityRate,
        FacilityContinuityAudit,
        FacilityContinuityFrame,
        FacilityNode,
        FacilityStorageRate,
    )

    basis, _, _ = _objects()
    audit = FacilityContinuityAudit((FacilityNode("left", basis),))
    boundary = ExternalFacilityRate("utility", "left", "utility:p", 0.0, None, 100.0, 20.0)
    frame = FacilityContinuityFrame("case-clock", 3.0, (), (boundary,),
        (FacilityStorageRate("left", basis, 0.0, 120.0),))
    result = audit.audit(frame)
    assert result.node_energy_residual_w == 0.0
    return ValidationOutcome(True, {"heat_w": 100.0, "shaft_w": 20.0}, ("No utility performance inferred.",))


def validate_reverse_flow(*, work_directory, **parameters):
    from h2physics.facility_continuity import FacilityContinuityFrame, FacilityStorageRate

    basis, state, audit = _objects()
    frame = FacilityContinuityFrame("case-clock", 4.0, (_transfer(state, -0.01),), (), (
        FacilityStorageRate("left", basis, 0.01, 40000.0),
        FacilityStorageRate("right", basis, -0.01, -40000.0)))
    result = audit.audit(frame)
    assert not result.violations(audit.tolerances)
    return ValidationOutcome(True, {"direction": -1}, ("Transport state ownership follows flow sign.",))


def validate_identity_rejection(*, work_directory, **parameters):
    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.facility_continuity import ExternalFacilityRate, FacilityContinuityFrame

    _, state, audit = _objects()
    duplicate = ExternalFacilityRate("duplicate", "left", "left:p", 0.01, state)
    rejected = 0
    try:
        audit.audit(FacilityContinuityFrame("case-clock", 5.0, (_transfer(state),), (duplicate,)), require_closed=False)
    except ValueError:
        rejected += 1
    other = PropertyBasis("Hydrogen", "different-reference", "normal")
    wrong = ThermoState(other, 2e6, 300.0, 1.6, 4e6, 2.75e6, 5e4, "gas")
    try:
        audit.audit(FacilityContinuityFrame("case-clock", 5.0, (),
            (ExternalFacilityRate("wrong", "left", "other:p", 0.01, wrong),)), require_closed=False)
    except ValueError:
        rejected += 1
    assert rejected == 2
    return ValidationOutcome(True, {"rejections": rejected}, ("Identity failures remain explicit.",))


def validate_retained_nonclosure(*, work_directory, **parameters):
    from h2physics.facility_continuity import FacilityContinuityFrame

    _, state, audit = _objects()
    frame = FacilityContinuityFrame("case-clock", 6.0, (_transfer(state),))
    result = audit.audit(frame, require_closed=False)
    assert result.violations(audit.tolerances)
    try:
        audit.audit(frame)
    except ValueError as error:
        message = str(error)
    else:
        raise AssertionError("Strict audit accepted an unbalanced facility")
    return ValidationOutcome(True, {"violation_count": len(result.violations(audit.tolerances))},
        (message, "No missing storage derivative was inferred."))
