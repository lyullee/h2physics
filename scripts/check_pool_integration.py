"""Verify actual dynamic pool objects, source integrals and numerical refinement.

All scenario inputs are authored. No measured radius/flux or source-derived
parameter table is imported; upstream experimental claims are not rerun here.
"""

import argparse
import hashlib
import importlib.metadata
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
from dynamiclh2poolx import (
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    run_dynamic_pool,
)
from scipy.integrate import quad

from h2physics.adapters.pool import (
    DeclaredGroundInflow,
    NativeDynamicPool,
    PoolCouplingError,
    PoolTolerances,
)
from h2physics.core import Origin
from h2physics.release import SourceLocation
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
REVISION = "6a700e8e183039bbb81803bacc416f6c9117ed71"
NATIVE_SHA = "bac236e164f144a4269615a83fc6e3d994fa02ab06b853a43e386cfc2bbc8fd4"
ORIGIN = 200.
RELATIVE_OUTPUT = (0., .2, .6, 1.13, 2., 4., 8.)
PRESSURE = 101325.
# Fixed numerical agreement targets; these are not experimental accuracy gates.
SPATIAL_MASS_LIMIT, TEMPORAL_MASS_LIMIT = .01, .002
RADIUS_LIMIT_M = .02


def package_sha():
    root = Path(importlib.metadata.distribution("dynamiclh2poolx").locate_file("dynamiclh2poolx"))
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", action="store_true", help="Generate an original local diagnostic plot with Matplotlib")
    args = parser.parse_args()
    assert importlib.metadata.version("dynamiclh2poolx") == "0.2.0rc2"
    assert package_sha() == NATIVE_SHA
    properties = CoolPropProperties("Hydrogen")
    liquid, vapor = properties.saturated(PRESSURE, 0.), properties.saturated(PRESSURE, 1.)
    latent = vapor.enthalpy_j_kg-liquid.enthalpy_j_kg
    location = SourceLocation("authored-ground", "authored-facility-clock", "authored-horizontal-frame",
                              (0., 0., 0.), (0., 0., 1.))
    vapor_location = replace(location, source_id="authored-pool-vapor")
    native_inflow = DeclaredInflow(times_s=(0., 1.13), rates_kg_s=(.025, 0.))
    inflow = DeclaredGroundInflow(native_inflow, location, liquid, ORIGIN, ORIGIN+8.,
        Origin.SYNTHETIC, "authored-explicit-saturated-ground-input", "isolation")
    bridge = NativeDynamicPool(run_dynamic_pool, properties,
        engine_id="DynamicLH2PoolX:0.2.0rc2:"+REVISION,
        tolerances=PoolTolerances(event_clock_roundoff_s=1e-10))
    surface = SolidSemiInfiniteSurface(name="authored-solid", conductivity_W_mK=.16,
        diffusivity_m2_s=7e-7, initial_temperature_K=80.)

    def run(dr, dt, *, radius=1.5, outputs=RELATIVE_OUTPUT):
        numerics = ShallowLayerNumerics(domain_radius_m=radius, source_radius_m=.12,
                                        radial_step_m=dr, maximum_time_step_s=dt)
        config = DynamicPoolConfig(surface=surface, numerics=numerics, ambient_pressure_Pa=PRESSURE)
        return bridge.run(config, inflow, output_times_s=tuple(ORIGIN+t for t in outputs),
                          vapor_location=vapor_location)

    spatial = [(dr, dt, run(dr, dt)) for dr, dt in
               ((.02, .01), (.01, .005), (.005, .0025), (.0025, .00125), (.00125, .000625))]
    temporal = [(dt, run(.005, dt)) for dt in (.01, .005, .0025, .00125)]
    total_input = inflow.cumulative_mass_kg(inflow.end_time_s, clock_id=location.clock_id)

    def changes(a, b):
        mass = max(abs(x.native.liquid_mass_kg-y.native.liquid_mass_kg)
                   for x, y in zip(a.samples, b.samples, strict=True))/total_input
        radius = max(abs(x.native.reported_radius_m-y.native.reported_radius_m)
                     for x, y in zip(a.samples, b.samples, strict=True))
        return mass, radius

    spatial_changes = [changes(a[2], b[2]) for a, b in zip(spatial, spatial[1:])]
    temporal_changes = [changes(a[1], b[1]) for a, b in zip(temporal, temporal[1:])]
    spatial_pass = spatial_changes[-1][0] <= SPATIAL_MASS_LIMIT and spatial_changes[-1][1] <= RADIUS_LIMIT_M
    temporal_pass = temporal_changes[-1][0] <= TEMPORAL_MASS_LIMIT and temporal_changes[-1][1] <= RADIUS_LIMIT_M
    print("coupled refinement:", spatial_changes, "temporal refinement:", temporal_changes, flush=True)
    finest = spatial[-1][2]
    try:
        strict = NativeDynamicPool(run_dynamic_pool, properties, engine_id="native-default-clock")
        strict.run(spatial[0][2].config, inflow, output_times_s=tuple(ORIGIN+t for t in RELATIVE_OUTPUT),
                   vapor_location=vapor_location)
    except PoolCouplingError as error:
        original_input_error = error.native.ledger[-1].cumulative_inflow_kg-total_input
        original_reported_residual = error.native.mass_balance_residual_kg
        assert abs(original_input_error) > 1e-8
    else:
        raise AssertionError("The retained native near-knot timing failure did not reproduce")
    assert finest.native.ledger[0] is finest.samples[0].native
    source = finest.evaporation_source()
    expected_evaporation = finest.native.ledger[-1].cumulative_evaporation_kg
    assert abs(source.total_mass_kg-expected_evaporation) < 1e-14
    rebinned = source.rebin([ORIGIN, ORIGIN+.15, ORIGIN+1., ORIGIN+3., ORIGIN+8.], clock_id=location.clock_id)
    assert abs(rebinned.total_mass_kg-source.total_mass_kg) < 1e-14
    at_stop = next(row for row in finest.native.ledger if math.isclose(row.time_s, 1.13))
    post_stop_evaporation = expected_evaporation-at_stop.cumulative_evaporation_kg
    assert post_stop_evaporation > .001 and at_stop.liquid_inflow_rate_kg_s == 0.
    assert finest.native.ledger[4].reported_radius_m == 0. and finest.native.ledger[4].liquid_mass_kg > 0.
    last_rate_trapezoid = float(np.trapezoid(
        [row.last_substep_evaporation_rate_kg_s for row in finest.native.ledger], RELATIVE_OUTPUT))

    # Zero thermal driving force: an independently integrated step input is retained.
    no_heat_surface = replace(surface, initial_temperature_K=liquid.temperature_k)
    no_heat_config = replace(finest.config, surface=no_heat_surface)
    no_heat_inflow = DeclaredGroundInflow(DeclaredInflow((0., .17), (.011, 0.)), location,
        liquid, ORIGIN, ORIGIN+.7, Origin.SYNTHETIC, "authored-zero-thermal-drive", "isolation")
    no_heat = bridge.run(no_heat_config, no_heat_inflow,
        output_times_s=(ORIGIN, ORIGIN+.17, ORIGIN+.7), vapor_location=vapor_location)
    no_heat_error = abs(no_heat.native.ledger[-1].liquid_mass_kg-.011*.17)
    assert no_heat_error < 1e-13 and no_heat.native.ledger[-1].cumulative_evaporation_kg == 0.

    # Independent quadrature of a capped conduction flux, across its change of regime.
    capped = replace(surface, heat_flux_cap_W_m2=9000.)
    numerator = capped.conductivity_W_mK*(capped.initial_temperature_K-liquid.temperature_k)
    switch = (numerator/(9000.*math.sqrt(math.pi*capped.diffusivity_m2_s)))**2
    integrated_depth = quad(lambda t: min(9000., numerator/math.sqrt(math.pi*capped.diffusivity_m2_s*t))
                            /(liquid.density_kg_m3*latent), 0., 3., points=[switch],
                            epsabs=1e-14, epsrel=1e-10)[0]
    native_depth = capped.evaporated_depth_m(0., 3., liquid.temperature_k, liquid.density_kg_m3, latent)
    depth_error = abs(integrated_depth-native_depth)
    assert depth_error < 1e-13

    larger_domain = run(spatial[-1][0], spatial[-1][1], radius=3.)
    domain_changes = changes(finest, larger_domain)
    assert domain_changes[0] < 1e-8 and domain_changes[1] < 1e-8
    try:
        run(.01, .005, radius=.3)
    except PoolCouplingError as error:
        escaped = error.native.ledger[-1].escaped_domain_mass_kg
        domain_issue = error.issues[0]
        assert escaped > 0.
    else:
        raise AssertionError("The deliberately inadequate domain was not rejected")
    try:
        NativeDynamicPool(run_dynamic_pool, CoolPropProperties("ParaHydrogen"), engine_id="unsupported-para")
    except ValueError:
        para_rejected = True
    else:
        raise AssertionError("The normal-Hydrogen native engine was relabeled as ParaHydrogen")

    lines = ["# Native dynamic pool and conservative mass-source verification", "",
        "All process/surface inputs below are authored synthetic verification cases. "
        "No measured curve or third-party digitised observation is imported. The optional "
        "MIT [DynamicLH2PoolX](https://github.com/lyullee/DynamicLH2PoolX/tree/"+REVISION+") "
        "owns radial finite-volume spreading, local contact-age conduction, evaporation "
        "and time stepping. Native objects/results are retained; host code only supplies "
        "explicit boundaries and checks their ledgers.", "",
        f"- Version 0.2.0rc2; revision `{REVISION}`; native sorted relative .py paths plus bytes SHA-256 `{NATIVE_SHA}`.",
        "- The separately installed exact GitHub revision and released PyPI package have identical checked module bytes.",
        f"- Property basis: `{properties.basis}`; native constant saturation T {liquid.temperature_k:.12g} K, "
        f"rho liquid {liquid.density_kg_m3:.12g} kg/m3 and latent difference {latent:.12g} J/kg.",
        "- Native inflow: 0.025 kg/s on [0,1.13) s, then zero through 8 s. "
        "Host absolute clock origin: 200 s, same explicitly named frame/center for both boundaries.",
        "- Solid: k=0.16 W/(m K), alpha=7e-7 m2/s, initial T=80 K, no heat-flux cap, multiplier 1. "
        "These are numerical inputs, not fitted or claimed material coefficients.",
        "- Radial domain 1.5 m, parabolic source radius 0.12 m, default CFL 0.2/Chezy 0.001, "
        "dry depth 1e-8 m, reported front depth 7.5e-4 m, zero retention, "
        "zero_radial_momentum_vapor evaporation closure. Initial pool inventory is zero.",
        "- Every output independently checks the declared step integral, mass storage/evaporation/escape/adjustment, "
        "native interval mean and normal-hydrogen density/temperature. Gate: 1e-10 kg + 1e-8 times cumulative input; "
        "default allowed numerical adjustment and escaped mass are both zero.", "",
        "## Native event-clock failure and explicit boundary correction", "",
        "The native loop treats a next knot within 1e-12 s as already reached, while its "
        "original rate_at uses a strict time comparison. An absolute-origin subtraction or "
        "accumulated time-step roundoff can leave the clock just below isolation: the old "
        "positive rate then persists for an entire extra step. Independent input integration "
        "catches this even though the internal inventory ledger can report near-zero residual.", "",
        f"- Unmodified coarse case input error: {original_input_error:.12g} kg; "
        f"native reported final residual: {original_reported_residual:.12g} kg.",
        "- Positive cases explicitly choose event_clock_roundoff_s=1e-10. A structural "
        "dataclass input proxy delegates to the actual native rate_at at a known knot only "
        "within that budget; every correction and original native object is retained. The "
        "default budget remains zero. No pool equation, time integrator or global function is patched.",
        f"- Maximum input-clock correction in the finest coupled run: {finest.maximum_input_clock_correction_s:.12g} s. "
        "Original independent mass gates stay unchanged. Request 010 includes the receiving fix.", "",
        "## Coupled spatial/time refinement", "",
        f"Fixed gates: maximum sample inventory difference / total supplied mass ≤{SPATIAL_MASS_LIMIT:g}; "
        f"maximum reported-radius difference ≤{RADIUS_LIMIT_M:g} m. All compared output edges are "
        f"{RELATIVE_OUTPUT} s. These are numerical agreement targets, not experimental accuracy.", "",
        "| Coarse dr (m) / maximum dt (s) | Fine dr (m) / maximum dt (s) | Mass difference / supplied | Radius difference (m) | Gate |",
        "|---|---|---:|---:|---|"]
    for (dr1, dt1, _), (dr2, dt2, _), (dm, dr) in zip(spatial[:-1], spatial[1:], spatial_changes, strict=True):
        lines.append(f"| {dr1:g} / {dt1:g} | {dr2:g} / {dt2:g} | {dm:.10g} | {dr:.10g} | "
                     f"{'PASS' if dm <= SPATIAL_MASS_LIMIT and dr <= RADIUS_LIMIT_M else 'FAIL'} |")
    lines += ["", "## Time refinement at fixed dr=0.005 m", "",
        f"Fixed mass target ≤{TEMPORAL_MASS_LIMIT:g} of supplied mass; radius target unchanged. "
        "Values are configured maximum steps; the native CFL condition can choose smaller steps. "
        "These differences are not monotone; passing the finite agreement target does not "
        "establish an asymptotic temporal order or a Richardson uncertainty.", "",
        "| Coarse / fine maximum dt (s) | Mass difference / supplied | Radius difference (m) | Gate |",
        "|---|---:|---:|---|"]
    for (dt1, _), (dt2, _), (dm, dr) in zip(temporal[:-1], temporal[1:], temporal_changes, strict=True):
        lines.append(f"| {dt1:g} / {dt2:g} | {dm:.10g} | {dr:.10g} | "
                     f"{'PASS' if dm <= TEMPORAL_MASS_LIMIT and dr <= RADIUS_LIMIT_M else 'FAIL'} |")
    lines += ["", "## Finest coupled run", "",
        "| Relative time (s) | Supplied mass (kg) | Liquid inventory (kg) | Evaporated mass (kg) | Reported radius (m) | Wet area (m2) | Independent mass residual (kg) |",
        "|---:|---:|---:|---:|---:|---:|---:|"]
    for audited in finest.samples:
        row = audited.native
        lines.append(f"| {row.time_s:.9g} | {audited.declared_cumulative_inflow_kg:.10g} | "
            f"{row.liquid_mass_kg:.10g} | {row.cumulative_evaporation_kg:.10g} | {row.reported_radius_m:.9g} | "
            f"{row.wet_area_m2:.9g} | {audited.independently_recomputed_mass_residual_kg:.9g} |")
    lines += ["", f"- Exact source-interval mass sum: {source.total_mass_kg:.12g} kg; "
        f"rebinned mass difference {rebinned.total_mass_kg-source.total_mass_kg:.9g} kg.",
        f"- Evaporation after liquid input isolation: {post_stop_evaporation:.12g} kg.",
        f"- Trapezoids of sparsely reported last-substep rates instead give {last_rate_trapezoid:.12g} kg; "
        "this retained negative comparison is not the interval source integral.",
        f"- Derived vapor enthalpy transfer {source.enthalpy_transfer_j:.12g} J and latent demand "
        f"{source.total_mass_kg*latent:.12g} J use the explicit constant saturation states. "
        "Latent demand is derived, not an independently measured heat input or a checked complete energy ledger.",
        f"- Zero thermal-driving limit inventory error: {no_heat_error:.9g} kg; evaporation exactly zero.",
        f"- Independent capped-conduction quadrature depth error: {depth_error:.9g} m.",
        f"- Domain 1.5 to 3 m changes mass/supply and reported radius by {domain_changes}.",
        f"- Deliberately inadequate 0.3 m domain rejected: escaped {escaped:.9g} kg; `{domain_issue}`.",
        f"- Explicit ParaHydrogen binding rejection: {para_rejected}.", "",
        "A zero reported radius is a depth-threshold observation, not a dry pool. The native "
        "dry-depth treatment leaves a small nonzero final inventory; the run ends as window_end, "
        "not certified depletion. Numerical adjustment, domain escape and unknown properties are "
        "not erased. Interval rebinning preserves a piecewise-constant mean representation; "
        "it cannot reconstruct unobserved within-bin timing. Endpoint wet/reported areas "
        "and interval-mean/last-substep rates remain distinct. No instantaneous heat flux, "
        "vertical momentum or fully resolved atmospheric boundary is invented.", "",
        "## Experimental data and unfinished contracts", "",
        "The [PRESLHY E3.4 source](https://doi.org/10.35097/1319) lists eleven attachments "
        "under CC BY-SA 4.0. The default permissive-data acquisition policy withholds all "
        "eleven; metadata hashes, authors, version and omissions are recorded separately. "
        "No restricted source data or upstream digitised radius curves are redistributed "
        "or treated as independently acquired observations here. A different source or "
        "separately reviewed data workflow is required for experimental comparison.", "",
        "The current native hard-coded normal-Hydrogen properties, lack of radial-state "
        "snapshots/interval-area and independent heat ledgers remain receiving extension work. "
        "The host rejects a para-Hydrogen label; it does not replace the solver or patch "
        "global property functions. Request 010 describes the actual Python contracts. "
        "Upstream component studies have their own domains and provenance and are not "
        "automatically transferred to this authored facility case.", "", "Host SHA-256:", ""]
    for relative in ("src/h2physics/sources.py", "src/h2physics/adapters/pool.py", "scripts/check_pool_integration.py"):
        lines.append(f"- `{relative}`: `{hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()}`")
    (ROOT/"research/native_pool.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    if args.plot:
        plot_run(finest, source)
    print("native pool:", expected_evaporation, "kg evaporated; post-isolation", post_stop_evaporation,
          "kg; finest coupled refinement", spatial_changes[-1], "time", temporal_changes[-1], flush=True)
    assert spatial_pass and temporal_pass, "Refinement targets failed; full positive/negative report retained"


def plot_run(run, source):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    time = np.array([row.native.time_s for row in run.samples])
    axes[0].plot(time, [1e3*row.native.liquid_mass_kg for row in run.samples], "o-", label="Liquid inventory")
    axes[0].plot(time, [1e3*row.native.cumulative_evaporation_kg for row in run.samples], "o-", label="Cumulative evaporation")
    axes[0].axvline(1.13, color="black", ls="--", label="Input isolated")
    axes[0].set(xlabel="Time since ground input / s", ylabel="Mass / g")
    axes[0].legend()
    axes[1].stairs(1e3*source.mean_rates_kg_s, source.edges_s-ORIGIN, label="Conservative interval means")
    axes[1].plot(time, [1e3*row.native.last_substep_evaporation_rate_kg_s for row in run.samples],
                 "o--", label="Last substep samples")
    axes[1].set(xlabel="Time since ground input / s", ylabel="Evaporation rate / (g/s)")
    axes[1].legend()
    for axis in axes:
        axis.grid(alpha=.2)
    figure.suptitle("Authored numerical case: native dynamic LH2 pool; normal Hydrogen")
    destination = ROOT/"artifacts/pool"
    destination.mkdir(exist_ok=True)
    figure.savefig(destination/"inventory_and_source.png", dpi=150)
    plt.close(figure)


if __name__ == "__main__":
    main()
