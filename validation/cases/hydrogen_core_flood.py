"""Deferred contract for source-bound hydrogen/nitrogen core-flood tables."""

import hashlib
import importlib
import math

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mendeley-hydrogen-core-flood-source-bound-kr-tables",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_ingest",
        parameters={
            "fixture_module": "validation.fixtures.hydrogen_core_flood",
            "fixture_builder": "build_hydrogen_core_flood_fixture",
        },
        invariants=(
            "publisher license and all four publisher attachment digests are pinned",
            "publisher snapshot and root listing bytes are pinned and resolved without HTTP access",
            "only exact publisher filenames and the exact Kr worksheet are admitted",
            "reported worksheet labels, row ordering, and native cell values are retained",
            "each retained worksheet row has a stable workbook and one-based source-row identity",
            "files changed after acquisition are rejected before spreadsheet parsing",
            "selection by exact source filename returns the associated experiment table",
            "no curve fit, relabeling, saturation normalization, or unit conversion occurs",
        ),
    ), ValidationCase(
        identifier="core-flood-branch-specific-relative-mobility",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_branch_adapter",
        invariants=(
            "gas species, hysteresis branch, and flowing relative phase stay distinct and source-bound",
            "exact caller-selected source headers must resolve uniquely and match declared field roles",
            "canonical Krg/Krw headers reject a conflicting relative phase while other header meanings remain caller-declared",
            "raw values, explicit unit factors, source worksheet rows, and row identities remain available",
            "saturation coordinates must be strictly monotone in original workbook order",
            "query points use piecewise-linear interpolation only within the observed saturation interval",
            "interpolated numerical quantities use tight floating-point tolerances while source identities and row IDs remain exact",
            "mobility is relative permeability divided by explicitly positive phase viscosity in Pa s",
            "percent and other non-unit coordinates require caller-supplied positive scale factors",
            "source mutation, ambiguous fields, mismatched phases, and extrapolation are rejected",
            "nitrogen primary drainage remains a nitrogen branch and cannot be relabeled as hydrogen",
        ),
    ), ValidationCase(
        identifier="core-flood-source-bound-power-law-curve-summary",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_power_law_fit",
        invariants=(
            "caller-supplied irreducible-water and residual-gas saturation endpoints are retained with evidence",
            "fit uses every source row from one immutable gas/branch/phase table with fixed endpoint saturations",
            "water and gas relative-permeability phases use their respective effective-saturation coordinates",
            "reported source row identities remain bound to fitted parameters and residual diagnostics",
            "queries outside the observed saturation interval and stale fit/source changes are rejected",
            "fit residuals are descriptive curve-compression errors, not independent physical validation",
        ),
    ))


def validate_ingest(*, work_directory, **parameters):
    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or not isinstance(builder_name, str) or not builder_name.isidentifier()):
        raise ValueError("Configure an offline core-flood source fixture explicitly")
    builder = getattr(importlib.import_module(module_name), builder_name, None)
    if not callable(builder):
        raise ValueError("Fixture must provide the pinned dataset receipt and staged workbooks")
    # The worker must use the staged publisher metadata. Fail if fixture
    # construction tries the live repository resolver or any HTTP helper.
    from unittest.mock import patch

    with patch(
        "h2physics.data.repositories.read_url",
        side_effect=AssertionError("Core-flood ingestion fixture attempted network access"),
    ):
        fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict) or set(fixture) != {"dataset", "directory"}:
        raise TypeError("Fixture must return exactly a Dataset receipt and workbook directory")

    from h2physics.data import load_hydrogen_core_flood

    source_receipt = fixture["dataset"]
    assert source_receipt.metadata_sha256 == (
        "dbbcb9e3e4b5e4e4a85d513b1111ea9fe7657005acb911d3c36885c01b775b8a"
    )
    assert len(source_receipt.supporting_metadata) == 1
    listing_url, listing_bytes = source_receipt.supporting_metadata[0]
    assert listing_url.startswith("https://data.mendeley.com/public-api/datasets/rfhf7wjydn/files?")
    assert hashlib.sha256(listing_bytes).hexdigest() == (
        "e91a03765634534500ab119b75544bda441c747198ec03a1afe914db1e919c72"
    )
    data = load_hydrogen_core_flood(fixture["directory"], dataset=fixture["dataset"])
    assert data.doi == "10.17632/rfhf7wjydn.1"
    assert len(data.tables) == 4
    assert tuple(table.filename for table in data.tables) == (
        "Imbibition_H2.xlsx", "Primary_drainage_H2.xlsx",
        "Primary_drainage_N2.xlsx", "Secondary_drainage_H2.xlsx",
    )
    assert all(table.worksheet == "Kr" and len(table.rows) >= 2 for table in data.tables)
    assert all(len(table.source_row_ids) == len(table.rows) for table in data.tables)
    assert all(table.source_row_ids[0].endswith("row-1") for table in data.tables)
    assert data.table("Primary_drainage_H2.xlsx") is data.tables[1]
    return ValidationOutcome(True, {
        "doi": data.doi, "license_id": data.license_id,
        "experiment_tables": len(data.tables),
        "native_headers_preserved": True,
        "publisher_metadata_resolved_offline": True,
        "fit_or_normalization_applied": False,
    }, (
        "This contract checks source integrity and worksheet preservation only.",
        "Table units and experimental interpretation require domain review before calibration.",
    ))


