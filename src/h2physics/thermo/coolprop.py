"""Low-level CoolProp provider with one protected state per instance.

Scientific and API references:
https://coolprop.org/coolprop/LowLevelAPI.html
https://doi.org/10.1063/1.3160306 (hydrogen equations of state)
https://doi.org/10.1021/ie4033999 (CoolProp property library)
"""

import math
import threading

from ..core import PropertyBasis, ThermoState, finite


class CoolPropMolarEnthalpy:
    """Reaction-species enthalpies evaluated with CoolProp plus declared references.

    CoolProp supplies state-dependent properties. ``reference_offsets_j_mol``
    must put each species on one caller-declared formation-enthalpy basis; EOS
    enthalpy zeros alone are not suitable for reaction heat calculations.
    """

    def __init__(self, species, fluids, reference_offsets_j_mol, *, basis_id,
                 temperature_bounds_k, pressure_bounds_pa, backend="HEOS"):
        if backend != "HEOS":
            raise ValueError("Reaction enthalpy requires direct HEOS; tabular use needs separate qualification")
        try:
            import CoolProp
            import CoolProp.CoolProp as cp
        except ImportError as error:
            raise ImportError("Install h2physics[thermo] to use CoolProp") from error
        self.species = tuple(species)
        self.fluids = tuple(fluids)
        self.reference_offsets_j_mol = tuple(float(x) for x in reference_offsets_j_mol)
        self.basis_id = str(basis_id)
        self.temperature_bounds_k = tuple(temperature_bounds_k)
        self.pressure_bounds_pa = tuple(pressure_bounds_pa)
        if (not self.species or len(self.species) != len(self.fluids)
                or len(self.fluids) != len(self.reference_offsets_j_mol)
                or not self.basis_id or len({s.identifier for s in self.species}) != len(self.species)
                or any(not math.isfinite(x) for x in self.reference_offsets_j_mol)
                or len(self.temperature_bounds_k) != 2
                or any(not math.isfinite(x) for x in self.temperature_bounds_k)
                or not 0 < self.temperature_bounds_k[0] < self.temperature_bounds_k[1]
                or len(self.pressure_bounds_pa) != 2
                or any(not math.isfinite(x) for x in self.pressure_bounds_pa)
                or not 0 < self.pressure_bounds_pa[0] < self.pressure_bounds_pa[1]):
            raise ValueError("Declare matching species, fluids, reference offsets and finite domains")
        self._cp = cp
        self.version = CoolProp.__version__
        self.backend = backend
        self._states = tuple(CoolProp.AbstractState(backend, fluid) for fluid in self.fluids)
        self._lock = threading.RLock()

    def definition_signature(self):
        """Read retained definitions and native ownership without a property call."""
        return (self.species, self.fluids, self.reference_offsets_j_mol,
                self.basis_id, self.temperature_bounds_k, self.pressure_bounds_pa,
                self.backend, self.version, id(self._cp),
                tuple(id(state) for state in self._states), self.enthalpies_j_mol)

    def enthalpies_j_mol(self, temperature_k, pressure_pa):
        t = finite(temperature_k, "temperature", positive=True)
        p = finite(pressure_pa, "pressure", positive=True)
        if not self.temperature_bounds_k[0] <= t <= self.temperature_bounds_k[1]:
            raise ValueError("Temperature is outside the declared CoolProp reaction domain")
        if not self.pressure_bounds_pa[0] <= p <= self.pressure_bounds_pa[1]:
            raise ValueError("Pressure is outside the declared CoolProp reaction domain")
        with self._lock:
            values = []
            for species, state, offset in zip(self.species, self._states, self.reference_offsets_j_mol, strict=True):
                state.update(self._cp.PT_INPUTS, p, t)
                expected = species.phase.split(":", 1)[0]
                if ((expected == "liquid" and state.phase() not in {
                        self._cp.iphase_liquid, self._cp.iphase_supercritical_liquid})
                        or (expected in {"gas", "vapor"} and state.phase() not in {
                            self._cp.iphase_gas, self._cp.iphase_supercritical_gas,
                            self._cp.iphase_supercritical})):
                    raise ValueError("CoolProp state does not match the declared reaction-species phase")
                value = float(state.hmolar()) + offset
                if not math.isfinite(value):
                    raise ValueError("CoolProp returned non-finite molar enthalpy")
                values.append(value)
        import numpy as np
        return np.asarray(values)


