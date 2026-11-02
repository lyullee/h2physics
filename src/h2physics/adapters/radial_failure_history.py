"""Bind a radial wall-temperature solution to a typed vessel failure history.

The thermal solver and native fracture solver keep their existing ownership.
This adapter samples the computed wall profile at one declared radial location
and maps it to the matching pressure samples without reconstructing time data.
"""

from __future__ import annotations

import hashlib
import json
import marshal
from collections.abc import Mapping
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from dataclasses import field as dataclass_field

import numpy as np

from ..core import immutable_array, finite
from ..materials.elastic_cylinder import CylinderStressSamples
from ..materials.radial_heat import RadialHeatResult, RadialThermomechanicalHistory
from ..materials.radial_thermoelastic import RadialThermoelasticStressSample
from .cylinder_vessel_history import (
    CylinderVesselHistoryBinding,
    bind_cylinder_samples_to_vessel_history,
)
from .vessel_failure import VesselFailureContext, VesselFailureHistory, VesselLoading


def _callback_value_binding(value, seen=None):
    """Capture ordinary nested callback state without invoking user code."""
    seen = set() if seen is None else seen
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, (float, np.floating)):
        return ("float", float(value).hex())
    if isinstance(value, np.integer):
        return int(value)
    if id(value) in seen:
        return ("reference", id(value))
    seen.add(id(value))
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            return ("object-array", id(value), value.shape, tuple(
                _callback_value_binding(item, seen) for item in value.flat))
        return ("array", id(value), value.dtype.str, value.shape,
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest())
    if isinstance(value, Mapping):
        return ("mapping", id(value), tuple(
            (str(key), _callback_value_binding(item, seen))
            for key, item in value.items()))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(
            _callback_value_binding(item, seen) for item in value))
    if is_dataclass(value) and not isinstance(value, type):
        return (type(value).__module__, type(value).__qualname__, id(value), tuple(
            (item.name, _callback_value_binding(getattr(value, item.name), seen))
            for item in dataclass_fields(value)))
    return _callback_object_state(value, seen)


def _callback_object_state(value, seen):
    state = getattr(value, "__dict__", None)
    slots = []
    for cls in type(value).__mro__:
        declared = getattr(cls, "__slots__", ())
        if isinstance(declared, str):
            declared = (declared,)
        for name in declared:
            if name in ("__dict__", "__weakref__"):
                continue
            try:
                item = getattr(value, name)
            except (AttributeError, ValueError):
                continue
            slots.append((name, _callback_value_binding(item, seen)))
    return (type(value).__module__, type(value).__qualname__, id(value),
            _callback_value_binding(state, seen) if state is not None else None,
            tuple(slots))


def _callable_binding(value, seen=None):
    if not callable(value):
        return _callback_value_binding(value, seen)
    seen = set() if seen is None else seen
    if id(value) in seen:
        return ("reference", id(value))
    seen.add(id(value))
    bound_self = getattr(value, "__self__", None)
    call = value if getattr(value, "__code__", None) is not None else getattr(value, "__call__", value)
    function = getattr(call, "__func__", call)
    code = getattr(function, "__code__", None)
    closure = getattr(function, "__closure__", None)
    closure_values = []
    for cell in closure or ():
        try:
            closure_values.append(_callback_value_binding(cell.cell_contents, seen))
        except ValueError:  # A closed-over name may have been deleted.
            closure_values.append("<empty closure cell>")
    state = None
    if bound_self is not None and not isinstance(bound_self, type):
        state = _callback_object_state(bound_self, seen)
    elif code is None:
        state = _callback_object_state(value, seen)
    return (
        getattr(value, "__module__", type(value).__module__),
        getattr(value, "__qualname__", type(value).__qualname__),
        id(function),
        hashlib.sha256(marshal.dumps(code)).hexdigest() if code is not None else None,
        _callback_value_binding(getattr(function, "__defaults__", None), seen),
        _callback_value_binding(getattr(function, "__kwdefaults__", None), seen),
        tuple(closure_values),
        id(bound_self) if bound_self is not None else None,
        state,
    )


def _array_binding(value):
    array = np.ascontiguousarray(value)
    return array.dtype.str, array.shape, hashlib.sha256(array.tobytes()).hexdigest()


