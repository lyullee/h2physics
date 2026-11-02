"""Deferred cumulative source and whole-facility ledger contracts."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "FiniteFacilitySource ledger history is implemented_unverified.",
    "The handler uses an authored native process case, not measured facility data.",
    "Source-plane enthalpy is a caller-declared fixed-state projection; its residual is diagnostic.",
    "Accepted-sample quadrature is not the native RK-stage integral or a refinement qualification.",
    "The cumulative receipt is bound to its original source/run and rejects stale or changed arrays.",
)


def cases():
    return (
        ValidationCase(
            identifier="facility-source-cumulative-ledger",
            profile="facility-protection",
            entrypoint=__name__ + ":validate_cumulative_ledger",
            invariants=(
                "cumulative source bins reconcile with the bound finite window",
                "summed stored-mass change closes against summed native external boundary mass at every accepted sample",
                "whole-system stored-energy change closes against native boundary energy at every accepted sample",
                "native boundary energy separates into transported enthalpy and ambient heat",
                "source outlet enthalpy and fixed-state projection remain separate cumulative ledgers with explicit residual",
                "all ledger histories share one immutable absolute time axis",
            ),
        ),
    )


def validate_cumulative_ledger(*, work_directory, **parameters):
    from examples.facility_protection import make_case

    del work_directory, parameters
    binding = make_case()["source"]
    binding.require_current()
    ledger = binding.ledger_history()
    mass_scale = np.maximum(
        np.abs(ledger.inventory_mass_change_kg), np.abs(ledger.native_boundary_mass_kg)
    )
    mass_limit = np.maximum(binding.tolerances.mass_absolute_kg,
                             binding.tolerances.relative * mass_scale)
    energy_scale = np.maximum.reduce((
        np.abs(ledger.inventory_energy_change_j),
        np.abs(ledger.native_boundary_energy_j),
        np.abs(ledger.transported_enthalpy_j),
        np.abs(ledger.ambient_heat_j),
    ))
    energy_limit = np.maximum(binding.tolerances.energy_absolute_j,
                               binding.tolerances.relative * energy_scale)
    if np.any(np.abs(ledger.mass_residual_kg) > mass_limit):
        raise AssertionError("Whole finite-system mass history does not close")
    if np.any(np.abs(ledger.energy_residual_j) > energy_limit):
        raise AssertionError("Whole finite-system stored energy does not close")
    if np.any(np.abs(ledger.boundary_energy_partition_residual_j) > energy_limit):
        raise AssertionError("Native boundary energy does not split into transport and heat")
    if not np.allclose(
        ledger.other_net_boundary_mass_kg,
        ledger.native_boundary_mass_kg + ledger.source_mass_kg,
        rtol=1e-12,
        atol=binding.tolerances.mass_absolute_kg,
    ):
        raise AssertionError("Residual external mass ledger is inconsistent")
    if abs(ledger.other_net_boundary_mass_kg[-1]
           - binding.other_net_boundary_mass_kg) > binding.tolerances.mass_absolute_kg:
        raise AssertionError("Final residual external mass differs from its declared reconciliation")
    if abs(ledger.source_mass_kg[-1] - binding.source.total_mass_kg) > binding.tolerances.mass_absolute_kg:
        raise AssertionError("Cumulative source bins differ from the bound finite source")
    projection = binding.energy_projection()
    if abs(ledger.native_source_enthalpy_j[-1] - sum(projection.native_transport_enthalpy_j)) > (
        binding.tolerances.energy_absolute_j
    ):
        raise AssertionError("Cumulative source enthalpy differs from its accepted interval integrals")
    histories = (
        ledger.source_mass_kg,
        ledger.inventory_mass_change_kg,
        ledger.native_boundary_mass_kg,
        ledger.other_net_boundary_mass_kg,
        ledger.inventory_energy_change_j,
        ledger.native_boundary_energy_j,
        ledger.transported_enthalpy_j,
        ledger.ambient_heat_j,
        ledger.mass_residual_kg,
        ledger.energy_residual_j,
        ledger.boundary_energy_partition_residual_j,
        ledger.native_source_enthalpy_j,
        ledger.projected_source_enthalpy_j,
        ledger.source_enthalpy_projection_residual_j,
    )
    if any(values.flags.writeable or values.shape != ledger.time_s.shape for values in histories):
        raise AssertionError("Ledger arrays must share one immutable accepted-time axis")
    ledger.require_current()
    forged = type(ledger)(
        ledger.source_sha256, ledger.component_id, ledger.clock_id,
        ledger.state_projection_evidence_id, ledger.time_s,
        ledger.source_mass_kg + 1.0, ledger.inventory_mass_change_kg,
        ledger.native_boundary_mass_kg, ledger.other_net_boundary_mass_kg + 1.0,
        ledger.inventory_energy_change_j, ledger.native_boundary_energy_j,
        ledger.transported_enthalpy_j, ledger.ambient_heat_j,
        ledger.native_source_enthalpy_j, ledger.projected_source_enthalpy_j,
    )
    try:
        forged.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A forged cumulative history was accepted")
    saved = ledger.source_mass_kg.copy()
    ledger.source_mass_kg.setflags(write=True)
    ledger.source_mass_kg[1] += 1.0
    try:
        ledger.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A mutated cumulative receipt was accepted")
    finally:
        ledger.source_mass_kg[:] = saved
        ledger.source_mass_kg.setflags(write=False)
    return ValidationOutcome(
        True,
        {
            "accepted_samples": int(ledger.time_s.size),
            "source_mass_kg": float(ledger.source_mass_kg[-1]),
            "other_net_boundary_mass_kg": float(ledger.other_net_boundary_mass_kg[-1]),
            "total_mass_residual_kg": float(ledger.mass_residual_kg[-1]),
            "total_energy_residual_j": float(ledger.energy_residual_j[-1]),
            "boundary_energy_partition_residual_j": float(
                ledger.boundary_energy_partition_residual_j[-1]
            ),
            "source_enthalpy_projection_residual_j": float(
                ledger.source_enthalpy_projection_residual_j[-1]
            ),
        },
        LIMITS,
    )
