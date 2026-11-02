# Supplementary implementation contract for Request012: HyRAM source-transition conservation

**Receiving owner:** HyRAM native jet/source implementation and its maintainers.
**Host owner:** `h2physics` HyRAM adapter.
**Change type:** native source-transition diagnostics and, if justified, a separately
versioned initialization implementation.
**Current disposition:** open; host admission remains fail-closed.

This request expands the existing
[preferred dispersion boundary request](../requests/012_preferred_dispersion_boundaries.md)
and the [receiving implementation plan](hyram_gaussian_entry_receiving_plan.md).
It does not authorize the host to adjust native profiles or implement a second jet
solver. Preserve the GPL-3.0-only ownership of HyRAM and keep any native changes in
the receiving repository under its applicable license.

## Host audit implementation status — 2026-10-30

The host now has `h2physics.adapters.hyram_transition` with immutable radial-plane
capture and a same-run expanded-plug/Gaussian-entry conservation audit. It recomputes
H2 and total-mixture mass flow, axial momentum flux with pressure thrust relative to
ambient, and excess enthalpy plus kinetic-energy flux. It requires caller-declared
H2 source, ambient entrainment, external axial force and energy transfer, plus
separate balance and quadrature-error budgets. Missing data yields an `incomplete`
ledger; the adapter never inserts a zero or modifies the native initialization.
These contracts assume an axis-aligned radial plane and a common ambient pressure,
enthalpy, EOS and composition basis. The host can seal the caller's captured arrays
and retain the native object identity but cannot prove the capture came from the
claimed installed HyRAM revision. The synthetic case
`hyram-plug-to-gaussian-transition-ledger` is deferred in the Hangang/Nurion plans;
it is not native HyRAM reproduction or independent experimental evidence. The
receiving provider still must expose trustworthy snapshots and quadrature
convergence/error evidence before this audit can evaluate the actual mass gap.

## Reproduced issue and required behavior

The pinned authored case is normal hydrogen at 2 MPa and 300 K, through a 2 mm
opening with native discharge coefficient 0.8, into calm air at 101325 Pa and
293.15 K. The retained plug flow is `0.00309566981064 kg/s`; the host-integrated
H2 flow at Gaussian entry is `0.00237396473540 kg/s`. The entry deficit is about
23.31%, while subsequent ODE H2-flow drift is about `1.63e-10 kg/s`. The mismatch
is at initialization; it must not be hidden by fitting `lambda`, scaling the
concentration field, loosening the source gate, or replacing the native result.

First pin and inspect the exact installed HyRAM 6.1 source revision. The prior
public-branch `PlugNode.establish()` inspection is a hypothesis only and does not
identify the installed implementation. Preserve the original default result as an
unchanged, separately identifiable result in all comparisons.

## Proposed native Python boundary

The provider should issue same-run immutable radial snapshots from the plug exit
and Gaussian entry. Tuples below illustrate an API contract; the receiving owner
may choose a more efficient representation if it preserves immutability, units,
identity, and equivalent checks.

```python
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class RadialPlaneSnapshot:
    run_id: str
    source_revision: str
    plane: Literal["expanded_plug_exit", "gaussian_entry"]
    plane_id: str
    native_source: object
    transition_id: str
    axis_unit_vector: tuple[float, float, float]
    radial_coordinate_m: tuple[float, ...]
    annular_area_weight_m2: tuple[float, ...]
    density_kg_m3: tuple[float, ...]
    hydrogen_mass_fraction: tuple[float, ...]
    normal_velocity_m_s: tuple[float, ...]
    axial_velocity_m_s: tuple[float, ...]
    speed_squared_m2_s2: tuple[float, ...]
    pressure_pa: tuple[float, ...] | None
    mixture_enthalpy_j_kg: tuple[float, ...] | None
    ambient_pressure_pa: float
    ambient_enthalpy_j_kg: float
    thermo_model_id: str
    composition_basis_id: str
    profile_definition_id: str
    quadrature_id: str
    radial_cutoff_m: float
    profile_sha256: str


@dataclass(frozen=True, slots=True)
class SourceTransitionLedger:
    run_id: str
    transition_id: str
    plug: RadialPlaneSnapshot
    gaussian: RadialPlaneSnapshot
    h2_interstage_source_kg_s: float
    h2_flow_residual_kg_s: float
    mixture_flow_residual_kg_s: float
    ambient_entrainment_kg_s: float | None
    axial_momentum_residual_n: float | None
    external_axial_force_n: float | None
    excess_energy_residual_w: float | None
    external_energy_rate_w: float | None
    integration_error_h2_kg_s: float
    integration_error_mixture_kg_s: float
    integration_error_momentum_n: float | None
    integration_error_energy_w: float | None
    h2_budget_kg_s: float
    mixture_budget_kg_s: float
    momentum_budget_n: float | None
    excess_energy_budget_w: float | None
    acceptance: Literal["accepted", "rejected", "incomplete"]
    failure_reasons: tuple[str, ...]


class HyRAMSourceTransitionProvider(Protocol):
    def source_transition_ledger(
        self, run: object, *,
        quadrature_id: str,
    ) -> SourceTransitionLedger: ...
```

The provider must reject snapshots from different runs, transitions, source
objects, axes, thermodynamic references, composition bases, or profile versions.
Each radial vector must have the same nonzero length as the area weights; weights
must be finite and positive; all physical entries must be finite and in-domain.
Returned values must not alias mutable native arrays. `profile_sha256` covers the
profile values and quadrature weights in a specified canonical byte order. The
snapshot also retains the exact native source object for in-process identity checks;
the digest alone is not a substitute for that identity.

