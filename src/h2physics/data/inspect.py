"""Inspect data containers without running included third-party programs."""

import csv
import io
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True, slots=True)
class TableProfile:
    name: str
    format: str
    rows: int | None
    columns: int | None
    column_names: tuple[str, ...] = ()
    counting_basis: str = ""


@dataclass(frozen=True, slots=True)
class FileProfile:
    name: str
    format: str
    tables: tuple[TableProfile, ...]
    archive_members: int = 0
    numeric_members: int = 0
    program_members_not_executed: int = 0


def _csv_profile(name: str, stream) -> TableProfile:
    first = stream.read(32_768)
    stream.seek(0)
    try:
        dialect = csv.Sniffer().sniff(first, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(stream, dialect)
    header = next(reader, [])
    rows = sum(bool(row) for row in reader)
    return TableProfile(name, "delimited", rows, len(header), tuple(header),
                        "nonempty records after the first row; header meaning requires review")


def _xlsx_profile(name: str, stream) -> tuple[TableProfile, ...]:
    from openpyxl import load_workbook

    workbook = load_workbook(stream, read_only=True, data_only=True)
    result = []
    try:
        for sheet in workbook.worksheets:
            first = next(sheet.iter_rows(values_only=True), ())
            result.append(TableProfile(name + ":" + sheet.title, "xlsx", sheet.max_row,
                                       sheet.max_column, tuple(str(x) if x is not None else "" for x in first),
                                       "declared worksheet dimensions, including formatted/empty cells"))
    finally:
        workbook.close()
    return tuple(result)


def inspect_file(path: Path, *, maximum_uncompressed_bytes: int = 2_000_000_000,
                 maximum_member_bytes: int = 250_000_000) -> FileProfile:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
            table = _csv_profile(path.name, source)
        return FileProfile(path.name, "delimited", (table,))
    if suffix == ".xlsx":
        return FileProfile(path.name, "xlsx", _xlsx_profile(path.name, path))
    if suffix == ".mat":
        from scipy.io import whosmat

        try:
            contents = whosmat(path)
            tables = tuple(TableProfile(name, "mat", shape[0] if shape else None,
                                        shape[1] if len(shape) > 1 else None, (), str(shape))
                           for name, shape, _ in contents)
        except NotImplementedError:
            import h5py

            with h5py.File(path, "r") as data:
                tables = tuple(TableProfile(name, "mat-hdf5", None, None, (),
                                            "HDF5 object; inspect schema before interpretation") for name in data)
        return FileProfile(path.name, "mat", tables)
    if suffix == ".zip":
        tables, numeric, programs = [], 0, 0
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if sum(x.file_size for x in members) > maximum_uncompressed_bytes:
                raise ValueError("Archive exceeds the declared uncompressed size limit")
            for item in members:
                member = PurePosixPath(item.filename.replace("\\", "/"))
                if member.is_absolute() or ".." in member.parts:
                    raise ValueError("Archive contains an unsafe path")
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError("Archive contains symbolic-link content")
                ext = member.suffix.lower()
                programs += ext in {".py", ".m", ".exe", ".bat", ".ps1", ".ipynb"}
                numeric += ext in {".csv", ".tsv", ".xlsx", ".mat", ".h5", ".hdf5", ".pif"}
                if item.file_size > maximum_member_bytes or item.is_dir() or "__MACOSX" in member.parts:
                    continue
                if ext in {".csv", ".tsv"}:
                    with archive.open(item) as binary:
                        with io.TextIOWrapper(binary, encoding="utf-8-sig", errors="replace", newline="") as source:
                            tables.append(_csv_profile(item.filename, source))
                elif ext == ".xlsx" and item.file_size <= 50_000_000:
                    with archive.open(item) as binary:
                        tables.extend(_xlsx_profile(item.filename, io.BytesIO(binary.read())))
        return FileProfile(path.name, "zip", tuple(tables), len(members), numeric, programs)
    return FileProfile(path.name, suffix.lstrip(".") or "unknown", ())
