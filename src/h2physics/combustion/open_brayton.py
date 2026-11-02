"""Caller-bounded hydrogen open Brayton reference using native Cantera gas states.

This is a steady, single-stream reference cycle. It delegates mixture properties
and HP equilibrium to the supplied Cantera phase; it does not provide turbomachine
maps, mechanical losses, controls, cooling flows or a plant equipment design.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from ..core import finite


def _identity(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name} identity")
    return value.strip()


def _composition(value, name):
    if isinstance(value, Mapping):
        pairs = tuple(value.items())
    else:
        if isinstance(value, (str, bytes)):
            raise TypeError(f"{name} must be a species/fraction mapping or pair sequence")
        pairs = tuple(value)
    if not pairs:
        raise ValueError(f"{name} cannot be empty")
    normalized = []
    seen = set()
    for pair in pairs:
        try:
            species, raw_fraction = pair
        except (TypeError, ValueError) as error:
            raise TypeError(f"{name} entries must be species/fraction pairs") from error
        species = _identity(species, f"{name} species")
        if species in seen:
            raise ValueError(f"{name} contains a duplicate species")
        seen.add(species)
        fraction = finite(raw_fraction, f"{name} mole fraction")
        if fraction < 0.0:
            raise ValueError(f"{name} mole fractions cannot be negative")
        normalized.append((species, fraction))
    if not math.isclose(math.fsum(item[1] for item in normalized), 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError(f"{name} mole fractions must sum to one; they are not normalized implicitly")
    return tuple(normalized)


def _require_close(actual, expected, label, *, relative=1e-12, absolute=1e-9):
    if not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute):
        raise ValueError(f"{label} differs from the retained native station states")


@dataclass(frozen=True, slots=True)
class OpenBraytonInputs:
    """Explicit one-point boundary and caller-supplied machine performance inputs.

    The reference is per kilogram of compressor-inlet air. Fuel compression,
    generator conversion, mechanical loss, cooling flow, pressure-side bleed,
    external heat loss and accessory loads are outside the boundary.
    """

    mechanism_id: str
    process_window_id: str
    air_temperature_k: float
    air_pressure_pa: float
    air_mole_fractions: tuple
    compressor_pressure_ratio: float
    compressor_isentropic_efficiency: float
    combustor_pressure_recovery: float
    hydrogen_fuel_to_air_mass_ratio: float
    hydrogen_inlet_temperature_k: float
    turbine_exhaust_pressure_pa: float
    turbine_isentropic_efficiency: float
    hydrogen_lhv_j_kg: float
    air_state_evidence_id: str
    hydrogen_feed_evidence_id: str
    machine_parameter_evidence_id: str
    lhv_evidence_id: str

    def __post_init__(self):
        object.__setattr__(self, "mechanism_id", _identity(self.mechanism_id, "mechanism"))
        object.__setattr__(self, "process_window_id", _identity(self.process_window_id, "process-window"))
        for field, label in (
            ("air_state_evidence_id", "air-state evidence"),
            ("hydrogen_feed_evidence_id", "hydrogen-feed evidence"),
            ("machine_parameter_evidence_id", "machine-parameter evidence"),
            ("lhv_evidence_id", "hydrogen-LHV evidence"),
        ):
            object.__setattr__(self, field, _identity(getattr(self, field), label))
        object.__setattr__(self, "air_mole_fractions", _composition(
            self.air_mole_fractions, "air composition"
        ))
        if dict(self.air_mole_fractions).get("O2", 0.0) <= 0.0:
            raise ValueError("The declared air/oxidizer stream must contain positive O2")
        for field, label in (
            ("air_temperature_k", "air inlet temperature"),
            ("hydrogen_inlet_temperature_k", "hydrogen inlet temperature"),
        ):
            object.__setattr__(self, field, finite(getattr(self, field), label, positive=True))
        for field, label in (
            ("air_pressure_pa", "air inlet pressure"),
            ("turbine_exhaust_pressure_pa", "turbine exhaust pressure"),
            ("hydrogen_lhv_j_kg", "hydrogen lower heating value"),
        ):
            object.__setattr__(self, field, finite(getattr(self, field), label, positive=True))
        ratio = finite(self.compressor_pressure_ratio, "compressor pressure ratio", positive=True)
        if ratio <= 1.0:
            raise ValueError("Compressor pressure ratio must exceed one")
        object.__setattr__(self, "compressor_pressure_ratio", ratio)
        for field, label in (
            ("compressor_isentropic_efficiency", "compressor isentropic efficiency"),
            ("turbine_isentropic_efficiency", "turbine isentropic efficiency"),
        ):
            efficiency = finite(getattr(self, field), label, positive=True)
            if efficiency > 1.0:
                raise ValueError(f"{label} cannot exceed one")
            object.__setattr__(self, field, efficiency)
        recovery = finite(self.combustor_pressure_recovery, "combustor pressure recovery", positive=True)
        if recovery > 1.0:
            raise ValueError("Combustor pressure recovery must be in (0, 1]")
        object.__setattr__(self, "combustor_pressure_recovery", recovery)
        object.__setattr__(self, "hydrogen_fuel_to_air_mass_ratio", finite(
            self.hydrogen_fuel_to_air_mass_ratio,
            "hydrogen/fuel-to-air mass ratio", positive=True,
        ))
        compressor_pressure = self.air_pressure_pa * ratio
        combustor_pressure = compressor_pressure * recovery
        if self.turbine_exhaust_pressure_pa >= combustor_pressure:
            raise ValueError("Turbine exhaust pressure must be below combustor outlet pressure")


@dataclass(frozen=True, slots=True)
class BraytonGasState:
    """Immutable scalar/native-composition snapshot of one reference-cycle station."""

    station: str
    temperature_k: float
    pressure_pa: float
    enthalpy_j_kg: float
    entropy_j_kg_k: float
    species_names: tuple[str, ...]
    mass_fractions: tuple[float, ...]
    elemental_mass_fractions: tuple[tuple[str, float], ...]
    mechanism_id: str
    process_window_id: str

    def __post_init__(self):
        object.__setattr__(self, "station", _identity(self.station, "station"))
        object.__setattr__(self, "mechanism_id", _identity(self.mechanism_id, "mechanism"))
        object.__setattr__(self, "process_window_id", _identity(self.process_window_id, "process-window"))
        object.__setattr__(self, "temperature_k", finite(self.temperature_k, "state temperature", positive=True))
        object.__setattr__(self, "pressure_pa", finite(self.pressure_pa, "state pressure", positive=True))
        object.__setattr__(self, "enthalpy_j_kg", finite(self.enthalpy_j_kg, "state enthalpy"))
        object.__setattr__(self, "entropy_j_kg_k", finite(self.entropy_j_kg_k, "state entropy"))
        if isinstance(self.species_names, (str, bytes)):
            raise TypeError("Species names must be a sequence, not text")
        names = tuple(_identity(value, "species") for value in self.species_names)
        if not names or len(set(names)) != len(names):
            raise ValueError("State needs unique ordered species names")
        fractions = tuple(finite(value, "species mass fraction") for value in self.mass_fractions)
        if (len(fractions) != len(names) or any(value < 0.0 for value in fractions)
                or not math.isclose(math.fsum(fractions), 1.0, rel_tol=0, abs_tol=1e-10)):
            raise ValueError("State species fractions must be a complete normalized vector")
        if isinstance(self.elemental_mass_fractions, (str, bytes)):
            raise TypeError("Element fractions must be a sequence, not text")
        raw_elements = tuple(self.elemental_mass_fractions)
        elements, seen = [], set()
        for entry in raw_elements:
            try:
                name, fraction = entry
            except (TypeError, ValueError) as error:
                raise TypeError("Element fractions must be name/value pairs") from error
            name = _identity(name, "element")
            if name in seen:
                raise ValueError("Element fractions contain a duplicate element")
            seen.add(name)
            fraction = finite(fraction, "element mass fraction")
            if fraction < 0.0 or fraction > 1.0 + 1e-10:
                raise ValueError("Element mass fractions must lie in [0, 1]")
            elements.append((name, fraction))
        if (not elements or not math.isclose(
            math.fsum(value for _, value in elements), 1.0, rel_tol=0, abs_tol=1e-8
        )):
            raise ValueError("Element fractions must cover a normalized elemental basis")
        object.__setattr__(self, "species_names", names)
        object.__setattr__(self, "mass_fractions", fractions)
        object.__setattr__(self, "elemental_mass_fractions", tuple(elements))


class OpenBraytonError(RuntimeError):
    """Failed native stage plus its retained phase and completed state snapshots."""

    def __init__(self, stage, cause, native_phase, completed_states, mechanism_id):
        self.stage = stage
        self.cause = cause
        self.native_phase = native_phase
        self.completed_states = tuple(completed_states)
        self.mechanism_id = mechanism_id
        super().__init__(f"Native open Brayton reference failed during {stage}")


@dataclass(frozen=True, slots=True)
class OpenBraytonRun:
    """Reference cycle result; powers are ideal single-shaft terms before losses."""

    inputs: OpenBraytonInputs
    states: tuple[BraytonGasState, ...]
    elemental_mass_residuals: tuple[tuple[str, float], ...]
    compressor_work_j_kg_air: float
    turbine_work_j_kg_air: float
    net_work_j_kg_air: float
    hydrogen_heat_input_j_kg_air: float
    thermal_efficiency: float
    combustor_enthalpy_residual_j_kg_air: float
    open_cycle_energy_residual_j_kg_air: float
    native_phase: object
    _mechanism_signature: tuple
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_OPEN_BRAYTON_ISSUERS:
            raise ValueError("Open Brayton results are issued only by the native cycle runner")
        _PENDING_OPEN_BRAYTON_ISSUERS.remove(self._issuer_token)
        if not isinstance(self.inputs, OpenBraytonInputs):
            raise TypeError("Run output must retain its typed input declaration")
        states = tuple(self.states)
        expected_stations = (
            "air_inlet", "compressor_outlet", "hydrogen_feed",
            "combustor_outlet", "turbine_exhaust",
        )
        if len(states) != len(expected_stations) or any(
            not isinstance(state, BraytonGasState) for state in states
        ):
            raise TypeError("Run output needs all five typed immutable station states")
        if tuple(state.station for state in states) != expected_stations:
            raise ValueError("Run station order must follow the declared open-cycle boundary")
        if any(
            state.mechanism_id != self.inputs.mechanism_id
            or state.process_window_id != self.inputs.process_window_id
            for state in states
        ):
            raise ValueError("Station states must retain the input mechanism and process-window identities")
        if any(state.species_names != states[0].species_names for state in states):
            raise ValueError("Station states must use one ordered species basis")
        element_basis = tuple(name for name, _ in states[0].elemental_mass_fractions)
        if any(
            tuple(name for name, _ in state.elemental_mass_fractions) != element_basis
            for state in states
        ):
            raise ValueError("Station states must use one ordered elemental basis")
        object.__setattr__(self, "states", states)
        element_residuals = tuple(
            (_identity(name, "element residual"), finite(value, "element residual"))
            for name, value in self.elemental_mass_residuals
        )
        if (not element_residuals
                or tuple(name for name, _ in element_residuals)
                != tuple(name for name, _ in states[3].elemental_mass_fractions)):
            raise ValueError("Element residuals must use the combustor outlet's declared element basis")
        object.__setattr__(self, "elemental_mass_residuals", element_residuals)
        for field, label in (
            ("compressor_work_j_kg_air", "compressor work"),
            ("turbine_work_j_kg_air", "turbine work"),
            ("net_work_j_kg_air", "net work"),
            ("hydrogen_heat_input_j_kg_air", "hydrogen heat input"),
            ("thermal_efficiency", "thermal efficiency"),
            ("combustor_enthalpy_residual_j_kg_air", "combustor enthalpy residual"),
            ("open_cycle_energy_residual_j_kg_air", "open-cycle energy residual"),
        ):
            object.__setattr__(self, field, finite(getattr(self, field), label))
        if self.hydrogen_heat_input_j_kg_air <= 0.0:
            raise ValueError("Hydrogen heat input must be positive")

        air_in, compressor_out, hydrogen_feed, combustor_out, turbine_out = states
        fuel_ratio = self.inputs.hydrogen_fuel_to_air_mass_ratio
        expected_compressor_work = compressor_out.enthalpy_j_kg - air_in.enthalpy_j_kg
        expected_turbine_work = (1.0 + fuel_ratio) * (
            combustor_out.enthalpy_j_kg - turbine_out.enthalpy_j_kg
        )
        expected_net_work = expected_turbine_work - expected_compressor_work
        expected_heat_input = fuel_ratio * self.inputs.hydrogen_lhv_j_kg
        expected_combustor_residual = (
            (1.0 + fuel_ratio) * combustor_out.enthalpy_j_kg
            - compressor_out.enthalpy_j_kg - fuel_ratio * hydrogen_feed.enthalpy_j_kg
        )
        expected_energy_residual = (
            air_in.enthalpy_j_kg + fuel_ratio * hydrogen_feed.enthalpy_j_kg
            + expected_compressor_work - expected_turbine_work
            - (1.0 + fuel_ratio) * turbine_out.enthalpy_j_kg
        )
        _require_close(self.compressor_work_j_kg_air, expected_compressor_work, "Compressor work")
        _require_close(self.turbine_work_j_kg_air, expected_turbine_work, "Turbine work")
        _require_close(self.net_work_j_kg_air, expected_net_work, "Net work")
        _require_close(self.hydrogen_heat_input_j_kg_air, expected_heat_input, "Hydrogen heat input")
        _require_close(
            self.thermal_efficiency,
            expected_net_work / expected_heat_input,
            "Thermal efficiency",
        )
        _require_close(
            self.combustor_enthalpy_residual_j_kg_air,
            expected_combustor_residual,
            "Combustor enthalpy residual",
        )
        _require_close(
            self.open_cycle_energy_residual_j_kg_air,
            expected_energy_residual,
            "Open-cycle energy residual",
        )
        air_elements, fuel_elements, product_elements = map(
            _element_map, (compressor_out, hydrogen_feed, combustor_out)
        )
        expected_elements = tuple(
            (element, product_elements[element]
             - (air_elements[element] + fuel_ratio * fuel_elements[element]) / (1.0 + fuel_ratio))
            for element in product_elements
        )
        if tuple(name for name, _ in expected_elements) != tuple(
            name for name, _ in element_residuals
        ):
            raise ValueError("Element residual identity differs from the retained native station states")
        for (name, actual), (_, expected) in zip(element_residuals, expected_elements, strict=True):
            _require_close(actual, expected, f"Element residual {name}", absolute=1e-12)
        expected_pressures = (
            self.inputs.air_pressure_pa,
            self.inputs.air_pressure_pa * self.inputs.compressor_pressure_ratio,
            self.inputs.air_pressure_pa * self.inputs.compressor_pressure_ratio
            * self.inputs.combustor_pressure_recovery,
            self.inputs.air_pressure_pa * self.inputs.compressor_pressure_ratio
            * self.inputs.combustor_pressure_recovery,
            self.inputs.turbine_exhaust_pressure_pa,
        )
        for state, expected_pressure in zip(states, expected_pressures, strict=True):
            _require_close(state.pressure_pa, expected_pressure, f"{state.station} pressure")
        _require_close(air_in.temperature_k, self.inputs.air_temperature_k, "Air inlet temperature")
        _require_close(
            hydrogen_feed.temperature_k,
            self.inputs.hydrogen_inlet_temperature_k,
            "Hydrogen feed temperature",
        )
        hydrogen_index = states[0].species_names.index("H2")
        if not math.isclose(hydrogen_feed.mass_fractions[hydrogen_index], 1.0, rel_tol=0, abs_tol=1e-12):
            raise ValueError("Hydrogen feed station must retain a pure-H2 composition")
        terminal = _snapshot(self.native_phase, "native_terminal", self.inputs)
        if terminal.species_names != turbine_out.species_names:
            raise ValueError("Native terminal phase species differ from the turbine station basis")
        for actual, expected, label in (
            (terminal.temperature_k, turbine_out.temperature_k, "Native terminal temperature"),
            (terminal.pressure_pa, turbine_out.pressure_pa, "Native terminal pressure"),
            (terminal.enthalpy_j_kg, turbine_out.enthalpy_j_kg, "Native terminal enthalpy"),
            (terminal.entropy_j_kg_k, turbine_out.entropy_j_kg_k, "Native terminal entropy"),
        ):
            _require_close(actual, expected, label)
        for actual, expected in zip(
            terminal.mass_fractions, turbine_out.mass_fractions, strict=True
        ):
            _require_close(actual, expected, "Native terminal species fraction", absolute=1e-12)
        if _native_species_signature(self.native_phase) != (
            states[0].species_names, tuple(name for name, _ in states[0].elemental_mass_fractions)
        ):
            raise ValueError("Native terminal phase mechanism species/elements changed after execution")
        if _native_mechanism_signature(self.native_phase) != self._mechanism_signature:
            raise ValueError("Native mechanism identity changed after execution")

    def require_current(self):
        """Recheck retained native mechanism and terminal state without minting a run."""
        if _native_mechanism_signature(self.native_phase) != self._mechanism_signature:
            raise ValueError("Native mechanism identity changed after execution")
        terminal = _snapshot(self.native_phase, "native_terminal", self.inputs)
        turbine_out = self.states[4]
        if terminal.species_names != turbine_out.species_names:
            raise ValueError("Native terminal phase species differ from the retained turbine station")
        for actual, expected, label in (
            (terminal.temperature_k, turbine_out.temperature_k, "Native terminal temperature"),
            (terminal.pressure_pa, turbine_out.pressure_pa, "Native terminal pressure"),
            (terminal.enthalpy_j_kg, turbine_out.enthalpy_j_kg, "Native terminal enthalpy"),
            (terminal.entropy_j_kg_k, turbine_out.entropy_j_kg_k, "Native terminal entropy"),
        ):
            _require_close(actual, expected, label)
        for actual, expected in zip(terminal.mass_fractions, turbine_out.mass_fractions, strict=True):
            _require_close(actual, expected, "Native terminal species fraction", absolute=1e-12)
        return self


def _require_native_phase(phase):
    required = (
        "thermo_model", "basis", "species_names", "element_names", "Y", "T", "P",
        "enthalpy_mass", "entropy_mass", "molecular_weights",
        "atomic_weights", "n_atoms", "species", "reactions", "multiplier",
        "n_reactions", "TPX", "SPY", "HPY", "equilibrate",
    )
    if any(not hasattr(phase, name) for name in required):
        raise TypeError("Supply a native Cantera gas ThermoPhase with SPY/HPY and HP equilibrium")
    if phase.thermo_model != "ideal-gas":
        raise ValueError("This reference admits only a native ideal-gas Cantera phase")
    if phase.basis != "mass":
        raise ValueError(
            "This reference uses mass-specific J/kg and J/kg/K cycle properties; "
            "set the native Cantera phase basis to 'mass'"
        )


def _native_species_signature(phase):
    return (tuple(str(value) for value in phase.species_names),
            tuple(str(value) for value in phase.element_names))


def _native_mechanism_signature(phase):
    """Fingerprint mechanism definitions used by this calculation."""
    species, elements = _native_species_signature(phase)
    molecular = tuple(float(value).hex() for value in phase.molecular_weights)
    atomic = tuple(float(value).hex() for value in phase.atomic_weights)
    atoms = tuple(
        tuple(float(phase.n_atoms(i, j)).hex() for j in range(len(elements)))
        for i in range(len(species))
    )
    thermo = tuple(
        (
            item.name,
            tuple(sorted((str(key), _mechanism_value(value))
                         for key, value in dict(item.composition).items())),
            float(item.charge).hex(),
            type(item.thermo).__name__,
            float(item.thermo.reference_pressure).hex(),
            float(item.thermo.min_temp).hex(),
            float(item.thermo.max_temp).hex(),
            tuple(float(value).hex() for value in item.thermo.coeffs),
        )
        for item in phase.species()
    )
    reactions = tuple(
        (_mechanism_value(reaction.input_data),
         float(phase.multiplier(index)).hex())
        for index, reaction in enumerate(phase.reactions())
    )
    return (str(phase.thermo_model), str(phase.basis), species, elements, molecular, atomic, atoms,
            thermo, reactions)


def _mechanism_value(value):
    """Canonicalize Cantera's nested species/reaction definition mappings."""
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _mechanism_value(item))
                            for key, item in value.items()))
    if isinstance(value, (tuple, list)):
        return tuple(_mechanism_value(item) for item in value)
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            return repr(number)
        return number.hex()
    if isinstance(value, np.ndarray):
        return _mechanism_value(value.tolist())
    return repr(value)