def _content_binding(result):
    pressure = result.pressure_samples
    thermal = result.thermal_history
    source = result.source_binding
    history = source.history
    payload = (
        tuple(_array_binding(getattr(pressure, name)) for name in (
            "time_s", "radius_m", "radial_stress_pa", "hoop_stress_pa",
            "axial_stress_pa", "von_mises_stress_pa",
        )),
        pressure.clock_id,
        pressure.evidence_id,
        (pressure.geometry.inner_radius_m, pressure.geometry.outer_radius_m,
         pressure.geometry.end_condition, pressure.geometry.geometry_id),
        tuple((load.internal_pressure_pa, load.external_pressure_pa, load.load_id,
               str(load.origin)) for load in pressure.loads),
        tuple(_array_binding(getattr(thermal, name)) for name in (
            "time_s", "radius_m", "temperature_k", "inner_heat_into_solid_j",
            "outer_heat_into_solid_j", "stored_energy_j", "energy_residual_j",
            "inner_surface_temperature_k", "outer_surface_temperature_k",
        )),
        (thermal.inner_radius_m, thermal.outer_radius_m, thermal.cylinder_length_m,
         thermal.reference_temperature_k, thermal.history_id, thermal.clock_id,
         thermal.evidence_id, thermal.material.density_kg_m3,
         thermal.material.material_id, thermal.material.evidence_id,
         _callable_binding(thermal.material.heat_capacity_j_kg_k),
         _callable_binding(thermal.material.conductivity_w_m_k)),
        tuple((boundary.kind, _callable_binding(boundary.value), boundary.evidence_id,
               _callable_binding(boundary.coefficient))
              for boundary in (thermal.inner_boundary, thermal.outer_boundary)),
        (history.context.vessel_id, history.context.wall_region_id, history.context.frame_id,
         history.context.clock_id, history.context.source_id,
         (history.context.fluid_basis.fluid, history.context.fluid_basis.reference_id,
          history.context.fluid_basis.spin_composition),
         history.context.hydrogen_mole_fraction,
         history.context.hydrogen_service_evidence_id,
         history.context.wall_temperature_evidence_id,
         history.context.geometry_binding_evidence_id, str(history.context.origin),
         history.reconstruction_evidence_id,
         tuple((sample.time_s, sample.internal_pressure_pa_absolute,
                sample.external_pressure_pa_absolute, sample.wall_temperature_k,
                sample.phase_id, id(sample.native_snapshot), id(sample.native_state),
                id(sample.native_fluid), tuple(id(parent) for parent in sample.reconstruction_parents))
               for sample in history.samples)),
        _array_binding(source.wall_temperature_k), source.phase_id,
        source.pressure_source_evidence_id, source.temperature_evidence_id,
        result.temperature_radius_m, result.mapping_evidence_id,
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _sample_wall_temperature(thermal_history: RadialHeatResult, radius_m: float) -> np.ndarray:
    """Linearly sample each stored radial field, including both wall surfaces."""
    thermal_history.require_current()
    radius = finite(radius_m, "mechanical temperature radius", positive=True)
    nodes = np.r_[thermal_history.inner_radius_m, thermal_history.radius_m,
                  thermal_history.outer_radius_m]
    if not np.isfinite(radius) or radius < nodes[0] or radius > nodes[-1]:
        raise ValueError("Mechanical temperature radius must lie within the thermal wall")
    result = np.empty(thermal_history.time_s.size)
    for index, row in enumerate(thermal_history.temperature_k):
        values = np.r_[thermal_history.inner_surface_temperature_k[index], row,
                       thermal_history.outer_surface_temperature_k[index]]
        result[index] = np.interp(radius, nodes, values)
    result = immutable_array(result, name="result")
    return result


@dataclass(frozen=True, slots=True)
class RadialThermalVesselBinding:
    """Retain pressure, computed thermal field and mapped mechanical history."""

    pressure_samples: CylinderStressSamples
    thermal_history: RadialHeatResult
    source_binding: CylinderVesselHistoryBinding
    temperature_radius_m: float
    mapping_evidence_id: str
    _identity_bindings: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)
    _content_sha256: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        self._validate_relationships()
        object.__setattr__(self, "_identity_bindings", self._object_bindings())
        object.__setattr__(self, "_content_sha256", _content_binding(self))

    def _object_bindings(self):
        history = self.source_binding.history
        pressure = self.pressure_samples
        thermal = self.thermal_history
        return (
            pressure, thermal, self.source_binding, pressure.geometry, *pressure.loads,
            thermal.material, thermal.inner_boundary, thermal.outer_boundary,
            history, history.context, history.samples, *history.samples,
        )

    def _validate_relationships(self):
        if type(self.pressure_samples) is not CylinderStressSamples:
            raise TypeError("Retain the typed cylinder pressure samples")
        if type(self.thermal_history) is not RadialHeatResult:
            raise TypeError("Retain the actual radial wall heat result")
        if type(self.source_binding) is not CylinderVesselHistoryBinding:
            raise TypeError("Retain the typed vessel-history mapping")
        if self.source_binding.pressure_samples is not self.pressure_samples:
            raise ValueError("Mapped history must retain the supplied pressure sample object")
        history = self.source_binding.history
        if type(history) is not VesselFailureHistory or type(history.context) is not VesselFailureContext:
            raise TypeError("Retain the original typed vessel history and service context")
        if history.native_trace is not None:
            raise ValueError("This sampled radial bridge does not admit an independent native trace")
        if any(
            sample.native_snapshot is not None or sample.native_state is not None
            or sample.native_fluid is not None or sample.reconstruction_parents
            for sample in history.samples
        ):
            raise ValueError("This exact-sample thermal bridge does not admit reconstructed/native load states")
        if not isinstance(self.mapping_evidence_id, str) or not self.mapping_evidence_id.strip():
            raise ValueError("Declare evidence for radial temperature-to-region mapping")
        radius = finite(self.temperature_radius_m, "mechanical temperature radius", positive=True)
        expected = _sample_wall_temperature(self.thermal_history, radius)
        if (self.pressure_samples.clock_id != self.thermal_history.clock_id
                or not np.array_equal(self.pressure_samples.time_s, self.thermal_history.time_s)):
            raise ValueError("Thermal and pressure histories must share an identical clock grid")
        geometry = self.pressure_samples.geometry
        if (geometry.inner_radius_m != self.thermal_history.inner_radius_m
                or geometry.outer_radius_m != self.thermal_history.outer_radius_m):
            raise ValueError("Thermal and pressure cylinder surfaces must match exactly")
        if not np.array_equal(expected, self.source_binding.wall_temperature_k):
            raise ValueError("Vessel history temperature differs from the retained radial field")
        if self.source_binding.temperature_evidence_id != self.thermal_history.evidence_id:
            raise ValueError("Vessel context must identify the radial heat result evidence")
        object.__setattr__(self, "temperature_radius_m", radius)

    def require_current(self):
        current = self._object_bindings()
        if not self._identity_bindings or any(
            value is not original
            for value, original in zip(current, self._identity_bindings, strict=True)
        ):
            raise ValueError("Radial failure binding lost its original source objects")
        self._validate_relationships()
        if _content_binding(self) != self._content_sha256:
            raise ValueError("Radial heat, pressure, history or mapping content changed")
        return self

    @property
    def history(self):
        self.require_current()
        return self.source_binding.history

    @property
    def wall_temperature_k(self):
        self.require_current()
        return self.source_binding.wall_temperature_k

    def predict_failure(
        self,
        evaluator,
        *,
        maximum_reconstruction_step_s: float,
        root_time_tolerance_s: float = 1.0e-7,
        maximum_evaluations: int = 10_000,
    ):
        """Pass the guarded P/T history to HELPR's pressure-only SIF route.

        Wall temperature affects the supplied material law. A radial-gradient
        thermoelastic stress history is not consumed by the current HELPR owner.
        """
        from .vessel_failure import (
            HelprVesselFailure,
            VesselFailurePrediction,
        )

        if type(evaluator) is not HelprVesselFailure:
            raise TypeError("Pass the actual existing HelprVesselFailure owner")
        try:
            self.require_current()
        except Exception as cause:
            raise RadialThermalVesselFailureError(
                "Radial source binding failed before HELPR evaluation",
                binding=self,
                cause=cause,
                stage="pre_evaluation_integrity",
            ) from cause
        try:
            prediction = evaluator.predict(
                self.source_binding.history,
                maximum_reconstruction_step_s=maximum_reconstruction_step_s,
                root_time_tolerance_s=root_time_tolerance_s,
                maximum_evaluations=maximum_evaluations,
            )
        except Exception as cause:
            raise RadialThermalVesselFailureError(
                "The guarded radial thermal history was rejected by the HELPR owner",
                binding=self,
                cause=cause,
                stage="helpr_evaluation",
            ) from cause
        if type(prediction) is not VesselFailurePrediction:
            cause = TypeError("HELPR failure owner must return its actual typed prediction")
            raise RadialThermalVesselFailureError(
                str(cause),
                binding=self,
                cause=cause,
                stage="invalid_prediction",
                prediction=prediction,
            ) from cause
        try:
            prediction.require_current()
        except Exception as cause:
            raise RadialThermalVesselFailureError(
                "HELPR failure report changed before radial-history handoff",
                binding=self,
                cause=cause,
                stage="invalid_prediction_receipt",
                prediction=prediction,
            ) from cause
        try:
            self.require_current()
        except Exception as cause:
            raise RadialThermalVesselFailureError(
                "Radial source binding changed during HELPR evaluation",
                binding=self,
                cause=cause,
                stage="post_evaluation_integrity",
                prediction=prediction,
            ) from cause
        return prediction


