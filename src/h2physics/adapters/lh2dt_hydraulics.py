"""Native geometry/state/result bridge to the one converged Darcy closure."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..core import finite
from ..hydraulics import DarcyFlowResult, DarcyGeometry, solve_darcy_flow
from .lh2dt import Lh2dtProperties


@dataclass(frozen=True, slots=True)
class DarcyPipeEvaluation:
    native: Any
    hydraulic: DarcyFlowResult | None
    friction_law_id: str

    def __getattr__(self, name):
        return getattr(self.native, name)


class Lh2dtDarcyPipe:
    """Reuse native geometry/viscosity with an explicitly selected friction law.

    Native thermal parameters and actual result factories remain available.
    The selected correlation is a declared physical closure, never a fallback.
    """

    def __init__(self, native_pipe, bridge: Lh2dtProperties, *,
                 viscosity_reader: Callable[[Any], float], friction_law: Callable[[float, float], float],
                 friction_law_id: str, result_factory: Callable[..., Any]):
        if native_pipe.properties is not bridge.native:
            raise ValueError("Darcy bridge and native pipe must share the property instance")
        if not friction_law_id.strip():
            raise ValueError("The friction closure identity must be explicit")
        self.native_pipe, self.properties = native_pipe, bridge.native
        self.viscosity_reader, self.friction_law = viscosity_reader, friction_law
        self.friction_law_id, self.result_factory = friction_law_id, result_factory

    @property
    def geometry(self):
        return DarcyGeometry(self.native_pipe.length, self.native_pipe.diameter,
                             self.native_pipe.roughness, self.native_pipe.local_k)

    @property
    def elevation_change_m(self):
        return finite(self.native_pipe.dz, "elevation_change_m")

    @property
    def heat_into_fluid_w(self):
        return finite(self.native_pipe.heat, "heat_into_fluid_w")

    def __getattr__(self, name):
        return getattr(self.native_pipe, name)

    def evaluate(self, left, right):
        gravity = 9.80665
        forward_drive = left.pressure_Pa-right.pressure_Pa-left.density_kg_m3*gravity*self.elevation_change_m
        reverse_drive = right.pressure_Pa-left.pressure_Pa+right.density_kg_m3*gravity*self.elevation_change_m
        forward = forward_drive >= reverse_drive
        upstream, downstream = (left, right) if forward else (right, left)
        drive = forward_drive if forward else reverse_drive
        dz = self.elevation_change_m*(1. if forward else -1.)
        if drive <= 0.:
            if self.heat_into_fluid_w != 0.:
                raise ValueError("A stagnant prescribed heat input requires a stored thermal inventory")
            result = None
            rate = reynolds = friction = heat = 0.
            enthalpy = upstream.specific_enthalpy_J_kg
            drop = upstream.pressure_Pa-downstream.pressure_Pa
            momentum = drive
        else:
            result = solve_darcy_flow(self.geometry, density_kg_m3=upstream.density_kg_m3,
                viscosity_pa_s=self.viscosity_reader(upstream), driving_pressure_pa=drive,
                friction_law=self.friction_law)
            rate, reynolds, friction = result.mass_flow_kg_s, result.reynolds_number, result.darcy_friction_factor
            heat = self.heat_into_fluid_w
            enthalpy = upstream.specific_enthalpy_J_kg+heat/rate
            drop = upstream.density_kg_m3*gravity*dz+result.modeled_pressure_drop_pa
            momentum = upstream.pressure_Pa-downstream.pressure_Pa-drop
        native = self.result_factory(mass_flow_kg_s=rate*(1. if forward else -1.),
            outlet_specific_enthalpy_J_kg=enthalpy, reynolds_number=reynolds,
            darcy_friction_factor=friction, heat_into_fluid_W=heat,
            upstream_side=None if rate == 0. else ("left" if forward else "right"),
            pressure_drop_Pa=drop, momentum_residual_Pa=momentum)
        return DarcyPipeEvaluation(native, result, self.friction_law_id)

    def evaluate_mass_flow(self, left, right):
        return self.evaluate(left, right).mass_flow_kg_s
