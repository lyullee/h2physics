"""Verify the shared nozzle, accepted source samples and actual native tank depletion."""

import hashlib
import importlib.metadata
import sys
from pathlib import Path

import numpy as np

from h2physics.adapters.lh2dt import Lh2dtBulkNozzleOutflow, Lh2dtProperties
from h2physics.release import (
    HomogeneousIsentropicNozzle,
    NozzleOpening,
    SourceHistory,
    SourceLocation,
)
from h2physics.thermo import CoolPropProperties

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/native_packages"
if not target.exists():
    raise SystemExit("Install the pinned LH2DT package into artifacts/native_packages first")
sys.path.insert(0, str(target))
# Imports are deliberately after the isolated native-package selection.
from lh2dt import HomogeneousTank, HydrogenProperties, TankGeometry, TankState  # noqa: E402
from lh2dt.streams import MassEnergyFlow  # noqa: E402

native_hash = hashlib.sha256()
for file in sorted((target / "lh2dt").glob("*.py")):
    native_hash.update(file.name.encode())
    native_hash.update(file.read_bytes())
expected_native_hash = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"
if native_hash.hexdigest() != expected_native_hash:
    raise SystemExit("Native source differs from the reviewed snapshot; review and repin explicitly")

direct = CoolPropProperties("ParaHydrogen")
native = HydrogenProperties("ParaHydrogen")
provider = Lh2dtProperties(native, reference_id=direct.basis.reference_id)
nozzle = HomogeneousIsentropicNozzle(provider)
rows = []
convergence = []
for case in ("warm_gas", "equilibrium_cryo_bulk"):
    tank = HomogeneousTank(TankGeometry(.1, 2e4, .05, .2), native)
    if case == "warm_gas":
        state = direct.state_pt(5e6, 300.)
        mass = state.density_kg_m3 * .1
        initial = TankState(mass, mass * state.internal_energy_j_kg, state.temperature_k)
        diameter, duration = .001, 5.
    else:
        initial = tank.initialize_saturated(5e5, .5)
        diameter, duration = .002, 2.
    initial_thermo = tank.thermo(initial)
    opening = NozzleOpening.circular(case, diameter, effective_area_factor=.8,
                                      area_basis_id="synthetic-effective-area-closure")
    callback = Lh2dtBulkNozzleOutflow(nozzle, opening, back_pressure_pa=101325.,
                                    opening_fraction=1., flow_factory=MassEnergyFlow)
    initial_sample = callback.sample(0., initial_thermo)
    for dt in (.5, .25, .125):
        trace = tank.simulate(initial, duration_s=duration, time_step_s=dt,
                              ambient_temperature_K=initial_thermo.temperature_K,
                              flow_callback=callback)
        times = (0., *(row.time_s for row in trace))
        samples = (initial_sample, *(callback.sample(row.time_s, row.thermo) for row in trace))
        history = SourceHistory(SourceLocation(f"tank/{case}", "synthetic-time-zero", "local-ENU",
                                               (0., 0., 1.), (1., 0., 0.)),
                                 times, samples, "window_end")
        final = trace[-1]
        loss = initial.hydrogen_mass_kg - final.state.hydrogen_mass_kg
        node_quadrature = float(np.trapezoid([s.mass_flow_kg_s for s in samples], times))
        quadrature_error = abs(node_quadrature - loss)
        mass_residual = loss + final.cumulative_boundary_mass_kg
        energy_residual = max(abs(row.total_energy_residual_J) for row in trace)
        source_energy_residual = max(abs(s.energy_residual_w) for s in samples)
        assert loss > 0 and loss < initial.hydrogen_mass_kg
        assert final.thermo.pressure_Pa < initial_thermo.pressure_Pa
        assert abs(mass_residual) < 1e-12
        assert energy_residual < 1e-5
        assert source_energy_residual < 1e-7
        assert history.mass_flow_series().values.shape == (len(times), 1)
        rows.append((case, dt, loss, final.thermo.pressure_Pa, quadrature_error,
                     mass_residual, energy_residual, source_energy_residual))
        print(f"verified {case}, dt={dt:g} s, released={loss:.12g} kg", flush=True)
        if dt == .125:
            convergence.append((case, initial_sample, samples[-1], initial, final))
    errors = [row[4] for row in rows if row[0] == case]
    assert errors[0] > errors[1] > errors[2]
    assert errors[0] / errors[1] > 3.5 and errors[1] / errors[2] > 3.5

