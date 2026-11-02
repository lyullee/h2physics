"""Transfer accepted adsorption product into existing H2 pipeline linepack.

This boundary reuses the finite-vessel delivery ledger and lumped linepack
inventory. It adds no adsorption, compressor, or pipeline-flow physics.
"""

from dataclasses import dataclass, field
from hashlib import sha256
from math import isclose

from ..core import finite
from ..pipeline_linepack import IsothermalLinepackState, LinepackStepLedger
from ..real_gas_linepack import RealGasLinepackState, RealGasLinepackStepLedger
from ..storage.product_delivery import AdsorptionProductMassFlow
from ..thermo.isothermal_eos import CoolPropIsothermalEOS

_H2_MOLAR_MASS_KG_MOL = 0.00201588
_PENDING: set[object] = set()


def _admit_basis(initial, product, declared_spin, spin_evidence):
    if type(initial) not in {IsothermalLinepackState, RealGasLinepackState}:
        raise TypeError("Supply an existing analytic or native real-gas linepack state")
    if (product.delivery.delivery_species != ("H2",)
            or product.species.count("H2") != 1):
        raise ValueError("The linepack accepts only a delivery explicitly selected as H2")
    source_bases = (product.delivery.charged.gas_state.basis,
                    product.delivery.discharged.gas_state.basis)
    source_bases[0].require_compatible(source_bases[1])
    for basis in source_bases:
        if (basis.spin_composition == "no-molecular-H2"
                or basis.reference_id.startswith("CoolProp:")
                and not basis.fluid.startswith("CoolProp HEOS fixed mixture ")
                and basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}):
            raise ValueError("Native source property basis does not contain molecular hydrogen")
    known = {value.spin_composition for value in source_bases
             if value.spin_composition in {"normal", "para", "ortho"}}
    if declared_spin is not None:
        if declared_spin not in {"normal", "para", "ortho"}:
            raise ValueError("Declare a known H2 spin composition")
        if known and known != {declared_spin}:
            raise ValueError("Declared H2 spin contradicts the admitted source basis")
    elif len(known) == 1:
        declared_spin = next(iter(known))
    if spin_evidence is not None and (not isinstance(spin_evidence, str) or not spin_evidence.strip()):
        raise ValueError("Spin mapping evidence must be explicit nonempty text")
    h2_mass = float(product.molar_masses_kg_mol[product.species.index("H2")])
    if type(initial) is IsothermalLinepackState:
        target_mass = initial.molecular_mass_kg_mol
        if not isclose(target_mass, _H2_MOLAR_MASS_KG_MOL, rel_tol=1e-8, abs_tol=0.):
            raise ValueError("Analytic H2 linepack requires the declared H2 molar mass")
        definition = ()
    else:
        eos = initial.eos
        target_spin = {"Hydrogen": "normal", "ParaHydrogen": "para", "OrthoHydrogen": "ortho"}
        if (type(eos) is not CoolPropIsothermalEOS or eos.backend != "HEOS"
                or eos.fluid not in target_spin or eos.identity != initial.eos_identity):
            raise ValueError("Native H2 linepack requires its unchanged pure-H2 CoolProp HEOS owner")
        if declared_spin != target_spin[eos.fluid]:
            raise ValueError("Known adsorption H2 spin must match the native linepack spin")
        if not known and spin_evidence is None:
            raise ValueError("Unresolved source H2 spin needs an explicit caller mapping evidence")
        with eos._lock:
            if tuple(eos._state.fluid_names()) != (eos.fluid,):
                raise ValueError("Native linepack fluid identity differs from its declared pure-H2 basis")
            target_mass = finite(eos._state.molar_mass(), "native H2 molar mass", positive=True)
        native_pressure = eos.pressure_rho_t(initial.density_kg_m3, initial.temperature_k)
        if not isclose(native_pressure, initial.pressure_pa, rel_tol=1e-8, abs_tol=1e-6):
            raise ValueError("Linepack state no longer reproduces from its actual native EOS")
        definition = (id(eos), eos.identity, eos.fluid, eos.backend, eos.version,
                      id(eos._state), id(eos._cp), eos._allowed_phases,
                      eos.density_pt, eos.pressure_rho_t, target_mass)
    if not isclose(h2_mass, target_mass, rel_tol=1e-8, abs_tol=0.):
        raise ValueError("Adsorption H2 and linepack molecular-mass bases must agree")
    return declared_spin, definition


