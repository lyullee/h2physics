"""Run native frozen-mixture/common-nozzle evidence; write no external inputs."""

import hashlib
import math
import time
from pathlib import Path

import cantera as ct
import numpy as np

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
from h2physics.adapters.cantera_volume import (
    CanteraOpenGasVolume,
    GasBoundaryRate,
    GasFeed,
    GasVent,
)
from h2physics.core import Origin
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening


def constant_cp_provider(hydrogen_fraction):
    species = []
    # Original arbitrary coefficients, in native J/kmol and J/kmol/K.
    for name, atoms, limits, coefficients in (
        ("H2", {"H": 2}, (180, 3200), (300, 1.7e6, 8e4, 31000)),
        ("N2", {"N": 2}, (220, 2800), (300, -2.2e6, 1.25e5, 35000)),
    ):
        item = ct.Species(name, atoms)
        item.thermo = ct.ConstantCp(*limits, 101325., coefficients)
        species.append(item)
    native = ct.Solution(name="authored-frozen-evidence", thermo="ideal-gas", kinetics=None,
                         species=species)
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    basis = MechanismBasis("authored-frozen-evidence-v1", source_hash, "Apache-2.0-authored-fixture",
        ("https://cantera.org/3.2/reference/thermo/species-thermo.html#constant-heat-capacity",),
        150, 3000, 1e4, 2e6)
    return CanteraFrozenGasProperties(native, basis,
                                     {"H2": hydrogen_fraction, "N2": 1-hydrogen_fraction})


def analytic_values(pressure, temperature, hydrogen_fraction):
    fractions = (hydrogen_fraction, 1-hydrogen_fraction)
    amounts = [y/w for y, w in zip(fractions, (2.016, 28.014), strict=True)]
    total = math.fsum(amounts)
    universal = 8314.46261815324
    gas_constant = total*universal
    cp = math.fsum(n*c for n, c in zip(amounts, (31000, 35000), strict=True))
    h = math.fsum(n*(h0+c*(temperature-300))
        for n, h0, c in zip(amounts, (1.7e6, -2.2e6), (31000, 35000), strict=True))
    s = math.fsum(n*(s0+c*math.log(temperature/300)
                     - universal*math.log(n/total*pressure/101325))
        for n, s0, c in zip(amounts, (8e4, 1.25e5), (31000, 35000), strict=True))
    return (pressure/(gas_constant*temperature), h, h-gas_constant*temperature, s,
            cp, cp-gas_constant, math.sqrt(cp/(cp-gas_constant)*gas_constant*temperature))


