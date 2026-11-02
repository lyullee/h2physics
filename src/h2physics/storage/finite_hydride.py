"""Finite hydrogen gas/solid core and closed-inventory native-thermodynamic run.

The existing HydrideKinetics owns uptake/release and equilibrium. SciPy integrates
the new two-temperature conserved inventories; gas DU/PT flashes, fugacity and
isothermal derivatives remain with an injected native provider. No gas EOS or
kinetic correlation is implemented here. Primary context and native API:
https://doi.org/10.1115/FUELCELL2006-97140
https://arxiv.org/abs/2107.06095
https://coolprop.org/coolprop/LowLevelAPI.html
"""

import math
import threading
from collections.abc import Callable
from dataclasses import dataclass, field, fields

import numpy as np
from scipy.integrate import solve_ivp

from ..core import PropertyBasis, ThermoState, _real_numeric_array, finite, immutable_array
from .hydride import HydrideKinetics, HydrideParameters, HydrideState, VanthoffPlateau

_PENDING_TRACE_ISSUERS: set[object] = set()


def _issue_trace_token():
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    return token


@dataclass(frozen=True, slots=True)
class HydrideGasThermodynamics:
    """Pure H2 thermodynamic functions, with actual caller-owned native objects.

    ``isothermal_mass_energy_derivative`` returns d[m*u(m/V,T)]/dm at fixed T,V
    in J/kg, using the native EOS. It is only required by isothermal reference
    runs. Normal/para identity and the energy zero are in ``basis``; no spin
    conversion is performed by this contract.
    """

    basis: PropertyBasis
    molar_mass_kg_mol: float
    state_rho_u: Callable[[float, float], ThermoState]
    state_pt: Callable[[float, float], ThermoState]
    fugacity_pa: Callable[[ThermoState], float]
    source_id: str
    native_objects: tuple
    state_rho_t: Callable | None = None
    isothermal_mass_energy_derivative: Callable | None = None

    def __post_init__(self):
        if type(self.basis) is not PropertyBasis:
            raise TypeError("Native hydride thermodynamics requires a PropertyBasis")
        finite(self.molar_mass_kg_mol, "native hydrogen molar mass", positive=True)
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("Native hydrogen thermodynamics needs a source identity")
        if isinstance(self.native_objects, (str, bytes)):
            raise TypeError("Retain native provider objects as a collection, not text")
        native_objects = tuple(self.native_objects)
        if not native_objects:
            raise ValueError("Declare native gas provenance and retain its actual native objects")
        if not all(callable(f) for f in (self.state_rho_u, self.state_pt, self.fugacity_pa)):
            raise ValueError("Native DU/PT and fugacity callbacks are required")
        for optional, label in (
            (self.state_rho_t, "rho-T"),
            (self.isothermal_mass_energy_derivative, "isothermal energy derivative"),
        ):
            if optional is not None and not callable(optional):
                raise TypeError(f"Optional native {label} capability must be callable")
        if not self.basis.spin_composition or self.basis.spin_composition == "unspecified":
            raise ValueError("Declare the hydrogen spin/thermochemistry identity")
        object.__setattr__(self, "native_objects", native_objects)

    @classmethod
    def coolprop(cls, fluid: str):
        """Compose the existing HEOS property provider and native fugacity/derivatives.

        Fluid must explicitly select normal or para hydrogen. Existing provider
        DU/PT flashes and snapshots are reused, including the native energy zero.
        No table, phase imposition or reference-state mutation is introduced.
        """
        import CoolProp
        import CoolProp.CoolProp as cp

        from ..thermo.coolprop import CoolPropProperties

        if fluid not in {"Hydrogen", "ParaHydrogen"}:
            raise ValueError("Select pure normal Hydrogen or ParaHydrogen explicitly")
        properties = CoolPropProperties(fluid)
        native = CoolProp.AbstractState("HEOS", fluid)
        lock = threading.RLock()

        def fugacity(state):
            properties.basis.require_compatible(state.basis)
            with lock:
                native.update(cp.PT_INPUTS, state.pressure_pa, state.temperature_k)
                return native.fugacity(0)

        def density_temperature(density, temperature):
            with lock:
                native.update(cp.DmassT_INPUTS, density, temperature)
                return properties.state_pt(native.p(), temperature)

        def mass_energy_derivative(state):
            properties.basis.require_compatible(state.basis)
            with lock:
                native.update(cp.DmassT_INPUTS, state.density_kg_m3, state.temperature_k)
                return native.umass()+state.density_kg_m3*native.first_partial_deriv(
                    cp.iUmass, cp.iDmass, cp.iT)

        return cls(properties.basis, native.molar_mass(), properties.state_rho_u,
                   properties.state_pt, fugacity, f"CoolProp:{CoolProp.__version__}:HEOS:{fluid}",
                   (properties, native), density_temperature, mass_energy_derivative)


