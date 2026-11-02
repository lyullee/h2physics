# PEACE alkaline cell-testing dataset: source review

This is a distinct TU/e dataset from the already-ingested BTU pressurized
short-stack dataset. The PEACE project lists “Cell Component Development and
Qualification: Electrochemical Testing” under Eindhoven University of Technology
and links DOI `10.4121/834a5e8f-8c05-42d1-98b9-afc4af42d5ca.v1`. The project summary
describes electrochemical tests of electrode and membrane combinations in
laboratory alkaline flow cells. See the [official PEACE dataset list](https://www.h2peace.eu/public-media/datasets)
and the [4TU.ResearchData record](https://data.4tu.nl/datasets/834a5e8f-8c05-42d1-98b9-afc4af42d5ca/1).

## Record metadata found

The DOI registration record identifies version 1, the title, creators Matheus de
Groot and Saksham Pandey, publisher 4TU.ResearchData, issue date 2026-01-20, and
license CC BY 4.0. The explicit license is recorded in the [DataCite registration](https://api.datacite.org/dois/10.4121%2F834a5e8f-8c05-42d1-98b9-afc4af42d5ca.v1).
The DOI registration lists generic formats `.xlsx`, `.idf`, and `.zip`, but no
file names, byte sizes, checksums, or content URL.

## Repository access and acquisition status

The official project DOI link resolves to the 4TU record URL above, but the 4TU
landing page and its public API could not be reached from this environment: the
browser retrieval rejected the redirect target and direct repository HTTP requests
timed out. As a result, the repository record itself could not be inspected for its
file inventory, per-file license scope, publisher checksums, README/codebook, or
column schema. The available DOI registration supports record-level CC BY 4.0
reuse, but it is not a substitute for the missing 4TU file metadata.

No dataset files were downloaded. No parser or ingestion case was added because
there are no verified file names, checksums, or schema against which to define a
source-bound reader. Revisit when the public 4TU record/API is reachable; pin every
listed source file and publisher checksum before interpreting any measured field.
The machine-readable status is in
[`research/data/peace-alkaline-cell-testing.toml`](../research/data/peace-alkaline-cell-testing.toml).
