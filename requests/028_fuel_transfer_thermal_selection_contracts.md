# Request 028 — fuel cell, finite transfer, thermal and selection contracts

The host repository now defines these source-only interfaces. Receiving
repositories remain unchanged and every new validation profile is unexecuted.

## Fuel-cell device level

Expose device-qualified polarization/activity, reactant utilization, crossover,
water phase/management and thermal boundary results while retaining explicit
H2/O2/H2O ports and the common formation-enthalpy reference. Return the original
result with a public producer verification hook. Do not hide compressor,
oxidant-conditioning, cooling or DC conversion behind a single efficiency.

Acceptance requires the `fuel-cell` and `fuel-cell-native` profiles, original
electrochemistry/thermochemical regressions and independent device observations.

## Refuelling/transfer owner

The finite-hydride source now accepts an optional same-clock, caller-supplied H2
mass-flow boundary with native stream enthalpy. It retains cumulative external
mass and enthalpy in its conservation trace; this is a storage-side port contract,
not a pressure-flow or station simulator.

The station simulator should expose accepted native steps for two finite endpoint
inventories, optional finite hose/line storage, exact clock/mode/port identity,
termination brackets and original failure prefixes. A standard protocol or
controller must remain a separately qualified model level with its source,
temperature/pressure limits and vehicle-tank applicability. Do not reinterpret
the host's caller schedule as SAE/ISO compliance.

Acceptance requires `finite-transfer`, the original tank/valve/nozzle/dynamic
network suites, installed native replay and source-qualified station data.

## Thermal utilities

Physical producers should expose original interval heat duties with temperature
level, direction, clock, reference and external-versus-internal boundary roles.
Utility supply, heat-recovery availability, COP, pinch constraints, losses and
prices are separate evidence-bearing inputs. A closed internal exchanger transfer
must not also receive external heating/rejection credit.

Acceptance requires `thermal-utilities`, the original producer/HX/device suites
and independent utility/process evidence for any availability or performance
claim.

## Application model registration

Applications may register exact `(family, level, provider)` factories through
the host model-selection contract. They should publish pinned revision,
capabilities and evidence IDs. Missing or failed preferred providers must remain
an error; no receiving registry may silently choose another physics level.

Acceptance requires `model-selection` plus each selected provider's own runtime,
license and scientific validation gates. Registry success alone is not model
qualification.
