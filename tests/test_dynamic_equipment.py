from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt_dynamics import (
    DynamicEquipmentRun,
    DynamicEquipmentStep,
    EquipmentCommandTransition,
    InventoryClosureError,
    Lh2dtDynamicEquipment,
    Lh2dtInventoryNode,
    integrate_equipment_rate,
    lumped_inventory_reader,
    stratified_inventory_reader,
)
from h2physics.adapters.lh2dt_equipment import EquipmentNetworkSnapshot
from h2physics.core import PropertyBasis, ThermoState
from h2physics.dynamics import (
    ConservedInventory,
    InventoryBalance,
    InventoryTolerances,
    ScheduledEquipmentCommand,
)

BASIS = PropertyBasis("authored-fluid", "authored-energy-reference")


def test_inventory_accounts_for_solid_energy_and_reference_changes_do_not_weaken_gates():
    first = ConservedInventory(BASIS, 1., -1e9, 2e9)
    last = replace(first, mass_kg=.9, fluid_internal_energy_j=first.fluid_internal_energy_j-20.,
                   solid_internal_energy_j=first.solid_internal_energy_j+12.)
    balance = InventoryBalance(first, last, -.1, -8., -20., 12.)
    assert not balance.violations(InventoryTolerances())
    assert "inventory energy does not close" in replace(balance, boundary_energy_j=-7.999).violations(InventoryTolerances())
    assert "transport and external heat" in replace(balance, transported_enthalpy_j=-19.).violations(InventoryTolerances())[0]
    with pytest.raises(ValueError, match="bases differ"):
        InventoryBalance(first, replace(last, basis=PropertyBasis("other", "other")), -.1, -8., -20., 12.)


def test_lumped_reader_requires_a_physical_wall_temperature_and_explicit_capacity():
    reader = lumped_inventory_reader(2., BASIS)
    native = SimpleNamespace(mass_kg=3., internal_energy_J=-100., wall_temperature_K=20.)
    assert reader(native).total_energy_j == -60.
    with pytest.raises(ValueError, match="positive"):
        reader(SimpleNamespace(**{**vars(native), "wall_temperature_K": -20.}))
    with pytest.raises(ValueError, match="positive"):
        lumped_inventory_reader(0., BASIS)


@dataclass(frozen=True)
class Node:
    name: str
    initial_state: object
    thermo: object
    derivative: object


class RecordingGraph:
    """Stationary interface test double; no flow law or integration algorithm."""

    def __init__(self, on_solve=None):
        self.boundaries = {"cv": None}
        self.on_solve = on_solve

    def set_boundary_states(self, states):
        self.boundaries.update(states)

    def solve(self):
        states = {name: ThermoState(BASIS, raw.pressure_Pa, 300., 1.,
            raw.specific_enthalpy_J_kg, -1e5, 10., "gas") for name, raw in self.boundaries.items()}
        snapshot = EquipmentNetworkSnapshot(states, (), {}, {}, 0., 0., 0., 0., True, object())
        if self.on_solve:
            self.on_solve(snapshot)
        return snapshot


class RecordingAdapter:
    def __init__(self):
        self.native = RecordingGraph()
        self.bridge = SimpleNamespace(basis=BASIS)
        self.solve_limits = []

    def solve(self, **options):
        self.solve_limits.append(options["max_pressure_nfev"])
        return self.native.solve()

    def checked_native(self, *, on_solve):
        self.native.on_solve = on_solve
        return self.native


def fixture_driver(*, corrupt_identity=False, corrupt_energy=False, declare_heat=True):
    clock = []
    state = SimpleNamespace(mass_kg=1., internal_energy_J=100., wall_temperature_K=20.)

    def derivative(_state, _flows, at):
        clock.append(at)
        return SimpleNamespace(**({"ambient_heat_W": 0.} if declare_heat else {}))

    node = Node("cv", state, lambda _s: SimpleNamespace(pressure_Pa=1e5,
        specific_enthalpy_J_kg=0.), derivative)

    class Simulator:
        def __init__(self, graph, nodes, **options):
            self.graph, self.nodes = graph, nodes

        def simulate(self, duration, width):
            model = self.nodes["cv"]
            model.thermo(model.initial_state)
            model.derivative(model.initial_state, (), 0.)
            model.derivative(model.initial_state, (), duration)
            snapshot = self.graph.solve()
            # One solve only: the accepted identity contract is independent of RK call count.
            return [SimpleNamespace(time_s=duration, states={"cv": model.initial_state},
                network_solution=object() if corrupt_identity else snapshot.native,
                cumulative_boundary_mass_kg={"cv": 0.},
                cumulative_boundary_energy_J={"cv": 1. if corrupt_energy else 0.},
                cumulative_boundary_transport_energy_J={"cv": 0.},
                cumulative_boundary_ambient_heat_J={"cv": 0.})]

    return Lh2dtDynamicEquipment(RecordingAdapter(),
        {"cv": Lh2dtInventoryNode(node, lumped_inventory_reader(2., BASIS))},
        simulator_factory=Simulator), clock


