"""Single-flash HEOS states exposed through a tested subset of the native API.

This is a property-interface adapter, not another equation of state or an
automatic fallback. Native components and their integrators remain unchanged.
"""

from collections.abc import Callable
from typing import Any

from ..thermo.coolprop import CoolPropProperties
from .lh2dt import from_lh2dt_state, to_lh2dt_state


class Lh2dtLowLevelProperties:
    """Native equipment facade over one protected h2physics HEOS provider.

    The actual native state factory is injected. Unsupported native methods
    remain absent; no hidden call to a second property implementation is made.
    This tested subset supports the checked tank/pipe/pump/vaporizer/network.
    """

    _IDENTITY_FIELDS = frozenset({"provider", "state_factory", "fluid", "basis", "_provider_binding"})

    def __setattr__(self, name, value):
        if getattr(self, "_provider_binding", None) is not None and name in self._IDENTITY_FIELDS:
            raise AttributeError("Native property provider identity and state factory are immutable")
        object.__setattr__(self, name, value)

    def __init__(self, properties: CoolPropProperties, *, state_factory: Callable[..., Any]):
        if properties.backend != "HEOS":
            raise ValueError("Native cryogenic equipment requires the reference HEOS path here")
        self.provider, self.state_factory = properties, state_factory
        self.fluid, self.basis = properties.basis.fluid, properties.basis
        self.maximum_quality_adjustment = 0.
        self.quality_adjustment_count = 0
        self.last_adjusted_state = None
        self._provider_binding = self._configuration()

    def _configuration(self):
        provider = self.provider
        current = getattr(provider, "require_current", None)
        if callable(current):
            current()
        native = getattr(provider, "provider", provider)
        native_state = getattr(native, "_state", None)
        backend_name = getattr(native_state, "backend_name", None)
        fluid_names = getattr(native_state, "fluid_names", None)
        return (
            id(provider), id(native), self.fluid, self.basis,
            getattr(provider, "backend", None), getattr(provider, "version", None),
            getattr(provider, "composition_sha256", None),
            getattr(provider, "internal_energy_policy", None),
            getattr(provider, "quality_roundoff_tolerance", None),
            id(native_state), id(getattr(native, "_cp", None)), id(self.state_factory),
            backend_name() if callable(backend_name) else backend_name,
            tuple(fluid_names()) if callable(fluid_names) else fluid_names,
        )

    def require_current(self):
        if self._configuration() != self._provider_binding:
            raise ValueError("Native property facade no longer matches its admitted provider")
        return self

    def _state(self, method, *args):
        self.require_current()
        try:
            state = method(*args)
        except Exception:
            self.require_current()
            raise
        self.require_current()
        return self._native(state)

    def _native(self, state):
        self.require_current()
        if state.raw_vapor_mass_fraction is not None:
            self.maximum_quality_adjustment = max(self.maximum_quality_adjustment,
                abs(state.raw_vapor_mass_fraction-state.vapor_mass_fraction))
            self.quality_adjustment_count += 1
            self.last_adjusted_state = state
        converted = to_lh2dt_state(state, expected_basis=self.basis, factory=self.state_factory)
        self.require_current()
        return converted

    def from_pT(self, pressure_Pa, temperature_K):
        return self._state(self.provider.state_pt, pressure_Pa, temperature_K)

    def from_ph(self, pressure_Pa, specific_enthalpy_J_kg):
        return self._state(self.provider.state_ph, pressure_Pa, specific_enthalpy_J_kg)

    def from_ps(self, pressure_Pa, specific_entropy_J_kgK):
        return self._state(self.provider.state_ps, pressure_Pa, specific_entropy_J_kgK)

    def from_pu(self, pressure_Pa, specific_internal_energy_J_kg):
        return self._state(self.provider.state_pu, pressure_Pa, specific_internal_energy_J_kg)

    def from_rho_u(self, density_kg_m3, specific_internal_energy_J_kg):
        return self._state(self.provider.state_rho_u, density_kg_m3, specific_internal_energy_J_kg)

    def from_prho(self, pressure_Pa, density_kg_m3):
        return self._state(self.provider.state_prho, pressure_Pa, density_kg_m3)

    def saturated_liquid(self, pressure_Pa):
        return self._state(self.provider.saturated, pressure_Pa, 0.)

    def saturated_vapor(self, pressure_Pa):
        return self._state(self.provider.saturated, pressure_Pa, 1.)

    def saturation_pressure_Pa(self, temperature_K):
        self.require_current()
        try:
            value = self.provider.saturated_at_temperature(temperature_K, 0.).pressure_pa
        except Exception:
            self.require_current()
            raise
        self.require_current()
        return value

    def viscosity_Pa_s(self, state):
        self.require_current()
        native_state = from_lh2dt_state(state, basis=self.basis)
        try:
            value = self.provider.phase_viscosity(native_state)
        except Exception:
            self.require_current()
            raise
        self.require_current()
        return value
