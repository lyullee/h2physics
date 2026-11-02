"""Bounded least squares, scaled Jacobian diagnostics and experiment-disjoint assessment.

The numerical provider is SciPy's maintained implementation:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html
Neither optimizer success nor a full numerical Jacobian rank establishes scientific
identifiability, independent validation, or a parameter confidence interval.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

import numpy as np
from scipy.optimize import least_squares

from ..core import Origin, finite, immutable_array
from ..observations import ObservationTable, Variable

Predictor = Callable[[ObservationTable, Mapping[str, float]], np.ndarray]


@dataclass(frozen=True, slots=True)
class BoundedParameter:
    name: str
    initial: float
    lower: float
    upper: float
    scale: float

    def __post_init__(self):
        if not self.name:
            raise ValueError("Fitted parameters require names")
        for name in ("initial", "lower", "upper"):
            finite(getattr(self, name), name)
        finite(self.scale, "parameter scale", positive=True)
        if not self.lower < self.upper or not self.lower <= self.initial <= self.upper:
            raise ValueError("Parameter start must lie within increasing declared bounds")


@dataclass(frozen=True, slots=True)
class FitResult:
    parameter_values: Mapping[str, float]
    purpose: str
    model_id: str
    fitting_data_sha256: str
    input_variables: tuple[Variable, ...]
    response_variable: Variable
    fitting_row_ids: tuple[str, ...]
    fitting_experiment_ids: tuple[str, ...]
    omitted_row_ids: tuple[str, ...]
    residual_normalization: np.ndarray
    scaled_jacobian_singular_values: np.ndarray
    numerical_rank: int
    numerical_rank_relative_threshold: float
    scaled_condition_number: float
    root_mean_square_error: float
    optimizer_cost: float
    function_evaluations: int
    active_parameter_bounds: tuple[tuple[str, int], ...]
    optimizer_loss: str = "linear"
    optimizer_f_scale: float = 1.0

    def __post_init__(self):
        object.__setattr__(self, "parameter_values", MappingProxyType(dict(self.parameter_values)))
        if self.optimizer_loss not in {"linear", "soft_l1", "huber", "cauchy", "arctan"}:
            raise ValueError("Fit result must retain a supported SciPy least-squares loss")
        finite(self.optimizer_f_scale, "robust-loss transition scale", positive=True)
        for name in ("residual_normalization", "scaled_jacobian_singular_values"):
            values = immutable_array(getattr(self, name), dtype=float, name=name)
            object.__setattr__(self, name, values)

    @property
    def validation_qualified(self):
        return False


@dataclass(frozen=True, slots=True)
class HeldOutComparison:
    observation_count: int
    experiment_ids: tuple[str, ...]
    response_unit: str
    bias: float
    root_mean_square_error: float
    mean_absolute_error: float
    maximum_absolute_error: float
    purpose: str
    omitted_row_ids: tuple[str, ...]
    observation_data_sha256: str

    @property
    def validation_qualified(self):
        # Group disjointness alone cannot establish apparatus/source independence.
        return False


def _prepare(table, inputs, response, *, purpose):
    for variable in (*inputs, response):
        table.column(variable.name, expected=variable)
    index = [variable.name for variable in table.variables].index(response.name)
    if purpose == "parameter_estimation" and table.origins[index] not in {Origin.MEASURED, Origin.RECONSTRUCTED}:
        raise ValueError("Parameter estimation requires a measured/reconstructed target; use explicit curve_reproduction for other origins")
    mask = table.complete_rows(*(variable.name for variable in (*inputs, response)))
    if not np.any(mask):
        raise ValueError("No jointly valid observations remain")
    return table.select_rows(mask), tuple(row for row, keep in zip(table.row_ids, mask, strict=True) if not keep), mask


def _prediction(predictor, table, parameters):
    values = np.asarray(predictor(table, MappingProxyType(dict(parameters))), dtype=float)
    if values.shape != (len(table.values),) or not np.all(np.isfinite(values)):
        raise ValueError("The observation operator must return a finite prediction for every retained row")
    return values


def fit_observations(table: ObservationTable, *, inputs: tuple[Variable, ...], response: Variable,
                     parameters: tuple[BoundedParameter, ...], predictor: Predictor,
                     model_id: str,
                     residual_normalization=1.,
                     purpose: Literal["parameter_estimation", "curve_reproduction"] = "parameter_estimation",
                     rank_relative_threshold: float = 1e-8,
                     maximum_function_evaluations: int = 1000,
                     loss: Literal["linear", "soft_l1", "huber", "cauchy", "arctan"] = "linear",
                     f_scale: float = 1.0) -> FitResult:
    """Fit a user-supplied native observation operator in the response's declared unit.

    Residual normalization is a declared numerical scale, not automatically a
    measurement standard deviation. Invalid rows are omitted with identities.
    Experiment grouping and the fitting/held-out choice are made before this call.
    Finite bounds and meaningful parameter scales are required; no covariance or
    confidence interval is manufactured from a zero or small fitting residual.
    """
    if not model_id:
        raise ValueError("Record the native observation-model identity")
    if purpose not in {"parameter_estimation", "curve_reproduction"}:
        raise ValueError("Select an explicit fitting purpose")
    if loss not in {"linear", "soft_l1", "huber", "cauchy", "arctan"}:
        raise ValueError("Select a supported SciPy least-squares loss")
    finite(f_scale, "robust-loss transition scale", positive=True)
    if not parameters or len({p.name for p in parameters}) != len(parameters) or not inputs:
        raise ValueError("Declare unique parameters and input variables")
    finite(rank_relative_threshold, "rank relative threshold", positive=True)
    if rank_relative_threshold >= 1:
        raise ValueError("The relative rank threshold must be below one")
    selected, omitted, mask = _prepare(table, inputs, response, purpose=purpose)
    if len(selected.values) < len(parameters):
        raise ValueError("Fewer valid observations than fitted parameters")
    normalization = np.broadcast_to(np.asarray(residual_normalization, dtype=float), (len(table.values),))[mask].copy()
    if not np.all(np.isfinite(normalization)) or np.any(normalization <= 0):
        raise ValueError("Residual normalizations must be positive and finite")
    observed, _ = selected.column(response.name)
    names = [parameter.name for parameter in parameters]

    def residual(values):
        predicted = _prediction(predictor, selected, dict(zip(names, values, strict=True)))
        return (predicted-observed)/normalization

    scales = np.array([p.scale for p in parameters])
    result = least_squares(residual, [p.initial for p in parameters],
        bounds=([p.lower for p in parameters], [p.upper for p in parameters]),
        x_scale=scales, max_nfev=maximum_function_evaluations,
        loss=loss, f_scale=f_scale)
    if not result.success:
        raise RuntimeError(f"Parameter optimization did not converge: {result.message}")
    singular = np.linalg.svd(result.jac * scales[None, :], compute_uv=False)
    rank = int(np.count_nonzero(singular > (singular[0]*rank_relative_threshold)))
    condition = float(singular[0]/singular[-1]) if rank == len(parameters) else float("inf")
    parameter_values = dict(zip(names, result.x, strict=True))
    error = _prediction(predictor, selected, parameter_values)-observed
    return FitResult(parameter_values, purpose, model_id, selected.content_sha256,
        tuple(inputs), response, selected.row_ids,
        tuple(sorted(set(selected.experiment_ids))), omitted, normalization, singular, rank,
        rank_relative_threshold, condition, float(np.sqrt(np.mean(error**2))), float(result.cost),
        result.nfev, tuple(zip(names, map(int, result.active_mask), strict=True)), loss, f_scale)


def assess_held_out(fit: FitResult, table: ObservationTable, *, predictor: Predictor) -> HeldOutComparison:
    """Compare new groups without calling group disjointness independent validation."""
    if set(table.row_ids).intersection(fit.fitting_row_ids) or set(table.experiment_ids).intersection(fit.fitting_experiment_ids):
        raise ValueError("Held-out comparison must exclude every fitted row and experiment group")
    selected, omitted, _ = _prepare(table, fit.input_variables, fit.response_variable, purpose=fit.purpose)
    observed, _ = selected.column(fit.response_variable.name)
    error = _prediction(predictor, selected, fit.parameter_values)-observed
    return HeldOutComparison(len(error), tuple(sorted(set(selected.experiment_ids))),
        fit.response_variable.unit, float(np.mean(error)), float(np.sqrt(np.mean(error**2))),
        float(np.mean(abs(error))), float(np.max(abs(error))), fit.purpose, omitted, selected.content_sha256)
