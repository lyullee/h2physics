"""Exact hydrogen-species mixing for fixed-state well-mixed room networks.

Each interval uses caller-prescribed molar-transfer rates. The model solves
the linear species balance exactly while each compartment's total molar stock
is held fixed by a balanced total throughflow schedule. It does not compute the
flow field or compartment pressure/temperature response.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from math import isclose

import numpy as np
from scipy.linalg import expm

from .core import finite, immutable_array

_R_J_MOL_K = 8.31446261815324
_ISSUED_TRACES: set[object] = set()


def _nonempty(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label}")
    return value.strip()


@dataclass(frozen=True, slots=True)
class WellMixedCompartment:
    """Fixed-volume ideal-gas room with caller-owned constant P/T state."""

    identifier: str
    volume_m3: float
    absolute_pressure_pa: float
    temperature_k: float
    initial_hydrogen_mole_fraction: float
    state_owner_id: str
    state_evidence_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", _nonempty(self.identifier, "compartment identifier"))
        for name in ("state_owner_id", "state_evidence_id"):
            object.__setattr__(self, name, _nonempty(getattr(self, name), name))
        for name in ("volume_m3", "absolute_pressure_pa", "temperature_k"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        fraction = finite(self.initial_hydrogen_mole_fraction, "initial hydrogen mole fraction")
        if not 0. <= fraction <= 1.:
            raise ValueError("Initial hydrogen mole fraction must lie in [0, 1]")
        object.__setattr__(self, "initial_hydrogen_mole_fraction", fraction)

    @property
    def total_moles(self) -> float:
        return finite(
            self.absolute_pressure_pa * self.volume_m3 / (_R_J_MOL_K * self.temperature_k),
            "fixed compartment total moles", positive=True,
        )


@dataclass(frozen=True, slots=True)
class CompartmentMolarTransfer:
    """One direction of a caller-prescribed piecewise-constant molar stream.

    A missing source denotes an external inlet and requires its hydrogen mole
    fraction. A missing destination denotes discharge to the exterior. Both
    endpoints may be internal for inter-compartment transfer.
    """

    identifier: str
    source_compartment_id: str | None
    destination_compartment_id: str | None
    molar_flow_mol_s: tuple[float, ...]
    state_owner_id: str
    state_evidence_id: str
    clock_id: str
    external_hydrogen_mole_fraction: float | None = None

    def __post_init__(self) -> None:
        for name in ("identifier", "state_owner_id", "state_evidence_id", "clock_id"):
            object.__setattr__(self, name, _nonempty(getattr(self, name), name))
        if self.source_compartment_id is None and self.destination_compartment_id is None:
            raise ValueError("A stream must touch at least one compartment")
        if self.source_compartment_id is not None:
            object.__setattr__(self, "source_compartment_id",
                               _nonempty(self.source_compartment_id, "source compartment ID"))
        if self.destination_compartment_id is not None:
            object.__setattr__(self, "destination_compartment_id",
                               _nonempty(self.destination_compartment_id, "destination compartment ID"))
        if (self.source_compartment_id is not None and self.destination_compartment_id is not None
                and self.source_compartment_id == self.destination_compartment_id):
            raise ValueError("A stream cannot begin and end in the same compartment")
        try:
            values = tuple(finite(value, "molar flow") for value in self.molar_flow_mol_s)
        except TypeError as error:
            raise ValueError("molar_flow_mol_s must be a finite sequence") from error
        if not values or any(value < 0. for value in values):
            raise ValueError("Molar-flow schedule must be nonempty and nonnegative")
        object.__setattr__(self, "molar_flow_mol_s", values)
        fraction = self.external_hydrogen_mole_fraction
        if self.source_compartment_id is None:
            if fraction is None:
                raise ValueError("External inlet must declare its hydrogen mole fraction")
            fraction = finite(fraction, "external hydrogen mole fraction")
            if not 0. <= fraction <= 1.:
                raise ValueError("External hydrogen mole fraction must lie in [0, 1]")
            object.__setattr__(self, "external_hydrogen_mole_fraction", fraction)
        elif fraction is not None:
            raise ValueError("Only an external inlet may declare a hydrogen source fraction")


@dataclass(frozen=True, slots=True)
class CompartmentNetworkModel:
    """Fixed-state compartment set and its explicitly scheduled stream graph."""

    compartments: tuple[WellMixedCompartment, ...]
    transfers: tuple[CompartmentMolarTransfer, ...]
    clock_id: str
    flow_balance_rtol: float = 1.e-9
    flow_balance_atol_mol_s: float = 1.e-12

    def __post_init__(self) -> None:
        object.__setattr__(self, "clock_id", _nonempty(self.clock_id, "network clock ID"))
        compartments, transfers = tuple(self.compartments), tuple(self.transfers)
        if not compartments or any(type(item) is not WellMixedCompartment for item in compartments):
            raise TypeError("Supply at least one WellMixedCompartment")
        if any(type(item) is not CompartmentMolarTransfer for item in transfers):
            raise TypeError("Every transfer must be a CompartmentMolarTransfer")
        identifiers = [item.identifier for item in compartments]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Compartment identifiers must be unique")
        for transfer in transfers:
            if transfer.clock_id != self.clock_id:
                raise ValueError("Every stream and compartment network must share the same clock ID")
            for endpoint in (transfer.source_compartment_id, transfer.destination_compartment_id):
                if endpoint is not None and endpoint not in identifiers:
                    raise ValueError(f"Unknown compartment endpoint {endpoint!r}")
        if len({transfer.identifier for transfer in transfers}) != len(transfers):
            raise ValueError("Transfer identifiers must be unique")
        rtol = finite(self.flow_balance_rtol, "flow balance relative tolerance")
        atol = finite(self.flow_balance_atol_mol_s, "flow balance absolute tolerance")
        if rtol < 0. or atol < 0.:
            raise ValueError("Flow-balance tolerances must be nonnegative")
        object.__setattr__(self, "compartments", compartments)
        object.__setattr__(self, "transfers", transfers)
        object.__setattr__(self, "flow_balance_rtol", rtol)
        object.__setattr__(self, "flow_balance_atol_mol_s", atol)


@dataclass(frozen=True, slots=True)
class HydrogenCompartmentNetworkTrace:
    """Run-issued H2 mole fractions and whole-network species ledger."""

    time_s: np.ndarray = field(repr=False, compare=False)
    hydrogen_mole_fraction: np.ndarray = field(repr=False, compare=False)
    cumulative_external_hydrogen_in_mol: np.ndarray = field(repr=False, compare=False)
    cumulative_external_hydrogen_out_mol: np.ndarray = field(repr=False, compare=False)
    hydrogen_balance_residual_mol: np.ndarray = field(repr=False, compare=False)
    cumulative_external_carrier_in_mol: np.ndarray = field(repr=False, compare=False)
    cumulative_external_carrier_out_mol: np.ndarray = field(repr=False, compare=False)
    carrier_balance_residual_mol: np.ndarray = field(repr=False, compare=False)
    model: CompartmentNetworkModel = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer not in _ISSUED_TRACES:
            raise ValueError("Compartment-network traces are issued only by a completed simulation")
        _ISSUED_TRACES.remove(self._issuer)
        for name in ("time_s", "hydrogen_mole_fraction", "cumulative_external_hydrogen_in_mol",
                     "cumulative_external_hydrogen_out_mol", "hydrogen_balance_residual_mol",
                     "cumulative_external_carrier_in_mol", "cumulative_external_carrier_out_mol",
                     "carrier_balance_residual_mol"):
            object.__setattr__(self, name, immutable_array(getattr(self, name), dtype=float, name=name))
        n_time, n_rooms = len(self.time_s), len(self.model.compartments)
        if (self.time_s.shape != (n_time,) or n_time < 2 or self.time_s[0] != 0.
                or not np.all(np.isfinite(self.time_s)) or np.any(np.diff(self.time_s) <= 0.)):
            raise ValueError("Trace time must start at zero and increase strictly")
        if (self.hydrogen_mole_fraction.shape != (n_time, n_rooms)
                or not np.all(np.isfinite(self.hydrogen_mole_fraction))
                or np.any(self.hydrogen_mole_fraction < 0.)
                or np.any(self.hydrogen_mole_fraction > 1.)):
            raise ValueError("Trace species fractions are outside their physical range")
        for name in ("cumulative_external_hydrogen_in_mol", "cumulative_external_hydrogen_out_mol",
                     "hydrogen_balance_residual_mol", "cumulative_external_carrier_in_mol",
                     "cumulative_external_carrier_out_mol", "carrier_balance_residual_mol"):
            array = getattr(self, name)
            if array.shape != (n_time,) or not np.all(np.isfinite(array)):
                raise ValueError(f"Trace {name} must be finite and align to time")
        expected = self._replay_balance()
        if not np.allclose(self.hydrogen_balance_residual_mol, expected, rtol=1.e-10, atol=1.e-10):
            raise ValueError("Trace hydrogen residual does not replay from accepted states and transfers")
        expected_carrier = self._replay_carrier_balance()
        if not np.allclose(self.carrier_balance_residual_mol, expected_carrier,
                           rtol=1.e-10, atol=1.e-10):
            raise ValueError("Trace carrier-gas residual does not replay from accepted states and transfers")

    def _replay_balance(self) -> np.ndarray:
        stock0 = sum(room.total_moles * room.initial_hydrogen_mole_fraction
                     for room in self.model.compartments)
        stock = self.hydrogen_mole_fraction @ np.asarray(
            [room.total_moles for room in self.model.compartments], dtype=float,
        )
        return stock - stock0 - self.cumulative_external_hydrogen_in_mol + self.cumulative_external_hydrogen_out_mol

    def _replay_carrier_balance(self) -> np.ndarray:
        inventories = np.asarray([room.total_moles for room in self.model.compartments], dtype=float)
        stock = (1. - self.hydrogen_mole_fraction) @ inventories
        stock0 = float(np.dot(1. - self.hydrogen_mole_fraction[0], inventories))
        return stock - stock0 - self.cumulative_external_carrier_in_mol + self.cumulative_external_carrier_out_mol

    @property
    def compartment_ids(self) -> tuple[str, ...]:
        return tuple(room.identifier for room in self.model.compartments)

    @property
    def hydrogen_moles(self) -> np.ndarray:
        values = self.hydrogen_mole_fraction * np.asarray(
            [room.total_moles for room in self.model.compartments], dtype=float,
        )[None, :]
        return immutable_array(values, dtype=float, name="hydrogen_moles")

    @property
    def carrier_mole_fraction(self) -> np.ndarray:
        return immutable_array(1. - self.hydrogen_mole_fraction, dtype=float,
                               name="carrier_mole_fraction")

    @property
    def carrier_moles(self) -> np.ndarray:
        values = self.carrier_mole_fraction * np.asarray(
            [room.total_moles for room in self.model.compartments], dtype=float,
        )[None, :]
        return immutable_array(values, dtype=float, name="carrier_moles")


class CompartmentNetworkExecutionError(RuntimeError):
    """Numerical failure retaining the last completed output-time prefix."""

    def __init__(self, message: str, *, failed_interval: int,
                 time_bracket_s: tuple[float, float],
                 accepted_prefix: HydrogenCompartmentNetworkTrace | None):
        super().__init__(message)
        self.failed_interval = failed_interval
        self.time_bracket_s = time_bracket_s
        self.accepted_prefix = accepted_prefix


def simulate_hydrogen_compartment_network(
    model: CompartmentNetworkModel,
    *,
    time_samples_s: Sequence[float],
) -> HydrogenCompartmentNetworkTrace:
    """Solve exact well-mixed H2 transport over piecewise-constant flow steps.

    Per-room total inflow and outflow must balance on every interval, retaining
    fixed room pressure and temperature. The species ODE uses an augmented
    matrix exponential, so transport and external H2 ledgers share the exact
    same accepted piecewise-constant flow schedule.
    """
    if type(model) is not CompartmentNetworkModel:
        raise TypeError("model must be CompartmentNetworkModel")
    times = np.asarray(time_samples_s, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or times[0] != 0.
            or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0.)):
        raise ValueError("time_samples_s must start at zero and increase strictly")
    n_room, n_interval = len(model.compartments), len(times) - 1
    if any(len(stream.molar_flow_mol_s) != n_interval for stream in model.transfers):
        raise ValueError("Every stream schedule must have one value per time interval")
    index = {room.identifier: i for i, room in enumerate(model.compartments)}
    inventories = np.asarray([room.total_moles for room in model.compartments], dtype=float)
    x = np.empty((len(times), n_room), dtype=float)
    x[0] = [room.initial_hydrogen_mole_fraction for room in model.compartments]
    h2_in = np.zeros(len(times))
    h2_out = np.zeros(len(times))
    carrier_in = np.zeros(len(times))
    carrier_out = np.zeros(len(times))
    for k, (t0, t1) in enumerate(zip(times[:-1], times[1:], strict=True)):
        incoming = np.zeros(n_room)
        outgoing = np.zeros(n_room)
        for stream in model.transfers:
            flow = stream.molar_flow_mol_s[k]
            if stream.source_compartment_id is not None:
                outgoing[index[stream.source_compartment_id]] += flow
            if stream.destination_compartment_id is not None:
                incoming[index[stream.destination_compartment_id]] += flow
        for room_i, room in enumerate(model.compartments):
            if not isclose(incoming[room_i], outgoing[room_i],
                           rel_tol=model.flow_balance_rtol, abs_tol=model.flow_balance_atol_mol_s):
                raise ValueError(f"Molar inflow/outflow do not balance for {room.identifier!r} at interval {k}")

    def issue_trace(trace_times, h2_fraction, h_in, h_out, c_in, c_out, trace_model):
        initial_h2 = float(np.dot(h2_fraction[0], inventories))
        h2_stock = h2_fraction @ inventories
        h2_residual = h2_stock - initial_h2 - h_in + h_out
        carrier_fraction = 1. - h2_fraction
        initial_carrier = float(np.dot(carrier_fraction[0], inventories))
        carrier_stock = carrier_fraction @ inventories
        carrier_residual = carrier_stock - initial_carrier - c_in + c_out
        token = object()
        _ISSUED_TRACES.add(token)
        try:
            return HydrogenCompartmentNetworkTrace(
                trace_times, h2_fraction, h_in, h_out, h2_residual,
                c_in, c_out, carrier_residual, trace_model, _issuer=token,
            )
        except Exception:
            _ISSUED_TRACES.discard(token)
            raise

    def raise_prefix_failure(error, interval, start_s, end_s):
        accepted = None
        if interval:
            prefix_model = replace(
                model,
                transfers=tuple(replace(stream, molar_flow_mol_s=stream.molar_flow_mol_s[:interval])
                                for stream in model.transfers),
            )
            accepted = issue_trace(times[:interval + 1], x[:interval + 1],
                                   h2_in[:interval + 1], h2_out[:interval + 1],
                                   carrier_in[:interval + 1], carrier_out[:interval + 1],
                                   prefix_model)
        raise CompartmentNetworkExecutionError(
            f"Compartment network failed at interval {interval}; completed prefix retained",
            failed_interval=interval, time_bracket_s=(float(start_s), float(end_s)),
            accepted_prefix=accepted,
        ) from error

    for k, (t0, t1) in enumerate(zip(times[:-1], times[1:], strict=True)):
        interval_duration = float(t1 - t0)
        maximum_float = np.finfo(float).max
        for stream in model.transfers:
            flow = stream.molar_flow_mol_s[k]
            if ((stream.source_compartment_id is None or stream.destination_compartment_id is None)
                    and flow > maximum_float / interval_duration):
                raise_prefix_failure(OverflowError("External species ledger would overflow"), k, t0, t1)
        generator = np.zeros((n_room + 5, n_room + 5), dtype=float)
        for stream in model.transfers:
            flow = stream.molar_flow_mol_s[k]
            source = None if stream.source_compartment_id is None else index[stream.source_compartment_id]
            destination = None if stream.destination_compartment_id is None else index[stream.destination_compartment_id]
            if source is not None:
                generator[source, source] -= flow / inventories[source]
            if destination is not None:
                if source is None:
                    generator[destination, n_room] += (
                        flow * stream.external_hydrogen_mole_fraction / inventories[destination]
                    )
                    generator[n_room + 1, n_room] += flow * stream.external_hydrogen_mole_fraction
                    generator[n_room + 3, n_room] += flow * (1. - stream.external_hydrogen_mole_fraction)
                else:
                    generator[destination, source] += flow / inventories[destination]
            elif source is not None:
                generator[n_room + 2, source] += flow
                generator[n_room + 4, n_room] += flow
                generator[n_room + 4, source] -= flow
        if not np.all(np.isfinite(generator)):
            raise_prefix_failure(FloatingPointError("Nonfinite species generator"), k, t0, t1)
        if not np.all(np.isfinite(generator * interval_duration)):
            raise_prefix_failure(FloatingPointError("Nonfinite interval evolution matrix"), k, t0, t1)
        augmented_state = np.concatenate((x[k], [1., h2_in[k], h2_out[k], carrier_in[k], carrier_out[k]]))
        try:
            advanced = expm(generator * interval_duration) @ augmented_state
            if not np.all(np.isfinite(advanced)):
                raise FloatingPointError("Matrix exponential produced a nonfinite species state")
            if np.any(advanced[:n_room] < 0.) or np.any(advanced[:n_room] > 1.):
                raise FloatingPointError("Matrix exponential produced a negative or super-unity H2 fraction")
            if np.any(advanced[n_room + 1:] < 0.):
                raise FloatingPointError("Matrix exponential produced a negative species ledger")
            x[k + 1] = advanced[:n_room]
            h2_in[k + 1], h2_out[k + 1] = advanced[n_room + 1: n_room + 3]
            carrier_in[k + 1], carrier_out[k + 1] = advanced[n_room + 3: n_room + 5]
        except Exception as error:
            raise_prefix_failure(error, k, t0, t1)
    return issue_trace(times, x, h2_in, h2_out, carrier_in, carrier_out, model)


__all__ = [
    "WellMixedCompartment", "CompartmentMolarTransfer", "CompartmentNetworkModel",
    "HydrogenCompartmentNetworkTrace", "CompartmentNetworkExecutionError",
    "simulate_hydrogen_compartment_network",
]
