"""Deferred source and structural-contract cases for HE-Austenite observations."""

from __future__ import annotations

import hashlib
import os
import tomllib
from dataclasses import replace
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

RECEIPT_RELATIVE = Path("research/data/austenite-embrittlement.toml")
DATA_ROOT_VARIABLE = "H2_DATA_AUSTENITE_ROOT"
DATASET_DOI = "10.5281/zenodo.23107780"
DATASET_RECORD = "23107780"


def _source_parameters():
    root = os.environ.get(DATA_ROOT_VARIABLE)
    return {} if not root else {"source_path": root}


def cases():
    return (
        ValidationCase(
            identifier="austenite-observation-provenance",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_source_provenance",
            parameters=_source_parameters(),
            invariants=(
                "missing external-data path is rejected and the exact Zenodo record/version is pinned",
                "pinned CC-BY identity, all acquired-file SHA-256/MD5/size fields and unqualified status are retained",
                "113 compiled records preserve unique source identities and all original row fields",
                "31 linked composition records and 102 explicit record mappings remain separate",
                "literature compilation status is not promoted to independent material validation",
            ),
        ),
        ValidationCase(
            identifier="austenite-observation-contract-integrity",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_observation_contracts",
            parameters=_source_parameters(),
            invariants=(
                "block source records, observation rows, numeric columns and invalid reasons stay aligned",
                "paired-property residuals and tolerance classifications are internally consistent",
                "malformed row identity, invalid-reason shape, result shape, residual and mask bindings are rejected",
                "receipt identity, rights and non-pinned acquired-file digests are rejected",
                "same-compilation arithmetic is not reported as independent model validation",
            ),
        ),
    )


def _load_source(*, source_root: str | None = None):
    if source_root is None:
        source_root = os.environ.get(DATA_ROOT_VARIABLE)
    if not source_root:
        raise ValueError(
            f"Stage the external dataset on the cluster and set {DATA_ROOT_VARIABLE} in the profile setup"
        )
    directory = Path(source_root)
    if not directory.is_absolute():
        raise ValueError(f"{DATA_ROOT_VARIABLE} must be an absolute cluster path")
    repository = Path(__file__).resolve().parents[2]
    receipt = tomllib.loads((repository / RECEIPT_RELATIVE).read_text(encoding="utf-8"))
    if (
        receipt["doi"] != DATASET_DOI
        or receipt["version"] != DATASET_RECORD
        or receipt["license_id"] != "CC-BY-4.0"
        or not receipt["rights_permitted"]
        or receipt["validation_qualified"] is not False
    ):
        raise ValueError("Pinned dataset identity, rights or unqualified status do not admit this source profile")
    from h2physics.data import EmbrittlementCollection

    return receipt, EmbrittlementCollection.from_receipt(directory, receipt)


def validate_source_provenance(*, work_directory, **parameters):
    del work_directory
    try:
        _load_source(source_root="")
    except ValueError:
        pass
    else:
        raise AssertionError("Missing staged source path was not rejected")
    receipt, collection = _load_source(source_root=parameters.get("source_path"))
    with collection as source:
        if len(source.records) != 113 or len(source.compositions) != 31:
            raise ValueError("Pinned HE-Austenite v1.0 table dimensions differ from the receipt audit")
        if len(source.composition_mapping) != 102:
            raise ValueError("Pinned HE-Austenite v1.0 composition mapping count differs")
        if any(not record.row_id or len(record.source.cells) != 45 for record in source.records):
            raise ValueError("Each source record must retain its complete 45-field source row")
        unmapped = sum(record.linked_composition is None for record in source.records)
        if unmapped != 11:
            raise ValueError("Unmapped composition rows must remain explicit")
        file_count = len(collection.expected_sha256)
        acquired = [entry for entry in receipt["files"] if entry.get("status") == "acquired"]
        if len(acquired) != file_count or len(acquired) != 9:
            raise ValueError("Acquired-file receipt does not match the reviewed nine-file profile")
        if sum(entry["size_bytes"] for entry in acquired) != receipt["acquired_bytes"]:
            raise ValueError("Receipt acquired-byte total differs from its file inventory")
        if len(receipt["files"]) != receipt["listed_file_count"]:
            raise ValueError("Receipt listed-file count differs from its complete inventory")
        for entry in acquired:
            name = entry["name"]
            path = collection.directory / name
            if Path(entry["relative_path"]).name != name:
                raise ValueError("Receipt staging path does not resolve to its declared filename")
            payload = path.read_bytes()
            if (
                len(payload) != entry["size_bytes"]
                or hashlib.sha256(payload).hexdigest() != entry["sha256"]
                or hashlib.md5(payload, usedforsecurity=False).hexdigest() != entry["publisher_checksum"]
                or collection.expected_sha256.get(name) != entry["sha256"]
                or entry["publisher_checksum_algorithm"] != "md5"
                or entry["publisher_checksum_verified"] is not True
            ):
                raise ValueError(f"Staged source file differs from its receipt custody fields: {name}")

    return ValidationOutcome(
        accepted=True,
        metrics={
            "record_count": len(source.records),
            "composition_count": len(source.compositions),
            "composition_mapping_count": len(source.composition_mapping),
            "unmapped_record_count": unmapped,
            "acquired_file_count": file_count,
        },
        limitations=(
            "Source provenance/schema only. The table is a literature compilation, not a new experiment; "
            "underlying paper rights, specimen identity, material heat identity and independent validation remain open.",
            f"Dataset DOI and CC BY 4.0 terms come from the pinned receipt: {receipt['doi']}.",
        ),
    )


