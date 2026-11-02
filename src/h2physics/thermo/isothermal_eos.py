"""Single-phase isothermal EOS closure for compressible-flow models.

Characteristic speed is derived from the isothermal pressure-density
derivative. This API deliberately never substitutes CoolProp's adiabatic
speed-of-sound property.
"""

from __future__ import annotations

import math
import threading
from typing import Protocol

from ..core import finite


class IsothermalSinglePhaseEOS(Protocol):
    """Mass-basis pressure, density and isothermal acoustic closure (SI units)."""

    @property
    def identity(self) -> str: ...

    def density_pt(self, p_pa: float, t_k: float) -> float: ...

    def pressure_rho_t(self, rho_kg_m3: float, t_k: float) -> float: ...

    def isothermal_sound_speed_rho_t(self, rho_kg_m3: float, t_k: float) -> float: ...


class CoolPropIsothermalEOS:
    """Lazy HEOS-backed homogeneous-phase closure for one pure fluid.

    The fluid string and installed CoolProp version are retained as identity.
    Saturated/two-phase and unclassified states are rejected. Density and
    pressure use mass-basis input pairs. The isothermal characteristic speed
    follows c_T = sqrt((∂p/∂ρ)_T) = sqrt(1/(ρ κ_T)).
    """

    def __init__(self, fluid: str = "Hydrogen", *, backend: str = "HEOS"):
        if (not isinstance(fluid, str) or not fluid.strip()
                or "&" in fluid or "[" in fluid or "]" in fluid):
            raise ValueError("Declare one CoolProp pure-fluid identifier, not an unresolved mixture")
        if backend != "HEOS":
            raise ValueError("Isothermal derivative closure currently admits only the direct HEOS backend")
        try:
            import CoolProp
            import CoolProp.CoolProp as cp
        except ImportError as error:
            raise ImportError("Install h2physics[thermo] to use CoolPropIsothermalEOS") from error
        self.fluid = fluid.strip()
        self.backend = backend
        self.version = CoolProp.__version__
        self._cp = cp
        self._state = CoolProp.AbstractState(backend, self.fluid)
        self._lock = threading.RLock()
        self._allowed_phases = frozenset((
            cp.iphase_gas,
            cp.iphase_supercritical_gas,
            cp.iphase_supercritical,
        ))

    @property
    def identity(self) -> str:
        return f"CoolProp:{self.version}:{self.backend}:{self.fluid}:isothermal-homogeneous"

    def _update_pt(self, p_pa: float, t_k: float):
        self._state.update(
            self._cp.PT_INPUTS,
            finite(p_pa, "pressure Pa", positive=True),
            finite(t_k, "temperature K", positive=True),
        )
        self._require_homogeneous_gas()

    def _update_rho_t(self, rho_kg_m3: float, t_k: float):
        self._state.update(
            self._cp.DmassT_INPUTS,
            finite(rho_kg_m3, "mass density kg/m^3", positive=True),
            finite(t_k, "temperature K", positive=True),
        )
        self._require_homogeneous_gas()

    def _require_homogeneous_gas(self):
        if self._state.phase() not in self._allowed_phases:
            raise ValueError("Isothermal pipeline closure requires a homogeneous gas/supercritical state")

    def density_pt(self, p_pa: float, t_k: float) -> float:
        with self._lock:
            self._update_pt(p_pa, t_k)
            return finite(self._state.rhomass(), "EOS mass density", positive=True)

    def pressure_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        with self._lock:
            self._update_rho_t(rho_kg_m3, t_k)
            return finite(self._state.p(), "EOS pressure", positive=True)

    def isothermal_sound_speed_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        with self._lock:
            self._update_rho_t(rho_kg_m3, t_k)
            density = finite(self._state.rhomass(), "EOS mass density", positive=True)
            try:
                compressibility = finite(
                    self._state.isothermal_compressibility(),
                    "isothermal compressibility Pa^-1", positive=True,
                )
            except (AttributeError, NotImplementedError) as error:
                raise ValueError("Selected CoolProp backend does not expose isothermal compressibility") from error
            return finite(math.sqrt(1.0/(density*compressibility)),
                          "isothermal characteristic speed m/s", positive=True)


