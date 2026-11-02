"""Deferred mutation contract for the shared finite source value object."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-source-immutable-lineage",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_source_integrity",
        invariants=(
            "finite source rate, mass, integration and window methods revalidate original bins",
            "post-construction writable-array mutation is detected before use",
            "nested state or source provenance mutation is detected before use",
            "same-value source copies do not impersonate the original issued object",
        ),
    ),)


def validate_source_integrity(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import SourceLocation
    from h2physics.sources import IntervalMassSource

    basis = PropertyBasis("hydrogen", "finite-source-integrity", "normal")
    state = ThermoState(basis, 101325., 25., 0.08, 450000., 320000., 12000., "gas")
    location = SourceLocation("leak", "source-integrity-clock", "global-xz",
                              (0., 0., 0.), (1., 0., 0.))
    source = IntervalMassSource(
        location, np.array([2., 3., 5.]), np.array([.2, .6]), state,
        Origin.MEASURED, "finite-source-integrity-observation", "isolation",
    )
    assert source.require_current() is source
    assert source.total_mass_kg == .8
    assert source.mass_between(2., 4., clock_id=location.clock_id) == .5
    copied = replace(source)
    assert copied.require_current() is copied
    assert copied is not source

    original_first = float(source.mass_kg[0])
    source.mass_kg.setflags(write=True)
    source.mass_kg[0] = original_first + .1
    try:
        source.rate_at(2.5, clock_id=location.clock_id)
    except ValueError:
        pass
    else:
        raise AssertionError("Finite source accepted changed mass bins")
    finally:
        source.mass_kg[0] = original_first
        source.mass_kg.setflags(write=False)

    original_enthalpy = state.enthalpy_j_kg
    object.__setattr__(state, "enthalpy_j_kg", original_enthalpy + 10.)
    try:
        source.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Finite source accepted changed nested thermodynamic state")
    finally:
        object.__setattr__(state, "enthalpy_j_kg", original_enthalpy)

    original_evidence = source.evidence_id
    object.__setattr__(source, "evidence_id", "changed-evidence")
    try:
        _ = source.total_mass_kg
    except ValueError:
        pass
    else:
        raise AssertionError("Finite source accepted changed evidence provenance")
    finally:
        object.__setattr__(source, "evidence_id", original_evidence)

    return ValidationOutcome(
        True,
        {"mass_bins": len(source.mass_kg), "mutation_domains_rejected": 3},
        ("Synthetic object-integrity contract only; no source experiment or physical model ran.",),
    )
