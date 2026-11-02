"""Original reader for the numeric, single-line subset of STAR-style property files.

The interface follows the public schema at https://doi.org/10.5281/zenodo.21355851.
It does not import or reproduce the reader supplied with that dataset. Unsupported
multiline text, nested save frames and irregular tables fail explicitly.
"""

import shlex
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TextIO

import numpy as np
from numpy.typing import NDArray

from ..core import immutable_array


@dataclass(frozen=True, slots=True)
class PropertyLoop:
    tags: tuple[str, ...]
    values: NDArray[np.float64]

    def __post_init__(self):
        values = np.array(self.values, dtype=float, copy=True)
        if values.ndim != 2 or values.shape[1] != len(self.tags):
            raise ValueError("The numeric property table does not match its column tags")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("Duplicate property tags are ambiguous")
        values = immutable_array(values, name="property table")
        object.__setattr__(self, "values", values)

    def column(self, suffix: str):
        matches = [i for i, tag in enumerate(self.tags) if tag.endswith("_" + suffix)
                   and (suffix.startswith("uncertainty") or "_uncertainty_" not in tag)]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one property column for {suffix!r}")
        return self.values[:, matches[0]]


@dataclass(frozen=True, slots=True)
class PropertyFile:
    name: str
    metadata: Mapping[str, str]
    loops: tuple[PropertyLoop, ...]

    def __post_init__(self):
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def read_property_file(source: TextIO) -> PropertyFile:
    tokens = []
    for line in source:
        if line.startswith(";"):
            raise ValueError("Multiline STAR values are outside this reader's declared subset")
        tokens.extend(shlex.split(line, comments=True, posix=True))
    metadata, loops, name = {}, [], ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("data_"):
            if name:
                raise ValueError("Only one data block per property file is supported")
            name = token[5:]
            index += 1
        elif token == "loop_":
            index += 1
            tags = []
            while index < len(tokens) and tokens[index].startswith("_"):
                tags.append(tokens[index])
                index += 1
            if not tags:
                raise ValueError("A property loop needs column tags")
            values = []
            while index < len(tokens):
                item = tokens[index]
                if item.startswith(("_", "data_", "save_")) or item == "loop_":
                    break
                values.append(np.nan if item in {"?", "."} else float(item))
                index += 1
            if len(values) % len(tags):
                raise ValueError("A property loop has an incomplete numeric row")
            loops.append(PropertyLoop(tuple(tags), np.asarray(values).reshape(-1, len(tags))))
        elif token.startswith("_"):
            if token in metadata or index + 1 >= len(tokens):
                raise ValueError("Duplicate or incomplete metadata entry")
            metadata[token] = tokens[index + 1]
            index += 2
        else:
            raise ValueError(f"Unsupported property-file token: {token!r}")
    if not name or not loops:
        raise ValueError("A property file needs a named block and a numeric loop")
    return PropertyFile(name, metadata, tuple(loops))


def acoustic_columns(data: PropertyFile, loop: PropertyLoop):
    """Return T [K], p [Pa] and sound speed [m/s], retaining missing values."""
    units = {"temperature": "K", "pressure": "MPa", "SoS": "m/s"}
    for quantity, unit in units.items():
        if data.metadata.get("_units_" + quantity) != unit:
            raise ValueError(f"Unexpected or undeclared acoustic {quantity} unit")
    return loop.column("temperature"), loop.column("pressure") * 1e6, loop.column("SoS")
