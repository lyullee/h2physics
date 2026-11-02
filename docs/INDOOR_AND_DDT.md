# Indoor releases and combustion-regime screening

The indoor adapter and the FA/DDT screen answer different questions. Neither
returns an explosion probability, a structural load waveform, or a facility
safety certificate. They can be imported independently from their Python modules.

## Indoor accumulation and conditional peak pressure

`h2physics.adapters.indoor_release.run_hyram_indoor_release` constructs native
HyRAM+ `Fluid`, `Source`, `Orifice`, `Vent`, `Enclosure` and `IndoorRelease`
objects from immutable SI boundaries. HyRAM+ owns its nozzle, plume, layering,
flammability and enclosure peak calculations. This adapter does not copy or
replace those solvers. HyRAM+ remains a separately installed GPL-3.0-only
dependency, outside h2physics source and distributions.
The selected route uses normal hydrogen and air, and rejects native liquid or
two-phase inlet states. It is not an indoor liquid-hydrogen spreading model.

The inspected native API is HyRAM+ **6.1**. The actual native execution recorded
for this addition used Python 3.12, CoolProp 8.0.0 and SciPy **1.16.3**. A local
native dependency directory containing a second SciPy must be selected before
starting Python, or installed in its own environment. Adding that directory
after parts of another SciPy have already been imported can mix Python wrappers
and binary modules. The initial mixed-runtime test failed with a `dopri5`
callback signature error. The isolated, consistently selected runtime passed;
no native solver was patched and no alternate physics was substituted.

```python
from h2physics.adapters.indoor_release import (
    IndoorEnclosure, IndoorHydrogenSource, IndoorReleaseSettings, IndoorVent,
    run_hyram_indoor_release,
)

# Authored demonstration boundaries; these are not qualified facility inputs.
source = IndoorHydrogenSource(
    pressure_pa_absolute=200_000.0, temperature_k=293.15,
    vessel_volume_m3=0.01, orifice_diameter_m=0.001,
    source_id="example-H2-vessel", boundary_evidence_id="authored-demonstration",
)
room = IndoorEnclosure(
    height_m=2.0, floor_area_m2=4.0, release_height_m=0.5,
    release_to_wall_m=2.0,
    ceiling_vent=IndoorVent(area_m2=0.04, height_m=1.9),
    floor_vent=IndoorVent(area_m2=0.04, height_m=0.1),
    geometry_evidence_id="authored-demonstration",
)
settings = IndoorReleaseSettings(
    duration_s=0.1, clock_id="operation-seconds", source_start_time_s=42.0,
    steady_source=True, steady_steps=2,
)
result = run_hyram_indoor_release(source, room, settings)
result.require_current()
print(result.ignition_delay_s)
print(result.peak_overpressure_pa_gauge)
```

`steady_source=True` maintains the declared upstream state. Vessel volume does
not impose finite depletion in this mode. `steady_source=False` delegates finite
source emptying to HyRAM+. The present native evidence covers the short steady
example; it is not a validated blowdown envelope. Native errors propagate.

The returned `IndoorIgnitionDelayPeaks` explicitly has axis kind
`release_age_at_hypothetical_ignition`:

| Field | Meaning |
| --- | --- |
| `ignition_delay_s` | Age of the release when hypothetical ignition occurs |
| `ignition_clock_time_s` | The same points plus declared source start time |
| `peak_overpressure_pa_gauge` | Native peak relative to the declared ambient pressure |
| `conditional_peak_pressure_pa_absolute` | Ambient absolute pressure plus that peak |
| `layer_hydrogen_mole_fraction` | Native `x_layer` in mol/mol, not percent |
| `layer_depth_m` | Native upper-layer depth, not interface height above the floor |
| `flammable_jet_hydrogen_mass_kg` / `flammable_layer_hydrogen_mass_kg` | Native flammable H2 stocks |

The snapshots are immutable copies. The retained native object is available for
research inspection; `require_current()` detects changes in the native arrays
captured by this result. A peak-versus-ignition-delay curve must **not** be passed
as pressure-versus-time-after-ignition to a structural response model. This
adapter does not predict a vented explosion's multiple transient peaks, spatial
receptor pressures, reflected load, or blast impulse.

