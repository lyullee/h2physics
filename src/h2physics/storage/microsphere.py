"""Finite H2 cavity coupled to the shared spherical-wall diffusion core.

Public scientific context: https://doi.org/10.3389/fmats.2019.00342
Native property API: https://coolprop.org/coolprop/LowLevelAPI.html
No glass composition, transport coefficient or optical-release law is bundled.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ..core import ThermoState, finite, immutable_array
from ..materials import (
    DiffusionDomain,
    DiffusionMesh,
    FiniteSurfaceInventory,
    PowerLawSolubility,
    SurfaceCondition,
    TransportBoundary,
    TransportResult,
    TrapPopulation,
)
from .finite_hydride import HydrideGasThermodynamics


@dataclass(frozen=True, slots=True)
class MicrosphereDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_gas_inventory_mol: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if (self.minimum_temperature_k >= self.maximum_temperature_k
                or self.minimum_pressure_pa >= self.maximum_pressure_pa):
            raise ValueError("Microsphere temperature/pressure bounds must increase")


@dataclass(frozen=True, slots=True)
class MicrosphereResult:
    """Prescribed-temperature mass transport, not a coupled energy prediction."""

    transport: TransportResult
    gas_states: tuple[ThermoState, ...]
    gas_fugacity_pa: np.ndarray
    gas_transfer_residual_mol: np.ndarray
    total_hydrogen_mass_kg: np.ndarray
    clock_id: str
    boundary_evidence: str
    parameter_evidence: str

    def __post_init__(self):
        for name in ("gas_fugacity_pa", "gas_transfer_residual_mol", "total_hydrogen_mass_kg"):
            array = np.array(getattr(self, name), dtype=float, copy=True)
            array = immutable_array(array, name=name)
            object.__setattr__(self, name, array)

    @property
    def time_s(self):
        return self.transport.time_s

    @property
    def gas_inventory_mol(self):
        return self.transport.left_inventory_mol


class MicrosphereStorage:
    """Rigid single cavity and homogeneous spherical membrane with finite storage.

    Molecular H2 crosses equilibrium surfaces; D(T), solubility and optional
    trap kinetics are caller-owned. Native density/T states and fugacity reuse
    the existing finite-gas property contract, without a second EOS or ODE.
    Uniform gas/wall temperature is prescribed on one explicit clock. Thermal
    duty, stress, fracture, optical effects and a sphere-size population are
    unresolved at this level.
    """

    def __init__(self, *, inner_radius_m: float, outer_radius_m: float, cells: int,
                 diffusivity_m2_s: Callable[[float], float], solubility: PowerLawSolubility,
                 gas: HydrideGasThermodynamics, domain: MicrosphereDomain,
                 parameter_evidence: str, traps: tuple[TrapPopulation, ...] = ()):
        if solubility.carrier.identity != "molecular_hydrogen":
            raise ValueError("A cavity H2 molecule must match the wall mobile-entity basis")
        if not np.isclose(solubility.carrier.molar_mass_kg_mol, gas.molar_mass_kg_mol,
                          rtol=1e-10, atol=0.):
            raise ValueError("Wall and native gas hydrogen molar masses differ")
        if gas.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}:
            raise ValueError("Microsphere storage requires a declared pure hydrogen identity")
        if not callable(gas.state_rho_t):
            raise ValueError("Finite prescribed-temperature gas needs a native density/T capability")
        if not parameter_evidence.strip():
            raise ValueError("Declare material coefficient evidence or authored-verification identity")
        self.mesh = DiffusionMesh.spherical_shell(inner_radius_m, outer_radius_m, cells)
        self.cavity_volume_m3 = 4*np.pi/3*inner_radius_m**3
        self.transport = DiffusionDomain(solubility.carrier, self.mesh, diffusivity_m2_s,
                                         traps=traps)
        self.solubility, self.gas, self.domain = solubility, gas, domain
        self.parameter_evidence = parameter_evidence

    def gas_state(self, amount_mol: float, temperature_k: float) -> ThermoState:
        """Native fixed-spin EOS, with no pressure/phase fallback or clipping."""
        amount = finite(amount_mol, "cavity hydrogen moles", positive=True)
        temperature = finite(temperature_k, "prescribed temperature", positive=True)
        domain = self.domain
        if amount <= domain.minimum_gas_inventory_mol:
            raise ValueError("Cavity gas reached its declared inventory floor")
        if not domain.minimum_temperature_k <= temperature <= domain.maximum_temperature_k:
            raise ValueError("Prescribed microsphere temperature outside declared domain")
        density = amount*self.gas.molar_mass_kg_mol/self.cavity_volume_m3
        state = self.gas.state_rho_t(density, temperature)
        self.gas.basis.require_compatible(state.basis)
        if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Microsphere cavity requires a single gas-like native phase")
        if not domain.minimum_pressure_pa <= state.pressure_pa <= domain.maximum_pressure_pa:
            raise ValueError("Microsphere native gas pressure outside declared domain")
        if (not np.isclose(state.density_kg_m3, density, rtol=1e-8, atol=0.)
                or not np.isclose(state.temperature_k, temperature, rtol=1e-10, atol=0.)):
            raise ValueError("Native gas state does not reproduce its density/T inventory")
        return state

    def simulate(self, time_s, initial_gas_mol: float, initial_mobile_mol_m3, *,
                 temperature_k: Callable[[float], float],
                 external_hydrogen_fugacity_pa: Callable[[float], float] | None = None,
                 external_wall_condition: Callable[[float, float], SurfaceCondition] | None = None,
                 clock_id: str, boundary_evidence: str, initial_trapped_mol_m3=None,
                 relative_tolerance: float = 1e-8, absolute_tolerance_mol_m3: float = 1e-10,
                 maximum_step_s: float = np.inf) -> MicrosphereResult:
        if (not isinstance(clock_id, str) or not clock_id.strip()
                or not isinstance(boundary_evidence, str) or not boundary_evidence.strip()):
            raise ValueError("Declare one boundary clock and prescribed-history evidence")
        if (external_hydrogen_fugacity_pa is None) == (external_wall_condition is None):
            raise ValueError("Choose exactly one outer fugacity or wall surface condition")

        def cavity_face(time, amount):
            temperature = temperature_k(time)
            state = self.gas_state(amount, temperature)
            fugacity = finite(self.gas.fugacity_pa(state), "native H2 fugacity", positive=True)
            return SurfaceCondition("concentration",
                self.solubility.concentration_mol_m3(fugacity, temperature))

        def boundary(time):
            temperature = temperature_k(time)
            if external_wall_condition is not None:
                face = external_wall_condition(time, temperature)
            else:
                concentration = self.solubility.concentration_mol_m3(
                    external_hydrogen_fugacity_pa(time), temperature)
                face = SurfaceCondition("concentration", concentration)
            return TransportBoundary(None, face)

        reservoir = FiniteSurfaceInventory(initial_gas_mol, self.domain.minimum_gas_inventory_mol,
                                            cavity_face, boundary_evidence)
        result = self.transport.simulate(time_s, initial_mobile_mol_m3,
            boundary=boundary, temperature_k=temperature_k,
            initial_trapped_mol_m3=initial_trapped_mol_m3, left_inventory=reservoir,
            relative_tolerance=relative_tolerance,
            absolute_tolerance_mol_m3=absolute_tolerance_mol_m3, maximum_step_s=maximum_step_s)
        states = tuple(self.gas_state(float(n), temperature_k(float(t)))
                       for t, n in zip(result.time_s, result.left_inventory_mol, strict=True))
        fugacities = np.array([self.gas.fugacity_pa(s) for s in states])
        gas_defect = (result.left_inventory_mol-result.left_inventory_mol[0]
                      +result.left_integrated_mol)
        total_mass = (result.left_inventory_mol+result.wall_inventory_mol)*self.gas.molar_mass_kg_mol
        return MicrosphereResult(result, states, fugacities, gas_defect, total_mass,
                                 clock_id, boundary_evidence, self.parameter_evidence)
