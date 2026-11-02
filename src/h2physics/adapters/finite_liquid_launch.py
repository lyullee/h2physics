"""Accepted finite equipment outlet bins with explicit liquid state projections.

Native accepted-sample outlet enthalpy quadrature remains the reference. Each
bin needs a caller-selected representative liquid state and projection evidence;
the source's existing fixed state is never reused as an evolving outlet state.
"""

from dataclasses import dataclass, field
from math import isclose

from ..core import ThermoState, finite
from .droplet_transport import flash_initial_liquid_release
from .facility_protection import FiniteFacilitySource
from .parcel_population import run_parcel_population


@dataclass(frozen=True, slots=True)
class LiquidLaunchBin:
    index: int
    clock_id: str
    frame_id: str
    start_s: float
    end_s: float
    mass_kg: float
    representative_state: ThermoState
    native_outlet_enthalpy_j: float
    projected_enthalpy_j: float
    enthalpy_residual_j: float
    projection_evidence_id: str
    native_quadrature: object


@dataclass(frozen=True, slots=True)
class FiniteLiquidLaunch:
    source_binding: FiniteFacilitySource
    states_by_bin: tuple
    projection_evidence_ids: tuple
    native_enthalpy_j: tuple
    projected_enthalpy_j: tuple
    residuals_j: tuple
    absolute_enthalpy_tolerance_j: float
    relative_enthalpy_tolerance: float
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def _payload(self):
        return (id(self.source_binding), tuple((id(s), repr(s)) for s in self.states_by_bin),
                self.projection_evidence_ids, self.native_enthalpy_j,
                self.projected_enthalpy_j, self.residuals_j,
                self.absolute_enthalpy_tolerance_j, self.relative_enthalpy_tolerance)

    def require_current(self):
        if not self._binding or self._payload() != self._binding:
            raise ValueError("Finite liquid launch must retain its issued source/state projection")
        self.source_binding.require_current()
        observed = self.source_binding.energy_projection().native_transport_enthalpy_j
        if observed != self.native_enthalpy_j:
            raise ValueError("Native outlet enthalpy quadrature changed after liquid projection")
        return self

    def bin_ledger(self):
        """Return immutable per-bin accounting without launching any parcel.

        Zero-mass bins retain their declared liquid state/evidence and native
        quadrature. They have no launch operation; nonzero transported energy
        must still satisfy the caller's explicitly supplied projection budget.
        """
        self.require_current()
        source = self.source_binding.source
        projection = self.source_binding.energy_projection()
        rows = tuple(LiquidLaunchBin(
            index, source.location.clock_id, source.location.coordinate_frame_id,
            float(source.edges_s[index]), float(source.edges_s[index+1]),
            float(mass), self.states_by_bin[index], self.native_enthalpy_j[index],
            self.projected_enthalpy_j[index], self.residuals_j[index],
            self.projection_evidence_ids[index], projection.native_integrals[index])
            for index, mass in enumerate(source.mass_kg))
        self.require_current()
        return rows

    def launch_bin(self, index, *, properties, downstream_pressure_pa,
                   phase_equilibrium_evidence_id, launch_time_s, groups_factory,
                   flight_owner_factory, flight_options, distribution_evidence_id):
        """Resolve a bin into caller-declared parcels at an explicit bin launch time.

        The whole integrated bin mass launches at the supplied time as a declared
        temporal projection. This does not reconstruct a continuous spray.
        """
        self.require_current()
        if type(index) is not int or not 0 <= index < len(self.states_by_bin):
            raise ValueError("Select one existing liquid source bin")
        source = self.source_binding.source
        if source.mass_kg[index] <= 0.:
            raise ValueError("A zero-mass source bin has no parcel launch; inspect bin_ledger instead")
        time = finite(launch_time_s, "launch_time_s")
        if not source.edges_s[index] <= time < source.edges_s[index+1]:
            raise ValueError("Launch time must belong to the original half-open source bin")
        options = dict(flight_options)
        if options.get("start_s") != time:
            raise ValueError("Flight start must equal the declared bin launch time")
        flash = flash_initial_liquid_release(properties, self.states_by_bin[index],
            downstream_pressure_pa=downstream_pressure_pa,
            total_release_mass_kg=float(source.mass_kg[index]),
            phase_equilibrium_evidence_id=phase_equilibrium_evidence_id)
        owner = flight_owner_factory(flash)
        groups = groups_factory(flash)
        if owner.boundary.clock_id != source.location.clock_id:
            raise ValueError("Bin launch and flight must preserve the original source clock")
        if owner.boundary.frame_id != source.location.coordinate_frame_id:
            raise ValueError("Bin launch and flight must preserve the source coordinate frame")
        self.require_current()
        result = run_parcel_population(flash, owner, groups,
            distribution_evidence_id=distribution_evidence_id, flight_options=options)
        self.require_current()
        return result

    def scenario_for_bin(self, index, *, scenario_id, launch_options,
                         impact_group_id, impact_owner_factory,
                         pool_options_factory, slab_options_factory=None):
        """Lazily compose one native bin launch with explicit impact/pool owners.

        ``launch_options`` are the named arguments of ``launch_bin`` except its
        bin index. Flashing runs exactly once inside that population node.
        """
        from collections.abc import Mapping
        from types import MappingProxyType

        from ..scenarios import OperationalScenario, ScenarioNode, ScenarioOutput, ScenarioValue
        from .parcel_impact_chain import impact_population_member
        from .parcel_pool_chain import run_deposited_batch_pool, run_parcel_pool_dispersion

        if type(index) is not int or not 0 <= index < len(self.states_by_bin):
            raise ValueError("Select one original finite source bin")
        if not isinstance(launch_options, Mapping):
            raise TypeError("Declare explicit per-bin launch options")
        if any(not callable(factory) for factory in (impact_owner_factory, pool_options_factory)):
            raise TypeError("Declare explicit finite impact and pool factories")
        if slab_options_factory is not None and not callable(slab_options_factory):
            raise TypeError("Optional SLAB factory must be callable")
        options = dict(launch_options)
        if "index" in options:
            raise ValueError("The original source-bin index cannot be overridden")
        if "flight_options" in options:
            options["flight_options"] = MappingProxyType(dict(options["flight_options"]))
        options = MappingProxyType(options)

        def population_operation(binding):
            binding.require_current()
            return binding.launch_bin(index, **options)

        def impact_operation(population):
            self.require_current()
            population.require_current()
            owner = impact_owner_factory(population)
            self.require_current()
            population.require_current()
            return impact_population_member(population, impact_group_id, owner)

        def pool_operation(member):
            self.require_current()
            member.require_current()
            supplied = pool_options_factory(member)
            self.require_current()
            member.require_current()
            if not isinstance(supplied, Mapping):
                raise TypeError("Pool factory must return explicit named arguments")
            if {"step", "impact_owner"} & supplied.keys():
                raise ValueError("Original member owns the impact step and owner")
            result = run_deposited_batch_pool(member.impact_result.steps[0],
                impact_owner=member.impact_owner, **dict(supplied))
            self.require_current()
            member.require_current()
            return result

        nodes = [
            ScenarioNode("population", population_operation,
                {"binding": ScenarioValue(self)}, scenario_id+":native-liquid-bin"),
            ScenarioNode("impact", impact_operation,
                {"population": ScenarioOutput("population")}, scenario_id+":unit-member-impact"),
            ScenarioNode("pool", pool_operation,
                {"member": ScenarioOutput("impact")}, scenario_id+":deposited-stock"),
        ]
        if slab_options_factory is not None:
            def dispersion_operation(pool):
                self.require_current()
                pool.require_current()
                supplied = slab_options_factory(pool)
                self.require_current()
                pool.require_current()
                if not isinstance(supplied, Mapping):
                    raise TypeError("SLAB factory must return explicit named arguments")
                result = run_parcel_pool_dispersion(pool, **dict(supplied))
                self.require_current()
                return result
            nodes.append(ScenarioNode("dispersion", dispersion_operation,
                {"pool": ScenarioOutput("pool")}, scenario_id+":SLAB-slices"))
        return OperationalScenario(scenario_id, tuple(nodes))


