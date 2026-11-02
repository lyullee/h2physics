"""Map public LH2DT objects through explicit SI and energy-reference contracts.

The caller supplies the original model/factory. This adapter only maps object
fields; equipment equations remain in the separately installed native engine.
Public interface basis: https://github.com/lyullee/lh2dt_models
"""

from collections.abc import Callable
from typing import Any, Protocol

from ..core import PropertyBasis, Stream, ThermoState, finite
from ..release import HomogeneousIsentropicNozzle, NozzleOpening


class Lh2dtState(Protocol):
    pressure_Pa: float
    temperature_K: float
    density_kg_m3: float
    specific_enthalpy_J_kg: float
    specific_internal_energy_J_kg: float
    specific_entropy_J_kgK: float
    quality: float | None
    phase: str


def from_lh2dt_state(state: Lh2dtState, *, basis: PropertyBasis) -> ThermoState:
    return ThermoState(
        basis, state.pressure_Pa, state.temperature_K, state.density_kg_m3,
        state.specific_enthalpy_J_kg, state.specific_internal_energy_J_kg,
        state.specific_entropy_J_kgK, "two_phase" if state.phase == "twophase" else state.phase,
        vapor_mass_fraction=state.quality,
    )


def to_lh2dt_state(state: ThermoState, *, expected_basis: PropertyBasis,
                   factory: Callable[..., Any]):
    expected_basis.require_compatible(state.basis)
    return factory(
        pressure_Pa=state.pressure_pa, temperature_K=state.temperature_k,
        density_kg_m3=state.density_kg_m3, specific_enthalpy_J_kg=state.enthalpy_j_kg,
        specific_internal_energy_J_kg=state.internal_energy_j_kg,
        specific_entropy_J_kgK=state.entropy_j_kg_k, quality=state.vapor_mass_fraction,
        phase="twophase" if state.phase == "two_phase" else state.phase,
    )


def to_lh2dt_flow(stream: Stream, *, expected_basis: PropertyBasis,
                  factory: Callable[..., Any]):
    expected_basis.require_compatible(stream.state.basis)
    return factory(mass_flow_kg_s=stream.mass_flow_kg_s,
                   specific_enthalpy_J_kg=stream.state.enthalpy_j_kg,
                   source=f"{stream.component_id}/{stream.port_id}")


class Lh2dtProperties:
    """Adapt an existing native provider, retaining its declared reference state."""

    def __init__(self, provider, *, reference_id: str):
        self.native = provider
        spin = {"Hydrogen": "normal", "ParaHydrogen": "para", "OrthoHydrogen": "ortho"}.get(provider.fluid, "unspecified")
        self._basis = PropertyBasis(provider.fluid, reference_id, spin)

    @property
    def basis(self):
        return self._basis

    def state_pt(self, pressure_pa, temperature_k):
        return from_lh2dt_state(self.native.from_pT(pressure_pa, temperature_k), basis=self.basis)

    def state_ph(self, pressure_pa, enthalpy_j_kg):
        return from_lh2dt_state(self.native.from_ph(pressure_pa, enthalpy_j_kg), basis=self.basis)

    def state_ps(self, pressure_pa, entropy_j_kg_k):
        return from_lh2dt_state(self.native.from_ps(pressure_pa, entropy_j_kg_k), basis=self.basis)


class Lh2dtBulkNozzleOutflow:
    """Native homogeneous-tank callback; tank equations stay in LH2DT.

    This deliberately supports only bulk-mixture withdrawal. The reviewed native
    tank overrides every negative flow's enthalpy with its bulk enthalpy. A liquid
    dip tube or vapor vent needs the receiving-engine extension in request 001.
    Histories are sampled separately, since native RK stages/retries are not
    accepted observation times. Split integration at discontinuous commands.
    """

    def __init__(self, nozzle: HomogeneousIsentropicNozzle, opening: NozzleOpening, *,
                 back_pressure_pa: float | Callable[[float], float],
                 opening_fraction: float | Callable[[float], float],
                 flow_factory: Callable[..., Any]):
        self.nozzle = nozzle
        self.opening = opening
        self.back_pressure_pa = back_pressure_pa
        self.opening_fraction = opening_fraction
        self.flow_factory = flow_factory

    def sample(self, time_s: float, native_state: Lh2dtState):
        time = finite(time_s, "time_s")
        pressure = self.back_pressure_pa(time) if callable(self.back_pressure_pa) else self.back_pressure_pa
        fraction = self.opening_fraction(time) if callable(self.opening_fraction) else self.opening_fraction
        state = from_lh2dt_state(native_state, basis=self.nozzle.properties.basis)
        return self.nozzle.solve(state, back_pressure_pa=pressure, opening=self.opening,
                                 opening_fraction=fraction)

    def __call__(self, time_s: float, native_state: Lh2dtState):
        result = self.sample(time_s, native_state)
        if result.mass_flow_kg_s == 0:
            return ()
        return (self.flow_factory(
            mass_flow_kg_s=-result.mass_flow_kg_s,
            specific_enthalpy_J_kg=result.upstream_stagnation.enthalpy_j_kg,
            source=f"{self.opening.opening_id}:homogeneous-bulk-nozzle",
        ),)