@dataclass(frozen=True, slots=True)
class RadialThermoelasticVesselBinding:
    """Bind the full-wall pressure-plus-thermal stress history to a vessel source.

    This host-side contract preserves a total Cauchy-stress field for a future
    native fracture consumer. It does not calculate stress intensity or alter the
    current pressure-only HELPR route.
    """

    vessel_binding: RadialThermalVesselBinding
    thermomechanical_history: RadialThermomechanicalHistory
    field_convention: str
    field_convention_evidence_id: str
    _identity_bindings: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)
    _contract_sha256: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        self._validate_relationships()
        object.__setattr__(self, "_identity_bindings", self._object_bindings())
        object.__setattr__(self, "_contract_sha256", self._contract_fingerprint())

    def _contract_fingerprint(self):
        return hashlib.sha256(repr((
            self.field_convention,
            self.field_convention_evidence_id,
        )).encode("utf-8")).hexdigest()

    def _object_bindings(self):
        history = self.thermomechanical_history
        stress = history.stress
        return (
            self.vessel_binding, self.thermomechanical_history,
            self.vessel_binding.pressure_samples, self.vessel_binding.thermal_history,
            stress, stress.geometry, stress.material, stress.loads,
            stress.temperature_profiles, *stress.loads, *stress.temperature_profiles,
            stress.time_s, stress.radius_m, stress.radial_stress_pa,
            stress.hoop_stress_pa, stress.axial_stress_pa,
        )

    def _validate_relationships(self):
        if type(self.vessel_binding) is not RadialThermalVesselBinding:
            raise TypeError("Pass the admitted radial pressure/temperature vessel binding")
        if type(self.thermomechanical_history) is not RadialThermomechanicalHistory:
            raise TypeError("Pass the actual paired radial heat and thermoelastic history")
        self.vessel_binding.require_current()
        self.thermomechanical_history.require_current()
        stress = self.thermomechanical_history.stress
        stress.require_current()
        if self.thermomechanical_history.heat is not self.vessel_binding.thermal_history:
            raise ValueError("Thermoelastic stress must use the exact heat result in the vessel binding")
        pressure = self.vessel_binding.pressure_samples
        if (stress.clock_id != pressure.clock_id
                or not np.array_equal(stress.time_s, pressure.time_s)):
            raise ValueError("Pressure, thermal and thermoelastic histories need one exact clock")
        if stress.geometry is not pressure.geometry:
            raise ValueError("Thermoelastic stress must retain the exact pressure-cylinder geometry")
        if len(stress.loads) != len(pressure.loads) or any(
            stress_load is not pressure_load
            for stress_load, pressure_load in zip(stress.loads, pressure.loads, strict=True)
        ):
            raise ValueError("Thermoelastic stress must retain the exact pressure-load objects")
        if (stress.radius_m[0] != stress.geometry.inner_radius_m
                or stress.radius_m[-1] != stress.geometry.outer_radius_m):
            raise ValueError("Thermoelastic stress field must span both cylinder surfaces")
        if self.field_convention != "total_pressure_plus_thermal":
            raise ValueError("This stress solve returns total pressure-plus-thermal stress")
        if (not isinstance(self.field_convention_evidence_id, str)
                or not self.field_convention_evidence_id.strip()):
            raise ValueError("Identify the declared total-stress field convention")

    def require_current(self):
        current = self._object_bindings()
        if (not self._identity_bindings
                or any(value is not original for value, original in zip(
                    current, self._identity_bindings, strict=True,
                ))):
            raise ValueError("Radial thermoelastic vessel binding lost original field/source objects")
        self._validate_relationships()
        if self._contract_fingerprint() != self._contract_sha256:
            raise ValueError("Radial thermoelastic field convention/evidence changed after binding")
        return self

    @property
    def total_stress_history(self):
        self.require_current()
        return self.thermomechanical_history.stress

    def sample_at(self, sample_index: int) -> RadialThermoelasticVesselSample:
        """Join one exact total-stress field with its original vessel loading sample."""
        self.require_current()
        if isinstance(sample_index, bool) or not isinstance(sample_index, (int, np.integer)):
            raise TypeError("Vessel stress sample index must be an integer, not a boolean")
        index = int(sample_index)
        if not 0 <= index < self.thermomechanical_history.stress.time_s.size:
            raise ValueError("Vessel stress sample index lies outside finite history support")
        stress_sample = self.thermomechanical_history.stress.stress_field_at(index)
        loading = self.vessel_binding.history.samples[index]
        return RadialThermoelasticVesselSample(self, stress_sample, loading)


