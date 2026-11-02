"""Caller-owned gas-compressor maps paired with the existing Brayton reference.

Map values are observations or supplied design data; this module never predicts
them. The native Cantera cycle remains the property/combustion owner. Corrected
coordinates and the link between compressor and turbine speeds are caller
evidence because map owners use different reference conventions.
"""

import math
from dataclasses import dataclass, field

from ..core import finite
from .turbine_map import (
    CompressorOperatingPoint,
    CoupledShaftLedger,
    MapBoundBraytonInputs,
    MapBoundBraytonRun,
    TurbineComponentMap,
    couple_compressor_to_map_bound_brayton,
    run_map_bound_open_cycle_brayton,
)


_PENDING_RUN_ISSUERS: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare compressor-map {name}")
    return value.strip()


def _axis(values, name):
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a sequence of finite values")
    result = tuple(finite(value, f"{name} coordinate") for value in values)
    if len(result) < 2 or any(b <= a for a, b in zip(result, result[1:])):
        raise ValueError(f"{name} needs at least two strictly increasing coordinates")
    return result


def _matrix(values, n_speed, n_ratio, name):
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a rectangular matrix")
    result = tuple(tuple(finite(value, f"{name} value") for value in row) for row in values)
    if len(result) != n_speed or any(len(row) != n_ratio for row in result):
        raise ValueError(f"{name} dimensions must match speed and pressure-ratio coordinates")
    return result


def _bracket(axis, value, name):
    value = finite(value, name)
    if value < axis[0] or value > axis[-1]:
        raise ValueError(f"{name} lies outside the supplied compressor-map domain")
    for index, upper in enumerate(axis[1:]):
        if value <= upper:
            fraction = (value - axis[index]) / (upper - axis[index])
            return index, fraction
    return len(axis) - 2, 1.0


def _bilinear(matrix, i, wi, j, wj):
    lower = matrix[i][j] * (1.0 - wj) + matrix[i][j + 1] * wj
    upper = matrix[i + 1][j] * (1.0 - wj) + matrix[i + 1][j + 1] * wj
    return lower * (1.0 - wi) + upper * wi


