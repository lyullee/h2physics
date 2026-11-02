"""Native VLE phase compositions and explicit mole-to-mass quality accounting.

The installed CoolProp AbstractState API supplies mole_fractions_liquid/vapor.
No equilibrium composition is estimated here. Reference:
https://coolprop.org/apidoc/CoolProp.AbstractState.html
"""

from dataclasses import dataclass, field
from math import fsum, isclose

from ..core import finite

_PENDING_PARTITION_ISSUERS: set[object] = set()
_PENDING_INVERSE_ISSUERS: set[object] = set()


def _issue_native_partition(**values):
    token = object()
    _PENDING_PARTITION_ISSUERS.add(token)
    try:
        return MixturePhasePartition(**values, _issuer_token=token)
    except Exception:
        _PENDING_PARTITION_ISSUERS.discard(token)
        raise


def _issue_native_inverse(**values):
    token = object()
    _PENDING_INVERSE_ISSUERS.add(token)
    try:
        return MixturePartitionInverse(**values, _issuer_token=token)
    except Exception:
        _PENDING_INVERSE_ISSUERS.discard(token)
        raise


class MixturePartitionInverseError(RuntimeError):
    def __init__(self, cause, evaluations, native_root=None):
        super().__init__(str(cause))
        self.cause = cause
        self.evaluations = tuple(evaluations)
        self.native_root = native_root


@dataclass(frozen=True, slots=True)
class MixturePartitionInverse:
    partition: object
    target_enthalpy_j_kg: float
    quality_bounds: tuple
    bracket_residuals_j_kg: tuple
    evaluations: tuple
    native_root: object
    enthalpy_residual_j_kg: float
    branch_evidence_id: str
    monotonicity_is_sampled_only: bool = True
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_INVERSE_ISSUERS:
            raise ValueError("Native mixture inverses must be issued by a converged provider solve")
        _PENDING_INVERSE_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        if (type(self.partition) is not MixturePhasePartition
                or not self.evaluations or self.evaluations[-1] is not self.partition
                or any(type(item) is not MixturePhasePartition for item in self.evaluations)):
            raise TypeError("A native mixture inverse must retain its provider-issued phase evaluations")
        self.partition.require_current()
        bounds = tuple(finite(value, "inverse quality bound") for value in self.quality_bounds)
        bracket = tuple(finite(value, "inverse bracket residual")
                        for value in self.bracket_residuals_j_kg)
        residual = finite(self.enthalpy_residual_j_kg, "inverse enthalpy residual")
        if (len(bounds) != 2 or not 0. <= bounds[0] < bounds[1] <= 1.
                or len(bracket) != 2 or abs(residual) > max(abs(value) for value in bracket)
                or getattr(self.native_root, "converged", False) is not True):
            raise ValueError("Native mixture inverse must retain a converged root inside its sampled branch")
        if not isinstance(self.branch_evidence_id, str) or not self.branch_evidence_id.strip():
            raise ValueError("Retain nonempty branch-selection evidence")
        object.__setattr__(self, "target_enthalpy_j_kg",
                           finite(self.target_enthalpy_j_kg, "target inverse enthalpy"))
        object.__setattr__(self, "enthalpy_residual_j_kg", residual)
        object.__setattr__(self, "quality_bounds", bounds)
        object.__setattr__(self, "bracket_residuals_j_kg", bracket)
        object.__setattr__(self, "evaluations", tuple(self.evaluations))
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        root = self.native_root
        root_values = tuple((name, getattr(root, name, None)) for name in (
            "converged", "iterations", "function_calls", "flag", "root"))
        return (id(self.partition), self.target_enthalpy_j_kg, self.quality_bounds,
                self.bracket_residuals_j_kg, tuple(id(item) for item in self.evaluations),
                id(root), root_values, self.enthalpy_residual_j_kg,
                self.branch_evidence_id, self.monotonicity_is_sampled_only)

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Native mixture inverse receipt changed after solver issuance")
        for partition in self.evaluations:
            partition.require_current()
        return self


