"""Two actual sealed native fluid/wall sides; definitions only, not executed."""


def build_model(*, native_target=None, conductance=2., fluid_wall=(5., 6.), network_factory=None):
    from examples.lh2dt_compressor import native_modules
    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_heat_exchanger import (
        FiniteHeatExchangerSide,
        HeatExchangerCoupling,
        HeatExchangerDomain,
        Lh2dtFiniteHeatExchanger,
    )
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.core import Origin
    from h2physics.thermo import CoolPropProperties

    native = native_modules(native_target)
    sides = []
    for i, (name, fluid, pressure, volume, temperature, capacity) in enumerate((
        ("left", "Hydrogen", 3e5, .01, 400., 100.),
        ("right", "ParaHydrogen", 2e5, .02, 250., 150.),
    )):
        direct = CoolPropProperties(fluid)
        properties = Lh2dtLowLevelProperties(direct, state_factory=native["properties"].ThermoState)
        bridge = Lh2dtProperties(properties, reference_id=direct.basis.reference_id)
        core = native["dynamic_vaporizer"].DynamicVaporizer(volume, capacity, fluid_wall[i],
            300., conductance, 1e6, properties)
        initial = core.initialize(properties.from_pT(pressure, temperature))
        sides.append(FiniteHeatExchangerSide(name, core, initial, bridge,
            HeatExchangerDomain(200., 650., 1e3, 1e7, 1e-8,
                ("gas", "supercritical_gas", "supercritical")),
            "authored-initial-native-fluid-and-finite-wall"))
    model = Lh2dtFiniteHeatExchanger(*sides,
        HeatExchangerCoupling(conductance, "authored-conductance-not-vendor-data", Origin.SYNTHETIC,
            "LH2DT:b2f276333c1b1793c39f25763703d196d36742ec"),
        native_side_node_factory=native["dynamic_network"].dynamic_vaporizer_node,
        native_network_factory=network_factory or native["network"].SteadyNetwork,
        native_simulator_factory=native["dynamic_network"].DynamicNetworkSimulator,
        equipment_id="example-finite-HX")
    return model, native


def run_example(*, native_target=None):
    model, _ = build_model(native_target=native_target)
    trace = model.run(duration_s=2., maximum_step_s=.1, start_time_s=100., clock_id="authored-HX-clock")
    trace.require_current()
    return model, trace
