"""Transfer a finite PV-electrolysis H2 batch into an existing linepack owner.

The adapter reuses the producer inventory and the existing lumped linepack
model. It does not add compression, piping, heat transfer, or dispatch physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from math import isclose

from ..core import finite
from ..pipeline_linepack import IsothermalLinepackState, LinepackStepLedger
from ..real_gas_linepack import RealGasLinepackState, RealGasLinepackStepLedger
from ..thermo.coolprop import CoolPropProperties
from ..thermo.isothermal_eos import CoolPropIsothermalEOS
from .pv_electrolysis import PVElectrolysisTrace

_H2_MOLAR_MASS_KG_MOL = 0.00201588
_PENDING: set[object] = set()


def _native_linepack_properties(initial, producer):
    if type(initial) is IsothermalLinepackState:
        return None
    if type(initial) is not RealGasLinepackState or type(initial.eos) is not CoolPropIsothermalEOS:
        raise TypeError("Use an existing linepack state with a native CoolProp EOS")
    eos = initial.eos
    matches = [item for item in producer.gas.native_objects
               if type(item) is CoolPropProperties]
    if len(matches) != 1:
        raise ValueError("Real-gas charging requires the producer's retained CoolProp provider")
    properties = matches[0]
    if (eos.backend != "HEOS" or properties.backend != "HEOS"
            or eos.fluid not in {"Hydrogen", "ParaHydrogen"}
            or eos.fluid != properties.basis.fluid or eos.version != properties.version
            or eos.identity != initial.eos_identity
            or tuple(eos._state.fluid_names()) != (eos.fluid,)
            or tuple(properties._state.fluid_names()) != (eos.fluid,)):
        raise ValueError("Producer and linepack must retain matched direct HEOS hydrogen identities")
    properties.basis.require_compatible(producer.gas.basis)
    properties.basis.require_compatible(producer.final.receiver.basis)
    return properties


def _linepack_definition(initial, producer):
    properties = _native_linepack_properties(initial, producer)
    if properties is None:
        return ()
    eos = initial.eos
    return (id(eos), eos.identity, id(eos._state), id(eos._cp),
            eos.density_pt, eos.pressure_rho_t,
            id(properties), properties.basis, properties.version, properties.backend,
            id(properties._state), id(properties._cp), properties.state_pt,
            properties.molar_mass_kg_mol)


@dataclass(frozen=True, slots=True)
class ElectrolysisSourceWithdrawalLedger:
    """Caller-evidenced source-side H2 stock removal; no EOS reflash is done."""

    initial_hydrogen_inventory_mol: float
    post_production_hydrogen_inventory_mol: float
    available_production_batch_mol: float
    withdrawn_from_source_mol: float
    transfer_loss_mol: float
    delivered_to_linepack_mol: float
    retained_production_batch_mol: float
    post_transfer_hydrogen_inventory_mol: float
    source_removal_evidence_id: str

    def __post_init__(self):
        for name in ("initial_hydrogen_inventory_mol", "post_production_hydrogen_inventory_mol",
                     "available_production_batch_mol", "withdrawn_from_source_mol",
                     "transfer_loss_mol", "delivered_to_linepack_mol",
                     "retained_production_batch_mol", "post_transfer_hydrogen_inventory_mol"):
            finite(getattr(self, name), name)
            if getattr(self, name) < 0.:
                raise ValueError(f"{name} cannot be negative")
        if not isinstance(self.source_removal_evidence_id, str) or not self.source_removal_evidence_id.strip():
            raise ValueError("Explicit source removal evidence is required")
        if not isclose(self.available_production_batch_mol,
                       self.post_production_hydrogen_inventory_mol
                       - self.initial_hydrogen_inventory_mol,
                       rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Source H2 production batch does not match its inventory difference")
        if not isclose(self.delivered_to_linepack_mol,
                       self.withdrawn_from_source_mol-self.transfer_loss_mol,
                       rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Source withdrawal, transfer loss and delivery do not close")
        if not isclose(self.retained_production_batch_mol,
                       self.available_production_batch_mol-self.withdrawn_from_source_mol,
                       rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Retained product batch does not match the withdrawal ledger")
        if not isclose(self.post_transfer_hydrogen_inventory_mol,
                       self.post_production_hydrogen_inventory_mol-self.withdrawn_from_source_mol,
                       rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Post-transfer source H2 inventory does not close")


@dataclass(frozen=True, slots=True)
class ElectrolysisLinepackEnergyLedger:
    """Caller-signed energy-reference and isothermal boundary closure."""

    source_energy_reference_id: str
    linepack_energy_reference_id: str
    reference_mapping_evidence_id: str
    boundary_energy_evidence_id: str
    transferred_hydrogen_mass_kg: float
    source_transfer_enthalpy_j: float
    reference_offset_j: float
    conditioning_energy_j: float
    linepack_energy_change_j: float
    residual_j: float
    absolute_tolerance_j: float
    relative_tolerance: float

    def __post_init__(self):
        for name in ("source_energy_reference_id", "linepack_energy_reference_id",
                     "reference_mapping_evidence_id", "boundary_energy_evidence_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Explicit {name} is required")
        for name in ("source_transfer_enthalpy_j", "reference_offset_j",
                     "conditioning_energy_j", "linepack_energy_change_j", "residual_j"):
            finite(getattr(self, name), name)
        finite(self.transferred_hydrogen_mass_kg,
               "energy ledger transferred_hydrogen_mass_kg", positive=True)
        finite(self.absolute_tolerance_j, "absolute_tolerance_j")
        finite(self.relative_tolerance, "relative_tolerance")
        if self.absolute_tolerance_j < 0. or self.relative_tolerance < 0.:
            raise ValueError("Energy closure tolerances cannot be negative")
        expected = (self.source_transfer_enthalpy_j + self.reference_offset_j
                    + self.conditioning_energy_j - self.linepack_energy_change_j)
        tolerance = self.absolute_tolerance_j + self.relative_tolerance * max(
            abs(self.source_transfer_enthalpy_j), abs(self.reference_offset_j),
            abs(self.conditioning_energy_j), abs(self.linepack_energy_change_j), 1.)
        if not isclose(self.residual_j, expected, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Energy ledger residual does not match its signed entries")
        if abs(expected) > tolerance:
            raise ValueError("Energy ledger does not close within its declared tolerances")


def _seal(producer, initial, final, ledger, values):
    return (id(producer), id(initial), id(final), id(ledger),
            producer.owner, producer.evidence.clock_id, values)


@dataclass(frozen=True, slots=True)
class ElectrolysisLinepackCharge:
    """Receipt for transferring one finite producer batch into linepack."""

    producer: PVElectrolysisTrace
    initial: IsothermalLinepackState | RealGasLinepackState
    final: IsothermalLinepackState | RealGasLinepackState
    ledger: LinepackStepLedger | RealGasLinepackStepLedger
    clock_id: str
    transfer_start_s: float
    transfer_end_s: float
    transfer_loss_mol: float
    available_hydrogen_mol: float
    transferred_hydrogen_mol: float
    transferred_hydrogen_mass_kg: float
    source_pressure_at_start_pa: float
    minimum_source_pressure_pa: float
    pressure_margin_pa: float
    source_temperature_bounds_k: tuple[float, float]
    maximum_temperature_difference_k: float
    time_mapping_evidence_id: str
    hydrogen_basis_evidence_id: str
    pressure_boundary_evidence_id: str
    isothermal_boundary_evidence_id: str
    transfer_boundary_evidence_id: str
    source_transfer_state_evidence_id: str
    source_removal_evidence_id: str
    energy_ledger: ElectrolysisLinepackEnergyLedger
    source_ledger: ElectrolysisSourceWithdrawalLedger
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue this receipt through charge_linepack_from_electrolysis")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "_binding", self._content())

    def _content(self):
        values = tuple((name, getattr(self, name)) for name in (
            "clock_id", "transfer_start_s", "transfer_end_s", "transfer_loss_mol", "available_hydrogen_mol",
            "transferred_hydrogen_mol", "transferred_hydrogen_mass_kg",
            "source_pressure_at_start_pa", "minimum_source_pressure_pa", "pressure_margin_pa",
            "source_temperature_bounds_k", "maximum_temperature_difference_k",
            "time_mapping_evidence_id", "hydrogen_basis_evidence_id",
            "pressure_boundary_evidence_id", "isothermal_boundary_evidence_id",
            "transfer_boundary_evidence_id",
            "source_transfer_state_evidence_id",
            "source_removal_evidence_id",
        ))
        return _seal(self.producer, self.initial, self.final, self.ledger,
                     values + (("energy_ledger", tuple(
                         (item.name, getattr(self.energy_ledger, item.name))
                         for item in fields(self.energy_ledger))),
                               ("source_ledger", tuple(
                         (item.name, getattr(self.source_ledger, item.name))
                         for item in fields(self.source_ledger))),
                               ("native_definition", _linepack_definition(self.initial, self.producer))))

    def require_current(self):
        if self._issued is None or self._binding != self._content():
            raise ValueError("Electrolysis-to-linepack receipt binding changed")
        if (type(self.producer) is not PVElectrolysisTrace
                or type(self.initial) not in {IsothermalLinepackState, RealGasLinepackState}
                or type(self.final) is not type(self.initial)
                or type(self.ledger) is not (RealGasLinepackStepLedger
                    if type(self.initial) is RealGasLinepackState else LinepackStepLedger)
                or type(self.initial) is RealGasLinepackState
                and self.final.eos is not self.initial.eos):
            raise TypeError("Receipt no longer retains the admitted producer and linepack ledgers")
        self.producer.require_current()
        recreated = _derive(
            self.producer, self.initial, self.transfer_loss_mol, self.clock_id,
            source_withdrawal_mol=self.source_ledger.withdrawn_from_source_mol,
            source_removal_evidence_id=self.source_ledger.source_removal_evidence_id,
            transfer_start_s=self.transfer_start_s,
            transfer_end_s=self.transfer_end_s,
            minimum_source_pressure_margin_pa=self.pressure_margin_pa,
            minimum_source_pressure_during_transfer_pa=self.minimum_source_pressure_pa,
            source_temperature_bounds_k=self.source_temperature_bounds_k,
            temperature_tolerance_k=max(self.maximum_temperature_difference_k, 1e-12),
            time_mapping_evidence_id=self.time_mapping_evidence_id,
            hydrogen_basis_evidence_id=self.hydrogen_basis_evidence_id,
            pressure_boundary_evidence_id=self.pressure_boundary_evidence_id,
            isothermal_boundary_evidence_id=self.isothermal_boundary_evidence_id,
            transfer_boundary_evidence_id=self.transfer_boundary_evidence_id,
            source_transfer_state_evidence_id=self.source_transfer_state_evidence_id,
            source_energy_reference_id=self.energy_ledger.source_energy_reference_id,
            linepack_energy_reference_id=self.energy_ledger.linepack_energy_reference_id,
            reference_mapping_evidence_id=self.energy_ledger.reference_mapping_evidence_id,
            boundary_energy_evidence_id=self.energy_ledger.boundary_energy_evidence_id,
            reference_offset_j=self.energy_ledger.reference_offset_j,
            conditioning_energy_j=self.energy_ledger.conditioning_energy_j,
            linepack_energy_change_j=self.energy_ledger.linepack_energy_change_j,
            absolute_energy_tolerance_j=self.energy_ledger.absolute_tolerance_j,
            relative_energy_tolerance=self.energy_ledger.relative_tolerance,
            source_transfer_enthalpy_j=self.energy_ledger.source_transfer_enthalpy_j,
        )
        (final, ledger, available, transferred, mass, source_start_pressure,
         minimum_source_pressure, margin, temperature_bounds, delta_t,
         energy_ledger, source_ledger) = recreated
        expected = {
            "final": final, "ledger": ledger, "energy_ledger": energy_ledger,
            "source_ledger": source_ledger, "available_hydrogen_mol": available,
            "transferred_hydrogen_mol": transferred, "transferred_hydrogen_mass_kg": mass,
            "transfer_start_s": ledger.start_time_s, "transfer_end_s": ledger.end_time_s,
            "source_pressure_at_start_pa": source_start_pressure,
            "minimum_source_pressure_pa": minimum_source_pressure,
            "pressure_margin_pa": margin, "source_temperature_bounds_k": temperature_bounds,
            "maximum_temperature_difference_k": delta_t,
        }
        for name, value in expected.items():
            if value != getattr(self, name):
                raise ValueError("Producer inventory, linepack state, or transfer ledger changed")
        return self


def _derive(producer, initial, transfer_loss_mol, clock_id, *,
            source_withdrawal_mol, source_removal_evidence_id,
            transfer_start_s, transfer_end_s,
            minimum_source_pressure_margin_pa, temperature_tolerance_k,
            minimum_source_pressure_during_transfer_pa, source_temperature_bounds_k,
            time_mapping_evidence_id, hydrogen_basis_evidence_id,
            pressure_boundary_evidence_id, isothermal_boundary_evidence_id,
            transfer_boundary_evidence_id, source_transfer_state_evidence_id,
            source_energy_reference_id,
            linepack_energy_reference_id, reference_mapping_evidence_id,
            boundary_energy_evidence_id, reference_offset_j, conditioning_energy_j,
            source_transfer_enthalpy_j, linepack_energy_change_j, absolute_energy_tolerance_j,
            relative_energy_tolerance):
    if type(producer) is not PVElectrolysisTrace:
        raise TypeError("Use the admitted PVElectrolysisTrace")
    if type(initial) not in {IsothermalLinepackState, RealGasLinepackState}:
        raise TypeError("Use an existing isothermal linepack state")
    producer.require_current()
    properties = _native_linepack_properties(initial, producer)
    molar_mass = (initial.molecular_mass_kg_mol if properties is None
                  else properties.molar_mass_kg_mol)
    for name, value in (
        ("clock", clock_id), ("time mapping evidence", time_mapping_evidence_id),
        ("hydrogen basis evidence", hydrogen_basis_evidence_id),
        ("pressure boundary evidence", pressure_boundary_evidence_id),
        ("isothermal boundary evidence", isothermal_boundary_evidence_id),
        ("transfer boundary evidence", transfer_boundary_evidence_id),
        ("source transfer state evidence", source_transfer_state_evidence_id),
        ("source removal evidence", source_removal_evidence_id),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {name} is required")
    if clock_id != producer.evidence.clock_id:
        raise ValueError("Producer and linepack must use the same declared physical clock")
    transfer_start = finite(transfer_start_s, "transfer_start_s")
    transfer_end = finite(transfer_end_s, "transfer_end_s")
    if transfer_start < producer.final.time_s or initial.time_s != transfer_start:
        raise ValueError("The separate linepack transfer window must begin after production at the mapped start time")
    duration = transfer_end - transfer_start
    if duration <= 0.:
        raise ValueError("The separate post-production transfer window must have positive duration")

    owner = producer.owner
    hydrogen_id = owner.hydrogen_id
    species = next((item for item in owner.reaction.species
                    if item.identifier == hydrogen_id), None)
    if (species is None or dict(species.elements) != {"H": 2}
            or species.charge != 0 or species.phase not in {"gas", "vapor"}
            or not isclose(species.molar_mass_kg_mol, _H2_MOLAR_MASS_KG_MOL,
                           rel_tol=1e-8, abs_tol=0.)
            or not isclose(producer.gas.molar_mass_kg_mol, _H2_MOLAR_MASS_KG_MOL,
                           rel_tol=1e-8, abs_tol=0.)
            or not isclose(molar_mass, _H2_MOLAR_MASS_KG_MOL,
                           rel_tol=1e-8, abs_tol=0.)):
        raise ValueError("Producer species, gas ledger, and linepack must share neutral H2 mass basis")
    available = (finite(producer.final.amounts_mol.get(hydrogen_id, 0.), "final H2 inventory")
                 - finite(producer.initial.amounts_mol.get(hydrogen_id, 0.), "initial H2 inventory"))
    if available <= 0.:
        raise ValueError("Accepted producer interval contains no positive net H2 batch")
    withdrawal = finite(source_withdrawal_mol, "source_withdrawal_mol", positive=True)
    if withdrawal > available:
        raise ValueError("Source withdrawal exceeds the net H2 production batch")
    loss = finite(transfer_loss_mol, "transfer_loss_mol")
    if loss < 0. or loss >= withdrawal:
        raise ValueError("Transfer loss must be nonnegative and smaller than the source withdrawal")
    transferred_mol = withdrawal-loss
    source_initial_mol = finite(producer.initial.amounts_mol.get(hydrogen_id, 0.),
                                "initial producer H2 inventory")
    source_final_mol = finite(producer.final.amounts_mol.get(hydrogen_id, 0.),
                              "final producer H2 inventory")
    source_ledger = ElectrolysisSourceWithdrawalLedger(
        source_initial_mol, source_final_mol, available, withdrawal, loss,
        transferred_mol, available-withdrawal, source_final_mol-withdrawal,
        source_removal_evidence_id.strip(),
    )

    source = producer.final.receiver
    if source.phase not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError("Only a single gaseous H2 product state can feed this linepack boundary")
    temperature_tolerance = finite(temperature_tolerance_k, "temperature_tolerance_k", positive=True)
    if (isinstance(source_temperature_bounds_k, (str, bytes))
            or not isinstance(source_temperature_bounds_k, (tuple, list))
            or len(source_temperature_bounds_k) != 2):
        raise ValueError("Declare lower/upper source-temperature bounds for the transfer window")
    source_temperature_bounds = tuple(
        finite(value, "source transfer temperature bound", positive=True)
        for value in source_temperature_bounds_k
    )
    if source_temperature_bounds[1] < source_temperature_bounds[0]:
        raise ValueError("Source-temperature bounds must increase or be equal")
    if not (source_temperature_bounds[0] <= source.temperature_k <= source_temperature_bounds[1]):
        raise ValueError("The accepted production-end product temperature lies outside the transfer bounds")
    temperature_difference = max(
        abs(source_temperature_bounds[0] - initial.temperature_k),
        abs(source_temperature_bounds[1] - initial.temperature_k),
    )
    if temperature_difference > temperature_tolerance:
        raise ValueError("Source-temperature bounds exceed the fixed-isothermal linepack tolerance")
    margin = finite(minimum_source_pressure_margin_pa, "minimum_source_pressure_margin_pa")
    if margin < 0.:
        raise ValueError("Source pressure margin cannot be negative")
    minimum_source_pressure = finite(minimum_source_pressure_during_transfer_pa,
                                     "minimum_source_pressure_during_transfer_pa", positive=True)
    if minimum_source_pressure > source.pressure_pa:
        raise ValueError("Declared minimum source pressure exceeds the accepted production-end state")
    mass = transferred_mol * molar_mass
    final, ledger = initial.advance(
        duration_s=duration,
        inlet_mass_flow_kg_s=mass / duration,
        outlet_mass_flow_kg_s=0.,
        minimum_mass_kg=0.,
    )
    pressure_margin = minimum_source_pressure - final.pressure_pa
    if pressure_margin < margin:
        raise ValueError("The evidenced minimum source pressure does not exceed final linepack pressure by the declared margin")
    source_reference = source.basis.reference_id
    for name, value in (("source energy reference", source_energy_reference_id),
                        ("linepack energy reference", linepack_energy_reference_id),
                        ("energy reference mapping evidence", reference_mapping_evidence_id),
                        ("boundary energy evidence", boundary_energy_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {name} is required")
    if source_energy_reference_id != source_reference:
        raise ValueError("Declared source energy reference differs from the admitted product-state basis")
    offset = finite(reference_offset_j, "reference_offset_j")
    if (linepack_energy_reference_id == source_energy_reference_id and offset != 0.
            or linepack_energy_reference_id != source_energy_reference_id
            and not reference_mapping_evidence_id.strip()):
        raise ValueError("Mismatched energy references require an explicit signed offset mapping")
    source_enthalpy = finite(source_transfer_enthalpy_j,
                             "integrated source_transfer_enthalpy_j")
    conditioning = finite(conditioning_energy_j, "conditioning_energy_j")
    linepack_energy = finite(linepack_energy_change_j, "linepack_energy_change_j")
    absolute_tolerance = finite(absolute_energy_tolerance_j, "absolute_energy_tolerance_j")
    relative_tolerance = finite(relative_energy_tolerance, "relative_energy_tolerance")
    if absolute_tolerance < 0. or relative_tolerance < 0.:
        raise ValueError("Energy closure tolerances cannot be negative")
    if properties is not None:
        if linepack_energy_reference_id != properties.basis.reference_id:
            raise ValueError("Real-gas linepack energy must use its native CoolProp reference")
        endpoints = [properties.state_pt(state.pressure_pa, state.temperature_k)
                     for state in (initial, final)]
        for state, native in zip((initial, final), endpoints, strict=True):
            if not isclose(state.density_kg_m3, native.density_kg_m3,
                           rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError("Linepack density differs from the retained native property provider")
        native_delta_u = (final.mass_kg * endpoints[1].internal_energy_j_kg
                          - initial.mass_kg * endpoints[0].internal_energy_j_kg)
        native_budget = absolute_tolerance + relative_tolerance * max(
            abs(native_delta_u), abs(linepack_energy), 1.)
        if abs(linepack_energy - native_delta_u) > native_budget:
            raise ValueError("Declared linepack energy change differs from native CoolProp inventory energy")
    energy_residual = source_enthalpy + offset + conditioning - linepack_energy
    energy_tolerance = absolute_tolerance + relative_tolerance * max(
        abs(source_enthalpy), abs(offset), abs(conditioning), abs(linepack_energy), 1.)
    if abs(energy_residual) > energy_tolerance:
        raise ValueError("Signed source/conditioning energy does not close to the caller-declared linepack energy change")
    energy_ledger = ElectrolysisLinepackEnergyLedger(
        source_energy_reference_id, linepack_energy_reference_id,
        reference_mapping_evidence_id.strip(), boundary_energy_evidence_id.strip(),
            mass, source_enthalpy, offset, conditioning, linepack_energy, energy_residual,
        absolute_tolerance, relative_tolerance,
    )
    if (ledger.start_time_s != transfer_start or ledger.end_time_s != transfer_end
            or not isclose(ledger.inlet_mass_kg, mass, rel_tol=1e-12, abs_tol=1e-15)
            or ledger.outlet_mass_kg != 0.
            or not isclose(final.mass_kg-initial.mass_kg, mass,
                           rel_tol=1e-12, abs_tol=1e-15)):
        raise ArithmeticError("Linepack charge does not conserve the transferred H2 batch")
    return (final, ledger, available, transferred_mol, mass, source.pressure_pa,
            minimum_source_pressure, pressure_margin, source_temperature_bounds,
            temperature_difference, energy_ledger, source_ledger)


def charge_linepack_from_electrolysis(
    initial: IsothermalLinepackState | RealGasLinepackState,
    producer: PVElectrolysisTrace,
    *,
    source_withdrawal_mol: float,
    source_removal_evidence_id: str,
    transfer_loss_mol: float = 0.,
    clock_id: str,
    transfer_start_s: float,
    transfer_end_s: float,
    minimum_source_pressure_margin_pa: float = 0.,
    minimum_source_pressure_during_transfer_pa: float,
    source_temperature_bounds_k: tuple[float, float],
    temperature_tolerance_k: float = 1e-6,
    time_mapping_evidence_id: str,
    hydrogen_basis_evidence_id: str,
    pressure_boundary_evidence_id: str,
    isothermal_boundary_evidence_id: str,
    transfer_boundary_evidence_id: str,
    source_transfer_state_evidence_id: str,
    source_energy_reference_id: str,
    linepack_energy_reference_id: str,
    reference_mapping_evidence_id: str,
    boundary_energy_evidence_id: str,
    reference_offset_j: float,
    conditioning_energy_j: float,
    source_transfer_enthalpy_j: float,
    linepack_energy_change_j: float,
    absolute_energy_tolerance_j: float = 1e-6,
    relative_energy_tolerance: float = 1e-10,
) -> ElectrolysisLinepackCharge:
    """Transfer one completed finite H2 batch over a separate later window.

    The linepack is advanced using its existing fixed-volume owner. Native
    real-gas states retain the producer's matched CoolProp reference and verify
    the declared inventory energy change against native endpoint energies.
    Transfer start/end follow production on the shared clock. A caller-evidenced
    source stock ledger records initial, produced, withdrawn, lost, retained and
    post-transfer H2 moles; it does not mutate or EOS-reflash the producer trace.
    Caller-evidenced
    minimum source pressure and source-temperature bounds must remain compatible
    with the receiving linepack throughout this separate transfer window. The
    source transfer enthalpy is an integrated caller input, not inferred from
    the production-end state. No compressor, valve, pipe, pressure-loss, or
    thermal-conditioning calculation is performed. The signed energy ledger
    checks caller-supplied source enthalpy, reference mapping, conditioning, and
    declared linepack energy change; it supplies no energy/thermal solver.
    """
    values = _derive(
        producer, initial, transfer_loss_mol, clock_id,
        source_withdrawal_mol=source_withdrawal_mol,
        source_removal_evidence_id=source_removal_evidence_id,
        transfer_start_s=transfer_start_s,
        transfer_end_s=transfer_end_s,
        minimum_source_pressure_margin_pa=minimum_source_pressure_margin_pa,
        temperature_tolerance_k=temperature_tolerance_k,
        minimum_source_pressure_during_transfer_pa=minimum_source_pressure_during_transfer_pa,
        source_temperature_bounds_k=source_temperature_bounds_k,
        time_mapping_evidence_id=time_mapping_evidence_id,
        hydrogen_basis_evidence_id=hydrogen_basis_evidence_id,
        pressure_boundary_evidence_id=pressure_boundary_evidence_id,
        isothermal_boundary_evidence_id=isothermal_boundary_evidence_id,
        transfer_boundary_evidence_id=transfer_boundary_evidence_id,
        source_transfer_state_evidence_id=source_transfer_state_evidence_id,
        source_energy_reference_id=source_energy_reference_id,
        linepack_energy_reference_id=linepack_energy_reference_id,
        reference_mapping_evidence_id=reference_mapping_evidence_id,
        boundary_energy_evidence_id=boundary_energy_evidence_id,
        reference_offset_j=reference_offset_j,
        conditioning_energy_j=conditioning_energy_j,
        source_transfer_enthalpy_j=source_transfer_enthalpy_j,
        linepack_energy_change_j=linepack_energy_change_j,
        absolute_energy_tolerance_j=absolute_energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance,
    )
    (final, ledger, available, transferred, mass, source_start_pressure,
     minimum_source_pressure, margin, temperature_bounds, delta_t,
     energy_ledger, source_ledger) = values
    token = object()
    _PENDING.add(token)
    try:
        receipt = ElectrolysisLinepackCharge(
            producer, initial, final, ledger, clock_id,
            transfer_start_s, transfer_end_s, transfer_loss_mol,
            available, transferred, mass, source_start_pressure,
            minimum_source_pressure, margin, temperature_bounds, delta_t,
            time_mapping_evidence_id.strip(), hydrogen_basis_evidence_id.strip(),
            pressure_boundary_evidence_id.strip(), isothermal_boundary_evidence_id.strip(),
            transfer_boundary_evidence_id.strip(), source_transfer_state_evidence_id.strip(),
            source_removal_evidence_id.strip(), energy_ledger, source_ledger, token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    return receipt.require_current()


__all__ = ["ElectrolysisSourceWithdrawalLedger", "ElectrolysisLinepackEnergyLedger",
           "ElectrolysisLinepackCharge",
           "charge_linepack_from_electrolysis"]
