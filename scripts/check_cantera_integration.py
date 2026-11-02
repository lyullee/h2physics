"""Record native chemistry conservation, event-grid and flame-refinement evidence."""

import hashlib
from pathlib import Path

import cantera as ct
import numpy as np

from h2physics.adapters.cantera import (
    CanteraGas,
    FlameSettings,
    MechanismBasis,
    ReactiveState,
    temperature_rise_event,
)


def main():
    root = Path(__file__).resolve().parents[1]
    raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
    basis = MechanismBasis(f"Cantera:{ct.__version__}:h2o2:ohmech", hashlib.sha256(raw).hexdigest(),
                           "Cantera-distribution-BSD-3-Clause; upstream-GRI-Mech-provenance",
                           ("https://cantera.org/3.2/examples/input/h2o2.html",), 300, 3500, 1e4, 2e6)
    provider = CanteraGas(lambda: ct.Solution(yaml=raw.decode("utf-8"), name="ohmech"), basis)
    mixture = {"H2": 2/6.76, "O2": 1/6.76, "N2": 3.76/6.76}
    lines = ["# Native chemistry and reacting-flow verification", "",
             f"Cantera {ct.__version__}; mechanism source SHA-256 `{basis.source_sha256}`.",
             "The installed h2o2/ohmech mechanism is an upstream GRI-Mech-derived example. "
             "Neither its mechanism file nor the dependency source is bundled here. "
             "Its use below verifies the adapter; it is not selection of a qualified "
             "hydrogen safety mechanism for every pressure/temperature. "
             "The declared test envelope is 300–3500 K and 0.01–2 MPa.", "",
             "The C++ default data directory loses non-ASCII Windows path characters in this "
             "installation. Python reads the installed mechanism and supplies its unchanged "
             "text to the native Solution constructor. The public adapter accepts a native "
             "phase factory and does not require a serialization format.", "",
             "## Equilibrium and closed reactors", "",
             "Authored stoichiometric H2/O2/N2 mixture at 101325 Pa; these are synthetic "
             "verification cases. Conservation is checked within each mechanism's energy basis.", "",
             "| Case | Final T K | Max energy residual J/kg | Max element fraction residual | 200 K rise bracket s |",
             "|---|---:|---:|---:|---|"]
    for temperature in (1000, 1001):
        initial = ReactiveState(temperature, 101325, mixture)
        for constraint in ("HP", "UV"):
            result = provider.equilibrium(initial, constraint=constraint)
            lines.append(f"| equilibrium {constraint}, T0={temperature} | {result.final.state.temperature_k:.7g} | "
                         f"{abs(result.energy_residual_j_kg):.8g} | "
                         f"{result.maximum_element_mass_fraction_residual:.8g} | — |")
        for tolerance, step in ((1e-9, 1e-5), (1e-11, 5e-6)):
            trace = provider.closed_reactor(initial, np.linspace(0, .002, 401), constraint="UV",
                                             maximum_time_step_s=step, relative_tolerance=tolerance)
            event = temperature_rise_event(trace, 200)
            lines.append(f"| UV reactor T0={temperature}, rtol={tolerance:g} | "
                         f"{trace.snapshots[-1].state.temperature_k:.7g} | "
                         f"{trace.maximum_energy_residual_j_kg:.8g} | "
                         f"{trace.maximum_element_mass_fraction_residual:.8g} | "
                         f"[{event.lower_time_s:g}, {event.upper_time_s:g}] |")
    phase = provider._phase(ReactiveState(1000, 101325, mixture))
    phase.TP = 1000 - 1e-6, 101325
    before, cv = phase.int_energy_mass, phase.cv_mass
    phase.TP = 1000 + 1e-6, 101325
    jump = phase.int_energy_mass - before - 2e-6 * cv
    lines += ["", f"The installed mixture's fitted thermochemistry has an approximately {jump:.8g} J/kg "
              "internal-energy jump across 1000 K after subtracting the smooth sensible change. "
              "A run initialized on that breakpoint retains a matching residual even with tighter "
              "integration tolerances. Coefficients and energy references are not altered. "
              "The 1001 K case separates solver convergence from that fit discontinuity.", "",
              "## Freely propagating premixed flame", "",
              "At 310 K and 101325 Pa, with multicomponent transport and Soret diffusion. "
              "Refinement below is numerical evidence, not experimental flame-speed validation.", "",
              "| Width m | Slope / curvature | Points | Speed m/s | Relative mass-flux span |",
              "|---:|---|---:|---:|---:|"]
    speeds = []
    for width, slope, curve in ((.03, .10, .15), (.03, .05, .08), (.05, .05, .08)):
        result = provider.free_flame(ReactiveState(310, 101325, mixture),
                                      FlameSettings(width, refinement_slope=slope, refinement_curve=curve))
        lines.append(f"| {width:g} | {slope:g} / {curve:g} | {result.grid_points} | "
                     f"{result.speed_m_s:.8g} | {result.relative_mass_flux_span:.8g} |")
        speeds.append(result.speed_m_s)
        print("flame", width, slope, result.grid_points, result.speed_m_s, flush=True)
    lines += ["", f"Coarse-to-fine speed change: {abs(speeds[1]/speeds[0]-1):.6g}; "
              f"fine-grid domain-width change: {abs(speeds[2]/speeds[1]-1):.6g}.", "",
              "No frequency, ignition probability, detonation transition or injury criterion "
              "is inferred from these calculations."]
    (root / "research/native_cantera.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
