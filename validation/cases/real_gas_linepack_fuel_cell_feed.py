"""Native real-gas linepack withdrawal and explicit fuel-cell energy handoff."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="real-gas-linepack-fuel-cell-hydrogen-feed-handoff",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_feed",
        invariants=(
            "reuse-CoolProp-real-gas-linepack-mass-ledger-and-pressure-endpoints",
            "native-outlet-state-matches-linepack-EOS-temperature-and-pressure-bin",
            "integrated-source-enthalpy-remains-explicit-caller-evidence",
            "exact-clock-and-finite-H2-feed-mass-reference-energy-closure",
            "known-normal-hydrogen-cannot-map-to-para-or-unspecified-feed-spin",
            "conditioned-feed-pressure-matches-the-actual-fuel-cell-inlet",
            "feed-origin-preserves-source-classification-without-measurement-upgrade",
            "source-cloning-state-forgery-and-post-issue-property-mutation-rejected",
        ),
    ),)


def validate_feed(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from scipy.integrate import quad

    from examples.fuel_cell import synthetic_problem
    from h2physics.adapters.linepack_fuel_cell_feed import bind_linepack_fuel_cell_feed
    from h2physics.adapters.linepack_source import advance_linepack_to_source
    from h2physics.core import Origin
    from h2physics.real_gas_linepack import RealGasLinepackState
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropIsothermalEOS, CoolPropProperties

    cell, initial_cell, commands = synthetic_problem()
    step = commands[0]
    eos = CoolPropIsothermalEOS("Hydrogen")
    properties = CoolPropProperties("Hydrogen")
    initial = RealGasLinepackState.from_pressure(
        volume_m3=2., temperature_k=step.temperature_k, pressure_pa=5e6,
        eos=eos, time_s=step.start_s, minimum_pressure_pa=1e5, maximum_pressure_pa=1e7,
    )
    arguments = dict(duration_s=step.end_s-step.start_s, inlet_mass_flow_kg_s=0.,
        outlet_mass_flow_kg_s=.02, minimum_mass_kg=.01)
    final, ledger = initial.advance(**arguments)
    outlet = properties.state_pt(.5*(initial.pressure_pa+final.pressure_pa), initial.temperature_k)
    location = SourceLocation("real-linepack-feed", step.clock_id, "pipe-axis",
                              (0., 0., 0.), (1., 0., 0.))
    common = dict(location=location, properties=properties, origin=Origin.SYNTHETIC,
        evidence_id="authored-real-linepack-port-operation",
        state_projection_evidence_id="authored-midpoint-outlet-projection-only")
    source = advance_linepack_to_source(initial, gas_state=outlet, **arguments, **common)
    assert source.require_current() is source
    assert source.ledger == ledger and source.final == final
    assert abs(source.ledger.mass_residual_kg) < 1e-12
    feed_state = properties.state_pt(cell.boundary.pressure_pa, step.temperature_k)
    names = tuple(cell.kernel.names)
    hs = cell.caloric_source.provider.enthalpies_j_mol(feed_state.temperature_k, feed_state.pressure_pa)
    amount = ledger.outlet_mass_kg / cell.stack.geometry.hydrogen_molar_mass_kg_mol
    feed_h = amount*float(hs[names.index(cell.hydrogen_id)])
    # Independent test quadrature of this prescribed zero-inlet isothermal
    # trajectory supplies the interval energy. Production adapters never infer
    # that energy from the representative state or recreate this path.
    def native_enthalpy_rate(elapsed):
        density = (initial.mass_kg-arguments["outlet_mass_flow_kg_s"]*elapsed)/initial.volume_m3
        pressure = eos.pressure_rho_t(density, initial.temperature_k)
        return arguments["outlet_mass_flow_kg_s"]*properties.state_pt(
            pressure, initial.temperature_k).enthalpy_j_kg

    source_h, quadrature_error = quad(native_enthalpy_rate, 0., arguments["duration_s"],
                                     epsabs=1e-5, epsrel=1e-10)
    native_feed_h = ledger.outlet_mass_kg*feed_state.enthalpy_j_kg
    reference_offset = feed_h-native_feed_h
    feed_arguments = dict(feed_source_id="authored-real-linepack-H2-feed",
        origin=Origin.SYNTHETIC, fuel_cell_feed_state=feed_state,
        source_enthalpy_j=source_h,
        source_enthalpy_reference_id=properties.basis.reference_id,
        receiver_energy_basis_id=cell.kernel.energy_basis_id, reference_offset_j=reference_offset,
        clock_evidence_id="authored-common-exact-clock",
        state_evidence_id="authored-pressure-and-temperature-conditioning",
        transfer_evidence_id="authored-finite-withdrawal-transfer",
        energy_evidence_id="authored-native-isothermal-path-quadrature-not-device-data",
        conditioning_energy_j=feed_h-source_h-reference_offset,
        absolute_mass_tolerance_kg=1e-12, relative_mass_tolerance=1e-10,
        absolute_energy_tolerance_j=1e-6, relative_energy_tolerance=1e-10)
    receipt = bind_linepack_fuel_cell_feed(source, cell, step, **feed_arguments)
    assert receipt.require_current() is receipt
    assert receipt.source_mass_kg == ledger.outlet_mass_kg
    assert receipt.source_enthalpy_j == source_h
    assert abs(receipt.energy_residual_j) < 1e-6
    trace = cell.run(initial_cell, (receipt.step,))
    assert trace.require_current() is trace
    assert trace.final.amounts_mol[cell.hydrogen_id] > initial_cell.amounts_mol[cell.hydrogen_id]

    rejected = 0
    for wrong in (
        replace(outlet, density_kg_m3=outlet.density_kg_m3*1.01),
        properties.state_pt(8e6, initial.temperature_k),
        properties.state_pt(outlet.pressure_pa, initial.temperature_k+1.),
    ):
        try:
            advance_linepack_to_source(initial, gas_state=wrong, **arguments, **common)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Forged or out-of-bin representative state was admitted")
    for operation in (
        lambda: replace(source),
        lambda: bind_linepack_fuel_cell_feed(source, cell, replace(step, clock_id="foreign"), **feed_arguments),
        lambda: bind_linepack_fuel_cell_feed(source, cell, step,
            **{**feed_arguments, "source_enthalpy_j": source_h+1e3}),
    ):
        try:
            operation()
        except (TypeError, ValueError):
            rejected += 1
        else:
            raise AssertionError("Clone, mismatched clock or unclosed interval energy was admitted")
    para_feed = CoolPropProperties("ParaHydrogen").state_pt(
        cell.boundary.pressure_pa, step.temperature_k)
    unspecified_feed = replace(feed_state,
        basis=replace(feed_state.basis, spin_composition="unspecified"))
    high_pressure_feed = properties.state_pt(2.*cell.boundary.pressure_pa, step.temperature_k)
    for wrong_feed, message in (
        (para_feed, "spin composition"),
        (unspecified_feed, "spin composition"),
        (high_pressure_feed, "conditioned inlet boundary"),
    ):
        try:
            bind_linepack_fuel_cell_feed(source, cell, step,
                **{**feed_arguments, "fuel_cell_feed_state": wrong_feed})
        except ValueError as error:
            assert message in str(error)
            rejected += 1
        else:
            raise AssertionError("An unmodeled spin conversion or inlet pressure change was admitted")
    try:
        bind_linepack_fuel_cell_feed(source, cell, step,
            **{**feed_arguments, "origin": Origin.MEASURED})
    except ValueError as error:
        assert "origin must preserve" in str(error)
        rejected += 1
    else:
        raise AssertionError("Synthetic linepack source was upgraded to measured feed evidence")
    mutations = (
        (eos, "version", "altered-native-provider"),
        (eos, "density_pt", lambda p, t: 1.),
        (properties, "state_pt", lambda p, t: outlet),
        (source.ledger, "outlet_mass_kg", source.ledger.outlet_mass_kg+0.001),
        (source, "state_projection_evidence_id", "relabeled-after-issue"),
    )
    for target, name, changed in mutations:
        original = getattr(target, name)
        try:
            object.__setattr__(target, name, changed)
            try:
                receipt.require_current()
            except ValueError:
                rejected += 1
            else:
                raise AssertionError("Changed EOS, property callable or source ledger retained admission")
        finally:
            object.__setattr__(target, name, original)
        assert receipt.require_current() is receipt
    return ValidationOutcome(True, {
        "withdrawal_mass_kg": receipt.source_mass_kg,
        "feed_amount_mol": receipt.feed_amount_mol,
        "initial_pressure_pa": initial.pressure_pa, "final_pressure_pa": final.pressure_pa,
        "mass_residual_kg": ledger.mass_residual_kg,
        "energy_residual_j": receipt.energy_residual_j,
        "integrated_source_enthalpy_j": source_h,
        "enthalpy_quadrature_error_j": quadrature_error,
        "invalid_boundaries_rejected": rejected,
        "normal_to_para_rejected": True,
        "normal_to_unspecified_spin_rejected": True,
        "mismatched_inlet_pressure_rejected": True,
        "source_origin_upgrade_rejected": True,
    }, (
        "Native real-gas inventory and component accounting; no measured facility validation",
        "Prescribed withdrawal and held temperature; no regulator, thermal or momentum solve",
        "Independent native-path energy quadrature is supplied to the adapter as caller evidence",
        "Conditioning is an imposed enthalpy balance, not a solved regulator or utility",
    ))
