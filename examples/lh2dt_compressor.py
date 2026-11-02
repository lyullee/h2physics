"""Explicit native compression boundaries; definitions only, not executed."""


def native_modules(native_target=None):
    import importlib
    import sys
    from pathlib import Path

    target = Path(native_target) if native_target is not None else Path(__file__).resolve().parents[1]/"artifacts/native_packages"
    target = target.resolve()
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    modules = {}
    for name in ("compressor", "properties", "tank", "network", "dynamic_network", "dynamic_vaporizer"):
        module = importlib.import_module("lh2dt."+name)
        if Path(module.__file__).resolve() != target/"lh2dt"/(name+".py"):
            raise ValueError("Native import did not resolve to the explicitly selected installation")
        modules[name] = module
    return modules


def build_stage(*, native_target=None, fluid="Hydrogen", ratio=2., efficiency=.8, stage_id="example-stage"):
    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_compressor import CompressorEnvelope, Lh2dtCompressorStage
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.thermo import CoolPropProperties

    native = native_modules(native_target)
    direct = CoolPropProperties(fluid)
    properties = Lh2dtLowLevelProperties(direct, state_factory=native["properties"].ThermoState)
    bridge = Lh2dtProperties(properties, reference_id=direct.basis.reference_id)
    stage = Lh2dtCompressorStage(native["compressor"].Compressor(properties,
        pressure_ratio=ratio, isentropic_efficiency=efficiency), bridge,
        state_factory=native["properties"].ThermoState, stage_id=stage_id,
        envelope=CompressorEnvelope(1e4, 1e8, 100., 1000., 1e-5, .1,
            "authored-thermodynamic-envelope-not-a-machine-map"))
    return stage, direct, native


def accepted_source(stage, native, *, start_s=100., duration_s=.1):
    """A genuine closed native source row; no compressor withdrawal is applied."""
    properties = stage.bridge.native
    fluid = properties.from_pT(1e6, 300.)
    geometry = native["tank"].TankGeometry(.02, 100., .1, .1)
    tank = native["tank"].HomogeneousTank(geometry, properties)
    mass = geometry.volume_m3*fluid.density_kg_m3
    initial = native["tank"].TankState(mass, mass*fluid.specific_internal_energy_J_kg, 300.)
    network = native["network"].SteadyNetwork(properties=properties)
    network.add_boundary("finite-source", tank.thermo(initial))
    node = native["dynamic_network"].homogeneous_tank_node("finite-source", tank, initial, 300.)
    simulator = native["dynamic_network"].DynamicNetworkSimulator(network, {"finite-source": node})
    rows = simulator.simulate(duration_s, duration_s)
    source = stage.bind_finite_source(tank, rows[-1], node_id="finite-source",
        local_time_origin_s=start_s, clock_tolerance_s=1e-10,
        clock_id="authored-source-clock", source_id="authored-native-finite-source")
    return source, simulator, rows


def run_example(*, native_target=None):
    stage, _, native = build_stage(native_target=native_target)
    source, simulator, rows = accepted_source(stage, native)
    point = stage.evaluate(source.fluid, .01, finite_source=source)
    point.require_current()
    return point, source, simulator, rows
