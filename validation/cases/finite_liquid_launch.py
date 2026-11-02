"""Deferred finite native source-to-liquid projection admission contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-liquid-launch-native-projection-gates", profile="facility-protection",
        entrypoint=__name__+":validate_contract", parameters={},
        invariants=("original admitted finite source required",
                    "one explicitly evidenced liquid state per native mass bin",
                    "gas outlet state cannot be relabelled as liquid spray",
                    "native accepted outlet enthalpy quadrature is retained",
                    "read-only per-bin report retains source clock/edges and native W-to-J quadrature",
                    "lazy per-bin scenario preserves dependency order and refuses unissued bindings before factories")),)


def validate_contract(*, work_directory, **parameters):
    from examples.facility_protection import make_case
    from h2physics.adapters.finite_liquid_launch import (
        FiniteLiquidLaunch,
        bind_finite_liquid_launch,
    )
    from h2physics.scenarios import ScenarioExecutionError

    calls = []
    def forbidden(value):
        calls.append(value)
        raise AssertionError("A lazy or unissued launch invoked a downstream factory")
    detached = FiniteLiquidLaunch(object(), (object(),), ("unissued",), (0.,), (0.,), (0.,), 1e-6, 1e-8)
    graph = detached.scenario_for_bin(0, scenario_id="unissued-bin-refusal",
        launch_options={}, impact_group_id="one", impact_owner_factory=forbidden,
        pool_options_factory=forbidden, slab_options_factory=forbidden)
    assert graph.execution_order == ("population", "impact", "pool", "dispersion")
    assert graph.nodes[0].dependencies == () and graph.nodes[-1].dependencies == ("pool",)
    assert calls == []
    try:
        graph.run(targets=("population",))
    except ScenarioExecutionError as error:
        assert error.node.node_id == "population" and error.completed == ()
        assert isinstance(error.cause, ValueError)
    else:
        raise AssertionError("Unissued finite liquid launch executed a population node")
    assert calls == []

    binding = make_case()["source"]
    binding.require_current()
    state = binding.source.state
    assert state.phase == "gas"
    count = len(binding.source.mass_kg)
    projection = binding.energy_projection()
    for index, integral in enumerate(projection.native_integrals):
        assert integral.clock_id == binding.source.location.clock_id
        assert integral.start_time_s == binding.source.edges_s[index]
        assert integral.end_time_s == binding.source.edges_s[index+1]
        assert integral.rate_unit == "W" and integral.integral_unit == "J"
    kwargs = dict(projection_evidence_ids=("authored-state-projection",)*count,
                  absolute_enthalpy_tolerance_j=1e-6, relative_enthalpy_tolerance=1e-8)
    for supplied in ((state,)*count, (state,)*(count+1)):
        try:
            bind_finite_liquid_launch(binding, supplied, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Gas projection or mismatched source-bin states admitted as liquid")
    try:
        bind_finite_liquid_launch(object(), (), **kwargs)
    except TypeError:
        pass
    else:
        raise AssertionError("Unissued source accepted for finite liquid launch")
    return ValidationOutcome(True, {"original_source_bins": count},
        ("Native gas reference refusal only; liquid-bin success and flight validation remain pending",))
