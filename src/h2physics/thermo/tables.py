"""Qualify released CoolProp tables within an explicit gas-only envelope.

The interpolation implementation remains in the separately installed CoolProp
library. Qualification here limits the envelope and measures error/performance;
it does not claim that interpolation is an independent equation of state.
Reference: https://coolprop.org/coolprop/Tabular.html
"""

import math
import statistics
import time
from dataclasses import dataclass, field

import numpy as np

from ..core import ThermoState, finite
from .coolprop import CoolPropProperties

FIELDS = ("density_kg_m3", "enthalpy_j_kg", "internal_energy_j_kg", "entropy_j_kg_k",
          "cp_j_kg_k", "cv_j_kg_k", "viscosity_pa_s", "conductivity_w_m_k",
          "speed_of_sound_m_s")
_PENDING_TABLE_QUALIFICATION_ISSUERS: set[object] = set()


def _issue_table_qualification(**values):
    token = object()
    _PENDING_TABLE_QUALIFICATION_ISSUERS.add(token)
    try:
        return TableQualification(**values, _issuer_token=token)
    except Exception:
        _PENDING_TABLE_QUALIFICATION_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class GasEnvelope:
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_temperature_k: float
    maximum_temperature_k: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if (self.minimum_pressure_pa >= self.maximum_pressure_pa or
                self.minimum_temperature_k >= self.maximum_temperature_k):
            raise ValueError("Each property envelope must have increasing, nonzero bounds")

    def require_pt(self, pressure_pa, temperature_k):
        pressure_pa = finite(pressure_pa, "pressure_pa", positive=True)
        temperature_k = finite(temperature_k, "temperature_k", positive=True)
        if not self.minimum_pressure_pa <= pressure_pa <= self.maximum_pressure_pa:
            raise ValueError("Pressure is outside the qualified table envelope")
        if not self.minimum_temperature_k <= temperature_k <= self.maximum_temperature_k:
            raise ValueError("Temperature is outside the qualified table envelope")


