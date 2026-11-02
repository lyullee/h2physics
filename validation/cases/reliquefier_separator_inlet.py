"""Deferred reliquefier-product to native separator inlet contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="reliquefier-product-native-separator-liquid-inlet-handoff",
        profile="finite-transfer",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "only owner-issued collected all-liquid product receipt is admitted",
            "product mass and specific enthalpy become one exact-window native liquid MassEnergyFlow",
            "source and target pure-hydrogen property bases and clock identity match",
            "caller names the receiver and supplies clock-alignment/port-assignment evidence",
            "caller identifies the transfer boundary that establishes pressure and thermal feasibility",
            "native separator remains owner of phase inventories, heat exchange, pressure response and energy closure",
            "no transfer-line pressure loss, flashing or thermal conditioning is inferred",
            "callback rejects times outside the receipt window and incomplete transfer-boundary identities",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from lh2dt.streams import MassEnergyFlow

    from h2physics.adapters.lh2dt import from_lh2dt_state
    from h2physics.adapters.lh2dt_reliquefier import SteadyReliquefierResult, _issue_result
    from h2physics.adapters.reliquefier_product import (
        CollectedProductInventory, FiniteColdReservoir, FiniteReliquefierProduct,
        ProductWindow, ReliquefierProductPorts,
    )
    from h2physics.adapters.reliquefier_separator_inlet import bind_reliquefier_product_to_separator
    from h2physics.adapters.finite_separator import run_finite_pure_fluid_separator
    from h2physics.equipment import BoundaryPower, ConnectionTransfer
    from validation.cases.finite_separator import build_problem

    tank, initial, bridge = build_problem()
    liquid = from_lh2dt_state(tank.thermo(initial).liquid, basis=bridge.basis)
    transfer = ConnectionTransfer(
        "synthetic-reliquefier", "synthetic-feed", "collected-liquid",
        "synthetic/feed", "synthetic/product", 0.1,
        liquid, liquid, BoundaryPower(heat_w=-1.0), None, None,
    )

    class SyntheticNativeResult:
        capacity_limited = False

    native_result = SyntheticNativeResult()
    steady = _issue_result(
        SteadyReliquefierResult,
        inlet=liquid, outlet=liquid, target_quality=0.0, transfer=transfer,
        inlet_liquid_mass_fraction=0.0, outlet_liquid_mass_fraction=1.0,
        net_liquid_production_kg_s=0.1, native_component=object(),
        native_inlet=object(), native_result=native_result,
    )
    window = ProductWindow("authored-reliquefier-storage-clock", 5.0, 5.1)
    inventory = CollectedProductInventory(bridge.basis, 0.0, 0.0)
    cold = FiniteColdReservoir("synthetic-cold-reservoir", 1e6, 1e6, "authored-cold-reference")
    receipt = FiniteReliquefierProduct(
        ReliquefierProductPorts("feed", "product", "return", "vent")
    ).collect_steady(
        steady, window, collected_product_kg=1e-3,
        returned_kg=9e-3, vented_kg=0.0, product=inventory, cold=cold,
    )
    inlet = bind_reliquefier_product_to_separator(
        receipt, bridge, receiver_id="tank-liquid-region",
        clock_alignment_evidence_id="authored-common-absolute-clock",
        receiver_assignment_evidence_id="authored-liquid-phase-port-mapping",
        transfer_boundary_evidence_id="authored-liquid-transfer-pressure-thermal-boundary",
    )
    flow_groups = inlet.phase_flows(5.05, None)
    assert len(flow_groups[0]) == 1 and not flow_groups[1]
    assert type(flow_groups[0][0]) is MassEnergyFlow
    assert flow_groups[0][0].mass_flow_kg_s == 1e-2
    assert flow_groups[0][0].specific_enthalpy_J_kg == receipt.product_state.enthalpy_j_kg
    rejected = 0
    for out_of_window in (4.99, 5.11):
        try:
            inlet.phase_flows(out_of_window, None)
        except ValueError:
            rejected += 1
    try:
        bind_reliquefier_product_to_separator(
            receipt, bridge, receiver_id="tank-liquid-region",
            clock_alignment_evidence_id="authored-common-absolute-clock",
            receiver_assignment_evidence_id="authored-liquid-phase-port-mapping",
            transfer_boundary_evidence_id="",
        )
    except ValueError:
        rejected += 1
    assert rejected == 3

    def phase_domain(state):
        assert 10. < state.temperature_k < 100.
        assert 1e4 <= state.pressure_pa <= 1.25e6

    trace = run_finite_pure_fluid_separator(
        tank, initial, bridge=bridge, material_species_id="H2:para",
        duration_s=0.1, maximum_step_s=0.01, start_time_s=5.0,
        clock_id=inlet.clock_id, phase_flows=inlet.phase_flows,
        ambient_temperature_k=30.,
        phase_assignment_evidence_id="authored-liquid-inlet-phase-assignment",
        phase_domains={"liquid": phase_domain, "vapor": phase_domain},
        mass_tolerance_kg=1e-9, energy_tolerance_j=1e-3,
        minimum_liquid_inventory_kg=1e-10, minimum_vapor_inventory_kg=1e-10,
    )
    inlet.require_current()
    trace.require_current()
    assert abs(trace.points[-1].total_mass_kg-trace.points[0].total_mass_kg-1e-3) <= 1e-9
    return ValidationOutcome(True, {
        "collected_product_kg": receipt.allocation.collected_product_mass_kg,
        "liquid_inlet_rate_kg_s": inlet.mass_flow_kg_s,
        "native_separator_mass_change_kg": trace.points[-1].total_mass_kg-trace.points[0].total_mass_kg,
        "maximum_mass_residual_kg": max(abs(point.mass_residual_kg) for point in trace.points),
        "maximum_energy_residual_j": max(abs(point.energy_residual_j) for point in trace.points),
    }, ("Synthetic interface contract only; no liquid-transfer hydraulics or tank qualification is implied.",))
