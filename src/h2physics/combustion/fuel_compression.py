"""Steady pure-hydrogen compression through Cantera or injected CoolProp.

The model supplies a single adiabatic, fixed-composition reference stage. The
selected native provider owns entropy and enthalpy; flow, pressure target and
efficiency remain explicit caller inputs. No map, intercooler, leak or machine
qualification is implied.
"""

from __future__ import annotations

import math
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass

from ..core import PropertyBasis, ThermoState, finite

_PENDING_COMPRESSION_ISSUERS: set[object] = set()
_PENDING_REAL_FLUID_ISSUERS: set[object] = set()


def _issue_compression_run(**values):
    token = object()
    _PENDING_COMPRESSION_ISSUERS.add(token)
    try:
        return HydrogenCompressionRun(**values, _issuer_token=token)
    except Exception:
        _PENDING_COMPRESSION_ISSUERS.discard(token)
        raise


def _identity(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label} identity")
    return value.strip()


def _seal_value(value):
    """Canonicalize typed receipt payloads; reject opaque unsealed values."""
    if is_dataclass(value):
        content = {item.name: _seal_value(getattr(value, item.name))
                   for item in fields(value)
                   if item.name not in {"native_phase", "provider", "_issuer_token", "_payload_seal"}}
        if hasattr(value, "native_phase"):
            content["native_phase_identity"] = id(value.native_phase)
            content["native_phase_signature"] = _seal_value(
                getattr(value, "_mechanism_signature", None))
        if hasattr(value, "provider"):
            content["provider_signature"] = _seal_value(
                getattr(value, "_provider_signature", None))
        return {"type": type(value).__qualname__, "fields": content}
    if isinstance(value, Mapping):
        return {str(key): _seal_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_seal_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Receipt payload cannot contain nonfinite values")
        return {"float_hex": value.hex()}
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"Unsupported receipt payload type: {type(value).__qualname__}")


