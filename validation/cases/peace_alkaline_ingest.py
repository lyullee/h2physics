"""Deferred synthetic token-preservation contract for PEACE raw CSV intake."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="peace-alkaline-raw-token-ingest",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_synthetic_contract",
        invariants=(
            "semicolon-delimited fields and comma-decimal tokens are retained as strings",
            "source labels and blank cells are preserved without unit or clock inference",
            "an explicitly selected header row is required; malformed row widths fail",
            "the synthetic parser contract does not establish electrolysis-model validation",
        ),
    ), ValidationCase(
        identifier="peace-alkaline-source-bound-file-integrity",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_synthetic_file_integrity",
        invariants=(
            "source bytes are checked against declared filename, byte length, publisher MD5 and SHA-256 before UTF-8 decoding",
            "the typed table retains exact bytes, parsed preamble and string-valued source fields",
            "require_current rejects same-path bytes changed after source-bound loading",
            "the synthetic integrity contract does not load the archive or validate a physical model",
        ),
    ), ValidationCase(
        identifier="peace-alkaline-publisher-described-source-projection",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_synthetic_projection",
        invariants=(
            "raw experiment and description map receipts are independently checked before parsing",
            "selected publisher-described values remain immutable strings aligned to original data rows",
            "source IDs, cleaned labels and full description text are retained without unit extraction",
            "normal volume basis, calibration, clock alignment and stack-versus-cell interpretation remain unresolved",
        ),
    ), ValidationCase(
        identifier="peace-alkaline-projection-forgery-rejection",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_synthetic_forgery_rejection",
        invariants=(
            "directly constructed source and projection wrappers are not accepted as loader-issued objects",
            "dataclass replacements that alter parsed rows, mapping text or projected channels fail freshness checks",
            "in-place mutation through object-level escape hatches is detected by source reconstruction",
            "only synthetic files are used; no real archived bytes or physical quantities are evaluated",
        ),
    ), ValidationCase(
        identifier="peace-alkaline-unit-safe-source-normalization",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_synthetic_unit_normalization",
        invariants=(
            "ampere, kilowatt, volt, degree-Celsius and reported-bar channels receive only declared SI unit conversions",
            "every normalized series retains the exact source token series and source descriptor",
            "time, H2 normal-volume flow and H2 quality remain raw without unsupported basis interpretation",
            "reported pressure remains pressure-basis unresolved and is not converted to an absolute pressure",
        ),
    ), ValidationCase(
        identifier="peace-alkaline-existing-stack-model-bridge",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_synthetic_stack_model_bridge",
        invariants=(
            "source-hash-bound same-row current, voltage and caller-selected temperature enter the existing HydrogenStack model",
            "model geometry and sensor-to-state mappings are explicit caller inputs; no stack calibration is claimed",
            "only observed rows are evaluated with no interpolation or extrapolation",
            "hydrogen flow remains raw because its normal-volume reference state is unspecified",
        ),
    ),)


def validate_synthetic_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.data.peace_alkaline import read_raw_token_table

    table = read_raw_token_table(
        "preamble\nSensor-A;Voltage raw;Clock token\n1,25;2,0;09:10:11\n2,50;;09:10:12\n",
        header_row=1,
    )
    assert table.header == ("Sensor-A", "Voltage raw", "Clock token")
    assert table.rows == (("1,25", "2,0", "09:10:11"), ("2,50", "", "09:10:12"))
    try:
        read_raw_token_table("A;B\n1\n")
    except ValueError:
        rejected = True
    else:
        rejected = False
    assert rejected
    return ValidationOutcome(True, {
        "synthetic_rows": len(table.rows),
        "source_tokens_preserved": True,
        "malformed_width_rejected": rejected,
    }, (
        "Synthetic token-preservation only; publisher files are not read by this case.",
        "No channel units, calibration, cell performance or process-model parameter is inferred.",
    ))


def validate_synthetic_file_integrity(*, work_directory, **parameters):
    del parameters
    import hashlib
    from pathlib import Path

    from h2physics.data.peace_alkaline import load_raw_file

    directory = Path(work_directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "experiment_1_raw.csv"
    payload = "synthetic preamble\nA raw;B raw\n1,25;09:10:11\n".encode("utf-8")
    path.write_bytes(payload)
    table = load_raw_file(
        path,
        expected_filename=path.name,
        expected_size_bytes=len(payload),
        expected_publisher_md5=hashlib.md5(payload).hexdigest(),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        header_row=1,
    )
    assert table.raw_bytes == payload
    assert table.preamble == (("synthetic preamble",),)
    assert table.header == ("A raw", "B raw")
    assert table.rows == (("1,25", "09:10:11"),)
    table.require_current()

    path.write_bytes(payload.replace(b"1,25", b"1,26"))
    try:
        table.require_current()
    except ValueError:
        stale_rejected = True
    else:
        stale_rejected = False
    assert stale_rejected
    return ValidationOutcome(True, {
        "synthetic_source_bytes_retained": len(table.raw_bytes),
        "preamble_rows_retained": len(table.preamble),
        "stale_same_path_rejected": stale_rejected,
    }, (
        "Synthetic file integrity only; no ignored publisher files are opened.",
        "CSV fields remain strings; no units, values or clock alignment are inferred.",
    ))


def validate_synthetic_projection(*, work_directory, **parameters):
    del parameters
    import hashlib
    from pathlib import Path

    from h2physics.data.peace_alkaline import (
        load_column_descriptions,
        load_raw_file,
        project_source_observations,
    )

    directory = Path(work_directory)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / "experiment_1_raw.csv"
    map_path = directory / "column_descriptions.csv"
    raw_bytes = (
        "Zeit;ATA00 CE001;ATA00 CE002;ATA00 CE003;RAA10 CT001;RAA10 CT002;RAA10 CT003;"
        "RAA30 CT001;RAA20 CT001;RAA20 CP001;RAA20 CF002;RAA20 CQ001\n"
        "10:00:00;12,5;4,2;3,8;21,0;22,0;23,0;19,0;20,0;2,03;0,02314815;0,78\n"
        "10:00:01;12,6;4,3;3,9;21,1;22,1;23,1;19,1;20,1;2,04;;0,79\n"
    ).encode("utf-8")
    descriptions = (
        ("Zeit", "time", "Timestamp (HH:MM:SS)"),
        ("ATA00 CE001", "Total Current (A)", "Total electrical current in amperes"),
        ("ATA00 CE002", "Total Power (kW)", "Total electrical power in kilowatts"),
        ("ATA00 CE003", "Total Voltage (V)", "Total voltage in volts"),
        ("RAA10 CT001", "T_in_lye (°C)", "Inlet lye temperature in degrees Celsius"),
        ("RAA10 CT002", "T_out_lyeh2 (°C)", "Outlet lye temperature on H2 side in degrees Celsius"),
        ("RAA10 CT003", "T_out_lyeo2 (°C)", "Outlet lye temperature on O2 side in degrees Celsius"),
        ("RAA30 CT001", "Oxygen gas temperature after cooling (°C)", "O2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CT001", "H2 gas Temperature after cooling (°C)", "H2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CP001", "System Pressure (bar)", "System operating pressure in bar"),
        ("RAA20 CF002", "Hydrogen flow rate (Nm3/h)", "Hydrogen output flow rate in normal cubic meters per hour"),
        ("RAA20 CQ001", "H2 quality (%)", "Purity/quality of hydrogen output in percent"),
    )
    map_text = "original_column,cleaned_column,description\n" + "".join(
        f'"{source}","{label}","{description}"\n'
        for source, label, description in descriptions
    )
    map_bytes = map_text.encode("utf-8")
    raw_path.write_bytes(raw_bytes)
    map_path.write_bytes(map_bytes)
    raw = load_raw_file(
        raw_path,
        expected_filename=raw_path.name,
        expected_size_bytes=len(raw_bytes),
        expected_publisher_md5=hashlib.md5(raw_bytes).hexdigest(),
        expected_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
    column_map = load_column_descriptions(
        map_path,
        expected_filename=map_path.name,
        expected_size_bytes=len(map_bytes),
        expected_publisher_md5=hashlib.md5(map_bytes).hexdigest(),
        expected_sha256=hashlib.sha256(map_bytes).hexdigest(),
    )
    block = project_source_observations(raw, column_map)
    assert block.source_row_indices == (0, 1)
    assert block.time.values == ("10:00:00", "10:00:01")
    assert block.total_current.values == ("12,5", "12,6")
    assert block.total_power.values == ("4,2", "4,3")
    assert block.total_voltage.values == ("3,8", "3,9")
    assert len(block.temperatures) == 5
    assert block.reported_pressure.values == ("2,03", "2,04")
    assert block.hydrogen_flow.values == ("0,02314815", "")
    assert block.hydrogen_quality.values == ("0,78", "0,79")
    assert block.total_current.description.source_channel_id == "ATA00 CE001"
    assert block.total_current.description.publisher_label == "Total Current (A)"
    assert block.total_current.description.publisher_description_text == "Total electrical current in amperes"
    assert block.hydrogen_flow.description.publisher_label == "Hydrogen flow rate (Nm3/h)"
    block.require_current()
    return ValidationOutcome(True, {
        "synthetic_source_rows": len(block.source_row_indices),
        "selected_channels": 11,
        "temperature_channels": len(block.temperatures),
        "source_hashes_bound": True,
    }, (
        "Synthetic source projection only; the acquired publisher files are not accessed.",
        "Values remain source tokens; normal-volume reference conditions, calibration, cell/stack semantics and clock interpretation remain unresolved.",
    ))


def validate_synthetic_forgery_rejection(*, work_directory, **parameters):
    del parameters
    import dataclasses
    import hashlib
    from pathlib import Path

    from h2physics.data.peace_alkaline import (
        PEACEColumnDescriptionMap,
        PEACEObservationBlock,
        SourceTokenTable,
        load_column_descriptions,
        load_raw_file,
        project_source_observations,
    )

    directory = Path(work_directory)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / "experiment_1_raw.csv"
    map_path = directory / "column_descriptions.csv"
    raw_bytes = (
        "Zeit;ATA00 CE001;ATA00 CE002;ATA00 CE003;RAA10 CT001;RAA10 CT002;RAA10 CT003;"
        "RAA30 CT001;RAA20 CT001;RAA20 CP001;RAA20 CF002;RAA20 CQ001\n"
        "10:00:00;1;2;3;4;5;6;7;8;9;10;11\n"
    ).encode("utf-8")
    required = (
        ("Zeit", "time", "Timestamp (HH:MM:SS)"),
        ("ATA00 CE001", "Total Current (A)", "Total electrical current in amperes"),
        ("ATA00 CE002", "Total Power (kW)", "Total electrical power in kilowatts"),
        ("ATA00 CE003", "Total Voltage (V)", "Total voltage in volts"),
        ("RAA10 CT001", "T_in_lye (°C)", "Inlet lye temperature in degrees Celsius"),
        ("RAA10 CT002", "T_out_lyeh2 (°C)", "Outlet lye temperature on H2 side in degrees Celsius"),
        ("RAA10 CT003", "T_out_lyeo2 (°C)", "Outlet lye temperature on O2 side in degrees Celsius"),
        ("RAA30 CT001", "Oxygen gas temperature after cooling (°C)", "O2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CT001", "H2 gas Temperature after cooling (°C)", "H2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CP001", "System Pressure (bar)", "System operating pressure in bar"),
        ("RAA20 CF002", "Hydrogen flow rate (Nm3/h)", "Hydrogen output flow rate in normal cubic meters per hour"),
        ("RAA20 CQ001", "H2 quality (%)", "Purity/quality of hydrogen output in percent"),
    )
    map_bytes = ("original_column,cleaned_column,description\n" + "".join(
        f'"{source}","{label}","{description}"\n'
        for source, label, description in required
    )).encode("utf-8")
    raw_path.write_bytes(raw_bytes)
    map_path.write_bytes(map_bytes)
    raw = load_raw_file(
        raw_path, expected_filename=raw_path.name, expected_size_bytes=len(raw_bytes),
        expected_publisher_md5=hashlib.md5(raw_bytes).hexdigest(),
        expected_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
    mapping = load_column_descriptions(
        map_path, expected_filename=map_path.name, expected_size_bytes=len(map_bytes),
        expected_publisher_md5=hashlib.md5(map_bytes).hexdigest(),
        expected_sha256=hashlib.sha256(map_bytes).hexdigest(),
    )
    block = project_source_observations(raw, mapping)

    def rejected(call):
        try:
            call()
        except (TypeError, ValueError):
            return True
        return False

    direct_raw = SourceTokenTable(
        header=raw.header, rows=raw.rows, preamble=raw.preamble, raw_bytes=raw.raw_bytes,
        source_filename=raw.source_filename, source_size_bytes=raw.source_size_bytes,
        publisher_md5=raw.publisher_md5, source_sha256=raw.source_sha256,
        _source_path=raw._source_path, _header_row=raw._header_row,
    )
    replaced_raw = dataclasses.replace(raw, rows=(("forged",),))
    direct_map = PEACEColumnDescriptionMap(
        entries=mapping.entries, raw_bytes=mapping.raw_bytes,
        source_filename=mapping.source_filename, source_size_bytes=mapping.source_size_bytes,
        publisher_md5=mapping.publisher_md5, source_sha256=mapping.source_sha256,
        _source_path=mapping._source_path,
    )
    replaced_map = dataclasses.replace(mapping, entries=())
    direct_block = PEACEObservationBlock(**{
        item.name: getattr(block, item.name)
        for item in dataclasses.fields(block)
        if item.name != "_issuer_token"
    })
    replaced_block = dataclasses.replace(block, source_row_indices=(99,))
    mutated_block = dataclasses.replace(block)
    object.__setattr__(mutated_block, "hydrogen_quality", block.hydrogen_flow)
    rejects = (
        rejected(direct_raw.require_current),
        rejected(replaced_raw.require_current),
        rejected(direct_map.require_current),
        rejected(replaced_map.require_current),
        rejected(direct_block.require_current),
        rejected(replaced_block.require_current),
        rejected(mutated_block.require_current),
    )
    assert all(rejects)
    return ValidationOutcome(True, {
        "direct_or_modified_wrappers_rejected": sum(rejects),
        "forgery_attempts": len(rejects),
    }, (
        "Synthetic forgery checks only; no ignored source files are read.",
        "Source bytes and publisher labels are reconstructed without physical interpretation.",
    ))


def validate_synthetic_unit_normalization(*, work_directory, **parameters):
    del parameters
    import dataclasses
    import hashlib
    from pathlib import Path

    from h2physics.data.peace_alkaline import (
        PEACESIObservationBlock,
        load_column_descriptions,
        load_raw_file,
        normalize_unambiguous_channels,
        project_source_observations,
    )

    directory = Path(work_directory)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / "experiment_1_raw.csv"
    map_path = directory / "column_descriptions.csv"
    raw_bytes = (
        "Zeit;ATA00 CE001;ATA00 CE002;ATA00 CE003;RAA10 CT001;RAA10 CT002;RAA10 CT003;"
        "RAA30 CT001;RAA20 CT001;RAA20 CP001;RAA20 CF002;RAA20 CQ001\n"
        "10:00:00;12,5;4,2;3,8;21,0;22,0;23,0;19,0;20,0;2,03;0,02314815;0,78\n"
    ).encode("utf-8")
    rows = (
        ("Zeit", "time", "Timestamp (HH:MM:SS)"),
        ("ATA00 CE001", "Total Current (A)", "Total electrical current in amperes"),
        ("ATA00 CE002", "Total Power (kW)", "Total electrical power in kilowatts"),
        ("ATA00 CE003", "Total Voltage (V)", "Total voltage in volts"),
        ("RAA10 CT001", "T_in_lye (°C)", "Inlet lye temperature in degrees Celsius"),
        ("RAA10 CT002", "T_out_lyeh2 (°C)", "Outlet lye temperature on H2 side in degrees Celsius"),
        ("RAA10 CT003", "T_out_lyeo2 (°C)", "Outlet lye temperature on O2 side in degrees Celsius"),
        ("RAA30 CT001", "Oxygen gas temperature after cooling (°C)", "O2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CT001", "H2 gas Temperature after cooling (°C)", "H2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CP001", "System Pressure (bar)", "System operating pressure in bar"),
        ("RAA20 CF002", "Hydrogen flow rate (Nm3/h)", "Hydrogen output flow rate in normal cubic meters per hour"),
        ("RAA20 CQ001", "H2 quality (%)", "Purity/quality of hydrogen output in percent"),
    )
    map_bytes = ("original_column,cleaned_column,description\n" + "".join(
        f'"{source}","{label}","{description}"\n' for source, label, description in rows
    )).encode("utf-8")
    raw_path.write_bytes(raw_bytes)
    map_path.write_bytes(map_bytes)
    raw = load_raw_file(
        raw_path, expected_filename=raw_path.name, expected_size_bytes=len(raw_bytes),
        expected_publisher_md5=hashlib.md5(raw_bytes).hexdigest(),
        expected_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
    description_map = load_column_descriptions(
        map_path, expected_filename=map_path.name, expected_size_bytes=len(map_bytes),
        expected_publisher_md5=hashlib.md5(map_bytes).hexdigest(),
        expected_sha256=hashlib.sha256(map_bytes).hexdigest(),
    )
    source = project_source_observations(raw, description_map)
    normalized = normalize_unambiguous_channels(source)
    assert normalized.total_current.values_si == (12.5,)
    assert normalized.total_current.si_unit == "A"
    assert normalized.total_power.values_si == (4200.0,)
    assert normalized.total_power.si_unit == "W"
    assert normalized.total_voltage.values_si == (3.8,)
    assert normalized.temperatures[0].values_si == (294.15,)
    assert normalized.reported_pressure.values_si == (203000.0,)
    assert normalized.reported_pressure.quantity == "reported_pressure"
    assert normalized.source.total_power.values == ("4,2",)
    assert normalized.raw_only_channels == (
        source.time, source.hydrogen_flow, source.hydrogen_quality,
    )
    normalized.require_current()
    changed_series = dataclasses.replace(normalized.total_power, values_si=(1.0,))
    forged = dataclasses.replace(normalized, total_power=changed_series)
    direct = PEACESIObservationBlock(
        source=normalized.source,
        total_current=normalized.total_current,
        total_power=normalized.total_power,
        total_voltage=normalized.total_voltage,
        temperatures=normalized.temperatures,
        reported_pressure=normalized.reported_pressure,
    )
    for invalid in (forged, direct):
        try:
            invalid.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("forged normalized view was accepted")
    return ValidationOutcome(True, {
        "converted_channels": 9,
        "raw_only_channels": len(normalized.raw_only_channels),
        "source_tokens_retained": True,
        "reported_pressure_basis_unresolved": True,
        "direct_or_replaced_si_views_rejected": True,
    }, (
        "Synthetic unit normalization only; no ignored publisher files are opened.",
        "Normal-volume basis, H2 quality basis, calibration and cell/stack interpretation remain unresolved.",
    ))


def validate_synthetic_stack_model_bridge(*, work_directory, **parameters):
    del parameters
    import hashlib
    from pathlib import Path

    from h2physics.adapters.peace_alkaline_model import bind_peace_alkaline_electrolysis_profile
    from h2physics.data.peace_alkaline import (
        load_column_descriptions, load_raw_file, normalize_unambiguous_channels,
        project_source_observations,
    )
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    directory = Path(work_directory)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path, map_path = directory / "experiment_1_raw.csv", directory / "column_descriptions.csv"
    payload = (
        "Zeit;ATA00 CE001;ATA00 CE002;ATA00 CE003;RAA10 CT001;RAA10 CT002;RAA10 CT003;"
        "RAA30 CT001;RAA20 CT001;RAA20 CP001;RAA20 CF002;RAA20 CQ001\n"
        "10:00:00;12,5;4,2;3,8;21,0;22,0;23,0;19,0;20,0;2,03;0,02314815;0,78\n"
        "10:00:01;12,6;4,3;3,9;21,1;22,1;23,1;19,1;20,1;2,04;;0,79\n"
    ).encode("utf-8")
    descriptions = (
        ("Zeit", "time", "Timestamp (HH:MM:SS)"),
        ("ATA00 CE001", "Total Current (A)", "Total electrical current in amperes"),
        ("ATA00 CE002", "Total Power (kW)", "Total electrical power in kilowatts"),
        ("ATA00 CE003", "Total Voltage (V)", "Total voltage in volts"),
        ("RAA10 CT001", "T_in_lye (°C)", "Inlet lye temperature in degrees Celsius"),
        ("RAA10 CT002", "T_out_lyeh2 (°C)", "Outlet lye temperature on H2 side in degrees Celsius"),
        ("RAA10 CT003", "T_out_lyeo2 (°C)", "Outlet lye temperature on O2 side in degrees Celsius"),
        ("RAA30 CT001", "Oxygen gas temperature after cooling (°C)", "O2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CT001", "H2 gas Temperature after cooling (°C)", "H2 gas temperature after cooling stage in degrees Celsius"),
        ("RAA20 CP001", "System Pressure (bar)", "System operating pressure in bar"),
        ("RAA20 CF002", "Hydrogen flow rate (Nm3/h)", "Hydrogen output flow rate in normal cubic meters per hour"),
        ("RAA20 CQ001", "H2 quality (%)", "Purity/quality of hydrogen output in percent"),
    )
    map_bytes = ("original_column,cleaned_column,description\n" + "".join(
        f'"{source}","{label}","{description}"\n' for source, label, description in descriptions
    )).encode("utf-8")
    raw_path.write_bytes(payload)
    map_path.write_bytes(map_bytes)
    raw = load_raw_file(raw_path, expected_filename=raw_path.name, expected_size_bytes=len(payload),
                        expected_publisher_md5=hashlib.md5(payload).hexdigest(),
                        expected_sha256=hashlib.sha256(payload).hexdigest())
    mapping = load_column_descriptions(map_path, expected_filename=map_path.name,
                                       expected_size_bytes=len(map_bytes),
                                       expected_publisher_md5=hashlib.md5(map_bytes).hexdigest(),
                                       expected_sha256=hashlib.sha256(map_bytes).hexdigest())
    source = normalize_unambiguous_channels(project_source_observations(raw, mapping))
    profile = bind_peace_alkaline_electrolysis_profile(
        source, temperature_channel_id="RAA10 CT002",
        electrical_scope_evidence_id="synthetic-stack-voltage-current-mapping",
        temperature_mapping_evidence_id="synthetic-outlet-lye-temperature-as-model-input",
    )
    stack = HydrogenStack(
        StackGeometry(series_cells=3, active_area_m2=0.01, hydrogen_molar_mass_kg_mol=0.00201588),
        lambda _temperature: ReactionEnergy(237000., 286000., "synthetic-reference", "liquid"),
        {},
    )
    trace = profile.evaluate(stack)
    trace.require_current()
    points = trace.points
    assert tuple(point.row_index for point in points) == (0,)
    assert points[0].time_token == "10:00:00"
    assert points[0].temperature_k == 295.15
    assert points[0].current_a == 12.5
    assert points[0].measured_voltage_v == 3.8
    assert len(profile.omitted_rows) == 1 and profile.omitted_rows[0][0] == 1
    assert len(trace.source_sha256) == 64 and len(trace.description_sha256) == 64
    return ValidationOutcome(True, {
        "modelled_source_rows": len(points),
        "omitted_missing_channel_rows": len(profile.omitted_rows),
        "source_bound_current_voltage_temperature": True,
        "hydrogen_flow_conversion_performed": False,
    }, (
        "Synthetic model-input bridge only; no publisher file or physical model validation is included.",
        "Caller-declared scope is required; actual cell/stack meanings, calibration, pressure state and normal-volume basis remain unresolved.",
    ))