# A discontinuous command is handled by separate native integration windows.
# The flowing window includes its left-limit end; the next window is closed throughout.
case, start_source, last_source, initial, final = convergence[0]
isolated = Lh2dtBulkNozzleOutflow(nozzle, start_source.opening, back_pressure_pa=101325.,
                                opening_fraction=0., flow_factory=MassEnergyFlow)
tank = HomogeneousTank(TankGeometry(.1, 2e4, .05, .2), native)
post_isolation = tank.simulate(final.state, duration_s=1., time_step_s=.25,
                               ambient_temperature_K=300., flow_callback=isolated)
assert post_isolation[-1].state.hydrogen_mass_kg == final.state.hydrogen_mass_kg
assert all(row.cumulative_boundary_mass_kg == 0 for row in post_isolation)
closed_sample = isolated.sample(5., final.thermo)
SourceHistory(SourceLocation("tank/isolated", "synthetic-time-zero", "local-ENU",
                             (0., 0., 1.), (1., 0., 0.)), (5.,), (closed_sample,), "isolation")

# These are numerical checks of a synthetic bulk outlet, not independent flow experiments.
text = ["# Native tank / shared nozzle verification", "",
        "Run `python scripts/check_release_integration.py` after installing the pinned optional native engine.",
        f"Native package: lh2dt_models {importlib.metadata.version('lh2dt_models')}; "
        "revision `b2f276333c1b1793c39f25763703d196d36742ec`.",
        f"Native Python-source SHA-256: `{native_hash.hexdigest()}`.",
        f"CoolProp {direct.version} HEOS ParaHydrogen; the exact reference identity is retained in native mapping.",
        "", "Both cases use a rigid 0.1 m³ reservoir, wall capacity 20000 J/K, ambient UA 0.05 W/K, "
        "fluid/wall UA 0.2 W/K and ambient/initial wall at initial fluid temperature. "
        "The gas starts at 5 MPa, 300 K (1 mm opening, 5 s); the cryogenic case starts at "
        "0.5 MPa with half the vessel volume liquid (2 mm opening, 2 s). "
        "Back pressure is 101325 Pa and the declared effective-area factor is 0.8.",
        "", "| Case | Step s | Released kg | Final P Pa | Node trapezoid error kg | "
        "Tank mass residual kg | Tank energy residual J | Nozzle energy residual W |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
for values in rows:
    text.append("| " + " | ".join([values[0], *(f"{v:.12g}" for v in values[1:])]) + " |")
text.extend(["", "The native RK4 boundary ledger closes; accepted-node trapezoid quadrature "
             "is a separate, lower-order check and its errors decrease approximately fourfold "
             "on halving the step. This does not establish independent physical validation.",
             "", "| Case | Initial flow kg/s | Final flow kg/s | Initial nozzle P Pa | "
             "Final nozzle P Pa | Initial nozzle quality | Final nozzle quality |",
             "|---|---:|---:|---:|---:|---:|---:|"])
for case, first, last, _, _ in convergence:
    text.append(f"| {case} | {first.mass_flow_kg_s:.12g} | {last.mass_flow_kg_s:.12g} | "
                f"{first.exit_state.pressure_pa:.12g} | {last.exit_state.pressure_pa:.12g} | "
                f"{first.exit_state.vapor_mass_fraction} | {last.exit_state.vapor_mass_fraction} |")
text.extend(["", "Nozzle static enthalpy plus kinetic energy equals upstream stagnation enthalpy. "
             "Nozzle quality is not a ground-transfer fraction. Native LH2DT only supports bulk "
             "withdrawal in this check; phase-selective extraction remains request 001.",
             "", "Isolation is verified by separate integration windows; the subsequent window "
             "has zero boundary mass throughout. RK stage/retry calls are never logged as accepted "
             "source times. The demonstration does not interpolate a jump or supply an atmospheric jet.",
             "", "Source hashes (SHA-256):", ""])
for relative in ("src/h2physics/release.py", "src/h2physics/adapters/lh2dt.py",
                 "scripts/check_release_integration.py"):
    text.append(f"- `{relative}`: `{hashlib.sha256((root / relative).read_bytes()).hexdigest()}`")
(root / "research/native_release.md").write_text("\n".join(text) + "\n", encoding="utf-8", newline="\n")
print("\n".join(text[:17]))
