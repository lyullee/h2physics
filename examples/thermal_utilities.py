"""Deferred finite heat accounting examples; no work runs on import.

Authored budgets/temperature bounds are explicit assumptions, not vendor or
measurement evidence. Native calculations occur only when these functions are
called later in the authorized environment.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeclaredSource:
    edges_s: tuple
    signed_heat_j: tuple
    clock_id: str
    source_id: str
    basis_id: str
    original_boundary_owner: object


@dataclass(frozen=True, slots=True)
class DeclaredHeatAdapter:
    identifier: str = "authored-explicit-finite-heat-entries-not-a-physical-model"

    def snapshot(self, source, window):
        from h2physics.adapters.thermal_utilities import HeatComponent, HeatSnapshot

        if type(source) is not DeclaredSource or source.clock_id != window.clock_id:
            raise TypeError("Use the original explicitly authored finite entry and clock")
        return HeatSnapshot(
            source,
            window,
            source.source_id,
            "authored-thermal-boundary",
            source.basis_id,
            source.edges_s,
            source.signed_heat_j,
            (HeatComponent(source.original_boundary_owner, "heat-port"),),
            ((),) * (len(source.edges_s) - 1),
            "required-process-duty",
            ("authored-finite-numerical-input-not-measurement", window.evidence_id),
            (source.original_boundary_owner,),
            "declared finite numerical entries; no native process model",
        )


def declared_case():
    from h2physics.adapters.thermal_utilities import (
        ExergyReference,
        HeatAllocation,
        HeatAvailability,
        HeatDuty,
        HeatWindow,
        TemperatureLevel,
        account_heat,
    )
    from h2physics.core import Origin

    window = HeatWindow(0.0, 2.0, "authored-heat-clock", "explicit-two-second-window")
    donor = HeatDuty.bind(
        DeclaredSource(
            (0.0, 1.0, 2.0),
            (-15.0, -25.0),
            window.clock_id,
            "authored-hot-duty",
            "authored-donor-reference",
            {"role": "explicit donor ledger"},
        ),
        DeclaredHeatAdapter(),
        window,
    )
    sink = HeatDuty.bind(
        DeclaredSource(
            (0.0, 1.0, 2.0),
            (10.0, 20.0),
            window.clock_id,
            "authored-cold-duty",
            "authored-sink-reference",
            {"role": "explicit sink ledger"},
        ),
        DeclaredHeatAdapter(),
        window,
    )
    environment = ExergyReference(
        "authored-environment",
        298.15,
        101325.0,
        "authored-air",
        "explicit-environment-context-no-exergy-evaluation",
        "declared-context-only",
    )
    hot = TemperatureLevel(
        400.0, 410.0, "authored-hot-interface", "explicit-interval-bounds", environment
    )
    cold = TemperatureLevel(
        320.0, 330.0, "authored-cold-interface", "explicit-interval-bounds", environment
    )
    budget = HeatAvailability(
        donor,
        [12.0, 22.0],
        "explicit-finite-recoverable-budget",
        "authored-single-hot-boundary",
        donor.source,
        Origin.SYNTHETIC,
    )
    transfer = HeatAllocation(
        "declared-contact",
        budget,
        sink,
        [11.0, 21.0],
        [10.0, 20.0],
        [1.0, 1.0],
        (hot, hot),
        (cold, cold),
        5.0,
        "authored-passive-contact",
        "heat-increments-J-with-separate-process-reference-zeros",
        "explicit-one-joule-per-bin-loss-to-declared-environment",
        "authored-within-bin-coincidence-assumption-not-a-time-resolved-model",
    )
    result = account_heat(
        (donor, sink),
        (transfer,),
        evidence_id="authored-finite-allocation",
        energy_tolerance_j=1e-9,
    )
    return result, donor, sink, budget, transfer


def native_exchanger_case(*, native_target=None):
    from examples.lh2dt_heat_exchanger import run_example
    from h2physics.adapters.thermal_utilities import (
        ExergyReference,
        FiniteExchangerHeatAdapter,
        HeatAllocation,
        HeatAvailability,
        HeatDuty,
        HeatWindow,
        NativeExchangeReceipt,
        TemperatureLevel,
        account_heat,
    )
    from h2physics.core import Origin

    model, trace = run_example(native_target=native_target)
    window = HeatWindow(
        trace.points[0].time_s,
        trace.points[-1].time_s,
        trace.clock_id,
        "original-native-finite-HX-window",
    )
    donor = HeatDuty.bind(trace, FiniteExchangerHeatAdapter("left"), window)
    sink = HeatDuty.bind(trace, FiniteExchangerHeatAdapter("right"), window)
    receipt = NativeExchangeReceipt.bind(
        donor,
        sink,
        evidence_id="actual-closed-native-interwall-transfer",
        energy_tolerance_j=trace.inventory_tolerances.energy_absolute_j,
    )
    environment = ExergyReference(
        "authored-HX-environment",
        298.15,
        101325.0,
        "authored-air",
        "context-only-no-exergy-or-refrigerator-work",
        "declared-context-only",
    )
    hot = TemperatureLevel(
        380.0, 405.0, "actual-left-wall", "authored-interval-bound-not-a-vendor-limit", environment
    )
    cold = TemperatureLevel(
        245.0, 270.0, "actual-right-wall", "authored-interval-bound-not-a-vendor-limit", environment
    )
    n = len(receipt.heat_j)
    budget = HeatAvailability(
        donor,
        donor.rejection_j,
        "already-settled-native-finite-heat",
        "original-native-left-wall-heat-port",
        trace,
        Origin.PREDICTED,
    )
    transfer = HeatAllocation(
        "original-native-HX-transfer",
        budget,
        sink,
        receipt.heat_j,
        receipt.heat_j,
        [0.0] * n,
        (hot,) * n,
        (cold,) * n,
        0.0,
        "actual-native-wall-contact",
        "separate-normal-and-para-closed-inventory-heat-increments",
        "native-closed-pair-has-no-external-heat-loss",
        "actual-same-native-simultaneous-composite-integration",
        receipt,
    )
    ledger = account_heat(
        (donor, sink),
        (transfer,),
        evidence_id="record-original-native-closed-transfer-once",
        energy_tolerance_j=trace.inventory_tolerances.energy_absolute_j,
    )
    return ledger, model, trace, donor, sink, transfer


def process_duties():
    """Read original traces separately; different clocks are never aligned here."""
    from examples.carrier_conversion import run_liquid_example
    from examples.microbial_cell import build_problem
    from examples.pv_electrolysis import build_model, run_example
    from h2physics.adapters.microbial_economics import MicrobialCostProjection
    from h2physics.adapters.physical_economics import PhysicalCostProjection, ReportingWindow
    from h2physics.adapters.thermal_utilities import (
        CarrierHeatAdapter,
        HeatDuty,
        HeatWindow,
        ProjectionHeatAdapter,
    )

    pv = run_example(build_model())
    pv_projection = PhysicalCostProjection.from_pv_electrolysis(
        pv,
        ReportingWindow(
            pv.initial.time_s,
            pv.final.time_s,
            pv.evidence.clock_id,
            "actual-PV-full-window",
            "generated_h2_kg",
        ),
        hydrogen_id="hydrogen",
    )
    pw = HeatWindow(
        pv.initial.time_s, pv.final.time_s, pv.evidence.clock_id, "actual-PV-heat-window"
    )
    model, initial, stages = build_problem()
    mec = model.run(initial, stages)
    mec_projection = MicrobialCostProjection.from_microbial_cell(
        mec,
        ReportingWindow(
            stages[0].start_s,
            stages[-1].end_s,
            mec.evidence.clock_id,
            "actual-MEC-full-window",
            "generated_h2_kg",
        ),
        hydrogen_id="hydrogen",
    )
    mw = HeatWindow(
        stages[0].start_s, stages[-1].end_s, mec.evidence.clock_id, "actual-MEC-heat-window"
    )
    carrier = run_liquid_example()
    rows = carrier.process_trace.steps
    cw = HeatWindow(
        rows[0].stage.start_s,
        rows[-1].stage.end_s,
        carrier.evidence.clock_id,
        "actual-carrier-full-window",
    )
    return {
        "pv_stack": HeatDuty.bind(pv_projection, ProjectionHeatAdapter("pv-stack"), pw),
        "pv_receiver": HeatDuty.bind(pv_projection, ProjectionHeatAdapter("pv-receiver"), pw),
        "mec": HeatDuty.bind(mec_projection, ProjectionHeatAdapter("mec"), mw),
        "carrier": HeatDuty.bind(carrier, CarrierHeatAdapter(), cw),
    }


def native_device_duties(*, native_target=None):
    import importlib

    from examples.lh2dt_compressor import native_modules
    from h2physics.adapters.lh2dt_compressor import Lh2dtNativeProvenance
    from h2physics.adapters.lh2dt_reliquefier import Lh2dtSteadyReliquefier
    from h2physics.adapters.thermal_utilities import (
        DynamicDeviceHeatAdapter,
        HeatDuty,
        HeatWindow,
        SteadyNativeHeatAdapter,
    )
    from h2physics.dynamics import InventoryTolerances
    from scripts.check_reliquefier_integration import domain, make_dynamic, make_run, properties

    native_modules(native_target)
    native = importlib.import_module("lh2dt")
    direct, facade, bridge = properties(native)
    cooler = native.Reliquefier(30.0, facade)
    model = Lh2dtSteadyReliquefier(
        cooler,
        bridge,
        state_factory=native.ThermoState,
        domain=domain(),
        component_id="authored-cold-point",
    )
    cold = model.evaluate(direct.saturated(2e5, 1.0), outlet_pressure_pa=2e5, mass_flow_kg_s=1e-4)
    vaporizer = native.Vaporizer(0.2, 30.0, facade)
    hot = vaporizer.evaluate(facade.from_pT(2e5, 30.0), 2e5, 1e-5, 80.0)
    window = HeatWindow(
        10.0, 10.25, "authored-explicit-steady-hold", "quarter-second-hold-not-observation"
    )
    cold_profile = HeatDuty.bind(
        cold,
        SteadyNativeHeatAdapter(
            "reliquefier",
            cooler,
            bridge,
            Lh2dtNativeProvenance.capture(cooler, cold.native_result),
            "explicit-native-cold-point-held-for-declared-window",
        ),
        window,
    )
    hot_profile = HeatDuty.bind(
        hot,
        SteadyNativeHeatAdapter(
            "vaporizer",
            vaporizer,
            bridge,
            Lh2dtNativeProvenance.capture(vaporizer, hot),
            "explicit-native-vaporizer-point-held-for-declared-window",
        ),
        window,
    )
    direct2, dynamic = make_dynamic(native, fluid_ua=5.0, cold_ua=5.0, cap=2.0, wall_capacity=2.0)
    initial = dynamic.initialize(direct2.state_pt(2e5, 25.0), wall_temperature_k=25.0)
    binding, run = make_run(native, dynamic, initial, duration=0.02, step=0.01)
    dw = HeatWindow(
        run.start_time_s, run.steps[-1].time_s, run.clock_id, "original-finite-cold-side-window"
    )
    dynamic_profile = HeatDuty.bind(
        run,
        DynamicDeviceHeatAdapter(
            "cold-volume",
            dynamic.native,
            Lh2dtNativeProvenance.capture(dynamic.native, *(r.native for r in run.steps)),
            binding,
            "original-native-cold-volume-node-component-link",
            InventoryTolerances(1e-8, 1e-4, 1e-8),
        ),
        dw,
    )
    return cold_profile, hot_profile, dynamic_profile


if __name__ == "__main__":
    raise SystemExit(
        "Execution deferred: call explicit example functions only in the authorized environment."
    )
