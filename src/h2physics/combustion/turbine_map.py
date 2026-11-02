"""Strict rectangular gas-turbine component-map interpolation.

This module admits and interpolates caller-owned map observations. It does not
predict a turbine map, extrapolate outside its domain, or couple a shaft/cycle.
Map convention and data provenance remain explicit caller responsibilities.
"""

import math
from dataclasses import dataclass, field

from ..core import finite


def _identity(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name} identity")
    return value.strip()


def _axis(values, name):
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a sequence of finite values")
    result = tuple(finite(value, f"{name} value") for value in values)
    if len(result) < 2:
        raise ValueError(f"{name} needs at least two coordinates")
    if any(right <= left for left, right in zip(result, result[1:])):
        raise ValueError(f"{name} coordinates must be strictly increasing")
    return result


def _matrix(values, n_speed, n_ratio, name):
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a rectangular matrix")
    rows = tuple(tuple(finite(value, f"{name} value") for value in row) for row in values)
    if len(rows) != n_speed or any(len(row) != n_ratio for row in rows):
        raise ValueError(f"{name} dimensions must match speed and pressure-ratio coordinates")
    return rows


def _bracket(axis, value, name):
    value = finite(value, name)
    if value < axis[0] or value > axis[-1]:
        raise ValueError(f"{name} lies outside the supplied map domain")
    for index in range(len(axis) - 1):
        if value <= axis[index + 1]:
            fraction = (value - axis[index]) / (axis[index + 1] - axis[index])
            return index, fraction
    return len(axis) - 2, 1.0


def _bilinear(matrix, i, wi, j, wj):
    lower = matrix[i][j] * (1.0 - wj) + matrix[i][j + 1] * wj
    upper = matrix[i + 1][j] * (1.0 - wj) + matrix[i + 1][j + 1] * wj
    return lower * (1.0 - wi) + upper * wi


