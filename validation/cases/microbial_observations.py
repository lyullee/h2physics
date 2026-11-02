"""Deferred actual-workbook data checks; no loader/case executes at import."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(identifier="microbial-observation-current", profile="microbial-observations",
            entrypoint=__name__+":validate_current", invariants=(
                "actual licensed pinned workbook", "original row order and cached cells",
                "shared SI scaling and finite masks", "unresolved clock/port stays unresolved")),
        ValidationCase(identifier="microbial-observation-integrity", profile="microbial-observations",
            entrypoint=__name__+":validate_integrity", invariants=(
                "changed source bytes rejected before reading data", "original raw file unchanged",
                "source-bound blocks issued only after pinned workbook parsing",
                "forged/replaced measured values cannot inherit publisher identity")),
    )


def _root():
    import os
    from pathlib import Path
    value = os.environ.get("H2_CLUSTER_DATA_RAW_ROOT")
    if not value:
        raise ValueError("Supply the actual cluster licensed raw-data snapshot root")
    root = Path(value)
    if not root.is_absolute():
        raise ValueError("The cluster raw-data snapshot path must be absolute")
    return root


def validate_current(*, work_directory):
    import json
    import math
    from pathlib import Path

    import numpy as np

    from h2physics.data.microbial_observations import (
        FIRST_DATA_ROW,
        LAST_DATA_ROW,
        SOURCE_DOI,
        SOURCE_SHA256,
        iter_microbial_current,
    )
    blocks = tuple(iter_microbial_current(_root(), block_rows=997))
    rows = tuple(row for block in blocks for row in block.source_rows)
    assert rows == tuple(range(FIRST_DATA_ROW, LAST_DATA_ROW+1))
    maximum_error = 0.
    valid_counts = [0, 0]
    for block in blocks:
        table = block.observations
        assert not block.clock_alignment_resolved and not block.electrode_current_role_resolved
        assert not block.independently_validated_hydrogen
        assert table.row_ids == tuple(f"Potentiostat_data!{row}" for row in block.source_rows)
        assert np.array_equal(table.valid, np.isfinite(table.values))
        for row_index, original in enumerate(block.original_cached_cells):
            for column_index, factor in ((0, 86400.), (1, .001)):
                value = original[column_index]
                try:
                    expected = float(value)*factor if not isinstance(value, bool) else math.nan
                except (TypeError, ValueError, OverflowError):
                    expected = math.nan
                expected_valid = math.isfinite(expected)
                assert bool(table.valid[row_index, column_index]) == expected_valid
                if expected_valid:
                    valid_counts[column_index] += 1
                    maximum_error = max(maximum_error, abs(table.values[row_index, column_index]-expected))
        assert dict(table.context)["clock_alignment"].startswith("unresolved")
    assert maximum_error < 1e-9 and min(valid_counts) > 0
    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination/"current-observations.npz",
        values=np.concatenate([b.observations.values for b in blocks]),
        valid=np.concatenate([b.observations.valid for b in blocks]), rows=np.asarray(rows))
    metrics = {"preserved_source_rows": len(rows), "blocks": len(blocks),
               "same_export_unit_scaling_error": maximum_error,
               "finite_clock_cells": valid_counts[0], "finite_current_cells": valid_counts[1]}
    (destination/"source.json").write_text(json.dumps({"doi": SOURCE_DOI,
        "sha256": SOURCE_SHA256, "license": "CC-BY-4.0",
        "creators": ["Cerrillo, Miriam", "Burgos, Laura", "Noguerol, Joan", "Riau, Victor", "Bonmatí, August"],
        "scope": "source/unit/schema check only; not H2 validation",
        "metrics": metrics}, allow_nan=False)+"\n", encoding="utf-8")
    return ValidationOutcome(True, metrics, (
        "Same-source SI scaling/provenance only; no independent physical accuracy",
        "Three-chamber source; device/phase/clock/area and H2 measurement remain unqualified"))


def validate_integrity(*, work_directory):
    from dataclasses import replace
    import hashlib
    from pathlib import Path

    from h2physics.data.microbial_observations import (
        MicrobialCurrentBlock,
        SOURCE_RELATIVE_PATH,
        SOURCE_SHA256,
        iter_microbial_current,
    )
    original = (_root()/SOURCE_RELATIVE_PATH).read_bytes()
    assert hashlib.sha256(original).hexdigest() == SOURCE_SHA256
    alternate = Path(work_directory)/"tampered-snapshot"
    target = alternate/SOURCE_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(original[:-1]+bytes((original[-1]^1,)))
    try:
        next(iter_microbial_current(alternate))
    except ValueError as error:
        assert "SHA-256" in str(error)
    else:
        raise AssertionError("Changed workbook accepted")
    assert hashlib.sha256((_root()/SOURCE_RELATIVE_PATH).read_bytes()).hexdigest() == SOURCE_SHA256
    block = next(iter_microbial_current(_root(), block_rows=31))
    rejected = 0
    try:
        MicrobialCurrentBlock(
            block.observations, block.source_rows, block.original_cached_cells,
            block.invalid_tokens,
        )
    except ValueError:
        rejected += 1
    try:
        replace(block, source_sha256="0" * 64)
    except ValueError:
        rejected += 1
    altered = block.observations.values.copy()
    altered[0, 1] += 1.0
    try:
        replace(block, observations=replace(block.observations, values=altered))
    except ValueError:
        rejected += 1
    assert rejected == 3
    return ValidationOutcome(True, {"changed_source_rejected": 1,
        "original_source_unchanged": 1, "forged_provenance_paths_rejected": rejected},
        ("Source-lineage/integrity guards only; no calibration or H2-yield validation",))
