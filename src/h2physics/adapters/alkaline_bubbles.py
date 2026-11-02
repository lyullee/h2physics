"""Caller-calibrated bubble losses for alkaline water electrolysis.

This reduced-order adapter adds an electrode-area correction and an effective-
medium electrolyte-resistance increment to the shared electrochemistry core.
It does not predict bubble dynamics or infer coverage from current density.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from ..core import finite
from ..electrochemistry import HydrogenStack, StackResult

ConditionInput = Callable[["AlkalineBubbleCondition"], float]
_PENDING_ISSUERS: set[object] = set()


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name} evidence identity")
    return value.strip()


def _callback_binding(callback: Callable) -> tuple:
    function = getattr(callback, "__func__", callback)
    owner = getattr(callback, "__self__", None)
    code = getattr(function, "__code__", None)
    return (id(callback), id(function), id(owner), None if code is None else
            (code.co_filename, code.co_firstlineno, code.co_code))


@dataclass(frozen=True, slots=True)
class AlkalineBubbleCondition:
    """Explicit operating point passed to every bubble/property callback."""

    current_density_a_m2: float
    temperature_k: float
    absolute_pressure_pa: float
    electrolyte_concentration_mol_m3: float | None = None
    electrolyte_composition_id: str | None = None
    anode_id: str | None = None
    cathode_id: str | None = None

    def __post_init__(self) -> None:
        current = finite(self.current_density_a_m2, "geometric current density")
        temperature = finite(self.temperature_k, "stack temperature", positive=True)
        pressure = finite(self.absolute_pressure_pa, "absolute pressure", positive=True)
        if current < 0.:
            raise ValueError("Electrolysis current density must be nonnegative")
        object.__setattr__(self, "current_density_a_m2", current)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "absolute_pressure_pa", pressure)
        concentration = self.electrolyte_concentration_mol_m3
        if concentration is not None:
            concentration = finite(concentration, "electrolyte concentration", positive=True)
            object.__setattr__(self, "electrolyte_concentration_mol_m3", concentration)
        if (concentration is None) != (self.electrolyte_composition_id is None):
            raise ValueError("Electrolyte concentration and composition identity must be declared together")
        for name in ("electrolyte_composition_id", "anode_id", "cathode_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _identity(value, name))
        if (self.anode_id is None) != (self.cathode_id is None):
            raise ValueError("Anode and cathode identifiers must be declared together")


@dataclass(frozen=True, slots=True)
class AlkalineBubbleModel:
    """Calibrated bubble-state callbacks and reduced-order loss assumptions.

    Coverage callbacks return the inactive surface fraction on each electrode;
    the void callback returns gas volume fraction along the ionic path. These
    observables are independent inputs and are never inferred from each other.
    The bubble-free electrolyte area resistance is in ohm m² per cell.
    """

    anode_coverage: ConditionInput = field(repr=False, compare=False)
    cathode_coverage: ConditionInput = field(repr=False, compare=False)
    electrolyte_void_fraction: ConditionInput = field(repr=False, compare=False)
    bubble_free_area_resistance_ohm_m2: ConditionInput = field(repr=False, compare=False)
    anode_tafel_slope_v_decade: ConditionInput = field(repr=False, compare=False)
    cathode_tafel_slope_v_decade: ConditionInput = field(repr=False, compare=False)
    coverage_evidence_id: str
    void_fraction_evidence_id: str
    electrolyte_resistance_evidence_id: str
    tafel_slope_evidence_id: str
    correlation_evidence_id: str
    bruggeman_exponent: float = 1.5
    correlation_id: str = "bruggeman-dilute-gas-effective-conductivity"
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        callbacks = (
            self.anode_coverage, self.cathode_coverage,
            self.electrolyte_void_fraction,
            self.bubble_free_area_resistance_ohm_m2,
            self.anode_tafel_slope_v_decade,
            self.cathode_tafel_slope_v_decade,
        )
        if any(not callable(callback) for callback in callbacks):
            raise TypeError("Bubble state and calibrated property inputs must be callables")
        for name in (
            "coverage_evidence_id", "void_fraction_evidence_id",
            "electrolyte_resistance_evidence_id", "tafel_slope_evidence_id",
            "correlation_evidence_id", "correlation_id",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        exponent = finite(self.bruggeman_exponent, "effective-conductivity exponent", positive=True)
        object.__setattr__(self, "bruggeman_exponent", exponent)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self) -> tuple:
        return (
            *(_callback_binding(getattr(self, name)) for name in (
                "anode_coverage", "cathode_coverage", "electrolyte_void_fraction",
                "bubble_free_area_resistance_ohm_m2", "anode_tafel_slope_v_decade",
                "cathode_tafel_slope_v_decade",
            )),
            self.coverage_evidence_id, self.void_fraction_evidence_id,
            self.electrolyte_resistance_evidence_id, self.tafel_slope_evidence_id,
            self.correlation_evidence_id, self.bruggeman_exponent, self.correlation_id,
        )

    def require_current(self) -> AlkalineBubbleModel:
        if self._payload() != self._seal:
            raise ValueError("Bubble model callbacks or evidence identities changed after configuration")
        return self

    def evaluate_losses(self, condition: AlkalineBubbleCondition) -> tuple[float, float]:
        """Return (surface-coverage V/cell, electrolyte-void V/cell)."""
        self.require_current()
        if type(condition) is not AlkalineBubbleCondition:
            raise TypeError("Supply an AlkalineBubbleCondition with absolute pressure")
        current = condition.current_density_a_m2
        theta_a = finite(self.anode_coverage(condition), "anode bubble coverage")
        theta_c = finite(self.cathode_coverage(condition), "cathode bubble coverage")
        phi = finite(self.electrolyte_void_fraction(condition), "electrolyte gas void fraction")
        if not 0.0 <= theta_a < 1.0 or not 0.0 <= theta_c < 1.0:
            raise ValueError("Each electrode bubble coverage must lie in [0, 1)")
        if not 0.0 <= phi < 1.0:
            raise ValueError("Electrolyte gas void fraction must lie in [0, 1)")
        slope_a = finite(self.anode_tafel_slope_v_decade(condition), "anode Tafel slope")
        slope_c = finite(self.cathode_tafel_slope_v_decade(condition), "cathode Tafel slope")
        if slope_a < 0.0 or slope_c < 0.0:
            raise ValueError("Tafel slopes must be nonnegative")
        coverage_loss = slope_a * math.log10(1.0 / (1.0-theta_a))
        coverage_loss += slope_c * math.log10(1.0 / (1.0-theta_c))

        area_resistance = finite(
            self.bubble_free_area_resistance_ohm_m2(condition),
            "bubble-free electrolyte area resistance",
        )
        if area_resistance < 0.0:
            raise ValueError("Bubble-free electrolyte area resistance cannot be negative")
        void_multiplier = (1.0-phi) ** (-self.bruggeman_exponent) - 1.0
        void_loss = current * area_resistance * void_multiplier
        return finite(coverage_loss, "coverage voltage loss"), finite(void_loss, "void-resistance voltage loss")


@dataclass(frozen=True, slots=True)
class AlkalineBubbleEvaluation:
    """Electrolysis result with explicit additive bubble penalties.

    The retained base result remains the shared HydrogenStack owner. Derived
    power and voltage values are reconstructed and checked on every access.
    """

    stack: HydrogenStack = field(repr=False, compare=False)
    bubble_model: AlkalineBubbleModel = field(repr=False, compare=False)
    current_density_a_m2: float
    temperature_k: float
    condition: AlkalineBubbleCondition
    faradaic_efficiency: float
    base_result: StackResult
    coverage_voltage_loss_v_cell: float
    electrolyte_void_voltage_loss_v_cell: float
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer not in _PENDING_ISSUERS:
            raise TypeError("Create bubble evaluations with evaluate_alkaline_bubbles")
        _PENDING_ISSUERS.remove(self._issuer)
        if type(self.stack) is not HydrogenStack or type(self.bubble_model) is not AlkalineBubbleModel:
            raise TypeError("Retain the original shared stack and calibrated bubble model")
        self.bubble_model.require_current()
        if type(self.base_result) is not StackResult or self.base_result.mode != "electrolysis":
            raise ValueError("Bubble correction applies to a shared electrolysis result")
        current = finite(self.current_density_a_m2, "current density")
        temperature = finite(self.temperature_k, "temperature", positive=True)
        efficiency = finite(self.faradaic_efficiency, "Faradaic efficiency", positive=True)
        if current < 0.0 or efficiency > 1.0:
            raise ValueError("Current density and Faradaic efficiency are outside their domains")
        if type(self.condition) is not AlkalineBubbleCondition:
            raise TypeError("Bubble evaluation must retain its explicit operating condition")
        if (self.condition.current_density_a_m2 != current
                or self.condition.temperature_k != temperature):
            raise ValueError("Bubble condition does not match the shared stack operating point")
        expected = self.bubble_model.evaluate_losses(self.condition)
        actual = (finite(self.coverage_voltage_loss_v_cell, "coverage loss"),
                  finite(self.electrolyte_void_voltage_loss_v_cell, "void loss"))
        if actual != expected:
            raise ValueError("Bubble-loss projection does not match the retained model inputs")
        object.__setattr__(self, "current_density_a_m2", current)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "faradaic_efficiency", efficiency)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self) -> tuple:
        return (id(self.stack), id(self.bubble_model), self.current_density_a_m2,
                self.temperature_k, self.condition, self.faradaic_efficiency, self.base_result,
                self.coverage_voltage_loss_v_cell, self.electrolyte_void_voltage_loss_v_cell)

    def require_current(self) -> AlkalineBubbleEvaluation:
        self.bubble_model.require_current()
        if self._payload() != self._seal:
            raise ValueError("Bubble evaluation fields changed after issuance")
        expected = self.bubble_model.evaluate_losses(self.condition)
        if expected != (self.coverage_voltage_loss_v_cell, self.electrolyte_void_voltage_loss_v_cell):
            raise ValueError("Retained bubble loss differs from the configured callbacks")
        fresh_base = self.stack.evaluate(self.current_density_a_m2, self.temperature_k,
            mode="electrolysis", faradaic_efficiency=self.faradaic_efficiency)
        if fresh_base != self.base_result:
            raise ValueError("Retained shared electrochemistry result is stale")
        return self

    @property
    def bubble_voltage_loss_v_cell(self) -> float:
        self.require_current()
        return self.coverage_voltage_loss_v_cell + self.electrolyte_void_voltage_loss_v_cell

    @property
    def corrected_cell_voltage_v(self) -> float:
        self.require_current()
        return self.base_result.cell_voltage_v + self.coverage_voltage_loss_v_cell + self.electrolyte_void_voltage_loss_v_cell

    @property
    def corrected_stack_voltage_v(self) -> float:
        self.require_current()
        return self.corrected_cell_voltage_v * self.stack.geometry.series_cells

    @property
    def additional_electric_input_w(self) -> float:
        self.require_current()
        return self.base_result.current_a * self.bubble_voltage_loss_v_cell * self.stack.geometry.series_cells

    @property
    def corrected_electric_input_w(self) -> float:
        self.require_current()
        return self.base_result.electric_input_w + self.additional_electric_input_w

    @property
    def corrected_unallocated_energy_rate_w(self) -> float:
        self.require_current()
        return self.base_result.unallocated_energy_rate_w + self.additional_electric_input_w


def evaluate_alkaline_bubbles(
    stack: HydrogenStack,
    bubble_model: AlkalineBubbleModel,
    current_density_a_m2: float,
    temperature_k: float,
    *,
    absolute_pressure_pa: float,
    electrolyte_concentration_mol_m3: float | None = None,
    electrolyte_composition_id: str | None = None,
    anode_id: str | None = None,
    cathode_id: str | None = None,
    faradaic_efficiency: float = 1.0,
) -> AlkalineBubbleEvaluation:
    """Evaluate shared electrochemistry plus calibrated bubble-loss terms.

    The existing stack's kinetic/electrolyte losses must be bubble-free or have
    their bubble contribution explicitly excluded to prevent double counting.
    """
    if type(stack) is not HydrogenStack or type(bubble_model) is not AlkalineBubbleModel:
        raise TypeError("Supply a HydrogenStack and an AlkalineBubbleModel")
    bubble_model.require_current()
    current = finite(current_density_a_m2, "current density")
    temperature = finite(temperature_k, "temperature", positive=True)
    condition = AlkalineBubbleCondition(
        current, temperature, absolute_pressure_pa,
        electrolyte_concentration_mol_m3, electrolyte_composition_id,
        anode_id, cathode_id,
    )
    efficiency = finite(faradaic_efficiency, "Faradaic efficiency", positive=True)
    if current < 0.0 or efficiency > 1.0:
        raise ValueError("Current density and Faradaic efficiency are outside their domains")
    base = stack.evaluate(current, temperature, mode="electrolysis", faradaic_efficiency=efficiency)
    coverage, void = bubble_model.evaluate_losses(condition)
    token = object()
    _PENDING_ISSUERS.add(token)
    return AlkalineBubbleEvaluation(stack, bubble_model, current, temperature, condition, efficiency,
                                    base, coverage, void, _issuer=token)


__all__ = ["AlkalineBubbleCondition", "AlkalineBubbleModel", "AlkalineBubbleEvaluation",
           "evaluate_alkaline_bubbles"]