class CoolPropMixtureIsothermalEOS:
    """Isothermal single-phase protocol adapter for a frozen HEOS mixture.

    The supplied mixture provider owns composition and CoolProp's binary
    interaction parameters. This wrapper exposes its mass-basis PT↔rho-T
    closure to linepack and pipe models without changing composition or
    substituting an ideal-gas mixture rule.
    """

    def __setattr__(self, name, value):
        if hasattr(self, "_definition") and name in {"properties", "_identity", "_definition"}:
            raise AttributeError("Frozen mixture EOS ownership and identity are immutable")
        object.__setattr__(self, name, value)

    def __init__(self, properties):
        from .coolprop_mixture import CoolPropMixtureProperties

        if type(properties) is not CoolPropMixtureProperties:
            raise TypeError("Supply one immutable CoolPropMixtureProperties provider")
        if properties.backend != "HEOS":
            raise ValueError("Frozen mixture isothermal closure requires native HEOS")
        self.properties = properties
        # A PropertyBasis records fluid, energy reference and spin, rather than
        # a provider attribute. Retain all three and the frozen composition;
        # an unresolved mixture spin declaration must remain unresolved.
        self._identity = (f"{properties.basis.reference_id}:"
                          f"fluid={properties.basis.fluid}:spin={properties.basis.spin_composition}:"
                          f"{properties.composition_sha256}:isothermal-frozen-mixture")
        self._definition = self._definition_snapshot()

    def _definition_snapshot(self):
        properties = self.properties
        basis = properties.basis
        return (self._identity, id(properties),
                (basis.fluid, basis.reference_id, basis.spin_composition),
                properties.backend, properties.version,
                properties.composition_sha256, properties.species,
                properties.coolprop_fluids, properties.mole_fractions,
                properties.molar_masses_kg_mol, properties.coolprop_molar_masses_kg_mol,
                id(properties._state), id(properties._cp), id(properties._mixture_cp),
                properties.state_pt, properties.state_rho_t,
                properties.isothermal_sound_speed_rho_t,
                properties._evaluate, properties._snapshot,
                properties.internal_energy_policy, properties.quality_roundoff_tolerance)

    @property
    def identity(self) -> str:
        if self._definition_snapshot() != self._definition:
            raise ValueError("Frozen CoolProp mixture EOS identity or native definition changed")
        return self._identity

    @staticmethod
    def _require_gas(state):
        if state.phase not in {"gas", "supercritical", "supercritical_gas"}:
            raise ValueError("Isothermal mixture closure requires a homogeneous gas state")
        return state

    def density_pt(self, p_pa: float, t_k: float) -> float:
        _ = self.identity
        state = self._require_gas(self.properties.state_pt(
            finite(p_pa, "pressure_pa", positive=True),
            finite(t_k, "temperature_k", positive=True),
        ))
        density = finite(state.density_kg_m3, "EOS mixture mass density", positive=True)
        _ = self.identity
        return density

    def pressure_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        _ = self.identity
        state = self._require_gas(self.properties.state_rho_t(
            finite(rho_kg_m3, "density_kg_m3", positive=True),
            finite(t_k, "temperature_k", positive=True),
        ))
        pressure = finite(state.pressure_pa, "EOS mixture pressure", positive=True)
        _ = self.identity
        return pressure

    def isothermal_sound_speed_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        _ = self.identity
        speed = self.properties.isothermal_sound_speed_rho_t(
            finite(rho_kg_m3, "density_kg_m3", positive=True),
            finite(t_k, "temperature_k", positive=True),
        )
        _ = self.identity
        return finite(speed, "isothermal mixture characteristic speed", positive=True)


__all__ = ["IsothermalSinglePhaseEOS", "CoolPropIsothermalEOS",
           "CoolPropMixtureIsothermalEOS"]
