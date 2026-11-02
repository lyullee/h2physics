import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.observations import ObservationTable, Variable, split_experiments
from h2physics.research import BoundedParameter, assess_held_out, fit_observations

X, Y = Variable("x", "current_density", "A/m2"), Variable("y", "voltage", "V")


def observations(origin=Origin.MEASURED):
    x = np.arange(12.)
    values = np.c_[x, 2*x+3]
    valid = np.ones_like(values, bool)
    values[2, 1] = np.nan
    valid[2, 1] = False
    return ObservationTable(values, (X, Y), valid, tuple(f"row{i}" for i in range(12)),
        tuple("A" if i < 6 else "B" for i in range(12)), (Origin.SYNTHETIC, origin), "authored")


def test_bounded_fit_and_whole_group_comparison_recover_known_parameters():
    partition = split_experiments(observations(), {"B"})
    def predict(table, p):
        return p["slope"]*table.column("x")[0]+p["intercept"]
    result = fit_observations(partition.fitting, inputs=(X,), response=Y,
        parameters=(BoundedParameter("slope", 1, 0, 5, 1), BoundedParameter("intercept", 1, 0, 5, 1)),
        predictor=predict, model_id="authored-linear-v1")
    assert result.parameter_values["slope"] == pytest.approx(2)
    assert result.parameter_values["intercept"] == pytest.approx(3)
    assert result.omitted_row_ids == ("row2",)
    assert result.numerical_rank == 2
    assert assess_held_out(result, partition.held_out, predictor=predict).root_mean_square_error < 1e-6
    with pytest.raises(ValueError, match="experiment group"):
        assess_held_out(result, partition.fitting, predictor=predict)


def test_rank_deficiency_and_unknown_origin_are_reported_without_validation_claim():
    table = observations(Origin.UNRESOLVED)
    parameters = (BoundedParameter("a", 1, 0, 5, 1), BoundedParameter("b", 1, 0, 5, 1))
    def predict(table, p):
        return (p["a"]+p["b"])*table.column("x")[0]
    with pytest.raises(ValueError, match="measured/reconstructed"):
        fit_observations(table, inputs=(X,), response=Y, parameters=parameters, predictor=predict, model_id="authored-collinear-v1")
    result = fit_observations(table, inputs=(X,), response=Y, parameters=parameters, predictor=predict,
                              purpose="curve_reproduction", model_id="authored-collinear-v1")
    assert result.numerical_rank == 1 and np.isinf(result.scaled_condition_number)
    assert not result.validation_qualified
