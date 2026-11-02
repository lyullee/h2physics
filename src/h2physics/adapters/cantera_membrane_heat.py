"""Source-bound thermal duty view of a finite Cantera membrane trace.

This exposes only the two imposed thermostat ledgers already integrated by the
native model. It does not infer recoverable heat, utility capacity, or a heat
exchanger between the sides.
"""

from dataclasses import dataclass

import numpy as np

from .thermal_utilities import HeatComponent, HeatSnapshot, HeatWindow


@dataclass(frozen=True, slots=True)
class CanteraMembraneThermostatHeatAdapter:
    side: str

    def __post_init__(self):
        if self.side not in {"left", "right"}:
            raise ValueError("Select exactly one original finite-side thermostat")

    @property
    def identifier(self):
        return "native-finite-membrane-" + self.side + "-thermostat-duty"

    def snapshot(self, source, window: HeatWindow) -> HeatSnapshot:
        from .cantera_membrane_device import FiniteMembraneTrace

        if type(source) is not FiniteMembraneTrace:
            raise TypeError("Use the original finite Cantera membrane trace")
        if type(window) is not HeatWindow:
            raise TypeError("Use an explicit thermal reporting window")
        self._require_current(source)
        if window.clock_id != source.parameters.clock_id:
            raise ValueError("Heat window and native membrane clocks differ")
        times = np.asarray(source.time_s, dtype=float)
        starts = np.flatnonzero(times == window.start_s)
        ends = np.flatnonzero(times == window.end_s)
        if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
            raise ValueError("Select increasing exact accepted membrane output samples")
        lo, hi = int(starts[0]), int(ends[0])
        edges = times[lo:hi + 1]
        cumulative = np.asarray(source.thermostat_heat_j[lo:hi + 1], dtype=float)
        if cumulative.shape != (len(edges), 2):
            raise ValueError("Native thermostat ledger must retain both finite sides")
        heat = np.diff(cumulative, axis=0)
        if not np.all(np.isfinite(heat)) or not np.all(np.diff(edges) > 0):
            raise ValueError("Native thermostat ledger is not a finite ordered interval series")
        points = source.snapshots[lo:hi + 1]
        side_index = 0 if self.side == "left" else 1
        temps = tuple((float(points[i].sides[side_index].temperature_k),
                       float(points[i + 1].sides[side_index].temperature_k))
                      for i in range(len(points) - 1))
        p = source.parameters
        result = HeatSnapshot(
            source, window, p.source_id, "finite-membrane-thermostats:" + p.thermal_boundary_id,
            "native-cantera-thermostat-energy-j;species-order=" + ",".join(source.species),
            edges, heat[:, side_index],
            (HeatComponent(source.native, self.side + "-thermostat"),),
            temps, "external-device-heat",
            (window.evidence_id, p.source_id, p.thermal_boundary_id),
            (source, source.native, source.native.network, source.native.connection,
             *source.snapshots[lo:hi + 1]),
            "native signed thermostat energy into both prescribed-temperature gas sides; no utility availability inferred")
        self._require_current(source)
        return result

    @staticmethod
    def _require_current(source):
        native = source.native
        if len(native.reactors) != 2 or not len(source.snapshots):
            raise ValueError("Finite membrane source has no complete two-side native record")
        final = source.snapshots[-1]
        if float(native.network.time) != float(source.time_s[-1]):
            raise ValueError("Native membrane network advanced after its accepted trace")
        for reactor, accepted in zip(native.reactors, final.sides, strict=True):
            phase = reactor.phase
            if (float(reactor.mass) != float(accepted.mass_kg)
                    or float(reactor.volume) != float(accepted.volume_m3)
                    or float(phase.T) != float(accepted.temperature_k)
                    or float(phase.P) != float(accepted.pressure_pa)
                    or not np.array_equal(np.asarray(phase.Y),
                        np.asarray([accepted.mass_fractions[name] for name in source.species]))):
                raise ValueError("Native membrane terminal state changed after trace capture")


def bind_cantera_membrane_thermostat_heat(source, window):
    """Return separate left/right native signed duties in the shared API."""
    from .thermal_utilities import HeatDuty

    return tuple(HeatDuty.bind(source, CanteraMembraneThermostatHeatAdapter(side), window)
                 for side in ("left", "right"))
