"""Caller-scheduled finite native transfer; definitions only, never run on import."""


def build_model(*, native_target=None, with_line=False, reverse=False, source_pressure_pa=3e6,
                receiver_pressure_pa=1e6, stress_ambient=False):
    import importlib
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    import numpy as np

    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_equipment import Lh2dtSharedValve
    from h2physics.adapters.lh2dt_finite_transfer import (
        FiniteTransferBody,
        Lh2dtFiniteTransfer,
        TransferAmbient,
    )
    from h2physics.adapters.lh2dt_heat_exchanger import HeatExchangerDomain
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.core import Origin, TimeSeries
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties

    target = (Path(native_target) if native_target is not None else
              Path(__file__).resolve().parents[1]/"artifacts/native_packages").resolve()
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    modules = {}
    for name in ("tank", "properties", "network", "dynamic_network", "dynamic_pipe", "valve"):
        module = importlib.import_module("lh2dt."+name)
        if Path(module.__file__).resolve() != target/"lh2dt"/(name+".py"):
            raise ValueError("Native import did not resolve to the selected installed source")
        modules[name] = module
    api = SimpleNamespace(SteadyNetwork=modules["network"].SteadyNetwork,
        DynamicNetworkSimulator=modules["dynamic_network"].DynamicNetworkSimulator,
        homogeneous_tank_node=modules["dynamic_network"].homogeneous_tank_node,
        dynamic_hem_pipe_node=modules["dynamic_network"].dynamic_hem_pipe_node,
        ThermoState=modules["properties"].ThermoState)
    direct = CoolPropProperties("Hydrogen")
    native_properties = Lh2dtLowLevelProperties(direct, state_factory=api.ThermoState)
    bridge = Lh2dtProperties(native_properties, reference_id=direct.basis.reference_id)
    domain = HeatExchangerDomain(200., 650., 1e4, 1e8, 1e-8,
                                ("gas", "supercritical_gas", "supercritical"))
    times = np.array((100., 100.1, 100.2, 102.))
    temperatures = np.array((300., 300., 1e12 if stress_ambient else 300.,
                             1e12 if stress_ambient else 300.))[:, None]
    ambient = TransferAmbient(TimeSeries(times, temperatures, ("ambient",), ("K",),
        np.ones((4, 1), dtype=bool), "authored-transfer-clock", Origin.SYNTHETIC,
        "authored-ambient-stress-input" if stress_ambient else "authored-isothermal-environment",
        ("ambient_temperature",)))
    bodies = []
    for name, pressure, volume in (("source", source_pressure_pa, .05),
                                   ("receiver", receiver_pressure_pa, .01)):
        fluid = native_properties.from_pT(pressure, 300.)
        geometry = modules["tank"].TankGeometry(volume, 1000., .1, .1)
        core = modules["tank"].HomogeneousTank(geometry, native_properties)
        mass = volume*fluid.density_kg_m3
        state = modules["tank"].TankState(mass, mass*fluid.specific_internal_energy_J_kg, 300.)
        bodies.append(FiniteTransferBody(name, "homogeneous-tank", core, state, domain,
            "authored-finite-"+name, "authored-tank-wall-and-ambient", ambient))
    line = None
    if with_line:
        core = modules["dynamic_pipe"].DynamicHEMPipe(1., .01, 1e-6, 100.,
            fluid_wall_UA_W_K=.1, ambient_temperature_K=300., ambient_UA_W_K=.1,
            fluid_volume_m3=.001, properties=native_properties)
        state = core.initialize(native_properties.from_pT(2e6, 300.))
        line = FiniteTransferBody("line", "mixed-line", core, state, domain,
            "authored-native-line-holdup", "authored-fixed-line-ambient-and-film-UAs", None)
    valves = tuple(Lh2dtSharedValve(HomogeneousIsentropicNozzle(direct), bridge,
        NozzleOpening.circular("authored-valve-"+str(i), .0003, effective_area_factor=.8,
            area_basis_id="authored-effective-area-not-qualified-hardware"),
        result_factory=modules["valve"].ValveResult, opening_fraction=0., allow_reverse=reverse)
        for i in range(2 if with_line else 1))
    model = Lh2dtFiniteTransfer(*bodies, bridge=bridge, native_api=api, valves=valves,
        equipment_id="authored-finite-transfer", line=line)
    return model


def schedule(model):
    from h2physics.adapters.lh2dt_finite_transfer import TransferStage

    return (TransferStage("transfer", 100., 100.2, "transfer", (1.,)*len(model.valves),
                          "authored-fixed-opening-window"),
            TransferStage("isolated-hold", 100.2, 100.4, "isolated", (0.,)*len(model.valves),
                          "authored-instantaneous-isolation-boundary"))


def run_example(*, native_target=None, with_line=False):
    model = build_model(native_target=native_target, with_line=with_line)
    trace = model.run(schedule(model), clock_id="authored-transfer-clock", maximum_step_s=.05,
                      clock_tolerance_s=1e-10, isolate_on_completion=True)
    trace.require_current()
    return model, trace
