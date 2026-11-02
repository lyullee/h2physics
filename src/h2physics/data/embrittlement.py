"""Source-specific HE-Austenite compilation observations, not a fracture law.

Muhammad Faizan, https://doi.org/10.5281/zenodo.23107780, CC BY 4.0 data.
Original measurements, compilation-derived fields and conflicting composition
representations remain distinct. External observations are not bundled.
"""

import csv
import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from types import MappingProxyType

import numpy as np

from ..core import Origin, immutable_array
from ..observations import ObservationTable, Variable
from .pressure_peaking import file_sha256

PROFILE_ID = "he-austenite-23107780-profile-1"
MAIN_FILE = "he_austenite_v1.0.csv"
COMPOSITION_FILE = "compositions.csv"
MAP_FILE = "record_composition_map.csv"
FILES = (MAIN_FILE, COMPOSITION_FILE, MAP_FILE, "HE-Austenite_v1.0.xlsx", "README.md",
         "data_dictionary.md", "CONTRIBUTING.md", "LICENSE-DATA.txt", "requirements.txt")
DATASET_DOI = "10.5281/zenodo.23107780"
DATASET_VERSION = "23107780"
DATASET_LICENSE = "CC-BY-4.0"
PINNED_FILE_SHA256 = MappingProxyType({
    "requirements.txt": "9898258dad6808ea28b3387edacf81e2583bae79297c14d7c2954208ae54c8b2",
    "LICENSE-DATA.txt": "ad94dcb83d0ca380f780ba302961fe7a26837c5e78cd58aa34bc7d7d7a16335b",
    MAP_FILE: "358ede7737c7792b7aaf88b3362b0cc0e7c061c8d6c686b8bf07ae40486c3354",
    COMPOSITION_FILE: "07fbba9be6220e0613e98bfa889c0a7c43b98b7361d195584429cfc740e4f3b3",
    "data_dictionary.md": "019a988672bd7aaad0ada92eaa8b3d4965bb950db5aa70cae4d835beef4aaa86",
    "CONTRIBUTING.md": "1b2e941bc8e1a7de3a80eea7e26a85d92573712f870f1f0914af8777c7f0622e",
    "README.md": "600da68e995e2fa9bb33a3aa477ba9b651b1c438ca87a5f78499d282be0319af",
    "HE-Austenite_v1.0.xlsx": "c0e4a8ee6b20c3cf0db2af09447e9075f1b1c392353ee34fd62747be71c29f87",
    MAIN_FILE: "a392282dd1585b6f6d84ce96a931c827e78587310c0a59d6c1409843f89dc5b7",
})
HEADERS = tuple("record_id source_id source_short alloy heat material_family product_form is_weld zone "
    "weld_process filler_metal ferrite_number hydrogen_exposure h2_pressure_MPa hydrogen_content_wppm "
    "charging_time_h test_temperature_K test_temperature_C strain_rate_per_s test_type property_name "
    "reference_environment property_reference property_h2 relative_ratio embrittlement_flag C_wt_pct "
    "Si_wt_pct Mn_wt_pct Cr_wt_pct Ni_wt_pct Mo_wt_pct N_wt_pct Cu_wt_pct Nb_wt_pct Ti_wt_pct "
    "composition_basis composition_source ni_equivalent ni_equivalent_reported md30_calculated "
    "derived_assumptions derived verified notes".split())
ELEMENTS = ("C", "Si", "Mn", "Cr", "Ni", "Mo", "N", "Cu", "Nb", "Ti")
COMPOSITION_HEADERS = ("comp_key", "material_label", "composition_basis", "derive_nieq",
    "derive_md30", "composition_source", *ELEMENTS, "notes")
MAP_HEADERS = ("record_id", "comp_key")
PROPERTIES = ("reduction of area", "elongation", "tensile strength", "notched tensile strength",
              "plastic strain to failure")
