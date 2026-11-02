"""Conditional, source-flow-conditioned comparison with actual HyTunnel jet scans.

All concentration data stay outside Git. Fixed native coefficients are not
estimated against this dataset. Reported pipe pressure is not silently used as
nozzle stagnation pressure, and ambiguous source rows remain excluded.
"""

import argparse
import hashlib
import importlib
import math
import sys
import time
import tomllib
from collections import Counter
from pathlib import Path

import numpy as np
from check_degali_integration import NATIVE_SHA, REVISION, module_sha

from h2physics.adapters.degali import (
    SHARED_AREA,
    JetCouplingError,
    JetPlane,
    axisymmetric_boundary,
    expand_nozzle_gas,
    hydrogen_energy_gauge_type,
    profile_integrated_buoyancy_type,
    run_axisymmetric_jet,
)
from h2physics.core import Origin
from h2physics.data.hytunnel import load_hytunnel_jet_workbook
from h2physics.jet_observations import observe_native_gas_jet
from h2physics.release import NozzleOpening, SourceLocation
from h2physics.release_inverse import infer_nozzle_stagnation_pressure
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
DATASET = "doi:10.5281/zenodo.4668554"
# Authored error budgets, declared before native comparisons; not source-specified uncertainties.
RMSE_LIMIT, MAXIMUM_ERROR_LIMIT, CENTRELINE_RELATIVE_LIMIT = .02, .05, .25
REFINEMENT_RMSE_LIMIT = .001
GRIDS = ((81, .02, 2e-6), (161, .01, 2e-7), (321, .005, 2e-7))
CASES = (
    ("d1_m5", "002", "1 mm 5g H2 W = 0"),
    ("d1_m1p5", "002", "1 mm 1.5g H2 W = 0"),
    ("d4_m1", "003", "4 mm 1g H2 W=0"),
    ("d4_m2p5", "004", "4 mm 2.5g H2 W = 0"),
    ("d4_m5", "004", "4 mm 5g H2 W = 0"),
)
HELD_OUT = "d4_m5"
SOURCE_FILES = ("src/h2physics/data/hytunnel.py", "src/h2physics/release_inverse.py",
                "src/h2physics/jet_observations.py", "src/h2physics/adapters/degali.py",
                "scripts/compare_hytunnel_jets.py")


def source_hashes():
    return {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCE_FILES}


