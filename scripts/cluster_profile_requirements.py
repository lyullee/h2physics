"""Generate curated cluster profile requirements using stdlib AST/source reads only.

No validation module, model, optional library, setup script or scheduler is imported
or executed. This report declares prerequisites; it is not an installer or an
attestation that the selected interpreter contains them.
"""

import ast
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Deliberately curated capability sets, not dependency guesses from profile names.
PROFILE_CAPABILITIES = {
    "pv-electrolysis": ("thermo", "pvlib", "lh2dt"),
    "fracture-fatigue": ("thermo", "helpr", "data"),
    "solid-reaction": (), "solid-reaction-native": ("chemistry",),
    "finite-hydride": ("thermo",),
    "hydride-compressor": ("thermo", "lh2dt"),
    "pool-fire": ("thermo", "risk"), "hydrogen-economics": ("pyh2a",),
    "droplet-transport": ("thermo", "hydraulics"),
    "droplet-impact": ("thermo", "pool"),
    "underground-storage": ("thermo", "uh2sc"),
    "biological-process": ("biological",),
    "microbial-cell": ("chemistry",), "flash-front": ("chemistry",),
    "obstacle-dispersion": ("fds",),
    "jet-fire-conservation": ("thermo", "preferred", "chemistry"),
    "microbial-economics": ("chemistry", "pyh2a"),
    "microbial-observations": (),
    "source-data-ingestion": ("data",),
    "preferred-dispersion": ("preferred",),
    "carrier-conversion": (), "carrier-conversion-native": ("chemistry",),
    "compressor-boundaries": ("thermo", "lh2dt"),
    "heat-exchanger-boundaries": ("thermo", "lh2dt"),
    "facility-protection": ("thermo", "lh2dt", "hydraulics", "chemistry", "monitoring", "risk"),
    "joint-uncertainty": ("thermo", "uncertainty"),
    "porous-reservoir": ("thermo",),
    "fragment-trajectory": (),
    "model-selection": ("thermo", "uncertainty", "chemistry", "lh2dt", "preferred"),
    "fuel-cell": ("thermo",), "fuel-cell-native": ("chemistry",),
    "finite-transfer": ("thermo", "lh2dt"),
    "thermal-utilities": ("thermo", "lh2dt"),
    "finite-adsorption-vessel": ("thermo", "psa"),
    "valve-actuator": ("thermo", "lh2dt"),
    "finite-relief-lift": ("thermo", "lh2dt"),
    "facility-continuity": ("thermo", "lh2dt"),
    "pump-operation": ("thermo", "lh2dt"),
    "electrochemical-thermal": ("thermo", "pvlib", "lh2dt"),
    "compressor-map": ("thermo", "lh2dt"),
    "flowing-heat-exchanger": ("thermo", "lh2dt"),
    "reliquefier-product": ("thermo", "lh2dt"),
    "counterflow-heat-exchanger": ("thermo",),
    "thermal-target": (), "jet-fire-radiation": ("thermo", "preferred"),
    "counterflow-flame": ("chemistry",), "counterflow-data": (),
    "hydrogen-engine": ("chemistry", "thermo"),
    "buried-pipeline-data": (),
    "hydrogen-channel-data": (),
    "gas-compressible-pipe": (),
    "photochemistry": (),
    "gas-composition": ("thermo", "lh2dt"),
    "mixture-vle": ("thermo",), "pool-energy-contract": (),
    "oxygen-deficiency": ("chemistry",),
    "hyram-overpressure": ("hyram-overpressure",),
    "detonation-native": ("detonation", "chemistry"),
}

