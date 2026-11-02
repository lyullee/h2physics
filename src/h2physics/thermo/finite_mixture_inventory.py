"""Accepted-step finite-volume marching for a fixed-volume VLE mixture vessel.

The module composes CoolProp's native mixture phase packets and the shared
bounded V/U flash. It advances user-supplied finite intervals, not a continuous
rate law: each outlet is evaluated on the left-end accepted phase state and the
updated composition/U are flashed before the next interval. This explicit
first-order scheme is intentionally narrow; callers own temporal refinement.
"""

from dataclasses import dataclass, field
from math import fsum, isclose
from typing import Callable

from ..core import finite
from ..mixtures import GasComposition
from .coolprop_mixture import CoolPropMixtureProperties
from .mixture_inventory_flash import flash_two_phase_inventory_vu
from .mixture_phase_partition import MixtureInventoryStateAdmission


@dataclass(frozen=True, slots=True)
class MixtureProviderTemplate:
    """Immutable component/backend settings used to issue a provider per stock.

    CoolProp's provider captures one overall composition. A new provider is
    therefore constructed for every accepted component inventory. The caller
    supplies the component order and molar masses once; no species are inferred.
    """

    species: tuple[str, ...]
    molar_masses_kg_mol: tuple[float, ...]
    coolprop_fluids: tuple[str, ...]
    energy_reference_id: str
    inverse_temperature_bounds_k: tuple[float, float] | None = None
    molar_mass_relative_tolerance: float = 1e-4

    def __post_init__(self):
        species = tuple(self.species)
        masses = tuple(finite(v, "component molar mass", positive=True)
                       for v in self.molar_masses_kg_mol)
        fluids = tuple(self.coolprop_fluids)
        if (len(species) < 2 or len(set(species)) != len(species)
                or any(not isinstance(s, str) or not s.strip() for s in species)):
            raise ValueError("Declare at least two unique named mixture species")
        if len(masses) != len(species) or len(fluids) != len(species):
            raise ValueError("Species, molar masses and CoolProp fluid names must have equal lengths")
        if any(not isinstance(v, str) or not v.strip() for v in fluids) or len(set(fluids)) != len(fluids):
            raise ValueError("CoolProp fluid names must be nonblank and unique")
        if not isinstance(self.energy_reference_id, str) or not self.energy_reference_id.strip():
            raise ValueError("Declare one energy-reference identity for all evolving compositions")
        bounds = self.inverse_temperature_bounds_k
        if bounds is not None:
            bounds = tuple(finite(v, "inverse temperature bound", positive=True) for v in bounds)
            if len(bounds) != 2 or bounds[0] >= bounds[1]:
                raise ValueError("Inverse temperature bounds must increase")
        tolerance = finite(self.molar_mass_relative_tolerance,
                           "molar-mass relative tolerance", positive=True)
        if tolerance > 1e-3:
            raise ValueError("Molar-mass tolerance cannot exceed 1e-3")
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "molar_masses_kg_mol", masses)
        object.__setattr__(self, "coolprop_fluids", fluids)
        object.__setattr__(self, "inverse_temperature_bounds_k", bounds)
        object.__setattr__(self, "molar_mass_relative_tolerance", tolerance)

    def provider_for(self, component_moles):
        moles = _mole_vector(component_moles, len(self.species), "component inventory")
        total = fsum(moles)
        if total <= 0.:
            raise ValueError("Mixture inventory must retain positive total moles")
        composition = GasComposition(
            "finite-vessel:" + ":".join(float(n / total).hex() for n in moles),
            self.species, tuple(n / total for n in moles), self.molar_masses_kg_mol,
        )
        mapping = dict(zip(self.species, self.coolprop_fluids, strict=True))
        return CoolPropMixtureProperties(
            composition, fluid_names=mapping,
            molar_mass_relative_tolerance=self.molar_mass_relative_tolerance,
            inverse_temperature_bounds_k=self.inverse_temperature_bounds_k,
        )


def _mole_vector(values, size, label):
    result = tuple(finite(v, label) for v in values)
    if len(result) != size or any(v < 0. for v in result):
        raise ValueError(f"{label} must be a nonnegative species-ordered vector")
    return result


