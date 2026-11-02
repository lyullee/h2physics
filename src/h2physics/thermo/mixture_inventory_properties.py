"""Explicit bounded native mixture property facade for finite inventories."""

from dataclasses import dataclass, field

from ..core import finite
from .coolprop_mixture import CoolPropMixtureProperties


@dataclass(frozen=True, slots=True)
class BoundedMixtureInventoryProperties:
    provider: CoolPropMixtureProperties
    pressure_bounds_pa: tuple
    branch_evidence_id: str
    density_absolute_tolerance_kg_m3: float
    internal_energy_absolute_tolerance_j_kg: float
    pressure_absolute_tolerance_pa: float
    branch_samples: int = 9
    maximum_iterations: int = 100
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _last_inverse: object = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.provider) is not CoolPropMixtureProperties:
            raise TypeError("Wrap the original immutable fixed-composition CoolProp provider")
        bounds = tuple(finite(p, "pressure bound", positive=True) for p in self.pressure_bounds_pa)
        if len(bounds) != 2 or bounds[0] >= bounds[1]:
            raise ValueError("Declare increasing pressure bounds for native inventory inversion")
        if self.provider.inverse_temperature_bounds_k is None:
            raise ValueError("Configure the original provider's temperature branch before wrapping it")
        if not isinstance(self.branch_evidence_id, str) or not self.branch_evidence_id.strip():
            raise ValueError("Declare evidence for the finite-inventory inverse branch")
        for name in ("density_absolute_tolerance_kg_m3", "internal_energy_absolute_tolerance_j_kg",
                     "pressure_absolute_tolerance_pa"):
            finite(getattr(self, name), name, positive=True)
        if type(self.branch_samples) is not int or self.branch_samples < 3:
            raise ValueError("At least three branch samples are required")
        if type(self.maximum_iterations) is not int or self.maximum_iterations <= 0:
            raise ValueError("Declare a positive inverse iteration limit")
        object.__setattr__(self, "pressure_bounds_pa", bounds)
        object.__setattr__(self, "_binding", self._payload())

    def _payload(self):
        return (id(self.provider), self.provider.basis, self.provider.composition_sha256,
                self.provider.inverse_temperature_bounds_k, self.pressure_bounds_pa,
                self.branch_evidence_id, self.density_absolute_tolerance_kg_m3,
                self.internal_energy_absolute_tolerance_j_kg, self.pressure_absolute_tolerance_pa,
                self.branch_samples, self.maximum_iterations)

    def require_current(self):
        if self._payload() != self._binding:
            raise ValueError("Bounded inventory provider lost its original composition or inverse configuration")
        return self

    @property
    def basis(self):
        self.require_current()
        return self.provider.basis

    @property
    def backend(self):
        self.require_current()
        return self.provider.backend

    @property
    def composition_id(self):
        self.require_current()
        return self.provider.composition_id

    @property
    def species(self):
        self.require_current()
        return self.provider.species

    @property
    def mole_fractions(self):
        self.require_current()
        return self.provider.mole_fractions

    @property
    def molar_masses_kg_mol(self):
        self.require_current()
        return self.provider.molar_masses_kg_mol

    @property
    def last_inverse(self):
        """Most recent instance-wide successful diagnostic; no growing history.

        Native evaluations are protected by the original provider's lock. Use a
        separate facade per concurrent trajectory when attribution of this one
        diagnostic slot matters; it is not a per-thread result history.
        """
        self.require_current()
        return self._last_inverse

    def state_rho_u(self, density_kg_m3, internal_energy_j_kg):
        self.require_current()
        # Clear old success before evaluation so a failed native call cannot
        # leave a misleading successful receipt attached to the latest request.
        object.__setattr__(self, "_last_inverse", None)
        result = self.provider.state_rho_u_bounded(density_kg_m3, internal_energy_j_kg,
            pressure_bounds_pa=self.pressure_bounds_pa, branch_evidence_id=self.branch_evidence_id,
            density_absolute_tolerance_kg_m3=self.density_absolute_tolerance_kg_m3,
            internal_energy_absolute_tolerance_j_kg=self.internal_energy_absolute_tolerance_j_kg,
            pressure_absolute_tolerance_pa=self.pressure_absolute_tolerance_pa,
            branch_samples=self.branch_samples, maximum_iterations=self.maximum_iterations)
        self.require_current()
        object.__setattr__(self, "_last_inverse", result)
        return result.state

    def state_pt(self, pressure_pa, temperature_k):
        self.require_current()
        return self.provider.state_pt(pressure_pa, temperature_k)

    def state_ph(self, pressure_pa, enthalpy_j_kg):
        self.require_current()
        return self.provider.state_ph(pressure_pa, enthalpy_j_kg)

    def state_ps(self, pressure_pa, entropy_j_kg_k):
        self.require_current()
        return self.provider.state_ps(pressure_pa, entropy_j_kg_k)

    def state_prho(self, pressure_pa, density_kg_m3):
        self.require_current()
        return self.provider.state_prho(pressure_pa, density_kg_m3)

    def state_pu(self, pressure_pa, internal_energy_j_kg):
        self.require_current()
        return self.provider.state_pu(pressure_pa, internal_energy_j_kg)
