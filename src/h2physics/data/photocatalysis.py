"""Lossless bounded views of the CC-BY-4.0 brookite photocatalysis text exports.

Data: https://doi.org/10.5281/zenodo.15277951. Numerical data, source labels and
physical mapping evidence are distinct; missing axes/units are not inferred.
"""

import hashlib
import math
import re
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import numpy as np

from ..core import Origin
from ..observations import ObservationTable, Variable
from .pressure_peaking import file_sha256

PROFILE_ID = "brookite-tio2-text-v1-profile-1"
ARCHIVE_SHA256 = "b22f168f0244fa9138c6e392150171d9c808bec605f619268f8e8d18de997353"
PRIMARY_DOI = "10.1021/acsaem.4c01950"
MOLAR_RATE_SOURCE_UNIT = "umol_H2/(g_catalyst*h)"
MOLAR_RATE_SI_UNIT = "mol_H2/(kg_catalyst*s)"
MOLAR_RATE_FACTOR = 1e-6 / (1e-3 * 3600.)
# Only source layout is declared here. A headerless figure name is not an axis/unit proof.
LAYOUTS = {
    "Figure2a.txt": (0, 6), "Figure2a_ref..txt": (0, 2), "Figure2b.txt": (0, 6),
    "Figure2c.txt": (0, 5), "Figure2d.txt": (0, 5), "Figure4a.txt": (0, 3),
    "Figure4b.txt": (3, 7), "Figure5_dark.txt": (0, 3), "Figure5_under_UV.txt": (0, 3),
    "Figure6a.txt": (3, 4), "Figure7a.txt": (1, 4), "Figure7b.txt": (1, 62),
    "Figure7c.txt": (0, 62), "Figure7d.txt": (1, 62), "FigureS1.txt": (2, 12),
    "FigureS10.txt": (2, 3), "FigureS11a.txt": (0, 2), "FigureS11b.txt": (3, 4),
    "FigureS13a1.txt": (2, 6), "FigureS13a2.txt": (1, 6), "FigureS13a3.txt": (1, 6),
    "FigureS13b.txt": (1, 4), "FigureS2a.txt": (3, 7), "FigureS2b.txt": (3, 7),
    "FigureS3a.txt": (2, 9), "FigureS3b.txt": (2, 9), "FigureS3c.txt": (2, 9),
    "FigureS3d.txt": (2, 9), "FigureS3e.txt": (1, 2), "FigureS5.txt": (0, 3),
    "FigureS6a.txt": (2, 9), "FigureS6b.txt": (2, 9), "FigureS6c.txt": (2, 9),
    "FigureS6d.txt": (1, 2), "FigureS8.txt": (1, 7), "FigureS9a.txt": (2, 2),
    "FigureS9b.txt": (2, 2),
}
_NUMERIC = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


@dataclass(frozen=True, slots=True)
class PhotocatalysisMember:
    name: str
    bytes: int
    sha256: str
    crc32: str


@dataclass(frozen=True, slots=True)
class PhotocatalysisColumn:
    source_column: int
    header_cells: tuple[str, ...]
    variable: Variable
    origin: Origin


@dataclass(frozen=True, slots=True)
class PhotocatalysisSchema:
    member: PhotocatalysisMember
    header_rows: tuple[tuple[str, ...], ...]
    columns: tuple[PhotocatalysisColumn, ...]
    first_data_line: int
    last_data_line: int
    encoding: str
    source_role: str
    axis_status: str


@dataclass(frozen=True, slots=True)
class PhotocatalysisBlock:
    observations: ObservationTable
    schema: PhotocatalysisSchema
    source_lines: tuple[int, ...]
    raw_cells: tuple[tuple[str, ...], ...]
    invalid_reasons: tuple[tuple[str, ...], ...]

    @property
    def sample_labels(self):
        """Only explicitly categorical source tables expose their first-column labels."""
        if self.schema.member.name not in ("Figure4a.txt", "FigureS5.txt"):
            return ()
        return tuple(row[0] for row in self.raw_cells)

    @property
    def row_labels(self):
        """S13b's categorical energy labels are row labels, not catalyst identities."""
        if self.schema.member.name not in ("Figure4a.txt", "FigureS5.txt", "FigureS13b.txt"):
            return ()
        return tuple(row[0] for row in self.raw_cells)

    def as_time_series(self):
        raise ValueError("No automatic time/axis assignment or TimeSeries conversion for figure exports")


