"""Deferred contract for caller-configured multi-bank refill sequencing."""

from h2physics.cluster_validation import ValidationCase


def cases():
    return (ValidationCase(
        identifier="generic-cascade-refill-exclusive-bank-sequencing",
        profile="finite-transfer",
        entrypoint=__name__ + ":validate_sequence",
        invariants=(
            "caller-thresholds-advance-bank-sequence-monotonically",
            "only-one-bank-permit-may-be-enabled-at-a-time",
            "insufficient-source-headroom-disables-every-bank-permit",
            "receiver-target-disables-every-bank-permit-and-completes-sequence",
            "sensor-owner-and-common-clock-identities-remain-fixed",
            "controller-selects-banks-only-and-does-not-claim-flow-or-standard-compliance",
        ),
    ),)


def validate_sequence(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.cascade_refill import (
        CascadeBankStage,
        CascadeRefillMeasurement,
        CascadeRefillStatus,
        GenericCascadeRefillSequencer,
    )

    stages = (
        CascadeBankStage("low", 4e6, 0.5e6),
        CascadeBankStage("medium", 16e6, 0.5e6),
        CascadeBankStage("high", None, 0.5e6),
    )
    controller = GenericCascadeRefillSequencer(
        "generic-cascade-contract", 30e6, stages, "cascade-clock",
        "synthetic-authored-stage-thresholds",
    )
    bank_ids = {"low": "sensor-low", "medium": "sensor-medium", "high": "sensor-high"}
    bank_owners = {bank: "synthetic-bank-sensor-owner" for bank in bank_ids}
    state = controller.initial_state(
        time_s=0.0, receiver_sensor_id="receiver-pressure",
        receiver_sensor_owner_id="synthetic-receiver-owner",
        bank_sensor_ids=bank_ids, bank_sensor_owner_ids=bank_owners,
    )

    def sample(time_s, receiver_pressure_pa_absolute, bank_pressure_pa_absolute, sample_id):
        return CascadeRefillMeasurement(
            time_s, receiver_pressure_pa_absolute, bank_pressure_pa_absolute,
            "receiver-pressure", "synthetic-receiver-owner", bank_ids, bank_owners,
            "cascade-clock", sample_id,
        )

    initial = controller.step(state, sample(
        0., 1e6, {"low": 5e6, "medium": 17e6, "high": 32e6}, "sample-0"), end_time_s=1.)
    assert initial.status == CascadeRefillStatus.SELECTED
    assert initial.selected_bank_id == "low"

    medium = controller.step(initial.next_state, sample(
        1., 4e6, {"low": 4.4e6, "medium": 17e6, "high": 32e6}, "sample-1"), end_time_s=2.)
    assert medium.status == CascadeRefillStatus.SELECTED
    assert medium.selected_bank_id == "medium"
    assert medium.next_state.stage_index == 1

    waiting = controller.step(medium.next_state, sample(
        2., 16e6, {"low": 4.2e6, "medium": 16.4e6, "high": 16.4e6}, "sample-2"), end_time_s=3.)
    assert waiting.status == CascadeRefillStatus.WAITING_FOR_HEADROOM
    assert waiting.selected_bank_id is None
    assert not any(item.enabled for item in waiting.permits)

    high = controller.step(waiting.next_state, sample(
        3., 20e6, {"low": 4.2e6, "medium": 16.4e6, "high": 28e6}, "sample-3"), end_time_s=4.)
    assert high.status == CascadeRefillStatus.SELECTED
    assert high.selected_bank_id == "high"
    assert sum(item.enabled for item in high.permits) == 1

    complete = controller.step(high.next_state, sample(
        4., 30e6, {"low": 4.2e6, "medium": 16.4e6, "high": 28e6}, "sample-4"), end_time_s=5.)
    assert complete.status == CascadeRefillStatus.COMPLETE
    assert complete.selected_bank_id is None
    assert not any(item.enabled for item in complete.permits)
