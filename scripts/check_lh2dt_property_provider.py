"""Check and time the native state interface, using the exact reference EOS in both paths."""

import hashlib
import statistics
import sys
import time
from pathlib import Path

from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.thermo import CoolPropProperties

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/native_packages"
sys.path.insert(0, str(target))
from lh2dt.properties import HydrogenProperties, ThermoState  # noqa: E402

reference = HydrogenProperties("ParaHydrogen")
provider = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
fast = Lh2dtLowLevelProperties(provider, state_factory=ThermoState)
single = [reference.from_pT(p, t) for p, t in ((300000., 20.), (300000., 28.),
          (1000000., 20.), (5000000., 300.), (100000., 300.))]
states = list(single)
for pressure in (100000., 300000.):
    left, right = reference.saturated_liquid(pressure), reference.saturated_vapor(pressure)
    states.extend([left, reference.from_ph(pressure, .8*left.specific_enthalpy_J_kg
                                          +.2*right.specific_enthalpy_J_kg), right])
queries = [("from_pT", (state.pressure_Pa, state.temperature_K)) for state in single]
for state in states:
    queries.extend([("from_ph", (state.pressure_Pa, state.specific_enthalpy_J_kg)),
                    ("from_ps", (state.pressure_Pa, state.specific_entropy_J_kgK)),
                    ("from_pu", (state.pressure_Pa, state.specific_internal_energy_J_kg)),
                    ("from_prho", (state.pressure_Pa, state.density_kg_m3)),
                    ("from_rho_u", (state.density_kg_m3, state.specific_internal_energy_J_kg))])
fields = {"pressure_Pa": 1e-4, "temperature_K": 1e-7, "density_kg_m3": 1e-9,
          "specific_enthalpy_J_kg": 1e-5, "specific_internal_energy_J_kg": 1e-5,
          "specific_entropy_J_kgK": 1e-6}
largest_absolute = dict.fromkeys(fields, 0.)
worst_gate_fraction = 0.
for name, args in queries:
    expected, actual = getattr(reference, name)(*args), getattr(fast, name)(*args)
    assert isinstance(actual, ThermoState)
    for field, absolute in fields.items():
        error = abs(getattr(expected, field)-getattr(actual, field))
        largest_absolute[field] = max(largest_absolute[field], error)
        gate = absolute+1e-8*abs(getattr(expected, field))
        worst_gate_fraction = max(worst_gate_fraction, error/gate)
        assert error <= gate, (name, args, field, error, gate)
    assert expected.phase == actual.phase
    if expected.quality is None or actual.quality is None:
        assert expected.quality is actual.quality
    else:
        assert abs(expected.quality-actual.quality) <= 1e-8
for state in [*single, reference.saturated_liquid(300000.), reference.saturated_vapor(300000.)]:
    assert abs(fast.viscosity_Pa_s(state)/reference.viscosity_Pa_s(state)-1.) < 1e-8
for temperature in (20., 25., 30.):
    assert abs(fast.saturation_pressure_Pa(temperature)/reference.saturation_pressure_Pa(temperature)-1.) < 1e-10


def timing(model):
    start = time.perf_counter()
    checksum = 0.
    for _ in range(5):
        for name, args in queries:
            checksum += getattr(model, name)(*args).density_kg_m3
    elapsed = time.perf_counter()-start
    assert checksum > 0
    return elapsed


slow_times, fast_times = [], []
for _ in range(3):
    slow_times.append(timing(reference))
    fast_times.append(timing(fast))
slow, quick = statistics.median(slow_times), statistics.median(fast_times)
lines = ["# Native equipment property-interface verification", "",
    "Both paths use CoolProp HEOS ParaHydrogen. The reference is the pinned native "
    "LH2DT HydrogenProperties; the new structural facade returns the actual native "
    "ThermoState factory after one protected AbstractState flash. No EOS, property "
    "table, interpolation or hidden fallback is added.", "",
    f"Declared basis: `{provider.basis.reference_id}`. Native revision "
    "`b2f276333c1b1793c39f25763703d196d36742ec`.",
    f"{len(queries)} PT/PH/PS/PU/P-rho/rho-U queries cover liquid, vapor, warm gas and "
    "saturated/intermediate quality. Phase labels and quality also agree. Relative "
    "tolerance is 1e-8 with field-specific absolute floors below; viscosity and saturation "
    "pressure have separate comparisons. No experimental property accuracy is inferred.", "",
    "| Field | Absolute floor | Largest absolute difference |", "|---|---:|---:|"]
lines += [f"| {name} | {floor:.12g} | {largest_absolute[name]:.12g} |" for name, floor in fields.items()]
lines += ["", f"Largest fraction of a state-comparison gate: {worst_gate_fraction:.12g}.",
    f"Explicit quality roundoff budget: {provider.quality_roundoff_tolerance:g}; "
    f"maximum observed adjustment {fast.maximum_quality_adjustment:.12g}; "
    f"adjustment count after verification/timing {fast.quality_adjustment_count}.",
    "The native state class has no raw-quality field; the facade retains maximum/count "
    "and the last adjusted host state. Unsupported native methods remain absent. "
    "Mixture viscosity is not invented; the native HEM pipe keeps its own declared "
    "mixture closure. This subset is for the explicitly checked equipment, not every "
    "native component or constructor that demands an exact HydrogenProperties type.", "",
    f"Mixed public-interface timing: {len(queries)*5} full native states per trial, "
    f"three trials; median reference {slow:.12g} s, facade {quick:.12g} s, ratio {slow/quick:.9g}.",
    "This measured run includes mapping/native object creation. It does not predict "
    "whole-network speedup; the coupled simulator is measured separately.", "", "Host code SHA-256:", ""]
for relative in ("src/h2physics/adapters/lh2dt_properties.py", "src/h2physics/thermo/coolprop.py",
                 "scripts/check_lh2dt_property_provider.py"):
    lines.append(f"- `{relative}`: `{hashlib.sha256((root/relative).read_bytes()).hexdigest()}`")
(root / "research/native_property_provider.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
print("native interface queries", len(queries), "worst gate fraction", worst_gate_fraction, "speed ratio", slow/quick)
