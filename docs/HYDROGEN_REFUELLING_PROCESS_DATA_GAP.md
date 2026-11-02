# Hydrogen refuelling process-trace source gap

## Audit result

The reviewed official repository and API records did not yield a directly reusable, machine-readable set of per-fill, time-aligned station/dispenser/receptacle/tank pressure and temperature plus mass-flow or dispensed-mass histories with public downloadable files, explicit reuse terms, a version or snapshot date, exact file inventory/checksums, channel units and a sampling timebase. No raw refuelling trace was acquired. The source-by-source blocker record is in `research/data/hydrogen-refuelling-process-traces-gap.toml`.

This is an access-and-rights gap, not a claim that no such measurements exist. Multiple facilities and published studies describe measured fueling records. The missing piece is an inspectable, licensed raw-data artifact suitable for repository reuse.

## Strongest raw-trace lead: Powertech / H2Protocol

Published hydrogen-refuelling models identify the H2Protocol site and a Powertech Labs dataset named “SAE J2601 Tables Method - Laboratory Data” as an empirical source. The lead is relevant because it is described as laboratory fueling data and appears to contain tank pressure, temperature and state-of-charge information. During this audit the official data page did not load: the web page request timed out and the workstation HTTPS request returned a TLS internal error. No API schema or downloadable file inventory could be inspected, and no explicit raw-data license or redistribution permission was located. Do not copy or redistribute any files until the custodian provides an accessible versioned package, explicit reuse terms, per-file bytes/checksums and a schema.

## Other access and rights blockers

The Cal State LA Hydrogen Research and Fueling Facility papers describe in-situ/back-to-back operation and multi-year station performance, but the associated university repository pages report no downloadable files. The station logs have no separate reuse license. Open-access rights for a paper do not automatically license its absent underlying data. The existing record at `research/data/cal-state-la-hrs-operational.toml` tracks those two source records.

NREL's H2FillS page describes a registered software download and an end-user license. H2FillS is a useful thermodynamic filling model, but the public page does not provide a separate raw empirical trace package or a license for those source data. Its simulation output is not empirical fueling validation data.

NREL's Hydrogen Secure Data Center has protected raw station and vehicle records supplied by industry partners. Public composite data products provide aggregate or anonymized indicators, not raw event files. DOE/NREL heavy-duty high-flow demonstrations are documented in webinar material with summary statistics and plotted time histories; those figures are not machine-readable raw-data releases and are deliberately not converted into data here.

NIST describes its Transient Flow Facility as reproducing pressure, temperature and flow transients for hydrogen dispenser metrology, but the reviewed project page is a facility description, not a public dataset record. No raw hydrogen refuelling run files, checksums or data license were found there.

CARB's 2024 In-Use Study is a particularly relevant measured-source lead: the report describes a HyStEP instrumented test device and includes selected station/tank pressure, temperature and mass-flow histories and test summaries. CARB's official program page exposes the report PDF, but no machine-readable per-fill logs, versioned raw-file inventory or checksums were located. The study describes anonymized participants, and no separate reuse grant for underlying sensor records was found. The figures are not digitized, ingested or used as validation data.

The NREL/NLR station composite product index covers fill counts, amounts, duration/rates, final pressure and some fuel-temperature summaries, but these are grouped products and not individual time series. The Hydrogen Secure Data Center is described as protected partner data, and the H2FillS software download requires registration and an end-user license; neither provides an openly reusable empirical trace package in the reviewed public record. H2FillS-generated simulation output is synthetic/model output, not independent fill measurement.

## Useful alternatives that do not validate fueling physics

- The H2-Stations registry and status API is explicitly CC BY 4.0. API v2 includes station layout plus availability, usage, hydrogen-storage and pricing sections and requires a personal bearer token. The API documents point-in-time operations and does not document a per-fill pressure/temperature/mass-flow endpoint or historical trace archive. The bounded public station-list workbook snapshot already acquired for this project is documented in `research/data/h2-stations-hrs-inventory.toml`.
- NREL hydrogen-station and FCEV composite data products provide context on station deployment, fill duration, vehicle tank levels, pressure and temperature summaries, reliability, and energy use. They are composite/aggregate products, not row-level event traces.
- DOE AFDC station downloads provide station inventory and historical station-list information. They do not contain dispenser process histories; inspect the terms for the selected export before reuse.
- DOE webinar material reports a small number of heavy-duty fueling performance summaries. These are pointers for a future data request only; figures are not digitized or used as measurements here.

