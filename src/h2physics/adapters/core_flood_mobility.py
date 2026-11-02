"""Source-bound interpolation and empirical compression of core-flood curves.

Values stay tied to exact workbook headers and source rows. Caller declarations
control units and physical roles; the optional power-law summary is a fit to
those observations, not an inferred field law or independent qualification.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from ..data.hydrogen_core_flood import CoreFloodTable

GasId = Literal["H2", "N2"]
BranchId = Literal["primary_drainage", "imbibition", "secondary_drainage"]
RelativePhase = Literal["gas", "water"]

_SOURCE_BRANCHES = {
    "Imbibition_H2.xlsx": ("H2", "imbibition"),
    "Primary_drainage_H2.xlsx": ("H2", "primary_drainage"),
    "Primary_drainage_N2.xlsx": ("N2", "primary_drainage"),
    "Secondary_drainage_H2.xlsx": ("H2", "secondary_drainage"),
}
_SOURCE_HASHES = {
    "Imbibition_H2.xlsx": "1f07f4bd5f5472f57ff0dd718744b180f8d8ee5b7e4ca9a51d484a90e5e002db",
    "Primary_drainage_H2.xlsx": "60b94149b4f84b131fc1a70eac592dc741f22486cec1725ec7b904c4b56ec7ff",
    "Primary_drainage_N2.xlsx": "ae2934256439f959f358c3dce468beaed9f6e98b8388934d26a36791fa047a3f",
    "Secondary_drainage_H2.xlsx": "a79b90ecc62ee1b23f821da31149d0673d741e6652979ce46ddcf77714ba14e4",
}
_SOURCE_URLS = {
    "Imbibition_H2.xlsx": "https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/17cb9ae3-70cc-4231-b979-643b5d199a90/file_downloaded",
    "Primary_drainage_H2.xlsx": "https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/ce094687-9357-4234-8dc4-9fda3efa5199/file_downloaded",
    "Primary_drainage_N2.xlsx": "https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/83ab3ce9-5b2f-47af-a33b-fbc53a8929c4/file_downloaded",
    "Secondary_drainage_H2.xlsx": "https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/3616a016-909b-46e2-820b-abfdd4aeae02/file_downloaded",
}
_SCALED_UNITS = {"%", "percent", "percentage"}
_NATIVE_UNITS = {"1", "fraction", "dimensionless"}
# Canonical two-phase K_rg / K_rw notation carries an explicit phase subscript;
# only these unambiguous prefixes are interpreted, while other headers stay caller-owned.
_CANONICAL_RELATIVE_PHASE_HEADERS = (
    (re.compile(r"^krg(?:$|[^a-z0-9])", re.IGNORECASE), "gas"),
    (re.compile(r"^krw(?:$|[^a-z0-9])", re.IGNORECASE), "water"),
)
_PENDING_BRANCHES: set[object] = set()
_PENDING_POINTS: set[object] = set()
_PENDING_POWER_LAW_FITS: set[object] = set()


def _issue_branch(*args, **values) -> CoreFloodBranch:
    token = object()
    _PENDING_BRANCHES.add(token)
    try:
        return CoreFloodBranch(*args, **values, _issuer=token)
    except Exception:
        _PENDING_BRANCHES.discard(token)
        raise


def _issue_point(*args, **values) -> CoreFloodMobilityPoint:
    token = object()
    _PENDING_POINTS.add(token)
    try:
        return CoreFloodMobilityPoint(*args, **values, _issuer=token)
    except Exception:
        _PENDING_POINTS.discard(token)
        raise


def _issue_power_law_fit(**values) -> CoreFloodPowerLawFit:
    token = object()
    _PENDING_POWER_LAW_FITS.add(token)
    try:
        return CoreFloodPowerLawFit(**values, _issuer=token)
    except Exception:
        _PENDING_POWER_LAW_FITS.discard(token)
        raise


def _fingerprint(table: CoreFloodTable, indices: tuple[int, int], declarations: tuple[object, ...]) -> str:
    digest = hashlib.sha256()
    digest.update(repr((table.filename, table.source_url, table.sha256, table.worksheet,
                        table.rows, table.source_row_ids, indices, declarations)).encode("utf-8"))
    return digest.hexdigest()


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be an actual numeric workbook cell; tokens are not coerced")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _positive_scale(unit: str, scale: float | None, label: str) -> float:
    normalized = unit.strip().casefold()
    if not normalized:
        raise ValueError(f"{label} unit declaration is required")
    if normalized in _NATIVE_UNITS:
        if scale is not None:
            value = _number(scale, f"{label} scale")
            if value <= 0:
                raise ValueError(f"{label} scale must be positive")
            return value
        return 1.0
    if normalized in _SCALED_UNITS and scale is None:
        raise ValueError(f"{label} reported as percent requires an explicit scale to fraction")
    if scale is None:
        raise ValueError(f"{label} non-unit declaration requires an explicit scale to fraction")
    value = _number(scale, f"{label} scale")
    if value <= 0:
        raise ValueError(f"{label} scale must be positive")
    return value


@dataclass(frozen=True, slots=True)
class CoreFloodMobilityPoint:
    """One interpolation result with both source endpoints and their exact row IDs."""

    saturation: float
    relative_permeability: float
    mobility_per_intrinsic_permeability: float
    left_source_row_id: str
    right_source_row_id: str
    interpolation_weight: float
    raw_left_saturation: float
    raw_right_saturation: float
    raw_left_relative_permeability: float
    raw_right_relative_permeability: float
    gas_id: str
    branch: str
    relative_phase: str
    _branch_source: CoreFloodBranch = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer not in _PENDING_POINTS:
            raise ValueError("Use CoreFloodBranch.evaluate() to issue a source-bound point")
        _PENDING_POINTS.remove(self._issuer)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self) -> str:
        values = (self.saturation, self.relative_permeability,
                  self.mobility_per_intrinsic_permeability, self.left_source_row_id,
                  self.right_source_row_id, self.interpolation_weight,
                  self.raw_left_saturation, self.raw_right_saturation,
                  self.raw_left_relative_permeability, self.raw_right_relative_permeability,
                  self.gas_id, self.branch, self.relative_phase,
                  self._branch_source._fingerprint())
        return hashlib.sha256(repr(values).encode("utf-8")).hexdigest()

    def require_current(self) -> CoreFloodMobilityPoint:
        self._branch_source.require_current()
        if self._seal != self._fingerprint():
            raise ValueError("Interpolation result or its source branch changed after issuance")
        return self


@dataclass(frozen=True, slots=True)
class CoreFloodBranch:
    """A single gas, hysteresis branch, and relative phase from one source workbook."""

    table: CoreFloodTable
    gas_id: GasId
    branch: BranchId
    relative_phase: RelativePhase
    saturation_header: str
    saturation_role: str
    saturation_unit: str
    saturation_basis: str
    saturation_scale: float
    relative_permeability_header: str
    relative_permeability_role: str
    relative_permeability_unit: str
    relative_permeability_basis: str
    relative_permeability_scale: float
    viscosity_pa_s: float
    viscosity_basis: str
    viscosity_evidence: str
    interpretation_evidence: str
    saturation_values: tuple[float, ...]
    relative_permeability_values: tuple[float, ...]
    raw_saturation_values: tuple[float, ...]
    raw_relative_permeability_values: tuple[float, ...]
    source_row_ids: tuple[str, ...]
    _column_indices: tuple[int, int] = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer not in _PENDING_BRANCHES:
            raise ValueError("Use build_core_flood_branch() to issue a source-bound branch")
        _PENDING_BRANCHES.remove(self._issuer)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _declarations(self) -> tuple[object, ...]:
        return (self.gas_id, self.branch, self.relative_phase, self.saturation_header,
                self.saturation_role, self.saturation_unit, self.saturation_basis,
                self.saturation_scale, self.relative_permeability_header,
                self.relative_permeability_role, self.relative_permeability_unit,
                self.relative_permeability_basis, self.relative_permeability_scale,
                self.viscosity_pa_s, self.viscosity_basis, self.viscosity_evidence,
                self.interpretation_evidence, self.saturation_values,
                self.relative_permeability_values, self.raw_saturation_values,
                self.raw_relative_permeability_values, self.source_row_ids)

    def _fingerprint(self) -> str:
        return _fingerprint(self.table, self._column_indices, self._declarations())

    def require_current(self) -> CoreFloodBranch:
        if self._fingerprint() != self._seal:
            raise ValueError("Core-flood branch or source table changed after adapter construction")
        return self

    @property
    def observed_saturation_domain(self) -> tuple[float, float]:
        self.require_current()
        return min(self.saturation_values), max(self.saturation_values)

    def evaluate(self, saturation: float) -> CoreFloodMobilityPoint:
        """Interpolate only inside observed saturation values, preserving row direction."""
        self.require_current()
        query = _number(saturation, "saturation query")
        low, high = self.observed_saturation_domain
        if query < low or query > high:
            raise ValueError("Saturation query is outside the observed source domain; extrapolation is disabled")
        for index, (left, right) in enumerate(zip(self.saturation_values, self.saturation_values[1:])):
            if min(left, right) <= query <= max(left, right):
                weight = (query - left) / (right - left)
                left_kr = self.relative_permeability_values[index]
                right_kr = self.relative_permeability_values[index + 1]
                kr = left_kr + weight * (right_kr - left_kr)
                return _issue_point(
                    query, kr, kr / self.viscosity_pa_s,
                    self.source_row_ids[index], self.source_row_ids[index + 1], weight,
                    self.raw_saturation_values[index], self.raw_saturation_values[index + 1],
                    self.raw_relative_permeability_values[index],
                    self.raw_relative_permeability_values[index + 1],
                    self.gas_id, self.branch, self.relative_phase, self,
                )
        raise ValueError("Saturation samples are not strictly monotone")


@dataclass(frozen=True, slots=True)
class CoreFloodPowerLawFit:
    """Source-bound empirical power-law summary of one reported branch.

    This is a curve compression for the supplied observations, not a new
    measurement, reservoir law qualification, or independent validation.
    """

    branch_source: CoreFloodBranch = field(repr=False, compare=False)
    irreducible_water_saturation: float
    residual_gas_saturation: float
    endpoint_relative_permeability: float
    exponent: float
    rmse: float
    maximum_absolute_error: float
    observed_saturation_domain: tuple[float, float]
    source_row_ids: tuple[str, ...]
    endpoint_evidence: str
    fit_method: str
    function_evaluations: int
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer not in _PENDING_POWER_LAW_FITS:
            raise ValueError("Use fit_core_flood_power_law() to issue a source-bound fit")
        _PENDING_POWER_LAW_FITS.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "source_row_ids", tuple(self.source_row_ids))
        object.__setattr__(self, "observed_saturation_domain",
                           tuple(self.observed_saturation_domain))
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self) -> str:
        values = (self.branch_source._fingerprint(), self.irreducible_water_saturation,
                  self.residual_gas_saturation, self.endpoint_relative_permeability,
                  self.exponent, self.rmse, self.maximum_absolute_error,
                  self.observed_saturation_domain, self.source_row_ids,
                  self.endpoint_evidence, self.fit_method, self.function_evaluations)
        return hashlib.sha256(repr(values).encode("utf-8")).hexdigest()

    def require_current(self) -> CoreFloodPowerLawFit:
        self.branch_source.require_current()
        if self._seal != self._fingerprint():
            raise ValueError("Fitted curve or its source branch changed after issuance")
        return self

    def evaluate(self, water_saturation: float) -> float:
        """Evaluate only inside the observations used for this fit; no extrapolation."""
        self.require_current()
        sw = _number(water_saturation, "water saturation query")
        low, high = self.observed_saturation_domain
        if sw < low or sw > high:
            raise ValueError("Fitted curve query is outside its observed source domain")
        denominator = (1.0 - self.irreducible_water_saturation
                       - self.residual_gas_saturation)
        effective_water = (sw - self.irreducible_water_saturation) / denominator
        coordinate = (effective_water if self.branch_source.relative_phase == "water"
                      else 1.0 - effective_water)
        return self.endpoint_relative_permeability * max(0.0, coordinate) ** self.exponent


def fit_core_flood_power_law(
    branch: CoreFloodBranch,
    *,
    irreducible_water_saturation: float,
    residual_gas_saturation: float,
    endpoint_evidence: str,
) -> CoreFloodPowerLawFit:
    """Fit ``kr = kr_endpoint * Se**n`` to one explicitly interpreted branch.

    Water phase uses ``Se = (Sw - Swir)/(1 - Swir - Sgr)``; gas phase uses
    ``Se = 1 - (Sw - Swir)/(1 - Swir - Sgr)``. Endpoint saturations are
    caller-owned inputs with a required evidence ID; they are never inferred
    from the table. The unweighted least-squares fit uses every retained source
    row and is restricted to observations inside those caller endpoints.
    """
    if not isinstance(branch, CoreFloodBranch):
        raise TypeError("branch must be a source-bound CoreFloodBranch")
    branch.require_current()
    if not isinstance(endpoint_evidence, str) or not endpoint_evidence.strip():
        raise ValueError("Endpoint saturation evidence ID is required")
    swir = _number(irreducible_water_saturation, "irreducible water saturation")
    sgr = _number(residual_gas_saturation, "residual gas saturation")
    if swir < 0 or sgr < 0 or swir + sgr >= 1:
        raise ValueError("Endpoint saturations must be nonnegative and sum to less than one")
    sw = np.asarray(branch.saturation_values, dtype=float)
    kr = np.asarray(branch.relative_permeability_values, dtype=float)
    if len(sw) < 3 or len(branch.source_row_ids) < 3:
        raise ValueError("At least three source observations are required for a two-parameter fit")
    if sw.min() < swir or sw.max() > 1.0 - sgr:
        raise ValueError("Caller endpoints must enclose every observed saturation")
    if (kr.min() < 0 or kr.max() > 1.0
            or not np.all(np.isfinite(kr))):
        raise ValueError("Power-law fitting requires finite relative permeability in [0, 1]")
    denominator = 1.0 - swir - sgr
    effective_water = (sw - swir) / denominator
    coordinate = (effective_water if branch.relative_phase == "water"
                  else 1.0 - effective_water)
    if np.count_nonzero(coordinate > 0) < 2:
        raise ValueError("At least two positive effective-saturation observations are needed")
    from scipy.optimize import least_squares

    def residual(parameters):
        endpoint, exponent = parameters
        return endpoint * np.power(np.clip(coordinate, 0.0, 1.0), exponent) - kr

    result = least_squares(
        residual, x0=(max(float(kr.max()), 1e-8), 2.0),
        bounds=((1e-12, 0.05), (1.0, 20.0)), method="trf",
        ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=10_000,
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        raise ValueError("Power-law least-squares fit did not converge to finite parameters")
    errors = residual(result.x)
    return _issue_power_law_fit(
        branch_source=branch, irreducible_water_saturation=swir,
        residual_gas_saturation=sgr,
        endpoint_relative_permeability=float(result.x[0]), exponent=float(result.x[1]),
        rmse=float(np.sqrt(np.mean(errors**2))),
        maximum_absolute_error=float(np.max(np.abs(errors))),
        observed_saturation_domain=(float(sw.min()), float(sw.max())),
        source_row_ids=branch.source_row_ids, endpoint_evidence=endpoint_evidence,
        fit_method="scipy.optimize.least_squares/trf; unweighted; bounds endpoint [1e-12,1], exponent [0.05,20]",
        function_evaluations=int(result.nfev),
    )


def build_core_flood_branch(
    table: CoreFloodTable,
    *,
    gas_id: GasId,
    branch: BranchId,
    relative_phase: RelativePhase,
    saturation_header: str,
    saturation_role: str,
    saturation_unit: str,
    saturation_basis: str,
    relative_permeability_header: str,
    relative_permeability_role: str,
    relative_permeability_unit: str,
    relative_permeability_basis: str,
    interpretation_evidence: str,
    viscosity_pa_s: float,
    viscosity_basis: str,
    viscosity_evidence: str,
    saturation_scale: float | None = None,
    relative_permeability_scale: float | None = None,
) -> CoreFloodBranch:
    """Build one declared phase/branch view; exact headings and evidence are mandatory.

    Saturation and relative permeability use fractional coordinates internally.
    If either source values are not already declared as dimensionless/fractions,
    provide a positive factor that converts the raw cells to a fraction. The raw
    values and factors remain available on the result.
    """
    if not isinstance(table, CoreFloodTable) or table.worksheet != "Kr":
        raise TypeError("Pass one publisher CoreFloodTable from its exact Kr worksheet")
    expected_identity = _SOURCE_BRANCHES.get(table.filename)
    if (expected_identity is None or table.sha256 != _SOURCE_HASHES[table.filename]
            or table.source_url != _SOURCE_URLS[table.filename]
            or table.worksheet != "Kr" or expected_identity != (gas_id, branch)):
        raise ValueError("Gas and hysteresis branch must match the pinned source workbook")
    if saturation_role != "water_saturation":
        raise ValueError("The saturation field role must be explicitly declared as water_saturation")
    expected_role = "gas_relative_permeability" if relative_phase == "gas" else "water_relative_permeability"
    if relative_phase not in {"gas", "water"} or relative_permeability_role != expected_role:
        raise ValueError("Selected field role must explicitly match the declared relative phase")
    required_text = {
        "saturation header": saturation_header, "saturation unit": saturation_unit,
        "saturation basis": saturation_basis,
        "relative-permeability header": relative_permeability_header,
        "relative-permeability unit": relative_permeability_unit,
        "relative-permeability basis": relative_permeability_basis,
        "interpretation evidence": interpretation_evidence,
        "viscosity basis": viscosity_basis, "viscosity evidence": viscosity_evidence,
    }
    if any(not isinstance(value, str) or not value.strip() for value in required_text.values()):
        missing = tuple(name for name, value in required_text.items()
                        if not isinstance(value, str) or not value.strip())
        raise ValueError("Explicit source interpretation declarations are required: " + ", ".join(missing))
    canonical_phase = next((phase for pattern, phase in _CANONICAL_RELATIVE_PHASE_HEADERS
                            if pattern.match(relative_permeability_header.strip())), None)
    if canonical_phase is not None and canonical_phase != relative_phase:
        raise ValueError(
            f"Canonical {relative_permeability_header!r} header denotes {canonical_phase} relative permeability"
        )
    if relative_permeability_unit.strip().casefold() not in _NATIVE_UNITS | _SCALED_UNITS:
        raise ValueError("Relative-permeability units must be declared dimensionless or percent")
    viscosity = _number(viscosity_pa_s, "dynamic viscosity in Pa s")
    if viscosity <= 0:
        raise ValueError("Dynamic viscosity in Pa s must be strictly positive")
    headers = table.headers
    sat_matches = tuple(i for i, header in enumerate(headers) if header == saturation_header)
    kr_matches = tuple(i for i, header in enumerate(headers) if header == relative_permeability_header)
    if len(sat_matches) != 1 or len(kr_matches) != 1 or sat_matches[0] == kr_matches[0]:
        raise ValueError("Each exact caller-selected header must resolve to one distinct column")
    sat_index, kr_index = sat_matches[0], kr_matches[0]
    if len(table.source_row_ids) != len(table.rows) or len(table.rows) < 3:
        raise ValueError("Source rows and stable source identities must align and include two observations")
    raw_sat, raw_kr, source_ids = [], [], []
    for row_index, (row, source_id) in enumerate(zip(table.rows[1:], table.source_row_ids[1:], strict=True), 2):
        if max(sat_index, kr_index) >= len(row):
            raise ValueError("A selected source field is missing from a workbook row")
        raw_sat.append(_number(row[sat_index], f"saturation at {source_id}"))
        raw_kr.append(_number(row[kr_index], f"relative permeability at {source_id}"))
        expected_id = f"hydrogen-core-flood:{table.filename}:Kr:row-{row_index}"
        if source_id != expected_id:
            raise ValueError("Every selected observation needs its original one-based workbook row ID")
        source_ids.append(source_id)
    sat_scale = _positive_scale(saturation_unit, saturation_scale, "Saturation")
    kr_scale = _positive_scale(relative_permeability_unit, relative_permeability_scale,
                               "Relative permeability")
    sat_values = tuple(value * sat_scale for value in raw_sat)
    kr_values = tuple(value * kr_scale for value in raw_kr)
    if any(value < 0 or value > 1 for value in sat_values):
        raise ValueError("Declared saturation scale must yield values in the unit interval")
    if any(value < 0 for value in kr_values):
        raise ValueError("Relative-permeability values cannot be negative")
    deltas = tuple(right - left for left, right in zip(sat_values, sat_values[1:]))
    if not (all(delta > 0 for delta in deltas) or all(delta < 0 for delta in deltas)):
        raise ValueError("Saturation samples must be strictly monotone in source order")
    return _issue_branch(
        table, gas_id, branch, relative_phase, saturation_header, saturation_role,
        saturation_unit, saturation_basis, sat_scale, relative_permeability_header,
        relative_permeability_role, relative_permeability_unit,
        relative_permeability_basis, kr_scale, viscosity, viscosity_basis,
        viscosity_evidence, interpretation_evidence, sat_values, kr_values,
        tuple(raw_sat), tuple(raw_kr), tuple(source_ids), (sat_index, kr_index),
    )
