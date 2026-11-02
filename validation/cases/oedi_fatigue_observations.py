"""Deferred provenance/schema checks for the OEDI 4130X fatigue workbook."""

import os
import tomllib
from dataclasses import fields, replace
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def _source_parameters():
    root = os.environ.get("H2_DATA_OEDI_FATIGUE_ROOT")
    return {} if not root else {"source_path": root}


def _source_workbook(parameters):
    source = Path(parameters.get("source_path", "data/raw/oedi-h2-materials"))
    workbook = source / "low-alloy-tempered-martensite-1211san11fat.xlsx"
    if not workbook.is_file():
        raise FileNotFoundError(
            "Stage the checksum-pinned OEDI workbook and set H2_DATA_OEDI_FATIGUE_ROOT "
            "to its directory, or pass source_path in the cluster case parameters"
        )
    return workbook


def cases():
    return (
        ValidationCase(
            identifier="oedi-4130x-fatigue-provenance",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_oedi_fatigue_provenance",
            parameters=_source_parameters(),
            invariants=(
                "pinned workbook checksum and source row identities are preserved",
                "staged workbook SHA-256/MD5/size and license agree with the acquired source receipt",
                "receipt dataset identity, file acquisition state and rights/validation flags are explicit",
                "five source series retain measurement units and test metadata",
                "the identical-file 4.5 MPa catalog discrepancy is retained while primary evidence admits 45 MPa",
                "direct dataset/series construction rejects detached source hashes, schema and test conditions",
                "only the checksum-validating workbook reader can issue source-bound observed values",
                "no fatigue law is fitted and no vessel-life claim is inferred",
            ),
        ),
        ValidationCase(
            identifier="oedi-helpr-rate-comparison-diagnostic",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":compare_oedi_rates_with_native_helpr",
            parameters=_source_parameters(),
            invariants=(
                "the admitted 45 MPa workbook condition is passed to the selected native HELPR model",
                "measured rows are compared without fitting any coefficients",
                "source rows, data conditions and returned native predictions remain identifiable",
                "saved archive reopens without pickle and preserves aligned provenance/diagnostic fields",
                "native raw scalar returns align with accepted m/cycle rates and source-row IDs",
                "row point views preserve source/measured/native values and reject inconsistent rate ratios",
                "reported point/positive-count/log-RMSE metrics equal the archived arrays and scalars",
                "returned rate ratios, log-ratios and RMSE are internally consistent",
                "comparison outputs reject changed source rows, measured values or native condition bindings",
                "post-return freshness checks bind workbook source metadata, native owner and result arrays",
                "comparison row identities are frozen as unique nonempty strings",
                "the caller records the explicit gas-composition evidence or assumption because source purity is absent",
                "diagnostic receipt preserves native/model/source identity, failure row/stage and omits exception text without injecting a native failure",
                "diagnostic constructor rejects completed rows that are not the ordered source prefix before the failed row",
                "failure receipt resolves failed-row delta-K and observed growth to the source series",
                "rate residuals are diagnostic and do not imply vessel-life or model qualification",
            ),
        ),
    )


