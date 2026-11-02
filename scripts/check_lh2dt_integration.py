"""Exercise real native objects and a tank without a service or serialization layer."""

import hashlib
import importlib.metadata
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/native_packages"
if not target.exists():
    raise SystemExit("Install the pinned native package into artifacts/native_packages first")
sys.path.insert(0, str(target))

from lh2dt import HomogeneousTank, HydrogenProperties, TankGeometry
from lh2dt.properties import ThermoState as NativeState
from lh2dt.streams import MassEnergyFlow

from h2physics.adapters import Lh2dtProperties, to_lh2dt_flow, to_lh2dt_state
from h2physics.core import Stream
from h2physics.thermo import CoolPropProperties

direct = CoolPropProperties("ParaHydrogen")
native = HydrogenProperties("ParaHydrogen")
adapter = Lh2dtProperties(native, reference_id=direct.basis.reference_id)
largest_relative_difference = 0.
for pressure, temperature in ((150e3, 22.), (5e6, 300.), (1e5, 300.)):
    expected = direct.state_pt(pressure, temperature)
    actual = adapter.state_pt(pressure, temperature)
    for name in ("density_kg_m3", "enthalpy_j_kg", "internal_energy_j_kg", "entropy_j_kg_k"):
        difference = abs(getattr(actual, name) - getattr(expected, name)) / abs(getattr(expected, name))
        largest_relative_difference = max(largest_relative_difference, difference)
        assert difference < 1e-8
    mapped = to_lh2dt_state(expected, expected_basis=adapter.basis, factory=NativeState)
    assert isinstance(mapped, NativeState)

source = direct.saturated(150e3, 0.)
flow = to_lh2dt_flow(Stream("external-supply", "out", .001, source),
                     expected_basis=adapter.basis, factory=MassEnergyFlow)
tank = HomogeneousTank(TankGeometry(1., 1e5, .01, .01), native)
initial = tank.initialize_saturated(150e3, .5, wall_temperature_K=source.temperature_k)
trace = tank.simulate(initial, duration_s=10., time_step_s=1.,
                      ambient_temperature_K=source.temperature_k,
                      flow_callback=lambda _time, _state: [flow])
mass_difference = trace[-1].state.hydrogen_mass_kg - initial.hydrogen_mass_kg
assert abs(mass_difference - .01) < 1e-10
energy_residual = max(abs(row.total_energy_residual_J) for row in trace)
assert energy_residual < 1e-3
version = importlib.metadata.version("lh2dt_models")
source_hash = hashlib.sha256()
for file in sorted((target / "lh2dt").glob("*.py")):
    source_hash.update(file.name.encode())
    source_hash.update(file.read_bytes())
text = (f'package = "lh2dt_models"\nversion = "{version}"\n'
        f'source_revision = "b2f276333c1b1793c39f25763703d196d36742ec"\n'
        f'python_source_sha256 = "{source_hash.hexdigest()}"\n'
        f'maximum_relative_property_difference = {largest_relative_difference!r}\n'
        f'tank_boundary_mass_kg = {mass_difference!r}\n'
        f'maximum_tank_energy_residual_j = {energy_residual!r}\n'
        'scope = "native object conversion and synthetic tank boundary verification"\n'
        'experimental_validation = false\n')
(root / "research/native_lh2dt.toml").write_text(text, encoding="utf-8")
print(text)
