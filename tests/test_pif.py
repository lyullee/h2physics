import io

import numpy as np
import pytest

from h2physics.data.pif import acoustic_columns, read_property_file


def test_original_property_fixture_preserves_units_unknowns_and_immutability():
    data = read_property_file(io.StringIO("""data_authored_fixture
_units_temperature K
_units_pressure MPa
_units_SoS m/s
_lit_authors 'Synthetic fixture'
loop_
_example_temperature
_example_pressure
_example_SoS
_example_uncertainty_SoS
300 0.2 1300 2
310 ? 1320 ?
"""))
    temperature, pressure, speed = acoustic_columns(data, data.loops[0])
    assert pressure[0] == 200000
    assert np.isnan(pressure[1])
    assert temperature[1] == 310 and speed[0] == 1300
    assert not data.loops[0].values.flags.writeable
    with pytest.raises(TypeError):
        data.metadata["_units_pressure"] = "bar"


@pytest.mark.parametrize("body", ["loop_\n_a\n_b\n1", "_x 1\n_x 2", ";multiline"])
def test_irregular_or_unsupported_property_input_is_rejected(body):
    with pytest.raises(ValueError):
        read_property_file(io.StringIO("data_authored\n" + body))
