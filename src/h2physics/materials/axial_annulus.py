"""Axial-only transport through a constant-section annular cylinder."""

import math
from collections.abc import Callable

from ..core import finite
from .finite_volume import DiffusionDomain, DiffusionMesh, TransportResult
from .transport import HydrogenCarrier, TrapPopulation


class AxialAnnulusDiffusion:
    """Reuse the shared 1-D solver for axial transport across an annulus.

    The cross-section is the exact, constant area between the declared radii.
    Only the axial coordinate is resolved. Radial gradients, r-z coupling,
    changing section, heat transfer, stress feedback and material qualification
    are outside this model. A prescribed stress potential can be forwarded to
    the shared owner. Material and diffusivity inputs remain caller-owned.
    """

    def __init__(
        self,
        carrier: HydrogenCarrier,
        *,
        inner_radius_m: float,
        outer_radius_m: float,
        length_m: float,
        cells: int,
        diffusivity_m2_s: Callable[[float], float],
        traps: tuple[TrapPopulation, ...] = (),
    ):
        if type(carrier) is not HydrogenCarrier:
            raise TypeError("Retain an explicit HydrogenCarrier")
        inner = finite(inner_radius_m, "inner radius", positive=True)
        outer = finite(outer_radius_m, "outer radius", positive=True)
        length = finite(length_m, "axial length", positive=True)
        if outer <= inner:
            raise ValueError("Outer radius must exceed inner radius")
        if isinstance(cells, bool) or not isinstance(cells, int) or cells < 3:
            raise ValueError("Axial diffusion needs at least three integer cells")
        if not callable(diffusivity_m2_s):
            raise TypeError("Diffusivity must be a temperature callback")
        if not isinstance(traps, tuple) or any(type(item) is not TrapPopulation for item in traps):
            raise TypeError("traps must be a tuple of TrapPopulation parameters")

        area = finite(math.pi * (outer - inner) * (outer + inner),
                      "annular cross-section area", positive=True)
        self.carrier = carrier
        self.inner_radius_m = inner
        self.outer_radius_m = outer
        self.length_m = length
        self.cells = cells
        self.cross_section_area_m2 = area
        self.diffusivity_m2_s = diffusivity_m2_s
        self.traps = traps
        self.mesh = DiffusionMesh.planar(length, cells, area_m2=area)

    def simulate(self, time_s, initial_mobile_mol_m3, *, boundary,
                 temperature_k: Callable[[float], float], initial_trapped_mol_m3=None,
                 left_inventory=None, right_inventory=None,
                 stress_potential=None,
                 relative_tolerance: float = 1e-8,
                 absolute_tolerance_mol_m3: float = 1e-10,
                 maximum_step_s: float = float("inf")) -> TransportResult:
        """Delegate integration and native result lineage to DiffusionDomain."""
        return DiffusionDomain(
            self.carrier, self.mesh, self.diffusivity_m2_s, traps=self.traps,
        ).simulate(
            time_s, initial_mobile_mol_m3, boundary=boundary,
            temperature_k=temperature_k,
            initial_trapped_mol_m3=initial_trapped_mol_m3,
            left_inventory=left_inventory, right_inventory=right_inventory,
            stress_potential=stress_potential,
            relative_tolerance=relative_tolerance,
            absolute_tolerance_mol_m3=absolute_tolerance_mol_m3,
            maximum_step_s=maximum_step_s,
        )