@dataclass(frozen=True, slots=True)
class RadialThermoelasticVesselSample:
    """One exact-clock join of total wall stress and pressure/temperature loading."""

    binding: RadialThermoelasticVesselBinding
    stress_sample: RadialThermoelasticStressSample
    loading: VesselLoading
    _identity_bindings: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        self._validate_relationships()
        object.__setattr__(self, "_identity_bindings", (
            self.binding, self.stress_sample, self.stress_sample.stress_field,
            self.loading, self.binding.vessel_binding.history,
        ))

    def _validate_relationships(self):
        if type(self.binding) is not RadialThermoelasticVesselBinding:
            raise TypeError("Vessel stress sample requires its actual source binding")
        if type(self.stress_sample) is not RadialThermoelasticStressSample:
            raise TypeError("Vessel stress sample requires an exact typed stress snapshot")
        if type(self.loading) is not VesselLoading:
            raise TypeError("Vessel stress sample requires the actual vessel loading record")
        self.binding.require_current()
        self.stress_sample.require_current()
        index = self.stress_sample.sample_index
        source_history = self.binding.vessel_binding.history
        if (index >= len(source_history.samples)
                or source_history.samples[index] is not self.loading):
            raise ValueError("Vessel loading is not the original record at the selected index")
        stress_field = self.stress_sample.stress_field
        if (self.loading.time_s != self.stress_sample.time_s
                or self.stress_sample.clock_id != self.binding.thermomechanical_history.clock_id):
            raise ValueError("Vessel loading and total stress must share the exact clock sample")
        if (self.loading.internal_pressure_pa_absolute != stress_field.load.internal_pressure_pa
                or self.loading.external_pressure_pa_absolute != stress_field.load.external_pressure_pa):
            raise ValueError("Vessel loading pressures differ from the total-stress pressure load")
        if self.loading.wall_temperature_k != self.binding.vessel_binding.wall_temperature_k[index]:
            raise ValueError("Vessel loading temperature differs from the retained radial heat mapping")

    def require_current(self):
        current = (
            self.binding, self.stress_sample, self.stress_sample.stress_field,
            self.loading, self.binding.vessel_binding.history,
        )
        if (not self._identity_bindings
                or any(value is not original for value, original in zip(
                    current, self._identity_bindings, strict=True,
                ))):
            raise ValueError("Joined vessel/stress sample lost its original source objects")
        self._validate_relationships()
        return self

    @property
    def total_stress_field(self):
        self.require_current()
        return self.stress_sample.stress_field