def _origin(name, headers, column):
    label = " ".join(row[column] for row in headers).lower()
    if any(word in label for word in ("fitted", "component", "residual", "backgnd", "normalize")):
        return Origin.RECONSTRUCTED
    if "experimental data" in label or "experimenta data" in label:
        return Origin.MEASURED  # Reported experimental field, not independent validation.
    if name in ("Figure2d.txt", "FigureS2b.txt", "FigureS13b.txt", "FigureS3e.txt", "FigureS6d.txt"):
        return Origin.RECONSTRUCTED
    if name == "Figure4b.txt" and column in (0, 1):
        return Origin.RECONSTRUCTED  # Coordinate and reported apparent-yield processing.
    if name == "Figure4a.txt" and column == 1:
        return Origin.RECONSTRUCTED  # Source-reported specific rate, not raw gas metrology.
    return Origin.UNRESOLVED


def _role(name):
    if name in ("Figure4a.txt", "FigureS5.txt"):
        return "categorical catalyst comparison; rate/auxiliary units require explicit source evidence"
    if name == "Figure4b.txt":
        return "reported AQY export; first wavelength/AQY units explicit, other column roles unresolved"
    if name in ("FigureS9a.txt", "FigureS9b.txt", "FigureS10.txt"):
        return "reported Time(h) history; ordinate unit and cumulative/rate interpretation unresolved"
    if name.startswith(("FigureS3", "FigureS6", "FigureS13")):
        return "material characterization with reported experimental/processed fields; not H2 kinetic targets"
    return "figure-specific numerical characterization; physical axes require source-supported mapping"


