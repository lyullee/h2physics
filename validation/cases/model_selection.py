"""Deferred exact model-selection cases; discovery returns metadata only."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = (
        ("selection-exact", "validate_exact", ("exact family/level/provider", "original factory result")),
        ("selection-no-fallback", "validate_no_fallback", ("missing exact provider fails", "no alternative call")),
        ("selection-gates", "validate_gates", ("status/capability/evidence explicit",)),
        ("selection-duplicate", "validate_duplicate", ("one exact binding", "unknown/planned family rejected")),
        ("selection-stale", "validate_stale", ("factory callable identity", "selection retains binding")),
        ("selection-preferred-dispersion", "validate_preferred_dispersion",
         ("high-pressure gas selects hyram", "LH2-origin release selects slabx-lh2",
          "exact preferred provider is registered and no cross-origin fallback occurs",
          "scenario input keys cannot be changed through the source mapping",
          "scenario solver options are copied and read-only after construction",
          "provider acceptance policy rejects non-bool truthy/falsy values at admission",
          "direct HyRAM/SLABx run and projection APIs reject non-bool acceptance flags before native access",
          "execution receipt acceptance and evidence match the retained provider result",
          "direct or dataclass-replaced executions cannot claim selected-provider run provenance",
          "HyRAM callable inputs forward only on the gas route",
          "SLABx boundary, width context, runner, premise and output forward on the LH2 route",
          "LH2 quasi-steady snapshots preserve parent-bin time/mass while explicitly excluding plume memory",
          "per-bin footprints and caller-projected thermodynamic states remain aligned with active source bins",
          "a failed LH2 snapshot retains completed-bin results, failing native result and original bin index",
          "snapshot receipt rejects changed parent mass arrays and native trajectory data",
          "snapshot receipt rejects a native bin whose absolute clock window is shifted",
          "typed source-bin ledger preserves exact windows, zero-mass slots, rate and run identity",
          "source-bin ledger freshness is tied to the original finite source and does not imply plume memory",
          "callback-side source mutation is rejected before a SLAB run receipt is sealed",
          "requested/constructed/final native rate, duration, area, temperature and mass are separately audited")),
        ("slabx-lh2-run-issuer", "validate_slabx_run_issuer",
         ("caller-created SLABLH2Run receipts cannot claim native execution provenance",)),
        ("cluster-setup-script-pin", "validate_cluster_setup_pin",
         ("setup script digest is mandatory and validated", "generated PBS worker checks the pinned digest before and after sourcing",
          "environment setup is loaded only between the two digest checks", "script generation never submits a scheduler job")),
        ("pem-eis-ohmic-stack-bridge", "validate_pem_ohmic_bridge",
         ("measured/reconstructed whole-sweep FitResult must include source real and imaginary points",
          "caller-ordered multi-sweep fit fingerprint and row sequence match concatenated PEM observations",
          "multi-sweep operating context is selected explicitly and all fit/DC provenance is retained",
          "active cell area maps fitted resistance to area resistance with units",
          "DC context, source member, experiment group, fit and interpretation identities are retained",
          "caller-owned temperature adjustment is optional and provenance guarded",
          "loss-map composition rejects component replacement and possible ohmic double counting",
          "invalid, unrelated or incomplete fit/source bindings are rejected",
          "bridge feeds the existing OhmicLoss without adding a new stack model")),
        ("research-fit-robust-loss", "validate_robust_fit_loss",
         ("linear loss remains the default and is recorded explicitly",
          "caller-selected robust loss and positive transition scale are retained in FitResult",
          "robust fitting reduces sensitivity to a declared synthetic gross outlier",
          "response-unit RMSE remains distinct from robust optimizer cost",
          "unsupported loss and nonpositive transition scale are rejected")),
    )
    return tuple(ValidationCase(identifier=name, profile="model-selection",
        entrypoint=__name__+":"+entry, parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)


def _binding(factory, **changes):
    from h2physics.model_selection import ProviderBinding

    values = dict(family_id="dispersion.outdoor", level_id="high-pressure-gas-jet",
                  provider_id="HyRAM+", status="native_adapter_verified", revision="fixture-r1",
                  capabilities={"high-pressure-gas", "native-dispersion"},
                  evidence_ids={"dependency-receipt", "domain-evidence"}, factory=factory)
    values.update(changes)
    return ProviderBinding.bind(**values)


def _request(**changes):
    from h2physics.model_selection import ModelRequest

    values = dict(family_id="dispersion.outdoor", level_id="high-pressure-gas-jet",
                  provider_id="HyRAM+", accepted_statuses={"native_adapter_verified"},
                  required_capabilities={"high-pressure-gas"},
                  required_evidence_ids={"dependency-receipt"})
    values.update(changes)
    return ModelRequest(**values)


def validate_slabx_run_issuer(*, work_directory, **parameters):
    from h2physics.adapters.slabx_lh2 import SLABLH2Run

    try:
        SLABLH2Run(
            native=object(), used_source=object(), boundary=object(),
            atmosphere=object(), premise={}, source_mass_residual_kg=0.0,
            source_area_change_m2=0.0, boundary_audit=object(),
            source_tolerances=object(), accepted=False,
        )
    except ValueError:
        return ValidationOutcome(True, {"forged_run_rejected": True}, ())
    raise AssertionError("A caller-created run receipt claimed native SLABx-LH2 execution")


def validate_exact(*, work_directory, **parameters):
    from h2physics.model_selection import ModelRegistry

    marker = object()
    calls = []
    def factory():
        calls.append(marker)
        return marker
    registry = ModelRegistry()
    binding = registry.register(_binding(factory))
    selection = registry.select(_request())
    built = selection.build()
    assert selection.binding is binding and built.model is marker and calls == [marker]
    assert built.require_current() is built
    return ValidationOutcome(True, {"factory_calls": len(calls)}, ("Authored registry only.",))


def validate_no_fallback(*, work_directory, **parameters):
    from h2physics.model_selection import ModelRegistry

    calls = []
    registry = ModelRegistry()
    registry.register(_binding(lambda: calls.append("preferred")))
    try:
        registry.select(_request(provider_id="DEGALI-comparison"))
    except LookupError as error:
        assert "no fallback" in str(error)
    else:
        raise AssertionError("A missing exact provider silently selected an alternative")
    assert not calls
    return ValidationOutcome(True, {"alternative_calls": len(calls)}, ("Metadata selection only.",))


def validate_gates(*, work_directory, **parameters):
    from h2physics.model_selection import ModelRegistry

    registry = ModelRegistry()
    registry.register(_binding(lambda: None))
    rejected = 0
    for request in (
        _request(accepted_statuses={"implemented_unverified"}),
        _request(required_capabilities={"liquid-origin"}),
        _request(required_evidence_ids={"missing-evidence"}),
    ):
        try:
            registry.select(request)
        except ValueError:
            rejected += 1
    assert rejected == 3
    return ValidationOutcome(True, {"rejected_gates": rejected}, ("Tags are declared evidence, not validation.",))


def validate_duplicate(*, work_directory, **parameters):
    from h2physics.model_selection import ModelRegistry

    registry = ModelRegistry()
    binding = _binding(lambda: None)
    registry.register(binding)
    rejected = 0
    for candidate in (
        binding,
        _binding(lambda: None, family_id="missing.family"),
        _binding(lambda: None, family_id="combustion.jet_fire"),
    ):
        try:
            registry.register(candidate)
        except (ValueError, KeyError):
            rejected += 1
    assert rejected == 3
    return ValidationOutcome(True, {"rejected_registrations": rejected}, ("No global registry.",))


def validate_stale(*, work_directory, **parameters):
    from h2physics.model_selection import ModelRegistry

    registry = ModelRegistry()
    binding = registry.register(_binding(lambda: None))
    selection = registry.select(_request())
    object.__setattr__(binding, "factory", lambda: "changed")
    try:
        selection.require_current()
    except ValueError:
        return ValidationOutcome(True, {"stale_factory_rejected": True},
                                 ("Callable closure/private state is provider-owned.",))
    raise AssertionError("Changed factory identity remained admissible")


def validate_preferred_dispersion(*, work_directory, **parameters):
    from unittest.mock import patch

    from h2physics.dispersion import (
        DispersionExecution,
        DispersionExecutionError,
        DispersionScenario,
        HydrogenReleaseFamily,
        preferred_dispersion_provider,
        run_preferred_gas_dispersion,
        run_preferred_lh2_dispersion,
        run_preferred_lh2_quasi_steady_slices,
    )
    from h2physics.model_selection import ModelRegistry, ModelRequest, ProviderBinding

    assert preferred_dispersion_provider(HydrogenReleaseFamily.HIGH_PRESSURE_GAS) == "hyram"
    assert (
        preferred_dispersion_provider(HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN)
        == "slabx-lh2"
    )
    gas_calls = []

    class GasRun:
        def __init__(self, inputs):
            self.inputs = inputs
            self.evidence_id = inputs["evidence_id"]
            self.accepted = True

    def marker_gas_route(family, *, fluid_factory, orifice_factory, jet_factory,
                         upstream, ambient, opening, location, evidence_id,
                         solver_options, require_accepted=True):
        call = locals().copy()
        call.pop("family")
        call.pop("require_accepted")
        gas_calls.append(call)
        return GasRun(call)

    caller_solver_options = {"Smax": 10.}
    forwarded = dict(
        fluid_factory=object(),
        orifice_factory=object(),
        jet_factory=object(),
        upstream=object(),
        ambient=object(),
        opening=object(),
        location=object(),
        evidence_id="source-evidence",
        solver_options=caller_solver_options,
    )
    original_inputs = dict(forwarded)
    original_inputs["solver_options"] = dict(caller_solver_options)
    gas_scenario = DispersionScenario(HydrogenReleaseFamily.HIGH_PRESSURE_GAS, forwarded)
    rejected_acceptance_flags = 0
    for invalid_flag in (0, 1, "false", None):
        try:
            DispersionScenario(
                HydrogenReleaseFamily.HIGH_PRESSURE_GAS,
                {**original_inputs, "require_accepted": invalid_flag},
            )
        except (TypeError, ValueError):
            rejected_acceptance_flags += 1
    assert rejected_acceptance_flags == 4
    direct_acceptance_calls = (
        lambda: run_preferred_gas_dispersion(
            HydrogenReleaseFamily.HIGH_PRESSURE_GAS,
            fluid_factory=None, orifice_factory=None, jet_factory=None,
            upstream=None, ambient=None, opening=None, location=None,
            evidence_id="unreachable", solver_options={}, require_accepted=0),
        lambda: run_preferred_lh2_dispersion(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
            source=None, native_pool_factory=None, substance=None, area_m2=1.,
            footprint_evidence_id="unreachable", ambient_pressure_pa=1., atmosphere=None,
            emission_thermo=None, water_thermo=None, runner=None, premise_check=None,
            width_context=None, width_coupling=False, x_max_m=1., require_accepted="false"),
        lambda: run_preferred_lh2_quasi_steady_slices(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
            source=None, native_pool_factory=None, substance=None, area_m2=1.,
            footprint_evidence_id="unreachable", ambient_pressure_pa=1., atmosphere=None,
            emission_thermo=None, water_thermo=None, runner=None, premise_check=None,
            width_context=None, width_coupling=False, x_max_m=1., require_accepted=None),
    )
    rejected_direct_acceptance_flags = 0
    for invoke in direct_acceptance_calls:
        try:
            invoke()
        except TypeError:
            rejected_direct_acceptance_flags += 1
    assert rejected_direct_acceptance_flags == len(direct_acceptance_calls)
    from h2physics.adapters.hyram import run_hyram_gas_jet
    from h2physics.adapters.hyram_flame import HyRAMFlameRun, run_hyram_flame
    from h2physics.adapters.hyram_jet_source import project_hyram_jet_to_finite_source
    from h2physics.adapters.slabx_lh2 import run_slabx_lh2, run_slabx_lh2_quasi_steady_slices

    direct_native_acceptance_calls = (
        lambda: run_hyram_gas_jet(
            fluid_factory=None, orifice_factory=None, jet_factory=None,
            upstream=None, ambient=None, opening=None, location=None,
            evidence_id="unreachable", solver_options={}, require_accepted=0),
        lambda: run_hyram_flame(
            fluid_factory=None, orifice_factory=None, flame_factory=None,
            transmissivity_function=None, upstream=None, ambient=None, opening=None,
            location=None, window=None, solver_options={}, require_accepted="false"),
        lambda: project_hyram_jet_to_finite_source(
            None, start_s=0., end_s=1., clock_id="unreachable", source_state=None,
            source_state_evidence_id="unreachable", origin="synthetic", require_accepted=1),
        lambda: run_slabx_lh2(
            boundary=None, atmosphere=None, emission_thermo=None, water_thermo=None,
            runner=None, premise_check=None, width_context=None, width_coupling=False,
            x_max_m=1., require_accepted=0),
        lambda: run_slabx_lh2_quasi_steady_slices(
            source=None, native_pool_factory=None, substance=None, area_m2=1.,
            footprint_evidence_id="unreachable", ambient_pressure_pa=1., atmosphere=None,
            emission_thermo=None, water_thermo=None, runner=None, premise_check=None,
            width_context=None, width_coupling=False, x_max_m=1., require_accepted=None),
        lambda: HyRAMFlameRun.irradiance(
            object.__new__(HyRAMFlameRun), None, relative_humidity=.5,
            minimum_source_distance_m=1., allow_rejected_flame=1),
        lambda: HyRAMFlameRun.irradiance(
            object.__new__(HyRAMFlameRun), None, relative_humidity=.5,
            minimum_source_distance_m=1., require_kernel_accepted="false"),
    )
    rejected_native_acceptance_flags = 0
    for invoke in direct_native_acceptance_calls:
        try:
            invoke()
        except TypeError:
            rejected_native_acceptance_flags += 1
    assert rejected_native_acceptance_flags == len(direct_native_acceptance_calls)
    caller_solver_options["Smax"] = 20.
    forwarded.clear()
    assert gas_scenario.provider_id == "hyram"
    assert dict(gas_scenario.inputs) == original_inputs
    assert gas_scenario.inputs["solver_options"] == {"Smax": 10.}
    try:
        gas_scenario.inputs["solver_options"]["Smax"] = 30.
    except TypeError:
        pass
    else:
        raise AssertionError("Scenario-owned solver options remained mutable")
    with patch("h2physics.dispersion.run_preferred_gas_dispersion",
               side_effect=marker_gas_route):
        gas_execution = gas_scenario.run()
    assert gas_execution.result.inputs == original_inputs
    assert gas_execution.family is HydrogenReleaseFamily.HIGH_PRESSURE_GAS
    assert gas_execution.provider_id == "hyram"
    assert gas_execution.source_evidence_ids == ("source-evidence",)
    assert gas_execution.accepted is True
    gas_execution.require_current()
    captured_gas_inputs = dict(gas_execution.result.inputs)
    gas_execution.result.inputs["evidence_id"] = "changed-evidence"
    try:
        gas_execution.require_current()
    except ValueError as error:
        assert "changed after capture" in str(error)
    else:
        raise AssertionError("Changed provider result remained covered by its receipt")
    gas_execution.result.inputs.clear()
    gas_execution.result.inputs.update(captured_gas_inputs)
    gas_execution.require_current()
    try:
        DispersionScenario(
            HydrogenReleaseFamily.HIGH_PRESSURE_GAS,
            {**original_inputs, "extra": "different"},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A gas scenario admitted a provider-unknown input")
    assert len(gas_calls) == 1
    try:
        DispersionExecution(
            gas_execution.family, gas_execution.provider_id, gas_execution.result,
            gas_execution.source_evidence_ids, False,
        )
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A receipt accepted flag inconsistent with its result was admitted")
    try:
        DispersionExecution(
            gas_execution.family, gas_execution.provider_id, gas_execution.result,
            gas_execution.source_evidence_ids, True,
        )
    except TypeError:
        pass
    else:
        raise AssertionError("A caller-created receipt claimed an actual provider run")
    from dataclasses import replace
    try:
        replace(gas_execution)
    except TypeError:
        pass
    else:
        raise AssertionError("A copied execution receipt retained its one-use run provenance")
    for invalid_evidence in (
        "source-evidence",
        ("source-evidence", "source-evidence"),
        ("different-evidence",),
    ):
        try:
            DispersionExecution(
                gas_execution.family, gas_execution.provider_id, gas_execution.result,
                invalid_evidence, True,
            )
        except (TypeError, ValueError):
            continue
        raise AssertionError("Malformed or duplicate provider evidence was admitted")

    slab_calls = []
    marker = object()

    class State:
        basis = type("Basis", (), {"fluid": "Hydrogen", "spin_composition": "normal"})()
        vapor_mass_fraction = 1.
        pressure_pa = 101325.
        temperature_k = 300.

    class Location:
        direction_unit = (0., 0., 1.)
        position_m = (0., 0., 0.)

    class Source:
        state = State()
        location = Location()
        edges_s = (0., 10.)
        evidence_id = "vapor-source-evidence"

        @property
        def mean_rates_kg_s(self):
            return (0.1,)

        @property
        def total_mass_kg(self):
            return 1.

    class NativeSubstance:
        mw = 0.00201588

    class NativeSource:
        substance = NativeSubstance()
        rate = 0.1
        area = 1.0
        duration = 10.0
        T = 300.0

    class Atmosphere:
        p = 101325.

    class Thermo:
        substance = NativeSubstance()

    class UsedSource:
        rate = 0.1
        duration = 10.
        area = 1.
        T = 300.

    class Trajectory:
        def __init__(self):
            self.x = [0., 10.]

    native_source = NativeSource()

    def pool_factory(**kwargs):
        slab_calls.append(("pool", kwargs))
        return native_source

    def runner(source, atmosphere, emission, water, *, x_max, **options):
        slab_calls.append(("runner", source, atmosphere, emission, water, x_max, options))
        return Trajectory(), UsedSource()

    from contextlib import nullcontext

    def premise_check(trajectory):
        slab_calls.append(("premise", trajectory))
        return {"max": 0.5, "violated": False}

    def width_context(enabled):
        slab_calls.append(("width", enabled))
        return nullcontext()

    slab_parameters = dict(
        source=Source(),
        native_pool_factory=pool_factory,
        substance=NativeSubstance(),
        area_m2=1.,
        footprint_evidence_id="footprint-evidence",
        ambient_pressure_pa=101325.,
        atmosphere=Atmosphere(),
        emission_thermo=Thermo(),
        water_thermo=Thermo(),
        runner=runner,
        premise_check=premise_check,
        width_context=width_context,
        width_coupling=False,
        x_max_m=100.,
    )
    lh2_scenario = DispersionScenario(
        HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN, slab_parameters
    )
    assert lh2_scenario.provider_id == "slabx-lh2"
    lh2_execution = lh2_scenario.run()
    lh2_result = lh2_execution.result
    from dataclasses import replace as dataclass_replace

    try:
        dataclass_replace(lh2_result)
    except ValueError:
        pass
    else:
        raise AssertionError("A cloned SLAB run receipt retained native issuance")
    assert lh2_result.native is Trajectory or isinstance(lh2_result.native, Trajectory)
    assert lh2_result.accepted
    assert lh2_execution.provider_id == "slabx-lh2"
    assert lh2_execution.accepted is True
    assert lh2_execution.source_evidence_ids == (
        "vapor-source-evidence", "footprint-evidence"
    )
    assert lh2_result.boundary_audit.used_temperature_change_k == 0.0
    assert lh2_result.boundary_audit.used_rate_change_kg_s == 0.0
    assert lh2_result.boundary_audit.used_duration_change_s == 0.0
    assert [entry[0] for entry in slab_calls] == ["pool", "width", "runner", "premise"]
    assert slab_calls[1][1] is False
    assert slab_calls[2][1] is native_source
    assert slab_calls[2][5] == 100.
    assert lh2_result.source_mass_residual_kg == 0.
    from math import log

    from h2physics.adapters.slabx_lh2 import run_slabx_lh2, steady_vapor_pool_boundary
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import SourceLocation
    from h2physics.sources import IntervalMassSource

    vapor_basis = PropertyBasis("Hydrogen", "synthetic-ideal-vapor-contract", "normal")

    def synthetic_vapor_state(temperature_k):
        gas_constant = 8.314462618 / .00201588
        heat_capacity = 14300.0
        enthalpy = heat_capacity * temperature_k
        return ThermoState(
            vapor_basis, 101325.0, temperature_k,
            101325.0 / (gas_constant * temperature_k),
            enthalpy, enthalpy - gas_constant * temperature_k,
            heat_capacity * log(temperature_k / 22.0), "gas",
            cp_j_kg_k=heat_capacity, vapor_mass_fraction=1.0,
        )

    vapor_state = synthetic_vapor_state(22.0)
    warmer_vapor_state = synthetic_vapor_state(24.0)
    finite_source = IntervalMassSource(
        SourceLocation("lh2-source", "plant-clock", "ground-frame", (0., 0., 0.), (0., 0., 1.)),
        (5.0, 7.0, 8.0, 10.0), (1.0, 0.0, 2.0), vapor_state,
        Origin.PREDICTED, "finite-vapor-history", "isolation",
    )

    callback_source = IntervalMassSource(
        SourceLocation("callback-source", "plant-clock", "ground-frame",
                       (0., 0., 0.), (0., 0., 1.)),
        (0., 10.), (1.0,), vapor_state, Origin.PREDICTED,
        "callback-source-evidence", "window_end",
    )

    class CallbackPool:
        def __init__(self, *, rate, area, duration, T_source, substance):
            self.rate, self.area, self.duration = rate, area, duration
            self.T_source, self.substance = T_source, substance

        @property
        def T(self):
            return self.T_source

    callback_boundary = steady_vapor_pool_boundary(
        callback_source, native_pool_factory=CallbackPool,
        substance=NativeSubstance(), area_m2=1.0,
        footprint_evidence_id="callback-footprint",
        ambient_pressure_pa=101325.0,
    )

    def mutating_runner(source, atmosphere, emission, water, *, x_max, **options):
        original_mass = float(callback_source.mass_kg[0])
        callback_source.mass_kg.setflags(write=True)
        callback_source.mass_kg[0] = original_mass + 0.1
        return Trajectory(), UsedSource()

    try:
        run_slabx_lh2(
            boundary=callback_boundary, atmosphere=Atmosphere(),
            emission_thermo=Thermo(), water_thermo=Thermo(),
            runner=mutating_runner, premise_check=premise_check,
            width_context=width_context, width_coupling=False, x_max_m=100.0,
        )
    except ValueError as error:
        assert "changed" in str(error)
    else:
        raise AssertionError("SLAB callback mutation was captured as a valid run boundary")
    finally:
        callback_source.mass_kg[0] = 1.0
        callback_source.mass_kg.setflags(write=False)

    snapshot_pool_calls = []

    class BinNativeSource:
        def __init__(self, *, rate, area, duration, T_source, substance):
            self.rate, self.area, self.duration = rate, area, duration
            self.T_source, self.substance = T_source, substance

        @property
        def T(self):
            return self.T_source

    def bin_pool_factory(**kwargs):
        snapshot_pool_calls.append(kwargs)
        return BinNativeSource(**kwargs)

    snapshot_series = run_preferred_lh2_quasi_steady_slices(
        HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
        source=finite_source,
        native_pool_factory=bin_pool_factory,
        substance=NativeSubstance(),
        area_m2=(1.0, 1.5, 2.0),
        footprint_evidence_id=("snapshot-footprint-a", "zero-bin", "snapshot-footprint-b"),
        state_by_interval=(vapor_state, None, warmer_vapor_state),
        state_projection_evidence_ids=("state-at-22k", None, "state-at-24k"),
        ambient_pressure_pa=101325.,
        atmosphere=Atmosphere(),
        emission_thermo=Thermo(),
        water_thermo=Thermo(),
        runner=lambda src, *args, **kwargs: (Trajectory(), src),
        premise_check=premise_check,
        width_context=width_context,
        width_coupling=False,
        x_max_m=100.,
    )
    assert snapshot_series.edges_s == (5.0, 7.0, 8.0, 10.0)
    assert snapshot_series.interval_windows_s == ((5.0, 7.0), (7.0, 8.0), (8.0, 10.0))
    source_bin_ledger = snapshot_series.source_bin_ledger
    assert tuple(row.window_s for row in source_bin_ledger) == snapshot_series.interval_windows_s
    assert tuple(row.mass_kg for row in source_bin_ledger) == tuple(finite_source.mass_kg)
    assert tuple(row.mean_rate_kg_s for row in source_bin_ledger) == (.5, 0.0, 1.0)
    assert all(row.clock_id == finite_source.location.clock_id for row in source_bin_ledger)
    assert tuple(row.native_run for row in source_bin_ledger) == snapshot_series.interval_runs
    assert tuple(row.accepted for row in source_bin_ledger) == (True, None, True)
    assert tuple(row.zero_mass for row in source_bin_ledger) == (False, True, False)
    assert all(not row.plume_memory_included for row in source_bin_ledger)
    assert all(row.require_current() is row for row in source_bin_ledger)
    assert snapshot_series.termination_time_s == 10.0
    assert snapshot_series.termination_reason == "isolation"
    assert snapshot_series.total_source_mass_kg == finite_source.total_mass_kg == 3.0
    assert snapshot_series.plume_memory_included is False
    assert len(snapshot_pool_calls) == 2
    assert snapshot_pool_calls[0]["rate"] == .5 and snapshot_pool_calls[0]["duration"] == 2.0
    assert snapshot_pool_calls[1]["rate"] == 1.0 and snapshot_pool_calls[1]["duration"] == 2.0
    assert snapshot_pool_calls[0]["area"] == 1.0 and snapshot_pool_calls[0]["T_source"] == 22.0
    assert snapshot_pool_calls[1]["area"] == 2.0 and snapshot_pool_calls[1]["T_source"] == 24.0
    assert snapshot_series.interval_runs[2].boundary.mass_source.state is warmer_vapor_state
    assert snapshot_series.interval_runs[2].boundary_audit.initial_temperature_change_k == 0.0
    assert snapshot_series.interval_runs[2].boundary_audit.used_temperature_change_k == 0.0
    first_snapshot_run = snapshot_series.interval_runs[0]
    assert first_snapshot_run.require_current() is first_snapshot_run
    from dataclasses import replace

    # A native steady run with the right mass/rate/duration must still map to
    # the exact parent-bin clock window. A shifted clock cannot be re-sealed as
    # if it were the original finite-source interval.
    shifted_first_source = replace(
        first_snapshot_run.boundary.mass_source,
        edges_s=(6.0, 8.0),
    )
    shifted_first_boundary = replace(
        first_snapshot_run.boundary,
        mass_source=shifted_first_source,
    )
    shifted_first_run = replace(first_snapshot_run, boundary=shifted_first_boundary)
    try:
        replace(snapshot_series, interval_runs=(
            shifted_first_run, None, snapshot_series.interval_runs[2],
        ))
    except ValueError:
        pass
    else:
        raise AssertionError("Snapshot receipt accepted a source bin with a shifted clock")

    try:
        replace(first_snapshot_run, accepted=not first_snapshot_run.accepted)
    except ValueError:
        pass
    else:
        raise AssertionError("SLAB run constructor accepted a forged acceptance flag")
    from h2physics.adapters.slabx_lh2 import SLABLH2SnapshotSeriesError

    class ClampedBinNativeSource(BinNativeSource):
        @property
        def T(self):
            return min(self.T_source, 23.0)

    try:
        run_preferred_lh2_quasi_steady_slices(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
            source=finite_source,
            native_pool_factory=lambda **kwargs: ClampedBinNativeSource(**kwargs),
            substance=NativeSubstance(),
            area_m2=(1.0, 1.5, 2.0),
            footprint_evidence_id=("snapshot-footprint-a", "zero-bin", "snapshot-footprint-b"),
            state_by_interval=(vapor_state, None, warmer_vapor_state),
            state_projection_evidence_ids=("state-at-22k", None, "state-at-24k"),
            ambient_pressure_pa=101325.,
            atmosphere=Atmosphere(),
            emission_thermo=Thermo(),
            water_thermo=Thermo(),
            runner=lambda src, *args, **kwargs: (Trajectory(), src),
            premise_check=premise_check,
            width_context=width_context,
            width_coupling=False,
            x_max_m=100.,
        )
    except SLABLH2SnapshotSeriesError as error:
        assert error.failed_index == 2 and error.result.accepted is False
        assert error.result.boundary_audit.initial_temperature_change_k == -1.0
        assert error.result.boundary_audit.used_temperature_change_k == -1.0
    else:
        raise AssertionError("Native source-temperature clamping was accepted as requested")
    assert snapshot_series.interval_runs[1] is None
    assert snapshot_series.interval_runs[0].accepted
    assert snapshot_series.interval_runs[2].boundary.mass_source.end_reason == "isolation"
    original_first_mass = float(finite_source.mass_kg[0])
    finite_source.mass_kg.setflags(write=True)
    finite_source.mass_kg[0] = original_first_mass + .25
    try:
        snapshot_series.require_current()
        source_bin_ledger[0].require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Snapshot receipt accepted a changed source mass array")
    finally:
        finite_source.mass_kg[0] = original_first_mass
        finite_source.mass_kg.setflags(write=False)
    trajectory = snapshot_series.interval_runs[0].native
    trajectory.x[0] = -1.0
    try:
        snapshot_series.interval_runs[0].require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("SLAB run receipt accepted a changed native trajectory")
    try:
        snapshot_series.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Snapshot receipt accepted a changed native trajectory")
    trajectory.x[0] = 0.0
    assert snapshot_series.require_current() is snapshot_series
    native_pool = snapshot_series.interval_runs[0].boundary.native_source
    original_native_temperature = native_pool.T_source
    native_pool.T_source = original_native_temperature + 1.0
    try:
        snapshot_series.interval_runs[0].boundary.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Native pool boundary accepted a changed constructed temperature")
    native_pool.T_source = original_native_temperature
    assert snapshot_series.require_current() is snapshot_series
    premise_calls = 0

    def fail_second_active_snapshot(trajectory):
        nonlocal premise_calls
        premise_calls += 1
        failed = premise_calls == 2
        return {"max": 1.5 if failed else 0.5, "violated": failed}

    try:
        run_preferred_lh2_quasi_steady_slices(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
            source=finite_source,
            native_pool_factory=bin_pool_factory,
            substance=NativeSubstance(),
            area_m2=1.,
            footprint_evidence_id="snapshot-footprint",
            ambient_pressure_pa=101325.,
            atmosphere=Atmosphere(),
            emission_thermo=Thermo(),
            water_thermo=Thermo(),
            runner=lambda src, *args, **kwargs: (Trajectory(), src),
            premise_check=fail_second_active_snapshot,
            width_context=width_context,
            width_coupling=False,
            x_max_m=100.,
        )
    except SLABLH2SnapshotSeriesError as error:
        assert error.failed_index == 2
        assert len(error.completed_runs) == 2
        assert error.completed_runs[0].accepted and error.completed_runs[1] is None
        assert error.result.accepted is False and error.native is error.result.native
    else:
        raise AssertionError("Failed SLAB snapshot discarded its native failure receipt")
    pool_factory_calls = 0

    def fail_second_boundary(**kwargs):
        nonlocal pool_factory_calls
        pool_factory_calls += 1
        if pool_factory_calls == 2:
            raise ValueError("authored second-bin boundary rejection")
        return bin_pool_factory(**kwargs)

    try:
        run_preferred_lh2_quasi_steady_slices(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
            source=finite_source,
            native_pool_factory=fail_second_boundary,
            substance=NativeSubstance(),
            area_m2=1.,
            footprint_evidence_id="snapshot-footprint",
            ambient_pressure_pa=101325.,
            atmosphere=Atmosphere(),
            emission_thermo=Thermo(),
            water_thermo=Thermo(),
            runner=lambda src, *args, **kwargs: (Trajectory(), src),
            premise_check=premise_check,
            width_context=width_context,
            width_coupling=False,
            x_max_m=100.,
        )
    except SLABLH2SnapshotSeriesError as error:
        assert error.failed_index == 2 and error.result is None
        assert error.cause.args == ("authored second-bin boundary rejection",)
        assert error.completed_runs[0].accepted and error.completed_runs[1] is None
    else:
        raise AssertionError("Boundary failure did not retain its preceding snapshots")
    slab_calls.clear()
    try:
        run_preferred_lh2_dispersion(
            HydrogenReleaseFamily.HIGH_PRESSURE_GAS, **slab_parameters
        )
    except NotImplementedError as error:
        assert "no fallback" in str(error)
    else:
        raise AssertionError("High-pressure gas request entered the SLABx-LH2 route")
    assert not slab_calls
    try:
        run_preferred_gas_dispersion(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN, **original_inputs
        )
    except NotImplementedError as error:
        assert "no fallback" in str(error)
    else:
        raise AssertionError("LH2-origin release entered the gas-nozzle adapter")
    assert len(gas_calls) == 1

    broken_scenario = DispersionScenario(
        HydrogenReleaseFamily.HIGH_PRESSURE_GAS, original_inputs
    )
    cross_family_inputs = dict(slab_parameters)
    cross_family_inputs["evidence_id"] = "gas-only-evidence"
    try:
        DispersionScenario(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN, cross_family_inputs
        )
    except ValueError as error:
        assert "gas-only" in str(error)
    else:
        raise AssertionError("An LH2 scenario admitted a gas-provider field")
    try:
        with patch("h2physics.dispersion.run_preferred_gas_dispersion",
                   side_effect=marker_gas_route):
            broken_scenario.run()
    except DispersionExecutionError as error:
        assert error.provider_id == "hyram"
        assert error.family is HydrogenReleaseFamily.HIGH_PRESSURE_GAS
        assert isinstance(error.cause, TypeError)
        assert error.__cause__ is error.cause
    else:
        raise AssertionError("Scenario failure omitted the selected-provider identity")
    selections = (
        (HydrogenReleaseFamily.HIGH_PRESSURE_GAS, "high-pressure-gas-jet", {"gas-origin"}),
        (HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN, "lh2-origin-vapor", {"lh2-origin"}),
    )
    registry = ModelRegistry()
    markers = {}
    for family, level, capabilities in selections:
        provider = preferred_dispersion_provider(family)
        markers[(level, provider)] = marker
        registry.register(ProviderBinding.bind(
            family_id="dispersion.outdoor",
            level_id=level,
            provider_id=provider,
            status="implemented_unverified",
            revision="preferred-dispersion-contract-r1",
            capabilities=capabilities,
            evidence_ids={"preferred-provider-selection"},
            factory=lambda selected=marker: selected,
        ))

    calls = 0
    for family, level, capabilities in selections:
        provider = preferred_dispersion_provider(family)
        request = ModelRequest(
            family_id="dispersion.outdoor",
            level_id=level,
            provider_id=provider,
            accepted_statuses={"implemented_unverified"},
            required_capabilities=capabilities,
            required_evidence_ids={"preferred-provider-selection"},
        )
        built = registry.select(request).build()
        assert built.model is markers[(level, provider)]
        calls += 1

    try:
        registry.select(ModelRequest(
            family_id="dispersion.outdoor",
            level_id="missing-lh2-origin-vapor",
            provider_id=preferred_dispersion_provider(HydrogenReleaseFamily.HIGH_PRESSURE_GAS),
            accepted_statuses={"native_adapter_verified"},
            required_capabilities={"lh2-origin"},
        ))
    except LookupError as error:
        assert "no fallback" in str(error)
    else:
        raise AssertionError("A cross-origin preferred-provider request was admitted")
    assert calls == 2
    return ValidationOutcome(
        accepted=True,
        metrics={
            "preferred_builds": calls,
            "route_callback_calls": len(gas_calls) + len(slab_calls),
            "cross_origin_fallbacks": 0,
        },
        limitations=(
            "The routing wrapper is checked with a call sentinel; native dispersion "
            "engines and plume predictions are not run or validated.",
        ),
    )


def validate_cluster_setup_pin(*, work_directory, **parameters):
    import hashlib

    from h2physics.cluster_validation import ClusterProfile, PBSResources, write_pbs_array

    digest = hashlib.sha256(b"site setup fixture\n").hexdigest()
    profile = ClusterProfile(
        name="model-selection",
        python_executable="/opt/python/bin/python",
        setup_script="/opt/environment/setup.sh",
        setup_sha256=digest,
        numerical_threads=1,
    )
    case = ValidationCase(
        identifier="setup-pin-fixture",
        profile=profile.name,
        entrypoint=__name__ + ":validate_exact",
        invariants=("metadata-only fixture",),
    )
    resources = PBSResources("debug", "account", 1, 1, "01:00:00")
    destination = work_directory / "setup-pin.pbs"
    script = write_pbs_array(
        (case,), {profile.name: profile}, resources,
        destination=destination,
        cluster_repository="/opt/project",
        cluster_plan_file="/opt/project/validation/plan.py",
        cluster_result_directory="/opt/results",
        expected_revision="a" * 40,
        expected_source_manifest_sha256="b" * 64,
        expected_plan_sha256="c" * 64,
        name="setup-pin",
    ).read_text(encoding="utf-8")
    before = f'test "$(sha256sum -- {profile.setup_script})" = \'{digest}  {profile.setup_script}\''
    after = f'test "$(sha256sum -- {profile.setup_script})" = \'{digest}  {profile.setup_script}\''
    if not (script.index(before) < script.index("source /opt/environment/setup.sh")
            < script.index(after, script.index("source /opt/environment/setup.sh"))):
        raise AssertionError("Generated setup digest checks do not bracket environment sourcing")
    pinned_import_path = (
        'export PYTHONPATH=/opt/project/src:/opt/project/scripts'
        '${PYTHONPATH:+:$PYTHONPATH}'
    )
    if pinned_import_path not in script:
        raise AssertionError(
            "Generated workers must prefer pinned src, then expose pinned scripts, "
            "before inherited PYTHONPATH entries"
        )
    if "qsub" in script or "sbatch" in script:
        raise AssertionError("The PBS writer must not submit a job")
    try:
        ClusterProfile("model-selection", "/opt/python/bin/python", "/opt/environment/setup.sh", "unpinned", 1)
    except ValueError:
        pass
    else:
        raise AssertionError("An unpinned environment setup script was accepted")
    return ValidationOutcome(True, {
        "pinned_digest": 1,
        "checks_bracket_source": 1,
        "pinned_src_and_scripts_precedence": 1,
        "scheduler_submissions": 0,
    }, ("Deferred contract case; this authoring check has not been executed.",))


def validate_pem_ohmic_bridge(*, work_directory, **parameters):
    import hashlib
    from dataclasses import replace

    import numpy as np

    from h2physics.adapters.pem_ohmic import PemOhmicLossBinding
    from h2physics.core import Origin
    from h2physics.data.pem import VARIABLES, PemExperiment, PemLoadReport, PemSpectrum
    from h2physics.electrochemistry import OhmicLoss
    from h2physics.impedance import COMPONENT, FREQUENCY, IMPEDANCE, ImpedanceSpectrum
    from h2physics.observations import ObservationTable, concatenate_observations
    from h2physics.research.fitting import FitResult

    member_digest = hashlib.sha256(b"fixture-pem-member").hexdigest()
    source = "fixture-pem-source"
    group = "cell-1/POL_GEIS/1"
    point_ids = tuple(f"cell-1/row-{index}" for index in range(3, 7))
    second_point_ids = tuple(f"cell-1/row-{index}" for index in range(9, 13))
    dc_ids = ("cell-1/row-1", "cell-1/row-2")
    second_dc_ids = ("cell-1/row-7", "cell-1/row-8")
    observation_values = np.ones((12, len(VARIABLES)))
    observation_values[:, 1] = 333.15
    observation_values[:, 4] = (0., 0., 100., 200., 400., 800., 0., 0., 100., 200., 400., 800.)
    observation_values[:, 5] = (0., 0., .10, .11, .12, .13, 0., 0., .10, .11, .12, .13)
    table = ObservationTable(
        observation_values, VARIABLES, np.ones_like(observation_values, dtype=bool),
        (*dc_ids, *point_ids, *second_dc_ids, *second_point_ids),
        ("cell-1/DC/1", "cell-1/DC/1", *(group for _ in point_ids),
         "cell-1/DC/2", "cell-1/DC/2", *(group for _ in second_point_ids)),
        (Origin.MEASURED,), source,
        (("member_sha256", member_digest), ("active_area_m2", "0.0004")),
    )
    experiment = PemExperiment(
        table, ("DC", "DC", *("POL_GEIS" for _ in point_ids),
                "DC", "DC", *("POL_GEIS" for _ in second_point_ids)),
        4e-4, "cell-1-clock", 1, PemLoadReport(12, 12, member_digest, 0, 0),
    )
    spectrum_native = ImpedanceSpectrum(
        np.array([100., 200., 400., 800.]),
        np.array([.10-.01j, .11-.02j, .12-.03j, .13-.04j]),
        np.ones(4, dtype=bool), point_ids, group+"/sweep-1", source,
        Origin.RECONSTRUCTED, frequency_origin=Origin.MEASURED,
    )
    spectrum = PemSpectrum(spectrum_native, 12., 1.8, 333.15, 2e5, dc_ids, 1.0)
    second_spectrum_native = ImpedanceSpectrum(
        np.array([100., 200., 400., 800.]),
        np.array([.10-.01j, .11-.02j, .12-.03j, .13-.04j]),
        np.ones(4, dtype=bool), second_point_ids, group+"/sweep-2", source,
        Origin.RECONSTRUCTED, frequency_origin=Origin.MEASURED,
    )
    second_spectrum = PemSpectrum(
        second_spectrum_native, 12., 1.8, 333.15, 2e5, second_dc_ids, .5,
    )
    spectrum_table = spectrum_native.cartesian_observations()
    fit = FitResult(
        {"R0": .1}, "parameter_estimation", "native-impedance-test-circuit",
        spectrum_table.content_sha256, (FREQUENCY, COMPONENT), IMPEDANCE,
        spectrum_table.row_ids, (spectrum_native.experiment_id,), (), np.ones(8), np.ones(1),
        1, 1e-8, 1., .01, .001, 10, (),
    )
    binding = PemOhmicLossBinding.from_fit(
        experiment, spectrum, fit, parameter_name="R0",
        interpretation_id="caller-reviewed-whole-cell-effective-resistance",
        expected_model_id="native-impedance-test-circuit",
    )
    assert binding.area_resistance_ohm_m2 == .1*4e-4
    assert binding.require_current() is binding
    assert binding.dc_context_row_ids == dc_ids
    assert binding.fit_numerical_rank == binding.fit_parameter_count == 1
    assert np.isclose(binding.voltage_loss_v(30_000., 333.15), .1*4e-4*30_000.)
    second_table = second_spectrum_native.cartesian_observations()
    ordered_fit_table = concatenate_observations(
        (spectrum_table, second_table), source_id=source,
    )
    multi_fit = replace(
        fit,
        fitting_data_sha256=ordered_fit_table.content_sha256,
        fitting_row_ids=ordered_fit_table.row_ids,
        fitting_experiment_ids=tuple(sorted((spectrum_native.experiment_id,
                                             second_spectrum_native.experiment_id))),
    )
    multi_binding = PemOhmicLossBinding.from_fit(
        experiment, (spectrum, second_spectrum), multi_fit, parameter_name="R0",
        interpretation_id="caller-reviewed-two-sweep-effective-resistance",
        operating_spectrum_id=second_spectrum_native.experiment_id,
    )
    assert multi_binding.fit_spectrum_experiment_ids == (
        spectrum_native.experiment_id, second_spectrum_native.experiment_id,
    )
    assert multi_binding.spectrum_experiment_id == second_spectrum_native.experiment_id
    assert multi_binding.fit_dc_context_row_ids == (dc_ids, second_dc_ids)
    try:
        PemOhmicLossBinding.from_fit(
            experiment, (spectrum, second_spectrum), multi_fit, parameter_name="R0",
            interpretation_id="missing-operating-sweep",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Multi-sweep PEM fit silently selected a stack operating point")
    stack_losses = binding.extend_loss_mapping({}, component_id="measured-eis-r0")
    assert np.isclose(stack_losses["measured-eis-r0"](30_000., 333.15),
                      binding.voltage_loss_v(30_000., 333.15))
    try:
        binding.extend_loss_mapping(stack_losses, component_id="measured-eis-r0")
    except ValueError:
        pass
    else:
        raise AssertionError("PEM loss mapping silently replaced an existing component")
    existing_ohmic = {"separate-contact": OhmicLoss(lambda _temperature: 1e-6)}
    try:
        binding.extend_loss_mapping(existing_ohmic, component_id="measured-eis-r0")
    except ValueError:
        pass
    else:
        raise AssertionError("PEM loss mapping admitted a possible duplicate ohmic term")
    justified_losses = binding.extend_loss_mapping(
        existing_ohmic, component_id="measured-eis-r0",
        allow_existing_ohmic_terms=True,
        double_count_evidence_id="separate-contact-measurement",
    )
    assert set(justified_losses) == {"separate-contact", "measured-eis-r0"}
    assert justified_losses.double_count_evidence_id == "separate-contact-measurement"
    assert justified_losses.require_current() is justified_losses
    try:
        justified_losses.losses["forged"] = lambda *_: 0.0
    except TypeError:
        pass
    else:
        raise AssertionError("PEM stack loss receipt exposed a mutable mapping")
    adjusted = PemOhmicLossBinding.from_fit(
        experiment, spectrum, fit, parameter_name="R0",
        interpretation_id="caller-temperature-adjustment",
        temperature_adjustment=lambda temperature: 1.+.002*(temperature-333.15),
    )
    assert np.isclose(adjusted.voltage_loss_v(30_000., 343.15), .1*4e-4*30_000.*1.02)
    try:
        replace(binding, active_area_m2=2e-4)
    except ValueError:
        pass
    else:
        raise AssertionError("PEM EIS bridge accepted a forged area resistance receipt")
    try:
        forged_spectrum = replace(spectrum, dc_context_row_ids=())
        PemOhmicLossBinding.from_fit(
            experiment, forged_spectrum, fit, parameter_name="R0",
            interpretation_id="forged-input",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("PEM EIS bridge accepted removed DC context")
    incomplete = replace(fit, fitting_row_ids=fit.fitting_row_ids[:-1])
    try:
        PemOhmicLossBinding.from_fit(
            experiment, spectrum, incomplete, parameter_name="R0",
            interpretation_id="incomplete-fit",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("PEM EIS bridge accepted a fit omitting a complex projection")
    for changed_fit, maximum_condition in (
        (replace(fit, numerical_rank=0), None),
        (replace(fit, active_parameter_bounds=(("R0", 1),)), None),
        (fit, .5),
    ):
        try:
            PemOhmicLossBinding.from_fit(
                experiment, spectrum, changed_fit, parameter_name="R0",
                interpretation_id="inadmissible-fit-diagnostic",
                maximum_condition_number=maximum_condition,
            )
        except ValueError:
            continue
        raise AssertionError("PEM EIS bridge accepted an unidentifiable or inadmissible R0")
    return ValidationOutcome(
        accepted=True,
        metrics={"source_points": len(point_ids), "dc_context_rows": len(dc_ids),
                 "area_resistance_ohm_m2": binding.area_resistance_ohm_m2,
                 "temperature_multiplier": 1.02},
        limitations=("Synthetic contract only; it neither refits the archived spectra nor "
                      "qualifies R0 as membrane resistance, a DC law or a thermal coefficient.",),
    )


def validate_robust_fit_loss(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.core import Origin
    from h2physics.observations import ObservationTable, Variable
    from h2physics.research.fitting import BoundedParameter, fit_observations

    x = Variable("x", "dimensionless", "1")
    y = Variable("y", "dimensionless", "1")
    table = ObservationTable(
        values=np.array([[0., 0.], [1., 1.], [2., 2.], [3., 3.], [4., 4.], [5., 100.]]),
        variables=(x, y), valid=np.ones((6, 2), dtype=bool),
        row_ids=tuple(f"row-{index}" for index in range(6)),
        experiment_ids=("authored-synthetic",) * 6,
        origins=(Origin.MEASURED, Origin.MEASURED), source_id="authored-robust-loss-fixture",
    )
    parameters = (BoundedParameter("gain", .5, -10., 20., 1.),)

    def predictor(observations, values):
        return observations.column("x")[0] * values["gain"]

    fit_args = dict(inputs=(x,), response=y, parameters=parameters, predictor=predictor,
                    model_id="authored-through-origin-line", purpose="parameter_estimation")
    ordinary = fit_observations(table, **fit_args)
    robust = fit_observations(table, loss="cauchy", f_scale=.5, **fit_args)
    assert ordinary.optimizer_loss == "linear" and ordinary.optimizer_f_scale == 1.
    assert robust.optimizer_loss == "cauchy" and robust.optimizer_f_scale == .5
    assert abs(robust.parameter_values["gain"] - 1.) < abs(ordinary.parameter_values["gain"] - 1.)
    assert robust.root_mean_square_error != robust.optimizer_cost
    for options in ({"loss": "invented"}, {"f_scale": 0.}, {"f_scale": -1.}):
        try:
            fit_observations(table, **fit_args, **options)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid robust-loss configuration was admitted")
    return ValidationOutcome(True, {
        "default_loss": ordinary.optimizer_loss,
        "robust_loss": robust.optimizer_loss,
        "robust_f_scale": robust.optimizer_f_scale,
        "retained_rows": len(robust.fitting_row_ids),
    }, ("Synthetic estimator contract only; not physical or experimental validation.",))
