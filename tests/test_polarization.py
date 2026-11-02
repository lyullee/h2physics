import io

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.polarization import load_polarization_grid
from h2physics.observations import concatenate_observations


def test_two_header_grid_keeps_curve_groups_and_missing_observations():
    tables = load_polarization_grid(io.StringIO("T/degC\t20\t30\n"
        "j/mA/cm2\tE/V\tE/V\n0\t1\t.9\n10\t.8\t\n"),
        source_id="authored", group_prefix="fixture", temperature_unit="degC",
        current_density_unit="mA/cm2", voltage_unit="V")
    assert tables[0].values[1, 0] == 100
    assert tables[0].values[0, 1] == pytest.approx(293.15)
    assert not tables[1].valid[1, 2]
    assert tables[0].origins[2] == Origin.UNRESOLVED
    combined = concatenate_observations(tables, source_id="combined")
    assert len(set(combined.experiment_ids)) == 2 and len(combined.values) == 4
    assert len(combined.content_sha256) == 64
    changed = combined.select_rows(np.arange(4)[::-1])
    assert combined.content_sha256 != changed.content_sha256
