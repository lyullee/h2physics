"""Source-bound projection of measured hydrogen-channel flow into finite bins."""

from dataclasses import dataclass, field

import numpy as np

from ..core import Origin, ThermoState, finite
from ..data.hydrogen_channel import HydrogenChannelCase
from ..release import SourceLocation
from ..sources import IntervalMassSource

_PENDING_TOKENS: set[object] = set()


@dataclass(frozen=True, slots=True)
class HydrogenChannelFiniteSource:
    """Measured flow data projected into an existing finite safety-source API.

    This profile covers only the measured flow-clock support. Sensor-clock
    columns are not aligned, and no source values are extrapolated at either end.
    """

    case: HydrogenChannelCase
    source: IntervalMassSource
    flow_column: str
    time_column: str
    flow_rule: str
    clock_id: str
    time_s: tuple[float, ...]
    mass_flow_kg_s: tuple[float, ...]
    _token: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING_TOKENS:
            raise TypeError("Issue finite sources only through the source-bound projector")
        _PENDING_TOKENS.remove(self._token)
        object.__setattr__(self, "_binding", self._current_binding())

    def _current_binding(self):
        return (id(self.case), id(self.source), self.flow_column, self.time_column,
                self.flow_rule, self.clock_id, self.time_s, self.mass_flow_kg_s)

    @property
    def source_sha256(self):
        return self.case.source_sha256

    @property
    def member_sha256(self):
        return self.case.member_sha256

    def require_current(self):
        self.case.require_current()
        self.source.require_current()
        if self._current_binding() != self._binding:
            raise ValueError("Hydrogen-channel projection lost its original source/profile fields")
        expected_times, expected_rates = _flow_inputs(
            self.case, self.time_column, self.flow_column,
        )
        expected_mass = _interval_masses(expected_times, expected_rates, self.flow_rule)
        if (self.time_s != tuple(expected_times)
                or self.mass_flow_kg_s != tuple(expected_rates)
                or not np.array_equal(self.source.edges_s, expected_times)
                or not np.array_equal(self.source.mass_kg, expected_mass)
                or self.source.origin is not Origin.MEASURED
                or self.source.location.clock_id != self.clock_id):
            raise ValueError("Finite source bins or evidence no longer reproduce from measured flow rows")
        return self


def _flow_inputs(case, time_column, flow_column):
    if type(case) is not HydrogenChannelCase:
        raise TypeError("Supply a reader-issued HydrogenChannelCase")
    if time_column != "flow time [s]" or flow_column != "mass flow meter 1 [g/s]":
        raise ValueError("Use the exact publisher-declared flow-clock and mass-flow labels")
    try:
        time_index = case.column_names.index(time_column)
        flow_index = case.column_names.index(flow_column)
    except ValueError as error:
        raise ValueError("Selected publisher flow/time columns are absent") from error
    valid = case.valid[:, time_index] & case.valid[:, flow_index]
    if not np.all(valid):
        raise ValueError("Missing flow-clock or mass-flow rows prevent a complete source interval")
    times = np.asarray(case.values[:, time_index], dtype=float)
    rates = np.asarray(case.values[:, flow_index], dtype=float)*1e-3  # declared g/s to kg/s
    if (times.ndim != 1 or rates.ndim != 1 or len(times) < 2
            or not np.all(np.isfinite(times)) or not np.all(np.isfinite(rates))
            or np.any(np.diff(times) <= 0.) or np.any(times < 0.) or np.any(rates < 0.)):
        raise ValueError("Measured flow clock must increase and H2 mass-flow rates must be nonnegative")
    return tuple(float(value) for value in times), tuple(float(value) for value in rates)


def _interval_masses(times, rates, flow_rule):
    if flow_rule not in {"left_hold", "right_hold", "trapezoid"}:
        raise ValueError("Select left_hold, right_hold or trapezoid quadrature explicitly")
    edges = np.asarray(times, dtype=float)
    values = np.asarray(rates, dtype=float)
    durations = np.diff(edges)
    if flow_rule == "left_hold":
        interval_rates = values[:-1]
    elif flow_rule == "right_hold":
        interval_rates = values[1:]
    else:
        interval_rates = .5*(values[:-1]+values[1:])
    return interval_rates*durations


def project_hydrogen_channel_finite_source(
    case: HydrogenChannelCase, *, location: SourceLocation,
    representative_state: ThermoState, flow_rule: str,
    state_projection_evidence_id: str,
) -> HydrogenChannelFiniteSource:
    """Bind explicit H2 flow/time columns to ``IntervalMassSource`` bins.

    Pressure values from the dataset are intentionally not used: their gauge/
    absolute basis and source-plane meaning are unresolved. The representative
    thermodynamic state and flow quadrature must therefore be caller supplied.
    """
    if type(case) is not HydrogenChannelCase:
        raise TypeError("Supply a reader-issued HydrogenChannelCase")
    case.require_current()
    if type(location) is not SourceLocation or type(representative_state) is not ThermoState:
        raise TypeError("Supply an explicit release location and representative H2 state")
    if representative_state.basis.fluid.lower() != "hydrogen":
        raise ValueError("Representative source state must declare hydrogen as its fluid")
    if representative_state.phase not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError("Representative measured release state must be gas phase")
    if (not isinstance(state_projection_evidence_id, str)
            or not state_projection_evidence_id.strip()):
        raise ValueError("Declare why the representative state applies to this measured interval")
    times, rates = _flow_inputs(case, "flow time [s]", "mass flow meter 1 [g/s]")
    mass = _interval_masses(times, rates, flow_rule)
    source = IntervalMassSource(
        location=location,
        edges_s=np.asarray(times),
        mass_kg=mass,
        state=representative_state,
        origin=Origin.MEASURED,
        evidence_id=(f"{case.source_doi}:{case.source_sha256}:{case.member_sha256}:"
                     f"flow-time-s:mass-flow-g-s:{flow_rule}:{state_projection_evidence_id.strip()}"),
        end_reason="window_end",
    )
    token = object()
    _PENDING_TOKENS.add(token)
    return HydrogenChannelFiniteSource(
        case=case, source=source, flow_column="mass flow meter 1 [g/s]",
        time_column="flow time [s]", flow_rule=flow_rule,
        clock_id=location.clock_id,
        time_s=times, mass_flow_kg_s=rates, _token=token,
    )


__all__ = ["HydrogenChannelFiniteSource", "project_hydrogen_channel_finite_source"]
