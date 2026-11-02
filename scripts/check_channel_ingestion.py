"""Load acquired flow and concentration records without assuming their clock alignment."""

import argparse
import csv
import io
from pathlib import Path
from zipfile import ZipFile

from h2physics.core import Origin
from h2physics.data.loaders import Column, load_csv_member

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--sensor-time-unit", choices=["s", "ms", "min"], default=None,
                    help="Explicit caller declaration; does not establish independent time-unit evidence")
args = parser.parse_args()
lines = ["# Open-channel ingestion checks", "",
         "Each experiment retains separate flow and sensor clock identities. Their relative",
         "alignment is not assumed. Flow uses the source's explicit seconds and g/s columns.",
         "The sensor clock has no unit in its header. Native concentration histories are withheld",
         "unless the caller explicitly declares a sensor-time unit; no default seconds assumption is used.",
         f"Caller sensor-time declaration for this run: {args.sensor_time_unit or 'none'}.",
         "Filling pressure is omitted because the column alone does not establish pressure basis.", "",
         "| Experiment | Flow records | Sensor records | Invalid sensor values | Omitted padding rows |",
         "|---|---:|---:|---:|---:|"]
case_count = 0
for archive in sorted((root / "data/raw/hydrogen-channel").glob("*/*.zip")):
    with ZipFile(archive) as data:
        member = next(name for name in data.namelist() if name.endswith(".csv"))
        with data.open(member) as binary:
            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as source:
                header = next(csv.reader(source))
    experiment = archive.stem
    flow_columns = [name for name in header if name.startswith("mass flow meter ") and name.endswith("[g/s]")]
    if len(flow_columns) != 1:
        raise ValueError(f"{experiment}: flow-meter selection is ambiguous")
    flow = load_csv_member(archive, member,
                          columns=(Column(flow_columns[0], "source_mass_flow", "mass_flow", "g/s"),),
                          time_column="flow time [s]", time_unit="s", clock_id=experiment + ":flow",
                          origin=Origin.MEASURED, source_id=experiment, omit_missing_time=True)
    if args.sensor_time_unit is None:
        lines.append(f"| {experiment} | {flow.series.time_s.size} | withheld: clock unit unresolved | — | "
                     f"{flow.report.omitted_missing_time_rows} flow rows |")
        case_count += 1
        continue
    sensors = load_csv_member(archive, member,
                             columns=tuple(Column(name, name.split(" h2 concentration")[0],
                                                  "volume_fraction", "%")
                                           for name in header if "h2 concentration [%]" in name),
                             time_column="h2 sensor time", time_unit=args.sensor_time_unit,
                             clock_id=experiment + ":sensors", origin=Origin.RECONSTRUCTED,
                             source_id=experiment, omit_missing_time=True)
    lines.append(f"| {experiment} | {flow.series.time_s.size} | {sensors.series.time_s.size} | "
                 f"{sensors.report.invalid_measurement_values} | "
                 f"{flow.report.omitted_missing_time_rows + sensors.report.omitted_missing_time_rows} |")
    case_count += 1
(root / "research/channel_ingestion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Loaded {case_count} experiments; inspect research/channel_ingestion.md for actual cases")