@dataclass(frozen=True, slots=True)
class RadialFailureSeries:
    """Receiving signed SIF evaluations over exact common-clock samples.

    This exact-sample bridge does not interpolate between thermal solver times or
    represent nonuniform stress through the pressure-only HELPR owner. The caller's
    signed values are retained as supplied; no absolute-value conversion is applied.
    """

    binding: RadialThermoelasticVesselBinding
    calculator: object = dataclass_field(repr=False)
    stress_intensity_values_pa_sqrt_m: tuple[float, ...]
    calculation_evidence_id: str
    sampled_times_s: tuple[float, ...]
    maximum_sampled_sif_pa_sqrt_m: float
    maximum_sampled_index: int
    _binding_identity: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)
    _binding_fingerprint: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.binding) is not RadialThermoelasticVesselBinding:
            raise TypeError("Retain the original radial thermoelastic vessel binding")
        self.binding.require_current()
        if not callable(self.calculator):
            raise TypeError("Supply a caller crack/SIF calculation that consumes total-stress samples")
        if not isinstance(self.calculation_evidence_id, str) or not self.calculation_evidence_id.strip():
            raise ValueError("Declare crack geometry, SIF law and calculation applicability evidence")
        values, times = tuple(self.stress_intensity_values_pa_sqrt_m), tuple(self.sampled_times_s)
        expected = tuple(float(value) for value in self.binding.thermomechanical_history.time_s)
        times = tuple(finite(value, "sampled SIF time") for value in times)
        if len(values) != len(expected) or times != expected:
            raise ValueError("Keep one SIF value at every exact source thermal solver time")
        values = tuple(finite(value, "sampled signed stress intensity") for value in values)
        index = max(range(len(values)), key=values.__getitem__)
        if (isinstance(self.maximum_sampled_index, bool)
                or not isinstance(self.maximum_sampled_index, (int, np.integer))
                or int(self.maximum_sampled_index) != index
                or self.maximum_sampled_sif_pa_sqrt_m != values[index]):
            raise ValueError("Sampled SIF maximum differs from the retained native evaluations")
        object.__setattr__(self, "stress_intensity_values_pa_sqrt_m", values)
        object.__setattr__(self, "sampled_times_s", times)
        object.__setattr__(self, "maximum_sampled_index", index)
        object.__setattr__(self, "maximum_sampled_sif_pa_sqrt_m",
                           finite(self.maximum_sampled_sif_pa_sqrt_m,
                                  "maximum sampled signed stress intensity"))
        object.__setattr__(self, "_binding_identity", (self.binding, self.calculator))
        object.__setattr__(self, "_binding_fingerprint", _content_binding((
            self.binding, self.calculator, values, self.calculation_evidence_id,
            times, self.maximum_sampled_sif_pa_sqrt_m, index)))

    def require_current(self):
        self.binding.require_current()
        current = (self.binding, self.calculator)
        values = tuple(finite(value, "sampled signed stress intensity")
                       for value in self.stress_intensity_values_pa_sqrt_m)
        times = tuple(finite(value, "sampled SIF time") for value in self.sampled_times_s)
        expected = tuple(float(value) for value in self.binding.thermomechanical_history.time_s)
        if len(values) != len(expected) or times != expected:
            raise ValueError("Radial failure receipt no longer covers its exact source samples")
        if (isinstance(self.maximum_sampled_index, bool)
                or not isinstance(self.maximum_sampled_index, (int, np.integer))):
            raise ValueError("Maximum sampled SIF index must remain an integer")
        index = max(range(len(values)), key=values.__getitem__)
        maximum = finite(self.maximum_sampled_sif_pa_sqrt_m,
                         "maximum sampled signed stress intensity")
        if int(self.maximum_sampled_index) != index or maximum != values[index]:
            raise ValueError("Maximum SIF summary differs from the retained exact-sample values")
        if (len(current) != len(self._binding_identity)
                or any(a is not b for a, b in zip(current, self._binding_identity, strict=True))
                or _content_binding((self.binding, self.calculator, values,
                    self.calculation_evidence_id, times, maximum, index))
                    != self._binding_fingerprint):
            raise ValueError("Radial failure receipt lost its source or calculation identity")
        return self

    def first_sample_at_or_above(self, threshold_pa_sqrt_m: float, *,
                                 threshold_evidence_id: str):
        """Return the first exact SIF sample reaching a caller-supplied threshold.

        This reports sampled threshold attainment only; it does not interpolate
        an event time, predict failure, or qualify the threshold for a flaw.
        """
        self.require_current()
        threshold = finite(threshold_pa_sqrt_m, "caller SIF threshold", positive=True)
        if not isinstance(threshold_evidence_id, str) or not threshold_evidence_id.strip():
            raise ValueError("Declare evidence for the caller-supplied SIF threshold")
        for index, value in enumerate(self.stress_intensity_values_pa_sqrt_m):
            if value >= threshold:
                return SampledSifThresholdHit(
                    self, threshold, threshold_evidence_id, index,
                    self.sampled_times_s[index], value,
                ).require_current()
        return None

    def sampled_window(self, start_time_s: float, end_time_s: float):
        """Select an inclusive window whose endpoints are exact native samples.

        No SIF, stress or time values are interpolated. The returned view keeps
        global source indices so a report can be joined back to the thermal clock.
        """
        self.require_current()
        start = finite(start_time_s, "SIF window start time")
        end = finite(end_time_s, "SIF window end time")
        if end <= start:
            raise ValueError("SIF window endpoints must be strictly increasing")
        try:
            start_index = self.sampled_times_s.index(start)
            end_index = self.sampled_times_s.index(end)
        except ValueError as error:
            raise ValueError("SIF window endpoints must match exact native samples") from error
        return RadialFailureWindow(self, start_index, end_index).require_current()


