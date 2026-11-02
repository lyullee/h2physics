# Hydrogen engine figure data: model-linkage gap

## Acquired source boundary

TUdatalib record [10.48328/tudatalib-2291](https://doi.org/10.48328/tudatalib-2291)
is open access and lists CC BY 4.0, eight acquired bitstreams totaling 8,828,090 bytes.
The acquisition and file hashes are recorded in
[`research/data/hydrogen-engine-flame-wall.toml`](../research/data/hydrogen-engine-flame-wall.toml).
The existing `inspect_hdf5_metadata()` was used to inspect HDF5 object paths, shapes,
dtypes and attributes only. No array values are loaded by that API or copied into this
repository. This is a small collection relative to large process archives, but the
record-level grant does not close the outstanding component-level third-party rights
review; raw bitstreams remain excluded from source distributions.

## Why a physical adapter is blocked

The [schema audit](HYDROGEN_ENGINE_DATA_SCHEMA.md) identifies fragments that look
relevant to existing open-cylinder, engine-boundary and wall-thermal APIs. The stored
fields do not establish enough exact meanings for a source-bound physical comparison:

- `Fig2.h5`: pressure is labelled in bar and an axis in degrees crank angle, but the
  crank-angle zero/reference and pressure-transducer location are absent; mean/std
  population and relation to individual cycles are not established.
- `Fig3.h5`: temperature and lifetime carry units, but the lifetime phenomenon,
  measurement location and condition pairing are not defined in the file schema.
- `Fig5.h5`: coordinates and crank-angle labels exist, but the flame-map scalar,
  spatial transform and the meaning of the three index planes are missing.
- `Fig6.h5`/`Fig7.h5`: temperature differences and after-impingement angles need a
  defined temperature reference, sensor location, coordinate reference and pairing.
- `Fig8.h5`/`Fig9.h5`: heat-flux-like values in W/m² do not state their sensing plane,
  location or sample correspondence to flame power and crank-angle/space coordinates.

The item description's broad engine and diagnostic context does not resolve these
field-level semantics. Assigning any field to pressure-volume work, a wall heat flux,
or a boundary temperature would add assumptions absent from the source record. The
new metadata-only case `hydrogen-engine-figure-data-model-link-gap` checks that this
boundary remains documented; it is not an engine calculation or validation result.

## Prepared request

[`requests/hydrogen_engine_figure_data_mapping.md`](../requests/hydrogen_engine_figure_data_mapping.md)
is a specific, not-sent request to the authors and repository maintainers for a
versioned sidecar keyed by filename and HDF5 object path. It requests units, physical
quantity, coordinate reference, sensor/location, cycle and condition identity,
aggregation/uncertainty definition, and per-file rights notes. An exact metadata API
and bitstream inventory are in the acquisition manifest; a future sidecar needs its
own version and digest.

Once those definitions arrive, only an exact field with compatible location and
coordinate semantics should be linked to existing physical APIs. Do not infer a
combustion boundary or pressure-volume trace from figure titles or published plots.
