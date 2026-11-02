"""Deferred actual-native compressor contracts; no calculation at import/discovery."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = (
        ("compressor-boundary-point", "validate_point", ("native source/PS/PH retained", "mass/enthalpy/shaft closure")),
        ("compressor-boundary-stale", "validate_stale", ("original result identity", "parameter/method stale rejection")),
        ("compressor-boundary-source", "validate_source", ("finite native source row/clock", "no implicit withdrawal")),
        ("compressor-boundary-prefix", "validate_prefix", ("failed native result retained", "completed serial prefix")),
    )
    return tuple(ValidationCase(identifier=name, profile="compressor-boundaries",
        entrypoint=__name__+":"+function, invariants=invariants) for name, function, invariants in definitions)


def _stage(**parameters):
    from examples.lh2dt_compressor import build_stage
    return build_stage(**parameters)


def validate_point(*, work_directory, **parameters):
    stage, direct, _ = _stage(**parameters)
    inlet = direct.state_pt(1e6, 300.)
    result = stage.evaluate(inlet, .01)
    result.require_current()
    assert result.native_component is stage.native
    assert result.native_provenance.package_sha256 == stage.native_provenance.package_sha256
    assert result.transfer.operating_point_admissible is None
    assert result.transfer.momentum_residual_pa is None
    assert result.source_boundary == "prescribed-steady-inlet-no-source-inventory"
    assert result.power.shaft_work_w > 0 and result.outlet.pressure_pa > inlet.pressure_pa
    assert abs(result.energy_residual_w) <= stage.tolerances.energy_limit_w(result.power.total_w)
    assert abs(result.outlet.enthalpy_identity_residual_j_kg) < .1
    ideal = direct.state_ps(result.outlet.pressure_pa, inlet.entropy_j_kg_k)
    assert abs(ideal.enthalpy_j_kg-result.isentropic_outlet.enthalpy_j_kg) < .1
    return ValidationOutcome(True, {"shaft_w": result.power.shaft_work_w,
        "energy_residual_w": result.energy_residual_w}, ("No machine map/electrical efficiency/finite withdrawal",))


def validate_stale(*, work_directory, **parameters):
    from dataclasses import replace
    stage, direct, _ = _stage(**parameters)
    inlet = direct.state_pt(1e6, 300.)
    first = stage.evaluate(inlet, .01)
    try:
        replace(first, mass_flow_kg_s=.02).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Copied compressor result acquired original provenance")
    stage.native.isentropic_efficiency = .6
    second = stage.evaluate(inlet, .01)
    second.require_current()
    assert second.power.shaft_work_w > first.power.shaft_work_w
    try:
        first.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed efficiency did not make the old point stale")
    evaluate = stage.native.evaluate
    stage.native.evaluate = lambda *args: evaluate(*args)
    try:
        try:
            second.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Native method rebinding was accepted")
    finally:
        del stage.native.evaluate
    second.require_current()
    provider = stage.bridge.native.provider
    backend = provider.backend
    provider.backend = "TTSE&HEOS"
    try:
        try:
            second.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Unqualified tabular provider was accepted as reference HEOS")
    finally:
        provider.backend = backend
    second.require_current()
    return ValidationOutcome(True, {"stale_rejections": 4}, ("Validity guard, not a tamper-proof security boundary",))


def validate_source(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.lh2dt_compressor import accepted_source
    stage, _, native = _stage(**parameters)
    source, simulator, rows = accepted_source(stage, native)
    before = (source.native_state.hydrogen_mass_kg, source.native_state.hydrogen_internal_energy_J)
    result = stage.evaluate(source.fluid, .01, finite_source=source)
    result.require_current()
    assert source.native_step is rows[-1] and simulator.network.boundaries
    assert source.native_step.states[source.node_id] is source.native_state
    assert result.finite_source is source and source.mass_kg > 0
    assert (source.native_state.hydrogen_mass_kg, source.native_state.hydrogen_internal_energy_J) == before
    assert source.time_s == source.local_time_origin_s+rows[-1].time_s
    try:
        replace(source, mass_kg=2*source.mass_kg).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Altered cached finite source was admitted")
    return ValidationOutcome(True, {"finite_source_kg": source.mass_kg, "source_time_s": source.time_s},
        ("One accepted snapshot only; source depletion/receiver coupling are external native responsibilities",))


def validate_prefix(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.lh2dt_compressor import (
        CompressionClosureError,
        CompressorBoundaryError,
        Lh2dtCompressionTrain,
        Lh2dtCompressorStage,
    )
    first, direct, native = _stage(**parameters)
    second = Lh2dtCompressorStage(native["compressor"].Compressor(first.bridge.native,
        pressure_ratio=3., isentropic_efficiency=.8), first.bridge, state_factory=first.state_factory,
        stage_id="second", envelope=replace(first.envelope, maximum_temperature_k=400.))
    train = Lh2dtCompressionTrain((first, second), train_id="authored-failure-prefix")
    try:
        train.evaluate(direct.state_pt(1e6, 300.), .01)
    except CompressorBoundaryError as error:
        assert isinstance(error.cause, CompressionClosureError)
        assert len(error.completed_stages) == 1 and error.native_result is not None
        assert error.completed_stages[0].native_component is first.native
        assert error.native_result.outlet.temperature_K > 400.
    else:
        raise AssertionError("Out-of-envelope serial discharge was accepted")
    return ValidationOutcome(True, {"retained_completed_stages": 1}, ("Synthetic envelope; not vendor qualification",))
