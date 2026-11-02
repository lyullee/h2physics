# HyRAM+ hydrogen ignition probability adapter

## Scope

`h2physics.adapters.hyram_ignition` is a typed Python seam into the optional
HyRAM+ QRA probability lookup. It reuses the installed native implementation;
this project contains no copied lookup values or duplicate probability law.
HyRAM+ exposes the lookup as release mass flow in kg/s plus a table of flow
boundaries and corresponding immediate and delayed probabilities. The adapter
accepts an evidence-bound table or captures the default hydrogen table from the
installed package, then calls the native rate-bin function directly.

The result holds two absolute release-relative branch probabilities:

- `immediate_probability`: immediate ignition relative to the leak/release;
- `delayed_probability`: delayed ignition relative to the leak/release;
- `total_probability`: their sum, checked not to exceed one.

The delayed probability is not conditioned on immediate ignition not occurring.
If a downstream event tree requires conditional branches, make that conversion
explicit in that event-tree owner. This adapter does not calculate leak rates,
incident frequencies, detection/isolation credit, event consequences, harm,
or facility risk. It does not infer the release rate from a tank, opening or
source history.

## API

```python
from h2physics.adapters import (
    evaluate_hyram_ignition_probability,
    hyram_default_hydrogen_ignition_table,
)

table = hyram_default_hydrogen_ignition_table()
result = evaluate_hyram_ignition_probability(0.02, table=table)
print(result.immediate_probability, result.delayed_probability)
print(result.hyram_version, result.native_module_sha256)
```

The rate is in kg/s. The default table is captured from the exact installed
HyRAM+ distribution at call time. The returned table content SHA-256 and the
result's package version/native kernel source SHA-256 help reproduce that
selection. For a study-specific parameterization, construct
`HyRAMIgnitionTable` with explicit increasing thresholds, one probability per
resulting interval, a stable table ID and evidence ID. The adapter rejects
non-finite or negative rates/thresholds, invalid probabilities, non-increasing
thresholds and branch sums above one. HyRAM+ owns threshold-edge selection.

HyRAM+ is an optional separately installed GPL-3.0-only dependency and is not
added to this project's dependency metadata or bundled distribution. The adapter
imports it only when called, but that call loads HyRAM+ into the same Python
process. This project is Apache-2.0; any combined installation or redistribution
needs a separate license-compatibility review. No compatibility or release
clearance is asserted here. Package version or Python API changes can break
this seam; installation and native API execution must be verified on Hangang
before release. This implementation is marked `implemented_unverified` until
that run completes.

## Evidence and limits

The official HyRAM+ technical reference describes QRA model inputs and the
immediate/delayed ignition branch basis. The current code's Python package
documents `hyram.qra.ignition_probs.get_ignition_probability()` and the
custom-table input used by the full QRA analysis. Those sources define the
native engine behavior; they do not establish that its default table is
appropriate for every facility, release class or jurisdiction.

The adapter does not expose uncertainty distributions because the native
lookup returns point probabilities. Analysts must separately document the
provenance, applicability range and uncertainty of a chosen table. It must not
be interpreted as a spontaneous-ignition physics model or a facility-specific
ignition prediction.

References:

- Sandia National Laboratories, [HyRAM+](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/) project and documentation page.
- Sandia National Laboratories, [HyRAM+ source repository](https://github.com/sandialabs/hyram), GPL-3.0-only; see `src/hyram/qra/analysis.py` and `src/hyram/qra/ignition_probs.py` in the separately installed dependency.
- Ehrhart et al., *Hydrogen Plus Other Alternative Fuels Risk Assessment Models (HyRAM+) Version 6.0 Technical Reference Manual*, SAND2025-04942 (2025), listed on the [official project documentation page](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/).

## Validation status

`hyram-hydrogen-ignition-probability-native-contract` is a deferred Hangang
case. It checks custom threshold routing, exact-edge behavior, release-relative
branch sums, provider identity and capture of the installed hydrogen default
table. Passing it will verify adapter/API execution only. It does not validate
the empirical or expert-judgment basis of the probabilities or qualify an
installation's risk.
