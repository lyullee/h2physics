"""Safe, versioned persistence for immutable isothermal EOS tables.

The artifact is one uncompressed NumPy ZIP container with a canonical TOML
manifest embedded as UTF-8 bytes. The single-file replace makes publication
atomic, while checksums bind every array and the reconstructed table identity.
No executable object deserialization is used.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .isothermal_eos_table import IsothermalEOSTable

if TYPE_CHECKING:
    from .isothermal_eos_table import IsothermalEOSTableQualification


_SCHEMA_VERSION = 1
_FORMAT = "h2physics-isothermal-eos-table"
_ARRAY_NAMES = (
    "density_axis_kg_m3",
    "temperature_axis_k",
    "pressure_pa",
    "isothermal_sound_speed_m_s",
)
_MAX_MANIFEST_BYTES = 65_536
_MAX_TABLE_NODES = 2_000_000
_DEFAULT_MAX_ARTIFACT_BYTES = 128 * 1024 * 1024


def _toml_string(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("TOML string values must be strings")
    escaped = (value.replace("\\", "\\\\").replace('"', '\\"')
               .replace("\b", "\\b").replace("\t", "\\t")
               .replace("\n", "\\n").replace("\f", "\\f")
               .replace("\r", "\\r"))
    if any(ord(character) < 0x20 for character in value
           if character not in "\b\t\n\f\r"):
        raise ValueError("TOML metadata strings cannot contain control characters")
    return f'"{escaped}"'


def _array_digest(array: np.ndarray) -> str:
    canonical = np.ascontiguousarray(array, dtype="<f8")
    digest = hashlib.sha256()
    digest.update(np.asarray(canonical.shape, dtype="<u8").tobytes())
    digest.update(canonical.tobytes(order="C"))
    return digest.hexdigest()


def _canonical_manifest(
    table: IsothermalEOSTable,
    qualification: IsothermalEOSTableQualification | None,
) -> bytes:
    entries = {
        "format": _toml_string(_FORMAT),
        "schema_version": str(_SCHEMA_VERSION if table.sound_speed_mode == "sampled" else 2),
        "source_eos_identity": _toml_string(table.source_eos_identity),
        "interpolation": _toml_string(table.interpolation),
        "no_extrapolation": "true",
        "shape_temperature_density": f"[{table.shape[0]}, {table.shape[1]}]",
        "table_sha256": _toml_string(table.table_sha256),
        "qualification_present": "true" if qualification is not None else "false",
    }
    if table.sound_speed_mode != "sampled":
        entries["sound_speed_mode"] = _toml_string(table.sound_speed_mode)
    for name in _ARRAY_NAMES:
        entries[f"{name}_sha256"] = _toml_string(_array_digest(getattr(table, name)))
    if qualification is not None:
        for field_name, field_value in _qualification_values(qualification).items():
            if isinstance(field_value, str):
                entries[field_name] = _toml_string(field_value)
            elif type(field_value) is int:
                entries[field_name] = str(field_value)
            elif type(field_value) is float:
                entries[field_name] = repr(field_value)
            else:
                raise TypeError(f"Unsupported historical qualification field {field_name}")
    text = "".join(f"{name} = {entries[name]}\n" for name in sorted(entries))
    encoded = text.encode("utf-8")
    if len(encoded) > _MAX_MANIFEST_BYTES:
        raise ValueError("EOS table metadata exceeds the bounded manifest size")
    return encoded


def save_isothermal_eos_table(
    table: IsothermalEOSTable,
    path: str | os.PathLike[str],
    *,
    qualification: IsothermalEOSTableQualification | None = None,
    maximum_artifact_bytes: int = _DEFAULT_MAX_ARTIFACT_BYTES,
) -> Path:
    """Write a table as a checksummed, atomic `.npz` artifact.

    The output is built in memory only after the table's node and output-byte
    budgets are checked, then fsynced and atomically replaced on the same
    filesystem. Existing files are replaced only after a complete artifact is
    available. No EOS calls are performed.
    """
    if type(table) is not IsothermalEOSTable:
        raise TypeError("Persist only an immutable IsothermalEOSTable")
    if type(maximum_artifact_bytes) is not int or maximum_artifact_bytes < 1024:
        raise ValueError("maximum_artifact_bytes must be an integer of at least 1024")
    node_count = table.shape[0] * table.shape[1]
    if node_count > _MAX_TABLE_NODES:
        raise ValueError("EOS table exceeds the artifact node limit")
    estimated = (table.density_axis_kg_m3.nbytes + table.temperature_axis_k.nbytes
                 + table.pressure_pa.nbytes + table.isothermal_sound_speed_m_s.nbytes
                 + _MAX_MANIFEST_BYTES + 4096)
    if estimated > maximum_artifact_bytes:
        raise ValueError("EOS table exceeds the requested artifact byte limit")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if qualification is not None:
        from .isothermal_eos_table import IsothermalEOSTableQualification

        if type(qualification) is not IsothermalEOSTableQualification:
            raise TypeError("qualification must be an IsothermalEOSTableQualification receipt")
        _require_matching_qualification(table, qualification)
    manifest = _canonical_manifest(table, qualification)
    buffer = io.BytesIO()
    np.savez(
        buffer,
        density_axis_kg_m3=np.asarray(table.density_axis_kg_m3, dtype="<f8"),
        temperature_axis_k=np.asarray(table.temperature_axis_k, dtype="<f8"),
        pressure_pa=np.asarray(table.pressure_pa, dtype="<f8"),
        isothermal_sound_speed_m_s=np.asarray(
            table.isothermal_sound_speed_m_s, dtype="<f8"),
        metadata_toml=np.frombuffer(manifest, dtype=np.uint8),
    )
    payload = buffer.getvalue()
    if len(payload) > maximum_artifact_bytes:
        raise ValueError("Serialized EOS table exceeds the requested artifact byte limit")
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{destination.name}.", suffix=".tmp",
            dir=destination.parent, delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
    return destination


def load_isothermal_eos_table(
    path: str | os.PathLike[str],
    *,
    expected_source_eos_identity: str | None = None,
    maximum_artifact_bytes: int = _DEFAULT_MAX_ARTIFACT_BYTES,
) -> tuple[IsothermalEOSTable, IsothermalEOSTableQualification | None]:
    """Load and authenticate a bounded table artifact without EOS regeneration.

    ZIP members, total size, compression mode, array names, shape, manifest
    schema, per-array hashes and final table digest are all checked before the
    resulting immutable table and optional historical qualification receipt
    are returned as a pair. A receipt is evidence of a previous comparison,
    not a fresh validation. The table API continues to reject queries outside
    its explicit rho-T/p-T envelope.
    """
    if type(maximum_artifact_bytes) is not int or maximum_artifact_bytes < 1024:
        raise ValueError("maximum_artifact_bytes must be an integer of at least 1024")
    source = Path(path)
    size = source.stat().st_size
    if size <= 0 or size > maximum_artifact_bytes:
        raise ValueError("EOS artifact is empty or exceeds the configured byte limit")
    expected_members = {f"{name}.npy" for name in _ARRAY_NAMES}
    expected_members.add("metadata_toml.npy")
    with zipfile.ZipFile(source, "r") as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)) or set(names) != expected_members:
            raise ValueError("EOS artifact contains duplicate, missing, or unrecognized members")
        if any(member.compress_type != zipfile.ZIP_STORED for member in members):
            raise ValueError("Compressed ZIP members are not accepted in EOS table artifacts")
        if sum(member.file_size for member in members) > maximum_artifact_bytes:
            raise ValueError("EOS artifact expands beyond the configured byte limit")
        if any(member.file_size > maximum_artifact_bytes for member in members):
            raise ValueError("An EOS artifact member exceeds the configured byte limit")
    arrays = {}
    with np.load(source, allow_pickle=False, max_header_size=10_000) as contents:
        if set(contents.files) != {name[:-4] for name in expected_members}:
            raise ValueError("EOS artifact array index differs from its ZIP inventory")
        for name in _ARRAY_NAMES:
            value = contents[name]
            if value.dtype.kind != "f" or value.dtype.itemsize != 8:
                raise ValueError(f"EOS artifact array {name} must contain float64 values")
            arrays[name] = np.asarray(value, dtype="<f8")
        metadata_bytes = contents["metadata_toml"]
        if (metadata_bytes.dtype != np.dtype("uint8") or metadata_bytes.ndim != 1
                or metadata_bytes.nbytes > _MAX_MANIFEST_BYTES):
            raise ValueError("EOS artifact TOML metadata exceeds its bounded encoding")
        manifest_bytes = metadata_bytes.tobytes()
    try:
        manifest_text = manifest_bytes.decode("utf-8")
        metadata = tomllib.loads(manifest_text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("EOS artifact metadata is not valid UTF-8 TOML") from error
    base_keys = {
        "format", "schema_version", "source_eos_identity", "interpolation",
        "no_extrapolation", "shape_temperature_density", "table_sha256",
        "qualification_present",
        *(f"{name}_sha256" for name in _ARRAY_NAMES),
    }
    if metadata.get("schema_version") == 2:
        base_keys.add("sound_speed_mode")
    qualification_keys = set(_qualification_key_names())
    qualification_present = metadata.get("qualification_present")
    if (type(qualification_present) is not bool
            or set(metadata) != base_keys | (qualification_keys if qualification_present else set())):
        raise ValueError("EOS artifact metadata schema has missing or unknown fields")
    if (metadata["format"] != _FORMAT or type(metadata["schema_version"]) is not int
            or metadata["schema_version"] not in (_SCHEMA_VERSION, 2)
            or metadata["no_extrapolation"] is not True):
        raise ValueError("EOS artifact format/version or envelope policy is unsupported")
    if _canonical_manifest_text(metadata) != manifest_text:
        raise ValueError("EOS artifact metadata is not in canonical serialization")
    if expected_source_eos_identity is not None:
        if (not isinstance(expected_source_eos_identity, str)
                or metadata["source_eos_identity"] != expected_source_eos_identity):
            raise ValueError("EOS artifact source identity does not match the requested EOS")
    shape = metadata["shape_temperature_density"]
    if (not isinstance(shape, list) or len(shape) != 2
            or any(type(item) is not int or item < 2 for item in shape)
            or shape[0] * shape[1] > _MAX_TABLE_NODES):
        raise ValueError("EOS artifact table shape is invalid or exceeds the node limit")
    if (arrays["pressure_pa"].shape != tuple(shape)
            or arrays["isothermal_sound_speed_m_s"].shape != tuple(shape)
            or arrays["density_axis_kg_m3"].shape != (shape[1],)
            or arrays["temperature_axis_k"].shape != (shape[0],)):
        raise ValueError("EOS artifact array shapes disagree with the manifest")
    for name, array in arrays.items():
        if _array_digest(array) != metadata[f"{name}_sha256"]:
            raise ValueError(f"EOS artifact checksum mismatch for {name}")
    table = IsothermalEOSTable(
        arrays["density_axis_kg_m3"], arrays["temperature_axis_k"],
        arrays["pressure_pa"], arrays["isothermal_sound_speed_m_s"],
        metadata["source_eos_identity"], metadata["interpolation"],
        metadata.get("sound_speed_mode", "sampled"),
    )
    if table.table_sha256 != metadata["table_sha256"]:
        raise ValueError("EOS artifact reconstructed table digest does not match its manifest")
    receipt = None
    if qualification_present:
        from .isothermal_eos_table import IsothermalEOSTableQualification

        receipt = IsothermalEOSTableQualification(
            source_eos_identity=metadata["qualification_source_eos_identity"],
            table_identity=metadata["qualification_table_identity"],
            table_sha256=metadata["qualification_table_sha256"],
            validation_point_count=metadata["qualification_validation_point_count"],
            seed=metadata["qualification_seed"],
            interpolation=metadata["qualification_interpolation"],
            maximum_relative_pressure_error=metadata["qualification_maximum_relative_pressure_error"],
            maximum_relative_density_error=metadata["qualification_maximum_relative_density_error"],
            maximum_relative_sound_speed_error=metadata["qualification_maximum_relative_sound_speed_error"],
            maximum_relative_error_allowed=metadata["qualification_maximum_relative_error_allowed"],
            reference_seconds_per_query=metadata["qualification_reference_seconds_per_query"],
            table_seconds_per_query=metadata["qualification_table_seconds_per_query"],
        )
        _require_matching_qualification(table, receipt)
    return table, receipt


def _qualification_key_names() -> tuple[str, ...]:
    return (
        "qualification_source_eos_identity", "qualification_table_identity",
        "qualification_table_sha256", "qualification_validation_point_count",
        "qualification_seed", "qualification_interpolation",
        "qualification_maximum_relative_pressure_error",
        "qualification_maximum_relative_density_error",
        "qualification_maximum_relative_sound_speed_error",
        "qualification_maximum_relative_error_allowed",
        "qualification_reference_seconds_per_query",
        "qualification_table_seconds_per_query",
    )


def _qualification_values(qualification: IsothermalEOSTableQualification) -> dict:
    return {
        "qualification_source_eos_identity": qualification.source_eos_identity,
        "qualification_table_identity": qualification.table_identity,
        "qualification_table_sha256": qualification.table_sha256,
        "qualification_validation_point_count": qualification.validation_point_count,
        "qualification_seed": qualification.seed,
        "qualification_interpolation": qualification.interpolation,
        "qualification_maximum_relative_pressure_error": qualification.maximum_relative_pressure_error,
        "qualification_maximum_relative_density_error": qualification.maximum_relative_density_error,
        "qualification_maximum_relative_sound_speed_error": qualification.maximum_relative_sound_speed_error,
        "qualification_maximum_relative_error_allowed": qualification.maximum_relative_error_allowed,
        "qualification_reference_seconds_per_query": qualification.reference_seconds_per_query,
        "qualification_table_seconds_per_query": qualification.table_seconds_per_query,
    }


def _require_matching_qualification(
    table: IsothermalEOSTable,
    qualification: IsothermalEOSTableQualification,
) -> None:
    if (qualification.source_eos_identity != table.source_eos_identity
            or qualification.table_identity != table.identity
            or qualification.table_sha256 != table.table_sha256
            or qualification.interpolation != table.interpolation):
        raise ValueError("Historical qualification receipt does not match this EOS table")


def _canonical_manifest_text(metadata: dict) -> str:
    entries = {
        "format": _toml_string(metadata["format"]),
        "schema_version": str(metadata["schema_version"]),
        "source_eos_identity": _toml_string(metadata["source_eos_identity"]),
        "interpolation": _toml_string(metadata["interpolation"]),
        "no_extrapolation": "true" if metadata["no_extrapolation"] else "false",
        "shape_temperature_density": (
            f"[{metadata['shape_temperature_density'][0]}, "
            f"{metadata['shape_temperature_density'][1]}]"),
        "table_sha256": _toml_string(metadata["table_sha256"]),
        "qualification_present": "true" if metadata["qualification_present"] else "false",
    }
    if "sound_speed_mode" in metadata:
        entries["sound_speed_mode"] = _toml_string(metadata["sound_speed_mode"])
    for name in _ARRAY_NAMES:
        entries[f"{name}_sha256"] = _toml_string(metadata[f"{name}_sha256"])
    if metadata["qualification_present"]:
        for name in _qualification_key_names():
            value = metadata[name]
            entries[name] = (_toml_string(value) if isinstance(value, str)
                             else repr(value) if isinstance(value, float)
                             else str(value))
    return "".join(f"{name} = {entries[name]}\n" for name in sorted(entries))


__all__ = ["save_isothermal_eos_table", "load_isothermal_eos_table"]
