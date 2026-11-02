"""Versioned QM9-LOHC computed data, molecular checks and reference heat input.

The primary data descriptor defines gas-phase dehydrogenation at 298.15 K,
101325 Pa, with delta_H in kJ/mol H2. These are not liquid kinetic data.
https://doi.org/10.1038/s41597-025-04468-0
"""

import csv
import hashlib
import io
import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from zipfile import ZipFile

from ..adapters.rdkit import MolecularIdentity, molecule_from_smiles
from ..reactions import ReferenceReactionHeat, StoichiometricReaction

QM9_ARCHIVE_SHA256 = "9f89ee72586dd00e5be58c0650b11d2e135e993873f90da23c8094c5265ee242"
QM9_ROOT = "HydrogenStorage-QM9-LOHC-1fe4a16"
QM9_MAIN_MEMBER = QM9_ROOT + "/QM9_G4MP2_all.csv"
QM9_DESCRIPTOR = "https://doi.org/10.1038/s41597-025-04468-0"
QM9_DATA_DOI = "10.5281/zenodo.10926772"


@dataclass(frozen=True, slots=True)
class LOHCRow:
    source_id: str
    line: int
    cells: Mapping[str, str]

    def __post_init__(self):
        if not self.source_id or self.line < 2:
            raise ValueError("Preserve a data-member identity and CSV line number")
        object.__setattr__(self, "cells", MappingProxyType(dict(self.cells)))


@dataclass(frozen=True, slots=True)
class LOHCArchive:
    source_sha256: str
    member_sha256: str
    duplicate_table_matches: bool
    rows: tuple[LOHCRow, ...]


def load_qm9_lohc_archive(path: str | Path, *, expected_sha256: str = QM9_ARCHIVE_SHA256,
                         maximum_bytes: int = 2_000_000) -> LOHCArchive:
    """Read one authoritative table, never executing/extracting archive programs.

    The default checksum selects the acquired, rights-reviewed Zenodo release.
    A different checksum is an explicit caller declaration, e.g. an authored fixture.
    """
    path = Path(path)
    if path.stat().st_size > maximum_bytes:
        raise ValueError("Archive exceeds the declared size budget")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ValueError("Archive differs from its declared SHA-256")
    with ZipFile(io.BytesIO(raw)) as archive:
        for name in (QM9_MAIN_MEMBER, QM9_ROOT + "/QM9-LOHC-web/QM9_G4MP2_all.csv"):
            if archive.namelist().count(name) != 1 or archive.getinfo(name).file_size > 10_000_000:
                raise ValueError("Expected a unique bounded QM9 table member")
        payload = archive.read(QM9_MAIN_MEMBER)
        duplicate = archive.read(QM9_ROOT + "/QM9-LOHC-web/QM9_G4MP2_all.csv")
    member_hash = hashlib.sha256(payload).hexdigest()
    source_id = f"{QM9_DATA_DOI}:sha256={digest}:{QM9_MAIN_MEMBER}:sha256={member_hash}"
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    required = {"unsat_SMILE", "sat_SMILE", "delta_H", "nH2", "pH2", "molar_mass"}
    if (reader.fieldnames is None or not required <= set(reader.fieldnames)
            or len(set(reader.fieldnames)) != len(reader.fieldnames)):
        raise ValueError("QM9 table does not match the declared column profile")
    rows = []
    for record in reader:
        if None in record or any(value is None for value in record.values()):
            raise ValueError("CSV row width conflicts with its header")
        rows.append(LOHCRow(source_id, reader.line_num, record))
    if not rows:
        raise ValueError("QM9 reaction table is empty")
    return LOHCArchive(digest, member_hash, payload == duplicate, tuple(rows))


def _number(row, key):
    try:
        value = float(row.cells.get(key, ""))
        return value if math.isfinite(value) else math.nan
    except ValueError:
        return math.nan


@dataclass(frozen=True, slots=True)
class LOHCReactionAudit:
    row: LOHCRow
    lean: MolecularIdentity | None
    rich: MolecularIdentity | None
    hydrogen: MolecularIdentity
    reaction: StoichiometricReaction | None
    reference_heat: ReferenceReactionHeat | None
    calculated_capacity_mass_fraction: float
    reported_capacity_mass_fraction: float
    capacity_difference_percentage_points: float
    lean_molar_mass_difference_g_mol: float
    issues: tuple[str, ...]

    @property
    def pair_key(self) -> tuple[str, str] | None:
        if self.lean is None or self.rich is None:
            return None
        return self.lean.canonical_smiles, self.rich.canonical_smiles