def constant_cp_checks(lines):
    opening = NozzleOpening("authored-frozen-vent", 2e-5, .73, "declared-effective-area")
    maxima = dict.fromkeys(("property_relative_error", "ph_temperature_relative_error",
                           "ps_temperature_relative_error", "eos_energy_identity_j_kg"), 0.)
    lines += ["## Independent constant-cp checks", "",
        "The native species are constructed from arbitrary coefficients authored in this script. "
        "They are synthetic numerical fixtures, not a measured H2/N2 caloric model. The independent "
        "oracle uses ideal-mixture algebra with specified molar masses 2.016 and 28.014 kg/kmol, "
        "R = 8314.46261815324 J/(kmol K), mixing entropy and separate formation/reference offsets. "
        "Selected native fits intersect the declared domain at 220–2800 K and 0.01–2 MPa.", "",
        "| Y(H2) | Back pressure Pa | Regime | Solved exit Pa | Pressure relative error | "
        "Mass-flow relative error | Energy residual W |", "|---:|---:|---|---:|---:|---:|---:|"]
    total_cases = 0
    for fraction in (.02, .14, .75):
        provider = constant_cp_provider(fraction)
        for pressure in (1e4, 1e5, 8e5, 2e6):
            for temperature in (220, 350, 700, 1150, 2100, 2800):
                expected = analytic_values(pressure, temperature, fraction)
                state = provider.state_pt(pressure, temperature)
                observed = (state.density_kg_m3, state.enthalpy_j_kg, state.internal_energy_j_kg,
                            state.entropy_j_kg_k, state.cp_j_kg_k, state.cv_j_kg_k,
                            state.speed_of_sound_m_s)
                maxima["property_relative_error"] = max(maxima["property_relative_error"],
                    max(abs(a-b)/max(abs(b), 1.) for a, b in zip(observed, expected, strict=True)))
                for method, value, key in (
                    (provider.state_ph, state.enthalpy_j_kg, "ph_temperature_relative_error"),
                    (provider.state_ps, state.entropy_j_kg_k, "ps_temperature_relative_error"),
                ):
                    provider.native_phase.basis = "molar"
                    provider.native_phase.TPY = 300, 1e5, {"N2": 1}
                    recovered = method(pressure, value)
                    maxima[key] = max(maxima[key], abs(recovered.temperature_k/temperature-1))
                maxima["eos_energy_identity_j_kg"] = max(maxima["eos_energy_identity_j_kg"],
                                                         abs(state.enthalpy_identity_residual_j_kg))
                total_cases += 1
        upstream = provider.state_pt(8e5, 700)
        gamma = upstream.cp_j_kg_k/upstream.cv_j_kg_k
        gas_constant = upstream.cp_j_kg_k-upstream.cv_j_kg_k
        critical = 8e5*(2/(gamma+1))**(gamma/(gamma-1))
        for back in (1e5, critical, 7e5):
            result = HomogeneousIsentropicNozzle(provider).solve(upstream,
                back_pressure_pa=back, opening=opening)
            expected_pressure = max(back, critical)
            expected_temperature = 700*(expected_pressure/8e5)**((gamma-1)/gamma)
            expected_speed = math.sqrt(2*upstream.cp_j_kg_k*(700-expected_temperature))
            expected_mass = (opening.effective_area_m2(1)*expected_pressure
                             /(gas_constant*expected_temperature)*expected_speed)
            pressure_error = abs(result.exit_state.pressure_pa/expected_pressure-1)
            mass_error = abs(result.mass_flow_kg_s/expected_mass-1)
            if pressure_error > 1e-7 or mass_error > 1e-7 or abs(result.energy_residual_w) > 1e-6:
                raise AssertionError("Independent constant-cp nozzle gate failed")
            lines.append(f"| {fraction:g} | {back:.10g} | {result.regime} | "
                f"{result.exit_state.pressure_pa:.10g} | {pressure_error:.8g} | "
                f"{mass_error:.8g} | {result.energy_residual_w:.8g} |")
        print(f"constant-cp Y(H2)={fraction:g}: property grid and three common-nozzle cases passed",
              flush=True)
    if maxima["property_relative_error"] > 1e-12 or maxima["eos_energy_identity_j_kg"] > 1e-8:
        raise AssertionError("Independent constant-cp property gate failed")
    if max(maxima["ph_temperature_relative_error"], maxima["ps_temperature_relative_error"]) > 2e-8:
        raise AssertionError("Native frozen flash gate failed")
    lines += ["", f"Property grid: {total_cases} PT states; "
        "72 PH and 72 PS roundtrips after contaminating native state and unit basis. "
        "Exact boundary targets reuse the already evaluated native TPY endpoint; interior "
        "targets use native HP/SP inversion.", "",
        "| Diagnostic | Maximum |", "|---|---:|"]
    lines += [f"| {key} | {value:.10g} |" for key, value in maxima.items()]


def installed_mechanism_checks(lines):
    lines += ["", "## Installed mechanism execution", "",
        "Python reads each separately installed file and passes its unmodified UTF-8 text "
        "to the native Solution constructor, avoiding the observed C++ non-ASCII Windows "
        "path failure. No mechanism is copied into this repository. File hashes identify "
        "these exact installed inputs; they do not qualify another mechanism.", "",
        "| Mechanism / phase | Source SHA-256 |", "|---|---|"]
    providers = []
    for filename, name in (("h2o2.yaml", "ohmech"), ("gri30.yaml", "gri30")):
        raw = (Path(ct.__file__).parent / "data" / filename).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        basis = MechanismBasis(f"Cantera:{ct.__version__}:{filename}:{name}", digest,
            "Cantera-distribution-BSD-3-Clause; upstream-GRI-Mech-provenance",
            (f"https://cantera.org/3.2/examples/input/{filename.removesuffix('.yaml')}.html",),
            300, 3000, 1e4, 2e6)
        phase = ct.Solution(yaml=raw.decode("utf-8"), name=name)
        provider = CanteraFrozenGasProperties(phase, basis, {"H2": .03, "O2": .225, "N2": .745})
        providers.append((filename, provider))
        lines.append(f"| {filename} / {name} | {digest} |")
    lines += ["", "| Mechanism | P0 Pa | T0 K | Back pressure Pa | Regime | Exit Pa | "
        "Flow kg/s | Max PH/PS T relative error | Energy residual W |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|"]
    for filename, provider in providers:
        for pressure, temperature, back in ((6e5, 850, 1e5), (6e5, 850, 5.5e5)):
            state = provider.state_pt(pressure, temperature)
            error = max(abs(provider.state_ph(pressure, state.enthalpy_j_kg).temperature_k/temperature-1),
                        abs(provider.state_ps(pressure, state.entropy_j_kg_k).temperature_k/temperature-1))
            result = HomogeneousIsentropicNozzle(provider).solve(state, back_pressure_pa=back,
                opening=NozzleOpening("installed-frozen-vent", 1e-5, 1, "ideal-area"))
            if error > 2e-8 or abs(result.energy_residual_w) > 1e-6:
                raise AssertionError("Installed native flash/nozzle gate failed")
            frozen = [provider.mass_fractions.get(n, 0) for n in provider.native_phase.species_names]
            if not np.array_equal(provider.native_phase.Y, frozen):
                raise AssertionError("Frozen native species identity changed")
            lines.append(f"| {filename} | {pressure:g} | {temperature:g} | {back:g} | "
                f"{result.regime} | {result.exit_state.pressure_pa:.10g} | "
                f"{result.mass_flow_kg_s:.10g} | {error:.8g} | {result.energy_residual_w:.8g} |")
        print(f"{filename}: actual native frozen flashes and common nozzle passed", flush=True)


