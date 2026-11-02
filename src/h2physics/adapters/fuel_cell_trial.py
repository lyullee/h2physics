"""Solver-neutral stack exchange for one synchronized fuel-cell trial state.

This module composes existing activity and polarization owners. It is a
callback payload for a future native simultaneous integrator; it does not
integrate compartments, localize events, or close stack/channel energy.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ..core import finite
from ..electrochemistry import (
    FuelCellOperatingState,
    HydrogenStack,
    ReactionEnergy,
    StackResult,
    fuel_cell_activity_correction,
)
from .fuel_cell_activity_receipt import FuelCellFugacityActivityProvider
from .result_provenance import recorded_content_sha256


_ROLES = ("hydrogen", "oxygen", "water_vapor")
_PENDING_EXCHANGE_ISSUERS: set[object] = set()


def _issue_exchange(**values):
    token = object()
    _PENDING_EXCHANGE_ISSUERS.add(token)
    try:
        return FuelCellTrialExchange(**values, _issuer_token=token)
    except Exception:
        _PENDING_EXCHANGE_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class FuelCellTrialGasState:
    """Caller-projected state of one separated native gas control volume.

    The producer supplies the mole fraction and reactive-species inventory
    from its actual trial state. This value type cannot verify native origin.
    """

    role: str
    species_id: str
    time_s: float
    clock_id: str
    pressure_pa: float
    temperature_k: float
    volume_m3: float
    species_mole_fraction: float
    species_moles_mol: float
    species_molar_mass_kg_mol: float
    activity_reference_pressure_pa: float
    activity_reference_id: str
    evidence_id: str
    _seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self.role not in _ROLES:
            raise ValueError("Declare hydrogen, oxygen or water_vapor as the channel role")
        for name in ("species_id", "clock_id", "activity_reference_id", "evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name} for the trial gas state")
        for name in ("time_s", "pressure_pa", "temperature_k", "volume_m3",
                     "species_moles_mol", "species_molar_mass_kg_mol",
                     "activity_reference_pressure_pa"):
            finite(getattr(self, name), name, positive=name != "time_s")
        fraction = finite(self.species_mole_fraction, "species_mole_fraction", positive=True)
        if fraction > 1.0:
            raise ValueError("species_mole_fraction cannot exceed one")
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            self.role, self.species_id, self.time_s, self.clock_id, self.pressure_pa,
            self.temperature_k, self.volume_m3, self.species_mole_fraction,
            self.species_moles_mol, self.species_molar_mass_kg_mol,
            self.activity_reference_pressure_pa, self.activity_reference_id,
            self.evidence_id,
        ))

    def require_current(self):
        if not self._seal or self._content() != self._seal:
            raise ValueError("Fuel-cell trial gas state changed after projection")
        return self

    @property
    def ideal_activity(self) -> float:
        self.require_current()
        return finite(
            self.species_mole_fraction * self.pressure_pa
            / self.activity_reference_pressure_pa,
            "dimensionless ideal-gas activity", positive=True,
        )


@dataclass(frozen=True, slots=True)
class FuelCellSynchronizedTrial:
    """Three separate channel states and one stack command at an exact trial time."""

    time_s: float
    clock_id: str
    stack_temperature_k: float
    current_density_a_m2: float
    channels: Mapping[str, FuelCellTrialGasState]
    evidence_id: str
    _seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        time = finite(self.time_s, "trial time")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Declare the synchronized absolute clock")
        finite(self.stack_temperature_k, "stack_temperature_k", positive=True)
        current = finite(self.current_density_a_m2, "current_density_a_m2")
        if current < 0.0:
            raise ValueError("Current density is a nonnegative magnitude")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare synchronized native-state evidence")
        channels = dict(self.channels)
        if set(channels) != set(_ROLES) or any(type(value) is not FuelCellTrialGasState
                                               for value in channels.values()):
            raise ValueError("Supply separate typed H2, O2 and water-vapor trial states")
        for role, channel in channels.items():
            channel.require_current()
            if role != channel.role or channel.clock_id != self.clock_id or channel.time_s != time:
                raise ValueError("All three native channel projections must share the exact trial time and clock")
        object.__setattr__(self, "channels", MappingProxyType(channels))
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            self.time_s, self.clock_id, self.stack_temperature_k,
            self.current_density_a_m2, self.evidence_id,
            id(self.channels),
            tuple((role, channel, channel._seal) for role, channel in self.channels.items()),
        ))

    def require_current(self):
        for channel in self.channels.values():
            channel.require_current()
        if not self._seal or self._content() != self._seal:
            raise ValueError("Synchronized fuel-cell trial changed after admission")
        return self


@dataclass(frozen=True, slots=True)
class FuelCellTrialExchange:
    """Issued stack result and stoichiometric source terms for one trial only."""

    stack: HydrogenStack = field(repr=False)
    trial: FuelCellSynchronizedTrial
    standard_reaction_energy: ReactionEnergy
    operating_state: FuelCellOperatingState
    corrected_reaction_energy: ReactionEnergy
    stack_result: StackResult
    species_molar_rate_into_cv_mol_s: Mapping[str, float]
    species_mass_rate_into_cv_kg_s: Mapping[str, float]
    net_mass_rate_residual_kg_s: float
    unresolved_energy_rate_w: float
    fugacity_provider: FuelCellFugacityActivityProvider | None = field(default=None, repr=False)
    evidence_id: str = ""
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)
    _stack_signature: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_EXCHANGE_ISSUERS:
            raise ValueError("Use evaluate_fuel_cell_trial_exchange() to issue an exchange")
        _PENDING_EXCHANGE_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        self._validate_projection()
        object.__setattr__(self, "species_molar_rate_into_cv_mol_s",
                           MappingProxyType(dict(self.species_molar_rate_into_cv_mol_s)))
        object.__setattr__(self, "species_mass_rate_into_cv_kg_s",
                           MappingProxyType(dict(self.species_mass_rate_into_cv_kg_s)))
        object.__setattr__(self, "_stack_signature", self._current_stack_signature())
        object.__setattr__(self, "_seal", self._content())

    def _current_stack_signature(self):
        return recorded_content_sha256((
            id(self.stack), self.stack.geometry, self.stack.thermochemistry, self.stack.losses,
        ))

    def _content(self):
        return recorded_content_sha256((
            id(self.stack), id(self.trial), self.standard_reaction_energy,
            self.operating_state, self.corrected_reaction_energy,
            self.stack_result, self.species_molar_rate_into_cv_mol_s,
            self.species_mass_rate_into_cv_kg_s, self.net_mass_rate_residual_kg_s,
            self.unresolved_energy_rate_w, self.fugacity_provider, self.evidence_id,
        ))

    def _validate_projection(self):
        if type(self.stack) is not HydrogenStack or type(self.trial) is not FuelCellSynchronizedTrial:
            raise TypeError("Exchange requires the original HydrogenStack and synchronized trial")
        self.trial.require_current()
        if type(self.standard_reaction_energy) is not ReactionEnergy:
            raise TypeError("Supply the shared standard ReactionEnergy")
        if self.standard_reaction_energy.water_phase != "vapor":
            raise ValueError("The three gas-channel exchange supports vapor product water only")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare exchange and callback-boundary evidence")
        provider = self.fugacity_provider
        if provider is not None:
            if type(provider) is not FuelCellFugacityActivityProvider:
                raise TypeError("Use the existing typed caller-owned fugacity activity provider")
            provider.require_current()
        h2, oxygen, water = (self.trial.channels[role] for role in _ROLES)
        mass_basis_residual = (h2.species_molar_mass_kg_mol
                               + 0.5 * oxygen.species_molar_mass_kg_mol
                               - water.species_molar_mass_kg_mol)
        scale = max(water.species_molar_mass_kg_mol, 1e-30)
        if abs(mass_basis_residual) > 1e-6 * scale:
            raise ValueError("H2/O2/H2O molar-mass basis does not close the reaction stoichiometry")
        expected_operating = _operating_state(self.trial, provider)
        if self.operating_state != expected_operating:
            raise ValueError("Operating-state activities must derive from this exact trial snapshot")
        expected_energy = fuel_cell_activity_correction(self.standard_reaction_energy, expected_operating)
        if self.corrected_reaction_energy != expected_energy:
            raise ValueError("Corrected energy does not reproduce from the shared activity API")
        if (type(self.stack_result) is not StackResult or self.stack_result.mode != "fuel_cell"
                or self.stack_result.reaction_energy != expected_energy):
            raise ValueError("Retain the existing stack result at the activity-corrected trial state")
        h2_rate = finite(self.stack_result.hydrogen_production_mol_s, "H2 production rate")
        if h2_rate > 0.0:
            raise ValueError("Fuel-cell mode cannot produce H2 under the existing negative-output sign")
        expected_molar = {"hydrogen": h2_rate, "oxygen": 0.5 * h2_rate, "water_vapor": -h2_rate}
        expected_mass = {
            role: expected_molar[role] * self.trial.channels[role].species_molar_mass_kg_mol
            for role in _ROLES
        }
        if dict(self.species_molar_rate_into_cv_mol_s) != expected_molar:
            raise ValueError("Species molar source ledger differs from the shared stack extent")
        if dict(self.species_mass_rate_into_cv_kg_s) != expected_mass:
            raise ValueError("Species mass source ledger differs from the admitted molar masses")
        mass_residual = sum(expected_mass.values())
        if abs(self.net_mass_rate_residual_kg_s - mass_residual) > 1e-12 + 1e-9 * sum(abs(x) for x in expected_mass.values()):
            raise ValueError("Reported reaction mass residual is inconsistent")
        if abs(mass_residual) > 1e-12 + 1e-6 * sum(abs(x) for x in expected_mass.values()):
            raise ValueError("H2/O2/H2O reaction source does not conserve mass")
        if self.unresolved_energy_rate_w != self.stack_result.unallocated_energy_rate_w:
            raise ValueError("Unallocated stack energy must remain explicitly unresolved")
        if provider is not None:
            provider.require_current()

    def require_current(self):
        self._validate_projection()
        if (not self._seal or self._content() != self._seal
                or self._current_stack_signature() != self._stack_signature):
            raise ValueError("Fuel-cell trial exchange or its stack configuration changed")
        return self


def _operating_state(trial: FuelCellSynchronizedTrial,
                     provider: FuelCellFugacityActivityProvider | None):
    channels = trial.channels
    activities = {}
    for role, channel in channels.items():
        partial_pressure = finite(
            channel.pressure_pa * channel.species_mole_fraction,
            role + " partial pressure", positive=True,
        )
        if provider is None:
            activities[role] = finite(
                partial_pressure / channel.activity_reference_pressure_pa,
                role + " dimensionless ideal activity", positive=True,
            )
        else:
            activities[role] = provider.relative_activity(
                channel.species_id, partial_pressure,
                channel.activity_reference_pressure_pa, channel.temperature_k,
            )
    if provider is not None:
        provider.require_current()
    return FuelCellOperatingState(
        trial.stack_temperature_k, channels["hydrogen"].pressure_pa,
        channels["oxygen"].pressure_pa, activities["hydrogen"],
        activities["oxygen"], activities["water_vapor"], "vapor",
        channels["hydrogen"].activity_reference_id,
        channels["oxygen"].activity_reference_id,
        channels["water_vapor"].activity_reference_id,
        trial.evidence_id,
    )


def evaluate_fuel_cell_trial_exchange(
    stack: HydrogenStack,
    standard_reaction_energy: ReactionEnergy,
    trial: FuelCellSynchronizedTrial,
    *,
    evidence_id: str,
    fugacity_provider: FuelCellFugacityActivityProvider | None = None,
) -> FuelCellTrialExchange:
    """Project exact-trial activities through the existing shared stack model.

    This returns callback source terms only. A receiving native integrator must
    call it from one synchronized RHS evaluation and own state integration,
    event handling, and accepted-prefix retention.
    """
    if type(stack) is not HydrogenStack or type(trial) is not FuelCellSynchronizedTrial:
        raise TypeError("Supply the original HydrogenStack and a synchronized trial")
    trial.require_current()
    if fugacity_provider is not None:
        if type(fugacity_provider) is not FuelCellFugacityActivityProvider:
            raise TypeError("Use the existing typed caller-owned fugacity activity provider")
        fugacity_provider.require_current()
    stack_signature = recorded_content_sha256((
        id(stack), stack.geometry, stack.thermochemistry, stack.losses,
    ))
    operating_state = _operating_state(trial, fugacity_provider)
    corrected = fuel_cell_activity_correction(standard_reaction_energy, operating_state)
    corrected_stack = HydrogenStack(
        stack.geometry, lambda _temperature: corrected, stack.losses,
    )
    result = corrected_stack.evaluate(
        trial.current_density_a_m2, trial.stack_temperature_k,
        mode="fuel_cell", faradaic_efficiency=1.0,
    )
    if recorded_content_sha256((
            id(stack), stack.geometry, stack.thermochemistry, stack.losses,
    )) != stack_signature:
        raise ValueError("Stack configuration changed during synchronized trial evaluation")
    if fugacity_provider is not None:
        fugacity_provider.require_current()
    h2_rate = result.hydrogen_production_mol_s
    molar = {"hydrogen": h2_rate, "oxygen": 0.5 * h2_rate, "water_vapor": -h2_rate}
    mass = {role: molar[role] * trial.channels[role].species_molar_mass_kg_mol
            for role in _ROLES}
    exchange = _issue_exchange(
        stack=stack, trial=trial, standard_reaction_energy=standard_reaction_energy,
        operating_state=operating_state, corrected_reaction_energy=corrected,
        stack_result=result, species_molar_rate_into_cv_mol_s=molar,
        species_mass_rate_into_cv_kg_s=mass,
        net_mass_rate_residual_kg_s=sum(mass.values()),
        unresolved_energy_rate_w=result.unallocated_energy_rate_w,
        fugacity_provider=fugacity_provider, evidence_id=evidence_id,
    )
    trial.require_current()
    return exchange.require_current()