NUMERIC_FIELDS = ("ferrite_number", "h2_pressure_MPa", "hydrogen_content_wppm", "charging_time_h",
    "test_temperature_K", "test_temperature_C", "strain_rate_per_s", "property_reference",
    "property_h2", "relative_ratio", *(e+"_wt_pct" for e in ELEMENTS), "ni_equivalent",
    "ni_equivalent_reported", "md30_calculated")

_PENDING_EMBRITTLEMENT_BLOCK_ISSUERS: set[object] = set()


def _source_row_identity(row):
    if row is None:
        return None
    return (row.filename, row.file_sha256, row.record_number, row.first_line,
            row.last_line, row.headers, row.cells)


def _embrittlement_block_fingerprint(block):
    digest = hashlib.sha256()
    digest.update(block.observations.content_sha256.encode("ascii"))
    for record in block.records:
        payload = repr((record.collection_source_id,
                        _source_row_identity(record.source),
                        _source_row_identity(record.linked_composition),
                        _source_row_identity(record.composition_mapping))).encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    digest.update(repr(block.invalid_reasons).encode("utf-8"))
    return digest.hexdigest()


def _number(text):
    if not text.strip():
        return math.nan, "source_blank"
    if text.strip() in {"--", "NA", "N/A"}:
        return math.nan, "source_placeholder"
    try:
        value = float(text)
    except ValueError:
        return math.nan, "source_nonnumeric"
    return value, "" if math.isfinite(value) else "source_nonfinite"


@dataclass(frozen=True, slots=True)
class CsvSourceRow:
    filename: str
    file_sha256: str
    record_number: int
    first_line: int
    last_line: int
    headers: tuple[str, ...]
    cells: tuple[str, ...]

    @property
    def fields(self):
        return MappingProxyType(dict(zip(self.headers, self.cells, strict=True)))

    @property
    def row_id(self):
        return (f"{self.filename}|{self.file_sha256}|record-{self.record_number}"
                f"|lines-{self.first_line}-{self.last_line}")


@dataclass(frozen=True, slots=True)
class CompositionDiscrepancy:
    field: str
    primary_csv_raw: str
    linked_composition_raw: str


@dataclass(frozen=True, slots=True)
class EmbrittlementRecord:
    source: CsvSourceRow
    collection_source_id: str
    linked_composition: CsvSourceRow | None
    composition_mapping: CsvSourceRow | None

    @property
    def fields(self):
        return self.source.fields

    @property
    def record_id(self):
        return self.source.cells[0]

    @property
    def row_id(self):
        return f"{self.collection_source_id}|{self.source.row_id}|{self.record_id}"

    @property
    def reported_source_id(self):
        """Bibliographic source label, not a specimen or independent experiment ID."""
        return self.fields["source_id"]

    @property
    def material_group_id(self):
        if self.linked_composition is None:
            return None
        return self.linked_composition.fields["comp_key"]

    @property
    def composition_discrepancies(self):
        if self.linked_composition is None:
            return ()
        problems = []
        for element in ELEMENTS:
            a, b = self.fields[element+"_wt_pct"], self.linked_composition.fields[element]
            x, rx = _number(a)
            y, ry = _number(b)
            if (bool(rx) != bool(ry)) or (not rx and not ry and x != y) or (rx and ry and a != b):
                problems.append(CompositionDiscrepancy(element, a, b))
        for field in ("composition_basis", "composition_source"):
            a, b = self.fields[field], self.linked_composition.fields[field]
            if a != b:
                problems.append(CompositionDiscrepancy(field, a, b))
        return tuple(problems)

    def numeric_role(self, field):
        values = self.fields
        if field == "relative_ratio":
            if values["property_reference"] and values["property_h2"]:
                return "compilation ratio of reported paired values; not independent measurement"
            if "relative_ratio" in values["derived"].split(";"):
                return "compilation-derived ratio without absolute pair; source loss context retained"
            return "source-reported ratio without absolute pair"
        if field == "ni_equivalent_reported":
            return "source-labelled reported index; actual completeness conflicts with dictionary; origin unresolved"
        if field in {"ni_equivalent", "md30_calculated"} or field in values["derived"]:
            return "compilation-derived; source assumptions and printed value retained"
        if field.endswith("_wt_pct"):
            return "primary CSV composition representation; " + (values["composition_basis"] or "basis unresolved")
        return "literature-extracted value in compilation; original experiment not revalidated"

    @property
    def issues(self):
        result = ["pressure_absolute_gauge_total_partial_purity_unresolved", "hydrogen_spin_unresolved",
                  "specimen_identity_and_replicate_count_unresolved", "fracture_mode_not_a_structured_observation"]
        if self.fields["hydrogen_exposure"] == "gaseous precharge":
            result.append("reported_exposure_pressure_is_not_automatically_test_pressure")
        if self.fields["property_name"] == "plastic strain to failure":
            result.append("plastic_strain_absolute_unit_unresolved")
        if self.composition_discrepancies:
            result.append("primary_and_linked_composition_disagree")
        if "pressure" in self.fields["derived"]:
            result.append("pressure_is_compilation_range_midpoint")
        if self.record_id == "SAND2012-ch2101-T3111-5":
            result.append("source_README_identifies_reuse_of_a_Caskey_measurement")
        return tuple(result)


