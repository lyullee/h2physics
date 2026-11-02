# Open measured hydrogen safety data shortlist

This shortlist applies the following release criteria: measured release,
dispersion, or jet-fire observations; a machine-readable payload; an explicit
reusable license; and a source record that can be cited and checksum-audited.
The strongest current matches are already acquired and catalogued in this
repository.

## Selected records already in the inventory

| Record | Fit and rights | Acquired source integrity | Main limits |
|---|---|---|---|
| [BAM hydrogen jet-fire tests](https://doi.org/10.5281/zenodo.21026781) | Zenodo API declares open access and CC BY 4.0. One 75,221,648-byte ZIP includes text exports for thermocouple histories, hydrogen mass flow, and infrared-related data. | Publisher MD5 `019059edc40e776d6c54d917931e4e39`; local archive SHA-256 `c4e199a20960174845f27dbbb6521b65c797740ba3f503463ee96073cf2d8bed`. The exact record API response and full receipt are in [`research/data/bam-hydrogen-jet-fire.toml`](../research/data/bam-hydrogen-jet-fire.toml). | The selected thermal-target channel does not establish incident heat flux. Geometry, calibration, target mapping, and test-condition linkage remain caller evidence. IR-camera assets are excluded pending separate rights and format review. See [`BAM_HYDROGEN_JET_FIRE_DATA.md`](BAM_HYDROGEN_JET_FIRE_DATA.md). |
| [USN open-channel hydrogen dispersion](https://doi.org/10.23642/usn.26117989.v2) | DataverseNO declares CC BY 4.0 and lists 23 public files, about 49.2 MB total. The description identifies temporal mass flow, filling pressure, and hydrogen concentration measured by 29 sensors. | All 23 files are acquired. The version-pinned Figshare V2 metadata, per-file sizes/checksums, and local SHA-256 values are in [`research/data/hydrogen-channel.toml`](../research/data/hydrogen-channel.toml). | Dataset filenames differ from article test labels; sensor units, clock interpretation, concentration basis, and calibration are not inferred. See [`HYDROGEN_CHANNEL_DATA.md`](HYDROGEN_CHANNEL_DATA.md). |

The [H2SAFE indoor-release dataset](https://data.openei.org/submissions/8799) is a
smaller CC BY 4.0 companion with time-series CSVs and 3D sensor/source metadata,
but its five tests release helium. It is suitable as explicitly qualified
surrogate-dispersion evidence, not as measured hydrogen dispersion. Its source
receipt and species limitations are in [`H2SAFE_INDOOR_DATA.md`](H2SAFE_INDOOR_DATA.md).

## Candidate excluded on rights evidence

NIST's [garage helium-dispersion page](https://www.nist.gov/el/fire/hydrogen-flammability-detection-and-fire-safety)
describes 18 machine-readable Excel test files (about 53 MB) with helium volume
fraction and differential pressure over time. This is useful measured surrogate
data, but the dataset page does not state a file-level license or reuse grant.
NIST's general guidance says its federal publications are generally public
domain in the United States, while its rights page also distinguishes technical
series works and reserves foreign rights; neither statement expressly grants
worldwide reuse of this separately linked archive. The archive is therefore not
downloaded, copied, or added to the inventory. A dataset-specific rights
statement from NIST is the remaining requirement.

## Source records

- [BAM Zenodo record](https://zenodo.org/records/21026781) and [official record API](https://zenodo.org/api/records/21026781).
- [DataverseNO channel record](https://dataverse.no/dataset.xhtml?persistentId=doi:10.23642/USN.26117989), [declared CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/).
- [NIST helium-dispersion data description](https://www.nist.gov/el/fire/hydrogen-flammability-detection-and-fire-safety), [NIST publication-rights FAQ](https://www.nist.gov/nist-research-library/library-faqs), and [NIST rights terms](https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications).

No model validation is implied by this source screen.