@dataclass(frozen=True, slots=True)
class RadialFailureWindow:
    """Exact-sample view of one inclusive subrange of a radial SIF series."""

    series: RadialFailureSeries
    start_index: int
    end_index: int
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.series) is not RadialFailureSeries:
            raise TypeError("Retain the original radial failure series")
        self.series.require_current()
        if (isinstance(self.start_index, bool) or not isinstance(self.start_index, (int, np.integer))
                or isinstance(self.end_index, bool) or not isinstance(self.end_index, (int, np.integer))):
            raise TypeError("SIF window indices must be integers")
        start, end = int(self.start_index), int(self.end_index)
        if not 0 <= start < end < len(self.series.sampled_times_s):
            raise ValueError("SIF windows require two ordered in-range source samples")
        object.__setattr__(self, "start_index", start)
        object.__setattr__(self, "end_index", end)
        object.__setattr__(self, "_seal", self._signature())

    def _signature(self):
        payload = (id(self.series), self.start_index, self.end_index,
                   self.series.sampled_times_s[self.start_index:self.end_index + 1],
                   self.series.stress_intensity_values_pa_sqrt_m[self.start_index:self.end_index + 1])
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def require_current(self):
        self.series.require_current()
        if (not 0 <= self.start_index < self.end_index < len(self.series.sampled_times_s)
                or not self._seal or self._signature() != self._seal):
            raise ValueError("Radial failure window changed after exact-sample selection")
        return self

    @property
    def sampled_times_s(self):
        self.require_current()
        return self.series.sampled_times_s[self.start_index:self.end_index + 1]

    @property
    def stress_intensity_values_pa_sqrt_m(self):
        self.require_current()
        return self.series.stress_intensity_values_pa_sqrt_m[self.start_index:self.end_index + 1]

    @property
    def duration_s(self):
        times = self.sampled_times_s
        return finite(times[-1] - times[0], "sampled SIF window duration")

    @property
    def minimum_signed_sif_pa_sqrt_m(self):
        return min(self.stress_intensity_values_pa_sqrt_m)

    @property
    def maximum_signed_sif_pa_sqrt_m(self):
        return max(self.stress_intensity_values_pa_sqrt_m)

    @property
    def maximum_source_index(self):
        values = self.stress_intensity_values_pa_sqrt_m
        local = max(range(len(values)), key=values.__getitem__)
        return self.start_index + local


