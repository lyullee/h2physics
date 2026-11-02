"""Run an authored-input example of a branched isothermal pipe wave network.

All pressures and geometry below are illustrative synthetic inputs. They are
not measurements, a design basis, or facility validation evidence.
"""

from __future__ import annotations

import numpy as np

from h2physics.core import Origin
from h2physics import (
    IdealHydrogenIsothermalEOS,
    IsothermalPipeNetworkEdge,
    IsothermalPipeNetworkNode,
    IsothermalPipeNetworkWaveModel,
)


def main() -> None:
    # Authored synthetic locations and evidence IDs make the example's
    # provenance explicit; they do not stand in for surveyed facility data.
    nodes = (
        IsothermalPipeNetworkNode(
            identifier="junction",
            coordinates_m=(0.0, 0.0, 0.0),
            kind="junction",
            state_owner_id="example-authored-initial-state",
            evidence_id="example-synthetic-junction-state-v1",
            origin=Origin.SYNTHETIC,
            pressure_bounds_pa=(1.5e6, 2.6e6),
        ),
        IsothermalPipeNetworkNode(
            identifier="branch_a_end",
            coordinates_m=(-12.0, 0.0, 0.0),
            kind="closed",
            state_owner_id="example-authored-initial-state",
            evidence_id="example-synthetic-closed-end-a-v1",
            origin=Origin.SYNTHETIC,
        ),
        IsothermalPipeNetworkNode(
            identifier="branch_b_end",
            coordinates_m=(12.0, 0.0, 0.0),
            kind="closed",
            state_owner_id="example-authored-initial-state",
            evidence_id="example-synthetic-closed-end-b-v1",
            origin=Origin.SYNTHETIC,
        ),
        IsothermalPipeNetworkNode(
            identifier="branch_c_end",
            coordinates_m=(0.0, 12.0, 0.0),
            kind="closed",
            state_owner_id="example-authored-initial-state",
            evidence_id="example-synthetic-closed-end-c-v1",
            origin=Origin.SYNTHETIC,
        ),
    )
    edges = (
        IsothermalPipeNetworkEdge(
            identifier="branch_a",
            start_node_id="branch_a_end",
            end_node_id="junction",
            length_m=12.0,
            internal_diameter_m=0.08,
            cell_count=6,
            geometry_owner_id="example-authored-geometry",
            geometry_evidence_id="example-synthetic-branch-a-geometry-v1",
            darcy_friction_factor=0.02,
            origin=Origin.SYNTHETIC,
        ),
        IsothermalPipeNetworkEdge(
            identifier="branch_b",
            start_node_id="branch_b_end",
            end_node_id="junction",
            length_m=12.0,
            internal_diameter_m=0.08,
            cell_count=6,
            geometry_owner_id="example-authored-geometry",
            geometry_evidence_id="example-synthetic-branch-b-geometry-v1",
            darcy_friction_factor=0.02,
            origin=Origin.SYNTHETIC,
        ),
        IsothermalPipeNetworkEdge(
            identifier="branch_c",
            start_node_id="branch_c_end",
            end_node_id="junction",
            length_m=12.0,
            internal_diameter_m=0.08,
            cell_count=6,
            geometry_owner_id="example-authored-geometry",
            geometry_evidence_id="example-synthetic-branch-c-geometry-v1",
            darcy_friction_factor=0.02,
            origin=Origin.SYNTHETIC,
        ),
    )

    model = IsothermalPipeNetworkWaveModel(
        nodes=nodes,
        edges=edges,
        temperature_k=298.15,
        clock_id="example-relative-seconds-v1",
        eos=IdealHydrogenIsothermalEOS(),
        maximum_cfl=0.3,
    )
    cell_count = {edge.identifier: edge.cell_count for edge in edges}
    initial_pressure_pa = {
        "branch_a": np.full(cell_count["branch_a"], 2.4e6),
        "branch_b": np.full(cell_count["branch_b"], 2.0e6),
        "branch_c": np.full(cell_count["branch_c"], 1.8e6),
    }
    initial_velocity_m_s = {
        edge.identifier: np.zeros(edge.cell_count) for edge in edges
    }

    trace = model.simulate(
        initial_pressure_pa=initial_pressure_pa,
        initial_velocity_m_s=initial_velocity_m_s,
        time_samples_s=np.linspace(0.0, 0.02, 5),
    )

    print(f"Samples: {len(trace.time_s)}")
    print(f"EOS: {trace.eos_identity}")
    print(f"Final junction pressure: {trace.junction_pressure_pa['junction'][-1]:.3f} Pa")
    for edge in edges:
        pressure = trace.edge_pressure_pa[edge.identifier][-1]
        face_flow = trace.edge_face_mass_flow_kg_s[edge.identifier][-1]
        print(
            f"{edge.identifier}: final pressure range "
            f"{pressure.min():.3f}–{pressure.max():.3f} Pa; "
            f"junction-end mass flow {face_flow[-1]:.6g} kg/s"
        )
    print(
        "Maximum absolute network mass residual: "
        f"{np.max(np.abs(trace.global_mass_balance_residual_kg)):.6g} kg"
    )
    print("Synthetic demonstration only; no scientific validation is implied.")


if __name__ == "__main__":
    main()
