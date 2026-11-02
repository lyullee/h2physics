"""Original miniature exports; no external table or observation is redistributed."""

from dataclasses import replace
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.data.photocatalysis import (
    MOLAR_RATE_FACTOR,
    MOLAR_RATE_SOURCE_UNIT,
    PhotocatalysisArchive,
    PhotocatalysisMappingEvidence,
    reported_aqy,
    reported_h2_specific_rate,
)
from h2physics.data.pressure_peaking import file_sha256
from h2physics.observations import split_experiments


def fixture(tmp_path, members=None):
    path = tmp_path / "authored.zip"
    if members is None:
        members = {"Figure4a.txt": "cat A\t3600\t17\ncat B\t-1800\t--\ncat C\t \t\n"}
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, text in members.items():
            archive.writestr(name, text.encode("utf-8"))
    return path


def opened(path, **kwargs):
    return PhotocatalysisArchive(path, source_id="authored-source", study_id="authored-one-study",
        expected_sha256=file_sha256(path), require_complete=False, **kwargs)


def evidence(block, **kwargs):
    values = dict(member_sha256=block.schema.member.sha256, source_column=2,
        source_unit=MOLAR_RATE_SOURCE_UNIT, primary_source_id="authored-primary",
        primary_locator="authored methods / specific-rate definition", evidence_id="authored-mapping",
        catalyst_mass_basis_id="total dry catalyst mass", condition_source_id="authored-conditions")
    return PhotocatalysisMappingEvidence(**(values | kwargs))


def aqy_fixture(tmp_path):
    # Columns 4-7 are deliberately unrelated fields. No unit is supplied for column3.
    return fixture(tmp_path, {"Figure4b.txt": "Wavelength\tAQY\t2\t\t\t\t\n"
        "nm\t%\tSample\t\t\t\t\nName\tcat A\tcat B\t\t\t\t\n"
        "500\t12\t25\t9\t8\t7\t6\n0\t-2\t--\t9\t8\t7\t6\n"})


def test_raw_rows_labels_masks_signs_and_unknown_units(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks("Figure4a.txt"))
        assert block.source_lines == (1, 2, 3)
        assert block.sample_labels == ("cat A", "cat B", "cat C")
        assert block.raw_cells[2] == ("cat C", " ", "")
        assert block.invalid_reasons[1] == ("categorical_or_unresolved_text", "", "source_placeholder")
        assert block.invalid_reasons[2][1:] == ("source_blank", "source_blank")
        assert block.observations.values[1, 1] == -1800
        assert block.observations.valid.sum() == 3
        assert all(v.unit == "source_unit_unresolved" for v in block.observations.variables)
        assert block.observations.origins == (Origin.UNRESOLVED, Origin.RECONSTRUCTED, Origin.UNRESOLVED)
        assert "Figure4a.txt" in block.observations.row_ids[0]
        assert block.schema.member.sha256 in block.observations.row_ids[0]
        assert block.observations.row_ids[0].endswith("line-1")
        assert not block.observations.values.flags.writeable
        with pytest.raises(ValueError, match="TimeSeries"):
            block.as_time_series()


def test_windows_are_source_lines_and_blocking_does_not_change_values(tmp_path):
    with opened(fixture(tmp_path)) as source:
        blocks = tuple(source.iter_blocks("Figure4a.txt", block_rows=1))
        whole = next(source.iter_blocks("Figure4a.txt"))
        np.testing.assert_equal(np.concatenate([b.observations.values for b in blocks]), whole.observations.values)
        assert tuple(i for b in blocks for i in b.observations.row_ids) == whole.observations.row_ids
        assert next(source.iter_blocks("Figure4a.txt", first_line=2, last_line=2)).source_lines == (2,)
        for kwargs in ({"block_rows": 0}, {"block_rows": 2049}, {"block_rows": True},
                       {"first_line": 0}, {"last_line": 4}, {"first_line": 3, "last_line": 2}):
            with pytest.raises(ValueError):
                tuple(source.iter_blocks("Figure4a.txt", **kwargs))


def test_finite_grammar_preserves_overflow_and_non_numeric_tokens(tmp_path):
    with opened(fixture(tmp_path, {"Figure4a.txt": "label\t1e999\tNaN\n\t\t\n"})) as source:
        block = next(source.iter_blocks("Figure4a.txt"))
        assert np.isinf(block.observations.values[0, 1])
        assert block.invalid_reasons[0][1:] == ("source_nonfinite", "categorical_or_unresolved_text")
        assert not block.observations.valid.any()
        assert block.source_lines == (1, 2)  # Entirely missing rows survive.


