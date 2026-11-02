"""Deferred contracts for segmented transient compressible pipe inventories."""

from math import log10

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="segmented-isothermal-gas-pipe-inventory-network",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_network_contract",
        invariants=(
            "finite cell inventories drive instantaneous pressure-dependent Darcy link flows",
            "signed intercell transfers cancel from total network mass conservation",
            "caller boundary injection and withdrawal are integrated over the declared clock",
            "a positive caller-selected cell inventory floor localizes and identifies terminal depletion",
            "fixed temperature/composition and quasi-steady links are explicit model assumptions",
        ),
    ), ValidationCase(
        identifier="segmented-native-CoolProp-isothermal-pipe-network",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_native_network",
        invariants=(
            "native-cell-EOS-and-shared-native-Darcy-links-drive-the-existing-mass-ODE",
            "closed-three-cell-transfer-conserves-mass-and-real-step-refinement-reproduces-pressure",
            "reverse-nearzero-and-no-flow-cases-preserve-signed-links",
            "native-inventory-floor-event-retains-the-accepted-terminal-state",
            "mixed-bases-phase-policy-and-provider-mutation-reject-without-fallback",
        ),
    ), ValidationCase(
        identifier="segmented-native-frozen-mixture-isothermal-pipe-network",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_native_mixture_network",
        invariants=(
            "same-frozen-mixture-reference-and-composition-are-retained-in-every-cell",
            "native-quasi-steady-links-reuse-the-existing-network-mass-ODE",
            "closed-three-cell-transfer-conserves-mass-and-step-refinement-reproduces-the-solution",
        ),
    ))


def validate_network_contract(*, work_directory, **parameters):
    import numpy as np

    from h2physics.hydraulics import DarcyGeometry
    from h2physics.isothermal_gas_pipe_network import (
        IsothermalGasPipeNetwork,
        IsothermalPipeCell,
        IsothermalPipeLink,
    )

    del work_directory, parameters
    def darcy_factor(reynolds, relative_roughness):
        if reynolds < 2300.:
            return 64. / reynolds
        return (-1.8 * log10((relative_roughness / 3.7) ** 1.11 + 6.9 / reynolds)) ** -2

    # Keep signed cell-boundary forcing larger than the internal exchange so
    # both local mass-change assertions remain identifiable in this fixture.
    geometry = DarcyGeometry(100., .001, 1e-5)
    pressure = (5.0e6, 4.5e6, 4.0e6)
    temp = 300.
    molar_mass = .00201588
    gas_constant = 8.31446261815324
    cells = tuple(IsothermalPipeCell(
        f"segment-{i}", 1., temp, molar_mass,
        p * molar_mass / (gas_constant * temp),
    ) for i, p in enumerate(pressure))
    links = tuple(IsothermalPipeLink(
        f"link-{i}", geometry, 8.9e-6,
    ) for i in range(2))
    network = IsothermalGasPipeNetwork(cells, links, darcy_factor, "authored-Haaland-plus-laminar-v1")
    trace = network.simulate(
        boundary_mass_flow_kg_s=(.002, 0., -.001),
        boundary_evidence_ids=("synthetic-inlet", "synthetic-sealed-midpoint", "synthetic-outlet"),
        time_samples_s=(0., .1, .5, 1.),
        minimum_cell_mass_kg=.01,
        relative_tolerance=1e-10,
        absolute_tolerance_kg=1e-12,
    )
    if not trace.complete or not np.array_equal(trace.time_s, (0., .1, .5, 1.)):
        raise AssertionError("Accepted network run did not retain its full requested sample clock")
    if np.max(np.abs(trace.mass_balance_residual_kg)) > 1e-8:
        raise AssertionError("Signed boundaries and intercell transfers did not close network mass")
    if not np.all(trace.link_mass_flow_kg_s[0] > 0.):
        raise AssertionError("Initially descending pressure did not produce downstream flow")
    if not (trace.mass_kg[-1, 0] > trace.mass_kg[0, 0]
            and trace.mass_kg[-1, 2] < trace.mass_kg[0, 2]):
        raise AssertionError("Boundary injection/withdrawal did not affect their declared cells")
    try:
        trace.mass_kg.setflags(write=True)
    except ValueError:
        immutable = True
    else:
        raise AssertionError("Network trace mass arrays must be bytes-backed immutable")

    equal_pressure_cells = tuple(IsothermalPipeCell(
        f"depletion-segment-{i}", 1., temp, molar_mass,
        5.e6 * molar_mass / (gas_constant * temp),
    ) for i in range(2))
    depletion_network = IsothermalGasPipeNetwork(
        equal_pressure_cells,
        (IsothermalPipeLink("small-bore", DarcyGeometry(100., .001, 1e-6), 8.9e-6),),
        darcy_factor, "authored-Haaland-plus-laminar-v1",
    )
    initial_first_mass = equal_pressure_cells[0].initial_mass_kg
    floor = initial_first_mass - .01
    terminal = depletion_network.simulate(
        boundary_mass_flow_kg_s=(-1., 0.),
        boundary_evidence_ids=("synthetic-demand", "synthetic-isolated-boundary"),
        time_samples_s=(0., .2), minimum_cell_mass_kg=floor,
        relative_tolerance=1e-10,
        absolute_tolerance_kg=1e-12,
    )
    if (terminal.complete or terminal.terminal_cell_id != "depletion-segment-0"
            or not np.isclose(terminal.mass_kg[-1, 0], floor, rtol=0., atol=2e-8)):
        raise AssertionError("Inventory-floor event was not localized and attributed to its cell")
    return ValidationOutcome(True, {
        "cells": len(trace.cell_ids),
        "links": len(trace.link_ids),
        "sample_count": len(trace.time_s),
        "maximum_mass_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
        "initial_link_flows_kg_s": trace.link_mass_flow_kg_s[0].tolist(),
        "depletion_time_s": float(terminal.time_s[-1]),
        "depletion_cell_id": terminal.terminal_cell_id,
        "immutable_arrays": immutable,
    }, (
        "Synthetic software contract only; fixed ideal-gas temperature/composition and quasi-steady Darcy links, no real-gas EOS, line inertia, pressure waves, choking, or energy equation.",
    ))


