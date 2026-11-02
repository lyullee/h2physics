"""Bounded, hash-verified decoding for reviewed MATLAB v5 recorder exports."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path


def decode_recorded_mat(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_file_bytes: int,
    maximum_file_bytes: int,
    maximum_array_bytes: int,
    numeric_columns: dict[str, int],
    metadata_names: tuple[str, ...],
):
    """Decode only named numeric matrices and small cell metadata arrays."""
    from scipy.io import loadmat, whosmat

    supplied = Path(path)
    if supplied.is_symlink() or not supplied.is_absolute():
        raise ValueError("MAT path must be absolute and cannot be a symbolic link")
    source = supplied.resolve()
    if (not source.is_file() or source.stat().st_size != expected_file_bytes
            or source.stat().st_size > maximum_file_bytes):
        raise ValueError("MAT file byte size differs from the reviewed file budget")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256:
        raise ValueError("MAT SHA-256 differs from the recorded source receipt")
    shapes = {name: (shape, kind) for name, shape, kind in whosmat(source)}
    required = set(numeric_columns) | set(metadata_names)
    missing = sorted(required - set(shapes))
    unreviewed = sorted(set(shapes) - required)
    if missing or unreviewed:
        raise ValueError(
            "MAT variable inventory differs from the reviewed recorder profile; "
            f"missing={missing}, unreviewed={unreviewed}"
        )
    decoded_bytes = 0
    for name, columns in numeric_columns.items():
        shape, kind = shapes[name]
        if len(shape) != 2 or shape[1] != columns or kind != "double":
            raise ValueError(f"MAT numeric matrix {name} has an unreviewed shape or type")
        decoded_bytes += math.prod(shape) * 8
    for name in metadata_names:
        shape, kind = shapes[name]
        if kind != "cell" or math.prod(shape) > 100:
            raise ValueError(f"MAT metadata array {name} has an unreviewed shape or type")
    if decoded_bytes > maximum_array_bytes:
        raise ValueError("Decoded MAT arrays exceed the declared memory budget")
    data = loadmat(source, variable_names=sorted(required), verify_compressed_data_integrity=True)
    verify = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            verify.update(chunk)
    if verify.hexdigest() != expected_sha256:
        raise ValueError("MAT file changed while decoding its numeric data")
    return source, data, shapes


__all__ = ["decode_recorded_mat"]