### Open sampling-system measurements: adjacent, not a vehicle fill trace

The Zenodo v1.0 record [Group B -- HySam system measurement data](https://doi.org/10.5281/zenodo.20590842)
is the closest openly published high-pressure hydrogen process-measurement
collection found in this refresh. The project already acquired its three
workbooks under the record's CC BY 4.0 declaration and recorded the source
receipt in `research/data/hysam-sampling-system.toml`; their exact byte counts,
publisher MD5 values, local SHA-256 digests, and sheet dimensions are listed in
`docs/HYSAM_SAMPLING_DATA.md`. Its existing reader is
`h2physics.data.hysam_sampling.load_hysam_workbook()`.

The record describes fuel-sampling-system measurements, not station dispenser
fills into vehicle tanks. The workbooks expose a time-labelled column and
instrument-tag/value columns, but the available record does not fully define
units, pressure reference, measurement plane, calibration, sensor placement,
or shared run-clock semantics. It is therefore useful for future sampling and
metrology interfaces only. It does not close the per-fill raw-data gap and is
not admitted as refuelling-process validation data. The source-bound workbook
reader and deferred case check file identity/schema rather than physical model
accuracy.

## Reopening the source gap

Revisit this audit only when a provider offers an explicit raw-data grant and a bounded machine-readable package. Before ingesting, pin the source record/version and retrieval timestamp, preserve the exact license and attribution requirements, record file names, bytes and publisher checksums, compute local SHA-256 receipts, inspect schemas and units, and qualify whether channels are station-side, dispenser-side, receptacle-side or vehicle-tank measurements. Keep source-ingestion checks separate from model evaluation. No Hangang case is assigned while the source data and rights remain unavailable.

## Primary source records reviewed

- [NREL H2FillS program page](https://www.nrel.gov/hydrogen/H2FillS) and [user manual](https://www.nrel.gov/docs/libraries/hydrogen/h2fills-user-manual.pdf).
- [DOE / NREL high-flow fueling webinar transcript](https://www.energy.gov/cmei/fuels/march-h2iq-hour-hydrogen-fuel-dispensing-medium-and-heavy-duty-vehicles-text-version).
- [NREL retail-station composite products](https://nrel.sitefinity.cloud/hydrogen/infrastructure-cdps-retail) and [FCEV composite products](https://nrel.sitefinity.cloud/hydrogen/fuel-cell-electric-vehicle-cdps).
- [NIST Transient Flow Facility](https://www.nist.gov/programs-projects/transient-flow-facility).
- [DOE OSTI report describing the Hydrogen Secure Data Center](https://www.osti.gov/servlets/purl/1076655).
- [Cal State LA in-situ/back-to-back paper](https://doi.org/10.1016/j.jclepro.2021.129737) and [multi-year station-performance paper](https://doi.org/10.1016/j.ijhydene.2023.04.084).
- [Powertech/H2Protocol data lead cited by a peer-reviewed fueling-model paper](https://doi.org/10.1016/j.renene.2024.120410); the raw-data access and reuse rights could not be verified at the linked source site.
- [CARB's Existing Light-Duty Hydrogen Refueling Stations In-Use Study](https://ww2.arb.ca.gov/our-work/programs/hydrogen-fueling-infrastructure); measured report figures and methods are available, but raw traces and their reuse rights are not.
- [NREL/NLR next-generation station composite products](https://nrel.sitefinity.cloud/hydrogen/infrastructure-cdps-all); aggregate performance summaries only, no raw fill log files.
- [Zenodo HySaM system measurement record](https://doi.org/10.5281/zenodo.20590842); open CC BY 4.0 sampling-system workbooks already acquired by this project, but not dispenser-to-vehicle fill histories.
- [Clean Hydrogen JU H2-Stations API v2](https://docs.h2-stations.eu/for-data-users/api-v2/); licensed station/operational signals, not per-fill instrument traces.
- [Public HyStEP technical records](https://h2tools.org/hystep-hydrogen-station-equipment-performance-device); instrument and design evidence, without a trace-data package.
