"""Deferred common-clock operation receipt contract; execute on Nurion later."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="lh2dt-common-clock-operational-receipt",
        profile="lh2dt-operation",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "native supply nodes are present in every accepted dynamic inventory",
            "optional actuator command and output histories use the declared common clock and window",
            "optional relief traces and protection records retain original transition ownership",
            "a protected replay is admitted only when it retains the identical accepted dynamic run and its actions lie inside the receipt window",
            "an optional utility ledger requires explicit binding evidence and exact scenario clock/window agreement",
            "mismatched clocks, detached protection, or out-of-window events are rejected",
            "post-bind changes to native graph links, component bindings, or power-reader assignments fail currentness",
            "receipt does not execute a solver or claim native event-root support",
            "changed receipt declarations or retained inventory/transfer ledgers fail currentness",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    """Bind a caller-provided original scenario bundle and report its scope."""
    from h2physics.adapters.operational_scenario_receipt import bind_operational_scenario

    receipt = bind_operational_scenario(**parameters["scenario"])
    receipt.require_current()
    original_scenario_id = receipt.scenario_id
    object.__setattr__(receipt, "scenario_id", original_scenario_id + ":mutated")
    from h2physics.adapters.operational_scenario_receipt import OperationalScenarioError
    try:
        receipt.require_current()
    except OperationalScenarioError as error:
        assert "declarations or retained dynamic" in str(error)
    else:
        raise AssertionError("Changed receipt declaration was not detected")
    object.__setattr__(receipt, "scenario_id", original_scenario_id)
    receipt.require_current()
    network = receipt.supply.network
    link = network.native.links[0]
    network.add_link(
        "deferred-receipt-topology-mutation",
        link.left,
        link.right,
        link.component,
        power_reader=network._power_readers[link.name],
        source_port_id=link.source_port_id + "/deferred-mutation",
        target_port_id=link.target_port_id + "/deferred-mutation",
    )
    try:
        receipt.require_current()
    except OperationalScenarioError as error:
        assert "declarations or retained dynamic" in str(error)
        topology_mutation_rejected = True
    else:
        topology_mutation_rejected = False
    assert topology_mutation_rejected
    return ValidationOutcome(
        True,
        {"scenario_id": receipt.scenario_id,
         "clock_id": receipt.clock_id,
         "accepted_dynamic_steps": len(receipt.dynamic_run.steps),
         "actuator_count": len(receipt.actuator_traces),
         "relief_count": len(receipt.relief_traces),
         "protection_count": len(receipt.protection_records),
         "protected_run_count": len(receipt.protected_runs),
         "utility_profile_count": (0 if receipt.utility_ledger is None
                                   else len(receipt.utility_ledger.profiles)),
         "topology_mutation_rejected": topology_mutation_rejected},
        ("Identity/window continuity only; utility linkage is caller-attested; no thermal coupling, re-solve, or event localization",),
    )