@dataclass(frozen=True, slots=True)
class SampledSifThresholdHit:
    """Evidence-bound exact sample at which a caller threshold is first reached."""

    series: RadialFailureSeries
    threshold_pa_sqrt_m: float
    threshold_evidence_id: str
    sample_index: int
    time_s: float
    sampled_sif_pa_sqrt_m: float

    def require_current(self):
        self.series.require_current()
        threshold = finite(self.threshold_pa_sqrt_m, "caller SIF threshold", positive=True)
        if not isinstance(self.threshold_evidence_id, str) or not self.threshold_evidence_id.strip():
            raise ValueError("Declare evidence for the caller-supplied SIF threshold")
        index = self.sample_index
        if isinstance(index, bool) or not isinstance(index, (int, np.integer)):
            raise TypeError("Sample index must be an integer")
        if not 0 <= int(index) < len(self.series.sampled_times_s):
            raise ValueError("Threshold hit must refer to an existing exact SIF sample")
        index = int(index)
        value = finite(self.sampled_sif_pa_sqrt_m, "sampled SIF at threshold")
        if (self.time_s != self.series.sampled_times_s[index]
                or value != self.series.stress_intensity_values_pa_sqrt_m[index]
                or value < threshold
                or any(previous >= threshold for previous in
                       self.series.stress_intensity_values_pa_sqrt_m[:index])):
            raise ValueError("Threshold receipt is not the first matching exact sample")
        return self


def evaluate_radial_stress_intensity_samples(binding, calculator, *, calculation_evidence_id):
    """Evaluate caller SIF law at each exact total-stress sample and retain values."""
    if type(binding) is not RadialThermoelasticVesselBinding:
        raise TypeError("Supply the exact radial thermoelastic vessel binding")
    if not callable(calculator):
        raise TypeError("Supply a caller SIF calculation that accepts total-stress samples")
    if not isinstance(calculation_evidence_id, str) or not calculation_evidence_id.strip():
        raise ValueError("Declare crack geometry, SIF law and calculation applicability evidence")
    binding.require_current()
    times, values = [], []
    for index, time_s in enumerate(binding.thermomechanical_history.time_s):
        sample = binding.sample_at(index)
        value = finite(calculator(sample), "sampled signed stress intensity")
        times.append(float(time_s))
        values.append(value)
        binding.require_current()
    values = tuple(values)
    index = max(range(len(values)), key=values.__getitem__)
    result = RadialFailureSeries(binding, calculator, values, calculation_evidence_id,
        tuple(times), values[index], index)
    return result.require_current()