@dataclass(frozen=True, slots=True)
class BoundHydrogenEnergyReference:
    """One bound-H2 chemical internal-energy increment on the native gas zero.

    With negligible condensed-phase PV, e_bound = h_H2,ref - DeltaH_des,ref.
    Thus closed-system absorption DeltaU = P*v_mol - DeltaH_des at reference,
    which becomes RT - DeltaH_des for an ideal gas, rather than -DeltaH_des.
    Constant solid heat capacity is independent of loading in this reduced level.
    """

    gas_reference_state: ThermoState
    hydrogen_molar_mass_kg_mol: float
    desorption_enthalpy_j_mol_h2: float
    evidence_id: str

    def __post_init__(self):
        if type(self.gas_reference_state) is not ThermoState:
            raise TypeError("Bound-H reference requires the native gas ThermoState")
        finite(self.hydrogen_molar_mass_kg_mol, "reference molar mass", positive=True)
        if finite(self.desorption_enthalpy_j_mol_h2, "reference desorption enthalpy") < 0:
            raise ValueError("Desorption enthalpy must be nonnegative")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare reference-heat provenance or an authored verification identity")

    @property
    def bound_energy_j_mol_h2(self):
        return (self.gas_reference_state.enthalpy_j_kg*self.hydrogen_molar_mass_kg_mol
                - self.desorption_enthalpy_j_mol_h2)

    @property
    def reference_absorption_internal_energy_j_mol_h2(self):
        return (self.bound_energy_j_mol_h2
                - self.gas_reference_state.internal_energy_j_kg*self.hydrogen_molar_mass_kg_mol)

    @classmethod
    def from_gas(cls, gas: HydrideGasThermodynamics, *, temperature_k: float,
                 pressure_pa: float, desorption_enthalpy_j_mol_h2: float, evidence_id: str):
        return cls(gas.state_pt(pressure_pa, temperature_k), gas.molar_mass_kg_mol,
                   desorption_enthalpy_j_mol_h2, evidence_id)


@dataclass(frozen=True, slots=True)
class FiniteHydrideDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_gas_mass_kg: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)
        if (self.minimum_temperature_k >= self.maximum_temperature_k
                or self.minimum_pressure_pa >= self.maximum_pressure_pa):
            raise ValueError("Hydride gas/solid domain bounds must increase")


@dataclass(frozen=True, slots=True)
class FiniteHydrideSnapshot:
    time_s: float
    fraction: float
    solid_temperature_k: float
    gas_mass_kg: float
    solid_hydrogen_mass_kg: float
    gas: ThermoState
    gas_internal_energy_j: float
    solid_internal_energy_j: float

    @property
    def total_hydrogen_mass_kg(self):
        return self.gas_mass_kg+self.solid_hydrogen_mass_kg

    @property
    def total_internal_energy_j(self):
        return self.gas_internal_energy_j+self.solid_internal_energy_j


@dataclass(frozen=True, slots=True)
class FiniteHydrideHeatInput:
    bath_temperature_k: float
    gas_heat_w: float = 0.
    solid_heat_w: float = 0.

    def __post_init__(self):
        finite(self.bath_temperature_k, "bath temperature", positive=True)
        finite(self.gas_heat_w, "external gas heat")
        finite(self.solid_heat_w, "external solid heat")


@dataclass(frozen=True, slots=True)
class FiniteHydrideHeatBoundary:
    clock_id: str
    support_start_s: float
    support_end_s: float
    callback: Callable[[float, FiniteHydrideSnapshot], FiniteHydrideHeatInput]
    source_id: str

    def __post_init__(self):
        finite(self.support_start_s, "boundary support start")
        finite(self.support_end_s, "boundary support end")
        if self.support_start_s >= self.support_end_s:
            raise ValueError("Heat-boundary clock support must increase")
        if (not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not isinstance(self.source_id, str) or not self.source_id.strip()
                or not callable(self.callback)):
            raise ValueError("Declare heat-boundary callback, clock and source identities")

    def value(self, time, snapshot):
        if not self.support_start_s <= time <= self.support_end_s:
            raise ValueError("Heat boundary was evaluated outside its explicit clock support")
        value = self.callback(float(time), snapshot)
        if not isinstance(value, FiniteHydrideHeatInput):
            raise TypeError("The heat callback must return FiniteHydrideHeatInput")
        return value


@dataclass(frozen=True, slots=True)
class FiniteHydrideGasPortInput:
    """One signed H2 mass stream with a state on the bed's native basis.

    Positive mass flow enters the bed; negative flow leaves it. Stream enthalpy
    is taken from the original provider state and is never inferred from the
    bed state for an inlet. An outlet must use the exact current bed state.
    """

    mass_flow_kg_s: float
    stream_state: ThermoState
    evidence_id: str

    def __post_init__(self):
        finite(self.mass_flow_kg_s, "signed H2 port mass flow")
        if type(self.stream_state) is not ThermoState:
            raise TypeError("H2 port stream requires an original native ThermoState")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("H2 port flow requires source/evidence identity")

    @property
    def enthalpy_flow_w(self):
        return self.mass_flow_kg_s*self.stream_state.enthalpy_j_kg


@dataclass(frozen=True, slots=True)
class FiniteHydrideGasPortBoundary:
    """Caller-owned H2 stream schedule on the same absolute clock as the bed.

    The callback supplies the signed mass flow and its native stream state.
    The bed still owns the native EOS, finite inventory, existing hydride rates
    and energy balance; this boundary does not calculate a pressure-flow law.
    """

    clock_id: str
    support_start_s: float
    support_end_s: float
    callback: Callable[[float, FiniteHydrideSnapshot], FiniteHydrideGasPortInput]
    source_id: str

    def __post_init__(self):
        finite(self.support_start_s, "H2 port support start")
        finite(self.support_end_s, "H2 port support end")
        if self.support_start_s >= self.support_end_s:
            raise ValueError("H2 port clock support must increase")
        if (not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not isinstance(self.source_id, str) or not self.source_id.strip()
                or not callable(self.callback)):
            raise ValueError("Declare H2 port callback, clock and source identities")

    def value(self, time, snapshot):
        if not self.support_start_s <= time <= self.support_end_s:
            raise ValueError("H2 port was evaluated outside its explicit clock support")
        transfer = self.callback(float(time), snapshot)
        if type(transfer) is not FiniteHydrideGasPortInput:
            raise TypeError("H2 port callback must return FiniteHydrideGasPortInput")
        if transfer.evidence_id.strip() != self.source_id.strip():
            raise ValueError("H2 stream evidence must match the retained port schedule source")
        snapshot.gas.basis.require_compatible(transfer.stream_state.basis)
        if (transfer.stream_state.phase not in {"gas", "supercritical_gas", "supercritical"}
                or transfer.stream_state.vapor_mass_fraction not in (None, 1.)):
            raise ValueError("Finite hydride H2 port supports only an explicit single gas-phase stream")
        if transfer.mass_flow_kg_s < 0. and transfer.stream_state is not snapshot.gas:
            raise ValueError("H2 outlet enthalpy must use the exact current bed state")
        return transfer


