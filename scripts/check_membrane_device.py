"""Execute both finite native sides, independent limits and retaining failures."""

import hashlib
import importlib.metadata
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_membrane import (
    CanteraDustyGasTransport,
    MembraneEndpoint,
    MembraneTransportEvidence,
    PorousTransportGeometry,
)
from h2physics.adapters.cantera_membrane_device import (
    CanteraFiniteMembraneDevice,
    FiniteMembraneIntegrationError,
    FiniteMembraneParameters,
    MembraneIntegrationSettings,
)
from h2physics.core import Origin


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import cantera as ct

    root = Path(__file__).resolve().parents[1]
    host_names = ("src/h2physics/adapters/cantera_membrane_device.py", "tests/test_cantera_membrane_device.py",
        "scripts/check_membrane_device.py", "docs/FINITE_MEMBRANE_DEVICE.md",
        "src/h2physics/adapters/cantera_membrane.py", "src/h2physics/adapters/cantera_volume.py",
        "src/h2physics/adapters/cantera.py", "src/h2physics/core.py")
    before = {name: sha(root/name) for name in host_names}
    data_file = Path(ct.__file__).parent/"data/h2o2.yaml"
    raw = data_file.read_bytes()
    distribution = importlib.metadata.distribution("cantera")
    license_path = next(Path(distribution.locate_file(p)) for p in distribution.files
                        if str(p).endswith("licenses/License.txt"))
    native_paths = {"installed h2o2.yaml": data_file, "Cantera license": license_path,
                    "Cantera compiled extension": Path(ct._cantera.__file__)}
    native_before = {name: sha(path) for name, path in native_paths.items()}
    names = ("H2", "N2", "AR")
    def factory():
        species = {s.name: s for s in ct.Species.list_from_yaml(raw.decode(), "species")}
        phase = ct.Solution(thermo="ideal-gas", species=[species[n] for n in names],
                            transport_model="multicomponent")
        phase.TPX = 330., 101325., [.7, .2, .1]
        return phase
    basis = MechanismBasis("installed-h2o2-authored-frozen-H2-N2-Ar", sha(data_file),
        "Cantera BSD-3-Clause; upstream GRI species and transport provenance",
        ("https://cantera.org/3.2/python/transport.html",), 300., 1000., .001, 2e5)
    evidence = MembraneTransportEvidence("installed-native-transport", "warm-frozen-gas", "neutral-ideal-gas",
        "native-NASA-formation-reference", "native-H2-spin-unresolved")
    geometry = PorousTransportGeometry(.35, 2.5, 50e-9, 0., .001, "authored-pore",
                                       "authored-no-material-validation", Origin.SYNTHETIC)
    parameters = FiniteMembraneParameters(.005, .02, .02, "authored-absolute-clock", 100., 140.,
        "separate-fixed-330K-thermostats", "authored-finite-device", Origin.SYNTHETIC)
    def endpoint(name, fractions, pressure=101325.):
        return MembraneEndpoint(330., pressure, names, fractions, "mole", name, evidence.gas_phase_id,
            geometry.geometry_id, "authored-finite-initial-state", Origin.SYNTHETIC)
    left, right = endpoint("left", [.7, .2, .1]), endpoint("right", [.4, .5, .1])
    def solve(a=left, b=right, *, time=(100., 101., 102.), p=parameters, settings=MembraneIntegrationSettings()):
        device = CanteraFiniteMembraneDevice(CanteraDustyGasTransport(factory, basis, evidence=evidence))
        return device.run(a, b, geometry, p, time, settings=settings)

    started = perf_counter()
    base = solve()
    refined = solve(settings=MembraneIntegrationSettings(maximum_time_step_s=.025,
        relative_tolerance=2e-11, absolute_tolerance=1e-17))
    equal = solve(b=replace(left, boundary_id="right"))
    reverse = solve(right, left)
    area_scaled = solve(time=(100., 101.), p=replace(parameters, area_m2=.01))
    dt = 1e-4
    short = solve(time=(100., 100.+dt), settings=MembraneIntegrationSettings(maximum_time_step_s=dt/5,
        relative_tolerance=1e-11, absolute_tolerance=1e-18))
    mw = base.native.reactors[0].phase.molecular_weights/1000.
    observed = (short.snapshots[-1].species_mass_kg-short.snapshots[0].species_mass_kg)/dt
    initial_source = short.snapshots[0].molar_flux_mol_m2_s*mw*parameters.area_m2
    source_expected = np.array([-initial_source, initial_source])
    derivative_error = float(np.max(abs(observed-source_expected))/np.max(abs(source_expected)))
    low = solve(endpoint("left", [.7, .2, .1], .01), endpoint("right", [.4, .5, .1], .01),
        time=(100., 110., 120.), settings=MembraneIntegrationSettings(maximum_time_step_s=.2,
            relative_tolerance=1e-10, absolute_tolerance=1e-22,
            minimum_side_inventory_kg=(1e-18, 1e-18), energy_ledger_scale_j=1e-3))
    initial_mol = low.snapshots[0].species_mass_kg/mw
    d = 2/3*geometry.mean_pore_radius_m*geometry.porosity/geometry.tortuosity*np.sqrt(
        8*(ct.gas_constant/1000)*330/(np.pi*mw))
    rate = parameters.area_m2*d/geometry.thickness_m*(1/parameters.left_volume_m3+1/parameters.right_volume_m3)
    asymptote = initial_mol.sum(axis=0)*parameters.left_volume_m3/(parameters.left_volume_m3+parameters.right_volume_m3)
    oracle = asymptote+(initial_mol[0]-asymptote)*np.exp(-rate*20.)
    actual = low.snapshots[-1].species_mass_kg[0]/mw
    knudsen_error = float(np.max(abs(actual-oracle)/abs(oracle)))
    refinement = float(np.max(abs(base.snapshots[-1].species_mass_kg-refined.snapshots[-1].species_mass_kg)))
    reversal = float(np.max(abs(base.snapshots[-1].species_mass_kg[::-1]-reverse.snapshots[-1].species_mass_kg)))
    area_error = float(np.max(abs(base.snapshots[-1].species_mass_kg-area_scaled.snapshots[-1].species_mass_kg)))
    native_right = factory()
    native_right.TPX = 330., 101325., right.fractions
    minimum = native_right.density_mass*parameters.right_volume_m3*.9999
    failures = {}
    for label, times, settings in (
        ("right inventory guard", (100., 100.001, 102.), MembraneIntegrationSettings(maximum_time_step_s=.02,
            minimum_side_inventory_kg=(1e-12, minimum))),
        ("rejected native trial extension", (100., 101., 102.), MembraneIntegrationSettings(trial_sum_deviation_budget=1e-16)),
        ("post-completed independent audit", (100., 101., 102.), MembraneIntegrationSettings(
            species_audit_absolute_kg=1e-30, energy_audit_absolute_j=1e-30, audit_relative=1e-30))):
        try:
            solve(time=times, settings=settings)
        except FiniteMembraneIntegrationError as error:
            failures[label] = error
    probe = solve(time=(100., 100.001))
    connection = probe.native.connection
    connection.kernel.permeability, connection.kernel.mean_pore_radius = 1e-8, 1e-4
    restored_rate = connection.rates(100.002)/parameters.area_m2*1000.
    pore_reset_error = float(np.max(abs(restored_rate-probe.snapshots[-1].molar_flux_mol_m2_s)))
    source = probe.native.initial_transport_result.source_phase
    source.set_binary_diff_coeffs_polynomial(0, 1, source.get_binary_diff_coeffs_polynomial(0, 1)*1.01)
    source_rejected = False
    try:
        connection.rates(100.003)
    except ValueError:
        source_rejected = connection.first_error is not None
    references = (base, refined, equal, reverse, area_scaled, short, low)
    max_species_error = max(float(np.max(abs(t.side_species_residual_kg))) for t in references)
    max_combined_mass = max(float(np.max(abs(t.combined_mass_residual_kg))) for t in references)
    max_energy_error = max(float(np.max(abs(t.side_energy_residual_j))) for t in references)
    max_combined_u = max(float(np.max(abs(t.combined_internal_energy_residual_j))) for t in references)
    after = {name: sha(root/name) for name in host_names}
    native_after = {name: sha(path) for name, path in native_paths.items()}
    gates = {
        "both finite native reactors in one actual network": all(len(t.native.reactors) == 2
            and isinstance(t.native.network, ct.ReactorNet) for t in references),
        "independent short-time native source units and gross area <2e-5 relative": derivative_error < 2e-5,
        "finite pressure/composition feedback and counterdiffusion": base.snapshots[-1].sides[0].pressure_pa < 101325.
            < base.snapshots[-1].sides[1].pressure_pa and base.snapshots[0].molar_flux_mol_m2_s[0] > 0
            > base.snapshots[0].molar_flux_mol_m2_s[1],
        "equal states remain stationary": np.max(abs(equal.species_transfer_kg)) < 1e-20,
        "side species and combined mass close": max_species_error < 1e-11 and max_combined_mass < 1e-11,
        "each-side U=H+Q and combined U close": max_energy_error < 1e-7 and max_combined_u < 1e-7,
        "separate required thermostats cancel at common T": np.max(abs(base.thermostat_heat_j.sum(axis=1))) < 1e-8,
        "reversed sides swap inventories <1e-11 kg": reversal < 1e-11,
        "gross area-time scaling <1e-11 kg": area_error < 1e-11,
        "native maximum-step/tolerance refinement <1e-11 kg": refinement < 1e-11,
        "independent finite Knudsen exponential limit <2e-7 relative": knudsen_error < 2e-7,
        "native raw trial and accepted deviations recorded separately": base.maximum_native_trial_sum_deviation > 1e-10
            and base.maximum_accepted_sum_deviation < 1e-12 and base.maximum_native_trial_relative_volume_deviation > 0,
        "actual depletion/trial/audit failures retain raw objects and causes": len(failures) == 3
            and all(len(e.native_states) == 2 and e.__cause__ is not None for e in failures.values())
            and failures["right inventory guard"].last_accepted_time_s == 100.001
            and failures["post-completed independent audit"].trace is not None,
        "private kernel pore reset and source polynomial guard": pore_reset_error < 1e-12 and source_rejected,
        "host/test/script/docs and reused sources unchanged": before == after,
        "native data/license/binary unchanged": native_before == native_after,
        "new host inputs are LF text": all(b"\r" not in (root/name).read_bytes() for name in host_names[:4]),
    }
    elapsed = perf_counter()-started
    rows = ["# Finite two-side native porous membrane reference", "",
        "Reproduce: `python scripts/check_membrane_device.py` with optional Cantera3.2.", "",
        f"Actual Cantera{ct.__version__}; seven accepted reference trajectories, a separate mutable-object guard probe "
        f"and three retained failure probes took {elapsed:.6g}s. No native implementation or dataset is bundled.", "",
        "Original warm H2/N2/Ar inputs:330K,101325Pa; mole fractions left(.7,.2,.1),right(.4,.5,.1); "
        "both finite rigid volumes.02m3, gross membrane area.005m2, thickness.001m, pore radius50nm, porosity.35, "
        "native tortuosity factor2.5 and explicit zero permeability. All are authored fixtures, not measured membrane data. "
        "The native signed stationary-solid flux is multiplied by gross area once, with no extra epsilon or product-fraction normalization.", "",
        "Existing constitutive preparation supplies independently owned actual native phases and a private DustyGas. "
        "Two native ExtensibleIdealGasReactors in one ReactorNet own finite mass/species/dilution; public bulk-source hook sdot uses kmol/s. "
        "No physical mass/species derivative is copied or replaced. CVODES also integrates appended species/H/thermostat ledgers. "
        "Both sides are frozen ideal gas with the same native NASA formation reference and mechanism-unresolved H2 spin; no pure-fluid caloric-zero substitution.", "",
        "Native energy is off to prescribe the same T on both sides. Signed transferred partial H and required thermostat Q=(u-h) dotted "
        "with native species transfer are separate. Each rigid-side deltaU=Htransfer+Q closes; combined species/mass/U are conserved. "
        "This is not an adiabatic device or a prediction of membrane thermal flux, wall storage or heat-recovery performance.", "",
        "| Actual check | Value |", "|---|---:|",
        f"| left final pressure Pa at102s | {base.snapshots[-1].sides[0].pressure_pa:.12g} |",
        f"| right final pressure Pa at102s | {base.snapshots[-1].sides[1].pressure_pa:.12g} |",
        f"| left required thermostat Q J | {base.thermostat_heat_j[-1,0]:.12g} |",
        f"| right required thermostat Q J | {base.thermostat_heat_j[-1,1]:.12g} |",
        f"| short-time native source/area relative error | {derivative_error:.12g} |",
        f"| max side species residual kg | {max_species_error:.12g} |",
        f"| max combined mass residual kg | {max_combined_mass:.12g} |",
        f"| max side U-H-Q residual J | {max_energy_error:.12g} |",
        f"| max combined U residual J | {max_combined_u:.12g} |",
        f"| reversal inventory error kg | {reversal:.12g} |",
        f"| area-time scaling inventory error kg | {area_error:.12g} |",
        f"| maximum-step/tolerance refinement error kg | {refinement:.12g} |",
        f"| finite Knudsen exponential relative error | {knudsen_error:.12g} |",
        f"| private pore reset flux error mol/m2/s | {pore_reset_error:.12g} |", "",
        "The short-time derivative uses.0001s and the actual initial native flux times molecular weights and gross area. "
        "Refinement changes native maxstep.1→.025s, rtol1e-9→2e-11, atol1e-15→1e-17. "
        "The independent finite-volume analytic oracle uses the dilute Knudsen limit at.01Pa for20s: each concentration difference "
        "decays exponentially with rate A*D_eff/L*(1/V_left+1/V_right), preserving each total species amount. "
        "D_eff uses the published/native Knudsen limit. No equilibrium solver or second trajectory ODE generates that oracle.", "",
        "| Native/accepted numerical admission | Observed maximum |", "|---|---:|",
        f"| raw native trial Y sum deviation | {base.maximum_native_trial_sum_deviation:.12g} |",
        f"| sampled accepted Y sum deviation | {base.maximum_accepted_sum_deviation:.12g} |",
        f"| raw native trial T deviation K | {base.maximum_native_trial_temperature_deviation_k:.12g} |",
        f"| raw native trial relative volume deviation | {base.maximum_native_trial_relative_volume_deviation:.12g} |",
        f"| actual evaluated absolute clock range s | {base.evaluated_clock_bounds_s} |", "",
        "Raw native NoNorm trial species concentrations are passed without host clipping or renormalization. "
        "The explicit constant-T numerical extension admits trial sum and relative T/V deviations up to1e-6; accepted sampled sum budget is1e-10 "
        "with exact prescribed T/volume. Native trial type is unobservable; extrema are not labeled proven FD probes. "
        "Native DustyGas uses a Tiny mean-mole-fraction floor internally; this is not epsilon inventory added to the two finite sides. "
        "Internal clipping/regularization history is not available through the API.", "",
        "| Retained rejected probe | Accepted prefix length | Last accepted s | First triggering s | Native time s | Completed trace | First reason |", "|---|---:|---:|---:|---:|---|---|"]
    for name, error in failures.items():
        cause = error.native.connection.first_error or error.__cause__
        reason = " ".join(str(cause).split())[:250]
        rows.append(f"| {name} | {len(error.snapshots)} | {error.last_accepted_time_s} | {error.triggering_time_s} | "
                    f"{error.native_time_s:.12g} | {error.trace is not None} | {reason} |")
    rows.extend(["", "Inventory rejection uses a right-side limit99.99% of its initial native mass. It retains the actual first offending state/time "
        "and a previously accepted sample, not an exact depletion event root. A deliberately overstrict trial budget and a post-completed "
        "independent audit budget also fail visibly. All errors retain actual ReactorNet/reactors, native states/ledgers, accepted prefix and original cause. "
        "The first boundary error is sticky even if CVODES would retry. Native failure probes can print native small-step warnings; they are not hidden or repaired.", "",
        "A separate completed probe is intentionally edited after return to verify pore reset and source-polynomial rejection; its edits invalidate "
        "that mutable object's recorded trace. The seven accepted reference trajectories are not edited. Each coupling checks source state/basis, "
        "owned/source thermo and transport polynomials, private kernel definition, reactor configuration and evidence binding. "
        "The private kernel has no user callbacks and its write-only pore values are reset before evaluating a changed state.", "",
        "| Verification gate | Pass |", "|---|---|"])
    rows.extend(f"| {name} | {passed} |" for name, passed in gates.items())
    rows.extend(["", "No independent measured membrane/device comparison has been performed. Physical material selectivity, adsorption/storage, "
        "layer resolution, nonisothermal transport, heat capacity/conduction, supported depletion events/restarts, products/separation work and "
        "facility operation require additional native models and evidence. No production efficiency, validated recovery or complete thermal membrane is claimed.", "",
        "Primary sources: [extensible native reactors](https://cantera.org/3.2/python/zerodim.html#extensiblereactor), "
        "[native ideal-gas control volume](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html), "
        "[DustyGas API](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport), "
        "[versioned hook units](https://github.com/Cantera/cantera/blob/v3.2.0/src/zeroD/IdealGasReactor.cpp). "
        "Cantera implementation is BSD-3-Clause; separately installed upstream thermochemical/transport provenance is retained. No mechanism/coefficients are redistributed.", "",
        "## Source fingerprints", "", "| Host input | Begin SHA256 | End SHA256 |", "|---|---|---|"])
    rows.extend(f"| {name} | {before[name]} | {after[name]} |" for name in host_names)
    rows.extend(["", "| Installed input | Begin SHA256 | End SHA256 |", "|---|---|---|"])
    rows.extend(f"| {name} | {native_before[name]} | {native_after[name]} |" for name in native_paths)
    rows.extend(["", f"Source phase exact hash: `{base.native.initial_transport_result.source_phase_sha256}`. "
        f"Owned phase exact hashes: `{base.native.initial_transport_result.phase_copy_audits[0].owned_fingerprint}`, "
        f"`{base.native.initial_transport_result.phase_copy_audits[1].owned_fingerprint}`. "
        "New host/report text is LF; native source and compiled inputs are unchanged."])
    (root/"research/finite_membrane_device.md").write_text("\n".join(rows)+"\n", encoding="utf-8", newline="\n")
    print(f"Finite native membrane: {sum(gates.values())}/{len(gates)} gates passed in {elapsed:.6g}s")
    for name, passed in gates.items():
        if not passed:
            print("FAILED:", name)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