class CoolPropProperties:
    def __init__(self, fluid: str = "Hydrogen", *, backend: str = "HEOS",
                 internal_energy_policy: str = "library", quality_roundoff_tolerance: float = 0.):
        if not isinstance(fluid, str) or not fluid.strip():
            raise ValueError("Declare a nonempty CoolProp fluid name")
        if not isinstance(backend, str):
            raise TypeError("CoolProp backend must be a text identifier")
        if backend not in {"HEOS", "BICUBIC&HEOS", "TTSE&HEOS"}:
            raise ValueError("Select an explicitly supported reference or tabular backend")
        if not isinstance(internal_energy_policy, str):
            raise TypeError("Internal-energy policy must be a text identifier")
        if internal_energy_policy not in {"library", "derive_from_h_p_rho"}:
            raise ValueError("Unsupported internal-energy closure")
        if backend == "HEOS" and internal_energy_policy != "library":
            raise ValueError("The reference EOS must retain its own internal energy")
        tolerance = finite(quality_roundoff_tolerance, "quality_roundoff_tolerance")
        if not 0 <= tolerance <= 1e-6:
            raise ValueError("Quality roundoff tolerance must lie in [0, 1e-6]")
        try:
            import CoolProp
            import CoolProp.CoolProp as cp
        except ImportError as error:
            raise ImportError("Install h2physics[thermo] to use the CoolProp provider") from error
        self._cp = cp
        self._state = CoolProp.AbstractState(backend, fluid)
        self._lock = threading.RLock()
        spin = {"Hydrogen": "normal", "ParaHydrogen": "para", "OrthoHydrogen": "ortho"}.get(fluid, "unspecified")
        self._basis = PropertyBasis(fluid, f"CoolProp:{CoolProp.__version__}:HEOS:{fluid}:default", spin)
        self.backend = backend
        self.version = CoolProp.__version__
        self.internal_energy_policy = internal_energy_policy
        self.quality_roundoff_tolerance = tolerance

    @property
    def basis(self) -> PropertyBasis:
        return self._basis

    @property
    def molar_mass_kg_mol(self) -> float:
        """Molar mass from the selected CoolProp fluid definition."""
        with self._lock:
            return float(self._state.molar_mass())

    @property
    def critical_temperature_k(self) -> float:
        with self._lock:
            return self._state.T_critical()

    @property
    def critical_pressure_pa(self) -> float:
        with self._lock:
            return self._state.p_critical()

    def _snapshot(self) -> ThermoState:
        state, cp = self._state, self._cp
        phase_id = state.phase()
        phases = {
            cp.iphase_liquid: "liquid", cp.iphase_gas: "gas",
            cp.iphase_twophase: "two_phase", cp.iphase_supercritical: "supercritical",
            cp.iphase_supercritical_gas: "supercritical_gas",
            cp.iphase_supercritical_liquid: "supercritical_liquid",
            cp.iphase_critical_point: "critical_point",
        }
        two_phase = phase_id == cp.iphase_twophase

        def optional(method):
            try:
                value = float(method())
                return value if value > 0 else None
            except (ValueError, NotImplementedError):
                return None

        pressure, density, enthalpy = state.p(), state.rhomass(), state.hmass()
        internal_energy = (state.umass() if self.internal_energy_policy == "library"
                           else enthalpy - pressure / density)
        quality = float(state.Q()) if two_phase else None
        raw_quality = None
        if quality is not None and not 0 <= quality <= 1:
            correction = max(-quality, quality-1.)
            if correction > self.quality_roundoff_tolerance:
                raise ValueError("EOS vapor fraction outside [0, 1]; explicit roundoff budget exceeded")
            raw_quality, quality = quality, min(1., max(0., quality))
        return ThermoState(
            self.basis, pressure, state.T(), density, enthalpy, internal_energy,
            state.smass(), phases.get(phase_id, "unknown"),
            None if two_phase else optional(state.cpmass),
            None if two_phase else optional(state.cvmass),
            None if two_phase else optional(state.viscosity),
            None if two_phase else optional(state.conductivity),
            None if two_phase else optional(state.speed_sound),
            quality, raw_quality,
        )

    def _evaluate(self, pair, first, second) -> ThermoState:
        with self._lock:
            self._state.update(pair, first, second)
            return self._snapshot()

    def state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState:
        return self._evaluate(self._cp.PT_INPUTS,
                              finite(pressure_pa, "pressure_pa", positive=True),
                              finite(temperature_k, "temperature_k", positive=True))

    def state_ph(self, pressure_pa: float, enthalpy_j_kg: float) -> ThermoState:
        return self._evaluate(self._cp.HmassP_INPUTS,
                              finite(enthalpy_j_kg, "enthalpy_j_kg"),
                              finite(pressure_pa, "pressure_pa", positive=True))

    def state_ps(self, pressure_pa: float, entropy_j_kg_k: float) -> ThermoState:
        return self._evaluate(self._cp.PSmass_INPUTS,
                              finite(pressure_pa, "pressure_pa", positive=True),
                              finite(entropy_j_kg_k, "entropy_j_kg_k"))

    def state_pu(self, pressure_pa: float, internal_energy_j_kg: float) -> ThermoState:
        return self._evaluate(self._cp.PUmass_INPUTS,
                              finite(pressure_pa, "pressure_pa", positive=True),
                              finite(internal_energy_j_kg, "internal_energy_j_kg"))

    def state_rho_u(self, density_kg_m3: float, internal_energy_j_kg: float) -> ThermoState:
        return self._evaluate(self._cp.DmassUmass_INPUTS,
                              finite(density_kg_m3, "density_kg_m3", positive=True),
                              finite(internal_energy_j_kg, "internal_energy_j_kg"))

    def state_prho(self, pressure_pa: float, density_kg_m3: float) -> ThermoState:
        return self._evaluate(self._cp.DmassP_INPUTS,
                              finite(density_kg_m3, "density_kg_m3", positive=True),
                              finite(pressure_pa, "pressure_pa", positive=True))

    def saturated_at_temperature(self, temperature_k: float, vapor_mass_fraction: float) -> ThermoState:
        quality = finite(vapor_mass_fraction, "vapor_mass_fraction")
        if not 0 <= quality <= 1:
            raise ValueError("Vapor mass fraction must lie in [0, 1]")
        return self._evaluate(self._cp.QT_INPUTS, quality,
                              finite(temperature_k, "temperature_k", positive=True))

    def phase_viscosity(self, state: ThermoState) -> float:
        """Single phase or an explicit saturated endpoint; no mixture closure."""
        self.basis.require_compatible(state.basis)
        quality = state.vapor_mass_fraction
        if quality is not None and quality not in (0., 1.):
            raise ValueError("Two-phase mixture viscosity needs a separate declared closure")
        with self._lock:
            if quality is None:
                self._state.update(self._cp.HmassP_INPUTS, state.enthalpy_j_kg, state.pressure_pa)
            else:
                self._state.update(self._cp.PQ_INPUTS, state.pressure_pa, quality)
            if self._state.phase() == self._cp.iphase_twophase and self._state.Q() not in (0., 1.):
                raise ValueError("Flashed mixture viscosity needs a separate declared closure")
            return finite(self._state.viscosity(), "viscosity_pa_s", positive=True)

    def saturated(self, pressure_pa: float, vapor_mass_fraction: float) -> ThermoState:
        quality = finite(vapor_mass_fraction, "vapor_mass_fraction")
        if not 0 <= quality <= 1:
            raise ValueError("Vapor mass fraction must lie in [0, 1]")
        return self._evaluate(self._cp.PQ_INPUTS,
                              finite(pressure_pa, "pressure_pa", positive=True), quality)