def _payload_digest(value) -> str:
    payload = json.dumps(_seal_value(value), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _coolprop_provider_signature(provider):
    return (type(provider).__qualname__, id(provider), provider.version, provider.backend,
            provider.basis, provider.internal_energy_policy,
            provider.quality_roundoff_tolerance)


def _coolprop_state_snapshot(state: ThermoState, station: str, basis: PropertyBasis,
                             provider):
    if type(state) is not ThermoState:
        raise TypeError("CoolProp provider must return its ThermoState")
    basis.require_compatible(state.basis)
    phase_ok = state.phase in {"gas", "supercritical_gas"}
    if state.phase == "supercritical":
        phase_ok = (state.temperature_k >= provider.critical_temperature_k
                    and state.pressure_pa >= provider.critical_pressure_pa)
    if not phase_ok or state.vapor_mass_fraction is not None:
        raise ValueError("Fuel compressor requires a single-phase gas CoolProp state")
    return HydrogenCompressionState(
        station, state.temperature_k, state.pressure_pa, state.enthalpy_j_kg,
        state.entropy_j_kg_k, 1.0, state.density_kg_m3, state.phase, state.basis)


@dataclass(frozen=True, slots=True)
class HydrogenCompressionInputs:
    """Explicit operating point for one adiabatic pure-H2 compressor stage.

    Pressures are absolute Pa, temperature K, mass flow kg/s, and efficiency is
    the isentropic compressor efficiency. This generic performance parameter
    must be supplied with its evidence identity; it is not a default hardware
    prediction.
    """

    mechanism_id: str
    process_window_id: str
    inlet_temperature_k: float
    inlet_pressure_pa: float
    discharge_pressure_pa: float
    hydrogen_mass_flow_kg_s: float
    isentropic_efficiency: float
    state_evidence_id: str
    efficiency_evidence_id: str

    def __post_init__(self):
        for name in ("mechanism_id", "process_window_id", "state_evidence_id",
                     "efficiency_evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        for name in ("inlet_temperature_k", "inlet_pressure_pa", "discharge_pressure_pa",
                     "hydrogen_mass_flow_kg_s"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        if self.discharge_pressure_pa <= self.inlet_pressure_pa:
            raise ValueError("A compressor stage requires discharge pressure above inlet pressure")
        efficiency = finite(self.isentropic_efficiency, "isentropic efficiency", positive=True)
        if efficiency > 1.0:
            raise ValueError("Isentropic efficiency must not exceed one")
        object.__setattr__(self, "isentropic_efficiency", efficiency)


@dataclass(frozen=True, slots=True)
class HydrogenCompressionState:
    station: str
    temperature_k: float
    pressure_pa: float
    enthalpy_j_kg: float
    entropy_j_kg_k: float
    mass_fraction_h2: float
    density_kg_m3: float
    phase: str = "gas"
    property_basis: PropertyBasis | None = None

    def __post_init__(self):
        object.__setattr__(self, "station", _identity(self.station, "station"))
        for name in ("temperature_k", "pressure_pa", "mass_fraction_h2"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        object.__setattr__(self, "enthalpy_j_kg", finite(self.enthalpy_j_kg, "specific enthalpy"))
        object.__setattr__(self, "entropy_j_kg_k", finite(self.entropy_j_kg_k, "specific entropy"))
        object.__setattr__(self, "density_kg_m3", finite(self.density_kg_m3, "density", positive=True))
        if self.mass_fraction_h2 > 1.0:
            raise ValueError("Hydrogen mass fraction cannot exceed one")
        object.__setattr__(self, "phase", _identity(self.phase, "thermodynamic phase"))
        if self.property_basis is not None and type(self.property_basis) is not PropertyBasis:
            raise TypeError("State property basis must be a PropertyBasis")


@dataclass(frozen=True, slots=True)
class HydrogenRealFluidCompressionInputs:
    """Explicit H2 stage inputs plus caller-qualified property domain."""

    provider_id: str
    process_window_id: str
    inlet_temperature_k: float
    inlet_pressure_pa: float
    discharge_pressure_pa: float
    hydrogen_mass_flow_kg_s: float
    isentropic_efficiency: float
    temperature_bounds_k: tuple[float, float]
    pressure_bounds_pa: tuple[float, float]
    state_evidence_id: str
    efficiency_evidence_id: str
    domain_evidence_id: str
    entropy_relative_tolerance: float = 1e-8

    def __post_init__(self):
        for name in ("provider_id", "process_window_id", "state_evidence_id",
                     "efficiency_evidence_id", "domain_evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        for name in ("inlet_temperature_k", "inlet_pressure_pa", "discharge_pressure_pa",
                     "hydrogen_mass_flow_kg_s"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        if self.discharge_pressure_pa <= self.inlet_pressure_pa:
            raise ValueError("A compressor stage requires discharge pressure above inlet pressure")
        efficiency = finite(self.isentropic_efficiency, "isentropic efficiency", positive=True)
        if efficiency > 1.0:
            raise ValueError("Isentropic efficiency must not exceed one")
        object.__setattr__(self, "isentropic_efficiency", efficiency)
        for name, label in (("temperature_bounds_k", "temperature"),
                            ("pressure_bounds_pa", "pressure")):
            bounds = tuple(getattr(self, name))
            if len(bounds) != 2:
                raise ValueError(f"Declare finite increasing {label} bounds")
            lower, upper = (finite(value, f"{label} bound", positive=True) for value in bounds)
            if lower >= upper:
                raise ValueError(f"{label.capitalize()} bounds must increase")
            object.__setattr__(self, name, (lower, upper))
        if not self.temperature_bounds_k[0] <= self.inlet_temperature_k <= self.temperature_bounds_k[1]:
            raise ValueError("Inlet temperature lies outside the caller-declared property domain")
        if not (self.pressure_bounds_pa[0] <= self.inlet_pressure_pa
                < self.discharge_pressure_pa <= self.pressure_bounds_pa[1]):
            raise ValueError("Stage pressures lie outside the caller-declared property domain")
        tolerance = finite(self.entropy_relative_tolerance,
                           "isentropic entropy relative tolerance", positive=True)
        if tolerance >= 1e-3:
            raise ValueError("Entropy consistency tolerance must be below 1e-3")
        object.__setattr__(self, "entropy_relative_tolerance", tolerance)


def _compression_ledger(inputs, inlet, isentropic_outlet, actual_outlet):
    """Shared adiabatic enthalpy/shaft ledger for native and CoolProp paths."""
    specific_work = finite(actual_outlet.enthalpy_j_kg-inlet.enthalpy_j_kg,
                           "specific compression work")
    expected_work = finite((isentropic_outlet.enthalpy_j_kg-inlet.enthalpy_j_kg)
                           / inputs.isentropic_efficiency,
                           "efficiency-adjusted compression work")
    if specific_work <= 0 or not math.isclose(specific_work, expected_work,
                                              rel_tol=1e-8, abs_tol=1e-7):
        raise ValueError("Actual outlet enthalpy does not satisfy the declared compressor efficiency")
    power = finite(inputs.hydrogen_mass_flow_kg_s*specific_work, "compressor shaft power")
    enthalpy_rise = finite(inputs.hydrogen_mass_flow_kg_s*
                           (actual_outlet.enthalpy_j_kg-inlet.enthalpy_j_kg),
                           "enthalpy-flow rise")
    residual = finite(enthalpy_rise-power, "compressor energy residual")
    return specific_work, power, enthalpy_rise, residual


@dataclass(frozen=True, slots=True)
class HydrogenCompressionRun:
    inputs: HydrogenCompressionInputs
    inlet: HydrogenCompressionState
    isentropic_outlet: HydrogenCompressionState
    actual_outlet: HydrogenCompressionState
    specific_shaft_work_j_kg: float
    shaft_power_w: float
    enthalpy_rise_w: float
    energy_residual_w: float
    native_phase: object = field(repr=False, compare=False)
    _mechanism_signature: tuple = field(repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _payload_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_COMPRESSION_ISSUERS:
            raise ValueError("Compression results are issued only by the native runner")
        _PENDING_COMPRESSION_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        if not isinstance(self.inputs, HydrogenCompressionInputs):
            raise TypeError("Retain the declared compression inputs")
        if tuple(item.station for item in (self.inlet, self.isentropic_outlet,
                                           self.actual_outlet)) != (
                "fuel_inlet", "isentropic_reference", "compressor_outlet"):
            raise ValueError("Compression station ordering is invalid")
        for name in ("specific_shaft_work_j_kg", "shaft_power_w", "enthalpy_rise_w",
                     "energy_residual_w"):
            object.__setattr__(self, name, finite(getattr(self, name), name))
        expected_ledger = _compression_ledger(
            self.inputs, self.inlet, self.isentropic_outlet, self.actual_outlet)
        actual_ledger = (self.specific_shaft_work_j_kg, self.shaft_power_w,
                         self.enthalpy_rise_w, self.energy_residual_w)
        if any(not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-8)
               for a, b in zip(actual_ledger, expected_ledger, strict=True)):
            raise ValueError("Adiabatic stage ledger differs from the shared compression balance")
        object.__setattr__(self, "_payload_seal", _payload_digest(self))

    def require_current(self):
        from .open_brayton import _native_mechanism_signature

        current_signature = _native_mechanism_signature(self.native_phase)
        if current_signature != self._mechanism_signature:
            raise ValueError("Native compression mechanism changed after the run")
        if _state(self.native_phase, "compressor_outlet") != self.actual_outlet:
            raise ValueError("Native compression outlet state changed after the run")
        if _payload_digest(self) != self._payload_seal:
            raise ValueError("Compression inputs, states or ledgers changed after the run")


def _issue_real_fluid_run(**values):
    token = object()
    _PENDING_REAL_FLUID_ISSUERS.add(token)
    try:
        return HydrogenRealFluidCompressionRun(**values, _issuer_token=token)
    except Exception:
        _PENDING_REAL_FLUID_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class HydrogenRealFluidCompressionRun:
    inputs: HydrogenRealFluidCompressionInputs
    provider_id: str
    provider_version: str
    property_basis: PropertyBasis
    inlet: HydrogenCompressionState
    isentropic_outlet: HydrogenCompressionState
    actual_outlet: HydrogenCompressionState
    specific_shaft_work_j_kg: float
    shaft_power_w: float
    enthalpy_rise_w: float
    energy_residual_w: float
    provider: object = field(repr=False, compare=False)
    _provider_signature: tuple = field(repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _payload_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_REAL_FLUID_ISSUERS:
            raise ValueError("Real-fluid compression results are issued only by the CoolProp runner")
        _PENDING_REAL_FLUID_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        from ..thermo.coolprop import CoolPropProperties

        if type(self.provider) is not CoolPropProperties:
            raise TypeError("Inject the existing CoolPropProperties provider directly")
        if type(self.property_basis) is not PropertyBasis:
            raise TypeError("Retain the CoolProp PropertyBasis")
        if self.provider_id != self.inputs.provider_id or self.provider_version != self.provider.version:
            raise ValueError("CoolProp provider identity/version differs from issued inputs")
        if self.provider.backend != "HEOS" or self.provider.basis.fluid not in {
                "Hydrogen", "ParaHydrogen", "OrthoHydrogen"}:
            raise ValueError("Real-fluid compression requires a CoolProp HEOS hydrogen provider")
        self.property_basis.require_compatible(self.provider.basis)
        for state in (self.inlet, self.isentropic_outlet, self.actual_outlet):
            if state.property_basis != self.property_basis:
                raise ValueError("Compression station property basis changed")
            phase_ok = state.phase in {"gas", "supercritical_gas"}
            if state.phase == "supercritical":
                phase_ok = (state.temperature_k >= self.provider.critical_temperature_k
                            and state.pressure_pa >= self.provider.critical_pressure_pa)
            if not phase_ok:
                raise ValueError("Compression station is outside the admitted gas phase")
            if not self.inputs.temperature_bounds_k[0] <= state.temperature_k <= self.inputs.temperature_bounds_k[1]:
                raise ValueError("Compression state exceeds its declared temperature domain")
            if not self.inputs.pressure_bounds_pa[0] <= state.pressure_pa <= self.inputs.pressure_bounds_pa[1]:
                raise ValueError("Compression state exceeds its declared pressure domain")
        if (self.inlet.station, self.isentropic_outlet.station, self.actual_outlet.station) != (
                "fuel_inlet", "isentropic_reference", "compressor_outlet"):
            raise ValueError("Real-fluid compression station ordering is invalid")
        if not math.isclose(self.inlet.temperature_k, self.inputs.inlet_temperature_k,
                            rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("Real-fluid inlet temperature differs from the input")
        if not math.isclose(self.inlet.pressure_pa, self.inputs.inlet_pressure_pa,
                            rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError("Real-fluid inlet pressure differs from the input")
        if not math.isclose(self.actual_outlet.pressure_pa, self.inputs.discharge_pressure_pa,
                            rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError("Real-fluid discharge pressure differs from the input")
        if not math.isclose(self.isentropic_outlet.pressure_pa,
                            self.inputs.discharge_pressure_pa,
                            rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError("CoolProp PS reference pressure differs from the discharge target")
        if not math.isclose(self.isentropic_outlet.entropy_j_kg_k,
                            self.inlet.entropy_j_kg_k,
                            rel_tol=self.inputs.entropy_relative_tolerance, abs_tol=1e-5):
            raise ValueError("CoolProp PS result does not preserve inlet entropy within tolerance")
        for name in ("specific_shaft_work_j_kg", "shaft_power_w", "enthalpy_rise_w",
                     "energy_residual_w"):
            object.__setattr__(self, name, finite(getattr(self, name), name))
        expected_ledger = _compression_ledger(
            self.inputs, self.inlet, self.isentropic_outlet, self.actual_outlet)
        actual_ledger = (self.specific_shaft_work_j_kg, self.shaft_power_w,
                         self.enthalpy_rise_w, self.energy_residual_w)
        if any(not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-7)
               for a, b in zip(actual_ledger, expected_ledger, strict=True)):
            raise ValueError("Real-fluid shaft ledger differs from the shared compression balance")
        if _coolprop_provider_signature(self.provider) != self._provider_signature:
            raise ValueError("CoolProp provider metadata changed while issuing the result")
        object.__setattr__(self, "_payload_seal", _payload_digest(self))

    def require_current(self):
        if _coolprop_provider_signature(self.provider) != self._provider_signature:
            raise ValueError("CoolProp provider identity, version, backend or basis changed")
        self.property_basis.require_compatible(self.provider.basis)
        if _payload_digest(self) != self._payload_seal:
            raise ValueError("Real-fluid inputs, states or shaft ledger changed after the run")


@dataclass(frozen=True, slots=True)
class HydrogenFuelBraytonLink:
    """One-way coupling of a fuel compressor to the existing open Brayton point.

    This retained ledger verifies pressure, temperature, mechanism/window labels
    and hydrogen flow against the native cycle. It reports gas-path power after
    the fuel-compressor load, before mechanical, generator or auxiliary losses.
    """

    cycle_run: object
    fuel_compression: HydrogenCompressionRun
    air_mass_flow_kg_s: float
    coupling_evidence_id: str
    cycle_shaft_power_w: float = field(init=False)
    fuel_compressor_power_w: float = field(init=False)
    net_after_fuel_compression_w: float = field(init=False)
    shaft_residual_w: float = field(init=False)
    _payload_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        from .open_brayton import OpenBraytonRun

        if type(self.cycle_run) is not OpenBraytonRun:
            raise TypeError("Supply an actual native OpenBraytonRun")
        if type(self.fuel_compression) is not HydrogenCompressionRun:
            raise TypeError("Supply a HydrogenCompressionRun")
        self.fuel_compression.require_current()
        air_flow = finite(self.air_mass_flow_kg_s, "Brayton compressor-inlet air flow",
                          positive=True)
        evidence = _identity(self.coupling_evidence_id, "fuel/Brayton coupling evidence")
        cycle_input = self.cycle_run.inputs
        fuel_input = self.fuel_compression.inputs
        hydrogen_feed = self.cycle_run.states[2]
        cycle_fuel_flow = air_flow * cycle_input.hydrogen_fuel_to_air_mass_ratio
        if fuel_input.mechanism_id != cycle_input.mechanism_id:
            raise ValueError("Fuel compressor and cycle must declare one mechanism identity")
        if fuel_input.process_window_id != cycle_input.process_window_id:
            raise ValueError("Fuel compressor and Brayton cycle windows differ")
        if self.fuel_compression._mechanism_signature != self.cycle_run._mechanism_signature:
            raise ValueError("Fuel compressor and Brayton native mechanism definitions differ")
        if not math.isclose(fuel_input.discharge_pressure_pa, hydrogen_feed.pressure_pa,
                            rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError("Fuel-compressor discharge pressure must match the native combustor feed")
        if not math.isclose(self.fuel_compression.actual_outlet.temperature_k,
                            hydrogen_feed.temperature_k, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("Cycle hydrogen-feed temperature differs from compressor discharge")
        if not math.isclose(fuel_input.hydrogen_mass_flow_kg_s, cycle_fuel_flow,
                            rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("Fuel-compressor flow differs from the cycle's declared fuel/air ratio")
        gas_path = self.cycle_run.net_work_j_kg_air * air_flow
        compressor = self.fuel_compression.shaft_power_w
        net = gas_path - compressor
        for name, value in (("air_mass_flow_kg_s", air_flow),
                            ("coupling_evidence_id", evidence),
                            ("cycle_shaft_power_w", gas_path),
                            ("fuel_compressor_power_w", compressor),
                            ("net_after_fuel_compression_w", net),
                            ("shaft_residual_w", net - gas_path + compressor)):
            object.__setattr__(self, name, value if name == "coupling_evidence_id"
                               else finite(value, name))
        self._require_cycle_current()
        object.__setattr__(self, "_payload_seal", _payload_digest(self))

    def _require_cycle_current(self):
        from .open_brayton import _native_mechanism_signature, _snapshot

        if _native_mechanism_signature(self.cycle_run.native_phase) != self.cycle_run._mechanism_signature:
            raise ValueError("Native Brayton mechanism changed after the cycle run")
        if _snapshot(self.cycle_run.native_phase, "turbine_exhaust",
                     self.cycle_run.inputs) != self.cycle_run.states[-1]:
            raise ValueError("Native Brayton terminal state changed after the cycle run")

    def require_current(self):
        """Revalidate input linkage and the retained native cycle before reuse."""
        self.fuel_compression.require_current()
        self._require_cycle_current()
        if _payload_digest(self) != self._payload_seal:
            raise ValueError("Fuel/Brayton inputs, evidence or ledger changed after issue")


class HydrogenCompressionError(RuntimeError):
    """Retain the failed native stage and original exception."""

    def __init__(self, stage, cause, native_phase, completed_states=()):
        self.stage = stage
        self.cause = cause
        self.native_phase = native_phase
        self.completed_states = tuple(completed_states)
        super().__init__(f"Native hydrogen compression failed during {stage}")


def _state(phase, station):
    fractions = dict(zip(phase.species_names, phase.Y, strict=True))
    other = math.fsum(float(value) for name, value in fractions.items() if name != "H2")
    h2 = float(fractions.get("H2", 0.0))
    if not math.isclose(h2, 1.0, rel_tol=0.0, abs_tol=1e-12) or other > 1e-12:
        raise ValueError("Fuel-compression stage only admits pure gas-phase H2")
    if phase.phase_of_matter != "gas":
        raise ValueError("Fuel compression requires a gas phase")
    return HydrogenCompressionState(station, float(phase.T), float(phase.P),
                                    float(phase.enthalpy_mass), float(phase.entropy_mass), h2,
                                    float(phase.density_mass))


def run_hydrogen_compression(phase, inputs: HydrogenCompressionInputs) -> HydrogenCompressionRun:
    """Solve one steady adiabatic stage with Cantera's native ``SPY``/``HPY``.

    Efficiency is applied to the isentropic enthalpy rise; the resulting outlet
    is solved at the caller's discharge pressure and unchanged H2 composition.
    No real-gas correction is added to Cantera's selected ideal-gas phase.
    """
    if not isinstance(inputs, HydrogenCompressionInputs):
        raise TypeError("Supply HydrogenCompressionInputs")
    required = ("thermo_model", "species_names", "element_names", "phase_of_matter",
                "TPX", "SPY", "HPY", "Y", "T", "P", "density_mass", "enthalpy_mass",
                "entropy_mass", "min_temp", "max_temp")
    if any(not hasattr(phase, name) for name in required):
        raise TypeError("Supply an actual Cantera ideal-gas ThermoPhase with SPY and HPY")
    if phase.thermo_model != "ideal-gas" or "H2" not in phase.species_names:
        raise ValueError("The native mechanism must be ideal-gas and contain H2")
    states = []
    stage = "fuel inlet"
    try:
        phase.TPX = inputs.inlet_temperature_k, inputs.inlet_pressure_pa, {"H2": 1.0}
        inlet = _state(phase, "fuel_inlet")
        states.append(inlet)

        stage = "isentropic reference"
        phase.SPY = inlet.entropy_j_kg_k, inputs.discharge_pressure_pa, phase.Y
        isentropic = _state(phase, "isentropic_reference")
        if isentropic.enthalpy_j_kg <= inlet.enthalpy_j_kg:
            raise ValueError("Native isentropic compression state has no positive enthalpy rise")

        stage = "actual compressor outlet"
        h_out = inlet.enthalpy_j_kg + (
            isentropic.enthalpy_j_kg-inlet.enthalpy_j_kg
        ) / inputs.isentropic_efficiency
        phase.HPY = h_out, inputs.discharge_pressure_pa, phase.Y
        outlet = _state(phase, "compressor_outlet")
        states.append(outlet)
        work, power, rise, residual = _compression_ledger(
            inputs, inlet, isentropic, outlet)
        from .open_brayton import _native_mechanism_signature
        return _issue_compression_run(inputs=inputs, inlet=inlet,
            isentropic_outlet=isentropic, actual_outlet=outlet,
            specific_shaft_work_j_kg=work, shaft_power_w=power,
            enthalpy_rise_w=rise, energy_residual_w=residual, native_phase=phase,
            _mechanism_signature=_native_mechanism_signature(phase))
    except Exception as exc:
        raise HydrogenCompressionError(stage, exc, phase, states) from exc


def run_real_fluid_hydrogen_compression(provider, inputs: HydrogenRealFluidCompressionInputs
                                        ) -> HydrogenRealFluidCompressionRun:
    """Run PT inlet, PS reference and PH efficiency outlet with injected CoolProp HEOS.

    Each accepted station must be a single-phase gas or a supercritical state
    above both critical coordinates, and must stay within the caller-declared
    application envelope. The reference CoolProp backend does not silently fall
    back to Cantera or ideal-gas properties.
    """
    from ..thermo.coolprop import CoolPropProperties

    if type(provider) is not CoolPropProperties:
        raise TypeError("Inject an actual h2physics.thermo.CoolPropProperties provider")
    if not isinstance(inputs, HydrogenRealFluidCompressionInputs):
        raise TypeError("Supply HydrogenRealFluidCompressionInputs")
    if provider.backend != "HEOS":
        raise ValueError("The direct real-fluid compression reference requires CoolProp HEOS")
    if provider.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}:
        raise ValueError("CoolProp provider basis must identify a hydrogen fluid")
    provider_signature = _coolprop_provider_signature(provider)
    basis = provider.basis
    states = []
    stage = "CoolProp PT inlet"
    try:
        inlet_packet = provider.state_pt(inputs.inlet_pressure_pa, inputs.inlet_temperature_k)
        inlet = _coolprop_state_snapshot(inlet_packet, "fuel_inlet", basis, provider)
        states.append(inlet)

        stage = "CoolProp PS isentropic reference"
        reference_packet = provider.state_ps(inputs.discharge_pressure_pa,
                                             inlet.entropy_j_kg_k)
        reference = _coolprop_state_snapshot(
            reference_packet, "isentropic_reference", basis, provider)
        if reference.enthalpy_j_kg <= inlet.enthalpy_j_kg:
            raise ValueError("CoolProp PS reference has no positive compression enthalpy rise")

        stage = "CoolProp PH efficiency outlet"
        target_h = inlet.enthalpy_j_kg + (
            reference.enthalpy_j_kg-inlet.enthalpy_j_kg
        ) / inputs.isentropic_efficiency
        outlet_packet = provider.state_ph(inputs.discharge_pressure_pa, target_h)
        outlet = _coolprop_state_snapshot(
            outlet_packet, "compressor_outlet", basis, provider)
        states.append(outlet)

        for label, state in (("inlet", inlet), ("isentropic reference", reference),
                             ("outlet", outlet)):
            if not (inputs.temperature_bounds_k[0] <= state.temperature_k
                    <= inputs.temperature_bounds_k[1]):
                raise ValueError(f"{label} temperature is outside the declared CoolProp domain")
            if not (inputs.pressure_bounds_pa[0] <= state.pressure_pa
                    <= inputs.pressure_bounds_pa[1]):
                raise ValueError(f"{label} pressure is outside the declared CoolProp domain")
        if not math.isclose(reference.entropy_j_kg_k, inlet.entropy_j_kg_k,
                            rel_tol=inputs.entropy_relative_tolerance, abs_tol=1e-5):
            raise ValueError("CoolProp PS result does not preserve inlet entropy within tolerance")
        ledger = _compression_ledger(inputs, inlet, reference, outlet)
        if _coolprop_provider_signature(provider) != provider_signature:
            raise ValueError("CoolProp provider identity/basis changed during the compression run")
        return _issue_real_fluid_run(
            inputs=inputs, provider_id=inputs.provider_id, provider_version=provider.version,
            property_basis=basis, inlet=inlet, isentropic_outlet=reference,
            actual_outlet=outlet, specific_shaft_work_j_kg=ledger[0],
            shaft_power_w=ledger[1], enthalpy_rise_w=ledger[2],
            energy_residual_w=ledger[3], provider=provider,
            _provider_signature=provider_signature)
    except Exception as exc:
        raise HydrogenCompressionError(stage, exc, provider, states) from exc


def couple_hydrogen_compression_to_brayton(cycle_run, fuel_compression, *,
                                           air_mass_flow_kg_s: float,
                                           evidence_id: str) -> HydrogenFuelBraytonLink:
    """Subtract explicitly matched fuel-compressor power from native cycle work."""
    return HydrogenFuelBraytonLink(cycle_run, fuel_compression, air_mass_flow_kg_s,
                                   evidence_id)
