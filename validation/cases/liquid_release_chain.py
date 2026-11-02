"""Deferred lazy composition contracts; no import-time physical execution."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="liquid-release-lazy-owner-chain", profile="droplet-impact",
        entrypoint=__name__+":validate_contract", parameters={},
        invariants=("construction invokes no property or domain factory",
                    "existing graph preserves flash/population/impact/pool dependency order",
                    "optional SLAB depends on original pool output",
                    "invalid factories and implicit flight options rejected")),)


def validate_contract(*, work_directory, **parameters):
    from h2physics.adapters.liquid_release_chain import liquid_release_scenario
    from h2physics.scenarios import ScenarioExecutionError

    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise RuntimeError("A lazy scenario constructor invoked a factory")

    arguments = dict(
        scenario_id="authored-lazy-liquid-chain", properties=object(),
        upstream_state=object(), downstream_pressure_pa=101325., total_release_mass_kg=.01,
        phase_equilibrium_evidence_id="authored-explicit-flash", population_factory=forbidden,
        flight_owner_factory=forbidden, flight_options={"start_s": 0., "end_s": 1.},
        distribution_evidence_id="authored-population", impact_group_id="one",
        impact_owner_factory=forbidden, pool_options_factory=forbidden,
    )
    scenario = liquid_release_scenario(**arguments)
    assert calls == []
    assert scenario.execution_order == ("flash", "population", "impact", "pool")
    assert scenario.nodes[1].dependencies == ("flash",)
    assert scenario.nodes[2].dependencies == ("population",)
    assert scenario.nodes[3].dependencies == ("impact",)
    with_slab = liquid_release_scenario(**arguments, slab_options_factory=forbidden)
    assert with_slab.execution_order[-1] == "dispersion"
    assert with_slab.nodes[-1].dependencies == ("pool",)
    assert calls == []
    # Request only the first node with invalid typed inputs. The existing flash
    # boundary must refuse before any domain factory or property call occurs.
    try:
        scenario.run(targets=("flash",))
    except ScenarioExecutionError as error:
        assert error.node.node_id == "flash" and error.completed == ()
        assert isinstance(error.cause, TypeError) and error.cause is error.__cause__
    else:
        raise AssertionError("An untyped upstream flash input was accepted")
    assert calls == []
    for changes in ({"population_factory": None}, {"flight_options": None},
                    {"slab_options_factory": object()}):
        try:
            liquid_release_scenario(**dict(arguments, **changes))
        except TypeError:
            pass
        else:
            raise AssertionError("Implicit callback/options entered liquid source composition")
    return ValidationOutcome(True, {"nodes_without_SLAB": 4, "nodes_with_SLAB": 5,
        "constructor_factory_calls": len(calls)},
        ("Composition and refusal contract only; no physical source/impact/pool execution",))
