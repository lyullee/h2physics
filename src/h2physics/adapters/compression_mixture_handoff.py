"""Bounded handoff from a real-fluid hydrogen compressor to a finite vessel.

This bridge translates one caller-declared constant-flow interval; it does not
model a receiver valve, compressor transient, heat leak, or pressure control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose

from ..combustion.fuel_compression import HydrogenRealFluidCompressionRun
from ..core import finite
from ..thermo.finite_mixture_inventory import (
    MixtureProviderTemplate,
    MixtureVesselAcceptedState,
    MixtureVesselInterval,
)


_PENDING: dict[object, tuple] = {}
def _make_interval(compressor, receiver, template, species_name,
                   start_time_s, end_time_s, evidence_id):
    if type(compressor) is not HydrogenRealFluidCompressionRun:
        raise TypeError("Only an issued real-fluid hydrogen compression run is supported")
    if type(receiver) is not MixtureVesselAcceptedState:
        raise TypeError("An accepted finite-mixture receiver state is required")
    if type(template) is not MixtureProviderTemplate:
        raise TypeError("A finite-mixture receiver needs its exact provider template")
    compressor.require_current()
    receiver.require_current()
    if not isinstance(species_name, str) or not species_name.strip():
        raise ValueError("Select the receiver's hydrogen species by exact declared name")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Declare evidence for the compressor-to-receiver boundary")
    start = finite(start_time_s, "inlet interval start")
    end = finite(end_time_s, "inlet interval end", positive=True)
    if start < receiver.time_s or end <= start:
        raise ValueError("Inlet interval must follow the accepted receiver state")
    if (compressor.provider.backend != "HEOS"
            or compressor.provider.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}):
        raise ValueError("The inlet source must use a direct CoolProp HEOS hydrogen provider")
    if compressor.property_basis.reference_id != template.energy_reference_id:
        raise ValueError("Compressor outlet and receiver must declare the same enthalpy reference")
    if (receiver.provider.backend != "HEOS"
            or receiver.provider.version != compressor.provider.version):
        raise ValueError("Compressor and receiver must use the same CoolProp HEOS release")
    if (tuple(receiver.provider.species) != template.species
            or tuple(receiver.provider.coolprop_fluids) != template.coolprop_fluids
            or tuple(receiver.provider.molar_masses_kg_mol) != template.molar_masses_kg_mol):
        raise ValueError("Receiver point was not issued from the supplied component template")
    if compressor.provider.basis.fluid not in template.coolprop_fluids:
        raise ValueError("Receiver template does not map the compressor's exact hydrogen fluid")
    source_index = template.coolprop_fluids.index(compressor.provider.basis.fluid)
    receiver_index = template.species.index(species_name) if species_name in template.species else -1
    if receiver_index < 0 or receiver_index != source_index:
        raise ValueError("Chosen receiver species does not map to the compressor hydrogen fluid")
    declared_mass = template.molar_masses_kg_mol[receiver_index]
    actual_mass = receiver.provider.coolprop_molar_masses_kg_mol[receiver_index]
    if not isclose(declared_mass, actual_mass,
                   rel_tol=template.molar_mass_relative_tolerance, abs_tol=1e-12):
        raise ValueError("Receiver hydrogen molar mass is inconsistent with its admitted CoolProp fluid")
    outlet = compressor.actual_outlet
    if not isclose(outlet.mass_fraction_h2, 1., rel_tol=0., abs_tol=1e-12):
        raise ValueError("Only a pure-hydrogen compressor outlet can feed this species mapping")
    receiver_pressure = receiver.flash.admission.partition.state.pressure_pa
    if outlet.pressure_pa <= receiver_pressure:
        raise ValueError("Compressor discharge pressure must exceed accepted receiver pressure")
    duration = end - start
    mass = compressor.inputs.hydrogen_mass_flow_kg_s * duration
    moles = mass / declared_mass
    species_moles = tuple(moles if i == receiver_index else 0.
                          for i in range(len(template.species)))
    enthalpy = mass * outlet.enthalpy_j_kg
    interval = MixtureVesselInterval(
        end_time_s=end,
        liquid_inlet_component_moles=(0.,) * len(template.species),
        vapor_inlet_component_moles=species_moles,
        liquid_inlet_enthalpy_j=0., vapor_inlet_enthalpy_j=enthalpy,
        evidence_id=evidence_id,
    )
    return interval, receiver_pressure, duration


@dataclass(frozen=True, slots=True)
class CompressionMixtureHandoff:
    """Owner-sealed compressor stream translation into one vessel interval."""

    compressor: HydrogenRealFluidCompressionRun = field(repr=False, compare=False)
    receiver: MixtureVesselAcceptedState = field(repr=False, compare=False)
    template: MixtureProviderTemplate
    hydrogen_species: str
    start_time_s: float
    end_time_s: float
    evidence_id: str
    interval: MixtureVesselInterval
    receiver_pressure_pa: float
    transferred_mass_kg: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        expected = _PENDING.pop(self._issuer_token, None)
        actual = (id(self.compressor), id(self.receiver), id(self.template),
                  self.hydrogen_species, self.start_time_s, self.end_time_s,
                  self.evidence_id, id(self.interval), self.receiver_pressure_pa,
                  self.transferred_mass_kg)
        if expected is None or expected != actual:
            raise TypeError("Use bind_compression_to_mixture_receiver to issue a handoff")
        object.__setattr__(self, "_issuer_token", None)
        object.__setattr__(self, "_seal", actual)

    def require_current(self):
        self.compressor.require_current()
        self.receiver.require_current()
        interval, pressure, duration = _make_interval(
            self.compressor, self.receiver, self.template, self.hydrogen_species,
            self.start_time_s, self.end_time_s, self.evidence_id)
        mass = self.compressor.inputs.hydrogen_mass_flow_kg_s * duration
        current = (id(self.compressor), id(self.receiver), id(self.template),
                   self.hydrogen_species, self.start_time_s, self.end_time_s,
                   self.evidence_id, id(self.interval), self.receiver_pressure_pa,
                   self.transferred_mass_kg)
        if (current != self._seal or interval != self.interval
                or pressure != self.receiver_pressure_pa or mass != self.transferred_mass_kg):
            raise ValueError("Compressor-to-vessel interval or retained owners changed")
        return self


def bind_compression_to_mixture_receiver(
    compressor: HydrogenRealFluidCompressionRun,
    receiver: MixtureVesselAcceptedState,
    *,
    template: MixtureProviderTemplate,
    hydrogen_species: str,
    start_time_s: float,
    end_time_s: float,
    evidence_id: str,
) -> CompressionMixtureHandoff:
    """Create one constant-flow vapor inlet interval from an accepted compressor.

    The caller supplies the actual interval duration and source-bound evidence.
    This function does not infer valve capacity or integrate a compressor map.
    """
    interval, pressure, duration = _make_interval(
        compressor, receiver, template, hydrogen_species,
        start_time_s, end_time_s, evidence_id)
    mass = compressor.inputs.hydrogen_mass_flow_kg_s * duration
    token = object()
    values = (id(compressor), id(receiver), id(template), hydrogen_species,
              start_time_s, end_time_s, evidence_id, id(interval), pressure, mass)
    _PENDING[token] = values
    try:
        return CompressionMixtureHandoff(
            compressor, receiver, template, hydrogen_species,
            start_time_s, end_time_s, evidence_id, interval, pressure, mass,
            _issuer_token=token)
    except Exception:
        _PENDING.pop(token, None)
        raise


__all__ = ["CompressionMixtureHandoff", "bind_compression_to_mixture_receiver"]