def validate_observation_contracts(*, work_directory, **parameters):
    del work_directory
    from h2physics.data.embrittlement import (
        EmbrittlementBlock,
        PROPERTIES,
        PairedPropertyCheck,
        paired_property_check,
    )

    receipt, collection = _load_source(source_root=parameters.get("source_path"))
    from h2physics.data import EmbrittlementCollection

    for field, value in (("version", "other"), ("license_id", "UNLICENSED"),
                         ("rights_permitted", False)):
        altered = dict(receipt)
        altered[field] = value
        try:
            EmbrittlementCollection.from_receipt(collection.directory, altered)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Altered receipt {field} was admitted")
    altered = dict(receipt)
    altered["files"] = list(receipt["files"])
    altered["files"][0] = dict(altered["files"][0], sha256="0" * 64)
    try:
        EmbrittlementCollection.from_receipt(collection.directory, altered)
    except ValueError:
        pass
    else:
        raise AssertionError("Altered acquired-file digest was admitted")

    checked_rows = 0
    checked_properties = 0
    with collection as source:
        for property_name in PROPERTIES:
            for block in source.iter_blocks(property_name, block_rows=17):
                checked_properties += 1
                checked_rows += len(block.records)
                if block.observations.row_ids != tuple(record.row_id for record in block.records):
                    raise ValueError("Source row identities changed during property block construction")
                if len(block.invalid_reasons) != len(block.records):
                    raise ValueError("Invalid-reason rows do not match source record rows")
                check = paired_property_check(block)
                if not np.array_equal(
                    check.within_tolerance,
                    check.available & (np.abs(check.residual) <= check.tolerance),
                ):
                    raise ValueError("Paired-property tolerance classifications are inconsistent")
                try:
                    EmbrittlementBlock(block.observations, block.records, block.invalid_reasons)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Caller-fabricated embrittlement block retained publisher identity")
                try:
                    replace(block)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Copied embrittlement block reused its issuance token")
                original_reasons = block.invalid_reasons
                if block.records:
                    changed_reasons = list(original_reasons)
                    first = list(changed_reasons[0])
                    first[0] = first[0] + ":tampered"
                    changed_reasons[0] = tuple(first)
                    object.__setattr__(block, "invalid_reasons", tuple(changed_reasons))
                    try:
                        paired_property_check(block)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("Changed source-block audit metadata remained current")
                    finally:
                        object.__setattr__(block, "invalid_reasons", original_reasons)
                try:
                    malformed_records = (
                        tuple(reversed(block.records)) if len(block.records) > 1 else ()
                    )
                    replace(block, records=malformed_records)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Reordered source-record binding was admitted")
                malformed_reasons = (
                    block.invalid_reasons[:-1] if len(block.records) > 1 else ()
                )
                try:
                    replace(block, invalid_reasons=malformed_reasons)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Misaligned invalid-reason binding was admitted")

        fixture = PairedPropertyCheck(
            ("paired-valid", "paired-missing"),
            np.array([0.5, np.nan]),
            np.array([0.5, np.nan]),
            np.array([0.0, np.nan]),
            np.array([True, False]),
            np.array([True, False]),
            0.002,
        )
        invalid_fixtures = (
            {"residual": np.array([0.1, np.nan])},
            {"available": np.array([True, True])},
            {"within_tolerance": np.array([False, False])},
            {"calculated_ratio": np.array([0.5])},
        )
        for changes in invalid_fixtures:
            try:
                replace(fixture, **changes)
            except ValueError:
                continue
            raise AssertionError(f"Malformed paired-property result was admitted: {tuple(changes)}")

    return ValidationOutcome(
        accepted=True,
        metrics={"property_block_count": checked_properties, "source_row_count": checked_rows},
        limitations=(
            "Checks data binding and arithmetic result contracts only; the paired ratios come from one compilation "
            f"({receipt['doi']}) and are not independent physical/model validation.",
        ),
    )
