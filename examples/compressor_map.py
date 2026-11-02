"""Unexecuted compressor-map construction; native stage is supplied elsewhere."""

from h2physics.adapters.compressor_map import (
    CompressorMapEvidence,
    CompressorMapLine,
    CompressorOperatingMap,
)

evidence = CompressorMapEvidence(
    "caller-map", "https://example.invalid/not-vendor-data", "caller-supplied",
    "0" * 64,
)
operating_map = CompressorOperatingMap(
    "example-map", 288.15, 101325.0,
    (
        CompressorMapLine(100.0, 0.01, 0.03, 1.2, 2.0, 0.55, 0.85),
        CompressorMapLine(200.0, 0.02, 0.06, 1.4, 3.0, 0.60, 0.88),
    ), evidence,
)

# Deferred: MappedCompressor(actual_native_stage, operating_map).evaluate(...)
