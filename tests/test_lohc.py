import csv
import hashlib
import io
import zipfile

import pytest

from h2physics.data.lohc import (
    QM9_MAIN_MEMBER,
    QM9_ROOT,
    LOHCArchive,
    LOHCRow,
    audit_lohc_reaction,
    audit_qm9_lohc_dataset,
    load_qm9_lohc_archive,
)


def authored_row(**changes):
    # Authored structure pair and arbitrary test heat, not a publisher row.
    cells = dict(unsat_SMILE="C=C", sat_SMILE="CC", delta_H="42.5", nH2="1",
                 pH2="6.7043565014965", molar_mass="28.054")
    cells.update(changes)
    return LOHCRow("authored-fixture", 2, cells)


def require_rdkit():
    pytest.importorskip("rdkit")


def test_native_molecule_identity_capacity_and_reference_normalization():
    require_rdkit()
    audited = audit_lohc_reaction(authored_row())
    assert audited.issues == ()
    assert audited.lean.native_molecule.GetNumAtoms() == 2
    assert dict(audited.rich.species.elements) == {"C": 2, "H": 6}
    assert audited.reaction.coefficients == (-1, 1, 1)
    assert audited.calculated_capacity_mass_fraction == pytest.approx(.002016/.03007)
    heat = audited.reference_heat
    assert heat.origin == "computed" and heat.temperature_k == 298.15
    assert heat.enthalpy_j_mol_extent == 42500
    assert heat.heat_j(audited.reaction.convert({"rich": 3}, 2),
                       temperature_k=298.15, pressure_pa=101325) == 85000


@pytest.mark.parametrize("changes,issue", [
    ({"nH2": "2"}, "reported_nH2_conflicts"),
    ({"nH2": "nan"}, "invalid_reported_nH2"),
    ({"sat_SMILE": "CCO"}, "imbalance"),
    ({"sat_SMILE": "C=C"}, "positive_integer"),
    ({"sat_SMILE": "[13CH3]C"}, "native_molecular"),
    ({"delta_H": ""}, "missing_or_nonfinite"),
])
def test_bad_source_rows_are_retained_and_cannot_supply_heat(changes, issue):
    require_rdkit()
    row = authored_row(**changes)
    audited = audit_lohc_reaction(row)
    assert audited.row is row
    assert audited.reference_heat is None
    assert any(issue in value for value in audited.issues)


def test_capacity_disagreement_is_retained_separately_from_balanced_heat():
    require_rdkit()
    audited = audit_lohc_reaction(authored_row(pH2="11"))
    assert "reported_capacity_differs_from_native_mass_basis" in audited.issues
    assert audited.reference_heat is not None
    assert audited.row.cells["pH2"] == "11"


def test_conflicting_duplicate_pair_heats_are_withheld_without_averaging():
    require_rdkit()
    first = authored_row()
    second = LOHCRow("authored-fixture", 3, authored_row(delta_H="44").cells)
    archive = LOHCArchive("authored", "authored", True, (first, second))
    individual = audit_lohc_reaction(first)
    assert individual.reference_heat is not None
    audited = audit_qm9_lohc_dataset(archive)
    assert all(a.reference_heat is None for a in audited)
    assert all("conflicting_reference_enthalpies_for_canonical_pair" in a.issues for a in audited)
    assert [a.row.cells["delta_H"] for a in audited] == ["42.5", "44"]
    identical = audit_qm9_lohc_dataset(LOHCArchive("authored", "authored", True,
        (first, LOHCRow("authored-fixture", 3, first.cells))))
    assert all(a.reference_heat is not None for a in identical)


def test_archive_selects_one_table_checks_duplicate_and_never_extracts(tmp_path):
    row = authored_row()
    data = io.StringIO()
    writer = csv.DictWriter(data, fieldnames=list(row.cells))
    writer.writeheader()
    writer.writerow(row.cells)
    path = tmp_path / "authored.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(QM9_MAIN_MEMBER, data.getvalue())
        z.writestr(QM9_ROOT + "/QM9-LOHC-web/QM9_G4MP2_all.csv", data.getvalue())
        z.writestr("untrusted.py", "raise RuntimeError('never execute')")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="SHA-256"):
        load_qm9_lohc_archive(path)
    archive = load_qm9_lohc_archive(path, expected_sha256=digest)
    assert archive.duplicate_table_matches
    assert len(archive.rows) == 1 and archive.rows[0].line == 2
    assert len(list(tmp_path.iterdir())) == 1