@dataclass(frozen=True, slots=True)
class MixtureVesselInterval:
    """Finite transfers over one caller-chosen interval.

    Inlet component moles and their integrated enthalpy are supplied by the
    caller. Outlets are phase-selective total moles withdrawn from the *current
    left-end accepted phase*, whose native composition and enthalpy determine
    both species removal and exported energy. Heat/work are signed energy into
    the vessel in J. No rates or interpolated control schedule are inferred.
    """

    end_time_s: float
    liquid_inlet_component_moles: tuple[float, ...]
    vapor_inlet_component_moles: tuple[float, ...]
    liquid_inlet_enthalpy_j: float
    vapor_inlet_enthalpy_j: float
    liquid_outlet_total_moles: float = 0.
    vapor_outlet_total_moles: float = 0.
    heat_into_vessel_j: float = 0.
    work_into_vessel_j: float = 0.
    evidence_id: str = ""

    def __post_init__(self):
        object.__setattr__(self, "end_time_s", finite(self.end_time_s, "interval end time", positive=True))
        for name in ("liquid_inlet_component_moles", "vapor_inlet_component_moles"):
            values = tuple(finite(v, name) for v in getattr(self, name))
            if any(v < 0. for v in values):
                raise ValueError(f"{name} cannot contain negative transfers")
            object.__setattr__(self, name, values)
        for vector_name, energy_name in (
            ("liquid_inlet_component_moles", "liquid_inlet_enthalpy_j"),
            ("vapor_inlet_component_moles", "vapor_inlet_enthalpy_j"),
        ):
            if not any(getattr(self, vector_name)) and getattr(self, energy_name) != 0.:
                raise ValueError("A zero-mole inlet cannot carry a nonzero stream enthalpy transfer")
        for name in ("liquid_outlet_total_moles", "vapor_outlet_total_moles"):
            object.__setattr__(self, name, finite(getattr(self, name), name))
            if getattr(self, name) < 0.:
                raise ValueError("Outlet phase moles cannot be negative")
        for name in ("liquid_inlet_enthalpy_j", "vapor_inlet_enthalpy_j",
                     "heat_into_vessel_j", "work_into_vessel_j"):
            object.__setattr__(self, name, finite(getattr(self, name), name))
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Each finite interval needs a boundary/evidence identity")


@dataclass(frozen=True, slots=True)
class MixtureVesselAcceptedState:
    """One accepted finite-volume state, equilibrium flash and cumulative ledgers."""

    time_s: float
    provider: CoolPropMixtureProperties = field(repr=False, compare=False)
    flash: object = field(repr=False, compare=False)
    admission: MixtureInventoryStateAdmission = field(repr=False, compare=False)
    cumulative_inlet_component_moles: tuple[float, ...]
    cumulative_outlet_component_moles: tuple[float, ...]
    cumulative_energy_into_vessel_j: float
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if (type(self.provider) is not CoolPropMixtureProperties
                or type(self.admission) is not MixtureInventoryStateAdmission
                or self.admission.provider is not self.provider
                or self.flash.provider is not self.provider):
            raise TypeError("Accepted state must retain its exact composition provider and V/U flash")
        self.require_current(check_seal=False)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (self.time_s, id(self.provider), self.provider.composition_sha256,
                id(self.flash), self.flash._payload(), id(self.admission), self.admission._payload(),
                self.cumulative_inlet_component_moles,
                self.cumulative_outlet_component_moles,
                self.cumulative_energy_into_vessel_j)

    def require_current(self, *, check_seal=True):
        if check_seal and (not self._seal or self._payload() != self._seal):
            raise ValueError("Accepted mixture vessel state changed after issuance")
        self.flash.require_current()
        self.admission.require_current()
        finite(self.time_s, "accepted time")
        n = len(self.provider.species)
        inlet = _mole_vector(self.cumulative_inlet_component_moles, n, "cumulative inlet moles")
        outlet = _mole_vector(self.cumulative_outlet_component_moles, n, "cumulative outlet moles")
        if inlet != self.cumulative_inlet_component_moles or outlet != self.cumulative_outlet_component_moles:
            raise ValueError("Accepted cumulative ledgers changed")
        finite(self.cumulative_energy_into_vessel_j, "cumulative net energy")
        return self


