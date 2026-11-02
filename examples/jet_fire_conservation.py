"""Deferred diagnostic example of an unchanged native HyRAM flame.

The warm-source fixture is authored to exercise a native 200--6000 K caloric
domain. It is not a replay or repair of the earlier 300 K failed baseline.
No native import or physics occurs at this module's import.
"""

STATUS = "implemented_unverified_diagnostic_only"


def build_source(*, native_packages=None, upstream_temperature_k=500., ambient_temperature_k=310.):
    import sys
    from pathlib import Path

    if native_packages is not None:
        sys.path.insert(0, str(Path(native_packages).resolve()))
    from hyram.phys import Flame, Fluid, Orifice
    from hyram.phys._flame import calc_transmissivity

    from h2physics.adapters.hyram_flame import SteadyFlameWindow, run_hyram_flame
    from h2physics.core import Origin
    from h2physics.release import NozzleOpening, SourceLocation
    from h2physics.thermo.coolprop import CoolPropProperties

    clock = "authored-jet-fire-steady-clock"
    return run_hyram_flame(fluid_factory=Fluid, orifice_factory=Orifice, flame_factory=Flame,
        transmissivity_function=calc_transmissivity,
        upstream=CoolPropProperties("Hydrogen").state_pt(2e6, upstream_temperature_k),
        ambient=CoolPropProperties("Air").state_pt(101325., ambient_temperature_k),
        opening=NozzleOpening.circular("authored-2mm-native-only", .002,
            effective_area_factor=.8, area_basis_id="native-Cd-geometric-opening"),
        location=SourceLocation("authored-unaccepted-native-flame", clock,
            "authored-global-z-up", (0., 0., 2.), (1., 0., 0.)),
        window=SteadyFlameWindow(clock, 10., 20., "authored-steady-source-only",
            "authored-fixed-reservoir-established-flame", Origin.SYNTHETIC),
        solver_options={"Smax": 30., "tol": 1e-7, "n_pts_integral": 300},
        require_accepted=False)


def build_auditor(*, cutoff_widths=8., order=16, minimum_temperature_k=200.):
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_thermo import CanteraMolarEnthalpy
    from h2physics.adapters.hyram_flame_conservation import (
        ConservationInterpretation,
        ConservationQuadrature,
        HyRAMFlameConservation,
    )
    from h2physics.core import Origin

    if ct.__version__ != "3.2.0":
        raise ValueError("Use the already reviewed native Cantera3.2.0 fixture")
    raw = (Path(ct.__file__).parent/"data"/"nasa_gas.yaml").read_bytes()
    if hashlib.sha256(raw).hexdigest() != "4de6199d65d2d3db782e30573720c723130953707336add59713b02d8667e4db":
        raise ValueError("Installed NASA gas species differ from the source-inspected fixture")
    species = {s.name: s for s in ct.Species.list_from_yaml(raw.decode("utf-8"), section="species")}
    names = ("H2", "O2", "H2O", "N2", "CO2")
    phase = ct.Solution(thermo="ideal-gas", species=[species[name] for name in names],
                        name="native-five-species-caloric-diagnostic")
    basis = MechanismBasis("installed-Cantera3.2:nasa-gas-five-species", hashlib.sha256(raw).hexdigest(),
        "Cantera-BSD-3-Clause;NASA-TM-4513-public-US-government-work",
        ("https://ntrs.nasa.gov/citations/19940013151", "https://cantera.org/3.2/python/thermo.html"),
        minimum_temperature_k, 6000., 1e4, 5e6)
    provider = CanteraMolarEnthalpy(lambda: phase, basis, names)
    interpretation = ConservationInterpretation("authored-cross-model-caloric-diagnostic",
        "actual-HyRAM-expanded-H2-source-plane", "native-dry-O2-N2-3.76-surrogate-not-full-Air-composition",
        "normal-source-to-mechanism-spin-unresolved-assumption-diagnostic-only",
        "native-NASA-formation-reference-not-an-EOS-or-energy-zero-correction",
        "actual-native-Gaussian-mixture-fraction-and-velocity-ansatz", Origin.SYNTHETIC)
    quadrature = ConservationQuadrature(cutoff_widths, 32, order, 1e-9, .1, 1e-12)
    return HyRAMFlameConservation(provider, interpretation, quadrature)


def run_example(*, native_packages=None):
    source = build_source(native_packages=native_packages)
    auditor = build_auditor()
    last = len(source.native.S)-1
    result = auditor.audit(source, native_section_indices=(0, last//2, last))
    radiation = source.irradiance([[0., 3., 2.], [1., 3., 2.]], relative_humidity=.5,
        minimum_source_distance_m=.1, allow_rejected_flame=True)
    return auditor, result, auditor.bind_native_radiation(result, radiation)


def main():
    _, result, radiation = run_example(native_packages="artifacts/native_hyram_packages")
    print(result.status)
    print("Unclosed visible-domain energy rate W:", result.unclosed_visible_energy_rate_w)
    print("Heat identification:", result.required_heat_input_w)
    print("Whole jet fire accepted:", result.accepted, radiation.accepted)


if __name__ == "__main__":
    main()
