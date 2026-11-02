"""Lumped finite-capacity pipe wall coupled to the caloric Euler gas solver.

The gas solver is reused unchanged. A caller-selected outer clock freezes wall
temperature during each gas segment, then advances the wall from the exact gas
heat ledger and optional ambient conductance. This is a first-order split model.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .caloric_pipe_waves import (
    CaloricPipeWallHeatBoundary,
    CaloricPipeWaveModel,
    CaloricPipeWaveTrace,
)
from .core import finite, immutable_array

_ISSUED_FINITE_WALL_TRACES: set[object] = set()


def _issue_trace(**values):
    token = object()
    _ISSUED_FINITE_WALL_TRACES.add(token)
    try:
        return FiniteWallCaloricPipeTrace(**values, _issuer_token=token)
    except Exception:
        _ISSUED_FINITE_WALL_TRACES.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class LumpedPipeWall:
    """One perfectly mixed wall node representing the whole modeled pipe.

    ``heat_capacity_j_k`` is total wall heat capacity, not volumetric capacity.
    Optional ambient exchange uses a caller-supplied total UA in W/K.
    """

    identifier: str
    state_owner_id: str
    state_evidence_id: str
    clock_id: str
    initial_temperature_k: float
    heat_capacity_j_k: float
    gas_heat_transfer_coefficient_w_m2_k: float
    ambient_temperature_k: float | None = None
    ambient_ua_w_k: float = 0.0
    ambient_evidence_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("identifier", "state_owner_id", "state_evidence_id", "clock_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare finite wall {name}")
        object.__setattr__(self, "initial_temperature_k",
                           finite(self.initial_temperature_k, "initial_temperature_k", positive=True))
        object.__setattr__(self, "heat_capacity_j_k",
                           finite(self.heat_capacity_j_k, "heat_capacity_j_k", positive=True))
        h = finite(self.gas_heat_transfer_coefficient_w_m2_k,
                   "gas_heat_transfer_coefficient_w_m2_k")
        ua = finite(self.ambient_ua_w_k, "ambient_ua_w_k")
        if h < 0. or ua < 0.:
            raise ValueError("Heat-transfer coefficients must be nonnegative")
        object.__setattr__(self, "gas_heat_transfer_coefficient_w_m2_k", h)
        object.__setattr__(self, "ambient_ua_w_k", ua)
        if (self.ambient_temperature_k is None) != (self.ambient_evidence_id is None):
            raise ValueError("Ambient temperature and evidence must be declared together")
        if ua > 0. and self.ambient_temperature_k is None:
            raise ValueError("Positive ambient UA requires ambient state and evidence")
        if self.ambient_temperature_k is not None:
            object.__setattr__(self, "ambient_temperature_k",
                               finite(self.ambient_temperature_k, "ambient_temperature_k", positive=True))
            if not isinstance(self.ambient_evidence_id, str) or not self.ambient_evidence_id.strip():
                raise ValueError("Declare ambient_evidence_id")


@dataclass(frozen=True, slots=True)
class FiniteWallCaloricPipeTrace:
    """Outer-clock wall states and the underlying accepted gas segment traces."""

    time_s: np.ndarray = field(repr=False, compare=False)
    wall_temperature_k: np.ndarray = field(repr=False, compare=False)
    cumulative_wall_energy_change_j: np.ndarray = field(repr=False, compare=False)
    cumulative_gas_wall_heat_into_gas_j: np.ndarray = field(repr=False, compare=False)
    cumulative_ambient_heat_into_wall_j: np.ndarray = field(repr=False, compare=False)
    combined_energy_balance_residual_j: np.ndarray = field(repr=False, compare=False)
    gas_traces: tuple[CaloricPipeWaveTrace, ...]
    wall: LumpedPipeWall
    clock_id: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer_token not in _ISSUED_FINITE_WALL_TRACES:
            raise ValueError("Finite-wall traces are issued only by a completed coupled run")
        _ISSUED_FINITE_WALL_TRACES.remove(self._issuer_token)
        for name in ("time_s", "wall_temperature_k", "cumulative_wall_energy_change_j",
                     "cumulative_gas_wall_heat_into_gas_j", "cumulative_ambient_heat_into_wall_j",
                     "combined_energy_balance_residual_j"):
            arr = immutable_array(getattr(self, name), dtype=float, name=name)
            object.__setattr__(self, name, arr)
        n = len(self.time_s)
        if (n < 2 or self.time_s.shape != (n,) or self.time_s[0] != 0.
                or np.any(np.diff(self.time_s) <= 0.) or not np.all(np.isfinite(self.time_s))):
            raise ValueError("Outer time samples must start at zero and strictly increase")
        for name in ("wall_temperature_k", "cumulative_wall_energy_change_j",
                     "cumulative_gas_wall_heat_into_gas_j", "cumulative_ambient_heat_into_wall_j",
                     "combined_energy_balance_residual_j"):
            if getattr(self, name).shape != (n,) or not np.all(np.isfinite(getattr(self, name))):
                raise ValueError(f"{name} must be finite and align to outer time")
        if np.any(self.wall_temperature_k <= 0.) or len(self.gas_traces) != n - 1:
            raise ValueError("Wall states must remain positive and one gas trace is required per interval")
        if self.clock_id != self.wall.clock_id:
            raise ValueError("Trace clock differs from finite-wall clock")
        expected_q_gas = np.zeros(n)
        expected_q_ambient = np.zeros(n)
        expected_wall_t = np.empty(n)
        expected_wall_t[0] = self.wall.initial_temperature_k
        boundary_energy = np.zeros(n)
        gas_energy_change = np.zeros(n)
        for i, (start, end, gas_trace) in enumerate(
                zip(self.time_s[:-1], self.time_s[1:], self.gas_traces, strict=True)):
            if type(gas_trace) is not CaloricPipeWaveTrace or gas_trace.clock_id != self.clock_id:
                raise ValueError("Each outer interval must retain a compatible issued caloric gas trace")
            if (gas_trace.time_s[0] != 0.
                    or not np.isclose(gas_trace.time_s[-1], end - start, rtol=1.e-12, atol=1.e-15)):
                raise ValueError("Inner gas trace must span its outer interval on its local clock")
            if (gas_trace.wall_heat_boundary_id != self.wall.identifier
                    or gas_trace.wall_heat_state_owner_id != self.wall.state_owner_id
                    or gas_trace.wall_heat_evidence_id != self.wall.state_evidence_id
                    or gas_trace.heat_transfer_coefficient_w_m2_k
                    != self.wall.gas_heat_transfer_coefficient_w_m2_k
                    or not np.isclose(gas_trace.wall_temperature_k, expected_wall_t[i], rtol=1.e-12, atol=1.e-12)):
                raise ValueError("Gas segment wall boundary must match the issued finite-wall state and evidence")
            if i and (gas_trace.eos_identity != self.gas_traces[0].eos_identity
                      or gas_trace.pipe_length_m != self.gas_traces[0].pipe_length_m
                      or gas_trace.internal_diameter_m != self.gas_traces[0].internal_diameter_m
                      or gas_trace.cell_center_m.shape != self.gas_traces[0].cell_center_m.shape
                      or not np.array_equal(gas_trace.cell_center_m, self.gas_traces[0].cell_center_m)):
                raise ValueError("All gas segments must retain identical EOS identity and pipe geometry")
            if i and any(not np.allclose(current[0], previous[-1], rtol=2.e-10, atol=1.e-9)
                         for current, previous in (
                             (gas_trace.pressure_pa, self.gas_traces[i - 1].pressure_pa),
                             (gas_trace.temperature_k, self.gas_traces[i - 1].temperature_k),
                             (gas_trace.velocity_m_s, self.gas_traces[i - 1].velocity_m_s),
                         )):
                raise ValueError("Adjacent gas traces must join continuously at outer-clock boundaries")
            q_gas = float(gas_trace.cumulative_wall_heat_in_j[-1])
            expected_q_gas[i + 1] = expected_q_gas[i] + q_gas
            after_gas = expected_wall_t[i] - q_gas / self.wall.heat_capacity_j_k
            if self.wall.ambient_ua_w_k > 0.:
                tau = self.wall.heat_capacity_j_k / self.wall.ambient_ua_w_k
                next_t = self.wall.ambient_temperature_k + (after_gas - self.wall.ambient_temperature_k) * np.exp(-(end-start)/tau)
            else:
                next_t = after_gas
            ambient = self.wall.heat_capacity_j_k * (next_t - after_gas)
            expected_wall_t[i + 1] = next_t
            expected_q_ambient[i + 1] = expected_q_ambient[i] + ambient
            boundary_energy[i + 1] = boundary_energy[i] + gas_trace.cumulative_boundary_energy_in_j[-1]
            gas_energy_change[i + 1] = gas_energy_change[i] + gas_trace.total_energy_j[-1] - gas_trace.total_energy_j[0]
        expected_wall_du = self.wall.heat_capacity_j_k * (expected_wall_t - self.wall.initial_temperature_k)
        expected_residual = gas_energy_change + expected_wall_du - boundary_energy - expected_q_ambient
        for name, actual, expected in (
            ("wall_temperature_k", self.wall_temperature_k, expected_wall_t),
            ("cumulative_wall_energy_change_j", self.cumulative_wall_energy_change_j, expected_wall_du),
            ("cumulative_gas_wall_heat_into_gas_j", self.cumulative_gas_wall_heat_into_gas_j, expected_q_gas),
            ("cumulative_ambient_heat_into_wall_j", self.cumulative_ambient_heat_into_wall_j, expected_q_ambient),
            ("combined_energy_balance_residual_j", self.combined_energy_balance_residual_j, expected_residual),
        ):
            if not np.allclose(actual, expected, rtol=2.e-10, atol=1.e-8):
                raise ValueError(f"Finite-wall trace {name} does not replay from retained solver traces")


def simulate_caloric_pipe_with_finite_wall(
    model: CaloricPipeWaveModel, *, wall: LumpedPipeWall,
    initial_pressure_pa: Sequence[float], initial_temperature_k: Sequence[float],
    initial_velocity_m_s: Sequence[float], time_samples_s: Sequence[float],
    clock_id: str,
) -> FiniteWallCaloricPipeTrace:
    """Advance gas and a single lumped wall node on caller output intervals.

    Per interval, wall temperature is frozen for the existing gas integration;
    its temperature then changes by ``-Q_gas/C_wall``. Ambient exchange is
    integrated exactly for a constant ambient temperature and UA over that
    interval. Refine ``time_samples_s`` until split-step sensitivity is small.
    """
    if type(model) is not CaloricPipeWaveModel:
        raise TypeError("model must be CaloricPipeWaveModel")
    if type(wall) is not LumpedPipeWall:
        raise TypeError("wall must be LumpedPipeWall")
    if clock_id != wall.clock_id:
        raise ValueError("Wall and model run must share the same clock identity")
    times = np.asarray(time_samples_s, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or times[0] != 0.
            or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0.)):
        raise ValueError("time_samples_s must start at zero and strictly increase")
    p = np.asarray(initial_pressure_pa, dtype=float)
    t = np.asarray(initial_temperature_k, dtype=float)
    u = np.asarray(initial_velocity_m_s, dtype=float)
    if any(a.shape != (model.cell_count,) or not np.all(np.isfinite(a)) for a in (p, t, u)):
        raise ValueError("Initial gas arrays must be finite and match model.cell_count")
    if np.any(p <= 0.) or np.any(t <= 0.):
        raise ValueError("Initial gas pressure and temperature must be positive")
    wall_t = [wall.initial_temperature_k]
    wall_du = [0.]
    q_gas_cum = [0.]
    q_ambient_cum = [0.]
    combined_residual = [0.]
    traces = []
    gas_boundary_energy_cum = 0.
    for i, (start, end) in enumerate(zip(times[:-1], times[1:], strict=True)):
        boundary = CaloricPipeWallHeatBoundary(
            identifier=wall.identifier, state_owner_id=wall.state_owner_id,
            state_evidence_id=wall.state_evidence_id, clock_id=clock_id,
            wall_temperature_k=wall_t[-1],
            heat_transfer_coefficient_w_m2_k=wall.gas_heat_transfer_coefficient_w_m2_k,
        )
        trace = model.simulate(
            initial_pressure_pa=p, initial_temperature_k=t, initial_velocity_m_s=u,
            time_samples_s=(0., float(end - start)), clock_id=clock_id,
            wall_heat_boundary=boundary,
        )
        traces.append(trace)
        q_gas = float(trace.cumulative_wall_heat_in_j[-1])
        t_after_gas = wall_t[-1] - q_gas / wall.heat_capacity_j_k
        if t_after_gas <= 0. or not np.isfinite(t_after_gas):
            raise FloatingPointError("Finite wall update reached nonpositive temperature")
        if wall.ambient_ua_w_k > 0.:
            tau = wall.heat_capacity_j_k / wall.ambient_ua_w_k
            t_next = wall.ambient_temperature_k + (t_after_gas - wall.ambient_temperature_k) * np.exp(-(end-start)/tau)
        else:
            t_next = t_after_gas
        if t_next <= 0. or not np.isfinite(t_next):
            raise FloatingPointError("Ambient wall update reached nonpositive temperature")
        q_ambient = wall.heat_capacity_j_k * (t_next - t_after_gas)
        gas_boundary_energy_cum += float(trace.cumulative_boundary_energy_in_j[-1])
        # Recompute cumulative whole-system residual from gas and wall changes.
        cumulative_gas_delta = sum(float(x.total_energy_j[-1] - x.total_energy_j[0]) for x in traces)
        combined = (cumulative_gas_delta
                    + wall.heat_capacity_j_k * (t_next - wall.initial_temperature_k)
                    - gas_boundary_energy_cum - (q_ambient_cum[-1] + q_ambient))
        wall_t.append(float(t_next))
        wall_du.append(float(wall.heat_capacity_j_k * (t_next - wall.initial_temperature_k)))
        q_gas_cum.append(q_gas_cum[-1] + q_gas)
        q_ambient_cum.append(q_ambient_cum[-1] + q_ambient)
        combined_residual.append(float(combined))
        p, t, u = trace.pressure_pa[-1], trace.temperature_k[-1], trace.velocity_m_s[-1]
    return _issue_trace(
        time_s=times, wall_temperature_k=np.asarray(wall_t),
        cumulative_wall_energy_change_j=np.asarray(wall_du),
        cumulative_gas_wall_heat_into_gas_j=np.asarray(q_gas_cum),
        cumulative_ambient_heat_into_wall_j=np.asarray(q_ambient_cum),
        combined_energy_balance_residual_j=np.asarray(combined_residual),
        gas_traces=tuple(traces), wall=wall, clock_id=clock_id,
    )