def validate_branch_adapter(*, work_directory, **parameters):
    from h2physics.adapters.core_flood_mobility import build_core_flood_branch
    from h2physics.data.hydrogen_core_flood import CoreFloodTable

    filename = "Primary_drainage_H2.xlsx"
    table = CoreFloodTable(
        filename=filename,
        source_url=("https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/"
                    "ce094687-9357-4234-8dc4-9fda3efa5199/file_downloaded"),
        sha256="60b94149b4f84b131fc1a70eac592dc741f22486cec1725ec7b904c4b56ec7ff",
        worksheet="Kr",
        rows=(
            ("Sw synthetic", "Krg synthetic"),
            (0.2, 0.05), (0.5, 0.3), (0.8, 0.8),
        ),
        source_row_ids=tuple(
            f"hydrogen-core-flood:{filename}:Kr:row-{row}" for row in range(1, 5)
        ),
    )
    branch = build_core_flood_branch(
        table, gas_id="H2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic water saturation",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic gas phase relative permeability",
        interpretation_evidence="synthetic explicit contract labels",
        viscosity_pa_s=0.001, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic declared input",
    )
    point = branch.evaluate(0.35)
    assert math.isclose(point.relative_permeability, 0.175, rel_tol=1e-14, abs_tol=1e-15)
    assert math.isclose(point.mobility_per_intrinsic_permeability, 175.0,
                        rel_tol=1e-14, abs_tol=1e-12)
    assert point.left_source_row_id.endswith("row-2")
    assert point.right_source_row_id.endswith("row-3")
    assert math.isclose(point.raw_left_saturation, 0.2, rel_tol=0., abs_tol=1e-15)
    assert branch.saturation_scale == 1.0
    assert branch.require_current() is branch and point.require_current() is point

    n2_filename = "Primary_drainage_N2.xlsx"
    n2_table = CoreFloodTable(
        filename=n2_filename,
        source_url=("https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/"
                    "83ab3ce9-5b2f-47af-a33b-fbc53a8929c4/file_downloaded"),
        sha256="ae2934256439f959f358c3dce468beaed9f6e98b8388934d26a36791fa047a3f",
        worksheet="Kr", rows=table.rows,
        source_row_ids=tuple(
            f"hydrogen-core-flood:{n2_filename}:Kr:row-{row}" for row in range(1, 5)
        ),
    )
    n2_branch = build_core_flood_branch(
        n2_table, gas_id="N2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic water saturation",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic nitrogen gas relative permeability",
        interpretation_evidence="synthetic explicit N2 record",
        viscosity_pa_s=0.000018, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic N2 input",
    )
    assert n2_branch.gas_id == "N2" and n2_branch.branch == "primary_drainage"

    def rejected(call, label):
        try:
            call()
        except (TypeError, ValueError):
            return
        raise AssertionError(f"Core-flood branch contract accepted {label}")

    rejected(lambda: branch.evaluate(0.1), "saturation extrapolation")
    rejected(lambda: build_core_flood_branch(
        table, gas_id="N2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic", interpretation_evidence="synthetic",
        viscosity_pa_s=0.001, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic",
    ), "relabeling the H2 workbook as N2")
    rejected(lambda: build_core_flood_branch(
        table, gas_id="H2", branch="primary_drainage", relative_phase="water",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="water_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic", interpretation_evidence="synthetic",
        viscosity_pa_s=0.001, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic",
    ), "binding canonical Krg to the water phase")
    rejected(lambda: build_core_flood_branch(
        table, gas_id="H2", branch="primary_drainage", relative_phase="gas",
        saturation_header="missing saturation", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic", interpretation_evidence="synthetic",
        viscosity_pa_s=0.001, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic",
    ), "a missing exact header")
    duplicate_header_table = CoreFloodTable(
        filename=table.filename, source_url=table.source_url, sha256=table.sha256,
        worksheet=table.worksheet,
        rows=(("Sw synthetic", "Krg synthetic", "Sw synthetic"),
              (0.2, 0.05, 0.2), (0.5, 0.3, 0.5), (0.8, 0.8, 0.8)),
        source_row_ids=table.source_row_ids,
    )
    rejected(lambda: build_core_flood_branch(
        duplicate_header_table, gas_id="H2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic", interpretation_evidence="synthetic",
        viscosity_pa_s=0.001, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic",
    ), "a repeated exact header")
    nonmonotone_table = CoreFloodTable(
        filename=table.filename, source_url=table.source_url, sha256=table.sha256,
        worksheet=table.worksheet,
        rows=(table.rows[0], table.rows[1], table.rows[3], table.rows[2]),
        source_row_ids=table.source_row_ids,
    )
    rejected(lambda: build_core_flood_branch(
        nonmonotone_table, gas_id="H2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic", interpretation_evidence="synthetic",
        viscosity_pa_s=0.001, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic",
    ), "nonmonotone saturation samples")
    rejected(lambda: build_core_flood_branch(
        table, gas_id="H2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic", interpretation_evidence="synthetic",
        viscosity_pa_s=0.0, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic",
    ), "nonpositive viscosity")
    percent = build_core_flood_branch(
        CoreFloodTable(
            filename=table.filename, source_url=table.source_url, sha256=table.sha256,
            worksheet=table.worksheet,
            rows=(("Sw synthetic", "Krg synthetic"),
                  (20.0, 5.0), (50.0, 30.0), (80.0, 80.0)),
            source_row_ids=table.source_row_ids,
        ), gas_id="H2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="percent", saturation_basis="synthetic percent saturation",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="percent",
        relative_permeability_basis="synthetic percent relative permeability",
        interpretation_evidence="synthetic explicit scale contract",
        viscosity_pa_s=0.001, viscosity_basis="dynamic viscosity",
        viscosity_evidence="synthetic declared input",
        saturation_scale=0.01, relative_permeability_scale=0.01,
    )
    assert math.isclose(percent.saturation_scale, 0.01, rel_tol=0., abs_tol=1e-16)
    assert math.isclose(percent.relative_permeability_scale, 0.01, rel_tol=0., abs_tol=1e-16)
    assert all(math.isclose(actual, expected, rel_tol=0., abs_tol=1e-15)
               for actual, expected in zip(percent.saturation_values, (0.2, 0.5, 0.8), strict=True))
    assert all(math.isclose(actual, expected, rel_tol=0., abs_tol=1e-15)
               for actual, expected in zip(percent.relative_permeability_values,
                                           (0.05, 0.3, 0.8), strict=True))
    changed_point = branch.evaluate(0.35)
    object.__setattr__(changed_point, "relative_permeability", 0.2)
    rejected(changed_point.require_current, "an edited interpolation result")
    changed = list(table.rows)
    changed[1] = (0.25, 0.05)
    object.__setattr__(table, "rows", tuple(changed))
    rejected(branch.require_current, "a source table mutation")
    return ValidationOutcome(True, {
        "source": "synthetic contract only", "gas_id": branch.gas_id,
        "branch": branch.branch, "relative_phase": branch.relative_phase,
        "interpolation": "piecewise-linear within observed range",
        "mobility_basis": "relative permeability / explicitly supplied dynamic viscosity",
        "scales_recorded": True, "source_mutation_detected": True,
        "measured_data_fit_performed": False,
    }, (
        "This synthetic contract exercises API behavior, not measured-data interpretation.",
        "Measured branch selection, field semantics, unit declarations, and viscosity evidence require review.",
    ))