def validate_native_network(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.hydraulics import DarcyGeometry
    from h2physics.isothermal_gas_pipe_network import (
        IsothermalGasPipeNetwork,
        IsothermalPipeCell,
        IsothermalPipeLink,
    )
    from h2physics.thermo import CoolPropIsothermalEOS

    def darcy_factor(reynolds, relative_roughness):
        if reynolds < 2300.:
            return 64./reynolds
        return (-1.8*log10((relative_roughness/3.7)**1.11+6.9/reynolds))**-2

    def cell(index, pressure, *, fluid="Hydrogen", temperature=300.):
        return IsothermalPipeCell.from_pressure(cell_id=f"native-cell-{index}",
            volume_m3=.001, temperature_k=temperature, pressure_pa=pressure,
            eos=CoolPropIsothermalEOS(fluid))

    cells = tuple(cell(index, pressure) for index, pressure in enumerate((5e6, 4.8e6, 4.6e6)))
    links = tuple(IsothermalPipeLink(f"native-link-{index}", DarcyGeometry(10., .001, 1e-6), 8.9e-6)
                  for index in range(2))
    network = IsothermalGasPipeNetwork(cells, links, darcy_factor, "authored-Haaland-laminar-native")
    assert cells[0].eos is not cells[1].eos
    assert cells[0].specific_gas_constant_j_kg_k is None
    arguments = dict(boundary_mass_flow_kg_s=(0., 0., 0.),
        boundary_evidence_ids=("closed-left", "closed-middle", "closed-right"),
        time_samples_s=(0., .5, 1.), minimum_cell_mass_kg=1e-5,
        method="RK45", relative_tolerance=1e-5, absolute_tolerance_kg=1e-10)
    traces = [network.simulate(**arguments, maximum_step_s=step) for step in (.5, .25, .125)]
    coarse, medium, fine = traces
    fine.require_current()
    assert fine.complete and np.all(fine.link_mass_flow_kg_s[0] > 0.)
    assert np.max(np.abs(fine.mass_balance_residual_kg)) < 1e-10
    assert fine.mass_kg[-1, 0] < fine.mass_kg[0, 0]
    assert fine.mass_kg[-1, -1] > fine.mass_kg[0, -1]
    difference_a = float(np.max(np.abs(coarse.mass_kg[-1]-medium.mass_kg[-1])))
    difference_b = float(np.max(np.abs(medium.mass_kg[-1]-fine.mass_kg[-1])))
    assert difference_b <= difference_a+1e-13 and difference_b < 1e-9
    for row, pressure in zip(fine.mass_kg, fine.pressure_pa, strict=True):
        direct = [item.eos.pressure_rho_t(mass/item.volume_m3, item.temperature_k)
                  for item, mass in zip(cells, row, strict=True)]
        assert np.allclose(direct, pressure, rtol=1e-12, atol=1e-6)
    forward = network._link_flows(np.array([5e6, 4.8e6, 4.6e6]))
    reverse = network._link_flows(np.array([4.6e6, 4.8e6, 5e6]))
    assert np.allclose(reverse, -forward[::-1], rtol=1e-9, atol=1e-12)
    near_zero = network._link_flows(np.array([5e6, 5e6-.001, 5e6-.002]))
    assert np.all(near_zero > 0.) and np.all(near_zero < forward)
    assert np.array_equal(network._link_flows(np.full(3, 5e6)), np.zeros(2))
    equal = tuple(cell(index, 5e6) for index in range(2))
    quiet_network = IsothermalGasPipeNetwork(equal, (links[0],), darcy_factor,
                                            "authored-Haaland-laminar-native")
    quiet = quiet_network.simulate(boundary_mass_flow_kg_s=(0., 0.),
        boundary_evidence_ids=("closed-a", "closed-b"), time_samples_s=(0., .1),
        minimum_cell_mass_kg=1e-5)
    assert np.array_equal(quiet.mass_kg[0], quiet.mass_kg[-1])
    assert np.array_equal(quiet.link_mass_flow_kg_s, np.zeros((2, 1)))
    floor = equal[0].initial_mass_kg-1e-5
    terminal = quiet_network.simulate(boundary_mass_flow_kg_s=(-.01, 0.),
        boundary_evidence_ids=("prescribed-withdrawal", "closed-b"),
        time_samples_s=(0., .005), minimum_cell_mass_kg=floor,
        maximum_step_s=.0005, relative_tolerance=1e-9, absolute_tolerance_kg=1e-12)
    terminal.require_current()
    assert not terminal.complete and terminal.terminal_cell_id == equal[0].cell_id
    assert np.isclose(terminal.mass_kg[-1, 0], floor, rtol=0., atol=1e-10)

    rejected = 0
    analytic = IsothermalPipeCell("analytic", .001, 300., .00201588, .004)
    for operation in (
        lambda: IsothermalGasPipeNetwork((cells[0], analytic), (links[0],), darcy_factor, "mixed"),
        lambda: IsothermalGasPipeNetwork((cells[0], cell(8, 5e6, fluid="ParaHydrogen")),
            (links[0],), darcy_factor, "wrong-spin"),
        lambda: IsothermalGasPipeNetwork((cells[0], cell(8, 5e6, temperature=301.)),
            (links[0],), darcy_factor, "wrong-temperature"),
        lambda: cell(8, 1e6, temperature=20.),
        lambda: cell(9, 4.8e6, fluid="H2"),
        lambda: IsothermalPipeCell("wrong-molar-mass", .001, 300., .004, .004,
            eos=CoolPropIsothermalEOS("Hydrogen")),
        lambda: network.simulate(**arguments, maximum_step_s=0.),
        lambda: replace(fine),
    ):
        try:
            operation()
        except (TypeError, ValueError):
            rejected += 1
        else:
            raise AssertionError("Invalid native cell/network basis or trace clone admitted")
    eos = cells[0].eos
    for target, name, changed in (
        (eos, "version", "changed-version"),
        (eos, "pressure_rho_t", lambda rho, t: 5e6),
        (eos, "_require_homogeneous_gas", lambda: None),
        (eos, "_update_pt", lambda p, t: None),
        (eos, "_update_rho_t", lambda rho, t: None),
        (eos, "isothermal_sound_speed_rho_t", lambda rho, t: 1000.),
        (eos, "_allowed_phases", eos._allowed_phases | {eos._cp.iphase_liquid}),
        (network, "friction_law", lambda re, rough: .02),
        (fine, "friction_law_id", "relabelled-friction"),
    ):
        original = getattr(target, name)
        try:
            object.__setattr__(target, name, changed)
            try:
                fine.require_current()
            except ValueError:
                rejected += 1
            else:
                raise AssertionError("Native EOS, correlation or trace evidence mutation admitted")
        finally:
            object.__setattr__(target, name, original)
    fine.require_current()
    assert rejected == 17
    return ValidationOutcome(True, {
        "native_cells": len(cells), "closed_mass_residual_kg": float(np.max(np.abs(fine.mass_balance_residual_kg))),
        "initial_link_flows_kg_s": forward.tolist(), "near_zero_flows_kg_s": near_zero.tolist(),
        "final_pressure_pa": fine.pressure_pa[-1].tolist(),
        "coarse_medium_mass_difference_kg": difference_a,
        "medium_fine_mass_difference_kg": difference_b,
        "inventory_floor_time_s": float(terminal.time_s[-1]),
        "native_invalid_definitions_rejected": rejected,
    }, (
        "Native direct CoolProp fixed-temperature gas inventories and quasi-steady subsonic links",
        "Constant caller viscosity/friction and prescribed boundary rates; no pipe inertia or thermal solve",
        "Numerical conservation/refinement checks; no measured pipeline qualification",
    ))


def validate_native_mixture_network(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.hydraulics import DarcyGeometry
    from h2physics.isothermal_gas_pipe_network import (
        IsothermalGasPipeNetwork,
        IsothermalPipeCell,
        IsothermalPipeLink,
    )
    from h2physics.mixtures import GasComposition
    from h2physics.thermo import CoolPropMixtureIsothermalEOS, CoolPropMixtureProperties

    def eos():
        return CoolPropMixtureIsothermalEOS(CoolPropMixtureProperties(GasComposition(
            "closed-H2-N2-network", ("Hydrogen", "Nitrogen"), (.1, .9), (.00201588, .0280134),
        )))

    cells = tuple(IsothermalPipeCell.from_pressure(
        cell_id=f"mixture-{index}", volume_m3=.001, temperature_k=300., pressure_pa=pressure, eos=eos(),
    ) for index, pressure in enumerate((5.e6, 4.8e6, 4.6e6)))
    viscosity = cells[0].eos.properties.state_pt(5.e6, 300.).viscosity_pa_s
    links = tuple(IsothermalPipeLink(f"mixture-link-{index}", DarcyGeometry(10., .001, 1.e-6), viscosity)
                  for index in range(2))
    network = IsothermalGasPipeNetwork(cells, links, lambda re, rr: .03, "authored-mixture-constant-factor")
    arguments = dict(boundary_mass_flow_kg_s=(0., 0., 0.),
        boundary_evidence_ids=("closed-left", "closed-middle", "closed-right"),
        time_samples_s=(0., .05, .1), minimum_cell_mass_kg=1.e-5,
        method="RK45", relative_tolerance=1.e-7, absolute_tolerance_kg=1.e-12)
    coarse, medium, fine = [network.simulate(**arguments, maximum_step_s=step)
                             for step in (.1, .05, .025)]
    fine.require_current()
    first_difference = float(np.max(np.abs(coarse.mass_kg[-1]-medium.mass_kg[-1])))
    second_difference = float(np.max(np.abs(medium.mass_kg[-1]-fine.mass_kg[-1])))
    assert second_difference <= first_difference+1.e-13
    assert second_difference < 1.e-9
    assert np.max(np.abs(fine.mass_balance_residual_kg)) < 1.e-11
    assert np.all(fine.link_mass_flow_kg_s[0] > 0.)
    assert fine.mass_kg[-1, 0] < fine.mass_kg[0, 0]
    assert fine.mass_kg[-1, -1] > fine.mass_kg[0, -1]
    assert all("mixture-H2-spin-unresolved" in identity for identity in fine.eos_identities)
    assert cells[0].eos is not cells[1].eos
    return ValidationOutcome(True, {
        "cells": len(cells), "h2_mole_fraction": .1,
        "maximum_mass_residual_kg": float(np.max(np.abs(fine.mass_balance_residual_kg))),
        "coarse_medium_mass_difference_kg": first_difference,
        "medium_fine_mass_difference_kg": second_difference,
        "initial_link_flows_kg_s": fine.link_mass_flow_kg_s[0].tolist(),
        "final_pressure_pa": fine.pressure_pa[-1].tolist(),
    }, (
        "Fixed-composition CoolProp mixture and existing quasi-steady mass ODE; no species equation.",
        "All cells require identical full provider reference/composition identities; distinct source composition IDs remain distinct.",
        "Synthetic numerical conservation/refinement only; no blend-pipeline data or facility qualification.",
    ))
