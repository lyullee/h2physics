"""Exercise the actual pinned native gas expansion and calm axisymmetric jet.

All inputs are authored numerical cases. No external observation, source example,
digitised curve or fitted entrainment coefficient is used by this check.
"""

import argparse
import hashlib
import importlib
import math
import sys
import time
from pathlib import Path

import numpy as np

from h2physics.adapters.degali import (
    SHARED_AREA,
    JetCouplingError,
    JetPlane,
    axisymmetric_boundary,
    expand_nozzle_gas,
    profile_integrated_buoyancy_type,
    run_axisymmetric_jet,
)
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
REVISION = "6ead182dc19039725a0b40811b48c6d39f947790"
NATIVE_SHA = "f84bb2c38e26a507a3e495005f38d8fed097d312f6a47932fe10d3cdb587220a"
# Declared before the refinement runs. Agreement is numerical, not experimental accuracy.
ENDPOINT_FRACTION_AGREEMENT = 5e-4
ENDPOINT_TEMPERATURE_AGREEMENT_K = .1
VERTICAL_FORCE_AGREEMENT = .005
GRIDS = ((81, .01, 2e-6), (161, .005, 2e-7), (321, .0025, 2e-7))


def module_sha(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", type=Path,
                        help="Optional isolated site-packages directory containing pinned DEGALI")
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    if args.native_packages:
        sys.path.insert(0, str(args.native_packages.resolve()))
    native = importlib.import_module("degali")
    axis = importlib.import_module("degali.addons.axisymmetric_jet")
    notional = importlib.import_module("degali.addons.notional")
    eos = importlib.import_module("degali.addons.hydrogen_eos")
    assert native.__version__ == "0.3.0"
    package_hash = module_sha(Path(native.__file__).parent)
    assert package_hash == NATIVE_SHA, "Native module bytes differ from the reviewed snapshot"
    print("native", native.__version__, package_hash, flush=True)
    corrected_type = profile_integrated_buoyancy_type(axis.ConservedGaussianJet)
    report = ["# Native gas-plane and calm-jet integration", "",
        "Authored numerical cases; no independent experimental validation or facility qualification.", "",
        f"Native MIT [DEGALI snapshot](https://github.com/lyullee/degali/tree/{REVISION}), "
        f"package version {native.__version__}, Python-module path/byte SHA-256 `{package_hash}`. "
        "The PyPI 0.1.0 release is not assumed equivalent to this source snapshot.", "",
        "## Model and gates", "",
        "The one shared isentropic nozzle supplies the native ambient-plane expander. "
        "Its effective stream area is explicitly also the pressure-force area. The caller "
        "places a horizontal virtual plane 2 m above declared ground; its axial offset is "
        "not predicted. The upstream pressure is 2 MPa absolute, ambient pressure 101325 Pa, "
        "nominal opening 2 mm and effective area factor 0.8. Normal H2 starts at 300 K; "
        "para-H2 at 100 K. Ambient phase air is dry at 293.15 K and includes argon.", "",
        "The native temperature/mass-fraction profile, equilibrium air condensation, "
        "temperature-dependent component enthalpy, four-flux establishment and consistent "
        "phase ambient are explicit. Entrainment coefficients remain 1.16 / 0.28 / 0.082 "
        "(profile spreading / momentum entrainment / plume cap), radial limit 5 widths. "
        "Fuel cp comes from the pure-fluid ambient reference; declared air cp is 1005 J/kg/K. "
        "Radiation, coflow and the experimental nonideal-mixture-volume correction are off.", "",
        "An original thin native subclass replaces only the vertical flux source by the "
        "actual native radial buoyancy integral. The current upstream analytic density-profile "
        "force is inconsistent with its independent temperature/composition profile. All "
        "profiles, Jacobian, remaining sources and spatial integration remain native. "
        "No density-profile root failure triggers a hidden fallback or fitted coefficient.", "",
        "Default host limits: H2 species 1e-6, horizontal momentum 1e-6, energy 1e-5 "
        "and establishment 1e-7, all relative. Energy is scaled by "
        "mdot*(abs(h_source_model)+v_source^2/2), separately reporting absolute W and "
        "net energy. Native reference interpolation is checked against the public "
        "pure-H2 ideal enthalpy query within 1 J/kg. Refinement targets: endpoint Y "
        f"relative {ENDPOINT_FRACTION_AGREEMENT}, endpoint T {ENDPOINT_TEMPERATURE_AGREEMENT_K} K, "
        f"and sampled vertical-force integral relative {VERTICAL_FORCE_AGREEMENT}. "
        "These thresholds were declared before the authoritative runs.", "",
        "A separate preliminary DOP853/161-point/2e-8 diagnostic completed normal H2 "
        "but its para-H2 run was interrupted after more than 300 observed CPU seconds without "
        "a completed solution. That diagnostic is not a passed result. The declared "
        "authoritative sequence uses RK45 and records its actual residuals.", ""]
    report += ["The first RK45 sequence failed the para-H2 energy gate at 321 points "
        "(0.523570536 W against a 0.237922351 W budget), while species and horizontal "
        "momentum passed. An additional 641-point / 0.00125 m / 2e-7 run is therefore "
        "included for that unresolved case. The conservation and endpoint targets are unchanged.", ""]
    finest_runs = []
    all_passed = True
    for fluid, temperature in (("Hydrogen", 300.), ("ParaHydrogen", 100.)):
        properties = CoolPropProperties(fluid)
        nozzle = HomogeneousIsentropicNozzle(properties).solve(
            properties.state_pt(2e6, temperature), back_pressure_pa=101325.,
            opening=NozzleOpening.circular("authored-jet", .002, effective_area_factor=.8,
                area_basis_id="authored-effective-stream-and-pressure-area"))
        plane = expand_nozzle_gas(nozzle, properties,
            expander=notional.expand_measured_throat_to_ambient,
            location=SourceLocation("authored-gas-plane", "authored-facility-clock", "authored-frame",
                                    (0., 0., 2.), (1., 0., 0.)),
            location_basis_id="authored-virtual-plane-position", pressure_area_policy=SHARED_AREA)
        boundary = axisymmetric_boundary(plane, properties,
            section=JetPlane("authored-frame", (0., 0., 0.), (1., 0., 0.), (0., 0., 1.)),
            ambient_temperature_k=293.15, source_factory=axis.AxisymmetricJetSource,
            enthalpy_factory=axis.SourceEnthalpyBoundary)
        mw_air, humidity, rho_air = axis.phase_ambient_from_rh(293.15, 101325., 0., include_argon=True)
        options = dict(ambient_temperature=293.15, ambient_pressure=101325., ambient_density=rho_air,
            fuel_molecular_weight=.00201588, ambient_molecular_weight=mw_air,
            fuel_heat_capacity=boundary.ambient_reference_state.cp_j_kg_k,
            ambient_heat_capacity=1005., conservative_establishment=True,
            equilibrium_air_condensation=True, temperature_dependent_phase_enthalpy=True,
            hydrogen_enthalpy_species=fluid, equilibrium_argon_condensation=True,
            consistent_phase_ambient=True, ambient_absolute_humidity=humidity)
        reference = eos.hydrogen_gas_departure(293.15, 101325., fluid).ideal_enthalpy
        density_model = axis.ConservedGaussianJet(boundary.native, radial_points=81, **options)
        try:
            density_model.established_initial_state()
            density_failure = "No initialization failure on this environment; inspect residuals"
        except RuntimeError as error:
            density_failure = str(error)
        report += [f"## {fluid}", "",
            f"Mass flow {plane.mass_flow_kg_s:.12g} kg/s; ambient-plane T "
            f"{plane.state.temperature_k:.12g} K, v {plane.velocity_m_s:.12g} m/s, "
            f"diameter {plane.diameter_m:.12g} m. Momentum residual "
            f"{plane.mass_flow_kg_s*plane.velocity_m_s-nozzle.effective_area_thrust_n:.9g} N; "
            f"total-specific-energy residual {plane.state.enthalpy_j_kg+.5*plane.velocity_m_s**2-nozzle.upstream_stagnation.enthalpy_j_kg:.9g} J/kg.", "",
            f"Retained native density-profile initialization: `{density_failure}`.", "",
            "| Radial points | max step / m | rtol | seconds | species rel | horizontal M rel | energy error / W | energy scale / W | gate |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        runs = []
        grids = GRIDS+((641, .00125, 2e-7),) if fluid == "ParaHydrogen" else GRIDS
        for radial_points, step, rtol in grids:
            start = time.perf_counter()
            model = corrected_type(boundary.native, radial_points=radial_points,
                thermodynamic_profile="temperature_mass_fraction", **options)
            try:
                run = run_axisymmetric_jet(model, boundary,
                    ideal_reference_enthalpy_j_kg=reference,
                    solver_options=dict(maximum_distance=.5, maximum_step=step, relative_tolerance=rtol))
            except JetCouplingError as error:
                if error.run is None:
                    raise
                run = error.run
            elapsed = time.perf_counter()-start
            audit = run.audit
            report.append(f"| {radial_points} | {step} | {rtol} | {elapsed:.6g} | "
                f"{audit.maximum_relative_species_error:.9g} | {audit.maximum_relative_horizontal_momentum_error:.9g} | "
                f"{audit.maximum_energy_error_w:.9g} | {audit.energy_scale_w:.9g} | "
                f"{'PASS' if audit.passed else '; '.join(audit.failures)} |")
            print(fluid, radial_points, "seconds", elapsed, "audit", audit, flush=True)
            runs.append(run)
        fine, finest = runs[-2:]
        finest_runs.append(finest)
        fraction_change = abs(finest.native.mass_fraction[-1]/fine.native.mass_fraction[-1]-1)
        temperature_change = abs(finest.native.temperature[-1]-fine.native.temperature[-1])
        states = [finest.native.state_at_s(distance) for distance in finest.native.S]
        forces = np.array([finest.model.buoyancy_force(state) for state in states])
        integral = float(np.trapezoid(forces, finest.native.S))
        vertical = finest.native.momentum_flux*np.sin(finest.native.theta)
        force_error = abs(vertical[-1]-vertical[0]-integral)/max(abs(integral), 1e-12)
        state = states[0]
        analytic_force = math.pi*finest.model.spreading_ratio**2*state[1]**2*axis.GRAVITY*(finest.model.ambient_density-state[2])
        force_bias = analytic_force-finest.model.buoyancy_force(state)
        samples = finest.radial_observations((.1, .3, .5), (0.,), evidence_id="authored-"+fluid)
        passed = (finest.audit.passed and fraction_change <= ENDPOINT_FRACTION_AGREEMENT
                  and temperature_change <= ENDPOINT_TEMPERATURE_AGREEMENT_K
                  and force_error <= VERTICAL_FORCE_AGREEMENT)
        all_passed &= passed
        report += ["", f"Finest run points: {len(finest.native.S)}; establishment S "
            f"{finest.native.S[0]:.12g} m; end S {finest.native.S[-1]:.12g} m. "
            f"Initial ambient entrainment {finest.audit.initial_entrained_air_kg_s:.12g} kg/s; "
            f"minimum evaluated-envelope ground clearance {finest.audit.minimum_ground_clearance_m:.9g} m. "
            f"Enthalpy-gauge difference {finest.audit.reference_enthalpy_error_j_kg:.9g} J/kg.", "",
            f"Source HEOS static h {plane.state.enthalpy_j_kg:.12g} J/kg; ambient real H2 "
            f"reference {boundary.ambient_reference_state.enthalpy_j_kg:.12g} J/kg; "
            f"ambient ideal H2 reference {reference:.12g} J/kg. Native model source h "
            f"{finest.model.source_specific_enthalpy():.12g} J/kg and net source h+KE flux "
            f"{finest.audit.source_total_energy_flux_w:.12g} W. Finest four-flux establishment "
            f"residuals `{finest.model.establishment_residuals}`.", "",
            f"{grids[-2][0]} to {grids[-1][0]}-point/step refinement: endpoint whole-mixture Y relative change "
            f"{fraction_change:.9g}, T change {temperature_change:.9g} K. "
            f"Sampled vertical momentum/force-integral relative difference {force_error:.9g}. "
            f"The original analytic force minus actual integrated force at establishment is "
            f"{force_bias:.9g} N/m. Combined numerical gate: {'PASS' if passed else 'FAIL'}.", "",
            f"Predicted native centreline observations (S, r, whole-mixture Y, bulk rho, T): "
            f"`{samples.values.tolist()}`. Fingerprint `{samples.content_sha256}`.", ""]
    report += ["## Scope and remaining work", "",
        "Mass entrainment is ambient material, not loss of hydrogen. Complete-mixture "
        "Y includes condensate and is not gas-phase mole fraction. Native interpolation "
        "is used for section samples and does not claim conservative interpolation. "
        "The phase model uses component enthalpy/phase tables and a mixture volume closure, "
        "not a complete real multicomponent EOS. Native low-temperature tables and their "
        "continuations remain model limitations. No explicit gravitational-potential-energy "
        "term, spin conversion, crosswind, obstacle, ground impact or finite-release material "
        "clock is added. Passing this short steady calm case cannot qualify a transient "
        "pool plume, a measurement operator, hazard distance or facility design.", "",
        "Request 011 records native force consistency, public section-flux/source contracts, "
        "reference bookkeeping, state injection and phase-aware observations. These checks "
        "do not transfer upstream experimental validation to the authored coupled case.", "",
        "Host SHA-256:", ""]
    for path in ("src/h2physics/adapters/degali.py", "scripts/check_degali_integration.py"):
        report.append(f"- `{path}`: `{hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}`")
    (ROOT/"research/native_degali.md").write_text("\n".join(report)+"\n", encoding="utf-8", newline="\n")
    if args.plot:
        plot_runs(finest_runs)
    assert all_passed, "Numerical targets failed; positive and negative results retained"


def plot_runs(runs):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.3), layout="constrained")
    for run in runs:
        label = run.boundary.gas_plane.state.basis.fluid+f" (audit {'PASS' if run.audit.passed else 'FAIL'})"
        axes[0].plot(run.native.S, run.native.mass_fraction, label=label)
        axes[1].plot(run.native.S, run.native.temperature, label=label)
    axes[0].set(ylabel="Whole-mixture H2 mass fraction / 1", xlabel="Streamline distance / m")
    axes[1].set(ylabel="Centreline temperature / K", xlabel="Streamline distance / m")
    for axis in axes:
        axis.legend()
        axis.grid(alpha=.2)
    figure.suptitle("Authored numerical cases: native calm jet, finest evaluated grids")
    folder = ROOT/"artifacts/degali"
    folder.mkdir(exist_ok=True)
    figure.savefig(folder/"centreline.png", dpi=150)
    plt.close(figure)


if __name__ == "__main__":
    main()
