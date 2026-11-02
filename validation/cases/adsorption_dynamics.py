"""Deferred numerical contract checks for the lumped LDF adsorption model."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Synthetic thermodynamic/isotherm fixtures are software-contract inputs only.",
    "No measured material kinetics, calorimetry or vessel-wall validation is implied.",
    "Single-species, rigid, lumped-temperature model; no axial breakthrough physics.",
)


def cases():
    return (
        ValidationCase(
            identifier="adsorption-dynamics-closed-lumped-energy",
            profile="finite-adsorption-vessel",
            entrypoint=__name__ + ":validate_closed",
            invariants=("free plus adsorbed inventory is conserved without boundary flow",
                        "total stored energy closes with LDF redistribution",
                        "EOS pressure and thermal response stay inside declared domains",
                        "repeated bound-provider method lookup retains stable owner/function identity while configuration edits are rejected"),
        ),
        ValidationCase(
            identifier="adsorption-dynamics-piecewise-feed-energy-ledger",
            profile="finite-adsorption-vessel",
            entrypoint=__name__ + ":validate_feed",
            invariants=("piecewise feed ends at an exact integration edge",
                        "feed amount appears in the free plus adsorbed inventory ledger",
                        "feed enthalpy and external heat close stored energy"),
        ),
        ValidationCase(
            identifier="adsorption-dynamics-finite-h2-source-handoff",
            profile="finite-adsorption-vessel",
            entrypoint=__name__ + ":validate_finite_source_handoff",
            invariants=(
                "completed single-species H2 outlet moles map exactly to accepted finite source mass bins",
                "source clock alignment and representative-state projection require separate caller evidence",
                "integrated representative-state enthalpy must close the native outlet ledger within a declared budget",
                "wrong property basis and stale trace owner are rejected",
                "the source handoff adds no breakthrough, valve, pressure-control or dispersion model",
            ),
        ),
        ValidationCase(
            identifier="competitive-extended-langmuir-multicomponent",
            profile="finite-adsorption-vessel",
            entrypoint=__name__ + ":validate_extended_langmuir",
            invariants=(
                "each site's total competitive loading remains below its absolute capacity",
                "species pressure derivatives include the cross-competition terms",
                "optional temperature derivatives retain the declared species-by-site shape",
                "basis, species ordering and pressure/temperature domains are enforced",
                "returned equilibrium and Jacobian arrays are immutable",
            ),
        ),
    )


def validate_extended_langmuir(*, work_directory, **parameters):
    from h2physics.adsorption import (
        AdsorptionBasis, AdsorptionDomain, ExtendedLangmuirIsotherm,
    )

    del work_directory, parameters
    basis = AdsorptionBasis(
        "synthetic-competitive-site", ("H2", "CO2"), "mol-per-kg-absolute",
        "extended-langmuir", "synthetic-affinity-set", ("synthetic-fixture",), "absolute",
    )
    isotherm = ExtendedLangmuirIsotherm(
        basis, AdsorptionDomain(250., 400., 2.0e6), (2., 4.),
        lambda temperature: np.array([[2.0e-6, 0.5e-6], [1.0e-6, 3.0e-6]])
        * (300. / temperature),
        "synthetic-competitive-isotherm-fixture",
        lambda temperature: -np.array([[2.0e-6, 0.5e-6], [1.0e-6, 3.0e-6]])
        * (300. / temperature**2),
    )
    state = isotherm.equilibrium((3.0e5, 1.0e5), 300.)
    assert state.site_loadings_mol_kg.shape == (2, 2)
    assert np.all(state.site_loadings_mol_kg.sum(axis=0) < isotherm.site_capacity_mol_kg)
    assert np.any(state.site_pressure_derivatives_mol_kg_pa < 0.)
    assert np.all(np.diagonal(state.site_pressure_derivatives_mol_kg_pa, axis1=1, axis2=2) > 0.)
    assert state.site_pressure_derivatives_mol_kg_pa[0, 0, 1] < 0.
    assert state.site_temperature_derivatives_mol_kg_k.shape == (2, 2)
    for array in (state.site_loadings_mol_kg, state.site_pressure_derivatives_mol_kg_pa,
                  state.site_temperature_derivatives_mol_kg_k):
        try:
            array.setflags(write=True)
        except ValueError:
            continue
        raise AssertionError("Returned isotherm arrays must be backed by immutable storage")
    try:
        isotherm.equilibrium((2.0e6, 1.0), 300.)
    except ValueError:
        pass
    else:
        raise AssertionError("The declared total-pressure domain must be enforced")
    return ValidationOutcome(True, {
        "species": len(basis.species),
        "sites": len(isotherm.site_capacity_mol_kg),
        "max_site_fraction": float(np.max(
            state.site_loadings_mol_kg.sum(axis=0) / isotherm.site_capacity_mol_kg
        )),
        "cross_pressure_derivative": float(state.site_pressure_derivatives_mol_kg_pa[0, 0, 1]),
    }, ("Synthetic equilibrium contract only; no material-specific fit or adsorption validation",))


def _inputs(callback, *, end=20., boundaries=(0., 20.)):
    from examples.adsorption_dynamics import authored_dynamic_vessel
    from h2physics.storage.adsorption_dynamics import AdsorptionDynamicsInputs

    return AdsorptionDynamicsInputs(
        vessel=authored_dynamic_vessel(),
        initial_pressure_pa=1.0e6,
        initial_temperature_k=298.15,
        initial_site_loadings_mol_kg=(0.1, 0.05),
        ldf_rate_constant_s=(0.03, 0.01),
        adsorption_energy_j_mol=(-6500., -9000.),
        solid_wall_heat_capacity_j_k=3.0e4,
        reference_temperature_k=298.15,
        temperature_bounds_k=(200., 400.),
        pressure_bounds_pa=(1.0e4, 2.0e7),
        start_time_s=0., end_time_s=end, boundaries_s=boundaries,
        boundary_rates=callback,
        rate_evidence_id="synthetic-rate-fixture",
        energy_evidence_id="synthetic-energy-fixture",
        run_id="deferred-adsorption-dynamics-contract",
    )


def _total_moles(trace):
    mass_adsorbent = trace.inputs.vessel.geometry.adsorbent_mass_kg
    return trace.free_gas_mol + mass_adsorbent * trace.site_loadings_mol_kg.sum(axis=1)


def validate_closed(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    from h2physics.storage.adsorption_dynamics import (
        AdsorptionBoundaryRates, integrate_adsorption_dynamics,
    )

    def no_boundary(state):
        del state
        return AdsorptionBoundaryRates(0., 0., 0., 0., "synthetic-closed", "synthetic-h2-reference")

    trace = integrate_adsorption_dynamics(_inputs(no_boundary))
    assert trace.require_current() is trace
    inventory = _total_moles(trace)
    inventory_residual = float(abs(inventory[-1] - inventory[0]))
    component_residual = float(max(abs(trace.component_residual_mol)))
    energy_residual = float(max(abs(trace.energy_residual_j)))
    assert trace.status == "completed"
    assert inventory_residual < 1e-7
    assert component_residual < 1e-7
    assert energy_residual < 0.1
    assert np.allclose(trace.total_component_mol, inventory, rtol=1e-12, atol=1e-11)
    try:
        replace(trace, total_component_mol=trace.total_component_mol + 1.)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A modified total-mole trace was accepted with stale component state")
    try:
        replace(trace, component_residual_mol=trace.component_residual_mol + 1.)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A forged component residual was accepted")
    return ValidationOutcome(True, {
        "inventory_residual_mol": inventory_residual,
        "maximum_component_residual_mol": component_residual,
        "maximum_energy_residual_j": energy_residual,
        "forged_component_receipts_rejected": 2,
        "accepted_steps": trace.accepted_step_count,
    }, LIMITS)


def validate_feed(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.storage.adsorption_dynamics import (
        AdsorptionBoundaryRates, integrate_adsorption_dynamics,
    )

    def feed(state):
        rate = 0.002 if state.time_s < 10. else 0.
        return AdsorptionBoundaryRates(rate, 28000. if rate else 0., 0., 35. if rate else 0.,
                                       "synthetic-piecewise-feed", "synthetic-h2-reference")

    trace = integrate_adsorption_dynamics(_inputs(feed, boundaries=(0., 10., 20.)))
    assert trace.require_current() is trace
    added = float(_total_moles(trace)[-1] - _total_moles(trace)[0])
    ledger_gain = float(trace.cumulative_feed_mol[-1] - trace.cumulative_outlet_mol[-1])
    component_residual = float(max(abs(trace.component_residual_mol)))
    assert trace.status == "completed"
    assert abs(added - 0.02) < 1e-6
    assert abs(ledger_gain - 0.02) < 1e-8
    assert component_residual < 1e-7
    assert max(abs(trace.energy_residual_j)) < 0.1
    return ValidationOutcome(True, {
        "feed_inventory_gain_mol": added,
        "feed_outlet_ledger_gain_mol": ledger_gain,
        "maximum_component_residual_mol": component_residual,
        "maximum_energy_residual_j": float(max(abs(trace.energy_residual_j))),
        "accepted_steps": trace.accepted_step_count,
    }, LIMITS)


def validate_finite_source_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.adapters import bind_adsorption_dynamics_to_finite_source
    from h2physics.core import PropertyBasis
    from h2physics.release import SourceLocation
    from h2physics.storage.adsorption_dynamics import (
        AdsorptionBoundaryRates, integrate_adsorption_dynamics,
    )

    def outlet(state):
        del state
        return AdsorptionBoundaryRates(
            0., 0., 1.e-4, 0., "synthetic-outlet", "synthetic-h2-reference")

    trace = integrate_adsorption_dynamics(_inputs(outlet))
    location = SourceLocation(trace.inputs.run_id, "synthetic-clock",
        "synthetic-vessel-frame", (0., 0., 0.), (1., 0., 0.))
    state = trace.inputs.vessel.gas.state_pt(trace.pressure_pa[0], trace.temperature_k[0])
    handoff = bind_adsorption_dynamics_to_finite_source(
        trace, location=location, representative_state=state,
        clock_alignment_evidence_id="synthetic-clock-alignment",
        state_projection_evidence_id="synthetic-mean-state-projection",
        energy_tolerance_j=10., relative_tolerance=1.e-2,
    )
    handoff.require_current()
    expected_mass = (trace.cumulative_outlet_mol[-1]
                     * trace.inputs.vessel.gas.mean_molar_mass_kg_mol)
    assert abs(handoff.source.total_mass_kg-expected_mass) < 1e-12
    assert len(handoff.source.mass_kg) == trace.accepted_step_count
    assert handoff.source.location is location
    wrong_state = replace(state, basis=PropertyBasis(state.basis.fluid, "different-reference"))
    try:
        bind_adsorption_dynamics_to_finite_source(
            trace, location=location, representative_state=wrong_state,
            clock_alignment_evidence_id="synthetic-clock-alignment",
            state_projection_evidence_id="synthetic-wrong-state",
            energy_tolerance_j=10., relative_tolerance=1.e-2,
        )
    except ValueError:
        wrong_basis_rejected = True
    else:
        raise AssertionError("An incompatible source thermodynamic basis was accepted")
    original_status = trace.status
    object.__setattr__(trace, "status", "solver_failure")
    try:
        handoff.require_current()
    except ValueError:
        stale_trace_rejected = True
    else:
        raise AssertionError("A source handoff remained current after its owner trace changed")
    object.__setattr__(trace, "status", original_status)
    handoff.require_current()
    return ValidationOutcome(True, {
        "outlet_mass_kg": handoff.transferred_mass_kg,
        "native_outlet_enthalpy_j": handoff.native_outlet_enthalpy_j,
        "representative_state_enthalpy_residual_j": handoff.enthalpy_residual_j,
        "enthalpy_budget_j": handoff.enthalpy_budget_j,
        "wrong_basis_rejected": wrong_basis_rejected,
        "stale_trace_rejected": stale_trace_rejected,
        "accepted_intervals": len(handoff.source.mass_kg),
    }, LIMITS + (
        "Synthetic source-state projection tolerance is illustrative and not equipment validation.",
        "A finite mass source does not establish a real valve, product conditioning or downstream release plane.",
    ))
