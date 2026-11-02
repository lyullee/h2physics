import io

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.loaders import Column, load_delimited
from h2physics.units import convert_to_si


def test_unknown_pressure_basis_and_standard_flow_cannot_be_guessed():
    with pytest.raises(ValueError, match="basis"):
        convert_to_si([1], quantity="pressure", unit="bar")
    with pytest.raises(ValueError, match="Unsupported"):
        convert_to_si([1], quantity="mass_flow", unit="SLPM")
    assert convert_to_si([1], quantity="pressure", unit="bar", pressure_basis="gauge",
                         ambient_pressure_pa=101325)[0] == 201325


def test_loader_retains_missing_values_and_requires_padding_policy():
    text = "t,flow\n0,1\n1,#N/A\n,2\n"
    kwargs = dict(columns=(Column("flow", "mass_flow", "mass_flow", "g/s"),),
                  time_column="t", time_unit="s", clock_id="declared-flow-clock",
                  origin=Origin.MEASURED, source_id="original-fixture")
    with pytest.raises(ValueError, match="omission"):
        load_delimited(io.StringIO(text), **kwargs)
    loaded = load_delimited(io.StringIO(text), omit_missing_time=True, **kwargs)
    assert loaded.series.values[0, 0] == .001
    assert np.isnan(loaded.series.values[1, 0])
    assert not loaded.series.valid[1, 0]
    assert loaded.report.omitted_missing_time_rows == 1
    assert not loaded.report.interpolation_performed


def test_different_clock_rows_are_not_silently_sorted_or_combined():
    with pytest.raises(ValueError, match="increasing"):
        load_delimited(io.StringIO("t,c\n1,2\n0,3\n"),
                       columns=(Column("c", "c", "volume_fraction", "%"),),
                       time_column="t", time_unit="s", clock_id="one-clock",
                       origin=Origin.MEASURED, source_id="fixture")


def test_differential_pressure_does_not_become_absolute_pressure_after_si_conversion():
    result = load_delimited(io.StringIO("t,dp\n0,2\n1,3\n"),
                            columns=(Column("dp", "DP", "pressure_difference", "kPa", "differential"),),
                            time_column="t", time_unit="s", clock_id="one-clock",
                            origin=Origin.MEASURED, source_id="fixture")
    assert result.series.units == ("Pa",)
    with pytest.raises(ValueError, match="physical quantity"):
        result.series.channel_values("DP", quantity="pressure")
