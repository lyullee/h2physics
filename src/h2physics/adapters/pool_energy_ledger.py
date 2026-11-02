"""Host acceptance boundary for native accepted-clock pool energy ledgers.

The host intentionally does not integrate sparse instantaneous heat-flux output.
The receiving pool engine must publish cumulative energy terms at its accepted
output edges before this adapter can build a control-volume receipt.
"""

from dataclasses import dataclass, field
from math import fsum

import numpy as np

from ..core import immutable_array, finite
from .parcel_pool_chain import ParcelPoolContinuation


class PoolEnergyCapabilityError(RuntimeError):
    """The selected native pool result does not expose the requested energy basis."""


@dataclass(frozen=True, slots=True)
class PoolEnergyLedger:
    continuation: ParcelPoolContinuation = field(repr=False)
    substrate_mode: str
    energy_reference_id: str
    vapor_phase_id: str
    time_s: np.ndarray
    liquid_internal_energy_j: np.ndarray
    cumulative_liquid_inlet_enthalpy_j: np.ndarray
    cumulative_vapor_outlet_enthalpy_j: np.ndarray
    cumulative_substrate_heat_into_liquid_j: np.ndarray
    cumulative_external_heat_into_substrate_j: np.ndarray
    cumulative_pressure_volume_work_out_j: np.ndarray
    boundary_pressure_pa: np.ndarray
    liquid_volume_m3: np.ndarray
    mass_residual_kg: np.ndarray
    energy_residual_j: np.ndarray
    substrate_energy_change_j: np.ndarray | None
    substrate_energy_residual_j: np.ndarray | None
    cumulative_unapplied_heat_j: np.ndarray
    cumulative_dry_surface_heat_j: np.ndarray
    cumulative_heat_cap_rejection_j: np.ndarray
    mass_tolerance_kg: float
    energy_tolerance_j: float
    _identity: tuple = field(default=(), init=False, repr=False, compare=False)
    _source_values: tuple = field(default=(), init=False, repr=False, compare=False)
    _native_field_names: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.continuation) is not ParcelPoolContinuation:
            raise TypeError("Retain the original deposited-stock pool continuation")
        if self.substrate_mode not in {"prescribed_external_reservoir", "finite_wall"}:
            raise ValueError("Declare a prescribed external reservoir or a finite wall substrate")
        if (not isinstance(self.energy_reference_id, str) or not self.energy_reference_id.strip()
                or self.energy_reference_id != self.continuation.initialization.batch.state.basis.reference_id):
            raise ValueError("Pool energy reference must match the original deposited-state property basis")
        expected_vapor_phase = (f"{self.continuation.initialization.batch.state.basis.fluid}:"
                                f"{self.continuation.initialization.batch.state.basis.spin_composition}:vapor")
        if self.vapor_phase_id != expected_vapor_phase:
            raise ValueError("Pool vapor enthalpy phase must match the original fluid/spin vapor identity")
        self.continuation.require_current()
        size = len(self.continuation.absolute_times_s)
        names = ("time_s", "liquid_internal_energy_j", "cumulative_liquid_inlet_enthalpy_j",
                 "cumulative_vapor_outlet_enthalpy_j", "cumulative_substrate_heat_into_liquid_j",
                 "cumulative_external_heat_into_substrate_j", "cumulative_pressure_volume_work_out_j",
                 "boundary_pressure_pa", "liquid_volume_m3",
                 "mass_residual_kg", "energy_residual_j", "cumulative_unapplied_heat_j",
                 "cumulative_dry_surface_heat_j", "cumulative_heat_cap_rejection_j")
        for name in names:
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != (size,) or not np.all(np.isfinite(values)):
                raise ValueError("Pool energy arrays must be finite and aligned with every native output edge")
            values = immutable_array(values, name="values")
            object.__setattr__(self, name, values)
        if (not np.array_equal(self.time_s, np.asarray(self.continuation.absolute_times_s))
                or np.any(np.diff(self.time_s) <= 0.)
                or np.any(self.boundary_pressure_pa <= 0.) or np.any(self.liquid_volume_m3 < 0.)):
            raise ValueError("Pool energy state must retain the original increasing clock and physical boundary")
        mass_tolerance = finite(self.mass_tolerance_kg, "pool mass tolerance", positive=True)
        tolerance = finite(self.energy_tolerance_j, "pool energy tolerance", positive=True)
        object.__setattr__(self, "mass_tolerance_kg", mass_tolerance)
        object.__setattr__(self, "energy_tolerance_j", tolerance)
        if self.substrate_mode == "finite_wall":
            if self.substrate_energy_change_j is None or self.substrate_energy_residual_j is None:
                raise ValueError("Finite wall continuation requires native wall energy change and balance")
            for name in ("substrate_energy_change_j", "substrate_energy_residual_j"):
                values = np.array(getattr(self, name), dtype=float, copy=True)
                if values.shape != (size,) or not np.all(np.isfinite(values)):
                    raise ValueError("Finite substrate energy arrays must match every accepted pool edge")
                values = immutable_array(values, name="values")
                object.__setattr__(self, name, values)
            if np.any(np.abs(self.substrate_energy_residual_j) > tolerance):
                raise ValueError("Finite substrate native energy balance exceeds its declared tolerance")
        elif self.substrate_energy_change_j is not None or self.substrate_energy_residual_j is not None:
            raise ValueError("Prescribed external reservoir cannot claim a finite substrate internal-energy change")
        elif np.any(self.cumulative_external_heat_into_substrate_j != 0.):
            raise ValueError("External-reservoir mode cannot claim a finite substrate heat-input ledger")
        if (np.any(np.abs(self.mass_residual_kg) > mass_tolerance)
                or np.any(np.abs(self.energy_residual_j) > tolerance)):
            raise ValueError("Native pool mass or energy balance exceeds the declared acceptance budget")
        for name in ("cumulative_unapplied_heat_j", "cumulative_dry_surface_heat_j",
                     "cumulative_heat_cap_rejection_j"):
            values = getattr(self, name)
            if np.any(values < 0.) or values[0] != 0. or np.any(np.diff(values) < 0.):
                raise ValueError(
                    "Cumulative pool heat allocation diagnostics must start at zero and be nondecreasing"
                )
        rows = tuple(self.continuation.native_result.ledger)
        expected_mass = np.asarray([self.continuation.initialization.batch.mass_kg
            -float(row.liquid_mass_kg)-float(row.cumulative_evaporation_kg) for row in rows])
        expected_energy = (self.liquid_internal_energy_j-self.liquid_internal_energy_j[0]
            -self.cumulative_liquid_inlet_enthalpy_j+self.cumulative_vapor_outlet_enthalpy_j
            -self.cumulative_substrate_heat_into_liquid_j+self.cumulative_pressure_volume_work_out_j)
        if (not np.allclose(self.mass_residual_kg, expected_mass, rtol=1e-12, atol=1e-12)
                or not np.allclose(self.energy_residual_j, expected_energy, rtol=1e-12, atol=1e-9)):
            raise ValueError("Pool mass/energy residual arrays must be independently reconstructed from retained terms")
        if self.substrate_mode == "finite_wall":
            expected_substrate = (self.substrate_energy_change_j-self.substrate_energy_change_j[0]
                -self.cumulative_external_heat_into_substrate_j
                +self.cumulative_substrate_heat_into_liquid_j)
            if not np.allclose(self.substrate_energy_residual_j, expected_substrate,
                               rtol=1e-12, atol=1e-9):
                raise ValueError("Finite-wall residual must be independently reconstructed from its retained terms")
        object.__setattr__(self, "_identity", (self.continuation, self.continuation.native_result,
            self.substrate_mode, self.energy_reference_id, self.vapor_phase_id,
            self.mass_tolerance_kg, self.energy_tolerance_j))
        native_field_names = (*_NATIVE_ENERGY_FIELDS,
            *((_FINITE_WALL_ENERGY_FIELD,) if self.substrate_mode == "finite_wall" else ()))
        try:
            source_values = tuple(tuple(finite(getattr(row, name), name)
                                       for name in native_field_names) for row in rows)
        except (AttributeError, TypeError, ValueError) as error:
            raise PoolEnergyCapabilityError(
                "Native pool accepted edges do not expose the declared energy fields"
            ) from error
        object.__setattr__(self, "_native_field_names", native_field_names)
        object.__setattr__(self, "_source_values", source_values)
        self.require_current()

    def require_current(self):
        if (not self._identity or self.continuation is not self._identity[0]
                or self.continuation.native_result is not self._identity[1]
                or self.substrate_mode != self._identity[2]
                or self.energy_reference_id != self._identity[3]
                or self.vapor_phase_id != self._identity[4]
                or self.mass_tolerance_kg != self._identity[5]
                or self.energy_tolerance_j != self._identity[6]):
            raise ValueError("Pool energy ledger lost its original native pool run")
        self.continuation.require_current()
        mass_tolerance = finite(self.mass_tolerance_kg, "pool mass tolerance", positive=True)
        energy_tolerance = finite(self.energy_tolerance_j, "pool energy tolerance", positive=True)
        if (not np.array_equal(self.time_s, np.asarray(self.continuation.absolute_times_s))
                or np.any(np.abs(self.mass_residual_kg) > mass_tolerance)
                or np.any(np.abs(self.energy_residual_j) > energy_tolerance)
                or np.any(self.boundary_pressure_pa <= 0.) or np.any(self.liquid_volume_m3 < 0.)
                or any(getattr(self, name)[0] != 0. or np.any(np.diff(getattr(self, name)) < 0.)
                       for name in (
                    "cumulative_unapplied_heat_j", "cumulative_dry_surface_heat_j",
                    "cumulative_heat_cap_rejection_j"))):
            raise ValueError("Pool energy receipt no longer satisfies its declared bounds")
        if (self.substrate_mode == "prescribed_external_reservoir"
                and np.any(self.cumulative_external_heat_into_substrate_j != 0.)):
            raise ValueError("External-reservoir receipt acquired a finite substrate heat input")
        rows = tuple(self.continuation.native_result.ledger)
        try:
            current = tuple(tuple(float(getattr(row, name)) for name in self._native_field_names)
                            for row in rows)
        except (AttributeError, TypeError, ValueError) as error:
            raise PoolEnergyCapabilityError("Native pool energy fields changed or became unavailable") from error
        if current != self._source_values:
            raise ValueError("Native accepted pool energy ledger changed after capture")
        columns = tuple(zip(*current, strict=True))
        if any(not np.array_equal(getattr(self, name), np.asarray(column))
               for name,column in zip(self._native_field_names, columns, strict=True)):
            raise ValueError("Pool energy arrays differ from the captured native accepted-edge fields")
        liquid_mass = np.asarray([float(row.liquid_mass_kg) for row in rows])
        evaporation = np.asarray([float(row.cumulative_evaporation_kg) for row in rows])
        expected_mass = (self.continuation.initialization.batch.mass_kg-liquid_mass-evaporation)
        expected_energy = np.asarray([
            fsum((entry[0], -current[0][0], -entry[1], entry[2], -entry[3], entry[4]))
            for entry in current])
        if (not np.allclose(self.mass_residual_kg, expected_mass, rtol=1e-12, atol=1e-12)
                or not np.allclose(self.energy_residual_j, expected_energy, rtol=1e-12, atol=1e-9)):
            raise ValueError("Pool mass/energy residual arrays differ from the recomputed native edge balances")
        if self.substrate_mode == "finite_wall":
            expected_substrate = np.asarray([
                fsum((float(getattr(row, "substrate_energy_change_j")),
                      -float(getattr(row, _FINITE_WALL_ENERGY_FIELD)), entry[3]))
                for row,entry in zip(rows,current,strict=True)])
            if (not np.allclose(self.substrate_energy_change_j,
                                   np.asarray([float(getattr(row,"substrate_energy_change_j")) for row in rows]))
                    or not np.allclose(self.substrate_energy_residual_j, expected_substrate,
                                       rtol=1e-12, atol=1e-9)):
                raise ValueError("Finite-wall energy fields differ from the independently recomputed wall balance")
        return self

    @property
    def source_values(self):
        return self._source_values