def evolving_enclosure_check(lines):
    reference = constant_cp_provider(.14)

    def phase_factory():
        return constant_cp_provider(.14).native_phase

    property_phase = phase_factory()
    basis = reference.mechanism_basis
    opening = NozzleOpening("evolving-frozen-vent", 1e-5, .8, "declared-effective-area")
    compositions, corrections = [], []

    def vent_flow(time_s, current):
        properties = CanteraFrozenGasProperties(property_phase, basis,
            dict(zip(current.species_names, current.Y, strict=True)),
            composition_sum_tolerance=1e-7,
            composition_correction_id="native-CVODES-Jacobian-largest-species-trial-extension")
        state = properties.state_pt(current.P, current.T)
        result = HomogeneousIsentropicNozzle(properties).solve(state,
            back_pressure_pa=1e5, opening=opening)
        compositions.append(properties.mass_fractions["H2"])
        if properties.composition_correction is not None:
            corrections.append(properties.composition_correction)
        return result.mass_flow_kg_s

    feed = GasFeed(GasBoundaryRate("feed", "absolute-evidence-clock", 12.5, 13.,
        lambda t, phase: .001, Origin.SYNTHETIC, "authored-H2-feed"),
        ReactiveState(500, 4e5, {"H2": 1}))
    vent = GasVent(GasBoundaryRate("vent", "absolute-evidence-clock", 12.5, 13., vent_flow,
        Origin.SYNTHETIC, "common-nozzle"), ReactiveState(500, 1e5, {"N2": 1}))
    trace = CanteraOpenGasVolume(phase_factory, basis).run(
        ReactiveState(500, 3e5, {"H2": .1, "N2": .9}), np.linspace(12.5, 12.55, 6),
        volume_m3=.5, clock_id="absolute-evidence-clock", feeds=(feed,), vents=(vent,),
        maximum_time_step_s=.01, relative_tolerance=1e-8, absolute_tolerance=1e-12)
    mass_error = float(np.max(abs(trace.mass_residual_kg)))
    species_error = float(np.max(abs(trace.species_residual_kg)))
    energy_error = float(np.max(abs(trace.energy_residual_j)))
    correction = max((abs(c.mass_fraction_change) for c in corrections), default=0.)
    signed_correction = max((c.mass_fraction_change for c in corrections), key=abs, default=0.)
    accepted_sum_deviations = [math.fsum(s.mass_fractions.values())-1 for s in trace.snapshots]
    accepted_signed = max(accepted_sum_deviations, key=abs)
    if mass_error > 1e-8 or species_error > 1e-8 or energy_error > 2e-3 or correction > 1e-7:
        raise AssertionError("Evolving mixture enclosure/common-nozzle conservation gate failed")
    lines += ["", "## Evolving native enclosure and shared-nozzle callback", "",
        "An actual CanteraOpenGasVolume run starts at absolute time 12.5 s, 500 K, "
        "0.3 MPa and 0.5 m3 with mole fractions H2=0.1 and N2=0.9. A constant "
        "0.001 kg/s pure-H2 feed enters at 500 K; the single common nozzle vents "
        "to 0.1 MPa through 8e-6 m2 effective area. Six output times end at "
        "12.55 s. Native callbacks have declared support through 13 s. The "
        "property phase is separate from the active reactor phase.", "",
        "This run explicitly budgets a 1e-7 mass-fraction sum correction for native "
        "CVODES trial states under policy native-CVODES-Jacobian-largest-species-trial-extension. "
        "This is a deliberate extension of the callback away from the physical composition "
        "simplex, not floating-point roundoff. Native finite-difference Jacobian probes can "
        "leave that simplex by about 1.5e-8; accepted-state ulp deviations are recorded "
        "separately below. "
        "Only the largest nonnegative species absorbs the sum residual; all raw "
        "values, selected species, changes and the budget are inspectable. Negative "
        "species, materially invalid sums and corrections above budget remain errors. "
        "The default property constructor permits no correction.", "",
        "| Diagnostic | Observed |", "|---|---:|",
        f"| Nozzle callback evaluations | {len(compositions)} |",
        f"| Recorded composition sum corrections | {len(corrections)} |",
        f"| Maximum absolute species correction | {correction:.10g} |",
        f"| Signed correction at maximum magnitude (exact float.hex) | {signed_correction.hex()} |",
        f"| Maximum sampled accepted-state absolute sum deviation | {abs(accepted_signed):.10g} |",
        f"| Signed accepted-state sum deviation at maximum magnitude (exact float.hex) | "
        f"{accepted_signed.hex()} |",
        f"| Initial accepted Y(H2) | {trace.snapshots[0].mass_fractions['H2']:.10g} |",
        f"| Final accepted Y(H2) | {trace.snapshots[-1].mass_fractions['H2']:.10g} |",
        f"| Integrated vent mass kg | {trace.integral('outlet:vent:mass')[-1]:.10g} |",
        f"| Maximum mass residual kg | {mass_error:.10g} |",
        f"| Maximum species residual kg | {species_error:.10g} |",
        f"| Maximum energy residual J | {energy_error:.10g} |", "",
        "The residuals compare native inventory changes with native appended boundary "
        "integrals. Independent constant-cp/nozzle checks appear above; this coupled "
        "run is integration/conservation evidence, not an enclosure experiment. The opt-in "
        "trial extension does not establish physical validity for off-simplex states."]
    print("evolving native mixture: shared-nozzle callback and finite enclosure ledgers passed",
          flush=True)