@dataclass(frozen=True, slots=True)
class FiniteHydrideRates:
    """Instantaneous conserved rates shared by closed and externally ported beds.

    External material flow is positive into the free gas. ``gas_mass_kg_s`` is
    its total derivative after solid uptake; the two are deliberately separate.
    Enthalpy transport uses the same declared gas/reference basis as the bed.
    """

    fraction_s_inv: float
    gas_mass_kg_s: float
    gas_internal_energy_w: float
    solid_temperature_k_s: float
    external_gas_mass_flow_kg_s: float
    external_gas_enthalpy_flow_w: float
    external_gas_heat_w: float
    external_solid_heat_w: float
    material_enthalpy_to_solid_w: float
    gas_solid_heat_to_gas_w: float
    nominal_reaction_heat_w: float
    hydrogen_uptake_kg_s: float
    gas_thermostat_heat_w: float
    solid_thermostat_heat_w: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class FiniteHydrideTrace:
    time_s: np.ndarray
    snapshots: tuple[FiniteHydrideSnapshot, ...]
    integrated_external_gas_heat_j: np.ndarray
    integrated_external_solid_heat_j: np.ndarray
    integrated_material_enthalpy_to_solid_j: np.ndarray
    integrated_gas_solid_heat_to_gas_j: np.ndarray
    integrated_nominal_reaction_heat_j: np.ndarray
    integrated_hydrogen_uptake_kg: np.ndarray
    integrated_gas_thermostat_heat_j: np.ndarray
    integrated_solid_thermostat_heat_j: np.ndarray
    gas_energy_residual_j: np.ndarray
    solid_energy_residual_j: np.ndarray
    total_energy_residual_j: np.ndarray
    total_hydrogen_residual_kg: np.ndarray
    gas_transfer_residual_kg: np.ndarray
    solid_transfer_residual_kg: np.ndarray
    gas_integrated_state_residual_j: np.ndarray
    clock_id: str
    termination: str
    event_time_s: float | None
    isothermal_temperature_k: float | None
    gas_thermodynamics: HydrideGasThermodynamics
    energy_reference: BoundHydrogenEnergyReference
    native_solution: object
    energy_scale_j: float
    integrated_external_gas_mass_kg: np.ndarray | None = None
    integrated_external_gas_enthalpy_j: np.ndarray | None = None
    gas_port_boundary: FiniteHydrideGasPortBoundary | None = None
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _gas_state_content: tuple[str, ...] = field(default=(), init=False, repr=False, compare=False)

    def require_current(self):
        """Recheck accepted H2 states against the retained property provider."""
        from ..adapters.result_provenance import recorded_content_sha256

        if (not self._gas_state_content or self._gas_state_content != tuple(
                recorded_content_sha256(snapshot.gas) for snapshot in self.snapshots)):
            raise ValueError("Finite hydride retained gas state changed after issuance")
        for snapshot in self.snapshots:
            self.gas_thermodynamics.basis.require_compatible(snapshot.gas.basis)
            current = self.gas_thermodynamics.state_pt(
                snapshot.gas.pressure_pa, snapshot.gas.temperature_k
            )
            if type(current) is not type(snapshot.gas):
                raise ValueError("Finite hydride trace no longer matches its retained gas provider")
            # Reflashing returned P,T can differ by a few floating-point ulps.
            # Identity/phase/quality and optional capability presence remain exact.
            for item in fields(ThermoState):
                actual, admitted = getattr(current, item.name), getattr(snapshot.gas, item.name)
                if item.name in {"vapor_mass_fraction", "raw_vapor_mass_fraction"}:
                    matches = actual == admitted
                elif isinstance(actual, float) and isinstance(admitted, float):
                    matches = math.isclose(actual, admitted, rel_tol=1e-12, abs_tol=0.)
                else:
                    matches = actual == admitted
                if not matches:
                    raise ValueError("Finite hydride trace no longer matches its retained gas provider")
        if self.gas_port_boundary is not None:
            if self.gas_port_boundary.clock_id != self.clock_id:
                raise ValueError("Finite hydride trace port clock binding changed")
        return self

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRACE_ISSUERS:
            raise TypeError("Create finite hydride traces through a completed native-provider integration")
        _PENDING_TRACE_ISSUERS.remove(self._issuer_token)
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Finite hydride trace needs an explicit clock identity")
        if type(self.gas_thermodynamics) is not HydrideGasThermodynamics:
            raise TypeError("Trace must retain the declared native hydrogen thermodynamics")
        if type(self.energy_reference) is not BoundHydrogenEnergyReference:
            raise TypeError("Trace must retain its bound-hydrogen energy reference")
        if self.gas_port_boundary is not None:
            if type(self.gas_port_boundary) is not FiniteHydrideGasPortBoundary:
                raise TypeError("Trace gas port must retain its typed issuing boundary")
            if self.gas_port_boundary.clock_id != self.clock_id:
                raise ValueError("Trace gas port and accepted states must share one clock identity")
        if self.native_solution is None:
            raise ValueError("Trace must retain the native integration solution")
        if self.termination not in {"window_end", "gas_inventory_floor"}:
            raise ValueError("Unknown finite hydride termination state")
        time = np.array(_real_numeric_array(self.time_s, "hydride trace time"), copy=True)
        snapshots = tuple(self.snapshots)
        if (time.ndim != 1 or not len(time) or not np.all(np.isfinite(time))
                or np.any(np.diff(time) <= 0) or len(snapshots) != len(time)):
            raise ValueError("Hydride trace requires matching nonempty, strictly ordered sample axes")
        if any(type(snapshot) is not FiniteHydrideSnapshot for snapshot in snapshots):
            raise TypeError("Every hydride output sample must retain its typed physical snapshot")
        if any(snapshot.time_s != time[index] for index, snapshot in enumerate(snapshots)):
            raise ValueError("Hydride snapshot clocks differ from the retained trace time axis")
        for snapshot in snapshots:
            if type(snapshot.gas) is not ThermoState:
                raise TypeError("Every hydride sample must retain its native thermodynamic state")
            HydrideState(snapshot.fraction, snapshot.solid_temperature_k)
        energy_scale = finite(self.energy_scale_j, "integrated energy scale", positive=True)
        if self.isothermal_temperature_k is not None:
            finite(self.isothermal_temperature_k, "isothermal temperature", positive=True)
        if self.event_time_s is None:
            if self.termination != "window_end":
                raise ValueError("A non-event termination cannot name an integration event time")
        elif (self.termination != "gas_inventory_floor"
                or finite(self.event_time_s, "hydride event time") != time[-1]):
            raise ValueError("Gas-floor event must be the final retained trace sample")

        vector_names = (
            "integrated_external_gas_heat_j", "integrated_external_solid_heat_j",
            "integrated_material_enthalpy_to_solid_j", "integrated_gas_solid_heat_to_gas_j",
            "integrated_nominal_reaction_heat_j", "integrated_hydrogen_uptake_kg",
            "integrated_gas_thermostat_heat_j", "integrated_solid_thermostat_heat_j",
            "gas_energy_residual_j", "solid_energy_residual_j", "total_energy_residual_j",
            "total_hydrogen_residual_kg", "gas_transfer_residual_kg",
            "solid_transfer_residual_kg", "gas_integrated_state_residual_j",
            "integrated_external_gas_mass_kg", "integrated_external_gas_enthalpy_j",
        )
        arrays = {}
        for name in vector_names:
            supplied = getattr(self, name)
            if supplied is None and name in {
                "integrated_external_gas_mass_kg", "integrated_external_gas_enthalpy_j"
            }:
                supplied = np.zeros(time.shape)
            value = np.array(_real_numeric_array(supplied, name), copy=True)
            if value.shape != time.shape or not np.all(np.isfinite(value)):
                raise ValueError("Hydride trace ledger vectors must be finite and match its sample axis")
            value = immutable_array(value, name=name)
            arrays[name] = value
        if any(arrays[name][0] != 0. for name in (
            *vector_names[:8], "integrated_external_gas_mass_kg", "integrated_external_gas_enthalpy_j"
        )):
            raise ValueError("Integrated hydride energy and uptake ledgers must start at zero")
        if self.gas_port_boundary is None:
            if (np.any(arrays["integrated_external_gas_mass_kg"] != 0.)
                    or np.any(arrays["integrated_external_gas_enthalpy_j"] != 0.)):
                raise ValueError("Nonzero external H2 ledgers require their original port boundary")
        elif not (
            self.gas_port_boundary.support_start_s <= time[0] < time[-1]
            <= self.gas_port_boundary.support_end_s
        ):
            raise ValueError("Accepted H2 port trace lies outside its retained boundary support")

        gas_mass = np.array([finite(s.gas_mass_kg, "trace gas mass", positive=True)
                             for s in snapshots])
        solid_mass = np.array([finite(s.solid_hydrogen_mass_kg, "trace solid hydrogen mass")
                               for s in snapshots])
        if np.any(solid_mass < 0):
            raise ValueError("Solid hydrogen inventory cannot be negative")
        gas_energy = np.array([finite(s.gas_internal_energy_j, "trace gas internal energy")
                               for s in snapshots])
        solid_energy = np.array([finite(s.solid_internal_energy_j, "trace solid internal energy")
                                 for s in snapshots])
        for snapshot, mass in zip(snapshots, gas_mass, strict=True):
            self.gas_thermodynamics.basis.require_compatible(snapshot.gas.basis)
            if not math.isclose(snapshot.gas_internal_energy_j,
                                mass*snapshot.gas.internal_energy_j_kg,
                                rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError("Hydride trace gas energy differs from its retained native state")
        if not self.gas_thermodynamics.basis == self.energy_reference.gas_reference_state.basis:
            raise ValueError("Hydride trace native gas and energy-reference bases differ")
        specific_volumes = np.array([mass/snapshot.gas.density_kg_m3
                                     for mass, snapshot in zip(gas_mass, snapshots, strict=True)])
        if not np.allclose(specific_volumes, specific_volumes[0], rtol=1e-8, atol=0.):
            raise ValueError("Hydride trace gas snapshots do not share one fixed free volume")
        occupied = np.array([snapshot.fraction for snapshot in snapshots])
        if (not np.all(np.isfinite(occupied)) or np.any((occupied < 0.) | (occupied > 1.))
                or np.any((occupied == 0.) & (solid_mass != 0.))):
            raise ValueError("Hydride trace fraction and solid hydrogen inventories disagree")
        positive = occupied > 0.
        if np.any(positive) and not np.allclose(
                solid_mass[positive]/occupied[positive],
                (solid_mass/np.where(positive, occupied, 1.))[positive][0],
                rtol=1e-12, atol=1e-14):
            raise ValueError("Hydride trace solid inventory does not use one fixed capacity")

        qgas = arrays["integrated_external_gas_heat_j"]
        qsolid = arrays["integrated_external_solid_heat_j"]
        material = arrays["integrated_material_enthalpy_to_solid_j"]
        qgs = arrays["integrated_gas_solid_heat_to_gas_j"]
        uptake = arrays["integrated_hydrogen_uptake_kg"]
        mg0, ms0 = gas_mass[0], solid_mass[0]
        expected = {
            "gas_energy_residual_j": (gas_energy-gas_energy[0]+material-qgs-qgas
                                       -arrays["integrated_external_gas_enthalpy_j"]),
            "solid_energy_residual_j": solid_energy-solid_energy[0]-material+qgs-qsolid,
            "total_energy_residual_j": (gas_energy+solid_energy-gas_energy[0]
                                         -solid_energy[0]-qgas-qsolid
                                         -arrays["integrated_external_gas_enthalpy_j"]),
            "total_hydrogen_residual_kg": (gas_mass+solid_mass-mg0-ms0
                                           -arrays["integrated_external_gas_mass_kg"]),
            "gas_transfer_residual_kg": (gas_mass-mg0+uptake
                                         -arrays["integrated_external_gas_mass_kg"]),
            "solid_transfer_residual_kg": solid_mass-ms0-uptake,
        }
        if any(not np.array_equal(arrays[name], value) for name, value in expected.items()):
            raise ValueError("Hydride trace conservation ledgers do not reconstruct from samples")
        time = immutable_array(time, name="hydride trace time")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "snapshots", snapshots)
        from ..adapters.result_provenance import recorded_content_sha256

        object.__setattr__(self, "_gas_state_content", tuple(
            recorded_content_sha256(snapshot.gas) for snapshot in snapshots))
        object.__setattr__(self, "energy_scale_j", energy_scale)
        for name, value in arrays.items():
            object.__setattr__(self, name, value)


