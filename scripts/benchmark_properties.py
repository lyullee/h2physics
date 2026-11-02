"""Measure table accuracy and full-state call cost in the declared warm-gas envelope."""

from pathlib import Path

from h2physics.thermo import (
    CoolPropProperties,
    GasEnvelope,
    QualifiedGasTable,
    TableQualificationError,
)


def main():
    root = Path(__file__).resolve().parents[1]
    lines = ["# Thermodynamic table qualification", "",
             "Direct HEOS comparisons check interpolation error, not independent EOS accuracy.",
             "The envelope excludes phase change and the critical temperature region.",
             "Timings include complete state construction and the public table domain guards. "
             "The workload contains PT and interior PH/PS calls in approximately equal numbers.", "",
             "PT and interior PH/PS states are compared. Energy identity uses a separate gate.", "",
             "The explicit derive_from_h_p_rho policy computes internal energy from h − p/rho "
             "and records the change from the library value. It does not modify h, rho, s, "
             "cp, cv or acoustic derivatives, and does not establish complete differential "
             "thermodynamic consistency. The default remains library-provided internal energy.", "",
             "| Fluid | Backend | Energy policy | PT points | PH/PS points | Largest relative error | Speedup | Gate |",
             "|---|---|---|---:|---:|---:|---:|---|"]
    details = []
    for fluid in ("Hydrogen", "ParaHydrogen"):
        reference = CoolPropProperties(fluid)
        for backend in ("BICUBIC&HEOS", "TTSE&HEOS"):
            for policy in ("library", "derive_from_h_p_rho"):
                try:
                    table = QualifiedGasTable(reference, GasEnvelope(1e5, 90e6, 230, 400),
                                              backend=backend, validation_points=1000,
                                              internal_energy_policy=policy)
                    report = table.qualification
                except TableQualificationError as error:
                    report = error.report
                largest = max(value for _, value in report.maximum_relative_errors)
                lines.append(f"| {fluid} | {backend} | {policy} | {report.validation_point_count} | "
                             f"{report.inverse_validation_point_count} | {largest:.6g} | "
                             f"{report.measured_speedup:.3f} | "
                             f"{'PASS' if report.qualification_passed else 'FAIL'} |")
                details += ["", f"## {fluid} with {backend}, {policy}", ""]
                details += [f"- {name}: {value:.8g}" for name, value in report.maximum_relative_errors]
                details += [f"- Maximum h-u-p/rho residual: {report.maximum_enthalpy_identity_residual_j_kg:.8g} J/kg",
                            f"- Maximum scaled identity error: {report.maximum_relative_enthalpy_identity_error:.8g}",
                            f"- Identity error limit: {report.maximum_relative_identity_error_allowed:.8g}",
                            f"- Maximum internal-energy adjustment: {report.maximum_internal_energy_adjustment_j_kg:.8g} J/kg",
                            f"- Envelope: {report.envelope}", f"- Seed: {report.seed}", ""]
                print(fluid, backend, policy, "error", largest, "speedup", report.measured_speedup,
                      "gate", report.qualification_passed, flush=True)
    path = root / "research/property_tables.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines + details) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