# Optional extras and separately reviewed source recipes are distinct routes.
CAPABILITIES = {
    "thermo": ("extra thermo: CoolProp", "docs/DEPENDENCIES.md"),
    "data": ("extra data: openpyxl for source workbook admission", "docs/DATA.md"),
    "chemistry": ("extra chemistry; finite gas-volume routes require Cantera 3.2.x", "research/native_cantera.md"),
    "uncertainty": ("extra uncertainty: SciPy>=1.15", "src/h2physics/uncertainty.py"),
    "hydraulics": ("extra hydraulics: fluids", "docs/HYDRAULICS.md"),
    "pool": ("extra pool: DynamicLH2PoolX", "research/native_pool.md"),
    "risk": ("extra risk", "requirements/native-risk.txt"),
    "pvlib": ("separate native pvlib installation", "research/pvlib_dependency.toml"),
    "lh2dt": ("separate pinned native LH2DT; no host extra installs it", "research/native_lh2dt.toml"),
    "psa": ("separate pinned native PSA-Dyna; no host extra installs it", "research/native_psa.md"),
    "helpr": ("separate pinned native HELPR", "research/fracture_dependency.toml"),
    "pyh2a": ("separate reviewed native pyH2A", "research/economics_dependency.toml"),
    "uh2sc": ("separate pinned native UH2SC Linux environment", "research/underground_storage_dependency.toml"),
    "fds": ("external reviewed FDS executable/MPI runtime", "research/obstacle_dispersion_dependency.toml"),
    "preferred": ("separate HyRAM/SLABx-LH2 compatible environment", "requirements/native-preferred-dispersion.txt"),
    "biological": ("separate pinned QSDsan/BioSTEAM/thermosteam environment", "requirements/native-biological.txt"),
    "monitoring": ("separate reviewed process-monitoring toolkit", "requirements/native-monitoring.txt"),
    "hyram-overpressure": ("separate pinned native HyRAM/Bauwens environment", "requirements/native-hyram-overpressure.txt"),
    "detonation": ("reviewed Caltech SDToolbox artifact with Cantera 3.2", "docs/NATIVE_DETONATION.md"),
}


