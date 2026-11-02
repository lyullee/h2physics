"""Synthetic source-bound parser contracts for the cryogenic MOF dataset."""

from hashlib import md5, sha256

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="cryo-mof-isotherm-source-bound-reader",
            profile="source-data-ingestion",
            entrypoint=__name__ + ":validate_source_bound_reader",
            invariants=(
                "each direction remains aligned to original row identifiers and raw tokens",
                "20 K normalized pressure and reference gas volume remain distinct from absolute pressure and uptake",
                "77/87 K reported bar coordinates do not acquire an absolute pressure basis",
                "missing branch cells remain missing without interpolation or row deletion",
                "only the pinned DOI/version/Etalab attachment with matching publisher and receipt hashes is admitted",
                "loaded observations reject forged construction and changed source bytes",
                "no time coordinate, excess-to-absolute conversion, or model validation is inferred",
            ),
        ),
    )


def validate_source_bound_reader(*, work_directory):
    from dataclasses import replace
    from hashlib import sha256 as sha256_file
    from pathlib import Path

    from h2physics.data.cryo_mof import CryoMOFIsothermTable, load_cryo_mof_isotherm
    from h2physics.data.models import Dataset, RemoteFile

    root = Path(work_directory)
    root.mkdir(parents=True, exist_ok=True)
    examples = (
        (
            "H2.20K--MIL-100(Fe).csv",
            "Relative pressure adsorption (p/p) ,Quantity Adsorbed (cm3 g-1 STP) ,"
            "Relative pressure desorption (p/p) ,Quantity Desorbed (cm3 g-1 STP)\n"
            "0.25,10.0,0.75,\n0.5,20.0,0.6,18.0\n",
            "normalized_pressure", 0.25, "reference_specific_volume", 0.01,
            "0.25",
        ),
        (
            "H2.77K--MIL-100(Fe).csv",
            "Relative pressure adsorption (bar) ,Quantity Adsorbed (mmol/g) ,"
            "Relative pressure desorption (bar) ,Quantity Desorbed (mmol/g)\n"
            "0.2,-0.01,0.8,4.0\n",
            "reported_pressure", 20000.0, "specific_amount", -0.01,
            "0.2",
        ),
    )
    loaded = []
    for (filename, source, pressure_quantity, expected_pressure, uptake_quantity,
         expected_uptake, expected_pressure_token) in examples:
        data = source.encode("utf-8")
        path = root / filename
        path.write_bytes(data)
        remote = RemoteFile(
            filename, "https://example.org/" + filename, len(data),
            "md5", md5(data, usedforsecurity=False).hexdigest(),
        )
        metadata = b"synthetic source receipt"
        dataset = Dataset(
            key="cryo-mof-dormancy", title="Synthetic cryogenic adsorption fixture",
            doi="10.57745/FCV2R0", version="1.1", authors=("synthetic fixture",),
            license_id="etalab-2.0", license_url="https://spdx.org/licenses/etalab-2.0.html",
            metadata_url="https://example.org/metadata", metadata_sha256=sha256(metadata).hexdigest(),
            origin="measured", families=("adsorption",), files=(remote,), metadata_bytes=metadata,
        )
        table = load_cryo_mof_isotherm(
            path, dataset=dataset, expected_sha256=sha256_file(data).hexdigest())
        assert table.require_current() is table
        assert table.pressure_quantity == pressure_quantity
        assert table.pressure_basis_id.endswith("unresolved")
        assert table.uptake_quantity == uptake_quantity
        assert table.branch("adsorption")[0].pressure_value_si == expected_pressure
        assert table.branch("adsorption")[0].uptake_value_si == expected_uptake
        assert table.branch("adsorption")[0].source_row == 2
        assert table.branch("adsorption")[0].pressure_source_token == expected_pressure_token
        direct_rejected = False
        try:
            replace(table)
        except TypeError:
            direct_rejected = True
        assert direct_rejected
        wrong_digest_rejected = False
        try:
            load_cryo_mof_isotherm(path, dataset=dataset, expected_sha256="0" * 64)
        except ValueError:
            wrong_digest_rejected = True
        assert wrong_digest_rejected
        loaded.append((path, table, data))

    first = loaded[0][1]
    assert first.branch("adsorption")[1].uptake_value_si == 0.02
    assert first.branch("desorption")[0].uptake_value_si is None
    assert first.branch("desorption")[1].source_row == 3
    projected = first.observation_table("desorption")
    assert len(projected.values) == 2
    assert not projected.valid[0, 1] and projected.valid[1, 1]
    assert projected.variables[0].quantity == "normalized_pressure"
    assert projected.variables[1].basis_id == first.uptake_basis_id
    assert len(set(projected.experiment_ids)) == 1
    assert dict(projected.context)["basis_qualified"] == "false"
    original_pressure = first.observations[0].pressure_value_si
    object.__setattr__(first.observations[0], "pressure_value_si", -123.0)
    nested_mutation_rejected = False
    try:
        first.require_current()
    except ValueError:
        nested_mutation_rejected = True
    object.__setattr__(first.observations[0], "pressure_value_si", original_pressure)
    assert nested_mutation_rejected
    mutated_path, _, original = loaded[1]
    mutated_path.write_bytes(original + b"\n")
    stale_rejected = False
    try:
        loaded[1][1].require_current()
    except ValueError:
        stale_rejected = True
    assert stale_rejected

    forged_rejected = False
    try:
        CryoMOFIsothermTable(*([None] * 19))
    except (TypeError, ValueError):
        forged_rejected = True
    assert forged_rejected
    return ValidationOutcome(True, {
        "synthetic_regimes": len(loaded),
        "source_order_and_tokens_retained": True,
        "missing_branch_value_preserved": True,
        "wrong_receipt_hash_rejected": True,
        "nested_observation_mutation_rejected": nested_mutation_rejected,
        "source_mutation_rejected": stale_rejected,
        "forged_table_rejected": forged_rejected,
    }, (
        "Synthetic parser and receipt contracts only; no measured source file is opened by this case.",
        "Pressure basis, 20 K reference-gas state and uptake amount convention remain unresolved.",
        "Adsorption observations are not time histories and do not validate a storage vessel or dormancy model.",
    ))