@dataclass(frozen=True, slots=True)
class CompressorComponentMap:
    """Rectangular corrected-flow/efficiency observations for a gas compressor.

    Rows index corrected speed and columns index outlet-over-inlet total
    pressure ratio. No correction reference is inferred from these values.
    """

    map_id: str
    evidence_id: str
    source_uri: str
    license_id: str
    source_sha256: str
    speed_unit: str
    pressure_ratio_convention: str
    corrected_mass_flow_basis: str
    corrected_speed: tuple[float, ...]
    compression_pressure_ratio: tuple[float, ...]
    corrected_mass_flow_kg_s: tuple[tuple[float, ...], ...]
    isentropic_efficiency: tuple[tuple[float, ...], ...]
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._seal and self._payload() != self._seal:
            raise ValueError("Compressor map changed after source admission")
        for name in (
            "map_id", "evidence_id", "source_uri", "license_id", "speed_unit",
            "pressure_ratio_convention", "corrected_mass_flow_basis",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        digest = _text(self.source_sha256, "SHA-256")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
            raise ValueError("source_sha256 must identify the admitted map bytes")
        object.__setattr__(self, "source_sha256", digest.lower())
        if self.pressure_ratio_convention != "outlet-over-inlet-total-pressure":
            raise ValueError("Compressor maps require outlet-over-inlet total-pressure ratio")
        speed = _axis(self.corrected_speed, "corrected speed")
        ratio = _axis(self.compression_pressure_ratio, "compression pressure ratio")
        if speed[0] <= 0.0 or ratio[0] <= 1.0:
            raise ValueError("Corrected speed must be positive and compression ratio must exceed one")
        flow = _matrix(self.corrected_mass_flow_kg_s, len(speed), len(ratio), "corrected mass flow")
        efficiency = _matrix(self.isentropic_efficiency, len(speed), len(ratio), "isentropic efficiency")
        if any(value <= 0.0 for row in flow for value in row):
            raise ValueError("Corrected-flow map values must be positive")
        if any(value <= 0.0 or value > 1.0 for row in efficiency for value in row):
            raise ValueError("Compressor efficiencies must lie in (0, 1]")
        object.__setattr__(self, "corrected_speed", speed)
        object.__setattr__(self, "compression_pressure_ratio", ratio)
        object.__setattr__(self, "corrected_mass_flow_kg_s", flow)
        object.__setattr__(self, "isentropic_efficiency", efficiency)
        if not self._seal:
            object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return tuple(getattr(self, name) for name in (
            "map_id", "evidence_id", "source_uri", "license_id", "source_sha256",
            "speed_unit", "pressure_ratio_convention", "corrected_mass_flow_basis",
            "corrected_speed", "compression_pressure_ratio", "corrected_mass_flow_kg_s",
            "isentropic_efficiency",
        ))

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Compressor map changed after source admission")
        return self


@dataclass(frozen=True, slots=True)
class CompressorMapPoint:
    """Bounded bilinear map output retaining its source grid."""

    component_map: CompressorComponentMap
    corrected_speed: float
    compression_pressure_ratio: float
    corrected_mass_flow_kg_s: float
    isentropic_efficiency: float

    def __post_init__(self):
        if type(self.component_map) is not CompressorComponentMap:
            raise TypeError("component_map must be a CompressorComponentMap")
        self.component_map.require_current()
        speed = finite(self.corrected_speed, "corrected speed", positive=True)
        ratio = finite(self.compression_pressure_ratio, "compression pressure ratio", positive=True)
        i, wi = _bracket(self.component_map.corrected_speed, speed, "corrected speed")
        j, wj = _bracket(self.component_map.compression_pressure_ratio, ratio,
                          "compression pressure ratio")
        expected_flow = _bilinear(self.component_map.corrected_mass_flow_kg_s, i, wi, j, wj)
        expected_efficiency = _bilinear(self.component_map.isentropic_efficiency, i, wi, j, wj)
        flow = finite(self.corrected_mass_flow_kg_s, "corrected mass flow", positive=True)
        efficiency = finite(self.isentropic_efficiency, "isentropic efficiency", positive=True)
        if not math.isclose(flow, expected_flow, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Corrected flow differs from the source-grid interpolation")
        if not math.isclose(efficiency, expected_efficiency, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Efficiency differs from the source-grid interpolation")
        if efficiency > 1.0:
            raise ValueError("Isentropic efficiency cannot exceed one")
        object.__setattr__(self, "corrected_speed", speed)
        object.__setattr__(self, "compression_pressure_ratio", ratio)
        object.__setattr__(self, "corrected_mass_flow_kg_s", expected_flow)
        object.__setattr__(self, "isentropic_efficiency", expected_efficiency)

    def require_current(self):
        self.component_map.require_current()
        # Reconstruction catches field edits without calling any process model.
        CompressorMapPoint(
            component_map=self.component_map,
            corrected_speed=self.corrected_speed,
            compression_pressure_ratio=self.compression_pressure_ratio,
            corrected_mass_flow_kg_s=self.corrected_mass_flow_kg_s,
            isentropic_efficiency=self.isentropic_efficiency,
        )
        return self


def interpolate_compressor_map(component_map: CompressorComponentMap, *, corrected_speed: float,
                                compression_pressure_ratio: float) -> CompressorMapPoint:
    """Interpolate within the supplied rectangle and reject all extrapolation."""
    if type(component_map) is not CompressorComponentMap:
        raise TypeError("component_map must be a CompressorComponentMap")
    component_map.require_current()
    speed = finite(corrected_speed, "corrected speed", positive=True)
    ratio = finite(compression_pressure_ratio, "compression pressure ratio", positive=True)
    i, wi = _bracket(component_map.corrected_speed, speed, "corrected speed")
    j, wj = _bracket(component_map.compression_pressure_ratio, ratio,
                      "compression pressure ratio")
    return CompressorMapPoint(
        component_map, speed, ratio,
        _bilinear(component_map.corrected_mass_flow_kg_s, i, wi, j, wj),
        _bilinear(component_map.isentropic_efficiency, i, wi, j, wj),
    )


@dataclass(frozen=True, slots=True)
class MapMatchedBraytonInputs:
    """Caller-selected component-map points for one existing steady Brayton run.

    The two corrected-speed coordinates are linked by an explicit evidence ID;
    their numerical equality is not assumed because map correction references
    can differ. Flow conversion factors are similarly caller-owned.
    """

    cycle_inputs: object
    compressor_map: CompressorComponentMap
    compressor_corrected_speed: float
    compressor_pressure_ratio: float
    compressor_actual_to_corrected_flow_factor: float
    turbine_map: TurbineComponentMap
    turbine_corrected_speed: float
    turbine_actual_to_corrected_flow_factor: float
    air_mass_flow_kg_s: float
    speed_link_evidence_id: str
    compressor_flow_evidence_id: str
    turbine_flow_evidence_id: str
    relative_flow_tolerance: float = 1e-3
    absolute_flow_tolerance_kg_s: float = 1e-6
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        from .open_brayton import OpenBraytonInputs

        if type(self.cycle_inputs) is not OpenBraytonInputs:
            raise TypeError("cycle_inputs must be OpenBraytonInputs")
        if type(self.compressor_map) is not CompressorComponentMap:
            raise TypeError("compressor_map must be CompressorComponentMap")
        if type(self.turbine_map) is not TurbineComponentMap:
            raise TypeError("turbine_map must be TurbineComponentMap")
        self.compressor_map.require_current()
        self.turbine_map.require_current()
        if self.turbine_map.pressure_ratio_convention != "inlet-over-exit-total-pressure":
            raise ValueError("The existing Brayton boundary requires inlet-over-exit turbine ratio")
        for name in ("speed_link_evidence_id", "compressor_flow_evidence_id", "turbine_flow_evidence_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("compressor_corrected_speed", "turbine_corrected_speed",
                     "compressor_actual_to_corrected_flow_factor",
                     "turbine_actual_to_corrected_flow_factor", "air_mass_flow_kg_s"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        ratio = finite(self.compressor_pressure_ratio, "compressor pressure ratio", positive=True)
        if ratio <= 1.0:
            raise ValueError("Compressor pressure ratio must exceed one")
        object.__setattr__(self, "compressor_pressure_ratio", ratio)
        relative = finite(self.relative_flow_tolerance, "relative flow tolerance", positive=True)
        absolute = finite(self.absolute_flow_tolerance_kg_s, "absolute flow tolerance", positive=True)
        if relative > 0.1:
            raise ValueError("Relative flow tolerance cannot exceed 0.1")
        object.__setattr__(self, "relative_flow_tolerance", relative)
        object.__setattr__(self, "absolute_flow_tolerance_kg_s", absolute)
        point = interpolate_compressor_map(
            self.compressor_map, corrected_speed=self.compressor_corrected_speed,
            compression_pressure_ratio=ratio)
        corrected_air_flow = self.air_mass_flow_kg_s * self.compressor_actual_to_corrected_flow_factor
        if not math.isclose(corrected_air_flow, point.corrected_mass_flow_kg_s,
                            rel_tol=relative, abs_tol=absolute):
            raise ValueError("Declared compressor air flow does not match the selected map point")
        payload = self._payload()
        if self._seal and self._seal != payload:
            raise ValueError("Map-matched input declarations changed after admission")
        if not self._seal:
            object.__setattr__(self, "_seal", payload)

    def _payload(self):
        return (
            id(self.cycle_inputs), repr(self.cycle_inputs), id(self.compressor_map),
            self.compressor_corrected_speed, self.compressor_pressure_ratio,
            self.compressor_actual_to_corrected_flow_factor, id(self.turbine_map),
            self.turbine_corrected_speed, self.turbine_actual_to_corrected_flow_factor,
            self.air_mass_flow_kg_s, self.speed_link_evidence_id,
            self.compressor_flow_evidence_id, self.turbine_flow_evidence_id,
            self.relative_flow_tolerance, self.absolute_flow_tolerance_kg_s,
        )

    def require_current(self):
        self.compressor_map.require_current()
        self.turbine_map.require_current()
        if not self._seal or self._seal != self._payload():
            raise ValueError("Map-matched input declarations changed after admission")
        return self


@dataclass(frozen=True, slots=True)
class MapMatchedBraytonRun:
    """Source-bound compressor/turbine map composition around the native cycle."""

    inputs: MapMatchedBraytonInputs
    compressor_point: CompressorMapPoint
    turbine_run: MapBoundBraytonRun
    shaft_ledger: CoupledShaftLedger
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_RUN_ISSUERS:
            raise ValueError("Use run_map_matched_brayton() to issue this composition")
        _PENDING_RUN_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        self._validate()
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (id(self.inputs), id(self.compressor_point), id(self.turbine_run),
                id(self.shaft_ledger), self.shaft_ledger.shaft_residual_w)

    def _validate(self):
        from dataclasses import replace

        self.inputs.require_current()
        self.compressor_point.require_current()
        self.turbine_run.require_current()
        self.shaft_ledger.require_current()
        expected_point = interpolate_compressor_map(
            self.inputs.compressor_map,
            corrected_speed=self.inputs.compressor_corrected_speed,
            compression_pressure_ratio=self.inputs.compressor_pressure_ratio)
        if self.compressor_point != expected_point:
            raise ValueError("Compressor point differs from the selected map interpolation")
        if self.compressor_point.component_map is not self.inputs.compressor_map:
            raise ValueError("Compressor map point is detached from the admitted map")
        mapped_cycle = replace(
            self.inputs.cycle_inputs,
            compressor_pressure_ratio=expected_point.compression_pressure_ratio,
            compressor_isentropic_efficiency=expected_point.isentropic_efficiency,
        )
        if self.turbine_run.inputs.cycle_inputs != mapped_cycle:
            raise ValueError("Native cycle does not retain the selected compressor-map values")
        turbine_inputs = self.turbine_run.inputs
        if (turbine_inputs.component_map is not self.inputs.turbine_map
                or turbine_inputs.corrected_speed != self.inputs.turbine_corrected_speed
                or turbine_inputs.air_mass_flow_kg_s != self.inputs.air_mass_flow_kg_s
                or turbine_inputs.actual_to_corrected_flow_factor
                != self.inputs.turbine_actual_to_corrected_flow_factor):
            raise ValueError("Turbine map boundary differs from the admitted map-pair input")
        if self.shaft_ledger.turbine_run is not self.turbine_run:
            raise ValueError("Shaft ledger is detached from the mapped turbine run")
        compressor_point = self.shaft_ledger.compressor_point
        if (compressor_point.operating_point_id != self.inputs.cycle_inputs.process_window_id
                or compressor_point.evidence_id != self.inputs.compressor_map.evidence_id
                or compressor_point.shaft_speed_link_evidence_id != self.inputs.speed_link_evidence_id
                or compressor_point.flow_link_evidence_id != self.inputs.compressor_flow_evidence_id
                or not math.isclose(compressor_point.inlet_air_mass_flow_kg_s,
                                    self.inputs.air_mass_flow_kg_s, rel_tol=1e-12, abs_tol=1e-12)
                or not math.isclose(compressor_point.specific_work_j_kg_air,
                                    self.turbine_run.cycle_run.compressor_work_j_kg_air,
                                    rel_tol=1e-12, abs_tol=1e-9)):
            raise ValueError("Compressor shaft contribution is detached from the native mapped cycle")
        if self.turbine_run.inputs.speed_link_evidence_id != self.inputs.speed_link_evidence_id:
            raise ValueError("Compressor and turbine corrected-speed link evidence differ")
        if self.turbine_run.inputs.flow_conversion_evidence_id != self.inputs.turbine_flow_evidence_id:
            raise ValueError("Turbine flow-conversion evidence differs from the composition")
        return self

    def require_current(self):
        self._validate()
        if not self._seal or self._seal != self._payload():
            raise ValueError("Map-matched Brayton result changed after issuance")
        return self

    @property
    def shaft_residual_w(self):
        self.require_current()
        return self.shaft_ledger.shaft_residual_w


def run_map_matched_brayton(phase, inputs: MapMatchedBraytonInputs) -> MapMatchedBraytonRun:
    """Run existing Cantera/reference code using caller-selected component maps.

    This does not search for a common speed, correct map coordinates, or balance
    the shaft to zero. It reports the existing component power residual at the
    supplied operating point.
    """
    from dataclasses import replace

    if type(inputs) is not MapMatchedBraytonInputs:
        raise TypeError("Supply MapMatchedBraytonInputs")
    point = interpolate_compressor_map(
        inputs.compressor_map,
        corrected_speed=inputs.compressor_corrected_speed,
        compression_pressure_ratio=inputs.compressor_pressure_ratio)
    cycle_inputs = replace(
        inputs.cycle_inputs,
        compressor_pressure_ratio=point.compression_pressure_ratio,
        compressor_isentropic_efficiency=point.isentropic_efficiency,
    )
    turbine_inputs = MapBoundBraytonInputs(
        cycle_inputs=cycle_inputs,
        component_map=inputs.turbine_map,
        corrected_speed=inputs.turbine_corrected_speed,
        air_mass_flow_kg_s=inputs.air_mass_flow_kg_s,
        actual_to_corrected_flow_factor=inputs.turbine_actual_to_corrected_flow_factor,
        speed_link_evidence_id=inputs.speed_link_evidence_id,
        flow_conversion_evidence_id=inputs.turbine_flow_evidence_id,
        relative_flow_tolerance=inputs.relative_flow_tolerance,
        absolute_flow_tolerance_kg_s=inputs.absolute_flow_tolerance_kg_s,
    )
    turbine_run = run_map_bound_open_cycle_brayton(phase, turbine_inputs)
    compressor_operating_point = CompressorOperatingPoint(
        operating_point_id=cycle_inputs.process_window_id,
        process_window_id=cycle_inputs.process_window_id,
        evidence_id=inputs.compressor_map.evidence_id,
        shaft_speed_link_evidence_id=inputs.speed_link_evidence_id,
        flow_link_evidence_id=inputs.compressor_flow_evidence_id,
        specific_work_j_kg_air=turbine_run.cycle_run.compressor_work_j_kg_air,
        inlet_air_mass_flow_kg_s=inputs.air_mass_flow_kg_s,
    )
    shaft_ledger = couple_compressor_to_map_bound_brayton(turbine_run, compressor_operating_point)
    token = object()
    _PENDING_RUN_ISSUERS.add(token)
    try:
        return MapMatchedBraytonRun(inputs, point, turbine_run, shaft_ledger, token)
    except Exception:
        _PENDING_RUN_ISSUERS.discard(token)
        raise