def validate_power_law_fit(*, work_directory, **parameters):
    from h2physics.adapters.core_flood_mobility import (
        build_core_flood_branch, fit_core_flood_power_law,
    )
    from h2physics.data.hydrogen_core_flood import CoreFloodTable

    filename = "Primary_drainage_H2.xlsx"
    sw = (0.0, 0.2, 0.4, 0.6, 0.72)
    swir, sgr, kr_end, exponent = 0.0, 0.2, 0.9, 2.0
    kr = tuple(kr_end * (1.0 - value / (1.0 - sgr)) ** exponent for value in sw)
    table = CoreFloodTable(
        filename=filename,
        source_url=("https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/"
                    "ce094687-9357-4234-8dc4-9fda3efa5199/file_downloaded"),
        sha256="60b94149b4f84b131fc1a70eac592dc741f22486cec1725ec7b904c4b56ec7ff",
        worksheet="Kr",
        rows=(("Sw synthetic", "Krg synthetic"),
              *((value, permeability) for value, permeability in zip(sw, kr, strict=True))),
        source_row_ids=tuple(
            f"hydrogen-core-flood:{filename}:Kr:row-{row}" for row in range(1, len(sw) + 2)
        ),
    )
    branch = build_core_flood_branch(
        table, gas_id="H2", branch="primary_drainage", relative_phase="gas",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic water saturation",
        relative_permeability_header="Krg synthetic",
        relative_permeability_role="gas_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic gas relative permeability",
        interpretation_evidence="synthetic explicit field declaration",
        viscosity_pa_s=1e-5, viscosity_basis="synthetic dynamic viscosity",
        viscosity_evidence="synthetic declared viscosity",
    )
    fitted = fit_core_flood_power_law(
        branch, irreducible_water_saturation=swir,
        residual_gas_saturation=sgr, endpoint_evidence="synthetic endpoint declaration",
    )
    assert math.isclose(fitted.endpoint_relative_permeability, kr_end,
                        rel_tol=1e-8, abs_tol=1e-10)
    assert math.isclose(fitted.exponent, exponent, rel_tol=1e-8, abs_tol=1e-10)
    assert fitted.rmse < 1e-10 and fitted.maximum_absolute_error < 1e-10
    assert fitted.source_row_ids == branch.source_row_ids
    assert math.isclose(fitted.evaluate(0.2), kr_end * 0.75**exponent,
                        rel_tol=1e-9, abs_tol=1e-11)
    assert fitted.require_current() is fitted
    try:
        fitted.evaluate(0.8)
    except ValueError:
        pass
    else:
        raise AssertionError("Fitted curve extrapolated beyond its observations")
    try:
        fit_core_flood_power_law(
            branch, irreducible_water_saturation=0.0,
            residual_gas_saturation=1.0, endpoint_evidence="invalid endpoints",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Fit accepted a degenerate saturation interval")
    kw_end, water_exponent = 0.7, 1.5
    kw = tuple(kw_end * (value / (1.0 - sgr)) ** water_exponent for value in sw)
    water_table = CoreFloodTable(
        filename=filename, source_url=table.source_url, sha256=table.sha256,
        worksheet="Kr",
        rows=(("Sw synthetic", "Krw synthetic"),
              *((value, permeability) for value, permeability in zip(sw, kw, strict=True))),
        source_row_ids=table.source_row_ids,
    )
    water_branch = build_core_flood_branch(
        water_table, gas_id="H2", branch="primary_drainage", relative_phase="water",
        saturation_header="Sw synthetic", saturation_role="water_saturation",
        saturation_unit="fraction", saturation_basis="synthetic water saturation",
        relative_permeability_header="Krw synthetic",
        relative_permeability_role="water_relative_permeability",
        relative_permeability_unit="dimensionless",
        relative_permeability_basis="synthetic water relative permeability",
        interpretation_evidence="synthetic explicit field declaration",
        viscosity_pa_s=1e-3, viscosity_basis="synthetic dynamic viscosity",
        viscosity_evidence="synthetic declared viscosity",
    )
    water_fit = fit_core_flood_power_law(
        water_branch, irreducible_water_saturation=swir,
        residual_gas_saturation=sgr, endpoint_evidence="synthetic endpoint declaration",
    )
    assert math.isclose(water_fit.endpoint_relative_permeability, kw_end,
                        rel_tol=1e-8, abs_tol=1e-10)
    assert math.isclose(water_fit.exponent, water_exponent,
                        rel_tol=1e-8, abs_tol=1e-10)
    assert water_fit.rmse < 1e-10
    return ValidationOutcome(True, {
        "gas_id": fitted.branch_source.gas_id,
        "branch": fitted.branch_source.branch,
        "phase": fitted.branch_source.relative_phase,
        "endpoint_relative_permeability": fitted.endpoint_relative_permeability,
        "power_law_exponent": fitted.exponent,
        "rmse": fitted.rmse,
        "source_rows": len(fitted.source_row_ids),
        "fit_method": fitted.fit_method,
        "water_phase_exponent": water_fit.exponent,
    }, (
        "Synthetic contract only; real workbook headings and field semantics still require review.",
        "A fitted Corey-type curve summarizes the selected table and does not qualify reservoir performance.",
    ))
