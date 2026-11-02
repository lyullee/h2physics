"""Unexecuted flowing heat-exchanger admission sketch."""

from dataclasses import replace

from h2physics.adapters.lh2dt_flowing_heat_exchanger import (
    FlowingHeatExchangerAdmission,
    FlowingHeatExchangerSide,
)
from h2physics.equipment import BoundaryPower, ConnectionTransfer


def bind_example(model, trace):
    """Bind synthetic process transfers supplied by an existing flow owner."""
    point = trace.points[-1]
    sides = []
    for index, side_id in enumerate((model.left.side_id, model.right.side_id)):
        inlet = point.sides[side_id].fluid
        heat_w = 100.0 if index == 0 else -100.0
        mass_flow = 0.01
        outlet = replace(inlet, pressure_pa=inlet.pressure_pa-1000.0,
                         enthalpy_j_kg=inlet.enthalpy_j_kg+heat_w/mass_flow)
        transfer = ConnectionTransfer(
            f"hx:{side_id}", f"{side_id}:in", f"{side_id}:out",
            f"{side_id}:inlet", f"{side_id}:outlet", mass_flow,
            inlet, outlet, BoundaryPower(heat_w=heat_w), 0.0, True,
        )
        sides.append(FlowingHeatExchangerSide(
            side_id, transfer, 1000.0, "caller-pressure-loss", "caller-flow-owner"))
    owner = FlowingHeatExchangerAdmission(model, equipment_id="flowing-hx")
    return owner, sides


# Deferred until Nurion after an original native trace exists:
# owner, sides = bind_example(model, trace)
# result = owner.bind(trace, trace_point_index=-1, left=sides[0], right=sides[1])
