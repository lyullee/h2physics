"""Deferred contracts for caloric Euler flow over a branched pipe graph."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-network-closed-equilibrium",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_closed_equilibrium",
            invariants=(
                "equal-single-phase-states-remain-in-equilibrium-across-a-three-branch-junction",
                "closed-network-total-mass-and-total-energy-ledgers-close",
                "junction-trace-retains-pressure-temperature-geometry-clock-and-evidence-identities",
                "network-topology-is-connected-and-every-branch-has-explicit-origin-and-geometry-evidence",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-network-perfect-mixing-balance",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_mixing_balance",
            invariants=(
                "junction-common-pressure-and-temperature-solve-closes-exact-applied-rusanov-mass-and-energy-fluxes",
                "unequal-inlet-temperature-disturbance-propagates-without-silent-phase-switch",
                "adiabatic-perfect-mixing-node-does-not-admit-negative-entropy-production",
                "global-mass-and-total-energy-residuals-account-for-terminal-and-junction-fluxes",
                "trace-is-immutable-and-cannot-be-reissued-by-dataclass-replacement",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-network-fixed-reservoir-contract",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_reservoir_contract",
            invariants=(
                "fixed-reservoir-state-requires-matching-clock-owner-evidence-and-property-basis",
                "terminal-exchange-ledgers-use-the-applied-face-flux",
                "wrong-reservoir-clock-is-rejected-before-time-advancement",
                "network-mass-and-energy-close-against-signed-terminal-transfer",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-network-friction-wall-heat-ledgers",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_source_ledgers",
            invariants=(
                "per-edge-source-maps-require-explicit-identity-clock-owner-and-evidence",
                "darcy-friction-relaxes-momentum-without-adding-or-removing-total-energy",
                "signed-fixed-wall-heat-is-integrated-into-network-total-energy-residual",
                "source-free-network-regression-retains-zero-wall-heat-and-conservative-closure",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-network-finite-reservoir-exchange",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_finite_reservoir_exchange",
            invariants=(
                "finite-reservoir-U-and-mass-use-the-exact-signed-applied-Rusanov-endpoint-flux",
                "fixed-volume-reservoir-state-is-recovered-through-the-same-rho-u-EOS",
                "combined-pipe-and-reservoir-mass-and-energy-ledgers-close-at-each-output-time",
                "finite-reservoir-stock-pressure-temperature-and-provenance-histories-are-retained",
                "finite-reservoir-signed-transfer-is-correct-at-either-edge-orientation",
                "prescribed-fixed-state-reservoir-mode-remains-separate-and-unchanged",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-network-finite-reservoir-rejections",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_finite_reservoir_rejections",
            invariants=(
                "finite-reservoir-inventory-floor-and-ceiling-reject-without-clipping",
                "finite-reservoir-pressure-and-temperature-EOS-domain-bounds-are-enforced",
                "reservoir-node-owner-evidence-origin-clock-and-EOS-basis-must-match-network",
                "invalid-or-depleted-step-does-not-produce-an-accepted-trace",
            ),
        ),
    )


class _SyntheticHydrogenEOS:
    """Authored calorically-perfect closure for software contracts only."""

    def __init__(self):
        from h2physics.core import PropertyBasis

        self.basis = PropertyBasis("SyntheticHydrogen", "network-caloric-v1", "normal")
        self.identity = "network-synthetic-calorically-perfect-hydrogen-v1"
        self.configuration = {"R_j_kg_k": 4124., "cv_j_kg_k": 10188.}
        self.gas_constant_j_kg_k = 4124.
        self.cv_j_kg_k = 10188.
        self.cp_j_kg_k = self.cv_j_kg_k+self.gas_constant_j_kg_k

    def _state(self, density, internal_energy):
        import math
        from h2physics.core import ThermoState

        temperature = internal_energy/self.cv_j_kg_k
        pressure = density*self.gas_constant_j_kg_k*temperature
        entropy = self.cv_j_kg_k*math.log(temperature/300.)-self.gas_constant_j_kg_k*math.log(density)
        sound = math.sqrt((self.cp_j_kg_k/self.cv_j_kg_k)*self.gas_constant_j_kg_k*temperature)
        return ThermoState(
            self.basis, pressure, temperature, density, internal_energy+pressure/density,
            internal_energy, entropy, "gas", self.cp_j_kg_k, self.cv_j_kg_k,
            speed_of_sound_m_s=sound,
        )

    def state_pt(self, pressure_pa, temperature_k):
        density = pressure_pa/(self.gas_constant_j_kg_k*temperature_k)
        return self._state(density, self.cv_j_kg_k*temperature_k)

    def state_rho_u(self, density_kg_m3, internal_energy_j_kg):
        return self._state(density_kg_m3, internal_energy_j_kg)


def _network(eos):
    from h2physics.caloric_pipe_network_waves import (
        CaloricPipeNetworkEdge, CaloricPipeNetworkNode, CaloricPipeNetworkWaveModel,
    )
    from h2physics.core import Origin

    common = dict(origin=Origin.SYNTHETIC)
    nodes = (
        CaloricPipeNetworkNode("left", (-2., 0., 0.), "closed", "synthetic", "left-wall", **common),
        CaloricPipeNetworkNode("junction", (0., 0., 0.), "junction", "synthetic", "mixer-node",
                               pressure_bounds_pa=(4.e6, 12.e6), temperature_bounds_k=(250., 350.), **common),
        CaloricPipeNetworkNode("right", (2., 0., 0.), "closed", "synthetic", "right-wall", **common),
        CaloricPipeNetworkNode("branch", (0., 2., 0.), "closed", "synthetic", "branch-wall", **common),
    )
    edges = (
        CaloricPipeNetworkEdge("inlet-leg", "left", "junction", 2., .05, 12,
                               "synthetic-geometry", "inlet-geometry", **common),
        CaloricPipeNetworkEdge("outlet-leg", "junction", "right", 2., .05, 12,
                               "synthetic-geometry", "outlet-geometry", **common),
        CaloricPipeNetworkEdge("branch-leg", "junction", "branch", 2., .05, 12,
                               "synthetic-geometry", "branch-geometry", **common),
    )
    return CaloricPipeNetworkWaveModel(
        nodes, edges, eos, "synthetic-network-clock-v1", maximum_cfl=.25,
        junction_mass_tolerance_kg_s=1.e-7,
        junction_energy_tolerance_w=1.e-2,
    )


def _uniform(model, pressure=8.e6, temperature=300.):
    import numpy as np

    p = {edge.identifier: np.full(edge.cell_count, pressure) for edge in model.edges}
    t = {edge.identifier: np.full(edge.cell_count, temperature) for edge in model.edges}
    u = {edge.identifier: np.zeros(edge.cell_count) for edge in model.edges}
    return p, t, u


def validate_closed_equilibrium(*, work_directory, **parameters):
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    model = _network(_SyntheticHydrogenEOS())
    p, t, u = _uniform(model)
    trace = model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                           initial_velocity_m_s=u, time_samples_s=(0., .001, .002))
    pressure_error = max(float(np.max(np.abs(values-8.e6))) for values in trace.pressure_pa.values())
    temperature_error = max(float(np.max(np.abs(values-300.))) for values in trace.temperature_k.values())
    mass_residual = float(np.max(np.abs(trace.mass_balance_residual_kg)))
    energy_residual = float(np.max(np.abs(trace.energy_balance_residual_j)))
    if pressure_error > 1.e-6 or temperature_error > 1.e-10:
        raise AssertionError("Uniform network state drifted without a forcing")
    if mass_residual > 1.e-10 or energy_residual > 1.e-5:
        raise AssertionError("Closed caloric network did not conserve mass and total energy")
    if (set(trace.junction_pressure_pa) != {"junction"}
            or trace.node_evidence_ids["junction"] != "mixer-node"
            or trace.clock_id != model.clock_id
            or trace.edge_lengths_m != {edge.identifier: edge.length_m for edge in model.edges}):
        raise AssertionError("Trace lost its junction, geometry, or clock provenance")
    return ValidationOutcome(True, {
        "junction_pressure_pa": trace.junction_pressure_pa["junction"].tolist(),
        "junction_temperature_k": trace.junction_temperature_k["junction"].tolist(),
        "maximum_mass_residual_kg": mass_residual,
        "maximum_energy_residual_j": energy_residual,
        "maximum_cfl": trace.maximum_cfl,
    }, ("Synthetic closed-network contract only; no measured-network validation.",))


def validate_mixing_balance(*, work_directory, **parameters):
    from dataclasses import replace

    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    model = _network(_SyntheticHydrogenEOS())
    p, t, u = _uniform(model)
    t["inlet-leg"][:] = 290.
    t["outlet-leg"][:] = 300.
    t["branch-leg"][:] = 310.
    trace = model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                           initial_velocity_m_s=u, time_samples_s=(0., .0005, .001))
    mres = max(float(np.max(np.abs(values)))
               for values in trace.junction_mass_residual_kg_s.values())
    eres = max(float(np.max(np.abs(values)))
               for values in trace.junction_energy_residual_w.values())
    entropy_generation = min(float(np.min(values))
                             for values in trace.junction_entropy_generation_w_k.values())
    if mres > model.junction_mass_tolerance_kg_s or eres > model.junction_energy_tolerance_w:
        raise AssertionError("Junction mass/total-energy closure exceeded its explicit tolerances")
    if entropy_generation < 0.:
        raise AssertionError("Perfect-mixing junction reports negative entropy production")
    if (np.max(np.abs(trace.mass_balance_residual_kg)) > 1.e-8
            or np.max(np.abs(trace.energy_balance_residual_j)) > 1.e-2):
        raise AssertionError("Network global conservation residual exceeded its declared budget")
    if all(np.allclose(values[0], values[-1], rtol=0., atol=1.e-9)
           for values in trace.temperature_k.values()):
        raise AssertionError("Unequal-temperature branch input produced no resolved state change")
    try:
        replace(trace, maximum_cfl=0.)
    except ValueError as error:
        if "issued only" not in str(error):
            raise AssertionError("Trace clone was rejected for an unrelated reason") from error
    else:
        raise AssertionError("A replaced network trace retained completed-run issuance")
    return ValidationOutcome(True, {
        "junction_pressure_pa": trace.junction_pressure_pa["junction"].tolist(),
        "junction_temperature_k": trace.junction_temperature_k["junction"].tolist(),
        "max_junction_mass_residual_kg_s": mres,
        "max_junction_energy_residual_w": eres,
        "minimum_junction_entropy_generation_w_k": entropy_generation,
        "max_global_mass_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
        "max_global_energy_residual_j": float(np.max(np.abs(trace.energy_balance_residual_j))),
    }, ("Synthetic perfect-mixing Euler junction; no tee-loss or measured data inference.",))


def validate_reservoir_contract(*, work_directory, **parameters):
    from dataclasses import replace

    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.caloric_pipe_network_waves import (
        CaloricPipeNetworkEdge, CaloricPipeNetworkNode, CaloricPipeNetworkWaveModel,
    )
    from h2physics.core import Origin
    from h2physics.caloric_pipe_waves import CaloricPipeReservoirBoundary

    del work_directory, parameters
    eos = _SyntheticHydrogenEOS()
    model = CaloricPipeNetworkWaveModel(
        (
            CaloricPipeNetworkNode("reservoir", (0., 0., 0.), "reservoir", "source-owner",
                                   "source-state-evidence", Origin.SYNTHETIC),
            CaloricPipeNetworkNode("wall", (2., 0., 0.), "closed", "synthetic", "wall-evidence",
                                   Origin.SYNTHETIC),
        ),
        (CaloricPipeNetworkEdge("single-leg", "reservoir", "wall", 2., .05, 16,
                                "synthetic", "pipe-geometry", Origin.SYNTHETIC),),
        eos, "synthetic-network-clock-v1", maximum_cfl=.25,
    )
    boundary = CaloricPipeReservoirBoundary(
        "source-node", "source-owner", "source-state-evidence", model.clock_id,
        eos.state_pt(6.e6, 295.), 0.,
    )
    p, t, u = _uniform(model)
    trace = model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                           initial_velocity_m_s=u, time_samples_s=(0., .0005, .001),
                           reservoir_boundaries={"reservoir": boundary})
    if (np.max(np.abs(trace.mass_balance_residual_kg)) > 1.e-8
            or np.max(np.abs(trace.energy_balance_residual_j)) > 1.e-2):
        raise AssertionError("Reservoir terminal balances do not match the applied face flux")
    bad = replace(boundary, clock_id="different-clock")
    try:
        model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                       initial_velocity_m_s=u, time_samples_s=(0., .001),
                       reservoir_boundaries={"reservoir": bad})
    except ValueError as error:
        if "clock" not in str(error).lower():
            raise AssertionError("Wrong clock rejected for an unrelated reason") from error
    else:
        raise AssertionError("Mismatched boundary clock was accepted")
    return ValidationOutcome(True, {
        "net_terminal_mass_in_kg": float(trace.cumulative_terminal_mass_in_kg[-1]),
        "net_terminal_energy_in_j": float(trace.cumulative_terminal_energy_in_j[-1]),
        "max_global_mass_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
        "max_global_energy_residual_j": float(np.max(np.abs(trace.energy_balance_residual_j))),
    }, ("Fixed reservoir endpoint only; no source-stock depletion is modeled.",))


def validate_source_ledgers(*, work_directory, **parameters):
    import numpy as np

    from h2physics.caloric_pipe_network_waves import (
        CaloricPipeNetworkEdge, CaloricPipeNetworkNode, CaloricPipeNetworkWaveModel,
    )
    from h2physics.caloric_pipe_waves import CaloricPipeWallHeatBoundary, UniformDarcyFriction
    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.core import Origin

    del work_directory, parameters
    eos = _SyntheticHydrogenEOS()
    model = CaloricPipeNetworkWaveModel(
        (CaloricPipeNetworkNode("left", (0., 0., 0.), "closed", "synthetic", "left-wall", Origin.SYNTHETIC),
         CaloricPipeNetworkNode("right", (2., 0., 0.), "closed", "synthetic", "right-wall", Origin.SYNTHETIC)),
        (CaloricPipeNetworkEdge("single-leg", "left", "right", 2., .05, 16,
                                "synthetic-geometry", "single-leg-evidence", Origin.SYNTHETIC),),
        eos, "synthetic-source-clock-v1", maximum_cfl=.2,
    )
    p = {"single-leg": np.full(16, 8.e6)}
    t = {"single-leg": np.full(16, 300.)}
    u = {"single-leg": np.full(16, 20.)}
    times = (0., 0.0002, 0.0004)
    baseline = model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                              initial_velocity_m_s=u, time_samples_s=times)
    friction = UniformDarcyFriction(.025, "synthetic-darcy-v1", "synthetic-owner",
                                    "synthetic-friction-evidence", model.clock_id)
    wall = CaloricPipeWallHeatBoundary("synthetic-wall-v1", "synthetic-owner",
                                       "synthetic-wall-evidence", model.clock_id, 320., 25.)
    sourced = model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                             initial_velocity_m_s=u, time_samples_s=times,
                             darcy_friction_laws={"single-leg": friction},
                             wall_heat_boundaries={"single-leg": wall})
    heat_in = float(sourced.cumulative_wall_heat_in_j[-1])
    baseline_residual = float(np.max(np.abs(baseline.energy_balance_residual_j)))
    source_residual = float(np.max(np.abs(sourced.energy_balance_residual_j)))
    if heat_in <= 0.:
        raise AssertionError("Hot-wall boundary did not add positive energy to the gas")
    if not np.all(sourced.velocity_m_s["single-leg"][-1] < baseline.velocity_m_s["single-leg"][-1]):
        raise AssertionError("Darcy friction did not reduce the positive velocity field")
    if baseline.cumulative_wall_heat_in_j[-1] != 0. or baseline_residual > 1.e-5:
        raise AssertionError("Source-free network regression did not preserve its original energy ledger")
    if source_residual > 1.e-4:
        raise AssertionError("Wall heat was not included in the network energy residual")
    if (sourced.friction_evidence_ids != {"single-leg": "synthetic-friction-evidence"}
            or sourced.wall_heat_evidence_ids != {"single-leg": "synthetic-wall-evidence"}):
        raise AssertionError("Trace omitted the source-law evidence identities")
    return ValidationOutcome(True, {
        "cumulative_wall_heat_in_j": heat_in,
        "max_source_run_energy_residual_j": source_residual,
        "max_source_free_energy_residual_j": baseline_residual,
        "final_mean_velocity_source_free_m_s": float(np.mean(baseline.velocity_m_s["single-leg"][-1])),
        "final_mean_velocity_with_friction_m_s": float(np.mean(sourced.velocity_m_s["single-leg"][-1])),
    }, ("Synthetic network source-ledger contract; friction and wall laws are authored, not field calibrated.",))


def _finite_reservoir_fixture(eos, *, pressure_bounds=(2.e6, 15.e6), terminal_at_end=False):
    import numpy as np

    from h2physics.caloric_pipe_network_waves import (
        CaloricPipeNetworkEdge, CaloricPipeNetworkNode, CaloricPipeNetworkWaveModel,
    )
    from h2physics.core import Origin
    from h2physics.finite_caloric_pipe_reservoir import FiniteCaloricPipeReservoir

    clock = "synthetic-finite-caloric-reservoir-clock-v1"
    tank_x, wall_x = (2., 0.) if terminal_at_end else (0., 2.)
    start_node, end_node = (("wall", "tank-node") if terminal_at_end
                            else ("tank-node", "wall"))
    model = CaloricPipeNetworkWaveModel(
        (CaloricPipeNetworkNode("tank-node", (tank_x, 0., 0.), "finite_reservoir",
                                "tank-owner", "tank-state-evidence", Origin.SYNTHETIC),
         CaloricPipeNetworkNode("wall", (wall_x, 0., 0.), "closed", "synthetic", "wall-evidence",
                                Origin.SYNTHETIC)),
        (CaloricPipeNetworkEdge("tank-leg", start_node, end_node, 2., .05, 16,
                                "synthetic-geometry", "tank-leg-geometry", Origin.SYNTHETIC),),
        eos, clock, maximum_cfl=.2,
    )
    tank_state = eos.state_pt(10.e6, 300.)
    initial_mass = tank_state.density_kg_m3*.1
    inventory = FiniteCaloricPipeReservoir(
        identifier="synthetic-tank-v1", node_id="tank-node",
        state_owner_id="tank-owner", state_evidence_id="tank-state-evidence",
        clock_id=clock, eos_identity=eos.identity, property_basis=eos.basis,
        volume_m3=.1, mass_kg=initial_mass,
        internal_energy_j=initial_mass*tank_state.internal_energy_j_kg,
        minimum_mass_kg=.1*initial_mass, maximum_mass_kg=2.*initial_mass,
        pressure_bounds_pa=pressure_bounds, temperature_bounds_k=(250., 350.),
        origin=Origin.SYNTHETIC,
    )
    p = {"tank-leg": np.full(16, 4.e6)}
    t = {"tank-leg": np.full(16, 300.)}
    u = {"tank-leg": np.zeros(16)}
    return model, inventory, p, t, u


def validate_finite_reservoir_exchange(*, work_directory, **parameters):
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    eos = _SyntheticHydrogenEOS()
    results = {}
    for terminal_at_end in (False, True):
        model, inventory, p, t, u = _finite_reservoir_fixture(
            eos, terminal_at_end=terminal_at_end,
        )
        trace = model.simulate(
            initial_pressure_pa=p, initial_temperature_k=t, initial_velocity_m_s=u,
            time_samples_s=(0., .0002, .0004), finite_reservoirs={"tank-node": inventory},
        )
        trace.require_current()
        mass_history = trace.finite_reservoir_mass_kg["tank-node"]
        energy_history = trace.finite_reservoir_internal_energy_j["tank-node"]
        pressure_history = trace.finite_reservoir_pressure_pa["tank-node"]
        mass_error = float(np.max(np.abs(trace.mass_balance_residual_kg)))
        energy_error = float(np.max(np.abs(trace.energy_balance_residual_j)))
        if not mass_history[-1] < mass_history[0] or not energy_history[-1] < energy_history[0]:
            raise AssertionError("Higher-pressure finite reservoir did not discharge mass and internal energy")
        if not pressure_history[-1] < pressure_history[0]:
            raise AssertionError("Finite-reservoir pressure did not follow the declining inventory")
        if mass_error > 1.e-8 or energy_error > 1.e-2:
            raise AssertionError("Combined pipe plus caloric reservoir balance did not close")
        if (trace.finite_reservoir_records["tank-node"] is not inventory
                or trace.finite_reservoir_temperature_k["tank-node"].shape != trace.time_s.shape):
            raise AssertionError("Finite reservoir trace omitted inventory identity or state histories")
        direction = "end" if terminal_at_end else "start"
        results[direction] = {
            "initial_mass_kg": float(mass_history[0]),
            "final_mass_kg": float(mass_history[-1]),
            "initial_internal_energy_j": float(energy_history[0]),
            "final_internal_energy_j": float(energy_history[-1]),
            "initial_pressure_pa": float(pressure_history[0]),
            "final_pressure_pa": float(pressure_history[-1]),
            "max_combined_mass_residual_kg": mass_error,
            "max_combined_energy_residual_j": energy_error,
        }
    return ValidationOutcome(True, {
        "orientation_results": results,
    }, ("Synthetic rigid-vessel endpoint contract only; no tank, valve, or pipeline qualification.",))


def validate_finite_reservoir_rejections(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    eos = _SyntheticHydrogenEOS()
    model, inventory, p, t, u = _finite_reservoir_fixture(
        eos, pressure_bounds=(9.999999e6, 10.000001e6),
    )
    checks = []
    try:
        inventory.advance(
            current_mass_kg=inventory.mass_kg,
            current_internal_energy_j=inventory.internal_energy_j,
            outward_mass_flow_kg_s=.49*inventory.mass_kg,
            outward_energy_flow_w=0., duration_s=2., eos=eos,
        )
    except ValueError as error:
        if "outside its bounds" not in str(error):
            raise AssertionError("Depletion was rejected for an unrelated reason") from error
        checks.append("mass_floor")
    else:
        raise AssertionError("Finite-reservoir mass depletion was silently accepted")
    try:
        model.simulate(
            initial_pressure_pa=p, initial_temperature_k=t, initial_velocity_m_s=u,
            time_samples_s=(0., .0004), finite_reservoirs={"tank-node": inventory},
        )
    except ValueError as error:
        if "pressure left" not in str(error):
            raise AssertionError("Pressure-domain excursion was rejected for an unrelated reason") from error
        checks.append("pressure_domain")
    else:
        raise AssertionError("Finite-reservoir pressure leaving its declared domain was accepted")
    wrong_evidence = replace(inventory, state_evidence_id="wrong-evidence")
    try:
        model.simulate(
            initial_pressure_pa=p, initial_temperature_k=t, initial_velocity_m_s=u,
            time_samples_s=(0., .0002), finite_reservoirs={"tank-node": wrong_evidence},
        )
    except ValueError as error:
        if "must match exactly" not in str(error):
            raise AssertionError("Mismatched inventory evidence was rejected for an unrelated reason") from error
        checks.append("evidence_identity")
    else:
        raise AssertionError("Mismatched finite-reservoir evidence was accepted")
    return ValidationOutcome(True, {"rejected_contracts": checks},
                             ("Synthetic state/domain rejection contract only.",))
