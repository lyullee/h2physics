"""One-point map-matched Brayton boundary with compressor-air cooling bleed.

The module reuses the existing Cantera compressor/combustor reference and map
interpolation. A declared portion of compressor discharge bypasses the combustor
and mixes once at the turbine inlet. This is a station-level conservation
composition, not a staged turbine cooling or blade-film model.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from .compressor_map import CompressorComponentMap, CompressorMapPoint, interpolate_compressor_map
from .open_brayton import OpenBraytonInputs, OpenBraytonRun, run_open_cycle_brayton
from .turbine_map import TurbineComponentMap, TurbineMapPoint, interpolate_turbine_map

_PENDING = set()


def _identity(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name} evidence identity")
    return value.strip()


@dataclass(frozen=True, slots=True)
class CoolingBleedInputs:
    """Caller-owned map coordinates and a single compressor-air bleed boundary.

    The air and hydrogen rates are actual kg/s at the declared stations. The
    cooling stream is a fraction of compressor inlet air, sampled at the native
    compressor-discharge state and throttled isenthalpically to the declared
    injection pressure. Map correction and speed-link conventions are supplied
    by the caller rather than inferred.
    """

    cycle_inputs: OpenBraytonInputs
    compressor_map: CompressorComponentMap
    turbine_map: TurbineComponentMap
    compressor_corrected_speed: float
    compressor_pressure_ratio: float
    turbine_corrected_speed: float
    turbine_to_compressor_corrected_speed_ratio: float
    compressor_actual_to_corrected_flow_factor: float
    turbine_actual_to_corrected_flow_factor: float
    air_mass_flow_kg_s: float
    hydrogen_mass_flow_kg_s: float
    cooling_air_fraction: float
    cooling_line_pressure_drop_pa: float
    shaft_mechanical_loss_w: float
    shaft_power_target_w: float
    speed_link_evidence_id: str
    compressor_flow_evidence_id: str
    turbine_flow_evidence_id: str
    hydrogen_mass_flow_evidence_id: str
    cooling_split_evidence_id: str
    cooling_pressure_evidence_id: str
    shaft_loss_evidence_id: str
    shaft_target_evidence_id: str
    flow_relative_tolerance: float = 1e-3
    flow_absolute_tolerance_kg_s: float = 1e-6
    energy_absolute_tolerance_w: float = 1e-2
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.cycle_inputs) is not OpenBraytonInputs:
            raise TypeError("cycle_inputs must be OpenBraytonInputs")
        if type(self.compressor_map) is not CompressorComponentMap:
            raise TypeError("Supply an admitted compressor component map")
        if type(self.turbine_map) is not TurbineComponentMap:
            raise TypeError("Supply an admitted turbine component map")
        self.compressor_map.require_current()
        self.turbine_map.require_current()
        if self.turbine_map.pressure_ratio_convention != "inlet-over-exit-total-pressure":
            raise ValueError("Turbine map must declare inlet-over-exit total-pressure ratio")
        for name in ("speed_link_evidence_id", "compressor_flow_evidence_id",
                     "turbine_flow_evidence_id", "hydrogen_mass_flow_evidence_id",
                     "cooling_split_evidence_id",
                     "cooling_pressure_evidence_id", "shaft_loss_evidence_id",
                     "shaft_target_evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        for name in ("compressor_corrected_speed", "compressor_pressure_ratio",
                     "turbine_corrected_speed", "turbine_to_compressor_corrected_speed_ratio",
                     "compressor_actual_to_corrected_flow_factor",
                     "turbine_actual_to_corrected_flow_factor", "air_mass_flow_kg_s",
                     "hydrogen_mass_flow_kg_s"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        if self.compressor_pressure_ratio <= 1.:
            raise ValueError("Compressor pressure ratio must exceed one")
        expected_turbine_speed = (self.compressor_corrected_speed
                                  * self.turbine_to_compressor_corrected_speed_ratio)
        if not math.isclose(expected_turbine_speed, self.turbine_corrected_speed,
                            rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Declared turbine speed differs from the evidence-bound corrected-speed link")
        fraction = finite(self.cooling_air_fraction, "compressor-air bleed fraction")
        if not 0. <= fraction < 1.:
            raise ValueError("Cooling bleed fraction must lie in [0, 1)")
        object.__setattr__(self, "cooling_air_fraction", fraction)
        drop = finite(self.cooling_line_pressure_drop_pa, "cooling-line pressure drop")
        if drop < 0.:
            raise ValueError("Cooling-line pressure drop cannot be negative")
        object.__setattr__(self, "cooling_line_pressure_drop_pa", drop)
        loss = finite(self.shaft_mechanical_loss_w, "shaft mechanical loss")
        if loss < 0.:
            raise ValueError("Shaft mechanical loss cannot be negative")
        object.__setattr__(self, "shaft_mechanical_loss_w", loss)
        object.__setattr__(self, "shaft_power_target_w", finite(self.shaft_power_target_w,
                                                                  "shaft target power"))
        for name, label in (("flow_relative_tolerance", "flow relative tolerance"),
                             ("flow_absolute_tolerance_kg_s", "flow absolute tolerance"),
                             ("energy_absolute_tolerance_w", "energy residual tolerance")):
            value = finite(getattr(self, name), label, positive=True)
            if name == "flow_relative_tolerance" and value > .1:
                raise ValueError("Flow relative tolerance cannot exceed 0.1")
            object.__setattr__(self, name, value)
        comp_point = interpolate_compressor_map(
            self.compressor_map, corrected_speed=self.compressor_corrected_speed,
            compression_pressure_ratio=self.compressor_pressure_ratio)
        corrected_air = self.air_mass_flow_kg_s * self.compressor_actual_to_corrected_flow_factor
        if not math.isclose(corrected_air, comp_point.corrected_mass_flow_kg_s,
                            rel_tol=self.flow_relative_tolerance,
                            abs_tol=self.flow_absolute_tolerance_kg_s):
            raise ValueError("Compressor corrected air flow does not match the admitted map")
        ratio = (self.cycle_inputs.air_pressure_pa * self.compressor_pressure_ratio
                 * self.cycle_inputs.combustor_pressure_recovery
                 / self.cycle_inputs.turbine_exhaust_pressure_pa)
        interpolate_turbine_map(self.turbine_map, corrected_speed=self.turbine_corrected_speed,
                                expansion_pressure_ratio=ratio)
        compressor_discharge_pressure = (self.cycle_inputs.air_pressure_pa
                                         * self.compressor_pressure_ratio)
        turbine_inlet_pressure = compressor_discharge_pressure * self.cycle_inputs.combustor_pressure_recovery
        expected_cooling_pressure_drop = compressor_discharge_pressure - turbine_inlet_pressure
        if not math.isclose(drop, expected_cooling_pressure_drop,
                            rel_tol=1e-10, abs_tol=1e-3):
            raise ValueError("Cooling-path pressure drop must land exactly at the declared turbine inlet pressure")
        actual_turbine_flow = self.air_mass_flow_kg_s + self.hydrogen_mass_flow_kg_s
        turb_point = interpolate_turbine_map(
            self.turbine_map, corrected_speed=self.turbine_corrected_speed,
            expansion_pressure_ratio=ratio)
        corrected_turbine = actual_turbine_flow * self.turbine_actual_to_corrected_flow_factor
        if not math.isclose(corrected_turbine, turb_point.corrected_mass_flow_kg_s,
                            rel_tol=self.flow_relative_tolerance,
                            abs_tol=self.flow_absolute_tolerance_kg_s):
            raise ValueError("Total turbine corrected flow does not match the admitted map")
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (id(self.cycle_inputs), repr(self.cycle_inputs), id(self.compressor_map),
                id(self.turbine_map), self.compressor_corrected_speed,
                self.compressor_pressure_ratio, self.turbine_corrected_speed,
                self.turbine_to_compressor_corrected_speed_ratio,
                self.compressor_actual_to_corrected_flow_factor,
                self.turbine_actual_to_corrected_flow_factor, self.air_mass_flow_kg_s,
                self.hydrogen_mass_flow_kg_s, self.cooling_air_fraction,
                self.cooling_line_pressure_drop_pa, self.shaft_mechanical_loss_w,
                self.shaft_power_target_w, self.speed_link_evidence_id,
                self.compressor_flow_evidence_id, self.turbine_flow_evidence_id,
                self.hydrogen_mass_flow_evidence_id, self.cooling_split_evidence_id,
                self.cooling_pressure_evidence_id,
                self.shaft_loss_evidence_id, self.shaft_target_evidence_id,
                self.flow_relative_tolerance, self.flow_absolute_tolerance_kg_s,
                self.energy_absolute_tolerance_w)

    def require_current(self):
        self.compressor_map.require_current()
        self.turbine_map.require_current()
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Cooling-bleed input changed after admission")
        return self


@dataclass(frozen=True, slots=True)
class CoolingBleedBraytonRun:
    """Conservation-audited single turbine-inlet cooling mix around Cantera."""

    inputs: CoolingBleedInputs
    compressor_point: CompressorMapPoint
    turbine_point: TurbineMapPoint
    primary_cycle: OpenBraytonRun
    primary_air_mass_flow_kg_s: float
    cooling_air_mass_flow_kg_s: float
    turbine_gas_mass_flow_kg_s: float
    cooling_pressure_pa: float
    mixed_turbine_inlet_temperature_k: float
    mixed_turbine_inlet_pressure_pa: float
    mixed_turbine_inlet_enthalpy_j_kg: float
    mixed_turbine_inlet_entropy_j_kg_k: float
    mixed_species_mass_fractions: tuple[tuple[str, float], ...]
    mixed_elemental_mass_fractions: tuple[tuple[str, float], ...]
    isentropic_turbine_exhaust_enthalpy_j_kg: float
    turbine_exhaust_pressure_pa: float
    turbine_exhaust_temperature_k: float
    turbine_exhaust_enthalpy_j_kg: float
    compressor_power_w: float
    turbine_power_w: float
    shaft_residual_w: float
    compressor_flow_residual_kg_s: float
    turbine_flow_residual_kg_s: float
    mix_energy_residual_w: float
    elemental_mass_residuals_kg_s: tuple[tuple[str, float], ...]
    _issuer: object = field(repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Create cooling-bleed outputs through run_cooled_brayton_point")
        _PENDING.remove(self._issuer)
        self.require_current(check_seal=False)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (id(self.inputs), id(self.compressor_point), id(self.turbine_point),
                id(self.primary_cycle), self.primary_air_mass_flow_kg_s,
                self.cooling_air_mass_flow_kg_s, self.turbine_gas_mass_flow_kg_s,
                self.cooling_pressure_pa, self.mixed_turbine_inlet_temperature_k,
                self.mixed_turbine_inlet_pressure_pa, self.mixed_turbine_inlet_enthalpy_j_kg,
                self.mixed_turbine_inlet_entropy_j_kg_k, self.mixed_species_mass_fractions,
                self.mixed_elemental_mass_fractions,
                self.isentropic_turbine_exhaust_enthalpy_j_kg,
                self.turbine_exhaust_pressure_pa, self.turbine_exhaust_temperature_k,
                self.turbine_exhaust_enthalpy_j_kg,
                self.compressor_power_w, self.turbine_power_w, self.shaft_residual_w,
                self.compressor_flow_residual_kg_s, self.turbine_flow_residual_kg_s,
                self.mix_energy_residual_w, self.elemental_mass_residuals_kg_s)

    def require_current(self, *, check_seal=True):
        self.inputs.require_current()
        self.compressor_point.require_current()
        self.turbine_point.require_current()
        self.primary_cycle.require_current()
        if check_seal and (not self._seal or self._payload() != self._seal):
            raise ValueError("Cooling-bleed Brayton result changed after issuance")
        air = finite(self.inputs.air_mass_flow_kg_s, "total inlet air flow", positive=True)
        bleed = air * self.inputs.cooling_air_fraction
        primary = air - bleed
        gas = air + self.inputs.hydrogen_mass_flow_kg_s
        _close(self.primary_air_mass_flow_kg_s, primary, "primary combustor air flow")
        _close(self.cooling_air_mass_flow_kg_s, bleed, "compressor cooling bleed flow")
        _close(self.turbine_gas_mass_flow_kg_s, gas, "turbine gas flow")
        hot, cold = self.primary_cycle.states[3], self.primary_cycle.states[1]
        hot_flow = primary + self.inputs.hydrogen_mass_flow_kg_s
        expected_comp = interpolate_compressor_map(
            self.inputs.compressor_map,
            corrected_speed=self.inputs.compressor_corrected_speed,
            compression_pressure_ratio=self.inputs.compressor_pressure_ratio)
        expected_turb = interpolate_turbine_map(
            self.inputs.turbine_map,
            corrected_speed=self.inputs.turbine_corrected_speed,
            expansion_pressure_ratio=hot.pressure_pa / self.inputs.cycle_inputs.turbine_exhaust_pressure_pa)
        if self.compressor_point != expected_comp or self.turbine_point != expected_turb:
            raise ValueError("Retained component map points differ from the admitted operating coordinates")
        if (not math.isclose(self.primary_cycle.inputs.hydrogen_fuel_to_air_mass_ratio,
                             self.inputs.hydrogen_mass_flow_kg_s / primary,
                             rel_tol=1e-12, abs_tol=1e-14)
                or self.primary_cycle.inputs.compressor_isentropic_efficiency
                != expected_comp.isentropic_efficiency
                or self.primary_cycle.inputs.turbine_isentropic_efficiency
                != expected_turb.isentropic_efficiency):
            raise ValueError("Native primary cycle differs from the declared fuel and component-map inputs")
        _close(self.cooling_pressure_pa,
               cold.pressure_pa - self.inputs.cooling_line_pressure_drop_pa,
               "cooling-path outlet pressure")
        _close(self.cooling_pressure_pa, self.mixed_turbine_inlet_pressure_pa,
               "cooling injection pressure")
        mixed_h = (hot_flow * hot.enthalpy_j_kg + bleed * cold.enthalpy_j_kg) / gas
        _close(self.mixed_turbine_inlet_enthalpy_j_kg, mixed_h,
               "mixed turbine-inlet enthalpy")
        expected_species = (hot_flow * np.asarray(hot.mass_fractions)
                            + bleed * np.asarray(cold.mass_fractions)) / gas
        if (tuple(name for name, _ in self.mixed_species_mass_fractions) != hot.species_names
                or not np.allclose([v for _, v in self.mixed_species_mass_fractions],
                                   expected_species, rtol=1e-12, atol=1e-14)):
            raise ValueError("Mixed turbine-inlet species differ from the admitted streams")
        expected_elements = (hot_flow * np.asarray([v for _, v in hot.elemental_mass_fractions])
                             + bleed * np.asarray([v for _, v in cold.elemental_mass_fractions])) / gas
        if (tuple(name for name, _ in self.mixed_elemental_mass_fractions)
                != tuple(name for name, _ in hot.elemental_mass_fractions)
                or not np.allclose([v for _, v in self.mixed_elemental_mass_fractions],
                                   expected_elements, rtol=1e-12, atol=1e-14)):
            raise ValueError("Mixed turbine-inlet elements differ from the admitted streams")
        _close(self.turbine_exhaust_pressure_pa,
               self.inputs.cycle_inputs.turbine_exhaust_pressure_pa,
               "turbine exhaust pressure")
        _close(self.turbine_power_w,
               gas * (self.mixed_turbine_inlet_enthalpy_j_kg
                      - self.turbine_exhaust_enthalpy_j_kg),
               "turbine shaft power")
        _close(self.mix_energy_residual_w,
               gas * self.mixed_turbine_inlet_enthalpy_j_kg
               - hot_flow * hot.enthalpy_j_kg - bleed * cold.enthalpy_j_kg,
               "turbine-inlet mixer energy residual")
        expected_hout = (self.mixed_turbine_inlet_enthalpy_j_kg
                         - self.turbine_point.isentropic_efficiency
                         * (self.mixed_turbine_inlet_enthalpy_j_kg
                            - self.isentropic_turbine_exhaust_enthalpy_j_kg))
        _close(self.turbine_exhaust_enthalpy_j_kg, expected_hout,
               "map-efficiency turbine exhaust enthalpy")
        _close(self.compressor_flow_residual_kg_s,
               air * self.inputs.compressor_actual_to_corrected_flow_factor
               - self.compressor_point.corrected_mass_flow_kg_s,
               "compressor corrected flow residual")
        _close(self.turbine_flow_residual_kg_s,
               gas * self.inputs.turbine_actual_to_corrected_flow_factor
               - self.turbine_point.corrected_mass_flow_kg_s,
               "turbine corrected flow residual")
        _close(self.compressor_power_w,
               self.primary_cycle.compressor_work_j_kg_air * air,
               "compressor shaft power")
        expected_shaft = (self.turbine_power_w - self.compressor_power_w
                          - self.inputs.shaft_mechanical_loss_w
                          - self.inputs.shaft_power_target_w)
        _close(self.shaft_residual_w, expected_shaft, "shaft residual")
        if abs(self.mix_energy_residual_w) > self.inputs.energy_absolute_tolerance_w:
            raise ValueError("Turbine-inlet cooling mixer energy residual exceeds tolerance")
        mixed_elements = dict(self.mixed_elemental_mass_fractions)
        expected_element_residuals = tuple(
            (element, gas * mixed_elements[element]
             - hot_flow * dict(hot.elemental_mass_fractions)[element]
             - bleed * dict(cold.elemental_mass_fractions)[element])
            for element, _ in hot.elemental_mass_fractions
        )
        if (tuple(name for name, _ in self.elemental_mass_residuals_kg_s)
                != tuple(name for name, _ in expected_element_residuals)
                or any(not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-9)
                       for (_, actual), (_, expected) in zip(self.elemental_mass_residuals_kg_s,
                                                              expected_element_residuals, strict=True))
                or any(abs(value) > self.inputs.flow_absolute_tolerance_kg_s
                       for _, value in self.elemental_mass_residuals_kg_s)):
            raise ValueError("Cooling mix elemental mass residual exceeds absolute tolerance")
        return self


def _close(actual, expected, label, *, rel=1e-12, abs_tol=1e-8):
    actual = finite(actual, label)
    expected = finite(expected, label + " expected")
    if not math.isclose(actual, expected, rel_tol=rel, abs_tol=abs_tol):
        raise ValueError(f"Retained {label} differs from recomputed source terms")


def _element_map(state):
    return dict(state.elemental_mass_fractions)


def run_cooled_brayton_point(phase_factory, inputs: CoolingBleedInputs) -> CoolingBleedBraytonRun:
    """Run one evidence-bound compressor bleed and turbine-inlet mixing point.

    One portion of compressed air bypasses the combustor. The existing native
    cycle runner calculates the remaining primary-air/fuel equilibrium state.
    A second Cantera phase performs enthalpy-conserving mixing and turbine
    expansion at the supplied turbine-map efficiency. The map correction factors,
    speed link, bleed fraction, pressure loss, shaft losses and target are all
    caller-owned evidence-bound inputs.
    """
    import cantera as ct
    from dataclasses import replace

    if type(inputs) is not CoolingBleedInputs:
        raise TypeError("Supply CoolingBleedInputs")
    if not callable(phase_factory):
        raise TypeError("A native Cantera phase factory is required")
    inputs.require_current()
    comp = interpolate_compressor_map(
        inputs.compressor_map, corrected_speed=inputs.compressor_corrected_speed,
        compression_pressure_ratio=inputs.compressor_pressure_ratio)
    p_turb_in = (inputs.cycle_inputs.air_pressure_pa
                 * inputs.compressor_pressure_ratio
                 * inputs.cycle_inputs.combustor_pressure_recovery)
    p_turb_out = inputs.cycle_inputs.turbine_exhaust_pressure_pa
    t_ratio = p_turb_in / p_turb_out
    turb = interpolate_turbine_map(
        inputs.turbine_map, corrected_speed=inputs.turbine_corrected_speed,
        expansion_pressure_ratio=t_ratio)
    air_flow = inputs.air_mass_flow_kg_s
    cool_flow = air_flow * inputs.cooling_air_fraction
    primary_flow = air_flow - cool_flow
    fuel_flow = inputs.hydrogen_mass_flow_kg_s
    if primary_flow <= 0.:
        raise ValueError("Cooling bleed leaves no primary combustor air")
    cycle_inputs = replace(
        inputs.cycle_inputs,
        compressor_pressure_ratio=inputs.compressor_pressure_ratio,
        compressor_isentropic_efficiency=comp.isentropic_efficiency,
        turbine_isentropic_efficiency=turb.isentropic_efficiency,
        hydrogen_fuel_to_air_mass_ratio=fuel_flow / primary_flow,
    )
    if cycle_inputs.turbine_exhaust_pressure_pa >= p_turb_in:
        raise ValueError("Turbine exhaust pressure must remain below cooled turbine inlet")
    primary_cycle = run_open_cycle_brayton(phase_factory(), cycle_inputs)
    if not isinstance(primary_cycle, OpenBraytonRun):
        raise TypeError("Cantera cycle runner returned an invalid native result")
    hot = primary_cycle.states[3]
    cold = primary_cycle.states[1]
    if abs(hot.pressure_pa - p_turb_in) > 1e-8 * p_turb_in:
        raise ValueError("Native combustor outlet pressure differs from the turbine map station")
    cooling_pressure = cold.pressure_pa - inputs.cooling_line_pressure_drop_pa
    if not math.isclose(cooling_pressure, hot.pressure_pa, rel_tol=1e-10, abs_tol=1e-3):
        raise ValueError("Cooling-path pressure must land at the native turbine-inlet station")
    turbine_flow = primary_flow + fuel_flow + cool_flow
    if not math.isclose(turbine_flow, air_flow + fuel_flow, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("Combustor, compressor-bleed and turbine mass flows do not close")
    hot_flow = primary_flow + fuel_flow
    h_mix = (hot_flow * hot.enthalpy_j_kg + cool_flow * cold.enthalpy_j_kg) / turbine_flow
    species = hot.species_names
    if cold.species_names != species:
        raise ValueError("Cantera station species order changed across the primary cycle")
    y_hot, y_cold = np.asarray(hot.mass_fractions), np.asarray(cold.mass_fractions)
    y_mix = (hot_flow * y_hot + cool_flow * y_cold) / turbine_flow
    phase = phase_factory()
    if not isinstance(phase, ct.Solution):
        raise TypeError("phase_factory must return native Cantera Solution objects")
    if phase is primary_cycle.native_phase:
        raise ValueError("The mixer needs a distinct phase; do not mutate the retained primary-cycle owner")
    if tuple(phase.species_names) != species:
        raise ValueError("Mixing phase species order differs from the retained Brayton states")
    y_dict = dict(zip(species, y_mix, strict=True))
    phase.HPY = h_mix, hot.pressure_pa, y_dict
    mix_h, mix_s, mix_t, mix_p = (float(phase.enthalpy_mass), float(phase.entropy_mass),
                                  float(phase.T), float(phase.P))
    finite(mix_h, "mixed turbine-inlet enthalpy")
    finite(mix_s, "mixed turbine-inlet entropy")
    mixed_elements = tuple((element, finite(phase.elemental_mass_fraction(element),
                                            f"mixed {element} mass fraction"))
                           for element in phase.element_names)
    phase.SPY = mix_s, p_turb_out, y_dict
    h_is = float(phase.enthalpy_mass)
    if mix_h <= h_is:
        raise ValueError("Declared turbine pressure and frozen composition do not yield positive expansion work")
    h_out = mix_h - turb.isentropic_efficiency * (mix_h - h_is)
    phase.HPY = h_out, p_turb_out, y_dict
    out_h, out_t = float(phase.enthalpy_mass), float(phase.T)
    turbine_power = (mix_h - out_h) * turbine_flow
    compressor_power = primary_cycle.compressor_work_j_kg_air * air_flow
    shaft_residual = (turbine_power - compressor_power
                      - inputs.shaft_mechanical_loss_w - inputs.shaft_power_target_w)
    mix_residual = (turbine_flow * mix_h - hot_flow * hot.enthalpy_j_kg
                    - cool_flow * cold.enthalpy_j_kg)
    hot_elements, cold_elements = _element_map(hot), _element_map(cold)
    elements = tuple(name for name, _ in hot.elemental_mass_fractions)
    if tuple(name for name, _ in mixed_elements) != elements:
        raise ValueError("Cantera mixing phase changed the elemental basis")
    element_residuals = tuple((element, turbine_flow * fraction
                                - hot_flow * hot_elements[element]
                                - cool_flow * cold_elements[element])
                               for element, fraction in mixed_elements)
    token = object()
    _PENDING.add(token)
    try:
        return CoolingBleedBraytonRun(
            inputs, comp, turb, primary_cycle, primary_flow, cool_flow, turbine_flow,
            cooling_pressure, mix_t, mix_p, mix_h, mix_s,
            tuple((name, float(value)) for name, value in zip(species, y_mix, strict=True)),
            mixed_elements, h_is, p_turb_out, out_t, out_h,
            compressor_power, turbine_power, shaft_residual,
            air_flow * inputs.compressor_actual_to_corrected_flow_factor - comp.corrected_mass_flow_kg_s,
            turbine_flow * inputs.turbine_actual_to_corrected_flow_factor - turb.corrected_mass_flow_kg_s,
            mix_residual, element_residuals, token,
        )
    except Exception:
        _PENDING.discard(token)
        raise


__all__ = ["CoolingBleedInputs", "CoolingBleedBraytonRun", "run_cooled_brayton_point"]