@dataclass(frozen=True, slots=True)
class TurbineComponentMap:
    """Caller-provided corrected-flow and efficiency map on a rectangular grid.

    Rows index ``corrected_speed`` and columns index ``expansion_pressure_ratio``.
    The pressure-ratio convention, correction basis, units, and evidence identity
    are mandatory metadata; this type assigns no universal map convention.
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
    expansion_pressure_ratio: tuple[float, ...]
    corrected_mass_flow_kg_s: tuple[tuple[float, ...], ...]
    isentropic_efficiency: tuple[tuple[float, ...], ...]
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._seal and self._payload() != self._seal:
            raise ValueError("Turbine map changed after source admission")
        for field_name in ("map_id", "evidence_id", "source_uri", "license_id", "speed_unit", "pressure_ratio_convention", "corrected_mass_flow_basis"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare turbine-map {field_name}")
            object.__setattr__(self, field_name, value.strip())
        digest = self.source_sha256
        if not isinstance(digest, str) or len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest.lower()
        ):
            raise ValueError("source_sha256 must identify the turbine-map evidence bytes")
        object.__setattr__(self, "source_sha256", digest.lower())
        speed = _axis(self.corrected_speed, "corrected speed")
        ratio = _axis(self.expansion_pressure_ratio, "expansion pressure ratio")
        if speed[0] <= 0.0:
            raise ValueError("corrected-speed coordinates must be positive")
        if ratio[0] <= 1.0:
            raise ValueError("expansion pressure ratios must exceed one")
        flow = _matrix(self.corrected_mass_flow_kg_s, len(speed), len(ratio), "corrected mass flow")
        efficiency = _matrix(self.isentropic_efficiency, len(speed), len(ratio), "isentropic efficiency")
        if any(value <= 0.0 for row in flow for value in row):
            raise ValueError("corrected mass-flow values must be positive")
        if any(value <= 0.0 or value > 1.0 for row in efficiency for value in row):
            raise ValueError("isentropic efficiencies must be in (0, 1]")
        object.__setattr__(self, "corrected_speed", speed)
        object.__setattr__(self, "expansion_pressure_ratio", ratio)
        object.__setattr__(self, "corrected_mass_flow_kg_s", flow)
        object.__setattr__(self, "isentropic_efficiency", efficiency)

        if not self._seal:
            object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return tuple(getattr(self, name) for name in (
            "map_id", "evidence_id", "source_uri", "license_id", "source_sha256",
            "speed_unit", "pressure_ratio_convention", "corrected_mass_flow_basis",
            "corrected_speed", "expansion_pressure_ratio", "corrected_mass_flow_kg_s",
            "isentropic_efficiency",
        ))

    def require_current(self):
        """Reject relabeled or replaced map data before interpolation or binding."""
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Turbine map changed after source admission")
        return self


@dataclass(frozen=True, slots=True)
class TurbineMapPoint:
    """Interpolated map point retaining and rechecking its complete map source."""

    component_map: TurbineComponentMap
    corrected_speed: float
    expansion_pressure_ratio: float
    corrected_mass_flow_kg_s: float
    isentropic_efficiency: float

    def __post_init__(self):
        if not isinstance(self.component_map, TurbineComponentMap):
            raise TypeError("component_map must be a TurbineComponentMap")
        self.component_map.require_current()
        speed = finite(self.corrected_speed, "corrected speed")
        ratio = finite(self.expansion_pressure_ratio, "expansion pressure ratio")
        i, wi = _bracket(self.component_map.corrected_speed, speed, "corrected speed")
        j, wj = _bracket(self.component_map.expansion_pressure_ratio, ratio, "expansion pressure ratio")
        flow = _bilinear(self.component_map.corrected_mass_flow_kg_s, i, wi, j, wj)
        efficiency = _bilinear(self.component_map.isentropic_efficiency, i, wi, j, wj)
        supplied_flow = finite(self.corrected_mass_flow_kg_s, "corrected mass flow")
        supplied_efficiency = finite(self.isentropic_efficiency, "isentropic efficiency")
        if not math.isclose(supplied_flow, flow, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("corrected mass flow differs from retained component-map interpolation")
        if not math.isclose(supplied_efficiency, efficiency, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("efficiency differs from retained component-map interpolation")
        object.__setattr__(self, "corrected_speed", speed)
        object.__setattr__(self, "expansion_pressure_ratio", ratio)
        object.__setattr__(self, "corrected_mass_flow_kg_s", flow)
        object.__setattr__(self, "isentropic_efficiency", efficiency)

    def require_current(self):
        """Recheck the retained source map and interpolation without running a cycle."""
        self.component_map.require_current()
        # Reconstruction detects edits to the point coordinates or copied values.
        TurbineMapPoint(
            component_map=self.component_map,
            corrected_speed=self.corrected_speed,
            expansion_pressure_ratio=self.expansion_pressure_ratio,
            corrected_mass_flow_kg_s=self.corrected_mass_flow_kg_s,
            isentropic_efficiency=self.isentropic_efficiency,
        )
        return self


@dataclass(frozen=True, slots=True)
class MapBoundBraytonInputs:
    """Join a caller map point to the explicit single-point Brayton reference.

    The flow conversion factor is caller-provided because corrected-flow
    conventions vary by map owner. It converts actual turbine kg/s to the map's
    declared corrected-flow basis; this API does not infer reference conditions.
    Only the documented inlet-over-exit total-pressure-ratio convention is
    admitted for comparison with the cycle boundary.
    """

    cycle_inputs: object
    component_map: TurbineComponentMap
    corrected_speed: float
    air_mass_flow_kg_s: float
    actual_to_corrected_flow_factor: float
    speed_link_evidence_id: str
    flow_conversion_evidence_id: str
    relative_flow_tolerance: float = 1e-3
    absolute_flow_tolerance_kg_s: float = 1e-6

    def __post_init__(self):
        from .open_brayton import OpenBraytonInputs

        if type(self.cycle_inputs) is not OpenBraytonInputs:
            raise TypeError("cycle_inputs must be validated OpenBraytonInputs")
        if type(self.component_map) is not TurbineComponentMap:
            raise TypeError("component_map must be a TurbineComponentMap")
        self.component_map.require_current()
        if self.component_map.pressure_ratio_convention != "inlet-over-exit-total-pressure":
            raise ValueError("Map must use inlet-over-exit total-pressure ratio for this cycle binding")
        object.__setattr__(self, "corrected_speed", finite(self.corrected_speed,
                                                           "map corrected speed", positive=True))
        object.__setattr__(self, "air_mass_flow_kg_s", finite(self.air_mass_flow_kg_s,
                                                               "air mass flow", positive=True))
        object.__setattr__(self, "actual_to_corrected_flow_factor", finite(
            self.actual_to_corrected_flow_factor, "actual-to-corrected flow factor", positive=True))
        object.__setattr__(self, "speed_link_evidence_id", _identity(
            self.speed_link_evidence_id, "map speed link evidence"))
        object.__setattr__(self, "flow_conversion_evidence_id", _identity(
            self.flow_conversion_evidence_id, "map flow conversion evidence"))
        relative = finite(self.relative_flow_tolerance, "relative map-flow tolerance", positive=True)
        absolute = finite(self.absolute_flow_tolerance_kg_s, "absolute map-flow tolerance", positive=True)
        if relative > 0.1:
            raise ValueError("Relative map-flow tolerance cannot exceed 0.1")
        object.__setattr__(self, "relative_flow_tolerance", relative)
        object.__setattr__(self, "absolute_flow_tolerance_kg_s", absolute)
        compressor_pressure = (self.cycle_inputs.air_pressure_pa
                              * self.cycle_inputs.compressor_pressure_ratio)
        combustor_pressure = (compressor_pressure
                              * self.cycle_inputs.combustor_pressure_recovery)
        expected_ratio = combustor_pressure / self.cycle_inputs.turbine_exhaust_pressure_pa
        interpolate_turbine_map(self.component_map, corrected_speed=self.corrected_speed,
                                expansion_pressure_ratio=expected_ratio)


@dataclass(frozen=True, slots=True)
class MapBoundBraytonRun:
    """Single-point Brayton result with an admitted turbine-map flow/efficiency.

    This proves map-to-cycle boundary consistency under caller evidence. It is
    not a compressor-map coupling, shaft solution, or machine qualification.
    """

    inputs: MapBoundBraytonInputs
    map_point: TurbineMapPoint
    cycle_run: object
    actual_turbine_mass_flow_kg_s: float
    corrected_turbine_mass_flow_kg_s: float

    def __post_init__(self):
        from .open_brayton import OpenBraytonRun

        if type(self.inputs) is not MapBoundBraytonInputs:
            raise TypeError("Retain typed map-bound cycle inputs")
        if type(self.map_point) is not TurbineMapPoint:
            raise TypeError("Retain the interpolated turbine map point")
        if type(self.cycle_run) is not OpenBraytonRun:
            raise TypeError("Retain the original open Brayton cycle result")
        self._validate_values()

    def _validate_values(self):
        from dataclasses import replace

        inputs = self.inputs
        expected_ratio = (inputs.cycle_inputs.air_pressure_pa
                          * inputs.cycle_inputs.compressor_pressure_ratio
                          * inputs.cycle_inputs.combustor_pressure_recovery
                          / inputs.cycle_inputs.turbine_exhaust_pressure_pa)
        point = self.map_point
        if (point.component_map is not inputs.component_map
                or point.corrected_speed != inputs.corrected_speed):
            raise ValueError("Retained map point is detached from the declared component map/speed")
        expected_point = interpolate_turbine_map(
            inputs.component_map, corrected_speed=inputs.corrected_speed,
            expansion_pressure_ratio=expected_ratio)
        if (point.expansion_pressure_ratio != expected_point.expansion_pressure_ratio
                or point.corrected_mass_flow_kg_s != expected_point.corrected_mass_flow_kg_s
                or point.isentropic_efficiency != expected_point.isentropic_efficiency):
            raise ValueError("Retained map point differs from its source-grid interpolation")
        actual = inputs.air_mass_flow_kg_s * (1.0 + inputs.cycle_inputs.hydrogen_fuel_to_air_mass_ratio)
        corrected = actual * inputs.actual_to_corrected_flow_factor
        actual_supplied = finite(self.actual_turbine_mass_flow_kg_s,
                                 "actual turbine mass flow", positive=True)
        corrected_supplied = finite(self.corrected_turbine_mass_flow_kg_s,
                                    "corrected turbine mass flow", positive=True)
        if not math.isclose(actual_supplied, actual, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Actual turbine flow differs from air plus declared hydrogen feed")
        if not math.isclose(corrected_supplied, corrected, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Corrected turbine flow differs from caller's conversion factor")
        if not math.isclose(corrected, point.corrected_mass_flow_kg_s,
                            rel_tol=self.inputs.relative_flow_tolerance,
                            abs_tol=self.inputs.absolute_flow_tolerance_kg_s):
            raise ValueError("Cycle turbine flow does not match the admitted map point")
        expected_cycle_inputs = replace(
            inputs.cycle_inputs,
            turbine_isentropic_efficiency=point.isentropic_efficiency,
        )
        if self.cycle_run.inputs != expected_cycle_inputs:
            raise ValueError("Cycle run does not retain the exact declared inputs and mapped turbine efficiency")
        if (not math.isclose(self.cycle_run.states[3].pressure_pa
                             / self.cycle_run.states[4].pressure_pa,
                             point.expansion_pressure_ratio, rel_tol=1e-10, abs_tol=1e-12)):
            raise ValueError("Cycle station pressure ratio differs from the mapped expansion point")
        if (self.cycle_run.inputs.mechanism_id != self.inputs.cycle_inputs.mechanism_id
                or self.cycle_run.inputs.process_window_id != self.inputs.cycle_inputs.process_window_id):
            raise ValueError("Map-bound cycle result lost its declared mechanism/window")
        object.__setattr__(self, "actual_turbine_mass_flow_kg_s", actual)
        object.__setattr__(self, "corrected_turbine_mass_flow_kg_s", corrected)

    def require_current(self):
        self.cycle_run.require_current()
        self._validate_values()
        return self

    @property
    def compressor_power_w(self):
        """Reference compressor input power at the declared inlet-air flow.

        This scales the existing per-kilogram-of-air cycle ledger. It excludes
        auxiliary, fuel-compression, and mechanical losses.
        """
        self.require_current()
        return self.cycle_run.compressor_work_j_kg_air * self.inputs.air_mass_flow_kg_s

    @property
    def turbine_gross_power_w(self):
        """Reference turbine gross power before cooling, bleed, and shaft losses."""
        self.require_current()
        return self.cycle_run.turbine_work_j_kg_air * self.inputs.air_mass_flow_kg_s

    @property
    def net_gas_path_power_w(self):
        """Gross turbine power less compressor input for this reference boundary."""
        self.require_current()
        return self.cycle_run.net_work_j_kg_air * self.inputs.air_mass_flow_kg_s


@dataclass(frozen=True, slots=True)
class ShaftPowerBalanceInputs:
    """Evidence-bound conversion from a map-bound gas path to one shaft/output.

    Loss is an explicitly supplied shaft power in watts; generator efficiency is
    caller supplied. This does not solve component maps or machine controls.
    """

    cycle_run: MapBoundBraytonRun
    shaft_mechanical_loss_w: float
    generator_efficiency: float
    loss_evidence_id: str
    generator_evidence_id: str

    def __post_init__(self):
        if type(self.cycle_run) is not MapBoundBraytonRun:
            raise TypeError("cycle_run must be a map-bound Brayton result")
        self.cycle_run.require_current()
        loss = finite(self.shaft_mechanical_loss_w, "shaft mechanical loss")
        if loss < 0.0:
            raise ValueError("shaft mechanical loss cannot be negative")
        object.__setattr__(self, "shaft_mechanical_loss_w", loss)
        efficiency = finite(self.generator_efficiency, "generator efficiency", positive=True)
        if efficiency > 1.0:
            raise ValueError("generator efficiency cannot exceed one")
        object.__setattr__(self, "generator_efficiency", efficiency)
        object.__setattr__(self, "loss_evidence_id", _identity(self.loss_evidence_id, "shaft-loss evidence"))
        object.__setattr__(self, "generator_evidence_id", _identity(self.generator_evidence_id, "generator evidence"))


@dataclass(frozen=True, slots=True)
class ShaftPowerBalance:
    """Auditable steady shaft and electrical power ledger for one admitted point."""

    inputs: ShaftPowerBalanceInputs
    turbine_power_w: float
    compressor_power_w: float
    gas_path_net_power_w: float
    shaft_net_power_w: float
    electric_power_w: float

    def __post_init__(self):
        self.require_current()

    def require_current(self):
        run = self.inputs.cycle_run
        run.require_current()
        turbine = run.turbine_gross_power_w
        compressor = run.compressor_power_w
        gas_net = turbine - compressor
        shaft_net = gas_net - self.inputs.shaft_mechanical_loss_w
        electric = shaft_net * self.inputs.generator_efficiency
        actuals = (self.turbine_power_w, self.compressor_power_w,
                   self.gas_path_net_power_w, self.shaft_net_power_w, self.electric_power_w)
        expected = (turbine, compressor, gas_net, shaft_net, electric)
        for label, actual, value in zip(("turbine power", "compressor power", "gas-path net power", "shaft net power", "electric power"), actuals, expected):
            actual = finite(actual, label)
            if not math.isclose(actual, value, rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError(f"{label} differs from its retained power-balance inputs")
        if shaft_net < 0.0:
            raise ValueError("shaft losses exceed available gas-path net power")
        for name, value in zip(("turbine_power_w", "compressor_power_w", "gas_path_net_power_w", "shaft_net_power_w", "electric_power_w"), expected):
            object.__setattr__(self, name, value)
        return self


@dataclass(frozen=True, slots=True)
class CompressorOperatingPoint:
    """Caller-adapted compressor result at the same declared shaft operating point.

    The adapter must supply specific work on a kg-of-inlet-air basis and the
    matching inlet-air mass flow. This type intentionally owns no compressor map.
    """

    operating_point_id: str
    process_window_id: str
    evidence_id: str
    shaft_speed_link_evidence_id: str
    flow_link_evidence_id: str
    specific_work_j_kg_air: float
    inlet_air_mass_flow_kg_s: float

    def __post_init__(self):
        for name in ("operating_point_id", "process_window_id", "evidence_id",
                     "shaft_speed_link_evidence_id", "flow_link_evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        object.__setattr__(self, "specific_work_j_kg_air", finite(
            self.specific_work_j_kg_air, "compressor specific work", positive=True))
        object.__setattr__(self, "inlet_air_mass_flow_kg_s", finite(
            self.inlet_air_mass_flow_kg_s, "compressor inlet air flow", positive=True))


@dataclass(frozen=True, slots=True)
class CoupledShaftLedger:
    """Compares independently owned compressor and turbine results at one point."""

    turbine_run: MapBoundBraytonRun
    compressor_point: CompressorOperatingPoint
    compressor_power_w: float
    turbine_power_w: float
    shaft_residual_w: float
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        self.require_current()

    def require_current(self):
        self.turbine_run.require_current()
        point = self.compressor_point
        cycle = self.turbine_run.inputs.cycle_inputs
        if point.process_window_id != cycle.process_window_id:
            raise ValueError("Compressor and turbine process windows differ")
        if point.operating_point_id != cycle.process_window_id:
            raise ValueError("Compressor point must identify the cycle operating point")
        air_flow = self.turbine_run.inputs.air_mass_flow_kg_s
        if not math.isclose(point.inlet_air_mass_flow_kg_s, air_flow, rel_tol=1e-8, abs_tol=1e-10):
            raise ValueError("Compressor and turbine inlet-air flow bases differ")
        compressor = point.specific_work_j_kg_air * air_flow
        turbine = self.turbine_run.turbine_gross_power_w
        residual = turbine - compressor
        for name, actual, expected in (("compressor power", self.compressor_power_w, compressor),
                                       ("turbine power", self.turbine_power_w, turbine),
                                       ("shaft residual", self.shaft_residual_w, residual)):
            if not math.isclose(finite(actual, name), expected, rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError(f"{name} differs from retained component results")
        object.__setattr__(self, "compressor_power_w", compressor)
        object.__setattr__(self, "turbine_power_w", turbine)
        object.__setattr__(self, "shaft_residual_w", residual)
        payload = (id(self.turbine_run), id(point), compressor, turbine, residual)
        if self._seal and self._seal != payload:
            raise ValueError("Coupled shaft ledger changed after issuance")
        if not self._seal:
            object.__setattr__(self, "_seal", payload)
        return self


def couple_compressor_to_map_bound_brayton(turbine_run, compressor_point):
    """Join explicit compressor output to turbine output; residual is not closure."""
    if type(turbine_run) is not MapBoundBraytonRun:
        raise TypeError("Supply a map-bound Brayton turbine result")
    if type(compressor_point) is not CompressorOperatingPoint:
        raise TypeError("Supply an evidence-bound compressor operating point")
    compressor_point.__post_init__()
    compressor_power = compressor_point.specific_work_j_kg_air * compressor_point.inlet_air_mass_flow_kg_s
    turbine_power = turbine_run.turbine_gross_power_w
    return CoupledShaftLedger(turbine_run, compressor_point, compressor_power,
                              turbine_power, turbine_power - compressor_power)


def balance_map_bound_brayton_shaft(inputs: ShaftPowerBalanceInputs) -> ShaftPowerBalance:
    """Apply explicit shaft loss and generator conversion to an admitted cycle."""
    if type(inputs) is not ShaftPowerBalanceInputs:
        raise TypeError("Supply ShaftPowerBalanceInputs")
    inputs.cycle_run.require_current()
    turbine = inputs.cycle_run.turbine_gross_power_w
    compressor = inputs.cycle_run.compressor_power_w
    gas_net = turbine - compressor
    shaft_net = gas_net - inputs.shaft_mechanical_loss_w
    if shaft_net < 0.0:
        raise ValueError("shaft losses exceed available gas-path net power")
    return ShaftPowerBalance(inputs, turbine, compressor, gas_net, shaft_net,
                             shaft_net * inputs.generator_efficiency)


def run_map_bound_open_cycle_brayton(phase, inputs: MapBoundBraytonInputs) -> MapBoundBraytonRun:
    """Run the existing open reference after admitting one turbine map point.

    Compressor efficiency remains caller-supplied. The supplied map point sets
    turbine efficiency and must match the cycle pressure ratio and corrected flow
    after an explicit caller-evidenced correction factor. No shaft balance is
    calculated.
    """
    from dataclasses import replace

    from .open_brayton import run_open_cycle_brayton

    if type(inputs) is not MapBoundBraytonInputs:
        raise TypeError("Supply MapBoundBraytonInputs")
    cycle = inputs.cycle_inputs
    ratio = (cycle.air_pressure_pa * cycle.compressor_pressure_ratio
             * cycle.combustor_pressure_recovery / cycle.turbine_exhaust_pressure_pa)
    point = interpolate_turbine_map(inputs.component_map,
                                    corrected_speed=inputs.corrected_speed,
                                    expansion_pressure_ratio=ratio)
    actual_flow = inputs.air_mass_flow_kg_s * (1.0 + cycle.hydrogen_fuel_to_air_mass_ratio)
    corrected_flow = actual_flow * inputs.actual_to_corrected_flow_factor
    if not math.isclose(corrected_flow, point.corrected_mass_flow_kg_s,
                        rel_tol=inputs.relative_flow_tolerance,
                        abs_tol=inputs.absolute_flow_tolerance_kg_s):
        raise ValueError("Cycle turbine flow lies outside the selected map point tolerance")
    mapped_cycle_inputs = replace(cycle, turbine_isentropic_efficiency=point.isentropic_efficiency)
    run = run_open_cycle_brayton(phase, mapped_cycle_inputs)
    return MapBoundBraytonRun(inputs, point, run, actual_flow, corrected_flow)


def interpolate_turbine_map(component_map: TurbineComponentMap, *, corrected_speed: float, expansion_pressure_ratio: float) -> TurbineMapPoint:
    """Return bilinear map values, rejecting all extrapolation and malformed maps."""

    if not isinstance(component_map, TurbineComponentMap):
        raise TypeError("component_map must be a TurbineComponentMap")
    component_map.require_current()
    speed = finite(corrected_speed, "corrected speed")
    ratio = finite(expansion_pressure_ratio, "expansion pressure ratio")
    i, wi = _bracket(component_map.corrected_speed, speed, "corrected speed")
    j, wj = _bracket(component_map.expansion_pressure_ratio, ratio, "expansion pressure ratio")
    return TurbineMapPoint(
        component_map=component_map,
        corrected_speed=speed,
        expansion_pressure_ratio=ratio,
        corrected_mass_flow_kg_s=_bilinear(component_map.corrected_mass_flow_kg_s, i, wi, j, wj),
        isentropic_efficiency=_bilinear(component_map.isentropic_efficiency, i, wi, j, wj),
    )


@dataclass(frozen=True, slots=True)
class TurbineMapPairingReceipt:
    """Evidence-bound pairing of separately owned compressor and turbine observations.

    This receipt aligns two admitted component observations to one caller-named
    operating point. The link evidence is explicit because the component APIs use
    independently owned coordinates and do not prove a common shaft, flow basis,
    pressure convention, clock, or process window. No mass, work, or shaft balance
    is inferred by this type.
    """

    pairing_id: str
    process_window_id: str
    clock_window_link_evidence_id: str
    component_pairing_evidence_id: str
    shaft_speed_basis_link_evidence_id: str
    flow_basis_link_evidence_id: str
    pressure_ratio_basis_link_evidence_id: str
    compressor_trace: object
    compressor_point_index: int
    turbine_point: TurbineMapPoint
    _seal: tuple | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        for name in (
            "pairing_id", "process_window_id", "clock_window_link_evidence_id",
            "component_pairing_evidence_id", "shaft_speed_basis_link_evidence_id",
            "flow_basis_link_evidence_id", "pressure_ratio_basis_link_evidence_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare turbine operating-point {name}")
            object.__setattr__(self, name, value.strip())

        # Import lazily: compressor equipment is an optional native adapter and
        # must not become a combustion package import-time dependency.
        from ..adapters.compressor_map import MappedCompressorTrace

        if type(self.compressor_trace) is not MappedCompressorTrace:
            raise TypeError("Retain an original MappedCompressorTrace")
        if type(self.turbine_point) is not TurbineMapPoint:
            raise TypeError("Retain an original TurbineMapPoint")
        if isinstance(self.compressor_point_index, bool) or not isinstance(self.compressor_point_index, int):
            raise TypeError("compressor_point_index must be an integer index")
        self.compressor_trace.require_current()
        if not 0 <= self.compressor_point_index < len(self.compressor_trace.points):
            raise ValueError("compressor_point_index is outside the admitted trace")
        point = self.compressor_trace.points[self.compressor_point_index]
        if point.command.mode != "compressing":
            raise ValueError("An isolated compressor record cannot be paired as an operating point")
        if point.corrected_flow_kg_s is None or point.corrected_speed_rad_s is None or point.limits is None:
            raise ValueError("The compressor observation must retain corrected map coordinates and limits")
        object.__setattr__(self, "_seal", self._current_seal())

    def _current_seal(self):
        compressor_point = self.compressor_trace.points[self.compressor_point_index]
        return (
            id(self.compressor_trace), self.compressor_trace.clock_id,
            self.compressor_trace.map_id, self.compressor_trace.evidence_id,
            self.compressor_point_index, compressor_point.command,
            compressor_point.corrected_flow_kg_s, compressor_point.corrected_speed_rad_s,
            id(compressor_point.native_result), id(self.turbine_point.component_map),
            repr(self.turbine_point.component_map), self.turbine_point.component_map.map_id,
            self.turbine_point.component_map.evidence_id,
            self.turbine_point.corrected_speed, self.turbine_point.expansion_pressure_ratio,
            self.turbine_point.corrected_mass_flow_kg_s, self.turbine_point.isentropic_efficiency,
            self.pairing_id, self.process_window_id,
            self.clock_window_link_evidence_id, self.component_pairing_evidence_id,
            self.shaft_speed_basis_link_evidence_id, self.flow_basis_link_evidence_id,
            self.pressure_ratio_basis_link_evidence_id,
        )

    def require_current(self):
        """Recheck the original native compressor trace and both retained maps."""
        self.compressor_trace.require_current()
        if type(self.turbine_point) is not TurbineMapPoint:
            raise TypeError("The retained turbine map observation changed type")
        self.turbine_point.require_current()
        current = self._current_seal()
        if self._seal != current:
            raise ValueError("The paired turbine operating-point receipt became stale")
        return self

    @property
    def compressor_observation(self):
        """Original compressor-map observation selected by this receipt."""
        self.require_current()
        return self.compressor_trace.points[self.compressor_point_index]

    @property
    def compressor_map_evidence_id(self):
        self.require_current()
        return self.compressor_trace.evidence_id

    @property
    def turbine_map_evidence_id(self):
        self.require_current()
        return self.turbine_point.component_map.evidence_id
