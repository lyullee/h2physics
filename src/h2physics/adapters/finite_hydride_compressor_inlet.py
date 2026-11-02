"""Accepted finite-hydride desorption to existing HEOS compressor runs.

The adapter pairs each finite-bed withdrawal interval with one already-issued
steady real-fluid compressor run. It transfers no solver or pressure-flow law;
the finite hydride owns its accepted port history and the compressor owns its
thermodynamic operating point.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

from ..combustion.fuel_compression import HydrogenRealFluidCompressionRun
from ..core import finite
from ..storage.finite_hydride import FiniteHydrideTrace

_PENDING_ISSUERS: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _source_signature(trace):
    digest = hashlib.sha256(repr((
        id(trace), trace.clock_id, trace.termination, id(trace.gas_port_boundary),
        trace.gas_thermodynamics.basis, trace.gas_thermodynamics.source_id,
        tuple((row.time_s, id(row.gas), row.gas.pressure_pa, row.gas.temperature_k,
               row.gas.density_kg_m3, row.gas.enthalpy_j_kg, row.gas.entropy_j_kg_k,
               row.total_hydrogen_mass_kg) for row in trace.snapshots),
    )).encode())
    for value in (trace.time_s, trace.integrated_external_gas_mass_kg,
                  trace.integrated_external_gas_enthalpy_j):
        if value is None:
            digest.update(b"none")
        else:
            array = np.asarray(value)
            digest.update(array.dtype.str.encode())
            digest.update(repr(array.shape).encode())
            digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _coolprop_source(trace, compressor):
    providers = tuple(obj for obj in trace.gas_thermodynamics.native_objects
                     if type(obj).__name__ == "CoolPropProperties"
                     and type(obj).__module__ == "h2physics.thermo.coolprop")
    if len(providers) != 1:
        raise ValueError("Finite-hydride trace must retain exactly one CoolPropProperties source provider")
    provider = providers[0]
    if (provider.backend != "HEOS" or compressor.provider.backend != "HEOS"
            or provider.version != compressor.provider.version):
        raise ValueError("Hydride and mechanical compressor must use the same HEOS release")
    provider.basis.require_compatible(trace.gas_thermodynamics.basis)
    provider.basis.require_compatible(compressor.property_basis)
    provider.basis.require_compatible(compressor.provider.basis)
    return provider


def _project(trace, compressor_runs, *, source_edge_indices,
             process_window_ids, clock_alignment_evidence_ids,
             hydraulic_transfer_evidence_ids, state_projection_evidence_ids,
             absolute_mass_tolerance_kg, relative_mass_tolerance,
             absolute_energy_tolerance_j, relative_energy_tolerance):
    if type(trace) is not FiniteHydrideTrace:
        raise TypeError("Use the original owner-issued FiniteHydrideTrace")
    trace.require_current()
    if trace.gas_port_boundary is None:
        raise ValueError("Finite-hydride trace must retain its accepted gas-port boundary")
    if trace.gas_port_boundary.clock_id != trace.clock_id:
        raise ValueError("Hydride bed and discharge port clocks differ")
    if trace.integrated_external_gas_mass_kg is None or trace.integrated_external_gas_enthalpy_j is None:
        raise ValueError("Trace lacks accepted external-gas mass or enthalpy ledgers")

    times = tuple(float(value) for value in trace.time_s)
    snapshots = tuple(trace.snapshots)
    count = len(times)-1
    if (count < 1 or len(snapshots) != len(times)
            or any(right <= left for left, right in zip(times[:-1], times[1:]))):
        raise ValueError("Hydride discharge needs matching, strictly increasing accepted intervals")
    if any(snapshot.time_s != times[index] for index, snapshot in enumerate(snapshots)):
        raise ValueError("Hydride snapshots differ from the accepted trace clock")
    mass_ledger = np.asarray(trace.integrated_external_gas_mass_kg, dtype=float)
    energy_ledger = np.asarray(trace.integrated_external_gas_enthalpy_j, dtype=float)
    if (mass_ledger.shape != (count+1,) or energy_ledger.shape != (count+1,)
            or not np.all(np.isfinite(mass_ledger)) or not np.all(np.isfinite(energy_ledger))):
        raise ValueError("Hydride external mass and enthalpy ledgers must match accepted clock rows")
    if mass_ledger[0] != 0. or energy_ledger[0] != 0.:
        raise ValueError("Hydride external port ledgers must be zeroed at the accepted window start")
    withdrawals = -np.diff(mass_ledger)
    exported_energy = -np.diff(energy_ledger)
    if np.any(withdrawals <= 0.) or not np.all(np.isfinite(exported_energy)):
        raise ValueError("Every mapped hydride interval must contain positive outward H2 mass")

    runs = tuple(compressor_runs)
    edges = tuple(source_edge_indices)
    windows = tuple(_text(value, "compressor interval identity") for value in process_window_ids)
    clocks = tuple(_text(value, "clock-alignment evidence") for value in clock_alignment_evidence_ids)
    hydraulics = tuple(_text(value, "hydraulic-transfer evidence") for value in hydraulic_transfer_evidence_ids)
    state_evidence = tuple(_text(value, "state-projection evidence") for value in state_projection_evidence_ids)
    if (len(runs) != count or len(edges) != count or len(windows) != count
            or len(clocks) != count or len(hydraulics) != count or len(state_evidence) != count):
        raise ValueError("Provide exactly one compressor run, state edge and evidence set per bed interval")
    if len(set(windows)) != count:
        raise ValueError("Each accepted bed interval needs a unique compressor process-window identity")
    absolute_mass = finite(absolute_mass_tolerance_kg, "absolute H2 mass tolerance", positive=True)
    relative_mass = finite(relative_mass_tolerance, "relative H2 mass tolerance", positive=True)
    absolute_energy = finite(absolute_energy_tolerance_j, "absolute transfer-energy tolerance", positive=True)
    relative_energy = finite(relative_energy_tolerance, "relative transfer-energy tolerance", positive=True)
    if relative_mass > 1e-2 or relative_energy > 1e-2:
        raise ValueError("Relative mass and energy tolerances cannot exceed 1e-2")

    mean_h = []
    mass_residuals = []
    energy_residuals = []
    projected_mass = []
    projected_energy = []
    for index, run in enumerate(runs):
        if type(run) is not HydrogenRealFluidCompressionRun:
            raise TypeError("Each interval requires an owner-issued real-fluid hydrogen compressor run")
        run.require_current()
        _coolprop_source(trace, run)
        if run.inputs.process_window_id != windows[index]:
            raise ValueError("Compressor process-window identity differs from the mapped bed interval")
        if run.inputs.state_evidence_id != state_evidence[index]:
            raise ValueError("Compressor input must retain the exact mapped bed-edge state evidence")
        edge = edges[index]
        if isinstance(edge, bool) or not isinstance(edge, int) or edge not in {index, index+1}:
            raise ValueError("Each compressor inlet must map to the left or right accepted row of its interval")
        source = snapshots[edge].gas
        run.property_basis.require_compatible(source.basis)
        run.inlet.property_basis.require_compatible(source.basis)
        if run.inlet.mass_fraction_h2 != 1.0 or run.inlet.phase not in {
                "gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Mechanical compressor inlet must retain the accepted pure-H2 gas state")
        for actual, expected, abs_tol, rel_tol, label in (
            (run.inlet.pressure_pa, source.pressure_pa, 1e-6, 1e-12, "absolute pressure"),
            (run.inlet.temperature_k, source.temperature_k, 1e-9, 1e-12, "temperature"),
            (run.inlet.density_kg_m3, source.density_kg_m3, 1e-10, 1e-9, "density"),
            (run.inlet.enthalpy_j_kg, source.enthalpy_j_kg, 1e-6, 1e-10, "specific enthalpy"),
            (run.inlet.entropy_j_kg_k, source.entropy_j_kg_k, 1e-7, 1e-9, "specific entropy"),
        ):
            if not math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol):
                raise ValueError(f"Compressor inlet does not retain selected hydride {label}")
        if run.inlet.phase != source.phase:
            raise ValueError("Compressor inlet and selected hydride edge phase differ")

        duration = times[index+1]-times[index]
        mass = finite(run.inputs.hydrogen_mass_flow_kg_s, "compressor H2 mass flow", positive=True)*duration
        mass_residual = mass-withdrawals[index]
        mass_budget = absolute_mass+relative_mass*withdrawals[index]
        if abs(mass_residual) > mass_budget:
            raise ValueError("Compressor interval H2 throughput does not close against bed withdrawal")
        inlet_energy = mass*run.inlet.enthalpy_j_kg
        energy_residual = inlet_energy-exported_energy[index]
        energy_budget = absolute_energy+relative_energy*max(abs(inlet_energy), abs(exported_energy[index]), 1.)
        if abs(energy_residual) > energy_budget:
            raise ValueError("Compressor inlet energy does not close against the accepted bed port ledger")
        projected_mass.append(mass)
        projected_energy.append(inlet_energy)
        mass_residuals.append(mass_residual)
        energy_residuals.append(energy_residual)
        mean_h.append(exported_energy[index]/withdrawals[index])

    signature = _source_signature(trace)
    return (runs, edges, windows, clocks, hydraulics, state_evidence,
            tuple(withdrawals.tolist()), tuple(exported_energy.tolist()), tuple(mean_h),
            tuple(projected_mass), tuple(projected_energy), tuple(mass_residuals),
            tuple(energy_residuals), times, signature, absolute_mass, relative_mass,
            absolute_energy, relative_energy)


@dataclass(frozen=True, slots=True)
class FiniteHydrideCompressorInlet:
    """Interval-by-interval mass/energy coupling from bed outflow to compressor."""

    trace: FiniteHydrideTrace = field(repr=False, compare=False)
    compressor_runs: tuple[HydrogenRealFluidCompressionRun, ...] = field(repr=False, compare=False)
    source_edge_indices: tuple[int, ...]
    process_window_ids: tuple[str, ...]
    clock_alignment_evidence_ids: tuple[str, ...]
    hydraulic_transfer_evidence_ids: tuple[str, ...]
    state_projection_evidence_ids: tuple[str, ...]
    interval_withdrawal_mass_kg: tuple[float, ...]
    interval_exported_enthalpy_j: tuple[float, ...]
    interval_mean_exported_enthalpy_j_kg: tuple[float, ...]
    compressor_interval_mass_kg: tuple[float, ...]
    compressor_interval_inlet_enthalpy_j: tuple[float, ...]
    mass_residual_kg: tuple[float, ...]
    enthalpy_residual_j: tuple[float, ...]
    absolute_mass_tolerance_kg: float
    relative_mass_tolerance: float
    absolute_energy_tolerance_j: float
    relative_energy_tolerance: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise TypeError("Issue this coupling only through bind_finite_hydride_to_compressor")
        _PENDING_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        projected = self._replay()
        if (self.interval_withdrawal_mass_kg != projected[6]
                or self.interval_exported_enthalpy_j != projected[7]
                or self.interval_mean_exported_enthalpy_j_kg != projected[8]
                or self.compressor_interval_mass_kg != projected[9]
                or self.compressor_interval_inlet_enthalpy_j != projected[10]
                or self.mass_residual_kg != projected[11]
                or self.enthalpy_residual_j != projected[12]):
            raise ValueError("Finite-hydride/compressor receipt differs from replayed accepted ledgers")
        object.__setattr__(self, "_seal", self._content(projected[14]))

    def _replay(self):
        return _project(
            self.trace, self.compressor_runs,
            source_edge_indices=self.source_edge_indices,
            process_window_ids=self.process_window_ids,
            clock_alignment_evidence_ids=self.clock_alignment_evidence_ids,
            hydraulic_transfer_evidence_ids=self.hydraulic_transfer_evidence_ids,
            state_projection_evidence_ids=self.state_projection_evidence_ids,
            absolute_mass_tolerance_kg=self.absolute_mass_tolerance_kg,
            relative_mass_tolerance=self.relative_mass_tolerance,
            absolute_energy_tolerance_j=self.absolute_energy_tolerance_j,
            relative_energy_tolerance=self.relative_energy_tolerance,
        )

    def _content(self, signature=None):
        return (
            id(self.trace), tuple(id(run) for run in self.compressor_runs),
            self.source_edge_indices, self.process_window_ids,
            self.clock_alignment_evidence_ids, self.hydraulic_transfer_evidence_ids,
            self.state_projection_evidence_ids, self.interval_withdrawal_mass_kg,
            self.interval_exported_enthalpy_j, self.interval_mean_exported_enthalpy_j_kg,
            self.compressor_interval_mass_kg, self.compressor_interval_inlet_enthalpy_j,
            self.mass_residual_kg, self.enthalpy_residual_j,
            self.absolute_mass_tolerance_kg, self.relative_mass_tolerance,
            self.absolute_energy_tolerance_j, self.relative_energy_tolerance,
            signature,
        )

    def require_current(self):
        replay = self._replay()
        expected = self._content(replay[14])
        if not self._seal or expected != self._seal:
            raise ValueError("Finite-hydride/compressor coupling changed after issuance")
        return self


def bind_finite_hydride_to_compressor(
    trace: FiniteHydrideTrace,
    compressor_runs,
    *,
    source_edge_indices,
    process_window_ids,
    clock_alignment_evidence_ids,
    hydraulic_transfer_evidence_ids,
    state_projection_evidence_ids,
    absolute_mass_tolerance_kg: float,
    relative_mass_tolerance: float,
    absolute_energy_tolerance_j: float,
    relative_energy_tolerance: float,
) -> FiniteHydrideCompressorInlet:
    """Pair each accepted bed outflow bin with its original native compressor run.

    The bed's integrated external H2 mass and enthalpy losses are the source
    ledger. One existing HEOS compressor run per exact bin must use the selected
    accepted bed edge state and matching average mass flow. The caller supplies
    clock, direct-transfer and edge-state mapping evidence. No pressure loss,
    post-bed conditioning, compressor scheduling, or flow dynamics are inferred.
    """
    runs = tuple(compressor_runs)
    edges = tuple(source_edge_indices)
    windows = tuple(process_window_ids)
    clocks = tuple(clock_alignment_evidence_ids)
    hydraulics = tuple(hydraulic_transfer_evidence_ids)
    state_evidence = tuple(state_projection_evidence_ids)
    projected = _project(
        trace, runs, source_edge_indices=edges, process_window_ids=windows,
        clock_alignment_evidence_ids=clocks,
        hydraulic_transfer_evidence_ids=hydraulics,
        state_projection_evidence_ids=state_evidence,
        absolute_mass_tolerance_kg=absolute_mass_tolerance_kg,
        relative_mass_tolerance=relative_mass_tolerance,
        absolute_energy_tolerance_j=absolute_energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance,
    )
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        result = FiniteHydrideCompressorInlet(
            trace, runs, edges, tuple(_text(x, "process window id") for x in windows),
            tuple(_text(x, "clock evidence id") for x in clocks),
            tuple(_text(x, "hydraulic evidence id") for x in hydraulics),
            tuple(_text(x, "state evidence id") for x in state_evidence),
            projected[6], projected[7], projected[8], projected[9], projected[10],
            projected[11], projected[12], projected[15], projected[16],
            projected[17], projected[18], _issuer_token=token,
        )
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
    return result.require_current()


__all__ = ["FiniteHydrideCompressorInlet", "bind_finite_hydride_to_compressor"]
