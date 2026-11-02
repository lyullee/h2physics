"""Expose accepted synchronized fuel-cell coolant energy in HeatDuty form."""

from __future__ import annotations

import numpy as np

from .thermal_utilities import HeatComponent, HeatDuty, HeatSnapshot, HeatWindow


class CanteraFuelCellCoolantHeatAdapter:
    """Read the original signed cumulative coolant-energy ledger only."""

    identifier = "cantera-synchronized-fuel-cell-coolant-boundary-duty"

    def snapshot(self, source, window: HeatWindow) -> HeatSnapshot:
        from .cantera_fuel_cell import CanteraFuelCellTrace

        if type(source) is not CanteraFuelCellTrace:
            raise TypeError("Use an accepted synchronized native CanteraFuelCellTrace")
        if type(window) is not HeatWindow:
            raise TypeError("Use an explicit physical-seconds HeatWindow")
        source.require_current()
        if window.clock_id != source.clock_id:
            raise ValueError("Thermal reporting and fuel-cell clocks must match exactly")
        times = np.asarray([point.time_s for point in source.accepted], dtype=float)
        starts, ends = np.flatnonzero(times == window.start_s), np.flatnonzero(times == window.end_s)
        if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
            raise ValueError("Select increasing exact accepted fuel-cell output times")
        lo, hi = int(starts[0]), int(ends[0])
        points = source.accepted[lo:hi + 1]
        edges = times[lo:hi + 1]
        cumulative = np.asarray([point.stack_coolant_energy_into_j for point in points], dtype=float)
        if (len(edges) < 2 or cumulative.shape != edges.shape
                or not np.all(np.isfinite(cumulative)) or np.any(np.diff(edges) <= 0.)):
            raise ValueError("Accepted coolant-energy ledger must be finite on its ordered source clock")
        heat = np.diff(cumulative)
        coolant_k = source.thermal.coolant_temperature_k
        temperatures = tuple((coolant_k, coolant_k) for _ in heat)
        result = HeatSnapshot(
            source, window, source.run_evidence_id,
            "fuel-cell-stack-coolant:" + source.thermal.boundary_evidence_id,
            "Cantera-native-stack-sensible-energy:" + source.thermal.energy_reference_id,
            edges, heat,
            (HeatComponent(source.native.connection, "stack-coolant-boundary"),),
            temperatures, "external-device-heat",
            (window.evidence_id, source.run_evidence_id,
             source.thermal.boundary_evidence_id),
            (source, source.native, source.native.network, source.native.connection, *points),
            "accepted signed cumulative heat into the fuel-cell stack from its prescribed coolant boundary; no utility recovery inferred",
        )
        source.require_current()
        return result


def bind_cantera_fuel_cell_coolant_heat(source, window: HeatWindow) -> HeatDuty:
    """Create one source-bound signed coolant boundary duty snapshot."""
    return HeatDuty.bind(source, CanteraFuelCellCoolantHeatAdapter(), window)