def main():
    fingerprints = source_hashes()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", type=Path)
    parser.add_argument("--case", choices=[row[0] for row in CASES])
    parser.add_argument("--quick", action="store_true", help="One coarse diagnostic, not the full research gate")
    parser.add_argument("--plot", action="store_true", help="Create original diagnostic plots; requires Matplotlib")
    args = parser.parse_args()
    if args.native_packages:
        sys.path.insert(0, str(args.native_packages.resolve()))
    native = importlib.import_module("degali")
    axis = importlib.import_module("degali.addons.axisymmetric_jet")
    notional = importlib.import_module("degali.addons.notional")
    eos = importlib.import_module("degali.addons.hydrogen_eos")
    assert native.__version__ == "0.3.0" and module_sha(Path(native.__file__).parent) == NATIVE_SHA
    receipt = tomllib.loads((ROOT/"research/data/mechanical-ventilation.toml").read_text(encoding="utf-8"))
    workbooks = {}
    for entry in receipt["files"]:
        if entry["name"].endswith(".xlsx") and "005" not in entry["name"]:
            path = ROOT/"data/raw"/entry["relative_path"]
            loaded = load_hytunnel_jet_workbook(path, source_id=DATASET+"/"+entry["name"])
            assert loaded.source_sha256 == entry["sha256"]
            workbooks[entry["name"][9:12]] = loaded
    all_sheets = [sheet for book in workbooks.values() for sheet in book.sheets]
    counts = Counter(issue.code for sheet in all_sheets for issue in sheet.issues)
    report = ["# Conditional HyTunnel gas-jet comparison", "",
        "This is a conditional external-data comparison, not facility qualification. "
        "Source temperature, effective inlet/area interpretation, dry air, free-field geometry "
        "and point-sample response remain assumptions. Upstream training/data overlap is not established.", "",
        f"[Source dataset](https://doi.org/10.5281/zenodo.4668554), version 4668554, "
        "Joachim Grune and Karsten Sempert, CC BY 4.0. Raw and normalized observations are not redistributed. "
        f"Exact MIT native [DEGALI revision](https://github.com/lyullee/degali/tree/{REVISION}), "
        f"Python-module fingerprint `{NATIVE_SHA}`.", "",
        f"All four concentration workbooks: {len(all_sheets)} worksheets, "
        f"{sum(len(s.observations.values) for s in all_sheets)} spatial sensor rows. "
        f"Retained issue counts: `{dict(counts)}`. A source-sheet He/H2 conflict stays unresolved; "
        "the 1 mm / 1 g/s calm sheet has ambient header/value conflicts and is not repaired automatically. "
        "Repeated coordinate headers can move the sampling line and are retained. Zero readings "
        "are valid observations; negative readings and inconsistent summary order are masked, not clipped.", "",
        "Reported source flow, ambient pressure and ambient temperature are averaged across "
        "distinct scan rows for each configuration; measured scan-row ranges remain reported. "
        "Source H2 stagnation temperature is assumed equal to that mean ambient temperature. "
        "The existing nozzle is inverted for an equivalent inlet pressure at measured nominal "
        "area and mass flow. This conditions the source and does not validate a flow prediction "
        "or infer a measured pressure at an uninstrumented nozzle. The pipe-pressure channel "
        "is retained only for comparison; unresolved line losses are not a fitted discharge coefficient.", "",
        "The ambient virtual plane is explicitly colocated with the physical orifice. "
        "Native four-flux temperature/composition establishment and profile-integrated buoyancy "
        "are used without fitting entrainment coefficients. Dry phase air includes Ar. "
        "The global source-relative measurement plane has z=0; an explicitly unbounded model "
        "avoids inventing a ground elevation. Curved centreline projection uses the actual "
        "native piecewise-linear trajectory. The public analytic native Gaussian profile is "
        "explicitly continued beyond radial flux quadrature; every such tail point is flagged. "
        "No axial extrapolation, condensation-to-gas conversion or suction-probe aperture/response "
        "correction is hidden in the observer.", "",
        "For numerical conditioning only, native flux energy is expressed as E+C*m_H2, "
        "where C is the ambient-plane source kinetic energy per unit mass. The source target "
        "receives the identical H2 reference shift. Native tables, physical profiles and root "
        "solver remain unchanged. All host energy gates convert back to the original physical "
        "reference and retain their original scale and limits. Unshifted native initialization "
        "and a doubled-shift state-invariance comparison are recorded independently.", "",
        f"Authored comparison targets: RMSE <= {RMSE_LIMIT} volume fraction, maximum error "
        f"<= {MAXIMUM_ERROR_LIMIT}, median centreline relative error <= {CENTRELINE_RELATIVE_LIMIT}; "
        f"fine-pair predicted-field RMSE change <= {REFINEMENT_RMSE_LIMIT}. "
        "Complete observation coverage and native conservation are separate gates. "
        f"The whole `{HELD_OUT}` configuration is reserved in the reporting split. "
        "No concentration parameter estimation is performed in either split. Maxima/minima "
        "are recorded fluctuations, not confidence intervals or error weights.", ""]
    all_passed = True
    for key, book_key, sheet_name in CASES:
        if args.case and key != args.case:
            continue
        sheet = next(item for item in workbooks[book_key].sheets if item.sheet_name == sheet_name)
        table = sheet.observations
        _, indices = np.unique(table.column("scan_row")[0], return_index=True)
        inputs, ranges = {}, {}
        for name in ("ambient_pressure", "ambient_temperature", "source_mass_flow",
                     "source_reported_pressure", "nominal_diameter"):
            values, valid = table.column(name)
            assert np.all(valid[indices]), (sheet_name, name, "unresolved source conditions")
            inputs[name] = float(np.mean(values[indices]))
            ranges[name] = (float(np.min(values[indices])), float(np.max(values[indices])))
        assert len(set(table.column("nominal_diameter")[0][indices])) == 1
        props = CoolPropProperties("Hydrogen")
        inferred = infer_nozzle_stagnation_pressure(props,
            observed_mass_flow_kg_s=inputs["source_mass_flow"],
            stagnation_temperature_k=inputs["ambient_temperature"],
            temperature_basis_id="authored assumption: H2 T0 equals mean measured ambient T",
            evidence_id=DATASET+"/"+key+"/measured-flow-conditioning",
            back_pressure_pa=inputs["ambient_pressure"],
            opening=NozzleOpening.circular(key, inputs["nominal_diameter"], effective_area_factor=1.,
                area_basis_id="nominal orifice with inferred equivalent inlet; no fitted contraction factor"),
            pressure_bounds_pa=(inputs["ambient_pressure"], 30e6))
        frame = "HyTunnel-CS:source-relative-Cartesian"
        plane = expand_nozzle_gas(inferred.nozzle, props,
            expander=notional.expand_measured_throat_to_ambient,
            location=SourceLocation(key, "steady-configuration:no-time-axis", frame, (0., 0., 0.), (1., 0., 0.)),
            location_basis_id="authored assumption: virtual ambient plane colocated with observed orifice",
            pressure_area_policy=SHARED_AREA)
        ambient_t, ambient_p = inputs["ambient_temperature"], inputs["ambient_pressure"]
        boundary = axisymmetric_boundary(plane, props,
            section=JetPlane(frame, (0., 0., 0.), (1., 0., 0.), (0., 0., 1.), None),
            ambient_temperature_k=ambient_t, source_factory=axis.AxisymmetricJetSource,
            enthalpy_factory=axis.SourceEnthalpyBoundary)
        mw_air, humidity, rho_air = axis.phase_ambient_from_rh(ambient_t, ambient_p, 0., include_argon=True)
        reference = eos.hydrogen_gas_departure(ambient_t, ambient_p, "Hydrogen").ideal_enthalpy
        points = np.column_stack((table.column("x")[0], table.column("y")[0], np.zeros(len(table.values))))
        observed, observed_valid = table.column("mean_h2_volume_fraction")
        centre = np.isclose(points[:, 1], 0., rtol=0., atol=1e-12)
        BaseJet = profile_integrated_buoyancy_type(axis.ConservedGaussianJet)
        energy_shift = .5*plane.velocity_m_s**2
        Jet = hydrogen_energy_gauge_type(BaseJet, shift_j_kg_h2=energy_shift)
        rows = []
        grids = GRIDS[:1] if args.quick else GRIDS
        model_options = dict(ambient_temperature=ambient_t, ambient_pressure=ambient_p,
            ambient_density=rho_air, fuel_molecular_weight=.00201588, ambient_molecular_weight=mw_air,
            fuel_heat_capacity=boundary.ambient_reference_state.cp_j_kg_k, ambient_heat_capacity=1005.,
            conservative_establishment=True, thermodynamic_profile="temperature_mass_fraction",
            equilibrium_air_condensation=True, temperature_dependent_phase_enthalpy=True,
            hydrogen_enthalpy_species="Hydrogen", equilibrium_argon_condensation=True,
            consistent_phase_ambient=True, ambient_absolute_humidity=humidity)
        original = BaseJet(boundary.native, radial_points=grids[0][0], **model_options)
        try:
            original.established_initial_state()
            original_status = f"closed: {original.establishment_residuals}"
        except RuntimeError as error:
            original_status = str(error)
        first = Jet(boundary.native, radial_points=grids[0][0], **model_options)
        doubled_type = hydrogen_energy_gauge_type(BaseJet, shift_j_kg_h2=2*energy_shift)
        doubled = doubled_type(boundary.native, radial_points=grids[0][0], **model_options)
        gauge_failure = ""
        try:
            first_s, first_state = first.established_initial_state()
            doubled_s, doubled_state = doubled.established_initial_state()
            gauge_state_difference = float(np.max(abs(first_state-doubled_state)/np.maximum(abs(first_state), 1e-6)))
            gauge_invariant = first_s == doubled_s and gauge_state_difference <= 1e-5
        except RuntimeError as error:
            gauge_failure = str(error)
            gauge_state_difference, gauge_invariant = math.nan, False
        report += [f"## {key}: {'held out' if key == HELD_OUT else 'development comparison'}", "",
            f"Source configuration `{sheet_name}`; source table fingerprint `{table.content_sha256}`. "
            f"Distinct scan rows {len(indices)}; mean inputs `{inputs}`; scan ranges `{ranges}`. "
            f"Equivalent inlet pressure {inferred.equivalent_stagnation_pressure_pa:.12g} Pa "
            f"({inferred.origin}); measured pipe pressure mean {inputs['source_reported_pressure']:.12g} Pa. "
            f"Source-flow inversion relative error {inferred.relative_mass_error:.9g}; "
            f"{inferred.forward_evaluations} existing-kernel evaluations. "
            f"Unshifted native initialization: `{original_status}`. Explicit C "
            f"{energy_shift:.12g} J/kg-H2; C versus 2C maximum scaled state difference "
            f"{gauge_state_difference:.9g}, invariance gate {'PASS' if gauge_invariant else 'FAIL'}. "
            f"Additional initialization failure: `{gauge_failure or 'none'}`.", "",
            "| Radial points | seconds | native audit | compared/valid measured | radial tail points | RMSE | max absolute error | median axial relative error |",
            "|---:|---:|---|---:|---:|---:|---:|---:|"]
        for radial, step, rtol in grids:
            start = time.perf_counter()
            model = Jet(boundary.native, radial_points=radial, **model_options)
            try:
                run = run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=reference,
                    solver_options=dict(maximum_distance=float(np.max(points[:, 0]))+.5,
                        minimum_mass_fraction=1e-5, maximum_step=step, relative_tolerance=rtol))
            except JetCouplingError as error:
                if error.run is None:
                    report.append(f"| {radial} | {time.perf_counter()-start:.6g} | {error} | unavailable | unavailable | unavailable | unavailable | unavailable |")
                    print(key, radial, "native initialization/integration failure", error, flush=True)
                    rows.append(None)
                    continue
                run = error.run
            prediction = observe_native_gas_jet(run, points, coordinate_frame_id=frame,
                coordinate_origin=Origin.MEASURED, evidence_id=key+f"-native-{radial}",
                radial_tail_policy="native_gaussian_continuation", allow_failed_run=True)
            predicted, predicted_valid = prediction.observations.column("h2_volume_fraction")
            common = observed_valid & predicted_valid
            residual = predicted[common]-observed[common]
            rmse = float(np.sqrt(np.mean(residual**2)))
            maximum = float(np.max(abs(residual)))
            axial = common & centre & (observed > 0.)
            axial_relative = float(np.median(abs(predicted[axial]/observed[axial]-1)))
            tails = int(np.sum(prediction.observations.column("outside_radial_quadrature")[0] == 1.))
            elapsed = time.perf_counter()-start
            report.append(f"| {radial} | {elapsed:.6g} | {'PASS' if run.audit.passed else '; '.join(run.audit.failures)} | "
                f"{np.sum(common)}/{np.sum(observed_valid)} | {tails} | {rmse:.9g} | {maximum:.9g} | {axial_relative:.9g} |")
            rows.append((run, prediction, rmse, maximum, axial_relative, common))
            print(key, radial, "seconds", elapsed, "audit", run.audit,
                  "RMSE", rmse, "max", maximum, "axial-relative", axial_relative, flush=True)
        if rows[-1] is None:
            all_passed = False
            report += ["", "The finest native case did not produce an auditable result; no field accuracy is inferred.", ""]
            continue
        run, prediction, rmse, maximum, axial_relative, common = rows[-1]
        if len(rows) > 1 and rows[-2] is not None:
            previous = rows[-2][1].observations.column("h2_volume_fraction")[0]
            now = prediction.observations.column("h2_volume_fraction")[0]
            refinement = float(np.sqrt(np.mean((now[common]-previous[common])**2)))
        else:
            refinement = math.nan
        end_to_end_gauge = True
        if key in {"d4_m1", HELD_OUT} and not args.quick:
            doubled_model = doubled_type(boundary.native, radial_points=grids[-1][0], **model_options)
            try:
                doubled_run = run_axisymmetric_jet(doubled_model, boundary,
                    ideal_reference_enthalpy_j_kg=reference,
                    solver_options=dict(maximum_distance=float(np.max(points[:, 0]))+.5,
                        minimum_mass_fraction=1e-5, maximum_step=grids[-1][1], relative_tolerance=grids[-1][2]))
            except JetCouplingError as error:
                doubled_run = error.run
            if doubled_run is None:
                end_to_end_gauge = False
                report += ["", "The doubled-gauge trajectory did not produce a completed native result.", ""]
            else:
                doubled_prediction = observe_native_gas_jet(doubled_run, points, coordinate_frame_id=frame,
                    coordinate_origin=Origin.MEASURED, evidence_id=key+"-double-gauge",
                    radial_tail_policy="native_gaussian_continuation", allow_failed_run=True)
                double_phi, double_valid = doubled_prediction.observations.column("h2_volume_fraction")
                base_phi = prediction.observations.column("h2_volume_fraction")[0]
                covered = common & double_valid
                field_change = float(np.sqrt(np.mean((double_phi[covered]-base_phi[covered])**2)))
                end_to_end_gauge = (np.all(double_valid[observed_valid]) and field_change <= REFINEMENT_RMSE_LIMIT
                                   and doubled_run.audit.passed == run.audit.passed)
                report += ["", f"Full C versus 2C trajectory/observer RMSE change {field_change:.9g}; "
                    f"unchanged-reference native audit statuses {run.audit.passed}/{doubled_run.audit.passed}; "
                    f"full-path gauge-invariance gate {'PASS' if end_to_end_gauge else 'FAIL'}. "
                    f"Doubled-gauge physical maximum energy error {doubled_run.audit.maximum_energy_error_w:.9g} W.", ""]
        passed = (not args.quick and gauge_invariant and run.audit.passed and np.all(common[observed_valid])
                  and rmse <= RMSE_LIMIT and maximum <= MAXIMUM_ERROR_LIMIT
                  and axial_relative <= CENTRELINE_RELATIVE_LIMIT and refinement <= REFINEMENT_RMSE_LIMIT
                  and end_to_end_gauge)
        all_passed &= passed
        report += ["", f"Finest audit `{run.audit}`. Fine-pair predicted-field RMSE change "
            f"{refinement:.9g}; authored combined gate {'PASS' if passed else 'FAIL'}. "
            f"Invalid prediction reasons `{dict(Counter(reason for reason in prediction.invalid_reasons if reason))}`. "
            f"Predicted observation fingerprint `{prediction.observations.content_sha256}`. "
            "Independent experimental/facility qualification remains false.", ""]
        if args.plot:
            plot_case(key, sheet, prediction, run, passed)
    report += ["## Scope", "",
        "The source-area/temperature/pressure inversion and virtual-plane placement are "
        "conditional assumptions; this is not a resolved supply-line loss or nozzle calibration. "
        "The selected native model is steady and calm. Wind/stratification/wall, finite-release "
        "material clocks, probe dynamics, ambient humidity and complete independent qualification "
        "remain open. The dataset's flow-velocity workbook is not a uniform wind boundary. "
        "Do not replace its spatially varying co/counter/cross flow by this calm prediction.", ""]
    report += ["Host SHA-256:", ""]
    for path, digest in fingerprints.items():
        report.append(f"- `{path}`: `{digest}`")
    if source_hashes() != fingerprints:
        report += ["", "FAIL: host source files changed during this run; start-of-run fingerprints retained."]
        all_passed = False
    destination = (ROOT/"artifacts/mechanical_ventilation"/f"comparison-{args.case or 'all'}-{'quick' if args.quick else 'full'}.md"
                   if args.case or args.quick else ROOT/"research/hytunnel_jets.md")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text("\n".join(report)+"\n", encoding="utf-8", newline="\n")
    assert all_passed, "Declared comparison/numerical targets failed; report retained"


