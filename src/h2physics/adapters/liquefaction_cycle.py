"""Actual TESPy hydrogen compressor/cold-utility/JT/separator topology.

CoolProp supplies all pure-fluid states. The external cryogenic utility is a
declared finite stream, not a solved refrigerator or an inferred electric load.
Native TESPy component contracts: https://tespy.readthedocs.io/en/stable/ .
"""

from dataclasses import dataclass
from importlib.metadata import version

from ..core import finite


@dataclass(frozen=True, slots=True)
class HydrogenLiquefactionSpec:
    compressor_isentropic_efficiency: float
    source_id: str
    hydrogen_fluid: str = "Hydrogen"
    feed_mass_flow_kg_s: float = 0.01
    feed_temperature_k: float = 300.0
    feed_pressure_pa_absolute: float = 101325.0
    compression_pressure_pa_absolute: float = 5_000_000.0
    precooler_outlet_temperature_k: float = 28.0
    separator_pressure_pa_absolute: float = 101325.0
    utility_fluid: str = "Helium"
    utility_inlet_temperature_k: float = 15.0
    utility_outlet_temperature_k: float = 250.0
    utility_pressure_pa_absolute: float = 200000.0
    utility_pressure_ratio: float = 1.0
    hydrogen_cooler_pressure_ratio: float = 1.0
    precooler_sections: int = 128

    def __post_init__(self):
        if self.hydrogen_fluid not in {"Hydrogen", "ParaHydrogen"}:
            raise ValueError("Select native Hydrogen or ParaHydrogen with a fixed spin convention")
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("Identify design inputs and compressor-efficiency evidence")
        if not isinstance(self.utility_fluid, str) or not self.utility_fluid.strip():
            raise ValueError("Declare the native pure cold-utility fluid")
        for name in self.__dataclass_fields__:
            if name not in {"source_id", "hydrogen_fluid", "utility_fluid", "precooler_sections"}:
                finite(getattr(self, name), name, positive=True)
        if type(self.precooler_sections) is not int or self.precooler_sections < 2:
            raise ValueError("At least two native precooler sections are required")
        for name in ("compressor_isentropic_efficiency", "utility_pressure_ratio",
                     "hydrogen_cooler_pressure_ratio"):
            if getattr(self, name) > 1:
                raise ValueError("Efficiency and pressure ratios must not exceed one")
        if self.compression_pressure_pa_absolute <= self.feed_pressure_pa_absolute:
            raise ValueError("Compressor outlet pressure must exceed feed pressure")
        if self.compression_pressure_pa_absolute * self.hydrogen_cooler_pressure_ratio <= (
                self.separator_pressure_pa_absolute):
            raise ValueError("JT expansion requires a positive pressure decrease")
        if not self.utility_inlet_temperature_k < self.precooler_outlet_temperature_k:
            raise ValueError("Cold utility must enter below the hydrogen cooler outlet temperature")
        if self.utility_outlet_temperature_k <= self.utility_inlet_temperature_k:
            raise ValueError("Cold utility must warm as it absorbs heat")


class NoTwoPhaseLiquefactionError(ValueError):
    """Native JT feed cannot be represented by a two-product phase separator."""

    def __init__(self, inlet_enthalpy_j_kg, saturated_liquid_enthalpy_j_kg,
                 saturated_vapor_enthalpy_j_kg):
        self.inlet_enthalpy_j_kg = inlet_enthalpy_j_kg
        self.saturated_liquid_enthalpy_j_kg = saturated_liquid_enthalpy_j_kg
        self.saturated_vapor_enthalpy_j_kg = saturated_vapor_enthalpy_j_kg
        super().__init__("Native JT outlet is outside the two-phase separator domain; "
                         "no liquid/vapor yield is invented or clipped")


@dataclass(frozen=True, slots=True)
class LiquefactionCycleAudit:
    liquid_mass_flow_kg_s: float
    vapor_mass_flow_kg_s: float
    liquid_mass_fraction: float
    compressor_shaft_input_w: float
    external_cold_utility_heat_absorbed_w: float
    cold_utility_mass_flow_kg_s: float
    hydrogen_first_law_residual_w: float
    utility_heat_balance_residual_w: float
    separator_mass_residual_kg_s: float
    separator_energy_residual_w: float
    jt_enthalpy_residual_j_kg: float
    precooler_sampled_minimum_approach_k: float
    precooler_sections: int
    tespy_version: str
    coolprop_version: str


