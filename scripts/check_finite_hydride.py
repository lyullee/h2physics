"""Reproduce synthetic finite native-gas hydride conservation and refinement."""

import hashlib
import importlib.metadata as metadata
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.storage.finite_hydride import (
    BoundHydrogenEnergyReference,
    FiniteHydrideBed,
    FiniteHydrideDomain,
    FiniteHydrideHeatBoundary,
    FiniteHydrideHeatInput,
    HydrideGasThermodynamics,
)
from h2physics.storage.hydride import (
    ArrheniusRate,
    HydrideKinetics,
    HydrideParameters,
    HydrideState,
    VanthoffPlateau,
)
from h2physics.thermo import CoolPropProperties


def main():
    root = Path(__file__).resolve().parents[1]
    inputs = ("src/h2physics/storage/finite_hydride.py", "src/h2physics/storage/hydride.py",
              "src/h2physics/thermo/coolprop.py", "tests/test_finite_hydride.py",
              "scripts/check_finite_hydride.py")
    fingerprints = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}
    start = perf_counter()

    def model(fluid="Hydrogen", *, minimum_mass=1e-7, rate=.01):
        gas = HydrideGasThermodynamics.coolprop(fluid)
        parameters = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
        kinetics = HydrideKinetics(VanthoffPlateau(24000., 80., 1e5),
            ArrheniusRate(rate, 0., 300.), ArrheniusRate(2*rate, 0., 300.))
        reference = BoundHydrogenEnergyReference.from_gas(gas, temperature_k=300., pressure_pa=1e5,
            desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-verification-only-24000-J-per-mol-H2")
        return FiniteHydrideBed(parameters, kinetics, gas, reference,
            FiniteHydrideDomain(200., 600., 1e3, 1e7, minimum_mass),
            free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.)

    def run(bed, *, step=.5, pressure=3e5, temperature=300., fraction=.1,
            duration=100., heating=0., isothermal=False, points=201):
        heat = FiniteHydrideHeatBoundary("authored-absolute-clock", 100., 100.+duration,
            lambda t, s: FiniteHydrideHeatInput(300., solid_heat_w=heating),
            "authored-constant-power-boundary")
        return bed.simulate(np.linspace(100., 100.+duration, points),
            HydrideState(fraction, temperature), bed.gas.state_pt(pressure, temperature),
            boundary=heat, clock_id="authored-absolute-clock", maximum_step_s=step,
            relative_tolerance=1e-9, isothermal_temperature_k=temperature if isothermal else None)

    bed = model()
    coarse, medium, fine = (run(bed, step=step) for step in (1., .5, .25))
    para_bed = model("ParaHydrogen")
    para = run(para_bed)
    release = run(bed, pressure=5e4, temperature=320., fraction=.8, duration=20.)
    reversal = run(bed, pressure=2e5, duration=80., heating=400., points=321)
    zero = run(model(rate=0.), duration=10., points=21)
    initial_mass = bed.gas.state_pt(3e5, 300.).density_kg_m3*.005
    floor_bed = model(minimum_mass=.95*initial_mass)
    floor = run(floor_bed, step=.1)
    isothermal = run(bed, duration=60., isothermal=True, points=2001)
    all_runs = (coarse, medium, fine, para, release, reversal, zero, floor, isothermal)
    max_mass = max(float(np.max(abs(r.total_hydrogen_residual_kg))) for r in all_runs)
    max_transfer = max(float(max(np.max(abs(r.gas_transfer_residual_kg)),
                                 np.max(abs(r.solid_transfer_residual_kg)))) for r in all_runs)
    max_energy = max(float(max(np.max(abs(r.total_energy_residual_j)),
                               np.max(abs(r.gas_energy_residual_j)),
                               np.max(abs(r.solid_energy_residual_j)),
                               np.max(abs(r.gas_integrated_state_residual_j)))) for r in all_runs)

    # Independent native EOS reconstruction: none of the model's stored masses,
    # energies or bound-H coefficient is used to construct these quantities.
    audit_native = CoolPropProperties("Hydrogen")
    native_ref = audit_native.state_pt(1e5, 300.)
    molar_mass = bed.gas.molar_mass_kg_mol
    independently_bound_energy_per_kg = native_ref.enthalpy_j_kg-24000./molar_mass
    reconstructed_energy = []
    reconstructed_mass = []
    for s in fine.snapshots:
        native = audit_native.state_pt(s.gas.pressure_pa, s.gas.temperature_k)
        mass = native.density_kg_m3*.005
        solid_h2 = .002*s.fraction
        reconstructed_mass.append(mass+solid_h2)
        reconstructed_energy.append(mass*native.internal_energy_j_kg
            +1000.*(s.solid_temperature_k-300.)+solid_h2*independently_bound_energy_per_kg)
    native_total_energy_drift = float(np.max(abs(np.array(reconstructed_energy)-reconstructed_energy[0])))
    native_total_mass_drift = float(np.max(abs(np.array(reconstructed_mass)-reconstructed_mass[0])))

    independent_thermostat_power = []
    for s in isothermal.snapshots:
        # Only the existing kinetics and actual native fixed-T derivative enter
        # this independently sampled whole-system heat rate; interface enthalpy
        # and gas-solid heat cancel when both control volumes are combined.
        native = audit_native.state_pt(s.gas.pressure_pa, 300.)
        fugacity = bed.gas.fugacity_pa(native)
        dx = bed.kinetics.fraction_rate_s_inv(s.fraction, 300., fugacity)
        uptake = .002*dx
        independent_thermostat_power.append(uptake*(independently_bound_energy_per_kg
            -bed.gas.isothermal_mass_energy_derivative(native)))
    sampled_thermostat_heat = np.trapezoid(independent_thermostat_power, isothermal.time_s)
    integrated_thermostat_heat = (isothermal.integrated_gas_thermostat_heat_j[-1]
                                 +isothermal.integrated_solid_thermostat_heat_j[-1])
    thermostat_sampling_difference = float(sampled_thermostat_heat-integrated_thermostat_heat)
    temperatures = [abs(a.snapshots[-1].solid_temperature_k-b.snapshots[-1].solid_temperature_k)
                    for a, b in ((coarse, medium), (medium, fine))]
    fractions = [abs(a.snapshots[-1].fraction-b.snapshots[-1].fraction)
                 for a, b in ((coarse, medium), (medium, fine))]
    pressure_differences = [abs(a.snapshots[-1].gas.pressure_pa-b.snapshots[-1].gas.pressure_pa)
                            for a, b in ((coarse, medium), (medium, fine))]
    reverse_changes = np.diff([s.fraction for s in reversal.snapshots])
    ref = bed.energy_reference
    native_pv_mol = (native_ref.pressure_pa/native_ref.density_kg_m3*molar_mass)
    gates = {
        "closed total hydrogen drift <1e-13 kg": max_mass < 1e-13,
        "independent uptake gas/solid ledger defects <1e-13 kg": max_transfer < 1e-13,
        "each gas/solid/total-U/integrated-state defect <1e-5 J": max_energy < 1e-5,
        "independent native PT total mass/energy drift <1e-13 kg /1e-5 J":
            native_total_mass_drift < 1e-13 and native_total_energy_drift < 1e-5,
        "reference absorption DeltaU equals native Pv_mol-DeltaHdes <1e-8 J/mol":
            abs(ref.reference_absorption_internal_energy_j_mol_h2-(native_pv_mol-24000.)) < 1e-8,
        "absorption warms and consumes finite gas, below complete loading":
            fine.snapshots[-1].solid_temperature_k > 300.
            and .1 < fine.snapshots[-1].fraction < 1.
            and fine.snapshots[-1].gas_mass_kg < fine.snapshots[0].gas_mass_kg,
        "same model desorbs, returns H2 and cools solid":
            release.integrated_hydrogen_uptake_kg[-1] < 0
            and release.snapshots[-1].solid_temperature_k < 320.,
        "prescribed 400 W reverses uptake with independent 32000 J input":
            max(reverse_changes) > 1e-5 and min(reverse_changes) < -1e-5
            and abs(reversal.integrated_external_solid_heat_j[-1]-32000.) < 1e-5,
        "gas floor localized before requested end, retained positive inventory":
            floor.termination == "gas_inventory_floor" and 100. < floor.event_time_s < 200.
            and abs(floor.snapshots[-1].gas_mass_kg-floor_bed.domain.minimum_gas_mass_kg) < 1e-13,
        "zero kinetic limit remains stationary":
            zero.snapshots[-1].fraction == zero.snapshots[0].fraction
            and abs(zero.snapshots[-1].gas.pressure_pa-zero.snapshots[0].gas.pressure_pa) < 1e-5,
        "isothermal native thermostat independent sampled heat <0.01 J":
            abs(thermostat_sampling_difference) < .01,
        "1/0.5/0.25 s refinement fraction/T/P <1e-8 /1e-5 K /0.01 Pa":
            max(fractions) < 1e-8 and max(temperatures) < 1e-5 and max(pressure_differences) < .01,
        "explicit normal/para identities retained":
            fine.snapshots[-1].gas.basis.spin_composition == "normal"
            and para.snapshots[-1].gas.basis.spin_composition == "para",
        "source fingerprints unchanged during native calculation": all(
            hashlib.sha256((root/name).read_bytes()).hexdigest() == sha
            for name, sha in fingerprints.items()),
    }
    elapsed = perf_counter()-start
    lines = ["# Finite gas / hydride inventory verification", "",
        "Reproduce: `python scripts/check_finite_hydride.py` with the thermo extra. "
        "The source tests additionally use native Cantera constant-cp H2 for an independently derived "
        "finite-gas isothermal loading limit and the ideal-gas DeltaU=RT-DeltaHdes check.", "",
        f"Native CoolProp {metadata.version('CoolProp')}; SciPy {metadata.version('scipy')}; "
        f"nine complete integrations including three refinements, {elapsed:.6g} s local wall time. "
        "Actual native property objects and actual SciPy OdeResults are retained. No gas EOS or kinetic "
        "correlation is duplicated; the existing HydrideKinetics/VanthoffPlateau/ArrheniusRate are composed.", "",
        "All coefficients below are authored synthetic verification inputs, not fitted to an alloy: "
        "0.002 kg H2 capacity; solid C=1000 J/K; DeltaHdes=24000 J/mol H2 at 300 K, 100000 Pa; "
        "DeltaS=80 J/(mol H2 K); absorption/desorption rates 0.01/0.02 s^-1 at zero activation energy; "
        "free gas volume 0.005 m3; gas-solid conductance 10 W/K; no ambient conductance. "
        "Normal and para fluids keep separate native caloric references. Default absorption starts "
        "at x=0.1, both temperatures 300 K and gas pressure 300000 Pa, absolute clock [100,200] s. "
        "The declared numerical envelope is 200-600 K /1000-1e7 Pa, not an experimental material envelope.", "",
        "Bound-H energy per mole is native h_H2,ref minus DeltaHdes. Gas/solid interface enthalpy "
        "appears with opposite signs, and nominal reaction heat is diagnostic only: it is not added "
        "again to total U. At reference, closed absorption DeltaU=Pv_mol-DeltaHdes, including the "
        "pressure-work distinction from the isobaric reaction enthalpy. Condensed-phase PV and loading-dependent "
        "solid sensible heat are neglected. The constant-DeltaH plateau is matched at the reference only; "
        "full temperature-dependent free-energy/caloric consistency remains future qualification.", "",
        "| Quantity | Observed value |", "|---|---:|",
        f"| Closed uptake final x / gas mass | {fine.snapshots[-1].fraction:.12g} / {fine.snapshots[-1].gas_mass_kg:.12g} kg |",
        f"| Closed uptake final solid / gas T | {fine.snapshots[-1].solid_temperature_k:.12g} / {fine.snapshots[-1].gas.temperature_k:.12g} K |",
        f"| Closed uptake final pressure | {fine.snapshots[-1].gas.pressure_pa:.12g} Pa |",
        f"| Reference DeltaHdes / absorption DeltaU | 24000 / {ref.reference_absorption_internal_energy_j_mol_h2:.12g} J/mol H2 |",
        f"| Maximum closed mass / transfer defects | {max_mass:.12g} / {max_transfer:.12g} kg |",
        f"| Maximum gas/solid/total-U defect | {max_energy:.12g} J |",
        f"| Independent native PT reconstructed mass / U drift | {native_total_mass_drift:.12g} kg / {native_total_energy_drift:.12g} J |",
        f"| Fine nominal sorption heat, not added twice | {fine.integrated_nominal_reaction_heat_j[-1]:.12g} J |",
        f"| Desorption transferred H2 | {release.integrated_hydrogen_uptake_kg[-1]:.12g} kg |",
        f"| Positive gas-floor termination time | {floor.event_time_s:.12g} s |",
        f"| Isothermal total thermostat heat / sampled difference | {integrated_thermostat_heat:.12g} / {thermostat_sampling_difference:.12g} J |",
        f"| Two refinement-pair fraction / solid T / P differences | {fractions} / {temperatures} K / {pressure_differences} Pa |", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "This is software/numerical verification of one finite lumped level, not alloy calibration or measured "
        "validation. Acquired AB2 shell-temperature data still lack resolved pressure/MFC units and bases, "
        "free gas volume/porosity and bed-vs-shell observation roles. None of those values or mappings is inferred here. "
        "No raw/normalized external data, mechanism or third-party implementation is included.", "",
        "The model is closed to external H2 ports and has one uniform gas state plus one solid temperature. "
        "Porous transport, powder expansion, wall storage, loading-dependent heat capacity, full free-energy "
        "equilibrium, connected process ports and independent apparatus qualification remain receiving/research work. "
        "Trial fraction/phase/domain violations fail without clipping. A positive gas-floor root is retained "
        "as termination, not advertised as an exact empty-bed or exhausted-gas event.", "",
        "Primary context: [Brown et al. 2006](https://doi.org/10.1115/FUELCELL2006-97140), "
        "[Krane et al. 2021 primary preprint](https://arxiv.org/abs/2107.06095), "
        "[Leachman et al. hydrogen EOS](https://doi.org/10.1063/1.3160306), "
        "[CoolProp native API](https://coolprop.org/coolprop/LowLevelAPI.html). "
        "Conservation coupling, reference derivation, fixtures and tests are original; no source coefficient "
        "table, figure, implementation or worked example was copied.", "", "## Source fingerprints", "",
        *(f"- `{name}`: `{sha}`" for name, sha in fingerprints.items()), ""]
    (root/"research/finite_hydride.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"Local integration wall time: {elapsed:.6g} s; report: research/finite_hydride.md")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
