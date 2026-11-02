"""Three-branch network with caller-prescribed pressure-history terminals.

The histories are boundary inputs. This example does not evolve reservoir
inventory or infer depletion from pipe-side exchange.
"""

import numpy as np

from h2physics.core import Origin
from h2physics.isothermal_pipe_network_waves import (
    IsothermalPipeNetworkEdge, IsothermalPipeNetworkNode, IsothermalPipeNetworkWaveModel)
from h2physics.isothermal_pipe_waves import IdealHydrogenIsothermalEOS
from h2physics.pipe_reservoir_boundary import FiniteReservoirPressureBoundary


def run_example():
    eos = IdealHydrogenIsothermalEOS()
    clock = "example-network-clock"
    reservoir_a = FiniteReservoirPressureBoundary(
        "example-reservoir-a", "example-owner-a", "example-history-a", clock,
        eos.identity, 300., (0., .5, 1.), (5.1e6, 5.15e6, 5.2e6), Origin.SYNTHETIC)
    reservoir_b = FiniteReservoirPressureBoundary(
        "example-reservoir-b", "example-owner-b", "example-history-b", clock,
        eos.identity, 300., (0., .5, 1.), (4.9e6, 4.85e6, 4.8e6), Origin.SYNTHETIC)
    nodes = (
        IsothermalPipeNetworkNode("junction", (0.,0.,0.), "junction", "junction-owner",
            "junction-state", Origin.SYNTHETIC, (4.e6,6.e6)),
        IsothermalPipeNetworkNode("reservoir-a", (100.,0.,0.), "reservoir",
            reservoir_a.state_owner_id, reservoir_a.state_evidence_id, Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("reservoir-b", (0.,100.,0.), "reservoir",
            reservoir_b.state_owner_id, reservoir_b.state_evidence_id, Origin.SYNTHETIC),
        IsothermalPipeNetworkNode("closed-wall", (-100.,0.,0.), "closed", "wall-owner",
            "wall-state", Origin.SYNTHETIC),
    )
    edges = (
        IsothermalPipeNetworkEdge("pipe-a", "junction", "reservoir-a", 100., .1, 20,
            "geometry-a", "segment-a", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("pipe-b", "reservoir-b", "junction", 100., .12, 20,
            "geometry-b", "segment-b", origin=Origin.SYNTHETIC),
        IsothermalPipeNetworkEdge("pipe-c", "junction", "closed-wall", 100., .09, 20,
            "geometry-c", "segment-c", origin=Origin.SYNTHETIC),
    )
    model = IsothermalPipeNetworkWaveModel(nodes, edges, 300., clock, eos, maximum_cfl=.2)
    initial_pressure = {edge.identifier: np.full(edge.cell_count, 5.e6) for edge in edges}
    initial_velocity = {edge.identifier: np.zeros(edge.cell_count) for edge in edges}
    return model.simulate(initial_pressure_pa=initial_pressure,
        initial_velocity_m_s=initial_velocity, time_samples_s=(0., .25, .5),
        reservoir_boundaries={"reservoir-a": reservoir_a, "reservoir-b": reservoir_b})
