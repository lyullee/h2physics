"""Three-branch network with an EOS-backed finite-inventory terminal."""

import numpy as np

from h2physics.core import Origin
from h2physics.finite_pipe_reservoir import FiniteIsothermalPipeReservoir
from h2physics.isothermal_pipe_network_waves import (
    IsothermalPipeNetworkEdge,
    IsothermalPipeNetworkNode,
    IsothermalPipeNetworkWaveModel,
)
from h2physics.isothermal_pipe_waves import IdealHydrogenIsothermalEOS


def run_example():
    eos = IdealHydrogenIsothermalEOS()
    clock = "finite-inventory-example-clock"
    temperature = 300.
    vessel_volume = .2
    vessel_pressure = 5.2e6
    inventory = eos.density_pt(vessel_pressure, temperature) * vessel_volume
    reservoir = FiniteIsothermalPipeReservoir(
        identifier="example-finite-vessel",
        node_id="finite-vessel-node",
        state_owner_id="example-vessel-owner",
        state_evidence_id="synthetic-initial-inventory",
        clock_id=clock,
        eos_identity=eos.identity,
        temperature_k=temperature,
        volume_m3=vessel_volume,
        mass_kg=inventory,
        minimum_mass_kg=.05 * inventory,
        maximum_mass_kg=2. * inventory,
        origin=Origin.SYNTHETIC,
    )
    nodes = (
        IsothermalPipeNetworkNode("junction", (0., 0., 0.), "junction",
            "junction-owner", "junction-evidence", Origin.SYNTHETIC, (4.e6, 6.e6)),
        IsothermalPipeNetworkNode("finite-vessel-node", (100., 0., 0.), "finite_reservoir",
            reservoir.state_owner_id, reservoir.state_evidence_id, Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("closed-a", (0., 100., 0.), "closed",
            "wall-owner-a", "wall-evidence-a", Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("closed-b", (-100., 0., 0.), "closed",
            "wall-owner-b", "wall-evidence-b", Origin.SYNTHETIC),
    )
    edges = (
        IsothermalPipeNetworkEdge("pipe-vessel", "junction", "finite-vessel-node",
            100., .1, 20, "geometry-owner-v", "geometry-evidence-v", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("pipe-a", "junction", "closed-a",
            100., .1, 20, "geometry-owner-a", "geometry-evidence-a", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("pipe-b", "junction", "closed-b",
            100., .1, 20, "geometry-owner-b", "geometry-evidence-b", origin=Origin.SYNTHETIC),
    )
    model = IsothermalPipeNetworkWaveModel(
        nodes, edges, temperature, clock, eos, maximum_cfl=.2)
    initial_pressure = {edge.identifier: np.full(edge.cell_count, 5.e6) for edge in edges}
    initial_velocity = {edge.identifier: np.zeros(edge.cell_count) for edge in edges}
    return model.simulate(
        initial_pressure_pa=initial_pressure,
        initial_velocity_m_s=initial_velocity,
        time_samples_s=(0., .25, .5),
        finite_reservoirs={reservoir.node_id: reservoir},
    )
