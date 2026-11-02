"""Deferred synthetic source-reader contract for the PEM ripple archive."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (ValidationCase(
        identifier="pem-ripple-streaming-reader-source-integrity",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_synthetic_reader_contract",
        invariants=(
            "pinned ZIP bytes and per-member SHA-256 issue immutable measured arrays",
            "IV current and voltage retain source A/V values and sweep step indices",
            "continuous timestamps preserve strict millisecond offsets and missing-time gaps",
            "naive timestamps receive no inferred timezone and no interpolation is applied",
            "reported fitted values remain distinguished from measured channels",
            "changed archive bytes and reconstructed result arrays fail freshness checks",
            "synthetic parser coverage establishes no physical-model validation",
        ),
    ),)


def validate_synthetic_reader_contract(*, work_directory, **parameters):
    del parameters
    import csv
    import hashlib
    import io
    import zipfile
    from dataclasses import replace
    from pathlib import Path

    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.data.pem_ripple import (
        PemRippleArchive,
        _load_archive,
        load_pem_ripple_continuous_trace,
        load_pem_ripple_fit_table,
        load_pem_ripple_iv_curve,
    )

    root = Path(work_directory)
    root.mkdir(parents=True, exist_ok=True)
    archive_path = root / "synthetic-pem-ripple.zip"
    prefix = "PEM_ripple_degradation_data/"
    fit = io.StringIO(newline="")
    writer = csv.writer(fit, lineterminator="\n")
    writer.writerow(("PEM", "Cycle", "R_mem", "alpha", "i_0", "I_lim", "RMSE"))
    for cell_number in range(1, 5):
        for cycle in ("Initial", *(f"C{i}" for i in range(1, 9))):
            writer.writerow((f"PEM{cell_number}", cycle, 0.1, 0.4, 0.00001, 10.0, 0.002))

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive_file:
        archive_file.writestr(
            prefix + "IV_curves/PEM1/PEM1_Initial.csv",
            "current_A,voltage_V,step_index\n0.0,0.0,0\n2.0,1.8,1\n",
        )
        archive_file.writestr(
            prefix + "Continuous_voltage/PEM1_continuous_voltage.csv",
            "timestamp,current_A,voltage_V\n"
            "2024-10-24 21:11:11.301,2.0,1.8\n"
            "2024-10-24 21:11:12.308,2.1,1.81\n"
            "2024-10-24 21:11:16.305,2.0,1.8\n",
        )
        archive_file.writestr(prefix + "Fitted_parameters.csv", fit.getvalue())
    archive_size = archive_path.stat().st_size
    archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    bundle = _load_archive(archive_path, archive_size, archive_sha)
    if not isinstance(bundle, PemRippleArchive):
        raise AssertionError("Synthetic source archive did not receive a typed handle")

    iv = load_pem_ripple_iv_curve(bundle, cell_id="PEM1", cycle="Initial")
    trace = load_pem_ripple_continuous_trace(bundle, cell_id="PEM1")
    fits = load_pem_ripple_fit_table(bundle)
    if (not np.array_equal(iv.current_a, (0.0, 2.0))
            or not np.array_equal(iv.voltage_v, (0.0, 1.8))
            or not np.array_equal(iv.step_index, (0, 1))):
        raise AssertionError("Source IV values changed during parsing")
    if tuple(iv.iter_source_rows()) != (("0.0", "0.0", "0"), ("2.0", "1.8", "1")):
        raise AssertionError("Exact IV source tokens were not retained for streaming")
    if trace.timestamp_origin_token != "2024-10-24 21:11:11.301":
        raise AssertionError("Source timestamp origin token was not retained")
    if not np.allclose(trace.interval_s, (1.007, 3.997), rtol=0., atol=1.e-12):
        raise AssertionError("Continuous clock gap was changed or filled")
    continuous_tokens = tuple(trace.iter_source_rows())
    if (len(continuous_tokens) != 3
            or continuous_tokens[0] != ("2024-10-24 21:11:11.301", "2.0", "1.8")):
        raise AssertionError("Exact continuous timestamp/value tokens were not retained")
    if trace.timezone_status != "timezone not declared; source timestamps are naive":
        raise AssertionError("A timezone was invented for naive source timestamps")
    if len(fits.records) != 36 or fits.records[0].fit_rmse_v != 0.002:
        raise AssertionError("Publisher-reported derived parameter rows were not retained")

    try:
        replace(trace, current_a=np.array((9., 9., 9.)))
    except ValueError:
        forged_projection_rejected = True
    else:
        forged_projection_rejected = False
    if not forged_projection_rejected:
        raise AssertionError("A modified trace inherited source issuance")

    with archive_path.open("ab") as changed:
        changed.write(b"changed")
    try:
        trace.require_current()
    except ValueError:
        changed_source_rejected = True
    else:
        changed_source_rejected = False
    if not changed_source_rejected:
        raise AssertionError("A trace remained current after its archive bytes changed")

    return ValidationOutcome(True, {
        "synthetic_iv_rows": len(iv.current_a),
        "synthetic_continuous_rows": len(trace.current_a),
        "preserved_interval_s": tuple(float(value) for value in trace.interval_s),
        "reported_fit_rows": len(fits.records),
        "modified_projection_rejected": forged_projection_rejected,
        "changed_archive_rejected": changed_source_rejected,
    }, (
        "Synthetic source-reader contract only; no publisher measurements or models were evaluated.",
        "No calibration, timezone, test-cell geometry or missing experiment condition is inferred.",
    ))