def bind_radial_thermoelastic_history_to_vessel(
    vessel_binding: RadialThermalVesselBinding,
    thermomechanical_history: RadialThermomechanicalHistory,
    *,
    field_convention: str,
    field_convention_evidence_id: str,
) -> RadialThermoelasticVesselBinding:
    """Bind an exact-clock full-wall total stress field to the retained vessel sources.

    The thermoelastic solver already includes both surface pressure tractions and
    thermal strain. The field convention is therefore explicit and pressure is not
    eligible for a second addition by a downstream SIF implementation.
    """
    return RadialThermoelasticVesselBinding(
        vessel_binding,
        thermomechanical_history,
        field_convention,
        field_convention_evidence_id,
    )


class RadialThermalVesselFailureError(RuntimeError):
    """Retain the radial source binding and native HELPR result/failure."""

    def __init__(self, message, *, binding, cause, stage, prediction=None):
        if stage not in {
            "pre_evaluation_integrity", "helpr_evaluation",
            "invalid_prediction", "post_evaluation_integrity",
        }:
            raise ValueError("Unknown radial-vessel failure composition stage")
        super().__init__(message)
        self.binding = binding
        self.cause = cause
        self.stage = stage
        self.prediction = prediction


def bind_radial_thermal_history_to_vessel(
    pressure_samples: CylinderStressSamples,
    context: VesselFailureContext,
    thermal_history: RadialHeatResult,
    *,
    temperature_radius_m: float,
    phase_id: str,
    pressure_source_evidence_id: str,
    temperature_mapping_evidence_id: str,
    reconstruction_evidence_id: str,
) -> RadialThermalVesselBinding:
    """Create a no-time-interpolation pressure/thermal failure input history.

    Temperature is linearly sampled in radius between the actual thermal cell
    centers and retained surface temperatures. The requested radial point and
    mapping-evidence identity are explicit; applicability of that point to a
    crack or weld is a separate engineering qualification. Temporal grids and
    cylinder surfaces must match exactly. No pressure or temperature extrapolation
    is performed.
    """
    if type(pressure_samples) is not CylinderStressSamples:
        raise TypeError("Pass actual typed cylinder pressure samples")
    if type(context) is not VesselFailureContext:
        raise TypeError("Pass the actual typed vessel-failure context")
    if type(thermal_history) is not RadialHeatResult:
        raise TypeError("Pass an actual radial heat result")
    if pressure_samples.clock_id != context.clock_id:
        raise ValueError("Vessel context and pressure sample clock identities differ")
    if thermal_history.clock_id != context.clock_id:
        raise ValueError("Vessel context and thermal history clock identities differ")
    if not np.array_equal(pressure_samples.time_s, thermal_history.time_s):
        raise ValueError("Thermal and pressure histories require identical sample times")
    geometry = pressure_samples.geometry
    if (geometry.inner_radius_m != thermal_history.inner_radius_m
            or geometry.outer_radius_m != thermal_history.outer_radius_m):
        raise ValueError("Pressure and thermal cylinder surfaces must match exactly")
    if context.wall_temperature_evidence_id != thermal_history.evidence_id:
        raise ValueError("Vessel context must identify the radial thermal evidence")
    if not isinstance(temperature_mapping_evidence_id, str) or not temperature_mapping_evidence_id.strip():
        raise ValueError("Declare the radial-to-mechanical temperature mapping evidence")
    temperatures = _sample_wall_temperature(thermal_history, temperature_radius_m)
    source = bind_cylinder_samples_to_vessel_history(
        pressure_samples,
        context,
        temperatures,
        phase_id=phase_id,
        pressure_source_evidence_id=pressure_source_evidence_id,
        temperature_evidence_id=thermal_history.evidence_id,
        reconstruction_evidence_id=reconstruction_evidence_id,
    )
    return RadialThermalVesselBinding(
        pressure_samples,
        thermal_history,
        source,
        finite(temperature_radius_m, "mechanical temperature radius", positive=True),
        temperature_mapping_evidence_id,
    )


__all__ = [
    "RadialFailureSeries",
    "RadialFailureWindow",
    "SampledSifThresholdHit",
    "RadialThermalVesselBinding",
    "RadialThermalVesselFailureError",
    "RadialThermoelasticVesselBinding",
    "RadialThermoelasticVesselSample",
    "bind_radial_thermal_history_to_vessel",
    "bind_radial_thermoelastic_history_to_vessel",
    "evaluate_radial_stress_intensity_samples",
]
