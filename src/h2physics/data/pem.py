"""Streaming source profile for the licensed PEMWE catalyst time-series archive.

Canonical numeric channels retain their raw masks and physical source rows.
Protocol labels remain separate from frequency sweeps and independent cells.
"""

import csv
import hashlib
import io
from collections.abc import Collection
from dataclasses import dataclass
from typing import BinaryIO

import numpy as np

from ..core import Origin, finite
from ..impedance import ImpedanceSpectrum
from ..observations import ObservationTable, Variable

# Actual archived headers differ from the metadata's compact column labels.
HEADERS = ("elapsed time in s", "Temp in degC", "I in mA", "E in V", "freq in Hz",
           "Z_magnitude in Ohm", "Z_phase in deg", "conductivity in uS/cm", "pressure in bar abs",
           "H2_uncorrected in vol.%", "H2_corrected in vol.%", "measurement_type", "measurement_type_counter")
VARIABLES = (
    Variable("time_s", "elapsed_time", "s"), Variable("block_temperature_k", "temperature", "K"),
    Variable("current_a", "electric_current", "A"), Variable("voltage_v", "electric_potential", "V"),
    Variable("frequency_hz", "frequency", "Hz"), Variable("magnitude_ohm", "impedance_magnitude", "ohm"),
    Variable("phase_deg", "impedance_phase", "deg"), Variable("conductivity_s_m", "conductivity", "S/m"),
    Variable("cathode_pressure_pa", "absolute_pressure", "Pa"),
    Variable("hydrogen_fraction_uncorrected", "reported_gas_volume_fraction", "1", "uncorrected-GC"),
    Variable("hydrogen_fraction_corrected", "reported_gas_volume_fraction", "1", "author-dilution-corrected-GC"),
    Variable("protocol_counter", "protocol_counter", "1"),
)


class _HashedReader(io.RawIOBase):
    def __init__(self, stream):
        self.stream, self.digest = stream, hashlib.sha256()

    def readable(self):
        return True

    def readinto(self, buffer):
        block = self.stream.read(len(buffer))
        buffer[:len(block)] = block
        self.digest.update(block)
        return len(block)


@dataclass(frozen=True, slots=True)
class PemLoadReport:
    rows_seen: int
    rows_retained: int
    member_sha256: str
    malformed_numeric_cells: int
    nonpositive_frequency_rows: int


@dataclass(frozen=True, slots=True)
class PemExperiment:
    observations: ObservationTable
    measurement_types: tuple[str, ...]
    active_area_m2: float
    clock_id: str
    phase_sign: int
    report: PemLoadReport

    def __post_init__(self):
        finite(self.active_area_m2, "active_area_m2", positive=True)
        if self.observations.variables != VARIABLES:
            raise ValueError("PEM observations must use the reviewed variable contract")
        if len(self.measurement_types) != len(self.observations.values) or not self.clock_id:
            raise ValueError("PEM protocol labels and clock must identify every retained row")
        if self.phase_sign not in (-1, 1) or isinstance(self.phase_sign, bool):
            raise ValueError("Declare phase_sign as +1 or -1")
        object.__setattr__(self, "measurement_types", tuple(self.measurement_types))


@dataclass(frozen=True, slots=True)
class PemSpectrum:
    spectrum: ImpedanceSpectrum
    dc_current_a: float | None
    dc_voltage_v: float | None
    block_temperature_k: float | None
    cathode_pressure_pa: float | None
    dc_context_row_ids: tuple[str, ...]
    dc_gap_s: float | None = None