def _seal(flow, initial, final, ledger, start_s, end_s, timing_evidence,
          species_evidence, transfer_evidence, spin, spin_evidence, eos_binding):
    return sha256(repr((id(flow), id(initial), id(final), id(ledger), flow,
        initial, final, ledger, start_s, end_s, timing_evidence,
        species_evidence, transfer_evidence, spin, spin_evidence, eos_binding)).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AdsorptionLinepackCharge:
    """Issuer-bound transfer result from one adsorption delivery interval."""

    product: AdsorptionProductMassFlow
    initial: IsothermalLinepackState | RealGasLinepackState
    final: IsothermalLinepackState | RealGasLinepackState
    ledger: LinepackStepLedger | RealGasLinepackStepLedger
    time_mapping_evidence_id: str
    hydrogen_basis_evidence_id: str
    transfer_boundary_evidence_id: str
    hydrogen_spin_composition: str | None = None
    hydrogen_spin_evidence_id: str | None = None
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)
    _eos_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Create adsorption-to-linepack receipts with charge_linepack_from_adsorption_product")
        _PENDING.remove(self._issuer)
        spin, binding = _admit_basis(self.initial, self.product,
                                    self.hydrogen_spin_composition, self.hydrogen_spin_evidence_id)
        object.__setattr__(self, "hydrogen_spin_composition", spin)
        object.__setattr__(self, "_eos_binding", binding)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_seal", _seal(
            self.product, self.initial, self.final, self.ledger,
            self.ledger.start_time_s, self.ledger.end_time_s,
            self.time_mapping_evidence_id, self.hydrogen_basis_evidence_id,
            self.transfer_boundary_evidence_id, self.hydrogen_spin_composition,
            self.hydrogen_spin_evidence_id, self._eos_binding))

    def require_current(self):
        self.product.require_current()
        if self._issuer is not self._issued:
            raise ValueError("Adsorption-to-linepack receipt lost its original issuer")
        spin, binding = _admit_basis(self.initial, self.product,
                                    self.hydrogen_spin_composition, self.hydrogen_spin_evidence_id)
        native = type(self.initial) is RealGasLinepackState
        if (type(self.final) is not type(self.initial)
                or type(self.ledger) is not (RealGasLinepackStepLedger if native else LinepackStepLedger)
                or spin != self.hydrogen_spin_composition or binding != self._eos_binding
                or self.product.delivery.delivery_species != ("H2",)
                or self.product.species.count("H2") != 1
                or self.ledger.start_time_s != self.initial.time_s
                or self.ledger.end_time_s != self.final.time_s
                or not isclose(self.ledger.end_time_s-self.ledger.start_time_s,
                               self.product.elapsed_s, rel_tol=1e-12, abs_tol=1e-12)
                or not isclose(self.ledger.inlet_mass_kg, self.product.delivered_product_mass_kg,
                               rel_tol=1e-12, abs_tol=1e-15)
                or self.ledger.outlet_mass_kg != 0.
                or not isclose(self.final.mass_kg-self.initial.mass_kg,
                               self.ledger.inlet_mass_kg, rel_tol=1e-12, abs_tol=1e-15)
                or abs(self.ledger.mass_residual_kg) > 1e-12*max(1., self.initial.mass_kg)
                or not self.time_mapping_evidence_id.strip()
                or not self.hydrogen_basis_evidence_id.strip()
                or not self.transfer_boundary_evidence_id.strip()
                or self._seal != _seal(self.product, self.initial, self.final,
                    self.ledger, self.ledger.start_time_s, self.ledger.end_time_s,
                    self.time_mapping_evidence_id, self.hydrogen_basis_evidence_id,
                    self.transfer_boundary_evidence_id, self.hydrogen_spin_composition,
                    self.hydrogen_spin_evidence_id, self._eos_binding)):
            raise ValueError("Adsorption product and linepack transfer ledgers no longer agree")
        if native:
            _, final_binding = _admit_basis(self.final, self.product,
                self.hydrogen_spin_composition, self.hydrogen_spin_evidence_id)
            if (self.final.eos is not self.initial.eos or final_binding != self._eos_binding
                    or self.ledger.eos_identity != self.initial.eos_identity
                    or self.ledger.initial_pressure_pa != self.initial.pressure_pa
                    or self.ledger.final_pressure_pa != self.final.pressure_pa
                    or self.ledger.initial_mass_kg != self.initial.mass_kg
                    or self.ledger.final_mass_kg != self.final.mass_kg
                    or self.final.volume_m3 != self.initial.volume_m3
                    or self.final.temperature_k != self.initial.temperature_k):
                raise ValueError("Native linepack endpoint/EOS ledger changed")
        return self


