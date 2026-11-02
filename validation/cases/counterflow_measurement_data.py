"""Deferred source-hash and schema checks for acquired counterflow measurements."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

DATA_ARCHIVE_SHA256 = "8b905fe6653c2c526301f050883ec271eee5d85df73797faf85f0c45c4b729db"
ESR_WORKBOOK_SHA256 = "39c5dc653c0f123f91cdf00ccadb031ba9ed5df587b68c54511098109bb88d35"
NORMALIZED_OPTICAL_SHA256 = "b038d513a4b613b477c44f9c38e6882a88234bcd4f8995b04d6a6b2ec5b8548c"
OPTICAL_SPECTRA_SHA256 = "547b2b9886cd22e58758944032a52648ae20f10c28437c2bc3424b8e0e1a8236"


def cases():
    return (
        ValidationCase(
            identifier="counterflow-extinction-data-ingest",
            profile="counterflow-data",
            entrypoint=__name__ + ":validate_extinction_ingest",
            parameters={},
            invariants=(
                "archive and workbook SHA-256 receipts",
                "eight measured extinction rows",
                "nine temperature and twelve species profiles",
                "sixty normalized optical profiles and three band/spectral series each",
                "source row/column identities and axis units",
            ),
        ),
    )


def validate_extinction_ingest(*, work_directory, archive_root, archive_path, **parameters):
    from dataclasses import replace
    import hashlib

    from h2physics.data.counterflow_flame import (
        load_extinction_strain_rates,
        load_inflame_species_profiles,
        load_normalized_optical_profiles,
        load_optical_band_integrals,
        load_optical_spectra,
        load_temperature_profiles,
    )

    with open(archive_path, "rb") as archive:
        archive_sha256 = hashlib.file_digest(archive, "sha256").hexdigest()
    if archive_sha256 != DATA_ARCHIVE_SHA256:
        raise AssertionError("The BagIt archive does not match the acquired receipt")
    dataset = load_extinction_strain_rates(archive_root)
    rows = tuple(record.source_row for record in dataset.observations)
    if dataset.workbook_sha256 != ESR_WORKBOOK_SHA256:
        raise AssertionError("The extinction-rate workbook does not match the acquired receipt")
    if rows != tuple(range(2, 10)):
        raise AssertionError("The source table rows were omitted, reordered or duplicated")
    if dataset.license != "CC-BY-4.0" or len(dataset.observations) != 8:
        raise AssertionError("Dataset identity, license or measured-row count changed")
    temperatures = load_temperature_profiles(archive_root)
    if len(temperatures) != 9 or any(
        profile.observable != "temperature" for profile in temperatures
    ):
        raise AssertionError("Expected nine source-bound temperature profile pairs")
    if any(len(profile.coordinate_m) != len(profile.values) for profile in temperatures):
        raise AssertionError("Temperature profile coordinates and observations are misaligned")
    species = load_inflame_species_profiles(archive_root)
    if len(species) != 12 or {profile.observable for profile in species} != {"H2", "NH3", "NO"}:
        raise AssertionError("Expected four source-bound H2/NH3/NO profile groups")
    if any(len(profile.coordinate_m) != len(profile.values) for profile in species):
        raise AssertionError("Species profile coordinates and observations are misaligned")
    optical = load_normalized_optical_profiles(archive_root)
    if len(optical) != 60 or {profile.diagnostic for profile in optical} != {
        "NHX",
        "NOX",
        "OHX",
        "Vis",
    }:
        raise AssertionError("Expected fifteen normalized optical profiles for each diagnostic")
    if any(profile.axis_unit != "m" for profile in optical):
        raise AssertionError("Spatial optical coordinates were not converted to metres")
    if {profile.workbook_sha256 for profile in optical} != {NORMALIZED_OPTICAL_SHA256}:
        raise AssertionError("The normalized optical workbook checksum changed")
    band_integrals = load_optical_band_integrals(archive_root)
    if {profile.diagnostic for profile in band_integrals} != {"NO*", "OH*", "NH*"}:
        raise AssertionError("The three optical band-integral series were not retained")
    if {profile.workbook_sha256 for profile in band_integrals} != {OPTICAL_SPECTRA_SHA256}:
        raise AssertionError("The band-integral workbook checksum changed")
    spectra = load_optical_spectra(archive_root)
    if {spectrum.band for spectrum in spectra} != {
        "NO*-dominated wavelength range",
        "OH*-dominated wavelength range",
        "NH*-dominated wavelength range",
    }:
        raise AssertionError("The three reported spectral diagnostic ranges were not retained")
    if {spectrum.workbook_sha256 for spectrum in spectra} != {OPTICAL_SPECTRA_SHA256}:
        raise AssertionError("The optical spectra workbook checksum changed")
    missing_optical = sum(
        value is None
        for profile in optical + band_integrals
        for value in profile.normalized_intensity
    )
    if missing_optical == 0:
        raise AssertionError("Missing source optical intensities were not retained explicitly")
    for record in (dataset, temperatures[0], species[0], optical[0], spectra[0]):
        try:
            replace(record)
        except ValueError:
            pass
        else:
            raise AssertionError("A source-bound counterflow record was cloned without its loader")
    try:
        from h2physics.data.counterflow_flame import MeasuredFlameProfile

        MeasuredFlameProfile(
            "forged-temperature",
            "temperature",
            "K",
            temperatures[0].coordinate_m,
            temperatures[0].values,
            temperatures[0].conditions,
            temperatures[0].source_rows,
            temperatures[0].source_columns,
            temperatures[0].workbook_name,
            temperatures[0].workbook_sha256,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A caller-constructed profile claimed publisher workbook provenance")
    return ValidationOutcome(
        True,
        {
            "archive_sha256": archive_sha256,
            "workbook_sha256": dataset.workbook_sha256,
            "measurement_rows": len(dataset.observations),
            "first_source_row": rows[0],
            "last_source_row": rows[-1],
            "temperature_profiles": len(temperatures),
            "species_profiles": len(species),
            "normalized_optical_profiles": len(optical),
            "band_integral_series": len(band_integrals),
            "spectral_series": len(spectra),
            "retained_missing_optical_intensities": missing_optical,
            "source_receipt_direct_or_clone_forgery_rejected": True,
        },
        (
            "Ingestion and provenance audit only; no flame solve or model-data comparison.",
            "NH3/H2 transfer dataset; not pure-H2 validation.",
        ),
    )
