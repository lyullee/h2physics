"""Conditional measured-P/T inventory consistency; not independent flow validation."""

import hashlib
import tomllib
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from scipy.integrate import cumulative_trapezoid

from h2physics.core import Origin
from h2physics.data.preslhy import load_discha_member
from h2physics.data.sampling import bin_means
from h2physics.observations import (
    ObservationTable,
    Variable,
    concatenate_observations,
    split_experiments,
)
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.research import BoundedParameter, assess_held_out, fit_observations
from h2physics.thermo import CoolPropProperties


def predict(table, parameters):
    nominal, _ = table.column("nominal_nozzle_loss_fraction")
    return parameters["effective_area_factor"] * nominal


def main():
    root = Path(__file__).resolve().parents[1]
    archive_name = "PRE3P1A_KIT_D1_300K_DATA.zip"
    receipt = tomllib.loads((root / "research/data/preslhy-discharge.toml").read_text(encoding="utf-8"))
    source = next(item for item in receipt["files"] if item["name"] == archive_name)
    if source["status"] not in {"acquired", "cached"}:
        raise RuntimeError("The declared numerical bundle has not been acquired")
    archive = root / "data/raw" / source["relative_path"]
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_hash != source["sha256"]:
        raise RuntimeError("Numerical bundle differs from its acquisition receipt")
    provider = CoolPropProperties("Hydrogen")
    nozzle = HomogeneousIsentropicNozzle(provider)
    volume, reference_pressure = .002815, 101325.
    variables = (Variable("time", "time", "s"),
                 Variable("nominal_nozzle_loss_fraction", "mass_fraction", "1", "window-initial-inventory"),
                 Variable("inferred_inventory_loss_fraction", "mass_fraction", "1", "window-initial-inventory"))
    tables, results, source_rows = [], [], []
    with ZipFile(archive) as container:
        names = sorted(name for name in container.namelist() if name.endswith(".xlsx"))
    expected = {"20190523_144939.xlsx", "20190523_150133.xlsx",
                "20190523_151013.xlsx", "20190523_151618.xlsx"}
    if set(names) != expected:
        raise RuntimeError("Bundle workbook membership changed; review the new source explicitly")
    for name in names:
        case = Path(name).stem
        run = load_discha_member(archive, name, source_id=f"10.35097/1187:{archive_name}:{name}",
            clock_id=f"{case}:publisher-PNoz-onset", pressure_basis="gauge",
            reference_pressure_pa=reference_pressure, include_fast_pressure=True)
        opening = NozzleOpening.circular(case, run.nominal_nozzle_diameter_m, effective_area_factor=1.,
                                         area_basis_id="nominal-area-consistency-reference")
        source_rows.append((case, run.workbook_sha256, run.initial_pressure_pa,
                            run.fast_pressure.series.time_s.size, run.temperatures.series.time_s.size))
        for width in (.2, .1, .05):
            # Identical comparison endpoints for all resolutions. Each center is
            # an explicit arithmetic mean over its own width, not a point sample.
            grid = np.linspace(2., 10., round(8/width)+1)
            edges = np.linspace(2.-width/2, 10.+width/2, len(grid)+1)
            p = bin_means(run.fast_pressure.series, edges, clock_id=run.fast_pressure.series.clock_id,
                          minimum_samples=max(1, int(width/.0005*.45)))
            t = bin_means(run.temperatures.series, edges, clock_id=run.temperatures.series.clock_id,
                          minimum_samples=max(1, int(width/.01*.45)))
            if not np.all(p.series.valid[:, 0]) or not np.all(t.series.valid[:, :3]):
                raise RuntimeError("The declared observation window has insufficient valid sensor coverage")
            pressure = p.series.values[:, 0]
            temperature = t.series.values[:, :3].mean(axis=1)
            states = [provider.state_pt(float(a), float(b)) for a, b in zip(pressure, temperature, strict=True)]
            inventory = volume * np.array([state.density_kg_m3 for state in states])
            rates = []
            for state in states:
                try:
                    result = nozzle.solve(state, back_pressure_pa=reference_pressure, opening=opening)
                except RuntimeError as error:
                    raise RuntimeError(f"{case}, bin={width}, P={state.pressure_pa!r}, "
                                       f"T={state.temperature_k!r}: {error}") from error
                rates.append(result.mass_flow_kg_s)
            flow = np.array(rates)
            cumulative = cumulative_trapezoid(flow, grid, initial=0.)
            loss = inventory[0]-inventory
            inferred_factor = loss[-1]/cumulative[-1]
            spread = float(np.max(np.ptp(t.series.values[:, :3], axis=1)))
            results.append((case, width, inventory[0], loss[-1], cumulative[-1],
                            inferred_factor, spread, int(p.valid_sample_counts[:, 0].min()),
                            int(t.valid_sample_counts[:, :3].min())))
            if width == .1:
                values = np.column_stack((grid, cumulative/inventory[0], loss/inventory[0]))
                table = ObservationTable(values, variables, np.isfinite(values),
                    tuple(f"{case}:bin-{i}" for i in range(len(grid))), (case,)*len(grid),
                    (Origin.RECONSTRUCTED,)*3, run.source_id,
                    (("workbook_sha256", run.workbook_sha256),
                     ("clock", run.ambient.series.clock_id),
                     ("observation_operator", "0.1 s arithmetic bins; three closed-TC mean"),
                     ("volume_m3", repr(volume)), ("gauge_reference_pa", repr(reference_pressure))))
                tables.append(table)
            print(f"{case}, {width:g} s bins: inferred factor={inferred_factor:.8g}", flush=True)
    all_data = concatenate_observations(tables, source_id="PRESLHY-1mm-warm-conditional-inventory")
    # Whole 20-bar experiment is held out; the 200/10/5-bar experiments fit one
    # effective factor. Rows within an integrated curve are strongly correlated.
    partition = split_experiments(all_data, {"20190523_151013"})
    parameter = BoundedParameter("effective_area_factor", .8, .05, 1., 1.)
    fit = fit_observations(partition.fitting, inputs=variables[:2], response=variables[2],
        parameters=(parameter,), predictor=predict, purpose="parameter_estimation",
        model_id="shared-nozzle-conditional-discha-inventory-v1", residual_normalization=.01)
    assessment = assess_held_out(fit, partition.held_out, predictor=predict)
    lines = ["# PRESLHY conditional inventory / nozzle consistency", "",
        "Source: [Jordan, T. (2023), KIT dataset](https://doi.org/10.35097/1187), CC BY 4.0, archive-1. "
        f"Bundle `{archive_name}` SHA-256: `{archive_hash}`.", "",
        "Four different initial-pressure experiments are used. No raw workbook, apparatus "
        "illustration or source explanatory text is redistributed. Source metadata/checksums "
        "are retained in `research/data/preslhy-discharge.toml`.", "",
        "This is a conditional consistency comparison, not independent mass-flow validation. "
        "Inventory is reconstructed from measured pressure and the mean of three closed "
        "vessel thermocouples using CoolProp; the nozzle uses those same P/T inputs and EOS. "
        "Temperature is observed forcing here, not a prediction from the tank energy equation. "
        "Force/balance signals are ingested but excluded from quantitative acceptance because "
        "the source identifies limited accuracy. No statistical uncertainty is inferred from "
        "the many correlated samples or from optimizer rank.", "",
        f"Declared assumptions: rigid volume {volume:g} m³; source pressure interpreted as "
        f"gauge with an assumed ambient reference {reference_pressure:g} Pa; frozen normal "
        f"hydrogen in CoolProp {provider.version} HEOS; no spin conversion. "
        "A barometric record and source spin fraction are not available. The source includes "
        "finite valve/pipework; its losses are folded into an effective-area factor only for "
        "this comparison. A measured line temperature or nozzle-solid temperature is not "
        "silently substituted for reservoir stagnation temperature.", "",
        "The author's synchronized PNoz-onset clocks are retained, with original recorder "
        "elapsed-time channels. No new time shift is estimated. Comparison centers span "
        "2–10 s to avoid initial valve travel. Explicit arithmetic bins use 0.2, 0.1 and "
        "0.05 s widths; both endpoints remain fixed. Counts describe sensor samples, not "
        "independent repeats. No missing/extrapolated bin is accepted. A three-sensor mean "
        "is a declared homogeneous-temperature observation operator, not a spatially resolved state.", "",
        "| Experiment | Workbook SHA-256 | Initial absolute P Pa | Fast-pressure rows | Temperature rows |",
        "|---|---|---:|---:|---:|"]
    lines += [f"| {case} | `{digest}` | {pressure:.12g} | {npres} | {ntemp} |"
              for case, digest, pressure, npres, ntemp in source_rows]
    lines += ["", "| Experiment | Bin s | Initial-window inventory kg | Inferred loss kg | "
              "Nominal-nozzle loss kg | Endpoint effective factor | Max closed-TC spread K | "
              "Min P samples/bin | Min T samples/bin |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    lines += ["| " + " | ".join([row[0], *(f"{value:.12g}" for value in row[1:])]) + " |" for row in results]
    lines += ["", "The endpoint ratio is a diagnostic per experiment. The shared fit below "
        "uses full cumulative curves at 0.1 s resolution, with a declared [0.05, 1] bound. "
        "It is an effective apparatus factor, not an independently calibrated universal nozzle coefficient.", "",
        f"- Fitting groups: {fit.fitting_experiment_ids}.",
        "- Held-out group: 20190523_151013 (approximately 20 bar gauge initially).",
        f"- Fitted factor: {fit.parameter_values['effective_area_factor']:.12g}; active bounds {fit.active_parameter_bounds}.",
        f"- Fitting RMSE: {fit.root_mean_square_error:.12g} of initial-window inventory.",
        f"- Held-out RMSE: {assessment.root_mean_square_error:.12g} of initial-window inventory.",
        f"- Held-out max absolute error: {assessment.maximum_absolute_error:.12g} of initial-window inventory.",
        f"- Fitting/held-out rows: {len(fit.fitting_row_ids)} / {assessment.observation_count}.",
        f"- Input fingerprints: `{fit.fitting_data_sha256}` / `{assessment.observation_data_sha256}`.",
        "", "No domain-qualification threshold is assigned to this exploratory result. "
        "An independent calibrated flow/inventory reference, pressure/temperature uncertainties, "
        "thermocouple response and spatial representativeness, verified ambient/spin basis "
        "and resolved valve/line hydraulics remain required before qualifying discharge physics.",
        "", "Code SHA-256:", ""]
    for name in ("scripts/compare_discha_release.py", "src/h2physics/data/preslhy.py",
                 "src/h2physics/data/sampling.py", "src/h2physics/release.py",
                 "src/h2physics/core.py", "src/h2physics/thermo/coolprop.py"):
        lines.append(f"- `{name}`: `{hashlib.sha256((root/name).read_bytes()).hexdigest()}`")
    (root / "research/discha_inventory_comparison.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    print("conditional held-out inventory RMSE", assessment.root_mean_square_error)


if __name__ == "__main__":
    main()