def _snapshot(phase, station, inputs):
    names = tuple(str(value) for value in phase.species_names)
    elements = tuple(str(value) for value in phase.element_names)
    mass = np.asarray(phase.Y, dtype=float)
    molecular_weights = np.asarray(phase.molecular_weights, dtype=float)
    atomic_weights = np.asarray(phase.atomic_weights, dtype=float)
    if (mass.ndim != 1 or mass.size != len(names) or molecular_weights.shape != mass.shape
            or atomic_weights.shape != (len(elements),) or not np.all(np.isfinite(mass))
            or np.any(mass < 0) or not np.isclose(math.fsum(mass), 1.0, atol=1e-12, rtol=0)):
        raise ValueError("Native Cantera state has invalid species or element arrays")
    element_mass = []
    for element_index, element in enumerate(elements):
        contribution = 0.0
        for species_index in range(len(names)):
            atoms = finite(phase.n_atoms(species_index, element_index), "native atom count")
            contribution += mass[species_index] * atoms * atomic_weights[element_index] / molecular_weights[species_index]
        element_mass.append((element, finite(contribution, "element mass fraction")))
    return BraytonGasState(
        station,
        finite(phase.T, f"{station} temperature", positive=True),
        finite(phase.P, f"{station} pressure", positive=True),
        finite(phase.enthalpy_mass, f"{station} enthalpy"),
        finite(phase.entropy_mass, f"{station} entropy"),
        names,
        tuple(float(value) for value in mass),
        tuple(element_mass),
        inputs.mechanism_id,
        inputs.process_window_id,
    )


