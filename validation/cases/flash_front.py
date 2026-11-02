"""Deferred native material-front validation definitions; no calculation at import."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    entries = (
        ("flash-front-axial", "validate_axial", ("independent native-speed axial travel", "finite HP mass/U/work")),
        ("flash-front-gaps", "validate_gaps", ("unreachable remains absent", "finite contact overlap")),
        ("flash-front-binding", "validate_binding", ("native/result mutation rejection", "public factory/source/state/lifecycle guards", "native front trace cannot be forged, cloned, or stale")),
        ("flash-front-native-refinement", "validate_refinement", ("actual native flame domain/grid sensitivity",)),
    )
    return tuple(ValidationCase(identifier=name, profile="flash-front",
        entrypoint=__name__+":"+entrypoint, invariants=invariants)
        for name, entrypoint, invariants in entries)


def _reference(**parameters):
    from examples.flash_front import build_reference
    return build_reference(**parameters)


def _save(directory, metrics, *, references=(), trace=None):
    import json
    from pathlib import Path

    import numpy as np
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    evidence = {"metrics": metrics, "references": [
        {"identifier": r.identifier, "mechanism_id": r.flame_result.basis.identifier,
         "mechanism_sha256": r.flame_result.basis.source_sha256,
         "native_flame_sha256": r.flame_sha256, "admission_id": r.admission.evidence_id,
         "source_bytes_verified": r.flame_source_binding.handle.source_bytes_verified,
         "native_definition_sha256": r.flame_source_binding.handle.definition_sha256}
        for r in references]}
    if trace is not None:
        evidence["arrival_s"] = dict(trace.arrival_s)
        evidence["cell_ids"] = [c.identifier for c in trace.cells]
    (destination/"flash-front.json").write_text(json.dumps(evidence, allow_nan=False)+"\n", encoding="utf-8")
    for i, reference in enumerate(references):
        flame = reference.flame_result.native_solution
        np.savez(destination/f"native-flame-{i}.npz", grid_m=flame.grid, temperature_k=flame.T,
            velocity_m_s=flame.velocity, density_kg_m3=flame.density_mass, species_x=flame.X,
            species_names=np.asarray(flame.gas.species_names),
            band_time_s=reference.thermal_progress_time_s,
            band_temperature_k=reference.thermal_progress_temperature_k,
            unburned_tpy=np.array((reference.unburned_phase.T, reference.unburned_phase.P,
                                  *reference.unburned_phase.Y)),
            burned_tpy=np.array((reference.burned_phase.T, reference.burned_phase.P,
                                *reference.burned_phase.Y)))
    if trace is not None:
        np.savez(destination/"native-paths.npz", travel_s=trace.native_travel_times_s,
            predecessors=trace.native_predecessors, sources=trace.native_sources,
            edge_time_s=trace.native_sparse_graph.data,
            edge_indices=trace.native_sparse_graph.indices,
            edge_indptr=trace.native_sparse_graph.indptr)


def validate_axial(*, work_directory):
    from h2physics.adapters.flash_front import FrontCell, run_material_front
    reference = _reference()
    cells = tuple(FrontCell(f"cell-{i}", (i, 0, 0), reference) for i in range(5))
    trace = run_material_front(cells, spacing_m=(.1, .1, .1), ignition_cell_ids=("cell-0",),
                               ignition_s=10., horizon_s=20., clock_projection_tolerance_s=1e-10)
    error = max(abs(trace.arrival_s[f"cell-{i}"]-(10.+i*.1/reference.speed_m_s)) for i in range(5))
    assert error < 1e-10 and len(trace.burned_cells) == 5
    assert abs(trace.mass_residual_kg) < 1e-12
    assert abs(trace.total_energy_residual_j) <= trace.burned_mixture_mass_kg*.02+1e-10
    assert sum(b.hydrogen_consumed_kg for b in trace.burned_cells) > 0
    for burn in trace.burned_cells:
        assert burn.expanded_hp_volume_m3 > burn.initial_volume_m3
        assert burn.pressure_work_out_j > 0
        assert abs(burn.internal_energy_change_j+burn.pressure_work_out_j) <= burn.mixture_mass_kg*.02+1e-10
    metrics = {"axial_time_error_s": error, "mass_residual_kg": trace.mass_residual_kg,
               "energy_residual_j": trace.total_energy_residual_j, "native_speed_m_s": reference.speed_m_s}
    _save(work_directory, metrics, references=(reference,), trace=trace)
    return ValidationOutcome(True, metrics, ("Material-frame lattice only; no lab flame or harm validation",))


def validate_gaps(*, work_directory):
    from h2physics.adapters.flash_front import FrontCell, MaterialContact, run_material_front
    reference = _reference()
    cells = tuple(FrontCell(f"cell-{i}", (i, 0, 0), reference) for i in (0, 1, 3))
    travel = .1/reference.speed_m_s
    duration = reference.thermal_band_residence_s
    trace = run_material_front(cells, spacing_m=(.1, .1, .1), ignition_cell_ids=("cell-0",),
        ignition_s=0., horizon_s=travel+duration, clock_projection_tolerance_s=1e-10,
        contacts=(MaterialContact("reached", "cell-1", travel, travel+duration, "authored"),
                  MaterialContact("absent", "cell-3", 0., 100., "authored")))
    assert trace.arrival_s["cell-3"] is None
    assert trace.contacts[1].overlap_s == 0
    assert abs(trace.contacts[0].overlap_s-duration) < 1e-10
    assert trace.unburned_mixture_mass_kg > 0 and len(trace.burned_cells) == 2
    metrics = {"thermal_material_residence_s": duration, "unburned_mass_kg": trace.unburned_mixture_mass_kg}
    _save(work_directory, metrics, references=(reference,), trace=trace)
    return ValidationOutcome(True, metrics, ("Missing paths are not obstacle-flow calculations",))


def _public_factory_guards(reference):
    import gc
    import weakref
    from dataclasses import replace

    from h2physics.adapters.cantera import CanteraGas, CanteraPhaseFactoryError, ReactiveState

    owner, initial = reference.gas_owner, reference.initial
    assert owner.source_bytes_verified
    source = owner.mechanism_source
    assert source.sha256 == owner.basis.source_sha256
    scratch = owner.create_phase(initial)
    snapshot = owner.snapshot_phase(scratch)
    assert scratch.native_phase is not reference.unburned_phase
    assert snapshot.density_kg_m3 == scratch.native_phase.density_mass
    scratch.native_phase.basis = "molar"
    assert owner.snapshot_phase(scratch).density_kg_m3 == scratch.native_phase.density_mass
    scratch.native_phase.basis = "mass"
    frozen = owner.bind_phase(scratch, freeze_state=True)
    evolving = owner.bind_phase(scratch, freeze_state=False)
    assert evolving.snapshot_role == "validated-creation-state"
    scratch.native_phase.TP = initial.temperature_k+1., initial.pressure_pa
    evolving.require_current()
    assert abs(owner.snapshot_phase(scratch).state.temperature_k-(initial.temperature_k+1.)) < 1e-10
    try:
        frozen.require_current()
    except CanteraPhaseFactoryError as error:
        assert "Frozen native phase state" in str(error)
        assert error.native_phase is scratch.native_phase and error.cause is error.__cause__
    else:
        raise AssertionError("A frozen reference silently followed mutable native TP")
    try:
        owner.require_phase_binding(replace(evolving))
    except CanteraPhaseFactoryError:
        pass
    else:
        raise AssertionError("A cloned binding was admitted as owner-issued")

    # A real native singleton is deliberately a bad callback; first admission
    # stays caller-declared, and reuse is rejected before overwriting TPX.
    singleton = owner.phase_factory()
    legacy = CanteraGas(lambda: singleton, owner.basis)
    first = legacy.create_phase(initial)
    assert not first.source_bytes_verified and not legacy.source_bytes_verified
    sealed = legacy.bind_phase(first)
    try:
        legacy.create_phase(ReactiveState(initial.temperature_k+1., initial.pressure_pa,
                                          initial.mole_fractions))
    except CanteraPhaseFactoryError as error:
        assert "reused" in str(error) and error.native_phase is singleton
    else:
        raise AssertionError("A callback reused a live native phase")
    sealed.require_current()
    assert singleton.T == first.creation_snapshot.state.temperature_k
    other_owner = CanteraGas(lambda: singleton, owner.basis)
    try:
        other_owner.create_phase(initial)
    except CanteraPhaseFactoryError as error:
        assert "reused" in str(error) and error.native_phase is singleton
    else:
        raise AssertionError("A live native phase was aliased across public owners")
    sealed.require_current()

    # Existing bare-phase calls stay supported and retain at most their latest
    # handle. Their mutable state is not implicitly frozen.
    compatible = CanteraGas(lambda: owner.phase_factory(), owner.basis)
    bare_first = compatible._phase(initial)
    bare_first.TP = initial.temperature_k+1., initial.pressure_pa
    bare_second = compatible._phase(initial)
    assert bare_first is not bare_second and isinstance(bare_second, owner.ct.Solution)
    assert compatible.live_phase_handle_count == 1
    assert compatible.last_legacy_phase_handle.native_phase is bare_second

    try:
        CanteraGas.from_yaml(source.source_bytes+b"\n# changed source bytes\n", owner.basis,
                             phase_name=source.phase_name)
    except ValueError as error:
        assert "source SHA" in str(error)
    else:
        raise AssertionError("Changed source bytes acquired the old source identity")

    outside = owner.create_phase(initial)
    outside.native_phase.TP = owner.basis.maximum_temperature_k+1., initial.pressure_pa
    try:
        owner.snapshot_phase(outside)
    except CanteraPhaseFactoryError as error:
        assert "domain" in str(error) and error.native_phase is outside.native_phase
    else:
        raise AssertionError("Native state escaped the declared source/fit domain")

    changed_definition = owner.create_phase(initial)
    assert changed_definition.native_phase.n_reactions > 0
    changed_definition.native_phase.set_multiplier(1.01, 0)
    try:
        changed_definition.require_current()
    except CanteraPhaseFactoryError as error:
        assert "definition" in str(error)
    else:
        raise AssertionError("Native reaction definition/multiplier changes were accepted")

    old_basis = owner.basis
    owner.basis = replace(old_basis, source_sha256="0"*64)
    try:
        try:
            owner.snapshot_phase(scratch)
        except CanteraPhaseFactoryError as error:
            assert "ownership" in str(error)
        else:
            raise AssertionError("A stale source/domain declaration remained admissible")
    finally:
        owner.basis = old_basis

    original_factory = owner.phase_factory
    owner.phase_factory = lambda: singleton
    try:
        try:
            owner.create_phase(initial)
        except CanteraPhaseFactoryError as error:
            assert "ownership" in str(error) and error.native_phase is None
        else:
            raise AssertionError("A replaced factory retained the original source/domain identity")
    finally:
        owner.phase_factory = original_factory

    gc.collect()
    before = owner.live_phase_handle_count
    for _ in range(3):
        temporary = owner.create_phase(initial)
    last_weak = weakref.ref(temporary)  # Python handle, not a native weakref assumption.
    del temporary
    gc.collect()
    assert last_weak() is None and owner.live_phase_handle_count == before
    reference.guard()
    return {"factory_source_guards_defined": True, "temporary_native_phases_retained": 0,
            "legacy_source_bytes_verified": False, "public_source_bytes_verified": True}


def _mass_display_basis_guards(reference):
    import numpy as np

    from h2physics.adapters.cantera import CanteraGas, CanteraPhaseFactoryError
    from h2physics.adapters.flash_front import FrontCell, run_material_front

    owner, flame = reference.gas_owner, reference.flame_result.native_solution
    rho_mass = np.array(flame.density_mass, copy=True)
    cells = (FrontCell("display-basis-cell", (0, 0, 0), reference),)
    options = {"spacing_m": (.1, .1, .1), "ignition_cell_ids": ("display-basis-cell",),
               "ignition_s": 0., "horizon_s": 1., "clock_projection_tolerance_s": 1e-10}
    before = run_material_front(cells, **options)
    phases = (flame.gas, reference.unburned_phase, reference.burned_phase)
    old_bases = tuple(phase.basis for phase in phases)
    try:
        for phase in phases:
            phase.basis = "molar"
        reference.guard()
        assert np.allclose(flame.density_mass, rho_mass, rtol=1e-14, atol=0.)
        assert not np.allclose(flame.density, rho_mass, rtol=1e-6, atol=0.)
        assert owner.snapshot_phase(reference.unburned_binding.handle).density_kg_m3 == reference.unburned_binding.snapshot.density_kg_m3
        after = run_material_front(cells, **options)
        assert after.initial_cloud_mass_kg == before.initial_cloud_mass_kg
        assert after.burned_cells[0].expanded_hp_volume_m3 == before.burned_cells[0].expanded_hp_volume_m3
        assert after.total_energy_residual_j == before.total_energy_residual_j
    finally:
        for phase, basis in zip(phases, old_bases, strict=True):
            phase.basis = basis

    # Native onedim initialization itself uses gas.density for its mdot guess;
    # reject that unsupported input coordinate before creating a new FreeFlame.
    molar_phase = owner.phase_factory()
    molar_phase.basis = "molar"
    molar_owner = CanteraGas(lambda: molar_phase, owner.basis)
    try:
        molar_owner.free_flame(reference.initial, reference.flame_result.settings)
    except CanteraPhaseFactoryError as error:
        assert error.stage == "free_flame_basis" and error.native_phase is molar_phase
        assert molar_phase.basis == "molar"
    else:
        raise AssertionError("Native flame initialization silently consumed molar density as mass density")
    reference.guard()
    return {"mass_snapshot_and_flame_vector_display_invariance_defined": True,
            "native_molar_basis_flame_setup_rejected": True}


def validate_binding(*, work_directory):
    from dataclasses import replace

    from h2physics.adapters.flash_front import FlashFrontError, FrontCell, run_material_front
    reference = _reference()
    factory_metrics = _public_factory_guards(reference)
    display_metrics = _mass_display_basis_guards(reference)
    hp = reference.hp_result
    hp.require_current()
    flame_result = reference.flame_result
    flame_result.require_current()
    try:
        replace(flame_result)
    except ValueError:
        pass
    else:
        raise AssertionError("Free-flame result clone retained native issuance")
    try:
        type(flame_result)(flame_result.basis, flame_result.settings,
                           flame_result.speed_m_s, flame_result.grid_points,
                           flame_result.relative_mass_flux_span,
                           flame_result.native_solution, flame_result.native_phase_handle)
    except ValueError:
        pass
    else:
        raise AssertionError("Directly fabricated free-flame result was accepted")
    from h2physics.adapters.cantera import temperature_rise_event
    reactor_trace = reference.gas_owner.closed_reactor(
        reference.initial, (0., 1e-7), maximum_time_step_s=1e-8)
    temperature_rise_event(reactor_trace, 1.)
    try:
        replace(reactor_trace)
    except ValueError:
        pass
    else:
        raise AssertionError("Reactor trace clone retained native issuance")
    try:
        type(reactor_trace)(reactor_trace.basis, reactor_trace.constraint,
            reactor_trace.time_s, reactor_trace.snapshots,
            reactor_trace.maximum_energy_residual_j_kg,
            reactor_trace.maximum_element_mass_fraction_residual)
    except ValueError:
        pass
    else:
        raise AssertionError("Directly fabricated reactor trace was accepted")
    try:
        replace(hp)
    except ValueError:
        pass
    else:
        raise AssertionError("Equilibrium result clone retained native issuance")
    try:
        type(hp)(hp.basis, hp.constraint, hp.initial, hp.final,
                 hp.energy_residual_j_kg, hp.maximum_element_mass_fraction_residual)
    except ValueError:
        pass
    else:
        raise AssertionError("Directly fabricated equilibrium result was accepted")
    changed = replace(reference, speed_m_s=2*reference.speed_m_s)
    try:
        run_material_front((FrontCell("cell", (0, 0, 0), changed),), spacing_m=(.1, .1, .1),
                           ignition_cell_ids=("cell",), ignition_s=0., horizon_s=1., clock_projection_tolerance_s=1e-10)
    except FlashFrontError as error:
        assert isinstance(error.cause, ValueError) and not error.completed_burns
    else:
        raise AssertionError("Changed native summary was accepted")
    try:
        run_material_front((FrontCell("a", (0, 0, 0), reference),
                            FrontCell("b", (1, 0, 0), reference)), spacing_m=(.1, .1, .1),
                           ignition_cell_ids=("a",), ignition_s=1e18, horizon_s=1e18+1024.,
                           clock_projection_tolerance_s=1e-10)
    except FlashFrontError as error:
        assert isinstance(error.cause, ValueError) and "clock" in str(error.cause).lower()
        assert not error.completed_burns
    else:
        raise AssertionError("Unresolvable absolute clock was accepted")
    trace = run_material_front((FrontCell("a", (0, 0, 0), reference),
                                FrontCell("b", (1, 0, 0), reference)), spacing_m=(.1, .1, .1),
                               ignition_cell_ids=("a",), ignition_s=0., horizon_s=1.,
                               clock_projection_tolerance_s=1e-10)
    trace.require_current()
    try:
        replace(trace)
    except ValueError:
        pass
    else:
        raise AssertionError("Flash-front result clone retained native issuance")
    trace.native_sparse_graph.data[0] *= 1.01
    try:
        trace.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed native front graph remained a current result")
    # Actual native mutation must invalidate the original record as well.
    reference.flame_result.native_solution.P *= 1.01
    try:
        reference.guard()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed native pressure was accepted")
    try:
        temperature_rise_event(reactor_trace, 1.)
    except ValueError:
        pass
    else:
        raise AssertionError("Changed native reactor state remained a current trace")
    metrics = {"rejected_summary_mutations": 1, "rejected_native_mutations": 1,
               "rejected_fabricated_equilibrium_results": 2,
               "rejected_unresolved_clocks": 1}
    metrics.update(factory_metrics)
    metrics.update(display_metrics)
    _save(work_directory, metrics)
    return ValidationOutcome(True, metrics, ("Static bindings are validity guards, not a security boundary",))


def validate_refinement(*, work_directory):
    coarse = _reference(width_m=.04, slope=.08)
    fine = _reference(width_m=.08, slope=.04)
    difference = abs(fine.speed_m_s-coarse.speed_m_s)/fine.speed_m_s
    assert difference < .05
    metrics = {"relative_native_speed_difference": difference,
               "coarse_grid_points": coarse.flame_result.grid_points,
               "fine_grid_points": fine.flame_result.grid_points}
    _save(work_directory, metrics, references=(coarse, fine))
    return ValidationOutcome(True, metrics, (
        "Five-percent authored numerical gate; no measured flame/flash-fire qualification",))
