"""Actual native hydrogen uncertainty propagation with independent quadrature."""

import argparse
import hashlib
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy import stats

from h2physics.core import Origin
from h2physics.observations import Variable
from h2physics.thermo.coolprop import CoolPropProperties
from h2physics.uncertainty import (
    IndependentParameterSpace,
    ModelOutput,
    ParameterDistribution,
    UncertainModel,
    UncertaintyEvaluationError,
    UncertaintyEvidence,
    independent_qmc_design,
    propagate,
    sobol_sensitivity,
)


def authored_hydrogen_case():
    provider = CoolPropProperties("Hydrogen")
    parameters = (
        (Variable("pressure", "pressure", "Pa", "absolute"), 1e7, 3e7),
        (Variable("temperature", "temperature", "K"), 280.0, 330.0),
        (Variable("volume", "volume", "m3", "rigid-free-gas-volume"), 0.008, 0.012),
    )
    space = IndependentParameterSpace(
        tuple(
            ParameterDistribution(
                variable,
                stats.uniform(loc=low, scale=high - low),
                "authored-uniform:" + variable.name,
                "synthetic-warm-inventory",
                Origin.SYNTHETIC,
                low,
                high,
            )
            for variable, low, high in parameters
        ),
        "authored-independent-PTV",
        "warm-normal-H2-HEOS",
    )
    basis = provider.basis

    def callback(p):
        state = provider.state_pt(p["pressure"], p["temperature"])
        basis.require_compatible(state.basis)
        if state.phase not in {"gas", "supercritical", "supercritical_gas"}:
            raise ValueError("authored warm single-fluid domain rejected")
        mass = p["volume"] * state.density_kg_m3
        return ModelOutput(
            {"mass": mass, "internal_energy": mass * state.internal_energy_j_kg}, state
        )

    model = UncertainModel(
        callback,
        (
            Variable("mass", "mass", "kg", basis.fluid + ":" + basis.spin_composition),
            Variable("internal_energy", "internal_energy", "J", basis.reference_id),
        ),
        UncertaintyEvidence(
            "native-HEOS-rigid-hydrogen-inventory",
            "existing-CoolPropProperties",
            "native-stateless-PT-query",
            "authored-independent-input-laws",
            Origin.SYNTHETIC,
        ),
    )
    return provider, space, model