class FiniteHydrideIntegrationError(RuntimeError):
    def __init__(self, message, *, trial_time_s, trial_values, gas_thermodynamics,
                 native_solution=None, cause=None):
        super().__init__(message)
        self.trial_time_s = trial_time_s
        self.trial_values = np.array(trial_values, copy=True)
        self.gas_thermodynamics = gas_thermodynamics
        self.native_solution = native_solution
        self.cause = cause
        self.__cause__ = cause


class FiniteHydrideBed:
    """A constant-free-volume gas/solid core, with a closed simulation convenience.

    The host owns these new conservation equations and delegates every gas state,
    fugacity and derivative to native thermodynamics. Existing HydrideKinetics
    owns the reaction rate, including hysteresis. ``simulate`` remains closed;
    ported compositions reuse ``snapshot_from_inventory`` and ``rates`` directly.
    """

    def __init__(self, parameters: HydrideParameters, kinetics: HydrideKinetics,
                 gas: HydrideGasThermodynamics, energy_reference: BoundHydrogenEnergyReference,
                 domain: FiniteHydrideDomain, *, free_gas_volume_m3: float,
                 gas_solid_conductance_w_k: float, gas_ambient_conductance_w_k: float = 0.):
        finite(free_gas_volume_m3, "free gas volume", positive=True)
        for value in (gas_solid_conductance_w_k, gas_ambient_conductance_w_k):
            if finite(value, "thermal conductance") < 0:
                raise ValueError("Thermal conductances must be nonnegative")
        gas.basis.require_compatible(energy_reference.gas_reference_state.basis)
        for mass in (parameters.hydrogen_molar_mass_kg_mol,
                     energy_reference.hydrogen_molar_mass_kg_mol):
            if not math.isclose(mass, gas.molar_mass_kg_mol, rel_tol=1e-10, abs_tol=0.):
                raise ValueError("Gas, capacity and energy-reference H2 molar masses differ")
        if parameters.reaction_heat_j_mol_h2 != energy_reference.desorption_enthalpy_j_mol_h2:
            raise ValueError("Existing hydride heat and bound-H energy reference disagree")
        if (isinstance(kinetics.equilibrium, VanthoffPlateau)
                and kinetics.equilibrium.desorption_enthalpy_j_mol_h2
                != energy_reference.desorption_enthalpy_j_mol_h2):
            raise ValueError("Vanthoff equilibrium and caloric reference desorption enthalpies disagree")
        self.parameters, self.kinetics, self.gas = parameters, kinetics, gas
        self.energy_reference, self.domain = energy_reference, domain
        self.free_gas_volume_m3 = free_gas_volume_m3
        self.gas_solid_conductance_w_k = gas_solid_conductance_w_k
        self.gas_ambient_conductance_w_k = gas_ambient_conductance_w_k
        checked = gas.state_pt(energy_reference.gas_reference_state.pressure_pa,
                               energy_reference.gas_reference_state.temperature_k)
        for name in ("density_kg_m3", "enthalpy_j_kg", "internal_energy_j_kg"):
            if not math.isclose(getattr(checked, name),
                                getattr(energy_reference.gas_reference_state, name),
                                rel_tol=1e-10, abs_tol=1e-5):
                raise ValueError("Gas reference enthalpy/internal energy/density no longer matches native thermodynamics")
        self._require_gas(checked)
        self._require_gas(energy_reference.gas_reference_state)

    def _require_gas(self, state):
        self.gas.basis.require_compatible(state.basis)
        d = self.domain
        if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Finite hydride level requires a single gas/supercritical-H2 phase")
        if state.vapor_mass_fraction not in (None, 1.):
            raise ValueError("A condensed or two-phase H2 inventory is outside this model")
        if not d.minimum_temperature_k <= state.temperature_k <= d.maximum_temperature_k:
            raise ValueError("Gas temperature is outside the declared hydride domain")
        if not d.minimum_pressure_pa <= state.pressure_pa <= d.maximum_pressure_pa:
            raise ValueError("Gas pressure is outside the declared hydride domain")

    def snapshot_from_inventory(self, time_s: float, fraction: float, gas_mass_kg: float,
                                gas_internal_energy_j: float, solid_temperature_k: float, *,
                                isothermal_temperature_k: float | None = None):
        """Recover this bed's physical state from explicit finite gas inventories.

        This is also the closed simulator's sole state reconstruction path. The
        positive gas floor is an integration event, so positive trial masses on
        either side of that floor remain evaluable for a bracketed root.
        """
        finite(time_s, "snapshot clock")
        HydrideState(float(fraction), float(solid_temperature_k))
        mass = finite(gas_mass_kg, "finite gas mass", positive=True)
        energy = finite(gas_internal_energy_j, "finite gas internal energy")
        if isothermal_temperature_k is not None:
            finite(isothermal_temperature_k, "isothermal temperature", positive=True)
            if not callable(self.gas.state_rho_t):
                raise ValueError("Isothermal state reconstruction requires native rho-T thermodynamics")
        if not self.domain.minimum_temperature_k <= solid_temperature_k <= self.domain.maximum_temperature_k:
            raise ValueError("Solid temperature is outside the declared hydride domain")
        density = mass/self.free_gas_volume_m3
        state = (self.gas.state_rho_u(density, energy/mass)
                 if isothermal_temperature_k is None else
                 self.gas.state_rho_t(density, isothermal_temperature_k))
        self._require_gas(state)
        ref, p = self.energy_reference, self.parameters
        solid_energy = (p.heat_capacity_j_k*(solid_temperature_k-ref.gas_reference_state.temperature_k)
                        +p.hydrogen_capacity_kg/self.gas.molar_mass_kg_mol
                        *fraction*ref.bound_energy_j_mol_h2)
        return FiniteHydrideSnapshot(float(time_s), float(fraction), float(solid_temperature_k),
            mass, float(p.hydrogen_capacity_kg*fraction), state,
            mass*state.internal_energy_j_kg, float(solid_energy))

    def rates(self, state: FiniteHydrideSnapshot, heat: FiniteHydrideHeatInput, *,
              gas_mass_flow_kg_s: float = 0., gas_enthalpy_flow_w: float = 0.,
              isothermal_temperature_k: float | None = None) -> FiniteHydrideRates:
        """Existing kinetics/thermal/reference core with optional external ports.

        Gas material enthalpy and bound-H energy already account for sorption;
        nominal reaction heat is an observable and is never added a second time.
        A fixed-T reference includes thermostat duty for the *total* gas-mass
        derivative, including external flow as well as sorption.
        """
        if not isinstance(heat, FiniteHydrideHeatInput):
            raise TypeError("FiniteHydrideHeatInput is required")
        if not isinstance(state, FiniteHydrideSnapshot):
            raise TypeError("A physical FiniteHydrideSnapshot is required")
        self._require_gas(state.gas)
        HydrideState(state.fraction, state.solid_temperature_k)
        if not self.domain.minimum_temperature_k <= state.solid_temperature_k <= self.domain.maximum_temperature_k:
            raise ValueError("Solid temperature is outside the declared hydride domain")
        mass_flow = finite(gas_mass_flow_kg_s, "net external gas mass flow")
        enthalpy_flow = finite(gas_enthalpy_flow_w, "net external material enthalpy flow")
        p, gas, ref = self.parameters, self.gas, self.energy_reference
        expected_solid_energy = (p.heat_capacity_j_k
            *(state.solid_temperature_k-ref.gas_reference_state.temperature_k)
            +p.hydrogen_capacity_kg/gas.molar_mass_kg_mol*state.fraction*ref.bound_energy_j_mol_h2)
        for actual, expected, tolerance in (
                (state.gas_mass_kg, state.gas.density_kg_m3*self.free_gas_volume_m3, 1e-14),
                (state.solid_hydrogen_mass_kg, p.hydrogen_capacity_kg*state.fraction, 1e-14),
                (state.gas_internal_energy_j, state.gas_mass_kg*state.gas.internal_energy_j_kg, 1e-8),
                (state.solid_internal_energy_j, expected_solid_energy, 1e-8)):
            if not math.isclose(finite(actual, "snapshot inventory/energy"), expected,
                                rel_tol=1e-10, abs_tol=tolerance):
                raise ValueError("Bed snapshot inventory/energy differs from its native state/reference")
        fugacity = finite(gas.fugacity_pa(state.gas), "native hydrogen fugacity", positive=True)
        rate = self.kinetics.fraction_rate_s_inv(state.fraction, state.solid_temperature_k, fugacity)
        uptake = p.hydrogen_capacity_kg*rate
        molar_uptake = uptake/gas.molar_mass_kg_mol
        if rate >= 0:
            transfer_h = state.gas.enthalpy_j_kg
        else:
            transfer_state = gas.state_pt(state.gas.pressure_pa, state.solid_temperature_k)
            self._require_gas(transfer_state)
            transfer_h = transfer_state.enthalpy_j_kg
        material_power = uptake*transfer_h
        gas_solid_heat = self.gas_solid_conductance_w_k*(state.solid_temperature_k-state.gas.temperature_k)
        gas_heat = (heat.gas_heat_w+self.gas_ambient_conductance_w_k
                    *(heat.bath_temperature_k-state.gas.temperature_k))
        solid_heat = (heat.solid_heat_w+p.ambient_conductance_w_k
                      *(heat.bath_temperature_k-state.solid_temperature_k))
        gas_mass_rate = mass_flow-uptake
        gas_energy_rate = -material_power+gas_solid_heat+gas_heat+enthalpy_flow
        solid_energy_rate = material_power-gas_solid_heat+solid_heat
        gas_thermostat = solid_thermostat = 0.
        if isothermal_temperature_k is None:
            solid_temperature_rate = (solid_energy_rate
                -molar_uptake*ref.bound_energy_j_mol_h2)/p.heat_capacity_j_k
        else:
            finite(isothermal_temperature_k, "isothermal temperature", positive=True)
            if (not callable(gas.isothermal_mass_energy_derivative)
                    or state.gas.temperature_k != isothermal_temperature_k
                    or state.solid_temperature_k != isothermal_temperature_k):
                raise ValueError("Isothermal rates require matching held temperatures and native derivative")
            fixed_t_energy_derivative = finite(gas.isothermal_mass_energy_derivative(state.gas),
                                               "native fixed-T inventory derivative")
            constrained_gas_energy_rate = gas_mass_rate*fixed_t_energy_derivative
            gas_thermostat = constrained_gas_energy_rate-gas_energy_rate
            solid_thermostat = molar_uptake*ref.bound_energy_j_mol_h2-solid_energy_rate
            gas_heat += gas_thermostat
            solid_heat += solid_thermostat
            gas_energy_rate = constrained_gas_energy_rate
            solid_temperature_rate = 0.
        return FiniteHydrideRates(rate, gas_mass_rate, gas_energy_rate, solid_temperature_rate,
            mass_flow, enthalpy_flow, gas_heat, solid_heat, material_power, gas_solid_heat,
            molar_uptake*p.reaction_heat_j_mol_h2, uptake, gas_thermostat, solid_thermostat)

    def simulate(self, time_s, initial_solid: HydrideState, initial_gas: ThermoState, *,
                 boundary: FiniteHydrideHeatBoundary, clock_id: str, maximum_step_s: float,
                 relative_tolerance: float = 1e-9, energy_scale_j: float = 1e3,
                 isothermal_temperature_k: float | None = None,
                 gas_port: FiniteHydrideGasPortBoundary | None = None) -> FiniteHydrideTrace:
        """Integrate a closed bed or one bed with an explicit signed H2 stream.

        A supplied gas port contributes native stream enthalpy and net material
        to cumulative trace ledgers. It does not provide a pressure-flow law.
        """
        times = np.asarray(time_s, dtype=float)
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or np.any(np.diff(times) <= 0)):
            raise ValueError("Finite hydride output times must be finite and strictly increasing")
        finite(maximum_step_s, "maximum integration step", positive=True)
        finite(energy_scale_j, "integrated energy scale", positive=True)
        if not 0 < finite(relative_tolerance, "relative integration tolerance") < 1:
            raise ValueError("Relative integration tolerance must lie in (0,1)")
        if (not isinstance(clock_id, str) or not clock_id.strip()
                or not isinstance(boundary.clock_id, str) or boundary.clock_id != clock_id):
            raise ValueError("Heat and hydride absolute clock identities differ")
        if not boundary.support_start_s <= times[0] < times[-1] <= boundary.support_end_s:
            raise ValueError("Requested hydride window exceeds heat-boundary support")
        if gas_port is not None:
            if type(gas_port) is not FiniteHydrideGasPortBoundary:
                raise TypeError("gas_port must be a FiniteHydrideGasPortBoundary")
            if gas_port.clock_id != clock_id or not (
                gas_port.support_start_s <= times[0] < times[-1] <= gas_port.support_end_s
            ):
                raise ValueError("H2 port and hydride run must share one supported absolute clock window")
        self._require_gas(initial_gas)
        p, d, gas, ref = self.parameters, self.domain, self.gas, self.energy_reference
        if not d.minimum_temperature_k <= initial_solid.temperature_k <= d.maximum_temperature_k:
            raise ValueError("Solid temperature is outside the declared hydride domain")
        mass0 = initial_gas.density_kg_m3*self.free_gas_volume_m3
        if mass0 <= d.minimum_gas_mass_kg:
            raise ValueError("Initial gas mass must exceed the explicit finite-inventory floor")
        recovered = gas.state_rho_u(initial_gas.density_kg_m3, initial_gas.internal_energy_j_kg)
        for name in ("temperature_k", "pressure_pa"):
            if not math.isclose(getattr(recovered, name), getattr(initial_gas, name), rel_tol=1e-8):
                raise ValueError("Initial gas state is inconsistent with native DU thermodynamics")
        self._require_gas(recovered)
        if isothermal_temperature_k is not None:
            finite(isothermal_temperature_k, "isothermal temperature", positive=True)
            if (not callable(gas.state_rho_t)
                    or not callable(gas.isothermal_mass_energy_derivative)):
                raise ValueError("Isothermal mode needs native rho-T and fixed-T mass-energy derivatives")
            if (initial_solid.temperature_k != isothermal_temperature_k
                    or initial_gas.temperature_k != isothermal_temperature_k):
                raise ValueError("Isothermal gas and solid must start at the declared thermostat temperature")
        capacity = p.hydrogen_capacity_kg
        x0 = initial_solid.fraction
        energy0 = mass0*initial_gas.internal_energy_j_kg

        def snapshot(time, values):
            fraction, integrated_ug, solid_temperature = values[:3]
            external_mass = values[11]
            mass = mass0-capacity*(fraction-x0)+external_mass
            if mass <= 0:
                raise ValueError("A numerical trial exhausted the finite gas; refine the time step")
            return self.snapshot_from_inventory(time, fraction, mass, integrated_ug*energy_scale_j,
                solid_temperature, isothermal_temperature_k=isothermal_temperature_k)

        last_time, last_values = float(times[0]), np.array([x0, energy0/energy_scale_j,
                                                           initial_solid.temperature_k]+[0.]*10)

        def rhs(time, values):
            nonlocal last_time, last_values
            last_time, last_values = float(time), values.copy()
            state = snapshot(time, values)
            heat = boundary.value(time, state)
            if gas_port is None:
                rates = self.rates(state, heat, isothermal_temperature_k=isothermal_temperature_k)
            else:
                transfer = gas_port.value(time, state)
                rates = self.rates(
                    state,
                    heat,
                    gas_mass_flow_kg_s=transfer.mass_flow_kg_s,
                    gas_enthalpy_flow_w=transfer.enthalpy_flow_w,
                    isothermal_temperature_k=isothermal_temperature_k,
                )
            return [rates.fraction_s_inv, rates.gas_internal_energy_w/energy_scale_j,
                    rates.solid_temperature_k_s, rates.external_gas_heat_w/energy_scale_j,
                    rates.external_solid_heat_w/energy_scale_j,
                    rates.material_enthalpy_to_solid_w/energy_scale_j,
                    rates.gas_solid_heat_to_gas_w/energy_scale_j,
                    rates.nominal_reaction_heat_w/energy_scale_j, rates.hydrogen_uptake_kg_s,
                    rates.gas_thermostat_heat_w/energy_scale_j,
                    rates.solid_thermostat_heat_w/energy_scale_j,
                    rates.external_gas_mass_flow_kg_s,
                    rates.external_gas_enthalpy_flow_w/energy_scale_j]

        def gas_floor(time, values):
            return (mass0-capacity*(values[0]-x0)+values[11]
                    -d.minimum_gas_mass_kg)

        gas_floor.terminal, gas_floor.direction = True, -1
        solution = None
        try:
            solution = solve_ivp(rhs, (float(times[0]), float(times[-1])), last_values,
                method="DOP853", t_eval=times, events=gas_floor,
                rtol=relative_tolerance,
                atol=[1e-12, 1e-11, 1e-8, 1e-11, 1e-11, 1e-11, 1e-11, 1e-11,
                      1e-13, 1e-11, 1e-11, 1e-13, 1e-11],
                max_step=maximum_step_s)
            if not solution.success:
                raise RuntimeError(solution.message)
            output_time, output_values = solution.t.copy(), solution.y.copy()
            event_time = float(solution.t_events[0][0]) if len(solution.t_events[0]) else None
            if event_time is not None and output_time[-1] != event_time:
                output_time = np.append(output_time, event_time)
                output_values = np.column_stack((output_values, solution.y_events[0][0]))
            snapshots = tuple(snapshot(t, values) for t, values in
                              zip(output_time, output_values.T, strict=True))
        except Exception as exc:
            raise FiniteHydrideIntegrationError(f"Finite hydride integration failed: {exc}",
                trial_time_s=last_time, trial_values=last_values, gas_thermodynamics=gas,
                native_solution=solution, cause=exc) from exc
        qgas, qsolid, material, qgs, nominal = output_values[3:8]*energy_scale_j
        uptake = output_values[8]
        thermostat_gas, thermostat_solid = output_values[9:11]*energy_scale_j
        external_mass = output_values[11]
        external_enthalpy = output_values[12]*energy_scale_j
        ug = np.array([s.gas_internal_energy_j for s in snapshots])
        us = np.array([s.solid_internal_energy_j for s in snapshots])
        mg = np.array([s.gas_mass_kg for s in snapshots])
        ms = np.array([s.solid_hydrogen_mass_kg for s in snapshots])
        gas_residual = ug-ug[0]+material-qgs-qgas-external_enthalpy
        solid_residual = us-us[0]-material+qgs-qsolid
        total_hydrogen = mg+ms-mg[0]-ms[0]-external_mass
        gas_transfer = mg-mg[0]+uptake-external_mass
        total_energy = ug+us-ug[0]-us[0]-qgas-qsolid-external_enthalpy
        return FiniteHydrideTrace(output_time, snapshots, qgas, qsolid, material, qgs, nominal,
            uptake, thermostat_gas, thermostat_solid, gas_residual, solid_residual,
            total_energy, total_hydrogen, gas_transfer, ms-ms[0]-uptake,
            ug-output_values[1]*energy_scale_j,
            clock_id, "gas_inventory_floor" if event_time is not None else "window_end", event_time,
            isothermal_temperature_k, gas, ref, solution, energy_scale_j,
            external_mass, external_enthalpy, gas_port, _issue_trace_token())
