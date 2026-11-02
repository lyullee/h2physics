"""Native TESPy cycle solves and ExerPy physical-exergy analysis.

Temperatures and pressures at this boundary are K and Pa. Native network
objects remain available for direct component replacement and further solves.
No process topology, chemical-exergy reference or component map is inferred.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import version
from types import MappingProxyType

from ..core import finite


@dataclass(frozen=True, slots=True)
class RankineCycleSpec:
    """Pure-fluid, steady Rankine cycle with explicit hot/cold water boundaries.

    This four-component level omits recuperation, generator/motor losses,
    mechanical pressure losses on the working-fluid side and hydrogen chemistry.
    Changing ``working_fluid`` selects CoolProp's native pure-fluid properties.
    """

    working_fluid: str = "R245fa"
    mass_flow_kg_s: float = 1.0
    turbine_inlet_temperature_k: float = 400.0
    high_pressure_pa: float = 2_000_000.0
    low_pressure_pa: float = 200_000.0
    turbine_isentropic_efficiency: float = 0.85
    pump_isentropic_efficiency: float = 0.75
    hot_inlet_temperature_k: float = 450.0
    hot_outlet_temperature_k: float = 420.0
    hot_pressure_pa: float = 1_000_000.0
    cold_inlet_temperature_k: float = 290.0
    cold_outlet_temperature_k: float = 300.0
    cold_pressure_pa: float = 200_000.0
    external_pressure_ratio: float = 0.99
    source_id: str = "declared-design-case"

    def __post_init__(self):
        if not self.working_fluid.strip() or not self.source_id.strip():
            raise ValueError("Declare fluid identity and design-condition source")
        for name in self.__dataclass_fields__:
            if name not in {"working_fluid", "source_id"}:
                finite(getattr(self, name), name, positive=True)
        for value in (self.turbine_isentropic_efficiency,
                      self.pump_isentropic_efficiency, self.external_pressure_ratio):
            if value > 1:
                raise ValueError("Efficiencies and pressure ratios cannot exceed one")
        if self.high_pressure_pa <= self.low_pressure_pa:
            raise ValueError("Expansion requires high pressure greater than low pressure")
        if not (self.hot_inlet_temperature_k > self.hot_outlet_temperature_k
                > self.turbine_inlet_temperature_k > self.cold_outlet_temperature_k
                > self.cold_inlet_temperature_k):
            raise ValueError("Declare ordered heating/cooling boundary temperatures")


@dataclass(frozen=True, slots=True)
class CycleEnergyAudit:
    """Signed external duties; positive heat/work enters the working fluid."""

    heat_input_w: float
    heat_rejected_w: float
    turbine_output_w: float
    pump_input_w: float
    net_output_w: float
    first_law_residual_w: float
    maximum_mass_residual_kg_s: float
    source_id: str
    tespy_version: str
    coolprop_version: str

    @property
    def thermal_efficiency(self):
        return self.net_output_w / self.heat_input_w


@dataclass(frozen=True, slots=True)
class SolvedRankineCycle:
    network: object
    spec: RankineCycleSpec
    energy: CycleEnergyAudit


def solve_rankine_cycle(spec: RankineCycleSpec = RankineCycleSpec()) -> SolvedRankineCycle:
    """Build and solve a real TESPy network, using CoolProp-backed fluids.

    The two finite-temperature water streams provide resolved heat supply and
    rejection. The result is a thermal power-cycle example suitable for coupling
    net shaft power to a separately defined electrolyzer; it is not an H2
    liquefier, a geothermal reservoir model or a measured plant qualification.
    """
    from tespy.components import (
        Condenser,
        CycleCloser,
        HeatExchanger,
        PowerSink,
        PowerSource,
        Pump,
        Sink,
        Source,
        Turbine,
    )
    from tespy.connections import Connection, PowerConnection
    from tespy.networks import Network

    if not isinstance(spec, RankineCycleSpec):
        raise TypeError("Supply RankineCycleSpec")
    nw = Network(iterinfo=False)
    # TESPy default units are explicitly replaced at this public SI boundary.
    nw.units.set_defaults(temperature="K", pressure="Pa", pressure_difference="Pa", enthalpy="J/kg",
                          power="W", heat="W", mass_flow="kg/s")
    cc, turbine, condenser, pump, boiler = (CycleCloser("cycle_closer"),
        Turbine("turbine"), Condenser("condenser"), Pump("pump"), HeatExchanger("boiler"))
    c1 = Connection(cc, "out1", turbine, "in1", label="turbine_inlet")
    c2 = Connection(turbine, "out1", condenser, "in1", label="turbine_outlet")
    c3 = Connection(condenser, "out1", pump, "in1", label="pump_inlet")
    c4 = Connection(pump, "out1", boiler, "in2", label="pump_outlet")
    c0 = Connection(boiler, "out2", cc, "in1", label="boiler_outlet")
    hot_in = Connection(Source("heat_source"), "out1", boiler, "in1", label="hot_in")
    hot_out = Connection(boiler, "out1", Sink("heat_return"), "in1", label="hot_out")
    cold_in = Connection(Source("coolant_source"), "out1", condenser, "in2", label="cold_in")
    cold_out = Connection(condenser, "out2", Sink("coolant_return"), "in1", label="cold_out")
    output = PowerConnection(turbine, "power", PowerSink("shaft_output"), "power", label="shaft_out")
    input_ = PowerConnection(PowerSource("pump_drive"), "power", pump, "power", label="shaft_in")
    nw.add_conns(c0, c1, c2, c3, c4, hot_in, hot_out, cold_in, cold_out, output, input_)
    turbine.set_attr(eta_s=spec.turbine_isentropic_efficiency)
    pump.set_attr(eta_s=spec.pump_isentropic_efficiency)
    boiler.set_attr(pr1=spec.external_pressure_ratio, pr2=1.0)
    condenser.set_attr(pr1=1.0, pr2=spec.external_pressure_ratio)
    c1.set_attr(T=spec.turbine_inlet_temperature_k, p=spec.high_pressure_pa,
                m=spec.mass_flow_kg_s, fluid={spec.working_fluid: 1.0})
    c2.set_attr(p=spec.low_pressure_pa)
    hot_in.set_attr(T=spec.hot_inlet_temperature_k, p=spec.hot_pressure_pa, fluid={"Water": 1.0})
    hot_out.set_attr(T=spec.hot_outlet_temperature_k)
    cold_in.set_attr(T=spec.cold_inlet_temperature_k, p=spec.cold_pressure_pa, fluid={"Water": 1.0})
    cold_out.set_attr(T=spec.cold_outlet_temperature_k)
    nw.solve("design", print_results=False)
    nw.assert_convergence()
    # A converged algebraic solution alone does not ensure feasible heat exchange.
    for component in (boiler, condenser):
        if min(component.ttd_u.val_SI, component.ttd_l.val_SI) <= 0:
            raise ValueError("Solved cycle crosses a heat-exchanger terminal temperature")
    qin = finite(-boiler.Q.val_SI, "boiler duty", positive=True)
    qout = finite(-condenser.Q.val_SI, "heat rejection", positive=True)
    wt = finite(-turbine.P.val_SI, "turbine output", positive=True)
    wp = finite(pump.P.val_SI, "pump input", positive=True)
    residual = qin - qout - wt + wp
    mass_residual = max(abs(c.m.val_SI-spec.mass_flow_kg_s) for c in (c0,c1,c2,c3,c4))
    audit = CycleEnergyAudit(qin, qout, wt, wp, wt-wp, residual, mass_residual,
                             spec.source_id, version("tespy"), version("CoolProp"))
    if abs(residual) > 1e-6 * max(qin, qout, wt, wp):
        raise ValueError("Solved cycle fails its external first-law balance")
    return SolvedRankineCycle(nw, spec, audit)


@dataclass(frozen=True, slots=True)
class PhysicalExergyAudit:
    """Native physical-exergy balance with caller-defined useful-product boundary."""

    analysis: object
    environment_temperature_k: float
    environment_pressure_pa: float
    fuel_exergy_w: float
    product_exergy_w: float
    loss_exergy_w: float
    destruction_exergy_w: float
    balance_residual_w: float
    component_destruction_w: Mapping[str, float]
    exerpy_version: str

    def __post_init__(self):
        object.__setattr__(self, "component_destruction_w",
                           MappingProxyType(dict(self.component_destruction_w)))


def analyze_physical_exergy(network, *, environment_temperature_k: float,
                           environment_pressure_pa: float, fuel: Mapping,
                           product: Mapping, loss: Mapping | None = None) -> PhysicalExergyAudit:
    """Pass a converged TESPy network directly to current ExerPy.

    Boundary dictionaries contain native connection labels under ``inputs`` and
    ``outputs``. In ExerPy 0.2 these mean additive and subtractive terms for
    EACH boundary, rather than physical directions across the plant boundary.
    Fuel/product/loss semantics belong to the declared application.
    Chemical exergy, reaction formation energy and kinetic/potential exergy are
    outside this physical-exergy calculation.
    """
    from exerpy import ExergyAnalysis
    from tespy.networks import Network
    if not isinstance(network, Network):
        raise TypeError("Supply an actual native TESPy Network")
    network.assert_convergence()
    temperature = finite(environment_temperature_k, "environment temperature", positive=True)
    pressure = finite(environment_pressure_pa, "environment pressure", positive=True)
    analysis = ExergyAnalysis.from_tespy(network, Tamb=temperature, pamb=pressure,
                                         chemExLib=None, split_physical_exergy=True)
    def boundary(value):
        result = {key: list(labels) for key, labels in value.items()}
        if set(result) - {"inputs", "outputs"}:
            raise ValueError("Exergy boundaries use inputs/outputs connection labels")
        if any(isinstance(labels, str) for labels in value.values()):
            raise ValueError("Supply sequences of connection labels, not a string")
        return result
    analysis.analyse(E_F=boundary(fuel), E_P=boundary(product),
                     E_L=boundary(loss or {}))
    destruction = {name: finite(comp.E_D, "component destruction")
                   for name, comp in analysis.components.items()
                   if comp.__class__.__name__ != "CycleCloser"}
    ef, ep, el = (finite(getattr(analysis, name), name) for name in ("E_F", "E_P", "E_L"))
    ed = math.fsum(destruction.values())
    return PhysicalExergyAudit(analysis, temperature, pressure, ef, ep, el, ed,
                               ef-ep-el-ed, destruction, version("exerpy"))


def analyze_rankine_exergy(cycle: SolvedRankineCycle, *, environment_temperature_k=298.15,
                          environment_pressure_pa=101325.0) -> PhysicalExergyAudit:
    """Hot stream and any consumed coolant exergy supply net shaft output.

    Cooling water below the reference temperature may LOSE physical exergy
    while absorbing heat: that decrease is an additional resource. A net
    coolant exergy increase is instead a declared rejected-stream loss. The
    difference uses native connection h/s on the same water reference; it does
    not require a new fluid-property closure.
    """
    temperature = finite(environment_temperature_k, "environment temperature", positive=True)
    cold_in = cycle.network.get_conn("cold_in")
    cold_out = cycle.network.get_conn("cold_out")
    coolant_exergy_change = cold_in.m.val_SI * (
        cold_out.h.val_SI-cold_in.h.val_SI-temperature*(cold_out.s.val_SI-cold_in.s.val_SI))
    fuel = {"inputs": ["hot_in"], "outputs": ["hot_out"]}
    loss = {}
    if coolant_exergy_change < 0:
        fuel["inputs"].append("cold_in")
        fuel["outputs"].append("cold_out")
    else:
        loss = {"inputs": ["cold_out"], "outputs": ["cold_in"]}
    return analyze_physical_exergy(cycle.network,
        environment_temperature_k=temperature,
        environment_pressure_pa=environment_pressure_pa,
        fuel=fuel,
        product={"inputs": ["shaft_out"], "outputs": ["shaft_in"]},
        loss=loss)