def charge_linepack_from_adsorption_product(
    initial: IsothermalLinepackState | RealGasLinepackState,
    product: AdsorptionProductMassFlow,
    *,
    start_time_s: float,
    end_time_s: float,
    minimum_mass_kg: float,
    time_mapping_evidence_id: str,
    hydrogen_basis_evidence_id: str,
    transfer_boundary_evidence_id: str,
    hydrogen_spin_composition: str | None = None,
    hydrogen_spin_evidence_id: str | None = None,
) -> AdsorptionLinepackCharge:
    """Add one measured-by-ledger H2 interval to the existing linepack owner.

    The caller must map the adsorption endpoint interval onto the pipeline clock
    and establish that the selected product is hydrogen. No process timing,
    purification, compression, pressure matching, or transient flow is inferred.
    The native route requires a source-compatible known spin. For an unresolved
    mixed source, a caller spin declaration and its evidence are mandatory; they
    are boundary claims rather than native source spin qualification. Only mass
    enters this ledger: source enthalpy and conditioning energy are not inferred.
    """
    if type(product) is not AdsorptionProductMassFlow:
        raise TypeError("Supply an accepted AdsorptionProductMassFlow")
    product.require_current()
    spin, _ = _admit_basis(initial, product, hydrogen_spin_composition, hydrogen_spin_evidence_id)
    start = finite(start_time_s, "start_time_s")
    end = finite(end_time_s, "end_time_s")
    if (start != initial.time_s or end <= start
            or not isclose(end-start, product.elapsed_s, rel_tol=1e-12, abs_tol=1e-12)):
        raise ValueError("Explicit source interval must match the linepack clock and product averaging interval")
    for label, value in (("time mapping evidence", time_mapping_evidence_id),
                         ("hydrogen basis evidence", hydrogen_basis_evidence_id),
                         ("transfer boundary evidence", transfer_boundary_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {label}")
    final, ledger = initial.advance(
        duration_s=end-start,
        inlet_mass_flow_kg_s=product.delivered_product_average_mass_rate_kg_s,
        outlet_mass_flow_kg_s=0.,
        minimum_mass_kg=minimum_mass_kg,
    )
    if ledger.start_time_s != start or ledger.end_time_s != end:
        raise ValueError("Native linepack clock does not exactly match the requested mapped interval")
    if not isclose(ledger.inlet_mass_kg, product.delivered_product_mass_kg,
                   rel_tol=1e-12, abs_tol=1e-15):
        raise ArithmeticError("Linepack charge does not conserve the adsorption product mass")
    token = object()
    _PENDING.add(token)
    try:
        receipt = AdsorptionLinepackCharge(
            product, initial, final, ledger, time_mapping_evidence_id.strip(),
            hydrogen_basis_evidence_id.strip(), transfer_boundary_evidence_id.strip(),
            spin, hydrogen_spin_evidence_id, _issuer=token)
    except Exception:
        _PENDING.discard(token)
        raise
    return receipt.require_current()


__all__ = ["AdsorptionLinepackCharge", "charge_linepack_from_adsorption_product"]