def audit_lohc_reaction(row: LOHCRow, *, capacity_tolerance_percentage_points: float = .01
                         ) -> LOHCReactionAudit:
    """Check structure and every reported normalization; retain failed original rows.

    The capacity tolerance is a reporting gate only. A difference is retained and
    never repairs a publisher value or changes the reconstructed mass basis.
    """
    if not 0 <= capacity_tolerance_percentage_points < math.inf:
        raise ValueError("Declare a finite nonnegative capacity reporting tolerance")
    issues = []
    hydrogen = molecule_from_smiles("[H][H]", identifier="H2", phase="gas")
    molecules = []
    for key, identifier in (("unsat_SMILE", "lean"), ("sat_SMILE", "rich")):
        try:
            molecules.append(molecule_from_smiles(row.cells.get(key, ""), identifier=identifier,
                                                 phase="gas"))
        except ValueError:
            molecules.append(None)
            issues.append(f"{key}:native_molecular_identity_rejected")
    lean, rich = molecules
    claimed_h2 = _number(row, "nH2")
    reaction = None
    capacity = mass_difference = math.nan
    if lean is not None and rich is not None:
        n_h2 = (rich.species.elements.get("H", 0) - lean.species.elements.get("H", 0))/2
        if n_h2 <= 0 or not n_h2.is_integer():
            issues.append("structures_do_not_release_positive_integer_H2")
        else:
            try:
                reaction = StoichiometricReaction(f"{row.source_id}:line={row.line}:dehydrogenation",
                    (rich.species, lean.species, hydrogen.species), (-1., 1., n_h2))
                capacity = n_h2*hydrogen.species.molar_mass_kg_mol/rich.species.molar_mass_kg_mol
            except ValueError:
                issues.append("structure_pair_element_charge_or_mass_imbalance")
            if claimed_h2 != n_h2:
                issues.append("reported_nH2_conflicts_with_molecular_composition")
        mass_difference = 1000*lean.species.molar_mass_kg_mol - _number(row, "molar_mass")
        if not math.isfinite(mass_difference) or abs(mass_difference) > 1e-6:
            issues.append("reported_lean_molar_mass_differs_from_native_basis")
    if not math.isfinite(claimed_h2) or claimed_h2 <= 0 or not claimed_h2.is_integer():
        issues.append("invalid_reported_nH2")
    reported_capacity = _number(row, "pH2")/100
    difference = 100*(capacity-reported_capacity)
    if not 0 <= reported_capacity <= 1:
        issues.append("invalid_reported_capacity")
    elif math.isfinite(difference) and abs(difference) > capacity_tolerance_percentage_points:
        issues.append("reported_capacity_differs_from_native_mass_basis")
    enthalpy = _number(row, "delta_H")
    if not math.isfinite(enthalpy):
        issues.append("missing_or_nonfinite_reference_enthalpy")
    heat = None
    if (reaction is not None and claimed_h2 == reaction.coefficients[2]
            and math.isfinite(enthalpy)):
        heat = ReferenceReactionHeat(reaction, enthalpy*1000*claimed_h2, 298.15, 101325.,
            f"{row.source_id}:line={row.line};{QM9_DESCRIPTOR}",
            "G4MP2 standard gas-phase dehydrogenation; publisher kJ/mol H2 converted to J/mol extent",
            "computed")
    return LOHCReactionAudit(row, lean, rich, hydrogen, reaction, heat, capacity,
                             reported_capacity, difference, mass_difference, tuple(issues))


def audit_qm9_lohc_dataset(archive: LOHCArchive, *, capacity_tolerance_percentage_points: float = .01
                           ) -> tuple[LOHCReactionAudit, ...]:
    """Apply cross-row identity checks before admitting a heat for model input.

    Distinct source rows with the same canonical molecular pair can disagree in
    enthalpy. Without another documented identity (e.g. conformer), neither value
    is selected, averaged or assigned to that pair automatically.
    """
    audits = [audit_lohc_reaction(row,
        capacity_tolerance_percentage_points=capacity_tolerance_percentage_points) for row in archive.rows]
    groups = defaultdict(list)
    for index, audit in enumerate(audits):
        if audit.pair_key is not None:
            groups[audit.pair_key].append(index)
    for indices in groups.values():
        heats = {_number(audits[i].row, "delta_H") for i in indices
                 if math.isfinite(_number(audits[i].row, "delta_H"))}
        if len(heats) > 1:
            for index in indices:
                audit = audits[index]
                audits[index] = replace(audit, reference_heat=None, issues=(*audit.issues,
                    "conflicting_reference_enthalpies_for_canonical_pair"))
    return tuple(audits)
