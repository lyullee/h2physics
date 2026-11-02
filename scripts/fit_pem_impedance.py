"""Fit one measured whole-cell sweep, assess complete repeats and cell transfer.

Run check_pem_ingestion.py first. Native impedance.py owns all circuit physics.
Selection and illustrative diagnostic gates below precede every numerical fit.
"""

import hashlib
import importlib.metadata
from pathlib import Path

import numpy as np
from check_pem_ingestion import MEMBERS, ROOT, read_cache
from impedance.models.circuits import CustomCircuit

from h2physics.adapters import PemOhmicLossBinding
from h2physics.adapters.impedance import NativeCircuitOperator
from h2physics.data.pem import pem_spectra
from h2physics.impedance import COMPONENT, FREQUENCY, IMPEDANCE
from h2physics.research import BoundedParameter, assess_held_out, fit_observations

CIRCUIT = "L0-R0-p(R1,CPE1)"
PARAMETERS = (
    BoundedParameter("L0", 1e-6, 0., 1e-4, 1e-6),
    BoundedParameter("R0", .05, 1e-5, 10., .05),
    BoundedParameter("R1", .05, 1e-6, 10., .05),
    BoundedParameter("CPE1_0", .1, 1e-7, 1e4, .1),
    BoundedParameter("CPE1_1", .9, .1, 1., 1.),
)


def complex_metrics(spectrum, predicted):
    valid = spectrum.valid
    error = predicted[valid]-spectrum.impedance_ohm[valid]
    return float(np.sqrt(np.mean(abs(error)**2))), float(np.max(abs(error)))


def diagnostic_limit(spectrum):
    # A research comparison target, not sensor uncertainty or a safety acceptance rule.
    return max(.001, .02*float(np.mean(abs(spectrum.impedance_ohm[spectrum.valid]))))


