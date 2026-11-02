# Residential hydrogen pilot data: rights and physical boundary gap

The Zenodo v1 record [10.5281/zenodo.15166733](https://zenodo.org/records/15166733) describes PLC measurements from a residential PV, battery, electrolyzer, buffer, compressor, high-pressure tank and fuel-cell pilot in Spain. It reports five-second samples from 2024-03-27 through 2024-04-15 and describes subsystem power in W, pressure in bar, H2 flows in NL/h, cumulative H2 in NL, SOC and ambient temperature. The listed payload is `HY2RES_202404.csv`, shown as 38.6 MB with publisher MD5 `9a3c3e3b1668596854b43bfd790d3e0e`.

The official record's Rights/License field is empty. The payload has not been downloaded or ingested; no reuse license is inferred from the record being openly accessible. The metadata-only Hangang case `residential-h2-pilot-license-and-physical-boundary-gap` records this restriction.

Even after rights are clarified, row-level use needs the CSV bytes and hash, timestamp timezone, meaning of OPEN/CLOSE break markers, normal-liter reference temperature and pressure, pressure gauge/absolute basis, sensor calibration, equipment volumes, and the mapping of interval flows and cumulative totals to model boundaries. The existing process-monitoring, fuel-cell and storage-delivery APIs are possible consumers after those items are documented. No calibration, fitting, conversion or model comparison is performed by this case.

Attribution metadata: Rodriguez De Lope, L.; Agüero, R.; Diez, L.; Ortiz, I.; Ortiz Sainz de Aja, A.; Maestre Muñoz, V. M. (2025), Zenodo record 10.5281/zenodo.15166733. Because the record does not specify a license, attribution details here do not grant reuse rights.