@dataclass(frozen=True, slots=True)
class MixturePhaseAmounts:
    partition: object
    total_moles: float
    liquid_component_moles: tuple
    vapor_component_moles: tuple
    liquid_component_mass_kg: tuple
    vapor_component_mass_kg: tuple

    def __post_init__(self):
        if type(self.partition) is not MixturePhasePartition:
            raise TypeError("Finite phase amounts retain their typed native partition")
        self.partition.__post_init__()
        total = finite(self.total_moles, "total moles", positive=True)
        q = self.partition.vapor_mole_fraction
        liquid = tuple(total*(1.-q)*x for x in self.partition.liquid_mole_fractions)
        vapor = tuple(total*q*y for y in self.partition.vapor_mole_fractions)
        expected = (liquid, vapor,
            tuple(n*m for n, m in zip(liquid, self.partition.component_molar_masses_kg_mol, strict=True)),
            tuple(n*m for n, m in zip(vapor, self.partition.component_molar_masses_kg_mol, strict=True)))
        for name, target in zip(("liquid_component_moles", "vapor_component_moles",
                "liquid_component_mass_kg", "vapor_component_mass_kg"), expected, strict=True):
            values = tuple(finite(v, name) for v in getattr(self, name))
            if values != target:
                raise ValueError("Finite phase component amounts differ from their native partition")
            object.__setattr__(self, name, values)

    @property
    def total_mass_kg(self):
        return fsum((*self.liquid_component_mass_kg, *self.vapor_component_mass_kg))

    @property
    def component_moles(self):
        return tuple(a+b for a, b in zip(self.liquid_component_moles, self.vapor_component_moles, strict=True))

    @property
    def phase_volumes_m3(self):
        """Return phase volumes from native phase densities and retained masses.

        An absent phase has zero volume without requiring an endpoint density.
        An occupied phase with missing density fails closed. These are equilibrium
        packet volumes; they do not flash a vessel inventory or imply a holdup model.
        """
        self.__post_init__()
        masses = (fsum(self.liquid_component_mass_kg), fsum(self.vapor_component_mass_kg))
        densities = (self.partition.liquid_density_kg_m3,
                     self.partition.vapor_density_kg_m3)
        volumes = []
        for mass, density in zip(masses, densities, strict=True):
            if mass == 0.:
                volumes.append(0.)
            elif density is None:
                raise ValueError("Occupied native phase requires its density for volume accounting")
            else:
                volumes.append(finite(mass/density, "native phase volume", positive=True))
        return tuple(volumes)

    @property
    def phase_internal_energies_j(self):
        """Return phase U from native h, rho and the shared absolute pressure.

        The identity is u=h-p/rho on each admitted phase and the provider's
        energy-reference basis. Missing properties on an occupied phase reject.
        """
        self.__post_init__()
        masses = (fsum(self.liquid_component_mass_kg), fsum(self.vapor_component_mass_kg))
        enthalpies = (self.partition.liquid_enthalpy_j_kg,
                      self.partition.vapor_enthalpy_j_kg)
        densities = (self.partition.liquid_density_kg_m3,
                     self.partition.vapor_density_kg_m3)
        energies = []
        for mass, enthalpy, density in zip(masses, enthalpies, densities, strict=True):
            if mass == 0.:
                energies.append(0.)
            elif enthalpy is None or density is None:
                raise ValueError("Occupied native phase requires enthalpy and density for internal-energy accounting")
            else:
                specific_u = enthalpy-self.partition.state.pressure_pa/density
                energies.append(finite(mass*specific_u, "native phase internal energy"))
        return tuple(energies)

    @property
    def volume_residual_m3(self):
        """Compare summed phase volume with bulk mass/native density."""
        phase_volume = fsum(self.phase_volumes_m3)
        bulk_volume = self.total_mass_kg/self.partition.state.density_kg_m3
        return finite(phase_volume-bulk_volume, "native phase-volume residual")

    @property
    def total_internal_energy_j(self):
        """Return summed native phase U after per-phase property admission."""
        return fsum(self.phase_internal_energies_j)

    @property
    def internal_energy_residual_j(self):
        """Compare phase-resolved U with the bulk native state on the same mass basis."""
        bulk = self.total_mass_kg*self.partition.state.internal_energy_j_kg
        return finite(self.total_internal_energy_j-bulk,
                      "native phase-weighted internal-energy residual")


