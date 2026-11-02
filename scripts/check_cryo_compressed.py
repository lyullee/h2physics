"""Replay native finite cryo-compressed storage with independent EOS/event audits."""

import argparse
import hashlib
import sys
import time
from importlib.metadata import version
from pathlib import Path

from scipy.optimize import brentq

from h2physics.adapters.cryo_compressed import (
    CryoCompressedAuditError,
    CryoCompressedDomain,
    CryoCompressedEvidence,
    CryoCompressedGeometry,
    CryoCompressedNative,
    CryoCompressedStorage,
)
from h2physics.adapters.lh2dt_relief import ReliefTankBoundary
from h2physics.core import Origin
from h2physics.release import NozzleOpening
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
HOST_PATHS = ("src/h2physics/adapters/cryo_compressed.py", "tests/test_cryo_compressed.py",
    "scripts/check_cryo_compressed.py", "src/h2physics/adapters/lh2dt_relief.py",
    "src/h2physics/adapters/lh2dt_properties.py", "src/h2physics/adapters/lh2dt.py",
    "src/h2physics/release.py", "src/h2physics/thermo/coolprop.py", "src/h2physics/dynamics.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_hashes(root):
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return {"ordered-top-level-Python": digest.hexdigest(),
            **{name: sha(root/name) for name in ("tank.py", "valve.py", "properties.py")}}


def build(native, fluid="ParaHydrogen", *, set_pressure=100e6, reseat=99e6, wall=25.):
    return CryoCompressedStorage(native, properties=CoolPropProperties(fluid),
        geometry=CryoCompressedGeometry(.01, 100., 1., 100.),
        domain=CryoCompressedDomain(20., 350., 2e6, 120e6, .01, 80., 2.,
            ("supercritical_liquid", "supercritical", "supercritical_gas"), "authored-no-solid-envelope"),
        evidence=CryoCompressedEvidence("authored-20MPa-25K", "authored-fixed-volume-wall",
            "authored-constant-UAs", "authored-binary-pressure-protection",
            "authored-single-fluid-no-solid-domain", Origin.SYNTHETIC),
        initial_pressure_pa_absolute=20e6, initial_temperature_k=25., initial_wall_temperature_k=wall,
        opening=NozzleOpening("authored-cryo-PRV", 1e-8, 1., "authored-effective-area"),
        set_pressure_pa_absolute=set_pressure, reseat_pressure_pa_absolute=reseat)


def run(storage, *, step=.5, duration=100., power=1000.):
    boundary = ReliefTankBoundary("authored-operation-clock", 100., 100.+duration,
        storage.properties.state_pt(19e6, 25.), lambda t: 300.,
        lambda t, fluid, wall: power-storage.geometry.ambient_ua_w_k*(300.-wall),
        "authored-constant-net-wall-power")
    return storage.run(duration_s=duration, maximum_step_s=step, start_time_s=100.,
                       clock_id=boundary.clock_id, boundary=boundary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", type=Path, default=ROOT/"artifacts/native_packages")
    args = parser.parse_args()
    sys.path.insert(0, str(args.native_packages.resolve()))
    native = CryoCompressedNative.from_installed(
        source_id="LH2DT:b2f276333c1b1793c39f25763703d196d36742ec")
    native_root = Path(native.tank_module.__file__).parent
    before = {name: sha(ROOT/name) for name in HOST_PATHS}
    native_before = native_hashes(native_root)
    started = time.perf_counter()
    traces, rows = [], []
    for fluid in ("Hydrogen", "ParaHydrogen", "OrthoHydrogen"):
        storage = build(native, fluid)
        trace = run(storage)
        traces.append(trace)
        first, last = trace.points[0], trace.points[-1]
        rows.append((fluid, first.inventory.mass_kg, first.fluid.density_kg_m3,
            trace.critical_temperature_k, last.fluid.temperature_k, last.fluid.pressure_pa,
            last.native_state.wall_temperature_K))
        print(f"actual native sealed {fluid} warming passed", flush=True)
    primary = traces[1]
    coarse = run(primary.storage, step=1.)
    fine = run(primary.storage, step=.25)
    traces += [coarse, fine]
    refinement = [(abs(t.points[-1].fluid.temperature_k-fine.points[-1].fluid.temperature_k),
                   abs(t.points[-1].fluid.pressure_pa-fine.points[-1].fluid.pressure_pa),
                   abs(t.points[-1].native_state.wall_temperature_K-fine.points[-1].native_state.wall_temperature_K))
                  for t in (coarse, primary)]
    stationary = run(primary.storage, duration=5., power=0.)
    cooling = run(primary.storage, duration=5., power=-100.)
    traces += [stationary, cooling]
    isolated = run(build(native, wall=200.), duration=30., step=.1, power=0.)
    traces.append(isolated)
    fresh = CoolPropProperties("ParaHydrogen")
    mass = isolated.points[0].inventory.mass_kg
    rho = mass/.01
    total = isolated.points[0].inventory.total_energy_j
    equilibrium_p = brentq(lambda pressure: mass*fresh.state_prho(pressure, rho).internal_energy_j_kg
        +100.*fresh.state_prho(pressure, rho).temperature_k-total, 20e6, 40e6, xtol=1e-6)
    equilibrium_t = fresh.state_prho(equilibrium_p, rho).temperature_k
    equilibrium_error = max(abs(isolated.points[-1].fluid.temperature_k-equilibrium_t),
                            abs(isolated.points[-1].native_state.wall_temperature_K-equilibrium_t))
    relief = [run(build(native, set_pressure=21e6, reseat=20.5e6), duration=6., step=step)
              for step in (.5, .25, .125)]
    traces += relief
    events = [trace.native_trace.transitions[0] for trace in relief]
    event_time_differences = [abs(event.time_s-events[-1].time_s) for event in events[:-1]]
    from dataclasses import replace
    limited_storage = build(native, set_pressure=21e6, reseat=20.5e6)
    floor = limited_storage.initial_native_state.hydrogen_mass_kg-1e-5
    limited_storage.domain = replace(limited_storage.domain, minimum_inventory_kg=floor)
    limited = run(limited_storage, duration=6.)
    traces.append(limited)
    retention = []
    ramp_storage = build(native)
    ramp_storage.domain = replace(ramp_storage.domain, maximum_temperature_k=26., maximum_initial_temperature_k=25.)
    ramp_boundary = ReliefTankBoundary("ramp-clock", 100., 101.,
        ramp_storage.properties.state_pt(19e6, 25.), lambda t: 25.,
        lambda t, fluid, wall: 1200.*(t-100.)**10, "authored-smooth-ramp-endpoint-regression")
    try:
        ramp_storage.run(duration_s=1., maximum_step_s=1., start_time_s=100.,
                         clock_id=ramp_boundary.clock_id, boundary=ramp_boundary)
    except CryoCompressedAuditError as error:
        retention.append(("smooth-ramp accepted wall endpoint", error.native_trace.time_s[-1],
            error.accepted_time_s, len(error.audited_points), error.native_state.wall_temperature_K,
            error.native_state is error.native_trace.intervals[-1].native_step.state
            and error.point is None and len(error.audited_points) == 1
            and error.native_trace.time_s[-1] == 101. and error.native_state.wall_temperature_K > 26.
            and all(stage.wall_temperature_k <= 26. for stage in error.native_trace.intervals[-1].stages)
            and isinstance(error.__cause__, ValueError)))
    else:
        raise AssertionError("The accepted wall endpoint must fail its post-run domain audit")
    for method_name in ("state_pt", "state_prho"):
        rejected_storage = build(native)
        rejected_reference = CoolPropProperties("ParaHydrogen")
        original_query = getattr(rejected_reference, method_name)
        cause = RuntimeError("authored independent EOS query failure")
        def failing_query(pressure, other):
            if pressure > 20e6+1.:
                raise cause
            return original_query(pressure, other)
        setattr(rejected_reference, method_name, failing_query)
        rejected_storage.independent_properties_factory = lambda fluid: rejected_reference
        try:
            run(rejected_storage, duration=1., step=.5)
        except CryoCompressedAuditError as error:
            retention.append((f"independent {method_name} raises", error.native_trace.time_s[-1],
                error.accepted_time_s, len(error.audited_points), error.native_state.wall_temperature_K,
                error.native_state is error.native_trace.intervals[0].native_step.state
                and error.point is None and len(error.audited_points) == 1
                and error.native_trace.time_s[-1] == 101. and error.accepted_time_s == 100.5
                and isinstance(error.audited_points, tuple) and error.__cause__ is cause))
        else:
            raise AssertionError(f"Independent {method_name} must retain its query failure")
    warm = fresh.state_pt(20e6, 300.)
    low_lh2 = fresh.saturated(1.5e5, 0.)
    density_ratio = primary.points[0].fluid.density_kg_m3/warm.density_kg_m3
    defects = {"mass_conservation_kg": max(abs(p.balance.mass_residual_kg) for t in traces for p in t.points),
        "energy_conservation_J": max(abs(p.balance.energy_residual_j) for t in traces for p in t.points),
        "PT_mass_kg": max(abs(p.pt_mass_residual_kg) for t in traces for p in t.points),
        "PT_energy_J": max(abs(p.pt_energy_residual_j) for t in traces for p in t.points),
        "Prho_energy_J": max(abs(p.prho_energy_residual_j) for t in traces for p in t.points),
        "Prho_temperature_K": max(abs(p.prho_temperature_residual_k) for t in traces for p in t.points)}
    exact_heat_error = max(abs(p.inventory.total_energy_j-primary.points[0].inventory.total_energy_j
        -1000.*(p.time_s-100.)) for p in primary.points)
    after = {name: sha(ROOT/name) for name in HOST_PATHS}
    native_after = native_hashes(native_root)
    gates = {
        "three actual native spin-specific tank/state/driver objects retained": len(rows) == 3 and all(
            isinstance(t.native_trace.native_tank, native.tank_module.HomogeneousTank)
            and t.native_trace.native_tank is t.storage.native_tank for t in traces),
        "sealed cryogenic25K to above native critical T without changing EOS/ODE": all(
            t.points[0].fluid.temperature_k < t.critical_temperature_k < t.points[-1].fluid.temperature_k
            and t.points[0].fluid.phase == "supercritical_liquid" and t.points[-1].fluid.phase == "supercritical"
            and t.native_trace.released_mass_kg[-1] == 0. for t in traces[:3]),
        "closed high-pressure paths remain above critical P": all(
            min(p.fluid.pressure_pa for p in t.points) > t.critical_pressure_pa for t in traces[:3]),
        "independent physical mass/U+wall ledgers <1e-12kg/1e-5J":
            defects["mass_conservation_kg"] < 1e-12 and defects["energy_conservation_J"] < 1e-5,
        "fresh native PT reconstructs inventory <1e-10kg/1e-4J":
            defects["PT_mass_kg"] < 1e-10 and defects["PT_energy_J"] < 1e-4,
        "fresh native Prho reconstructs U/T <1e-4J/1e-7K":
            defects["Prho_energy_J"] < 1e-4 and defects["Prho_temperature_K"] < 1e-7,
        "independent constant net external heat exact total energy <1e-5J": exact_heat_error < 1e-5,
        "native finite wall closed-equilibrium root <1e-6K": equilibrium_error < 1e-6,
        "uniform zero-net-power state and signed cooling remain physical":
            abs(stationary.points[-1].fluid.temperature_k-25.) < 1e-10
            and cooling.points[-1].fluid.temperature_k < 25. and cooling.native_trace.external_heat_j[-1] < 0.,
        "native1/.5/.25s refinement <1Pa/.001K":
            max(row[1] for row in refinement) < 1. and max(max(row[0], row[2]) for row in refinement) < .001,
        "actual shared relief open events meet fixed0.001Pa/1e-8s brackets": all(
            abs(event.pressure_pa-21e6) < .001
            and event.upper_bracket_time_s-event.lower_bracket_time_s <= 1e-8
            and event.source_before.mass_flow_kg_s == 0. and event.source_after.mass_flow_kg_s > 0.
            for event in events),
        "existing pressure-event time refinement <1e-4s": max(event_time_differences) < 1e-4,
        "positive finite floor localized without valve closure or mass clipping":
            limited.native_trace.termination == "inventory_floor"
            and abs(limited.native_trace.inventory_event.mass_kg-floor) < 1e-12
            and limited.native_trace.inventory_event.source_at_limit.mass_flow_kg_s > 0.,
        "warm-gas/low-pressureLH2 domains are physically distinct": density_ratio > 5.
            and low_lh2.pressure_pa < fresh.critical_pressure_pa < primary.points[0].fluid.pressure_pa,
        **{f"post-run failure retains raw trace/state/prior prefix/cause: {row[0]}": row[-1]
           for row in retention},
        "native and executed host/test/script begin/end fingerprints unchanged":
            before == after and native_before == native_after,
    }
    elapsed = time.perf_counter()-started
    lines = ["# Native finite cryo-compressed storage", "",
        "Original synthetic software/native-conservation verification, not a manufacturer map, storage rating, "
        "material calibration or independent apparatus validation. Reproduce: `python scripts/check_cryo_compressed.py`.", "",
        f"LH2DT0.1.2 pinnedb2f276333c1b1793c39f25763703d196d36742ec; CoolProp{version('CoolProp')}, "
        f"SciPy{version('scipy')}; {len(traces)+len(retention)} completed native driver integrations "
        f"({len(traces)} accepted audited traces, {len(retention)} rejected post-run audit regressions) "
        f"in{elapsed:.6f}s.", "",
        "Fixed0.01m3 homogeneous fluid; wallC100J/K, ambientUA1W/K, fluid/wallUA100W/K. "
        "Initial20MPa(abs)/25K with own-fluid initial wall. An explicit callback cancels the ambient term "
        "and supplies net1000W into the wall for100s on operation clock100–200s. This manufactured forcing "
        "is an analytic verification boundary, not a physical insulation or refrigeration rating. "
        "The supplied pressure-protection set100MPa/reseat99MPa is not reached in these sealed runs; "
        "receiver19MPa25K and effective area1e-8m2 are explicit. No tank ODE/EOS/nozzle/event code was replaced.", "",
        "Declared authored domain20–350K,2–120MPa(abs), positive inventory floor0.01kg; "
        "cryogenic initialT<=80K and initialP>=2*own-native-criticalP. Allowed single-fluid classes are "
        "supercritical_liquid/supercritical/supercritical_gas. Solid exclusion remains a caller-evidenced "
        "application premise. Crossing Tcritical while P>Pcritical is not passage through the critical point "
        "or a two-phase transition. No normal/para/ortho conversion is inferred.", "",
        "| Fluid | Initial mass kg | Initial rho kg/m3 | Native Tcritical K | Final fluid T K | Final P Pa(abs) | Final wall T K |",
        "|---|---:|---:|---:|---:|---:|---:|", *(
            "| "+name+" | "+" | ".join(f"{value:.12g}" for value in row)+" |" for name, *row in rows), "",
        "| Independent defect | Maximum |", "|---|---:|",
        *(f"| {name} | {value:.12g} |" for name, value in defects.items()), "",
        f"Exact external-power total-energy error{exact_heat_error:.12g}J. Independent finite-fluid/wall "
        f"equilibrium{equilibrium_t:.12g}K; final maximumT error{equilibrium_error:.12g}K. "
        f"Para-H2 coarse/medium versus fine differences(Tfluid K,P Pa,Twall K):{refinement}.", "",
        "Independent native EOS inversion gates (1e-10kg,1e-4J,1e-7K) are separate from physical "
        "inventory conservation gates(1e-12kg,1e-5J,relative1e-10). A direct-Prho flash can return "
        "approximately2e-9K numerical temperature roundtrip error here, corresponding to approximately1e-5J; "
        "that is not a tank energy defect or an EOS-accuracy claim.", "",
        "## Pressure events and finite inventory", "",
        "Actual existing Lh2dtReliefTankDriver, transactional native PressureReliefValve and shared "
        "HomogeneousIsentropicNozzle are reused. Separate6s windows use set21MPa/reseat20.5MPa and the same "
        "19MPa receiver; after opening real finite bulk withdrawal continues. A pressure event is not "
        "treated as a stop, valve isolation or vapor-selective pickup. Endpoint bracketing requires "
        "resolved first crossings and does not detect arbitrary hidden within-step nonmonotonic events.", "",
        "| Native max step s | Open time s | Pressure Pa(abs) | Released mass kg | Released enthalpy J |",
        "|---:|---:|---:|---:|---:|", *(
            f"| {step} | {event.time_s:.12g} | {event.pressure_pa:.12g} | "
            f"{trace.native_trace.released_mass_kg[-1]:.12g} | {trace.native_trace.released_enthalpy_j[-1]:.12g} |"
            for step, event, trace in zip((.5,.25,.125), events, relief, strict=True)), "",
        f"Open-time differences vs finest:{event_time_differences}s. Floor case stops at "
        f"{limited.native_trace.inventory_event.time_s:.12g}s, mass{limited.native_trace.inventory_event.mass_kg:.12g}kg "
        f"against declared{floor:.12g}kg; valve/source remains open. Positive sub-floor native trial states "
        "are allowed only to localize the existing event; the final floor residual uses the explicit1e-12kg event budget. "
        "No accepted mass is clipped.", "",
        f"At20MPa the25K/300K para-H2 density ratio is{density_ratio:.12g}; the150kPa saturated-liquid "
        f"comparison has rho{low_lh2.density_kg_m3:.12g}kg/m3. The builder rejects warm300K and low-pressure "
        "initializations instead of relabeling those other storage levels as cryo-compressed.", "",
        "## Completed native runs with rejected post-run audits", "",
        "| Regression | Completed native end s | Failing accepted time s | Prior audited points | Failing native wall K | Retained |",
        "|---|---:|---:|---:|---:|---|", *(
            f"| {name} | {end:.12g} | {at:.12g} | {prefix} | {wall:.12g} | {kept} |"
            for name, end, at, prefix, wall, kept in retention), "",
        "The smooth wall power1200*(t-100)^10W case uses ambient25K, wall domain maximum26K, "
        "and a single1s native interval100–101s. All actual RK stage inputs remain inside the wall "
        "domain but the accepted endpoint exits it. The post-run error retains the completed native "
        "trace, actual failing accepted state, its time, the immutable already audited prefix, optional "
        "constructed point and original chained exception. Deliberately raised independent PT/P-rho "
        "query failures are negative error-retention fixtures; they do not substitute for native physics "
        "in the successful verification cases. Residual-gate failures retain the same fields in tests.", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "High-pressure warming is verified for the declared authored envelope. Initial fill/cooling plant, "
        "refueling, vacuum insulation construction, pressure-vessel strength/fatigue, spatial stratification, "
        "selective phase ports, evolving spin thermochemistry, real valve capacity and measured apparatus "
        "qualification remain open. Signed wall cooling is an explicit thermal boundary, not a predicted "
        "refrigeration cycle/COP. Native phase/domain/EOS failures propagate with actual objects; no ideal-gas "
        "or alternate tank fallback is used. An accepted-step/stop-at-first-pressure API remains useful receiving work.", "",
        "Primary sources: [LLNL/DOE cryo-compressed storage report]"
        "(https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress07/vi_a_6_aceves.pdf), "
        "[NIST separate hydrogen EOS](https://doi.org/10.1063/1.3160306), "
        "[native LH2DT](https://github.com/lyullee/lh2dt_models), "
        "[CoolProp native library](https://doi.org/10.1021/ie4033999). Native engine remains separately installed MIT. "
        "No third-party implementation, coefficient table or external measurements are bundled.", "",
        "## Begin/end fingerprints", "", "| Native source | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {native_after[name]} |" for name, value in native_before.items()), "",
        "| Host source/test/replay | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {after[name]} |" for name, value in before.items()), ""]
    (ROOT/"research/cryo_compressed.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
    if not all(gates.values()):
        raise SystemExit("Cryo-compressed gate failed; actual report retained")
    print(f"wrote research/cryo_compressed.md; local calculation{elapsed:.6f}s", flush=True)


if __name__ == "__main__":
    main()
