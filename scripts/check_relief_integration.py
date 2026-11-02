"""Replay actual pinned native pressure relief with finite tank event audits."""

import hashlib
import importlib
import importlib.metadata as metadata
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.adapters.lh2dt_relief import (
    Lh2dtReliefTankDriver,
    ReliefTankBoundary,
    shared_native_relief,
)
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.thermo import CoolPropProperties

REVISION = "b2f276333c1b1793c39f25763703d196d36742ec"
NATIVE_SOURCE_SHA256 = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"


def native_hash(directory):
    digest = hashlib.sha256()
    for file in sorted(directory.glob("*.py")):
        digest.update(file.name.encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    target = root/"artifacts/native_packages"
    native_directory = target/"lh2dt"
    if not native_directory.is_dir():
        raise SystemExit("Install the separately reviewed pinned LH2DT snapshot first")
    before_native = native_hash(native_directory)
    if before_native != NATIVE_SOURCE_SHA256:
        raise SystemExit("Installed LH2DT module bytes differ from the reviewed pinned source")
    input_files = ("src/h2physics/adapters/lh2dt_relief.py", "tests/test_lh2dt_relief.py",
                   "scripts/check_relief_integration.py", "src/h2physics/adapters/lh2dt_equipment.py",
                   "src/h2physics/release.py", "src/h2physics/adapters/lh2dt_properties.py")
    hashes = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in input_files}
    native_files = {name: hashlib.sha256((native_directory/name).read_bytes()).hexdigest()
                    for name in ("tank.py", "valve.py", "properties.py", "streams.py", "adaptive.py")}
    sys.path.insert(0, str(target))
    native = importlib.import_module("lh2dt")
    if Path(native.__file__).resolve().parent != native_directory.resolve():
        raise SystemExit("Native import did not resolve to the reviewed snapshot")
    valve_module = importlib.import_module("lh2dt.valve")
    tank_module = importlib.import_module("lh2dt.tank")
    state_type = importlib.import_module("lh2dt.properties").ThermoState
    flow_type = importlib.import_module("lh2dt.streams").MassEnergyFlow
    started = perf_counter()

    def make_case(*, pressure=1.9e5, duration=30., power=100., set_pressure=2e5, reseat=1.8e5):
        properties = CoolPropProperties("Hydrogen")
        provider = Lh2dtLowLevelProperties(properties, state_factory=state_type)
        bridge = Lh2dtProperties(provider, reference_id=properties.basis.reference_id)
        opening = NozzleOpening("authored-PRV-opening", 1e-6, 1., "declared-effective-orifice-area")
        protection = shared_native_relief(native_valve_type=valve_module.Valve,
            native_relief_factory=valve_module.PressureReliefValve, result_factory=valve_module.ValveResult,
            nozzle=HomogeneousIsentropicNozzle(properties), bridge=bridge, opening=opening,
            set_pressure_pa_absolute=set_pressure, reseat_pressure_pa_absolute=reseat,
            native_source_id=f"LH2DT:{REVISION}")
        tank = tank_module.HomogeneousTank(tank_module.TankGeometry(.01, 100., 1., 10.), provider)
        state = provider.from_pT(pressure, 300.)
        mass = state.density_kg_m3*.01
        initial = tank_module.TankState(mass, mass*state.specific_internal_energy_J_kg, 300.)
        boundary = ReliefTankBoundary("authored-absolute-clock", 100., 100.+duration,
            properties.state_pt(1e5, 300.), lambda t: 300.,
            lambda t, s, wall: power-1.*(300.-wall), "authored-constant-net-wall-power")
        driver = Lh2dtReliefTankDriver(tank, protection, flow_factory=flow_type, state_factory=state_type)
        return driver, initial, boundary

    def run(step, *, minimum_fraction=None, **case_options):
        driver, initial, boundary = make_case(**case_options)
        return driver.run(initial, duration_s=case_options.get("duration", 30.),
            maximum_step_s=step, start_time_s=100., clock_id="authored-absolute-clock",
            boundary=boundary, minimum_inventory_kg=(1e-6 if minimum_fraction is None
                                                    else initial.hydrogen_mass_kg*minimum_fraction))

    runs = [run(step) for step in (.5, .25, .125)]
    coarse, medium, fine = runs
    zero = run(.1, duration=1., power=0.)
    sealed_heat = run(.1, duration=1., set_pressure=1e7, reseat=9e6)
    inventory = run(.25, pressure=2.1e5, duration=5., minimum_fraction=.99)
    all_runs = (*runs, zero, sealed_heat, inventory)
    max_mass = max(float(np.max(abs(r.mass_residual_kg))) for r in all_runs)
    max_energy = max(float(np.max(abs(r.energy_residual_j))) for r in all_runs)
    max_clock = max((e.upper_bracket_time_s-e.lower_bracket_time_s
                     for r in all_runs for e in r.transitions), default=0.)
    localized = [e for r in runs for e in r.transitions]
    max_pressure_error = max(abs(e.pressure_pa-e.threshold_pa) for e in localized)
    event_differences = [max(abs(a.time_s-b.time_s) for a, b in
        zip(other.transitions, fine.transitions, strict=True)) for other in (coarse, medium)]
    final_mass_differences = [float(abs(r.released_mass_kg[-1]-fine.released_mass_kg[-1]))
                              for r in (coarse, medium)]
    final_pressure_differences = [abs(r.intervals[-1].native_step.thermo.pressure_Pa
                                    -fine.intervals[-1].native_step.thermo.pressure_Pa) for r in (coarse, medium)]
    sampled_mass = sampled_enthalpy = 0.
    for interval in fine.intervals:
        dt = interval.end_time_s-interval.start_time_s
        sampled_mass += .5*dt*(interval.source_at_start.mass_flow_kg_s+interval.source_at_end.mass_flow_kg_s)
        sampled_enthalpy += .5*dt*(interval.source_at_start.nozzle.withdrawal_energy_w
                                 +interval.source_at_end.nozzle.withdrawal_energy_w)
    sample_mass_error = sampled_mass-fine.released_mass_kg[-1]
    sample_energy_error = sampled_enthalpy-fine.released_enthalpy_j[-1]

    # Retain the raw native trial-order failure without using it for integration.
    probe_driver, _, _ = make_case()
    protection = probe_driver.protection
    provider = protection.bridge.native
    high, band, downstream = provider.from_pT(2.1e5, 300.), provider.from_pT(1.9e5, 300.), provider.from_pT(1e5, 300.)
    raw = protection.native_origin
    raw_band_before = raw.evaluate(band, downstream).mass_flow_kg_s
    raw.evaluate(high, downstream)
    raw_band_after = raw.evaluate(band, downstream).mass_flow_kg_s
    protected_values = [protection.evaluate(s, downstream).mass_flow_kg_s for s in (high, band, high, band)]
    native_unchanged = native_hash(native_directory) == before_native
    after_hashes = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in hashes}
    sources_unchanged = hashes == after_hashes
    gates = {
        "actual native tank/relief/Valve and native valve-result objects retained":
            all(isinstance(r.native_tank, tank_module.HomogeneousTank)
                and isinstance(r.native_relief_final, valve_module.PressureReliefValve)
                and isinstance(r.native_relief_final.valve, valve_module.Valve)
                and all(isinstance(i.native_step, tank_module.TankStepResult)
                        and isinstance(i.source_at_end.native, valve_module.ValveResult) for i in r.intervals)
                for r in all_runs),
        "raw native evaluation-order failure reproduced, protected probes remain closed":
            raw_band_before == 0. and raw_band_after > 0. and not protection.is_open
            and all(value == 0. for value in protected_values),
        "three resolutions agree on open/reseat cycle": all(
            [e.kind for e in r.transitions] == ["open", "reseat"] for r in runs),
        "native event pressure error <=0.001 Pa and clock bracket <=1e-8 s":
            max_pressure_error <= .001 and max_clock <= 1e-8,
        "closed finite mass / fluid+wall energy defects <1e-12 kg /1e-5 J":
            max_mass < 1e-12 and max_energy < 1e-5,
        "independent constant net wall heat integrates exactly to 3000 J":
            abs(fine.external_heat_j[-1]-3000.) < 1e-7,
        "zero-heat closed analytic limit": not zero.transitions and zero.released_mass_kg[-1] == 0.
            and abs(zero.intervals[-1].native_step.thermo.temperature_K-300.) < 1e-9,
        "sealed positive-heat analytic total-U change 100 J":
            not sealed_heat.transitions and abs(sealed_heat.external_heat_j[-1]-100.) < 1e-8
            and max(abs(sealed_heat.energy_residual_j)) < 1e-5,
        "event times / released mass / final pressure refine <0.01 s /1e-7 kg /10 Pa":
            max(event_differences) < .01 and max(final_mass_differences) < 1e-7
            and max(final_pressure_differences) < 10.,
        "finest independent accepted-sample mass/enthalpy quadrature <0.01%":
            abs(sample_mass_error) < 1e-4*fine.released_mass_kg[-1]
            and abs(sample_energy_error) < 1e-4*fine.released_enthalpy_j[-1],
        "positive inventory floor localized, without fake valve isolation":
            inventory.termination == "inventory_floor" and inventory.native_relief_final.is_open
            and abs(inventory.inventory_event.mass_kg-inventory.minimum_inventory_kg) < 1e-12
            and inventory.inventory_event.source_at_limit.mass_flow_kg_s > 0.,
        "original accepted-native origins were not mutated by integration": all(
            not r.native_relief_origin.is_open for r in all_runs),
        "begin/end native and host fingerprints unchanged": native_unchanged and sources_unchanged,
    }
    elapsed = perf_counter()-started
    lines = ["# Native pressure-relief integration", "",
        "Reproduce: `python scripts/check_relief_integration.py` after separately installing the reviewed native snapshot.", "",
        f"Native source revision `{REVISION}`, separately installed MIT LH2DT; HEOS through the existing "
        f"single-flash facade; CoolProp {metadata.version('CoolProp')}, SciPy {metadata.version('scipy')}; "
        f"{elapsed:.6g} s local calculation wall time. "
        "Six integrations include three temporal refinements, zero heat, sealed heating and a finite inventory floor.", "",
        "Original synthetic gas case: normal H2, V=0.01 m3; fluid/wall initially 300 K; initial upstream 190000 Pa "
        "absolute; wall capacity 100 J/K; ambient/fluid-wall UAs 1/10 W/K. Set/reseat 200000/180000 Pa absolute "
        "are caller inputs. Fixed downstream 100000 Pa, effective-area factor 1, opening 1e-6 m2. "
        "A manufactured explicit wall boundary gives constant net 100 W after accounting for the native ambient UA. "
        "Clock [100,130] s; maximum steps 0.5/0.25/0.125 s. This is a finite homogeneous gas reference, not a vapor "
        "pickup model for a stratified cryogenic tank or a rated relief device.", "",
        "Native PressureReliefValve.evaluate mutates its latch on trial calls. The retained raw test has band flow "
        f"{raw_band_before:.12g} kg/s before a high-pressure trial and {raw_band_after:.12g} kg/s afterwards. "
        "Protected trials call the actual underlying native Valve subclass at the fixed accepted opening; only its "
        "public evaluate method delegates the existing shared valve/nozzle. A native latch copy is promoted only "
        "after successful accepted-event evaluation. No protected latch field, native equation or external source is edited.", "",
        "Native HomogeneousTank.simulate owns each RK4 interval and boundary ledger. Host event replay starts "
        "from the same accepted tank/latch state and brackets the first resolved threshold. Endpoint detection "
        "does not establish completeness for arbitrary unresolved within-step nonmonotonic pressure excursions. "
        "The maximum step and forcing bandwidth need independent convergence/application checks.", "",
        "| Quantity | Observed value |", "|---|---:|",
        *(f"| Fine {e.kind} event | {e.time_s:.12g} s; {e.pressure_pa:.12g} Pa |" for e in fine.transitions),
        f"| Fine released mass / stagnation enthalpy | {fine.released_mass_kg[-1]:.12g} kg / {fine.released_enthalpy_j[-1]:.12g} J |",
        f"| Maximum mass / fluid+wall energy defect | {max_mass:.12g} kg / {max_energy:.12g} J |",
        f"| Maximum threshold pressure / clock-bracket error | {max_pressure_error:.12g} Pa / {max_clock:.12g} s |",
        f"| Coarse/medium event-time differences from fine | {event_differences} s |",
        f"| Coarse/medium released-mass differences from fine | {final_mass_differences} kg |",
        f"| Coarse/medium final pressure differences from fine | {final_pressure_differences} Pa |",
        f"| Fine accepted-sample mass / enthalpy quadrature differences | {sample_mass_error:.12g} kg / {sample_energy_error:.12g} J |",
        f"| Fine accepted/trial native intervals | {len(fine.intervals)} / {fine.trial_interval_count} |",
        f"| Positive inventory-floor time / mass | {inventory.inventory_event.time_s:.12g} s / {inventory.inventory_event.mass_kg:.12g} kg |", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "Pressure actuation uses physical upstream absolute pressure, not a transmitter reading or a differential-pressure "
        "substitution. Event pre/post source limits remain separate at the same tank state and clock. The remote "
        "throttling port retains upstream enthalpy; the one solved nozzle plane retains static enthalpy plus KE. "
        "The current native homogeneous tank owns bulk-mixture withdrawal. No unknown vapor takeoff, vent-stack "
        "backpressure, area, heat load, actuator stroke or annual initiating frequency is inferred.", "",
        "These are numerical/interface verification results. Native binary hysteresis excludes manufacturer lift curves, "
        "seat leakage, finite stroke, chatter mechanics and certification. Equal set/reseat and downstream at/above "
        "reseat are explicitly unavailable at this event level. Native failures and sub-floor clock intervals fail "
        "with accepted tank/protection state retained, rather than becoming successful isolation. Further receiving work "
        "is a public native latch snapshot/restore/pure-evaluate interface, native accepted-event hooks and general "
        "first-crossing/dense-output capability. No receiving repository was changed or messaged.", "",
        "Primary sources: [native LH2DT](https://github.com/lyullee/lh2dt_models), "
        "[NASA Glenn choking reference](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html), "
        "[ANL cryogenic relief thermodynamic context](https://www.phy.anl.gov/division/esh/Cryogenic/Appendix%202/appendix%202.htm). "
        "The adapter/event driver/tests are original; no valve/tank implementation, coefficient table or experimental "
        "dataset is bundled. This replay is not relief sizing, certification or vendor qualification.", "",
        "## Begin/end fingerprints", "",
        f"- Native Python aggregate before: `{before_native}`",
        f"- Native Python aggregate after: `{native_hash(native_directory)}`",
        *(f"- Native `{name}`: `{sha}`" for name, sha in native_files.items()),
        *(f"- `{name}`: `{sha}`" for name, sha in hashes.items()),
        f"- Native unchanged: {native_unchanged}; host source/test/script unchanged: {sources_unchanged}.", "",
        "| Host source | Begin SHA-256 | End SHA-256 |", "|---|---|---|",
        *(f"| `{name}` | `{sha}` | `{after_hashes[name]}` |" for name, sha in hashes.items()), ""]
    (root/"research/native_relief.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"Local calculation: {elapsed:.6g} s; report: research/native_relief.md")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
