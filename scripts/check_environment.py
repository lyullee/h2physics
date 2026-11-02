"""Report whether the local Python environment can use h2physics.

This is an installation diagnostic, not a scientific verification suite. It
does not execute model calculations or download optional dependencies.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    distribution: str
    import_name: str
    group: str


DEPENDENCIES = (
    Dependency("h2physics", "h2physics", "core"),
    Dependency("numpy", "numpy", "core"),
    Dependency("scipy", "scipy", "core"),
    Dependency("CoolProp", "CoolProp", "thermo"),
    Dependency("openpyxl", "openpyxl", "data"),
    Dependency("h5py", "h5py", "data"),
    Dependency("cantera", "cantera", "chemistry"),
    Dependency("fluids", "fluids", "hydraulics"),
    Dependency("pytest", "pytest", "test"),
)

PROFILES = {
    "core": {"core"},
    "research": {"core", "thermo", "data", "chemistry", "hydraulics", "test"},
}


def inspect_environment(profile: str, *, import_modules: bool = False) -> list[str]:
    required_groups = PROFILES[profile]
    missing: list[str] = []
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    if sys.version_info < (3, 12):
        missing.append("Python >=3.12")

    for dependency in DEPENDENCIES:
        try:
            version = importlib.metadata.version(dependency.distribution)
        except importlib.metadata.PackageNotFoundError:
            state = "distribution not installed"
            if dependency.group in required_groups:
                missing.append(dependency.distribution)
            marker = "required" if dependency.group in required_groups else "optional"
            print(f"[{marker:8}] {dependency.distribution}: {state}")
            continue

        try:
            spec = importlib.util.find_spec(dependency.import_name)
        except Exception as exc:
            spec = None
            import_error = exc.__class__.__name__
        else:
            import_error = "module not found"

        if spec is None:
            state = f"{version} installed; {import_error}"
            if dependency.group in required_groups:
                missing.append(dependency.distribution)
        else:
            location = spec.origin or "namespace package"
            if import_modules:
                try:
                    module = importlib.import_module(dependency.import_name)
                    location = getattr(module, "__file__", location)
                except Exception as exc:
                    state = f"{version} installed; import failed ({exc.__class__.__name__})"
                    if dependency.group in required_groups:
                        missing.append(dependency.distribution)
                else:
                    state = f"{version} - {location}"
            else:
                state = f"{version} - {location}"
        marker = "required" if dependency.group in required_groups else "optional"
        print(f"[{marker:8}] {dependency.distribution}: {state}")

    if missing:
        print("\nEnvironment is incomplete: " + ", ".join(missing))
    else:
        print(f"\nEnvironment is ready for the '{profile}' profile.")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="core")
    parser.add_argument(
        "--imports",
        action="store_true",
        help="also import each installed module to check runtime loadability",
    )
    args = parser.parse_args()
    missing = inspect_environment(args.profile, import_modules=args.imports)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
