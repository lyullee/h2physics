"""Small caller-property example for the spatial counterflow exchanger."""

from dataclasses import dataclass

from h2physics.adapters.counterflow_heat_exchanger import (
    CounterflowBoundary,
    CounterflowDefinition,
    CounterflowDomain,
    CounterflowHeatExchanger,
)


@dataclass(frozen=True)
class IdealCaloricState:
    pressure_pa: float
    enthalpy_j_kg: float
    temperature_k: float


def constant_cp_factory(cp_j_kg_k):
    def state_ph(pressure_pa_absolute, enthalpy_j_kg):
        return IdealCaloricState(
            pressure_pa_absolute,
            enthalpy_j_kg,
            enthalpy_j_kg / cp_j_kg_k,
        )

    return state_ph


def build(cell_count=8):
    definition = CounterflowDefinition(
        "hx-demo",
        "warm-hydrogen",
        "cold-hydrogen",
        (100.0 / cell_count,) * cell_count,
        "authored-total-UA-100-W-K",
        "uniform-area-coordinate",
    )
    domain = CounterflowDomain(15.0, 500.0, 15_000.0, 7_000_000.0, "ideal-cp-demo-domain")
    owner = CounterflowHeatExchanger(
        definition,
        hot_state_ph=constant_cp_factory(14_000.0),
        cold_state_ph=constant_cp_factory(12_000.0),
        domain=domain,
    )
    boundary = CounterflowBoundary(
        0.10,
        0.12,
        14_000.0 * 300.0,
        12_000.0 * 80.0,
        (2.0e6,) * (cell_count + 1),
        (1.0e6,) * (cell_count + 1),
        "authored-steady-boundary",
    )
    return owner, boundary


if __name__ == "__main__":
    exchanger, inlet = build()
    result = exchanger.solve(inlet)
    print(result.hot_temperature_k[-1], result.cold_temperature_k[0])