@dataclass(frozen=True, slots=True)
class SolvedHydrogenLiquefactionCycle:
    network: object
    spec: HydrogenLiquefactionSpec
    audit: LiquefactionCycleAudit


def solve_hydrogen_liquefaction(spec: HydrogenLiquefactionSpec) -> SolvedHydrogenLiquefactionCycle:
    """Solve a single-pass externally precooled H2 liquefaction process.

    No vapor recycle, recuperation, ortho/para conversion, finite tank cooldown,
    refrigerant compressor or cold-box electricity is implied. The saturated
    products and every connection remain actual TESPy/CoolProp results.
    """
    from CoolProp.CoolProp import PhaseSI, PropsSI
    from tespy.components import (
        Compressor,
        DropletSeparator,
        PowerSource,
        SectionedHeatExchanger,
        Sink,
        Source,
        Valve,
    )
    from tespy.connections import Connection, PowerConnection
    from tespy.networks import Network

    if not isinstance(spec, HydrogenLiquefactionSpec):
        raise TypeError("Supply HydrogenLiquefactionSpec")
    if PhaseSI("P", spec.feed_pressure_pa_absolute, "T", spec.feed_temperature_k,
                spec.hydrogen_fluid) not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError("The compressor topology requires a single-gas hydrogen feed")
    # Reject single-phase inlet to the mandatory native two-product separator
    # before a mathematically converged network can invent a negative product.
    h_pre = PropsSI("Hmass", "P", spec.compression_pressure_pa_absolute *
                     spec.hydrogen_cooler_pressure_ratio,
                     "T", spec.precooler_outlet_temperature_k, spec.hydrogen_fluid)
    h_liq = PropsSI("Hmass", "P", spec.separator_pressure_pa_absolute, "Q", 0,
                    spec.hydrogen_fluid)
    h_vap = PropsSI("Hmass", "P", spec.separator_pressure_pa_absolute, "Q", 1,
                    spec.hydrogen_fluid)
    if not h_liq < h_pre < h_vap:
        raise NoTwoPhaseLiquefactionError(h_pre, h_liq, h_vap)
    nw = Network(iterinfo=False)
    nw.units.set_defaults(temperature="K", pressure="Pa", pressure_difference="Pa",
                          enthalpy="J/kg", power="W", heat="W", mass_flow="kg/s")
    compressor, cooler, valve, separator = (Compressor("hydrogen_compressor"),
        SectionedHeatExchanger("external_cryogenic_precooler"), Valve("jt_valve"),
        DropletSeparator("hydrogen_phase_separator"))
    feed = Connection(Source("hydrogen_feed"), "out1", compressor, "in1", label="h2_feed")
    compressed = Connection(compressor, "out1", cooler, "in1", label="h2_compressed")
    precooled = Connection(cooler, "out1", valve, "in1", label="h2_precooled")
    expanded = Connection(valve, "out1", separator, "in1", label="h2_jt_outlet")
    liquid = Connection(separator, "out1", Sink("liquid_product"), "in1", label="h2_liquid")
    vapor = Connection(separator, "out2", Sink("vapor_product"), "in1", label="h2_vapor")
    cold_in = Connection(Source("external_cold_supply"), "out1", cooler, "in2", label="cold_in")
    cold_out = Connection(cooler, "out2", Sink("external_cold_return"), "in1", label="cold_out")
    shaft = PowerConnection(PowerSource("compressor_drive"), "power", compressor,
                             "power", label="compressor_shaft")
    nw.add_conns(feed, compressed, precooled, expanded, liquid, vapor, cold_in, cold_out, shaft)
    compressor.set_attr(eta_s=spec.compressor_isentropic_efficiency)
    cooler.set_attr(pr1=spec.hydrogen_cooler_pressure_ratio, pr2=spec.utility_pressure_ratio,
                    num_sections=spec.precooler_sections)
    feed.set_attr(m=spec.feed_mass_flow_kg_s, p=spec.feed_pressure_pa_absolute,
                  T=spec.feed_temperature_k, fluid={spec.hydrogen_fluid: 1.0})
    compressed.set_attr(p=spec.compression_pressure_pa_absolute)
    precooled.set_attr(T=spec.precooler_outlet_temperature_k)
    expanded.set_attr(p=spec.separator_pressure_pa_absolute)
    cold_in.set_attr(p=spec.utility_pressure_pa_absolute, T=spec.utility_inlet_temperature_k,
                     fluid={spec.utility_fluid: 1.0})
    cold_out.set_attr(T=spec.utility_outlet_temperature_k)
    nw.solve("design", print_results=False)
    nw.assert_convergence()
    if min(cooler.ttd_u.val_SI, cooler.ttd_l.val_SI) <= 0:
        raise ValueError("Solved precooler has a crossing terminal temperature")
    minimum_approach = finite(cooler.td_pinch.val_SI, "native sampled precooler pinch")
    if minimum_approach <= 0:
        raise ValueError("Solved precooler has an internal temperature crossing on its native section grid")
    ml = finite(liquid.m.val_SI, "liquid product flow", positive=True)
    mv = finite(vapor.m.val_SI, "vapor product flow", positive=True)
    work = finite(compressor.P.val_SI, "compressor shaft input", positive=True)
    cold_heat = finite(-cooler.Q.val_SI, "external cold duty", positive=True)
    cm = finite(cold_in.m.val_SI, "cold-utility flow", positive=True)
    def hdot(connection):
        return connection.m.val_SI * connection.h.val_SI
    separator_mass = expanded.m.val_SI - ml - mv
    separator_energy = hdot(expanded) - hdot(liquid) - hdot(vapor)
    first_law = hdot(feed) + work - cold_heat - hdot(liquid) - hdot(vapor)
    utility_energy = cold_heat - cm * (cold_out.h.val_SI - cold_in.h.val_SI)
    jt_residual = precooled.h.val_SI - expanded.h.val_SI
    for residual in (separator_energy, first_law, utility_energy):
        if abs(residual) > 1e-6 * max(cold_heat, work, 1.):
            raise ValueError("Native liquefaction process fails its component/first-law balance")
    if abs(separator_mass) > 1e-10 * spec.feed_mass_flow_kg_s + 1e-12:
        raise ValueError("Native phase separator fails mass balance")
    if abs(jt_residual) > 1e-7 * max(abs(precooled.h.val_SI), 1.):
        raise ValueError("Native JT valve fails its isenthalpic balance")
    audit = LiquefactionCycleAudit(ml, mv, ml/spec.feed_mass_flow_kg_s, work, cold_heat,
        cm, first_law, utility_energy, separator_mass, separator_energy, jt_residual,
        minimum_approach, spec.precooler_sections, version("tespy"), version("CoolProp"))
    return SolvedHydrogenLiquefactionCycle(nw, spec, audit)


