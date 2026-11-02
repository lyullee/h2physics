"""Reproduce finite native open-volume inventory, energy and refinement checks."""

import argparse
import hashlib
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_volume import (
    CanteraOpenGasVolume,
    GasBoundaryRate,
    GasFeed,
    GasHeatBoundary,
    GasVent,
)
from h2physics.core import Origin


def main():
    import cantera as ct

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--energy-ledger-scale-j", type=float, default=1e6,
                        help="J per native appended energy unit; 1 reproduces the unscaled case")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    inputs = ("src/h2physics/adapters/cantera_volume.py", "scripts/check_cantera_volume.py",
              "tests/test_cantera_volume.py")
    fingerprints = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}
    raw = (Path(ct.__file__).parent/"data/h2o2.yaml").read_bytes()
    mechanism_hash = hashlib.sha256(raw).hexdigest()
    basis = MechanismBasis(f"Cantera:{ct.__version__}:h2o2:H2-N2-frozen-subset",
        mechanism_hash, "Cantera-BSD-3-Clause; upstream GRI-Mech species provenance",
        ("https://cantera.org/3.2/examples/input/h2o2.html",
         "https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html"),
        310., 1200., 2e4, 5e5)

    def factory():
        # Python reads installed data because the native Windows path does not
        # preserve this user's Unicode directory. No mechanism is copied here.
        donor = ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
        return ct.Solution(thermo="ideal-gas", kinetics=None,
                           species=[donor.species("H2"), donor.species("N2")])

    provider = CanteraOpenGasVolume(factory, basis)
    initial = ReactiveState(400., 101325., {"N2": 1.})
    inlet = ReactiveState(420., 101325., {"H2": 1.})
    sink = ReactiveState(400., 101325., {"N2": 1.})
    environment = ReactiveState(450., 101325., {"N2": 1.})
    times = np.linspace(100., 101., 1001)

    def rate(name, callback):
        return GasBoundaryRate(name, "authored-operation-clock", 100., 102., callback,
                               Origin.SYNTHETIC, "original-positive-verification-case")

    feed = GasFeed(rate("H2-feed", lambda t, phase: .001*(1+.5*(t-100.))), inlet)
    vent = GasVent(rate("extraction", lambda t, phase: .0004), sink)
    wall = GasHeatBoundary("external-wall", "authored-operation-clock", 100., 102.,
        environment, 1., 2., heat_flux_w_m2=lambda t: 5.*np.cos(t-100.))

    def solve(step, *, feeds=(), vents=(), heat=()):
        return provider.run(initial, times, volume_m3=.5,
            clock_id="authored-operation-clock", feeds=feeds, vents=vents,
            heat_boundaries=heat, maximum_time_step_s=step, relative_tolerance=1e-11,
            absolute_tolerance=1e-15, energy_ledger_scale_j=args.energy_ledger_scale_j)

    calculation_start = perf_counter()
    sealed_feed = solve(.01, feeds=(feed,))
    first, final_feed = sealed_feed.snapshots[0], sealed_feed.snapshots[-1]
    inflow = .00125  # Independent integral of the authored linear-time rate.
    native = factory()
    native.TPX = inlet.temperature_k, inlet.pressure_pa, dict(inlet.mole_fractions)
    hin = native.enthalpy_mass
    expected_mass = first.mass_kg+inflow
    expected_energy = first.internal_energy_j+inflow*hin
    native.UVY = expected_energy/expected_mass, .5/expected_mass, {
        "H2": inflow/expected_mass, "N2": first.mass_kg/expected_mass}
    feed_temperature_error = final_feed.temperature_k-native.T
    feed_pressure_error = final_feed.pressure_pa-native.P

    sealed_vent = solve(.01, vents=(vent,))
    final_vent = sealed_vent.snapshots[-1]
    native.TPX = first.temperature_k, first.pressure_pa, {"N2": 1.}
    entropy = native.entropy_mass
    expected_vent_mass = first.mass_kg-.0004
    native.SV = entropy, .5/expected_vent_mass
    vent_temperature_error = final_vent.temperature_k-native.T
    vent_pressure_error = final_vent.pressure_pa-native.P

    coarse = solve(.02, feeds=(feed,), vents=(vent,), heat=(wall,))
    fine = solve(.005, feeds=(feed,), vents=(vent,), heat=(wall,))
    calculation_elapsed_s = perf_counter()-calculation_start
    last = fine.snapshots[-1]
    temperatures = np.array([s.temperature_k for s in fine.snapshots])
    h_out = np.array([s.specific_enthalpy_j_kg for s in fine.snapshots])
    sampled_wall = np.trapezoid(2.*(450.-temperatures)+5.*np.cos(times-100.), times)
    sampled_outlet_energy = np.trapezoid(.0004*h_out, times)
    heat_quadrature_error = sampled_wall-fine.integral("wall:heat")[-1]
    outlet_quadrature_error = sampled_outlet_energy-fine.integral("outlet:enthalpy")[-1]
    mass_input_error = fine.integral("inlet:H2-feed:mass")[-1]-inflow
    final_mass_error = last.mass_kg-(first.mass_kg+inflow-.0004)
    final_state_difference = max(abs(coarse.snapshots[-1].temperature_k-last.temperature_k),
        abs(coarse.snapshots[-1].pressure_pa-last.pressure_pa)/1000.)
    all_runs = (sealed_feed, sealed_vent, coarse, fine)
    max_mass = max(float(np.max(abs(r.mass_residual_kg))) for r in all_runs)
    max_species = max(float(np.max(abs(r.species_residual_kg))) for r in all_runs)
    max_energy = max(float(np.max(abs(r.energy_residual_j))) for r in all_runs)
    gates = {
        "native nonreacting finite volume and original objects retained": all(
            isinstance(r.native.reactor, ct.ExtensibleIdealGasReactor)
            and isinstance(r.native.network, ct.ReactorNet)
            and r.native.reactor.phase.n_reactions == 0
            and not r.native.reactor.chemistry_enabled for r in all_runs),
        "independent linear source integral <1e-11 kg": abs(mass_input_error) < 1e-11,
        "independent final mass <1e-10 kg": abs(final_mass_error) < 1e-10,
        "native integrated mass and species residuals <1e-10 kg": max(max_mass, max_species) < 1e-10,
        "native integrated energy residual <0.001 J": max_energy < .001,
        "sealed feed independent native UVY T <1e-6 K and P <0.001 Pa":
            abs(feed_temperature_error) < 1e-6 and abs(feed_pressure_error) < .001,
        "adiabatic vent independent native SV T <1e-6 K and P <0.001 Pa":
            abs(vent_temperature_error) < 1e-6 and abs(vent_pressure_error) < .001,
        "independent sampled wall and outlet integrals <0.0001 J":
            max(abs(heat_quadrature_error), abs(outlet_quadrature_error)) < .0001,
        "0.02/0.005 s final T and P/1000 agreement <1e-6": final_state_difference < 1e-6,
        "actual absolute native clock preserved inside declared support": all(
            r.evaluated_clock_bounds_s[0] == 100.
            and r.evaluated_clock_bounds_s[1] <= 102. for r in all_runs),
        "source hashes unchanged during computation": all(
            hashlib.sha256((root/name).read_bytes()).hexdigest() == sha
            for name, sha in fingerprints.items()),
    }
    lines = ["# Native open gas volume verification", "",
        "Reproduce: `python scripts/check_cantera_volume.py` with the optional chemistry extra.", "",
        f"Native engine: Cantera {ct.__version__}; actual ExtensibleIdealGasReactor / ReactorNet / "
        "Reservoir / MassFlowController / Wall objects. No mechanism, raw experiment or native source is bundled.", "",
        "The original synthetic case starts at absolute t=100 s: 0.5 m³ N2, 400 K, 101325 Pa; "
        "H2 feed 420 K with 0.001[1+0.5(t-100)] kg/s; fixed extraction 0.0004 kg/s. "
        "The wall has A=1 m², U=2 W/(m² K), Tenv=450 K and signed prescribed flux 5 cos(t-100) W/m². "
        "Output ends at 101 s; authored callbacks explicitly support [100,102] s, including native trial times.", "",
        "Only native boundary-integral rows are appended. Physical temperature, mass, volume and species equations "
        "and CVODES integration remain native. The ledgers are integrated numerical estimates, not exact quadrature.", "",
        "The pure-vent check uses native SV conservation independently of the physical integration. "
        "The feed-only check uses an independent authored source integral and native UVY inversion. "
        "Constant-cp analytic feed, vent, mixing and wall limits are additional unit tests.", "",
        f"Each appended energy integral uses {args.energy_ledger_scale_j:g} J per native state unit; "
        "returned integrals and residuals remain SI J. Mass/species ledgers remain kg. "
        "Native physical rows, rtol/atol and every conservation/analytic acceptance budget are unchanged. "
        "Use `--energy-ledger-scale-j 1` to retain the original unscaled numerical reference. "
        "That reference can emit native initial `t+h=t` step-roundoff warnings at the absolute 100 s start; "
        "no warnings, clocks, solvers or energy references are suppressed or reset. "
        "The constant-feed test compares scaled/unscaled states and SI integrals against the same budgets. "
        "Measured before/after timings and warnings are in docs/OPEN_GAS_VOLUME.md.", "",
        "| Quantity | Observed value |", "|---|---:|",
        f"| Independently integrated source mass | {inflow:.12g} kg |",
        f"| Coupled final mass | {last.mass_kg:.12g} kg |",
        f"| Coupled final T / P | {last.temperature_k:.12g} K / {last.pressure_pa:.12g} Pa |",
        f"| Coupled final H2 mass / mole fraction | {last.mass_fractions['H2']:.12g} / "
        f"{last.mole_fractions['H2']:.12g} |",
        f"| Maximum mass / species residual | {max_mass:.12g} / {max_species:.12g} kg |",
        f"| Maximum energy residual | {max_energy:.12g} J |",
        f"| Feed-only independent native T / P error | {feed_temperature_error:.12g} K / "
        f"{feed_pressure_error:.12g} Pa |",
        f"| Vent-only independent native T / P error | {vent_temperature_error:.12g} K / "
        f"{vent_pressure_error:.12g} Pa |",
        f"| Independent sampled wall integral difference | {heat_quadrature_error:.12g} J |",
        f"| Independent sampled outlet integral difference | {outlet_quadrature_error:.12g} J |",
        f"| Coarse/fine final max(T, P/1000) difference | {final_state_difference:.12g} |",
        f"| Fine actual callback clock bounds | {fine.evaluated_clock_bounds_s} s |", "",
        f"Four-run native replay plus independent native inversions: {calculation_elapsed_s:.6g} s "
        "wall time on this run; timings are workload-sensitive.", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "These are software and numerical verification results. The well-mixed thermodynamic volume does not "
        "predict spatial concentration, stratification, ignition, explosion or outdoor dispersion. "
        "HyRAM+ remains the preferred high-pressure gaseous-hydrogen dispersion provider and SLABx-LH2 "
        "the preferred LH2-origin provider. No measured ventilation pressure/flow clocks have been inferred or aligned. "
        "The current H2 thermochemistry is mechanism-specific and spin-unresolved, with native formation-energy reference; "
        "there is no automatic CoolProp/normal/para energy conversion.", "",
        "Feed reservoir thermo is fixed within one run. Finite upstream supply, bidirectional ports, discontinuous "
        "commands, exact depletion/event localization, source-state changes and wall storage remain future work. "
        "Callbacks may delegate the existing shared nozzle using a separate native frozen-mixture phase; "
        "this reproduction instead declares prescribed extraction and does not claim a solved vent opening.", "",
        "Primary references: [native ideal-gas control volume equations]"
        "(https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html), "
        "[native extension/flow/wall APIs](https://cantera.org/3.2/python/zerodim.html), "
        "[installed mechanism provenance](https://cantera.org/3.2/examples/input/h2o2.html). "
        "Original adapter, cases and tests; separately installed Cantera retains its BSD-3-Clause terms "
        "and upstream species provenance.", "", "## Reproduction fingerprints", "",
        f"- Installed h2o2.yaml SHA-256: `{mechanism_hash}`",
        f"- Native enclosure thermo SHA-256: `{fine.phase_fingerprint}`",
        *(f"- `{name}`: `{sha}`" for name, sha in fingerprints.items()), ""]
    destination = root/"research/open_gas_volume.md"
    destination.write_text("\n".join(lines), encoding="utf-8")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print("Report: research/open_gas_volume.md")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
