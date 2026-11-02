"""Audit non-time MOF isotherms and source-ambiguous SOFC polarization curves."""

import csv
from pathlib import Path

import numpy as np

from h2physics.core import Origin
from h2physics.data.loaders import Column, load_observation_table
from h2physics.data.polarization import load_polarization_grid


def main():
    root = Path(__file__).resolve().parents[1]
    lines = ["# Non-time observation ingestion", "",
        "MOF source: Jimenez Lopez et al., [dataset v1.1](https://doi.org/10.57745/FCV2R0), "
        "Etalab Open Licence 2.0; source updated 2026-08-25T11:13:19Z. "
        "Rows preserve adsorption/desorption direction and missing cells. Curves from one "
        "file keep the same group; no independent-trial count is inferred.", "",
        "At 20 K the pressure normalizer and STP gas state remain unresolved. At 77/87 K "
        "the headers call the bar-valued coordinate relative pressure, so it is retained "
        "as reported_pressure in Pa with unresolved semantics. Its conversion is only a "
        "unit scaling, not a declaration of absolute pressure. Uptake is kept in its "
        "source-defined basis; excess/absolute and mass-basis details need confirmation.", "",
        "| File / branch | Rows | Complete pairs | Missing cells | Pressure quantity | Uptake quantity |",
        "|---|---:|---:|---:|---|---|"]
    totals = {"mof_curves": 0, "mof_rows": 0, "sofc_curves": 0, "sofc_rows": 0}
    for path in sorted((root / "data/raw/cryo-mof-dormancy").rglob("H2*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream))
        if len(header) != 4:
            raise ValueError("Unreviewed isotherm header shape")
        cryogenic = path.name.startswith("H2.20K")
        for branch, offset in (("adsorption", 0), ("desorption", 2)):
            columns = (
                Column(header[offset], "pressure_coordinate", "normalized_pressure" if cryogenic else "reported_pressure",
                       "1" if cryogenic else "bar", basis_id="source-pressure-normalizer-or-basis-unresolved"),
                Column(header[offset+1], "uptake", "reference_specific_volume" if cryogenic else "specific_amount",
                       "cm3/g" if cryogenic else "mmol/g", basis_id=("STP-source-unspecified" if cryogenic
                       else "source-uptake-excess-and-mass-basis-unspecified")),
            )
            with path.open(encoding="utf-8-sig", newline="") as source:
                table = load_observation_table(source, columns=columns, experiment_id=path.stem,
                    source_id=f"10.57745/FCV2R0:{path.name}:{branch}", origins=(Origin.MEASURED,)*2,
                    context=(("branch", branch), ("pressure_basis_qualified", "false")))
            totals["mof_curves"] += 1
            totals["mof_rows"] += len(table.values)
            lines.append(f"| {path.name} / {branch} | {len(table.values)} | "
                         f"{np.count_nonzero(table.complete_rows('pressure_coordinate', 'uptake'))} | "
                         f"{np.count_nonzero(~table.valid)} | {columns[0].quantity} | {columns[1].quantity} |")
    lines += ["", "## SOFC polarization grid", "",
        "Source: [Mendeley collection v1](https://doi.org/10.17632/j8b9v4cb9d.1), CC BY 4.0. "
        "Explicit declarations are degrees Celsius, mA/cm² and V; header encodings/glyphs "
        "vary. Measurement versus model origin is unresolved, so voltage columns are "
        "marked unresolved. Temperature conditions are reconstructed from column headings. "
        "A successful load does not make these independent measured validation curves.", "",
        "| Source file | Curves | Records | Missing cells |", "|---|---:|---:|---:|"]
    for path in sorted((root / "data/raw/sofc-polarization").rglob("*.txt")):
        with path.open(encoding="cp1252", newline="") as source:
            tables = load_polarization_grid(source, source_id=f"10.17632/j8b9v4cb9d.1:{path.name}",
                group_prefix=path.stem, temperature_unit="degC", current_density_unit="mA/cm2", voltage_unit="V")
        count = sum(len(t.values) for t in tables)
        totals["sofc_curves"] += len(tables)
        totals["sofc_rows"] += count
        lines.append(f"| {path.name} | {len(tables)} | {count} | "
                     f"{sum(np.count_nonzero(~t.valid) for t in tables)} |")
    lines += ["", f"Totals: {totals}.", "",
        "No pressure/STP basis is inferred, no negative or super-unity ratio is clipped, "
        "and no row is assigned an artificial time coordinate. Native adsorption/thermal "
        "validation remains blocked by scientific input gaps rather than by the table API."]
    (root / "research/static_ingestion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(totals)


if __name__ == "__main__":
    main()