def _property_units(property_name):
    if property_name in {"reduction of area", "elongation"}:
        return "1", .01, property_name.replace(" ", "_")+"_fraction"
    if property_name in {"tensile strength", "notched tensile strength"}:
        return "Pa", 1e6, property_name.replace(" ", "_")
    if property_name == "plastic strain to failure":
        return "source_unit_unresolved", 1., "plastic_strain_to_failure"
    raise ValueError("Declare one of the source's five property definitions")


def embrittlement_variables(property_name):
    unit, _, quantity = _property_units(property_name)
    return (
        Variable("ferrite_number", "reported_ferrite_number", "1", "source FN index; not ferrite volume fraction"),
        Variable("exposure_pressure_pa", "reported_exposure_pressure", "Pa",
            "source gas exposure MPa; absolute/gauge,total/partial,H2 purity and exposure/test role unresolved"),
        Variable("material_hydrogen_mass_fraction", "reported_material_hydrogen_mass_fraction", "1",
            "source wt ppm; total/diffusible/trapped and measurement method unresolved"),
        Variable("charging_duration_s", "reported_charging_duration", "s", "precharge duration, not a test clock"),
        Variable("test_temperature_k_reported", "reported_test_temperature", "K", "source K field retained without Celsius repair"),
        Variable("test_temperature_k_from_C", "reported_test_temperature_from_C", "K", "source C field +273.15; separate from source K"),
        Variable("nominal_strain_rate_per_s", "reported_nominal_strain_rate", "1/s", "nominal source value; local/plastic rate unresolved"),
        *(Variable(name, "reported_"+quantity, unit,
            f"{property_name}; source same-study paired {role}; gauge/notch/loading definition in source context")
          for name, role in (("property_reference", "reference environment"), ("property_h2", "in/after H2"))),
        Variable("relative_ratio", "reported_relative_"+property_name.replace(" ", "_"), "1",
            "H2/reference of same reported property; source may derive from loss or report ratio alone"),
        *(Variable(e+"_mass_fraction_primary", "reported_primary_csv_"+e+"_mass_fraction", "1",
            "source wt%; primary CSV only, linked composition remains separate; blank is not zero") for e in ELEMENTS),
        Variable("nickel_equivalent_index", "compilation_derived_nickel_equivalent_index", "1",
            "source six-element weighted wt%-index scaled by.01; not nickel concentration"),
        Variable("nickel_equivalent_reported_index", "source_labelled_reported_nickel_equivalent_index", "1",
            "source wt%-index scaled by.01; completeness/provenance conflicts, not independent target"),
        Variable("md30_index_k", "compilation_derived_martensite_stability_temperature_index", "K",
            "source empirical Angel index C+273.15; assumptions preserved; not measured test/phase-transition temperature"),
    )


