# AGH hydrogen/cushion-gas core-flood data acquisition gap

## Source and rights

The AGH University of Krakow RODBUK record identifies version 1.0 of the
underground-storage hydrogen/cushion-gas mixing dataset by Karol Dąbrowski and
Łukasz Klimkowski. The record and selected-file page both declare CC BY 4.0.
The publisher describes laboratory core-flood concentration measurements made
with X-ray scanning and Raman spectroscopy. Attribution must use the citation
on the record. The license declaration is recorded as source metadata; it does
not mean the raw payload should be copied into this repository.

Selected candidate: `RawDataXrayRaman.zip`, Dataverse file ID 2480. The official
file page lists an MD5 of
`e5173b39afbaf264f3dbb0b298aa83e5` and a rounded size of 375.7 MB. The publisher
does not expose an exact byte count in the page text.

## Acquisition result

The public API URL
`https://agh.rodbuk.pl/api/access/datafile/2480?gbrecs=true` was attempted from
the local command shell on 2026-10-31. `curl` returned exit code 28 after an
approximately 21.6 second connection timeout to `agh.rodbuk.pl:443`. No
credentials or authenticated route were used. The browser/search index exposes
publisher metadata but not the binary contents. No file was saved and neither
the publisher MD5 nor local SHA-256 has been verified.

The candidate is registered with 0 acquired bytes in
`research/data/agh-uhs-h2-cushion-gas-core-flood.toml`. Its payload stays
unacquired until the official download is reachable. If acquired later, write
it under ignored `data/raw/agh-uhs-h2-cushion-gas-core-flood/`, verify the exact
publisher MD5, compute SHA-256, and list ZIP members without extracting unsafe
paths. Inspect the README and schemas before deciding whether a reader or a
deferred ingestion case is justified.

## Modeling fit and limits

The described measurements may support a core-scale breakthrough/mixing
comparison for hydrogen and cushion gases. They are not automatically evidence
for full cavern cycling, field-scale dispersion, wellbore flow, or pipeline
release. Instrument response, species calibration, spatial coordinate,
pressure/temperature, gas mixtures, core properties, flow rates and boundary
conditions must be recovered from the payload and its documentation before a
physical observation operator can be defined. No model fit or validation claim
is made from the metadata description alone.

Official sources: [AGH RODBUK dataset record](https://agh.rodbuk.pl/dataset.xhtml?persistentId=doi%3A10.58032%2FAGH%2FI5QS9P) and [selected file metadata](https://agh.rodbuk.pl/file.xhtml?fileId=2480&version=1.0).
