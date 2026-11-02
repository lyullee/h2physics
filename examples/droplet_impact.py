"""Authored conditional impact example; not executed during development.

Every coefficient below is a synthetic verification fixture. No LH2 impact
measurement, qualified deposition fraction or fitted material value is claimed.
"""

from h2physics.adapters.droplet_impact import (
    FiniteSurfaceImpact,
    ImpactOutcome,
    ImpactQualification,
    IntercontactThermalResult,
    QualifiedImpactClosure,
    SurfacePatch,
)
from h2physics.core import Origin
from h2physics.release import SourceLocation

STATUS = "implemented_unverified"


def authored_outcome(*, conductance_w_k=.01, contact_duration_s=.01,
                     deposited_fraction=.6, normal_restitution=.4):
    return ImpactOutcome(deposited_fraction, normal_restitution, .5, (0., 0., .2),
        conductance_w_k, contact_duration_s, 0., "authored-conditional-contact-not-H2-calibration",
        Origin.SYNTHETIC, {"assumption": "authored coefficients and zero net interfacial energy"})


def build_model(*, outcome=None, heat_capacity_j_k=.01, wall_temperature_k=80.,
                closure=None, tolerances=None, intercontact_heat=None):
    from h2physics.thermo.coolprop import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    location = SourceLocation("authored-impact-patch", "authored-impact-clock",
        "authored-inertial-z-up", (0., 0., 0.), (0., 0., 1.))
    patch = SurfacePatch(location, 100., .01, heat_capacity_j_k, wall_temperature_k,
        15., 120., .1, "authored-finite-effective-mass-and-capacity-not-material-fit",
        "authored-rigid-fixed-mount-zero-work-arrest",
        "authored-clear-to-separate-at-rest-receiver-no-wet-patch-impact",
        "authored-intercontact-thermal-boundary", Origin.SYNTHETIC,
        {"authored_surface": "finite capacity/effective inertial mass reference"})
    if closure is None:
        parameters = authored_outcome() if outcome is None else outcome
        qualification = ImpactQualification("authored-contact-domain-not-experimental-qualification",
            Origin.SYNTHETIC, (1e5, 1.1e5), (15., 120.), (1e-5, .01), (.1, 10.), (0., 1e5),
            "authored-lumped-small-Biot-assumption", "authored-impulsive-negligible-external-work",
            "authored-saturated-normal-H2-local-phase-equilibrium")
        closure = QualifiedImpactClosure(qualification, lambda context: parameters, parameters)
    kwargs = {} if tolerances is None else {"tolerances": tolerances}
    return FiniteSurfaceImpact(properties, patch, closure,
        intercontact_heat=intercontact_heat, **kwargs)


def authored_intercontact_heat(context):
    """Monotone prescribed heat reference; not a measured surface boundary."""
    heat = 0.001 if context.end_time_s > context.start_time_s else 0.
    final = context.initial_temperature_k+heat/context.heat_capacity_j_k
    return IntercontactThermalResult(context.start_time_s, context.end_time_s, heat,
        min(context.initial_temperature_k, final), max(context.initial_temperature_k, final),
        "authored-monotone-intercontact-heat-reference", Origin.SYNTHETIC,
        {"boundary": "prescribed integrated heat, no measured trajectory"} if heat else None)


def incident_trace(model, *, start_s=100., maximum_step_s=.01):
    """Deferred actual native parcel event; no constructed/fake ParcelTrace."""
    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        SaturatedParcelFlight,
    )

    patch = model.patch
    boundary = ParcelBoundary(patch.location.clock_id, patch.location.coordinate_frame_id,
        "authored-zero-relative-drag-and-zero-flight-heat", .01, 1e-5,
        (0., 0., -1.), (0., 0., 0.), 1e5, 1., .002, .01)
    flight = SaturatedParcelFlight(model.properties, 101325., boundary,
        lambda state: BoilingHeat(0., "authored-zero-boiling-heat-limit"),
        force_approximation_evidence_id="authored-isolated-zero-external-force-reference")
    return flight.run(start_s=start_s, end_s=start_s+2., position_m=(0., 0., 1.),
        velocity_m_s=(0., 0., -1.), mass_kg=1e-6, residual_mass_floor_kg=1e-8,
        maximum_step_s=maximum_step_s, relative_tolerance=1e-10,
        absolute_tolerances=(1e-12,)*17, ground_z_m=0.)


def main():
    model = build_model()
    result = model.run((incident_trace(model),))
    print(STATUS)
    print("Incident/deposited/rebound/vapor kg:", result.total_incident_mass_kg,
          result.deposited_mass_kg, result.rebound_mass_kg, result.vapor_mass_kg)
    print("Finite patch final K:", result.final_wall_temperature_k)
    print("This conditional reference is not a qualified LH2 impact correlation.")


if __name__ == "__main__":
    main()