@dataclass(frozen=True, slots=True)
class MixtureInventoryStateAdmission:
    """Admit a native equilibrium packet against a finite V/U/species target.

    This value object does not solve a flash or advance a vessel. It checks that
    one fixed-overall-composition provider-issued phase packet closes
    caller-declared component moles, volume and internal energy before another
    module accepts that native result. It does not evolve composition.
    """

    provider: object = field(repr=False)
    partition: "MixturePhasePartition" = field(repr=False)
    total_component_moles: tuple[float, ...]
    target_internal_energy_j: float
    vessel_volume_m3: float
    component_mole_tolerance: float
    volume_absolute_tolerance_m3: float
    energy_absolute_tolerance_j: float
    evidence_id: str
    phase_amounts: MixturePhaseAmounts = field(init=False)
    component_mole_residuals: tuple[float, ...] = field(init=False)
    volume_residual_m3: float = field(init=False)
    internal_energy_residual_j: float = field(init=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def _payload(self):
        partition = self.partition
        state = partition.state
        state_values = tuple(getattr(state, name) for name in (
            "basis", "pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg",
            "internal_energy_j_kg", "entropy_j_kg_k", "phase", "cp_j_kg_k", "cv_j_kg_k",
            "viscosity_pa_s", "conductivity_w_m_k", "speed_of_sound_m_s",
            "vapor_mass_fraction", "raw_vapor_mass_fraction", "vapor_mole_fraction"))
        partition_values = tuple(getattr(partition, name) for name in (
            "composition_sha256", "species", "overall_mole_fractions", "liquid_mole_fractions",
            "vapor_mole_fractions", "component_molar_masses_kg_mol", "vapor_mole_fraction",
            "component_mole_balance_tolerance", "liquid_enthalpy_j_kg", "vapor_enthalpy_j_kg",
            "liquid_density_kg_m3", "vapor_density_kg_m3"))
        return (id(self.provider), id(partition.provider), id(partition._provider_token),
                self.provider.composition_sha256, self.provider.basis,
                tuple(self.provider.species), tuple(self.provider.mole_fractions),
                tuple(self.provider.coolprop_molar_masses_kg_mol), id(partition),
                state_values, partition_values, tuple(self.total_component_moles),
                self.target_internal_energy_j, self.vessel_volume_m3,
                self.component_mole_tolerance, self.volume_absolute_tolerance_m3,
                self.energy_absolute_tolerance_j, self.evidence_id)

    def _evaluate(self):
        from .coolprop_mixture import CoolPropMixtureProperties

        if type(self.provider) is not CoolPropMixtureProperties:
            raise TypeError("Use the fixed-composition native CoolProp mixture provider")
        if type(self.partition) is not MixturePhasePartition:
            raise TypeError("Retain a native MixturePhasePartition result")
        self.partition.__post_init__()
        if self.partition.provider is not self.provider:
            raise ValueError("Native phase partition was issued by a different provider object")
        self.provider.basis.require_compatible(self.partition.state.basis)
        if (self.partition.composition_sha256 != self.provider.composition_sha256
                or self.partition.species != tuple(self.provider.species)
                or self.partition.component_molar_masses_kg_mol
                   != tuple(self.provider.coolprop_molar_masses_kg_mol)):
            raise ValueError("Native phase packet does not belong to the retained provider composition")
        target = tuple(finite(value, "target component moles")
                       for value in self.total_component_moles)
        if (len(target) != len(self.provider.species) or any(value < 0. for value in target)
                or fsum(target) <= 0.):
            raise ValueError("Finite mixture inventory needs nonnegative species moles and positive total moles")
        tolerance = finite(self.component_mole_tolerance, "component mole tolerance", positive=True)
        volume_tolerance = finite(self.volume_absolute_tolerance_m3,
                                  "volume absolute tolerance", positive=True)
        energy_tolerance = finite(self.energy_absolute_tolerance_j,
                                  "internal-energy absolute tolerance", positive=True)
        target_volume = finite(self.vessel_volume_m3, "vessel volume", positive=True)
        target_energy = finite(self.target_internal_energy_j, "target internal energy")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare source/branch evidence for the inventory admission")
        amounts = self.partition.split_moles(fsum(target))
        residuals = tuple(expected-observed for expected, observed in zip(
            target, amounts.component_moles, strict=True))
        if any(abs(value) > tolerance for value in residuals):
            raise ValueError("Native phase packet does not close target component mole inventories")
        volume_residual = finite(fsum(amounts.phase_volumes_m3)-target_volume,
                                 "finite inventory volume residual")
        energy_residual = finite(amounts.total_internal_energy_j-target_energy,
                                 "finite inventory internal-energy residual")
        if abs(volume_residual) > volume_tolerance:
            raise ValueError("Native phase packet does not close the fixed vessel volume")
        if abs(energy_residual) > energy_tolerance:
            raise ValueError("Native phase packet does not close target internal energy")
        return target, amounts, residuals, volume_residual, energy_residual

    def _require_seal(self):
        try:
            current = self._payload()
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("Mixture inventory admission lost its native source binding") from error
        if not self._seal or current != self._seal:
            raise ValueError("Mixture inventory admission changed after native source binding")

    def __post_init__(self):
        if self._seal:
            self._require_seal()
        target, amounts, residuals, volume_residual, energy_residual = self._evaluate()
        object.__setattr__(self, "total_component_moles", target)
        object.__setattr__(self, "phase_amounts", amounts)
        object.__setattr__(self, "component_mole_residuals", residuals)
        object.__setattr__(self, "volume_residual_m3", volume_residual)
        object.__setattr__(self, "internal_energy_residual_j", energy_residual)
        if not self._seal:
            object.__setattr__(self, "_seal", self._payload())

    def require_current(self):
        self._require_seal()
        target, amounts, residuals, volume_residual, energy_residual = self._evaluate()
        if (amounts != self.phase_amounts or target != self.total_component_moles
                or residuals != self.component_mole_residuals
                or volume_residual != self.volume_residual_m3
                or energy_residual != self.internal_energy_residual_j):
            raise ValueError("Mixture inventory admission summary differs from its retained packet")
        return self


@dataclass(frozen=True, slots=True)
class MixturePhasePartition:
    state: object
    composition_sha256: str
    species: tuple
    overall_mole_fractions: tuple
    liquid_mole_fractions: tuple
    vapor_mole_fractions: tuple
    component_molar_masses_kg_mol: tuple
    vapor_mole_fraction: float
    component_mole_balance_tolerance: float
    liquid_enthalpy_j_kg: float | None = None
    vapor_enthalpy_j_kg: float | None = None
    liquid_density_kg_m3: float | None = None
    vapor_density_kg_m3: float | None = None
    provider: object = field(default=None, repr=False, compare=False)
    _provider_token: object = field(default=None, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def _payload(self):
        state_values = tuple(getattr(self.state, name) for name in (
            "basis", "pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg",
            "internal_energy_j_kg", "entropy_j_kg_k", "phase", "cp_j_kg_k", "cv_j_kg_k",
            "viscosity_pa_s", "conductivity_w_m_k", "speed_of_sound_m_s",
            "vapor_mass_fraction", "raw_vapor_mass_fraction", "vapor_mole_fraction"))
        return (
            id(self.provider), id(self._provider_token), id(self.state), state_values,
            self.composition_sha256, tuple(self.species), tuple(self.overall_mole_fractions),
            tuple(self.liquid_mole_fractions), tuple(self.vapor_mole_fractions),
            tuple(self.component_molar_masses_kg_mol), self.vapor_mole_fraction,
            self.component_mole_balance_tolerance, self.liquid_enthalpy_j_kg,
            self.vapor_enthalpy_j_kg, self.liquid_density_kg_m3, self.vapor_density_kg_m3,
            self.provider.composition_sha256, self.provider.basis,
            tuple(self.provider.species), tuple(self.provider.mole_fractions),
            tuple(self.provider.coolprop_molar_masses_kg_mol),
        )

    def _require_current(self):
        try:
            current = self._payload()
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("Native phase partition lost its provider/state binding") from error
        if not self._seal or current != self._seal:
            raise ValueError("Native phase partition changed after provider issuance")

    def __post_init__(self):
        from .coolprop_mixture import CoolPropMixtureProperties, MixtureThermoState

        if self._seal:
            self._require_current()
        else:
            token = self._issuer_token
            if (token not in _PENDING_PARTITION_ISSUERS
                    or type(self.provider) is not CoolPropMixtureProperties):
                raise ValueError("Native phase partitions must be issued by a CoolProp mixture flash")
            _PENDING_PARTITION_ISSUERS.remove(token)
            object.__setattr__(self, "_issuer_token", None)

        if type(self.state) is not MixtureThermoState:
            raise TypeError("Retain the actual native mixture-state contract")
        if (type(self.provider) is not CoolPropMixtureProperties
                or self._provider_token is not self.provider._partition_token):
            raise ValueError("Native phase partition must retain its issuing CoolProp provider token")
        self.state.__post_init__()
        self.provider.basis.require_compatible(self.state.basis)
        if (self.composition_sha256 != self.provider.composition_sha256
                or tuple(self.species) != tuple(self.provider.species)
                or tuple(self.component_molar_masses_kg_mol)
                   != tuple(self.provider.coolprop_molar_masses_kg_mol)):
            raise ValueError("Native phase partition differs from its issuing provider composition")
        for name in ("liquid_enthalpy_j_kg", "vapor_enthalpy_j_kg",
                     "liquid_density_kg_m3", "vapor_density_kg_m3"):
            value = getattr(self, name)
            if value is not None:
                finite(value, name, positive="density" in name)
        if self.state.phase != "two_phase" or self.state.vapor_mass_fraction is not None:
            raise ValueError("Phase partition needs two-phase native mole-quality semantics")
        if (not isinstance(self.composition_sha256, str) or len(self.composition_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.composition_sha256)):
            raise ValueError("Retain the lowercase native composition SHA-256")
        names = tuple(self.species)
        if (not names or any(not isinstance(name, str) or not name.strip() for name in names)
                or len(set(names)) != len(names)):
            raise ValueError("Phase partition needs ordered unique species identities")
        for name in ("overall_mole_fractions", "liquid_mole_fractions", "vapor_mole_fractions"):
            values = tuple(finite(value, name) for value in getattr(self, name))
            if len(values) != len(names) or any(value < 0. or value > 1. for value in values):
                raise ValueError("Native phase fractions must match declared species")
            if not isclose(fsum(values), 1., abs_tol=1e-10, rel_tol=0.):
                raise ValueError("Native phase mole fractions must be normalized")
            object.__setattr__(self, name, values)
        masses = tuple(finite(value, "component molar mass", positive=True)
                       for value in self.component_molar_masses_kg_mol)
        if len(masses) != len(names):
            raise ValueError("Every phase component needs its native molar mass")
        object.__setattr__(self, "species", names)
        object.__setattr__(self, "component_molar_masses_kg_mol", masses)
        quality = finite(self.vapor_mole_fraction, "native vapor mole fraction")
        tolerance = finite(self.component_mole_balance_tolerance, "component balance tolerance", positive=True)
        if not 0. <= quality <= 1.:
            raise ValueError("Native vapor mole fraction must be in [0, 1]")
        if self.state.vapor_mole_fraction != quality:
            raise ValueError("Retained native state and partition quality differ")
        component_balance_residuals = tuple(
            z-((1.-quality)*x+quality*y)
            for z, x, y in zip(self.overall_mole_fractions, self.liquid_mole_fractions,
                               self.vapor_mole_fractions, strict=True)
        )
        if any(abs(residual) > tolerance for residual in component_balance_residuals):
            detail = "; ".join(
                f"{name}: z={overall:.17g}, xL={liquid:.17g}, "
                f"yV={vapor:.17g}, residual={residual:.17g}"
                for name, overall, liquid, vapor, residual in zip(
                    names, self.overall_mole_fractions, self.liquid_mole_fractions,
                    self.vapor_mole_fractions, component_balance_residuals, strict=True)
            )
            raise ValueError(
                "Native liquid/vapor compositions do not reproduce total component moles "
                f"at vapor mole quality {quality:.17g} (absolute tolerance {tolerance:.17g}): {detail}"
            )
        if not self._seal:
            object.__setattr__(self, "_seal", self._payload())

    def require_current(self):
        self.__post_init__()
        return self

    @property
    def liquid_molar_mass_kg_mol(self):
        return fsum(x*m for x, m in zip(self.liquid_mole_fractions, self.component_molar_masses_kg_mol, strict=True))

    @property
    def vapor_molar_mass_kg_mol(self):
        return fsum(y*m for y, m in zip(self.vapor_mole_fractions, self.component_molar_masses_kg_mol, strict=True))

    @property
    def vapor_mass_fraction(self):
        q = self.vapor_mole_fraction
        return q*self.vapor_molar_mass_kg_mol/(
            (1.-q)*self.liquid_molar_mass_kg_mol+q*self.vapor_molar_mass_kg_mol)

    def split_moles(self, total_moles):
        """Partition a finite molar amount using retained native phase composition.

        Component residuals follow the admitted VLE tolerance; no component is
        adjusted to force exact closure or modify the native phase equilibrium.
        """
        self.__post_init__()
        total = finite(total_moles, "total moles", positive=True)
        q = self.vapor_mole_fraction
        liquid = tuple(total*(1.-q)*x for x in self.liquid_mole_fractions)
        vapor = tuple(total*q*y for y in self.vapor_mole_fractions)
        return MixturePhaseAmounts(self, total, liquid, vapor,
            tuple(n*m for n, m in zip(liquid, self.component_molar_masses_kg_mol, strict=True)),
            tuple(n*m for n, m in zip(vapor, self.component_molar_masses_kg_mol, strict=True)))

    def split_mass(self, total_mass_kg):
        """Partition a finite mass on the actual admitted native phase mixture.

        Conversion uses phase-weighted molar mass, preserving the selected VLE
        partition without silently correcting its finite component residuals.
        """
        mass = finite(total_mass_kg, "total mass", positive=True)
        q = self.vapor_mole_fraction
        molar_mass = (1.-q)*self.liquid_molar_mass_kg_mol+q*self.vapor_molar_mass_kg_mol
        return self.split_moles(mass/molar_mass)

    def withdraw_component_moles(self, liquid_component_moles, vapor_component_moles,
                                 liquid_total_moles, vapor_total_moles, *,
                                 liquid_withdrawal_moles=0., vapor_withdrawal_moles=0.):
        """Withdraw from each phase's actual current composition and retain residual stock.

        This accounting primitive deliberately does not flash the combined residual
        inventory. A vessel's changing-inventory EOS flash and phase events require
        the receiving native separator requested separately.
        """
        from math import fsum

        liquid = tuple(finite(value, "liquid component stock") for value in liquid_component_moles)
        vapor = tuple(finite(value, "vapor component stock") for value in vapor_component_moles)
        if (len(liquid) != len(self.species) or len(vapor) != len(self.species)
                or any(value < 0. for value in liquid+vapor)):
            raise ValueError("Phase component stocks must be nonnegative and match the native species order")
        liquid_total = finite(liquid_total_moles, "liquid phase moles")
        vapor_total = finite(vapor_total_moles, "vapor phase moles")
        if liquid_total < 0. or vapor_total < 0. or liquid_total+vapor_total <= 0.:
            raise ValueError("Phase inventories must be nonnegative with positive combined stock")
        molar_tolerance = max(self.component_mole_balance_tolerance, 1e-12)*max(liquid_total, vapor_total, 1.)
        if (abs(fsum(liquid)-liquid_total) > molar_tolerance
                or abs(fsum(vapor)-vapor_total) > molar_tolerance):
            raise ValueError("Declared phase component inventories do not match phase total moles")
        total_moles = liquid_total+vapor_total
        declared_quality = vapor_total/total_moles
        quality_tolerance = max(self.component_mole_balance_tolerance, 1e-12)
        if abs(declared_quality-self.vapor_mole_fraction) > quality_tolerance:
            raise ValueError("Phase totals do not match the retained native mole quality")
        expected_liquid = (tuple(liquid_total*x for x in self.liquid_mole_fractions)
                           if liquid_total > 0. else (0.,)*len(self.species))
        expected_vapor = (tuple(vapor_total*y for y in self.vapor_mole_fractions)
                          if vapor_total > 0. else (0.,)*len(self.species))
        if (any(abs(actual-expected) > molar_tolerance for actual, expected in
                    zip(liquid, expected_liquid, strict=True))
                or any(abs(actual-expected) > molar_tolerance for actual, expected in
                    zip(vapor, expected_vapor, strict=True))):
            raise ValueError("Current phase inventories do not match the retained native equilibrium compositions")
        out_l = finite(liquid_withdrawal_moles, "liquid withdrawal")
        out_v = finite(vapor_withdrawal_moles, "vapor withdrawal")
        if not 0. <= out_l <= liquid_total or not 0. <= out_v <= vapor_total:
            raise ValueError("Phase withdrawals must remain within their own current inventories")
        liquid_out = (tuple(out_l*x for x in self.liquid_mole_fractions)
                      if liquid_total > 0. else (0.,)*len(self.species))
        vapor_out = (tuple(out_v*y for y in self.vapor_mole_fractions)
                     if vapor_total > 0. else (0.,)*len(self.species))
        liquid_left = tuple(stock-out for stock, out in zip(liquid, liquid_out, strict=True))
        vapor_left = tuple(stock-out for stock, out in zip(vapor, vapor_out, strict=True))
        residuals = tuple(a+b-c-d for a,b,c,d in zip(liquid, vapor, liquid_left, vapor_left, strict=True))
        if any(abs(value-(lo+vo)) > 1e-12*max(liquid_total, vapor_total, 1.) for value,lo,vo in zip(
                residuals, liquid_out, vapor_out, strict=True)):
            raise ValueError("Phase-specific withdrawal failed component conservation")
        return MixturePhaseWithdrawal(self, liquid, vapor, liquid_out, vapor_out,
            liquid_left, vapor_left, (self.liquid_enthalpy_j_kg, self.vapor_enthalpy_j_kg))


@dataclass(frozen=True, slots=True)
class MixturePhaseWithdrawal:
    """Current-phase selective component withdrawal accounting receipt."""

    partition: MixturePhasePartition
    liquid_component_moles_before: tuple
    vapor_component_moles_before: tuple
    liquid_component_moles_out: tuple
    vapor_component_moles_out: tuple
    liquid_component_moles_after: tuple
    vapor_component_moles_after: tuple
    phase_enthalpies_j_kg: tuple

    def __post_init__(self):
        if type(self.partition) is not MixturePhasePartition:
            raise TypeError("Withdrawal must retain its native phase partition")
        self.partition.__post_init__()
        for name in ("liquid_component_moles_before", "vapor_component_moles_before",
                     "liquid_component_moles_out", "vapor_component_moles_out",
                     "liquid_component_moles_after", "vapor_component_moles_after"):
            values = tuple(finite(value, name) for value in getattr(self, name))
            if len(values) != len(self.partition.species) or any(value < 0. for value in values):
                raise ValueError("Withdrawal vectors must be nonnegative and match retained species")
            object.__setattr__(self, name, values)
        for before, out, after in zip(self.liquid_component_moles_before,
                self.liquid_component_moles_out, self.liquid_component_moles_after, strict=True):
            if not isclose(before, out+after, rel_tol=0., abs_tol=1e-12):
                raise ValueError("Liquid component withdrawal does not conserve inventory")
        for before, out, after in zip(self.vapor_component_moles_before,
                self.vapor_component_moles_out, self.vapor_component_moles_after, strict=True):
            if not isclose(before, out+after, rel_tol=0., abs_tol=1e-12):
                raise ValueError("Vapor component withdrawal does not conserve inventory")
        liquid_total = fsum(self.liquid_component_moles_before)
        vapor_total = fsum(self.vapor_component_moles_before)
        combined = liquid_total+vapor_total
        if combined <= 0.:
            raise ValueError("A phase-withdrawal receipt must retain positive combined stock")
        tolerance = max(self.partition.component_mole_balance_tolerance, 1e-12)*max(combined, 1.)
        if abs(vapor_total/combined-self.partition.vapor_mole_fraction) > max(
                self.partition.component_mole_balance_tolerance, 1e-12):
            raise ValueError("Withdrawal stock totals do not match retained native mole quality")
        for before, out, fractions, label in (
                (self.liquid_component_moles_before, self.liquid_component_moles_out,
                 self.partition.liquid_mole_fractions, "liquid"),
                (self.vapor_component_moles_before, self.vapor_component_moles_out,
                 self.partition.vapor_mole_fractions, "vapor")):
            phase_total = fsum(before)
            withdrawn_total = fsum(out)
            for stock, withdrawal, fraction in zip(before, out, fractions, strict=True):
                expected_stock = phase_total*fraction if phase_total > 0. else 0.
                expected_withdrawal = withdrawn_total*fraction if phase_total > 0. else 0.
                if (abs(stock-expected_stock) > tolerance
                        or abs(withdrawal-expected_withdrawal) > tolerance):
                    raise ValueError(
                        f"{label.title()} receipt does not preserve its retained native phase composition"
                    )
        enthalpies = tuple(self.phase_enthalpies_j_kg)
        if len(enthalpies) != 2:
            raise ValueError("Retain liquid and vapor outlet enthalpies separately")
        for value in enthalpies:
            if value is not None:
                finite(value, "native phase outlet enthalpy")
        if enthalpies != (self.partition.liquid_enthalpy_j_kg,
                          self.partition.vapor_enthalpy_j_kg):
            raise ValueError("Withdrawal enthalpies differ from the retained native phase partition")
        object.__setattr__(self, "phase_enthalpies_j_kg", enthalpies)

    @property
    def liquid_component_mass_out_kg(self):
        """Component-resolved mass removed from the current liquid phase."""
        return tuple(n*m for n, m in zip(
            self.liquid_component_moles_out,
            self.partition.component_molar_masses_kg_mol, strict=True))

    @property
    def vapor_component_mass_out_kg(self):
        """Component-resolved mass removed from the current vapor phase."""
        return tuple(n*m for n, m in zip(
            self.vapor_component_moles_out,
            self.partition.component_molar_masses_kg_mol, strict=True))

    @property
    def phase_mass_out_kg(self):
        """Liquid and vapor withdrawal masses, in the retained species order."""
        return (fsum(self.liquid_component_mass_out_kg),
                fsum(self.vapor_component_mass_out_kg))

    @property
    def phase_enthalpy_out_j(self):
        """Per-phase enthalpy carried by withdrawals, or ``None`` if unavailable.

        This is boundary bookkeeping using the retained native phase specific
        enthalpies (J/kg). It does not flash the residual component inventory.
        """
        result = []
        for mass, enthalpy in zip(self.phase_mass_out_kg,
                                  self.phase_enthalpies_j_kg, strict=True):
            if mass == 0.:
                result.append(0.)
            elif enthalpy is None:
                result.append(None)
            else:
                result.append(finite(mass*enthalpy, "phase withdrawal enthalpy"))
        return tuple(result)

    @property
    def total_enthalpy_out_j(self):
        """Total withdrawal enthalpy, unavailable if a nonzero phase lacks it."""
        values = self.phase_enthalpy_out_j
        if any(value is None for value in values):
            return None
        return fsum(values)