def test_duplicate_members_keep_distinct_rows_and_one_study(tmp_path):
    header = "\t".join(str(i) for i in range(62)) + "\n"
    body = "\t".join(str(i + 3) for i in range(62)) + "\n"
    with opened(fixture(tmp_path, {"Figure7b.txt": header + body,
                                  "Figure7d.txt": header + body,
                                  "Figure7c.txt": body})) as source:
        assert source.duplicate_groups == (("Figure7b.txt", "Figure7d.txt"),)
        left = next(source.iter_blocks("Figure7b.txt"))
        right = next(source.iter_blocks("Figure7d.txt"))
        unmapped = next(source.iter_blocks("Figure7c.txt"))
        assert left.observations.row_ids != right.observations.row_ids
        assert dict(left.observations.context)["source_equivalence_id"] == dict(right.observations.context)["source_equivalence_id"]
        assert left.observations.experiment_ids == right.observations.experiment_ids == ("authored-one-study",)
        assert unmapped.schema.header_rows == ()
        assert unmapped.source_lines == (1,) and left.source_lines == (2,)
        assert unmapped.schema.columns[1].header_cells == ()
        with pytest.raises(ValueError, match="proper subset"):
            split_experiments(left.observations, {"authored-one-study"})


def test_independent_grids_duplicate_labels_and_processed_origins(tmp_path):
    with opened(fixture(tmp_path, {"FigureS13a3.txt":
        "Wavelength\tExperimental Data\tFitted\tComponent3\tComponent3\tResidual\n"
        "400\t1\t2\t3\t4\t-1\n",
        "Figure6a.txt": "Energy\tIntensity\tEnergy\tIntensity\n"
        "eV\ta.u.\teV\ta.u.\ncat A\t\tcat B\t\n1\t3\t5\t7\n2\t4\t9\t8\n"})) as source:
        block = next(source.iter_blocks("FigureS13a3.txt"))
        assert block.schema.columns[3].header_cells == block.schema.columns[4].header_cells
        assert block.observations.variables[3].name != block.observations.variables[4].name
        assert block.observations.origins[1] is Origin.MEASURED
        assert block.observations.origins[2:] == (Origin.RECONSTRUCTED,) * 4
        grid = next(source.iter_blocks("Figure6a.txt"))
        assert grid.schema.header_rows[1] == ("eV", "a.u.", "eV", "a.u.")
        np.testing.assert_equal(grid.observations.values[:, [0, 2]], [[1, 5], [2, 9]])
        assert grid.source_lines == (4, 5)


def test_source_normalization_is_reconstructed_and_energy_labels_are_not_samples(tmp_path):
    with opened(fixture(tmp_path, {"FigureS13a1.txt":
        "Wavelength\tExperimental data\tFitted\tComponent1\tComponent2\tComponent3\n"
        "nm\tNormalize to [0,1]\t\t\t\t\n400\t1.2\t-1\t3\t4\t5\n",
        "FigureS13b.txt": "Energy label\tcat A\tcat B\tcat C\n2.5 eV\t1\t2\t3\n"})) as source:
        normalized = next(source.iter_blocks("FigureS13a1.txt"))
        assert normalized.observations.origins[1] is Origin.RECONSTRUCTED
        assert normalized.observations.values[0, 1] == 1.2  # No unit-interval repair.
        labelled = next(source.iter_blocks("FigureS13b.txt"))
        assert labelled.row_labels == ("2.5 eV",)
        assert labelled.sample_labels == ()


def test_h2_rate_requires_reviewed_member_specific_mapping(tmp_path):
    with opened(fixture(tmp_path)) as source:
        block = next(source.iter_blocks("Figure4a.txt"))
        for mapping in (evidence(block), evidence(block, review_status="caller_reviewed", member_sha256="wrong"),
                        evidence(block, review_status="caller_reviewed", source_column=3),
                        evidence(block, review_status="caller_reviewed", source_unit="mL/h")):
            with pytest.raises(ValueError, match="Mapping"):
                reported_h2_specific_rate(block, evidence=mapping)
        with pytest.raises(ValueError, match="mass normalization"):
            reported_h2_specific_rate(block, evidence=evidence(block, review_status="caller_reviewed",
                                                              catalyst_mass_basis_id=""))
        mapping = evidence(block, review_status="caller_reviewed")
        view = reported_h2_specific_rate(block, evidence=mapping)
        assert view.source is block and view.mapping_evidence is mapping
        assert view.observations.values[0, 0] == pytest.approx(.001)
        assert view.observations.values[1, 0] == pytest.approx(-.0005)
        assert MOLAR_RATE_FACTOR == pytest.approx(1 / 3_600_000)
        np.testing.assert_equal(view.observations.valid[:, 0], block.observations.valid[:, 1])
        assert view.sample_labels == block.sample_labels
        assert view.observations.row_ids == block.observations.row_ids
        assert view.observations.origins == (Origin.RECONSTRUCTED,)
        assert block.observations.values[0, 2] == 17  # Auxiliary field is never sigma.


