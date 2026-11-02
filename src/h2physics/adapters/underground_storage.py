"""Unverified whole-native UH2SC cavern/well/ground with independent inventories.

UH2SC owns every cavern, water, ideal well and rock residual and time step. The
host reuses direct HEOS properties to audit finite mass, internal energy and rock
heat storage. No native defect is patched, no cavern ODE is duplicated, and no
leakage, geomechanics, biology or rupture probability is inferred.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import numpy as np

from scipy.integrate import trapezoid

from ..core import immutable_array, Origin, ThermoState, finite
from ..release import SourceLocation
from ..sources import IntervalMassSource
from ..thermo.coolprop import CoolPropProperties

UH2SC_REVISION = "d5057350df4d86c5c11a22e76beca24275518c8c"
_SOURCE = {
    "__init__.py": "0cfe9eec3eab730fa7da158216a23be91686d00393606fe9c27f88b28c72da8a",
    "abstract.py": "7c8e845bd0687958a7eeaa3044489831412e592d8c8412b5cc2aa8c6132924c4",
    "constants.py": "e334f5fac2c0a52df50e6af2eb6edf75ad16af8cb816770ce0f60d2669187a8e",
    "errors.py": "05a5be02060222a0a11b29ed87bc028b5923bdef63b39b9696973096a152b76e",
    "fluid.py": "168e9629826b0cc48925f39a222ffad1bd3f25f3b271627557ab02c1c9749cca",
    "fluidfit.py": "a01769e1a4e200926dfe07dcc69ee18781a291bce30f7936f78abd0986224298",
    "ghe.py": "924be919330582bc9cf133040bd4f5ae5cf7b634418941da4b686d730dbedee8",
    "model.py": "e06c6b492f0a630fbe9c02e06e27854b97df7705472db7f09187bfdce83f0785",
    "salt_cavern.py": "a0b4d5958113fd1856110731e368c5abe51b191bdcf5a002ced5fc746faa4389",
    "solvers.py": "ad49476cbc5488389cae8d5ded1b893ba910f2e6fa4b1b431a390d1eb0179353",
    "thermodynamics.py": "c749b20a0947964f9ef5ec1b9bf4bea06d70ecf6fd3ba5074b66ddf7e764f28f",
    "transport.py": "ab39e7cf2f12016440ca8839434cd028b377b9da9a9b79c365b2dcb17db46a5f",
    "utilities.py": "2cdfde3518f69af758b3b238083e22f80d53d1a5c5813c2e9045f4f0cec0f82e",
    "validator.py": "d29c7f8af391f5fc48e1776dc621ffc8c4b13877ffecf3b3f599eb85a349e3cc",
    "well.py": "6ace8a9c56cfd32659a4c659b7f2e402304d92d80b9da25a8df5339531392461",
    "input_schemas/ghe_schema.yml": "a2692e273962852e1bb548486f74dc3b5a5146459a840599d0c1ac440a76b1cd",
    "input_schemas/schema_general.yml": "8baafd7c02c3b0896f9d9f1d815f1a6c00512f568b199eafb322b6d7e8ac6cb0",
    "input_schemas/valve_type_schema.yml": "f4943f497d03921d0d4be0967c8bd774c099102741941027fc458d4322042fee",
    "input_schemas/well_schema.yml": "3a6ec92799ec123028a14dee5c147030e4e71ed4790ed8e43b33d223bbbb5e0e",
}


def _ids(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(
            "Explicit clock/frame/site/geometry/rock/reference/approximation evidence is required"
        )


def _hash(value):
    def plain(item):
        if isinstance(item, Mapping):
            return {k: plain(v) for k, v in item.items()}
        if isinstance(item, (tuple, list)):
            return [plain(v) for v in item]
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        return item

    return hashlib.sha256(
        json.dumps(plain(value), sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _array(value):
    result = np.array(value, dtype=float, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError("Native/audit arrays must be finite")
    result = immutable_array(result, name="result")
    return result


_PENDING_UNDERGROUND_TRACE_ISSUERS: set[object] = set()


def _issue_underground_trace(*values):
    """Issue a trace only from the completed native owner path."""
    token = object()
    _PENDING_UNDERGROUND_TRACE_ISSUERS.add(token)
    try:
        return UndergroundTrace(*values, _issuer_token=token)
    except Exception:
        _PENDING_UNDERGROUND_TRACE_ISSUERS.discard(token)
        raise


def _require_supplied(expected, actual):
    if isinstance(expected, Mapping):
        for key, value in expected.items():
            _require_supplied(value, actual[key])
    elif actual != expected:
        raise ValueError("Native factory changed an explicitly supplied input")


@dataclass(frozen=True, slots=True)
class UndergroundEvidence:
    clock_id: str
    frame_id: str
    site_id: str
    source_id: str
    start_time_s: float
    geometry_evidence_id: str
    rock_property_evidence_id: str
    farfield_boundary_evidence_id: str
    well_history_evidence_id: str
    pure_water_surrogate_evidence_id: str
    omitted_mechanical_energy_evidence_id: str
    origin: Origin

    def __post_init__(self):
        _ids(
            self.clock_id,
            self.frame_id,
            self.site_id,
            self.source_id,
            self.geometry_evidence_id,
            self.rock_property_evidence_id,
            self.farfield_boundary_evidence_id,
            self.well_history_evidence_id,
            self.pure_water_surrogate_evidence_id,
            self.omitted_mechanical_energy_evidence_id,
        )
        finite(self.start_time_s, "absolute operation clock origin")
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED or origin is Origin.MEASURED:
            raise ValueError(
                "This computed native history is not an unresolved or measured observation"
            )
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class UndergroundDomain:
    minimum_pressure_pa_absolute: float
    maximum_pressure_pa_absolute: float
    minimum_temperature_k: float
    maximum_temperature_k: float
    maximum_water_vapor_mass_fraction: float
    evidence_id: str

    def __post_init__(self):
        _ids(self.evidence_id)
        if (
            not 0
            < finite(self.minimum_pressure_pa_absolute, "minimum absolute pressure")
            < finite(self.maximum_pressure_pa_absolute, "maximum absolute pressure")
        ):
            raise ValueError("Declare an ordered positive pressure operating envelope")
        if (
            not 273.16
            <= finite(self.minimum_temperature_k, "minimum warm temperature")
            < finite(self.maximum_temperature_k, "maximum warm temperature")
            <= 380.0
        ):
            raise ValueError("The warm pure-H2/water audit is restricted to 273.16..380K")
        if not 0 < finite(self.maximum_water_vapor_mass_fraction, "dilute vapor budget") < 1:
            raise ValueError(
                "Explicitly qualify the native noninteracting water-vapor approximation"
            )


@dataclass(frozen=True, slots=True)
class UndergroundAuditBudgets:
    hydrogen_mass_kg: float
    water_mass_kg: float
    thermal_energy_j: float
    relative: float
    eos_relative: float
    final_time_s: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if self.relative >= 1 or self.eos_relative >= 1:
            raise ValueError("Dimensionless numerical audit budgets must be below one")


@dataclass(frozen=True, slots=True)
class UndergroundSnapshot:
    native_time_s: float
    time_s: float
    raw_solution: object
    raw_independent_variables: object
    hydrogen_mass_kg: float
    liquid_water_mass_kg: float
    water_vapor_mass_kg: float
    gas_volume_m3: float
    liquid_volume_m3: float
    total_pressure_pa_absolute: float
    dry_hydrogen: object
    liquid_water: object
    water_vapor: object
    wall_temperature_k: float
    rock_temperature_k: np.ndarray
    fluid_internal_energy_j: float
    rock_energy_change_j: float
    hydrogen_rate_into_kg_s: float
    water_rate_into_kg_s: float
    enthalpy_rate_into_w: float
    heat_into_rock_w: float
    heat_out_outer_rock_w: float
    heat_out_farfield_w: float
    eos_relative_defect: float

    def __post_init__(self):
        object.__setattr__(self, "rock_temperature_k", _array(self.rock_temperature_k))


@dataclass(frozen=True, slots=True)
class UndergroundTrace:
    evidence: UndergroundEvidence
    domain: UndergroundDomain
    budgets: UndergroundAuditBudgets
    native_model: object
    native_run_return: object
    native_log_records: tuple
    snapshots: tuple[UndergroundSnapshot, ...]
    boundary_integrals: np.ndarray
    residuals: np.ndarray
    native_source_sha256: Mapping
    original_inputs: Mapping
    input_sha256: str
    native_version_labels: tuple[str, str]
    independent_properties: tuple
    failures: tuple[str, ...]
    numerically_admitted: bool
    software_status: str = "implemented_unverified"
    integral_method: str = (
        "native implicit-step right-endpoint flux audit; no continuous-history accuracy claim"
    )
    residual_columns: tuple = (
        "hydrogen_mass_kg",
        "water_mass_kg",
        "fluid_internal_energy_j",
        "rock_energy_j",
        "combined_thermal_energy_j",
        "requested_well_mass_kg",
    )
    integral_columns: tuple = (
        "hydrogen_in_kg",
        "water_in_kg",
        "enthalpy_in_j",
        "heat_into_rock_j",
        "heat_outer_out_j",
        "heat_farfield_out_j",
    )
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_UNDERGROUND_TRACE_ISSUERS:
            raise ValueError("Underground traces are issued only by the completed native owner")
        _PENDING_UNDERGROUND_TRACE_ISSUERS.remove(self._issuer_token)
        for name in ("boundary_integrals", "residuals"):
            object.__setattr__(self, name, _array(getattr(self, name)))
        object.__setattr__(
            self, "native_source_sha256", MappingProxyType(dict(self.native_source_sha256))
        )
        object.__setattr__(
            self, "original_inputs", MappingProxyType(copy.deepcopy(dict(self.original_inputs)))
        )

    def native_output_series(self, description: str) -> "UndergroundNativeSeries":
        """Select an exact native independent-output column on the accepted clock.

        The returned values preserve the original UH2SC descriptor and are not
        relabeled or unit-converted by the adapter. This is a projection of the
        accepted output rows, not a new cavern property or derived safety limit.
        """
        if not self.numerically_admitted:
            raise ValueError("Only an admitted native cavern trace can expose accepted output series")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Select an exact nonempty native output description")
        return UndergroundNativeSeries(self, description)


@dataclass(frozen=True, slots=True)
class UndergroundNativeSeries:
    """Exact selected UH2SC independent-output rows with original-clock lineage."""

    trace: UndergroundTrace
    description: str
    native_time_s: np.ndarray = field(init=False)
    time_s: np.ndarray = field(init=False)
    values: np.ndarray = field(init=False)
    _column_index: int = field(init=False, repr=False, compare=False)
    _seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.trace) is not UndergroundTrace or not self.trace.numerically_admitted:
            raise TypeError("A native series must retain an admitted UndergroundTrace")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("A native output series requires its exact description")
        descriptions = tuple(self.trace.native_model.independent_vars_descriptions)
        matches = tuple(index for index, value in enumerate(descriptions)
                        if value == self.description)
        if len(matches) != 1:
            raise ValueError("Select one unique description from the native independent outputs")
        index = matches[0]
        rows = tuple(np.asarray(snapshot.raw_independent_variables, dtype=float)
                     for snapshot in self.trace.snapshots)
        if any(row.ndim != 1 or row.shape != (len(descriptions),)
               or not np.all(np.isfinite(row)) for row in rows):
            raise ValueError("Native independent-output rows do not match the retained descriptors")
        native_time = np.asarray([snapshot.native_time_s for snapshot in self.trace.snapshots])
        absolute_time = np.asarray([snapshot.time_s for snapshot in self.trace.snapshots])
        values = np.asarray([row[index] for row in rows], dtype=float)
        if (len(rows) < 2 or np.any(np.diff(native_time) <= 0.)
                or not np.array_equal(absolute_time,
                                      native_time + self.trace.evidence.start_time_s)):
            raise ValueError("Native output series does not share the admitted trace clock")
        native_time = immutable_array(native_time, name="native cavern output clock")
        absolute_time = immutable_array(absolute_time, name="absolute cavern output clock")
        values = immutable_array(values, name="native cavern output series")
        object.__setattr__(self, "native_time_s", native_time)
        object.__setattr__(self, "time_s", absolute_time)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "_column_index", index)
        object.__setattr__(self, "_seal", self._content())

    @property
    def clock_id(self) -> str:
        return self.trace.evidence.clock_id

    @property
    def source_sha256(self) -> Mapping[str, str]:
        return self.trace.native_source_sha256

    def _content(self):
        return _hash((id(self.trace), self.description, self._column_index,
                      self.native_time_s, self.time_s, self.values))

    def require_current(self):
        if self._content() != self._seal:
            raise ValueError("Native output series changed after binding")
        descriptions = tuple(self.trace.native_model.independent_vars_descriptions)
        if (self._column_index >= len(descriptions)
                or descriptions[self._column_index] != self.description):
            raise ValueError("Native output description changed after binding")
        expected = np.asarray([
            np.asarray(snapshot.raw_independent_variables, dtype=float)[self._column_index]
            for snapshot in self.trace.snapshots
        ], dtype=float)
        if not np.array_equal(self.values, expected):
            raise ValueError("Native output samples differ from the original accepted trace")
        return self

    def withdrawal_projection(
        self,
        *,
        location: SourceLocation,
        representative_state: ThermoState,
        flow_rule: Literal["left_hold", "right_hold", "trapezoid"],
        quadrature_evidence_id: str,
        state_projection_evidence_id: str,
        end_reason: str,
    ) -> UndergroundWithdrawalProjection:
        """Project accepted dry-H2 cavern withdrawal to finite source bins.

        The common representative state and interval quadrature are explicit
        projections supplied by the caller. The result represents only the dry
        hydrogen component, not the moist cavern gas or an external jet.
        """
        if not self.numerically_admitted:
            raise ValueError("Only an admitted native cavern trace can feed a downstream source")
        if type(location) is not SourceLocation:
            raise TypeError("Supply the shared SourceLocation contract")
        if location.clock_id != self.evidence.clock_id:
            raise ValueError("Source clock differs from the native cavern operation clock")
        if type(representative_state) is not ThermoState:
            raise TypeError("Supply one explicit dry-hydrogen representative ThermoState")
        _ids(quadrature_evidence_id, state_projection_evidence_id)
        if not isinstance(flow_rule, str) or flow_rule not in {
            "left_hold", "right_hold", "trapezoid",
        }:
            raise ValueError("Select left_hold, right_hold or trapezoid flow integration")
        times, rates, enthalpy_rates = _withdrawal_sample_values(self)
        for sample in self.snapshots:
            representative_state.basis.require_compatible(sample.dry_hydrogen.basis)
        duration = np.diff(times)
        interval_mass = _integrate_withdrawal(rates, duration, flow_rule)
        native_enthalpy = _integrate_withdrawal(enthalpy_rates, duration, flow_rule)
        projected_enthalpy = interval_mass * representative_state.enthalpy_j_kg
        source_evidence = ":".join((
            location.source_id, "uh2sc-dry-h2-withdrawal", flow_rule,
            quadrature_evidence_id.strip(), state_projection_evidence_id.strip(),
        ))
        source = IntervalMassSource(
            location, times, interval_mass, representative_state, Origin.PREDICTED,
            source_evidence, end_reason,
        )
        return UndergroundWithdrawalProjection(
            self, source, representative_state, flow_rule,
            quadrature_evidence_id.strip(), state_projection_evidence_id.strip(),
            tuple(float(x) for x in times), tuple(float(x) for x in rates),
            tuple(float(x) for x in enthalpy_rates),
            tuple(float(x) for x in interval_mass),
            tuple(float(x) for x in native_enthalpy),
            tuple(float(x) for x in projected_enthalpy),
        )


@dataclass(frozen=True, slots=True)
class UndergroundWithdrawalProjection:
    """Immutable shared-source projection for dry hydrogen leaving a cavern."""

    trace: UndergroundTrace
    source: IntervalMassSource
    representative_state: ThermoState
    flow_rule: Literal["left_hold", "right_hold", "trapezoid"]
    quadrature_evidence_id: str
    state_projection_evidence_id: str
    sample_time_s: tuple[float, ...]
    hydrogen_out_rate_kg_s: tuple[float, ...]
    hydrogen_out_enthalpy_flow_w: tuple[float, ...]
    interval_mass_kg: tuple[float, ...]
    native_dry_hydrogen_enthalpy_j: tuple[float, ...]
    projected_enthalpy_j: tuple[float, ...]

    def __post_init__(self):
        if (type(self.trace) is not UndergroundTrace or not self.trace.numerically_admitted
                or type(self.source) is not IntervalMassSource
                or type(self.source.location) is not SourceLocation
                or type(self.representative_state) is not ThermoState):
            raise TypeError("Projection must retain an admitted native trace and shared source")
        self.source.require_current()
        if len(self.trace.snapshots) < 2:
            raise ValueError("At least two native samples are required in a source projection")
        if not isinstance(self.flow_rule, str) or self.flow_rule not in {
            "left_hold", "right_hold", "trapezoid",
        }:
            raise ValueError("Unsupported withdrawal quadrature")
        _ids(self.quadrature_evidence_id, self.state_projection_evidence_id)
        if (self.source.location.clock_id != self.trace.evidence.clock_id
                or self.source.state is not self.representative_state
                or self.source.origin != Origin.PREDICTED):
            raise ValueError("Finite source lost its clock/state/predicted-origin binding")
        expected_evidence = ":".join((
            self.source.location.source_id, "uh2sc-dry-h2-withdrawal", self.flow_rule,
            self.quadrature_evidence_id, self.state_projection_evidence_id,
        ))
        if self.source.evidence_id != expected_evidence:
            raise ValueError("Finite source lost its projection/quadrature evidence")
        self.representative_state.basis.require_compatible(
            self.trace.snapshots[0].dry_hydrogen.basis
        )
        names = (
            "sample_time_s", "hydrogen_out_rate_kg_s", "hydrogen_out_enthalpy_flow_w",
            "interval_mass_kg", "native_dry_hydrogen_enthalpy_j", "projected_enthalpy_j",
        )
        values = {name: tuple(finite(x, name) for x in getattr(self, name)) for name in names}
        sample_count = len(values["sample_time_s"])
        interval_count = sample_count - 1
        if (sample_count < 2
                or any(len(values[name]) != sample_count for name in names[1:3])
                or any(len(values[name]) != interval_count for name in names[3:])):
            raise ValueError("Withdrawal sample and interval ledgers are not aligned")
        if (any(b <= a for a, b in zip(values["sample_time_s"], values["sample_time_s"][1:]))
                or any(x < 0 for x in values["hydrogen_out_rate_kg_s"])
                or any(x < 0 for x in values["interval_mass_kg"])):
            raise ValueError("Withdrawal clock/rates/masses are invalid")
        if (not np.array_equal(self.source.edges_s, np.asarray(values["sample_time_s"]))
                or not np.allclose(self.source.mass_kg, values["interval_mass_kg"],
                                   rtol=1e-13, atol=1e-14)):
            raise ValueError("Shared finite source differs from its retained withdrawal bins")
        expected_samples = _withdrawal_sample_values(self.trace)
        if any(tuple(float(x) for x in expected) != values[name]
               for expected, name in zip(expected_samples, names[:3], strict=True)):
            raise ValueError("Projection samples differ from the accepted native cavern trace")
        duration = np.diff(np.asarray(values["sample_time_s"]))
        expected_mass = _integrate_withdrawal(values["hydrogen_out_rate_kg_s"], duration,
                                               self.flow_rule)
        expected_energy = _integrate_withdrawal(
            values["hydrogen_out_enthalpy_flow_w"], duration, self.flow_rule,
        )
        expected_projection = expected_mass * self.representative_state.enthalpy_j_kg
        if (not np.allclose(expected_mass, values["interval_mass_kg"], rtol=1e-13, atol=1e-14)
                or not np.allclose(expected_energy, values["native_dry_hydrogen_enthalpy_j"],
                                   rtol=1e-13, atol=1e-10)
                or not np.allclose(expected_projection, values["projected_enthalpy_j"],
                                   rtol=1e-13, atol=1e-10)):
            raise ValueError("Projection ledgers differ from their declared quadrature/state")
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def enthalpy_projection_residual_j(self):
        return tuple(native - projected for native, projected in zip(
            self.native_dry_hydrogen_enthalpy_j, self.projected_enthalpy_j, strict=True,
        ))

    def require_current(self):
        self.source.require_current()
        expected = _withdrawal_sample_values(self.trace)
        if any(tuple(float(x) for x in current) != retained for current, retained in zip(
            expected, (self.sample_time_s, self.hydrogen_out_rate_kg_s,
                       self.hydrogen_out_enthalpy_flow_w), strict=True,
        )):
            raise ValueError("Native cavern withdrawal samples changed after source projection")
        if (not np.array_equal(self.source.edges_s, np.asarray(self.sample_time_s))
                or not np.array_equal(self.source.mass_kg, np.asarray(self.interval_mass_kg))
                or self.source.state is not self.representative_state):
            raise ValueError("Finite source arrays/state changed after projection")
        return self


def _withdrawal_sample_values(trace):
    if len(trace.snapshots) < 2:
        raise ValueError("At least two accepted native snapshots are needed for source projection")
    times = np.asarray([sample.time_s for sample in trace.snapshots], dtype=float)
    relative_times = np.asarray([sample.native_time_s for sample in trace.snapshots], dtype=float)
    signed_hydrogen = np.asarray(
        [sample.hydrogen_rate_into_kg_s for sample in trace.snapshots], dtype=float,
    )
    if (not np.all(np.isfinite(times)) or not np.all(np.isfinite(relative_times))
            or np.any(np.diff(times) <= 0.) or np.any(np.diff(relative_times) <= 0.)
            or not np.allclose(times, trace.evidence.start_time_s + relative_times,
                               rtol=1e-12, atol=1e-9)
            or not np.all(np.isfinite(signed_hydrogen))):
        raise ValueError("Accepted native cavern source clock/rates must align and be finite")
    outward = np.maximum(-signed_hydrogen, 0.)
    outward_enthalpy = outward * np.asarray(
        [sample.dry_hydrogen.enthalpy_j_kg for sample in trace.snapshots], dtype=float,
    )
    event_times, event_rates, event_enthalpy = [], [], []
    for index in range(len(times) - 1):
        event_times.append(float(times[index]))
        event_rates.append(float(outward[index]))
        event_enthalpy.append(float(outward_enthalpy[index]))
        first, second = signed_hydrogen[index:index + 2]
        if (first < 0. < second) or (second < 0. < first):
            fraction = abs(first) / (abs(first) + abs(second))
            event_times.append(float(times[index] + fraction * (times[index + 1] - times[index])))
            event_rates.append(0.)
            event_enthalpy.append(0.)
    event_times.append(float(times[-1]))
    event_rates.append(float(outward[-1]))
    event_enthalpy.append(float(outward_enthalpy[-1]))
    return np.asarray(event_times), np.asarray(event_rates), np.asarray(event_enthalpy)


def _integrate_withdrawal(rate_kg_s, duration_s, flow_rule):
    if flow_rule not in {"left_hold", "right_hold", "trapezoid"}:
        raise ValueError("Select left_hold, right_hold or trapezoid quadrature")
    rate = np.asarray(rate_kg_s, dtype=float)
    duration = np.asarray(duration_s, dtype=float)
    if (rate.ndim != 1 or duration.shape != (len(rate) - 1,)
            or not np.all(np.isfinite(rate)) or not np.all(np.isfinite(duration))
            or np.any(duration <= 0.)):
        raise ValueError("Withdrawal quadrature inputs must be finite, aligned samples")
    if flow_rule == "left_hold":
        return rate[:-1] * duration
    if flow_rule == "right_hold":
        return rate[1:] * duration
    return (rate[:-1] + rate[1:]) * duration / 2.


class UndergroundStorageError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        native_model=None,
        native_run_return=None,
        source_inputs=None,
        snapshots=(),
        native_log_records=(),
        native_time_s=None,
        trace=None,
    ):
        super().__init__(message)
        self.native_model = native_model
        self.native_run_return = native_run_return
        self.source_inputs = source_inputs
        self.snapshots = tuple(snapshots)
        self.native_log_records = tuple(native_log_records)
        self.native_time_s = native_time_s
        self.trace = trace


class _NativeLogs(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class Uh2scUndergroundStorage:
    """Actual whole-native cylindrical cavern + ideal adiabatic well + finite rock.

    Rejected native/conservation cases raise with original objects and full audited
    evidence. No fallback to a simpler tank or modified rock equation is supplied.
    """

    def __init__(
        self,
        evidence: UndergroundEvidence,
        domain: UndergroundDomain,
        budgets: UndergroundAuditBudgets,
        *,
        native_model_factory=None,
        property_factory=CoolPropProperties,
    ):
        if (
            type(evidence) is not UndergroundEvidence
            or type(domain) is not UndergroundDomain
            or type(budgets) is not UndergroundAuditBudgets
        ):
            raise TypeError("Use actual explicit evidence, operating domain and audit budgets")
        self.evidence, self.domain, self.budgets = evidence, domain, budgets
        self.native_factory = native_model_factory
        self.property_factory = property_factory

    @staticmethod
    def _preflight(inputs):
        if not isinstance(inputs, Mapping):
            raise TypeError("Native input is a Python mapping, not a mandatory wire/file format")
        copied = copy.deepcopy(dict(inputs))
        initial, calculation = copied["initial"], copied["calculation"]
        if initial["fluid"] != "Hydrogen" or calculation["cool_prop_backend"] != "HEOS":
            raise ValueError("This independent audit supports explicit normal Hydrogen HEOS only")
        if len(copied["wells"]) != 1 or len(copied["ghes"]) != 1:
            raise ValueError(
                "The inspected full native model currently supports one well and one GHE"
            )
        end = finite(calculation["end_time"], "native finite end time", positive=True)
        step = finite(calculation["max_time_step"], "maximum native time step", positive=True)
        if copied["initial"]["liquid_height"] <= 0:
            raise ValueError("Do not remove the native finite liquid-water control volume")
        for well in copied["wells"].values():
            if well["ideal_pipes"] is not True or len(well["valves"]) != 1:
                raise ValueError("Only the native single-pipe ideal adiabatic well is supported")
            for valve in well["valves"].values():
                if valve["type"] != "mdot" or valve["reservoir"]["fluid"] != "Hydrogen":
                    raise ValueError(
                        "Declare native signed prescribed mass flow and the same pure H2 basis"
                    )
                times, rates = _array(valve["time"]), _array(valve["mdot"])
                if (
                    times.ndim != 1
                    or rates.shape != times.shape
                    or len(times) < 2
                    or times[0] != 0
                    or np.any(np.diff(times) <= 0)
                    or times[-1] < end + step
                ):
                    raise ValueError(
                        "Native rate support must include 0..end+one maximum step; no extrapolation"
                    )
        return copied

    @staticmethod
    def _source_hashes(root):
        hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in _SOURCE}
        if hashes != _SOURCE:
            raise ValueError(
                "The actual UH2SC source/schema snapshot differs from the inspected revision"
            )
        return hashes

    @staticmethod
    def _definition(model):
        ground = next(c for c in model.components.values() if c.component_type == "GHE")
        return _hash(
            (
                model.inputs,
                tuple(
                    (name, type(c).__module__, type(c).__name__, id(c), tuple(c.global_indices))
                    for name, c in model.components.items()
                ),
                ground.Cg,
                ground.Rg,
                ground.RTg,
                ground.grid,
                ground.Tg,
                ground.r_inner,
                ground.length_component,
                ground.number_elements,
            )
        )

    def run(self, inputs, *, solver_options: Mapping):
        model, native_return, trace, handler, accepted_time = None, None, None, None, None
        points = []
        original = copy.deepcopy(dict(inputs)) if isinstance(inputs, Mapping) else inputs
        binding = (
            self.evidence,
            self.domain,
            self.budgets,
            self.native_factory,
            self.property_factory,
        )

        def guard():
            if any(
                a is not b
                for a, b in zip(
                    binding,
                    (
                        self.evidence,
                        self.domain,
                        self.budgets,
                        self.native_factory,
                        self.property_factory,
                    ),
                    strict=True,
                )
            ):
                raise ValueError("Underground owner evidence/domain/factory binding changed")

        try:
            copied = self._preflight(inputs)
            fingerprint = _hash(copied)
            module = importlib.import_module("uh2sc.model")
            package = importlib.import_module("uh2sc")
            root = Path(inspect.getfile(package)).parent
            source = self._source_hashes(root)
            distribution_version = metadata.version("uh2sc")
            if distribution_version != "1.0.0":
                raise ValueError(
                    "This source-pinned adapter targets the inspected pyproject version1.0.0"
                )
            factory = self.native_factory or module.Model
            model = factory(
                copy.deepcopy(copied),
                solver_options=copy.deepcopy(dict(solver_options)),
                get_independent_vars=True,
            )
            if (
                type(model) is not module.Model
                or model.is_single_component_test
                or model.is_test_mode
            ):
                raise TypeError("Factory must create the actual whole native UH2SC Model")
            if any(callable(getattr(type(model), name, None)) for name in vars(model)):
                raise ValueError("Native instance method replacements are unsupported")
            _require_supplied(copied, model.inputs)
            if model.time != 0 or model.solutions:
                raise ValueError("Native factory must supply a fresh finite initial-value model")
            guard()
            native_definition = self._definition(model)
            h2, water = self.property_factory("Hydrogen"), self.property_factory("Water")
            for provider, fluid in ((h2, "Hydrogen"), (water, "Water")):
                if (
                    not isinstance(provider, CoolPropProperties)
                    or provider.backend != "HEOS"
                    or provider.basis.fluid != fluid
                    or provider.internal_energy_policy != "library"
                    or provider.quality_roundoff_tolerance != 0
                ):
                    raise ValueError(
                        "Independent inventories require direct strict default-reference HEOS"
                    )
            if h2.version != water.version:
                raise ValueError("Keep a common actual CoolProp version/reference family")
            handler = _NativeLogs()
            model.logging.addHandler(handler)
            native_return = model.run()
            guard()
            if self._definition(model) != native_definition or _hash(copied) != fingerprint:
                raise ValueError("Native model/input/geometry definitions changed during the run")
            if _hash(self._preflight(inputs)) != fingerprint:
                raise ValueError("Caller source inputs changed during native execution")
            self._source_hashes(root)
            cavern = model.components["cavern"]
            well = next(c for c in model.components.values() if c.component_type == "Well")
            ground = next(c for c in model.components.values() if c.component_type == "GHE")
            if len(well.pipes) != 1 or cavern._number_fluids != 1:
                raise ValueError(
                    "Actual native component/species count is outside the supported audit"
                )
            if (
                model.fluids["cavern"]._fit is not None
                or model.fluids["cavern"].backend != "HEOS"
                or model.fluids["cavern"].fluid_names() != ["Hydrogen"]
            ):
                raise ValueError(
                    "Native fitted/mixed/spin-fluid properties cannot be relabeled default normal H2"
                )
            for pipe in well.pipes.values():
                if (
                    pipe.fluid._fit is not None
                    or pipe.fluid.backend != "HEOS"
                    or pipe.fluid.fluid_names() != ["Hydrogen"]
                ):
                    raise ValueError(
                        "Native well fluid and dry cavern gas must use the same direct HEOS basis"
                    )
            times = tuple(model.solutions)
            if times != tuple(model.independent_vars) or len(times) < 2 or times[0] != 0:
                raise ValueError(
                    "Original native state/independent-output clocks are incomplete or misaligned"
                )
            if any(b <= a for a, b in zip(times[:-1], times[1:], strict=True)):
                raise ValueError("Native output clock is not strictly increasing")
            # Nodal cylindrical dual volumes use midpoint faces and retain BOTH
            # end-node thermal inventories. No native index/last-cell repair.
            grid = _array(ground.grid)
            faces = np.r_[grid[0], (grid[:-1] + grid[1:]) / 2, grid[-1]]
            ghe_input = next(iter(copied["ghes"].values()))
            capacity = (
                ghe_input["density"]
                * ghe_input["heat_capacity"]
                * math.pi
                * ground.length_component
                * np.diff(faces**2)
            )
            if (
                len(capacity) != ground.number_elements + 1
                or np.any(capacity <= 0)
                or not np.allclose(capacity, ground.Cg, rtol=1e-13, atol=0)
            ):
                raise ValueError(
                    "Native finite ground heat capacities disagree with independent cylindrical volumes"
                )
            ground_description = list(ground.independent_vars_descriptions)
            descriptions = list(model.independent_vars_descriptions)
            ground_offset = 0
            for component in model.components.values():
                if component is ground:
                    break
                ground_offset += len(component.independent_vars_descriptions)
            cg, wg, gg = cavern.global_indices[0], well.global_indices[0], ground.global_indices[0]
            n = ground.number_elements
            t_initial = None
            integrals, residuals = [], []
            integral = np.zeros(6)
            failures = []
            valve = next(iter(next(iter(copied["wells"].values()))["valves"].values()))
            for time in times:
                accepted_time = float(time)
                raw, independent = model.solutions[time], model.independent_vars[time]
                values, auxiliary = _array(raw), _array(independent)
                if values.ndim != 1 or auxiliary.shape != (len(descriptions),):
                    raise ValueError(
                        "Actual native output shapes differ from their component layouts"
                    )
                gas_t, wall_t, water_mass, water_t, hydrogen_mass = values[cg : cg + 5]
                if min(water_mass, hydrogen_mass) <= 0:
                    raise ValueError("Native finite fluid inventory became nonpositive")

                def aux(name):
                    return finite(auxiliary[descriptions.index(name)], name)

                vapor_mass = aux("Water vapor mass in cavern (kg)")
                volume = aux("Cavern volume (m3)")
                water_volume = aux("Brine volume (m3)")
                pressure = aux("Total cavern pressure (gasses + water vapor) (Pa)")
                dry_pressure = aux("Cavern average gas pressure excluding water vapor (Pa)")
                brine_pressure = aux("Brine average pressure (Pa)")
                if min(vapor_mass, volume, water_volume) <= 0:
                    raise ValueError("Native water/vapor volumes or mass are not positive")
                domain = self.domain
                rock = values[gg + 1 : gg + n + 2]
                if (
                    not domain.minimum_pressure_pa_absolute
                    <= pressure
                    <= domain.maximum_pressure_pa_absolute
                    or any(
                        not domain.minimum_temperature_k
                        <= temperature
                        <= domain.maximum_temperature_k
                        for temperature in (*rock, gas_t, wall_t, water_t)
                    )
                ):
                    raise ValueError(
                        "Actual native P/T output left the caller's operating/material envelope"
                    )
                if (
                    vapor_mass / (hydrogen_mass + vapor_mass)
                    > domain.maximum_water_vapor_mass_fraction
                ):
                    raise ValueError(
                        "Native noninteracting vapor exceeds its explicit dilute-water budget"
                    )
                gas = h2.state_pt(dry_pressure, gas_t)
                liquid = water.state_pt(brine_pressure, water_t)
                vapor = water.saturated_at_temperature(gas_t, 1.0)
                if (
                    gas.phase not in {"gas", "supercritical", "supercritical_gas"}
                    or liquid.phase != "liquid"
                ):
                    raise ValueError(
                        "Actual direct-EOS phase lies outside native warm gas/liquid-water assumptions"
                    )
                if t_initial is None:
                    t_initial = rock.copy()
                rock_energy = float(capacity @ (rock - t_initial))
                fluid_energy = (
                    hydrogen_mass * gas.internal_energy_j_kg
                    + water_mass * liquid.internal_energy_j_kg
                    + vapor_mass * vapor.internal_energy_j_kg
                )
                eos_error = max(
                    abs(gas.density_kg_m3 * volume / hydrogen_mass - 1),
                    abs(liquid.density_kg_m3 * water_volume / water_mass - 1),
                    abs(vapor.density_kg_m3 * volume / vapor_mass - 1),
                    abs((dry_pressure + vapor.pressure_pa) / pressure - 1),
                )
                well_rate = finite(values[wg], "signed actual native mean well flow")
                if well_rate >= 0:
                    hydrogen_rate, water_rate = well_rate, 0.0
                    inlet = h2.state_pt(values[wg + 4], values[wg + 3])
                    enthalpy_rate = well_rate * inlet.enthalpy_j_kg
                else:
                    dry_fraction = hydrogen_mass / (hydrogen_mass + vapor_mass)
                    hydrogen_rate, water_rate = (
                        well_rate * dry_fraction,
                        well_rate * (1 - dry_fraction),
                    )
                    enthalpy_rate = (
                        hydrogen_rate * gas.enthalpy_j_kg + water_rate * vapor.enthalpy_j_kg
                    )
                far_values = auxiliary[ground_offset : ground_offset + len(ground_description)]
                far_heat = float(np.sum(far_values[n - 1 :]))
                point = UndergroundSnapshot(
                    time,
                    self.evidence.start_time_s + time,
                    raw,
                    independent,
                    hydrogen_mass,
                    water_mass,
                    vapor_mass,
                    volume,
                    water_volume,
                    pressure,
                    gas,
                    liquid,
                    vapor,
                    wall_t,
                    rock,
                    fluid_energy,
                    rock_energy,
                    hydrogen_rate,
                    water_rate,
                    enthalpy_rate,
                    float(values[gg]),
                    float(values[gg + n + 2]),
                    far_heat,
                    eos_error,
                )
                points.append(point)
                if len(points) > 1:
                    dt = time - points[-2].native_time_s
                    integral += dt * np.array(
                        (
                            hydrogen_rate,
                            water_rate,
                            enthalpy_rate,
                            point.heat_into_rock_w,
                            point.heat_out_outer_rock_w,
                            far_heat,
                        )
                    )
                integrals.append(integral.copy())
                first = points[0]
                du = fluid_energy - first.fluid_internal_energy_j
                knots = np.r_[
                    0.0,
                    np.asarray(valve["time"])[
                        (np.asarray(valve["time"]) > 0) & (np.asarray(valve["time"]) < time)
                    ],
                    time,
                ]
                requested_mass = float(
                    trapezoid(np.interp(knots, valve["time"], valve["mdot"]), knots)
                )
                residuals.append(
                    (
                        hydrogen_mass - first.hydrogen_mass_kg - integral[0],
                        water_mass
                        + vapor_mass
                        - first.liquid_water_mass_kg
                        - first.water_vapor_mass_kg
                        - integral[1],
                        du - integral[2] + integral[3],
                        rock_energy - integral[3] + integral[4] + integral[5],
                        du + rock_energy - integral[2] + integral[4] + integral[5],
                        integral[0] + integral[1] - requested_mass,
                    )
                )
            errors = _array(residuals)
            budgets = self.budgets
            energy_scale = max(
                1.0,
                max(
                    abs(p.fluid_internal_energy_j - points[0].fluid_internal_energy_j)
                    + abs(p.rock_energy_change_j)
                    for p in points
                ),
                float(np.max(abs(integral[2:]))),
            )
            limits = (
                budgets.hydrogen_mass_kg + budgets.relative * points[0].hydrogen_mass_kg,
                budgets.water_mass_kg
                + budgets.relative * max(p.water_vapor_mass_kg for p in points),
                *([budgets.thermal_energy_j + budgets.relative * energy_scale] * 3),
                budgets.hydrogen_mass_kg
                + budgets.water_mass_kg
                + budgets.relative * abs(requested_mass),
            )
            for index, limit in enumerate(limits):
                if np.max(abs(errors[:, index])) > limit:
                    failures.append(f"independent ledger column {index} exceeds {limit} SI")
            if max(p.eos_relative_defect for p in points) > budgets.eos_relative:
                failures.append("independent direct-EOS volume/partial-pressure closure")
            if abs(times[-1] - copied["calculation"]["end_time"]) > budgets.final_time_s:
                failures.append("native run returned a truncated/overshot finite support")
            if any(record.levelno >= logging.ERROR for record in handler.records):
                failures.append("native engine logged an error despite returning")
            self._source_hashes(root)
            guard()
            if self._definition(model) != native_definition:
                failures.append("native physical definitions changed")
            trace = _issue_underground_trace(
                self.evidence,
                self.domain,
                budgets,
                model,
                native_return,
                tuple(handler.records),
                tuple(points),
                integrals,
                errors,
                source,
                original,
                fingerprint,
                (distribution_version, str(package.__version__)),
                (h2, water),
                tuple(failures),
                not failures,
            )
            if failures:
                raise ValueError("; ".join(failures))
            return trace
        except Exception as cause:
            raise UndergroundStorageError(
                f"Unverified native underground calculation rejected: {cause}",
                native_model=model,
                native_run_return=native_return,
                source_inputs=original,
                snapshots=points,
                native_log_records=() if handler is None else handler.records,
                native_time_s=accepted_time
                if accepted_time is not None
                else getattr(model, "time", None),
                trace=trace,
            ) from cause
        finally:
            if model is not None and handler is not None:
                model.logging.removeHandler(handler)
