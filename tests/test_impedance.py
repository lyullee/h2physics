import csv
import hashlib
import io

import numpy as np
import pytest

from h2physics.adapters.impedance import NativeCircuitOperator
from h2physics.core import Origin
from h2physics.data.pem import HEADERS, load_pem_csv, pem_spectra
from h2physics.impedance import ImpedanceSpectrum


def source_row(time, *, frequency=0., current_ma=1000., magnitude=0., phase=-30.,
               label="POL_GEIS", counter=1):
    return [time, 80., current_ma, 2., frequency, magnitude, phase, 10., 30.,
            2., 1., label, counter]


def load(rows, **selection):
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(HEADERS)
    writer.writerows(rows)
    content = text.getvalue().encode("utf-8")
    stream = io.BytesIO(content)
    experiment = load_pem_csv(stream, experiment_id="authored/cell-A", source_id="authored",
        measurement_types=selection.pop("measurement_types", ("POL_GEIS",)),
        counters=selection.pop("counters", None), active_area_m2=4e-4,
        phase_sign=selection.pop("phase_sign", 1), **selection)
    assert not stream.closed
    assert experiment.report.member_sha256 == hashlib.sha256(content).hexdigest()
    return experiment


def test_source_hash_covers_unselected_rows_and_units_masks_are_explicit():
    rows = [source_row(0), source_row(1, frequency=100., magnitude=.1),
            source_row(2, label="H2_char"), source_row(3, label="unselected")]
    rows[1][2:4] = ["bad", -0.02]
    rows[2][9] = ""
    experiment = load(rows, measurement_types=("POL_GEIS", "H2_char"))
    table = experiment.observations
    assert experiment.report.rows_seen == 4 and experiment.report.rows_retained == 3
    assert experiment.report.malformed_numeric_cells == 1
    assert experiment.report.nonpositive_frequency_rows == 2
    np.testing.assert_allclose(table.values[0, [1, 2, 7, 8, 9, 10]],
                               [353.15, 1., .001, 3e6, .02, .01])
    assert not table.valid[0, 4:7].any()  # Source DC placeholders are retained and masked.
    assert table.values[0, 4] == table.values[0, 5] == 0.
    assert not table.valid[1, 2] and table.values[1, 3] == -.02
    assert not table.valid[0, 10] and table.valid[2, 10]
    assert not table.valid[2, 9] and np.isnan(table.values[2, 9])
    assert table.row_ids == tuple(f"authored/cell-A/row-{i}" for i in (2, 3, 4))
    assert table.experiment_ids[2] == "authored/cell-A/H2_char/1"
    empty = load(rows, counters=(99,))
    assert empty.observations.values.shape == (0, 12)


def test_spectra_use_separate_dc_tails_not_ac_current_or_previous_holds():
    rows = [source_row(0, current_ma=1000), source_row(1, current_ma=1200),
        source_row(2, frequency=100, magnitude=.2, current_ma=800),
        source_row(3, frequency=1000, magnitude=.1, current_ma=1300),
        source_row(4, current_ma=2000),
        source_row(5, frequency=100, magnitude=.3),
        source_row(6, frequency=1000, magnitude=.2),
        source_row(7, frequency=100, magnitude=.4),  # An adjacent sweep has no DC hold.
        source_row(8, frequency=1000, magnitude=.3),
        source_row(9, frequency=100, magnitude=.2, counter=2)]
    spectra = pem_spectra(load(rows))
    assert len(spectra) == 4
    assert spectra[0].dc_current_a == pytest.approx(1.1)
    assert spectra[0].dc_gap_s == 1.
    assert spectra[1].dc_current_a == 2.
    assert len(spectra[1].dc_context_row_ids) == 1
    assert spectra[2].dc_current_a is None and spectra[3].dc_current_a is None
    assert spectra[0].spectrum.experiment_id.endswith("/1/sweep-1")
    assert spectra[2].spectrum.experiment_id.endswith("/1/sweep-3")
    assert spectra[3].spectrum.experiment_id.endswith("/2/sweep-1")
    assert spectra[0].spectrum.impedance_ohm[0] == pytest.approx(.2*np.exp(-1j*np.pi/6))