def quadrature_reference(space, model, order):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    moments, seconds = np.zeros(len(model.outputs)), np.zeros(len(model.outputs))
    for i in range(order):
        for j in range(order):
            for k in range(order):
                positions = (i, j, k)
                values = {
                    p.variable.name: p.admitted_minimum
                    + (p.admitted_maximum - p.admitted_minimum) * (nodes[n] + 1) / 2
                    for p, n in zip(space.parameters, positions, strict=True)
                }
                output = model.callback(values).values
                y = np.array([output[v.name] for v in model.outputs])
                weight = weights[i] * weights[j] * weights[k] / 8
                moments += weight * y
                seconds += weight * y * y
    return moments, seconds - moments * moments


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=Path("research/uncertainty.md"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = (
        "src/h2physics/uncertainty.py",
        "tests/test_uncertainty.py",
        "scripts/check_uncertainty.py",
        "docs/UNCERTAINTY.md",
        "src/h2physics/core.py",
        "src/h2physics/observations.py",
        "src/h2physics/thermo/coolprop.py",
    )

    def hashes():
        return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}

    before = hashes()
    import CoolProp
    import CoolProp.CoolProp as cp
    import scipy
    import scipy.stats._qmc as qmc_module
    import scipy.stats._sensitivity_analysis as sensitivity_module

    native_paths = {
        "SciPy sensitivity source": Path(sensitivity_module.__file__),
        "SciPy QMC source": Path(qmc_module.__file__),
        "CoolProp compiled library": Path(cp.__file__),
    }
    native_before = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in native_paths.items()}
    start = perf_counter()
    provider, space, model = authored_hydrogen_case()
    design = independent_qmc_design(space, power=12, seed=2701)
    propagation = propagate(design, model)
    summary = propagation.summarize((0.05, 0.5, 0.95))
    mean_ref, var_ref = quadrature_reference(space, model, 10)
    mean_check, var_check = quadrature_reference(space, model, 14)
    sensitivity = sobol_sensitivity(space, model, power=12, seed=2702)
    refined = sobol_sensitivity(space, model, power=13, seed=2703)
    relative_mean = np.max(abs(summary.mean / mean_ref - 1))
    relative_variance = np.max(abs(summary.population_variance / var_ref - 1))
    quadrature_change = max(
        np.max(abs(mean_check / mean_ref - 1)), np.max(abs(var_check / var_ref - 1))
    )
    index_change = max(
        np.max(abs(sensitivity.first_order - refined.first_order)),
        np.max(abs(sensitivity.total_order - refined.total_order)),
    )
    analytic_space = IndependentParameterSpace(
        tuple(
            ParameterDistribution(
                Variable(f"x{i}", "authored_dimensionless", "1"),
                stats.uniform(),
                "uniform01",
                "authored-analytic-limit",
                Origin.SYNTHETIC,
                0.0,
                1.0,
            )
            for i in range(2)
        ),
        "authored-independent",
        "analytic-variance-reference",
    )
    evidence = UncertaintyEvidence(
        "analytic-reference", "original", "stateless", "not-measured", Origin.SYNTHETIC
    )
    analytic_model = UncertainModel(
        lambda p: {"sum": p["x0"] + 3 * p["x1"], "product": p["x0"] * p["x1"]},
        (Variable("sum", "dimensionless", "1"), Variable("product", "dimensionless", "1")),
        evidence,
    )
    analytic = sobol_sensitivity(analytic_space, analytic_model, power=12, seed=729)
    first_error = np.max(abs(analytic.first_order - np.array([[0.1, 0.9], [3 / 7, 3 / 7]])))
    total_error = np.max(abs(analytic.total_order - np.array([[0.1, 0.9], [4 / 7, 4 / 7]])))
    one_space = IndependentParameterSpace(
        (analytic_space.parameters[0],), "authored-single-input", "native-scalar-failure"
    )
    one_model = UncertainModel(
        lambda p: {"sum": p["x0"]}, (Variable("sum", "dimensionless", "1"),), evidence
    )
    try:
        sobol_sensitivity(one_space, one_model, power=4, seed=17)
    except UncertaintyEvaluationError as exc:
        scalar_error = str(exc)
        scalar_retained = len(exc.completed_evaluations) == 48 and isinstance(
            exc.__cause__, TypeError
        )
    else:
        scalar_error, scalar_retained = "Native failure changed; review required", False
    failing_calls = 0

    def failed_model(p):
        nonlocal failing_calls
        failing_calls += 1
        if failing_calls == 4:
            raise RuntimeError("authored physical domain rejection")
        return {"mass": p["pressure"]}

    failed = UncertainModel(failed_model, (Variable("mass", "diagnostic", "1"),), evidence)
    try:
        propagate(design, failed)
    except UncertaintyEvaluationError as exc:
        failure_retained = len(exc.completed_evaluations) == 3 and isinstance(
            exc.__cause__, RuntimeError
        )
    else:
        failure_retained = False
    last_native = {}

    def invalid_response(p):
        physical = model.callback(p)
        last_native["raw"] = physical.raw
        return ModelOutput({"mass": np.nan, "internal_energy": 0.0}, physical.raw)

    invalid = UncertainModel(invalid_response, model.outputs, model.evidence)
    try:
        propagate(design, invalid)
    except UncertaintyEvaluationError as exc:
        invalid_raw_retained = (
            exc.failed_raw is last_native["raw"]
            and exc.failed_raw.basis == provider.basis
            and np.isnan(exc.failed_output_values["mass"])
        )
    else:
        invalid_raw_retained = False
    native_after = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in native_paths.items()}
    after = hashes()
    gates = {
        "host/native executed sources unchanged": before == after and native_before == native_after,
        "all4096 native QMC coordinates retained without thinning": len(propagation.evaluations)
        == 4096,
        "actual normal-H2 HEOS/native provider and immutable physical snapshots": provider.basis.spin_composition
        == "normal"
        and all(e.raw.basis == provider.basis for e in propagation.evaluations),
        "two independent tensor orders agree below1e-10relative": quadrature_change < 1e-10,
        "native QMC means agree with independent quadrature below1e-5relative": relative_mean
        < 1e-5,
        "native QMC variances agree below5e-4relative": relative_variance < 5e-4,
        "native Saltelli cases retained at both4096/8192 base sizes": len(sensitivity.evaluations)
        == 20480
        and len(refined.evaluations) == 40960,
        "independent-seed/base2 index change below2e-3": index_change < 2e-3,
        "native additive/product first-order limits below1e-3": first_error < 1e-3,
        "native additive/product total-order limits below1e-3": total_error < 1e-3,
        "one-input-one-output native failure retains all actual cases": scalar_retained,
        "physical callback failure retains accepted prefix and cause": failure_retained,
        "invalid returned response retains actual native ThermoState and raw values": invalid_raw_retained,
    }
    elapsed = perf_counter() - start
    lines = [
        "# Native uncertainty propagation verification",
        "",
        f"Actual SciPy{scipy.__version__}, NumPy{np.__version__}, CoolProp{CoolProp.__version__}; {elapsed:.9g}s.",
        "",
        "Authored independent uniform P10–30MPa, T280–330K and rigid free volume8–12L; "
        "normal hydrogen, existing native HEOS/default reference. No measured uncertainty, "
        "sensor/material covariance, vessel rating or facility qualification is implied.",
        "",
        "| Output | QMC mean | Quadrature mean | QMC population variance | Quadrature variance | 5% | Median | 95% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        *(
            f"| {v.name} [{v.unit}] | {summary.mean[i]:.12g} | {mean_ref[i]:.12g} | "
            f"{summary.population_variance[i]:.12g} | {var_ref[i]:.12g} | "
            f"{summary.quantiles[0, i]:.12g} | {summary.quantiles[1, i]:.12g} | {summary.quantiles[2, i]:.12g} |"
            for i, v in enumerate(model.outputs)
        ),
        "",
        f"Mean defect={relative_mean:.9g}relative; variance defect={relative_variance:.9g}relative; "
        f"tensor10/14 change={quadrature_change:.9g}relative; independent-seed4096/8192 maximum index change={index_change:.9g}.",
        "",
        "| Output | Parameter | First order4096 | Total order4096 | First order8192 | Total order8192 |",
        "|---|---|---:|---:|---:|---:|",
        *(
            f"| {v.name} | {p.variable.name} | {sensitivity.first_order[i, j]:.12g} | "
            f"{sensitivity.total_order[i, j]:.12g} | {refined.first_order[i, j]:.12g} | {refined.total_order[i, j]:.12g} |"
            for i, v in enumerate(model.outputs)
            for j, p in enumerate(space.parameters)
        ),
        "",
        "Indices retain native finite-sample values without clipping. Quantiles are sample "
        "quadrature summaries, not confidence limits or annual frequencies. "
        "Actual native/model objects, full coordinate/response snapshots and raw ThermoState "
        "objects remain available in the Python results. No EOS/table/transport solver is duplicated.",
        "",
        f"Retained actual single-input/single-output native cause: `{scalar_error}`. "
        "All48 model cases survive; no dummy dimension/output or alternate estimator is inserted.",
        "",
        "| Numerical gate | Pass |",
        "|---|---|",
        *(f"| {name} | {bool(passed)} |" for name, passed in gates.items()),
        "",
        "| Native input | Begin SHA256 | End SHA256 |",
        "|---|---|---|",
        *(f"| {n} | `{h}` | `{native_after[n]}` |" for n, h in native_before.items()),
        "",
        "| Executed host input | Begin SHA256 | End SHA256 |",
        "|---|---|---|",
        *(f"| `{p}` | `{h}` | `{after[p]}` |" for p, h in before.items()),
        "",
        "Primary native statistical contracts: [SciPy sensitivity](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html), "
        "[native QMC](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html). "
        "Scientific references and limitations are in docs/UNCERTAINTY.md. "
        "No external raw dataset or implementation is bundled.",
        "",
    ]
    target = args.report if args.report.is_absolute() else root / args.report
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
    print(f"Actual native uncertainty replay {elapsed:.6g}s; {target.name}", flush=True)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
