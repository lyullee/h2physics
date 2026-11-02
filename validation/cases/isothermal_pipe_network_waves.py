"""Deferred branched isothermal pressure-wave network contract suite."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    profile = "gas-compressible-pipe"
    return (
        ValidationCase(
            identifier="hydrogen-pipeline-branched-isothermal-wave-network",
            profile=profile, entrypoint=__name__ + ":validate_network",
            invariants=(
                "each-pipe-edge-advances-one-dimensional-isothermal-Euler-finite-volumes",
                "each-junction-has-common-EOS-backed-pressure-and-zero-summed-outward-Rusanov-mass-flow",
                "junction-pressure-root-stays-inside-caller-bounds-and-subsonic-characteristic-states",
                "global-network-mass-closes-across-all-junctions-and-closed-wall-terminals",
                "clock-EOS-temperature-node-state-and-edge-geometry-provenance-are-retained",
                "supersonic-junction-states-are-rejected",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-network-wave-reversed-orientation-order",
            profile=profile, entrypoint=__name__ + ":validate_reversed_orientation",
            invariants=(
                "reversing-each-edge-and-node-insertion-order-preserves-physical-pressure-fields",
                "velocity-and-signed-face-flow-transform-consistently-with-edge-orientation",
                "junction-continuity-and-global-mass-closure-are-order-independent",
                "source-and-geometry-provenance-remain-keyed-to-stable-identifiers",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-network-wave-unequal-branch-areas",
            profile=profile, entrypoint=__name__ + ":validate_unequal_areas",
            invariants=(
                "junction-continuity-sums-area-weighted-mass-flux-not-velocity-or-volume-flow",
                "unequal-branch-area-edge-flows-close-junction-and-network-mass-ledgers",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-network-wave-darcy-friction",
            profile=profile, entrypoint=__name__ + ":validate_friction",
            invariants=(
                "nonzero-per-edge-Darcy-friction-advances-without-changing-mass-conservation",
                "friction-and-zero-friction-receipts-retain-identical-EOS-clock-geometry-basis",
                "frictional-wave-state-remains-finite-and-junction-mass-conserving",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-network-wave-pressure-bound-failure",
            profile=profile, entrypoint=__name__ + ":validate_pressure_bound_failure",
            invariants=(
                "a-junction-pressure-bracket-that-cannot-contain-a-continuity-root-is-rejected",
                "failure-identifies-the-caller-pressure-bound-contract-not-an-implicit-fallback",
            ),
        ),
    )


def _fixture(*, reverse_orientation=False, reverse_node_order=False,
             diameters=(.1, .1, .1), friction=.01,
             pressure_bounds=(4.e6, 6.e6)):
    import numpy as np

    from h2physics.core import Origin
    from h2physics.isothermal_pipe_network_waves import (
        IsothermalPipeNetworkEdge,
        IsothermalPipeNetworkNode,
        IsothermalPipeNetworkWaveModel,
    )
    from h2physics.isothermal_pipe_waves import IdealHydrogenIsothermalEOS

    nodes = (
        IsothermalPipeNetworkNode(
            identifier="authored-central-junction", coordinates_m=(0., 0., 0.),
            kind="junction", state_owner_id="authored-junction-state",
            evidence_id="authored-junction-contract", origin=Origin.SYNTHETIC,
            pressure_bounds_pa=pressure_bounds,
        ),
        IsothermalPipeNetworkNode(
            identifier="authored-branch-a-wall", coordinates_m=(100., 0., 0.),
            kind="closed", state_owner_id="authored-wall-a",
            evidence_id="authored-wall-a-contract", origin=Origin.SYNTHETIC,
        ),
        IsothermalPipeNetworkNode(
            identifier="authored-branch-b-wall", coordinates_m=(0., 100., 0.),
            kind="closed", state_owner_id="authored-wall-b",
            evidence_id="authored-wall-b-contract", origin=Origin.SYNTHETIC,
        ),
        IsothermalPipeNetworkNode(
            identifier="authored-branch-c-wall", coordinates_m=(-100., 0., 0.),
            kind="closed", state_owner_id="authored-wall-c",
            evidence_id="authored-wall-c-contract", origin=Origin.SYNTHETIC,
        ),
    )
    labels = ("a", "b", "c")
    edges = tuple(IsothermalPipeNetworkEdge(
        identifier=f"authored-branch-{label}",
        start_node_id=(f"authored-branch-{label}-wall" if reverse_orientation
                       else "authored-central-junction"),
        end_node_id=("authored-central-junction" if reverse_orientation
                     else f"authored-branch-{label}-wall"),
        length_m=100., internal_diameter_m=diameters[index], cell_count=12,
        geometry_owner_id=f"authored-geometry-{label}",
        geometry_evidence_id=f"authored-segment-{label}",
        darcy_friction_factor=friction, origin=Origin.SYNTHETIC,
    ) for index, label in enumerate(labels))
    if reverse_node_order:
        nodes = tuple(reversed(nodes))
    if reverse_orientation and reverse_node_order:
        edges = tuple(reversed(edges))
    eos = IdealHydrogenIsothermalEOS()
    model = IsothermalPipeNetworkWaveModel(
        nodes=nodes, edges=edges, temperature_k=300.,
        clock_id="authored-network-clock", eos=eos, maximum_cfl=.25,
    )
    count = 12
    pressure = {
        "authored-branch-a": np.full(count, 5.10e6),
        "authored-branch-b": np.full(count, 4.90e6),
        "authored-branch-c": np.full(count, 5.00e6),
    }
    velocity = {key: np.zeros(count) for key in pressure}
    return model, nodes, edges, eos, pressure, velocity


def _simulate(model, pressure, velocity, *, times=(0., .005, .01)):
    return model.simulate(
        initial_pressure_pa=pressure,
        initial_velocity_m_s=velocity,
        time_samples_s=times,
    )


def _require_network_trace(trace, model, nodes, edges, eos, *, expected_bounds=(4.e6, 6.e6)):
    import numpy as np

    count = {edge.identifier: edge.cell_count for edge in edges}
    assert trace.clock_id == model.clock_id
    assert trace.eos_identity == eos.identity and trace.temperature_k == model.temperature_k
    assert set(trace.edge_pressure_pa) == set(count)
    assert set(trace.junction_pressure_pa) == {"authored-central-junction"}
    for edge in edges:
        assert trace.edge_pressure_pa[edge.identifier].shape == (len(trace.time_s), count[edge.identifier])
        assert trace.edge_velocity_m_s[edge.identifier].shape == trace.edge_pressure_pa[edge.identifier].shape
        assert trace.edge_face_mass_flow_kg_s[edge.identifier].shape == (
            len(trace.time_s), count[edge.identifier]+1,
        )
        wall_face = 0 if edge.start_node_id.endswith("-wall") else -1
        assert np.allclose(trace.edge_face_mass_flow_kg_s[edge.identifier][:, wall_face], 0.)
    junction_pressure = trace.junction_pressure_pa["authored-central-junction"]
    assert np.all((junction_pressure >= expected_bounds[0])
                  & (junction_pressure <= expected_bounds[1]))
    assert np.max(np.abs(trace.junction_mass_residual_kg_s[
        "authored-central-junction"])) < 1.e-8
    assert np.max(np.abs(trace.global_mass_balance_residual_kg)) < 1.e-8
    assert set(trace.edge_geometry_evidence_ids) == set(count)
    assert set(trace.node_state_owner_ids) == {node.identifier for node in nodes}
    assert set(trace.node_evidence_ids) == {node.identifier for node in nodes}
    return trace


def validate_network(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    model, nodes, edges, eos, pressure, velocity = _fixture()
    trace = _require_network_trace(
        _simulate(model, pressure, velocity), model, nodes, edges, eos,
    )
    assert any(np.max(np.abs(flow)) > 0.
               for flow in trace.edge_face_mass_flow_kg_s.values())

    def must_reject(call):
        try:
            call()
        except (TypeError, ValueError, FloatingPointError):
            return
        raise AssertionError("Supersonic junction state was accepted")

    fast_velocity = {key: value.copy() for key, value in velocity.items()}
    fast_velocity["authored-branch-a"] = np.full(12, 2.e3)
    must_reject(lambda: _simulate(model, pressure, fast_velocity, times=(0., .001)))
    return ValidationOutcome(True, {
        "clock_id": trace.clock_id,
        "eos_identity": trace.eos_identity,
        "junction_pressure_pa": trace.junction_pressure_pa[
            "authored-central-junction"].tolist(),
        "junction_mass_residual_kg_s": trace.junction_mass_residual_kg_s[
            "authored-central-junction"].tolist(),
        "total_mass_kg": trace.total_mass_kg.tolist(),
        "global_mass_balance_residual_kg": trace.global_mass_balance_residual_kg.tolist(),
        "edge_geometry_evidence_ids": dict(trace.edge_geometry_evidence_ids),
    }, (
        "Synthetic software contract only; geometry/state identifiers are authored inputs.",
        "No compressor, valve, reservoir depletion, gravity, thermal transient, or measured-network qualification is included.",
    ))


def validate_reversed_orientation(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    base_model, base_nodes, base_edges, eos, pressure, velocity = _fixture()
    base = _require_network_trace(
        _simulate(base_model, pressure, velocity), base_model, base_nodes, base_edges, eos,
    )
    reversed_model, reversed_nodes, reversed_edges, reversed_eos, reversed_pressure, reversed_velocity = _fixture(
        reverse_orientation=True, reverse_node_order=True,
    )
    reversed_trace = _require_network_trace(
        _simulate(reversed_model, reversed_pressure, reversed_velocity),
        reversed_model, reversed_nodes, reversed_edges, reversed_eos,
    )
    for edge_id in base.edge_pressure_pa:
        assert np.allclose(reversed_trace.edge_pressure_pa[edge_id][:, ::-1],
                           base.edge_pressure_pa[edge_id], rtol=1.e-8, atol=1.e-5)
        assert np.allclose(reversed_trace.edge_velocity_m_s[edge_id][:, ::-1],
                           -base.edge_velocity_m_s[edge_id], rtol=1.e-8, atol=1.e-8)
        assert np.allclose(reversed_trace.edge_face_mass_flow_kg_s[edge_id][:, ::-1],
                           -base.edge_face_mass_flow_kg_s[edge_id], rtol=1.e-8, atol=1.e-9)
    assert np.allclose(reversed_trace.junction_pressure_pa["authored-central-junction"],
                       base.junction_pressure_pa["authored-central-junction"],
                       rtol=1.e-8, atol=1.e-5)
    return ValidationOutcome(True, {
        "orientation_reversed": True,
        "node_and_edge_insertion_order_reversed": True,
        "junction_pressure_pa": reversed_trace.junction_pressure_pa[
            "authored-central-junction"].tolist(),
        "maximum_global_mass_residual_kg": float(np.max(np.abs(
            reversed_trace.global_mass_balance_residual_kg))),
        "edge_geometry_evidence_ids": dict(reversed_trace.edge_geometry_evidence_ids),
    }, ("Synthetic orientation/insertion-order invariance only; no measured network evidence.",))


def validate_unequal_areas(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    diameters = (.08, .10, .14)
    model, nodes, edges, eos, pressure, velocity = _fixture(diameters=diameters)
    trace = _require_network_trace(
        _simulate(model, pressure, velocity), model, nodes, edges, eos,
    )
    central_outflow = sum(
        trace.edge_face_mass_flow_kg_s[edge.identifier][:, 0]
        for edge in edges
    )
    assert np.max(np.abs(central_outflow)) < 1.e-8
    assert len({edge.internal_diameter_m for edge in edges}) == 3
    assert np.max(np.abs(trace.global_mass_balance_residual_kg)) < 1.e-8
    return ValidationOutcome(True, {
        "branch_diameters_m": list(diameters),
        "central_outward_mass_flow_sum_kg_s": central_outflow.tolist(),
        "junction_mass_residual_kg_s": trace.junction_mass_residual_kg_s[
            "authored-central-junction"].tolist(),
        "global_mass_balance_residual_kg": trace.global_mass_balance_residual_kg.tolist(),
    }, ("Synthetic unequal-area continuity contract only.",))


def validate_friction(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    frictional = _fixture(friction=.8)
    frictionless = _fixture(friction=0.)
    model, nodes, edges, eos, pressure, velocity = frictional
    trace = _require_network_trace(
        _simulate(model, pressure, velocity, times=(0., .01, .02)),
        model, nodes, edges, eos,
    )
    reference_model, reference_nodes, reference_edges, reference_eos, ref_pressure, ref_velocity = frictionless
    reference = _require_network_trace(
        _simulate(reference_model, ref_pressure, ref_velocity, times=(0., .01, .02)),
        reference_model, reference_nodes, reference_edges, reference_eos,
    )
    frictional_speed = max(float(np.max(np.abs(value)))
                           for value in trace.edge_velocity_m_s.values())
    frictionless_speed = max(float(np.max(np.abs(value)))
                             for value in reference.edge_velocity_m_s.values())
    assert frictional_speed < frictionless_speed
    assert all(edge.darcy_friction_factor == .8 for edge in edges)
    return ValidationOutcome(True, {
        "darcy_friction_factor": .8,
        "maximum_frictional_speed_m_s": frictional_speed,
        "maximum_zero_friction_speed_m_s": frictionless_speed,
        "frictional_global_mass_residual_kg": trace.global_mass_balance_residual_kg.tolist(),
        "frictionless_global_mass_residual_kg": reference.global_mass_balance_residual_kg.tolist(),
    }, ("Synthetic constant-Darcy momentum damping contract; not a friction correlation validation.",))


def validate_pressure_bound_failure(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    model, _nodes, _edges, _eos, pressure, velocity = _fixture(
        pressure_bounds=(7.e6, 8.e6),
    )
    try:
        _simulate(model, pressure, velocity, times=(0., .001))
    except ValueError as error:
        if "declared bounds" not in str(error):
            raise AssertionError("Pressure-bound case failed for an unrelated reason") from error
    else:
        raise AssertionError("Junction pressure root outside the caller bracket was accepted")
    return ValidationOutcome(True, {
        "rejected_pressure_bounds_pa": [7.e6, 8.e6],
        "initial_branch_pressures_pa": [5.10e6, 4.90e6, 5.00e6],
        "clock_id": model.clock_id,
        "edge_ids": [edge.identifier for edge in _edges],
    }, ("Synthetic rejection contract only; no extrapolated junction state is imputed.",))
