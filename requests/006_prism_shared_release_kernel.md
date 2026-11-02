# PRISM shared equilibrium nozzle and source-plane handoff

Status: concrete local implementation and synthetic verification available; request prepared,
not sent. Target: `lyullee/prism`, reviewed revision
`884b0553341beb2d51d1d3c563f86982f378e160`.

## Reason and authoritative ownership

The reviewed `lh2-tno/src/prism_lh2_models/lh2_critical_flow.py` HEM path accepts upstream
P/T, evaluates an isentrope and selects the largest interior sampled mass flux. Its interface
cannot distinguish saturated liquid/vapor/two-phase states at the same P/T. Omitting the
back-pressure endpoint prevents exact selection of a back-pressure-limited solution;
skipping failing state evaluations hides incomplete EOS-path coverage.

The local `h2physics.release.HomogeneousIsentropicNozzle` now supplies a single original
kernel for the same equilibrium physical level. Consolidate equivalent HEM implementations
by delegation. Do not maintain another corrected copy of the same search algorithm in PRISM.
Nonequilibrium flow can remain a distinct level when its additional closure is justified.

## Local Python contract

```python
class EquilibriumNozzle(Protocol):
    def solve(self, upstream_stagnation: ThermoState, *,
              back_pressure_pa: float, opening: NozzleOpening,
              opening_fraction: float = 1.0) -> NozzleResult: ...
```

The complete executable contracts are in `src/h2physics/release.py` and the usage guide
is `docs/RELEASE_AND_SOURCE.md`. `ThermoState` carries absolute SI state, optional quality
and explicit fluid/spin/energy-reference identity. `NozzleOpening` has an opening ID,
nominal area, explicit effective-area factor and basis ID. `NozzleResult` retains upstream,
back pressure, exit state, effective area, velocity, flux, mass flow, regime and diagnostics.
The host `NozzleSourceProjection` also requires nonblank quadrature and representative-state
evidence IDs when directly constructed; a matching source evidence string cannot legitimize
whitespace-only declarations. A deferred constructor contract records that rejection.

Use native Python objects/callables. An injected structural protocol avoids making PRISM's
whole dependency graph or optional consequence packages mandatory for this library. Existing
PRISM result fields can be populated from the local result without changing their units.
If the old P/T convenience constructor is retained, require a single-phase state or explicit
quality/enthalpy when P/T is ambiguous. Never infer quality from temperature equality.

## Required receiving behavior

1. Delegate the HEM physical path to one injected kernel. Keep version/reference provenance.
2. Preserve back-pressure-limited and closed/no-forward states. There is no unique critical
   throat for a closed source; use an optional state or an explicit regime.
3. Surface EOS-domain and numerical failures. Do not skip failed samples and label the
   remaining maximum qualified. Preserve convergence/evaluation diagnostics.
4. Distinguish nozzle static enthalpy, kinetic power and reservoir withdrawal energy.
   Preserve the declared area interpretation when transferring momentum/pressure force.
5. Consume `SourceHistory` through the retained common clock, opening/source identity and
   spatial reference. Store accepted integration states, not RK stages or retries.
6. Do not map nozzle liquid quality directly to ground-liquid transfer. Droplets/impact
   and atmospheric expansion need separate explicit providers and conservation tests.
7. Keep independent nonequilibrium methods opt-in; their presence does not validate HEM
   or justify using an arbitrary relaxation parameter without source-specific evidence.

## Acceptance

- Compare constant-cp ideal-gas choked pressure/flux to the analytical result and recover
  the exact back-pressure endpoint for subcritical flow.
- Exercise explicit saturated liquid/vapor and mixed-quality upstream states through PS
  flashes; reject a deliberately inconsistent reference/state and an EOS-domain hole.
- Check zero forward flow when closed or reverse-pressured and linear effective-area scaling.
- Check nozzle static-plus-kinetic energy and the actual native tank mass/energy ledgers.
- Reproduce step-refinement evidence in `research/native_release.md`. This verifies synthetic
  coupling only; independent applicable critical-flow experiments remain required.
- Preserve existing public import/result compatibility or document a deliberate version change.

The kernel now records optional single-phase sonic refinements and maximum declared quality
roundoff. Preserve these diagnostics when mapping results. New flat-peak states and the
unchanged pressure/flux acceptance gates are reproducible in `research/nozzle_search_coordinates.md`.
The optional quality budget is zero by default; retaining raw EOS quality is required when
a caller explicitly permits a tiny endpoint adjustment. Public-data conditional inventory
comparison is available, but does not establish a universal experimental flow coefficient.

The local tests are `tests/test_release.py`; the actual native integration script is
`scripts/check_release_integration.py`. This request does not authorize changing other repos
or publishing from the current session.