def test_aqy_native_header_first_column_and_no_borrowed_candidate_unit(tmp_path):
    with opened(aqy_fixture(tmp_path)) as source:
        block = next(source.iter_blocks("Figure4b.txt"))
        view = reported_aqy(block)
        np.testing.assert_allclose(view.observations.values[:, 0], [500e-9, 0])
        np.testing.assert_allclose(view.observations.values[:, 1], [.12, -.02])
        assert not view.observations.valid[1, 0] and view.observations.valid[1, 1]
        assert view.sample_labels == ("cat A", "cat A")
        assert view.mapping_evidence is None and view.source is block
        with pytest.raises(ValueError, match="no explicit percent"):
            reported_aqy(block, source_column=3)
        mapping = evidence(block, source_column=3, source_unit="%", review_status="caller_reviewed")
        candidate = reported_aqy(block, source_column=3, evidence=mapping)
        assert candidate.observations.values[0, 1] == .25
        assert not candidate.observations.valid[1, 1]
        assert candidate.sample_labels == ("cat B", "cat B")
        assert "electron normalization" in candidate.observations.variables[1].basis_id


def test_mapping_never_uses_inaccessible_primary_as_automatic_clearance(tmp_path):
    with opened(aqy_fixture(tmp_path)) as source:
        block = next(source.iter_blocks("Figure4b.txt"))
        with pytest.raises(ValueError, match="unreviewed"):
            reported_aqy(block, source_column=3, evidence=evidence(block, source_column=3, source_unit="%"))
        with pytest.raises(ValueError, match="header evidence"):
            reported_aqy(replace(block, schema=replace(block.schema, header_rows=(
                ("Wavelength", "AQY", "2", "", "", "", ""),
                ("s", "%", "Sample", "", "", "", ""),
                ("Name", "cat A", "cat B", "", "", "", "")))))
    for kwargs in ({"primary_locator": ""}, {"source_column": True}, {"review_status": "verified_by_software"}):
        with pytest.raises(ValueError):
            evidence(block, **kwargs)


@pytest.mark.parametrize("member", ["../Figure4a.txt", "/Figure4a.txt", "C:Figure4a.txt", "a\\Figure4a.txt"])
def test_unsafe_archive_members_are_rejected(tmp_path, member):
    # Windows ZipInfo may normalize backslashes; the resulting undeclared member
    # still fails the reviewed schema rather than being opened as a data table.
    with pytest.raises(ValueError, match="Unsafe|schema"):
        with opened(fixture(tmp_path, {member: "1\t2\t3\n"})):
            pass


def test_schema_hash_completeness_and_context_are_enforced(tmp_path):
    path = fixture(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        with PhotocatalysisArchive(path, source_id="source", study_id="study", expected_sha256="wrong"):
            pass
    with pytest.raises(ValueError, match="schema"):
        with PhotocatalysisArchive(path, source_id="source", study_id="study", expected_sha256=file_sha256(path)):
            pass
    source = opened(path)
    with pytest.raises(ValueError, match="inside"):
        source.schema("Figure4a.txt")
    with opened(fixture(tmp_path, {"Figure4a.txt": "1\t2\n"})) as source:
        with pytest.raises(ValueError, match="line/column"):
            next(source.iter_blocks("Figure4a.txt"))


@pytest.mark.parametrize("budgets", [{"maximum_bytes": 1}, {"maximum_expanded_bytes": 1},
                                    {"maximum_member_bytes": 1}, {"maximum_lines": 0}])
def test_archive_budgets_are_explicit(tmp_path, budgets):
    with pytest.raises(ValueError):
        with opened(fixture(tmp_path), **budgets):
            pass


def test_source_mutation_is_detected_on_exit(tmp_path):
    path = fixture(tmp_path)
    with pytest.raises(ValueError, match="changed during"):
        with opened(path):
            with path.open("ab") as stream:
                stream.write(b"authored-source-mutation")
