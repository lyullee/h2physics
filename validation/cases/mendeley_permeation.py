"""Deferred source-bound ingest contract for normalized steel permeation MAT data."""

import importlib

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mendeley-ms1700-qp1180-normalized-permeation-ingest",
        profile="fracture-fatigue",
        entrypoint=__name__ + ":validate_normalized_permeation_ingest",
        parameters={
            "fixture_module": "REPLACE_WITH_MENDELEY_PERMEATION_FIXTURE_MODULE",
            "fixture_builder": "build_mendeley_permeation_fixture",
        },
        invariants=(
            "resolved CC-BY-4.0 v1 Dataset metadata and attachment listing are pinned",
            "result retains publisher title, contributor attribution, measured origin and license identity",
            "MAT input is local, regular, exact-sized and SHA-256 matched to publisher listing",
            "both grade arrays retain source variable, source row order and exact row identities",
            "normalized time and flux coordinates are returned unchanged and immutable",
            "wrong grade or modified post-load coordinates are rejected",
            "no dimensional flux, diffusivity, solubility, trapping law or material coefficient is inferred",
        ),
    ),)


def validate_normalized_permeation_ingest(*, work_directory, **parameters):
    """Load an offline staged source fixture; never discover or download files."""
    from h2physics.data.mendeley_permeation import load_mendeley_normalized_permeation

    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name
            or not isinstance(builder_name, str) or not builder_name.isidentifier()):
        raise ValueError("Configure an offline Mendeley permeation source fixture and builder")
    builder = getattr(importlib.import_module(module_name), builder_name, None)
    if not callable(builder):
        raise ValueError("Fixture module must expose the configured builder")
    fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict) or set(fixture) != {"dataset", "mat_path"}:
        raise TypeError("Fixture must return the resolved Dataset receipt and staged MAT path")

    source = load_mendeley_normalized_permeation(
        fixture["mat_path"], dataset=fixture["dataset"]
    )
    assert source.require_current() is source
    assert tuple(item.material_grade for item in source.series) == ("MS1700", "QP1180")
    assert tuple(item.variable_name for item in source.series) == ("Msdata", "QPdata")
    assert tuple(len(item.source_row_ids) for item in source.series) == (2197, 1333)
    assert tuple(item.source_row_ids[0].rsplit(":", 1)[-1] for item in source.series) == (
        "row-1", "row-1"
    )
    assert all(item.coordinates.shape == (count, 2) and not item.coordinates.flags.writeable
               for item, count in zip(source.series, (2197, 1333), strict=True))
    for invalid_grade in ("ms1700", "", "MS1700/QP1180"):
        try:
            source.for_grade(invalid_grade)
        except ValueError:
            pass
        else:
            raise AssertionError("Reader accepted a grade selection outside its exact material IDs")

    object.__setattr__(source.series[0], "coordinates", source.series[0].coordinates.copy())
    try:
        source.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Reader accepted changed normalized coordinate values")

    return ValidationOutcome(True, {
        "title": source.title,
        "doi": source.doi,
        "version": source.version,
        "authors": source.authors,
        "origin": source.origin.value,
        "license_id": source.license_id,
        "grade_row_counts": {item.material_grade: len(item.source_row_ids)
                             for item in source.series},
        "source_sha256": source.source_sha256,
        "coordinates_immutable": True,
        "post_load_mutation_rejected": True,
    }, (
        "The fixture verifies source-bound normalized coordinates only; no measured physical coefficient is inferred.",
        "The source labels its first coordinate s/m² and its second coordinate normalized flux; no dimensional flux scale is supplied.",
    ))