_NATIVE_ENERGY_FIELDS = (
    "liquid_internal_energy_j", "cumulative_liquid_inlet_enthalpy_j",
    "cumulative_vapor_outlet_enthalpy_j", "cumulative_substrate_heat_into_liquid_j",
    "cumulative_pressure_volume_work_out_j",
    "boundary_pressure_pa", "liquid_volume_m3",
    "cumulative_unapplied_heat_j", "cumulative_dry_surface_heat_j",
    "cumulative_heat_cap_rejection_j",
)
_FINITE_WALL_ENERGY_FIELD = "cumulative_external_heat_into_substrate_j"


def bind_native_pool_energy_ledger(continuation, *, substrate_mode,
                                   energy_reference_id, vapor_phase_id,
                                   mass_tolerance_kg, energy_tolerance_j):
    """Bind only energy fields integrated by the native pool at its own accepted edges."""
    if type(continuation) is not ParcelPoolContinuation:
        raise TypeError("Use the original native deposited-stock continuation")
    continuation.require_current()
    rows = tuple(continuation.native_result.ledger)
    field_names = (*_NATIVE_ENERGY_FIELDS,
                   *((_FINITE_WALL_ENERGY_FIELD,) if substrate_mode == "finite_wall" else ()))
    try:
        raw = tuple(tuple(finite(getattr(row, name), name) for name in field_names)
                    for row in rows)
        mass = tuple(finite(row.liquid_mass_kg, "native pool liquid mass") for row in rows)
        evaporation = tuple(finite(row.cumulative_evaporation_kg, "native pool evaporation") for row in rows)
        substrate_u = (tuple(finite(row.substrate_energy_change_j, "native substrate energy change")
                             for row in rows) if substrate_mode == "finite_wall" else None)
        substrate_residual = (tuple(fsum((substrate_u[index], -substrate_u[0],
                               -raw[index][-1], raw[index][3]))
                               for index in range(len(rows)))
                              if substrate_mode == "finite_wall" else None)
    except (AttributeError, TypeError, ValueError) as error:
        raise PoolEnergyCapabilityError(
            "Native pool must expose accepted-edge cumulative energy, work, heat allocation and boundary fields"
        ) from error
    columns = tuple(zip(*raw, strict=True))
    values = dict(zip(field_names, columns, strict=True))
    external_heat = (values[_FINITE_WALL_ENERGY_FIELD] if substrate_mode == "finite_wall"
                     else tuple(0. for _ in rows))
    times = np.asarray(continuation.absolute_times_s, dtype=float)
    initial_u = raw[0][0]
    residuals = tuple(fsum((entry[0], -initial_u, -entry[1], entry[2], -entry[3], entry[4]))
                      for entry in raw)
    initial_mass = continuation.initialization.batch.mass_kg
    mass_residuals = tuple(initial_mass-mass_i-evap_i for mass_i,evap_i in zip(mass,evaporation,strict=True))
    if (any(value != 0. for value in raw[0][1:5])
            or (substrate_u is not None and (substrate_u[0] != 0. or raw[0][-1] != 0.))):
        raise ValueError("Native pool energy integrals must start from the declared initial-stock edge")
    result = PoolEnergyLedger(continuation, substrate_mode, energy_reference_id,
        vapor_phase_id, times,
        values["liquid_internal_energy_j"], values["cumulative_liquid_inlet_enthalpy_j"],
        values["cumulative_vapor_outlet_enthalpy_j"], values["cumulative_substrate_heat_into_liquid_j"],
        external_heat,
        values["cumulative_pressure_volume_work_out_j"], values["boundary_pressure_pa"],
        values["liquid_volume_m3"], mass_residuals, residuals, substrate_u, substrate_residual,
        values["cumulative_unapplied_heat_j"], values["cumulative_dry_surface_heat_j"],
        values["cumulative_heat_cap_rejection_j"], mass_tolerance_kg, energy_tolerance_j)
    return result.require_current()


__all__ = ["PoolEnergyCapabilityError", "PoolEnergyLedger", "bind_native_pool_energy_ledger"]