def main():
    start = time.perf_counter()
    lines = ["# Frozen gas property and shared-nozzle verification", "",
        f"Local execution: Cantera {ct.__version__}; original script "
        "scripts/check_cantera_properties.py. All states and nozzle cases below are synthetic "
        "software verification. They are not independent mixture-EOS or vent experiments.", ""]
    constant_cp_checks(lines)
    installed_mechanism_checks(lines)
    evolving_enclosure_check(lines)
    lines += ["", "## Scope and rights", "",
        "The API retains actual caller-created native phases and supplies the existing "
        "HomogeneousIsentropicNozzle through PropertyProvider. TPY, HP and SP remain native; "
        "no EOS, choking solver, chemistry integrator or transport model is duplicated. "
        "The formation enthalpy, entropy and composition fingerprints remain in PropertyBasis. "
        "Native mechanism H2 is explicitly spin-unresolved, and normal/para/ortho-H2 "
        "thermodynamic claims are rejected.", "",
        "The intersection of declared mechanism limits and selected species fit limits is "
        "enforced. The ideal-gas pressure envelope is a caller declaration, not real-gas "
        "validation. Viscosity/conductivity, equilibrium composition, cryogenic condensation, "
        "dissociation evolution, spin conversion, atmospheric source ownership and vent "
        "discharge-coefficient qualification are outside these checks.", "",
        "The source hash is the caller's provenance assertion. A separate fingerprint "
        "records the actual native species thermochemistry and detects later definition "
        "edits, but cannot authenticate a claimed upstream source. Successful queries reset "
        "the native mass unit basis and all species; callers must synchronize direct "
        "concurrent access to the retained object.", "",
        "Cantera is a separately installed BSD-3-Clause dependency: "
        "[license](https://github.com/Cantera/cantera/blob/v3.2.0/License.txt). "
        "The installed example inputs declare GRI-Mech-derived provenance. That "
        "distribution fact does not grant blanket redistribution rights for another "
        "mechanism. Neither mechanism files nor third-party examples/data are bundled.", "",
        "Primary references: [native property API](https://cantera.org/3.2/python/thermo.html), "
        "[species caloric fits](https://cantera.org/3.2/reference/thermo/species-thermo.html), "
        "[ideal gas](https://cantera.org/3.2/reference/thermo/phase-thermo.html#ideal-gas), "
        "[NASA mass-flow relation](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html).", "",
        f"Elapsed local script time: {time.perf_counter()-start:.6g} s."]
    target = Path(__file__).resolve().parents[1] / "research/frozen_gas_properties.md"
    target.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"wrote {target.name}", flush=True)


if __name__ == "__main__":
    main()
