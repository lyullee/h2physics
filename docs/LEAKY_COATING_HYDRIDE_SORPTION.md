# Pd leaky-coating hydrogen sorption traces

## Source and license

This reader covers four selected measured Figure 4 text files from the [Zenodo v1 dataset](https://doi.org/10.5281/zenodo.6670268), which explicitly declares CC BY 4.0. Attribution: Kazaz, Selim; Billeter, Emanuel; Borgschulte, Andreas (2022), *Dataset to Sorption kinetics in metal hydrides by leaky coating*, Zenodo, https://doi.org/10.5281/zenodo.6670268. The linked article is *Sorption kinetics in metal hydrides by leaky coating* (International Journal of Hydrogen Energy, DOI 10.1016/j.ijhydene.2022.07.248).

The selected data are Figure 4 feed-pressure-delta and UHV mass-spectrometer channels for Pd membrane absorption at 105 °C (4a) and absorption/desorption at 85 °C (4c). Source metadata describes a 45 μm Pd membrane with a 10 nm Cu coating that permits a small hydrogen flux to an ultra-high-vacuum mass spectrometer while limiting the bulk uptake measurement loss.

## Schema and observation meaning

All source time axes are seconds and pressure-value axes are mbar. `Fig4a_deltap_f.txt` has a shared time column with channels `p1`–`p15`; `Fig4a_pUHV.txt` contains a distinct time column for each UHV channel. Figure 4c feed and UHV files each use a shared time column with channels `p1`–`p8`, but their sampling lengths differ, so the reader does not align feed and UHV rows by index. Values are retained as source tokens with a numeric convenience view. Negative feed-channel entries are preserved because this is a reported pressure-change signal, not absolute pressure.

The source contains missing-value markers (`--`) in both clock and value fields.
The reader keeps every original time/value pair, source row number and token in
`trace.source_pairs`. Its numeric `time_s`/`value_tokens` view includes only
complete finite pairs, so missing records remain inspectable rather than being
parsed as numbers or silently discarded. Across the four pinned files the
reader records 59,328 source pairs, including 1,785 missing-time tokens, 137
missing-value tokens and 1,922 incomplete pairs. The Hangang ingestion contract
asserts those counts. The initial 5aq campaign run exposed the parser's prior
attempt to convert `--` to a float; this was a source-schema ingestion failure,
not a model result.

## Model boundary

These data observe palladium membrane sorption and UHV-side hydrogen signal, not a tank or plant storage process. The source explains that UHV signal is proportional to near-surface solid hydrogen concentration, but the scale factor between it and feed pressure is arbitrary. The selected feed channel is a pressure change, not a documented absolute inlet pressure. The dataset also lacks complete per-channel run identity and initial/terminal solid state mapping. It is therefore not used to fit `DiffusionSlab`, `HydrideKinetics` or a vessel model. The source reader supplies reusable measured traces only.

## Python API

```python
from h2physics.data import read_leaky_coating_sorption_data

observations = read_leaky_coating_sorption_data(
    "data/raw/leaky-coating-hydride-sorption/1"
)
for trace in observations.traces:
    print(trace.figure, trace.signal, trace.channel, trace.time_s, trace.values_mbar)
observations.require_current()
```

Files are pinned by exact size, publisher MD5, and SHA-256 in `research/data/leaky-coating-hydride-sorption.toml`. Original data files are under the gitignored `data/raw/` tree. No source figure text or article prose is copied into code.