@dataclass(frozen=True, slots=True)
class FiniteMixtureVesselRun:
    """Immutable owner-issued accepted trajectory and independent balance audit."""

    run_id: str
    template: MixtureProviderTemplate
    vessel_volume_m3: float
    energy_reference_id: str
    accepted: tuple[MixtureVesselAcceptedState, ...]
    intervals: tuple[MixtureVesselInterval, ...]
    component_mole_absolute_tolerance: float
    energy_absolute_tolerance_j: float
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise ValueError("Declare a run identity")
        if self.energy_reference_id != self.template.energy_reference_id:
            raise ValueError("Run and provider template energy references differ")
        volume = finite(self.vessel_volume_m3, "fixed vessel volume", positive=True)
        accepted, intervals = tuple(self.accepted), tuple(self.intervals)
        if len(accepted) != len(intervals) + 1 or len(accepted) < 2:
            raise ValueError("Retain initial state and exactly one new accepted state per interval")
        if len(intervals) and accepted[0].time_s != 0.:
            raise ValueError("Initial accepted state must be at time zero")
        object.__setattr__(self, "vessel_volume_m3", volume)
        object.__setattr__(self, "accepted", accepted)
        object.__setattr__(self, "intervals", intervals)
        object.__setattr__(self, "component_mole_absolute_tolerance",
                           finite(self.component_mole_absolute_tolerance, "mole closure tolerance", positive=True))
        object.__setattr__(self, "energy_absolute_tolerance_j",
                           finite(self.energy_absolute_tolerance_j, "energy closure tolerance", positive=True))
        self._audit()
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        interval_values = tuple((item.end_time_s, item.liquid_inlet_component_moles,
            item.vapor_inlet_component_moles, item.liquid_inlet_enthalpy_j,
            item.vapor_inlet_enthalpy_j, item.liquid_outlet_total_moles,
            item.vapor_outlet_total_moles, item.heat_into_vessel_j,
            item.work_into_vessel_j, item.evidence_id) for item in self.intervals)
        return (self.run_id, id(self.template), self.vessel_volume_m3,
                self.energy_reference_id, tuple(id(item) for item in self.accepted),
                tuple(item._payload() for item in self.accepted), interval_values,
                self.component_mole_absolute_tolerance, self.energy_absolute_tolerance_j)

    def _audit(self):
        first = self.accepted[0]
        first.require_current()
        if tuple(first.provider.species) != self.template.species:
            raise ValueError("Initial provider changed the declared species order")
        if _thermo_reference_signature(first.provider)[0] != "HEOS":
            raise ValueError("The finite mixture run currently requires the declared HEOS backend")
        if any(not isclose(observed, declared, rel_tol=self.template.molar_mass_relative_tolerance,
                           abs_tol=1e-12)
               for observed, declared in zip(first.provider.coolprop_molar_masses_kg_mol,
                                              self.template.molar_masses_kg_mol, strict=True)):
            raise ValueError("Initial provider molar masses differ from the declared template")
        if first.time_s != 0.:
            raise ValueError("Accepted history needs an exact zero-time initial state")
        n = len(self.template.species)
        if (first.cumulative_inlet_component_moles != (0.,)*n
                or first.cumulative_outlet_component_moles != (0.,)*n
                or first.cumulative_energy_into_vessel_j != 0.):
            raise ValueError("Initial cumulative transfer ledgers must be zero")
        prior = first
        reference_signature = _thermo_reference_signature(first.provider)
        for index, (point, interval) in enumerate(zip(self.accepted[1:], self.intervals, strict=True)):
            prior.require_current()
            point.require_current()
            if point.time_s != interval.end_time_s or point.time_s <= prior.time_s:
                raise ValueError("Accepted times must strictly follow their matching intervals")
            if point.admission.vessel_volume_m3 != self.vessel_volume_m3:
                raise ValueError("Fixed vessel volume changed in accepted history")
            if tuple(point.provider.species) != self.template.species:
                raise ValueError("Accepted provider changed species order")
            if any(not isclose(observed, declared,
                               rel_tol=self.template.molar_mass_relative_tolerance,
                               abs_tol=1e-12)
                   for observed, declared in zip(point.provider.coolprop_molar_masses_kg_mol,
                                                  self.template.molar_masses_kg_mol, strict=True)):
                raise ValueError("Accepted provider changed molar masses")
            if _thermo_reference_signature(point.provider) != reference_signature:
                raise ValueError("CoolProp version, backend, or hydrogen spin basis changed across accepted states")
            expected_n = tuple(a + b + c - d for a, b, c, d in zip(
                prior.admission.total_component_moles,
                interval.liquid_inlet_component_moles,
                interval.vapor_inlet_component_moles,
                _outlet_moles(prior.flash, interval, self.template), strict=True))
            for observed, expected in zip(point.admission.total_component_moles, expected_n, strict=True):
                if abs(observed - expected) > self.component_mole_absolute_tolerance:
                    raise ValueError("Accepted component inventory fails its interval transfer ledger")
            out = _outlet_energy(prior.flash, interval, self.template)
            ein = fsum((interval.liquid_inlet_enthalpy_j, interval.vapor_inlet_enthalpy_j,
                        interval.heat_into_vessel_j, interval.work_into_vessel_j))
            expected_u = prior.admission.target_internal_energy_j + ein - out
            if abs(point.admission.target_internal_energy_j - expected_u) > self.energy_absolute_tolerance_j:
                raise ValueError("Accepted internal energy fails its interval boundary ledger")
            if point.cumulative_inlet_component_moles != tuple(a+b+c for a,b,c in zip(
                    prior.cumulative_inlet_component_moles,
                    interval.liquid_inlet_component_moles,
                    interval.vapor_inlet_component_moles, strict=True)):
                raise ValueError("Cumulative inlet ledger does not reproduce interval increments")
            if point.cumulative_outlet_component_moles != tuple(a+b for a,b in zip(
                    prior.cumulative_outlet_component_moles,
                    _outlet_moles(prior.flash, interval, self.template), strict=True)):
                raise ValueError("Cumulative outlet ledger does not reproduce phase withdrawals")
            if abs(point.cumulative_energy_into_vessel_j - (prior.cumulative_energy_into_vessel_j + ein - out)) > self.energy_absolute_tolerance_j:
                raise ValueError("Cumulative energy ledger does not reproduce interval transfer")
            prior = point

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Finite-mixture accepted trajectory changed after issuance")
        self._audit()
        return self


