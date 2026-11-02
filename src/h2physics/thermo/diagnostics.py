"""Derived state diagnostics that keep EOS and transport ownership explicit.

This module reports dimensionless/state-derived quantities only. It does not
provide an equation of state, transport correlation, or discharge closure.
"""

import hashlib
from dataclasses import dataclass, field

from ..core import ThermoState, finite

_SINGLE_PHASE_GAS = frozenset({"gas", "supercritical", "supercritical_gas"})


@dataclass(frozen=True, slots=True)
class GasStateDiagnostics:
    """Derived quantities from one gas-phase state and caller-supplied R.

    Missing transport/heat-capacity fields remain ``None``. The specific gas
    constant is explicit so mixture composition and mass basis are never
    inferred from a display name.
    """

    state: ThermoState
    specific_gas_constant_j_kg_k: float
    compressibility_factor: float = field(init=False)
    heat_capacity_ratio: float | None = field(init=False)
    prandtl_number: float | None = field(init=False)
    thermal_diffusivity_m2_s: float | None = field(init=False)
    kinematic_viscosity_m2_s: float | None = field(init=False)
    _state_signature: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.state, ThermoState):
            raise TypeError("Gas diagnostics require a typed ThermoState")
        if self.state.phase not in _SINGLE_PHASE_GAS:
            raise ValueError("Gas diagnostics require an admitted single-phase gas state")
        gas_constant = finite(self.specific_gas_constant_j_kg_k,
                              "specific gas constant", positive=True)
        z = finite(self.state.pressure_pa /
                   (self.state.density_kg_m3 * gas_constant * self.state.temperature_k),
                   "compressibility factor", positive=True)
        gamma = self.state.heat_capacity_ratio
        mu, conductivity, cp = (self.state.viscosity_pa_s,
                                self.state.conductivity_w_m_k,
                                self.state.cp_j_kg_k)
        prandtl = (mu * cp / conductivity
                   if mu is not None and cp is not None and conductivity is not None else None)
        alpha = (conductivity / (self.state.density_kg_m3 * cp)
                 if conductivity is not None and cp is not None else None)
        nu = mu / self.state.density_kg_m3 if mu is not None else None
        if gamma is not None:
            gamma = finite(gamma, "heat-capacity ratio", positive=True)
            if self.state.cv_j_kg_k is None or self.state.cp_j_kg_k is None:
                raise ValueError("Heat-capacity ratio requires both retained cp and cv")
            if not gamma == self.state.cp_j_kg_k / self.state.cv_j_kg_k:
                raise ValueError("Heat-capacity ratio no longer matches the retained state")
        if prandtl is not None:
            prandtl = finite(prandtl, "Prandtl number", positive=True)
        if alpha is not None:
            alpha = finite(alpha, "thermal diffusivity", positive=True)
        if nu is not None:
            nu = finite(nu, "kinematic viscosity", positive=True)
        object.__setattr__(self, "specific_gas_constant_j_kg_k", gas_constant)
        object.__setattr__(self, "compressibility_factor", z)
        object.__setattr__(self, "heat_capacity_ratio", gamma)
        object.__setattr__(self, "prandtl_number", prandtl)
        object.__setattr__(self, "thermal_diffusivity_m2_s", alpha)
        object.__setattr__(self, "kinematic_viscosity_m2_s", nu)
        object.__setattr__(self, "_state_signature", self._signature())

    def _signature(self) -> str:
        payload = (self.state, self.specific_gas_constant_j_kg_k,
                   self.compressibility_factor, self.heat_capacity_ratio,
                   self.prandtl_number, self.thermal_diffusivity_m2_s,
                   self.kinematic_viscosity_m2_s)
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def require_current(self):
        """Reject a modified state or derived diagnostic before downstream use."""
        expected_z = self.state.pressure_pa / (
            self.state.density_kg_m3 * self.specific_gas_constant_j_kg_k
            * self.state.temperature_k
        )
        if not self._state_signature or self._signature() != self._state_signature:
            raise RuntimeError("Gas-state diagnostic fields changed after construction")
        expected_gamma = self.state.heat_capacity_ratio
        mu = self.state.viscosity_pa_s
        conductivity = self.state.conductivity_w_m_k
        cp = self.state.cp_j_kg_k
        expected_prandtl = (mu * cp / conductivity
                            if mu is not None and cp is not None and conductivity is not None else None)
        expected_alpha = (conductivity / (self.state.density_kg_m3 * cp)
                          if conductivity is not None and cp is not None else None)
        expected_nu = mu / self.state.density_kg_m3 if mu is not None else None
        if (self.compressibility_factor != expected_z
                or self.heat_capacity_ratio != expected_gamma
                or self.prandtl_number != expected_prandtl
                or self.thermal_diffusivity_m2_s != expected_alpha
                or self.kinematic_viscosity_m2_s != expected_nu):
            raise RuntimeError("Gas-state diagnostic no longer matches its source state")
        return self

    @classmethod
    def from_state(cls, state: ThermoState, *, specific_gas_constant_j_kg_k: float):
        """Build diagnostics without inferring composition or filling missing data."""
        if not isinstance(state, ThermoState):
            raise TypeError("Gas diagnostics require a typed ThermoState")
        if state.phase not in _SINGLE_PHASE_GAS:
            raise ValueError("Gas diagnostics require an admitted single-phase gas state")
        gas_constant = finite(specific_gas_constant_j_kg_k,
                              "specific gas constant", positive=True)
        return cls(state, gas_constant)
