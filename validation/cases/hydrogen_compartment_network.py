"""Deferred synthetic contracts for the fixed-state H2 compartment network."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (ValidationCase(
        identifier="hydrogen-fixed-state-compartment-network-mixing-closure",
        profile="oxygen-deficiency",
        entrypoint=__name__ + ":validate_network_contract",
        invariants=(
            "balanced-prescribed-molar-throughflow-mixes-hydrogen-between-compartments",
            "external-hydrogen-input-and-exhaust-close-the-network-species-ledger",
            "piecewise-constant-flow-schedules-use-one-common-output-clock",
            "unbalanced-node-throughflow-and-clock-mismatch-are-rejected",
            "issued-result-retains-fixed-state-compartment-and-stream-provenance",
            "late-numerical-failure-preserves-the-last-completed-output-prefix",
        ),
    ),)


def validate_network_contract(*, work_directory, **parameters):
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.compartment_network import (
        CompartmentMolarTransfer,
        CompartmentNetworkModel,
        WellMixedCompartment,
        simulate_hydrogen_compartment_network,
    )

    rooms = (
        WellMixedCompartment("source-room", 12., 101_325., 293.15, 0.,
                             "fixture-owner", "fixture-state"),
        WellMixedCompartment("adjacent-room", 24., 101_325., 293.15, 0.,
                             "fixture-owner", "fixture-state"),
    )
    schedule = (0.01, 0.01)
    streams = (
        CompartmentMolarTransfer("synthetic-h2-feed", None, "source-room", schedule,
                                 "fixture-source", "pure-h2-boundary", "room-clock", 1.),
        CompartmentMolarTransfer("doorway-transfer", "source-room", "adjacent-room", schedule,
                                 "fixture-door", "prescribed-molar-transfer", "room-clock"),
        CompartmentMolarTransfer("mechanical-exhaust", "adjacent-room", None, schedule,
                                 "fixture-fan", "prescribed-exhaust", "room-clock"),
    )
    model = CompartmentNetworkModel(rooms, streams, "room-clock")
    trace = simulate_hydrogen_compartment_network(model, time_samples_s=(0., 10., 20.))
    if trace.hydrogen_mole_fraction[-1, 1] <= 0.:
        raise AssertionError("Hydrogen did not propagate into the adjacent room")
    if np.max(np.abs(trace.hydrogen_balance_residual_mol)) > 1.e-10:
        raise AssertionError("External hydrogen inventory ledger did not close")
    if trace.cumulative_external_hydrogen_in_mol[-1] <= 0.:
        raise AssertionError("External feed was not retained in the trace")

    unbalanced = CompartmentNetworkModel(
        rooms,
        (CompartmentMolarTransfer("unbalanced-feed", None, "source-room", (0.01, 0.0),
                                  "fixture-source", "unbalanced", "room-clock", 1.),),
        "room-clock",
    )
    for bad_model, bad_times in ((unbalanced, (0., 10., 20.)), (model, (0., 10.))):
        try:
            simulate_hydrogen_compartment_network(bad_model, time_samples_s=bad_times)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid flow balance or stream clock coverage was accepted")
    wrong_clock_stream = CompartmentMolarTransfer(
        "wrong-clock", None, "source-room", schedule,
        "fixture-source", "wrong-clock-evidence", "other-clock", 1.,
    )
    try:
        CompartmentNetworkModel(rooms, (wrong_clock_stream,), "room-clock")
    except ValueError:
        pass
    else:
        raise AssertionError("A transfer with an incompatible clock was accepted")
    extreme_schedule = (0.01, 1.0e308)
    extreme_model = CompartmentNetworkModel(
        rooms,
        (
            CompartmentMolarTransfer("extreme-feed", None, "source-room", extreme_schedule,
                                     "fixture-source", "extreme-synthetic", "room-clock", 1.),
            CompartmentMolarTransfer("extreme-door", "source-room", "adjacent-room", extreme_schedule,
                                     "fixture-door", "extreme-synthetic", "room-clock"),
            CompartmentMolarTransfer("extreme-exhaust", "adjacent-room", None, extreme_schedule,
                                     "fixture-fan", "extreme-synthetic", "room-clock"),
        ),
        "room-clock",
    )
    try:
        simulate_hydrogen_compartment_network(extreme_model, time_samples_s=(0., 1., 3.))
    except Exception as error:
        from h2physics.compartment_network import CompartmentNetworkExecutionError

        if not isinstance(error, CompartmentNetworkExecutionError):
            raise
        if (error.failed_interval != 1 or error.accepted_prefix is None
                or not np.array_equal(error.accepted_prefix.time_s, (0., 1.))):
            raise AssertionError("Numerical failure did not preserve its accepted prefix")
    else:
        raise AssertionError("An overflowing species-ledger interval was accepted")
    return ValidationOutcome(True, {
        "room_ids": trace.compartment_ids,
        "final_h2_mole_fraction": tuple(float(x) for x in trace.hydrogen_mole_fraction[-1]),
        "external_hydrogen_in_mol": float(trace.cumulative_external_hydrogen_in_mol[-1]),
        "external_hydrogen_out_mol": float(trace.cumulative_external_hydrogen_out_mol[-1]),
        "maximum_species_residual_mol": float(np.max(np.abs(trace.hydrogen_balance_residual_mol))),
        "maximum_carrier_residual_mol": float(np.max(np.abs(trace.carrier_balance_residual_mol))),
    }, ("synthetic fixed-state mixing contract only; no pressure-driven flow or facility qualification",))
