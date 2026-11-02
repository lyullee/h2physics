"""Two finite thermostated rigid gas sides, with native porous transport.

Cantera owns the EOS, bulk mass/species equations and CVODES integration.
The public surface-source extension hook supplies signed membrane kmol/s;
it does not create a chemical surface reaction or a second physical ODE.
"""

import math
from dataclasses import dataclass

import numpy as np

from ..core import Origin, finite
from .cantera_membrane import (
    FLUX_FRAME,
    CanteraDustyGasTransport,
    MembraneEndpoint,
    _array,
    _hash,
    _transport_data,
)
from .cantera_volume import _phase_fingerprint, _snapshot


@dataclass(frozen=True, slots=True)
class FiniteMembraneParameters:
    area_m2: float
    left_volume_m3: float
    right_volume_m3: float
    clock_id: str
    support_start_s: float
    support_end_s: float
    thermal_boundary_id: str
    source_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("area_m2", "left_volume_m3", "right_volume_m3"):
            finite(getattr(self, name), name, positive=True)
        for name in ("clock_id", "thermal_boundary_id", "source_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError("Declare device clock, isothermal boundary and source evidence")
        if finite(self.support_start_s, "support start") >= finite(self.support_end_s, "support end"):
            raise ValueError("Device clock support must increase")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve the finite-device parameter role")


@dataclass(frozen=True, slots=True)
class MembraneIntegrationSettings:
    maximum_time_step_s: float = .1
    relative_tolerance: float = 1e-9
    absolute_tolerance: float = 1e-15
    maximum_steps: int = 30000
    minimum_side_inventory_kg: tuple[float, float] = (1e-12, 1e-12)
    energy_ledger_scale_j: float = 1.
    trial_sum_deviation_budget: float = 1e-6
    accepted_sum_deviation_budget: float = 1e-10
    relative_trial_temperature_budget: float = 1e-6
    relative_trial_volume_budget: float = 1e-6
    species_audit_absolute_kg: float = 1e-10
    energy_audit_absolute_j: float = 1e-6
    audit_relative: float = 1e-7

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            if name not in {"minimum_side_inventory_kg", "maximum_steps"}:
                finite(getattr(self, name), name, positive=True)
        if any(not 0 < getattr(self, n) < 1 for n in ("relative_tolerance", "absolute_tolerance",
                "trial_sum_deviation_budget", "accepted_sum_deviation_budget", "relative_trial_temperature_budget",
                "relative_trial_volume_budget",
                "audit_relative")):
            raise ValueError("Native and audit dimensionless budgets must lie in (0,1)")
        if isinstance(self.maximum_steps, bool) or not isinstance(self.maximum_steps, int) or self.maximum_steps < 1:
            raise ValueError("Native maximum steps must be a positive integer")
        limits = tuple(self.minimum_side_inventory_kg)
        if len(limits) != 2:
            raise ValueError("Declare both finite-side inventory limits")
        for value in limits:
            finite(value, "minimum side inventory", positive=True)
        object.__setattr__(self, "minimum_side_inventory_kg", limits)


@dataclass(frozen=True, slots=True)
class FiniteMembraneSnapshot:
    time_s: float
    sides: tuple
    species_mass_kg: np.ndarray
    molar_flux_mol_m2_s: np.ndarray

    def __post_init__(self):
        for name in ("species_mass_kg", "molar_flux_mol_m2_s"):
            object.__setattr__(self, name, _array(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class NativeFiniteMembraneObjects:
    reactors: tuple
    network: object
    initial_transport_result: object
    connection: object


@dataclass(frozen=True, slots=True)
class FiniteMembraneTrace:
    parameters: FiniteMembraneParameters
    settings: MembraneIntegrationSettings
    geometry: object
    species: tuple[str, ...]
    time_s: np.ndarray
    snapshots: tuple[FiniteMembraneSnapshot, ...]
    species_transfer_kg: np.ndarray
    enthalpy_transfer_j: np.ndarray
    thermostat_heat_j: np.ndarray
    side_species_residual_kg: np.ndarray
    side_energy_residual_j: np.ndarray
    combined_species_residual_kg: np.ndarray
    combined_internal_energy_residual_j: np.ndarray
    maximum_accepted_sum_deviation: float
    maximum_native_trial_sum_deviation: float
    maximum_native_trial_temperature_deviation_k: float
    maximum_native_trial_relative_volume_deviation: float
    evaluated_clock_bounds_s: tuple[float, float]
    native: NativeFiniteMembraneObjects
    frame: str = FLUX_FRAME
    thermal_closure: str = "same prescribed T; separate required thermostats; transported species partial H"

    def __post_init__(self):
        for name in ("time_s", "species_transfer_kg", "enthalpy_transfer_j", "thermostat_heat_j",
                     "side_species_residual_kg", "side_energy_residual_j", "combined_species_residual_kg",
                     "combined_internal_energy_residual_j"):
            object.__setattr__(self, name, _array(getattr(self, name)))

    @property
    def combined_mass_residual_kg(self):
        return _array(self.combined_species_residual_kg.sum(axis=1))

    @property
    def side_mass_residual_kg(self):
        return _array(self.side_species_residual_kg.sum(axis=2))


class FiniteMembraneIntegrationError(RuntimeError):
    """Actual native network, partial state, accepted prefix and first failure."""

    def __init__(self, message, *, native, snapshots, integrals, triggering_time_s, trace=None):
        self.native, self.snapshots, self.trace = native, tuple(snapshots), trace
        self.integrals = _array(integrals, finite_only=False)
        self.triggering_time_s = triggering_time_s
        self.last_accepted_time_s = self.snapshots[-1].time_s if self.snapshots else None
        self.native_time_s = float(native.network.time)
        self.native_states = tuple(_array(r.phase.state, finite_only=False) for r in native.reactors)
        self.native_ledgers = tuple(_array(r.ledger, finite_only=False) for r in native.reactors)
        self.triggering_native_states = native.connection.first_error_native_states
        super().__init__(message)


class _NativeConnection:
    def __init__(self, prepared, parameters, geometry, settings, transport):
        self.prepared, self.parameters, self.geometry, self.settings = prepared, parameters, geometry, settings
        self.transport = transport
        self.kernel = prepared.native_dusty_gas
        self.kernel_fingerprint = _phase_fingerprint(self.kernel)
        self.source_state = prepared.source_phase.state.copy()
        self.source_basis = prepared.source_phase.basis
        self.source_transport = _hash(_transport_data(prepared.source_phase))
        self.transport_binding = (transport.phase_factory, transport.mechanism_basis, transport.evidence)
        self.reactors = ()
        self.first_error, self.error_time = None, None
        self.first_error_native_states = ()
        self.last_native_flux_kmol_m2_s, self.last_flux_time_s = None, None
        self.clock_bounds = [math.inf, -math.inf]
        self.maximum_trial_sum = self.maximum_trial_temperature = self.maximum_trial_volume = 0.
        self.key, self.rate_kmol_s = None, None

    def rates(self, time):
        if self.first_error is not None:
            raise ValueError("A previous native membrane boundary failure is retained") from self.first_error
        try:
            return self._rates(float(time))
        except Exception as error:
            self.remember_error(error, time)
            raise

    def remember_error(self, error, time):
        if self.first_error is None:
            self.first_error, self.error_time = error, float(time)
            self.first_error_native_states = tuple(_array(r.phase.state, finite_only=False) for r in self.reactors)

    def _rates(self, time):
        p, s, g = self.parameters, self.settings, self.geometry
        self.clock_bounds[0], self.clock_bounds[1] = min(self.clock_bounds[0], time), max(self.clock_bounds[1], time)
        if not p.support_start_s <= finite(time, "native membrane clock") <= p.support_end_s:
            raise ValueError("Native membrane evaluation exceeds explicit clock support")
        if (self.transport.phase_factory, self.transport.mechanism_basis, self.transport.evidence) != self.transport_binding:
            raise ValueError("Constitutive source/evidence binding changed")
        source = self.prepared.source_phase
        if (_phase_fingerprint(source, include_reactions=True) != self.prepared.source_phase_sha256
                or _hash(_transport_data(source)) != self.source_transport
                or not np.array_equal(source.state, self.source_state) or source.basis != self.source_basis):
            raise ValueError("Native source state/definition changed during finite transport")
        if self.kernel.transport_model != "DustyGas" or _phase_fingerprint(self.kernel) != self.kernel_fingerprint:
            raise ValueError("Private native membrane kernel definition changed")
        temperature = self.prepared.left.temperature_k
        states = []
        for k, (r, audit, fit_audit) in enumerate(zip(self.reactors, self.prepared.phase_copy_audits,
                                                    self.prepared.transport_copy_audits, strict=True)):
            phase = r.phase
            if phase is not self.prepared.owned_endpoint_phases[k]:
                raise ValueError("Native reactor phase identity changed")
            if (_phase_fingerprint(phase, include_reactions=True) != audit.owned_fingerprint
                    or _hash(_transport_data(phase)) != fit_audit.owned_sha256):
                raise ValueError("Owned native thermo/transport definition changed")
            self.prepared.mechanism_basis.require_state(phase.T, phase.P)
            if not phase.min_temp <= phase.T <= phase.max_temp:
                raise ValueError("Native species fit range was exceeded")
            if finite(r.mass, "native side mass", positive=True) <= s.minimum_side_inventory_kg[k]:
                raise ValueError(f"Finite side {k} reached its declared inventory limit")
            expected_volume = (p.left_volume_m3, p.right_volume_m3)[k]
            self.maximum_trial_volume = max(self.maximum_trial_volume, abs(r.volume/expected_volume-1.))
            if (abs(r.volume-expected_volume) > s.relative_trial_volume_budget*expected_volume
                    or r.chemistry_enabled or r.energy_enabled):
                raise ValueError("Native rigid/isothermal/frozen reactor configuration changed")
            y = phase.Y
            deviation = abs(math.fsum(y)-1.)
            self.maximum_trial_sum = max(self.maximum_trial_sum, deviation)
            delta_t = abs(phase.T-temperature)
            self.maximum_trial_temperature = max(self.maximum_trial_temperature, delta_t)
            if (not np.all(np.isfinite(y)) or np.any(y < 0) or deviation > s.trial_sum_deviation_budget
                    or delta_t > s.relative_trial_temperature_budget*temperature):
                raise ValueError("Native trial left the declared unprojected composition/isothermal extension")
            states.append(phase.state.copy())
        key = (time, *(state.tobytes() for state in states))
        if key == self.key:
            return self.rate_kmol_s
        # Reset all native write-only pore parameters. Gross membrane area is
        # applied once; native DustyGas already owns porosity/tortuosity.
        self.kernel.porosity, self.kernel.tortuosity = g.porosity, g.tortuosity
        self.kernel.mean_pore_radius, self.kernel.permeability = g.mean_pore_radius_m, g.permeability_m2
        a, b = (r.phase for r in self.reactors)
        # Native NoNorm trial Y can leave the simplex. Pass raw mass
        # concentrations without host clipping/normalization. Internal trial
        # type is unobservable; the bounded constant-T extension is explicit.
        flux = self.kernel.molar_fluxes(temperature, temperature, a.density_mass, b.density_mass,
                                       a.Y, b.Y, g.thickness_m)
        self.last_native_flux_kmol_m2_s, self.last_flux_time_s = _array(flux, finite_only=False), float(time)
        self.rate_kmol_s = _array(np.asarray(flux)*p.area_m2)
        self.key = key
        return self.rate_kmol_s


class CanteraFiniteMembraneDevice:
    def __init__(self, transport: CanteraDustyGasTransport):
        if not isinstance(transport, CanteraDustyGasTransport):
            raise TypeError("Use the existing actual native DustyGas constitutive owner")
        self.transport = transport

    def run(self, left: MembraneEndpoint, right: MembraneEndpoint, geometry,
            parameters: FiniteMembraneParameters, time_s, *, settings=MembraneIntegrationSettings()):
        times = _array(time_s)
        if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0):
            raise ValueError("Output times must be finite and strictly increasing")
        if (times[0] < parameters.support_start_s
                or times[-1]+settings.maximum_time_step_s > parameters.support_end_s):
            raise ValueError("Output window plus native maximum step must lie in device clock support")
        prepared = self.transport.flux(left, right, geometry)
        ct = self.transport.ct
        ns = len(prepared.species)
        connection = _NativeConnection(prepared, parameters, geometry, settings, self.transport)
        labels = tuple("membrane-species-"+name for name in prepared.species)+("membrane-H", "thermostat-Q")
        scales = np.ones(ns+2)
        scales[-2:] = settings.energy_ledger_scale_j

        class FiniteSide(ct.ExtensibleIdealGasReactor):
            def __init__(self, phase, side, **kwargs):
                self.side, self.ledger = side, np.zeros(ns+2)
                super().__init__(phase, **kwargs)
                self.chemistry_enabled = False

            def after_initialize(self, time):
                self.base_size = self.n_vars
                self.n_vars += len(labels)

            def after_get_state(self, y):
                y[self.base_size:] = self.ledger

            def after_update_state(self, y):
                self.ledger[:] = y[self.base_size:]

            def before_component_name(self, index):
                if index >= self.base_size:
                    return labels[index-self.base_size]

            def before_component_index(self, name):
                if name in labels:
                    return self.base_size+labels.index(name)

            def after_eval_surfaces(self, lhs, rhs, sdot):
                # Public bulk source hook is kmol/s, not kmol/m3/s. The native
                # base applies molecular weights, net mass and dilution terms.
                sdot[:] += (-1., 1.)[self.side]*connection.rates(network.time)

            def after_eval(self, time, lhs, rhs):
                try:
                    rates = (-1., 1.)[self.side]*connection.rates(time)
                    h = np.asarray(self.phase.partial_molar_enthalpies)
                    u = np.asarray(self.phase.partial_molar_int_energies)
                    ledger_rates = np.r_[rates*self.phase.molecular_weights, rates@h, rates@(u-h)]
                    if not np.all(np.isfinite(ledger_rates)):
                        raise ValueError("Membrane boundary energy/species rate is nonfinite")
                    lhs[self.base_size:] = 1.
                    rhs[self.base_size:] = ledger_rates/scales
                except Exception as error:
                    connection.remember_error(error, time)
                    raise

        reactors = tuple(FiniteSide(phase, side=k, clone=False, energy="off", name=("left", "right")[k])
                         for k, phase in enumerate(prepared.owned_endpoint_phases))
        for r, volume, limit in zip(reactors, (parameters.left_volume_m3, parameters.right_volume_m3),
                                    settings.minimum_side_inventory_kg, strict=True):
            r.volume = volume
            if r.mass <= limit:
                raise ValueError("Initial finite side is below its declared inventory limit")
        connection.reactors = reactors
        network = ct.ReactorNet(reactors)
        network.initial_time = float(times[0])
        network.rtol, network.atol = settings.relative_tolerance, settings.absolute_tolerance
        network.max_time_step, network.max_steps = settings.maximum_time_step_s, settings.maximum_steps
        native = NativeFiniteMembraneObjects(reactors, network, prepared, connection)
        snapshots, integrals, trace = [], [], None
        accepted_deviation = 0.

        def capture(time):
            nonlocal accepted_deviation
            rate = connection.rates(time)
            if connection.first_error is not None:
                raise ValueError("A native trial boundary failure was retained") from connection.first_error
            for k, r in enumerate(reactors):
                deviation = abs(math.fsum(r.phase.Y)-1.)
                accepted_deviation = max(accepted_deviation, deviation)
                if deviation > settings.accepted_sum_deviation_budget:
                    raise ValueError("Accepted native composition violates its simplex budget")
                if r.T != left.temperature_k:
                    raise ValueError("Accepted native side departed from prescribed isothermal T")
                if r.volume != (parameters.left_volume_m3, parameters.right_volume_m3)[k]:
                    raise ValueError("Accepted native side departed from its rigid volume")
            snapshots.append(FiniteMembraneSnapshot(time, tuple(_snapshot(time, r) for r in reactors),
                np.array([r.mass*r.phase.Y for r in reactors]), rate/parameters.area_m2*1000.))
            integrals.append(np.array([r.ledger*scales for r in reactors]))

        try:
            network.initialize()
            capture(float(times[0]))
            for time in times[1:]:
                network.advance(float(time))
                capture(float(time))
            values = np.asarray(integrals)
            masses = np.array([s.species_mass_kg for s in snapshots])
            energy = np.array([[side.internal_energy_j for side in s.sides] for s in snapshots])
            species_error = masses-masses[0]-values[:, :, :ns]
            energy_error = energy-energy[0]-values[:, :, -2]-values[:, :, -1]
            combined_species = masses.sum(axis=1)-masses[0].sum(axis=0)
            combined_energy = energy.sum(axis=1)-energy[0].sum()
            trace = FiniteMembraneTrace(parameters, settings, geometry, prepared.species, times,
                tuple(snapshots), values[:, :, :ns], values[:, :, -2], values[:, :, -1], species_error,
                energy_error, combined_species, combined_energy, accepted_deviation,
                connection.maximum_trial_sum, connection.maximum_trial_temperature,
                connection.maximum_trial_volume,
                tuple(connection.clock_bounds), native)
            species_limit = settings.species_audit_absolute_kg+settings.audit_relative*np.max(masses[0])
            energy_limit = settings.energy_audit_absolute_j+settings.audit_relative*np.max(abs(energy))
            if (max(np.max(abs(species_error)), np.max(abs(combined_species))) > species_limit
                    or max(np.max(abs(energy_error)), np.max(abs(combined_energy))) > energy_limit):
                raise ValueError("Finite membrane independent species/energy audit failed")
            return trace
        except Exception as error:
            raise FiniteMembraneIntegrationError(str(error), native=native, snapshots=snapshots,
                integrals=integrals, triggering_time_s=connection.error_time, trace=trace) from error