class PhotocatalysisArchive:
    """Read-only native ZIP/TSV; no archive extraction, plotting or source execution.

    Per-member text decoding is bounded; numeric arrays/masks/identities are block
    bounded. Wide files keep each original column and independent grids intact.
    """

    def __init__(self, path: str | Path, *, source_id: str, study_id: str,
                 expected_sha256: str = ARCHIVE_SHA256, require_complete: bool = True,
                 maximum_bytes: int = 8_000_000, maximum_expanded_bytes: int = 10_000_000,
                 maximum_member_bytes: int = 2_000_000, maximum_lines: int = 20_000):
        if not all(isinstance(v, str) and v.strip() for v in (source_id, study_id, expected_sha256)):
            raise ValueError("Declare source, one-study grouping and archive SHA-256")
        for value in (maximum_bytes, maximum_expanded_bytes, maximum_member_bytes, maximum_lines):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Archive/text budgets must be positive integers")
        self.path, self.source_id, self.study_id = Path(path), source_id, study_id
        self.expected_sha256, self.require_complete = expected_sha256, require_complete
        self.maximum_bytes, self.maximum_expanded_bytes = maximum_bytes, maximum_expanded_bytes
        self.maximum_member_bytes, self.maximum_lines = maximum_member_bytes, maximum_lines
        self._archive = None

    def __enter__(self):
        if self.path.stat().st_size > self.maximum_bytes:
            raise ValueError("Archive compressed size exceeds budget")
        self.sha256 = file_sha256(self.path)
        if self.sha256 != self.expected_sha256:
            raise ValueError("Photocatalysis archive SHA-256 differs from receipt")
        self._archive = ZipFile(self.path)
        try:
            infos = self._archive.infolist()
            if (len(infos) > 100 or len({i.filename for i in infos}) != len(infos)
                    or sum(i.file_size for i in infos) > self.maximum_expanded_bytes):
                raise ValueError("Archive count/expanded size exceeds budget")
            members = []
            for info in infos:
                name = info.orig_filename
                if (name.startswith(("/", "\\")) or ".." in PurePosixPath(name).parts
                        or any(ord(char) < 32 for char in name)
                        or "\\" in name or ":" in name or stat.S_ISLNK(info.external_attr >> 16)
                        or info.flag_bits & 1 or info.file_size > self.maximum_member_bytes
                        or info.file_size / max(1, info.compress_size) > 2000):
                    raise ValueError("Unsafe or oversized source ZIP member")
                if info.is_dir():
                    continue
                payload = self._archive.read(info.filename)  # Native ZIP CRC check.
                members.append(PhotocatalysisMember(info.filename, len(payload),
                    hashlib.sha256(payload).hexdigest(), f"{info.CRC:08x}"))
            self.members = tuple(members)
            self.text_members = tuple(item for item in members if item.name.endswith(".txt"))
            names = {item.name for item in self.text_members}
            if names - set(LAYOUTS) or (self.require_complete and names != set(LAYOUTS)):
                raise ValueError("Archive text-member schema differs from reviewed collection")
            self.duplicate_groups = tuple(tuple(item.name for item in members if item.sha256 == digest)
                for digest in sorted({item.sha256 for item in members})
                if sum(item.sha256 == digest for item in members) > 1)
            return self
        except Exception:
            self._archive.close()
            self._archive = None
            raise

    def __exit__(self, *args):
        self._archive.close()
        self._archive = None
        if file_sha256(self.path) != self.sha256:
            raise ValueError("Photocatalysis archive changed during decoding")

    def _rows(self, name):
        if self._archive is None:
            raise ValueError("Consume text observations inside the source context")
        member = next((m for m in self.text_members if m.name == name), None)
        if member is None:
            raise ValueError("Declare an acquired reviewed text member")
        payload = self._archive.read(name)
        if hashlib.sha256(payload).hexdigest() != member.sha256:
            raise ValueError("Member snapshot changed")
        try:
            text, encoding = payload.decode("utf-8-sig"), "utf-8-sig"
        except UnicodeDecodeError:
            text, encoding = payload.decode("cp1252"), "cp1252-explicit-fallback"
        lines = text.splitlines()
        if len(lines) > self.maximum_lines or any(len(line) > 32_768 for line in lines):
            raise ValueError("Text line count/width exceeds budget")
        rows = tuple(tuple(line.split("\t")) for line in lines)
        header_count, columns = LAYOUTS[name]
        if len(rows) <= header_count or any(len(row) != columns for row in rows):
            raise ValueError("Native tabular line/column schema differs")
        return member, rows, encoding

    def schema(self, name) -> PhotocatalysisSchema:
        member, rows, encoding = self._rows(name)
        header_count, columns = LAYOUTS[name]
        headers = rows[:header_count]
        definitions = tuple(PhotocatalysisColumn(i + 1, tuple(row[i] for row in headers),
            Variable(f"column_{i+1}", "reported_numeric", "source_unit_unresolved",
                     f"{self.source_id}|{member.sha256}|{name}|source-column-{i+1}; physical mapping not assumed"),
            _origin(name, headers, i)) for i in range(columns))
        return PhotocatalysisSchema(member, headers, definitions, header_count + 1,
            len(rows), encoding, _role(name),
            "No automatic axes sharing, sample relabelling, normalization or physical unit borrowing")

    def iter_blocks(self, name: str, *, block_rows: int = 512, first_line: int | None = None,
                    last_line: int | None = None) -> Iterator[PhotocatalysisBlock]:
        if isinstance(block_rows, bool) or not isinstance(block_rows, int) or not 1 <= block_rows <= 2048:
            raise ValueError("block_rows must be an integer in [1, 2048]")
        schema = self.schema(name)
        _, rows, _ = self._rows(name)
        first = schema.first_data_line if first_line is None else first_line
        last = schema.last_data_line if last_line is None else last_line
        if (any(isinstance(v, bool) or not isinstance(v, int) for v in (first, last))
                or first < schema.first_data_line or last < first or last > schema.last_data_line):
            raise ValueError("Source line window lies outside the data region")
        for start in range(first, last + 1, block_rows):
            stop = min(start + block_rows, last + 1)
            source_lines = tuple(range(start, stop))
            raw = rows[start - 1:stop - 1]
            values = np.full((len(raw), len(schema.columns)), np.nan)
            reasons = []
            for i, row in enumerate(raw):
                problems = []
                for j, original in enumerate(row):
                    token = original.strip()
                    if not token:
                        problem = "source_blank"
                    elif token == "--":
                        problem = "source_placeholder"
                    elif _NUMERIC.fullmatch(token):
                        values[i, j] = float(token)
                        problem = "" if math.isfinite(values[i, j]) else "source_nonfinite"
                    else:
                        problem = "categorical_or_unresolved_text"
                    problems.append(problem)
                reasons.append(tuple(problems))
            table = ObservationTable(values, tuple(c.variable for c in schema.columns), np.isfinite(values),
                tuple(f"{self.source_id}|{self.sha256}|{name}|{schema.member.sha256}|line-{line}"
                      for line in source_lines), (self.study_id,) * len(raw),
                tuple(c.origin for c in schema.columns), self.source_id,
                (("profile", PROFILE_ID), ("archive_sha256", self.sha256), ("member", name),
                 ("member_sha256", schema.member.sha256), ("source_equivalence_id", schema.member.sha256),
                 ("header_lines", str(schema.first_data_line - 1)), ("encoding", schema.encoding),
                 ("source_role", schema.source_role), ("axis_status", schema.axis_status),
                 ("replicate_status", "one study; duplicate members and reused controls are not independent replicates")))
            yield PhotocatalysisBlock(table, schema, source_lines, raw, tuple(reasons))


