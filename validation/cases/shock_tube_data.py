"""Deferred checks for source-issued ELVHYS run summaries and recorder blocks."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="shock-tube-block-loader-provenance",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_block_issuance",
            invariants=(
                "a successful parsed signal block can only be issued by the reviewed recorder parser",
                "direct blocks cannot attach fabricated values and masks to a real recorder source receipt",
                "dataclass replacement cannot preserve source identity while changing parsed values",
                "ordinary bounded parser output retains original source lines and measurement access",
                "standalone local recorders do not claim the study DOI or publisher-run identity",
                "campaign conditions can only be projected from a study-issued metadata run",
                "dataclass replacement cannot retain campaign metadata provenance after field changes",
            ),
        ),
        ValidationCase(
            identifier="cryogenic-room-block-loader-provenance",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_cryogenic_room_block",
            invariants=(
                "only the checked source recorder issues source-identified cryogenic observation blocks",
                "direct construction and dataclass replacement cannot retain a recorder source identity with changed values",
                "parsed synthetic fixture keeps its exact source rows and observation interface",
            ),
        ),
        ValidationCase(
            identifier="thermal-effects-block-loader-provenance",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_thermal_effects_block",
            invariants=(
                "source-identified thermal blocks are issued only by the checked HDF5 reader",
                "direct construction and dataclass replacement cannot attach a publisher digest to substituted arrays",
                "the synthetic thermal reader fixture preserves original recorder and source identity",
            ),
        ),
    )


def validate_block_issuance(*, work_directory, **parameters):
    del parameters
    from pathlib import Path

    from h2physics.data.shock_tube import (
        DOI,
        HEADERS,
        ShockTubeBlock,
        ShockTubeRecorder,
        ShockTubeRun,
        _issue_shock_tube_run,
    )

    source = Path(work_directory) / "ELE431KIT011TEMP20240101.csv"
    header = HEADERS["TEMP"]
    numeric = lambda time: ";".join((str(time), *(["298.15"] * (len(header) - 1))))
    source.write_text(";".join(header) + "\n" + numeric(0) + "\n" + numeric(1) + "\n",
                      encoding="utf-8")
    recorder = ShockTubeRecorder(source)
    block = next(recorder.iter_blocks(block_rows=1))
    rejected = 0
    for forged in (
        lambda: replace(block, values=block.values + 100.0),
        lambda: ShockTubeBlock(block.recorder, block.source_lines, block.raw_lines,
            block.raw_cells, block.raw_values, block.values + 100.0, block.valid,
            block.reasons, block.predecessor_time_s),
    ):
        try:
            forged()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Caller-created parsed values retained an acquired source identity")
    assert len(block.source_lines) == 1 and block.source_lines[0] == 2
    assert block.observations.source_id == recorder.source_id
    assert recorder.source_id.startswith("local-file|")
    assert recorder.study_id != DOI
    metadata = dict(block.observations.context)
    assert metadata["study_id"] == "caller-supplied-local-file"

    run_values = ("ELEVHYS011:20240101", "011", "20240101", "unignited/inert-labelled",
        "synthetic-membrane", 100_000.0, .21, 293.15, 7, "a" * 64, "*")
    rejected_run_constructions = 0
    try:
        ShockTubeRun(*run_values)
    except ValueError:
        rejected_run_constructions += 1
    else:
        raise AssertionError("Direct campaign-summary construction claimed a source line/hash")
    issued_run = _issue_shock_tube_run(*run_values)
    try:
        replace(issued_run, burst_pressure_pa_reported=999_999.0)
    except ValueError:
        rejected_run_constructions += 1
    else:
        raise AssertionError("Replaced campaign summary retained metadata provenance")
    return ValidationOutcome(True, {
        "direct_or_replaced_forged_blocks_rejected": rejected,
        "qualified_parser_preserves_source_line_and_observation_access": True,
        "standalone_recorder_is_not_attributed_to_publisher_study": True,
        "direct_or_replaced_campaign_summaries_rejected": rejected_run_constructions,
    }, ("Synthetic CSV fixture only; no external source or network was used.",))


def validate_cryogenic_room_block(*, work_directory, **parameters):
    del parameters
    from dataclasses import replace
    from pathlib import Path

    from h2physics.data.oxygen_observations import (
        CryogenicRoomBlock,
        CryogenicRoomCase,
        CryogenicRoomRecorder,
    )
    from h2physics.data.pressure_peaking import file_sha256

    source = Path(work_directory) / "ELE402HSE001CONC20240101.csv"
    source.write_text("Time,H2A\n0,0.2\n1,0.3\n", encoding="utf-8")
    digest = file_sha256(source)
    case = CryogenicRoomCase(1, 2, (), 101325.0, 0.01, "synthetic", False, digest)
    recorder = CryogenicRoomRecorder(
        source, case=case, positions={}, expected_sha256=digest, directory_label="synthetic"
    )
    block = next(recorder.iter_blocks(block_rows=1))
    rejected = 0
    for forged in (
        lambda: replace(block, values=block.values + 100.0),
        lambda: CryogenicRoomBlock(
            block.recorder, block.source_lines, block.raw_lines, block.raw_cells,
            block.raw_values, block.numeric_valid, block.values + 100.0,
            block.valid, block.reasons,
        ),
    ):
        try:
            forged()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Forged values inherited a cryogenic source identity")
    assert len(block.source_lines) == 1 and block.source_lines[0] == 2
    assert block.observations.source_id == recorder.source_id
    return ValidationOutcome(True, {
        "direct_or_replaced_forged_blocks_rejected": rejected,
        "qualified_parser_preserves_source_line_and_observation_access": True,
    }, ("Synthetic CSV fixture only; no external source or network was used.",))


def validate_thermal_effects_block(*, work_directory, **parameters):
    del parameters
    import h5py
    import numpy as np
    from pathlib import Path

    from h2physics.data.pressure_peaking import file_sha256
    from h2physics.data.thermal_effects import (
        SOURCE_FIELDS,
        ThermalBlock,
        ThermalEffectsFile,
    )

    source = Path(work_directory) / "thermal-effects-source.h5"
    with h5py.File(source, "w") as native:
        for group_name, fields in SOURCE_FIELDS.items():
            if group_name == "TS":
                continue
            group = native.create_group(group_name)
            group.attrs["MATLAB_class"] = b"struct"
            for field_name in fields:
                dataset = group.create_dataset(
                    field_name, data=np.array([[0.0], [1.0]], dtype=np.float64)
                )
                dataset.attrs["MATLAB_class"] = b"double"

    digest = file_sha256(source)
    rejected = 0
    with ThermalEffectsFile(
        source, source_id="synthetic-thermal-source", experiment_id="run-1",
        expected_sha256=digest,
    ) as reader:
        recorder = next(
            item for item in reader.recorders
            if any(channel.path == "/HF/temp1" for channel in item.channels)
        )
        block = next(reader.iter_blocks(recorder, block_rows=1))
        for forge in (
            lambda: ThermalBlock(
                block.values + 100.0, block.valid, block.raw_values,
                block.source_indices, block.variables, block.origins,
                block.recorder, block.source_id, block.source_sha256,
                block.experiment_id, block.context, block.issues,
            ),
            lambda: replace(block, values=block.values + 100.0),
        ):
            try:
                forge()
            except ValueError:
                rejected += 1
            else:
                raise AssertionError("Forged thermal observations inherited the source digest")
    assert block.source_sha256 == digest
    assert block.observations.source_id == "synthetic-thermal-source"
    return ValidationOutcome(True, {
        "direct_or_replaced_forged_blocks_rejected": rejected,
        "reader_issued_block_keeps_source_digest": True,
    }, ("Synthetic HDF5 only; no external data or network was used.",))