def _outlet_moles(flash, interval, template):
    packet = flash.partition
    amounts = flash.phase_amounts
    result = [0.] * len(template.species)
    for phase, requested, stock, composition in (
        ("liquid", interval.liquid_outlet_total_moles,
         fsum(amounts.liquid_component_moles), packet.liquid_mole_fractions),
        ("vapor", interval.vapor_outlet_total_moles,
         fsum(amounts.vapor_component_moles), packet.vapor_mole_fractions),
    ):
        if requested > stock + 1e-12 * max(stock, 1.):
            raise ValueError(f"{phase} outlet withdraws more moles than the current phase inventory")
        if requested and not any(composition):
            raise ValueError(f"{phase} outlet requests a phase with no native composition")
        for i, fraction in enumerate(composition):
            result[i] += requested * fraction
    return tuple(result)


def _outlet_energy(flash, interval, template):
    packet = flash.partition
    masses_per_mole = tuple(template.molar_masses_kg_mol)
    energy = 0.
    for requested, composition, enthalpy, label in (
        (interval.liquid_outlet_total_moles, packet.liquid_mole_fractions,
         packet.liquid_enthalpy_j_kg, "liquid"),
        (interval.vapor_outlet_total_moles, packet.vapor_mole_fractions,
         packet.vapor_enthalpy_j_kg, "vapor"),
    ):
        if requested == 0.:
            continue
        if enthalpy is None:
            raise ValueError(f"Occupied {label} outlet needs native phase enthalpy")
        mass = fsum(requested * y * mw for y, mw in zip(composition, masses_per_mole, strict=True))
        energy += mass * enthalpy
    return finite(energy, "phase-selective outlet enthalpy")


def _thermo_reference_signature(provider):
    """Identity fields that must stay fixed while composition fingerprints vary."""
    basis = provider.basis
    prefix = basis.reference_id.rsplit(":", 1)[0]
    return (provider.backend, provider.version, prefix, basis.spin_composition)


