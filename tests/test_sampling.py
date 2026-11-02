import numpy as np
import pytest

from h2physics.core import Origin, TimeSeries
from h2physics.data.sampling import bin_means, linear_sample


def source():
    return TimeSeries(np.array([0., 1., 2., 5.]), np.array([[0.], [2.], [4.], [10.]]),
                      ("temperature",), ("K",), np.array([[True], [True], [False], [True]]),
                      "common-clock", Origin.MEASURED, "authored-sampling-fixture", ("temperature",))


def test_linear_operator_preserves_exact_points_masks_gaps_and_does_not_extrapolate():
    result = linear_sample(source(), [-1., 0., .5, 1., 1.5, 3., 5., 6.],
                           clock_id="common-clock", maximum_gap_s=1.1)
    np.testing.assert_array_equal(result.valid[:, 0], [False, True, True, True, False, False, True, False])
    np.testing.assert_allclose(result.values[[1, 2, 3, 6], 0], [0., 1., 2., 10.])
    assert result.origin == Origin.RECONSTRUCTED
    with pytest.raises(ValueError, match="same.*clock"):
        linear_sample(source(), [0., .5], clock_id="other", maximum_gap_s=1.)


def test_explicit_bins_preserve_counts_and_require_minimum_samples():
    result = bin_means(source(), [0., 2., 5.], clock_id="common-clock", minimum_samples=2)
    np.testing.assert_array_equal(result.valid_sample_counts[:, 0], [2, 1])
    np.testing.assert_allclose(result.series.time_s, [1., 3.5])
    assert result.series.values[0, 0] == 1.
    assert not result.series.valid[1, 0]
    assert not result.valid_sample_counts.flags.writeable
    assert not result.edges_s.flags.writeable


def test_no_empty_or_backward_sampling_grid():
    for grid in ([], [1., 0.], [1., 1.]):
        with pytest.raises(ValueError, match="strictly increasing"):
            linear_sample(source(), grid, clock_id="common-clock", maximum_gap_s=1.)
