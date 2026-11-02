"""Accepted station model for staged compressor-air turbine cooling.

This composes an already-issued Cantera Brayton combustor state with successive
frozen-composition expansion steps and caller-declared coolant injections. It
does not resolve blade passages, film effectiveness, metal temperature, or flow
capacity.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from .open_brayton import (BraytonGasState, OpenBraytonRun, _require_native_phase,
                           _snapshot, _native_mechanism_signature)

_PENDING = set()


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label}")
    return value.strip()


def _sequence(values, label, *, positive=False, nonnegative=False):
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{label} must be a numeric sequence")
    result = tuple(finite(value, label, positive=positive) for value in values)
    if not result:
        raise ValueError(f"{label} cannot be empty")
    if nonnegative and any(value < 0.0 for value in result):
        raise ValueError(f"{label} cannot contain negative values")
    return result


def _state_payload(state):
    return (state.temperature_k, state.pressure_pa, state.enthalpy_j_kg,
            state.entropy_j_kg_k, state.species_names, state.mass_fractions,
            state.elemental_mass_fractions, state.mechanism_id,
            state.process_window_id)


@dataclass(frozen=True, slots=True)
class StagedTurbineCoolingInputs:
    """Stagewise pressure, efficiency, coolant rate and heat pickup declaration.

    `coolant_mass_flow_kg_s` is air bled from the same compressor outlet that
    feeds the retained `OpenBraytonRun`. It enters after each specified stage
    expansion. `coolant_heat_pickup_j_kg` is the caller's coolant enthalpy rise
    from the compressor-discharge reference before throttling to that injection
    pressure; it represents heat removed from hardware only as an external
    ledger term, not a solved blade thermal state.
    """

    brayton: OpenBraytonRun
    air_mass_flow_kg_s: float
    hydrogen_mass_flow_kg_s: float
    stage_exit_pressures_pa: tuple[float, ...]
    stage_isentropic_efficiencies: tuple[float, ...]
    coolant_mass_flow_kg_s: tuple[float, ...]
    coolant_heat_pickup_j_kg: tuple[float, ...]
    evidence_ids: tuple[str, ...]
    pressure_basis_evidence_id: str
    efficiency_evidence_id: str
    feed_evidence_id: str
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.brayton) is not OpenBraytonRun:
            raise TypeError("brayton must be a native OpenBraytonRun")
        object.__setattr__(self, "air_mass_flow_kg_s", finite(
            self.air_mass_flow_kg_s, "total compressor inlet air flow", positive=True))
        object.__setattr__(self, "hydrogen_mass_flow_kg_s", finite(
            self.hydrogen_mass_flow_kg_s, "hydrogen feed flow", positive=True))
        pressures = _sequence(self.stage_exit_pressures_pa, "stage exit pressure", positive=True)
        efficiencies = _sequence(self.stage_isentropic_efficiencies,
                                 "stage isentropic efficiency", positive=True)
        coolant = _sequence(self.coolant_mass_flow_kg_s, "stage coolant flow", nonnegative=True)
        pickup = _sequence(self.coolant_heat_pickup_j_kg, "coolant heat pickup", nonnegative=True)
        n = len(pressures)
        if not (len(efficiencies) == len(coolant) == len(pickup) == n):
            raise ValueError("Every turbine stage needs pressure, efficiency, coolant flow and heat pickup")
        if any(value > 1.0 for value in efficiencies):
            raise ValueError("Stage efficiencies must lie in (0, 1]")
        if not any(value > 0.0 for value in coolant):
            raise ValueError("At least one stage must receive a positive coolant flow")
        hot = self.brayton.states[3]
        if any(a <= b for a, b in zip((hot.pressure_pa, *pressures), pressures, strict=False)):
            raise ValueError("Stage exit pressures must strictly decrease from the combustor outlet")
        if not math.isclose(pressures[-1], self.brayton.inputs.turbine_exhaust_pressure_pa,
                            rel_tol=1e-12, abs_tol=1e-5):
            raise ValueError("Final stage pressure must equal the retained Brayton exhaust pressure")
        compressor = self.brayton.states[1]
        if compressor.pressure_pa <= hot.pressure_pa:
            raise ValueError("Compressor discharge must remain above the combustor/turbine inlet")
        if any(p >= compressor.pressure_pa for p in pressures):
            raise ValueError("Cooling injection pressures must be below coolant source pressure")
        primary_air = self.air_mass_flow_kg_s - math.fsum(coolant)
        if primary_air <= 0.0:
            raise ValueError("Staged coolant flow must remain below total compressor air flow")
        fuel_ratio = self.hydrogen_mass_flow_kg_s / primary_air
        if not math.isclose(fuel_ratio, self.brayton.inputs.hydrogen_fuel_to_air_mass_ratio,
                            rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("Hydrogen/air flow ratio differs from the retained Brayton run")
        ids = tuple(_text(value, "stage cooling evidence identity") for value in self.evidence_ids)
        if len(ids) != n:
            raise ValueError("Each stage requires its own cooling-flow evidence identity")
        for name in ("pressure_basis_evidence_id", "efficiency_evidence_id", "feed_evidence_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "stage_exit_pressures_pa", pressures)
        object.__setattr__(self, "stage_isentropic_efficiencies", efficiencies)
        object.__setattr__(self, "coolant_mass_flow_kg_s", coolant)
        object.__setattr__(self, "coolant_heat_pickup_j_kg", pickup)
        object.__setattr__(self, "evidence_ids", ids)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (id(self.brayton), self.air_mass_flow_kg_s, self.hydrogen_mass_flow_kg_s,
                self.stage_exit_pressures_pa, self.stage_isentropic_efficiencies,
                self.coolant_mass_flow_kg_s, self.coolant_heat_pickup_j_kg,
                self.evidence_ids, self.pressure_basis_evidence_id,
                self.efficiency_evidence_id, self.feed_evidence_id)

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Staged-cooling inputs changed after admission")
        terminal = _snapshot(self.brayton.native_phase, "staged_input_brayton_terminal",
                             self.brayton.inputs)
        if _state_payload(terminal) != _state_payload(self.brayton.states[-1]):
            raise ValueError("Retained native Brayton phase changed after the source run")
        return self


@dataclass(frozen=True, slots=True)
class TurbineCoolingStage:
    index: int
    pressure_in_pa: float
    pressure_out_pa: float
    mass_flow_in_kg_s: float
    coolant_mass_flow_kg_s: float
    mass_flow_out_kg_s: float
    expansion_inlet: BraytonGasState
    expansion_outlet: BraytonGasState
    mixed_outlet: BraytonGasState
    isentropic_outlet_enthalpy_j_kg: float
    shaft_power_w: float
    coolant_enthalpy_j_kg: float
    coolant_heat_pickup_w: float
    mixing_energy_residual_w: float
    evidence_id: str


@dataclass(frozen=True, slots=True)
class StagedTurbineCoolingRun:
    inputs: StagedTurbineCoolingInputs
    stages: tuple[TurbineCoolingStage, ...]
    initial_mass_flow_kg_s: float
    final_mass_flow_kg_s: float
    coolant_total_kg_s: float
    coolant_heat_pickup_w: float
    turbine_power_w: float
    energy_residual_w: float
    exhaust: BraytonGasState
    native_phase: object
    _signature: tuple
    _issuer: object = field(repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise ValueError("Staged turbine results are issued only by the native runner")
        _PENDING.remove(self._issuer)
        self.inputs.require_current()
        stages = tuple(self.stages)
        if len(stages) != len(self.inputs.stage_exit_pressures_pa):
            raise ValueError("Result must retain each declared expansion and injection stage")
        total_cool = math.fsum(self.inputs.coolant_mass_flow_kg_s)
        start = self.inputs.air_mass_flow_kg_s - total_cool + self.inputs.hydrogen_mass_flow_kg_s
        expected = self.inputs.air_mass_flow_kg_s + self.inputs.hydrogen_mass_flow_kg_s
        for name, actual, wanted in (
            ("initial flow", self.initial_mass_flow_kg_s, start),
            ("final flow", self.final_mass_flow_kg_s, expected),
            ("coolant flow", self.coolant_total_kg_s, total_cool),
            ("coolant heat", self.coolant_heat_pickup_w,
             math.fsum(q * dh for q, dh in zip(self.inputs.coolant_mass_flow_kg_s,
                                                self.inputs.coolant_heat_pickup_j_kg, strict=True))),
            ("turbine power", self.turbine_power_w,
             math.fsum(stage.shaft_power_w for stage in stages)),
        ):
            if not math.isclose(finite(actual, name), wanted, rel_tol=1e-11, abs_tol=1e-7):
                raise ValueError(f"Staged turbine {name} ledger does not close")
        cold_h = self.inputs.brayton.states[1].enthalpy_j_kg
        hot_h = self.inputs.brayton.states[3].enthalpy_j_kg
        expected_energy_residual = (
            start * hot_h + total_cool * cold_h + self.coolant_heat_pickup_w
            - self.final_mass_flow_kg_s * self.exhaust.enthalpy_j_kg
            - self.turbine_power_w
        )
        residual = finite(self.energy_residual_w, "staged turbine energy residual")
        scale = max(abs(start * hot_h), abs(self.final_mass_flow_kg_s * self.exhaust.enthalpy_j_kg),
                    abs(self.turbine_power_w), 1.0)
        if not math.isclose(residual, expected_energy_residual, rel_tol=1e-12, abs_tol=1e-7):
            raise ValueError("Staged turbine energy residual differs from retained stream terms")
        if abs(residual) > 1e-7 * scale:
            raise ValueError("Staged turbine total energy ledger does not close")
        for i, stage in enumerate(stages):
            if stage.index != i or stage.evidence_id != self.inputs.evidence_ids[i]:
                raise ValueError("Stage identity/evidence differs from the admitted input")
            if not math.isclose(stage.mass_flow_out_kg_s,
                                stage.mass_flow_in_kg_s + stage.coolant_mass_flow_kg_s,
                                rel_tol=1e-12, abs_tol=1e-10):
                raise ValueError("Stage mass flow does not close")
            mixing_energy_scale = max(
                abs(stage.mass_flow_out_kg_s * stage.mixed_outlet.enthalpy_j_kg),
                abs(stage.mass_flow_in_kg_s * stage.expansion_outlet.enthalpy_j_kg),
                abs(stage.coolant_mass_flow_kg_s * stage.coolant_enthalpy_j_kg),
                1.0,
            )
            if abs(stage.mixing_energy_residual_w) > 1e-7 * mixing_energy_scale:
                raise ValueError("Stage injection mixing energy residual exceeds tolerance")
        if stages[-1].mixed_outlet != self.exhaust:
            raise ValueError("Exhaust state must be the final mixed stage state")
        native = _snapshot(self.native_phase, "staged_turbine_terminal", self.inputs.brayton.inputs)
        if _state_payload(native) != _state_payload(self.exhaust):
            raise ValueError("Native terminal phase differs from retained staged exhaust")
        object.__setattr__(self, "stages", stages)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (self.inputs._payload(), self.stages, self.initial_mass_flow_kg_s,
                self.final_mass_flow_kg_s, self.coolant_total_kg_s,
                self.coolant_heat_pickup_w, self.turbine_power_w,
                self.energy_residual_w, self.exhaust,
                id(self.native_phase), self._signature)

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Staged turbine result changed after issuance")
        self.inputs.require_current()
        native = _snapshot(self.native_phase, "staged_turbine_terminal", self.inputs.brayton.inputs)
        if _state_payload(native) != _state_payload(self.exhaust):
            raise ValueError("Native staged turbine phase changed after issuance")
        signature = _native_mechanism_signature(self.native_phase)
        if signature != self._signature:
            raise ValueError("Native staged turbine mechanism changed after issuance")
        return self


def run_staged_turbine_cooling(phase_factory, inputs: StagedTurbineCoolingInputs):
    """Expand and mix through discrete stages using caller-owned coolant inputs."""
    import cantera as ct

    if not callable(phase_factory):
        raise TypeError("Supply a factory returning a fresh Cantera Solution")
    if type(inputs) is not StagedTurbineCoolingInputs:
        raise TypeError("Supply StagedTurbineCoolingInputs")
    inputs.require_current()
    phase = phase_factory()
    _require_native_phase(phase)
    if not isinstance(phase, ct.Solution):
        raise TypeError("phase_factory must return a Cantera Solution")
    if phase is inputs.brayton.native_phase:
        raise ValueError("Use a fresh phase; preserve the original Brayton native owner")
    hot = inputs.brayton.states[3]
    cold = inputs.brayton.states[1]
    if tuple(phase.species_names) != hot.species_names:
        raise ValueError("Cantera mechanism species differ from the retained Brayton stations")
    hot_flow = (inputs.air_mass_flow_kg_s - math.fsum(inputs.coolant_mass_flow_kg_s)
                + inputs.hydrogen_mass_flow_kg_s)
    # The Brayton hot state was calculated per kg of inlet air; the declared feed
    # ratio fixes its actual mass-flow basis without altering the native state.
    flow = hot_flow
    current = hot
    power = 0.0
    stage_rows = []
    for i, (p_out, eta, coolant_flow, heat_pickup) in enumerate(zip(
        inputs.stage_exit_pressures_pa, inputs.stage_isentropic_efficiencies,
        inputs.coolant_mass_flow_kg_s, inputs.coolant_heat_pickup_j_kg, strict=True
    )):
        stage_inlet = current
        p_in = current.pressure_pa
        y = dict(zip(current.species_names, current.mass_fractions, strict=True))
        phase.SPY = current.entropy_j_kg_k, p_out, y
        h_is = float(phase.enthalpy_mass)
        h_out = current.enthalpy_j_kg - eta * (current.enthalpy_j_kg - h_is)
        if h_out >= current.enthalpy_j_kg:
            raise ValueError(f"Stage {i} does not produce positive expansion work")
        phase.HPY = h_out, p_out, y
        expanded = _snapshot(phase, f"turbine_stage_{i}_expanded", inputs.brayton.inputs)
        stage_power = flow * (current.enthalpy_j_kg - expanded.enthalpy_j_kg)
        power += stage_power
        total_out = flow + coolant_flow
        coolant_h = cold.enthalpy_j_kg + heat_pickup
        if coolant_flow > 0.0:
            y_cold = np.asarray(cold.mass_fractions)
            y_hot = np.asarray(expanded.mass_fractions)
            mixed_y = (flow * y_hot + coolant_flow * y_cold) / total_out
            mixed_h = (flow * expanded.enthalpy_j_kg + coolant_flow * coolant_h) / total_out
            mixed_dict = dict(zip(expanded.species_names, mixed_y, strict=True))
            phase.HPY = mixed_h, p_out, mixed_dict
            mixing_residual = (total_out * float(phase.enthalpy_mass)
                               - flow * expanded.enthalpy_j_kg - coolant_flow * coolant_h)
            current = _snapshot(phase, f"turbine_stage_{i}_mixed", inputs.brayton.inputs)
        else:
            coolant_h = cold.enthalpy_j_kg
            mixing_residual = 0.0
            current = expanded
        stage_rows.append(TurbineCoolingStage(
            i, p_in, p_out, flow, coolant_flow, total_out, stage_inlet, expanded, current,
            h_is, stage_power, coolant_h, coolant_flow * heat_pickup,
            mixing_residual, inputs.evidence_ids[i]))
        flow = total_out
    token = object()
    _PENDING.add(token)
    try:
        signature = _native_mechanism_signature(phase)
        if signature != inputs.brayton._mechanism_signature:
            raise ValueError("Staged turbine phase mechanism differs from the retained Brayton run")
        total_cool = math.fsum(inputs.coolant_mass_flow_kg_s)
        heat = math.fsum(q * dh for q, dh in zip(inputs.coolant_mass_flow_kg_s,
                                                   inputs.coolant_heat_pickup_j_kg, strict=True))
        energy_residual = (hot_flow * hot.enthalpy_j_kg
                           + total_cool * cold.enthalpy_j_kg + heat
                           - flow * current.enthalpy_j_kg - power)
        return StagedTurbineCoolingRun(
            inputs, tuple(stage_rows), hot_flow, flow,
            total_cool, heat, power, energy_residual, current, phase, signature, token)
    except Exception:
        _PENDING.discard(token)
        raise


__all__ = ["StagedTurbineCoolingInputs", "TurbineCoolingStage",
           "StagedTurbineCoolingRun", "run_staged_turbine_cooling"]
