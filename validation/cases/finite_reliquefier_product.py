"""Deferred finite-reliquefier-product acceptance definitions."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Implemented_unverified; no local model or native execution.",
    "No separator, COP, cycle, controller, depletion root or apparatus qualification.",
)


def cases():
    definitions = (
        ("reliquefier-product-steady", "validate_steady", ("original steady result", "mass/enthalpy collection")),
        ("reliquefier-product-cold", "validate_cold", ("finite cold budget", "native steady duty")),
        ("reliquefier-product-dynamic", "validate_dynamic", ("original dynamic inventory", "explicit accumulated mass")),
        ("reliquefier-product-guards", "validate_guards", ("unique ports", "all-liquid product")),
        ("reliquefier-product-depletion", "validate_depletion", ("finite cooling rejection",)),
        ("reliquefier-product-stale", "validate_stale", ("original result seal",)),
        ("reliquefier-reversible-work", "validate_reversible_work", ("flow-exergy minimum work", "specific external work")),
        ("reliquefier-reversible-work-boundary", "validate_reversible_work_boundary", ("property basis", "loss-free mass boundary")),
    )
    return tuple(ValidationCase(identifier=name, profile="reliquefier-product",
        entrypoint=__name__+":"+entry, parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)


def _fixture():
    from dataclasses import dataclass

    from h2physics.adapters.lh2dt_reliquefier import SteadyReliquefierResult, _issue_result
    from h2physics.adapters.reliquefier_product import (
        CollectedProductInventory,
        FiniteColdReservoir,
        FiniteReliquefierProduct,
        ProductWindow,
        ReliquefierProductPorts,
    )
    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.equipment import BoundaryPower, ConnectionTransfer

    @dataclass
    class Native:
        capacity_limited: bool = False

    basis = PropertyBasis("Hydrogen", "case-reference", "normal")
    inlet = ThermoState(basis, 2e5, 30.0, 2.0, 4e5, 3e5, 1e4, "gas")
    outlet = ThermoState(basis, 1.5e5, 20.0, 70.0, 1e5, 0.98e5, 5e3, "liquid",
                         vapor_mass_fraction=0.0, raw_vapor_mass_fraction=0.0)
    transfer = ConnectionTransfer("rq", "rq:in", "rq:out", "rq/in", "rq/out", 0.1,
        inlet, outlet, BoundaryPower(heat_w=-30000.0), None, None)
    native = Native()
    result = _issue_result(SteadyReliquefierResult, inlet=inlet, outlet=outlet,
        target_quality=0.0, transfer=transfer, inlet_liquid_mass_fraction=0.0,
        outlet_liquid_mass_fraction=1.0, net_liquid_production_kg_s=0.1,
        native_component=object(), native_inlet=object(), native_result=native)
    collector = FiniteReliquefierProduct(ReliquefierProductPorts("feed", "product", "return", "vent"))
    window = ProductWindow("case-clock", 0.0, 10.0)
    product = CollectedProductInventory(basis, 0.0, 0.0)
    cold = FiniteColdReservoir("cold", 1e6, 1e6, "case-cold-reference")
    return collector, result, window, product, cold


def validate_steady(*, work_directory, **parameters):
    collector, result, window, product, cold = _fixture()
    receipt = collector.collect_steady(result, window, collected_product_kg=0.8,
                                       returned_kg=0.2, vented_kg=0.0,
                                       product=product, cold=cold)
    assert receipt.product_after.mass_kg == 0.8 and receipt.allocation.mass_residual_kg == 0.0
    return ValidationOutcome(True, {"collected_kg": receipt.product_after.mass_kg}, LIMITS)


def validate_cold(*, work_directory, **parameters):
    collector, result, window, product, cold = _fixture()
    receipt = collector.collect_steady(result, window, collected_product_kg=1.0,
                                       returned_kg=0.0, vented_kg=0.0,
                                       product=product, cold=cold)
    assert receipt.cold_before.remaining_available_cooling_j - receipt.cold_after.remaining_available_cooling_j == 300000.0
    return ValidationOutcome(True, {"removed_heat_j": receipt.cold_duty.removed_heat_j}, LIMITS)


def validate_dynamic(*, work_directory, **parameters):

    from h2physics.adapters.lh2dt_reliquefier import ReliquefierDerivative, ReliquefierStep, _issue_result
    from h2physics.adapters.reliquefier_product import DynamicInventoryWitness, IntegratedColdDuty
    from h2physics.core import Origin
    from h2physics.dynamics import ConservedInventory
    from h2physics.equipment import BoundaryPower

    collector, steady, window, product, cold = _fixture()
    basis = steady.outlet.basis
    initial = ConservedInventory(basis, 2.0, 2e5, 1e5)
    final = ConservedInventory(basis, 2.2, 2.2e5, 1e5)
    rates = ReliquefierDerivative(steady.outlet, BoundaryPower(heat_w=-1000.0), 0.0, 0.0, 0.0, object())
    step = _issue_result(ReliquefierStep, fluid=steady.outlet, inventory=final,
                         liquid_inventory_kg=2.2, final_rates=rates, native=object())
    receipt = collector.collect_dynamic(step, window, feed_kg=0.5, collected_product_kg=0.2,
        returned_kg=0.1, vented_kg=0.0, inventory=DynamicInventoryWitness(initial, final),
        cold_duty=IntegratedColdDuty(10000.0, "integrated-native-duty", Origin.PREDICTED),
        product=product, cold=cold)
    assert abs(receipt.allocation.device_accumulation_kg-0.2) < 1e-15
    return ValidationOutcome(True, {"accumulation_kg": receipt.allocation.device_accumulation_kg}, LIMITS)


def validate_guards(*, work_directory, **parameters):
    from dataclasses import replace
    from h2physics.adapters.lh2dt_reliquefier import SteadyReliquefierResult
    from h2physics.adapters.lh2dt_reliquefier import _issue_result
    from h2physics.adapters.reliquefier_product import ReliquefierProductPorts

    rejected = 0
    try:
        ReliquefierProductPorts("same", "same", "return", "vent")
    except ValueError:
        rejected += 1
    collector, result, window, product, cold = _fixture()
    try:
        SteadyReliquefierResult(result.inlet, result.inlet, result.target_quality, result.transfer,
            result.inlet_liquid_mass_fraction, 0.0, 0.0, result.native_component,
            result.native_inlet, result.native_result)
    except ValueError:
        rejected += 1
    bad = _issue_result(SteadyReliquefierResult, inlet=result.inlet, outlet=result.inlet,
        target_quality=result.target_quality, transfer=result.transfer,
        inlet_liquid_mass_fraction=result.inlet_liquid_mass_fraction,
        outlet_liquid_mass_fraction=0.0, net_liquid_production_kg_s=0.0,
        native_component=result.native_component, native_inlet=result.native_inlet,
        native_result=result.native_result)
    try:
        collector.collect_steady(bad, window, collected_product_kg=1.0,
            returned_kg=0.0, vented_kg=0.0, product=product, cold=cold)
    except ValueError:
        rejected += 1
    try:
        replace(result, target_quality=0.5).require_current()
    except ValueError:
        rejected += 1
    receipt = collector.collect_steady(result, window, collected_product_kg=1.0,
        returned_kg=0.0, vented_kg=0.0, product=product, cold=cold)
    try:
        replace(receipt, mode="forged").require_current()
    except ValueError:
        rejected += 1
    assert rejected == 5
    return ValidationOutcome(True, {"rejections": rejected}, LIMITS)


def validate_depletion(*, work_directory, **parameters):
    from h2physics.adapters.reliquefier_product import FiniteColdReservoir

    collector, result, window, product, _ = _fixture()
    cold = FiniteColdReservoir("small", 1.0, 1.0, "case-cold-reference")
    try:
        collector.collect_steady(result, window, collected_product_kg=1.0,
            returned_kg=0.0, vented_kg=0.0, product=product, cold=cold)
    except ValueError as error:
        message = str(error)
    else:
        raise AssertionError("Finite cold budget accepted excessive duty")
    return ValidationOutcome(True, {"rejected": 1}, (*LIMITS, message))


def validate_stale(*, work_directory, **parameters):
    collector, result, window, product, cold = _fixture()
    receipt = collector.collect_steady(result, window, collected_product_kg=1.0,
        returned_kg=0.0, vented_kg=0.0, product=product, cold=cold)
    result.native_result.capacity_limited = True
    try:
        receipt.require_current()
    except ValueError as error:
        message = str(error)
    else:
        raise AssertionError("Mutated original native result retained a valid seal")
    return ValidationOutcome(True, {"rejected": 1}, (*LIMITS, message))


def validate_reversible_work(*, work_directory, **parameters):
    from h2physics.adapters.liquefaction_performance import (
        HydrogenFlowState, benchmark_hydrogen_liquefaction,
    )

    feed = HydrogenFlowState(450_000.0, 6_000.0, "h2-reference-a", "feed-state-data")
    liquid = HydrogenFlowState(20_000.0, 100.0, "h2-reference-a", "liquid-state-data")
    result = benchmark_hydrogen_liquefaction(
        feed=feed, liquid_product=liquid, feed_mass_kg=2.0, product_mass_kg=2.0,
        external_work_j=2.0e7, environment_temperature_k=300.0,
        process_window_id="liq-window-0001",
        process_evidence_id="work-meter-window-a",
    )
    assert result.minimum_reversible_work_j_kg == 1_340_000.0
    assert result.specific_external_work_kwh_kg == 2.0e7 / 2.0 / 3_600_000.0
    assert result.process_window_id == "liq-window-0001"
    return ValidationOutcome(True, {"minimum_work_j": result.minimum_reversible_work_j}, LIMITS)


def validate_reversible_work_boundary(*, work_directory, **parameters):
    from h2physics.adapters.liquefaction_performance import (
        HydrogenFlowState, benchmark_hydrogen_liquefaction,
    )

    feed = HydrogenFlowState(450_000.0, 6_000.0, "h2-reference-a", "feed-state-data")
    liquid = HydrogenFlowState(20_000.0, 100.0, "h2-reference-b", "liquid-state-data")
    rejected = 0
    try:
        benchmark_hydrogen_liquefaction(
            feed=feed, liquid_product=liquid, feed_mass_kg=1.0, product_mass_kg=1.0,
            external_work_j=1.0e7, environment_temperature_k=300.0,
            process_window_id="liq-window-0001",
            process_evidence_id="work-meter-window-a",
        )
    except ValueError:
        rejected += 1
    liquid = HydrogenFlowState(20_000.0, 100.0, "h2-reference-a", "liquid-state-data")
    try:
        benchmark_hydrogen_liquefaction(
            feed=feed, liquid_product=liquid, feed_mass_kg=1.1, product_mass_kg=1.0,
            external_work_j=1.0e7, environment_temperature_k=300.0,
            process_window_id="liq-window-0001",
            process_evidence_id="work-meter-window-a",
        )
    except ValueError:
        rejected += 1
    try:
        benchmark_hydrogen_liquefaction(
            feed=feed,
            liquid_product=liquid,
            feed_mass_kg=1.0,
            product_mass_kg=1.0,
            external_work_j=1.0e7,
            environment_temperature_k=300.0,
            process_window_id=" ",
            process_evidence_id="work-meter-window-a",
        )
    except ValueError:
        rejected += 1
    assert rejected == 3
    return ValidationOutcome(True, {"rejections": rejected}, LIMITS)