## Required ledgers and conventions

All rates and integrated fluxes use SI units. The radial quadrature weights
represent annular area in `m²` and include the declared radial truncation rule.
The plane normal and jet axis must be explicitly aligned for the axial formulas
below; otherwise the owner must provide the complete vector momentum flux and
traction rather than projecting implicitly.

For radial sample `i`, density `rho_i` is in `kg/m³`, hydrogen mass fraction
`Y_i` is dimensionless, normal and axial speeds are in `m/s`, pressure is in `Pa`,
and mixture specific enthalpy is in `J/kg`:

- H2 mass flow: `m_H2 = Σ rho_i * Y_i * u_n_i * ΔA_i` (`kg/s`).
- H2 inter-plane balance: `m_H2,gaussian - m_H2,plug - m_H2,source = 0`
  (`kg/s`). The gas-jet establishment transition should explicitly report zero
  inter-plane H2 production/consumption; an undeclared or unknown term is incomplete.
- Total mixture mass flow: `m_mix = Σ rho_i * u_n_i * ΔA_i` (`kg/s`).
- Ambient entrainment is an explicit independently reported term. For a declared
  ambient-air-only entrainment basis,
  `m_mix,gaussian - m_mix,plug - m_air,entrained = 0` (`kg/s`). Do not require
  total mixture flow to stay unchanged when ambient entrainment is physically
  represented.
- Axial momentum flow, for a plane normal aligned with the jet axis:
  `J_x = Σ (rho_i * u_n_i * u_x_i + p_i - p_ambient) * ΔA_i` (`N`). The
  transition balance is `J_x,gaussian - J_x,plug - F_x,external = 0` (`N`).
- Excess enthalpy plus kinetic-energy flow against the same ambient reference:
  `E_dot = Σ rho_i * u_n_i * ((h_i - h_ambient) + 0.5 * |v_i|²) * ΔA_i` (`W`).
  The transition balance is `E_dot_gaussian - E_dot_plug - Q_dot_external = 0`
  (`W`). Potential energy is excluded and must be stated as such.

H2 mass, mixture mass/entrainment, momentum, and excess-energy residuals must be
reported independently; no one balance can compensate for another. Pressure or
caloric profiles missing from the same-run state make the associated momentum or
energy ledger `incomplete`, never estimated from centerline values. Unknown force,
heat, species source, or ambient entrainment terms also make the related closure
`incomplete`. A candidate accepted result requires every declared balance to have
all terms available and each residual within its own fixed caller-approved budget.
H2 and mixture budgets are mandatory positive finite values; momentum and energy
budgets are mandatory when those ledgers are available. Budgets are not optimized
against the case and cannot change after the run.

## Acceptance and evidence

1. Record HyRAM source commit, package-tree digest, Python, NumPy and SciPy versions,
   solver settings, and input identities. Resolve the previously observed
   SciPy/HyRAM callback compatibility issue using a supported dependency range or
   upstream API; do not patch callback behavior globally.
2. Re-run the unmodified baseline case and preserve the values above within a
   predeclared reproduction budget. Retain native result objects and machine-readable
   same-run snapshots for both planes.
3. For the baseline and each candidate, report each plane's H2/mix flow, entrained
   ambient rate, momentum flux, excess-energy flux, every inter-plane residual,
   integration estimate, cutoff, and quadrature identity. Keep integration/truncation
   error separate from physical plane-to-plane residual.
4. Halve the radial quadrature spacing and independently tighten the radial tail
   cutoff. Each ledger's change must meet its separately declared numerical
   integration budget.
5. If the native owner implements a conservative initialization, return it as a
   separately versioned method/result. Recompute all ledgers; do not mutate the
   baseline output. Run the unchanged downstream integration and distinguish its
   transport drift from the entry mismatch.
6. Run the matrix below as independent parallel jobs. Every job records source and
   environment fingerprints, raw native result, snapshots, ledgers, budgets, and
   failure reason. Preserve rejected and incomplete results.
7. Conservation demonstrates software consistency only. Independent applicable
   measurements and predeclared comparison metrics are required before marking any
   result experimentally validated or broadly suitable.

| Axis | Parallel cases |
|---|---|
| Upstream pressure | Baseline 2 MPa; lower and higher pressure with otherwise matched settings |
| Opening | Smaller and larger openings around the baseline 2 mm |
| Pressure ratio | At least one materially different upstream-to-ambient pressure ratio |
| Ambient | Baseline plus a second declared ambient pressure/temperature state |
| Numerical integration | Baseline quadrature; half radial spacing; tighter tail cutoff, each varied independently |
| Regression | Original default initialization, unchanged downstream ODE from its entry, and separately versioned candidate initialization if supplied |

Numerical values and budgets for the additional conditions must be declared before
submission; no case is accepted by inheriting the baseline budget without review.

## Host-side integration after receipt

The host adapter may consume the issued ledger through a read-only receipt, verify
its same-run identities and recompute every available flux from the immutable
snapshots. It continues to reject a native run when H2 source mass fails the current
host gate. It must preserve `incomplete` versus `rejected`, retain the original
native result, and expose all residuals and budgets to callers. Until the receiving
provider supplies complete snapshots, the host must not claim momentum/energy
closure or repair the H2 mass gap.
