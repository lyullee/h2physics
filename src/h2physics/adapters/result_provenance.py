"""Read-only fingerprints for retained producer results.

The helpers inspect already stored values.  They never call a physical model,
property function or native solver, and they do not turn a fingerprint into a
scientific validation claim.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass

import numpy as np


def recorded_content_token(value, seen=None):
    """Return an identity-aware token for retained result content only."""
    seen = set() if seen is None else seen
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, (float, np.floating)):
        return ("float", float(value).hex())
    if isinstance(value, np.integer):
        return int(value)
    if id(value) in seen:
        return ("reference", id(value))
    seen.add(id(value))
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            raise TypeError("Object arrays cannot establish a native numeric-result seal")
        return (
            "array",
            id(value),
            value.dtype.str,
            value.shape,
            value.flags.writeable,
            hashlib.sha256(value.tobytes(order="C")).hexdigest(),
        )
    if isinstance(value, Mapping):
        return (
            "mapping",
            id(value),
            tuple((str(k), recorded_content_token(v, seen)) for k, v in value.items()),
        )
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(recorded_content_token(v, seen) for v in value))
    if is_dataclass(value):
        return (
            type(value).__module__,
            type(value).__qualname__,
            id(value),
            tuple(
                (f.name, recorded_content_token(getattr(value, f.name), seen))
                for f in fields(value)
                if f.name != "_admission"
            ),
            recorded_content_token(type(value).__call__, seen) if callable(value) else None,
        )
    # Native tabular caches are retained without importing their provider.
    if all(hasattr(value, name) for name in ("to_numpy", "columns", "index", "dtypes")):
        array = np.asarray(value.to_numpy(copy=True))
        if array.dtype.hasobject:
            raise TypeError("Object-valued native tables cannot establish a numeric-result seal")
        return (
            "native-table",
            id(value),
            recorded_content_token(tuple(value.columns), seen),
            recorded_content_token(tuple(value.index), seen),
            tuple(str(v) for v in value.dtypes),
            array.dtype.str,
            array.shape,
            hashlib.sha256(array.tobytes(order="C")).hexdigest(),
        )
    if callable(value):
        function = getattr(value, "__func__", value)
        return (
            "callable",
            id(function),
            id(getattr(function, "__code__", None)),
            recorded_content_token(getattr(function, "__defaults__", None), seen),
            recorded_content_token(getattr(function, "__kwdefaults__", None), seen),
        )
    return (type(value).__module__, type(value).__qualname__, id(value))


def recorded_content_sha256(value):
    """Hash :func:`recorded_content_token` without executing model callbacks."""
    return hashlib.sha256(
        json.dumps(recorded_content_token(value), separators=(",", ":")).encode()
    ).hexdigest()
