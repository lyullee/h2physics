"""Refresh the deferred-case inventory from metadata catalogs only.

This imports each declared validation.cases module and calls its cases() catalog.
It never resolves or invokes a scientific case entrypoint, configures a scheduler,
connects to Nurion or submits work.
"""

import ast
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from h2physics.catalog import model_catalog  # noqa: E402
from h2physics.cluster_validation import collect_cases  # noqa: E402

PLAN = ROOT / "validation/nurion_plan_example.py"
DOC = ROOT / "docs/NURION_VALIDATION_PLAN.md"
START = "<!-- BEGIN GENERATED CASE INVENTORY -->"
END = "<!-- END GENERATED CASE INVENTORY -->"
HISTORY_NOTE = (
    "This current metadata count supersedes intermediate case totals in dated checkpoint notes below."
)

UNVERIFIED_FAMILY_CASES = {
    "storage.extended_langmuir": {
        "finite-adsorption-vessel": ("competitive-extended-langmuir-multicomponent",),
    },
    "storage.solid_reaction": {
        "solid-reaction": (
            "solid-baseline", "solid-heat", "solid-water-feed", "solid-reference",
            "solid-startup-gas", "solid-finite-failure", "solid-negative", "solid-binding",
        ),
        "solid-reaction-native": ("solid-native-caloric",),
    },
    "storage.adsorption_delivery_mass_flow": {
        "finite-adsorption-vessel": ("adsorption-delivery-component-mass-flow",),
    },
    "storage.underground": {
        "underground-storage": (
            "underground-equilibrium", "underground-rock-exchange",
            "underground-injection-withdrawal", "underground-refinement",
        ),
    },
    "production.microbial_cell": {
        "microbial-cell": (
            "microbial-native-charge", "microbial-biomass-energy", "microbial-disconnected",
            "microbial-finite-failure", "microbial-boundary-guards",
            "microbial-original-result-binding",
        ),
        "microbial-observations": (
            "microbial-observation-current", "microbial-observation-integrity",
        ),
    },
    "production.energy_coupling": {
        "pv-electrolysis": (
            "pv-baseline", "pv-dark-isolated", "pv-no-root", "pv-water-depletion",
            "pv-delivery-pressure", "pv-receiver-domain", "pv-faradaic-heat",
            "pv-faradaic-efficiency-bounds",
            "pv-held-stage-refinement", "pv-caloric-reference", "pv-original-result",
            "pv-profile-midpoint-stages", "electrolysis-fuel-cell-single-batch-handoff",
            "electrochemical-hydrogen-storage-metered-round-trip-ledger",
            
        ),
    },
    "materials.integrity": {
        "fracture-fatigue": (
            "fracture-paris-si-exponential", "fracture-terminal-events-refinement",
            "fracture-hydrogen-native-constitutive", "fracture-arrest-restart-and-negatives",
            "elastic-cylinder-pressure-boundaries", "elastic-cylinder-pressure-samples",
            "elastic-cylinder-uniform-thermoelasticity", "cylinder-pressure-vessel-history-bridge",
            "fracture-block-sample-summary",
            "mendeley-ms1700-qp1180-normalized-permeation-ingest",
            "mendeley-ahss1300-source-bound-observations",
            "radial-hydrogen-concentration-eigenstrain",
            "cylindrical-transport-eigenstrain-bridge",
        ),
        "thermal-utilities": (
            "thermal-declared-balance", "thermal-negative-gates", "thermal-native-HX",
            "thermal-process-readers", "thermal-native-devices", "thermal-mutation-failure",
        ),
    },
    "release.droplets": {
        "droplet-transport": (
            "parcel-constant-heat", "parcel-ground-crossing", "parcel-initial-flash",
        ),
    },
    "release.impact": {
        "droplet-impact": (
            "impact-baseline", "impact-elastic", "impact-zero-contact", "impact-dryout",
            "impact-refinement", "impact-missing-heat", "impact-prefix",
            "impact-intercontact-heat", "impact-native-pool",
            "parcel-population-finite-impact-sequence",
        ),
    },
    "dispersion.obstacle": {
        "obstacle-dispersion": (
            "obstacle-zero-source", "obstacle-finite-pulse", "obstacle-obstacle-pair",
            "obstacle-refinement",
        ),
    },
    "dispersion.fixed_flow_snapshots": {
        "preferred-dispersion": ("hyram-finite-source-fixed-flow-snapshots",),
    },
    "dispersion.buoyant_layer": {
        "facility-protection": (
            "two-vent-hydrogen-buoyant-layer-accumulation",
            "two-vent-layer-dry-air-oxygen-composition-projection",
        ),
    },
    "dispersion.compartment_network": {
        "oxygen-deficiency": ("hydrogen-fixed-state-compartment-network-mixing-closure",),
    },
    "combustion.laminar_flame": {
        "counterflow-flame": (
            "counterflow-native-profile", "counterflow-strain-definitions",
            "counterflow-profile-sampling", "counterflow-pressure-admission",
        ),
        "counterflow-data": ("counterflow-extinction-data-ingest",),
    },
    "combustion.jet_fire": {
        "jet-fire-conservation": (
            "jet-conservation-rejection", "jet-conservation-quadrature",
            "jet-conservation-domain", "jet-conservation-binding",
            "jet-conservation-radiation", "jet-conservation-energy",
        ),
        "jet-fire-radiation": (
            "jet-radiation-far-field", "jet-radiation-attenuation",
            "jet-radiation-refinement", "jet-radiation-domain",
        ),
    },
    "combustion.pool_fire": {
        "pool-fire": (
            "pool-fire-baseline", "pool-fire-geometry", "pool-fire-refinement",
            "pool-fire-heat-budget", "pool-fire-oxygen", "pool-fire-geometry-rejection",
            "pool-fire-prefix", "pool-fire-native-pool",
        ),
        "pool-energy-contract": ("native-pool-accepted-edge-energy-contract",),
        "thermal-target": (
            "thermal-target-pulse", "thermal-target-lossless",
            "thermal-target-refinement", "thermal-target-domain",
        ),
    },
    "combustion.flash_fire": {
        "flash-front": (
            "flash-front-axial", "flash-front-gaps", "flash-front-binding",
            "flash-front-native-refinement",
        ),
    },
    "combustion.piston_engine": {
        "hydrogen-engine": (
            "hydrogen-engine-slider-crank-geometry",
            "hydrogen-engine-input-admission",
            "hydrogen-engine-boundary-schedule-contract",
            "hydrogen-engine-crank-schedule-conversion",
            "hydrogen-engine-native-closed-charge",
            "hydrogen-engine-piston-heat-flux-schedule",
            "hydrogen-engine-failure-prefix",
            "hydrogen-engine-boundary-stream-ledger",
            "hydrogen-engine-open-control-volume-forced-flow",
            "hydrogen-engine-native-pressure-valve-boundary",
            "hydrogen-engine-crank-angle-fuel-delivery-native-flow",
            "hydrogen-engine-open-cylinder-shared-nozzle-inlet",
            "hydrogen-engine-wall-gas-coupling-energy-ledger",
            "hydrogen-engine-wall-zero-UA-reduction",
            "hydrogen-engine-wall-external-boundary-ledger",
        ),
    },
    "combustion.gas_turbine": {
        "hydrogen-engine": (
            "hydrogen-brayton-reference",
            "hydrogen-brayton-input-guards",
            "hydrogen-brayton-summary-integrity",
            "hydrogen-brayton-compressor-turbine-map-pair",
            "hydrogen-brayton-bounded-map-operating-point-solve",
            "hydrogen-brayton-operating-point-incomplete-seed-search",
            "hydrogen-brayton-compressor-bleed-zero-limit",
            "hydrogen-brayton-compressor-bleed-mixed-turbine",
            "hydrogen-brayton-cooling-pressure-rejection",
            "hydrogen-brayton-cooling-speed-link-rejection",
        ),
    },
    "effects.rupture": {
        "fracture-fatigue": (
            "vessel-native-capacity-units", "vessel-thermal-initiation-refinement",
            "vessel-native-finite-storage-binding", "vessel-domains-failure-retention",
        ),
    },
    "effects.fragment_trajectory": {
        "fragment-trajectory": ("conditional-fragment-flight-impact",),
    },
    "facility.monitoring": {
        "facility-protection": (
            "facility-concentration-alarm",
            "sensor-time-constant-calibration-recovery",
            "sensor-time-constant-calibration-rejections",
            "two-vent-layer-oxygen-deficit-sensor-alarm-handoff",
        ),
    },
    "facility.detector_reliability": {
        "facility-protection": (
            "kofn-detector-common-cause-reliability",
            "kofn-detector-versioned-trial-evidence",
        ),
    },
    "materials.diffusion": {
        "material-transport": (
            "power-law-solubility-diffusion-boundary",
            "quasi-steady-permeation-history",
            "steady-permeation-surface-resistance",
            "hydrogen-diffusion-surface-film-boundary",
            "cylindrical-shell-hydrogen-diffusion",
            "radial-hydrogen-diffusion-shell-api",
            "diffusion-outward-h2-finite-source-handoff",
        ),
    },
    "research.economics": {
        "hydrogen-economics": (
            "economics-native-direct", "economics-finite-link", "economics-undiscounted",
            "economics-negative", "economics-failure-retention", "economics-public-projection",
            "economics-source-cache",
        ),
        "microbial-economics": (
            "mec-economics-owner", "mec-economics-link", "mec-economics-guards",
            "mec-economics-failure", "mec-economics-public-projection",
            "mec-economics-producer-mutation",
        ),
    },
}