@dataclass(frozen=True, slots=True)
class TableQualification:
    fluid: str
    reference_backend: str
    table_backend: str
    property_library_version: str
    envelope: GasEnvelope
    validation_point_count: int
    seed: int
    maximum_relative_errors: tuple[tuple[str, float], ...]
    maximum_enthalpy_identity_residual_j_kg: float
    maximum_relative_enthalpy_identity_error: float
    maximum_relative_error_allowed: float
    maximum_relative_identity_error_allowed: float
    reference_seconds_per_call: float
    table_seconds_per_call: float
    internal_energy_policy: str
    maximum_internal_energy_adjustment_j_kg: float
    inverse_validation_point_count: int
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TABLE_QUALIFICATION_ISSUERS:
            raise TypeError("Create table qualification reports through QualifiedGasTable")
        _PENDING_TABLE_QUALIFICATION_ISSUERS.remove(self._issuer_token)
        for name in ("fluid", "reference_backend", "table_backend", "property_library_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Table qualification requires an explicit {name}")
        if type(self.envelope) is not GasEnvelope:
            raise TypeError("Table qualification must retain its typed gas envelope")
        if (type(self.validation_point_count) is not int or self.validation_point_count < 1
                or type(self.inverse_validation_point_count) is not int
                or self.inverse_validation_point_count < 0
                or type(self.seed) is not int or self.seed < 0):
            raise ValueError("Table qualification counts and seed must be nonnegative explicit integers")
        if (self.reference_backend != "HEOS"
                or self.table_backend not in {"BICUBIC&HEOS", "TTSE&HEOS"}):
            raise ValueError("Table qualification must identify the supported HEOS/table backends")
        errors = tuple(tuple(item) for item in self.maximum_relative_errors)
        if (len(errors) != len(FIELDS)
                or any(len(item) != 2 or not isinstance(item[0], str) for item in errors)
                or {name for name, _ in errors} != set(FIELDS)):
            raise ValueError("Table qualification must retain exactly one error per released property")
        for _, error in errors:
            if finite(error, "maximum property relative error") < 0.:
                raise ValueError("Table qualification property errors must be nonnegative")
        for name in (
            "maximum_enthalpy_identity_residual_j_kg",
            "maximum_relative_enthalpy_identity_error",
        ):
            if finite(getattr(self, name), name) < 0.:
                raise ValueError("Table qualification identity errors must be nonnegative")
        for name in (
            "maximum_relative_error_allowed",
            "maximum_relative_identity_error_allowed",
            "reference_seconds_per_call",
            "table_seconds_per_call",
        ):
            finite(getattr(self, name), name, positive=True)
        if finite(self.maximum_internal_energy_adjustment_j_kg,
                  "maximum internal-energy adjustment") < 0.:
            raise ValueError("Internal-energy adjustment magnitude cannot be negative")
        if (not isinstance(self.internal_energy_policy, str)
                or self.internal_energy_policy not in {"library", "derive_from_h_p_rho"}):
            raise ValueError("Table qualification has an unsupported internal-energy policy")
        object.__setattr__(self, "maximum_relative_errors", errors)
        object.__setattr__(self, "_seal", self._current_values())

    def _current_values(self):
        return (
            self.fluid, self.reference_backend, self.table_backend,
            self.property_library_version,
            (self.envelope.minimum_pressure_pa, self.envelope.maximum_pressure_pa,
             self.envelope.minimum_temperature_k, self.envelope.maximum_temperature_k),
            self.validation_point_count, self.seed, self.maximum_relative_errors,
            self.maximum_enthalpy_identity_residual_j_kg,
            self.maximum_relative_enthalpy_identity_error,
            self.maximum_relative_error_allowed,
            self.maximum_relative_identity_error_allowed,
            self.reference_seconds_per_call, self.table_seconds_per_call,
            self.internal_energy_policy, self.maximum_internal_energy_adjustment_j_kg,
            self.inverse_validation_point_count,
        )

    def require_current(self):
        if self._current_values() != self._seal:
            raise ValueError("Table qualification report changed after the provider issued it")
        return self

    @property
    def measured_speedup(self):
        self.require_current()
        return self.reference_seconds_per_call / self.table_seconds_per_call

    def meets_speedup_target(self, minimum_speedup: float = 1.0) -> bool:
        """Compare the recorded benchmark with a caller-selected observed-speed target.

        This is a deterministic comparison of retained timing summaries, not a
        statistical performance guarantee or a property-accuracy gate.
        """
        self.require_current()
        target = finite(minimum_speedup, "minimum_speedup", positive=True)
        return self.measured_speedup >= target

    @property
    def error_gate_passed(self):
        self.require_current()
        return max(value for _, value in self.maximum_relative_errors) <= self.maximum_relative_error_allowed

    @property
    def qualification_passed(self):
        self.require_current()
        return (self.error_gate_passed and self.maximum_relative_enthalpy_identity_error
                <= self.maximum_relative_identity_error_allowed)


class TableQualificationError(ValueError):
    def __init__(self, report: TableQualification):
        if type(report) is not TableQualification:
            raise TypeError("A table qualification error must retain an issued TableQualification")
        super().__init__("Table does not meet the requested property or energy-identity budget")
        self.report = report


