"""Deferred source-lineage checks for the MATLAB pressure-peaking reader."""

from dataclasses import replace

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="pressure-mat-loader-only-provenance",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_mat_loader_issuance",
            invariants=(
                "only the schema- and checksum-qualified MAT loader can issue recorder and run objects",
                "recorder blocks carrying source rows and file digests are issued only by an authorized recorder projection",
                "dataclass replacement cannot retain loader provenance while changing payload or identity",
                "ordinary bounded row extraction from a loader-issued synthetic MAT remains available",
            ),
        ),
        ValidationCase(
            identifier="pressure-concentration-loader-provenance",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_concentration_loader_issuance",
            invariants=(
                "only the checksum/schema-qualified XEN workbook loader can issue a workbook receipt",
                "only the workbook row iterator can issue source-bound concentration blocks",
                "dataclass replacement cannot retain loader/block issuance tokens",
                "mutated workbook identity or observation-block payload is rejected before projection",
                "legitimate bounded row projection retains original workbook source identities",
            ),
        ),
    )


def validate_mat_loader_issuance(*, work_directory, **parameters):
    del parameters
    from pathlib import Path

    from scipy.io import savemat

    from h2physics.data.pressure_peaking import (
        GEN_DIMENSIONS,
        GEN_LABELS,
        SIGMA_DIMENSIONS,
        SIGMA_LABELS,
        PressureMatRun,
        PressureRecorder,
        RecorderBlock,
        load_pressure_mat,
    )

    source = Path(work_directory) / "pressure-peaking-lineage.mat"
    savemat(source, {
        "SIGMA": np.array([[0.0, 1.0, 1.0], [0.1, 2.0, 1.1]]),
        "GEN3i": np.array([[0.0, 1.0], [0.1, 2.0]]),
        "SIGMAdimensions": np.asarray(SIGMA_DIMENSIONS, dtype=object),
        "SIGMAunits": np.asarray(SIGMA_LABELS, dtype=object),
        "GENdimensions": np.asarray(GEN_DIMENSIONS, dtype=object),
        "GENunits": np.asarray(GEN_LABELS, dtype=object),
    })
    run = load_pressure_mat(source, source_id="synthetic-pressure-fixture",
                            experiment_id="synthetic-run")
    block = next(run.sigma.iter_blocks(block_rows=1))
    expected_rejections = 0
    forged = (
        lambda: PressureRecorder(run.sigma.raw, "SIGMA", SIGMA_DIMENSIONS, SIGMA_LABELS,
            run.source_id, run.source_sha256, run.experiment_id, run.sigma.clock_id),
        lambda: PressureMatRun(run.source_id, run.source_sha256, run.experiment_id,
            run.sigma, run.gen3i, run.issues),
        lambda: RecorderBlock(block.series, block.source_rows, block.experiment_id,
            block.source_sha256, block.matrix_name),
        lambda: replace(run.sigma, source_sha256="0" * 64),
        lambda: replace(run, source_id="forged-source"),
        lambda: replace(block, source_sha256="0" * 64),
    )
    for construct in forged:
        try:
            construct()
        except ValueError:
            expected_rejections += 1
        else:
            raise AssertionError("MAT source provenance was forged by direct construction/replacement")
    assert len(block.source_rows) == 1 and int(block.source_rows[0]) == 1
    assert run.source_sha256 == run.sigma.source_sha256 == run.gen3i.source_sha256
    return ValidationOutcome(True, {
        "forged_or_replaced_mat_receipts_rejected": expected_rejections,
        "legitimate_loader_projection_preserved_source_rows": True,
    }, ("Synthetic MAT fixture only; no external source file or network was used.",))


def validate_concentration_loader_issuance(*, work_directory, **parameters):
    del parameters
    from pathlib import Path

    from openpyxl import Workbook

    from h2physics.data.pressure_peaking import (
        CONCENTRATION_HEADERS,
        ConcentrationBlock,
        PressureConcentrationWorkbook,
        PressureDataIssue,
        file_sha256,
        load_pressure_concentration,
    )

    path = Path(work_directory) / "pressure-concentration-lineage.xlsx"
    workbook_file = Workbook()
    sheet = workbook_file.active
    sheet.title = "XEN-H2"
    metadata_headers = ("Device ID", "Factory Device ID", "Firmware", "Measurement mode") + tuple(
        f"Metadata {index}" for index in range(5, 18))
    metadata_values = ("device-A", "device-A", "firmware-fixture", "H2") + ("",) * 13
    sheet.append(metadata_headers)
    sheet.append(metadata_values)
    sheet.append(CONCENTRATION_HEADERS)
    sheet.append((1, "00:00:00.0", 1.0, 1.0, 25.0, 25.0, 50.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 50.0, 0))
    workbook_file.save(path)
    workbook_file.close()

    source = load_pressure_concentration(
        path, source_id="synthetic-xen-fixture", experiment_id="synthetic-xen-run",
        expected_sha256=file_sha256(path),
    )
    block = next(source.iter_blocks(block_rows=1))
    rejected = 0
    forged = (
        lambda: PressureConcentrationWorkbook(
            source.path, source.source_id, source.source_sha256, source.experiment_id,
            source.sheet_name, source.headers, source.metadata_headers, source.metadata_values,
            source.clock_id, source.issues,
        ),
        lambda: ConcentrationBlock(block.observations, block.raw_clock_strings,
                                   block.issues, block.clock_id),
        lambda: replace(source, source_id="forged-xen-source"),
        lambda: replace(block, clock_id="forged-clock"),
    )
    for construct in forged:
        try:
            construct()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("XEN workbook/block provenance was forged by construction or replacement")

    assert block.observations.source_id == "synthetic-xen-fixture"
    assert block.observations.row_ids == (
        "synthetic-xen-fixture|XEN-H2|row-4",
    )
    object.__setattr__(block, "issues", (PressureDataIssue("forged", "Time", 1),))
    try:
        block.as_time_series()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Mutated concentration block remained current")

    object.__setattr__(source, "source_id", "forged-after-load")
    try:
        next(source.iter_blocks(block_rows=1))
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Mutated workbook receipt remained current")
    return ValidationOutcome(True, {
        "direct_clone_and_mutation_rejections": rejected,
        "legitimate_xlsx_source_row_preserved": True,
    }, ("Synthetic XLSX fixture only; no external workbook or network was used.",))
