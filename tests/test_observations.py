import io

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.loaders import Column, load_observation_table
from h2physics.observations import ObservationTable, Variable, split_experiments


def test_non_time_loader_retains_decreasing_abscissa_and_reference_volume_basis():
    loaded = load_observation_table(io.StringIO("relative,uptake\n.8,20\n.1,10\n.1,\n"),
        columns=(Column("relative", "p_ratio", "normalized_pressure", "1", basis_id="source-normalizer-unknown"),
                 Column("uptake", "q_volume", "reference_specific_volume", "cm3/g", basis_id="STP-source-unspecified")),
        experiment_id="authored-isotherm", source_id="synthetic", origins=(Origin.SYNTHETIC,)*2)
    np.testing.assert_allclose(loaded.values[:2], [[.8, .02], [.1, .01]])
    assert not loaded.valid[2, 1] and len(loaded.row_ids) == 3
    assert not loaded.values.flags.writeable
    with pytest.raises(ValueError, match="basis differs"):
        loaded.column("q_volume", expected=Variable("q", "reference_specific_volume", "m3/kg", "specified-STP"))
    with pytest.raises(ValueError, match="basis"):
        Variable("q", "specific_amount", "mol/kg")


def test_experiment_partition_never_splits_a_group_or_duplicates_source_rows():
    table = ObservationTable(np.arange(12).reshape(6, 2),
                              (Variable("j", "current_density", "A/m2"), Variable("v", "voltage", "V")),
                              np.ones((6, 2), bool), tuple(f"row-{i}" for i in range(6)),
                              ("A", "B", "A", "B", "C", "C"), (Origin.MEASURED,)*2, "authored")
    partition = split_experiments(table, {"B"})
    assert partition.held_out.row_ids == ("row-1", "row-3")
    assert set(partition.fitting.experiment_ids).isdisjoint(partition.held_out.experiment_ids)
    with pytest.raises(ValueError, match="proper subset"):
        split_experiments(table, {"unknown"})
    with pytest.raises(ValueError, match="unique"):
        table.select_rows([0, 0])


def test_reported_pressure_cannot_pass_as_absolute_and_time_loader_retains_reference_basis():
    from h2physics.data.loaders import load_delimited

    loaded = load_observation_table(io.StringIO("p\n2\n"),
        columns=(Column("p", "p", "reported_pressure", "bar", basis_id="unresolved"),),
        experiment_id="A", source_id="authored", origins=(Origin.SYNTHETIC,))
    assert loaded.values[0, 0] == 200000
    with pytest.raises(ValueError, match="basis differs"):
        loaded.column("p", expected=Variable("p", "pressure", "Pa", "absolute"))
    series = load_delimited(io.StringIO("t,q\n0,10\n1,20\n"),
        columns=(Column("q", "q", "reference_specific_volume", "cm3/g", basis_id="source-STP-unknown"),),
        time_column="t", time_unit="s", clock_id="authored", origin=Origin.SYNTHETIC, source_id="test").series
    with pytest.raises(ValueError, match="Declare"):
        series.channel_values("q", quantity="reference_specific_volume")
    values, valid = series.channel_values("q", quantity="reference_specific_volume", basis_id="source-STP-unknown")
    assert values[0] == .01 and np.all(valid)