def source_inventory():
    plan = ast.parse((ROOT/"validation/nurion_plan_example.py").read_text(encoding="utf-8"))
    profiles = {}
    modules = []
    for node in ast.walk(plan):
        if (isinstance(node, ast.Tuple) and len(node.elts) == 2
                and all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in node.elts)
                and node.elts[1].value.startswith("H2_CLUSTER_")):
            profiles[node.elts[0].value] = node.elts[1].value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "collect_cases":
            modules = [ast.literal_eval(argument) for argument in node.args]
    if set(profiles) != set(PROFILE_CAPABILITIES):
        raise ValueError("Curated profile map differs from plan: " + repr(set(profiles)^set(PROFILE_CAPABILITIES)))
    declarations = {name: [] for name in profiles}
    unresolved = []
    for module in modules:
        path = ROOT/(module.replace(".", "/")+".py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        literals = {node.value for node in ast.walk(tree)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        matches = set(profiles)&literals
        if not matches:
            unresolved.append(module)
        for profile in matches:
            declarations[profile].append(module)
    return profiles, declarations, unresolved


def main():
    profiles, declarations, unresolved = source_inventory()
    project = tomllib.loads((ROOT/"pyproject.toml").read_text(encoding="utf-8"))
    lines = ["# Cluster profile source requirements", "",
        "Generated by `scripts/cluster_profile_requirements.py` using stdlib AST/file reads only.",
        "No model, metadata entrypoint, installation, native import or scheduler ran.", "",
        "Every profile requires the host Python>=3.12 environment and core NumPy/SciPy.",
        "The curated capability sets below declare additional routes; they do not prove an",
        "interpreter satisfies them. Confirm actual versions/rights and pin each setup hash.", "",
        "| Profile | Setup environment prefix | Explicit capabilities | Source-declared case modules |",
        "|---|---|---|---|"]
    for name, prefix in profiles.items():
        lines.append(f"| {name} | `{prefix}` | {', '.join(PROFILE_CAPABILITIES[name]) or 'core only'} | "
                     + ", ".join(f"`{module}`" for module in declarations[name])+" |")
    lines += ["", "Module associations come from exact profile string literals in source, including",
              "definition tuples; no cases() function is called. Dynamically assembled profile",
              "declarations need separate metadata reconciliation with validation_inventory.py.", "",
              "## Explicit capability routes", "",
              "| Capability | Install/runtime contract | Source/rights record |", "|---|---|---|"]
    for name, (description, record) in CAPABILITIES.items():
        if not (ROOT/record).is_file():
            raise ValueError("Missing curated source record: "+record)
        lines.append(f"| {name} | {description} | `{record}` |")
    lines += ["", "## Concrete setup omissions to prevent", "",
        "- `compressor-map` now also contains a deferred turbine-map pairing receipt. It requires a reviewed turbine-map source URI/hash/license and a project fixture builder returning a real pinned-LH2DT compressor trace plus the turbine map point; profile setup supplies LH2DT only and does not prove gas-turbine coupling.",
        "- `source-data-ingestion` now includes the synthetic cryogenic MOF parser/receipt contract. The acquired H2 attachments remain in ignored local storage; this case does not open or qualify those measurements.",
        "- `hydrogen-engine` includes a CoolProp HEOS real-fluid fuel-compression case alongside Cantera cases; install the thermo extra for the full profile. The real-fluid compression result is not converted to the Cantera cycle property basis.",
        "- `buried-pipeline-data` reads a caller-staged V2 CSV using core NumPy only; its offline fixture must bind the repository metadata receipt and local file path. The raw CSVs remain outside Git/package artifacts and this profile does not qualify their anonymous columns.",
        "- `hydrogen-channel-data` reads one caller-staged CC BY 4.0 V2 case ZIP using core NumPy only; its fixture must bind publisher metadata and the local archive. The reader preserves the two header rows and does not infer sensor clocks or physical meanings.",
        "- `source-data-ingestion` exercises synthetic XLSX parser and core-flood branch-adapter contracts, a mocked metadata-only TUdatalib DSpace API receipt and a synthetic HDF5 structure inventory; `openpyxl` and `h5py` are needed only when their respective reader cases execute. Acquired core-flood workbooks remain in ignored local/scratch storage and are not interpreted by the synthetic adapter contract.",
        "- `gas-composition` exercises the LH2DT inventory facade as well as CoolProp; a core/thermo-only environment is insufficient for its full current scope. Its generic adsorption-vessel composition fixture does not by itself imply PSA-Dyna installation.",
        "- `finite-adsorption-vessel` now includes native scheduled PSA cycle checks. The pure endpoint vessel API alone does not require PSA-Dyna, but this complete profile does.",
        "- `model-selection` includes joint QMC and actual finite facility/scenario dependencies. Install the uncertainty extra for SciPy>=1.15, not just the core lower bound SciPy>=1.14.",
        "- `fuel-cell-native` includes separated gas-volume paths whose original owner admits Cantera 3.2.x. The chemistry extra's broad upper range is not proof that a later native version is supported.",
        "- `fuel-cell` includes finite Water coolant EOS cases and therefore needs the thermo extra even when the original prescribed thermochemical fixtures use only core dependencies.",
        "- `facility-protection` includes a direct native Cantera composition-binding case and the finite-supply helper imports fluids friction; include chemistry and hydraulics alongside LH2DT/monitoring/risk.",
        "- `fracture-fatigue` includes the OEDI workbook reader which imports openpyxl at execution; the data extra is required for the complete profile.",
        "- `fracture-fatigue` also includes a source-bound MS1700/QP1180 MAT ingest case. Stage the exact 39,455-byte v1 attachment and provide an offline fixture builder that supplies its resolved Dataset receipt; SciPy is required. The reader preserves normalized coordinates only and makes no physical fit.",
        "- `fracture-fatigue` also includes an MS AHSS 1300 workbook ingest contract. Stage the exact 88,885-byte v1 workbook and provide an offline fixture builder that supplies its resolved Dataset receipt; openpyxl is required. The current-unit label is unresolved and no hydrogen flux or material fit is inferred.",
        "- Native jet fire/radiation fixtures create CoolProp source/ambient states even when HyRAM is already separately installed; declare thermo explicitly.",
        "- `flowing-heat-exchanger`, `finite-transfer` and thermal profiles require the reviewed LH2DT source even when a setup previously installed only CoolProp.",
        "- Preferred dispersion has an explicit SciPy compatibility recipe; do not merge incompatible native versions into all profiles or silently substitute providers.", "",
        "Current chemistry extra: `"+repr(project["project"]["optional-dependencies"]["chemistry"])+"`.",
        "Actual profile interpreters, native binary locations, data paths and setup-script SHA-256",
        "values remain campaign inputs. This report supplies no credentials or assumed queue/account.",
        "A missing source record fails generation; no network retrieval is attempted."]
    if unresolved:
        lines += ["", "Source modules needing dynamic profile reconciliation: "+", ".join(unresolved)]
    (ROOT/"docs/CLUSTER_PROFILE_REQUIREMENTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"{len(profiles)} curated profiles; {sum(map(len, declarations.values()))} source module associations")


if __name__ == "__main__":
    main()
