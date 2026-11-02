# Native inverse contents heat and effective area

The optional MIT pifira0.3.0 package owns the closed-vessel pressure-rise energy
calculation and centered angular radiation-shape fit. The host keeps native
objects, enforces explicit units/references/observation scope and compares
native contents U with a separate direct-HEOS pressure/density flash.

This produces the signed rate of contents internal-energy increase. Incident
fire radiation/convection, wall storage, losses, work, vent transport and spin
conversion need their own energy allocation. Pressure rise alone cannot separate
those terms or establish a flame footprint.

## Native installation and identity

```powershell
python -m pip install ".[thermo,inverse_heat]"
python scripts/check_pifira_heat.py
```

For a separately installed target use the script's `--native-packages` argument.
The checked wheel, PyPI metadata/license and nine installed-source identities are
recorded in research/pifira_dependency.toml. This is a version-specific adapter;
the native source, external mechanisms and experimental data are not bundled.
The native module and TankSpec remain ordinary Python objects.

## Pressure-history interface

```python
import numpy as np
import pifira
from h2physics.adapters.pifira_heat import (
    ClosedHeatDomain, ClosedHeatEvidence, PifiraClosedVesselHeat,
)
from h2physics.core import Origin, TimeSeries
from h2physics.thermo import CoolPropProperties

# Authored synthetic example, without apparatus calibration.
properties = CoolPropProperties("ParaHydrogen")
tank = pifira.TankSpec(volume=.04, fluid="HEOS::ParaHydrogen", fill=.35)
evidence = ClosedHeatEvidence(
    "authored-heat", "closed-material-boundary", "rigid-vessel",
    "homogeneous-equilibrium", "contents-U-only; wall/work separate",
    Origin.SYNTHETIC,
)
adapter = PifiraClosedVesselHeat(
    pifira, tank, properties, evidence=evidence,
    domain=ClosedHeatDomain(1e5, 8e5),
)
history = TimeSeries(
    np.array([100., 110., 120.]), np.array([[1.5e5], [2e5], [2.5e5]]),
    ("P",), ("Pa",), np.ones((3, 1), bool), "heat-clock",
    Origin.SYNTHETIC, "authored-heat", ("pressure",), ("absolute",),
)
# Explicit native initial-fill inference; a qualified measured mass can replace it.
mass = adapter.derive_initial_mass(1.5e5)
trace = adapter.run(history, "P", mass_kg=mass,
                    mass_evidence_id="native-declared-initial-fill")
interval_average_power_w = trace.interval_heat_w
native_total_energy_j = trace.native_energy_j
native_tank = trace.native_tank
```

The pressure channel must explicitly be `pressure`, `Pa`, basis `absolute`, with
complete valid samples and a resolved source/origin. No gauge conversion, mask
fill, clock alignment or assumed vent closure is performed. The native function
uses a gauge-coordinate API with its own101325Pa zero. The host subtracts that
zero and the native function adds it back, preserving the supplied absolute
pressure. That algebraic conversion does not identify a measured gauge sensor's
reference atmosphere.

`mass_kg` is always explicit. `derive_initial_mass` is a separate opt-in operation
using the declared native initial liquid volume fraction. A provided fixed mass
does not use TankSpec.fill to recompute mass at later pressures. Sample states
must remain within the declared two-phase quality/pressure domain. Direct HEOS
flash failure, a single-phase state, different pure-fluid/spin definitions,
native/EOS U mismatch, native definition mutation or a failed interval U ledger
is a rejection. No lever-rule extrapolation or phase clipping is authorized.

The finite interval result is native ΔU/Δt. It does not require pressure to vary
linearly; it is an interval-average contents energy rate. Cooling can be negative
and stationary pressure gives zero within the model. Between-sample phase paths
and the truth of fixed mass/volume/equilibrium are not established by endpoint
checks. The declared evidence needs independent apparatus/operation support.

## Conditional angular area and flux

`pifira_effective_area` delegates the actual native angular optimizer and native
height/area functions. Supply wall temperatures in K, centered angles in degrees,
ambient K, diameter, `AxialContactGeometry` and `EffectiveAreaEvidence`. The axial
geometry gives flame-contact and wetted start/end coordinates in one explicit
common axis frame. At least five distinct angles in[-180,180), including
the known centre and both tails, are required. No peak centering is inferred.

The selected native interpretation is a positive local Gaussian in wall
T^4−Tamb^4. The host independently checks its residual, full-circumference limit
and declared tail coverage. A broad/flat, truncated, miscentered or negative-drive
profile can fail. The host translates both explicit axial intervals to their
common overlap start, then delegates the positive remaining min-height to the
native function. Unequal lower positions are retained. Disjoint intervals return
zero area and cannot be divided into a finite equivalent flux. The native
equivalent angular width and conditional axial intersection are model choices, not a measured incident-fire area or
a universal statement that vapor-space heating is negligible. Geometry, emissivity,
wall conduction and observation roles need their own evidence.

Ordinary arithmetic-mean temperatures do not determine mean T^4. The evidence
must declare instantaneous or fourth-power-equivalent temperatures and the source,
clock and support. A fit covariance warning remains visible; returned residuals
are numerical shape diagnostics, not parameter uncertainty or measured accuracy.

`contents_equivalent_heat_flux(trace, interval, area,
allocation_evidence_id=...)` uses the native flux function and converts its kW/m2
output to W/m2. It requires exact source/clock/interval identities. The returned
`ContentsEquivalentFlux` retains both objects, interval and allocation evidence.
The result is a signed contents-energy-equivalent flux, with wall/loss/work scope
still explicit. It cannot silently become incident flux for a wall or a dose.
The `EffectiveAreaResult` is issued only by the native-fit adapter and carries a
sealed snapshot of its geometry, observations, native functions and fitted values.
`contents_equivalent_heat_flux` rechecks it before using the area; direct construction,
cloning or post-issuance changes cannot provide an area basis to the handoff.

## Verification and remaining work

`tests/test_pifira_heat.py` checks actual native normal/para/ortho H2, independent
forward-EOS heating, signed/zero energy, invalid phase/reference/observation
handling, mutation/corrupted-ledger rejection, analytic area, thermal scaling and
explicit pairing. `check_pifira_heat.py` uses three native spin providers and two
output grids, independently prescribed time-varying power, native/EOS U and
analytic geometry. Begin/end identities and results are in research/native_fire_heat.md.

These are numerical/native-reference checks. Acquired thermal experiments retain
their own unresolved recorder clock, sensor and quantity roles; they have not
validated this inverse vessel model. Stratification, wall/contents heat exchange,
venting, evolving-spin thermochemistry, spatial fire prediction and source-specific
independent apparatus comparisons remain open.

Primary references: [native pifira API](https://github.com/lyullee/pifira),
[archived0.3.0 source](https://doi.org/10.5281/zenodo.22291661), and
[CoolProp direct EOS](https://coolprop.org/coolprop/LowLevelAPI.html). Original
composition, checks and synthetic cases are provided here; no native implementation,
published worked example, coefficient table or experimental content is copied.
