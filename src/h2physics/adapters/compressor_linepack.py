"""One-step HEOS compressor discharge to an existing isothermal H2 linepack.

This adapter reuses the existing compressor result and lumped linepack advance.
It explicitly accounts for the heat needed to map the real-fluid discharge to
the linepack's fixed-temperature state; no compressor, valve, line or thermal
conditioning solver is introduced.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..combustion.fuel_compression import HydrogenRealFluidCompressionRun
from ..core import ThermoState, finite
from ..pipeline_linepack import IsothermalLinepackState, LinepackStepLedger
from ..real_gas_linepack import RealGasLinepackState, RealGasLinepackStepLedger
from ..thermo.isothermal_eos import CoolPropIsothermalEOS

_H2_MOLAR_MASS_KG_MOL = 0.00201588
_PENDING_ISSUERS: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _same_state(actual, expected, *, label):
    if type(actual) is not ThermoState or type(expected) is not ThermoState:
        raise TypeError(f"{label} must retain original CoolProp ThermoState objects")
    expected.basis.require_compatible(actual.basis)
    if (actual.phase != expected.phase
            or actual.vapor_mass_fraction not in (None, 1.)
            or expected.vapor_mass_fraction not in (None, 1.)):
        raise ValueError(f"{label} must be single-phase hydrogen gas")
    for value, reference, abs_tol, rel_tol, prop in (
        (actual.pressure_pa, expected.pressure_pa, 1e-6, 1e-12, "absolute pressure"),
        (actual.temperature_k, expected.temperature_k, 1e-9, 1e-12, "temperature"),
        (actual.density_kg_m3, expected.density_kg_m3, 1e-10, 1e-9, "density"),
        (actual.enthalpy_j_kg, expected.enthalpy_j_kg, 1e-6, 1e-10, "specific enthalpy"),
        (actual.internal_energy_j_kg, expected.internal_energy_j_kg, 1e-6, 1e-10,
         "specific internal energy"),
        (actual.entropy_j_kg_k, expected.entropy_j_kg_k, 1e-8, 1e-9, "specific entropy"),
    ):
        if not math.isclose(value, reference, rel_tol=rel_tol, abs_tol=abs_tol):
            raise ValueError(f"{label} does not close against CoolProp {prop}")


def _native_definitions(initial, compressor):
    properties = compressor.provider
    definition = (id(properties), properties.basis, properties.backend,
                  properties.version, id(properties._state), id(properties._cp),
                  properties.state_pt, properties.internal_energy_policy,
                  properties.quality_roundoff_tolerance)
    if type(initial) is RealGasLinepackState:
        eos = initial.eos
        definition += (id(eos), eos.identity, eos.fluid, eos.backend, eos.version,
                       id(eos._state), id(eos._cp), eos.density_pt,
                       eos.pressure_rho_t, eos.isothermal_sound_speed_rho_t)
    return definition


def _project(initial, compressor, conditioned_inlet_state, *, duration_s,
             minimum_mass_kg, start_time_s, time_mapping_evidence_id,
             hydrogen_basis_evidence_id, transfer_boundary_evidence_id,
             thermal_conditioning_evidence_id, thermal_conditioning_energy_j,
             absolute_energy_tolerance_j, relative_energy_tolerance):
    if type(initial) not in {IsothermalLinepackState, RealGasLinepackState}:
        raise TypeError("Supply an original isothermal or real-gas linepack state")
    if type(compressor) is not HydrogenRealFluidCompressionRun:
        raise TypeError("Supply an owner-issued CoolProp real-fluid hydrogen compressor result")
    if type(conditioned_inlet_state) is not ThermoState:
        raise TypeError("Supply the native CoolProp state projected to linepack conditions")
    compressor.require_current()
    if (compressor.provider.backend != "HEOS"
            or compressor.provider.basis.fluid not in {"Hydrogen", "ParaHydrogen"}
            or not math.isclose(compressor.actual_outlet.mass_fraction_h2, 1.,
                                rel_tol=0., abs_tol=1e-12)):
        raise ValueError("Only a direct pure-H2 HEOS compressor discharge is admitted")
    if type(initial) is RealGasLinepackState:
        eos = initial.eos
        if (type(eos) is not CoolPropIsothermalEOS or eos.backend != "HEOS"
                or eos.fluid != compressor.provider.basis.fluid
                or eos.version != compressor.provider.version
                or eos.identity != initial.eos_identity):
            raise ValueError("Linepack and compressor require matched native HEOS hydrogen providers and spin")
        expected_spin = {"Hydrogen": "normal", "ParaHydrogen": "para"}[eos.fluid]
        if compressor.provider.basis.spin_composition != expected_spin:
            raise ValueError("Native linepack and compressor spin bases differ")
    elif not math.isclose(initial.molecular_mass_kg_mol, _H2_MOLAR_MASS_KG_MOL,
                          rel_tol=1e-8, abs_tol=0.):
        raise ValueError("The analytic linepack molecular-mass basis must be pure hydrogen")
    compressor.property_basis.require_compatible(compressor.provider.basis)

    duration = finite(duration_s, "compressor transfer duration", positive=True)
    floor = finite(minimum_mass_kg, "linepack minimum mass")
    if floor < 0.:
        raise ValueError("Linepack minimum mass must be nonnegative")
    start = finite(start_time_s, "compressor transfer start time")
    if start != initial.time_s:
        raise ValueError("Transfer interval must begin at the linepack state's exact clock time")
    end = start+duration
    time_id = _text(time_mapping_evidence_id, "compressor process-window to linepack clock mapping")
    basis_id = _text(hydrogen_basis_evidence_id, "pure-H2 basis evidence")
    transfer_id = _text(transfer_boundary_evidence_id, "compressor-to-linepack hydraulic transfer evidence")
    thermal_id = _text(thermal_conditioning_evidence_id, "isothermal conditioning evidence")
    absolute = finite(absolute_energy_tolerance_j, "absolute conditioning-energy tolerance", positive=True)
    relative = finite(relative_energy_tolerance, "relative conditioning-energy tolerance", positive=True)
    if relative > 1e-2:
        raise ValueError("Relative energy tolerance cannot exceed 1e-2")

    rate = finite(compressor.inputs.hydrogen_mass_flow_kg_s,
                  "compressor hydrogen mass flow", positive=True)
    mass = rate*duration
    final, ledger = initial.advance(
        duration_s=duration, inlet_mass_flow_kg_s=rate,
        outlet_mass_flow_kg_s=0., minimum_mass_kg=floor,
    )
    if compressor.actual_outlet.pressure_pa <= final.pressure_pa:
        raise ValueError("Compressor discharge must exceed the final linepack pressure")

    properties = compressor.provider
    properties.basis.require_compatible(conditioned_inlet_state.basis)
    source_state = properties.state_pt(
        compressor.actual_outlet.pressure_pa,
        compressor.actual_outlet.temperature_k,
    )
    mapped_state = properties.state_pt(final.pressure_pa, initial.temperature_k)
    if type(initial) is RealGasLinepackState:
        for endpoint in (initial, final):
            endpoint_state = properties.state_pt(endpoint.pressure_pa, endpoint.temperature_k)
            if not math.isclose(endpoint_state.density_kg_m3, endpoint.density_kg_m3,
                                rel_tol=1e-8, abs_tol=1e-10):
                raise ValueError("Linepack EOS density differs from the compressor's native property basis")
    _same_state(source_state, properties.state_pt(
        compressor.actual_outlet.pressure_pa,
        compressor.actual_outlet.temperature_k,
    ), label="Reconstructed compressor outlet")
    if (not math.isclose(source_state.pressure_pa,
                         compressor.actual_outlet.pressure_pa,
                         rel_tol=1e-12, abs_tol=1e-6)
            or not math.isclose(source_state.temperature_k,
                                compressor.actual_outlet.temperature_k,
                                rel_tol=1e-12, abs_tol=1e-9)):
        raise ValueError("CoolProp discharge reconstruction changed compressor outlet P/T")
    _same_state(conditioned_inlet_state, mapped_state,
                label="Isothermal linepack inlet projection")
    if (not math.isclose(source_state.enthalpy_j_kg,
                         compressor.actual_outlet.enthalpy_j_kg,
                         rel_tol=1e-10, abs_tol=1e-6)
            or not math.isclose(source_state.density_kg_m3,
                                compressor.actual_outlet.density_kg_m3,
                                rel_tol=1e-9, abs_tol=1e-10)):
        raise ValueError("CoolProp reconstruction differs from the issued compressor outlet")
    expected_heat = mass*(conditioned_inlet_state.enthalpy_j_kg-source_state.enthalpy_j_kg)
    supplied_heat = finite(thermal_conditioning_energy_j,
                           "signed thermal-conditioning energy")
    energy_residual = supplied_heat-expected_heat
    budget = absolute+relative*max(abs(supplied_heat), abs(expected_heat), 1.)
    if abs(energy_residual) > budget:
        raise ValueError("Caller heat ledger does not condition compressor product to linepack fixed temperature")
    if not math.isclose(ledger.inlet_mass_kg, mass, rel_tol=1e-12, abs_tol=1e-15):
        raise ArithmeticError("Linepack charge mass differs from the compressor's accepted interval")
    return (final, ledger, source_state, mapped_state, duration, start, end,
            rate, mass, expected_heat, supplied_heat, energy_residual,
            time_id, basis_id, transfer_id, thermal_id, absolute, relative,
            floor)


@dataclass(frozen=True, slots=True)
class CompressorLinepackCharge:
    """Sealed one-interval compressor-to-linepack mass and conditioning-energy receipt."""

    initial: IsothermalLinepackState | RealGasLinepackState
    compressor: HydrogenRealFluidCompressionRun = field(repr=False, compare=False)
    conditioned_inlet_state: ThermoState = field(repr=False, compare=False)
    final: IsothermalLinepackState | RealGasLinepackState
    ledger: LinepackStepLedger | RealGasLinepackStepLedger
    source_outlet_state: ThermoState = field(repr=False, compare=False)
    duration_s: float
    minimum_mass_kg: float
    start_time_s: float
    end_time_s: float
    mass_flow_kg_s: float
    transferred_mass_kg: float
    required_conditioning_energy_j: float
    supplied_conditioning_energy_j: float
    conditioning_energy_residual_j: float
    time_mapping_evidence_id: str
    hydrogen_basis_evidence_id: str
    transfer_boundary_evidence_id: str
    thermal_conditioning_evidence_id: str
    absolute_energy_tolerance_j: float
    relative_energy_tolerance: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise TypeError("Issue linepack charge receipts through charge_linepack_from_compressor")
        _PENDING_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        projected = self._replay()
        self._require_equal(projected)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (id(self.initial), id(self.compressor), id(self.conditioned_inlet_state),
                id(self.final), id(self.ledger), id(self.source_outlet_state),
                self.duration_s, self.minimum_mass_kg, self.start_time_s, self.end_time_s,
                self.mass_flow_kg_s, self.transferred_mass_kg,
                self.required_conditioning_energy_j, self.supplied_conditioning_energy_j,
                self.conditioning_energy_residual_j, self.time_mapping_evidence_id,
                self.hydrogen_basis_evidence_id, self.transfer_boundary_evidence_id,
                self.thermal_conditioning_evidence_id, self.absolute_energy_tolerance_j,
                self.relative_energy_tolerance,
                _native_definitions(self.initial, self.compressor))

    def _replay(self):
        return _project(
            self.initial, self.compressor, self.conditioned_inlet_state,
            duration_s=self.duration_s, minimum_mass_kg=self.minimum_mass_kg,
            start_time_s=self.start_time_s,
            time_mapping_evidence_id=self.time_mapping_evidence_id,
            hydrogen_basis_evidence_id=self.hydrogen_basis_evidence_id,
            transfer_boundary_evidence_id=self.transfer_boundary_evidence_id,
            thermal_conditioning_evidence_id=self.thermal_conditioning_evidence_id,
            thermal_conditioning_energy_j=self.supplied_conditioning_energy_j,
            absolute_energy_tolerance_j=self.absolute_energy_tolerance_j,
            relative_energy_tolerance=self.relative_energy_tolerance,
        )

    def _require_equal(self, projected):
        if (type(self.initial) is RealGasLinepackState
                and (type(self.final) is not RealGasLinepackState
                     or self.final.eos is not self.initial.eos
                     or self.final.eos_identity != self.initial.eos_identity)):
            raise ValueError("Real-gas charge must retain the original linepack EOS owner")
        expected = (projected[0], projected[1], projected[2], projected[4],
                    projected[18], projected[5], projected[6], projected[7], projected[8],
                    projected[9], projected[10], projected[11], projected[12],
                    projected[13], projected[14], projected[15], projected[16],
                    projected[17])
        actual = (self.final, self.ledger, self.source_outlet_state,
                  self.duration_s, self.minimum_mass_kg,
                  self.start_time_s, self.end_time_s,
                  self.mass_flow_kg_s, self.transferred_mass_kg,
                  self.required_conditioning_energy_j, self.supplied_conditioning_energy_j,
                  self.conditioning_energy_residual_j, self.time_mapping_evidence_id,
                  self.hydrogen_basis_evidence_id, self.transfer_boundary_evidence_id,
                  self.thermal_conditioning_evidence_id, self.absolute_energy_tolerance_j,
                  self.relative_energy_tolerance)
        if actual != expected or projected[3] != self.conditioned_inlet_state:
            raise ValueError("Compressor-to-linepack receipt differs from replayed transfer ledgers")

    def require_current(self):
        if not self._seal:
            raise ValueError("Compressor-to-linepack receipt has no original issuer seal")
        if self._content() != self._seal:
            raise ValueError("Compressor-to-linepack receipt changed after issuance")
        replay = self._replay()
        self._require_equal(replay)
        return self


def charge_linepack_from_compressor(
    initial: IsothermalLinepackState | RealGasLinepackState,
    compressor: HydrogenRealFluidCompressionRun,
    *,
    duration_s: float,
    start_time_s: float,
    minimum_mass_kg: float,
    conditioned_inlet_state: ThermoState,
    thermal_conditioning_energy_j: float,
    time_mapping_evidence_id: str,
    hydrogen_basis_evidence_id: str,
    transfer_boundary_evidence_id: str,
    thermal_conditioning_evidence_id: str,
    absolute_energy_tolerance_j: float,
    relative_energy_tolerance: float,
) -> CompressorLinepackCharge:
    """Charge an existing native HEOS or explicit analytic linepack owner.

    The caller supplies the physical interval and the typed HEOS state at final
    linepack pressure/fixed temperature. Signed conditioning energy must close
    the discharge-to-linepack state enthalpy change. The linepack remains a
    mass-only fixed-temperature model; no storage energy balance is claimed.
    Real-gas inventories require the same native HEOS fluid, spin and version
    as the compressor. Existing analytic inventories are explicit references.
    """
    projected = _project(
        initial, compressor, conditioned_inlet_state,
        duration_s=duration_s, minimum_mass_kg=minimum_mass_kg,
        start_time_s=start_time_s,
        time_mapping_evidence_id=time_mapping_evidence_id,
        hydrogen_basis_evidence_id=hydrogen_basis_evidence_id,
        transfer_boundary_evidence_id=transfer_boundary_evidence_id,
        thermal_conditioning_evidence_id=thermal_conditioning_evidence_id,
        thermal_conditioning_energy_j=thermal_conditioning_energy_j,
        absolute_energy_tolerance_j=absolute_energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance,
    )
    final, ledger, source_state, mapped_state, duration, start, end, rate, mass, expected_heat, supplied_heat, residual, time_id, basis_id, transfer_id, thermal_id, absolute, relative, minimum_mass = projected
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        result = CompressorLinepackCharge(
            initial, compressor, mapped_state, final, ledger, source_state,
            duration, minimum_mass, start, end, rate, mass, expected_heat, supplied_heat,
            residual, time_id, basis_id, transfer_id, thermal_id, absolute,
            relative, _issuer_token=token,
        )
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
    return result.require_current()


__all__ = ["CompressorLinepackCharge", "charge_linepack_from_compressor"]