def _element_map(state):
    return dict(state.elemental_mass_fractions)


_PENDING_OPEN_BRAYTON_ISSUERS: set[object] = set()


def _issue_open_brayton_run(**values):
    token = object()
    _PENDING_OPEN_BRAYTON_ISSUERS.add(token)
    try:
        return OpenBraytonRun(**values, _issuer_token=token)
    except Exception:
        _PENDING_OPEN_BRAYTON_ISSUERS.discard(token)
        raise


def run_open_cycle_brayton(phase, inputs: OpenBraytonInputs) -> OpenBraytonRun:
    """Evaluate a single-point H2 open Brayton reference with native Cantera.

    Compressor and turbine deviations are represented solely by caller-provided
    isentropic efficiencies; the combustor is adiabatic, constant-pressure and
    HP-equilibrium. Turbine expansion freezes the combustor outlet composition.
    This algebra includes neither component maps nor auxiliary hardware.
    """
    if not isinstance(inputs, OpenBraytonInputs):
        raise TypeError("Supply validated OpenBraytonInputs")
    _require_native_phase(phase)
    mechanism_signature = _native_mechanism_signature(phase)
    species = set(str(name) for name in phase.species_names)
    declared_air = dict(inputs.air_mole_fractions)
    if not set(declared_air).issubset(species) or "H2" not in species:
        raise ValueError("Mechanism must contain every declared air species and H2")
    states = []
    stage = "air inlet"
    try:
        phase.TPX = inputs.air_temperature_k, inputs.air_pressure_pa, declared_air
        air_in = _snapshot(phase, "air_inlet", inputs)
        states.append(air_in)

        stage = "compressor isentropic reference"
        compressor_pressure = inputs.air_pressure_pa * inputs.compressor_pressure_ratio
        phase.SPY = air_in.entropy_j_kg_k, compressor_pressure, air_in.mass_fractions
        h_isentropic = finite(phase.enthalpy_mass, "isentropic compressor enthalpy")
        if h_isentropic <= air_in.enthalpy_j_kg:
            raise ValueError("Native compressor reference state has no positive enthalpy rise")

        stage = "compressor"
        compressor_h = air_in.enthalpy_j_kg + (
            h_isentropic - air_in.enthalpy_j_kg
        ) / inputs.compressor_isentropic_efficiency
        phase.HPY = compressor_h, compressor_pressure, air_in.mass_fractions
        compressor_out = _snapshot(phase, "compressor_outlet", inputs)
        states.append(compressor_out)

        stage = "hydrogen feed state"
        combustor_pressure = compressor_pressure * inputs.combustor_pressure_recovery
        phase.TPX = inputs.hydrogen_inlet_temperature_k, combustor_pressure, {"H2": 1.0}
        hydrogen_feed = _snapshot(phase, "hydrogen_feed", inputs)
        states.append(hydrogen_feed)

        stage = "combustor inlet mixture"
        fuel_air_ratio = inputs.hydrogen_fuel_to_air_mass_ratio
        total_mass_per_air = 1.0 + fuel_air_ratio
        mixed_mass_fractions = (
            np.asarray(compressor_out.mass_fractions, dtype=float)
            + fuel_air_ratio * np.asarray(hydrogen_feed.mass_fractions, dtype=float)
        ) / total_mass_per_air
        mixed_enthalpy = (
            compressor_out.enthalpy_j_kg + fuel_air_ratio * hydrogen_feed.enthalpy_j_kg
        ) / total_mass_per_air
        phase.HPY = mixed_enthalpy, combustor_pressure, mixed_mass_fractions

        stage = "HP equilibrium combustor"
        phase.equilibrate("HP")
        combustor_out = _snapshot(phase, "combustor_outlet", inputs)
        states.append(combustor_out)

        stage = "turbine isentropic reference"
        phase.SPY = (
            combustor_out.entropy_j_kg_k,
            inputs.turbine_exhaust_pressure_pa,
            combustor_out.mass_fractions,
        )
        h_turbine_isentropic = finite(phase.enthalpy_mass, "isentropic turbine enthalpy")
        if h_turbine_isentropic >= combustor_out.enthalpy_j_kg:
            raise ValueError("Native turbine reference state has no positive enthalpy drop")

        stage = "turbine"
        turbine_h = combustor_out.enthalpy_j_kg - inputs.turbine_isentropic_efficiency * (
            combustor_out.enthalpy_j_kg - h_turbine_isentropic
        )
        phase.HPY = turbine_h, inputs.turbine_exhaust_pressure_pa, combustor_out.mass_fractions
        turbine_out = _snapshot(phase, "turbine_exhaust", inputs)
        states.append(turbine_out)
    except Exception as error:
        raise OpenBraytonError(stage, error, phase, states, inputs.mechanism_id) from error

    if not (len({state.species_names for state in states}) == 1):
        raise ValueError("Native Cantera species ordering changed during the cycle evaluation")
    fuel_air_ratio = inputs.hydrogen_fuel_to_air_mass_ratio
    compressor_work = compressor_out.enthalpy_j_kg - air_in.enthalpy_j_kg
    turbine_work = (1.0 + fuel_air_ratio) * (
        combustor_out.enthalpy_j_kg - turbine_out.enthalpy_j_kg
    )
    net_work = turbine_work - compressor_work
    fuel_heat = fuel_air_ratio * inputs.hydrogen_lhv_j_kg
    energy_residual = (
        air_in.enthalpy_j_kg + fuel_air_ratio * hydrogen_feed.enthalpy_j_kg
        + compressor_work - turbine_work
        - (1.0 + fuel_air_ratio) * turbine_out.enthalpy_j_kg
    )
    combustor_residual = (
        (1.0 + fuel_air_ratio) * combustor_out.enthalpy_j_kg
        - compressor_out.enthalpy_j_kg
        - fuel_air_ratio * hydrogen_feed.enthalpy_j_kg
    )
    air_elements, fuel_elements, product_elements = map(
        _element_map, (compressor_out, hydrogen_feed, combustor_out)
    )
    element_residuals = tuple(
        (element, product_elements[element]
         - (air_elements[element] + fuel_air_ratio * fuel_elements[element]) / (1.0 + fuel_air_ratio))
        for element in product_elements
    )
    result = _issue_open_brayton_run(
        inputs=inputs,
        states=tuple(states),
        elemental_mass_residuals=element_residuals,
        compressor_work_j_kg_air=finite(compressor_work, "compressor work"),
        turbine_work_j_kg_air=finite(turbine_work, "turbine work"),
        net_work_j_kg_air=finite(net_work, "net work"),
        hydrogen_heat_input_j_kg_air=finite(fuel_heat, "hydrogen heating input", positive=True),
        thermal_efficiency=finite(net_work / fuel_heat, "thermal efficiency"),
        combustor_enthalpy_residual_j_kg_air=finite(combustor_residual, "combustor enthalpy residual"),
        open_cycle_energy_residual_j_kg_air=finite(energy_residual, "open-cycle energy residual"),
        native_phase=phase,
        _mechanism_signature=mechanism_signature,
    )
    return result