@dataclass(frozen=True, slots=True)
class PhotocatalysisMappingEvidence:
    member_sha256: str
    source_column: int
    source_unit: str
    primary_source_id: str
    primary_locator: str
    evidence_id: str
    review_status: str = "candidate_unverified"
    catalyst_mass_basis_id: str = ""
    condition_source_id: str = ""

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() for v in (self.member_sha256,
                self.source_unit, self.primary_source_id, self.primary_locator, self.evidence_id)):
            raise ValueError("Source/member/column/unit/primary locator and evidence identity are required")
        if isinstance(self.source_column, bool) or not isinstance(self.source_column, int) or self.source_column < 1:
            raise ValueError("Mapping source column must be a positive integer")
        if self.review_status not in ("candidate_unverified", "caller_reviewed"):
            raise ValueError("Mapping review status must remain explicit")

    def require(self, block, column, unit):
        if (self.review_status != "caller_reviewed" or self.member_sha256 != block.schema.member.sha256
                or self.source_column != column or self.source_unit != unit):
            raise ValueError("Mapping is unreviewed or differs from its source member/column/unit")


@dataclass(frozen=True, slots=True)
class MappedPhotocatalysisBlock:
    source: PhotocatalysisBlock
    observations: ObservationTable
    mapping_evidence: PhotocatalysisMappingEvidence | None
    evidence_status: str
    sample_labels: tuple[str, ...]


def reported_h2_specific_rate(block: PhotocatalysisBlock, *, evidence: PhotocatalysisMappingEvidence):
    """Caller-evidenced Figure4a rate scaling; original fields and auxiliary column remain separate.

    A nonempty citation is not automatically verified by this software. No default
    mapping is activated from an inaccessible primary paper or figure filename.
    """
    if block.schema.member.name != "Figure4a.txt":
        raise ValueError("This specific-rate view is restricted to the reviewed Figure4a layout")
    evidence.require(block, 2, MOLAR_RATE_SOURCE_UNIT)
    if not evidence.catalyst_mass_basis_id.strip():
        raise ValueError("The catalyst mass normalization basis must be declared")
    source = block.observations
    values = source.values[:, 1:2] * MOLAR_RATE_FACTOR
    variable = Variable("reported_h2_specific_rate", "reported_h2_molar_specific_rate", MOLAR_RATE_SI_UNIT,
        f"{evidence.catalyst_mass_basis_id}; source mapping {evidence.evidence_id}; "
        f"conditions {evidence.condition_source_id or 'unresolved'}; collection/calibration unresolved")
    table = ObservationTable(values, (variable,), source.valid[:, 1:2], source.row_ids,
        source.experiment_ids, (Origin.RECONSTRUCTED,), source.source_id,
        source.context + (("mapping_status", "caller-reviewed unit mapping; not independent source qualification"),
            ("mapping_primary", evidence.primary_source_id), ("mapping_locator", evidence.primary_locator),
            ("mapping_evidence_id", evidence.evidence_id), ("mapping_source_column", "2"),
            ("parent_observations_sha256", source.content_sha256)))
    return MappedPhotocatalysisBlock(block, table, evidence,
        "caller-reviewed declaration; source primary evidence is not automatically verified", block.sample_labels)


def reported_aqy(block: PhotocatalysisBlock, *, source_column: int = 2,
                 evidence: PhotocatalysisMappingEvidence | None = None):
    """Native-header wavelength/AQY view; extra columns never inherit units silently."""
    if block.schema.member.name != "Figure4b.txt" or source_column not in (2, 3):
        raise ValueError("Declare Figure4b's first AQY column or explicitly reviewed candidate column")
    headers = block.schema.header_rows
    if (headers[0][0] != "Wavelength" or headers[1][0] != "nm" or headers[0][1] != "AQY"
            or headers[1][1] != "%" or headers[2][0] != "Name"):
        raise ValueError("Native wavelength/AQY header evidence differs")
    if source_column == 3 or evidence is not None:
        if evidence is None:
            raise ValueError("Column3 has no explicit percent unit; caller-reviewed primary evidence is required")
        evidence.require(block, source_column, "%")
    source = block.observations
    values = np.column_stack((source.values[:, 0] * 1e-9, source.values[:, source_column - 1] * .01))
    valid = np.column_stack((source.valid[:, 0] & (values[:, 0] > 0), source.valid[:, source_column - 1]))
    status = "native TXT header units only" if evidence is None else "caller-reviewed candidate-column declaration"
    variables = (Variable("wavelength", "wavelength", "m", "source Figure4b wavelength coordinate"),
        Variable("reported_AQY", "reported_apparent_quantum_yield", "1",
                 "source AQY percent; incident/absorbed photons/electron normalization/optical boundary unresolved"))
    table = ObservationTable(values, variables, valid, source.row_ids, source.experiment_ids,
        (Origin.RECONSTRUCTED,) * 2, source.source_id,
        source.context + (("mapping_status", status), ("mapping_source_column", str(source_column)),
            ("mapping_evidence_id", evidence.evidence_id if evidence else "native lines1-2:Wavelength/nm/AQY/%"),
            ("parent_observations_sha256", source.content_sha256)))
    return MappedPhotocatalysisBlock(block, table, evidence, status,
        (headers[2][source_column - 1],) * len(source.values))