def analyze_liquefaction_exergy(cycle: SolvedHydrogenLiquefactionCycle, *,
                                environment_temperature_k=298.15,
                                environment_pressure_pa=101325.0):
    """Native physical-exergy balance including the consumed cold utility.

    Fuel comprises compressor shaft work, feed physical exergy and the cold
    stream's exergy decrease. Both separated hydrogen streams are material
    products of this open single-pass boundary. This is not a plant SEC/COP.
    """
    from .thermal_cycles import analyze_physical_exergy

    if not isinstance(cycle, SolvedHydrogenLiquefactionCycle):
        raise TypeError("Supply SolvedHydrogenLiquefactionCycle")
    temperature = finite(environment_temperature_k, "environment temperature", positive=True)
    cold_in, cold_out = (cycle.network.get_conn(name) for name in ("cold_in", "cold_out"))
    consumed = cold_in.m.val_SI * (cold_in.h.val_SI - cold_out.h.val_SI -
                                  temperature * (cold_in.s.val_SI - cold_out.s.val_SI))
    if consumed <= 0:
        raise ValueError("Selected cold-utility boundary does not consume physical exergy")
    return analyze_physical_exergy(cycle.network, environment_temperature_k=temperature,
        environment_pressure_pa=environment_pressure_pa,
        fuel={"inputs": ["compressor_shaft", "h2_feed", "cold_in"], "outputs": ["cold_out"]},
        product={"inputs": ["h2_liquid", "h2_vapor"]})
