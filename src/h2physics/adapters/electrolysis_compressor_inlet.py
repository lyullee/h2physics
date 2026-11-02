"""Bind an accepted electrolyzer H2 batch to a caller-declared compressor inlet."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from ..core import ThermoState, finite
from ..combustion.fuel_compression import HydrogenRealFluidCompressionInputs
from .pv_electrolysis import PVElectrolysisTrace

_PENDING: set[object] = set()


@dataclass(frozen=True, slots=True)
class ElectrolysisCompressorInlet:
    producer: PVElectrolysisTrace
    provider: object
    compression_inputs: HydrogenRealFluidCompressionInputs
    provider_id: str
    process_window_id: str
    clock_id: str
    withdrawal_start_s: float
    withdrawal_end_s: float
    transfer_evidence_id: str
    available_hydrogen_mol: float
    withdrawn_hydrogen_kg: float
    _token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Issue this compressor boundary through bind_electrolysis_compressor_inlet")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_token", None)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (id(self.producer), id(self.provider), id(self.compression_inputs),
                tuple((name, getattr(self.compression_inputs, name))
                      for name in self.compression_inputs.__dataclass_fields__),
                getattr(self.provider, "version", None),
                getattr(self.provider, "backend", None),
                getattr(self.provider, "basis", None),
                getattr(self.provider, "internal_energy_policy", None),
                getattr(self.provider, "quality_roundoff_tolerance", None),
                self.provider_id, self.process_window_id, self.clock_id,
                self.withdrawal_start_s, self.withdrawal_end_s,
                self.transfer_evidence_id, self.available_hydrogen_mol,
                self.withdrawn_hydrogen_kg)

    def require_current(self):
        if self._content() != self._seal:
            raise ValueError("Electrolysis/compressor receipt binding changed")
        self.producer.require_current()
        source = self.producer.final.receiver
        if type(source) is not ThermoState:
            raise TypeError("Retain the electrolyzer receiver ThermoState")
        if (self.provider.basis != self.producer.gas.basis
                or self.provider.backend != "HEOS"
                or any(not callable(getattr(self.provider, name, None))
                       for name in ("state_pt", "state_ps", "state_ph"))):
            raise ValueError("Compressor EOS provider no longer matches the producer property basis")
        current = self.provider.state_pt(source.pressure_pa, source.temperature_k)
        if current != source:
            raise ValueError("Compressor EOS inlet state differs from the accepted producer gas state")
        recreated = _make(self.producer, self.provider, self.compression_inputs,
                          self.provider_id, self.process_window_id,
                          self.clock_id, self.withdrawal_start_s,
                          self.withdrawal_end_s, self.transfer_evidence_id)
        if recreated != (self.available_hydrogen_mol, self.withdrawn_hydrogen_kg):
            raise ValueError("Producer inventory, clock or withdrawal ledger changed")
        return self


def _make(producer, provider, inputs, provider_id, process_window_id,
          clock_id, start_s, end_s, evidence_id):
    if type(producer) is not PVElectrolysisTrace:
        raise TypeError("Use the admitted PVElectrolysisTrace")
    if type(inputs) is not HydrogenRealFluidCompressionInputs:
        raise TypeError("Use the existing real-fluid hydrogen compression input contract")
    producer.require_current()
    for name, value in (("provider", provider_id), ("process window", process_window_id),
                        ("clock", clock_id), ("transfer evidence", evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {name} identity is required")
    start = finite(start_s, "compressor withdrawal start")
    end = finite(end_s, "compressor withdrawal end")
    if end <= start or start < producer.final.time_s:
        raise ValueError("Compressor draw must follow completed production on an increasing window")
    if clock_id != producer.evidence.clock_id:
        raise ValueError("Producer and compressor draw must use the same declared physical clock")
    owner = producer.owner
    species = next((item for item in owner.reaction.species
                    if item.identifier == owner.hydrogen_id), None)
    if (species is None or dict(species.elements) != {"H": 2}
            or species.charge != 0 or species.phase not in {"gas", "vapor"}):
        raise ValueError("Producer species is not the declared neutral gaseous H2")
    initial = finite(producer.initial.amounts_mol.get(owner.hydrogen_id, 0.),
                     "initial producer H2 inventory")
    final = finite(producer.final.amounts_mol.get(owner.hydrogen_id, 0.),
                   "final producer H2 inventory")
    produced = final - initial
    if produced <= 0.:
        raise ValueError("The accepted production interval must add a positive H2 batch")
    source = producer.final.receiver
    if inputs.provider_id != provider_id or inputs.process_window_id != process_window_id:
        raise ValueError("Compressor inputs must retain the selected provider and process-window identities")
    if (inputs.inlet_pressure_pa != source.pressure_pa
            or inputs.inlet_temperature_k != source.temperature_k):
        raise ValueError("Compression inlet must use the exact accepted producer P,T state")
    if inputs.state_evidence_id != evidence_id:
        raise ValueError("Compression inlet evidence must identify this source transfer")
    if provider.basis != producer.gas.basis or provider.backend != "HEOS":
        raise ValueError("Only matching HEOS fluid/spin/reference bases can cross this boundary")
    provider_state = provider.state_pt(source.pressure_pa, source.temperature_k)
    if provider_state != source:
        raise ValueError("EOS providers do not reproduce the exact producer inlet state")
    if source.phase not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError("Compression inlet requires an accepted single gas/supercritical H2 state")
    available = produced
    mass = inputs.hydrogen_mass_flow_kg_s * (end - start)
    molar_mass = producer.gas.molar_mass_kg_mol
    withdrawn_mol = mass / molar_mass
    if withdrawn_mol > available + max(1e-12, available * 1e-10):
        raise ValueError("Declared compressor withdrawal exceeds the accepted electrolyzer batch")
    return available, mass


def bind_electrolysis_compressor_inlet(
    producer: PVElectrolysisTrace,
    provider,
    compression_inputs: HydrogenRealFluidCompressionInputs,
    *,
    provider_id: str,
    process_window_id: str,
    clock_id: str,
    withdrawal_start_s: float,
    withdrawal_end_s: float,
    transfer_evidence_id: str,
) -> ElectrolysisCompressorInlet:
    """Issue a finite batch-to-steady-stage inlet handoff.

    This does not model a receiver pressure trajectory, regulator, pipe,
    conditioning, or compressor operation. The caller supplies a constant draw
    over a declared interval; total withdrawn mass may not exceed produced H2.
    """
    available, mass = _make(producer, provider, compression_inputs,
                            provider_id, process_window_id, clock_id,
                            withdrawal_start_s, withdrawal_end_s,
                            transfer_evidence_id)
    token = object()
    _PENDING.add(token)
    try:
        return ElectrolysisCompressorInlet(
            producer, provider, compression_inputs, provider_id,
            process_window_id, clock_id,
            withdrawal_start_s, withdrawal_end_s, transfer_evidence_id,
            available, mass, _token=token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
