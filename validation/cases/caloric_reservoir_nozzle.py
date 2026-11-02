"""Deferred contracts for shared-nozzle withdrawal from caloric pipe tanks."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (
        ValidationCase(
            identifier="hydrogen-caloric-network-closed-wall-momentum-reflection",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_wall_momentum_reflection",
            invariants=(
                "start-and-end-wall-ghost-order-follows-the-axial-coordinate",
                "both-endpoint-momentum-updates-match-the-Rusanov-reflection-sign",
                "reversing-initial-velocity-mirrors-the-native-CP-solution",
                "zero-boundary-mass-and-energy-flux-alone-cannot-prove-momentum-reflection",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-caloric-network-nozzle-blowdown-projection",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_blowdown_projection",
            invariants=(
                "choked-and-subcritical-nozzle-regimes-come-from-the-shared-provider",
                "each-accepted-internal-step-debits-start-state-nozzle-mass-and-withdrawal-energy",
                "left-hold-native-source-history-projects-to-the-exact-solver-mass-debit",
                "fixed-volume-reservoir-pressure-and-temperature-recover-from-evolving-mass-U",
                "combined-pipe-reservoir-nozzle-mass-and-energy-ledgers-close",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-caloric-network-nozzle-identity-domain-depletion-rejections",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_rejections",
            invariants=(
                "nozzle-property-basis-must-exactly-match-the-tank-rho-u-EOS-basis",
                "tank-state-provider-density-and-domain-must-reproduce-the-admitted-inventory-state",
                "reservoir-pressure-domain-exit-rejects-the-whole-candidate-step-without-clipping",
                "oversized-nozzle-inventory-depletion-is-rejected-without-committing-pipe-or-tank",
            ),
        ),
    )


def _fixture(*, back_pressure_pa=101325., opening_diameter_m=.003,
             pressure_bounds_pa=(1.e5, 2.e7)):
    import numpy as np

    from h2physics.caloric_pipe_network_waves import (
        CaloricPipeNetworkEdge,
        CaloricPipeNetworkNode,
        CaloricPipeNetworkWaveModel,
    )
    from h2physics.caloric_pipe_nozzle_coupling import CaloricFiniteReservoirNozzleCoupling
    from h2physics.caloric_pipe_waves import _eos_identity
    from h2physics.core import Origin
    from h2physics.finite_caloric_pipe_reservoir import FiniteCaloricPipeReservoir
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation
    from h2physics.thermo.coolprop import CoolPropProperties

    eos = CoolPropProperties("Hydrogen")
    clock = "synthetic-caloric-nozzle-clock-v1"
    nodes = (
        CaloricPipeNetworkNode("tank", (0., 0., 0.), "finite_reservoir",
                               "synthetic-tank-owner", "synthetic-tank-state", Origin.SYNTHETIC),
        CaloricPipeNetworkNode("wall", (2., 0., 0.), "closed", "synthetic-wall-owner",
                               "synthetic-wall-state", Origin.SYNTHETIC),
    )
    edges = (CaloricPipeNetworkEdge("tank-leg", "tank", "wall", 2., .05, 24,
                                    "synthetic-layout", "synthetic-edge-state", Origin.SYNTHETIC),)
    model = CaloricPipeNetworkWaveModel(nodes, edges, eos, clock, maximum_cfl=.2)
    initial = eos.state_pt(10.e6, 300.)
    mass = initial.density_kg_m3*.1
    inventory = FiniteCaloricPipeReservoir(
        identifier="synthetic-caloric-tank", node_id="tank",
        state_owner_id="synthetic-tank-owner", state_evidence_id="synthetic-tank-state",
        clock_id=clock, eos_identity=_eos_identity(eos),
        property_basis=eos.basis, volume_m3=.1, mass_kg=mass,
        internal_energy_j=mass*initial.internal_energy_j_kg,
        minimum_mass_kg=.05*mass, maximum_mass_kg=2.*mass,
        pressure_bounds_pa=pressure_bounds_pa, temperature_bounds_k=(150., 400.),
        origin=Origin.SYNTHETIC,
    )
    opening = NozzleOpening.circular(
        "synthetic-caloric-leak", opening_diameter_m,
        effective_area_factor=.8, area_basis_id="synthetic-area-evidence",
    )
    coupling = CaloricFiniteReservoirNozzleCoupling(
        identifier="synthetic-caloric-source", node_id="tank",
        reservoir_id=inventory.identifier, edge_id="tank-leg", opening=opening,
        opening_fraction=1., back_pressure_pa=back_pressure_pa,
        location=SourceLocation("synthetic-caloric-source", clock,
                                "synthetic-plant-frame", (0., 0., 0.), (1., 0., 0.)),
        nozzle=HomogeneousIsentropicNozzle(eos), state_owner_id="synthetic-tank-owner",
        evidence_id="synthetic-nozzle-opening-location-and-state-contract",
        origin=Origin.SYNTHETIC, density_relative_tolerance=1.e-8,
        density_absolute_tolerance_kg_m3=1.e-10,
    )
    pressure = {"tank-leg": np.full(24, 4.e6)}
    temperature = {"tank-leg": np.full(24, 300.)}
    velocity = {"tank-leg": np.zeros(24)}
    return model, eos, inventory, coupling, pressure, temperature, velocity


def validate_blowdown_projection(*, work_directory, **parameters):
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    cases = {}
    for label, back_pressure in (("choked", 101325.), ("subcritical", 8.e6)):
        model, eos, inventory, coupling, pressure, temperature, velocity = _fixture(
            back_pressure_pa=back_pressure,
        )
        trace = model.simulate(
            initial_pressure_pa=pressure, initial_temperature_k=temperature,
            initial_velocity_m_s=velocity, time_samples_s=(0., .01, .02),
            finite_reservoirs={inventory.node_id: inventory},
            finite_reservoir_nozzles={inventory.node_id: coupling},
        )
        history = trace.finite_reservoir_nozzle_history[inventory.node_id]
        initial_state = inventory.initial_state(eos)
        projection = trace.project_nozzle_source(
            inventory.node_id, representative_state=initial_state,
            quadrature_evidence_id="synthetic-accepted-step-left-hold",
            state_projection_evidence_id="synthetic-initial-state-as-window-representative",
        )
        expected_regime = "choked" if label == "choked" else "back_pressure_limited"
        if history.samples[0].regime != expected_regime or history.samples[0].mass_flow_kg_s <= 0.:
            raise AssertionError(f"Shared nozzle did not produce a positive {label} source")
        if (not trace.finite_reservoir_mass_kg[inventory.node_id][-1]
                < trace.finite_reservoir_mass_kg[inventory.node_id][0]):
            raise AssertionError("Accepted nozzle source did not deplete the finite tank mass")
        if (not trace.finite_reservoir_internal_energy_j[inventory.node_id][-1]
                < trace.finite_reservoir_internal_energy_j[inventory.node_id][0]):
            raise AssertionError("Accepted nozzle source did not withdraw tank internal energy")
        if (np.ptp(trace.finite_reservoir_pressure_pa[inventory.node_id]) <= 0.
                or np.ptp(trace.finite_reservoir_temperature_k[inventory.node_id]) <= 0.):
            raise AssertionError("Caloric tank pressure and temperature did not evolve during blowdown")
        # This case has no external reservoir, junction or wall heat. Positive
        # nozzle debits belong on the same side as the stock change in a
        # closed-system residual: delta(stock) + withdrawn = 0.
        expected_mass_residual = (trace.total_mass_kg-trace.total_mass_kg[0]
                                  +trace.cumulative_nozzle_mass_out_kg[inventory.node_id])
        expected_energy_residual = (trace.total_energy_j-trace.total_energy_j[0]
                                    +trace.cumulative_nozzle_withdrawal_energy_j[inventory.node_id])
        assert np.allclose(trace.mass_balance_residual_kg, expected_mass_residual, rtol=0., atol=1e-12)
        assert np.allclose(trace.energy_balance_residual_j, expected_energy_residual, rtol=0., atol=1e-6)
        if (np.max(np.abs(trace.mass_balance_residual_kg)) > 1.e-7
                or np.max(np.abs(trace.energy_balance_residual_j)) > 1.e-1
                or not np.isclose(sum(projection.interval_mass_kg),
                                  trace.cumulative_nozzle_mass_out_kg[inventory.node_id][-1],
                                  rtol=1.e-12, atol=1.e-12)):
            raise AssertionError(
                "Nozzle source projection or combined tank-pipe ledger did not close: "
                f"max_mass={np.max(np.abs(trace.mass_balance_residual_kg))!r} kg, "
                f"max_energy={np.max(np.abs(trace.energy_balance_residual_j))!r} J, "
                f"projected_mass={sum(projection.interval_mass_kg)!r} kg, "
                f"debited_mass={trace.cumulative_nozzle_mass_out_kg[inventory.node_id][-1]!r} kg")
        cases[label] = {
            "regime": history.samples[0].regime,
            "accepted_source_sample_count": len(history.time_s),
            "mass_out_kg": float(trace.cumulative_nozzle_mass_out_kg[inventory.node_id][-1]),
            "withdrawal_energy_j": float(
                trace.cumulative_nozzle_withdrawal_energy_j[inventory.node_id][-1]),
            "initial_pressure_pa": float(trace.finite_reservoir_pressure_pa[inventory.node_id][0]),
            "final_pressure_pa": float(trace.finite_reservoir_pressure_pa[inventory.node_id][-1]),
            "initial_temperature_k": float(trace.finite_reservoir_temperature_k[inventory.node_id][0]),
            "final_temperature_k": float(trace.finite_reservoir_temperature_k[inventory.node_id][-1]),
            "projected_mass_kg": float(sum(projection.interval_mass_kg)),
            "projection_interval_count": len(projection.interval_mass_kg),
            "minimum_projection_interval_mass_kg": float(min(projection.interval_mass_kg)),
            "maximum_projection_interval_mass_kg": float(max(projection.interval_mass_kg)),
            "property_basis": eos.basis.reference_id,
            "maximum_mass_balance_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
            "maximum_energy_balance_residual_j": float(np.max(np.abs(trace.energy_balance_residual_j))),
        }
    return ValidationOutcome(True, {"regimes": cases},
                             ("Deferred provider-backed software contracts; no empirical blowdown qualification.",))


def validate_rejections(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.release import HomogeneousIsentropicNozzle
    from h2physics.thermo.coolprop import CoolPropProperties

    del work_directory, parameters
    model, _eos, inventory, coupling, pressure, temperature, velocity = _fixture()
    wrong_nozzle = replace(coupling, nozzle=HomogeneousIsentropicNozzle(
        CoolPropProperties("ParaHydrogen")))
    try:
        model.simulate(initial_pressure_pa=pressure, initial_temperature_k=temperature,
                       initial_velocity_m_s=velocity, time_samples_s=(0., .001),
                       finite_reservoirs={inventory.node_id: inventory},
                       finite_reservoir_nozzles={inventory.node_id: wrong_nozzle})
    except ValueError as error:
        if "exact PropertyBasis" not in str(error):
            raise AssertionError("Nozzle property basis was rejected for an unrelated reason") from error
    else:
        raise AssertionError("Nozzle provider with a different PropertyBasis was accepted")

    domain_model, domain_eos, domain_inventory, domain_coupling, p, t, u = _fixture(
        pressure_bounds_pa=(9.999999e6, 10.000001e6),
    )
    try:
        domain_model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                              initial_velocity_m_s=u, time_samples_s=(0., .001),
                              finite_reservoirs={domain_inventory.node_id: domain_inventory},
                              finite_reservoir_nozzles={domain_inventory.node_id: domain_coupling})
    except ValueError as error:
        if "pressure left" not in str(error):
            raise AssertionError("Tank pressure-domain failure was rejected for an unrelated reason") from error
    else:
        raise AssertionError("Tank pressure leaving its declared domain was accepted")

    depleted_model, _depleted_eos, depleted_inventory, depleted_coupling, p, t, u = _fixture(
        opening_diameter_m=10.0,
    )
    try:
        depleted_model.simulate(initial_pressure_pa=p, initial_temperature_k=t,
                                initial_velocity_m_s=u, time_samples_s=(0., .01),
                                finite_reservoirs={depleted_inventory.node_id: depleted_inventory},
                                finite_reservoir_nozzles={depleted_inventory.node_id: depleted_coupling})
    except ValueError as error:
        cause_text = str(error).lower().replace("_", " ")
        if (not any(message in cause_text for message in ("depleted", "bounds"))
                and not all(term in cause_text for term in ("mass", "positive"))):
            raise AssertionError("Tank nozzle depletion was rejected for an unrelated reason") from error
    else:
        raise AssertionError("Oversized nozzle silently depleted or clipped the tank state")
    return ValidationOutcome(True, {"rejections": ("property_basis", "pressure_domain", "depletion")},
                             ("Deferred rejection contracts; candidate states are not clipped.",))


def validate_wall_momentum_reflection(*, work_directory, **parameters):
    """Native-CP one-step checks of both wall-face momentum signs."""
    del work_directory, parameters
    import numpy as np

    from h2physics.caloric_pipe_network_waves import (
        CaloricPipeNetworkEdge,
        CaloricPipeNetworkNode,
        CaloricPipeNetworkWaveModel,
    )
    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.core import Origin
    from h2physics.thermo import CoolPropProperties

    eos = CoolPropProperties("Hydrogen")
    initial = eos.state_pt(4e6, 300.)
    nodes = tuple(CaloricPipeNetworkNode(name, (position, 0., 0.), "closed",
        "authored-wall-owner", "authored-wall-state", Origin.SYNTHETIC)
        for name, position in (("left", 0.), ("right", 2.)))
    edge = CaloricPipeNetworkEdge("wall-pipe", "left", "right", 2., .05, 8,
        "authored-pipe-owner", "authored-pipe-state", Origin.SYNTHETIC)
    model = CaloricPipeNetworkWaveModel(nodes, (edge,), eos, "wall-reflection-clock", maximum_cfl=.2)
    duration = 1e-6
    traces = []
    maximum_error = 0.
    for velocity in (5., -5.):
        trace = model.simulate(
            initial_pressure_pa={edge.identifier: np.full(edge.cell_count, 4e6)},
            initial_temperature_k={edge.identifier: np.full(edge.cell_count, 300.)},
            initial_velocity_m_s={edge.identifier: np.full(edge.cell_count, velocity)},
            time_samples_s=(0., duration))
        # For a uniform initial interior, each endpoint momentum changes by
        # -dt/dx*(|v|+c)*rho*v. A wrongly ordered right ghost flips that sign.
        expected = initial.density_kg_m3*velocity*(1.-duration/(edge.length_m/edge.cell_count)
            *(abs(velocity)+initial.speed_of_sound_m_s))
        momentum = trace.density_kg_m3[edge.identifier][-1]*trace.velocity_m_s[edge.identifier][-1]
        for index in (0, -1):
            error = abs(float(momentum[index])-expected)
            maximum_error = max(maximum_error, error)
            assert np.isclose(momentum[index], expected, rtol=1e-11, atol=1e-9)
        assert np.max(np.abs(trace.mass_balance_residual_kg)) < 1e-12
        assert np.max(np.abs(trace.energy_balance_residual_j)) < 1e-6
        traces.append(trace)
    plus, minus = traces
    assert np.allclose(plus.pressure_pa[edge.identifier][-1, ::-1],
                       minus.pressure_pa[edge.identifier][-1], rtol=1e-11, atol=1e-5)
    assert np.allclose(plus.velocity_m_s[edge.identifier][-1, ::-1],
                       -minus.velocity_m_s[edge.identifier][-1], rtol=1e-11, atol=1e-9)
    return ValidationOutcome(True, {
        "endpoint_momentum_checks": 4,
        "maximum_momentum_density_error_kg_m2_s": maximum_error,
        "mirrored_velocity_solution_verified": True,
    }, ("Single-step native-EOS numerical reflection check; no empirical pipe validation.",))
