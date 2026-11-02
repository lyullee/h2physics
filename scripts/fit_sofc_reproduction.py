"""Demonstrate whole-curve holdout and identifiability diagnostics on open SOFC data.

The collection's measured-versus-modeled curve origin is unresolved. This run
is explicitly curve reproduction, not experimental parameter identification.
"""

import hashlib
import math
from pathlib import Path

import numpy as np

from h2physics.constants import R_J_MOL_K
from h2physics.data.polarization import load_polarization_grid
from h2physics.electrochemistry import OhmicLoss, SymmetricButlerVolmerLoss
from h2physics.observations import concatenate_observations, split_experiments
from h2physics.research import BoundedParameter, assess_held_out, fit_observations


def predict(table, parameters):
    current, _ = table.column("current_density")
    temperature, _ = table.column("temperature")
    activation = SymmetricButlerVolmerLoss(lambda t: parameters["exchange_a_m2"], 1.)
    resistance = OhmicLoss(lambda t: parameters["resistance_ohm_m2"]
                           * math.exp(parameters["resistance_activation_j_mol"]/R_J_MOL_K*(1/t-1/1073.15)))
    return np.array([parameters["reversible_like_v"] + parameters["temperature_coefficient_v_k"]*(t-1073.15)
                     - activation(j, t) - resistance(j, t) for j, t in zip(current, temperature, strict=True)])


def main():
    root = Path(__file__).resolve().parents[1]
    path = next((root / "data/raw/sofc-polarization").rglob("Ui_50H2_10H2O_40N2.txt"))
    source_id = f"10.17632/j8b9v4cb9d.1:{path.name}"
    with path.open(encoding="cp1252", newline="") as source:
        tables = load_polarization_grid(source, source_id=source_id, group_prefix=path.stem,
            temperature_unit="degC", current_density_unit="mA/cm2", voltage_unit="V")
    table = concatenate_observations(tables, source_id=source_id+":all-temperatures")
    held_out_groups = {group for group in table.experiment_ids if group.endswith("T=1073.15K")}
    partition = split_experiments(table, held_out_groups)
    # Declare the comparison target and groups before fitting. These are
    # illustrative reproduction targets, not acceptance for a safety model.
    rmse_limit, maximum_limit = .02, .05
    parameters = (BoundedParameter("reversible_like_v", 1.02, .2, 1.8, 1.),
        BoundedParameter("temperature_coefficient_v_k", -.0003, -.005, .005, .001),
        BoundedParameter("resistance_ohm_m2", 5e-5, 1e-8, 1e-3, 1e-4),
        BoundedParameter("resistance_activation_j_mol", 20000, 0, 100000, 10000),
        BoundedParameter("exchange_a_m2", 10000, .01, 1e7, 10000))
    fit = fit_observations(partition.fitting, inputs=table.variables[:2], response=table.variables[2],
        parameters=parameters, predictor=predict, model_id="sofc-shared-BV-ohmic-reproduction-v1",
        residual_normalization=.01, purpose="curve_reproduction", maximum_function_evaluations=1000)
    comparison = assess_held_out(fit, partition.held_out, predictor=predict)
    passed = comparison.root_mean_square_error <= rmse_limit and comparison.maximum_absolute_error <= maximum_limit
    lines = ["# Open SOFC curve reproduction", "",
        "Source: [Mendeley dataset v1](https://doi.org/10.17632/j8b9v4cb9d.1), CC BY 4.0. "
        "Source filename: `Ui_50H2_10H2O_40N2.txt`. "
        f"Source SHA-256: `{hashlib.sha256(path.read_bytes()).hexdigest()}`.", "",
        "Voltage origin remains unresolved (the collection includes model/experimental "
        "material). This is explicitly curve reproduction, not independent experimental "
        "parameter estimation or qualification. The observation operator reuses the local "
        "symmetric Butler–Volmer and ohmic loss classes. An affine open-circuit-like "
        "temperature term and activated resistance are fitted; these effective coefficients "
        "are not assigned to a particular electrode mechanism or standard reaction energy.", "",
        "The 800 °C curve is held out in full. Curves at 750, 775 and 825 °C are used for fitting. "
        "They share an apparatus/source, so group separation is not independent-source validation. "
        "Residual normalization is 0.01 V for numerical scaling; it is not a measured uncertainty. "
        "The illustrative target, selected in the script before fitting, is RMSE ≤0.02 V "
        "and maximum absolute error ≤0.05 V.", "",
        f"- Fitting observations: {len(fit.fitting_row_ids)}; omitted invalid rows: {len(fit.omitted_row_ids)}.",
        f"- Fitting data fingerprint: `{fit.fitting_data_sha256}`.",
        f"- Held-out observations: {comparison.observation_count}; fingerprint: `{comparison.observation_data_sha256}`.",
        f"- Fitting RMSE: {fit.root_mean_square_error:.9g} V.",
        f"- Held-out RMSE: {comparison.root_mean_square_error:.9g} V.",
        f"- Held-out maximum absolute error: {comparison.maximum_absolute_error:.9g} V.",
        f"- Illustrative reproduction target: {'PASS' if passed else 'FAIL'}.",
        f"- Scaled Jacobian rank: {fit.numerical_rank}/{len(parameters)} at relative threshold {fit.numerical_rank_relative_threshold:g}.",
        f"- Scaled Jacobian condition number: {fit.scaled_condition_number:.9g}.",
        f"- Scaled singular values: {tuple(float(v) for v in fit.scaled_jacobian_singular_values)}.", "",
        "| Effective parameter | Fitted value | Declared lower / upper | Active bound |",
        "|---|---:|---|---:|"]
    for parameter, (_, active) in zip(parameters, fit.active_parameter_bounds, strict=True):
        lines.append(f"| {parameter.name} | {fit.parameter_values[parameter.name]:.10g} | "
                     f"{parameter.lower:g} / {parameter.upper:g} | {active} |")
    lines += ["", "The open-circuit-like coefficient is not a qualified reversible voltage. "
        "No covariance or confidence interval is inferred from fitting residuals. Inspect "
        "rank, conditioning and active bounds before interpreting fitted coefficients. "
        "True thermochemistry, gas activities, observation origin and an independent source "
        "are still required for physical electrochemical validation."]
    (root / "research/sofc_reproduction.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("SOFC curve reproduction", comparison.root_mean_square_error, comparison.maximum_absolute_error,
          "rank", fit.numerical_rank, "target", passed)


if __name__ == "__main__":
    main()
