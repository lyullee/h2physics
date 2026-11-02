"""Linear generalized structural response to a supplied pressure waveform.

The equation is M*x'' + C*x' + K*x = A_eff*p(t). Transformation factors,
failure limits and reflected/net pressure must be supplied for the actual
structure. See UFC 3-340-02: https://www.wbdg.org/ffc/army-coe/ufc/ufc-3-340-02
No resistance table, empirical blast curve or plastic failure law is bundled.
"""

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from ..core import _real_numeric_array, finite, immutable_array
from ..pressure_loads import PressureTimeHistory


@dataclass(frozen=True, slots=True)
class LinearSDOF:
    """Generalized quantities must all use the same displacement coordinate."""

    mass_kg: float
    stiffness_n_m: float
    damping_n_s_m: float
    effective_loaded_area_m2: float
    model_id: str

    def __post_init__(self):
        for name in ("mass_kg", "stiffness_n_m", "effective_loaded_area_m2"):
            finite(getattr(self, name), name, positive=True)
        if finite(self.damping_n_s_m, "damping") < 0:
            raise ValueError("Damping must be nonnegative")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("Generalized structural model identity is required")

    @property
    def natural_angular_frequency_rad_s(self):
        return float(np.sqrt(self.stiffness_n_m / self.mass_kg))


@dataclass(frozen=True, slots=True)
class SDOFResponse:
    model: LinearSDOF
    load: PressureTimeHistory
    time_s: np.ndarray
    displacement_m: np.ndarray
    velocity_m_s: np.ndarray
    acceleration_m_s2: np.ndarray
    restoring_force_n: np.ndarray
    kinetic_energy_j: np.ndarray
    elastic_energy_j: np.ndarray
    input_work_j: np.ndarray
    damping_dissipation_j: np.ndarray
    energy_residual_j: np.ndarray

    def __post_init__(self):
        for name in ("time_s", "displacement_m", "velocity_m_s", "acceleration_m_s2",
                     "restoring_force_n", "kinetic_energy_j", "elastic_energy_j",
                     "input_work_j", "damping_dissipation_j", "energy_residual_j"):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.ndim != 1 or not np.all(np.isfinite(value)):
                raise ValueError("Response arrays must be finite vectors")
            if name != "time_s" and value.shape != np.shape(self.time_s):
                raise ValueError("Response vectors must share one sampling clock")
            object.__setattr__(self, name, immutable_array(value))


def solve_linear_sdof(model: LinearSDOF, load: PressureTimeHistory, time_s, *,
                      initial_displacement_m=0., initial_velocity_m_s=0.,
                      relative_tolerance=1e-9, absolute_tolerance=1e-11) -> SDOFResponse:
    """Integrate at every waveform corner, then sample the requested times.

    Initial conditions belong to ``time_s[0]``, which must equal the load's first
    timestamp. The output may continue into free vibration after load support.
    Work and damping are integrated as states, independently of output cadence.
    """
    if type(model) is not LinearSDOF or type(load) is not PressureTimeHistory:
        raise TypeError("Supply LinearSDOF and actual-event PressureTimeHistory objects")
    time = _real_numeric_array(time_s, "response time")
    if (time.ndim != 1 or len(time) < 2 or not np.all(np.isfinite(time))
            or np.any(np.diff(time) <= 0) or time[0] != load.time_s[0]):
        raise ValueError("Increasing response times must start at the load's first timestamp")
    x0 = finite(initial_displacement_m, "initial displacement")
    v0 = finite(initial_velocity_m_s, "initial velocity")
    rtol = finite(relative_tolerance, "relative tolerance", positive=True)
    atol = finite(absolute_tolerance, "absolute tolerance", positive=True)
    if not 1e-13 <= rtol <= 1e-3 or not 1e-15 <= atol <= 1e-3:
        raise ValueError("Declare numerical tolerances within supported integration limits")
    cuts = np.unique(np.r_[time[0], load.time_s[(load.time_s > time[0])
                                             & (load.time_s < time[-1])], time[-1]])
    output = np.empty((4, len(time)))
    state = np.array([x0, v0, 0., 0.])
    output[:, 0] = state
    period = 2*np.pi/model.natural_angular_frequency_rad_s
    for start, end in zip(cuts[:-1], cuts[1:], strict=True):
        # Within a segment the input is linear. Evaluating endpoints with the
        # segment's own interpolation avoids crossing a declared endpoint jump.
        if start >= load.time_s[-1]:
            p0 = slope = 0.
        else:
            p0 = float(load.at(start))
            slope = (float(load.at(end))-p0)/(end-start)

        def rhs(t, y):
            x, velocity = y[:2]
            force = model.effective_loaded_area_m2*(p0+slope*(t-start))
            return (velocity,
                    (force-model.damping_n_s_m*velocity-model.stiffness_n_m*x)/model.mass_kg,
                    force*velocity, model.damping_n_s_m*velocity**2)

        integration = solve_ivp(rhs, (start, end), state, method="DOP853",
                                rtol=rtol, atol=atol, dense_output=True,
                                max_step=min(period/32, (end-start)/4))
        if not integration.success:
            raise RuntimeError(f"Structural integration failed: {integration.message}")
        selected = (time > start) & (time <= end)
        if np.any(selected):
            output[:, selected] = integration.sol(time[selected])
        state = integration.y[:, -1]
    x, velocity, work, dissipation = output
    restoring = model.stiffness_n_m*x
    acceleration = (model.effective_loaded_area_m2*load.at(time)
                    -model.damping_n_s_m*velocity-restoring)/model.mass_kg
    kinetic = .5*model.mass_kg*velocity**2
    elastic = .5*model.stiffness_n_m*x**2
    initial_energy = .5*model.mass_kg*v0**2+.5*model.stiffness_n_m*x0**2
    residual = kinetic+elastic-initial_energy-work+dissipation
    return SDOFResponse(model, load, time, x, velocity, acceleration, restoring,
                        kinetic, elastic, work, dissipation, residual)