def test_declared_phase_direction_and_dc_gap_are_not_inferred():
    rows = [source_row(0), source_row(30, frequency=1000, magnitude=.2),
            source_row(31, frequency=100, magnitude=.3)]
    experiment = load(rows, phase_sign=-1)
    separated = pem_spectra(experiment)
    assert len(separated) == 2 and separated[0].dc_current_a is None
    assert separated[0].dc_gap_s == 30.
    descending = pem_spectra(experiment, ascending_frequency=False, maximum_dc_gap_s=40.)
    assert len(descending) == 1 and descending[0].dc_current_a == 1.
    assert descending[0].spectrum.impedance_ohm[0].imag > 0.
    with pytest.raises(ValueError, match="reset"):
        pem_spectra(experiment, frequency_reset_ratio=1.)
    with pytest.raises(ValueError, match="phase_sign"):
        load(rows, phase_sign=True)


def test_bad_headers_and_ragged_rows_fail_without_closing_caller_stream():
    for raw in (b"x,y\n1,2\n", (",".join(HEADERS)+"\n1,2\n").encode()):
        stream = io.BytesIO(raw)
        with pytest.raises(ValueError, match="header|Ragged"):
            load_pem_csv(stream, experiment_id="A", source_id="test", measurement_types=("POL_GEIS",),
                         counters=None, active_area_m2=1., phase_sign=1)
        assert not stream.closed


def test_cartesian_projection_preserves_masks_bases_and_point_identity():
    spectrum = ImpedanceSpectrum([10., np.nan], [2.-3j, complex(np.nan, np.nan)],
        [True, False], ("row-A", "row-B"), "cell/sweep", "authored", Origin.SYNTHETIC)
    table = spectrum.cartesian_observations()
    np.testing.assert_allclose(table.values[[0, 2]], [[10., 0., 2.], [10., 1., -3.]])
    assert table.row_ids == ("row-A/real", "row-B/real", "row-A/imag", "row-B/imag")
    assert table.valid[:, 2].tolist() == [True, False, True, False]
    assert table.variables[2].basis_id == "whole-cell;exp(+j*omega*t)"
    assert table.origins[0] == Origin.SYNTHETIC
    assert not spectrum.impedance_ohm.flags.writeable
    with pytest.raises(ValueError, match="unique"):
        ImpedanceSpectrum([1., 2.], [1j, 2j], [True, True], ("same", "same"),
                          "cell", "authored", Origin.SYNTHETIC)


class AuthoredNative:
    def __init__(self, *, circuit, initial_guess):
        assert circuit == "authored-test-only"
        self.parameters = initial_guess

    def get_param_names(self):
        return ["offset", "slope"], ["ohm", "ohm/Hz"]

    def predict(self, frequency, *, use_initial):
        assert use_initial
        return self.parameters[0]+1j*self.parameters[1]*frequency


def test_native_factory_order_and_cartesian_selector_contract():
    op = NativeCircuitOperator(AuthoredNative, circuit="authored-test-only",
                               parameter_names=("offset", "slope"))
    spectrum = ImpedanceSpectrum([10., 20.], [0j, 0j], [True, True],
        ("a", "b"), "authored", "authored", Origin.SYNTHETIC)
    parameters = {"offset": 2., "slope": -.5}
    evaluation = op.evaluate([10., 20.], parameters)
    assert isinstance(evaluation.native, AuthoredNative)
    assert not evaluation.impedance_ohm.flags.writeable
    np.testing.assert_allclose(op(spectrum.cartesian_observations(), parameters), [2., 2., -5., -10.])
    reversed_order = NativeCircuitOperator(AuthoredNative, circuit="authored-test-only",
                                          parameter_names=("slope", "offset"))
    with pytest.raises(ValueError, match="parameter order"):
        reversed_order.evaluate([1.], parameters)
    with pytest.raises(ValueError, match="positive finite"):
        op.evaluate([0.], parameters)
    wrong_units = NativeCircuitOperator(AuthoredNative, circuit="authored-test-only",
        parameter_names=("offset", "slope"), parameter_units=("ohm", "ohm/s"))
    with pytest.raises(ValueError, match="units differ"):
        wrong_units.evaluate([1.], parameters)
