"""Deferred contract for source-bound AHSS 1300 permeation observations."""

import importlib
from dataclasses import replace
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mendeley-ahss1300-source-bound-observations",
        profile="fracture-fatigue",
        entrypoint=__name__ + ":validate_source_ingest",
        parameters={
            "fixture_module": "validation.fixtures.ahss1300_permeation",
            "fixture_builder": "build_ahss1300_permeation_fixture",
        },
        invariants=(
            "all peer attachments from the versioned publisher listing are counted and retained in the source receipt",
            "workbook source-column header is preserved verbatim, including the original Greek-mu current-unit glyph",
            "publisher metadata and attachment-listing bytes match pinned hashes",
            "local workbook is regular, exact-sized and matches publisher SHA-256",
            "both worksheet identities, dimensions, row order and time/current pairs are preserved",
            "row IDs identify worksheet and original one-based workbook row",
            "missing, replaced or relabeled publisher attachments are rejected",
            "source workbook byte mutation is rejected before workbook parsing",
            "microampere current units are recovered without inventing exposed electrode area",
            "mutation of observation values invalidates source-bound result",
            "no dimensional hydrogen flux, diffusivity or material law is inferred",
        ),
    ),)


def validate_source_ingest(*, work_directory, **parameters):
    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or not isinstance(builder_name, str) or not builder_name.isidentifier()):
        raise ValueError("The AHSS 1300 source fixture must be explicitly configured")
    builder = getattr(importlib.import_module(module_name), builder_name, None)
    if not callable(builder):
        raise ValueError("Fixture module must provide the AHSS 1300 workbook and Dataset receipt")
    fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict) or set(fixture) != {
        "dataset", "workbook_path", "expected_current_header",
    }:
        raise TypeError("Fixture must return the dataset, workbook path and pinned source header")
    receipt = fixture["dataset"]
    if (receipt.key != "hydrogen-permeation-ms-ahss-1300"
            or receipt.title != "Hydrogen permeation test on MS AHSS grade 1300"
            or receipt.doi != "10.17632/tnsgf7v76z.1" or receipt.version != "1"
            or receipt.license_id != "CC-BY-4.0"
            or len(receipt.supporting_metadata) != 1
            or len(receipt.files) != 1):
        raise ValueError("Offline source fixture receipt differs from the pinned publisher record")

    from h2physics.data import load_ahss1300_permeation

    data = load_ahss1300_permeation(fixture["workbook_path"], dataset=fixture["dataset"])
    assert data.require_current() is data
    assert data.observation_counts == (1260, 599)
    assert tuple(data.values[0].shape) == (1260, 2)
    assert tuple(data.values[1].shape) == (599, 2)
    assert data.source_row_ids[0][0].endswith("row-2")
    assert data.source_row_ids[0][-1].endswith("row-1261")
    assert data.source_row_ids[1][0].endswith("row-2")
    assert data.source_row_ids[1][-1].endswith("row-600")
    assert data.current_unit == "uA"
    assert data.current_header == "Current, \u03bcA"
    assert fixture["expected_current_header"] == data.current_header
    assert all(values[0, 0] < values[-1, 0] for values in data.values)
    assert all(not values.flags.writeable for values in data.values)
    selected = data.observations(data.sheet_names[0])
    assert selected is data.values[0]
    import numpy as np

    for name in data.sheet_names:
        ampere = data.current_ampere(name)
        assert np.array_equal(ampere, data.observations(name)[:, 1] * 1e-6)
        assert not ampere.flags.writeable

    def rejected(call, label):
        try:
            call()
        except (TypeError, ValueError):
            return
        raise AssertionError(f"AHSS 1300 contract accepted {label}")

    remote = receipt.files[0]
    rejected(lambda: load_ahss1300_permeation(
        fixture["workbook_path"], dataset=replace(receipt, files=()),
    ), "a receipt without its publisher attachment")
    altered_digest = ("0" if remote.checksum[0] != "0" else "1") + remote.checksum[1:]
    replaced_remote = replace(remote, checksum=altered_digest)
    rejected(lambda: load_ahss1300_permeation(
        fixture["workbook_path"], dataset=replace(receipt, files=(replaced_remote,)),
    ), "a relabeled publisher attachment digest")
    wrong_listing_url, wrong_listing = receipt.supporting_metadata[0]
    rejected(lambda: load_ahss1300_permeation(
        fixture["workbook_path"], dataset=replace(
            receipt, supporting_metadata=((wrong_listing_url, wrong_listing + b" "),),
        ),
    ), "a replaced publisher attachment listing")

    corrupted_path = Path(work_directory) / "ahss1300-corrupted.xlsx"
    corrupted_path.parent.mkdir(parents=True, exist_ok=True)
    corrupted = bytearray(Path(fixture["workbook_path"]).read_bytes())
    corrupted[-1] ^= 1
    corrupted_path.write_bytes(corrupted)
    rejected(lambda: load_ahss1300_permeation(corrupted_path, dataset=receipt),
             "a source workbook with changed bytes")

    # Exercise schema gates on a private in-memory view; production bytes still
    # pass their exact publisher hash before this parser is ever reached.
    import io

    from openpyxl import load_workbook

    from h2physics.data.ahss1300_permeation import _read_source_workbook

    raw_bytes = Path(fixture["workbook_path"]).read_bytes()
    schema_rejections = 0
    for label, edit in (
        ("second header", lambda book: setattr(book.worksheets[1]["B1"], "value", "Current, A")),
        ("material location", lambda book: setattr(book.worksheets[0]["E3"], "value", None)),
        ("extra column", lambda book: setattr(book.worksheets[1]["G1"], "value", 1.0)),
        ("numeric string", lambda book: setattr(book.worksheets[1]["B2"], "value", "112")),
        ("duplicate time", lambda book: setattr(book.worksheets[1]["A3"], "value", book.worksheets[1]["A2"].value)),
    ):
        book = load_workbook(io.BytesIO(raw_bytes), data_only=True)
        try:
            edit(book)
            rejected(lambda: _read_source_workbook(book), label)
            schema_rejections += 1
        finally:
            book.close()

    altered = [value.copy() for value in data.values]
    altered[0][0, 0] += 1.0
    object.__setattr__(data, "values", tuple(altered))
    rejected = False
    try:
        data.require_current()
    except ValueError:
        rejected = True
    assert rejected
    return ValidationOutcome(True, {
        "title": data.title, "doi": data.doi, "author": data.author,
        "license_id": data.license_id, "source_url": data.source_url,
        "sheet_rows": [1260, 599],
        "current_unit_resolved": True, "no_material_coefficient_inferred": True,
        "schema_rejections": schema_rejections, "bad_receipts_rejected": True, "changed_workbook_rejected": True,
    }, (
        "This source contract checks measured worksheet ingestion only.",
        "Microampere current units are source-defined; exposed area and full boundary histories remain unresolved.",
    ))