def main():
    version = importlib.metadata.version("impedance")
    if version != "1.7.1":
        raise ValueError("This replay profile requires the recorded impedance 1.7.1 release")
    operator = NativeCircuitOperator(CustomCircuit, circuit=CIRCUIT,
        parameter_names=tuple(p.name for p in PARAMETERS),
        parameter_units=("H", "Ohm", "Ohm", "Ohm^-1 sec^a", ""))
    frequency = np.geomspace(100., 10000., 23)
    analytic_parameters = dict(zip(operator.parameter_names, (1e-6, .1, .2, .05, 1.), strict=True))
    native = operator.evaluate(frequency, analytic_parameters)
    omega = 2*np.pi*frequency
    analytic = .1+1j*omega*1e-6+.2/(1+1j*omega*.2*.05)
    analytic_error = float(np.max(abs(native.impedance_ohm-analytic)))
    assert analytic_error < 1e-14
    module_root = Path(importlib.metadata.distribution("impedance").locate_file("impedance"))
    source_digest = hashlib.sha256()
    for path in sorted(module_root.rglob("*.py")):
        source_digest.update(path.relative_to(module_root).as_posix().encode())
        source_digest.update(path.read_bytes())
    lines = ["# Measured PEM whole-spectrum parameter estimation", "",
        "Data: Steffen Brundiers (2026), [version v1](https://doi.org/10.5281/zenodo.19361280), "
        "CC BY 4.0. Archive/member hashes and canonical channels: [ingestion audit](pem_ingestion.md). "
        "These are measured cell responses; complex Z is reconstructed from reported magnitude/phase.", "",
        "The optional MIT [impedance.py](https://doi.org/10.21105/joss.02349) dependency owns "
        "the selected circuit, parser and elements. The actual installed CustomCircuit is "
        "injected into NativeCircuitOperator; the existing SciPy least-squares/SVD and "
        "whole-group comparison API owns estimation/diagnostics. No native circuit solver "
        "or fitting implementation is copied or replaced.", "",
        f"- Native release: `{version}`; all installed package .py files, sorted relative "
        f"path plus bytes SHA-256: `{source_digest.hexdigest()}`.",
        f"- Analytic alpha=1 series-L/R + parallel-RC limit: maximum error {analytic_error:.9g} ohm.",
        f"- Circuit: `{CIRCUIT}`; native names/units: {tuple(zip(native.parameter_names, native.parameter_units, strict=True))}.", "",
        "Selection is fixed before fitting: the first complete spectrum with reconstructed "
        "DC current in [11.8,12.2] A in POL_GEIS counter 1 of each cell. The other complete "
        "12 A spectra in counters 1/2 are held out in their entirety. Missing DC context "
        "is not guessed from AC current. Frequencies are used as acquired, without dropping "
        "unfavorable points or extending the approximately 100–10000 Hz measured band. "
        "Adjacent DC context is limited to the same source protocol with a maximum 120 s gap.", "",
        "The five bounded effective parameters use the same fixed starting values in all "
        "cells. Residual normalization 0.01 ohm is only numerical scaling. Real/imaginary "
        "parts are correlated projections of each complex reading; 46 Cartesian rows are "
        "23 complex observations, not 46 independent experiments. No uncertainty or "
        "confidence interval is manufactured from residuals.", "",
        "The predeclared illustrative complex-RMSE target is max(0.001 ohm, 0.02 mean|Z|) "
        "on each assessed whole sweep. PASS/FAIL is a diagnostic comparison only. Repeat "
        "protocols are the same cell/bench, and the four cells come from one source. "
        "None establishes independent-source or facility qualification.", "",
        "| Parameter | Start | Lower | Upper | Numerical scale |",
        "|---|---:|---:|---:|---:|"]
    lines += [f"| {p.name} | {p.initial:g} | {p.lower:g} | {p.upper:g} | {p.scale:g} |" for p in PARAMETERS]
    fitted = {}
    plotting = []
    for member in MEMBERS:
        cell = member.removesuffix("_dataset.csv")
        experiment = read_cache(member)
        spectra = [item for item in pem_spectra(experiment, maximum_dc_gap_s=120.)
                   if item.dc_current_a is not None and 11.8 <= item.dc_current_a <= 12.2
                   and np.all(item.spectrum.valid) and len(item.spectrum.frequency_hz) >= 10]
        fitting = [item for item in spectra if "/POL_GEIS/1/" in item.spectrum.experiment_id]
        if not fitting:
            lines += ["", f"## {cell}", "", "No eligible counter-1 spectrum: estimation omitted."]
            continue
        selected = fitting[0]
        table = selected.spectrum.cartesian_observations()
        fit = fit_observations(table, inputs=(FREQUENCY, COMPONENT), response=IMPEDANCE,
            parameters=PARAMETERS, predictor=operator, model_id="native-impedance-1.7.1/"+CIRCUIT,
            residual_normalization=.01, purpose="parameter_estimation", maximum_function_evaluations=2000)
        try:
            ohmic_binding = PemOhmicLossBinding.from_fit(
                experiment, selected, fit, parameter_name="R0",
                interpretation_id="researcher-approved-whole-cell-effective-R0-as-static-ohmic-loss",
                expected_model_id="native-impedance-1.7.1/"+CIRCUIT,
            )
            bridge_rejection = None
        except ValueError as error:
            ohmic_binding = None
            bridge_rejection = str(error)
        fitted[cell] = (fit, selected)
        predicted = operator.evaluate(selected.spectrum.frequency_hz, fit.parameter_values).impedance_ohm
        rmse, maximum = complex_metrics(selected.spectrum, predicted)
        # This demonstrates direct parameter-object reuse in the shared static core.
        if ohmic_binding is None:
            area_resistance = equivalent_loss = None
        else:
            area_resistance = ohmic_binding.area_resistance_ohm_m2
            stack_losses = ohmic_binding.extend_loss_mapping(
                {}, component_id="pem-eis-effective-r0",
            )
            equivalent_loss = stack_losses["pem-eis-effective-r0"](
                selected.dc_current_a/experiment.active_area_m2,
                selected.block_temperature_k,
            )
            assert np.isclose(equivalent_loss, selected.dc_current_a*fit.parameter_values["R0"])
        lines += ["", f"## {cell}", "",
            f"Fitted sweep: `{selected.spectrum.experiment_id}`; DC {selected.dc_current_a:.9g} A, "
            f"{selected.dc_voltage_v:.9g} V; block {selected.block_temperature_k:.9g} K; "
            f"cathode {selected.cathode_pressure_pa:.9g} Pa absolute. "
            "Block temperature is not a known reaction temperature.", "",
            f"- Cartesian input fingerprint: `{fit.fitting_data_sha256}`.",
            f"- Complex fitting RMSE / max error: {rmse:.9g} / {maximum:.9g} ohm.",
            f"- Scaled Jacobian rank: {fit.numerical_rank}/5; condition: {fit.scaled_condition_number:.9g}; "
            f"evaluations: {fit.function_evaluations}.",
            f"- Scaled singular values: {tuple(float(v) for v in fit.scaled_jacobian_singular_values)}.",
            f"- Active bounds: {fit.active_parameter_bounds}.",
            (f"- Effective R0×area: {area_resistance:.9g} ohm m2; shared OhmicLoss at the "
             f"selected DC current: {equivalent_loss:.9g} V. This includes unresolved contact/lead "
             "and cell contributions; it is not membrane resistivity or a qualified DC loss."
             if ohmic_binding is not None else
             f"- PEM-to-stack loss bridge withheld: {bridge_rejection}. Fit and whole-sweep "
             "diagnostics remain available; no DC loss was transferred."), "",
            *((f"- Typed stack-loss binding: `{ohmic_binding.interpretation_id}`; source member SHA-256 `{ohmic_binding.source_member_sha256}`; fit SHA-256 `{ohmic_binding.fitting_data_sha256}`; DC rows `{ohmic_binding.dc_context_row_ids}`; pressure `{ohmic_binding.effective_pressure_pa:.9g} Pa absolute.", "")
              if ohmic_binding is not None else ()),
            "| Effective native parameter | Estimate |", "|---|---:|"]
        lines += [f"| {name} | {value:.12g} |" for name, value in fit.parameter_values.items()]
        lines += ["", "| Held-out whole sweep | Cartesian SHA-256 | Complex RMSE / max (ohm) | Target (ohm) | Result |",
                  "|---|---|---:|---:|---|"]
        held = []
        for item in spectra:
            if item is selected:
                continue
            comparison = assess_held_out(fit, item.spectrum.cartesian_observations(), predictor=operator)
            prediction = operator.evaluate(item.spectrum.frequency_hz, fit.parameter_values).impedance_ohm
            error, maximum = complex_metrics(item.spectrum, prediction)
            assert np.isclose(error, np.sqrt(2.)*comparison.root_mean_square_error)
            limit = diagnostic_limit(item.spectrum)
            lines.append(f"| `{item.spectrum.experiment_id}` | `{comparison.observation_data_sha256}` | "
                         f"{error:.9g} / {maximum:.9g} | {limit:.9g} | {'PASS' if error <= limit else 'FAIL'} |")
            held.append(item.spectrum)
        plotting.append((cell, selected.spectrum, predicted, held))
        print(cell, "complex fitting RMSE", rmse, "condition", fit.scaled_condition_number,
              "held-out", len(held), flush=True)
    if "Reference" in fitted:
        lines += ["", "## Fixed Reference coefficients transferred to different cells", "",
            "These predictions do not refit the target cells. Materials differ and all cells "
            "share a source; the exercise tests parameter portability, without claiming "
            "universal coefficients or independent-source validation.", "",
            "| Target cell first eligible sweep | Complex RMSE / max (ohm) | Target (ohm) | Result |",
            "|---|---:|---:|---|"]
        reference_fit = fitted["Reference"][0]
        for cell, (_, selected) in fitted.items():
            if cell == "Reference":
                continue
            comparison = assess_held_out(reference_fit, selected.spectrum.cartesian_observations(), predictor=operator)
            prediction = operator.evaluate(selected.spectrum.frequency_hz, reference_fit.parameter_values).impedance_ohm
            error, maximum = complex_metrics(selected.spectrum, prediction)
            limit = diagnostic_limit(selected.spectrum)
            lines.append(f"| {cell}: `{selected.spectrum.experiment_id}` | {error:.9g} / {maximum:.9g} | "
                         f"{limit:.9g} | {'PASS' if error <= limit else 'FAIL'} |")
    lines += ["", "The finite measured band cannot establish a unique charge-transfer, diffusion, "
        "membrane, catalyst or aging mechanism. CPE Q has alpha-dependent units and is not "
        "an ordinary capacitance unless alpha=1. An active bound or ill-conditioned Jacobian "
        "restricts parameter interpretation even when the curve fits. Linear/time-invariant "
        "behavior and Kramers–Kronig consistency have not been qualified by this replay. "
        "No crossover flux, degradation law, true reversible voltage or stack thermal "
        "inventory is inferred from this small-signal circuit.", "", "Host code SHA-256:", ""]
    for relative in ("src/h2physics/impedance.py", "src/h2physics/data/pem.py",
                     "src/h2physics/adapters/impedance.py", "scripts/fit_pem_impedance.py"):
        lines.append(f"- `{relative}`: `{hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()}`")
    (ROOT/"research/pem_impedance.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    plot_fits(plotting)


def plot_fits(cases):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    for axis, (cell, spectrum, prediction, held) in zip(axes.flat, cases, strict=False):
        axis.plot(1e3*spectrum.impedance_ohm.real, -1e3*spectrum.impedance_ohm.imag,
                  "o", ms=4, label="Fit data (one sweep)")
        axis.plot(1e3*prediction.real, -1e3*prediction.imag, "-", label="Native circuit")
        for item in held:
            axis.plot(1e3*item.impedance_ohm.real, -1e3*item.impedance_ohm.imag, ".", alpha=.6,
                      label="Holdout "+item.experiment_id.split("/POL_GEIS/")[-1])
        axis.set(title=cell, xlabel="Re(Z) / milliohm", ylabel="-Im(Z) / milliohm")
        axis.axhline(0., color="grey", lw=.5)
        axis.grid(alpha=.2)
        axis.legend(fontsize=8)
    figure.suptitle("Measured PEM cell EIS: 12 A; approximately 100–10000 Hz\n"
                    "Brundiers (2026), DOI 10.5281/zenodo.19361280, CC BY 4.0")
    figure.savefig(ROOT/"artifacts/pem_eis/fits.png", dpi=150)
    plt.close(figure)


if __name__ == "__main__":
    main()