def _call_arguments(node, function_name):
    calls = [
        item for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and isinstance(item.func, ast.Name)
        and item.func.id == function_name
    ]
    if len(calls) != 1:
        raise ValueError(f"Expected one {function_name}(...) declaration")
    values = []
    for argument in calls[0].args:
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
            raise ValueError(f"{function_name} arguments must be literal module names")
        values.append(argument.value)
    return values


def _configured_profiles(tree):
    assignments = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PROFILES"
                for target in node.targets)
    ]
    if len(assignments) != 1 or not isinstance(assignments[0].value, ast.DictComp):
        raise ValueError("PROFILES must retain its explicit metadata-comprehension form")
    generator = assignments[0].value.generators[0]
    if not isinstance(generator.iter, ast.Tuple):
        raise ValueError("Profile declarations must remain explicit tuple entries")
    names = []
    for entry in generator.iter.elts:
        if (not isinstance(entry, ast.Tuple) or not entry.elts
                or not isinstance(entry.elts[0], ast.Constant)
                or not isinstance(entry.elts[0].value, str)):
            raise ValueError("Every profile needs a literal name")
        names.append(entry.elts[0].value)
    if len(names) != len(set(names)):
        raise ValueError("Profile names must be unique")
    return set(names)


def _inventory():
    tree = ast.parse(PLAN.read_text(encoding="utf-8"))
    modules = _call_arguments(tree, "collect_cases")
    if len(modules) != len(set(modules)):
        raise ValueError("Case modules must be listed once")
    configured = _configured_profiles(tree)
    for module in modules:
        case_file = ROOT.joinpath(*module.split(".")).with_suffix(".py")
        if not case_file.is_file():
            raise FileNotFoundError(case_file)
    cases = collect_cases(*modules)
    identifiers = [case.identifier for case in cases]
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError("Deferred case identifiers must be nonempty and globally unique")
    by_profile = Counter(case.profile for case in cases)
    unconfigured = set(by_profile) - configured
    unused = configured - set(by_profile)
    if unconfigured or unused:
        raise ValueError(f"Case/profile mismatch: unconfigured={unconfigured}; unused={unused}")
    unverified = {
        spec.identifier for spec in model_catalog()
        if spec.status == "implemented_unverified"
    }
    if unverified != set(UNVERIFIED_FAMILY_CASES):
        raise ValueError(
            "Update family/profile ownership mapping: "
            f"unmapped={unverified - set(UNVERIFIED_FAMILY_CASES)}; "
            f"no-longer-unverified={set(UNVERIFIED_FAMILY_CASES) - unverified}"
        )
    by_identifier = {case.identifier: case for case in cases}
    invalid_mappings = {}
    for family, profile_cases in UNVERIFIED_FAMILY_CASES.items():
        for profile, identifiers in profile_cases.items():
            for identifier in identifiers:
                case = by_identifier.get(identifier)
                if case is None or case.profile != profile:
                    invalid_mappings.setdefault(family, []).append(
                        (identifier, profile, case.profile if case else None)
                    )
    if invalid_mappings:
        raise ValueError(f"Family-to-case/profile mapping is invalid: {invalid_mappings}")
    empty_mappings = [
        family for family, profile_cases in UNVERIFIED_FAMILY_CASES.items()
        if not profile_cases or any(not ids for ids in profile_cases.values())
    ]
    if empty_mappings:
        raise ValueError(f"Every unverified family/profile needs case IDs: {empty_mappings}")
    return modules, cases, by_profile, unverified