def validate_oedi_fatigue_provenance(*, work_directory, **parameters):
    from h2physics.data.oedi_fatigue import (
        FatigueGrowthSeries,
        OediFatigueDataset,
        load_oedi_4130x_fatigue,
    )

    workbook = _source_workbook(parameters)
    dataset = load_oedi_4130x_fatigue(workbook)
    receipt_path = Path(__file__).resolve().parents[2] / "research/data/oedi-hydrogen-materials.toml"
    receipt = tomllib.loads(receipt_path.read_text(encoding="utf-8"))
    file_receipt = receipt["files"][0]
    assert receipt["key"] == "oedi-hydrogen-materials"
    assert receipt["identifier"] == "https://data.openei.org/submissions/277"
    assert receipt["rights_permitted"] is True
    assert receipt["validation_qualified"] is False
    assert receipt["listed_xlsx_count"] == 8
    assert receipt["acquired_xlsx_count"] == 1
    assert workbook.name == file_receipt["name"]
    assert file_receipt["status"] == "acquired_source_condition_admitted_45_MPa_metadata_discrepancy_retained"
    assert file_receipt["relative_path"] == (
        "oedi-h2-materials/low-alloy-tempered-martensite-1211san11fat.xlsx"
    )
    assert workbook.stat().st_size == file_receipt["size_bytes"]
    assert dataset.source_sha256 == file_receipt["sha256"]
    assert dataset.source_md5 == file_receipt["md5"]
    assert dataset.source_url == file_receipt["url"]
    assert dataset.license_id == receipt["license_id"]
    assert dataset.license_url == receipt["license_url"]
    source_series = dataset.series[0]
    altered_values = np.array(source_series.observations.values, copy=True)
    altered_values[0, 0] += 1.0
    altered_observations = replace(source_series.observations, values=altered_values)
    direct_series_fields = {
        item.name: (altered_observations if item.name == "observations"
                    else getattr(source_series, item.name))
        for item in fields(FatigueGrowthSeries)
        if item.init and item.name != "_issuer_token"
    }
    direct_series_rejected = False
    try:
        FatigueGrowthSeries(**direct_series_fields)
    except ValueError:
        direct_series_rejected = True
    if not direct_series_rejected:
        raise AssertionError("Directly constructed source-labelled fatigue values were admitted")
    direct_dataset_fields = {
        item.name: getattr(dataset, item.name)
        for item in fields(OediFatigueDataset)
        if item.init and item.name != "_issuer_token"
    }
    direct_dataset_rejected = False
    try:
        OediFatigueDataset(**direct_dataset_fields)
    except ValueError:
        direct_dataset_rejected = True
    if not direct_dataset_rejected:
        raise AssertionError("A manually assembled OEDI receipt bypassed the verified file loader")
    bad_pressure_series = replace(dataset.series[0], pressure_mpa=4.5)
    bad_hash_context = dict(dataset.series[0].observations.context)
    bad_hash_context["source_sha256"] = "0" * 64
    bad_hash_table = replace(
        dataset.series[0].observations, context=tuple(bad_hash_context.items())
    )
    invalid_bindings = (
        {"series": (bad_pressure_series, *dataset.series[1:])},
        {"series": tuple(reversed(dataset.series))},
    )
    for changes in invalid_bindings:
        try:
            replace(dataset, **changes)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Detached source series binding was admitted: {tuple(changes)}")
    try:
        replace(dataset.series[0], observations=bad_hash_table)
    except ValueError:
        pass
    else:
        raise AssertionError("Observation rows with a changed source hash were admitted")
    assert dataset.source_sha256
    assert dataset.source_md5
    assert dataset.license_id == "CC-BY-4.0"
    assert dataset.source_url.endswith("/1211san11fat.xlsx")
    assert dataset.license_url == "https://creativecommons.org/licenses/by/4.0/"
    assert dataset.related_condition_source_url.startswith("https://hymatbase.stfc.ac.uk/")
    assert dataset.material == "4130X"
    assert len(dataset.series) == 5
    assert [series.environment for series in dataset.series] == ["H2"] * 4 + ["air"]
    assert [series.pressure_mpa for series in dataset.series] == [45.0] * 4 + [0.1]
    assert dataset.condition_identity_admitted
    assert "4.5 MPa" in dataset.condition_metadata_discrepancy
    assert "45 MPa" in dataset.condition_resolution
    assert dataset.condition_authority_url.startswith("https://www.sandia.gov/")

    metrics = {
        "series_count": len(dataset.series),
        "direct_forged_values_rejected": direct_series_rejected,
        "manual_dataset_assembly_rejected": direct_dataset_rejected,
    }
    for series in dataset.series:
        table = series.observations
        delta_k, delta_k_valid = table.column("stress_intensity_factor_range")
        growth, growth_valid = table.column("crack_growth_rate")
        assert np.all(delta_k_valid & growth_valid)
        assert np.all(delta_k > 0.0) and np.all(growth > 0.0)
        assert table.origins == ("measured", "measured")
        metrics[f"{series.series_id}_rows"] = len(table.row_ids)

    output = Path(work_directory)
    output.mkdir(parents=True, exist_ok=True)
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Source/schema provenance only. The identical-file 4.5 MPa catalog metadata conflict "
            "is retained while 45 MPa is admitted for the workbook observations; no calibration, "
            "fatigue validation, or vessel-life claim is admitted.",
        ),
    )


