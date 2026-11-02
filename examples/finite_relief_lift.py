"""Construction sketch for the unexecuted finite relief-lift composition."""

from dataclasses import dataclass

from h2physics.adapters.relief_lift import (
    FiniteLiftRelief,
    PhasePickup,
    PhasePickupOwner,
    ReliefLiftLaw,
)


@dataclass(frozen=True)
class AuthoredTankPoint:
    pressure_pa: float
    vapor_state: object
    vapor_mass_kg: float
    state_id: str


def build_finite_relief(*, native_protection, nozzle, opening):
    """Bind actual owners supplied by the calling native-relief setup.

    This function deliberately cannot construct a synthetic native protection or
    property state. The caller must pass the existing reviewed objects.
    """

    basis = nozzle.properties.basis

    def select_vapor(native_state):
        if not isinstance(native_state, AuthoredTankPoint):
            raise TypeError("This example owner admits only its explicit tank-point type")
        return PhasePickup(
            vessel_pressure_pa=native_state.pressure_pa,
            upstream=native_state.vapor_state,
            available_mass_kg=native_state.vapor_mass_kg,
            phase_id="vapor-port",
            selection_id="authored-top-port-selection",
            state_id=native_state.state_id,
            native_tank_state=native_state,
        )

    owner = PhasePickupOwner(
        owner_id="authored-phase-resolved-tank-owner",
        property_basis=basis,
        admitted_phase_ids=("vapor-port",),
        select=select_vapor,
    )
    law = ReliefLiftLaw(
        opening_rate_fraction_s=4.0,
        closing_rate_fraction_s=2.0,
        closed_leakage_fraction=1e-4,
        maximum_clock_step_s=0.05,
        law_id="authored-linear-travel-reference",
        coefficient_evidence_id="replace-with-qualified-device-evidence",
    )
    return FiniteLiftRelief(
        native_protection,
        nozzle=nozzle,
        opening=opening,
        pickup=owner,
        law=law,
        evidence_id="authored-unverified-relief-lift-composition",
    )


def build_native_fixture(*, vapor_mass_kg=1.0):
    """Build authored accepted-sample cases around reviewed native owners.

    Native LH2DT protection and property-state objects are used, but fixture
    pressures, inventory, lift coefficients and downstream conditions are
    synthetic contract inputs rather than equipment data.
    """
    import lh2dt
    from pathlib import Path
    from lh2dt import valve as valve_module
    from lh2dt.properties import ThermoState as NativeState

    from h2physics.adapters.lh2dt import from_lh2dt_state
    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.adapters.lh2dt_relief import shared_native_relief
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties
    from scripts.check_relief_integration import NATIVE_SOURCE_SHA256, REVISION, native_hash

    native_dir = Path(lh2dt.__file__).resolve().parent
    if native_hash(native_dir) != NATIVE_SOURCE_SHA256:
        raise ValueError("Use the reviewed pinned LH2DT source for the deferred fixture")
    properties = CoolPropProperties("Hydrogen")
    facade = Lh2dtLowLevelProperties(properties, state_factory=NativeState)
    bridge = Lh2dtProperties(facade, reference_id=properties.basis.reference_id)
    opening = NozzleOpening("authored-finite-lift-orifice", 1e-6, 1.,
                            "synthetic-contract-area")
    nozzle = HomogeneousIsentropicNozzle(properties)
    protection = shared_native_relief(
        native_valve_type=valve_module.Valve,
        native_relief_factory=valve_module.PressureReliefValve,
        result_factory=valve_module.ValveResult,
        nozzle=nozzle, bridge=bridge, opening=opening,
        set_pressure_pa_absolute=2e5, reseat_pressure_pa_absolute=1.8e5,
        native_source_id="LH2DT:" + REVISION,
    )
    pressures = (1.9e5, 2.1e5, 2.0e5, 1.7e5)
    points = tuple(facade.from_pT(pressure, 300.) for pressure in pressures)
    native_state_type = type(points[0])

    def select_phase(native_state):
        if type(native_state) is not native_state_type:
            raise TypeError("Synthetic phase owner accepts only its native LH2DT state type")
        return PhasePickup(
            vessel_pressure_pa=native_state.pressure_Pa,
            upstream=from_lh2dt_state(native_state, basis=properties.basis),
            available_mass_kg=vapor_mass_kg,
            phase_id="synthetic-vapor-port",
            selection_id="authored-top-port-fixture",
            state_id=f"synthetic-relief-state-{native_state.pressure_Pa:.0f}Pa",
            native_tank_state=native_state,
        )

    owner = PhasePickupOwner(
        owner_id="authored-synthetic-native-phase-owner",
        property_basis=properties.basis,
        admitted_phase_ids=("synthetic-vapor-port",), select=select_phase,
    )
    law = ReliefLiftLaw(
        opening_rate_fraction_s=4., closing_rate_fraction_s=2.,
        closed_leakage_fraction=1e-4, maximum_clock_step_s=.05,
        law_id="authored-finite-lift-contract-law",
        coefficient_evidence_id="synthetic-fixture-only",
    )
    model = FiniteLiftRelief(
        protection, nozzle=nozzle, opening=opening, pickup=owner, law=law,
        evidence_id="synthetic-finite-lift-deferred-contract",
    )
    downstream = properties.state_pt(1e5, 300.)
    return model, points, downstream