class QualifiedGasTable:
    """A qualified PT/PH/PS provider. Out-of-envelope states raise; no EOS substitution."""

    def __setattr__(self, name, value):
        if getattr(self, "_qualification_binding", None) is not None:
            raise AttributeError("A qualified table's property identity, envelope and report are immutable")
        object.__setattr__(self, name, value)

    def _configuration(self):
        native_backend = self._table._state.backend_name()
        native_fluids = tuple(self._table._state.fluid_names())
        return (id(self._table), id(self._table._state), id(self._table._cp),
                id(self._table._lock),
                native_backend, native_fluids,
                self._table.basis, self._table.backend,
                self._table.version, self._table.internal_energy_policy,
                self._table.quality_roundoff_tolerance, self.envelope,
                repr(self.envelope), id(self.qualification), repr(self.qualification))

    def require_current(self):
        binding = getattr(self, "_qualification_binding", None)
        if binding is not None and self._configuration() != binding:
            raise ValueError("Qualified table backend, envelope or qualification report changed")
        return self

    def __init__(self, reference: CoolPropProperties, envelope: GasEnvelope, *,
                 backend: str = "BICUBIC&HEOS", validation_points: int = 300,
                 maximum_relative_error: float = 0.005, seed: int = 20261026,
                 timing_repetitions: int = 3, maximum_relative_identity_error: float = 1e-7,
                 internal_energy_policy: str = "library"):
        if not isinstance(reference, CoolPropProperties):
            raise TypeError("Table qualification requires the direct HEOS CoolProp reference provider")
        if type(envelope) is not GasEnvelope:
            raise TypeError("Supply a typed GasEnvelope for table qualification")
        if (reference.backend != "HEOS" or not isinstance(backend, str)
                or backend not in {"BICUBIC&HEOS", "TTSE&HEOS"}):
            raise ValueError("Qualification requires HEOS and a supported released table backend")
        if envelope.minimum_temperature_k <= 1.2 * reference.critical_temperature_k:
            raise ValueError("This gas-table level excludes the critical and subcritical temperature region")
        if (type(validation_points) is not int or type(timing_repetitions) is not int
                or type(seed) is not int
                or validation_points < 20 or timing_repetitions < 1):
            raise ValueError("Qualification needs an integer seed, at least 20 points and one timing repetition")
        if (not isinstance(internal_energy_policy, str)
                or internal_energy_policy not in {"library", "derive_from_h_p_rho"}):
            raise ValueError("Select a supported table internal-energy policy")
        finite(maximum_relative_error, "maximum_relative_error", positive=True)
        finite(maximum_relative_identity_error, "maximum_relative_identity_error", positive=True)
        self._table = CoolPropProperties(reference.basis.fluid, backend=backend,
                                        internal_energy_policy=internal_energy_policy)
        raw_table = (self._table if internal_energy_policy == "library" else
                     CoolPropProperties(reference.basis.fluid, backend=backend))
        reference.basis.require_compatible(self._table.basis)
        self.envelope = envelope
        rng = np.random.default_rng(seed)
        pressures = np.exp(rng.uniform(math.log(envelope.minimum_pressure_pa),
                                      math.log(envelope.maximum_pressure_pa), validation_points))
        temperatures = rng.uniform(envelope.minimum_temperature_k,
                                   envelope.maximum_temperature_k, validation_points)
        points = list(zip(pressures, temperatures, strict=True))
        points += [(p, t) for p in (envelope.minimum_pressure_pa, envelope.maximum_pressure_pa)
                   for t in (envelope.minimum_temperature_k, envelope.maximum_temperature_k)]
        errors = {field: 0.0 for field in FIELDS}
        identity_residual = 0.0
        identity_relative = 0.0
        maximum_adjustment = 0.0
        reference_inputs = []
        for point_index, (pressure, temperature) in enumerate(points):
            expected = reference.state_pt(float(pressure), float(temperature))
            reference_inputs.append(expected)
            if expected.phase not in {"gas", "supercritical", "supercritical_gas"}:
                raise ValueError("Reference envelope contains a state outside the gas-table model level")
            results = [self._checked(self._table.state_pt(float(pressure), float(temperature)))]
            # Reference enthalpy/entropy may invert just outside an exact table
            # corner. Check inverse inputs at the independently sampled interior.
            if point_index < validation_points:
                results.extend([
                    self._checked(self._table.state_ph(float(pressure), expected.enthalpy_j_kg)),
                    self._checked(self._table.state_ps(float(pressure), expected.entropy_j_kg_k)),
                ])
            raw_results = ([raw_table.state_pt(float(pressure), float(temperature))]
                           if raw_table is not self._table else results[:1])
            if point_index < validation_points and raw_table is not self._table:
                raw_results.extend([raw_table.state_ph(float(pressure), expected.enthalpy_j_kg),
                                    raw_table.state_ps(float(pressure), expected.entropy_j_kg_k)])
            elif raw_table is self._table:
                raw_results = results
            for result, raw_result in zip(results, raw_results, strict=True):
                maximum_adjustment = max(maximum_adjustment, abs(result.internal_energy_j_kg
                                                                 - raw_result.internal_energy_j_kg))
                if abs(result.temperature_k - expected.temperature_k) / expected.temperature_k > maximum_relative_error:
                    raise ValueError("Inverse table state exceeds the temperature error budget")
                for field_name in FIELDS:
                    truth, predicted = getattr(expected, field_name), getattr(result, field_name)
                    if truth is None or predicted is None:
                        raise ValueError(f"Table qualification lacks property {field_name}")
                    if abs(truth) < 1e-12:
                        raise ValueError("Relative-error qualification needs a different budget near a zero reference")
                    errors[field_name] = max(errors[field_name], abs(predicted - truth) / abs(truth))
                residual = abs(result.enthalpy_identity_residual_j_kg)
                identity_residual = max(identity_residual, residual)
                energy_scale = max(abs(result.enthalpy_j_kg), abs(result.internal_energy_j_kg),
                                   result.pressure_pa / result.density_kg_m3)
                identity_relative = max(identity_relative, residual / energy_scale)

        def duration(provider):
            readings = []
            for _ in range(timing_repetitions):
                started = time.perf_counter()
                for index, ((pressure, temperature), state) in enumerate(zip(points, reference_inputs, strict=True)):
                    provider.state_pt(float(pressure), float(temperature))
                    if index < validation_points:
                        provider.state_ph(float(pressure), state.enthalpy_j_kg)
                        provider.state_ps(float(pressure), state.entropy_j_kg_k)
                readings.append((time.perf_counter() - started) / (len(points) + 2*validation_points))
            return statistics.median(readings)

        self.qualification = _issue_table_qualification(
            fluid=reference.basis.fluid, reference_backend=reference.backend,
            table_backend=backend, property_library_version=reference.version,
            envelope=envelope, validation_point_count=len(points), seed=seed,
            maximum_relative_errors=tuple(errors.items()),
            maximum_enthalpy_identity_residual_j_kg=identity_residual,
            maximum_relative_enthalpy_identity_error=identity_relative,
            maximum_relative_error_allowed=maximum_relative_error,
            maximum_relative_identity_error_allowed=maximum_relative_identity_error,
            reference_seconds_per_call=duration(reference), table_seconds_per_call=duration(self),
            internal_energy_policy=internal_energy_policy,
            maximum_internal_energy_adjustment_j_kg=maximum_adjustment,
            inverse_validation_point_count=2*validation_points,
        )
        if not self.qualification.qualification_passed:
            raise TableQualificationError(self.qualification)
        self._qualification_binding = self._configuration()

    @property
    def basis(self):
        self.require_current()
        return self._table.basis

    def _checked(self, state: ThermoState) -> ThermoState:
        self.require_current()
        self.envelope.require_pt(state.pressure_pa, state.temperature_k)
        if state.phase not in {"gas", "supercritical", "supercritical_gas"}:
            raise ValueError("Table result is outside the qualified gas phase")
        return state

    def state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState:
        self.require_current()
        finite(pressure_pa, "pressure_pa", positive=True)
        finite(temperature_k, "temperature_k", positive=True)
        self.envelope.require_pt(pressure_pa, temperature_k)
        return self._checked(self._table.state_pt(pressure_pa, temperature_k))

    def state_ph(self, pressure_pa: float, enthalpy_j_kg: float) -> ThermoState:
        self.require_current()
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        finite(enthalpy_j_kg, "enthalpy_j_kg")
        if not self.envelope.minimum_pressure_pa <= pressure <= self.envelope.maximum_pressure_pa:
            raise ValueError("Pressure is outside the qualified table envelope")
        return self._checked(self._table.state_ph(pressure_pa, enthalpy_j_kg))

    def state_ps(self, pressure_pa: float, entropy_j_kg_k: float) -> ThermoState:
        self.require_current()
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        finite(entropy_j_kg_k, "entropy_j_kg_k")
        if not self.envelope.minimum_pressure_pa <= pressure <= self.envelope.maximum_pressure_pa:
            raise ValueError("Pressure is outside the qualified table envelope")
        return self._checked(self._table.state_ps(pressure_pa, entropy_j_kg_k))
