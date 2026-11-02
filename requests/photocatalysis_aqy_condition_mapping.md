# Brookite photocatalysis AQY condition-mapping request

Prepared request for authors/repository maintainers of the CC BY 4.0 Zenodo dataset
[10.5281/zenodo.15277951](https://doi.org/10.5281/zenodo.15277951). This request has
not been sent. The archived observation exports are acquired and schema-read; this
asks for the evidence required to connect them to the existing photon-accounted H2
production API without manufacturing conditions.

For each `Figure4b.txt` reported AQY point, please provide a machine-readable matching
record with:

1. Exact sample/catalyst label and specimen identity, catalyst mass and its dry/wet
   normalization basis.
2. AQY numerator and denominator equations with definitions: incident or absorbed
   photons, electron equivalents or H2 molecules, electron stoichiometry, and any
   correction for reflected/transmitted light.
3. The spectral irradiance or incident photon-flux distribution used for that exact
   observation, including wavelength grid, units, time basis and calibration trace.
4. Reactor/catalyst geometry, illuminated area, optical path, medium and co-reactant
   composition. Identify methanol-assisted measurements separately from overall-water
   splitting.
5. Temperature, pressure, illumination interval, gas collection method, H2 quantity,
   calibration/blank corrections and uncertainty for each observation.
6. Repeat identity, replicate count and whether the source row is measured, averaged,
   or derived from a fit. Preserve exact row/member IDs and file hashes.
7. Per-file licensing confirmation for any additional export and its publisher checksum.

The current dataset's `Figure4b.txt` declares wavelength in nm and AQY in percent, but
the comparison to the existing `PhotonYield` API still requires the exact electron/photon
basis and matching `PhotonSupply` fingerprint. The source reader intentionally leaves
those optical and condition links unresolved. Do not send new data as a replacement for
the source rows; provide a sidecar mapping keyed to the existing row IDs or a new linked
version with explicit provenance. No kinetics fit is requested.