def load_pem_csv(stream: BinaryIO, *, experiment_id: str, source_id: str,
                 measurement_types: Collection[str], counters: Collection[int] | None,
                 active_area_m2: float, phase_sign: int) -> PemExperiment:
    """Consume the entire member for its hash; retain only explicit protocol selections.

    Zero-frequency/zero-impedance placeholders remain numeric but masked from
    spectral use. No timestamps, missing GC readings or protocol stages are filled.
    phase_sign declares whether source phase is arg(Z) or its negative.
    """
    finite(active_area_m2, "active_area_m2", positive=True)
    if phase_sign not in (-1, 1) or isinstance(phase_sign, bool):
        raise ValueError("Declare phase_sign as +1 or -1")
    selected_types = frozenset(measurement_types)
    selected_counters = None if counters is None else frozenset(counters)
    if not experiment_id or not source_id or not selected_types:
        raise ValueError("Declare experiment/source identities and selected protocol types")
    if selected_counters is not None and any(isinstance(c, bool) or not isinstance(c, int) or c < 1
                                             for c in selected_counters):
        raise ValueError("Selected counters must be positive integers")
    hashed = _HashedReader(stream)
    text = io.TextIOWrapper(io.BufferedReader(hashed), encoding="utf-8-sig", newline="")
    values, labels, row_ids, groups = [], [], [], []
    count = malformed = nonpositive = 0
    try:
        rows = csv.DictReader(text)
        if tuple(rows.fieldnames or ()) != HEADERS:
            raise ValueError("Archived PEM header differs from the reviewed source profile")
        for row in rows:
            count += 1
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Ragged PEM source row {rows.line_num}")
            label, counter_raw = row[HEADERS[-2]], row[HEADERS[-1]]
            if label not in selected_types:
                continue
            try:
                counter = int(counter_raw)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid selected protocol counter at source row {rows.line_num}") from exc
            if counter < 1:
                raise ValueError("Selected protocol counters must be positive")
            if selected_counters is not None and counter not in selected_counters:
                continue
            vector = []
            for header in HEADERS[:11]:
                cell = row[header]
                try:
                    vector.append(float(cell) if cell else float("nan"))
                except ValueError:
                    vector.append(float("nan"))
                    malformed += 1
            vector[1] += 273.15
            vector[2] *= 1e-3
            vector[7] *= 1e-4
            vector[8] *= 1e5
            vector[9] *= .01
            vector[10] *= .01
            vector.append(float(counter))
            nonpositive += int(np.isfinite(vector[4]) and vector[4] <= 0.)
            values.append(vector)
            labels.append(label)
            row_ids.append(f"{experiment_id}/row-{rows.line_num}")
            groups.append(f"{experiment_id}/{label}/{counter}")
    finally:
        text.detach().close()  # Close buffering without taking ownership of the caller's binary stream.
    matrix = np.array(values, dtype=float).reshape((-1, len(VARIABLES)))
    valid = np.isfinite(matrix)
    valid[:, 1] &= matrix[:, 1] > 0.
    valid[:, 4] &= matrix[:, 4] > 0.
    valid[:, 5] &= (matrix[:, 5] > 0.) & valid[:, 4]
    valid[:, 6] &= valid[:, 4]
    valid[:, 7] &= matrix[:, 7] >= 0.
    valid[:, 8] &= matrix[:, 8] > 0.
    for index in (9, 10):
        valid[:, index] &= (matrix[:, index] >= 0.) & (matrix[:, index] <= 1.)
    valid[:, 10] &= np.array([label in {"H2_char", "CstC_12A", "CstC_1A"} for label in labels], dtype=bool)
    origins = (Origin.MEASURED, Origin.RECONSTRUCTED, Origin.RECONSTRUCTED, Origin.MEASURED,
               Origin.MEASURED, Origin.MEASURED, Origin.MEASURED, Origin.RECONSTRUCTED,
               Origin.RECONSTRUCTED, Origin.RECONSTRUCTED, Origin.RECONSTRUCTED, Origin.RECONSTRUCTED)
    clock = experiment_id+"/reported-elapsed"
    table = ObservationTable(matrix, VARIABLES, valid, tuple(row_ids), tuple(groups), origins, source_id,
        (("member_sha256", hashed.digest.hexdigest()), ("clock_id", clock),
         ("active_area_m2", str(active_area_m2)), ("source_phase_sign", str(phase_sign)),
         ("selection_types", repr(sorted(selected_types))),
         ("selection_counters", repr(None if selected_counters is None else sorted(selected_counters)))))
    return PemExperiment(table, tuple(labels), active_area_m2, clock, phase_sign,
        PemLoadReport(count, len(values), hashed.digest.hexdigest(), malformed, nonpositive))


def pem_spectra(experiment: PemExperiment, *, dc_tail_rows: int = 10,
                maximum_dc_gap_s: float = 2., frequency_reset_ratio: float = 2.,
                ascending_frequency: bool = True) -> tuple[PemSpectrum, ...]:
    """Split positive-frequency blocks, retaining order and complete sweep identities.

    The preceding non-EIS tail supplies an explicit reconstructed DC context.
    EIS instantaneous AC current is never rounded into a presumed setpoint.
    """
    if not isinstance(dc_tail_rows, int) or isinstance(dc_tail_rows, bool) or dc_tail_rows < 1:
        raise ValueError("dc_tail_rows must be positive")
    finite(maximum_dc_gap_s, "maximum_dc_gap_s", positive=True)
    if finite(frequency_reset_ratio, "frequency_reset_ratio") <= 1.:
        raise ValueError("A sweep reset ratio must exceed one")
    if not isinstance(ascending_frequency, bool):
        raise ValueError("Declare the source frequency sweep direction")
    table = experiment.observations
    result, active, dc = [], [], []
    sequence = {}

    def flush():
        if not active:
            return
        group = table.experiment_ids[active[0]]
        ordinal = sequence.get(group, 0)+1
        sequence[group] = ordinal
        indices = np.array(active)
        frequency, magnitude, phase = table.values[indices, 4], table.values[indices, 5], table.values[indices, 6]
        response = magnitude*np.exp(1j*experiment.phase_sign*np.deg2rad(phase))
        spectral_valid = np.all(table.valid[indices][:, (4, 5, 6)], axis=1)
        spectrum = ImpedanceSpectrum(frequency, response, spectral_valid,
            tuple(table.row_ids[i] for i in indices), f"{group}/sweep-{ordinal}", table.source_id,
            Origin.RECONSTRUCTED, table.context+(("protocol_group", group),),
            frequency_origin=Origin.MEASURED)
        context = dc[-dc_tail_rows:]
        gap = (float(table.values[active[0], 0]-table.values[context[-1], 0])
               if context and table.valid[active[0], 0] and table.valid[context[-1], 0] else None)
        if gap is None or not 0. <= gap <= maximum_dc_gap_s:
            context = []

        def median(column):
            kept = [i for i in context if table.valid[i, column]]
            return float(np.median(table.values[kept, column])) if kept else None

        result.append(PemSpectrum(spectrum, median(2), median(3), median(1), median(8),
                                  tuple(table.row_ids[i] for i in context), gap))
        active.clear()

    for index in range(len(table.values)):
        changed = index > 0 and table.experiment_ids[index] != table.experiment_ids[index-1]
        if changed:
            flush()
            dc.clear()
        if table.valid[index, 4]:
            reset = active and (table.values[index, 4] < table.values[active[-1], 4]/frequency_reset_ratio
                if ascending_frequency else table.values[index, 4] > frequency_reset_ratio*table.values[active[-1], 4])
            if reset:
                flush()
                dc.clear()
            active.append(index)
        else:
            had_spectrum = bool(active)
            flush()
            if had_spectrum:
                dc.clear()
            dc.append(index)
    flush()
    return tuple(result)
