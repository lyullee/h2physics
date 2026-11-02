"""Prescribed hydrostatic-stress contribution to dilute solid H transport.

This is a solid chemical-potential term, not a replacement fluid EOS.
The caller supplies the mean normal stress with tensile stress positive and
the partial molar volume per mole of the declared mobile carrier.
Primary physical context: https://doi.org/10.1016/0001-6160(71)90054-X
and https://www.sciencedirect.com/science/article/pii/S0925838816326901.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ..constants import R_J_MOL_K
from ..core import Origin, finite, immutable_array
from .transport import HydrogenCarrier


@dataclass(frozen=True, slots=True)
class HydrostaticStressPotential:
    """One-way prescribed stress, with ``mu_stress = -V_H * sigma_h``.

    ``hydrostatic_stress_pa(time_s, positions_m)`` returns one stress per
    requested material coordinate. It receives immutable coordinate storage.
    Time has the same seconds and origin as the diffusion solve; ``clock_id``
    records that caller-declared correspondence. No stress/diffusion feedback,
    temperature gradient, plasticity or stress-dependent trap law is inferred.
    """

    carrier: HydrogenCarrier
    hydrostatic_stress_pa: Callable
    partial_molar_volume_m3_mol: float
    temperature_domain_k: tuple[float, float]
    stress_field_id: str
    partial_molar_volume_evidence_id: str
    clock_id: str
    origin: Origin

    def __post_init__(self):
        if type(self.carrier) is not HydrogenCarrier:
            raise TypeError("Declare the mobile H/H2 carrier for the solid molar-volume basis")
        if not callable(self.hydrostatic_stress_pa):
            raise TypeError("Hydrostatic stress must be a time/material-coordinate callback")
        volume = finite(self.partial_molar_volume_m3_mol, "partial molar volume m3/mol")
        if volume < 0.:
            raise ValueError("This dilute tensile-stress closure needs nonnegative partial molar volume")
        if len(self.temperature_domain_k) != 2:
            raise ValueError("Declare the material temperature envelope")
        lower, upper = (finite(x, "material temperature bound", positive=True)
                        for x in self.temperature_domain_k)
        if lower >= upper:
            raise ValueError("Material temperature bounds must increase")
        for value in (self.stress_field_id, self.partial_molar_volume_evidence_id, self.clock_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Declare stress, material-volume and clock evidence")
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("Resolve prescribed stress and material-parameter provenance")
        object.__setattr__(self, "partial_molar_volume_m3_mol", volume)
        object.__setattr__(self, "temperature_domain_k", (lower, upper))
        object.__setattr__(self, "origin", origin)

    def dimensionless_potential(self, time_s, positions_m, temperature_k):
        """Return ``V_H * sigma_h / (R*T)`` at the requested coordinates."""
        time = finite(time_s, "stress field time s")
        temperature = finite(temperature_k, "stress transport temperature K", positive=True)
        if not self.temperature_domain_k[0] <= temperature <= self.temperature_domain_k[1]:
            raise ValueError("Stress transport is outside the declared material temperature envelope")
        coordinates = immutable_array(positions_m, dtype=float, name="stress coordinates m")
        if coordinates.ndim != 1 or not np.all(np.isfinite(coordinates)):
            raise ValueError("Stress coordinates must be a finite one-dimensional array")
        values = np.asarray(self.hydrostatic_stress_pa(time, coordinates))
        if values.dtype.kind not in "iuf":
            raise ValueError("Hydrostatic stress samples must be real numbers, not booleans or complex values")
        values = np.asarray(values, dtype=float)
        if values.shape != coordinates.shape or not np.all(np.isfinite(values)):
            raise ValueError("Supply finite tensile-positive mean normal stress at every coordinate")
        thermal_energy = finite(R_J_MOL_K * temperature, "molar thermal energy", positive=True)
        with np.errstate(over="ignore", invalid="ignore"):
            potential = values * (self.partial_molar_volume_m3_mol / thermal_energy)
        if not np.all(np.isfinite(potential)):
            raise ValueError("Dimensionless solid stress potential exceeds finite arithmetic")
        return immutable_array(potential, name="dimensionless solid stress potential")
