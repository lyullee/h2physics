"""Source-bound OEDI fatigue observations with reconciled workbook conditions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import numpy as np

from ..core import Origin, finite
from ..observations import ObservationTable, Variable

SOURCE_ID = "oedi-hydrogen-materials:low-alloy-tempered-martensite-1211san11fat.xlsx"
SOURCE_MD5 = "300ff2f91554a9dc9f52956ecc5895cf"
SOURCE_SHA256 = "1dcfb0500aa4fa21f32111785a71c5025f9cf77c07f88b414f051a2f42f4a33a"
EXPECTED_PRESSURE_MPA = 45.0
RELATED_RECORD_PRESSURE_MPA = 4.5
EXPECTED_SHEET = "Mechanical Properties-Fatigue"
_MAX_WORKBOOK_BYTES = 10_000_000
SOURCE_URL = "https://data.openei.org/files/277/1211san11fat.xlsx"
SOURCE_PUBLISHER = "National Renewable Energy Laboratory; Sandia National Laboratories data contact"
SOURCE_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
CONDITION_AUTHORITY_URL = (
    "https://www.sandia.gov/research/publications/details/"
    "fracture-and-fatigue-tolerant-steel-pressure-vessels-for-gaseous-hydrogen-2010-12-01/"
)
RELATED_CONDITION_URL = "https://hymatbase.stfc.ac.uk/records/pytvh-6n886"
SERIES_COLUMNS = ((5, 6), (8, 9), (11, 12), (14, 15), (17, 18))
SERIES_ENVIRONMENTS = ("H2", "H2", "H2", "H2", "air")
FATIGUE_VARIABLES = (
    Variable("stress_intensity_factor_range", "stress_intensity_factor", "Pa m^0.5"),
    Variable("crack_growth_rate", "crack_growth_rate", "m/cycle"),
)
_PENDING_SERIES_ISSUERS: set[object] = set()
_PENDING_DATASET_ISSUERS: set[object] = set()


def _issue_fatigue_series(**values):
    token = object()
    _PENDING_SERIES_ISSUERS.add(token)
    try:
        return FatigueGrowthSeries(**values, _issuer_token=token)
    except Exception:
        _PENDING_SERIES_ISSUERS.discard(token)
        raise


def _issue_oedi_dataset(**values):
    token = object()
    _PENDING_DATASET_ISSUERS.add(token)
    try:
        return OediFatigueDataset(**values, _issuer_token=token)
    except Exception:
        _PENDING_DATASET_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class FatigueGrowthSeries:
    """One reported delta-K/crack-growth-rate series and its test conditions."""

    series_id: str
    environment: str
    pressure_mpa: float
    temperature_label: str
    orientation: str
    test_method: str
    r_ratio: float
    frequency_hz: float
    reference: str
    source_columns: tuple[int, int]
    observations: ObservationTable
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SERIES_ISSUERS:
            raise ValueError("Use the checksum-validating OEDI workbook loader to issue fatigue series")
        _PENDING_SERIES_ISSUERS.remove(self._issuer_token)
        if (not isinstance(self.series_id, str) or not self.series_id.strip()
                or not isinstance(self.environment, str) or self.environment not in {"H2", "air"}):
            raise ValueError("Declare an explicit fatigue-series identity and environment")
        for name in ("temperature_label", "orientation", "test_method", "reference"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"Fatigue condition {name} must retain its source text")
        for name in ("pressure_mpa", "r_ratio", "frequency_hz"):
            value = finite(getattr(self, name), name)
            object.__setattr__(self, name, value)
        if self.pressure_mpa < 0 or not 0 <= self.r_ratio < 1 or self.frequency_hz <= 0:
            raise ValueError("Fatigue-series pressure, R-ratio or frequency is out of range")
        if type(self.observations) is not ObservationTable:
            raise TypeError("Fatigue series must retain an ObservationTable")
        columns = tuple(self.source_columns)
        if (len(columns) != 2 or any(isinstance(value, (bool, np.bool_))
                                     or not isinstance(value, (int, np.integer)) or value < 1
                                     for value in columns)
                or columns[1] != columns[0] + 1):
            raise ValueError("Retain an adjacent one-based source workbook column pair")
        columns = tuple(int(value) for value in columns)
        object.__setattr__(self, "source_columns", columns)
        if self.observations.source_id != SOURCE_ID or self.observations.variables != FATIGUE_VARIABLES:
            raise ValueError("Fatigue observations must preserve this workbook source and SI schema")
        if not self.observations.row_ids:
            raise ValueError("Each fatigue series must preserve at least one workbook observation")
        if self.observations.origins != (Origin.MEASURED, Origin.MEASURED):
            raise ValueError("Workbook observations must retain their measured origin")
        if self.observations.experiment_ids != (self.series_id,) * len(self.observations.row_ids):
            raise ValueError("Every source observation must retain the exact fatigue-series identity")
        context = dict(self.observations.context)
        required_context = {
            "source_sha256": SOURCE_SHA256,
            "source_md5": SOURCE_MD5,
            "source_sheet": EXPECTED_SHEET,
            "source_columns_one_based": f"{columns[0]},{columns[1]}",
            "test_method": self.test_method,
        }
        if any(context.get(key) != value for key, value in required_context.items()):
            raise ValueError("Observation context differs from the pinned workbook series")
        prefix = f"{SOURCE_ID}:row-"
        try:
            source_rows = tuple(int(row.removeprefix(prefix)) for row in self.observations.row_ids)
        except ValueError as error:
            raise ValueError("Fatigue rows must retain positive one-based workbook row IDs") from error
        if (any(not row.startswith(prefix) for row in self.observations.row_ids)
                or any(row < 14 for row in source_rows)
                or any(b <= a for a, b in zip(source_rows[:-1], source_rows[1:], strict=True))
                or context.get("source_rows_one_based") != ",".join(map(str, source_rows))):
            raise ValueError("Source row IDs and retained workbook-row metadata must agree")
        if not context.get("environment_label") or not context.get("reported_environment"):
            raise ValueError("Preserve the workbook's original environment labels")


@dataclass(frozen=True, slots=True)
class OediFatigueDataset:
    """Workbook observations with a retained, evidence-resolved pressure discrepancy."""

    source_file: str
    source_url: str
    source_md5: str
    source_sha256: str
    publisher: str
    license_id: str
    license_url: str
    material: str
    material_form: str
    temper: str
    condition_metadata_discrepancy: str
    condition_resolution: str
    condition_authority_url: str
    related_condition_source_url: str
    condition_identity_admitted: bool
    series: tuple[FatigueGrowthSeries, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_DATASET_ISSUERS:
            raise ValueError("Use load_oedi_4130x_fatigue to issue a file-bound dataset")
        _PENDING_DATASET_ISSUERS.remove(self._issuer_token)
        series = tuple(self.series)
        if (self.source_file != "low-alloy-tempered-martensite-1211san11fat.xlsx"
                or self.source_url != SOURCE_URL or self.publisher != SOURCE_PUBLISHER):
            raise ValueError("Dataset filename, public URL and attribution must match the pinned source")
        if self.source_md5 != SOURCE_MD5 or self.source_sha256 != SOURCE_SHA256:
            raise ValueError("OEDI dataset object must retain both pinned source checksums")
        if self.license_id != "CC-BY-4.0" or self.license_url != SOURCE_LICENSE_URL:
            raise ValueError("Preserve the source license and its URL")
        if (not isinstance(self.condition_metadata_discrepancy, str)
                or not self.condition_metadata_discrepancy.strip()
                or not isinstance(self.condition_resolution, str)
                or not self.condition_resolution.strip()):
            raise ValueError("Preserve the discrepancy and the evidence-based resolution")
        if (self.condition_authority_url != CONDITION_AUTHORITY_URL
                or self.related_condition_source_url != RELATED_CONDITION_URL):
            raise ValueError("Preserve both the condition authority and discrepant metadata record")
        if self.material != "4130X" or "4.5 MPa" not in self.condition_metadata_discrepancy:
            raise ValueError("Retain the reviewed material identity and contradictory catalog condition")
        if self.condition_identity_admitted is not True:
            raise ValueError("This source file's tested condition is identified by primary evidence")
        if len(series) != 5 or any(type(item) is not FatigueGrowthSeries for item in series):
            raise ValueError("This workbook receipt requires its five source fatigue series")
        expected_ids = tuple(f"oedi-4130x-{env.lower()}-{index}" for index, env in enumerate(SERIES_ENVIRONMENTS, 1))
        expected_pressures = (EXPECTED_PRESSURE_MPA,) * 4 + (0.1,)
        if (tuple(item.series_id for item in series) != expected_ids
                or tuple(item.environment for item in series) != SERIES_ENVIRONMENTS
                or tuple(item.source_columns for item in series) != SERIES_COLUMNS
                or tuple(item.pressure_mpa for item in series) != expected_pressures):
            raise ValueError("Series order, source columns or reported pressure differs from the pinned workbook")
        object.__setattr__(self, "series", series)


def _value(sheet, row: int, column: int):
    return sheet.cell(row=row, column=column).value


def _text(sheet, row: int, column: int, *, required: bool = True) -> str:
    value = _value(sheet, row, column)
    if value is None or not str(value).strip():
        if required:
            raise ValueError(f"Missing workbook metadata at {sheet.title}!R{row}C{column}")
        return ""
    return str(value).strip()


def _number(sheet, row: int, column: int) -> float:
    value = _value(sheet, row, column)
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Expected numeric workbook cell at {sheet.title}!R{row}C{column}") from error
    if not np.isfinite(result):
        raise ValueError(f"Non-finite workbook value at {sheet.title}!R{row}C{column}")
    return result


def load_oedi_4130x_fatigue(path: Path) -> OediFatigueDataset:
    """Read the pinned public workbook without fitting a constitutive relation.

    The source workbook labels four hydrogen series at 45 MPa; an associated
    HyMatBase entry labels the same file bytes at 4.5 MPa. Exact MD5 identity,
    the workbook's source cells and a Sandia study record support 45 MPa as the
    observation condition. The discrepancy remains in the returned metadata.
    """
    from openpyxl import load_workbook

    path = Path(path)
    if path.stat().st_size > _MAX_WORKBOOK_BYTES:
        raise ValueError("OEDI workbook exceeds the declared size limit")
    raw_bytes = path.read_bytes()
    actual_hash = hashlib.sha256(raw_bytes).hexdigest()
    if actual_hash != SOURCE_SHA256:
        raise ValueError("OEDI workbook SHA-256 differs from the pinned source receipt")
    actual_md5 = hashlib.md5(raw_bytes, usedforsecurity=False).hexdigest()
    if actual_md5 != SOURCE_MD5:
        raise ValueError("OEDI workbook bytes differ from the independently listed file identity")
    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError("OEDI workbook ZIP integrity check failed")
            if sum(item.file_size for item in archive.infolist()) > 50_000_000:
                raise ValueError("OEDI workbook expanded content exceeds the declared limit")
        workbook = load_workbook(path, read_only=True, data_only=False)
    except (BadZipFile, OSError) as error:
        raise ValueError("OEDI workbook is not a readable XLSX archive") from error

    try:
        required_sheets = {"Material", "Environment", EXPECTED_SHEET}
        if not required_sheets.issubset(workbook.sheetnames):
            raise ValueError("OEDI workbook sheet layout differs from the audited source")
        material = workbook["Material"]
        environment_sheet = workbook["Environment"]
        fatigue = workbook[EXPECTED_SHEET]
        material_name = _text(material, 1, 1)
        material_form = _text(material, 3, 1)
        temper = _text(material, 4, 1)
        groups = []
        for index, (first_column, second_column) in enumerate(SERIES_COLUMNS, start=1):
            environment_label = _text(fatigue, 5, first_column)
            descriptor = _text(fatigue, 5, first_column + 1)
            if descriptor.startswith("="):
                # Formula expression is retained rather than evaluated or used
                # to infer the environmental value.
                environment = "reported formula: " + descriptor
            else:
                environment = descriptor
            method = _text(fatigue, 7, first_column)
            test_method = _text(fatigue, 7, first_column + 1)
            r_ratio = _number(fatigue, 8, first_column + 1)
            frequency = _number(fatigue, 9, first_column + 1)
            reference = _text(fatigue, 10, first_column + 1, required=False)
            x_header = _text(fatigue, 12, first_column)
            y_header = _text(fatigue, 12, first_column + 1)
            if "K" not in x_header or "da/dN" not in y_header:
                raise ValueError("OEDI fatigue columns do not match the audited delta-K schema")
            records = []
            for source_row in range(14, fatigue.max_row + 1):
                x, y = _value(fatigue, source_row, first_column), _value(
                    fatigue, source_row, first_column + 1
                )
                if x is None and y is None:
                    continue
                records.append((source_row, x, y))
            if not records:
                raise ValueError(f"OEDI fatigue series {index} contains no observations")
            values = np.array(
                [[np.nan if x is None else float(x) * 1.0e6,
                  np.nan if y is None else float(y)] for _, x, y in records],
                dtype=float,
            )
            table = ObservationTable(
                values,
                (
                    *FATIGUE_VARIABLES,
                ),
                np.isfinite(values),
                tuple(f"{SOURCE_ID}:row-{row}" for row, _, _ in records),
                (f"oedi-4130x-series-{index}",) * len(records),
                (Origin.MEASURED, Origin.MEASURED),
                SOURCE_ID,
                (
                    ("source_sha256", actual_hash),
                    ("source_md5", actual_md5),
                    ("source_sheet", EXPECTED_SHEET),
                    ("source_columns_one_based", f"{first_column},{first_column + 1}"),
                    ("source_rows_one_based", ",".join(str(row) for row, _, _ in records)),
                    ("environment_label", environment_label),
                    ("reported_environment", environment),
                    ("test_method", test_method),
                ),
            )
            environment_column = 5 if index == 5 else 6
            pressure_mpa = _number(environment_sheet, 8, environment_column)
            condition = "air" if index == 5 else "H2"
            if condition == "H2" and pressure_mpa != EXPECTED_PRESSURE_MPA:
                raise ValueError("OEDI hydrogen pressure differs from the audited workbook receipt")
            temperature_label = _text(environment_sheet, 7, environment_column)
            groups.append(
                _issue_fatigue_series(
                    series_id=f"oedi-4130x-{condition.lower()}-{index}",
                    environment=condition,
                    pressure_mpa=pressure_mpa,
                    temperature_label=temperature_label,
                    orientation=_text(fatigue, 6, first_column + 1),
                    test_method=test_method,
                    r_ratio=r_ratio,
                    frequency_hz=frequency,
                    reference=reference,
                    source_columns=(first_column, first_column + 1),
                    observations=table,
                )
            )
            if not environment_label or not method:
                raise ValueError("OEDI fatigue test-condition labels are incomplete")
    finally:
        workbook.close()

    discrepancy = (
        "HyMatBase lists 4.5 MPa for the exact same workbook bytes, while the workbook's "
        "Environment sheet and fatigue-condition cells state 45 MPa."
    )
    resolution = (
        "The local XLSX matches the HyMatBase file MD5 and the Data.gov-pinned SHA-256; "
        "its own condition cells state 45 MPa, and the Sandia publication record for this "
        "4130X fatigue study also states 45 MPa. Use 45 MPa for these workbook observations; "
        "retain the contradictory 4.5 MPa database field as a metadata discrepancy."
    )
    return _issue_oedi_dataset(
        source_file=path.name,
        source_url=SOURCE_URL,
        source_md5=actual_md5,
        source_sha256=actual_hash,
        publisher=SOURCE_PUBLISHER,
        license_id="CC-BY-4.0",
        license_url=SOURCE_LICENSE_URL,
        material=material_name,
        material_form=material_form,
        temper=temper,
        condition_metadata_discrepancy=discrepancy,
        condition_resolution=resolution,
        condition_authority_url=CONDITION_AUTHORITY_URL,
        related_condition_source_url=RELATED_CONDITION_URL,
        condition_identity_admitted=True,
        series=tuple(groups),
    )


__all__ = [
    "FatigueGrowthSeries",
    "OediFatigueDataset",
    "SOURCE_ID",
    "SOURCE_MD5",
    "SOURCE_SHA256",
    "load_oedi_4130x_fatigue",
]
