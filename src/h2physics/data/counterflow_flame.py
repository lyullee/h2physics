"""Source-bound ingestion for the KIT NH3/H2 counterflow flame archive.

The raw dataset remains outside the package. This reader exposes the measured
extinction-rate table with its workbook hash and source-row identity; it does
not infer missing burner conditions or claim an independent model validation.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

DATASET_ID = "nh3-h2-counterflow-flame"
DATASET_DOI = "10.35097/bnpe6n1ppv92yjw4"
DATASET_URL = "https://publikationen.bibliothek.kit.edu/1000197646"
DATASET_LICENSE = "CC-BY-4.0"
EXTINCTION_WORKBOOK = "Extinction Strain Rates.xlsx"
EXTINCTION_HEADERS = (
    "xO2  (mole/mole)",
    "xH2 (mole/mole)",
    "Extinction Strain Rate (1/s)",
)
_PENDING_DATA_ISSUERS: set[object] = set()


def _issue_data_record(record_type, *args, **values):
    token = object()
    _PENDING_DATA_ISSUERS.add(token)
    try:
        return record_type(*args, **values, _issuer_token=token)
    except Exception:
        _PENDING_DATA_ISSUERS.discard(token)
        raise


def _consume_data_issuer(token):
    if token not in _PENDING_DATA_ISSUERS:
        raise ValueError("Use the checksum-reading counterflow data loader to issue source records")
    _PENDING_DATA_ISSUERS.remove(token)


@dataclass(frozen=True, slots=True)
class ExtinctionStrainObservation:
    """One measured condition as written in the publisher workbook."""

    source_row: int
    oxygen_mole_fraction: float
    hydrogen_mole_fraction: float
    extinction_strain_rate_s_inv: float


@dataclass(frozen=True, slots=True)
class ExtinctionStrainDataset:
    """Immutable observations tied to the source workbook's SHA-256."""

    dataset_id: str
    doi: str
    source_url: str
    license: str
    workbook_name: str
    workbook_sha256: str
    observations: tuple[ExtinctionStrainObservation, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        _consume_data_issuer(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)


@dataclass(frozen=True, slots=True)
class MeasuredFlameProfile:
    """One source-preserved spatial profile and its reported condition labels."""

    profile_id: str
    observable: str
    unit: str
    coordinate_m: tuple[float, ...]
    values: tuple[float | None, ...]
    conditions: tuple[tuple[str, float | str], ...]
    source_rows: tuple[int, ...]
    source_columns: tuple[int, ...]
    workbook_name: str
    workbook_sha256: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        _consume_data_issuer(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        if not self.profile_id or not self.observable or not self.unit:
            raise ValueError("Declare profile identity, observable and source unit")
        if not self.coordinate_m or len(self.coordinate_m) != len(self.values):
            raise ValueError("Profile coordinates and observations must have equal nonzero length")
        if len(self.source_rows) != len(self.coordinate_m):
            raise ValueError("Retain the source worksheet row for every profile point")
        if any(not math.isfinite(x) for x in self.coordinate_m):
            raise ValueError("Profile coordinates must be finite")
        if any(b <= a for a, b in zip(self.coordinate_m, self.coordinate_m[1:])):
            raise ValueError("Source profile coordinates must be strictly increasing")
        if any(value is not None and not math.isfinite(value) for value in self.values):
            raise ValueError("Profile measurements must be finite or explicitly missing")
        if not self.source_columns or not self.workbook_name or len(self.workbook_sha256) != 64:
            raise ValueError("Retain workbook identity, checksum and source columns")


@dataclass(frozen=True, slots=True)
class OpticalDiagnosticSeries:
    """A normalized optical signal; it is not a mole fraction or temperature."""

    series_id: str
    diagnostic: str
    signal_header: str
    axis_values: tuple[float, ...]
    axis_unit: str
    normalized_intensity: tuple[float | None, ...]
    conditions: tuple[tuple[str, float | str], ...]
    source_rows: tuple[int, ...]
    source_columns: tuple[int, ...]
    workbook_name: str
    workbook_sha256: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        _consume_data_issuer(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        if (
            not self.series_id
            or not self.diagnostic
            or not self.signal_header
            or not self.axis_unit
        ):
            raise ValueError("Declare optical-series identity, signal and coordinate unit")
        if not self.axis_values or len(self.axis_values) != len(self.normalized_intensity):
            raise ValueError("Optical coordinate and signal arrays must have equal nonzero length")
        if len(self.source_rows) != len(self.axis_values):
            raise ValueError("Retain the worksheet row for each optical observation")
        if any(not math.isfinite(value) for value in self.axis_values):
            raise ValueError("Optical coordinates must be finite")
        if len(self.axis_values) > 1:
            ascending = all(b > a for a, b in zip(self.axis_values, self.axis_values[1:]))
            descending = all(b < a for a, b in zip(self.axis_values, self.axis_values[1:]))
            if not (ascending or descending):
                raise ValueError("Retain only a strictly monotonic source axis")
        if any(
            value is not None and not math.isfinite(value) for value in self.normalized_intensity
        ):
            raise ValueError("Normalized optical intensity must be finite or explicitly missing")
        if not self.source_columns or not self.workbook_name or len(self.workbook_sha256) != 64:
            raise ValueError("Retain workbook identity, checksum and source columns")


@dataclass(frozen=True, slots=True)
class OpticalSpectrum:
    """A source-reported spectral diagnostic with dimensionless signal values."""

    spectrum_id: str
    band: str
    wavelength_nm: tuple[float, ...]
    normalized_intensity: tuple[float | None, ...]
    conditions: tuple[tuple[str, float | str], ...]
    source_rows: tuple[int, ...]
    source_columns: tuple[int, int]
    workbook_name: str
    workbook_sha256: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        _consume_data_issuer(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        if not self.spectrum_id or not self.band:
            raise ValueError("Declare spectrum identity and reported band")
        if not self.wavelength_nm or len(self.wavelength_nm) != len(self.normalized_intensity):
            raise ValueError("Wavelength and intensity arrays must have equal nonzero length")
        if len(self.source_rows) != len(self.wavelength_nm):
            raise ValueError("Retain the worksheet row for each spectral observation")
        if any(not math.isfinite(value) for value in self.wavelength_nm):
            raise ValueError("Wavelengths must be finite")
        if any(b <= a for a, b in zip(self.wavelength_nm, self.wavelength_nm[1:])):
            raise ValueError("Spectral wavelengths must be strictly increasing")
        if any(
            value is not None and not math.isfinite(value) for value in self.normalized_intensity
        ):
            raise ValueError("Spectral intensity must be finite or explicitly missing")
        if not self.workbook_name or len(self.workbook_sha256) != 64:
            raise ValueError("Retain spectrum workbook identity and checksum")


def _conditions(sheet, column, labels, *, first_row=1):
    conditions = []
    for row_number, label in enumerate(labels, start=first_row):
        if sheet.cell(row_number, 1).value != label:
            raise ValueError("Optical condition labels do not match the audited worksheet schema")
        value = sheet.cell(row_number, column).value
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError(f"Invalid optical source condition {label!r}")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"Non-finite optical source condition {label!r}")
        conditions.append((label, float(value) if isinstance(value, (int, float)) else value))
    return tuple(conditions)


def load_normalized_optical_profiles(archive_root: Path) -> tuple[OpticalDiagnosticSeries, ...]:
    """Read normalized NH*, NO*, OH* and visible-emission spatial signals."""

    from openpyxl import load_workbook

    workbook_name = "Normalized intensity profiles of NHX, NOX, OHX, and Vis.xlsx"
    path = Path(archive_root) / "data" / "dataset" / workbook_name
    if not path.is_file():
        raise FileNotFoundError(path)
    workbook_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    profiles = []
    expected_sheets = {
        "NHX": "I_NH*_(/)",
        "NOX": "I_NO*_(/)",
        "OHX": "I_OH*_(/)",
        "Vis": "I_Vis_(/)",
    }
    condition_labels = ("xH2", "xNH3", "xO2", "xAr", "xH2,rel")
    try:
        if {sheet.title for sheet in workbook.worksheets} != set(expected_sheets):
            raise ValueError("Optical spatial workbook sheets differ from the audited diagnostics")
        for sheet in workbook.worksheets:
            if sheet.cell(6, 2).value != "z_(mm)":
                raise ValueError(f"Unexpected spatial coordinate header in {sheet.title}")
            signal_header = expected_sheets[sheet.title]
            profile_index = 0
            for column in range(3, sheet.max_column + 1):
                header = sheet.cell(6, column).value
                if header is None:
                    continue
                if header != signal_header:
                    raise ValueError(f"Unexpected normalized signal header in {sheet.title}")
                conditions = _conditions(sheet, column, condition_labels)
                coordinates, series, source_rows = _profile_rows(
                    sheet, 2, (column,), first_row=7, scale=0.001
                )
                if not coordinates:
                    continue
                profiles.append(
                    _issue_data_record(
                        OpticalDiagnosticSeries,
                        f"{sheet.title}-{profile_index}",
                        sheet.title,
                        signal_header,
                        coordinates,
                        "m",
                        series[0],
                        conditions,
                        source_rows,
                        (2, column),
                        workbook_name,
                        workbook_hash,
                    )
                )
                profile_index += 1
    finally:
        workbook.close()
    return tuple(profiles)


def load_optical_band_integrals(archive_root: Path) -> tuple[OpticalDiagnosticSeries, ...]:
    """Read spatially resolved NO*/OH*/NH* band signals in source row order."""

    from openpyxl import load_workbook

    workbook_name = "UV emission spectrograph spectra and band integrals.xlsx"
    path = Path(archive_root) / "data" / "dataset" / workbook_name
    if not path.is_file():
        raise FileNotFoundError(path)
    workbook_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    profiles = []
    labels = ("Flame type", "Fuel", "Oxidizer", "Strainrate")
    groups = ((4, 5, "NO*"), (9, 10, "OH*"), (14, 15, "NH*"))
    try:
        if "Band Integrals" not in workbook.sheetnames:
            raise ValueError("The optical workbook lacks its declared band-integral worksheet")
        sheet = workbook["Band Integrals"]
        conditions = _conditions(sheet, 2, labels)
        for index, (coordinate_column, signal_column, band) in enumerate(groups):
            if sheet.cell(1, coordinate_column).value != band:
                raise ValueError("Band-integral observable header does not match its block")
            if (sheet.cell(2, coordinate_column).value, sheet.cell(2, signal_column).value) != (
                " z / mm",
                "I / -",
            ):
                raise ValueError("Band-integral coordinate or signal unit is unexpected")
            coordinates, series, source_rows = _profile_rows(
                sheet, coordinate_column, (signal_column,), first_row=3, scale=0.001
            )
            profiles.append(
                _issue_data_record(
                    OpticalDiagnosticSeries,
                    f"band-{band}-{index}",
                    band,
                    "I / -",
                    coordinates,
                    "m",
                    series[0],
                    conditions,
                    source_rows,
                    (coordinate_column, signal_column),
                    workbook_name,
                    workbook_hash,
                )
            )
    finally:
        workbook.close()
    return tuple(profiles)


def load_optical_spectra(archive_root: Path) -> tuple[OpticalSpectrum, ...]:
    """Read NO*/OH*/NH*-dominated spectra without assigning species concentrations."""

    from openpyxl import load_workbook

    workbook_name = "UV emission spectrograph spectra and band integrals.xlsx"
    path = Path(archive_root) / "data" / "dataset" / workbook_name
    if not path.is_file():
        raise FileNotFoundError(path)
    workbook_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    spectra = []
    groups = (
        (4, 5, "NO*-dominated wavelength range"),
        (9, 10, "OH*-dominated wavelength range"),
        (13, 14, "NH*-dominated wavelength range"),
    )
    try:
        if "Spectra" not in workbook.sheetnames:
            raise ValueError("The optical workbook lacks its declared spectra worksheet")
        sheet = workbook["Spectra"]
        conditions = _conditions(sheet, 2, ("Flame type", "Fuel", "Oxidizer", "Strainrate"))
        for coordinate_column, signal_column, band in groups:
            if sheet.cell(1, coordinate_column).value != band:
                raise ValueError("Spectral observable header does not match its block")
            if (sheet.cell(2, coordinate_column).value, sheet.cell(2, signal_column).value) != (
                "wavelength / nm",
                "I / -",
            ):
                raise ValueError("Spectral coordinate or signal unit is unexpected")
            wavelengths, series, source_rows = _profile_rows(
                sheet, coordinate_column, (signal_column,), first_row=3, scale=1.0
            )
            spectra.append(
                _issue_data_record(
                    OpticalSpectrum,
                    f"spectrum-{band.split('*')[0]}",
                    band,
                    wavelengths,
                    series[0],
                    conditions,
                    source_rows,
                    (coordinate_column, signal_column),
                    workbook_name,
                    workbook_hash,
                )
            )
    finally:
        workbook.close()
    return tuple(spectra)


def _profile_rows(sheet, coordinate_column, value_columns, *, first_row, scale):
    coordinates, values_by_column, source_rows = [], [[] for _ in value_columns], []
    column_offset = {column: column - coordinate_column for column in value_columns}
    last_column = max((coordinate_column, *value_columns))
    rows = sheet.iter_rows(
        min_row=first_row,
        max_row=sheet.max_row,
        min_col=coordinate_column,
        max_col=last_column,
        values_only=True,
    )
    for row_number, row in enumerate(rows, start=first_row):
        coordinate = row[0]
        values = [row[column_offset[column]] for column in value_columns]
        if coordinate is None and all(value is None for value in values):
            continue
        if (
            coordinate is None
            or isinstance(coordinate, bool)
            or not isinstance(coordinate, (int, float))
        ):
            raise ValueError(f"Invalid profile coordinate at source row {row_number}")
        coordinate = float(coordinate) * scale
        if not math.isfinite(coordinate):
            raise ValueError(f"Non-finite profile coordinate at source row {row_number}")
        point_values = []
        for value in values:
            if value is None:
                point_values.append(None)
            elif isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Non-numeric profile measurement at source row {row_number}")
            else:
                numeric = float(value)
                if not math.isfinite(numeric):
                    raise ValueError(f"Non-finite profile measurement at source row {row_number}")
                point_values.append(numeric)
        coordinates.append(coordinate)
        for series, value in zip(values_by_column, point_values, strict=True):
            series.append(value)
        source_rows.append(row_number)
    return (
        tuple(coordinates),
        tuple(tuple(series) for series in values_by_column),
        tuple(source_rows),
    )


def load_temperature_profiles(archive_root: Path) -> tuple[MeasuredFlameProfile, ...]:
    """Read paired source position/temperature columns without filling ragged cells."""

    from openpyxl import load_workbook

    workbook_name = "Temperature Data.xlsx"
    path = Path(archive_root) / "data" / "dataset" / workbook_name
    if not path.is_file():
        raise FileNotFoundError(path)
    workbook_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    profiles = []
    try:
        if len(workbook.worksheets) != 1:
            raise ValueError("The temperature workbook must contain one declared worksheet")
        sheet = workbook.worksheets[0]
        if (sheet.cell(3, 2).value, sheet.cell(3, 3).value) != ("z_(cm)", "Temperature_(K)"):
            raise ValueError("Temperature profile headers do not match the audited schema")
        if sheet.cell(1, 1).value != "xH2" or sheet.cell(2, 1).value != "xO2":
            raise ValueError("Temperature condition labels do not match the audited schema")
        profile_index = 0
        for coordinate_column in range(2, sheet.max_column + 1, 2):
            x_h2 = sheet.cell(1, coordinate_column).value
            x_o2 = sheet.cell(2, coordinate_column).value
            value_column = coordinate_column + 1
            if value_column > sheet.max_column or x_h2 is None or x_o2 is None:
                raise ValueError("A paired temperature profile lacks condition metadata")
            if not all(
                isinstance(x, (int, float)) and not isinstance(x, bool) for x in (x_h2, x_o2)
            ):
                raise ValueError("Temperature condition fractions must be numeric")
            if not all(0.0 <= float(x) <= 1.0 for x in (x_h2, x_o2)):
                raise ValueError("Temperature condition fractions lie outside [0, 1]")
            if (sheet.cell(3, coordinate_column).value, sheet.cell(3, value_column).value) != (
                "z_(cm)",
                "Temperature_(K)",
            ):
                raise ValueError("A temperature profile pair has unexpected column labels")
            coordinates, series, source_rows = _profile_rows(
                sheet, coordinate_column, (value_column,), first_row=4, scale=0.01
            )
            if not coordinates:
                continue
            profiles.append(
                _issue_data_record(
                    MeasuredFlameProfile,
                    f"temperature-{profile_index}",
                    "temperature",
                    "K",
                    coordinates,
                    series[0],
                    (("xH2", float(x_h2)), ("xO2", float(x_o2))),
                    source_rows,
                    (coordinate_column, value_column),
                    workbook_name,
                    workbook_hash,
                )
            )
            profile_index += 1
    finally:
        workbook.close()
    return tuple(profiles)


def load_inflame_species_profiles(archive_root: Path) -> tuple[MeasuredFlameProfile, ...]:
    """Read H2/NH3/NO volume-percent profiles and retain source missing cells."""

    from openpyxl import load_workbook

    workbook_name = "In-flame species profiles of H2, NH3, and NO.xlsx"
    path = Path(archive_root) / "data" / "dataset" / workbook_name
    if not path.is_file():
        raise FileNotFoundError(path)
    workbook_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    profiles = []
    condition_labels = ("xH2", "xNH3", "xO2", "xAr", "xH2,rel")
    species_labels = ("H2_(vol.%)", "NH3_(vol.%)", "NO_(vol.%)")
    try:
        if len(workbook.worksheets) != 1:
            raise ValueError("The in-flame species workbook must contain one worksheet")
        sheet = workbook.worksheets[0]
        for row_number, label in enumerate(condition_labels, start=1):
            if sheet.cell(row_number, 1).value != label:
                raise ValueError("Species-profile condition labels do not match the audited schema")
        if sheet.cell(6, 2).value != "z_(mm)":
            raise ValueError("Species-profile coordinate label does not match the audited schema")
        profile_index = 0
        for first_column in range(3, sheet.max_column + 1, len(species_labels)):
            columns = tuple(range(first_column, first_column + len(species_labels)))
            if columns[-1] > sheet.max_column:
                raise ValueError("The species-profile workbook ends with an incomplete group")
            if tuple(sheet.cell(6, column).value for column in columns) != species_labels:
                raise ValueError(
                    "Species-profile columns do not match H2/NH3/NO volume-percent labels"
                )
            conditions = []
            for row_number, label in enumerate(condition_labels, start=1):
                values = tuple(sheet.cell(row_number, column).value for column in columns)
                if any(value != values[0] for value in values[1:]):
                    raise ValueError("Condition metadata differs within one species-profile group")
                value = values[0]
                if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                    raise ValueError(f"Invalid source condition {label!r}")
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError(f"Non-finite source condition {label!r}")
                conditions.append((label, value))
            coordinates, series, source_rows = _profile_rows(
                sheet, 2, columns, first_row=7, scale=0.001
            )
            if not coordinates:
                continue
            for observable, column, values in zip(species_labels, columns, series, strict=True):
                profiles.append(
                    _issue_data_record(
                        MeasuredFlameProfile,
                        f"species-{profile_index}-{observable}",
                        observable.removesuffix("_(vol.%)"),
                        "vol.%",
                        coordinates,
                        values,
                        tuple(conditions),
                        source_rows,
                        (2, column),
                        workbook_name,
                        workbook_hash,
                    )
                )
            profile_index += 1
    finally:
        workbook.close()
    return tuple(profiles)


def load_extinction_strain_rates(archive_root: Path) -> ExtinctionStrainDataset:
    """Read the declared flat ESR table from an extracted RADAR4KIT BagIt root.

    ``archive_root`` is the directory containing ``data/dataset``. Formula
    execution, condition completion, duplicate averaging, sorting, and fitting
    are deliberately outside this ingestion function.
    """

    from openpyxl import load_workbook

    path = Path(archive_root) / "data" / "dataset" / EXTINCTION_WORKBOOK
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = path.read_bytes()
    workbook_hash = hashlib.sha256(payload).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    observations = []
    try:
        if len(workbook.worksheets) != 1:
            raise ValueError("The extinction-rate workbook must contain one declared table")
        sheet = workbook.worksheets[0]
        header = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
        if tuple(header[: len(EXTINCTION_HEADERS)]) != EXTINCTION_HEADERS:
            raise ValueError("The extinction-rate column names do not match the audited schema")
        for source_row, row in enumerate(
            sheet.iter_rows(min_row=2, max_col=3, values_only=True), start=2
        ):
            if all(value is None for value in row):
                continue
            if any(value is None or isinstance(value, bool) for value in row):
                raise ValueError(
                    f"Incomplete extinction-rate observation at source row {source_row}"
                )
            if any(not isinstance(value, (int, float)) for value in row):
                raise ValueError(
                    f"Non-numeric extinction-rate observation at source row {source_row}"
                )
            oxygen, hydrogen, rate = (float(value) for value in row)
            if not all(math.isfinite(value) for value in (oxygen, hydrogen, rate)):
                raise ValueError(
                    f"Non-finite extinction-rate observation at source row {source_row}"
                )
            if not 0 <= oxygen <= 1 or not 0 <= hydrogen <= 1 or rate <= 0:
                raise ValueError(
                    f"Out-of-domain extinction-rate observation at source row {source_row}"
                )
            observations.append(ExtinctionStrainObservation(source_row, oxygen, hydrogen, rate))
    finally:
        workbook.close()
    if not observations:
        raise ValueError("The extinction-rate workbook contains no measurements")
    return _issue_data_record(
        ExtinctionStrainDataset,
        DATASET_ID,
        DATASET_DOI,
        DATASET_URL,
        DATASET_LICENSE,
        EXTINCTION_WORKBOOK,
        workbook_hash,
        tuple(observations),
    )
