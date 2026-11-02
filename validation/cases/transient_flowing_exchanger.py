"""Deferred actual native flowing hold-up contract; no execution at import."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="native-transient-flowing-exchanger-holdup", profile="flowing-heat-exchanger",
        entrypoint=__name__ + ":validate_transient",
        invariants=("actual native flow derivatives and integration advance both finite sides",
                    "per-stage streams use current fluid states and declared reference",
                    "mass and fluid-wall energy close with cumulative transport",
                    "accepted interwall heat cancels globally",
                    "irregular declared boundary changes are rejected before native integration"),
    ),)


def build_trace(*, interval_aware=False):
    from lh2dt.dynamic_network import DynamicNetworkSimulator, dynamic_vaporizer_node
    from lh2dt.dynamic_vaporizer import DynamicVaporizer
    from lh2dt.network import SteadyNetwork
    from lh2dt.properties import ThermoState
    from lh2dt.streams import MassEnergyFlow

    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_compressor import Lh2dtNativeProvenance
    from h2physics.adapters.lh2dt_heat_exchanger import (
        FiniteHeatExchangerSide,
        HeatExchangerCoupling,
        HeatExchangerDomain,
        Lh2dtFiniteHeatExchanger,
    )
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.adapters.lh2dt_transient_flowing_exchanger import Lh2dtTransientFlowingExchanger
    from h2physics.core import Origin
    from h2physics.thermo import CoolPropProperties

    sides = []
    for name, temperature in (("left", 320.), ("right", 280.)):
        eos = CoolPropProperties()
        native_properties = Lh2dtLowLevelProperties(eos, state_factory=ThermoState)
        bridge = Lh2dtProperties(native_properties, reference_id=eos.basis.reference_id)
        component = DynamicVaporizer(.01, 100., 5., 300., 2., 1e6, native_properties)
        state = component.initialize(native_properties.from_pT(3e5, temperature))
        sides.append(FiniteHeatExchangerSide(name, component, state, bridge,
            HeatExchangerDomain(200., 500., 1e3, 1e7, 1e-8,
                               ("gas", "supercritical_gas", "supercritical")), "authored-initial-inventory"))
    provenance = Lh2dtNativeProvenance.capture(*(side.native_component for side in sides))
    owner = Lh2dtFiniteHeatExchanger(*sides,
        HeatExchangerCoupling(2., "authored-interwall-conductance", Origin.SYNTHETIC,
                             "LH2DT:"+provenance.revision),
        native_side_node_factory=dynamic_vaporizer_node, native_network_factory=SteadyNetwork,
        native_simulator_factory=DynamicNetworkSimulator, equipment_id="authored-flowing-hx")

    def streams(*, time_s, clock_id, fluids):
        assert clock_id == "authored-flowing-clock" and time_s >= 10.
        return {name: (MassEnergyFlow(1e-5, state.enthalpy_j_kg),
                       MassEnergyFlow(-1e-5, state.enthalpy_j_kg))
                for name, state in fluids.items()}

    def interval_streams(*, time_s, clock_id, fluids, interval_start_s, interval_end_s):
        assert interval_start_s <= time_s <= interval_end_s+1e-10
        assert clock_id == "authored-flowing-clock"
        rate = 1e-5 if interval_start_s == 10. else 0.
        return {name: (MassEnergyFlow(rate, state.enthalpy_j_kg),)
                for name, state in fluids.items()}

    trace = Lh2dtTransientFlowingExchanger(owner, streams,
        boundary_evidence_id="authored-current-state-balanced-native-streams").run(
            duration_s=.1, maximum_step_s=.01, start_time_s=10., clock_id="authored-flowing-clock",
            boundary_change_times_s=(10.035,) if interval_aware else (),
            interval_boundary_streams=interval_streams if interval_aware else None)
    return trace


def validate_transient(*, work_directory, **parameters):
    from dataclasses import replace

    del work_directory, parameters
    trace = build_trace()
    assert trace.require_current() is trace
    assert trace.points[-1].time_s == 10.1
    assert len(trace.native_boundary_evaluations) > len(trace.points)
    assert all(max(map(abs, point.mass_residuals_kg)) < 1e-10 for point in trace.points)
    direct_values = {
        name: getattr(trace, name)
        for name, field in type(trace).__dataclass_fields__.items()
        if field.init and name != "_issuer_token"
    }
    unissued_rejected = 0
    for construct in (
        lambda: type(trace)(**direct_values),
        lambda: replace(trace, clock_id="forged-clock"),
    ):
        try:
            construct()
        except TypeError:
            unissued_rejected += 1
    assert unissued_rejected == 2
    for change in (10.015, 10.02):
        try:
            trace.owner.run(duration_s=.1, maximum_step_s=.01, start_time_s=10.,
                            clock_id="authored-flowing-clock", boundary_change_times_s=(change,))
        except ValueError:
            pass
        else:
            raise AssertionError("Declared jump was admitted without an interval endpoint callback")
    from math import isclose
    jumped = build_trace(interval_aware=True)
    assert len(jumped.native_segments) == 2
    assert jumped.native_segments[1].initial_state is jumped.native_segments[0].final_state
    assert isclose(jumped.points[-1].native_state.left_ledgers[0], 1e-5*.035,
                   rel_tol=1e-12, abs_tol=1e-16)
    assert isclose(jumped.points[-1].native_state.right_ledgers[0], 1e-5*.035,
                   rel_tol=1e-12, abs_tol=1e-16)
    return ValidationOutcome(True, {"accepted_points": len(trace.points),
                                   "unissued_trace_rejections": unissued_rejected},
                             ("Authored finite mixed hold-up; no pressure-loss/counterflow spatial validation",))
