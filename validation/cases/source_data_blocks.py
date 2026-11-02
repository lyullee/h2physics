"""Deferred source-block receipt checks using tiny synthetic XLSX containers."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(identifier="fermentation-block-issuer-integrity", profile="source-data-ingestion",
            entrypoint=__name__+":validate_fermentation", invariants=(
                "synthetic qualified workbook issues one reactor block",
                "direct construction and dataclass replacement cannot forge lineage",
                "post-issuance metadata mutation is detected")),
        ValidationCase(identifier="hydride-tank-block-issuer-integrity", profile="source-data-ingestion",
            entrypoint=__name__+":validate_hydride_tank", invariants=(
                "synthetic qualified workbook issues a row-preserving block",
                "direct construction and dataclass replacement cannot forge lineage",
                "post-issuance raw-cell mutation is detected")),
        ValidationCase(identifier="tudatalib-engine-metadata-receipt", profile="source-data-ingestion",
            entrypoint="validation.cases.tudatalib_repository:validate_metadata_contract", invariants=(
                "exact item, ORIGINAL bundle and bitstream-list bytes are retained",
                "item identity, DOI, CC-BY-4.0, sizes and MD5 declarations are parsed",
                "only official-host credential-free HTTPS links are accepted",
                "pinned DOI mismatch and unresolved license are rejected",
                "multiple ORIGINAL bundles and unsafe links are rejected",
                "provider lookup requests metadata only and never attachment content")),
        ValidationCase(identifier="hdf5-structure-inventory", profile="source-data-ingestion",
            entrypoint=__name__+":validate_hdf5_inventory", invariants=(
                "synthetic HDF5 groups, dataset shapes, dtypes, chunks, compression and attributes are retained",
                "soft and external links are listed without dereferencing targets",
                "inventory objects are reader-issued and bind their exact immutable metadata content",
                "source byte identity is retained and declared inventory limits are enforced",
                "an existing inventory rejects post-return source-byte changes and recovers after restoration",
                "array values are not interpreted as measurements or assigned units")),
    )


def _column_name(index):
    result = ""
    while index:
        index, remainder = divmod(index-1, 26)
        result = chr(65+remainder)+result
    return result


def _write_xlsx(path, sheet_name, headers, rows):
    """Create a minimal XLSX with inline strings; stdlib only, no source data."""
    from xml.sax.saxutils import escape
    from zipfile import ZipFile, ZIP_DEFLATED

    sheet_rows = []
    for row_number, row in enumerate((headers, *rows), start=1):
        cells = []
        for column, value in enumerate(row, start=1):
            reference = f"{_column_name(column)}{row_number}"
            if isinstance(value, str):
                cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
            elif value is not None:
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
        sheet_rows.append(f'<row r="{row_number}">'+"".join(cells)+"</row>")
    last_column = _column_name(max(map(len, (headers, *rows))))
    sheet_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_column}{len(rows)+1}"/>'
        '<sheetData>'+"".join(sheet_rows)+'</sheetData></worksheet>')
    workbook_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>')
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _require_rejected(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("Forged or changed source block was accepted")


def validate_fermentation(*, work_directory):
    from dataclasses import replace
    from pathlib import Path

    from h2physics.data.fermentation import FermentationBlock, FermentationWorkbook

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    headers = ("Nr.", "R", "Duration (d)", "Temperature (°C)", "pH", "HRT (d)", "BP (L/d)",
        "CO2 (vol%)", "CH4 (vol%)", "H2 (vol%)", "HP (L/d)", "HY (L/g)", "HPR (L/(L/d))",
        "MP (L/d)", "MPR (L/(L/d))", "OLR (COD) (g/L/d)", "COD in (g/L)", "COD out  (g/L)",
        "Hac (g/L)", "HPr_1 (g/L)", "Hbu (g/L)", "Hva (g/L)", "Hca (g/L)", "tVFA (g/L)")
    values = (1, 1, 1, 35, 7, 10, 100, .1, .2, .7, 70, 1, 1, 20, 1, 1, 5, 2, 1, 1, 1, 1, 1, 5)
    source_path = destination/"fermentation-synthetic.xlsx"
    _write_xlsx(source_path, "Data", headers, (values,))
    from h2physics.data.pressure_peaking import file_sha256
    with FermentationWorkbook(source_path, source_id="synthetic-fermentation", study_id="synthetic-study",
                              expected_sha256=file_sha256(source_path)) as workbook:
        block = next(workbook.iter_blocks())
        assert block.source_rows == (2,) and block.reactor_id == "R-1"
        block.require_current()
    _require_rejected(lambda: FermentationBlock(block.observations, block.source_rows,
        block.raw_cells, block.formula_cells, block.invalid_reasons, block.reactor_id, block.issues))
    _require_rejected(lambda: replace(block, reactor_id="R-forged"))
    object.__setattr__(block, "raw_cells", (("mutated",),))
    _require_rejected(block.require_current)
    return ValidationOutcome(True, {"synthetic_rows": 1, "forgery_paths_rejected": 3},
        ("Synthetic reader provenance only; no biological process validation",))


def validate_hydride_tank(*, work_directory):
    from dataclasses import replace
    from datetime import datetime
    from pathlib import Path

    from h2physics.data.hydride_tank import HEADERS, HydrideTankBlock, iter_hydride_tank_blocks

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    values = (1, "2026-01-01", 0, 1, 101325, 25, 25, 25, 25, 25, 1, 1)
    source_path = destination/"hydride-tank-synthetic.xlsx"
    _write_xlsx(source_path, "Synthetic", HEADERS, (values,))
    block = next(iter_hydride_tank_blocks(source_path, "Synthetic", source_id="synthetic-hydride",
        experiment_id="synthetic-run", clock_id="synthetic-run/local",
        datetime_origin=datetime(2026, 1, 1), block_rows=1))
    assert block.source_rows == (2,) and len(block.raw_cells) == 1
    block.require_current()
    _require_rejected(lambda: HydrideTankBlock(block.observations, block.source_rows, block.raw_cells))
    _require_rejected(lambda: replace(block, source_rows=(3,)))
    object.__setattr__(block, "raw_cells", (("tampered",),))
    _require_rejected(block.require_current)
    return ValidationOutcome(True, {"synthetic_rows": 1, "forgery_paths_rejected": 3},
        ("Synthetic reader provenance only; no tank or hydride kinetics validation",))


def validate_hdf5_inventory(*, work_directory):
    """Use a tiny synthetic file to describe the metadata-only HDF5 boundary."""
    from pathlib import Path

    import h5py
    import numpy as np

    from h2physics.data.hdf5_inventory import inspect_hdf5_metadata
    from h2physics.data.hdf5_inventory import HDF5MetadataInventory

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "synthetic-structure.h5"
    with h5py.File(path, "w") as handle:
        group = handle.create_group("measurements")
        group.attrs["description"] = "synthetic array; unit intentionally undeclared"
        group.create_dataset("signal", data=np.arange(6, dtype="f4").reshape(2, 3),
                             chunks=(1, 3), compression="gzip")
        handle["signal-alias"] = h5py.SoftLink("/measurements/signal")
        handle["external-placeholder"] = h5py.ExternalLink("absent.h5", "/external/data")
    inventory = inspect_hdf5_metadata(path)
    assert inventory.require_current() is inventory
    try:
        HDF5MetadataInventory(
            inventory.source_path, inventory.source_sha256,
            inventory.source_size_bytes, inventory.hdf5_library_version,
            inventory.objects,
        )
    except ValueError:
        direct_inventory_rejected = True
    else:
        raise AssertionError("Direct HDF5 inventory construction acquired reader issuance")
    from dataclasses import replace
    try:
        replace(inventory)
    except ValueError:
        forged_inventory_rejected = True
    else:
        raise AssertionError("A cloned HDF5 metadata inventory retained reader issuance")
    original_library_version = inventory.hdf5_library_version
    object.__setattr__(inventory, "hdf5_library_version", "changed-after-inspection")
    try:
        inventory.require_current()
    except RuntimeError:
        mutated_inventory_rejected = True
    else:
        raise AssertionError("A changed HDF5 metadata inventory remained current")
    finally:
        object.__setattr__(inventory, "hdf5_library_version", original_library_version)
    assert inventory.require_current() is inventory
    records = {record.path: record for record in inventory.objects}
    signal = records["/measurements/signal"]
    assert signal.shape == (2, 3) and signal.dtype == "float32"
    assert signal.chunks == (1, 3) and signal.compression == "gzip"
    assert records["/measurements"].attributes == (
        ("description", "str", "synthetic array; unit intentionally undeclared"),)
    assert records["/signal-alias"].kind == "soft_link"
    assert records["/external-placeholder"].kind == "external_link"
    assert inventory.source_size_bytes == path.stat().st_size
    assert len(inventory.source_sha256) == 64
    try:
        inspect_hdf5_metadata(path, maximum_objects=1)
    except ValueError:
        pass
    else:
        raise AssertionError("Declared HDF5 object limits must be enforced")
    try:
        inspect_hdf5_metadata(path, maximum_attribute_bytes=1)
    except ValueError:
        pass
    else:
        raise AssertionError("Declared HDF5 attribute-byte limits must be enforced")
    from hashlib import sha256
    assert inventory.source_sha256 == sha256(path.read_bytes()).hexdigest()
    original_bytes = path.read_bytes()
    path.write_bytes(original_bytes + b"changed-after-inventory")
    try:
        inventory.require_current()
    except RuntimeError:
        stale_file_rejected = True
    else:
        raise AssertionError("An inventory remained current after its source bytes changed")
    finally:
        path.write_bytes(original_bytes)
    assert inventory.require_current() is inventory
    return ValidationOutcome(True, {
        "synthetic_object_records": len(inventory.objects),
        "dataset_rank": len(signal.shape),
        "source_sha256": inventory.source_sha256,
        "declared_limits_rejected": 2,
        "direct_inventory_rejected": direct_inventory_rejected,
        "forged_inventory_rejected": forged_inventory_rejected,
        "mutated_inventory_rejected": mutated_inventory_rejected,
        "post_inventory_source_change_rejected": stale_file_rejected,
    }, ("HDF5 structure metadata only; no measurement values or units inferred",))
