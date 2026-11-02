"""Explicit observation operators on an already declared common clock.

Neither operation estimates a clock shift, fills a missing endpoint or creates
independent observations. Counts are sample counts, not statistical replicates.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ..core import Origin, TimeSeries, finite, immutable_array


def _clock_grid(values, series, clock_id):
    grid = np.array(values, dtype=float, copy=True)
    if clock_id != series.clock_id:
        raise ValueError("Sampling requires the same explicitly declared clock")
    if grid.ndim != 1 or not grid.size or not np.all(np.isfinite(grid)) or np.any(np.diff(grid) <= 0):
        raise ValueError("Sampling grid must be finite, nonempty and strictly increasing")
    return grid


def linear_sample(series: TimeSeries, time_s, *, clock_id: str,
                  maximum_gap_s: float) -> TimeSeries:
    """Linearly interpolate valid bracketing samples within the declared gap limit.

    Unsupported points are masked. Exact valid source samples remain available
    regardless of neighboring gaps. Extrapolation is never performed.
    """
    grid = _clock_grid(time_s, series, clock_id)
    gap = finite(maximum_gap_s, "maximum_gap_s", positive=True)
    time = series.time_s
    if not time.size:
        raise ValueError("Cannot sample an empty source")
    values = np.full((len(grid), len(series.channels)), np.nan)
    valid = np.zeros(values.shape, dtype=bool)
    for row, target in enumerate(grid):
        right = int(np.searchsorted(time, target))
        if right < len(time) and time[right] == target:
            valid[row] = series.valid[right]
            values[row] = np.where(valid[row], series.values[right], np.nan)
        elif 0 < right < len(time) and time[right] - time[right-1] <= gap:
            weight = (target-time[right-1]) / (time[right]-time[right-1])
            valid[row] = series.valid[right-1] & series.valid[right]
            values[row] = np.where(valid[row], (1-weight)*series.values[right-1]
                                   + weight*series.values[right], np.nan)
    return TimeSeries(grid, values, series.channels, series.units, valid, clock_id,
                       Origin.RECONSTRUCTED, "linear-sample:" + series.source_id,
                       series.quantities, series.basis_ids)


@dataclass(frozen=True, slots=True)
class BinnedSeries:
    series: TimeSeries
    valid_sample_counts: NDArray[np.int64]
    edges_s: NDArray[np.float64]

    def __post_init__(self):
        counts = np.array(self.valid_sample_counts, dtype=np.int64, copy=True)
        edges = np.array(self.edges_s, dtype=float, copy=True)
        if counts.shape != self.series.values.shape or np.any(counts < 0):
            raise ValueError("Bin counts must match series channels and be nonnegative")
        if (edges.shape != (len(self.series.time_s)+1,) or not np.all(np.isfinite(edges))
                or np.any(np.diff(edges) <= 0)):
            raise ValueError("Bin edges must bound each sample interval")
        counts = immutable_array(counts, name="valid_sample_counts")
        edges = immutable_array(edges, name="edges_s")
        object.__setattr__(self, "valid_sample_counts", counts)
        object.__setattr__(self, "edges_s", edges)


def bin_means(series: TimeSeries, edges_s, *, clock_id: str,
              minimum_samples: int) -> BinnedSeries:
    """Arithmetic means in [left, right) bins, with a closed final right endpoint.

    This is sample weighting, not a time-weighted average. The caller must choose
    appropriate bins/counts for the actual recorder cadence. No uncertainty or
    interval coverage is inferred from the count alone.
    """
    edges = _clock_grid(edges_s, series, clock_id)
    if len(edges) < 2:
        raise ValueError("Binning needs at least two edges")
    if isinstance(minimum_samples, bool) or not isinstance(minimum_samples, int) or minimum_samples < 1:
        raise ValueError("minimum_samples must be a positive integer")
    bins = np.searchsorted(edges, series.time_s, side="right") - 1
    bins[series.time_s == edges[-1]] = len(edges)-2
    selected = (bins >= 0) & (bins < len(edges)-1)
    counts = np.zeros((len(edges)-1, len(series.channels)), dtype=np.int64)
    means = np.full(counts.shape, np.nan)
    for column in range(len(series.channels)):
        take = selected & series.valid[:, column]
        counts[:, column] = np.bincount(bins[take], minlength=len(edges)-1)
        total = np.bincount(bins[take], weights=series.values[take, column], minlength=len(edges)-1)
        good = counts[:, column] >= minimum_samples
        means[good, column] = total[good] / counts[good, column]
    result = TimeSeries((edges[:-1]+edges[1:])/2, means, series.channels, series.units,
                        counts >= minimum_samples, clock_id, Origin.RECONSTRUCTED,
                        "bin-means:" + series.source_id, series.quantities, series.basis_ids)
    return BinnedSeries(result, counts, edges)