def run_finite_mixture_vu_intervals(
    template: MixtureProviderTemplate,
    initial_component_moles,
    *,
    initial_internal_energy_j: float,
    vessel_volume_m3: float,
    intervals,
    pressure_bounds_pa,
    quality_bounds,
    initial_guesses,
    volume_absolute_tolerance_m3: float,
    energy_absolute_tolerance_j: float,
    component_mole_absolute_tolerance: float,
    phase_mole_balance_tolerance: float,
    branch_evidence_id: str,
    run_id: str,
    root_pressure_relative_tolerance: float = 1e-7,
    root_quality_absolute_tolerance: float = 1e-8,
):
    """Advance caller-supplied finite intervals with phase-selective outlets.

    This explicit accepted-step algorithm performs a native CoolProp two-phase
    V/U flash at the initial state and after every interval. Outlet composition
    and enthalpy are sampled from the preceding accepted equilibrium packet;
    interval refinement is therefore required for rapidly varying trajectories.
    Any flash, domain or closure failure aborts with no fabricated later rows.
    Only a bounded two-phase branch is supported; phase events and wall states
    are outside this first executable level.
    """
    if type(template) is not MixtureProviderTemplate:
        raise TypeError("Supply a MixtureProviderTemplate")
    intervals = tuple(intervals)
    if not intervals or any(type(item) is not MixtureVesselInterval for item in intervals):
        raise ValueError("Supply at least one typed finite interval")
    moles = _mole_vector(initial_component_moles, len(template.species), "initial component moles")
    volume = finite(vessel_volume_m3, "fixed vessel volume", positive=True)
    energy = finite(initial_internal_energy_j, "initial internal energy")
    p_bounds = tuple(pressure_bounds_pa)
    q_bounds = tuple(quality_bounds)
    guesses = tuple(tuple(g) for g in initial_guesses)
    flash_kw = dict(
        vessel_volume_m3=volume, pressure_bounds_pa=p_bounds, quality_bounds=q_bounds,
        initial_guesses=guesses,
        volume_absolute_tolerance_m3=volume_absolute_tolerance_m3,
        energy_absolute_tolerance_j=energy_absolute_tolerance_j,
        component_mole_absolute_tolerance=component_mole_absolute_tolerance,
        phase_mole_balance_tolerance=phase_mole_balance_tolerance,
        branch_evidence_id=branch_evidence_id,
        root_pressure_relative_tolerance=root_pressure_relative_tolerance,
        root_quality_absolute_tolerance=root_quality_absolute_tolerance,
    )

    def accept(time_s, stocks, target_u, cumulative_in, cumulative_out, cumulative_e):
        provider = template.provider_for(stocks)
        flash = flash_two_phase_inventory_vu(provider, stocks,
            internal_energy_j=target_u, **flash_kw)
        admission = flash.admission
        point = MixtureVesselAcceptedState(
            time_s, provider, flash, admission, tuple(cumulative_in),
            tuple(cumulative_out), cumulative_e)
        return point

    zero = (0.,) * len(template.species)
    accepted = [accept(0., moles, energy, zero, zero, 0.)]
    cumulative_in, cumulative_out, cumulative_energy = zero, zero, 0.
    previous = accepted[0]
    for interval in intervals:
        if interval.end_time_s <= previous.time_s:
            raise ValueError("Finite interval endpoints must be strictly increasing")
        if (len(interval.liquid_inlet_component_moles) != len(template.species)
                or len(interval.vapor_inlet_component_moles) != len(template.species)):
            raise ValueError("Each inlet composition must follow the declared species order")
        removed = _outlet_moles(previous.flash, interval, template)
        new_moles = tuple(a+b+c-d for a,b,c,d in zip(
            previous.admission.total_component_moles,
            interval.liquid_inlet_component_moles,
            interval.vapor_inlet_component_moles, removed, strict=True))
        if any(v <= 0. for v in new_moles):
            raise ValueError("Each declared mixture component must remain strictly positive")
        outlet_energy = _outlet_energy(previous.flash, interval, template)
        net_energy = fsum((interval.liquid_inlet_enthalpy_j,
                           interval.vapor_inlet_enthalpy_j,
                           interval.heat_into_vessel_j,
                           interval.work_into_vessel_j, -outlet_energy))
        new_energy = previous.admission.target_internal_energy_j + net_energy
        cumulative_in = tuple(a+b+c for a,b,c in zip(
            cumulative_in, interval.liquid_inlet_component_moles,
            interval.vapor_inlet_component_moles, strict=True))
        cumulative_out = tuple(a+b for a,b in zip(cumulative_out, removed, strict=True))
        cumulative_energy = fsum((cumulative_energy, net_energy))
        point = accept(interval.end_time_s, new_moles, new_energy,
                       cumulative_in, cumulative_out, cumulative_energy)
        accepted.append(point)
        previous = point
    return FiniteMixtureVesselRun(
        run_id, template, volume, template.energy_reference_id,
        tuple(accepted), intervals, component_mole_absolute_tolerance,
        energy_absolute_tolerance_j)


__all__ = ["FiniteMixtureVesselRun", "MixtureProviderTemplate",
           "MixtureVesselAcceptedState", "MixtureVesselInterval",
           "run_finite_mixture_vu_intervals"]
