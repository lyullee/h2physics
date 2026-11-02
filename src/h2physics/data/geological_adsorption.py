"""Source-bound measurements for geological-material hydrogen excess adsorption.

The loader deliberately retains the reported excess-loading basis. It does not
convert excess loading to absolute uptake or provide an adsorption-bed model.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from zipfile import BadZipFile, ZipFile

import numpy as np

from ..core import immutable_array

SOURCE_DOI = "10.5281/zenodo.22305898"
SOURCE_LICENSE = "CC-BY-4.0"
SOURCE_SHA256 = "40c16cca5099e2c69dc44aceb43300854307b3a6c8351c43013afc9967e60dc6"
_ARCHIVE_PREFIX = "submission_package ZENODO_MINIMAL_FINAL/02_processed_data/isotherms/"
_MATERIAL_FILES = {
    "cox": "cox.csv",
    "kunipia": "kunipia.csv",
    "laponite": "laponite.csv",
    "mof177": "mof177.csv",
}
_REQUIRED_COLUMNS = frozenset(
    {
        "sample",
        "run",
        "P_bar",
        "T_K",
        "q_mmol_g",
        "u_total_mmol_g",
        "LOD_mmol_g",
        "LLOQ_mmol_g",
        "detection_status",
    }
)
_MAX_ARCHIVE_BYTES = 32_000_000
_MAX_ROWS = 100_000
_PENDING_ISOTHERM_ISSUERS: set[object] = set()


def _issue_isotherm(**values):
    token = object()
    _PENDING_ISOTHERM_ISSUERS.add(token)
    try:
        return GeologicalAdsorptionIsotherm(**values, _issuer_token=token)
    except Exception:
        _PENDING_ISOTHERM_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class GeologicalAdsorptionPoint:
    """One reported H2 excess-adsorption point and its source-row identity."""

    source_row: int
    sample: str
    run: str
    pressure_bar: float
    temperature_k: float
    signed_excess_loading_mmol_per_g: float
    total_standard_uncertainty_mmol_per_g: float | None
    detection_limit_mmol_per_g: float | None
    quantification_limit_mmol_per_g: float | None
    detection_status: str
    source_fields: tuple[tuple[str, str], ...]
    uptake_basis: Literal["signed_excess"] = field(default="signed_excess", init=False)

    def __post_init__(self) -> None:
        if (isinstance(self.source_row, bool) or not isinstance(self.source_row, int)
                or self.source_row < 2
                or not isinstance(self.sample, str) or not self.sample.strip()
                or not isinstance(self.run, str) or not self.run.strip()):
            raise ValueError("Every observation needs its CSV row, sample, and run identity")
        for name in ("pressure_bar", "temperature_k", "signed_excess_loading_mmol_per_g"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.pressure_bar <= 0.0 or self.temperature_k <= 0.0:
            raise ValueError("Pressure and absolute temperature must be positive")
        for name in (
            "total_standard_uncertainty_mmol_per_g",
            "detection_limit_mmol_per_g",
            "quantification_limit_mmol_per_g",
        ):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0.0
            ):
                raise ValueError(f"{name} must be a finite nonnegative value when present")
        if not isinstance(self.detection_status, str) or not self.detection_status.strip():
            raise ValueError("Retain the source detection-status field")
        fields = tuple(self.source_fields)
        if any(not isinstance(pair, tuple) or len(pair) != 2
               or any(not isinstance(item, str) for item in pair) for pair in fields):
            raise ValueError("Every original CSV field must remain a string name/value pair")
        if len(dict(fields)) != len(fields):
            raise ValueError("Source CSV field names must be unique")
        object.__setattr__(self, "source_fields", fields)

    def require_absolute_uptake(self) -> None:
        """Reject use as absolute uptake until a separately evidenced conversion exists."""
        raise ValueError(
            "This source reports signed excess adsorption, not absolute uptake; "
            "a pore-volume/gas-density conversion with independent evidence is required."
        )

    def surface_excess_provider(
        self,
        *,
        temperature_k: float,
        maximum_temperature_delta_k: float = 1e-6,
    ):
        """Create a bounded pure-H2 surface-excess provider for research comparisons.

        This exposes the source's signed excess quantity through the existing
        adsorption-provider contract. It never promotes excess to absolute
        uptake. Interpolation is linear in log-pressure within one measured
        isotherm only; temperature interpolation, multicomponent competition,
        and extrapolation are refused.
        """
        return GeologicalSurfaceExcessProvider.from_isotherm(
            self, temperature_k=temperature_k,
            maximum_temperature_delta_k=maximum_temperature_delta_k,
        )


@dataclass(frozen=True, slots=True)
class GeologicalAdsorptionIsotherm:
    """Immutable points for one material, tied to the archived publisher file."""

    material_id: str
    source_file: str
    source_sha256: str
    source_doi: str
    license_id: str
    points: tuple[GeologicalAdsorptionPoint, ...]
    uptake_basis: Literal["signed_excess"] = field(default="signed_excess", init=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer_token not in _PENDING_ISOTHERM_ISSUERS:
            raise ValueError("Use the checksum-validating archive loader to issue a source-bound isotherm")
        _PENDING_ISOTHERM_ISSUERS.remove(self._issuer_token)
        if self.material_id not in _MATERIAL_FILES:
            raise ValueError("Unsupported material identifier")
        if self.source_file != _ARCHIVE_PREFIX + _MATERIAL_FILES[self.material_id]:
            raise ValueError("Source file does not match the declared material")
        if self.source_doi != SOURCE_DOI or self.license_id != SOURCE_LICENSE:
            raise ValueError("Dataset provenance does not match the pinned source record")
        if self.source_sha256 != SOURCE_SHA256 or not self.points:
            raise ValueError("Require the pinned archive checksum and at least one row")
        points = tuple(self.points)
        if any(point.uptake_basis != "signed_excess" for point in points):
            raise ValueError("Do not mix uptake bases in a source isotherm")
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self) -> str:
        return hashlib.sha256(repr((
            self.material_id, self.source_file, self.source_sha256, self.source_doi,
            self.license_id, self.points, self.uptake_basis,
        )).encode("utf-8")).hexdigest()

    def require_current(self):
        if not self._seal or self._fingerprint() != self._seal:
            raise ValueError("Geological adsorption source rows or archive receipt changed after loading")
        return self

    def require_absolute_uptake(self) -> None:
        """Fail closed when a caller requests vessel-ready absolute uptake."""
        self.require_current()
        self.points[0].require_absolute_uptake()


@dataclass(frozen=True, slots=True)
class GeologicalSurfaceExcessProvider:
    """Single-component, single-temperature bounded log-pressure interpolation."""

    basis: object
    domain: object
    source: GeologicalAdsorptionIsotherm
    temperature_k: float
    pressure_pa: object
    excess_loading_mol_kg: object
    source_points: tuple[GeologicalAdsorptionPoint, ...]
    maximum_temperature_delta_k: float
    _fingerprint: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        from ..adsorption import AdsorptionBasis, AdsorptionDomain

        self.source.require_current()
        if (type(self.basis) is not AdsorptionBasis
                or type(self.domain) is not AdsorptionDomain
                or type(self.source) is not GeologicalAdsorptionIsotherm
                or self.basis.loading_definition != "surface_excess"
                or self.basis.material_id != self.source.material_id
                or self.basis.parameter_id != self.source.source_sha256):
            raise ValueError("Provider basis/domain must retain its exact source and excess identity")
        pressure = np.array(self.pressure_pa, dtype=float, copy=True)
        loading = np.array(self.excess_loading_mol_kg, dtype=float, copy=True)
        source_points = tuple(self.source_points)
        if (pressure.ndim != 1 or loading.shape != pressure.shape or len(pressure) < 2
                or not np.all(np.isfinite(pressure)) or np.any(pressure <= 0.)
                or not np.all(np.isfinite(loading)) or np.any(np.diff(pressure) <= 0.)
                or len(source_points) != len(pressure)
                or any(type(point) is not GeologicalAdsorptionPoint for point in source_points)):
            raise ValueError("Provider retains an ordered finite measured pressure/loading curve")
        if (not math.isfinite(self.temperature_k) or self.temperature_k <= 0.
                or not math.isfinite(self.maximum_temperature_delta_k)
                or self.maximum_temperature_delta_k < 0.):
            raise ValueError("Provider temperature and tolerance must be finite and valid")
        selected = tuple(point for point in self.source.points
                         if abs(point.temperature_k-self.temperature_k)
                         <= self.maximum_temperature_delta_k)
        groups = {point.temperature_k for point in selected}
        if len(groups) != 1 or next(iter(groups)) != self.temperature_k:
            raise ValueError("Provider temperature must identify one exact measured isotherm")
        expected_points = tuple(sorted(selected, key=lambda point: point.pressure_bar))
        expected_pressure = np.asarray([point.pressure_bar*1e5 for point in expected_points])
        expected_loading = np.asarray([
            point.signed_excess_loading_mmol_per_g for point in expected_points
        ])
        if (len(expected_points) < 2 or len(source_points) != len(expected_points)
                or any(actual is not expected for actual, expected in
                       zip(source_points, expected_points, strict=True))
                or not np.array_equal(pressure, expected_pressure)
                or not np.array_equal(loading, expected_loading)):
            raise ValueError("Provider arrays and row receipts must reproduce the selected source isotherm")
        pressure = immutable_array(pressure, name="pressure_pa")
        loading = immutable_array(loading, name="excess_loading_mol_kg")
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "excess_loading_mol_kg", loading)
        object.__setattr__(self, "source_points", source_points)
        object.__setattr__(self, "_fingerprint", self._current_fingerprint())

    @classmethod
    def from_isotherm(
        cls, isotherm, *, temperature_k, maximum_temperature_delta_k=1e-6,
    ):
        from ..adsorption import AdsorptionBasis, AdsorptionDomain

        if type(isotherm) is not GeologicalAdsorptionIsotherm:
            raise TypeError("Use a source-bound GeologicalAdsorptionIsotherm")
        isotherm.require_current()
        tolerance = maximum_temperature_delta_k
        if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
                or not math.isfinite(tolerance) or tolerance < 0.):
            raise ValueError("Temperature-matching tolerance must be finite and nonnegative")
        selected_temperature = temperature_k
        if (isinstance(selected_temperature, bool)
                or not isinstance(selected_temperature, (int, float))
                or not math.isfinite(selected_temperature) or selected_temperature <= 0.):
            raise ValueError("Select one finite positive measured isotherm temperature")
        groups = defaultdict(list)
        for point in isotherm.points:
            if abs(point.temperature_k-selected_temperature) <= tolerance:
                groups[point.temperature_k].append(point)
        if len(groups) != 1:
            raise ValueError(
                "Select one measured isotherm temperature; no temperature interpolation is supplied"
            )
        temperature, points = next(iter(groups.items()))
        points = tuple(sorted(points, key=lambda point: point.pressure_bar))
        pressures = np.asarray([point.pressure_bar * 1e5 for point in points], dtype=float)
        loading = np.asarray([
            point.signed_excess_loading_mmol_per_g for point in points
        ], dtype=float)
        if len(pressures) < 2 or np.any(np.diff(pressures) <= 0.):
            raise ValueError("A pressure isotherm needs at least two unique ordered pressure points")
        basis = AdsorptionBasis(
            material_id=isotherm.material_id,
            species=("H2",),
            amount_basis_id="mol_H2_per_kg_adsorbent_signed_excess",
            engine_id="measured-geological-excess-log-pressure-interpolation",
            parameter_id=isotherm.source_sha256,
            references=(isotherm.source_doi,),
            loading_definition="surface_excess",
        )
        domain = AdsorptionDomain(
            minimum_temperature_k=temperature-tolerance,
            maximum_temperature_k=temperature+tolerance,
            minimum_total_pressure_pa=float(pressures[0]),
            maximum_total_pressure_pa=float(pressures[-1]),
        )
        return cls(basis, domain, isotherm, temperature, pressures, loading, points, float(tolerance))

    def _current_fingerprint(self):
        return hashlib.sha256(repr((
            id(self.source), self.source.source_sha256, self.source.material_id,
            self.source.points, self.basis, self.domain, self.temperature_k,
            self.maximum_temperature_delta_k,
            self.pressure_pa.shape, self.pressure_pa.tobytes(),
            self.excess_loading_mol_kg.shape, self.excess_loading_mol_kg.tobytes(),
            self.source_points,
        )).encode("utf-8")).hexdigest()

    def require_current(self):
        self.source.require_current()
        if self.source.uptake_basis != "signed_excess":
            raise ValueError("The original geological dataset uptake basis changed")
        if self._current_fingerprint() != self._fingerprint:
            raise ValueError("Geological excess provider/source measurements changed after capture")
        return self

    def equilibrium(self, partial_pressures_pa, temperature_k):
        from ..adsorption import AdsorptionSourceObservation, AdsorptionState

        self.require_current()
        if (len(self.source.points) == 0
                or self.source.uptake_basis != "signed_excess"
                or self.basis.loading_definition != "surface_excess"):
            raise ValueError("The original signed-excess data basis changed")
        pressure = np.asarray(partial_pressures_pa, dtype=float)
        if (pressure.shape != (1,) or not np.all(np.isfinite(pressure))
                or pressure[0] <= 0.):
            raise ValueError("This measured provider accepts one positive pure-H2 partial pressure")
        self.domain.require_state(pressure, temperature_k)
        if abs(float(temperature_k)-self.temperature_k) > self.maximum_temperature_delta_k:
            raise ValueError("Temperature differs from the selected measured isotherm")
        if not self.pressure_pa[0] <= pressure[0] <= self.pressure_pa[-1]:
            raise ValueError("Pressure extrapolation beyond measured points is not permitted")
        log_pressure = math.log(float(pressure[0]))
        log_points = np.log(self.pressure_pa)
        upper = int(np.searchsorted(log_points, log_pressure, side="right"))
        if upper == 0:
            lower, upper, fraction = 0, 0, 0.
        elif upper == len(log_points):
            lower, upper, fraction = len(log_points)-1, len(log_points)-1, 0.
        else:
            lower = upper-1
            fraction = float((log_pressure-log_points[lower])/(log_points[upper]-log_points[lower]))
        weights = ((1.-fraction, fraction) if lower != upper else (1., 0.))
        loading = float(weights[0]*self.excess_loading_mol_kg[lower]
                        + weights[1]*self.excess_loading_mol_kg[upper])
        observations = tuple(
            AdsorptionSourceObservation(
                species=self.basis.species[0],
                source_row=self.source_points[index].source_row,
                interpolation_weight=float(weight),
                source_loading_mol_kg=float(
                    self.source_points[index].signed_excess_loading_mmol_per_g
                ),
                standard_uncertainty_mol_kg=(
                    None if self.source_points[index].total_standard_uncertainty_mmol_per_g is None
                    else float(self.source_points[index].total_standard_uncertainty_mmol_per_g)
                ),
                detection_limit_mol_kg=(
                    None if self.source_points[index].detection_limit_mmol_per_g is None
                    else float(self.source_points[index].detection_limit_mmol_per_g)
                ),
                quantification_limit_mol_kg=(
                    None if self.source_points[index].quantification_limit_mmol_per_g is None
                    else float(self.source_points[index].quantification_limit_mmol_per_g)
                ),
                source_dataset_id=self.source.source_doi,
                source_sha256=self.source.source_sha256,
                uncertainty_kind=("reported_standard_uncertainty"
                    if self.source_points[index].total_standard_uncertainty_mmol_per_g is not None
                    else "unqualified"),
            )
            for index, weight in ((lower, weights[0]), (upper, weights[1])) if weight > 0.
        )
        return AdsorptionState(
            basis=self.basis,
            partial_pressures_pa=pressure,
            temperature_k=float(temperature_k),
            site_loadings_mol_kg=np.asarray([[loading]]),
            source_observations=(observations,),
        )

    def require_absolute_uptake(self):
        self.require_current()
        self.source.require_absolute_uptake()


def load_geological_adsorption_isotherm(
    archive_path: str | Path,
    material_id: str,
) -> GeologicalAdsorptionIsotherm:
    """Read one processed source CSV from the pinned Zenodo archive without extraction.

    Raw observations remain in the caller's archive; this package does not ship a
    copy. ``q_mmol_g`` is retained as signed excess loading, numerically equivalent
    in scale to mol/kg but intentionally not relabelled as absolute uptake.
    """
    material = material_id.strip().lower() if isinstance(material_id, str) else ""
    if material not in _MATERIAL_FILES:
        raise ValueError(f"material_id must be one of {tuple(_MATERIAL_FILES)}")
    path = Path(archive_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise ValueError("The adsorption source archive exceeds the declared input limit")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Archive SHA-256 differs from the pinned Zenodo source")
    member = _ARCHIVE_PREFIX + _MATERIAL_FILES[material]

    try:
        with ZipFile(path) as archive:
            info = archive.getinfo(member)
            if info.file_size > 2_000_000:
                raise ValueError("Selected source table exceeds the declared member limit")
            with archive.open(info) as binary:
                stream = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
                reader = csv.DictReader(stream)
                columns = tuple(reader.fieldnames or ())
                missing = _REQUIRED_COLUMNS.difference(columns)
                if missing:
                    raise ValueError(f"Source CSV is missing columns: {sorted(missing)}")
                if len(set(columns)) != len(columns):
                    raise ValueError("Source CSV contains duplicate column names")
                rows: list[GeologicalAdsorptionPoint] = []
                for source_row, row in enumerate(reader, start=2):
                    if source_row > _MAX_ROWS + 1:
                        raise ValueError("Source CSV exceeds the declared row limit")
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError(f"Malformed field count at source row {source_row}")
                    rows.append(_parse_point(source_row, row))
    except BadZipFile as exc:
        raise ValueError("Source is not a readable ZIP archive") from exc
    except KeyError as exc:
        raise ValueError(f"Pinned archive does not contain {member}") from exc

    return _issue_isotherm(
        material_id=material,
        source_file=member,
        source_sha256=digest,
        source_doi=SOURCE_DOI,
        license_id=SOURCE_LICENSE,
        points=tuple(rows),
    )


def _parse_point(source_row: int, row: Mapping[str, str]) -> GeologicalAdsorptionPoint:
    def required_float(name: str) -> float:
        token = row[name].strip()
        if not token:
            raise ValueError(f"Missing {name} at source row {source_row}")
        try:
            value = float(token)
        except ValueError as exc:
            raise ValueError(f"Invalid {name} at source row {source_row}: {token!r}") from exc
        if not math.isfinite(value):
            raise ValueError(f"Non-finite {name} at source row {source_row}")
        return value

    def optional_float(name: str) -> float | None:
        token = row[name].strip()
        if not token:
            return None
        return required_float(name)

    return GeologicalAdsorptionPoint(
        source_row=source_row,
        sample=row["sample"].strip(),
        run=row["run"].strip(),
        pressure_bar=required_float("P_bar"),
        temperature_k=required_float("T_K"),
        signed_excess_loading_mmol_per_g=required_float("q_mmol_g"),
        total_standard_uncertainty_mmol_per_g=optional_float("u_total_mmol_g"),
        detection_limit_mmol_per_g=optional_float("LOD_mmol_g"),
        quantification_limit_mmol_per_g=optional_float("LLOQ_mmol_g"),
        detection_status=row["detection_status"].strip(),
        source_fields=tuple((key, value) for key, value in row.items()),
    )


__all__ = [
    "GeologicalAdsorptionIsotherm",
    "GeologicalAdsorptionPoint",
    "load_geological_adsorption_isotherm",
]
