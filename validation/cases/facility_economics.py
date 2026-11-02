"""Deferred operation-to-cost ownership admission contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="facility-economics-requires-admitted-operation", profile="hydrogen-economics",
        entrypoint=__name__+":validate_admission", parameters={}, invariants=(
            "actual finite accident source alone is not an admitted complete facility operation",
            "source mass is never promoted implicitly to manufactured or sold product",
            "invalid operation cannot trigger physical tariff pricing",
        ),
    ),)


def validate_admission(*, work_directory, **parameters):
    from examples.facility_protection import make_case
    from h2physics.adapters.facility_economics import price_facility_operation

    source = make_case()["source"]
    source.require_current()
    try:
        price_facility_operation(source, None, (), evidence_id="authored-cost-ownership-rejection")
    except TypeError as error:
        assert "FacilityOperationReceipt" in str(error)
    else:
        raise AssertionError("Accident source was promoted implicitly to facility production/cost")
    assert source.require_current() is source
    return ValidationOutcome(True, {"source_as_product_rejections": 1}, (
        "Ownership rejection only; no successful facility cost or financial result is fabricated",
        "No current prices, annual production, product sales or economic validity established",
    ))