@dataclass(frozen=True, slots=True)
class EmbrittlementBlock:
    observations: ObservationTable
    records: tuple[EmbrittlementRecord, ...]
    invalid_reasons: tuple[tuple[str, ...], ...]
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _fingerprint: str = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_EMBRITTLEMENT_BLOCK_ISSUERS:
            raise ValueError("Embrittlement blocks are issued by the pinned collection reader")
        _PENDING_EMBRITTLEMENT_BLOCK_ISSUERS.remove(self._issuer_token)
        records = tuple(self.records)
        reasons = tuple(tuple(row) for row in self.invalid_reasons)
        if type(self.observations) is not ObservationTable:
            raise TypeError("An embrittlement block must retain its ObservationTable")
        if not records or any(type(record) is not EmbrittlementRecord for record in records):
            raise ValueError("A block must retain one source record per observation row")
        if self.observations.row_ids != tuple(record.row_id for record in records):
            raise ValueError("Observation row IDs must match the retained source records in order")
        expected_shape = (len(records), len(NUMERIC_FIELDS))
        if self.observations.values.shape != expected_shape:
            raise ValueError("Observation values must align with source records and numeric fields")
        if self.observations.valid.shape != expected_shape:
            raise ValueError("Observation validity masks must align with values")
        if len(reasons) != len(records) or any(
            len(row) != len(NUMERIC_FIELDS)
            or any(not isinstance(reason, str) for reason in row)
            for row in reasons
        ):
            raise ValueError("Invalid-reason entries must align with each source numeric field")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "invalid_reasons", reasons)
        object.__setattr__(self, "_fingerprint", _embrittlement_block_fingerprint(self))

    def require_current(self):
        if _embrittlement_block_fingerprint(self) != self._fingerprint:
            raise ValueError("Embrittlement observations or source-record binding changed after capture")
        return self

    @property
    def numeric_source_fields(self):
        """Original field for each SI/explicit-unresolved observation column."""
        return NUMERIC_FIELDS

    def as_time_series(self):
        raise ValueError("A compiled paired test condition/property is not a time history")


@dataclass(frozen=True, slots=True)
class PairedPropertyCheck:
    row_ids: tuple[str, ...]
    calculated_ratio: np.ndarray
    reported_ratio: np.ndarray
    residual: np.ndarray
    available: np.ndarray
    within_tolerance: np.ndarray
    tolerance: float

    def __post_init__(self):
        row_ids = tuple(self.row_ids)
        count = len(row_ids)
        if not count or any(not isinstance(value, str) or not value.strip() for value in row_ids):
            raise ValueError("Paired-property results need nonempty source row identities")
        if len(set(row_ids)) != count:
            raise ValueError("Paired-property source row identities must be unique")
        tolerance = float(self.tolerance)
        if isinstance(self.tolerance, (bool, np.bool_)) or not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError("Paired-property tolerance must be finite and nonnegative")
        for name in ("calculated_ratio", "reported_ratio", "residual"):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != (count,):
                raise ValueError(f"Paired-property {name} must align with source rows")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        for name in ("available", "within_tolerance"):
            values = np.array(getattr(self, name), dtype=bool, copy=True)
            if values.shape != (count,):
                raise ValueError(f"Paired-property {name} must align with source rows")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        expected_residual = self.calculated_ratio - self.reported_ratio
        if not np.allclose(self.residual, expected_residual, rtol=2e-12, atol=2e-12, equal_nan=True):
            raise ValueError("Paired-property residuals must equal calculated minus reported ratios")
        if np.any(self.available & (
            ~np.isfinite(self.calculated_ratio)
            | ~np.isfinite(self.reported_ratio)
            | ~np.isfinite(self.residual)
        )):
            raise ValueError("Available paired-property checks require finite source values")
        expected_within = self.available & (np.abs(self.residual) <= tolerance)
        if not np.array_equal(self.within_tolerance, expected_within):
            raise ValueError("Tolerance flags must match the declared residual budget")
        object.__setattr__(self, "row_ids", row_ids)
        object.__setattr__(self, "tolerance", tolerance)


