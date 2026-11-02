"""Inventory container schemas. No bundled code or macros are executed."""

import json
import tomllib
from pathlib import Path

from h2physics.data.inspect import inspect_file


def string(value):
    return json.dumps(str(value), ensure_ascii=False)


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "research/schema"
    output.mkdir(parents=True, exist_ok=True)
    summary = ["# Acquired data schema audit", "",
               "Counts refer to files, tables or declared dimensions. They are not independent experiment counts.",
               "Pressure basis, clock alignment, geometry and measurement origin require separate review.", "",
               "| Dataset | Inspected files | Tables | Rows in delimited tables | Container errors |",
               "|---|---:|---:|---:|---:|"]
    for receipt in sorted((root / "research/data").glob("*.toml")):
        data = tomllib.loads(receipt.read_text(encoding="utf-8"))
        lines = [f"dataset = {string(data['key'])}", f"doi = {string(data['doi'])}",
                 f"license_id = {string(data['license_id'])}", "validation_qualified = false"]
        count = rows = tables = errors = 0
        for record in data.get("files", []):
            if record["status"] not in {"acquired", "cached"}:
                continue
            path = root / "data/raw" / record["relative_path"]
            lines += ["", "[[files]]", f"name = {string(record['name'])}"]
            try:
                profile = inspect_file(path)
                count += 1
                lines += [f"format = {string(profile.format)}", f"archive_members = {profile.archive_members}",
                          f"numeric_members = {profile.numeric_members}",
                          f"program_members_not_executed = {profile.program_members_not_executed}"]
                for table in profile.tables:
                    tables += 1
                    if table.format == "delimited" and table.rows:
                        rows += table.rows
                    lines += ["", "[[files.tables]]", f"name = {string(table.name)}",
                              f"format = {string(table.format)}", f"rows = {table.rows or 0}",
                              f"columns = {table.columns or 0}", f"counting_basis = {string(table.counting_basis)}",
                              "column_names = [" + ", ".join(string(x) for x in table.column_names) + "]"]
            except Exception as error:
                errors += 1
                lines += [f"error = {string(type(error).__name__ + ': ' + str(error))}"]
                print(data["key"], record["name"], "ERROR", error, flush=True)
        text = "\n".join(lines) + "\n"
        tomllib.loads(text)
        (output / (data["key"] + ".toml")).write_text(text, encoding="utf-8")
        summary.append(f"| {data['key']} | {count} | {tables} | {rows} | {errors} |")
        print(data["key"], "files", count, "tables", tables, "delimited_rows", rows, "errors", errors, flush=True)
    (root / "docs/DATA_SCHEMA_AUDIT.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