def test_command_boundaries_preserve_absolute_clock_and_accepted_object_identity():
    driver, clock = fixture_driver()
    applied = []
    commands = tuple(ScheduledEquipmentCommand(str(at), at, lambda at, _g: applied.append(at))
                     for at in (10.137, 10.411))
    run = driver.run(1., 1., start_time_s=10., clock_id="operation-A", commands=commands,
                     pressure_solver_max_nfev=17)
    assert driver.network.solve_limits == [17, 17, 17]
    assert applied == [10.137, 10.411]
    assert [row.time_s for row in run.steps] == [10.137, 10.411, 11.]
    assert clock == [10., 10.137, 10.137, 10.411, 10.411, 11.]
    assert run.transitions[0].time_s == 10.137
    assert not any(balance.violations(InventoryTolerances()) for row in run.steps for balance in row.balances.values())
    with pytest.raises(TypeError):
        run.initial_inventories["extra"] = run.initial_inventories["cv"]


@pytest.mark.parametrize(("options", "error", "message"), [
    ({"corrupt_identity": True}, ValueError, "no checked identity"),
    ({"corrupt_energy": True}, InventoryClosureError, "energy does not close"),
    ({"declare_heat": False}, ValueError, "declare external"),
])
def test_native_contract_failures_are_rejected(options, error, message):
    driver, _clock = fixture_driver(**options)
    with pytest.raises(error, match=message):
        driver.run(1., 1., clock_id="operation-A")


def test_commands_cannot_silently_fall_outside_the_window_or_merge_at_unresolved_times():
    driver, _clock = fixture_driver()
    noop = lambda _t, _g: None  # noqa: E731
    with pytest.raises(ValueError, match="outside"):
        driver.run(1., 1., clock_id="operation-A", commands=(ScheduledEquipmentCommand("late", 2., noop),))
    with pytest.raises(ValueError, match="unique"):
        driver.run(1., 1., clock_id="operation-A", commands=(ScheduledEquipmentCommand("same", .1, noop),
            ScheduledEquipmentCommand("same", .2, noop)))
    with pytest.raises(ValueError, match="clock precision"):
        driver.run(1., 1., clock_id="operation-A", commands=(ScheduledEquipmentCommand("tiny", 1e-10, noop),))
    for invalid in (True, 0, -1, 1.5):
        with pytest.raises(ValueError, match="positive integer"):
            driver.run(1., 1., clock_id="operation-A", pressure_solver_max_nfev=invalid)


def test_initial_continuous_control_cannot_bypass_the_conserved_boundary():
    driver, _clock = fixture_driver()

    def replace_boundary(_at, graph):
        graph.set_boundary_states({"cv": SimpleNamespace(pressure_Pa=2e5, specific_enthalpy_J_kg=0.)})

    with pytest.raises(ValueError, match="replaced dynamic inventory"):
        driver.run(1., 1., clock_id="operation-A", continuous_command=replace_boundary)


def test_stratified_inventory_keeps_both_fluid_regions_and_both_walls():
    reader = stratified_inventory_reader(100., 200., BASIS)
    state = SimpleNamespace(liquid_mass_kg=2., vapor_mass_kg=.1,
        liquid_internal_energy_J=-100., vapor_internal_energy_J=-20.,
        lower_wall_temperature_K=20., upper_wall_temperature_K=30.)
    inventory = reader(state)
    assert inventory.mass_kg == 2.1 and inventory.fluid_internal_energy_j == -120.
    assert inventory.solid_internal_energy_j == 8000. and inventory.total_energy_j == 7880.
    with pytest.raises(ValueError, match="positive"):
        reader(SimpleNamespace(**{**vars(state), "vapor_mass_kg": 0.}))


def test_sampled_quadrature_preserves_both_limits_of_a_command_jump():
    # Analytic rate: 2 until t=.37, then 5. These are quadrature inputs, not a flow model.
    template = EquipmentNetworkSnapshot({}, (), {}, {}, 0., 0., 0., 0., True, object())
    before, after = replace(template, boundary_outlet_kg_s=2.), replace(template, boundary_outlet_kg_s=5.)
    rows = tuple(DynamicEquipmentStep(at, {}, {}, snapshot, None)
                 for at, snapshot in ((.2, before), (.37, before), (.6, after), (1., after)))
    run = DynamicEquipmentRun("quadrature-clock", 0., {"cv": ConservedInventory(BASIS, 1., 0., 0.)}, before, rows,
        (EquipmentCommandTransition(.37, ("switch",), before, after),))
    integral = integrate_equipment_rate(run, lambda snapshot: snapshot.boundary_outlet_kg_s,
                                        rate_unit="kg/s", integral_unit="kg")
    assert integral.value == pytest.approx(2.*.37+5.*.63)
    assert integral.clock_id == "quadrature-clock" and integral.interval_count == 4
    assert integral.basis == BASIS
    assert integral.method == "piecewise_linear_trapezoid" and integral.integral_unit == "kg"
    with pytest.raises(ValueError, match="explicit"):
        integrate_equipment_rate(run, lambda snapshot: 1., rate_unit="", integral_unit="kg")
    with pytest.raises(ValueError, match="finite"):
        integrate_equipment_rate(run, lambda snapshot: float("nan"), rate_unit="kg/s", integral_unit="kg")