def plot_case(key, sheet, prediction, run, passed):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    data = sheet.observations
    observed, valid_observed = data.column("mean_h2_volume_fraction")
    predicted, valid_predicted = prediction.observations.column("h2_volume_fraction")
    common = valid_observed & valid_predicted
    x, y = data.column("x")[0], data.column("y")[0]
    centre = common & np.isclose(y, 0., rtol=0., atol=1e-12)
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.8), layout="constrained")
    axes[0].plot(x[centre], 100*observed[centre], "o", label="Measured mean in source plane")
    axes[0].plot(x[centre], 100*predicted[centre], "-", label="Native model point observer")
    axes[0].set(xlabel="Distance from physical orifice / m", ylabel="H2 gas volume fraction / %")
    axes[0].legend(fontsize=8)
    upper = 100*max(float(np.max(observed[common])), float(np.max(predicted[common])))
    colour = axes[1].scatter(100*observed[common], 100*predicted[common], c=x[common], s=16)
    axes[1].plot([0., upper], [0., upper], "k--", linewidth=.8)
    axes[1].set(xlabel="Measured mean / vol. %", ylabel="Predicted point value / vol. %")
    figure.colorbar(colour, ax=axes[1], label="Distance from orifice / m")
    for axis in axes:
        axis.grid(alpha=.2)
    figure.suptitle(f"{key}: conditional calm-jet comparison; numerical audit "
                   f"{'PASS' if run.audit.passed else 'FAIL'}; comparison {'PASS' if passed else 'FAIL'}", fontsize=11)
    figure.supxlabel("Data: Grune & Sempert, doi:10.5281/zenodo.4668554, CC BY 4.0. "
                     "Original derived plot; T0=ambient and unbounded dry point model are assumptions.", fontsize=7)
    folder = ROOT/"artifacts/mechanical_ventilation"
    folder.mkdir(exist_ok=True)
    figure.savefig(folder/(key+"-comparison.png"), dpi=150)
    plt.close(figure)


if __name__ == "__main__":
    main()
