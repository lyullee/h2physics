"""Deferred branched-network contracts for finite isothermal inventories."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (
        ValidationCase(
            identifier="hydrogen-pipeline-network-wave-finite-inventory-reservoir",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_finite_inventory",
            invariants=(
                "finite-reservoir-mass-is-advanced-by-the-exact-signed-endpoint-Rusanov-flux",
                "reservoir-pressure-is-recomputed-from-current-mass-fixed-volume-temperature-and-shared-EOS",
                "pipe-plus-finite-reservoir-combined-mass-closes-at-every-sample",
                "endpoint-mass-pressure-histories-and-owner-evidence-clock-EOS-origin-are-retained",
                "finite-inventory-boundary-is-distinct-from-prescribed-pressure-history-without-reservoir-stock",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-network-wave-finite-inventory-rejections",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_contract_rejections",
            invariants=(
                "finite-reservoir-node-record-and-owner-evidence-must-match-exactly",
                "reservoir-clock-EOS-temperature-volume-state-and-inventory-bounds-are-explicit",
                "missing-or-extra-finite-inventory-node-records-are-rejected",
            ),
        ),
    )


def _fixture(*, owner_id="authored-finite-reservoir-owner", clock_id="authored-finite-reservoir-clock",
             mass_floor=.05):
    import numpy as np

    from h2physics.core import Origin
    from h2physics.finite_pipe_reservoir import FiniteIsothermalPipeReservoir
    from h2physics.isothermal_pipe_network_waves import (
        IsothermalPipeNetworkEdge,
        IsothermalPipeNetworkNode,
        IsothermalPipeNetworkWaveModel,
    )
    from h2physics.isothermal_pipe_waves import IdealHydrogenIsothermalEOS

    eos = IdealHydrogenIsothermalEOS()
    reservoir_pressure = 5.2e6
    temperature = 300.
    volume = .2
    mass = eos.density_pt(reservoir_pressure, temperature) * volume
    reservoir = FiniteIsothermalPipeReservoir(
        identifier="authored-finite-inventory",
        node_id="finite-reservoir-terminal",
        state_owner_id=owner_id,
        state_evidence_id="authored-initial-inventory-record",
        clock_id=clock_id,
        eos_identity=eos.identity,
        temperature_k=temperature,
        volume_m3=volume,
        mass_kg=mass,
        minimum_mass_kg=mass_floor,
        maximum_mass_kg=2. * mass,
        origin=Origin.SYNTHETIC,
    )
    nodes = (
        IsothermalPipeNetworkNode("central", (0., 0., 0.), "junction",
            "junction-owner", "junction-evidence", Origin.SYNTHETIC, (4.e6, 6.e6)),
        IsothermalPipeNetworkNode("finite-reservoir-terminal", (100., 0., 0.),
            "finite_reservoir", owner_id, reservoir.state_evidence_id, Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("wall-a", (0., 100., 0.), "closed",
            "wall-owner-a", "wall-evidence-a", Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("wall-b", (-100., 0., 0.), "closed",
            "wall-owner-b", "wall-evidence-b", Origin.SYNTHETIC),
    )
    edges = (
        IsothermalPipeNetworkEdge("branch-reservoir", "central", "finite-reservoir-terminal",
            100., .1, 12, "geometry-owner-r", "geometry-evidence-r", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("branch-wall-a", "central", "wall-a",
            100., .1, 12, "geometry-owner-a", "geometry-evidence-a", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("branch-wall-b", "central", "wall-b",
            100., .1, 12, "geometry-owner-b", "geometry-evidence-b", origin=Origin.SYNTHETIC),
    )
    model = IsothermalPipeNetworkWaveModel(
        nodes, edges, temperature, clock_id, eos, maximum_cfl=.2)
    pressures = {edge.identifier: np.full(edge.cell_count, 5.e6) for edge in edges}
    velocities = {edge.identifier: np.zeros(edge.cell_count) for edge in edges}
    return model, nodes, edges, eos, reservoir, pressures, velocities


def validate_finite_inventory(*, work_directory, **parameters):
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    model, nodes, edges, eos, reservoir, pressure, velocity = _fixture()
    trace = model.simulate(
        initial_pressure_pa=pressure,
        initial_velocity_m_s=velocity,
        time_samples_s=(0., .01, .02),
        finite_reservoirs={reservoir.node_id: reservoir},
    )
    assert trace.clock_id == model.clock_id and trace.eos_identity == eos.identity
    assert set(trace.finite_inventory_mass_kg) == {reservoir.node_id}
    assert np.all(np.diff(trace.finite_inventory_mass_kg[reservoir.node_id]) < 0.)
    assert np.all(np.diff(trace.finite_inventory_pressure_pa[reservoir.node_id]) < 0.)
    assert np.max(np.abs(trace.global_mass_balance_residual_kg)) < 1.e-8
    assert np.allclose(trace.total_mass_kg, trace.total_mass_kg[0], rtol=0., atol=1.e-8)
    assert trace.finite_inventory_ids[reservoir.node_id] == reservoir.identifier
    assert trace.finite_inventory_state_owner_ids[reservoir.node_id] == reservoir.state_owner_id
    assert trace.finite_inventory_evidence_ids[reservoir.node_id] == reservoir.state_evidence_id
    assert trace.finite_inventory_clock_ids[reservoir.node_id] == reservoir.clock_id
    assert trace.finite_inventory_origins[reservoir.node_id] == reservoir.origin
    assert trace.node_state_owner_ids[reservoir.node_id] == reservoir.state_owner_id
    assert set(trace.edge_geometry_evidence_ids) == {edge.identifier for edge in edges}
    return ValidationOutcome(True, {
        "reservoir_id": reservoir.identifier,
        "endpoint_node_id": reservoir.node_id,
        "finite_reservoir_mass_kg": trace.finite_inventory_mass_kg[reservoir.node_id].tolist(),
        "finite_reservoir_pressure_pa": trace.finite_inventory_pressure_pa[reservoir.node_id].tolist(),
        "combined_pipe_and_reservoir_mass_kg": trace.total_mass_kg.tolist(),
        "combined_mass_residual_kg": trace.global_mass_balance_residual_kg.tolist(),
        "owner_id": reservoir.state_owner_id,
        "evidence_id": reservoir.state_evidence_id,
        "clock_id": reservoir.clock_id,
        "eos_identity": eos.identity,
        "origin": str(reservoir.origin),
    }, ("Synthetic finite-inventory/network coupling contract only; not vessel validation.",))


def validate_contract_rejections(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    rejected = {}
    model, _nodes, _edges, _eos, reservoir, pressure, velocity = _fixture()
    try:
        model.simulate(initial_pressure_pa=pressure, initial_velocity_m_s=velocity,
            time_samples_s=(0., .001),
            finite_reservoirs={reservoir.node_id: replace(reservoir, state_owner_id="wrong-owner")})
    except ValueError as error:
        if "owner" not in str(error):
            raise AssertionError("Owner/evidence mismatch rejected for an unrelated reason") from error
        rejected["owner_evidence"] = True
    else:
        raise AssertionError("Mismatched finite-reservoir owner was accepted")
    for label, update in (
        ("clock", {"clock_id": "wrong-clock"}),
        ("eos", {"eos_identity": "wrong-eos"}),
        ("temperature", {"temperature_k": 301.}),
    ):
        invalid = replace(reservoir, **update)
        try:
            model.simulate(initial_pressure_pa=pressure, initial_velocity_m_s=velocity,
                time_samples_s=(0., .001), finite_reservoirs={reservoir.node_id: invalid})
        except ValueError:
            rejected[label] = True
        else:
            raise AssertionError(f"Finite reservoir {label} mismatch was accepted")
    try:
        model.simulate(initial_pressure_pa=pressure, initial_velocity_m_s=velocity,
            time_samples_s=(0., .001), finite_reservoirs={})
    except ValueError as error:
        if "cover every finite_reservoir node" not in str(error):
            raise AssertionError("Missing inventory record rejected for an unrelated reason") from error
        rejected["missing_record"] = True
    else:
        raise AssertionError("Missing finite-inventory node record was accepted")
    try:
        replace(reservoir, mass_kg=reservoir.minimum_mass_kg)
    except ValueError:
        rejected["depleted_initial_inventory"] = True
    else:
        raise AssertionError("Inventory at/below its strict floor was accepted")
    assert set(rejected) == {"owner_evidence", "clock", "eos", "temperature", "missing_record",
                            "depleted_initial_inventory"}
    return ValidationOutcome(True, {
        "rejected_contracts": rejected,
        "reservoir_id": reservoir.identifier,
        "node_id": reservoir.node_id,
        "clock_id": reservoir.clock_id,
        "eos_identity": reservoir.eos_identity,
    }, ("Synthetic identity/domain rejection contracts only; no flow clipping.",))