def bind_finite_liquid_launch(source_binding, states_by_bin, *, projection_evidence_ids,
                             absolute_enthalpy_tolerance_j, relative_enthalpy_tolerance):
    if type(source_binding) is not FiniteFacilitySource:
        raise TypeError("Use an original admitted finite facility source binding")
    source_binding.require_current()
    states = tuple(states_by_bin)
    evidence = tuple(projection_evidence_ids)
    masses = source_binding.source.mass_kg
    if len(states) != len(masses) or len(evidence) != len(states):
        raise ValueError("Every accepted source mass bin needs a liquid state and evidence")
    absolute = finite(absolute_enthalpy_tolerance_j, "absolute enthalpy tolerance", positive=True)
    relative = finite(relative_enthalpy_tolerance, "relative enthalpy tolerance", positive=True)
    native_projection = source_binding.energy_projection()
    native = native_projection.native_transport_enthalpy_j
    source = source_binding.source
    for index, integral in enumerate(native_projection.native_integrals):
        if (integral.clock_id != source.location.clock_id
                or integral.start_time_s != source.edges_s[index]
                or integral.end_time_s != source.edges_s[index+1]
                or integral.rate_unit != "W" or integral.integral_unit != "J"):
            raise ValueError("Native outlet enthalpy quadrature must match each original source mass bin")
    projected, residuals = [], []
    for mass, state, identity, native_energy in zip(masses, states, evidence, native, strict=True):
        if type(state) is not ThermoState:
            raise TypeError("Liquid launch requires typed pure-fluid per-bin state projections")
        state.__post_init__()
        if state.phase not in {"liquid", "two_phase"} or state.vapor_mass_fraction not in (None, 0.):
            raise ValueError("Per-bin launch state must be liquid or saturated liquid")
        source_binding.source.state.basis.require_compatible(state.basis)
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("Each liquid state projection needs explicit source evidence")
        energy = float(mass)*state.enthalpy_j_kg
        if not isclose(native_energy, energy, abs_tol=absolute, rel_tol=relative):
            raise ValueError("Per-bin liquid enthalpy exceeds its native outlet projection budget")
        projected.append(energy)
        residuals.append(native_energy-energy)
    result = FiniteLiquidLaunch(source_binding, states, evidence, tuple(native),
        tuple(projected), tuple(residuals), absolute, relative)
    object.__setattr__(result, "_binding", result._payload())
    return result.require_current()