Native method and scope: [HyRAM+ technical reference](https://www.osti.gov/servlets/purl/2563814)
and [Sandia capabilities](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/).

## Flame acceleration and DDT necessary conditions

`h2physics.combustion_screening` separates three pieces:

1. `MixtureExpansion` holds the density ratio of the unburned mixture to
   adiabatic constant-pressure equilibrium products. The optional
   `cantera_mixture_expansion` computes it with the caller's actual Cantera
   ideal-gas `Solution`, restores the original gas state, and retains the
   mechanism evidence identity. It admits H2, O2, N2 and steam, with the selected
   dry-air N2/O2 molar ratio of 3.76. This is reacting-engine thermochemistry,
   separate from CoolProp fluid-state calculations.
2. `FlameAccelerationCriterion` combines an evidenced interval for critical
   expansion ratio with the qualified temperature, pressure, hydrogen, steam
   and geometry domain. It does not infer the critical value from composition
   alone. An optional published polynomial evaluates sigma-star from
   `x = (Ea/R)/Tu` when the application supplies qualified x support and
   turbulent Peclet number at least 100. `activation_temperature_k` is Ea/R in K,
   not an activation energy in J/mol. There is no implicit cryogenic
   extrapolation or universal room-temperature threshold.
3. `DetonationCellCriterion` compares an evidenced characteristic dimension
   with a supplied multiple of an evidenced cell-width interval. The selected
   multiple defaults to 7. Cell data must match the exact mixture-condition
   identity; the geometry evidence must define which dimension is meaningful.
   A tube criterion does not automatically apply to a flat layer, unconfined
   cloud or complex compartment.

The polynomial implementation and its qualifications follow
[Kuznetsov et al., 2022](https://doi.org/10.1016/j.ijhydene.2022.07.024),
whose [author-institution record](https://publikationen.bibliothek.kit.edu/1000150188)
identifies the article. The paper distinguishes its measured cryogenic work
from extrapolation of earlier critical-expansion criteria. This implementation
does not bundle an experimental parameter table or cell-width dataset.

`vent_corrected_critical_expansion` optionally applies a supplied coefficient
interval in `sigma_vent/sigma_closed = 1 + c*alpha`. The caller must supply
the qualified vent-ratio range and evidence for the coefficient and geometry.
Here alpha is vent area divided by total tube surface area; it is not vent
area divided by floor area. [Alekseev et al., 2001](https://doi.org/10.1016/S0950-4230(01)00051-1)
studied specific transverse-vented obstructed tubes. No coefficient is treated
as universal, and no correction is silently applied to other enclosures.

### Direct Python use

```python
from pathlib import Path
import cantera as ct
from h2physics.combustion_screening import (
    DetonationCellCriterion, EvidenceInterval, FlameAccelerationCriterion,
    ScreeningDomain, ScreeningGeometry, cantera_mixture_expansion,
    screen_combustion,
)

native_yaml = (Path(ct.__file__).parent / "data" / "h2o2.yaml").read_text(encoding="utf-8")
expansion = cantera_mixture_expansion(
    ct.Solution(yaml=native_yaml, name="ohmech"), temperature_k=300.0,
    pressure_pa_absolute=101325.0,
    mole_fractions={"H2": 2.0, "O2": 1.0, "N2": 3.76},
    condition_id="example-mixture", mechanism_evidence_id="installed-h2o2.yaml",
)
geometry = ScreeningGeometry.CLOSED_OBSTRUCTED_TUBE
# Every value below is authored to demonstrate API arithmetic, not a measured
# cell width or a qualified applicability range. Replace the whole evidence set.
domain = ScreeningDomain(290.0, 310.0, 100_000.0, 110_000.0,
    0.1, 0.3, 0.0, (geometry,), "authored-example-domain")
flame = FlameAccelerationCriterion(
    EvidenceInterval(3.5, 4.0, "authored-critical-interval"), domain,
    "authored-example-rule",
)
cell = DetonationCellCriterion(
    EvidenceInterval(0.05, 0.2, "authored-cell-width-m"),
    EvidenceInterval(1.0, 1.0, "authored-length-m"), domain,
    "example-mixture", "authored-length-definition", "authored-cell-rule",
)
screen = screen_combustion(expansion, geometry, flame, cell)
print(screen.flame_acceleration, screen.cell_size, screen.combined_ddt)
print(screen.reasons)
```

Each status is `necessary_condition_met`, `necessary_condition_not_met`, or
`indeterminate`. Strictly greater-than comparisons are used. Uncertainty
overlapping a threshold stays indeterminate; the midpoint is not substituted.
Out-of-domain criteria or mismatched cell conditions are also indeterminate.
Both necessary conditions met still leaves actual ignition, obstacle layout,
flame path, run-up and transition unresolved. A failed criterion only rejects
this selected route; it does not exclude direct initiation or declare safety.

## Executed verification and reproducibility

The focused command is:

```text
python -m pytest -q tests/test_combustion_screening.py tests/test_indoor_release.py
```

In an environment without HyRAM+, the two genuine-native indoor tests are
explicitly skipped. For separately reviewed local native sources,
`H2PHYSICS_HYRAM_PATH` selects their directory; if it contains scientific runtime
packages, also place it on `PYTHONPATH` **before starting Python** or install the
matching dependencies in an isolated environment. Never insert a second SciPy
into an already running scientific process.

The successful recorded run passed **30 tests**, including the actual HyRAM+
steady calculation and actual Cantera H2/air equilibrium. Coverage includes SI
and clock admission, exact projection of native fractions/gauge pressures,
absolute-pressure conversion, immutable snapshots, changed-native detection,
independent density-ratio identity, threshold and equality cases, uncertainty
overlap, unmatched cell conditions, geometry/domain exclusions, polynomial
arithmetic and vent correction bounds. These are host numerical/connection
checks. They do not revalidate native engine physics or compare the new screen
with held-out FA/DDT measurements.
