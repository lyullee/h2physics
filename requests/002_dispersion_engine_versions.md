# Compatible native dispersion provider versions

Status: actionable version and provider-boundary request.

Targets: PRISM, API581 engine, Process Risk Consequence Toolkit and SLAB-family packages.

## Observed conflict

The reviewed PRISM full extra requires SLABx 1.0.7 and SLABx-LH2 0.1.5. The reviewed
API581 optional native boundary requires SLABx 1.0.8 and SLABx-LH2 0.2.0. The consequence
toolkit dense option also requires SLABx 1.0.8. One interpreter cannot satisfy both exact
sets simultaneously. The host must not suppress dependency resolution or silently choose
an untested engine.

## Requested receiving changes

- Expose native provider injection with an explicit engine identity/version and supported
  source/observation domain. Keep engine installation optional.
- Choose and verify a shared compatible release set, or publish genuinely versioned
  provider entry points that can be selected explicitly.
- Preserve source-state, phase, pressure, temperature, energy and time-history semantics
  when changing an adapter; do not claim compatibility from matching argument names.
- Keep stable reproduction paths for older scientific results.

## Acceptance cases

1. Install the selected shared extras in a fresh native Python environment with no resolver conflict.
2. Execute the same qualified source case before/after the adapter change and compare conserved
   quantities and the declared concentration observation operator.
3. Verify finite-source termination and pool/jet handoffs without counting a terminal endpoint
   as another time interval.
4. Retain negative cases for unqualified phase partitions, unsupported source geometries and
   incompatible energy references.
5. Report package revisions, test commands, result differences and unchanged applicability limits.

The local `TimeSeries`, `PropertyBasis` and `MassPartition` are native adapter inputs;
receiving packages need not import this project to support equivalent structural contracts.

The current host now has a separately pinned actual DEGALI gas-plane/calm-jet path;
see NATIVE_JETS.md in docs and request 011 for its profile/flux/phase/clock work.
This narrower native composition does not resolve the full PRISM/SLAB version conflict,
qualify pool launch geometry or establish finite-source termination.
