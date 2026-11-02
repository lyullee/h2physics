"""Schema-neutral HDF5 structure inspection; dataset values are never loaded."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path


_PENDING_INVENTORY_ISSUERS: set[object] = set()


def _inventory_signature(source_path, source_sha256, source_size_bytes,
                         hdf5_library_version, objects):
    payload = (source_path, source_sha256, source_size_bytes,
               hdf5_library_version, objects)
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HDF5ObjectMetadata:
    """One group, dataset, or link record from an HDF5 container."""

    path: str
    kind: str
    shape: tuple[int, ...] | None = ()
    dtype: str = ""
    chunks: tuple[int, ...] | None = None
    compression: str | None = None
    link_target: str = ""
    attributes: tuple[tuple[str, str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class HDF5MetadataInventory:
    """Content-pinned structure and attributes, without interpreting units."""

    source_path: str
    source_sha256: str
    source_size_bytes: int
    hdf5_library_version: str
    objects: tuple[HDF5ObjectMetadata, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_INVENTORY_ISSUERS:
            raise ValueError("HDF5 inventories are issued only by inspect_hdf5_metadata()")
        _PENDING_INVENTORY_ISSUERS.remove(self._issuer_token)
        if (not isinstance(self.source_path, str) or not self.source_path
                or not isinstance(self.source_sha256, str)
                or len(self.source_sha256) != 64
                or any(char not in "0123456789abcdef" for char in self.source_sha256)):
            raise ValueError("Retain an absolute source path and lowercase SHA-256 identity")
        if (type(self.source_size_bytes) is not int or self.source_size_bytes < 0
                or not isinstance(self.hdf5_library_version, str)
                or not self.hdf5_library_version.strip()):
            raise ValueError("Retain valid source size and HDF5 library version metadata")
        objects = tuple(self.objects)
        if any(type(item) is not HDF5ObjectMetadata for item in objects):
            raise TypeError("Inventory objects must be actual HDF5 metadata records")
        object.__setattr__(self, "objects", objects)
        object.__setattr__(self, "_seal", self._current_signature())

    def _current_signature(self):
        return _inventory_signature(
            self.source_path, self.source_sha256, self.source_size_bytes,
            self.hdf5_library_version, tuple(self.objects),
        )

    def require_current(self):
        """Reject use after the inspected source path no longer matches its digest.

        This checks byte identity only. It does not reread HDF5 metadata, assign
        semantics, or establish publisher authenticity or redistribution rights.
        """
        if not self._seal or self._current_signature() != self._seal:
            raise RuntimeError("HDF5 metadata inventory changed after inspection")
        source = Path(self.source_path)
        if source.is_symlink() or not source.is_file():
            raise RuntimeError("Inspected HDF5 source is no longer a regular non-symlink file")
        stat = source.stat()
        if (stat.st_size != self.source_size_bytes
                or _sha256(source) != self.source_sha256):
            raise RuntimeError("Inspected HDF5 source changed after metadata inventory")
        return self


def _freeze_attribute(value, *, maximum_items: int):
    """Convert an attribute into bounded immutable Python values with type tags."""
    import numpy as np

    if isinstance(value, np.ndarray):
        if value.size > maximum_items:
            raise ValueError("HDF5 attribute array exceeds the declared item limit")
        return tuple(_freeze_attribute(item, maximum_items=maximum_items)
                     for item in value.tolist())
    if isinstance(value, np.generic):
        return _freeze_attribute(value.item(), maximum_items=maximum_items)
    if isinstance(value, (list, tuple)):
        if len(value) > maximum_items:
            raise ValueError("HDF5 attribute sequence exceeds the declared item limit")
        return tuple(_freeze_attribute(item, maximum_items=maximum_items) for item in value)
    if isinstance(value, (str, bytes, bool, int, float, complex)) or value is None:
        return value
    raise TypeError(f"Unsupported HDF5 attribute value type: {type(value).__name__}")


def _attribute_size(value) -> int:
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, tuple):
        return sum(_attribute_size(item) for item in value)
    if isinstance(value, complex):
        return 16
    if isinstance(value, float):
        return 8
    if isinstance(value, int):
        return max(1, (value.bit_length() + 7) // 8)
    return 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_hdf5_metadata(path: str | Path, *, maximum_file_bytes: int = 1_000_000_000,
                          maximum_objects: int = 100_000,
                          maximum_attribute_items: int = 100_000,
                          maximum_attributes: int = 100_000,
                          maximum_attribute_bytes: int = 16_000_000) -> HDF5MetadataInventory:
    """Inventory HDF5 groups, datasets, links and attributes without reading arrays.

    This operation deliberately assigns no units, physical quantities, coordinates,
    or observation meaning. External and soft links are recorded but never followed.
    The optional ``data`` dependencies provide h5py and NumPy.
    """
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValueError("HDF5 source must be a regular non-symlink file")
    for value, name in ((maximum_file_bytes, "maximum_file_bytes"),
                        (maximum_objects, "maximum_objects"),
                        (maximum_attribute_items, "maximum_attribute_items"),
                        (maximum_attributes, "maximum_attributes"),
                        (maximum_attribute_bytes, "maximum_attribute_bytes")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    stat_before = source.stat()
    if stat_before.st_size > maximum_file_bytes:
        raise ValueError("HDF5 source exceeds the declared file-size limit")
    digest = _sha256(source)
    try:
        import h5py
        import numpy as np  # noqa: F401 - verifies the attribute conversion runtime
    except ImportError as error:
        raise RuntimeError("HDF5 inspection requires the optional 'data' dependencies") from error

    records: list[HDF5ObjectMetadata] = []
    visited_groups: set[int] = set()
    attribute_count = 0
    attribute_bytes = 0

    def attributes_for(node):
        nonlocal attribute_count, attribute_bytes
        retained = []
        for name in sorted(node.attrs):
            attribute_count += 1
            if attribute_count > maximum_attributes:
                raise ValueError("HDF5 attribute count exceeds the declared inventory limit")
            attribute_id = node.attrs.get_id(name)
            if attribute_id.get_storage_size() > maximum_attribute_bytes:
                raise ValueError("HDF5 attribute exceeds the declared byte limit")
            value = node.attrs[name]
            frozen = _freeze_attribute(value, maximum_items=maximum_attribute_items)
            attribute_bytes += _attribute_size(frozen)
            if attribute_bytes > maximum_attribute_bytes:
                raise ValueError("HDF5 attributes exceed the declared aggregate byte limit")
            retained.append((str(name), type(value).__name__, frozen))
        return tuple(retained)

    def walk(group, prefix: str):
        address = int(h5py.h5o.get_info(group.id).addr)
        if address in visited_groups:
            return
        visited_groups.add(address)
        for name in sorted(group.keys()):
            object_path = f"{prefix}/{name}" if prefix else f"/{name}"
            link = group.get(name, getlink=True)
            if isinstance(link, h5py.SoftLink):
                record = HDF5ObjectMetadata(object_path, "soft_link", link_target=link.path)
            elif isinstance(link, h5py.ExternalLink):
                record = HDF5ObjectMetadata(
                    object_path, "external_link", link_target=f"{link.filename}:{link.path}")
            else:
                node = group[name]
                attrs = attributes_for(node)
                if isinstance(node, h5py.Group):
                    record = HDF5ObjectMetadata(object_path, "group", attributes=attrs)
                elif isinstance(node, h5py.Dataset):
                    record = HDF5ObjectMetadata(
                        object_path, "dataset",
                        tuple(int(n) for n in node.shape) if node.shape is not None else None,
                        str(node.dtype),
                        tuple(int(n) for n in node.chunks) if node.chunks is not None else None,
                        str(node.compression) if node.compression is not None else None,
                        attributes=attrs,
                    )
                else:
                    raise TypeError(f"Unsupported HDF5 object at {object_path}")
                records.append(record)
                if isinstance(node, h5py.Group):
                    walk(node, object_path)
            if isinstance(link, (h5py.SoftLink, h5py.ExternalLink)):
                records.append(record)
            if len(records) > maximum_objects:
                raise ValueError("HDF5 object count exceeds the declared inventory limit")

    with h5py.File(source, "r") as container:
        records.append(HDF5ObjectMetadata("/", "group", attributes=attributes_for(container)))
        walk(container, "")
        if len(records) > maximum_objects:
            raise ValueError("HDF5 object count exceeds the declared inventory limit")
        library_version = str(h5py.version.hdf5_version)
    stat_after = source.stat()
    if ((stat_before.st_size, stat_before.st_mtime_ns)
            != (stat_after.st_size, stat_after.st_mtime_ns)
            or _sha256(source) != digest):
        raise RuntimeError("HDF5 source changed while its metadata inventory was read")
    token = object()
    _PENDING_INVENTORY_ISSUERS.add(token)
    try:
        inventory = HDF5MetadataInventory(
            os.path.abspath(source), digest, stat_after.st_size,
            library_version, tuple(records), token,
        )
    except Exception:
        _PENDING_INVENTORY_ISSUERS.discard(token)
        raise
    return inventory.require_current()


__all__ = ["HDF5MetadataInventory", "HDF5ObjectMetadata", "inspect_hdf5_metadata"]
