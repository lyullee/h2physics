"""Deferred prescribed-pressure history contracts for pipe networks."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    profile = "gas-compressible-pipe"
    return (
        ValidationCase(identifier="hydrogen-pipeline-network-wave-prescribed-reservoir-history",
            profile=profile, entrypoint=__name__ + ":validate_reservoir_history",
            invariants=("clock-bound-pressure-history-interpolates-without-extrapolation",
                        "boundary-owner-evidence-EOS-and-temperature-are-retained",
                        "pipe-side-cumulative-exchange-closes-network-mass-ledger",
                        "source-reservoir-inventory-and-depletion-are-not-modeled")),
        ValidationCase(identifier="hydrogen-pipeline-network-wave-reservoir-contract-rejections",
            profile=profile, entrypoint=__name__ + ":validate_reservoir_rejections",
            invariants=("clock-EOS-temperature-time-support-and-owner-mismatch-reject",
                        "missing-reservoir-node-boundary-is-rejected")),
    )


def _fixture(variant=None):
    import numpy as np
    from h2physics.core import Origin
    from h2physics.isothermal_pipe_network_waves import (
        IsothermalPipeNetworkEdge, IsothermalPipeNetworkNode, IsothermalPipeNetworkWaveModel)
    from h2physics.isothermal_pipe_waves import IdealHydrogenIsothermalEOS
    from h2physics.pipe_reservoir_boundary import FiniteReservoirPressureBoundary
    eos = IdealHydrogenIsothermalEOS()
    clock = "authored-network-reservoir-clock"
    a = FiniteReservoirPressureBoundary("reservoir-a", "owner-a", "evidence-a", clock,
        eos.identity, 300., (0., .01, .02), (5.10e6, 5.15e6, 5.20e6), Origin.SYNTHETIC)
    b = FiniteReservoirPressureBoundary("reservoir-b", "owner-b", "evidence-b", clock,
        eos.identity, 300., (0., .01, .02), (4.90e6, 4.85e6, 4.80e6), Origin.SYNTHETIC)
    boundaries = {"reservoir-node-a": a, "reservoir-node-b": b}
    if variant == "clock": boundaries["reservoir-node-a"] = replace(a, clock_id="bad-clock")
    elif variant == "eos": boundaries["reservoir-node-a"] = replace(a, eos_identity="bad-eos")
    elif variant == "temperature": boundaries["reservoir-node-a"] = replace(a, temperature_k=301.)
    elif variant == "support": boundaries["reservoir-node-a"] = replace(a,
        time_s=(0., .005), pressure_pa=(5.10e6, 5.125e6))
    elif variant == "owner": boundaries["reservoir-node-a"] = replace(a, state_owner_id="wrong-owner")
    elif variant == "missing": boundaries.pop("reservoir-node-b")
    nodes = (
        IsothermalPipeNetworkNode("central", (0.,0.,0.), "junction", "junction-owner", "junction-evidence", Origin.SYNTHETIC, (4.e6,6.e6)),
        IsothermalPipeNetworkNode("reservoir-node-a", (100.,0.,0.), "reservoir", a.state_owner_id, a.state_evidence_id, Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("reservoir-node-b", (0.,100.,0.), "reservoir", b.state_owner_id, b.state_evidence_id, Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("wall", (-100.,0.,0.), "closed", "wall-owner", "wall-evidence", Origin.SYNTHETIC),
    )
    edges = (
        IsothermalPipeNetworkEdge("edge-a", "central", "reservoir-node-a", 100., .10, 12, "geo-a", "seg-a", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("edge-b", "reservoir-node-b", "central", 100., .12, 12, "geo-b", "seg-b", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("edge-c", "central", "wall", 100., .09, 12, "geo-c", "seg-c", origin=Origin.SYNTHETIC),
    )
    model = IsothermalPipeNetworkWaveModel(nodes, edges, 300., clock, eos, maximum_cfl=.2)
    pressure = {edge.identifier: np.full(12, 5.e6) for edge in edges}
    velocity = {edge.identifier: np.zeros(12) for edge in edges}
    return model, nodes, edges, eos, boundaries, pressure, velocity


def validate_reservoir_history(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np
    model, nodes, edges, eos, boundaries, pressure, velocity = _fixture()
    trace = model.simulate(initial_pressure_pa=pressure, initial_velocity_m_s=velocity,
        time_samples_s=(0.,.005,.01), reservoir_boundaries=boundaries)
    assert trace.clock_id == model.clock_id and trace.eos_identity == eos.identity
    assert trace.temperature_k == model.temperature_k
    assert np.allclose(trace.reservoir_pressure_pa["reservoir-node-a"], (5.10e6,5.125e6,5.15e6))
    assert np.allclose(trace.reservoir_pressure_pa["reservoir-node-b"], (4.90e6,4.875e6,4.85e6))
    for node_id, boundary in boundaries.items():
        assert trace.reservoir_ids[node_id] == boundary.identifier
        assert trace.reservoir_state_owner_ids[node_id] == boundary.state_owner_id
        assert trace.reservoir_evidence_ids[node_id] == boundary.state_evidence_id
        assert trace.reservoir_clock_ids[node_id] == boundary.clock_id
        assert trace.reservoir_origins[node_id] == boundary.origin
    assert trace.boundary_mass_in_kg[-1] > 0. and trace.boundary_mass_out_kg[-1] > 0.
    expected = trace.total_mass_kg-trace.total_mass_kg[0]-trace.boundary_mass_in_kg+trace.boundary_mass_out_kg
    assert np.allclose(trace.global_mass_balance_residual_kg, expected, rtol=0., atol=1.e-12)
    assert np.max(np.abs(trace.global_mass_balance_residual_kg)) < 1.e-8
    assert np.max(np.abs(trace.junction_mass_residual_kg_s["central"])) < 1.e-8
    assert set(trace.edge_geometry_evidence_ids) == {edge.identifier for edge in edges}
    assert set(trace.node_evidence_ids) == {node.identifier for node in nodes}
    return ValidationOutcome(True, {"pipe_side_inflow_kg": trace.boundary_mass_in_kg.tolist(),
        "pipe_side_outflow_kg": trace.boundary_mass_out_kg.tolist(),
        "global_mass_residual_kg": trace.global_mass_balance_residual_kg.tolist(),
        "reservoir_evidence_ids": dict(trace.reservoir_evidence_ids)},
        ("Prescribed pressure only; no source reservoir inventory/depletion model.",
         "Exchange is a pipe-side ledger, not a reservoir mass balance."))


def validate_reservoir_rejections(*, work_directory, **parameters):
    del work_directory, parameters
    def reject(call):
        try: call()
        except (TypeError, ValueError, FloatingPointError): return
        raise AssertionError("Invalid network reservoir contract was accepted")
    for variant in ("clock","eos","temperature","support","owner","missing"):
        model, _, _, _, boundaries, pressure, velocity = _fixture(variant)
        reject(lambda: model.simulate(initial_pressure_pa=pressure, initial_velocity_m_s=velocity,
            time_samples_s=(0.,.005,.01), reservoir_boundaries=boundaries))
    model, _, _, _, _, pressure, velocity = _fixture()
    reject(lambda: model.simulate(initial_pressure_pa=pressure, initial_velocity_m_s=velocity,
        time_samples_s=(0.,.005,.01)))
    return ValidationOutcome(True, {"rejected_contracts": ["clock","EOS","temperature",
        "time support","owner/evidence","missing boundary map"]},
        ("Synthetic rejection contract only; no source reservoir inventory is evaluated.",))