def paired_property_check(block: EmbrittlementBlock, *, tolerance: float = .002):
    """Same-export arithmetic check only; never independent model validation."""
    if type(block) is not EmbrittlementBlock:
        raise TypeError("Paired-property checks require a collection-issued block")
    block.require_current()
    if isinstance(tolerance, (bool, np.bool_)) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Declare a finite nonnegative ratio comparison tolerance")
    table = block.observations
    reference, reference_valid = table.column("property_reference")
    exposed, exposed_valid = table.column("property_h2")
    reported, ratio_valid = table.column("relative_ratio")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        calculated = exposed/reference
        residual = calculated-reported
    available = reference_valid & exposed_valid & ratio_valid & (reference > 0) & np.isfinite(residual)
    return PairedPropertyCheck(table.row_ids, calculated, reported, residual, available,
                               available & (abs(residual) <= tolerance), float(tolerance))


class EmbrittlementCollection:
    """Read-only bounded CSV profile with a separately retained composition join.

    Numeric arrays are block bounded. Record/metadata storage has explicit file,
    field and row limits. No source program, formula or macro is executed.
    """

    def __init__(self, directory: str | Path, *, source_id: str,
                 expected_sha256: Mapping[str, str], require_complete: bool = True,
                 maximum_file_bytes: int = 2_000_000, maximum_rows: int = 5000):
        if not isinstance(source_id, str) or source_id != DATASET_DOI:
            raise ValueError("Collection source identity must match the pinned HE-Austenite DOI")
        expected = dict(expected_sha256)
        required = set(FILES if require_complete else (MAIN_FILE, COMPOSITION_FILE, MAP_FILE))
        if not required <= set(expected) or set(expected)-set(FILES):
            raise ValueError("Declare exact hashes for every admitted source file")
        if any(PINNED_FILE_SHA256.get(name) != digest for name, digest in expected.items()):
            raise ValueError("Source hashes differ from the reviewed version-pinned file manifest")
        for value in (maximum_file_bytes, maximum_rows):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Explicit source file/row budgets must be positive integers")
        self.directory, self.source_id = Path(directory), source_id
        self.expected_sha256 = MappingProxyType(expected)
        self.maximum_file_bytes, self.maximum_rows = maximum_file_bytes, maximum_rows
        self._open = False

    @classmethod
    def from_receipt(cls, directory: str | Path, receipt: Mapping, *,
                     require_complete: bool = True, maximum_file_bytes: int = 2_000_000,
                     maximum_rows: int = 5000):
        """Build a pinned collection from the repository's parsed acquisition receipt.

        The caller parses the receipt format and supplies the external data directory;
        this method performs no discovery, download, or path inference. Receipt fields
        are validated against this reviewed dataset profile before any files are read.
        """
        if not isinstance(receipt, Mapping):
            raise TypeError("Pass a parsed dataset receipt mapping")
        if (receipt.get("doi") != DATASET_DOI
                or receipt.get("version") != DATASET_VERSION
                or receipt.get("license_id") != DATASET_LICENSE
                or receipt.get("rights_permitted") is not True):
            raise ValueError("Receipt identity or rights do not match the reviewed data profile")
        entries = receipt.get("files")
        if not isinstance(entries, (list, tuple)):
            raise ValueError("Receipt must contain its acquired file entries")
        hashes = {}
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError("Each acquired-file receipt entry must be a mapping")
            name, digest = entry.get("name"), entry.get("sha256")
            if (not isinstance(name, str) or not isinstance(digest, str) or name in hashes
                    or entry.get("status") != "acquired"):
                raise ValueError("Receipt filenames and SHA-256 values must be unique strings")
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Receipt SHA-256 values must be lowercase hexadecimal digests")
            hashes[name] = digest
        required = set(FILES if require_complete else (MAIN_FILE, COMPOSITION_FILE, MAP_FILE))
        if not required <= set(hashes) or set(hashes) - set(FILES):
            raise ValueError("Receipt acquired-file set differs from the reviewed profile")
        return cls(directory, source_id=receipt["doi"], expected_sha256=hashes,
                   require_complete=require_complete, maximum_file_bytes=maximum_file_bytes,
                   maximum_rows=maximum_rows)

    def __enter__(self):
        for name, expected in self.expected_sha256.items():
            path = self.directory/name
            if path.stat().st_size > self.maximum_file_bytes or file_sha256(path) != expected:
                raise ValueError("Source file budget/SHA-256 differs from declared receipt")
        self._open = True
        try:
            compositions = tuple(self._csv(COMPOSITION_FILE, COMPOSITION_HEADERS))
            mapping = tuple(self._csv(MAP_FILE, MAP_HEADERS))
            self.compositions = compositions
            self.composition_mapping = mapping
            lookup = self._unique(compositions, "comp_key")
            maps = self._unique(mapping, "record_id")
            if any(row.fields["comp_key"] not in lookup for row in mapping):
                raise ValueError("Composition mapping refers to an absent original key")
            raw = tuple(self._csv(MAIN_FILE, HEADERS))
            records = self._unique(raw, "record_id")
            if set(maps)-set(records):
                raise ValueError("Composition mapping refers to an absent original record")
            self.records = tuple(EmbrittlementRecord(row, self.source_id,
                lookup[maps[row.cells[0]].fields["comp_key"]] if row.cells[0] in maps else None,
                maps.get(row.cells[0])) for row in raw)
            if any(r.fields["property_name"] not in PROPERTIES for r in self.records):
                raise ValueError("Source contains an unreviewed property/unit definition")
            return self
        except Exception:
            self._open = False
            raise

    def __exit__(self, *args):
        self._open = False
        if any(file_sha256(self.directory/name) != expected for name, expected in self.expected_sha256.items()):
            raise ValueError("Compilation source changed during decoding")

    def _csv(self, name, headers):
        with (self.directory/name).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            if tuple(next(reader)) != headers:
                raise ValueError("Source CSV header identity differs from reviewed schema")
            last_line = reader.line_num
            for number, cells in enumerate(reader, 2):
                if number > self.maximum_rows+1 or len(cells) != len(headers) or any(len(c) > 32768 for c in cells):
                    raise ValueError("Native CSV record/column/field budget differs")
                yield CsvSourceRow(name, self.expected_sha256[name], number, last_line+1,
                                   reader.line_num, headers, tuple(cells))
                last_line = reader.line_num

    @staticmethod
    def _unique(rows, key):
        result = {}
        for row in rows:
            value = row.fields[key]
            if not value or value != value.strip() or value in result:
                raise ValueError("Original CSV identifiers must be nonempty and unique")
            result[value] = row
        return result

    def composition_observations(self, composition: CsvSourceRow):
        if not self._open or not any(composition is row for row in self.compositions):
            raise ValueError("Select an actual linked composition inside its source context")
        values = np.array([_number(composition.fields[e])[0]*.01 for e in ELEMENTS])[None, :]
        variables = tuple(Variable(e, "reported_linked_"+e+"_mass_fraction", "1",
            "linked composition representation; "+composition.fields["composition_basis"]+"; not primary CSV")
            for e in ELEMENTS)
        return ObservationTable(values, variables, np.isfinite(values) & (values >= 0) & (values <= 1),
            (self.source_id+"|"+composition.row_id+"|"+composition.fields["comp_key"],),
            (self.source_id+"/dependent-compilation",), (Origin.RECONSTRUCTED,)*len(ELEMENTS), self.source_id,
            (("profile", PROFILE_ID), ("comp_key", composition.fields["comp_key"]),
             ("material_label", composition.fields["material_label"]),
             ("composition_source", composition.fields["composition_source"])))

    def iter_blocks(self, property_name: str, *, reference_environment: str | None = None,
                    zone: str | None = None, hydrogen_exposure: str | None = None, block_rows: int = 64):
        if not self._open:
            raise ValueError("Consume observations inside the source context")
        if isinstance(block_rows, bool) or not isinstance(block_rows, int) or not 1 <= block_rows <= 512:
            raise ValueError("block_rows must be an integer in [1,512]")
        variables = embrittlement_variables(property_name)
        _, property_factor, _ = _property_units(property_name)
        selected = tuple(r for r in self.records if r.fields["property_name"] == property_name
            and (reference_environment is None or r.fields["reference_environment"] == reference_environment)
            and (zone is None or r.fields["zone"] == zone)
            and (hydrogen_exposure is None or r.fields["hydrogen_exposure"] == hydrogen_exposure))
        factors = (1., 1e6, 1e-6, 3600., 1., 1., 1., property_factor, property_factor, 1.,
                   *((.01,)*10), .01, .01, 1.)
        for start in range(0, len(selected), block_rows):
            records = selected[start:start+block_rows]
            values = np.full((len(records), len(NUMERIC_FIELDS)), np.nan)
            reasons = []
            for i, record in enumerate(records):
                invalid = []
                for j, (field, factor) in enumerate(zip(NUMERIC_FIELDS, factors, strict=True)):
                    value, reason = _number(record.fields[field])
                    values[i, j] = value*factor + (273.15 if field in {"test_temperature_C", "md30_calculated"} else 0.)
                    if not reason and not math.isfinite(values[i, j]):
                        reason = "unit_conversion_nonfinite"
                    if not reason and field not in {"test_temperature_C", "md30_calculated"} and value < 0:
                        reason = "source_negative_physical_field"
                    if not reason and field in {"test_temperature_K", "test_temperature_C"} and values[i, j] <= 0:
                        reason = "source_nonpositive_temperature"
                    if not reason and field.endswith("_wt_pct") and value > 100:
                        reason = "source_composition_above_mass_fraction_one"
                    invalid.append(reason)
                reasons.append(tuple(invalid))
            valid = np.isfinite(values) & np.array([[not reason for reason in row] for row in reasons])
            origins = tuple(Origin.UNRESOLVED if field == "ni_equivalent_reported" or
                (property_name == "plastic strain to failure" and field in {"property_reference", "property_h2"})
                else Origin.RECONSTRUCTED for field in NUMERIC_FIELDS)
            table = ObservationTable(values, variables, valid, tuple(r.row_id for r in records),
                (self.source_id+"/dependent-compilation",)*len(records), origins, self.source_id,
                (("profile", PROFILE_ID), ("primary_file_sha256", self.expected_sha256[MAIN_FILE]),
                 ("property_name", property_name), ("independence", "one dependent compilation; bibliographic labels/materials are not independent specimens"),
                 ("source_version", "pinned Zenodo record; filenames v1.0 versus internal README/workbook v0.2 retained"),
                 ("pressure_basis", "absolute/gauge,total/partial,H2 purity and precharge/test distinction unresolved"),
                 ("units", "property-specific; plastic-strain absolute unit unresolved; no index used as measured fracture law")))
            token = object()
            _PENDING_EMBRITTLEMENT_BLOCK_ISSUERS.add(token)
            try:
                block = EmbrittlementBlock(table, records, tuple(reasons), _issuer_token=token)
            except Exception:
                _PENDING_EMBRITTLEMENT_BLOCK_ISSUERS.discard(token)
                raise
            yield block