def compare_oedi_rates_with_native_helpr(*, work_directory, **parameters):
    import inspect

    from helpr.physics.environment import EnvironmentSpecification

    from h2physics.adapters import (
        OediFatigueComparisonError,
        OediFatiguePoint,
        compare_oedi_fatigue_series,
    )
    from h2physics.adapters.fracture_fatigue import (
        HELPR_REVISION,
        HELPR_VERSION,
        HelprFatigueLaw,
        HelprLawSelection,
        HydrogenCrackEnvironment,
    )
    from h2physics.core import Origin
    from h2physics.data.oedi_fatigue import load_oedi_4130x_fatigue

    workbook = _source_workbook(parameters)
    dataset = load_oedi_4130x_fatigue(workbook)
    reference_pressure_mpa = inspect.signature(
        EnvironmentSpecification
    ).parameters["reference_pressure"].default
    law = HelprFatigueLaw(
        HelprLawSelection(
            "g_202006",
            "selected-native-HELPR-H2-curve-diagnostic-no-fit",
            reference_pressure_pa=float(reference_pressure_mpa) * 1.0e6,
        )
    )
    pressure_mpa = 45.0
    temperature_k = 298.15
    hydrogen_fraction = 1.0
    native_environment = EnvironmentSpecification(
        pressure_mpa,
        pressure_mpa,
        temperature_k,
        hydrogen_fraction,
        reference_pressure=reference_pressure_mpa,
    )
    environment = HydrogenCrackEnvironment(
        pressure_mpa * 1.0e6,
        pressure_mpa * 1.0e6,
        temperature_k,
        hydrogen_fraction,
        float(native_environment.fugacity) * 1.0e6,
        "HELPR-native-Abel-Noble",
        "native-pressure-and-workbook-RT-metadata-reconstruction",
        Origin.RECONSTRUCTED,
    )

    output = Path(work_directory)
    output.mkdir(parents=True, exist_ok=True)
    metrics = {"hydrogen_series_count": 4}
    limitations = [
        "Diagnostic point comparison only; no model acceptance threshold or coefficient fit is applied.",
        "The workbook reports RT; 298.15 K uses the associated 25 C record and is reconstructed.",
        "Test gas purity is not an exact measured mole fraction; a pure-H2 native input is an explicit approximation.",
        "The HELPR point API does not accept the measured 1 Hz frequency as a constitutive input.",
        "Heat identity is incomplete and the comparison does not qualify vessel life or component geometry.",
    ]
    for series in dataset.series:
        if series.environment != "H2":
            continue
        result = compare_oedi_fatigue_series(
            dataset,
            series.series_id,
            law,
            environment,
            temperature_interpretation_id=(
                "Sandia 25 C associated record interpreted as 298.15 K; "
                "workbook RT label itself is not an exact temperature"
            ),
            gas_composition_interpretation_id=(
                "Explicit pure-H2 input approximation; source workbook does not report gas purity"
            ),
        )
        points = result.points
        assert result.require_current() is result
        issued_rows = result.source_row_ids
        object.__setattr__(result, "source_row_ids", tuple(reversed(issued_rows)))
        try:
            result.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("A post-return source-row replacement retained the comparison receipt")
        finally:
            object.__setattr__(result, "source_row_ids", issued_rows)
        assert result.require_current() is result
        assert len(points) == len(result.source_row_ids)
        for index, point in enumerate(points):
            assert type(point) is OediFatiguePoint
            assert point.dataset_source_id == dataset.series[0].observations.source_id
            assert point.dataset_source_sha256 == dataset.source_sha256
            assert point.dataset_source_url == dataset.source_url
            assert point.dataset_license_id == dataset.license_id
            assert point.series_id == series.series_id
            assert point.source_columns_one_based == series.source_columns
            assert point.source_row_id == result.source_row_ids[index]
            assert point.delta_k_pa_sqrt_m == result.delta_k_pa_sqrt_m[index]
            assert point.observed_growth_m_per_cycle == result.observed_growth_m_per_cycle[index]
            assert point.native_raw_return == result.native_raw_returns[index]
            assert point.predicted_growth_m_per_cycle == result.predicted_growth_m_per_cycle[index]
            assert point.rate_ratio == result.rate_ratio[index]
        first = points[0]
        try:
            replace(first, rate_ratio=first.rate_ratio * 1.01)
        except ValueError:
            pass
        else:
            raise AssertionError("A point with inconsistent observed/predicted ratio was admitted")
        diagnostic_error = OediFatigueComparisonError(
            "synthetic receipt-schema check; no native failure is injected",
            dataset=dataset,
            series=series,
            environment=environment,
            temperature_interpretation_id=result.temperature_interpretation_id,
            gas_composition_interpretation_id=result.gas_composition_interpretation_id,
            law=result.law,
            native_owner=result.native_owner,
            failure_row_id=result.source_row_ids[0],
            failure_stage="native_point_evaluation",
            cause=RuntimeError("synthetic cause omitted from serialized diagnostic"),
            completed=(),
        )
        failure_receipt = diagnostic_error.diagnostic_record()
        assert failure_receipt["dataset_source_sha256"] == dataset.source_sha256
        assert failure_receipt["series_id"] == series.series_id
        assert failure_receipt["native_model_name"] == result.law.selection.model_name
        assert failure_receipt["native_definition_sha256"] == result.native_owner.definition_sha256
        assert failure_receipt["failure_row_id"] == result.source_row_ids[0]
        assert failure_receipt["failure_delta_k_pa_sqrt_m"] == result.delta_k_pa_sqrt_m[0]
        assert failure_receipt["failure_observed_growth_m_per_cycle"] == (
            result.observed_growth_m_per_cycle[0]
        )
        assert failure_receipt["failure_stage"] == "native_point_evaluation"
        assert failure_receipt["failure_exception_type"] == "RuntimeError"
        assert failure_receipt["completed_row_ids"] == ()
        assert failure_receipt["completed_native_returns"] == ()
        assert "synthetic cause omitted" not in repr(failure_receipt)
        try:
            OediFatigueComparisonError(
                "invalid synthetic prefix",
                dataset=dataset,
                series=series,
                environment=environment,
                temperature_interpretation_id=result.temperature_interpretation_id,
                gas_composition_interpretation_id=result.gas_composition_interpretation_id,
                law=result.law,
                native_owner=result.native_owner,
                failure_row_id=result.source_row_ids[0],
                failure_stage="native_point_evaluation",
                cause=RuntimeError("synthetic cause"),
                completed=((
                    result.source_row_ids[0],
                    result.predicted_growth_m_per_cycle[0],
                    result.predicted_growth_m_per_cycle[0],
                ),),
            )
        except ValueError:
            pass
        else:
            raise AssertionError("A failed row overlapping the completed source prefix was accepted")
        try:
            compare_oedi_fatigue_series(
                dataset,
                series.series_id,
                law,
                environment,
                temperature_interpretation_id="source workbook RT mapped to reconstructed 298.15 K",
                gas_composition_interpretation_id="",  # missing declaration must fail before native calls
            )
        except ValueError:
            pass
        else:
            raise AssertionError("An undeclared gas-composition interpretation was accepted")
        corruptions = (
            {"source_row_ids": result.source_row_ids[::-1]},
            {"observed_growth_m_per_cycle": result.observed_growth_m_per_cycle * 1.01},
            {"native_raw_returns": tuple(0.0 for _ in result.native_raw_returns)},
            {"environment": replace(
                environment,
                minimum_pressure_pa=environment.minimum_pressure_pa * 1.01,
                maximum_pressure_pa=environment.maximum_pressure_pa * 1.01,
            )},
            {"environment": replace(environment, fugacity_basis_id="different-native-basis")},
            {"gas_composition_interpretation_id": ""},
        )
        for changes in corruptions:
            try:
                replace(result, **changes)
            except (TypeError, ValueError):
                continue
            raise AssertionError(f"Corrupted OEDI comparison binding was admitted: {tuple(changes)}")
        mutable_rows = list(result.source_row_ids)
        copied = replace(result, source_row_ids=mutable_rows)
        mutable_rows[0] = "mutated-after-construction"
        if copied.source_row_ids != result.source_row_ids:
            raise AssertionError("Comparison source-row identity changed after construction")
        archive = output / f"{series.series_id}_helpr_comparison.npz"
        np.savez_compressed(
            archive,
            source_row_ids=np.asarray(result.source_row_ids),
            source_sha256=np.asarray(dataset.source_sha256),
            source_url=np.asarray(dataset.source_url),
            data_publisher=np.asarray(dataset.publisher),
            data_license_id=np.asarray(dataset.license_id),
            data_license_url=np.asarray(dataset.license_url),
            series_id=np.asarray(series.series_id),
            source_temperature_label=np.asarray(series.temperature_label),
            source_columns_one_based=np.asarray(series.source_columns, dtype=np.int64),
            source_reference=np.asarray(series.reference),
            pressure_pa=np.asarray(environment.maximum_pressure_pa),
            minimum_pressure_pa=np.asarray(environment.minimum_pressure_pa),
            temperature_k=np.asarray(environment.temperature_k),
            temperature_interpretation_id=np.asarray(
                result.temperature_interpretation_id
            ),
            hydrogen_mole_fraction=np.asarray(environment.hydrogen_mole_fraction),
            hydrogen_fugacity_pa=np.asarray(environment.hydrogen_fugacity_pa),
            environment_evidence_id=np.asarray(environment.evidence_id),
            environment_origin=np.asarray(environment.origin.value),
            fugacity_basis_id=np.asarray(environment.fugacity_basis_id),
            source_test_gas_label=np.asarray(series.environment),
            source_test_pressure_mpa=np.asarray(series.pressure_mpa),
            gas_composition_interpretation_id=np.asarray(
                result.gas_composition_interpretation_id
            ),
            r_ratio=np.asarray(series.r_ratio),
            frequency_hz=np.asarray(series.frequency_hz),
            test_method=np.asarray(series.test_method),
            orientation=np.asarray(series.orientation),
            native_library=np.asarray("HELPR"),
            native_library_version=np.asarray(HELPR_VERSION),
            native_library_revision=np.asarray(HELPR_REVISION),
            native_model_name=np.asarray(result.law.selection.model_name),
            native_model_evidence_id=np.asarray(
                result.law.selection.model_evidence_id
            ),
            native_model_parameters=np.asarray(
                [
                    f"{name}={result.native_owner.arguments[name]!r}"
                    for name in sorted(result.native_owner.arguments)
                ]
            ),
            native_reference_pressure_pa=np.asarray(
                np.nan
                if result.law.selection.reference_pressure_pa is None
                else result.law.selection.reference_pressure_pa
            ),
            native_fugacity_compatibility_relative_budget=np.asarray(
                result.law.selection.fugacity_compatibility_relative_budget
            ),
            native_definition_sha256=np.asarray(
                result.native_owner.definition_sha256
            ),
            native_source_modules=np.asarray(sorted(result.law.source_sha256)),
            native_source_sha256=np.asarray(
                [result.law.source_sha256[name]
                 for name in sorted(result.law.source_sha256)]
            ),
            delta_k_pa_sqrt_m=result.delta_k_pa_sqrt_m,
            observed_growth_m_per_cycle=result.observed_growth_m_per_cycle,
            native_raw_returns=np.asarray(result.native_raw_returns, dtype=float),
            predicted_growth_m_per_cycle=result.predicted_growth_m_per_cycle,
            rate_ratio=result.rate_ratio,
            log10_rate_ratio=result.log10_rate_ratio,
            positive_prediction_count=np.asarray(
                np.count_nonzero(result.predicted_growth_m_per_cycle > 0)
            ),
            positive_prediction_log_rmse=np.asarray(
                np.nan
                if result.positive_prediction_log_rmse is None
                else result.positive_prediction_log_rmse
            ),
        )
        with np.load(archive, allow_pickle=False) as saved:
            expected_rows = np.asarray(result.source_row_ids)
            assert np.array_equal(saved["source_row_ids"], expected_rows)
            assert np.array_equal(saved["source_sha256"], np.asarray(dataset.source_sha256))
            assert saved["temperature_interpretation_id"].item() == (
                result.temperature_interpretation_id
            )
            assert saved["gas_composition_interpretation_id"].item() == (
                result.gas_composition_interpretation_id
            )
            assert float(saved["source_test_pressure_mpa"].item()) == series.pressure_mpa
            assert saved["source_test_gas_label"].item() == series.environment
            assert saved["fugacity_basis_id"].item() == environment.fugacity_basis_id
            assert saved["environment_evidence_id"].item() == environment.evidence_id
            assert saved["native_library_revision"].item() == HELPR_REVISION
            assert saved["native_definition_sha256"].item() == (
                result.native_owner.definition_sha256
            )
            for name in (
                "delta_k_pa_sqrt_m",
                "observed_growth_m_per_cycle",
                "native_raw_returns",
                "predicted_growth_m_per_cycle",
                "rate_ratio",
                "log10_rate_ratio",
            ):
                assert saved[name].shape == expected_rows.shape
                assert np.array_equal(
                    saved[name], getattr(result, name), equal_nan=True
                )
            assert np.array_equal(
                saved["native_raw_returns"],
                np.asarray(result.native_raw_returns, dtype=float),
            )
            archived_points = int(saved["source_row_ids"].size)
            archived_positive = int(saved["positive_prediction_count"].item())
            archived_log_rmse = float(
                saved["positive_prediction_log_rmse"].item()
            )
            expected_positive = int(
                np.count_nonzero(result.predicted_growth_m_per_cycle > 0)
            )
            assert archived_positive == expected_positive
            metrics[f"{series.series_id}_point_count"] = archived_points
            metrics[f"{series.series_id}_positive_prediction_count"] = archived_positive
        if result.positive_prediction_log_rmse is not None:
            assert np.isclose(
                archived_log_rmse,
                result.positive_prediction_log_rmse,
                rtol=0.0,
                atol=0.0,
            )
            metrics[f"{series.series_id}_positive_prediction_log_rmse"] = (
                archived_log_rmse
            )
        else:
            assert np.isnan(archived_log_rmse)

    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=tuple(limitations),
    )
