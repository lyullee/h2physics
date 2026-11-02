"""Audit native finite gas conversion, boundary/reaction ledgers and definition copies."""

import hashlib
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_volume import (
    CanteraOpenGasVolume,
    GasBoundaryRate,
    GasFeed,
    GasVent,
)
from h2physics.core import Origin


def main():
    import cantera as ct

    root = Path(__file__).resolve().parents[1]
    inputs = ("src/h2physics/adapters/cantera_volume.py", "scripts/check_reactive_process.py",
              "tests/test_reactive_gas_volume.py", "src/h2physics/adapters/cantera.py")
    before = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}
    raw = (Path(ct.__file__).parent/"data/gri30.yaml").read_bytes()
    mechanism_hash = hashlib.sha256(raw).hexdigest()
    basis = MechanismBasis("installed-GRI30-gas-carbon-steam-reference", mechanism_hash,
        "Separately installed Cantera BSD-3-Clause; upstream GRI-Mech provenance retained",
        ("https://cantera.org/3.2/examples/input/gri30.html",
         "https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html"),
        500., 3000., 2e4, 2e6)

    def factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name="gri30")

    initial = ReactiveState(1500., 101325., {"N2": 1.})
    sink = ReactiveState(1500., 101325., {"N2": 1.})
    times = np.linspace(0., .2, 41)

    def phase_at(state):
        phase = factory()
        phase.TPX = state.temperature_k, state.pressure_pa, dict(state.mole_fractions)
        return phase

    def rate(name):
        return GasBoundaryRate(name, "authored-carbon-steam-clock", 0., .5, lambda t: .0001,
            Origin.SYNTHETIC, "authored-throughput-reference", phase_access="time_only")

    def solve(feed_state, step, tolerance):
        return CanteraOpenGasVolume(factory, basis, chemistry="finite_rate").run(initial, times,
            volume_m3=.001, clock_id="authored-carbon-steam-clock",
            feeds=(GasFeed(rate("feed"), feed_state),), vents=(GasVent(rate("outlet"), sink),),
            maximum_time_step_s=step, relative_tolerance=tolerance, absolute_tolerance=1e-15)

    def plain_native_reference(feed_state):
        # This reference has no host extension, appended variables or copied rates.
        reactor = ct.IdealGasReactor(phase_at(initial), clone=False, energy="on", volume=.001)
        upstream = ct.Reservoir(phase_at(feed_state), clone=False)
        downstream = ct.Reservoir(phase_at(sink), clone=False)
        devices = (ct.MassFlowController(upstream, reactor, mdot=.0001),
                   ct.MassFlowController(reactor, downstream, mdot=.0001))
        net = ct.ReactorNet([reactor])
        net.rtol, net.atol, net.max_time_step = 1e-10, 1e-16, .0025
        rows = [(reactor.T, reactor.phase.P, reactor.phase.Y.copy())]
        for t in times[1:]:
            net.advance(float(t))
            rows.append((reactor.T, reactor.phase.P, reactor.phase.Y.copy()))
        return rows, (reactor, net, upstream, downstream, devices)

    started = perf_counter()
    steam_feed = ReactiveState(1500., 2e5, {"CH4": .2, "H2O": .5, "N2": .3})
    oxidative_feed = ReactiveState(1500., 2e5, {"CH4": .2, "H2O": .5, "O2": .05, "N2": .25})
    coarse = solve(steam_feed, .01, 1e-8)
    fine = solve(steam_feed, .0025, 1e-10)
    oxidative = solve(oxidative_feed, .005, 1e-9)
    reference, native_objects = plain_native_reference(steam_feed)
    traces = (coarse, fine, oxidative)
    temperature_error = max(abs(s.temperature_k-r[0]) for s, r in zip(fine.snapshots, reference))
    pressure_error = max(abs(s.pressure_pa-r[1]) for s, r in zip(fine.snapshots, reference))
    species_error = max(float(np.max(abs(np.array([s.mass_fractions[k] for k in fine.species_names])
        -r[2]))) for s, r in zip(fine.snapshots, reference))
    refinement_t = max(abs(a.temperature_k-b.temperature_k)
                       for a, b in zip(coarse.snapshots, fine.snapshots))
    refinement_y = max(abs(a.mass_fractions[k]-b.mass_fractions[k])
        for a, b in zip(coarse.snapshots, fine.snapshots) for k in fine.species_names)
    max_mass = max(float(abs(t.mass_residual_kg).max()) for t in traces)
    max_species = max(float(abs(t.species_residual_kg).max()) for t in traces)
    max_element = max(float(abs(t.element_residual_kg).max()) for t in traces)
    max_energy = max(float(abs(t.energy_residual_j).max()) for t in traces)
    max_reaction_mass = max(float(abs(t.reaction_species_integrals_kg.sum(axis=1)).max())
                            for t in traces)
    source_error = max(float(abs(t.integral("inlet:feed:mass")-.0001*times).max()) for t in traces)
    mass_change = max(abs(t.snapshots[-1].mass_kg-t.snapshots[0].mass_kg) for t in traces)
    minimum_y = min(min(s.mass_fractions.values()) for t in traces for s in t.snapshots)
    copies = tuple(a for t in traces for a in t.phase_copy_audits)
    copy_roundtrip = max(a.maximum_relative_roundtrip for a in copies)
    after = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}
    gates = {
        "native gas chemistry and native ReactorNet remain actual objects": all(
            t.native.reactor.chemistry_enabled and isinstance(t.native.network, ct.ReactorNet)
            for t in traces) and isinstance(native_objects[0], ct.IdealGasReactor),
        "mass/species/element defects <1e-10 kg": max(max_mass, max_species, max_element) < 1e-10,
        "native U and boundary enthalpy energy defect <1e-4 J": max_energy < 1e-4,
        "integrated native chemical production sums to mass <1e-10 kg": max_reaction_mass < 1e-10,
        "independent constant source integral and constant inventory <1e-10 kg":
            max(source_error, mass_change) < 1e-10,
        "plain native unextended full trajectory <1e-3 K /0.2 Pa /1e-7 Y":
            temperature_error < 1e-3 and pressure_error < .2 and species_error < 1e-7,
        "coarse/fine full trajectory <1e-3 K /1e-7 Y": refinement_t < 1e-3 and refinement_y < 1e-7,
        "steam-only gas converts carbon feed and produces net H2 and CO":
            fine.integral("reaction:species:H2")[-1] > 1e-8
            and fine.integral("reaction:species:CO")[-1] > 0.
            and fine.integral("reaction:species:CH4")[-1] < 0.,
        "oxidative feed separately produces H2 with positive heat response":
            oxidative.integral("reaction:species:H2")[-1] > 1e-8
            and oxidative.snapshots[-1].temperature_k > initial.temperature_k,
        "no external chemical-heat boundary or wall heat added": all(
            not t.heat_boundaries and np.all(t.integral("wall:heat") == 0.) for t in traces),
        "raw accepted-output composition; sampled minimum Y >=-1e-12": minimum_y >= -1e-12,
        "private definitions audited <=2e-15 relative; exact owned hash retained":
            copy_roundtrip <= 2e-15 and all(t.phase_fingerprint == t.phase_copy_audits[0].owned_fingerprint
                and t.source_phase_fingerprint == t.phase_copy_audits[0].source_fingerprint for t in traces),
        "reaction H2 production distinct from boundary-only H2 removal":
            fine.integral("reaction:species:H2")[-1] > 0.
            and fine.integral("net:species:H2")[-1] < 0.,
        "host/test/replay source bytes unchanged across run": before == after,
    }
    elapsed = perf_counter()-started
    lines = ["# Native finite reacting gas process", "",
        "Reproduce: `python scripts/check_reactive_process.py` with the optional chemistry extra.", "",
        f"Cantera {ct.__version__}; installed GRI30 has {fine.native.reactor.phase.n_species} species and "
        f"{fine.native.reactor.phase.n_reactions} gas reactions. Three host native integrations plus one plain "
        f"native reference took {elapsed:.6g} s. Native kinetics/EOS/CVODES are unchanged; no mechanism is bundled.", "",
        "Original verification inputs: rigid 0.001 m3 ideal-gas inventory, initially pure N2 at 1500 K and "
        "101325 Pa. Fixed feed reservoir is 1500 K /200000 Pa, X(CH4,H2O,N2)=(0.2,0.5,0.3). Inlet and "
        "outlet are each prescribed 0.0001 kg/s on the absolute [0,0.2] s window; callbacks explicitly support "
        "[0,0.5] s. Outlet removes native well-mixed composition/enthalpy. No wall or work is present. A separate "
        "oxidative case uses X(CH4,H2O,O2,N2)=(0.2,0.5,0.05,0.25). These are authored numerical cases, "
        "not apparatus operating data, catalyst fits or independent experiments.", "",
        "Coarse steam run: max step 0.01 s /rtol1e-8; fine: 0.0025 s /rtol1e-10; oxidative: 0.005 s /rtol1e-9; "
        "host atol1e-15. The plain IdealGasReactor reference has no host extension/appended ledger, uses the "
        "original native definitions, max step0.0025 s /rtol1e-10 /atol1e-16, and compares every output state.", "",
        "Boundary-only species integrals remain separate from integrated native net chemical production. "
        "Species defects subtract both; elemental defects subtract boundary transport only. Native formation "
        "energy is already included in U and h, so no separate reaction power is added. Energy-ledger numerical "
        "conditioning uses the existing1e6 J scale; returned quantities are SI. No physical row is rescaled.", "",
        "All reactive phases own independent native species thermo and reaction objects. The constructor preserves "
        "native thermo class, exact coefficients/bounds/reference pressure and runtime reaction multipliers. "
        "A one-time structural gate admits only native numeric unit-roundtrip error <=2e-15 relative with zero "
        "absolute allowance; prose note changes are counted. Element order may change, with both orders recorded "
        "and per-name atomic weights checked. Source and owned exact hashes are distinct. Actual owned definitions "
        "are checked exactly at accepted outputs. Phase-exposing callbacks additionally retain exact per-RHS "
        "checks; explicit time-only callbacks receive no native phase and use privately owned definitions.", "",
        "| Quantity | Observed value |", "|---|---:|",
        f"| Steam final T /P | {fine.snapshots[-1].temperature_k:.12g} K /{fine.snapshots[-1].pressure_pa:.12g} Pa |",
        f"| Steam final H2 /CH4 mole fraction | {fine.snapshots[-1].mole_fractions['H2']:.12g} /{fine.snapshots[-1].mole_fractions['CH4']:.12g} |",
        f"| Steam integrated chemical H2 production | {fine.integral('reaction:species:H2')[-1]:.12g} kg |",
        f"| Steam net boundary H2 transfer | {fine.integral('net:species:H2')[-1]:.12g} kg |",
        f"| Oxidative final T /H2 mole fraction | {oxidative.snapshots[-1].temperature_k:.12g} K /{oxidative.snapshots[-1].mole_fractions['H2']:.12g} |",
        f"| Maximum mass /species /element defect | {max_mass:.12g} /{max_species:.12g} /{max_element:.12g} kg |",
        f"| Maximum U/enthalpy energy defect | {max_energy:.12g} J |",
        f"| Independent source /constant inventory error | {source_error:.12g} /{mass_change:.12g} kg |",
        f"| Plain native full-trajectory T /P /Y error | {temperature_error:.12g} K /{pressure_error:.12g} Pa /{species_error:.12g} |",
        f"| Coarse/fine full-trajectory T /Y difference | {refinement_t:.12g} K /{refinement_y:.12g} |",
        f"| Accepted-output sampled minimum mass fraction | {minimum_y:.12g} |",
        f"| Max native copy roundtrip /per-phase changed numeric counts | {copy_roundtrip:.12g} /{[a.numeric_roundtrip_count for a in copies]} |", "",
        "| Gate | Pass |", "|---|---|", *(f"| {k} | {v} |" for k, v in gates.items()), "",
        "This is one gas-phase carbon/steam conversion reference for production research. GRI30 gas chemistry "
        "does not qualify a catalytic steam reformer or shift bed. Catalyst surfaces, solids/coke, porous transport, "
        "spatial residence profiles, pressure-driven capacity, wall inventory, phase changes, industrial yields and "
        "measured process qualification remain open. Imposed equal mass flows do not solve a compressor or valve. "
        "H2 spin remains unresolved on the native formation-energy zero; no CoolProp energy conversion is implied.", "",
        "Primary references: [native control-volume equations](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html), "
        "[public extension/flow APIs](https://cantera.org/3.2/python/zerodim.html), "
        "[native reaction-rate APIs](https://cantera.org/3.2/python/kinetics.html), "
        "[separately installed GRI30 provenance](https://cantera.org/3.2/examples/input/gri30.html). "
        "Cantera retains BSD-3-Clause and upstream mechanism provenance. No external code, coefficient table or "
        "mechanism text is copied into this repository or its distributions.", "",
        "## Reproduction fingerprints", "",
        f"- Installed gri30.yaml SHA-256: `{mechanism_hash}`",
        f"- Source mechanism-phase SHA-256: `{fine.source_phase_fingerprint}`",
        f"- Owned native phase SHA-256: `{fine.phase_fingerprint}`",
        f"- Source /owned element ordering: `{fine.phase_copy_audits[0].source_element_names}` /`{fine.element_names}`",
        "", "| Host source | Begin SHA-256 | End SHA-256 |", "|---|---|---|",
        *(f"| `{name}` | `{sha}` | `{after[name]}` |" for name, sha in before.items()), ""]
    (root/"research/reactive_process.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"Local calculation {elapsed:.6g} s; report: research/reactive_process.md")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
