# PEM current-ripple measurements

## Source and rights

The acquisition is Mendeley Data v2, DOI [10.17632/93jz2rgy4d.2](https://doi.org/10.17632/93jz2rgy4d.2), by Kingston Nguyen, Dezso Sera, Saman A. Gorji, Jonathan Love and Geoff Walker. The publisher record declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); attribution is retained in `research/data/pem-ripple-degradation.toml`. The archive is kept in ignored local raw-data storage and is not copied into the source release.

The pinned attachment is 90,759,411 bytes with SHA-256 `47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab`. The reader verifies that complete receipt before issuing an archive handle and hashes each requested CSV member while streaming it directly from the ZIP. It never extracts the four large continuous logs.

## Contents and source interpretation

The archive provides nine unaveraged polarization files for each of four single cells (baseline and eight later characterizations), four continuous operational logs, and a separate table of fitted parameters. The README maps PEM1/PEM2/PEM3/PEM4 to 300 Hz ripple, DC, 600 Hz ripple and 1,200 Hz ripple, respectively; the three ripple cases are reported at 50% magnitude. The campaign description states a common 2 A mean current over 1,000 h.

The IV reader retains `current_A` in A, `voltage_V` in V and `step_index` as an integer index, without reducing repeated steps. The continuous reader retains current and voltage in the same declared units. Both typed results can stream their exact original CSV row tokens with `iter_source_rows()`. The continuous timestamp strings contain no timezone designator; the numeric API stores the first exact token and strictly increasing millisecond offsets relative to that token. Every inter-sample interval is available so characterization pauses remain visible. No interpolation, gap filling, timezone assignment or synchronization across cells is performed.

The `Fitted_parameters.csv` rows are reported analysis products, not independent measurements. The API labels the documented `R_mem` (ohm), `i_0` (A), `I_lim` (A) and `RMSE` (V) fields as fit output; `alpha` is kept as a reported scalar without assigning an unstated unit. The reader does not refit or use those values as validation observations.

## Python API

After installing the `data` extra, reproduce the bounded acquisition from the
project root with `python scripts/acquire_data.py --keys pem-ripple-degradation`.
The script verifies the publisher checksum, writes the receipt, and stores the
ZIP under ignored `data/raw/`; do not add that raw archive to source control.

```python
from h2physics.data import (
    load_pem_ripple_archive,
    load_pem_ripple_continuous_trace,
    load_pem_ripple_fit_table,
    load_pem_ripple_iv_curve,
)

archive = load_pem_ripple_archive()
curve = load_pem_ripple_iv_curve(archive, cell_id="PEM1", cycle="Initial")
trace = load_pem_ripple_continuous_trace(archive, cell_id="PEM1")
fits = load_pem_ripple_fit_table(archive)

curve.current_a, curve.voltage_v, curve.step_index
trace.elapsed_s, trace.interval_s, trace.current_a, trace.voltage_v
fits.records[0]
```

Each result exposes the source member SHA-256 and a `require_current()` method that rejects a changed archive or altered projected arrays. Load one cell's continuous trace at a time; each log is large. The scientific validation plan contains a deferred synthetic parser/integrity contract; it has not established physical-model accuracy.

## Limits before model comparison

The deposited channels do not establish active electrode area, cell temperature or pressure, water-feed state, sensor calibration, voltage/current uncertainty, timezone or cross-cell clock synchronization. Consequently A cannot be converted to current density from this dataset alone, and the records cannot independently qualify a stack polarization, degradation, thermal or hydrogen-production model. Any later comparison must supply and document the missing geometry and state mapping, separate measured from fitted data, preserve campaign-level independence and avoid filling suspended logging periods.