def _render(modules, cases, by_profile, unverified):
    rows = [
        START,
        f"**Current metadata inventory:** {len(cases)} deferred case definitions across "
        f"{len(by_profile)} declared environment profiles and {len(modules)} case modules.",
        "These are authored plans, not executions or accepted scientific evidence. "
        "The inventory imports only each module's cases() metadata catalog; case entrypoints, "
        "models, native engines and schedulers are not run.",
        "",
        "| Profile | Deferred cases |",
        "|---|---:|",
    ]
    rows.extend(f"| {profile} | {count} |" for profile, count in sorted(by_profile.items()))
    rows.extend(("", "**Associated deferred profiles for implemented-unverified families:**", "",
                 "| Catalog family | Deferred profiles |", "|---|---|"))
    rows.extend(
        f"| {family} | {', '.join(UNVERIFIED_FAMILY_CASES[family])} |"
        for family in sorted(unverified)
    )
    rows.extend(("", "**Case IDs mapped to each unverified family (planned only):**", "",
                 "| Catalog family | Profile | Deferred case IDs |",
                 "|---|---|---|"))
    rows.extend(
        f"| {family} | {profile} | {', '.join(identifiers)} |"
        for family in sorted(unverified)
        for profile, identifiers in UNVERIFIED_FAMILY_CASES[family].items()
    )
    rows.extend(("", HISTORY_NOTE, END, ""))
    return "\n".join(rows)


def main():
    modules, cases, by_profile, unverified = _inventory()
    document = DOC.read_text(encoding="utf-8")
    if document.count(START) != 1 or document.count(END) != 1:
        raise ValueError("Validation plan must contain one generated inventory marker pair")
    before, remainder = document.split(START, 1)
    _, after = remainder.split(END, 1)
    after = after.replace(HISTORY_NOTE, "")
    DOC.write_text(
        before.rstrip("\n") + "\n\n"
        + _render(modules, cases, by_profile, unverified) + "\n"
        + after.lstrip("\n"),
        encoding="utf-8",
    )
    print(f"{len(cases)} deferred cases; {len(by_profile)} profiles; {len(modules)} modules")


if __name__ == "__main__":
    main()
