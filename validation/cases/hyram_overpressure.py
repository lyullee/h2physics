"""Deferred issuer/currentness contract for standalone native Bauwens results."""

import dataclasses

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hyram-bauwens-result-issuer",
        profile="hyram-overpressure",
        entrypoint=__name__ + ":validate_result_issuer",
        invariants=(
            "only a native Bauwens evaluation issues a peak-pressure receipt",
            "only a converged native root plus forward evaluation issues a threshold receipt",
            "direct construction, cloning, and post-issuance mutation are rejected",
        ),
    ), ValidationCase(
        identifier="hyram-bauwens-native-exposure-handoff",
        profile="hyram-overpressure",
        entrypoint=__name__ + ":validate_exposure_handoff",
        invariants=("owner-issued native peak remains current",
                    "absolute ambient pressure is never relabeled as gauge pressure",
                    "caller support and source-energy evidence are retained; no impulse inferred"),
    ))


def validate_exposure_handoff(*, work_directory, **parameters):
    import sys
    from pathlib import Path

    del work_directory
    native_packages = parameters.get("native_packages")
    if native_packages is not None:
        sys.path.insert(0, str(Path(native_packages).resolve()))
    from hyram.phys import Bauwens_method
    from h2physics.adapters.hyram_exposure import pressure_peak_from_hyram_overpressure
    from h2physics.adapters.hyram_overpressure import (
        BauwensCorrelationDomain, DetonableHydrogenEnergy, HyRAMBauwensOverpressure,
        OverpressureEnvironment, OverpressureEvent)
    from h2physics.core import Origin

    domain = BauwensCorrelationDomain(.01, 100., 8e4, 1.2e5, .1,
                                      "hangang-declared-bauwens-domain")
    model = HyRAMBauwensOverpressure(Bauwens_method, domain=domain,
                                     native_source_id="installed-HyRAM-Bauwens")
    energy = DetonableHydrogenEnergy(.01, 120e6, "caller-participating-mass",
        "caller-combustion-heat", "caller-combustion-basis", "caller-source-id", Origin.SYNTHETIC)
    event = OverpressureEvent("caller-event", (0., 0., 0.), "global-xyz-z-up",
                              "caller-event-centre", 10., "caller-absolute-clock")
    environment = OverpressureEnvironment(101325., "caller-ambient-pressure")
    native = model.evaluate(energy, event, environment, ((20., 0., 0.),), frame_id=event.frame_id)
    peak = pressure_peak_from_hyram_overpressure(native, receptor_index=0,
        support_s=(9., 11.), receptor_id="hangang-bauwens-receiver",
        basis_id="native-incident-gauge-pressure-rise-no-waveform")
    assert peak.overpressure_pa == native.peak_overpressure_pa[0]
    assert peak.receptor.position_m == tuple(native.receptors_m[0])
    assert peak.clock_id == event.clock_id and peak.support_s == (9., 11.)
    assert peak.positive_impulse_pa_s is None
    assert "caller-event-centre" in peak.input_evidence_ids
    assert peak.input_evidence_ids[-1] == domain.evidence_id
    return ValidationOutcome(True, {"native_peak_pressure_pa": peak.overpressure_pa,
        "impulse_inferred": peak.positive_impulse_pa_s is not None,
        "input_evidence_count": len(peak.input_evidence_ids)},
        ("Static conditional peak only; caller timing context does not define a waveform or arrival time.",))


def validate_result_issuer(*, work_directory, **parameters):
    del work_directory, parameters
    from hyram.phys import Bauwens_method

    from h2physics.adapters.hyram_overpressure import (
        BauwensCorrelationDomain,
        BauwensPeakResult,
        BauwensThresholdResult,
        DetonableHydrogenEnergy,
        HyRAMBauwensOverpressure,
        OverpressureEnvironment,
        OverpressureEvent,
    )
    from h2physics.core import Origin

    domain = BauwensCorrelationDomain(.01, 100., 8e4, 1.2e5, .1,
                                      "synthetic-declared-domain")
    model = HyRAMBauwensOverpressure(Bauwens_method, domain=domain,
                                     native_source_id="installed-HyRAM-Bauwens")
    energy = DetonableHydrogenEnergy(.01, 120e6, "synthetic-mass", "synthetic-heat",
                                     "synthetic-basis", "synthetic-participating-fuel",
                                     Origin.SYNTHETIC)
    event = OverpressureEvent("synthetic-event", (0., 0., 0.), "local-frame",
                              "synthetic-centre", 0., "synthetic-clock")
    environment = OverpressureEnvironment(101325., "synthetic-ambient")
    peak = model.evaluate(energy, event, environment, ((20., 0., 0.),), frame_id="local-frame")
    peak.require_current()
    target = float(peak.peak_overpressure_pa[0])
    threshold = model.threshold_radius(target, energy, event, environment)
    threshold.require_current()

    for result, result_type in ((peak, BauwensPeakResult),
                                (threshold, BauwensThresholdResult)):
        try:
            dataclasses.replace(result)
        except ValueError:
            pass
        else:
            raise AssertionError(f"caller clone accepted for {result_type.__name__}")
    changed = peak.peak_overpressure_pa.copy()
    object.__setattr__(peak, "peak_overpressure_pa", changed + 1.)
    try:
        peak.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("mutated Bauwens peak receipt remained current")

    return ValidationOutcome(True, {
        "native_peak_pressure_pa": target,
        "native_threshold_radius_m": threshold.radius_m,
        "peak_and_threshold_require_current": True,
        "clone_and_mutation_rejected": True,
    }, ("Synthetic inputs; conditional correlation only; no safety distance claim",))
