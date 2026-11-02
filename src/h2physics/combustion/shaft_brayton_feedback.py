"""Speed-dependent mapped gas-path powers for the existing shaft integrator.

Native Cantera and the admitted component maps retain gas-path ownership.
This module binds physical rotor speed to both corrected map coordinates;
it supplies no speed correction, machine map, controller or thermodynamics.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from math import isclose

from ..core import finite
from .compressor_map import MapMatchedBraytonInputs, MapMatchedBraytonRun, run_map_matched_brayton


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label}")
    return value.strip()


@dataclass(frozen=True, slots=True)
class MapMatchedShaftPowerEvaluation:
    """One actual gas-path evaluation at an ODE trial time and rotor speed."""

    time_s: float
    speed_rad_s: float
    compressor_corrected_speed: float
    turbine_corrected_speed: float
    native_run: MapMatchedBraytonRun = field(repr=False, compare=False)
    native_phase: object = field(repr=False, compare=False)
    speed_mapping_evidence_id: str

    def __post_init__(self):
        object.__setattr__(self, "time_s", finite(self.time_s, "trial time"))
        for name in ("speed_rad_s", "compressor_corrected_speed", "turbine_corrected_speed"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        object.__setattr__(self, "speed_mapping_evidence_id", _text(
            self.speed_mapping_evidence_id, "physical-to-corrected-speed evidence"))
        self.require_current()

    def require_current(self):
        if type(self.native_run) is not MapMatchedBraytonRun:
            raise TypeError("Retain an actual mapped Brayton run")
        self.native_run.require_current()
        inputs = self.native_run.inputs
        if (inputs.compressor_corrected_speed != self.compressor_corrected_speed
                or inputs.turbine_corrected_speed != self.turbine_corrected_speed):
            raise ValueError("Gas-path map speeds differ from the rotor-speed projection")
        return self

    @property
    def turbine_power_w(self):
        self.require_current()
        return finite(self.native_run.shaft_ledger.turbine_power_w, "native turbine power")

    @property
    def compressor_power_w(self):
        self.require_current()
        return finite(self.native_run.shaft_ledger.compressor_power_w, "native compressor power")


@dataclass(frozen=True, slots=True)
class MapMatchedBraytonShaftFeedback:
    """Caller-declared speed correction and operating law, native power owner.

    ``corrected_speeds(time_s, omega_rad_s)`` returns compressor and turbine
    corrected speeds in the units of the admitted maps. ``operating_inputs``
    receives those two values as its last arguments and returns a complete
    MapMatchedBraytonInputs. Actual flow admission and mapped efficiencies are
    checked by the existing cycle composition. The operating law must specify
    the remaining pressure-ratio, flow and fuel boundaries; it is not inferred
    from the shaft energy equation. Factories must return fresh native phases.
    """

    phase_factory: Callable = field(repr=False, compare=False)
    corrected_speeds: Callable = field(repr=False, compare=False)
    operating_inputs: Callable = field(repr=False, compare=False)
    feedback_id: str
    shaft_id: str
    power_basis_id: str
    speed_mapping_evidence_id: str
    operating_law_evidence_id: str
    maximum_evaluations: int = 10000
    _signature: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        for name in ("phase_factory", "corrected_speeds", "operating_inputs"):
            if not callable(getattr(self, name)):
                raise TypeError(f"{name} must be callable")
        for name in ("feedback_id", "shaft_id", "power_basis_id",
                     "speed_mapping_evidence_id", "operating_law_evidence_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if (isinstance(self.maximum_evaluations, bool)
                or not isinstance(self.maximum_evaluations, int)
                or self.maximum_evaluations < 1):
            raise ValueError("maximum_evaluations must be a positive integer")
        object.__setattr__(self, "_signature", self._payload())

    def _payload(self):
        return (id(self.phase_factory), id(self.corrected_speeds), id(self.operating_inputs),
                self.feedback_id, self.shaft_id, self.power_basis_id,
                self.speed_mapping_evidence_id, self.operating_law_evidence_id,
                self.maximum_evaluations)

    def require_current(self):
        if self._payload() != self._signature:
            raise ValueError("Shaft gas-path configuration changed")
        return self

    def evaluate(self, time_s, speed_rad_s, *, previous_phase_ids=frozenset()):
        self.require_current()
        time = finite(time_s, "gas-path trial time")
        speed = finite(speed_rad_s, "physical rotor speed", positive=True)
        coordinates = tuple(self.corrected_speeds(time, speed))
        if len(coordinates) != 2:
            raise ValueError("Map-speed projection must return exactly two coordinates")
        compressor, turbine = (finite(x, "corrected map speed", positive=True)
                               for x in coordinates)
        inputs = self.operating_inputs(time, speed, compressor, turbine)
        if type(inputs) is not MapMatchedBraytonInputs:
            raise TypeError("Operating law must return MapMatchedBraytonInputs")
        if (not isclose(inputs.compressor_corrected_speed, compressor, rel_tol=1.e-12, abs_tol=0.)
                or not isclose(inputs.turbine_corrected_speed, turbine, rel_tol=1.e-12, abs_tol=0.)):
            raise ValueError("Operating law changed the mapped rotor-speed coordinates")
        if inputs.speed_link_evidence_id != self.speed_mapping_evidence_id:
            raise ValueError("Gas path and rotor need the same speed-mapping evidence")
        phase = self.phase_factory()
        if id(phase) in previous_phase_ids:
            raise ValueError("Gas-path phase factory must return a fresh native phase per evaluation")
        run = run_map_matched_brayton(phase, inputs)
        self.require_current()
        return MapMatchedShaftPowerEvaluation(
            time, speed, inputs.compressor_corrected_speed, inputs.turbine_corrected_speed,
            run, phase, self.speed_mapping_evidence_id)


class ShaftFeedbackEvaluationError(RuntimeError):
    """Gas-path failure with prior trial evaluations, not an accepted trajectory."""

    def __init__(self, time_s, speed_rad_s, evaluations, cause):
        super().__init__(f"Shaft gas-path evaluation failed at t={time_s}, omega={speed_rad_s}: {cause}")
        self.time_s = time_s
        self.speed_rad_s = speed_rad_s
        self.trial_evaluations = tuple(evaluations)
        self.cause = cause


__all__ = ["MapMatchedBraytonShaftFeedback", "MapMatchedShaftPowerEvaluation",
           "ShaftFeedbackEvaluationError"]
