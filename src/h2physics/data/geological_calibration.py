"""Pinned raw H2/He observations and sample inputs; no calibration fit or EOS."""

import csv
import io
from dataclasses import dataclass, field
from hashlib import sha256
from math import isfinite
from pathlib import Path
from zipfile import ZipFile

from .geological_adsorption import SOURCE_SHA256


@dataclass(frozen=True, slots=True)
class ReportedSIQuantity:
    name: str
    value: float | None
    unit: str
    source_column: str
    role: str
    missing_reason: str | None = None

    def __post_init__(self):
        if not all(isinstance(value, str) and value.strip()
                   for value in (self.name, self.unit, self.source_column, self.role)):
            raise ValueError("A reported quantity needs explicit name, unit, column and role")
        if self.value is not None and (isinstance(self.value, bool)
                or not isinstance(self.value, (int, float)) or not isfinite(self.value)):
            raise ValueError("A present reported quantity must be finite")
        if self.value is None and (not isinstance(self.missing_reason, str)
                                   or not self.missing_reason.strip()):
            raise ValueError("A missing reported quantity needs its source-level reason")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("A present quantity cannot also claim to be missing")

    def require_absolute_pressure_pa(self):
        """Do not promote a converted source pressure to EOS-ready absolute pressure."""
        if self.unit != "Pa" or not self.role.endswith("_pressure"):
            raise ValueError("This source quantity is not a reported pressure")
        raise ValueError(
            "Absolute-versus-gauge pressure basis is unqualified; independent evidence "
            "and an explicit conversion are required before EOS use."
        )


@dataclass(frozen=True, slots=True)
class GeologicalCalibrationRow:
    member: str
    line_number: int
    material: str
    run: str | None
    raw_fields: tuple
    quantities: tuple[ReportedSIQuantity, ...]


@dataclass(frozen=True, slots=True)
class GeologicalCalibrationData:
    source_sha256: str
    hydrogen_rows: tuple[GeologicalCalibrationRow, ...]
    helium_rows: tuple[GeologicalCalibrationRow, ...]
    sample_rows: tuple[GeologicalCalibrationRow, ...]
    source_doi: str = field(default="10.5281/zenodo.22305898", init=False)
    source_license: str = field(default="CC-BY-4.0", init=False)
    pressure_basis: str = field(default="reported; absolute-versus-gauge not qualified", init=False)


def load_geological_calibration(path):
    """Read three raw source tables with explicit reported-pressure roles.

    Source-defined initial, equilibrium and calibration roles are retained.
    Conversion to Pa does not admit a reported pressure as an absolute EOS input.
    Missing He pressure differences stay None and are never supplied by a fit.
    Values of reported uncertainties are converted to SI without propagation.
    """
    path = Path(path)
    if path.stat().st_size > 32_000_000:
        raise ValueError("Raw calibration archive exceeds the pinned bounded reader")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Raw calibration archive differs from the pinned source")
    specs = (
        ("h2_equilibrium_points.csv", ("material", "run", "P_initial_bar", "P_bar", "T_K", "DeltaP_H2_mbar"),
         (("P_initial_bar", "initial_pressure_pa", 1e5, "Pa", "reported_initial_pressure"),
          ("P_bar", "equilibrium_pressure_pa", 1e5, "Pa", "reported_equilibrium_pressure"),
          ("T_K", "temperature_k", 1., "K", "reported"),
          ("DeltaP_H2_mbar", "hydrogen_pressure_difference_pa", 100., "Pa", "reported_difference"))),
        ("he_calibration_points.csv", ("material", "P_bar", "DeltaP_He_mbar"),
         (("P_bar", "calibration_pressure_pa", 1e5, "Pa", "reported_calibration_pressure"),
          ("DeltaP_He_mbar", "helium_pressure_difference_pa", 100., "Pa", "reported_difference"))),
        ("sample_configuration.csv", ("material", "mass_g", "Vr_L", "Vs_L", "u_mass_g", "u_Vr_L", "u_Vs_L", "u_T_K", "u_DeltaP_H2_mbar"),
         (("mass_g", "sample_mass_kg", .001, "kg", "configuration"),
          ("Vr_L", "reference_volume_m3", .001, "m3", "configuration"),
          ("Vs_L", "sample_volume_m3", .001, "m3", "configuration"),
          ("u_mass_g", "sample_mass_standard_uncertainty_kg", .001, "kg", "reported_standard_uncertainty"),
          ("u_Vr_L", "reference_volume_standard_uncertainty_m3", .001, "m3", "reported_standard_uncertainty"),
          ("u_Vs_L", "sample_volume_standard_uncertainty_m3", .001, "m3", "reported_standard_uncertainty"),
          ("u_T_K", "temperature_standard_uncertainty_k", 1., "K", "reported_standard_uncertainty"),
          ("u_DeltaP_H2_mbar", "hydrogen_pressure_difference_standard_uncertainty_pa", 100., "Pa", "reported_standard_uncertainty"))),
    )
    outputs = []
    with ZipFile(io.BytesIO(raw)) as archive:
        for filename, header, columns in specs:
            matches = [n for n in archive.namelist() if n.endswith("/01_raw_data/h2_he_equilibrium/"+filename)]
            if len(matches) != 1:
                raise ValueError("Raw calibration table must have one exact archive member")
            member = matches[0]
            reader = csv.DictReader(io.StringIO(archive.read(member).decode("utf-8-sig"), newline=""))
            if tuple(reader.fieldnames or ()) != header:
                raise ValueError("Pinned raw calibration schema changed")
            rows = []
            for values in reader:
                if None in values or any(value is None for value in values.values()) or not values["material"].strip():
                    raise ValueError("Malformed raw calibration source row")
                quantities = []
                for column, name, factor, unit, role in columns:
                    token = values[column].strip()
                    number = None if not token else float(token)*factor
                    missing_reason = None
                    if number is None:
                        if column == "DeltaP_He_mbar":
                            missing_reason = "absent source observation; logger-derived replacement not applied"
                        elif filename == "sample_configuration.csv" and column in {"mass_g", "Vr_L", "Vs_L"}:
                            missing_reason = "absent CSV configuration; linked source workbook inputs not resolved"
                        else:
                            raise ValueError("Required raw calibration source quantity is absent")
                    if number is not None and (not isfinite(number) or (role == "reported_standard_uncertainty" and number < 0.)):
                        raise ValueError("Raw source quantity or uncertainty is inadmissible")
                    quantities.append(ReportedSIQuantity(name, number, unit, column, role, missing_reason))
                rows.append(GeologicalCalibrationRow(member, reader.line_num, values["material"],
                    values.get("run"), tuple(values.items()), tuple(quantities)))
            outputs.append(tuple(rows))
    return GeologicalCalibrationData(SOURCE_SHA256, *outputs)
